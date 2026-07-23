# Gleipnir Goals Library (K-1)

Process-as-data markdown, indexed by `manifest.md`. This is the GOTCHA layer-1
"Goals" surface and the "check goals first" target of the pre-flight checklist.

## What belongs here — and what does not (the G-5 rule)

Under Gleipnir G-5, **sequencing lives in the deterministic engine, not in
goals.** The spec (K-1) is explicit: goals describing sequencing become
*documentation of the coded pipeline*, not instructions an LLM executes; goals
remain authoritative only for **judgment content within steps**.

So, at the current build stage (G-5 engine not yet built):

| Goal kind | Allowed now? | Why |
|---|---|---|
| Judgment-content goals (how to do a step well) | **Yes** | legitimate goals-content |
| Format/artifact goals (e.g. plan-format) | **Yes** | not sequencing |
| Methodology workflow (ATLAS/GOTCHA as process) | **Yes** | prerequisite-to-planning, references skills |
| Pipeline sequencing goals (stage order, loop caps, MR gate) | **No, not yet** | G-5 engine will own these; authoring them now would recreate the prose-orchestration model Axiom 2 forbids |

When the G-5 engine lands (build-order step 3), sequencing goals may be added
here **as documentation of the engine's coded pipeline**, clearly marked as
descriptive-not-executable.

## Current contents

Only the goals that are legitimately goals-content today. See `manifest.md`.
The absence of sequencing goals is deliberate, not an omission.

**Status:** authored, not yet closed. These goals are content; the engine that
would consume sequencing goals does not exist yet.
