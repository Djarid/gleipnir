# Decision: S-2 execution sandbox (containerised build/test/lint)

**Status:** decided and built (this session). Durable decision record. Realises
spec S-2 (option B container) / T-6 (sandbox folded into S-2) for the
*execution* surface: build/test/lint run inside an ephemeral container, never on
the host. Authored by the operator via the escape hatch (Tier-3). Plan of
record: `../plans/s2-sandbox.md`; probe ground truth:
`../plans/s2-sandbox-probe-findings.md`.

## Why

Agent-authored test code is arbitrary code. Running it on the host is the
unbounded blast radius S-2/T-6/G-2 exist to remove. The sandbox makes build/
test/lint execute in a bounded, disposable container so a malicious or buggy
test cannot reach the host filesystem, credentials, or network.

## What was decided and built

- **Runtime detection at invocation**, never hardcoded: prefer `podman`, fall
  back to `docker`, else **fail closed** (no host fallback ever). Implemented in
  `src/gleipnir/sandbox/runtime.py` (`detect_cri`).
- **Readiness off the structured signal.** macOS/podman machine readiness is
  decided from `podman machine list --format json` → `Running`, **not**
  `podman info` (the probe proved it returns host data with the machine
  stopped) and **never** by parsing the cryptic connection-error string (the
  G-4a prose-parsing anti-pattern). Three deterministic cases: none→init+start,
  stopped→start, running→proceed.
- **Bounded run.** `--network=none` (no egress), source bind-mounted **read-only**
  at `/work`, a **separate writable scratch** mount at `/work/.scratch` for
  pytest cache + coverage data, `PYTHONDONTWRITEBYTECODE=1`. Nothing under
  `.git/`, `.gleipnir/`, or any credential/key path is ever mounted.
- **Image pinned by digest.** `Containerfile` = `python:3.12-slim`
  @sha256:55842c72… with `pytest`+`pytest-cov` pre-installed as **dev tooling in
  the image** (NOT runtime deps — the enforcement core stays stdlib-only per
  `runtime-and-deps.md`). Pre-installed so runs need no network.
- **Thin entrypoint, exact-match grant.** `bin/gleipnir-sandbox` is a one-line
  shim that `exec`s the stdlib-Python CLI; the agent allowlist grants exactly
  `bin/gleipnir-sandbox test|lint` (no trailing wildcard → no compound-command
  bypass). `build` is a deliberate operator/bootstrap action; test/lint **never
  auto-build** a missing image (that would hand the agent transitive build
  capability) — they fail closed with an actionable message.
- **Fail-closed everywhere:** no CRI, unready machine, or missing image all
  refuse with an actionable message; none fall back to host execution.

## Roster change (the G-2 capability swap)

`.gleipnir/agents/gleipnir-code.md` bash allowlist was changed from the
host-shaped set (`pytest*`, `make test`, `npm …`, `go …`) to exactly
`bin/gleipnir-sandbox test|lint`. This is the point at which "build/test runs in
a bounded container" stops being discipline and becomes capability: the host
test binaries are no longer granted. The swap was performed promptly after the
in-container validation (154 passed, 93% coverage), bounding the discipline-only
window per the plan.

## Environment (probe facts)

macOS 26 / arm64, podman 6.0.2 (docker absent). The docker-fallback path is
designed but untested on this box. Machine lifecycle here was
existing-but-stopped → `start` (not `init`).

## Status: partially closes G-2; not yet G-1/G-3/E-1

This bounds **execution** blast radius (the T-6 half of G-2). It does NOT close:
- the **read-only mount of the enforcement subset of `.gleipnir/`** (G-1
  closure) — still tree-side;
- **credential isolation / the broker argument policy** (E-1);
- the digest-verified boundary (G-3.1 applied to config) + S-3 preflight.
Those remain later substrate obligations. `Makefile` (host `pytest` on one
file) is superseded by the sandbox entrypoint and should be removed/retargeted
in a follow-up.
