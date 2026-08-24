/**
 * delegate.test.ts — the correctness arbiter for `delegate.ts` (plan
 * Assemble step 7; success criteria 2-4, AC-5..AC-9).
 *
 * CAPABILITY-WALL NOTE (read before trusting AC-9 as "D6 answered"): these
 * tests do NOT construct a real `createAgentSession` — that requires the
 * live `@earendil-works/pi-coding-agent` runtime, only reachable inside
 * `bin/gleipnir-sandbox --profile pi`, which this delegation's live bash
 * grant did not actually include (see `pi-package/README.md`, "Capability
 * wall"). AC-5..AC-8 instead exercise the exact underlying mechanisms
 * `delegate.ts` wraps (`resolveChildTools`, `depth.ts`'s
 * enter/exit/withDepthGuard) directly — those ARE real, executable,
 * pi-SDK-free unit tests, not stand-ins. AC-9 exercises the exact
 * `enforcement.ts` module `delegate.ts` explicitly re-wires into the child
 * (the D6 defensive choice) via a fake minimal `ExtensionAPI`, proving the
 * WIRING is correct — it does not and cannot prove, without sandbox access,
 * whether pi's real child sessions also auto-inherit the parent hook. That
 * empirical question is unresolved and is called out explicitly in the
 * final report, not asserted either way.
 */

import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { AgentSession } from "@earendil-works/pi-coding-agent";

import delegateExtension, { resolveChildTools } from "../src/delegate.ts";
import enforcement from "../src/enforcement.ts";
import { ROLE_ALLOW_SETS } from "../src/roleTable.ts";
import { clearActiveRole, setActiveRole } from "../src/activeRole.ts";
import {
  DepthCapExceededError,
  getDepth,
  resetDepth,
  setCap,
  withDepthGuard,
} from "../src/depth.ts";

afterEach(() => {
  clearActiveRole();
  resetDepth();
  setCap(3); // restore the module default between tests
});

test("AC-5: resolveChildTools returns exactly the delegated role's allow-set", () => {
  const tools = resolveChildTools("gleipnir-code");

  assert.deepEqual(
    new Set(tools),
    new Set(ROLE_ALLOW_SETS["gleipnir-code"]),
    "child's tool set must equal the role's allow-set, no more, no less",
  );
});

test("AC-5b: resolveChildTools refuses an unknown role rather than defaulting", () => {
  assert.throws(() => resolveChildTools("not-a-real-role"), /unknown role/);
});

test("AC-6: delegation at depth === cap is refused with a reason", async () => {
  setCap(1);

  // First level succeeds and completes (depth returns to 0).
  await withDepthGuard(async () => {
    assert.equal(getDepth(), 1);
  });
  assert.equal(getDepth(), 0);

  // Simulate depth already at the cap (e.g. an outer, still-open delegation)
  // and confirm the next attempt is refused, not silently allowed.
  await withDepthGuard(async () => {
    assert.equal(getDepth(), 1);
    await assert.rejects(
      () => withDepthGuard(async () => {}),
      DepthCapExceededError,
      "a delegate call at depth === cap must be refused, not allowed",
    );
  });
});

test("AC-7: nested delegation (a child that itself delegates) is caught by the same cap", async () => {
  setCap(2);

  await withDepthGuard(async () => {
    // depth 1 — one level of delegation.
    assert.equal(getDepth(), 1);
    await withDepthGuard(async () => {
      // depth 2 — the child's own transitive delegate call.
      assert.equal(getDepth(), 2);
      await assert.rejects(
        () => withDepthGuard(async () => {}),
        DepthCapExceededError,
        "nested delegation past the cap must be refused too, not just first-level",
      );
    });
  });
  assert.equal(getDepth(), 0);
});

test("AC-8: the depth counter is restored after a child throws", async () => {
  setCap(3);

  await withDepthGuard(async () => {
    assert.equal(getDepth(), 1);
  });
  assert.equal(getDepth(), 0, "sanity: depth returns to 0 after a clean run");

  await assert.rejects(
    withDepthGuard(async () => {
      assert.equal(getDepth(), 1);
      throw new Error("simulated child failure");
    }),
    /simulated child failure/,
  );

  assert.equal(
    getDepth(),
    0,
    "AC-8: depth must be restored to its prior value even when the guarded fn throws",
  );
});

