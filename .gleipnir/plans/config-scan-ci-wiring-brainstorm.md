# Design Brief: Wire `config-scan` into CI (push/PR-time gate)

> **Status: CONVERGED — READY FOR `gleipnir-plan`.** This brief was produced by
> the `gleipnir-brainstorm` subagent (Clarify → Explore → Propose → Decision
> Analysis). The two material decisions and two smaller confirmations surfaced
> below were **converged by the operator** (via the orchestrator's `question`
> flow, this session) and are recorded verbatim in **Selected Approach**. The
> advisory recommendations in the Decision Analysis are the *inputs* to those
> decisions; the **Selected Approach** section is now authoritative. The plan
> stage plans from the converged choices, not from the recommendations.

## Problem Statement

`config-scan` (the config-scoping preflight, `bin/gleipnir-preflight
config-scan`) catches a class of enforcement-config defects — fail-open MCP
scoping, single-holder violations, malformed `permission:`/`tools:` blocks,
mis-scoped globs, unparseable frontmatter/JSONC — before they reach a live
opencode session. It is **already wired on two paths**: (a) the `git-guard.ts`
opencode plugin (before every `gleipnir-git` broker git write) and (b) the
`hooks/pre-commit` VCS hook (ALWAYS-ON on every local commit, fail-closed). The
**last deferred piece** is a **CI gate**: a push/PR-time check that runs
independently of local hook state, so a mis-scoped roster cannot land in the
remote even if a contributor's local hook is absent, disabled, or bypassed with
`git commit --no-verify`.

The deliverable is net-new CI wiring: there is **no `.github/` directory and no
existing CI workflow** in this repo today. Default scope is **only wiring
config-scan into CI** — not building a general test/lint CI pipeline (see
Constraint on scope discipline below).

## Constraints

- **Governing routing constraint (flag, do not resolve): FULL 8-stage hardened
  pipeline.** Any plan touching `.github/**` is in the Axis-1 disqualifier set
  `X` (`.github/**`), so the prose/config-only light track is **unavailable**.
  The downstream plan MUST run the full 8-stage pipeline (brainstorm → plan →
  spec-review → test → code → quality → git → gate) regardless of how small the
  YAML looks. See "Axis-1 / Axis-2 classification" below for the confirmed
  finding.
