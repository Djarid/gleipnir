"""Tests for the G-4d ledger reduction skeleton (`src/gleipnir/ledger/reduce.py`).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D1 + Assemble step 2 +
Stress-test checks A/A2/B/C/I. Written RED-first, before `reduce.py` existed.

Covers:
  - Revert-only stream -> correct Measured revert_count/escalation_count,
    escalation_count read via `payload.escalated` (typed attribute).
  - Empty file -> real Measured(0, 0) + all seam Gaps.
  - Missing file -> empty reduction (no raise) + all seam Gaps.
  - Malformed line among valid ones -> skipped-and-counted, no raise.
  - Zero-denominator escalation-rate convention (0/0 vacuous sentinel vs. a
    genuine 0.0 with reverts present).
  - Every non-revert metric is an explicit Gap, never Measured(0).
  - No `re` import / no `.split(` in reduce.py (typed-attribute discipline).
  - No cost NUMBER ever appears in the serialized report.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from gleipnir.bus.emit import EventBus
from gleipnir.bus.events import EventKind, RevertOccurredEvent
from gleipnir.ledger.metric import Gap, Measured
from gleipnir.ledger.reduce import SEAM_NAMES, LedgerReport, build_seam_gaps, reduce

REDUCE_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "ledger" / "reduce.py"
)


def _bus(tmp_path: Path, session_id: str = "session-1") -> EventBus:
    return EventBus(session_id, logs_dir=tmp_path / "logs")


def _emit_revert(bus: EventBus, *, escalated: bool = False) -> None:
    payload = RevertOccurredEvent(
        from_state="test", to_state="code", revert_count=1, escalated=escalated
    )
    result = bus.emit(
        EventKind.REVERT_OCCURRED,
        payload,
        emitter="engine.driver",
        enforcement_surface="engine",
        action="revert_occurred",
        agent="gleipnir-code",
        originating_turn=1,
        artifact_ref="pl-test-1",
    )
    assert result.ok is True


# ---------------------------------------------------------------------------
# Assemble step 2 fixture (a): revert-only stream.
# ---------------------------------------------------------------------------


class TestRevertOnlyStream:
    def test_revert_count_and_escalation_count_correct(self, tmp_path: Path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)

        assert isinstance(report.revert_count, Measured)
        assert report.revert_count.value == 3
        assert isinstance(report.escalation_count, Measured)
        assert report.escalation_count.value == 2

    def test_escalation_counted_via_typed_attribute_not_string_match(
        self, tmp_path: Path
    ):
        """Mixed escalated=True/False reverts yield the correct count; the
        source contains no `re` import and no `.split(`/substring parse of
        event fields (AST/grep, mirroring the bus discipline)."""

        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=True)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=True)
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)
        assert report.escalation_count.value == 3
        assert report.revert_count.value == 5

        source = REDUCE_SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name != "re" for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module != "re"
            if isinstance(node, ast.Attribute) and node.attr == "split":
                pytest.fail(
                    "reduce.py must read fields by attribute access, not by "
                    "splitting a message string"
                )

    def test_reduce_never_calls_json_loads_directly(self):
        """`reduce.py` must read bus lines ONLY via `Event.from_json_line` —
        never a hand-rolled `json.loads` of a bus line."""

        source = REDUCE_SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "loads":
                pytest.fail(
                    "reduce.py must never call json.loads directly on a bus "
                    "line -- Event.from_json_line is the only door in"
                )


# ---------------------------------------------------------------------------
# Assemble step 2 fixture (b): empty file.
# ---------------------------------------------------------------------------


class TestEmptyLog:
    def test_empty_file_yields_real_measured_zero(self, tmp_path: Path):
        log = tmp_path / "session-empty.jsonl"
        log.write_text("")

        report = reduce(log)

        assert report.revert_count.value == 0
        assert report.escalation_count.value == 0

    def test_empty_file_yields_all_seam_gaps(self, tmp_path: Path):
        log = tmp_path / "session-empty.jsonl"
        log.write_text("")

        report = reduce(log)

        gap_names = {g.name for g in report.gaps}
        assert gap_names == set(SEAM_NAMES)
        for gap in report.gaps:
            assert isinstance(gap, Gap)
            assert gap.reason


# ---------------------------------------------------------------------------
# Assemble step 2 fixture (c): missing file -> empty reduction, no raise.
# ---------------------------------------------------------------------------


class TestMissingLog:
    def test_missing_file_is_not_an_error(self, tmp_path: Path):
        missing = tmp_path / "does-not-exist.jsonl"
        assert not missing.exists()

        report = reduce(missing)  # must NOT raise

        assert report.revert_count.value == 0
        assert report.escalation_count.value == 0
        assert {g.name for g in report.gaps} == set(SEAM_NAMES)


# ---------------------------------------------------------------------------
# Assemble step 2 fixture (d): malformed line among valid ones.
# ---------------------------------------------------------------------------


class TestMalformedLine:
    def test_malformed_line_is_skipped_and_counted(self, tmp_path: Path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=False)
        with open(bus.path, "a", encoding="utf-8") as fh:
            fh.write("{ not valid json at all\n")
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)

        assert report.unreadable_line_count == 1
        assert report.revert_count.value == 2
        assert report.escalation_count.value == 1

    def test_multiple_malformed_lines_all_counted(self, tmp_path: Path):
        bus = _bus(tmp_path)
        _emit_revert(bus)
        with open(bus.path, "a", encoding="utf-8") as fh:
            fh.write("not json\n")
            fh.write("{}\n")  # valid JSON, but missing 'kind' -> BusError
        report = reduce(bus.path)
        assert report.unreadable_line_count == 2
        assert report.revert_count.value == 1

    def test_encoding_corrupt_line_does_not_blind_the_whole_reduction(
        self, tmp_path: Path
    ):
        """A single invalid-UTF-8 line (e.g. a process killed mid-write across
        a multibyte boundary) must be counted as unreadable and skipped -- it
        must NOT crash the reduction and blind the ledger to the valid lines
        before and after it."""

        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=False)
        with open(bus.path, "ab") as fh:
            fh.write(b"\xff\xfe not valid utf-8\n")
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)  # must not raise UnicodeDecodeError

        assert report.unreadable_line_count == 1
        assert report.revert_count.value == 2
        assert report.escalation_count.value == 1


# ---------------------------------------------------------------------------
# Assemble step 2 fixtures (e)/(f) + Stress-test A2: zero-denominator
# escalation-rate convention.
# ---------------------------------------------------------------------------


class TestEscalationRateZeroDenominatorConvention:
    def test_zero_revert_gives_vacuous_sentinel_not_fabricated_zero(
        self, tmp_path: Path
    ):
        """No RevertOccurredEvents at all: revert_count == 0. The
        escalation_rate must be a vacuous Measured(value=None,
        denominator=0) -- NEVER a misleading 0.0."""

        log = tmp_path / "session-zero-revert.jsonl"
        log.write_text("")

        report = reduce(log)

        assert report.revert_count.value == 0
        assert report.escalation_rate.denominator == 0
        assert report.escalation_rate.value is None

    def test_revert_only_but_zero_escalated_gives_genuine_measured_zero(
        self, tmp_path: Path
    ):
        """Reverts ARE present, but none escalated: revert_count > 0,
        escalation_count == 0. This is a genuine measured 0.0 rate with a
        real (nonzero) denominator -- distinguished in value from the
        zero-revert vacuous case above."""

        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=False)

        report = reduce(bus.path)

        assert report.revert_count.value == 2
        assert report.escalation_count.value == 0
        assert report.escalation_rate.denominator == 2
        assert report.escalation_rate.value == 0.0
        assert report.escalation_rate.value is not None

    def test_nonzero_escalation_rate_is_a_real_fraction(self, tmp_path: Path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=False)
        _emit_revert(bus, escalated=False)

        report = reduce(bus.path)

        assert report.escalation_rate.denominator == 4
        assert report.escalation_rate.value == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Stress-test check C: every non-revert metric is an explicit Gap, never a
# Measured(value=0).
# ---------------------------------------------------------------------------


class TestNonRevertMetricsAreExplicitGaps:
    EXPECTED_SEAMS = {
        "iterations",
        "retries",
        "token_usage",
        "cost",
        "effort_attribution",
        "efficiency",
        "uplift",
    }

    def test_seam_names_match_expected_set(self):
        assert set(SEAM_NAMES) == self.EXPECTED_SEAMS

    def test_report_gaps_cover_every_seam_as_a_gap_not_a_measured_zero(
        self, tmp_path: Path
    ):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)

        report = reduce(bus.path)

        gap_by_name = {g.name: g for g in report.gaps}
        assert set(gap_by_name) == self.EXPECTED_SEAMS
        for name, gap in gap_by_name.items():
            assert isinstance(gap, Gap), f"{name} must be a Gap, not a Measured"
            assert not isinstance(gap, Measured)
            assert gap.reason, f"{name} gap must carry a non-empty reason"

    def test_build_seam_gaps_is_the_shared_canonical_list(self):
        gaps = build_seam_gaps()
        assert {g.name for g in gaps} == self.EXPECTED_SEAMS


# ---------------------------------------------------------------------------
# Stress-test check H: NO cost number emitted, ever, this slice.
# ---------------------------------------------------------------------------


class TestNoCostNumberEmitted:
    def test_cost_slot_is_always_a_gap(self, tmp_path: Path):
        bus = _bus(tmp_path)
        _emit_revert(bus)
        report = reduce(bus.path)

        cost_entries = [g for g in report.gaps if g.name == "cost"]
        assert len(cost_entries) == 1
        assert isinstance(cost_entries[0], Gap)

    def test_serialized_report_cost_slot_has_no_numeric_value_key(
        self, tmp_path: Path
    ):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        report = reduce(bus.path)

        parsed = json.loads(report.to_json())
        cost_dict = next(g for g in parsed["gaps"] if g["name"] == "cost")
        assert cost_dict["kind"] == "gap"
        assert "value" not in cost_dict

    def test_a_distinctive_rate_number_never_leaks_into_the_report(
        self, tmp_path: Path
    ):
        """Even though this test constructs a plausible rate-table-shaped
        number, `reduce()` never touches `ratetable.py` at all this slice --
        so the number cannot appear in the serialized report by
        construction. This proves the invariant, not just asserts a lucky
        absence."""

        distinctive_rate = "123456.789"
        bus = _bus(tmp_path)
        _emit_revert(bus)
        report = reduce(bus.path)

        assert distinctive_rate not in report.to_json()


# ---------------------------------------------------------------------------
# session_id capture.
# ---------------------------------------------------------------------------


class TestSessionIdCapture:
    def test_session_id_captured_from_first_valid_event(self, tmp_path: Path):
        bus = _bus(tmp_path, session_id="session-xyz")
        _emit_revert(bus)
        report = reduce(bus.path)
        assert report.session_id == "session-xyz"

    def test_session_id_is_none_when_no_events(self, tmp_path: Path):
        log = tmp_path / "empty.jsonl"
        log.write_text("")
        report = reduce(log)
        assert report.session_id is None


# ---------------------------------------------------------------------------
# LedgerReport is a real (frozen) dataclass, not a loose dict.
# ---------------------------------------------------------------------------


class TestLedgerReportShape:
    def test_report_is_frozen(self, tmp_path: Path):
        log = tmp_path / "empty.jsonl"
        log.write_text("")
        report = reduce(log)
        with pytest.raises(Exception):
            report.unreadable_line_count = 99  # type: ignore[misc]

    def test_to_json_round_trips_through_json_loads(self, tmp_path: Path):
        bus = _bus(tmp_path)
        _emit_revert(bus, escalated=True)
        report = reduce(bus.path)
        parsed = json.loads(report.to_json())
        assert parsed["revert_count"]["value"] == 1
        assert parsed["escalation_count"]["value"] == 1
