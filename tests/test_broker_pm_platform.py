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
                   platform: str, json_body: dict | None = None,
                   timeout: float = 10.0)
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

import json

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

    def test_ssh_explicit_protocol_url(self):
        info = platform.parse_remote_url("ssh://git@gitlab.com/owner/repo.git")
        assert info.host == "gitlab.com"
        assert info.owner == "owner"
        assert info.repo == "repo"
        assert info.platform == "gitlab"

    def test_ssh_explicit_protocol_url_with_port(self):
        info = platform.parse_remote_url("ssh://git@host:22/owner/repo.git")
        assert info.host == "host"
        assert info.owner == "owner"
        assert info.repo == "repo"

    def test_ssh_explicit_protocol_no_match_falls_through(self):
        # No trailing "/<path>" -> _SSH_PROTO_RE fails to match -> the
        # `if match:` branch (line 92) is not taken -> falls through with
        # empty host/path.
        info = platform.parse_remote_url("ssh://host-with-no-path")
        assert info.host == ""
        assert info.owner == ""
        assert info.repo == ""

    def test_https_trailing_slash_only_fails_regex_and_falls_through(self):
        # _HTTPS_RE requires `(.+)$` after the slash; a trailing-slash-only
        # URL fails the regex entirely -> host/path stay "" -> line 100
        # `else ("", "")` -> owner/repo "" -> platform "gitlab" (E2).
        info = platform.parse_remote_url("https://github.com/")
        assert info.host == ""
        assert info.owner == ""
        assert info.repo == ""
        assert info.platform == "gitlab"

    def test_https_bare_scheme_falls_through(self):
        info = platform.parse_remote_url("https://")
        assert info.host == ""
        assert info.owner == ""
        assert info.repo == ""
        assert info.platform == "gitlab"

    def test_garbage_url_no_match_falls_through(self):
        info = platform.parse_remote_url("garbage-no-colon-no-slash")
        assert info.host == ""
        assert info.owner == ""
        assert info.repo == ""
        assert info.platform == "gitlab"

    def test_https_url_with_only_dot_git_path_yields_empty_owner_repo(self):
        # path==".git" after stripping the ".git" suffix -> "" -> parts==[]
        # -> _split_owner_repo's `if not parts: return "", ""` (line 61).
        info = platform.parse_remote_url("https://github.com/.git")
        assert info.host == "github.com"
        assert info.owner == ""
        assert info.repo == ""
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

    def test_get_token_returns_none_for_unknown_platform(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        assert platform.get_token("bitbucket") is None
        assert platform.has_token("bitbucket") is False


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

    def __call__(
        self, method, url, *, token=None, platform=None, json_body=None, timeout=10.0
    ):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "token": token,
                "platform": platform,
                "json_body": json_body,
            }
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
        assert call["platform"] == "github"

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
        assert recorder.calls[0]["platform"] == "gitlab"

    def test_issue_create_gitlab_with_body_sets_description_not_body(
        self, monkeypatch
    ):
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        recorder = _RequestRecorder({"iid": 1})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("git@gitlab.com:owner/repo.git")
        result = platform.issue_create(remote, title="Bug found", body="desc")

        assert result["success"] is True
        assert len(recorder.calls) == 1
        json_body = recorder.calls[0]["json_body"]
        assert json_body["description"] == "desc"
        assert "body" not in json_body


# ---------------------------------------------------------------------------
# _api_base / _issues_endpoint -- GitHub Enterprise custom-domain branch
# ---------------------------------------------------------------------------


class TestApiBaseAndEndpoints:
    def test_api_base_github_enterprise_custom_domain_uses_api_v3(self):
        remote = platform.RemoteInfo(
            host="ghe.corp.example", owner="o", repo="r", platform="github"
        )
        assert platform._api_base(remote) == "https://ghe.corp.example/api/v3"
        assert platform._issues_endpoint(remote).startswith(
            "https://ghe.corp.example/api/v3/repos/"
        )

    def test_api_base_github_com_uses_api_github_com(self):
        remote = platform.RemoteInfo(
            host="github.com", owner="o", repo="r", platform="github"
        )
        assert platform._api_base(remote) == "https://api.github.com"

    def test_api_base_gitlab_uses_api_v4(self):
        remote = platform.RemoteInfo(
            host="gitlab.com", owner="o", repo="r", platform="gitlab"
        )
        assert platform._api_base(remote) == "https://gitlab.com/api/v4"
        assert platform._issues_endpoint(remote).startswith(
            "https://gitlab.com/api/v4/projects/"
        )


