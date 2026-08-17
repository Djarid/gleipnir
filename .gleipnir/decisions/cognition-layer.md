# Decision: the cognition layer (AETOS two-gate mechanism, adapted)

**Status: decided and applied (operator, build mode). Durable decision record
(Tier-3).** Converged via the orchestrator-surfaced decision gate (brainstorm
Decision Analysis → operator convergence → plan → hardened-path spec-review,
2 rounds). Plan of record: `../plans/cognition-layer.md`; brainstorm:
`../plans/cognition-layer-brainstorm.md`.

## The gap

The operator identified that **G-5 conflates sequencing with thinking**. G-5 is
a deterministic state machine that routes work between roles (`brainstorm →
plan → spec-review → test → code → quality → git → gate`) — it answers *what
runs when, and who does it*. It has no answer to *how a problem is reasoned
through* such that the artifact is sound rather than plausible-looking. ATLAS
and GOTCHA existed only as skill files plus a prose note ("methodology runs
ahead of the pipeline") that the planner was TRUSTED to have followed — a prose
guardrail, the exact Dromi-class anti-pattern G-5 itself was created to kill for
orchestration. G-5 solved the orchestration-is-prose problem and left the
cognition-is-prose problem untouched, one layer down.

The brainstorm's honest refinement: the cognition layer is **half-built, not
missing** (`plan-format.md` already required the ATLAS section shape), and the
deepest truth is that **thinking cannot be mechanised** — only its structure
required and its genuineness reviewed. The fix is therefore (i) a required
artifact-shape (enforceable) plus (ii) an explicit review obligation that the
shape is genuinely filled (judgment, made checkable via a proxy).

## Converged decisions

- **D1 — Adopt AETOS's two-gate mechanism (Approach D with the AETOS content).**
  AETOS (Gleipnir's parent, `../../aetos/`) already solves this with two gates,
  both verifying the reasoning was done. Design-time: a Design Principles
  section on the plan (`../../aetos/.aetos/agents/aetos-plan.md` L79–99).
  Review-time: a 7-category SOLID/DRY rubric with a `[D]`/`[J]` deterministic/
  judgment split (`../../aetos/.aetos/goals/code-quality-review.md`) and a
  spec-vs-implementation cross-check at Important severity
  (`../../aetos/.aetos/agents/quality-reviewer.md` step 1.5). This does NOT
  amend G-5 (see D5); it lives in the plan-format artifact-shape layer + the
  review-rubric layer.

- **D2 — Design-time gate is three-case-routed, reusing the prose/config track's
  Axis-1 set `X`.** SOLID/DRY/SRP need object/function structure, which "produces
  an executable artifact?" (Axis-1's `X`) does NOT always imply. So: (i)
  OOP/functional code (`P ∩ X ≠ ∅`, has OOP structure) → full SOLID+DRY+SRP+
  Design Intent; (ii) executable-but-non-OOP (Makefile / CI YAML / shell /
  `bin/**` / `hooks/**` / shebang-config) → DRY+Design Intent, SOLID/SRP attested
  `N/A — no object/function structure`; (iii) prose/config-only (`P ∩ X = ∅`) →
  Design Intent only, SOLID/DRY/SRP attested `N/A — no executable artifact`. ONE
  predicate (`X`), one author-declared/reviewer-checkable refinement — no second
  classifier. Gleipnir adaptation: AETOS applies SOLID uniformly; the case-(ii)
  and case-(iii) split is Gleipnir-specific (AETOS has no prose/config track and
  did not separate executable-but-non-OOP).

- **D3 — Review-time gate COMPOSES into the existing hardened path, not a
  parallel mechanism.** SOLID/DRY is a checklist *dimension of* the existing
  "Blast-radius / false-success" pass (not a third rubric); the cross-check is a
  *sub-check of* the existing passes; `[D]`/`[J]` tags *annotate* the existing
  negative-check attestation `evidence` field. The hardened path keeps exactly
  two non-fusing passes. Gleipnir adaptation: AETOS's `[D]` findings flow from a
  `codegraph_quality_scan` provider-registry MCP Gleipnir does not have; the tag
  *semantics* are adopted (`[D]` = `bin/gleipnir-sandbox` output where a code
  plan exists; `[J]` = judgment / grep), the provider registry is not.

- **D4 — The cross-check is TWO distinct checks bound to two stages.** At
  `spec-review` (pre-implementation) it is the intent-quality check: is the
  Design Intent a specific, falsifiable claim, or a vacuous aspiration? A vacuous
  intent is rejected there (a spec-conformance finding). At `quality`
  (post-implementation) it is the honour check: does the applied implementation
  honour the stated Design Intent/principle? A divergence is **Important
  severity — it blocks the `git` stage unless explicitly acknowledged by the
  operator** (the reviewer never self-clears it, L-C8; the operator is Gleipnir's
  decision authority, replacing AETOS's "the team"). For a prose/config-only
  plan (single collapsed pass) both run once against the applied edit.
  **Acknowledgement is recorded in the durable decision record (this file or the
  change's own), NOT the disposable Tier-0 plan.**

- **D5 — The load-bearing anti-vacuity rule.** The Design Intent MUST be a
  specific, falsifiable claim (names a concrete responsibility / boundary /
  constraint a reviewer could point to a violation of). A generic quality
  aspiration ("clean", "correct", "well-structured", "follows best practice") is
  rejected at spec-review, exactly as the hardened path's SUBSTANCE rule rejects
  narrative attestation evidence. Without falsifiability the cross-check is
  theatre (any implementation "honours" a vacuous intent). This closes the
  brainstorm's Pre-Mortem risk #1 (the genuineness verdict becomes a
  rubber-stamp) and was the round-1 spec-review's primary blocking finding.

- **D6 — Not a new guard; does not amend G-5.** Cognition-genuineness is a
  plan-format-shape + review-rubric concern. No adversary forges a reasoning
  process (each G-1..G-6 guard closes an adversarial hole); a busy LLM filling a
  section perfunctorily is a quality concern answered by review, not a guard. Its
  mechanically-enforceable part (shape presence) is the `plan-format.md`
  Validation + the G-5 completion edge; its non-mechanical part (genuineness) is
  irreducibly review, with the cross-check as its enforceable proxy. The
  recategorisation-as-"G-7" question is pre-empted here so it cannot re-surface.

## Model-sizing linkage

The cross-check is what makes the "Opus-at-plan assumes good framing" spend
(`stage-role-map.md` §"Model-sizing principle") *safe* rather than merely
*assumed*: it converts "we assume the framing is good" into "framing genuineness
is an explicit, recorded review obligation whose divergences block the git
stage."

## What was applied

Operator-applied Tier-3 edits (build mode), per `../plans/cognition-layer.md`:

- `goals/plan-format.md` — new required section 8 **Design Principles**
  (three-case-routed, with the anti-vacuity rule) + Validation clause update.
- `agents/quality-reviewer.md` — new **Cognition review (AETOS Gate 2)**
  subsection (SOLID/DRY dimension, the two-stage cross-check, `[D]`/`[J]` tags).
- `stage-role-map.md` — new **Cognition layer** subsection (composition rules,
  per-stage cognition-binding coverage table, guard-vocabulary note,
  model-sizing linkage).
- this decision record.

## Honest status

**Authored, takes effect next session** (agent-file / config changes are
restart-gated). The mechanically-enforceable half (required Design Principles
shape, Validation-blocking) is real; the genuineness half is a review obligation,
not a mechanism, by the design's own honest ceiling — the cross-check is the
strongest checkable proxy for it, not a guarantee that reasoning occurred.

## Known seams

- The intent-quality bar ("name a violable constraint") can be satisfied by a
  trivial-but-technically-falsifiable claim; genuineness remains ultimately a
  review judgment, disclosed honestly, not eliminated.
- Case (i)-vs-(ii) routing ("has object/function structure?") is a bounded
  reviewer judgment (a shell script with helper functions vs a genuine module is
  not always crisp), materially narrower than the defect it fixes and of the
  same kind as the existing Axis-2(b) content-pattern predicate.
