# Design Brief: G-5 engine revert-cap model (escalation counter)

**Stage:** `brainstorm` (owned by `gleipnir-brainstorm`). **Tier:** 0 (this
`plans/` file is the only artifact this role writes; disposable).
**Status:** operator-converged. This brief surfaces and resolves ONE material
design decision that had been made inside planning (`engine-revert-edges.md`,
§Q2) and baked into code without operator convergence — the exact process
defect the precept-10 convergence gate exists to close.

---

## Problem Statement

When a G-5 gate stage FAILs and reverts to an earlier stage, **what counts
toward escalation** to `ESCALATED` / the human gate? The engine must escalate
"at exactly N by code, deterministically" (spec G-5, line 220) and must not let
a revert *cycle* (e.g. alternating `SPEC_REVIEW↔PLAN` and `QUALITY↔CODE`) thrash
forever without escalating. The counter model that answers "what counts toward
N" is a load-bearing correctness choice with lasting consequences for how the
engine reports *why* it escalated — and it was chosen inside the planner and
implemented (`Engine._revert_count`, `DEFAULT_REVERT_BUDGET`) without being put
to the operator. This brief re-surfaces it as a first-class decision.

## Constraints

- **Determinism (G-5 / GOTCHA A1).** Escalation must fire at **exactly N** by an
  integer comparison in code — never N-1, never N+1. Routing is a `(state,
  Verdict)` table lookup; the counter is plain ints on the `Engine` instance.
- **Anti-thrash (load-bearing).** No input may loop forever without reaching
  `ESCALATED` or `HUMAN_QUESTION`. A cycle spreading reverts across *different*
  edges must still escalate deterministically. This property can only be
  guaranteed by a **whole-run (global) view** — a per-edge/per-stage-only
  counter cannot see the cycle total.
- **Fail-closed (Axiom 2 / G-3.2).** Any ambiguity refuses or escalates; absence
  of an edge stays `NoSuchTransition`.
- **stdlib-only** (`decisions/runtime-and-deps.md`): counters are ints; no deps.
- **Cross-process resume gap (common to all options).** The counter resets on
  `resume_at` today (engine `__init__.py:331`) — the bridge carries state, not
  the counter. This is an existing honest gap, not a differentiator between
  options.
- **Spec line 177 anticipates "revert occurred"** as a structural session-shape
  fact the G-4 bus is meant to observe — so revert *shape* is expected to be an
  observable signal, whether or not the engine is its authoritative source.

## Approaches Considered

### Approach A: Global revert budget (as built)

**Summary:** One `Engine._revert_count`, `+1` per backward FAIL hop, monotonic
(never reset by PASS, re-entry, or reaching a target), escalate at
`_revert_count >= _revert_budget` (default 3). Already implemented and passing.

**Tradeoffs:**
- Pro: Simplest possible "exactly N by code" — one number to reason about,
  compared in code; strongest form of the G-5 determinism claim.
- Pro: Anti-thrash guarantee holds natively — a whole-run counter catches any
  cycle shape (the T4 alternating-edge case).
- Pro: Already built, 181 tests green (advisory only — NOT a reason to choose it;
  see bias warnings).
- Con: **Blunt signal.** Cannot distinguish "one stage genuinely stuck" from
  "healthy multi-stage iteration" — the operator's original objection. The
  engine holds no per-stage data, so "why did it escalate" is only "N reverts."

**Estimated Scope:** none (built); the converged additions are (a) a documented
deferred-C seam and (b) per-hop bus-event emission — both additive, low.

**Risk:** low — the escalation trigger is done and proven; the only open risk is
signal loss, mitigated by the converged bus-logging mandate.

### Approach B: Per-stage re-entry counter

**Summary:** Count re-entries per stage; escalate when any stage's re-entry
count hits N. Measures "this specific stage is stuck."

**Tradeoffs:**
- Pro: Most human-legible escalation reason ("SPEC_REVIEW stuck 3×").
- Pro: Native per-stage signal in the engine.
- Con: **Alone it FAILS the anti-thrash property** — an alternating
  `SPEC_REVIEW↔PLAN` / `QUALITY↔CODE` cycle keeps each per-stage counter under
  its own cap (2+2, neither reaching N=4) while the pipeline thrashes forever.
  Violates "escalate at exactly N by code." To fix it you add a global backstop
  — at which point B *is* C.

**Estimated Scope:** medium (per-stage map + a global backstop = C).

**Risk:** high — as a standalone model it re-opens the exact hole the plan's
§Q2/T4 were written to close. Not viable without a global ceiling.

### Approach C: Hybrid (per-stage + global ceiling)

**Summary:** Per-stage re-entry counter (catches a stuck stage early, meaningful
reason) PLUS a higher global ceiling (backstops whole-pipeline thrash).

**Tradeoffs:**
- Pro: Richest engine signal — native "which stage is stuck" AND anti-thrash.
- Pro: Best-of-both on escalation meaningfulness.
- Con: Two counters, two caps, two "exactly N" claims to prove and keep
  consistent; escalation becomes `min(any stage hits M, global hits N)`, harder
  to reason about; more resume state; more test surface.
