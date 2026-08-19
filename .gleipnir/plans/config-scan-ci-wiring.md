# Plan: Wire `config-scan` into CI (GitHub Actions push/PR gate)

> **Status: PLANNED — ready for `spec-review`.** ATLAS brief produced by
> `gleipnir-plan` FROM the converged design brief
> `config-scan-ci-wiring-brainstorm.md` (all four operator-converged decisions
> inherited verbatim; not re-decided here). Governing routing (from brief +
> delegation, NOT re-derived): **full 8-stage hardened pipeline** because the
> plan touches `.github/**` (Axis-1 disqualifier set `X`). Cognition Gate-1
> **case (ii)** (executable-but-non-OOP CI YAML).

---

## 1. Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | CI design | Dedicated `.github/workflows/config-scan.yml`, triggers `push`→`main` + `pull_request` | PR-only (B); folded broad CI (C) | **Operator-converged** (brief Selected Approach → Decision 1). Widest net, no branch-protection dependency, no scope creep |
| D2 | Exit-2 (`PROCEED_UNCLOSED`) handling in CI | **Hard-fail** the job (documented divergence from plugin/hook warn-and-proceed) | Warn-and-proceed (mirror contract) | **Operator-converged** (brief Decision 2). CI is the authoritative non-interactive gate; no live operator typed `--override-ack` for a CI run |
| D3 | Exit 0 / exit 1 / else-or-can't-run handling | 0=pass, 1=fail, else/can't-run=fail-closed — mirrored unchanged from plugin/hook | (n/a — carried) | **Operator-converged** (brief "Carried unchanged"). Only exit-2 diverges |
| D4 | Rollout | Advisory / non-required; branch-protection "required check" is an operator follow-up outside tracked files | Mark required from day one | **Operator-converged** (brief Rollout). GitHub branch protection is not repo YAML; plan cannot enact it |
| D5 | Scope | ONLY config-scan wiring; no test/lint/coverage CI | Bundle full pytest suite (Approach C) | **Operator-converged** (brief Scope). Anti-scope-creep |
| D6 | Invocation path in CI | Build a **bare `.venv`** (`python -m venv .venv`, no deps) and call `./bin/gleipnir-preflight config-scan` — the SAME entrypoint the hook + plugin use | Call `python -m gleipnir.preflight config-scan` directly with `PYTHONPATH=src` (no venv) | **Plan-level (Two-Way Door).** The shim hard-codes `exec "$repo/.venv/bin/python"` (verified `bin/gleipnir-preflight:20-21`); the direct-module path works and is stdlib-only, but mirroring the shim makes CI exercise the *actual production invocation* the hook/plugin rely on, so a shim regression is caught. One extra ~2s venv step is negligible for a milliseconds check |
| D7 | Python version | `actions/setup-python` pinned to `3.12` | `3.11` (the `requires-python` floor) | **Plan-level (Two-Way Door).** `pyproject.toml` requires `>=3.11`; `3.12` matches the S-2 sandbox base `python:3.12-slim` (verified `Containerfile:21`, `runtime.py:51`), so CI runs the same minor the enforcement core is validated against |
| D8 | `actions/checkout` + `setup-python` pinning | Pin both by **full commit SHA** with a trailing version comment | Pin by tag (`@v4`) | **Plan-level (Two-Way Door).** SHA-pinning a third-party action is the supply-chain-hardening default; a moving tag is a mutable dependency. Consistent with the repo's digest-pinned container base |
| D9 | Executable-bit dependency | Rely on the committed `100755` mode of `bin/gleipnir-preflight` (verified restored, `bin-executable-bit.md`); add a defensive `chmod +x` step so a `core.fileMode=false` checkout still runs | Assume checkout preserves +x silently | **Plan-level.** Belt-and-braces: `actions/checkout` preserves committed modes, but an explicit `chmod +x` makes the job robust and self-documenting; costs nothing |
| D10 | Drift-check for the third (CI) exit-code mirror + Makefile target | **Do NOT add** either in this task; record the CI exit-2 divergence in the decision record as the authoritative "intentional exception" note | Add a cross-runtime drift-check test / `config-scan` Makefile target now | **Plan-level scope discipline.** Both are brief "optional" items. A code drift-check is a `tests/**` artifact (out of this plan's touched set, would enlarge blast radius); the divergence is documented durably instead. Named as an operator follow-up |
| D11 | `test`-stage executor + shape | (a) Static/dry validation of the YAML by `quality-reviewer` at review (schema + exit-code-mapping read-through); **no** live GitHub Actions trigger inside the pipeline. (b) IF a live end-to-end trigger is wanted, it is an **operator** (or `git-ops` pushing to a throwaway branch) action, named explicitly — `gleipnir-code` CANNOT do it | Route a live `git push` / Actions trigger to `gleipnir-code` | **Plan-level, precedent-bound** (`config-scoping-preflight.md` "Host shell tests execute OUTSIDE the roster grant"). `gleipnir-code`'s bash grant is exact-match `bin/gleipnir-sandbox test\|lint` only — no `git push`, no `sh`. Repeating that mis-route is the exact error spec-review previously caught |
| D12 | `code`-stage executor | Both files (`.github/workflows/config-scan.yml` new; `config-scoping-preflight.md` edit) are applied by the **operator or a bounded build role** — NOT a roster subagent. **Accurate grant note:** `gleipnir-code`'s `edit` grant is `"*": allow` minus denies for `.gleipnir/**`, `.git/**`, `src/gleipnir/preflight/**` only (verified `agents/gleipnir-code.md:12-16`), so it CAN technically write `.github/**` today — the routing is NOT because it lacks the capability. It is chosen (a) to bundle both target files under one coherent apply step with a single executor, since the decision-record edit has no roster path anyway (`gleipnir-code` denies `.gleipnir/**` — the L-C27 gap), and (b) because the repo's first-ever `.github/workflows/` file is a deliberately elevated authorship action kept off the standard roster path | Route file creation to `gleipnir-code` | **Plan-level.** Rationale (a)+(b) above; the decision-record edit is Tier-3 operator-applied (genuinely no roster path). NOTE: `gleipnir-code`'s edit grant not excluding `.github/**` is a latent roster-permission observation worth a future `tier3-coach` look — OUT OF SCOPE for this plan to fix, recorded as an observation only |

---

## 2. Architect

**Problem (one sentence).** Add a push/PR-time GitHub Actions gate that runs
`config-scan` independently of local hook state, so a mis-scoped enforcement
config cannot land on `main` even when a contributor's local `pre-commit` hook
is absent, disabled, or bypassed with `--no-verify`.

**User.** The operator / maintainers of the Gleipnir repo (the merge gate),
and every contributor whose push/PR is checked. Secondary consumer: a future
`gleipnir` release that can point at a green required check.

**Measurable success criteria.**
1. A workflow file exists at `.github/workflows/config-scan.yml` and is picked
   up by GitHub Actions on `push` to `main` and on any `pull_request`.
2. On a config that is CLOSED (config-scan exit 0) the job **succeeds**.
3. On a REFUSE (exit 1) the job **fails**.
4. On `PROCEED_UNCLOSED` (exit 2) the job **fails** (the documented divergence).
5. On any other exit code, or an unrunnable CLI/venv, the job **fails**
   (fail-closed).
6. The exit-2 divergence is documented **both** in a workflow comment **and**
   durably in `.gleipnir/decisions/config-scoping-preflight.md`.
7. The job requires **no** repository write permissions and works for a
   fork-originated PR (read-only `GITHUB_TOKEN` is sufficient).
8. No dependency install is performed (stdlib-only check); only Python + a bare
   `.venv` are provisioned.

**Constraints (inherited, verified).**
- Enforcement core is stdlib-only, `requires-python = ">=3.11"` (verified
  `pyproject.toml:5,8`); config-scan needs **no** dependency install.
- The shim `bin/gleipnir-preflight` execs `"$repo/.venv/bin/python"` (verified
  lines 20-21) → a `.venv` must exist at repo root for the shim path (D6).
- `config-scan` subcommand needs **no** `--agent-uid`/`--agent-gid` — it is
  dispatched before the boundary parser (verified `__main__.py:113-124`). The
  exact CI invocation is `./bin/gleipnir-preflight config-scan`.
- Exit-code contract source of truth (verified): `config_scan.py`
  `config_scan_main` returns 0/2/1 for CLOSED/PROCEED_UNCLOSED/REFUSE
  (lines 1248-1253); `git-guard.ts` `decideFromExit` maps 0→allow, 2→warn,
  1→abort, else→abort (lines 128-148); `hooks/pre-commit` maps the same
  (lines 61-80). CI mirrors 0/1/else **exactly** and diverges on 2 only.
- **Executor-routing constraint (corrected).** `gleipnir-code`'s `edit` grant is
  `"*": allow` minus narrow denies for `.gleipnir/**`, `.git/**`, and
  `src/gleipnir/preflight/**` (verified `agents/gleipnir-code.md:12-16`);
  `.github/**` is **NOT** in that deny list, so `gleipnir-code` structurally CAN
  write `.github/workflows/config-scan.yml` today. It is nonetheless routed to the
  **operator / bounded build role** — NOT because a capability path is missing,
  but (a) to keep both target files (the new workflow AND the Tier-3
  decision-record edit) under ONE coherent apply step with a single executor,
  since the decision-record edit genuinely has no roster path anyway
  (`gleipnir-code` denies `.gleipnir/**` outright; the L-C27 gap — no roster agent
  materializes the operating-posture Tier-3 instructed-write grant); and (b) the
  repo's first-ever `.github/workflows/` file is a deliberately elevated/reviewed
  authorship action this plan keeps off the standard roster path regardless of the
  technical grant. (Distinct from D11: `gleipnir-code` also cannot `git push` /
  trigger Actions — a separate, real capability gap.)
- Rollout advisory: no branch-protection change in tracked files (D4).

---

## 3. Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Status | Source of truth for |
|---|---|---|---|
| CI workflow | `.github/workflows/config-scan.yml` | **NEW** (first-ever `.github/`) | The push/PR gate; the CI exit-code mapping (third mirror) |
| Decision record update | `.gleipnir/decisions/config-scoping-preflight.md` | **EDIT** (exists, 131 lines) | Durable record that CI is now wired + the exit-2 divergence rationale |
| Exit-code contract (read-only ref) | `src/gleipnir/preflight/config_scan.py::config_scan_main` | exists | Canonical 0/1/2 semantics |
| Exit-code mirror #1 (read-only ref) | `.gleipnir/plugins/git-guard.ts::decideFromExit` | exists | Plugin mapping CI mirrors (except exit 2) |
| Exit-code mirror #2 (read-only ref) | `hooks/pre-commit` | exists | Hook mapping CI mirrors (except exit 2) |
| Shim entrypoint (read-only ref) | `bin/gleipnir-preflight` | exists (`100755`) | The invocation CI reproduces (D6) |

### Integrations map

- **GitHub Actions runner → repo.** `actions/checkout` (SHA-pinned) fetches the
  tree preserving committed file modes. No secrets, no registry, no network
  beyond the action downloads.
- **Runner → Python.** `actions/setup-python@<sha>` provisions CPython 3.12.
- **Job → config-scan.** `python -m venv .venv` (bare, no `pip install`), then
  `./bin/gleipnir-preflight config-scan` run from repo root. The shim resolves
  the repo root from its own location (verified `bin/gleipnir-preflight:18-19`),
  so cwd is not fragile, but the job runs it from the checkout root anyway.
- **Exit code → job status.** The job's final step branches on the captured
  exit code per the D2/D3 mapping and exits nonzero to fail the job on
  1 / 2 / anything-unexpected / can't-run.
- **`GITHUB_TOKEN`.** The workflow declares top-level `permissions:
  contents: read` (least privilege). config-scan is strictly read-only (verified
  `config_scan.py` docstrings + thin edge is `read_text`/`glob` only) and writes
  nothing back, so no `write` scope is needed — this is what makes a **fork PR**
  safe: fork PRs get a read-only token by default, which is exactly sufficient.

### Edge cases

| # | Edge case | Handling |
|---|---|---|
| E1 | config well-scoped (exit 0) | Step succeeds; job green |
| E2 | REFUSE — FAIL finding / unparseable (exit 1) | Step exits nonzero; job red |
| E3 | `PROCEED_UNCLOSED` (exit 2) — divergence | Step exits nonzero; job red (only reachable if someone edits the step to pass `--override-ack`, which STILL fails — the point of D2) |
| E4 | Unexpected exit code (e.g. 3, 137) | `case *)` → exit nonzero; fail-closed |
| E5 | `.venv` missing/broken or `bin/gleipnir-preflight` non-executable / shim can't run | `set -euo pipefail` + explicit code capture: a nonzero/failed invocation is caught and the job fails-closed; the defensive `chmod +x` (D9) removes the most likely can't-run cause |
| E6 | Fork PR (untrusted contributor) | `permissions: contents: read` only; no secrets exposed; read-only scan needs no write-back — job runs and reports normally |
| E7 | Push to a non-`main` branch | Not triggered (push filter is `branches: [main]`); PRs still cover feature branches via the `pull_request` trigger |
| E8 | Redundant double-run (push to a PR branch fires both triggers) | Accepted (brief Approach A con); negligible for a milliseconds check |
| E9 | `core.fileMode=false` on the runner masking committed +x | Mitigated by D9's explicit `chmod +x` before invocation |

---

## 4. Link (validated before building)

- **Invocation verified from source, not assumed** (delegation requirement):
  read `bin/gleipnir-preflight` (execs `.venv/bin/python -m gleipnir.preflight`)
  and `src/gleipnir/preflight/__main__.py` (`config-scan` token dispatched at
  line 113 to `config_scan.config_scan_main` **before** the uid/gid parser) —
  confirms `./bin/gleipnir-preflight config-scan` is the complete, flagless
  invocation and the shim needs a `.venv`.
- **Exit-code contract verified from all three sources** (`config_scan_main`
  0/2/1; `git-guard.ts` `decideFromExit`; `hooks/pre-commit` case block) — the
  CI mapping is a faithful third mirror diverging on exit 2 only.
- **Python version verified** against `pyproject.toml` (`>=3.11`) and the
  sandbox base image `python:3.12-slim` (`Containerfile:21`, `runtime.py:51`).
- **No `.github/` exists** — confirmed by the brief's Explore (glob/grep found
  none); this is the first CI workflow. No collision risk.
