/**
 * state.ts — SRP: the pipeline state vocabulary + main-line order + default
 * revert budget, and nothing else. One reason to change: the set of states.
 *
 * Ports (oracle, semantics frozen — D-S4-1=Approach C): `src/gleipnir/engine/
 * __init__.py` L55-79 (`PipelineState`, `PIPELINE_ORDER`) + L87
 * (`DEFAULT_REVERT_BUDGET`).
 *
 * Surface mapping (idiom-table row 1, D-S4-P2): Python `class
 * PipelineState(str, Enum)` (10 str members) -> a frozen `const`-object +
 * derived string-literal-union `type`, NOT a TS `enum` — preserves the
 * string *values* (needed by the router/bridge seam) and avoids TS `enum`
 * erasure quirks under `--experimental-strip-types`.
 *
 * This module imports nothing from pi runtime, nothing from any other
 * `engine/*` module (AC-PURITY at the vocabulary layer) — everything else in
 * `engine/**` depends on this file, never the other way around.
 */

/** The 10-member pipeline state vocabulary (oracle `__init__.py` L55-65).
 * Two of the ten (`HUMAN_QUESTION`, `ESCALATED`) are engine-internal control
 * states, not positions on `PIPELINE_ORDER` — see that constant below. */
export const PipelineState = Object.freeze({
  BRAINSTORM: "brainstorm",
  PLAN: "plan",
  SPEC_REVIEW: "spec_review",
  TEST: "test",
  CODE: "code",
  QUALITY: "quality",
  GIT: "git",
  GATE: "gate",
  HUMAN_QUESTION: "human_question",
  ESCALATED: "escalated",
} as const);

/** The string-literal union derived from the frozen const-object above —
 * every legitimate `PipelineState` VALUE, for use as a type. */
export type PipelineState = (typeof PipelineState)[keyof typeof PipelineState];

/** The main line, in spec order (oracle L70-79). `HUMAN_QUESTION` and
 * `ESCALATED` are reachable side-states, not positions on this line. */
export const PIPELINE_ORDER: readonly PipelineState[] = Object.freeze([
  PipelineState.BRAINSTORM,
  PipelineState.PLAN,
  PipelineState.SPEC_REVIEW,
  PipelineState.TEST,
  PipelineState.CODE,
  PipelineState.QUALITY,
  PipelineState.GIT,
  PipelineState.GATE,
]);

/** Global revert budget (oracle L87): the default number of backward `FAIL`
 * hops permitted (across every revert edge, combined) before the engine
 * escalates. A single per-engine counter, never a per-state mapping — see
 * `engine.ts`'s `Engine.step`. */
export const DEFAULT_REVERT_BUDGET = 3;

/** The set of every legitimate `PipelineState` VALUE, built once from the
 * const-object above (DRY — never a hand-duplicated second list). Backs
 * `isPipelineState` below. */
const PIPELINE_STATE_VALUES: ReadonlySet<string> = Object.freeze(
  new Set(Object.values(PipelineState)),
);

/**
 * Runtime type guard: is `value` a genuine `PipelineState` member?
 *
 * **Known, deliberately-flagged surface limitation (see the S4 final report
 * / D-S4-P2):** Python's `isinstance(state, PipelineState)` rejects even a
 * PLAIN STRING that happens to equal a member's value (e.g. the literal
 * `"spec_review"`), because a `str, Enum` member is a distinct runtime type
 * from a bare `str`. The TS idiom chosen here (D-S4-P2: const-object +
 * string-literal union, NOT a TS `enum`) has no such nominal/structural
 * distinction for primitive strings — `PipelineState` values ARE plain
 * strings at runtime, so a same-valued plain string is indistinguishable
 * from a "genuine" member. This function can therefore only fail-closed on
 * values that are NOT one of the ten legitimate strings at all (wrong type,
 * or a string with no matching value) — it cannot reproduce Python's
 * stronger "even the right string is not the enum" refusal. `engine.ts`'s
 * ported `test_resume_at_rejects_non_pipelinestate` is adapted accordingly
 * (see that test file's comment) — this is a reported, not silently
 * absorbed, divergence.
 */
export function isPipelineState(value: unknown): value is PipelineState {
  return typeof value === "string" && PIPELINE_STATE_VALUES.has(value);
}
