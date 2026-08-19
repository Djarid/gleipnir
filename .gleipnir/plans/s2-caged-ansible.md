# Plan: S-2 caged-mode host setup as an Ansible playbook

**Stage:** `plan` (full 8-stage **hardened** pipeline — routing confirmed below).
**Planned FROM the converged decision** `../decisions/s2-caged-ansible.md`
(D1 = Ansible; D2 = apply acts 1–5 + install wrapper + AC-4 as a FAILING
assertion; caged ENTRY stays an explicit operator act; D3 = all three test
layers incl. layer-3 fixture-tree idempotency (operator-converged)). This plan does **not**
re-decide the tool or the scope; it inherits the 7 binding constraints of that
record verbatim and cites them by number (BC-1 … BC-7).

**Authoritative inputs (read, confirmed to exist):**
- `../decisions/s2-caged-ansible.md` — the converged decision + BC-1..BC-7.
- `../plans/s2-activation-control-proposal.md` acts (1)–(6) — the OS end-state.
- `../decisions/operating-posture.md` — honesty invariant, key-600 both-mode floor.
- `src/gleipnir/preflight/__main__.py` — exit contract (rc 0 = CLOSED **or**
  uncaged-default; caged-not-closed = rc 1; `--override-ack` = rc 2).
- `src/gleipnir/preflight/boundary.py` — `ENFORCEMENT_PATHS` (lines 168–222, the
  LOCKED 8-path set; `plugins/**` `tolerate_absent=True`); key resolved ONLY from
  `GLEIPNIR_MARKER_KEY_FILE` (line 1030).
- `bin/gleipnir-launch` (act-6 artifact, written+reviewed this session),
  `bin/gleipnir-preflight` (thin shim → `python -m gleipnir.preflight`).
- `.gleipnir/agent-identity.env` — confirmed present: `GLEIPNIR_AGENT_UID=510`,
  `GLEIPNIR_AGENT_GID=510` (single source of truth for uid/gid — BC-6/act-2).

**GOTCHA pre-flight (visible):** goals checked (`manifest.md` → `plan-format.md`
applies; `methodology.md` applies); order = plan-before-code (this plan writes
NO playbook; the code stage owns `ansible/**`); `ansible/` dir does not yet
exist → marked **to-be-created** throughout (never cited as existing).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Tool | **Ansible playbook** | Nix/nix-darwin; shell installer | **Operator-converged** (`s2-caged-ansible.md` D1) — inherited verbatim, not re-decided here. |
| D2 | Automation scope | **Apply acts 1–5 + install wrapper (act 6) + AC-4 as a FAILING assert; caged ENTRY stays operator act** | Full auto-relaunch; setup-only no-assert | **Operator-converged** (`s2-caged-ansible.md` D2) — inherited verbatim. |
| P1 | Playbook home | New **repo-root `ansible/`** dir (to-be-created) | Under `.gleipnir/` | BC-6: it is out-of-framework operator tooling (class of `bin/`) and must never live in the subtree it hardens. |
| P2 | File layout | **Single playbook `site.yml` + `group_vars/all.yml` (2 vars) + a static `inventory.ini` (localhost)**; NO roles, NO generator | Roles/collection scaffold; templated config system | Decision warns against a config system/generator; one host, ~7 tasks — proportionate minimalism. Roles add ceremony with no reuse payoff. |
| P3 | uid/gid source | **Read from `.gleipnir/agent-identity.env`** at play start (`ansible.builtin.slurp` or `include_vars` of the env file parsed to `uid`/`gid`), NOT hardcoded | Hardcode 510 in `group_vars` | BC-6/act-2: `agent-identity.env` is the single source of truth; the playbook and preflight/wrapper must agree. `group_vars/all.yml` holds only the *repo path* + account NAME, never the numeric ids. |
| P4 | Act-1 (macOS user) module | **`command:` (`sysadminctl`/`dscl`) with a `dscl -read` query-then-`when:` idempotency guard** | `ansible.builtin.user` (Darwin) | BC-5: `ansible.builtin.user` on Darwin is unreliable for a non-login service account. No `creates` file exists for a dscl account → guard on a `register`ed query, not `creates`. |
| P5 | Acts 3/4 perms module | **`ansible.builtin.file` with symbolic `mode` (`a+rX` / `a+rX,go-w`) + `recurse: yes`** for the recursive perm passes; `command: chmod` only if byte-parity forces it | `command: chmod -R` everywhere | `file` is idempotent + reports changed-state honestly (drives the two-run idempotency test); symbolic modes match the acts verbatim. One caveat may force a `command` fallback. |
| P6 | Act-5-after-act-4 ordering | **Two ordered tasks in one play; key-600 task placed textually AFTER the recursive `a+rX` task** | Handler-based | BC-2: Ansible's deterministic top-down ordering makes this a plain sequencing requirement; a handler would fire at play end, out of the guaranteed order. |
| P7 | AC-4 assert | **`command: bin/gleipnir-preflight … --mode caged` with task-level `environment: { GLEIPNIR_MARKER_KEY_FILE: … }`, `register` rc, then `ansible.builtin.assert rc == 0`** | `failed_when: rc != 0` on the command alone | BC-4: `environment:` survives `become` (sudo strips the interactive var). A separate `assert` gives an explicit, readable failure message (BC-7: the AC-4 verdict, not playbook success, is the caged signal). |
| D3 | Test fidelity | All three test layers, incl. layer-3 fixture-tree idempotency | Layers 1-2 only; layer 1 only | Operator-converged (../decisions/s2-caged-ansible.md D3) — inherited verbatim, not re-decided. Layer 3 is the only layer that verifies the idempotency Design Intent. |

