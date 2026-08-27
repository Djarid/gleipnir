# Plan: S6 — Broker / credential isolation (G-2) reachability from a pi extension

> **Role:** `gleipnir-plan` (plan stage). **Planned FROM** the CONVERGED brief
> `.gleipnir/plans/pi-dev-replatform-s6-brainstorm.md` (all five decisions
> D-S6-1..5 decided by the operator; **all five MATCHED the brainstorm
> recommendation — no divergence**). This plan does NOT re-derive those
> decisions; it refines them into concrete Assemble steps and an
> acceptance-check set traceable to the two UNCHANGED Python brokers
> (`src/gleipnir/broker/git/mcp_server.py`, `src/gleipnir/broker/pm/mcp_server.py`)
> and grounded in the proven pi-package idioms (`delegate.ts`, `enforcement.ts`,
> `roleTable.ts`, `activeRole.ts`) + the pi SDK primary docs, all read directly
> this session (L-C36).

## GOTCHA pre-flight (visible)

- **Goals checked:** `.gleipnir/goals/manifest.md` → `plan-format.md` is the
  binding artifact/format goal; this plan follows its 8 required sections
  including the **Design Principles** Gate-1 section (case (i), OOP/functional
  TS). `methodology.md` (ATLAS/GOTCHA-ahead-of-planning) satisfied by this
  plan's shape.
- **Plan-before-code:** confirmed. `pi-package/src/broker/` does NOT yet exist
  (glob of `pi-package/src` returns `roleTable/enforcement/delegate/depth/
  activeRole.ts` + `engine/*` + `verify/*` + `enginePersistence.ts` — no
  `broker/`). `pi-package/test/broker.test.ts` / `mcpStdioClient.test.ts` do
  NOT exist. This is a plan; it writes only to `.gleipnir/plans/`.
- **GOTCHA layer mapping:** this slice spans two GOTCHA layers. The
  MCP-over-stdio client + broker tool `execute` handlers are the **Tools**-layer
  capability boundary (the deterministic-code half that relays a bounded tool
  call to a spawned subprocess). The `roleTable`/`canUse` glob-to-concrete
  resolution is the **Context/Args**-layer capability-data boundary. No new
  **Orchestration** (G-5 engine) or **Hard-prompt** work.
- **Capability boundary:** I may write ONLY `.gleipnir/plans/**`. This plan file
  is the sole artifact I produce. No code, no tests, no Tier-3.
