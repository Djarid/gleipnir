# Design Brief: The cognition layer — does Gleipnir need a structural answer to "how was this reasoned through," the way G-5 gives one to "what runs when"?

_Brainstorm stage output (`gleipnir-brainstorm`). **OPERATOR-CONVERGED** (via
the orchestrator): **Approach D with the AETOS two-gate mechanism as concrete
content** — see Selected Approach. The `## Decision Analysis` below was the
input to the precept-10 convergence gate; it is retained as the decision's
justification. `gleipnir-plan` plans from the converged Selected Approach,
reading the cited AETOS source files directly._

## Problem Statement

Gleipnir has two orthogonal concerns tangled under one name:

1. **Sequencing** — *what runs when, and who does it.* This is G-5: a
   deterministic state machine routing work between roles
   (`brainstorm → plan → spec-review → test → code → quality → git → gate`).
   Well-built, structurally enforced, agent-unreachable.
2. **Cognition** — *how a problem is reasoned through such that the artifact is
   sound rather than plausible-looking.* This is ATLAS (Architect → Trace →
   Link → Assemble → Stress-test) and GOTCHA's layered separation.

G-5's founding move (GOTCHA Amendment 1) was pulling **sequencing** OUT of "the
LLM decides the order" (prose the LLM is trusted to follow) INTO deterministic
code. The claim under examination: **the thinking process was left exactly
where G-5 found the sequencing** — as prose the LLM is trusted to have
followed. Nothing MAKES ATLAS framing happen or VERIFIES a plan was produced by
it. This is lesson **L-C14** ("a good practice that lives only in habit erodes;
the decisions-table had to be baked into `plan-format.md`") raised to the level
of the *entire thinking process* rather than one table.

The question is not "add a cognition layer" — it is: **is the gap real and
wide, real but half-closed, or a framing artifact? And if real, what is the
honest, bounded, enforceable form of a fix — given that thinking, unlike
sequencing, is not mechanical?**

## Constraints

- **Tier-3, operator-only.** Everything a fix would touch — `stage-role-map.md`,
  `goals/plan-format.md`, `skills/**`, `agents/**`, `AGENTS.md`, any new guard
  in the G-1..G-6 vocabulary — is Tier-3 (operator-authored, G-1). This brief
  and any plan describe the change; only the operator applies it.
- **The framework's own goal is the binding metric.** Quality-efficient
  outcomes per LLM token (G-4d ledger). A cognition layer that adds recurring
  per-turn token cost or a new premium-model pass must be justified against
  this, not against a "more rigor is better" intuition.
- **Honesty about enforceability.** G-5 could make sequencing deterministic
  because sequencing *is* mechanical. Thinking is not. Any proposal that claims
  to "make reasoning deterministic" is proposing to enforce something
  unenforceable and must be rejected on its face. The live design space is
  bounded by what *can* be made structural.
- **The status quo was partly ratified, deliberately.** The
  roster-gotcha-loading brainstorm (Approach C, operator-converged) established
  that per-role GOTCHA *inlining* is intentional policy, not a coverage gap —
  on token-efficiency grounds. That decision is about **skill distribution**
  (who carries the methodology text). It is NOT a ruling on **cognition
  verification** (whether the methodology was genuinely applied). Conflating
  the two would be status-quo bias; they are engaged separately below.
- **Two prior artifacts frame the crux:** `goals/plan-format.md` already
  *requires* the ATLAS sections (Architect/Trace/Link/Assemble/Stress-test +
  Decisions index + Execution Workflow) as plan structure; L-C14 is the exact
  precedent for moving a good-practice from habit into enforced artifact-shape.

## The honest gap assessment (Decision Analysis Question 1)

**Finding: the gap is REAL but HALF-CLOSED, and it is asymmetric across two
axes — genuineness and coverage. It is not "wide open," and it is not a framing
artifact.** Precisely:

**What IS already structurally wired (the closed half):**

- `plan-format.md` **structurally requires** the ATLAS sections for the `plan`
  artifact: Decisions (index), Architect, Trace, Link, Assemble, Stress-test,
  Execution Workflow. Its Validation clause states a plan is *not complete*
  until every section is present and Stress-test lists concrete checkable
  criteria. So for the **plan artifact specifically**, the cognitive structure
  is a required artifact-shape, not merely habit. The L-C14 fix already
  happened for one row (the Decisions index) and, by extension, for the ATLAS
  section skeleton.
- `spec-review` (`quality-reviewer`) checks the plan **against the spec** as a
  rubric. That is a real gate.
- The `brainstorm` stage has its own required shape (Clarify → Explore →
  Propose → Converge, the `## Decision Analysis` format) — so cognition
  structure is *already* generalised to at least one non-plan stage.

**What is NOT wired (the open half) — two distinct sub-gaps:**

- **(1a) Genuineness is unverified.** Required-sections-present is a *shape*
  check. Nothing verifies the sections were genuinely *reasoned* rather than
  perfunctorily filled. A plan with a syntactically complete Trace section that
  is hand-wavy, or a Stress-test that lists vacuous criteria, passes the
  presence check. spec-review checks conformance-to-spec, not
  reasoned-through-ness. This is the residue of the prose-trust the gap names:
  the shape moved into enforced format, but the *quality of thought filling it*
  is still trusted/reviewed, not gated.
- **(1b) Coverage stops at the plan (and, weakly, brainstorm).** The
  cognitive-structure-as-required-artifact-shape pattern is enforced for
  `plan` and `brainstorm`. It is **not** a general property of every
  artifact-producing stage. `test`, `code`, and `quality` produce artifacts
  with no equivalent required cognitive shape. (The counter-argument: `code` is
  bound by the pre-written test as arbiter, and `quality` by the plan as
  rubric — so cognition there is arguably *already* bounded by a different
  mechanism. This is genuinely load-bearing and is engaged in the options.)

**So the crux (the operator's own sharpest question) resolves as:** required-
sections-in-a-doc is **not** "exactly the prose guardrail that doesn't
guarantee thinking" — it is strictly stronger than pure prose-trust, because
absence of a section is mechanically detectable and blocks completion. But it
is **also not** a guarantee of genuine reasoning, because presence ≠ quality.
The true gap is therefore narrow and specific: **(1a) no genuineness check, and
(1b) incomplete generalisation** — NOT "the cognition layer does not exist."
Framing it as "cognition-is-prose, wide open" overstates it; framing it as
"already handled by plan-format" understates it. The middle is the truth.

## Approaches Considered

### Approach A: Status quo — skills + plan-format required sections + per-role inlining (do-nothing, argued honestly)

**Summary:** Change nothing. The cognitive structure is already a required
artifact-shape for `plan` and `brainstorm`; `code` is bounded by the test,
`quality` by the plan; per-role GOTCHA inlining was already ratified as
intentional. Trust the reviewer and operator to catch perfunctory reasoning as
they do today.

**Tradeoffs:**
- Pro: zero token cost, zero rework, no new machinery. Consistent with the
  ratified roster-gotcha decision and the two-way-door minimalism it endorsed.
- Pro: honestly acknowledges that genuine reasoning is *irreducibly* a matter
  of judgment/review — arguably nothing MORE can be structurally enforced than
  what already is (shape + spec-review + operator convergence).
- Con (decisive per L-C14): the very lesson the framework already accepted says
  a good practice that lives only in habit/intent erodes. "The reviewer will
  notice perfunctory reasoning" is exactly such a habit — it is not encoded
  anywhere as an explicit obligation. L-C14 was raised on *one table*; the same
  root cause applies to genuineness-of-reasoning as a whole and is currently
  un-addressed.
- Con: the coverage asymmetry (1b) is invisible/undocumented — there is no
  statement of *why* `test`/`code`/`quality` need no cognitive-shape gate (the
  "bounded by test/plan" argument is sound but nowhere written), so it will
  re-surface as a phantom gap exactly as the gotcha-loading question did.

**Estimated scope:** none. **Risk:** low-execution / medium-strategic — the
strategic risk is that the framework's *own* accepted lesson (L-C14) indicts
this option.

### Approach B: Genuineness-review rubric — make "was this genuinely reasoned?" an explicit spec-review obligation

**Summary:** Do not invent a new stage or guard. Add to the **existing
spec-review rubric** an explicit, named adversarial check: *"is each required
cognitive section genuinely reasoned, or perfunctorily filled?"* — modelled
exactly on the hardened-path blast-radius pass already in the
prose/config-only track (`stage-role-map.md`), which pairs a spec-conformance
verdict with a separate adversarial "how could this be wrongly green?" verdict.
Cognition genuineness becomes a second rubric dimension with its own recorded
verdict, authored into `plan-format.md`'s Validation clause and the
`quality-reviewer` agent.

**Tradeoffs:**
- Pro: directly closes sub-gap (1a), the sharper of the two. Uses machinery the
  framework already has and trusts (the two-verdict hardened-path pattern), so
  it is a known, proven shape, not a novel invention.
- Pro: honest about enforceability — it does NOT claim to mechanise reasoning;
  it makes "judge the genuineness" an *explicit, recorded, non-optional review
  obligation* instead of an implicit habit. This is precisely the L-C14 move
  (habit → enforced artifact) applied at the right altitude: the thing being
  enforced is *the reviewer's obligation to check*, which IS mechanically
  enforceable (a missing verdict blocks completion), even though the judgment
  inside it is not.
- Con: moves the prose-trust one level — into the reviewer. A reviewer can rubber-
  stamp "genuinely reasoned: PASS" as perfunctorily as an author fills a section.
  Mitigation (Fix): require the genuineness verdict to cite *specific* evidence
  (which claim in the Trace is unsupported / which Stress-test criterion is
  vacuous, or an explicit "none found"), mirroring the hardened-path
  substance+correspondence rules that already forbid narrative-only attestations.
  This bounds but does not eliminate the residual judgment.
- Con: adds reviewer cost (a second verdict) to every plan. Modest; the
  spec-review pass already exists, this is one added dimension, not a new pass.

**Estimated scope:** `goals/plan-format.md` (Validation clause), `quality-
reviewer` agent (rubric), possibly `stage-role-map.md` (note the dimension).
2–3 Tier-3 files. **Risk:** low-medium — the reviewer-rubber-stamp residue is
real but is the same residue the framework already accepts for blast-radius
review, bounded by the evidence-citation requirement.

### Approach C: Elevate cognition to a first-class guard (provisional "G-7") binding methodology to artifacts

**Summary:** Name cognition as a first-class concern in the guard model — a
"G-7" that binds a required cognitive artifact-shape to each producing stage the
way G-5 binds roles to stages, with a defined enforcement mechanism (the G-5
engine refuses the stage's outgoing edge until the required cognitive artifact-
shape is present and its genuineness verdict recorded).

**Tradeoffs:**
- Pro: gives cognition parity of *status* with sequencing, memory, evidence
  — a clean conceptual home, and a single place the G-5 engine enforces
  shape-presence deterministically (which IS mechanical).
- Pro: naturally generalises across stages (addresses 1b structurally).
- Con (over-engineering risk, flagged below): a new top-level guard is heavy
  machinery for what may be fully served by "a required artifact-shape (already
  exists) + a genuineness rubric (Approach B)." The G-1..G-6 guards each close a
  distinct *adversarial* hole (unreachable guards, capability removal,
  unforgeable evidence, unblindable senses, deterministic orchestration,
  unpoisonable memory). Cognition-genuineness is not an *adversary* problem —
  no attacker forges a reasoning process; a busy LLM fills a section
  perfunctorily. Elevating a *quality* concern to *guard* status may miscategorise
  it and inflate the guard vocabulary.
- Con: the only part of "G-7" that is mechanically enforceable (shape-presence)
  is *already* what `plan-format.md` Validation + the G-5 completion edge do.
  The part that is NOT mechanical (genuineness) cannot be enforced by a guard —
  it can only be *reviewed* (Approach B). So G-7 risks being B relabelled as a
  guard, paying conceptual weight for no additional enforcement.
- Con: high framework-vocabulary rework; touches the spec's guard register.

**Estimated scope:** spec guard register, `AGENTS.md` guard table,
`stage-role-map.md`, plan-format, G-5 engine config. 5+ Tier-3/spec surfaces.
**Risk:** medium-high — largest rework; risk of miscategorising a quality
concern as a guard.

### Approach D: Generalise the plan-format pattern — required cognitive shape per artifact-producing stage (+ genuineness rubric)

**Summary:** Make "required cognitive structure" an explicit property of **every
artifact-producing stage**, each with its shape enforced like `plan-format.md`
and each with the Approach-B genuineness rubric. `brainstorm` already has one
(Clarify/Explore/Propose/Converge); `plan` has ATLAS; author the missing ones —
OR, where a stage's cognition is *already bounded by a different mechanism*
(`code` by the pre-written test, `quality` by the plan-as-rubric), **explicitly
document that as the stage's cognition binding** rather than inventing a
redundant shape. This is B (genuineness) + a deliberate, documented resolution
of the coverage asymmetry (1b).

**Tradeoffs:**
- Pro: closes BOTH sub-gaps (1a via the rubric, 1b via explicit per-stage
  cognition bindings) and — critically — does so by *documenting where cognition
  is already bounded* rather than bolting shapes onto stages that don't need
  them. This directly answers the operator's "does code/spec-review/test get any
  cognition discipline, or only plan?" with a per-stage table.
- Pro: it is the L-C14 move applied *completely*: every stage's cognitive
  discipline moves from implicit-habit into an explicit, enforced-or-documented
  artifact-shape. No phantom-gap recurrence, because the coverage decision is
  written down (the failure mode the gotcha-loading brainstorm had to fix
  post-hoc).
- Pro: still honest about enforceability — mechanical part (shape presence) is
  engine-enforceable per stage; non-mechanical part (genuineness) is the B
  rubric. No claim to mechanise thinking.
- Con: more authoring than B (a per-stage cognition-binding table + rubric),
  though much of it is *documenting the existing* binding (`code`↔test,
  `quality`↔plan) rather than new machinery.
- Con: risk of format-proliferation — inventing shapes for stages that are
  fine as-is. Mitigation (Fix): the default for a stage whose cognition is
  already bounded is *document the existing binding*, NOT author a new shape;
  new shapes only where a real gap exists (which the analysis suggests is
  *none* beyond the genuineness rubric — plan and brainstorm have shapes, code
  and quality are bounded by test/plan). In practice D collapses toward "B + a
  one-page per-stage cognition-binding table," not a stack of new formats.

**Estimated scope:** `goals/plan-format.md`, a new short per-stage cognition-
binding note (likely in `stage-role-map.md` or `skills/README.md`),
`quality-reviewer` agent. 3–4 Tier-3 files. **Risk:** low-medium — slightly
more than B, but the extra is mostly documentation of existing bindings.

## Decision Analysis

**Decision type:** Architectural tradeoff with long-term, framework-vocabulary
consequences → per the K-3 auto-selection table: **Second-Order Thinking →
Pre-Mortem**, gated first by the **Reversibility Filter**, cross-checked with a
**Weighted Decision Matrix** (four genuinely distinct structural forms to
compare objectively).

### Reversibility Filter

**Reversibility: mostly Two-Way Door, with one One-Way sub-component.**
- A, B, D are two-way doors: a genuineness rubric or a per-stage cognition-
  binding note is a cheap Tier-3 edit, removable if it proves noisy.
- C (a new "G-7" guard) is closer to a **One-Way Door**: introducing a
  top-level guard into the framework's vocabulary and spec register is
  expensive to walk back — other artifacts, tests, and mental models accrete to
  it. **This asymmetry matters:** it means C must clear a higher bar (does it
  buy enforcement the two-way-door options cannot?), and the analysis is
  calibrated toward the minimal change that closes the *real* (narrow) gap.

**Recommendation from the filter:** apply deeper analysis (below), but bias
toward the reversible options unless C demonstrably enforces something B/D
cannot — which the honest-enforceability constraint suggests it does not.

### Weighted Decision Matrix

Criteria weighted to the framework's stated goal (quality-efficient outcomes
per token), the honest-enforceability constraint, and the L-C14 principle.
Cells are score (0–10) × weight.

