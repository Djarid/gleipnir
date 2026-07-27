# Plan: G-5 engine — revert edges (backward routing on gate FAIL)

**Stage:** `plan` (owned by `gleipnir-plan`). **Model:** Opus (unbounded-judgment stage).
**Status:** authored, ready to hand to the orchestrator for sequencing into
`spec-review -> test -> code -> quality -> [local commit] -> gate`. **Tier:** 0
(this `plans/` file is the only artifact this role writes; disposable).

**Scope note (read first).** The *direction* is operator-confirmed and is
recorded here as LOCKED: the engine's `TRANSITIONS` today only routes FORWARD
(PASS advances one stage) plus a SELF-LOOP on `SPEC_REVIEW`/`QUALITY`
(FAIL loops, capped -> `ESCALATED`). That cannot express the real workflow,
where a FAIL at a gate stage must REVERT to an EARLIER stage. This plan's job
is to make **revert edges** rigorously executable by the test/code stages —
not to re-decide whether reverts are wanted. Where a durable ruling must
survive across sessions it is flagged for the operator to persist in Tier-3
`decisions/` (see the closing **Durable-decision hand-off**).

---

## GOTCHA pre-flight (recorded)

- **Goal order correct:** plan-before-code. The engine exists and is green
  (49/49); this is a *contract-changing* extension, so the plan explicitly
  partitions which of the 49 tests must stay unchanged vs which change *by
  design* (§Compatibility, §Stress-test).
- **Goals checked:** `../goals/manifest.md`/`plan-format.md` (this file follows
  the required Architect/Trace/Link/Assemble/Stress-test/Execution structure);
  `../stage-role-map.md` (sequencing stays in code — `TRANSITIONS` as the sole
  authority, GOTCHA Amendment 1); spec **G-5** conformance clauses (loop caps
  fire "at exactly N by code"; "no code path" bypass; precept-10 human gate).
- **Layered per GOTCHA-as-amended:** the revert *decision* is a bounded,
  typed enum classification returned by the judge and routed by the table; it
  is **never** free text an LLM narrates a jump from (Amendment 1). Sequencing —
  including where a FAIL reverts to — lives in checked-in data, not prose.
- **Gaps this plan must close (named up front, resolved in Trace):**
  1. The transition table has no backward edges; a FAIL at `TEST` has *no*
     entry at all today (`NoSuchTransition`), and `SPEC_REVIEW`/`QUALITY` FAIL
     only self-loop. The real workflow needs FAIL-to-earlier-stage.
  2. The loop-cap machinery counts **per-state self-loops**. Reverts introduce
     a *cycle* (`plan -> ... -> quality -> plan -> ...`) that a per-state
     self-loop counter cannot see — so "escalation fires at exactly N" could be
     defeated by thrashing through a cycle. A new, deterministic budget rule is
     required and is the load-bearing correctness point of this plan.
  3. Whether reverting resets downstream progress / re-entry counters is
     undefined. This plan pins it deterministically.
- **Capability boundary honoured:** this file is the only artifact I write.
  The engine/test changes are `gleipnir-code`'s (`test` then `code` stages).
  The durable ruling is a Tier-3 operator hand-off, named below.

---

## Architect

**Problem (one sentence).** The G-5 engine's `TRANSITIONS` table can only route
forward (PASS) or self-loop-until-escalated (FAIL on `SPEC_REVIEW`/`QUALITY`),
so it cannot express the operator's real workflow in which a failed
spec-review, test, or quality review **reverts to a defined earlier stage** —
and it must gain those backward edges *without* weakening the G-5 guarantees
(escalation at exactly N, no verdict routes into `GATE`, the human gate's sole
exit) that the 49 existing tests and the wire-in depend on.

**User.** The **operator** (whose real pipeline is
`interactive-planning -> brainstorm -> plan -> spec-review -> test -> code ->
quality/review [ -> git-ops [ -> git-pm ] ]`, where any gate FAIL can send work
back to an earlier stage). Downstream, the **orchestrator/driver** (which
consumes the transition table as data) and the **wire-in hook** (whose
allow-table projection must stay derivable from `PipelineState`).

**Measurable success criteria.**

1. A FAIL at a **gate stage** routes **backward** to that stage's defined
   revert target — `SPEC_REVIEW` FAIL -> `PLAN`; `TEST` FAIL -> `SPEC_REVIEW`;
   `QUALITY` FAIL -> `CODE` — deterministically, via data in the table, not via
   any text the judge narrates (§Stress-test T1). All three targets are
   **strictly backward** by `PIPELINE_ORDER` index (see §Q1: `SPEC_REVIEW`(2)->`PLAN`(1),
   `TEST`(3)->`SPEC_REVIEW`(2), `QUALITY`(5)->`CODE`(4)), so each genuinely
   reverts and each counts toward the global budget (§T4).
2. The revert *target* is a **bounded, typed choice** the router consults,
   never open-ended free text; a judge that tries to smuggle a jump target as a
   string is rejected (`InvalidVerdict`), exactly as today (§T2, §Q1 below).
3. **Escalation still fires at exactly N, deterministically** — now against a
   rule that a *revert cycle* also counts toward, so no
   `plan -> ... -> quality -> plan -> ...` thrash can loop forever without
   reaching `ESCALATED` (or `HUMAN_QUESTION`) at a bounded, exact count
   (§T3, §T4; the load-bearing G-5 correctness point, §Q2 below).
4. **No verdict routes into `GATE`.** Adding revert edges must not add any
   judged-verdict edge whose target is `GATE`; `attempt_gate` remains the sole
   entrance (§T5). `GATE`/`ESCALATED` stay terminal (no outgoing key); the
   human gate keeps its single non-`step()` exit (§T6).
5. The **allow-table projection** the wire-in derives from `PipelineState`
   stays derivable and correct after reverts: a reverted state maps to its
   legitimate role exactly as a forward-reached state does (§T7).
