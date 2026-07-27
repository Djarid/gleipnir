# Plan: language-agnostic sandbox (config-driven verb dispatch)

**Stage:** plan. **Role:** gleipnir-plan. **Plans FROM** the operator-converged
D1–D6 decision below (LOCKED; captured here, not re-decided). A durable
decision record `.gleipnir/decisions/language-agnostic-sandbox.md` is named for
the operator to persist (see Operator hand-offs).

## GOTCHA pre-flight (visible)

- **Goals check** (`.gleipnir/goals/manifest.md`): plan-format is the governing
  goal; this file follows `plan-format.md`'s six required sections. Methodology
  goal (ATLAS/GOTCHA ahead of planning) is honoured — Architect/Trace framed
  before any build order. No sequencing goal exists or is authored here (G-5
  rule respected: I sequence nothing; I hand the ordered build to the
  orchestrator).
- **Plan-before-code:** correct order confirmed. This produces a plan only; no
  code is written by this role.
- **Gaps named:** the target-project `build` verb is deferred this slice (D3:
  python/node need no compile step); the naming-collision resolution is NOT
  deferred. The real node-image build + real `.mjs` run is an operator hand-off
  (see Link and the (c) recommendation); this slice validates dispatch logic
  with a faked exec, mirroring `tests/test_sandbox_cli.py`.
- **Layer placement (GOTCHA):** the Tier-3 config is a **Context/Args** artifact
  (data steering deterministic dispatch), NOT a Hard-prompt or Tool grant. The
  verb set is the **Tools** surface and must not widen. The arbiter-integrity
  property is a **G-1** (unreachable-guard) concern realised via the preflight
  enforcement-path set — not prose.

## Converged decisions (operator-decided; LOCKED — captured, not re-opened)

- **D1+D4 (cardinal, coupled):** a **Tier-3 POLICY config file**
  (operator-authored, agent-UNWRITABLE) declares, per target project profile:
  `{ base image (digest-pinned), test command, lint command, optional coverage
  command/parser }`. The AGENT-facing surface stays a **small fixed exact-match
  verb set** (`test` / `lint` / `build`); the sandbox READS the Tier-3 config
  and DISPATCHES the verb to the configured toolchain command. The agent never
  gains raw `cargo`/`gcc`/`node`/`make`. **CRITICAL PROPERTY:** the `test`
  command IS the Axiom-1 arbiter, so the config MUST be Tier-3 (the agent cannot
  rewrite `test` to `true`/no-op) AND MUST be enrolled in the G-1 preflight's
  enforcement path set (`boundary.py` `ENFORCEMENT_PATHS`) so the preflight
  verifies it is OS-read-only to the agent uid. Auto-detection may at most
  SUGGEST a profile to the operator, never DECIDE the command at runtime.
  **Build-verb naming collision resolved** (see Trace §T5).
- **D2:** per-toolchain, operator-built, digest-pinned images (mirror the
  `Containerfile` pattern: `FROM …@sha256`, deps preinstalled, `--network=none`,
  no `ENTRYPOINT`). A project-supplied image is allowed ONLY if its digest is
  pinned in the Tier-3 config.
- **D3:** pre-baked deps in the digest-pinned image. General offline-deps
  (fetch-then-seal) is a SEPARATE later (E-1-grade) decision, explicitly
  deferred. First slice picks node because `tests/test_sequence_gate.mjs` is
  zero-dep/offline.
- **D5:** coverage = honest optional-with-recorded-justification per project;
  per-language adapter as onboarded; NEVER silently drop the metric (report
  `coverage: unavailable (justified: …)`). Python keeps `pytest-cov`; node
  reports coverage-unavailable-justified (or node built-in coverage if trivial).
- **D6 first slice:** generalize `__main__.py` to READ the Tier-3 config and
  dispatch verbs, PROVEN with two targets — (1) **Python regression** (existing
  pytest+coverage still works, now config-driven, full suite green) and (2)
  **node** (`tests/test_sequence_gate.mjs`: DISPATCH-PROVEN this slice — the
  faked exec asserts the right node image + argv are selected; the REAL node run
  that actually closes the dogfood node seam is deferred to the operator
  hand-off). Rust/C/C++ + plugin system OUT.

---

## 1. Architect

**Problem (one sentence).** The S-2 sandbox is under-scoped to self-hosting
Python — its CLI hard-wires `python -m pytest`/`compileall` and a single Python
image — so Gleipnir cannot guard a multi-language target project, and the only
alternative (handing the agent a raw toolchain) would neuter the Axiom-1 test
arbiter; this slice makes the verb→command mapping a Tier-3, agent-unwritable,
preflight-enforced config that the CLI dispatches, proven on Python (regression)
and node (new).

**User.** The `gleipnir-code` agent (runs `bin/gleipnir-sandbox test|lint`
inside a bounded delegation, unchanged surface); the operator (authors the
Tier-3 profile + builds/pins images); the quality/gate stages (consume the
honest coverage output). Downstream: any non-Python target project onboarded
later via a new profile + image, with no CLI code change.

