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
   *Probe update: the in-container run showed **101 passing** — engine 49 + marker/CLI 20
   + wire-in (bridge/allow_table/driver) 32 — so the suite has grown past the "90 across 6
   files" figure and the wire-in Python build is green in-container. The parity requirement
   is unchanged; the current count is 101.*
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
6. **Test coverage is a first-class output, not opt-in.** Every in-container test run
   surfaces **two** metrics — **pass rate AND coverage %** ("N passed" alone is
   insufficient) — and coverage is reported as **LINE + BRANCH**, with **branch the
   authoritative measure**: a framework about fail-closed edge cases must prove its
   *failure branches* are exercised, not merely its lines. **Target 85%**: always
   *reported*, and anything below 85% must be *justified* by the code/test agents. It is
   **soft during bootstrap** (below-target is a justify-not-fail condition, not yet a hard
   CI failure) and **hardens into a C-2 CI coverage gate later** — the trajectory is
   report-and-justify now → hard C-2 gate later.

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
| (a) | Container image definition | `Containerfile` at repo root (OCI-standard name; podman & docker both build it) | Containerfile syntax | Tier 0/1 build input (tree-side; not enforcement-bearing on its own) | `gleipnir-code` under delegation (bootstrap caveat below). **Pre-installs dev test tooling `pytest` AND `pytest-cov` into the image** (not pip-installed at runtime — consistent with `--network=none` steady state). `pytest-cov` is **dev-only tooling inside the image, NOT a runtime dependency of the enforcement core** — runtime-and-deps.md stays stdlib-only for shipped code |
| (b) | CRI-detection + machine-ensure + run logic | `src/gleipnir/sandbox/` (new package under the stdlib-only enforcement core) | **stdlib Python** (`subprocess`, `shutil.which`, `json`, `argparse`) | Tier 0 code; graduates toward enforcement-bearing when it becomes preflight input | `gleipnir-code` (source + tests) |
| (c) | Sandbox entrypoint the agent invokes | `bin/gleipnir-sandbox` (thin wrapper) delegating to (b) | **thin shell shim → stdlib-Python** (see decision below) | Tier 0 | `gleipnir-code` |
| (d) | Mount layout | expressed as data inside (b) — the `podman run`/`docker run` argv | n/a (config within (b)) | Tier 0 | `gleipnir-code` |
| (e) | `gleipnir-code` frontmatter allowlist change | `.gleipnir/agents/gleipnir-code.md` | agent frontmatter | **Tier 3 (POLICY)** | **operator only — HAND-OFF, not written here** |

**Hand-off item (e) — grants must be EXACT-match, NO trailing `*`.** The new entrypoint
allowlist entries (`bin/gleipnir-sandbox test`, `bin/gleipnir-sandbox build`,
`bin/gleipnir-sandbox lint`) must be **exact strings with no trailing wildcard** — unlike
today's `pytest*` / `npm run lint*` prefix-wildcard entries. A trailing `*` prefix-match
would let a compound command (`bin/gleipnir-sandbox test; curl …`) piggyback on the prefix;
exact-match denies that class outright. The operator performing the Tier-3 edit must **not**
reintroduce a wildcard by habit when swapping the host-shaped entries for these.

**Recommended entrypoint language (constraint 6):** **thin shell shim (`bin/gleipnir-sandbox`)
that immediately `exec`s stdlib-Python in `src/gleipnir/sandbox/`.** Why: the *testable*
logic (CRI detection parsing, machine-state handling, fail-closed decisions) must be
stdlib-Python so it is unit-testable with faked runtime probes and covered by the
stdlib-only conformance check; the shell shim exists only so the agent's bash allowlist
can name a single fixed command with no shell logic of its own (no branching in shell
that could drift or be an enumerable-bypass surface). All decisions live in Python; the
shim is one `exec` line.

