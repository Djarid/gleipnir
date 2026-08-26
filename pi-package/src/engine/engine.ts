/**
 * engine.ts — SRP: move engine state per the deterministic rules, and
 * nothing else. One reason to change: the state-mover behaviour.
 *
 * Ports (oracle, semantics frozen): `src/gleipnir/engine/__init__.py`
 * L214-511 (`StepResult`, the typed error classes, `Engine`).
 *
 * REAL BODIES (Assemble step 5a, code stage): every method below is
 * implemented against `__init__.py` L272-511's behavioural contract, which
 * `test/engine.test.ts` (the structural port of `tests/test_engine.py`)
 * pins 1:1. The Assemble step-2a interface-stub phase (bodies that threw
 * `Error("not implemented")`) is superseded by this real implementation.
 *
 * `engine.ts` imports ONLY `state.ts`, `transitions.ts`, `attestation.ts`
 * (pure core; no pi runtime imports, no filesystem, no bus — AC-PURITY,
 * mirrors `DESIGN.md`'s non-goals + oracle module docstring).
 */

import {
  PipelineState,
  isPipelineState,
  DEFAULT_REVERT_BUDGET,
  BrandedPipelineState,
} from "./state.ts";
import { Verdict, TRANSITIONS, isVerdict, type Judge } from "./transitions.ts";
import { Attestation, AttestationStatus } from "./attestation.ts";

export type { Judge };

/**
 * The outcome of one `step()`, `answerHumanQuestion()` or `attemptGate()`
 * call (oracle `@dataclass(frozen=True) class StepResult`, L214-221). Plain
 * `interface` + a frozen constructed object (idiom-table row 7) — NO brand
 * check is required here (unlike `Attestation`; see that module's header),
 * so the plain-structural idiom is the correct, unamended choice.
 */
export interface StepResult {
  readonly state: PipelineState;
  readonly escalated: boolean;
}

/** Base for all engine faults (oracle `EngineError(Exception)`, L229-230).
 * Idiom-table row 5: a typed `Error` subclass with `.name` set, mirroring
 * `depth.ts`'s `DepthCapExceededError` idiom. */
export class EngineError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EngineError";
  }
}

/** The judge returned something other than a `Verdict` member (oracle
 * `InvalidVerdict(EngineError)`, L233-237). Also used by `Engine.resumeAt`
 * to reject a non-`PipelineState` value (oracle L338-341, which reuses
 * `InvalidVerdict` for that refusal too — not a separate exception). */
export class InvalidVerdict extends EngineError {
  constructor(message: string) {
    super(message);
    this.name = "InvalidVerdict";
  }
}

/** The current state has no transition for the given verdict (oracle
 * `NoSuchTransition(EngineError)`, L240-244). */
export class NoSuchTransition extends EngineError {
  constructor(message: string) {
    super(message);
    this.name = "NoSuchTransition";
  }
}

/** Raised by `step()` whenever `state is HUMAN_QUESTION` (oracle
 * `HumanGateBlocked(EngineError)`, L247-249). */
export class HumanGateBlocked extends EngineError {
  constructor(message: string) {
    super(message);
    this.name = "HumanGateBlocked";
  }
}

/** `attemptGate()` was called with `attestation` absent (oracle
 * `AttestationRequired(EngineError)`, L252-253). */
export class AttestationRequired extends EngineError {
  constructor(message: string) {
    super(message);
    this.name = "AttestationRequired";
  }
}

/** `attemptGate()` was called with an attestation that is absent, pending,
 * red, or whose `pipelineId` does not match (oracle
 * `AttestationNotGreen(EngineError)`, L256-262). */
export class AttestationNotGreen extends EngineError {
  constructor(message: string) {
    super(message);
    this.name = "AttestationNotGreen";
  }
}

/**
 * The G-5 deterministic orchestration engine (oracle `class Engine`,
 * L272-511). Construction and every method are implemented against the
 * behavioural contract `tests/test_engine.py` pins (see that file, ported
 * 1:1 in `test/engine.test.ts`).
 */
export class Engine {
  readonly pipelineId: string;

