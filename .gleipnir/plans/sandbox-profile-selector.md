# Plan: `--profile <name>` selector for `bin/gleipnir-sandbox test|lint`

> **Stage:** `plan` (gleipnir-plan). **Plans FROM** the operator-converged
> proposal `.gleipnir/plans/sandbox-profile-selector-control-proposal.md`
> (`## Convergence`: **Option A** — add `--profile <name>` to `test`/`lint`,
> validate against the fixed profile set, widen `gleipnir-code`'s bash allowlist
> to enumerate ALL THREE profile names for symmetry). The A/B/C tradeoff and the
> blast-radius-widening acceptance were **decided by the operator via the
> orchestrator's `question` tool** — this plan does **not** re-decide them; it
> plans the bounded work.
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0). This file is the sole artifact of this stage. Every step it describes
> is executed later by the role bound to it (the orchestrator sequences; nothing
> here runs now). This plan **names and drafts** one Tier-3 operator step (the
> `gleipnir-code.md` bash-allowlist widening) and produces ready-to-apply text
> for it — it does **not** apply it. This mirrors how
> `broker-pm-coverage-gap.md` (Decision 4) names a Tier-3 `profiles.toml`
> amendment the code agent cannot perform.
>
> **Routing:** hardened path, **full 8-stage pipeline** (Axis-1 disqualifier:
> `P` touches `src/gleipnir/sandbox/**` ∈ `X`; AND the paired Tier-3 grant
> change touches `.gleipnir/agents/gleipnir-code.md` ∈ enforcement-path set `E`,
> Axis-2(a)+(b)). This is the highest-scrutiny category `stage-role-map.md`
> defines: two separate review passes + a negative-check attestation on the
> grant change.

---

## Decisions (index)

Summary of every decision this plan fixes, in order encountered; full reasoning
is in the sections below. Rows 1–2 are operator-converged (cited, not
re-decided); rows 3–7 are bounded planning-stage decisions; row 8 is the
material Tier-3 sequencing constraint surfaced (not decided) by the planner;
row 9 records the explicit re-verification the operator requested.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | **[OPERATOR-CONVERGED]** Option A/B/C | **A** — `--profile <name>` flag + allowlist enumerating all three names (`python`, `broker`, `node`) | B (omit redundant `python`); C (keep manual `default_profile` round-trip) | Operator chose A via `question` for symmetry/legibility over B's minimal-grant; C rejected (untenable round-trip). See proposal `## Convergence` (2026-08-22). |
| 2 | **[OPERATOR-CONVERGED]** Blast-radius widening (agent may self-select `broker`/`node` image) | **Accepted YES** | Reject (would force C) | Operator accepted the one material judgment: the bounded agent may self-select the broker/node image WITHIN the fixed Tier-3 profile set (still gated by strict image rule + argv-list rule + no-wildcard enumeration). Proposal `## Convergence`. |
| 3 | Where validation of an unknown profile name happens | **Reuse the EXISTING `resolve_profile(profiles, name)` KeyError→`ProfileError`→exit 3 path** — thread `args.profile` through, add NO new validation layer | A new bespoke name-allowlist check in `__main__.py` | `resolve_profile` (profiles.py:293) already fail-closes on an unknown name against `profiles.by_name` loaded from the fixed Tier-3 file. Adding a second check duplicates logic (DRY violation) and risks divergence. The fail-closed-on-unknown requirement is satisfied by the seam as-is. |
| 4 | How `--profile` is added to the `test` subparser without REMAINDER swallowing it | **Add `--profile` as an optional BEFORE the `pytest_args` REMAINDER positional; the enumerated allowlist entries carry NO trailing selectors** (`test --profile broker`, not `test --profile broker -- x`) | Adding it after REMAINDER / accepting selector passthrough on `--profile` | `p_test.add_argument("pytest_args", nargs=REMAINDER)` captures everything after the first non-option token. `--profile X` must be parsed as an option before REMAINDER begins. A test locks `test --profile broker` parsing; selector passthrough on a named profile is a SEPARATE future surface (proposal notes this), not folded here. |
| 5 | Threading point in `__main__.py` | **`_resolve_dispatch_profile(repo, config_root, name=...)` gains an optional `name` param, passed to `resolve_profile(profiles, name)`; `_cmd_test`/`_cmd_lint` pass `args.profile`** | Resolving the profile name anywhere other than the existing dispatch-profile helper | `_resolve_dispatch_profile` (`__main__.py:101`) is the single place both `_cmd_test` and `_cmd_lint` resolve the profile — threading `name` there keeps ONE resolution path (SRP), no duplication across the two verbs. |
| 6 | Default behaviour (no `--profile`) | **`default=None` → `resolve_profile(profiles, None)` → `profiles.default_profile`** — byte-for-byte today's behaviour | Making `--profile` required; changing the default | Backward compatibility (converged test requirement 5): bare `test`/`lint` must behave EXACTLY as today. `default=None` and the existing `name=None`→default branch guarantee this with no behavioural change. |
| 7 | Test fixture for the `broker` profile | **Author a broker-bearing fixture** (add `[profile.broker]` to `tests/fixtures/sandbox_profiles.toml` OR an inline `_write_config` TOML per test) using a strict-image-rule-valid image | Relying on the live Tier-3 `.gleipnir/sandbox/profiles.toml` | The tracked fixture (`tests/fixtures/sandbox_profiles.toml`) currently declares only `python`+`node` — no `broker`. `--profile broker` resolution tests need a broker profile in the INJECTED test config (never the live Tier-3 file; the agent cannot read config from `.gleipnir/**` on the dispatch path). Code agent decides fixture shape; both are valid. |
| 8 | **[MATERIAL — Tier-3, surfaced to operator, NOT applied here]** `gleipnir-code.md` bash-allowlist widening | **Operator applies** the 12 new enumerated allow entries (6 per `bin/`/`./bin/` variant × already includes both prefixes) drafted verbatim in §Operator hand-off | Agent applies it (impossible — every roster grant denies `.gleipnir/**`); a `--profile *` wildcard (reopens AETOS enumerable-bypass) | Without this grant, the code half (i) is INERT for the agent: an arg-bearing `bin/gleipnir-sandbox test --profile broker` matches no current allow entry and is denied. This is a Tier-3 POLICY edit; the planner drafts ready-to-apply text and names it operator-only. Enumeration, NO wildcard. |
| 9 | **[RE-VERIFY, operator-requested]** Does this violate `language-agnostic-sandbox.md`'s config-path PROHIBITED clause? | **NO — confirmed different axis** | (assuming without checking) | The PROHIBITED clause (T3, lines 263–271) bans `--config-path`/`--config-root` and env override of the config **LOCATION** (which file is the arbiter). `--profile` selects AMONG profiles inside the one fixed file; it adds no location override. Different axis, not violated. See Link §L5. |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`.gleipnir/goals/manifest.md`):** "Plan format"
  (`plan-format.md`) and "Methodology (ATLAS/GOTCHA ahead of planning)" apply.
  This plan follows the Decisions-index / Architect / Trace / Link / Assemble /
  Stress-test / Execution-Workflow / **Design Principles** structure. No
  pipeline-sequencing goal authored or implied (G-5 rule respected).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or git are produced here.
