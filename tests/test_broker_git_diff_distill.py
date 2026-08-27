"""Integration test: `git_diff`'s real tool wiring dispatches through the
content-handler pilot (`DiffHunkTruncationHandler`) before returning.

Plan: `.gleipnir/plans/git-diff-distill.md`, Assemble Step 1, Stress-test
T-12. Imports `gleipnir.broker.git.mcp_server` (transitively `mcp`) --
broker-profile only; see `tests/conftest.py` `collect_ignore`.

Fixture shape replicated (not imported) from
`tests/test_broker_git_mcp_server.py`'s house convention: real temp git
repo via `git init` + `symbolic-ref HEAD` + `config user.*` + one initial
commit; tool functions are directly callable per-`@mcp.tool()` FastMCP
semantics and each returns a JSON string, parsed via `json.loads`.

Test-first note (Axiom 1): at authoring time the dispatch call does not
exist yet in `git_diff`, so the large-diff truncation assertions below are
EXPECTED TO FAIL until Assemble Step 4 wires the call site. That failure is
the point.

Tier-3 note: this file must be added to `.gleipnir/sandbox/profiles.toml`
`[profile.broker].test`'s literal file list (operator-only edit, Assemble
Step 5) before `bin/gleipnir-sandbox test` (broker profile) will collect it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from gleipnir.broker.git import mcp_server

# ---------------------------------------------------------------------------
# Shared helpers (replicated from tests/test_broker_git_mcp_server.py).
# ---------------------------------------------------------------------------

_GIT_ENV_VARS = (
    "GLEIPNIR_GIT_STRICT",
    "GLEIPNIR_GIT_PROTECT_BRANCHES",
    "GLEIPNIR_GIT_CHECK_DATA_FILES",
    "GLEIPNIR_GIT_PROTECTED_BRANCHES",
)


def _clear_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _GIT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(args: list[str], cwd: str) -> str:
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


class TestGitDiffDistillIntegration:
    def test_large_unstaged_diff_is_truncated_with_intact_envelope(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_git_env(monkeypatch)
        big = Path(repo) / "big.txt"
        # 100 lines committed, then every line changed -> a single hunk body
        # well above the T=40 threshold.
        original = "".join(f"line {i}\n" for i in range(1, 101))
        big.write_text(original)
        _git(["add", "big.txt"], repo)
        _git(["commit", "-m", "add big.txt"], repo)

        modified = "".join(f"line {i} CHANGED\n" for i in range(1, 101))
        big.write_text(modified)

        raw = mcp_server.git_diff(repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert "diff" in result and set(result.keys()) == {"success", "diff"}
        assert "truncated" in result["diff"]
        assert len(result["diff"]) < len(original) + len(modified)
        # File header / stat-relevant lines survive.
        assert "big.txt" in result["diff"]
        assert "diff --git a/big.txt b/big.txt" in result["diff"]

    def test_small_diff_round_trips_unchanged(
        self, repo: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_git_env(monkeypatch)
        readme = Path(repo) / "README.md"
        readme.write_text("initial\nsmall modification\n")

        raw = mcp_server.git_diff(repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert "small modification" in result["diff"]
        assert "truncated" not in result["diff"]

    def test_error_path_is_untouched_by_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_git_env(monkeypatch)
        not_a_repo = tmp_path / "not_a_repo"
        not_a_repo.mkdir()

        raw = mcp_server.git_diff(repo_dir=str(not_a_repo))
        result = json.loads(raw)

        assert result["success"] is False
        assert set(result.keys()) == {"success", "error"}
        assert result["error"]
