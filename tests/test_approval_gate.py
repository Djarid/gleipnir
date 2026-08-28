"""Unit + end-to-end tests for the Tier-3 write-gate (`approval/gate.py`)
and its CLI entry point (`approval/__main__.py`,
`python -m gleipnir.approval.gate --check <path> --content-file <path>
--token <file>`).

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Assemble Step 1/4,
Stress-test T-8..T-11, T-22. Mirrors `verify/__main__.py:_cmd_check`'s
REFUSE-on-any-doubt shape and `tests/test_verify_cli.py`'s CLI-testing
convention (drive through `main([...])`, not a subprocess spawn).

**The mint-vs-check content-hash fix (Decisions 19 + 20).** The CLI now
takes a required `--content-file` argument and hashes THAT (the exact
proposed resulting content) into the `change_hash` it checks -- never a
fresh read of `--check`'s live disk bytes, which would always be the
pre-edit/base content (`tool.execute.before` fires before the write
lands). Every CLI test below passes `--content-file` pointing at a temp
file holding the SAME content that was minted against, so the existing
pass/fail assertions keep working under the new contract. T-22
(`TestContentDivergence`) is the new regression test proving the CLI binds
to the handed-in content, not the `--check` target's disk bytes.

Test-first note (Axiom 1, restored retroactively): these tests are written
as the correctness arbiter for `src/gleipnir/approval/gate.py` and
`approval/__main__.py`; any defect they surface is fixed in the
implementation, not in the test.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from gleipnir.approval.__main__ import main as cli_main
from gleipnir.approval.gate import GateDecision, GateVerdict, require_valid_token
from gleipnir.approval.token import APPROVAL_MAX_AGE_SECONDS, mint_approval

KEY = b"gate-test-key-not-on-agent-surface"


def _write_token(path: Path, token) -> None:
    path.write_text(token.to_json())


# ---------------------------------------------------------------------------
# Fail-closed gate (T-8, T-9)
# ---------------------------------------------------------------------------


class TestFailClosedGate:
    def test_missing_token_file_refuses(self, tmp_path: Path) -> None:
        decision = require_valid_token(
            "h" * 64, "alice", tmp_path / "absent.json", KEY
        )
        assert decision.verdict is GateVerdict.REFUSE
        assert decision.reasons

    def test_malformed_token_file_refuses(self, tmp_path: Path) -> None:
        token_path = tmp_path / "token.json"
        token_path.write_text("{ not valid json")
        decision = require_valid_token("h" * 64, "alice", token_path, KEY)
        assert decision.verdict is GateVerdict.REFUSE

    def test_stale_token_refuses(self, tmp_path: Path) -> None:
        now = 1_000_000
        token = mint_approval("h" * 64, "alice", "tailscale", KEY, minted_at=now - 181)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        decision = require_valid_token(
            "h" * 64, "alice", token_path, KEY, max_age_seconds=180, now=now
        )
        assert decision.verdict is GateVerdict.REFUSE

    def test_content_mismatch_refuses(self, tmp_path: Path) -> None:
        token = mint_approval("h1" * 32, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        decision = require_valid_token("h2" * 32, "alice", token_path, KEY)
        assert decision.verdict is GateVerdict.REFUSE

    def test_identity_mismatch_refuses(self, tmp_path: Path) -> None:
        token = mint_approval("h" * 64, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        decision = require_valid_token("h" * 64, "bob", token_path, KEY)
        assert decision.verdict is GateVerdict.REFUSE

    def test_valid_fresh_token_allows(self, tmp_path: Path) -> None:
        token = mint_approval("h" * 64, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        decision = require_valid_token("h" * 64, "alice", token_path, KEY)
        assert decision.verdict is GateVerdict.ALLOW
        assert decision.reasons == ()

    def test_gate_decision_is_frozen(self) -> None:
        import dataclasses

        assert dataclasses.fields(GateDecision)
        decision = GateDecision(GateVerdict.ALLOW)
        with pytest.raises(dataclasses.FrozenInstanceError):
            decision.verdict = GateVerdict.REFUSE  # type: ignore[misc]


# ---------------------------------------------------------------------------
# End-to-end: mint -> gate -> refuse/accept (T-10, T-11)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_end_to_end_refuse_without_token(self, tmp_path: Path) -> None:
        decision = require_valid_token(
            "h" * 64, "alice", tmp_path / "never-minted.json", KEY
        )
        assert decision.verdict is GateVerdict.REFUSE

    def test_end_to_end_accept_with_valid_token(self, tmp_path: Path) -> None:
        change_hash = hashlib.sha256(b"pending tier-3 content").hexdigest()
        token = mint_approval(change_hash, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        decision = require_valid_token(change_hash, "alice", token_path, KEY)
        assert decision.verdict is GateVerdict.ALLOW

    def test_end_to_end_each_binding_failure_is_refused(self, tmp_path: Path) -> None:
        now = 1_000_000
        change_hash = hashlib.sha256(b"pending tier-3 content").hexdigest()

        stale = mint_approval(
            change_hash, "alice", "tailscale", KEY, minted_at=now - 181
        )
        stale_path = tmp_path / "stale.json"
        _write_token(stale_path, stale)
        assert (
            require_valid_token(
                change_hash, "alice", stale_path, KEY, now=now
            ).verdict
            is GateVerdict.REFUSE
        )

        fresh = mint_approval(change_hash, "alice", "tailscale", KEY, minted_at=now)
        content_mismatch_path = tmp_path / "content_mismatch.json"
        _write_token(content_mismatch_path, fresh)
        other_hash = hashlib.sha256(b"different content").hexdigest()
        assert (
            require_valid_token(
                other_hash, "alice", content_mismatch_path, KEY, now=now
            ).verdict
            is GateVerdict.REFUSE
        )

        identity_mismatch_path = tmp_path / "identity_mismatch.json"
        _write_token(identity_mismatch_path, fresh)
        assert (
            require_valid_token(
                change_hash, "mallory", identity_mismatch_path, KEY, now=now
            ).verdict
            is GateVerdict.REFUSE
        )


# ---------------------------------------------------------------------------
# CLI end-to-end: `python -m gleipnir.approval.gate --check <path>
# --content-file <path> --token <file>`, exit 0 = ALLOW, non-zero = REFUSE
# (Decision 14/19 exact contract). Every test hands `--content-file` a temp
# file containing the SAME content that was minted against -- these tests
# exercise the fail-closed / pass/fail machinery, not the content-divergence
# defect itself (that is TestContentDivergence / T-22 below).
# ---------------------------------------------------------------------------


class TestCLI:
    def _key_file(self, tmp_path: Path) -> Path:
        kf = tmp_path / "key"
        kf.write_bytes(KEY)
        return kf

    def _target_file(self, tmp_path: Path, content: bytes = b"pending write") -> Path:
        target = tmp_path / "target.txt"
        target.write_bytes(content)
        return target

    def _content_file(self, tmp_path: Path, content: bytes, name: str = "content-file") -> Path:
        """The `--content-file` a caller (the `tier3-gate.ts` hook) hands the
        CLI: the exact proposed RESULTING content for this write, which is
        what the CLI now hashes into `change_hash` (Decision 19) -- distinct
        from `--check`'s target file, which is only the file identifier."""
        cf = tmp_path / name
        cf.write_bytes(content)
        return cf

    def test_cli_allows_with_valid_fresh_token(self, tmp_path: Path) -> None:
        target = self._target_file(tmp_path)
        content = b"the exact resulting content this write will produce"
        content_file = self._content_file(tmp_path, content)
        change_hash = hashlib.sha256(content).hexdigest()
        token = mint_approval(change_hash, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(token_path),
            ]
        )
        assert rc == 0

    def test_cli_refuses_missing_target_file(self, tmp_path: Path) -> None:
        content_file = self._content_file(tmp_path, b"anything")
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(tmp_path / "no-such-file.txt"),
                "--content-file",
                str(content_file),
                "--token",
                str(tmp_path / "token.json"),
            ]
        )
        assert rc == 1

    def test_cli_refuses_missing_content_file(self, tmp_path: Path) -> None:
        target = self._target_file(tmp_path)
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(target),
                "--content-file",
                str(tmp_path / "no-such-content-file"),
                "--token",
                str(tmp_path / "token.json"),
            ]
        )
        assert rc == 1

    def test_cli_refuses_missing_token_file(self, tmp_path: Path) -> None:
        target = self._target_file(tmp_path)
        content_file = self._content_file(tmp_path, b"pending write")
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(tmp_path / "no-such-token.json"),
            ]
        )
        assert rc == 1

    def test_cli_refuses_malformed_token(self, tmp_path: Path) -> None:
        target = self._target_file(tmp_path)
        content_file = self._content_file(tmp_path, b"pending write")
        token_path = tmp_path / "token.json"
        token_path.write_text("{ garbage")
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(token_path),
            ]
        )
        assert rc == 1

    def test_cli_refuses_content_mismatched_token(self, tmp_path: Path) -> None:
        target = self._target_file(tmp_path, content=b"version A")
        content_file = self._content_file(tmp_path, b"version A")
        wrong_hash = hashlib.sha256(b"version B").hexdigest()
        token = mint_approval(wrong_hash, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(token_path),
            ]
        )
        assert rc == 1

    def test_cli_exits_3_on_key_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
        target = self._target_file(tmp_path)
        content_file = self._content_file(tmp_path, b"pending write")
        rc = cli_main(
            [
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(tmp_path / "token.json"),
            ]
        )
        assert rc == 3

    def test_cli_max_age_override_lets_a_181s_old_token_still_pass_at_wider_window(
        self, tmp_path: Path
    ) -> None:
        target = self._target_file(tmp_path)
        content = b"pending write"
        content_file = self._content_file(tmp_path, content)
        change_hash = hashlib.sha256(content).hexdigest()
        import time

        now = int(time.time())
        token = mint_approval(
            change_hash, "alice", "tailscale", KEY, minted_at=now - 181
        )
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)
        # Default 180s window would refuse; override to a wider window.
        rc = cli_main(
            [
                "--key-file",
                str(self._key_file(tmp_path)),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(token_path),
                "--max-age",
                "300",
            ]
        )
        assert rc == 0

    def test_cli_default_max_age_is_the_180s_constant(self) -> None:
        from gleipnir.approval.__main__ import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["--check", "x", "--content-file", "y", "--token", "z"]
        )
        assert args.max_age == APPROVAL_MAX_AGE_SECONDS == 180

    def test_cli_content_file_is_required(self) -> None:
        from gleipnir.approval.__main__ import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--check", "x", "--token", "y"])


