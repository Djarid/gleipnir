# Plan: S-2 Execution Sandbox (build-order step 1, option B container-core)

**Stage:** plan (authored by `gleipnir-plan`, Tier-0 artifact under `.gleipnir/plans/`).
**Status of the thing being planned:** authored, not yet closed. This is the step
that *starts making G-2 real* — it moves agent-written test code off the host into a
bounded, ephemeral container. It does not by itself close G-1/G-2/G-3; it is the
substrate those closures later stand on.

> **Provenance (decided by operator — captured, not re-decided).** D-4 is already
> resolved to **option B (container read-only mount) as core** in
> `.gleipnir/decisions/substrate-design-pass.md`; config load path is **mount-side**;
> the enforcement core is **Python + stdlib-only** per
> `.gleipnir/decisions/runtime-and-deps.md`. This plan builds within those decisions;
> it does not reopen them.

---

## A — Architect

**Problem (one sentence).** Build/test/lint currently run host-side via a `.venv` and
an ad-hoc bash allowlist; replace that with an ephemeral, runtime-detected container
sandbox so agent-written test code executes in a bounded blast radius (S-2 / T-6 / G-2),
never on the host.

**User.** `gleipnir-code` (the implementation agent, which must run its own tests but
must not run arbitrary code on the host); and the operator/framework layer that builds
and validates the sandbox itself.

