"""Gleipnir PM broker -- remote/token detection + GitHub/GitLab REST client.

stdlib-only (`os`, `re`, `json`, `urllib`) so this module stays unit-testable
without the `mcp` SDK installed (see `tests/test_broker_stdlib_only.py`).
Stateless: no local cache, no SQLite.

Influenced by (pattern, not code) AETOS's `aetos/git/remote.py` (the
``RemoteInfo``/``parse_remote_url`` shape + env-var token priority) and
``aetos/pm/platform.py`` (the GitHub/GitLab REST split). Reimplemented fresh
for Gleipnir -- no AETOS import.

Plan: `.gleipnir/plans/broker-mcp.md`, Assemble Step 4.
Spec/arbiter: `tests/test_broker_pm_platform.py`.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import quote as _url_quote

# ---------------------------------------------------------------------------
# RemoteInfo + URL parsing
# ---------------------------------------------------------------------------


@dataclass
class RemoteInfo:
    """Parsed git remote information."""

    host: str
    owner: str
    repo: str
    platform: str  # "github" or "gitlab"


_HTTPS_RE = re.compile(r"^https?://(?:[^@/]+@)?([^/]+)/(.+)$")
_SSH_PROTO_RE = re.compile(r"^ssh://(?:[^@]+@)?([^/:]+)(?::\d+)?/(.+)$")
_SSH_SCP_RE = re.compile(r"^(?:[^@]+@)?([^:/]+):(.+)$")


def _detect_platform(host: str) -> str:
    """Detect the platform ("github" or "gitlab") from a hostname."""
    if "github" in host.lower():
        return "github"
    return "gitlab"


def _split_owner_repo(path: str) -> tuple[str, str]:
    """Split a URL path tail into (owner, repo), handling GitLab subgroups."""
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "", ""
    repo = parts[-1]
    owner = "/".join(parts[:-1])
    return owner, repo


def parse_remote_url(url: str) -> RemoteInfo:
    """Parse a git remote URL (HTTPS, SSH, or SCP-like) into a RemoteInfo.

    Supports:
        - HTTPS: ``https://github.com/owner/repo.git``
        - SSH (scp-like): ``git@gitlab.com:owner/repo.git``
        - SSH (explicit protocol): ``ssh://git@host/owner/repo.git``
        - GitLab subgroup nesting: ``https://gitlab.com/group/subgroup/repo.git``
          (``owner`` becomes the full ``"group/subgroup"`` path)

    Args:
        url: Raw git remote URL.

    Returns:
        A ``RemoteInfo`` with the parsed fields.
    """
    url = url.strip()
    host = ""
    path = ""

    if url.startswith("http://") or url.startswith("https://"):
        match = _HTTPS_RE.match(url)
        if match:
            host, path = match.group(1), match.group(2)
    elif url.startswith("ssh://"):
        match = _SSH_PROTO_RE.match(url)
        if match:
            host, path = match.group(1), match.group(2)
    else:
        match = _SSH_SCP_RE.match(url)
        if match:
            host, path = match.group(1), match.group(2)

    owner, repo = _split_owner_repo(path) if path else ("", "")
    platform = _detect_platform(host)

    return RemoteInfo(host=host, owner=owner, repo=repo, platform=platform)


# ---------------------------------------------------------------------------
# Token resolution -- os.environ only (no python-dotenv; plan Link L2)
# ---------------------------------------------------------------------------

_TOKEN_ENV_VARS: Dict[str, str] = {
    "gitlab": "GITLAB_TOKEN",
    "github": "GITHUB_TOKEN",
}


def get_token(platform: str) -> Optional[str]:
    """Resolve the API token for ``platform`` from ``os.environ`` only."""
    env_var = _TOKEN_ENV_VARS.get(platform)
    if not env_var:
        return None
    value = os.environ.get(env_var)
    return value or None


def has_token(platform: str) -> bool:
    """Return True if an API token is configured for ``platform``."""
    return get_token(platform) is not None


# ---------------------------------------------------------------------------
# HTTP seam -- the ONE function all issue_* verbs call through.
# ---------------------------------------------------------------------------


def _http_request(
    method: str,
    url: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Perform a bounded-timeout HTTP request against a platform REST API.

    Tests monkeypatch this attribute directly so no live network is ever
    exercised in the unit-test suite.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        if "github" in url:
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["PRIVATE-TOKEN"] = token

    data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


def _no_token_error(platform: str) -> Dict[str, Any]:
    env_var = _TOKEN_ENV_VARS.get(platform, "GITLAB_TOKEN/GITHUB_TOKEN")
    return {
        "success": False,
        "error": (
            f"No API token available for platform '{platform}'. "
            f"Set the {env_var} environment variable."
        ),
    }


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------


def _api_base(remote: RemoteInfo) -> str:
    if remote.platform == "github":
        if remote.host == "github.com":
            return "https://api.github.com"
        return f"https://{remote.host}/api/v3"
    return f"https://{remote.host}/api/v4"


def _project_path(remote: RemoteInfo) -> str:
    return f"{remote.owner}/{remote.repo}" if remote.owner else remote.repo


def _issues_endpoint(remote: RemoteInfo) -> str:
    base = _api_base(remote)
    if remote.platform == "github":
        return f"{base}/repos/{_project_path(remote)}/issues"
    encoded = _url_quote(_project_path(remote), safe="")
    return f"{base}/projects/{encoded}/issues"


# ---------------------------------------------------------------------------
# issue_* verbs
# ---------------------------------------------------------------------------


def issue_create(
    remote: RemoteInfo,
    title: str,
    body: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an issue on the platform. Structured error, no crash, no
    network, if no token is configured."""
    token = get_token(remote.platform)
    if not token:
        return _no_token_error(remote.platform)

    payload: Dict[str, Any] = {"title": title}
    if body is not None:
        if remote.platform == "github":
            payload["body"] = body
        else:
            payload["description"] = body

    data = _http_request(
        "POST", _issues_endpoint(remote), token=token, json_body=payload
    )
    return {"success": True, "data": data}


def issue_update(remote: RemoteInfo, issue_id: Any, **fields: Any) -> Dict[str, Any]:
    """Update fields on an existing issue. Structured error if no token."""
    token = get_token(remote.platform)
    if not token:
        return _no_token_error(remote.platform)

    method = "PATCH" if remote.platform == "github" else "PUT"
    url = f"{_issues_endpoint(remote)}/{issue_id}"
    data = _http_request(method, url, token=token, json_body=fields)
    return {"success": True, "data": data}


def issue_comment(remote: RemoteInfo, issue_id: Any, body: str) -> Dict[str, Any]:
    """Add a comment to an issue. Structured error if no token."""
    token = get_token(remote.platform)
    if not token:
        return _no_token_error(remote.platform)

    base = _issues_endpoint(remote)
    if remote.platform == "github":
        url = f"{base}/{issue_id}/comments"
    else:
        url = f"{base}/{issue_id}/notes"

    data = _http_request("POST", url, token=token, json_body={"body": body})
    return {"success": True, "data": data}


def issue_close(remote: RemoteInfo, issue_id: Any) -> Dict[str, Any]:
    """Close an issue. Structured error if no token."""
    token = get_token(remote.platform)
    if not token:
        return _no_token_error(remote.platform)

    url = f"{_issues_endpoint(remote)}/{issue_id}"
    if remote.platform == "github":
        method, payload = "PATCH", {"state": "closed"}
    else:
        method, payload = "PUT", {"state_event": "close"}

    data = _http_request(method, url, token=token, json_body=payload)
    return {"success": True, "data": data}
