# Design Brief: S4 — G-5 deterministic engine, re-expressed in TypeScript

> **Status: CONVERGED — all six decisions (D-S4-1..6) decided by the operator.**
> This is a `gleipnir-brainstorm` (subagent) artifact. Per the brainstorm skill's
> Phase-4 constraint (a subagent's `question` cannot reach the operator, L-C6),
> the six material decisions below were surfaced as a `## Decision Analysis` with
> a recommendation each, **returned to the orchestrator**, and the operator
> converged on each via the orchestrator's `question` tool (operator-via-
> orchestrator, legitimate per L-C6 — NOT self-attested). Every choice matched
> the brainstorm recommendation (no divergence). The "Selected Approach" section
> now records the converged decisions. `gleipnir-plan` plans from this converged
> brief.

## Problem Statement

Re-implement the G-5 deterministic orchestration engine — the pipeline
state-machine + judges + allow-table + state-persistence bridge — natively in
TypeScript, running **in-process** inside the pi extension, so that the
pipeline-stage sequencing (brainstorm→plan→spec-review→test→code→quality→git→
gate, plus the revert edges, the escalation sink, the human-question gate, and
the attestation-only gate edge) is enforced by deterministic TS code rather than
narrated by an LLM. The existing Python engine
(`src/gleipnir/engine/{__init__,driver,judges,allow_table,bridge}.py` +
`DESIGN.md` + their tests) is the **correctness oracle**: the TS engine must
re-earn the behaviour the Python test suite pins.

This is the "unbounded judgment compounds here" core of the framework. It is a
substantial code-level slice (unlike S3, which was convergence-only).

## The Python engine's actual shape (read directly, not summarised from docs)

The oracle is four modules + a pure-core `__init__.py`:

### `engine/__init__.py` — the pure state machine (511 lines, 49 tests)
- **`PipelineState`** (str-Enum, 10 members): `BRAINSTORM, PLAN, SPEC_REVIEW,
  TEST, CODE, QUALITY, GIT, GATE` (the 8 main-line states in `PIPELINE_ORDER`)
  plus two engine-internal control states `HUMAN_QUESTION` and `ESCALATED`
  (neither is on the main line; neither is a role-bound stage).
- **`Verdict`** (str-Enum, exactly 3 members): `PASS, FAIL, NEEDS_HUMAN`. No
  `SKIP`, no free-text. A judge returning a non-`Verdict` is `InvalidVerdict`
  (raised, never coerced) — this is the "text cannot route" guarantee.
- **`Judge`** = `Callable[[PipelineState, Mapping], Verdict]`. Pure data in,
  enum out. The router NEVER inspects `payload`; only the judge does.
