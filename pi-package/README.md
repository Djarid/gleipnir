# pi-package — S2 (full 8-role roster) slice

Status: **implemented and verified** — `bin/gleipnir-sandbox test --profile pi`
(28/28 pass, including a real end-to-end `createAgentSession` child and a real
nested-delegation depth-cap chain, see "D6 finding" and AC-13/14 below, plus
the D1 coarse-presence fix's own proof, AC-21) and `bin/gleipnir-sandbox lint
--profile pi` (clean). This package is the S2 slice of the pi.dev-native
re-expression of Gleipnir, per the full ATLAS plan
`.gleipnir/plans/pi-dev-replatform-s2.md` (which promotes the S1 one-role
proof-of-mechanism, `pi-dev-replatform-first-slice.md`, to the full roster).

**D1 correction applied (this session, `code` stage of the S2 plan).** A
prior interrupted session left `ROLE_ALLOW_SETS_RAW`'s `baseTools` missing the
scoped-but-real base tool for 5 roles (`edit` for `gleipnir-brainstorm`/
`gleipnir-plan`; `bash` for `gleipnir-code`/`quality-reviewer`/`git-ops`) —
a violation of the plan's coarse-presence rule ("present-but-scoped ⇒ in
`baseTools`, with the restriction recorded in `bounds`"). This session fixed
`roleTable.ts` in place, added `AC-21` (`test/roleTable.test.ts`) proving the
corrected presence/absence and that each affected role's `bounds` is
non-empty, and fixed the direct ripple this created in three existing negative
probes that had used `"bash"` as a cross-role deny probe — see "D1 ripple
fix" below.

## What this slice proves

1. **CRUX 1 — enforcement, full roster.** A `tool_call` block hook
   (`src/enforcement.ts`) reads a Gleipnir-owned role→capability table
   (`src/roleTable.ts`) and the current session's active role
   (`src/activeRole.ts`) to deny a not-allowed tool call and permit an
   allowed one, for all **8 roster roles**, each a typed
   `{ baseTools, customTools, brokerTools }` partition. Deny-by-default per
   role: unset role, unknown role, and any unlisted tool resolve to `false`
   (AC-16). **G-2 at the table level:** `git-ops` is the sole holder of a
   git-broker name; every other role's `brokerTools` is empty (AC-17). Base
   vocabulary is the real SDK `ToolName` union (`read | bash | edit | write |
   grep | find | ls`); the S1 `read_file`/`write_file` names are retired
   (AC-18). The table (and its nested partitions) is deep-frozen — it cannot
   be widened at runtime (AC-19).
2. **CRUX 2 — delegation, nested-reachable.** A `delegate` custom tool
   (`src/delegate.ts`) spins up a role-bounded child session via
   `createAgentSession`, guarded by a depth cap (`src/depth.ts`). S2 makes
   nested delegation actually reachable end-to-end: a child whose role
   declares `"delegate"` now RECEIVES the real `delegate` tool definition
   (projected from the table via `resolveChildCustomTools`, DRY), so it can
   re-invoke `delegate` — and the depth cap refuses that real nested
   re-invocation, restoring the counter afterward (AC-11..AC-14). A
   non-delegate child does not receive it (deny-by-default through the
   pass-through, AC-12). The primary session's role is seeded at
   `session_start` (`orchestrator`), guarded so a child's `session_start`
   cannot clobber a pushed child role (AC-15).
3. **D6 — the child-hook binding question.** See below. **Settled for the
   wiring-correctness question; one residual empirical gap remains, named
   explicitly.**

## How to reproduce

```sh
bin/gleipnir-sandbox test --profile pi   # node --test enforcement + delegate + roleTable tests
bin/gleipnir-sandbox lint --profile pi   # tsc --noEmit -p tsconfig.json
```

Both run inside the `gleipnir-sandbox-pi` container (`--network=none`,
repo mounted read-only), which pre-installs the five pi peer packages +
`typebox` + `typescript` at the filesystem-root `/node_modules` (see
`Containerfile.pi`) — `pi-package/node_modules` is deliberately absent; do
not add a local install. Confirmed reachable and live this session: 28/28
tests pass, lint is clean.

## Peer-dep resolution (AC-10)

`package.json` declares the five pi peers (`@earendil-works/pi-coding-agent`,
`@earendil-works/pi-agent-core`, `@earendil-works/pi-ai`,
`@earendil-works/pi-tui`, `typebox`) under `peerDependencies` with `"*"`, and
lists NONE of them under `dependencies` (there is no `dependencies` key at
all) — they are resolved by the sandbox's pre-installed `/node_modules`, never
bundled.

## D6 finding: **settled for the wiring-correctness question; one named residual gap**

**The question (plan Decision D6, AC-9):** does a freshly-created
`createAgentSession` child inherit the parent extension's `tool_call` hook
automatically, or does it need explicit `bindExtensions`/`resourceLoader`/
`extensionFactories` wiring?

**Prior session status (superseded):** an earlier delegation could not reach
`--profile pi` at all (a stale sandbox permission snapshot). That has since
been cleared by a session restart; `--profile pi` `test`/`lint` are now
confirmed live, and this delegation ran real code against the real
`@earendil-works/pi-coding-agent` package inside the sandbox.

**What was empirically determined this session, via direct introspection of
the real SDK (a temporary RECON probe run in-sandbox, findings distilled into
`delegate.test.ts`'s comments, raw dumps not kept in the committed suite):**

1. `session._extensionRunner.emitToolCall(event)` is **verbatim** the
   function the SDK's own `session._installAgentToolHooks()` wires to
   `agent.beforeToolCall` for every real, model-driven tool call:
   `runner.emitToolCall({ type: "tool_call", toolName: toolCall.name,
   toolCallId: toolCall.id, input: args })`. It is reachable directly (via
   the private, underscore-prefixed `_extensionRunner` field — not a
   documented public API) on any real session `createAgentSession` returns.
2. `emitToolCall`'s real body iterates `this.extensions` — i.e. **only** the
   extensions the child's *own* `resourceLoader` loaded — and for each,
   `ext.handlers.get("tool_call")`. **There is no "auto-inherit the parent's
   hook" code path in the SDK at all.** Enforcement dispatch is scoped
   entirely to whatever the child's own `resourceLoader.getExtensions()`
   produced.
3. Given (2), `delegate.ts`'s explicit `new DefaultResourceLoader({
   extensionFactories: [enforcementExtension] })` + `await
   resourceLoader.reload()` wiring — already in place before this session —
   is **not** a defensive "redundant but harmless" fallback as originally
   written; it is **the only mechanism** by which the child is enforced. A
   child built without it would have an empty `_extensionRunner.extensions`
   and every tool call would silently pass (`emitToolCall` returning
   `undefined` unconditionally).
4. `AgentSession` (the class every `createAgentSession`-returned `session` is
   an instance of) is a **named public export** of
   `@earendil-works/pi-coding-agent`, and `prompt` is an ordinary prototype
   method — confirmed patchable at the class level.

**The genuine end-to-end test this session added
(`test/delegate.test.ts`, `AC-9-E2E`):** calls `delegate.ts`'s real,
unmodified `execute` (captured via a `registerTool`-capturing shim, the same
capture pattern already used for `.on` elsewhere in this suite — not a mock
of `delegate.ts`'s logic). That real `execute` runs its real body — real
`DefaultResourceLoader` + `extensionFactories` wiring, real
`resourceLoader.reload()`, real `createAgentSession` — against the real
`@earendil-works/pi-coding-agent` package. The **only** stubbed call is
`AgentSession.prototype.prompt` itself (monkey-patched for the test's
duration, restored in `finally`); inside the stub, `this` is the real session
instance `execute` constructed (asserted `instanceof AgentSession`), and the
test drives `this._extensionRunner.emitToolCall(...)` — the SDK's own
real dispatch, per finding 1 — with a denied tool (`"write"`, outside
`gleipnir-code`'s allow-set) and an allowed one (`"read"`, inside it),
asserting block / pass respectively.

**Why `prompt` had to be stubbed at all (the concrete, named empirical
limit):** `createAgentSession`'s own body (read directly off the SDK this
session) calls `ModelRuntime.create({ authPath, modelsPath })` and
`findInitialModel(...)` against `~/.pi/agent`/provider auth before a real
`session.prompt(...)` can run a model turn. That is genuinely unreachable
under this sandbox's `--network=none` policy with no configured provider
credentials in-container. **This is the actual empirical limit of what S1 can
prove in this sandbox:** a fully unstubbed, model-decides-to-call-a-tool,
live conversational turn cannot be exercised here — only everything up to and
including the real `tool_call` dispatch pipeline can be, and that is now
covered by `AC-9-E2E`, for real.

**Net D6 verdict:** the "does a real child, wired the way `delegate.ts` wires
it, actually enforce?" question is **settled: yes**, on real SDK code, not a
fake. The "does pi have some other, undiscovered auto-inherit path that would
make the explicit wiring unnecessary?" question is also settled by finding 2
above: no, there isn't one — the dispatch loop only ever sees
`this.extensions`. The one gap that remains unclosed is the live-model-turn
case named directly above, which is a network/auth limitation, not a
wiring-correctness one.

## S1 limitations — both RESOLVED in S2

The two follow-ups S1 quality review surfaced are now closed:

1. **RESOLVED (D-A pass-through).** S1's `customTools: []` made nested
   `delegate` architecturally unreachable end-to-end. S2 adds
   `resolveChildCustomTools(role)` (DRY-projected from the same role table)
   and passes the real `delegate` tool definition (`buildDelegateTool()`)
   into a child whose role declares `"delegate"`. Nested delegation is now
   reachable and the depth cap refuses it under a real re-invocation
   (AC-13/AC-14). Deny-by-default is preserved through the pass-through: a
   non-delegate child receives `[]` (AC-12).
2. **RESOLVED (D-B vocabulary fix).** The S1 `read_file`/`write_file` names
   are retired; `baseTools` now uses the real SDK `ToolName` union
   (`read | bash | edit | write | grep | find | ls`), enforced by `tsc`
   against the `ToolName` type and by a runtime membership check against
   `SDK_BASE_TOOL_NAMES` (AC-18).

## Named residual limits carried into S2 (NOT resolved — honest scope)

- **Live-model-turn gap (inherited from S1, unchanged).** AC-9-E2E drives the
  real `tool_call`/`emitToolCall` dispatch via a stubbed
  `AgentSession.prototype.prompt`, because `createAgentSession` needs provider
  auth unreachable under `--network=none`. A fully model-driven turn (no stub)
  is not exercised. This is a network/auth limit, not a wiring-correctness
  one.
- **AC-13/14's nested-call mechanism is direct re-invocation, not
  `emitToolCall` (named for description accuracy, a fifth residual item
  alongside the three above).** Unlike AC-9-E2E, the AC-13/14 nested-depth-cap
  test does NOT drive the nested call through
  `this._extensionRunner.emitToolCall(...)`. From inside that same kind of
  stubbed `AgentSession.prototype.prompt`, it re-invokes the module-level
  captured `delegate` `execute` reference directly — a real nested
  re-invocation of `delegate.ts`'s own execute, at the layer the pass-through
  (`resolveChildCustomTools`) makes reachable. `quality-reviewer` confirmed
  this is a legitimate, defensible technique that genuinely proves the
  depth-cap-under-real-recursive-execute property; it is called out here only
  so the mechanism is described accurately rather than implied to route
  through `emitToolCall` like AC-9-E2E does.
- **Argument-level (per-arg/per-path) enforcement is OUT of S2 scope,
  captured-as-metadata.** The per-role `bounds` field in `roleTable.ts`
  records each role's per-path/per-arg bound (e.g. `gleipnir-code` may `edit`
  but not under `.gleipnir/**`; `git-ops` may `read` but not `.git/**`;
  `quality-reviewer`'s bash is `git {diff,log,show,status}` only) so the
  canonical table does not lose them — but S2 enforces only the COARSE
  tool-presence allow/deny via `canUse`. Fine-grained `event.input`
  inspection is S3/S7 (the E-1 argument-policy seam).
- **`ToolName` is mirrored locally, not imported.** The SDK defines
  `ToolName`/`allToolNames` only at the subpath
  `.../dist/core/tools/index`, which its `exports` map does not expose (only
  `.`, `./rpc-entry`, `./client`), and the root index does not re-export
  them. So the union is declared verbatim in `roleTable.ts` and AC-18
  guards against drift by asserting membership. Reconcile if a future SDK
  release re-exports `ToolName` from root.

## Prior "capability wall" note (resolved)

An earlier delegation in this session's history reported both verification
commands denied by a stale permission snapshot. That snapshot issue was
cleared by a session restart (confirmed by the operator); `bin/gleipnir-sandbox
test --profile pi` and `bin/gleipnir-sandbox lint --profile pi` are both live
and were both run for real by this delegation (28/28 tests pass, lint clean).

## AC → test mapping

| AC | Test | File |
|---|---|---|
| AC-1 (deny) | "AC-1: a tool not in the active role's allow-set is blocked..." | `test/enforcement.test.ts` |
| AC-2 (allow) | "AC-2: an allowed tool call passes..." | `test/enforcement.test.ts` |
| AC-3 (deny-by-default, unset role) | "AC-3: deny-by-default when no active role is set" | `test/enforcement.test.ts` |
| AC-4 (non-interactive fail-closed) | "AC-4: non-interactive fail-closed..." | `test/enforcement.test.ts` |
| AC-5 (bounded child) | "AC-5: resolveChildTools returns exactly..." | `test/delegate.test.ts` |
| AC-6 (depth cap, first level) | "AC-6: delegation at depth === cap is refused..." | `test/delegate.test.ts` |
| AC-7 (depth cap, nested) | "AC-7: nested delegation... is caught by the same cap" | `test/delegate.test.ts` |
| AC-8 (counter safety) | "AC-8: the depth counter is restored after a child throws" | `test/delegate.test.ts` |
| AC-9 (child-hook binding, D6, module-level) | "AC-9: the child's explicitly re-wired enforcement extension blocks..." | `test/delegate.test.ts` |
| AC-9-E2E (child-hook binding, D6, real end-to-end) | "AC-9-E2E: delegate.ts's real execute(), via a real createAgentSession child..." | `test/delegate.test.ts` |
| AC-10 (package validity) | manual: `package.json` peers vs `dependencies` (see "Peer-dep resolution" above) | `package.json` |
| AC-11 (pass-through projected from table, DRY) | "AC-11: resolveChildCustomTools projects a delegate-role's declared customTools..." | `test/delegate.test.ts` |
| AC-12 (deny-by-default through pass-through) | "AC-12: a non-delegate child role does not receive delegate..." | `test/delegate.test.ts` |
| AC-12b (re-passable delegate definition) | "AC-12b: buildDelegateTool produces a re-passable definition..." | `test/delegate.test.ts` |
| AC-13/AC-14 (real nested depth-cap E2E via direct re-invocation of the captured `execute` from the stubbed `prompt` — NOT via `emitToolCall` — + counter restore) | "AC-13/AC-14: nested delegation via a real re-invoked delegate is refused past the depth cap..." | `test/delegate.test.ts` |
| AC-15 (session_start orchestrator seed, guarded) | "AC-15: session_start seeds orchestrator on an empty stack, and does NOT clobber..." | `test/enforcement.test.ts` |
| AC-16 (deny-by-default per role, all 8) | "AC-16: deny-by-default holds for every one of the 8 roles" + "AC-16 (hook): a denied tool blocks through the real hook..." | `test/roleTable.test.ts`, `test/enforcement.test.ts` |
| AC-17 (G-2 git-broker sole-holder + inert name) | "AC-17: git-ops is the sole broker (git) holder..." + P2 pm-partition check | `test/roleTable.test.ts` |
| AC-18 (SDK ToolName vocabulary fidelity) | "AC-18: base-tool vocabulary matches the SDK ToolName union..." | `test/roleTable.test.ts` |
| AC-19 (frozen table, no runtime widening) | "AC-19: the table (including nested partitions) is frozen..." | `test/roleTable.test.ts` |
| AC-20 (manifest + .pi/settings.json validity) | manual: `pi.extensions` resolves, no peer under `dependencies`, `.pi/settings.json` valid | `package.json`, `.pi/settings.json` |
| AC-21 (D1 coarse-presence fix: present-but-scoped `edit`/`bash` in `baseTools` with `bounds` recorded; genuinely-denied stay absent) | "AC-21: D1 coarse-presence fix — present-but-scoped capabilities appear in baseTools with bounds recorded; genuinely-denied ones stay absent" | `test/roleTable.test.ts` |

## Out of scope (do not expand)

No G-5 engine (S4), no HMAC/attestation (S5), no broker reachability (S6, the
git-broker name is inert/declared-only here), no S7 preflight/argument-level
enforcement. The Tier-3 `stage-role-map.md`/`AGENTS.md` supersession is a
SEPARATE operator-authored follow-up (plan D-D), NOT done here. No Open-Q1
(in-process vs process-isolated delegation), Open-Q2 (fail-closed-vs-sink
*policy*), Open-Q3 (MCP-broker reachability), or Open-Q4 (cutover sequencing)
decisions are made here.