- **Decision-record target verified**: `config-scoping-preflight.md` exists with
  a "Honesty labels / open items" section (lines 83-92) whose first bullet
  currently says "CI still deferred" — the exact text to flip.
- **Executable bit verified**: `bin/gleipnir-preflight` committed `100755`
  (restored in `9645974`, `bin-executable-bit.md`); the D9 `chmod +x` is
  defensive, not load-bearing.
- **Roster write-grant boundary verified (corrected)**: `gleipnir-code`'s edit
  deny list is `.gleipnir/**`, `.git/**`, `src/gleipnir/preflight/**` only
  (`agents/gleipnir-code.md:12-16`) — `.github/**` is NOT excluded, so it CAN
  write the workflow file today; the Tier-3 decision-record edit, by contrast, has
  no roster path (the `.gleipnir/**` deny — L-C27). Executor routing D11/D12 is a
  deliberate bundling/elevation choice, not a missing-capability forcing function
  (see §2, D12, §7).

---

## 5. Assemble (intended build order)

1. **`spec-review`** (`quality-reviewer`) — two-pass hardened rubric (see §7).
   Validate: the drafted YAML (§8) matches the converged decisions, the
   exit-code mapping is a faithful mirror-except-exit-2, the Design Principles
   section is present & falsifiable, and the empty Axis-2 negative-check set is
   correctly empty (not a skipped gap).
