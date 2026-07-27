# Plan: S-2 / G-1 Closure — First Slice (relocate-and-deny hybrid + fail-closed preflight)

**Stage:** plan (authored by `gleipnir-plan`, Tier-0 artifact under `.gleipnir/plans/`).
**Status of the thing being planned:** authored, activation-partial. This slice
*begins making G-1 real* for the host-run opencode agent by (a) taking the agent uid
off the enforcement subtree, (b) making that subtree OS-read-only (and the key
OS-unreadable) to the agent uid within the single `OPENCODE_CONFIG_DIR`, and (c) adding
an out-of-framework, fail-closed launch-wrapper preflight that *behaviourally probes* the
boundary. It does **not** claim terminal G-1 closure: the OS-perms floor is an honest
first floor, **not** the container terminal boundary (B-literal) — that is deferred.

> **Provenance (operator-decided via the orchestrator — LOCKED; captured, not re-decided).**
> D1–D5 and the uid-separation CRUX below are the converged decision. D-4 in
> `.gleipnir/decisions/substrate-design-pass.md` already resolves the substrate to
> **B core / A where containers are unavailable / C hardening**, and the config load
> path to **mount-side / never tree-side**. The Part 0 escape-hatch scope clause
> (`gleipnir_specification_v0_3_12.md`) is binding. The enforcement core is
> **Python + stdlib-only** (`.gleipnir/decisions/runtime-and-deps.md`). This plan builds
> **within** those decisions; it does not reopen them. The one thing this plan surfaces
> back to the operator is **design question (a)** in the Architect section — the honest
> dev-box posture — which is a Tier-3 decision this role cannot itself make.

---

## GOTCHA pre-flight (visible, per methodology goal)

- **Goals checked first** (`.gleipnir/goals/manifest.md`): the applicable goal is
  `plan-format.md` (this file follows its 6 sections) and `methodology.md`
  (ATLAS/GOTCHA-ahead-of-planning — satisfied: this plan IS the Architect/Trace output).
  No pipeline-sequencing goal is authored, correctly (G-5 owns sequencing).
- **Plan-before-code order** is correct: no code is written by this role; only this
  plan file under `.gleipnir/plans/**` (the only path `gleipnir-plan` may write).
- **Layer mapping (GOTCHA):** the probe/decision *logic* is layer-3 Tools (deterministic
  code, unit-tested); the *invocation* is layer-2 Orchestration but here it is the
  **out-of-framework** operator/launch-wrapper act (not the G-5 engine, and never an
  in-framework agent) — this is the terminal-closure invariant: a guard whose activation
  is validated by the population it guards is the G-3 forgeable-evidence failure applied
  to activation.
- **Gaps named:** `.gleipnir/plugins/sequence-gate.ts` **exists today** as
  enforcement-bearing guard code and is currently agent-writable (a live G-1 exposure —
  see Trace), and there is no separate OS uid on a single-uid dev box. Both are handled
  honestly below (buildable-now logic vs operator-environment setup), not papered over.

---

## A — Architect

**Problem (one sentence).** The host-run opencode agent loads its enforcement config
(agent permission maps, `stage-role-map.md`, the G-3 key, and future plugins) from a
tree-side `OPENCODE_CONFIG_DIR=.gleipnir` that the agent's own uid can write and read —
a G-1 fail — so an in-framework agent could rewrite the very permission maps and key
that are meant to cage it.

**User.**
- **Primary:** the *operator / launch wrapper* (the owning principal, outside the
  framework), who runs the preflight before starting an opencode session and needs a
  fail-closed, honest verdict on whether the boundary actually holds.
- **Secondary:** every in-framework roster agent, whose caging this boundary makes real;
  and the framework maintainer, who needs the probe logic unit-tested now even where the
  environment (separate uid, `plugins/`) does not yet exist.
- **Explicitly NOT a user / NOT in scope:** the operator's built-in `/plan` and `/build`
  escape-hatch agents (Part 0). The preflight neither checks, restricts, nor refuses them.

**Measurable success.**
1. The preflight **refuses to launch** (fail-closed, nonzero exit) when *any* enforcement
   file is writable by the agent uid, when the key is readable by the agent uid, or when
   any enforcement path resolves (through symlinks) to a writable location.
2. The preflight **passes** (allows launch) *only* when every enforcement file is
   unwritable by the agent uid AND the key is unreadable by the agent uid AND no
   enforcement path resolves outside the read-only subtree.
3. On a **single-uid dev box with no real separation**, the write-probe (agent uid ==
   owning uid) reports **WRITABLE → NOT closed → refuse**. This is the intended honest
   v0.1 behaviour (per the CRUX): no false "G-1 closed" claim is ever emitted. See
   design question (a) for the operator-acknowledged posture that keeps a dev box usable
   without lying.
4. Any probe error, ambiguity, or unexpected condition is treated as **NOT closed
   (refuse)** — never as "assume fine".
5. The probe/decision **logic** is stdlib-only Python, fully unit-testable now with
   `tmp_path` + real `chmod`, with no dependence on a real second uid, container, or
   `plugins/` existing.
6. The full existing suite (**291 tests green** across the current `tests/` set) stays
   green; this slice adds tests and a new module, and touches no existing enforcement
   semantics.

