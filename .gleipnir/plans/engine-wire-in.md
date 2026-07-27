# Plan: G-5 engine wire-in (minimal structural sequencing block)

**Status:** planning artifact (Tier 0, disposable). ATLAS brief per
`../goals/plan-format.md`. Authored by `gleipnir-plan`. Sequencing of the
stages this plan defines belongs to the orchestrator, not to this document.

**Scope in one line:** make the already-built, currently-inert G-5 engine
(`src/gleipnir/engine/`, 49/49 green) actually *block* out-of-order `task`
delegations, by wiring opencode's pre-tool hook (S-1 hook #1 /
`tool.execute.before`) to the engine's pipeline state, fail-closed. Nothing
more.

---

## GOTCHA pre-flight (recorded)

- **Goal order correct:** plan-before-code; engine exists, this is the wire-in.
- **Gaps this plan must close:**
  1. No Python *driver* exists — `Engine` is a pure in-memory state machine
     with no caller, no persistence, no filesystem surface (DESIGN.md
     "Non-goals": "No S-2 substrate concerns... pure in-memory state").
  2. No opencode plugin exists — `.gleipnir/plugins/` is absent; the hook seat
     is unbuilt.
  3. The *target-agent → legitimate-current-state* check table is not written
     anywhere; `stage-role-map.md` binds stages to roles but not the reverse
     lookup the hook needs. Trace produces it below.
- **Layered per GOTCHA-as-amended:** sequencing stays in code (the Python
  `TRANSITIONS` table is the single source of truth; Amendment 1). The pre-tool
  hook is a *gate*, not an orchestrator — it consults state and aborts; it does
  not decide order. State *advances* off a **mechanically observed** `task`
  completion (the Tier-3 **post-tool** hook), never off an agent's narrated
  report — closing the self-attestation pattern G-5/G-3.2 forbid.
- **Capability boundary honoured:** this file is the only artifact I write. The
  TS plugin and the state-file writer grant are **Tier-3 / operator-authored**
  hand-offs, flagged throughout. A durable decision is named for `decisions/`.

---

## Architect

**Problem (one sentence).** The deterministic G-5 engine models the correct
pipeline sequence, the human-question block and the attestation gate, but it is
wired to nothing, so today "an agent cannot be dispatched out of order" is true
only by the orchestrator's prose discipline — not by the runtime refusing the
call.

**User.** The operator (who needs the framework's central claim — deterministic
sequencing that cannot be skipped — to be *structurally* true, not
aspirational). Secondarily every roster agent, including the orchestrator,
which becomes *subject to* the engine rather than trusted to emulate it.

**Measurable success criteria.**

1. A `task` delegation to a role that is **not** legitimate for the engine's
   current pipeline state is **aborted by the runtime** (the hook throws;
   opencode never spawns the subagent). Verified by an out-of-order delegation
   that raises, with the subagent provably not invoked.
2. The **allowed** next delegation for the current state **proceeds**
   unmodified. Verified by the in-order delegation completing normally.
3. A **missing, unreadable, or corrupt** state bridge causes the hook to
   **abort** (fail-closed), never to allow-by-default. Verified by deleting /
   truncating / tampering the state artifact and confirming the next
   delegation is refused.
4. The **orchestrator's own** `task` delegations are gated by the same hook
   (self-reference): the orchestrator cannot dispatch out of order either.
   Verified by an out-of-order delegation issued *by the orchestrator* being
   aborted.
5. The **existing 49 engine tests remain green** — the wire-in adds a driver
   and a persistence surface *around* the engine and does not alter
   `TRANSITIONS`, the state enum, or any method contract.
6. **Single source of truth preserved:** the sequencing rule the hook enforces
   is derived from (or verified against) the Python `TRANSITIONS` table, not a
   second, independently-editable copy of the pipeline order.

**Constraints.**

- **Two languages, one truth.** Enforcement core is Python (engine;
  `decisions/runtime-and-deps.md`); the hook is TypeScript/Bun (opencode
  runtime). The bridge spans them. `TRANSITIONS` must stay the sole authority.
- **Tier discipline (`decisions/gleipnir-layout-and-memory-model.md`).** The
  hook is Tier-3 enforcement code (guard code): operator-authored,
  agent-unwritable, under the enforcement boundary. No roster agent — not even
  `gleipnir-code` — may write it. Any state artifact the hook reads must live
  at a tier whose writer is a framework process, **never** an agent-writable
  tier (Tier 0/2), or an agent could forge its way past the gate.
- **Fail-closed everywhere.** Unknown state, missing bridge, ambiguous
  mapping, corrupt artifact ⇒ abort. Absence of a code path is denial, matching
  the engine's own posture (`NoSuchTransition`, `AttestationNotGreen`) and the
  G-3.1 verifier (`verify/marker.py`: "any doubt refuses").
- **Minimal slice only.** No L2–L5 autonomy config, no configurable gates, no
  bolt-ons, no evidence-rung machinery beyond the attestation edge the engine
  already has. Those layer onto a *now-live* engine afterward.
