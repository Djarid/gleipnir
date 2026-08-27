"""AC-WIRE-1 — pure-Python protocol-level MCP-over-stdio wire confirmation.

Plan: `.gleipnir/plans/pi-dev-replatform-s6.md`, §Test-harness constraint /
§Assemble step 3c / §Stress-test AC-WIRE-1. Runs under the **broker profile**
(needs the real `mcp` package + a real `python -m
gleipnir.broker.git.mcp_server` subprocess) — see `tests/conftest.py`
`collect_ignore`.

**What this file is NOT:** it does not invoke the TS `mcpStdioClient.ts`
client. `Containerfile.broker` (`python:3.12-slim`) has no Node/TypeScript
runtime, so the TS client cannot run here; `Containerfile.pi` (`node:22-slim`)
has no Python, so the real broker cannot run there either. Per the plan's
honest scope split: this file proves the REAL FastMCP-stdio server's wire
FORMAT in pure Python (both sides Python, same image); the hand-rolled TS
client's conformance to that SAME format is proven separately, against a
Node mock speaking the identical subset, by
`pi-package/test/mcpStdioClient.test.ts` under `[profile.pi]`.

**Why this file speaks raw JSON-RPC by hand (no `mcp` client SDK):** the
POINT is to record the exact bytes a hand-rolled client must produce/expect —
using the `mcp` package's own client here would test the SDK against itself,
not pin the wire subset an independent hand-rolled implementation needs.

**Wire subset recorded (mirrors `mcpStdioClient.ts`'s implementation, which
this test exists to confirm against the REAL server, not merely the mock):**
newline-delimited JSON-RPC 2.0 over stdin/stdout; `initialize` request with
`protocolVersion`/`capabilities`/`clientInfo` params; a `notifications/
initialized` notification (no `id`, no reply) sent before the first
`tools/call`; a `tools/call` request with `{"name": ..., "arguments": ...}`
params; a `result.content` list of `{"type": "text", "text": ...}` items on
success.

**Standing-vs-one-time (§Open Items #5):** `[profile.broker]`'s `test` argv
in `.gleipnir/sandbox/profiles.toml` is Tier-3 (`.gleipnir/sandbox/**`),
operator-only — this delegation cannot add this file to it. Until an
operator does, this file is authored but NOT collected by
`bin/gleipnir-sandbox test --profile broker`'s explicit file list (mirrors
the `test_broker_git_mcp_server.py` / `test_broker_git_commit_guard.py`
precedent, which name the identical Tier-3 residual in their own
docstrings).
"""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


def _git(args: List[str], cwd: str) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"test-setup `git {' '.join(args)}` failed in {cwd}: {result.stderr}"
    )
    return result.stdout


@pytest.fixture
def repo(tmp_path: Path) -> str:
    """A real temp git repo, branch `main`, with one prior commit, so
    `git_status` has a real, unambiguous branch/porcelain state to report."""
    repo_dir = str(tmp_path / "wire-protocol-repo")
    Path(repo_dir).mkdir()
    _git(["init"], repo_dir)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], repo_dir)
    _git(["config", "user.email", "wire-protocol-test@example.invalid"], repo_dir)
    _git(["config", "user.name", "wire-protocol-test"], repo_dir)
    (Path(repo_dir) / "README.md").write_text("wire protocol fixture\n")
    _git(["add", "README.md"], repo_dir)
    _git(["commit", "-m", "initial"], repo_dir)
    return repo_dir


