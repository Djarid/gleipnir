/**
 * roleTable.ts — SRP: the capability DATA + lookup, and nothing else.
 *
 * Pure data + a `canUse(role, toolName)` lookup. No pi runtime imports (the
 * `ToolName` type is a compile-time-only import so a typo like `read_file`
 * becomes a `tsc` error, not a silent string — see AC-18). The full 8-role
 * Gleipnir roster (S2), each expressed as a typed
 * `{ baseTools, customTools, brokerTools }` partition. Deny-by-default: an
 * unset role, an unknown role, or a tool absent from ALL three of the role's
 * partitions all resolve to `false` — there is no implicit-allow path
 * anywhere in this module.
 *
 * Open/Closed (Design Principles): adding roles/tools extends this DATA
 * without touching `enforcement.ts`'s hook logic — the table is data-driven,
 * the hook is closed to modification as the roster grows. `canUse` treats
 * every role uniformly (LSP): union membership across the three partitions,
 * no per-role special case (the inert git-broker name is handled by the same
 * membership rule, not a `git-ops` branch).
 *
 * Source of truth: `.gleipnir/agents/*.md` frontmatter `permission:`/`tools:`
 * blocks (all 8 read at S2 authoring). Partition split (plan D-B, P2):
 *   - `baseTools`   = the SDK's real base `ToolName`s the role may call
 *                     (`read | bash | edit | write | grep | find | ls`).
 *   - `customTools` = non-base host/gleipnir capabilities the role may call
 *                     (`delegate`, `webfetch`, `question`, `notify`, and the
 *                     pm broker namespace — see the P2 modelling note below).
 *   - `brokerTools` = RESERVED for the git broker sole-holder (G-2 / Micro);
 *                     non-empty ONLY for `git-ops`.
 *
 * P2 modelling note (ratified in the plan Trace §capability mapping): both
 * `gleipnir-git_*` and `gleipnir-pm_*` are MCP broker namespaces of the same
 * structural class in opencode. This table deliberately places ONLY the git
 * broker name in `brokerTools` and puts the pm namespace in
 * `project-mgr.customTools`, so the G-2 assertion is the clean, falsifiable
 * "exactly one role has a non-empty `brokerTools`, and it is `git-ops`"
 * (AC-17). `project-mgr` still uniquely holds pm; git-ops still uniquely holds
 * git; deny-by-default and G-2 are preserved either way — only which partition
 * carries the pm string differs.
 *
 * Per-arg / per-path bounds (e.g. `gleipnir-code` may `edit` but NOT under
 * `.gleipnir/**`; `git-ops` may `read` but NOT `.git/**`;
 * `quality-reviewer`'s bash is `git {diff,log,show,status}` only) are NOT
 * expressible as a coarse base-`ToolName` grant. They are recorded here as
 * `bounds` METADATA per role so the canonical table does not lose them, and
 * their fine-grained ENFORCEMENT (argument-level `event.input` inspection) is
 * deferred to S3/S7 (the E-1 argument-policy seam). S2 enforces the coarse
 * tool-presence allow/deny via `canUse`; it does NOT enforce the bounds.
 */

/**
 * The SDK's base tool-name union, mirrored locally.
 *
 * LINK FINDING (S2, in-sandbox `tsc`): the SDK DOES define
 * `export type ToolName = "read" | "bash" | "edit" | "write" | "grep" | "find"
 * | "ls"` and `export declare const allToolNames: Set<ToolName>` — but ONLY at
 * the subpath `@earendil-works/pi-coding-agent/dist/core/tools/index`, which is
 * NOT reachable: the package `exports` map exposes only `.`, `./rpc-entry` and
 * `./client`, and the root `index.d.ts` re-exports many tool symbols but
 * deliberately NOT `ToolName`/`allToolNames`. So the plan's Link item 5
 * assumption ("import `ToolName` from the SDK") does not hold against the
 * shipped package. Rather than reach past the exports map into `dist/**`
 * (fragile, breaks on any repackage), the union is declared here verbatim and
 * the AC-18 runtime test asserts every `baseTools` value is a member of the
 * local `SDK_BASE_TOOL_NAMES` set — so a drift from the SDK's real vocabulary
 * is caught by test, and a typo like `read_file` is caught by `tsc` against
 * this type. Reconcile if a future SDK release re-exports `ToolName` from root.
 */
