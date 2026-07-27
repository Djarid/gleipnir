---
version: "1.1"
name: brainstorm
description: "Collaborative design exploration for complex tasks. Guides through clarification, codebase exploration, multi-approach analysis, and convergence on a design brief."
license: MIT
metadata:
  version: "1.1"
  origin: aetos
  inherited_by: gleipnir
  inheritance: near-verbatim
  amendments:
    - "Converge = the precept-10 human-decision gate: material design decisions converge on the operator BEFORE the brief/plan is finalized. Under G-5 this is an engine-enforced decision state, not prose the LLM may skip."
    - "Convergence is surfaced by the ORCHESTRATOR, not a subagent: a subagent's `question` cannot reach the operator, so a brainstorm subagent produces the Decision Analysis and RETURNS it; the orchestrator asks the operator and hands back the converged choice. A subagent must never claim a convergence it cannot obtain (self-attestation)."
---

> **GLEIPNIR INHERITANCE NOTE (read first).** Inherited near-verbatim from AETOS
> (MIT, origin: aetos). Gleipnir adds one binding, marked `[GLEIPNIR]` at
> Phase 4: **Converge is the precept-10 human-decision gate.** The operator
> decides between proposed approaches (and any material design tradeoff a
> `decision-frameworks` analysis surfaces) *before* the design brief is written
> and *before* planning proceeds. This exists because the framework's own build
> repeatedly made plan-stage design decisions (e.g. a revert-cap model) inside
> the planner and never surfaced them to the operator — the exact failure this
> gate closes. Under G-5 the convergence is a deterministic decision state the
> engine enforces (no outgoing edge until the operator answers), not an LLM
> courtesy. `gleipnir-brainstorm` owns this skill; `gleipnir-plan` plans only
> *from* a converged brief and must not decide material tradeoffs itself.

# Brainstorming Skill

Use this skill when a task is **complex** — unclear requirements, multiple valid
implementation paths, architectural changes, or when the user explicitly requests
design exploration. This skill prevents premature specification of under-defined
work.

## When to Use

- User says "brainstorm this", "design first", "think through", "what approach"
- Task involves cross-cutting architectural changes
- Multiple valid approaches are apparent from the request
- Requirements are ambiguous or vague

## 4-Phase Workflow

### Phase 1: Clarify