- **Exit-code contract is single-sourced and MUST be mirrored a third time
  consistently** (or a divergence explicitly justified). The contract
  (`src/gleipnir/preflight/config_scan.py::config_scan_main`, exit 0/1/2):
    - `0` = CLOSED → proceed (config well-scoped)
    - `1` = REFUSE → block (a FAIL finding or unparseable config)
    - `2` = PROCEED_UNCLOSED → operator `--override-ack` (not-closed, but
      operator acknowledged)
    - anything else / can't-run → **fail-closed block**
  It is already mirrored identically in `.gleipnir/plugins/git-guard.ts`
  (`decideFromExit`, lines ~128–148: 0→allow, 2→warn+allow, 1→abort, default→
  abort; `PreflightUnavailable` for can't-run) and in `hooks/pre-commit`
  (lines ~59–80: same case mapping). CI is the third mirror.
- **The `config-scan` subcommand needs NO `--agent-uid`/`--agent-gid`.**
  Verified in `src/gleipnir/preflight/__main__.py::main()`: a leading
  `config-scan` token is dispatched to `config_scan.config_scan_main` BEFORE
  the boundary parser (which is the parser that requires uid/gid). So the CI
  invocation is exactly `./bin/gleipnir-preflight config-scan` — no uid/gid, no
  `--config-root` needed (it defaults to `<repo>/.gleipnir`).
- **`bin/gleipnir-preflight` execs `"$repo/.venv/bin/python"`** (verified,
  line 20–21). It **requires a `.venv` to exist at the repo root.** CI must
  create one (`python -m venv .venv`). Because the enforcement core (incl.
  `config_scan.py`) is **stdlib-only** (`decisions/runtime-and-deps.md`), the
  venv needs **no dependency install** for config-scan itself — a bare venv on
  Python `>=3.11` is sufficient. (`pytest`/`pytest-cov` are dev-only extras,
  needed only if the job ALSO runs the test suite — out of default scope.)
- **Runtime/deps:** enforcement core is stdlib-only, Python `>=3.11`
  (`pyproject.toml` `requires-python = ">=3.11"`). CI should pin a concrete
  minor (e.g. `3.11` or `3.12` — the sandbox base is `python:3.12-slim`).
- **Platform:** origin is `git@github.com:Djarid/gleipnir.git` → **GitHub** →
  the CI mechanism is **GitHub Actions** (`.github/workflows/*.yml`).
- **Scope discipline (anti scope-creep):** the ask is "wire config-scan into
  CI." Explore surfaced NO compelling reason to bundle the full pytest suite —
  config-scan is a pure, dependency-free, milliseconds check over ~9 markdown
  files + one JSONC file. Running the whole suite in CI is a *separate,
  larger* piece of work (needs the dev extras, arguably the sandbox, coverage
  gate wiring per spec C-2). Bundling it would silently convert a
  "config-scan CI wiring" ask into "stand up a general CI pipeline." Kept out
  of default scope; surfaced as an explicit optional in Decision 4.
- **Agent-unwritable target.** `.github/**` is outside every roster agent's
  write grant (no role holds platform/CI credentials; this brainstorm subagent
  can write only `.gleipnir/plans/**`). The workflow file is applied by the
  operator (or a bounded build role for the in-repo file); marking the check
  *required* is a GitHub branch-protection UI action, operator-only.

## Prior art (read and reconciled — this is NOT a fresh problem)

- **`.gleipnir/plans/config-scan-wiring-control-proposal.md`** (a `tier3-coach`
  proposal) already analysed this exact CI wiring with a four-tradeoff Decision
  Analysis, and included a **complete verbatim GitHub Actions workflow**
  (`.github/workflows/config-scan.yml`). Its Decision 1 recommended **Option C
  (both hook + CI)**.
- **Important context shift:** that proposal was written *before* the pre-commit
  hook was implemented. The hook has since shipped **ALWAYS-ON** (see
  `hooks/pre-commit` lines 33–81 and `config-scan-precommit-hook.md` decisions
  D-A…D-I, operator-converged). So the "local half" of Option C is DONE, and
  the current task is precisely the **remaining CI half (Option B)** — the
  already-recommended direction. **This does not make it operator-converged:**
  the operator converged the *hook* decisions (D-A…D-I), not the *CI* ones. The
  CI-specific tradeoffs (push+PR vs PR-only; job shape; exit-2 handling in a
  non-interactive context; required-vs-advisory; first-ever-CI appetite) remain
  open and are re-surfaced below, refreshed for the current (hook-already-live)
  reality.
- One tradeoff from the old proposal is now **effectively settled by the hook
  precedent** and is carried forward, not re-litigated: **block on FAIL, WARN
  advisory unless `--strict`**, matching `decide_config`'s severity model and
  the shipped hook. It is noted in Decision 3 but is not the material open
  question — the material CI-specific question is exit-2 handling.

## What was explored

- **`config_scan.py` + `__main__.py`**: confirmed the exit-code contract, the
  subcommand dispatch (no uid/gid needed for `config-scan`), and the
  stdlib-only purity of the check.
- **`git-guard.ts` (185 lines)** and **`hooks/pre-commit` (101 lines)**: read
  both exit-code mappings in full. They agree exactly (0/1/2/else); CI must be
  the third consistent mirror. Notably: the plugin treats exit 2 as
  **warn+allow** and the hook treats exit 2 as **warn+proceed** — both because
  a *live operator* deliberately invoked `--override-ack`. That assumption does
  not obviously hold in CI (Decision 2).
- **`bin/gleipnir-preflight`, `bin/gleipnir-sandbox`, `Makefile`,
  `pyproject.toml`**: the shim execs `.venv/bin/python`; `make test/lint` run in
  the S-2 sandbox (container), NOT on the host. config-scan is NOT a sandboxed
  target — it is a fast host/CI-runnable pure check. The Makefile has no
  `config-scan` target today.
- **`tests/test_precommit_hook.sh`**: host shell conformance test for the hook's
  mapping; run on host, not via the sandbox. Establishes the precedent that a
  drift-check guards the duplicated mapping across runtimes rather than a shared
  module.
- **`runtime-and-deps.md`**: stdlib-only enforcement core; dev extras
  (`pytest>=8,<9`, `pytest-cov>=5,<6`) are the only declared deps and are NOT
  needed for config-scan.
- **`.envrc`**: sets `OPENCODE_CONFIG_DIR=.gleipnir` — not needed by config-scan
  (its default `--config-root` is `<repo>/.gleipnir` computed from the module
  path), but worth noting CI runs without direnv.
- **No `.github/` directory exists** (confirmed: glob/grep found no workflow
  files; task statement corroborates). This is first-ever CI.

## Approaches Considered

### Approach A: Single dedicated `config-scan` GitHub Actions workflow, triggered on `push` + `pull_request`

**Summary:** One workflow file `.github/workflows/config-scan.yml` with a single
job that checks out, sets up Python, creates a bare `.venv`, and runs
`./bin/gleipnir-preflight config-scan`. Triggered on both `push` (to `main`) and
`pull_request`. This is essentially the verbatim artifact from the prior
`config-scan-wiring-control-proposal.md`, refreshed.

**Tradeoffs:**
- Pro: Catches a mis-scoped roster on **both** direct pushes to `main` AND on
  PRs — the widest net; nothing lands in the protected branch unchecked.
- Pro: Mirrors the repo's existing two-layer safety pattern (fast local floor +
  authoritative server-side gate), consistent with how secret-scan is layered.
