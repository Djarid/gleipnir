"""Tests for G-4d ledger reconciliation (`src/gleipnir/ledger/reconcile.py`).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D4 + Assemble step 4 +
Stress-test check A/C. Written RED-first, before `reconcile.py` existed.

Covers:
  - `reconcile` independently re-derives revert_count/escalation_count from
    the raw JSONL and agrees with `reduce()`'s `LedgerReport`.
  - A divergence between the two call sites raises `LedgerError`.
  - The gap-report enumerates every non-revert metric as an explicit `Gap`.
"""

from __future__ import annotations

import ast
import dataclasses
import sys
from pathlib import Path

import pytest

from gleipnir.bus.emit import EventBus
from gleipnir.bus.events import (
    EventKind,
    GateReachedEvent,
    NeedsHumanRaisedEvent,
    RevertOccurredEvent,
)
from gleipnir.ledger.metric import Gap, LedgerError, Measured
from gleipnir.ledger.reconcile import ReconciliationReport, reconcile
from gleipnir.ledger.reduce import SEAM_NAMES, reduce

RECONCILE_SOURCE_PATH = Path(sys.modules["gleipnir.ledger.reconcile"].__file__)


def _bus(tmp_path, session_id="session-1"):
    return EventBus(session_id, logs_dir=tmp_path / "logs")


def _emit_revert(bus, *, escalated=False):
    payload = RevertOccurredEvent(
        from_state="test", to_state="code", revert_count=1, escalated=escalated
    )
    result = bus.emit(
        EventKind.REVERT_OCCURRED,
        payload,
        emitter="engine.driver",
        enforcement_surface="engine",
        action="revert_occurred",
    )
    assert result.ok is True


def _emit_needs_human(bus, *, from_state="test"):
    payload = NeedsHumanRaisedEvent(from_state=from_state)
    result = bus.emit(
        EventKind.NEEDS_HUMAN_RAISED,
        payload,
        emitter="engine.driver",
        enforcement_surface="engine",
        action="needs_human_raised",
    )
    assert result.ok is True


def _emit_gate_reached(bus, *, pipeline_id="pl-1"):
    payload = GateReachedEvent(pipeline_id=pipeline_id)
    result = bus.emit(
        EventKind.GATE_REACHED,
        payload,
        emitter="engine.driver",
        enforcement_surface="engine",
        action="gate_reached",
    )
    assert result.ok is True


class TestReconciliationAgreesWithReduce:
    def test_reconcile_matches_reduced_report(self, tmp_path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)
        result = reconcile(bus.path, report)

        assert isinstance(result, ReconciliationReport)
        assert result.revert_count == report.revert_count.value
        assert result.escalation_count == report.escalation_count.value

    def test_reconcile_matches_on_empty_log(self, tmp_path):
        log = tmp_path / "empty.jsonl"
        log.write_text("")
        report = reduce(log)
        result = reconcile(log, report)
        assert result.revert_count == 0
        assert result.escalation_count == 0
        assert result.human_question_count == 0
        assert result.gate_reached_count == 0

    def test_reconcile_matches_with_malformed_lines_present(self, tmp_path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        with open(bus.path, "a", encoding="utf-8") as fh:
            fh.write("not valid json\n")
        _emit_revert(bus, escalated=False)

        report = reduce(bus.path)
        result = reconcile(bus.path, report)

        assert result.revert_count == 2
        assert result.escalation_count == 1
        assert result.unreadable_line_count == 1

    def test_reconcile_matches_needs_human_and_gate_reached_counts(self, tmp_path):
        """G-4 terminal-events slice (D7, `g4-terminal-events.md`): reconcile
        independently re-derives human_question_count/gate_reached_count and
        agrees with reduce()'s report."""

        bus = _bus(tmp_path)
        _emit_needs_human(bus, from_state="test")
        _emit_needs_human(bus, from_state="quality")
        _emit_gate_reached(bus, pipeline_id="pl-1")
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)
        result = reconcile(bus.path, report)

        assert result.human_question_count == report.human_question_count.value == 2
        assert result.gate_reached_count == report.gate_reached_count.value == 1


