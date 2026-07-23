# Plans — transient session working artifacts

This directory holds **transient** planning artifacts: per-session ATLAS
briefs, validation reports, and scaffold working notes. They are working files,
not permanent reference material.

## Lifecycle policy (prevents documentation debt)

- **Transient by default.** Files here (e.g. `session-NN-*.md`,
  `step-N-*.md`) are disposable once their work has merged and any durable
  outcome has been promoted.
- **Promote durable outcomes.** If a plan produces a decision later work
  depends on (a resolved D-item, a substrate choice, an architecture ruling),
  that outcome is written as a record in `../decisions/` — which IS durable
  reference material and is kept.
- **Clean up after merge.** Per the inherited GOTCHA guardrail ("clean up plan
  files after the associated feature is merged"), session artifacts here should
  be removed or archived once their feature lands and their durable outcome is
  promoted. Do not let them accumulate as permanent repo docs.

## The distinction

| Directory | Contents | Kept? |
|---|---|---|
| `../decisions/` | resolutions later work depends on | **durable** |
| `../plans/` (here) | per-session briefs, validation, working notes | **transient** |
| `../goals/` | process-as-data goals (K-1) | durable, but goals not plans |

## Current contents (session history, pending cleanup)

- `session-01-atlas-brief.md`, `session-01-validation.md` — retroactive
  methodology pass over the initial build session.
- `session-02-cleanup-brief.md` — this goals/plans reorganisation.
- `step-0-scaffold.md` — the step-0 build record.

These remain for now as a readable trail of how the scaffold came to be; under
the policy above they are candidates for archival once the framework stabilises
and their durable outcomes (already in `../decisions/` and the spec) are the
authoritative record.
