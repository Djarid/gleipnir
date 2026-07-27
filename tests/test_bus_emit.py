"""Tests for the G-4 event bus emit/append API (`src/gleipnir/bus/emit.py`).

Plan: `.gleipnir/plans/g4-bus-first-slice.md`, Assemble step 3 / Stress-test
checks 4, 5, 9, 10. Written RED-first, before `src/gleipnir/bus/emit.py`
exists.

Covers:
  - `emit` appends exactly one valid JSONL line to
    `.gleipnir/logs/<session_id>.jsonl`.
  - A second emit appends a second line with `sequence` incremented.
  - `logs/` dir is auto-created when absent.
  - The file is per-session (two sessions -> two files).
  - Un-writable `logs/` -> `emit` degrades (returns failure, does not
    raise) and increments `dropped`.
"""

from __future__ import annotations

import json
from pathlib import Path

from gleipnir.bus.emit import EmitResult, EventBus
from gleipnir.bus.events import EventKind, RevertOccurredEvent


def _payload() -> RevertOccurredEvent:
    return RevertOccurredEvent(
        from_state="test", to_state="spec_review", revert_count=1, escalated=False
    )


def _emit_one(bus: EventBus, **overrides) -> EmitResult:
    kwargs = dict(
        emitter="engine.driver",
        enforcement_surface="engine",
        agent="gleipnir-code",
        action="revert_occurred",
        originating_turn=1,
        artifact_ref="pl-test-1",
    )
    kwargs.update(overrides)
    return bus.emit(EventKind.REVERT_OCCURRED, _payload(), **kwargs)


class TestEmitAppendsJsonl:
    def test_emit_creates_logs_dir_when_absent(self, tmp_path: Path):
        logs_dir = tmp_path / "logs"
        assert not logs_dir.exists()

        bus = EventBus("session-1", logs_dir=logs_dir)
        result = _emit_one(bus)

        assert result.ok is True
        assert logs_dir.is_dir()

    def test_emit_appends_one_valid_json_line(self, tmp_path: Path):
        logs_dir = tmp_path / "logs"
        bus = EventBus("session-1", logs_dir=logs_dir)
        _emit_one(bus)

        path = logs_dir / "session-1.jsonl"
        assert path.exists()
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["session_id"] == "session-1"
        assert parsed["sequence"] == 1

    def test_second_emit_appends_second_line_with_incremented_sequence(
        self, tmp_path: Path
    ):
        logs_dir = tmp_path / "logs"
        bus = EventBus("session-1", logs_dir=logs_dir)
        _emit_one(bus)
        _emit_one(bus)

        path = logs_dir / "session-1.jsonl"
        lines = path.read_text().splitlines()
        assert len(lines) == 2
        seq1 = json.loads(lines[0])["sequence"]
        seq2 = json.loads(lines[1])["sequence"]
        assert seq2 == seq1 + 1

    def test_two_sessions_produce_two_distinct_files(self, tmp_path: Path):
        logs_dir = tmp_path / "logs"
        bus_a = EventBus("session-a", logs_dir=logs_dir)
        bus_b = EventBus("session-b", logs_dir=logs_dir)
        _emit_one(bus_a)
        _emit_one(bus_b)

        assert (logs_dir / "session-a.jsonl").exists()
        assert (logs_dir / "session-b.jsonl").exists()
        assert (logs_dir / "session-a.jsonl") != (logs_dir / "session-b.jsonl")

    def test_emit_result_carries_the_built_event(self, tmp_path: Path):
        logs_dir = tmp_path / "logs"
        bus = EventBus("session-1", logs_dir=logs_dir)
        result = _emit_one(bus)

        assert result.event is not None
        assert result.event.kind is EventKind.REVERT_OCCURRED
        assert result.event.envelope.session_id == "session-1"


class TestEmitDegradesOnUnwritableLogs:
    def test_unwritable_logs_dir_degrades_and_increments_dropped(
        self, tmp_path: Path
    ):
        # logs_dir path collides with an existing FILE, so mkdir(parents=True,
        # exist_ok=True) raises FileExistsError (an OSError subclass) --
        # portable across platforms/UIDs, unlike a chmod-based test.
        blocked = tmp_path / "logs_is_actually_a_file"
        blocked.write_text("not a directory")

        bus = EventBus("session-1", logs_dir=blocked)
        assert bus.dropped == 0

        result = _emit_one(bus)  # must NOT raise

        assert result.ok is False
        assert bus.dropped == 1

    def test_repeated_failures_keep_incrementing_dropped(self, tmp_path: Path):
        blocked = tmp_path / "logs_is_actually_a_file"
        blocked.write_text("not a directory")
        bus = EventBus("session-1", logs_dir=blocked)

        _emit_one(bus)
        _emit_one(bus)
        _emit_one(bus)

        assert bus.dropped == 3
