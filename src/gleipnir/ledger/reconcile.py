"""Gleipnir G-4d metrics ledger — reconciliation (D4).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D4 + Assemble step 4 +
Stress-test check A. This is the executable form of Conformance [D]
"bus-emission gap" at slice scale.

``reconcile`` independently RE-DERIVES the one measured (revert) metric
directly from the raw bus JSONL — via the SAME typed read path
(`Event.from_json_line`), but a genuinely separate code path from
`reduce.py` — and asserts equality with the `LedgerReport`'s `Measured`
values. A divergence raises `LedgerError`: this is a contract violation
between two call sites over the same data (a programmer/consistency fault),
not a telemetry fault, so raising here is the correct posture (symmetric
with the D3 honesty types' fail-closed construction).

**Scope honesty (plan section 2.6):** this is SELF-CONSISTENCY, not
cross-source, reconciliation. It catches a divergence between two call
sites, but NOT a bug shared by both (e.g. a misread of the typed payload
both would make identically) -- there is no second ground-truth source yet.
Cross-source reconciliation is a named seam for when independent inputs
(runtime usage logs, the rate table) are wired in.

Also produces the explicit gap-report enumerating every not-yet-emitted
metric (delegates to `reduce.build_seam_gaps` so both call sites name the
same seams identically).

Stdlib-only (`.gleipnir/decisions/runtime-and-deps.md`): ``dataclasses``,
``pathlib``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gleipnir.bus.events import BusError, Event, EventKind
from gleipnir.ledger.metric import Gap, LedgerError
from gleipnir.ledger.reduce import LedgerReport, build_seam_gaps

__all__ = ["ReconciliationReport", "reconcile"]


@dataclass(frozen=True)
class ReconciliationReport:
    """The self-consistency re-derivation's result: the independently
    re-counted revert baseline (equal to the `LedgerReport`'s, by
    construction -- `reconcile` raises before returning on divergence), plus
    the canonical gap enumeration for every not-yet-emitted metric."""

    session_id: str | None
    revert_count: int
    escalation_count: int
    unreadable_line_count: int
    gaps: tuple[Gap, ...]


def _recount_from_raw_jsonl(
    session_log_path: str | Path,
) -> tuple[int, int, int, str | None]:
    """A SEPARATE re-implementation of the revert-count reduction over the
    raw JSONL, reading ONLY via `Event.from_json_line` (typed attribute
    access) -- deliberately not a call into `reduce.reduce`, so this is a
    genuine independent re-derivation, not the same code path re-run."""

    path = Path(session_log_path)
    revert_total = 0
    escalated_total = 0
    unreadable = 0
    session_id: str | None = None

    if path.is_file():
        # Read as BYTES and decode per line (same robustness as reduce.py): an
        # encoding-corrupt line is folded into `unreadable`, never a crash.
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
                if event.payload.escalated:
                    escalated_total += 1

    return revert_total, escalated_total, unreadable, session_id


def reconcile(session_log_path: str | Path, report: LedgerReport) -> ReconciliationReport:
    """Independently re-derive revert_count/escalation_count from the raw
    JSONL and assert equality with `report`'s `Measured` values.

    Raises `LedgerError` on divergence between the two call sites (a
    contract fault, correctly fail-closed). Returns the reconciled report
    (with the canonical seam-gap enumeration) when consistent.
    """

    revert_total, escalated_total, unreadable, session_id = _recount_from_raw_jsonl(
        session_log_path
    )

    if revert_total != report.revert_count.value:
        raise LedgerError(
            "reconciliation divergence on revert_count: "
            f"re-derived={revert_total!r} report={report.revert_count.value!r}"
        )
    if escalated_total != report.escalation_count.value:
        raise LedgerError(
            "reconciliation divergence on escalation_count: "
            f"re-derived={escalated_total!r} report={report.escalation_count.value!r}"
        )

    # Independently re-derive the escalation RATE from the re-derived counts,
    # applying the same zero-denominator convention as reduce.py (value=None,
    # the vacuous sentinel, when there are no reverts). Catches a rate-
    # arithmetic bug in reduce.py that leaves the raw counts correct.
    expected_rate = None if revert_total == 0 else escalated_total / revert_total
    if expected_rate != report.escalation_rate.value:
        raise LedgerError(
            "reconciliation divergence on escalation_rate: "
            f"re-derived={expected_rate!r} report={report.escalation_rate.value!r}"
        )

    return ReconciliationReport(
        session_id=session_id,
        revert_count=revert_total,
        escalation_count=escalated_total,
        unreadable_line_count=unreadable,
        gaps=build_seam_gaps(),
    )
