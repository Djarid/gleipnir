# Plan: Wire `config-scan` into the git pre-commit hook

**Stage routing (this plan runs the FULL 8-stage hardened pipeline).**
`hooks/pre-commit` is in the Axis-1 disqualifier set `X` (`hooks/**`), so the
prose/config-only track is unavailable — no matter that the plan also touches a
`decisions/` prose file. Enforcement-bearing (hook that *runs* on every commit).
Cognition Gate-1 **case (ii)** (executable-but-non-OOP: a `#!/bin/sh` hook):
**DRY + Design Intent** apply; **SOLID + class/module SRP attested N/A**.

**GOTCHA pre-flight (output visibly).**
- **Goal check** (`goals/manifest.md`): consulted. Relevant goals — Plan format
  (`plan-format.md`), Methodology (ATLAS/GOTCHA ahead of planning). No pipeline-
  sequencing goal exists (deliberately absent under G-5); the orchestrator
  sequences from `stage-role-map.md`. ✔
- **Plan-before-code**: correct order. This plan is the artifact; the hook edit
  and tests are the downstream `code`/`test` stages. This planner writes ONLY
  `.gleipnir/plans/**`. ✔
- **Gaps named**: none blocking. The one honesty caveat (cooperative-policy
  until S-2) is inherited from `git-guard.ts` and carried in the Honesty label
  below.
- **Layer mapping (GOTCHA)**: this is a *Tools/Orchestration-layer* change (a
  deterministic VCS-layer gate), not a Goals or Hard-prompt change. The hook is
  the deterministic-code seat that a probabilistic agent cannot talk its way
  past; the fail-mode is coded, not judged.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-A | Where config-integrity is enforced on a plain commit | ADD `config-scan` to `hooks/pre-commit` alongside secret-scan | Leave it to git-guard.ts only (broker path); CI-only | **Operator-converged this session.** Closes the asymmetry: git-guard.ts gates only *broker* writes; a plain `git commit` currently skips config-scan entirely. |
| D-B | Fail-mode when config-scan can't run or REFUSEs | FAIL-CLOSED (refuse the commit) | Fail-open / warn-only | **Operator-converged this session.** Mirrors git-guard.ts's fail-closed discipline. Humans may `--no-verify`; the broker cannot pass it, so agents can't bypass. |
| D-C | Exit-code contract the hook maps | Mirror `git-guard.ts` EXACTLY: 0=CLOSED→proceed, 1=REFUSE→block, 2=PROCEED_UNCLOSED→warn+proceed, any other / can't-run→fail-closed block | Invent a hook-local mapping | git-guard.ts (L69–73, L128–148) is the single source of the contract; hook and plugin MUST agree or a repo could pass one gate and fail the other. |
| D-D | Always-on vs opt-in | **ALWAYS-ON** (like secret-scan; parity with git-guard.ts D9 ALWAYS-ACTIVE) | Gate behind `GLEIPNIR_GIT_STRICT` like branch/data-file checks | Config mis-scoping is dangerous regardless of strict mode; git-guard runs it unconditionally. **Confirms the operator's stated recommendation.** |
| D-E | Integration with existing `fail` accumulator | Reuse the `fail=0 … exit $fail` accumulator; config-scan sets `fail=1` on block, never short-circuits secret-scan | A second `exit` mid-hook; a separate accumulator | Both checks must run and both must be able to fail the commit; neither may short-circuit the other. Cleanest with the existing pattern. |
| D-F | `set -e` safety around a non-zero-exiting command | `code=0; "$cli" config-scan || code=$?` capture pattern | Bare `"$cli" config-scan` (would abort the hook under `set -e` on any non-zero exit, defeating the mapping) | `set -eu` is preserved; the `|| code=$?` idiom captures the exit code without the ERR-exit aborting the hook before the mapping runs. |
| D-G | CLI location / repo-root resolution | Resolve repo root robustly; invoke the resolved `bin/gleipnir-preflight` | Hardcode `bin/gleipnir-preflight` relative to cwd | Hook normally runs with cwd=repo root, but must be robust to worktree/subdir invocation. Resolution strategy in Trace §Edge cases. |
| D-H | Where the hook test lives + how it runs + WHO executes it | New **host shell test** `tests/test_precommit_hook.sh`, run directly on host (NOT via `bin/gleipnir-sandbox test`). **Test AUTHORED by gleipnir-code; EXECUTED by the build-session/orchestrator (holds `bash`)**, because no roster subagent's grant permits `sh <file>` (gleipnir-code denies `sh*`/`bash*`/`*`; only `bin/gleipnir-sandbox` exact-match is allowed). NOT routed through the sandbox (a host shell hook needs a real git index; mirrors the host-run `.mjs` test precedent — but those `.mjs` tests are likewise executed OUTSIDE any agent grant, see the note below). | pytest under the sandbox; a `.mjs` test; assigning the `sh …` run to gleipnir-code | The hook is `#!/bin/sh` and needs a real git index; the sandbox python image has no such fixture harness and host execution of the *hook itself* is the realistic arbiter. Mirrors the established host-run precedent of `test_git_guard.mjs` / `test_sequence_gate.mjs` (run directly, not sandboxed). The executor split closes the stale assumption that gleipnir-code could run the shell test: its grant was tightened to `bin/gleipnir-sandbox` exact-match when the sandbox landed. See §Trace and §Stress-test. |
| D-I | Stale decision-record status fix | Update `.gleipnir/decisions/config-scoping-preflight.md` status + open-items to reflect: git-guard.ts already wires the *broker* path, and this plan adds the *VCS-hook* path | Leave the "NOT YET WIRED" status | The status line is stale (operator-flagged). Both wirings must be reflected so the record stops mis-stating enforcement reality. |

