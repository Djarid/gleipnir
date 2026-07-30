# Gleipnir K-2 Skills — Methodology Inheritance

This directory holds the methodology skills Gleipnir inherits from AETOS
(spec Part K-2). They are **prerequisites to planning**, not post-plan
helpers: ATLAS's Architect/Trace and GOTCHA's layered separation run *before*
any plan is drafted. A plan produced without them is unbounded, and an
unbounded plan is what forces premium-model spend downstream — the opposite
of the framework's goal (quality-efficient outcomes per LLM token).

## What is inherited

| Skill | Source | Inheritance | License |
|---|---|---|---|
| `gotcha/SKILL.md` | `aetos/.aetos/skills/gotcha/SKILL.md` (v1.0, 349 lines) | **GOTCHA-as-amended** (two deltas) | MIT, origin: aetos |
| `atlas/SKILL.md` | `aetos/.aetos/skills/atlas/SKILL.md` (v1.0, 300 lines) | **near-verbatim** (one caveat) | MIT, origin: aetos |
| `brainstorm/SKILL.md` | `aetos/.aetos/skills/brainstorm/SKILL.md` (v1.1) | **near-verbatim** (Converge = precept-10 human-decision gate) | MIT, origin: aetos |
| `decision-frameworks/SKILL.md` | `aetos/.aetos/skills/decision-frameworks/SKILL.md` (v1.2) | **near-verbatim** — this IS Gleipnir's **K-3**; analysis is input to convergence, bias signal feeds G-4c | MIT, origin: aetos |
| `tier3-coach/SKILL.md` | — (net-new) | **ORIGINAL to Gleipnir** — not inherited; Detect→Locate→Propose→Converge→Hand-off for controls that belong in an agent-unreachable layer (Tier-3, git hooks, CI, OS). Proposes only, never implements | MIT, origin: gleipnir |

**Why brainstorm + decision-frameworks were added (the decision-surfacing fix).**
During the framework's own construction, plan-stage *design decisions* (e.g. a
revert-cap model) were made inside `gleipnir-plan` and validated by the
spec-review gate, but never surfaced to the operator to decide. AETOS already
solved this: a dedicated brainstorm role runs Clarify→Explore→**Propose**→
**Converge**, where material decisions — analysed via the decision-frameworks
K-3 catalogue (10 frameworks + 12 bias detectors) — converge on the operator
*before* the plan is finalized. Gleipnir now mirrors that: `gleipnir-brainstorm`
owns these two skills and the convergence gate; `gleipnir-plan` plans only from
a converged brief.

The four AETOS skills are copied verbatim as the inheritance base, then
annotated inline. No original text was deleted; superseded passages are retained
for provenance inside `<details>` blocks and every change is marked
`[GLEIPNIR ...]`.

**One skill is original to Gleipnir, not inherited:** `tier3-coach` (origin:
gleipnir). When a control is moved out of an agent-reachable layer, it relocates
to a layer the agent *cannot* write (Tier-3 config, git hooks, CI, OS); the
agent must **propose** the control there and hand off, not smuggle it into a
reachable layer. `gleipnir-brainstorm` loads it when such a gap appears.

## The load-bearing point: layer 2 (Orchestration)

GOTCHA and ATLAS inherit cleanly **except at layer 2 (Orchestration)**, which
both describe using the v1.0 "the LLM decides which tools to use and in what
order" model. Gleipnir G-5 supersedes exactly that: sequencing lives in a
deterministic engine that calls the LLM for per-step judgment only. This one
collision is the thing to get right; everything else is a faithful copy.

If a future reader reintroduces the v1.0 LLM-decides-sequence model at layer
2, they have reopened the prose-orchestration hole that Axiom 2 forbids.

## The named deltas

### GOTCHA Amendment 1 — Orchestration (layer 2) → G-5 engine
The Orchestration layer is rewritten from "the LLM decides which tools and in
what order" to "the deterministic G-5 engine sequences transitions, loop caps
and escalation branches in code and calls the LLM for per-step judgment only;
the LLM's outputs feed the router, it does not decide order." Without this,
inheriting GOTCHA verbatim reintroduces prose orchestration at the
methodology layer.

### GOTCHA Amendment 2 — prose permission → S-2 structural immutability
"Only modify goals with explicit permission" is a prose guard (Dromi-class).
Rewritten so that enforcement-bearing config (permission definitions, guard
code, the rate table, weakening toggles) is immutable from the agent side by
the **S-2 substrate boundary, not by instruction**. The prose convention
applies to non-enforcement goals/context only.

**Productive link:** GOTCHA's graduated Guardrails list maps onto Gleipnir's
**G-4c measured graduation** and the **K-3 framework catalogue**. The manual
15-item cap is replaced by G-4c's measured criteria (fired on a real event,
measurable failure-rate reduction, under a false-positive threshold);
failing candidates expire.

### ATLAS — layer-2 caveat + plan-persistence
ATLAS maps Stress-test → Orchestration, so it inherits the same layer-2
caveat: the validate-and-report *judgment* is an LLM step, but ATLAS phase
sequencing and gate caps are **engine-controlled, not LLM-narrated**. ATLAS's
plan-persistence discipline ("write the plan to disk immediately; plan-file
writes are never blocked by read-only or plan mode; writing a plan IS
planning") is carried forward **unchanged** — it aligns with Gleipnir's
plan-format requirement (K-1).

## Who loads GOTCHA — the per-role inlining model (intentional, not a gap)

Only `gleipnir-brainstorm` loads `skill gotcha` in its Startup — and only because
it also loads `brainstorm` + `decision-frameworks` and uses the full 6-layer
methodology framing. This is **deliberate**, not an oversight:

- **Bounded/mechanical roles inline the slice they use.** notify, project-mgr,
  git-ops, and session-scribe (Haiku, per the model-sizing principle) each carry
  the one or two GOTCHA guardrails relevant to their narrow job directly in their
  own agent file (e.g. notify's "verify outputs vs inputs"; git-ops's "merge, not
  rebase"; session-scribe's verify-against-disk). Loading the full 349-line skill
  into every turn of a mechanical role would be a permanent per-turn token cost
  for content the role cannot use — against the framework's own goal
  (quality-efficient outcomes per LLM token) and its model-sizing principle
  ("Haiku for mechanical roles").
- **Judgment roles also inline, not load.** Even `gleipnir-plan` (runs the GOTCHA
  pre-flight) and the `orchestrator` (whose identity *is* Amendment 1) inline
  their relevant discipline rather than load the whole skill; the orchestrator
  *references* this file in prose deliberately, and stays prose-reference-only.

So "only 1 of 9 agents loads gotcha" is the expected, correct state — evidence of
per-role inlining, not under-coverage. Do not "fix" it by blanket-adding
`Load skill gotcha` to every agent. (Decided at the roster-gotcha-loading
brainstorm; see `plans/roster-gotcha-loading-brainstorm.md`.)

## Status

**Authored, not yet closed.** These skills are content. The enforcement they
reference (G-5 engine, S-2 boundary, G-4c graduation) does not exist yet;
it lands in later build-order steps. Until then, the amendments document the
*intended* binding, and the layer-2 collision is resolved on paper so no one
rebuilds it wrong.