- **Layer placement (GOTCHA layers):** the code half is a **Tools/dispatch**
  change to the sandbox CLI (which profile the deterministic dispatch selects) —
  it does NOT widen the agent-facing VERB set (`test`/`lint` unchanged), only
  which already-declared profile is selectable. The paired allowlist widening is
  a **capability grant** (Tools-layer permission), Tier-3 POLICY, operator-only.
  The config LOCATION-fixity property is a **G-1 / Context-Args** invariant and
  is explicitly preserved (Decision 9).
- **Gaps / factual findings named (verified against actual source this
  session):**
  1. **The `resolve_profile(profiles, name)` seam already exists and already
     fail-closes** (profiles.py:293–304): `name=None`→default;
     unknown→`ProfileError`. The code work is *threading*, not *inventing*
     validation (Decision 3).
  2. **`_resolve_dispatch_profile` hard-passes `resolve_profile(profiles)` with
     no name today** (`__main__.py:101–108`) — the exact threading point.
  3. **Argparse REMAINDER hazard** on the `test` subparser (`__main__.py:232`) —
     `--profile` must be an option parsed before `pytest_args` REMAINDER (Decision 4).
  4. **The `broker` profile is NOT in the test fixture** (`tests/fixtures/
     sandbox_profiles.toml` has only `python`+`node`) — a broker-bearing test
     config must be authored (Decision 7).
  5. **The grant syntax in `gleipnir-code.md` is exact-match string keys** with
     `"*": deny` (lines 32–44) — so enumerated arg-bearing entries are the
     correct expression; the converged text (12 lines) matches this shape.
- **New material tradeoff found?** **None beyond the two already
  operator-converged (Decisions 1–2).** One Tier-3 sequencing gate is surfaced
  (Decision 8) — an operator action, not a design choice the planner resolves.
  Everything else is bounded, mechanical.

---

## 1. Architect

**Problem (one sentence).** `bin/gleipnir-sandbox test|lint` resolves its
toolchain profile solely from the global `default_profile` (`_resolve_dispatch_profile`
→ `resolve_profile(profiles)` with `name=None`), so running a NON-default
profile (`broker`/`node`) forces the operator into a manual Tier-3
`default_profile` hand-edit round-trip; this slice adds a `--profile <name>` CLI
flag that threads the operator-supplied name into the **already-present**
`resolve_profile(profiles, name)` seam — validated fail-closed against ONLY the
profiles declared in the fixed Tier-3 `.gleipnir/sandbox/profiles.toml`, with
the config LOCATION unchanged and unoverridable.

**User.** The `gleipnir-code` agent (can now select `broker`/`node` for a run
without a Tier-3 round-trip, once the operator widens its allowlist — Decision 8);
the operator (no longer hand-flips `default_profile`); downstream plans such as
`d5-sidecar-write.md` that were blocked on broker-profile verification.

**Measurable success criteria.**
1. `bin/gleipnir-sandbox test --profile broker` resolves and dispatches the
   `broker` profile's configured test command + image (verified via the
   faked-exec harness: right image + right argv).
2. `bin/gleipnir-sandbox test --profile node` likewise selects the node image +
   node command; `--profile python` likewise selects the python image + pytest
   command. `lint --profile <name>` selects the corresponding lint command.
