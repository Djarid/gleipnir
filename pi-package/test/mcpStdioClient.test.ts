/**
 * mcpStdioClient.test.ts — the correctness arbiter for the hand-rolled
 * MCP-over-stdio transport (`.gleipnir/plans/pi-dev-replatform-s6.md`,
 * Assemble step 3a; AC-CLIENT-1..5).
 *
 * Runs against `test/fixtures/mock-broker.mjs` (a tiny Node MCP-stdio mock —
 * see the plan's "Test-harness constraint": the `[profile.pi]` sandbox image
 * has no Python interpreter, so a REAL `python -m gleipnir.broker.*`
 * subprocess cannot be spawned here; the mock proves the client/relay/
 * credential-isolation LOGIC offline. Byte-level wire compatibility with the
 * REAL FastMCP-stdio server is the SEPARATE cross-profile confirmation,
 * AC-WIRE-1, `tests/test_broker_wire_protocol.py` under `[profile.broker]`.
 */

import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  pickEnv,
  relayToolCall,
  resetRequestIdForTestOnly,
  type SpawnSpec,
} from "../src/broker/mcpStdioClient.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const MOCK_BROKER_PATH = join(__dirname, "fixtures", "mock-broker.mjs");

function mockSpec(mode: string, extraEnv: Record<string, string> = {}): SpawnSpec {
  return {
    command: process.execPath,
    args: [MOCK_BROKER_PATH],
    env: { ...pickEnv(["PATH"]), MOCK_MODE: mode, ...extraEnv },
  };
}

test.beforeEach(() => {
  // The id counter is module-scope; reset between tests so no test's
  // assertions accidentally depend on another test's prior call count (the
  // `depth.ts` `resetDepth()` idiom).
  resetRequestIdForTestOnly();
});

test("AC-CLIENT-1: initialize + tools/call round-trip returns the mock's echoed structured result", async () => {
  const controller = new AbortController();
  const result = await relayToolCall(
    mockSpec("echo"),
    "git_status",
    { repo_dir: "" },
    controller.signal,
  );
  assert.equal(result.success, true, `expected success, got: ${JSON.stringify(result)}`);
  const parsed = JSON.parse(result.result ?? "{}");
  assert.equal(parsed.toolName, "git_status");
  assert.deepEqual(parsed.arguments, { repo_dir: "" });
});

test("AC-CLIENT-1b: params pass through untouched, including a value shaped like a git flag (structured, never argv — AC-RELAY-1)", async () => {
  const controller = new AbortController();
  const params = { message: "fix: tidy up --no-verify mentions in docs", files: "README.md" };
  const result = await relayToolCall(mockSpec("echo"), "commit_changes", params, controller.signal);
  assert.equal(result.success, true, `expected success, got: ${JSON.stringify(result)}`);
  const parsed = JSON.parse(result.result ?? "{}");
  assert.equal(parsed.toolName, "commit_changes");
  // The `--no-verify`-shaped substring travels as the STRING VALUE of the
  // `message` param, never assembled into an argv array — this is exactly
  // what a structured `tools/call` params object guarantees (D-S6-5).
  assert.deepEqual(parsed.arguments, params);
});

