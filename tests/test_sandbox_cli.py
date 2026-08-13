"""Tests for the S-2 sandbox CLI entrypoint (src/gleipnir/sandbox/__main__.py).

Exercises the config-driven decision logic without a real container: the
argparse surface, the profile-driven `test`/`lint` argv assembly (coverage
first-class for the python profile, honest-degradation for node), and the
fail-closed paths (SandboxError/ProfileError -> exit 3, never host
execution). `_exec` and the runtime edges are monkeypatched so no
podman/docker is required.

Per `.gleipnir/plans/language-agnostic-sandbox.md`: the agent-facing verb
set is exactly `test`/`lint` (exact-match, no widening); `image-build` is a
separate, operator-only subcommand. The config root is injected IN-PROCESS
via `main(argv, config_root=...)` — never a CLI flag, never an env var —
against `tests/fixtures/sandbox_profiles.toml` (the python profile) or a
`tmp_path`-local variant (the node profile, and the fail-closed edge cases).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gleipnir.sandbox import __main__ as cli
from gleipnir.sandbox.profiles import ProfileError
from gleipnir.sandbox.runtime import NoRuntimeError, ImageNotAvailableError

# The tracked regression fixture (`load_profiles` always looks for exactly
# `<config_root>/profiles.toml`; the tracked file is named
# `sandbox_profiles.toml` per the plan's file list, so its TEXT is
# materialized into a `profiles.toml` under a fresh `tmp_path` for each test
# that needs it — never read directly as `config_root`).
_FIXTURE_TOML_TEXT = (Path(__file__).parent / "fixtures" / "sandbox_profiles.toml").read_text()


@pytest.fixture
def captured_exec(monkeypatch):
    """Replace _exec so we capture the argv the CLI would have run, without
    actually spawning a container. Returns a list that gets the argv."""
    calls: list[list[str]] = []

    def fake_exec(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(cli, "_exec", fake_exec)
    return calls


def _write_config(tmp_path: Path, text: str) -> Path:
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "profiles.toml").write_text(text)
    return root


@pytest.fixture
def python_config_root(tmp_path: Path) -> Path:
    """The tracked `python`+`node` regression fixture, materialized as
    `<config_root>/profiles.toml` (default_profile = "python")."""
    return _write_config(tmp_path, _FIXTURE_TOML_TEXT)


_NODE_TOML = """
default_profile = "node"

[profile.node]
image = "gleipnir-sandbox-node@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
test = ["node", "--test", "tests/test_sequence_gate.mjs"]
lint = ["node", "--check", "tests/test_sequence_gate.mjs"]
coverage = { unavailable = true, justified = "node built-in coverage deferred; zero-dep .mjs seam only" }
test_selector_prefix = false
"""


# ---------------------------------------------------------------------------
# Parser: agent-facing verb set does not widen
# ---------------------------------------------------------------------------

def test_parser_requires_a_subcommand():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_parser_accepts_exactly_test_lint_image_build():
    for sub in ("test", "lint", "image-build"):
        args = cli.build_parser().parse_args([sub])
        assert args.subcommand == sub


def test_parser_has_no_build_verb_build_is_renamed():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["build"])


def test_lint_subparser_has_no_image_flag():
    """Image comes SOLELY from the resolved profile on the dispatch path —
    no --image flag exists on `lint` (T2 minor). `lint` has no REMAINDER
    positional, so an unrecognized `--image` is a real parse error."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["lint", "--image", "whatever"])


def test_test_subparser_namespace_has_no_image_attribute():
    """Image comes SOLELY from the resolved profile on the dispatch path —
    there is no dedicated `--image` flag on `test`. A normal parse of
    `test` carries no `image` attribute on the namespace, and `--image` is
    not accepted as a flag at all: argparse rejects it as an unrecognized
    argument (SystemExit 2) rather than silently swallowing it as a
    selector — proof the flag was intentionally removed from the dispatch
    path, not merely left unrecognized-but-tolerated."""
    args = cli.build_parser().parse_args(["test"])
    assert not hasattr(args, "image")
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["test", "--image", "whatever"])


def test_image_build_subcommand_keeps_its_own_image_flag():
    args = cli.build_parser().parse_args(["image-build"])
    assert args.image == cli.SANDBOX_IMAGE


# ---------------------------------------------------------------------------
# `test` command: python profile — coverage first-class, config-driven
# ---------------------------------------------------------------------------

def test_python_profile_test_injects_coverage_and_cache_flags(
    monkeypatch, captured_exec, python_config_root
):
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env=()):
        seen["cmd"] = list(cmd)
        seen["image"] = image
        seen["extra_env"] = list(extra_env)
        return ["podman", "run", "...", *cmd]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    rc = cli.main(["test"], config_root=python_config_root)
    assert rc == 0
    assert seen["image"] == "gleipnir-sandbox:latest"
    assert "--cov=src/gleipnir" in seen["cmd"]
    assert "--cov-branch" in seen["cmd"]
    assert "--cov-report=term-missing" in seen["cmd"]
    assert "no:cacheprovider" in seen["cmd"]
    assert ("COVERAGE_FILE", "/work/.scratch/.coverage") in seen["extra_env"]


