# Tier-3 Control Proposal: wiring the `config-scan` config-scoping preflight

_Produced by the `tier3-coach` skill. This is a PROPOSAL — the artifacts belong
in the substrate/VCS layer (`hooks/`) and the CI/platform layer (`.github/`),
neither of which the agent can write. The exact, ready-to-apply artifacts are
given verbatim below; applying them is the operator's action per Handoff. The
material tradeoffs in the Decision Analysis are surfaced for the operator to
converge — this brief does NOT decide them._

## Gap

The config-scoping preflight `config-scan` **exists and is fully tested** but
**nothing runs it automatically** — it is a guard that is authored but not
wired in. It scans the opencode agent roster (`.gleipnir/agents/*.md`
frontmatter) plus `opencode.jsonc` and returns a fail-closed verdict:

- exit **0 = CLOSED** (config well-scoped; launch OK)
- exit **1 = REFUSE** (a `FAIL` finding or unparseable config; DO NOT launch)
- exit **2 = PROCEED_UNCLOSED** (not-closed but operator `--override-ack`)

It catches, among others: a boolean where an allow/deny/ask string is expected
(the L-C12 grammar bug), a **single-holder violation** (e.g. `gleipnir-git_*`
not denied by an agent that should deny it), a **fail-open MCP namespace** (no
agent denies a broker namespace at all), a **global-disable** in
`opencode.jsonc`'s top-level `tools`, a **mis-scoped glob** (`gleipnir-git*`
missing the underscore, which never matches a real tool name), and any
**malformed/unparseable** agent frontmatter or JSONC agent block.

**What is unenforced today:** a misconfigured or malformed agent roster —
fail-open MCP scoping, a single-holder violation, a broken `permission:` block,
malformed jsonc — can be **committed and launched with no automatic check**.
The only thing standing between a broken roster and a live session is an
operator remembering to run `bin/gleipnir-preflight config-scan` by hand. A
guard that must be remembered is, in practice, a guard that is off.

**Safety vs preference.** Detecting a **fail-open / single-holder / grammar**
defect in enforcement-bearing config is a **safety invariant** — these are the
exact roster mis-scopings the whole framework exists to prevent, and shipping
one silently is a real regression. Whether to *also* fail on WARN-severity
findings (mis-scoped glob, over-restriction) via `--strict`, and whether the
fast local check should be default-on or opt-in, are **operator preferences**.

## Correct layer

Two layers, both **agent-unwritable** by design (`tier3-coach` layer map):

| Where the control belongs | Layer | Agent-writable? | Who applies |
|---|---|---|---|
| `hooks/pre-commit` config-scan step | **Substrate / VCS** | **No** — `git-ops` denies `.git/**`; no role has a hooks grant | Operator (edits committed `hooks/`; `core.hooksPath` already set) |
| `.github/workflows/config-scan.yml` | **CI / platform** | **No** — no roster role holds platform-admin credentials | Operator (commits YAML; GitHub runs it) |

Confirmation the agent cannot write these: this brainstorm subagent's only
`.gleipnir/` write grant is Tier-0 `plans/**` (this file). It has no grant to
`hooks/`, `.github/`, or `.git/`. That the control belongs somewhere the agent
cannot reach is exactly why the output is a proposal, not an edit — routing it
into a reachable layer to dodge the handoff is the `tier3-coach` Anti-Pattern 1.

**Platform confirmed:** origin remote is `git@github.com:Djarid/gleipnir.git`
→ GitHub → the CI option is **GitHub Actions**. There is **no `.github/`
directory and no `.gitlab-ci.yml`** in the repo today: wiring CI stands up the
**first-ever CI** in this repo (an appetite question for the operator — see
Decision Analysis tradeoff (4)).

**Verified ground truth (re-read this session):**
- `config-scan` is a subcommand on the out-of-framework CLI
  `bin/gleipnir-preflight` (`src/gleipnir/preflight/__main__.py::main()`
  dispatches on a leading `config-scan` token; `config_scan_main` owns its own
  `--strict` / `--override-ack` flags; exits 0/1/2 as above).
- `bin/gleipnir-preflight` is a thin shim that execs
  `"$repo/.venv/bin/python" -m gleipnir.preflight "$@"` — **it requires a
  `.venv`**. A pre-commit step must therefore degrade gracefully (skip, not
  crash the commit) when the venv/CLI is absent on a contributor's machine.
