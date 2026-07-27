"""Tests for the S-2 sandbox CLI entrypoint (src/gleipnir/sandbox/__main__.py).

Exercises the decision logic without a real container: the argparse surface,
the coverage-first-class `test` command's argv assembly, and the fail-closed
paths (SandboxError -> exit 3, never host execution). `_exec` and the
runtime edges are monkeypatched so no podman/docker is required.
"""

from __future__ import annotations

import pytest

from gleipnir.sandbox import __main__ as cli
from gleipnir.sandbox.runtime import NoRuntimeError, ImageNotAvailableError


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


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_parser_requires_a_subcommand():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_parser_accepts_test_lint_build():
    for sub in ("test", "lint", "build"):
        args = cli.build_parser().parse_args([sub])
        assert args.subcommand == sub


def test_image_defaults_to_sandbox_image():
    args = cli.build_parser().parse_args(["test"])
    assert args.image == cli.SANDBOX_IMAGE


# ---------------------------------------------------------------------------
# `test` command: coverage is first-class in the assembled pytest command
# ---------------------------------------------------------------------------

def test_test_command_injects_coverage_and_cache_flags(monkeypatch, captured_exec):
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env):
        seen["cmd"] = list(cmd)
        seen["extra_env"] = list(extra_env)
        return ["podman", "run", "...", *cmd]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    rc = cli.main(["test"])
    assert rc == 0
    # coverage flags present (line+branch+term-missing), first-class
    assert "--cov=src/gleipnir" in seen["cmd"]
    assert "--cov-branch" in seen["cmd"]
    assert "--cov-report=term-missing" in seen["cmd"]
    # ro-mount hygiene flags
    assert "no:cacheprovider" in seen["cmd"]
    # COVERAGE_FILE routed into the rw scratch mount, not the ro source
    assert ("COVERAGE_FILE", "/work/.scratch/.coverage") in seen["extra_env"]


def test_test_command_forwards_extra_pytest_args(monkeypatch, captured_exec):
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image, extra_env):
        seen["cmd"] = list(cmd)
        return ["podman", "run"]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    cli.main(["test", "--", "-k", "bridge"])
    assert "-k" in seen["cmd"] and "bridge" in seen["cmd"]


# ---------------------------------------------------------------------------
# Fail-closed: a SandboxError from runtime -> exit 3, never runs on host
# ---------------------------------------------------------------------------

def test_test_command_fails_closed_on_no_runtime(monkeypatch, captured_exec):
    def raise_no_runtime(*a, **k):
        raise NoRuntimeError("no container runtime found")

    monkeypatch.setattr(cli, "prepare_sandbox_run", raise_no_runtime)
    rc = cli.main(["test"])
    assert rc == 3
    assert captured_exec == []  # never executed anything


def test_test_command_fails_closed_on_missing_image(monkeypatch, captured_exec):
    def raise_missing(*a, **k):
        raise ImageNotAvailableError("image not built")

    monkeypatch.setattr(cli, "prepare_sandbox_run", raise_missing)
    rc = cli.main(["test"])
    assert rc == 3
    assert captured_exec == []


def test_lint_command_fails_closed_on_no_runtime(monkeypatch, captured_exec):
    def raise_no_runtime(*a, **k):
        raise NoRuntimeError("no runtime")

    monkeypatch.setattr(cli, "prepare_sandbox_run", raise_no_runtime)
    rc = cli.main(["lint"])
    assert rc == 3
    assert captured_exec == []


def test_lint_command_runs_compileall(monkeypatch, captured_exec):
    seen = {}

    def fake_prepare(cmd, *, repo_root, scratch_dir, image):
        seen["cmd"] = list(cmd)
        return ["podman", "run", *cmd]

    monkeypatch.setattr(cli, "prepare_sandbox_run", fake_prepare)
    rc = cli.main(["lint"])
    assert rc == 0
    assert "compileall" in seen["cmd"]


# ---------------------------------------------------------------------------
# `build` command: never auto-builds from test/lint; needs a runtime
# ---------------------------------------------------------------------------

def test_build_command_fails_closed_without_runtime(monkeypatch, captured_exec):
    monkeypatch.setattr(cli, "detect_cri", lambda: None)
    rc = cli.main(["build"])
    assert rc == 3
    assert captured_exec == []


def test_build_command_assembles_build_argv(monkeypatch, captured_exec, tmp_path):
    monkeypatch.setattr(cli, "detect_cri", lambda: "podman")
    monkeypatch.setattr(cli, "ensure_machine_ready", lambda **k: None)
    # point _repo_root at a tmp repo that has a Containerfile
    (tmp_path / "Containerfile").write_text("FROM scratch\n")
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    rc = cli.main(["build"])
    assert rc == 0
    argv = captured_exec[0]
    assert argv[0] == "podman" and "build" in argv and "-t" in argv


def test_build_command_fails_if_no_containerfile(monkeypatch, captured_exec, tmp_path):
    monkeypatch.setattr(cli, "detect_cri", lambda: "podman")
    monkeypatch.setattr(cli, "ensure_machine_ready", lambda **k: None)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)  # no Containerfile
    rc = cli.main(["build"])
    assert rc == 3
    assert captured_exec == []