def test_python_profile_forwards_extra_pytest_args_as_selectors(
    monkeypatch, captured_exec, python_config_root
):
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env=()):
        seen["cmd"] = list(cmd)
        return ["podman", "run"]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    cli.main(["test", "--", "-k", "bridge"], config_root=python_config_root)
    assert "-k" in seen["cmd"] and "bridge" in seen["cmd"]
    # the configured argv is always the HEAD; selectors are only appended
    assert seen["cmd"][: len(["python", "-m", "pytest", "-p", "no:cacheprovider"])] == [
        "python", "-m", "pytest", "-p", "no:cacheprovider",
    ]


def test_python_profile_lint_runs_configured_command(
    monkeypatch, captured_exec, python_config_root
):
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env=()):
        seen["cmd"] = list(cmd)
        seen["image"] = image
        seen["extra_env"] = list(extra_env)
        return ["podman", "run", *cmd]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    rc = cli.main(["lint"], config_root=python_config_root)
    assert rc == 0
    assert seen["cmd"] == ["python", "-m", "compileall", "-q", "src"]
    assert seen["image"] == "gleipnir-sandbox:latest"
    # D1: compileall's .pyc writes must be redirected off the ro /work mount
    # and into the rw scratch mount, or every file errors with
    # `OSError: [Errno 30] Read-only file system` (the bug this test guards).
    assert ("PYTHONPYCACHEPREFIX", "/work/.scratch/pycache") in seen["extra_env"]


def test_lint_exit_code_propagates_from_exec(monkeypatch, python_config_root):
    """Regression guard: `_cmd_lint` must return exactly whatever `_exec`
    (i.e. `subprocess.run(argv).returncode`) reports for the executed lint
    command — never silently coerced to 0. This locks in the (verified-live,
    already-correct) returncode-propagation path so a future regression that
    swallows a nonzero `compileall` exit — an accidental `or 0`, a dropped
    `return`, a `... | tail`-style code path, or any change that stops
    forwarding `proc.returncode` — fails this test immediately, without
    needing a real container or a real syntax error on disk.

    Deliberately does NOT use the `captured_exec` fixture (which always
    returns 0); it replaces `_exec` per-call so the exit code is the
    independent variable under test.
    """
    monkeypatch.setattr(
        cli, "prepare_sandbox_run", lambda cmd, **k: ["podman", "run", *cmd]
    )

    for code in (0, 1, 3):
        monkeypatch.setattr(cli, "_exec", lambda argv, _code=code: _code)
        rc = cli.main(["lint"], config_root=python_config_root)
        assert rc == code


def test_broker_profile_lint_also_gets_pycache_redirect(monkeypatch, captured_exec, tmp_path):
    """The redirect is set unconditionally in the profile-agnostic `_cmd_lint`
    (D2), so the broker profile's `compileall -q src/gleipnir/broker` lint
    receives it too, with no separate code path."""
    config_root = _write_config(
        tmp_path,
        """
default_profile = "broker"

[profile.broker]
image = "gleipnir-sandbox:latest"
test = ["true"]
lint = ["python", "-m", "compileall", "-q", "src/gleipnir/broker"]
coverage = { unavailable = true, justified = "n/a" }
""",
    )
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env=()):
        seen["cmd"] = list(cmd)
        seen["extra_env"] = list(extra_env)
        return ["podman", "run", *cmd]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    rc = cli.main(["lint"], config_root=config_root)
    assert rc == 0
    assert seen["cmd"] == ["python", "-m", "compileall", "-q", "src/gleipnir/broker"]
    assert ("PYTHONPYCACHEPREFIX", "/work/.scratch/pycache") in seen["extra_env"]


# ---------------------------------------------------------------------------
# `test` command: node profile — right image + right argv, honest coverage
# ---------------------------------------------------------------------------

