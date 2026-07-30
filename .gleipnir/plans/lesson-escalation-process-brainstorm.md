# Design Brief: Tier-0→Tier-2 lesson-candidate escalation process

> **Status: operator-converged (Approach A-hybrid), awaiting `gleipnir-plan`.**
> Written by `gleipnir-brainstorm` (Tier-0 writer) after the operator converged
> on Approach A-hybrid — with all four sub-positions accepted as recommended —
> via the orchestrator's `question` gate. This brief is the input `gleipnir-plan`
> plans FROM (full ATLAS), the planning step that was skipped when the escalation
> process was first self-designed inside the orchestrator without methodology.
> The `## Decision Analysis` below records the alternatives considered and why
> A-hybrid won; it is the justification for the converged choice, not a
> re-opening of it.

## Problem Statement

The *mechanism* for appending a lesson candidate to
`.gleipnir/lessons/session-lessons-candidates.md` is already converged
(**Option A** of the separate `tier2-escalation-control-proposal.md`:
session-scribe's grant extended to that single file, human-gated via the
orchestrator's `question` primitive). What was **never** properly designed is
the **escalation process** riding on top of that mechanism: *how* a candidate is
proposed, confirmed, appended, and handled on rejection.

The 8-step process in `tier2-escalation-control-proposal.md` was self-designed by
the orchestrator without methodology — a process decision made inside the
sequencing role and never explored against alternatives. That is precisely the
failure mode the brainstorm/convergence gate exists to close (cf. L-C6: the
decision-surfacing gate had that exact bug inside it). This brief redoes that
process design properly: 2–3 genuinely distinct process designs, a structured
decision analysis, and an operator-converged choice — before planning proceeds.

The design turns on five open questions, treated as the axes every process
design takes a position on:

1. **Trigger granularity** — propose+confirm each lesson one-at-a-time, or batch
   multiple candidates into one `question` at a checkpoint?
2. **No-response / timeout** — is "no response" a real case, or out of scope?
3. **Session cap** — cap escalation proposals per session, or leave uncapped?
4. **Provenance richness** — lightweight footer, or richer (session/task id,
   triggering source)?
5. **Rejected proposals** — logged for pattern-tracking, or fully discarded?

## Constraints

- **The mechanism is fixed, not re-opened.** Option A (session-scribe → one named
  file, orchestrator `question` gate) is converged; this brief designs only the
  process on top of it.
- **`question` reaches the operator only from the orchestrator.** Subagents
  cannot reach the operator (L-C6); the orchestrator is the sole convergence
  channel. Any confirmation step lives at the orchestrator.
- **`question` is a blocking pipeline state with no outgoing edge until answered**
  (orchestrator.md; gotcha Amendment A1). There is no timer; "no response" cannot
  silently produce a write.
- **session-scribe is inert without an explicit orchestrator delegation** — it
  holds no `question`, no `task`, no `bash`, no git (session-scribe.md). It writes
  the one named file only on delegation carrying operator-confirmed text, reads it
  back, and reports (steps: 15, Haiku, temperature 0).
- **File format is strict**: title / **Observed** / **Proposed lesson**, sequential
  `L-C<n>` numbering, entries inserted **before** the `## Note on placement`
  tombstone section (session-lessons-candidates.md).
- **Honesty posture is structural to the file**: content is self-labeled
  CANDIDATE / pre-graduation / not-yet-enforced. Nothing in the process may claim
  a candidate is a graduated lesson.
- **No throwaway machinery ahead of G-4c.** The real review-gated pipeline
  (Receive→Classify→Validate→Review→Append-audit) and G-4c graduation do not
  exist yet; anything captured now that the pipeline will re-shape is waste,
  against the framework's cost-per-outcome goal.
- **Two-Way Door**, but with behavioural stickiness: reversal is prose-only, yet
  the interruption cadence and debris posture set a precedent that is cheap to
  change on paper and sticky in practice.

## Approaches Considered

### Approach A: Minimal Synchronous Gate

**Summary:** Each observed lesson is proposed and confirmed individually the
moment it is noticed, via one `question` per candidate. No session cap.
Rejections fully discarded. Lightweight provenance footer.

**Positions:** 1: one-at-a-time · 2: out of scope · 3: uncapped · 4: lightweight ·
5: full discard.

**Tradeoffs:**
- Pro: Tightest feedback loop — the operator sees each lesson with its triggering
  context still fresh, so edit/approve judgment is best-informed.
- Pro: Zero debris — nothing written on rejection, cleanest honesty posture, no
  Tier-0 residue to garbage-collect.
- Pro: Smallest surface to specify and reverse; nothing speculative built ahead of
  G-4c.
- Con: **Most interruptions** — a session observing several lessons (this session
  observed L-C11/12/12b/13 together) fires that many separate `question` blocks —
  the interrupt-heavy pattern the operator flagged.
- Con: No visibility into over-triggering — a noisy orchestrator leaves no
  rejection record.

**Estimated Scope:** prose in `orchestrator.md` + footer convention. Complexity: low.

**Risk:** low — worst case is operator annoyance at interruption frequency; no data
or safety risk.

### Approach A-hybrid: Immediate-by-default with opportunistic coalescing (SELECTED)

**Summary:** Approach A's immediate synchronous gate, with one refinement: when
several candidates land together in the same short window, the orchestrator may
**coalesce** them into one `question`; a lone observation defaults to immediate.
Uncapped. Rejections fully discarded. Lightweight provenance + session id. This is
a genuine fourth position, surfaced during Pros-Cons-Fixes as the fix that
collapses the A-vs-B interruption gap.

**Positions:** 1: immediate-by-default, coalesce-when-clustered · 2: out of scope ·
3: uncapped · 4: lightweight + session id · 5: full discard.

**Tradeoffs:**
- Pro: Keeps A's wins — simplicity, no throwaway machinery, no-debris honesty
  posture, high reversibility.
- Pro: Buys back most of Approach B's interruption savings (coalesce a cluster
  into one `question`) **without** B's cross-session accumulation machinery.