- **`TRANSITIONS`** = the sequencing, as data (`dict[PipelineState,
  dict[Verdict, PipelineState]]`). Load-bearing structural absences:
  - `GIT` has **no `PASS` edge** (only `attempt_gate` reaches `GATE`);
  - `GATE`/`ESCALATED`/`HUMAN_QUESTION` are **absent as keys** (terminal / no
    routed exit — the human gate's only exit is `answer_human_question`);
  - **Revert edges** (backward `FAIL`, the only 3 `FAIL` entries):
    `SPEC_REVIEW→PLAN`, `TEST→SPEC_REVIEW`, `QUALITY→CODE`. Every other state
    has no `FAIL` edge → `NoSuchTransition` (fail-closed).
- **Escalation**: a **single global revert budget** (`DEFAULT_REVERT_BUDGET=3`,
  monotonic `revert_count`, never reset by PASS/re-entry). At exactly N reverts
  → `ESCALATED`. The load-bearing anti-thrash property (a cross-edge cycle
  `SR↔PLAN`+`QUALITY↔CODE` that per-edge counters would never catch) is pinned
  by the concrete-N=4 cycle-thrash test.
- **`Engine`** methods (the only state-movers): `step(judge, payload)`,
  `answer_human_question(answer)`, `attempt_gate(attestation)`, plus
  `resume_at(pipeline_id, state)` construction (rehydrate at a state; revert
  counter resets to 0 on resume — an honestly-flagged gap).
- **`Attestation`** (G-3.2): `(pipeline_id, status)` where `status ∈
  {ABSENT,PENDING,GREEN,RED}`. `attempt_gate` requires state==`GIT`, a real
  `Attestation` instance (not a dict/string — rejected by type), `status==GREEN`
  AND `pipeline_id` match. Any doubt refuses, state unchanged.

### `engine/allow_table.py` — the state→allowed-roles projection (105 lines)
- **`ROLE_STATES`** = the `stage-role-map.md` binding lifted into code
  (brainstorm→gleipnir-brainstorm; plan→gleipnir-plan; spec-review/quality→
  quality-reviewer; test/code→gleipnir-code; git→git-ops).
- **`ALLOW_TABLE`** is **derived** (a projection) by iterating every
  `PipelineState` and collecting bound roles — NOT a hand-maintained second
  copy. `allowed_agents_for(state)` is deny-by-default (unknown state → empty
  set). `project-mgr`/`notify` have no pipeline stage → structurally absent.
- **This is the state→role authority the enforcement layer consults.** Note it
  overlaps in *purpose* with pi's `roleTable.ts` (role→tool) but is a different
  axis: `allow_table` says *which role may act in state S*; `roleTable` says
  *which tools a role may call*.

### `engine/judges.py` — real judge factories (304 lines)
- Three parameterized factories, each taking an **injected reader** (the only
  I/O boundary — never in the pure core): `make_spec_review_judge`,
  `make_quality_judge`, `make_test_judge`.
- `SPEC_REVIEW`/`QUALITY`: parse a `quality-reviewer` transcript for anchored
  verdict-line grammars (`^SPEC-CONFORM: PASS/FAIL$`, `^BLAST-RADIUS: …$`, the
  standard `APPROVED/CHANGES REQUIRED` grammar; QUALITY recognises THREE
  grammars). Fail-closed to `NEEDS_HUMAN` on any ambiguity.
- `TEST`: maps a **mechanical exit code** (`bin/gleipnir-sandbox test --
  --collect-only`) — `0→PASS`, non-zero→`FAIL`, `None→NEEDS_HUMAN`. Uses
  `--collect-only` because the TEST→CODE edge fires *before* implementation
  exists (test-first), so only test-collectability is the honest signal.
- Judges are **payload-blind by construction**: they consume only their
  injected reader, never the engine `payload`.

### `engine/bridge.py` + `engine/driver.py` — the cross-process persistence + I/O half
- **This is the key architectural finding for S4.** `bridge.py` is a
  **cross-process state marker**: because each opencode hook call is a *fresh
  process*, the canonical pipeline state is a **persisted, HMAC-signed file**
  (`StateMarker`: `version, pipeline_state, allowed_agents, minted_at, mac`).
  It reuses `verify/marker.py`'s `load_key`/`KeyUnavailable`/fail-closed posture
  but binds the MAC to the state payload directly (no tree hash).
- `driver.py` is the **I/O + bus-emit half** that keeps the engine pure: it
  loads the key fail-closed *before* any state change, calls `Engine.step`,
  re-writes the bridge, and (if a bus is injected) emits G-4
  `RevertOccurred`/`NeedsHumanRaised`/`GateReached` events. `resume_from_bridge`
  rehydrates a `Driver` at the persisted state, validating MAC + freshness
  fail-closed (a tampered/stale/missing bridge raises `BridgeInvalid` — it never
  silently resets to BRAINSTORM).
- **Why this matters for the port:** the entire bridge/marker/cross-process
  machinery exists *because opencode runs each hook in a fresh process*. Per the
  ratified Open-Q1 decision, pi delegation is **in-process** (`createAgentSession`
  in the same address space), and the pi extension already holds **live module
  state** (`activeRole.ts` stack, `depth.ts` counter). So the in-process pi
  engine can hold `Engine` state in a live module singleton — the HMAC-signed
  file bridge may be **unnecessary for in-process correctness** and only needed
  for *restart/compaction survival*. This is decision D-S4-2 below.

## How S4 integrates with the already-built S1–S3 pi code (confirmed by reading)

- `enforcement.ts` — `tool_call` block hook. Reads `getActiveRole()` +
  `canUse(role, tool)`. **Governs WHICH TOOLS a role may call.** This is a
  DIFFERENT layer from G-5 pipeline-stage sequencing.
- `roleTable.ts` — role→tool capability data (`ROLE_ALLOW_SETS`, deep-frozen).
- `delegate.ts` — the `delegate` custom tool: builds a role-bounded
  `createAgentSession` child, depth-guarded, enforcement re-wired via
  `extensionFactories` (D6). **Governs HOW a child session is spawned.**
- `activeRole.ts` — session-scoped active-role **stack** (push/pop, in-process
  module state).
- `depth.ts` — delegation depth counter + cap (in-process module state).

**Confirmed integration boundary:** none of these five modules implements
pipeline-stage *sequencing* (which stage comes next, revert edges, escalation,
the human/attestation gates). They implement capability enforcement and
delegation mechanics. The G-5 engine is a **separate sequencing layer** that
sits *above* them: it decides the pipeline is (say) in `SPEC_REVIEW`, therefore
`allowed_agents_for(SPEC_REVIEW) = {quality-reviewer}`, and the orchestrator
should `delegate` to `quality-reviewer` next. The engine's `allow_table`
projection is the natural bridge: it constrains *which role the orchestrator may
delegate to in the current stage*, which composes with (does not replace)
`enforcement.ts`'s role→tool check. This composition point is decision D-S4-6.

## Constraints

- **Oracle-bound.** Exit criterion requires the TS engine to pass a port of the
  Python engine test suite (`test_engine.py` 49 tests is the core; plus the
  allow_table/judges/bridge/driver suites as scoped by the port decision).
- **In-process, stable delegation edge.** Per `decisions/pi-replatform-open-q1.md`,
  S4 sequences over a *stable in-process* `createAgentSession` edge. S4 must not
  reopen Open-Q1; it consumes the stability guarantee.
- **Attestation is S5, not S4.** The build-order names S5 as "G-3.1 attestation
  (HMAC marker) in TypeScript" and S5 depends on S4. The engine's `attempt_gate`
  *shape* (the GIT→GATE edge that requires a green `Attestation`) is part of the
  G-5 state machine and must be ported; the *real HMAC verification / marker
  reproduction* is S5. Boundary confirmed unambiguous (D-S4-4).
- **Router re-expression is in the exit criterion.** "The prose/config
  blast-radius router (`stage-role-map.md` Axis-1/2) is re-expressed as engine
  config" is an explicit S4 exit item (D-S4-5).
- **No scope-creep into S1–S3.** S4 must not re-touch role→tool enforcement or
  delegation mechanics (D-S4-6).
- **Test harness.** pi-package tests run via `node --experimental-strip-types
  --test test/*.test.ts` inside `bin/gleipnir-sandbox --profile pi`
  (`--network=none`). The live-model-turn gap (provider auth unreachable in the
  sandbox) is an inherited residual — engine judges that need live LLM calls
  cannot be exercised end-to-end here (interacts with D-S4-3).
- **Per L-C36:** file states above were read directly this session, not inferred
  from stale docs.

## Approaches Considered

The overarching S4 shape has three genuinely distinct strategies. The six
material sub-decisions (D-S4-1..6) are then analysed individually, because they
are separable and each needs its own operator convergence.

### Approach A: Faithful 1:1 port (mechanical translation)

**Summary:** Port `PipelineState`/`Verdict`/`TRANSITIONS`/`Engine`/`ALLOW_TABLE`
to TS with the *same* member names, transition data, judge signature, and
budget semantics, then mechanically translate `test_engine.py` (+ allow_table
tests) into `node --test` cases. The Python suite becomes the TS suite almost
line-for-line.

**Tradeoffs:**
- Pro: The exit criterion ("passes a port of the Python engine test suite") is
  met most directly and most auditably — a reviewer can diff TS tests against
  Python tests.
- Pro: The correctness argument is strongest: every load-bearing property
  (exact-N escalation, GIT-has-no-PASS, text-cannot-route, attestation refusal)
  is re-earned by a recognisably-equivalent test.
- Pro: Lowest judgment risk — the design decisions were already converged in the
  Python engine's own brainstorm (`engine-revert-cap-model-brainstorm.md`), so
  S4 does not re-open them.
- Con: TS idiom differs from Python (enums, frozen dicts, exceptions vs typed
  errors); a literal port can be non-idiomatic TS (e.g. faking Python's
  str-Enum). Requires a small, explicit "idiom mapping" table rather than
  pretending the languages are identical.

**Estimated Scope:** `pi-package/src/engine/{state,transitions,engine,allowTable,
judges}.ts` (~5 modules) + `test/engine.test.ts` (+ allowTable/judges) porting
~49+ core cases. Complexity: **medium-high** (the state machine is small; the
fidelity discipline + test port is the bulk).

**Risk:** **low** — the oracle exists and is exhaustive; the main risk is
under-porting a subtle test (e.g. the cycle-thrash `_state` repositioning trick).

### Approach B: Idiomatic TS re-expression, behaviour-parity proven separately

**Summary:** Re-express the engine in idiomatic TS (discriminated unions instead
of str-Enums, a `Result`-style return instead of exceptions, maybe a different
judge signature), and prove behaviour parity via a *fresh* TS-native test suite
that targets the same spec properties rather than translating the Python tests.

**Tradeoffs:**
- Pro: Cleaner, more idiomatic TS that fits the pi-package's existing style
  (discriminated unions, no exception-driven control flow).
- Pro: Frees the engine from Python-isms that don't map well.
- Con: **Weakens the exit criterion's auditability** — "a port of the Python
  test suite" becomes "a different suite that we claim covers the same
  properties," which is exactly the kind of unverifiable parity claim the
  framework's review gates exist to catch. A reviewer can no longer diff.
- Con: Re-opens design decisions (judge signature, error model) that were
  already operator-converged for the Python engine — risks re-litigating settled
  tradeoffs at the code stage.
- Con: Higher judgment risk with no correctness upside (the test is the arbiter;
  idiom does not make the arbiter stronger).

**Estimated Scope:** same modules, but a *new* test suite designed from the
spec. Complexity: **high** (design + parity-argument burden).

**Risk:** **medium-high** — parity is asserted rather than demonstrated by
construction; the "did we actually re-earn property X?" question becomes a
judgment call at review instead of a mechanical diff.

### Approach C: Structural 1:1 port with TS-idiomatic surface (hybrid)

**Summary:** Preserve the *semantic* structure 1:1 — identical state names,
identical `TRANSITIONS` data, identical 3-value verdict, identical global-budget
semantics, identical structural absences — but express them in the most natural
TS form (`const`-object enums or string-literal unions, a frozen transitions
record, typed error classes mirroring the Python exception names). Port the
Python tests structurally (same test *names* and *assertions*), adapting only
syntax. An explicit "Python→TS idiom mapping" table documents each surface
choice so the port is auditable despite not being byte-identical.

**Tradeoffs:**
- Pro: Keeps the strong, auditable correctness argument of A (test-for-test
  correspondence, reviewer can diff by name/assertion) while producing TS a
  pi-package maintainer would actually write.
- Pro: Does not re-open any converged design decision — semantics are frozen to
  the oracle; only syntax adapts.
- Pro: The idiom-mapping table is itself the falsifiable Design Intent for the
  cognition gate (every surface deviation from Python is named and justified).
- Con: Requires discipline to keep "idiomatic surface" from sliding into
  "behaviour change" — the mapping table must be enforced at review (the honour
  check).

**Estimated Scope:** as A, plus a short idiom-mapping section in the plan.
Complexity: **medium-high**.

**Risk:** **low-medium** — the discipline risk is real but is exactly what the
hardened-path two-pass review + cognition honour-check are designed to catch.

## Decision Analysis

> **Convergence note (operator-via-orchestrator, L-C6-legitimate — not
> self-attested).** All six analyses below were surfaced to the operator through
> the orchestrator's `question` tool and the operator converged on each,
> matching the brainstorm recommendation exactly (no divergence): D-S4-1 →
> Approach C; D-S4-2 → Option 2a; D-S4-3 → Hypothesis A; D-S4-4 → confirmed
> boundary; D-S4-5 → Option 5a; D-S4-6 → confirmed boundary + additive seam
> in-scope. The analyses are unchanged (they are the INPUT to the decision, per
> K-3); the converged choices are recorded in `## Selected Approach`.

Six material decisions. D-S4-1 is the central one (it conditions the rest); the
others are analysed individually because each is separable and needs its own
operator convergence.

### D-S4-1 — Port fidelity strategy (THE central decision)

**Framework used:** Reversibility Filter → Weighted Decision Matrix (a
multi-option architectural choice with long-lived consequences; the Reversibility
Filter classifies it first).

**Reversibility:** One-Way Door (soft). The port fidelity choice sets the shape
of the engine module + its whole test suite; reversing it after S5–S8 build on
top means re-porting the core every dependent slice consumes. Reversal cost is
high → full analysis warranted.

**Analysis results:**

| Criterion | Weight | A (1:1 literal) | B (idiomatic, sep. parity) | C (structural 1:1 + TS surface) |
|---|---|---|---|---|
| Exit-criterion auditability ("passes a *port* of the suite") | 10 | 10 → 100 | 4 → 40 | 9 → 90 |
| Correctness confidence (re-earns load-bearing properties) | 10 | 9 → 90 | 6 → 60 | 9 → 90 |
| Does NOT re-open converged decisions | 8 | 10 → 80 | 3 → 24 | 9 → 72 |
| TS idiom / pi-package maintainability | 6 | 4 → 24 | 10 → 60 | 8 → 48 |
| Implementation + review cost (higher=cheaper) | 5 | 7 → 35 | 3 → 15 | 6 → 30 |
| **Total** | | **329** | **199** | **330** |

**Recommended (D-S4-1): Approach C (structural 1:1 port with TS-idiomatic
surface).** A and C are within one point; both crush B. C edges A by producing
maintainable TS without sacrificing auditability, *provided* the idiom-mapping
table is mandatory and review-enforced. If the operator prefers to eliminate all
idiom-discipline risk, A is a fully acceptable fallback (identical correctness
argument, less-idiomatic TS). **The decision the operator must make: C vs A**
(B is not recommended — it weakens the exit criterion for no correctness gain).

**Caveat:** the winner scores lowest on nothing critical; C's only weak axis
(idiom-discipline) is mitigated by the mandatory mapping table + honour check.

### D-S4-2 — Engine state persistence mapping (in-process singleton vs signed-file bridge vs appendEntry)

**Framework used:** Second-Order Thinking (architectural, long-term
consequences) + Pros-Cons-Fixes.

**The finding driving this:** the Python `bridge.py`/`driver.py` HMAC-signed-file
machinery exists *because opencode runs each hook in a fresh process*. Pi
delegation is **in-process** (Open-Q1 ratified), and the extension already holds
live module state. So there are three options:

- **Option 2a — In-process module singleton.** Hold the `Engine` in a live
  module (like `activeRole`/`depth`). No file, no HMAC, for in-session
  correctness.
- **Option 2b — Signed-file bridge (port `bridge.py` faithfully).** Keep the
  HMAC-signed state file for tamper-evidence + cross-restart survival.
- **Option 2c — `pi.appendEntry()` session-persisted state.** Use pi's
  documented restart-surviving primitive to persist engine position.

**Second-order analysis:**
- 2a near-term: simplest, matches the existing in-process modules. Far-term: the
  engine position is lost on a pi session restart or a `session_before_compact`
  — the pipeline "forgets" it was at `QUALITY`. **Is that acceptable for S4?**
  The S4 exit criterion is about *deterministic sequencing + test parity*, not
  restart survival. Restart survival is arguably an S4-or-later *separate*
  concern (the Python `resume_at`/`resume_from_bridge` was its own slice).
- 2b near-term: faithful port, but the HMAC key machinery *is S5's job*
  (G-3.1 attestation/marker in TS). Porting the signed bridge in S4 **pulls S5
  forward** and re-opens the "reproduce Python golden vectors vs re-specify"
  decision (build-order [ASSUMPTION-3]) prematurely. Far-term: tamper-evidence
  on state, but at the cost of S4/S5 boundary bleed.
- 2c near-term: uses the pi-native restart-survival primitive the brief
  identified; far-term: clean separation (state position persists, HMAC signing
  is a *separate* S5 concern that can wrap it later).

**Key insight:** persistence *survival* (2c/appendEntry) and persistence
*integrity* (2b/HMAC) are **separable**, and the Python design fused them only
because the opencode fresh-process model forced state to be re-read (and
therefore forgeable) every hop. In-process, S4 can adopt the **live singleton
for correctness now**, and treat *signed* restart-survival as an explicit seam
that S5 (which owns HMAC in TS) closes.

**Recommended (D-S4-2): Option 2a (in-process module singleton) as the S4
engine-state home, with restart/compaction survival explicitly DEFERRED to a
named seam that S5 closes (signed via S5's TS HMAC marker, optionally over
`pi.appendEntry`).** This keeps S4 focused on sequencing + parity, does not pull
S5's HMAC machinery forward, and matches the ratified in-process model.
`resume_at`-style rehydration *shape* can still be ported (it's pure-core) so the
seam is a wiring point, not a redesign. **Operator must confirm: is losing engine
position on restart/compaction acceptable within S4's scope** (recommended:
yes, defer to S5 seam), or must S4 persist across restart now (→ 2c, and if
*signed* persistence is required, that pulls S5 forward)?

**Bias check:** ⚠️ *Sunk Cost Fallacy (candidate, ruled out):* one might port
`bridge.py` "because it's already written and tested" — but per the detector,
past investment is not a reason; the fresh-process rationale that motivated it
does not hold in-process. Recommending 2a over 2b is the sunk-cost-resistant
call.

### D-S4-3 — Judge re-expression (port shapes now, live judging later?)

**Framework used:** Hypothesis-Driven Analysis (uncertainty about what is
testable in the sandbox).

**Hypothesis A:** *If S4 ports the judge factory SHAPES + their transcript/
exit-code grammars (pure functions of an injected reader), and leaves the actual
reader wiring (live `quality-reviewer` transcript fetch / real sandbox
subprocess) to the caller edge, then the engine's judged transitions are fully
test-covered with fake readers, because the Python judges are already
payload-blind pure functions of an injected reader.*
- Key assumption: the grammars (SPEC-CONFORM/BLAST-RADIUS/standard; exit-code
  mapping) port faithfully and are testable with fixture strings/ints.
- Evidence for: `judges.py` is *explicitly* designed this way — the reader is
  "the ONLY I/O boundary and is supplied by the caller/harness edge." Tests use
  fixed strings. The `--network=none` live-model gap (S2/S3 residual) does not
  affect grammar tests (they don't call a model).
- Evidence against: the `TEST` judge's real reader runs
  `bin/gleipnir-sandbox test -- --collect-only` as a subprocess — that subprocess
  wiring may or may not be exercisable in the pi sandbox, but the *judge* (int→
  Verdict) is trivially testable regardless.
- Confidence: **High.**

**Hypothesis B:** *If S4 also wires real live judging (real reviewer transcript,
real subprocess), then it inherits the live-model-turn gap and cannot fully
test end-to-end in `--network=none`.*
- Confidence: **High** that this gap exists; wiring real judging into S4 buys
  little and imports the known residual.

**Recommended (D-S4-3): Port the judge SHAPES + grammars now (Hypothesis A);
defer real reader wiring (live transcript fetch, real sandbox subprocess) to the
caller/integration edge, tested with fake readers exactly as Python does.** This
matches the oracle's own design and sidesteps the sandbox network limit.
**Operator must confirm** the judge *grammars* are in-scope for S4 (recommended:
yes — they're part of the engine's judged-transition contract) while *live
judging integration* is out (recommended: yes, defer).

**Bias check:** ⚠️ *Scope Creep (candidate, ruled out):* wiring real judging
"while we're in here" would expand S4 to import the live-model residual — the
detector says force the narrower choice. Recommending shapes-only resists it.

### D-S4-4 — Attestation dependency boundary (S4 vs S5)

**Framework used:** Reversibility Filter (fast-track — the boundary is
documented, this is a confirm-not-decide).

**Reversibility:** Two-Way Door for the *shape*; the boundary itself is already
set by the build-order.

**Analysis:** The build-order is unambiguous: S5 = "G-3.1 attestation (HMAC
marker) in TypeScript," and S5 *depends on* S4 ("S4 (engine emits the attested
transitions)"). The G-5 state machine's `attempt_gate` edge (GIT→GATE requires a
`GREEN` `Attestation` whose `pipeline_id` matches) is part of the **engine
contract** and MUST be ported (the `TestAttestationGate` cases are core oracle
tests). But the `Attestation` is a **plain value object** the caller supplies;
the Python `DESIGN.md` explicitly lists "No real CI/attestation fetch" as an
engine-core non-goal. So S4 ports:
- ✅ `Attestation` value type + `AttestationStatus` enum,
- ✅ `attempt_gate`'s refusal logic (type/status/pipeline_id checks, state
  unchanged on refusal),
