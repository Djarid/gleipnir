"""Tests for `src/gleipnir/approval/mcp_server.py` (Gleipnir Tier-3 approval
MCP wrapper, `gleipnir-approval`).

Plan: `.gleipnir/plans/tier3-mcp-approval-launcher.md`, Assemble Step 1,
Execution Workflow ("test" stage: T-1..T-5, T-8, T-9, and the T-11
reverse-import scan). Test-first (Axiom 1): written before
`mcp_server.py`'s implementation.

Runs under the **broker** sandbox profile (imports `mcp` transitively via
`mcp_server`, like `tests/test_broker_*_mcp_server.py`) -- see
`tests/conftest.py` `collect_ignore` (this module is added there so the lean
`python` self-host profile, which has no `mcp` SDK installed, does not abort
collection on this file's top-level import).

T-6 (byte-identity of the two `server.py` docstring-only edits), T-7 (no
literal secret in `opencode.jsonc`), and T-10 (per-agent deny-list negative
check) are NOT pytest tests here -- they are Tier-3/enforcement-path
negative-check attestations produced by `quality-reviewer` at the `quality`
stage (`stage-role-map.md` "Hardened path"), over files this delegation does
not touch (`opencode.jsonc`, `.gleipnir/agents/*.md`) or verifies via `git
diff` (not available to this bounded role). See the plan's Execution
Workflow section for those.
"""

from __future__ import annotations

import ast
import json
import logging
import threading
import time
from pathlib import Path

import pytest

from gleipnir.approval import mcp_server
from gleipnir.approval.identity import registry as identity_registry
from gleipnir.approval.server import compute_change_hash, staged_path_for

MCP_SERVER_PATH = Path(mcp_server.__file__)

# The closed import allow-list from `.server` (plan Trace / Decision 13):
# mcp_server.py may import ONLY these symbols from the core.
_ALLOWED_SERVER_IMPORTS = {
    "run_server",
    "register_default_resolvers",
    "compute_change_hash",
    "staged_path_for",
    "default_token_dir",
}

# The exact minting/key symbols mcp_server.py must NEVER reference by name
# (Decision 3/13, T-11's "wraps, never mints" reverse-import scan).
_FORBIDDEN_MINT_KEY_SYMBOLS = {"capture_approval", "mint_approval", "load_key"}


def _parse(py_file: Path) -> ast.Module:
    return ast.parse(py_file.read_text(encoding="utf-8"))


def _top_level_import_roots(py_file: Path) -> set[str]:
    """Third-party/absolute top-level import roots (mirrors
    `tests/test_broker_stdlib_only.py`'s helper of the same name -- kept as
    a local, self-contained copy per that file's own per-file-helper
    convention)."""
    roots: set[str] = set()
    for node in ast.walk(_parse(py_file)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import -- intra-package, not third-party
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _dot_server_import_names(py_file: Path) -> set[str]:
    """Names imported via `from .server import ...` (the ONE relative
    import the closed allow-list governs)."""
    names: set[str] = set()
    for node in ast.walk(_parse(py_file)):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module == "server"
        ):
            for alias in node.names:
                names.add(alias.name)
    return names


