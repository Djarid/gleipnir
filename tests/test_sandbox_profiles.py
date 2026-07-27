"""Tests for the Tier-3 sandbox toolchain-dispatch config reader
(`src/gleipnir/sandbox/profiles.py`).

Spec: `.gleipnir/plans/language-agnostic-sandbox.md`, Assemble step 1 /
Stress-test #3. Pure, fail-closed: every defect (missing file, malformed
TOML, unknown profile, a verb with no configured command, an
unpinned/invalid image, a shell-string instead of an argv list, an
unjustified coverage-unavailable) raises `ProfileError`, never a silent
default. The B1 image-rule quartet is the cardinal assertion: the pure
reader distinguishes the ONE grandfathered literal from an arbitrary bare
tag — there is no shape rule that accepts a generic `name:tag`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gleipnir.sandbox.profiles import (
    Coverage,
    Profile,
    ProfileError,
    command_for,
    load_profiles,
    resolve_profile,
)
from gleipnir.sandbox.runtime import SandboxError

VALID_DIGEST = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def _write(tmp_path: Path, text: str) -> Path:
    (tmp_path / "profiles.toml").write_text(text)
    return tmp_path


_VALID_TWO_PROFILE_TOML = f"""
default_profile = "python"

[profile.python]
image = "gleipnir-sandbox:latest"
test = ["python", "-m", "pytest", "-p", "no:cacheprovider"]
lint = ["python", "-m", "compileall", "-q", "src"]
coverage = {{ args = ["--cov=src/gleipnir", "--cov-branch", "--cov-report=term-missing"], file_env = "COVERAGE_FILE", file_path = "/work/.scratch/.coverage" }}
test_selector_prefix = true

[profile.node]
image = "gleipnir-sandbox-node@sha256:{VALID_DIGEST}"
test = ["node", "--test", "tests/test_sequence_gate.mjs"]
lint = ["node", "--check", "tests/test_sequence_gate.mjs"]
coverage = {{ unavailable = true, justified = "node built-in coverage deferred" }}
test_selector_prefix = false
"""


# ---------------------------------------------------------------------------
# ProfileError is a SandboxError subclass (uniform exit-3 catch in __main__)
# ---------------------------------------------------------------------------

def test_profile_error_is_sandbox_error_subclass():
    assert issubclass(ProfileError, SandboxError)


# ---------------------------------------------------------------------------
# Happy path: load + resolve both profiles
# ---------------------------------------------------------------------------

class TestLoadValidConfig:
    def test_loads_python_and_node_profiles(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profiles = load_profiles(root)
        assert profiles.default_profile == "python"
        assert set(profiles.by_name) == {"python", "node"}

    def test_resolve_default_when_name_is_none(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profiles = load_profiles(root)
        profile = resolve_profile(profiles)
        assert profile.name == "python"
        assert profile.image == "gleipnir-sandbox:latest"

    def test_resolve_by_explicit_name(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profiles = load_profiles(root)
        profile = resolve_profile(profiles, "node")
        assert profile.name == "node"
        assert profile.image == f"gleipnir-sandbox-node@sha256:{VALID_DIGEST}"

    def test_python_profile_fields(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profile = resolve_profile(load_profiles(root), "python")
        assert profile.test_argv == ("python", "-m", "pytest", "-p", "no:cacheprovider")
        assert profile.lint_argv == ("python", "-m", "compileall", "-q", "src")
        assert profile.test_selector_prefix is True
        assert profile.coverage.unavailable is False
        assert "--cov-branch" in profile.coverage.args
        assert profile.coverage.file_env == "COVERAGE_FILE"
        assert profile.coverage.file_path == "/work/.scratch/.coverage"

    def test_node_profile_fields(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profile = resolve_profile(load_profiles(root), "node")
        assert profile.test_argv == ("node", "--test", "tests/test_sequence_gate.mjs")
        assert profile.test_selector_prefix is False
        assert profile.coverage.unavailable is True
        assert profile.coverage.justified == "node built-in coverage deferred"
        assert profile.coverage.args == ()

    def test_command_for_returns_the_configured_argv(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profile = resolve_profile(load_profiles(root), "python")
        assert command_for(profile, "test") == profile.test_argv
        assert command_for(profile, "lint") == profile.lint_argv


# ---------------------------------------------------------------------------
# B1: the strict image-validation quartet (the cardinal assertion)
# ---------------------------------------------------------------------------

class TestStrictImageRuleQuartet:
    def _config(self, tmp_path: Path, image: str) -> Path:
        return _write(
            tmp_path,
            f"""
default_profile = "p"