---

## Architect

**Problem (one sentence).** Replace the hand-run six-shell-act S-2 caged-mode
host setup with a single idempotent, re-runnable, self-verifying Ansible playbook
that applies acts 1–5, installs the act-6 wrapper, and fails its own run unless
the caged boundary genuinely CLOSED — while caged *entry* stays an explicit
operator act.

**User.** The trusted operator (owning principal), running the playbook by hand
under `sudo`/`become` from a checkout of this repo. **Never** an in-framework
agent (BC-6).

**Measurable success criteria.**
1. `ansible-playbook ansible/site.yml --syntax-check` exits 0.
2. `ansible-lint ansible/` reports no errors (warnings triaged).
3. On a correctly-caged box, a full run ends with the AC-4 assert **passing**
   (preflight rc 0 under `--mode caged`), and the whole run reports
   **`changed=0`** on an immediate second run (idempotency — the core Design
   Intent, P-DI below).
4. On a box that is *not* caged (e.g. key mode ≠ 600, or an enforcement path
   agent-writable), the AC-4 assert **fails the run** (non-zero exit) with a
   message naming the preflight verdict — never a false green (BC-7).
5. `--check` (dry-run) reports the tasks it *would* change without mutating the
   host, and names no unexpected changes on an already-set-up box.
6. Numeric uid/gid are read from `.gleipnir/agent-identity.env`, appearing
   **nowhere** as literals in the playbook (P3).

**Constraints (BC-1..BC-7, inherited verbatim; do not re-decide):**
- **BC-1** Six acts authoritative in `../plans/s2-activation-control-proposal.md`;
  the 8 enforcement paths authoritative in `boundary.py` `ENFORCEMENT_PATHS`.
  The playbook **mechanises**, never re-authors, the set. `plugins/` tolerates
  absence.
- **BC-2** Key-600 (act 5) task MUST run *after* the recursive `a+rX` subtree
  task (act 4).
- **BC-3** Key-600 is a permanent floor in BOTH modes; the key task is
  unconditional (never gated on mode/teardown).
