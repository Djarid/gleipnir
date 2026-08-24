# Plan: pi.dev primitive-proof slice (S1) — enforcement + delegation hands-on

> **Status: ATLAS plan (Tier-0, transient).** This is Part 2 of the pi.dev
> replatform delegation — the full ATLAS plan for the **first buildable slice
> (S1)** identified in `pi-dev-replatform-build-order.md`. It proves the two
> load-bearing CRUX mechanisms (CRUX 1: `tool_call`-block-hook enforcement;
> CRUX 2: `createAgentSession` delegation with a depth cap) hands-on for ONE
> simple role, on a minimal Pi package skeleton, **before** the rest of the
> roster is committed to this shape. It is handed to `gleipnir-code` next.
>
> **Pipeline routing:** this plan touches **new TypeScript source** (classes /
> functions) under a **new package directory** — it produces an executable
> artifact with object/function structure, so it is Gate-1 **case (i)**
> (OOP/functional → full SOLID+DRY+SRP+Design-Intent) and matches the *spirit*
> of the Axis-1 disqualifier set `X` (TS source files, `*.ts`). It is therefore
> **full-hardened-pipeline eligible — NOT a light/prose-only plan**, even though
> `X`'s current literals are opencode/Python-shaped (`stage-role-map.md`'s `X`
> lists `**/*.ts` explicitly, so this matches directly).

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Overall approach (inherited) | B: native TS re-expression, pi-only | A (Py-over-RPC), C (dual-target), D (phased) | Operator-converged in `pi-dev-replatform-brainstorm.md` (matrix B=416). Not reopened. |
| D2 | S1 delegation proof vehicle | In-process `createAgentSession` + `SessionManager.inMemory()` | `runRpcMode` subprocess | Proves CRUX 2 with the least infrastructure; the final in-process-vs-RPC isolation choice is Open-Q1, **[ASSUMPTION-1]** in the roadmap — NOT decided here |
| D3 | Enforcement mechanism | Gleipnir-owned role→capability table read in a `tool_call` block hook | Host permission-map (does not exist in pi) | CRUX 1: pi has no per-agent permission-map primitive; the shipped `permission-gate.ts` example is the exact pattern |
| D4 | Depth-cap storage (S1 scope) | In-extension module-scope counter, incremented on `delegate`, decremented on child dispose | `pi.appendEntry` session-persisted state | S1 proves the *mechanism* in-process; cross-restart persistence via `appendEntry` is an S3 concern, not needed to prove the cap refuses runaway nesting |
| D5 | Non-interactive gate in S1 | Demonstrate the shipped `ctx.hasUI` fail-closed branch as the *mechanism* only | Deciding the fail-closed-vs-sink *policy* | Open-Q2 is a POLICY decision reserved for the operator; S1 shows the mechanism works, does not pick the policy |
| D6 | Child-hook binding (the load-bearing unknown) | S1 **must empirically determine** whether a `createAgentSession` child inherits the parent extension's `tool_call` hook or needs explicit `bindExtensions(...)`, and encode the answer | Assuming either way | SDK docs say `bindExtensions` is needed after session *replacement*; freshly-*created* child behaviour is unverified and delegation enforcement depends on it |
| D7 | HMAC / engine scope in S1 | **Out of scope** — S1 proves enforcement + delegation primitives only | Bundling engine/attestation into S1 | Engine (S4) and attestation (S5) are separate steps; S1 is the primitive-proof foundation, kept minimal |

## Architect

- **Problem (one sentence):** Prove, hands-on and test-backed, that pi.dev's
  `tool_call` block hook can enforce a Gleipnir-owned role→capability table
  (CRUX 1) and that a Gleipnir `delegate` custom tool over `createAgentSession`
  can spawn a role-bounded child session with a working depth cap (CRUX 2) —
  before the full roster is committed to this shape.
- **User:** the Gleipnir maintainer (`gleipnir-code` builds it; the operator
  reviews it as the go/no-go evidence for steps S2–S9).
- **Measurable success criteria:**
  1. A tool call not in a role's allow-set is blocked with a `reason`; an
     allowed tool call passes — proven by an automated test.
  2. A `delegate` call creates a child session bounded to a role's tool set.
  3. A `delegate` call that would exceed the depth cap is refused.
  4. The child-hook binding question (D6) is answered with test evidence
     (child either inherits enforcement automatically, or the plan documents the
     explicit `bindExtensions` call that makes it so).
  5. The package loads as a valid Pi package (`pi -e ./…` or a resource-loader
     harness) with correct peer-deps declared and not bundled.
