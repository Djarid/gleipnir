# Delegation Smoke-Test — Session 02

Transient session artifact (see `README.md` lifecycle policy).

## Question

Can we transition to the delegated agent model now (Tier 1: capability +
context isolation + model-sizing), ahead of the G-5 engine (Tier 2:
deterministic sequencing)?

## Test and result

| Test | Result |
|---|---|
| Roster frontmatter parses (all 6 agents) | PASS |
| Orchestrator `task` allowlist names match agent files | PASS |
| Delegate to `gleipnir-code` (roster agent) | **FAIL — "Unknown agent type"** |
| Delegate to `general` (opencode built-in) | PASS |

## Diagnosis

The roster is correct on disk but **not loaded in the current session**: this
opencode process was not started with `OPENCODE_CONFIG_DIR=.gleipnir`, so
`.gleipnir/agents/` was never read. The delegation *mechanism* works (built-in
delegation succeeded); only the Gleipnir roster is absent.

## The transition gate (concrete)

Tier 1 delegation is available as soon as opencode is launched with the config
dir active:

- `OPENCODE_CONFIG_DIR=.gleipnir opencode` from the repo root, or
- launch `opencode` from a direnv-hooked shell in this repo (`.envrc` exports
  the var; run `direnv allow` once).

No code is required for Tier 1. Verify after launch by delegating to
`@gleipnir-code` and expecting a reply, and by confirming `orchestrator` is the
default agent.

## Tier 2 (later)

Deterministic sequencing is the G-5 engine, build-order step 3. Using Tier 1
now informs that design: watch where the orchestrator's prose judgment does
real work vs. where it just mechanically follows `stage-role-map.md` (the
latter is exactly what moves into engine code).

## Status

Roster wiring: verified correct. Roster live: NO in this session (launch-env
gate). Mechanism: verified working.