| Criterion | Weight | A (status quo) | B (genuineness rubric) | C (G-7 guard) | D (generalise + rubric) |
|---|---|---|---|---|---|
| Closes the REAL gap: (1a) genuineness | 9 | 1 → 9 | 9 → 81 | 8 → 72 | 9 → 81 |
| Closes (1b) coverage / stops phantom-gap recurrence | 7 | 2 → 14 | 4 → 28 | 8 → 56 | 9 → 63 |
| Honest about enforceability (no mechanised-thinking claim) | 9 | 9 → 81 | 9 → 81 | 5 → 45 | 9 → 81 |
| Token / rework economy (goal-critical) | 8 | 10 → 80 | 8 → 64 | 3 → 24 | 7 → 56 |
| Consistency w/ existing proven machinery (2-verdict pattern, L-C14) | 7 | 4 → 28 | 9 → 63 | 5 → 35 | 9 → 63 |
| Reversibility (avoids one-way vocabulary lock-in) | 6 | 10 → 60 | 9 → 54 | 3 → 18 | 8 → 48 |
| Does NOT miscategorise a quality concern as a guard | 6 | 8 → 48 | 9 → 54 | 3 → 18 | 8 → 48 |
| **Total** | | **320** | **425** | **268** | **440** |

**Ranking: D (440) > B (425) ≫ A (320) > C (268).**

