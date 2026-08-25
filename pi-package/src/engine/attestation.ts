/**
 * attestation.ts — SRP: the attestation VALUE contract, and nothing else.
 * One reason to change: the attestation shape (S5 extends it with real HMAC
 * marker verification — VALUE/CONTRACT only here, per D-S4-4).
 *
 * Ports (oracle, semantics frozen): `src/gleipnir/engine/__init__.py`
 * L196-212 (`AttestationStatus`, `Attestation`).
 *
 * ============================================================================
 * MANDATORY PRE-CODE AMENDMENT #1 (spec-review binding condition — applied
 * here, not merely in the idiom table's prose).
 * ============================================================================
 * The plan's idiom-table row 7 offered "plain `interface` + frozen object OR
 * a `readonly`-field class" for `Attestation`/`StepResult`, but row 6
 * requires a REAL brand/`instanceof` check so `Engine.attemptGate` can
 * genuinely reject a dict-lookalike (`{pipelineId, status}` object literal)
 * the same way Python's `isinstance(attestation, Attestation)` does (oracle
 * L485; oracle test `test_agent_supplied_text_or_lookalike_cannot_satisfy_
 * the_gate`, which asserts dict/string/bool/int lookalikes are ALL refused).
 * A plain structural `interface` has NO runtime tag — a `{pipelineId,
 * status}` literal would satisfy it, defeating the refusal entirely. So
 * `Attestation` here is a REAL CLASS: `attestation instanceof Attestation`
 * is `false` for any object literal, string, boolean, or number, exactly
 * mirroring the Python refusal. (`StepResult`, which carries NO such
 * security-load-bearing brand requirement, stays the plain-`interface` +
 * frozen-object idiom in `engine.ts` — the amendment is scoped to
 * `Attestation` only, per its own wording.)
 * ============================================================================
 */

/** The four attestation statuses (oracle L196-201). Surface mapping
 * (idiom-table row 3): const-object + derived union, frozen — same pattern
 * as `PipelineState`/`Verdict`. */
export const AttestationStatus = Object.freeze({
  ABSENT: "absent",
  PENDING: "pending",
  GREEN: "green",
  RED: "red",
} as const);

export type AttestationStatus = (typeof AttestationStatus)[keyof typeof AttestationStatus];

/**
 * The evidence G-3.2 requires: a pipeline id and its status, fetched by the
 * engine/caller from the authoritative CI/verifier surface, never asserted
 * by an agent. `Engine.attemptGate` is the only method that reads one
 * (oracle `@dataclass(frozen=True) class Attestation`, L203-211).
 *
 * A REAL CLASS (amendment #1 above) — `instanceof Attestation` is the TS
 * analogue of Python's `isinstance(attestation, Attestation)`. Frozen at
 * construction (`Object.freeze(this)`) so no field can be reassigned after
 * the fact, mirroring `@dataclass(frozen=True)`.
 */
export class Attestation {
  readonly pipelineId: string;
  readonly status: AttestationStatus;

  constructor(pipelineId: string, status: AttestationStatus) {
    this.pipelineId = pipelineId;
    this.status = status;
    Object.freeze(this);
  }
}
