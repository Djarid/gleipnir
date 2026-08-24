/**
 * delegate.ts — SRP: construct + bound + run a child session, and nothing
 * else (does NOT decide in-process-vs-RPC isolation — that is Open-Q1,
 * revisited at S3/S6; folding that choice in here would be a second
 * responsibility per the plan's Design Principles and must be escalated,
 * not baked in).
 *
 * ============================================================================
 * D6 — SETTLED (plan Decision D6, Assemble step 6, AC-9 / AC-9-E2E)
 * ============================================================================
 *
 * THE QUESTION: does a freshly-created `createAgentSession` child inherit
 * the parent extension's `tool_call` hook automatically, or does it need
 * explicit `bindExtensions`/`resourceLoader`/`extensionFactories` wiring?
 *
 * VERDICT: no auto-inherit path exists. The SDK's real `emitToolCall`
 * (`session._extensionRunner.emitToolCall`, verbatim the function
 * `_installAgentToolHooks()` wires to `agent.beforeToolCall` for every real,
 * model-driven tool call) iterates only `this.extensions` — i.e. only the
 * extensions the CHILD's *own* `resourceLoader` loaded. There is no code
 * path anywhere in the SDK that reaches back into a parent session's
 * extensions. Confirmed by direct introspection of the real
 * `@earendil-works/pi-coding-agent` package inside the
 * `bin/gleipnir-sandbox --profile pi` container (`--network=none`,
 * pre-installed peers, no host copy).
 *
 * WHAT THIS MEANS FOR THE ENGINEERING CHOICE ALREADY MADE HERE: this module
 * always explicitly constructs the child's resource loader with
 * `extensionFactories: [enforcementExtension]` — the very same
 * `enforcement.ts` module the parent loaded — so the child is enforced by
 * construction. Given the verdict above, that wiring is NOT a defensive
 * "redundant but harmless" fallback against an unknown branch (as this
 * header once speculated); it is the ONLY mechanism by which the child gets
 * enforced. A child built without it would have an empty
 * `_extensionRunner.extensions` and every tool call would silently pass
 * (`emitToolCall` returning `undefined` unconditionally).
 *
 * PROOF: `AC-9` (`delegate.test.ts`) proves the wiring is correct at the
 * module level (the re-wired `enforcement.ts` blocks a denied tool for the
 * child's role) using a fake minimal `ExtensionAPI`. `AC-9-E2E`
 * (`delegate.test.ts`) goes further and proves it end-to-end against a
 * REAL `createAgentSession` child built by this module's own unmodified
 * `execute`: real `DefaultResourceLoader` + `extensionFactories` wiring,
 * real `resourceLoader.reload()`, real `createAgentSession`, and the real
 * `_extensionRunner.emitToolCall` dispatch — the only stubbed call is
 * `AgentSession.prototype.prompt` itself, restored in `finally`.
 *
 * THE ONE NAMED RESIDUAL GAP (still real, not closed by the above): a
 * fully model-driven, live conversational turn — no `prompt` stub anywhere
 * — cannot be exercised in this sandbox. `createAgentSession`'s own body
 * calls `ModelRuntime.create({ authPath, modelsPath })` and
 * `findInitialModel(...)` against `~/.pi/agent`/provider auth before a real
 * `session.prompt(...)` can run a model turn, and that is unreachable under
 * `--network=none` with no configured provider credentials in-container.
 * Everything up to and including the real `tool_call` dispatch pipeline is
 * now covered by `AC-9-E2E`; only the live-model-turn step beyond that
 * remains untested, and it is a network/auth limitation, not a
 * wiring-correctness one. See `pi-package/README.md` ("D6 finding") and
 * `delegate.test.ts`'s "D6 VERDICT FROM THIS TEST" comment for the same
 * account in full.
 * ============================================================================
 */

