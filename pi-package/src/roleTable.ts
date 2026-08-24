/**
 * roleTable.ts — SRP: the capability DATA + lookup, and nothing else.
 *
 * Pure data + a `canUse(role, toolName)` lookup. No pi imports (testable in
 * total isolation, per the plan's Assemble step 2 and Trace table). ONE role
 * for S1 (the full 8-role roster is S2, per D-plan scope). Deny-by-default:
 * an unset role, an unknown role, or a tool absent from the role's allow-set
 * all resolve to `false` — there is no implicit-allow path anywhere in this
 * module.
 *
 * Open/Closed (Design Principles): adding roles/tools in S2 extends this data
 * without touching `enforcement.ts`'s hook logic — the table is data-driven,
 * the hook is closed to modification as the roster grows.
 */

/** One role's allow-set. Frozen so a caller cannot mutate the table at runtime. */
export type RoleName = string;

const GLEIPNIR_CODE_ALLOW_SET: ReadonlySet<string> = Object.freeze(
  new Set(["read_file", "write_file", "delegate"]),
);

/**
 * The S1 role table: ONE simple role (`gleipnir-code`), a small allow-set,
 * deny-by-default for everything else (including `bash`, deliberately
 * absent — mirrors the AETOS enumerable-bypass lesson this whole framework
 * corrects: dangerous verbs are absent by capability, not caught by a
 * pattern deny).
 */
export const ROLE_ALLOW_SETS: Readonly<Record<RoleName, ReadonlySet<string>>> =
  Object.freeze({
    "gleipnir-code": GLEIPNIR_CODE_ALLOW_SET,
  });

/**
 * Deny-by-default lookup: `role` is `undefined`/empty -> false; `role` is
 * unknown to the table -> false; `toolName` absent from the role's
 * allow-set -> false. Only an explicit table hit returns `true`.
 */
export function canUse(role: RoleName | undefined, toolName: string): boolean {
  if (!role) {
    return false;
  }
  const allowSet = ROLE_ALLOW_SETS[role];
  if (!allowSet) {
    return false;
  }
  return allowSet.has(toolName);
}