- Pro: Dedicated, single-purpose workflow — clear name in the Actions UI, easy
  to mark as a required check, no coupling to a future test pipeline.
- Con: Redundant runs when a push and its PR overlap (a push to a PR branch
  fires both triggers) — minor wasted CI minutes.
- Con: `push` on non-`main` branches (if triggered broadly) could be noisy;
  scoping `push` to `[main]` mitigates this.

**Estimated Scope:** 1 new file (`.github/workflows/config-scan.yml`), ~35 lines
YAML. Complexity: low.

**Risk:** low — a nonzero exit fails the job by construction; the only real risk
is the `.venv` step or Python setup being mis-specified (mitigated by the
verified stdlib-only, no-install requirement).

### Approach B: Single dedicated `config-scan` workflow, `pull_request` only

**Summary:** Same single-purpose workflow, but triggered **only** on
`pull_request` (no `push` trigger). Relies on a branch-protection rule requiring
PRs into `main` so all changes flow through a PR where the check runs.

**Tradeoffs:**
- Pro: No redundant double-runs; each change is checked exactly once, at the PR.
- Pro: Cleanest fit with a PR-based workflow and a "required check on PR" merge
  gate.
- Pro: Slightly fewer CI minutes.
- Con: A **direct push to `main`** (if branch protection allows it, or via
  admin) **bypasses the check entirely** — the gate has a hole exactly where the
  framework most wants coverage (the protected branch). The framework's own
  posture is fail-closed; a trigger that misses direct pushes is a fail-open
  seam unless branch protection *also* forbids direct pushes.
- Con: Couples the gate's effectiveness to a separate branch-protection setting
  the operator must also configure (two things to get right, not one).

**Estimated Scope:** 1 new file, ~30 lines YAML. Complexity: low.

**Risk:** medium — the effectiveness depends on branch-protection forbidding
direct pushes to `main`; if that is not set, the gate silently misses the
highest-value path.

### Approach C: Fold config-scan into a broader net-new "CI" workflow (config-scan + full test suite)

**Summary:** Stand up a general `ci.yml` with multiple jobs — config-scan AND
the full pytest suite (and possibly lint/coverage per spec C-2) — as the repo's
first CI pipeline.

**Tradeoffs:**
- Pro: Delivers general CI value (tests run on every PR) in the same stroke.
- Pro: One workflow file to maintain instead of several later.
- Con: **Scope creep** — the ask is "wire config-scan into CI," not "build CI."
  The test suite needs the dev extras, and the spec (C-2, coverage gate)
  envisions tests running in the S-2 sandbox with `--cov-branch` and a coverage
  target — a materially larger, separate design decision with its own
  tradeoffs (sandbox-in-CI vs host pytest, coverage threshold enforcement).
- Con: Couples a simple, done-today safety gate to a larger piece of work,
  delaying the config-scan gate behind decisions it does not need.
- Con: Higher blast radius / more to review in the hardened pipeline.

