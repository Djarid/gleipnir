# Decision: language-agnostic sandbox executor (config-driven toolchain dispatch)

**Status:** decided and implemented; converged via the orchestrator-surfaced
decision gate; plan `../plans/language-agnostic-sandbox.md` (spec-review
APPROVED, 2 rounds); implementing commit `91d1127`. Verified:
`bin/gleipnir-sandbox test` = 438 passed, 11 skipped, 93% coverage; preflight
suite green; `runtime.py` unchanged.

## The reframe

Gleipnir guards target projects in any language (C, C++, Python, Rust, JS, TS).
The enforcement CORE is Python stdlib-only by a separate decision
(`runtime-and-deps.md`) — that governs the GUARD code, not target-project
language. The sandbox executor was previously under-scoped to the self-hosting
Python case; this generalises it. The isolation core (`runtime.py`:
`build_run_argv`/`prepare_sandbox_run` already parameterize `cmd`/`image`,
`--network=none`, ro-source mount, `image_available` never-builds) was already
language-agnostic and is UNCHANGED; only the CLI + a new Tier-3 config layer
changed.

## Converged decisions (operator-decided; LOCKED)

- **D1+D4 (cardinal, coupled):** a Tier-3 POLICY config file
  (`.gleipnir/sandbox/profiles.toml`, operator-authored, agent-unwritable)
  declares the per-target verb->command mapping {image, test argv, lint argv,
  optional coverage}. The agent-facing surface stays a small fixed exact-match
  verb set (test/lint/[build]); the sandbox reads the config and dispatches the
  verb to the configured toolchain command. The agent never gains raw
  cargo/gcc/node. CARDINAL PROPERTY: the test command IS the Axiom-1 arbiter, so
  the config MUST be Tier-3 AND enrolled in the G-1 preflight enforcement path
  set (`boundary.py` added `EnforcementPath("sandbox/**", RO,
  tolerate_absent=False)`) so the preflight REFUSES if `profiles.toml` is
  agent-writable or absent. This closes the "neuter the arbiter to a no-op inside
  perfect isolation" hole (the E-1 lesson: isolation protects where code runs,
  not what command is the arbiter). The configured argv is always the fixed
  command head; agent passthrough is constrained to test selectors, never the
  command root; `config_root` is fixed to the Tier-3 path in production and
  injectable in-process for tests only (no `--config-path`/env override the agent
  can pass). Auto-detection may only suggest a profile to the operator, never
  decide the command at runtime.
- **Image strategy (D2):** per-toolchain, operator-built, digest-pinned images.
  STRICT image rule (`profiles.py::_validate_image`): accept ONLY the exact
  literal `gleipnir-sandbox:latest` (grandfathered self-host image) OR a
  `name@sha256:<64 lowercase hex>` digest ref; every other/arbitrary/unpinned tag
  is refused (closes image-substitution).
- **build->image-build rename:** the old `build` subcommand (build the sandbox
  image, operator-only, off the agent allowlist) is renamed `image-build`,
  freeing `build` for a future target-compile verb (deferred).
- **Offline-deps (D3):** pre-baked deps in the digest-pinned image. The general
  offline-deps problem (arbitrary target dep trees vs `--network=none`) is
  DEFERRED; a fetch-then-seal network phase is a separate later decision
  (E-1-grade — it re-opens egress).
- **Coverage (D5):** honest optional-with-recorded-justification per profile;
  per-language adapter as onboarded; never silently drop the metric (report
  "coverage: unavailable (justified: ...)"). Python keeps pytest-cov.
- **First slice (D6):** generalise the CLI to read the Tier-3 config + dispatch,
  proven with Python (regression, full suite green through the config) + a node
  profile (dispatch proven via faked exec; the real node run + node image are a
  hand-off).

## Verification

438 passed, 11 skipped, 93% coverage in-sandbox; `test_preflight_decision.py`
green (the coupled `boundary.py` change did not regress it); `runtime.py`
unchanged (git-confirmed); agent verb surface unchanged (exactly `test|lint`). A
build finding — the self-host test path required a not-yet-authored Tier-3
`profiles.toml` (a circular dependency bricking `make test`) — was resolved by
authoring the live `.gleipnir/sandbox/profiles.toml`.

## Node profile REAL RUN — CLOSED (this session)

No longer dispatch-proven only; run for real, end-to-end, in the bounded
container:
- **Image:** `Containerfile.node` (`FROM node:22-slim`, digest-pinned), built to
  `localhost/gleipnir-sandbox-node`.
- **Live profile:** `[profile.node]` in `.gleipnir/sandbox/profiles.toml`,
  digest-pinned, `--experimental-strip-types` (the .mjs imports a `.ts`; node
  22.23.1 in-image). `default_profile` left `"python"` — self-host untouched.
- **Result:** `tests/test_sequence_gate.mjs` — **16 passed, exit 0**, under
  `--network=none`, INCLUDING the dogfood block (live-Python-Driver-minted PLAN
  bridge validated byte-for-byte by the TS/JS hook). Python↔JS HMAC contract now
  agent-verified. No regression (python self-host still green).

## Broker profile — added (broker-MCP session)

A third live profile, `[profile.broker]`, runs the broker MCP servers' test
suite (`tests/test_broker_*.py`) in a dedicated image `gleipnir-sandbox-broker`
(digest-pinned; `./Containerfile.broker` = `python:3.12-slim` + pytest/pytest-cov
+ `mcp>=1.0,<2`). Separate image (not the main one) so the MCP SDK's large
transitive tree (pydantic/starlette/uvicorn/cryptography/httpx) is isolated to
broker testing; the lean self-host image is unchanged, `default_profile` stays
`python`. A `conftest.py` `collect_ignore` skips the mcp-dependent
`test_broker_tool_surface.py` under the python profile so the two don't collide.

## Known not-yet-closed / seams

- Rust/C/C++ profiles + the general offline-deps/fetch-then-seal decision.
- A future target-`build` verb.
- The S-2 mount + terminal closure that makes `.gleipnir/` structurally (not just
  preflight-verified) unwritable.
