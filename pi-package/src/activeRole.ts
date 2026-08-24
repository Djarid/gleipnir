/**
 * activeRole.ts — SRP: the current-role STATE model, and nothing else.
 *
 * Session-scoped active-role holder. Modelled as a stack rather than a
 * single variable so that nested delegation (a child that itself delegates,
 * AC-7) attributes each in-flight `tool_call` to whichever session is
 * currently executing, and so the parent's role is restored automatically
 * when a child (or grandchild) session finishes — the same push/pop shape
 * `depth.ts` uses for its counter, and for the same reason (D4's
 * try/finally safety property).
 *
 * ASSUMPTION flagged for the record: this in-process stack is sound only if
 * pi's runtime does not interleave tool_call events across sessions inside a
 * single Node.js turn (i.e. a parent `await`s a child's `session.prompt(...)`
 * to completion before its own next tool call can fire). That is the
 * ordinary single-event-loop behaviour of `createAgentSession`-based
 * in-process delegation (D2/[ASSUMPTION-1]) and was not something this
 * delegation could empirically re-confirm against pi's real runtime (see
 * README "D6 finding" — the same capability wall that blocked D6 blocked
 * exercising this too). If a future step moves delegation to `runRpcMode`
 * (process isolation) this stack model does not need to change, because each
 * process gets its own module instance.
 */

const roleStack: string[] = [];

/** Push a new current role (delegate-entry / session_start). */
export function pushActiveRole(role: string): void {
  roleStack.push(role);
}

/** Pop back to the previous role (delegate-exit, always via try/finally). */
export function popActiveRole(): string | undefined {
  return roleStack.pop();
}

/** The role for whichever session is currently executing, if any. */
export function getActiveRole(): string | undefined {
  return roleStack.length > 0 ? roleStack[roleStack.length - 1] : undefined;
}

/** Replace the whole stack with a single role (e.g. at `session_start`). */
export function setActiveRole(role: string): void {
  roleStack.length = 0;
  roleStack.push(role);
}

/** Clear all state — deny-by-default until a role is (re-)set. Test-only reset too. */
export function clearActiveRole(): void {
  roleStack.length = 0;
}