**Estimated Scope:** 1 new file, ~60–90 lines YAML, plus decisions on
sandbox-vs-host test execution and coverage gating. Complexity: medium–high.

**Risk:** medium — larger surface, more failure modes, and it re-opens the
test-in-CI design questions the default scope deliberately avoids.

## Decision Analysis

Two material tradeoffs are surfaced for operator convergence. (Trigger vs job
shape are combined into Decision 1 as the "which CI design" multi-option
choice; exit-2 semantics is the distinct Decision 2 the task statement
explicitly flagged as needing Clarify/Explore, not an assumption.)

### Decision 1 — Which CI design: A (push+PR, dedicated) vs B (PR-only, dedicated) vs C (folded into broad CI)?

**Framework used:** Weighted Decision Matrix (multi-option comparison), with a
Reversibility Filter pre-check.

**Reversibility Filter:** All three are **Two-Way Doors** — a workflow YAML is
trivially reversible (delete/edit the file), no data migration, no external
lock-in. Fast-track is permissible; but because this is a *safety* gate
(a mis-scoped roster is the exact failure the framework exists to prevent), the
matrix is still run to make the reasoning explicit.

**Analysis results:**

| Criterion | Weight | A (push+PR) | B (PR-only) | C (folded CI) |
|---|---|---|---|---|
| Catches defect before it lands on `main` | 9 | 9 → 81 | 6 → 54 | 9 → 81 |
| No fail-open seam (covers direct push to `main`) | 8 | 9 → 72 | 4 → 32 | 9 → 72 |
| Scope matches the ask (no creep) | 8 | 9 → 72 | 9 → 72 | 3 → 24 |
| Low setup cost / first-ever-CI appetite | 6 | 8 → 48 | 8 → 48 | 4 → 24 |
| Independent of other settings (self-contained gate) | 6 | 8 → 48 | 4 → 24 | 7 → 42 |
| Minimal wasted CI minutes | 3 | 6 → 18 | 9 → 27 | 5 → 15 |
| **Total** | | **339** | **257** | **258** |

**Recommended (advisory, NOT a decision): Approach A** — a single dedicated
`config-scan` workflow triggered on `push` (to `main`) + `pull_request`. It
scores highest: it covers the protected branch with no dependence on a separate
branch-protection setting, matches the ask without scope creep, and is the
lowest-risk first-ever-CI footprint. It is also the direction the prior
`config-scan-wiring-control-proposal.md` already recommended (Option B of that
proposal = CI, written on push+PR), now that its local-hook half has shipped.

**Caveats:** A's only real cost is occasional redundant double-runs
(push+PR overlap) — negligible for a milliseconds check. If the operator's
workflow forbids direct pushes to `main` via branch protection anyway, B's
fail-open seam closes and B becomes essentially equivalent to A at slightly
lower cost — so the operator's actual branch-protection posture is the swing
factor between A and B.

### Decision 2 — Exit-2 (`PROCEED_UNCLOSED`) handling in CI: warn-and-proceed (mirror plugin/hook) vs hard-fail?

**Framework used:** Pros-Cons-Fixes (binary, safety-flavoured), with a
Second-Order Thinking cross-check on the "mirror the contract" default.

This is the CI-specific question the task statement explicitly flagged. Exit 2
means `PROCEED_UNCLOSED` — config is NOT closed, but an operator passed
`--override-ack`. In the plugin and the hook, exit 2 is **warn-and-proceed**
because a *live, interactive operator* deliberately typed `--override-ack` to
accept the risk. **In CI there is no interactive operator in the loop of that
specific run** — the workflow as designed runs a bare `./bin/gleipnir-preflight
config-scan` with **no `--override-ack` flag**, so a genuine exit 2 can only
arise if someone edited the workflow to pass `--override-ack`, or (defensively)
if the code path produced it unexpectedly.

**Option 2a — Warn-and-proceed (mirror the plugin/hook contract exactly):**

| Pros | Cons | Fix |
|---|---|---|
| Third mirror is byte-for-byte consistent with `git-guard.ts` + `hooks/pre-commit`; the drift-check story stays simple (all three agree) | In CI there is no interactive operator who "deliberately invoked --override-ack" for *this* run; treating an unclosed config as a pass on the authoritative gate weakens exactly the gate meant to be strongest | Since the CI invocation never passes `--override-ack`, a "warn+proceed" branch is effectively dead code in practice — so mirroring is cheap and safe *as long as the workflow never adds `--override-ack`* |