- **BC-4** AC-4 assert MUST set `GLEIPNIR_MARKER_KEY_FILE` explicitly on the task
  `environment:` (sudo strips it); assert `rc == 0` under `--mode caged`.
- **BC-5** macOS user creation (act 1) is `command: sysadminctl`/`dscl` +
  query-then-`when:` guard (no `creates` file).
- **BC-6** Out-of-framework OPERATOR tooling (class of `bin/`), run under
  `sudo`/`become`, never by an agent, never under `.gleipnir/`; home = repo-root
  `ansible/`.
- **BC-7** Caged entry stays explicit; the authoritative caged signal is only the
  AC-4 preflight verdict, never playbook success.

---

## Trace

### Artifacts and where they live (source of truth)

All under a **new repo-root `ansible/` directory (to-be-created; does NOT exist
yet)** — the code stage creates these; this plan writes none of them:

| Artifact | Purpose | Source of truth it mechanises |
|---|---|---|
| `ansible/site.yml` | The single play: acts 1–5, wrapper install (act 6), AC-4 assert | acts 1–6 in `s2-activation-control-proposal.md` |
| `ansible/inventory.ini` | Static localhost inventory (`localhost ansible_connection=local`) | n/a (host is always the local mac) |
| `ansible/group_vars/all.yml` | `repo` path, agent account `name` ("gleipniragent"), key path, enforcement-path list. **No numeric uid/gid** (P3). | `s2-activation-control-proposal.md` names; `boundary.py` path list |
| `ansible/README.md` | One-screen "how to run / what it does NOT do (BC-7 caged entry)" | this plan's Execution Workflow |
| `ansible/tests/` | Non-destructive test assets (see Test Strategy) — fixture tree + a `check`/lint invocation | this plan's Stress-test |

**uid/gid resolution (P3).** At play start, a task reads
`{{ repo }}/.gleipnir/agent-identity.env` and sets `agent_uid`/`agent_gid` facts
from its two lines (`slurp` + `set_fact` regex, or `include_vars` with a
`.env`-shaped parse). Every later task references `{{ agent_uid }}`/`{{ agent_gid }}`.
This keeps the playbook, `bin/gleipnir-launch`, and `bin/gleipnir-preflight`
reading the **same** two numbers (currently 510/510).

### Integrations map

- **`bin/gleipnir-preflight`** — invoked by the AC-4 task via `command:` with
  `--agent-uid {{ agent_uid }} --agent-gid {{ agent_gid }} --mode caged` and the
  `environment:` key-file fix (P7/BC-4). The shim execs
  `python -m gleipnir.preflight`; needs `$repo/.venv` present (Link check L-4).
- **`bin/gleipnir-launch`** — act-6 install target: `copy`/`file` sets owner
  `<operator>:staff` mode `0755`. Already written+reviewed; the playbook only
  *installs perms/ownership*, it does not author the file. (If the file already
  matches, `file` reports no change — idempotent.)
- **`.gleipnir/agent-identity.env`** — read-only input (P3); the playbook does
  NOT rewrite it (act-2's *write* is already applied on this box; if absent, a
  guarded `copy` recreates it — see edge case E-6).
- **`boundary.py` `ENFORCEMENT_PATHS`** — the act-4 recursive hardening iterates
  the 8 paths as **data in `group_vars`** that MIRRORS the LOCKED set; the
  playbook does not import Python. A spec-review check (S-6) confirms the mirror
  matches the LOCKED tuple exactly, `plugins/` marked absence-tolerant.

### Edge cases (must be handled by the code stage)

- **E-1 (act-1 idempotency).** Account already exists → the `dscl -read
  /Users/{{ name }} UniqueID` query task `register`s success; the create task is
  `when: user_query is failed` (or rc != 0). Re-run = no change. (P4/BC-5.)
