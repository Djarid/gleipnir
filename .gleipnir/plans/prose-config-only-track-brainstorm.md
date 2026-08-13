# Design Brief: Prose/Config-Only Pipeline Track (stage-role-map.md)

> **Status: converged.** The operator has converged (via the orchestrator's
> `question` tool at the precept-10 gate) on **Approach B**. This brief records
> that converged choice; the `## Decision Analysis` below is its justification.
> `gleipnir-brainstorm` did not and cannot decide this itself — it surfaced the
> analysis; the operator decided.

## Problem Statement

The G-5 pipeline (`brainstorm -> plan -> spec-review -> test -> code -> quality
-> git -> gate`, per `stage-role-map.md`) presupposes an **executable artifact**
and a **test arbiter** (Axiom 1: the test, not the model, guarantees
correctness). Some plans have neither — they are **prose/config-only**: a Tier-3
YAML permission grant, standing prose in an agent/goal file, a footer/naming
convention, with no `src/` or `tests/` byte touched.

When `gleipnir-plan` built `lesson-escalation-process.md` (a plan of exactly
this kind), it improvised a lighter mapping for that one plan: skip
`test`/`code`/`git`/`gate` in the usual sense; let `quality-reviewer` serve both
the `spec-review` stage **and** the quality role in a single pass; treat the
live-run Stress-test fixtures as the lightweight equivalent of "the test." It
explicitly flagged this as **reasonable-but-precedent-setting**, said it must
**not** be re-decided ad hoc per plan, and named the standing rule a *material
process decision* for the brainstorm/convergence gate + operator — declining to
self-decide it (lines 398–409 of that plan).

The decision under this brief: **whether, and how, to ratify a standing
"prose/config-only track" in `stage-role-map.md`** — which stages collapse, what
qualifies a plan for the track, and how (if at all) the Stress-test-as-test
substitution works — rather than letting the precedent harden by repetition.

## Constraints

- **Tier-3 weight.** `stage-role-map.md` is Tier-3/operator-authored
  (`AGENTS.md` trust-tier table; G-1). No roster agent can write it. The
  framework amends it *rarely* — so the rule must be right the first time and
  must not be over-fitted to the one plan that raised it.
- **Enforcement-integrity is a hard constraint, above efficiency.** The stated
  framework goal is quality-efficient outcomes per token, but the axioms
  subordinate efficiency to enforcement integrity. A false SUCCESS on an
  enforcement control is the worst failure mode (L-C7).
- **L-C7 is directly on point.** "For a guard whose failure mode is a false
  SUCCESS … adversarial multi-round review is … the mechanism that finds the
  false-success paths, because they are invisible to a green test count. Weight
  review effort by blast radius." The G-1 boundary preflight needed **three**
  quality rounds to catch a CARDINAL false-CLOSED plus two residual variants —
  a Tier-3 enforcement boundary.
- **Determinism for the future G-5 engine.** Whatever rule is ratified must be
  mechanically routable — the engine must decide "is this the prose/config
  track?" without re-litigating LLM judgment per plan. A trigger that requires
  per-plan judgment is not a rule, it is deferred ad-hoc-ery.
- **`quality-reviewer` is already bound to BOTH `spec-review` and `quality`**
  (`agents/quality-reviewer.md` L35–38). The stages differ by **rubric and
  time** (spec vs. blast-radius; pre- vs. post-implementation), not by
  personnel. So the precedent's real move is collapsing the *two rubrics into
  one pass*, not fusing two roles.

## Approaches Considered

### Approach A: Ratify the precedent as-is

**Summary:** Add a "prose/config-only track": trigger = no source code;
collapse `test`/`code`/`git`/`gate`; `quality-reviewer` serves both
`spec-review` and quality in one pass; live Stress-test fixtures run once = "the
test."

**Tradeoffs:**
- Pro: Cheapest and fastest; matches what already worked once.
- Pro: Transparent — the precedent was flagged, not smuggled.
- Con: Collapses exactly the *second, adversarial, false-success-hunting* rubric
  that L-C7 identifies as the only detector of a false "closed" — for the single
  highest-consequence change class (Tier-3 permission grants). "Fixtures ran
  once" is a green-count equivalent; it does not hunt false success. An
  over-broad grant (a `lessons/**` glob vs. a named file — literally fixture #10
  of the plan that set this precedent) passes fixtures while being wrong.

**Estimated Scope:** `stage-role-map.md` (one track block). **Complexity:** low.