import type {
  ExtensionAPI,
  AgentToolResult,
} from "@earendil-works/pi-coding-agent";
// VERIFIED (build-mode, in-container `tsc --noEmit --profile pi`, this session):
// `@earendil-works/pi-coding-agent` exports `createAgentSession`,
// `SessionManager` (with `.inMemory(cwd?)`), and `DefaultResourceLoader`.
// Confirmed against the shipped .d.ts (core/sdk.d.ts, core/session-manager.d.ts,
// core/resource-loader.d.ts) — the SDK's own docstring example uses exactly
// `new DefaultResourceLoader({cwd, agentDir, ...})` + `loader.reload()` +
// `createAgentSession({resourceLoader, sessionManager: SessionManager.inMemory()})`.
import {
  createAgentSession,
  SessionManager,
  DefaultResourceLoader,
  getAgentDir,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import { ROLE_ALLOW_SETS, type RoleName } from "./roleTable.ts";
import { popActiveRole, pushActiveRole } from "./activeRole.ts";
import { DepthCapExceededError, withDepthGuard } from "./depth.ts";
import enforcementExtension from "./enforcement.ts";

/** Resolve a role's allow-set to the plain tool-name array a child session's
 * `tools` option expects (DRY: the allow-set is defined ONCE in roleTable.ts;
 * this is the only place it is projected into pi's `tools` shape). */
export function resolveChildTools(role: RoleName): string[] {
  const allowSet = ROLE_ALLOW_SETS[role];
  if (!allowSet) {
    throw new Error(`delegate: unknown role "${role}" has no allow-set`);
  }
  return [...allowSet];
}

export interface DelegateParams {
  role: RoleName;
  prompt: string;
}

/** DRY: both `execute` return paths (success and depth-cap refusal) must
 * resolve to the SAME `AgentToolResult<T>` (`pi-agent-core/dist/types.d.ts`)
 * instantiation, not a raw value or an ad hoc `{ error }` object — this is
 * the single place that shape is assembled.
 *
 * `registerTool`'s inferred result type for this tool (no explicit result
 * schema declared) is `AgentToolResult<void>` — confirmed by the in-container
 * `tsc --noEmit --profile pi` error when this helper was generic over `T`
 * and the two branches instantiated it differently (`void` vs
 * `{ error: string }`), which is not assignable to the single `void`
 * instantiation the SDK's `execute` signature requires. Both branches below
 * therefore return `AgentToolResult<void>` and carry their payload only in
 * `content` (human/LLM-readable text), not in `details` — `details` stays
 * `undefined`, matching `void`. */
function textResult(text: string): AgentToolResult<void> {
  return { content: [{ type: "text", text }], details: undefined };
}

export default function delegate(pi: ExtensionAPI): void {
  pi.registerTool({
    name: "delegate",
    label: "Delegate to a bounded child session",
    description:
      "Creates a role-bounded child agent session (depth-capped, enforcement-wired per D6) and runs a prompt in it.",
    parameters: Type.Object({
      role: Type.String(),
      prompt: Type.String(),
    }),
    async execute(
      _toolCallId: string,
      params: DelegateParams,
      _signal: AbortSignal,
      _onUpdate: (update: unknown) => void,
      _ctx: unknown,
    ) {
      const tools = resolveChildTools(params.role);

      try {
        return await withDepthGuard(async () => {
          pushActiveRole(params.role);
          try {
            // D6: explicit re-wiring, not an inheritance assumption — see
            // the module-level comment block above.
            const resourceLoader = new DefaultResourceLoader({
              cwd: process.cwd(),
              agentDir: getAgentDir(),
              extensionFactories: [enforcementExtension],
            });
            // Required: extensionFactories are only actually loaded once
            // `reload()` resolves — without this call the enforcement
            // extension would never be wired into the child, silently
            // making the D6 defensive re-registration a no-op.
            await resourceLoader.reload();

            const { session } = await createAgentSession({
              resourceLoader,
              sessionManager: SessionManager.inMemory(),
              tools,
              customTools: [],
            });

            try {
              const result = await session.prompt(params.prompt);
              // AgentToolResult<void> shape (pi-agent-core/dist/types.d.ts):
              // `session.prompt`'s resolved value is not assumed to already
              // be in that shape — it is summarised into `content`
              // unconditionally so this tool's return is always well-formed
              // regardless of what the child session resolves to. The
              // tool's inferred result type is `void` (see `textResult`
              // above), so the payload lives only in `content`, not
              // `details`.
              return textResult(
                typeof result === "string" ? result : JSON.stringify(result),
              );
            } finally {
              await session.dispose();
            }
          } finally {
            popActiveRole();
          }
        });
      } catch (err) {
        if (err instanceof DepthCapExceededError) {
          // Refuse gracefully with a clear reason (AC-6/AC-7) rather than an
          // unhandled throw — and still shaped as the same AgentToolResult<void>
          // instantiation as the success path (see `textResult` above).
          return textResult(err.message);
        }
        throw err;
      }
    },
  });
}
