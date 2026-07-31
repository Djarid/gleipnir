"""Broker commit-guard tests (T1-T5) for `commit_changes` secret-scan wire-in.

Plan: `.gleipnir/plans/git-enforcement-plugin.md`, Assemble step 1 / Stress-test
"Broker commit-guard tests". Target behaviour (does NOT exist yet -- this is
the point, Axiom 1): `commit_changes` in
`src/gleipnir/broker/git/mcp_server.py` must, after staging and BEFORE
`git commit`, capture `git diff --cached`, run
`guards.precommit_check(branch, diff, staged_files)`, and on a secret finding
refuse (`git reset HEAD`, no commit) instead of the TODAY behaviour (plain
`git add` then `git commit`, no guard at all).

These tests drive the REAL `commit_changes` tool function directly against a
temp git repo (create with `git init`, configure `user.email`/`user.name`,
write files, call the tool function -- it returns a JSON string). This
mirrors the plan's own description of how to drive it, and the
`AKIA_SECRET` shape reused verbatim from `tests/test_broker_git_guards.py`
(`"AKIA" + "Q7X9" * 4`) so the planted secret is guaranteed to match
`guards.SECRET_PATTERNS` (an AWS-access-key-ID shape) rather than a guessed,
possibly non-matching, fake.

Runs under the **broker profile** (imports `mcp` transitively via
`mcp_server`) -- see `tests/conftest.py` `collect_ignore` and the plan's D8 /
Assemble step 0 (the `profiles.toml` amendment needed for
`bin/gleipnir-sandbox test` to actually collect this file is an OPERATOR,
Tier-3 action, not performed by this delegation).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest

from gleipnir.broker.git import mcp_server


# ---------------------------------------------------------------------------
# Planted fake secret -- SAME shape as tests/test_broker_git_guards.py so it
# is guaranteed to match `guards.SECRET_PATTERNS` (AWS access key ID), not a
# guessed pattern that might not actually trip the scanner.
# guards.py L122: (r"AKIA[0-9A-Z]{16}", "AWS access key ID")
# ---------------------------------------------------------------------------

AKIA_SECRET = "AKIA" + ("Q7X9" * 4)  # AKIA + 16 upper/digit chars
assert len(AKIA_SECRET) == 20 and AKIA_SECRET[:4] == "AKIA"

_GIT_ENV_VARS = (
    "GLEIPNIR_GIT_STRICT",
    "GLEIPNIR_GIT_PROTECT_BRANCHES",
    "GLEIPNIR_GIT_CHECK_DATA_FILES",
    "GLEIPNIR_GIT_PROTECTED_BRANCHES",
)


def _clear_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset every opt-in broker toggle so tests exercise the DEFAULT posture
    (safety-only secret-scan; branch/data-file checks off) -- T4's premise."""
    for var in _GIT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(args: List[str], cwd: str) -> str:
    """Run a real `git` command for test setup/verification (NOT the broker).

    Raises via assert on failure so a broken fixture fails loudly instead of
    masquerading as a broker-guard failure.
    """
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


def _rev_parse_head(repo_dir: str) -> str:
    return _git(["rev-parse", "HEAD"], repo_dir).strip()


def _staged_names(repo_dir: str) -> List[str]:
    out = _git(["diff", "--cached", "--name-only"], repo_dir)
    return [line for line in out.splitlines() if line]


def _porcelain(repo_dir: str) -> str:
    return _git(["status", "--porcelain"], repo_dir)