- Pro: No pending batch held across the session, so **no compaction-loss hazard**
  (unlike B) — coalescing happens within a short window, not across a checkpoint.
- Con: "Same short window" is a soft judgment (though far narrower and lower-risk
  than B's "natural checkpoint," because it does not require holding state across
  a session).
- Con: Slightly more nuanced to specify than pure A (a default plus a coalescing
  case), though still a single-role prose change.

**Estimated Scope:** prose in `orchestrator.md` (immediate-default + coalescing
case) + footer convention (date + `reviewed_by` + substitution note + session id).
Complexity: low.

**Risk:** low — worst case is a coalescing judgment that batches slightly too
eagerly or too little; no data or safety risk, no state lost on compaction.

### Approach B: Batched Checkpoint Review

**Summary:** The orchestrator accumulates observed candidates during a session and
presents them as one `question` batch at a natural checkpoint (session close /
before a mode switch), with per-item approve/edit/reject. Formalizes the actually
observed pattern (L-C11–13 were added in batched passes). Soft session cap.
Rejections discarded. Lightweight provenance. This is the true shape of the
self-designed 8-step sketch, corrected.

**Positions:** 1: batched · 2: out of scope · 3: soft cap · 4: lightweight ·
5: full discard.

**Tradeoffs:**
- Pro: **Fewest interruptions** — one review event per session regardless of
  candidate count; matches how the operator actually worked this session.