> **Visual companion offer:** Before sending Phase 1 questions, send the
> standalone visual companion offer first. See [Visual Companion Integration](#visual-companion-integration).

Gather the information needed to explore meaningfully. Batch ALL clarifying
questions into a **single `question` tool call** — never ask one question at a
time.

Questions to consider:
- What problem are they actually trying to solve? (not the solution)
- What constraints exist? (technical, compatibility, timeline)
- What have they already considered or ruled out?
- What does success look like?
- Are there existing patterns in the codebase to follow or improve?

**Do not jump to a solution.** Understand the problem first.

### Phase 2: Explore

Investigate the codebase for context relevant to the request:
- Architecture and existing patterns
- Files and modules likely affected
- Prior art (similar implementations, related specs in `.opencode/plans/`)
- Constraints implied by the codebase (data flow, API boundaries, test patterns)
- `.aetos/context/` for domain knowledge

Use `glob`, `grep`, and `read` to build a mental model. The goal is to have
enough context to propose meaningfully different approaches — not to design the
solution yet.

### Phase 3: Propose

Present **2-3 approaches** (distinct strategies) to the user. Each approach must include:

- **Summary**: 1-2 sentences describing the approach
- **Tradeoffs**: pros and cons (minimum 2 pros, 1 con)
- **Estimated Scope**: files affected, complexity level (low/medium/high)
- **Risk**: low/medium/high — what could go wrong or require rework

The approaches must be **genuinely distinct** — different strategies, not
variations on the same theme. Do not present only one approach disguised as
multiple alternatives.

Example structure:
```
### Approach A: <name>
**Summary:** <1-2 sentences>
**Tradeoffs:**
- Pro: ...
- Con: ...
**Estimated Scope:** <files>, <complexity>
**Risk:** <level> — <what could go wrong>
```

### Phase 4: Converge

Present the approaches to the user for selection:
1. Summarize the trade-space clearly
2. Make a recommendation if one approach is clearly better
3. Ask the user to confirm or refine their choice

The user MUST confirm the approach — do not skip the user approval step. If the
user rejects all approaches, ask follow-up questions to understand what is
missing and propose revised approaches. After 2 rounds of rejection, ask: "Would
you like to describe your preferred approach, and I'll document it as the design
brief?"

Once the user confirms, write the design brief to disk (see Output Format below).

> **[GLEIPNIR] Converge is the precept-10 human-decision gate — and it is
> surfaced by the ORCHESTRATOR, not by a subagent.** This is a hard runtime
> constraint, learned by dogfooding: **a subagent's `question` tool does NOT
> reach the operator** — it surfaces only inside the subagent's own
> sub-session. So a brainstorm *subagent* that "asks the operator to converge"
> and records an answer has **converged with itself** — self-attestation, the
> exact failure this whole gate exists to prevent. Therefore:
>
> - **If you are running as a subagent** (e.g. `gleipnir-brainstorm`): run
>   Clarify → Explore → Propose, produce the `## Decision Analysis` (options +
>   framework + bias check + recommendation), and then **RETURN it to the
>   orchestrator. Do NOT call `question` to "converge", do NOT decide, and do
>   NOT write the design brief for a material decision until the operator's
>   choice has come back from the orchestrator.** Never claim a convergence you
>   cannot structurally obtain.
> - **The orchestrator** (a primary agent, which *can* reach the operator) puts
>   the decision to the operator via `question`, then hands the operator's
>   **converged choice** back so the brief records it.
>
> Every **material design decision** (a tradeoff between viable approaches; a
> choice a `decision-frameworks` analysis flagged; anything with lasting or
> hard-to-reverse consequences) is decided by the **operator** this way, before
> the brief is finalized. `gleipnir-plan` plans *from* the converged brief and
> does **not** decide these itself. The Decision Analysis is the *input* to
> convergence, never the decision. Under G-5 this is a deterministic decision
> state with no outgoing edge until the operator answers; pre-engine it is
> honoured by this discipline. Do not confuse a downstream spec-review passing
> with operator convergence — different gates: convergence decides *what*,
> spec-review checks the plan built on that decision.

## Output Format: Design Brief

Write the design brief to `.opencode/plans/<name>-brainstorm.md` where `<name>`
is a slugified version of the task description.

```markdown
# Design Brief: <title>

## Problem Statement

<What problem the user is solving — not the solution.>

## Constraints

- <Technical constraints>
- <Compatibility requirements>
- <Time/scope constraints>

## Approaches Considered

### Approach A: <name>

**Summary:** <1-2 sentences>

**Tradeoffs:**
- Pro: ...
- Pro: ...
- Con: ...

**Estimated Scope:** <files, complexity>

**Risk:** <low/medium/high — what could go wrong>

### Approach B: <name>

... (same structure)

### Approach C: <name> (optional)

... (same structure)

## Selected Approach

**Choice:** Approach <X>

**Rationale:** <Why this approach was chosen over others>

## Open Questions

- <Anything unresolved for @aetos-plan to address>

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| ... | ... |
```

## Anti-Patterns

**Anti-Pattern 1: Jump to a solution before exploring alternatives**
Do not jump to a solution before exploring the problem space and alternatives.
The Explore phase exists for a reason — skip it and you risk solving the wrong
problem or missing a better approach.

**Anti-Pattern 2: Present only one approach disguised as multiple**
Do not present fake alternatives that are minor variations of the same strategy.
Each approach must represent a meaningfully different design decision with distinct
trade-offs. If only one approach is apparent, say so — "This task appears to have
a clear solution path" — then document it as the recommended approach.

**Anti-Pattern 3: Write implementation code**
Do not write implementation code during brainstorming. The output is a design brief only.
No Python, no TypeScript, no shell scripts. Pseudocode is acceptable to illustrate
an approach, but actual implementation belongs in the code phase.

**Anti-Pattern 4: Skip the user approval step**
The user MUST confirm the selected approach before the design brief is written.
Do not skip the user approval step. Never write the design brief without first
presenting approaches and receiving explicit confirmation. If the user says "go
ahead" or "pick one" — that counts as approval, but they must say something.

## Decision Framework Integration

When a decision point is detected during Phase 3 (Propose), load and apply the
`decision-frameworks` skill to bring structured analysis to the choice.

### Decision-Point Detection Patterns

These natural language patterns indicate a decision point has been reached:

- "should we use X or Y?"
- "compare A vs B" / "compare A versus B"
- "what's the best approach for..."
- "which option", "choose between"
- "tradeoff between" / "trade-off"
- "pros and cons of"

### Activation During Phase 3 (Propose)

When one of the above patterns is detected (or when the conversation clearly
involves choosing between options):

1. **Classify the decision type** — binary, multi-option, architectural,
   prioritisation, risk assessment, or go/no-go
2. **Select a framework** from the auto-selection table in the
   `decision-frameworks` skill
3. **Apply the framework's process steps** to the options under consideration
4. **Run bias detectors** against the current analysis — check all 12 bias
   trigger patterns from the `decision-frameworks` skill
5. **Surface bias warnings** naturally in the conversation (at most 3 warnings;
   note if others were also detected)

### Design Brief Integration

When a decision framework is applied, the design brief MUST include a
`## Decision Analysis` section:

```markdown
## Decision Analysis

**Framework used:** <framework name and rationale for selection>

**Analysis results:**
<framework output format populated with this decision's data>

**Bias warnings:** <any bias detectors that triggered, or "None detected">

**Recommendation:** <the framework's recommended option>
```

This section is appended after the "Approaches Considered" section or added as
a standalone section.

### Fallback

If the `decision-frameworks` skill cannot be loaded, continue with the standard
Phase 3 workflow — present approaches with tradeoffs. Do not fail the
brainstorming session because the skill is unavailable.

## Visual Companion Integration

When a brainstorming session begins, load and apply the `visual-companion` skill
to offer browser-based rendering for content that benefits from rich visual
presentation.

### Standalone Offer Step

Before sending Phase 1 clarifying questions, send the visual companion offer as
a **standalone** message — separate from all questions and separate from any
other content. Never combine the consent offer with Phase 1 questions.

Example sequence:
1. Send standalone visual companion offer (its own message, nothing else)
2. Wait for explicit yes/no response
3. Then send Phase 1 clarifying questions as a normal `question` tool call

### Per-Question Routing

After the user responds to the consent offer, apply the `visual-companion`
content classification table to route each question or content item:

- **Visual content** (comparison tables, architecture diagrams, option matrices,
  flowcharts) → render in browser via Marionette
- **Text content** (yes/no questions, single-value answers, short clarifying
  questions, plain prose) → text stays in terminal

Mixed batches are handled item-by-item: visual items go to the browser, text
items stay in the terminal. Inform the user when splitting a batch.

### Terminal-Only Fallback When Declined

If the user declines the visual companion, all phases produce terminal-only
output without errors. All phases (Clarify, Explore, Propose, Converge) work
fully in terminal-only mode — there is no missing functionality. Do not
re-prompt after a decline in the same session.

### Fallback When Visual Companion Is Unavailable

If the `visual-companion` skill cannot be loaded, or if Firefox/Marionette is
unavailable (connection refused on port 2828), skip the offer step and default
to terminal-only mode for all content. The brainstorming session continues
normally with terminal output only.

## Resilience

If the `brainstorm` skill cannot be loaded, fall back to the inline instructions
in the agent template. The skill provides depth; the agent template provides
resilience. Never refuse to produce output.

## Edge Cases

- **Single obvious approach**: Present it as "Approach A (Recommended)" with a
  note that this task has a clear path. Still complete the full design brief format.
- **User says "just pick one"**: Treat as immediate convergence — write the brief
  with the agent's recommendation as the selected approach.
- **Context compaction mid-flow**: Check `.opencode/plans/` for a partial
  `*-brainstorm.md` on resumption. Continue from where the brief left off.
