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

**Extended for the review-page/staging UX**
(`.gleipnir/plans/tier3-approval-ux.md`, Assemble Steps 1-3, Stress-test
S1/S5-S8/S13). `staged_path_for`/`load_staged`/`render_review_page` are pure,
fully unit-testable (no sockets) per that plan's Trace section B -- these
new tests follow the SAME core-tested convention as the block above (no
live `http.server.HTTPServer` socket is spun up anywhere in this file); the
GET/POST `/approve/<hash>` thin-edge wiring is exercised through the exact
same pure functions the handler methods call (`load_staged` +
`render_review_page` for GET, `load_staged` + `capture_approval` for POST),
which is what the plan explicitly calls the testable seam.
"""

from __future__ import annotations

import hashlib
import html
import http.client
import http.server
import json
import threading
from pathlib import Path

import pytest

from gleipnir.approval.identity import IdentityUnresolved, RequestContext, ResolvedIdentity
from gleipnir.approval.server import (
    _read_target_bytes,
    build_request_context,
    capture_approval,
    compute_change_hash,
    load_staged,
    make_handler_class,
    render_review_page,
    staged_path_for,
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


# ---------------------------------------------------------------------------
# Tier-3 approval UX: staging, review page, POST-by-hash
# (`.gleipnir/plans/tier3-approval-ux.md`, Assemble Steps 1-3)
# ---------------------------------------------------------------------------


def _write_envelope(
    token_dir: Path,
    content: str,
    *,
    file_path: str = "target.txt",
    tool: str = "write",
    staged_at: int = 1_700_000_000,
    change_hash: str | None = None,
) -> str:
    """Test helper: write a `pending-<hash>.json` staged envelope to
    `token_dir` exactly the way the hook stages it (P1), and return the
    hash used for the filename. Defaults to the REAL sha256(content_utf8)
    hash unless a (deliberately wrong, for the malformed-hash tests)
    `change_hash` override is given."""

    the_hash = change_hash if change_hash is not None else compute_change_hash(
        content.encode("utf-8")
    )
    envelope = {
        "content": content,
        "filePath": file_path,
        "tool": tool,
        "staged_at": staged_at,
    }
    token_dir.mkdir(parents=True, exist_ok=True)
    staged_path_for(token_dir, the_hash).write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    return the_hash


class TestStagedPathFor:
    def test_staged_path_for_uses_the_full_hash_not_a_prefix(
        self, tmp_path: Path
    ) -> None:
        change_hash = "b" * 64
        path = staged_path_for(tmp_path, change_hash)
        assert path.name == f"pending-{'b' * 64}.json"
        assert path.parent == tmp_path

    def test_staged_path_for_is_distinct_from_token_path_for(
        self, tmp_path: Path
    ) -> None:
        change_hash = "c" * 64
        staged = staged_path_for(tmp_path, change_hash)
        minted = token_path_for(tmp_path, change_hash)
        assert staged != minted
        assert staged.name.startswith("pending-")
        assert minted.name.startswith("approval-")


class TestLoadStaged:
    def test_load_staged_present_returns_the_envelope_dict(
        self, tmp_path: Path
    ) -> None:
        change_hash = _write_envelope(tmp_path, "hello staged content")
        envelope = load_staged(tmp_path, change_hash)
        assert envelope == {
            "content": "hello staged content",
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1_700_000_000,
        }

    def test_load_staged_absent_returns_none(self, tmp_path: Path) -> None:
        assert load_staged(tmp_path, "d" * 64) is None

    def test_load_staged_malformed_json_returns_none(self, tmp_path: Path) -> None:
        change_hash = "e" * 64
        tmp_path.mkdir(parents=True, exist_ok=True)
        staged_path_for(tmp_path, change_hash).write_bytes(b"{not valid json")
        assert load_staged(tmp_path, change_hash) is None

    def test_load_staged_rejects_non_hex_hash_never_touches_the_filesystem_join(
        self, tmp_path: Path
    ) -> None:
        # E7: a malformed/path-traversal-shaped hash must 404 (None) without
        # ever building a path that escapes token_dir.
        assert load_staged(tmp_path, "../../etc/passwd") is None
        assert load_staged(tmp_path, "not-hex!!") is None
        assert load_staged(tmp_path, "a" * 63) is None  # too short
        assert load_staged(tmp_path, "a" * 65) is None  # too long

    def test_load_staged_reads_utf8_explicitly_not_locale_dependent(
        self, tmp_path: Path
    ) -> None:
        # Multibyte content must round-trip exactly -- the P2/S13 contract.
        content = "emoji \u2705\U0001F510\n multibyte \u03b1\u03b2\u03b3"
        change_hash = _write_envelope(tmp_path, content)
        envelope = load_staged(tmp_path, change_hash)
        assert envelope is not None
        assert envelope["content"] == content


class TestRenderReviewPage:
    def test_escapes_content_and_neutralizes_a_script_payload(self) -> None:
        envelope = {
            "content": "<script>alert(1)</script>",
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1,
        }
        body = render_review_page(envelope, None)
        assert isinstance(body, bytes)
        text = body.decode("utf-8")
        assert "<script>alert(1)</script>" not in text
        assert "&lt;script&gt;" in text

    def test_new_file_case_when_current_on_disk_is_none(self) -> None:
        envelope = {
            "content": "brand new content",
            "filePath": "new/target.txt",
            "tool": "write",
            "staged_at": 1,
        }
        text = render_review_page(envelope, None).decode("utf-8")
        assert "new file" in text.lower()
        assert "brand new content" in text

    def test_includes_a_unified_diff_when_base_bytes_differ(self) -> None:
        envelope = {
            "content": "line one\nline TWO changed\nline three\n",
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1,
        }
        current_on_disk = b"line one\nline two\nline three\n"
        text = render_review_page(envelope, current_on_disk).decode("utf-8")
        # A difflib.unified_diff block carries these markers.
        assert "@@" in text or "---" in text
        assert "+++" in text or "-line two" in text or "line TWO changed" in text

    def test_embeds_a_form_posting_to_approve_hash(self) -> None:
        content = "form target content"
        envelope = {
            "content": content,
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1,
        }
        expected_hash = compute_change_hash(content.encode("utf-8"))
        text = render_review_page(envelope, None).decode("utf-8")
        assert f'action="/approve/{expected_hash}"' in text
        assert 'method="POST"' in text

    def test_escapes_diff_lines_too_not_only_the_raw_content_block(self) -> None:
        envelope = {
            "content": "safe\n<img src=x onerror=alert(1)>\n",
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1,
        }
        current_on_disk = b"safe\nold line\n"
        text = render_review_page(envelope, current_on_disk).decode("utf-8")
        assert "<img src=x onerror=alert(1)>" not in text


class TestPostByHashCoreReuse:
    """The POST-by-hash core path reuses `capture_approval` UNCHANGED (P3):
    load the staged envelope by hash, then mint over its `content` bytes."""

    def test_staged_content_mints_a_token_bound_to_the_staged_bytes(
        self, tmp_path: Path
    ) -> None:
        content = "the exact staged Tier-3 change"
        change_hash = _write_envelope(tmp_path, content)
        envelope = load_staged(tmp_path, change_hash)
        assert envelope is not None

        token = capture_approval(
            remote_ip="100.64.0.1",
            headers={},
            pending_content=envelope["content"].encode("utf-8"),
            key=KEY,
            resolve=_fake_resolve_ok,
            minted_at=1_000_000,
            token_dir=tmp_path,
        )
        assert token.change_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert token.change_hash == change_hash

    def test_missing_staged_file_never_mints_anything(self, tmp_path: Path) -> None:
        assert load_staged(tmp_path, "f" * 64) is None
        # No mint call is even reachable without an envelope -- nothing to
        # assert on the mint side; confirm no token file exists either.
        assert list(tmp_path.glob("approval-*.json")) == []


class TestEndToEndWhatYouSeeIsWhatYouSign:
    """Stress-test S8: stage X -> GET renders X -> POST mints -> the minted
    token's change_hash == sha256(X_utf8). Proven end-to-end through the
    same pure functions the do_GET/do_POST thin edge calls."""

    def test_s8_stage_render_mint_round_trip(self, tmp_path: Path) -> None:
        X = "the WYSIWYS content\nwith <a tag> and a newline"

        # Stage (mirrors the hook's writeFileSync of the envelope).
        change_hash = _write_envelope(tmp_path, X)

        # GET renders X (escaped).
        envelope = load_staged(tmp_path, change_hash)
        assert envelope is not None
        rendered = render_review_page(envelope, None).decode("utf-8")
        assert html.escape(X, quote=True) in rendered

        # POST mints against the SAME staged bytes.
        token = capture_approval(
            remote_ip="100.64.0.1",
            headers={},
            pending_content=envelope["content"].encode("utf-8"),
            key=KEY,
            resolve=_fake_resolve_ok,
            minted_at=1_000_000,
            token_dir=tmp_path,
        )

        assert token.change_hash == hashlib.sha256(X.encode("utf-8")).hexdigest()
        assert token.change_hash == change_hash


class TestMissingStagedFile404Case:
    """P7/S7: GET and POST `/approve/<hash>` with no staged file must 404 and
    never mint -- proven at the `load_staged` seam both routes are built on."""

    def test_no_staged_file_for_hash_is_absent_never_a_crash(
        self, tmp_path: Path
    ) -> None:
        assert load_staged(tmp_path, "0" * 64) is None

    def test_stale_hash_after_content_changes_is_also_absent(
        self, tmp_path: Path
    ) -> None:
        _write_envelope(tmp_path, "version one")
        # A DIFFERENT hash (as if content changed) was never staged.
        other_hash = compute_change_hash(b"version two")
        assert load_staged(tmp_path, other_hash) is None


class TestCrossLanguageJSONRoundTripFidelity:
    """Stress-test S13: build the staged envelope file AS IF a real
    `JSON.stringify` from TS had written it -- i.e. write actual JSON text to
    disk matching the exact envelope shape the plan specifies (P1), not a
    Python dict passed in-memory -- and confirm the Python-side
    load+hash path produces the correct hash for multibyte/astral content.
    """

    X = "emoji \u2705\U0001F510\n multibyte \u03b1\u03b2\u03b3"

    def _expected_hash(self) -> str:
        return hashlib.sha256(self.X.encode("utf-8")).hexdigest()

    def test_ascii_escaped_json_stringify_form(self, tmp_path: Path) -> None:
        # Node's default JSON.stringify escapes non-ASCII to \uXXXX /
        # surrogate-pair \uXXXX\uXXXX for astral characters. `json.dumps`
        # with ensure_ascii=True (the default) reproduces that exact wire
        # form byte-for-byte.
        envelope = {
            "content": self.X,
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1_700_000_001,
        }
        raw_json_text = json.dumps(envelope, ensure_ascii=True)
        # Sanity: this really did escape the astral/multibyte chars, i.e.
        # this fixture is exercising the \uXXXX path, not silently
        # degrading to the raw-UTF-8 fixture below.
        assert "\\u" in raw_json_text
        assert self.X not in raw_json_text

        change_hash = self._expected_hash()
        tmp_path.mkdir(parents=True, exist_ok=True)
        staged_path_for(tmp_path, change_hash).write_bytes(
            raw_json_text.encode("utf-8")
        )

        envelope_loaded = load_staged(tmp_path, change_hash)
        assert envelope_loaded is not None
        assert envelope_loaded["content"] == self.X

        recomputed_hash = compute_change_hash(
            envelope_loaded["content"].encode("utf-8")
        )
        assert recomputed_hash == change_hash == self._expected_hash()

    def test_raw_utf8_json_stringify_form(self, tmp_path: Path) -> None:
        # The non-ASCII-escaping form (ensure_ascii=False) -- the raw UTF-8
        # bytes on the wire, matching a JSON.stringify replacement/serializer
        # that emits literal UTF-8 rather than \uXXXX escapes. Both forms
        # MUST decode to the identical string and hash identically.
        envelope = {
            "content": self.X,
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1_700_000_002,
        }
        raw_json_text = json.dumps(envelope, ensure_ascii=False)
        # `json.dumps` ALWAYS escapes JSON control characters (e.g. `\n` ->
        # `\\n`) regardless of `ensure_ascii`, so `self.X` as a whole is not
        # a literal substring here -- but with `ensure_ascii=False` the
        # non-ASCII multibyte/astral characters themselves are emitted as
        # literal UTF-8, not `\uXXXX` escapes. Assert that literal form
        # directly (the thing this fixture variant is actually exercising).
        assert "\u2705" in raw_json_text  # \u2705 == the emoji, literal
        assert "\U0001F510" in raw_json_text  # literal astral character
        assert "\u03b1\u03b2\u03b3" in raw_json_text  # literal multibyte
        assert "\\u" not in raw_json_text  # confirms no \uXXXX escaping

        change_hash = self._expected_hash()
        tmp_path.mkdir(parents=True, exist_ok=True)
        staged_path_for(tmp_path, change_hash).write_bytes(
            raw_json_text.encode("utf-8")
        )

        envelope_loaded = load_staged(tmp_path, change_hash)
        assert envelope_loaded is not None
        assert envelope_loaded["content"] == self.X

        recomputed_hash = compute_change_hash(
            envelope_loaded["content"].encode("utf-8")
        )
        assert recomputed_hash == change_hash == self._expected_hash()

    def test_both_json_stringify_forms_agree_with_each_other(
        self, tmp_path: Path
    ) -> None:
        ascii_dir = tmp_path / "ascii"
        raw_dir = tmp_path / "raw"
        change_hash = self._expected_hash()

        for d, ensure_ascii in ((ascii_dir, True), (raw_dir, False)):
            d.mkdir(parents=True, exist_ok=True)
            envelope = {
                "content": self.X,
                "filePath": "target.txt",
                "tool": "write",
                "staged_at": 1,
            }
            staged_path_for(d, change_hash).write_bytes(
                json.dumps(envelope, ensure_ascii=ensure_ascii).encode("utf-8")
            )

        ascii_envelope = load_staged(ascii_dir, change_hash)
        raw_envelope = load_staged(raw_dir, change_hash)
        assert ascii_envelope is not None and raw_envelope is not None
        assert ascii_envelope["content"] == raw_envelope["content"] == self.X


class TestLoadStagedNonDictJson:
    """`load_staged` must reject validly-parsed JSON that is not an object
    (e.g. a bare list/string) -- not every valid JSON document is a usable
    envelope."""

    def test_a_json_array_is_not_a_valid_envelope(self, tmp_path: Path) -> None:
        change_hash = "1" * 64
        tmp_path.mkdir(parents=True, exist_ok=True)
        staged_path_for(tmp_path, change_hash).write_bytes(
            json.dumps(["not", "an", "envelope"]).encode("utf-8")
        )
        assert load_staged(tmp_path, change_hash) is None

    def test_a_bare_json_string_is_not_a_valid_envelope(self, tmp_path: Path) -> None:
        change_hash = "2" * 64
        tmp_path.mkdir(parents=True, exist_ok=True)
        staged_path_for(tmp_path, change_hash).write_bytes(
            json.dumps("just a string").encode("utf-8")
        )
        assert load_staged(tmp_path, change_hash) is None


class TestRenderReviewPageNoTextualDifference:
    def test_identical_content_and_disk_bytes_reports_no_difference(self) -> None:
        content = "unchanged content\nsame on both sides\n"
        envelope = {
            "content": content,
            "filePath": "target.txt",
            "tool": "write",
            "staged_at": 1,
        }
        text = render_review_page(envelope, content.encode("utf-8")).decode("utf-8")
        assert "no textual difference" in text.lower()


class TestReadTargetBytes:
    """`_read_target_bytes` is the display-only diff-base reader (P5/E5) --
    NEVER hashed/minted. Directly unit-tested (pure, no sockets) per the
    same core-tested convention as `load_staged`/`render_review_page`."""

    def test_reads_an_existing_absolute_file_verbatim(self, tmp_path: Path) -> None:
        target = tmp_path / "on-disk.txt"
        target.write_bytes(b"the on-disk base bytes")
        assert _read_target_bytes(str(target)) == b"the on-disk base bytes"

    def test_missing_file_returns_none_not_a_crash(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist.txt"
        assert _read_target_bytes(str(missing)) is None

    def test_non_string_input_returns_none(self) -> None:
        assert _read_target_bytes(None) is None
        assert _read_target_bytes(42) is None

    def test_empty_string_returns_none(self) -> None:
        assert _read_target_bytes("") is None


class TestLiveHttpApproveRoutes:
    """One deliberate exception to the "core-tested, no live sockets"
    convention documented above (and in `server.py`'s own module
    docstring): this class exercises the ACTUAL `do_GET`/`do_POST`
    thin-edge dispatch (route parsing + status-code mapping) over a real
    loopback socket, confirming the wiring described in Trace section B
    (P6/P7/P3) truly dispatches to the pure functions unit-tested above --
    not merely that the pure functions behave correctly in isolation.
    Loopback-only (`127.0.0.1`), no external network reachability
    required."""

    def _start(self, token_dir: Path, resolve=_fake_resolve_ok):
        handler_class = make_handler_class(key=KEY, resolve=resolve, token_dir=token_dir)
        httpd = http.server.HTTPServer(("127.0.0.1", 0), handler_class)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return httpd, thread

    def _stop(self, httpd, thread) -> None:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    def test_get_approve_hash_renders_the_staged_content(self, tmp_path: Path) -> None:
        content = "live-http staged content"
        change_hash = _write_envelope(tmp_path, content)
        httpd, thread = self._start(tmp_path)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("GET", f"/approve/{change_hash}")
            resp = conn.getresponse()
            body = resp.read()
            assert resp.status == 200
            assert resp.getheader("Content-Type") == "text/html"
            assert html.escape(content, quote=True).encode("utf-8") in body
            conn.close()
        finally:
            self._stop(httpd, thread)

    def test_get_approve_hash_404s_for_missing_staged_file(self, tmp_path: Path) -> None:
        httpd, thread = self._start(tmp_path)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("GET", "/approve/" + "0" * 64)
            resp = conn.getresponse()
            resp.read()
            assert resp.status == 404
            conn.close()
        finally:
            self._stop(httpd, thread)

    def test_post_approve_hash_mints_a_token_from_the_staged_bytes(
        self, tmp_path: Path
    ) -> None:
        content = "live-http POST-by-hash content"
        change_hash = _write_envelope(tmp_path, content)
        httpd, thread = self._start(tmp_path)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("POST", f"/approve/{change_hash}")
            resp = conn.getresponse()
            body = resp.read()
            assert resp.status == 200
            payload = json.loads(body)
            assert payload["status"] == "approved"
            assert payload["change_hash"] == change_hash
            conn.close()
            assert token_path_for(tmp_path, change_hash).is_file()
        finally:
            self._stop(httpd, thread)

    def test_post_approve_hash_404s_and_never_mints_for_missing_staged_file(
        self, tmp_path: Path
    ) -> None:
        httpd, thread = self._start(tmp_path)
        try:
            missing_hash = "9" * 64
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("POST", f"/approve/{missing_hash}")
            resp = conn.getresponse()
            resp.read()
            assert resp.status == 404
            conn.close()
            assert list(tmp_path.glob("approval-*.json")) == []
        finally:
            self._stop(httpd, thread)

    def test_post_approve_hash_403s_on_unresolvable_identity_never_mints(
        self, tmp_path: Path
    ) -> None:
        content = "content that will be rejected"
        change_hash = _write_envelope(tmp_path, content)
        httpd, thread = self._start(tmp_path, resolve=_fake_resolve_unresolvable)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("POST", f"/approve/{change_hash}")
            resp = conn.getresponse()
            body = resp.read()
            assert resp.status == 403
            payload = json.loads(body)
            assert payload["status"] == "rejected"
            conn.close()
            assert list(tmp_path.glob("approval-*.json")) == []
        finally:
            self._stop(httpd, thread)

    def test_get_root_and_exact_approve_serve_instructions_unchanged(
        self, tmp_path: Path
    ) -> None:
        httpd, thread = self._start(tmp_path)
        try:
            for path in ("/", "/approve"):
                conn = http.client.HTTPConnection(
                    "127.0.0.1", httpd.server_address[1], timeout=5
                )
                conn.request("GET", path)
                resp = conn.getresponse()
                body = resp.read()
                assert resp.status == 200
                assert b"Gleipnir Tier-3 approval listener" in body
                conn.close()
        finally:
            self._stop(httpd, thread)

    def test_post_exact_approve_raw_body_path_still_works_unchanged(
        self, tmp_path: Path
    ) -> None:
        pending = b"raw body legacy path content"
        httpd, thread = self._start(tmp_path)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("POST", "/approve", body=pending)
            resp = conn.getresponse()
            body = resp.read()
            assert resp.status == 200
            payload = json.loads(body)
            assert payload["change_hash"] == hashlib.sha256(pending).hexdigest()
            conn.close()
        finally:
            self._stop(httpd, thread)

    def test_unknown_path_404s_for_both_get_and_post(self, tmp_path: Path) -> None:
        httpd, thread = self._start(tmp_path)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
            conn.request("GET", "/nope")
            resp = conn.getresponse()
            resp.read()
            assert resp.status == 404
            conn.close()

            conn2 = http.client.HTTPConnection(
                "127.0.0.1", httpd.server_address[1], timeout=5
            )
            conn2.request("POST", "/nope")
            resp2 = conn2.getresponse()
            resp2.read()
            assert resp2.status == 404
            conn2.close()
        finally:
            self._stop(httpd, thread)