**Risk:** high — under-reviews the highest-consequence changes; risk is highest
exactly where the track's efficiency is highest (the correlation trap).

### Approach B: Ratify a track, split by blast radius (SELECTED)

**Summary:** Define the track, but split it. Low-consequence non-enforcement
prose (docs, comments, non-enforcement goals/context) gets the light single-pass
collapse. **Enforcement-bearing config** (Tier-3 permission grants, guard /
enforcement wiring, digests) requires a **SEPARATE hardened adversarial review
pass** — distinct spec-review and blast-radius/false-success rubrics, *not
fused* — and an **explicit negative-check attestation** replacing "fixtures ran
once." Mechanical trigger: any byte under `src/`, `tests/`, any hook, or any
executable/interpreted artifact → **full pipeline, never the track**.

**Tradeoffs:**
- Pro: Buys L-C7 integrity (weight-10 criterion) exactly where it matters, while
  keeping the light path for genuinely low-blast prose.
- Pro: Preserves the precedent's *transparency* merit (it ratifies a track — it
  does not reject the idea) while fixing its integrity hole.
- Pro: Kills the "mostly config but one bash hook" trap via the mechanical
  disqualifier.
- Con: Second-most token-hungry option — deliberately spends more review on the
  high-consequence subset (intended trade, not a flaw).
- Con: The low/high blast-radius split must be made **deterministic enough for
  the engine to route on it**. If it cannot, this is grounds to fall back to C
  (see Open Questions).

**Estimated Scope:** `stage-role-map.md` (track block + trigger + hardened
sub-rule + attestation requirement). **Complexity:** medium.

**Risk:** medium — the residual risk is entirely in whether the blast-radius
split can be encoded mechanically (open question for `gleipnir-plan`'s ATLAS
pass), not in the integrity guarantee itself.

### Approach C: No track; always run the full 8 stages (fallback)

**Summary:** "No code" means `test`/`code`/`quality` report an explicit,
attested **"N/A — nothing to test"** stage transition rather than being skipped.
Uniform pipeline, no special track, no blast-radius classification.

**Tradeoffs:**
- Pro: Highest determinism — "N/A" is a clean mechanical transition; no new
  classification surface for the engine to get right.
- Pro: Never under-reviews a high-consequence change; uniform integrity.
- Con: Pays full ceremony even for a one-line comment fix — fights the stated
  efficiency goal.

**Estimated Scope:** `stage-role-map.md` (an "N/A stage" convention).
**Complexity:** low–medium.

**Risk:** low on integrity, higher on efficiency. **This is the ratified
fallback if B's split proves non-mechanical.**

### Approach D: No standing rule; keep deciding ad hoc

**Summary:** Reject the precedent-setting concern; each prose/config plan
re-derives its own mapping, reviewed at spec-review.

**Tradeoffs:**
- Pro: Zero Tier-3 amendment cost now.
- Con: Institutionalises precedent-by-repetition — the exact failure the
  convergence gate exists to close. No determinism for the engine.

**Estimated Scope:** none. **Complexity:** none. **Risk:** high (process risk).

## Decision Analysis

**Decision:** Whether (and how) to ratify a standing "prose/config-only track"
in `stage-role-map.md` (Tier-3), defining which pipeline stages collapse for a
plan with no executable artifact and how the Stress-test-as-test substitution
works — surfaced by `gleipnir-plan` as a deferred, precedent-setting process
decision it explicitly declined to self-decide.

**Reversibility framing (Reversibility Filter, run first):** Ratifying a rule in
`stage-role-map.md` is a **one-way-door-ish** decision *in practice* — not
because the text is hard to delete (mechanically a two-way door), but because
`stage-role-map.md` is Tier-3/operator-authored and the framework amends it
*rarely*. Once a track exists, future prose/config plans route through it by
default and the rule accretes precedent. So this warrants the full catalog, not
a fast-track. The *individual precedent already set* by the lesson-escalation
plan is a two-way door (its edits are reversible); the *standing rule* under
analysis is the durable commitment.

**Framework used:** **Primary — Weighted Decision Matrix** (4 discrete options
across weighted criteria). **Supporting — Second-Order Thinking + Pre-Mortem**
on the leading/precedent option. Rationale: an architectural/process tradeoff
with long-term, hard-to-amend consequences — the auto-selection table routes
architectural tradeoffs to Second-Order → Pre-Mortem, and the multi-option shape
calls for a matrix spine.

