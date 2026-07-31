# Plan: Git-enforcement — layered plugin config-scan + broker secret-scan (Approach C)

**Stage:** plan. **Status:** WRITTEN from the operator-converged brief
(`.gleipnir/plans/git-enforcement-plugin-brainstorm.md`). This plan does NOT
re-decide the mechanism (Approach C) or the drift-fix — both are
operator-converged. It resolves the three NON-material plan-level tradeoffs
(a)(b)(c), makes a plan-level recommendation on the fate of `hooks/pre-commit`,
and specifies the work test-first. **Author:** gleipnir-plan.

**Convergence citation:** operator converged on Approach C (layered) via the
orchestrator, and on the mandatory `broker-mcp.md` drift-fix (brief Pre-Mortem
#4). See the brief's "Recommendation" + the delegation instruction.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Enforcement mechanism | **C (layered):** config-scan in a new plugin at `tool.execute.before`; secret-scan server-side in the broker `commit_changes` | A (pure plugin); B (pure broker) | **OPERATOR-CONVERGED.** Each check runs where its inputs are visible: config-scan needs only files on disk (plugin-friendly); secret-scan needs the staged diff (broker-friendly, post-stage). Closes A's false-CLOSED risk + the ground-truth #2 drift |
| D2 | Fix the `broker-mcp.md` drift (line ~34 false claim) | **Amend the record** to state the truth after this change; note the prior false claim | Leave as-is | **OPERATOR-CONVERGED (mandatory, Pre-Mortem #4).** The record currently claims `commit_changes` runs `precommit_check`; the code runs a plain `git commit`. After this change the broker WILL run the secret-scan, so the record must reflect that + flag its prior falseness. Tier-3, operator-authored |
| D3 (a) | Which git tool calls to gate | config-scan on **BOTH** `gleipnir-git_commit_changes` AND `gleipnir-git_push_current_branch`; secret-scan on **commit** only | commit-only for both; push-only | **PLAN-LEVEL** (brief advisory, Two-Way Door). Don't commit *or* push while the agent/permission config is mis-scoped (config integrity is repo-wide, diff-independent). Secrets enter history at commit, so the secret-scan belongs there; a push of already-committed content is too late to secret-gate meaningfully |
| D4 (b) | How the plugin invokes the Python scan | **Shell out** to `bin/gleipnir-preflight config-scan`, resolving the CLI path from the plugin `directory` param (mirror sequence-gate's bridge-path resolution); **fail-CLOSED on any invocation error** | Reimplement the scan in TypeScript | **PLAN-LEVEL** (brief advisory, near-one-way door). Single source of truth, stdlib-only enforcement core preserved, no TS drift. Fail-closed-on-error mirrors sequence-gate: a scan that can't run must not silently pass |
| D5 (c) | Plugin exit-code handling | **0=CLOSED→pass; 1=REFUSE→throw/abort; 2=PROCEED_UNCLOSED→warn-and-proceed** | Treat 2 as a hard block; treat any nonzero uniformly | **PLAN-LEVEL** (brief advisory). Matches the config-scan CLI's own 0/1/2 contract (`config_scan.py` `config_scan_main`, verified). Exit-2 is the operator-override "proceed unclosed" path — warn, don't deadlock an L2/L3 operator |
| D6 | Broker secret-scan scope | **Safety-only, always-on secret-scan** (`scan_diff_for_secrets` via `precommit_check`); keep branch/data-file **opt-in** as today | Wire ALL of `precommit_check`'s checks as always-on | **PLAN-LEVEL** (brief Pre-Mortem #2). Always-on branch/data-file refusal would re-create the L2/L3 deadlock the guard lineage deliberately removed. `precommit_check` is ALREADY scoped this way (`guards.py`: secret-scan always-on; branch/data-file gated by env) — wiring it in as-is preserves that |
| D7 | Fate of `hooks/pre-commit` | **KEEP as a human-facing convenience** (default-on secret-scan, opt-in branch/data-file), unchanged except a header note | Retire it; replace it | **PLAN-LEVEL RECOMMENDATION** (brief advisory; judged NON-material — see "Hook-fate analysis"). It imposes nothing extra (already opt-in via `core.hooksPath`), and covers HUMAN terminal commits that neither the broker nor the plugin touch. A header note records that framework/agent enforcement now lives in the broker+plugin |
| D8 | Broker test profile | New broker-invocation tests run under the **broker profile** (`gleipnir-sandbox-broker`), collect-ignored under the python profile | Add `mcp` to the default image | **PLAN-LEVEL.** `commit_changes` lives in `mcp_server.py` which imports `mcp` (FastMCP). Mirrors `test_broker_tool_surface.py`'s existing profile split (`conftest.py` `collect_ignore`) so the lean image is unchanged |
| D9 | Plugin arming posture | **ALWAYS-ACTIVE** whenever the plugin is loaded — the config-scan gate fires on every agent git commit/push in every session; a REFUSE (exit 1) aborts the git op, an exit-2 PROCEED_UNCLOSED (`--override-ack`) warns-and-proceeds as the operator's deliberate escape valve. Does NOT gate on `GLEIPNIR_PIPELINE`/bridge-file existence | Armed-only (mirror sequence-gate's default-OFF, active only when a pipeline is armed) | **OPERATOR-CONVERGED.** Config integrity is a safety invariant that matters regardless of pipeline arming (a mis-scoped agent/permission config is dangerous whether or not a pipeline is running), so the guard cannot be a no-op-unless-armed like sequence-gate. Exit-2 is the release valve, so always-active never deadlocks an L2/L3 operator |

---

## Architect

**Problem (one sentence):** Move git-enforcement OFF the VCS hook layer (which
forces behaviour on every human/clone) and INTO the framework's own agent
surface — a Tier-3 opencode plugin runs the config-scan before any broker git
tool call, and the broker itself runs the always-on secret-scan post-stage
pre-commit — while fixing the `broker-mcp.md` record that falsely claims the
broker already does this.

**User:** the operator (authors the Tier-3 plugin + record + any hook change)
and, transitively, every framework agent run whose git operations are now
gated inside the agent workflow rather than by a repo-imposed hook.

**Measurable success criteria:**
1. A broker `commit_changes` whose staged diff contains a planted secret is
   **REFUSED** (no commit created; HEAD unchanged), with a redacted finding —
   proven by a failing-then-passing test that drives the real tool function
   against a temp git repo.
2. A broker `commit_changes` on a clean staged diff **succeeds** (commit created)
   — no false-positive deadlock; branch/data-file checks stay opt-in (default off).
3. The plugin `git-guard.ts`, keyed on `gleipnir-git_commit_changes` and
   `gleipnir-git_push_current_branch`, shells out to `bin/gleipnir-preflight
   config-scan`, and: passes on exit 0, THROWS (aborts the tool call) on exit 1,
   warns-and-proceeds on exit 2, and **fails CLOSED (throws)** on any invocation
   error — proven by a golden-fixture test mirroring `test_sequence_gate.mjs`.
4. `.gleipnir/decisions/broker-mcp.md` (~line 34) states the TRUE post-change
   behaviour AND notes the prior false claim; AND every false "the broker
   already gates commits" claim in `mcp_server.py` — the module docstring, the
   `commit_changes` docstring, AND the agent-facing `FastMCP(instructions=...)`
   string — is corrected to state the post-change truth (always-on secret-scan;
   protected-branch/data-file opt-in).
5. Every artifact's trust tier is stated; agent-writable-vs-operator-writable is
   explicit; the cooperative-policy-until-S-2 honesty label is present.

**Constraints (inherited from the brief, all verified against source):**
- Enforcement must NOT live in a `pre-commit` hook *as the framework's
  enforcement seat*, and NOT in CI. (The hook survives only as opt-in human
  convenience — D7.)
- Reuse existing Python logic: `guards.precommit_check` /
  `scan_diff_for_secrets` (secret-scan); `bin/gleipnir-preflight config-scan`
  (config-scan, exit 0/1/2). No TS reimplementation. **Verified in source.**
- stdlib-only enforcement core preserved (shell-out, not reimpl).
- Honesty label: pre-S-2 both the plugin seat (`.gleipnir/plugins/**`) and the
  broker source (`src/gleipnir/broker/**`) are agent-*writable*; this is
  cooperative-policy, not a hard boundary, until the S-2 mount + G-1 preflight.
- The broker already structurally refuses hook-bypass (`--no-verify` / `-n` /
  `-c core.hooksPath`) at `_run_git`. **Verified** (`mcp_server.py` L75-113).

---

## Trace

### Artifacts, where they live, source of truth, and TRUST TIER

| Artifact | Path | Status | Tier / Writer |
|---|---|---|---|
| New plugin | `.gleipnir/plugins/git-guard.ts` | **to be created** | **TIER-3 — OPERATOR writes.** No roster agent (incl. gleipnir-code) may write it; it is the guard (Axiom 2 / G-1) |
| Plugin golden-fixture test | `tests/test_git_guard.mjs` | **to be created** | Test — gleipnir-code MAY write. (Tests live in `tests/`, not under `.gleipnir/`.) |
| Broker source change | `src/gleipnir/broker/git/mcp_server.py` (`commit_changes` wire-in **+ the module docstring, `commit_changes` docstring, and the agent-facing `FastMCP(instructions=...)` string — all part of the D2 drift-fix**) | **edit existing** | Code — **gleipnir-code writes**. (Under `src/`, not a Tier-3 path. The `instructions=` string is agent-facing MCP metadata but is source code, so it is a code-stage edit, not operator/Tier-3.) |
| **Sandbox profile config** | `.gleipnir/sandbox/profiles.toml` (`default_profile` + `[profile.broker].test`) | **amend existing** | **TIER-3 — OPERATOR writes.** REQUIRED for the broker commit-guard test to run: today `default_profile="python"` and `[profile.broker].test` is a hardcoded four-file argv NOT including `tests/test_broker_git_commit_guard.py`, and the CLI has no `--profile` flag and refuses extra selectors on this profile (`test_selector_prefix=false`). The operator must (1) select the broker profile for the run via `default_profile` and (2) append the new test to `[profile.broker].test`. **Named here so the build does not stall.** Verified against source this pass |
| Broker guard logic | `src/gleipnir/broker/git/guards.py` (`precommit_check`, `scan_diff_for_secrets`) | **reuse, unchanged** | Code — no edit needed; already correct + 96% covered |
| Broker commit-guard test | `tests/test_broker_git_commit_guard.py` | **to be created** | Test — gleipnir-code MAY write. Runs under the **broker profile** (imports `mcp`) |
| Decision record | `.gleipnir/decisions/broker-mcp.md` (~line 34) | **amend existing** | **TIER-3 — OPERATOR writes.** Durable decision record |
| Existing hook | `hooks/pre-commit` | **keep; optional header note** | Substrate/VCS — **OPERATOR writes.** Not agent-reachable |
| Config-scan CLI | `bin/gleipnir-preflight config-scan` → `src/gleipnir/preflight/config_scan.py` | **reuse, unchanged** | Existing; invoked by the plugin, not modified |

**No new preflight subcommand is required.** Unlike Approach A (which would have
needed a new `secret-scan`/`commit-scan` subcommand for the plugin to scan a
staged diff), Approach C puts the secret-scan in the broker where
`guards.precommit_check` already exists. The plugin only invokes the
**existing** `config-scan` subcommand. This removes the brief's "possibly 1 new
thin preflight subcommand" from scope.

### Integrations map

```
 opencode (Node process, host cwd)
   └─ tool.execute.before  ── git-guard.ts (TIER-3 plugin) ─┐
        keyed on:                                           │ shell out
          gleipnir-git_commit_changes                       ▼
          gleipnir-git_push_current_branch      bin/gleipnir-preflight config-scan
                                                   (exit 0=pass / 1=throw / 2=warn)
                                                   scans .gleipnir/agents/** + opencode.jsonc
   └─ MCP tool call ── gleipnir-git broker (src/gleipnir/broker/git/mcp_server.py)
        commit_changes:
          1. git add (files | -A)              ← stages first (as today)
          2. git diff --cached                 ← NEW: capture staged diff
          3. guards.precommit_check(branch, diff, staged_files)  ← NEW wire-in
          4. if not passed → git reset HEAD; return refusal      ← NEW
          5. git commit -m message             ← unchanged (still fires any human hook)
```

**Ordering invariant (critical):** the secret-scan must run **after `git add`
and before `git commit`** — that is the only window where `git diff --cached`
reflects exactly what will be committed. Today `commit_changes` stages then
commits with nothing in between: the staging block is `mcp_server.py` **L272-292**
and the `git commit` call is **L294** (verified this pass). The wire-in inserts
steps 2-4 between the staging block (ending L292) and the `git commit` call
(L294).

### Edge cases

1. **Nothing staged / empty diff** → `scan_diff_for_secrets("")` returns `[]` →
   `precommit_check` passes → commit proceeds (an empty commit is git's own
   concern, not a secret-scan concern).
2. **`git diff --cached` itself fails** (e.g. not a git repo) → treat as a
   broker error and return `{"success": false, ...}` WITHOUT committing
   (fail-closed: never commit when the scan could not run). Do NOT fall through
   to `git commit`.
3. **`reset HEAD` on refusal** → after a secret finding, run a bare `git reset
   HEAD` (mixed reset, no pathspec) to unstage. **Precise scope:** a bare
   `git reset HEAD` unstages ALL currently-staged content, not only the files
   this `commit_changes` call staged — so if the agent had pre-staged other
   content BEFORE calling the broker, that content is unstaged too. Working-tree
   contents are NOT touched (no `--hard`): every file remains on disk with its
   changes intact; nothing is lost (L-C11-safe), only the staging index is
   cleared. This is acceptable because the broker's contract is to refuse the
   commit cleanly, and re-staging is a cheap, non-destructive follow-up; but the
   plan does NOT claim it "leaves the tree exactly as the agent found it" — the
   staging state may differ (pre-staged content becomes unstaged). Matches the
   record's "reset HEAD on refusal" intent (which this change makes true), with
   this unstage-scope caveat made explicit. (If narrower unstage scope is ever
   wanted, `git reset HEAD -- <this-call's-files>` would scope it to just the
   files this call staged — noted as a possible future refinement, NOT specified
   here, since the always-on scope is secret-scan safety, not staging hygiene.)
4. **False-positive avoidance** → secret-scan only (`_COMPILED_PATTERNS`);
   branch/data-file remain env-gated in `precommit_check`, so a trunk-based /
   L2/L3 operator is never refused on branch alone (no deadlock — Pre-Mortem #2).
5. **Commit message that mentions a secret pattern in prose** → only `+`-added
   *diff content* lines are scanned (`scan_diff_for_secrets` skips `+++`/`---`/
   `diff --git`/`@@`/context). The commit message is not part of the staged diff,
   so it is never scanned. (Distinct from the `_rejects_hook_bypass` message-skip
   logic, which is unrelated and unchanged.)
6. **Plugin: config-scan CLI missing / `.venv` absent / nonzero-but-not-0/1/2**
   → fail CLOSED (throw), mirroring sequence-gate's catch-all `GateAbort`.
7. **Plugin fires for a non-git tool** → early `return` (no-op), exactly like
   sequence-gate's `if (input.tool !== "task") return`.
8. **Plugin arming posture (OPERATOR-CONVERGED — D9)** → the config-scan gate is
   **ALWAYS-ACTIVE** for the two git tools whenever the plugin is loaded (unlike
   sequence-gate, which is default-OFF and a no-op unless a pipeline is armed),
   because config integrity is a safety invariant, not a pipeline-run concern.
   The plugin does **NOT** gate on `GLEIPNIR_PIPELINE`/bridge-file existence —
   it fires in every session, arming env var set or not. The exit-2
   PROCEED_UNCLOSED (`--override-ack`) warn-and-proceed is the operator's
   deliberate escape valve (so always-active never deadlocks an L2/L3 operator).

---

## Link — validated before building

- **`sequence-gate.ts` pattern confirmed** (re-read): `tool.execute.before`,
  `input.tool` guard, `directory` param for path resolution, `throw`-to-abort,
  catch-all fail-closed. `git-guard.ts` mirrors this exactly, keyed on the two
  git tool names instead of `task`.
- **`test_sequence_gate.mjs` pattern confirmed** (re-read): golden-fixture +
  temp-dir driving of the real hook, `assert.rejects` for the throw path.
  `test_git_guard.mjs` mirrors this: golden fixtures for exit 0/1/2 + a
  fail-closed-on-missing-CLI case.
- **`guards.precommit_check` confirmed** (re-read): already secret-scan-always-on,
  branch/data-file opt-in; returns `{passed, secrets, error, ...}`. No change
  needed to `guards.py` — only the wire-in in `mcp_server.py`.
- **Config-scan CLI exit contract confirmed** (`config_scan.py` `config_scan_main`
  + `__main__.py` dispatch, re-read): `config-scan` is a subcommand of
  `bin/gleipnir-preflight`; returns 0=CLOSED, 2=PROCEED_UNCLOSED, 1=REFUSE.
- **Broker test profile confirmed**: `test_broker_tool_surface.py` imports `mcp`
  and runs under the broker profile via `conftest.py` `collect_ignore`. The new
  commit-guard test follows the same path (it must import `mcp_server`, which
  imports `mcp`).
- **`bin/gleipnir-preflight` path resolution confirmed**: it is a thin shim
  execing `$repo/.venv/bin/python -m gleipnir.preflight`. The plugin resolves it
  as `join(directory, "bin/gleipnir-preflight")` — `directory` is the host repo
  root (same param sequence-gate uses for `BRIDGE_REL`).

---

## Assemble — intended build order

**Test-first for the broker code; operator applies Tier-3 artifacts.**

0. **[OPERATOR, Tier-3] Amend `.gleipnir/sandbox/profiles.toml` so the broker
   commit-guard test can run.** This is a HARD PRECONDITION for steps 1 and 3 to
   exercise the new test under the broker image — without it the test is never
   collected by `bin/gleipnir-sandbox test` (there is no `--profile` flag; the
   profile comes from `default_profile`, and `[profile.broker].test` is a
   hardcoded argv with `test_selector_prefix=false`). Two edits: (i) append
   `"tests/test_broker_git_commit_guard.py"` to `[profile.broker].test`; (ii)
   select the broker profile for the broker test run via `default_profile`
   (set `"broker"` for the run, restore `"python"` after — this is the only lever
   the shipped CLI exposes). Tier-3, operator-authored; named in the Trace tier
   table. gleipnir-code and gleipnir-plan may NOT write this file.
1. **[gleipnir-code] Write the FAILING broker commit-guard tests** —
   `tests/test_broker_git_commit_guard.py` (broker profile; needs the step-0
   profile amendment to be collected). See the explicit test list in Stress-test
   T1-T5. These fail because `commit_changes` does not yet run the scan. Also add
   the test to `conftest.py` `collect_ignore` for the python profile alongside
   `test_broker_tool_surface.py` (it imports `mcp`).
2. **[gleipnir-code] Implement the broker wire-in** — edit `commit_changes` in
   `src/gleipnir/broker/git/mcp_server.py`: after staging, `git diff --cached`,
   call `guards.precommit_check(branch, diff, staged_files)`, on `not passed`
   run `git reset HEAD` and return the refusal (with redacted findings from the
   result), else proceed to the existing `git commit`. Update ALL agent-facing
   and human-facing metadata in the file to state the truth after the change
   (this is part of the D2 drift-fix scope — see "Broker source truth-fixes"
   below): (a) the module docstring (L1-27) + the write-tools section comment
   (L237-250) which currently say "imposes NO commit policy of its own"; (b) the
   `commit_changes` docstring (L255-268) which says it "runs a plain `git
   commit`"; AND (c) the `FastMCP(..., instructions=...)` string (L41-47), which
   is AGENT-FACING MCP metadata and today makes a FALSE claim. Tests from step 1
   now pass.
3. **[gleipnir-code] Run the broker profile suite** — confirm green under
   `gleipnir-sandbox-broker`; confirm no regression under the python profile
   (the new test is collect-ignored there).
4. **[OPERATOR] Write the Tier-3 plugin** `.gleipnir/plugins/git-guard.ts` per
   the "Plugin design specification" below. gleipnir-code MAY write the
   accompanying `tests/test_git_guard.mjs` + golden fixtures (tests are not
   Tier-3), but the `.ts` plugin file itself is operator-authored.
5. **[OPERATOR] Amend `.gleipnir/decisions/broker-mcp.md`** (~line 34) per the
   "Record amendment specification" below. Tier-3.
6. **[OPERATOR, optional] Add a header note to `hooks/pre-commit`** recording
   that framework/agent enforcement moved to the broker + plugin, and this hook
   is now a human-facing convenience only. No logic change (D7).
7. **[gleipnir-code] Run `tests/test_git_guard.mjs`** (Node) once the operator's
   plugin is in place — confirm the golden-fixture cross-language behaviour.

**What gleipnir-code CAN implement:** steps 1-3, 7, and the test/fixtures in
step 4 (broker source + all tests). **What only the OPERATOR can apply:** the
Tier-3 `profiles.toml` amendment (step 0), the Tier-3 `.ts` plugin file (step 4),
the Tier-3 record amendment (step 5), and the substrate hook note (step 6).

---

## Plugin design specification (so the operator can write `git-guard.ts`)

Mirror `sequence-gate.ts` structure. TIER-3 header comment must state:
operator-authored, agent-unwritable, cooperative-policy-until-S-2.

**Tool-name keys (D3a):**
```ts
const GATED_TOOLS = new Set([
  "gleipnir-git_commit_changes",
  "gleipnir-git_push_current_branch",
])
```
In `tool.execute.before`: `if (!GATED_TOOLS.has(input.tool)) return`.

**Always-active — NO arming gate (D9, OPERATOR-CONVERGED):** unlike
`sequence-gate.ts`, which no-ops unless a pipeline is armed (it checks
`GLEIPNIR_PIPELINE` / the bridge file's existence), `git-guard.ts` has **no such
check**. Once loaded it gates every `gleipnir-git_commit_changes` /
`gleipnir-git_push_current_branch` call in every session, whether or not any
pipeline/arming env var is set. Do NOT copy sequence-gate's arming/bridge-file
guard into this plugin. The only early `return` is the non-gated-tool
pass-through above; config integrity is a safety invariant that holds regardless
of pipeline state, and exit-2 (below) is the operator's release valve.

**Shell-out + path resolution (D4b):** resolve the CLI from `directory` exactly
as sequence-gate resolves `BRIDGE_REL`:
```ts
const CLI_REL = "bin/gleipnir-preflight"
const cli = join(directory, CLI_REL)
// spawn synchronously; capture exit code. Use node:child_process spawnSync.
const res = spawnSync(cli, ["config-scan"], { cwd: directory, encoding: "utf8" })
```

**Exit-code handling (D5c):**
```ts
if (res.error || res.status === null) {
  throw new GitGuardAbort(`git-guard: config-scan could not run (${res.error}); fail-closed`)
}
switch (res.status) {
  case 0: return                    // CLOSED → allow the git tool call
  case 2:                            // PROCEED_UNCLOSED → warn, do not block
    console.warn(`git-guard: config scan PROCEED_UNCLOSED (exit 2); proceeding. ${res.stderr}`)
    return
  case 1:                            // REFUSE → abort the git tool call
    throw new GitGuardAbort(`git-guard: config scan REFUSED (exit 1). ${res.stderr}`)
  default:                           // any other code → fail-closed
    throw new GitGuardAbort(`git-guard: config scan unexpected exit ${res.status}; fail-closed. ${res.stderr}`)
}
```

**Fail-closed-on-error (D4b):** wrap the body in `try/catch` with a catch-all
that re-throws (mirror sequence-gate L219-226): any stray exception aborts the
tool call, never silently allows it. `GitGuardAbort extends Error`.

**Exported pure helper for testing:** factor the exit-code→action decision into
an exported pure function, e.g.
`export function decideFromExit(status: number | null, error?: unknown): "allow" | "warn" | "abort"`,
so `test_git_guard.mjs` can assert the 0/1/2/error mapping without spawning a
subprocess — the same pattern sequence-gate uses by exporting `validateMarker` /
`isDelegationAllowed` as pure, test-only surfaces.

**Golden-fixture test approach (`tests/test_git_guard.mjs`, mirrors
`test_sequence_gate.mjs`):**
- Import `decideFromExit` (pure) and assert: `0→"allow"`, `1→"abort"`,
  `2→"warn"`, `99→"abort"`, `null→"abort"`.
- Drive the real `GitGuard({directory})["tool.execute.before"]` against a temp
  directory containing a **stub `bin/gleipnir-preflight`** shell script whose
  exit code the test controls (write a 1-line `#!/bin/sh; exit N` script,
  `chmod +x`), and assert: exit-0 stub → resolves (no throw); exit-1 stub →
  `assert.rejects`; missing CLI → `assert.rejects` (fail-closed). This is the
  golden-fixture analogue: the stub CLI is the fixture, exactly as
  `golden_marker.json` is sequence-gate's fixture.
- Assert a non-git tool name is a pass-through (no throw, no spawn).

---

## Record amendment specification (so the operator can amend `broker-mcp.md`)

The false claim at **line ~34** currently reads:

> `commit_changes` evaluates `guards.precommit_check` and refuses BEFORE
> constructing any commit argv (`reset HEAD` on refusal).

**After this change it must state the truth**, and note the prior falseness.
Suggested replacement prose (operator's wording, this is the intent):

> `commit_changes` stages files, then runs the always-on **secret-scan**
> (`guards.precommit_check`, secret-scan portion) over the staged diff
> (`git diff --cached`) and refuses with `git reset HEAD` on a secret finding,
> BEFORE the `git commit`. **Correction (was drift):** an earlier version of
> this record claimed this behaviour already existed; it did not — until
> `.gleipnir/plans/git-enforcement-plugin.md` wired it in, `commit_changes` ran
> a plain `git commit` and the secret-scan reached agent commits only via the
> installed `hooks/pre-commit`. Branch/data-file checks remain opt-in
> (unchanged). The config-scan runs separately in the `git-guard.ts` plugin at
> `tool.execute.before` (not in the broker).

## Broker source truth-fixes (D2 drift-fix scope, code stage) — so `mcp_server.py` metadata states the truth

The D2 drift-fix is NOT limited to `broker-mcp.md`. The same false "the broker
already gates commits" claim survives in THREE places inside
`src/gleipnir/broker/git/mcp_server.py`, all of which gleipnir-code fixes in
step 2 (this is a **code-stage** edit under `src/`, NOT a Tier-3 path — see the
Trace tier table: this file is "Code — gleipnir-code writes"):

1. **Module docstring (L1-27) + write-tools section comment (L237-250)** —
   currently "The broker imposes NO commit policy of its own … `commit_changes`
   runs a plain `git commit`." After the change this is true ONLY for the
   *opt-in* branch/data-file checks; the always-on **secret-scan** is now broker
   policy. Reword to: the broker runs an always-on secret-scan over the staged
   diff before committing (refuse + `git reset HEAD` on a finding); branch and
   data-file checks remain opt-in and, like before, are otherwise the operator's
   hooks' job; the hook-bypass structural refusal at `_run_git` is unchanged.

2. **`commit_changes` docstring (L255-268)** — currently "Runs a plain `git
   commit`." Reword to state it stages, runs the always-on secret-scan over
   `git diff --cached`, refuses with `git reset HEAD` on a secret finding, and
   only then commits.

3. **`FastMCP(..., instructions=...)` string (L41-47)** — this is **agent-facing
   MCP metadata** (the model reads it to understand the tool). It currently
   claims, FALSELY today and still PARTLY falsely after this change:

   > commit_changes stages and commits with a structural pre-commit gate
   > (protected-branch refusal + secret-scan + data-file check).

   It is false today (no gate runs at all) and would be false even after this
   change if left as-is, because per D6 protected-branch and data-file stay
   **opt-in**, not always-on. Fix it to state the post-change truth precisely:
   `commit_changes` stages, runs an **always-on secret-scan** over the staged
   diff and refuses on a finding, then commits; **protected-branch and data-file
   checks are opt-in** (off unless the operator enables them via env); no
   force-push path exists anywhere in this server. (Command 9 in the Stress-test
   verification sweep confirms the old false substring is gone.)

Verified this pass (L-C15): the false `instructions=` substring is present at
`mcp_server.py` L41-47; the "imposes NO commit policy" claims are at L6-8 and
L240-242; the "plain `git commit`" claim is at L257-261.

---

## Hook-fate analysis (D7) — judged NON-material; recommendation stands

The delegation asks me to STOP and flag hook-fate to the operator IF it is
genuinely material (a real either/or with lasting consequence). **I judge it
NON-material** and therefore make a plan-level recommendation. Reasoning:

- **Reversibility:** keep/retire the hook is a Two-Way Door — reverting is a
  one-line file change with no downstream code dependency (the brief's own
  Reversibility Filter classifies it Two-Way).
- **No lasting consequence either way:** the hook does not gate any agent path
  once the broker runs the secret-scan (agent commits are covered by the broker
  regardless of the hook). Its ONLY remaining audience is HUMAN terminal
  commits, which neither the broker nor the plugin touch. Keeping it costs
  nothing (it is opt-in via `core.hooksPath`, imposes nothing on clones/users),
  and removing it only *loses* the human-commit secret-scan convenience.
- **No principle conflict:** keeping an opt-in human convenience does not
  violate the operator's "don't force onto users" principle — `core.hooksPath`
  is the operator's own choice, never imposed on a clone.

Because both the cost of keeping and the cost of the wrong choice are ~zero, and
because it is trivially reversible, this is not a decision-frameworks-flag
tradeoff. **Recommendation: KEEP `hooks/pre-commit`** as a human-facing
convenience (default-on secret-scan, opt-in branch/data-file), with only an
optional header note that framework/agent enforcement now lives in the
broker + plugin. If the operator disagrees, retiring it is a one-line follow-up.

---

## Stress-test — acceptance checks

### Broker commit-guard tests (test-first, `tests/test_broker_git_commit_guard.py`, broker profile)

These are the FAILING tests gleipnir-code writes BEFORE the wire-in. They drive
the real `commit_changes` function against a temp git repo (create with
`git init`, configure `user.email`/`user.name`, write files, call the tool
function directly — it returns a JSON string).

- **T1 — refuses on a secret in the staged diff.** Stage a file whose added
  content contains a planted `AKIA`-shaped key (reuse the `AKIA_SECRET` shape
  from `test_broker_git_guards.py`: `"AKIA" + "Q7X9"*4`). Call `commit_changes`.
  Assert: returned JSON `success=false`; error names a secret finding; the
  finding's `match` is **redacted** (the full secret does not appear verbatim in
  the returned string); **`git rev-parse HEAD` is unchanged** (no commit created).
- **T2 — passes on a clean staged diff.** Stage a benign file. Call
  `commit_changes`. Assert: `success=true`; a new commit exists (HEAD advanced);
  the returned `hash` matches `git rev-parse HEAD`.
- **T3 — reset-HEAD-on-refusal unstages (no working-tree loss).** After the
   T1 refusal, assert the secret file still exists on disk AND is no longer staged
   (`git diff --cached --name-only` does not list it; `git status --porcelain`
   shows it as unstaged/untracked). Proves the mixed `git reset HEAD` semantics
   (index cleared, working tree intact — L-C11-safe). **Also assert the
   all-staged scope precisely:** pre-stage a SECOND benign file before calling
   `commit_changes`, then after the refusal assert that second file is ALSO
   unstaged — documenting that a bare `git reset HEAD` clears the WHOLE index,
   not just this call's staging (edge case 3). This makes the caveat a tested
   fact, not just prose.
- **T4 — no false-positive deadlock (safety-only scope).** On a clean diff while
  on `main` with NO `GLEIPNIR_GIT_PROTECT_BRANCHES` set, `commit_changes`
  **succeeds** (branch protection stays opt-in; committing to main is not
  refused). And with `GLEIPNIR_GIT_CHECK_DATA_FILES` unset, staging a `.sqlite`
  file with clean content **succeeds** (data-file check stays opt-in). This is
  the Pre-Mortem #2 guard: always-on scope is secret-scan only.
- **T5 — scan runs post-stage, pre-commit (ordering).** With a secret staged,
  assert the refusal happens with HEAD unchanged (as T1) AND the working file is
  present — i.e. the scan saw the staged content (`git diff --cached`), proving
  the scan is wired between `git add` and `git commit`, not before staging (which
  would scan nothing → false-CLOSED, the worst failure the brief names).

### Plugin golden-fixture tests (`tests/test_git_guard.mjs`, Node)

- **T6 — exit-code decision mapping (pure).** `decideFromExit`: `0→allow`,
  `1→abort`, `2→warn`, `99→abort`, `null→abort`.
- **T7 — exit-0 stub CLI → tool call proceeds** (no throw) for both gated tool
  names.
- **T8 — exit-1 stub CLI → `assert.rejects`** (throw-to-abort) for
  `gleipnir-git_commit_changes`.
- **T9 — exit-2 stub CLI → proceeds with a warning** (no throw).
- **T10 — missing CLI → `assert.rejects`** (fail-closed on invocation error).
- **T11 — non-git tool name → pass-through** (no throw, no spawn).
- **T12 — (a) REFUSE (exit 1) ABORTS the git tool call.** With an exit-1 stub
  CLI, driving `GitGuard({directory})["tool.execute.before"]` for
  `gleipnir-git_commit_changes` → `assert.rejects` (the git op is aborted, not
  allowed). This is the D9 REFUSE contract — a REFUSE must stop the commit/push.
- **T13 — (b) exit-2 PROCEED_UNCLOSED WARNS but does NOT abort.** With an exit-2
  stub CLI, the same driver call **resolves** (no throw) — asserting the git op
  proceeds — while a warning is emitted (assert `console.warn` was called, e.g.
  via a spy/capture). Proves exit-2 is the operator escape valve: warn-and-proceed,
  never a hard block.
- **T14 — (c) the plugin is ACTIVE with NO arming env var set.** With **no**
  `GLEIPNIR_PIPELINE` (and no bridge file) in the environment, an exit-1 stub CLI
  still causes `assert.rejects` for a gated tool — proving `git-guard.ts` gates
  unconditionally when loaded and, unlike `test_sequence_gate.mjs`'s armed/unarmed
  split, has no no-op-unless-armed path. (Contrast: sequence-gate would pass-through
  here.)

### RUNNABLE verification commands

**CLI-contract note (verified against `src/gleipnir/sandbox/__main__.py` +
`.gleipnir/sandbox/profiles.toml`, this pass — L-C15).** `bin/gleipnir-sandbox`
has exactly three subcommands: `test`, `lint`, `image-build`. **There is NO
`--profile` flag** and no `--image` flag on the agent-facing path — the profile
is resolved SOLELY from `profiles.default_profile` (`resolve_profile`), which is
`"python"` today. The profile is NOT overridable by flag or env var (the
`config_root` seam is in-process test-harness only, never reachable from the
`bin/gleipnir-sandbox` invocation). For the `test` subcommand, extra pytest
tokens are accepted ONLY when the resolved profile sets
`test_selector_prefix = true`; on a profile with `test_selector_prefix = false`
(which `[profile.broker]` is today) any extra token is **refused with exit 3**,
never forwarded. `[profile.broker].test` is a HARDCODED argv (four files today,
NOT including `tests/test_broker_git_commit_guard.py`).

**Consequence:** the broker commit-guard test does NOT run under the broker
profile until the OPERATOR amends `profiles.toml` (see Assemble step 0 and the
Trace tier table's Tier-3 row). Two operator amendments are required for the
broker tests below to select and cover the new test:
1. **Select the broker profile for the run.** Because there is no `--profile`
   flag, the run must resolve `[profile.broker]`. The operator sets
   `default_profile = "broker"` for the broker test run (and restores
   `"python"` afterward), OR adds a profile-selection mechanism if one is later
   introduced. As shipped today, the ONLY lever is `default_profile`.
2. **Add the new test to `[profile.broker].test`.** Append
   `"tests/test_broker_git_commit_guard.py"` to the hardcoded `test` argv in
   `[profile.broker]`, because `test_selector_prefix = false` means the argv
   cannot be extended from the CLI.

```sh
# 1. Broker commit-guard + full broker suite (regression), broker profile.
#    PRECONDITION (OPERATOR, Tier-3): profiles.toml has default_profile="broker"
#    AND [profile.broker].test includes "tests/test_broker_git_commit_guard.py".
#    The argv is fixed by the profile; no per-file selector can be passed
#    (test_selector_prefix=false), so this runs the profile's whole configured
#    argv (which now includes the new test):
bin/gleipnir-sandbox test

# 2. (Same command as 1 — under the broker profile `test` runs the profile's
#    hardcoded argv, which is the broker suite. There is no separate "one file"
#    invocation because extra selectors are refused with exit 3 on this profile.
#    To scope down you would edit [profile.broker].test, an operator Tier-3 edit.)

# 3. Python self-host profile (regression; new broker test collect-ignored here).
#    PRECONDITION: profiles.toml default_profile="python" (its shipped default).
#    Runs the python profile's argv; -q is a valid selector-prefix token
#    (python profile has test_selector_prefix=true), so it IS accepted:
bin/gleipnir-sandbox test -- -q

# 4. Plugin golden-fixture test (Node). The node profile already runs a fixed
#    argv (tests/test_sequence_gate.mjs) and refuses extra selectors
#    (test_selector_prefix=false), so test_git_guard.mjs is NOT reachable via
#    `bin/gleipnir-sandbox test` without an operator profile edit. Run it
#    directly with node (mirrors how test_sequence_gate.mjs is authored/run):
node --experimental-strip-types --test tests/test_git_guard.mjs

# 5. Confirm the config-scan CLI the plugin shells out to actually exists and exits 0/1/2:
bin/gleipnir-preflight config-scan; echo "exit=$?"

# 6. Confirm the plugin keys on the exact broker tool names present in the record.
rg -n 'gleipnir-git_commit_changes|gleipnir-git_push_current_branch' .gleipnir/plugins/git-guard.ts

# 7. Confirm the record no longer carries the false claim verbatim
#    (should return NO match once amended):
rg -n 'evaluates .guards.precommit_check. and refuses BEFORE' .gleipnir/decisions/broker-mcp.md

# 8. Confirm the broker source now runs the scan (grep for the new precommit_check call in commit_changes):
rg -n 'precommit_check' src/gleipnir/broker/git/mcp_server.py

# 9. Confirm the broker MCP `instructions=` string no longer makes the false
#    always-on branch/data-file claim (should return NO match once amended):
rg -n 'protected-branch refusal \+ secret-scan \+ data-file check' src/gleipnir/broker/git/mcp_server.py
```

**Verification-claim correction (this pass).** An earlier draft of this section
asserted "I verified each `rg`/command string resolves as written" — that claim
was FALSE for the sandbox commands: they used a non-existent `--profile` flag
and would have failed. What I have ACTUALLY verified this pass, by reading the
source: (a) `bin/gleipnir-sandbox` exposes only `test`/`lint`/`image-build`,
takes no `--profile`/`--image` flag, and resolves the profile from
`default_profile` (`src/gleipnir/sandbox/__main__.py` L86-93, L209-234); (b)
`[profile.broker]` has `test_selector_prefix = false` and a hardcoded four-file
`test` argv excluding the new test (`profiles.toml` L58-63); (c) therefore the
two operator `profiles.toml` amendments above are REQUIRED and are named as a
Tier-3 dependency. Commands 5-9 are content/existence checks I can reason about
directly (existing `bin/gleipnir-preflight` shim; `rg` literal-pattern matches
against the strings quoted from the real files read this pass). Commands 1-4
are stated as they will resolve ONCE the operator amendment lands (command 1) or
run directly under node (command 4); I have NOT executed them (this role holds
no bash) and do not claim a live run — only that they match the real CLI
contract read from source.

---

## Execution Workflow

0. **OPERATOR, Tier-3:** amend `.gleipnir/sandbox/profiles.toml` per Assemble
   step 0 — append `"tests/test_broker_git_commit_guard.py"` to
   `[profile.broker].test` and set `default_profile="broker"` for the broker
   test run. HARD PRECONDITION for steps 1-2's `bin/gleipnir-sandbox test` to
   collect the new test.
1. **gleipnir-code, test stage:** author `tests/test_broker_git_commit_guard.py`
   (T1-T5) under the broker profile. Add it to `conftest.py` `collect_ignore`
   for the python profile alongside `test_broker_tool_surface.py` (it imports
   `mcp`). Run command 1 (broker profile) → RED.
2. **gleipnir-code, code stage:** wire `precommit_check` into `commit_changes`.
   The staging block is `mcp_server.py` **L272-292** and the `git commit` call is
   **L294** (verified this pass); insert the scan BETWEEN them (after the last
   `git add` branch completes, before `_run_git(["commit", "-m", message], rd)`):
   capture `git diff --cached`, call
   `guards.precommit_check(branch, diff, staged_files)`, on `not result["passed"]`
   run `git reset HEAD` and return
   `{"success": false, "error": result["error"], "findings": <redacted secrets>}`,
   else proceed. On a `git diff --cached` failure, return a broker error WITHOUT
   committing (edge case 2). Update the module docstring, the `commit_changes`
   docstring, AND the `FastMCP(instructions=...)` string per "Broker source
   truth-fixes" (D2 drift-fix). Run command 1 → GREEN, command 3 → no-regression.
3. **OPERATOR:** author `.gleipnir/plugins/git-guard.ts` (Tier-3) per the Plugin
   design specification; amend `.gleipnir/decisions/broker-mcp.md` (Tier-3) per
   the Record amendment specification; optionally add the header note to
   `hooks/pre-commit`.
4. **gleipnir-code, test stage:** author `tests/test_git_guard.mjs` + the stub-CLI
   fixtures (T6-T14); run command 4 (`node --experimental-strip-types --test
   tests/test_git_guard.mjs`, run directly — NOT via `bin/gleipnir-sandbox test`,
   whose node profile has a fixed argv and `test_selector_prefix=false`) → GREEN.
5. **quality stage:** verify all Stress-test criteria; run commands 5-9 as the
   evidence sweep (command 9 confirms the false `instructions=` substring is
   gone). Confirm the honesty label is present in both the plugin header and this
   plan.
6. **git stage (git-ops):** commit the code + test artifacts. NOTE: the broker
   will now secret-scan its own commit of these files — the planted secrets live
   only inside test files as programmatically-shaped fakes on `+`-added lines, so
   verify they do not trip the broker's own scan (they are inside `.py`/`.mjs`
   test literals; if the always-on scan flags them, stage them via the human
   hook path or confirm the redaction/pattern boundary — a real integration
   detail for the git stage to watch, not a plan blocker).

---

## Honesty label (cooperative-policy until S-2) — EXPLICIT

**Neither seat is a hard boundary today.** Both `.gleipnir/plugins/git-guard.ts`
(the plugin seat) and `src/gleipnir/broker/git/mcp_server.py` (the broker source)
sit in **agent-writable space** pre-S-2. A `throw`/refuse in either is
genuinely agent-*unbypassable* only once the S-2 mount + G-1 preflight make
those paths OS-read-only to the agent uid
(`.gleipnir/decisions/s2-g1-closure.md`). Until then, enforcement rests on the
roster capability denies + this cooperative-policy discipline — exactly the same
posture `sequence-gate.ts` carries. This plan does NOT claim Approach C is a hard
boundary today.

**What IS structurally real today:** the broker cannot pass `--no-verify` / `-n`
/ `-c core.hooksPath` (refused at `_run_git`, verified), so whichever seat
enforces, an agent cannot bypass it via a hook-skip flag. That structural
invariant is unchanged by this plan.

---

## Confirmation: no NEW material decision

I found **no genuinely new material tradeoff** beyond the hook-fate flag the
delegation pre-authorised me to evaluate — and I judged that flag NON-material
(see Hook-fate analysis) and made the recommended plan-level call rather than
escalating. All other resolutions (D3-D6, D8) are non-material plan-level
tradeoffs the delegation explicitly assigned to me with advisory leans, resolved
with reasoning above. D1 (mechanism) and D2 (drift-fix) are operator-converged
and were NOT re-decided. **The plugin-arming posture (always-active vs
armed-only), previously surfaced as an Open item for operator confirmation, is
now OPERATOR-CONVERGED (D9): always-active whenever loaded, with exit-2
PROCEED_UNCLOSED (`--override-ack`) as the operator's escape valve. It was
converged by the operator, not decided in-plan.** No genuinely new material
tradeoff remains open.

**Spec-review correction pass (this edit) — no material decision introduced.**
The spec-review found two blocking defects and two minor notes; all four are
mechanical corrections to build steps/verification, not design choices, and D1
(Approach C), D2 (drift-fix), and D9 (always-active) are UNCHANGED — D2's *scope*
was widened (per the review instruction) to also fix the false
`FastMCP(instructions=...)` string in `mcp_server.py`, but the decision itself
(amend the record + broker metadata to state the truth) is the same converged
D2. The one NEW artifact the correction surfaced — the operator amendment to
`.gleipnir/sandbox/profiles.toml` — is NOT a material tradeoff: it is a
mechanical Tier-3 prerequisite forced by the real sandbox CLI contract (no
`--profile` flag; profile from `default_profile`; `[profile.broker]` argv is
hardcoded with `test_selector_prefix=false`). There is no either/or to converge;
the profile edit is the ONLY way the shipped CLI can run the new broker test, so
it is named as a build dependency, not escalated as a decision.