- `hooks/pre-commit` already exists (46 lines): `set -eu`, a `fail=0`
  accumulator, an always-on secret-scan, and opt-in branch/data-file blocks
  toggled by `GLEIPNIR_GIT_*` env vars. `core.hooksPath = hooks` **is already
  set** in this repo's `.git/config`, so the hook runs for humans and (via the
  broker's commit) agents. The `gleipnir-git` broker cannot pass `--no-verify`;
  the operator can with their own `--no-verify`.
- The enforcement core is stdlib-only, Python `>=3.11`; tests run under
  `pytest` (`pyproject.toml`). The config-scan check itself is pure-Python over
  ~9 small markdown files + one jsonc file — **milliseconds**, no network, no DB.

## Proposed artifact

Two artifacts are proposed. Which subset to apply (A / B / C / D) is the
operator's convergence call — see Decision Analysis. Both are given **complete
and verbatim**, ready to apply.

### Artifact 1 — pre-commit config-scan step (Option A / part of C)

Appended to the **existing** `hooks/pre-commit`, mirroring its `GLEIPNIR_*`
opt-in idiom and `fail=0` accumulator exactly. It is **opt-in
(default-off)** via a new `GLEIPNIR_CONFIG_SCAN=1` toggle and **skips
gracefully** if the CLI/venv is unavailable, so it never breaks commits for a
contributor without the dev environment. (An always-on variant is discussed in
Decision Analysis tradeoff (2) — this artifact is the opt-in form, matching the
recommendation.)

**Path:** `hooks/pre-commit`

**Content (the block to insert immediately before the final `exit $fail`
line — everything else in the existing 46-line file is unchanged):**
```sh
# --- Config-scoping scan (OPT-IN) ---
# Runs the out-of-framework config-scan preflight over the agent roster +
# opencode.jsonc. A REFUSE (exit 1) blocks the commit. Opt-in and
# skip-if-absent: a contributor without the dev .venv is never blocked by a
# missing tool (the authoritative gate is CI, not this fast local check).
#   GLEIPNIR_CONFIG_SCAN=1         enable this step
#   GLEIPNIR_CONFIG_SCAN_STRICT=1  also fail on WARN findings (--strict)
if [ "${GLEIPNIR_CONFIG_SCAN:-}" = "1" ]; then
  repo_root=$(git rev-parse --show-toplevel)
  if [ -x "$repo_root/bin/gleipnir-preflight" ] && [ -x "$repo_root/.venv/bin/python" ]; then
    scan_args="config-scan"
    [ "${GLEIPNIR_CONFIG_SCAN_STRICT:-}" = "1" ] && scan_args="$scan_args --strict"
    # shellcheck disable=SC2086
    if ! "$repo_root/bin/gleipnir-preflight" $scan_args >&2; then
      echo "pre-commit: config-scan REFUSED — roster/opencode.jsonc mis-scoped." >&2
      echo "  (fix the finding above, or the operator may 'git commit --no-verify')" >&2
      fail=1
    fi
  else
    echo "pre-commit: GLEIPNIR_CONFIG_SCAN=1 set but bin/gleipnir-preflight or .venv missing — skipping (CI is authoritative)." >&2
  fi
fi
```

**Activation (operator, build mode / shell):**
```sh
# 1. Insert the block above into hooks/pre-commit, before `exit $fail`.
# 2. hooks/pre-commit is already +x and core.hooksPath=hooks is already set.
# 3. Turn the step on for this working copy:
git config --local --add hooks.dummy 0   # (no-op placeholder; not required)
export GLEIPNIR_CONFIG_SCAN=1            # per-shell, or add to the operator's env
# optional, promote WARN → block:
export GLEIPNIR_CONFIG_SCAN_STRICT=1
```
(No `chmod`/`core.hooksPath` step is needed — the file is already executable and
`core.hooksPath=hooks` is already configured, verified in `.git/config`.)

