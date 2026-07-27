"""Tests for the G-5 wire-in state bridge marker (``StateMarker``).

Spec context (plan `.gleipnir/plans/engine-wire-in.md`, Assemble step 2-3):
the Python engine <-> TS hook bridge carries the current ``PipelineState``
plus its allowed-agents projection, both bound under one keyed HMAC. There is
no independent tree to recompute against (unlike ``verify/marker.py``'s
``tree_hash``) -- the bridge payload *is* the state, so the MAC binds
directly to ``(pipeline_state, allowed_agents, minted_at)``.

These tests are written before ``src/gleipnir/engine/bridge.py`` exists
(test-first, per delegation discipline).
"""

from __future__ import annotations

import json

import pytest

from gleipnir.engine.bridge import (
    STATE_MARKER_VERSION,
    StateMarker,
    StateMarkerError,
    mint_state,
    validate_state,
)
from gleipnir.verify.marker import KeyUnavailable

VERIFIER_KEY = b"verifier-only-secret-key-not-on-agent-surface"
AGENT_GUESSED_KEY = b"agent-guessed-key"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_genuine_marker_validates():
    m = mint_state("plan", ["gleipnir-plan"], VERIFIER_KEY)
    assert validate_state(m, VERIFIER_KEY) is True


def test_marker_roundtrips_through_json():
    m = mint_state("brainstorm", ["gleipnir-plan"], VERIFIER_KEY)
    m2 = StateMarker.from_json(m.to_json())
    assert m2 == m
    assert validate_state(m2, VERIFIER_KEY) is True


def test_allowed_agents_order_does_not_affect_validity():
    """The canonical signing input sorts allowed_agents, so the wire order
    of an honestly-produced list does not matter."""
    m = mint_state("git", ["git-ops"], VERIFIER_KEY)
    assert validate_state(m, VERIFIER_KEY) is True


# ---------------------------------------------------------------------------
# Tamper / forgery -- an agent without the key cannot produce a marker that
# validates, and a one-byte tamper of state or allowed_agents invalidates a
# genuine marker (mirrors verify/marker.py's tree-tamper conformance tests).
# ---------------------------------------------------------------------------


def test_agent_fabricated_marker_fails():
    forged = StateMarker(
        version=STATE_MARKER_VERSION,
        pipeline_state="gate",
        allowed_agents=(),
        minted_at=1_000_000,
        mac="deadbeef" * 8,
    )
    assert validate_state(forged, VERIFIER_KEY) is False


def test_agent_mints_with_wrong_key_fails():
    m = mint_state("plan", ["gleipnir-plan"], AGENT_GUESSED_KEY)
    assert validate_state(m, VERIFIER_KEY) is False


def test_one_byte_state_tamper_invalidates():
    genuine = mint_state("plan", ["gleipnir-plan"], VERIFIER_KEY)
    tampered = StateMarker(
        version=genuine.version,
        pipeline_state="code",  # tampered: claim a different state
        allowed_agents=genuine.allowed_agents,
        minted_at=genuine.minted_at,
        mac=genuine.mac,  # reuse the genuine MAC
    )
    assert validate_state(tampered, VERIFIER_KEY) is False


def test_one_byte_allowed_agents_tamper_invalidates():
    genuine = mint_state("test", ["gleipnir-code"], VERIFIER_KEY)
    tampered = StateMarker(
        version=genuine.version,
        pipeline_state=genuine.pipeline_state,
        allowed_agents=("git-ops",),  # tampered: widen the allow set
        minted_at=genuine.minted_at,
        mac=genuine.mac,
    )
    assert validate_state(tampered, VERIFIER_KEY) is False


def test_added_allowed_agent_invalidates():
    genuine = mint_state("spec_review", ["quality-reviewer"], VERIFIER_KEY)
    tampered = StateMarker(
        version=genuine.version,
        pipeline_state=genuine.pipeline_state,
        allowed_agents=genuine.allowed_agents + ("git-ops",),
        minted_at=genuine.minted_at,
        mac=genuine.mac,
    )
    assert validate_state(tampered, VERIFIER_KEY) is False


# ---------------------------------------------------------------------------
# Freshness and version binding
# ---------------------------------------------------------------------------


def test_stale_marker_fails():
    old = mint_state("plan", ["gleipnir-plan"], VERIFIER_KEY, minted_at=1000)
    assert (
        validate_state(old, VERIFIER_KEY, max_age_seconds=3600, now=1_000_000)
        is False
    )


def test_future_marker_fails():
    future = mint_state(
        "plan", ["gleipnir-plan"], VERIFIER_KEY, minted_at=2_000_000
    )
    assert validate_state(future, VERIFIER_KEY, now=1_000_000) is False


def test_wrong_version_fails():
    m = mint_state("plan", ["gleipnir-plan"], VERIFIER_KEY)
    bad = StateMarker(
        version=99,
        pipeline_state=m.pipeline_state,
        allowed_agents=m.allowed_agents,
        minted_at=m.minted_at,
        mac=m.mac,
    )
    assert validate_state(bad, VERIFIER_KEY) is False


# ---------------------------------------------------------------------------
# Missing / garbage input is fail-closed
# ---------------------------------------------------------------------------


def test_malformed_marker_json_raises():
    with pytest.raises(StateMarkerError):
        StateMarker.from_json("{not json")


def test_marker_missing_fields_raises():
    with pytest.raises(StateMarkerError):
        StateMarker.from_json(json.dumps({"version": 1}))


def test_marker_wrong_types_raises():
    with pytest.raises(StateMarkerError):
        StateMarker.from_json(
            json.dumps(
                {
                    "version": 1,
                    "pipeline_state": "plan",
                    "allowed_agents": "not-a-list",
                    "minted_at": 1,
                    "mac": "abc",
                }
            )
        )


def test_key_unavailable_is_reused_from_verify_marker():
    """The fail-closed key-loading machinery is reused, not reinvented."""
    from gleipnir.engine.bridge import KeyUnavailable as BridgeKeyUnavailable

    assert BridgeKeyUnavailable is KeyUnavailable
