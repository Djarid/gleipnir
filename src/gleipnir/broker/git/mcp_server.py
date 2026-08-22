"""Gleipnir git broker MCP server (`gleipnir-git`).

Exposes exactly four tools: `git_status`, `git_diff` (read); `commit_changes`,
`push_current_branch` (write).

`commit_changes` runs an ALWAYS-ON secret-scan (`guards.precommit_check`,
secret-scan portion) over the staged diff before committing: on a finding it
refuses (unstages via `git reset HEAD`, never runs `git commit`); on a pass it
commits as normal, which still runs any git hooks the operator has installed.
Protected-branch refusal and data-file checks remain OPT-IN (via the
`GLEIPNIR_GIT_*` env vars below) — they are NOT part of the default gate,
because mandating a branching workflow or a hygiene rule could deadlock an
autonomous (L2/L3) operator; only genuine, hard-to-undo safety harm
(committing a live credential) blocks by default. The broker's hard
invariants are otherwise STRUCTURAL absences, enforced at the `_run_git`
choke point:

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
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from gleipnir.broker.git import guards

mcp = FastMCP(
    "gleipnir-git",
    instructions=(
        "Guardrailed git operations. git_status/git_diff are read-only. "
        "commit_changes stages, then runs an ALWAYS-ON secret-scan over the "
        "staged diff and refuses (unstaging, no commit) on a finding; "
        "protected-branch refusal and data-file checks are OPT-IN via "
        "GLEIPNIR_GIT_* env vars, not part of the default gate. "
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
# The guard screens FLAG POSITIONS, not free text: `commit_changes` builds
# argvs like `["commit", "-m", message]` where `message` is arbitrary user
# content that may legitimately *mention* "--no-verify" or "core.hooksPath"
# (e.g. a commit documenting this very guard). Scanning every token blindly
# would false-positive on that payload. So the scanner skips the value that
# immediately follows a message/file option (`-m`/`--message`/`-F`/`--file`,
# including their `=`-joined forms) before checking for bypass surfaces --
# it refuses bypass FLAGS wherever they appear, but never trips on message
# or file-content TEXT.
# ---------------------------------------------------------------------------

_HOOK_BYPASS_TOKENS = ("--no-verify", "-n")

# Options whose NEXT argv token is an opaque free-text value (never a flag):
# the commit message (`-m`/`--message`) or a message-file path (`-F`/`--file`).
# Compared CASE-SENSITIVELY (unlike the bypass-token checks below): git's
# short flags are case-sensitive and `-F` (message-file) is a different flag
# from `-f` (force) -- lowercasing here would wrongly conflate them.
_MESSAGE_VALUE_OPTIONS = ("-m", "--message", "-F", "--file")

# `=`-joined forms glue the payload onto the option token itself; skip the
# whole token rather than trying to peel the value off. Also case-sensitive.
_MESSAGE_EQUALS_PREFIXES = ("--message=", "--file=")


def _rejects_hook_bypass(args: List[str]) -> Optional[str]:
    """Return a reason string if ``args`` would bypass git hooks, else None.

    Screens flag POSITIONS only: the value following a message/file option
    (`-m`/`--message`/`-F`/`--file`, or their `=`-joined forms) is opaque
    payload and is skipped, never scanned as a potential flag.
    """
    skip_next = False
    for tok in args:
        if skip_next:
            skip_next = False
            continue
        stripped = tok.strip()
        if stripped in _MESSAGE_VALUE_OPTIONS:
            skip_next = True
            continue
        if stripped.startswith(_MESSAGE_EQUALS_PREFIXES):
            continue
        low = stripped.lower()
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
# D5 run-manifest sidecar write (Seam 8; `.gleipnir/plans/seam7-seam8-wiring.md`
# Assemble Phase 3 step 5, refined by `.gleipnir/plans/d5-sidecar-write.md`).
# After a successful commit, the broker PROCESS (not a roster agent) stamps
# the new HEAD into the framework-written, agent-read-only run manifest so
# the fresh-process advance/fetch path can correlate `(pipeline_id,
# head_sha)` for GIT->GATE. D5 CONVERGED: this is a PLAIN FILE (no own
# HMAC/digest) -- integrity comes solely from the existing
# `.gleipnir/var/run/` agent-unwritable grant class, NOT from any signature
# added here. The shape/keys/path exactly match the READ side,
# `gleipnir.preflight.advance.read_pipeline_run_identity`
# (`{"pipeline_id": <str>, "head_sha": <str>}` at
# `.gleipnir/var/run/pipeline-run.json`), which fail-closes to `None` unless
# BOTH keys are non-empty strings -- so both are written together or not at
# all.
#
# `pipeline_id` is sourced from the `GLEIPNIR_PIPELINE_ID` env var -- the SAME
# session-scoped arming convention the Phase-2 advance hook already uses
# (`.gleipnir/plugins/advance-hook.ts`, `PIPELINE_ID_ENV`), NOT an agent-facing
# tool parameter: making it a tool arg would let an agent forge the correlation
# identity the gate refuses mismatches on. When it is unset/empty (an ordinary
# non-pipeline commit, i.e. an UNARMED run) NO sidecar is written and
# `commit_changes` behaves exactly as before. The write is best-effort and
# NEVER changes `commit_changes`'s success/return contract: the commit has
# already happened, so a sidecar-write failure must not turn a successful
# commit into a reported failure (that would be a false-negative worse than a
# missing sidecar, which the read side already fail-closes on).
#
# `run_root` is an injectable keyword (mirrors `advance.py`'s own
# `run_root=` seam on `read_pipeline_run_identity`), defaulting to
# `_repo_root() / ".gleipnir" / "var" / "run"`. `commit_changes` calls this
# helper with NO `run_root` override (production default) -- the parameter
# exists purely for test isolation and adds no agent-facing surface.
# ---------------------------------------------------------------------------

_PIPELINE_ID_ENV = "GLEIPNIR_PIPELINE_ID"

# Filename + repo-root-relative directory, matching
# `gleipnir.preflight.advance` (`DEFAULT_RUN_ROOT` / `PIPELINE_RUN_FILENAME`).
_PIPELINE_RUN_FILENAME = "pipeline-run.json"
_PIPELINE_RUN_REL_DIR = Path(".gleipnir") / "var" / "run"


def _repo_root() -> Path:
    # .../src/gleipnir/broker/git/mcp_server.py -> parents[4] is the repo root.
    return Path(__file__).resolve().parents[4]


def _write_run_manifest_head_sha(
    commit_hash: str, *, run_root: Optional[Path] = None
) -> None:
    """Best-effort D5 sidecar stamp: write `{pipeline_id, head_sha}` to
    `<run_root>/pipeline-run.json` after a successful commit, ONLY when
    armed (``GLEIPNIR_PIPELINE_ID`` set and non-empty) and ``commit_hash`` is
    a non-empty string. Never raises: any failure is swallowed so a
    sidecar-write problem cannot flip an already-succeeded commit's result.
    Writes both required keys together (the read side fail-closes on a
    missing or empty either-key), plain file, no MAC (D5 CONVERGED).

    ``run_root`` is an injectable override (T1 testability seam, mirrors
    `advance.py`'s `read_pipeline_run_identity(run_root=...)`); it defaults
    to the real `.gleipnir/var/run` tree resolved from this file's own
    location. `commit_changes` never passes this argument -- it is not part
    of any agent-facing surface."""
    pipeline_id = os.environ.get(_PIPELINE_ID_ENV, "").strip()
    if not pipeline_id or not commit_hash:
        return
    try:
        root = run_root if run_root is not None else (_repo_root() / _PIPELINE_RUN_REL_DIR)
        path = root / _PIPELINE_RUN_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"pipeline_id": pipeline_id, "head_sha": commit_hash}),
            encoding="utf-8",
        )
    except OSError:
        # Fail-safe: the commit already succeeded. A missing/failed sidecar
        # write degrades to "GATE cannot yet be attempted" on the read side
        # (`read_pipeline_run_identity` -> None -> `MissingRunIdentity`),
        # which is the correct fail-closed outcome -- never a false green,
        # and never a false commit failure.
        return


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
# `commit_changes` runs an ALWAYS-ON secret-scan on the staged diff, post-stage
# and pre-commit (via `guards.precommit_check`): on a secret finding it refuses
# — no `git commit` runs, the index is unstaged (bare `git reset HEAD`), and the
# redacted finding is returned. This is the one safety-hard-to-undo check
# (committing a live credential is real harm), so it is not optional. The
# protected-branch and data-file checks remain OPT-IN via the GLEIPNIR_GIT_*
# env vars (GLEIPNIR_GIT_PROTECT_BRANCHES / GLEIPNIR_GIT_CHECK_DATA_FILES /
# GLEIPNIR_GIT_STRICT) — off by default, to avoid the false-positive/deadlock
# that an always-on hygiene gate caused. Any operator-installed git hook still
# also runs (the broker's `git commit` fires it). The broker's hard invariant:
# it will not pass a hook-bypass flag (--no-verify / -n / -c core.hooksPath),
# enforced at the `_run_git` choke point, so an agent can never skip the scan
# or the operator's hooks. The operator bypassing their own hooks via their own
# `--no-verify` alias is their call; the agent can't.
# ---------------------------------------------------------------------------


@mcp.tool()
def commit_changes(message: str, files: str = "", repo_dir: str = "") -> str:
    """Stage files, run an always-on secret-scan, and commit.

    After staging, captures the staged diff (``git diff --cached``) and runs
    ``guards.precommit_check`` — the secret-scan portion is ALWAYS ON (it is
    the only safety-hard-to-undo check: committing a live credential is real
    harm). On a secret finding this refuses: NO ``git commit`` runs, the
    index is unstaged (bare ``git reset HEAD`` — mixed reset, no pathspec,
    no ``--hard``, so working-tree content is never touched, only the
    staged-content of a bare index-wide unstage), and the (redacted) finding
    is returned. On a pass, proceeds to a plain ``git commit`` exactly as
    before — which still runs any git hooks the operator has installed. The
    broker never passes ``--no-verify``, so it cannot bypass those hooks; a
    hook rejection surfaces as a normal commit failure in the returned error.

    Protected-branch refusal and data-file checks (also part of
    ``guards.precommit_check``) remain OPT-IN — via ``GLEIPNIR_GIT_STRICT`` /
    ``GLEIPNIR_GIT_PROTECT_BRANCHES`` / ``GLEIPNIR_GIT_CHECK_DATA_FILES`` —
    and are NOT evaluated by default here, so a trunk-based / autonomous
    (L2/L3) operator is never refused on branch alone.

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

    # Always-on safety gate: secret-scan the staged diff BEFORE committing.
    # This is the only window where `git diff --cached` reflects exactly what
    # is about to be committed (post-stage, pre-commit).
    diff_result = _run_git(["diff", "--cached"], rd)
    if not diff_result.get("success"):
        # Fail-closed: never commit when the scan itself could not run.
        return json.dumps(
            {
                "success": False,
                "error": "Failed to read staged diff for secret-scan: "
                + (
                    diff_result.get("stderr", "").strip()
                    or diff_result.get("error", "")
                ),
            }
        )

    names_result = _run_git(["diff", "--cached", "--name-only"], rd)
    staged_files = (
        [n for n in names_result["stdout"].splitlines() if n]
        if names_result.get("success")
        else []
    )

    check = guards.precommit_check(branch, diff_result["stdout"], staged_files)
    if not check["passed"]:
        # Refuse: never commit. Unstage via a bare `git reset HEAD` (mixed
        # reset, no pathspec, no --hard) -- index-wide but working-tree-safe.
        _run_git(["reset", "HEAD"], rd)
        return json.dumps(
            {
                "success": False,
                "error": check.get("error") or "Pre-commit secret-scan failed",
                "secrets": check.get("secrets", []),
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

    # D5 (Seam 8): stamp the new HEAD into the run-manifest sidecar as a
    # best-effort side effect of this commit -- armed runs only, never alters
    # the return contract below. See `_write_run_manifest_head_sha`.
    _write_run_manifest_head_sha(commit_hash)

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