- **D leads narrowly over B** because it closes both sub-gaps and — decisively
  per the framework's own history — *writes down the coverage decision*, which
  is the specific thing the gotcha-loading episode proved you must do or the
  question re-surfaces as a phantom gap. B closes the sharper sub-gap (1a) but
  leaves (1b) undocumented.
- **B is the strong, leaner fallback** — if the operator judges the coverage
  documentation (D's increment over B) to be unnecessary ceremony, B alone
  closes the genuineness gap that is the crux, using proven machinery, at lower
  authoring cost.
- **A ranks third** — cheap and honest-about-enforceability, but indicted by
  the framework's own accepted L-C14 lesson (habit erodes) and leaves the
  phantom-gap recurrence risk open.
- **C ranks LAST** despite being the most "ambitious" — it scores worst on
  enforceability-honesty, token/rework economy, reversibility, and guard-
  categorisation, because its only mechanically-enforceable part (shape
  presence) already exists (plan-format + G-5 edge) and its non-mechanical part
  (genuineness) cannot be a guard at all — it can only be a review (B). C is
  largely "B relabelled as a guard," paying one-way-door vocabulary cost for no
  additional enforcement. This is the over-engineering trap the bias check
  flags below.

### Second-Order Thinking (the crux — Question 3, can thinking be enforced at all?)

- **The load-bearing insight:** cognition decomposes into a **mechanical part**
  (does the artifact HAVE the required cognitive shape — sections present,
  criteria concrete) and a **non-mechanical part** (is the shape genuinely
  *reasoned*). The mechanical part is *already* structurally enforced for the
  plan (plan-format Validation) and can be enforced by the G-5 completion edge
  for any stage. The non-mechanical part **cannot be mechanised** — and any
  option that pretends otherwise (the seductive-false-goal C flirts with) is
  proposing the impossible.
- **Therefore the honest ceiling of a cognition layer is exactly:** (i) a
  required cognitive artifact-shape (enforceable — and mostly already built),
  PLUS (ii) an explicit adversarial *review* that the shape is genuinely filled
  (judgment, not mechanism — but the *obligation to perform and record* that
  review IS enforceable). This is not a fantasy of mechanised reasoning; it is a
  real, bounded change. **B and D are precisely this ceiling; C over-reaches
  past it; A stops short of it.**
- **Near-term (D):** one added review dimension + a per-stage cognition-binding
  table. **Second-order:** genuineness becomes a recorded, non-optional verdict
  (habit → enforced obligation, the L-C14 completion) and the coverage question
  is settled in writing. **Third-order:** the model-sizing rationale
  (`stage-role-map.md`) — "Opus at plan assumes good framing" — becomes *safe*
  rather than merely *assumed*: the genuineness rubric is the mechanism that
  makes the premium plan-stage spend actually buy sound framing instead of
  plausible-looking framing. This directly answers Question 4: a cognition layer
  does not amend G-5; it lives in the **plan-format/artifact-shape + review-
  rubric layer** and it *validates the assumption the Opus-at-plan spend rests
  on*, converting "we assume framing is good" into "framing genuineness is an
  explicit gate."

### Pre-Mortem on the leading option (D)

Assume it is 6 months later and D failed.

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Genuineness verdict becomes a rubber-stamp ("genuinely reasoned: PASS" with no substance) | **High** | High | Require the verdict to cite *specific* evidence — which claim is unsupported / which criterion is vacuous, or explicit "none found" — reusing the hardened-path substance+correspondence+post-change-state rules that already forbid narrative-only attestations. Without this, D degrades to A. |
| 2 | Format-proliferation: new cognitive shapes bolted onto stages that were fine (code, quality) | Medium | Medium | Default = *document the existing binding* (code↔test, quality↔plan), NOT author a new shape. New shapes only where a real gap exists (analysis says: none beyond the rubric). |
| 3 | Added reviewer cost erodes the token goal it was meant to protect | Medium | Medium | It is one added *dimension* on an existing pass, not a new pass/stage. Measure against the G-4d ledger; if the genuineness dimension never changes a verdict over a trial window, treat as a failing candidate (G-4c-style expiry). |
| 4 | The per-stage cognition-binding table drifts from the actual roster/stage map | Medium | Medium | Single source of truth; treat it as a companion-check of `stage-role-map.md` (the L-C20 "derived source must be updated" discipline). |
| 5 | Miscategorised later as a guard anyway ("why isn't this G-7?"), reopening C | Low | Medium | The brief explicitly records *why* it is a review-rubric-and-shape concern, not a guard (no adversary forges reasoning) — pre-empting the recategorisation the way the gotcha-loading note pre-empted its phantom gap. |

**Top risks: #1 (rubber-stamp) and #2 (format-proliferation).** Both have
concrete, already-precedented mitigations (evidence-citation; document-don't-
invent). **Verdict: Proceed with mitigations** — #1's mitigation (evidence-
citation) is load-bearing and must be a hard requirement, not advisory, or D
collapses into A.

