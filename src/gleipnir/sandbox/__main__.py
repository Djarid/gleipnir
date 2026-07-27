"""S-2 sandbox CLI entrypoint (invoked by `bin/gleipnir-sandbox`).

Subcommands the agent's allowlist grants (exact-match, no wildcard):

    gleipnir-sandbox test    run the full suite in-container, WITH coverage
    gleipnir-sandbox lint    run the lint (compile) check in-container
    gleipnir-sandbox build   build the sandbox image (operator/bootstrap only)

`test` is coverage-first-class: it runs pytest inside the container with
``--cov=src/gleipnir --cov-branch --cov-report=term-missing`` plus the
``-p no:cacheprovider`` the read-only mount requires, and prints BOTH the pass
count and the line+branch coverage totals (pytest-cov's own summary). The 85%
target is a reported/justify-below discipline (not yet a hard exit failure); the
run's exit code reflects test pass/fail, and coverage is surfaced for the
operator/quality stage to act on.

Everything dangerous is delegated to ``runtime.py``'s fail-closed orchestration:
no CRI, an unready machine, or a missing image all refuse with an actionable
message and never fall back to host execution or auto-build.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .runtime import (
    IMAGE,
    SCRATCH_SUBPATH,
    SandboxError,
    detect_cri,
    ensure_machine_ready,
    image_available,
    prepare_sandbox_run,
)

# The image the entrypoint runs against. The Containerfile builds this tag with
# pytest + pytest-cov pre-installed, so `test`/`lint` runs need no network
# (`--network=none`) and no runtime pip install. Overridable via --image for
# bootstrapping against the raw base.
SANDBOX_IMAGE = "gleipnir-sandbox:latest"

# Coverage is a first-class output of `test` (operator policy): line + branch,
# reported every run, 85% target/justify-below.
_COVERAGE_ARGS = [
    "--cov=src/gleipnir",
    "--cov-branch",
    "--cov-report=term-missing",
]


def _repo_root() -> Path:
    # src/gleipnir/sandbox/__main__.py -> repo root is three parents up from
    # the package dir. Resolve so the mount path is absolute.
    return Path(__file__).resolve().parents[3]


def _scratch_dir(repo_root: Path) -> Path:
    scratch = repo_root / ".gleipnir" / "var" / "run" / SCRATCH_SUBPATH
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def _exec(argv: list[str]) -> int:
    """Run a prepared argv, streaming output; return its exit code."""
    print("gleipnir-sandbox:", " ".join(argv), file=sys.stderr)
    proc = subprocess.run(argv)
    return proc.returncode


def _cmd_test(args: argparse.Namespace) -> int:
    repo = _repo_root()
    pytest_cmd = [
        "python",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        *_COVERAGE_ARGS,
        *args.pytest_args,
    ]
    try:
        argv = prepare_sandbox_run(
            pytest_cmd,
            repo_root=repo,
            scratch_dir=_scratch_dir(repo),
            image=args.image,
            # coverage's SQLite data file must land in the rw scratch mount,
            # not the ro source at /work (probe finding, coverage variant).
            extra_env=[("COVERAGE_FILE", "/work/.scratch/.coverage")],
        )
    except SandboxError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3  # fail-closed: refused, never ran on host
    return _exec(argv)


def _cmd_lint(args: argparse.Namespace) -> int:
    repo = _repo_root()
    # compile every source file to catch syntax errors; runs in-container
    lint_cmd = ["python", "-m", "compileall", "-q", "src"]
    try:
        argv = prepare_sandbox_run(
            lint_cmd,
            repo_root=repo,
            scratch_dir=_scratch_dir(repo),
            image=args.image,
        )
    except SandboxError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3
    return _exec(argv)


def _cmd_build(args: argparse.Namespace) -> int:
    """Build the sandbox image. Operator/bootstrap action — this is the ONE
    place a build happens, invoked deliberately, never auto-triggered by test/
    lint (runtime.py refuses to build)."""
    repo = _repo_root()
    cri = detect_cri()
    if cri is None:
        print(
            "gleipnir-sandbox: no container runtime (podman/docker) found; "
            "cannot build.",
            file=sys.stderr,
        )
        return 3
    try:
        ensure_machine_ready(cri=cri)
    except SandboxError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3
    containerfile = repo / "Containerfile"
    if not containerfile.is_file():
        print(
            f"gleipnir-sandbox: Containerfile not found at {containerfile}",
            file=sys.stderr,
        )
        return 3
    argv = [
        cri,
        "build",
        "-t",
        args.image,
        "-f",
        str(containerfile),
        str(repo),
    ]
    return _exec(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gleipnir-sandbox")
    parser.add_argument(
        "--image",
        default=SANDBOX_IMAGE,
        help=f"sandbox image tag (default: {SANDBOX_IMAGE})",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_test = sub.add_parser("test", help="run the full suite in-container with coverage")
    p_test.add_argument("pytest_args", nargs=argparse.REMAINDER)
    p_test.set_defaults(func=_cmd_test)

    p_lint = sub.add_parser("lint", help="run the compile/lint check in-container")
    p_lint.set_defaults(func=_cmd_lint)

    p_build = sub.add_parser("build", help="build the sandbox image (operator/bootstrap)")
    p_build.set_defaults(func=_cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "pytest_args", None) and args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
