"""Tests: the G-5 driver emits G-4 `RevertOccurredEvent`s on revert hops.

Plan: `.gleipnir/plans/g4-bus-first-slice.md`, Assemble step 5 / Stress-test
checks 6-8, 12. Written RED-first, before `driver.py` is wired to the bus.

Covers:
  6. A normal backward revert (FAIL judge, below budget) emits a
     `RevertOccurredEvent` with correct from/to/count + provenance.
  7. The budget-exhausting hop (FAIL to EXACTLY the budget) does NOT raise
     and emits `to_state == ESCALATED`, `escalated is True`,
     `revert_count == budget`.
  8. A NEEDS_HUMAN step does not raise and emits NO revert event.
  12. A driver constructed WITHOUT a bus still works; `Engine.step` is
      unmodified (engine imports no `bus`).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Mapping

import pytest

from gleipnir import engine as engine_pkg
from gleipnir.bus import Event, EventBus, EventKind, RevertOccurredEvent
from gleipnir.engine import (
    DEFAULT_REVERT_BUDGET,
    PipelineState,
    StepResult,
    Verdict,
)
from gleipnir.engine.driver import Driver

VERIFIER_KEY = b"verifier-only-secret-key-not-on-agent-surface"
PIPELINE_ID = "pl-bus-driver-test-1"


class FixedJudge:
    """Always returns the same verdict, ignoring state and payload (mirrors
    `tests/test_engine.py::FixedJudge`)."""

    def __init__(self, verdict: Verdict) -> None:
        self.verdict = verdict

    def __call__(self, _state: PipelineState, _payload: Mapping[str, Any]) -> Verdict:
        return self.verdict


def make_pass_judge() -> FixedJudge:
    return FixedJudge(Verdict.PASS)


def drive_to(driver: Driver, target: PipelineState) -> None:
    """Advance ``driver`` from its current state to ``target`` via an
    all-PASS judge (mirrors `tests/test_engine.py::drive_to`, through the
    driver instead of the bare engine)."""

    while driver.state is not target:
        driver.advance(make_pass_judge())


def _read_events(logs_dir: Path, session_id: str) -> list[Event]:
    path = logs_dir / f"{session_id}.jsonl"
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    return [Event.from_json_line(line) for line in lines]


@pytest.fixture
def key_file(tmp_path: Path) -> Path:
    kf = tmp_path / "key"
    kf.write_bytes(VERIFIER_KEY)
    return kf


@pytest.fixture
def bridge_path(tmp_path: Path) -> Path:
    return tmp_path / "var" / "run" / "pipeline-state.json"


# ---------------------------------------------------------------------------
# 6. Normal backward revert.
# ---------------------------------------------------------------------------


def test_normal_backward_revert_emits_revert_occurred_event(
    tmp_path, bridge_path, key_file
):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-normal-revert", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    drive_to(driver, PipelineState.SPEC_REVIEW)
    result = driver.advance(
        FixedJudge(Verdict.FAIL), agent="gleipnir-code", originating_turn=7
    )

    assert isinstance(result, StepResult)
    assert result.state is PipelineState.PLAN
    assert result.escalated is False

    events = _read_events(logs_dir, "session-normal-revert")
    assert len(events) == 1
    evt = events[0]
    assert evt.kind is EventKind.REVERT_OCCURRED
    assert isinstance(evt.payload, RevertOccurredEvent)
    assert evt.payload.from_state == PipelineState.SPEC_REVIEW.value
    assert evt.payload.to_state == PipelineState.PLAN.value
    assert evt.payload.escalated is False
    assert evt.payload.revert_count == 1
    assert evt.payload.revert_count == driver.engine.revert_count
    assert evt.envelope.agent == "gleipnir-code"
    assert evt.envelope.originating_turn == 7
    assert evt.envelope.session_id == "session-normal-revert"
    assert evt.envelope.artifact_ref == PIPELINE_ID


def test_multiple_reverts_increment_sequence_and_revert_count(
    tmp_path, bridge_path, key_file
):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-multi-revert", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    drive_to(driver, PipelineState.QUALITY)
    driver.advance(FixedJudge(Verdict.FAIL))  # QUALITY -> CODE, revert_count 1
    drive_to(driver, PipelineState.QUALITY)
    driver.advance(FixedJudge(Verdict.FAIL))  # QUALITY -> CODE, revert_count 2

    events = _read_events(logs_dir, "session-multi-revert")
    assert len(events) == 2
    assert events[0].payload.revert_count == 1
    assert events[1].payload.revert_count == 2
    assert events[0].envelope.sequence < events[1].envelope.sequence
    for evt in events:
        assert evt.payload.from_state == PipelineState.QUALITY.value
        assert evt.payload.to_state == PipelineState.CODE.value


# ---------------------------------------------------------------------------
# 7. Budget-exhausting (ESCALATED) hop -- no crash, emits per decision.
# ---------------------------------------------------------------------------


def test_budget_exhausting_hop_emits_escalated_event_without_raising(
    tmp_path, bridge_path, key_file
):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-escalate", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    drive_to(driver, PipelineState.SPEC_REVIEW)
    for _ in range(DEFAULT_REVERT_BUDGET - 1):
        driver.advance(FixedJudge(Verdict.FAIL))
        drive_to(driver, PipelineState.SPEC_REVIEW)

    # This must NOT raise ValueError from a bare PIPELINE_ORDER.index() on
    # ESCALATED -- the crash-safe classification (§2.4.1) is the point.
    result = driver.advance(FixedJudge(Verdict.FAIL))

    assert result.state is PipelineState.ESCALATED
    assert result.escalated is True
    assert driver.engine.revert_count == DEFAULT_REVERT_BUDGET

    events = _read_events(logs_dir, "session-escalate")
    escalated_events = [e for e in events if e.payload.escalated]
    assert len(escalated_events) == 1
    evt = escalated_events[0]
    assert evt.payload.to_state == PipelineState.ESCALATED.value
    assert evt.payload.revert_count == DEFAULT_REVERT_BUDGET
    assert evt.payload.from_state == PipelineState.SPEC_REVIEW.value


# ---------------------------------------------------------------------------
# 8. NEEDS_HUMAN hop -- no crash, no revert event.
# ---------------------------------------------------------------------------


def test_needs_human_hop_does_not_raise_and_emits_no_revert_event(
    tmp_path, bridge_path, key_file
):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-needs-human", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    result = driver.advance(FixedJudge(Verdict.NEEDS_HUMAN))

    assert result.state is PipelineState.HUMAN_QUESTION
    assert result.escalated is False

    events = _read_events(logs_dir, "session-needs-human")
    assert events == []


# ---------------------------------------------------------------------------
# 12. Optional bus / engine purity.
# ---------------------------------------------------------------------------


def test_driver_without_injected_bus_still_works(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    result = driver.advance(FixedJudge(Verdict.PASS))

    assert result.state is PipelineState.PLAN


def test_driver_without_bus_handles_revert_and_escalation_without_raising(
    bridge_path, key_file
):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    drive_to(driver, PipelineState.SPEC_REVIEW)
    for _ in range(DEFAULT_REVERT_BUDGET - 1):
        driver.advance(FixedJudge(Verdict.FAIL))
        drive_to(driver, PipelineState.SPEC_REVIEW)

    result = driver.advance(FixedJudge(Verdict.FAIL))
    assert result.state is PipelineState.ESCALATED
    assert result.escalated is True


def test_advance_on_clean_completion_still_works_as_thin_wrapper(
    bridge_path, key_file
):
    """Source compatibility: the pre-existing minimal-slice entry point is
    unchanged in behaviour."""

    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    result = driver.advance_on_clean_completion()

    assert result.state is PipelineState.PLAN


def test_engine_package_imports_no_bus_module():
    """Engine purity (plan Architect + §2.4): the engine core stays pure --
    no `bus` import, no filesystem/process boundary in `engine/__init__.py`.
    A static check, not a comment."""

    source = inspect.getsource(engine_pkg)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all("bus" not in alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not node.module or "bus" not in node.module