**Enforces / bypass semantics:** when `GLEIPNIR_CONFIG_SCAN=1`, every commit in
that working copy runs `config-scan`; a REFUSE (exit 1) sets `fail=1` and blocks
the commit. `--override-ack` is deliberately **not** wired into the hook (a
commit-time override belongs to the human via `--no-verify`, not an env flag).
A human bypasses with `git commit --no-verify` (their call); the `gleipnir-git`
broker cannot pass `--no-verify`, so an agent committing through the broker with
the toggle on always runs the scan. Default-off means teammates who never opt in
see zero behaviour change (the file's mere presence does nothing) — same
per-clone, per-person opt-in property documented for the existing hook.

**Honesty label:** **cooperative-policy-until-S-2.** `core.hooksPath`, the hook
file, and the env toggles are all operator-settable and not structurally locked
pre-S-2. The guarantee that the *agent* can't skip the step rests on the
broker's `--no-verify` refusal (real today). This is a **fast advisory floor at
commit time**, not a proof — CI is the authoritative gate.

### Artifact 2 — GitHub Actions CI gate (Option B / part of C)

The authoritative, environment-controlled gate. It runs `config-scan` on push
and PR and **fails the job on REFUSE (exit 1)**. It is **blocking by
construction** (a nonzero exit fails the check). This is the **first-ever CI
workflow** in the repo (see tradeoff (4)).

**Path:** `.github/workflows/config-scan.yml`

**Content (full, verbatim):**
```yaml
name: config-scan

# Authoritative config-scoping gate: runs the out-of-framework config-scan
# preflight over the agent roster (.gleipnir/agents/*.md) + opencode.jsonc.
# A REFUSE (exit 1) fails the job. This is the environment-controlled twin of
# the opt-in local pre-commit step; CI, not the local hook, is authoritative.

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  config-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Create venv (bin/gleipnir-preflight execs .venv/bin/python)
        run: |
          python -m venv .venv
          # Enforcement core is stdlib-only; no install needed for config-scan.

      - name: Run config-scan (REFUSE => exit 1 fails the job)
        run: |
          ./bin/gleipnir-preflight config-scan
          # To also fail on WARN findings, change the line above to:
          #   ./bin/gleipnir-preflight config-scan --strict
```

**Activation (operator):** commit `.github/workflows/config-scan.yml` to a
branch and open a PR / push to `main`; GitHub Actions runs it automatically. To
make it a **required** status check (so a REFUSE actually blocks merge, not just
reports red), the operator sets it as required in GitHub → Settings → Branches →
branch-protection for `main` (a platform-UI/admin action, outside every tier —
the agent cannot do this).

**Enforces / bypass semantics:** runs on every push to `main` and every PR;
`config-scan` exit 1 → step fails → job fails. It is **not bypassable by an
agent** (no roster role holds GitHub Actions admin or can edit branch
protection). The operator can bypass by not marking the check required, by
admin-merging, or by editing the workflow — all operator-level, as intended.
CI controls its own environment (it builds the `.venv`), so unlike the local
hook it never "skips because the venv is missing".

**Honesty label:** **cooperative-policy-until-S-2 for the config content**, but
CI is a genuinely stronger enforcement point than the local hook: it is
server-side, environment-controlled, and agent-unreachable. Its authority as a
*merge gate* depends on the operator marking it a **required** check — without
that it is advisory (reports status but does not block merge). The scan's own
findings are as sound as `config-scan`'s logic (fully unit-tested, fail-closed).

## Decision Analysis

Four material tradeoffs, surfaced for the operator to converge. This section
frames options + recommendation; it does **not** decide.

### Decision 1 — which wiring (A / B / C / D)?

**Type:** multi-option comparison → **Weighted Decision Matrix** (primary),
cross-checked against the Reversibility Filter.

**Reversibility Filter:** All four are **Two-Way Doors** — adding/removing a
hook step or a CI YAML is hours of reversible work, no data migration, no
external lock-in. Fast-track is permissible, but because this is a *safety*
control (a mis-scoped roster is the exact failure the framework prevents), the
matrix is still worth running.

Options:
- **(A)** pre-commit step only (fast, local, opt-in, bypassable, skip-if-absent).
- **(B)** CI only (authoritative, server-side, agent-unreachable, runs post-push).
- **(C)** both — fast local advisory + authoritative CI gate (defence in depth).
- **(D)** neither auto-wire — document `config-scan` as a manual/launch-time check.

| Criterion | Weight | A (hook) | B (CI) | C (both) | D (manual) |
|---|---|---|---|---|---|
| Catches defect before it lands | 9 | 7 → 63 | 8 → 72 | 9 → 81 | 2 → 18 |
| Agent cannot bypass | 8 | 6 → 48 | 9 → 72 | 9 → 72 | 1 → 8 |
| Fast feedback (pre-commit latency) | 5 | 9 → 45 | 4 → 20 | 9 → 45 | 3 → 15 |
| Low setup cost / appetite | 6 | 8 → 48 | 5 → 30 | 5 → 30 | 10 → 60 |
| No false-block for plain contributors | 6 | 8 → 48 | 7 → 42 | 7 → 42 | 10 → 60 |
| Authoritative (env-controlled) gate | 8 | 3 → 24 | 9 → 72 | 9 → 72 | 1 → 8 |
| **Total** | | **276** | **308** | **342** | **169** |

**Recommended: Option C (both).** Highest score, and it maps cleanly onto the
repo's *existing* two-layer pattern for the secret-scan story: a fast, opt-in
local floor (the pre-commit step) plus an authoritative, agent-unreachable gate
(CI). A alone leaves the authoritative gate empty and is agent-bypassable via
`--no-verify` at the human's discretion; B alone loses fast pre-commit feedback;
D leaves the safety invariant enforced by nothing but operator memory. **If
appetite for standing up first-ever CI is not there this session (tradeoff 4),
the fallback is A now + B when CI appetite exists** — A is a strict subset of C,
so nothing is wasted.

### Decision 2 — pre-commit step: always-on or opt-in default?

**Type:** binary → **Pros-Cons-Fixes**.

Precedent in the same file: **secret-scan is always-on** (a hard safety
invariant, cheap, low false-positive on added lines); **branch/data-file are
opt-in** (workflow preference). Where does a config-scoping check sit?

| Option | Pros | Cons | Fix |
|---|---|---|---|
| **Always-on** | Safety-invariant treatment; can never be forgotten | Requires `.venv`; a contributor without it would hit the skip-branch on *every* commit (noisy), or — if we didn't skip — a broken commit flow | Keep the skip-if-absent branch, but always-on makes the "skipping" message fire constantly for non-dev contributors; noise erodes signal |
| **Opt-in (default-off)** | No surprise for plain contributors; mirrors branch/data-file idiom; dev opts in with one env var | Must be remembered → in practice off unless enabled; the safety invariant then rests on CI | **CI (Artifact 2) is the always-on backstop** — so opt-in locally is safe *precisely because* CI is authoritative |

**Recommended: opt-in (default-off), `GLEIPNIR_CONFIG_SCAN=1`** — *conditional
on CI (Option B/C) being the authoritative backstop.* Rationale: unlike
secret-scan (pure-shell, zero deps, runs anywhere), config-scan needs the
`.venv`/CLI, so an always-on local step is either noisy (constant skip messages)
or fragile for contributors without the dev env. The safety guarantee is better
placed in CI, which controls its own environment. **If the operator chooses D
(no CI), reconsider: then the local step arguably *should* be always-on**, since
it would be the only automatic check — accept the contributor-noise cost as the
price of the invariant being enforced at all.

### Decision 3 — blocking or advisory (REFUSE fails vs warns only)?

**Type:** binary, safety-flavoured → **Pre-Mortem** on the blocking choice.

Assumed failure (6 months on, we chose *blocking* and regret it):

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | A false REFUSE blocks a legitimate commit/merge under deadline | Low–Med | Med | Human `--no-verify` locally; `--override-ack` exists for launch; CI check made non-required temporarily |
| 2 | `config-scan` bug refuses valid config | Low | Med | It is fully unit-tested + fail-closed by design; a bug is a code fix, not a reason to run advisory |
| 3 | Contributors resent a hard gate on first-ever CI | Low | Low | Introduce CI as non-required first (advisory), promote to required once trusted |

The scan is **fail-closed and unit-tested**; its FAIL findings are genuine
enforcement-config defects (fail-open namespace, single-holder violation,
malformed permission block). Letting those merge as a mere warning defeats the
purpose. **Recommended: blocking on FAIL** (REFUSE fails the commit/CI job),
with WARN findings **advisory by default** (do not fail unless `--strict`). This
matches `decide_config`'s own severity model (FAIL forces nonzero; WARN reported
but non-fatal unless `--strict`). For CI specifically, recommend introducing the
check as **non-required first**, then promoting to a required branch-protection
check once the operator has seen it run clean — de-risks the first-ever-CI
rollout (mitigation for failure mode 3).