# ---------------------------------------------------------------------------
# T-22: mint-vs-check content-divergence -- the quality-review-defect
# regression test. Proves the CLI binds the change_hash to the handed-in
# `--content-file` bytes, NOT a fresh read of `--check`'s live disk bytes.
# The `--check` target file's on-disk content deliberately DIFFERS from the
# approved content `X`, reproducing the real timing bug: tool.execute.before
# fires BEFORE the write lands, so the target's disk bytes are always the
# pre-edit/base content at check-time, never the approved-new content.
# ---------------------------------------------------------------------------


class TestContentDivergence:
    def test_cli_allows_when_content_file_matches_approved_content_despite_target_disk_divergence(
        self, tmp_path: Path
    ) -> None:
        approved_content = b"approved NEW content"
        base_content = b"pre-edit BASE content -- genuinely different bytes"
        assert approved_content != base_content

        # The --check target's LIVE DISK bytes are the pre-edit base -- never
        # mutated to the approved content, exactly as tool.execute.before
        # sees it (it fires strictly before the write lands).
        target = tmp_path / "target.txt"
        target.write_bytes(base_content)

        # Mint a token over the APPROVED content X (server.py's
        # compute_change_hash definition: sha256 of the posted/approved body).
        change_hash = hashlib.sha256(approved_content).hexdigest()
        token = mint_approval(change_hash, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)

        content_file = tmp_path / "content-file"
        content_file.write_bytes(approved_content)

        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)

        rc = cli_main(
            [
                "--key-file",
                str(key_file),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(token_path),
            ]
        )
        # ALLOW: the gate bound the change_hash to --content-file's bytes
        # (the approved content X), not --check's diverging disk bytes B.
        assert rc == 0

    def test_cli_refuses_when_content_file_diverges_by_one_byte_from_approved_content(
        self, tmp_path: Path
    ) -> None:
        approved_content = b"approved NEW content"
        base_content = b"pre-edit BASE content -- genuinely different bytes"
        assert approved_content != base_content

        target = tmp_path / "target.txt"
        target.write_bytes(base_content)

        change_hash = hashlib.sha256(approved_content).hexdigest()
        token = mint_approval(change_hash, "alice", "tailscale", KEY)
        token_path = tmp_path / "token.json"
        _write_token(token_path, token)

        # One byte changed relative to the approved content X.
        diverged_content = b"Approved NEW content"  # 'a' -> 'A'
        assert diverged_content != approved_content
        assert len(diverged_content) == len(approved_content)
        content_file = tmp_path / "content-file"
        content_file.write_bytes(diverged_content)

        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)

        rc = cli_main(
            [
                "--key-file",
                str(key_file),
                "--check",
                str(target),
                "--content-file",
                str(content_file),
                "--token",
                str(token_path),
            ]
        )
        # REFUSE: a one-byte divergence in the handed-in resulting content
        # invalidates the token -- proving the gate is genuinely
        # content-bound to --content-file, not silently allowing everything
        # (the bait-and-switch hole) or silently binding to --check's base.
        assert rc == 1
