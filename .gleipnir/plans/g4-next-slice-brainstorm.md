# Design Brief: G-4 next slice — engine-computed terminal/interoceptive event kinds

**Status:** OPERATOR-CONVERGED (precept-10 gate). Tier-0 session artifact
(disposable). Produced by `gleipnir-brainstorm`; converged via the
orchestrator-surfaced decision gate (this Decision Analysis → operator
convergence via the orchestrator's `question` tool). Next stage:
`gleipnir-plan` runs ATLAS Architect/Trace on this brief to produce a buildable
plan. (Convergence convention matches `prose-config-only-track-brainstorm.md`
and `s2-activation-brainstorm.md`.)

## Problem Statement

G-4 ("the guard's sense is not blindable") has **two slices already built** and
several interlocking gaps remaining. The task is to pick the single
highest-value, **buildable-now** next slice — untangling which gap unblocks the
most downstream work without depending on unbuilt inputs (S-2, signal history,
an unbuilt live emit path). The problem is *prioritisation under a hard
buildability gate*, not "how to build G-4."

## What's already built (context, verified against source)

- **SLICE 1 — typed event bus** (`.gleipnir/decisions/g4-bus.md`;
  `src/gleipnir/bus/{events,emit}.py`). A frozen `Event` envelope (the eight
  G-4a fields + `version`/`sequence`/`kind`) composed with a **typed per-kind
  payload** — NOT a prose-parsed dict. `EventBus.emit()` appends one JSONL line
  per event to Tier-1 `.gleipnir/logs/<session_id>.jsonl`; degrade-not-raise.
  **One consumer wired:** the engine revert-hop producer (`RevertOccurredEvent`).
- **SLICE 2 — ledger honesty skeleton** (`.gleipnir/decisions/g4d-ledger.md`;
  `src/gleipnir/ledger/{metric,reduce,ratetable,reconcile}.py`). Distinct
  `Measured`/`Estimated`/`Gap` types (a `Gap` is not `Measured(0)`);
  `reduce(session_log) -> LedgerReport` reads the bus via the typed read door;
  reconciliation. **One real metric:** the revert-derived baseline. Every other
  metric is an explicit `Gap`, never a fabricated zero.

**Two source facts that decided the ranking (verified this session):**

1. **`EventKind` currently has exactly ONE member** — `REVERT_OCCURRED`
   (`src/gleipnir/bus/events.py:59`); `_PAYLOAD_CLASSES` has one row
   (`events.py:115-116`). Adding a kind is a clean, low-friction extension.
2. **There is NO live emit call site.** Every `Driver(..., bus=…)` construction
   is in tests (`tests/test_driver_emits_revert.py`,
   `tests/test_armed_run_dogfood.py`). The live `tool.execute.after` advance
   hook (**Seam 7**, parked in `engine-wire-in.md` / `armed-run-dogfood.md`) is
   unbuilt — so *no live session emits anything to the bus today*. The revert
   producer is test/dogfood-exercised only. This constraint is inherited by any
   slice that adds emission and is **accepted** (see Selected Approach).

## Candidates Considered

1. **New bus event kinds — terminal/interoceptive + token-provenance ingress.**
   The ledger's named plug-in point for its deferred MEASURED metrics.
   *Partially buildable now:* engine-computed terminal facts (iteration-cap-hit,
   escalation) ride the same in-process driver path the revert event already
   uses; **token-provenance ingress is blocked** (no in-process token source).
2. **Observer / a real second consumer.** A reader over the typed stream.
   *Buildable* (nothing blocks a Python reader) but low value now — with no live
   emit path it observes an empty-or-test-only stream.
3. **TS-side event emission (post-tool-hook telemetry).** Real TS plugin surface
   exists (`.gleipnir/plugins/*.ts`, `tool.execute.after` confirmed in
   `hook-probe-findings.md`), but there is **no TS bus-writer** — needs
   cross-language JSONL duplication or a new Python emit-CLI; touches
   enforcement-adjacent Tier-3 plugin space (hardened-path review).
4. **G-4c novelty triage.** Spec sequences it LAST; needs accumulated signal
   history; E-3 signal-quality seam open. **Premature.**
5. **Per-event integrity (reserved `version` slot).** Only matters if the ledger
   makes suppression an economic-gaming vector → gated on cost → gated on S-2.
   **Premature.**

## Decision Analysis

**Decision type:** Prioritisation (what to build first / defer) with a hard
buildability gate. **Framework:** RICE Scoring (primary, per the prioritisation
row of the auto-selection table), preceded by a buildable-now eligibility gate
(Reversibility-Filter-style disqualifier), cross-checked with a Weighted
Decision Matrix on the four named axes (value-now, buildability-now,
dependency-unblocking, blast-radius). Rationale: the ask is multi-criteria
prioritisation, and RICE's Confidence dimension forces an honest discount on the
blocked candidates.

### Eligibility gate (buildable-now vs. blocked) — applied first

| Candidate | Buildable now? | Blocking dependency |
|---|---|---|
| **1. New event kinds (terminal/interoceptive + token ingress)** | **PARTIALLY — the highest-value half is buildable now** | Engine-computed terminal facts (iteration-cap-hit, escalation, retry) ride the *same* driver path the revert event already uses — no new dependency. Token-provenance ingress is blocked (no in-process token source; needs the post-tool/model-usage surface). |
| **2. Observer / real second consumer** | **YES (Python reader)** | None to build it; but it can only observe what's emitted — today, revert events in tests only. Live value gated on Seam 7. |
| **3. TS-side event emission** | Feasible but **higher-cost / cross-cutting** | No TS bus-writer; cross-language format duplication or a new Python emit-CLI; touches Tier-3 enforcement-adjacent plugin space (hardened-path review). |
| **4. G-4c novelty triage** | **NO — premature** | Needs accumulated signal history; spec sequences it LAST; E-3 open. |
| **5. Per-event integrity** | **NO — premature** | Contingent on cost becoming a gaming vector → S-2-gated. |

### RICE scoring

Effort in relative person-days; Impact on the 0.25–3 scale; Confidence as the
honesty discount. Blocked candidates scored for completeness with honest
Confidence discounts.

| Candidate | Reach (downstream consumers unblocked) | Impact | Confidence | Effort | RICE |
|---|---|---|---|---|---|
| **1. New event kinds (iteration-cap / escalation-terminal first; retries next)** | 3 | 3 | 90% | 2 | **4.05** |
| **2. Observer / second consumer** | 1 | 1 | 70% | 2 | 0.35 |
| **3. TS-side emission** | 2 | 2 | 55% | 4 | 0.55 |
| **4. Novelty triage (G-4c)** | 1 | 2 | 20% | 5 | 0.08 |
| **5. Per-event integrity** | 1 | 1 | 25% | 2 | 0.125 |

**Ranked:** **1 ≫ 3 > 2 > 5 > 4.**

### Weighted Decision Matrix cross-check (the four named axes)

Weights: value-now 9, buildability-now 10, dependency-unblocking 9, low
blast-radius/complexity 6. Scores 0–10, shown as score×weight.

| Criterion | W | C1 New kinds | C2 Observer | C3 TS emit |
|---|---|---|---|---|
| Value-now (honest new signal) | 9 | 8→72 | 4→36 | 5→45 |
| Buildability-now (Python, not gated) | 10 | 8→80 | 9→90 | 4→40 |
| Dependency-unblocking (most downstream) | 9 | 9→81 | 3→27 | 5→45 |
| Low blast-radius / complexity | 6 | 7→42 | 8→48 | 4→24 |
| **Total** | | **275** | **201** | **154** |

Both frameworks agree: **Candidate 1 leads.** The matrix surfaces the real
tension — Candidate 2 (observer) wins on *pure buildability* but loses badly on
value/unblocking, because with no live emit path it would observe an
empty-or-test-only stream. That is the trap named for the operator.

### Recommendation (advisory input to convergence — resolved by the operator)

Build **Candidate 1, scoped to the engine-computed terminal/interoceptive kinds
first** (`ITERATION_CAP_HIT` / `ESCALATION` and `RETRY`-class events emitted
from the driver at terminals it already reaches in-process), plus matching typed
`reduce()` branches so the ledger's `iterations` and `retries` seams flip from
`Gap` to `Measured`. It is buildable now (Python-side, riding the exact driver
emit path the revert event already proves out), directly unblocks the ledger's
own named plug-in point, produces real MEASURED signals, and is low
blast-radius. **Scope OUT:** token-provenance ingress (blocked), cost
(S-2-gated), effort attribution (needs two-ingress provenance).

### Bias check (12 detectors run; top 3 surfaced)

- ⚠️ **IKEA Effect / "build the technically-interesting piece."** Candidate 3
  (cross-language TS emission) and Candidate 5 (crypto integrity) are the shiny
  slices; they are down-ranked on value/unblocking, not on interest. Flag: if
  C3/C5 start to feel attractive, it should be on merit, not novelty.
- ⚠️ **Scope Creep Bias.** The pull is "build all of G-4 / the whole economic
  chain." The recommendation resists this by scoping to engine-computed terminal
  kinds only and deferring token/cost/effort. If the slice expands back toward
  "all measured metrics at once," that is the bias re-asserting — hold the line.
- ⚠️ **Sunk Cost / Status Quo (mild).** "We built the bus + ledger, so keep
  feeding them" is correct *here* (the plug-in point is real and named) but is
  justified on **future value** (new honest metrics, cheaply), not prior
  investment. (Others detected, lower confidence: Anchoring on the candidate
  ordering; Confirmation toward C1 — mitigated by scoring blocked candidates
  explicitly rather than dismissing them.)

## Selected Approach

> ### ⚠️ RE-SCOPE (operator-reconsulted) — READ THIS FIRST; supersedes the specific metrics below
>
> **Status:** OPERATOR-RECONSULTED and RE-CONVERGED at the precept-10 gate (via
> the orchestrator's `question` tool), during ATLAS planning. The *choice*
> (Candidate 1 — buildable-now, driver-observable terminal-event kinds + matching
> ledger `Measured` metrics) stands; the **specific metrics named in the original
> converged text below are CORRECTED**. The original text is **preserved
> un-deleted and marked SUPERSEDED** so the history is intact (same convention as
> other corrected briefs). Concrete decisions live in the plan
> `.gleipnir/plans/g4-terminal-events.md` (see its D1 / D6 / D8).
>
> **Premise-error finding (verified against actual engine source during ATLAS
> Trace).** The original brief's premise was partly WRONG:
> - **The engine has NO iteration or retry concept.** A `FAIL` routes *backward*
>   = a **revert**, already emitted as `RevertOccurredEvent`. The self-loop /
>   `LOOPING_STATES` model was **retired**. The only cap is the **global revert
>   budget**, whose exhaustion is the **escalated revert** — already emitted as
>   `RevertOccurredEvent(escalated=True)`.
> - Therefore the two seams the original text said C1 would flip — the ledger's
>   **`iterations` and `retries` `Gap`→`Measured`** — are **NOT buildable**
>   without first adding an iteration/retry concept to the engine, which is a
>   **separate, larger slice** (an engine-concept change, not a bus/ledger
>   extension).
> - **`escalation` is already captured** by `RevertOccurredEvent.escalated` —
>   adding a separate escalation event would be **redundant**.
>
> **Operator re-convergence (the buildable-now substitute).** Build two
> **genuinely-new, buildable-now, driver-observable terminal-event kinds** the
> planner found instead:
> - **`NEEDS_HUMAN_RAISED`** — a human-question was raised at a terminal the
>   driver already reaches. Promotes the new Measured metric **`human_question_count`**.
> - **`GATE_REACHED`** — the pipeline reached the gate / terminal. Promotes the
>   new Measured metric **`gate_reached_count`**.
>
> These are honest new `Measured` metrics off the same driver emit path the
> revert event already uses (engine stays pure). The IN-scope emit-site pattern,
> the SCOPED-OUT deferrals (token / cost / effort), and the "test-exercised only
> until Seam 7" known constraint below all still apply unchanged.
>
> **`iterations` / `retries` remain honest deferred `Gap`s with CORRECTED
> reasons.** They are not "no XEvent kind on the bus yet" — they are "the engine
> has no iteration/retry *concept* to source them from." Sourcing them needs a
> **separate engine-concept slice**, explicitly OUT of scope here, which
> **returns through the brainstorm gate** if wanted (it is a material design
> decision, not a mechanical extension).

**~~SUPERSEDED (metrics corrected by the re-scope above; preserved for
history)~~ — Choice: Candidate 1 — new engine-computed terminal/interoceptive
event kinds + matching ledger reduce branches. OPERATOR-CONVERGED** at the
precept-10 gate (via the orchestrator's `question` tool), matching the advisory
recommendation.

**Scoped to (IN):** engine-computed terminal/interoceptive kinds emitted from
the **driver** at terminals it **already reaches in-process** — ~~specifically
**iteration-cap-hit, escalation, and retry-class events** — plus matching typed
`reduce()` branches so the ledger's **`iterations` and `retries` seams flip from
`Gap` to `Measured`**~~ **[SUPERSEDED — these specific kinds/metrics were
corrected by the RE-SCOPE note above: the engine has no iteration/retry concept
and escalation is already captured by the escalated revert. The buildable-now
substitute is `NEEDS_HUMAN_RAISED` + `GATE_REACHED` → `human_question_count` +
`gate_reached_count`; `iterations`/`retries` stay deferred `Gap`s.]** The engine
stays pure (no I/O, no bus import); emission is wired in the driver, exactly as
the revert event is today.

**Explicitly SCOPED OUT (named deferred seams — do NOT expand the slice toward
"all measured metrics"):**

- **Token-provenance ingress** — BLOCKED. No in-process token source exists;
  needs the post-tool / model-usage surface. The token half of Candidate 1 is
  not buildable now; only the engine-computed terminal-event half is.
- **Cost** — S-2-gated. Remains an *unconditional* `Gap` this slice (per
  `g4d-ledger.md` D2), even if a rate-table digest verifies, until the S-2 mount
  makes the rate table structurally agent-unwritable.
- **Effort attribution** — deferred. Needs the two-ingress (runtime +
  platform-webhook) provenance, and E-2 (the webhook receiver) has no component
  home yet.

**Known constraint — acknowledged and accepted by the operator.** These new
metrics will be **test-exercised only until Seam 7 (the live
`tool.execute.after` advance hook) lands** — exactly like the revert event
today, because there is no live emit call site yet. This slice widens **WHAT the
senses can measure**; it does **not** by itself make emission land in a live
session. The operator chose Candidate 1 over building Seam 7 first with this
tradeoff visible: value now is in *widening measurable facts at the ledger's
named plug-in point*, and the live-emission gap is a separate, already-tracked
seam.

**Rationale:** highest RICE (4.05) and highest weighted-matrix total (275);
buildable now Python-side with no dependence on S-2, signal history, or the
unbuilt Seam 7 beyond what Slice 1 already tolerated; directly unblocks the most
downstream gap (the ledger's `iterations`/`retries` MEASURED metrics); honest
new signal consistent with the anti-vanity contract; low blast-radius
(agent-writable `src/` only, no Tier-3 config).

## Scope Sketch

| Area | Files/Modules Likely Affected |
|---|---|
| New event kinds | `src/gleipnir/bus/events.py` — add `EventKind` members + one frozen payload dataclass per kind + one `_PAYLOAD_CLASSES` registry row per kind |
| Emit sites | `src/gleipnir/engine/driver.py` — emit each new terminal event from the driver path (alongside `_emit_revert_if_any`); engine (`engine/__init__.py`) stays pure |
| Ledger reduce branches | `src/gleipnir/ledger/reduce.py` — add typed counting branches in `reduce()`'s event loop; move `iterations`/`retries` out of `_SEAM_REASONS` into `Measured` |
| Reconciliation | `src/gleipnir/ledger/reconcile.py` — re-derive the new counts independently; keep the gap-report honest |
| Tests | `tests/test_bus_events.py`, `tests/test_driver_emits_*.py`, `tests/test_ledger_reduce.py`, `tests/test_ledger_reconcile.py` |

## Open Questions (for `gleipnir-plan`)

- Exact new `EventKind` names and payload shapes (fields per kind). The enum
  comment already gestures at `GUARD_TRIGGERED` / `HUMAN_ESCALATION` /
  `TASK_ABANDONED`; the plan decides the concrete set for iteration-cap /
  escalation / retry.
- Precisely where in the driver each new terminal event is classified/emitted
  (the crash-safe classification pattern of `_emit_revert_if_any` is the model).
- Denominator/provenance conventions for the new `Measured` metrics (mirror the
  revert-count / escalation-rate zero-denominator convention).
- Whether "retry" is derivable from existing engine state or needs a distinct
  driver-observed trigger.

## Next-stage handoff (`gleipnir-plan` — ATLAS Architect/Trace)

`gleipnir-plan` plans FROM this converged brief (it does not re-decide the
material tradeoff). Concrete plug-in points found in source this session
(verify/cite in the plan):

- **`EventKind`** in `src/gleipnir/bus/events.py` — currently one member
  `REVERT_OCCURRED` (line 59). Adding a kind = **enum member** + **frozen
  payload dataclass** + **one `_PAYLOAD_CLASSES` registry row** (lines 115-116).
  Read-path dispatch (`from_json_line`) is table-driven — no string parsing.
- **The ledger's `_SEAM_REASONS`** in `src/gleipnir/ledger/reduce.py` — already
  carries `"iterations"` (line 51) and `"retries"` (line 52) entries **waiting**
  to be promoted; `reduce()`'s event loop (the `if event.kind is
  EventKind.REVERT_OCCURRED` branch) is the spot new-kind counting slots into.
- **The driver emit site** — where `RevertOccurredEvent` is emitted
  (`_emit_revert_if_any` in `src/gleipnir/engine/driver.py`); new terminal
  events emit from the **same driver path**, engine stays pure.

The plan will decide the exact new `EventKind` names/payload shapes and where in
the driver each is emitted.