3. Bare `bin/gleipnir-sandbox test` / `lint` (no `--profile`) behaves EXACTLY as
   today — resolves `default_profile`, same coverage flags, same scratch routing,
   same fail-closed behaviour (backward-compatibility regression, NOT a breaking
   change).
4. `--profile nonexistent` (any unknown name) **fails closed**: `ProfileError` →
   exit 3, a clear error naming the defined profiles, and it does **NOT** fall
   back to silently running the default profile. `captured_exec == []` (nothing
   ran).
5. The config LOCATION stays fixed and unoverridable: NO `--config-path`/
   `--config-root` flag, NO env override is added; `--profile` selects only
   AMONG already-declared profiles inside the one fixed file (the
   `language-agnostic-sandbox.md` PROHIBITED clause is untouched — Decision 9).
6. The agent-facing VERB set does not widen (still exactly `test`/`lint`/
   `image-build`); `--profile` is an option on the existing verbs, not a new verb
   and not a raw toolchain.
7. **[Operator Tier-3, drafted here]** `gleipnir-code.md`'s bash allowlist is
   widened by exactly the 12 enumerated arg-bearing entries (no wildcard) so the
   agent can invoke the flag — applied by the operator AFTER code/test/quality
   pass (§Operator hand-off).

**Constraints.**
- **Isolation CORE (`runtime.py`) UNCHANGED.** `prepare_sandbox_run(cmd, *,
  image=…, extra_env=…)` already parameterizes `cmd` and `image`; a selected
  profile's command + image flow through with ZERO core change.
- **Config-reader (`profiles.py`) UNCHANGED — or additive only.**
  `resolve_profile(profiles, name)` already accepts an optional `name` and
  already fail-closes on an unknown one. No edit to `profiles.py` is expected
  (Decision 3); if any is proposed it must be justified as strictly additive.
- **Stdlib-only** (`.gleipnir/decisions/runtime-and-deps.md`) — no new dependency.
- **Config LOCATION fixed** (Decision 9 / Criterion 5). NO location override of
  any kind on the agent-facing dispatch path.
- **No wildcard in the Tier-3 grant.** Enumerated exact-match entries only
  (reopening `--profile *` would be the AETOS enumerable-bypass hole).

---

## 2. Trace

### T1. The threading seam (code half — `src/gleipnir/sandbox/__main__.py`)

Source of truth confirmed this session:

- `_resolve_dispatch_profile(repo, config_root)` (`__main__.py:101–108`) loads
  the profiles and returns `resolve_profile(profiles)` — **hard `name=None`
  today.** This is the single resolution helper both `_cmd_test` and `_cmd_lint`
  call. **Change:** add an optional `name: str | None = None` parameter, passed
  to `resolve_profile(profiles, name)`. One threading point, both verbs (SRP;
  Decision 5).
- `_cmd_test(args, *, config_root)` (`:111`) and `_cmd_lint(args, *,
  config_root)` (`:160`) each call `_resolve_dispatch_profile(repo,
  config_root)`. **Change:** pass `name=args.profile`.
- `resolve_profile(profiles, name)` (`profiles.py:293–304`) — **UNCHANGED.**
  `name=None`→`profiles.default_profile`; a `name` not in `profiles.by_name`
  raises `ProfileError` (via KeyError) naming `sorted(profiles.by_name)`. This
  IS the fail-closed-on-unknown path (Criterion 4). No new validation is added
  (Decision 3 — DRY).
- The `except ProfileError` arms already present in `_cmd_test` (`:116–118`) and
  `_cmd_lint` (`:165–167`) map `ProfileError` → `print(...); return 3`. An
  unknown `--profile` therefore fail-closes through the EXISTING path, exit 3,
  `captured_exec == []`.

### T2. The argparse surface (`build_parser`, `__main__.py:225–250`)

- `p_test` has `p_test.add_argument("pytest_args", nargs=argparse.REMAINDER)`
  (`:232`). **REMAINDER captures every token after the first non-option
  argument.** `--profile` MUST be added as an optional (`--profile`,
  `default=None`) so argparse consumes `--profile broker` as an option BEFORE the
  REMAINDER positional begins. Add `p_test.add_argument("--profile",
  default=None, help=...)` (Decision 4).
- `p_lint` (`:235–238`) has NO REMAINDER positional and no `--image` flag (that
  removal is already locked by `test_lint_subparser_has_no_image_flag`). Add
  `p_lint.add_argument("--profile", default=None, help=...)`.
- `image-build` (`:240–248`) — **UNCHANGED**, operator-only, off the agent
  allowlist. `--profile` is NOT added there.
- `main()` (`:253–259`) routes `test`/`lint` through `args.func(args,
  config_root=config_root)`; `args.profile` rides on the namespace. The existing
  `--` stripping (`:255–256`) is unaffected because `--profile X` is parsed as an
  option, not into `pytest_args`.