2. **`test`** — static validation of the workflow YAML per D11(a): reviewer
   confirms YAML well-formedness + exit-code branch correctness by read-through
   (and `actionlint` if the reviewer's environment has it — advisory, not
   required, since it is not in the roster grant). **No** live Actions trigger
   in-pipeline. This stage carries an attested transition, NOT "N/A — no
   executable artifact" (the workflow IS executable-but-non-OOP); the arbiter
   here is static conformance, because a live trigger requires a named external
   executor (D11(b)).
3. **`code`** — apply the two file changes (D12): create
   `.github/workflows/config-scan.yml` with the §8 content; edit
   `config-scoping-preflight.md` per §8. Applied by operator / bounded build
   role. Note (D12): `gleipnir-code` *could* technically write the `.github/**`
   file (its edit deny list omits `.github/**`), but both files are bundled under
   one executor because the Tier-3 decision-record edit has no roster path anyway
   and the first-ever CI workflow is a deliberately elevated authorship action.
4. **`quality`** — blast-radius pass (§7) incl. the SOLID/DRY dimension (DRY
   only, per Gate-1 case (ii)) and the cognition honour-check (does the applied
   YAML honour the stated Design Intent?).
5. **`git`** (`git-ops`) — commit + push both files.
6. **`gate`** (orchestrator) — read attestation, emit pipeline state.
7. **Operator follow-ups (OUT of pipeline, named not enacted):**
   (a) after the check is observed green, optionally mark it a **required**
   status check in GitHub branch-protection settings (D4 — repo-settings UI,
   not tracked YAML); (b) optionally run a **live** end-to-end trigger via a
   throwaway branch push/PR to confirm the workflow runs & reports (D11(b)),
   executed by the operator or `git-ops`; (c) optional future drift-check test +
   `config-scan` Makefile target (D10).

