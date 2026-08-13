"""Tests: the G-5 driver emits G-4 `NeedsHumanRaisedEvent`s and
`GateReachedEvent`s on the human-gate hop and the clean-completion
terminal.

Plan: `.gleipnir/plans/g4-terminal-events.md`, Assemble step 2 / Stress-test
check D. Written RED-first, before `driver.py` emitted either kind.

Covers:
  (a) A NEEDS_HUMAN advance emits exactly one `NEEDS_HUMAN_RAISED` event
      with `from_state` = the raising stage, correct envelope
      (agent/turn/session/artifact_ref), and emits no revert event.
  (b) A full drive to a green-attestation gate emits exactly one
      `GATE_REACHED` with `pipeline_id`.
  (c) A refused gate emits nothing (and does not rewrite the bridge).
  (e) A driver with no bus still works and does not raise on either path.
  (f) write-bridge-still-runs / degrade-not-raise.

Engine purity (`test_engine_package_imports_no_bus_module`) is already
covered in `tests/test_driver_emits_revert.py`; not duplicated here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

from gleipnir.bus import Event, EventBus, EventKind, GateReachedEvent, NeedsHumanRaisedEvent
from gleipnir.engine import (
    Attestation,
    AttestationNotGreen,
    AttestationStatus,
    PipelineState,
    Verdict,
)
from gleipnir.engine.driver import Driver

VERIFIER_KEY = b"verifier-only-secret-key-not-on-agent-surface"
PIPELINE_ID = "pl-bus-driver-terminal-test-1"


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
    all-PASS judge (mirrors `tests/test_driver_emits_revert.py::drive_to`)."""

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
# (a) NEEDS_HUMAN hop emits exactly one NEEDS_HUMAN_RAISED, no revert event.
# ---------------------------------------------------------------------------


def test_needs_human_hop_emits_needs_human_raised_event(
    tmp_path, bridge_path, key_file
):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-needs-human-raised", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    result = driver.advance(
        FixedJudge(Verdict.NEEDS_HUMAN), agent="gleipnir-plan", originating_turn=2
    )

    assert result.state is PipelineState.HUMAN_QUESTION

    events = _read_events(logs_dir, "session-needs-human-raised")
    assert len(events) == 1
    evt = events[0]
    assert evt.kind is EventKind.NEEDS_HUMAN_RAISED
    assert isinstance(evt.payload, NeedsHumanRaisedEvent)
    assert evt.payload.from_state == PipelineState.BRAINSTORM.value
    assert evt.envelope.agent == "gleipnir-plan"
    assert evt.envelope.originating_turn == 2
    assert evt.envelope.session_id == "session-needs-human-raised"
    assert evt.envelope.artifact_ref == PIPELINE_ID
    # No revert event emitted for this hop -- it is not a revert.
    assert all(e.kind is not EventKind.REVERT_OCCURRED for e in events)


