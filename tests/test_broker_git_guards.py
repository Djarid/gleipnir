"""Unit tests for the git broker's pre-commit guard module (T-B, T-C).

Plan: `.gleipnir/plans/broker-mcp.md`, Assemble Step 2 / Step 3, Stress-test
T-B (secret-scan) + T-C (protected-branch refusal). Target module (does NOT
exist yet -- this is the point, Axiom 1):

    src/gleipnir/broker/git/guards.py   (stdlib-only: os, re, subprocess)

ASSUMED API (documented for the implementer -- the plan names the functions
but not every signature; this test file is the concrete spec test-first
gives them):

    get_protected_branches() -> list[str]
        Reads GLEIPNIR_GIT_PROTECTED_BRANCHES (comma-separated). Default
        ["main", "master"] when unset.

    is_protected_branch(branch: str) -> bool

    SECRET_PATTERNS: list[tuple[str | re.Pattern, str]]
        (pattern, description) pairs.

    scan_diff_for_secrets(diff_text: str) -> list[dict]
        Scans ONLY "+"-added content lines (never the "+++"/"---" file
        headers, the "diff --git" line, or unchanged " " context lines).
        Each finding is a dict with keys: "file", "line", "description",
        "match" -- "match" is REDACTED (the full secret must never appear
        verbatim in a finding).

    check_staged_data_files(staged_files: list[str]) -> list[str]
        Flags .db/.sqlite/.env/venv artifacts among the given paths.

    precommit_check(branch: str, diff: str, staged_files: list[str] | None = None)
        -> Mapping[str, object] (dict or object with a `.passed` attribute)
        Combined gate: passed is False if the branch is protected, OR the
        diff contains a secret, OR a staged data file is flagged.

Two planted fake secrets are used, sized programmatically (not by manual
character counting) so their shape is verifiably correct:
  - an AWS-Access-Key-ID-shaped string: "AKIA" + 16 upper/digit chars
  - a GitHub-personal-access-token-shaped string: "ghp_" + 36 alnum chars
Neither is a real credential.
"""

from __future__ import annotations

import pytest

from gleipnir.broker.git import guards


AKIA_SECRET = "AKIA" + ("Q7X9" * 4)  # AKIA + 16 upper/digit chars
GHP_SECRET = "ghp_" + ("aB3xQ9" * 6)  # ghp_ + 36 alnum chars

assert len(AKIA_SECRET) == 20 and AKIA_SECRET[:4] == "AKIA"
assert len(GHP_SECRET) == 40 and GHP_SECRET.startswith("ghp_") and len(GHP_SECRET) - 4 == 36


def _diff_with_added_secret(secret: str, filename: str = "config.py") -> str:
    """A realistic unified diff with `secret` on a single "+"-added line.

    Also carries a context line (leading space) containing a decoy match of
    the SAME secret text, to prove context lines are not scanned.
    """
    return (
        f"diff --git a/{filename} b/{filename}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{filename}\n"
        f"+++ b/{filename}\n"
        "@@ -1,3 +1,4 @@\n"
        f" context_mentions_but_not_scanned = {secret!r}\n"
        "-old_value = 1\n"
        f'+API_KEY = "{secret}"\n'
        " trailing_context_line\n"
    )


CLEAN_DIFF = (
    "diff --git a/app.py b/app.py\n"
    "index aaaaaaa..bbbbbbb 100644\n"
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a, b):\n"
    "-    return a - b\n"
    "+    return a + b\n"
)


def _passed(result) -> bool:
    """precommit_check may return a dict or an object; support both."""
    if isinstance(result, dict):
        return bool(result["passed"])
    return bool(result.passed)


# ---------------------------------------------------------------------------
# get_protected_branches / is_protected_branch
# ---------------------------------------------------------------------------