6. **The subset of the 49 tests that encodes structural guarantees stays
   green unchanged;** the subset that *asserts the absence of a backward edge*
   changes by design, and every such change is enumerated with its reason
   (§Compatibility, §T8).

**Constraints.**

- **Determinism (G-5 / Amendment 1).** Every routing decision — forward,
  self-loop, revert, escalate — is a lookup in checked-in `TRANSITIONS`-shaped
  data keyed by `(state, Verdict)`. The router never inspects `payload`, never
  pattern-matches text. Revert targets are data, not narration.
- **Fail-closed (Axiom 2 / G-3.2).** Any ambiguity — an unknown verdict, a
  state with no edge for a verdict, a budget overrun — refuses or escalates;
  never a default-allow forward jump. Absence of an edge remains
  `NoSuchTransition`.
- **Minimal enum (operator instruction).** `Verdict` stays a small enum, no
  `SKIP`, no free-text. §Q3 decides whether a new `REVERT` member is needed or
  `FAIL` is reinterpreted; the enum must remain a closed, typed channel.
- **Compatibility with the wire-in and bolt-on plans.** The change must keep
  the allow-table projection derivable (`engine-wire-in.md`) and must not
  collide with the `configured-optionality.md` core-vs-bolt-on refactor
  (`GIT -> LOCAL_COMMIT`, remote states as bolt-ons). This plan touches the
  *forward-and-backward mainline routing*; it flags — and does not redesign —
  the bolt-on and the `interactive-planning` pre-stage (§Q5).
- **stdlib-only** (`decisions/runtime-and-deps.md`): the counters/budget are
  plain ints in the `Engine` instance; no new deps.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Tier / writer | Role in this change |
|---|---|---|---|
| Engine core | `src/gleipnir/engine/__init__.py` | code; `gleipnir-code` (test-first) | Add revert edges to `TRANSITIONS`; add the revert-budget counter + escalation rule; adjust `step()` routing |
| Engine design record | `src/gleipnir/engine/DESIGN.md` | code; `gleipnir-code` | Document revert edges, the budget rule, and the reinterpreted verdict semantics |
| Engine tests | `tests/test_engine.py` (+ possible new module) | code; `gleipnir-code` | Author revert/budget acceptance tests **first**; adjust the by-design test changes (§Compatibility) |
| Stage-role map (authority) | `../stage-role-map.md` | Tier 3 | Unchanged authority; the allow-table projection is re-derived against it |
| Wire-in plan (consumer) | `../plans/engine-wire-in.md` | Tier 0 | The allow-table + bridge must stay consistent with the new routing (§T7) |
| Optionality plan (adjacent) | `../plans/configured-optionality.md` | Tier 0 | Core-vs-bolt-on refactor; this plan stays compatible, does not redesign it (§Q5) |
| **Durable decision record** | `../decisions/engine-revert-edges.md` | **Tier 3, operator only** | **This role CANNOT write it — see hand-off** |
| This plan | `../plans/engine-revert-edges.md` | Tier 0 | The only file this role writes |

### The design questions, resolved (this is the planning judgment)

#### Q1 — Revert target: fixed-per-stage vs bounded-selectable? **RECOMMEND: Option A (fixed-per-stage), with a typed extension seam for B.**

**Recommendation.** Each gate stage gets **one defined revert target**, encoded
as a static backward edge in `TRANSITIONS` keyed by `(state, Verdict.FAIL)`:

| Gate stage | FAIL routes to (revert target) | `PIPELINE_ORDER` (from -> to) | Backward? | Rationale |
|---|---|---|---|---|
| `SPEC_REVIEW` | `PLAN` | 2 -> 1 | yes | A spec-review failure means the plan is wrong; recoding won't fix a bad plan |
| `TEST` | `SPEC_REVIEW` | 3 -> 2 | yes | This is a **test-FIRST** pipeline: `TEST` *authors* the tests before `CODE` exists, so a failed test-authoring stage means the spec/plan was inadequate to write good tests against — revert backward to `SPEC_REVIEW`, not forward to `CODE`. (Operator decision; supersedes the earlier `TEST FAIL -> CODE`, which was FORWARD — `TEST`(3)->`CODE`(4), same target as PASS — and thus burned budget for no revert.) |
| `QUALITY` | `CODE` | 5 -> 4 | yes | A quality/blast-radius failure means the implementation needs rework |

**All three edges are strictly backward** by `PIPELINE_ORDER` index (target
index < source index): `SPEC_REVIEW`(2)->`PLAN`(1), `TEST`(3)->`SPEC_REVIEW`(2),
`QUALITY`(5)->`CODE`(4). None coincides with the stage's FORWARD/PASS target, so
each is a genuine revert and each increments the global revert budget (§Q2, §T4).

**Why A over B.** G-5's core claim is that sequencing is *checked-in data a
counter cannot forget*, not a judgment an LLM narrates. Option A keeps the
revert target **fully in the table** — the judge returns only PASS/FAIL, and
*where* a FAIL goes is a fixed edge no LLM chooses. This is the strongest form
of "no code path an LLM performs on text." Option B (LLM picks any earlier
stage) is *achievable* within G-5 only as a **bounded typed classification**
(the judge returns a member of a small `RevertTarget` enum, say
`{TO_PLAN, TO_SPEC_REVIEW, TO_CODE}`, and the router maps `(state, RevertTarget)` deterministically),
but it adds a second enum, a second routing dimension, and more test surface —
richness the operator's confirmed workflow does not yet require (each named
FAIL already has one natural target). **Decision: ship A now.** Leave a
documented seam: if B is later wanted, it is expressed as a *typed enum the
router consults*, never as free text — the router change would be to key
reverts on `(state, RevertTarget)` instead of `(state, Verdict.FAIL)`, keeping
the "no text routing" invariant intact. This seam is flagged in the durable
decision so B, if adopted, is adopted as bounded typed choice by construction.