export type ToolName =
  | "read"
  | "bash"
  | "edit"
  | "write"
  | "grep"
  | "find"
  | "ls";

/** The base tool-name set, mirroring the SDK's `allToolNames`. The single
 * source AC-18 checks `baseTools` membership against (DRY). */
export const SDK_BASE_TOOL_NAMES: ReadonlySet<ToolName> = Object.freeze(
  new Set<ToolName>(["read", "bash", "edit", "write", "grep", "find", "ls"]),
);

/** The three-partition capability declaration for one role. Readonly arrays so
 * a caller cannot push into a partition after construction; the whole record
 * is additionally deep-frozen below (AC-19). */
export interface RoleAllowSet {
  /** SDK base `ToolName`s the role may call. */
  readonly baseTools: readonly ToolName[];
  /** Non-base host/gleipnir custom tools the role may call. */
  readonly customTools: readonly string[];
  /** Git broker namespace — non-empty ONLY for the G-2 sole-holder (git-ops). */
  readonly brokerTools: readonly string[];
  /** Human-readable per-arg/per-path bounds captured as metadata (NOT enforced
   * by S2 — see the module header and plan §per-arg). */
  readonly bounds?: readonly string[];
}

export type RoleName = string;

/** The inert git-broker namespace name granted (in the table only) to the
 * sole holder. Referenced from this single constant so tests do not
 * hand-duplicate the literal (DRY, plan §DRY). "Inert" = the capability is
 * DECLARED in the table (so `canUse` returns `true` for git-ops), but no real
 * `gleipnir-git_*` tool is registered/reachable yet (that is S6). */
export const GIT_BROKER_TOOL = "gleipnir-git_*";

/** The pm broker namespace, modelled in `project-mgr.customTools` per P2 (see
 * header) so `brokerTools` stays git-only for the G-2 proof. */
export const PM_BROKER_TOOL = "gleipnir-pm_*";

/** A tool name no role should ever hold, in any partition — the shared
 * universal-deny probe used by both `roleTable.test.ts` and
 * `enforcement.test.ts`. Exported from this single constant so both test
 * files import rather than hand-duplicate the literal (DRY, same pattern as
 * `GIT_BROKER_TOOL`/`PM_BROKER_TOOL` above). */
export const UNIVERSALLY_DENIED = "totally_unregistered_tool_xyz";

/**
 * The S2 role table: all 8 roster roles, each a typed three-partition
 * allow-set, deny-by-default for everything not listed. `bash` is deliberately
 * absent from every base set except where the source frontmatter grants a
 * bounded bash allowlist (`gleipnir-code`, `quality-reviewer`, `git-ops`) —
 * and even there the coarse S2 grant is `bash` present, with the arg-level
 * allowlist recorded in `bounds` for S3/S7. This mirrors the AETOS
 * enumerable-bypass lesson the framework corrects: dangerous verbs are absent
 * by capability, caught structurally, not by a pattern deny.
 */
