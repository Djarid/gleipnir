"""Gleipnir PM broker MCP server (`gleipnir-pm`).

Exposes exactly nine tools: the four issue verbs `issue_create`,
`issue_update`, `issue_comment`, `issue_close`, plus the five PR/MR
lifecycle verbs `pr_create`, `pr_update`, `pr_comment`, `pr_merge`,
`pr_close`. Stateless -- no local cache; every call re-detects the origin
remote and delegates to `platform.py` for the actual REST call. Returns a
structured error (never raises) when no platform token is configured.
`pr_merge` is a plain merge only -- it exposes no force/admin-override
argument (P3).

Run as: ``python -m gleipnir.broker.pm.mcp_server``

Configuration:
    GITLAB_TOKEN / GITHUB_TOKEN -- platform API token (env-injected by
        opencode; no python-dotenv, see plan Link L2).

Plan: `.gleipnir/plans/broker-mcp.md` (issue_* verbs); PR/MR verbs added by
`.gleipnir/plans/pr-create-broker.md`, Assemble Step 4.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from gleipnir.broker.pm import platform

mcp = FastMCP(
    "gleipnir-pm",
    instructions=(
        "Stateless issue-tracker and PR/MR operations against the platform "
        "(GitHub or GitLab) detected from the current repo's origin remote. "
        "issue_create/issue_update/issue_comment/issue_close plus "
        "pr_create/pr_update/pr_comment/pr_merge/pr_close are the only nine "
        "tools; no milestones/time-tracking/labels beyond these verbs. "
        "pr_merge is a plain merge only -- it exposes no force/admin-override "
        "argument; branch-protection safety is structural, not a denied "
        "flag. Returns a structured error, never a crash, when no "
        "GITLAB_TOKEN/GITHUB_TOKEN is configured."
    ),
)


def _detect_remote(repo_dir: str = "") -> platform.RemoteInfo:
    """Detect and parse the origin remote URL for the given repo directory."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_dir or None,
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced as a structured error
        raise RuntimeError(f"Could not run git: {exc}") from exc

    if result.returncode != 0:
        raise RuntimeError("Could not determine the origin remote URL")

    return platform.parse_remote_url(result.stdout.strip())


def _remote_or_error(repo_dir: str) -> Dict[str, Any]:
    """Return {"remote": RemoteInfo} or {"error": {...}} -- never raises."""
    try:
        return {"remote": _detect_remote(repo_dir)}
    except RuntimeError as exc:
        return {"error": {"success": False, "error": str(exc)}}


@mcp.tool()
def issue_create(title: str, body: str = "", repo_dir: str = "") -> str:
    """Create an issue on the platform detected from the origin remote.

    Args:
        title: Issue title.
        body: Issue body/description (markdown supported).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.issue_create(resolved["remote"], title, body or None)
    return json.dumps(result, default=str)


@mcp.tool()
def issue_update(
    issue_id: str,
    title: str = "",
    body: str = "",
    state: str = "",
    repo_dir: str = "",
) -> str:
    """Update fields on an existing issue.

    Args:
        issue_id: Issue IID (GitLab) or number (GitHub).
        title: New title (omit to leave unchanged).
        body: New body/description (omit to leave unchanged).
        state: New state, e.g. "closed"/"opened" (omit to leave unchanged).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])

    fields: Dict[str, Any] = {}
    if title:
        fields["title"] = title
    if body:
        fields["body"] = body
    if state:
        fields["state"] = state

    result = platform.issue_update(resolved["remote"], issue_id, **fields)
    return json.dumps(result, default=str)


@mcp.tool()
def issue_comment(issue_id: str, body: str, repo_dir: str = "") -> str:
    """Add a comment to an issue.

    Args:
        issue_id: Issue IID (GitLab) or number (GitHub).
        body: Comment body (markdown supported).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.issue_comment(resolved["remote"], issue_id, body)
    return json.dumps(result, default=str)


@mcp.tool()
def issue_close(issue_id: str, repo_dir: str = "") -> str:
    """Close an issue.

    Args:
        issue_id: Issue IID (GitLab) or number (GitHub).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.issue_close(resolved["remote"], issue_id)
    return json.dumps(result, default=str)


@mcp.tool()
def pr_create(title: str, head: str, base: str, body: str = "", repo_dir: str = "") -> str:
    """Create a PR (GitHub) or MR (GitLab) on the platform detected from the
    origin remote. `head`/`base` are REQUIRED -- a PR target is never
    guessed (P2): there is no default branch and no auto-detection of the
    current branch.

    Args:
        title: PR/MR title.
        head: Source branch (GitHub "head" / GitLab "source_branch").
        base: Target branch (GitHub "base" / GitLab "target_branch").
        body: PR/MR body/description (markdown supported).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.pr_create(resolved["remote"], title, head, base, body or None)
    return json.dumps(result, default=str)


@mcp.tool()
def pr_update(
    pr_id: str,
    title: str = "",
    body: str = "",
    state: str = "",
    repo_dir: str = "",
) -> str:
    """Update fields on an existing PR/MR.

    Args:
        pr_id: PR number (GitHub) or MR IID (GitLab).
        title: New title (omit to leave unchanged).
        body: New body/description (omit to leave unchanged).
        state: New state, e.g. "closed"/"open" (omit to leave unchanged).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])

    fields: Dict[str, Any] = {}
    if title:
        fields["title"] = title
    if body:
        fields["body"] = body
    if state:
        fields["state"] = state

    result = platform.pr_update(resolved["remote"], pr_id, **fields)
    return json.dumps(result, default=str)


@mcp.tool()
def pr_comment(pr_id: str, body: str, repo_dir: str = "") -> str:
    """Add a comment to a PR/MR.

    Args:
        pr_id: PR number (GitHub) or MR IID (GitLab).
        body: Comment body (markdown supported).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.pr_comment(resolved["remote"], pr_id, body)
    return json.dumps(result, default=str)


@mcp.tool()
def pr_merge(pr_id: str, repo_dir: str = "") -> str:
    """Merge a PR/MR. Plain merge only -- there is NO force/admin-override
    argument (P3); branch-protection safety is structural, not a denied
    flag.

    Args:
        pr_id: PR number (GitHub) or MR IID (GitLab).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.pr_merge(resolved["remote"], pr_id)
    return json.dumps(result, default=str)


@mcp.tool()
def pr_close(pr_id: str, repo_dir: str = "") -> str:
    """Close a PR/MR.

    Args:
        pr_id: PR number (GitHub) or MR IID (GitLab).
        repo_dir: Working directory used to detect the origin remote.
    """
    resolved = _remote_or_error(repo_dir)
    if "error" in resolved:
        return json.dumps(resolved["error"])
    result = platform.pr_close(resolved["remote"], pr_id)
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run(transport="stdio")