**Measurable success criteria.**
1. `bin/gleipnir-sandbox test` and `lint` dispatch to the command + image read
   from the Tier-3 config (no hard-wired `python -m pytest` / image constant in
   the dispatch path).
2. **Python regression:** the full existing suite runs green driven from the
   config profile (same coverage flags, same `COVERAGE_FILE` scratch routing,
   same fail-closed behaviour). `test_sandbox_cli.py` + `test_sandbox_runtime.py`
   do not regress (amended only where the CLI shape legitimately changed).
3. **Node:** a `node` profile selects the node image and assembles
   `node --test tests/test_sequence_gate.mjs` as the run command — verified via
   the faked-exec harness that the RIGHT image + RIGHT argv are selected from
   config (real image build + real run is an operator hand-off).
4. The config is agent-unwritable AND in the preflight enforcement set: a test
   asserts the preflight REFUSES if the config path were agent-writable
   (mirroring existing per-file boundary tests). **The existing
   `tests/test_preflight_decision.py` suite stays GREEN** after the coupled
   `sandbox/**` (`tolerate_absent=False`) enforcement-path addition — the shared
   `config_root` fixture is updated to include a read-only `sandbox/profiles.toml`
   so no existing test flips CLOSED→REFUSE.
5. No raw toolchain capability leaks: the agent allowlist stays
   `bin/gleipnir-sandbox test|lint` exact-match; dispatch is internal; the verb
   set does NOT widen.
6. Fail-closed everywhere: config missing/malformed/unpinned-image/no-command-
   for-verb all refuse (exit 3), never a silent default or unbounded command.
7. Coverage degrades honestly for node (`unavailable (justified: …)`), never
   faked, never silently dropped.

**Constraints.**
- **Isolation CORE (`runtime.py`) UNCHANGED** (or additive only).
  `build_run_argv(cri, *, repo_root, scratch_dir, cmd, image=IMAGE, extra_env)`
  and `prepare_sandbox_run(cmd, *, image=…, extra_env=…)` already parameterize
  `cmd` and `image` — the generalization lives ENTIRELY in `__main__.py`
  (config read + verb→command/image selection) and a new config-reader module.
- Sandbox CLI stays **stdlib-only Python** (`.gleipnir/decisions/runtime-and-deps.md`).
- Preserve `--network=none`, ro-source + rw-scratch mounts, fail-closed
  orchestration, and **no leaked build capability** (`image_available` still
  never builds; the target `build` verb is NOT added this slice).
- **Do not cage the operator:** the Tier-3 config is operator-authored; the
  image-build subcommand stays operator-only and OFF the agent allowlist; the
  preflight (per `s2-g1-closure.md` Part 0) never restricts the operator's
  escape-hatch agents.
- The agent-facing Tools surface (the verb set) is FIXED and small; onboarding a
  language adds a profile + image, never a new verb or a raw compiler.

---

## 2. Trace

### T1. The Tier-3 config — path + format

- **Path (DECIDED, bounded):** `.gleipnir/sandbox/profiles.toml`
  (a NEW `.gleipnir/sandbox/` Tier-3 directory).
  - *Why a new dedicated path and not `goals/`/`decisions/`:* those subtrees are
    already enforcement-covered, but the sandbox profile is operationally
    distinct (a toolchain-dispatch table, not a goal or a decision record) and
    the operator must be able to reason about it as one file. It is Tier-3
    POLICY (authority over what the arbiter command IS), so it belongs beside
    the other POLICY paths, not in Tier-0.
  - **COUPLED CHANGE (flagged):** `.gleipnir/sandbox/**` is NOT yet in
    `boundary.py` `ENFORCEMENT_PATHS`. A new `EnforcementPath("sandbox/**",
    "sandbox", Posture.RO, "Tier-3 toolchain-dispatch profiles — the Axiom-1
    arbiter command lives here; agent-unwritable so `test` cannot be rewritten
    to a no-op", tolerate_absent=False)` entry MUST be added in the SAME slice.
    `tolerate_absent=False` is DELIBERATE: unlike `plugins/` (absent = no-plugin,
    tolerated), an absent arbiter-config leaves the `test` arbiter UNDEFINED and
    so must REFUSE — a missing arbiter-config is NOT a closed boundary. This edit
    is to `src/gleipnir/preflight/boundary.py`, which is agent-writable `src/`
    today (until S-2 closure), so `gleipnir-code` CAN make it. The CONFIG FILE it
    points at is operator Tier-3 (hand-off). Posture `RO` (not
    `RO_AND_UNREADABLE`): the profile is not a secret; the threat is *write*
    (rewriting the arbiter), and read is fine. **Coupled fixture update (B3):**
    the shared `config_root` fixture in `tests/test_preflight_decision.py` MUST
    gain a read-only `sandbox/profiles.toml` so the ~15+ existing green tests do
    not flip to REFUSE (Assemble step 6).