**Entrypoint behaviour — `gleipnir-sandbox test` (coverage is first-class):** the `test`
subcommand runs the **full suite** inside the container **with coverage enabled** —
pytest with `--cov=src/gleipnir --cov-branch --cov-report=term-missing` (in addition to
the already-specified `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`). The
entrypoint's output therefore includes the **line% and branch% totals** and the
**per-file `term-missing` breakdown**. Coverage is reported on every run, not opt-in.
Below-target (85%) is surfaced-and-justified during bootstrap, not a hard fail (see
Architect success #6); it hardens to a C-2 CI gate later.

### Integrations map

| Integration | Purpose | Reached how | Notes / boundary |
|---|---|---|---|
| Container runtime (podman preferred, docker/other CRI fallback) | Run the ephemeral test container | `shutil.which("podman")` then `which("docker")`; presence via `which`, **readiness** via `podman machine list --format json` (`Running`), **not** `podman info` | Detected **every invocation**; never persisted, never hardcoded. Probe finding: `podman info` returned host data even with the machine STOPPED, so `info` succeeding does **not** prove containers can run — use the machine-list `Running` field |
| `podman machine` (macOS only) | The Linux VM podman needs on macOS | `podman machine list --format json` → parse the `Running` field | **Three cases, handled deterministically:** no machine → `init` then `start`; machine exists with `Running:false` → `start`; `Running:true` → proceed (see edge cases). Probe hit the middle case — an existing `podman-machine-default` that was stopped, so START not INIT |
| Enforcement-core source + tests | The code under test | **read-only** bind mount into the container (`:ro`) for source; tests mounted (ro is sufficient — pytest writes only caches, which go to a **separate writable scratch dir**, never the ro mount) | Source `src/` **ro**; tests `tests/` **ro**; `pyproject.toml` **ro**. Probe confirmed the repo mounts ro fine and 101 tests pass; the only wrinkle was pytest attempting to write `.pytest_cache` into the ro mount (harmless warning) — resolved by a separate rw scratch + cache suppression |
| Writable scratch | pytest cache, `__pycache__`, **coverage data file (`.coverage`)** and coverage temp | a **separate writable scratch dir** — a tmpfs or rw-mounted `/tmp/pytest-cache` **distinct from the ro source mount**, discarded on `--rm` | Never a host path outside the repo work area; **the source mount is never made writable to dodge the cache clash** — ro source, rw scratch only. `--cov-report=term-missing` writes to **stdout** (surfaced), and any `.coverage` data file lands in the rw scratch, discarded on `--rm` |
| G-3 key / credentials | — | **NOT mounted. NOT an env var. NOT readable.** | Explicit non-integration — this is the G-2/G-3 boundary the sandbox must preserve |

**Mount layout (item (d), explicit ro vs rw):**
- `src/` → `:ro` (source under test; read-only on its own merits — agent-authored tests
  must not be able to mutate the code they test, so the source is immutable from inside
  the runner. This is a build-sandbox source-mount rationale, distinct from D-4, which
  concerns the `.gleipnir/` config load-path, not source mounts.)
- `tests/` → `:ro` (test code; agent-authored, treated as untrusted input — read-only into the runner)
- `pyproject.toml` → `:ro` (pytest config: `pythonpath=["src"]`, `testpaths=["tests"]`)
- pytest scratch/cache → a **separate writable scratch dir** (tmpfs or rw-mounted `/tmp/pytest-cache`), **distinct from the ro source mount** — the source mount is never made writable to accommodate cache writes
- run pytest with `-p no:cacheprovider` **and** set `PYTHONDONTWRITEBYTECODE=1` — the probe verified this combination yields a clean "101 passed" with **no** `PytestCacheWarning`; without it pytest tries to write `.pytest_cache` into the ro mount (harmless warning, tests still pass, but avoided by design)
- `.gleipnir/keys/**`, any credential, any git remote/token → **absent** (not mounted, not env)
- `.git/` → **not mounted** (the sandbox runs tests; it does not touch git — git is `git-ops` only)
- **network → `--network=none`** on the `podman run`/`docker run` argv: the sandbox has
  **no network by default**. In-container test code can therefore reach neither the public
  network (exfiltration) nor internal services. The *only* thing that ever needed network
  was a runtime `pip install` of pytest — and LINK 4 / Assemble step 4 make the steady
  state pre-installing pytest INTO the image, which eliminates that need. So steady-state
  runs are `--network=none`; the pinned-image step is what removes the sole network
  justification. (Network is granted only during the operator/framework *build* of the
  image, host-side, never during an agent's test run.)

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
- **Image not yet built / stale** → **always fail-closed with an actionable instruction;
  never auto-build.** The detection layer must **never** invoke `podman build` on a
  missing/stale image — doing so would hand the agent transitive build capability every
  time it calls the entrypoint. A missing or stale image is an actionable refusal:
  *"image not built — operator run `gleipnir-sandbox build` / `podman build -t
  gleipnir-sandbox .`"*. This is consistent with the bootstrap section: build is
  operator/framework-only, never agent-triggered.
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
  entrypoint, which **assumes the image already exists**. If the image is missing or stale
  the entrypoint **fails closed with an actionable message** (see edge cases) — it **never**
  auto-builds, because auto-building would give the agent transitive build capability every
  time it calls the entrypoint. The agent never needs raw container capability to *use* the
  sandbox, and never acquires build capability by *using* it.
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

> **Empirical status (per `s2-sandbox-probe-findings.md`).** Build Gates 1 and 2 are
> **empirically PASSED on the current environment**: macOS 26 / arm64, podman 6.0.2,
> docker absent, rootless container run works, and the existing suite ran in-container
> with **101 tests passed**. Those two gates are therefore satisfied **for this
> environment**. The docker-fallback path (Gate 1's non-podman branch, Stress-test #2)
> remains **designed-but-untested here** — docker is not installed on this box.

```
[ ] BUILD GATE 1 — Which CRI is actually present in THIS environment?  [EMPIRICALLY PASSED — see below]
    Action (host, operator/framework): `command -v podman; command -v docker`
    to establish PRESENCE. Record which one, and its version. Note: do NOT treat
    `podman info` as a readiness check — the probe found it returns host data even
    with the machine stopped (readiness is the machine-list `Running` field, LINK 5).
    STOP if neither is present and installable — the whole plan's premise fails here.

[ ] BUILD GATE 2 — Does rootless / permission actually work?  [EMPIRICALLY PASSED — see below]
    Linux: confirm rootless `podman run --rm <img> true` succeeds without sudo (uid map OK).
    macOS: confirm `podman machine` can init/start (VM provider present), then run.
    docker: confirm socket permission without privilege escalation.
    STOP if the only runtime needs privilege we will not grant — refuse rather than sudo.

[ ] LINK 3 — Minimal base image resolves and pulls  [VALIDATED]
    Validated base: `docker.io/library/python:3.12-slim` (probe: Python 3.12.13) — pulls
    under podman, is small, and pytest installs quickly in-image; satisfies python>=3.11
    (pyproject requires-python). Follow-up (steady-state): pin by digest and pre-install
    pytest into the image (or vendor it) rather than pip-installing at runtime.

[ ] LINK 4 — pytest availability strategy validated  [VALIDATED — pip path proven, in-image is steady-state]
    Probe confirmed pytest installs quickly in-image on `python:3.12-slim` via a runtime
    `pip install -q pytest` (fine for validation). Steady-state: pre-install the dev extra
    `pytest>=8,<9` (pyproject optional-deps `dev`) INTO the image so no per-run pip install
    is needed. **Also pre-install `pytest-cov`** (the coverage plugin backing
    `--cov`/`--cov-branch`) as dev tooling INSIDE the image. Enforcement-core stays
    stdlib-only; pytest AND pytest-cov are dev-tooling INSIDE the image, NOT runtime deps
    of the shipped core.

[ ] LINK 5 — macOS podman-machine sequence confirmed against the installed podman version  [PARTIALLY EMPIRICAL — start branch exercised]
    `podman machine list --format json` output shape verified against the actual version
    (probe: podman 6.0.2); the `Running` field is the readiness signal, NOT `podman info`
    (probe confirmed `info` returns host data even with the machine stopped). The STOPPED→start
    branch was exercised by the probe; init (no machine) and already-running branches remain
    to be exercised by hand.

[ ] LINK 6 — Mount semantics confirmed
    A `:ro` source mount is genuinely read-only from inside; pytest still runs with cache
    directed to a writable in-container location. Confirm before wiring the entrypoint.
```

**macOS detection/kickoff sequence (the exact order to implement in (b)):**
1. `shutil.which("podman")` → if present, this is the preferred runtime.
2. `podman machine list --format json` → key off the structured `Running` field, **all three cases deterministically**:
   - (a) empty / no machine → `podman machine init` then `podman machine start`.
   - (b) machine exists, `Running:false` (stopped) → `podman machine start`. *(This was the case the probe actually hit: an existing `podman-machine-default` that was stopped — START, not INIT. Do not assume a fresh box.)*
   - (c) machine exists, `Running:true` → proceed.
   - unparseable/unknown → treat as not-confirmed-running, attempt `start`, else clear error.
3. On any machine step failing → **actionable message** naming the exact command the
   operator should run; **do not** emit the raw gRPC/connection error.

**Linux path:** `which podman` present → rootless podman, **no machine step** → go
straight to `podman run --rm …`. If podman absent → `which docker` → docker path. If
neither → fail-closed.

**CRI-detection order (canonical):** podman → docker → (other CRI if ever added) →
fail-closed. Detected fresh every invocation.

**Readiness signal (canonical, macOS):** the deterministic "can I run containers?"
signal is the structured `Running` field from `podman machine list --format json` —
**not** `podman info` (which the probe found returns host data even with the machine
stopped) and **not** the cryptic connection error string
(`dial tcp 127.0.0.1:PORT: connect: connection refused`). Parsing that error prose
would be the G-4a prose-parsing anti-pattern; the entrypoint keys off the structured
JSON `Running` field instead and translates `Running:false` into a `podman machine
start`, never surfacing the raw error. This is why the machine-list-JSON approach is
chosen over `info`/error-parsing.

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
4. **Write the `Containerfile` (a)** — validated minimal base `docker.io/library/python:3.12-slim`
   (probe: Python 3.12.13, small, pytest installs quickly in-image), **pinned by digest**;
   pre-install the `pytest` **and `pytest-cov`** dev extras **into the image** (or vendor
   them) so runs do not pip-install at runtime — the probe's runtime `pip install -q pytest`
   is fine for validation but is not the steady-state. Set workdir; no credentials, no git,
   no network beyond build. Keep layers few.
5. **Write the thin entrypoint shim (c) `bin/gleipnir-sandbox`** → `exec`s (b) with the
   subcommand (`test|build|lint`). No logic in shell.
6. **Operator/framework builds the image and runs the first in-container validation**
   (bootstrap step — host action): `podman build` then `gleipnir-sandbox test` runs all
   101 (current count) tests inside the container and they are green, matching host —
   **and reports line% + branch% coverage** (`--cov=src/gleipnir --cov-branch
   --cov-report=term-missing`), which is inspected against the 85% target.
6a. **Close known branch-coverage gaps (test-authoring task, test-first).** The coverage
   policy has *already* caught concrete gaps: a manual read-based branch analysis of
   `src/gleipnir/sandbox/runtime.py` found **3 untested fail-closed branches** — the
   `except OSError` in `_run_machine_subcommand`, the non-dict list-entry branch in
   `parse_machine_list`, and the "start/init reported success but recheck still
   not-running → raise `MachineNotReadyError`" path in `ensure_machine_ready`. These are
   exactly the kind of failure-branch gaps that **branch coverage surfaces and line
   coverage / pass count hide**. Authoring tests to exercise these (raising branch
   coverage) is part of the sandbox build; the **quality stage drives coverage as high as
   possible** and surfaces any remaining branch gaps.
7. **Wire the stdlib-only conformance check** to include the new `sandbox/` package
   (grep/AST for non-stdlib top-level imports; must stay clean).
8. **HAND-OFF, operator only (Tier 3):** update `.gleipnir/agents/gleipnir-code.md`
   frontmatter — remove the host-shaped allowlist (`npm run build`, `npm test`,
   `npm run lint*`, `pytest*`, `go build*`, `go test*`, `make build/test/lint`) and
   replace with the single container-shaped entrypoint as **exact-match strings, NO
   trailing `*`** (allow exactly `bin/gleipnir-sandbox test`, `bin/gleipnir-sandbox build`,
   `bin/gleipnir-sandbox lint` — a trailing wildcard would let a compound command
   piggyback on the prefix; keep `pytest*`/`make*`/`sh*`/`git*` etc. denied).
   **Perform this swap PROMPTLY after step 6** (the in-container validation): until it
   lands, `gleipnir-code`'s host allowlist (`pytest*`, `make test`, …) stays
   **capability-live**, so "don't run host pytest" is *discipline, not capability* during
   that interim window. Doing the swap right after step 6 bounds that window and keeps it
   visible rather than open-ended. **This plan does not write it** — named as a hand-off
   per the capability boundary.
9. **HAND-OFF, operator only (Tier 3):** author the durable decision record (see below).

**Makefile note:** the current `make test` hardcodes `tests/test_engine.py` (1 of 6 files)
— this is the symptom, not the fix. The sandbox entrypoint runs the whole `tests/` tree
(pyproject `testpaths=["tests"]`). Whether `make` is retired or repointed at the entrypoint
is a small follow-on; the entrypoint, not `make`, becomes the agent's path.

---

## S — Stress-test (acceptance checks — concrete, checkable)

| # | Scenario | Expected result |
|---|---|---|
| 1 | podman present (Linux rootless or macOS running machine) | tests run **inside container**, all 101 (current count) pass |
| 2 | podman **absent**, docker present | detection falls back to docker, tests run in container, all 101 (current count) pass |
| 3 | **neither** present | build/test/lint **fail-closed refuse** with actionable message; **no host pytest runs** |
| 4 | macOS, machine **stopped** | `podman machine start` invoked; tests then run — OR a clear message naming the command (never a raw connection error) |
| 5 | macOS, **no machine** exists | `podman machine init` + `start`; or clear actionable failure |
| 6 | a test tries to read/write a host path **outside the mounts** | **blocked** — cannot escape the container (blast radius bounded) |
| 7 | attempt to read the G-3 key / any credential from inside the container | **fails** — not mounted, not env, not present |
| 8 | full suite parity | the **101 (current count)** test functions pass inside the container **identically** to host (same count, same green) |
| 9 | detection logic unit tests (faked probes) | podman/docker/neither/macOS-machine-states all covered, fail-closed asserted, run on host with **no real container** |
| 10 | stdlib-only conformance | `src/gleipnir/sandbox/` imports only stdlib (conformance check clean) |
| 11 | agent surface | `gleipnir-code` reaches tests **only** through `gleipnir-sandbox …`; raw `pytest`/`podman`/`docker`/`sh` remain denied (verified post-hand-off) |
| 12 | detection freshness | runtime is re-detected on every invocation (no cached/hardcoded runtime) |
| 13 | a test tries to open a network connection from inside the sandbox | **fails** — no egress (`--network=none`); the container has no network by default |
| 14 | a run that **passes** but has coverage **below the 85% target** | the entrypoint reports **BOTH** the pass count AND the line+branch coverage% — the below-target number is **still surfaced** (not hidden by "N passed"); below-target is justified by the code/test agent, not a hard fail during bootstrap |
| 15 | coverage granularity | **branch coverage specifically is reported** (not just line) — `--cov-branch` totals appear alongside line%, and `term-missing` shows per-file gaps |

**Note on 6 & 7:** these two are the ones that prove the step "starts making G-2 real."
If either fails, the sandbox is decorative — treat as a blocking defect, not a warning.

**Empirical status (per `s2-sandbox-probe-findings.md`).** Scenario **1** (podman, macOS
running machine), scenario **4** (macOS machine stopped → start), and the parity check
**8** are **empirically PASSED on this environment** — the probe started the stopped
`podman-machine-default` and ran the suite in-container to **101 (current count) passed**
(the earlier "90 across 6 files" figure predates the wire-in tests the probe also proved
green). Build Gates 1 and 2 are thus satisfied **for macOS 26 / arm64 / podman 6.0.2**.
Scenario **2** (docker fallback) stays **designed-but-untested here** because docker is
absent on this box — it remains a designed path, not an empirical pass.

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
   Do not weaken a test to make it green. **Treat coverage as a first-class output:** every
   run reports pass rate AND line+branch coverage%; branch is authoritative. Target 85% —
   always report it, and **justify** anything below 85% (soft during bootstrap, hardens to
   a C-2 gate later). Explicitly author tests for the **3 known untested fail-closed
   branches in `runtime.py`** (Assemble step 6a): the `except OSError` in
   `_run_machine_subcommand`, the non-dict list-entry branch in `parse_machine_list`, and
   the recheck-still-not-running → `MachineNotReadyError` path in `ensure_machine_ready`.
4. **Implement `src/gleipnir/sandbox/` (stdlib only)** to pass those tests. Keep the run
   edge thin; keep all decision logic pure and testable.
5. **Write the `Containerfile` and the thin `bin/gleipnir-sandbox` shim.** No shell logic
   in the shim beyond one `exec`.
6. **Hand back to the orchestrator** for the operator/framework bootstrap build +
   first in-container validation (all 101 (current count) tests green inside the container) and for the
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
   host-shaped allowlist in `gleipnir-code.md`. The new allowlist entries are
   **exact-match strings with NO trailing `*`** (`bin/gleipnir-sandbox test|build|lint`) —
   a trailing wildcard would let a compound command piggyback on the prefix, so the
   operator must not reintroduce one by habit. Raw `podman`/`docker`/`pytest`/`sh` remain
   denied to the agent. Records the mount layout (src/tests/pyproject `:ro`; key &
   credentials absent; **`--network=none` — no network by default**) as the G-2/G-3
   boundary for the sandbox.
3. **Bootstrap trust class:** image build and first validation are operator/framework host
   actions (same class as S-3 preflight/closure), never agent-in-sandbox — resolving the
   chicken-and-egg.

**File:** `.gleipnir/decisions/coverage-gate.md`
**Suggested title:** "Test-coverage reporting & gate trajectory (soft now → C-2 hard gate later)"
**Content to capture (this planning role cannot write it — operator-only Tier 3):**
1. **Two-metric reporting:** every test run surfaces **pass rate AND coverage %**; "N
   passed" alone is insufficient.
2. **Line + branch, branch authoritative:** coverage is reported as LINE + BRANCH, with
   **branch the meaningful/authoritative measure** — a fail-closed framework must prove its
   failure branches are exercised, not just its lines.
3. **85% target / justify-below / not-yet-hard-fail:** 85% is a **target**, always
   **reported**; anything **below 85% must be justified** by the code/test agents; it is
   **soft during bootstrap** — NOT yet a hard CI fail.
4. **Hardens to C-2 later:** the trajectory is report-and-justify now → **C-2 CI coverage
   gate (hard fail) later**.
5. **Quality stage drives it:** the post-implementation adversarial review (`quality`
   stage / quality-reviewer) strives to drive coverage as high as possible and must
   surface the branch-coverage gaps.

The `gleipnir-code.md` frontmatter edit (Trace item (e)) is another Tier-3 hand-off, and
`.gleipnir/decisions/s2-sandbox.md` above is a third; all three are operator-only and
distinct.