No **new** material tradeoff arose beyond D-A/D-B (see §Stress-test "Convergence
check"). D-C…D-I are mechanical consequences of the converged decisions +
existing contracts, not new design choices.

---

## Architect

- **Problem (one sentence).** A plain `git commit` does not run the config-
  scoping preflight — only broker-issued git writes do (via `git-guard.ts`) — so
  a mis-scoped agent/opencode config can be committed at the VCS layer; wire
  `config-scan` into `hooks/pre-commit`, fail-closed, to close that gap.
- **User.** Every committer in the repo — humans (who retain the `--no-verify`
  escape) and the `gleipnir-git` broker (which cannot pass `--no-verify`, so is
  hard-gated).
- **Measurable success criteria.**
  1. A staged **mis-scoped** config (config-scan → REFUSE/exit 1) causes the
     hook to **block** the commit (non-zero exit).
  2. A staged **clean** config (config-scan → CLOSED/exit 0) lets the commit
     **proceed** (assuming secret-scan also passes).
  3. `bin/gleipnir-preflight` **missing or non-executable** → hook **blocks**
     fail-closed with a clear, actionable message (mirrors git-guard's
     PreflightUnavailable messaging: suggest `chmod +x` /
     `git update-index --chmod=+x`).
  4. config-scan **exit 2** (PROCEED_UNCLOSED, operator `--override-ack`) →
     hook **warns and proceeds** (does not block).
  5. Any **other** exit code → hook **blocks** fail-closed.
  6. The existing **secret-scan is not weakened**: a staged secret still blocks
     even when config-scan passes, and config-scan blocking does not short-
     circuit secret-scan (both run; commit blocked if *either* fails).
  7. `set -eu` is preserved; the hook does not abort prematurely on config-scan's
     non-zero exit before the mapping runs.
- **Constraints.**
  - Mirror the `git-guard.ts` exit contract exactly (D-C).
  - stdlib-only enforcement core is unaffected (the hook shells out to the
    existing CLI; no new deps — `runtime-and-deps.md`).
  - The hook is Tier-3 enforcement config on the hardened path; the two review
    passes + negative-check attestation (`stage-role-map.md`) apply.
  - Do NOT re-decide the tool (config-scan) or the fail-mode (fail-closed):
    both are operator-converged (D-A/D-B).

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Status | Writer / stage |
|---|---|---|---|
| The hook (edited) | `hooks/pre-commit` | exists (46 lines, read) | gleipnir-code (`code` stage) — X-member, forces hardened routing |
| Host shell test (new) | `tests/test_precommit_hook.sh` | **to be created** | gleipnir-code (`test` stage) — tests live in `tests/`, not under `.gleipnir/` |
| Exit-code contract (source of truth) | `.gleipnir/plugins/git-guard.ts` L69–73, L128–148 | exists (read) | **not edited** — cited only |
| CLI shim invoked | `bin/gleipnir-preflight` | exists (21 lines, read) | **not edited** — invoked |
| Stale status fix | `.gleipnir/decisions/config-scoping-preflight.md` | exists (94 lines, read) | **OPERATOR** (Tier-3 decisions/ prose; not agent-written) |

**Path note (Tier-3 authorship).** `hooks/pre-commit` is not under `.gleipnir/`,
so it is writable by `gleipnir-code` at the `code` stage under hardened review.
`.gleipnir/decisions/config-scoping-preflight.md` is Tier-3 POLICY prose — its
edit is **operator-applied** (this planner names the exact change in D-I /
§Assemble; it does not and cannot write it).

### Integrations map

- **Hook → CLI.** `hooks/pre-commit` execs the resolved `bin/gleipnir-preflight
  config-scan`, captures the exit code, maps per D-C.
- **CLI → scan.** `bin/gleipnir-preflight` (thin shim) execs
  `.venv/bin/python -m gleipnir.preflight config-scan`; all decision logic lives
  in `src/gleipnir/preflight/config_scan.py` (unchanged by this plan).
- **Contract parity.** The hook's 0/1/2/else mapping is the shell twin of
  git-guard.ts's `decideFromExit` + `PreflightUnavailable` (missing/non-exec).
  Same repo, two committer paths (broker vs plain commit), one contract.
- **Accumulator.** config-scan feeds the same `fail` variable as secret-scan;
  final `exit $fail` (D-E).

### Edge cases

1. **`set -e` + non-zero exit.** A bare invocation would trip the ERR-exit and
   abort the hook before the mapping — use `code=0; "$cli" config-scan >&2 ||
   code=$?` (D-F). Verify the `|| code=$?` form is `set -e`-safe (a command in a
   `||` list does not trigger ERR-exit).
2. **CLI missing / non-executable.** Pre-check with a `[ -x "$cli" ]` test
   BEFORE invoking (mirrors git-guard's `accessSync(cli, X_OK)` pre-check). If
   absent or not `+x`: print an actionable fail-closed message (name the
   `chmod +x` / `git update-index --chmod=+x` fix, cite it as a BROKEN
   PREREQUISITE not a policy REFUSE) and set `fail=1`. Do NOT attempt the exec.
3. **Repo-root / worktree / subdir resolution (D-G).** The hook normally runs
   with cwd=repo root, but resolve robustly. Recommended: derive the repo root
   from git itself —
   `repo=$(git rev-parse --show-toplevel 2>/dev/null || true)` — and fall back
   to the hook's own directory (`hooks/` lives at repo root:
   `here=$(CDPATH= cd "$(dirname "$0")" && pwd); repo=${repo:-$(cd "$here/.." && pwd)}`).
   Then `cli="$repo/bin/gleipnir-preflight"`. Rationale: `git rev-parse
   --show-toplevel` is correct under worktrees and subdir invocation; the
   `dirname "$0"` fallback covers a degenerate no-git-in-PATH case (the hook is
   only ever run by git, so `$0` is a reliable anchor). The CLI is invoked with
   cwd unchanged (config-scan reads the repo from its own repo-root resolution,
   like `bin/gleipnir-preflight`'s shim) — but pass `cwd=$repo` explicitly by
   running it from `$repo` if config-scan is cwd-sensitive; **the code stage must
   confirm** whether `config_scan` resolves the repo from its own script
   location (like the shim's `here/..` logic) or from cwd, and set cwd
   accordingly. (Flagged as a code-stage verification, not a plan-blocker: the
   shim already resolves `repo` from its own path, so config-scan is expected to
   be cwd-insensitive — confirm.)
4. **config-scan writes to stderr.** git-guard surfaces the CLI's stderr on warn
   (exit 2). The hook should let config-scan's stderr flow through (`>&2`) so the
   committer sees the finding, then print its own one-line verdict.
5. **Secret-scan independence.** config-scan must not run before secret-scan in a
   way that `exit`s early; both use `fail=1` and fall through to `exit $fail`
   (D-E). Order between them is immaterial to correctness (both accumulate);
   place the config-scan block after the secret-scan block for readability.
6. **`--no-verify`.** Out of scope for the hook (git skips the hook entirely).
   The invariant that agents cannot bypass rests on the broker refusing to pass
   `--no-verify` (existing, `git-guard.ts` honesty label) — cited, not modified.

---

## Link (validated before building)

- **Read + confirmed to exist:** `hooks/pre-commit` (46 lines),
  `.gleipnir/plugins/git-guard.ts` (185 lines; exit contract at L69–73,
  decision at L128–148, PreflightUnavailable pre-check at L87–102),
  `bin/gleipnir-preflight` (21-line shim; resolves `repo` from `$0` dir),
  `.gleipnir/decisions/config-scoping-preflight.md` (94 lines; stale status at
  L3).
- **Test precedent confirmed:** `tests/test_git_guard.mjs` (golden-fixture +
  stub-CLI-in-temp-dir + exit 0/1/2/missing/non-exec cases) and
  `tests/test_sequence_gate.mjs` are **host-run** (`node --test …`,
  direct — NOT `bin/gleipnir-sandbox test`; the sandbox python image lacks node
  and the fixture harness). `Makefile` `test` target = `./bin/gleipnir-sandbox
  test` (python suite only). `tests/test_bin_executable.py` documents exactly
  why a non-executable `bin/*` fails the gate closed (the "CLI missing/non-exec"
  path this hook must also handle) and shows the `git ls-files -s` committed-mode
  read pattern.
- **Routing confirmed:** `hooks/**` ∈ `X` → full hardened pipeline; Gate-1 case
  (ii). (`stage-role-map.md`.)
- **Not yet validated (deferred to code stage, flagged above):** whether
  `config_scan` resolves its repo from cwd or from its own path (edge case 3).

---

## Assemble (intended build order)

1. **[test stage — AUTHOR: gleipnir-code; EXECUTE: build-session/orchestrator]**
   gleipnir-code AUTHORS `tests/test_precommit_hook.sh` (a host `/bin/sh` test)
   covering the six success criteria via the golden-fixture + stub-CLI approach
   (see §Stress-test for the concrete test matrix) and reports the **predicted
   RED** outcome (the hook does not yet invoke config-scan). The
   **build-session/orchestrator** (which holds `bash`) then RUNS
   `sh tests/test_precommit_hook.sh` → **RED**, confirming the real failure.
   gleipnir-code CANNOT run this raw host shell test — its bash grant denies
   `sh*`/`bash*`/`*` (only `bin/gleipnir-sandbox test|lint` exact-match is
   allowed), and no other roster subagent can either; execution is therefore the
   build session's, mirroring the Ansible-harness split used all session (and see
   the host-run-precedent note in §Assemble below). Register how it runs (host
   shell; documented in the test header, mirroring `test_git_guard.mjs`'s
   "Run with:" header and its NOT-sandboxed note).
2. **[code stage — AUTHOR: gleipnir-code; EXECUTE: build-session/orchestrator for
   the test runs]** gleipnir-code EDITS `hooks/pre-commit`: add the config-scan
   block after the secret-scan block — repo-root resolution (edge case 3), `[ -x
   "$cli" ]` pre-check (edge case 2, fail-closed message), `code=0; … || code=$?`
   capture (D-F), 0/1/2/else mapping (D-C) feeding `fail` (D-E), stderr
   passthrough (edge case 4). Preserve `set -eu`, the secret-scan block, the
   opt-in branch/data-file blocks, and the final `exit $fail`. Update the hook's
   header comment to mention config-scan alongside secret-scan (DRY: one place
   states what the hook enforces). The **build-session/orchestrator** then RUNS
   `sh tests/test_precommit_hook.sh` → **GREEN**, and RUNS the edited hook against
   the live repo (ST-10) to confirm the real repo's own commit still passes
   CLOSED (no self-lockout). gleipnir-code authors the edit but does not execute
   either shell run (grant boundary, as in step 1).
3. **[quality stage — quality-reviewer]** Run the TWO hardened passes
   (spec-conformance + blast-radius/false-success), produce the negative-check
   attestation (§Stress-test), verify criteria 1–7, and the honour check
   (applied hook honours the Design Intent). SOLID/DRY dimension scoped to
   DRY-only (case ii).
4. **[OPERATOR]** Apply the Tier-3 stale-status fix to
   `.gleipnir/decisions/config-scoping-preflight.md` (D-I): change the status
   line from "NOT YET WIRED" to reflect that git-guard.ts wires the broker path
   AND `hooks/pre-commit` now wires the VCS-hook path; update the matching
   open-item bullet. Exact edit named in §Execution Workflow.
5. **[git stage — git-ops]** Commit the hook + test (+ the operator's decision-
   record edit if co-staged). NOTE the meta-hazard below.
6. **[gate stage — orchestrator]** Read attestation; emit pipeline state.

**Meta-hazard (name for the git stage, not a plan blocker).** Committing this
hook change will itself run the newly-wired config-scan on the commit. That is
the desired dogfood — but the `test` stage must ensure the test fixtures (the
deliberately mis-scoped BAD config) live in a **temp dir**, never staged in the
real repo, or the real commit would REFUSE. The BAD config is a fixture the test
writes into a throwaway temp git repo, exactly as `test_git_guard.mjs`'s
`makeRepoWithStub` builds a temp repo. Confirm no fixture leaks into the real
staged set.

**Host-run-precedent note (who executes host tests).** The cited precedent —
`tests/test_git_guard.mjs` / `tests/test_sequence_gate.mjs` run "host-run"
(`node --test …`, direct, not sandboxed) — describes WHERE those tests run, not
that gleipnir-code runs them. gleipnir-code's bash grant was **tightened to
`bin/gleipnir-sandbox test|lint` exact-match when the sandbox landed**, so it
cannot invoke `node …` or `sh …` on the host any more than it can here. Those
`.mjs` tests are therefore executed **OUTSIDE gleipnir-code's grant** — by the
build session / orchestrator (which holds `bash`), the same executor this plan
assigns for `sh tests/test_precommit_hook.sh`. This plan does NOT rely on
gleipnir-code running any host shell command; the precedent is an execution-
location precedent, not an execution-by-the-agent precedent.

---

## Stress-test (acceptance checks)

**Test harness shape (D-H).** A host `/bin/sh` script that, per case, builds a
throwaway git repo in a temp dir (`git init`), installs the **real**
`hooks/pre-commit` (copied from the repo under test) as its hook or invokes it
directly with a controlled staged index, plants a **stub `bin/gleipnir-preflight`**
that exits with a controlled code (mirroring `test_git_guard.mjs`'s
`makeRepoWithStub`), stages content, runs the hook, and asserts the exit
status. This isolates the *hook's mapping logic* from config-scan's internals —
the hook contract is what's under test, and the stub is the contract's twin of
the real CLI.

Concrete acceptance criteria (each a test case):

- **ST-1 (clean → proceed).** Stub exits 0; benign staged content, no secret →
  hook exits **0**. (Criterion 2.)
- **ST-2 (mis-scoped → block).** Stub exits 1 (REFUSE) → hook exits **non-zero**;
  stderr names config-scan REFUSE. (Criterion 1.)
- **ST-3 (missing CLI → fail-closed block).** No `bin/gleipnir-preflight` present
  → hook exits **non-zero** with a BROKEN-PREREQUISITE message (not a policy
  REFUSE), suggesting `chmod +x` / `git update-index --chmod=+x`. (Criterion 3.)
- **ST-3b (non-exec CLI → fail-closed block).** `bin/gleipnir-preflight` present
  at mode 0644 → hook exits **non-zero**, same broken-prerequisite class as ST-3
  (the exact regression `test_bin_executable.py` guards). (Criterion 3.)
- **ST-4 (exit 2 → warn + proceed).** Stub exits 2 → hook exits **0**, prints a
  PROCEED_UNCLOSED / override warning to stderr. (Criterion 4.)
- **ST-5 (unexpected code → fail-closed block).** Stub exits 7 (and 42) → hook
  exits **non-zero**, "unexpected exit code" class. (Criterion 5.)
- **ST-6 (secret-scan not weakened).** Stub exits 0 (config CLOSED) BUT staged
  content contains a fake secret matching the secret-scan regex → hook exits
  **non-zero** (secret-scan still fires). (Criterion 6, half 1.)
- **ST-7 (both run, no short-circuit).** Stub exits 1 (REFUSE) AND staged content
  contains a fake secret → hook exits **non-zero**; assert BOTH the secret-scan
  message AND the config-scan REFUSE message appear (neither short-circuits the
  other). (Criteria 6 half 2 + E-2 the accumulator semantics.)
- **ST-8 (`set -eu` preserved).** The hook still begins `set -eu` and does not
  abort before the mapping on config-scan's non-zero exit (implicitly proven by
  ST-2/ST-5 producing the *mapped* verdict, not a bare premature abort — add an
  explicit assertion that the config-scan verdict message is emitted, proving
  the mapping ran rather than `set -e` aborting first). (Criterion 7.)
- **ST-9 (opt-in checks intact).** With `GLEIPNIR_GIT_STRICT=1` and a protected-
  branch / data-file staged, those checks still fire alongside config-scan (no
  regression to the existing opt-in blocks).
- **ST-10 (live-repo self-pass — no lockout).** The **build-session/orchestrator**
  (holds `bash`; NOT gleipnir-code) runs the edited hook against the real repo's
  current config (real `bin/gleipnir-preflight config-scan`, not a stub) and
  asserts it exits **0** — the framework does not lock itself out. (Mirrors the
  config-scoping-preflight ST-4 live-repo guard.) gleipnir-code authors this case
  inside `tests/test_precommit_hook.sh`; it does not execute the shell run (grant
  boundary — see the host-run-precedent note below).

**Negative-check attestation (hardened path — produced by `quality-reviewer`,
NOT the author).** One row per grant/enforcement change. The single enforcement
change here is the added config-scan block. Required row (schema; reviewer fills
evidence against the **applied, post-change** `hooks/pre-commit`):

| grant | intended_scope | over_broad_form_checked | evidence `[D]/[J]` | negative_result | attested_by |
|---|---|---|---|---|---|
| config-scan block blocks the commit ONLY on REFUSE / can't-run / unexpected-code | fail-closed on {1, non-runnable, other}; proceed on {0, 2} | an over-broad fail-open: does the block ever `exit 0` / leave `fail=0` on a REFUSE or a missing CLI? does it swallow config-scan's non-zero and proceed? | `[D]` grep/read the applied block: confirm no `code=0`-reset after capture, no unconditional `fail=0`, the `[ -x ]` pre-check sets `fail=1` on absence | "no fail-open path present: exit 1 / missing / non-exec / unexpected all set `fail=1`; only 0 and 2 fall through" | reviewer ≠ author |

Additional reviewer negative-check (parity, `[J]`+`[D]`): the hook's 0/1/2/else
mapping is **identical in outcome** to git-guard.ts `decideFromExit` +
`PreflightUnavailable` — grep both, confirm no divergence (e.g. hook does not
treat 2 as block, or 0 as warn).

**Convergence check (new-tradeoff scan).** I looked for a genuinely NEW material
tradeoff beyond D-A/D-B. **None found.** Every downstream choice (D-C…D-I) is
mechanically determined by (a) the operator-converged decisions, (b) the
existing git-guard.ts contract, or (c) existing repo conventions (host-run tests,
the `fail` accumulator). The one item requiring a human hand is the **Tier-3
decision-record edit (D-I)** — that is authorship-tier, not a design tradeoff,
and is routed to the operator in §Assemble/§Execution. Nothing to send back to
the brainstorm gate.

---

## Execution Workflow

For the implementing agent (`code`/`test` stages) and the operator:

1. **Test first** — **AUTHOR** (`test` stage, gleipnir-code): create
   `tests/test_precommit_hook.sh`. Header must state: run command
   (`sh tests/test_precommit_hook.sh` on the **host**, NOT via
   `bin/gleipnir-sandbox test` — the sandbox python image has no node/shell
   fixture harness and this exercises the real hook against a real temp git
   index), and why (mirror `test_git_guard.mjs`'s host-run note). Implement
   ST-1…ST-10 using temp git repos + a stub `bin/gleipnir-preflight` for
   ST-1/2/4/5/6/7/8 and a real CLI for ST-10. **EXECUTE** (build-session/
   orchestrator, which holds `bash`): run `sh tests/test_precommit_hook.sh` →
   **RED**. gleipnir-code does NOT run this — its bash grant denies
   `sh*`/`bash*`/`*` (only `bin/gleipnir-sandbox test|lint` exact-match), and no
   roster subagent can run a raw host shell test; the build session executes it,
   as with the Ansible harness this session. gleipnir-code reports the predicted
   RED; the build session reports the real RED.
2. **Edit the hook** — **AUTHOR** (`code` stage, gleipnir-code): insert the
   config-scan block into `hooks/pre-commit` after the secret-scan block.
   Skeleton the implementer must realise (illustrative — the implementer owns
   exact shell):
   - resolve `repo` (`git rev-parse --show-toplevel` with `dirname "$0"/..`
     fallback), `cli="$repo/bin/gleipnir-preflight"`;
   - `if [ ! -x "$cli" ]; then echo "...broken prerequisite, chmod +x..." >&2;
     fail=1; else code=0; ( cd "$repo" && "$cli" config-scan ) >&2 || code=$?;
     case "$code" in 0) : ;; 2) echo "...PROCEED_UNCLOSED, override..." >&2 ;;
     1) echo "...config-scan REFUSED..." >&2; fail=1 ;; *) echo "...unexpected
     exit $code, fail-closed..." >&2; fail=1 ;; esac; fi`
   - update the header comment to list config-scan alongside secret-scan;
   - leave `set -eu`, secret-scan, opt-in blocks, and `exit $fail` intact.
   Verify edge case 3 (config-scan cwd sensitivity) before finalising the
   `( cd "$repo" && … )` wrapper. **EXECUTE** (build-session/orchestrator): after
   the edit is applied, run `sh tests/test_precommit_hook.sh` → **GREEN**, and run
   ST-10 (the edited hook against the live repo) → exit 0. gleipnir-code authors
   the hook edit but does not run either shell command (grant boundary, as in
   step 1); the build session reports the real GREEN + ST-10 pass.
3. **Quality** (`quality` stage, quality-reviewer): two separate passes +
   negative-check attestation (above) + honour check against Design Intent.
4. **Operator (Tier-3 edit, D-I):** in
   `.gleipnir/decisions/config-scoping-preflight.md`, change the L3 status
   sentence "**...NOT YET WIRED to run automatically.**" and the first open-item
   bullet ("Not yet enforced automatically...") to state: config-scan is wired
   in TWO seats — the `git-guard.ts` opencode plugin (broker git writes) and
   `hooks/pre-commit` (every VCS commit, fail-closed); reference this plan.
5. **git** (git-ops): commit hook + test (+ co-staged decision edit). Heed the
   meta-hazard (no BAD fixture staged in the real repo).
6. **gate** (orchestrator): read attestation, emit state.

---

## Design Principles (Gate 1 — case (ii): executable-but-non-OOP shell hook)

- **SOLID analysis — `N/A — no object/function structure`.** `hooks/pre-commit`
  is a flat `#!/bin/sh` script with no classes, functions, interfaces, or
  modules; Liskov / Interface-Segregation / Dependency-Inversion / class-SRP
  have no referent.
- **Single-Responsibility (class/module) — `N/A — no object/function
  structure`.** Same reason.
- **DRY analysis.** (a) The exit-code contract is NOT re-specified — the hook
  mirrors the single source of truth in `git-guard.ts` (D-C); the plan forbids a
  hook-local reinvention of the mapping semantics. (b) The scan logic itself is
  NOT duplicated — the hook shells out to the existing `bin/gleipnir-preflight
  config-scan` (the same CLI git-guard.ts calls), not a shell reimplementation
  of config_scan. (c) The `fail`-accumulator + `exit $fail` idiom is reused, not
  a parallel accumulator (D-E). (d) The header comment names what the hook
  enforces in one place. Residual acceptable "duplication": the 0/1/2/else
  mapping exists in both `git-guard.ts` (JS) and the hook (shell) because they
  are two committer paths in two languages — this is intentional parity, and the
  quality pass's parity negative-check guards against the two *diverging* (the
  real DRY risk).
- **Design Intent (specific, falsifiable).** *After this change,
  `hooks/pre-commit` BLOCKS a commit whose staged config config-scan REFUSEs
  (exit 1), ALLOWS a commit whose config is CLOSED (exit 0), WARNS-and-allows on
  PROCEED_UNCLOSED (exit 2), FAILS CLOSED (blocks) when config-scan cannot run
  (missing/non-executable CLI) or returns any other exit code, and does NOT
  weaken the existing secret-scan (a staged secret still blocks even when
  config-scan passes, and neither check short-circuits the other).* Falsifiable:
  a reviewer can point to any hook path that (i) proceeds on exit 1, (ii) blocks
  on exit 0, (iii) blocks on exit 2, (iv) proceeds on a missing CLI, or (v) lets
  config-scan's `exit`/`set -e` behaviour skip the secret-scan — each of those
  violates the stated intent and is caught by ST-2/ST-1/ST-4/ST-3/ST-6–7.

---

## Honesty label (cooperative-policy until S-2)

Inherited from `git-guard.ts`. The hook is genuine enforcement for the
**broker** (which cannot pass `--no-verify`) but `hooks/pre-commit` sits in
agent-writable space pre-S-2, so a sufficiently-privileged agent could in
principle edit the hook itself; that becomes a hard boundary only once the S-2
mount makes `hooks/` OS-read-only to the agent uid. Humans retain the
`--no-verify` escape by design. This plan does not claim the hook is a hard
boundary today — it closes the *plain-commit config-integrity asymmetry*, which
is the converged goal.