- **Format (DECIDED): TOML, parsed with `tomllib` (stdlib, Python ≥3.11).**
  - *Why tomllib over json:* (1) stdlib-only satisfied — `tomllib` ships in the
    3.11+ interpreter this core already requires (`runtime-and-deps.md`), no new
    dependency into the S-2 trusted surface; (2) it is **read-only** (there is no
    stdlib TOML *writer*), which is a defense-in-depth fit for a file the code
    must never write; (3) TOML supports comments, so the operator can record the
    D5 coverage justification and the digest-pin provenance inline; (4) an
    operator-authored policy table is more legible/less brittle in TOML (no
    trailing-comma / quoting foot-guns) than JSON. json would also work and is
    stdlib; tomllib wins on the read-only + comments + operator-legibility axes.
- **Schema (per-profile table):**
  ```toml
  # .gleipnir/sandbox/profiles.toml  — Tier-3 POLICY, operator-authored.
  default_profile = "python"

  [profile.python]
  image = "gleipnir-sandbox:latest"      # digest-pinned via the image's own build
  test = ["python", "-m", "pytest", "-p", "no:cacheprovider"]
  lint = ["python", "-m", "compileall", "-q", "src"]
  # coverage: pytest-cov, first-class (coverage-gate.md)
  coverage = { args = ["--cov=src/gleipnir", "--cov-branch", "--cov-report=term-missing"],
               file_env = "COVERAGE_FILE", file_path = "/work/.scratch/.coverage" }
  test_selector_prefix = true            # pytest_args passthrough allowed as SELECTORS only

  [profile.node]
  image = "gleipnir-sandbox-node@sha256:<operator-fills-digest>"
  test = ["node", "--test", "tests/test_sequence_gate.mjs"]
  lint = ["node", "--check", "tests/test_sequence_gate.mjs"]  # or a project linter
  # D5 honest degradation: no coverage tool wired for node this slice.
  coverage = { unavailable = true, justified = "node built-in coverage deferred; zero-dep .mjs seam only" }
  test_selector_prefix = false
  ```
  - **`image` validation rule (CONCRETE, closes the image-substitution vector
    D2 exists to close). The pure reader — no I/O, cannot call `image_available`
    — applies EXACTLY this, and NO shape-pattern that accepts an arbitrary
    `name:tag`:** an `image` value is ACCEPTED **only if** it is EITHER
    - **(a)** the single exact literal string `gleipnir-sandbox:latest` — the
      grandfathered operator-built self-host image, accepted for backward-compat
      with the existing `Containerfile` (matched by **string equality**, not a
      tag pattern); OR
    - **(b)** a digest-pinned reference matching `name@sha256:<64 lowercase hex>`
      — validated by a **strict format check**: the value contains exactly one
      `@sha256:` separator and the part after it is exactly 64 hex characters.

    **EVERYTHING ELSE IS REFUSED** (`ProfileError` → exit nonzero, run nothing):
    any other bare tag, any `:latest` other than the one grandfathered literal,
    any unpinned reference, any `@sha256:` with a non-64-hex digest. There is
    deliberately NO rule that accepts a generic `name:tag` shape — that would
    silently reopen the image-substitution vector. See edge case 5.
  - `test`/`lint` are **argv lists** (never a shell string) — no shell parsing,
    no compound-command surface, consistent with the `bin/gleipnir-sandbox` shim
    rationale (no shell branching = no bypass).

### T2. The verb→command dispatch in `__main__.py`

- A new `_cmd_test`/`_cmd_lint` read the resolved profile and assemble the run
  command from `profile.test` / `profile.lint` (the argv list), plus — for
  `test` — the profile's `coverage.args` appended when coverage is available.
- **`pytest_args` passthrough is constrained to test SELECTORS, never a command
  root.** Today `_cmd_test` accepts `args.pytest_args` (REMAINDER after `--`).
  The dispatch must only ever APPEND those tokens to the *configured* test argv;
  it must NEVER let them replace or become the command root. Concretely: the run
  command is always `[*profile.test, *coverage_args, *extra_selectors]` — the
  configured `profile.test` is always the head. When `test_selector_prefix` is
  false (node), the extra-args passthrough is disabled (node's `--test` takes a
  file arg, not pytest selectors); passing extra args to a non-selector profile
  is refused rather than blindly forwarded. This preserves the property that the
  agent influences *which tests*, never *what command runs*.
- `extra_env` is assembled from the profile's `coverage.file_env`/`file_path`
  (python) or omitted (node). This flows into the UNCHANGED
  `prepare_sandbox_run(..., extra_env=…)`.
- `image` passed to `prepare_sandbox_run(..., image=profile.image)` — the
  UNCHANGED runtime does the fail-closed `image_available` check (never builds).