- **stdlib-only** for any Python added (`decisions/runtime-and-deps.md`).
- **opencode reality:** `subagent_depth: 1` (nested delegation allowed one
  level); `default_agent: orchestrator`; plugins load from
  `.gleipnir/plugins/` via `OPENCODE_CONFIG_DIR` (`opencode.jsonc`).

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Tier / writer | Role |
|---|---|---|---|
| G-5 engine (unchanged) | `src/gleipnir/engine/__init__.py` | code; `gleipnir-code` (test-first) | Sole authority on legal transitions (`TRANSITIONS`) |
| **Engine driver (new, Python)** | `src/gleipnir/engine/driver.py` (proposed) | code; `gleipnir-code` | Instantiates `Engine`, advances it on stage completion, **persists state to the bridge**, and (for option c) **emits the derived agent-allow table** |
| **State bridge artifact (new)** | see recommendation below | **framework-process writer, non-agent, Tier-3-equivalent** | Carries **both** current `PipelineState` **and** the allowed-agents projection for that state (+ one integrity MAC over both) from Python to the TS hook |
| **Pre-tool hook plugin (new, TypeScript)** | `.gleipnir/plugins/sequence-gate.ts` (proposed) | **Tier-3, operator-authored** | Reads bridge, maps dispatched agent → allowed?, throws to abort on deny/doubt |
| Stage-role map (authority for mapping) | `.gleipnir/stage-role-map.md` | Tier 3 | The stage→role binding the reverse table is derived from |
| Agent-allow check table (derived) | **re-emitted into the bridge per session** (not embedded in the plugin) | derived, not hand-maintained | current-state → set of legitimately-dispatchable target agents; the TS hook **reads** it from the bridge, so there is no static copy to drift |

### The reverse mapping the hook needs: target agent → legitimate current-state(s)

The hook intercepts `task` calls. Each `task` names a **target subagent**. The
hook must answer: *"from the engine's current state S, is dispatching agent X
legitimate?"* Derived from `stage-role-map.md` (the authority) and the engine's
`PipelineState` enum:

| Target agent | Bound stage(s) | Legitimate when engine state ∈ |
|---|---|---|
| `gleipnir-plan` | brainstorm, plan | `{BRAINSTORM, PLAN}` |
| `quality-reviewer` | spec-review, quality | `{SPEC_REVIEW, QUALITY}` |
| `gleipnir-code` | test, code | `{TEST, CODE}` |
| `git-ops` | git | `{GIT}` |
| `orchestrator` (gate) | gate | *(gate is the orchestrator's own bound stage; not a `task` target — see below)* |
| `project-mgr` | — (no G-5 pipeline stage) | **∅ — deny in the minimal slice** |
| `notify` | — (no G-5 pipeline stage) | **∅ — deny in the minimal slice** |

Notes that are load-bearing, not incidental:

- **`quality-reviewer` and `gleipnir-code` each map to two states.** The engine
  distinguishes `SPEC_REVIEW` vs `QUALITY` and `TEST` vs `CODE`, but both
  states in a pair route to the *same role*. The hook checks role-legitimacy
  ("is this agent allowed to run in state S at all"), which is exactly the
  granularity `stage-role-map.md` binds. That is sufficient for the minimal
  slice: it blocks the cross-stage jumps that matter (e.g. dispatching
  `git-ops` while in `PLAN`, or `gleipnir-code` while in `BRAINSTORM`).
- **`project-mgr` and `notify` have no G-5 pipeline stage** in
  `stage-role-map.md`. In the minimal slice they are **out of the gated
  pipeline** entirely. Two fail-closed options — the plan **recommends the
  first** and flags the choice as the one durable decision (below):
  - **(recommended) deny them while a pipeline is active** — the minimal slice
    gates only the eight pipeline stages; PM/notify are not part of the
    sequenced pipeline yet, so dispatching them mid-pipeline is "not the
    allowed next step" and is refused. This keeps the gate's rule identical to
    the engine's transition table with zero special-casing.
  - (alternative, explicitly *not* chosen now) allow them always as
    out-of-band — rejected for the minimal slice because "allow" defaults are
    exactly what fail-closed forbids; deferring them is safer than carving an
    allow-hole on day one.
- **`gate` is not a delegated `task`.** Per `stage-role-map.md` binding rules,
  `gate` is the orchestrator's *own* bound stage (reading attestation, emitting
  state) — it is `Engine.attempt_gate(...)`, not a subagent dispatch. So the
  hook does not need a "dispatch to gate" row; the attestation edge is already
  structural in the engine.

### How pipeline state advances (mechanically observed, never agent-reported)

The engine advances only via `step(judge, payload)`, `answer_human_question`,
and `attempt_gate` (DESIGN.md). For the minimal slice, the concrete question is:
*what tells the driver a stage completed so the next delegation becomes legal?*

**Design pin — the completion signal is a mechanically observed fact, not a
narrated report.** If the orchestrator (or any agent) *told* the driver "the
stage passed," that self-report would be the input advancing the very gate the
orchestrator is subject to — the self-attestation / self-narrated-sequence
pattern that G-5 and G-3.2 exist to forbid. So **no agent — not even the
orchestrator — supplies the "stage completed" signal.** The *runtime* observes
it, using opencode's **S-1 point-2 POST-tool hook (`tool.execute.after`)**,
which is itself Tier-3, non-agent code (the same non-agent side as the pre-tool
gate). The mechanism:

1. Orchestrator issues a `task` to the role bound to the current stage.
2. The **pre**-tool hook (`tool.execute.before`, the gate) permits it because
   the target agent is legitimate for the current state.
3. The delegated subagent runs and the `task` tool returns.
4. The **post**-tool hook (`tool.execute.after`) — Tier-3 framework code, not
   an agent — **observes** that the `task` tool returned. That mechanically
   observed outcome (tool returned without error) is the input that advances
   state: the hook triggers the driver to call `engine.step(judge=…)` with the
   verdict *derived from the observed tool outcome*, not from any text the
   orchestrator supplies.
5. The driver advances the engine deterministically per `TRANSITIONS` and
   (Tier-3, non-agent) **rewrites the bridge artifact** with the new state (+
   allow-table projection, + integrity, below). The next delegation is now
   checked against the new state.

