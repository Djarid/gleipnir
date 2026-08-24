# Plan: `pi` sandbox profile — toolchain to run the S1 pi.dev slice's TS tests

> **Status: ATLAS plan (Tier-0, transient).** A prerequisite-dependency plan:
> before `gleipnir-code` can run the S1 slice's TypeScript tests
> (`pi-dev-replatform-first-slice.md`), the S-2 sandbox needs a `pi` profile
> whose image can build/test a TypeScript pi.dev package. Same causal-dependency
> shape as the earlier "D5 sidecar-write required the sandbox `--profile` flag"
> precedent (`SESSION-STATE.md`). This plan is **ONLY** the sandbox/toolchain
> infrastructure — it does not touch the S1 pi-package's own content
> (`roleTable.ts`, `enforcement.ts`, etc.); that stays in
> `pi-dev-replatform-first-slice.md`'s scope.
>
> **Pipeline routing (Axis-1 / Axis-2, `../stage-role-map.md`):** `P` includes
> `Containerfile.pi` (a `Containerfile*` — Axis-1 disqualifier `X` member) and
> `.gleipnir/sandbox/profiles.toml` (Axis-2(a) enforcement-path `E` member,
> Tier-3 POLICY) and `.gleipnir/agents/gleipnir-code.md` (`E` member, carries a
> `bash:`/`permission:` grant block — Axis-2(b)) and `tests/**` (Axis-1 `X`).
> Because `P ∩ X ≠ ∅` (via `Containerfile.pi` and `tests/**`), this plan is
> **NOT track-eligible for the prose/config-only track at all** — the Axis-1
> eligibility gate disqualifies it outright. It therefore runs the **standard
> full 8-stage pipeline**, which already carries separate `spec-review` and
> `quality` stages by default (no collapsed-review/attestation-table construct
> from the prose/config-only-track section applies here). This is the correct,
> intended routing per the delegation's Constraints.

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Whether to build the `pi` profile at all | Build it, mirroring the `node`/`broker` profile pattern | Reuse `node` profile; skip | **Operator-converged** (delegation preamble: "operator has already converged: build this properly"). Not reopened. The existing `node` profile hardcodes two zero-dep `.mjs` files and installs no npm packages — it cannot resolve S1's peer deps or compile TS. |
| D2 | Peer-dep version pins (top-level) | The versions npm resolves TODAY from pi's graph: `pi-coding-agent@0.84.2`, `pi-agent-core@0.84.2`, `pi-ai@0.84.3`, `pi-tui@0.84.3`, `typebox@1.3.7`, `typescript@5.9.3` | Guessing; each package's own `latest`; `"*"` in the image | Reproducibility-faithful for the SIX literal top-level pins: install what pi's dependency graph resolves to now, not a floating range. Re-verified against the npm registry this session (see Link) — `pi-ai`/`pi-tui` `/latest` are **0.84.3** (both updated 2026-08-24), which `^0.84.2` resolves to; `pi-coding-agent`/`pi-agent-core` `/latest` are 0.84.2. `typebox` pinned to **1.3.7** (what all three pi packages depend on), NOT typebox's own latest 1.3.18 — the image must match pi's resolved graph, and typebox 1.x is ESM-only. **Caveat (see D8):** transitive deps below these six float without a lockfile. |
| D3 | TypeScript test runner + peer-dep resolution mechanism | Node built-in `node:test` + `--experimental-strip-types` (proven in the `node` profile for `.ts`) + `tsc --noEmit` (lint verb). **Peer deps baked into `/node_modules` at the FILESYSTEM ROOT** (outside the `/work` bind-mount), with the **root-level ancestor-walk reachability treated as EMPIRICALLY UNPROVEN and gated by a mandatory build+run smoke test (Assemble §1a)** — NOT asserted. NOT `-g`/`NODE_PATH` | vitest/jest/tsx; `npm install -g`; `NODE_PATH` prefix; per-profile extra `node_modules` bind-mount (a `runtime.py` change — escalated, D9) | Runner: lowest-new-dependency (delegation's preference); `node:test` already runs mixed `.mjs`/`.ts` with type imports in the `node` image. **Resolution mechanism (the Finding-1 fix) — with a precise, honest caveat:** the repo is bind-mounted READ-ONLY at `/work` at run time, so anything baked under `/work/**` is masked; a `-g` prefix is NOT an ancestor of `/work/pi-package/`; and **Node's ESM resolver ignores `NODE_PATH` entirely** (nodejs.org/api/esm.html: "No `NODE_PATH`", re-verified live this session). So peers MUST live in a `node_modules` that (i) survives the mount and (ii) is reached by Node's `node_modules` ancestor-walk from `/work/pi-package/test/`. The ONLY candidate outside the `/work` mount is `/node_modules` (root) — every other ancestor (`/work/pi-package/test/node_modules`, `/work/pi-package/node_modules`, `/work/node_modules`) is under the ro `/work` mount and masked. **CAVEAT (the load-bearing uncertainty this plan refuses to paper over):** the ESM `PACKAGE_RESOLVE` spec (nodejs.org/api/esm.html, re-read live this session) phrases the walk as *"While parentURL is not the file system root, … resolve `node_modules/` relative to parentURL; set parentURL to its parent"* — read literally, the iteration where `parentURL` would be `/` is EXCLUDED by the guard, so `/node_modules` is only reached if the reference implementation includes the root level (which real-world Node is widely observed to do, as the terminal `/node_modules` fallback). This spec-text-vs-observed-behaviour ambiguity is EXACTLY why the reviewer said "verify empirically, do not assert." Therefore `/node_modules`-root is the CHOSEN in-scope mechanism BUT is proven ONLY by the Assemble §1a real `podman build`+`run --network=none -v <tmp>:/work:ro` smoke test — gleipnir-plan holds no build capability, so §1a is an EXPLICIT gating handoff to gleipnir-code/operator, not a planning assertion. If §1a shows `ERR_MODULE_NOT_FOUND`, the mechanism is refuted → escalate D9 (the only robust fallback is a `runtime.py` extra-mount, a material decision), do NOT hack around it. Secondary fallback (orthogonal, runner-level): `--experimental-transform-types` if S1 test files use non-strippable TS; runner stays `node:test`. |
| D9 | Fallback IF §1a refutes `/node_modules`-root (Finding-1 robustness) | **ESCALATE to the operator as a material design decision — do NOT bake in.** The only mechanism that makes peers reachable WITHOUT depending on the ambiguous root-level walk is an additional read-only bind-mount placing a prebuilt `node_modules` at `/work/pi-package/node_modules` (reached at walk iteration 2, unambiguous). That requires modifying `src/gleipnir/sandbox/runtime.py::build_run_argv` to support a per-profile extra mount (new signature + tests) — an enforcement-bearing `src/**` change OUTSIDE this plan's declared scope | Silently editing `runtime.py`; a `-g`+`NODE_PATH` hack (ESM ignores it); a "lockfile" (does not change WHERE modules resolve, only WHICH versions) | The reviewer's suggested fallbacks (direction (b), "lockfile") do NOT actually solve the *resolution-location* problem: (b) still needs the deps to physically live outside `/work` yet be walk-reachable, and a lockfile is a version-pinning artifact, not a resolution mechanism. The genuine robust fallback changes the sandbox runtime's mount layout — a lasting, hard-to-reverse, enforcement-bearing decision (extra mounts widen the sandbox's surface). Per gleipnir-plan's role boundary, a material tradeoff between viable approaches is escalated to the operator via the orchestrator, NOT resolved in the plan. This plan proceeds on `/node_modules`-root as primary; D9 is the named, pre-surfaced escalation if §1a refutes it. |
| D4 | `pi` profile `test` argv target | `pi-package/test/*.test.ts` (the S1 slice's test dir) via explicit file globs resolved at build/authoring time | A `--test` directory-recursion over the whole tree | Scoped to the S1 package's test files, mirroring how `broker` scopes to `tests/test_broker_*.py` — keeps the profile's blast radius to the slice under proof. Exact file list is finalised when S1's test files exist (Assemble note). |
| D5 | Coverage for the `pi` profile | `unavailable = true, justified = "..."` honest degradation (mirrors `node` profile) | Fabricate a coverage story; wire c8/v8 coverage now | TS test coverage for `node:test` is not readily available without adding `@vitest/coverage-v8` or `c8` (new deps, against D3's minimality). Follow the `node` profile's own precedent: honest `unavailable` with justification, not a fabricated number. Coverage wiring is a deferrable later slice. |
| D6 | Who applies the Tier-3 edits | Operator/build-mode applies `profiles.toml` + `gleipnir-code.md` + builds/digest-pins the image; `gleipnir-code` writes only `Containerfile.pi` and `tests/**` | `gleipnir-code` writes the Tier-3 files | **L-C27 / enforcement-path invariant**: `.gleipnir/sandbox/**` and `.gleipnir/agents/**` are `E`-members no roster agent can write. This plan emits the exact diff text; the operator applies it, same as the sandbox-profile-selector precedent. |
| D7 | Base image | `docker.io/library/node:22-slim` at the SAME digest the existing `Containerfile.node` pins (`sha256:6c74791e...f6b3`) | A newer node tag; a different base | Reuse the already-probed, already-pinned node base the `node` profile trusts — no new base-image trust surface. `node:22-slim` ships Node ≥22.6 (strip-types available; the running image is 22.23.1 per the live `profiles.toml` comment). |
| D8 | Transitive-dep reproducibility (Finding 4) | **Accept + document** a bounded transitive-float gap for this slice; the six top-level pins are exact, transitive deps float to the caret range on build day | Add a committed lockfile (`package-lock.json`) to pin the full graph now | The six literal top-level installs are exact (D2). Their transitive deps (`@earendil-works/pi-client`, `pi-protocol`, `pi-telemetry`; and pi-ai's `@anthropic-ai/sdk`, `openai`, `@aws-sdk/*`, etc.) are NOT pinned by the literal `npm install` line and float — the ordinary npm-without-lockfile situation. This is a KNOWN, bounded gap: the image is still digest-pinned once built (so a given built image IS reproducible), only a *rebuild* could drift. A committed lockfile is the stronger fix but adds a new tracked artifact + its own maintenance/blast-radius surface; deferred to a later slice. D2's "not a floating latest" rationale is hereby scoped to the top-level six only, not the full transitive graph — no silent overclaim. |

## Architect

- **Problem (one sentence):** `gleipnir-code` cannot run the S1 pi.dev slice's
  TypeScript tests because the S-2 sandbox has no profile whose image carries
  pi's peer packages, a TypeScript compiler, and a TS-capable test runner —
  this plan adds a `pi` sandbox profile (image + profile entry + agent grant +
  profile-resolution tests) so those tests can run in the bounded container.
- **User:** `gleipnir-code` (runs `bin/gleipnir-sandbox test --profile pi` to
  execute S1's tests); the operator (builds+digest-pins the image and applies
  the two Tier-3 edits).
- **Measurable success criteria:**
  1. `Containerfile.pi` exists at repo root, mirrors the `Containerfile.node`/
     `Containerfile.broker` house style, and installs the D2-pinned peer deps +
     `typescript@5.9.3` into `/node_modules` at the filesystem ROOT (D3), such
     that a real `node ... -e "import('@earendil-works/pi-coding-agent')"` run
     from `/work/pi-package` inside the built container (`--network=none`, ro
     `/work`) does NOT throw `ERR_MODULE_NOT_FOUND` (empirically proven, not
     asserted — Assemble §1a).
  2. A `[profile.pi]` **diff-to-apply** for `.gleipnir/sandbox/profiles.toml`
     exists as exact text, mirroring `[profile.node]`/`[profile.broker]` shape,
     with a digest-pinned `image`, `test`/`lint` argv, honest `coverage`.
  3. A `gleipnir-code.md` **diff-to-apply** exists as exact text: the paired
     exact-match `bash` allows for `test --profile pi` / `lint --profile pi`
     (both `bin/` and `./bin/` forms) and the `.gleipnir/agents/**` note.
  4. Profile-resolution tests for `"pi"` land in `tests/test_sandbox_cli.py`
     (and, if warranted, `tests/test_sandbox_profiles.py`), mirroring the
     existing node/broker cases, and pass under `bin/gleipnir-sandbox test`.
  5. The plan states the build-then-apply-then-run sequencing explicitly.
- **Constraints:**
  - `.gleipnir/sandbox/**` + repo-root `Containerfile*` → Axis-1 `X` / Axis-2(a)
    `E` → full hardened pipeline, no light-path.
  - Real, current npm versions only — no guesses (see Link for verification).
  - Do NOT touch the S1 pi-package's own content (that is
    `pi-dev-replatform-first-slice.md`'s scope).
  - `gleipnir-code` writes ONLY `Containerfile.pi` + `tests/**`; the two Tier-3
    files are operator/build-mode-applied (D6).
  - `--network=none` at run time → EVERYTHING resolvable at test time
    (peer deps, tsc, runner) must be pre-installed into the image at BUILD time.

## Trace

**Artifacts and where they live (source of truth):**

| Artifact | Path | Writer | Status |
|---|---|---|---|
| Pi sandbox image recipe | `Containerfile.pi` (repo root) | `gleipnir-code` | to-be-created |
| `pi` profile entry | `.gleipnir/sandbox/profiles.toml` (append `[profile.pi]`) | **operator/build-mode (D6)** — plan supplies exact diff | to-be-applied |
| Agent bash grant + agents note | `.gleipnir/agents/gleipnir-code.md` | **operator/build-mode (D6)** — plan supplies exact diff | to-be-applied |
| Profile-resolution tests for `pi` | `tests/test_sandbox_cli.py` (+ maybe `tests/test_sandbox_profiles.py`) | `gleipnir-code` | to-be-created (added cases) |
| Built+digest-pinned image | local `localhost/gleipnir-sandbox-pi@sha256:<digest>` | **operator** (`podman build` + `podman inspect`) | to-be-built |

**Integrations map:**
- `bin/gleipnir-sandbox test --profile pi` → `src/gleipnir/sandbox/__main__.py`
  `main()` → `_resolve_dispatch_profile("pi")` → `resolve_profile(profiles,
  "pi")` (existing seam; `--profile` already implemented and tested) →
  dispatches `[profile.pi]`'s `test` argv against the pi image via
  `prepare_sandbox_run`.
- `[profile.pi].image` must satisfy `profiles.py::_validate_image`'s STRICT
  rule: a locally-built image → `name@sha256:<64 lowercase hex>` digest ref
  (NOT the grandfathered `gleipnir-sandbox:latest` literal — that is python-only).
- `Containerfile.pi` `FROM node:22-slim@sha256:6c74791e...f6b3` (same base as
  `Containerfile.node`) → build-time install of the D2-pinned packages +
  `typescript` **into `/node_modules` at the filesystem ROOT** (`npm install
  --prefix / <pkgs>`, or `cd /` then `npm install <pkgs>`; the produced
  `/node_modules` is an ancestor of `/work/pi-package/test/` and lives OUTSIDE
  the `/work` ro bind-mount, so it survives it and ESM bare-specifier
  resolution finds it) → no ENTRYPOINT/CMD (argv supplied per-run by
  `runtime.py::build_run_argv`, house convention). **NOT `-g`/`NODE_PATH`**
  (Finding 1: a `-g` prefix is not an ancestor of `/work/pi-package/`, and
  Node's ESM resolver ignores `NODE_PATH`).
- New `test_..._pi...` cases in `tests/test_sandbox_cli.py` reuse the existing
  `_write_config` + `fake_prepare` monkeypatch pattern (no real container),
  asserting `--profile pi` selects the pi image + argv and fails closed on an
  unknown profile — byte-for-byte mirror of the `_BROKER_TOML`/`_NODE_TOML`
  cases already in that file.

**Edge cases:**
- **Peer-dep resolution at `--network=none` (the Finding-1 failure mode):**
  installing the packages is NOT sufficient — they must be RESOLVABLE from
  `/work/pi-package/test/*.test.ts` at run time. Two traps this plan closes:
  (a) baking under `/work/**` (e.g. `/work/pi-package/node_modules`) is MASKED
  by the ro bind-mount at run time; (b) `-g` install + `NODE_PATH` does NOT work
  for ESM (`NODE_PATH` is ignored by the ESM resolver; a `-g` prefix is not an
  ancestor of the test dir). **Chosen mechanism:** install into `/node_modules`
  (root) — the only `node_modules` location outside `/work`. **This is NOT
  asserted to work:** per D3's caveat, the literal ESM `PACKAGE_RESOLVE` walk
  guard (`while parentURL is not the file system root`) excludes the root
  iteration, so root-level `/node_modules` reachability is spec-ambiguous
  (observed-Node includes it; spec text reads otherwise). AC-2 / Assemble §1a
  RUNS a real `import('@earendil-works/pi-coding-agent')` inside the built
  container (`--network=none`, ro `/work`) to DECIDE this empirically — a grep
  of the RUN line is explicitly insufficient. **If §1a refutes it, STOP and
  escalate D9** (the robust fallback is a `runtime.py` extra-mount, a material
  operator decision) — do NOT substitute a `-g`/`NODE_PATH` hack.
- **`typebox` ESM-only (1.x):** typebox 1.3.7 is ESM-only; the S1 package is
  ESM (TS with ESM imports), so this is consistent — but a CJS test harness
  would break. `node:test` + strip-types runs ESM, so this holds. Noted so a
  future runner swap does not silently reintroduce a CJS path.
- **Non-strippable TS syntax:** if S1's `.test.ts` uses enums/namespaces/param
  properties, `--experimental-strip-types` errors. Fallback:
  `--experimental-transform-types` (documented in the profile comment); the
  runner stays `node:test`. This is a profile-argv detail, not a runner change.
- **Image-rule near-miss:** the pi image field is a digest ref; a bare tag
  (`gleipnir-sandbox-pi:latest`) would be REFUSED by `_validate_image` (the
  grandfathered literal is `gleipnir-sandbox:latest` ONLY). The diff MUST use
  `name@sha256:<64hex>`. Placeholder digest in the diff is flagged for the
  operator to replace with the real `podman inspect` output.
- **Unknown `--profile pi` before the operator applies the TOML edit:** fails
  closed via the existing `resolve_profile` → `ProfileError` → exit 3 path
  (no new validation). A test asserts this pre-apply fail-closed behaviour is
  unchanged (reuses the existing `test_profile_nonexistent_*` pattern, just
  confirms nothing regressed).
- **`test`/`lint` grant is exact-match:** the two new grant lines must be exact
  strings (no trailing wildcard), matching the existing python/broker/node
  grant lines, so no compound command piggybacks on a prefix.

## Link (validated before building)

- **npm versions — RE-VERIFIED against `registry.npmjs.org` this session
  (2026-08-24), correcting the earlier pi-ai misreport (Finding 3):**
  - `@earendil-works/pi-coding-agent/latest` → **0.84.2** (registry root doc;
    updated 2026-08-14). Its dependency table pins `pi-agent-core ^0.84.2`,
    `pi-ai ^0.84.2`, `pi-tui ^0.84.2`, `typebox 1.3.7`, `typescript 5.9.3`
    (devDep), `vitest 4.1.9` (devDep).
  - `@earendil-works/pi-agent-core/latest` → **0.84.2** (depends `pi-ai
    ^0.84.2`, `typebox 1.3.7`).
  - `@earendil-works/pi-ai/latest` → **0.84.3** (registry `/latest` fetched;
    Version field literally `0.84.3`, updated 2026-08-24T11:06Z). **This
    corrects the prior draft's incorrect 0.84.2 citation.** `^0.84.2` (what
    the siblings declare) resolves to 0.84.3, so pinning 0.84.3 is what a real
    `npm install` produces today. pi-ai@0.84.3's own deps include
    `@anthropic-ai/sdk 0.91.1`, `openai 6.40.0`, `@aws-sdk/client-bedrock-runtime
    3.1048.0`, `typebox 1.3.7`, `@earendil-works/pi-telemetry ^0.84.3` — a large
    transitive graph (motivates D8's transitive-float caveat).
  - `@earendil-works/pi-tui/latest` → **0.84.3** (independently versioned;
    updated 2026-08-24T11:04Z — same hour as pi-ai).
  - `typebox/latest` → **1.3.18**, BUT pi pins **1.3.7**; the image installs
    **1.3.7** to match pi's resolved graph (D2). typebox 1.x is **ESM-only**
    (its Versions table).
- **Node ESM resolution facts — the Finding-1 mechanism basis (RE-VERIFIED
  live against `nodejs.org/api/esm.html` this session):** confirmed two facts —
  (1) "**No `NODE_PATH`**": the ESM resolver does not consult `NODE_PATH` for
  bare-specifier `import`, so the earlier `-g`+`NODE_PATH` approach is genuinely
  non-functional (not a network issue); (2) the `PACKAGE_RESOLVE` algorithm
  performs a `node_modules` ancestor-directory walk, phrased *"While parentURL
  is not the file system root, resolve `node_modules/` relative to parentURL;
  set parentURL to the parent folder URL"*. **Honest reading of (2):** the walk
  guard excludes the iteration where `parentURL == /`, so by the literal spec a
  root-level `/node_modules` is NOT resolved unless the implementation includes
  the root level (real-world Node is observed to). This is a spec-text-vs-
  observed-behaviour ambiguity on the ONE fact D3's mechanism depends on —
  hence it is **NOT treated as proven by reasoning.** Peers reachable from
  `/work/pi-package/test/` need a walk-reachable `node_modules` that survives
  the ro mount; `/node_modules` (root) is the only in-scope candidate, and its
  reachability is **decided empirically** by the Assemble §1a RUN-and-import
  proof (gleipnir-plan holds no build capability — this is an explicit gating
  handoff, not an assertion). If §1a refutes it → D9 escalation.
- **`--profile` selector — ALREADY BUILT & TESTED:** `tests/test_sandbox_cli.py`
  contains `test_profile_broker_*`, `test_profile_node_*`,
  `test_profile_nonexistent_fails_closed_never_dispatches`,
  `test_image_build_subparser_has_no_profile_flag` — the dispatch seam this plan
  targets exists; this plan ADDS a profile + its resolution tests, it does not
  build the selector.
- **STRICT image rule — CONFIRMED** in `.gleipnir/sandbox/profiles.toml` header
  + `tests/test_sandbox_profiles.py::TestStrictImageRuleQuartet`: locally-built
  images MUST be `name@sha256:<64 lowercase hex>`; the `gleipnir-sandbox:latest`
  literal is python-self-host-only.
- **House style — CONFIRMED** by reading `Containerfile`, `Containerfile.node`,
  `Containerfile.broker`: pinned `FROM ...@sha256:`, dev tooling pre-installed
  via a single `RUN`, `WORKDIR /work`, NO ENTRYPOINT/CMD, header comment block
  explaining the profile's purpose + `--network=none` rationale.
- **`node:test` + `--experimental-strip-types` runs `.ts` with type imports —
  CONFIRMED** by the live `[profile.node]` entry (runs a `.mjs` importing
  `.gleipnir/plugins/sequence-gate.ts` under `--experimental-strip-types`,
  node 22.23.1).
- **NOT YET EMPIRICALLY VERIFIED BY gleipnir-plan (I hold NO bash/build
  capability) — these are handed to `gleipnir-code`/operator as gating build
  steps, NOT assumed:**
  1. **`/node_modules`-root resolution actually works** under a real `podman
     build` + `podman run --network=none -v <tmp>:/work:ro`. The mechanism is
     reasoned from Node's documented ESM ancestor-walk + `NODE_PATH`-ignored
     facts (above), but — given the root-level walk ambiguity in D3's caveat —
     reasoning is explicitly NOT proof here. Assemble §1a is the explicit
     RUN-and-import smoke test that MUST produce real output (`RESOLVE_OK`, no
     `ERR_MODULE_NOT_FOUND`) before the plan is considered proven. **If §1a
     fails, STOP and escalate D9** — the robust fallback is a per-profile extra
     `node_modules` bind-mount in `runtime.py` (a material, enforcement-bearing
     `src/**` decision for the operator, OUTSIDE this plan's scope). Do NOT
     substitute a `-g`/`NODE_PATH` hack or a lockfile (neither changes WHERE
     modules resolve). Do not paper over a §1a failure.
  2. Whether S1's actual `.test.ts` files use only strippable TS. If not, the
     profile argv adds `--experimental-transform-types` (edge case above); the
     runner stays `node:test`. S1 test files do not exist yet — the exact
     `test` argv file list (D4) is finalised when they do.

## Assemble (intended build order)

1. **`Containerfile.pi`** (`gleipnir-code` writes) — `FROM
   node:22-slim@sha256:6c74791e...f6b3`; header comment block in the
   `Containerfile.node`/`.broker` style (purpose, `--network=none` rationale,
   no source/creds baked in); a single `RUN` that installs the six D2-pinned
   packages (`pi-coding-agent@0.84.2`, `pi-agent-core@0.84.2`, `pi-ai@0.84.3`,
   `pi-tui@0.84.3`, `typebox@1.3.7`, `typescript@5.9.3`) **into `/node_modules`
   at the filesystem ROOT** (e.g. `RUN cd / && npm install --no-package-lock
   <six pins>` — producing `/node_modules`, NOT a `-g` prefix, NOT under
   `/work`); `WORKDIR /work`; no ENTRYPOINT/CMD. Verify it mirrors the siblings.
2. **§1a — MANDATORY resolution smoke test (the Finding-1 proof; produced by
   `gleipnir-code`/operator, NOT gleipnir-plan — I hold no build capability).**
   Before trusting the profile, run for real:
   ```
   podman build -f Containerfile.pi -t gleipnir-sandbox-pi .
   mkdir -p /tmp/piwork/pi-package/test
   podman run --rm --network=none -v /tmp/piwork:/work:ro -w /work/pi-package \
     gleipnir-sandbox-pi \
      node --experimental-strip-types --input-type=module \
        -e "await import('@earendil-works/pi-coding-agent'); await import('typebox'); console.log('RESOLVE_OK')"
   ```
   PASS = prints `RESOLVE_OK`, NO `ERR_MODULE_NOT_FOUND`, with `--network=none`
   and `/work` mounted READ-ONLY (proving resolution is from `/node_modules`,
   not network, not a masked `/work` path). Capture the real stdout/exit code as
   the evidence artifact. **If it fails, STOP and escalate D9** — the
   `/node_modules`-root walk-reachability is refuted; the robust fallback is a
   per-profile extra `node_modules` bind-mount in `src/gleipnir/sandbox/
   runtime.py` (a material, enforcement-bearing decision the OPERATOR converges,
   not gleipnir-code). Do NOT proceed with a broken profile and do NOT hack a
   `-g`/`NODE_PATH`/lockfile substitute (none of those changes resolution
   location). This AC (AC-2) is not satisfiable by a Containerfile grep.
3. **`[profile.pi]` diff-to-apply** (plan artifact, §"Tier-3 write spec" below)
   — exact TOML text mirroring `[profile.node]`: digest-ref `image` (placeholder
   digest, operator replaces), `test`/`lint` argv, honest `coverage`,
   `test_selector_prefix = false`.
4. **`gleipnir-code.md` diff-to-apply** (plan artifact, §"Tier-3 write spec")
   — the four exact new `bash` allow lines + the `.gleipnir/agents/**` note.
5. **Profile-resolution tests** (`gleipnir-code` writes) in
   `tests/test_sandbox_cli.py`: add a `_PI_TOML` inline config (mirroring
   `_BROKER_TOML`) and `test_profile_pi_test_selects_pi_image_and_command` +
   `test_profile_pi_lint_selects_pi_lint_command` + a fail-closed confirmation,
   mirroring the broker cases exactly (monkeypatched `prepare_sandbox_run`, no
   real container). Test-first where feasible: author the assertions to the AC
   list; they pass once the inline config + existing dispatch resolve `"pi"`.
6. **Run** `bin/gleipnir-sandbox test` (python profile) to confirm the new test
   cases pass and nothing regressed. Report pass count + coverage%.
7. **Handback to operator** with: (a) `Containerfile.pi` on disk, (b) the §1a
   smoke-test output as real evidence, (c) the two Tier-3 diffs as exact text,
   (d) the build+digest-pin commands, (e) the sequencing note. Operator then
   executes steps 8–11 (outside `gleipnir-code`).
8. **[OPERATOR]** `podman build -f Containerfile.pi -t gleipnir-sandbox-pi .`
   then `podman inspect gleipnir-sandbox-pi --format '{{.Digest}}'` to get the
   real digest. (May reuse the §1a build.)
9. **[OPERATOR]** apply the `[profile.pi]` diff to
   `.gleipnir/sandbox/profiles.toml` with the REAL digest, and apply the
   `gleipnir-code.md` grant diff.
10. **[OPERATOR or a fresh light-touch `quality-reviewer` check — the Finding-6
    post-apply re-verification, NOT the pre-apply diff attestation]** After the
    Tier-3 edits are applied, re-grep the ACTUALLY-APPLIED files against their
    post-change bytes: (a) `.gleipnir/agents/gleipnir-code.md` contains the
    exact four allow lines with NO trailing wildcard —
    `grep -nE '"\.?/?bin/gleipnir-sandbox (test|lint) --profile pi": allow' .gleipnir/agents/gleipnir-code.md`
    returns exactly 4 lines and `grep -n 'profile pi\*' .gleipnir/agents/gleipnir-code.md`
    returns nothing; (b) `.gleipnir/sandbox/profiles.toml`'s `[profile.pi].image`
    is a real `name@sha256:<64hex>` (no `<OPERATOR-REPLACE>` placeholder left,
    no bare tag). This closes the gap where the pre-apply diff is trusted as if
    it were the applied bytes.
11. **[OPERATOR / then `gleipnir-code`]** with the image built, the TOML applied
    (+ §10 re-verified), and the grant applied, `gleipnir-code` can finally run
    `bin/gleipnir-sandbox test --profile pi` against S1's tests.

## Stress-test (concrete acceptance criteria)

1. **AC-1 (Containerfile shape):** `Containerfile.pi` starts with `FROM
   docker.io/library/node:22-slim@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3`,
   has `WORKDIR /work`, has NO `ENTRYPOINT`/`CMD`, and carries a purpose/`--network=none`
   header comment — a `diff` against `Containerfile.node` shows an **ADDED**
   install block (Containerfile.node is zero-dep by design and has NO `RUN`
   install line at all; the pi image ADDS one), not a differing line.
2. **AC-2 (peer deps genuinely RESOLVABLE, not merely installed) — the
   Finding-2 fix:** this AC is satisfied ONLY by the Assemble §1a real
   RUN-and-import: inside the built `gleipnir-sandbox-pi` image, with
    `--network=none` and `/work` mounted READ-ONLY, `node
    --experimental-strip-types --input-type=module -e "await
    import('@earendil-works/pi-coding-agent'); await import('typebox')"` run from
   `/work/pi-package` prints `RESOLVE_OK` and does NOT throw
   `ERR_MODULE_NOT_FOUND`. A `grep` of the Containerfile's `RUN` line is
   **explicitly NOT sufficient** (it would pass under the broken `-g`/`NODE_PATH`
   mechanism). Evidence = the captured stdout+exit-code of that run.
   - **AC-2b (correct pins present):** the `RUN` install line names exactly
     `@earendil-works/pi-coding-agent@0.84.2`, `@earendil-works/pi-agent-core@0.84.2`,
     `@earendil-works/pi-ai@0.84.3`, `@earendil-works/pi-tui@0.84.3`,
     `typebox@1.3.7`, `typescript@5.9.3` — NO floating `latest`/`^`/`*` on these
     six top-level pins (grep). (Transitive deps float per D8 — a known, accepted
     gap, not a violation of this AC.)
3. **AC-3 (image rule):** the `[profile.pi]` diff's `image` is a
   `name@sha256:<64 lowercase hex>` ref (a `grep -E 'sha256:[0-9a-f]{64}"$'`
   matches) — NOT a bare tag; a placeholder digest is clearly flagged
   `<OPERATOR-REPLACE-64-HEX-DIGEST>` for the operator.
4. **AC-4 (profile entry shape parity):** the `[profile.pi]` entry has exactly
   the keys `image`, `test`, `lint`, `coverage`, `test_selector_prefix` — the
   same key set as `[profile.node]` (a `diff` of the key lines matches node's).
5. **AC-5 (honest coverage):** `[profile.pi].coverage` is `{ unavailable =
   true, justified = "<non-empty>" }` — no fabricated `args`/number.
6. **AC-6 (grant lines exact-match):** the `gleipnir-code.md` diff adds exactly
   four `bash` allow lines — `bin/gleipnir-sandbox test --profile pi`,
   `bin/gleipnir-sandbox lint --profile pi`, and the two `./bin/...` forms —
   each an exact string with NO trailing wildcard, mirroring the existing
   node/broker grant lines byte-for-byte in shape. (This checks the *diff*;
   AC-11 checks the *applied bytes*.)
7. **AC-7 (profile-resolution tests):** the added `test_profile_pi_*` cases in
   `tests/test_sandbox_cli.py` assert `--profile pi` dispatches the pi image +
   the pi `test`/`lint` argv (via monkeypatched `prepare_sandbox_run`), and
   pass under `bin/gleipnir-sandbox test`.
8. **AC-8 (no scope bleed):** NO file under `pi-package/**` is created or
   modified by this plan (a `git status` shows only `Containerfile.pi`,
   `tests/test_sandbox_cli.py`, and — post-operator — the two Tier-3 files
   changed). The S1 package content is untouched.
9. **AC-9 (fail-closed pre-apply):** before the operator applies the TOML edit,
   `bin/gleipnir-sandbox test --profile pi` fails closed (exit 3, no dispatch)
   via the existing `resolve_profile`→`ProfileError` path — asserted by a test
   confirming an unknown-profile name still fails closed (no regression).
10. **AC-10 (sequencing stated):** the Execution Workflow states the
    build→apply-Tier-3→run ordering explicitly, so `gleipnir-code` does not
    attempt `--profile pi` before the image + TOML + grant exist.
11. **AC-11 (post-apply re-verification — Finding-6 fix):** AFTER the operator
    applies the two Tier-3 edits, the ACTUALLY-APPLIED files are re-grepped
    against their post-change bytes (Assemble §10, by the operator or a fresh
    light-touch `quality-reviewer`, NOT the author): (a)
    `grep -nE '"\.?/?bin/gleipnir-sandbox (test|lint) --profile pi": allow'
    .gleipnir/agents/gleipnir-code.md` returns exactly 4 lines AND a search for
    a trailing-wildcard variant (`profile pi\*`) returns nothing; (b)
    `.gleipnir/sandbox/profiles.toml`'s `[profile.pi].image` matches
    `sha256:[0-9a-f]{64}"$` with NO `<OPERATOR-REPLACE...>` placeholder
    remaining. The pre-apply diff attestation (AC-6) does NOT satisfy this;
    the applied-bytes check is a distinct, required step.

## Tier-3 write spec (exact text for the operator to apply — D6)

### (a) `.gleipnir/sandbox/profiles.toml` — APPEND this block

Append after the existing `[profile.broker]` block. Mirrors `[profile.node]`.
The operator replaces `<OPERATOR-REPLACE-64-HEX-DIGEST>` with the real digest
from `podman inspect gleipnir-sandbox-pi --format '{{.Digest}}'` (which returns
`sha256:<64hex>`; use the hex portion).

```toml
# Pi/TypeScript profile. Runs the S1 pi.dev primitive-proof slice's tests
# (pi-package/test/*.test.ts) in the bounded gleipnir-sandbox-pi image, which
# is the ONLY sandbox image carrying pi's peer packages + a TypeScript compiler.
# The S1 tests import @earendil-works/pi-coding-agent (+ siblings) and typebox;
# those + typescript are pre-installed at BUILD time so test runs need NO
# network (--network=none holds). Uses node:test + --experimental-strip-types
# (node 22.6+; the image ships node 22.x), the lowest-new-dependency TS runner;
# if S1 test files use non-strippable TS, add --experimental-transform-types to
# the test argv (the runner stays node:test). Scoped to pi-package/test/ so the
# pi suite runs against the pi image without pulling the whole tree.
#
# Image is digest-pinned per the strict image rule (profiles.py::_validate_image).
# Built from ./Containerfile.pi (node:22-slim digest-pinned + npm-installed pins);
# local digest resolved via `podman inspect ... --format '{{.Digest}}'`.
[profile.pi]
image = "localhost/gleipnir-sandbox-pi@sha256:<OPERATOR-REPLACE-64-HEX-DIGEST>"
test = ["node", "--experimental-strip-types", "--test", "pi-package/test/enforcement.test.ts", "pi-package/test/delegate.test.ts"]
lint = ["npx", "tsc", "--noEmit", "-p", "pi-package/tsconfig.json"]
coverage = { unavailable = true, justified = "node:test built-in TS coverage deferred; S1 primitive-proof slice, no coverage tool wired (mirrors node profile)" }
test_selector_prefix = false
```

> Note on the `test` file list: the two paths mirror S1's Trace
> (`pi-package/test/enforcement.test.ts`, `pi-package/test/delegate.test.ts`).
> If S1's final test filenames differ, the operator/`gleipnir-code` adjusts the
> list to the actual S1 test files at apply time (D4) — the argv shape is fixed,
> the file list tracks S1.
> Note on `lint`: `npx tsc --noEmit` is the strict type-check arbiter (the S1
> plan mandates strict `tsconfig.json`); `tsc` is installed in the image so
> `npx` resolves it offline.

### (b) `.gleipnir/agents/gleipnir-code.md` — ADD grant lines + note

In the `bash:` block, after the existing `... --profile node` lines and before
the `"git*": deny` line, ADD these four exact lines (mirroring the existing
python/broker/node grant lines exactly — exact-match, no trailing wildcard):

```yaml
    "bin/gleipnir-sandbox test --profile pi": allow
    "bin/gleipnir-sandbox lint --profile pi": allow
    "./bin/gleipnir-sandbox test --profile pi": allow
    "./bin/gleipnir-sandbox lint --profile pi": allow
```

No change to the `edit`/`read`/`task`/`webfetch`/`tools` blocks. The
`.gleipnir/agents/**` self-reference is why this edit is operator/build-mode
applied (L-C27): the agent cannot widen its own grant. No prose-body change is
required; optionally the operator may add a one-line note in the "Build/test/
lint run in the S-2 sandbox" paragraph that a `pi` profile now exists for the
pi.dev TS slice.

## Execution Workflow

- **Delegated to:** `gleipnir-code` (test stage + code stage; Sonnet) for the
  agent-writable artifacts ONLY — `Containerfile.pi` and the
  `tests/test_sandbox_cli.py` additions. The two Tier-3 files are NOT written by
  `gleipnir-code`; it emits nothing to `.gleipnir/sandbox/**` or
  `.gleipnir/agents/**` (denied by capability, L-C27).
- **Test-first:** author the `test_profile_pi_*` cases to the AC-7/AC-9 list
  using the existing `_write_config` + `fake_prepare` monkeypatch pattern
  (byte-for-byte mirror of the `_BROKER_TOML` cases). They pass once the inline
  `_PI_TOML` config resolves through the existing `--profile` dispatch — no
  production code change is needed (the selector already exists), so these are
  config-shape regression tests, not new-feature tests.
- **Verify:** `bin/gleipnir-sandbox test` (python profile, in-container). Report
  pass count + line+branch coverage%.
- **CRITICAL — build-then-prove-then-apply-then-reverify-then-run sequencing
  (the causal dependency this plan exists to satisfy; matches Assemble
  §1–§11):**
  1. `gleipnir-code` writes `Containerfile.pi` (`/node_modules`-root install,
     D3) + the test additions, verifies the python suite is green.
  2. **§1a MANDATORY resolution smoke test** — build the image and run the real
     `--network=none`, ro-`/work`, `node ... import(...)` proof (Assemble §2);
     capture `RESOLVE_OK` output. **If it throws `ERR_MODULE_NOT_FOUND`, STOP
     and escalate** — the mechanism is wrong, do not proceed with a broken
     profile. This is the evidence AC-2 requires; a Containerfile grep is NOT
     sufficient.
  3. **[OPERATOR]** builds/digest-pins the image (`podman build ...` +
     `podman inspect ... --format '{{.Digest}}'`).
  4. **[OPERATOR]** applies the two Tier-3 diffs (§ above), substituting the
     real digest into `[profile.pi].image`.
  5. **§10 post-apply re-verification (Finding-6)** — the operator or a fresh
     light-touch `quality-reviewer` re-greps the APPLIED files (AC-11): exactly
     4 wildcard-free allow lines in `gleipnir-code.md`, a real digest in
     `profiles.toml` with no placeholder left. NOT the pre-apply diff.
  6. **ONLY THEN** can `gleipnir-code` run `bin/gleipnir-sandbox test --profile
     pi` to execute S1's tests — the grant, the image, and the profile entry
     must all exist first. Attempting `--profile pi` before this fails closed
     (exit 3), which is correct, not a bug.
- **Do not expand scope:** no S1 pi-package content (roleTable/enforcement/
  delegate/etc.) — that is `pi-dev-replatform-first-slice.md`. If building the
  image surfaces a material toolchain decision (e.g. `node:test` genuinely
  cannot run S1's TS test files and a real runner dep like vitest is required,
  OR the `/node_modules`-root resolution mechanism fails §1a and direction (b)
  / a lockfile approach is needed), STOP and route it back to the operator via
  the orchestrator — do not silently add a runner dependency or a new
  resolution hack.
- **Handback:** the evidence artifact is (a) `Containerfile.pi` + green python
  suite, (b) **the §1a resolution smoke-test real output** (the load-bearing
  proof), (c) the two exact Tier-3 diffs, (d) the build/digest-pin commands.

## Design Principles (Gate 1 — case (ii): executable-but-non-OOP)

`P` = { `Containerfile.pi`, `.gleipnir/sandbox/profiles.toml` (append),
`.gleipnir/agents/gleipnir-code.md` (grant lines), `tests/test_sandbox_cli.py`
(added cases) }. `P ∩ X ≠ ∅` (the `Containerfile*` and `tests/**` are `X`
members) → executable artifact. The Containerfile/TOML/agent-config have **no
class/function/module structure** → **case (ii)**: DRY + Design Intent apply;
SOLID and the class/module SRP are **attested N/A**.

> Sub-note: the added Python test *functions* in `tests/test_sandbox_cli.py`
> technically have function structure (case (i) territory), but they are pure
> mirrors of existing `test_profile_broker_*`/`test_profile_node_*` functions —
> one assertion-bearing test function each, single responsibility by
> construction (assert `--profile pi` dispatches the right image+argv). No new
> abstraction, no shared helper beyond the already-existing `_write_config`/
> `captured_exec` fixtures. So the case-(i) analysis for them collapses to:
> SRP = "each test asserts one dispatch fact"; DRY = "reuse existing fixtures,
> do not reimplement config-writing." Recorded here rather than split into a
> separate case (i) block because the test additions carry no design novelty.

**SOLID analysis:** `N/A — no object/function structure`. `Containerfile.pi` is
a linear image recipe; the `[profile.pi]` TOML block and the agent grant lines
are declarative data; there are no classes/interfaces/subclasses for a
Liskov / Interface-Segregation / Dependency-Inversion / SRP analysis.

**Single Responsibility check (class/module):** `N/A — no object/function
structure` (same reason).

**DRY analysis:**
- The `pi` profile **reuses the existing `--profile` dispatch seam** — it adds
  a profile entry, not a parallel code path. No dispatch logic is duplicated.
- The Containerfile **reuses the `node:22-slim` base at the same pinned digest**
  as `Containerfile.node` — the base-image trust decision is made once, not
  re-derived.
- The profile entry **reuses the `node`/`broker` schema and the honest-coverage
  degradation pattern** verbatim in shape — no new schema, no fabricated
  coverage.
- The test additions **reuse the existing `_write_config` + `fake_prepare` +
  `captured_exec` fixtures** and the `_BROKER_TOML` inline-config pattern — no
  new test harness, no editing the shared tracked fixture (keeps its blast
  radius unchanged, per the sandbox-profile-selector precedent).
- The version pins are stated ONCE in D2 and referenced by the Containerfile
  and ACs — the six package names + versions are not re-typed with drift.
- The `/node_modules`-root resolution mechanism (D3) is stated once and the
  install-line, edge cases, AC-2, and §1a all reference it — the mechanism is
  not re-derived per-section.

**Design Intent (specific, falsifiable):** *The `pi` profile MUST make the S1
slice's TypeScript tests runnable inside the SAME bounded S-2 sandbox
(`--network=none`, `/work` mounted READ-ONLY) as every other profile, with pi's
peer packages RESOLVABLE (not merely installed) from `/work/pi-package`'s test
files — resolved from a `/node_modules` at the filesystem ROOT that survives
the ro `/work` mount, NEVER from the network and NEVER from a `-g`/`NODE_PATH`
location the ESM resolver cannot reach — such that a real
`import('@earendil-works/pi-coding-agent')` from `/work/pi-package` returns
without `ERR_MODULE_NOT_FOUND` and `bin/gleipnir-sandbox test --profile pi`
executes S1's `.test.ts` files with zero network egress and zero host toolchain
use.* A reviewer can falsify this by finding: (i) peers installed to a location
NOT resolvable at run time — under `/work` (masked by the ro mount), or a
`-g`/`NODE_PATH` prefix (not an ESM-resolver ancestor) — such that §1a's
RUN-and-import throws `ERR_MODULE_NOT_FOUND` (the exact Finding-1 failure);
(ii) any `[profile.pi]` field that would resolve a package at test time (e.g.
`npm install` in the `test` argv); (iii) a `test`/`lint` argv that shells out to
the host instead of the container; or (iv) an `image` that is a bare tag rather
than a digest ref. The intent is NOT "build a good profile" (vacuous) and NOT
merely "packages installed" (the Finding-1 false success) — it is the concrete,
empirically-checkable "peer deps are RESOLVABLE from `/node_modules`-root at
`--network=none` with ro `/work`, proven by §1a, never assumed."
