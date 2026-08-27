/**
 * mcpStdioClient.ts — SRP: the GENERIC MCP-over-stdio JSON-RPC transport,
 * and nothing else (`.gleipnir/plans/pi-dev-replatform-s6.md`, Design
 * Principles Boundary A).
 *
 * Hand-rolled, zero-dependency (D-S6-P4 / D-S6-1, `runtime-and-deps.md`):
 * implements ONLY the bounded subset the fixed 4-tool-per-broker surfaces
 * need — one `initialize` handshake + one `tools/call` per invocation, over
 * a spawned child's stdin/stdout, newline-delimited JSON-RPC 2.0 framing.
 * NO `@modelcontextprotocol/sdk`, NO `pi-mcp-extension`, NO pagination,
 * `tools/list`, reconnection, health-checks, SSE, or streamable-HTTP — see
 * the plan's "Hand-rolled feasibility" section for why this bounded subset
 * suffices.
 *
 * PURITY (AC-PURITY): imports ONLY `node:child_process`. This module knows
 * NOTHING about which broker, which tool, or any credential/env-var name —
 * `pickEnv` is a generic name-based env-copy utility; the CALLER (a broker
 * module) supplies the concrete allowlist of names. One reason to change:
 * the MCP-stdio wire/transport itself.
 *
 * Never throws out of `relayToolCall` for an expected failure mode (spawn
 * failure, child exit, malformed JSON, a top-level JSON-RPC `error`, OR a
 * well-formed response whose `result.isError === true` — the shape the REAL
 * broker actually uses for a tool-execution failure, confirmed by
 * AC-WIRE-1; see `isMcpErrorResult` below) — every one of those becomes a
 * `StructuredResult` with `success: false`, mirroring the Python brokers'
 * own never-raise posture (idiom-table row 6).
 *
 * The exact wire subset (the `initialize` `protocolVersion`, whether
 * `notifications/initialized` must precede `tools/call`, and the response
 * framing) is pinned against a REAL FastMCP-stdio broker by AC-WIRE-1
 * (`tests/test_broker_wire_protocol.py`, run under `[profile.broker]` — see
 * the plan's "Test-harness constraint" section) and proven against a MOCK
 * broker by `mcpStdioClient.test.ts` (`[profile.pi]`).
 */

import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";

/** A spawn specification for one broker child process. Carries NOTHING
 * broker-specific by construction — the CALLER (a broker module) decides
 * `command`/`args`/`env`; this module only ever spawns exactly what it is
 * told. */
export interface SpawnSpec {
  readonly command: string;
  readonly args: readonly string[];
  /** Explicit env for the child (never `undefined`-defaults-to-full-inherit
   * in practice — callers build this via `pickEnv` so the passthrough is
   * always an explicit, auditable, by-name allowlist; see D-S6-P2). */
  readonly env?: Readonly<Record<string, string | undefined>>;
  readonly cwd?: string;
}

/** The structured result every `relayToolCall` call resolves to — success
 * or a structured error, never an unhandled throw (idiom-table row 6). */
export interface StructuredResult {
  readonly success: boolean;
  /** The extracted tool result (see `extractResultText`), present on success. */
  readonly result?: string;
  /** A human-readable failure reason, present on failure. */
  readonly error?: string;
}

/** Generic, broker-agnostic env-copy utility (Boundary A): copies ONLY the
 * named variables that are present in the current process env, by NAME,
 * into a fresh object — a pure forwarding copy, never a value the caller
 * reads into an inspected/branched-on local (D-S6-3/D-S6-P2). This function
 * holds no knowledge of WHICH names are credential-bearing; the broker
 * module supplies the concrete allowlist (baseline system vars for git,
 * baseline + the two token names for pm). */
export function pickEnv(names: readonly string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const name of names) {
    const value = process.env[name];
    if (value !== undefined) {
      out[name] = value;
    }
  }
  return out;
}

/** The MCP protocol version this client's `initialize` request advertises.
 * Pinned by AC-WIRE-1 against the real FastMCP-stdio broker (bounded
 * correctness detail, D-S6-P4 §Trace "Hand-rolled feasibility" — not a
 * design tradeoff). */
export const PROTOCOL_VERSION = "2024-11-05";

/** The client's self-identification, sent in every `initialize` request. */
const CLIENT_INFO = { name: "gleipnir-broker-relay", version: "0.1.0" } as const;

let nextRequestId = 1;

/** Test-only reset so the module-scope id counter does not leak assertions
 * about specific id VALUES across test cases (mirrors `depth.ts`'s
 * `resetDepth()` idiom). The id counter's absolute value is never
 * load-bearing for correctness — only that request/response ids match. */
export function resetRequestIdForTestOnly(): void {
  nextRequestId = 1;
}

function allocateRequestId(): number {
  const id = nextRequestId;
  nextRequestId += 1;
  return id;
}

