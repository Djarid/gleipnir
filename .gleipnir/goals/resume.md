# Goal: Session resume (orient at session start)

**Kind:** workflow. **Trigger:** the start of any session, before taking on work.

At session start, **read the current session-state artifact
[`../plans/SESSION-STATE.md`](../plans/SESSION-STATE.md) to orient** — it holds
the current state, the built slices, the open threads / next actions, and where
to look. It is a **Tier-0 volatile** artifact (the `session-scribe` churns it
each session); it is **not authoritative** — the authoritative homes are
`../decisions/` (durable decision records) and the spec. If
`../plans/SESSION-STATE.md` is absent, there is no prior session state to
resume; start from `../decisions/` and the spec.

This goal is **generic and static**: it names only the *path* to the resume
artifact, never session-specific content. All per-session state lives in the
Tier-0 artifact and is churned there — this Tier-3 goal is authored once and
never changes per session.

**How the resume artifact is maintained.** The orchestrator delegates
"record session state" to the `session-scribe` (a Tier-0-scoped bookkeeping
writer) as an ad-hoc bounded delegation — not a G-5 pipeline stage. See
`../decisions/session-scribe.md`.