**Criteria and weights** (0–10 by importance to the goal — quality-efficient
outcomes per token, with enforcement-integrity as a hard constraint):

| Criterion | Weight | Why this weight |
|---|---|---|
| C1 — Catches false-SUCCESS on high-consequence config (L-C7 integrity) | **10** | The framework's reason to exist; a false "closed" on a permission grant is the worst failure mode |
| C2 — Token/latency efficiency (the stated goal) | 7 | Real, but explicitly subordinate to integrity per the axioms |
| C3 — Determinism / clarity for the future G-5 engine | 8 | The rule must be mechanically routable, not re-litigated per plan |
| C4 — Avoids precedent-by-repetition (what gleipnir-plan flagged) | 6 | The concern that triggered this brainstorm |
| C5 — Low amendment cost / not over-fitted to one plan | 5 | Tier-3 edits are rare; don't bake in a rule that needs re-cutting next plan |

**Scoring (raw 0–10; cell shows score×weight):**

| Criterion | W | A: Ratify as-is | B: Track + hardened sub-rule | C: Full 8, N/A stages | D: Ad hoc |
|---|---|---|---|---|---|
| C1 false-success catch | 10 | 3 → 30 | 9 → 90 | 7 → 70 | 4 → 40 |
| C2 efficiency | 7 | 9 → 63 | 7 → 49 | 4 → 28 | 6 → 42 |
| C3 determinism for engine | 8 | 6 → 48 | 8 → 64 | 9 → 72 | 2 → 16 |
| C4 avoids precedent-creep | 6 | 7 → 42 | 8 → 48 | 8 → 48 | 1 → 6 |
| C5 low over-fit / amend cost | 5 | 5 → 25 | 6 → 30 | 7 → 35 | 4 → 20 |
| **Total** | | **208** | **281** | **253** | **124** |

