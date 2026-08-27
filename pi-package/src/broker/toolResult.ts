/**
 * toolResult.ts — SRP: the shared pi-tool-result SHAPE helpers the two
 * broker modules (`gitBroker.ts`/`pmBroker.ts`) both need, and nothing else
 * (`.gleipnir/plans/pi-dev-replatform-s6.md`, Design Principles Boundary A).
 *
 * Extracted from `gitBroker.ts`/`pmBroker.ts`, where `textResult()`,
 * `toToolResult()`, and `ToolDefinition` were each byte-identical
 * triplicated/duplicated copies (SOLID/DRY finding, quality review of the
 * S6 broker slice) — this module is the ONE place they are defined now.
 *
 * Deliberately NOT inside `mcpStdioClient.ts`: that module is the GENERIC
 * MCP-over-stdio transport and must stay ignorant of pi-side tool-result
 * shapes (`AgentToolResult`) or `ToolDefinition` — it knows only
 * `StructuredResult` (Boundary A). This module sits on the OTHER side of
 * that boundary: it knows the pi-facing shapes, and converts
 * `mcpStdioClient.ts`'s `StructuredResult` into them, but holds no
 * broker-specific tool names, credential names, or spawn logic of its own.
 */

import type { AgentToolResult } from "@earendil-works/pi-coding-agent";
import type { TSchema } from "typebox";

import type { StructuredResult } from "./mcpStdioClient.ts";

/** Wrap `text` as the `AgentToolResult<void>` shape every broker tool's
 * `execute` resolves to — human/LLM-readable text in `content`, `details`
 * left `undefined` (matching the `void` result-type instantiation; see
 * `delegate.ts`'s own `textResult` header comment for the fuller
 * `tsc --noEmit` rationale, which still applies here). */
export function textResult(text: string): AgentToolResult<void> {
  return { content: [{ type: "text", text }], details: undefined };
}

/** Convert a `StructuredResult` from `mcpStdioClient.ts` into the same
 * `AgentToolResult<void>` shape — never an unhandled throw (idiom-table row
 * 6). Shared by both broker modules so a git-broker and a pm-broker tool
 * report a relay failure identically. */
export function toToolResult(structured: StructuredResult): AgentToolResult<void> {
  if (structured.success) {
    return textResult(structured.result ?? "");
  }
  return textResult(`error: ${structured.error ?? "unknown broker error"}`);
}

/** The shape both `buildGitBrokerTools()`/`buildPmBrokerTools()` build —
 * exported from one place so a `pi.registerTool` shape change is a
 * one-file edit, not a hand-synced pair. */
export interface ToolDefinition {
  readonly name: string;
  readonly label: string;
  readonly description: string;
  readonly parameters: TSchema;
  execute(
    toolCallId: string,
    params: Record<string, unknown>,
    signal: AbortSignal,
    onUpdate: (update: unknown) => void,
    ctx: unknown,
  ): Promise<AgentToolResult<void>>;
}
