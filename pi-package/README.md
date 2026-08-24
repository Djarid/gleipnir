# pi-package — S1 primitive-proof slice

Status: **implemented and verified** — `bin/gleipnir-sandbox test --profile pi`
(12/12 pass, including a real end-to-end `createAgentSession` child, see
"D6 finding" below) and `bin/gleipnir-sandbox lint --profile pi` (clean) both
ran successfully once the sandbox permission staleness from the prior session
was cleared by a session restart. This package is the first buildable slice
(S1) of the pi.dev-native re-expression of Gleipnir (Approach B,
`pi-dev-replatform-brainstorm.md`), per the full ATLAS plan
`.gleipnir/plans/pi-dev-replatform-first-slice.md`.

## What this slice proves

1. **CRUX 1 — enforcement.** A `tool_call` block hook
   (`src/enforcement.ts`) reads a Gleipnir-owned role→capability table
   (`src/roleTable.ts`) and the current session's active role
   (`src/activeRole.ts`) to deny a not-allowed tool call and permit an
   allowed one. Deny-by-default: unset role, unknown role, and unknown tool
   all resolve to `false`.
2. **CRUX 2 — delegation.** A `delegate` custom tool (`src/delegate.ts`)
   spins up a role-bounded child session via `createAgentSession`, guarded
   by a depth cap (`src/depth.ts`) that refuses runaway nesting (including
   transitive/nested delegation) and always restores its counter, even on
   failure (`try`/`finally`).
3. **D6 — the child-hook binding question.** See below. **Settled for the
   wiring-correctness question; one residual empirical gap remains, named
   explicitly.**

## How to reproduce

```sh
bin/gleipnir-sandbox test --profile pi   # node --test test/enforcement.test.ts test/delegate.test.ts
bin/gleipnir-sandbox lint --profile pi   # tsc --noEmit -p tsconfig.json
```

Both run inside the `gleipnir-sandbox-pi` container (`--network=none`,
repo mounted read-only), which pre-installs the five pi peer packages +
`typebox` + `typescript` at the filesystem-root `/node_modules` (see
`Containerfile.pi`) — `pi-package/node_modules` is deliberately absent; do
not add a local install. Confirmed reachable and live this session: 12/12
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
real dispatch, per finding 1 — with a denied tool (`"bash"`, outside
`gleipnir-code`'s allow-set) and an allowed one (`"read_file"`, inside it),
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

## Known limitations for S2

Two follow-ups surfaced by quality review, non-blocking for S1 but relevant
to how S2 (the full 8-role roster) is scoped:

1. **`customTools: []` makes nested `delegate` architecturally unreachable
   end-to-end.** `delegate.ts` passes `customTools: []` to every child
   unconditionally. Since `"delegate"` is itself a custom tool (not a base
   SDK `ToolName`), a child never actually receives it — so a child can
   **never** re-invoke `delegate` in a real, unstubbed system, even though
   `roleTable.ts`'s allow-set includes `"delegate"` for the `gleipnir-code`
   role. AC-7's "nested delegation" is therefore proven only at the
   isolated `depth.ts` counter-mechanism level (already disclosed in
   `delegate.test.ts:10-13`); end-to-end nested delegation is
   architecturally unreachable as currently wired, not merely untested. S2
   will need to either pass `customTools` through to children or otherwise
   decide whether nested delegation is in scope at all.
2. **Allow-set tool names don't match the SDK's real base `ToolName`s.**
   `roleTable.ts`'s allow-set uses `"read_file"`/`"write_file"`, which do
   not match the SDK's real base `ToolName`s (`read`, `bash`, `powershell`,
   `edit`, `write`, `grep`, `find`, `ls`). This is already disclosed richly
   in `test/delegate.test.ts`'s comments; it is recorded here too so it is
   visible to the operator without reading test-file comments. S2's roster
   expansion should reconcile the allow-set vocabulary against the SDK's
   real tool names.

## Prior "capability wall" note (resolved)

An earlier delegation in this session's history reported both verification
commands denied by a stale permission snapshot. That snapshot issue was
cleared by a session restart (confirmed by the operator); `bin/gleipnir-sandbox
test --profile pi` and `bin/gleipnir-sandbox lint --profile pi` are both live
and were both run for real by this delegation (12/12 tests pass, lint clean).

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

## Out of scope (do not expand)

No full 8-role roster (S2), no G-5 engine (S4), no HMAC/attestation (S5), no
broker (S6). No Open-Q1 (sandbox vs Gondolin), Open-Q2 (fail-closed-vs-sink
*policy*), Open-Q3 (MCP-broker reachability), or Open-Q4 (cutover sequencing)
decisions are made here — this slice only demonstrates mechanisms.