const ROLE_ALLOW_SETS_RAW: Record<RoleName, RoleAllowSet> = {
  // Primary session. Holds NEITHER broker namespace. `question` is the
  // operator channel (host UI primitive, orchestrator-only). `delegate` is
  // how it dispatches every unit of work (P4 seeds it as the top-level role).
  orchestrator: {
    baseTools: [],
    customTools: ["delegate", "question"],
    brokerTools: [],
    bounds: [
      "edit/bash/webfetch denied by capability (absent from baseTools)",
      "task -> only the 8 named subagents (delegation routing; not a base tool)",
    ],
  },
  // Design explorer. read + webfetch; edit scoped to .gleipnir/plans/** only.
  "gleipnir-brainstorm": {
    baseTools: ["read", "edit"],
    customTools: ["webfetch"],
    brokerTools: [],
    bounds: [
      "edit allowed ONLY under .gleipnir/plans/** (path bound; arg-level, S3/S7)",
      "question denied by capability (a subagent cannot reach the operator)",
    ],
  },
  // Planner. read + webfetch; edit scoped to .gleipnir/plans/** only.
  "gleipnir-plan": {
    baseTools: ["read", "edit"],
    customTools: ["webfetch"],
    brokerTools: [],
    bounds: ["edit allowed ONLY under .gleipnir/plans/** (path bound; arg-level, S3/S7)"],
  },
  // Implementation. read + edit; bounded bash allowlist; `delegate` in its
  // custom set (one of the two delegate-capable roles).
  "gleipnir-code": {
    baseTools: ["read", "edit", "bash"],
    customTools: ["delegate"],
    brokerTools: [],
    bounds: [
      "edit denied under .gleipnir/**, .git/**, .github/**, src/gleipnir/preflight/** (+ exact-path allows) (path bound; arg-level, S3/S7)",
      "bash allowlisted to `bin/gleipnir-sandbox {test,lint}` (+ profiles) only; git*/gh*/sh*/curl* denied (arg bound; arg-level, S3/S7)",
    ],
  },
  // Read-only reviewer. read only; read-only git-inspection bash.
  "quality-reviewer": {
    baseTools: ["read", "bash"],
    customTools: [],
    brokerTools: [],
    bounds: [
      "edit/write denied by capability",
      "bash allowlisted to `git {diff,log,show,status}` only (arg bound; arg-level, S3/S7)",
    ],
  },
  // The sole git/broker holder (G-2). read (not .git/**); branch/sync bash
  // allowlist; the inert git-broker namespace is the ONLY non-empty
  // brokerTools in the whole table.
  "git-ops": {
    baseTools: ["read", "bash"],
    customTools: [],
    brokerTools: [GIT_BROKER_TOOL],
    bounds: [
      "read denied under .git/** to protect the token (path bound; arg-level, S3/S7)",
      "bash allowlisted to branch/sync verbs (status/diff/log/checkout/switch/branch/merge/fetch/pull); commit+push move to the broker (arg bound; arg-level, S3/S7)",
    ],
  },
  // PM lifecycle. read only; holds the pm namespace — modelled in customTools
  // (P2) so brokerTools stays git-only for the G-2 proof.
  "project-mgr": {
    baseTools: ["read"],
    customTools: [PM_BROKER_TOOL],
    brokerTools: [],
    bounds: ["single-namespace: only the pm surface; git namespace denied"],
  },
  // Human notification channel. read only; holds the notify host tool.
  notify: {
    baseTools: ["read"],
    customTools: ["notify"],
    brokerTools: [],
    bounds: ["single-namespace: only the notify surface; both broker namespaces denied"],
  },
};

/** Deep-freeze a role's allow-set: freeze each partition array AND the
 * `RoleAllowSet` object, so neither `push` nor property reassignment can widen
 * the table at runtime (AC-19 — the C3-integrity property in code form). */
function deepFreezeAllowSet(set: RoleAllowSet): RoleAllowSet {
  Object.freeze(set.baseTools);
  Object.freeze(set.customTools);
  Object.freeze(set.brokerTools);
  if (set.bounds) {
    Object.freeze(set.bounds);
  }
  return Object.freeze(set);
}

for (const role of Object.keys(ROLE_ALLOW_SETS_RAW)) {
  deepFreezeAllowSet(ROLE_ALLOW_SETS_RAW[role]);
}

/** The frozen 8-role table. */
export const ROLE_ALLOW_SETS: Readonly<Record<RoleName, RoleAllowSet>> =
  Object.freeze(ROLE_ALLOW_SETS_RAW);

/** Every tool a role may call, across all three partitions, as one set. The
 * single place partition membership is unioned — `canUse` and any DRY test
 * projection both go through here rather than re-listing partitions. */
export function unionAllowSet(role: RoleName): ReadonlySet<string> {
  const set = ROLE_ALLOW_SETS[role];
  if (!set) {
    return new Set<string>();
  }
  return new Set<string>([...set.baseTools, ...set.customTools, ...set.brokerTools]);
}

/**
 * Deny-by-default lookup: `role` is `undefined`/empty -> false; `role` is
 * unknown to the table -> false; `toolName` absent from the role's union
 * allow-set (base ∪ custom ∪ broker) -> false. Only an explicit table hit in
 * one of the three partitions returns `true`. Uniform across all roles (LSP):
 * the inert git-broker name resolves `true` for git-ops and `false` for every
 * other role by the SAME membership rule, not a special case.
 */
export function canUse(role: RoleName | undefined, toolName: string): boolean {
  if (!role) {
    return false;
  }
  const set = ROLE_ALLOW_SETS[role];
  if (!set) {
    return false;
  }
  return (
    set.baseTools.includes(toolName as ToolName) ||
    set.customTools.includes(toolName) ||
    set.brokerTools.includes(toolName)
  );
}
