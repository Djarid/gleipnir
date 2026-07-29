"""Gleipnir git broker -- pre-commit safety guards.

stdlib-only (`os`, `re`) so this module stays unit-testable without the
`mcp` SDK installed (see `tests/test_broker_stdlib_only.py`). No git
invocations happen here -- this module only evaluates branch names and diff
text handed to it; the actual `git` subprocess calls for the broker's write
path live in `mcp_server.py`.

Influenced by (pattern, not code) AETOS's `aetos/git/guards.py`:
`is_protected_branch`, `SECRET_PATTERNS` + `scan_diff_for_secrets`, and a
combined pre-commit gate. Reimplemented fresh for Gleipnir, reading
`GLEIPNIR_GIT_PROTECTED_BRANCHES` instead of AETOS's env var name.

Plan: `.gleipnir/plans/broker-mcp.md`, Assemble Step 3, Stress-test T-B/T-C.
Spec/arbiter: `tests/test_broker_git_guards.py`.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Branch protection
#
# WORKFLOW POLICY, NOT A SAFETY INVARIANT — OPT-IN, DEFAULT OFF.
#
# Refusing to commit directly to main/master enforces a *branching workflow*
# (GitHub Flow / feature branches). That is a workflow preference, not a safety
# property: committing to main is not inherently dangerous the way a force-push,
# a committed secret, or a committed data artifact is. Baking a mandatory
# branching style into the broker would brick legitimate trunk-based workflows —
# and, critically, would DEADLOCK an autonomous (L2/L3) operator that has no
# human to answer a "switch off the protected branch" prompt.
#
# So branch protection is DISABLED by default. The operator opts in by setting
# GLEIPNIR_GIT_PROTECT_BRANCHES to a truthy value. Only then does the
# GLEIPNIR_GIT_PROTECTED_BRANCHES list (default main,master) take effect. The
# genuine safety checks (secret-scan, data-file) always run regardless.
# ---------------------------------------------------------------------------

_DEFAULT_PROTECTED_BRANCHES = "main,master"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def strict_mode() -> bool:
    """Whether the broker is in STRICT mode (default: False = non-strict).

    Reads ``GLEIPNIR_GIT_STRICT``. In non-strict mode the git broker constrains
    almost nothing beyond genuine safety: the ONLY always-on commit check is the
    secret-scan (committing a live credential is real, hard-to-undo harm). The
    opinionated/hygiene checks — data-file detection and protected-branch
    refusal — are OFF unless the operator opts into strict mode (or enables them
    individually). This exists so the broker is nearly invisible in normal use;
    a broker that nags more than it helps just gets routed around, and then the
    real safety value (secret-scan, structural force-push absence) is lost too.
    """
    return os.environ.get("GLEIPNIR_GIT_STRICT", "").strip().lower() in _TRUTHY


def branch_protection_enabled() -> bool:
    """Whether protected-branch refusal is active (default: False).

    Enabled by EITHER the dedicated ``GLEIPNIR_GIT_PROTECT_BRANCHES`` toggle OR
    strict mode (``GLEIPNIR_GIT_STRICT``). Off otherwise — committing to
    main/master is a workflow choice the operator owns, not a safety invariant,
    and a hard refusal would deadlock an autonomous (L2/L3) operator.
    """
    if strict_mode():
        return True
    return os.environ.get("GLEIPNIR_GIT_PROTECT_BRANCHES", "").strip().lower() in _TRUTHY


def data_file_check_enabled() -> bool:
    """Whether staged-data-file refusal is active (default: False).

    On only in strict mode (or via ``GLEIPNIR_GIT_CHECK_DATA_FILES``). Committing
    a ``.sqlite``/``.db`` is messy, not dangerous — hygiene, not safety — so it
    is off in non-strict mode. (A committed ``.env`` can leak secrets, but that
    overlaps the always-on secret-scan of the diff content.)
    """
    if strict_mode():
        return True
    return os.environ.get("GLEIPNIR_GIT_CHECK_DATA_FILES", "").strip().lower() in _TRUTHY


def get_protected_branches() -> List[str]:
    """Return the configured protected-branch names (the list that is consulted
    only when :func:`branch_protection_enabled` is True).

    Reads ``GLEIPNIR_GIT_PROTECTED_BRANCHES`` (comma-separated env var),
    defaulting to ``["main", "master"]`` when unset.
    """
    env = os.environ.get(
        "GLEIPNIR_GIT_PROTECTED_BRANCHES", _DEFAULT_PROTECTED_BRANCHES
    )
    return [b.strip() for b in env.split(",") if b.strip()]


def is_protected_branch(branch: str) -> bool:
    """Return True if branch protection is ENABLED *and* ``branch`` is in the
    configured protected list.

    Returns False when protection is not opted in (the default) — so
    trunk-based / autonomous operators are never refused on branch alone.
    """
    if not branch_protection_enabled():
        return False
    return branch.strip() in get_protected_branches()


# ---------------------------------------------------------------------------
# Secrets scanning
# ---------------------------------------------------------------------------

# (pattern, description) pairs -- pattern may be a raw regex string.
SECRET_PATTERNS: List[Tuple[str, str]] = [
    (r"xoxb-[0-9A-Za-z\-]{10,}", "Slack bot token"),
    (r"xoxp-[0-9A-Za-z\-]{10,}", "Slack user token"),
    (r"xoxs-[0-9A-Za-z\-]{10,}", "Slack session token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key ID"),
    (
        r"-----BEGIN\s+(?:RSA\s+|DSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----",
        "Private key",
    ),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth token"),
    (r"ghs_[a-zA-Z0-9]{36}", "GitHub server-to-server token"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab personal access token"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"ya29\.[0-9A-Za-z\-_]+", "Google OAuth token"),
    (
        r"['\"]?password['\"]?\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "Hardcoded password",
    ),
]

_COMPILED_PATTERNS = [(re.compile(p), desc) for p, desc in SECRET_PATTERNS]


def _redact(matched_text: str) -> str:
    """Redact a matched secret so the full value never appears verbatim."""
    if len(matched_text) > 12:
        return matched_text[:6] + "..." + matched_text[-4:]
    return "***"


def scan_diff_for_secrets(diff_text: str) -> List[Dict[str, Any]]:
    """Scan a unified diff for secret patterns on "+"-added lines only.

    The ``+++`` file header, the ``---`` header, the ``diff --git`` line,
    and unchanged (leading-space) context lines are never scanned -- only
    lines that begin with a single ``+`` (an added line).

    Args:
        diff_text: Unified diff text (e.g. ``git diff --cached`` output).

    Returns:
        A list of findings, each a dict with keys ``file``, ``line``,
        ``description``, ``match`` -- ``match`` is REDACTED; the full
        secret never appears verbatim in a finding.
    """
    findings: List[Dict[str, Any]] = []
    current_file = ""
    line_no = 0

    for line in diff_text.split("\n"):
        if line.startswith("+++"):
            rest = line[len("+++") :].strip()
            if rest.startswith("b/"):
                rest = rest[2:]
            current_file = rest.split()[0] if rest else ""
            line_no = 0
            continue
        if line.startswith("---"):
            continue
        if line.startswith("diff --git"):
            continue
        if line.startswith("@@"):
            hunk_match = re.search(r"\+(\d+)", line)
            if hunk_match:
                line_no = int(hunk_match.group(1)) - 1
            continue

        if line.startswith("+"):
            line_no += 1
            content = line[1:]
            for pattern, description in _COMPILED_PATTERNS:
                match = pattern.search(content)
                if match:
                    findings.append(
                        {
                            "file": current_file,
                            "line": line_no,
                            "description": description,
                            "match": _redact(match.group(0)),
                        }
                    )
        elif not line.startswith("-"):
            line_no += 1

    return findings


# ---------------------------------------------------------------------------
# Data file detection
# ---------------------------------------------------------------------------

_DATA_FILE_EXTENSIONS = (".db", ".sqlite", ".sqlite3")


def check_staged_data_files(staged_files: Sequence[str]) -> List[str]:
    """Flag ``.db``/``.sqlite``/``.env``/``venv/`` artifacts among staged paths.

    Args:
        staged_files: Paths staged for commit (as returned by
            ``git diff --cached --name-only``).

    Returns:
        The subset of ``staged_files`` that look like data/artifact files.
    """
    flagged: List[str] = []
    for filepath in staged_files:
        basename = filepath.rsplit("/", 1)[-1]

        if basename == ".env" or basename.startswith(".env."):
            flagged.append(filepath)
            continue

        if filepath.endswith(_DATA_FILE_EXTENSIONS):
            flagged.append(filepath)
            continue

        if (
            filepath.startswith("venv/")
            or "/venv/" in filepath
            or filepath.startswith(".venv/")
            or "/.venv/" in filepath
        ):
            flagged.append(filepath)
            continue

    return flagged


# ---------------------------------------------------------------------------
# Combined pre-commit gate
# ---------------------------------------------------------------------------


def precommit_check(
    branch: str,
    diff: str,
    staged_files: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Run the combined pre-commit gate.

    **Non-strict (default): the ONLY blocking check is the secret-scan.** The
    diff is ALWAYS scanned for secrets (committing a live credential is genuine,
    hard-to-undo harm — this is the check that makes the broker worth using).
    Protected-branch refusal and data-file detection are OFF unless opted in
    (see :func:`branch_protection_enabled` / :func:`data_file_check_enabled` /
    :func:`strict_mode`), because mandating a branching workflow or committing
    hygiene is a preference, not a safety invariant — and a broker that nags
    more than it protects just gets bypassed, losing the safety value too.

    ``passed`` is False if a secret is present, OR (only when enabled) the branch
    is protected, OR (only when enabled) a staged file is a data/artifact file.

    Args:
        branch: Current branch name.
        diff: Staged diff text to scan for secrets.
        staged_files: Staged file paths to check for data/artifact files.

    Returns:
        A dict with ``passed`` plus supporting detail (``protected_branch``,
        ``secrets``, ``data_files``, ``strict``).
    """
    staged_files = list(staged_files) if staged_files is not None else []

    # Always-on safety check.
    secrets = scan_diff_for_secrets(diff)

    # Opt-in / strict-only checks.
    protected = is_protected_branch(branch)  # already returns False unless enabled
    data_files = (
        check_staged_data_files(staged_files) if data_file_check_enabled() else []
    )

    passed = not secrets and not protected and not data_files

    error = None
    if secrets:
        error = f"Found {len(secrets)} potential secret(s) in staged changes"
    elif protected:
        error = f"Cannot commit on protected branch '{branch}'"
    elif data_files:
        error = f"Found {len(data_files)} data/artifact file(s) staged"

    return {
        "passed": passed,
        "branch": branch,
        "protected_branch": protected,
        "secrets": secrets,
        "data_files": data_files,
        "strict": strict_mode(),
        "error": error,
    }