/**
 * RECON FINDINGS (this delegation, `--profile pi` now live; distilled here,
 * raw console dumps removed from the committed suite — the findings below
 * are what AC-9-E2E, immediately following, is built on):
 *
 * 1. `session._extensionRunner.emitToolCall(event)` (internal, underscore-
 *    prefixed, NOT in the public .d.ts) is *verbatim* the function
 *    `session._installAgentToolHooks()` wires to `agent.beforeToolCall`:
 *      `runner.emitToolCall({ type: "tool_call", toolName: toolCall.name,
 *      toolCallId: toolCall.id, input: args })`.
 *    So calling it directly on a real, `createAgentSession`-constructed
 *    session's real `_extensionRunner` exercises the SAME dispatch a live
 *    model-driven tool call would — the only thing not exercised is the
 *    model's decision to call a tool at all. This is the "lower-level way to
 *    invoke a specific tool call... without a full model round-trip" the
 *    delegation asked to look for (option (a)) — found, but via a private
 *    API, not a documented one; flagged as a caveat below and in the README.
 * 2. `emitToolCall`'s real body: iterates `this.extensions`, and for each,
 *    `ext.handlers.get("tool_call")` — confirming a child's enforcement
 *    comes from whichever extensions its OWN `resourceLoader` loaded, not
 *    from some ambient parent-hook inheritance. This is the closest this
 *    session got to a direct D6 answer: there is no "auto-inherit the
 *    parent's hook" code path at all — dispatch is scoped to `this.extensions`
 *    on the (child's own) `_extensionRunner`, built from the (child's own)
 *    `resourceLoader.getExtensions()`. `delegate.ts`'s explicit
 *    `extensionFactories: [enforcementExtension]` wiring is therefore not
 *    "redundant-but-harmless as a defensive choice" — it is the ONLY
 *    mechanism by which the child is enforced. A child built without it
 *    would have an empty `this.extensions` and `emitToolCall` would return
 *    `undefined` (allowed) for every tool. D6 is answered: NO auto-inherit;
 *    explicit `resourceLoader`/`extensionFactories` wiring is REQUIRED, and
 *    `delegate.ts` already does it.
 * 3. `AgentSession` (the class `session` is an instance of) is a NAMED
 *    PUBLIC export of `@earendil-works/pi-coding-agent` (confirmed:
 *    `session.constructor === AgentSession`), and `prompt` is a regular
 *    prototype method (present in `Object.getOwnPropertyNames(Object.
 *    getPrototypeOf(session))`, not an instance-assigned closure) — so it CAN
 *    be monkey-patched at the class level before invoking `delegate.ts`'s
 *    real `execute`, letting every real construction step run for real and
 *    intercepting only the one call (`session.prompt(...)`) that would
 *    otherwise need network + model auth unavailable under
 *    `--network=none`. This is the mechanism AC-9-E2E below uses.
 * 4. Base tool names the real SDK registers are `read`, `bash`, `edit`,
 *    `write`, `grep`, `find`, `ls` (confirmed via `session._baseToolDefinitions`)
 *    — NOT `read_file`/`write_file` as `roleTable.ts`'s
 *    `GLEIPNIR_CODE_ALLOW_SET` currently names them. That mismatch does not
 *    invalidate AC-9 (the hook only compares `event.toolName` strings against
 *    the role table; it never needs the name to correspond to a real base
 *    tool for enforcement itself to be exercised), but it means "read_file"
 *    would never resolve to a callable tool in a real conversational turn.
 *    Flagged here and in the README; NOT silently fixed in this delegation
 *    (renaming the allow-set is a roleTable.ts scope decision, not an AC-9
 *    test-authoring one — out of scope for this delegation, escalate if it
 *    matters for S2).
 */

