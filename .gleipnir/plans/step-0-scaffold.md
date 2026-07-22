# Plan: Gleipnir Step 0 — Basic Agent Structure + Methodology + Model Sizing

## App Brief (ATLAS Architect)

- **Problem:** Gleipnir has a spec (v0.3.7) but no scaffold. Before the heavy
  substrate design pass, we need the basics: the agent roster, the methodology
  skills those agents run on, and a right-sized model per pipeline stage.
- **User:** the builder implementing Gleipnir; and the future G-5 engine that
  will read the stage-to-role map as configuration.
- **Success (measurable):** a `.gleipnir/` scaffold containing 6 agents, 2
  amended methodology skills, the stage-to-role map, and honest guard-status
  docs — with model choices right-sized to the goal (efficient outcomes per
  token) and nothing masquerading as an enforcing guard.
- **Constraints:** basics only at step 0; no substrate, broker, bus or engine
  code; models limited to those served by aperture in this environment; guards
  are "authored, not yet closed."

## Status: COMPLETE

This plan was executed in the same session. Deliverables below all exist on
disk under `.gleipnir/`.

## What was built

### 1. Methodology skills (K-2) — the foundation
- `skills/gotcha/SKILL.md` — verbatim AETOS GOTCHA v1.0 + **two amendments**:
  - **A1**: Orchestration (layer 2) rewritten to the G-5 deterministic-engine
    model; the LLM never decides sequence. Original retained in a `<details>`
    block for provenance.
  - **A2**: prose "modify only with permission" rewritten to S-2 structural
    immutability for enforcement-bearing config.
  - Guardrails list linked to G-4c measured graduation + K-3 catalogue.
- `skills/atlas/SKILL.md` — near-verbatim AETOS ATLAS v1.0 + the **layer-2
  caveat** (Stress-test judgment is an LLM step; phase sequencing + gate caps
  are engine-controlled) and preserved **plan-persistence discipline**.
- `skills/README.md` — the K-2 inheritance note naming both deltas, so no
  future reader reintroduces the v1.0 LLM-decides-sequence model.

**Corrected a real spec gap:** K-2 named ATLAS/GOTCHA but never defined them
or flagged the layer-2 collision. They are prerequisites to planning; the
scaffold makes them concrete and G-5-safe.

### 2. Roster (S-1.3.1 reference floor), deny-by-default
`agents/`: `orchestrator` (primary, G-5 stand-in), `gleipnir-code` (corrected
exemplar: `bash: deny` + build/test/lint allowlist), `quality-reviewer`
(read-only), `git-ops` (sole git/broker holder), `project-mgr`, `notify`.

### 3. Stage-to-role map (net-new S-1.3.1 artifact)
`stage-role-map.md`. Binds each G-5 stage to a roster role; documents that
ATLAS/GOTCHA run ahead of planning.

### 4. Model sizing (right-sized to the goal)
| Stage | Role | Model (aperture) |
|---|---|---|
| plan | orchestrator | `anthropic.claude-opus-4-8` |
| brainstorm / gate | orchestrator | opus |
| spec-review / quality | quality-reviewer | `anthropic.claude-sonnet-5` |
| test / code | gleipnir-code | `anthropic.claude-sonnet-5` |
| git | git-ops | `anthropic.claude-haiku-4-5` |
| project-mgr / notify | (respective) | `anthropic.claude-haiku-4-5` |

Principle: Opus only where judgment is unbounded (plan). Code drops to Sonnet
because ATLAS + pre-written tests bound it — the test is the arbiter, not
model IQ. Value shifts toward test authoring. Mechanical roles run Haiku.

### 5. `AGENTS.md`
Roster summary, model-sizing principle, the guard-status ("authored, not yet
closed") table, and the E-1..E-4 open seams.

### 6. Config-dir structure + `opencode.jsonc`
The scaffold lives in **`.gleipnir/`** (dotted, opencode convention), not
`gleipnir/`, and is a self-contained framework config directory distinct from
any target project's `.opencode/`. A project-root `opencode.jsonc` sets
`default_agent: orchestrator`, `subagent_depth: 1`, and loads the framework
instruction context. opencode is pointed at the dir with
`OPENCODE_CONFIG_DIR=.gleipnir opencode`, which makes it search `.gleipnir/`
for `agents/`, `skills/`, etc. This also seeds the G-1 story: one known guard
path the S-2 boundary can later make agent-unreachable. The `gleipnir-code`
edit-deny glob is `.gleipnir/**`.

## Execution Workflow (for reference / re-run)

1. `mkdir -p .gleipnir/{agents,skills/gotcha,skills/atlas,goals,plans}`.
2. Copy both SKILL.md from `aetos/.aetos/skills/{gotcha,atlas}/` verbatim.
3. Apply GOTCHA A1 + A2 and the Guardrails->G-4c link as inline `[GLEIPNIR ...]`
   edits, retaining originals in `<details>`.
4. Apply ATLAS layer-2 caveat + mark plan-persistence carried-forward.
5. Write `skills/README.md` inheritance note.
6. Author 6 agent markdown files, deny-by-default, models per table.
7. Write `stage-role-map.md` and `AGENTS.md`.

## Deliberately deferred (NOT step 0)

S-2 substrate (container/mount), G-2 broker + IPC + **E-1 argument policy**,
G-3 HMAC key + attestation binding, G-4 bus/ledger/observer, G-5 engine code,
K-1 goals content, C conformance harness, S-3 preflight + terminal closure.

## Next steps (spec build order)

1. **Substrate design pass** (D-1 + D-4 + config load path). The load-bearing
   unknown; resolve once. Turns the "authored, not yet closed" guards into
   real ones and gives terminal closure + S-3 preflight a mechanism.
2. G-3.1 keyed marker (needs only the key location from the substrate).
3. G-5 engine (the stage-role map becomes its config; G-3.2 lands here).
4. T-layer hardening delivers G-2 — and is where **E-1** must be closed with a
   real broker argument policy, not the pattern denies currently in
   `git-ops.md`.
5. G-4 bus/ledger/observer.
6. L/K/C productionisation.

## Recommended spec follow-up

Consider a spec revision recording that K-2's ATLAS/GOTCHA inheritance carries
two named layer-2 deltas (A1/A2) and one ATLAS caveat, mirroring how E-1..E-4
were made explicit — so the methodology collision is tracked in the spec, not
only in this scaffold.
