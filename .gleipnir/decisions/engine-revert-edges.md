# Decision: G-5 engine revert edges + global revert budget

**Status:** decided and implemented. Durable decision record (Tier-3,
operator-authored). Plan of record: `../plans/engine-revert-edges.md`
(spec-review approved, 3 rounds). Cap-model convergence:
`../plans/engine-revert-cap-model-brainstorm.md` (operator-converged via the
orchestrator — see the provenance note there).

## Why

The engine's original `TRANSITIONS` went forward-only plus self-loops on
SPEC_REVIEW/QUALITY. That cannot express the real workflow, where a failed
review / test / quality stage **reverts to an earlier stage**. This decision
adds backward revert edges and replaces the per-state loop-cap with a bounded
escalation rule.

## The revert edges (fixed-per-stage, data in TRANSITIONS)

A `Verdict.FAIL` at a gate stage routes BACKWARD to a fixed earlier stage — all
strictly backward by `PIPELINE_ORDER` index, so each is a genuine revert:

- `SPEC_REVIEW` FAIL → `PLAN`      (2 → 1)
- `TEST` FAIL → `SPEC_REVIEW`      (3 → 2)  — test-first: a failed
  test-authoring stage means the spec/plan was inadequate to test against
- `QUALITY` FAIL → `CODE`          (5 → 4)

`FAIL` is *reinterpreted* to mean "traverse this state's revert edge"; the
verdict enum stays exactly `{PASS, FAIL, NEEDS_HUMAN}` (no `SKIP`, no new
member). Revert targets are static table data, never an LLM choice
(no-text-routing / G-5). The self-loop model is **removed entirely**.

## Escalation: single global revert budget

**Operator-converged decision (Option A + seam):** escalation is triggered by a
**single per-engine monotonic revert budget** — `revert_count`, +1 per backward
FAIL hop, **never reset** (not on PASS, re-entry, or reaching a target),
escalating to `ESCALATED` at **exactly N** (`DEFAULT_REVERT_BUDGET`, overridable
via the constructor's `revert_budget`).

**Why global, not per-state/per-edge:** a cycle alternating through different
edges (spec-review↔plan, then quality↔code) keeps any per-edge counter under
its own cap forever and never escalates. A single global budget catches any
cycle shape — the load-bearing anti-thrash property (proven by the concrete-N=4
cycle-thrash test).

**The blunt-signal mitigation (part of the converged decision).** The global
budget is a deliberately *blunt* trigger: it conflates unrelated reverts and
cannot distinguish "one stage is stuck" from "healthy iteration across stages."
That signal loss is accepted **on the condition** that:

1. **Each revert hop is emitted as a G-4 bus event** ("revert occurred":
   from_state, to_state, revert_count). This preserves the per-stage "stuck"
   signal as observable data even though it is not the escalation trigger. The
   G-4 bus is not built yet, so this is a **recorded obligation / seam** (marked
   at the revert site in `src/gleipnir/engine/__init__.py` and here), to be
   wired when the bus lands. The spec already anticipates "revert occurred" as
   a bus signal (G-4b).
2. **A per-stage escalation ("hybrid C") remains a documented deferred seam** —
   not built; revisited if the blunt trigger proves inadequate in practice.

### Convergence provenance (honest)

This cap decision was first mis-recorded as "operator-converged" by the
`gleipnir-brainstorm` subagent, which cannot actually reach the operator (its
`question` surfaces only in its own sub-session) — it self-converged. That hole
was found and fixed (commit 634a81c: convergence is surfaced by the
orchestrator; the subagent's `question` is denied). The decision here IS
operator-converged, but via the corrected path: the **orchestrator surfaced the
Decision Analysis to the operator, who chose A + deferred-C seam + bus-logging**.

## Supersedes (cross-plan)

Per the plan's Q5, this decision is **authoritative on loop-cap / self-loop
semantics** and supersedes, in `../plans/configured-optionality.md` (to be
revised when that plan is built):

- **S12(c)** ("loop caps escalate at exactly N for SPEC_REVIEW and QUALITY with
  **independent counters**") → replaced by the single global revert-budget model.
- **§2.3** self-loop classification rows (`SPEC_REVIEW→SPEC_REVIEW`,
  `QUALITY→QUALITY` FAIL loops) → replaced by the revert-edge classification.
- `LOOPING_STATES` as an engine concept is **retired**.

## Known not-yet-closed

- `resume_at` resets `revert_count` to 0 on cross-process resume (same
  carried-forward gap as the old per-state counter). Documented; a later slice
  may persist the counter if cross-process budget fidelity is required.
- The G-4 bus-event emission (mitigation #1 above) is a seam until the bus
  exists.

## Verification

`src/gleipnir/engine/` (revert edges + global budget + `resume_at`), tested
in-sandbox: full repo suite 181 passed, 98% coverage (line+branch); driver 100%.
Structural guarantees preserved (GATE only via attempt_gate; HUMAN_QUESTION sole
exit; no FAIL edge into GATE). Quality-reviewed.