> **Important interaction with the current self-loop.** Today `SPEC_REVIEW` and
> `QUALITY` FAIL **self-loop** (same-state retry, capped). Under Option A a FAIL
> at those stages now routes **backward** (`SPEC_REVIEW -> PLAN`,
> `QUALITY -> CODE`) instead of self-looping. This is a **deliberate semantic
> change**: the operator's model is "a failed quality review goes *back to
> code*," not "re-run the same quality judge in place." The self-loop was the
> old engine's only way to express "not done yet"; the revert edge replaces it
> with the real target. The escalation guarantee is preserved by the budget
> rule in Q2 (which now counts revert *cycles*, not just self-loops).
> The **self-loop model is removed entirely**: `SPEC_REVIEW`/`QUALITY` no longer
> self-loop on FAIL — they revert. `LOOPING_STATES` as a concept is therefore
> **superseded** by the revert-edge set + global budget (§Q2); the self-loop
> tests change by design (§Compatibility). This supersession also reaches across
> plans — see §Q5 for how it overrides `configured-optionality.md`.

#### Q2 — Cap semantics with reverts: **RECOMMEND a global revert budget (a single per-engine counter), escalating at exactly N.**

**Recommendation.** Replace the per-state self-loop counter with a **single
global revert counter** on the `Engine` instance, incremented **once per revert
edge traversed** (i.e. each time `step()` routes a FAIL backward). A configurable
cap `REVERT_BUDGET` (default carried over from `DEFAULT_LOOP_CAP`, overridable in
the constructor). Rule, exactly:

- Reverts `1 .. N-1` perform the backward transition and return
  `StepResult(target, escalated=False)`.
- Revert `N` (the counter *reaching* the cap) transitions to `ESCALATED`
  instead of reverting, returning `StepResult(ESCALATED, escalated=True)`.
- The counter is **monotonic within an engine instance** — it is **not reset**
  by re-entering a stage, by a forward PASS, or by reaching the revert target.
  This is the whole point: a `plan -> spec-review -> plan -> spec-review -> ...`
  thrash burns budget every backward hop and therefore hits `ESCALATED` at
  exactly N total reverts, no matter which stages the cycle runs through.

**Why global, not per-edge or per-state.** A per-state or per-edge counter
re-opens the exact hole reverts create: a cycle
`plan -> spec-review(FAIL->plan) -> ... -> quality(FAIL->code) -> ...` touches
*different* edges, so per-edge counters each stay under their own cap while the
pipeline thrashes forever. A **single global budget** makes the escalation
bound a property of the *whole run's backward motion*, which is the thing G-5
requires to be finite-and-exact: "escalation fires at exactly N by code."
There is exactly one number to reason about, it only ever increases, and it is
compared in code — no LLM is asked "have we thrashed enough yet."

**Downstream-progress / re-entry semantics, pinned deterministically:**

- A revert **does not** silently reset any notion of downstream progress the
  engine holds, because the minimal engine holds none beyond `self._state`:
  reverting simply sets `self._state` to the target. Re-doing the intervening
  forward stages happens naturally by re-running `step()` PASS-by-PASS from the
  target. (If a later slice adds per-stage artifacts/verdicts, whether those
  are invalidated on revert is a *future* decision, flagged, not decided here.)
- Re-entering a stage **does not** reset the global revert counter (that is the
  anti-thrash guarantee). The counter is orthogonal to *which* state you are in.
- `NEEDS_HUMAN` is unaffected: it still routes to `HUMAN_QUESTION` from any
  main-line state and does **not** consume revert budget (it is not a revert;
  it is the human gate). `answer_human_question` returns to the origin state
  and likewise does not touch the counter.

**Interaction with escalation as a sink.** `ESCALATED` stays terminal (no
outgoing edge). Reaching it via budget-exhaustion is identical in shape to
today's cap-exhaustion escalation, so the "escalation is a deterministic sink"
guarantee is preserved unchanged.

> **Operator convergence (post-plan, via the orchestrator-surfaced gate).** The
> global-budget choice recommended here was subsequently put to the operator as
> a material decision (`../plans/engine-revert-cap-model-brainstorm.md`,
> `../decisions/engine-revert-edges.md`). The operator converged on: **global
> budget as the escalation TRIGGER** (as recommended) **+ a mandate to emit each
> revert hop as a G-4 bus event** (to preserve the per-stage "stuck" signal the
> blunt global counter loses — a seam until the bus exists) **+ a deferred
> hybrid-C per-stage seam** (not built). This is recorded at the revert site in
> the engine and in the durable decision; it does not change the budget
> mechanism specified here.

#### Q3 — Verdict model: **RECOMMEND reinterpret `FAIL` as "route to this stage's revert target"; do NOT add a new verdict.**

`Verdict` stays exactly `{PASS, FAIL, NEEDS_HUMAN}` — three members, no `SKIP`,
no free text (the existing `test_verdict_has_exactly_three_members_no_skip`
stays green **unchanged**). `FAIL` is *reinterpreted*: instead of "self-loop on
this state (capped)," it means "traverse this state's defined revert edge
(counting against the global budget; escalate at N)." The routing difference is
entirely in `TRANSITIONS` (the FAIL edge now names an *earlier* state) and in
the budget rule — not in the enum. This keeps the judge's channel minimal and
typed, and keeps `InvalidVerdict` rejecting any non-enum return exactly as
today. **No `REVERT` member is added.** (Q1's Option-B seam, if ever taken,
adds a *separate* `RevertTarget` enum as a second routing dimension — still not
a new `Verdict` member and still not text.)

#### Q4 — Compatibility with the structural G-5 guarantees.

The change is confined to (a) the FAIL rows of `TRANSITIONS` for the gate
stages and (b) the loop-cap counter's replacement by the global revert budget.
Everything the 49 tests assert *structurally* is preserved; only the assertions
that encode the *old self-loop model* or the *absence of a backward edge*
change, by design. Explicit partition:

**MUST stay green, unchanged (structural G-5 / G-3.2 guarantees):**

- `TestTransitionTableIsTheSpec::test_pipeline_order_matches_spec` — forward
  order is unchanged; reverts are additional backward edges, not a reordering.
- `test_verdict_has_exactly_three_members_no_skip` — enum unchanged (Q3).
- `test_gate_has_no_outgoing_edge`, `test_escalated_has_no_outgoing_edge`,
  `test_human_question_has_no_outgoing_edge` — terminals/human gate unchanged.
- `test_git_has_no_pass_edge`, `test_no_state_transitions_directly_into_gate`,
  all of `TestNoGateBypass`, `TestAttestationGate`, `TestHumanGate`,
  `TestResumeAt`, `TestTextInjectionCannotRoute` (payload never routes; a
  judge returning a raw string is rejected) — **all unchanged**. Reverts add
  **no** edge into `GATE` and change **nothing** about `attempt_gate`,
  `answer_human_question`, or the payload-blindness of the router.
- `TestHappyPathProgression` — the all-PASS forward walk is unchanged.

**CHANGE by design (and why they SHOULD):**

- `test_looping_states_are_spec_review_and_quality_only` — `LOOPING_STATES` is
  **superseded** by the revert-budget model (Q1/Q2). This test is replaced by a
  test asserting the *revert edges* exist for `SPEC_REVIEW`/`TEST`/`QUALITY`
  with their defined targets (`PLAN`/`SPEC_REVIEW`/`CODE`). Reason:
  self-loop-in-place is no longer the FAIL semantics; backward routing is.
- **`test_cap_is_per_state_independent_counters` (named explicitly)** — asserts
  that loop caps use **independent per-state counters**, which is **directly
  incompatible** with this plan's single global budget (and with the operator's
  Q5 supersession of `configured-optionality.md` S12(c)). It is **replaced by a
  global-budget test**: `TestRevertBudgetExactness::test_global_budget_is_single_monotonic_counter`,
  which asserts one counter shared across all revert edges, incremented once per
  backward hop, never reset, escalating at exactly N (the T4 cycle-thrash case is
  the proof). Reason: independent counters re-open the cycle-thrash hole (§Q2).
- The rest of `TestLoopCapExactness` — these assert the *per-state self-loop*
  counter. They are **rewritten** as `TestRevertBudgetExactness`: escalation at
  exactly N against the **global** counter, including the **cycle-thrash** case
  (T4, N=4, alternating edges) proving the global budget catches what per-state
  counters could not. `test_escalated_is_terminal` is retained in spirit
  (escalation still terminal) but reached via budget exhaustion.
- Any test asserting a FAIL at `SPEC_REVIEW`/`QUALITY` *stays on the same
  state* is inverted to assert it moves to the **revert target**
  (`SPEC_REVIEW`->`PLAN`, `QUALITY`->`CODE`). A FAIL at `TEST` (which had no
  FAIL edge before) is asserted to move to `SPEC_REVIEW` (T1/T1b).

No other test changes. The count may shift from 49 as loop-cap tests split into
budget + revert-edge tests; the plan does **not** target a specific new number,
only that every changed test is one of the enumerated by-design changes and
every structural test above stays green verbatim.

#### Q5 — Cross-plan reconciliation with the LOCKED `configured-optionality.md` (operator-decided).

`configured-optionality.md` is LOCKED, so this plan must state precisely how it
relates to it. A prior draft only checked state-**naming** overlap; that was
insufficient. There are **two semantic contradictions**, and the operator has
ruled on both: **revert-edges SUPERSEDES.** The global-budget/revert model is
**authoritative on loop-cap and self-loop semantics**; the conflicting parts of
`configured-optionality.md` are **superseded** and get revised to this model when
that plan is built.

| # | `configured-optionality.md` clause | Contradiction with this plan | Resolution (operator-decided) |
|---|---|---|---|
| (a) | **S12(c)**: "loop caps escalate at exactly N for `SPEC_REVIEW` and `QUALITY` with **INDEPENDENT counters**" | This plan uses a **single GLOBAL revert budget**, not independent per-state counters. Independent counters re-open the cycle-thrash hole (§Q2). | **S12(c) is SUPERSEDED.** Revised to the global-budget model (one monotonic counter, escalate at exactly N) when `configured-optionality.md` is built. |
| (b) | **§2.3 transition-classification table**: encodes the CURRENT self-loop model — "`SPEC_REVIEW -> SPEC_REVIEW` (FAIL loop)", "`QUALITY -> QUALITY` (FAIL loop)" | This plan **removes the self-loop model entirely**: FAIL no longer self-loops, it reverts (`SPEC_REVIEW`->`PLAN`, `QUALITY`->`CODE`). | **The §2.3 self-loop rows are SUPERSEDED.** Revised to the revert-edge classification when `configured-optionality.md` is built. `LOOPING_STATES` as a concept is superseded by the revert-edge set + global budget. |

**Authority statement.** On loop-cap/self-loop semantics, **revert-edges is
authoritative**; `configured-optionality.md` S12(c) ("independent counters") and
its §2.3 self-loop rows are superseded and must be revised to the
global-budget/revert model when that plan is built. This supersession is added to
the **Durable-decision hand-off** so the operator persists it. There is no
naming collision to resolve (state names are compatible); the resolution is
purely semantic (loop-cap counter model + self-loop removal).

**Remaining cross-plan compatibility notes (unchanged, non-conflicting):**

- **`interactive-planning`** in the operator's model precedes `brainstorm`. The
  current `PipelineState` enum starts at `BRAINSTORM`. This plan **does not add**
  an `INTERACTIVE_PLANNING` state — that is a separate scope. It only ensures
  the revert model is *compatible* with such a pre-stage: if it is later added
  as the new first state, its revert target rules (can `plan` FAIL revert
  *before* brainstorm?) are decided then; the global-budget rule needs no change
  to accommodate one more upstream state. **Flagged, not built.**
