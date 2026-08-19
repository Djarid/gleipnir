# `ansible/` — S-2 caged-mode host setup

Mechanises the six S-2/G-1 caged-mode host acts in
[`../.gleipnir/plans/s2-activation-control-proposal.md`](../.gleipnir/plans/s2-activation-control-proposal.md)
as a single idempotent, re-runnable, self-verifying playbook, per the
converged decision
[`../.gleipnir/decisions/s2-caged-ansible.md`](../.gleipnir/decisions/s2-caged-ansible.md)
and the plan
[`../.gleipnir/plans/s2-caged-ansible.md`](../.gleipnir/plans/s2-caged-ansible.md).

**Out-of-framework OPERATOR tooling** (BC-6) — same class as `bin/`. Run by
the trusted operator under `sudo`, never by an in-framework agent, never
under `.gleipnir/` (the very subtree it hardens).

## Status: authored, not yet executed (D4)

Ansible is **not installed** on the box this was authored on, and the S-2
sandbox has no `[profile.ansible]`. This playbook and its
[3-layer test harness](tests/README.md) are authored test-first, per the
operator-converged D4 decision, and are honestly labelled
**authored-but-not-yet-executed** until the operator installs Ansible
(`brew install ansible ansible-lint`, or `pipx`) and runs `ansible/tests/run.sh`
for the first genuine pass. Do not treat this playbook's presence in the repo
as evidence it has ever been run.

## What it does

Acts (1)–(6) of the proposal, in this exact order (act-5 key-lock textually
**after** act-4's recursive pass — BC-2 — so the recurse never leaves the
key loosened), then a **failing assertion** (AC-4) that the caged boundary
genuinely closed:

1. **act 1** — create the dedicated non-login agent uid/gid (`dscl`/
   `sysadminctl`), guarded so re-running is a no-op.
2. **act 3** — ownership/group layout: operator owns the repo; source +
   `.gleipnir` readable to all; Tier-0/1/2 dirs (`plans/`, `var/tmp/`,
   `logs/`, `memory/`, `lessons/`) group-writable by the agent account.
3. **act 4** — the 8 LOCKED enforcement paths
   (`src/gleipnir/preflight/boundary.py:168-222`) hardened `a+rX,go-w`;
   `plugins/` tolerates absence.
4. **act 5** — the G-3 key locked `0600`, owner-only — **after** act 4, so
   the recursive pass above never re-loosens it. Unconditional in both
   modes (never relaxed by any teardown path).
5. **act 6** — installs `bin/gleipnir-launch`'s perms (`0755`,
   `operator:staff`). Does **not** author or rewrite the file — it is
   already written and reviewed.
6. **AC-4** — runs `bin/gleipnir-preflight --mode caged` (with the
   `environment: GLEIPNIR_MARKER_KEY_FILE` fix, since `sudo` strips it) and
   **fails the playbook run** if the preflight does not report rc 0
   (`Verdict.CLOSED`). This is the "no false green" proof (BC-7): playbook
   success never substitutes for the preflight's own verdict.

## What it deliberately does NOT do

- **Never enters caged mode.** `sudo bin/gleipnir-launch` — the act of
  actually starting a caged session — stays a separate, explicit, later
  operator act (D2/BC-7). This playbook installs the *capability* and
  proves the boundary *can* close; it never flips the switch itself. The
  operator always knows when they go caged; it is never a side effect of
  running this setup.
- **Never installs Ansible itself** (host precondition, brew/pipx).
- **Never creates uid/gid literals** — `agent_uid`/`agent_gid` are read from
  `.gleipnir/agent-identity.env` at play start (P3); no numeric uid/gid
  literal appears anywhere in `site.yml` or `group_vars/all.yml`
  (`ansible/tests/layer1-static.sh`'s AC-nolit check enforces this).
- **Never rewrites `bin/gleipnir-launch`** — perms only.

## Running it

```sh
sudo ansible-playbook -i inventory.ini site.yml
```

Run from inside `ansible/` (so the default `repo: "{{ playbook_dir }}/.."`
resolves correctly), or from the repo root with explicit paths:

```sh
sudo ansible-playbook -i ansible/inventory.ini ansible/site.yml
```

Prerequisites:
- Ansible installed (`brew install ansible`).
- `.gleipnir/agent-identity.env` present (normally already true — act 2 of
  the proposal; this playbook reads it, never writes it, and fails fast
  with a clear message if it's missing rather than inventing a uid).
- `.gleipnir/keys/marker.key` present (fails fast with a clear message if
  missing rather than a raw chmod error).
- `$repo/.venv/bin/python` present — the AC-4 preflight shim
  (`bin/gleipnir-preflight`) execs it.

Dry-run first: `sudo ansible-playbook -i inventory.ini site.yml --check`.

The destructive act-1 user/group creation is tagged `user_create`,
`destructive` — skip it explicitly with `--skip-tags destructive` if you
only want to re-converge perms on a box that already has the agent account
(this is also how the layer-3 idempotency fixture tests avoid ever creating
a real OS account).

## Testing

See [`tests/README.md`](tests/README.md) for the 3-layer harness (static /
dry-run / idempotency) and its own honesty label. Run: `ansible/tests/run.sh`.

## Layout

```
ansible/
  site.yml              the single play: acts 1-6 + AC-4 assert
  inventory.ini          localhost, local connection
  group_vars/all.yml      repo path, account name, key path, 8-entry enforcement-path mirror
  README.md               this file
  tests/                   the 3-layer test harness (see tests/README.md)
```