@pytest.fixture
def repo(tmp_path: Path) -> str:
    """A real temp git repo, branch `main`, with one prior commit so HEAD
    exists before any `commit_changes` call under test."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    rd = str(repo_dir)
    _git(["init"], rd)
    # Force the branch name to `main` regardless of the host's
    # `init.defaultBranch` config, WITHOUT relying on `git init -b` (a
    # newer-git-only flag) -- `symbolic-ref` has existed forever and is safe
    # to run before the first commit.
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], rd)
    _git(["config", "user.email", "gleipnir-test@example.invalid"], rd)
    _git(["config", "user.name", "Gleipnir Test"], rd)
    (repo_dir / "README.md").write_text("initial\n")
    _git(["add", "README.md"], rd)
    _git(["commit", "-m", "initial commit"], rd)
    return rd


def _call_commit_changes(
    message: str, files: str = "", repo_dir: str = ""
) -> dict:
    """Invoke the real broker tool function directly and parse its JSON.

    `commit_changes` is a plain, directly-callable function decorated with
    `@mcp.tool()` (the FastMCP decorator registers it but returns the
    original function, per the plan's own driving instructions for this test
    file); it is NOT invoked through the MCP wire protocol here.
    """
    raw = mcp_server.commit_changes(message=message, files=files, repo_dir=repo_dir)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# T1 -- refuses on a secret in the staged diff.
# ---------------------------------------------------------------------------


class TestT1RefusesOnSecretInStagedDiff:
    def test_refuses_reports_finding_redacted_and_leaves_head_unchanged(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        head_before = _rev_parse_head(repo)

        secret_file = Path(repo) / "config.py"
        secret_file.write_text(f'API_KEY = "{AKIA_SECRET}"\n')

        raw = mcp_server.commit_changes(
            message="add config", files="config.py", repo_dir=repo
        )
        result = json.loads(raw)

        # Refused.
        assert result.get("success") is False, result

        # The error names a secret finding.
        assert "secret" in json.dumps(result).lower(), result

        # Redaction: the full secret must NEVER appear verbatim anywhere in
        # the returned payload, regardless of which key holds the finding.
        assert AKIA_SECRET not in raw, (
            f"unredacted secret leaked into broker response: {raw!r}"
        )

        # No commit was created.
        assert _rev_parse_head(repo) == head_before, (
            "HEAD must be unchanged when commit_changes refuses on a secret"
        )


# ---------------------------------------------------------------------------
# T2 -- passes on a clean staged diff.
# ---------------------------------------------------------------------------


class TestT2PassesOnCleanDiff:
    def test_clean_diff_creates_a_commit_and_advances_head(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        head_before = _rev_parse_head(repo)

        benign_file = Path(repo) / "notes.txt"
        benign_file.write_text("just some ordinary notes\n")

        result = _call_commit_changes(
            message="add notes", files="notes.txt", repo_dir=repo
        )

        assert result.get("success") is True, result
        head_after = _rev_parse_head(repo)
        assert head_after != head_before, "HEAD must advance on a successful commit"
        assert result.get("hash") == head_after, (
            "returned hash must match the new HEAD"
        )


# ---------------------------------------------------------------------------
# T3 -- reset-HEAD-on-refusal safety: unstages but never loses working-tree
# content, and the unstage is index-wide (bare `git reset HEAD`), not scoped
# to only this call's files.
# ---------------------------------------------------------------------------


class TestT3ResetHeadOnRefusalSafety:
    def test_secret_file_unstaged_but_content_survives_on_disk(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)

        secret_file = Path(repo) / "secret.py"
        secret_content = f'TOKEN = "{AKIA_SECRET}"\n'
        secret_file.write_text(secret_content)

        result = _call_commit_changes(
            message="add secret", files="secret.py", repo_dir=repo
        )
        assert result.get("success") is False, result

        # Working tree: the file is still there, with its content intact.
        assert secret_file.exists(), "reset HEAD must never delete working-tree files"
        assert secret_file.read_text() == secret_content, (
            "reset HEAD must never modify working-tree content (no --hard)"
        )

        # Index: no longer staged.
        assert "secret.py" not in _staged_names(repo)
        assert "?? secret.py" in _porcelain(repo).splitlines() or any(
            "secret.py" in line for line in _porcelain(repo).splitlines()
        )

    def test_reset_head_is_index_wide_a_pre_staged_second_file_is_also_unstaged(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        """Documents the caveat from the plan's edge case 3: a bare
        `git reset HEAD` clears the WHOLE index, not just the files THIS
        `commit_changes` call staged. Pre-stage a second, unrelated, benign
        file directly (bypassing the broker) BEFORE calling `commit_changes`
        for the secret file, then assert the second file is unstaged too --
        while its content also survives untouched on disk."""
        _clear_git_env(monkeypatch)

        other_file = Path(repo) / "other.txt"
        other_content = "pre-staged unrelated content\n"
        other_file.write_text(other_content)
        _git(["add", "other.txt"], repo)
        assert "other.txt" in _staged_names(repo)  # sanity: pre-staged before the call

        secret_file = Path(repo) / "secret.py"
        secret_content = f'TOKEN = "{AKIA_SECRET}"\n'
        secret_file.write_text(secret_content)

        result = _call_commit_changes(
            message="add secret", files="secret.py", repo_dir=repo
        )
        assert result.get("success") is False, result

        staged_after = _staged_names(repo)
        assert "secret.py" not in staged_after
        assert "other.txt" not in staged_after, (
            "a bare `git reset HEAD` unstages the WHOLE index, including "
            "content pre-staged by the agent before this call -- this is "
            "the documented (non-destructive) scope, not a narrower "
            "this-call-only unstage"
        )

        # Neither file's working-tree content was touched.
        assert secret_file.read_text() == secret_content
        assert other_file.read_text() == other_content


# ---------------------------------------------------------------------------
# T4 -- no false-positive deadlock: with the opt-in toggles UNSET, the
# always-on secret-scan is the ONLY thing that blocks by default.
# ---------------------------------------------------------------------------


class TestT4NoFalsePositiveDeadlockByDefault:
    def test_commit_on_main_succeeds_with_branch_protection_unset(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        assert _git(["branch", "--show-current"], repo).strip() == "main"

        benign_file = Path(repo) / "on_main.txt"
        benign_file.write_text("trunk-based commit, no branch toggle set\n")

        result = _call_commit_changes(
            message="trunk commit", files="on_main.txt", repo_dir=repo
        )
        assert result.get("success") is True, (
            f"branch protection is opt-in (GLEIPNIR_GIT_PROTECT_BRANCHES unset) "
            f"-- committing to main must succeed by default: {result}"
        )

    def test_staging_a_sqlite_data_file_succeeds_with_data_file_check_unset(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)

        data_file = Path(repo) / "cache.sqlite"
        data_file.write_bytes(b"not-actually-sqlite-but-clean-content")

        result = _call_commit_changes(
            message="add cache db", files="cache.sqlite", repo_dir=repo
        )
        assert result.get("success") is True, (
            f"data-file check is opt-in (GLEIPNIR_GIT_CHECK_DATA_FILES unset) "
            f"-- staging a .sqlite file with clean content must succeed by "
            f"default: {result}"
        )


# ---------------------------------------------------------------------------
# T5 -- POST-STAGE visibility: the scan must see `git diff --cached` AFTER
# staging, not an empty pre-stage tree. Uses the `files=""` (`git add -A`)
# path, distinct from T1's explicit single-file `files=` path, so a scan
# mistakenly wired BEFORE the staging step (which would see an empty diff
# and false-CLOSED-pass) is caught: if that bug were present, this test's
# "no commit created" assertion would fail because the buggy implementation
# would proceed straight to `git commit`.
# ---------------------------------------------------------------------------


class TestT5ScanRunsPostStageNotPreStage:
    def test_secret_in_a_to_be_staged_file_is_caught_via_add_all_path(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        head_before = _rev_parse_head(repo)

        # Nothing is staged yet -- if the scan ran BEFORE `git add -A`, the
        # diff it would see (`git diff --cached`) is empty right now.
        assert _staged_names(repo) == []

        secret_file = Path(repo) / "creds.py"
        secret_content = f'AWS_KEY = "{AKIA_SECRET}"\n'
        secret_file.write_text(secret_content)

        # files="" -> commit_changes runs `git add -A`, staging creds.py
        # itself. The scan must observe the POST-stage diff.
        result = _call_commit_changes(message="add creds", files="", repo_dir=repo)

        assert result.get("success") is False, (
            "a scan wired before staging would see an empty diff and "
            f"wrongly let this commit through (false-CLOSED): {result}"
        )
        assert AKIA_SECRET not in json.dumps(result)

        # No commit created; the working file remains present with its
        # original (secret-bearing) content -- proving the content that was
        # scanned is exactly what would have been committed, not something
        # rolled back/lost.
        assert _rev_parse_head(repo) == head_before
        assert secret_file.exists()
        assert secret_file.read_text() == secret_content
