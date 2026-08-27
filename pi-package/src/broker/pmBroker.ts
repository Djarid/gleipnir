/**
 * pmBroker.ts — SRP: broker-SPECIFIC registration of the four pm broker
 * tools, and nothing else (`.gleipnir/plans/pi-dev-replatform-s6.md`,
 * Design Principles Boundary A).
 *
 * Defines the 4 `gleipnir-pm_<tool>` pi custom tools + their `Type.Object`
 * parameter schemas (mirroring `src/gleipnir/broker/pm/mcp_server.py`'s
 * signatures verbatim, idiom-table row 3) + the pm spawn spec
 * (`python -m gleipnir.broker.pm.mcp_server`), delegating the actual
 * MCP-over-stdio relay to `mcpStdioClient.ts`. Holds NO JSON-RPC framing of
 * its own — it calls `relayToolCall`.
 *
 * Credential isolation (D-S6-3/D-S6-P2, idiom-table row 4): the pm broker's
 * token is read INSIDE the spawned child (`platform.py::get_token` ->
 * `os.environ.get(...)` on the platform's token env-var name, confirmed by
 * the plan's Trace item 2). This module passes the two token env-var NAMES
 * (below) through to the child BY NAME ONLY, via `pickEnv` (a pure, generic,
 * name-based forwarding copy) — it NEVER dereferences either token's value
 * straight off `process.env` into a local it inspects, logs, branches on, or
 * forwards as a literal; only `pickEnv`'s generic by-name copy ever touches
 * `process.env`. The token's readable lifetime is confined to the broker
 * child's own `os.environ` (Boundary B / AC-CRED-2).
 *
 * Relay-passes-structured-params-only (D-S6-5 Boundary C, AC-RELAY-1): every
 * `execute` below hands its `params` object straight to `relayToolCall` as
 * the MCP `tools/call` "arguments" — never assembled into any other shape.
 *
 * `textResult()`/`toToolResult()`/`ToolDefinition` are shared with
 * `gitBroker.ts` via `./toolResult.ts` (SOLID/DRY finding, quality review of
 * the S6 broker slice) — this module no longer defines its own copies.
 */

import type { ExtensionAPI, AgentToolResult } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import { relayToolCall, pickEnv, type SpawnSpec } from "./mcpStdioClient.ts";
import { toToolResult, type ToolDefinition } from "./toolResult.ts";
import { PM_BROKER_TOOLS } from "../roleTable.ts";

/** Baseline, non-credential system vars the spawned `python -m
 * gleipnir.broker.pm.mcp_server` child needs to run at all (it also shells
 * out to `git remote get-url origin` to detect the platform). */
const PM_BASELINE_ENV_NAMES: readonly string[] = [
  "PATH",
  "HOME",
  "LANG",
  "LC_ALL",
  "TMPDIR",
  "USER",
  "PYTHONPATH",
  "VIRTUAL_ENV",
];

/** The ONLY two credential-bearing names ever named in this module — passed
 * BY NAME ONLY (D-S6-P2, confirmed against `platform.py`'s
 * `_TOKEN_ENV_VARS`). `pickEnv` copies their VALUE from `process.env` into
 * the spawn env object as a pure forwarding operation; this module itself
 * never assigns either value to a local it inspects/logs/branches on. */
const PM_CREDENTIAL_ENV_NAMES: readonly string[] = ["GITHUB_TOKEN", "GITLAB_TOKEN"];

/** The pm broker's spawn spec: baseline system vars + the two token NAMES,
 * by-name-only passthrough (D-S6-3/D-S6-P2). Exported so `broker.test.ts`
 * can assert AC-CRED-2 directly against the spec's `env` keys (which names
 * are present) without ever needing to read a real token value. */
export function buildPmSpawnSpec(): SpawnSpec {
  return {
    command: "python",
    args: ["-m", "gleipnir.broker.pm.mcp_server"],
    env: pickEnv([...PM_BASELINE_ENV_NAMES, ...PM_CREDENTIAL_ENV_NAMES]),
  };
}

/** The Python tool name (the MCP `tools/call` "name") each concrete
 * `gleipnir-pm_<tool>` custom tool relays to — the pm `mcp_server.py`
 * function name verbatim (idiom-table row 1). Indexed by position against
 * `PM_BROKER_TOOLS` (roleTable.ts), never hand-duplicated. */
const PM_PYTHON_TOOL_NAMES: readonly string[] = [
  "issue_create",
  "issue_update",
  "issue_comment",
  "issue_close",
];

/** Parameter schemas mirroring `mcp_server.py`'s tool signatures verbatim
 * (idiom-table row 3). */
const ISSUE_CREATE_PARAMS = Type.Object({
  title: Type.String(),
  body: Type.Optional(Type.String()),
  repo_dir: Type.Optional(Type.String()),
});

const ISSUE_UPDATE_PARAMS = Type.Object({
  issue_id: Type.String(),
  title: Type.Optional(Type.String()),
  body: Type.Optional(Type.String()),
  state: Type.Optional(Type.String()),
  repo_dir: Type.Optional(Type.String()),
});

const ISSUE_COMMENT_PARAMS = Type.Object({
  issue_id: Type.String(),
  body: Type.String(),
  repo_dir: Type.Optional(Type.String()),
});

const ISSUE_CLOSE_PARAMS = Type.Object({
  issue_id: Type.String(),
  repo_dir: Type.Optional(Type.String()),
});

const PM_PARAM_SCHEMAS = [
  ISSUE_CREATE_PARAMS,
  ISSUE_UPDATE_PARAMS,
  ISSUE_COMMENT_PARAMS,
  ISSUE_CLOSE_PARAMS,
] as const;

const PM_TOOL_LABELS: readonly string[] = [
  "Create an issue (broker-relayed)",
  "Update an issue (broker-relayed)",
  "Comment on an issue (broker-relayed)",
  "Close an issue (broker-relayed)",
];

const PM_TOOL_DESCRIPTIONS: readonly string[] = [
  "Relays to the pm broker's issue_create tool: creates an issue on the platform detected from the origin remote.",
  "Relays to the pm broker's issue_update tool: updates title/body/state on an existing issue.",
  "Relays to the pm broker's issue_comment tool: adds a comment to an issue.",
  "Relays to the pm broker's issue_close tool: closes an issue.",
];

/**
 * Build the 4 concrete `gleipnir-pm_<tool>` tool definitions. Each `name`
 * EQUALS the corresponding concrete DATA row `roleTable.ts` lists in
 * `PM_BROKER_TOOLS` (D-S6-1b) — sourced from that SAME exported constant,
 * never hand-duplicated (AC-BROKER-1).
 */
export function buildPmBrokerTools(): ToolDefinition[] {
  return PM_BROKER_TOOLS.map((name, index) => {
    const pythonToolName = PM_PYTHON_TOOL_NAMES[index];
    return {
      name,
      label: PM_TOOL_LABELS[index],
      description: PM_TOOL_DESCRIPTIONS[index],
      parameters: PM_PARAM_SCHEMAS[index],
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal: AbortSignal,
        _onUpdate: (update: unknown) => void,
        _ctx: unknown,
      ): Promise<AgentToolResult<void>> {
        const structured = await relayToolCall(
          buildPmSpawnSpec(),
          pythonToolName,
          params,
          signal,
        );
        return toToolResult(structured);
      },
    };
  });
}

export default function pmBroker(pi: ExtensionAPI): void {
  for (const tool of buildPmBrokerTools()) {
    pi.registerTool(tool);
  }
}
