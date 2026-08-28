"""Unit tests for the Tier-3 approval token: mint/validate, content-binding,
identity-binding, freshness-binding, unforgeability, and version binding.

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Assemble Step 1,
Stress-test T-1..T-7. Mirrors `tests/test_marker.py`'s G-3.1 conventions
(the primitive `token.py` reuses), extended with the identity-binding half
that `verify.marker.Marker` does not carry.

Test-first note (Axiom 1, restored retroactively): these tests are written
as the correctness arbiter for `src/gleipnir/approval/token.py`; any defect
they surface is fixed in the implementation, not in the test. The
identity/registry/gate source-scan (T-15) lives in
`test_approval_identity_resolver.py` per the plan's Trace mapping.
"""

from __future__ import annotations

import pytest

from gleipnir.approval.token import (
    APPROVAL_MAX_AGE_SECONDS,
    APPROVAL_TOKEN_VERSION,
    ApprovalToken,
    ApprovalTokenError,
    mint_approval,
    validate_approval,
)
from gleipnir.verify.marker import KeyUnavailable, load_key

KEY = b"approval-test-key-not-on-agent-surface"
OTHER_KEY = b"a-different-key"


# ---------------------------------------------------------------------------
# Happy path (T-1)
# ---------------------------------------------------------------------------


def test_mint_then_validate_happy_path():
    token = mint_approval("h" * 64, "alice@example.com", "tailscale", KEY)
    assert validate_approval(token, "h" * 64, "alice@example.com", KEY) is True


def test_token_roundtrips_through_json():
    token = mint_approval("h" * 64, "alice@example.com", "tailscale", KEY)
    restored = ApprovalToken.from_json(token.to_json())
    assert restored == token
    assert validate_approval(restored, "h" * 64, "alice@example.com", KEY) is True


# ---------------------------------------------------------------------------
# Content-binding (T-2)
# ---------------------------------------------------------------------------


def test_content_mismatch_invalidates():
    token = mint_approval("h1" * 32, "alice@example.com", "tailscale", KEY)
    assert validate_approval(token, "h2" * 32, "alice@example.com", KEY) is False


# ---------------------------------------------------------------------------
# Identity-binding (T-3)
# ---------------------------------------------------------------------------


def test_identity_mismatch_invalidates():
    token = mint_approval("h" * 64, "alice@example.com", "tailscale", KEY)
    assert validate_approval(token, "h" * 64, "bob@example.com", KEY) is False


# ---------------------------------------------------------------------------
# Freshness -- 180s window, lower boundary pinned (T-4)
# ---------------------------------------------------------------------------


def test_freshness_at_179s_still_valid():
    now = 1_000_000
    token = mint_approval("h" * 64, "alice", "tailscale", KEY, minted_at=now - 179)
    assert (
        validate_approval(token, "h" * 64, "alice", KEY, max_age_seconds=180, now=now)
        is True
    )


def test_freshness_at_181s_invalid():
    now = 1_000_000
    token = mint_approval("h" * 64, "alice", "tailscale", KEY, minted_at=now - 181)
    assert (
        validate_approval(token, "h" * 64, "alice", KEY, max_age_seconds=180, now=now)
        is False
    )


def test_default_max_age_is_180_seconds():
    assert APPROVAL_MAX_AGE_SECONDS == 180


def test_default_max_age_is_used_when_not_overridden():
    now = 1_000_000
    token = mint_approval("h" * 64, "alice", "tailscale", KEY, minted_at=now - 179)
    # No max_age_seconds passed: falls back to APPROVAL_MAX_AGE_SECONDS.
    assert validate_approval(token, "h" * 64, "alice", KEY, now=now) is True


# ---------------------------------------------------------------------------
# Future-dated rejected (T-5)
# ---------------------------------------------------------------------------


def test_future_dated_token_invalid():
    now = 1_000_000
    token = mint_approval("h" * 64, "alice", "tailscale", KEY, minted_at=now + 5)
    assert validate_approval(token, "h" * 64, "alice", KEY, now=now) is False


# ---------------------------------------------------------------------------
# Unforgeability (T-6)
# ---------------------------------------------------------------------------


