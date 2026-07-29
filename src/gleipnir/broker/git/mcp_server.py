"""Gleipnir git broker MCP server (`gleipnir-git`).

Exposes exactly four tools: `git_status`, `git_diff` (read); `commit_changes`,
`push_current_branch` (write).

The broker imposes NO commit policy of its own — secret-scan / branch / data-
file checks belong in git hooks the operator installs, not in the framework.
`commit_changes` runs a plain `git commit`, which runs those hooks. The broker's
hard invariants are STRUCTURAL absences, enforced at the `_run_git` choke point:

  - **No force-push:** no tool exposes a force parameter; ``--force``/``-f``
    never appear in any argv (see `tests/test_broker_tool_surface.py`, T-A).
  - **No hook bypass:** ``--no-verify``/``-n``/``-c core.hooksPath`` are refused
    by `_run_git`, so an agent can never skip the operator's hooks (that would
    be a Tier-3/G-2 capability-escape). The operator's own `--no-verify` alias
    is the operator's call; the agent has no path to it.

`guards` is retained only for the ADVISORY `protected` field in `git_status`
(a report, never a block); protected-branch/secret/data-file are opt-in there.

Run as: ``python -m gleipnir.broker.git.mcp_server``

Configuration:
    GLEIPNIR_GIT_PROTECTED_BRANCHES -- comma-separated (default: main,master)

Plan: `.gleipnir/plans/broker-mcp.md`, Assemble Step 4.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from gleipnir.broker.git import guards

mcp = FastMCP(
    "gleipnir-git",
    instructions=(
        "Guardrailed git operations. git_status/git_diff are read-only. "
        "commit_changes stages and commits with a structural pre-commit "
        "gate (protected-branch refusal + secret-scan + data-file check). "
        "push_current_branch pushes the current branch -- no force-push "
        "path exists anywhere in this server."
    ),
)


# ---------------------------------------------------------------------------
# The ONE hard invariant: the broker may never bypass git hooks.
#
# Guard *policy* (secret-scan, branch protection, data-file hygiene) is NOT the
# broker's job — it belongs in git hooks the operator installs (bypassable by
# the operator's own `--no-verify`; that's on them). But an agent operating the
# broker must NOT be able to bypass those hooks, because a hook is where the
# operator may put Tier-3-relevant enforcement. Skipping it would be a G-2
# capability-escape. So every argv this broker runs is screened at this single
# choke point for hook-bypass surfaces, which are refused STRUCTURALLY:
#   - `--no-verify` / `-n`  (commit & push: skip pre-commit/pre-push hooks)
#   - `-c core.hooksPath=…`  (redirect hooks away, incl. to /dev/null)
#   - `--no-verify` folded into `=` forms
# This is not a heuristic that can false-positive on user content: the broker
# constructs all its own argvs from constants, so a match here can only mean a
# bypass attempt, never legitimate payload.
# ---------------------------------------------------------------------------

_HOOK_BYPASS_TOKENS = ("--no-verify", "-n")


def _rejects_hook_bypass(args: List[str]) -> Optional[str]:
    """Return a reason string if ``args`` would bypass git hooks, else None."""
    for tok in args:
        low = tok.strip().lower()
        if low in _HOOK_BYPASS_TOKENS or low.startswith("--no-verify"):
            return f"refused: '{tok}' would bypass git hooks (not permitted)"
        # `-c core.hooksPath=...` (or `--config`) redirecting/disabling hooks.
        if low.startswith("core.hookspath") or "core.hookspath=" in low:
            return f"refused: '{tok}' would redirect/disable git hooks (not permitted)"
    return None


def _run_git(
    args: List[str],
    repo_dir: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Run a git command and return a structured result.

    No force flags and no hook-bypass flags are ever passed by any caller in
    this module; this choke point ALSO refuses them defensively so no present
    or future tool can inject one (the one hard broker invariant — see the
    module comment above). Guard policy otherwise lives in git hooks, not here.
    """
    bypass = _rejects_hook_bypass(args)
    if bypass is not None:
        return {"success": False, "error": bypass}
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=repo_dir,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"git command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "error": "git executable not found"}
    except Exception as exc:  # noqa: BLE001 -- structured error, never crash
        return {"success": False, "error": str(exc)}


def _current_branch(repo_dir: Optional[str] = None) -> str:
    result = _run_git(["branch", "--show-current"], repo_dir)
    if result.get("success"):
        return result["stdout"].strip()
    return ""


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------


@mcp.tool()
def git_status(repo_dir: str = "") -> str:
    """Get repository status: branch, protection, and staged/unstaged/untracked files.

    Args:
        repo_dir: Working directory for the git command. Defaults to cwd.
    """
    rd = repo_dir or None
    branch = _current_branch(rd)

    porcelain = _run_git(["status", "--porcelain"], rd)
    staged: List[str] = []
    unstaged: List[str] = []
    untracked: List[str] = []

    if porcelain.get("success"):
        for line in porcelain["stdout"].rstrip("\n").split("\n"):
            if not line or len(line) < 4:
                continue
            index_status, work_status, filepath = line[0], line[1], line[3:]
            if index_status == "?":
                untracked.append(filepath)
                continue
            if index_status not in (" ", "?"):
                staged.append(filepath)
            if work_status not in (" ", "?"):
                unstaged.append(filepath)

    result = {
        "success": True,
        "branch": branch,
        "protected": guards.is_protected_branch(branch),
        "clean": not (staged or unstaged or untracked),
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
    }
    return json.dumps(result)