### Decision 4 — if CI: confirm platform + first-ever-CI appetite

**Not a framework decision — a confirmation the operator must give.** Platform
is confirmed **GitHub** from the origin remote, so the artifact is GitHub
Actions (Artifact 2 as written). But standing up `.github/workflows/` is the
**first CI in this repo** — that is a scope/appetite question only the operator
can answer:
- Is standing up first-ever CI in appetite this session, or should it be a
  separate, deliberate piece of work?
- Should the CI check be **required** (blocks merge) from day one, or introduced
  **advisory/non-required** first and promoted later?

If appetite is not there now, the recommended fallback is **A now, B later**
(see Decision 1) — the local opt-in step delivers value immediately and CI is
added when first-ever-CI is a deliberate, in-appetite task.

### Bias check (12 detectors run; top 3 surfaced)

- ⚠️ **Status Quo Bias** — "nothing runs it today and things are fine" gives the
  do-nothing option (D) a free pass. Applied equal scrutiny: D scores lowest
  precisely because *fine* here means *the safety invariant is enforced by
  operator memory alone*. Would we choose "manual only" if starting fresh? No.
- ⚠️ **Scope Creep Bias** — recommending C (both) risks looking like "do
  everything to avoid choosing." Guarded against: C is recommended on the matrix
  *and* an explicit fallback (A-now-B-later) is given so the operator can bound
  scope to appetite. The choice is not being deferred by broadening it.