- Pro: Batch presentation surfaces duplication/overlap across candidates (e.g.
  L-C4 vs L-C13's "empty return" relationship) that one-at-a-time misses.
- Pro: A soft cap gives a natural noise-ceiling signal.
- Con: **Delayed/bundled review** — the first candidate's triggering context may be
  stale by checkpoint.
- Con: Requires holding candidates across a session — volatile context (lost on
  compaction) or a new Tier-0 scratch file (a new artifact + its own append
  discipline), adding a moving part.
- Con: "Natural checkpoint" is an ambiguous trigger with no deterministic engine
  yet to enforce it — a soft edge that drifts.

**Estimated Scope:** prose in `orchestrator.md` + a Tier-0 accumulation convention
(likely a `plans/` scratch list) + footer convention. Complexity: medium.

**Risk:** medium — the compaction-loss-of-pending-candidates failure mode is real
(the orchestrator's own compaction-survival plugin exists because context is lost);
a batch held only in context can silently vanish.

### Approach C: Batched Checkpoint with Rejection Ledger

**Summary:** Approach B plus (1) rejected drafts recorded to a Tier-0 scratch
ledger (`plans/lesson-rejections.md`) with a one-line reason, for over-triggering
pattern-tracking; and (2) richer provenance — each footer also carries the session
id and the triggering observation's source (which subagent report / pipeline stage
surfaced it).

**Positions:** 1: batched · 2: out of scope · 3: soft cap · 4: **richer** ·
5: **logged**.

**Tradeoffs:**
- Pro: Only design giving a feedback signal on the orchestrator's own triggering
  quality (a proto-G-4c signal; the bias detectors are meant to feed that pipeline).
- Pro: Richer provenance is closest in shape to what G-4c will capture, so *less*
  re-shaping later if field names are chosen to match.
- Pro: Retains B's interruption savings.
- Con: **Over-engineering a placeholder** — the operator's open question 4 warns of
  exactly this; the real pipeline doesn't exist and captured fields may be
  re-shaped. The Scope Creep risk made concrete.
- Con: A rejection ledger is itself debris needing a lifecycle (cleanup? survival?
  reader?), solving a pattern-tracking problem that may not exist — L-C1–13 were all
  kept, none rejected.
- Con: Most to specify, most to reverse, most moving parts pre-engine.

**Estimated Scope:** prose in `orchestrator.md` + Tier-0 accumulation + a new Tier-0
rejection ledger + richer footer schema. Complexity: medium-high.

**Risk:** medium — low safety risk, but real *waste* risk: triage machinery built
ahead of the pipeline that will supersede it, against the cost-per-outcome goal.

## Decision Analysis

**Decision type:** Multi-option comparison of process designs (the mechanism is
already converged). **Framework:** Weighted Decision Matrix (multi-option),
preceded by the Reversibility Filter and followed by Pros-Cons-Fixes on the
closest contenders, with a Status Quo Bias check on the self-designed incumbent.

**Reversibility:** *Two-Way Door.* The process is prose in `orchestrator.md` plus
a footer convention. Reversal = edit the prose; no data migration, no external
lock-in. However, the cadence and debris posture set a **behavioural precedent**
that is cheap to change on paper but sticky in practice — that stickiness (not
reversal cost) is why the deeper matrix was warranted rather than a fast-track.

### Weighted Decision Matrix

Criteria weighted for a **low-stakes advisory** flow where the operator flagged
**interruption frequency** and **over-engineering** as live concerns, plus the
standing value of **not building throwaway machinery ahead of G-4c**.

| Criterion | Weight | A (Minimal) | B (Batched) | C (Batched+Ledger) |
|---|---|---|---|---|
| Low interruption cost to operator | 9 | 3 → 27 | 8 → 72 | 8 → 72 |
| Review quality (fresh triggering context) | 6 | 9 → 54 | 6 → 36 | 6 → 36 |
| Minimal moving parts / simplicity | 8 | 9 → 72 | 6 → 48 | 3 → 24 |
| No throwaway machinery ahead of G-4c | 8 | 9 → 72 | 7 → 56 | 3 → 24 |
| Honesty posture / no debris | 6 | 9 → 54 | 8 → 48 | 6 → 36 |
| Over-triggering visibility (proto-signal) | 4 | 2 → 8 | 5 → 20 | 9 → 36 |
| Robustness (survives compaction) | 5 | 9 → 45 | 5 → 25 | 5 → 25 |
| **Total** | | **332** | **305** | **253** |

**Matrix recommendation: Approach A (score 332).** B trails closely (305); C
trails (253), dragged down by the two heavily-weighted "simplicity" and "no
throwaway machinery" criteria.

**Caveat (winner scores poorly on the top-weighted criterion):** A scores lowest
(27) on *interruption cost*, the single highest-weighted criterion — the one axis
where B clearly beats it. A wins only because its advantage is spread across five
criteria while B's concentrates in one. This weighting is precisely the operator's
judgment, not the matrix's: if "don't interrupt me repeatedly" outranks all else,
B is the honest call despite the lower total.

### Pros-Cons-Fixes on the closest contenders (A vs B)

| Contender | Key con | Fix that narrows the gap |
|---|---|---|
| **A** (interruption-heavy) | One `question` per candidate | **Coalesce** candidates noticed in the same short window into one `question`, defaulting to immediate for a lone observation — most of B's interruption savings without B's cross-session accumulation or compaction-loss risk. |
| **B** (compaction-loss, stale context) | Pending batch lost on compaction; first candidate stale by checkpoint | Persist the pending list to Tier-0 + inline triggering context in each draft — but this adds back the moving part that made A simpler, converging B toward C. |

**Post-fix reading:** the A-with-coalescing profile (**A-hybrid**) is strongest —
it keeps A's simplicity / no-machinery / honesty wins and buys back most of B's
interruption advantage without B's compaction-loss hazard. Surfaced as a genuine
fourth position and selected.

### Positions on open questions 2–5 (where the designs converge/diverge)

- **Q2 (timeout):** All designs treat "no response" as **out of scope**. Grounded
  fact: `question` is a blocking state with no outgoing edge and no timer; an absent
  operator simply means the append never happens — the correct fail-safe (no
  unreviewed write). No design should add a timeout — it would branch for a state
  that cannot occur.
- **Q3 (session cap):** A/A-hybrid = **uncapped** (the per-use `question` gate is
  itself the noise-brake); a hard cap is unwarranted ceremony, and a soft cap is
  only useful if coupled with rejection-logging (C), which is the over-engineering
  the operator warned against.
- **Q4 (provenance):** **Lightweight** footer (date + `reviewed_by: operator via
  question` + substitution note) suffices for the interim; richer fields (C) risk
  re-shaping when G-4c lands. One cheap hedge: include the **session id** (one
  token, aids later reconciliation) but not the triggering-source machinery.
- **Q5 (rejected proposals):** **Full discard.** The stated benefit of logging
  (detect over-triggering) has no evidence of the problem — L-C1–13 were all kept,
  none rejected. A rejection ledger now solves a hypothetical and adds debris.

### Bias warnings

- ⚠️ **Status Quo Bias** — the self-designed 8-step sketch is Approach B's shape,
  and this task exists *because* it was self-decided without methodology. B was
  deliberately not given a free pass: it lost the matrix to A on simplicity and
  no-throwaway-machinery, and its compaction-loss con (never examined in the
  original sketch) was surfaced. Being "already written in the proposal file" is
  not a reason to select it.
- ⚠️ **Scope Creep Bias** — Approach C expands scope (rejection ledger + richer
  provenance) rather than forcing a choice; it solves problems (over-triggering,
  provenance reconciliation) that may not exist. Flagged and weighted down.
- ⚠️ **IKEA Effect** — the batched sketch was built this session by the
  orchestrator, risking overvaluation of it; the "if someone else built both" test
  favors A (simpler, fewer parts), which is why the sketch was not defaulted to.
- *(Below the top-3 cutoff — **Recency Bias**: "this session batched L-C11–13" is
  one session's artifact, not necessarily the right pattern to formalize; the
  operator's own open question 1 already named this doubt.)*

**Recommendation (advisory):** **Approach A-hybrid** — immediate-by-default with
opportunistic coalescing, uncapped, full discard, lightweight provenance +
session id. It wins the matrix on the criteria that matter for low-stakes advisory
content while the coalescing fix recovers most of B's only real advantage, without
B's compaction-loss hazard or C's speculative machinery. Confidence: Medium-High;
the A-vs-B call genuinely hinges on operator interruption-tolerance.

## Selected Approach

**Choice: Approach A-hybrid — Immediate-by-default synchronous gate with
opportunistic coalescing. Operator-converged** via the orchestrator's `question`
gate.

**The four sub-positions, accepted exactly as recommended:**

1. **Timeout = out of scope.** No fallback. `question` simply blocks; because it
   has no outgoing edge until answered, **no unreviewed write can happen** if the
   operator is absent — the append just never occurs (the correct fail-safe). No
   timer, no fallback branch is added.
2. **Session cap = uncapped.** No cap on escalation proposals per session; the
   per-use `question` confirmation is itself the noise-brake.
3. **Provenance = lightweight footer + session id.** Each appended entry carries a
   small footer: the date, `reviewed_by: operator (via question, this session)`, an
   explicit note that this substitutes for the not-yet-built deterministic reviewer
   step, and the **session id**. Nothing richer (no triggering-source machinery, no
   task id).
4. **Rejected proposals = full discard.** On rejection, nothing is written
   anywhere — no ledger, no Tier-0 debris, no record.

**Rationale:** A-hybrid wins the weighted matrix on the criteria that matter for
this low-stakes advisory flow (simplicity, no throwaway machinery ahead of G-4c,
no-debris honesty posture, reversibility), while opportunistic coalescing buys back
most of the interruption savings that were Approach B's sole advantage — without
B's cross-session accumulation machinery or compaction-loss hazard, and without
C's speculative rejection ledger and richer provenance. It is the most reversible
and the least likely to be re-worked when the real G-4c review-gated pipeline
lands. The operator accepted the recommendation and all four sub-positions.

## Open Questions

For `gleipnir-plan` to resolve during planning (full ATLAS):

- **Coalescing trigger definition.** What concretely counts as "the same short
  window" for coalescing? The plan must give the orchestrator a bounded,
  non-drifting rule (e.g. candidates surfaced within one delegation-result cycle,
  or before the next stage transition) — narrow enough that no state is held across
  a compaction, unlike Approach B's rejected "checkpoint."
- **Coalesced-batch `question` shape.** When coalescing, is it one `question` with
  per-item approve/edit/reject, and does an edit to one item re-confirm only that
  item? Reconcile with the existing loop-cap discipline (the sketch proposed a
  2-round edit cap — carry it forward or reconsider under A-hybrid).
- **Sequential numbering under coalescing.** How are `L-C<n>` numbers assigned when
  a batch of several is confirmed at once (assign at draft time vs at append time;
  guard against a stale highest-number read if two appends interleave)?
- **session-scribe delegation granularity.** One delegation per confirmed lesson,
  or one delegation appending a coalesced batch? Weigh against session-scribe's
  step budget (15) and its read-back verification obligation — a multi-entry append
  still must be verified entry-by-entry against disk.
- **Footer placement + session-id source.** Exact footer format within the existing
  title / Observed / Proposed-lesson entry structure, and where the orchestrator
  obtains a stable session id to stamp.
- **Interaction with the mechanism proposal.** `tier2-escalation-control-proposal.md`
  documents the (now superseded) 8-step process in its "converged escalation
  process" and "Handoff" sections; the plan should note that those sections are
  replaced by this brief's A-hybrid process, so the operator's build-mode
  application of `orchestrator.md` prose reflects A-hybrid, not the old sketch.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Escalation process prose (immediate-default + coalescing case; the confirm/edit/reject flow; uncapped; discard) | `.gleipnir/agents/orchestrator.md` (Tier-3; operator-applied) |
| Footer/provenance convention (date + reviewed_by + substitution note + session id) | Convention documented in `orchestrator.md`; applied into `.gleipnir/lessons/session-lessons-candidates.md` at append time |
| Append target + read-back verification | `.gleipnir/agents/session-scribe.md` behavior (already grant-scoped by the converged mechanism); entries inserted before the `## Note on placement` tombstone |
| Supersession note | `.gleipnir/plans/tier2-escalation-control-proposal.md` — its 8-step "converged escalation process" and Handoff step 2 are replaced by this brief's A-hybrid process |
| Mechanism (already converged, not changed here) | Option A grant on `session-scribe.md` for the single file `session-lessons-candidates.md` |
