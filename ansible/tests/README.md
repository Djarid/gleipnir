# `ansible/tests/` — the 3-layer test harness

Implements the Stress-test "TEST STRATEGY" section of
[`../../.gleipnir/plans/s2-caged-ansible.md`](../../.gleipnir/plans/s2-caged-ansible.md),
per the D3 operator-converged requirement (all three layers, incl. layer-3
fixture-tree idempotency) in
[`../../.gleipnir/decisions/s2-caged-ansible.md`](../../.gleipnir/decisions/s2-caged-ansible.md).

## Honesty label (D4) — READ THIS FIRST

**These tests are authored, not yet executed.** As of this session, this box
has no `ansible`, `ansible-playbook`, or `ansible-lint` binary, and the
S-2 sandbox (`bin/gleipnir-sandbox`) has no `[profile.ansible]` — only
`python`/`node`/`broker`. D4 (the operator-converged decision) is: author the
playbook and this harness now, test-first, and run them for the *first* time
once Ansible is installed (`brew install ansible ansible-lint`, or via
`pipx`). **Do not read a script in this directory exiting 0 as proof the
Ansible playbook is correct** unless its own output shows `PASS` lines, not
`SKIP` lines, for the checks that matter to you. `run.sh` prints an explicit
banner naming the toolchain gap every time it runs.

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