test("AC-CLIENT-2 (abort): aborting mid-call kills the child; the call resolves promptly; no orphaned process survives", async () => {
  const pidFile = `${process.env.TMPDIR ?? "/tmp"}/gleipnir-s6-mock-broker-pid-${process.pid}-${Date.now()}.txt`;
  const controller = new AbortController();
  const callPromise = relayToolCall(
    mockSpec("hang", { PID_FILE: pidFile }),
    "git_status",
    { repo_dir: "" },
    controller.signal,
  );

  // Give the child a moment to start and write its PID file before aborting.
  await new Promise((resolve) => setTimeout(resolve, 150));
  controller.abort();

  // The call must resolve (not hang forever) once the child is killed.
  const result = await Promise.race([
    callPromise,
    new Promise<never>((_resolve, reject) =>
      setTimeout(() => reject(new Error("relayToolCall did not resolve within 5s of abort")), 5000),
    ),
  ]);
  assert.equal(result.success, false, "an aborted call must resolve to a structured failure, not a success");

  // Confirm the child process the mock wrote its PID for is actually gone —
  // not merely that our promise resolved (the "no orphaned process" proof).
  const { readFileSync, rmSync } = await import("node:fs");
  let pidText: string | undefined;
  for (let attempt = 0; attempt < 20 && pidText === undefined; attempt++) {
    try {
      pidText = readFileSync(pidFile, "utf8").trim();
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
  }
  assert.ok(pidText, "the mock broker never wrote its PID file — cannot verify no-orphan");
  const pid = Number(pidText);
  assert.ok(Number.isInteger(pid) && pid > 0, `PID file did not contain a valid pid: ${pidText}`);

  let stillAlive = true;
  for (let attempt = 0; attempt < 20 && stillAlive; attempt++) {
    try {
      process.kill(pid, 0); // throws ESRCH once the process is gone
      await new Promise((resolve) => setTimeout(resolve, 25));
    } catch {
      stillAlive = false;
    }
  }
  assert.equal(stillAlive, false, `mock broker child (pid ${pid}) is still alive after abort — orphaned process`);

  try {
    rmSync(pidFile);
  } catch {
    // best-effort cleanup only
  }
});

test("AC-CLIENT-3 (spawn failure): a nonexistent command resolves to a structured error, never an unhandled throw", async () => {
  const controller = new AbortController();
  const spec: SpawnSpec = {
    command: "gleipnir-s6-this-command-does-not-exist-xyz",
    args: [],
  };
  const result = await relayToolCall(spec, "git_status", { repo_dir: "" }, controller.signal);
  assert.equal(result.success, false, "a spawn failure must be a structured failure");
  assert.ok(result.error && result.error.length > 0, "a structured failure must carry a non-empty error message");
});

test("AC-CLIENT-4a (malformed JSON from the child): a structured error, never a crash", async () => {
  const controller = new AbortController();
  const result = await relayToolCall(mockSpec("malformed"), "git_status", { repo_dir: "" }, controller.signal);
  assert.equal(result.success, false, "malformed JSON from the child must be a structured failure");
  assert.ok(result.error && result.error.length > 0);
});

test("AC-CLIENT-4b (served MCP error): a structured error carrying the server's message, never a crash", async () => {
  const controller = new AbortController();
  const result = await relayToolCall(mockSpec("error"), "git_status", { repo_dir: "" }, controller.signal);
  assert.equal(result.success, false, "a served MCP error must be a structured failure");
  assert.ok(result.error?.includes("mock broker error"), `expected the server's error message to surface, got: ${result.error}`);
});

test("AC-CLIENT-4c (MCP-level result.isError, no top-level JSON-RPC error): a structured failure carrying the tool's error text, never a masked success", async () => {
  const controller = new AbortController();
  const result = await relayToolCall(mockSpec("mcp-error"), "git_status", { repo_dir: "" }, controller.signal);
  assert.equal(
    result.success,
    false,
    "a result.isError:true response (the REAL broker's tool-execution-failure shape, AC-WIRE-1) must be a structured failure, not success",
  );
  assert.ok(
    result.error?.includes("mock broker mcp-error"),
    `expected the tool's error text to surface via result.error, got: ${JSON.stringify(result)}`,
  );
});

test("AC-CLIENT-5 (no env leak): the client adds no spawn env to any returned payload; only a value the SERVER itself chooses to echo appears", async () => {
  const sentinel = "SENTINEL-9f3a-client-test";
  const controller = new AbortController();
  const spec = mockSpec("sentinel", {
    SENTINEL_TOKEN: sentinel,
    // A second, DISTINCT credential-shaped value that the mock's "sentinel"
    // mode never reads or echoes — proving the CLIENT itself constructs
    // nothing from the full spawn env, only the server's deliberate choice
    // to echo SENTINEL_TOKEN is visible.
    GLEIPNIR_S6_TEST_UNRELATED_SECRET: "should-never-appear-anywhere",
  });
  const result = await relayToolCall(spec, "git_status", { repo_dir: "" }, controller.signal);
  assert.equal(result.success, true);
  const payload = JSON.stringify(result);
  assert.ok(payload.includes(sentinel), "the server's OWN deliberate echo of a caller-supplied value is not a leak (see mock-broker.mjs docstring)");
  assert.ok(
    !payload.includes("should-never-appear-anywhere"),
    "the client must not construct any payload containing an env value the server never asked to see",
  );
});

test("pickEnv: copies only the named vars present in the CURRENT process.env, never anything else", () => {
  const previous = process.env.GLEIPNIR_S6_PICKENV_TEST;
  process.env.GLEIPNIR_S6_PICKENV_TEST = "present-value";
  try {
    const copied = pickEnv(["GLEIPNIR_S6_PICKENV_TEST", "GLEIPNIR_S6_PICKENV_ABSENT"]);
    assert.deepEqual(copied, { GLEIPNIR_S6_PICKENV_TEST: "present-value" });
  } finally {
    if (previous === undefined) delete process.env.GLEIPNIR_S6_PICKENV_TEST;
    else process.env.GLEIPNIR_S6_PICKENV_TEST = previous;
  }
});

test("AC-PURITY (mcpStdioClient.ts): the module source names no concrete broker tool and no credential env-var name", async () => {
  const { readFileSync } = await import("node:fs");
  const src = readFileSync(join(__dirname, "..", "src", "broker", "mcpStdioClient.ts"), "utf8");
  for (const forbidden of [
    "git_status",
    "commit_changes",
    "issue_create",
    "GITHUB_TOKEN",
    "GITLAB_TOKEN",
    "gleipnir.broker.git",
    "gleipnir.broker.pm",
  ]) {
    assert.ok(
      !src.includes(forbidden),
      `mcpStdioClient.ts (the GENERIC transport, Boundary A) must not name "${forbidden}"`,
    );
  }
});