- **`git-ops` / `git-pm` tail** are the (optional, bolt-on) tail stages
  governed by `configured-optionality.md` (git-local core; remote push =
  `REMOTE_GIT` bolt-on; PR/MR = `PLATFORM_PM` bolt-on; `git-pm` currently
  **unbound** in `stage-role-map.md`). That plan renames the core `GIT` state to
  `LOCAL_COMMIT` and relocates remote states to a bolt-on registry. This
  revert-edges plan must **not** hard-code a revert edge into a state that the
  optionality refactor may rename or relocate. Concretely: the revert edges
  defined here target **only mainline states that both plans agree exist**
  (`PLAN`, `SPEC_REVIEW`, `CODE`) — never
  `GIT`/`LOCAL_COMMIT`/`PUSH`/`OPEN_PR_MR`. A "git failure -> back to code"
  revert (named in the operator's model) is therefore **compatible** but is
  defined against whichever last-pre-gate state the optionality refactor settles
  on, and is a **cross-plan sequencing point** for the operator to order
  (revert-edges vs the git refactor). This plan does **not** decide that ordering
  and does **not** redesign the bolt-on.

### Edge cases (all resolve deterministically; doubt -> refuse/escalate)

- **FAIL at a non-gate main-line state** (e.g. `BRAINSTORM`, `PLAN`, `CODE`)
  where no revert edge is defined ⇒ **`NoSuchTransition`** (unchanged
  fail-closed posture — absence of an edge is refusal, never a default jump).
  Only the defined gate stages get FAIL revert edges.
- **Revert counter already at `N-1`, another FAIL arrives** ⇒ transition to
  `ESCALATED`, `escalated=True`, exactly (never `N-1`, never `N+1`).
- **`NEEDS_HUMAN` during a revert cycle** ⇒ routes to `HUMAN_QUESTION` as
  usual; does **not** consume revert budget; `answer_human_question` returns to
  the origin state with the counter untouched.
- **Revert target equals a state that itself has a revert edge** (e.g. after
  `QUALITY -> CODE`, the pipeline goes `CODE -> QUALITY` again and can FAIL
  again) ⇒ each backward hop increments the single global counter; escalation
  is guaranteed at N regardless of the cycle's shape (this is the anti-thrash
  test, §T4).
- **`step()` from `GATE`/`ESCALATED`/`HUMAN_QUESTION`** ⇒ unchanged
  (`NoSuchTransition` / `HumanGateBlocked`); reverts add no key for these.
- **`resume_at` after a revert** ⇒ unchanged construction semantics; note the
  global revert counter resets on resume (same honesty as today's loop-count
  reset on resume — the bridge carries state, not the counter; flagged in the
  durable decision as a known cross-process fidelity gap, identical in
  character to the existing `resume_at` loop-count note).

### What is explicitly OUT of scope

- Adding the `INTERACTIVE_PLANNING` state (compatibility only, §Q5).
- The core-vs-bolt-on git refactor (`configured-optionality.md` owns it).
- Option B (LLM-selectable revert target): a documented *typed-enum* seam only;
  not built.
- Persisting the revert counter across processes (bridge/`resume_at`), same
  honest gap as today's loop-count.
- Per-stage artifact invalidation on revert (no such artifacts in the minimal
  engine yet).

---

## Link (validated before building)

- **The exact change points are identified.** Read
  `src/gleipnir/engine/__init__.py`: (i) `TRANSITIONS` FAIL rows for
  `SPEC_REVIEW` (line ~139, currently self-loop) and `QUALITY` (line ~152,
  currently self-loop) become backward edges, and a `TEST` FAIL row is **added**
  (today `TEST` has no FAIL key — line ~142); (ii) `LOOPING_STATES` /
  `DEFAULT_LOOP_CAP` and the self-loop branch in `step()` (lines ~379-385) are
  replaced by the global revert-budget branch; (iii) `loop_count` becomes
  `revert_count` (or is kept as a compatibility read of the global counter —
  code stage decides, tests pin the observable).
- **The escalation mechanics already exist to reuse.** The current self-loop
  path already does "increment a counter; at cap, go to `ESCALATED`,
  `escalated=True`." The revert-budget rule is the *same shape* against a single
  global counter — low-risk, well-precedented in the codebase.
- **The structural guarantees to preserve are enumerated in the tests.**
  `TestTransitionTableIsTheSpec`, `TestNoGateBypass`, `TestAttestationGate`,
  `TestHumanGate` are the guardrails; confirmed they do not depend on the
  self-loop model and stay green (§Compatibility).
- **The wire-in's allow-table derivation is state-based, not edge-based.**
  Read `engine-wire-in.md`: the reverse map is `target agent -> legitimate
  when engine state ∈ {…}`, derived from `PipelineState`, not from *how* the
  state was reached. A reverted `PLAN` state maps to `gleipnir-plan` exactly
  as a forward `PLAN` does — so revert edges need **no** allow-table change,
  confirmed. (Acceptance test T7 asserts this.)
- **Spec G-5 conformance language confirmed.** Spec line 220: "escalation fires
  at exactly N by code, deterministically"; "no code path that permits
  [skipping]"; "no bypass … because bypass is a … code path, not a string
  match." The global-budget rule and the data-only revert edges satisfy all
  three. Spec line 177 even names "revert occurred" as an anticipated
  structural fact — reverts are within the spec's model, not against it.
- **stdlib-only holds:** the counter is an `int`; no new imports.

---

## Assemble (test-first build order)

Each step authors its Stress-test items as **failing tests first**, then
implements to green. Ordered so the contract change is proven before the
routing change lands. All steps are `gleipnir-code` (`test` then `code`).