---

## 6. Stress-test (acceptance checks)

Concrete, checkable criteria the result is validated against:

| ST | Scenario | Expected | How verified |
|---|---|---|---|
| ST-1 | Well-scoped config (exit 0) | Job **green** | Read-through: `0)` branch is a no-op / success; the current live repo scans CLOSED (per `config-scoping-preflight.md` ST-4), so the real first run should be green |
| ST-2 | REFUSE (exit 1) | Job **red** | Read-through: `1)` branch sets nonzero exit; matches plugin/hook |
| ST-3 | `PROCEED_UNCLOSED` (exit 2) — the divergence | Job **red** | Read-through: `2)` branch sets nonzero exit (NOT warn-and-proceed); comment documents the divergence |
| ST-4 | Unexpected exit code | Job **red** (fail-closed) | Read-through: `*)` branch sets nonzero exit |
| ST-5 | Can't-run (missing/broken `.venv` or non-executable shim) | Job **red** (fail-closed) | `set -euo pipefail` + code capture: a failed `./bin/gleipnir-preflight` invocation yields a nonzero captured code → `*)` → fail; D9 `chmod +x` removes the common cause |
| ST-6 | Fork PR | Job runs; no secrets; **no write perms needed** | `permissions: contents: read` present at top level; config-scan is read-only (verified) |
| ST-7 | Trigger coverage | Fires on push→`main` AND on `pull_request` | `on:` block has both triggers; `push.branches: [main]` |
| ST-8 | No dependency install | Job does NOT run `pip install` | No `pip`/`install` step in the YAML; only `python -m venv .venv` |
| ST-9 | Exit-code parity with plugin/hook (except exit 2) | 0/1/else identical to `decideFromExit` + `hooks/pre-commit` | Side-by-side read-through of the `case` block vs the two mirrors |
| ST-10 | Divergence documented durably | `config-scoping-preflight.md` flipped to "CI wired" + exit-2 exception recorded | The applied edit (§8) present in the file at `quality` |
| ST-11 | Design Intent honoured | Applied YAML fails-closed on every non-zero/unexpected path (no warn-and-proceed anywhere) | Cognition honour-check at `quality` |

