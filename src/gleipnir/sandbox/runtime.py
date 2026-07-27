"""S-2 sandbox — CRI detection, macOS/podman machine readiness, run-argv.

Spec (`.gleipnir/plans/s2-sandbox.md`, Trace item (b), Link 5, Assemble steps
2-3) and ground truth (`.gleipnir/plans/s2-sandbox-probe-findings.md`):

  * **Detection** is fresh on every call (`shutil.which`), never cached, never
    hardcoded: prefer podman, then docker, else fail-closed. No other CRI is
    added here; `needs_machine_management` documents the platform boundary
    instead of guessing at future runtimes.
  * **Readiness** (macOS/podman only) is decided from the *structured*
    `podman machine list --format json` -> `Running` field. `podman info` is
    never consulted for readiness — the probe proved it returns host data
    even with the machine stopped — and the cryptic
    ``dial tcp ...: connection refused`` string is never parsed (the G-4a
    prose-parsing anti-pattern). The three deterministic cases: no machine
    (`init` then `start`), machine exists but stopped (`start`), machine
    running (proceed).
  * **Run-argv** is a pure function: `--network=none` (no egress ever, for a
    test run), source mounted `:ro`, a *separate* scratch dir mounted `:rw`
    for pytest's cache/`__pycache__`, `-w /work`,
    `PYTHONDONTWRITEBYTECODE=1`, and the pinned base image validated by the
    probe. Nothing under `.git/`, `.gleipnir/`, or any credential path is
    ever referenced.
  * **Orchestration is fail-closed**: no CRI -> raise, never fall back to
    host execution. Missing/stale image -> raise with an actionable
    "operator must build it" message; this module never invokes
    `<cri> build` itself — that would hand the calling agent transitive
    build capability every time it runs a test.

All decision logic (`detect_cri`, `parse_machine_list`,
`needs_machine_management`, `build_run_argv`, `build_pytest_argv`) is pure and
unit-testable without a real container runtime. `ensure_machine_ready` and
`image_available` are the thin edges that call `subprocess.run`; tests fake
that call rather than requiring podman/docker to be installed.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# The base image validated by the S-2 probe (see probe findings: pulls under
# podman, small, Python 3.12.13, pytest installs quickly in-image). Pinning by
# digest and pre-installing pytest into a custom `gleipnir-sandbox` image are
# the later, out-of-scope-here Containerfile step (Trace item (a)).
IMAGE = "docker.io/library/python:3.12-slim"

# In-container workdir for the ro source mount; the rw scratch mount lives
# underneath it so pytest's cache/`__pycache__` writes never touch the ro
# mount (probe finding: this combination gives a clean run, no
# PytestCacheWarning).
WORKDIR = "/work"
SCRATCH_SUBPATH = ".scratch"

# CRI detection order (canonical, per plan Link 5 / Assemble). Fresh every
# call; never cached, never hardcoded past this tuple.
_CRI_CANDIDATES: tuple[str, ...] = ("podman", "docker")

_MACHINE_LIST_ARGV = ["podman", "machine", "list", "--format", "json"]


class SandboxError(Exception):
    """Base for all sandbox faults. Every fault here is fail-closed: no
    sandbox fault ever falls back to running anything on the host."""


class NoRuntimeError(SandboxError):
    """No usable container runtime was detected. Never fall back to host
    execution — refuse and report."""


class MachineNotReadyError(SandboxError):
    """The podman machine could not be confirmed running (or could not be
    started/initialized). Carries an actionable message naming the exact
    command the operator should run; never the raw connection error."""


class ImageNotAvailableError(SandboxError):
    """The sandbox image is missing or could not be confirmed present. Never
    auto-built — carries an actionable "operator must build it" message."""


# ---------------------------------------------------------------------------
# 1. CRI detection
# ---------------------------------------------------------------------------

def detect_cri() -> str | None:
    """Detect the container runtime, fresh on every call.

    Prefers podman, then docker, else ``None``. Presence only (`which`); this
    function makes no judgment about whether the runtime is *ready* to run
    containers — see `needs_machine_management` / `ensure_machine_ready` for
    that, which is a separate, macOS/podman-specific concern.
    """

    for name in _CRI_CANDIDATES:
        if shutil.which(name):
            return name
    return None


# ---------------------------------------------------------------------------
# 2. Machine readiness (macOS/podman) — pure parsing over structured JSON
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MachineDecision:
    """The result of parsing `podman machine list --format json`.

    ``ready`` is True only when a machine reports `Running: true`. ``action``
    names what to do when not ready: ``"init"`` (no machine exists — init
    then start), ``"start"`` (a machine exists but is stopped, or the probe
    output could not be confidently parsed), or ``None`` when ``ready`` is
    True. ``reason`` is a short, human-safe explanation — never the raw
    connection-error string.
    """

    ready: bool
    action: str | None
    reason: str


def parse_machine_list(list_output: str) -> MachineDecision:
    """Pure function: decide machine readiness from `machine list` JSON.

    Never consults `podman info` (the probe proved it returns host data even
    with the machine stopped) and never parses the connection-error string
    (the G-4a prose-parsing anti-pattern) — both are structurally absent from
    this module, not merely avoided by discipline.

    Handles the three deterministic cases from the plan, plus a fail-closed
    default for anything unparseable/unexpected so a future podman version's
    output shape cannot crash this function:

      * empty list (no machine)              -> not ready, action "init"
      * a machine with `Running: false`       -> not ready, action "start"
      * a machine with `Running: true`        -> ready, action None
      * unparseable JSON / unexpected shape   -> not ready, action "start"
        (treated as "not confirmed running"; attempt a start rather than
        guess at init, since the far more common real-world case, per the
        probe, is an existing-but-stopped machine)
    """

    try:
        data = json.loads(list_output)
    except (ValueError, TypeError) as exc:
        return MachineDecision(
            ready=False,
            action="start",
            reason=f"unparseable `podman machine list` output ({exc}); "
            "treating as not confirmed running",
        )

    if not isinstance(data, list):
        return MachineDecision(
            ready=False,
            action="start",
            reason="unexpected `podman machine list` output shape "
            "(expected a JSON list); treating as not confirmed running",
        )

    if len(data) == 0:
        return MachineDecision(
            ready=False, action="init", reason="no podman machine exists"
        )

    for entry in data:
        if isinstance(entry, dict) and entry.get("Running") is True:
            return MachineDecision(
                ready=True, action=None, reason="podman machine is running"
            )

    return MachineDecision(
        ready=False,
        action="start",
        reason="podman machine exists but is not running",
    )


def needs_machine_management(cri: str, platform_name: str) -> bool:
    """Only podman on macOS goes through the machine init/start dance.

    Docker (any platform) and rootless podman on Linux run containers
    directly, no VM step. This function is the platform boundary the rest of
    the module keys off, kept explicit and pure so it does not silently grow
    to cover a future CRI by accident.
    """

    return cri == "podman" and platform_name == "Darwin"


def _run_machine_subcommand(subcommand: str, human_name: str) -> None:
    """Thin edge: invoke `podman machine <subcommand>`; translate any
    failure into an actionable `MachineNotReadyError`, never the raw
    stdout/stderr (which may contain the cryptic connection-refused string)."""

    argv = ["podman", "machine", subcommand]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    except OSError as exc:
        raise MachineNotReadyError(
            f"failed to invoke `{human_name}`: {exc}; "
            f"run `{human_name}` manually and retry"
        ) from exc
    if proc.returncode != 0:
        raise MachineNotReadyError(
            f"`{human_name}` failed (exit {proc.returncode}); "
            f"run `{human_name}` manually, inspect the output, and retry"
        )


def _get_machine_list_json() -> str:
    """Thin edge: run `podman machine list --format json`, return stdout."""

    proc = subprocess.run(
        list(_MACHINE_LIST_ARGV), capture_output=True, text=True, timeout=30
    )
    return proc.stdout


def ensure_machine_ready(
    cri: str = "podman", platform_name: str | None = None
) -> None:
    """Ensure the podman machine is running, or raise an actionable error.

    No-op for docker, and for podman on non-Darwin platforms (rootless Linux
    needs no machine). On Darwin with podman, follows the three deterministic
    cases from `parse_machine_list`:

      * ``ready`` -> return immediately.
      * ``action == "init"`` -> `podman machine init` then `start`.
      * ``action == "start"`` -> `podman machine start`.

    After acting, re-checks the machine list once; if still not ready, raises
    `MachineNotReadyError` with an actionable message. Never surfaces a raw
    connection error.
    """

    platform_name = platform_name if platform_name is not None else platform.system()
    if not needs_machine_management(cri, platform_name):
        return

    decision = parse_machine_list(_get_machine_list_json())
    if decision.ready:
        return

    if decision.action == "init":
        _run_machine_subcommand("init", "podman machine init")
        _run_machine_subcommand("start", "podman machine start")
    elif decision.action == "start":
        _run_machine_subcommand("start", "podman machine start")
    else:  # pragma: no cover - parse_machine_list never returns other values
        raise MachineNotReadyError(
            "podman machine state could not be determined; "
            "run `podman machine start` manually and retry"
        )

    recheck = parse_machine_list(_get_machine_list_json())
    if not recheck.ready:
        raise MachineNotReadyError(
            "podman machine did not report Running:true after "
            "init/start; run `podman machine start` manually, inspect "
            "the output, and retry"
        )


# ---------------------------------------------------------------------------
# 3. Run-argv construction (pure)
# ---------------------------------------------------------------------------

def build_run_argv(
    cri: str,
    *,
    repo_root: str | Path,
    scratch_dir: str | Path,
    cmd: Sequence[str],
    image: str = IMAGE,
) -> list[str]:
    """Build the argv to run `cmd` inside the sandbox. Pure — no subprocess.

    Layout (per plan Trace item (d) / mount layout):
      * source repo   -> `:ro` at `/work` (agent-authored tests must not
        mutate the code they test)
      * scratch dir   -> `:rw` at `/work/.scratch`, a *separate* mount from
        the ro source so pytest's cache/`__pycache__` never touches ro
      * `--network=none` -> no egress by default, ever
      * `-w /work`, `PYTHONDONTWRITEBYTECODE=1`
      * never references `.git/`, `.gleipnir/`, or any credential path —
        those are simply absent from this argv by construction
    """

    repo_root = Path(repo_root).resolve()
    scratch_dir = Path(scratch_dir).resolve()
    scratch_target = f"{WORKDIR}/{SCRATCH_SUBPATH}"

    return [
        cri,
        "run",
        "--rm",
        "--network=none",
        "-v",
        f"{repo_root}:{WORKDIR}:ro",
        "-v",
        f"{scratch_dir}:{scratch_target}:rw",
        "-w",
        WORKDIR,
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        image,
        *cmd,
    ]


def build_pytest_argv(
    cri: str,
    *,
    repo_root: str | Path,
    scratch_dir: str | Path,
    image: str = IMAGE,
    pytest_args: Sequence[str] = ("-q",),
) -> list[str]:
    """Build the argv to run the whole suite inside the sandbox.

    Always includes `-p no:cacheprovider` (probe: this, plus
    `PYTHONDONTWRITEBYTECODE=1` from `build_run_argv`, gives a clean run with
    no `PytestCacheWarning` from the ro source mount).
    """

    cmd = ["python", "-m", "pytest", "-p", "no:cacheprovider", *pytest_args]
    return build_run_argv(
        cri, repo_root=repo_root, scratch_dir=scratch_dir, cmd=cmd, image=image
    )


# ---------------------------------------------------------------------------
# Image availability (thin edge; never builds)
# ---------------------------------------------------------------------------

def image_available(cri: str, image: str = IMAGE) -> bool:
    """Check whether `image` is already present, without ever building it.

    Uses `<cri> image inspect <image>` (supported by both podman and docker)
    and treats any nonzero exit, or the binary being unreachable, as "not
    available" — fail-closed toward "you must build it", never toward
    silently building it here.
    """

    try:
        proc = subprocess.run(
            [cri, "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except OSError:
        return False
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# 4. Fail-closed orchestration
# ---------------------------------------------------------------------------

def prepare_sandbox_run(
    cmd: Sequence[str],
    *,
    repo_root: str | Path,
    scratch_dir: str | Path,
    image: str = IMAGE,
    platform_name: str | None = None,
) -> list[str]:
    """Tie detection + readiness + image-check + argv-construction together.

    Fail-closed at every step; never returns an argv that would run on the
    host, and never returns an argv when the image is missing:

      1. `detect_cri()` -> `None` raises `NoRuntimeError` (no host fallback).
      2. `ensure_machine_ready()` -> raises `MachineNotReadyError` with an
         actionable message on failure.
      3. `image_available()` -> `False` raises `ImageNotAvailableError` with
         an actionable "operator must build it" message; this function never
         invokes `<cri> build`.
      4. Only then is `build_run_argv` called and its result returned.
    """

    cri = detect_cri()
    if cri is None:
        raise NoRuntimeError(
            "no container runtime found (checked: "
            + ", ".join(_CRI_CANDIDATES)
            + "); install podman or docker. This never falls back to "
            "running on the host."
        )

    ensure_machine_ready(cri=cri, platform_name=platform_name)

    if not image_available(cri, image):
        raise ImageNotAvailableError(
            f"sandbox image '{image}' is not available; the operator must "
            f"build it (e.g. `bin/gleipnir-sandbox build` or "
            f"`{cri} build -t gleipnir-sandbox .`). This tool never builds "
            "images automatically."
        )

    return build_run_argv(
        cri, repo_root=repo_root, scratch_dir=scratch_dir, cmd=list(cmd), image=image
    )


def prepare_pytest_run(
    *,
    repo_root: str | Path,
    scratch_dir: str | Path,
    image: str = IMAGE,
    pytest_args: Sequence[str] = ("-q",),
    platform_name: str | None = None,
) -> list[str]:
    """`prepare_sandbox_run`, specialized to a full-suite pytest invocation."""

    cmd = ["python", "-m", "pytest", "-p", "no:cacheprovider", *pytest_args]
    return prepare_sandbox_run(
        cmd,
        repo_root=repo_root,
        scratch_dir=scratch_dir,
        image=image,
        platform_name=platform_name,
    )