### Bias check (12 detectors run; the 3 the operator named, surfaced first)

- ⚠️ **Over-engineering / Scope-Creep Bias (HIGH) — on Approach C.** The
  operator explicitly flagged this and it triggered hard: C builds an elaborate
  new top-level guard when "required-plan-sections (already exists) + a review
  rubric (B)" plausibly suffices. The matrix confirms C's only enforceable part
  already exists and its non-enforceable part cannot be a guard. **This is the
  primary bias risk and it points decisively away from C, toward B/D.**
- ⚠️ **Seductive-but-false-goal: "mechanising thinking" (HIGH, structural) —
  latent in any framing of C or an over-ambitious D.** The Second-Order insight
  is the antidote: cognition's non-mechanical half is *irreducibly* review, not
  mechanism. Any proposal must be checked against "does this claim to make
  reasoning deterministic?" — B and D as scoped do not; a maximalist C would.
  **Warning retained as a standing filter on whatever is chosen.**
- ⚠️ **Status-Quo Bias (MODERATE, and its inverse) — on Approach A.** Two
  directions checked: (i) defending A because per-role inlining was *already
  blessed* — but that decision was about skill *distribution*, not cognition
  *verification*; using it to defend "no genuineness check" is exactly the
  status-quo-bias trap the operator named. (ii) *Inverse* check: is the gap
  being inflated *because* change feels virtuous? Guarded against by the honest
  gap assessment, which explicitly finds the gap NARROW (half-closed), not wide
  — so the recommendation is the *minimal* option that closes the real gap
  (B/D), not the maximal one (C).

