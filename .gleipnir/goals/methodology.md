# Goal: Methodology (ATLAS + GOTCHA run ahead of planning)

**Kind:** workflow goal referencing the K-2 skills. Legitimate goals-content
now. This goal is process documentation, not sequencing the G-5 engine owns.

ATLAS and GOTCHA are **prerequisites to planning, not stages within it.** Run
them before drafting any plan. The skills themselves live at
`../skills/{atlas,gotcha}/SKILL.md` (inherited-and-amended; see
`../skills/README.md`).

## Before any implementation block

1. **GOTCHA Pre-Flight (visible in chat).** Output the checklist before writing
   code: plan file exists? goals manifest checked? tools manifest checked?
   Any conditional gates (platform lifecycle, consistency) applicable? If a
   required item is "no", stop and fix it first.
2. **ATLAS Architect + Trace to disk.** Write the brief (problem/user/success/
   constraints + trace + edge cases) *before* building, using
   `plan-format.md`. This precedes code; it does not document it after.
3. **ATLAS Link.** Validate connections/tools/inputs before assembling.

## During and after

4. **Assemble** in a layered order.
5. **Stress-test** against the brief's acceptance criteria; fix discrepancies.
   Validation is run against the written plan, not asserted.

## The layer-2 caveat (why this is a goal, not engine sequencing)

Under G-5, orchestration (sequencing, loop caps, gates) is the deterministic
engine's job, not the LLM's (GOTCHA Amendment 1). This goal covers the
*methodology judgment* — how to frame and validate work — which remains an LLM
concern. It must not be read as licence for the LLM to narrate pipeline order;
that is the engine's, once built.

## Current-stage honesty

The G-5 engine does not exist yet (build-order step 3). Until it does, the
orchestrator agent follows methodology and sequencing as prose. This goal makes
the methodology-judgment part explicit and disciplined; it does not pretend the
deterministic backstop is present.