**Option 2b — Hard-fail on exit 2 in CI (diverge deliberately):**

| Pros | Cons | Fix |
|---|---|---|
| CI, as the authoritative agent-unreachable gate, refuses to let an *unclosed* config land regardless of an override flag — an operator override is a *local/launch-time* concept, not a *merge-gate* concept; matches the framework's "CI is authoritative" posture | Diverges from the single-sourced contract mirrored in two other places; the drift-check must now encode a *documented exception* for CI rather than "all three identical" | Document the divergence explicitly in the workflow comment AND in the decision record, and teach the drift-check that CI's exit-2 handling is an intentional, recorded exception (not drift) |

**Second-Order Thinking cross-check (near vs far term):**
- *Near term:* Either option behaves identically in practice, because the
  workflow never passes `--override-ack`, so exit 2 essentially cannot occur on
  the authoritative run. The choice is about what CI does *if* someone later
  wires an override into it.
- *Far term:* If a future contributor adds `--override-ack` to the CI step to
  "get a red build green," Option 2a lets an unclosed config merge (the gate
  self-defeats); Option 2b structurally refuses, forcing the unclosed config to
  be actually fixed or the override to be an explicit, reviewed workflow edit
  that STILL fails. The far-term seam favours 2b for an *authoritative* gate.

**Recommended (advisory, NOT a decision): Option 2b — hard-fail on exit 2 in
CI, as a deliberate, documented divergence from the plugin/hook contract.**
Rationale: `--override-ack` is a live-operator, launch/commit-time escape valve;
CI is the *authoritative, non-interactive, agent-unreachable* gate, and an
override has no interactive operator behind it in a CI run. Failing closed on
"not closed" is the whole point of the authoritative gate. The cost (a
documented exception in the drift-check) is small and one-time. **If the
operator prefers maximal contract uniformity over CI-authoritativeness, 2a is
defensible precisely because the CI step never passes `--override-ack`, making
the warn-branch unreachable in practice** — this is a genuine either/or for the
operator, which is why it is surfaced rather than assumed.

**Note:** whichever is chosen, the "else / can't-run → fail-closed" tail of the
contract is mirrored unchanged (any unexpected exit code, or the CLI/venv being
unrunnable, fails the CI job). The divergence question is ONLY about exit 2.

### Bias check (12 detectors run; top 3 surfaced)

- ⚠️ **Status Quo Bias / Availability Heuristic (combined seam)** — "the plugin
  and hook both warn-and-proceed on exit 2, so CI should too" is a reflexive
  copy of a vivid, recent, adjacent pattern. Guarded against in Decision 2 by
  checking the *base rate*: the plugin/hook run with a live operator who typed
  `--override-ack`; CI does not. The contexts differ materially, which is why
  2b is a live option rather than an obvious no.
- ⚠️ **Scope Creep Bias** — Approach C (fold in the full test suite) is the
  "do everything" temptation. Guarded against: C scores low precisely on the
  scope-match criterion, and the default scope is held to "only config-scan"
  per the task's explicit anti-scope-creep instruction. The full-suite CI is
  named as a *separate future decision*, not folded in to avoid choosing.
- ⚠️ **Authority Bias** — the prior `config-scan-wiring-control-proposal.md`
  (and its "Option C recommended") is a tempting authority to defer to.
  Guarded against: its recommendation is treated as prior *analysis* to
  reconcile, NOT as an operator decision (only the hook's D-A…D-I were
  converged), and the CI-specific tradeoffs are re-derived for the current
  hook-already-live reality rather than inherited wholesale.

(No Sunk Cost, Anchoring, Confirmation, Bandwagon, Dunning-Kruger, IKEA,
Survivorship, or Recency bias triggers materially: the tool is built and
tested, so the decision is purely *how to wire it into CI*, and both
recommendations follow the framework analysis, not a pre-existing preference.)

### Recommendation summary (advisory — for the operator to converge)

- **Decision 1 (CI design):** **Approach A** — dedicated `config-scan` workflow,
  `push` (to `main`) + `pull_request`. Swing factor vs B: the operator's
  branch-protection posture on direct pushes to `main`.