- **Image comes ONLY from the selected profile — remove the residual `--image`
  contention (minor).** Today `_cmd_test`/`_cmd_lint` call
  `prepare_sandbox_run(..., image=args.image)`, and `__main__.py` carries a
  top-level `--image` argparse flag (`default=SANDBOX_IMAGE`) plus the
  `SANDBOX_IMAGE = "gleipnir-sandbox:latest"` module constant. In this slice the
  `test`/`lint` DISPATCH path takes `image` SOLELY from `profile.image`; the
  `--image` flag and the `SANDBOX_IMAGE` constant are REMOVED from the dispatch
  path (`_cmd_test`/`_cmd_lint` no longer read `args.image`). So the criterion
  "no hard-wired image in the dispatch path" is met in CODE, not by a
  permission-map accident. (The operator-only `image-build`/bootstrap subcommand
  is OFF the agent allowlist and MAY keep its own image argument for building —
  it is not on the agent-facing dispatch path.)

### T3. Config reader (new module)

- New `src/gleipnir/sandbox/profiles.py` (stdlib-only): pure functions
  `load_profiles(config_root: Path) -> Profiles` and
  `resolve_profile(profiles, name: str | None) -> Profile`, plus a frozen
  `Profile` dataclass `{ image, test_argv, lint_argv, coverage, test_selector_prefix }`.
  - Mirrors the `runtime.py` shape: a **pure, fully unit-testable core** (parse +
    validate + select) with the file read as the only thin edge (inject the
    path / bytes in tests). Fail-closed classification like
    `boundary.py`/`runtime.py`: a `ProfileError(SandboxError)` subclass for every
    refuse case, so `__main__.py`'s existing `except SandboxError -> exit 3`
    path catches them uniformly (no new exit code).
- **Config location — injectable for TESTS ONLY, fixed Tier-3 in production
  (B2):** `load_profiles(config_root: Path)` takes an EXPLICIT `config_root`
  parameter; the reader resolves `config_root / "profiles.toml"`. In PRODUCTION
  the CLI passes the fixed Tier-3 default
  `_repo_root() / ".gleipnir" / "sandbox"` — computed internally, NOT from any
  argument. In TESTS the harness passes a `tests/`-local fixture root
  (`tests/fixtures/`) IN-PROCESS by calling the CLI/`main()` entry with the
  injected `config_root`, so the Python regression proves against
  `tests/fixtures/sandbox_profiles.toml` without touching `.gleipnir/**`.
- **PROHIBITED (foreclosed here so no implementer improvises it):** the
  agent-facing invocation `bin/gleipnir-sandbox test|lint` MUST NOT accept a
  `--config-path`/`--config-root` CLI argument, and MUST NOT read the config
  root from an environment variable. The config path is FIXED to the Tier-3
  location in the agent-facing dispatch path. The injectable `config_root` is an
  IN-PROCESS test-harness seam ONLY (the test calls `main(..., config_root=…)`
  or a load helper directly) — it is never an agent-reachable arbiter-selection
  surface. Any env-var or CLI-flag override of the config location is explicitly
  disallowed by this plan.

### T4. Image selection from config

- python profile: `image = "gleipnir-sandbox:latest"` — the EXISTING image the
  `Containerfile` builds; unchanged, digest pinned in that Containerfile.
- node profile: a **NEW `Containerfile.node`** (operator hand-off) —
  `FROM docker.io/library/node:<ver>-slim@sha256:…`, `--network=none`-runnable,
  node preinstalled, **no `ENTRYPOINT`** (the run argv is supplied per-run by the
  unchanged `build_run_argv`), no source/keys/creds baked in. The operator
  builds and pins the digest, then records it in `profiles.toml`.
- The reader accepts an `image` value ONLY per the T1 rule: (a) the exact
  literal `gleipnir-sandbox:latest` (string equality, grandfathered self-host
  image), OR (b) a strict `name@sha256:<64 hex>` digest-pinned reference. No
  generic `name:tag` shape is ever accepted. `runtime.image_available`
  (unchanged) then fail-closes at RUN time if the (already-validated) image
  reference is absent — refuse with the existing actionable message.

### T5. The `build` naming-collision resolution (DECIDED)

- Today `_cmd_build` = "build the sandbox IMAGE" (operator/bootstrap, OFF the
  agent allowlist). The target-project `build` verb (compile C/C++/Rust) is a
  DIFFERENT concept.
- **Resolution:** rename the image-build subcommand `build -> image-build`
  (operator-only, OFF the agent allowlist; keep the same behaviour). This frees
  the word `build` so a future target-`build` verb (compile step) can be added
  without collision. The target-`build` verb is **DEFERRED this slice** (D3:
  python/node need no compile step) — but the naming is resolved now so it is
  not a trap.
- **Agent surface impact: NONE.** The agent allowlist is
  `bin/gleipnir-sandbox test|lint` exact-match — `build`/`image-build` was never
  on it. The rename touches only `__main__.py`'s argparse verb name + the
  operator-facing help text + `test_sandbox_cli.py`'s build tests (rename
  `["build"]` -> `["image-build"]`). Confirm the agent surface does not widen:
  still exactly `test` and `lint`.

### T6. Honest coverage degradation for node (D5)

