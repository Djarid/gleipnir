"""Gleipnir S-2 execution sandbox — CRI detection, machine readiness, run-argv.

Spec context: `.gleipnir/plans/s2-sandbox.md`. This package is Trace item (b):
the stdlib-only detection/machine-ensure/run logic that the thin
`bin/gleipnir-sandbox` shim (a later, separate artifact) will `exec` into. It
is deliberately scoped to *decision logic*, kept pure and unit-testable with
faked probes; the real container invocation is a thin edge (`subprocess.run`)
around that logic, never the other way around.

Nothing here mounts credentials, `.git/`, or `.gleipnir/`; nothing here falls
back to host execution; nothing here auto-builds the sandbox image. Those are
the fail-closed properties the tests in `tests/test_sandbox_runtime.py` pin
down.
"""

from .runtime import (
    IMAGE,
    WORKDIR,
    ImageNotAvailableError,
    MachineDecision,
    MachineNotReadyError,
    NoRuntimeError,
    SandboxError,
    build_pytest_argv,
    build_run_argv,
    detect_cri,
    ensure_machine_ready,
    image_available,
    needs_machine_management,
    parse_machine_list,
    prepare_pytest_run,
    prepare_sandbox_run,
)

__all__ = [
    "IMAGE",
    "WORKDIR",
    "ImageNotAvailableError",
    "MachineDecision",
    "MachineNotReadyError",
    "NoRuntimeError",
    "SandboxError",
    "build_pytest_argv",
    "build_run_argv",
    "detect_cri",
    "ensure_machine_ready",
    "image_available",
    "needs_machine_management",
    "parse_machine_list",
    "prepare_pytest_run",
    "prepare_sandbox_run",
]