- **MANDATORY Trace verification (per delegation + brief L-C36): DONE against
  primary source** — see §Link and §Trace. **Two findings require operator
  awareness (NOT full blockers, but flagged):** (1) the **hand-rolled client
  premise HELD** — no new dependency needed; but (2) **the pi-profile sandbox
  image has NO Python interpreter** (`node:22-slim`), so the round-trip test
  harness cannot spawn a real Python broker in-sandbox. This is handled with a
  MOCK stdio broker (a tiny Node script) — the same sandbox/auth-residual
  pattern S3/S5 used — and does NOT block the plan, but it is called out in
  `## Test-harness constraint (Python-in-sandbox finding)` and in my final
  report.

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-S6-1 | Which reach mechanism S6 uses | **Approach A** — self-authored first-party custom-tool MCP-over-stdio client; the `execute` handler spawns the UNCHANGED Python broker (`python -m gleipnir.broker.{git,pm}.mcp_server`) as an MCP-over-stdio subprocess, relays `initialize` + `tools/call`, returns the structured result | B (3rd-party `pi-mcp-extension` + `.pi/mcp.json`), C (`runRpcMode` process isolation) | Operator-converged (brief §Selected Approach). A wins on trust-surface minimisation + no-new-untrusted-config-surface (`runtime-and-deps.md` → G-1/G-2). Whole reach path stays Gleipnir-owned + auditable + inside S-2. |
| D-S6-2 | Reopen Open-Q1 (in-process vs process-isolated)? | **NO — Open-Q1 stays closed, `decisions/pi-replatform-open-q1.md` UNAMENDED** | reopen + adopt `runRpcMode` | Operator-converged. Because D-S6-1=A (not C), the Open-Q1 revisit-trigger ("requires process isolation for any role") was NOT met. In-process reach with tight credential-env-scoping (D-S6-3) is sufficient. No Tier-3 edit authorised. |
| D-S6-3 | Credential-injection scoping | **Broker child inherits/self-fetches its credential; the extension NEVER reads or forwards the value** | extension reads `process.env.<TOKEN>` and forwards it | Operator-converged. Token lives ONLY in the spawned broker child's own env; the extension names WHICH vars pass through (or lets the child inherit from the launch context), never reading the VALUE into its own heap. A test asserts no secret substring in any relayed payload. **Trace finding refines this — see D-S6-P2.** |
| D-S6-4 | Build-order position | **Keep S6 in place; buildable now** | pull earlier | Operator-converged. [ASSUMPTION-4] DISCHARGED: the S3-shaped custom-tool wrapper materialised, but nothing downstream depended on broker reachability (S4/S5 closed without it). No resequencing. |
| D-S6-5 | E-1 argument-policy scope in S6 | **Option 5a — coarse broker REACHABILITY + credential isolation only; E-1 arg-level policy DEFERRED to S7** | 5b (pull arg bounds forward), 5c (thin pass-through hook-bypass screen) | Operator-converged. The broker's OWN Python-side `_run_git` hard invariant (refuse `--no-verify`/`-n`/`-c core.hooksPath`) stays authoritative for hook-bypass safety. **Correctness constraint (tested):** the relay passes only structured MCP tool params, NEVER raw argv, so `_run_git` stays the authoritative choke point (verified: the brokers expose `commit_changes(message,...)`, not a `git commit --no-verify` argv surface — see §Trace). |
| D-S6-1b | **OPERATOR-CONVERGED** (via the orchestrator's `question` tool, after spec-review declined to self-clear the original plan-stage-judgment): how the inert `"gleipnir-git_*"`/`"gleipnir-pm_*"` glob literals in `roleTable.ts` resolve to the concrete relayed tool names for `canUse` | **Register the 4 concrete broker tool names per broker as literal DATA ROWS in the existing table partitions, resolved via `canUse`'s CURRENT exact-match `.includes()` — ZERO edit to the shared `canUse` matching code path.** git: `gleipnir-git_git_status`, `gleipnir-git_git_diff`, `gleipnir-git_commit_changes`, `gleipnir-git_push_current_branch` in `git-ops.brokerTools`; pm: `gleipnir-pm_issue_create`, `gleipnir-pm_issue_update`, `gleipnir-pm_issue_comment`, `gleipnir-pm_issue_close` in `project-mgr.customTools`. The single glob-shaped entry per broker is REPLACED by the 4 concrete literals (the cleanest mechanical shape: the inert placeholder becomes the real reachable set). | (the ORIGINAL plan's `*`-suffix glob matcher inside `canUse` — REJECTED: it touches the SHARED enforcement choke-point every role's every `tool_call` passes through, and `roleTable.ts` is one of the five D-S4-6 "ZERO edits" modules — a boundary reinforced by S5, NOT narrowed) | **Operator decision, NOT plan-stage judgment.** Spec-review flagged the original glob-matcher approach as touching the shared `canUse` choke-point on an untouchable-list module (D-S4-6), judged the S5 D-S5-P1 precedent NOT analogous (D-S5-P1 concerned files NOT on the untouchable list; `roleTable.ts` IS on it), declined to self-clear, and routed it to the operator. The operator converged on the LOWER-BLAST-RADIUS alternative the plan had named but not chosen: concrete-name DATA registration using `canUse` unchanged. `canUse` (roleTable.ts L248-260) is EXACT `.includes(toolName)` across all three partitions — so 4 literal names per broker resolve correctly with ZERO code change. The G-2 sole-holder property is preserved: only `git-ops` lists the git names, only `project-mgr` the pm names. Confirmed 4+4 names against `src/gleipnir/broker/{git,pm}/mcp_server.py` (read in full in original Trace). |
| D-S6-P2 | **[PLAN-STAGE JUDGMENT]** Exact credential env-passthrough shape per broker (D-S6-3 concretised against ACTUAL broker source) | **git broker: NO env passthrough at all** — git push credentials are AMBIENT (git's own credential helper / SSH agent / `~/.git-credentials`), reached only by the spawned git subprocess; the extension passes NOTHING credential-bearing. **pm broker: pass `GITHUB_TOKEN`/`GITLAB_TOKEN` BY NAME only** — the child spawn inherits the parent process env (`spawn(..., { env: process.env })` or an explicit allowlist of NAMES copied from `process.env` WITHOUT the extension logic reading/branching-on the value), and `platform.py::get_token` reads `os.environ[...]` inside the CHILD exactly as it already does. The extension code never dereferences the token value into a local variable it inspects/logs/forwards-as-a-literal. | (read `process.env.GITHUB_TOKEN` into a JS variable and forward it as an explicit `env: { GITHUB_TOKEN: theValue }` — this transits the value through the extension heap, Pre-Mortem #1) | Delegation item 2/4: confirm via reading the broker source whether ANY env passthrough is needed. **CONFIRMED by reading source:** `platform.py` L110-122 (`get_token` reads `os.environ["GITHUB_TOKEN"]`/`["GITLAB_TOKEN"]`); git `mcp_server.py` reads NO token (ambient). So git needs none; pm needs by-NAME inheritance only. **Flagged for spec-review** (§Open Items). |
| D-S6-P3 | **[PLAN-STAGE JUDGMENT]** Broker-child lifecycle (spawn-per-call vs long-lived) + AbortSignal propagation | **Spawn-per-call, with `signal` (execute param 3, an `AbortSignal`) wired to kill the child** — each `execute` spawns the broker, does `initialize` + one `tools/call`, reads the result, then closes stdin and lets the child exit (or kills it in a `finally`). `signal.addEventListener("abort", () => child.kill("SIGTERM"))` propagates cancellation. Rationale: the broker servers are STATELESS per call (pm re-detects the remote every call; git shells out fresh), so a long-lived child buys nothing and adds session-lifecycle/`session_shutdown`-cleanup complexity + a shared-mutable-state SRP smell. Spawn-per-call is the simplest correct shape and matches the brokers' own statelessness. | (long-lived child pooled across calls — needs `session_shutdown` teardown + concurrency framing over one stdio pipe; premature) | Delegation item 1: confirm the pi custom-tool execute API exposes cancellation and can kill the child cleanly. **CONFIRMED from primary source:** `execute(toolCallId, params, signal, onUpdate, ctx)` — `signal` is an `AbortSignal` (pi.dev/docs extensions Quick Start + delegate.ts's own `_signal: AbortSignal` param). `node:child_process` is available (Node built-ins available in extensions). **Flagged for spec-review** (§Open Items). |
| D-S6-P4 | **[PLAN-STAGE JUDGMENT]** MCP-stdio client library choice (the brief's CENTRAL TENSION) | **Hand-rolled minimal JSON-RPC-over-stdio client** implementing ONLY the `initialize` handshake + `tools/call` request/response subset the fixed 4-tool-per-broker surfaces need — ZERO new npm dependency. Uses `node:child_process.spawn` + newline/`Content-Length`-framed JSON over the child's stdin/stdout. | (`@modelcontextprotocol/sdk` client — a NEW runtime dependency on the enforcement core's most sensitive path, against `runtime-and-deps.md`) | Delegation item 4 + brief's flagged tension: the convergence chose Approach A ON THE BASIS of "zero third-party dependency," so silently adopting `@modelcontextprotocol/sdk` would diverge from the basis of the operator's choice. **Trace VERIFIED the hand-rolled approach is feasible** (see §Trace "Hand-rolled feasibility"), so NO escalation is required and NO `## BLOCKING` section is present. If it had proven genuinely infeasible, this plan would carry a `## BLOCKING — needs operator convergence` section per the delegation; it does not. **Flagged for spec-review** (§Open Items). |

## Architect

**Problem (one sentence).** Make the inert `git-ops.brokerTools =
["gleipnir-git_*"]` (and the pm namespace in `project-mgr.customTools`) into
REAL, reachable capabilities by writing a first-party pi-package extension whose
custom-tool `execute` handlers spawn the UNCHANGED Python MCP-over-stdio brokers
as subprocesses and relay a bounded `tools/call`, so exactly one role can invoke
each broker namespace — WITHOUT the calling role ever holding the underlying
credential (G-2 single-holder preserved at the reachability layer, not just the
table layer).

**User.** The `git-ops` role (git broker) and `project-mgr` role (pm broker),
which today hold an inert declared name that resolves through `canUse` but
reaches no real tool; and transitively the operator, whose commit/push and
issue-lifecycle actions now route through the audited, credential-isolated
broker path rather than an unreachable placeholder. Downstream: S7 (E-1
argument-policy preflight) will add per-arg/per-path bounds on top of this
coarse reachability — S6 leaves that seam clean and deferred.

**Measurable success criteria.**
1. A new `pi-package/src/broker/mcpStdioClient.ts` exports a minimal
   MCP-over-stdio client (hand-rolled JSON-RPC, `node:child_process` +
   `node:*` builtins only, NO new dependency) that, given a spawn spec
   (`command`, `args`, env-var NAMES to pass through) + a tool name + params +
   an `AbortSignal`, spawns the child, performs `initialize` + one `tools/call`,
   returns the child's structured JSON result, and kills the child on abort or
   completion.
2. `pi-package/src/broker/gitBroker.ts` registers the four git broker tools
   (`git_status`, `git_diff`, `commit_changes`, `push_current_branch`) as
   pi custom tools named `gleipnir-git_<tool>`, whose `execute` relays via the
   client to `python -m gleipnir.broker.git.mcp_server` with NO credential
   passthrough (ambient git creds); and `pi-package/src/broker/pmBroker.ts`
   registers the four pm tools (`issue_create`, `issue_update`,
   `issue_comment`, `issue_close`) named `gleipnir-pm_<tool>`, whose `execute`
   relays to `python -m gleipnir.broker.pm.mcp_server` passing ONLY the token
   env-var NAME (`GITHUB_TOKEN`/`GITLAB_TOKEN`) through inheritance.
3. `roleTable.ts` registers the 4 concrete broker tool names per broker as
   literal DATA ROWS in the existing partitions (git names in
   `git-ops.brokerTools`, pm names in `project-mgr.customTools`), resolved via
   `canUse`'s CURRENT exact-match `.includes()` — the `canUse` function body is
   BYTE-IDENTICAL before/after (D-S6-1b, operator-converged):
   `canUse("git-ops", "gleipnir-git_commit_changes") === true`,
   `canUse("project-mgr", "gleipnir-pm_issue_create") === true`, and
   `canUse(<any other role>, <either concrete name>) === false`. The single
   inert glob-shaped entry per broker is REPLACED by the 4 concrete literals;
   the G-2 sole-holder property (only one role lists each namespace's names) is
   preserved by construction.
4. **G-2 reachability proof (the AC to earn):** extended from S2's table-entry
   assertion to REAL reachability — exactly one role can invoke each broker
   namespace's concrete tools (`git-ops` for git, `project-mgr` for pm), and
   every other role is denied by `canUse` + the `tool_call` block hook.
5. **Credential-non-leak:** no relayed tool result or error, and no value the
   extension constructs, contains the token substring; the extension never
   dereferences `process.env.<TOKEN>` into an inspected local (tested with a
   sentinel-token fixture).
6. **Relay-passes-structured-params-only:** the relay sends MCP `tools/call`
   params (e.g. `{message: "..."}`), never a raw argv, so the broker's
   Python-side `_run_git` hook-bypass screen remains the authoritative choke
   point (tested: a params object mentioning `--no-verify` in a commit MESSAGE
   is passed as the message value, exactly as `_run_git` already tolerates —
   see §Trace).
7. All tests run green under `bin/gleipnir-sandbox --profile pi`
   (`--network=none`) using a MOCK stdio broker (a tiny Node script speaking the
   minimal MCP subset), because the pi-profile image has no Python interpreter
   and no network — see `## Test-harness constraint`.
8. ZERO change to the Python brokers (`src/gleipnir/broker/**`). ZERO widening
   of any role's declared capability (deny-by-default preserved; the only
   `roleTable.ts` change is DATA — the 4 concrete broker names per broker
   registered as literal rows, `canUse`'s function body byte-unchanged).
9. The idiom-mapping table (§Design Principles) is honoured by every surface
   choice (the review honour-check).

**Constraints.**
- **Zero new runtime dependency** (`runtime-and-deps.md`; D-S6-1/D-S6-P4): the
  MCP-stdio client is hand-rolled from `node:*` builtins. NO
  `@modelcontextprotocol/sdk`, NO `pi-mcp-extension`.
- **Brokers UNCHANGED** (D-S6-1, brief §(3)): no Python edits, no socket server;
  they are reused exactly as they ship (already `mcp.run(transport="stdio")`).
- **Credential never in the extension heap** (D-S6-3/D-S6-P2): the child obtains
  its credential by inheritance/self-fetch; the extension passes NAMES, never
  reads VALUES.
- **G-2 single-holder preserved** (brief §(1)): the concrete tools are reachable
  ONLY by the sole-holder role; deny-by-default everywhere else, enforced by the
  SAME `canUse` + `tool_call` block hook that gates every other tool.
- **E-1 arg-policy DEFERRED to S7** (D-S6-5): S6 does coarse reachability +
  credential isolation only; the broker's Python-side `_run_git` invariant is
  the authoritative hook-bypass enforcement in the interim.
- **Open-Q1 NOT reopened** (D-S6-2): no `runRpcMode`, no
  `decisions/pi-replatform-open-q1.md` amendment, no process-isolation
  machinery. (Confirmed this plan introduces none — spawn-per-call is ordinary
  in-process `child_process`, NOT the `pi --mode rpc` boundary Open-Q1 governs.)
- **Per L-C36:** all file shapes + the pi SDK tool/spawn/cancellation surface
  were read directly this session (§Link).

## Trace

### MANDATORY verification items (per the brief's "hands-on verification" list) — RESULTS

| # | Item | Result (primary-source) |
|---|---|---|
| 1 | Broker-child lifecycle / AbortSignal propagation | **CONFIRMED.** `execute(toolCallId, params, signal, onUpdate, ctx)` — `signal` (param 3) is an `AbortSignal` (pi.dev/docs/extensions Quick Start, verbatim; corroborated by `delegate.ts` L173-179 `_signal: AbortSignal`). `node:child_process` is available in extensions ("Node.js built-ins are also available"). So the child can be spawned in `execute` and killed via `signal.addEventListener("abort", () => child.kill())` + a `finally`. Chosen shape: spawn-per-call (D-S6-P3). |
| 2 | Exact env-passthrough-by-name spawn pattern | **CONFIRMED by reading broker source. git needs NONE** (`git/mcp_server.py` reads no token; push creds ambient). **pm needs only the NAME** `GITHUB_TOKEN`/`GITLAB_TOKEN` (`platform.py` L110-122 `get_token` → `os.environ.get(env_var)`, read inside the child). So the pm spawn inherits `process.env` (or copies just those two NAMES) and the child reads its own `os.environ`; the extension never reads the value. This is largely a non-issue for git and a by-name-only issue for pm (D-S6-P2). |
| 3 | glob-to-concrete-tool mapping for `canUse` | **`roleTable.ts` needs a DATA-ONLY change (operator-converged, D-S6-1b).** `canUse` (L248-260) is EXACT `.includes(toolName)`; it does NOT glob-match. The table holds `"gleipnir-git_*"` (L105) / `"gleipnir-pm_*"` (L109) as inert literals, so `canUse("git-ops","gleipnir-git_commit_changes")` is `false` today. **Resolution: register the 4 concrete names per broker as literal DATA ROWS** (git names in `git-ops.brokerTools`, pm names in `project-mgr.customTools`), replacing the single glob entry, and leave `canUse`'s body BYTE-IDENTICAL. This is the LOWER-BLAST-RADIUS shape — the ORIGINAL plan's `canUse` glob-matcher was REJECTED at spec-review (it touches the shared enforcement choke-point on an untouchable-list module, D-S4-6) and the operator converged on the data-only alternative. `delegate.ts::resolveChildTools` (L99-105) already documents that `brokerTools` is intentionally NOT projected into a child's `tools` — "the broker reach mechanism is separate (S6)" — so the reach path is the tool REGISTRATION here, not a `delegate` projection change. |
| 4 | Mock/real stdio-broker test harness under `--network=none` | **Python NOT present in the pi image → use a MOCK stdio broker.** `[profile.pi]` (`profiles.toml` L80-85) image is `Containerfile.pi` = `node:22-slim` (L45) — a Node-only Debian slim base; NO `python`/`python3` installed (only the six `@earendil-works/pi-*` + typebox + typescript npm pins). So a REAL `python -m gleipnir.broker...` subprocess CANNOT be spawned in the pi sandbox. Tests use a MOCK stdio broker: a tiny Node script speaking the minimal MCP subset (`initialize` reply + `tools/call` echo), spawned via `node`. This proves the client/relay/credential-isolation logic offline; the live real-Python round-trip is the same inherited sandbox residual as S3/S5. See `## Test-harness constraint`. |

### Hand-rolled feasibility (D-S6-P4 — the CENTRAL TENSION, resolved)

**The hand-rolled minimal MCP-over-stdio client IS feasible — the premise
holds.** Verified:
- The brokers are `FastMCP(...).run(transport="stdio")` (git `mcp_server.py`
  L48/L507-508; pm L27/L147-148). FastMCP-over-stdio speaks the standard MCP
  JSON-RPC 2.0 framing on stdin/stdout: a client sends an `initialize` request,
  receives the server capabilities, sends `notifications/initialized`, then
  sends `tools/call` requests and reads `result`/`error` responses. This is a
  BOUNDED, well-specified subset.
- Our surface is FIXED and tiny: 4 tools per broker, each a single request/
  response. We do NOT need pagination, `tools/list` (we hard-code the 4 names),
  reconnection, health-checks, `list_changed`, SSE, or streamable-HTTP — the
  corners a general client (`pi-mcp-extension`) must cover. We need only
  `initialize` + one `tools/call` per invocation.
- The transport is line/`Content-Length`-framed JSON over a child's
  stdin/stdout — `node:child_process.spawn` + a small newline/length-delimited
  reader. No third-party code. (`node:crypto` is NOT needed here; this is not
  the HMAC-marker slice.)
- **Conclusion:** hand-rolled is feasible and honours the basis of the
  operator's Approach-A convergence (zero third-party dep). NO escalation; NO
  `## BLOCKING` section. **The exact MCP JSON-RPC wire subset (method names,
  the `initialize` params/`protocolVersion`, whether FastMCP-stdio requires the
  `notifications/initialized` notification before `tools/call`) is a
  correctness detail the `test` stage MUST pin against the mock broker AND — as
  a one-time confirmation — against a REAL broker run under the `broker` profile
  (which HAS Python + mcp), see §Link item and §Open Items.** This is a
  bounded correctness task, not a design tradeoff.

### Artifacts and where they live (source of truth)

Behaviour source of truth is the two UNCHANGED Python brokers (the 4-tool
surface + the credential model); the MCP wire contract is the standard MCP
JSON-RPC 2.0 stdio subset; TS surface idiom source of truth is the idiom-mapping
table (§Design Principles) + existing pi-package modules.

| TS artifact | Status | Derives from / relays to | Responsibility (SRP) |
|---|---|---|---|
| `pi-package/src/broker/mcpStdioClient.ts` | **NEW** | standard MCP JSON-RPC stdio subset; `node:child_process`/`node:*` | The GENERIC transport: spawn a child per a spawn spec, `initialize` + one `tools/call`, frame/parse JSON-RPC, propagate `AbortSignal`, return the structured result or a structured error. Knows NOTHING about which broker, which tool, or any credential. One reason to change: the MCP-stdio wire/transport. |
| `pi-package/src/broker/gitBroker.ts` | **NEW** | git `mcp_server.py` 4-tool surface (relayed UNCHANGED) | Broker-SPECIFIC registration: define the 4 `gleipnir-git_<tool>` custom tools + their parameter schemas + the git spawn spec (`python -m gleipnir.broker.git.mcp_server`, NO credential passthrough), delegating the actual relay to `mcpStdioClient`. One reason to change: the git broker's tool surface. |
| `pi-package/src/broker/pmBroker.ts` | **NEW** | pm `mcp_server.py` 4-tool surface (relayed UNCHANGED) | Broker-SPECIFIC registration: the 4 `gleipnir-pm_<tool>` custom tools + schemas + the pm spawn spec (`python -m gleipnir.broker.pm.mcp_server`, pass `GITHUB_TOKEN`/`GITLAB_TOKEN` BY NAME only), delegating the relay to `mcpStdioClient`. One reason to change: the pm broker's tool surface. |
| `pi-package/src/broker/index.ts` (or fold into the two above) | **NEW (thin)** | — | The extension entrypoint(s): a default `ExtensionAPI` factory that `pi.registerTool`s the broker tools. May be one file per broker or a shared entry; the `test`/`code` stage picks per the SRP. |
| `pi-package/src/roleTable.ts` | **EDIT (DATA-only)** | — | Replace the single inert glob entry per broker with the 4 concrete literal tool names (git names in `git-ops.brokerTools`, pm names in `project-mgr.customTools`), resolved by `canUse`'s CURRENT exact-match `.includes()` (D-S6-1b, operator-converged). The `canUse` function body, `unionAllowSet`, the partition STRUCTURE, and the freeze logic are BYTE-UNCHANGED — this is a pure data-diff. |
| `pi-package/test/mcpStdioClient.test.ts` | **NEW** | mock stdio broker | Client transport unit tests: `initialize`+`tools/call` round-trip against the mock; abort kills the child; malformed/served-error handling; NO secret in any payload. |
| `pi-package/test/broker.test.ts` | **NEW** | mock stdio broker + roleTable | Broker-tool + reachability tests: the concrete tools register; `canUse` exact-match on the concrete DATA rows (sole-holder true, others false — the G-2 proof) + `canUse` body byte-identical (pure data-diff); relay passes structured params not argv; credential-non-leak with a sentinel token. |
| `pi-package/test/fixtures/mock-broker.mjs` (or `.ts`) | **NEW** | — | The MOCK stdio broker: a tiny Node script that reads MCP JSON-RPC on stdin, replies to `initialize`, echoes `tools/call` params (and can be told to emit an error / a payload embedding a sentinel to prove non-leak). Single source; reused by both test files. |

### Integrations map

- **`mcpStdioClient.ts` → `node:child_process` + `node:*` only.** Imports
  `spawn` (or `execFile`) from `node:child_process`; no pi runtime, no
  `roleTable`, no broker-specific knowledge. Pure transport. (It MAY import a
  `type` from `@earendil-works/pi-coding-agent` for the `AbortSignal`-carrying
  signature, compile-time only — but `AbortSignal` is a Node/DOM global, so even
  that is optional.)
- **`gitBroker.ts` / `pmBroker.ts` → `mcpStdioClient.ts` + pi runtime.** Each
  imports the client + `ExtensionAPI` (type) + `Type` from `typebox` (the
  `parameters` schema idiom, exactly as `delegate.ts` L81/L169). Each calls
  `pi.registerTool({ name: "gleipnir-git_<tool>", ..., async execute(id,
  params, signal, onUpdate, ctx) { return relay(...) } })`. The pm broker's
  spawn spec names `GITHUB_TOKEN`/`GITLAB_TOKEN`; the git broker's names
  nothing credential-bearing.
- **`roleTable.ts` → DATA-only change.** No new import, no code change: the 4
  concrete names per broker replace the single glob entry in the existing
  partitions, resolved by the unchanged exact-match `canUse`. The `canUse`
  function body, `unionAllowSet`, the partition structure, and the freeze logic
  are byte-unchanged. The `GIT_BROKER_TOOL`/`PM_BROKER_TOOL` glob constants
  (L105/L109) are removed or repointed to the concrete-name arrays — the code
  stage picks the cleanest mechanical shape (e.g. `GIT_BROKER_TOOLS: readonly
  string[]` = the 4 names), keeping the single-source-of-truth DRY property S2's
  constants had.
- **Extension registration → `pi-package/package.json` `pi.extensions` +
  `pi-package/.pi/settings.json` `extensions`.** The new broker extension
  entrypoint(s) are added to these two declarative arrays (additive), exactly
  as S5 added `enginePersistence.ts`. **[SCOPE FLAG]** these are
  enforcement-adjacent config (they select which extensions load) → the
  hardened review path (already applies, this plan touches `src/**`) verifies
  the diff adds ONLY the broker entry and changes no other extension/permission.
- **NO integration** with the Python brokers (unchanged), with
  `enforcement.ts`/`activeRole.ts`/`depth.ts` (the reach path rides on the
  EXISTING `tool_call` hook + `canUse` — a broker tool call from a non-holder
  role is denied by the SAME hook that denies any other out-of-allow-set tool),
  with `delegate.ts` (broker tools are NOT projected into child `tools` — see
  §Trace item 3), or with the engine/`verify`/`enginePersistence` modules.
- **NO `runRpcMode`, NO `.pi/mcp.json`, NO process-isolation machinery**
  (D-S6-2 closed; confirms this plan does not accidentally reopen Open-Q1).

### Edge cases (pinned)

- **Broker child fails to spawn** (e.g. `python` not found — the exact
  in-sandbox reality): the client returns a STRUCTURED error result, never
  throws unhandled; the tool result surfaces the failure to the calling role.
  (Mirrors the brokers' own never-raise posture.)
- **Broker child exits non-zero / writes malformed JSON**: structured error,
  no crash.
- **`AbortSignal` fires mid-call**: the child is killed (`SIGTERM`); the
  `execute` resolves/rejects promptly; no orphaned subprocess (verified by the
  abort test + a `finally` kill).
- **A commit MESSAGE legitimately contains `--no-verify`**: the relay passes it
  as the `message` PARAM value (structured), and the broker's `_run_git`
  already skips the value following `-m`/`--message` (git `mcp_server.py`
  L86-124 `_rejects_hook_bypass` skips message/file values) — so the message
  text is tolerated and the hook-bypass screen still fires on actual flag
  positions. S6 must NOT re-implement this screen (D-S6-5); it must only ensure
  it passes params, not argv.
- **Credential-bearing error**: an error from the pm broker must not echo the
  token; the broker already returns redacted structured errors, and the client
  relay must not add the child's env to any surfaced payload (tested with a
  sentinel token).
- **A non-holder role names a broker tool**: `canUse` exact-match returns false
  for that role (the concrete name is not in that role's partitions) → the
  `tool_call` block hook denies (deny-by-default; the G-2 proof).
- **Concurrent broker calls**: spawn-per-call means each call gets its own
  child + its own stdio pipe; no shared-pipe interleaving to reason about
  (a reason D-S6-P3 chose spawn-per-call over a pooled long-lived child).

## Test-harness constraint (Python-in-sandbox finding — flagged, NOT a plan blocker)

**Finding (verified):** the `[profile.pi]` sandbox image is `Containerfile.pi`,
built `FROM docker.io/library/node:22-slim@sha256:...` (Containerfile.pi L45).
It installs ONLY npm packages (`@earendil-works/pi-*`, `typebox`, `typescript`);
`node:22-slim` is a Debian-slim base with Node but **NO Python interpreter**.
The `[profile.broker]` image (`Containerfile.broker`, `python:3.12-slim` + `mcp`
+ `git`) HAS Python and the MCP SDK, but the pi TS tests run under
`[profile.pi]`, not `[profile.broker]`, and the two images are distinct
(digest-pinned).

**Consequence:** a pi-package test CANNOT spawn a REAL
`python -m gleipnir.broker.git.mcp_server` subprocess inside the pi sandbox —
there is no `python` on PATH. (This is a LOCAL-process-spawn limitation from the
image contents, NOT the `--network=none` limitation the brief hypothesised; the
brief correctly asked to check the image, and the check FAILS for Python.)

**Handling (no operator escalation needed):** the transport/relay/credential-
isolation logic is proven with a **MOCK stdio broker** —
`pi-package/test/fixtures/mock-broker.mjs`, a tiny Node script (Node IS present)
that speaks the minimal MCP JSON-RPC subset: reply to `initialize`, echo
`tools/call` params, and (on request) emit an error or a payload embedding a
sentinel token to prove non-leak. This proves the client is a correct MCP-stdio
client, that the relay passes structured params, that abort kills the child, and
that no secret leaks — all offline, all under `--profile pi --network=none`.

**The one thing the mock does NOT prove** is byte-level wire compatibility with
FastMCP's REAL `initialize`/`tools/call` framing. That is closed by a **one-time
cross-profile confirmation done in PURE PYTHON** (Correction 2, resolution (a);
see AC-WIRE-1): the `test` stage runs a small **Python** script under
`[profile.broker]` that speaks raw JSON-RPC-over-stdio DIRECTLY to a real
`python -m gleipnir.broker.git.mcp_server` subprocess (both Python, same
`python:3.12-slim` image) and records the exact wire subset. **It does NOT
invoke the TS client** — `[profile.broker]`'s image (`Containerfile.broker`) is
Python-only, with NO Node/TypeScript runtime, so the TS `mcpStdioClient.ts`
cannot run there. So the split is: the REAL server's wire FORMAT is proven in
Python under `[profile.broker]`; the TS client's CONFORMANCE to that format is
proven against the mock under `[profile.pi]`. This is honestly weaker than
"run the TS client against the real broker" (not executable under either
Node-XOR-Python image boundary), but it is actually executable and closes the
gap spec-review identified. It mirrors the S3/S5 residual: a sandbox-image
boundary, not an S6 wiring defect.

**[SCOPE FLAG — possible additive Tier-3 config, for the orchestrator/operator,
NOT this plan]:** if the cross-profile real-Python confirmation is wired as a
standing test (not a one-time manual check), it may need a small
`profiles.toml` addition or a `[profile.broker]` test-list entry. `profiles.toml`
is Tier-3 POLICY (`.gleipnir/sandbox/**`, always-hardened) — I CANNOT write it.
The plan names this as an §Open Item for the operator; the default assumption is
a one-time confirmation that needs no standing profile change.

## Link (what was validated before building)

Validated directly this session (read in full / fetched from primary source —
L-C36):
- **Both Python brokers read in full:** `src/gleipnir/broker/git/mcp_server.py`
  (508 L — 4 tools `git_status`/`git_diff`/`commit_changes`/`push_current_branch`;
  `_run_git` hook-bypass screen L100-161; `mcp.run(transport="stdio")` L507-508;
  git push creds ambient, NO token env-read) and
  `src/gleipnir/broker/pm/mcp_server.py` (148 L — 4 tools
  `issue_{create,update,comment,close}`; `mcp.run(transport="stdio")` L147-148).
- **pm credential model read in full:** `src/gleipnir/broker/pm/platform.py`
  L106-127 — `_TOKEN_ENV_VARS = {gitlab: "GITLAB_TOKEN", github: "GITHUB_TOKEN"}`;
  `get_token` → `os.environ.get(env_var)`, read INSIDE the broker child. Confirms
  D-S6-P2: pm needs the NAME passed through; git needs nothing.
- **roleTable read in full:** `pi-package/src/roleTable.ts` (261 L) —
  `GIT_BROKER_TOOL = "gleipnir-git_*"` (L105), `PM_BROKER_TOOL = "gleipnir-pm_*"`
  (L109); `canUse` L248-260 EXACT `.includes` (no glob) — grounds D-S6-1b: the
  concrete names resolve under this UNCHANGED exact-match; `git-ops.brokerTools
  = [GIT_BROKER_TOOL]` (L185, the sole non-empty `brokerTools`, AC-17);
  `project-mgr.customTools = [PM_BROKER_TOOL]` (L195). The 4 concrete git names
  (`git_status`/`git_diff`/`commit_changes`/`push_current_branch`) and 4 pm
  names (`issue_{create,update,comment,close}`) confirmed from the broker
  sources.
- **pi extension idioms read in full:** `pi-package/src/delegate.ts` (255 L —
  `pi.registerTool`/`buildDelegateTool` shape; `execute(_toolCallId, params,
  _signal: AbortSignal, _onUpdate, _ctx)` L173-179; `Type.Object` params;
  `resolveChildTools` L99-105 explicitly NOT projecting `brokerTools`, naming S6
  as the separate reach mechanism), `pi-package/src/enforcement.ts` (90 L — the
  `tool_call` block hook + `canUse` gate every tool passes; deny-by-default),
  `pi-package/src/activeRole.ts` (73 L — the role stack the hook reads).
- **pi test-harness + wiring read:** `pi-package/package.json` (`pi.extensions`
  array L11-15 currently `enforcement.ts`/`delegate.ts`/`enginePersistence.ts`;
  test script `node --experimental-strip-types --test`), `[profile.pi]` in
  `.gleipnir/sandbox/profiles.toml` (L80-85 — test argv lists the pi test files;
  image digest-pinned).
- **pi SDK surface CONFIRMED from primary source:** `pi.dev/docs/latest/sdk`
  (fetched — `defineTool`/`createAgentSession`/`customTools`; `runRpcMode`
  exists but NOT used) and `pi.dev/docs/latest/extensions` (fetched —
  `pi.registerTool({name,label,description,parameters,execute})`;
  `execute(toolCallId, params, signal, onUpdate, ctx)` with `signal: AbortSignal`
  verbatim in Quick Start; "Node.js built-ins are also available"; "Remote
  Execution"/`createBashTool` spawn-hook + `pi.exec(command,args,options?)` as
  first-party subprocess primitives; npm deps possible but require
  `dependencies` for distributed packages — the trust-surface cost Approach A
  avoids).
- **Sandbox image contents CONFIRMED:** `Containerfile.pi` (67 L — `node:22-slim`,
  npm pins ONLY, NO Python — the test-harness finding) vs `Containerfile.broker`
  (33 L — `python:3.12-slim` + `git` + `mcp>=1.0,<2` — where a real-Python
  round-trip CAN run).

## Assemble (intended build order)

**Discipline (L-C30): interface stub BEFORE tests, real bodies AFTER tests.**
The pi harness collects at import time, so a test importing a not-yet-existing
module fails at collection. Each new module lands as a typed interface stub
first (real exported signatures, bodies `throw new Error("not implemented")`),
so `test/*.test.ts` imports resolve at collection; then tests (Red); then real
bodies (Green). The `roleTable.ts` change is a DATA-only edit (the 4 concrete
names per broker replace the inert glob entry) applied in the real-body phase
alongside its test; `canUse`'s function body is byte-unchanged.

Order:

1. **Mock stdio broker fixture.**
   - **1a `pi-package/test/fixtures/mock-broker.mjs`** — the tiny Node MCP-stdio
     mock: read JSON-RPC on stdin, reply to `initialize`, echo `tools/call`
     params; support env-driven modes (emit-error; embed a sentinel token in a
     result to prove non-leak). This is a TEST fixture (Node script), authored
     first because both test files spawn it. (Not an interface stub — it is real
     from the start, like S5's golden fixtures.)

2. **Client + broker interface stubs.**
   - **2a `broker/mcpStdioClient.ts` stub** — export the client function
     signature (e.g. `relayToolCall(spec, toolName, params, signal):
     Promise<StructuredResult>`) + the spawn-spec type; body throws. Makes
     `mcpStdioClient.test.ts` import resolve.
   - **2b `broker/gitBroker.ts` + `broker/pmBroker.ts` stubs** — export the
     `ExtensionAPI` factory + the tool-name constants (`GIT_BROKER_TOOLS`,
     `PM_BROKER_TOOLS` — the concrete 4-name arrays) + the spawn specs; bodies
     throw / register no-op stubs. Makes `broker.test.ts` import resolve.

3. **Author the tests (Red — test stage arbiter).**
   - **3a `test/mcpStdioClient.test.ts`** — round-trip against `mock-broker.mjs`
     (`initialize`+`tools/call` returns the echoed params); abort kills the
     child (no orphan); spawn-failure → structured error; malformed-child-JSON →
     structured error; a result carrying a sentinel token is returned intact but
     the client adds NO env to any payload.
   - **3b `test/broker.test.ts`** — the concrete tool names register; `canUse`
     exact-match on the concrete DATA rows:
     `canUse("git-ops","gleipnir-git_commit_changes")===true`,
     `canUse("project-mgr","gleipnir-pm_issue_create")===true`, and
     `===false` for every other role (the G-2 reachability proof, mirroring
     AC-17 extended to concrete names); the `canUse` function body is asserted
     byte-identical before/after (a pure data-diff); relay passes structured
     params (a
     `message` containing `--no-verify` is passed as the value, not as argv);
     credential-non-leak with the sentinel token (no secret substring in any
     relayed result/error; the extension never dereferences the token value).
   - **3c (test-stage, cross-profile) real-Python wire confirmation — a PURE
     PYTHON protocol-level check, NOT a TS-client invocation** (Correction 2,
     resolution (a) — see §Test-harness constraint). `[profile.broker]`'s image
     (`Containerfile.broker`) is `python:3.12-slim` with NO Node/TypeScript
     runtime — so the TS `mcpStdioClient.ts` CANNOT run there. Instead: a small
     **Python** script under `[profile.broker]` speaks raw JSON-RPC-over-stdio
     directly to `python -m gleipnir.broker.git.mcp_server` (both Python, same
     image), doing one `initialize`+`git_status` round-trip, and RECORDS the
     exact wire subset the real FastMCP-stdio server requires (method names, the
     `initialize` `protocolVersion`, whether `notifications/initialized` is
     required before `tools/call`, the response framing). This proves the WIRE
     FORMAT the hand-rolled TS client must target; the TS client's correctness
     against that format is proven separately by the mock-broker suite (3a)
     under `[profile.pi]`. This is honestly weaker than "run the TS client
     against the real broker" (which is not executable under either image
     boundary), but it is actually executable as specified and closes the gap
     spec-review identified. See §Open Items for standing-test-vs-one-time.

4. **Real bodies + DATA edit (Green — code stage), bounded by the tests.**
   - **4a `broker/mcpStdioClient.ts`** — implement the hand-rolled JSON-RPC:
     `spawn(command, args, { env, stdio: ["pipe","pipe","pipe"] })`; write the
     `initialize` request, read+parse the response (length/newline-framed JSON),
     send `notifications/initialized` if the real-wire confirmation (3c) shows
     it is required, write the `tools/call` request, read the `result`/`error`,
     resolve the structured result; wire `signal` → `child.kill()`; kill the
     child in a `finally`; structured-error on spawn/parse/exit failure.
   - **4b `broker/gitBroker.ts` / `broker/pmBroker.ts`** — implement the
     `registerTool` calls for the 4+4 concrete tools with `Type.Object` param
     schemas mirroring the Python tool signatures (git: `repo_dir`; `git_diff`
     also `staged`/`target`/`file`; `commit_changes` `message`/`files`;
     `push_current_branch` `repo_dir`; pm: `issue_id`/`title`/`body`/`state` per
     tool), each `execute` calling `relayToolCall` with the right spawn spec.
     git spec passes NO credential env; pm spec inherits `process.env` (or copies
     only the two token NAMES) WITHOUT the extension reading the value.
   - **4c `roleTable.ts` (DATA-only, D-S6-1b)** — replace the single inert glob
     entry per broker with the 4 concrete literal names: `git-ops.brokerTools`
     gains `gleipnir-git_git_status`, `gleipnir-git_git_diff`,
     `gleipnir-git_commit_changes`, `gleipnir-git_push_current_branch`;
     `project-mgr.customTools` gains `gleipnir-pm_issue_create`,
     `gleipnir-pm_issue_update`, `gleipnir-pm_issue_comment`,
     `gleipnir-pm_issue_close`. The `GIT_BROKER_TOOL`/`PM_BROKER_TOOL` glob
     constants are repointed to the concrete-name arrays (or replaced by
     `GIT_BROKER_TOOLS`/`PM_BROKER_TOOLS: readonly string[]`) to keep the DRY
     single-source S2 had. **The `canUse` function body, `unionAllowSet`, the
     partition structure, and the freeze logic are BYTE-UNCHANGED** — this is a
     pure data-diff resolved by the existing exact-match `.includes()`. NO code
     change to any matching path.

5. **Wire the extension (additive).** Add the broker extension entrypoint(s) to
   `pi-package/package.json`'s `pi.extensions` array and
   `pi-package/.pi/settings.json`'s `extensions` array — additive, exactly as S5
   added `enginePersistence.ts`. **[SCOPE FLAG]** these two files are
   enforcement-adjacent config → the hardened blast-radius pass verifies the diff
   adds ONLY the broker registration line(s) and changes no other extension
   entry, permission, or grant. Also add the new `test/*.test.ts` files to the
   `package.json` test script + `[profile.pi]` test argv — **[SCOPE FLAG]**
   `profiles.toml` is Tier-3 (`.gleipnir/sandbox/**`), operator-only; adding the
   pi test-file names to the `[profile.pi]` `test` argv is a Tier-3 edit the
   operator/orchestrator applies, NOT this plan or the code stage (named in
   §Open Items).

**Step order rationale.** Mock fixture first (both test files spawn it); client
+ broker stubs before tests (collection-time import resolution, L-C30); tests
before real bodies (test-first, the test is the arbiter); the real-Python wire
confirmation (3c) BEFORE the client real body (4a) so the exact wire subset is
pinned, not guessed; the DATA-only `roleTable.ts` concrete-name registration
(4c) with its test; extension wiring last (it consumes the finished tools).

## Stress-test (acceptance checks)

### Client transport (`test/mcpStdioClient.test.ts` ← mock broker)

- **AC-CLIENT-1:** `relayToolCall(spec, "git_status", {repo_dir:""}, signal)`
  against `mock-broker.mjs` performs `initialize`+`tools/call` and returns the
  echoed structured result.
- **AC-CLIENT-2 (abort):** aborting `signal` mid-call kills the child; the call
  resolves/rejects promptly; no orphaned process (assert the child PID is gone).
- **AC-CLIENT-3 (spawn failure):** a spec whose `command` does not exist →
  STRUCTURED error result, no unhandled throw.
- **AC-CLIENT-4 (malformed / server error):** the mock emits malformed JSON /
  an MCP `error` → the client returns a structured error, never crashes.
- **AC-CLIENT-5 (no env leak):** the client adds NO spawn `env` to any returned
  payload; a result the mock embeds with a sentinel token is returned intact,
  but the client constructs nothing containing the token.

### Broker tools + G-2 reachability (`test/broker.test.ts`)

- **AC-BROKER-1 (registration):** the git broker registers exactly
  `gleipnir-git_git_status`, `gleipnir-git_git_diff`,
  `gleipnir-git_commit_changes`, `gleipnir-git_push_current_branch`; the pm
  broker registers exactly `gleipnir-pm_issue_create`,
  `gleipnir-pm_issue_update`, `gleipnir-pm_issue_comment`,
  `gleipnir-pm_issue_close`. (Concrete-name spelling is pinned so the registered
  tool name equals the table DATA row exactly; the `gleipnir-<ns>_<tool>` join
  is an idiom-table row.)
- **AC-G2-1 (exact-match reachability, sole-holder):**
  `canUse("git-ops","gleipnir-git_commit_changes")===true`;
  `canUse("project-mgr","gleipnir-pm_issue_create")===true` — resolved by the
  UNCHANGED exact-match `.includes()` against the concrete DATA rows.
- **AC-G2-2 (deny-by-default, everyone else):** for EVERY role other than the
  sole-holder, `canUse(role, <git concrete>)===false` and
  `canUse(role, <pm concrete>)===false` (the extended AC-17 G-2 proof — exactly
  one role reaches each namespace, at the REACHABILITY layer).
- **AC-G2-3 (`canUse` code path byte-identical):** `git diff` shows the
  `canUse` function body, `unionAllowSet`, the partition STRUCTURE, and the
  freeze logic byte-unchanged; the ONLY `roleTable.ts` change is DATA — the 4
  concrete names per broker replacing the single inert glob entry (and the
  glob constant repointed to the concrete-name array). This is the strong,
  simple claim the operator-converged shape makes checkable: a pure data-diff,
  verifiable via `git diff` showing ZERO changes inside the `canUse` function
  itself.
- **AC-RELAY-1 (structured params, not argv):** a `commit_changes` call whose
  `message` param contains `--no-verify` relays the STRING as the `message`
  value; the relay never constructs a git argv; the broker's `_run_git`
  authoritative screen is untouched (this test proves S6 does not fork the
  hook-bypass invariant — D-S6-5).
- **AC-CRED-1 (git, no passthrough):** the git spawn spec passes NO
  credential-bearing env; the test asserts the spec's env carries no token key.
- **AC-CRED-2 (pm, by-name only):** the pm spawn spec inherits/names
  `GITHUB_TOKEN`/`GITLAB_TOKEN` but the extension code never reads the VALUE
  into an inspected local; with a sentinel token in the (inherited) env, no
  relayed result/error contains the sentinel substring (Pre-Mortem #1/#2 closed).

### Cross-profile real-Python wire confirmation (`[profile.broker]`, test stage)

- **AC-WIRE-1 (PURE-PYTHON protocol-level check — Correction 2, resolution
  (a)):** a small **Python** script under `[profile.broker]` speaks raw
  JSON-RPC-over-stdio DIRECTLY to a REAL `python -m gleipnir.broker.git.mcp_server`
  subprocess (both Python, same `python:3.12-slim` image — no Node needed) and
  completes one `initialize`+`git_status` round-trip, RECORDING the exact wire
  subset the FastMCP-stdio server requires (method names, `initialize`
  `protocolVersion`, whether `notifications/initialized` precedes `tools/call`,
  response framing). This proves the WIRE FORMAT is as the hand-rolled TS client
  targets; it does NOT invoke the TS client (which cannot run under the
  Node-less broker image). The TS client's conformance to that format is proven
  by the mock-broker suite (AC-CLIENT-1..5) under `[profile.pi]`.
  **Why not run the TS client against the real broker:** `Containerfile.broker`
  is Python-only (no Node/TS runtime) and `Containerfile.pi` is Node-only (no
  Python) — neither image can run BOTH the TS client and the real Python broker
  in one process tree, so the honest, executable scope is: real-server wire
  format proven in Python; client conformance proven against the mock in Node.
  (Resolution (b) — adding Node to `Containerfile.broker` — was NOT chosen: it
  is a genuinely new Tier-3 image change outside any roster grant, and it
  widens the broker image's trusted surface for a check the split (a) proof
  covers without it.) If AC-WIRE-1 is wired as a STANDING test it needs an
  operator-only `[profile.broker]` test-argv addition in `profiles.toml`
  (Tier-3); otherwise it is a one-time confirmation the test stage records — the
  operator's call, flagged in §Open Items.

### Cross-cutting ACs

- **AC-ROUTE:** `bin/gleipnir-sandbox --profile pi` runs
  `node --experimental-strip-types --test test/mcpStdioClient.test.ts
  test/broker.test.ts` green under `--network=none` (mock broker only; no
  Python needed for these two).
- **AC-NODEP:** no new entry in `pi-package/package.json`
  `dependencies`/`peerDependencies` — the client is `node:*`-only (D-S6-P4;
  the basis of the Approach-A convergence).
- **AC-NOTOUCH-PY:** `git diff --name-only` shows ZERO changes under
  `src/gleipnir/broker/**` (the Python brokers are reused UNCHANGED).
- **AC-NOTOUCH-ENG:** ZERO change to `enforcement.ts`, `activeRole.ts`,
  `depth.ts`, `delegate.ts`, the `engine/*` modules, `verify/*`, and
  `enginePersistence.ts`. The over-broad form checked-and-ruled-out: "the broker
  reach work quietly widened a role's allow-set, changed the `tool_call` hook, or
  altered the delegate projection."
- **AC-DATA-ONLY:** the `roleTable.ts` diff shows ONLY DATA changes — the 4
  concrete names per broker replacing the inert glob entry (and the glob
  constant repointed to the concrete-name array) — and ZERO change inside the
  `canUse` function body, `unionAllowSet`, the partition structure, or the
  freeze logic. The over-broad form checked-and-ruled-out: "the DATA edit
  widened a role's allow-set beyond the 8 concrete broker names, added a
  non-broker tool, or (the REJECTED original) altered the shared `canUse`
  matching code path." Checkable as a pure data-diff: `git diff` shows the
  `canUse` function byte-identical.
- **AC-PURITY:** `mcpStdioClient.ts` imports only `node:*` (no pi runtime, no
  `roleTable`, no broker-specific knowledge); the broker modules import the
  client + pi types; `roleTable.ts` gains no import. (grep the import blocks.)
- **AC-NO-RPC:** `git grep` shows NO `runRpcMode` / `--mode rpc` /
  `.pi/mcp.json` introduced (D-S6-2: Open-Q1 not reopened, no process-isolation
  machinery).
- **AC-IDIOM:** every surface deviation from the Python broker signatures / the
  MCP wire is a row in the idiom table (§Design Principles) — the honour-check
  rejects any un-tabled surface choice.

## Execution Workflow

For the implementing agents (test stage + code stage, both `gleipnir-code`):

1. **Read this plan + the cited source** (both `mcp_server.py` files, `platform.py`
   L106-127, `roleTable.ts` L100-260, `delegate.ts` L163-255, the pi SDK
   extensions doc `execute` signature). Do NOT re-derive the broker tool surface
   from prose — it is the 4+4 tools named in §Trace, relayed UNCHANGED.
2. **Build in the Assemble order.** Mock fixture (1) → client + broker stubs (2)
   → author tests (3, Red) → real-Python wire confirmation (3c) → real bodies +
   DATA-only concrete-name registration in `roleTable.ts` (4, Green) → extension
   wiring (5).
3. **Pin the wire subset against the REAL broker ONCE (3c) before writing the
   client body (4a).** The mock proves the logic; the real broker proves the
   bytes. If they disagree, fix the client to match FastMCP, never the mock to
   match a wrong client.
4. **Hand-rolled, zero-dependency (D-S6-P4).** Do NOT add
   `@modelcontextprotocol/sdk` or any npm dependency. If you believe the
   hand-rolled client is genuinely infeasible (not merely more work), STOP and
   escalate to the operator via the orchestrator — do NOT silently pull in a
   dependency (the convergence chose Approach A on the basis of zero third-party
   dep). Trace found it feasible; this is the guardrail if the code stage
   discovers otherwise.
5. **Credential never in the extension heap (D-S6-3/D-S6-P2).** git: pass no
   credential env. pm: inherit / name-only the two token vars; NEVER read
   `process.env.<TOKEN>` into a local you inspect, log, branch on, or forward as
   a literal. The child reads its own `os.environ`. A sentinel-token test proves
   no leak.
6. **Relay structured params, never argv (D-S6-5).** The broker's Python-side
   `_run_git` hook-bypass screen is authoritative and UNCHANGED; the reach
   mechanism must not re-implement, weaken, or bypass it. Pass MCP `tools/call`
   params objects only.
7. **Brokers UNCHANGED.** Any edit under `src/gleipnir/broker/**` is a boundary
   violation — STOP.
8. **`roleTable.ts` change is DATA-ONLY (D-S6-1b, operator-converged).**
   Register the 4 concrete broker names per broker as literal DATA rows (git in
   `git-ops.brokerTools`, pm in `project-mgr.customTools`); leave `canUse`'s
   function body BYTE-IDENTICAL — do NOT add glob-matching or any other logic to
   the shared matching code path (that was the REJECTED original; `roleTable.ts`
   is a D-S4-6 "ZERO edits" module and `canUse` is the shared enforcement
   choke-point). If you find yourself editing the `canUse` body, adding a role,
   widening an allow-set beyond the 8 concrete broker names, or changing a
   partition's structure, STOP — that is out of scope. The `git diff` must show
   the `canUse` function unchanged.
9. **No process isolation (D-S6-2).** Spawn-per-call `node:child_process` is
   in-process delegation; do NOT introduce `runRpcMode`, `pi --mode rpc`, or
   `.pi/mcp.json` — that would reopen Open-Q1, which the operator closed.
10. **Verdicts:** hardened path (this plan touches `src/**`) → two separate
    review passes (spec-conformance + blast-radius) + negative-check attestation
    (§Pipeline Routing).

## Pipeline Routing

**Full 8-stage HARDENED pipeline.** Touched-path set `P` =
`pi-package/src/broker/mcpStdioClient.ts`, `pi-package/src/broker/gitBroker.ts`,
`pi-package/src/broker/pmBroker.ts`, the broker extension entrypoint,
`pi-package/src/roleTable.ts` (additive), `pi-package/test/mcpStdioClient.test.ts`,
`pi-package/test/broker.test.ts`, `pi-package/test/fixtures/mock-broker.mjs`,
plus additive edits to `pi-package/package.json` + `pi-package/.pi/settings.json`.
(The `[profile.broker]` test-argv / `[profile.pi]` test-argv additions in
`.gleipnir/sandbox/profiles.toml` are Tier-3, operator-applied — NOT in this
plan's `P`; see §Open Items.)

- **Axis-1 (`X`) disqualifier hit:** `P` contains `pi-package/src/**` and
  `pi-package/test/**` — executable TypeScript (+ a `.mjs` Node fixture) with
  class/function/module structure. → NOT the prose/config light track; the
  **full 8-stage pipeline** (`brainstorm → plan → spec-review → test → code →
  quality → git → gate`), test arbiter present. (Same routing as S4/S5.)
- **Gate-1 case:** **(i) OOP/functional code** — full SOLID+DRY+SRP+Design
  Intent required (§Design Principles), each falsifiable.
- **Axis-2(a) `E`-set touch: NONE of the always-hardened enforcement PATHS.**
  No file in `P` is under `.gleipnir/agents/**`, `.gleipnir/plugins/**`,
  `.gleipnir/sandbox/**`, `.gleipnir/policy/**`, `.gleipnir/keys/**`, nor is it
  `stage-role-map.md`, `opencode.jsonc`/`**/opencode.json`, nor an enumerated
  repo-root file. **Note `pi-package/package.json` / `.pi/settings.json`:** the
  pi-package's own manifest/settings, NOT the repo-root `E`-set files; they ARE
  enforcement-adjacent (they select which extensions load), so the blast-radius
  pass verifies the diff adds ONLY the broker registration and changes no other
  extension/permission/grant. Because `P` already routes hardened via Axis-1
  (`src/**`), the whole plan is hardened.
- **Hardened obligations (discharged at spec-review/quality/git, not by me):**
  the test arbiter (client + broker + G-2 + credential ACs) + the SOLID/DRY
  dimension of the blast-radius pass + the honour-check (does the applied code
  honour the idiom-table Design Intent?). The specific negative-checks the
  blast-radius pass must run: **AC-NOTOUCH-PY** + **AC-NOTOUCH-ENG** +
  **AC-DATA-ONLY** (the over-broad forms "the broker work quietly changed the
  Python brokers, widened a role allow-set / the `tool_call` hook, altered the
  delegate projection, or edited the shared `canUse` matching code path"
  checked-and-ruled-out; the `canUse` function body is `git diff`
  byte-identical) + **AC-CRED-1/2** (the extension never dereferences a token
  value) + **AC-NO-RPC** (Open-Q1 not reopened).

## Design Principles (Gate 1 — case (i): OOP/functional code)

### Design Intent (falsifiable — the SRP boundaries + the idiom table are the anchors)

**The falsifiable Design Intent of this slice is: (1) the reach path is a
STRUCTURAL relay — the pi custom tools carry NO broker logic and NO credential
handling of their own; they translate a role's tool call into an MCP `tools/call`
on the UNCHANGED Python broker and return its result verbatim, such that the
broker's own invariants (`_run_git` hook-bypass screen; the token read from the
child's `os.environ`) remain the sole authorities; and (2) the three SRP
boundaries below are honoured exactly.**

Three named, specific SRP boundaries a reviewer can point to a violation of:

- **Boundary A — generic transport (`mcpStdioClient.ts`) vs broker-specific
  registration (`gitBroker.ts`/`pmBroker.ts`).** `mcpStdioClient.ts` owns the
  MCP-over-stdio JSON-RPC transport (spawn, `initialize`, `tools/call`, framing,
  abort, structured-error) and knows NOTHING about which broker, which tool, or
  any credential/env-var name; `gitBroker.ts`/`pmBroker.ts` own the
  broker-specific tool definitions + spawn specs and hold NO JSON-RPC framing of
  their own (they call the client). **Falsifier:** `mcpStdioClient.ts` names a
  concrete tool (`git_status`, `issue_create`) or an env-var
  (`GITHUB_TOKEN`); or a broker module inlines JSON-RPC framing / a raw
  `spawn`+parse instead of calling the client. (This is the SRP the brief's
  §(1) architecture sketch names: `mcpStdioClient.ts` shared, `gitBroker`/
  `pmBroker` specific.)
- **Boundary B — reach mechanism (this slice) vs credential holding (the broker
  child).** The pi extension holds NO credential value: git passes none (ambient
  creds reach only the git subprocess); pm passes only the env-var NAME by
  inheritance. The token's readable lifetime is confined to the broker child's
  `os.environ`. **Falsifier:** the extension reads `process.env.GITHUB_TOKEN`
  (or `GITLAB_TOKEN`) into a local it inspects/logs/branches-on/forwards-as-a-
  literal; or any relayed result/error contains the sentinel token. (This is
  D-S6-3/D-S6-P2 in code form; AC-CRED-1/2 are its proofs.)
- **Boundary C — coarse reachability (S6) vs argument-level policy (S7).** S6
  enforces only tool-PRESENCE reachability (the sole-holder role can call the
  broker tool; deny-by-default everyone else, via `canUse` + the `tool_call`
  hook) and relies on the broker's OWN Python-side `_run_git` invariant for
  hook-bypass safety; it adds NO pi-side per-arg/per-path bounds. **Falsifier:**
  the reach code inspects/screens `event.input` args for policy (e.g. a pi-side
  `--no-verify` screen), which is the S7 E-1 seam pulled forward; or the relay
  constructs an argv the broker's `_run_git` would then have to re-screen.
  (This is D-S6-5 in code form; AC-RELAY-1 is its proof.)

All three are falsifiable exactly as the anti-vacuity rule requires: a reviewer
can point to a concrete import/line/argv/env-read that violates the boundary.
(Further concrete falsifiers: a new npm dependency added — AC-NODEP; a change
under `src/gleipnir/broker/**` — AC-NOTOUCH-PY; a widened role allow-set or any
edit to the `canUse` function body — AC-DATA-ONLY; a `runRpcMode`/`.pi/mcp.json`
introduced — AC-NO-RPC.)

**Note on the `roleTable.ts` boundary (operator-converged, D-S6-1b —
supersedes the original plan-stage judgment).** S2 authored
`GIT_BROKER_TOOL`/`PM_BROKER_TOOL` as INERT glob placeholders with the explicit
intent that "no real `gleipnir-git_*` tool is registered/reachable yet (that is
S6)" (roleTable.ts L100-105). This S6 plan makes them reachable by a DATA-only
edit: the 4 concrete literal names per broker replace the single glob entry in
the existing partitions, resolved by the UNCHANGED exact-match `canUse`. **The
original plan proposed a `*`-suffix glob matcher inside `canUse`; spec-review
REJECTED it** — `roleTable.ts` is one of the five D-S4-6 "ZERO edits" modules
(a boundary reinforced by S5) and `canUse` is the shared enforcement
choke-point every role's every `tool_call` passes through; the S5 D-S5-P1
precedent is NOT analogous (it concerned files NOT on the untouchable list). The
operator converged on the lower-blast-radius DATA-only shape. The governing rule
is DATA-only + no-widening + `canUse` body byte-identical; the concrete-name
rows add reachability and remove no deny path (AC-DATA-ONLY / AC-G2-3 prove it —
a pure data-diff showing the `canUse` function unchanged).

### Idiom-mapping table (Python broker / MCP wire → TS surface — every deviation named)

| # | Source surface | TS surface | Rationale |
|---|---|---|---|
| 1 | git `mcp_server.py` 4 tools `git_status`/`git_diff`/`commit_changes`/`push_current_branch`; pm 4 tools `issue_{create,update,comment,close}` | pi custom tools `gleipnir-git_<tool>` / `gleipnir-pm_<tool>` (namespace-prefixed concrete names) | The `gleipnir-<ns>_` prefix (from S2's inert `gleipnir-<ns>_*` placeholder, roleTable.ts L105/L109) + the Python tool name verbatim as the suffix — 1:1 and auditable. The `_` join is pinned so the registered tool name EQUALS the concrete DATA row `roleTable.ts` now lists, resolved by the UNCHANGED exact-match `canUse` (D-S6-1b). |
| 2 | FastMCP-over-stdio server (`mcp.run(transport="stdio")`) | hand-rolled JSON-RPC-over-stdio CLIENT (`node:child_process.spawn` + framed JSON), `initialize` + `tools/call` subset only | Zero-dep (D-S6-P4, `runtime-and-deps.md`); the fixed 4-tool surface needs no general MCP client. The exact wire subset is pinned by the real-Python confirmation (AC-WIRE-1), not guessed. |
| 3 | Python tool params (e.g. `commit_changes(message, files, repo_dir)`) | `Type.Object({...})` typebox schema mirroring each Python signature (the `delegate.ts` L169 idiom) | pi custom tools declare params via typebox; the schema mirrors the Python arg names so the relay passes them straight through as `tools/call` params. |
| 4 | pm token read inside broker: `os.environ.get("GITHUB_TOKEN"/"GITLAB_TOKEN")` (`platform.py` L110-122) | pm spawn spec inherits `process.env` (or names only those two vars); the child reads its own env; the extension reads NO value | Credential isolation (D-S6-3/D-S6-P2); the token's readable lifetime is the child's `os.environ`, never the extension heap. |
| 5 | git push creds ambient (git credential helper / SSH agent) | git spawn spec passes NO credential env at all | git needs no passthrough (Trace item 2); the git subprocess reaches ambient creds directly, exactly as the broker already assumes. |
| 6 | broker never raises; returns structured `{success:false,error:...}` | client + tool `execute` return structured results/errors, never unhandled throw (`AgentToolResult` shape, `delegate.ts` `textResult` L142 precedent) | Mirrors the broker's never-raise posture; a spawn/parse/exit failure surfaces as a tool result, not a crash. |
| 7 | broker `_run_git` screens argv flag positions (Python-side) | reach mechanism passes structured `tools/call` params, NEVER argv; adds NO pi-side screen | D-S6-5 Boundary C: the Python-side invariant stays authoritative; S6 must not fork it (AC-RELAY-1). |
| 8 | `execute` cancellation | `signal` (execute param 3, `AbortSignal`) → `child.kill()` + `finally` kill | pi SDK exposes cancellation via the `AbortSignal` param (Trace item 1); spawn-per-call means one child per call to kill (D-S6-P3). |
| 9 | `canUse` exact `.includes` (roleTable.ts L248-260) — UNCHANGED | the inert single glob entry per broker is replaced by 4 concrete literal DATA rows in the existing partitions | D-S6-1b (operator-converged): resolve reachability by DATA registration, not by editing the shared `canUse` matching code path; `canUse` body byte-identical (AC-G2-3 / AC-DATA-ONLY). |

## Open Items (flagged for spec-review / operator, per delegation)

1. **[OPERATOR-DECIDED — D-S6-1b, closed]** `roleTable.ts` reachability is a
   DATA-only edit: register the 4 concrete broker names per broker as literal
   rows, `canUse` body byte-unchanged. The original `*`-suffix glob-matcher was
   REJECTED at spec-review (touches the shared `canUse` choke-point on a D-S4-6
   "ZERO edits" module) and the operator converged on this lower-blast-radius
   shape. No longer an open question — recorded here as closed for traceability;
   the code stage must keep the `canUse` function byte-identical (AC-G2-3 /
   AC-DATA-ONLY).
2. **[PLAN-STAGE JUDGMENT — D-S6-P2]** Credential env-passthrough: git = none;
   pm = by-name only. Confirm the "extension never dereferences the token value"
   rule is testable as specified (sentinel token, AC-CRED-2).
3. **[PLAN-STAGE JUDGMENT — D-S6-P3]** Spawn-per-call lifecycle + `signal`→kill.
   Confirm no requirement for a long-lived pooled child (the brokers are
   stateless per call).
4. **[PLAN-STAGE JUDGMENT — D-S6-P4]** Hand-rolled zero-dep client. Confirm the
   feasibility finding + the escalation guardrail (code stage must escalate, not
   silently add a dep, if it hits genuine infeasibility).
5. **[TEST-HARNESS / possible Tier-3 — operator]** The pi-profile image has no
   Python. The logic suite uses a mock stdio broker under `[profile.pi]`. The
   one-time REAL-Python wire confirmation (AC-WIRE-1) runs under
   `[profile.broker]`. **Decision for the operator:** is AC-WIRE-1 a STANDING
   test (needs a Tier-3 `.gleipnir/sandbox/profiles.toml` `[profile.broker]`
   test-argv addition — operator-only, I cannot write it) or a ONE-TIME
   confirmation the test stage records (no profile change)? Default assumption:
   one-time.
6. **[Tier-3 wiring — operator/orchestrator]** Adding the two new pi test files
   to `[profile.pi]`'s `test` argv in `profiles.toml` (Tier-3, `.gleipnir/
   sandbox/**`) is operator-applied, NOT this plan or the code stage. The
   `package.json`/`.pi/settings.json` extension-array + test-script additions
   ARE in the code stage's scope (Tier-0-adjacent pi-package config).
7. **[WIRE SUBSET — test stage, bounded correctness not a tradeoff]** The exact
   MCP `initialize` `protocolVersion`, whether FastMCP-stdio requires
   `notifications/initialized` before `tools/call`, and the response framing
   (newline vs `Content-Length`) — pinned by AC-WIRE-1 against the real broker,
   not guessed.

**No `## BLOCKING — needs operator convergence` section:** the hand-rolled
client premise held under Trace (D-S6-P4), so no infeasibility escalation is
required. The Python-in-sandbox finding is handled with a mock + a bounded
cross-profile confirmation, not a design tradeoff. Both are stated explicitly in
the final report.
