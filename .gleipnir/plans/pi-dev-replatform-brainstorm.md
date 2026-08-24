# Design Brief: Re-expressing Gleipnir's capability as a pi.dev plugin

> **Status: CONVERGED.** The operator converged (via the orchestrator) on the
> two material decisions this brief surfaced: **(1) scope = pi.dev-ONLY, full
> substrate rewrite** (see the framing note below — this is a *correction back
> to the originally-intended target*, not a re-scope), and **(2) core
> architecture = Approach B, native TypeScript re-expression** (retire the
> Python enforcement core at the pi edge). The "Selected Approach" section
> records that converged choice. Four downstream questions remain open and are
> carried forward to `gleipnir-plan` as ATLAS Architect/Trace work (see
> "Handoff to plan"); they are **not** decided here.
>
> **Framing (operator-directed, non-negotiable in the finalized brief):** this
> is **NOT** "the operator chose to re-scope toward pi.dev." pi.dev-only was the
> **originally-intended target all along**; the opencode-hosted build was the
> **deviation** from that intent. This brief therefore **corrects the substrate
> back to the originally-intended target**, and the opencode-hosted work is the
> **interim/incorrect substrate now being superseded** — not a baseline being
> changed.

## Problem Statement

Gleipnir's actual contribution is a **capability**, not a codebase: an
AETOS-inherited 8-role roster improved with (a) a deterministic G-5 workflow
engine (a real state machine, not LLM-narrated sequencing) and (b) a "solicited
cognition" layer (Gate-1 Design Intent + Gate-2 honour check). That capability
was always intended to ship as a **plugin for pi.dev** (earendil-works "Pi
Coding Agent") — so Gleipnir rides pi.dev's community-maintained harness rather
than building/maintaining one (opencode).

The current repo implements the whole thing against **opencode** primitives
(`.gleipnir/agents/*.md` frontmatter, `opencode.jsonc`, `@opencode-ai/plugin`
TS plugins). The recorded decision `substrate-design-pass.md` (D-1) frames a
pi.dev target as "a contract-conformance exercise, not a rewrite" — a mechanical
port of opencode-shaped code. **The operator has explicitly rejected that
framing this session.** The intended target is a **ground-up re-expression of
the capability using pi.dev's actual primitives**, not a code shim. The
question needing convergence is the **concrete shape** of that re-platforming —
"should we target pi.dev" is already decided (yes) and is not reopened here.

## Constraints

- **Re-expression, not port.** If a capability must be built differently to fit
  pi.dev's real model, that is the point, not a defect. Do not preserve
  opencode-shaped structure for its own sake.
- **The capability must be preserved:** deterministic G-5 sequencing, the
  deny-by-default roster with per-role capability bounds, the brainstorm
  convergence gate (blocking human question), the cognition layer, the G-3
  attestation, the S-2 blast-radius boundary.
- **pi.dev is MIT, community-maintained, TypeScript-extended.** Gleipnir's
  enforcement core is Python + stdlib-only (`decisions/runtime-and-deps.md`).
  Any pi.dev integration is TypeScript at the harness edge; a Python core can
  only be reached across a process/IPC boundary (RPC/JSON stream), or the core
  logic must be re-expressed in TS.
- D-1 in `substrate-design-pass.md` and the spec's "port = conformance shim"
  wording must be **superseded** by a new decision record; this brief is the
  input to that.

## Explore Findings (pi.dev primitives — verified against primary docs)

Sources: `pi.dev/docs/latest/{extensions,security,sdk,settings,containerization,packages}`
(cross-checked against the earendil-works/pi repo docs). The two crux questions
from the delegation are answered decisively:

### CRUX 1 — Per-agent permission-map primitive: **DOES NOT EXIST as a host primitive**

pi.dev has **no** opencode-style `permission:` block (tool + bash-glob +
path-glob allow/deny/ask, runtime-enforced per agent). Its security model
(`security.md`) is explicit: *"Pi does not include a built-in sandbox… Built-in
tools can read/write/edit files and run shell with the permissions of the pi
process. Real isolation needs to come from the OS or a virtualization/container
boundary."* **Project trust is only an input-loading guard**, not a
capability boundary. What pi.dev *does* offer:

- **Coarse tool gating:** `tools` / `defaultTools` / `excludeTools` /
  `noTools` (SDK + settings) and `pi.setActiveTools(names)` (runtime) select
  *which built-in tools are enabled* — no per-path / per-arg granularity.
- **`tool_call` hook — CAN BLOCK.** `pi.on("tool_call", …)` fires before a tool
  executes and returns `{ block: true, reason?, terminate? }`. `event.input` is
  mutable. **This is the load-bearing primitive:** deny-by-default per-role
  capability enforcement must be *built by Gleipnir as an extension* on top of
  this block hook (inspect tool + args + active-role → allow/deny), because the
  host has no declarative permission map.

**Consequence:** the entire S-1.3.1 deny-by-default roster is **re-expressed**,
not ported. It becomes a Gleipnir extension that holds a role→capability table
and enforces it in the `tool_call` hook. This is exactly the "re-expression"
the operator wants — and it is arguably *more* faithful to G-1/G-2 than the
opencode `permission:` map, because the enforcement logic is Gleipnir's own
code, not a host feature we depend on.

### CRUX 2 — Subagent / task-delegation primitive with a depth cap: **NO first-class primitive; buildable via SDK**

pi.dev has **no** opencode `task` tool + `subagent_depth` cap. But the SDK
explicitly supports it as a documented use case: *"Build custom tools that spawn
sub-agents"* and *"Create automated pipelines with agent reasoning."*
Mechanisms:

- **`createAgentSession()` (in-process):** spin up a fresh scoped
  `AgentSession` with its own `tools`, `customTools`, `resourceLoader`,
  `systemPromptOverride`, `SessionManager.inMemory()`. A Gleipnir-registered
  `delegate` tool can create a child session bounded to a role's tool set.
- **`runRpcMode` / `--mode rpc` (process-isolated):** spawn `pi` as a subprocess
  over JSONL for stronger isolation between roles.
- **Depth cap** is not a host feature → Gleipnir tracks delegation depth in
  extension state (`pi.appendEntry` for session-persisted state) and refuses
  past a cap.

**Consequence:** the orchestrator→subagent delegation model is **re-expressed**
as a Gleipnir-built delegation tool over `createAgentSession`/RPC, with the
depth cap enforced in Gleipnir code.

### Other verified primitives (map to the S-1 8-hook contract)

| # | S-1 requirement | pi.dev mechanism | Status vs opencode |
|---|---|---|---|
| 1 | Pre-tool interception, **can abort** | `tool_call` hook → `{ block: true }` | **Present** (equivalent to `tool.execute.before`) |
| 2 | Post-tool observation | `tool_result` / `tool_execution_end` hooks | **Present** |
| 3 | Per-agent capability declaration | **NONE as host primitive** — build on `tool_call` block hook + `setActiveTools` | **ABSENT as primitive → Gleipnir-built** |
| 4 | Delegation primitive + depth cap | **NONE first-class** — build on `createAgentSession` / RPC; cap in ext state | **ABSENT as primitive → Gleipnir-built** |
| 5 | Human-question primitive (blocking) | `ctx.ui.confirm / .select / .input` (async, blocks) + `ctx.ui.custom()` | **Present** (note: TUI-bound; absent in `-p`/rpc/json non-interactive modes) |
| 6 | Context-compaction hook | `session_before_compact` / `session_compact` — customize/cancel; NOT experimental | **Present & better** (stable, first-class, vs opencode's experimental) |
| 7 | Session-lifecycle events | `session_start` (startup/new/resume/fork), `session_shutdown`, `agent_settled`, etc. | **Present & richer** |
| 8 | Platform-event ingress (inbound webhooks) | none built-in (same as opencode; = E-2) | **ABSENT** (unchanged; compensating external process) |

**Delivery unit:** a **Pi package** (npm/git/local) bundling `extensions/`,
`skills/`, `prompts/`, `themes/`, declared via `package.json` `pi` key or
convention dirs. This is the natural "Gleipnir as a plugin" artifact. Skills
port near-1:1 (pi Skills = Agent Skills, same concept as `.gleipnir/skills/`).

**Config surface:** `.pi/settings.json` (project) + `~/.pi/agent/settings.json`
(global), `.pi/extensions`, `.pi/skills`, `.pi/SYSTEM.md`. `preflight/
config_scan.py` (which parses `opencode.jsonc`) must be re-expressed to scan the
`.pi/*` surface. Note pi loads project resources *only after project trust* —
relevant to G-1/preflight design.

**Sandbox (S-2):** pi.dev's philosophy matches Gleipnir's exactly — no built-in
sandbox, isolation from OS/container. pi offers **Gondolin** (micro-VM,
tool-routing extension), **plain Docker** (whole process), **OpenShell**
(policy sandbox). Gleipnir's `bin/gleipnir-sandbox` (`--network=none`, ro
source, ephemeral container) is a *peer* of these and largely reusable as an
OS-level mechanism; the open choice is whether to keep it or adopt Gondolin.

### Reuse split — confirmed and refined against `src/gleipnir/`

Actual tree: `broker/ bus/ engine/ ledger/ preflight/ sandbox/ verify/`.

**Substrate-agnostic (pure Python, reusable AS-IS behind an IPC edge):**
- `engine/` (G-5 state machine, driver, bridge, judges, allow_table) — reusable
  IF the harness can call it over RPC/subprocess. This is the crux of the
  Python-vs-TS decision below.
- `verify/` (G-3.1 HMAC marker) — protocol-level, reusable.
- `bus/`, `ledger/` (G-4) — runtime-agnostic.
- `broker/{git,pm}` MCP servers — MCP is protocol-level; **but pi.dev's docs
  surveyed here do not confirm an MCP-client config** (opencode's `mcp:` block).
  Needs verification; brokers may need to be reached differently (RPC, or a
  pi custom tool wrapping the broker socket).
- `preflight/boundary.py` (OS-level) reusable; `preflight/config_scan.py`
  needs re-expression for `.pi/*`.
- `bin/gleipnir-{sandbox,preflight,launch}` — OS-level shell, reusable.

**Needs re-expression (opencode-API-specific):**
- `.gleipnir/agents/*.md` (opencode subagent frontmatter) → Gleipnir role table
  consumed by a TS enforcement extension.
- `opencode.jsonc` → `.pi/settings.json` + package manifest.
- `.gleipnir/plugins/*.ts` (compaction-survival, git-guard, advance-hook,
  sequence-gate — all `@opencode-ai/plugin`-shaped) → pi.dev Extensions
  (different event names: `tool_call`, `session_before_compact`, etc.).
- The "orchestrator as prompt-level G-5 stand-in reachable via `task`" model →
  a Gleipnir delegation tool over `createAgentSession`/RPC.

## Approaches Considered

### Approach A: Full pi.dev package, Python enforcement core over RPC ("thin TS edge, fat Python core")

**Summary:** Ship one Pi package. A TS extension wires pi's hooks (`tool_call`
block, compaction, session lifecycle, delegation tool) but delegates all
*decisions* (G-5 sequencing, allow-table, G-3 verify) to the existing Python
`engine/`+`verify/` core reached over a subprocess/RPC edge. Skills port ~1:1.

**Tradeoffs:**
- Pro: **Maximises reuse** of the tested Python enforcement core (`engine/`,
  `verify/`, `bus/`, `ledger/`) — the hardest, most-attested code survives.
- Pro: Keeps enforcement logic in the stdlib-only Python core
  (`runtime-and-deps.md` honoured); TS is a thin, auditable adapter.
- Pro: Python core stays runtime-portable (could back a future non-pi harness).
- Con: Introduces a **TS↔Python IPC seam** inside the hot path of every tool
  call — latency, serialization, and a new failure/spoofing surface (the block
  decision crosses a boundary). The `tool_call` hook is synchronous-ish; a slow
  IPC round-trip per tool call is a real cost.
- Con: Two languages to maintain; the "plugin" is really "plugin + sidecar."

**Estimated Scope:** New `extensions/` (TS adapter, delegation tool, hook
wiring), RPC bridge to `engine/`, re-expressed `config_scan`, package manifest,
skills copied. Python core largely untouched. **Complexity: high.**

**Risk:** Medium-high — the IPC-in-the-block-path is the novel risk; if pi's
`tool_call` can't cleanly await a subprocess decision, the model breaks.

### Approach B: Full pi.dev package, enforcement re-expressed in TypeScript ("native TS, retire the Python core at the edge")

**Summary:** Ship one Pi package that is **pure TypeScript**. Re-express the
G-5 engine, allow-table, and per-role capability enforcement as TS running
directly inside the extension (`tool_call` block hook calls in-process TS logic;
delegation via `createAgentSession`). The Python core is retired *for the pi
target* (kept only if a non-pi target is ever revived).

**Tradeoffs:**
- Pro: **No IPC seam** — the block decision is in-process, fast, single failure
  domain. Most faithful to "rides pi's harness."
- Pro: A single-language, idiomatic Pi package — cleanest possible "plugin,"
  easiest for the pi community to read/trust; distributes via npm/git natively.
- Pro: True to the operator's "ground-up re-expression of the capability, not
  the code" — the G-5 *idea* is re-implemented in the host's language.
- Con: **Discards the tested Python `engine/`/`verify/`** for this target — the
  most-attested code is rewritten (sunk-cost tension; but see bias note).
- Con: Re-expressing G-3 HMAC + G-5 determinism in TS must re-earn its test
  coverage; correctness burden shifts to new TS tests.
- Con: Conflicts with `runtime-and-deps.md`'s "stdlib-only Python enforcement
  core" decision — that decision would need explicit supersession for the pi
  target (TS + pinned peer deps instead).

**Estimated Scope:** New TS engine + allow-table + verify + hook wiring +
delegation tool + config scan; skills copied; package manifest; full TS test
suite. Python core untouched on disk but unused by pi target. **Complexity:
high** (net-new TS engine) but **lower operational complexity** (one language,
no sidecar).

**Risk:** Medium — rewriting the engine is bounded by the existing spec + tests
as an oracle, but it is genuinely new code that must re-earn trust.

### Approach C: Dual-target — shared Python core, both opencode and pi.dev adapters

**Summary:** Keep opencode working; add a pi.dev adapter alongside. Factor the
enforcement core so both an opencode plugin and a pi extension call the same
Python `engine/` over a common bridge. Gleipnir supports both harnesses.

**Tradeoffs:**
- Pro: No loss of the working opencode implementation; migration is incremental.
- Pro: Proves the "substrate-agnostic core" thesis concretely (two adapters).
- Con: **Directly contradicts the operator's correction** — this is the
  "port/conformance shim, dual-target" framing they rejected. It treats pi as a
  second adapter over opencode-shaped code, not a ground-up re-expression.
- Con: Highest ongoing maintenance (two harness edges, two hook vocabularies,
  two config surfaces forever); the IPC seam of A *plus* opencode upkeep.
- Con: Scope-creep — avoids the choice by keeping everything.

**Estimated Scope:** Everything in A, **plus** retaining/refactoring all
opencode glue behind a shared bridge. **Complexity: very high.**

**Risk:** High — largest surface, and it is the shape the operator explicitly
rejected; likely a convergence non-starter, included for completeness and as the
"do the least disruptive thing" strawman.

### Approach D: pi.dev-only, phased — TS enforcement edge first, reuse Python where the seam is cheap

**Summary:** A pragmatic hybrid of A and B. Commit to pi.dev-only (retire
opencode), but decide the Python-vs-TS boundary **per component by seam cost**,
not globally: re-express the *hot-path* enforcement (per-role `tool_call`
block, delegation, allow-table) in TS (no IPC in the hot path, per B); keep
*off-hot-path* Python components (`bus/`/`ledger/` G-4 observer, `verify/`
attestation batch checks, brokers) reachable over RPC where the seam is cheap
and reuse is high (per A). Ship as one Pi package + optional Python sidecar for
the off-path services.

**Tradeoffs:**
- Pro: Puts the IPC seam only where latency doesn't matter (audit/observer),
  never in the per-tool-call block decision — gets B's hot-path speed and A's
  reuse of the expensive-to-rewrite audit/ledger code.
- Pro: pi.dev-only (honours the correction), one primary language for the
  enforcement edge, incremental (Python sidecar can be absorbed into TS later).
- Pro: Lets the `runtime-and-deps.md` supersession be *scoped* — TS for the
  edge, Python retained for the sidecar services — rather than all-or-nothing.
- Con: A boundary that runs through the middle of the system needs a crisp,
  documented rule for what lives where, or it rots into ad-hoc.
- Con: Still two languages during the transition (though with a clear retirement
  path for the sidecar).

**Estimated Scope:** TS enforcement extension (engine sequencing + allow-table +
delegation + hooks) re-expressed; Python `bus`/`ledger`/`verify`/brokers kept
behind a documented RPC edge; `config_scan` re-expressed; skills copied;
package manifest. **Complexity: high**, but risk-partitioned.

**Risk:** Medium — the seam-placement rule is the thing to get right; otherwise
bounded by spec + existing tests.

## Decision Analysis

**Framework used:** **Weighted Decision Matrix** (multi-option comparison across
criteria — the auto-selection primary for "multi-option comparison"),
preceded by the **Reversibility Filter** (mandatory first step) and followed by
**Second-Order Thinking** on the Python-vs-TS core question (architectural
tradeoff with long-term consequences).

### Reversibility Filter

- **The pi.dev target decision:** already made by the operator; not in scope.
- **The scope decision (A/B/C/D) & the Python-vs-TS core boundary:**
  **One-Way Door (mostly).** Choosing to re-express the engine in TS (B) or
  retire opencode (B/D) is expensive to undo — it means a rewrite and a
  superseded `runtime-and-deps.md` decision. Choosing dual-target (C) is more
  reversible but commits to ongoing dual maintenance. → **Apply deeper analysis
  (Weighted Matrix + Second-Order).**

### Weighted Decision Matrix

Criteria weighted by the framework goal ("quality-efficient outcomes per token"
+ the operator's explicit "re-expression not port" directive):

| Criterion | Weight | A (Py core/RPC) | B (native TS) | C (dual-target) | D (phased hybrid) |
|---|---|---|---|---|---|
| Fidelity to operator's "re-express, not port" directive | 10 | 6 → 60 | 9 → 90 | 2 → 20 | 8 → 80 |
| Preserves capability (G-1/2/3/5 + cognition) | 10 | 8 → 80 | 8 → 80 | 8 → 80 | 8 → 80 |
| Hot-path correctness/simplicity (no IPC in block decision) | 8 | 4 → 32 | 9 → 72 | 4 → 32 | 8 → 64 |
| Reuse of tested/attested code | 7 | 9 → 63 | 4 → 28 | 9 → 63 | 7 → 49 |
| Ongoing maintenance cost (lower = better) | 7 | 5 → 35 | 8 → 56 | 2 → 14 | 6 → 42 |
| "Rides pi's community harness" cleanliness (as a shareable package) | 6 | 5 → 30 | 9 → 54 | 3 → 18 | 7 → 42 |
| Implementation risk (higher score = lower risk) | 6 | 5 → 30 | 6 → 36 | 4 → 24 | 6 → 36 |
| **Total** | | **330** | **416** | **251** | **393** |

**Recommended (advisory): Approach B (native TS), with Approach D as the strong
runner-up.** B scores highest on the operator's headline directive and hot-path
cleanliness; D is within ~5% and de-risks by keeping the expensive-to-rewrite
audit/ledger/verify code in Python behind an off-hot-path seam. C ranks last and
is the rejected framing. A is dominated by D (D puts the IPC seam only where A's
cost doesn't bite).

**Caveats where the winner scores poorly:** B's weakest cell is "reuse of tested
code" (4) — it rewrites the engine/verify. If the operator weights the existing
Python test coverage more heavily (e.g. correctness confidence > re-expression
purity), **D overtakes B.** The B-vs-D decision hinges on that weight.

### Second-Order Thinking (Python core vs TS re-expression)

- **Near term (B):** rewriting `engine/`/`verify/` in TS costs weeks and
  re-earns test coverage. **Second-order:** a single-language package is far
  easier for the pi community to audit/adopt, and removes the sidecar
  operational burden permanently.
- **Near term (D):** keep Python sidecar → faster to first working package.
  **Second-order:** the sidecar seam persists; risk it never gets retired and
  Gleipnir stays bi-lingual indefinitely (the C failure mode by the back door).
- **Far term key insight:** the decision is really *"is the enforcement core
  Gleipnir's portable asset (keep Python, harness-agnostic) or is the pi package
  the product (go native TS)?"* The operator's correction ("Gleipnir's
  contribution is the capability… ships as a plugin for pi.dev") leans toward
  **the package being the product → B**. But if a future non-pi target is still
  wanted, the portable Python core (A/D) retains option value.

### Bias warnings

- ⚠️ **Sunk Cost Fallacy** — The pull toward A/C/D partly rests on *"we already
  built and tested the Python `engine/`/`verify/`."* Past investment is not a
  reason to keep it. The question is future value: *if starting today on pi.dev
  with no prior code, would we write a Python core reached over IPC, or native
  TS?* Answer that independently of what already exists.
- ⚠️ **IKEA Effect** — The Python enforcement core is Gleipnir's own hand-built
  artifact; its elegance may be overweighted vs the plain fact that pi.dev is a
  TS harness and a TS-native package is the idiomatic, lower-friction fit. Judge
  the core as if someone else wrote it.
- ⚠️ **Status Quo Bias** — Approach C (dual-target, keep opencode) is the "change
  the least" option and will feel safe. The operator has *already* flagged that
  the status-quo framing (port/shim) is wrong; C should get no free pass and is
  ranked last accordingly.
- (Also detected, lower confidence: **Scope Creep Bias** on C/D — "keep both
  harnesses / keep both languages" avoids the choice; force the boundary to be
  explicit.)

**Recommendation (advisory only — the operator decides):** **Approach B** if the
operator values a clean single-language pi-native package and accepts rewriting
the engine under the existing spec+tests as oracle; **Approach D** if the
operator wants to preserve the tested Python audit/ledger/verify code and accepts
a scoped, documented Python sidecar seam off the hot path. **C is not
recommended** (it is the rejected framing). This recommendation is the *input*
to convergence, not the decision.

## Selected Approach

**Choice: Approach B — native TypeScript re-expression, pi.dev-ONLY, full
substrate rewrite.**

Gleipnir's capability (the AETOS-inherited 8-role roster, the deny-by-default
per-role permission enforcement, the delegation model, the deterministic G-5
engine, the G-1..G-6 guard stack, and the solicited-cognition layer) is
**re-expressed from the ground up as a native pi.dev TypeScript package** — a
Pi package bundling an enforcement `extension/` (role→capability table enforced
in the `tool_call` block hook), a `delegate` custom tool over
`createAgentSession`/RPC with a depth cap held in extension state, a
TypeScript re-implementation of the G-5 engine + judges + G-3 verify logic
running in-process, and the methodology `skills/` carried across near-1:1. The
Python enforcement core (`engine/`, `verify/`, and the allow-table logic) is
**retired at the pi edge**.

**This is explicitly a full substrate rewrite of the capability, not a port of
the existing opencode-shaped code and not a shim.** No opencode-API-shaped
artifact is carried over as-is: the opencode subagent frontmatter, the
`opencode.jsonc` root config, the `@opencode-ai/plugin` TypeScript plugins, and
the "orchestrator-as-prompt-stand-in-reachable-via-`task`" model are all
**re-expressed** using pi.dev's actual primitives, because pi.dev provides no
per-agent permission-map primitive and no first-class `task`/`subagent_depth`
delegation primitive (see Explore CRUX 1 & 2 above) — those capabilities are
therefore Gleipnir-built in TypeScript, which is the point, not a defect.

**Rationale:**

1. **It correctly serves the originally-intended target.** Per the operator's
   framing note at the top of this brief, pi.dev-only was always the intended
   substrate; the opencode-hosted build was the deviation. Approach B (native
   TS, pi-only) *is* that originally-intended shape realised — a single-language
   Pi package that rides pi.dev's community-maintained harness.
2. **Highest weighted-matrix score (B = 416),** ahead of D (393), A (330), and
   C (251 — the rejected dual-target/port framing). B led on the two
   highest-weight criteria (fidelity to "re-express, not port"; capability
   preservation) and on hot-path correctness (no IPC in the per-tool-call block
   decision) and package cleanliness.
3. **The convergence explicitly resolved the B-vs-D pivot in B's favour.** The
   matrix flagged that B's one weak cell was "reuse of tested Python code," and
   that a heavier weight on existing test coverage would tip to D. The operator
   weighted a clean single-language pi-native package and the retirement of the
   bi-lingual sidecar burden above preserving the Python core — accepting the
   engine/verify rewrite, bounded by the existing spec + tests as the oracle.
4. **The Sunk-Cost and IKEA-Effect bias warnings were consciously honoured, not
   overridden.** The tested Python core is not a reason to keep it at the pi
   edge; judged as future value on a TS harness, native TS is the idiomatic fit.

**Consequence:** the stdlib-only-Python-core constraint in
`decisions/runtime-and-deps.md` is superseded **for the enforcement core going
forward** (TypeScript + pinned pi peer-deps replaces it at the pi edge). This
requires a durable amendment/supersession note on that record — it must **not**
be silently dropped. See "Decision records to supersede/amend" below.

## Decision records to supersede/amend (NAME ONLY — not amended here)

These are Tier-3 durable records outside this brief's Tier-0 writer grant. They
are **named for the plan stage / operator to edit**; `gleipnir-brainstorm` does
not touch them. Each needs a supersession or amendment note (not a silent
change), consistent with the "correction back to the originally-intended target"
framing.

| # | Record / artifact | What must change | Nature |
|---|---|---|---|
| 1 | `.gleipnir/decisions/substrate-design-pass.md` — **D-1** | "opencode for v0.1; a pi.dev/pinion port is a contract-conformance exercise, not a rewrite" is **reversed**. Target is pi.dev-only; the work is a native TS re-expression (full rewrite), not a conformance port. The S-1 hook table must be re-verified against pi.dev primitives (CRUX 1 & 2: no permission-map, no `task` primitive → both Gleipnir-built). | **Supersede** |
| 2 | `.gleipnir/decisions/runtime-and-deps.md` — stdlib-only-Python-core constraint | Superseded **for the enforcement core**: TypeScript (with pinned pi peer-deps: `@earendil-works/pi-coding-agent`, `typebox`, etc.) replaces the stdlib-only-Python core at the pi edge. | **Amend/supersede** (scoped) |
| 3 | `gleipnir_specification_v0_3_12.md` — **D-1 register entry (line ~302)**, the Part-D substrate narrative (~line 310, ~334), and the "target opencode's hooks directly for v0.1… pi.dev port via pinion is a contract-conformance exercise, not a rewrite" statement (**line ~66**) | Same reversal as (1), at spec level. Candidate for a v0.3.13 revision. The E-2 entry's "ephemeral opencode target" wording (~line 323) also needs a pi.dev re-frame. | **Supersede** (next spec rev) |
| 4 | `.gleipnir/AGENTS.md` — "Why `.gleipnir/` and not `.opencode/`" section + `OPENCODE_CONFIG_DIR` framing + the guard-status table's opencode-hook references | The rationale is now pi.dev-centric (`.pi/` config surface, `ctx.isProjectTrusted`, pi extension/package model), not opencode's `OPENCODE_CONFIG_DIR`. Layout intent survives; the harness framing is re-expressed. | **Amend** |
| 5 | `.gleipnir/stage-role-map.md` — Axis-2(a) enforcement-path set `E` and Axis-1 disqualifier set `X` | The opencode-tied literals (`opencode.jsonc`/`**/opencode.json`, the `.gleipnir/plugins/**` opencode-plugin path, JSON(C) enforcement keys like `default_agent`/`subagent_depth`/`mcp`) must be re-expressed for pi.dev's surface (`.pi/settings.json`, `.pi/extensions/**`, the Pi package manifest `pi` key). The routing *mechanism* survives; the enumerated paths/keys change. | **Amend** |
| 6 | `src/gleipnir/preflight/config_scan.py` + its tests (`tests/test_config_scan_*.py`) | Re-expressed to scan the `.pi/*` surface + package manifest instead of parsing `opencode.jsonc`'s `agent:`/`tools:`/`mcp:` shape. (Code artifact, not a decision record, but named because the plan must sequence it.) | **Rewrite** (TS or scoped) |
| 7 | `bin/gleipnir-launch`, `bin/gleipnir-preflight`, `.gleipnir/policy/context-cap.jsonc`, `.github/workflows/config-scan.yml`, `hooks/pre-commit`, `opencode.jsonc` | All contain opencode-specific launch/exec/config-mirror/CI wiring (`exec opencode`, `OPENCODE_CONFIG_DIR`, opencode.jsonc `limit.context` mirror, config-scan-on-opencode-roster). Re-expressed for the pi launch/config model or retired. | **Rewrite/retire** |

> **Not exhaustive of every opencode string in the tree.** The Explore grep
> showed opencode references also threaded through `engine/driver.py`,
> `engine/__init__.py` (the "each opencode hook call is a fresh process"
> resume-from-bridge assumption), the broker MCP servers, and numerous test
> docstrings. The plan stage owns the full inventory; this table names the
> **decision records and the load-bearing enforcement wiring** that must not be
> changed silently.

## Handoff to plan — open ATLAS Architect/Trace questions (NOT decided)

These four are **not blocking further convergence** and are **not answered here**
— `gleipnir-plan` must resolve them during ATLAS Architect/Trace. Do not let a
downstream stage silently pick an answer.

1. **Sandbox (S-2) choice:** keep Gleipnir's `bin/gleipnir-sandbox` (ephemeral
   container, `--network=none`, ro source) as the OS boundary, **or** adopt
   pi.dev's **Gondolin** micro-VM tool-routing extension (or Docker/OpenShell)?
   Philosophically identical postures; this is reuse-of-our-mechanism vs
   consume-the-community-primitive. Trace: what does each cost in the pi launch
   model, and which preserves the caged-mode guarantees?
2. **Blocking human-gate in non-interactive modes:** pi's human-prompt
   primitives (`ctx.ui.confirm/select/input/custom`) are **TUI-bound and absent
   under `-p` / `--mode rpc` / `--mode json`**. The precept-10 convergence gate
   and every blocking-question guard depend on a real block. Architect a
   compensating design for unattended/automated runs (e.g. a pipeline decision
   state that fails-closed with no outgoing edge, an external question sink, or
   a policy that the gate-bearing stages require interactive mode).
3. **MCP-broker reachability from a pi extension:** the surveyed pi.dev docs do
   **not** confirm an opencode-style MCP-client config (`mcp:` block). Trace
   whether the git/pm brokers (`src/gleipnir/broker/{git,pm}/mcp_server.py`) are
   reachable from a pi extension via a documented MCP client, or must be reached
   via RPC / a custom-tool socket wrapper — this bears on the G-2 single-holder
   broker boundary.
4. **Migration/retirement sequencing of the opencode-hosted artifacts:** since
   this is a full replace, when are the opencode artifacts (config, plugins,
   agent frontmatter, config-scan, launch wiring) retired — big-bang at pi
   package parity, or kept inert until the pi package passes S-3 preflight + the
   AC acceptance tests? Architect the cutover so the tree is never in a
   half-enforced state.

## Scope Sketch

| Area | Artifact / module likely affected |
|------|-----------------------------------|
| Delivery unit | New **Pi package** (`package.json` `pi` key + `extensions/ skills/ prompts/ themes/`) |
| Enforcement edge | New TS extension: `tool_call` block hook + role→capability table (re-expresses the deny-by-default roster) |
| Delegation | New TS `delegate` tool over `createAgentSession`/RPC + depth cap in ext state (re-expresses `task`/`subagent_depth`) |
| G-5 engine | `src/gleipnir/engine/**` — **rewritten natively in TypeScript** (Approach B); Python retired at the pi edge |
| G-3 verify | `src/gleipnir/verify/**` — **TypeScript re-expression** (HMAC marker in-process in the extension) |
| G-4 bus/ledger | `src/gleipnir/{bus,ledger}/**` — re-expressed in TS (single-language package); off-hot-path, plan may stage separately |
| Compaction survival | `.gleipnir/plugins/compaction-survival.ts` → pi `session_before_compact`/`session_compact` extension |
| Git guard / advance / sequence | `.gleipnir/plugins/{git-guard,advance-hook,sequence-gate}.ts` → pi Extensions (event-name remap) |
| Roster | `.gleipnir/agents/*.md` → Gleipnir role table consumed by the enforcement extension |
| Root config | `opencode.jsonc` → `.pi/settings.json` + Pi package manifest (`package.json` `pi` key) |
| Config preflight | `src/gleipnir/preflight/config_scan.py` → re-expressed for the `.pi/*` surface + package manifest |
| Sandbox | `bin/gleipnir-sandbox` retained OR pi's Gondolin adopted — **plan-stage ATLAS question (Handoff #1), not decided** |
| Skills | `.gleipnir/skills/**` → pi `skills/` (near-1:1) |
| Decisions/wiring to supersede | see "Decision records to supersede/amend" table above (rows 1–7) |
| Decisions to supersede | `decisions/substrate-design-pass.md` D-1; `decisions/runtime-and-deps.md` (if TS core); spec "port = conformance shim" wording |