**Interaction with `--` selector passthrough (edge case, python profile only):**
`bin/gleipnir-sandbox test --profile python -- -k bridge` must parse `--profile
python` as the option and `-k bridge` as REMAINDER selectors. The enumerated
allowlist entries deliberately carry NO trailing selectors (`test --profile
broker`), so an agent invocation with BOTH `--profile` and `--` selectors would
not match any allow entry and is denied — selector passthrough on a named
profile is a separate, un-granted surface (proposal §(ii) note). A test asserts
`--profile python -- -k x` PARSES correctly at the CLI level (the code supports
it; the *grant* just doesn't allow the agent to issue it).

### T3. Fail-closed on unknown name (Criterion 4 — the safety hinge)

`--profile nonexistent` → `resolve_profile(profiles, "nonexistent")` →
`profiles.by_name["nonexistent"]` raises `KeyError` → re-raised as `ProfileError`
naming the defined set → caught by the verb's `except ProfileError` → exit 3,
message printed, **nothing dispatched** (`prepare_sandbox_run` never called,
`captured_exec == []`). This is STRICT enumerated matching against what is
actually configured — an arbitrary string that happens not to match is refused,
never treated as free text and never silently defaulted. **No new code enforces
this — the existing seam does; the tests prove it holds when driven through the
new flag.**

### T4. Config LOCATION fixity preserved (Decision 9 / Criterion 5)

The flag adds ONLY `--profile` (a profile *name*). It adds NO `--config-path`,
NO `--config-root`, and reads NO env var for the config root. `config_root`
remains the in-process test-harness seam it already is (`main(argv,
config_root=...)`); in production it is still `_default_config_root(repo)` =
`<repo>/.gleipnir/sandbox`, computed internally (`__main__.py:82–86`). The
`language-agnostic-sandbox.md` PROHIBITED clause (which bans overriding *which
file* is the arbiter) is on a DIFFERENT axis and is untouched — this flag selects
among profiles *inside* that one fixed file. Re-verified explicitly (Link §L5).

### T5. Agent allowlist widening (Tier-3 half — operator applies)

**Path:** `.gleipnir/agents/gleipnir-code.md`, frontmatter `permission.bash`
block (lines 31–44). Current shape (verified this session) is exact-match string
keys after `"*": deny`. The widening adds 12 enumerated entries (6 invocations ×
the `bin/` and `./bin/` prefix variants the file already distinguishes). Exact
ready-to-apply text is in §Operator hand-off. **No wildcard.** This is
enforcement-bearing (Axis-2(a): path ∈ `E`; Axis-2(b): a `bash` capability line
with `allow`), so it goes through the hardened track's two-pass review +
negative-check attestation when applied — the planner only drafts it.

### Edge cases (all fail-closed → exit 3 where a run is involved, never host-run)

1. **Unknown `--profile <name>`** → `ProfileError` → exit 3, names defined
   profiles, NEVER falls back to default. `captured_exec == []`. (T3.)
2. **No `--profile` (bare `test`/`lint`)** → `name=None` → `default_profile`,
   byte-for-byte today's behaviour (Criterion 3).
3. **`--profile python` explicitly** → resolves the python profile (identical to
   the default today, since `default_profile = "python"`) — proves the explicit
   path works alongside omission (converged test requirement 3).
4. **`--profile broker` / `--profile node`** → selects the broker/node image +
   command; the broker profile carries no `test_selector_prefix`, so its
   existing refuse-extra-selectors behaviour is unchanged.
5. **`--profile` with a valid name that is missing the requested verb's command**
   (e.g. a profile with no `lint`) → the existing `command_for` `ProfileError`
   path → exit 3 (unchanged behaviour, now reachable per-profile).
6. **`--profile broker -- <selector>`** → parses at the CLI, but the broker
   profile refuses extra selectors (`test_selector_prefix=false`) → exit 3; AND
   the agent grant does not allow this invocation shape anyway (T2).
7. **Argparse: `--profile` after REMAINDER tokens** — guarded by adding
   `--profile` as an option; a test locks that `test --profile broker` parses
   with `args.profile == "broker"` and empty `pytest_args`.

---

## 3. Link — validated BEFORE building

Every fact below was re-read from the actual files this session:

- **L1 (seam exists & fail-closes).** `resolve_profile(profiles, name: str |
  None = None)` (profiles.py:293) returns `default_profile` on `None` and raises
  `ProfileError` on an unknown name (KeyError arm, :300–304). The
  fail-closed-on-unknown requirement is met by the seam as-is — threading only
  (Decision 3).
- **L2 (single threading point).** `_resolve_dispatch_profile` (`__main__.py:101`)
  is the one helper both `_cmd_test`/`_cmd_lint` use; both already have an
  `except ProfileError → return 3` arm. Threading `name` there routes an unknown
  name to exit 3 with zero new error-handling code.
- **L3 (faked-exec harness).** `tests/test_sandbox_cli.py` `captured_exec`
  fixture + `monkeypatch`-ed `prepare_sandbox_run` prove "the RIGHT image + argv
  were assembled" without a container (e.g.
  `test_node_profile_test_selects_node_image_and_command:247`,
  `test_python_profile_test_injects_coverage_and_cache_flags:127`). The new
  `--profile` tests reuse exactly this pattern.
