# Decision: Orchestrator context-length cap (250K, orchestrator-only)

**Status: authored, enforced-at-hook, NOT YET CLOSED** — until S-2 boundary +
G-1 preflight make `.gleipnir/policy/**` and `.gleipnir/plugins/**` OS-ro to the
agent uid (`s2-g1-closure.md`), this cap is **cooperative policy**, not an
OS-enforced guard. Durable decision record. Authored by the operator via the
build-mode escape hatch (Tier-3). Plan of record:
`../plans/interactive-session-context-cap.md`; converged brief:
`../plans/interactive-session-context-cap-brainstorm.md`; spike:
`../plans/interactive-session-context-cap-spike.md`.

## UPDATE — cap UNSET, orchestrator moved to plain Sonnet 5 (later, same session)

The operator subsequently switched the orchestrator model to
`aperture-anthropic/anthropic.claude-sonnet-5` and **dropped the cap**,
deliberately exercising the "unset = no cap = model default" path this feature
was built to support:

- `orchestrator.md` `model:` → plain `anthropic.claude-sonnet-5` (no capped alias).
- `opencode.jsonc` — the capped-alias `provider` block **removed**; its absence
  IS the unset state (never `limit.context: 0`).
- `.gleipnir/policy/context-cap.jsonc` — `cap_tokens` set to `null`.
- The `compaction-survival.ts` plugin + the orchestrator's `compaction_survival:`
  pinned rules **remain** — they preserve critical context across ANY compaction
  (which now fires at Sonnet 5's default window), independent of any cap.

The capped-alias mechanism below is retained as the documented record of HOW to
re-apply a cap; it is simply not active now.

## Why

1M-token context windows are unnecessary and wasteful of tokens; the framework
goal is quality-efficient outcomes per token (G-4d scoreboard). An arbitrary,
operator-set cap on the orchestrator's interactive window bounds spend at the
one always-on primary agent without touching the bounded subagents (whose work
is already scoped by their delegations).

## What was decided (operator-converged)

- **VALUE:** default cap **250 000 tokens**. Arbitrary and operator-editable.
- **SCOPE:** the framework `orchestrator` agent **ONLY**. Not `/plan`, not
  `/build`, not any other agent/subagent. All others unlimited locally (remote
  provider limits still apply naturally).
- **WHERE (single source of truth):** `.gleipnir/policy/context-cap.jsonc`
  (`cap_tokens`), Tier-3, operator-only. Carries the explicit **"unset = no cap
  = model default"** documentation.
- **ENFORCEMENT:** a **distinct capped model id**
  (`aperture-anthropic/anthropic.claude-opus-4-8-capped`) declared in
  `opencode.jsonc` with `limit: { context: 250000, output: 32000 }` (the schema
  requires BOTH keys; `output` is not a functional cap we care about here — it
  matches the base Opus resolution at the Bedrock/Mantle endpoint so the alias
  differs from the base id only by `limit.context`); **only** `orchestrator.md`
  points `model:` at it. Because opencode keys `limit.context` on the model id
  (not the agent), and other opus agents keep the uncapped id, the cap does not
  leak to `gleipnir-plan` / `gleipnir-brainstorm`. This is the AETOS-proven
  pattern (`../aetos/opencode.json` per-model `limit`).
- **AT-CAP BEHAVIOUR:** native compaction + `.gleipnir/plugins/compaction-survival.ts`
  (ported from `../aetos/.aetos/plugins/compaction-survival.ts`, ref v3.19.0,
  paths adapted to `.gleipnir/`). On `experimental.session.compacting` it
  re-injects the orchestrator's pinned `compaction_survival:` frontmatter block
  under "## Critical Guardrails (preserved across compaction)"; a `chat.params`
  hook swallows the custom key so the provider never sees it. **No hard
  truncation, no fail-closed.**

## Unset = no cap = model default (first-class state)

To remove the artificial constraint: set `cap_tokens` to null (or delete it) in
the policy file, delete the `provider` block from `opencode.jsonc`, and repoint
`orchestrator.md` `model:` back to `aperture-anthropic/anthropic.claude-opus-4-8`.
"Unset" means the override line is **absent** — never `limit.context: 0`. The
orchestrator then uses its model's default context limit. This is a legitimate,
documented configuration, not an error.

## Honesty labels / open items

- **Cooperative-policy today.** The policy file, `opencode.jsonc`, agent
  frontmatter and the plugin are Tier-3 by intent but agent-unwritable only
  after S-2/G-1 close. (Note: the enforced `gleipnir-code` grant already denies
  all `.gleipnir/**` writes with no Tier-0 carve-out — observed this session
  when the code agent correctly refused to write `.gleipnir/var/tmp/`. That is
  deny-by-capability working; a separate seam is that `AGENTS.md` narrates
  `var/tmp/` as agent-writable while the grant does not.)
- **Experimental-hook version coupling.** `experimental.session.compacting` and
  `chat.params` "may change without notice." **Validated opencode version: the
  version running this session** (record the exact `opencode --version` at
  activation). An opencode upgrade is a re-validation trigger.
- **RESTART-TIME VERIFICATION — PASSED (operator-confirmed).** After the schema
  fix (`limit` requires both `context` and `output`; set to
  `{ 250000, 32000 }`), opencode was restarted and the orchestrator loaded fine
  reporting a **250000** context window. The capped alias resolves at the
  aperture endpoint. Stress-test S1 (cap applied), S2 (scope: only orchestrator
  on the capped id; plan/brainstorm on the uncapped id) confirmed. The reserved
  Approach-B escalation was NOT needed. S5 (preservation re-injection) and S6
  (key swallowed) verify naturally on the first real compaction.
- **Deferred / out of scope:** G-4d ledger integration, per-subagent budgets,
  session-level ad-hoc override (brief Open Questions).
