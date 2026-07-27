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