- **L4 (fixture gap).** `tests/fixtures/sandbox_profiles.toml` declares only
  `python`+`node`. A `broker` profile must be authored into a test config (add
  to the fixture, or an inline `_write_config` TOML like
  `test_broker_profile_lint_also_gets_pycache_redirect:213` already does) with a
  strict-image-rule-valid image (`gleipnir-sandbox:latest` literal or a
  `name@sha256:<64 hex>` digest). Code agent's call (Decision 7).
- **L5 (PROHIBITED clause re-verified — Decision 9).** `language-agnostic-
  sandbox.md` T3 (lines 263–271) prohibits a `--config-path`/`--config-root` CLI
  arg and any env-var override of the config **root/location**. `--profile`
  supplies a profile *name*, not a config location; it adds no location
  override. **Different axis — NOT violated.** The proposal's own §Gap ("Was the
  missing selector a deliberate safety decision?", lines 44–55) independently
  reaches the same conclusion. Confirmed explicitly, as the operator requested.
- **L6 (grant syntax).** `gleipnir-code.md` bash block (lines 31–44) is
  exact-match string keys with `"*": deny` and both `bin/` and `./bin/` prefix
  variants already present for `test`/`lint`. The 12 new entries mirror that
  exact shape (Decision 8 / §Operator hand-off).
- **L7 (code-agent capability).** `gleipnir-code` may `edit "*"` except
  `.gleipnir/**`/`.git/**`/`preflight/**`; `src/gleipnir/sandbox/**` and
  `tests/**` are in-grant. Its only test capability is `bin/gleipnir-sandbox
  test|lint` (exact-match). **Consequence for verification (hard ordering
  gate):** UNTIL the operator applies the Tier-3 grant (Decision 8), the agent
  CANNOT itself run `bin/gleipnir-sandbox test --profile broker` (denied by the
  current allowlist). It CAN author + prove the new tests via the injected
  `config_root` in-process (the tests call `cli.main(["test", "--profile",
  "broker"], config_root=...)` directly — no shell invocation, no allowlist
  dependency). The *acceptance run through the real shell flag* is only
  exercisable after the grant lands (post-quality, operator step). This mirrors
  the L4-gate pattern in `broker-pm-coverage-gap.md`.

---

## 4. Assemble — test-first build order

Each code step: write/adjust tests FIRST, then make them pass, run
`bin/gleipnir-sandbox test` (default python profile — the agent's granted
invocation), report pass count + line+branch coverage.

**Step 0 — [spec-review] two-pass hardened review of THIS plan** (spec-conform
+ blast-radius) before any code. (Sequenced by the orchestrator.)

**Step 1 — [code, TEST-FIRST] Author the `--profile` tests in
`tests/test_sandbox_cli.py`** (and any broker fixture per Decision 7), covering
the converged five requirements:
  - **(1) `--profile broker`** — `cli.main(["test", "--profile", "broker"],
    config_root=<broker-bearing config>)` assembles the broker image + broker
    test command via `captured_exec`/faked `prepare_sandbox_run`. Same for
    `lint --profile broker` → broker lint command.
  - **(2) `--profile node`** — selects the node image + `node --test …` command;
    prints `coverage: unavailable (justified: …)`, appends no `--cov`.
  - **(3) `--profile python` AND omission** — both resolve the python profile
    (explicit name AND bare `test` with no flag) with identical coverage flags,
    proving both paths work.
  - **(4) `--profile nonexistent`** — exit 3, `captured_exec == []`, error names
    the defined profiles, NO fallback to default (assert `prepare_sandbox_run`
    never called).
  - **(5) backward-compat regression** — bare `test`/`lint` with no `--profile`
    is byte-for-byte today's argv/image/coverage (reuse/extend the existing
    `test_python_profile_test_injects_coverage_and_cache_flags` assertions).
  - **Argparse guard** — `build_parser().parse_args(["test", "--profile",
    "broker"])` yields `args.profile == "broker"` and empty `pytest_args`; and
    `test --profile python -- -k x` parses `profile == "python"` with `-k x` in
    REMAINDER (Decision 4 / edge case 7).

**Step 2 — [code] Implement the thread.** Add `--profile` (`default=None`) to the
`test` and `lint` subparsers; add `name: str | None = None` to
`_resolve_dispatch_profile` and pass it to `resolve_profile(profiles, name)`;
`_cmd_test`/`_cmd_lint` pass `name=args.profile`. **Do NOT touch `profiles.py`**
(Decision 3) and **do NOT add any config-location flag/env** (Criterion 5). Make
Step-1 tests green.