class _StdioJsonRpcClient:
    """The bare-minimum, hand-rolled JSON-RPC-over-stdio driver this test
    uses to talk to the REAL broker subprocess — deliberately NOT the `mcp`
    package's own client (see module docstring: testing the SDK against
    itself would not pin the wire subset an independent client needs)."""

    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self._proc = proc
        self._next_id = 1
        self._selector = selectors.DefaultSelector()
        assert proc.stdout is not None
        self._selector.register(proc.stdout, selectors.EVENT_READ)

    def _allocate_id(self) -> int:
        req_id = self._next_id
        self._next_id += 1
        return req_id

    def _write(self, message: Dict[str, Any]) -> None:
        assert self._proc.stdin is not None
        line = json.dumps(message) + "\n"
        self._proc.stdin.write(line.encode("utf-8"))
        self._proc.stdin.flush()

    # 20s (not the original 10s): an observed intermittent flake this
    # session (~1-in-5 sandbox runs) showed a COLD container invocation
    # occasionally take >10s just to import `mcp`/`anyio`/pydantic and reach
    # the first `initialize` reply (proc.poll() was still `None` -- the
    # child was alive and simply slow, not crashed; confirmed via the
    # stderr/poll diagnostic below, which was empty on that run). This is
    # process cold-start latency, not a wire-protocol defect, so widening
    # the margin is the correct fix (vs. e.g. retrying), and stays cheap:
    # it only extends the wait on an already-slow path, never on the
    # common fast path.
    def _read_line(self, timeout: float = 20.0) -> Optional[str]:
        assert self._proc.stdout is not None
        events = self._selector.select(timeout=timeout)
        if not events:
            return None
        line = self._proc.stdout.readline()
        if not line:
            return None
        return line.decode("utf-8").rstrip("\n")

    def _read_available_stderr(self, timeout: float = 0.2) -> str:
        """Best-effort, non-blocking drain of whatever the child has already
        written to stderr. Used ONLY on a diagnosable failure (never on the
        happy path): a short `select()` poll followed by non-blocking
        `os.read()` calls, so a still-alive child that never closes stderr
        can never hang this helper (unlike a bare `.read()`, which would
        block until EOF)."""
        assert self._proc.stderr is not None
        sel = selectors.DefaultSelector()
        sel.register(self._proc.stderr, selectors.EVENT_READ)
        chunks: List[bytes] = []
        remaining = timeout
        try:
            while True:
                events = sel.select(timeout=remaining)
                if not events:
                    break
                chunk = os.read(self._proc.stderr.fileno(), 65536)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining = 0.0  # drain whatever's already buffered, then stop
        finally:
            sel.close()
        return b"".join(chunks).decode("utf-8", errors="replace")

    def request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        req_id = self._allocate_id()
        self._write({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        raw = self._read_line()
        if raw is None:
            exit_status = self._proc.poll()
            stderr_tail = self._read_available_stderr()
            raise AssertionError(
                f"broker child produced no response line for method={method!r} "
                f"(timed out or closed stdout); proc.poll()={exit_status!r} "
                f"(None means still running); captured stderr:\n"
                f"{stderr_tail or '<empty>'}"
            )
        parsed = json.loads(raw)
        assert parsed.get("id") == req_id, (
            f"response id {parsed.get('id')!r} did not match request id {req_id!r}: {raw!r}"
        )
        return parsed

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        message: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)


# Root cause (confirmed via the stderr capture in `_read_available_stderr`,
# added above): the child is spawned with `cwd=repo` -- a throwaway
# `tmp_path` git repo, NOT this repo's `src/` layout -- and inherits no
# `PYTHONPATH`. `python -m gleipnir.broker.git.mcp_server` resolves modules
# off `sys.path`, which for `-m` does NOT include this repo's `src/`
# directory unless the package is `pip install -e`'d (it isn't; see
# `Containerfile.broker`) or `PYTHONPATH` names it explicitly. Without
# either, the child dies at module-resolution time with
# `ModuleNotFoundError: No module named 'gleipnir'` (written to stderr,
# closing stdout before anything is ever read) -- exactly the "timed out or
# closed stdout" symptom this fixture's callers observed. `cwd=repo` itself
# is fine to keep (the tool calls pass `repo_dir` explicitly as an argument;
# the child's cwd is not otherwise load-bearing) -- the fix is purely
# `PYTHONPATH`.
_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


@pytest.fixture
def broker_proc(repo: str):
    child_env = dict(os.environ)
    # Prepend (don't clobber) in case a caller's environment already sets
    # PYTHONPATH to something relevant.
    existing = child_env.get("PYTHONPATH", "")
    child_env["PYTHONPATH"] = (
        _SRC_DIR if not existing else f"{_SRC_DIR}{os.pathsep}{existing}"
    )
    # Defense-in-depth against a stdio message sitting unflushed in a
    # block-buffered child (piped stdout is not a tty, so CPython defaults
    # to block-buffering it) -- belt-and-suspenders alongside the explicit
    # `.flush()` this test's own `_write()` already does on ITS side.
    child_env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "gleipnir.broker.git.mcp_server"],
        cwd=repo,
        env=child_env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        yield proc
    finally:
        proc.kill()
        proc.wait(timeout=10)


