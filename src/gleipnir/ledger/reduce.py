"""Gleipnir G-4d metrics ledger — reduction skeleton + the one real metric (D1).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D1 + Assemble step 2 +
Stress-test checks A/A2/B/I.

``reduce(session_log_path) -> LedgerReport`` is a PURE function over one
session's bus JSONL. It reads events ONLY through the bus's typed read path
(``gleipnir.bus.events.Event.from_json_line``) — never a hand-rolled
``json.loads`` of a bus line, never a string/regex/substring parse of any
field. ``payload.escalated`` is read by typed attribute access.

Two postures, deliberately different (not inconsistent):
  * Tier-1 telemetry read is ROBUST: a missing log file is absence-of-
    telemetry, not a fault (empty reduction, no raise); a malformed line is
    skipped-and-counted (``unreadable_line_count``), never fails the whole
    reduction (mirrors the bus's own degrade-not-raise discipline).
  * The D3 honesty types (`metric.py`) are STRICT: they raise on
    uncalibrated construction. Robust on telemetry, fail-closed on contract.

Every G-4d metric with no source event kind yet on the bus (iterations,
retries, token usage, cost, effort attribution, efficiency, uplift) is an
explicit ``Gap`` with a reason — NEVER a fabricated zero. ``EventKind``
currently has only ``REVERT_OCCURRED`` (`bus/events.py`), so every one of
these is a genuine bus-emission gap, not a lazy omission.

Stdlib-only (`.gleipnir/decisions/runtime-and-deps.md`): ``json`` (output
serialization only — never used to read a bus line), ``dataclasses``,
``pathlib``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gleipnir.bus.events import BusError, Event, EventKind
from gleipnir.ledger.metric import Gap, Measured

__all__ = ["LedgerReport", "reduce", "SEAM_NAMES", "build_seam_gaps"]


# The named seams (D1): every G-4d metric this slice does NOT compute,
# because its source event kind does not exist on the bus yet. Reported as
# explicit Gaps, never fabricated zeros. "cost" is included here too (D2):
# it is a Gap unconditionally this slice, regardless of rate-table digest
# status -- see `ratetable.py` for the (separately tested, not-yet-wired)
# digest machinery that will eventually back this decision.
#
# "iterations"/"retries" (D6, `.gleipnir/plans/g4-terminal-events.md`): these
# reasons were rewritten by that plan. The engine has NO iteration counter
# and NO same-stage retry/self-loop concept -- `Verdict.FAIL` always routes
# BACKWARD to an earlier stage (a revert, already counted via
# `revert_occurred`/`revert_count`), never a same-stage self-loop; the
# retired per-state `loop_count`/`LOOPING_STATES` model is superseded. The
# engine's only cap is the global revert budget, and reaching it IS the
# escalated revert (already counted via `escalation_count`). So there is no
# distinct iteration-cap or retry FACT for the driver to observe and emit --
# not "no EventKind yet" (that phrasing implied a fact merely un-wired; the
# fact itself does not exist in the engine's model). These stay Gaps
# (deferred, not fabricated) rather than flipping to a redundant metric that
# would double-count what `revert_count`/`escalation_count` already carry.
_SEAM_REASONS: dict[str, str] = {
    "iterations": (
        "no iteration-cap fact exists to source this from -- the engine has "
        "no iteration counter (the retired per-state loop_count/"
        "LOOPING_STATES model was superseded); its only cap is the global "
        "revert budget, and reaching it IS the escalated revert already "
        "counted via escalation_count"
    ),
    "retries": (
        "no distinct retry fact exists to source this from -- Verdict.FAIL "
        "always routes backward to an earlier stage (a revert, already "
        "counted via revert_count), never a same-stage self-loop; the "
        "engine has no retry-in-place concept for the driver to observe"
    ),
    "token_usage": "no TokenUsageEvent kind on the bus yet",
    "cost": (
        "cost deferred until the S-2 mount makes the rate table structurally "
        "agent-unwritable (spec section 193) -- unconditional this slice, "
        "even when the rate-table digest verifies"
    ),
    "effort_attribution": "no EffortAttributionEvent kind on the bus yet",
    "efficiency": "no EfficiencyEvent kind on the bus yet",
    "uplift": (
        "no uplift estimate produced this slice -- the Estimated/"
        "CalibrationBand/NotionalHumanRate types are built and tested, but "
        "no uplift value is computed yet"
    ),
}

SEAM_NAMES: tuple[str, ...] = tuple(_SEAM_REASONS)


def build_seam_gaps() -> tuple[Gap, ...]:
    """The canonical list of bus-emission-gap metrics. Shared by `reduce`
    and `reconcile.py`'s independent gap-report so the two call sites name
    the same seams identically."""

    return tuple(Gap(name=name, reason=reason) for name, reason in _SEAM_REASONS.items())


@dataclass(frozen=True)
class LedgerReport:
    """The first-slice ledger report: the one honestly-measured revert
    baseline, plus an explicit Gap for every not-yet-emitted metric.

    ``revert_count`` / ``escalation_count`` are raw counts (``denominator``
    conventionally ``1`` — "counted directly", not a ratio).
    ``escalation_rate`` is the derived ratio; its ``denominator`` is
    ``revert_count`` and follows the zero-denominator convention (edge case
    6): when ``revert_count == 0`` the rate is a vacuous ``Measured`` with
    ``value=None`` and ``denominator=0`` — never a fabricated ``0.0``.

    ``human_question_count`` / ``gate_reached_count``
    (`.gleipnir/plans/g4-terminal-events.md` D5) are two further raw counts
    (``denominator=1``, same convention as ``revert_count``), sourced from
    the ``NEEDS_HUMAN_RAISED`` / ``GATE_REACHED`` event kinds. An empty/
    missing log yields a genuine ``Measured(0, 1)`` for both — a measured
    zero, never a ``Gap``.
    """

    session_id: str | None
    revert_count: Measured
    escalation_count: Measured
    escalation_rate: Measured
    human_question_count: Measured
    gate_reached_count: Measured
    gaps: tuple[Gap, ...]
    unreadable_line_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "revert_count": self.revert_count.to_dict(),
            "escalation_count": self.escalation_count.to_dict(),
            "escalation_rate": self.escalation_rate.to_dict(),
            "human_question_count": self.human_question_count.to_dict(),
            "gate_reached_count": self.gate_reached_count.to_dict(),
            "gaps": [g.to_dict() for g in self.gaps],
            "unreadable_line_count": self.unreadable_line_count,
        }

    def to_json(self) -> str:
        """Canonical form, matching `verify/marker.py` / bus's
        ``json.dumps(..., sort_keys=True, separators=(",", ":"))`` pattern."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def reduce(session_log_path: str | Path) -> LedgerReport:
    """Pure function: one session's bus JSONL -> a `LedgerReport`.

    Reads events ONLY via `Event.from_json_line` -- attribute access on the
    typed payload, never a hand-rolled JSON parse or a string/substring
    parse of any field.

    Edge cases (plan section 2.5):
      * Missing file -> treated as zero events (an absence-of-telemetry
        fact, not a fault). Not an exception.
      * Empty file -> a real `Measured(0, 0)` revert baseline (a genuine
        measured zero, distinct from a Gap).
      * A malformed line (`Event.from_json_line` raises `BusError`) is
        skipped and counted in `unreadable_line_count`; the reduction keeps
        going over the remaining lines.
    """

    path = Path(session_log_path)
    revert_total = 0
    escalated_total = 0
    human_question_total = 0
    gate_reached_total = 0
    unreadable = 0
    session_id: str | None = None

    if path.is_file():
        # Read as BYTES and decode per line, so a single encoding-corrupt line
        # (e.g. a process killed mid-write across a multibyte boundary) is
        # folded into `unreadable` like a malformed JSON line -- it must NOT
        # blind the ledger to every valid line before/after it (edge case 3).
        for raw in path.read_bytes().splitlines():
            if not raw.strip():
                continue
            try:
                line = raw.decode("utf-8")
                event = Event.from_json_line(line)
            except (BusError, UnicodeDecodeError):
                unreadable += 1
                continue
            if session_id is None:
                session_id = event.envelope.session_id
            if event.kind is EventKind.REVERT_OCCURRED:
                revert_total += 1
                # Typed attribute access -- never a string match on to_state.
                if event.payload.escalated:
                    escalated_total += 1
            elif event.kind is EventKind.NEEDS_HUMAN_RAISED:
                # Typed kind check -- never a string match on payload.from_state.
                human_question_total += 1
            elif event.kind is EventKind.GATE_REACHED:
                # Typed kind check -- never a string match on payload.pipeline_id.
                gate_reached_total += 1

    revert_count = Measured(
        name="revert_count",
        value=revert_total,
        denominator=1,
        provenance="bus:revert_occurred count",
    )
    escalation_count = Measured(
        name="escalation_count",
        value=escalated_total,
        denominator=1,
        provenance="bus:revert_occurred escalated=True count",
    )

    if revert_total == 0:
        # Zero-denominator convention (edge case 6): a vacuous sentinel, NOT
        # a fabricated 0.0 -- "no reverts observed" must never read as "0%
        # escalation".
        escalation_rate = Measured(
            name="escalation_rate",
            value=None,
            denominator=0,
            provenance="vacuous: no reverts observed (0/0)",
        )
    else:
        # A genuine measured rate: reverts were observed, so a real (possibly
        # zero) escalation_count/revert_count is meaningful.
        escalation_rate = Measured(
            name="escalation_rate",
            value=escalated_total / revert_total,
            denominator=revert_total,
            provenance="bus:revert_occurred escalated_count/revert_count",
        )

    # Two honest raw counts (D5): denominator=1, mirroring revert_count's
    # construction. An empty/missing log yields a genuine Measured(0, 1) for
    # both -- a measured zero, never a Gap (edge case, `g4-terminal-events.md`).
    human_question_count = Measured(
        name="human_question_count",
        value=human_question_total,
        denominator=1,
        provenance="bus:needs_human_raised count",
    )
    gate_reached_count = Measured(
        name="gate_reached_count",
        value=gate_reached_total,
        denominator=1,
        provenance="bus:gate_reached count",
    )

    return LedgerReport(
        session_id=session_id,
        revert_count=revert_count,
        escalation_count=escalation_count,
        escalation_rate=escalation_rate,
        human_question_count=human_question_count,
        gate_reached_count=gate_reached_count,
        gaps=build_seam_gaps(),
        unreadable_line_count=unreadable,
    )