- **Decision 2 (exit-2 in CI):** **Option 2b** — hard-fail on exit 2 as a
  documented divergence, because CI is the authoritative non-interactive gate.
  2a is defensible if the operator values contract uniformity and accepts that
  the warn-branch is unreachable given the CI step never passes `--override-ack`.
- **Carried (not re-litigated):** block on FAIL (exit 1), WARN advisory unless
  `--strict`; mirror the "else/can't-run → fail-closed" tail exactly.
- **Also needs an operator confirmation (not a framework decision):**
  first-ever-CI appetite, and whether the check is marked **required** in
  branch protection from day one or introduced **advisory/non-required** first
  and promoted once seen clean.

## Selected Approach

**CONVERGED by the operator** (via orchestrator `question`, this session). The
four items below are **decided** — recorded verbatim as the operator's converged
choices. They are not to be re-argued or re-derived by `gleipnir-plan`; the plan
stage plans FROM them.

### Decision 1 (CI design) — CONVERGED

**Approach A** — dedicated `config-scan` GitHub Actions workflow triggered on
`push` (to `main`) AND `pull_request`.

### Decision 2 (exit-2 handling) — CONVERGED

**Hard-fail on exit code 2 (`PROCEED_UNCLOSED`) in CI** — a deliberate,
documented divergence from the `git-guard.ts` plugin / `hooks/pre-commit`
contract (which warn-and-proceed on exit 2 because a live operator typed
`--override-ack`; CI has no interactive operator in the loop and never passes
`--override-ack`, so this is the authoritative non-interactive gate refusing to
let an unclosed config land). The "else/can't-run → fail-closed" tail and the
exit-1 hard-block remain mirrored unchanged from the plugin/hook contract; ONLY
exit-2 semantics diverges, and that divergence must be documented in the
workflow file (a comment) AND in the plan/decision record so a future
drift-check treats it as an intentional, recorded exception rather than
accidental mismatch.

### Rollout confirmation — CONVERGED

**Advisory / non-required first** — the check is wired and runs on every
push+PR, but is NOT marked required in GitHub branch-protection settings yet;
promote to required later once observed green for a while.

> **Note for the plan:** actually configuring branch-protection "required status
> checks" is a GitHub repo-settings action outside this repo's tracked files —
> the plan should note this as an operator-performed follow-up step, not
> something the plan's file changes can enact themselves, and should NOT attempt
> to add a required-check config to any tracked file since GitHub branch
> protection isn't stored as repo YAML.

### Scope confirmation — CONVERGED

**Confirmed** — proceed with creating `.github/workflows/` for this repo for the
first time, scoped ONLY to config-scan (not a general CI pipeline). No other CI
concerns (test suite, lint, etc.) are in scope for this task. (This decides
against Approach C.)

### Carried unchanged (settled by prior precedent, not re-litigated)

- Block on FAIL (exit 1); WARN advisory unless `--strict`, matching
  `decide_config`'s severity model and the shipped hook.
- Mirror the "else / can't-run → fail-closed" tail of the exit-code contract
  exactly (any unexpected exit code, or an unrunnable CLI/venv, fails the CI
  job). Per Decision 2, ONLY exit-2 diverges; exit-0/exit-1/else are mirrored.

## Axis-1 / Axis-2 hardened-path classification (confirmed for the plan stage)

- **Axis 1 (eligibility gate): DISQUALIFIED from the light/prose track.** The
  plan touches `.github/**` (a GitHub Actions workflow file necessarily lives
  there), which is an explicit member of the Axis-1 disqualifier set `X`
  (`.github/**`). Therefore the plan runs the **FULL 8-stage hardened
  pipeline** (brainstorm → plan → spec-review → test → code → quality → git →
  gate), regardless of how small/config-only the change appears. The light
  path is not available.
- **Axis 2(a) (path rule): does NOT independently trip the enforcement-path
  set `E`.** A CI workflow under `.github/workflows/` is not in `E`
  (`.gleipnir/agents/**`, `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`,
  `.gleipnir/policy/**`, `.gleipnir/keys/**`, `.gleipnir/stage-role-map.md`,
  `opencode.jsonc`/`**/opencode.json`, or the enumerated repo-root cross-cutting
  files). It is not `opencode.jsonc`, not an agent/plugin/policy/keys file. So
  Axis 2(a) is not the reason for hardening.