def _all_identifiers(py_file: Path) -> set[str]:
    """EVERY identifier the source references, by name: import
    names/aliases, `ast.Name` loads/stores, and `ast.Attribute` attribute
    names (so `foo.load_key` is caught the same as a bare `load_key`).

    This is a NAME-BASED scan (see the module/class docstrings below for the
    explicit honesty caveat on what it does and does not prove)."""
    names: set[str] = set()
    for node in ast.walk(_parse(py_file)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _has_http_handler_class(py_file: Path) -> bool:
    """True if the module defines a class subclassing (something named)
    `BaseHTTPRequestHandler` -- the structural "no forked HTTP handler"
    check (T-4)."""
    for node in ast.walk(_parse(py_file)):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = base.attr if isinstance(base, ast.Attribute) else getattr(
                    base, "id", None
                )
                if base_name == "BaseHTTPRequestHandler":
                    return True
    return False


# ---------------------------------------------------------------------------
# T-1: module starts, binds the listener on a background thread, and serves
# MCP-over-stdio exposing exactly one tool, `request_approval`.
# ---------------------------------------------------------------------------


class TestT1ModuleShapeAndToolSurface:
    def test_module_exposes_a_module_level_fastmcp_instance_named_mcp(self):
        from mcp.server.fastmcp import FastMCP

        assert isinstance(mcp_server.mcp, FastMCP)

    def test_exposes_exactly_one_tool_named_request_approval(self):
        import asyncio

        tools = asyncio.run(mcp_server.mcp.list_tools())
        names = {t.name for t in tools}
        assert names == {"request_approval"}

    def test_start_listener_thread_registers_resolvers_then_runs_server_in_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []

        def fake_register() -> None:
            calls.append("register")

        def fake_run_server(**kwargs) -> None:
            calls.append("run_server")

        monkeypatch.setattr(mcp_server, "register_default_resolvers", fake_register)
        monkeypatch.setattr(mcp_server, "run_server", fake_run_server)

        thread = mcp_server.start_listener_thread()
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert calls == ["register", "run_server"]

    def test_start_listener_thread_returns_a_daemon_thread(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mcp_server, "register_default_resolvers", lambda: None)
        monkeypatch.setattr(mcp_server, "run_server", lambda **kw: None)

        thread = mcp_server.start_listener_thread()
        assert isinstance(thread, threading.Thread)
        assert thread.daemon is True
        thread.join(timeout=5)

    def test_start_listener_thread_with_a_real_key_keeps_running(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real (fake-blocking) `run_server` that never returns proves the
        thread stays alive -- i.e. genuinely "starts and binds" rather than
        exiting immediately, distinguishing T-1's happy path from T-9's
        fail-closed path below."""
        started = threading.Event()
        stop = threading.Event()

        def fake_run_server(**kwargs) -> None:
            started.set()
            stop.wait(timeout=5)  # mimics serve_forever() blocking

        # No real resolver registration/HTTP bind happens in this test (both
        # register_default_resolvers and run_server are faked below), so the
        # shared identity-registry global is never touched here.
        monkeypatch.setattr(mcp_server, "register_default_resolvers", lambda: None)
        monkeypatch.setattr(mcp_server, "run_server", fake_run_server)

        thread = mcp_server.start_listener_thread(token_dir=tmp_path)
        assert started.wait(timeout=5)
        assert thread.is_alive()
        stop.set()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# T-2: `request_approval` stages the envelope + returns the URL string; no
# browser is opened (B1).
# ---------------------------------------------------------------------------


class TestT2RequestApprovalStagesAndReturnsUrl:
    def test_stages_a_pending_hash_json_envelope_matching_stage_pending_content_shape(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)
        monkeypatch.delenv("GLEIPNIR_APPROVAL_BASE_URL", raising=False)

        content = "the exact pending Tier-3 change"
        before = int(time.time())
        result = mcp_server.request_approval(content, file_path="target.txt", tool="write")
        after = int(time.time())

        expected_hash = compute_change_hash(content.encode("utf-8"))
        staged_path = staged_path_for(tmp_path, expected_hash)
        assert staged_path.is_file()

        envelope = json.loads(staged_path.read_text(encoding="utf-8"))
        assert envelope["content"] == content
        assert envelope["filePath"] == "target.txt"
        assert envelope["tool"] == "write"
        assert before <= envelope["staged_at"] <= after

        assert isinstance(result, str)
        assert f"/approve/{expected_hash}" in result

    def test_defaults_file_path_and_tool_to_empty_string(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)
        content = "content with no filePath/tool given"
        mcp_server.request_approval(content)

        expected_hash = compute_change_hash(content.encode("utf-8"))
        envelope = json.loads(
            staged_path_for(tmp_path, expected_hash).read_text(encoding="utf-8")
        )
        assert envelope["filePath"] == ""
        assert envelope["tool"] == ""

    def test_returns_a_plain_string_not_a_dict_or_json_envelope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)
        result = mcp_server.request_approval("plain string check content")
        assert isinstance(result, str)
        with pytest.raises((ValueError, TypeError)):
            # A plain URL/message string is not itself valid JSON.
            json.loads(result)

    def test_never_imports_or_calls_a_browser_opener(self) -> None:
        # O-4/B1: request_approval must never auto-open a browser on this
        # host -- structurally, `webbrowser` must not even be imported.
        assert "webbrowser" not in _top_level_import_roots(MCP_SERVER_PATH)
        assert "webbrowser" not in _all_identifiers(MCP_SERVER_PATH)


# ---------------------------------------------------------------------------
# T-3: URL uses GLEIPNIR_APPROVAL_BASE_URL when set; relative-hint fallback
# when unset (parity with `buildApprovalUrl`, `tier3-gate.ts:435-445`).
# ---------------------------------------------------------------------------


class TestT3ApprovalUrlEnvVarAndFallback:
    def test_uses_the_base_url_env_var_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GLEIPNIR_APPROVAL_BASE_URL", "https://host.ts.net")
        url = mcp_server._build_approval_url("a" * 64)
        assert url == f"Approve at: https://host.ts.net/approve/{'a' * 64}"

    def test_strips_exactly_one_trailing_slash_from_the_base_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GLEIPNIR_APPROVAL_BASE_URL", "https://host.ts.net/")
        url = mcp_server._build_approval_url("b" * 64)
        assert url == f"Approve at: https://host.ts.net/approve/{'b' * 64}"

    def test_relative_hint_fallback_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GLEIPNIR_APPROVAL_BASE_URL", raising=False)
        url = mcp_server._build_approval_url("c" * 64)
        assert url == (
            f"Approve at: <your approval listener>/approve/{'c' * 64} "
            "(set GLEIPNIR_APPROVAL_BASE_URL to show the full URL here)"
        )

    def test_relative_hint_fallback_when_env_var_is_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An empty string is falsy -- must behave exactly like "unset",
        # never build a URL with an empty host.
        monkeypatch.setenv("GLEIPNIR_APPROVAL_BASE_URL", "")
        url = mcp_server._build_approval_url("d" * 64)
        assert "<your approval listener>" in url

    def test_request_approval_end_to_end_uses_the_fallback_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)
        monkeypatch.delenv("GLEIPNIR_APPROVAL_BASE_URL", raising=False)
        result = mcp_server.request_approval("some content")
        assert "<your approval listener>" in result

    def test_request_approval_end_to_end_uses_the_base_url_when_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)
        monkeypatch.setenv("GLEIPNIR_APPROVAL_BASE_URL", "https://host.ts.net")
        result = mcp_server.request_approval("some other content")
        expected_hash = compute_change_hash(b"some other content")
        assert result == f"Approve at: https://host.ts.net/approve/{expected_hash}"


# ---------------------------------------------------------------------------
# T-4 (structural): mcp_server.py defines no HTTP request-handler class and
# makes no hmac/hashlib mint/validate call of its own -- it wraps
# `server.py`, it does not fork it.
# ---------------------------------------------------------------------------


class TestT4NoForkedHttpOrCryptoLogic:
    def test_defines_no_http_request_handler_class(self) -> None:
        assert not _has_http_handler_class(MCP_SERVER_PATH)

    def test_does_not_import_hmac_or_hashlib_itself(self) -> None:
        # mcp_server.py reuses compute_change_hash (imported from .server)
        # rather than calling hashlib/hmac directly -- it has no crypto
        # logic of its own.
        roots = _top_level_import_roots(MCP_SERVER_PATH)
        assert "hmac" not in roots
        assert "hashlib" not in roots

    def test_does_not_import_http_server(self) -> None:
        assert "http" not in _top_level_import_roots(MCP_SERVER_PATH)


# ---------------------------------------------------------------------------
# T-5 (import scan): token.py, gate.py, and verify/marker.py do NOT import
# mcp -- the crypto core stays stdlib-only.
# ---------------------------------------------------------------------------


class TestT5CryptoCoreStaysMcpFree:
    @pytest.mark.parametrize(
        "relative_path",
        [
            "src/gleipnir/approval/token.py",
            "src/gleipnir/approval/gate.py",
            "src/gleipnir/verify/marker.py",
        ],
    )
    def test_core_module_does_not_import_mcp(self, relative_path: str) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        module_path = repo_root / relative_path
        assert module_path.is_file(), f"expected {module_path} to exist"
        assert "mcp" not in _top_level_import_roots(module_path)

    def test_mcp_server_is_the_only_approval_file_importing_mcp(self) -> None:
        approval_dir = Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "approval"
        for py_file in sorted(approval_dir.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            roots = _top_level_import_roots(py_file)
            if "mcp" in roots:
                assert py_file.name == "mcp_server.py", (
                    f"{py_file} imports `mcp` but is not mcp_server.py -- "
                    "only the FastMCP wrapper may import the SDK (Decision 8)"
                )


# ---------------------------------------------------------------------------
# T-8 (daemon lifecycle): the listener thread is a daemon thread (dies with
# the process; no orphan).
# ---------------------------------------------------------------------------


class TestT8DaemonLifecycle:
    def test_listener_thread_is_daemon(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mcp_server, "register_default_resolvers", lambda: None)
        monkeypatch.setattr(mcp_server, "run_server", lambda **kw: None)
        thread = mcp_server.start_listener_thread()
        assert thread.daemon is True
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# T-9 (fail-closed key): with GLEIPNIR_MARKER_KEY_FILE unset/empty, the MCP
# process refuses to serve the listener (KeyUnavailable), rather than
# serving keyless -- and does NOT crash the process (Decision 19).
# ---------------------------------------------------------------------------


class TestT9FailClosedKeyDoesNotCrashTheProcess:
    def test_missing_key_is_logged_and_the_thread_exits_without_raising(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)

        with caplog.at_level(logging.WARNING, logger=mcp_server.__name__):
            # Call the thread TARGET directly (synchronously) so the
            # KeyUnavailable failure path is deterministic, not racy.
            mcp_server._run_listener(key_file=None, token_dir=tmp_path)

        assert any(
            "listener" in record.message.lower() for record in caplog.records
        )

    def test_missing_key_via_real_thread_does_not_crash_the_process(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
        thread = mcp_server.start_listener_thread(key_file=None, token_dir=tmp_path)
        thread.join(timeout=5)
        # The thread exits (KeyUnavailable was caught, not propagated) --
        # if it had propagated, this would be an uncaught-thread-exception,
        # not silence; either way the test PROCESS survives, but we also
        # assert the thread actually terminated (log-and-continue, not
        # log-and-hang).
        assert not thread.is_alive()

    def test_request_approval_still_works_when_the_key_is_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Edge case 1: staging is key-independent -- request_approval must
        # keep working even though the listener could not start.
        monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
        monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)
        mcp_server._run_listener(key_file=None, token_dir=tmp_path)
        result = mcp_server.request_approval("staged despite no key")
        assert isinstance(result, str)
        assert "/approve/" in result


# ---------------------------------------------------------------------------
# T-11 (structural -- "wraps, never mints" reverse-import scan): mcp_server
# .py's source contains NO reference -- by name -- to capture_approval,
# mint_approval, or load_key, and imports ONLY the closed allow-list from
# .server.
# ---------------------------------------------------------------------------


class TestT11WrapsNeverMintsReverseImportScan:
    """T-11: the reverse-direction complement to T-5's import-scan (T-5
    asserts the crypto core does not import `mcp`; T-11 asserts the MCP
    wrapper does not import the minting core). A `from .server import
    capture_approval` followed by a call would mint a valid, content-bound
    approval token from inside this process (resolving identity against the
    local host via `tailscale whois` on `remote_ip`, `server.py:224-227`),
    silently defeating the separate-authenticated-device approval property
    (Decision 3 / the plan's Supersession clause).

    **Honesty note on scope (spec-review round 2, non-blocking Moderate
    finding -- folded in here, not skipped):** this is a name-based source
    scan aimed at accidental/incremental drift toward re-introducing minting
    logic in the wrapper, not adversarial obfuscation -- a
    deliberately-constructed dynamic reference (string concatenation,
    `getattr` with a computed name) would evade it; accepted because the
    threat model here is implementer drift, not a malicious wrapper author.
    """

    def test_source_contains_no_reference_to_any_forbidden_mint_key_symbol(
        self,
    ) -> None:
        identifiers = _all_identifiers(MCP_SERVER_PATH)
        found = identifiers & _FORBIDDEN_MINT_KEY_SYMBOLS
        assert not found, (
            f"mcp_server.py references forbidden minting/key symbol(s) "
            f"{found} -- this would let the MCP process mint a valid "
            "approval token itself, bypassing separate-device review "
            "(Decision 3/13, T-11)"
        )

    def test_imports_from_dot_server_are_a_subset_of_the_closed_allow_list(
        self,
    ) -> None:
        imported = _dot_server_import_names(MCP_SERVER_PATH)
        assert imported, "expected mcp_server.py to import something from .server"
        extra = imported - _ALLOWED_SERVER_IMPORTS
        assert not extra, (
            f"mcp_server.py imports {extra} from .server, outside the "
            f"closed allow-list {_ALLOWED_SERVER_IMPORTS} (Decision 13)"
        )

    def test_closed_allow_list_itself_excludes_every_forbidden_symbol(self) -> None:
        # Sanity/self-check: the allow-list this test enforces must not
        # itself contain a forbidden symbol (a guard against a future edit
        # accidentally widening _ALLOWED_SERVER_IMPORTS to include one).
        assert _ALLOWED_SERVER_IMPORTS.isdisjoint(_FORBIDDEN_MINT_KEY_SYMBOLS)

    def test_never_imports_token_module_or_marker_module_directly(self) -> None:
        # Belt-and-suspenders on top of the name-based scan above: no
        # `from .token import ...` and no `from ..verify.marker import ...`
        # at all (regardless of which names would be imported from them).
        for node in ast.walk(_parse(MCP_SERVER_PATH)):
            if not isinstance(node, ast.ImportFrom):
                continue
            assert node.module != "token" or node.level != 1, (
                "mcp_server.py must never import from .token (the crypto "
                "core) -- it only reuses .server's staging/URL helpers"
            )
            if node.module == "marker" and node.level == 2:
                pytest.fail(
                    "mcp_server.py must never import from ..verify.marker "
                    "(load_key lives there) -- Decision 13"
                )
