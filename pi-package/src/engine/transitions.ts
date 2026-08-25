/**
 * transitions.ts — SRP: the verdict vocabulary + the sequencing data, and
 * nothing else. One reason to change: the transition topology.
 *
 * Ports (oracle, semantics frozen): `src/gleipnir/engine/__init__.py` L90-98
 * (`Verdict`), L101-106 (`Judge`), L145-187 (`TRANSITIONS`) — reproducing
 * EVERY structural absence exactly (no `GIT.PASS`; `GATE`/`ESCALATED`/
 * `HUMAN_QUESTION` absent as keys; the 3 backward `FAIL` edges with verified
 * directions). The absences ARE the spec (oracle module docstring) — freezing
 * prevents runtime widening (idiom-table row 4, `roleTable.ts` AC-19
 * precedent).
 *
 * `Judge` is declared here (not in `engine.ts`) so `judges.ts` can depend on
 * `state.ts`/`transitions.ts` ONLY, per the Integrations map's "no import
 * into engine core" rule (mirrors `judges.py` L28-33) — `engine.ts` imports
 * `Judge` from here too, so the type is defined once (DRY), never
 * duplicated between the two modules that both need it.
 */

import { PipelineState } from "./state.ts";

/** The judge's entire channel back into the router: three members, no
 * free-text escape hatch and no "skip" member (oracle L90-98). Surface
 * mapping (idiom-table row 2): const-object + derived union, frozen, exactly
 * 3 keys — `test_verdict_has_exactly_three_members_no_skip` re-earns it. */
export const Verdict = Object.freeze({
  PASS: "pass",
  FAIL: "fail",
  NEEDS_HUMAN: "needs_human",
} as const);

export type Verdict = (typeof Verdict)[keyof typeof Verdict];

const VERDICT_VALUES: ReadonlySet<string> = Object.freeze(
  new Set(Object.values(Verdict)),
);

/** Runtime type guard: is `value` a genuine `Verdict` member? Used by
 * `engine.ts`'s `step()` to reject a judge that returns anything other than
 * a `Verdict` (e.g. a bare string like `"skip review"`) BEFORE any routing
 * is attempted — the `InvalidVerdict` refusal (oracle L392-396). */
export function isVerdict(value: unknown): value is Verdict {
  return typeof value === "string" && VERDICT_VALUES.has(value);
}

/** Injectable per-step judgment (oracle L106). Pure data in, pure `Verdict`
 * out — the engine core stays deterministic; tests supply a fixed/fake
 * `Judge` instead of an LLM call. Neither the engine core nor any `Judge`
 * factory in `judges.ts` ever inspects `payload` for control purposes —
 * only the judge's RETURN value (constrained to `Verdict`) reaches
 * `TRANSITIONS`. */
export type Judge = (
  state: PipelineState,
  payload: Readonly<Record<string, unknown>>,
) => Verdict;

/** One state's outgoing edges: a partial map from `Verdict` to the target
 * `PipelineState`. Partial because the absences are load-bearing (e.g. `GIT`
 * has no `PASS` key at all). */
export type TransitionEdges = Readonly<Partial<Record<Verdict, PipelineState>>>;

/** The full transition table: a partial map from `PipelineState` to its
 * edges. Partial because `GATE`, `ESCALATED` and `HUMAN_QUESTION` are
 * structurally ABSENT as keys — not present-with-empty-edges, but genuinely
 * missing, so `TRANSITIONS[state] === undefined` is how `engine.ts` detects
 * "no outgoing edge at all" for those three control/terminal states. */
export type TransitionTable = Readonly<Partial<Record<PipelineState, TransitionEdges>>>;

/**
 * The deterministic transition table (oracle L145-187). This *is* the
 * sequencing: checked-in data, not prose an orchestrator narrates.
 *
 *   * `GIT` has NO entry for `Verdict.PASS`. The only path from `GIT` to
 *     `GATE` is `Engine.attemptGate(attestation)` — a distinct method gated
 *     on a verified-green `Attestation` (G-3.2), never a `Verdict`.
 *   * `GATE` and `ESCALATED` are terminal: no key for them exists in this
 *     table at all — no outgoing edge, structurally, not by convention.
 *   * `HUMAN_QUESTION` is deliberately absent as a key: no `Verdict`, from
 *     any judge, produces a transition out of it via `step()`. The only way
 *     out is `Engine.answerHumanQuestion(answer)` (precept 10).
 *   * REVERT EDGES (backward `FAIL` hops, oracle L125-142):
 *         SPEC_REVIEW(2) --FAIL--> PLAN(1)
 *         TEST(3)        --FAIL--> SPEC_REVIEW(2)   (never forward to CODE)
 *         QUALITY(5)     --FAIL--> CODE(4)
 *     Every edge is a genuine backward hop (target index < source index in
 *     `PIPELINE_ORDER`) and each counts once against the single global
 *     revert budget — see `engine.ts`'s `Engine.step`. No `FAIL` edge exists
 *     for `BRAINSTORM`, `PLAN`, `CODE`, or `GIT`: a `FAIL` from any of those
 *     is `NoSuchTransition` — absence of an edge is refusal, never a
 *     default jump (fail-closed).
 */
const TRANSITIONS_RAW: Record<string, Readonly<Partial<Record<Verdict, PipelineState>>>> = {
  [PipelineState.BRAINSTORM]: {
    [Verdict.PASS]: PipelineState.PLAN,
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
  },
  [PipelineState.PLAN]: {
    [Verdict.PASS]: PipelineState.SPEC_REVIEW,
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
  },
  [PipelineState.SPEC_REVIEW]: {
    [Verdict.PASS]: PipelineState.TEST,
    // Revert edge (backward, 2 -> 1): a spec-review failure means the plan
    // is wrong; recoding won't fix a bad plan.
    [Verdict.FAIL]: PipelineState.PLAN,
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
  },
  [PipelineState.TEST]: {
    [Verdict.PASS]: PipelineState.CODE,
    // Revert edge (backward, 3 -> 2): test-first -- a failed test-authoring
    // stage means the spec/plan was inadequate to write good tests against.
    // Reverts to SPEC_REVIEW, never forward to CODE.
    [Verdict.FAIL]: PipelineState.SPEC_REVIEW,
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
  },
  [PipelineState.CODE]: {
    [Verdict.PASS]: PipelineState.QUALITY,
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
  },
  [PipelineState.QUALITY]: {
    [Verdict.PASS]: PipelineState.GIT,
    // Revert edge (backward, 5 -> 4): a quality/blast-radius failure means
    // the implementation needs rework.
    [Verdict.FAIL]: PipelineState.CODE,
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
  },
  [PipelineState.GIT]: {
    [Verdict.NEEDS_HUMAN]: PipelineState.HUMAN_QUESTION,
    // Deliberately no Verdict.PASS entry. See module header.
  },
  // PipelineState.GATE: intentionally absent (terminal; G-3.2).
  // PipelineState.HUMAN_QUESTION: intentionally absent (precept 10).
  // PipelineState.ESCALATED: intentionally absent (terminal escalation sink).
};

/** Deep-freeze: the outer table AND every inner edges-object, so neither a
 * new key nor a new edge can be added at runtime (idiom-table row 4). */
function deepFreezeTransitions(
  raw: Record<string, Readonly<Partial<Record<Verdict, PipelineState>>>>,
): TransitionTable {
  for (const edges of Object.values(raw)) {
    Object.freeze(edges);
  }
  return Object.freeze(raw) as TransitionTable;
}

export const TRANSITIONS: TransitionTable = deepFreezeTransitions(TRANSITIONS_RAW);