**Step 1 — Revert edges in the table (test-first).**
 1a. Author tests: `TRANSITIONS[SPEC_REVIEW][FAIL] is PLAN`;
     `TRANSITIONS[QUALITY][FAIL] is CODE`; `TRANSITIONS[TEST][FAIL] is SPEC_REVIEW`
     (the defined targets, §Q1); and a `step()` FAIL at each of these three
     lands on the target state (T1). Author **T1b** specifically: a `step()` FAIL
     at `TEST` lands on `SPEC_REVIEW` (never `CODE`) **and** increments the
     global `revert_count` by exactly 1 (the TEST edge's budget contribution,
     which no prior test exercised). Assert **no** FAIL edge targets `GATE` and
     no new state routes into `GATE` (T5) — reuse/extend the existing
     `test_no_state_transitions_directly_into_gate` shape.
 1b. Implement: add/replace the FAIL rows in `TRANSITIONS`. Do **not** yet
     touch the counter — this step only proves backward *routing* exists and
     targets the right states, with the escalation path still the old one until
     Step 2 (so land Step 1 + Step 2 together if the old counter would misfire;
     the code stage may fuse 1b+2b behind the tests).

**Step 2 — Global revert budget + exact-N escalation (test-first).**
 2a. Author `TestRevertBudgetExactness`: reverts `1..N-1` transition to the
     target with `escalated=False`; revert `N` transitions to `ESCALATED` with
     `escalated=True`; the observable counter (`revert_count`) reads `N`
     (T3). Author the **cycle-thrash** test (T4) with the **concrete N=4** hop
     sequence (`SR-fail(1) -> Q-fail(2) -> SR-fail(3) -> Q-fail(4)=ESCALATED`):
     alternating *different* revert edges still escalates at exactly 4 total
     reverts — proving a per-state/per-edge counter would fail here (2+2, neither
     reaching 4) but the global one does not. Author: `NEEDS_HUMAN`
     does **not** consume revert budget; `answer_human_question` leaves the
     counter untouched.
 2b. Implement: replace `LOOPING_STATES`/self-loop branch with a single
     `self._revert_count` incremented on every backward FAIL edge, compared to
     `REVERT_BUDGET` (default from `DEFAULT_LOOP_CAP`, constructor-overridable);
     at the cap, route to `ESCALATED` instead of the revert target. Keep
     `escalated` flag semantics identical to today.

**Step 3 — By-design test migration (the Compatibility partition).**
 3a. Rewrite `TestLoopCapExactness` -> `TestRevertBudgetExactness` (Step 2
     already authored it; here remove/replace the superseded self-loop tests).
     Replace `test_looping_states_are_spec_review_and_quality_only` with a
     revert-edge existence test. Invert any "FAIL stays on same state" assertion
     to "FAIL moves to revert target."
 3b. Confirm the **MUST-stay-green** subset (§Compatibility) passes **verbatim**
     — run them explicitly and assert no diff (T8).

**Step 4 — Allow-table / wire-in consistency (test-first).**
 4a. Author T7: the state->legitimate-role projection is identical whether a
     state was reached forward or via revert (a reverted `PLAN` -> `gleipnir-plan`;
     a reverted `CODE` -> `gleipnir-code`). Assert the projection covers every
     `PipelineState` including post-revert states, with `ESCALATED` mapping to
     deny-all (pipeline terminated).
 4b. No implementation expected (the projection is state-based); if a
     projection helper exists, extend its test coverage only.

**Step 5 — DESIGN.md update (code stage).**
 Update `src/gleipnir/engine/DESIGN.md`: the revert edges (with the target
 table), the global-budget escalation rule (superseding `LOOPING_STATES`), the
 reinterpreted-`FAIL` semantics (Q3), and the Option-B typed-enum seam (Q1).
 Update the ASCII diagram to show backward edges. (Tier-3 `decisions/` and any
 `stage-role-map.md` change are operator hand-offs, not written by the pipeline.)

**Step 6 — Full-suite acceptance.**
 Run the whole suite: the structural subset green unchanged, the by-design
 subset green in its migrated form, and the new revert/budget tests green.
 Confirm `TestNoGateBypass`, `TestAttestationGate`, `TestHumanGate`,
 `TestTextInjectionCannotRoute`, `TestResumeAt` all pass verbatim.

**Rationale for order.** Backward *routing* (Step 1) is proven before the
*escalation rule that bounds it* (Step 2), because the anti-thrash guarantee is
only meaningful once reverts exist; then the by-design test migration (Step 3)
makes the Compatibility partition explicit and auditable; wire-in consistency
(Step 4) confirms no downstream breakage; docs (Step 5) and full acceptance
(Step 6) close it.

---

## Stress-test (acceptance checks the code stage must satisfy)

Concrete, checkable; authored as tests before implementation.

- **T1 — Gate FAIL reverts to the defined earlier stage.** From `SPEC_REVIEW`,
  a FAIL routes to `PLAN`; from `TEST`, a FAIL routes to `SPEC_REVIEW`; from
  `QUALITY`, a FAIL routes to `CODE`. Each is a single deterministic `step()`
  transition, target read from `TRANSITIONS`, `escalated=False` (below budget).
  Each target is strictly backward by `PIPELINE_ORDER` (2->1, 3->2, 5->4).
- **T1b — TEST FAIL reverts to SPEC_REVIEW *and* increments the global revert
  budget.** Pins the operator-decided `TEST`(3) FAIL -> `SPEC_REVIEW`(2) edge
  specifically: a single `step()` FAIL at `TEST` lands on `SPEC_REVIEW` (never
  `CODE`), and the global `revert_count` **increments by exactly 1** on that hop
  (proving `TEST`->`SPEC_REVIEW` is a genuine BACKWARD revert that contributes to
  the budget, not a forward same-as-PASS hop). No prior test exercised the TEST
  edge's budget contribution; this one does.