**Measurable success.**
1. The existing suite — **90 test functions across 6 files** (`tests/test_bridge.py`,
   `test_cli.py`, `test_allow_table.py`, `test_driver.py`, `test_engine.py`,
   `test_marker.py`) — runs *inside the container* and is green, identical to host.
   (This is the concrete form of the operator's "49+ tests pass inside identically".)
2. `gleipnir-code` can run **all** tests through one entrypoint, not the current
   `make test` which is hardcoded to `tests/test_engine.py` only (1 of 6 files) — the
   symptom that triggered this step.
3. With no usable container runtime, build/test/lint **refuse** (fail-closed), and
   emit a clear, actionable message — never a silent host fallback, never a cryptic
   connection error.
4. A test that attempts to touch a host path outside the declared mounts **cannot**
   (bounded blast radius demonstrated).
5. The container runtime is **detected at every invocation**, preferring podman, falling
   back to docker/other CRI — no hardcoded runtime.

**Constraints.**
- Enforcement-core and any detection/entrypoint Python: **stdlib-only** (runtime-and-deps.md).
- Substrate is **option B** container (substrate-design-pass.md); ephemeral tagged-container
  pattern; disposable (`--rm`).
- Config/guard load path is **mount-side, read-only** for enforcement-bearing content.
- Credentials and the G-3 key are **never** mounted into the sandbox (preserve the
  G-2 credential boundary and the G-3 key boundary).
- Image kept **minimal** — small trusted surface to audit (serves G-1/G-2).
- This plan **writes no code and no Tier-3 config.** Two operator-only hand-offs are
  *named*, not performed (see Trace items (e) and the Durable-decision flag).

---

## T — Trace

### Artifacts (each classified by tier + writer)

| # | Artifact | Where it lives | Language / form | Tier | Writer |
|---|---|---|---|---|---|
| (a) | Container image definition | `Containerfile` at repo root (OCI-standard name; podman & docker both build it) | Containerfile syntax | Tier 0/1 build input (tree-side; not enforcement-bearing on its own) | `gleipnir-code` under delegation (bootstrap caveat below) |
| (b) | CRI-detection + machine-ensure + run logic | `src/gleipnir/sandbox/` (new package under the stdlib-only enforcement core) | **stdlib Python** (`subprocess`, `shutil.which`, `json`, `argparse`) | Tier 0 code; graduates toward enforcement-bearing when it becomes preflight input | `gleipnir-code` (source + tests) |
| (c) | Sandbox entrypoint the agent invokes | `bin/gleipnir-sandbox` (thin wrapper) delegating to (b) | **thin shell shim → stdlib-Python** (see decision below) | Tier 0 | `gleipnir-code` |
| (d) | Mount layout | expressed as data inside (b) — the `podman run`/`docker run` argv | n/a (config within (b)) | Tier 0 | `gleipnir-code` |
| (e) | `gleipnir-code` frontmatter allowlist change | `.gleipnir/agents/gleipnir-code.md` | agent frontmatter | **Tier 3 (POLICY)** | **operator only — HAND-OFF, not written here** |

**Recommended entrypoint language (constraint 6):** **thin shell shim (`bin/gleipnir-sandbox`)
that immediately `exec`s stdlib-Python in `src/gleipnir/sandbox/`.** Why: the *testable*
logic (CRI detection parsing, machine-state handling, fail-closed decisions) must be
stdlib-Python so it is unit-testable with faked runtime probes and covered by the
stdlib-only conformance check; the shell shim exists only so the agent's bash allowlist
can name a single fixed command with no shell logic of its own (no branching in shell
that could drift or be an enumerable-bypass surface). All decisions live in Python; the
shim is one `exec` line.

### Integrations map

| Integration | Purpose | Reached how | Notes / boundary |
|---|---|---|---|
| Container runtime (podman preferred, docker/other CRI fallback) | Run the ephemeral test container | `shutil.which("podman")` then `which("docker")`; probe with `<rt> info` / `version --format json` | Detected **every invocation**; never persisted, never hardcoded |
| `podman machine` (macOS only) | The Linux VM podman needs on macOS | `podman machine list --format json` → parse state | `init` if none, `start` if stopped, proceed if running (see edge cases) |
| Enforcement-core source + tests | The code under test | **read-only** bind mount into the container (`:ro`) for source; tests mounted (ro is sufficient — pytest writes only caches, which go to a tmpfs/rw scratch) | Source `src/` **ro**; tests `tests/` **ro**; `pyproject.toml` **ro** |
| Writable scratch | pytest cache, `__pycache__`, coverage temp | container-internal tmpfs or an rw scratch mount **inside the container's own writable layer**, discarded on `--rm` | Never a host path outside the repo work area |
| G-3 key / credentials | — | **NOT mounted. NOT an env var. NOT readable.** | Explicit non-integration — this is the G-2/G-3 boundary the sandbox must preserve |

**Mount layout (item (d), explicit ro vs rw):**
- `src/` → `:ro` (source under test; enforcement-bearing, mount-side read-only per config-load-path decision)
- `tests/` → `:ro` (test code; agent-authored, treated as untrusted input — read-only into the runner)
- `pyproject.toml` → `:ro` (pytest config: `pythonpath=["src"]`, `testpaths=["tests"]`)
- pytest scratch/cache → container writable layer only (tmpfs or `--rm` ephemeral layer)
- `.gleipnir/keys/**`, any credential, any git remote/token → **absent** (not mounted, not env)
- `.git/` → **not mounted** (the sandbox runs tests; it does not touch git — git is `git-ops` only)

### Edge cases (what could break)

- **No runtime at all** → fail-closed refuse with actionable message ("no container runtime
  found; install podman or docker"). Never fall back to host `pytest`.
- **podman present but macOS machine stopped** → attempt `podman machine start`; on failure,
  clear message naming `podman machine start`. Never surface the raw connection error.
- **podman present, no machine exists (fresh macOS)** → `podman machine init` then `start`;
  if init fails (e.g. no VM provider), clear actionable message.
- **podman binary present but daemon/VM unreachable and unrecoverable** → refuse, do not
  fall through to docker silently *unless* docker is genuinely present and usable (fallback
  is by absence/failure of the preferred runtime, deterministic, logged).
- **Linux rootless podman** → no machine needed; must still confirm rootless run works
  (uid mapping) — this is a build gate, not an assumption.
- **docker present but requires sudo / socket permission denied** → treat as *not usable*,
  message accordingly; do not silently escalate privilege.
- **Image not yet built / stale** → detection layer must decide build-if-absent vs
  fail-with-instruction (see bootstrap wrinkle — building is operator/framework-level).
- **A test tries to write or read outside the mounts** → blocked by container isolation
  (bounded blast radius); this is asserted in Stress-test.
- **`podman machine list --format json` output shape differs across podman versions** →
  parse defensively; unknown/unparseable state → treat as "not confirmed running" and act
  (validate against the podman version actually present — build gate).

### The bootstrap wrinkle (named explicitly)

Building and *validating* the sandbox image requires running container commands
(`podman build`, first `podman run`, possibly `podman machine init`). That is an
**operator / framework-level action**, run on the host, **not** an agent-in-sandbox
action. Resolution to avoid chicken-and-egg:

- **Operator/framework runs the setup** (one time / on image change): `podman machine`
  provisioning, `podman build -t gleipnir-sandbox .`, and the first validation run.
  This is out-of-framework host action, the same trust class as S-3 preflight and
  closure — exactly the layer permitted to run raw container commands.
- **`gleipnir-code` runs tests-in-sandbox afterward** via the single `gleipnir-sandbox test`
  entrypoint, which assumes the image already exists (or triggers a build only through
  the same operator-blessed path, never by the agent acquiring raw `podman build` in its
  allowlist). The agent never needs raw container capability to *use* the sandbox.
- Therefore the agent's new allowlist entry (item (e)) is exactly `gleipnir-sandbox …`,
  and **not** `podman`/`docker`, keeping raw container verbs off the agent surface (G-2).

### Relationship to S-3 preflight and to "authored, not yet closed"

- **S-3 preflight:** "container runtime present and the sandbox image available" is a
  natural preflight item — the runtime twin of the CI conformance gate. This plan makes
  the *detection logic* (b) reusable so preflight can call it read-only to assert
  availability before a session starts, fail-closed. Preflight wiring itself is a later
  step; this plan produces the check it will use.
- **Honesty:** this step does not flip G-2 to closed. It removes host execution for
  build/test/lint and puts them in a bounded container — the first concrete G-2
  blast-radius reduction. The credential/broker half of G-2 (E-1 argument policy) and
  the read-only mounting of the *enforcement subset* of `.gleipnir/` (G-1 closure) remain
  later obligations. State that plainly in any status table this touches.

---

## L — Link (validate BEFORE building)

Validate connections/tools/inputs first, because building an image before knowing the
runtime works wastes a full build cycle (ATLAS anti-pattern 2). **These are promoted to
explicit stop-conditions — a "no" halts the build.**

```
[ ] BUILD GATE 1 — Which CRI is actually present in THIS environment?
    Action (host, operator/framework): `command -v podman; command -v docker`
    then `podman info` (or `docker info`). Record which one, and its version.
    STOP if neither is present and installable — the whole plan's premise fails here.

[ ] BUILD GATE 2 — Does rootless / permission actually work?
    Linux: confirm rootless `podman run --rm <img> true` succeeds without sudo (uid map OK).
    macOS: confirm `podman machine` can init+start (VM provider present), then run.
    docker: confirm socket permission without privilege escalation.
    STOP if the only runtime needs privilege we will not grant — refuse rather than sudo.

[ ] LINK 3 — Minimal base image resolves and pulls
    Confirm the chosen minimal Python base (e.g. python:3.11-slim or a distro python)
    pulls under the detected runtime. Confirm python>=3.11 (pyproject requires-python).

[ ] LINK 4 — pytest availability strategy validated
    Confirm the dev extra `pytest>=8,<9` (pyproject optional-deps `dev`) installs in the
    image OR is provided by the base. Enforcement-core stays stdlib-only; pytest is
    dev-tooling INSIDE the image, not a runtime dep of the shipped core.

[ ] LINK 5 — macOS podman-machine sequence confirmed against the installed podman version
    `podman machine list --format json` output shape verified against the actual version;
    init/start/already-running branches each exercised once by hand.

[ ] LINK 6 — Mount semantics confirmed
    A `:ro` source mount is genuinely read-only from inside; pytest still runs with cache
    directed to a writable in-container location. Confirm before wiring the entrypoint.
```

**macOS detection/kickoff sequence (the exact order to implement in (b)):**
1. `shutil.which("podman")` → if present, this is the preferred runtime.
2. `podman machine list --format json` → parse:
   - empty / no machine → `podman machine init` then `podman machine start`.
   - machine exists, state `stopped` → `podman machine start`.
   - machine exists, state `running` → proceed.
   - unparseable/unknown → treat as not-confirmed-running, attempt `start`, else clear error.
3. On any machine step failing → **actionable message** naming the exact command the
   operator should run; **do not** emit the raw gRPC/connection error.

**Linux path:** `which podman` present → rootless podman, **no machine step** → go
straight to `podman run --rm …`. If podman absent → `which docker` → docker path. If
neither → fail-closed.

**CRI-detection order (canonical):** podman → docker → (other CRI if ever added) →
fail-closed. Detected fresh every invocation.

---

## A — Assemble (build order)

Test-first where the logic is testable; the image is validated by running the real suite
inside it. Order chosen so nothing is built on an unvalidated assumption.

1. **Confirm Link/Build gates 1–2 (host, operator/framework).** Record the present CRI
   and that rootless/permission works. *No source written until this passes.*
2. **Write tests for the detection/decision logic (b), test-first, stdlib-only.**
   Unit tests with **faked runtime probes** (monkeypatch `shutil.which` and a fake
   `subprocess.run`) covering: podman-present, podman-absent-docker-present,
   neither-present (fail-closed), macOS machine stopped/absent/running, unparseable
   machine JSON. These faked-probe tests need **no real container** and run on host.
3. **Implement (b) `src/gleipnir/sandbox/` to make those tests green.** Pure stdlib.
   Detection returns a decision object (runtime, machine-action, argv) — the run step is
   a thin edge so the decision logic is fully unit-testable.
4. **Write the `Containerfile` (a)** — minimal Python base ≥3.11, install `pytest` dev
   extra, set workdir; no credentials, no git, no network beyond build. Keep layers few.
5. **Write the thin entrypoint shim (c) `bin/gleipnir-sandbox`** → `exec`s (b) with the
   subcommand (`test|build|lint`). No logic in shell.
6. **Operator/framework builds the image and runs the first in-container validation**
   (bootstrap step — host action): `podman build` then `gleipnir-sandbox test` runs all
   90 tests inside the container and they are green, matching host.
7. **Wire the stdlib-only conformance check** to include the new `sandbox/` package
   (grep/AST for non-stdlib top-level imports; must stay clean).
8. **HAND-OFF, operator only (Tier 3):** update `.gleipnir/agents/gleipnir-code.md`
   frontmatter — remove the host-shaped allowlist (`npm run build`, `npm test`,
   `npm run lint*`, `pytest*`, `go build*`, `go test*`, `make build/test/lint`) and
   replace with the single container-shaped entrypoint (e.g. allow
   `bin/gleipnir-sandbox test`, `bin/gleipnir-sandbox build`, `bin/gleipnir-sandbox lint`;
   keep `pytest*`/`make*`/`sh*`/`git*` etc. denied). **This plan does not write it** —
   named as a hand-off per the capability boundary.
9. **HAND-OFF, operator only (Tier 3):** author the durable decision record (see below).

**Makefile note:** the current `make test` hardcodes `tests/test_engine.py` (1 of 6 files)
— this is the symptom, not the fix. The sandbox entrypoint runs the whole `tests/` tree
(pyproject `testpaths=["tests"]`). Whether `make` is retired or repointed at the entrypoint
is a small follow-on; the entrypoint, not `make`, becomes the agent's path.

---

## S — Stress-test (acceptance checks — concrete, checkable)

| # | Scenario | Expected result |
|---|---|---|
| 1 | podman present (Linux rootless or macOS running machine) | tests run **inside container**, all 90 pass |
| 2 | podman **absent**, docker present | detection falls back to docker, tests run in container, all 90 pass |
| 3 | **neither** present | build/test/lint **fail-closed refuse** with actionable message; **no host pytest runs** |
| 4 | macOS, machine **stopped** | `podman machine start` invoked; tests then run — OR a clear message naming the command (never a raw connection error) |
| 5 | macOS, **no machine** exists | `podman machine init` + `start`; or clear actionable failure |
| 6 | a test tries to read/write a host path **outside the mounts** | **blocked** — cannot escape the container (blast radius bounded) |
| 7 | attempt to read the G-3 key / any credential from inside the container | **fails** — not mounted, not env, not present |
| 8 | full suite parity | the **90 test functions across 6 files** pass inside the container **identically** to host (same count, same green) |
| 9 | detection logic unit tests (faked probes) | podman/docker/neither/macOS-machine-states all covered, fail-closed asserted, run on host with **no real container** |
| 10 | stdlib-only conformance | `src/gleipnir/sandbox/` imports only stdlib (conformance check clean) |
| 11 | agent surface | `gleipnir-code` reaches tests **only** through `gleipnir-sandbox …`; raw `pytest`/`podman`/`docker`/`sh` remain denied (verified post-hand-off) |
| 12 | detection freshness | runtime is re-detected on every invocation (no cached/hardcoded runtime) |

**Note on 6 & 7:** these two are the ones that prove the step "starts making G-2 real."
If either fails, the sandbox is decorative — treat as a blocking defect, not a warning.

---

## Execution Workflow (for the implementing agent)

**You are `gleipnir-code` acting under a bounded delegation from the orchestrator.**
The pipeline is test → code (per stage-role-map). Follow this order; do not skip the
gates.

1. **Do NOT run host `pytest` directly.** The whole point of this work is to stop that.
   Until your allowlist is updated (operator hand-off, step 8), you may be unable to run
   the full suite — that is expected and is the symptom being fixed. Report readiness;
   the operator performs the frontmatter change and the first in-container validation.
2. **Confirm Build Gates 1–2 are recorded as passed by the operator/framework before you
   write image or run code.** If they are not recorded, STOP and report — you must not
   attempt `podman build`/`podman machine` yourself (bootstrap is operator-level; those
   verbs are not in your surface, and must not be added).
3. **Write detection tests first** (Assemble step 2) with faked probes — these run on host,
   need no container, and are the correctness arbiter for the fail-closed and macOS logic.
   Do not weaken a test to make it green.
4. **Implement `src/gleipnir/sandbox/` (stdlib only)** to pass those tests. Keep the run
   edge thin; keep all decision logic pure and testable.
5. **Write the `Containerfile` and the thin `bin/gleipnir-sandbox` shim.** No shell logic
   in the shim beyond one `exec`.
6. **Hand back to the orchestrator** for the operator/framework bootstrap build +
   first in-container validation (all 90 tests green inside the container) and for the
   two Tier-3 hand-offs. You cannot perform those; report them as required next actions.
7. **Never** mount or reference the G-3 key, credentials, or `.git/`. If a task seems to
   need them, STOP — that is a boundary you must not cross.
8. **Never edit anything under `.gleipnir/`** — including your own frontmatter. That is
   the operator's Tier-3 action.

---

## Durable-decision flag (Tier 3 — `decisions/`, operator-authored, NOT written here)

Two things in this plan are durable resolutions later work will depend on and therefore
belong in a Tier-3 decision record, which this planning role may not write. Named
precisely so the operator can persist them:

**File:** `.gleipnir/decisions/s2-sandbox.md`
**Suggested title:** "S-2 execution sandbox — container-shaped build/test/lint (build-order step 1)"
**Content to capture:**
1. **Runtime-detection contract:** build/test/lint run in an ephemeral `--rm` container;
   runtime detected every invocation, order podman → docker → other CRI → **fail-closed**;
   host fallback is forbidden; macOS `podman machine` init/start handled with actionable
   messaging.
2. **Entrypoint contract & agent-surface change:** the agent's build/test/lint capability
   is the single `gleipnir-sandbox` entrypoint (thin shell → stdlib-Python), replacing the
   host-shaped allowlist in `gleipnir-code.md`; raw `podman`/`docker`/`pytest`/`sh` remain
   denied to the agent. Records the mount layout (src/tests/pyproject `:ro`; key &
   credentials absent) as the G-2/G-3 boundary for the sandbox.
3. **Bootstrap trust class:** image build and first validation are operator/framework host
   actions (same class as S-3 preflight/closure), never agent-in-sandbox — resolving the
   chicken-and-egg.

The `gleipnir-code.md` frontmatter edit (Trace item (e)) is the *other* Tier-3 hand-off,
distinct from this decision record; both are operator-only.