- ⚠️ **Availability Heuristic** — the existing secret-scan pattern is vivid and
  recent, tempting a reflexive "make config-scan always-on like secret-scan."
  Checked the base rate: config-scan differs materially (needs a `.venv`; not
  pure shell), which is exactly why Decision 2 recommends opt-in-local +
  always-on-CI rather than copying the secret-scan shape wholesale.

(No Sunk Cost, Anchoring, Confirmation, Bandwagon, Dunning-Kruger, IKEA,
Survivorship, Recency, or Authority trigger materially here — the tool is
already built and tested, so the decision is purely *where to wire it*, and the
recommendation follows the matrix, not a pre-existing preference.)

### Recommendation (advisory — for the operator to converge)

- **Wiring:** **C (both)** — opt-in pre-commit step + GitHub Actions CI gate.
  **Fallback if first-ever-CI is out of appetite:** A now, B later.
- **Pre-commit default:** **opt-in** (`GLEIPNIR_CONFIG_SCAN=1`), *because CI is
  the always-on backstop*. If no CI (D), make the local step always-on instead.
- **Blocking:** **block on FAIL** (REFUSE fails commit/CI); WARN advisory unless
  `--strict`. Introduce the CI check **non-required first**, promote to required
  once seen clean.
- **Platform/appetite:** confirmed GitHub; operator must confirm first-ever-CI
  appetite and required-vs-advisory rollout.

## Handoff

These are **substrate/VCS and CI/platform controls; the agent cannot and should
not write them** — routing them into a reachable layer to avoid this handoff is
the exact `tier3-coach` anti-pattern this proposal refuses.

To apply, once the operator has converged the four tradeoffs above:
1. **Switch to build** and insert the Artifact-1 block into `hooks/pre-commit`
   before its `exit $fail` line (file is already +x; `core.hooksPath=hooks` is
   already set). Enable per working copy with `export GLEIPNIR_CONFIG_SCAN=1`.
2. **Switch to build** and create `.github/workflows/config-scan.yml` with
   Artifact 2 verbatim; commit it. Then, in the GitHub branch-protection UI
   (operator/platform action — no agent), mark the `config-scan` check
   **required** on `main` if/when the operator wants it to gate merges.
3. Neither step is agent-bypassable: the `gleipnir-git` broker cannot pass
   `--no-verify` (binds the local hook for agents), and no roster role holds
   GitHub Actions admin (binds CI for agents). The operator retains bypass
   (`--no-verify`, admin-merge, non-required check) by design.

Do not implement here. This brief is the proposal; the orchestrator surfaces the
four tradeoffs to the operator; the operator (or a bounded build role for the
in-repo files) applies the converged subset.
