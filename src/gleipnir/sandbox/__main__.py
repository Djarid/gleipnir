"""S-2 sandbox CLI entrypoint (invoked by `bin/gleipnir-sandbox`).

Subcommands the agent's allowlist grants (exact-match, no wildcard):

    gleipnir-sandbox test    run the target project's test command in-container
    gleipnir-sandbox lint    run the target project's lint command in-container

`image-build` (operator/bootstrap only, OFF the agent allowlist) builds the
sandbox image — see `_cmd_image_build`.

**Config-driven dispatch (`.gleipnir/plans/language-agnostic-sandbox.md`).**
`test`/`lint` no longer hard-wire a command or an image: both are read from
the Tier-3, agent-unwritable profile config
(`src/gleipnir/sandbox/profiles.py::load_profiles`), resolved to the
`default_profile`, and dispatched. The configured argv is ALWAYS the command
HEAD; any extra passthrough tokens (`test -- <selectors>`) are constrained to
test SELECTORS ONLY and are refused outright on a profile that does not
declare `test_selector_prefix = true` — the agent can influence *which*
tests run, never *what command* runs. `image` comes SOLELY from the
resolved profile (`profile.image`) — there is no `--image` flag and no
`SANDBOX_IMAGE` constant read on this dispatch path.

The config location is FIXED to the Tier-3 path in production
(`<repo>/.gleipnir/sandbox`), computed internally — never overridable via a
CLI flag or an environment variable. The `config_root` parameter threaded
through `main()`/`_cmd_test`/`_cmd_lint` is an IN-PROCESS TEST-HARNESS SEAM
ONLY (tests call `main(argv, config_root=...)` directly); it is never
reachable from the agent-facing `bin/gleipnir-sandbox test|lint` invocation.

Everything dangerous is delegated to ``runtime.py``'s fail-closed
orchestration: no CRI, an unready machine, or a missing image all refuse
with an actionable message and never fall back to host execution or
auto-build. Every profile-config defect (`ProfileError`, a `SandboxError`
subclass) is caught by the same `except SandboxError` path and maps to the
same fail-closed exit 3 — never a silent default command.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .profiles import ProfileError, command_for, load_profiles, resolve_profile
from .runtime import (
    SCRATCH_SUBPATH,
    SandboxError,
    detect_cri,
    ensure_machine_ready,
    image_available,
    prepare_sandbox_run,
)

# Used ONLY by the operator-only `image-build` bootstrap subcommand (never on
# the agent-facing test/lint dispatch path, where `image` comes solely from
# the resolved profile).
SANDBOX_IMAGE = "gleipnir-sandbox:latest"


def _repo_root() -> Path:
    # src/gleipnir/sandbox/__main__.py -> repo root is three parents up from
    # the package dir. Resolve so the mount path is absolute.
    return Path(__file__).resolve().parents[3]


def _default_config_root(repo: Path) -> Path:
    # Fixed Tier-3 production location, computed internally — never taken
    # from a CLI flag or an environment variable.
    return repo / ".gleipnir" / "sandbox"


def _scratch_dir(repo: Path) -> Path:
    scratch = repo / ".gleipnir" / "var" / "run" / SCRATCH_SUBPATH
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def _exec(argv: list[str]) -> int:
    """Run a prepared argv, streaming output; return its exit code."""
    print("gleipnir-sandbox:", " ".join(argv), file=sys.stderr)
    proc = subprocess.run(argv)
    return proc.returncode


def _resolve_dispatch_profile(repo: Path, config_root: Path | None):
    """Load + resolve the `default_profile` from the (fixed-in-production,
    injectable-in-tests) config root. Raises `ProfileError` on any defect —
    callers map this to exit 3, never a silent default."""

    root = config_root if config_root is not None else _default_config_root(repo)
    profiles = load_profiles(root)
    return resolve_profile(profiles)


def _cmd_test(args: argparse.Namespace, *, config_root: Path | None = None) -> int:
    repo = _repo_root()
    try:
        profile = _resolve_dispatch_profile(repo, config_root)
        base_cmd = command_for(profile, "test")
    except ProfileError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3  # fail-closed: refused, never ran on host

    extra = list(args.pytest_args)
    if extra and not profile.test_selector_prefix:
        print(
            f"gleipnir-sandbox: profile {profile.name!r} does not support "
            "extra test-selector passthrough; refusing rather than "
            f"forwarding {extra!r} into the command root",
            file=sys.stderr,
        )
        return 3

    coverage_args: list[str] = []
    extra_env: list[tuple[str, str]] = []
    if profile.coverage.unavailable:
        print(
            f"coverage: unavailable (justified: {profile.coverage.justified})",
            file=sys.stderr,
        )
    else:
        coverage_args = list(profile.coverage.args)
        if profile.coverage.file_env and profile.coverage.file_path:
            # coverage's data file must land in the rw scratch mount, not
            # the ro source at /work (probe finding, coverage variant).
            extra_env.append((profile.coverage.file_env, profile.coverage.file_path))

    test_cmd = [*base_cmd, *coverage_args, *extra]

    try:
        argv = prepare_sandbox_run(
            test_cmd,
            repo_root=repo,
            scratch_dir=_scratch_dir(repo),
            image=profile.image,
            extra_env=extra_env,
        )
    except SandboxError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3  # fail-closed: refused, never ran on host
    return _exec(argv)


def _cmd_lint(args: argparse.Namespace, *, config_root: Path | None = None) -> int:
    repo = _repo_root()
    try:
        profile = _resolve_dispatch_profile(repo, config_root)
        lint_cmd = list(command_for(profile, "lint"))
    except ProfileError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3

    try:
        argv = prepare_sandbox_run(
            lint_cmd,
            repo_root=repo,
            scratch_dir=_scratch_dir(repo),
            image=profile.image,
        )
    except SandboxError as exc:
        print(f"gleipnir-sandbox: {exc}", file=sys.stderr)
        return 3
    return _exec(argv)


def _cmd_image_build(args: argparse.Namespace) -> int:
    """Build the sandbox image. Operator/bootstrap action — this is the ONE
    place a build happens, invoked deliberately, never auto-triggered by
    test/lint (`runtime.py` refuses to build). OFF the agent allowlist.
    Renamed from `build` to `image-build` to free the word `build` for a
    future target-project compile verb (T5) — this rename does not widen
    or alter the agent-facing surface, which was never `build` in the first
    place."""

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
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_test = sub.add_parser(
        "test", help="run the configured test command in-container with coverage"
    )
    p_test.add_argument("pytest_args", nargs=argparse.REMAINDER)
    p_test.set_defaults(func=_cmd_test)

    p_lint = sub.add_parser(
        "lint", help="run the configured lint/compile check in-container"
    )
    p_lint.set_defaults(func=_cmd_lint)

    p_image_build = sub.add_parser(
        "image-build", help="build the sandbox image (operator/bootstrap only)"
    )
    p_image_build.add_argument(
        "--image",
        default=SANDBOX_IMAGE,
        help=f"sandbox image tag to build (default: {SANDBOX_IMAGE})",
    )
    p_image_build.set_defaults(func=_cmd_image_build)

    return parser


def main(argv: list[str] | None = None, *, config_root: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "pytest_args", None) and args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]
    if args.subcommand in ("test", "lint"):
        return args.func(args, config_root=config_root)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