- ✅ the `TestAttestationGate` suite (green accepted; absent/pending/red/wrong-id/
  dict-lookalike/string all refused).

S4 does NOT build:
- ❌ real HMAC marker verification (that's `verify/marker.py`'s TS port = **S5**),
- ❌ golden-vector reproduction (S5's [ASSUMPTION-3]),
- ❌ any real CI/verifier fetch.

**Recommended (D-S4-4): Confirmed boundary — port the `attempt_gate` edge +
`Attestation` VALUE type + its refusal tests (engine contract); build NO real
HMAC/marker/fetch (S5).** The boundary is unambiguous; surfacing it only to
confirm no fuzziness. **Only fuzzy point to flag:** the Python `driver.py`'s
`attempt_gate` wrapper emits a G-4 `GateReached` bus event and the bridge is
signed — but the *bus* is S8 and the *signing* is S5, so the S4 engine's
`attempt_gate` returns the `GATE` `StepResult` with **no bus, no signing** (both
are later-slice wire-ins, exactly as the Python engine core has no bus import).

### D-S4-5 — "Prose/config router re-expressed as engine config" (does S4 block on the opencode→pi literal supersession?)

**Framework used:** Second-Order Thinking + Pros-Cons-Fixes (this is the
subtle interaction the delegation flagged).

**The precise question:** the exit criterion requires the `stage-role-map.md`
Axis-1 disqualifier set `X` and Axis-2(a) enforcement-path set `E` (the
blast-radius router) to be "re-expressed as engine config." But those literals
are **opencode-shaped** (`.gleipnir/agents/**`, `opencode.jsonc`, `.github/**`,
`hooks/**`, …), and per S2's D-D convergence, superseding them to `.pi/*`-shaped
equivalents is **explicitly DEFERRED** (a separate Tier-3 operator act, not yet
done). Does S4 *block* on that supersession?

**Two candidate readings:**
- **Option 5a — Re-express the router MECHANISM (engine-config shape + routing
  logic) now, with the current/representative path sets as config DATA, and
  leave the opencode→pi literal supersession as the separate deferred Tier-3
  act.** The engine gains a deterministic classifier: given a plan's touched-path
  set `P`, compute Axis-1 eligibility and Axis-2 hardened/light routing with **no
  per-plan LLM judgment** (the stage-role-map's own stated goal). The path
  literals are *configuration data* the classifier consumes; which literals
  (opencode vs pi) is orthogonal to whether the *mechanism* is correct.
- **Option 5b — Block S4 until the Tier-3 literal supersession happens**, so the
  router is expressed against final `.pi/*` literals.

**Second-order analysis:**
- 5a near-term: S4 delivers a tested, deterministic router mechanism; the literal
  set is a config constant that a later Tier-3 act swaps. Far-term: clean — the
  *mechanism* (the hard part: Axis-1 disqualifier logic, Axis-2(a) path match +
  Axis-2(b) content-pattern match, hardened-vs-light routing) is proven once and
  is literal-agnostic. The supersession becomes a data edit, not a re-port.
- 5b near-term: couples S4's completion to an unrelated Tier-3 decision that S2
  deliberately deferred — reintroducing a dependency the roadmap severed.
  Far-term: no benefit, because the mechanism would be identical either way.

**Key insight (the SRP argument):** the router *mechanism* (path-set → routing
decision) and the *path literals* (which paths are enforcement-bearing) are two
responsibilities. S4 owns the mechanism; the Tier-3 supersession owns the
literals. Folding the literal decision into S4 violates the same separation the
whole roadmap is built on and would make S4 block on a deferred convergence.

**Recommended (D-S4-5): Option 5a — S4 re-expresses the router MECHANISM as
deterministic engine config/logic, parameterised over a path-set that S4 seeds
with representative/placeholder literals (or the current opencode literals
clearly marked "superseded at the Tier-3 pi cutover"); the actual opencode→pi
literal supersession remains the separate deferred Tier-3 act. S4 does NOT block
on it.** Fix for the one con (representative literals could drift): make the path
sets a single named config constant with a comment binding it to the pending
Tier-3 supersession, and add a test that the *routing logic* (not the specific
literals) is correct, so a later literal swap is a data change with an unchanged,
still-green mechanism test.

**Bias check:** ⚠️ *Scope Creep (candidate, ruled out):* 5b would expand S4 to
absorb a deferred Tier-3 decision — the detector says don't broaden scope to
avoid a clean separation. 5a is the boundary-respecting call.

### D-S4-6 — Scope boundary vs S1–S3's already-built enforcement (confirm the layering)

**Framework used:** Pros-Cons-Fixes (a confirm-the-boundary decision, not a
multi-option tradeoff).

**Analysis:** The G-5 engine (pipeline-stage sequencing) is a **distinct layer**
from role→tool enforcement (`enforcement.ts`/`roleTable.ts`) and delegation
mechanics (`delegate.ts`/`depth.ts`/`activeRole.ts`). Reading confirmed none of
the five S1–S3 modules does stage sequencing. The one *composition* point is the
engine's `allow_table` projection: the engine knows the current stage → therefore
which role the orchestrator may `delegate` to next. That constrains delegation
*targets by stage*, composing with (not replacing) `enforcement.ts`'s role→tool
check.

- Pro (of a clean boundary): S4 adds a new `engine/` layer and a thin
  composition seam (stage→allowed-role feeding the orchestrator's delegate
  choice); it does not edit the frozen `roleTable.ts` or the `tool_call` hook.
- Con: the composition seam (how the engine's current-stage allow-set actually
  reaches the orchestrator's delegate decision) is genuinely new wiring and
  could tempt an implementer to modify `delegate.ts`/`enforcement.ts`. **Fix:**
  the plan must state the seam as *additive* (the engine exposes
  `allowedRolesFor(state)`; the orchestrator consults it before `delegate`), and
  the cognition honour-check + blast-radius pass must flag any diff to the S1–S3
  modules as an Important divergence.

**Recommended (D-S4-6): Confirmed — S4 is PURELY the pipeline-stage-sequencing
layer (next-stage, revert edges, escalation, human/attestation gates, the
allow_table projection, the blast-radius router) + a thin ADDITIVE composition
seam. S4 does NOT modify `roleTable.ts`, `enforcement.ts`, `delegate.ts`,
`depth.ts`, or `activeRole.ts`.** Any change to those five is out-of-scope
scope-creep to be caught at review. **Operator confirms** the composition seam
(engine stage → orchestrator delegate-target constraint) is in-scope for S4 as
*additive wiring* (recommended: yes), vs deferred entirely (would leave the
engine computed-but-unconsumed — acceptable but less useful).

### Bias warnings summary (across all six)

- ⚠️ **Sunk Cost Fallacy** (D-S4-2): resisted — do not port `bridge.py` merely
  because it exists; its fresh-process rationale is gone in-process.
- ⚠️ **Scope Creep** (D-S4-3 and D-S4-5): resisted twice — shapes-not-live-judging,
  and mechanism-not-literals. Both force the narrower boundary.
- ⚠️ **IKEA Effect** (mild, D-S4-1): the Python engine is "ours" and beloved;
  Approach C/A honour it, but the recommendation rests on the *exit criterion*
  (auditable port) not on attachment. Noted, not decisive.
- No other detectors triggered.

## Selected Approach

**CONVERGED by the operator (via the orchestrator's `question` tool;
operator-via-orchestrator, L-C6-legitimate — not self-attested). All six choices
matched the brainstorm recommendation; no divergence.** These are the decided
choices `gleipnir-plan` plans from:
- D-S4-1: **CONVERGED → Approach C** — structural 1:1 port with a TS-idiomatic
  surface (identical state names, `TRANSITIONS` data, 3-value verdict,
  global-budget semantics, and structural absences; TS-natural surface with a
  mandatory, review-enforced Python→TS idiom-mapping table as the falsifiable
  Design Intent). (A was the acceptable fallback; not taken.)
- D-S4-2: **CONVERGED → Option 2a** — in-process module singleton is the S4
  engine-state home; restart/compaction survival is explicitly DEFERRED to a
  named seam that S5 closes (signed via S5's TS HMAC marker, optionally over
  `pi.appendEntry`). The pure `resume_at` rehydration shape is still ported as
  that seam's wiring point.
- D-S4-3: **CONVERGED → Hypothesis A** — port the judge factory SHAPES + their
  transcript/exit-code grammars now (pure functions of an injected reader,
  tested with fake readers as Python does); live reader wiring (real
  `quality-reviewer` transcript fetch, real sandbox subprocess) is DEFERRED to
  the caller/integration edge.
- D-S4-4: **CONVERGED → confirmed boundary** — port the `attempt_gate` edge +
  the `Attestation` VALUE type + `AttestationStatus` enum + the
  `TestAttestationGate` refusal suite (the engine contract). Build NO real HMAC
  marker verification, NO golden-vector reproduction, NO CI/verifier fetch —
  those are S5. The S4 `attempt_gate` returns the `GATE` `StepResult` with no
  bus (S8) and no signing (S5).
- D-S4-5: **CONVERGED → Option 5a** — re-express the blast-radius router
  MECHANISM (Axis-1 disqualifier `X`, Axis-2(a) enforcement-path `E`, Axis-2(b)
  content-pattern `G`, hardened/light routing over touched-path set `P`) as
  deterministic engine config/logic now, parameterised over a single named
  path-set config constant seeded with the current/representative literals
  marked "superseded at the Tier-3 pi cutover." The opencode→pi literal
  supersession remains the separate DEFERRED Tier-3 act; **S4 does NOT block on
  it.**
- D-S4-6: **CONVERGED → confirmed boundary + additive seam in-scope now** — S4
  is PURELY the pipeline-stage-sequencing layer (next-stage, revert edges,
  escalation, human/attestation gates, the allow_table projection, the
  blast-radius router) PLUS a thin ADDITIVE composition seam
  (`allowedRolesFor(state)` consulted by the orchestrator before `delegate`).
  ZERO edits to the five S1–S3 modules (`roleTable.ts`, `enforcement.ts`,
  `delegate.ts`, `depth.ts`, `activeRole.ts`); any diff to them is an Important
  divergence caught at review.

## Open Questions (for `gleipnir-plan`, after convergence)

- **Test-port completeness scope:** the core is `test_engine.py` (49). Does the
  port also cover `test_allow_table.py` (SSOT/parity), `test_judges.py`, and the
  `driver`/`bridge` suites? Recommendation implicit in D-S4-2/3: port
  allow_table + judges-grammar suites; port `driver`/`bridge` only insofar as the
  in-process singleton needs them (much of `bridge`/`driver` is opencode
  fresh-process + bus/HMAC machinery deferred to S5/S8). `gleipnir-plan` to draw
  the exact test-port manifest.
- **Idiom-mapping table (if D-S4-1=C):** the plan must include the explicit
  Python→TS surface-mapping table as its falsifiable Design Intent.
- **Composition seam signature (D-S4-6):** exact shape of how the engine's
  current-stage allowed-role set reaches the orchestrator's delegate decision —
  additive only.
- **Router config location:** where the Axis-1 `X` / Axis-2 `E` literals + the
  content-pattern set `G` live as engine config, and the comment binding them to
  the pending Tier-3 pi supersession.
- **`resume_at` shape:** port the pure `resume_at` construction (state
  rehydration) as the seam S5 wires signed persistence into, even though S4
  itself uses the in-process singleton.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Engine core (state machine) | `pi-package/src/engine/state.ts`, `transitions.ts`, `engine.ts` (PipelineState, Verdict, TRANSITIONS, Engine, StepResult, typed errors, revert budget, attempt_gate, resume) |
| Allow-table projection | `pi-package/src/engine/allowTable.ts` (ROLE_STATES lifted from stage-role-map; derived ALLOW_TABLE; `allowedRolesFor`) |
| Judge factories + grammars | `pi-package/src/engine/judges.ts` (spec-review/quality/test factories, anchored-line grammars, exit-code map; injected-reader boundary) |
| Attestation value type | in `engine.ts` or `attestation.ts` (Attestation, AttestationStatus) — VALUE only, no HMAC (S5) |
| Blast-radius router | `pi-package/src/engine/router.ts` (Axis-1 `X`, Axis-2(a) `E`, Axis-2(b) `G`, hardened/light routing over touched-path set `P`; literals as pending-supersession config) |
| Composition seam (additive) | thin wiring so orchestrator consults `allowedRolesFor(state)` before `delegate` — NO edits to enforcement/roleTable/delegate |
| Tests (the oracle port) | `pi-package/test/engine.test.ts` (+ allowTable/judges/router) — `node --experimental-strip-types --test`, run under `bin/gleipnir-sandbox --profile pi` |
| Restart-survival seam (DEFERRED to S5) | named seam only: signed persistence over `pi.appendEntry`, wired by S5's TS HMAC marker |

## Decision Frameworks Note
Frameworks applied: Reversibility Filter, Weighted Decision Matrix (D-S4-1),
Second-Order Thinking (D-S4-2, D-S4-5), Hypothesis-Driven Analysis (D-S4-3),
Pros-Cons-Fixes (D-S4-4, D-S4-6). Bias detectors run across all six; Sunk Cost,
Scope Creep (×2), and a mild IKEA Effect surfaced and are addressed above. Per
the K-3 binding, these analyses are the INPUT to the operator's convergence, not
the decision.
```