  private _state: PipelineState;
  private readonly _revertBudget: number;
  private _revertCount: number;
  // Tracks which main-line state raised Verdict.NEEDS_HUMAN, so
  // answerHumanQuestion() knows where to return control. null whenever we
  // are not awaiting an answer (including right after one has just been
  // consumed) — mirrors oracle `_human_question_origin`, L306-310.
  private _humanQuestionOrigin: PipelineState | null;

  constructor(pipelineId: string, revertBudget?: number) {
    this.pipelineId = pipelineId;
    this._state = PipelineState.BRAINSTORM;
    this._revertBudget = revertBudget === undefined ? DEFAULT_REVERT_BUDGET : revertBudget;
    this._revertCount = 0;
    this._humanQuestionOrigin = null;
  }

  /**
   * Reconstruct an engine positioned at `state` (oracle `resume_at`,
   * L312-344). Construction, NOT a transition — the only ways to *move* the
   * engine remain `step`, `answerHumanQuestion` and `attemptGate`. `state`
   * must be a real `PipelineState` member; anything else is rejected
   * (fail-closed), never coerced. The revert counter resets to 0 on resume
   * (the honestly-flagged gap, oracle L330-335).
   *
   * S5 ADDITIVE HARDENING (D-S5-3/D-S5-P1, AC-BRAND-1..3): `state` must now
   * be a `BrandedPipelineState` (via `state.ts`'s `brandState()`), not a
   * bare `PipelineState` string. This closes the S4-deferred limitation
   * (`state.ts`'s `isPipelineState` header / S4 idiom-table row 15): a raw
   * string — even one with the exact same VALUE as a genuine member — is
   * REJECTED here, mirroring Python's `isinstance(state, PipelineState)`.
   * `step`/`answerHumanQuestion`/`attemptGate` are UNCHANGED (AC-ADDITIVE);
   * this is the ONLY tightening in this file.
   */
  static resumeAt(
    pipelineId: string,
    state: BrandedPipelineState,
    revertBudget?: number,
  ): Engine {
    if (!(state instanceof BrandedPipelineState)) {
      throw new InvalidVerdict(
        `resumeAt requires a branded PipelineState (via brandState()), got ${typeof state}`,
      );
    }
    const engine = new Engine(pipelineId, revertBudget);
    engine._state = state.value;
    return engine;
  }

  /** The engine's current state. Read-only from outside. */
  get state(): PipelineState {
    return this._state;
  }

  /** How many backward `Verdict.FAIL` hops this engine instance has
   * consumed so far (oracle `revert_count` property, L501-511). */
  get revertCount(): number {
    return this._revertCount;
  }

  /**
   * Call `judge` for the current state, then route deterministically
   * (oracle `step`, L354-435).
   */
  step(judge: Judge, payload?: Readonly<Record<string, unknown>>): StepResult {
    if (this._state === PipelineState.HUMAN_QUESTION) {
      throw new HumanGateBlocked(
        "step() cannot be called while awaiting a human answer; use answerHumanQuestion().",
      );
    }

    const verdict = judge(this._state, payload ?? {});
    if (!isVerdict(verdict)) {
      throw new InvalidVerdict(`judge returned ${JSON.stringify(verdict)}, not a Verdict member`);
    }

    const edges = TRANSITIONS[this._state];
    if (!edges || !(verdict in edges)) {
      throw new NoSuchTransition(`no transition for ${verdict} from ${this._state}`);
    }

    const target = edges[verdict] as PipelineState;

    if (verdict === Verdict.NEEDS_HUMAN) {
      this._humanQuestionOrigin = this._state;
      this._state = target;
      return { state: target, escalated: false };
    }

    if (verdict === Verdict.FAIL) {
      // A revert edge (the only FAIL entries in TRANSITIONS are the three
      // gate stages' backward edges). Count it against the single global
      // budget -- never reset by PASS, re-entry, or reaching a target --
      // and escalate the instant the counter REACHES the budget, exactly
      // at N (never N-1, never N+1). Mirrors oracle L411-432; the G-4 bus
      // emission the oracle comment describes is deliberately NOT wired
      // here (out of scope for S4 per the plan; the engine stays pure).
      this._revertCount += 1;
      if (this._revertCount >= this._revertBudget) {
        this._state = PipelineState.ESCALATED;
        return { state: PipelineState.ESCALATED, escalated: true };
      }
      this._state = target;
      return { state: target, escalated: false };
    }

    this._state = target;
    return { state: target, escalated: false };
  }