- **Constraints:**
  - Native TypeScript only (Approach B); no Python in this slice.
  - Depend on pi core packages via `peerDependencies: "*"` — do **not** bundle
    `@earendil-works/pi-coding-agent`, `@earendil-works/pi-ai`,
    `@earendil-works/pi-agent-core`, `@earendil-works/pi-tui`, `typebox`.
  - ONE simple role only (deny-by-default proof); the full 8-role roster is S2.
  - No engine, no HMAC, no broker, no bus in this slice (D7).
  - Do not decide the 4 open questions; where S1 touches them (D2, D5) it
    demonstrates a mechanism under a flagged assumption, it does not decide.

## Trace

**New artifacts and where they live** (all under a new package dir; nothing
here exists yet — all **to-be-created**):

| Artifact | Path (to-be-created) | Responsibility |
|---|---|---|
| Package manifest | `pi-package/package.json` | `name`, `keywords:["pi-package"]`, `pi.extensions`, `peerDependencies` (`"*"`), `devDependencies` (test runner, `typescript`) |
| TS config | `pi-package/tsconfig.json` | strict TS compile of the extension + tests |
| Role→capability table | `pi-package/src/roleTable.ts` | Pure data + a `canUse(role, toolName): boolean` lookup; ONE role (`gleipnir-code`-like) with a small allow-set; deny-by-default |
| Enforcement extension | `pi-package/src/enforcement.ts` | `export default function(pi: ExtensionAPI)`; registers the `tool_call` block hook that consults `roleTable` + active role; demonstrates `ctx.hasUI` fail-closed branch (D5) |
| Delegate tool | `pi-package/src/delegate.ts` | `pi.registerTool({ name:"delegate", … })` creating a bounded `createAgentSession` child; depth-cap counter (D4); returns child result |
| Depth cap | `pi-package/src/depth.ts` | Module-scope counter + `enter()/exit()` guard + cap constant; single responsibility (SRP) |
| Active-role state | `pi-package/src/activeRole.ts` | Holds the current role for the session (set at `session_start`/by delegate); the hook reads it |
| Tests | `pi-package/test/enforcement.test.ts`, `pi-package/test/delegate.test.ts` | The correctness arbiters (success criteria 1–4) |
| Package README | `pi-package/README.md` | What the slice proves + how to run |

**Integrations map:**
- `enforcement.ts` → `pi.on("tool_call", (event, ctx) => …)` → reads
  `activeRole` + `roleTable.canUse` → returns `{ block, reason }` | `undefined`.
- `delegate.ts` → `pi.registerTool` → on `execute`, checks `depth.enter()`,
  builds a child via `createAgentSession({ resourceLoader, sessionManager:
  SessionManager.inMemory(), tools: <role allow-set> })`, sets the child's
  active role, `await session.prompt(...)`, `session.dispose()`, `depth.exit()`.
- Child-session enforcement binding is the D6 experiment: test both "child
  inherits parent hook" and, if not, wire `resourceLoader` /
  `extensionFactories` so the child loads the same enforcement extension, and
  document which is required.

**Edge cases:**
- Tool call arrives before any active role is set → **fail closed** (block; a
  session with no role has an empty allow-set).
- `delegate` called at depth == cap → refuse with a clear `reason`; counter must
  decrement even if the child throws (use `try/finally`).
- `ctx.hasUI === false` on a would-prompt path → block by default (the shipped
  pattern) — S1 asserts this branch is reachable and blocks.
- Child session that itself calls `delegate` → depth increments transitively;
  the cap must catch nested delegation, not just first-level.
- Unknown `toolName` not in any allow-set → deny-by-default (blocked).
- Peer-dep import resolves at load time only if the host provides it → the test
  harness must run under a context where `@earendil-works/pi-coding-agent` is
  resolvable (documented in Execution Workflow).

## Link (validated before building)

- **CRUX-1 API shape — VALIDATED** against `examples/extensions/permission-gate.ts`
  (primary source, fetched this session): `pi.on("tool_call", async (event, ctx)
  => { if (event.toolName !== "bash") return undefined; … return { block: true,
  reason } })`; `ctx.hasUI` and `ctx.ui.select` confirmed. The block-hook and the
  non-interactive fallback are shipped, not inferred.
- **CRUX-2 API shape — VALIDATED** against `docs/sdk.md` + `examples/sdk/06-extensions.ts`
  + `dynamic-tools.ts`: `pi.registerTool({ name, label, description, parameters:
  Type.Object({…}), execute })`; `createAgentSession({ resourceLoader,
  sessionManager: SessionManager.inMemory(), tools, customTools, model })`;
  `session.prompt/.subscribe/.dispose`; `defineTool` + `customTools:[…]`.
