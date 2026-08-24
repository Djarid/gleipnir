/**
 * enforcement.ts — SRP: translate ONE `tool_call` event into an allow/deny
 * decision, and nothing else. Consumes `roleTable.canUse` + `activeRole`
 * (Dependency Inversion: depends on the narrow `canUse(role, tool)`
 * function, not on `roleTable`'s internal data structure, so storage can
 * change in S2 without touching this hook).
 *
 * CRUX-1 API shape — per the plan's Link section, validated against the
 * shipped `examples/extensions/permission-gate.ts`:
 *   pi.on("tool_call", async (event, ctx) => {
 *     ...
 *     return { block: true, reason } | undefined;
 *   });
 * `event.toolName` and `ctx.hasUI` are the two confirmed fields this hook
 * reads. The parameter/return types below are intentionally left to be
 * inferred from `ExtensionAPI["on"]`'s own overload for the `"tool_call"`
 * event (imported only as a type) rather than hand-declared, so a mismatch
 * between this file and the peer package's real signature surfaces as a
 * `tsc` error in `bin/gleipnir-sandbox lint --profile pi` (the exact
 * verification tool this delegation could not reach this session — see
 * README "Capability wall" — rather than being silently masked by a
 * hand-rolled, possibly-wrong local type).
 *
 * Design Intent (falsifiable, restated from the plan): enforcement must be
 * a property of THIS code, not of any host permission map — no path
 * through this function may return anything other than `{ block: true }`
 * for a `toolName` outside the active role's allow-set.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import { canUse } from "./roleTable.ts";
import { getActiveRole, seedActiveRoleIfEmpty } from "./activeRole.ts";

/** The primary session's role. The top-level session IS the orchestrator, so
 * `session_start` seeds it (P4). Referenced from one constant so the seed
 * wiring and its test do not hand-duplicate the literal. */
export const PRIMARY_ROLE = "orchestrator";

/**
 * D5: demonstrate the shipped `ctx.hasUI` fail-closed branch as a
 * MECHANISM only (Open-Q2 — the fail-closed-vs-sink *policy* for gate-
 * bearing stages under non-interactive modes — stays open; this hook does
 * not decide it). A denied call always fails closed; when there is no UI to
 * escalate to, the reason string says so explicitly (AC-4 asserts the
 * reason mentions "no UI").
 */
export default function enforcement(pi: ExtensionAPI): void {
  // P4: seed the top-level active role at session start. Guarded
  // (seedActiveRoleIfEmpty) so a child createAgentSession's own session_start
  // cannot re-seed `orchestrator` over a delegate-pushed child role (AC-15).
  // Registered defensively: if the runtime does not emit `session_start` this
  // is an inert registration; the seed's guard logic is unit-tested directly
  // (AC-15) rather than depending on a live session_start under --network=none
  // (plan Open Item 4 — the child-session session_start behaviour could not be
  // exercised empirically in this sandbox).
  pi.on("session_start", async () => {
    seedActiveRoleIfEmpty(PRIMARY_ROLE);
    return undefined;
  });

  pi.on("tool_call", async (event, ctx) => {
    const role = getActiveRole();

    if (canUse(role, event.toolName)) {
      // AC-2: an allowed tool call passes untouched.
      return undefined;
    }

    if (!ctx.hasUI) {
      // AC-4: the would-escalate path with no UI to escalate to — fail
      // closed, mechanism only (shipped permission-gate.ts pattern).
      return {
        block: true,
        reason: role
          ? `blocked: role "${role}" is not permitted to call tool "${event.toolName}" (no UI available to escalate; fail-closed)`
          : `blocked: no active role set and no UI available to escalate (fail-closed)`,
      };
    }

    // AC-1 / AC-3: deny-by-default, whether the role is unset or the tool
    // is simply outside the (set) role's allow-set.
    return {
      block: true,
      reason: role
        ? `blocked: role "${role}" is not permitted to call tool "${event.toolName}"`
        : `blocked: no active role set (deny-by-default)`,
    };
  });
}
