# Decision: session-scribe — a Tier-0-scoped framework-bookkeeping writer

**Status:** decided and implemented. Durable decision record (Tier-3, operator-
authored). Converged via the orchestrator-surfaced decision gate. Plan of
record: `../plans/session-scribe.md` (spec-review passed).

## Problem

The orchestrator holds no write/edit/bash by design (reference-floor;
sequences and judges, never produces — lesson L-C9). But a recurring class of
**framework-bookkeeping** writes (the session-state/resume note, the open-seams
ledger, scratch) had **no reachable scoped writer**: no roster agent cleanly
owns them, and the orchestrator can't do them — so they were forced through the
unbounded `/general` worker with per-use permission (lesson L-C10). And a fresh
session had nothing durable pointing it at the session-state artifact, so it
could not self-orient.

## Converged decisions (operator-decided; LOCKED)

- **D1 — a dedicated `session-scribe` roster sub-agent (Option A).** Deny-by-
  default; `edit` and `write` allow **only** `.gleipnir/plans/**` and
  `.gleipnir/var/tmp/**` (Tier 0); `read: allow` (broad — read is not the G-6
  threat, only write is); no `bash`, `task`, git, or `webfetch`; Haiku model
  (mechanical role). **Tier-3-NEVER guarantee:** no Tier-3 path (`agents/`,
  `skills/`, `goals/`, `decisions/`, `stage-role-map.md`, `keys/`, `plugins/`,
  `sandbox/`, `AGENTS.md`) and no Tier-2 path (`memory/`, `lessons/`) ever
  appears as an `edit`/`write` allow — enforced by capability (`"*": deny`),
  not prose. This prevents the scribe becoming a back door around the
  POLICY/arbiter integrity the framework protects.

- **D2 — scope = Tier-0 only.** The scribe writes `plans/**` + `var/tmp/**`
  only (session-state, seams, scratch). It does **not** write Tier-2 `lessons/`
  or `memory/` — candidate-lessons stay operator-authored pre-pipeline (per the
  `lessons/README` write-rule and L-C9) until the G-4c review-gated pipeline
  exists. It **never** writes any Tier-3 path.

- **D3 — resume mechanism.** A one-time, generic, durable resume goal in
  `goals/manifest.md` (+ `goals/resume.md`) points every session at the
  volatile `plans/SESSION-STATE.md`. The goal names only the *path*, no
  session-specific content, so it is authored once and never churned; all
  per-session state lives in the Tier-0 artifact, churned by the scribe. No
  per-session Tier-3 write. `SESSION-STATE.md` supersedes and absorbs the old
  `session-seams-ledger.md` (single resume entry point).

- **D4 — bookkeeping is an ad-hoc bounded delegation, not a G-5 stage.** The
  orchestrator gains `task: session-scribe: allow` (delegation only — it gains
  **no** write itself) and issues one-verb/object/verification/boundary
  delegations ("record session state: write the resume note to
  `plans/SESSION-STATE.md`; verify it landed"). This is orthogonal to the G-5
  pipeline and is **not** added to `stage-role-map.md`. It resolves L-C10:
  the orchestrator now has a reachable, bounded writer to delegate bookkeeping
  to, instead of bouncing work to the human or the unbounded `/general`.

## A → C graduation path (named end-state)

Option C — plugin-hosted **typed** bookkeeping tools (e.g.
`record_session_state`, `append_seam`) that write canonical artifacts to fixed
paths *by construction* — is the more auditable, GOTCHA-aligned end-state, but
is a net-new Tier-3 plugin build (there is no MCP substrate; the deterministic
boundary here is the opencode plugin layer). It is **not built now.** A→C is a
clean migration: the scribe's delegations become tool calls; the **Tier-0-only
write grant is unchanged.**

## Conformance

A candidate conformance assertion: **no roster agent's permission map grants a
Tier-3 or Tier-2 `edit`/`write`; the `session-scribe` allow-set ∩ Tier-3
path-set = ∅.** This makes the Tier-3-never guarantee testable structurally
(the same deny-by-default enforcement that `gleipnir-plan` already relies on).

## Verification

Implemented as: `.gleipnir/agents/session-scribe.md` (the map above);
`.gleipnir/agents/orchestrator.md` (+`session-scribe: allow` under `task`, no
write gained); `.gleipnir/goals/manifest.md` + `goals/resume.md` (the resume
goal); `.gleipnir/plans/SESSION-STATE.md` (the first resume artifact, absorbing
the seams ledger). The scribe `.md` and orchestrator allowlist take effect on
runtime reload.

## Known not-yet-closed / seams

- Option C (plugin typed bookkeeping tools) — the graduation target, not built.
- Tier-2 lessons-writing — deferred to the G-4c review-gated pipeline; the
  scribe deliberately does not write `lessons/`.
- The scribe `.md` + orchestrator task-allowlist edit require a runtime reload
  before the orchestrator can actually delegate to the scribe.
