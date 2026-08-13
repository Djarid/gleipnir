"""Coverage-gap tests for `src/gleipnir/broker/git/mcp_server.py`.

Plan: `.gleipnir/plans/broker-git-coverage-gap.md`. Target: raise line+branch
coverage on `mcp_server.py` from 52% to >=85% by exercising the tool
functions and error branches NOT already covered by
`tests/test_broker_git_commit_guard.py` (secret-scan refuse/pass/reset paths,
T1-T5) or `tests/test_broker_tool_surface.py` (4-tool set, force-param
absence, hook-bypass surface at the tool-surface level). This file does NOT
duplicate either.

Scope (plan Trace gaps G1-G6, plus two corrections applied per the delegation
that supersede the plan text where they conflict with the actual source):

  - G1 `git_status`: branch/`protected` field, porcelain status-code
    combinations (untracked/staged-only/unstaged-only/both), `clean` flag.
  - G2 `git_diff`: default/`--cached`/`target`/`file` argument combinations
    and the `{"success": False, "error": ...}` path.
  - G3 `push_current_branch`: first-push success, `-u` retry, both-fail,
    no-current-branch early return.
  - G4 `commit_changes`: the four non-secret-scan failure paths (per-file
    `add` failure, `add -A` failure, scan-read fail-closed, final `commit`
    failure) -- distinct from the secret-scan refuse/pass paths already
    owned by `test_broker_git_commit_guard.py`.
  - G6 `_current_branch`: fallback to `""` when the underlying `_run_git`
    call is unsuccessful.
  - **Correction 1 (supersedes the plan's G5 example):** the plan's
    worked example proposed driving `_run_git`'s `subprocess.TimeoutExpired`
    / `FileNotFoundError` / generic-`Exception` branches through `git_status`.
    That is wrong: `git_status` (mcp_server.py:174-211) ALWAYS returns
    `{"success": True, ...}` -- it never surfaces an `_run_git` failure as a
    tool-level error (see the porcelain-failure characterization test below).
    These branches are instead driven through `git_diff`
    (mcp_server.py:238-243), which genuinely propagates
    `{"success": False, "error": ...}`, by monkeypatching
    `mcp_server.subprocess.run` (not the bare `subprocess` module).
  - **Correction 2 (branches the plan's G1-G6 enumeration missed):**
    (a) `_run_git`'s hook-bypass early return (mcp_server.py:137-139), driven
    non-hypothetically via `commit_changes(files="--no-verify", ...)`; (b)
    `git_status`'s porcelain-failure False arm (mcp_server.py:189), which is
    a characterization test of today's graceful-degradation/silent-swallow
    behaviour, not a bug fix.

Driving pattern: reused from `tests/test_broker_git_commit_guard.py` (real
temp repo via `git init` + `symbolic-ref HEAD` + `config user.*` + one
initial commit; tool functions are directly callable per-`@mcp.tool()`
FastMCP semantics; each returns a JSON string, parsed via `json.loads`).
Monkeypatching (`mcp_server._run_git` scripted-by-argv, or
`mcp_server.subprocess.run`) is used only for branches not reliably
reachable with real git (G3, most of G4, the exception branches).

Runs under the **broker profile** (imports `mcp` transitively via
`mcp_server`) -- see `tests/conftest.py` `collect_ignore`. Per the plan's
Decision 4 / edge case E-COLLECT, `.gleipnir/sandbox/profiles.toml`
`[profile.broker].test` is a Tier-3, operator-only, EXPLICIT file list that
must also be amended to add this file before `bin/gleipnir-sandbox test`
(broker profile) will collect it -- a bounded code agent cannot make that
edit itself.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from gleipnir.broker.git import mcp_server

# ---------------------------------------------------------------------------
# Shared helpers (replicated from tests/test_broker_git_commit_guard.py's
# proven shape rather than imported, per the plan's Assemble Step 1 note).
# ---------------------------------------------------------------------------

_GIT_ENV_VARS = (
    "GLEIPNIR_GIT_STRICT",
    "GLEIPNIR_GIT_PROTECT_BRANCHES",
    "GLEIPNIR_GIT_CHECK_DATA_FILES",
    "GLEIPNIR_GIT_PROTECTED_BRANCHES",
)


def _clear_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset every opt-in broker toggle so tests exercise the DEFAULT posture."""
    for var in _GIT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(args: List[str], cwd: str) -> str:
    """Run a real `git` command for test setup/verification (NOT the broker)."""
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
    """A real temp git repo, branch `main`, with one prior commit."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    rd = str(repo_dir)
    _git(["init"], rd)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], rd)
    _git(["config", "user.email", "gleipnir-test@example.invalid"], rd)
    _git(["config", "user.name", "Gleipnir Test"], rd)
    (repo_dir / "README.md").write_text("initial\n")
    _git(["add", "README.md"], rd)
    _git(["commit", "-m", "initial commit"], rd)
    return rd


def _make_stubbed_run_git(
    scripted: Dict[Tuple[str, ...], Dict[str, Any]],
    calls: Optional[List[Tuple[str, ...]]] = None,
):
    """Build a `mcp_server._run_git` replacement scripted by exact argv match.

    Any argv not present in `scripted` returns a loud, obviously-unscripted
    failure so an unexpected call fails the test instead of silently passing.
    """

    def _stub(
        args: List[str], repo_dir: Optional[str] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        key = tuple(args)
        if calls is not None:
            calls.append(key)
        if key in scripted:
            return dict(scripted[key])
        return {"success": False, "error": f"unscripted git args: {list(args)}"}

    return _stub


# ---------------------------------------------------------------------------
# G1 -- git_status: branch/protected, porcelain combinations, clean flag.
# ---------------------------------------------------------------------------


class TestGitStatus:
    def test_clean_repo_reports_clean_true_and_unprotected(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        result = json.loads(mcp_server.git_status(repo_dir=repo))
        assert result["success"] is True
        assert result["branch"] == "main"
        assert result["protected"] is False
        assert result["clean"] is True
        assert result["staged"] == []
        assert result["unstaged"] == []
        assert result["untracked"] == []

    def test_protected_branch_true_arm_when_protection_opted_in(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", "1")
        result = json.loads(mcp_server.git_status(repo_dir=repo))
        assert result["branch"] == "main"
        assert result["protected"] is True

    def test_untracked_file_appears_only_in_untracked(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        (Path(repo) / "new_file.txt").write_text("brand new\n")
        result = json.loads(mcp_server.git_status(repo_dir=repo))
        assert result["untracked"] == ["new_file.txt"]
        assert result["staged"] == []
        assert result["unstaged"] == []
        assert result["clean"] is False

    def test_staged_only_file_appears_only_in_staged(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        (Path(repo) / "staged_file.txt").write_text("to be staged\n")
        _git(["add", "staged_file.txt"], repo)
        result = json.loads(mcp_server.git_status(repo_dir=repo))
        assert result["staged"] == ["staged_file.txt"]
        assert result["unstaged"] == []
        assert result["untracked"] == []

    def test_unstaged_only_modification_appears_only_in_unstaged(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        tracked = Path(repo) / "tracked.txt"
        tracked.write_text("v1\n")
        _git(["add", "tracked.txt"], repo)
        _git(["commit", "-m", "add tracked"], repo)

        tracked.write_text("v2 unstaged\n")
        result = json.loads(mcp_server.git_status(repo_dir=repo))
        assert result["staged"] == []
        assert result["unstaged"] == ["tracked.txt"]
        assert result["untracked"] == []

    def test_staged_then_further_modified_appears_in_both(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        tracked = Path(repo) / "both.txt"
        tracked.write_text("v1\n")
        _git(["add", "both.txt"], repo)
        _git(["commit", "-m", "add both"], repo)

        tracked.write_text("v2 staged\n")
        _git(["add", "both.txt"], repo)
        tracked.write_text("v3 unstaged-on-top\n")

        result = json.loads(mcp_server.git_status(repo_dir=repo))
        assert "both.txt" in result["staged"]
        assert "both.txt" in result["unstaged"]
        assert result["clean"] is False


class TestGitStatusRenameDoesNotCrash:
    def test_rename_status_line_is_handled_without_raising(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        """Documents current behaviour (not a correctness claim): a rename
        porcelain line (`R  old -> new`) does not crash the parser."""
        _clear_git_env(monkeypatch)
        old = Path(repo) / "old_name.txt"
        old.write_text("same content\n")
        _git(["add", "old_name.txt"], repo)
        _git(["commit", "-m", "add old_name"], repo)
        _git(["mv", "old_name.txt", "new_name.txt"], repo)

        raw = mcp_server.git_status(repo_dir=repo)
        result = json.loads(raw)
        assert result["success"] is True
        assert isinstance(result["staged"], list)


class TestGitStatusPorcelainFailureCharacterization:
    """Correction 2b: `git_status`'s porcelain-failure False arm
    (mcp_server.py:189). This is a characterization test of TODAY's
    graceful-degradation/silent-swallow behaviour -- `git_status` still
    returns `success: True` with empty lists when the underlying
    `git status --porcelain` call fails. Not a bug fix."""

    def test_porcelain_failure_degrades_to_success_true_with_empty_lists(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        real_run_git = mcp_server._run_git

        def _stub(
            args: List[str], repo_dir: Optional[str] = None, timeout: int = 30
        ) -> Dict[str, Any]:
            if args == ["status", "--porcelain"]:
                return {"success": False, "error": "boom", "stderr": "boom"}
            return real_run_git(args, repo_dir, timeout)

        monkeypatch.setattr(mcp_server, "_run_git", _stub)
        result = json.loads(mcp_server.git_status(repo_dir=repo))

        assert result["success"] is True
        assert result["staged"] == []
        assert result["unstaged"] == []
        assert result["untracked"] == []


# ---------------------------------------------------------------------------
# G2 -- git_diff: default/staged/target/file combinations + error branch.
# ---------------------------------------------------------------------------


class TestGitDiff:
    def test_default_unstaged_diff_is_non_empty(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        readme = Path(repo) / "README.md"
        readme.write_text("initial\nmodified unstaged\n")

        result = json.loads(mcp_server.git_diff(repo_dir=repo))
        assert result["success"] is True
        assert "modified unstaged" in result["diff"]

    def test_staged_true_returns_staged_diff_and_default_now_empty(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        readme = Path(repo) / "README.md"
        readme.write_text("initial\nstaged change\n")
        _git(["add", "README.md"], repo)

        staged_result = json.loads(mcp_server.git_diff(staged=True, repo_dir=repo))
        assert staged_result["success"] is True
        assert "staged change" in staged_result["diff"]

        unstaged_result = json.loads(mcp_server.git_diff(repo_dir=repo))
        assert unstaged_result["success"] is True
        assert unstaged_result["diff"] == ""

    def test_target_ref_compares_against_an_earlier_commit(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        head_before = _git(["rev-parse", "HEAD"], repo).strip()

        added = Path(repo) / "a.txt"
        added.write_text("v1\n")
        _git(["add", "a.txt"], repo)
        _git(["commit", "-m", "add a.txt"], repo)
        added.write_text("v2 uncommitted\n")

        result = json.loads(mcp_server.git_diff(target=head_before, repo_dir=repo))
        assert result["success"] is True
        assert "a.txt" in result["diff"]

    def test_file_scopes_diff_to_a_single_file(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        a = Path(repo) / "a.txt"
        b = Path(repo) / "b.txt"
        a.write_text("a-v1\n")
        b.write_text("b-v1\n")
        _git(["add", "a.txt", "b.txt"], repo)
        _git(["commit", "-m", "add a and b"], repo)

        a.write_text("a-v2\n")
        b.write_text("b-v2\n")

        result = json.loads(mcp_server.git_diff(file="a.txt", repo_dir=repo))
        assert result["success"] is True
        assert "a.txt" in result["diff"]
        assert "b.txt" not in result["diff"]

    def test_error_path_returns_success_false_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _clear_git_env(monkeypatch)
        not_a_repo = tmp_path / "not_a_repo"
        not_a_repo.mkdir()

        result = json.loads(mcp_server.git_diff(repo_dir=str(not_a_repo)))
        assert result["success"] is False
        assert result["error"]


class TestRunGitExceptionBranchesViaGitDiff:
    """Correction 1: retargets the plan's G5 exception-branch tests through
    `git_diff` (which genuinely propagates `{"success": False, "error": ...}`
    from `_run_git`'s except blocks), NOT `git_status` (which always returns
    `success: True` regardless of the underlying `_run_git` result -- see
    TestGitStatusPorcelainFailureCharacterization above). Patches
    `mcp_server.subprocess.run`, driven through the benign `["diff"]` argv so
    `_rejects_hook_bypass` returns None and execution reaches the try-block.
    """

    def test_timeout_expired_maps_to_timed_out_error(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise subprocess.TimeoutExpired(cmd=["git", "diff"], timeout=30)

        monkeypatch.setattr(mcp_server.subprocess, "run", _raise)
        result = json.loads(mcp_server.git_diff(repo_dir=repo))
        assert result == {
            "success": False,
            "error": "git command timed out after 30s",
        }

    def test_file_not_found_error_maps_to_git_executable_not_found(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise FileNotFoundError()

        monkeypatch.setattr(mcp_server.subprocess, "run", _raise)
        result = json.loads(mcp_server.git_diff(repo_dir=repo))
        assert result == {"success": False, "error": "git executable not found"}

    def test_generic_exception_maps_to_str_of_exception(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(mcp_server.subprocess, "run", _raise)
        result = json.loads(mcp_server.git_diff(repo_dir=repo))
        assert result == {"success": False, "error": "boom"}


# ---------------------------------------------------------------------------
# G3 -- push_current_branch: success / retry / both-fail / no-branch.
# ---------------------------------------------------------------------------


class TestPushCurrentBranch:
    def test_first_push_succeeds(self, monkeypatch: pytest.MonkeyPatch):
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("push", "origin", "main"): {"success": True, "stdout": "", "stderr": ""},
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        result = json.loads(mcp_server.push_current_branch(repo_dir="/irrelevant"))
        assert result == {"success": True, "branch": "main"}

    def test_first_push_fails_then_dash_u_retry_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("push", "origin", "main"): {
                "success": False,
                "stdout": "",
                "stderr": "no upstream configured",
            },
            ("push", "-u", "origin", "main"): {
                "success": True,
                "stdout": "",
                "stderr": "",
            },
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        result = json.loads(mcp_server.push_current_branch(repo_dir="/irrelevant"))
        assert result == {"success": True, "branch": "main"}

    def test_both_push_attempts_fail(self, monkeypatch: pytest.MonkeyPatch):
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("push", "origin", "main"): {
                "success": False,
                "stdout": "",
                "stderr": "first failure",
            },
            ("push", "-u", "origin", "main"): {
                "success": False,
                "stdout": "",
                "stderr": "second failure",
            },
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        result = json.loads(mcp_server.push_current_branch(repo_dir="/irrelevant"))
        assert result == {"success": False, "error": "second failure"}

    def test_no_current_branch_returns_early_without_pushing(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        calls: List[Tuple[str, ...]] = []
        scripted = {
            ("branch", "--show-current"): {"success": False, "stdout": "", "error": "x"},
        }
        monkeypatch.setattr(
            mcp_server, "_run_git", _make_stubbed_run_git(scripted, calls)
        )
        result = json.loads(mcp_server.push_current_branch(repo_dir="/irrelevant"))
        assert result == {
            "success": False,
            "error": "Could not determine current branch",
        }
        assert not any(c[0] == "push" for c in calls)


# ---------------------------------------------------------------------------
# G4 -- commit_changes: the four non-secret-scan failure paths.
# ---------------------------------------------------------------------------


class TestCommitChangesFailurePaths:
    def test_per_file_add_failure(self, monkeypatch: pytest.MonkeyPatch):
        """Scripted (not real-git) per the plan's explicit fallback: whether
        a nonexistent pathspec makes `git add <file>` fail is a git-version
        behaviour this session cannot verify in-sandbox (the broker profile
        is unreachable via this delegation's capability -- see report), so
        the per-file staging-failure branch (301-308) is driven deterministically
        instead of relying on that assumption."""
        _clear_git_env(monkeypatch)
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("add", "does-not-exist.txt"): {
                "success": False,
                "stdout": "",
                "stderr": "pathspec did not match any files",
            },
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        raw = mcp_server.commit_changes(
            message="x", files="does-not-exist.txt", repo_dir="/irrelevant"
        )
        result = json.loads(raw)
        assert result["success"] is False
        assert result["error"] == (
            "Failed to stage 'does-not-exist.txt': pathspec did not match any files"
        )

    def test_add_dash_a_failure(self, monkeypatch: pytest.MonkeyPatch):
        _clear_git_env(monkeypatch)
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("add", "-A"): {"success": False, "stdout": "", "stderr": "disk full"},
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        raw = mcp_server.commit_changes(message="x", files="", repo_dir="/irrelevant")
        result = json.loads(raw)
        assert result["success"] is False
        assert result["error"].startswith("Failed to stage: ")

    def test_scan_read_failure_is_fail_closed_no_commit(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        calls: List[Tuple[str, ...]] = []
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("add", "-A"): {"success": True, "stdout": "", "stderr": ""},
            ("diff", "--cached"): {
                "success": False,
                "stdout": "",
                "stderr": "diff broke",
            },
        }
        monkeypatch.setattr(
            mcp_server, "_run_git", _make_stubbed_run_git(scripted, calls)
        )
        raw = mcp_server.commit_changes(message="x", files="", repo_dir="/irrelevant")
        result = json.loads(raw)
        assert result["success"] is False
        assert result["error"].startswith(
            "Failed to read staged diff for secret-scan: "
        )
        assert not any(c[0] == "commit" for c in calls)

    def test_final_commit_failure_surfaces_as_normal_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        scripted = {
            ("branch", "--show-current"): {"success": True, "stdout": "main\n"},
            ("add", "-A"): {"success": True, "stdout": "", "stderr": ""},
            ("diff", "--cached"): {"success": True, "stdout": "", "stderr": ""},
            ("diff", "--cached", "--name-only"): {
                "success": True,
                "stdout": "",
                "stderr": "",
            },
            ("commit", "-m", "hook test"): {
                "success": False,
                "stdout": "",
                "stderr": "hook rejected",
            },
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        raw = mcp_server.commit_changes(
            message="hook test", files="", repo_dir="/irrelevant"
        )
        result = json.loads(raw)
        assert result["success"] is False
        assert result["error"] == "hook rejected"


# ---------------------------------------------------------------------------
# Correction 2a -- _run_git's hook-bypass early return (mcp_server.py:137-139).
# ---------------------------------------------------------------------------


class TestRunGitHookBypassEarlyReturn:
    def test_commit_changes_staging_no_verify_is_refused_before_any_add_runs(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ):
        """Drives the True arm non-hypothetically: `commit_changes` stages via
        `_run_git(["add", "--no-verify"], rd)`, which trips
        `_rejects_hook_bypass` at the `_run_git` choke point (137-139) before
        `subprocess.run` is ever reached. The refusal surfaces as a staging
        failure (the outer `commit_changes` wraps it as "Failed to stage
        '--no-verify': ...")."""
        _clear_git_env(monkeypatch)
        raw = mcp_server.commit_changes(
            message="x", files="--no-verify", repo_dir=repo
        )
        result = json.loads(raw)
        assert result["success"] is False
        assert "Failed to stage '--no-verify'" in result["error"]

    def test_run_git_directly_surfaces_the_hook_bypass_refusal_reason(
        self, repo: str
    ):
        """Direct, lower-level check that the choke point itself names the
        refusal (the text swallowed by `commit_changes`'s wrapping above)."""
        result = mcp_server._run_git(["add", "--no-verify"], repo)
        assert result["success"] is False
        assert "bypass git hooks" in result["error"]


# ---------------------------------------------------------------------------
# G6 -- _current_branch: fallback to "" when the underlying call fails.
# ---------------------------------------------------------------------------


class TestCurrentBranchFallback:
    def test_returns_empty_string_when_run_git_is_unsuccessful(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        scripted = {
            ("branch", "--show-current"): {"success": False, "error": "x"},
        }
        monkeypatch.setattr(mcp_server, "_run_git", _make_stubbed_run_git(scripted))
        assert mcp_server._current_branch("/irrelevant") == ""