**Constraints.**
- **Must NOT cage the operator escape hatch.** The preflight's subject set is the
  in-framework roster only; built-in `/plan` `/build` are never enumerated, checked, or
  restricted (Part 0 / spec v0.3.12 lines 35–37, 113, 134).
- **stdlib-only Python** for all logic (`runtime-and-deps.md`); mirror the "probe, don't
  assume" discipline of `src/gleipnir/sandbox/runtime.py` (structured facts, fail-closed,
  no prose-parsing, thin subprocess edges kept out of the pure core).
- **Do not break tree-side authoring** of `goals/`, `plans/`, and skill *bodies* — those
  stay agent-writable (D2). Only the enforcement subset goes read-only.
- **No marker code change.** The key path stays env-pointed via the existing
  `GLEIPNIR_MARKER_KEY_FILE` (`src/gleipnir/verify/marker.py`); D3 changes *where* the
  key lives and its OS perms, not the code that reads it.
- **The invocation must be out-of-framework** — not a script the agent can invoke, edit,
  or run as its own uid (chicken-and-egg / G-3 forgeable-activation). See Trace §Preflight.
- **Single coherent config root.** One `OPENCODE_CONFIG_DIR` with per-subtree OS perms;
  no opencode change expected (D2).

**REAL design questions.**

- **(a) MATERIAL — surfaced to operator, NOT decided here.** On a single-uid dev box the
  write-probe (same uid) correctly reports WRITABLE → preflight fails closed → the agent
  cannot launch. That is honest but *unusable* on a dev box with no real uid separation.
  The line between **honest-refuse** and **usable** must be an operator decision, because
  it is exactly the kind of durable safety-posture tradeoff Part 0 reserves to the
  operator. The **recommended** shape (for the operator to ratify or reject) is an
  **operator-acknowledged override that is a Part-0 OPERATOR action, never an
  agent-reachable toggle**: a file/flag the *launch wrapper* consults (living outside the
  agent-writable surface, in the same trust class as the wrapper itself) whose presence
  makes the preflight emit **"running WITHOUT real uid separation — G-1 NOT closed
  (dev-mode)"** and proceed, *recording* that honest label rather than silently passing.
  The override must never flip the verdict to "closed"; it only converts refuse→proceed
  while stamping the un-closed truth. This keeps the dev box usable without a false
  closure claim. **This plan builds the fail-closed path and the honest-label hook;
  whether the override exists at all, and where its file lives, is a Tier-3 decision for
  `.gleipnir/decisions/s2-g1-closure.md` — flagged below, not resolved here.**

