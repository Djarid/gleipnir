/**
 * enforcement.test.ts — the correctness arbiter for `enforcement.ts`
 * (plan Assemble step 4; success criteria 1 + AC-1..AC-4).
 *
 * Test-first for the hook logic (Axiom 1): these tests do not spin up a
 * real pi runtime (createAgentSession / a live model) — they register a
 * minimal fake `ExtensionAPI` that only implements `.on(name, handler)`,
 * capture the handler `enforcement.ts` installs for `"tool_call"`, and
 * invoke it directly with hand-built `event`/`ctx` objects matching the
 * plan's Link-validated shape (`event.toolName`, `ctx.hasUI`). This is
 * exactly the shipped `permission-gate.ts` pattern's own contract — no live
 * pi.dev SDK network/runtime access is required to exercise it, which
 * matters because this delegation ran under `--network=none` sandboxing
 * with no path to a live pi runtime (see `pi-package/README.md`,
 * "Capability wall").
 */

import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import enforcement, { PRIMARY_ROLE } from "../src/enforcement.ts";
import {
  clearActiveRole,
  getActiveRole,
  setActiveRole,
} from "../src/activeRole.ts";
import { ROLE_ALLOW_SETS, UNIVERSALLY_DENIED } from "../src/roleTable.ts";

type SessionStartHandler = () => Promise<undefined>;

/** Capture both the tool_call and session_start handlers enforcement installs,
 * so the P4 seed (AC-15) can be exercised through the real registered wiring
 * rather than only the underlying activeRole helper. */
function installEnforcementFull(): {
  toolCall: ToolCallHandler;
  sessionStart: SessionStartHandler;
} {
  let toolCall: ToolCallHandler | undefined;
  let sessionStart: SessionStartHandler | undefined;
  const fakePi = {
    on(name: string, fn: ToolCallHandler | SessionStartHandler) {
      if (name === "tool_call") {
        toolCall = fn as ToolCallHandler;
      } else if (name === "session_start") {
        sessionStart = fn as SessionStartHandler;
      }
    },
  };
  enforcement(fakePi as unknown as Parameters<typeof enforcement>[0]);
  assert.ok(toolCall, "enforcement() must register a tool_call handler");
  assert.ok(sessionStart, "enforcement() must register a session_start handler");
  return { toolCall: toolCall as ToolCallHandler, sessionStart: sessionStart as SessionStartHandler };
}

type ToolCallHandler = (
  event: { toolName: string; input?: unknown },
  ctx: { hasUI: boolean },
) => Promise<{ block: true; reason: string } | undefined>;

function installEnforcement(): ToolCallHandler {
  let handler: ToolCallHandler | undefined;
  const fakePi = {
    on(name: string, fn: ToolCallHandler) {
      if (name === "tool_call") {
        handler = fn;
      }
    },
  };
  enforcement(fakePi as unknown as Parameters<typeof enforcement>[0]);
  assert.ok(handler, "enforcement() must register a tool_call handler");
  return handler as ToolCallHandler;
}

afterEach(() => {
  clearActiveRole();
});

test("AC-1: a tool not in the active role's allow-set is blocked with a non-empty reason", async () => {
  const hook = installEnforcement();
  setActiveRole("gleipnir-code");

  // D1 correction: `bash` is now a real baseTools member for gleipnir-code
  // (present-but-arg-scoped, AC-21), so it can no longer serve as this role's
  // negative probe. `write` remains genuinely denied for gleipnir-code
  // (absent from baseTools/customTools/brokerTools).
  const result = await hook({ toolName: "write" }, { hasUI: true });

  assert.equal(result?.block, true);
  assert.ok(result && result.reason.length > 0, "reason must be non-empty");
});

test("AC-2: an allowed tool call passes (returns undefined)", async () => {
  const hook = installEnforcement();
  setActiveRole("gleipnir-code");

  // "read" is a real SDK base ToolName in gleipnir-code's baseTools (S2 vocab).
  const result = await hook({ toolName: "read" }, { hasUI: true });

  assert.equal(result, undefined);
});

test("AC-3: deny-by-default when no active role is set", async () => {
  const hook = installEnforcement();
  // Deliberately no setActiveRole() call.

  const result = await hook({ toolName: "read" }, { hasUI: true });

  assert.equal(result?.block, true);
});

test("AC-4: non-interactive fail-closed — ctx.hasUI === false blocks and the reason mentions no UI", async () => {
  const hook = installEnforcement();
  setActiveRole("gleipnir-code");

  // D1 correction: `bash` is now allowed for gleipnir-code (AC-21), so the
  // hook's canUse() check would short-circuit to `undefined` (allowed)
  // regardless of ctx.hasUI. `write` is still genuinely denied for
  // gleipnir-code, so it correctly reaches the fail-closed branch.
  const result = await hook({ toolName: "write" }, { hasUI: false });

  assert.equal(result?.block, true);
  assert.ok(
    result && /no ui/i.test(result.reason),
    `reason should mention "no UI"; got: ${result?.reason}`,
  );
});

test("edge case: unknown toolName not in any allow-set is denied even with a set role", async () => {
  const hook = installEnforcement();
  setActiveRole("gleipnir-code");

  const result = await hook({ toolName: "totally_unregistered_tool" }, { hasUI: true });

  assert.equal(result?.block, true);
});

test("AC-16 (hook): a denied tool blocks through the real hook for every one of the 8 roles", async () => {
  const hook = installEnforcement();
  // D1 correction: `bash` is NO LONGER a sound universal deny probe — it is a
  // real baseTools member for gleipnir-code/quality-reviewer/git-ops (present-
  // but-arg-scoped, AC-21). The universal probe must be a name absent from
  // EVERY role's union allow-set; import the same unregistered-name constant
  // `roleTable.test.ts` uses (`UNIVERSALLY_DENIED`), for DRY/consistency.
  for (const role of Object.keys(ROLE_ALLOW_SETS)) {
    clearActiveRole();
    setActiveRole(role);
    const result = await hook({ toolName: UNIVERSALLY_DENIED }, { hasUI: true });
    assert.equal(
      result?.block,
      true,
      `role "${role}" must block "${UNIVERSALLY_DENIED}" (deny-by-default through the hook)`,
    );
  }
});

test("AC-15: session_start seeds orchestrator on an empty stack, and does NOT clobber a pushed child role", async () => {
  const { sessionStart } = installEnforcementFull();

  // Empty stack -> seed the primary role.
  clearActiveRole();
  await sessionStart();
  assert.equal(
    getActiveRole(),
    PRIMARY_ROLE,
    "session_start on an empty stack must seed the orchestrator",
  );

  // Non-empty stack (a child delegate pushed its role) -> seed must NOT clobber.
  clearActiveRole();
  setActiveRole("gleipnir-code"); // simulate a child-pushed role
  await sessionStart(); // e.g. a child session's own session_start firing
  assert.equal(
    getActiveRole(),
    "gleipnir-code",
    "a child's session_start must NOT re-seed orchestrator over a pushed child role",
  );
});