- Con: The anti-thrash *safety* comes entirely from its global half — the
  per-stage half is **additive signal, not additive safety**. So its extra cost
  buys diagnostics, not correctness.

**Estimated Scope:** medium-high — dual counters, dual caps, expanded tests,
more state to persist across resume.

**Risk:** medium — correct but heavier; two interacting caps invite confusion
about which fired and why.

## Decision Analysis

**Frameworks used:** Per K-3 auto-selection, *Architectural tradeoff →
Second-Order Thinking → Pre-Mortem*, plus a **Weighted Decision Matrix** (three
discrete options across multiple criteria; gut feel insufficient). This is a
near-one-way-door: cheap to reverse *mechanically*, but it becomes a Tier-3
durable decision and a cross-plan supersession authority
(`configured-optionality.md` S12(c)/§2.3), so reversal carries coordination cost.

**Weighted Decision Matrix** (0–10, cell = score×weight; higher total stronger):

| Criterion | Weight | A — Global | B — Per-stage | C — Hybrid |
|---|---|---|---|---|
| Anti-thrash / determinism (escalate at exactly N on any cycle) | 10 | 9 → 90 | 5 → 50 | 9 → 90 |
| "Exactly N" cleanliness (one number to reason about, G-5) | 9 | 10 → 90 | 6 → 54 | 4 → 36 |
| Signal meaningfulness for a human (why did we escalate?) | 9 | 4 → 36 | 9 → 81 | 9 → 81 |
| Simplicity / minimal state cost | 8 | 10 → 80 | 6 → 48 | 3 → 24 |
| Cross-process resume fidelity | 5 | 4 → 20 | 3 → 15 | 3 → 15 |
| Spec alignment (line 177 "revert occurred" distinguishable) | 6 | 5 → 30 | 8 → 48 | 8 → 48 |
| **Total** | | **346** | **296** | **294** |

**Matrix result:** A highest (346), on determinism cleanliness + simplicity —
but A scores *worst* (4/10) on signal-meaningfulness, the exact "blunt" weakness
the operator flagged. A's win is bought at the cost of the operator's objection.

**Second-Order Thinking — key insight:** The anti-thrash guarantee can only come
from a global (whole-run) view. B cannot provide it alone; C's safety comes from
its global half anyway. So the real decision is **A (global-only)** vs **C
(global + per-stage signal layer)** — B is a near-strawman that either breaks or
becomes C. The genuine tradeoff is **signal richness (C) vs one-number
determinism/simplicity (A)**. Under A, when G-4 lands, "which stage is stuck"
must be reconstructed from the bus event log (spec line 177) rather than read off
the engine — the signal is *recoverable downstream*, just not native to the
engine.

**Pre-Mortem on the leading option (A):** Top risks are the "lossy signal" family
— (#1) G-4c triage can't tell one-stuck-stage from healthy iteration; (#2)
escalation reason is "N reverts" with no *where* — plus (#4) resume resets the
counter (common to all options). **Verdict: proceed-with-A is defensible iff the
signal loss is mitigated by emitting each revert hop as a bus event**, so the
engine's simple escalation trigger doesn't become the *only* record of revert
shape, and C stays a clean forward extension rather than a rewrite.

**Bias warnings (12 detectors run; top 3):**
- ⚠️ **Sunk Cost Fallacy (HIGH — operator-flagged):** A is built and green;
  "already built / low-risk to reuse" is doing real work in A's favour. Test:
  *if choosing today with nothing built, would we still pick A?* — yes on
  determinism/simplicity, but the signal objection would still pull toward C.
  Sunk cost is inflating A's margin, not creating it.
- ⚠️ **Status-Quo Bias (HIGH):** A is the default that runs; its signal weakness
  needed active scrutiny to surface. The whole reason this gate exists is that A
  was chosen inside planning without convergence. Incumbency is zero evidence of
  correctness.
- ⚠️ **IKEA Effect (MEDIUM):** A is the in-house artifact; its flaw is easy to
  minimise ("recoverable from the log"), C's benefit easy to underweight.
- *(Below cap: Anchoring — A was first/built; Scope-Creep — mild "get everything"
  pull toward C, correctly penalised on simplicity.)*

**Recommendation (advisory):** A as the escalation *trigger*, with an explicit
deferred seam for C's per-stage *signal* layer and a mandate to emit each revert
hop as a bus event. The anti-thrash guarantee must be global; C's added value is
signal not safety, and that signal is recoverable downstream via the event the
spec already anticipates. Take A now; don't pay C's dual-counter carrying cost
until G-4c demonstrably needs per-stage granularity *in the engine*.

## Selected Approach

**Choice: Approach A — global revert budget — as the escalation TRIGGER, plus
(1) a documented deferred C seam and (2) a mandate to emit each revert hop as a
G-4 bus event.**

> **Provenance correction.** An earlier draft of this brief claimed the
> operator converged "via the precept-10 gate" during the brainstorm subagent's
> own run. That was FALSE: `gleipnir-brainstorm` is a subagent and its
> `question` cannot reach the operator, so it self-converged and mis-recorded
> its own recommendation as the operator's decision — the exact self-attestation
> failure the gate exists to prevent (this bug was found and fixed in commit
> 634a81c; convergence is now surfaced by the orchestrator, and the subagent's
> `question` is denied). The decision below IS operator-converged, but via the
> correct path: the **orchestrator surfaced the Decision Analysis to the
> operator, who chose A + deferred-C seam + bus-logging**. The recommendation
> and the operator's choice coincided — but the choice is the operator's, made
> through the orchestrator, not the subagent's self-report.

**Rationale:**
1. **Anti-thrash + "exactly N by code" are satisfied most cleanly by the global
   counter** — one monotonic int, compared in code, catches any cycle shape
   (T4). This is the load-bearing G-5 correctness point, and it is already
   proven green.
2. **The only real weakness of A is signal bluntness**, and that signal is
   *recoverable downstream*: each revert hop is emitted as a bus event (spec line
   177 "revert occurred"), so "which stage is stuck" is reconstructable from the
   log even though the engine's escalation trigger stays global. The engine need
   not be the authoritative source of revert *shape* to escalate correctly.
3. **C's extra cost buys signal, not safety** (its anti-thrash comes from its
   global half). Paying the dual-counter carrying cost now is premature until
   G-4c actually demonstrates it needs per-stage granularity in the engine.
4. **The decision is recorded so C is a clean forward extension, not a
   reversal:** global is authoritative for the *escalation trigger*; a per-stage
   *signal* layer is a deferred additive layer, mirroring the Option-B typed-enum
   seam pattern already used in `engine-revert-edges.md` §Q1.
5. B is rejected: alone it breaks anti-thrash; with a backstop it is C.

**Explicitly acknowledged bias caveat (operator saw this at convergence):** the
choice partially rests on A being already built (sunk-cost / status-quo pull,
which the operator named). Had the operator weighted "a human must see *why* it
escalated" above the matrix's weight-9, the decision would flip to C (which ties
A on anti-thrash and beats it on signal). The operator made that value judgment
and chose A + mitigations.