def test_ac_wire_1_initialize_and_git_status_round_trip(broker_proc, repo: str) -> None:
    """AC-WIRE-1: a real `initialize` + `notifications/initialized` +
    `tools/call("git_status")` round-trip against the REAL, UNCHANGED
    `git/mcp_server.py` broker, pinning the exact wire subset the hand-rolled
    TS client (`mcpStdioClient.ts`) targets."""
    client = _StdioJsonRpcClient(broker_proc)

    init_response = client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "gleipnir-broker-relay-wire-test", "version": "0.1.0"},
        },
    )
    assert "error" not in init_response, f"initialize failed: {init_response.get('error')}"
    result = init_response.get("result")
    assert isinstance(result, dict), f"initialize result must be an object: {init_response!r}"
    # Record the exact keys a hand-rolled client can rely on.
    assert "protocolVersion" in result, "initialize result must carry protocolVersion"
    assert "capabilities" in result, "initialize result must carry capabilities"
    assert "serverInfo" in result, "initialize result must carry serverInfo"

    # The MCP stdio convention: a notification (no `id`) after a successful
    # `initialize`, before the first `tools/call`. FastMCP-stdio never
    # replies to it (it is a notification) — nothing to read here.
    client.notify("notifications/initialized")

    call_response = client.request(
        "tools/call",
        {"name": "git_status", "arguments": {"repo_dir": repo}},
    )
    assert "error" not in call_response, f"tools/call failed: {call_response.get('error')}"
    call_result = call_response.get("result")
    assert isinstance(call_result, dict), f"tools/call result must be an object: {call_response!r}"
    content = call_result.get("content")
    assert isinstance(content, list) and len(content) >= 1, (
        f"tools/call result.content must be a non-empty list: {call_result!r}"
    )
    first_item = content[0]
    assert first_item.get("type") == "text", (
        f"tools/call result.content[0].type must be 'text': {first_item!r}"
    )
    # git_status's payload is itself a JSON string (mcp_server.py's tool
    # functions return `json.dumps(...)`) — confirm it parses and reports the
    # branch this fixture created, proving the round-trip reached the REAL
    # git_status implementation, not a stub.
    inner = json.loads(first_item["text"])
    assert inner.get("branch") == "main", f"git_status did not report the expected branch: {inner!r}"


def test_ac_wire_1_unknown_tool_is_a_structured_error_not_a_crash(broker_proc, repo: str) -> None:
    """A malformed/unknown `tools/call` name must come back as a structured
    failure, never an unhandled server crash.

    **Corrected against the REAL wire capture** (this test's original form
    asserted a top-level JSON-RPC `error`, which this session's diagnostic
    run against the real, unmodified `git/mcp_server.py` broker disproved:
    the actual response was
    `{"jsonrpc": "2.0", "id": 2, "result": {"content": [...], "isError":
    true}}` — no `error` key at all). This matches the MCP spec's intended
    split: `tools/call` itself is a valid method (a protocol-level concern);
    which TOOL NAME is unrecognised is the tool's own execution outcome, so
    FastMCP reports it as an ordinary `result` with `isError: true`, not a
    JSON-RPC `error`. The never-raise posture `mcpStdioClient.ts` assumes
    (idiom-table row 6) still holds — no crash, still structured — but this
    is now pinned to the field the real wire subset actually uses. (NOTE for
    a future session: `mcpStdioClient.ts`'s `readResponseFor` currently only
    inspects the top-level `error` field, not `result.isError` — given this
    confirmed wire shape, that is a likely latent gap in the TS client, but
    fixing `pi-package/**` is out of this delegation's file scope; flagged
    for separate follow-up.)"""
    client = _StdioJsonRpcClient(broker_proc)
    client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "gleipnir-broker-relay-wire-test", "version": "0.1.0"},
        },
    )
    client.notify("notifications/initialized")

    response = client.request(
        "tools/call",
        {"name": "totally_unregistered_tool_xyz", "arguments": {}},
    )
    assert "error" not in response, (
        f"an unknown tool name must not surface as a JSON-RPC-level error "
        f"(the real broker reports it via result.isError instead): {response!r}"
    )
    result = response.get("result")
    assert isinstance(result, dict), f"tools/call result must be an object: {response!r}"
    assert result.get("isError") is True, (
        f"an unknown tool name must be reported via result.isError=True, "
        f"never a silent/ambiguous result: {result!r}"
    )
    content = result.get("content")
    assert isinstance(content, list) and len(content) >= 1, (
        f"an isError result must still carry a non-empty content list: {result!r}"
    )
    first_item = content[0]
    assert first_item.get("type") == "text", (
        f"tools/call result.content[0].type must be 'text': {first_item!r}"
    )
    assert "totally_unregistered_tool_xyz" in first_item.get("text", ""), (
        f"the error text should name the unknown tool: {first_item!r}"
    )