**Step 3 — [code] Run `bin/gleipnir-sandbox test`** (default python profile —
the agent's currently-granted invocation), confirm the full suite is green and
coverage holds (≥85% target). Report pass count + line% + branch%. NOTE the
hard gate: the agent cannot run `--profile broker` through the shell until the
Tier-3 grant lands (L7); the `--profile` paths are proven in-process via
injected `config_root`.

**Step 4 — [code] Report** files changed
(`src/gleipnir/sandbox/__main__.py`, `tests/test_sandbox_cli.py`, and any
`tests/fixtures/sandbox_profiles.toml` broker addition), verification run, and
confirm `profiles.py`/`runtime.py` untouched (or additive-only with justification).

**Step 5 — [quality] Two-pass hardened blast-radius review** against §Stress-test
(no verb-set widening, config-location fixity intact, fail-closed proven, no
`profiles.py` behavioural change), PLUS the SOLID/DRY dimension (§Design
Principles) and the honour check (applied impl. honours the stated Design
Intent).

**Step 6 — [git-ops] Commit** the code + test changes.

**Step 7 — [OPERATOR, Tier-3 — AFTER Steps 1–6 pass] Apply the grant widening**
to `.gleipnir/agents/gleipnir-code.md` using the verbatim text in §Operator
hand-off, then (in caged mode) re-run `bin/gleipnir-preflight` since the file is
under an enforcement path. This is enforcement-bearing → the operator-applied
edit itself goes through the hardened two-pass review + negative-check
attestation (the planner supplies the drafted attestation skeleton below).

**Assemble step order (summary):**
`0 (spec-review, 2 passes) → 1 (code: author --profile tests, 5 reqs) →
2 (code: thread --profile, no profiles.py change) →
3 (code: sandbox test default profile, coverage) → 4 (code: report) →
5 (quality: 2-pass + SOLID/DRY + honour check) → 6 (git-ops commit) →
7 (OPERATOR Tier-3: apply grant + preflight)`

---

## 5. Stress-test — acceptance checks

Concrete, checkable criteria the result is validated against.

- **A1 (broker dispatch).** `cli.main(["test", "--profile", "broker"],
  config_root=<broker config>)` assembles the broker image + broker test argv
  (faked-exec); `lint --profile broker` assembles the broker lint argv. Measured
  via `captured_exec`/`seen`, not asserted narratively.
- **A2 (node dispatch).** `--profile node` selects the node image + `node --test
  …`; emits `coverage: unavailable (justified: …)`; appends no `--cov`.
- **A3 (python explicit + omission equivalence).** `--profile python` and bare
  `test` (no flag) both assemble the identical python image + pytest + coverage
  argv — proving both the explicit-name and default-by-omission paths.
- **A4 (fail-closed on unknown — the safety hinge).** `--profile nonexistent`
  (and any other unmatched string) → exit 3, `captured_exec == []`,
  `prepare_sandbox_run` NEVER called, error message names the defined profiles,
  and NO silent fallback to the default profile. This is strict enumerated
  matching against the loaded profile set, not free-text tolerance.
- **A5 (backward compatibility — not a breaking change).** Bare `test`/`lint`
  with no `--profile` produce byte-for-byte the same argv/image/coverage/scratch
  routing as before this change; the existing `test_sandbox_cli.py` tests that
  do not pass `--profile` still pass unmodified (or are extended, never weakened).
- **A6 (config LOCATION fixity intact — Decision 9).** No `--config-path`/
  `--config-root` flag exists on `test`/`lint`; no config-root env var is read;
  `parse_args(["test", "--config-root", "x"])` raises `SystemExit` (unrecognized),
  mirroring the existing `--image`-removal tests. The `language-agnostic-
  sandbox.md` PROHIBITED clause is not violated.
- **A7 (verb surface does NOT widen).** The parser still exposes exactly
  `test`/`lint`/`image-build`; `--profile` is an option on `test`/`lint`, not a
  new subcommand and not a raw toolchain verb. `image-build` gains no `--profile`.
- **A8 (`profiles.py` unchanged / no new validation layer — DRY).** The
  config-reader has no behavioural diff; the fail-closed-on-unknown path is the
  existing `resolve_profile` KeyError arm, not a duplicate check in `__main__.py`.
- **A9 (isolation core unchanged).** `runtime.py` diff empty; its tests
  unmodified and green.
- **A10 (stdlib-only).** No new import in `__main__.py`; conformance grep passes.
- **A11 (Tier-3 grant drafted, NOT applied).** The plan contains verbatim
  ready-to-apply allowlist text (12 enumerated entries, no wildcard) and names it
  operator-only; `.gleipnir/agents/gleipnir-code.md` is NOT edited by any
  pipeline agent. When the operator applies it, the negative-check attestation
  (skeleton below) asserts no `--profile *` wildcard is present.

---

## 6. Execution Workflow

**For the orchestrator sequencing this plan.** ATLAS/GOTCHA already ran (this
plan). **Full 8-stage hardened pipeline** (this is `src/**` + a paired `E`-path
grant change — NOT prose/config-track eligible):

`brainstorm (done — converged proposal) → plan (this file) → spec-review
(2-pass hardened) → test → code → quality (2-pass + SOLID/DRY + honour check) →
git → gate`.

### Stage → role routing (per `stage-role-map.md`, confirmed)

| Stage | Bound role | This plan's work |
|---|---|---|
| spec-review | **quality-reviewer** | Two passes: spec-conformance (incl. intent-quality sub-check of the Design Intent) + blast-radius/false-success. Verdicts recorded separately. |
| test | **gleipnir-code** | Author the `--profile` tests (Assemble Step 1) BEFORE implementation. |
| code | **gleipnir-code** | Thread `--profile` through the existing seam (Step 2); make tests green (Step 3). |
| quality | **quality-reviewer** | Two-pass blast-radius review + SOLID/DRY dimension + the honour check (applied impl. honours Design Intent). |
| git | **git-ops** | Commit the code + test changes (the SOLE git holder). |
| gate | **orchestrator** | Read attestation / emit pipeline state. |

- **`test` and `code` may be a single `gleipnir-code` delegation** if the
  orchestrator prefers (test-first within one bounded delegation) — the tests
  are authored first regardless.
- **Tier-3 grant (Decision 8) is OUT of the pipeline's agent scope** — it is an
  operator step AFTER quality/git pass (Assemble Step 7). Every roster grant
  denies `.gleipnir/**`, so no pipeline agent can apply it. The operator applies
  it, and (being enforcement-bearing) it goes through the hardened two-pass
  review + negative-check attestation at that point.

### Implementer protocol (`gleipnir-code`)

- **Test-first per Assemble Step 1.** Do not weaken a test to make it green.
- **Touch ONLY** `src/gleipnir/sandbox/__main__.py`,
  `tests/test_sandbox_cli.py`, and (if chosen) `tests/fixtures/
  sandbox_profiles.toml`. **Do NOT touch** `profiles.py` (Decision 3 — the seam
  already exists), `runtime.py` (constraint), or anything under `.gleipnir/**`
  (denied by capability — the grant is an operator step).
- **Do NOT add** any `--config-path`/`--config-root` flag or config-root env var
  (Criterion 5 / Decision 9). `--profile` supplies a name only.
- Verify via `bin/gleipnir-sandbox test` (default python profile — your granted
  invocation); report pass count + line+branch coverage; justify anything below
  85%. Note that `--profile broker`/`node` through the real shell is not
  agent-runnable until the operator's Tier-3 grant lands (prove those paths
  in-process via injected `config_root`).
