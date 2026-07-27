"""Gleipnir G-5 — deterministic orchestration engine (implemented).

This module defines and implements the public contract that
``tests/test_engine.py`` exercises: pipeline states, the judge interface,
the deterministic transition table, the attestation model (G-3.2), and the
``Engine`` class's methods. The full test suite (49/49) passes against this
implementation; see ``DESIGN.md`` in this directory for the full design
record and the rationale for every structural absence below (they are
load-bearing, not omissions).

Do not add prose-orchestration logic here (an LLM deciding order by
inspecting text). Sequencing lives in ``TRANSITIONS`` as data. The only
inputs that move the engine are: a ``Verdict`` returned by a ``Judge``
(routed through ``TRANSITIONS``), an ``answer`` passed to
``answer_human_question``, and an ``Attestation`` passed to
``attempt_gate``. Nothing else changes engine state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping

__all__ = [
    "PipelineState",
    "Verdict",
    "AttestationStatus",
    "Attestation",
    "StepResult",
    "Judge",
    "TRANSITIONS",
    "PIPELINE_ORDER",
    "LOOPING_STATES",
    "DEFAULT_LOOP_CAP",
    "Engine",
    "EngineError",
    "InvalidVerdict",
    "NoSuchTransition",
    "HumanGateBlocked",
    "AttestationRequired",
    "AttestationNotGreen",
]


# ---------------------------------------------------------------------------
# Pipeline states (spec G-5): brainstorm -> plan -> spec-review -> test ->
# code -> quality -> git -> gate, plus the two structural states G-5 names
# explicitly: the blocking human-question gate (precept 10) and the
# deterministic escalation sink (precept 6's loop-cap overflow). Neither of
# the two extra states is a stage bound to a role in the stage-role map;
# both are engine-internal control states.
# ---------------------------------------------------------------------------


class PipelineState(str, Enum):
    BRAINSTORM = "brainstorm"
    PLAN = "plan"
    SPEC_REVIEW = "spec_review"
    TEST = "test"
    CODE = "code"
    QUALITY = "quality"
    GIT = "git"
    GATE = "gate"
    HUMAN_QUESTION = "human_question"
    ESCALATED = "escalated"


# The main line, in spec order. HUMAN_QUESTION and ESCALATED are reachable
# side-states, not positions on this line.
PIPELINE_ORDER: tuple[PipelineState, ...] = (
    PipelineState.BRAINSTORM,
    PipelineState.PLAN,
    PipelineState.SPEC_REVIEW,
    PipelineState.TEST,
    PipelineState.CODE,
    PipelineState.QUALITY,
    PipelineState.GIT,
    PipelineState.GATE,
)

# States with a loop cap (precept 6): spec-review and quality.
LOOPING_STATES: tuple[PipelineState, ...] = (
    PipelineState.SPEC_REVIEW,
    PipelineState.QUALITY,
)

DEFAULT_LOOP_CAP = 3


class Verdict(str, Enum):
    """The judge's entire channel back into the router: three members, no
    free-text escape hatch and no "skip" member. A judge returning anything
    other than a ``Verdict`` instance is a fault (``InvalidVerdict``), not a
    string the router tries to interpret."""

    PASS = "pass"
    FAIL = "fail"
    NEEDS_HUMAN = "needs_human"


# Injectable per-step judgment. Pure data in, pure enum out; the engine core
# stays deterministic and unit-testable because tests supply a fixed/fake
# Judge instead of an LLM call. The router NEVER inspects ``payload`` — only
# the judge does, and only the judge's return value (constrained to
# ``Verdict``) reaches ``TRANSITIONS``.
Judge = Callable[[PipelineState, Mapping[str, Any]], "Verdict"]


# ---------------------------------------------------------------------------
# The deterministic transition table. This *is* the sequencing: checked-in
# data, not prose the orchestrator narrates and might drift from.
#
#   * GIT has NO entry for Verdict.PASS. The only path from GIT to GATE is
#     Engine.attempt_gate(attestation) -- a distinct method gated on a
#     verified-green Attestation (G-3.2), never on a Verdict returned by a
#     judge.
#   * GATE and ESCALATED are terminal: no key for them exists in this table
#     at all, i.e. no outgoing edge exists, structurally, not by
#     convention.
#   * HUMAN_QUESTION is deliberately absent as a key: no Verdict, from any
#     judge, produces a transition out of it via step(). The only way out
#     is the distinct Engine.answer_human_question(answer) method
#     (precept 10) -- "skipped twice" is impossible because there is only
#     ever one exit and step() cannot reach it.
# ---------------------------------------------------------------------------

TRANSITIONS: dict[PipelineState, dict[Verdict, PipelineState]] = {
    PipelineState.BRAINSTORM: {
        Verdict.PASS: PipelineState.PLAN,
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
    },
    PipelineState.PLAN: {
        Verdict.PASS: PipelineState.SPEC_REVIEW,
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
    },
    PipelineState.SPEC_REVIEW: {
        Verdict.PASS: PipelineState.TEST,
        Verdict.FAIL: PipelineState.SPEC_REVIEW,
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
    },
    PipelineState.TEST: {
        Verdict.PASS: PipelineState.CODE,
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
    },
    PipelineState.CODE: {
        Verdict.PASS: PipelineState.QUALITY,
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
    },
    PipelineState.QUALITY: {
        Verdict.PASS: PipelineState.GIT,
        Verdict.FAIL: PipelineState.QUALITY,
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
    },
    PipelineState.GIT: {
        Verdict.NEEDS_HUMAN: PipelineState.HUMAN_QUESTION,
        # Deliberately no Verdict.PASS entry. See module docstring.
    },
    # PipelineState.GATE: intentionally absent (terminal; G-3.2).
    # PipelineState.HUMAN_QUESTION: intentionally absent (precept 10).
    # PipelineState.ESCALATED: intentionally absent (terminal escalation sink).
}


# ---------------------------------------------------------------------------
# G-3.2: the attestation model. The gate/completion state has no incoming
# edge except from a verified-green attestation.
# ---------------------------------------------------------------------------


class AttestationStatus(str, Enum):
    ABSENT = "absent"
    PENDING = "pending"
    GREEN = "green"
    RED = "red"


@dataclass(frozen=True)
class Attestation:
    """The evidence G-3.2 requires: a pipeline id and its status, fetched by
    the engine/caller from the authoritative CI/verifier surface, never
    asserted by an agent. Plain value object; ``attempt_gate`` is the only
    method that reads one."""

    pipeline_id: str
    status: AttestationStatus


@dataclass(frozen=True)
class StepResult:
    """The outcome of one ``step()``, ``answer_human_question()`` or
    ``attempt_gate()`` call: the engine's new state, and whether this call
    was the one that hit a loop cap and escalated."""

    state: PipelineState
    escalated: bool = False


# ---------------------------------------------------------------------------
# Exceptions. All are fail-closed refusals: a raise, not a default-allow.
# ---------------------------------------------------------------------------


class EngineError(Exception):
    """Base for all engine faults."""


class InvalidVerdict(EngineError):
    """The judge returned something other than a ``Verdict`` member (e.g. a
    plain string like ``"skip review"``). Raised instead of coerced, so a
    judge that tries to smuggle a text instruction through the return value
    fails loudly rather than being interpreted as routing input."""


class NoSuchTransition(EngineError):
    """The current state has no transition for the given verdict (e.g. any
    verdict at all from GATE/ESCALATED/HUMAN_QUESTION, or PASS from GIT).
    Raised, never silently absorbed: absence of a code path is absence, not
    a default allow."""


class HumanGateBlocked(EngineError):
    """Raised by ``step()`` whenever ``state is PipelineState.HUMAN_QUESTION``.
    The only way past this state is ``answer_human_question()``."""


class AttestationRequired(EngineError):
    """``attempt_gate()`` was called with ``attestation=None``."""


class AttestationNotGreen(EngineError):
    """``attempt_gate()`` was called with an attestation that is absent,
    pending, red, or whose ``pipeline_id`` does not match the engine's own.
    Fail-closed: refusal is the default, and no field other than a matching
    ``pipeline_id`` plus ``status == AttestationStatus.GREEN`` can satisfy
    it. No amount of agent-supplied text anywhere else in the engine's
    history substitutes for this check."""


# ---------------------------------------------------------------------------
# The engine itself. Stub: every method raises NotImplementedError. See
# DESIGN.md for the full behavioural contract each docstring below commits
# to; tests/test_engine.py is written against that contract.
# ---------------------------------------------------------------------------


class Engine:
    """The G-5 deterministic orchestration engine.

    Construction and every method below are implemented against the
    behavioural contract encoded in ``tests/test_engine.py`` (see
    ``DESIGN.md`` for the full design record); the suite passes 49/49
    against this implementation.
    """

    def __init__(
        self,
        pipeline_id: str,
        loop_caps: Mapping[PipelineState, int] | None = None,
    ) -> None:
        """Start a new engine instance at ``PipelineState.BRAINSTORM``.

        ``loop_caps`` overrides ``DEFAULT_LOOP_CAP`` per state in
        ``LOOPING_STATES``; states not listed use the default. Per-state
        ``FAIL`` counters start at 0.
        """

        self.pipeline_id = pipeline_id
        self._state: PipelineState = PipelineState.BRAINSTORM

        caps: dict[PipelineState, int] = {
            looping_state: DEFAULT_LOOP_CAP for looping_state in LOOPING_STATES
        }
        if loop_caps:
            caps.update(loop_caps)
        self._loop_caps = caps
        self._loop_counts: dict[PipelineState, int] = {
            looping_state: 0 for looping_state in LOOPING_STATES
        }

        # Tracks which main-line state raised Verdict.NEEDS_HUMAN, so
        # answer_human_question() knows where to return control. None
        # whenever we are not awaiting an answer (including right after
        # one has just been consumed).
        self._human_question_origin: PipelineState | None = None

    @classmethod
    def resume_at(
        cls,
        pipeline_id: str,
        state: "PipelineState",
        loop_caps: Mapping["PipelineState", int] | None = None,
    ) -> "Engine":
        """Reconstruct an engine positioned at ``state``.

        This is **construction, not a transition** — it exists because a live
        pipeline outlives any single process (each opencode hook call is a
        fresh process), so the canonical state is the persisted bridge, and a
        new process must rehydrate the engine at that state rather than restart
        at ``BRAINSTORM``. It does not, and must not, become a general state
        setter: the only ways to *move* the engine remain ``step``,
        ``answer_human_question`` and ``attempt_gate``. ``state`` must be a
        real ``PipelineState`` member; anything else is rejected (fail-closed),
        never coerced.

        Loop-cap counters are reset to 0 on resume — the minimal slice does not
        persist per-state FAIL counts across processes; the bridge carries only
        the pipeline state. (A later slice may persist counters if cross-process
        loop-cap fidelity is required; called out honestly rather than faked.)
        """

        if not isinstance(state, PipelineState):
            raise InvalidVerdict(
                f"resume_at requires a PipelineState, got {state!r}"
            )
        engine = cls(pipeline_id, loop_caps=loop_caps)
        engine._state = state
        return engine

    @property
    def state(self) -> PipelineState:
        """The engine's current state. Read-only from outside; the only
        ways to change it are ``step()``, ``answer_human_question()`` and
        ``attempt_gate()`` (plus ``resume_at`` construction)."""

        return self._state

    def step(
        self, judge: Judge, payload: Mapping[str, Any] | None = None
    ) -> StepResult:
        """Call ``judge`` for the current state, then route deterministically.

        Contract (see DESIGN.md "Trace" and "Assemble"):
          * Calls ``judge(self.state, payload or {})`` exactly once.
          * The return value MUST be a ``Verdict`` member; anything else
            raises ``InvalidVerdict`` before any routing is attempted.
          * If ``self.state`` has no entry in ``TRANSITIONS``, raises
            ``NoSuchTransition`` (covers GATE, ESCALATED, HUMAN_QUESTION,
            and ``Verdict.PASS`` from GIT).
          * If ``self.state is PipelineState.HUMAN_QUESTION``, raises
            ``HumanGateBlocked`` unconditionally, before even calling
            ``judge`` -- this method is never a way past that state.
          * If the resolved edge is a self-loop on a state in
            ``LOOPING_STATES`` (``Verdict.FAIL`` on SPEC_REVIEW/QUALITY),
            increments that state's counter; if the counter has now
            reached its cap, transitions to ``ESCALATED`` instead of
            looping and returns ``StepResult(ESCALATED, escalated=True)``;
            otherwise loops and returns
            ``StepResult(state, escalated=False)``.
          * Every other resolved edge moves ``self.state`` to the mapped
            target and returns ``StepResult(new_state, escalated=False)``.
        """

        if self._state is PipelineState.HUMAN_QUESTION:
            raise HumanGateBlocked(
                "step() cannot be called while awaiting a human answer; "
                "use answer_human_question()."
            )

        verdict = judge(self._state, payload or {})
        if not isinstance(verdict, Verdict):
            raise InvalidVerdict(
                f"judge returned {verdict!r}, not a Verdict member"
            )

        edges = TRANSITIONS.get(self._state)
        if edges is None or verdict not in edges:
            raise NoSuchTransition(
                f"no transition for {verdict!r} from {self._state!r}"
            )

        target = edges[verdict]

        if verdict is Verdict.NEEDS_HUMAN:
            self._human_question_origin = self._state
            self._state = target
            return StepResult(state=target, escalated=False)

        if target is self._state and self._state in LOOPING_STATES:
            cap = self._loop_caps[self._state]
            self._loop_counts[self._state] += 1
            if self._loop_counts[self._state] >= cap:
                self._state = PipelineState.ESCALATED
                return StepResult(state=PipelineState.ESCALATED, escalated=True)
            return StepResult(state=self._state, escalated=False)

        self._state = target
        return StepResult(state=target, escalated=False)

    def answer_human_question(self, answer: Any) -> StepResult:
        """The ONLY way out of ``HUMAN_QUESTION`` (precept 10).

        Returns control to whichever state raised ``Verdict.NEEDS_HUMAN``.
        Raises ``EngineError`` if called while ``self.state`` is not
        ``PipelineState.HUMAN_QUESTION``.
        """

        if self._state is not PipelineState.HUMAN_QUESTION:
            raise EngineError(
                "answer_human_question() called while not awaiting a "
                "human answer."
            )
        if self._human_question_origin is None:
            # Defensive: should be unreachable if state bookkeeping is
            # correct, but never silently no-op past a missing origin.
            raise EngineError(
                "no pending human question to answer."
            )

        origin = self._human_question_origin
        self._human_question_origin = None
        self._state = origin
        return StepResult(state=origin, escalated=False)

    def attempt_gate(self, attestation: "Attestation | None") -> StepResult:
        """The ONLY way into ``GATE`` (G-3.2). Requires ``self.state is
        PipelineState.GIT``; raises ``EngineError`` otherwise, regardless of
        ``attestation``.

        Refuses (raises, ``self.state`` unchanged) unless ``attestation``
        is an ``Attestation`` instance (``AttestationRequired`` if ``None``,
        ``TypeError`` for any other type), its ``pipeline_id`` equals
        ``self.pipeline_id``, and its ``status`` is
        ``AttestationStatus.GREEN`` (``AttestationNotGreen`` otherwise).
        No field of any ``payload`` passed to ``step()`` anywhere in this
        engine's history is ever consulted here, and no other call in this
        class reads an ``Attestation`` at all.
        """

        if self._state is not PipelineState.GIT:
            raise EngineError(
                "attempt_gate() is only valid while state is "
                "PipelineState.GIT."
            )

        if attestation is None:
            raise AttestationRequired("attempt_gate() requires an Attestation.")
        if not isinstance(attestation, Attestation):
            raise TypeError(
                f"attempt_gate() requires an Attestation instance, got "
                f"{type(attestation)!r}."
            )
        if (
            attestation.status is not AttestationStatus.GREEN
            or attestation.pipeline_id != self.pipeline_id
        ):
            raise AttestationNotGreen(
                "attestation is not green for this engine's pipeline_id."
            )

        self._state = PipelineState.GATE
        return StepResult(state=PipelineState.GATE, escalated=False)

    def loop_count(self, state: PipelineState) -> int:
        """Read-only: how many ``Verdict.FAIL`` self-loops ``state`` has
        consumed so far in this engine instance. Exposed so tests and
        callers can observe the deterministic counter directly, without
        relying on side effects of ``step()`` alone."""

        return self._loop_counts.get(state, 0)