- **Axis 2(b) (content rule): does NOT trip.** A config-scan CI workflow does
  **not** add a `permission:`/`tools:` block, a capability line
  (`edit|write|task|bash|webfetch` with allow/deny), a JSON(C) enforcement key
  (`"permission"|"tools"|"enabled"|"instructions"|"default_agent"|
  "subagent_depth"|"mcp"`), a new binding-table row in `stage-role-map.md`, or a
  `keys/**` digest line. It grants no agent capabilities. So Axis 2(b) is not
  tripped either.
- **Net classification:** The plan is on the **hardened / full-8-stage path
  because of Axis 1 (`.github/**` disqualifier), NOT because of Axis 2.** This
  is confirmed explicitly so the plan stage does not have to re-derive it. Note
  that "hardened path" here means the full 8-stage pipeline runs; the Axis-2
  hardened-path *review rubric* (two-pass spec-review + negative-check
  attestation for grant/enforcement changes) applies to enforcement-bearing
  config — since this change introduces **no** grant/enforcement pattern, the
  negative-check attestation has **no grant rows to attest** (a genuinely
  empty attestation set is correct here, not a skipped one). The plan should
  state this explicitly to avoid a phantom-gap finding at review.
- **Cognition Gate-1 routing:** `.github/**` is in `X` and a workflow YAML has
  **no class/function/module structure** → **case (ii)** (executable-but-non-OOP:
  CI YAML) → **DRY + Design Intent** apply; **SOLID + SRP attested "N/A — no
  object/function structure."** (A CI workflow that *runs* is executable per the
  `X` rationale, so it is case (ii), not the prose-only case (iii).)

## Open Questions (for `gleipnir-plan`, post-convergence)

**The material decisions and operator confirmations are CONVERGED (see Selected
Approach).** What remains here are non-material, planner's-discretion items only
— none re-opens a converged choice.

- **RESOLVED (Decision 1):** CI design = Approach A (push-to-`main` + PR,
  dedicated workflow). No longer open.
- **RESOLVED (Decision 2):** exit-2 handling = hard-fail (documented
  divergence). The cross-runtime drift-check therefore DOES need a documented CI
  exception for exit-2; exit-0/1/else stay mirrored. No longer open.
- **RESOLVED (scope):** config-scan only; no broader CI pipeline (Approach C
  rejected). No longer open.
- **RESOLVED (rollout):** advisory / non-required first; marking the check
  *required* is a GitHub repo-settings follow-up the operator performs — NOT a
  tracked-file change the plan can enact. No longer open.
- Pinned Python minor for `actions/setup-python` (`3.11` vs `3.12`) — trivial,
  planner's call within `>=3.11`; `3.12` matches the sandbox base image.
- Whether the drift-check that guards the plugin/hook exit-code parity should be
  extended to cover the CI mirror as a third runtime (recommended, and now REQUIRED
  to encode the exit-2 exception per Decision 2), and where that check lives (it
  is currently a review-time discipline, not a test).
- Whether a `config-scan` Makefile target should be added for parity/local
  convenience (optional; not required — CI can call `bin/gleipnir-preflight`
  directly, as the shipped hook does).

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| CI workflow (net-new) | `.github/workflows/config-scan.yml` (new) — Axis-1 disqualifier; full pipeline |
| Exit-code parity | (read-only reference) `.gleipnir/plugins/git-guard.ts`, `hooks/pre-commit`, `src/gleipnir/preflight/config_scan.py` — CI mirrors their contract (or documents the exit-2 divergence) |
| Decision record | `.gleipnir/decisions/config-scoping-preflight.md` — flip "CI deferred" open item to wired; record the converged CI design + exit-2 handling (Tier-3, operator-applied) |
| Session state | `.gleipnir/plans/SESSION-STATE.md` — close the "Config-scan CI gate" open thread (session-scribe) |
| Drift-check (optional) | a cross-runtime exit-code parity check extended to the CI mirror (location TBD by planner) |
| Makefile (optional) | `Makefile` — optional `config-scan` target for local parity (not required) |