- python: coverage args come from the profile, printed as today (line+branch +
  term-missing). Unchanged behaviour, now config-sourced.
- node: profile declares `coverage.unavailable = true` + `justified = "…"`. The
  CLI prints `coverage: unavailable (justified: <reason>)` to stderr on a node
  `test` run and does NOT append any coverage args and does NOT fabricate a
  number. It NEVER silently drops the metric line.

### T7. Agent allowlist — confirm no widening

- `.gleipnir/agents/gleipnir-code.md` bash allowlist stays exactly
  `bin/gleipnir-sandbox test` and `bin/gleipnir-sandbox lint` (+ `./` variants).
  Dispatch is internal to the CLI. **No allowlist edit is part of this slice**
  (and `gleipnir-code` cannot edit `.gleipnir/**` anyway). A Stress-test check
  asserts the surface is unchanged.

### Edge cases (all fail-closed → exit 3, actionable message, never host-run)

1. **Config file missing** → `ProfileError` "sandbox profile config not found at
   <path>; the operator must author it (Tier-3 policy)". Never default to
   `python -m pytest`.
2. **Config malformed** (tomllib parse error / wrong shape / missing required
   key) → `ProfileError` naming the defect. Never a partial/default profile.
3. **Requested profile not present** (or `default_profile` names a missing
   profile) → refuse; never silently pick another.
4. **Verb has no configured command** (e.g. profile omits `lint`) → refuse for
   that verb; NEVER a silent default command.
5. **Image not per the T1 rule** → refuse (D2), via the pure reader's string-
   equality + strict `@sha256:` check. Concretely: `gleipnir-sandbox:latest`
   (exact literal) → ACCEPT; `name@sha256:<64 hex>` → ACCEPT;
   `someimage:latest` (arbitrary bare `:latest`) → REFUSE; `myimg:1.2`
   (non-digest tag) → REFUSE; `name@sha256:<not-64-hex>` → REFUSE. There is NO
   shape rule that accepts an arbitrary `name:tag`.
6. **`test`/`lint` value is a string, not an argv list** → refuse (no shell
   surface). Empty argv → refuse.
7. **Coverage absent** → report `unavailable (justified: …)`; if `unavailable`
   is set without a `justified` reason → refuse (D5: never silently drop —
   absence must be *justified*, not blank).
8. **Extra passthrough args on a non-selector profile** (node) → refuse rather
   than forward (T2).

---

## 3. Link (validated before building)

- **CORE already parameterized (verified by reading `runtime.py`):**
  `build_run_argv(..., cmd, image=IMAGE, extra_env=())` appends `[image, *cmd]`;
  `prepare_sandbox_run(..., image=…, extra_env=…)` forwards both. So a node
  command + node image flow through the isolation core with ZERO core change —
  the constraint holds. Confirmed by `test_sandbox_runtime.py`
  (`test_build_run_argv_appends_cmd_after_image`,
  `test_build_run_argv_uses_requested_cri_and_rm`).
- **Faked-exec harness exists (verified in `test_sandbox_cli.py`):** the
  `captured_exec` fixture and `monkeypatch`-ed `prepare_sandbox_run` already
  prove "the RIGHT argv was assembled" without a container. This is exactly the
  seam the node dispatch test uses.
- **`.mjs` runnability (validated by reading `test_sequence_gate.mjs`):** it is
  zero-dep except `node:` builtins and a `.ts` import of
  `../.gleipnir/plugins/sequence-gate.ts`. Runs via `node --test
  tests/test_sequence_gate.mjs`. **Caveat surfaced (operator hand-off):** the
  `.ts` import requires a Node with type-stripping (`--experimental-strip-types`
  / Node ≥22.6, or ≥23 where it is on by default). The node image the operator
  builds MUST be a version that strips TS types, or the profile's `test` argv
  must include the strip flag. This is a hand-off detail, not a blocker for the
  dispatch-logic slice.
- **Preflight enforcement mechanism (validated by reading `boundary.py`):**
  `ENFORCEMENT_PATHS` is a data tuple; adding an entry is the documented,
  review-caught extension (the module comment explicitly says a forgotten entry
  must be caught by review, not globbed). `Posture.RO` + directory `**` walk +
  per-file write-probe is exactly the machinery that will prove the config is
  agent-unwritable. The per-file walk (`_collect_file_probes`) already handles a
  directory containing files — so `sandbox/profiles.toml` under a `sandbox/`
  entry is covered by the existing walk logic.
- **Coverage policy (validated by reading `coverage-gate.md`):** two-metric,
  branch-authoritative, reported/justify-below. D5's honest-degradation path is
  consistent — node reporting `unavailable (justified)` is the "never silently
  drop" rule applied to a toolchain with no wired coverage yet.
- **Stdlib-only (validated by `runtime-and-deps.md`):** `tomllib` is stdlib in
  the ≥3.11 interpreter already required. No new trusted-surface dependency.

---

## 4. Assemble (test-first build order)