[profile.p]
image = "{image}"
test = ["true"]
lint = ["true"]
coverage = {{ unavailable = true, justified = "n/a" }}
""",
        )

    def test_arbitrary_bare_latest_tag_refuses(self, tmp_path: Path):
        root = self._config(tmp_path, "someimage:latest")
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_non_digest_version_tag_refuses(self, tmp_path: Path):
        root = self._config(tmp_path, "myimg:1.2")
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_digest_pinned_reference_accepts(self, tmp_path: Path):
        root = self._config(tmp_path, f"name@sha256:{VALID_DIGEST}")
        profiles = load_profiles(root)
        assert resolve_profile(profiles, "p").image == f"name@sha256:{VALID_DIGEST}"

    def test_grandfathered_literal_accepts(self, tmp_path: Path):
        root = self._config(tmp_path, "gleipnir-sandbox:latest")
        profiles = load_profiles(root)
        assert resolve_profile(profiles, "p").image == "gleipnir-sandbox:latest"

    def test_non_64_hex_digest_refuses(self, tmp_path: Path):
        root = self._config(tmp_path, "name@sha256:deadbeef")
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_uppercase_hex_digest_refuses(self, tmp_path: Path):
        root = self._config(tmp_path, f"name@sha256:{VALID_DIGEST.upper()}")
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_double_at_sha256_separator_refuses(self, tmp_path: Path):
        root = self._config(tmp_path, f"name@sha256:{VALID_DIGEST}@sha256:{VALID_DIGEST}")
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_grandfathered_literal_is_string_equality_not_a_shape_rule(self, tmp_path: Path):
        """A near-miss on the grandfathered literal (extra whitespace, a
        different tag) must still refuse — this is exact string equality,
        never a `gleipnir-sandbox:*` shape pattern."""
        root = self._config(tmp_path, "gleipnir-sandbox:stable")
        with pytest.raises(ProfileError):
            load_profiles(root)


# ---------------------------------------------------------------------------
# Fail-closed edge cases (plan §2 Edge cases)
# ---------------------------------------------------------------------------

class TestFailClosedEdgeCases:
    def test_missing_config_file_raises(self, tmp_path: Path):
        with pytest.raises(ProfileError, match="not found"):
            load_profiles(tmp_path / "does-not-exist")

    def test_malformed_toml_raises(self, tmp_path: Path):
        root = _write(tmp_path, "default_profile = [[[ not valid")
        with pytest.raises(ProfileError, match="malformed"):
            load_profiles(root)

    def test_default_profile_missing_key_raises(self, tmp_path: Path):
        root = _write(tmp_path, "[profile.python]\nimage = \"gleipnir-sandbox:latest\"\n")
        with pytest.raises(ProfileError, match="default_profile"):
            load_profiles(root)

    def test_default_profile_names_undefined_profile_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "missing"

[profile.python]
image = "gleipnir-sandbox:latest"
test = ["true"]
lint = ["true"]
coverage = { unavailable = true, justified = "n/a" }
""",
        )
        with pytest.raises(ProfileError, match="not defined"):
            load_profiles(root)

    def test_resolve_unknown_profile_name_raises(self, tmp_path: Path):
        root = _write(tmp_path, _VALID_TWO_PROFILE_TOML)
        profiles = load_profiles(root)
        with pytest.raises(ProfileError, match="not defined"):
            resolve_profile(profiles, "rust")

    def test_no_profile_tables_at_all_raises(self, tmp_path: Path):
        root = _write(tmp_path, 'default_profile = "python"\n')
        with pytest.raises(ProfileError, match="\\[profile"):
            load_profiles(root)

    def test_verb_with_no_configured_command_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = ["true"]
coverage = { unavailable = true, justified = "n/a" }
""",
        )
        profile = resolve_profile(load_profiles(root), "p")
        with pytest.raises(ProfileError, match="no configured command"):
            command_for(profile, "lint")

    def test_test_value_as_shell_string_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = "python -m pytest"
coverage = { unavailable = true, justified = "n/a" }
""",
        )
        with pytest.raises(ProfileError, match="argv list"):
            load_profiles(root)

    def test_empty_argv_list_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = []
coverage = { unavailable = true, justified = "n/a" }
""",
        )
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_coverage_unavailable_without_justification_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = ["true"]
coverage = { unavailable = true }
""",
        )
        with pytest.raises(ProfileError, match="justified"):
            load_profiles(root)

    def test_coverage_unavailable_with_blank_justification_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = ["true"]
coverage = { unavailable = true, justified = "   " }
""",
        )
        with pytest.raises(ProfileError, match="justified"):
            load_profiles(root)

    def test_coverage_table_missing_entirely_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = ["true"]
""",
        )
        with pytest.raises(ProfileError, match="coverage"):
            load_profiles(root)

    def test_coverage_available_but_args_empty_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = ["true"]
coverage = { args = [] }
""",
        )
        with pytest.raises(ProfileError):
            load_profiles(root)

    def test_profile_entry_not_a_table_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"
profile = { p = "not-a-table" }
""",
        )
        with pytest.raises(ProfileError, match="table"):
            load_profiles(root)

    def test_test_selector_prefix_non_bool_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = "gleipnir-sandbox:latest"
test = ["true"]
coverage = { unavailable = true, justified = "n/a" }
test_selector_prefix = "yes"
""",
        )
        with pytest.raises(ProfileError, match="test_selector_prefix"):
            load_profiles(root)

    def test_image_missing_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
test = ["true"]
coverage = { unavailable = true, justified = "n/a" }
""",
        )
        with pytest.raises(ProfileError, match="image"):
            load_profiles(root)

    def test_image_non_string_raises(self, tmp_path: Path):
        root = _write(
            tmp_path,
            """
default_profile = "p"

[profile.p]
image = 123
test = ["true"]
coverage = { unavailable = true, justified = "n/a" }
""",
        )
        with pytest.raises(ProfileError, match="image"):
            load_profiles(root)