test("AC-9: the child's explicitly re-wired enforcement extension blocks a call to a tool outside its allow-set", async () => {
  // This is delegate.ts's D6 defensive choice made concrete: the SAME
  // `enforcement.ts` module delegate.ts passes via
  // `extensionFactories: [enforcementExtension]` is loaded here exactly as
  // pi would load it for the child, and a denied tool call is attempted
  // against it — not merely checking the hook is "registered" (the
  // spec-review tightening this AC-9 wording note required).
  let handler:
    | ((
        event: { toolName: string },
        ctx: { hasUI: boolean },
      ) => Promise<{ block: true; reason: string } | undefined>)
    | undefined;
  const fakeChildPi = {
    on(name: string, fn: typeof handler) {
      if (name === "tool_call") {
        handler = fn;
      }
    },
  };

  enforcement(fakeChildPi as unknown as Parameters<typeof enforcement>[0]);
  assert.ok(handler, "the re-wired enforcement extension must register a tool_call handler");

  // Simulate the child's active role (delegate.ts calls pushActiveRole(role)
  // before the child runs).
  setActiveRole("gleipnir-code");

  // "bash" is deliberately absent from gleipnir-code's allow-set (roleTable.ts).
  const denied = await handler!({ toolName: "bash" }, { hasUI: true });
  assert.equal(denied?.block, true, "AC-9: a denied tool call reaching the child must be blocked");
  assert.ok(denied && denied.reason.length > 0);

  // And an allowed one still passes for the child, proving this isn't a
  // blanket deny that would make the child useless.
  const allowed = await handler!({ toolName: "read_file" }, { hasUI: true });
  assert.equal(allowed, undefined);
});

