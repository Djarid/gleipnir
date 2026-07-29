"""Unit tests for the PM broker's remote/token/REST platform client.

Plan: `.gleipnir/plans/broker-mcp.md`, Assemble Step 2 / Step 4. Target
module (does NOT exist yet -- this is the point, Axiom 1):

    src/gleipnir/broker/pm/platform.py   (stdlib-only: os, re, json, urllib)

ASSUMED API (documented for the implementer -- test-first defines the
concrete contract):

    RemoteInfo
        A value object with attributes: host (str), owner (str),
        repo (str), platform ("github" | "gitlab").

    parse_remote_url(url: str) -> RemoteInfo
        Handles HTTPS ("https://github.com/owner/repo.git"), SSH
        ("git@gitlab.com:owner/repo.git") and GitLab subgroup nesting
        ("https://gitlab.com/group/subgroup/repo.git" -> owner is the full
        "group/subgroup" path -- documented convention, not re-litigated
        here, just pinned to one unambiguous target).

    has_token(platform: str) -> bool
    get_token(platform: str) -> str | None
        Resolve GITLAB_TOKEN for platform=="gitlab", GITHUB_TOKEN for
        platform=="github", from os.environ only (no python-dotenv --
        Link L2 of the plan).

    _http_request(method: str, url: str, *, token: str | None,
                   json_body: dict | None = None, timeout: float = 10.0)
        -> dict
        The ONE seam all four issue_* verbs call through. Tests monkeypatch
        this attribute directly (`monkeypatch.setattr(platform,
        "_http_request", fake)`) so NO live network is ever hit. If the
        implementer names this helper differently, these tests will fail
        with an AttributeError naming `_http_request` -- match this name.

    issue_create(remote: RemoteInfo, title: str, body: str | None = None) -> dict
    issue_update(remote: RemoteInfo, issue_id, **fields) -> dict
    issue_comment(remote: RemoteInfo, issue_id, body: str) -> dict
    issue_close(remote: RemoteInfo, issue_id) -> dict
        Each returns {"success": True, "data": <parsed _http_request result>}
        on success, or {"success": False, "error": <str>} when no token is
        configured -- WITHOUT raising and WITHOUT calling _http_request.
"""

from __future__ import annotations

import pytest

from gleipnir.broker.pm import platform


FAKE_GITHUB_TOKEN = "ghp_" + ("z9Y8x7" * 6)  # 40 chars total, shaped only
FAKE_GITLAB_TOKEN = "glpat-" + ("Q1w2E3" * 3)  # shaped only, not a real token


# ---------------------------------------------------------------------------
# parse_remote_url
# ---------------------------------------------------------------------------


class TestParseRemoteUrl:
    def test_https_github_url(self):
        info = platform.parse_remote_url("https://github.com/owner/repo.git")
        assert info.host == "github.com"
        assert info.owner == "owner"
        assert info.repo == "repo"
        assert info.platform == "github"

    def test_ssh_gitlab_url(self):
        info = platform.parse_remote_url("git@gitlab.com:owner/repo.git")
        assert info.host == "gitlab.com"
        assert info.owner == "owner"
        assert info.repo == "repo"
        assert info.platform == "gitlab"

    def test_https_gitlab_subgroup_url(self):
        info = platform.parse_remote_url(
            "https://gitlab.com/group/subgroup/repo.git"
        )
        assert info.host == "gitlab.com"
        assert info.owner == "group/subgroup"
        assert info.repo == "repo"
        assert info.platform == "gitlab"

    def test_scp_like_github_url_without_dot_git_suffix(self):
        info = platform.parse_remote_url("git@github.com:owner/repo")
        assert info.host == "github.com"
        assert info.owner == "owner"
        assert info.repo == "repo"
        assert info.platform == "github"


# ---------------------------------------------------------------------------
# token resolution
# ---------------------------------------------------------------------------


class TestTokenResolution:
    def test_has_token_true_for_gitlab_when_env_set(self, monkeypatch):
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        assert platform.has_token("gitlab") is True
        assert platform.get_token("gitlab") == FAKE_GITLAB_TOKEN
        assert platform.has_token("github") is False

    def test_has_token_true_for_github_when_env_set(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        assert platform.has_token("github") is True
        assert platform.get_token("github") == FAKE_GITHUB_TOKEN
        assert platform.has_token("gitlab") is False

    def test_has_token_false_when_neither_env_set(self, monkeypatch):
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        assert platform.has_token("gitlab") is False
        assert platform.has_token("github") is False
        assert platform.get_token("gitlab") is None
        assert platform.get_token("github") is None


# ---------------------------------------------------------------------------
# issue_* verbs -- no-token structured error (no crash, no network)
# ---------------------------------------------------------------------------


class TestIssueOpsWithoutToken:
    def test_issue_create_without_token_returns_structured_error(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        def _network_forbidden(*args, **kwargs):
            raise AssertionError(
                "no-token path must not attempt network access via _http_request"
            )

        monkeypatch.setattr(platform, "_http_request", _network_forbidden)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_create(remote, title="Bug found")

        assert result["success"] is False
        assert isinstance(result.get("error"), str) and result["error"]


# ---------------------------------------------------------------------------
# issue_* verbs -- happy path, REST mocked via _http_request
# ---------------------------------------------------------------------------


class _RequestRecorder:
    """Records every call and returns a fixed canned response."""

    def __init__(self, response):
        self.response = response
        self.calls: list[dict] = []

    def __call__(self, method, url, *, token=None, json_body=None, timeout=10.0):
        self.calls.append(
            {"method": method, "url": url, "token": token, "json_body": json_body}
        )
        return self.response


class TestIssueCreateHappyPath:
    def test_issue_create_hits_github_rest_with_correct_url_method_and_payload(
        self, monkeypatch
    ):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        canned_response = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/issues/42",
        }
        recorder = _RequestRecorder(canned_response)
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_create(remote, title="Bug found", body="steps to repro")

        assert result["success"] is True
        assert result["data"] == canned_response

        assert len(recorder.calls) == 1
        call = recorder.calls[0]
        assert call["method"] == "POST"
        assert call["url"] == "https://api.github.com/repos/owner/repo/issues"
        assert call["token"] == FAKE_GITHUB_TOKEN
        assert call["json_body"]["title"] == "Bug found"
        assert call["json_body"]["body"] == "steps to repro"

    def test_issue_create_hits_gitlab_rest_with_correct_url(self, monkeypatch):
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        canned_response = {"iid": 7, "web_url": "https://gitlab.com/owner/repo/-/issues/7"}
        recorder = _RequestRecorder(canned_response)
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("git@gitlab.com:owner/repo.git")
        result = platform.issue_create(remote, title="Bug found")

        assert result["success"] is True
        assert result["data"] == canned_response
        assert len(recorder.calls) == 1
        assert recorder.calls[0]["method"] == "POST"
        assert "gitlab.com" in recorder.calls[0]["url"]
        assert recorder.calls[0]["token"] == FAKE_GITLAB_TOKEN