- **E-2 (`plugins/` absence).** `plugins/` may not exist. The act-4 recursive
  task over the enforcement subtree must tolerate its absence (loop item marked
  `tolerate_absent`, `failed_when` excludes "path not found" for that item, OR a
  preceding `stat` gate). Mirrors `EnforcementPath(..., tolerate_absent=True)`
  and the proposal's `|| true`. (BC-1.)
- **E-3 (act-5 after act-4 — the load-bearing order).** If act-5 ran before
  act-4's recurse, the recurse would loosen the key back to group/other-readable.
  Tasks are ordered; a Stress-test assertion (AC-idem below) confirms the key is
  `0600` in the *final* state. (BC-2/BC-3.)
- **E-4 (sudo env-strip).** Without the `environment:` fix the AC-4 preflight
  sees "key absent" and REFUSEs even on a caged box → false failure. The task
  MUST carry `environment: { GLEIPNIR_MARKER_KEY_FILE: "{{ repo }}/.gleipnir/keys/marker.key" }`.
  (BC-4; reproduced live this session per the decision record.)
- **E-5 (operator identity for `chown`).** Acts 3/5/6 `chown` to the *operator*
  (owner), not root. The owner name is not hardcoded — resolve via an
  `ansible.builtin.command: id -un` (or the `ansible_user_id` fact of the
  *invoking* user before `become`), captured once. A wrong owner (root) would
  make the tree unowned by the verifier and break `load_key`-as-owner.