- **T2 — Revert target is data, never narrated text.** A judge that returns the
  bare string `"revert to plan"` (or any non-`Verdict`) raises `InvalidVerdict`
  before routing; a judge whose `payload` contains `"jump back to brainstorm"`
  changes nothing — the FAIL still routes to the *table-defined* target only.
  (Extends `TestTextInjectionCannotRoute`.)
- **T3 — Escalation fires at exactly N (global budget).** With
  `REVERT_BUDGET = N`, reverts `1..N-1` transition to their targets with
  `escalated=False`; the `N`th revert transitions to `ESCALATED` with
  `escalated=True`; `revert_count == N`. `N-1` reverts never escalate; the
  `N`th always does.
- **T4 — Revert-cycle thrash escalates at exactly N, deterministically
  (concrete N=4).** Set `REVERT_BUDGET = 4`. Drive this **exact** hop sequence,
  interleaving *different* revert edges so a per-state/per-edge counter could not
  see the total:

  | Hop | FAIL at | Reverts to | `revert_count` after | Result |
  |---|---|---|---|---|
  | 1 | `SPEC_REVIEW` | `PLAN` | 1 | transitioned, `escalated=False` |
  | 2 | `QUALITY` | `CODE` | 2 | transitioned, `escalated=False` |
  | 3 | `SPEC_REVIEW` | `PLAN` | 3 | transitioned, `escalated=False` |
  | 4 | `QUALITY` | (budget hit) | 4 | **`ESCALATED`, `escalated=True`** |

  **Acceptance (unambiguous):** hops 1–3 each perform the backward transition
  with `escalated=False`; hop 4 (the counter *reaching* N=4) transitions to
  `ESCALATED` with `escalated=True` and `revert_count == 4`. It escalates at
  **exactly** the 4th backward hop — not the 3rd, not the 5th — even though the
  reverts alternate between the `SPEC_REVIEW`->`PLAN` and `QUALITY`->`CODE`
  edges. This is the check a per-state/per-edge counter would fail (each edge
  would sit under its own sub-cap: 2 SPEC_REVIEW reverts + 2 QUALITY reverts,
  neither reaching 4); the single global budget catches it. There is **no**
  input that loops forever without reaching `ESCALATED` or `HUMAN_QUESTION`.
- **T5 — No verdict routes into `GATE`.** After adding revert edges, still no
  `(state, Verdict)` pair in `TRANSITIONS` maps to `GATE`; `attempt_gate`
  remains the sole entrance; `GATE` stays terminal (no outgoing key).
- **T6 — Human gate and terminals intact.** `HUMAN_QUESTION` still has no
  outgoing table edge and a sole `answer_human_question` exit; `ESCALATED` and
  `GATE` remain terminal; a `NEEDS_HUMAN` during a revert cycle routes to the
  human gate without consuming revert budget.
- **T7 — Allow-table / bridge consistency.** The state->legitimate-role
  projection is identical for a state reached via revert vs forward; it covers
  every `PipelineState`; `ESCALATED` deny-all. The wire-in bridge/driver need
  no change (state-based projection).
- **T8 — Structural subset green verbatim.** The enumerated MUST-stay-green
  tests (§Compatibility) pass with **no** source change. This list is **exactly**
  the prose MUST-stay-green partition above, no more, no fewer:
  `test_pipeline_order_matches_spec`,
  `test_verdict_has_exactly_three_members_no_skip`, the three
  `*_has_no_outgoing_edge` tests (`test_gate_has_no_outgoing_edge`,
  `test_escalated_has_no_outgoing_edge`, `test_human_question_has_no_outgoing_edge`),
  `test_git_has_no_pass_edge`, `test_no_state_transitions_directly_into_gate`,
  `TestNoGateBypass`, `TestAttestationGate`, `TestHumanGate`, `TestResumeAt`,
  `TestTextInjectionCannotRoute`, `TestHappyPathProgression`.
- **T9 — FAIL with no revert edge is refused.** A `Verdict.FAIL` from a state
  with no defined revert edge (e.g. `BRAINSTORM`, `CODE`, `PLAN`) raises
  `NoSuchTransition` — absence of an edge is refusal, not a default jump.
- **T10 — Determinism / no-text-routing preserved.** No `payload` content and
  no free-text ever alters routing; every forward/revert/escalate decision is a
  `(state, Verdict)` table lookup plus the integer budget comparison.

---

## Execution Workflow

**For the orchestrator (sequencing).** Route this plan through the locked stage
order: `spec-review` (`quality-reviewer`, Sonnet) validates this plan against
the spec/decisions as rubric, paying special attention to the Q2 budget rule
and the Compatibility partition -> `test` then `code` (`gleipnir-code`, Sonnet)
execute Assemble Steps 1-6 **test-first**, one Assemble step per delegation,
tests authored before implementation in each step -> `quality`
(`quality-reviewer`) blast-radius review against this plan, specifically the
by-design test changes and the anti-thrash guarantee -> `[local commit]` ->
`gate` (orchestrator reads attestation). **Cross-plan sequencing note:** the
`git failure -> code` revert and the `configured-optionality.md` git refactor
touch overlapping states; the orchestrator/operator decides which lands first
(§Q5). This plan deliberately defines revert targets **only** on states both
plans agree exist (`PLAN`, `SPEC_REVIEW`, `CODE`) so it can land either before or
after the git refactor without conflict. **Also note (§Q5):** this plan
**supersedes** `configured-optionality.md` on loop-cap/self-loop semantics
(global budget replaces S12(c) "independent counters"; revert edges replace the
§2.3 self-loop rows) — when that LOCKED plan is built, its S12(c) and §2.3
self-loop rows must be revised to this model.

**For the implementing agent (`gleipnir-code`).**
1. Work the Assemble steps **in order**; each is test-first — author its
   Stress-test items as failing tests, then implement to green.
2. Keep `Verdict` a three-member enum (Q3); do **not** add `SKIP` or a text
   channel. Do **not** add any `(state, Verdict)` edge whose target is `GATE`.
