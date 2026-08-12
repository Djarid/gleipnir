"""Regression guard: every tracked `bin/*` file must be committed executable.

Plan: `.gleipnir/plans/bin-executable-bit-fix.md`, Assemble Phase 1 (B).

Why this exists: the always-active `git-guard.ts` gate shells out to
`bin/gleipnir-preflight config-scan` before every broker git write. A
`bin/*` entrypoint committed WITHOUT the executable bit makes that spawn
fail and the gate abort fail-closed -- indistinguishable from a genuine
policy rejection, and silently locking the broker out. `bin/gleipnir-preflight`
was found in exactly this state (mode `100644`) and fixed in commit
`9645974` (restored `100755`). This test is the loud, named, actionable
regression guard for that class of breakage.

Reads the COMMITTED mode via `git ls-files -s bin/` -- NOT a working-tree
`os.access(path, os.X_OK)` probe -- because `git config core.fileMode false`
makes git ignore working-tree mode changes, which would hide a wrong
committed mode from a working-tree-only check (Decision 3 in the plan).

Skips cleanly (does not fail) where no usable git tooling / work tree is
present -- e.g. in `bin/gleipnir-sandbox test`, whose `python:3.12-slim`
base image likely has no `git` binary at all, even though the whole repo
root (including `.git`) IS bind-mounted read-only there. The skip keys off
the OBSERVABLE SYMPTOM (git missing / not a usable work tree in this
environment), not any claim that `.git` is excluded from the mount.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(args: List[str]) -> subprocess.CompletedProcess:
    """Run `git <args>` at the repo root.

    Does NOT assert returncode -- callers decide whether a non-zero exit
    (or a missing `git` binary) means "skip" or "read the output".
    """
    return subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _tracked_bin_modes() -> List[Tuple[str, str]]:
    """Return [(mode, path), ...] parsed from `git ls-files -s bin/`.

    Each `ls-files -s` line has the shape:
        "<mode> <sha> <stage>\\t<path>"
    """
    result = _git(["ls-files", "-s", "bin/"])
    entries: List[Tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        mode = line.split()[0]
        path = line.split("\t", 1)[1]
        entries.append((mode, path))
    return entries


def _usable_git_work_tree() -> bool:
    """True iff `git` is present AND this checkout is a usable work tree."""
    try:
        result = _git(["rev-parse", "--is-inside-work-tree"])
    except FileNotFoundError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


if not _usable_git_work_tree():
    pytest.skip(
        "no usable git tooling / not inside a usable git work tree in this "
        "environment (e.g. no git binary in the sandbox base image) -- "
        "bin/* committed-mode check skipped",
        allow_module_level=True,
    )


def _format_failure(non_exec: List[Tuple[str, str]]) -> str:
    offending = ", ".join(f"{mode} {path}" for mode, path in non_exec)
    fix_lines = "\n".join(
        f"  chmod +x {path} && git add {path}\n"
        f"  # or, mode-only (no content change):\n"
        f"  git update-index --chmod=+x {path}"
        for _, path in non_exec
    )
    return (
        "Tracked bin/* file(s) committed WITHOUT the executable bit -- the "
        "always-active git-guard gate shells out to bin/gleipnir-preflight "
        "and will fail-closed on a non-executable entrypoint, blocking ALL "
        "broker commits/pushes. Fix each file:\n"
        f"{fix_lines}\n"
        f"Offending: {offending}\n"
        "Note: this checks the COMMITTED mode (git ls-files -s), so "
        "`core.fileMode false` cannot hide the regression."
    )


def test_tracked_bin_files_are_committed_executable() -> None:
    entries = _tracked_bin_modes()
    if not entries:
        pytest.skip("no tracked bin/* files to check")
    # Only regular blobs (mode 100xxx) carry a meaningful executable bit and
    # a fixable +x mode. Skip symlinks (120000) and gitlinks (160000): the
    # `& 0o111` mask would false-positive them, and `chmod +x`/
    # `git update-index --chmod=+x` don't meaningfully apply to those types.
    non_exec = [
        (mode, path)
        for mode, path in entries
        if mode.startswith("100") and not (int(mode, 8) & 0o111)
    ]
    assert not non_exec, _format_failure(non_exec)