**What post-tool observation can and cannot tell you (stated honestly).** The
post-tool hook can see, as a mechanical fact, that the `task` tool *returned
without error* — i.e. the delegated subagent completed rather than crashing or
being aborted. It **cannot** judge whether the work was *good*: it does not know
if a spec-review found defects or a test suite genuinely passed. That
quality/verdict judgment is the job of the separate `spec-review` and `quality`
stages, which the engine **already models** as its `PASS`/`FAIL`/`NEEDS_HUMAN`
verdicts. So for the minimal slice the rule is precisely: **"task returned
cleanly" = advance-eligible** (the trivial completion verdict); richer per-stage
verdicts (real spec-review outcomes, CI attestation for the git→gate edge)
remain the engine's existing contract and are fed in as the driver matures. The
wire-in's job is only to make the *sequence* enforce off a mechanically observed
completion; the engine already owns *how* states change once a verdict arrives.

> **Who advances state — resolved onto the non-agent side (was an open seam).**
> The question "which component holds the canonical `Engine` instance for a live
> session, and how a delegation outcome reaches it" is folded into the driver
> **build gate** below (see Trace → *Driver invocation*). Its smallest correct
> shape: the **post-tool hook, being Tier-3 framework code, is what triggers the
> driver to advance** — keeping the *entire* advance path (observe → advance →
> rewrite bridge) on the non-agent side. No agent invokes the driver and no
> agent reports completion.

### BUILD GATE: how is the driver invoked in a live session?

*(Promoted from an open seam to an explicit build gate — the same treatment
given to the S-1 target-agent-visibility question, because the whole
advance-path correctness rests on it. The build stops until this is resolved.)*

The blocker this gate closes: **under the current roster grants, no agent can
invoke a Python driver CLI.** The orchestrator has `bash: deny` with no
exceptions; `gleipnir-code`'s bash allowlist is only npm/pytest/go/make. So any
prose that implied "the orchestrator (or a session process) invokes the driver
CLI" is *impossible* to realise through a roster agent — and *making* it
possible would mean granting a roster agent a new bash capability, which is
itself a **G-2 decision** and exactly the enumerable-capability expansion the
minimal slice must avoid.

**Resolution (design pin).** The driver is invoked by **framework / runtime
code — the same Tier-3 hook/plugin layer (or a framework process) — never by a
roster agent via a new bash grant.** Concretely, the **post-tool hook
(`tool.execute.after`)**, being Tier-3 framework code, is what advances the
driver and rewrites the bridge on observed `task` completion. This puts the
driver-advance on the *same non-agent side* as the pre-tool gate that consumes
its output: observe (post-hook) → advance engine → rewrite bridge → the
pre-hook reads it on the next `task`. The whole advance path is non-agent.

- **What is gated:** before building the advance path, the build confirms the
  post-tool hook layer (Tier-3) can host the driver invocation — either by
  importing/embedding the Python driver behaviour, or by the framework process
  owning the live `Engine` and the hook signalling it in-process. **If the only
  realisable path turns out to require a roster-agent bash grant, STOP** and
  hand the G-2 capability question to the operator rather than widening a grant
  in the minimal slice.
- **Why not an agent:** granting bash to advance state would let the agent that
  is *subject to* the gate also *drive* the gate — reintroducing the
  self-sequencing this whole wire-in removes.

### The key design problem: the Python-engine ↔ TS-hook **state bridge**

The engine is Python; the hook is TypeScript. The hook must know the current
`PipelineState` on every `task` interception. Four options evaluated against
**single-source-of-truth**, **determinism**, **trust tiers**, **simplicity**,
and **fail-closed / non-forgeability**.

**(a) TS hook shells out to the Python engine per check (subprocess).**
- *Single source of truth:* strong — the Python engine answers directly; no
  transition logic in TS.
- *Determinism:* fine functionally, but the hook is a *synchronous* pre-tool
  interceptor; spawning a Python subprocess (interpreter start + import) on
  **every** `task` call adds latency and a new failure mode (interpreter not
  found, PATH, venv) on the hot path.
- *Trust tiers:* the subprocess must not be agent-influenceable in what it
  runs; acceptable if the invocation is baked into the Tier-3 plugin.
- *Simplicity:* medium — cross-language process management inside a Bun hook,
  plus argument/exit-code protocol design.
- *Fail-closed:* natural — non-zero exit / no output ⇒ throw.
- *Verdict:* correct-by-construction on SSOT but the **worst on the hot path**
  and adds a runtime dependency (a working Python + venv) to *every tool call*,
  not just pipeline transitions.

**(b) Engine state persisted to a file the hook reads and the engine writes.**
- *Single source of truth:* strong — Python engine remains the only thing that
  *decides* state; the file is a read-only projection for the hook. The TS side
  performs a pure lookup (state → allowed agents), no transition logic.
- *Determinism:* excellent — the hook does a bounded file read + comparison; no
  process spawn, no clock-dependent behaviour on the hot path.
- *Trust tiers:* **this is the crux.** The file must be written by a framework
  process and be **unwritable by any agent**. It is *not* a Tier-0 `plans/`
  artifact (agent-disposable) and *not* Tier-2. It **is enforcement evidence**
  — the state the gate trusts on every `task` — so it is classified
  **non-agent-writable at Tier-3-equivalent strength**, not a Tier-1 RETRIEVED
  provenance log. A **framework-runtime state path** written only by the
  driver/engine process and read by the Tier-3 hook. If an agent could write
  it, the gate is forgeable — so the *writer grant* is the security-critical
  part, and it is a Tier-3-level policy decision (named below).
- *Simplicity:* highest — a small JSON file; both languages have trivial
  JSON + file IO in stdlib.