**Recommended by matrix: Option B (281),** with Option C (253) a credible
runner-up. **Caveat:** B is the second-most token-hungry option (C2=7, behind
A's 9) — it deliberately spends more review effort on the high-consequence
subset. That is the intended trade: it buys C1 (the dominant, weight-10
criterion) where it matters and keeps the light path for genuinely low-blast
prose.

**Why the precedent (Option A) scores worst on the criterion that matters most:**

1. **`quality-reviewer` is already bound to *both* stages**
   (`agents/quality-reviewer.md` L35–38). "Let quality-reviewer serve both" is
   **not** a new role-fusion — in the full pipeline the same role runs
   spec-review (rubric = the spec) *and* quality (rubric = blast-radius against
   the implementation), separated in **time and rubric**, not personnel. The
   precedent's real move is collapsing the **two rubrics into one pass** because
   there's no post-implementation artifact. For enforcement config that
   collapses exactly the *second, adversarial, false-success-hunting* rubric
   that L-C7 says catches false "closed" states.
2. **L-C7 cuts against A.** It observed the gates catching a CARDINAL
   false-CLOSED plus two residual variants in the G-1 boundary preflight (three
   quality rounds) — precisely a Tier-3 enforcement boundary. Its lesson: for a
   guard whose failure mode is a false SUCCESS, adversarial multi-round review is
   the mechanism that finds false-success paths, invisible to a green test
   count; weight review by blast radius. An over-broad grant
   (`lessons/**` glob vs. one named file — fixture #10 of the very plan that set
   this precedent) **passes a fixtures-ran-once check while being wrong.**

**Second-Order Thinking on Option A:**
- *Near term (first few plans):* smooth, cheap, fast — one reviewer pass, live
  fixtures, done. Looks like a clean win.
- *Far term:* every future Tier-3 permission grant and enforcement-wiring change
  inherits the collapsed adversarial pass by default. **Key insight: the track's
  efficiency is highest exactly where its risk is highest — the plans that
  qualify as "just config" are disproportionately Tier-3 enforcement grants, the
  most consequential edits in the system.** That correlation is the trap.

**Pre-Mortem on Option A (assume it failed):**

| # | Failure mode | Likelihood | Impact | Mitigation (→ points to B) |
|---|---|---|---|---|
| 1 | Over-broad grant ships (glob vs named file) because fixtures passed and no adversarial second rubric ran | M | **H** | Separate blast-radius/false-success pass for enforcement config (B) |
| 2 | "Prose/config-only" claimed for a plan that touches a small script/hook, dragging real code through the light track | M | H | Precise trigger: any `src/`/`tests/`/hook/executable byte disqualifies (B/C) |
| 3 | Future G-5 engine can't deterministically route "is this prose-only?" — LLM re-litigates per plan | M | M | Mechanical trigger on paths-touched, not judgment (B/C) |
| 4 | Precedent hardens silently; nobody revisits because "it's the rule now" | M | M | Ratify explicitly with the high-consequence carve-out visible (B) |

Top risks #1 and #2 are mitigated by Option B and a tightened trigger — why B
outscores A on C1 by 60 weighted points.

**On the runner-up (Option C):** C scores highest on determinism (C3=9) — "N/A —
nothing to test" is a clean, mechanically-checkable transition, preserving full
review depth uniformly so it never *under*-reviews. Its weakness is efficiency
(C2=4): full ceremony even for a one-line comment fix. C is the right choice if
the operator weights uniform-integrity-and-simplicity over efficiency, or
distrusts blast-radius classification as a new judgment surface. **B and C agree
on the thing that matters (don't shortcut review for enforcement config); they
differ only on whether low-blast prose earns a lighter path.** If B's split
can't be encoded deterministically, C is the safe fallback and still beats the
precedent.

**Trigger-boundary line (accepted alongside B):**
- **Clean disqualifier:** *any* byte under `src/`, `tests/`, any hook, or any
  executable/interpreted artifact → **full pipeline, never the track** (kills
  Pre-Mortem risk #2).
- **Track-eligible:** edits confined to prose (docs/goals/context) and
  declarative config (YAML grants, digests), no executable artifact at all.
- **Within track-eligible, the B split:** enforcement-bearing config (Tier-3
  grants, guard wiring, digests) → hardened path (separate adversarial pass +
  explicit negative-check attestation); non-enforcement prose → light single
  pass.

**Bias check:**
- ⚠️ **Status Quo Bias — detected (primary).** The framing invited ratifying
  "the one precedent that already happened" as the default, giving A less
  scrutiny than it deserved. Corrective test — *"Would we choose the single-pass
  collapse for a Tier-3 permission grant if starting fresh, knowing L-C7?"* —
  answer: no. A got full scrutiny and fell to last-but-one on the dominant
  criterion.
- ⚠️ **IKEA Effect / Sunk Cost — detected (secondary).** The precedent is
  `gleipnir-plan`'s own improvisation; pull to over-value it because it was
  built and "worked once." Corrective: the one live run *worked* only in the
  sense that fixtures passed — exactly the green-count L-C7 warns is blind to
  false success. Evaluated on future value only, the hardened split wins. The
  precedent's *transparency* (flagged, not smuggled) is genuine merit and is
  preserved under B — B ratifies a track, it does not reject one.
- ⚠️ **Scope Creep Bias — checked, not firing.** B is not "keep all options
  open" — it makes a definite choice with a mechanical trigger. It narrows, not
  broadens. (Watch that the low/high split doesn't itself become an ad-hoc
  per-plan judgment — if it can't be made mechanical, prefer C.)
- Others scanned (Anchoring on the precedent's wording; Authority from
  `gleipnir-plan`'s recommendation) — present but subordinate; the matrix
  re-scored each option independently rather than adjusting from the precedent
  anchor.

**Recommendation (advisory, superseded below by the operator's converged
choice):** Adopt Option B — ratify a documented "prose/config-only track" split
by blast radius, with a mechanical trigger, falling back to Option C if the
split proves non-mechanical. Reject A (under-reviews the highest-consequence
class, contra L-C7) and D (institutionalises precedent-by-repetition). B/C
separation is modest (281 vs 253); both are decisively above A/D.

## Selected Approach

**Choice:** **Approach B — ratify a "prose/config-only track" in
`stage-role-map.md`, split by blast radius.** *(Operator-converged via the
orchestrator's `question` tool at the precept-10 gate. The Decision Analysis
above is the input to this convergence, not the decision.)*

**Converged content:**
- Add a documented **"prose/config-only track"** to `stage-role-map.md`.
- **Light path** for low-consequence, non-enforcement prose (docs, comments,
  non-enforcement goals/context): the single-pass collapse.
- **Hardened path** for **enforcement-bearing config** (Tier-3 permission
  grants, guard/enforcement wiring, digests): a **SEPARATE hardened adversarial
  review pass** — distinct spec-review and blast-radius/false-success rubrics,
  **not fused into one pass** — plus an **explicit negative-check attestation**
  that **replaces** the "fixtures ran once" substitution. (This directly answers
  the plan's own fixture #10 concern: a negative check that a grant is *not*
  over-broad, e.g. that a `lessons/**` glob is NOT present where a single named
  file is intended.)
- **Mechanical trigger (accepted alongside B, not separately contested by the
  operator):** *any* byte written under `src/`, `tests/`, any hook, or any
  executable/interpreted artifact disqualifies a plan from the track → it runs
  the **full 8-stage pipeline**, no matter how small the code portion.
  Track-eligibility requires edits confined to prose and declarative config with
  **no executable artifact at all**.

**Rationale:** Buys L-C7 integrity (the weight-10 criterion) exactly where it
matters — the highest-consequence change class — while preserving the light path
where blast radius is genuinely low. It fixes the precedent's integrity hole
without discarding its transparency merit. Rejects the as-is precedent (A, which
under-reviews Tier-3 grants) and ad-hoc-ery (D, precedent-by-repetition). See
the Decision Analysis for the full scoring, second-order, pre-mortem, and bias
reasoning.

**Load-bearing caveat carried into planning — the fallback-to-C clause.**
Approach B is contingent on the low/high blast-radius split being made
**deterministic enough for the future G-5 engine to route on without LLM
judgment at each plan.** If `gleipnir-plan`'s ATLAS Architect/Trace pass finds
the split **cannot** be encoded mechanically to that standard, that is **grounds
to escalate back to the operator for a fallback-to-Option-C decision** (full
8-stage pipeline with attested "N/A — nothing to test" transitions), per this
analysis's own stated fallback clause. **`gleipnir-plan` must NOT decide the
fallback unilaterally** — a fallback from B to C is a material change to the
operator's converged choice and must return to the convergence gate. Planning
proceeds on B unless and until that determinism obstacle is actually hit.

## Open Questions

Deferred to `gleipnir-plan`'s ATLAS pass (concrete mechanics, not new material
tradeoffs — with the one escalation trigger noted):

1. **Exact `stage-role-map.md` amendment text** — the precise wording of the
   track block, the two paths, and where it sits relative to the existing map
   and binding rules.
2. **Precise mechanical-trigger wording** — how "any byte under `src/`,
   `tests/`, any hook, or executable/interpreted artifact" is expressed so the
   engine (and, pre-engine, the orchestrator) can apply it unambiguously.
   Includes settling edge cases (e.g. is a generated/committed digest an
   "artifact"? is a Makefile/CI YAML "executable"?).
3. **CRITICAL — can the low/high blast-radius split be encoded deterministically
   enough for G-5 to route on it without per-plan LLM judgment?** If **no**,
   escalate to the operator for the fallback-to-C decision (per the load-bearing
   caveat above). Do not decide the fallback in the planner.
4. **Attestation form** — what the "explicit negative-check attestation" for the
   hardened path concretely looks like (who produces it, what it asserts, how it
   is verified), consistent with L-C8 anti-self-attestation.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| The ratified rule (Tier-3, **operator-applied**, agent-unwritable) | `.gleipnir/stage-role-map.md` — new "prose/config-only track" section + trigger + hardened sub-rule + attestation requirement |
| Reference / consistency (may need a pointer, operator-authored) | `.gleipnir/AGENTS.md` (guard-status / pipeline framing), possibly `.gleipnir/agents/quality-reviewer.md` if the two-rubric-separated pass needs to be named there |
| Precedent record (informational) | `.gleipnir/plans/lesson-escalation-process.md` (the plan that raised this; its improvised mapping is now superseded by the ratified track) |
| Planning input (this brief) | `.gleipnir/plans/prose-config-only-track-brainstorm.md` (Tier-0, this file) |

## Next-Stage Handoff

**Next stage: `plan` — bound to `gleipnir-plan`.** `gleipnir-plan` runs **ATLAS
Architect/Trace** on this converged brief to produce the **exact
`stage-role-map.md` amendment text**, the precise mechanical-trigger wording, and
the determinism assessment of the blast-radius split (Open Question #3). It plans
*from* this converged brief and does **not** re-decide the material tradeoff
(Approach B is converged) — but it **must escalate back to the operator** if the
split proves non-mechanical (the fallback-to-C clause), rather than deciding
that itself.

Then: **`spec-review`** (bound to `quality-reviewer`, read-only) checks the
amendment text against this brief and the spec. Then **operator application** —
`stage-role-map.md` is Tier-3, **agent-unwritable**: no roster agent (including
`gleipnir-plan` or `gleipnir-brainstorm`) can write it; only the operator
applies the ratified text (G-1/G-6).
