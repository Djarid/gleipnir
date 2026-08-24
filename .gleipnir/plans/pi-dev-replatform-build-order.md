# Build Order: pi.dev-native re-expression of Gleipnir (Approach B)

> **Status: Architect-level roadmap (Tier-0, transient).** This is the
> build-order companion to the converged brief
> `pi-dev-replatform-brainstorm.md` (Selected Approach B: native TypeScript
> re-expression, pi.dev-ONLY, full substrate rewrite — retire the Python
> enforcement core at the pi edge). It breaks the full rewrite into an ordered
> sequence of buildable slices, analogous to the original
> `decisions/substrate-design-pass.md` "What this pass unblocks" steps 1–5, but
> re-targeted at pi.dev's *actual* primitives (verified below).
>
> **This roadmap decides NOTHING material.** The 4 carried-forward open
> questions from the brief's "Handoff to plan" are NOT resolved here; where the
> sequencing needs a provisional answer to order steps, it is flagged
> explicitly as an **[ASSUMPTION-N]** requiring operator convergence before the
> dependent step is built. The 7 decision-record supersessions are listed for
> the operator/plan-stage to enact; this Tier-0 artifact does not write
> `decisions/`.

## pi.dev primitives re-verified (this session, primary source)

Re-confirmed hands-on against the earendil-works/pi source + `pi.dev/docs`
(not merely trusting the brief's Explore summary), because these API shapes are
what step S1's slice will be coded against and a wrong shape wastes the
`gleipnir-code` delegation:

| Primitive | Verified signature / fact | Source |
|---|---|---|
| Extension entrypoint | `export default function (pi: ExtensionAPI) { … }`; package `@earendil-works/pi-coding-agent` | `examples/sdk/06-extensions.ts`, `docs/extensions.md` |
| Pre-tool block hook (CRUX 1) | `pi.on("tool_call", async (event, ctx) => { … return { block: true, reason } \| undefined })`; `event.toolName`, `event.input` (mutable) | `examples/extensions/permission-gate.ts` |
| Non-interactive discriminator (Open-Q2) | `ctx.hasUI` boolean; the canonical fail-closed pattern `if (!ctx.hasUI) return { block: true, reason }` is shown verbatim in the shipped example | `examples/extensions/permission-gate.ts` |
| Human-question (blocking) | `ctx.ui.select(msg, choices)` / `.confirm` / `.input` / `.notify`; TUI-bound | `permission-gate.ts`, `docs/extensions.md` |
| Custom tool register (CRUX 2) | `pi.registerTool({ name, label, description, parameters: Type.Object({…}) /* typebox */, execute(toolCallId, params, signal, onUpdate, ctx) })`; also standalone `defineTool()` + `customTools:[…]` | `docs/sdk.md`, `dynamic-tools.ts` |
| Child session (CRUX 2) | `createAgentSession({ resourceLoader, sessionManager: SessionManager.inMemory(), model, tools, customTools, modelRuntime })` → `{ session }`; `session.prompt()`, `.subscribe()`, `.dispose()` | `docs/sdk.md`, `06-extensions.ts` |
| Process-isolated delegation alt | `runRpcMode(runtime)` / CLI `pi --mode rpc --no-session` (JSONL) | `docs/sdk.md` |
| Session-persisted state (depth cap) | `pi.appendEntry()` (survives restart); in-extension module state for in-process depth | `docs/extensions.md` |
| Coarse tool gating | `tools` / `noTools:"all"\|"builtin"` / `excludeTools`; runtime `pi.setActiveTools` | `docs/sdk.md` |
| Compaction hook | `session_before_compact` / `session_compact` (stable, first-class) | brief Explore (table row 6) |
| Session lifecycle | `session_start` (startup/new/resume/fork), `session_shutdown`, `agent_start/agent_end`, `tool_execution_start/end` | `docs/sdk.md`, `06-extensions.ts` |
| Package manifest | `package.json` `"pi": { "extensions":[…], "skills":[…], "prompts":[…], "themes":[…] }` + `"keywords":["pi-package"]`; or convention dirs `extensions/ skills/ prompts/ themes/` | `docs/packages` |
| Peer deps (NOT bundled) | `peerDependencies` with `"*"` range: `@earendil-works/pi-ai`, `@earendil-works/pi-agent-core`, `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, `typebox` | `docs/packages` |
| Install / trust | `pi install {npm:\|git:\|path}`; project packages auto-install **after project trust**; project settings `.pi/settings.json`, global `~/.pi/agent/settings.json` | `docs/packages` |

**Two brief claims that this roadmap treats as still-unverified (they gate
later steps, not step S1):** (a) MCP-client reachability for the git/pm brokers
from a pi extension — the SDK exports surveyed show no `mcp:` client config;
this is Open-Q3 and blocks the broker step. (b) Whether `createAgentSession`
child sessions inherit the parent extension's `tool_call` hook or need explicit
`bindExtensions(...)` re-binding — the SDK notes `runtime.session.bindExtensions(...)`
is required after session *replacement*; whether a freshly *created* child
session auto-binds the enforcement hook is load-bearing for delegation
enforcement and must be proven in step S3 (flagged inside that step).

## Decision records / artifacts this build order will supersede (in order)

Named for the operator / plan-stage to enact — **NOT written here** (Tier-3,
outside this Tier-0 writer grant). Ordered by *when in the build they must
change* so the tree is never left in a half-superseded state:

| Order | Record / artifact | Enact at step | Nature |
|---|---|---|---|
| 1 | `decisions/runtime-and-deps.md` (stdlib-only-Python-core) | **S1** (first TS lands) | Amend/supersede (scoped): TS + pinned pi peer-deps at the pi edge |
| 2 | `decisions/substrate-design-pass.md` D-1 ("port = conformance, not rewrite") | **S1** (target reversal is realised the moment pi-native code exists) | Supersede |
| 3 | `stage-role-map.md` Axis-1 `X` / Axis-2(a) `E` (opencode literals) | **S2** (role table + package manifest become the enforcement surface) | Amend |
| 4 | `AGENTS.md` (`OPENCODE_CONFIG_DIR` framing, `.opencode` rationale, guard-status opencode-hook refs) | **S2** (`.pi/` surface becomes canonical) | Amend |
| 5 | `preflight/config_scan.py` + its tests (parses `opencode.jsonc`) | **S7** (preflight re-expression) | Rewrite (TS or scoped) |
| 6 | `bin/gleipnir-{launch,preflight}`, `.gleipnir/policy/context-cap.jsonc`, `.github/workflows/config-scan.yml`, `hooks/pre-commit`, `opencode.jsonc` | **S8** (cutover) | Rewrite/retire |
| 7 | `gleipnir_specification_v0_3_12.md` D-1 register (~L302), Part-D narrative (~L310/334), the L66 "conformance shim" line, E-2 "ephemeral opencode target" (~L323) | **S8** (spec revision candidate v0.3.13, after parity is proven) | Supersede (next spec rev) |

> The brief's own supersession table (rows 1–7) is the authority for *what*
> changes; this table adds *when* (dependency-ordered against the steps below).
> Note the brief numbered the spec as its own row and runtime-and-deps as row 2;
> the reordering here is by build-time, not by importance.

## The build order (steps S1–S9)

Each step names: goal, dependency, the open-question(s) it depends on (if any),
and the exit criterion that unblocks the next step. The spine mirrors the
original build order: **prove the substrate/primitives (S1) → capability
enforcement table (S2) → delegation (S3) → engine (S4) → attestation (S5) →
broker/credential isolation (S6) → preflight/config (S7) → bus/observer (S8-adj)
→ cutover (S9)** — re-pointed at pi's primitives.

### S1 — Primitive-proof slice (**Part 2 of this delegation; the first buildable slice**)

- **Goal:** scaffold a minimal Pi package skeleton (`package.json` `pi` key +
  peer-deps + one `extensions/` module) and prove the two load-bearing CRUX
  mechanisms hands-on for **ONE** simple role: (CRUX 1) a `tool_call` block hook
  reading a role→capability table denies a not-allowed tool and permits an
  allowed one; (CRUX 2) a `delegate` custom tool spins a `createAgentSession`
  child bounded to a role's tool set, with a depth cap held in extension state.
- **Dependency:** none (this is the foundation slice).
- **Open-question dependency:** none *required to build the proof*. It **touches**
  Open-Q2 (it will demonstrate the `ctx.hasUI` fail-closed branch as the
  mechanism) but does not *decide* the Q2 policy. **[ASSUMPTION-1]** S1 assumes
  the delegation proof uses in-process `createAgentSession` (not `runRpcMode`);
  this is a proof-vehicle choice, not the final delegation-isolation decision
  (that is revisited at S3/S6). Flagged.
- **Exit criterion:** an automated test shows (i) a denied tool call is blocked
  with a reason, (ii) an allowed one passes, (iii) a `delegate` call creates a
  bounded child and (iv) a delegation past the depth cap is refused — AND the
  binding question (does the child session enforce the parent's hook?) is
  answered with evidence. Full ATLAS plan: `pi-dev-replatform-first-slice.md`.

### S2 — Full role→capability table + package manifest (the deny-by-default roster)

- **Goal:** promote S1's one-role proof to the full 8-role roster
  (`orchestrator`, `gleipnir-brainstorm`, `gleipnir-plan`, `gleipnir-code`,
  `quality-reviewer`, `git-ops`, `project-mgr`, `notify`) as a Gleipnir-owned
  role→capability table consumed by the enforcement extension; finalise the Pi
  package manifest and `.pi/settings.json` project surface. Re-express the
  per-path/per-arg bounds the opencode `permission:` map used to carry, now in
  the extension's block logic (host has no permission-map primitive — CRUX 1).
- **Dependency:** S1 (mechanism proven).
- **Open-question dependency:** none directly; but enacts supersessions 3 & 4
  (stage-role-map `X`/`E` and `AGENTS.md` framing) because the `.pi/*` surface
  and the role table become the enforcement paths those records enumerate.
- **Exit criterion:** every role's allow-set is expressed and tested; the single
  broker holder (`git-ops`) is the only role whose table grants git (G-2 clause
  preserved at the table level); deny-by-default proven for each role.

### S3 — Delegation model + depth cap (re-express `task`/`subagent_depth`)

- **Goal:** promote S1's `delegate` proof to the real orchestrator→subagent
  model: a `delegate` tool that creates a role-bounded child session, enforces
  the depth cap, and guarantees the child inherits enforcement (the S1 binding
  answer decides whether that is automatic or needs explicit `bindExtensions`).
- **Dependency:** S1 (delegation proof), S2 (roles to delegate to).
- **Open-question dependency:** **Open-Q attached** — the in-process
  (`createAgentSession`) vs process-isolated (`runRpcMode`) delegation boundary
  interacts with the S-2 sandbox choice (Open-Q1) and the broker boundary
  (Open-Q3). **[ASSUMPTION-2]** S3 provisionally builds on in-process
  `createAgentSession` (per S1's [ASSUMPTION-1]); if the sandbox/broker
  convergence later requires process isolation for certain roles, S3's
  delegation edge must gain an RPC variant. Flagged — needs operator
  convergence on Open-Q1 before S3 is *finalised* (it can start on the
  in-process assumption).
- **Exit criterion:** orchestrator can delegate to a bounded role, depth cap
  refuses runaway nesting, child cannot exceed its role's capability table.

### S4 — G-5 deterministic engine, re-expressed in TypeScript

- **Goal:** re-implement the G-5 state machine + judges + allow-table logic
  natively in TS (oracle = existing `src/gleipnir/engine/{driver,judges,allow_table,bridge}.py`
  + `engine/DESIGN.md` + their tests), running in-process in the extension. This
  is the "unbounded judgment compounds here" core; the existing Python tests are
  the correctness oracle the TS suite must re-earn.
- **Dependency:** S2 (role table the engine sequences over), S3 (delegation the
  engine drives). Independent of the broker (per original build-order note).
- **Open-question dependency:** none new. Enacts supersession 1
  (runtime-and-deps) fully for the engine.
- **Exit criterion:** TS engine passes a port of the Python engine test suite;
  deterministic sequencing (not LLM-narrated) demonstrated; the prose/config
  blast-radius router (stage-role-map Axis-1/2) is re-expressed as engine config.

### S5 — G-3.1 attestation (HMAC marker) in TypeScript

- **Goal:** re-express the keyed-evidence marker (oracle = `src/gleipnir/verify/marker.py`
  + `tests/fixtures/golden_marker*.json`, `golden_key.bin`) as in-process TS so
  the engine's completion edges carry unforgeable evidence. Cross-language
  golden-vector test: the TS HMAC must reproduce the existing Python golden
  markers byte-for-byte (or the key/marker format is deliberately re-specified —
  a material choice to surface if it arises).
- **Dependency:** S4 (engine emits the attested transitions).
- **Open-question dependency:** none. **[ASSUMPTION-3]** the HMAC key format and
  marker schema are preserved (TS reproduces the Python golden vectors) rather
  than re-specified; if re-specification is needed this is a material decision to
  route back to the operator. Flagged.
- **Exit criterion:** TS marker verifies against the existing golden fixtures;
  self-declared-done is impossible without a valid marker.

### S6 — Broker / credential isolation (G-2) reachability from a pi extension

- **Goal:** reach the git/pm brokers (`src/gleipnir/broker/{git,pm}/mcp_server.py`)
  from the pi extension without granting any role the credential — preserving the
  single-holder (`git-ops`) clause and E-1 argument policy.
- **Dependency:** S2 (`git-ops` role), S3 (delegation boundary).
- **Open-question dependency:** **Open-Q3 (MCP-broker reachability) — BLOCKING.**
  The surveyed pi SDK exports show no opencode-style `mcp:` client config; until
  the operator/convergence confirms the reach mechanism (documented MCP client
  vs RPC vs a custom-tool socket wrapper), S6 cannot be finalised.
  **[ASSUMPTION-4]** for *sequencing only*, this roadmap places S6 after the
  engine so the broker is not on the critical path to a working enforcement
  package; if brokers turn out to need a custom-tool socket wrapper, that wrapper
  is itself a pi custom tool (S3-shaped) and may pull earlier. Flagged; do not
  build S6 until Open-Q3 is converged.

### S7 — Config preflight + `.pi/*` scanner (re-express `config_scan.py`)

- **Goal:** re-express `src/gleipnir/preflight/config_scan.py` (+ tests) to scan
  the `.pi/settings.json` + package-manifest surface instead of parsing
  `opencode.jsonc`'s `agent:`/`tools:`/`mcp:` shape; re-point the S-3 preflight
  boundary check (`preflight/boundary.py` is OS-level, reusable) at pi's config
  load path. Account for pi's "resources load only after project trust" fact
  (relevant to G-1: an untrusted-project load path must not bypass the scan).
- **Dependency:** S2 (the `.pi/*` surface + manifest exist to scan).
- **Open-question dependency:** none new; enacts supersession 5.
- **Exit criterion:** preflight fails-closed on a malformed/over-broad `.pi/*`
  role grant, matching the parity of the current opencode config-scan tests.

### S8 — G-4 bus / ledger / observer, re-expressed in TS (off-hot-path)

- **Goal:** re-express `src/gleipnir/{bus,ledger}/**` in TS for a single-language
  package (per Approach B), or stage as the last capability since it is
  off-hot-path (the brief allows separate staging). Includes the E-2 webhook
  receiver home (still absent as a pi primitive — unchanged; external process).
- **Dependency:** S4 (engine emits the events the bus carries), S5 (attested
  events).
- **Open-question dependency:** none. (E-2 remains an external compensating
  process, as in the original substrate pass.)
- **Exit criterion:** ledger reduces/reconciles the event stream; observer
  parity with the existing `tests/test_ledger_*` and `test_bus_*` suites.

### S9 — Cutover / retirement of the opencode-hosted artifacts

- **Goal:** retire `opencode.jsonc`, `.gleipnir/plugins/*.ts` (opencode-shaped),
  `.gleipnir/agents/*.md` frontmatter, `bin/gleipnir-{launch,preflight}`
  opencode wiring, `.github/workflows/config-scan.yml`, `hooks/pre-commit`
  opencode assumptions — and enact spec supersession 7 (v0.3.13). Sequence so the
  tree is **never in a half-enforced state** (either opencode-enforced or
  pi-enforced, never neither).
- **Dependency:** S1–S8 all at parity + passing S-3 preflight + the AC
  acceptance tests.
- **Open-question dependency:** **Open-Q4 (migration/retirement sequencing) —
  BLOCKING for S9.** Big-bang at pi-package parity vs keep opencode inert until
  pi passes preflight+AC is exactly this step's governing choice; it must be
  converged with the operator before S9 executes. **[ASSUMPTION-5]** the roadmap
  provisionally assumes "keep opencode artifacts inert (not deleted) until the
  pi package passes S-3 preflight + AC acceptance, then retire in one commit" —
  the safer of the two, avoiding a half-enforced window — but flags it as the
  operator's Open-Q4 call.

## Dependency graph (summary)

```
S1 (primitive proof) ──┬─> S2 (role table) ──┬─> S4 (engine) ──> S5 (attestation) ──┬─> S8 (bus/ledger)
                       │                     │                                       │
                       └─> S3 (delegation) ──┘                                       │
                                              └─> S6 (broker) [BLOCKED on Open-Q3] ──┘
                                    S2 ──> S7 (preflight/config)
   all ──> S9 (cutover) [BLOCKED on Open-Q4]
```

## Open questions carried forward (operator convergence required)

Restated from the brief's "Handoff to plan"; NONE decided here. Mapped to the
step each blocks and the flagged provisional assumption used only to *sequence*:

| Open-Q | Blocks step | Provisional assumption used for sequencing (NOT a decision) |
|---|---|---|
| Q1 Sandbox (keep `bin/gleipnir-sandbox` vs Gondolin/Docker/OpenShell) | S3 finalisation, S6 | [ASSUMPTION-1/2] in-process `createAgentSession` for the S1 proof and S3 start; revisit if isolation demands RPC |
| Q2 Blocking human-gate under `-p`/`--mode rpc`/`--mode json` | S1 demonstrates the mechanism; POLICY decision blocks any gate-bearing stage running unattended | S1 uses the shipped `ctx.hasUI` fail-closed pattern as the *mechanism*; the *policy* (fail-closed vs external question sink vs interactive-only gate) is Q2, undecided |
| Q3 MCP-broker reachability from a pi extension | **S6 (BLOCKING)** | [ASSUMPTION-4] S6 sequenced after the engine so brokers are off the critical path; reach mechanism undecided |
| Q4 Migration/retirement sequencing of opencode artifacts | **S9 (BLOCKING)** | [ASSUMPTION-5] keep opencode inert until pi passes preflight+AC, then one-commit retire — flagged as Q4's call |

## Design Principles (Gate 1 — roadmap artifact)

**Routing:** this roadmap artifact is **prose-only** (`P = { this .md file }`,
`P ∩ X = ∅` — no executable artifact). Per `plan-format.md` case (iii),
SOLID/DRY/SRP are **`N/A — no executable artifact`**.

**Design Intent (specific, falsifiable):** *This roadmap must sequence every
build step so that (a) no step depends on an unresolved open question without
that dependency being named and gated by an explicit `[ASSUMPTION-N]`/BLOCKING
marker, and (b) the tree is never left in a half-enforced state at any step
boundary.* A reviewer can falsify this by finding any step whose prerequisites
include an undecided open question that is NOT flagged, or any ordering where
enforcement is neither opencode-side nor pi-side (the S9 half-enforced-window
failure the [ASSUMPTION-5] guard exists to prevent).