---

## 7. Execution Workflow

**Pipeline:** full 8-stage hardened path (`.github/**` ∈ Axis-1 `X`). Route:
`spec-review → test → code → quality → git → gate` per §5.

**Hardened-path review rubric (per `stage-role-map.md`).** `quality-reviewer`
runs **two separate passes**, each with its own recorded verdict:
1. **Spec-conformance** (`SPEC-CONFORM: PASS/FAIL`) — rubric = this plan + the
   converged brief. Includes the cognition **intent-quality sub-check** (is the
   §9 Design Intent specific/falsifiable, not a vacuous aspiration?).
2. **Blast-radius / false-success** — adversarial: how could this be wrongly
   green? Includes the **DRY dimension** (Gate-1 case (ii): DRY only). At
   `quality`, includes the **honour check** (does the applied YAML honour §9's
   Design Intent — specifically, no warn-and-proceed path exists anywhere?).

**Negative-check attestation table — EXPLICITLY EMPTY (no phantom gap).** The
hardened-path negative-check attestation is required **only for
grant/enforcement changes** (Axis-2(a) path in `E`, or an Axis-2(b) `G`-pattern
line). This plan:
- adds **no** file under the enforcement-path set `E` (a `.github/workflows/`
  file is not in `E`; verified against the brief's Axis-2(a) analysis);
- adds **no** `permission:`/`tools:` block, capability line
  (`edit|write|task|bash|webfetch` + allow/deny), JSON(C) enforcement key,
  `stage-role-map.md` binding row, or `keys/**` digest line (Axis-2(b) `G`).

Therefore the **grant-row set is genuinely empty** — there is nothing to attest,
and this is **correct, not a skipped step**. Spec-review MUST treat the empty
attestation table as conformant (the change grants no agent capability). This is
stated here so review does not flag a phantom gap (delegation requirement).

**`[D]`/`[J]` evidence tags.** Findings/attestations at review annotate their
basis: `[D]` = tool-produced (e.g. `actionlint` output, a `grep`/`diff` of the
applied file), `[J]` = judgment. For THIS plan the empty attestation set carries
no `[D]`/`[J]` rows (nothing to attest).

**Executor routing (the load-bearing operational note).**
- `test` (D11): static YAML validation by `quality-reviewer` at review;
  optional `actionlint` if available (advisory). A **live** GitHub Actions
  trigger is OUT of the pipeline and, if wanted, is an **operator** or
  **`git-ops`** action (a real push to a throwaway branch) — `gleipnir-code`
  CANNOT `git push` or trigger Actions (its bash grant is exact-match
  `bin/gleipnir-sandbox test|lint` only). This mirrors the precedent recorded in
  `config-scoping-preflight.md` ("Host shell tests execute OUTSIDE the roster
  grant") — do NOT re-route a live trigger to `gleipnir-code`.
- `code` (D12): both the `.github/workflows/config-scan.yml` file and the Tier-3
  decision-record edit are applied by the **operator / bounded build role**, not a
  roster subagent. Accuracy note: `gleipnir-code`'s edit grant does NOT exclude
  `.github/**` (deny list is `.gleipnir/**`, `.git/**`, `src/gleipnir/preflight/**`
  only — verified `agents/gleipnir-code.md:12-16`), so it *can* structurally write
  the workflow file; the routing is a deliberate choice (bundle both files under
  one executor; the decision-record edit has no roster path via the `.gleipnir/**`
  deny — L-C27; first-ever CI workflow is elevated authorship), NOT a missing
  capability path. This is distinct from D11 (that `gleipnir-code` cannot
  `git push` / trigger Actions — a separate, real bash-grant gap).
- `git` (D5-scope, single-holder G-2): `git-ops` commits + pushes both files.

---

## 8. Concrete file-by-file diff plan

### 8a. NEW file: `.github/workflows/config-scan.yml`

Full drafted content (SHA pins are placeholders to be resolved to the current
release SHA of each action at apply time — the trailing comment records the
intended tag; resolving the exact current SHA is a `code`/operator step):

```yaml
# Gleipnir config-scan CI gate.
#
# Runs `bin/gleipnir-preflight config-scan` (the config-scoping preflight) as a
# server-side push/PR gate, independent of local hook state — so a mis-scoped
# enforcement roster / opencode.jsonc cannot land on `main` even if a
# contributor's local pre-commit hook is absent, disabled, or bypassed with
# `git commit --no-verify`. This is the THIRD mirror of the exit-code contract
# (after .gleipnir/plugins/git-guard.ts and hooks/pre-commit).
#
# EXIT-CODE CONTRACT (source of truth:
# src/gleipnir/preflight/config_scan.py::config_scan_main):
#   0 = CLOSED           -> pass  (config well-scoped)
#   1 = REFUSE           -> FAIL  (a FAIL finding or unparseable config)
#   2 = PROCEED_UNCLOSED -> FAIL  *** DELIBERATE, DOCUMENTED DIVERGENCE ***
#   * = anything else / can't-run -> FAIL (fail-closed)
#
# DIVERGENCE NOTE (exit 2): the git-guard.ts plugin and hooks/pre-commit treat
# exit 2 as WARN-AND-PROCEED, because a live, interactive operator deliberately
# typed `--override-ack` at commit/launch time. CI is the AUTHORITATIVE,
# non-interactive, agent-unreachable gate: there is no interactive operator in
# the loop of a CI run, and this workflow never passes `--override-ack`. So CI
# refuses to let an UNCLOSED config land regardless of an override flag. This
# divergence is intentional and is recorded durably in
# .gleipnir/decisions/config-scoping-preflight.md — a drift-check must treat it
# as a recorded exception, NOT accidental mismatch. Exit 0/1/else are mirrored
# unchanged.
#
# Rollout: advisory / non-required. Marking this a REQUIRED status check is a
# GitHub branch-protection setting (repo-settings UI), NOT tracked YAML — an
# operator follow-up once the check is observed green.

name: config-scan

on:
  push:
    branches: [main]
  pull_request:

# Least privilege: the scan is strictly read-only and writes nothing back, so a
# read-only token is sufficient. This is also what makes fork PRs safe (they get
# a read-only GITHUB_TOKEN by default).
permissions:
  contents: read

jobs:
  config-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@<CHECKOUT_SHA>  # v4.x — resolve to current release SHA

      - name: Set up Python
        uses: actions/setup-python@<SETUP_PYTHON_SHA>  # v5.x — resolve to current release SHA
        with:
          python-version: '3.12'  # matches the S-2 sandbox base python:3.12-slim

      # The enforcement core (incl. config_scan.py) is stdlib-only
      # (.gleipnir/decisions/runtime-and-deps.md), so a BARE venv with NO
      # dependency install is sufficient. bin/gleipnir-preflight execs
      # "$repo/.venv/bin/python", so the venv must exist.
      - name: Create bare venv (no deps — stdlib-only core)
        run: python -m venv .venv

      # Defensive: actions/checkout preserves the committed 100755 mode, but a
      # runner with core.fileMode=false could mask it. chmod costs nothing.
      - name: Ensure preflight shim is executable
        run: chmod +x bin/gleipnir-preflight

      - name: Run config-scan (fail-closed; exit 2 hard-fails — see header)
        shell: bash
        run: |
          set -uo pipefail
          code=0
          ./bin/gleipnir-preflight config-scan || code=$?
          case "$code" in
            0)
              echo "config-scan: CLOSED — config well-scoped."
              ;;
            1)
              echo "::error::config-scan REFUSED (exit 1): the agent roster / opencode.jsonc is mis-scoped. Fix the finding reported above."
              exit 1
              ;;
            2)
              echo "::error::config-scan reported PROCEED_UNCLOSED (exit 2). CI is the authoritative non-interactive gate and FAILS on an unclosed config regardless of --override-ack (documented divergence from the plugin/hook contract)."
              exit 1
              ;;
            *)
              echo "::error::config-scan returned unexpected exit code $code (or could not run); failing closed."
              exit 1
              ;;
          esac
```

Notes on the draft:
- `set -uo pipefail` (not `-e`): the `|| code=$?` idiom must capture a nonzero
  exit WITHOUT `-e` aborting the step before the `case` runs. `-u`/`-o pipefail`
  are retained for the rest.
- The `case` block is byte-parallel to `hooks/pre-commit` lines 61-80 for
  0/1/`*`; the **only** divergence is the `2)` arm (hook proceeds, CI exits 1).
- `::error::` annotations surface the reason in the GitHub Actions UI without
  needing write permissions.
- SHA placeholders `<CHECKOUT_SHA>` / `<SETUP_PYTHON_SHA>` are resolved at apply
  time (D8); the version comment records intent.

### 8b. EDIT: `.gleipnir/decisions/config-scoping-preflight.md`

Two text changes, both in the file's existing structure (verified line numbers):

**Change 1 — the status header (line 3).** Flip "CI wiring still deferred":

- FROM: `**Status: authored, built, WIRED on both the broker-plugin path AND the VCS pre-commit hook; CI wiring still deferred.**`
- TO: `**Status: authored, built, WIRED on the broker-plugin path, the VCS pre-commit hook, AND CI (push/PR).**`

And the sentence at lines 12-13 ("**Still deferred:** running config-scan in
CI …") is replaced with a "now wired in CI" sentence pointing at
`../plans/config-scan-ci-wiring.md` and `.github/workflows/config-scan.yml`.

**Change 2 — the "Honesty labels / open items" first bullet (lines 85-92).**
Replace the "CI still deferred" bullet with a "CI wired" bullet recording:
- config-scan now runs as a **third** enforcement path — a GitHub Actions
  push/PR gate (`.github/workflows/config-scan.yml`), independent of local hook
  state;
- the **exit-2 divergence**: CI hard-fails on exit 2 (`PROCEED_UNCLOSED`),
  deliberately diverging from the plugin/hook warn-and-proceed, because CI is the
  authoritative non-interactive gate with no live operator behind an
  `--override-ack`; exit 0/1/else are mirrored unchanged. **This is the durable
  home of that divergence** so a future cross-runtime drift-check treats it as a
  recorded, intentional exception, not accidental mismatch;
- **rollout is advisory / non-required**; marking the check a *required* status
  check is a GitHub branch-protection follow-up (repo-settings UI, not tracked
  YAML) the operator performs once the check is observed green;
- **operator follow-ups** (named, not enacted): (a) optional live end-to-end
  trigger via a throwaway branch; (b) optional future cross-runtime exit-code
  drift-check test extended to the CI mirror; (c) optional `config-scan`
  Makefile target for local parity.

(Exact final wording of the bullet is a `code`/operator authoring step; the
required *content* is the four points above. This is a Tier-3 record →
operator-applied.)

---

## 9. Design Principles (Gate-1 case (ii): executable-but-non-OOP CI YAML)

Routing: `P ∩ X ≠ ∅` (touches `.github/**`) and the touched `X`-member (a CI
workflow YAML) has **no class/function/module structure** → **case (ii)**:
DRY + Design Intent apply; SOLID + SRP attested N/A.

**SOLID analysis:** **N/A — no object/function structure.** A GitHub Actions
workflow YAML declares steps, not classes/functions/interfaces; there is no
Liskov / Interface-Segregation / Dependency-Inversion / Open-Closed subject.

**Single-Responsibility (class/module) check:** **N/A — no object/function
structure.** (The *workflow* has a single job with a single purpose, but there
is no module/class SRP to analyse in the plan-format sense.)

**DRY analysis.** The exit-code mapping (0/1/2/else) is **necessarily duplicated**
across three runtimes — `config_scan_main` (Python), `git-guard.ts` (TS),
`hooks/pre-commit` (POSIX sh), and now this workflow (bash-in-YAML). This is
**accepted, pre-existing duplication** (`config-scoping-preflight.md`: "Mapping
duplicated across the TS plugin and the POSIX hook is accepted (two runtimes,
cannot share code); a review-time drift check guards it"). CI cannot import the
Python or TS mapping, so a fourth copy is unavoidable. DRY is honoured by: (a)
keeping the `case` block **byte-parallel** to `hooks/pre-commit` for the shared
arms (0/1/else) so drift is visually detectable; (b) recording the ONE
intentional difference (exit 2) in exactly one durable place
(`config-scoping-preflight.md`), not scattered. No NEW logic is duplicated that
could have been referenced instead — the invocation is the single existing shim,
not a reimplementation of the check. Constants (Python version `3.12`, action
SHAs) each appear once.

**Design Intent (specific & falsifiable).** *The CI job MUST fail-closed on
every config-scan outcome that is not exit 0: exit 1, exit 2, any other exit
code, and any can't-run condition each cause a nonzero job result — there is NO
warn-and-proceed path anywhere in the workflow, and the job requires NO
repository write permission.* This is falsifiable: a reviewer can point to a
violation if any `case` arm other than `0)` allows the job to succeed, if a
`--override-ack` flag were added to the invocation, if a warn-and-continue
branch existed, or if `permissions:` granted any `write` scope. (This is exactly
the D2/D3 converged contract and the E6 fork-safety property, restated as a
checkable design claim; the `quality` honour-check verifies the applied YAML
against it.)

---

## 10. Axis-1 / Axis-2 classification (restated for spec-review; not re-derived)

- **Axis 1: DISQUALIFIED from the light/prose track** — touches `.github/**` ∈
  `X`. Full 8-stage hardened pipeline runs (confirmed by brief + delegation).
- **Axis 2(a): does NOT independently trip** — a `.github/workflows/` file is
  not in the enforcement-path set `E`.
- **Axis 2(b): does NOT trip** — no `permission:`/`tools:`/capability-line /
  JSON(C) enforcement-key / binding-row / `keys/**` digest content.
- **Net:** hardened *pipeline* runs because of Axis 1; the hardened-path
  **negative-check attestation set is genuinely EMPTY** (no grant/enforcement
  change) — this is correct, not a skipped gap (see §7).
- **Cognition Gate-1: case (ii)** (executable-but-non-OOP CI YAML) → §9 form.

---

## 11. Open questions

**None material.** All four operator-material decisions are converged (D1-D5);
every remaining choice (D6-D12) is a Two-Way-Door plan-level call resolved above.

Non-material items intentionally deferred (named, not open): the action SHA
values to pin (D8 — a mechanical apply-time resolution), and the optional
follow-ups in §5 step 7 / D10 (drift-check test, Makefile target, live trigger,
branch-protection promotion) — all operator follow-ups outside this plan's
touched set, none blocking.
```