Each step: write/adjust tests first, then make them pass, run
`bin/gleipnir-sandbox test`, report pass count + line+branch coverage.

1. **Config schema + reader (`profiles.py`), pure + fail-closed.** Tests first
   (`tests/test_sandbox_profiles.py`): load valid python+node profiles; resolve
   by name + default; every edge case in §2 → `ProfileError` (missing file,
   malformed, unknown profile, missing verb command, image-not-per-T1-rule,
   string-not-argv, empty argv, coverage-unavailable-without-justification).
   **Image-rule assertions (B1): `someimage:latest` → REFUSE; `myimg:1.2` →
   REFUSE; `name@sha256:<non-64-hex>` → REFUSE; a valid `name@sha256:<64 hex>` →
   ACCEPT; the exact literal `gleipnir-sandbox:latest` → ACCEPT.** Then implement
   the reader (tomllib, frozen `Profile`, `ProfileError(SandboxError)`) — the
   image check is string equality for the grandfather case and a strict
   `@sha256:<64 hex>` format check otherwise, with NO generic `name:tag` accept.
2. **Verb dispatch in `__main__.py` reads the profile.** Amend
   `test_sandbox_cli.py`: `test` assembles `[*profile.test, *coverage.args,
   *selectors]` with `COVERAGE_FILE` from the profile; `lint` assembles
   `profile.lint`; passthrough constrained to selectors (head is always the
   configured argv); `SandboxError`/`ProfileError` → exit 3, `captured_exec == []`.
   Then implement config-driven `_cmd_test`/`_cmd_lint` (delete the hard-wired
   `python -m pytest` / `compileall` / `_COVERAGE_ARGS` literals, sourced from
   the profile now). **Also remove the residual `--image` argparse flag and the
   `SANDBOX_IMAGE` module constant from the dispatch path (minor): `_cmd_test`/
   `_cmd_lint` stop reading `args.image` and pass `image=profile.image` only.**
   Amend the `test_sandbox_cli.py` tests that asserted `--image`/`SANDBOX_IMAGE`
   behaviour on `test`/`lint` accordingly (the operator-only `image-build` path
   keeps its own image arg).
3. **Fail-closed cases wired end-to-end through `main()`** (missing/malformed
   config, unknown profile, no-command-for-verb, unpinned image) → exit 3, never
   executes. (Tests in step 1 cover the reader; step 3 covers the CLI edge.)
4. **Python regression via config — against a `tests/`-LOCAL FIXTURE, not the
   live Tier-3 file (B2).** The agent authors
   `tests/fixtures/sandbox_profiles.toml` with a `[profile.python]` matching
   today's exact pytest + coverage flags + scratch `COVERAGE_FILE`, and drives
   the CLI with `config_root=tests/fixtures` INJECTED IN-PROCESS (never a CLI
   flag / env var). The full suite must be green with the same coverage output
   as before — the regression proof that config-driven == prior behaviour.
   Authoring the REAL live `.gleipnir/sandbox/profiles.toml` is entirely an
   OPERATOR HAND-OFF (the agent/planner never writes `.gleipnir/**`; production
   defaults to that Tier-3 path).
5. **Node dispatch selects node image + node command (faked exec).** Test:
   `main(["test"])` with the node profile selected assembles argv containing the
   node `@sha256` image and `node --test tests/test_sequence_gate.mjs`, verified
   via `captured_exec`; a node `test` run prints `coverage: unavailable
   (justified: …)` and appends no coverage args; extra passthrough args on the
   node profile → refuse. (Real node-image build + real `.mjs` run = operator
   hand-off, step 7.)
6. **Preflight `ENFORCEMENT_PATHS` entry for the config — with the shared
   fixture update (B3, the file most touched by this coupled change).** Add
   `EnforcementPath("sandbox/**", "sandbox", Posture.RO, …, tolerate_absent=False)`
   in `boundary.py`. **`tolerate_absent=False` is DELIBERATE for `sandbox/**`:**
   a missing arbiter-config is NOT a closed boundary — an absent profiles.toml
   means the Axiom-1 arbiter command is undefined, which must REFUSE, matching
   the arbiter-integrity intent (this is UNLIKE `plugins/`, which tolerates
   absence because an absent plugin is simply no-plugin, not a neutered
   arbiter). **Because `tolerate_absent=False`, the shared `config_root` fixture
   in `tests/test_preflight_decision.py` (used by ~15+ existing green tests —
   `TestCollectPathProbes`, `TestBlockerOneFalseClosedOnDirectoryEntries`,
   `TestResidualFalseClosedSymlinkedSubdirEscape`, `TestRunPreflight`, etc.)
   MUST be updated to create a `sandbox/` dir containing a read-only
   `profiles.toml`**, or those tests flip CLOSED→REFUSE on a
   missing-enforcement-path `PROBE_ERROR` for `sandbox`. Update that fixture in
   this step (add `(root / "sandbox").mkdir(); (root / "sandbox" /
   "profiles.toml").write_text(...)` RO) so the existing suite stays green. New
   tests (`test_preflight_boundary.py` style): the config path is in the probed
   set; a writable `sandbox/profiles.toml` forces `NOT_CLOSED` → `REFUSE`
   (mirroring the existing per-file writable-file test); a read-only one
   contributes CLOSED; an ABSENT `sandbox/` refuses (`tolerate_absent=False`).
   This is the arbiter-cannot-be-neutered proof.
