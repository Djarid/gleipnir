#!/usr/bin/env node
/**
 * mock-broker.mjs — the minimal MCP-over-stdio MOCK broker used by
 * `mcpStdioClient.test.ts` / `broker.test.ts`
 * (`.gleipnir/plans/pi-dev-replatform-s6.md`, Assemble step 1a).
 *
 * Speaks the same newline-delimited JSON-RPC 2.0 subset the hand-rolled
 * `mcpStdioClient.ts` client targets: replies to `initialize`, silently
 * accepts (never replies to) the `notifications/initialized` notification,
 * and replies to `tools/call` per `MOCK_MODE` (env-driven):
 *
 *   - "echo" (default): result.content = [{type:"text", text:
 *     JSON.stringify({toolName, arguments})}] — proves the relay passes
 *     STRUCTURED params (AC-RELAY-1) by round-tripping them verbatim.
 *   - "error": replies with a top-level JSON-RPC `error` object (AC-CLIENT-4).
 *   - "mcp-error": replies with a WELL-FORMED JSON-RPC response (no
 *     top-level `error`) whose `result` is `{content:[...], isError:true}`
 *     — the shape the REAL FastMCP-stdio broker actually uses to report a
 *     tool-execution failure (confirmed by AC-WIRE-1,
 *     `tests/test_broker_wire_protocol.py`). Distinct from "error" above:
 *     proves the client checks `result.isError`, not just the top-level
 *     `error` field (AC-CLIENT-4c).
 *   - "sentinel": result embeds `process.env.SENTINEL_TOKEN` (or a default)
 *     in the text — used to prove the CLIENT does not itself construct any
 *     payload containing a credential substring (AC-CLIENT-5/AC-CRED-2); the
 *     broker's own (intentional) echo of a caller-supplied value is not a
 *     leak, only a value the client fabricates on its own would be.
 *   - "malformed": writes an invalid JSON-RPC line instead of a proper
 *     response (AC-CLIENT-4).
 *   - "hang": never responds to `tools/call` (AC-CLIENT-2, the abort/kill
 *     path — the client must kill this process on `AbortSignal`).
 *
 * This mock is NOT itself proof of byte-level wire compatibility with the
 * REAL FastMCP-stdio broker — that is the separate, pure-Python
 * cross-profile confirmation, AC-WIRE-1
 * (`tests/test_broker_wire_protocol.py`, run under `[profile.broker]`). This
 * mock proves the client/relay/credential-isolation LOGIC only, offline,
 * under `[profile.pi]` `--network=none`. See the plan's "Test-harness
 * constraint" section.
 */

import { createInterface } from "node:readline";
import { writeFileSync } from "node:fs";

const MODE = process.env.MOCK_MODE || "echo";

// S6 AC-CLIENT-2 (abort / no-orphan proof): when the caller wants to assert
// this process is actually gone after an AbortSignal-triggered kill, it sets
// PID_FILE and this mock writes its own pid there at startup — a normal
// mock-broker.mjs invocation with no PID_FILE set does this no-op-adjacent
// extra write and otherwise behaves identically.
if (process.env.PID_FILE) {
  try {
    writeFileSync(process.env.PID_FILE, String(process.pid));
  } catch {
    // best-effort only; the test polling for the file will simply time out
    // and fail loudly rather than this mock crashing on a write error.
  }
}

function send(message) {
  process.stdout.write(JSON.stringify(message) + "\n");
}

const rl = createInterface({ input: process.stdin, terminal: false });

rl.on("line", (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch {
    // Malformed input FROM the client is not what this fixture tests (the
    // client's own framing is proven by mcpStdioClient.test.ts's requests
    // being well-formed); ignore rather than crash the mock.
    return;
  }

  if (msg.method === "initialize") {
    send({
      jsonrpc: "2.0",
      id: msg.id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        serverInfo: { name: "gleipnir-mock-broker", version: "0.1.0" },
      },
    });
    return;
  }

  if (msg.method === "notifications/initialized") {
    // A notification: no `id`, no response is ever sent for it.
    return;
  }

  if (msg.method === "tools/call") {
    const { name, arguments: args } = msg.params ?? {};

    if (MODE === "hang") {
      // Never respond — exercises the AbortSignal -> child.kill() path.
      return;
    }

    if (MODE === "malformed") {
      process.stdout.write("not-json-at-all{{{\n");
      return;
    }

    if (MODE === "error") {
      send({
        jsonrpc: "2.0",
        id: msg.id,
        error: { code: -32000, message: "mock broker error" },
      });
      return;
    }

    if (MODE === "mcp-error") {
      // No top-level `error` — a WELL-FORMED response whose `result` is
      // MCP's own tool-execution-failure shape, matching the real broker
      // (AC-WIRE-1).
      send({
        jsonrpc: "2.0",
        id: msg.id,
        result: {
          content: [{ type: "text", text: "mock broker mcp-error: tool execution failed" }],
          isError: true,
        },
      });
      return;
    }

    if (MODE === "sentinel") {
      const sentinel = process.env.SENTINEL_TOKEN || "SENTINEL-9f3a-mock-broker";
      send({
        jsonrpc: "2.0",
        id: msg.id,
        result: {
          content: [
            { type: "text", text: JSON.stringify({ sentinelEcho: sentinel }) },
          ],
        },
      });
      return;
    }

    // "echo" (default): round-trip the exact tool name + arguments object
    // the caller sent, proving structured params (never argv) reached here.
    send({
      jsonrpc: "2.0",
      id: msg.id,
      result: {
        content: [
          { type: "text", text: JSON.stringify({ toolName: name, arguments: args }) },
        ],
      },
    });
    return;
  }

  // Unknown method: a structured JSON-RPC error, never a crash — mirrors the
  // never-raise posture of the real Python brokers.
  send({
    jsonrpc: "2.0",
    id: msg.id,
    error: { code: -32601, message: `mock broker: unknown method "${msg.method}"` },
  });
});