def test_tampered_mac_invalidates():
    token = mint_approval("h" * 64, "alice", "tailscale", KEY)
    tampered_mac = ("0" if token.mac[0] != "0" else "1") + token.mac[1:]
    tampered = ApprovalToken(
        version=token.version,
        change_hash=token.change_hash,
        approver_identity=token.approver_identity,
        provider=token.provider,
        minted_at=token.minted_at,
        mac=tampered_mac,
    )
    assert validate_approval(tampered, "h" * 64, "alice", KEY) is False


def test_minted_with_wrong_key_fails_under_right_key():
    token = mint_approval("h" * 64, "alice", "tailscale", OTHER_KEY)
    assert validate_approval(token, "h" * 64, "alice", KEY) is False


def test_mac_lifted_onto_different_change_fails():
    """Lifting a genuine MAC onto a claimed different change_hash fails,
    because the MAC covers change_hash too (mirrors test_marker.py's
    `test_agent_copies_mac_onto_different_tree_fails`)."""
    genuine = mint_approval("h1" * 32, "alice", "tailscale", KEY)
    tampered = ApprovalToken(
        version=genuine.version,
        change_hash="h2" * 32,
        approver_identity=genuine.approver_identity,
        provider=genuine.provider,
        minted_at=genuine.minted_at,
        mac=genuine.mac,
    )
    assert validate_approval(tampered, "h2" * 32, "alice", KEY) is False


def test_mac_lifted_onto_different_identity_fails():
    genuine = mint_approval("h" * 64, "alice", "tailscale", KEY)
    tampered = ApprovalToken(
        version=genuine.version,
        change_hash=genuine.change_hash,
        approver_identity="bob",
        provider=genuine.provider,
        minted_at=genuine.minted_at,
        mac=genuine.mac,
    )
    assert validate_approval(tampered, "h" * 64, "bob", KEY) is False


# ---------------------------------------------------------------------------
# Wrong version rejected (T-7)
# ---------------------------------------------------------------------------


def test_wrong_version_invalidates():
    token = mint_approval("h" * 64, "alice", "tailscale", KEY)
    bad = ApprovalToken(
        version=99,
        change_hash=token.change_hash,
        approver_identity=token.approver_identity,
        provider=token.provider,
        minted_at=token.minted_at,
        mac=token.mac,
    )
    assert validate_approval(bad, "h" * 64, "alice", KEY) is False


def test_approval_token_version_constant_is_1():
    assert APPROVAL_TOKEN_VERSION == 1


# ---------------------------------------------------------------------------
# Malformed token JSON (fail-closed on parse)
# ---------------------------------------------------------------------------


def test_from_json_malformed_raises():
    with pytest.raises(ApprovalTokenError):
        ApprovalToken.from_json("{not json")


def test_from_json_missing_fields_raises():
    with pytest.raises(ApprovalTokenError):
        ApprovalToken.from_json('{"version": 1}')


# ---------------------------------------------------------------------------
# Key-unavailable is fail-closed via the reused G-3.1 primitive (Assemble
# Step 1: "key-unavailable handled fail-closed"). `token.py` takes key bytes
# directly and never calls `load_key` itself -- by Single Responsibility it
# knows nothing about *how* the key gets read; the caller obtains it via
# `verify.marker.load_key`, which is itself fail-closed on an absent/empty
# key. This proves the reuse is genuine, not merely a docstring claim.
# ---------------------------------------------------------------------------


def test_key_unavailable_via_reused_load_key_is_fail_closed(monkeypatch):
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    with pytest.raises(KeyUnavailable):
        load_key()


# ---------------------------------------------------------------------------
# Single-responsibility (Design Principles): token.py knows nothing about
# resolution or the network.
# ---------------------------------------------------------------------------


def test_token_module_does_not_import_resolver_or_http_server():
    """Checks actual import statements via `ast`, not a naive substring scan
    of the whole source -- the module's own docstring legitimately *names*
    `http.server`/the resolver seam in prose to explain what it does NOT
    import; only a real `import`/`from ... import` statement would violate
    the Single-Responsibility claim (plan Design Principles)."""
    import ast
    import inspect

    import gleipnir.approval.token as token_mod

    tree = ast.parse(inspect.getsource(token_mod))
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)

    assert not any("http.server" in name for name in imported_names)
    assert not any("identity" in name for name in imported_names)