@mcp.tool()
def git_diff(
    staged: bool = False,
    target: str = "",
    file: str = "",
    repo_dir: str = "",
) -> str:
    """Get diff output (unstaged changes by default).

    Args:
        staged: Show staged changes (``--cached``) instead of unstaged.
        target: Compare against a target branch/ref (e.g. "main").
        file: Show the diff for one file only.
        repo_dir: Working directory for the git command. Defaults to cwd.
    """
    rd = repo_dir or None
    args = ["diff"]
    if staged:
        args.append("--cached")
    if target:
        args.append(target)
    if file:
        args.extend(["--", file])

    result = _run_git(args, rd)
    if not result.get("success"):
        return json.dumps(
            {"success": False, "error": result.get("error") or result.get("stderr", "")}
        )
    return json.dumps({"success": True, "diff": result["stdout"]})


# ---------------------------------------------------------------------------
# Write tools
#
# The broker imposes NO commit policy of its own. Secret-scan / branch /
# data-file checks are NOT the broker's job — they belong in git hooks the
# operator installs (see `hooks/pre-commit.sample` and the decision record).
# `commit_changes` runs a plain `git commit`, which runs whatever hooks the
# operator has installed. If a hook rejects the commit, that surfaces as an
# ordinary git failure. The broker's ONLY hard invariant is that it will not
# pass a hook-bypass flag (--no-verify / -n / -c core.hooksPath) — enforced at
# the `_run_git` choke point — so an agent can never skip the operator's hooks
# (that would be a Tier-3/G-2 capability-escape). The operator bypassing their
# own hooks via their own `--no-verify` alias is their call; the agent can't.
# ---------------------------------------------------------------------------


@mcp.tool()
def commit_changes(message: str, files: str = "", repo_dir: str = "") -> str:
    """Stage files and commit.

    Runs a plain ``git commit`` — which runs any git hooks the operator has
    installed (e.g. a `pre-commit` hook doing secret/branch/data-file checks).
    The broker adds NO policy gate of its own and never passes ``--no-verify``,
    so it cannot bypass those hooks. A hook rejection surfaces as a normal
    commit failure in the returned error.

    Args:
        message: Commit message.
        files: Comma-separated file paths to stage. Empty stages all changes
            (``git add -A``).
        repo_dir: Working directory for the git command. Defaults to cwd.
    """
    rd = repo_dir or None
    branch = _current_branch(rd)

    if files:
        file_list = [f.strip() for f in files.split(",") if f.strip()]
        for f in file_list:
            stage_result = _run_git(["add", f], rd)
            if not stage_result.get("success"):
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Failed to stage '{f}': "
                        f"{stage_result.get('stderr', '').strip()}",
                    }
                )
    else:
        stage_result = _run_git(["add", "-A"], rd)
        if not stage_result.get("success"):
            return json.dumps(
                {
                    "success": False,
                    "error": f"Failed to stage: {stage_result.get('stderr', '').strip()}",
                }
            )

    commit_result = _run_git(["commit", "-m", message], rd)
    if not commit_result.get("success"):
        # This includes a hook rejection (e.g. an operator pre-commit hook).
        return json.dumps(
            {
                "success": False,
                "error": commit_result.get("stderr", "").strip()
                or commit_result.get("error", "Commit failed"),
            }
        )

    hash_result = _run_git(["rev-parse", "HEAD"], rd)
    commit_hash = hash_result["stdout"].strip() if hash_result.get("success") else ""

    return json.dumps(
        {
            "success": True,
            "hash": commit_hash,
            "message": message,
            "branch": branch,
        }
    )


@mcp.tool()
def push_current_branch(repo_dir: str = "") -> str:
    """Push the current branch to origin.

    Constructs ONLY ``["push", "origin", branch]`` and, if that fails (e.g.
    no upstream tracking configured), a ``["push", "-u", "origin", branch]``
    retry. No force parameter exists on this tool and no argv in this
    module ever includes ``--force``/``-f`` -- force-push cannot be
    expressed via this server.

    Args:
        repo_dir: Working directory for the git command. Defaults to cwd.
    """
    rd = repo_dir or None
    branch = _current_branch(rd)
    if not branch:
        return json.dumps(
            {"success": False, "error": "Could not determine current branch"}
        )

    result = _run_git(["push", "origin", branch], rd, timeout=60)
    if not result.get("success"):
        result = _run_git(["push", "-u", "origin", branch], rd, timeout=60)

    if not result.get("success"):
        return json.dumps(
            {
                "success": False,
                "error": result.get("stderr", "").strip()
                or result.get("error", "push failed"),
            }
        )

    return json.dumps({"success": True, "branch": branch})


if __name__ == "__main__":
    mcp.run(transport="stdio")
