# Goal: Brainstorm-first workflow (the decision-surfacing gate)

**Kind:** workflow goal referencing the K-2 `brainstorm` skill and the K-3
`decision-frameworks` skill. Legitimate goals-content now (it is process/
judgment content, not G-5 sequencing).

Complex tasks and **material design decisions** run through brainstorming
*before* any plan is written. This is how the framework guarantees that
decisions with real tradeoffs converge on the **operator**, not on the planner.

## Trigger

- The operator asks to "brainstorm", "design first", "what approach", "compare
  X vs Y", "which option".
- A task is classified complex: ambiguous requirements, multiple viable paths,
  cross-cutting/architectural change, or a decision with lasting/hard-to-reverse
  consequences.
- **Any point where a material design tradeoff is detected** — including
  mid-planning: `gleipnir-plan` must route such a decision back here rather than
  resolve it itself.

## Workflow

The orchestrator delegates the `brainstorm` stage to **`gleipnir-brainstorm`**,
which runs the 4-phase flow (`../skills/brainstorm/SKILL.md`):

1. **Clarify** — batch questions into a single `question` call.
2. **Explore** — investigate the codebase / external facts for constraints.
3. **Propose** — 2-3 distinct approaches with tradeoffs. On a decision point,
   activate `../skills/decision-frameworks/SKILL.md` (K-3): classify, apply a
   framework, run the 12 bias detectors, produce a `## Decision Analysis` with a
   recommendation.
4. **Converge — the precept-10 gate, surfaced by the ORCHESTRATOR.** Runtime
   constraint: a subagent's `question` cannot reach the operator, so
   `gleipnir-brainstorm` **returns its `## Decision Analysis` to the
   orchestrator** rather than converging itself. The **orchestrator** (the only
   role that can reach the operator) puts the decision to them via `question`
   and hands the operator's converged choice back. The design brief is written
   **only after** the operator converges, recording the operator's chosen
   approach. A subagent must never claim a convergence it cannot obtain
   (self-attestation).

Then the orchestrator delegates `plan` to `gleipnir-plan`, which plans **from**
the converged brief and does not re-decide the tradeoffs.

## The rule this goal enforces

A recommendation is not a decision. Spec-review passing is not convergence.
Material design decisions are the operator's, surfaced here, before the plan.
Under G-5 the convergence is a deterministic decision state the engine enforces;
pre-engine it is honoured by discipline (this goal + the brainstorm skill).

## Status

Authored. The `gleipnir-brainstorm` role and both skills exist; the G-5
engine-enforced convergence state is a later build step.