7. **Build-verb rename.** `build -> image-build` in argparse + help + the
   `test_sandbox_cli.py` build tests. Confirm the agent allowlist is untouched
   and the verb set is still `test|lint|image-build` with only `test|lint`
   agent-facing.

**Operator hand-offs occur AFTER agent steps 1–7:** author the real Tier-3
`profiles.toml` (agent authors only a `tests/`-local fixture, never the live
Tier-3 file), build+pin the node image, run the real `.mjs`, and persist the
decision record.

---

## 5. Stress-test (concrete acceptance checks)

1. **Arbiter cannot be neutered by the agent.** The preflight includes
   `.gleipnir/sandbox/**` (`tolerate_absent=False`); a test asserts that if
   `sandbox/profiles.toml` were agent-writable the preflight yields
   `NOT_CLOSED`/`REFUSE` (so the agent can never rewrite `test` to `true`/no-op),
   a read-only config contributes `CLOSED`, and an ABSENT `sandbox/` REFUSES
   (a missing arbiter-config is not a closed boundary) — mirroring the existing
   `agents/*.md` per-file boundary tests.
1b. **The existing `tests/test_preflight_decision.py` suite stays GREEN.** After
   the coupled `sandbox/**` addition, all ~15+ existing tests using the shared
   `config_root` fixture still pass because the fixture now creates a read-only
   `sandbox/profiles.toml`; none flips CLOSED→REFUSE on a missing-path
   `PROBE_ERROR`.
2. **Agent verb surface does NOT widen.** Assert the parser exposes exactly
   `test`, `lint`, `image-build`; assert (documented in the plan + a fixture
   check) the `gleipnir-code.md` allowlist stays `bin/gleipnir-sandbox test|lint`
   exact-match; no raw `node`/`cargo`/`gcc`/`make` verb exists.
3. **Config missing / malformed / image-not-per-T1-rule / no-command-for-verb**
   each → exit 3, `captured_exec == []` (never runs on host, never a silent
   default). **Image rule (B1) asserted explicitly: `someimage:latest` REFUSE,
   `myimg:1.2` REFUSE, `name@sha256:<64 hex>` ACCEPT, `gleipnir-sandbox:latest`
   ACCEPT** — the pure reader distinguishes the grandfathered literal from an
   arbitrary bare tag, so no image-substitution vector reopens.
4. **Python regression, full suite green driven from config.** `bin/gleipnir-
   sandbox test` runs the whole suite in-container via the python profile, with
   the same coverage flags and ≥ prior coverage; `test_sandbox_runtime.py` and
   the amended `test_sandbox_cli.py` pass.
5. **Node dispatch selects node image + node command.** Faked-exec test proves
   the assembled argv contains the node `@sha256` image and
   `node --test tests/test_sequence_gate.mjs` (right image + right command from
   config). **Image comes ONLY from the profile (minor):** assert the `test`/
   `lint` dispatch path has no `--image` flag and no `SANDBOX_IMAGE` constant —
   `image` is `profile.image` in CODE, not by permission-map accident.
6. **Coverage degrades honestly for node.** A node `test` run emits
   `coverage: unavailable (justified: …)` and appends no `--cov` args; setting
   `unavailable` without a justification is refused (never faked, never dropped).
7. **Isolation core UNCHANGED (or additive only).** `runtime.py` diff is empty
   or additive; `test_sandbox_runtime.py` unmodified and green;
   `--network=none` / ro-source / rw-scratch / fail-closed all still asserted.
8. **Stdlib-only.** No non-stdlib import in `profiles.py` or `__main__.py`
   (`tomllib` is stdlib); the runtime-and-deps conformance grep still passes.
9. **No leaked build capability.** `image_available` still never builds; no
   target-`build` verb added; `image-build` stays operator-only, off the agent
   allowlist.

---

## 6. Execution Workflow

- **Role sequencing (for the orchestrator, not me):** spec-review → test-authoring
  → code → quality → git, per the bound roster. This plan is the input; I
  sequence nothing.
- **Implementer protocol (`gleipnir-code`):**
  - Test-first per Assemble; do not weaken a test to make it green.
  - Touch only `src/gleipnir/sandbox/profiles.py` (new),
    `src/gleipnir/sandbox/__main__.py`, `src/gleipnir/preflight/boundary.py`
    (the one `ENFORCEMENT_PATHS` entry), and `tests/**` (including the new
    `tests/fixtures/sandbox_profiles.toml`). Do NOT touch `runtime.py` except
    additively (constraint). Do NOT touch `.gleipnir/**` (denied by capability)
    — the live Tier-3 `profiles.toml` is an operator hand-off; the agent proves
    the regression against a `tests/`-local fixture config injected IN-PROCESS
    via `config_root` (B2). Do NOT add a `--config-path`/`--config-root` CLI arg
    or a config-root env var to the agent-facing dispatch — the production path
    is fixed to the Tier-3 location; the injection is test-harness-only.
  - Verify via `bin/gleipnir-sandbox test`; report pass count + line+branch
    coverage; justify anything below 85% (coverage-gate.md).
  - Cannot commit/push; report back for the git stage.