**Checked, not triggered (or triggered-and-dismissed):** *Anchoring* — A is
presented first (as the do-nothing baseline) yet ranks third, not first;
ordering did not drive scores. *Confirmation* — the genuine case *for* the
status quo (nothing more than shape+review can be enforced) was sought and is
in fact the load-bearing insight that *bounds* B/D, not evidence for A.
*IKEA/Sunk-Cost* — no defence of C on "we'd have built something impressive"
grounds; C ranks last precisely because built-weight ≠ enforcement. *Authority*
— the operator's framing ("this is L-C14 at the level of the whole thinking
process") was tested, not accepted: found *partly* right (real gap) and *partly*
overstated (half-closed, not wide open). *Availability* — the vivid "cognition-
is-prose, wide open!" framing was base-rate-corrected against what
plan-format.md already enforces.

### Recommendation (ADVISORY — the operator decides; this is NOT a convergence)

**Primary: Approach D** — generalise the plan-format pattern into an explicit
per-stage cognition-binding (documenting existing bindings where cognition is
already bounded by the test/plan, authoring shapes only where genuinely
missing — which the analysis finds is nowhere beyond the rubric) **PLUS** the
Approach-B genuineness-review rubric with a **hard, non-negotiable evidence-
citation requirement** (Pre-Mortem risk #1). This is the L-C14 move applied
completely, at the honest enforceability ceiling, using proven two-verdict
machinery, with the coverage decision written down so it cannot re-surface as a
phantom gap.

**Strong leaner fallback: Approach B** — if the operator judges D's per-stage
coverage documentation to be unnecessary ceremony, B alone closes the sharper
(genuineness) sub-gap that is the actual crux, at lower authoring cost, and is
a clean two-way door.

**Not recommended: C** (over-engineering + miscategorises a review concern as a
guard; its enforceable part already exists) and **A** (indicted by the
framework's own L-C14 lesson; leaves both sub-gaps and the phantom-gap risk
open). The honest headline for the operator: **the cognition layer is not
missing — it is half-built (required shape for plan/brainstorm) and needs
(1a) a genuineness review obligation and (1b) its coverage written down; it
does NOT need a new guard, and it CANNOT be made deterministic — cognition's
non-mechanical half is irreducibly review, not mechanism.**

## Selected Approach

**OPERATOR-CONVERGED (via the orchestrator).** Choice: **Approach D
(generalise the plan-format pattern + genuineness rubric), with the rubric's
content now concretely specified by the AETOS precedent** — Gleipnir's parent
framework at `/Users/jasonh/git/aetos/`. The abstract recommendation ("required
cognitive shape + an adversarial genuineness review at the honest-enforceability
ceiling") is now filled in with a mechanism AETOS already implements, read
faithfully from the AETOS source and verified against it (citations below,
confirmed by direct read this turn).

### The converged mechanism: AETOS's two gates

The cognition layer is realised as **two gates, both verifying the reasoning
was actually done** — one at design time (on the plan/spec) and one at review
time (on the implementation). This is exactly the mechanical/non-mechanical
split this brief's Decision Analysis concluded was the honest ceiling; AETOS
already implements it.

**Gate 1 — Design-time gate (on the plan/spec).**
*Source (verified this turn): `/Users/jasonh/git/aetos/.aetos/agents/aetos-plan.md`
lines 79–99 (the "Design Principles Section"), and its mandatory ATLAS template
in `.aetos/goals/plan-format.md`.* Every plan must carry — IN ADDITION to the
ATLAS structure `.gleipnir/goals/plan-format.md` already requires — a **Design
Principles section** with three named sub-analyses, using AETOS's exact framing
questions:
- **SOLID analysis** — each principle evaluated against the proposed design:
  Single Responsibility (each function/class has exactly one reason to change?),
  Open/Closed (extend without modifying existing code?), Liskov Substitution
  (proposed subclasses/implementations respect parent contracts?), Interface
  Segregation (proposed interfaces narrow and focused?), Dependency Inversion
  (high-level modules decoupled from low-level implementation details?).
- **DRY analysis** — duplication risks in the design: logic duplicated across
  files/functions; existing helpers that should be reused instead of
  reimplemented; constants/config repeated without a named reference.
- **Single Responsibility check** — explicitly name the single responsibility
  of each new module/class/function; if a component has more than one, split it.

**Gate 2 — Review-time gate (on the implementation).**
*Source (verified this turn): `/Users/jasonh/git/aetos/.aetos/goals/code-quality-review.md`
and `/Users/jasonh/git/aetos/.aetos/agents/quality-reviewer.md`.* Three parts:
- **The 7-category review checklist** (`code-quality-review.md` lines 62–72):
  SOLID, DRY, naming/readability/maintainability, error handling, architecture,
  performance anti-patterns, security — with **SOLID/DRY at Important severity**
  (line 59: "blocks merge unless acknowledged").
- **The two-phase [D]/[J] workflow** (`code-quality-review.md` lines 79–99):
  Phase 1 is a deterministic static-analysis-tool scan whose findings are tagged
  `[D]` ("produced by tools, not LLM inference"); Phase 2 is LLM judgment for
  SOLID / architecture / cross-file DRY / intent, tagged `[J]` ("produced by LLM
  reasoning"). **This is the key insight the operator identified: it is exactly
  the mechanical/non-mechanical split this brief's own Decision Analysis named
  as the honest ceiling — AETOS already tags which findings are tool-derived vs
  judgment-derived.**
- **The spec-vs-implementation cross-check** (`quality-reviewer.md` step 1.5,
  lines 258–264): the reviewer checks the implementation against the spec's
  **stated design intent**; a divergence from a stated Design Principle is
  flagged **Important — "block merge unless explicitly acknowledged by the
  team."** *This is the mechanically-checkable PROXY for "was the thinking
  genuine" that escapes the un-mechanisable-thinking ceiling:* you cannot gate
  whether someone genuinely thought, but you CAN gate whether the implementation
  honours the design intent the plan committed to — and a divergence is
  dispositive that either the reasoning was hollow or the implementation
  abandoned it. This is the concrete resolution of the brief's central tension
  (Decision-Analysis Question 3: genuineness can only be reviewed, not
  mechanised).

### Why this is Approach D, and where it binds

- **It is Option D with the AETOS mechanism as the concrete content.** The
  design-time gate is D's "required cognitive shape per artifact-producing
  stage" (a new required plan section); the review-time gate is D's "adversarial
  genuineness review" — now specified as the 7-category checklist + [D]/[J]
  split + cross-check rather than left abstract.
- **It does NOT amend G-5** — consistent with this brief's Question-4 finding.
  It lives entirely in the **plan-format / artifact-shape layer** (Gate 1) and
  the **review-rubric layer** (Gate 2). No new guard, no engine change.
- **It resolves the brainstorm's central tension** (genuineness can only be
  reviewed, not mechanised) via two AETOS constructs: the **[D]/[J] tagging**
  (makes explicit which half is tool-mechanical vs judgment) and the
  **spec-vs-implementation cross-check** (the enforceable proxy — honour of
  stated intent — that stands in for the un-gateable "did they think").

### It must be ADAPTED to Gleipnir, not copied blind

Four required adaptations (the operator's convergence conditions):
- **(a) Design-time gate binds in Gleipnir's own files.** Add the **Design
  Principles required section** to `.gleipnir/goals/plan-format.md` (alongside
  the ATLAS sections it already requires) and bind it to the **plan** stage.
- **(b) Review-time gate binds in Gleipnir's `spec-review` and `quality`
  stages** via `quality-reviewer` — not AETOS's single post-code quality step.
- **(c) CRITICAL — the prose/config-only track must be handled.** The classifier
  ratified this session (`stage-role-map.md`) routes prose/config plans that
  have no executable artifact. **SOLID/DRY do not apply to a prose/config plan**,
  so the SOLID/DRY design-principle analysis is **code-plan-only**. But **"design
  intent stated in the plan is honoured by what was applied" DOES apply to a
  prose/config plan** — so the **spec-vs-implementation cross-check generalises
  to the track** (it is the track's genuineness proxy), while the SOLID/DRY
  sub-analysis is gated to code-bearing plans only. This keeps the light-path /
  hardened-path split intact.
- **(d) Reuse Gleipnir's existing hardened-path attestation machinery, don't
  invent a parallel one.** Gleipnir's hardened path already carries the
  evidence-citation / substance / correspondence / post-change-state discipline
  (`stage-role-map.md`) that the AETOS [D]/[J] tagging formalises. The [D]/[J]
  distinction maps onto Gleipnir's existing two-verdict hardened-path pattern
  (deterministic scan verdict vs adversarial-judgment verdict); adopt AETOS's
  tags as the naming/formalisation of what Gleipnir already requires, rather
  than standing up a second mechanism.

**Rationale:** this concretises the Decision-Analysis Primary recommendation (D)
without over-reaching: it is the honest ceiling (required shape + reviewed
genuineness), it uses a *proven, already-implemented* mechanism from the parent
framework (not a novel invention — lowers Dunning-Kruger/over-engineering risk),
and its central move — the spec-vs-implementation cross-check as the
enforceable proxy for genuineness — is precisely the resolution this brief's own
analysis derived for the un-mechanisable-thinking problem. The Pre-Mortem's
load-bearing risk #1 (rubber-stamp) is answered structurally: the cross-check is
not a "did you reason well?" opinion but a concrete "does the implementation
diverge from the stated design principle?" check, and a divergence is
dispositive and Important-severity (blocks merge unless acknowledged).

## Next-stage handoff (post-convergence)

**`gleipnir-plan` runs ATLAS on this converged brief** to produce the exact
Tier-3 edits, **reading the AETOS source files directly** (cited above and
verified) to reproduce the rubric faithfully rather than from this description:

- `.gleipnir/goals/plan-format.md` — add the **Design Principles** required
  section (SOLID / DRY / Single Responsibility sub-analyses), code-plan-scoped
  for SOLID/DRY per adaptation (c).
- `quality-reviewer` agent + the **`spec-review` and `quality` stage** rubrics —
  the 7-category checklist (SOLID/DRY at Important), the two-phase [D]/[J] split
  mapped onto Gleipnir's existing two-verdict hardened-path pattern (adaptation
  d), and the **spec-vs-implementation cross-check** as the genuineness proxy.
- The **cross-check rule generalised to the prose/config-only track** (the
  track's genuineness proxy), with SOLID/DRY gated to code-bearing plans only
  (adaptation c).

All targets are **Tier-3** (`agents/`, `goals/`, `stage-role-map.md`) →
**operator-applied**. The plan describes the edits and their verification; the
operator writes them. Because the edits are enforcement-bearing prose/config,
they route to the **hardened path** (two-verdict spec-review + negative-check
attestation), per the Tier note below.

## Resolved by convergence (formerly Open Questions)

- **B or D?** → **RESOLVED: D**, with the AETOS mechanism as content.
- **Where does the genuineness rubric live?** → **RESOLVED:** design-time gate
  in `plan-format.md` (new Design Principles section) bound to the plan stage;
  review-time gate in `quality-reviewer` bound to `spec-review` + `quality`.
- **Is the evidence-citation requirement hard or advisory?** → **RESOLVED: it
  is structural** — the cross-check (implementation-honours-stated-intent) is a
  concrete, Important-severity, blocks-merge-unless-acknowledged check, reusing
  Gleipnir's existing hardened-path evidence/substance discipline (adaptation d).

## Open Questions (for `gleipnir-plan`)

- **Coverage-binding table location** — the per-stage cognition-binding note
  (D's coverage half) in `stage-role-map.md` vs `skills/README.md`. Anchor
  choice; not material.
- **[D]/[J] mapping detail** — the exact wording that maps AETOS's [D]/[J] tags
  onto Gleipnir's two-verdict hardened-path pattern (deterministic-scan verdict
  vs adversarial-judgment verdict) without standing up a second mechanism.
- **Prose/config-track cross-check phrasing** — the precise rule stating the
  cross-check applies to the track while SOLID/DRY is code-plan-only.
- **Trial/expiry?** — whether the genuineness dimension is a G-4c-style
  candidate that expires if it never changes a verdict over a trial window
  (ties the cognition layer to the cost ledger; defer to plan).

## Scope Sketch

| Area | Files/Modules Likely Affected (all Tier-3, operator-authored) |
|------|-------------------------------|
| **Gate 1 — design-time (Design Principles section)** | `goals/plan-format.md` — add a required **Design Principles** section (SOLID / DRY / Single Responsibility sub-analyses, AETOS `aetos-plan.md` lines 79–99 framing), bound to the plan stage; SOLID/DRY scoped code-plan-only per adaptation (c) |
| **Gate 2 — review-time (rubric + [D]/[J] + cross-check)** | `quality-reviewer` agent + `spec-review`/`quality` stage rubrics — 7-category checklist (SOLID/DRY at Important, blocks merge unless acknowledged); two-phase [D]/[J] mapped onto Gleipnir's existing two-verdict hardened-path pattern (adaptation d); **spec-vs-implementation cross-check** (AETOS `quality-reviewer.md` step 1.5) as the genuineness proxy |
| **Prose/config-only-track adaptation (critical, (c))** | `stage-role-map.md` — the cross-check generalises to the track (its genuineness proxy); SOLID/DRY analysis gated to code-bearing plans only; light/hardened split preserved |
| Per-stage cognition-binding table (D coverage half) | `stage-role-map.md` **or** `skills/README.md` — short table: plan↔ATLAS + Design Principles, brainstorm↔Clarify/Explore/Propose/Converge, code↔pre-written test, quality↔cross-check-against-plan-intent; documents existing bindings |
| Guard-vocabulary note | `AGENTS.md` / spec register — one line: cognition-genuineness is a plan-format-shape + review-rubric concern (does NOT amend G-5, is NOT a new guard) |
| Model-sizing linkage | `stage-role-map.md` — the cross-check is what makes the "Opus-at-plan assumes good framing" spend *safe* rather than merely *assumed* |
| No mechanised-thinking | The un-gateable half stays review; the enforceable proxy is honour-of-stated-intent (the cross-check), not a "did they reason well?" opinion |

**Tier note for `gleipnir-plan`:** every target is Tier-3 (operator-authored).
This brief and any plan describe the change and its verification; only the
operator applies it. The change is prose/config (enforcement-bearing:
`plan-format.md`, `quality-reviewer`, and possibly `stage-role-map.md` are in
the hardened-path set) — so under the prose/config-only track it routes to the
**hardened path** (two-verdict spec-review + negative-check attestation), not
the light path.