- **Package manifest — VALIDATED** against `docs/packages`: `package.json` `pi`
  key, `keywords:["pi-package"]`, convention dirs, and the exact
  `peerDependencies "*"` list (do-not-bundle rule).
- **Depth-cap storage — VALIDATED** as available: `pi.appendEntry` (persisted)
  per `docs/extensions.md`; S1 uses in-process module state (D4), persistence
  deferred to S3.
- **NOT YET VALIDATED (the S1 experiment, D6):** whether a freshly-created child
  `createAgentSession` inherits the parent extension's `tool_call` hook. SDK
  notes only that `bindExtensions(...)` is required after session *replacement*
  (`newSession`/`switchSession`/`fork`), not creation. **S1's job is to settle
  this** — it is Link-listed as an open validation the slice itself closes, not
  a precondition. This is why S1 exists before S2–S9.
- **Oracle for later steps (not S1):** `src/gleipnir/engine/*` and
  `src/gleipnir/verify/marker.py` + `tests/fixtures/golden_marker*.json` are the
  correctness oracle for S4/S5 — confirmed present on disk this session, cited
  here only to bound S1 *out* of that scope (D7).

## Assemble (intended build order)

1. **Scaffold the package** — `pi-package/package.json` (peer-deps `"*"`,
   `keywords:["pi-package"]`, `pi.extensions:["./src/enforcement.ts"]`),
   `tsconfig.json` (strict), README stub. Verify it is a loadable Pi package
   shape before any logic.
2. **`roleTable.ts` + `activeRole.ts`** — the pure data + lookup and the
   session-scoped active-role holder. No pi imports yet in `roleTable` (pure);
   testable in isolation.
3. **`enforcement.ts`** — the `tool_call` block hook consuming (2). Include the
   `ctx.hasUI` fail-closed branch (D5). Deny-by-default for unset role / unknown
   tool.
4. **`enforcement.test.ts`** — success criteria 1 (block denied, allow allowed)
   + the unset-role and `!ctx.hasUI` edge cases. **Test-first for the hook logic
   where feasible** (the arbiter is the test).
5. **`depth.ts`** — module counter + `enter()/exit()` + cap; `try/finally`
   safety. Unit-test the cap in isolation.
6. **`delegate.ts`** — the `registerTool` delegate creating a bounded child;
   wires (5) and sets the child active role. Run the **D6 experiment here**:
   first test whether the child enforces the parent hook automatically; if not,
   wire the child `resourceLoader`/`extensionFactories` to load `enforcement.ts`
   and document that requirement.
7. **`delegate.test.ts`** — success criteria 2, 3, 4 (bounded child, cap
   refusal incl. nested, child-enforcement binding answered).
8. **README + a runnable proof harness** — document `pi -e ./…` (or an SDK
   `DefaultResourceLoader` + `createAgentSession` harness) so the operator can
   reproduce the proof; capture the D6 answer in the README as the go/no-go
   evidence for S2–S9.

## Stress-test (concrete acceptance criteria — the go/no-go for S2–S9)

A reviewer/`gleipnir-code` validates S1 against these checkable criteria (not
"it works"):

1. **AC-1 (deny):** a `tool_call` for a tool NOT in the active role's allow-set
   returns `{ block: true, reason }`; test asserts `block === true` and a
   non-empty `reason`.
2. **AC-2 (allow):** a `tool_call` for an allowed tool returns `undefined`
   (permitted); test asserts the tool executes.
3. **AC-3 (deny-by-default, unset role):** a `tool_call` with no active role set
   is blocked; test asserts block.
4. **AC-4 (non-interactive fail-closed):** on a path that would prompt, with
   `ctx.hasUI === false`, the hook blocks; test asserts block + reason mentions
   no-UI. (Mechanism only — Open-Q2 policy stays open.)
5. **AC-5 (bounded child):** a `delegate` call creates a child whose enabled
   tools equal the delegated role's allow-set; test asserts the child's tool set.
6. **AC-6 (depth cap, first level):** `delegate` at depth == cap is refused with
   a reason; test asserts refusal.
7. **AC-7 (depth cap, nested):** a child that calls `delegate` transitively
   increments depth and is caught by the cap; test asserts nested refusal.
8. **AC-8 (counter safety):** the depth counter returns to its prior value after
   a child throws (test forces a child error, asserts counter restored).
9. **AC-9 (child-hook binding, D6):** a test demonstrates the child session
   enforces the role table — EITHER inheriting the parent hook automatically OR
   via a documented `bindExtensions`/`resourceLoader` wiring; the README records
   which. **This is the load-bearing S1 finding.**
