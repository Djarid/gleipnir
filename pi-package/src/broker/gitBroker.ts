/**
 * gitBroker.ts — SRP: broker-SPECIFIC registration of the four git broker
 * tools, and nothing else (`.gleipnir/plans/pi-dev-replatform-s6.md`,
 * Design Principles Boundary A).
 *
 * Defines the 4 `gleipnir-git_<tool>` pi custom tools + their `Type.Object`
 * parameter schemas (mirroring `src/gleipnir/broker/git/mcp_server.py`'s
 * signatures verbatim, idiom-table row 3) + the git spawn spec
 * (`python -m gleipnir.broker.git.mcp_server`), delegating the actual
 * MCP-over-stdio relay to `mcpStdioClient.ts`. Holds NO JSON-RPC framing of
 * its own — it calls `relayToolCall`.
 *
 * Credential isolation (D-S6-3/D-S6-P2, idiom-table row 5): the git broker
 * needs NO credential env at all — git push/pull credentials are AMBIENT
 * (the operator's git credential helper / SSH agent / `~/.git-credentials`),
 * reached only by the SPAWNED git subprocess. `gitSpawnEnv()` copies ONLY a
 * baseline of non-credential system vars (by NAME, via `pickEnv` — never
 * read into an inspected/branched-on local) so the child can actually run
 * `python`/`git` and reach those ambient credentials itself; no token or
 * platform-credential env-var name (git or pm platform alike, or any other
 * secret-shaped name) ever appears in this module (AC-CRED-1).
 *
 * Relay-passes-structured-params-only (D-S6-5 Boundary C, AC-RELAY-1): every
 * `execute` below hands its `params` object straight to `relayToolCall` as
 * the MCP `tools/call` "arguments" — never reshaped into a raw command-line
 * vector. The broker's own Python-side `_run_git` hook-bypass screen remains
 * the sole authority; this module adds no policy of its own.
 *
 * `textResult()`/`toToolResult()`/`ToolDefinition` are shared with
 * `pmBroker.ts` via `./toolResult.ts` (SOLID/DRY finding, quality review of
 * the S6 broker slice) — this module no longer defines its own copies.
 */

import type { ExtensionAPI, AgentToolResult } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import { relayToolCall, pickEnv, type SpawnSpec } from "./mcpStdioClient.ts";
import { toToolResult, type ToolDefinition } from "./toolResult.ts";
import { GIT_BROKER_TOOLS } from "../roleTable.ts";

/** Baseline, non-credential system vars the spawned `python -m
 * gleipnir.broker.git.mcp_server` child needs to run at all and to reach
 * AMBIENT git credentials on its own (SSH agent socket, the user's
 * `~/.git-credentials` under `HOME`, `git`/`python` resolution via `PATH`).
 * Deliberately contains NO token/secret-shaped name (AC-CRED-1). */
const GIT_BASELINE_ENV_NAMES: readonly string[] = [
  "PATH",
  "HOME",
  "LANG",
  "LC_ALL",
  "SSH_AUTH_SOCK",
  "SSH_AGENT_PID",
  "TMPDIR",
  "USER",
  "PYTHONPATH",
  "VIRTUAL_ENV",
];

/** The git broker's spawn spec: NO credential-bearing env at all (D-S6-3).
 * Exported so `broker.test.ts` can assert AC-CRED-1 directly against the
 * spec's `env`, not against a narrative claim. */
export function buildGitSpawnSpec(): SpawnSpec {
  return {
    command: "python",
    args: ["-m", "gleipnir.broker.git.mcp_server"],
    env: pickEnv(GIT_BASELINE_ENV_NAMES),
  };
}

/** The Python tool name (the MCP `tools/call` "name") each concrete
 * `gleipnir-git_<tool>` custom tool relays to — the git `mcp_server.py`
 * function name verbatim (idiom-table row 1). Indexed by position against
 * `GIT_BROKER_TOOLS` (roleTable.ts) so the pi-facing name and the relayed
 * Python tool name are both derived from ONE ordered list, never
 * hand-duplicated. */
const GIT_PYTHON_TOOL_NAMES: readonly string[] = [
  "git_status",
  "git_diff",
  "commit_changes",
  "push_current_branch",
];

/** Parameter schemas mirroring `mcp_server.py`'s tool signatures verbatim
 * (idiom-table row 3). Every Python default-valued parameter is
 * `Type.Optional` here — the pi caller may omit it, exactly as the Python
 * side treats an omitted/empty value. */
const GIT_STATUS_PARAMS = Type.Object({
  repo_dir: Type.Optional(Type.String()),
});

const GIT_DIFF_PARAMS = Type.Object({
  staged: Type.Optional(Type.Boolean()),
  target: Type.Optional(Type.String()),
  file: Type.Optional(Type.String()),
  repo_dir: Type.Optional(Type.String()),
});

const COMMIT_CHANGES_PARAMS = Type.Object({
  message: Type.String(),
  files: Type.Optional(Type.String()),
  repo_dir: Type.Optional(Type.String()),
});

const PUSH_CURRENT_BRANCH_PARAMS = Type.Object({
  repo_dir: Type.Optional(Type.String()),
});

const GIT_PARAM_SCHEMAS = [
  GIT_STATUS_PARAMS,
  GIT_DIFF_PARAMS,
  COMMIT_CHANGES_PARAMS,
  PUSH_CURRENT_BRANCH_PARAMS,
] as const;

const GIT_TOOL_LABELS: readonly string[] = [
  "Git status (read-only, broker-relayed)",
  "Git diff (read-only, broker-relayed)",
  "Commit staged changes (broker-relayed, secret-scanned)",
  "Push the current branch (broker-relayed, no force-push path exists)",
];

const GIT_TOOL_DESCRIPTIONS: readonly string[] = [
  "Relays to the git broker's git_status tool: repository status (branch, protection, staged/unstaged/untracked files).",
  "Relays to the git broker's git_diff tool: diff output (unstaged by default; staged/target/file supported).",
  "Relays to the git broker's commit_changes tool: stages files, runs an always-on secret-scan over the staged diff, and commits on a pass.",
  "Relays to the git broker's push_current_branch tool: pushes the current branch to origin (no force-push parameter exists).",
];

/**
 * Build the 4 concrete `gleipnir-git_<tool>` tool definitions. Each `name`
 * EQUALS the corresponding concrete DATA row `roleTable.ts` lists in
 * `GIT_BROKER_TOOLS` (D-S6-1b) — sourced from that SAME exported constant,
 * never hand-duplicated, so the registered tool name and the table entry
 * can never drift apart (AC-BROKER-1). Exported (not just the default
 * extension entrypoint) so `broker.test.ts` can introspect the definitions
 * directly without needing a live `ExtensionAPI`.
 */
export function buildGitBrokerTools(): ToolDefinition[] {
  return GIT_BROKER_TOOLS.map((name, index) => {
    const pythonToolName = GIT_PYTHON_TOOL_NAMES[index];
    return {
      name,
      label: GIT_TOOL_LABELS[index],
      description: GIT_TOOL_DESCRIPTIONS[index],
      parameters: GIT_PARAM_SCHEMAS[index],
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal: AbortSignal,
        _onUpdate: (update: unknown) => void,
        _ctx: unknown,
      ): Promise<AgentToolResult<void>> {
        const structured = await relayToolCall(
          buildGitSpawnSpec(),
          pythonToolName,
          params,
          signal,
        );
        return toToolResult(structured);
      },
    };
  });
}

export default function gitBroker(pi: ExtensionAPI): void {
  for (const tool of buildGitBrokerTools()) {
    pi.registerTool(tool);
  }
}