- Cannot commit/push; report back for the git stage.

---

## 7. Design Principles (design-time cognition gate — Gate 1)

**Case (i): OOP/functional code plan.** `P` touches
`src/gleipnir/sandbox/__main__.py` (∈ `X`) and that file has function/module
structure → full SOLID + DRY + SRP + Design Intent apply.

### SOLID
- **Single Responsibility.** `_resolve_dispatch_profile` keeps its ONE reason to
  change: "resolve which profile this dispatch uses." Threading `name` through it
  (rather than adding profile-name logic into `_cmd_test` AND `_cmd_lint`
  separately) keeps that single responsibility in one place; the two `_cmd_*`
  functions retain their one responsibility (assemble + dispatch a verb).
- **Open/Closed.** The design EXTENDS behaviour (a new optional flag + one
  new parameter with a `None` default) without modifying `resolve_profile`,
  `profiles.py`, or `runtime.py`. The default-`None` branch means existing
  callers/behaviour are closed to modification while the new selection path is
  open via the parameter.
- **Liskov.** No subclasses introduced; the `Profile`/`Profiles` dataclasses and
  `ProfileError` hierarchy are unchanged, so no substitution contract is touched.
- **Interface Segregation.** `--profile` is added narrowly to exactly the two
  verbs that dispatch a profile (`test`/`lint`); `image-build` (which does not
  dispatch a profile) does NOT gain it — the interface stays focused per verb.
- **Dependency Inversion.** `__main__.py` continues to depend on the
  `resolve_profile(profiles, name)` abstraction, not on `profiles.by_name`
  internals; the unknown-name failure is delegated to that abstraction, not
  re-implemented at the CLI layer.

### DRY
- **No duplicated validation.** The fail-closed-on-unknown check is NOT
  re-implemented in `__main__.py`; it reuses the existing `resolve_profile`
  KeyError→`ProfileError` path (Decision 3). Adding a second name check would
  duplicate logic across two modules and risk divergence.
- **Single threading point.** `name` is threaded through the one shared
  `_resolve_dispatch_profile` helper, not copied into both `_cmd_test` and
  `_cmd_lint` resolution bodies.
- **Reuse the faked-exec harness.** Tests reuse the existing `captured_exec` /
  monkeypatched `prepare_sandbox_run` pattern rather than a new harness.
- **Grant enumeration** mirrors the existing exact-match `bin/`+`./bin/` prefix
  shape already in `gleipnir-code.md` (no new matching mechanism invented).

### Single Responsibility (named, per new/changed unit)
- `_resolve_dispatch_profile(repo, config_root, name=None)` — SOLE
  responsibility: turn (config location, optional name) into the resolved
  `Profile`, fail-closed. (Gains a parameter; keeps its one reason to change.)
- `--profile` argparse option — SOLE responsibility: surface an
  operator/agent-supplied profile *name* on the `test`/`lint` verbs.
- `_cmd_test` / `_cmd_lint` — unchanged responsibility (assemble + dispatch a
  verb); they now forward `args.profile` but gain no new reason to change.

### Design Intent (specific, falsifiable — the load-bearing genuineness proxy)
**The `--profile` flag MUST NOT introduce any second path to a profile that
bypasses `resolve_profile`'s validation against the fixed Tier-3 profile set, and
MUST NOT introduce any override of the config LOCATION.** Concretely, an
implementation VIOLATES this intent if ANY of the following is true, and a
reviewer can point to it:
1. `__main__.py` gains its own profile-name allowlist / membership check instead
   of routing an unknown name through `resolve_profile` (that would be a second,
   divergent validation path — violates the intent even if it happens to
   fail-closed).
2. An unknown `--profile` value ever results in a dispatched run (any fallback to
   the default profile on an unmatched name).