def test_needs_human_hop_from_a_later_stage_carries_that_stage(
    tmp_path, bridge_path, key_file
):
    """`from_state` is read by attribute from the driver's observed
    pre-step state, not hardcoded -- proven by raising from a stage other
    than BRAINSTORM."""

    logs_dir = tmp_path / "logs"
    bus = EventBus("session-needs-human-later", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    drive_to(driver, PipelineState.QUALITY)
    driver.advance(FixedJudge(Verdict.NEEDS_HUMAN))

    events = _read_events(logs_dir, "session-needs-human-later")
    needs_human_events = [e for e in events if e.kind is EventKind.NEEDS_HUMAN_RAISED]
    assert len(needs_human_events) == 1
    assert needs_human_events[0].payload.from_state == PipelineState.QUALITY.value


def test_multiple_needs_human_hops_each_emit_one_event(
    tmp_path, bridge_path, key_file
):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-needs-human-multi", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    driver.advance(FixedJudge(Verdict.NEEDS_HUMAN))
    driver.engine.answer_human_question("ok")
    driver.advance(FixedJudge(Verdict.NEEDS_HUMAN))

    events = _read_events(logs_dir, "session-needs-human-multi")
    needs_human_events = [e for e in events if e.kind is EventKind.NEEDS_HUMAN_RAISED]
    assert len(needs_human_events) == 2
    assert needs_human_events[0].envelope.sequence < needs_human_events[1].envelope.sequence


# ---------------------------------------------------------------------------
# (b)/(c) GATE_REACHED via the new attempt_gate wrapper.
# ---------------------------------------------------------------------------


def test_successful_gate_emits_gate_reached_event(tmp_path, bridge_path, key_file):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-gate-reached", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    drive_to(driver, PipelineState.GIT)
    attestation = Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.GREEN)
    result = driver.attempt_gate(attestation, agent="git-ops", originating_turn=9)

    assert result.state is PipelineState.GATE
    assert driver.state is PipelineState.GATE

    events = _read_events(logs_dir, "session-gate-reached")
    gate_events = [e for e in events if e.kind is EventKind.GATE_REACHED]
    assert len(gate_events) == 1
    evt = gate_events[0]
    assert isinstance(evt.payload, GateReachedEvent)
    assert evt.payload.pipeline_id == PIPELINE_ID
    assert evt.envelope.agent == "git-ops"
    assert evt.envelope.originating_turn == 9
    assert evt.envelope.artifact_ref == PIPELINE_ID


def test_refused_gate_raises_and_emits_nothing(tmp_path, bridge_path, key_file):
    logs_dir = tmp_path / "logs"
    bus = EventBus("session-gate-refused", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    drive_to(driver, PipelineState.GIT)
    bad_attestation = Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.RED)

    with pytest.raises(AttestationNotGreen):
        driver.attempt_gate(bad_attestation)

    assert driver.state is PipelineState.GIT

    events = _read_events(logs_dir, "session-gate-refused")
    assert events == []


def test_gate_attempted_before_git_raises_and_emits_nothing(
    tmp_path, bridge_path, key_file
):
    """A gate attempt from a non-GIT state is refused by the engine before
    any bridge write/emit could happen (mirrors `AttestationNotGreen`'s
    fail-closed posture)."""

    logs_dir = tmp_path / "logs"
    bus = EventBus("session-gate-too-early", logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()

    attestation = Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.GREEN)
    with pytest.raises(Exception):
        driver.attempt_gate(attestation)

    events = _read_events(logs_dir, "session-gate-too-early")
    assert events == []


# ---------------------------------------------------------------------------
# (e)/(f) No-bus driver + write-bridge-still-runs.
# ---------------------------------------------------------------------------


def test_driver_without_bus_handles_needs_human_without_raising(
    bridge_path, key_file
):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    result = driver.advance(FixedJudge(Verdict.NEEDS_HUMAN))

    assert result.state is PipelineState.HUMAN_QUESTION


def test_driver_without_bus_handles_gate_without_raising(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    drive_to(driver, PipelineState.GIT)
    attestation = Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.GREEN)
    result = driver.attempt_gate(attestation)

    assert result.state is PipelineState.GATE


def test_attempt_gate_writes_bridge_before_returning(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    drive_to(driver, PipelineState.GIT)
    attestation = Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.GREEN)
    driver.attempt_gate(attestation)

    assert bridge_path.exists()
    # A fresh resumed driver reads GATE off the bridge -- proves
    # write_bridge ran (not just the in-memory engine state).
    resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
    assert resumed.state is PipelineState.GATE


def test_refused_gate_does_not_rewrite_bridge(bridge_path, key_file):
    """Fail-closed key/bridge ordering (D4): a refused gate must not
    republish a bridge for a state the engine never actually reached."""

    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    drive_to(driver, PipelineState.GIT)
    driver.write_bridge()  # bridge now reflects GIT

    bad_attestation = Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.RED)
    with pytest.raises(AttestationNotGreen):
        driver.attempt_gate(bad_attestation)

    resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
    assert resumed.state is PipelineState.GIT