/** A minimal, line-buffered async reader over a Node `Readable` stream:
 * splits on `\n`, buffers partial lines across `data` chunks, and lets a
 * caller `await` the next complete line. Newline-delimited framing (not
 * `Content-Length`) per the MCP stdio transport convention — confirmed
 * against the real broker by AC-WIRE-1. */
function createLineReader(stream: NodeJS.ReadableStream): {
  nextLine(): Promise<string>;
} {
  let buffer = "";
  const pendingLines: string[] = [];
  const waiters: Array<(line: string | null) => void> = [];
  let ended = false;

  const flushBuffer = () => {
    let idx = buffer.indexOf("\n");
    while (idx >= 0) {
      const line = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 1);
      if (waiters.length > 0) {
        const waiter = waiters.shift()!;
        waiter(line);
      } else {
        pendingLines.push(line);
      }
      idx = buffer.indexOf("\n");
    }
  };

  stream.on("data", (chunk: Buffer | string) => {
    buffer += typeof chunk === "string" ? chunk : chunk.toString("utf8");
    flushBuffer();
  });
  stream.on("end", () => {
    ended = true;
    while (waiters.length > 0) {
      const waiter = waiters.shift()!;
      waiter(null);
    }
  });

  return {
    nextLine(): Promise<string> {
      if (pendingLines.length > 0) {
        return Promise.resolve(pendingLines.shift()!);
      }
      if (ended) {
        return Promise.reject(new Error("mcpStdioClient: broker child closed its stdout"));
      }
      return new Promise((resolve, reject) => {
        waiters.push((line) => {
          if (line === null) {
            reject(new Error("mcpStdioClient: broker child closed its stdout"));
          } else {
            resolve(line);
          }
        });
      });
    },
  };
}

function writeMessage(child: ChildProcessWithoutNullStreams, message: unknown): void {
  child.stdin.write(JSON.stringify(message) + "\n");
}

interface JsonRpcResponseOutcome {
  readonly result?: unknown;
  readonly error?: string;
}

/** True when a WELL-FORMED (no top-level JSON-RPC `error`) response's
 * `result` is itself the MCP tool-execution-failure shape:
 * `{content:[...], isError:true}`. Confirmed against the REAL FastMCP-stdio
 * broker by AC-WIRE-1 (`tests/test_broker_wire_protocol.py`,
 * `test_ac_wire_1_unknown_tool_is_a_structured_error_not_a_crash`) — a tool
 * name FastMCP does not recognise (and, by the same mechanism, any tool
 * execution failure) is reported via `result.isError`, NOT a top-level
 * JSON-RPC `error` object. Checking only `msg.error` (as this client did
 * before this check existed) silently reports such a failure back to the
 * caller as a success carrying the error text as its "result" — exactly the
 * push/commit/issue-op-failure-masked-as-success gap this function closes. */
function isMcpErrorResult(result: unknown): boolean {
  return (
    result !== null &&
    typeof result === "object" &&
    (result as { isError?: unknown }).isError === true
  );
}

/** Read lines until one carries the matching response `id` (tolerating
 * interleaved notifications, which carry no `id`, by skipping them). A
 * malformed line is a structured error, never an unhandled throw
 * (AC-CLIENT-4). */
