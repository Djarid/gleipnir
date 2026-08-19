# `ansible/tests/` — the 3-layer test harness

Implements the Stress-test "TEST STRATEGY" section of
[`../../.gleipnir/plans/s2-caged-ansible.md`](../../.gleipnir/plans/s2-caged-ansible.md),
per the D3 operator-converged requirement (all three layers, incl. layer-3
fixture-tree idempotency) in
[`../../.gleipnir/decisions/s2-caged-ansible.md`](../../.gleipnir/decisions/s2-caged-ansible.md).

## Status (D4-FU done) — READ THIS FIRST

**These tests have been run and pass green.** They were authored test-first per
the operator-converged D4 decision while Ansible was not yet installed; Ansible
has since been installed (`brew install ansible ansible-lint`; ansible-core
2.21.3, ansible-lint 26.8.0) and all three layers now PASS: syntax-check,
ansible-lint (production profile, 0 failures), `--check`-mutates-nothing,
idempotency (second run `changed=0`), and the AC-4-fail path. The first real run
surfaced and fixed genuine defects (act-4 file/dir split; act-3 overlap = D5;
act-4/act-5 key overlap = D6) — the value of actually running the harness.

Re-run with `sh run.sh` (needs Ansible on PATH). **If you run this on a box
WITHOUT Ansible, the layers that need it print `SKIP`, not `PASS`** — those SKIP
branches remain, so the harness degrades honestly on a bare box; read the
`PASS`/`SKIP`/`FAIL` lines, not just the exit code. `run.sh` prints a banner
naming the toolchain gap only when Ansible is genuinely absent.

One sub-part of layer 1 — the grep-based structural invariant checks
(AC-order, AC-env, AC-nolit, AC-mirror) — needs **no** Ansible at all (pure
text), so those genuinely run and genuinely pass/fail today, independent of
the D4 gap. They are the "load-bearing invariants as text" the plan calls
for.

## Layers

| Layer | Script | What it proves | Needs Ansible? |
|---|---|---|---|
| 1. Static | `layer1-static.sh` | `--syntax-check`, `ansible-lint`, + 4 grep-based structural asserts (order, env fix, no hardcoded uid, path-list mirror) | syntax-check/lint: yes. Grep asserts: no. |
| 2. Dry-run | `layer2-dryrun.sh` | `--check` against a disposable fixture tree resolves every task and mutates nothing | yes |
| 3. Idempotency | `layer3-idempotency.sh` | (a) real chmod/chown on a disposable fixture, run twice, second run `changed=0`; (b) the AC-4-fail "no false green" path | yes |

Run all three: `sh run.sh` (works regardless of execute bits; `run.sh`
internally invokes each layer via `sh`, not direct exec, for the same
reason — these scripts were authored by an agent with no `chmod`
capability, so don't assume the execute bit survived a fresh
checkout/tarball. `./run.sh` also works once bits are set, e.g. by `git`
preserving a committed `+x` mode.).

## Why a disposable fixture tree, not the real repo

Layers 2 and 3 build a throwaway directory (`mktemp -d`) that mimics the
shape of `.gleipnir/` just enough to exercise the playbook's task plumbing —
see `lib/fixture_tree.sh` for exactly what it contains and why (notably:
`plugins/` is left absent on purpose, to exercise the E-2 tolerate-absent
path; the fake key starts at mode 644 on purpose, to exercise both the
converge-to-600 path and the AC-4-fail path from one fixture shape). The
fixture is torn down (`rm -rf`) at the end of each script, guarded so
`teardown_fixture_tree` refuses to `rm -rf` anything that doesn't look like a
`mktemp -d` path.

**Never**: uid 510, the real `gleipniragent` account, `sudo`, or any mutation
of this checkout. `agent_account_name` is overridden to `staff` (a group that
already exists, unprivileged) for the fixture runs so act-3's `chgrp` step
exercises real idempotent logic without creating an OS account/group — see
the header comment in `layer3-idempotency.sh`.

## Why a fake `bin/gleipnir-preflight` inside the fixture

The fixture's `bin/gleipnir-preflight` is **not** the real preflight binary —
it's `fixtures/fake-gleipnir-preflight.sh`, copied in by
`lib/fixture_tree.sh`. The real `bin/gleipnir-preflight` execs
`"$repo/.venv/bin/python" -m gleipnir.preflight` from its *own* on-disk
location (not the fixture's), and `boundary.py`'s behavioural probe already
has its own unit-test coverage elsewhere in this repo
(`tests/test_preflight_decision.py` and friends). This harness's job is
narrower: prove the **Ansible task plumbing** around that binary — the
`environment: GLEIPNIR_MARKER_KEY_FILE` fix survives, the rc is checked, act-5
runs before AC-4 — not to re-derive `boundary.py`'s own verdict logic. The
fake stand-in honours the same rc contract (0 = CLOSED, 1 = REFUSE) using the
one perm this harness actually manipulates (the fixture key's mode).

The **genuine** AC-4-pass (real preflight, real `.venv`, real uid 510,
`Verdict.CLOSED`) can only be proven by the operator on the real box — that
is out of CI/this harness by design (see the plan's Test Strategy section)
and is not claimed here.

## Prerequisites once Ansible is installed

```sh
brew install ansible ansible-lint   # or: pipx install ansible ansible-lint
cd ansible/tests && ./run.sh
```