def test_node_profile_test_selects_node_image_and_command(
    monkeypatch, captured_exec, tmp_path, capsys
):
    config_root = _write_config(tmp_path, _NODE_TOML)
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env=()):
        seen["cmd"] = list(cmd)
        seen["image"] = image
        seen["extra_env"] = list(extra_env)
        return ["podman", "run", image, *cmd]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    rc = cli.main(["test"], config_root=config_root)
    assert rc == 0
    assert seen["image"] == (
        "gleipnir-sandbox-node@sha256:"
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    assert seen["cmd"] == ["node", "--test", "tests/test_sequence_gate.mjs"]
    # no coverage args ever appended for node
    assert not any(c.startswith("--cov") for c in seen["cmd"])
    assert seen["extra_env"] == []
    err = capsys.readouterr().err
    assert "coverage: unavailable (justified:" in err
    assert "zero-dep .mjs seam only" in err


def test_node_profile_never_fabricates_a_coverage_number(
    monkeypatch, captured_exec, tmp_path, capsys
):
    config_root = _write_config(tmp_path, _NODE_TOML)
    monkeypatch.setattr(
        cli, "prepare_sandbox_run",
        lambda cmd, **k: ["podman", "run", *cmd],
    )
    cli.main(["test"], config_root=config_root)
    err = capsys.readouterr().err
    assert "%" not in err.split("coverage: unavailable")[-1].split("\n")[0]


def test_node_profile_refuses_extra_selector_passthrough(
    monkeypatch, captured_exec, tmp_path
):
    config_root = _write_config(tmp_path, _NODE_TOML)
    monkeypatch.setattr(
        cli, "prepare_sandbox_run",
        lambda cmd, **k: pytest.fail("must not run: extra args should refuse first"),
    )
    rc = cli.main(["test", "--", "some-selector"], config_root=config_root)
    assert rc == 3
    assert captured_exec == []


# ---------------------------------------------------------------------------
# Fail-closed: config defects -> exit 3, never runs on host
# ---------------------------------------------------------------------------

def test_missing_config_file_fails_closed(captured_exec, tmp_path):
    rc = cli.main(["test"], config_root=tmp_path / "no-such-dir")
    assert rc == 3
    assert captured_exec == []


def test_malformed_toml_fails_closed(captured_exec, tmp_path):
    config_root = _write_config(tmp_path, "default_profile = [[[ not valid toml")
    rc = cli.main(["test"], config_root=config_root)
    assert rc == 3
    assert captured_exec == []


def test_unpinned_image_fails_closed(captured_exec, tmp_path):
    config_root = _write_config(
        tmp_path,
        """
default_profile = "bad"

[profile.bad]
image = "someimage:latest"
test = ["true"]
lint = ["true"]
coverage = { unavailable = true, justified = "n/a" }
""",
    )
    rc = cli.main(["test"], config_root=config_root)
    assert rc == 3
    assert captured_exec == []


def test_verb_with_no_configured_command_fails_closed(captured_exec, tmp_path):
    config_root = _write_config(
        tmp_path,
        """
default_profile = "nolint"

[profile.nolint]
image = "gleipnir-sandbox:latest"
test = ["true"]
coverage = { unavailable = true, justified = "n/a" }
""",
    )
    rc = cli.main(["lint"], config_root=config_root)
    assert rc == 3
    assert captured_exec == []


def test_profile_error_is_a_sandbox_error_subclass():
    from gleipnir.sandbox.runtime import SandboxError

    assert issubclass(ProfileError, SandboxError)


# ---------------------------------------------------------------------------
# Fail-closed: a SandboxError from runtime -> exit 3, never runs on host
# ---------------------------------------------------------------------------

def test_test_command_fails_closed_on_no_runtime(
    monkeypatch, captured_exec, python_config_root
):
    def raise_no_runtime(*a, **k):
        raise NoRuntimeError("no container runtime found")

    monkeypatch.setattr(cli, "prepare_sandbox_run", raise_no_runtime)
    rc = cli.main(["test"], config_root=python_config_root)
    assert rc == 3
    assert captured_exec == []  # never executed anything


def test_test_command_fails_closed_on_missing_image(
    monkeypatch, captured_exec, python_config_root
):
    def raise_missing(*a, **k):
        raise ImageNotAvailableError("image not built")

    monkeypatch.setattr(cli, "prepare_sandbox_run", raise_missing)
    rc = cli.main(["test"], config_root=python_config_root)
    assert rc == 3
    assert captured_exec == []


def test_lint_command_fails_closed_on_no_runtime(
    monkeypatch, captured_exec, python_config_root
):
    def raise_no_runtime(*a, **k):
        raise NoRuntimeError("no runtime")

    monkeypatch.setattr(cli, "prepare_sandbox_run", raise_no_runtime)
    rc = cli.main(["lint"], config_root=python_config_root)
    assert rc == 3
    assert captured_exec == []


# ---------------------------------------------------------------------------
# `image-build` command (renamed from `build`): never auto-builds from
# test/lint; needs a runtime. Operator-only, off the agent allowlist.
# ---------------------------------------------------------------------------

def test_image_build_command_fails_closed_without_runtime(monkeypatch, captured_exec):
    monkeypatch.setattr(cli, "detect_cri", lambda: None)
    rc = cli.main(["image-build"])
    assert rc == 3
    assert captured_exec == []


def test_image_build_command_assembles_build_argv(monkeypatch, captured_exec, tmp_path):
    monkeypatch.setattr(cli, "detect_cri", lambda: "podman")
    monkeypatch.setattr(cli, "ensure_machine_ready", lambda **k: None)
    (tmp_path / "Containerfile").write_text("FROM scratch\n")
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    rc = cli.main(["image-build"])
    assert rc == 0
    argv = captured_exec[0]
    assert argv[0] == "podman" and "build" in argv and "-t" in argv


def test_image_build_command_fails_if_no_containerfile(monkeypatch, captured_exec, tmp_path):
    monkeypatch.setattr(cli, "detect_cri", lambda: "podman")
    monkeypatch.setattr(cli, "ensure_machine_ready", lambda **k: None)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)  # no Containerfile
    rc = cli.main(["image-build"])
    assert rc == 3
    assert captured_exec == []