async function readResponseFor(
  reader: { nextLine(): Promise<string> },
  id: number,
): Promise<JsonRpcResponseOutcome> {
  for (;;) {
    let line: string;
    try {
      line = await reader.nextLine();
    } catch (err) {
      return { error: (err as Error)?.message ?? String(err) };
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch {
      return { error: `mcpStdioClient: malformed JSON-RPC line from broker: ${line}` };
    }

    if (typeof parsed !== "object" || parsed === null) {
      return { error: `mcpStdioClient: non-object JSON-RPC line from broker: ${line}` };
    }
    const msg = parsed as { id?: unknown; result?: unknown; error?: unknown };
    if (msg.id !== id) {
      // Not our response (e.g. an interleaved notification/unrelated reply)
      // — keep reading rather than treating it as an error.
      continue;
    }
    if (msg.error !== undefined) {
      return {
        error:
          typeof msg.error === "string" ? msg.error : JSON.stringify(msg.error),
      };
    }
    // ADDITIONAL check (does not replace the top-level `error` handling
    // above): a well-formed response whose `result` carries MCP's OWN
    // tool-execution-failure shape (`result.isError === true`) is treated
    // the same as a client-level failure — never surfaced to the caller as
    // `{success: true, result: <error text>}`.
    if (isMcpErrorResult(msg.result)) {
      return { error: extractResultText(msg.result) };
    }
    return { result: msg.result };
  }
}

/** Extract human/LLM-readable text from an MCP `tools/call` result. Real
 * MCP tool results wrap their payload as `{ content: [{type:"text",
 * text}, ...] }` (confirmed by AC-WIRE-1 against the real broker); this
 * client returns the joined text verbatim, falling back to a plain JSON
 * stringification of the raw result for any other shape (defensive, never
 * a throw). This is generic MCP wire-shape knowledge, not broker-specific
 * knowledge — no tool name or credential name appears here (Boundary A). */
function extractResultText(result: unknown): string {
  if (
    result !== null &&
    typeof result === "object" &&
    Array.isArray((result as { content?: unknown }).content)
  ) {
    const texts = (result as { content: unknown[] }).content
      .filter(
        (item): item is { type: string; text: string } =>
          item !== null &&
          typeof item === "object" &&
          (item as { type?: unknown }).type === "text" &&
          typeof (item as { text?: unknown }).text === "string",
      )
      .map((item) => item.text);
    if (texts.length > 0) {
      return texts.join("\n");
    }
  }
  return JSON.stringify(result);
}

async function performHandshakeAndCall(
  child: ChildProcessWithoutNullStreams,
  toolName: string,
  params: Record<string, unknown>,
): Promise<StructuredResult> {
  const reader = createLineReader(child.stdout);

  const initId = allocateRequestId();
  writeMessage(child, {
    jsonrpc: "2.0",
    id: initId,
    method: "initialize",
    params: {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: CLIENT_INFO,
    },
  });

  const initOutcome = await readResponseFor(reader, initId);
  if (initOutcome.error !== undefined) {
    return { success: false, error: `initialize failed: ${initOutcome.error}` };
  }

  // A notification (no `id`) — per the MCP stdio convention, sent after a
  // successful `initialize` response and before any `tools/call`. Pinned by
  // AC-WIRE-1 against the real broker; sending it unconditionally is safe
  // even if a given server tolerates its absence (it is a notification, so
  // the server never sends a response to it either way).
  writeMessage(child, { jsonrpc: "2.0", method: "notifications/initialized" });

  const callId = allocateRequestId();
  writeMessage(child, {
    jsonrpc: "2.0",
    id: callId,
    method: "tools/call",
    // Structured params ONLY — a `{name, arguments}` object, never a raw
    // argv array (D-S6-5 Boundary C / AC-RELAY-1). The broker's own
    // Python-side `_run_git` hook-bypass screen remains the sole authority
    // over argv-shaped flags because this client never constructs one.
    params: { name: toolName, arguments: params },
  });

  const callOutcome = await readResponseFor(reader, callId);
  if (callOutcome.error !== undefined) {
    return { success: false, error: callOutcome.error };
  }
  return { success: true, result: extractResultText(callOutcome.result) };
}

/**
 * Spawn `spec`'s child, perform one `initialize` + `tools/call("toolName",
 * params)` round-trip, and resolve to a `StructuredResult` — success or a
 * structured error, never an unhandled throw. `signal` is wired to kill the
 * child on abort (`child.kill("SIGTERM")`); the child is ALSO killed in a
 * `finally` on ordinary completion or any failure, so no orphaned process
 * survives a call (AC-CLIENT-2).
 *
 * Spawn-per-call (D-S6-P3): every invocation gets its own child + its own
 * stdio pipe. This function holds no broker-specific knowledge — `spec`,
 * `toolName`, and `params` are entirely caller-supplied (Boundary A).
 */
export async function relayToolCall(
  spec: SpawnSpec,
  toolName: string,
  params: Record<string, unknown>,
  signal: AbortSignal,
): Promise<StructuredResult> {
  let child: ChildProcessWithoutNullStreams;
  try {
    child = spawn(spec.command, [...spec.args], {
      cwd: spec.cwd,
      env: spec.env as NodeJS.ProcessEnv | undefined,
      stdio: ["pipe", "pipe", "pipe"],
    }) as ChildProcessWithoutNullStreams;
  } catch (err) {
    // Some platforms/commands throw synchronously on an unresolvable
    // command; most report it async via the 'error' event below. Both
    // paths resolve to the same structured-error shape.
    return {
      success: false,
      error: `mcpStdioClient: spawn failed: ${(err as Error)?.message ?? String(err)}`,
    };
  }

  const spawnErrorPromise = new Promise<never>((_resolve, reject) => {
    child.once("error", (err: Error) => {
      reject(new Error(`mcpStdioClient: spawn failed: ${err.message}`));
    });
  });

  const onAbort = () => {
    child.kill("SIGTERM");
  };
  if (signal.aborted) {
    onAbort();
  } else {
    signal.addEventListener("abort", onAbort, { once: true });
  }

  try {
    const outcome = await Promise.race([
      spawnErrorPromise,
      performHandshakeAndCall(child, toolName, params),
    ]);
    return outcome;
  } catch (err) {
    return { success: false, error: (err as Error)?.message ?? String(err) };
  } finally {
    signal.removeEventListener("abort", onAbort);
    if (child.exitCode === null && child.signalCode === null) {
      child.kill("SIGTERM");
    }
    child.stdin.end();
  }
}
