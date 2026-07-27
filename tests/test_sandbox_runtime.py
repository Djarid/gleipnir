"""Tests for the S-2 sandbox CRI-detection / machine-readiness / run-argv logic
(`src/gleipnir/sandbox/runtime.py`).

Spec context: `.gleipnir/plans/s2-sandbox.md` (Assemble step 2 — write these
tests BEFORE the implementation) and
`.gleipnir/plans/s2-sandbox-probe-findings.md` (ground truth: `podman info` is
NOT a readiness signal on macOS; `podman machine list --format json` ->
`Running` is).

Everything here runs on the host with FAKED probes (monkeypatched
`shutil.which` / `subprocess.run`) — no real container runtime is required.

Coverage (per delegation):
  * detect_cri: podman present; podman absent + docker present; neither.
  * machine-readiness parsing: no machine / stopped / running / unparseable
    JSON, all pure and crash-free.
  * run-argv construction: --network=none, ro source, rw+separate scratch,
    no credential/.git/.gleipnir mount, -w /work, pinned image, pytest with
    -p no:cacheprovider.
  * fail-closed orchestration: no CRI -> fail-closed, never a host-exec argv;
    missing image -> actionable error, never a `build` argv.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from gleipnir.sandbox import runtime


# ---------------------------------------------------------------------------
# CRI detection (shutil.which faked)
# ---------------------------------------------------------------------------

def test_detect_cri_prefers_podman_when_both_present(monkeypatch):
    monkeypatch.setattr(
        runtime.shutil, "which",
        lambda name: f"/usr/bin/{name}" if name in ("podman", "docker") else None,
    )
    assert runtime.detect_cri() == "podman"


def test_detect_cri_falls_back_to_docker_when_podman_absent(monkeypatch):
    monkeypatch.setattr(
        runtime.shutil, "which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    assert runtime.detect_cri() == "docker"


def test_detect_cri_none_when_neither_present(monkeypatch):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    assert runtime.detect_cri() is None


def test_detect_cri_is_freshly_detected_each_call(monkeypatch):
    """No caching: flipping the fake `which` between calls changes the result."""
    state = {"podman": True}
    monkeypatch.setattr(
        runtime.shutil, "which",
        lambda name: ("/usr/bin/podman" if state["podman"] else None) if name == "podman" else None,
    )
    assert runtime.detect_cri() == "podman"
    state["podman"] = False
    assert runtime.detect_cri() is None


# ---------------------------------------------------------------------------
# Machine-readiness parsing (pure function over canned JSON — the structured
# `Running` field, never `podman info`, never the connection-error string)
# ---------------------------------------------------------------------------

def test_machine_list_no_machine_means_init():
    decision = runtime.parse_machine_list(json.dumps([]))
    assert decision.ready is False
    assert decision.action == "init"


def test_machine_list_stopped_means_start():
    # Shape matches the probe's real `podman machine list --format json`.
    payload = json.dumps([
        {"Name": "podman-machine-default", "Running": False, "Starting": False}
    ])
    decision = runtime.parse_machine_list(payload)
    assert decision.ready is False
    assert decision.action == "start"


def test_machine_list_running_means_ready():
    payload = json.dumps([
        {"Name": "podman-machine-default", "Running": True, "Starting": False}
    ])
    decision = runtime.parse_machine_list(payload)
    assert decision.ready is True
    assert decision.action is None


def test_machine_list_picks_up_running_machine_among_several():
    payload = json.dumps([
        {"Name": "other", "Running": False},
        {"Name": "podman-machine-default", "Running": True},
    ])
    decision = runtime.parse_machine_list(payload)
    assert decision.ready is True


def test_machine_list_unparseable_json_is_not_ready_and_does_not_crash():
    decision = runtime.parse_machine_list("not json at all {{{")
    assert decision.ready is False
    assert decision.action in ("start", "init")
    assert "unparseable" in decision.reason.lower() or "json" in decision.reason.lower()


def test_machine_list_unexpected_shape_is_not_ready_and_does_not_crash():
    # e.g. a future podman version wraps the list in an object.
    decision = runtime.parse_machine_list(json.dumps({"machines": []}))
    assert decision.ready is False


def test_machine_list_never_consults_podman_info_or_error_string():
    """Ground-truth per the probe: `podman info` returns host data even when
    the machine is stopped, so it must never be the readiness signal, and the
    cryptic connection-error string must never be parsed. Assert the module
    has no such helper at all (it must not exist to be misused)."""
    assert not hasattr(runtime, "parse_podman_info")
    assert not hasattr(runtime, "parse_connection_error")


# ---------------------------------------------------------------------------
# needs_machine_management: only podman + macOS goes through the machine
# dance; docker and Linux rootless podman skip it entirely.
# ---------------------------------------------------------------------------

def test_needs_machine_management_true_for_podman_on_darwin():
    assert runtime.needs_machine_management("podman", "Darwin") is True


def test_needs_machine_management_false_for_docker():
    assert runtime.needs_machine_management("docker", "Darwin") is False


def test_needs_machine_management_false_for_podman_on_linux():
    assert runtime.needs_machine_management("podman", "Linux") is False


# ---------------------------------------------------------------------------
# Run-argv construction (pure; no subprocess involved)
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_and_scratch(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    return repo, scratch


def test_build_run_argv_has_network_none(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    assert "--network=none" in argv


def test_build_run_argv_source_mount_is_read_only(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]
    ro_mounts = [m for m in mounts if m.startswith(f"{repo.resolve()}:")]
    assert ro_mounts, f"no mount found for repo root in {mounts}"
    assert ro_mounts[0].endswith(":/work:ro")


def test_build_run_argv_scratch_mount_is_writable_and_separate(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]
    scratch_mounts = [m for m in mounts if m.startswith(f"{scratch.resolve()}:")]
    assert scratch_mounts, f"no mount found for scratch dir in {mounts}"
    assert scratch_mounts[0].endswith(":/work/.scratch:rw")
    # scratch mount must be a distinct target from the source mount
    assert scratch_mounts[0].split(":")[1:] != [":/work", "ro"]
    assert "/work/.scratch" != "/work"


def test_build_run_argv_never_mounts_credentials_git_or_gleipnir(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    joined = " ".join(argv)
    for forbidden in (".git", ".gleipnir", "credential", "keys/"):
        assert forbidden not in joined, f"forbidden path fragment {forbidden!r} leaked into argv: {argv}"


def test_build_run_argv_workdir_is_work(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    assert "-w" in argv
    assert argv[argv.index("-w") + 1] == "/work"


def test_build_run_argv_sets_pythondontwritebytecode(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    assert "-e" in argv
    assert "PYTHONDONTWRITEBYTECODE=1" in argv


def test_build_run_argv_uses_pinned_image_by_default(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    assert runtime.IMAGE in argv
    assert runtime.IMAGE == "docker.io/library/python:3.12-slim"


def test_build_run_argv_uses_requested_cri_and_rm(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "docker", repo_root=repo, scratch_dir=scratch, cmd=["true"]
    )
    assert argv[0] == "docker"
    assert argv[1] == "run"
    assert "--rm" in argv


def test_build_run_argv_appends_cmd_after_image(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_run_argv(
        "podman", repo_root=repo, scratch_dir=scratch, cmd=["python", "-m", "pytest", "-q"]
    )
    image_idx = argv.index(runtime.IMAGE)
    assert argv[image_idx + 1:] == ["python", "-m", "pytest", "-q"]


def test_build_pytest_argv_uses_no_cacheprovider(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_pytest_argv(
        "podman", repo_root=repo, scratch_dir=scratch, pytest_args=("-q",)
    )
    assert "-p" in argv
    assert "no:cacheprovider" in argv
    assert argv[argv.index("-p") + 1] == "no:cacheprovider"
    assert "-q" in argv


def test_build_pytest_argv_full_shape_matches_plan(repo_and_scratch):
    repo, scratch = repo_and_scratch
    argv = runtime.build_pytest_argv(
        "podman", repo_root=repo, scratch_dir=scratch, pytest_args=("-q",)
    )
    expected = [
        "podman", "run", "--rm", "--network=none",
        "-v", f"{repo.resolve()}:/work:ro",
        "-v", f"{scratch.resolve()}:/work/.scratch:rw",
        "-w", "/work",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        runtime.IMAGE,
        "python", "-m", "pytest", "-p", "no:cacheprovider", "-q",
    ]
    assert argv == expected


# ---------------------------------------------------------------------------
# ensure_machine_ready (thin orchestration; subprocess.run faked)
# ---------------------------------------------------------------------------

def _fake_completed(stdout: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr="")


def test_ensure_machine_ready_noop_for_docker(monkeypatch):
    calls = []
    monkeypatch.setattr(
        runtime.subprocess, "run",
        lambda *a, **k: calls.append(a) or _fake_completed(),
    )
    runtime.ensure_machine_ready(cri="docker", platform_name="Darwin")
    assert calls == []


def test_ensure_machine_ready_noop_for_linux_podman(monkeypatch):
    calls = []
    monkeypatch.setattr(
        runtime.subprocess, "run",
        lambda *a, **k: calls.append(a) or _fake_completed(),
    )
    runtime.ensure_machine_ready(cri="podman", platform_name="Linux")
    assert calls == []


def test_ensure_machine_ready_noop_when_already_running(monkeypatch):
    running_json = json.dumps([{"Name": "podman-machine-default", "Running": True}])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["podman", "machine", "list"]:
            return _fake_completed(stdout=running_json)
        raise AssertionError(f"unexpected command invoked: {argv}")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    runtime.ensure_machine_ready(cri="podman", platform_name="Darwin")
    # only the list check ran; no init/start was needed
    assert calls == [["podman", "machine", "list", "--format", "json"]]


def test_ensure_machine_ready_starts_stopped_machine(monkeypatch):
    stopped_json = json.dumps([{"Name": "podman-machine-default", "Running": False}])
    running_json = json.dumps([{"Name": "podman-machine-default", "Running": True}])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[:3] == ["podman", "machine", "list"]:
            # first check: stopped; after "start" is invoked, report running
            if any(c[:3] == ["podman", "machine", "start"] for c in calls):
                return _fake_completed(stdout=running_json)
            return _fake_completed(stdout=stopped_json)
        if argv[:3] == ["podman", "machine", "start"]:
            return _fake_completed(returncode=0)
        raise AssertionError(f"unexpected command invoked: {argv}")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    runtime.ensure_machine_ready(cri="podman", platform_name="Darwin")
    assert any(c[:3] == ["podman", "machine", "start"] for c in calls)
    assert not any(c[:3] == ["podman", "machine", "init"] for c in calls)


def test_ensure_machine_ready_inits_when_no_machine(monkeypatch):
    empty_json = json.dumps([])
    running_json = json.dumps([{"Name": "podman-machine-default", "Running": True}])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[:3] == ["podman", "machine", "list"]:
            if any(c[:3] == ["podman", "machine", "start"] for c in calls):
                return _fake_completed(stdout=running_json)
            return _fake_completed(stdout=empty_json)
        if argv[:3] in (["podman", "machine", "init"], ["podman", "machine", "start"]):
            return _fake_completed(returncode=0)
        raise AssertionError(f"unexpected command invoked: {argv}")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    runtime.ensure_machine_ready(cri="podman", platform_name="Darwin")
    assert any(c[:3] == ["podman", "machine", "init"] for c in calls)
    assert any(c[:3] == ["podman", "machine", "start"] for c in calls)


def test_ensure_machine_ready_raises_actionable_error_on_start_failure(monkeypatch):
    stopped_json = json.dumps([{"Name": "podman-machine-default", "Running": False}])

    def fake_run(argv, **kwargs):
        if argv[:3] == ["podman", "machine", "list"]:
            return _fake_completed(stdout=stopped_json)
        if argv[:3] == ["podman", "machine", "start"]:
            return _fake_completed(returncode=1, stdout="")
        raise AssertionError(f"unexpected command invoked: {argv}")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    with pytest.raises(runtime.MachineNotReadyError) as exc_info:
        runtime.ensure_machine_ready(cri="podman", platform_name="Darwin")
    assert "podman machine start" in str(exc_info.value)


def test_ensure_machine_ready_never_surfaces_raw_connection_error(monkeypatch):
    """Even if the underlying command raised something resembling the raw
    gRPC/socket error, the resulting message must be the actionable one, not
    the cryptic dial/connection-refused string."""
    stopped_json = json.dumps([{"Name": "podman-machine-default", "Running": False}])

    def fake_run(argv, **kwargs):
        if argv[:3] == ["podman", "machine", "list"]:
            return _fake_completed(stdout=stopped_json)
        if argv[:3] == ["podman", "machine", "start"]:
            return _fake_completed(
                returncode=1,
                stdout="Error: dial tcp 127.0.0.1:52711: connect: connection refused",
            )
        raise AssertionError(f"unexpected command invoked: {argv}")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    with pytest.raises(runtime.MachineNotReadyError) as exc_info:
        runtime.ensure_machine_ready(cri="podman", platform_name="Darwin")
    assert "connection refused" not in str(exc_info.value)
    assert "dial tcp" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Image availability (thin; subprocess.run faked)
# ---------------------------------------------------------------------------

def test_image_available_true_on_zero_exit(monkeypatch):
    monkeypatch.setattr(
        runtime.subprocess, "run",
        lambda *a, **k: _fake_completed(returncode=0),
    )
    assert runtime.image_available("podman", "some:image") is True


def test_image_available_false_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        runtime.subprocess, "run",
        lambda *a, **k: _fake_completed(returncode=1),
    )
    assert runtime.image_available("podman", "some:image") is False


def test_image_available_false_on_missing_binary(monkeypatch):
    def raise_oserror(*a, **k):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(runtime.subprocess, "run", raise_oserror)
    assert runtime.image_available("podman", "some:image") is False


def test_image_available_never_invokes_build(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return _fake_completed(returncode=0)

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    runtime.image_available("podman", "some:image")
    assert not any("build" in c for c in calls)


# ---------------------------------------------------------------------------
# Fail-closed top-level orchestration (prepare_sandbox_run / prepare_pytest_run)
# ---------------------------------------------------------------------------

def test_prepare_sandbox_run_raises_when_no_cri_and_never_returns_argv(monkeypatch, repo_and_scratch):
    repo, scratch = repo_and_scratch
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    with pytest.raises(runtime.NoRuntimeError):
        runtime.prepare_sandbox_run(
            ["true"], repo_root=repo, scratch_dir=scratch, platform_name="Linux"
        )


def test_prepare_sandbox_run_no_cri_error_states_fail_closed_intent(monkeypatch, repo_and_scratch):
    repo, scratch = repo_and_scratch
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    try:
        runtime.prepare_sandbox_run(
            ["true"], repo_root=repo, scratch_dir=scratch, platform_name="Linux"
        )
        pytest.fail("expected NoRuntimeError")
    except runtime.NoRuntimeError as exc:
        msg = str(exc).lower()
        assert "never" in msg
        assert "podman" in msg or "docker" in msg


def test_prepare_sandbox_run_missing_image_raises_actionable_and_never_builds(monkeypatch, repo_and_scratch):
    repo, scratch = repo_and_scratch
    monkeypatch.setattr(
        runtime.shutil, "which",
        lambda name: "/usr/bin/podman" if name == "podman" else None,
    )
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        # image inspect fails -> image not available
        return _fake_completed(returncode=1)

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    with pytest.raises(runtime.ImageNotAvailableError) as exc_info:
        runtime.prepare_sandbox_run(
            ["true"], repo_root=repo, scratch_dir=scratch, platform_name="Linux"
        )
    assert "build" in str(exc_info.value).lower()
    assert not any(c and c[1] == "build" for c in calls)


def test_prepare_sandbox_run_returns_valid_argv_on_success(monkeypatch, repo_and_scratch):
    repo, scratch = repo_and_scratch
    monkeypatch.setattr(
        runtime.shutil, "which",
        lambda name: "/usr/bin/podman" if name == "podman" else None,
    )

    def fake_run(argv, **kwargs):
        return _fake_completed(returncode=0)

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    argv = runtime.prepare_sandbox_run(
        ["true"], repo_root=repo, scratch_dir=scratch, platform_name="Linux"
    )
    assert argv[0] == "podman"
    assert "--network=none" in argv


def test_prepare_pytest_run_builds_expected_argv(monkeypatch, repo_and_scratch):
    repo, scratch = repo_and_scratch
    monkeypatch.setattr(
        runtime.shutil, "which",
        lambda name: "/usr/bin/podman" if name == "podman" else None,
    )
    monkeypatch.setattr(
        runtime.subprocess, "run",
        lambda *a, **k: _fake_completed(returncode=0),
    )
    argv = runtime.prepare_pytest_run(
        repo_root=repo, scratch_dir=scratch, pytest_args=("-q",), platform_name="Linux"
    )
    assert argv[-6:] == ["python", "-m", "pytest", "-p", "no:cacheprovider", "-q"]