- **E-6 (`agent-identity.env` absent).** If the env file is missing, the P3 read
  fails the run early with a clear message ("run act-2 / this playbook writes it
  guarded"). Chosen: a guarded `copy` recreates it from `name`+chosen uid/gid
  **only if absent** (idempotent, matches proposal act-2), then re-read. Present
  on this box, so normally a no-op.
- **E-7 (key file absent).** If `keys/marker.key` does not exist, act-5's
  `chmod 600` fails and (correctly) the AC-4 assert would REFUSE. The act-5 task
  should fail with an explicit "key file missing — generate it first" message
  rather than a raw chmod error.
- **E-8 (`--check` on a virgin box).** In `--check`, the act-1 query may report
  the user absent and the create task shows "would run"; downstream tasks that
  depend on the account may warn. `--check` is a *preview*, not a guarantee on a
  never-set-up box — documented in README (this is inherent to check-mode with
  `command:` tasks and is acceptable).

---

## Link (validated before building)

- **L-1** `ENFORCEMENT_PATHS` = exactly the 8 in `boundary.py:168–222`
  (`agents/*.md`, `stage-role-map.md`, `decisions/**`, `goals/**`, `keys/**`
  RO_AND_UNREADABLE, `plugins/**` tolerate-absent, `sandbox/**`, `AGENTS.md`).
  **Confirmed by direct read.** The `group_vars` list mirrors this.
- **L-2** Exit contract: rc 0 = CLOSED (or uncaged default); rc 1 = REFUSE
  (incl. caged-requested-but-not-closed); rc 2 = `--override-ack`. Under
  `--mode caged`, **only `Verdict.CLOSED` yields rc 0**. **Confirmed** in
  `__main__.py:147–156`. AC-4 asserts `rc == 0`.
- **L-3** Key resolved ONLY from `GLEIPNIR_MARKER_KEY_FILE`
  (`boundary.py:1030`). **Confirmed.** Justifies the `environment:` fix.
- **L-4** The AC-4 command needs `$repo/.venv/bin/python` (preflight shim,
  `bin/gleipnir-preflight:20`). The code stage/README must note this
  prerequisite; a missing venv is an operator-fixable precondition, not a
  playbook bug.
- **L-5** `.gleipnir/agent-identity.env` present with uid/gid 510. **Confirmed
  by read.** P3 read parses two `KEY=VALUE` lines.
- **L-6** `ansible/` does not exist. **Confirmed** (glob returns nothing). All
  `ansible/**` artifacts are to-be-created by the code stage.
- **L-7** Ansible availability is an operator precondition (brew/pipx), outside
  the stdlib-only enforcement core (decision "New dependency"). Not installed by
  the playbook (out of scope).

---

## Assemble (intended build order)

Test-first (hardened pipeline). Build order the code stage follows:

1. **Author the test assets FIRST** (Stress-test → Test Strategy): the
   syntax-check + `ansible-lint` invocation, and the `--check`/idempotency
   harness against a throwaway fixture tree. These define "correct" before the
   playbook exists (Axiom 1).
2. `ansible/inventory.ini` (localhost, local connection).
3. `ansible/group_vars/all.yml`: `repo`, account `name`, key path, and the
   8-entry `enforcement_paths` list mirroring the LOCKED set (P2/BC-1). **No
   numeric uid/gid** (P3).
4. `ansible/site.yml` — the single play, tasks in this exact order:
   1. **Pre:** resolve owner (E-5); read `agent-identity.env` → `agent_uid`/
      `agent_gid` (P3/E-6 guarded recreate if absent).
   2. **act 1** — user/group: `dscl -read` query (register) → guarded
      `command: sysadminctl`/`dscl` create `when:` absent (P4/BC-5/E-1).
   3. **act 3** — ownership/group layout: operator owns repo; source + `.gleipnir`
      `a+rX`; Tier-0/1/2 dirs `chgrp` agent + `g+w` (`file` symbolic + `recurse`).
   4. **act 4** — recursive enforcement-subtree hardening: loop the
      `enforcement_paths` list, `file` `a+rX,go-w recurse: yes`, `plugins/`
      absence-tolerant (E-2/BC-1).
   5. **act 5** — key `chmod 600` + `chown operator` — **placed AFTER act 4**
      (P6/BC-2); unconditional (BC-3); explicit-missing-key failure (E-7).
   6. **act 6** — install `bin/gleipnir-launch` perms/ownership (`0755`,
      `operator:staff`).
   7. **AC-4 assert** — `command: bin/gleipnir-preflight … --mode caged` with the
      `environment:` key-file fix (P7/BC-4/E-4), `register` rc,
      `ansible.builtin.assert that: "rc == 0"` with a verdict-naming fail message.
5. `ansible/README.md` — run instructions + explicit **out-of-scope / caged
   entry stays operator** note (BC-7).

---

## Stress-test (acceptance checks)

Concrete, checkable — the arbiter of "the playbook is correct":

- **AC-syntax** `ansible-playbook ansible/site.yml -i ansible/inventory.ini
  --syntax-check` → rc 0.
- **AC-lint** `ansible-lint ansible/` → no errors.
- **AC-order** Static assertion (grep/lint rule or a check-mode task-order dump):
  the act-5 key task appears textually AFTER the act-4 recurse task in
  `site.yml` (BC-2). A structural test, not runtime.
- **AC-env** Static assertion: the AC-4 task carries
  `environment: GLEIPNIR_MARKER_KEY_FILE` (BC-4/E-4) — grep the task block.
- **AC-nolit** Static assertion: no literal `510` (or any bare numeric uid/gid)
  appears in `site.yml`/`group_vars` (P3) — grep returns empty.
- **AC-mirror** Static assertion: the `enforcement_paths` list equals the 8
  LOCKED `ENFORCEMENT_PATHS` names, `plugins/` marked absence-tolerant (BC-1) —
  compared against `boundary.py:168–222`.
- **AC-check** `ansible-playbook … --check` against a **throwaway fixture tree**
  (a temp dir mimicking `.gleipnir/` layout with a fake key + fake identity env,
  `repo` pointed at it) reports the tasks without erroring and mutates nothing.
- **AC-idem** Run twice against the same fixture tree (or, on the real box, by
  the operator): the **second** run reports `changed=0` (idempotency — the core
  Design Intent). On the real box, the final key mode is `0600` (AC-order proven
  at runtime).
- **AC-4-pass** On a correctly-caged real box (operator-run): the AC-4 assert
  passes (preflight rc 0). — Operator-observed, not CI (destructive).
- **AC-4-fail** Deliberately break one enforcement perm (e.g. key mode 644) on a
  fixture/real box → the run FAILS at the AC-4 assert with a message naming the
  REFUSE verdict (BC-7). This is the "no false green" proof.

### TEST STRATEGY (most important — this is test-first, hardened)

**What "the playbook is correct" means, and how it is verified WITHOUT creating
uid 510 or chowning a live tree in CI:**

The destructive acts (uid creation, chown/chmod of the real repo) **cannot** run
in CI. So correctness is verified in **three non-destructive layers**,
proportionate to a one-host ~7-task playbook (molecule is **rejected as
overkill** — it exists for multi-platform role matrices; there is one role-less
play and one host):

1. **Static / syntax layer (cheap, always in CI):** `--syntax-check` (AC-syntax)
   + `ansible-lint` (AC-lint) + the grep-based structural assertions
   (AC-order, AC-env, AC-nolit, AC-mirror). These catch the *load-bearing*
   ordering/env/no-literal/mirror invariants **without executing any act** —
   they are exactly the constraints BC-1/BC-2/BC-4 encode, checked as text.
2. **Dry-run / check-mode layer (fixture tree):** point `repo` at a throwaway
   temp dir that mimics `.gleipnir/` (fake `marker.key`, fake
   `agent-identity.env`, empty enforcement dirs incl. an absent `plugins/` to
   exercise E-2). Run `--check` (AC-check) to prove tasks resolve and mutate
   nothing.
3. **Idempotency layer (fixture tree):** run the playbook twice against the
   fixture tree **with the destructive act-1 user-create task tag-excluded**
   (e.g. `--skip-tags user_create`, since uid creation cannot run in CI), and
   assert the **second** run reports `changed=0` (AC-idem). This proves the perm
   tasks (acts 3/4/5/6) converge — the DRY/Design-Intent core — using real
   `chmod` on a fake tree the CI user owns. The AC-4 assert on the fixture tree
   proves the **fail path** (AC-4-fail): a deliberately-wrong key mode makes the
   preflight REFUSE and fails the run — the "no false green" arbiter.

The genuine **caged CLOSED pass (AC-4-pass)** is only assertable on the real box
by the operator (creating uid 510, real perms). That is expected and documented:
CI proves *structure + idempotency + the fail path*; the operator proves *the
real close*. **All three test layers, incl. layer-3 fixture-tree idempotency
(real `chmod` on a disposable fake tree, run twice, `changed=0` on the second
run), are REQUIRED** — this is operator-converged as D3
(`../decisions/s2-caged-ansible.md` D3): layers-1-2-only and layer-1-only are
REJECTED. Layer 3 is the only layer that actually verifies the idempotency
Design Intent (`--check` alone asserts run-twice-equals-zero-changes only in
theory); the fixture-tree harness maintenance cost is accepted as the price of
genuinely proving idempotency.

---

## Execution Workflow (for the implementing/code agent)

1. **You build under `ansible/` ONLY** (to-be-created). You do **not** touch
   `.gleipnir/**`, `src/**`, `bin/**` (act-6 wrapper already exists — you install
   its perms via the play, you do NOT rewrite it). You do NOT run the playbook
   against the real host.
2. **Test-first:** author `ansible/tests/` (the layer-1 static asserts + the
   layer-2/3 fixture-tree harness) BEFORE `site.yml`, per Assemble step 1.
3. Build in Assemble order 2→5. Every perm task uses `ansible.builtin.file` with
   symbolic modes + `recurse` where recursive (P5); act-1 is the guarded
   `command:` (P4). Keep act-5 textually after act-4 (P6/BC-2).
4. **Do NOT hardcode uid/gid** — read from `agent-identity.env` (P3). **Do NOT**
   add a caged-entry/relaunch step (BC-7/D2). **Do NOT** install Ansible from the
   playbook (out of scope).
5. The AC-4 task MUST carry the `environment: GLEIPNIR_MARKER_KEY_FILE` fix
   (BC-4/E-4) and assert `rc == 0` under `--mode caged` (L-2).
6. Verify against the Stress-test ACs. Layer-1/2/3 tests are the CI arbiter;
   AC-4-pass is operator-run and out of CI.
7. **Out of scope (do not build):** caged entry/relaunch (stays operator act,
   BC-7/D2); the go-caged runbook Step-2/3/4 operational surface; installing
   Ansible itself; rewriting `bin/gleipnir-launch` or the preflight; editing
   `agent-identity.env` content beyond the guarded absent-recreate (E-6).

---

## Design Principles (Cognition Gate 1 — case (ii): executable-but-non-OOP)

Routing: `P ∩ X ≠ ∅` (a standalone `*.yml` playbook — Axis-1 disqualifier `X`),
and the touched `X`-member (a YAML playbook) has **no object/function/module
structure**. → **case (ii)**: DRY + Design Intent required; SOLID/SRP attested
`N/A`.

- **SOLID analysis — `N/A — no object/function structure`.** An Ansible playbook
  is a declarative task list; there are no classes, functions, interfaces, or
  subtypes for Single-Responsibility(class)/Open-Closed/Liskov/Interface-
  Segregation/Dependency-Inversion to analyse.
- **Class/module SRP — `N/A — no object/function structure`** (same reason).
- **DRY analysis.** (1) The numeric uid/gid exist in exactly ONE place —
  `.gleipnir/agent-identity.env` — and are READ, never duplicated, by the
  playbook (P3): the playbook, `bin/gleipnir-launch`, and the preflight all
  consume the same source, so a change to the ids never needs editing the
  playbook. (2) The 8 enforcement paths are declared ONCE as a `group_vars` list
  and iterated (act-4 loop), not repeated per-path (BC-1). (3) The repo path and
  account name are single `group_vars` references, not repeated literals. No
  logic is duplicated across tasks; symbolic `mode` strings match the acts
  verbatim rather than being re-derived.
- **Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**
  > **P-DI:** *Running the playbook a second time against an already-correctly-
  > caged host makes ZERO changes (`changed=0`) AND still ends with the AC-4
  > assert passing; and running it against a host whose enforcement perms have
  > drifted (e.g. key mode ≠ 600, or an enforcement path became agent-writable)
  > FAILS the run at the AC-4 assert rather than reporting success.*

  This is falsifiable: a reviewer can point to any task that is non-idempotent
  (reports `changed` on a converged host — e.g. an unguarded act-1 create, or a
  `command: chmod` that always reports changed), or any path where a drifted
  perm still lets the run report success, as a **violation** of P-DI. It names a
  concrete convergence-and-verification boundary the implementation must honour,
  not a generic "works well" aspiration. The honour-check at the `quality` stage
  verifies the applied playbook actually meets P-DI (idempotent + fails-on-drift).

---

## Touched-path set P (routing confirmation)

`P = { ansible/site.yml, ansible/inventory.ini, ansible/group_vars/all.yml,
ansible/README.md, ansible/tests/** }` — all **to-be-created** under a new
repo-root `ansible/` dir.

- **Axis-1 eligibility:** `P` contains standalone `**/*.yml` files → in
  disqualifier set `X` → **full 8-stage hardened pipeline** (light/prose track
  unavailable). Confirmed against `../decisions/s2-caged-ansible.md` "Routing".
- **Cognition Gate-1:** `P ∩ X ≠ ∅`, no OOP structure → **case (ii)** (above).
- Note: nothing in `P` is under `.gleipnir/**`, `src/**`, `bin/**`, or the
  enforcement-path set `E` — the playbook *acts on* those paths at runtime but
  the plan's artifacts live entirely in the new `ansible/` tree (BC-6).