class TestProtectedBranches:
    """Branch protection is OPT-IN, DEFAULT OFF (workflow policy, not a safety
    invariant). Committing to main is a workflow choice the operator owns;
    mandating feature branches would brick trunk-based workflows and DEADLOCK
    autonomous (L2/L3) operators that have no human to answer a prompt."""

    def test_protection_is_disabled_by_default(self, monkeypatch):
        # Default (toggle unset): nothing is protected — trunk-based / L2/L3
        # operators commit to main freely.
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECT_BRANCHES", raising=False)
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", raising=False)
        assert guards.branch_protection_enabled() is False
        assert guards.is_protected_branch("main") is False
        assert guards.is_protected_branch("master") is False
        assert guards.is_protected_branch("feature/add-widget") is False

    def test_protected_list_default_is_main_and_master(self, monkeypatch):
        # The LIST default is still main,master — it just only takes effect
        # once protection is explicitly enabled.
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", raising=False)
        assert guards.get_protected_branches() == ["main", "master"]

    def test_opt_in_enables_default_main_master_protection(self, monkeypatch):
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", "1")
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", raising=False)
        assert guards.branch_protection_enabled() is True
        assert guards.is_protected_branch("main") is True
        assert guards.is_protected_branch("master") is True
        assert guards.is_protected_branch("feature/add-widget") is False

    def test_toggle_accepts_truthy_variants(self, monkeypatch):
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", raising=False)
        for val in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", val)
            assert guards.branch_protection_enabled() is True
            assert guards.is_protected_branch("main") is True
        for val in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", val)
            assert guards.branch_protection_enabled() is False
            assert guards.is_protected_branch("main") is False

    def test_custom_protected_branches_env_is_respected_when_enabled(self, monkeypatch):
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", "1")
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", "release,hotfix")
        assert guards.get_protected_branches() == ["release", "hotfix"]
        assert guards.is_protected_branch("release") is True
        assert guards.is_protected_branch("hotfix") is True
        # master is NOT protected once the env overrides the default list
        assert guards.is_protected_branch("master") is False

    def test_custom_list_ignored_when_protection_disabled(self, monkeypatch):
        # Even a custom list does nothing unless protection is opted in.
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECT_BRANCHES", raising=False)
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", "release,hotfix")
        assert guards.is_protected_branch("release") is False

    def test_feature_branch_is_never_protected(self, monkeypatch):
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", "1")
        monkeypatch.delenv("GLEIPNIR_GIT_PROTECTED_BRANCHES", raising=False)
        assert guards.is_protected_branch("feature/broker-mcp") is False


# ---------------------------------------------------------------------------
# SECRET_PATTERNS / scan_diff_for_secrets
# ---------------------------------------------------------------------------


class TestSecretScan:
    def test_secret_patterns_table_shape(self):
        assert isinstance(guards.SECRET_PATTERNS, list)
        assert len(guards.SECRET_PATTERNS) > 0
        for entry in guards.SECRET_PATTERNS:
            pattern, description = entry
            assert isinstance(description, str) and description

    def test_added_line_with_planted_aws_key_yields_a_redacted_finding(self):
        diff_text = _diff_with_added_secret(AKIA_SECRET)
        findings = guards.scan_diff_for_secrets(diff_text)

        assert len(findings) == 1, f"expected exactly one finding, got {findings!r}"
        finding = findings[0]
        assert set(("file", "line", "description", "match")) <= set(finding.keys())
        assert finding["file"] == "config.py"
        assert isinstance(finding["description"], str) and finding["description"]
        # Redaction: the full secret must never appear verbatim in the finding.
        assert AKIA_SECRET not in finding["match"]

    def test_added_line_with_planted_github_token_yields_a_redacted_finding(self):
        diff_text = _diff_with_added_secret(GHP_SECRET, filename="server.py")
        findings = guards.scan_diff_for_secrets(diff_text)

        assert len(findings) == 1, f"expected exactly one finding, got {findings!r}"
        finding = findings[0]
        assert finding["file"] == "server.py"
        assert GHP_SECRET not in finding["match"]

    def test_plus_plus_plus_header_and_context_lines_are_not_scanned(self):
        """The +++ file header and unchanged (" "-prefixed) context lines
        must never be scanned, even when they contain secret-shaped text --
        only the finding produced above (from the "+"-added line) counts."""
        diff_text = _diff_with_added_secret(AKIA_SECRET)
        # The context line in _diff_with_added_secret already repeats the
        # secret; confirm scan still finds exactly one (from the + line).
        findings = guards.scan_diff_for_secrets(diff_text)
        assert len(findings) == 1

        # A diff whose secret ONLY appears in the +++ header (never on a
        # "+"-added content line) must yield NO findings at all.
        header_only_diff = (
            "diff --git a/config.py b/config.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/config.py\n"
            f"+++ b/config.py  {AKIA_SECRET}\n"
            "@@ -1,2 +1,2 @@\n"
            " unrelated_context_one\n"
            " unrelated_context_two\n"
        )
        assert guards.scan_diff_for_secrets(header_only_diff) == []

    def test_clean_diff_yields_no_findings(self):
        assert guards.scan_diff_for_secrets(CLEAN_DIFF) == []


# ---------------------------------------------------------------------------
# check_staged_data_files
# ---------------------------------------------------------------------------


