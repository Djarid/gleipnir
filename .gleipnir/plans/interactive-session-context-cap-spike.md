# Spike result — context-cap model-id scoping (plan Step 1 / L0 / S0)

**Stage:** spike gate for `interactive-session-context-cap.md`. Tier-0 note.
**Verdict: PASS — CONFIRMED at runtime.** Construction-level PASS (distinct
capped id, orchestrator-only) plus the residual runtime check is now CLEARED:
after the `limit` two-key schema fix (`context 250000` / `output 32000`),
opencode restarted and the orchestrator reported a 250000 window. The alias
resolves; no Approach-B escalation needed.

## Question the spike had to answer

Can a `limit.context = 250000` cap be scoped to the **orchestrator only**, without
leaking to `gleipnir-plan` / `gleipnir-brainstorm` (which share the same base
model), given this environment has **no `provider` block in the project
`opencode.jsonc`** and uses bare aperture model ids?

## Evidence gathered (read-only)

1. **Where the provider actually lives.** The `aperture-anthropic` provider is
   defined in the **global** config `~/.config/opencode/opencode.jsonc`
   (lines 39–52), not the project `opencode.jsonc`. Model ids are arbitrary
   **keys** under `provider.<id>.models` (e.g. `anthropic.claude-opus-4-8`).
   opencode merges project config over global (config docs, precedence order),
   so the project `opencode.jsonc` can *add* a model key under the same provider.

2. **All three opus agents share one id.** `orchestrator.md`,
   `gleipnir-plan.md`, `gleipnir-brainstorm.md` all set
   `model: aperture-anthropic/anthropic.claude-opus-4-8`. Therefore putting
   `limit.context` directly on that shared key **WOULD leak** the cap to plan +
   brainstorm — the S0 failure mode. Confirmed by reading the three agent files.

3. **The non-leaking mechanism (AETOS-proven).** opencode keys `limit.context`
   on the **model id**, and each agent's `model:` selects the id. AETOS
   (`../aetos/opencode.json` lines 11–18, 33) declares distinct
   `provider.models.<id>` entries each carrying their own `limit`, and points
   individual agents at specific ids. So the cap scopes to exactly the agents
   whose `model:` names the capped id. Pointing **only** the orchestrator at a
   distinct capped id caps only the orchestrator. **This is the S0 PASS
   construction.**

4. **Custom model-id keys are legal.** Per the models doc: for a custom
   provider, `model_id` is "the key from `provider.models`" — operator-defined.
   A new key under `aperture-anthropic.models` is a valid, selectable id.

## The applied construction (what Steps 2–4 wire)

Add a **distinct capped model id** under the existing `aperture-anthropic`
provider in the **project** `opencode.jsonc`, carrying `limit.context: 250000`,
and repoint **only** `orchestrator.md` `model:` to it. Every other opus agent
keeps the uncapped `anthropic.claude-opus-4-8`.

## Residual runtime check (the one thing a read cannot prove)

Whether the aperture endpoint accepts the **new key's `name`** as the upstream
model (i.e. the alias resolves to a real served model). Two safe options, in
order of preference:

- **(preferred) Reuse-name alias:** give the new key a `name` /`id` mapping that
  points at the same upstream model the base id uses, so only `limit.context`
  differs. If opencode sends `options.name` (or the models.dev id) as the model
  and the *key* is just a local handle, an arbitrary key is safe.
- **(fallback) If the endpoint echoes the key as the model name** and rejects an
  unknown one, the cap cannot be a pure alias; then S0 escalates to the reserved
  **Approach-B scoped plugin** (a `chat.params`/context hook that trims only when
  the active agent is the orchestrator). This is the operator-facing conditional
  decision the plan reserves — surface it, do not silently adopt.

**This residual check requires an opencode restart to observe** (config is read
at startup); it cannot be exercised from inside a running session. It is the
"throwaway config probe" the plan's L0 names. Marked as an explicit operator
verification step, not a blocker to authoring the artifacts.

## Gate decision

S0 **PASS by construction** for the config mechanism (distinct capped id,
orchestrator-only). Steps 2–5 proceed. The single runtime uncertainty (alias
resolution at the aperture endpoint) is isolated, documented, and carries a
named escalation path if it fails on restart.
