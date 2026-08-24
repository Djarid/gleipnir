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

import enforcement from "../src/enforcement.ts";
import { clearActiveRole, setActiveRole } from "../src/activeRole.ts";

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

  const result = await hook({ toolName: "bash" }, { hasUI: true });

  assert.equal(result?.block, true);
  assert.ok(result && result.reason.length > 0, "reason must be non-empty");
});

test("AC-2: an allowed tool call passes (returns undefined)", async () => {
  const hook = installEnforcement();
  setActiveRole("gleipnir-code");

  const result = await hook({ toolName: "read_file" }, { hasUI: true });

  assert.equal(result, undefined);
});

test("AC-3: deny-by-default when no active role is set", async () => {
  const hook = installEnforcement();
  // Deliberately no setActiveRole() call.

  const result = await hook({ toolName: "read_file" }, { hasUI: true });

  assert.equal(result?.block, true);
});

test("AC-4: non-interactive fail-closed — ctx.hasUI === false blocks and the reason mentions no UI", async () => {
  const hook = installEnforcement();
  setActiveRole("gleipnir-code");

  const result = await hook({ toolName: "bash" }, { hasUI: false });

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