## Open Questions (for `gleipnir-plan`)

- **Bus-event emission point.** The G-4 bus does not exist yet. The converged
  mandate is that each backward FAIL hop is emitted as a "revert occurred" event
  carrying the *edge traversed* (from-state → to-state). The planner should treat
  this as a **flagged forward dependency on G-4**, not an in-engine change now:
  the engine's escalation logic is unchanged; the emission is wired when the bus
  lands. Confirm whether a minimal in-engine hook (a callback the driver
  supplies) is warranted now, or whether it waits entirely for G-4.
- **Deferred C seam shape.** Record (in the Tier-3 decision below) that if C is
  later adopted, the per-stage layer is *additive signal* — the global budget
  remains the authoritative escalation trigger — so C is a forward extension.
- **Cross-process resume fidelity** of the counter remains the existing honest
  gap (resets on `resume_at`); it affects all options equally and is out of scope
  for this decision. Persist the gap note; do not fake it.

## Durable-decision hand-off (Tier-3 — operator must persist)

This brief is Tier-0/disposable. The converged ruling is durable and the existing
`engine-revert-edges.md` durable hand-off must be **amended** to record it. Since
Tier-3 `decisions/` is operator-only (G-1), `gleipnir-brainstorm` cannot write
it; naming it here for the operator:

- **Path:** `.gleipnir/decisions/engine-revert-edges.md` (amend item 3, "Global
  revert budget").
- **Amendment content:** The global revert budget is the operator-converged
  escalation **trigger** (a single per-engine monotonic counter, escalate at
  exactly N — as built). A **per-stage signal layer (Option C) is deliberately
  deferred**; if ever adopted it is *additive signal only* and the global budget
  remains the authoritative trigger. Each backward FAIL hop **must be emitted as
  a G-4 "revert occurred" bus event carrying the edge traversed**, so revert
  shape ("which stage is stuck") is recoverable downstream without making the
  engine its authoritative source. This resolves the operator's "blunt: conflates
  unrelated reverts" objection by relocating the signal to the bus rather than
  changing the escalation trigger. Convergence was performed at the precept-10
  gate on this brief; A was chosen with the sunk-cost/status-quo pull explicitly
  acknowledged.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Engine escalation trigger | `src/gleipnir/engine/__init__.py` — **no change** (global budget already built; A is the trigger) |
| Engine design record | `src/gleipnir/engine/DESIGN.md` — document the deferred-C seam + the bus-emission mandate |
| G-4 bus (future) | Flagged forward dependency: emit "revert occurred" per backward hop with edge traversed (spec line 177) — wired when the bus lands, not now |
| Durable decision (Tier-3, operator only) | `.gleipnir/decisions/engine-revert-edges.md` — amend item 3 per the hand-off above |
| Related plan (no change of direction) | `.gleipnir/plans/engine-revert-edges.md` — its §Q2 global-budget choice is now operator-converged; its Option-B seam pattern is the model for the deferred-C seam |