- **Fail-closed discipline:** every new refuse path returns exit 3 via a
  `SandboxError` subclass and an actionable message; never a host fallback,
  never a silent default command, never a fabricated coverage number.
- **After merge:** the operator performs the hand-offs (below) and persists the
  decision record; this plan file is Tier-0 disposable.

---

## Operator hand-offs (Tier-3 / out-of-agent-reach)

1. **The Tier-3 config FILE** — `.gleipnir/sandbox/profiles.toml`, authored by
   the operator (agent-unwritable). Use the schema in §T1 (python profile
   mirroring today's pytest+coverage flags; node profile with the built node
   image's pinned digest). The agent's tests use a `tests/`-local fixture copy,
   never this live file.
2. **The node image** — a new `Containerfile.node`
   (`FROM node:<ver>-slim@sha256:…`, node preinstalled, `--network=none`-runnable,
   no `ENTRYPOINT`, no source/keys), built by the operator via the renamed
   `bin/gleipnir-sandbox image-build`, its digest pinned into `profiles.toml`.
   Ensure the node version strips TS types (Node ≥22.6 with
   `--experimental-strip-types`, or ≥23) so the `.mjs`'s `.ts` import runs — or
   add the strip flag to the profile's `test` argv.
3. **Real `.mjs` run** — after the node image exists, run
   `bin/gleipnir-sandbox test` on the node profile against a repo checkout to
   confirm `test_sequence_gate.mjs` passes in-container (the real close of the
   dogfood node seam). Deferred from the agent slice per recommendation (c).
4. **`boundary.py` `ENFORCEMENT_PATHS` addition is agent-writable `src/`** (until
   S-2 closure) — so `gleipnir-code` CAN add the `sandbox/**` entry as part of
   this slice. The CONFIG FILE it points at is operator Tier-3. Once added, the
   operator's activation steps from `s2-g1-closure.md` (chmod the enforcement
   subtree — now including `.gleipnir/sandbox/` — OS-read-only to the agent uid,
   run `bin/gleipnir-preflight`) cover the new path automatically.
5. **Durable decision record** —
   `.gleipnir/decisions/language-agnostic-sandbox.md`, operator-authored,
   persisting: D1–D6; the arbiter-is-Tier-3 property (config unwritable +
   enrolled in preflight `ENFORCEMENT_PATHS`); the `build -> image-build` rename
   (freeing `build` for a future compile verb); and the DEFERRED fetch-then-seal
   offline-deps seam (E-1-grade, explicitly out of this slice).

---

## Recommendation on design question (c): test dispatch now vs build node image

**RECOMMEND: validate the DISPATCH LOGIC now with a faked exec; defer the real
node-image build + real `.mjs` run to an operator hand-off.**

Rationale (bounded, decide-and-justify):
- The value this slice adds is the **generalization + arbiter-integrity**: the
  CLI reads a Tier-3 config and dispatches the right command to the right image,
  fail-closed, without widening the agent surface or leaking a toolchain. That is
  entirely provable with the EXISTING faked-exec harness (`captured_exec` +
  monkeypatched `prepare_sandbox_run`) — the same pattern the current
  `test_sandbox_cli.py` uses to prove the python path assembles the right argv
  without a container.
- Building the node image requires an operator to build + pin a digest (D2) and
  resolve the Node TS-type-stripping caveat — both **operator Tier-3 actions**,
  not agent work, and both would block an otherwise-complete agent slice on an
  environment-specific artifact.
- Fail-closed already guarantees honesty: if the node image is absent, the
  UNCHANGED `image_available` refuses — so shipping the dispatch logic before
  the image exists cannot silently "pass" a run that never happened.
- This keeps the agent slice bounded (Sonnet-appropriate: plan + pre-written
  tests are the arbiter) and pushes the one genuinely environment-coupled,
  operator-authority step (build+pin+run) to where it belongs.
- **Not a material design decision** (no lasting/hard-to-reverse tradeoff): the
  real run is strictly additive after the image exists; deferring it changes
  nothing about the code shape. So it is decided here, not escalated.

## No material decisions escalated

Every choice in this plan is bounded by the LOCKED D1–D6 brief or is a
mechanical/reversible detail (config path, tomllib, faked-exec sequencing,
build-verb rename). None is a material tradeoff requiring operator convergence
beyond the D1–D6 already decided; the only operator actions are the Tier-3
hand-offs above (authoring policy artifacts + persisting the decision record),
which are operator-authority by tier, not unresolved design questions.