3. The global revert counter is monotonic within an instance and is **never**
   reset by re-entry, PASS, or reaching a target (Q2) — this is the anti-thrash
   guarantee; the cycle-thrash test (T4) is the one that proves it.
4. Escalation must fire at **exactly N** by the integer comparison — never at
   N-1, never at N+1 — mirroring the current cap semantics exactly (T3).
5. Preserve every structural guarantee in the MUST-stay-green subset verbatim
   (§Compatibility, T8); only the enumerated self-loop/loop-cap tests change,
   and each change must map to a stated reason.
6. Define revert targets **only** on `PLAN`/`CODE` (states both this plan and
   `configured-optionality.md` agree exist); never hard-code a revert into
   `GIT`/`LOCAL_COMMIT`/remote states (§Q5).
7. Update `DESIGN.md` (Step 5). Do **not** write `.gleipnir/decisions/` or
   `.gleipnir/stage-role-map.md` — hand the durable ruling to the operator.

**Definition of done.** T1-T10 green; the structural subset green verbatim; the
by-design test migration complete and each change justified; `DESIGN.md`
updated; the durable-decision content handed off to the operator.

**Fail-closed is the default posture:** an undefined edge is `NoSuchTransition`;
budget exhaustion is `ESCALATED`; a non-`Verdict` return is `InvalidVerdict`.
There is no default-allow forward jump anywhere in the routing.

---

## Durable-decision hand-off (Tier-3 — operator must persist)

This plan is Tier-0 and disposable. The following ruling is **durable** — later
engine work and the wire-in depend on it — so per `goals/plan-format.md` and the
trust-tier model it must be persisted in **Tier-3 `decisions/`**, which
**`gleipnir-plan` cannot write**.

- **Proposed path:** `.gleipnir/decisions/engine-revert-edges.md`
- **Proposed title:** *Decision: G-5 engine revert edges — fixed-per-stage
  backward routing and the global revert budget*
- **Content the operator should capture:**
  1. **Revert edges are fixed-per-stage table data (Option A):**
     `SPEC_REVIEW FAIL -> PLAN` (2->1), `TEST FAIL -> SPEC_REVIEW` (3->2),
     `QUALITY FAIL -> CODE` (5->4) — all strictly backward by `PIPELINE_ORDER`
     and all count toward the global revert budget. The FAIL verdict is
     *reinterpreted* to mean "traverse this state's defined revert edge"; the
     self-loop model is superseded. No new `Verdict` member
     (`{PASS, FAIL, NEEDS_HUMAN}` unchanged).
  2. **Option-B seam (bounded selectable target) is deliberately deferred** and,
     if ever adopted, must be a *typed `RevertTarget` enum the router consults*
     via `(state, RevertTarget)` keys — never free text. This preserves G-5's
     "no text routing" invariant by construction.
  3. **Global revert budget:** a single per-engine monotonic counter,
     incremented once per backward FAIL edge, escalating to `ESCALATED` at
     **exactly N** (`REVERT_BUDGET`, default = `DEFAULT_LOOP_CAP`,
     constructor-overridable). It is **not** reset by re-entry, PASS, or reaching
     a target. This closes the revert-cycle infinite-thrash hole that per-state
     or per-edge counters would leave open, and preserves G-5's "escalation
     fires at exactly N by code."
  4. **`NEEDS_HUMAN` does not consume revert budget;** the human gate and both
     terminals (`GATE`, `ESCALATED`) keep their structural guarantees unchanged;
     no verdict routes into `GATE` (`attempt_gate` remains the sole entrance).
  5. **Compatibility:** the allow-table projection (`engine-wire-in.md`) is
     state-based and unchanged by reverts; the wire-in bridge/driver need no
     change. Reverts add no `.gleipnir/`-writable surface.
  6. **Cross-plan sequencing flag:** the operator's "git failure -> code" revert
     and the `configured-optionality.md` git core-vs-bolt-on refactor
     (`GIT -> LOCAL_COMMIT`, remote states as bolt-ons) touch overlapping states.
     This decision defines revert targets **only** on `PLAN`/`CODE`; the git
     revert edge is defined against whichever last-pre-gate state the optionality
     refactor settles, and the ordering of the two changes is an operator
     sequencing decision.
  7. **`interactive-planning` pre-stage** is **not** added by this change; the
     revert model is compatible with a future upstream state and needs no budget
     change to accommodate one. Its revert-before-brainstorm rules are decided
     when/if that state is added.
  8. **Known not-yet-closed:** the global revert counter, like today's
     loop-count, **resets on `resume_at`** (the bridge carries state, not the
     counter); cross-process revert-budget fidelity is a later slice if needed —
     recorded honestly, not faked.
  9. **Cross-plan supersession of loop-cap / self-loop semantics (§Q5).**
     Persist explicitly, in Tier-3 `decisions/engine-revert-edges.md`, that this
     decision is **authoritative on loop-cap and self-loop semantics**:
     - `configured-optionality.md` **S12(c)** ("loop caps escalate at exactly N
       for `SPEC_REVIEW` and `QUALITY` with **INDEPENDENT counters**") is
       **SUPERSEDED** — revised to the single **global revert-budget** model
       (one monotonic counter, escalate at exactly N) when
       `configured-optionality.md` is built.
     - `configured-optionality.md` **§2.3** self-loop classification rows
       ("`SPEC_REVIEW -> SPEC_REVIEW` (FAIL loop)", "`QUALITY -> QUALITY`
       (FAIL loop)") are **SUPERSEDED** — revised to the revert-edge
       classification when that plan is built.
     - **`LOOPING_STATES` as an engine concept is RETIRED**, superseded by the
       revert-edge set + the global revert budget.

**Follow-up (operator, not a blocker).** If Option B is ever adopted, or the
`interactive-planning` state is added, update `stage-role-map.md` and
`DESIGN.md` accordingly; both are Tier-3 / code-stage work outside this plan.