- *Fail-closed / non-forgeability:* the missing/corrupt cases map cleanly to
  abort. **G-3.1-style digesting applies directly:** the driver HMACs the
  state payload with the verifier key (`verify/marker.py`; key under the S-2
  boundary via `GLEIPNIR_MARKER_KEY_FILE`), and the hook validates the MAC
  before trusting the state. An agent that overwrites the file cannot forge a
  valid MAC without the key, so tampering ⇒ validation fail ⇒ abort. This is
  the same defence the memory model already reuses for Tier-3/Tier-2 files.
  **Reuse caveat (not verbatim):** `verify/marker.py`'s `Marker`/`validate`
  bind to a **`tree_hash`** and `validate` demands a `current_tree_hash`
  *recomputed from the filesystem tree* (`compute_tree_hash`). A pipeline-state
  value has **no independent recompute** — there is no "current state" to hash
  off the tree, the bridge *is* the state. So the reuse needs an **adapted
  `StateMarker`**: either a parallel frozen dataclass that MACs
  `(version, state, allow_table, minted_at)` with the same key/HMAC/freshness
  machinery, or a documented repurposing of `Marker` where the payload field
  substitutes for the tree binding and the tree-equality check is *replaced*
  (not merely satisfied) by a state/allow-table match. The keyed-HMAC +
  freshness core is reused; the tree-binding check is **not** — do not imply
  verbatim reuse.
- *Verdict:* **recommended.** Best on determinism and simplicity, keeps Python
  as SSOT, and its one real risk (a writable state file) is closed by the
  existing G-3.1 mechanism plus a non-agent writer grant.

**(c) Sequencing logic mirrored in TypeScript in the plugin.**
- *Single source of truth:* **violated in spirit** — two copies of the
  transition/allow rule that can drift. Mitigations exist (generate the TS
  table from Python; a Python test asserts parity), but the plugin now *decides*
  legality, not just *looks it up*, so the enforcement rule lives in an
  agent-relevant surface twice.
- *Determinism:* excellent (no IPC), but correctness now depends on the mirror
  staying faithful.
- *Trust tiers:* the mirrored logic is Tier-3 (in the plugin), fine — but it
  still needs *current state* from somewhere, so it does **not remove the
  bridge**, only the transition maths. It reduces to (b) plus a redundant,
  drift-prone rule copy.
- *Simplicity:* deceptively low — the parity test + codegen is real ongoing
  cost.
- *Fail-closed:* fine.
- *Verdict:* rejected for the minimal slice. It adds a second authority for
  sequencing precisely where the framework's whole point is one authority. The
  engine stays the "test oracle," but a mirror that must be kept in sync is a
  new drift guard we would then have to enforce.

**(d) A small local IPC/service the engine exposes and the hook queries.**
- *Single source of truth:* strong (like a), Python answers.
- *Determinism:* good once up, but introduces a long-lived process, a port/
  socket, lifecycle (start/stop/health), and a new "service is down" failure
  mode on the hot path.
