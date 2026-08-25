/**
 * allowTable.ts — SRP: project state -> allowed-roles, and nothing else. One
 * reason to change: the stage-role binding.
 *
 * Ports (oracle, semantics frozen): `src/gleipnir/engine/allow_table.py`
 * L1-105 (`ROLE_STATES`, derived `ALLOW_TABLE`, `allowed_agents_for`).
 *
 * REAL BODY (Assemble step 5b, code stage): `ALLOW_TABLE` is DERIVED by
 * iterating every `PipelineState` member and collecting the roles bound to
 * it in `ROLE_STATES` (oracle `_derive_allow_table`, `allow_table.py`
 * L71-93) — a projection, never a hand-copied second table. `allowedRolesFor`
 * is deny-by-default (oracle `allowed_agents_for`, L96-105).
 *
 * ============================================================================
 * The composition seam (D-S4-6, Assemble step 6) — SPECIFIED here, per the
 * plan's default choice.
 * ============================================================================
 * `allowedRolesFor(state)` is the additive entry point an orchestrator (or a
 * thin wrapper it calls) consults BEFORE dispatching a role, so that a
 * delegation while the engine is in a control/terminal state (or to a role
 * not bound to the current state) is refused before it happens. Per the
 * plan's Assemble step 6, the default realisation is PROSE/DESIGN
 * SPECIFICATION, not a new code call site: this codebase's orchestrator is
 * the `.gleipnir/agents/orchestrator.md` PROMPT role (Tier-3 POLICY, not
 * `pi-package` TypeScript), so there is no genuine `pi-package` call site to
 * wire a consultation into yet (no code here dispatches roles the way
 * `delegate.ts`'s `execute` does for tool-call enforcement — `delegate.ts`
 * dispatches by ROLE-TO-TOOL capability, an orthogonal axis, per the
 * Integrations map). Per the plan: "the orchestrator agent consults
 * `allowedRolesFor(engineState)` and refuses to delegate to a role not in
 * the set" is the specification; NO new file (e.g. a `consultSeam.ts`) is
 * added in this delegation because none is genuinely needed yet — adding one
 * with no real caller would be premature code with no test arbiter beyond
 * "it exists," which the plan's Assemble step 6 explicitly makes conditional
 * ("only if genuinely needed").
 *
 * **The seam is additive-only (D-S4-6, hard constraint):** this module does
 * NOT import, and this delegation does NOT edit,
 * `pi-package/src/{roleTable,enforcement,delegate,depth,activeRole}.ts`. Any
 * future call site MUST go in a NEW file, never in one of those five.
 * ============================================================================
 */

import { PipelineState, isPipelineState } from "./state.ts";

export type RoleName = string;

/**
 * The role -> bound-states binding lifted directly from
 * `.gleipnir/stage-role-map.md`'s table (oracle `ROLE_STATES`,
 * `allow_table.py` L55-63). The one place the map's bindings are lifted into
 * code; the per-state table below is DERIVED from this, never a
 * hand-maintained second copy.
 */
export const ROLE_STATES: Readonly<Record<RoleName, ReadonlySet<PipelineState>>> =
  Object.freeze({
    "gleipnir-brainstorm": Object.freeze(new Set<PipelineState>([PipelineState.BRAINSTORM])),
    "gleipnir-plan": Object.freeze(new Set<PipelineState>([PipelineState.PLAN])),
    "quality-reviewer": Object.freeze(
      new Set<PipelineState>([PipelineState.SPEC_REVIEW, PipelineState.QUALITY]),
    ),
    "gleipnir-code": Object.freeze(
      new Set<PipelineState>([PipelineState.TEST, PipelineState.CODE]),
    ),
    "git-ops": Object.freeze(new Set<PipelineState>([PipelineState.GIT])),
  });

/** Roster roles known to have no G-5 pipeline stage (oracle
 * `NON_PIPELINE_ROLES`, `allow_table.py` L68) — must never appear in
 * `ROLE_STATES` or in any `ALLOW_TABLE` entry (minimal-slice deny). */
export const NON_PIPELINE_ROLES: ReadonlySet<RoleName> = Object.freeze(
  new Set<RoleName>(["project-mgr", "notify"]),
);

/**
 * Project `ROLE_STATES` onto every `PipelineState` member (oracle
 * `_derive_allow_table`, `allow_table.py` L71-90). Iterating `PipelineState`
 * itself (the engine's own vocabulary) — rather than listing states by hand
 * here — is what makes this a DERIVATION: a state absent from every role's
 * bound-states set (HUMAN_QUESTION, ESCALATED, GATE, or any future control
 * state) falls out with the empty set automatically, and a state present in
 * `PipelineState` but never assigned an entry is structurally impossible,
 * since every member is visited.
 */
function deriveAllowTable(): Readonly<Partial<Record<PipelineState, ReadonlySet<RoleName>>>> {
  const table: Partial<Record<PipelineState, ReadonlySet<RoleName>>> = {};
  for (const state of Object.values(PipelineState)) {
    const roles = new Set<RoleName>();
    for (const [role, boundStates] of Object.entries(ROLE_STATES)) {
      if (boundStates.has(state)) {
        roles.add(role);
      }
    }
    table[state] = Object.freeze(roles);
  }
  return Object.freeze(table);
}

/** The derived state -> allowed-roles projection (oracle `ALLOW_TABLE`,
 * `allow_table.py` L93). Every value is a frozen `Set` (idiom-table row 8;
 * `test_allow_table_values_are_frozensets` asserts this). */
export const ALLOW_TABLE: Readonly<Partial<Record<PipelineState, ReadonlySet<RoleName>>>> =
  deriveAllowTable();

const EMPTY_ROLE_SET: ReadonlySet<RoleName> = Object.freeze(new Set<RoleName>());

/**
 * The set of roles legitimately dispatchable while the engine is in `state`
 * (oracle `allowed_agents_for`, `allow_table.py` L96-105). Deny-by-default:
 * any value that is not a known `PipelineState` member returns the empty
 * set rather than raising or guessing.
 */
export function allowedRolesFor(state: unknown): ReadonlySet<RoleName> {
  if (!isPipelineState(state)) {
    return EMPTY_ROLE_SET;
  }
  return ALLOW_TABLE[state] ?? EMPTY_ROLE_SET;
}

// Re-exported for convenience; `isPipelineState` is not otherwise consumed
// by this stub phase (the real body, Assemble 5b, uses it directly).
export { isPipelineState };