10. **AC-10 (package validity):** the package loads via the documented harness
    with peer-deps resolved and NOT bundled (assert `package.json` has the five
    peers under `peerDependencies` with `"*"` and none under `dependencies`).

## Execution Workflow

- **Delegated to:** `gleipnir-code` (test stage + code stage; Sonnet). The test
  is the arbiter (Axiom 1) — author `enforcement.test.ts` and `delegate.test.ts`
  to the AC list above before/as the implementation lands.
- **Runtime:** Node + TypeScript. Pi core packages are **peer** deps; the test
  harness must run where `@earendil-works/pi-coding-agent` and `typebox` resolve
  (either install them as devDeps for the test env ONLY, or run under a pi
  checkout). Document the chosen test-env resolution in the README — it must not
  turn a peer dep into a bundled dep in the shipped `package.json`.
- **The D6 experiment is mandatory and comes before declaring S1 done.** If the
  child does NOT inherit the parent `tool_call` hook automatically, the delegate
  must construct the child with a `resourceLoader`/`extensionFactories` that
  loads `enforcement.ts`, and AC-9's test must prove the child is enforced. A
  child that can call denied tools is an S1 FAILURE, not a caveat.
- **Do not expand scope:** no full roster (S2), no engine (S4), no HMAC (S5), no
  broker (S6). If S1 surfaces a *material* design decision (e.g. the child
  enforcement requires a delegation architecture that forces the in-process-vs-RPC
  choice, Open-Q1), STOP and route it back to the operator via the orchestrator —
  do not bake an answer into S1.
- **Sandbox:** build/test runs under the existing `bin/gleipnir-sandbox`
  (ephemeral container, `--network=none`, ro source) per current policy; the
  keep-vs-Gondolin choice (Open-Q1) does not block S1's build/test.
- **Handback:** S1's README + passing AC test suite are the evidence artifact
  the operator uses to greenlight S2. Report the D6 answer explicitly.

## Design Principles (Gate 1 — case (i): OOP/functional TS source)

`P` includes new `*.ts` source with function/module structure → `P ∩ X ≠ ∅`
with structure → **case (i)**, full analysis:

**SOLID analysis:**
- **Single Responsibility:** `roleTable.ts` = the capability data + lookup ONLY;
  `activeRole.ts` = current-role state ONLY; `enforcement.ts` = translate a
  `tool_call` into an allow/deny ONLY; `depth.ts` = the delegation depth
  counter/cap ONLY; `delegate.ts` = construct+bound+run a child session ONLY.
  Each has exactly one reason to change (the capability data, the state model,
  the hook contract, the cap value, the delegation API, respectively).
- **Open/Closed:** adding roles/tools in S2 extends `roleTable` data without
  modifying the hook logic in `enforcement.ts` (data-driven); the hook is closed
  to modification as the roster grows.
- **Liskov:** no subclassing in S1; the `execute` and hook callbacks conform to
  pi's `ExtensionAPI`/`ToolDefinition` contracts exactly (verified signatures) —
  a Gleipnir tool must be substitutable for any pi custom tool.
- **Interface Segregation:** `enforcement.ts` depends only on
  `canUse(role,tool)` + the active role, not on the whole table internals;
  `delegate.ts` depends only on `depth.enter/exit` + `createAgentSession`, not on
  the enforcement internals.
- **Dependency Inversion:** the hook consumes the role table via the narrow
  `canUse` function, not a concrete data structure, so the storage (in-memory in
  S1, possibly `.pi/*`-loaded in S2) can change without touching the hook.

**DRY analysis:** the allow-set is defined ONCE in `roleTable.ts` and consumed by
both `enforcement.ts` (to block) and `delegate.ts` (to bound the child's `tools`)
— no duplication of the capability list. The block-reason strings are the only
repeated literals; centralise them if reused. No reimplementation of pi
primitives — the shipped `permission-gate.ts` pattern is reused, not re-derived.

**Single Responsibility check (explicit per module):** stated above — one
responsibility each; if `delegate.ts` grows to also *decide* isolation
(in-process vs RPC), that is a second responsibility → split and escalate
(Open-Q1), do not fold it in.

**Design Intent (specific, falsifiable):** *S1 must prove that enforcement is a
property of Gleipnir's own code (the role table read in the block hook), such
that a delegated child session CANNOT call a tool outside its role's allow-set —
if AC-9 shows a child calling a denied tool, the slice has failed its core
purpose, regardless of the other ACs passing.* A reviewer can falsify this by
finding any path (top-level or via `delegate`) where a not-allowed `toolName`
reaches execution without a `{ block: true }`, or any child session whose
enforcement is assumed rather than test-demonstrated (AC-9).
