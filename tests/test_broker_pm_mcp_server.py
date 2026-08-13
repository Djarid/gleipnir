"""Coverage-gap tests for `src/gleipnir/broker/pm/mcp_server.py`.

Plan: `.gleipnir/plans/broker-pm-coverage-gap.md`. Target: raise line+branch
coverage on `mcp_server.py` from 25% to >=85% by exercising the wrapper-layer
functions and error branches NOT already covered by
`tests/test_broker_pm_platform.py` (the REST client layer -- `RemoteInfo`,
`parse_remote_url`, token resolution, `issue_*` REST verbs) or
`tests/test_broker_tool_surface.py` (the 4-tool set / force-param absence at
the tool-surface level). This file does NOT duplicate either.

Scope (plan Trace gaps G1-G6):

  - G1 `_detect_remote`: `subprocess.run` raising -> RuntimeError, non-zero
    returncode -> RuntimeError, and the success path delegating to
    `platform.parse_remote_url`.
  - G2 `_remote_or_error`: the success `{"remote": ...}` arm and the error
    `{"error": {"success": False, "error": ...}}` arm.
  - G3 `issue_create`: remote-resolve-fails early-return (no `platform` call)
    and the happy path (including `body=""` -> `None` normalization).
  - G4 `issue_update`: remote-resolve-fails early-return, PLUS the conditional
    field-building logic (all-three-set / none-set / one-set-others-omitted),
    and the happy-path delegation.
  - G5 `issue_comment`: remote-resolve-fails early-return + happy path.
  - G6 `issue_close`: remote-resolve-fails early-return + happy path.

Mocking boundaries (plan Decision 2): `platform.issue_*` is monkeypatched at
the module-attribute level for the four tool wrappers' happy paths (one layer
above where `test_broker_pm_platform.py` mocks `_http_request`, so this file
never re-exercises `platform`'s internals). `_detect_remote`'s own
exception / non-zero-returncode arms are driven by monkeypatching
`mcp_server.subprocess.run` -- the attribute as looked up inside
`mcp_server.py` itself. Wrapper error-path tests drive `_remote_or_error`
(via `_detect_remote` raising) and additionally set the corresponding
`platform.*` verb to an `AssertionError`-raising fake to prove no delegation
happens on the error path (the same "network-forbidden" pattern used at
`test_broker_pm_platform.py:133`).

Runs under the **broker profile** (imports `mcp` transitively via
`mcp_server`) -- see `tests/conftest.py` `collect_ignore`. Per the plan's
Decision 4 / edge case E-COLLECT, `.gleipnir/sandbox/profiles.toml`
`[profile.broker].test` is a Tier-3, operator-only, EXPLICIT file list that
must also be amended to add this file before `bin/gleipnir-sandbox test`
(broker profile) will collect it -- a bounded code agent cannot make that
edit itself.

Residual: `mcp_server.py` line 148 (`if __name__ == "__main__": mcp.run(...)`)
is the one expected uncovered line -- it only runs under `python -m ...`, not
import, and is out of scope for this file.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

from gleipnir.broker.pm import mcp_server, platform

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _remote_info(
    host: str = "github.com",
    owner: str = "owner",
    repo: str = "repo",
    plat: str = "github",
) -> platform.RemoteInfo:
    return platform.RemoteInfo(host=host, owner=owner, repo=repo, platform=plat)


class _Recorder:
    """Records positional+keyword args and returns a fixed canned response."""

    def __init__(self, response: Dict[str, Any]) -> None:
        self.response = response
        self.calls: List[Tuple[Tuple[Any, ...], Dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append((args, kwargs))
        return self.response


def _forbidden(*args: Any, **kwargs: Any) -> Any:
    """A fake that fails the test if called -- proves no delegation happened."""
    raise AssertionError("platform.* must not be called on the error path")


def _stub_error_resolve(
    monkeypatch: pytest.MonkeyPatch, message: str = "no remote"
) -> None:
    """Force `_remote_or_error` down its error arm without touching subprocess."""

    def _raise(repo_dir: str = "") -> platform.RemoteInfo:
        raise RuntimeError(message)

    monkeypatch.setattr(mcp_server, "_detect_remote", _raise)


def _stub_success_resolve(
    monkeypatch: pytest.MonkeyPatch, remote: platform.RemoteInfo
) -> None:
    """Force `_remote_or_error` down its success arm without touching subprocess."""
    monkeypatch.setattr(mcp_server, "_detect_remote", lambda repo_dir="": remote)


# ---------------------------------------------------------------------------
# G1 -- _detect_remote: subprocess-raise / non-zero-returncode / success.
# ---------------------------------------------------------------------------


class TestDetectRemote:
    def test_subprocess_run_raising_wraps_as_could_not_run_git(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise OSError("boom")

        monkeypatch.setattr(mcp_server.subprocess, "run", _raise)
        with pytest.raises(RuntimeError, match=r"^Could not run git: "):
            mcp_server._detect_remote()

    def test_non_zero_returncode_raises_could_not_determine_remote(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def _fake_run(*args: Any, **kwargs: Any) -> Any:
            return SimpleNamespace(
                returncode=1, stdout="", stderr="fatal: no such remote"
            )

        monkeypatch.setattr(mcp_server.subprocess, "run", _fake_run)
        with pytest.raises(
            RuntimeError, match="Could not determine the origin remote URL"
        ):
            mcp_server._detect_remote()

    def test_success_delegates_to_platform_parse_remote_url(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def _fake_run(*args: Any, **kwargs: Any) -> Any:
            return SimpleNamespace(
                returncode=0,
                stdout="https://github.com/owner/repo.git\n",
                stderr="",
            )

        monkeypatch.setattr(mcp_server.subprocess, "run", _fake_run)
        result = mcp_server._detect_remote()
        assert result == platform.RemoteInfo(
            host="github.com", owner="owner", repo="repo", platform="github"
        )


# ---------------------------------------------------------------------------
# G2 -- _remote_or_error: success arm + error arm.
# ---------------------------------------------------------------------------


class TestRemoteOrError:
    def test_success_arm_returns_remote_key(self, monkeypatch: pytest.MonkeyPatch):
        remote = _remote_info()
        monkeypatch.setattr(mcp_server, "_detect_remote", lambda repo_dir="": remote)
        assert mcp_server._remote_or_error("") == {"remote": remote}

    def test_error_arm_returns_structured_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise(repo_dir: str = "") -> platform.RemoteInfo:
            raise RuntimeError("nope")

        monkeypatch.setattr(mcp_server, "_detect_remote", _raise)
        assert mcp_server._remote_or_error("") == {
            "error": {"success": False, "error": "nope"}
        }


# ---------------------------------------------------------------------------
# G3 -- issue_create: error path (no delegation) + happy path.
# ---------------------------------------------------------------------------


class TestIssueCreate:
    def test_error_path_returns_error_without_calling_platform(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _stub_error_resolve(monkeypatch, "no remote")
        monkeypatch.setattr(platform, "issue_create", _forbidden)

        result = json.loads(mcp_server.issue_create("t"))
        assert result == {"success": False, "error": "no remote"}

    def test_happy_path_calls_platform_issue_create_with_body(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {"number": 1}})
        monkeypatch.setattr(platform, "issue_create", recorder)

        raw = mcp_server.issue_create("My title", body="body text", repo_dir="")
        result = json.loads(raw)

        assert result == {"success": True, "data": {"number": 1}}
        assert len(recorder.calls) == 1
        args, kwargs = recorder.calls[0]
        assert args == (remote, "My title", "body text")
        assert kwargs == {}

    def test_happy_path_empty_body_normalizes_to_none(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {}})
        monkeypatch.setattr(platform, "issue_create", recorder)

        mcp_server.issue_create("Title only", body="", repo_dir="")

        assert len(recorder.calls) == 1
        args, _kwargs = recorder.calls[0]
        assert args == (remote, "Title only", None)


# ---------------------------------------------------------------------------
# G4 -- issue_update: error path + conditional field-building + happy path.
# ---------------------------------------------------------------------------


class TestIssueUpdate:
    def test_error_path_returns_error_without_calling_platform(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _stub_error_resolve(monkeypatch, "no remote")
        monkeypatch.setattr(platform, "issue_update", _forbidden)

        result = json.loads(mcp_server.issue_update("7"))
        assert result == {"success": False, "error": "no remote"}

    def test_all_three_fields_set_are_all_passed_through(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {}})
        monkeypatch.setattr(platform, "issue_update", recorder)

        raw = mcp_server.issue_update("7", title="T", body="B", state="closed")
        result = json.loads(raw)

        assert result == {"success": True, "data": {}}
        assert len(recorder.calls) == 1
        args, kwargs = recorder.calls[0]
        assert args == (remote, "7")
        assert kwargs == {"title": "T", "body": "B", "state": "closed"}

    def test_none_set_omits_all_field_kwargs(self, monkeypatch: pytest.MonkeyPatch):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {}})
        monkeypatch.setattr(platform, "issue_update", recorder)

        mcp_server.issue_update("7")

        assert len(recorder.calls) == 1
        args, kwargs = recorder.calls[0]
        assert args == (remote, "7")
        assert kwargs == {}

    def test_one_field_set_others_omitted(self, monkeypatch: pytest.MonkeyPatch):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {}})
        monkeypatch.setattr(platform, "issue_update", recorder)

        mcp_server.issue_update("7", state="closed")

        assert len(recorder.calls) == 1
        args, kwargs = recorder.calls[0]
        assert args == (remote, "7")
        assert kwargs == {"state": "closed"}


# ---------------------------------------------------------------------------
# G5 -- issue_comment: error path + happy path.
# ---------------------------------------------------------------------------


class TestIssueComment:
    def test_error_path_returns_error_without_calling_platform(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _stub_error_resolve(monkeypatch, "no remote")
        monkeypatch.setattr(platform, "issue_comment", _forbidden)

        result = json.loads(mcp_server.issue_comment("7", "hello"))
        assert result == {"success": False, "error": "no remote"}

    def test_happy_path_calls_platform_issue_comment(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {"id": 99}})
        monkeypatch.setattr(platform, "issue_comment", recorder)

        raw = mcp_server.issue_comment("7", "the comment body", repo_dir="")
        result = json.loads(raw)

        assert result == {"success": True, "data": {"id": 99}}
        assert len(recorder.calls) == 1
        args, kwargs = recorder.calls[0]
        assert args == (remote, "7", "the comment body")
        assert kwargs == {}


# ---------------------------------------------------------------------------
# G6 -- issue_close: error path + happy path.
# ---------------------------------------------------------------------------


class TestIssueClose:
    def test_error_path_returns_error_without_calling_platform(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _stub_error_resolve(monkeypatch, "no remote")
        monkeypatch.setattr(platform, "issue_close", _forbidden)

        result = json.loads(mcp_server.issue_close("7"))
        assert result == {"success": False, "error": "no remote"}

    def test_happy_path_calls_platform_issue_close(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        remote = _remote_info()
        _stub_success_resolve(monkeypatch, remote)
        recorder = _Recorder({"success": True, "data": {"state": "closed"}})
        monkeypatch.setattr(platform, "issue_close", recorder)

        raw = mcp_server.issue_close("7", repo_dir="")
        result = json.loads(raw)

        assert result == {"success": True, "data": {"state": "closed"}}
        assert len(recorder.calls) == 1
        args, kwargs = recorder.calls[0]
        assert args == (remote, "7")
        assert kwargs == {}