- **(b) BOUNDED — decided-and-justified.** Given a separate uid and `plugins/` may not
  exist yet, the buildable+testable-now surface is precisely the **pure probe/decision
  logic + the fail-closed decision function + tests** that simulate both writable and
  denied via `tmp_path` files with real `chmod` (and unreadable via mode `0o000`), plus
  the symlink-resolution check via real symlinks in `tmp_path`. What is **operator /
  environment setup** (out of this slice's code): provisioning the actual second OS uid,
  performing the real `chown`/`chmod` on the live `.gleipnir/` subtree, placing the real
  key outside agent-read, and installing the launch wrapper on the host. Justification:
  the logic is where correctness lives and is deterministically testable; the environment
  acts are host state the operator owns (same trust class as S-3 preflight / closure), and
  binding them into agent-run code would reintroduce the chicken-and-egg. The probe's thin
  subprocess/uid-drop edge is written but its *real* uid-drop path only executes when a
  genuine second uid exists; on same-uid it takes the honest "same uid → WRITABLE" path.
  The uid-drop edge **independently verifies the drop took effect (euid read-back) before
  the write/read is attempted or interpreted** — an unverifiable drop is its own error
  case, never folded into the write signal (see Trace §probe contract, B1).

---

## T — Trace

### Where the enforcement subset lives, and the exact path set

Single config root `OPENCODE_CONFIG_DIR=.gleipnir` (unchanged, `../opencode.jsonc`),
split per-subtree by OS perms (D2). The **enforcement subset** (OS-read-only to the agent
uid; key additionally OS-unreadable):

| Enforcement path | Perm required vs agent uid | Why (enforcement-bearing) | Notes |
|---|---|---|---|
| `.gleipnir/agents/*.md` (frontmatter permission maps) | unwritable | the caging permission maps themselves (G-1) | 8 files today (`git-ops`, `gleipnir-*`, `orchestrator`, `quality-reviewer`, `project-mgr`, `notify`) |
| `.gleipnir/stage-role-map.md` | unwritable | G-5 engine's state→role binding | single file |
| `.gleipnir/decisions/**` | unwritable | Tier-3 POLICY; the **LOCKED D1–D5 this plan operationalizes live here** — an agent that could rewrite `s2-g1-closure.md` could rewrite the boundary's own definition (G-1) | operator-authored only per the layout doc tier table |
| `.gleipnir/goals/**` | unwritable | Tier-3 POLICY per `gleipnir-layout-and-memory-model.md` (process-as-data, K-1); goal text is enforcement-bearing (drives planning/methodology) | see reconciliation note below — goals are Tier-3 even though `plans/` (Tier-0) is writable |
| `.gleipnir/keys/**` (the HMAC key file) | **unreadable AND unwritable** | G-3.1 key must not be forgeable — read is the threat (D3) | key file itself is `.gitignore`'d; env-pointed by `GLEIPNIR_MARKER_KEY_FILE` |
| `.gleipnir/keys/**` (rate table, weakening toggles, approved digests) | unwritable (read OK) | tamper of G-4d economics / weakening / integrity digests (D3) | rate table/toggles/digests: unwritable suffices |
| `.gleipnir/plugins/**` | unwritable | guard code / hooks (G-1) | **EXISTS TODAY** — `.gleipnir/plugins/sequence-gate.ts` is present and currently agent-writable (a live G-1 exposure), so it is a real path in this run's set, not hypothetical; a present-but-writable plugin ⇒ refuse |
| `.gleipnir/skills/**/SKILL.md` (bodies) | writable (NOT in subset) | methodology bodies are NOT enforcement-bearing — see reconciliation | per substrate-design-pass split table: skill *content* is tree-side OK |

**Reconciliation with the actual tier table** (`gleipnir-layout-and-memory-model.md` §"The
tiers"): Tier-3 POLICY is the full set `agents/ skills/ goals/ stage-role-map.md
decisions/ keys/`. The enforcement subset above takes ALL of Tier-3 as OS-read-only **with
one deliberate, justified narrowing**: `skills/` **bodies** (the `SKILL.md` methodology
prose) stay writable per the substrate-design-pass split table, because methodology text is
not enforcement-bearing — it cannot grant capability or flip a verdict. `goals/`, by
contrast, IS kept read-only: it is Tier-3 process-as-data that steers planning/methodology,
and unlike `plans/` (Tier-0, disposable) it is not disposable. This is the one place the
enforcement-path set differs from a naive "all of Tier-3": skill bodies out, everything else
Tier-3 in. **`AGENTS.md`** (the framework instruction file at `.gleipnir/AGENTS.md`) is
itself POLICY-class and enforcement-adjacent; it is added to the OS-read-only subset
(unwritable to the agent uid) — an agent that could rewrite its own governing instructions
defeats G-1 in spirit even if no permission map changed.

**Explicitly NOT in the enforcement subset (stay agent-writable — D2), each justified:**
`.gleipnir/plans/` (Tier-0, disposable), `.gleipnir/skills/` **bodies** (methodology prose,
not enforcement-bearing — see reconciliation), `.gleipnir/memory/` and `.gleipnir/lessons/`
(Tier-2, guarded by the review-gated write pipeline + G-3.1 digests, not by OS-ro here),
`.gleipnir/logs/` (Tier-1, framework-written), `.gleipnir/var/`. Making the writable ones
read-only would break tree-side authoring (a constraint violation); the Tier-2 paths are out
of *this* slice's OS-ro mechanism by design (a different, later guard owns them).

The **canonical enforcement-path set is data, in code** (an ordered, explicit list in the
new module — mirroring the trust-tier "path property encoded as an enum, not inferred from
content" discipline from `gleipnir-layout-and-memory-model.md`). It is *not* inferred by
globbing writability; it is the named set above, so a newly-added enforcement file that
someone forgot to list is caught by review, not silently trusted.

### The concrete mechanism (probe, don't assume)

New module: **`src/gleipnir/preflight/boundary.py`** (stdlib-only). Pure decision core +
a thin edge, exactly the `sandbox/runtime.py` shape:

- **Pure core (unit-testable now):**
  - `ENFORCEMENT_PATHS` — the named path set (relative to the config root), with a
    per-path required posture (`RO` vs `RO_AND_UNREADABLE`).
  - `resolve_final_target(path) -> Path` — fully resolves symlinks (`Path.resolve()` /
    `os.path.realpath`) so a symlink from a read-only enforcement path *into* a writable
    location is detected. The check is on the **resolved** target's writability.
  - `classify_probe_result(write_ok, read_ok, resolved_escapes, posture) -> ProbeVerdict`
    — pure mapping to `CLOSED` / `NOT_CLOSED(reason)`. Fail-closed default: any
    unexpected combination → `NOT_CLOSED`.
  - `decide(probe_results, override_ack) -> PreflightDecision` — aggregates all path
    verdicts. `REFUSE` unless *every* path is `CLOSED`. If any path is `NOT_CLOSED` and
    `override_ack` is present (the Part-0 operator override, question (a)), emit
    `PROCEED_UNCLOSED` with the honest **"G-1 NOT closed (dev-mode)"** label — never
    `CLOSED`. No override → `REFUSE`.
- **Thin edge (faked in tests, real at launch):**
  - **B1 — the uid-drop-and-verify contract (the CRUX depends on this).** When a genuine
    second uid exists, the write/read probe runs in a **forked child** that drops privilege
    to the target agent uid. The drop and the write are **separate, separately-classified
    steps**, NEVER wrapped in one broad `except PermissionError`:
    1. **Drop:** call `os.setgid(agent_gid)` / `os.setuid(agent_uid)` (setgid before setuid;
       drop supplementary groups). A `PermissionError`/`OSError` from the *drop itself* ⇒
       **DROP_FAILED**, an error case, → `REFUSE`. It is **never** interpreted as the file
       being read-only.
    2. **Read-back verify:** *independently* re-read the identity — `os.geteuid()` **and**
       `os.getuid()` must **both** equal `agent_uid` (and gid likewise). If the read-back
       does not confirm we are actually running as the agent uid (drop silently ineffective,
       partial drop, still-root, etc.) ⇒ **DROP_UNVERIFIED**, an error case, → **REFUSE**.
       The euid/uid read-back is the gate: nothing below runs until it confirms.
    3. **Only after a verified drop**, attempt the real write/read. *Now* a
       `PermissionError` from the write may be read as **CLOSED** for that path (and a
       successful write as `NOT_CLOSED`). Because steps 1–2 are separate error cases, a
       failed-or-unverifiable drop can never masquerade as a safely-read-only file (the
       false-CLOSED this closes).
    The child reports a **discriminated result** — `DROP_FAILED` / `DROP_UNVERIFIED` /
    `WRITE_DENIED(CLOSED)` / `WRITE_OK(NOT_CLOSED)` / `PROBE_ERROR` — to the parent (via exit
    code + payload); the parent maps only `WRITE_DENIED` to `CLOSED` and every other outcome
    to `REFUSE`.
  - `probe_write_as_agent(path, agent_uid)` — performs the forked drop-verify-write above
    (create+unlink a temp entry, or open-for-append then discard). On a single-uid box no
    drop occurs (target uid == current uid, read-back trivially confirms) and the write is
    attempted as the only uid, succeeding, correctly reporting **WRITABLE → NOT closed**.
  - `probe_read_key_as_agent(key_path, agent_uid)` — same forked drop-verify sequence, then
    attempts a **real** read of the key bytes as the (verified) agent uid; success → key
    readable → NOT closed.
  - **Do NOT use `os.access()` for the verdict, and it may NEVER gate whether the real probe
    runs.** `os.access` uses the *real* uid/gid and has documented effective-uid pitfalls and
    root-always-true behaviour; the verdict must come from an *actually attempted* write/read
    after a verified drop (fail-closed on `PermissionError` == good, success == NOT closed).
    `os.access` may at most affect **ordering or logging** — it must never short-circuit or
    skip the real attempted-write/read, which runs **unconditionally**. An implementer must
    not read an `os.access` "not writable" hint as licence to omit the real probe.

### The preflight as an out-of-framework wrapper (chicken-and-egg, answered honestly)

The **logic** lives in `src/gleipnir/preflight/boundary.py` and is unit-tested — that is
fine and desirable (it is data + pure functions; reading it grants no power).

The **invocation** must be out of the agent's reach, or a guard would be validated by the
population it guards (spec: "a guard whose closure is validated by the in-framework
population it guards is the G-3 forgeable-evidence failure applied to activation"). The
answer, concrete:

- The invocation entrypoint is a **launch wrapper run by the owning principal BEFORE the
  opencode session** — e.g. `bin/gleipnir-preflight` (thin shim, same pattern as
  `bin/gleipnir-sandbox`) that the *operator* runs, or a wrapper that lives **outside the
  repo entirely** (operator's shell profile / a system launch script). It runs as the
  owning uid, forks to drop to the agent uid for the write/read probes, aggregates, and
  **exits nonzero (refuse) unless the boundary holds**.
- **Why this is out of agent reach even though the shim is in `bin/`:** the agent's
  capability map grants `bin/gleipnir-sandbox test|lint` by *exact match* only; it does
  **not** grant `bin/gleipnir-preflight`, and (critically) the agent runs as the agent
  uid, which by the CRUX cannot write `bin/` or the wrapper. More importantly the
  *decision that matters* — dropping to the agent uid and refusing to launch — is taken by
  the **owning principal before the session exists**; the agent cannot invoke it *as the
  owning principal* no matter what, because uid separation is exactly what the CRUX
  establishes. On a single-uid box where the agent *could* run it, the honest answer is:
  there is no real boundary yet (preflight would say NOT closed), so nothing is being
  falsely protected — the dev-mode label is doing its job.
- **It must NOT be an agent tool.** The agent permission maps grant no `bin/gleipnir-
  preflight` and no `sh`/`bash` to reach it; the wrapper is operator-invoked, in the same
  trust class as S-3 preflight and CI-on-release.

### The three behavioural probes (precise)

For each enforcement path, and for the key specifically:

1. **Write-probe as agent uid → must FAIL (raise `PermissionError`).**
   **Precondition (B1):** the privilege drop to the agent uid must have been performed AND
   verified by euid/uid read-back (`os.geteuid()`/`os.getuid()` both == `agent_uid`) before
   any write is attempted or interpreted; a failed or unverifiable drop ⇒ REFUSE, never
   CLOSED. *After* a verified drop, attempt a real write to each enforcement file/dir. Success
   (write landed) ⇒ that path is **NOT closed** ⇒ refuse. Only a real `PermissionError` from
   the write, following a verified drop, counts as closed for that path. (This is the probe
   that fails-closed on a single-uid box.)
2. **Read-probe of the key as agent uid → must FAIL (raise `PermissionError`).**
   Same verified-drop precondition (B1) as the write-probe. *After* a verified drop, attempt
   to read the key bytes at `GLEIPNIR_MARKER_KEY_FILE` *as the agent uid*. Success (bytes
   returned) ⇒ key is **readable** ⇒ NOT closed ⇒ refuse. D3 requires the key be *unreadable*,
   not merely unwritable.
3. **Symlink-resolution check.**
   For each enforcement path, fully resolve symlinks (`realpath`) and confirm the resolved
   target is (i) still inside the intended read-only subtree and (ii) unwritable by the
   agent uid. A symlink from a read-only enforcement path into a writable location ⇒ NOT
   closed ⇒ refuse. (Closes the "point the ro name at a writable file" bypass.)

Aggregate rule: **CLOSED only if all three pass for all paths; any NOT_CLOSED or any probe
error ⇒ REFUSE** (or `PROCEED_UNCLOSED` with honest label iff the Part-0 override is
present — question (a)).

### Edge cases

- `plugins/` present (it is — `.gleipnir/plugins/sequence-gate.ts` exists today) → probed
  like any enforcement path; present-but-writable ⇒ refuse. `ENFORCEMENT_PATHS` also tolerates
  a *future*-absent case (dir emptied) as not-a-failure-for-absence, but the live reality this
  run is present-and-must-be-ro.
- **Key file entirely ABSENT** → fail-closed (`KeyUnavailable`-class) ⇒ refuse; a boundary
  with no key is not a closed boundary.
- **Key file present but EMPTY (zero bytes)** → fail-closed (`KeyUnavailable`-class) ⇒ refuse;
  a zero-byte key is not a usable key. (Distinct from absent, but same fail-closed verdict.)
- **Privilege drop failed or unverifiable (B1)** → `DROP_FAILED`/`DROP_UNVERIFIED` error case
  ⇒ refuse; NEVER read as read-only.
- Same-uid box → write-probe succeeds ⇒ NOT closed ⇒ refuse (or dev-mode proceed with
  honest label if override present).
- Running as root → `os.access` would lie (always writable/readable); the real
  attempted-write/read still succeeds as root ⇒ NOT closed ⇒ refuse. Correct: root is not
  a closed boundary.
- Symlink loop / unresolvable path → treat as error ⇒ refuse.
- Enforcement path missing entirely (e.g. `stage-role-map.md` deleted) → refuse (a missing
  guard file is not a closed guard).
- **TOCTOU between probe and session launch (named deferral, low-risk):** the preflight
  probes the boundary, then the operator launches the session; a change to the perms in that
  window is a time-of-check/time-of-use gap. It is **low-risk here and deferred**: the guarded
  *in-framework* agent process does not exist until *after* a successful launch, so there is no
  in-framework population able to race the window. Terminal closure (S-2 mount + S-3 preflight
  bound to session start) removes the gap; this slice names it rather than leaving it silent.

---

## L — Link (validated before building)

- **Marker key contract** (`src/gleipnir/verify/marker.py`): key path is env-pointed via
  `GLEIPNIR_MARKER_KEY_FILE`; `load_key` already fail-closes on unreadable/empty. This
  slice reuses that env var and does not modify marker code. **Validated.**
- **Probe-don't-assume pattern** (`src/gleipnir/sandbox/runtime.py`): pure core +
  thin subprocess/OS edge, fail-closed everywhere, structured facts not prose-parsing.
  This slice mirrors it. **Validated.**
- **Escape-hatch scope** (spec v0.3.12 Part 0, lines 35–37, 113, 134; substrate-design-pass
  §"Terminal closure" pt 3): preflight subject is in-framework roster only; `/plan`
  `/build` are never enumerated. **Validated as a hard constraint.**
- **stdlib-only** (`runtime-and-deps.md`): confirmed the whole `src/gleipnir/` core is
  stdlib-only today; new module must stay so (`os`, `pathlib`, `stat`, no third-party).
  **Validated.**
- **Existing test baseline**: `tests/` currently green at the referenced 291-count; the
  new module + tests must not perturb it. **To confirm at build via `bin/gleipnir-sandbox
  test`.**
- **`os.access` pitfall**: confirmed via Python docs semantics — real-uid based, root
  special-cased; therefore the *decision* uses attempted real write/read, not `os.access`.
  **Validated (design constraint recorded).**
- **Guard-on-guards trust dependency (named, not silent):** `src/gleipnir/preflight/
  boundary.py` is itself **agent-writable until merge** (it is `src/` code, not under the
  Tier-3 OS-ro set), so its integrity *as* the guard-on-guards rests entirely on the
  `quality`/`git` review gate catching any tamper before it lands — a real, named trust
  dependency, not an assumed one. **Validated as a recorded dependency.**
- **`plugins/` is a live current exposure:** `.gleipnir/plugins/sequence-gate.ts` exists
  today and is agent-writable — it is enforcement-bearing guard code and therefore in the
  OS-ro subset now, not a hypothetical-future path. **Validated (corrected from the earlier
  "does not exist yet" error).**
- **Unvalidated / operator-environment (explicitly out of this slice's build):** existence
  of a real second OS uid; live `chown`/`chmod` of `.gleipnir/`; host install of the
  launch wrapper. These are operator acts, flagged in Assemble as environment steps.

---

## As — Assemble (test-first build order)

**B2 — test-location strategy (which tests run WHERE, and why "291 + new green
in-sandbox" is honestly achievable).** The S-2 sandbox container runs as **root** (the
`Containerfile` has no `USER`; `build_run_argv` passes no `--user`), and root bypasses
permission bits — so a `chmod 0o444` file is still writable to root, making a chmod-based
"denied → CLOSED" test and a "root → NOT_CLOSED" test *observationally identical* under
root. The repo already documents exactly this trap (`tests/test_bus_emit.py:111` avoids
chmod-based tests as "not portable across platforms/UIDs"). We therefore split the suite,
using **strategy (a)+(b) together**:

- **In-sandbox suite (runs under root in the container; MUST stay green there):** the
  **pure decision logic** — `resolve_final_target`, `classify_probe_result`, `decide`,
  aggregation, the discriminated drop/probe result mapping — tested with the thin probe
  edge **mocked / injected** (feed `ProbeVerdict`s and drop-results directly; do not rely
  on real perms). This exercises the denied-case *decision* (a `NOT_CLOSED` probe result →
  `REFUSE`; an all-`CLOSED` set → `PROCEED`) without any dependence on chmod bits taking
  effect under root. The probe edge is **injectable** precisely so this is possible.
- **Host-only suite (real perms, real attempted write/read; marked `@pytest.mark.hostonly`
  and SKIPPED when running as root / in the sandbox):** the **real-chmod behavioural probe**
  tests — real `chmod 0o444`/`0o000` files under `tmp_path`, real attempted write/read,
  real symlink resolution, and (where a second uid is available) the real drop-and-verify.
  These are the tests that genuinely exercise "denied → CLOSED" against actual OS
  enforcement; they are honestly meaningful only off-root, so they run on the host CI/dev
  runner (non-root uid), not in the root sandbox.

The denied case is thus **genuinely exercised** (host-only, real perms) AND the decision
logic is **fully covered in-sandbox** (mocked edge). We do **not** claim a chmod-based
denied test passes under root — those are skipped there by the `hostonly` marker.

1. **Write tests first** — split across two files:
   **`tests/test_preflight_decision.py`** (in-sandbox, mocked edge, no real perms) and
   **`tests/test_preflight_probe_hostonly.py`** (`@pytest.mark.hostonly`, real perms,
   skipped under root/sandbox). All use stdlib + `pytest` + `tmp_path`; neither needs a
   container, and the host-only file needs a real non-root uid (a second uid only for the
   real-drop cases, which self-skip when absent):
   - **[decision, in-sandbox] denied case (mocked):** inject probe results = all `CLOSED`
     + key unreadable → `decide` → `PROCEED`. No chmod relied upon.
   - **[decision, in-sandbox] writable case (mocked):** inject a `NOT_CLOSED` write-probe
     result → `decide` → `REFUSE`.
   - **[decision, in-sandbox] key-readable case (mocked):** inject a `NOT_CLOSED` key
     read-probe result → `REFUSE`.
   - **[probe, host-only] real denied case:** `chmod 0o444` (ro) files + key `chmod 0o000`
     (unreadable) → real write/read probe reports `CLOSED` → `decide` → `PROCEED`.
   - **[probe, host-only] real writable case:** enforcement file `chmod 0o644` → real
     write-probe succeeds → `NOT_CLOSED` → `REFUSE`.
   - **[probe, host-only] real key-readable case:** key `chmod 0o444` → real read succeeds
     → `NOT_CLOSED` → `REFUSE`.
   - **[probe, host-only] symlink case:** an enforcement path is a real symlink into a
     writable `tmp_path` dir → real resolution detects escape → `REFUSE`. (Symlink
     *resolution* logic — `resolve_final_target` on constructed paths — is ALSO tested
     in-sandbox without needing real perms.)
   - **[decision, in-sandbox] probe-error/ambiguity case:** injected thin edge raises →
     `decide` → `REFUSE` (fail-closed).
   - **[decision, in-sandbox] B1 drop-didn't-take-effect case:** inject a probe result where
     the euid/uid read-back does NOT equal the target agent uid (`DROP_UNVERIFIED`), and a
     separate `DROP_FAILED` case → the probe must **REFUSE**, never report `CLOSED`. This is
     the explicit B1 stress-test: a drop that does not take effect must never be folded into
     the write-permission signal.
   - **[decision, in-sandbox] override case (question (a) hook):** a `NOT_CLOSED` path +
     `override_ack` present → `PROCEED_UNCLOSED` with the exact honest label string, and
     *never* `CLOSED`.
   - **[decision, in-sandbox] key-absent vs key-empty:** key path missing → `REFUSE`; key
     present but zero bytes → `REFUSE` (both `KeyUnavailable`-class, distinct inputs).
   - **[decision, in-sandbox] plugins case:** `plugins/` present-but-writable → `REFUSE`;
     absent-dir tolerated as not-a-failure-for-absence.
   - **[decision, in-sandbox] escape-hatch case:** assert the probe's path set contains no
     built-in `/plan` `/build` reference and the module exposes no operator-agent
     enumeration.
2. **Implement the pure core** (`ENFORCEMENT_PATHS`, `resolve_final_target`,
   `classify_probe_result`, `decide`) until the pure-logic tests pass.
3. **Implement the thin edge** (`probe_write_as_agent`, `probe_read_key_as_agent`, the
   real-uid-drop-**and-verify** fork path per B1 — drop, then euid/uid read-back gate, then
   write/read; discriminated result) with the subprocess/uid edge **injectable** so the pure
   decision logic is tested without real perms, same as `sandbox` tests fake `subprocess.run`.
4. **Add `bin/gleipnir-preflight`** thin shim (exec the stdlib CLI, same one-exec shape as
   `bin/gleipnir-sandbox`), plus a `__main__.py` that runs the probes and sets the exit
   code (0 = proceed, nonzero = refuse; distinct nonzero for dev-mode proceed vs refuse if
   useful). NOT added to any agent allowlist.
5. **Run the suites in the right places (B2):**
   - **In-sandbox** (`bin/gleipnir-sandbox test`, root container): the 291 existing tests +
     `tests/test_preflight_decision.py` (mocked-edge decision logic + symlink-resolution
     logic) run and MUST be green; the `@pytest.mark.hostonly` real-perms tests are **skipped
     here by the marker** (root would defeat chmod), so "291 + new decision tests green
     in-sandbox" is honestly achievable — no chmod-based denied test is claimed to pass under
     root. Coverage (line+branch) is reported.
   - **Host-only** (non-root uid, off-sandbox runner): `tests/test_preflight_probe_hostonly.py`
     runs the real-chmod attempted-write/read + symlink + (uid-available) real-drop tests,
     genuinely exercising the denied → CLOSED path against real OS enforcement.
6. **Operator-environment steps (documented, NOT executed by any agent):** create the
   agent uid; `chown` the enforcement subtree to the owning principal and `chmod` it
   ro-to-agent; place the real key unreadable-to-agent; install the wrapper on the host.
   These are named here so the plan is executable end-to-end by the operator, but they are
   out-of-framework acts.

---

## S — Stress-test (concrete acceptance checks)

1. Enforcement file **writable** by the testing uid → probe reports **NOT closed** →
   preflight decision **REFUSE** (nonzero exit).
2. Enforcement subset **ro (0o444)** to the testing uid → probe reports **closed** for
   those paths.
3. **Key readable** (0o444) → **REFUSE**.
4. **Key unreadable** (0o000) + all files ro → **PROCEED** (0 exit).
5. **Symlink** from an enforcement path into a writable location → resolution detects it →
   **REFUSE**.
6. Any **probe error / ambiguity / missing enforcement file** → **REFUSE** (fail-closed;
   never "assume fine").
7. **Key file entirely ABSENT** → **REFUSE** (`KeyUnavailable`-class; no key = no closed
   boundary).
8. **Key file present but EMPTY (zero bytes)** → **REFUSE** (distinct input from absent; same
   fail-closed verdict).
9. **B1 — privilege drop did NOT take effect**: simulate a drop where the euid/uid read-back
   does not equal the target agent uid (`DROP_UNVERIFIED`), and separately a `DROP_FAILED`
   (the setuid/setgid itself raised) → the probe must **REFUSE**, and MUST NOT report
   `CLOSED`. A failed/unverifiable drop is its own error case, never folded into the
   write-permission signal.
10. **Same-uid box**: write-probe as the only uid succeeds → **NOT closed** → **REFUSE**
    (no false "G-1 closed"); with the Part-0 override present → **PROCEED_UNCLOSED** stamped
    with the exact honest "G-1 NOT closed (dev-mode)" label, and the verdict is *never*
    `CLOSED`.
11. **Root**: real write/read as root succeeds → **NOT closed** → **REFUSE** (`os.access`
    is never the decision, and never gates whether the real probe runs).
12. **stdlib-only**: no third-party import in `src/gleipnir/preflight/` (mirror the
    `test_*_stdlib_only.py` pattern already in `tests/`).
13. **Escape hatch untouched**: the module and CLI contain no enumeration of, check on, or
    restriction of the operator's built-in `/plan` `/build`; the probe subject set is the
    in-framework enforcement path list only.
14. **`plugins/` present-and-writable refused** (`.gleipnir/plugins/sequence-gate.ts` is a
    live path today); absent-dir tolerated as not-a-failure-for-absence.
15. **Test-location honesty (B2)**: the chmod-based real-perms denied/writable/key tests are
    `@pytest.mark.hostonly` and **skip under root/in-sandbox**; the in-sandbox suite covers
    the denied *decision* via a mocked/injected probe edge. No chmod-based denied test is
    claimed to pass under root.
16. The existing **291 tests remain green** in-sandbox alongside the new decision tests; the
    in-sandbox run reports line+branch coverage; the host-only real-perms suite runs off-root.

---

## Durable decision to persist (Tier-3 — this role CANNOT write it)

**Flag for the operator to author `.gleipnir/decisions/s2-g1-closure.md`** (Tier-3 POLICY;
`gleipnir-plan` may write only `.gleipnir/plans/**`). It should record, as durable
resolutions that later work depends on:

- **D1** relocate-and-deny hybrid = the sanctioned "Option A where containers are
  unavailable" for the host-run agent; **B-literal (containerise the whole session) is
  DEFERRED to the C-hardening tier.**
- **CRUX** the hybrid closes G-1 *only* if the agent runs as a different OS uid than the
  owner of the enforcement files; else `chmod` is self-removable. Handled by a fail-closed
  behavioural preflight run as the owning principal.
- **D2** single `OPENCODE_CONFIG_DIR` with per-subtree OS perms; enforcement subset ro,
  `goals/`/`plans/`/skill bodies writable; symlink-resolution check on every enforcement
  path.
- **D3** key/rate-table/toggles under the ro boundary; **key OS-UNREADABLE** to the agent
  uid (not merely unwritable); path stays env-pointed via `GLEIPNIR_MARKER_KEY_FILE`;
  external secret-store is a C evolution, deferred.
- **D4** preflight = an out-of-framework, fail-closed launch wrapper run as the owning
  principal; not an agent-invokable/editable script; does not check the escape hatch.
- **D5** first-slice scope + explicit deferrals: containerising the session (B-literal→C),
  broker/credential isolation + E-1 argument policy (step 4 — NOT pulled in), full
  plugins/hooks-registered + bus-reachable preflight checks (gated on those existing).
- **Honesty posture (LABEL THIS EXPLICITLY):** the OS-perms floor is an honest first floor,
  **NOT the terminal boundary**; terminal G-1 closure is the S-2 container mount (B-literal)
  + full S-3 preflight, deferred. No session over this slice may claim "G-1 closed" — at
  most "G-1 boundary held at the OS-perms floor" (real separation present) or "G-1 NOT
  closed (dev-mode)" (single-uid override).
- **The operator-override honesty question (a):** whether a Part-0 operator-acknowledged
  override exists at all, and where its (non-agent-reachable) marker file lives. This is
  itself an operator decision; this plan builds the fail-closed path and the honest-label
  hook but does not presume the override into existence.

---

## Execution Workflow (for the implementing pipeline)

1. **Pipeline entry:** this is a normal Gleipnir build of framework *code* (the preflight
   module + CLI + tests), so it runs the standard stages: `spec-review` (this plan as
   rubric) → `test` (author `tests/test_preflight_boundary.py` first, per Assemble step 1)
   → `code` (implement pure core, then thin edge, then shim; Assemble steps 2–4) →
   `quality` → `git`. The enforcement *activation* (chown/chmod/key placement/wrapper
   install) is **operator-environment work outside this pipeline** (Assemble step 6),
   named but not agent-executed.
2. **Author-tests-first discipline:** the arbiter is the test, not model IQ. Every
   Stress-test item above must have a corresponding failing test before the module exists;
   do not weaken a test to make it green.
3. **`os.access` is banned from the decision path AND from gating the probe.** Reviewers:
   reject any verdict derived from `os.access`; the verdict must come from an actually-
   attempted write/read (after a verified drop) that fail-closes on `PermissionError`.
   `os.access` may ONLY influence ordering or logging — it must NEVER short-circuit or skip
   the real attempted-write/read, which runs unconditionally. Reject any code that reads an
   `os.access` "not writable" hint as licence to omit the real probe.
3a. **B1: drop-and-verify is mandatory and separately classified.** Reviewers: reject any
   probe that wraps the setuid/setgid drop AND the write in one `except PermissionError`.
   The drop must be followed by an independent euid/uid read-back (`os.geteuid()`/
   `os.getuid()` both == target) BEFORE any write/read; a failed or unverifiable drop is its
   own REFUSE case and may never be reported as CLOSED.
4. **Fail-closed is the default branch everywhere.** Any unhandled combination, exception,
   missing path, absent OR empty key, drop-failure/unverified-drop, or symlink anomaly ⇒
   REFUSE. Branch coverage on the failure paths is the point (this is a fail-closed guard).
4a. **Guard-on-guards trust dependency (named):** `src/gleipnir/preflight/boundary.py` is
   itself agent-writable until merge, so its integrity as a guard rests on the `quality`/`git`
   review gate. Reviewers own that dependency explicitly.
5. **Do not add `bin/gleipnir-preflight` to any agent allowlist**, and do not modify
   `src/gleipnir/verify/marker.py`. If either seems necessary, stop — it signals the
   chicken-and-egg boundary is being violated; route back to the orchestrator.
6. **Do not touch the escape hatch.** If any task implies enumerating or restricting
   `/plan` `/build`, refuse and route back — that is the Part 0 boundary, out of scope by
   design.
7. **Material decision escalation:** design question (a) (dev-box override posture) and the
   whole `.gleipnir/decisions/s2-g1-closure.md` record are **operator-authored Tier-3**.
   The pipeline surfaces them; it does not self-author them. If implementation reveals a
   new material tradeoff (e.g. the override marker's location is ambiguous), stop and route
   to `gleipnir-brainstorm` / the operator — do not bake in a choice.
8. **Verification:** run `bin/gleipnir-sandbox test`; report pass count (must include the
   prior 291 green) and line+branch coverage. The slice is done when every Stress-test
   item has a green test and the honest-posture labels are exactly as specified.