class TestStagedDataFiles:
    def test_flags_env_and_sqlite_and_db_and_venv(self):
        staged = [
            ".env",
            "notes.sqlite",
            "cache.db",
            "venv/bin/activate",
            "app.py",
            "README.md",
        ]
        flagged = guards.check_staged_data_files(staged)
        assert ".env" in flagged
        assert "notes.sqlite" in flagged
        assert "cache.db" in flagged
        assert "venv/bin/activate" in flagged
        assert "app.py" not in flagged
        assert "README.md" not in flagged

    def test_no_flags_for_ordinary_source_files(self):
        staged = ["src/gleipnir/broker/git/guards.py", "tests/test_x.py"]
        assert guards.check_staged_data_files(staged) == []


# ---------------------------------------------------------------------------
# precommit_check (combined gate)
# ---------------------------------------------------------------------------


class TestPrecommitCheckCombinedGate:
    """Non-strict (default): the ONLY blocking check is secret-scan. Branch
    protection and data-file checks are opt-in / strict-only. This is what keeps
    the broker from being so constraining that people bypass Gleipnir entirely."""

    def _clear(self, monkeypatch):
        for var in (
            "GLEIPNIR_GIT_STRICT",
            "GLEIPNIR_GIT_PROTECT_BRANCHES",
            "GLEIPNIR_GIT_CHECK_DATA_FILES",
            "GLEIPNIR_GIT_PROTECTED_BRANCHES",
        ):
            monkeypatch.delenv(var, raising=False)

    # --- always-on safety: secret-scan ---
    def test_fails_on_secret_in_diff_even_non_strict(self, monkeypatch):
        self._clear(monkeypatch)
        diff_text = _diff_with_added_secret(GHP_SECRET)
        result = guards.precommit_check(
            branch="feature/x", diff=diff_text, staged_files=[]
        )
        assert _passed(result) is False

    def test_secret_blocks_even_on_main_non_strict(self, monkeypatch):
        # Secret-scan is not conditional on branch or mode.
        self._clear(monkeypatch)
        diff_text = _diff_with_added_secret(GHP_SECRET)
        result = guards.precommit_check(branch="main", diff=diff_text, staged_files=[])
        assert _passed(result) is False

    # --- non-strict: opinionated checks do NOT block ---
    def test_commit_to_main_passes_non_strict(self, monkeypatch):
        # The boss-who-hates-branching / trunk-based / L2-L3 case.
        self._clear(monkeypatch)
        result = guards.precommit_check(branch="main", diff=CLEAN_DIFF, staged_files=[])
        assert _passed(result) is True

    def test_staged_data_file_passes_non_strict(self, monkeypatch):
        self._clear(monkeypatch)
        result = guards.precommit_check(
            branch="feature/x", diff=CLEAN_DIFF, staged_files=[".env"]
        )
        assert _passed(result) is True

    def test_passes_on_clean_feature_branch(self, monkeypatch):
        self._clear(monkeypatch)
        result = guards.precommit_check(
            branch="feature/x", diff=CLEAN_DIFF, staged_files=[]
        )
        assert _passed(result) is True

    # --- strict / opt-in: the opinionated checks re-engage ---
    def test_fails_on_protected_branch_when_strict(self, monkeypatch):
        self._clear(monkeypatch)
        monkeypatch.setenv("GLEIPNIR_GIT_STRICT", "1")
        result = guards.precommit_check(branch="main", diff=CLEAN_DIFF, staged_files=[])
        assert _passed(result) is False

    def test_fails_on_protected_branch_when_protect_opt_in(self, monkeypatch):
        self._clear(monkeypatch)
        monkeypatch.setenv("GLEIPNIR_GIT_PROTECT_BRANCHES", "1")
        result = guards.precommit_check(branch="main", diff=CLEAN_DIFF, staged_files=[])
        assert _passed(result) is False

    def test_fails_on_staged_data_file_when_strict(self, monkeypatch):
        self._clear(monkeypatch)
        monkeypatch.setenv("GLEIPNIR_GIT_STRICT", "1")
        result = guards.precommit_check(
            branch="feature/x", diff=CLEAN_DIFF, staged_files=[".env"]
        )
        assert _passed(result) is False

    def test_strict_flag_reported_in_result(self, monkeypatch):
        self._clear(monkeypatch)
        assert guards.precommit_check("feature/x", CLEAN_DIFF, [])["strict"] is False
        monkeypatch.setenv("GLEIPNIR_GIT_STRICT", "1")
        assert guards.precommit_check("feature/x", CLEAN_DIFF, [])["strict"] is True