3. Any `--config-path`, `--config-root`, or config-root environment-variable read
   is added to the agent-facing dispatch path (that would move the change onto
   the LOCATION axis the `language-agnostic-sandbox.md` PROHIBITED clause bans).
4. `profiles.py` or `runtime.py` gains a behavioural (non-additive) change.
5. The Tier-3 grant is expressed with any wildcard (`--profile *`) rather than
   enumerated exact-match entries.

This intent is falsifiable (each clause names a concrete implementation choice
that would violate it) and is the artifact the quality-stage honour check
verifies the applied implementation respects.

---

## Operator hand-off (Tier-3 / out-of-agent-reach) — DRAFTED, NOT APPLIED

**This plan produces the ready-to-apply text below; it does NOT apply it.** Every
roster grant denies `.gleipnir/**`, so no pipeline agent can make this edit. The
operator applies it **AFTER** the code/test/quality/git stages pass (Assemble
Step 7), then re-runs `bin/gleipnir-preflight` if caged.

### The grant-change text (verbatim — Option A, all three profile names, NO wildcard)

Replace the current `bash` block in `.gleipnir/agents/gleipnir-code.md`
(lines 31–44) so that, immediately after the four existing exact-match entries,
the twelve new enumerated arg-bearing entries are inserted (the existing denies
below them are unchanged):

```yaml
  bash:
    "*": deny
    "bin/gleipnir-sandbox test": allow
    "bin/gleipnir-sandbox lint": allow
    "./bin/gleipnir-sandbox test": allow
    "./bin/gleipnir-sandbox lint": allow
    # --- NEW: bounded per-profile selection (sandbox-profile-selector plan, Option A) ---
    "bin/gleipnir-sandbox test --profile python": allow
    "bin/gleipnir-sandbox test --profile broker": allow
    "bin/gleipnir-sandbox test --profile node": allow
    "bin/gleipnir-sandbox lint --profile python": allow
    "bin/gleipnir-sandbox lint --profile broker": allow
    "bin/gleipnir-sandbox lint --profile node": allow
    "./bin/gleipnir-sandbox test --profile python": allow
    "./bin/gleipnir-sandbox test --profile broker": allow
    "./bin/gleipnir-sandbox test --profile node": allow
    "./bin/gleipnir-sandbox lint --profile python": allow
    "./bin/gleipnir-sandbox lint --profile broker": allow
    "./bin/gleipnir-sandbox lint --profile node": allow
    # --- existing denies unchanged ---
    "node --experimental-strip-types --test tests/test_sequence_gate.mjs tests/test_git_guard.mjs tests/test_advance_hook.mjs": allow
    "git*": deny
    "gh*": deny
    "glab*": deny
    "sh*": deny
    "bash*": deny
    "env*": deny
    "curl*": deny
```

**Critical property — explicit enumeration, NOT a wildcard.** Exactly one entry
per (verb × prefix-variant × declared profile name). There is deliberately NO
`--profile *` pattern (that would reopen the AETOS enumerable-bypass hole:
`bin/gleipnir-sandbox test --profile python; git push` would prefix-match).
Adding a FOURTH profile later requires a further operator allowlist amendment —
the correct Tier-3 gate, by design.

### Negative-check attestation skeleton (for the operator/`quality-reviewer` when this grant is applied)

Per the hardened track, when the grant edit is applied it needs a negative-check
attestation with `attested_by ≠ author`. Skeleton the reviewer fills:

| grant | intended (narrowest) scope | over_broad_form_checked | evidence `[D]` | negative result | attested_by |
|---|---|---|---|---|---|
| the 12 enumerated `--profile` allow entries in `gleipnir-code.md` bash block | exactly `{python,broker,node}` × `{test,lint}` × `{bin/,./bin/}` — no more | a trailing `--profile *` (or any `*`-bearing) wildcard on a `gleipnir-sandbox` allow key | `grep -n 'gleipnir-sandbox.*--profile' .gleipnir/agents/gleipnir-code.md` on the POST-APPLY file | `--profile *` (wildcard) is NOT present; every matching line ends in a literal `python`/`broker`/`node` | `<reviewer, not the applier>` |

(Evidence must be captured against the applied/post-change state of
`.gleipnir/agents/gleipnir-code.md`, must grep the same file the grant applies
to, and must test the same over-broad form named — per the correspondence /
post-change-state rules in `stage-role-map.md`.)

### Persist the decision (operator)

The operator-converged Option-A decision (esp. the accepted blast-radius
widening — agent may self-select broker/node image) belongs in a durable Tier-3
decision record — natural home: append to
`.gleipnir/decisions/language-agnostic-sandbox.md`, or its own record — since
this plan is Tier-0 disposable.

---

## No material decisions escalated

The two material tradeoffs (Option A/B/C; blast-radius acceptance) were ALREADY
operator-converged (proposal `## Convergence`, Decisions 1–2) — this plan does
not re-open them. Every other choice here is bounded/mechanical (threading point,
argparse ordering, fixture shape, DRY reuse of the existing validation seam) or
is the named Tier-3 operator step (Decision 8), which is operator-authority by
tier, not an unresolved design question. Nothing new requires operator
convergence.