test("AC-9-E2E: delegate.ts's real execute(), via a real createAgentSession child, genuinely enforces the role table through the real ExtensionRunner.emitToolCall dispatch", async () => {
  // ==========================================================================
  // WHAT IS REAL HERE (per the RECON findings block above):
  //   - `delegateExtension` (the real default export of "../src/delegate.ts")
  //     is registered against a minimal `registerTool`-capturing shim — the
  //     SAME capture pattern `enforcement.test.ts`/the fake AC-9 test above
  //     already use for `.on`. This does NOT mock any of delegate.ts's own
  //     logic; it is the only way to obtain a reference to the `execute`
  //     function a module registers via `pi.registerTool(...)`.
  //   - Calling the captured `execute(...)` runs delegate.ts's REAL body,
  //     unmodified: `withDepthGuard` -> `pushActiveRole` -> a REAL
  //     `new DefaultResourceLoader({ extensionFactories: [enforcementExtension] })`
  //     -> a REAL `await resourceLoader.reload()` -> a REAL
  //     `await createAgentSession({ resourceLoader, sessionManager:
  //     SessionManager.inMemory(), tools, customTools: [] })`, against the
  //     real `@earendil-works/pi-coding-agent` package.
  //   - The resulting child session's `_extensionRunner` is therefore the
  //     REAL `ExtensionRunner` the SDK built from that REAL resourceLoader,
  //     with the REAL `enforcement.ts` module's `tool_call` handler
  //     registered on it — not a fake `ExtensionAPI`.
  //
  // WHAT IS STUBBED, AND WHY (the concrete, named empirical limit — see also
  // the README "D6 finding" section and delegate.ts's module header):
  //   - `AgentSession.prototype.prompt` is monkey-patched for the duration of
  //     this test only (restored in `finally`). `session.prompt(...)` is the
  //     ONE call in delegate.ts's `execute` that needs a live model +
  //     provider auth — `createAgentSession`'s own body (dumped via RECON
  //     this session) shows it calls `ModelRuntime.create({ authPath,
  //     modelsPath })` and `findInitialModel(...)` against `~/.pi/agent`,
  //     which is unreachable under this sandbox's `--network=none` policy
  //     and has no configured auth in-container. Everything BEFORE this call
  //     — resourceLoader construction, extensionFactories wiring,
  //     createAgentSession, the real ExtensionRunner — runs untouched.
  //   - Inside the stub, `this` is the REAL session instance delegate.ts's
  //     execute constructed (proven below by asserting `capturedSession
  //     instanceof AgentSession`). From it the test drives
  //     `this._extensionRunner.emitToolCall(event)` — the EXACT function the
  //     SDK's own `_installAgentToolHooks()` calls when a live model turn
  //     actually invokes a tool (`agent.beforeToolCall = async ({toolCall,
  //     args}) => runner.emitToolCall({type:"tool_call", toolName:
  //     toolCall.name, toolCallId: toolCall.id, input: args})`, confirmed via
  //     RECON dump this session). This is exactly "driving the tool_call
  //     hook's registered callback directly against a REAL
  //     resourceLoader-loaded extension instance" — option (a) named in the
  //     delegation brief — found to be possible, but only via a
  //     private/underscore-prefixed API (`_extensionRunner`), not a
  //     documented public one. That is itself a caveat: this test is coupled
  //     to pi's current internal shape and could break on a pi upgrade with
  //     no public-API signal.
  //
  // D6 VERDICT FROM THIS TEST: the "does delegate.ts's chosen wiring actually
  // enforce on a real child" question is now settled — yes, via a REAL
  // ExtensionRunner built from the REAL resourceLoader delegate.ts
  // constructs. Moreover, `emitToolCall`'s real body (iterates
  // `this.extensions`, i.e. only the extensions the CHILD's own
  // resourceLoader loaded) shows there is no ambient "auto-inherit the
  // parent's hook" code path at all — so the explicit `extensionFactories`
  // wiring delegate.ts already does is not a defensive redundancy, it is the
  // ONLY mechanism. What remains NOT settled is whether a live,
  // model-driven conversational turn — with no stub anywhere — would also
  // get blocked; that residual gap is exactly the network/model-auth
  // unavailability named above, and is the concrete, named empirical limit
  // of what this `--network=none` sandbox can prove (see the "STOP and
  // report" instruction this test's brief invoked). It is not a caveat this
  // test papers over — it is the reported limit.
  // ==========================================================================

  const originalPrompt = AgentSession.prototype.prompt;
  let capturedSession: AgentSession | undefined;
  let deniedResult: { block: true; reason: string } | undefined;
  let allowedResult: { block: true; reason: string } | undefined;

  (
    AgentSession.prototype as unknown as {
      prompt: (this: AgentSession, text: string) => Promise<string>;
    }
  ).prompt = async function stubbedPrompt(
    this: AgentSession,
    _text: string,
  ): Promise<string> {
    capturedSession = this;
    const runner = (
      this as unknown as {
        _extensionRunner: {
          emitToolCall: (event: {
            type: string;
            toolName: string;
            toolCallId: string;
            input: unknown;
          }) => Promise<{ block: true; reason: string } | undefined>;
        };
      }
    )._extensionRunner;

    // "bash" is deliberately absent from gleipnir-code's allow-set
    // (roleTable.ts) — the negative case AC-9-E2E exists to prove.
    deniedResult = await runner.emitToolCall({
      type: "tool_call",
      toolName: "bash",
      toolCallId: "ac9-e2e-denied",
      input: {},
    });
    // "read_file" IS in gleipnir-code's allow-set — the positive control,
    // so this test cannot pass by a hook that always blocks everything.
    allowedResult = await runner.emitToolCall({
      type: "tool_call",
      toolName: "read_file",
      toolCallId: "ac9-e2e-allowed",
      input: {},
    });

    return "stubbed model turn (no network/model-auth in --network=none sandbox; see file header + README D6 section)";
  };

  type DelegateExecuteFn = (
    toolCallId: string,
    params: { role: string; prompt: string },
    signal: AbortSignal,
    onUpdate: (update: unknown) => void,
    ctx: unknown,
  ) => Promise<{ content: Array<{ type: string; text: string }>; details: undefined }>;

  let executeFn: DelegateExecuteFn | undefined;
  const fakeParentPi = {
    registerTool(def: { name: string; execute: DelegateExecuteFn }) {
      if (def.name === "delegate") {
        executeFn = def.execute;
      }
    },
  };

  try {
    delegateExtension(fakeParentPi as unknown as Parameters<typeof delegateExtension>[0]);
    assert.ok(executeFn, "delegate() must register a tool named 'delegate' with an execute fn");

    const result = await executeFn!(
      "ac9-e2e-tool-call-id",
      { role: "gleipnir-code", prompt: "irrelevant -- prompt() is stubbed" },
      new AbortController().signal,
      () => {},
      undefined,
    );

    assert.ok(
      result.content[0]?.text.includes("stubbed model turn"),
      "delegate.ts's real execute() must complete and return its normal AgentToolResult shape",
    );
  } finally {
    AgentSession.prototype.prompt = originalPrompt;
  }

  assert.ok(capturedSession, "the stubbed prompt() must have been invoked with a real session");
  assert.ok(
    capturedSession instanceof AgentSession,
    "AC-9-E2E: the child must be a real AgentSession instance, not a fake",
  );

  assert.equal(
    deniedResult?.block,
    true,
    "AC-9-E2E: a real child session's real ExtensionRunner must block a denied tool call",
  );
  assert.ok(
    deniedResult && deniedResult.reason.length > 0,
    "AC-9-E2E: the block must carry a non-empty reason",
  );

  assert.equal(
    allowedResult,
    undefined,
    "AC-9-E2E: a real child session's real ExtensionRunner must allow an allowed tool call (positive control)",
  );
});