- *Trust tiers:* the socket must be unreachable by in-sandbox agent code — the
  **same class of problem E-1 flags for the broker IPC** ("the in-container IPC
  channel must not be reachable by arbitrary in-sandbox code"). That is real
  substrate work not yet built.
- *Simplicity:* lowest for a minimal slice — most moving parts.
- *Verdict:* rejected for the minimal slice; premature. Revisit only if a
  persistent-session model (the Olympus direction) makes a resident engine
  service natural, at which point it converges with the broker's IPC hardening.

**Recommendation: (b) — engine writes a digest-protected state file; the TS
hook reads and validates it.** One-line why: it keeps Python's `TRANSITIONS` as
the single source of truth, is the simplest thing that can be made *correct and
fail-closed*, and its only real risk (a forgeable state file) is closed for
free by the already-built G-3.1 HMAC mechanism plus a non-agent writer grant.

**Allow-table delivery — drift-proof by re-emission into the same bridge (not
a plugin-embedded copy).** The current-state → allowed-agents projection is
**re-emitted into the digest-protected bridge** on every state write: same
file, same MAC, same non-agent writer, so it inherits exactly the
writer-grant/tier treatment already designed for the state field. The TS hook
**reads** the allow projection from the bridge per session rather than
embedding a static copy — so there is **zero drift** and no second authority.
This is what keeps the recommendation squarely option (b) and avoids sliding
back into option (c)'s mirrored-rule-in-the-plugin drift: the plugin holds *no*
sequencing literal; it only reads and compares. The bridge payload therefore
carries **both** the current state **and** its allowed-agents set, both covered
by the **one** MAC. (If a future step ever *must* embed a static literal in the
TS plugin, that is a regression away from this design and would require an
explicit regeneration discipline plus a mechanical deployed-drift check — not a
mere Python-side parity test; the minimal slice deliberately does **not** go
there.)

**Where the state file lives, whose writer, which tier.** It is **not** an
agent-writable path. The driver (a framework process, not a roster agent)
writes it; the Tier-3 hook reads it. Proposed path under a framework-runtime
directory, e.g. `.gleipnir/var/run/pipeline-state.json` (a *runtime* sibling of
`var/tmp/`, but with a **framework-process-only writer grant**, not the
disposable free-write of `var/tmp/`). The exact path + writer-grant is a
Tier-3 policy decision and is named in the hand-off below; the hook's read path
must be one no roster agent can also write. The bridge is **enforcement
evidence**, so it is classified **non-agent-writable at Tier-3-equivalent
strength** (it carries the very state the gate trusts — not a Tier-1
provenance log). Integrity: HMAC over the state payload with the verifier key
(`GLEIPNIR_MARKER_KEY_FILE`), validated by the hook before use, so a tampered
or agent-planted file fails closed.

### The driver's OWN trust protection (distinct from the bridge-file MAC)

The bridge MAC stops a *reader* trusting a forged **file**. But the **driver
itself calls `mint()` with the real key**, so it *holds signing authority* — it
can produce a valid MAC for any state it writes. Yet the driver is ordinary
`src/` Python, editable by `gleipnir-code` (the roster's `code` stage). Two
distinct forgery vectors follow, neither closed by the bridge MAC:

- **(a) Source edit.** An agent that could edit `src/gleipnir/engine/driver.py`
  could change *what state the driver signs* (e.g. advance to `GIT` early) and
  the MAC would still validate, because the driver holds the key. Defence
  (design intent, honestly *not yet closed*): the driver source must sit
  **under the S-2 enforcement boundary** — agent-unwritable at build/deploy
  time — so no roster agent can alter signing behaviour. Today the roster denies
  `.gleipnir/` writes but `src/` is agent-writable; the structural guarantee
  awaits the S-2 mount + terminal closure.
- **(b) Unverified invocation.** If any code path *other than* the Tier-3
  post-tool hook could invoke the driver's advance, an attacker could advance
  state at will. Defence (design intent): the driver's advance entrypoint is
  invoked **only from the Tier-3 hook layer** (Blocker-2 resolution) — never
  from a roster-agent bash grant, never from a general CLI an agent can reach.
  This keeps signing authority bound to the same non-agent side as the gate.

**Recorded as a known not-yet-closed item** (not left implicit): the driver is
a signing-authority holder whose *source integrity* (a) and *invocation
integrity* (b) are enforced structurally only once S-2 mounts the enforcement
boundary and terminal closure + S-3 preflight verify it. Until then this slice
is honest: the driver's trust is *authored and hook-scoped, not yet
boundary-closed*. Carried into the OUT-of-scope note and the durable decision.

### Edge cases (all resolve to abort)

- **Bridge file missing** ⇒ abort. (No state ⇒ no legal delegation.)
- **Bridge file present but unparseable / wrong schema** ⇒ abort.
- **Bridge MAC invalid / key unavailable** ⇒ abort (G-3.1 posture).
- **State value not a known `PipelineState`** ⇒ abort.
- **State is `HUMAN_QUESTION` or `ESCALATED`** ⇒ **all** `task` dispatches
  abort. These are engine control states with no pipeline stage; the only exits
  are `answer_human_question` / (terminal). A `task` during them is by
  definition out of order.
- **State is `GATE`** (terminal) ⇒ abort all dispatches (pipeline done).
- **Target agent not in the allow table for the current state** (incl.
  `project-mgr`/`notify` in the minimal slice) ⇒ abort.
- **Ambiguous / unrecognised target agent** ⇒ abort (deny-by-default; never
  allow an agent the table does not name).
- **Stale bridge** (freshness): the G-3.1 marker carries `minted_at`; a stale
  state older than a bound ⇒ abort, so a delegation cannot ride an old,
  no-longer-current state.

### What is explicitly OUT of scope (minimal slice)

- L2–L5 autonomy configuration; configurable gates; any per-project policy
  knobs.
- Any bolt-on beyond the sequencing block (no notify/PM integration into the
  pipeline; no G-4 bus emission; no ledger).
- Real per-stage judgment content (real spec-review/quality verdicts, real CI
  attestation *fetch*) — the engine already models the *edges*; feeding richer
  verdicts is later. The minimal driver may use the trivial completion judge.
- Evidence rungs / G-3.2 attestation *sourcing* (the engine's `attempt_gate`
  contract is unchanged; wiring it to a real CI surface is out of scope here).
- The S-2 substrate mount and terminal closure that make the hook and key
  *structurally* unreachable — those remain later steps; this slice is honest
  about being "authored, enforced-at-the-hook, not yet closed at the boundary."

---

## Link (validated before building)

- **Engine contract is stable and sufficient.** Read `engine/__init__.py` +
  `DESIGN.md`: `PipelineState` enum, `TRANSITIONS`, `step`/`answer_human_
  question`/`attempt_gate`, and the fail-closed exceptions are all present and
  green (49/49). The wire-in needs no change to these — confirmed.
- **opencode exposes the enforcement seat.** Spec S-1 point 1 +
  D-1 resolution: `tool.execute.before` is present and "can abort a call"
  (verified 7/8 hooks). The `task` delegation primitive is hook #4. So a
  pre-tool hook *can* intercept `task` and throw. Confirmed against spec.
- **Plugin load path exists.** `opencode.jsonc` + `AGENTS.md`: opencode reads
  `.gleipnir/plugins/` via `OPENCODE_CONFIG_DIR`. (Directory does not yet
  exist — creating it + the plugin is operator Tier-3 work.)
- **Integrity primitive already built.** `verify/marker.py` (G-3.1) gives
  keyed-HMAC + fail-closed validate + freshness + key-outside-agent-surface —
  reused as the bridge's non-forgeability mechanism via an **adapted
  `StateMarker`** (see Trace: the tree-binding check has no independent
  recompute for a state value, so the tree-hash binding is replaced by a
  state/allow-table binding; the HMAC + freshness core is reused, not the tree
  check). Confirmed present.
- **Tier model is explicit about writers.** `decisions/gleipnir-layout-and-
  memory-model.md`: authority decreases as writability increases; a lower tier
  may not alter a higher one; state that gates agents must not be agent-
  writable. This is what forces option (b)'s non-agent writer grant. Confirmed.
- **stdlib-only holds:** the driver needs only `json`, `hmac`/`hashlib`
  (via `verify/marker.py`), `enum`, `pathlib`, `argparse` — all stdlib.

Not yet validated (must be checked during build, called out in Stress-test):
whether opencode's `tool.execute.before` receives the **target agent name** for
a `task` call in a shape the hook can read as *typed arguments* (S-1: "inspect
typed arguments"). If the target-agent field is not available to the hook, the
whole gate premise fails and the build must stop and document a compensating
mechanism (spec S-1 conformance clause).

---

## Assemble (test-first build order)

Ordered so each step is validated before the next. **Language and tier are
marked; the TS plugin is an operator Tier-3 hand-off the code stage cannot
write.**

1. **[Python · `gleipnir-code`] Prove the hook can see the target agent.**
   *Before any Python:* the operator/build confirms (a tiny throwaway probe or
   opencode docs) that `tool.execute.before` for a `task` call exposes the
   target subagent name as inspectable typed args. **Gate:** if it does not,
   stop and document the compensating mechanism (S-1 conformance). This is a
   Link item promoted to a build gate because everything downstream depends on
   it.

2. **[Python · `gleipnir-code`] Driver + bridge writer — tests first.**
   Write `tests/test_driver.py` asserting: a fresh driver writes a bridge file
   whose state is `brainstorm`; advancing on a clean-completion verdict rewrites
   it to `plan`; the written payload carries a valid G-3.1 MAC; the driver
   refuses to write without the key (fail-closed). *Then* implement
   `src/gleipnir/engine/driver.py` (owns an `Engine`, exposes read-current-state
   and advance-on-completion, persists via `verify/marker.py`). stdlib-only.

3. **[Python · `gleipnir-code`] Derived allow-table, re-emitted into the
   bridge + parity test.**
   Write a test asserting the current-state → allowed-agents table is derived
   from `stage-role-map` semantics and covers every `PipelineState`, with
   `HUMAN_QUESTION`/`ESCALATED`/`GATE` mapping to the empty set (deny-all) and
   `project-mgr`/`notify` absent from every allow set. Implement the table as
   data the driver **re-emits into the bridge alongside the state, under the
   single MAC** (not a plugin-embedded copy) — so the TS side *reads* the
   allowed-agents set for the current state from the bridge rather than
   re-deriving or embedding it. Add a test asserting every bridge write carries
   both the state **and** its matching allow set under one valid MAC. This is
   how option (b) subsumes the drift risk of option (c): SSOT stays in Python,
   the bridge is the only channel, the plugin holds no sequencing literal.

4. **[TypeScript · OPERATOR Tier-3 hand-off — NOT `gleipnir-code`]**
   **Driver-invocation BUILD GATE (do this BEFORE authoring the plugin).**
   Confirm the Tier-3 post-tool hook layer (`tool.execute.after`) can actually
   **host or trigger the Python driver's advance in-process** — either by
   importing/embedding the driver behaviour or by a framework process owning the
   live `Engine` that the hook signals — with the whole advance path (observe →
   advance → rewrite bridge) staying on the non-agent side. This mirrors the
   Trace *Driver invocation* build gate into an executable step, exactly as
   Assemble step 1 promotes the S-1 target-agent-visibility question to a gate.
   **STOP and escalate to the operator** if the only realisable path would
   require granting a roster agent a **bash capability** to invoke the driver:
   that is a G-2 capability expansion the minimal slice forbids, and it would
   let the agent that is *subject to* the gate also *drive* it. Do not widen a
   grant to get past this — hand the G-2 question to the operator. Only once the
   hook can host/trigger the advance without a new agent bash grant:
   author `.gleipnir/plugins/sequence-gate.ts`, which hosts **two** hooks:
   - the **pre-tool** hook (`tool.execute.before`) that, on a `task` call, (i)
     reads the bridge file, (ii) validates its MAC and freshness (fail-closed),
     (iii) looks up the target agent in the allow set **carried in the bridge**
     for the validated state, (iv) **throws to abort** on any deny/doubt, and
     lets legitimate delegations pass untouched. It **reads** the allow set from
     the bridge (step 3), embedding **no** sequencing literal of its own — zero
     drift.
   - the **post-tool** hook (`tool.execute.after`) that, on a `task` return,
     **observes** completion and triggers the driver to advance state + rewrite
     the bridge (Blocker-1/Blocker-2 resolution). No agent reports completion;
     no agent invokes the driver.

   **Authoring requirement (fail-closed integrity):** *both* hooks must
   **throw on ANY unhandled error path**. A stray catch-and-return — or a
   post-tool handler that swallows an error and lets the `task` result through
   — would silently flip the posture from fail-closed to fail-open. There is no
   permissible non-throwing exit on doubt.

   **This file is Tier-3 enforcement code: operator-authored, agent-unwritable.
   The `code` stage / roster must not write it. Flag as hand-off.**

5. **[Operator Tier-3] Writer-grant + path policy.**
   Establish the bridge path (e.g. `.gleipnir/var/run/pipeline-state.json`)
   with a **framework-process-only writer grant** and read-only from every
   roster agent (blanket agent deny on that path, matching the Tier-3 wall).
   Confirm `GLEIPNIR_MARKER_KEY_FILE` is set to a key path outside the agent
   surface. This is the security-critical grant and is Tier-3 policy.

6. **[Python · `gleipnir-code`] Integration/acceptance tests** (see
   Stress-test) exercising the full abort/allow behaviour against a real (or
   faithfully faked) hook invocation surface, plus re-running the existing
   suite to confirm 49/49 still green.

Rationale for order: the engine is untouched (SSOT preserved), so the *new*
correctness burden is the driver+bridge (steps 2–3, Python, testable in
isolation) and the hook (step 4, TS, the enforcement seat). Steps 2–3 must be
green *before* the TS hook is authored, so the hook consumes a proven allow
table and reads a proven bridge format.

---

## Stress-test (acceptance checks)

Concrete, checkable. Each maps to an Architect success criterion.

1. **Out-of-order delegation is aborted (SC1).** With bridge state = `plan`,
   an orchestrator `task` to `git-ops` is aborted by the hook (throws); the
   `git-ops` subagent is provably never spawned. Repeat for `gleipnir-code`
   while state = `brainstorm`.
2. **Allowed next delegation proceeds (SC2).** With state = `plan`, a `task`
   to `gleipnir-plan` passes the hook and runs normally, unmodified.
3. **Missing bridge fails closed (SC3).** Delete the bridge file; the next
   `task` (even a would-be-legal one) is aborted.
4. **Corrupt/tampered bridge fails closed (SC3).** Flip one byte of the state
   payload (invalidating the MAC), or set a valid-looking state with no/invalid
   MAC; the next `task` is aborted. An agent-planted file with a forged MAC
   fails validation without the key.
5. **Stale bridge fails closed.** A bridge whose `minted_at` exceeds the
   freshness bound aborts the next `task`.
6. **Control-state deny-all.** With state = `human_question` (and separately
   `escalated`, `gate`), *every* `task` dispatch is aborted.
7. **Non-pipeline agents denied in the minimal slice.** A `task` to
   `project-mgr` or `notify` is aborted regardless of pipeline state.
8. **Orchestrator is subject to the hook (SC4).** An out-of-order delegation
   issued by the orchestrator itself is aborted — the gate does not exempt the
   dispatcher.
9. **Unknown target agent denied.** A `task` naming an agent absent from the
   allow table is aborted (deny-by-default).
10. **Legal advance re-opens the next step, mechanically observed (SC2
    dynamic).** From `plan`, the plan `task` **returns** → the **post-tool
    hook observes** the clean return and triggers the driver → the driver
    advances the bridge to `spec_review` (+ re-emits the new allow set under the
    MAC) → a `task` to `quality-reviewer` now passes, and a `task` to
    `gleipnir-plan` now aborts (state moved on). Assert the advance is driven by
    the observed tool return, **not** by any orchestrator-supplied text.
11. **SSOT / no drift (SC6).** The parity test proves the allow table the hook
    reads **from the bridge** is derived from the engine/stage-role authority,
    covering every `PipelineState`; changing `TRANSITIONS` or the enum without
    regenerating the table fails the test. Additionally assert the TS plugin
    contains **no** sequencing literal of its own (drift-proof by re-emission,
    not by a mirrored copy).
12. **Existing suite green (SC5).** `tests/test_engine.py` remains 49/49; no
    engine contract changed.
13. **stdlib-only holds.** The added Python imports only stdlib (candidate C-3
    meta-check per `decisions/runtime-and-deps.md`).
14. **Hooks throw on every unhandled error path (no silent fail-open).** For
    *both* the pre-tool gate and the post-tool observer: inject an unexpected
    error (throwing bridge read, malformed payload the parser did not expect,
    an exception inside the handler) and assert the hook **throws / aborts** —
    never catches-and-returns, which would flip fail-closed to fail-open. In
    particular a post-tool handler that swallows an error must not let the
    `task` result through. There is no permissible non-throwing exit on doubt.

---

## Execution Workflow (for the implementing agents / operator)

**Roles and hand-offs (per `stage-role-map.md` + tier model):**

- The orchestrator sequences this plan's stages; it does not author them.
- **Python work (driver, allow-table, tests): `gleipnir-code`**, test-first —
  tests before implementation for every Python step (2, 3, 6). Bound to the
  `test` then `code` stages.
- **Quality review of the Python + acceptance design: `quality-reviewer`**
  (spec-review against this plan; quality review of blast radius).
- **The TypeScript plugin (step 4) and the writer-grant/path policy (step 5)
  are OPERATOR Tier-3 hand-offs.** No roster agent may write
  `.gleipnir/plugins/**` or set the Tier-3 path grant. The orchestrator must
  **stop and hand these to the operator** (via the escape hatch / `question`
  primitive), not attempt them through the `code` stage. This is the honest
  seam: the enforcement code that governs agents cannot be written by an agent.

**Sequencing protocol:**

1. Run the Link build-gate (Assemble step 1) first; **halt** if the hook
   cannot see the target-agent argument — document the compensating mechanism
   per S-1 before proceeding.
2. Deliver Python steps 2–3 test-first; confirm green before the hook exists.
3. Run the driver-invocation build-gate (Assemble step 4 preamble) **before**
   authoring the TS plugin; **halt and escalate to the operator** if the only
   realisable driver-advance path would require granting a roster agent a bash
   capability (a forbidden G-2 expansion) — do not widen the grant. Proceed to
   author the plugin only once the Tier-3 post-tool hook can host/trigger the
   driver advance in-process on the non-agent side.
4. Hand off steps 4–5 to the operator (Tier-3). The plugin consumes the
   driver-emitted allow table and reads the digest-protected bridge.
5. Run the full Stress-test suite (step 6). Ship only when all 14 checks pass
   (the 13 that passed review plus the new hook-throws-on-any-error check),
   including the untouched engine's 49/49.

**Fail-closed is the default posture of the whole slice:** anywhere the hook is
unsure — missing bridge, bad MAC, stale state, unknown agent, control state —
it **aborts the delegation**. There is no allow-by-default path, matching the
engine (`NoSuchTransition`) and the G-3.1 verifier ("any doubt refuses").

---

## Durable decision to persist (Tier-3 hand-off — I cannot write it)

This plan makes one resolution later work will depend on; it belongs in
`../decisions/`, which is Tier-3 (operator-authored). I cannot write it — I name
it for hand-off:

- **File:** `.gleipnir/decisions/engine-state-bridge.md`
- **Content to record:**
  1. **Decision:** the Python G-5 engine ↔ TypeScript hook state bridge is
     **option (b): a digest-protected state file** — the driver writes
     `PipelineState` **plus the current-state allowed-agents projection** to a
     framework-runtime path (e.g. `.gleipnir/var/run/pipeline-state.json`); the
     Tier-3 `tool.execute.before` hook reads and validates it. The allow
     projection is **re-emitted into the same file under the same MAC** (not
     embedded in the plugin), so the TS hook reads it per session — zero drift,
     no sequencing literal in TS.
  2. **Rationale:** keeps Python `TRANSITIONS` as single source of truth;
     simplest correct + fail-closed design; avoids per-call subprocess (a) and
     premature IPC (d); avoids the drift of a mirrored TS rule (c).
  3. **State advances by mechanical observation, never agent report.** No agent
     — not even the orchestrator — supplies the "stage completed" signal.
     opencode's **S-1 point-2 post-tool hook (`tool.execute.after`)**, itself
     Tier-3 non-agent code, **observes** that a delegated `task` returned and
     feeds that observed outcome to the driver's advance. The verdict passed to
     `engine.step()` derives from the mechanically observed tool outcome, not
     from narrated text — closing the self-attestation / self-narrated-sequence
     pattern G-5 and G-3.2 forbid. Honest scope: post-tool observation sees
     *"task returned cleanly" = advance-eligible*; it cannot judge work quality
     — that remains the `spec-review`/`quality` stages' verdicts, already the
     engine's contract.
  4. **Driver invocation is framework/runtime, never a roster agent.** The
     orchestrator has `bash: deny` and `gleipnir-code`'s allowlist is only
     npm/pytest/go/make, so no agent can invoke a Python driver CLI — and
     granting one a new bash capability is a **G-2 decision to avoid in the
     minimal slice**. The driver is invoked by the **Tier-3 hook/plugin layer
     (the post-tool hook) or a framework process** — the same non-agent side as
     the gate it feeds. The whole advance path (observe → advance → rewrite
     bridge) is non-agent.
  5. **Integrity:** the bridge payload (state + allow projection) is HMAC-signed
     with the G-3.1 verifier key (`GLEIPNIR_MARKER_KEY_FILE`, outside the agent
     surface); the hook validates MAC + freshness before trusting state;
     tamper/forge/stale ⇒ abort. Reuses the **keyed-HMAC + freshness core** of
     `src/gleipnir/verify/marker.py` via an **adapted `StateMarker`** — the
     tree-hash tree-binding of `Marker`/`validate` has no independent recompute
     for a state value, so that check is replaced by a state/allow-table
     binding, not reused verbatim.
  6. **Writer grant (security-critical):** the bridge path is written **only**
     by the framework driver process and is **read-only to every roster
     agent** (blanket agent deny, matching the Tier-3 wall). The bridge is
     **enforcement evidence** — classified non-agent-writable at
     Tier-3-equivalent strength, **not** a Tier-1 provenance log. An
     agent-writable bridge would make the gate forgeable — this grant is the
     load-bearing part.
  7. **Driver's own trust protection (distinct from the bridge MAC), recorded
     not-yet-closed.** The driver *holds the signing key* (it calls `mint()`),
     yet its source is agent-writable `src/` Python — so it is a potential
     forgery vector two ways: **(a) source edit** (an altered driver signs a
     wrong state and the MAC still validates) and **(b) unverified invocation**
     (advancing state from any path other than the Tier-3 hook). Intended
     defence: driver source under the **S-2 enforcement boundary**
     (agent-unwritable) and its advance entrypoint invoked **only from the
     Tier-3 hook layer**. This is **authored/hook-scoped, not yet
     boundary-closed** — it becomes structural with the S-2 mount + terminal
     closure + S-3 preflight.
  8. **Fail-open guard on the hooks.** Both the pre-tool gate and the post-tool
     observer must **throw on any unhandled error path**; a stray
     catch-and-return would silently flip fail-closed to fail-open. No
     non-throwing exit on doubt.
  9. **Minimal-slice mapping decision:** `project-mgr` and `notify` are **not**
     part of the gated pipeline in the minimal slice and are **denied while a
     pipeline is active** (chosen over an always-allow out-of-band carve-out,
     because fail-closed forbids day-one allow-holes). Revisit when their
     pipeline integration is designed.
  10. **Status:** authored/enforced-at-hook, **not yet closed** — structural
      unreachability of the hook, the key, the bridge writer, and the driver's
      source + invocation integrity (item 7) awaits the S-2 mount + terminal
      closure + S-3 preflight.

**Hygiene follow-up (not a blocker).** The prior review noted a **citation
drift**: some cross-references cite **v0.3.9** while the canonical version is
**v0.3.10**. This plan cites `DESIGN.md` without a version to avoid pinning to a
stale number; the operator should sweep the stray `v0.3.9` citations to
`v0.3.10` as a hygiene pass. The actual drift sites are:
- `src/gleipnir/engine/DESIGN.md` line ~11 (cites `gleipnir_specification_v0_3_9.md`; canonical is `v0.3.10`).
- `.gleipnir/plans/session-01-atlas-brief.md` line ~52 (same `v0_3_9` spec citation).
- `.gleipnir/plans/session-01-validation.md` (as originally noted).
Not in scope for this wire-in and not affecting any design decision above.

**Tier-doc follow-up (Tier-3 hand-off, added to the durable decision above).**
When the durable decision is persisted, the operator should also document the
new `.gleipnir/var/run/` path in the **top-level tier table** — both in
`.gleipnir/AGENTS.md` and in
`.gleipnir/decisions/gleipnir-layout-and-memory-model.md` — as a **distinct
framework-process-only writer-grant class** alongside `var/tmp/` (Tier 0):
`var/run/` carries enforcement evidence written **only** by a framework process
and read-only to every agent, whereas `var/tmp/` is disposable agent free-write.
Recording it keeps the tier docs from drifting out of sync with the new runtime
path this plan introduces.
