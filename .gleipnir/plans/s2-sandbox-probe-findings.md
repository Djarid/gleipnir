# S-2 Sandbox — CRI Probe Findings (build-gate ground truth)

Transient Tier-0 record. Ran on the operator/build surface (host inspection is
out-of-sandbox by definition). Grounds the spec-review of `s2-sandbox.md` in
real facts rather than assumptions.

## Environment

- **OS:** macOS 26.5.2 (Darwin 25.5.0), **arm64 (Apple Silicon)**.
- **Podman:** present, `/opt/homebrew/bin/podman`, **version 6.0.2**, provider
  `applehv` (Apple native hypervisor).
- **Docker:** absent. nerdctl/lima/colima: absent.
- **Verdict:** we are on the **Podman + macOS-VM path**. Docker fallback is not
  exercisable here (not installed), so it stays designed-but-untested on this box.

## Build Gate 1 (which CRI) — PASSED

Podman is present and usable once its machine is started. Detection order
(podman → docker → …) resolves to podman here.

## Build Gate 2 (rootless/permission works) — PASSED

- A machine exists (`podman-machine-default`) but was **`Running: false`**.
- `podman machine start` → `Running: true`, exit 0 (~seconds).
- `podman run --rm hello-world` → "Hello from Docker!", exit 0.
- Rootless container run works without privilege escalation.

## macOS machine-lifecycle facts (refine the entrypoint design)

- **`podman info` is NOT a reliable "can I run containers?" check on macOS:** it
  returned host data (`darwin/arm64`, version) even with the machine STOPPED.
  The deterministic signal is `podman machine list --format json` → `Running`.
  (Confirms the plan's choice; do not parse `info` or error strings — G-4a
  prose-parsing anti-pattern.)
- **Stopped-machine failure is the cryptic one the plan warned about:**
  `podman run` with machine stopped →
  `unable to connect to Podman socket: ... dial tcp 127.0.0.1:52711: connect:
  connection refused`. The entrypoint must translate `Running: false` into a
  `podman machine start` (or actionable message), never surface this raw.
- Machine here already exists, so the case is **start** (not `init`). Entrypoint
  must handle all three: none→init+start; stopped→start; running→proceed.

## The real proof: existing suite runs IN the container

```
podman run --rm -v "$PWD:/work:ro" -w /work docker.io/library/python:3.12-slim \
  sh -c "pip install -q pytest && python -m pytest -q"
=> 101 passed, 1 warning in 0.08s
```

- Repo mounted **read-only**; Python 3.12.13; sees `src/` (7 files) and all tests.
- **101 tests** = engine 49 + marker/CLI 20 + wire-in (bridge/allow_table/driver)
  32. This ALSO verifies the wire-in Python build is green (previously
  unverifiable under the host allowlist gap).

## Refinement the probe surfaced (feed into the plan)

- **Read-only mount + pytest cache clash:** pytest tried to write
  `.pytest_cache` into the ro mount → `PytestCacheWarning` (harmless, tests
  passed). The sandbox must give pytest writable scratch: mount a rw `/tmp` or
  cache dir, or run `-p no:cacheprovider`, and set `PYTHONDONTWRITEBYTECODE=1`.
  Source stays ro; only a scratch dir is rw. Add to the plan's mount layout.
- **Image choice validated:** `python:3.12-slim` from docker.io works and is
  small; pytest installs in-image quickly. (Later: pin/version + vendor to
  avoid per-run pip install; the plan's "minimal image" step.)

## Bootstrap note (chicken-and-egg resolved by observation)

Starting the machine and the first image pull are **operator/framework
bootstrap** actions (done here on the build surface), not agent-in-sandbox
actions — consistent with the plan's bootstrap section. Agents invoke the
sandbox entrypoint only after the machine is up; the entrypoint itself ensures
the machine on each run.
