"""Tests for the G-5 engine driver (`src/gleipnir/engine/driver.py`).

Spec context (plan `.gleipnir/plans/engine-wire-in.md`, Assemble step 2): the
driver owns an ``Engine`` instance, exposes read-current-state and
advance-on-completion, and persists the digest-protected bridge via
``StateMarker``. It is invoked by framework code (the post-tool hook); these
tests exercise its Python API directly, standing in for that caller.

Stress-test coverage (subset that is Python-testable at this layer):
  1. a fresh driver writes a bridge whose state is ``brainstorm``.
  2. advancing on a clean-completion verdict rewrites the bridge to ``plan``.
  3. the written payload carries a valid MAC.
  4. the driver refuses to write without the key (fail-closed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gleipnir.engine import PipelineState, StepResult
from gleipnir.engine.allow_table import allowed_agents_for
from gleipnir.engine.bridge import StateMarker, validate_state
from gleipnir.engine.driver import Driver
from gleipnir.verify.marker import KeyUnavailable

VERIFIER_KEY = b"verifier-only-secret-key-not-on-agent-surface"
PIPELINE_ID = "pl-driver-test-1"


@pytest.fixture
def key_file(tmp_path: Path) -> Path:
    kf = tmp_path / "key"
    kf.write_bytes(VERIFIER_KEY)
    return kf


@pytest.fixture
def bridge_path(tmp_path: Path) -> Path:
    return tmp_path / "var" / "run" / "pipeline-state.json"


def _read_marker(bridge_path: Path) -> StateMarker:
    return StateMarker.from_json(bridge_path.read_text())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_fresh_driver_writes_bridge_with_brainstorm_state(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    assert driver.state is PipelineState.BRAINSTORM

    driver.write_bridge()

    assert bridge_path.exists()
    marker = _read_marker(bridge_path)
    assert marker.pipeline_state == PipelineState.BRAINSTORM.value
    assert set(marker.allowed_agents) == allowed_agents_for(
        PipelineState.BRAINSTORM
    )
    assert validate_state(marker, VERIFIER_KEY) is True


def test_advance_on_clean_completion_rewrites_to_plan(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    result = driver.advance_on_clean_completion()

    assert isinstance(result, StepResult)
    assert result.state is PipelineState.PLAN
    assert driver.state is PipelineState.PLAN

    marker = _read_marker(bridge_path)
    assert marker.pipeline_state == PipelineState.PLAN.value
    assert set(marker.allowed_agents) == allowed_agents_for(PipelineState.PLAN)
    assert validate_state(marker, VERIFIER_KEY) is True


def test_advance_chain_walks_the_main_line(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()

    expected = [
        PipelineState.PLAN,
        PipelineState.SPEC_REVIEW,
        PipelineState.TEST,
        PipelineState.CODE,
        PipelineState.QUALITY,
        PipelineState.GIT,
    ]
    for expected_state in expected:
        result = driver.advance_on_clean_completion()
        assert result.state is expected_state
        marker = _read_marker(bridge_path)
        assert marker.pipeline_state == expected_state.value


def test_written_payload_carries_a_valid_mac(bridge_path, key_file):
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    driver.write_bridge()
    marker = _read_marker(bridge_path)
    assert marker.mac
    assert validate_state(marker, VERIFIER_KEY) is True
    # Wrong key must not validate -- the driver's MAC is genuinely keyed.
    assert validate_state(marker, b"some-other-key") is False


# ---------------------------------------------------------------------------
# Fail-closed: no key, no write
# ---------------------------------------------------------------------------


def test_driver_refuses_to_write_without_key(bridge_path, monkeypatch):
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=None)

    with pytest.raises(KeyUnavailable):
        driver.write_bridge()

    assert not bridge_path.exists()


def test_driver_refuses_to_advance_without_key(bridge_path, monkeypatch):
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=None)

    with pytest.raises(KeyUnavailable):
        driver.advance_on_clean_completion()

    # The engine must not have advanced past BRAINSTORM if the bridge write
    # (the only externally-observable side effect) failed. A driver that
    # advances state in memory but silently fails to publish it would be a
    # different, worse fail-open bug -- assert the whole operation refuses.
    assert driver.state is PipelineState.BRAINSTORM
    assert not bridge_path.exists()


def test_driver_picks_up_key_from_env(bridge_path, key_file, monkeypatch):
    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(key_file))
    driver = Driver(PIPELINE_ID, bridge_path, key_file=None)
    driver.write_bridge()
    assert bridge_path.exists()


# ---------------------------------------------------------------------------
# Resume-from-bridge: each opencode hook call is a fresh process, so the driver
# must rehydrate the engine at the bridge's CURRENT state rather than always
# starting at BRAINSTORM. This is the cross-process advance the post-tool hook
# relies on.
# ---------------------------------------------------------------------------


def test_resume_from_bridge_rehydrates_current_state(bridge_path, key_file):
    # Process 1: advance brainstorm -> plan -> spec_review, persist.
    d1 = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    d1.write_bridge()
    d1.advance_on_clean_completion()  # -> plan
    d1.advance_on_clean_completion()  # -> spec_review
    assert d1.state is PipelineState.SPEC_REVIEW

    # Process 2 (fresh Driver, as a new hook invocation would be): resume from
    # the bridge and confirm it is AT spec_review, not brainstorm.
    d2 = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
    assert d2.state is PipelineState.SPEC_REVIEW


def test_resume_then_advance_progresses_not_resets(bridge_path, key_file):
    d1 = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    d1.write_bridge()
    d1.advance_on_clean_completion()  # -> plan
    assert d1.state is PipelineState.PLAN

    # Fresh process resumes at plan and advances -> spec_review (NOT plan again).
    d2 = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
    result = d2.advance_on_clean_completion()
    assert result.state is PipelineState.SPEC_REVIEW
    marker = _read_marker(bridge_path)
    assert marker.pipeline_state == PipelineState.SPEC_REVIEW.value


def test_resume_rejects_tampered_bridge(bridge_path, key_file):
    d1 = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    d1.write_bridge()
    # Tamper: flip the state, keep the (now-invalid) mac.
    data = json.loads(bridge_path.read_text())
    data["pipeline_state"] = "git"
    bridge_path.write_text(json.dumps(data))

    # Resume must fail closed on an invalid MAC, not trust the forged state.
    with pytest.raises(Exception):
        Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)


def test_resume_without_key_fails_closed(bridge_path, key_file, monkeypatch):
    d1 = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
    d1.write_bridge()
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    with pytest.raises(KeyUnavailable):
        Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=None)


def test_resume_missing_bridge_fails_closed(bridge_path, key_file):
    # No bridge file written at all -> BridgeInvalid (never a fresh brainstorm).
    from gleipnir.engine.driver import BridgeInvalid

    with pytest.raises(BridgeInvalid):
        Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)


def test_resume_malformed_marker_fails_closed(bridge_path, key_file):
    from gleipnir.engine.driver import BridgeInvalid

    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text("{ not valid json")
    with pytest.raises(BridgeInvalid):
        Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)


def test_resume_unknown_state_fails_closed(bridge_path, key_file):
    """A genuinely-MAC'd bridge whose state is not a real PipelineState must
    still fail closed (defence in depth: mint one with a bogus state)."""
    from gleipnir.engine.driver import BridgeInvalid
    from gleipnir.engine.bridge import mint_state

    marker = mint_state("not_a_real_state", ["gleipnir-plan"], VERIFIER_KEY)
    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(marker.to_json())
    with pytest.raises(BridgeInvalid):
        Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