  /** The ONLY way out of `HUMAN_QUESTION` (oracle `answer_human_question`,
   * L437-460). */
  answerHumanQuestion(_answer: unknown): StepResult {
    if (this._state !== PipelineState.HUMAN_QUESTION) {
      throw new EngineError(
        "answerHumanQuestion() called while not awaiting a human answer.",
      );
    }
    if (this._humanQuestionOrigin === null) {
      // Defensive: should be unreachable if state bookkeeping is correct,
      // but never silently no-op past a missing origin (oracle L450-455).
      throw new EngineError("no pending human question to answer.");
    }

    const origin = this._humanQuestionOrigin;
    this._humanQuestionOrigin = null;
    this._state = origin;
    return { state: origin, escalated: false };
  }

  /** The ONLY way into `GATE` (oracle `attempt_gate`, L462-499). */
  attemptGate(attestation: Attestation | null): StepResult {
    if (this._state !== PipelineState.GIT) {
      throw new EngineError(
        "attemptGate() is only valid while state is PipelineState.GIT.",
      );
    }

    if (attestation === null || attestation === undefined) {
      throw new AttestationRequired("attemptGate() requires an Attestation.");
    }
    // MANDATORY PRE-CODE AMENDMENT #1 (see attestation.ts's module header):
    // a REAL brand check (`instanceof`), not a structural duck-type -- a
    // `{pipelineId, status}` object literal (or a string/bool/number) is
    // `false` here, exactly as Python's `isinstance(attestation, Attestation)`
    // rejects a dict-lookalike. Uses the built-in `TypeError`, mirroring the
    // oracle's own use of the built-in (not an `EngineError` subclass) for
    // this specific refusal (oracle L485-489).
    if (!(attestation instanceof Attestation)) {
      throw new TypeError(
        `attemptGate() requires an Attestation instance, got ${typeof attestation}.`,
      );
    }
    if (
      attestation.status !== AttestationStatus.GREEN ||
      attestation.pipelineId !== this.pipelineId
    ) {
      throw new AttestationNotGreen(
        "attestation is not green for this engine's pipeline_id.",
      );
    }

    this._state = PipelineState.GATE;
    return { state: PipelineState.GATE, escalated: false };
  }

  /**
   * TEST-ONLY accessor (D-S4-P4 / MANDATORY PRE-CODE AMENDMENT #2):
   * reposition the engine's private state directly, for the cycle-thrash
   * anti-thrash proof (`test_cycle_thrash_escalates_at_exactly_n_concrete_budget_4`
   * in `test/engine.test.ts`), which needs to exercise different revert
   * edges (SPEC_REVIEW->PLAN, QUALITY->CODE) while keeping `revertCount`
   * continuous across the hop. `Engine.resumeAt` is NOT used for this: it
   * always constructs a FRESH engine with `revertCount` reset to 0 (see
   * `resumeAt` above), which would silently reset the very counter this
   * test is trying to keep continuous -- the oracle test hits the SAME
   * problem and solves it the SAME way (a leading-underscore "private"
   * attribute poke, `engine._state = PipelineState.SPEC_REVIEW`,
   * `test_engine.py` L493). The leading underscore is load-bearing, not
   * cosmetic: it excludes this method from
   * `test_no_bypass_method_exists_on_engine`'s public-name scan (both the
   * oracle's `dir(Engine)` filter and this port's `Object.getOwnPropertyNames`
   * filter only flag names NOT starting with `_`), exactly mirroring how the
   * oracle's `_state` poke bypasses its own ported filter. This is NOT a
   * general production state setter -- the only ways to *move* the engine
   * in real use remain `step`, `answerHumanQuestion` and `attemptGate`.
   */
  _setStateForTestOnly(state: PipelineState): void {
    this._state = state;
  }
}

// Re-exported so callers/tests can reference the data modules through this
// single module path if convenient, without engine.ts re-defining them.
export { PipelineState, Verdict, TRANSITIONS, isPipelineState, isVerdict, Attestation };
// S5 addition: BrandedPipelineState, re-exported for the same convenience
// reason (callers needing resumeAt's new required type need not import
// state.ts separately).
export { BrandedPipelineState };