# ---------------------------------------------------------------------------
# _http_request -- the real network seam (urllib.request.urlopen mocked)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, raw: bytes):
        self._raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._raw


class _UrlopenRecorder:
    def __init__(self, raw: bytes = b""):
        self.raw = raw
        self.request = None  # the urllib.request.Request passed in
        self.timeout = None

    def __call__(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        return _FakeResponse(self.raw)


class TestHttpRequest:
    def test_github_platform_sends_bearer_header(self, monkeypatch):
        rec = _UrlopenRecorder()
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        platform._http_request(
            "GET",
            "https://api.github.com/repos/owner/repo/issues",
            token=FAKE_GITHUB_TOKEN,
            platform="github",
        )

        assert rec.request.get_header("Authorization") == f"Bearer {FAKE_GITHUB_TOKEN}"
        assert rec.request.get_header("Private-token") is None

    def test_gitlab_platform_sends_private_token_header(self, monkeypatch):
        rec = _UrlopenRecorder()
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        platform._http_request(
            "GET",
            "https://gitlab.com/api/v4/projects/owner%2Frepo/issues",
            token=FAKE_GITLAB_TOKEN,
            platform="gitlab",
        )

        assert rec.request.get_header("Private-token") == FAKE_GITLAB_TOKEN
        assert rec.request.get_header("Authorization") is None

    def test_no_token_sets_neither_auth_header(self, monkeypatch):
        rec = _UrlopenRecorder()
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        platform._http_request(
            "GET", "https://api.github.com/repos/owner/repo/issues", platform="github"
        )

        assert rec.request.get_header("Authorization") is None
        assert rec.request.get_header("Private-token") is None
        assert rec.request.get_header("Content-type") == "application/json"

    def test_json_body_is_encoded_as_bytes_with_content_type(self, monkeypatch):
        rec = _UrlopenRecorder()
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        platform._http_request(
            "POST",
            "https://api.github.com/repos/owner/repo/issues",
            platform="github",
            json_body={"title": "hi"},
        )

        assert rec.request.data == json.dumps({"title": "hi"}).encode("utf-8")
        assert rec.request.get_header("Content-type") == "application/json"

    def test_no_json_body_leaves_data_none(self, monkeypatch):
        rec = _UrlopenRecorder()
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        platform._http_request(
            "GET", "https://api.github.com/repos/owner/repo/issues", platform="github"
        )

        assert rec.request.data is None

    def test_empty_response_body_returns_empty_dict(self, monkeypatch):
        rec = _UrlopenRecorder(raw=b"")
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        result = platform._http_request(
            "GET", "https://api.github.com/repos/owner/repo/issues", platform="github"
        )

        assert result == {}

    def test_non_empty_response_body_returns_parsed_json(self, monkeypatch):
        rec = _UrlopenRecorder(raw=b'{"number": 1}')
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        result = platform._http_request(
            "GET", "https://api.github.com/repos/owner/repo/issues", platform="github"
        )

        assert result == {"number": 1}

    def test_ghe_custom_domain_uses_bearer_via_platform_arg_direct_seam(
        self, monkeypatch
    ):
        # The direct-seam fix proof (D7/D8): a URL with NO "github" substring,
        # but platform="github" -- pre-fix this would have sent PRIVATE-TOKEN
        # (URL-substring logic); post-fix it follows the `platform` arg.
        rec = _UrlopenRecorder()
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        platform._http_request(
            "POST",
            "https://ghe.corp.example/api/v3/repos/o/r/issues",
            token=FAKE_GITHUB_TOKEN,
            platform="github",
        )

        assert rec.request.get_header("Authorization") == f"Bearer {FAKE_GITHUB_TOKEN}"
        assert rec.request.get_header("Private-token") is None


# ---------------------------------------------------------------------------
# issue_update -- no-token error + PATCH(github)/PUT(gitlab) branches
# ---------------------------------------------------------------------------


class TestIssueUpdate:
    def test_issue_update_without_token_returns_structured_error(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        def _network_forbidden(*args, **kwargs):
            raise AssertionError("no-token path must not call _http_request")

        monkeypatch.setattr(platform, "_http_request", _network_forbidden)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_update(remote, 42, title="New title")

        assert result["success"] is False
        assert isinstance(result.get("error"), str) and result["error"]

    def test_issue_update_github_uses_patch(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        recorder = _RequestRecorder({"number": 42})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_update(remote, 42, title="New title")

        assert result["success"] is True
        call = recorder.calls[0]
        assert call["method"] == "PATCH"
        assert call["url"].endswith("/issues/42")
        assert call["json_body"] == {"title": "New title"}
        assert call["platform"] == "github"

    def test_issue_update_gitlab_uses_put(self, monkeypatch):
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        recorder = _RequestRecorder({"iid": 7})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("git@gitlab.com:owner/repo.git")
        result = platform.issue_update(remote, 7, title="New title")

        assert result["success"] is True
        call = recorder.calls[0]
        assert call["method"] == "PUT"
        assert call["url"].endswith("/issues/7")
        assert call["json_body"] == {"title": "New title"}
        assert call["platform"] == "gitlab"


# ---------------------------------------------------------------------------
# issue_comment -- no-token error + /comments(github) vs /notes(gitlab)
# ---------------------------------------------------------------------------


class TestIssueComment:
    def test_issue_comment_without_token_returns_structured_error(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        def _network_forbidden(*args, **kwargs):
            raise AssertionError("no-token path must not call _http_request")

        monkeypatch.setattr(platform, "_http_request", _network_forbidden)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_comment(remote, 42, "a comment")

        assert result["success"] is False
        assert isinstance(result.get("error"), str) and result["error"]

    def test_issue_comment_github_uses_comments_endpoint(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        recorder = _RequestRecorder({"id": 1})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_comment(remote, 42, "a comment")

        assert result["success"] is True
        call = recorder.calls[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/42/comments")
        assert call["json_body"] == {"body": "a comment"}
        assert call["platform"] == "github"

    def test_issue_comment_gitlab_uses_notes_endpoint(self, monkeypatch):
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        recorder = _RequestRecorder({"id": 1})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("git@gitlab.com:owner/repo.git")
        result = platform.issue_comment(remote, 7, "a comment")

        assert result["success"] is True
        call = recorder.calls[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/7/notes")
        assert call["json_body"] == {"body": "a comment"}
        assert call["platform"] == "gitlab"


# ---------------------------------------------------------------------------
# issue_close -- no-token error + PATCH{state:closed}(github) vs
# PUT{state_event:close}(gitlab)
# ---------------------------------------------------------------------------


class TestIssueClose:
    def test_issue_close_without_token_returns_structured_error(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        def _network_forbidden(*args, **kwargs):
            raise AssertionError("no-token path must not call _http_request")

        monkeypatch.setattr(platform, "_http_request", _network_forbidden)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_close(remote, 42)

        assert result["success"] is False
        assert isinstance(result.get("error"), str) and result["error"]

    def test_issue_close_github_uses_patch_state_closed(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        recorder = _RequestRecorder({"number": 42})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("https://github.com/owner/repo.git")
        result = platform.issue_close(remote, 42)

        assert result["success"] is True
        call = recorder.calls[0]
        assert call["method"] == "PATCH"
        assert call["json_body"] == {"state": "closed"}
        assert call["platform"] == "github"

    def test_issue_close_gitlab_uses_put_state_event_close(self, monkeypatch):
        monkeypatch.setenv("GITLAB_TOKEN", FAKE_GITLAB_TOKEN)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        recorder = _RequestRecorder({"iid": 7})
        monkeypatch.setattr(platform, "_http_request", recorder)

        remote = platform.parse_remote_url("git@gitlab.com:owner/repo.git")
        result = platform.issue_close(remote, 7)

        assert result["success"] is True
        call = recorder.calls[0]
        assert call["method"] == "PUT"
        assert call["json_body"] == {"state_event": "close"}
        assert call["platform"] == "gitlab"


# ---------------------------------------------------------------------------
# The GHE auth-header fix (D7) -- full-path characterization, urllib mocked
# so the REAL header-selection logic in _http_request runs (not the
# _RequestRecorder double). Proves the fix end-to-end through issue_create.
# ---------------------------------------------------------------------------


class TestGheAuthHeaderFixFullPath:
    def test_issue_create_on_ghe_custom_domain_sends_bearer_not_private_token(
        self, monkeypatch
    ):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_GITHUB_TOKEN)
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        rec = _UrlopenRecorder(raw=b'{"number": 1}')
        monkeypatch.setattr(platform.urllib.request, "urlopen", rec)

        remote = platform.RemoteInfo(
            host="ghe.corp.example", owner="o", repo="r", platform="github"
        )
        result = platform.issue_create(remote, title="Bug found")

        assert result["success"] is True
        assert rec.request.get_header("Authorization") == f"Bearer {FAKE_GITHUB_TOKEN}"
        assert rec.request.get_header("Private-token") is None
        assert "ghe.corp.example" in rec.request.full_url