class TestReconciliationDivergenceRaises:
    def test_divergent_revert_count_raises_ledger_error(self, tmp_path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=False)
        report = reduce(bus.path)

        # Fabricate a divergent report (simulating a bug at one call site).
        tampered = dataclasses.replace(
            report,
            revert_count=Measured(
                name="revert_count", value=99, denominator=1, provenance="tampered"
            ),
        )

        with pytest.raises(LedgerError):
            reconcile(bus.path, tampered)

    def test_divergent_escalation_count_raises_ledger_error(self, tmp_path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=False)
        report = reduce(bus.path)

        tampered = dataclasses.replace(
            report,
            escalation_count=Measured(
                name="escalation_count", value=99, denominator=1, provenance="tampered"
            ),
        )

        with pytest.raises(LedgerError):
            reconcile(bus.path, tampered)

    def test_divergent_escalation_rate_raises_ledger_error(self, tmp_path):
        """Reconciliation re-derives the RATE, not just the raw counts, so a
        rate-arithmetic bug that leaves the counts correct is still caught."""

        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        report = reduce(bus.path)

        # Counts stay correct; only the rate is tampered.
        tampered = dataclasses.replace(
            report,
            escalation_rate=Measured(
                name="escalation_rate", value=0.0, denominator=1, provenance="tampered"
            ),
        )

        with pytest.raises(LedgerError):
            reconcile(bus.path, tampered)

    def test_divergent_human_question_count_raises_ledger_error(self, tmp_path):
        """D7: a reduce()-metric with no matching reconcile() re-derivation
        would silently break the two-call-site consistency invariant; this
        proves reconcile() actually re-derives and checks it."""

        bus = _bus(tmp_path)
        _emit_needs_human(bus)
        report = reduce(bus.path)

        tampered = dataclasses.replace(
            report,
            human_question_count=Measured(
                name="human_question_count",
                value=99,
                denominator=1,
                provenance="tampered",
            ),
        )

        with pytest.raises(LedgerError):
            reconcile(bus.path, tampered)

    def test_divergent_gate_reached_count_raises_ledger_error(self, tmp_path):
        bus = _bus(tmp_path)
        _emit_gate_reached(bus)
        report = reduce(bus.path)

        tampered = dataclasses.replace(
            report,
            gate_reached_count=Measured(
                name="gate_reached_count",
                value=99,
                denominator=1,
                provenance="tampered",
            ),
        )

        with pytest.raises(LedgerError):
            reconcile(bus.path, tampered)


class TestGapReportEnumeratesEveryNonRevertMetric:
    def test_gap_report_covers_every_named_seam(self, tmp_path):
        bus = _bus(tmp_path)
        _emit_revert(bus)
        report = reduce(bus.path)
        result = reconcile(bus.path, report)

        assert {g.name for g in result.gaps} == set(SEAM_NAMES)
        for gap in result.gaps:
            assert isinstance(gap, Gap)
            assert gap.reason

    def test_gap_report_entries_are_gaps_not_measured_zeros(self, tmp_path):
        log = tmp_path / "empty.jsonl"
        log.write_text("")
        report = reduce(log)
        result = reconcile(log, report)

        for gap in result.gaps:
            assert not isinstance(gap, Measured)


class TestReadPathIsNotProseParsing:
    """`reconcile.py` independently re-reads the raw JSONL; it must use the
    same typed-attribute discipline as `reduce.py` (no `re`, no `.split`, no
    hand-rolled `json.loads` of a bus line) so this second call site cannot
    silently regress into string-parsing."""

    def test_reconcile_source_has_no_regex_or_split_or_json_loads(self):
        source = RECONCILE_SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name != "re" for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module != "re"
            if isinstance(node, ast.Attribute) and node.attr in ("split", "loads"):
                pytest.fail(
                    "reconcile.py must read bus lines only via "
                    "Event.from_json_line -- no split/json.loads/regex"
                )
