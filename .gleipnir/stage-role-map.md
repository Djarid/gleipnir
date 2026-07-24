# Stage-to-Role Map

**The net-new artifact required by spec S-1.3.1.** The roster is
inherited-and-audited from AETOS v4; this map is the one piece authored fresh,
because G-5 does not exist in AETOS and its pipeline states must bind to
concrete roles. It is constrained to bind only to roles that exist in the
roster (`.gleipnir/agents/`).

**Status: authored, not yet closed.** In the finished framework the G-5
deterministic engine reads this binding and emits delegations in code. Today
the `orchestrator` agent follows it as prompt-level guidance. When the engine
lands, this file becomes the engine's configuration rather than an agent
instruction.

## Methodology runs ahead of the pipeline

ATLAS and GOTCHA are prerequisites to planning, not stages within it. Before
the `brainstorm`/`plan` stages produce anything, ATLAS Architect/Trace
(`skills/atlas/SKILL.md`) and GOTCHA layering (`skills/gotcha/SKILL.md`) frame
the problem. A plan drafted without them is unbounded — and an unbounded plan
is what forces premium-model spend downstream, against the framework's goal.

## The map

Pipeline (spec G-5): `brainstorm -> plan -> spec-review -> test -> code -> quality -> git -> gate`

| Stage | Bound role | Model tier | Rationale (goal: quality-efficient outcomes per token) |
|---|---|---|---|
| brainstorm | gleipnir-plan | Opus (temp raised) | Divergent framing; the planning role runs it, not the orchestrator |
| plan | gleipnir-plan | **Opus** | Unbounded judgment; ATLAS Architect/Trace decisions compound most. The one place premium pays for itself. Owned by the dedicated planning role, not the orchestrator |
| spec-review | quality-reviewer | Sonnet | Judgment bounded by the spec as rubric |
| test | gleipnir-code | Sonnet (candidate for uplift) | In test-first, tests *define* correctness — the correctness arbiter. Watch for uplift to Opus if test design proves weak |
| code | gleipnir-code | **Sonnet** | Bounded by plan + ATLAS-Assemble order + pre-written tests. The test is the arbiter, not model IQ — do not pay Opus here |
| quality | quality-reviewer | Sonnet | Blast-radius review against the plan; catching defects here prevents expensive reverts |
| git | git-ops | **Haiku** | Mechanical, structured tool calls; the sole broker role |
| gate | orchestrator | Opus (reads attestation) | Reads authoritative evidence (future G-3.2) and emits pipeline state; near-deterministic once the engine exists |

## Model-sizing principle

Spend the strongest model only where judgment is **unbounded** and errors
compound: **plan**. Once ATLAS and pre-written tests bound the work, the
**code** stage drops to Sonnet — the test, not the model's capability, is what
guarantees correctness (Axiom 1). Value shifts toward **test authoring**,
since tests carry the correctness burden in a test-first pipeline. Mechanical
roles (git, and the future gate/PM/notify calls) run on Haiku. Concrete model
IDs are declared per agent in `.gleipnir/agents/*.md`, mapped to the
aperture-served models available in this environment.

## Binding rules (S-1.3.1)

- A stage may be routed **only** to its bound role. No role performs a stage
  it is not bound to.
- **The orchestrator sequences; it does not perform stages.** Planning
  (brainstorm/plan) is delegated to `gleipnir-plan`, not authored by the
  orchestrator. The orchestrator's only bound stage is `gate` (reading
  attestation and emitting pipeline state), which is near-deterministic; every
  other stage is delegated to its bound role.
- The `git` stage binds to `git-ops` and only `git-ops` — the broker
  single-holder clause. No other role holds git or credentials.
- One verb, object, verification and boundary per delegation; exploration and
  action are separate delegations (task-decomposition isolation).
