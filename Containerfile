# S-2 sandbox image (T-6 folded into S-2): the bounded, ephemeral environment
# in which build/test/lint run, so agent-authored test code never executes on
# the host (G-2 bounded blast radius).
#
# Base validated by the S-2 CRI probe (.gleipnir/plans/s2-sandbox-probe-findings.md):
# python:3.12-slim pulls under podman on macOS/arm64, small, Python 3.12.13.
# Pinned by digest below so the image is reproducible and not silently moved.
#
# pytest + pytest-cov are pre-installed as DEV TOOLING INSIDE THE IMAGE. They are
# NOT runtime dependencies of the enforcement core (that stays stdlib-only, per
# .gleipnir/decisions/runtime-and-deps.md) — they live only in this test image.
# Pre-installing them means test runs need NO network: the entrypoint runs the
# container with --network=none (no egress), and nothing pip-installs at runtime.
#
# The repo is bind-mounted read-only at /work at run time (not COPYied in), with
# a separate writable scratch mount — see src/gleipnir/sandbox/runtime.py. This
# image deliberately contains NO source, NO credentials, NO keys.

# python:3.12-slim (linux/arm64 + linux/amd64 multi-arch digest). Update the
# digest deliberately when bumping the base; never rely on a moving tag.
FROM docker.io/library/python:3.12-slim@sha256:55842c72c6b3584d06ec84c731fc516b30b8a53ad262ebd085e47ab568b3bfc1

# Pinned dev test tooling. Versions bounded so the image is reproducible.
RUN pip install --no-cache-dir "pytest>=8,<9" "pytest-cov>=5,<6"

# Default workdir matches the run-argv's -w /work (the ro source bind mount).
WORKDIR /work

# No ENTRYPOINT/CMD: the entrypoint argv (python -m pytest ... / compileall) is
# supplied per-run by src/gleipnir/sandbox/runtime.py's build_run_argv, so the
# image stays a generic bounded executor, not a baked-in single command.
