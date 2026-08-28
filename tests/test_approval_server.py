"""Unit tests for the approval listener's core orchestration
(`approval/server.py:capture_approval`), isolated from real HTTP sockets and
the real `tailscale` CLI via injected fakes (Stress-test T-17).

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Assemble Step 1/5,
Stress-test T-17. `capture_approval` is the fully-unit-testable
orchestration core (pure-core / thin-edge split, mirroring
`preflight.boundary` and `sandbox.runtime`); `ApprovalRequestHandler`/
`run_server` are the thin HTTP edge, exercised only indirectly here.

Test-first note (Axiom 1, restored retroactively): these tests are written
as the correctness arbiter for `src/gleipnir/approval/server.py`; any
defect they surface is fixed in the implementation, not in the test.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from gleipnir.approval.identity import IdentityUnresolved, RequestContext, ResolvedIdentity
from gleipnir.approval.server import (
    build_request_context,
    capture_approval,
    compute_change_hash,
    token_path_for,
)
from gleipnir.approval.token import ApprovalToken

KEY = b"server-test-key-not-on-agent-surface"


def _fake_resolve_ok(ctx: RequestContext) -> ResolvedIdentity:
    return ResolvedIdentity(identity="alice@example.com", provider="fake")


def _fake_resolve_unresolvable(ctx: RequestContext) -> ResolvedIdentity:
    raise IdentityUnresolved("no fake match")


class TestCaptureApprovalHappyPath:
    def test_capture_approval_writes_a_token_bound_to_the_shown_content(
        self, tmp_path: Path
    ) -> None:
        pending_content = b"the exact pending Tier-3 change"
        token = capture_approval(
            remote_ip="100.64.0.1",
            headers={},
            pending_content=pending_content,
            key=KEY,
            resolve=_fake_resolve_ok,
            minted_at=1_000_000,
            token_dir=tmp_path,
        )
        expected_hash = hashlib.sha256(pending_content).hexdigest()
        assert token.change_hash == expected_hash
        assert token.approver_identity == "alice@example.com"
        assert token.provider == "fake"

        written_path = token_path_for(tmp_path, expected_hash)
        assert written_path.is_file()
        restored = ApprovalToken.from_json(written_path.read_text())
        assert restored == token

    def test_capture_approval_creates_token_dir_if_absent(
        self, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "nested" / "var" / "tmp"
        assert not target_dir.exists()
        capture_approval(
            remote_ip="100.64.0.1",
            headers={},
            pending_content=b"content",
            key=KEY,
            resolve=_fake_resolve_ok,
            token_dir=target_dir,
        )
        assert target_dir.is_dir()

    def test_capture_approval_token_validates_under_the_gate(
        self, tmp_path: Path
    ) -> None:
        from gleipnir.approval.gate import GateVerdict, require_valid_token

        pending_content = b"a real pending diff"
        token = capture_approval(
            remote_ip="100.64.0.1",
            headers={},
            pending_content=pending_content,
            key=KEY,
            resolve=_fake_resolve_ok,
            token_dir=tmp_path,
        )
        token_path = token_path_for(tmp_path, token.change_hash)
        decision = require_valid_token(
            token.change_hash, token.approver_identity, token_path, KEY
        )
        assert decision.verdict is GateVerdict.ALLOW


class TestCaptureApprovalFailClosed:
    def test_unresolvable_identity_raises_and_mints_no_token(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(IdentityUnresolved):
            capture_approval(
                remote_ip="203.0.113.9",
                headers={},
                pending_content=b"some content",
                key=KEY,
                resolve=_fake_resolve_unresolvable,
                token_dir=tmp_path,
            )
        # No token file exists anywhere under token_dir -- nothing minted.
        assert list(tmp_path.glob("*.json")) == []


class TestHelpers:
    def test_compute_change_hash_is_sha256_hex(self) -> None:
        content = b"hello approval"
        assert compute_change_hash(content) == hashlib.sha256(content).hexdigest()

    def test_token_path_for_uses_16_char_hash_prefix(self, tmp_path: Path) -> None:
        change_hash = "a" * 64
        path = token_path_for(tmp_path, change_hash)
        assert path.name == f"approval-{'a' * 16}.json"
        assert path.parent == tmp_path

    def test_build_request_context_copies_headers_into_plain_dict(self) -> None:
        ctx = build_request_context("1.2.3.4", {"X-Foo": "bar"})
        assert ctx == RequestContext(remote_ip="1.2.3.4", headers={"X-Foo": "bar"})
        assert isinstance(ctx.headers, dict)
