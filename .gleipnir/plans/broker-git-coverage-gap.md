# Plan: Close the test-coverage gap on `broker/git/mcp_server.py`

> **Stage:** `plan` (gleipnir-plan). **Input:** an operator/orchestrator
> coverage-remediation request (no separate brainstorm brief — this is bounded
> test-authoring against existing, unchanged production code, not a design
> exploration). The target file sits at 52% line coverage per the last measured
> run; the guard/secret-scan path (`tests/test_broker_git_commit_guard.py`) and
> the tool-surface conformance (`tests/test_broker_tool_surface.py`) are already
> covered and must NOT be duplicated.
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0). This file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it (the orchestrator
> sequences that; nothing here is executed now). In particular this plan
> **names** one Tier-3 operator prerequisite (a `profiles.toml` amendment); it
> does not write it.

---

## Decisions (index)

Summary of every decision this plan fixes, in order encountered; full reasoning
is in the sections below. Rows 1–3 are planning-stage decisions; row 4 is a
material sequencing constraint surfaced to the operator (not decided by the
planner); row 5 records the Trace finding that **no production bug was found**.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Where the new tests live | **One new file** `tests/test_broker_git_mcp_server.py` driving the tool functions directly against real temp git repos, mirroring `test_broker_git_commit_guard.py`'s proven pattern | Extending the existing commit-guard file; or a pure-mock (`monkeypatch subprocess.run`) approach | A new file keeps the already-covered secret-scan tests untouched (no duplication) and names its scope in its own docstring. Real temp-repo driving (matching the existing broker test) exercises the true `subprocess`→`git` path the gaps are about; mocks are reserved ONLY for the three unreachable-via-real-git `_run_git` exception branches (row 2). |
| 2 | How to hit the `_run_git` exception branches (`TimeoutExpired`, `FileNotFoundError`, generic `Exception`) | **Targeted `monkeypatch` of `subprocess.run`** (and/or a 0s timeout / bogus PATH) for exactly those three branches, driven through a public tool call so the structured-error contract is asserted end-to-end | Trying to provoke them with real git (unreliable/slow — a real timeout needs a hanging git; `FileNotFoundError` needs git removed from PATH) | These three branches are not reliably reachable with a real `git` in-sandbox. Injecting the exception at the `subprocess.run` boundary is the standard, deterministic way to cover them and asserts the exact `{"success": False, "error": ...}` shape each returns. |
| 3 | Coverage target & measurement | **≥85% line+branch on `mcp_server.py`**, measured by `bin/gleipnir-sandbox test` (broker profile, which already runs `--cov=src/gleipnir/broker --cov-branch`); anything left below is honestly justified in the report per `gleipnir-code.md` | Claiming a number without the sandbox measuring it; targeting line-only | 85% is the standing target in `gleipnir-code.md`. The broker profile already emits line+branch term-missing coverage, so the number is measured, not asserted. The plan enumerates every currently-uncovered branch so ≥85% is achievable; the `if __name__ == "__main__"` guard (line 416–417) is the one expected unreachable line and is pre-justified. |
| 4 | **[MATERIAL — surfaced to operator, NOT decided here]** Test-file collection under the broker profile | Flag that `profiles.toml` (Tier-3, operator-only) **must be amended** to add the new test file to `[profile.broker].test` before `bin/gleipnir-sandbox test` will collect it | Silently assuming the runner picks up the new file | `.gleipnir/sandbox/profiles.toml:60` hardcodes an EXPLICIT list of broker test files; it is Tier-3 POLICY, agent-unwritable. A new test file is NOT auto-collected. This mirrors the D8 note in `test_broker_git_commit_guard.py`. Without the amendment the new tests are dead. **Operator action; the planner names it, does not perform it.** |
| 5 | Production-code changes | **None anticipated** — Trace confirmed every error branch in the gap list is reachable and behaves correctly; this is pure test-authoring | Silently "fixing" any code | Per the delegation's standing instruction: if a genuine bug requiring a production fix were found, it would be flagged here as a decision, not silently fixed. Trace found none (see Trace §"Bug-hunt result"). If `gleipnir-code` discovers one while making a test pass, it must STOP and surface it, not weaken the test or patch silently. |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`.gleipnir/goals/manifest.md`):** "Plan format"
  (`plan-format.md`) and "Methodology (ATLAS/GOTCHA ahead of planning)" apply.
  This plan follows the required Decisions-index / Architect / Trace / Link /
  Assemble / Stress-test / Execution-Workflow structure. No pipeline-sequencing
  goal is authored or implied (G-5 rule respected).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or git are produced here.
- **Layer placement (GOTCHA layers):** the target is a **Tools-layer** broker
  server (`gleipnir-git`) with **Args-layer** structural enforcement (the
  hook-bypass choke point, force-push absence). This work adds **no** behaviour;
  it adds **tests** that exercise existing tool functions and their error
  branches. It touches no enforcement core (G-3/G-5/G-4/memory) and does not
  change G-5 pipeline ordering.
- **Gaps / factual findings named (mechanical, verified this session):**
  1. **`profiles.toml` hardcodes the broker test list (Decision 4).**
     `.gleipnir/sandbox/profiles.toml:60` lists the five broker test files
     explicitly. A new `tests/test_broker_git_mcp_server.py` will **not** be
     collected by `bin/gleipnir-sandbox test` (broker profile) until an operator
     adds it to that list. Tier-3, operator-only. Surfaced, not decided.
  2. **The existing broker test's driving pattern is reusable.**
     `commit_changes`/`git_status`/`git_diff`/`push_current_branch` are plain
     functions decorated with `@mcp.tool()` (FastMCP returns the original
     callable), so they are directly importable and callable — verified in
     `test_broker_git_commit_guard.py:128`. The new file reuses this exact
     pattern (real temp repo via `git init` + `symbolic-ref HEAD` +
     `config user.*`, then call the tool function, parse its JSON string).
  3. **`git_status` porcelain parsing has a real untested edge.** Line 191
     skips lines with `len(line) < 4`; line 193 reads `index_status=line[0]`,
     `work_status=line[1]`, `filepath=line[3:]`. Untracked (`??`), staged-only
     (`M ` / `A `), unstaged-only (` M`), both (`MM`), and rename
     (`R  old -> new`) status codes are distinct branches the happy path does
     not cover.
- **New material tradeoff found?** **One (Decision 4), surfaced to the
  operator — the `profiles.toml` amendment is a Tier-3 action a bounded agent
  cannot perform.** It is a hard sequencing gate, not a design choice the
  planner resolves. Everything else is bounded, mechanical test-authoring.

---

## 1. Architect

**Problem (one sentence):** Raise line+branch coverage of
`src/gleipnir/broker/git/mcp_server.py` from 52% to ≥85% by authoring targeted
tests for the currently-unexercised tool functions and error branches
(`git_status` porcelain combinations, `git_diff` argument/error paths,
`push_current_branch` retry/failure/no-branch paths, `commit_changes` staging
and scan-read failure paths, `_run_git` exception branches, `_current_branch`
fallback) — **without duplicating** the already-covered secret-scan and
tool-surface tests and **without changing production code**.

**User:** the maintainers of the `gleipnir-git` broker (and the framework's own
CI/coverage scoreboard, G-4d cost-per-outcome ledger) who need the broker's
correctness-critical wiring — not just its `guards.py` logic — actually
exercised, per the tracked follow-up in `.gleipnir/decisions/broker-mcp.md:140`
("`mcp_server.py` integration coverage gap").

**Measurable success criteria:**

1. `bin/gleipnir-sandbox test` (broker profile) reports **≥85% line coverage
   AND ≥85% branch coverage** for `src/gleipnir/broker/git/mcp_server.py`; any
   residual uncovered line is named and justified in the code agent's report
   (the `if __name__ == "__main__":` guard at lines 416–417 is the one expected
   residual and is pre-justified — it only runs under `python -m …`, not import).
2. Every gap enumerated in Trace §"Coverage gaps (verified)" has at least one
   test that exercises it and asserts the observable contract (the returned
   JSON `success`/`error`/field values), not merely "it ran".
3. All existing broker tests still pass (no regression; the new file adds
   coverage, it does not modify the four existing broker test files).
4. **No production code under `src/gleipnir/broker/git/` is changed** (Decision
   5). If a genuine bug is found, it is surfaced as a new decision, not fixed
   silently.

**Constraints:**

- **Test-authoring only.** No behaviour change to `mcp_server.py`,
  `guards.py`, or any broker module. This is the `test` stage and (since it is
  pure test-authoring against unchanged code) may be the same delegation as
  `code` — see Execution Workflow.
- **No duplication.** Do not re-test the secret-scan refuse/pass paths
  (`test_broker_git_commit_guard.py` T1–T5) or the 4-tool set / force-param /
  hook-bypass surface (`test_broker_tool_surface.py`). New tests target only the
  uncovered functions/branches.
- **Sandbox-only execution.** Tests run via `bin/gleipnir-sandbox test`
  (broker profile) — the only test capability `gleipnir-code` holds. No host
  pytest. Coverage is `--cov=src/gleipnir/broker --cov-branch` (per
  `profiles.toml:62`).
- **Broker profile only.** The new file imports `gleipnir.broker.git.mcp_server`
  (which transitively imports `mcp`), so it must be skip-collected under the
  lean python profile. This is already handled generically for the broker
  suite by `conftest.py` `collect_ignore` **only for the two named files** —
  the new file must be added there too (see Trace edge case E-COLLECT).
- **Real git available in-sandbox.** The broker image
  (`Containerfile.broker`, python:3.12-slim) provides `git`; the existing
  `test_broker_git_commit_guard.py` already relies on real `git init`/`commit`
  in the broker profile, so real-repo fixtures are known-good there.

---

## 2. Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Role |
|---|---|---|---|---|
| **New** coverage test file | new: `tests/test_broker_git_mcp_server.py` | source tree (under `tests/`, outside `.gleipnir/**`) | **bounded `gleipnir-code`** | The deliverable: tests for the uncovered tool functions + error branches. |
| `conftest.py` `collect_ignore` amendment | `tests/conftest.py` (edit) | source tree | **bounded `gleipnir-code`** | Add the new file to `collect_ignore` when `mcp` is absent (so the lean python profile does not abort collection). |
| Target under test (UNCHANGED) | `src/gleipnir/broker/git/mcp_server.py` | source tree | (unchanged) | The 417-line broker server whose coverage is being raised. Read-only for this work. |
| Guard module (UNCHANGED) | `src/gleipnir/broker/git/guards.py` | source tree | (unchanged) | Provides `is_protected_branch`, `precommit_check`; called by the target. Already 96% covered. |
| Broker sandbox profile — **operator amendment** | `.gleipnir/sandbox/profiles.toml` (edit line 60) | **Tier-3 POLICY** | **operator only** | Add `tests/test_broker_git_mcp_server.py` to `[profile.broker].test` so `bin/gleipnir-sandbox test` collects it. **Decision 4 — a code agent cannot write this.** |
| Existing tests (NOT modified) | `tests/test_broker_git_commit_guard.py`, `tests/test_broker_tool_surface.py` | source tree | (unchanged) | Already-covered scope; the new file must not duplicate them. |

### Coverage gaps (verified against the actual source, line-referenced)

Each row is a distinct uncovered function/branch; the "verified" column records
the source lines confirming the branch exists and is reachable.

| Gap | Function | What's uncovered | Source lines (verified) |
|---|---|---|---|
| G1 | `git_status` | branch value + `protected` field via `guards.is_protected_branch`; correct split of `staged`/`unstaged`/`untracked` across porcelain status-code combinations (untracked `??`, staged-only, unstaged-only, both `MM`, rename); the `len(line) < 4` skip; the `clean` flag | 181–211 (parse loop 190–200; `protected` 205; `clean` 206) |
| G2 | `git_diff` | unstaged default (no flags); `staged=True` (`--cached`); `target` ref compare; `file` single-file scoping (`-- <file>`); and the **error path** when `_run_git` fails (returns `{"success": False, "error": ...}`) | 229–243 (arg build 230–236; error branch 239–242) |
| G3 | `push_current_branch` | success on first `push origin <branch>`; **retry-with-`-u`** when the first push fails; **final failure** after both attempts; **"Could not determine current branch"** early-return when `_current_branch` is empty | 393–413 (no-branch 395–398; first push 400; retry 401–402; fail 404–411) |
| G4 | `commit_changes` (paths NOT in commit-guard tests) | per-file `git add <file>` staging **failure**; `git add -A` staging **failure**; "failed to read staged diff for secret-scan" **fail-closed** path; final `git commit` **failure** (e.g. hook rejection surfacing as normal error) | 297–317 (per-file fail 301–308; add-A fail 311–317); scan-read fail 322–334; commit fail 356–365 |
| G5 | `_run_git` | `subprocess.TimeoutExpired` → timed-out error; `FileNotFoundError` → "git executable not found"; generic `Exception` → `str(exc)` | 154–159 |
| G6 | `_current_branch` | fallback-to-`""` when the underlying `_run_git` call fails (`success` falsy) | 162–166 (the `return ""` at 166) |

**Note on G4 vs the commit-guard tests:** `test_broker_git_commit_guard.py`
covers the secret-scan **refuse** (T1/T3/T5) and **pass→commit** (T2/T4) paths,
including the reset-HEAD unstage. It does **not** cover the four *failure*
branches in G4 (staging failures, scan-read failure, commit failure). Those are
new, non-overlapping.

### How each gap is driven (test design — enough for the code agent)

Reuse the `test_broker_git_commit_guard.py` fixture shape: a real temp repo
(`git init`; `git symbolic-ref HEAD refs/heads/main`; `git config user.email`/
`user.name`; one initial commit so HEAD exists), call the tool function
directly, `json.loads` the returned string, assert on the parsed dict. Clear the
`GLEIPNIR_GIT_*` env vars (as the existing file's `_clear_git_env` does) so
tests exercise the default posture unless a test explicitly opts branch
protection on.

- **G1 `git_status`:**
  - Clean repo → `clean: True`, empty lists, `branch == "main"`,
    `protected: False` (default, protection opt-in off).
  - With `GLEIPNIR_GIT_PROTECT_BRANCHES`/`GLEIPNIR_GIT_STRICT` set + branch
    `main` → `protected: True` (drives `guards.is_protected_branch` True arm).
  - Create an untracked file → appears in `untracked`, not `staged`/`unstaged`.
  - `git add` a new file → `staged` only.
  - Modify a tracked file without staging → `unstaged` only.
  - Stage then further-modify the same file → appears in **both** `staged` and
    `unstaged` (index vs worktree differ; covers both `if` arms at 197/199).
  - (Optional, robustness) a renamed file (`git mv` + status `R  old -> new`)
    to confirm the parser does not crash on the arrow form — assert it does not
    raise and returns a dict (documents current behaviour; not a correctness
    claim about rename splitting).
- **G2 `git_diff`:**
  - Modify a tracked file (unstaged) → default call returns `success: True`,
    non-empty `diff`.
  - Stage it → `staged=True` returns the staged diff; unstaged default now
    empty diff.
  - `target="main"` on a repo with a divergent ref/commit → target compare path
    (arg `["diff","main"]`) returns `success: True`.
  - `file="<one file>"` → single-file scoping (`["diff","--",file]`).
  - **Error path:** call `git_diff(repo_dir=<non-repo dir>)` or with a bogus
    `target` so `_run_git` returns `success: False`; assert the returned JSON is
    `{"success": False, "error": <stderr or error>}` (covers 239–242). A
    non-git directory makes `git diff` exit non-zero deterministically.
- **G3 `push_current_branch`** (no network — use a **local bare repo** as
  `origin`, or `monkeypatch` `_run_git`):
  - **Recommended:** `monkeypatch mcp_server._run_git` with a stub that returns
    scripted results by argv, so all four paths are deterministic and offline:
    - first `["push","origin",branch]` succeeds → `{"success": True, "branch": …}`.
    - first push fails, `["push","-u","origin",branch]` succeeds → success
      (covers the retry arm 401–402).
    - both fail → `{"success": False, "error": …}` (covers 404–411).
    - `_current_branch` returns `""` (stub or detached-HEAD repo) → early
      `{"success": False, "error": "Could not determine current branch"}`
      (395–398).
  - *(Alternative for the two success/retry arms:* a real local bare repo added
    as `origin` — `git init --bare` in another tmp dir, `git remote add origin` —
    lets a real `push` succeed offline. The `monkeypatch` route is simpler and
    covers all four arms uniformly, so it is the recommended primary; a real
    bare-repo push may be added as a bonus integration test if time allows.)
- **G4 `commit_changes` failure paths** (`monkeypatch mcp_server._run_git`
  scripted by argv, OR provoke with a real repo where possible):
  - per-file `add` failure: `files="does-not-exist.txt"` in a real repo makes
    `git add does-not-exist.txt` fail → `{"success": False, "error":
    "Failed to stage 'does-not-exist.txt': …"}` (301–308). *(Verify in-sandbox:
    modern git may treat a nonexistent pathspec as an error — if it does not,
    fall back to a scripted `_run_git` stub returning `success: False` for the
    `["add", f]` argv.)*
  - `add -A` failure: scripted `_run_git` stub returns `success: False` for
    `["add","-A"]` → `{"success": False, "error": "Failed to stage: …"}`
    (311–317).
  - scan-read failure (fail-closed): scripted stub makes `["diff","--cached"]`
    return `success: False` → `{"success": False, "error": "Failed to read
    staged diff for secret-scan: …"}` (322–334). Assert **no commit** happened.
  - final `commit` failure: scripted stub lets staging + diff + name-only +
    `precommit_check` pass but makes `["commit","-m",message]` return
    `success: False` (simulating a hook rejection) → `{"success": False,
    "error": <stderr or "Commit failed">}` (356–365). A real alternative:
    install a repo `pre-commit` hook that exits non-zero, then commit a benign
    file — the broker's `git commit` fires the hook and surfaces the rejection
    (this also exercises the "hooks still run" invariant). Prefer the scripted
    stub for determinism; the real-hook variant is a strong optional addition.
- **G5 `_run_git` exception branches** (`monkeypatch subprocess.run` inside
  `mcp_server`, driven through a public call so the contract is asserted):
  - `TimeoutExpired`: monkeypatch `subprocess.run` to raise
    `subprocess.TimeoutExpired(cmd, timeout)`; call `git_status`; assert the
    returned dict is `{"success": False, "error": "git command timed out after
    30s"}` (154–155). *(Alternatively `_run_git(["...","--"], timeout=0)` if a
    real 0s timeout reliably raises — the monkeypatch is deterministic.)*
  - `FileNotFoundError`: monkeypatch `subprocess.run` to raise
    `FileNotFoundError`; assert `{"success": False, "error": "git executable
    not found"}` (156–157).
  - generic `Exception`: monkeypatch `subprocess.run` to raise a plain
    `RuntimeError("boom")`; assert `{"success": False, "error": "boom"}`
    (158–159). `_run_git` may be called directly here (it is module-level) since
    the goal is the exception mapping, not a tool contract — but calling via a
    tool (e.g. `git_status`) additionally proves the tool degrades gracefully.
  - **Screen-first note:** `_run_git` first calls `_rejects_hook_bypass`; use a
    benign argv (e.g. `["status","--porcelain"]`) so the bypass screen returns
    None and execution reaches the `subprocess.run` try-block.
- **G6 `_current_branch` fallback:** monkeypatch `mcp_server._run_git` to
  return `{"success": False, "error": "x"}` for `["branch","--show-current"]`;
  assert `_current_branch(...)` returns `""` (166). This is also exercised
  transitively by the G3 "no branch" case.

### Bug-hunt result (Trace obligation, Decision 5)

Read the full 417-line target. **No production bug found.** Every branch in the
gap list is reachable and returns the documented structured contract:
`_run_git`'s three exception handlers, `git_status`'s porcelain parse, `git_diff`'s
error branch, `push_current_branch`'s retry/fail/no-branch arms, and
`commit_changes`'s staging/scan-read/commit failure arms are all sound. One
benign observation (not a bug): `git_status` line 191 `len(line) < 4` combined
with `filepath = line[3:]` assumes the standard porcelain `XY <path>` layout
(status chars at 0–1, space at 2, path from 3); rename lines (`R  old -> new`)
are stored with the whole ` old -> new` as `filepath`. This is existing
behaviour, correct for the tool's reporting purpose, and only **documented** by
the optional rename test — **not** changed. **If `gleipnir-code` uncovers a
genuine bug while writing a test, it must STOP and surface it as a new decision
(do not weaken the test, do not patch silently).**

### Edge cases

1. **E-COLLECT — profile collection (Decision 4, hard gate).** The new file
   imports `mcp` transitively; the broker profile's `test` command
   (`profiles.toml:60`) is an **explicit file list** that does not include the
   new file. Two things must both happen: (a) **operator** adds
   `tests/test_broker_git_mcp_server.py` to `[profile.broker].test`; (b)
   **code agent** adds the same file to `conftest.py` `collect_ignore` so the
   lean python profile skip-collects it. Without (a) the new tests never run in
   the sandbox; without (b) the python-profile run aborts at collection.
2. **Detached HEAD** for the `_current_branch` empty path: `git branch
   --show-current` prints empty on detached HEAD — a real way to drive G6/G3
   without monkeypatch (checkout a commit hash). Monkeypatch is simpler and
   preferred; noted as an alternative.
3. **`monkeypatch` target scoping:** patch `mcp_server._run_git` and
   `mcp_server.subprocess.run` (the names as bound in the target module), not
   the global `subprocess` — patch where it is looked up.
4. **Env isolation:** every test that does not intend branch protection must
   clear `GLEIPNIR_GIT_*` (reuse the existing `_clear_git_env` helper shape) so
   default-posture assertions hold; the one protected-branch `git_status` test
   sets them explicitly via `monkeypatch.setenv`.
5. **No secret leakage regression:** the G4 tests use benign content only (the
   secret-scan tests already own the secret path); do not plant real-shaped
   secrets in the new file except where explicitly asserting redaction (not
   needed here — that is the existing file's job).

---

## 3. Link — what must be validated BEFORE building

Every fact below was re-read from the actual files this session:

- **L1 (target contract).** `mcp_server.py` read in full (417 lines); the six
  gap functions and their branches confirmed at the line numbers cited in
  Trace. The tool functions are directly callable (FastMCP returns the wrapped
  function) — confirmed by the existing `test_broker_git_commit_guard.py:128`
  calling `mcp_server.commit_changes(...)` directly.
- **L2 (no duplication).** `test_broker_git_commit_guard.py` (T1–T5) covers the
  secret-scan refuse/pass/reset paths; `test_broker_tool_surface.py` covers the
  4-tool set, force-param absence, and `_rejects_hook_bypass`. The new file
  targets only the six gaps, which do **not** overlap those.
- **L3 (guard API used by the target).** `guards.is_protected_branch(branch)`
  (returns False unless protection opted in) and `guards.precommit_check(branch,
  diff, staged_files)` confirmed at `guards.py:101` and `:252`. The
  `GLEIPNIR_GIT_PROTECT_BRANCHES`/`GLEIPNIR_GIT_STRICT` env toggles gate the
  `protected` field.
- **L4 (broker profile — MEASUREMENT & COLLECTION).** `profiles.toml`
  `[profile.broker]` uses `image = gleipnir-sandbox-broker@sha256:…`
  (`--network=none`, digest-pinned), runs `pytest` over an **explicit
  five-file list** (line 60), and sets coverage
  `--cov=src/gleipnir/broker --cov-branch --cov-report=term-missing` (line 62).
  **Consequence:** the new file must be added to line 60 (Tier-3 operator) or it
  is not collected — the hard gate in Decision 4 / E-COLLECT.
- **L5 (conftest collect_ignore).** `tests/conftest.py:27–30` skip-collects
  `test_broker_tool_surface.py` and `test_broker_git_commit_guard.py` when `mcp`
  is absent. The new file must be added to that `collect_ignore` list (code
  agent, `tests/` is in-grant).
- **L6 (real git in the broker image).** The broker image is python:3.12-slim
  with `git` present (the existing commit-guard test does real `git init`/
  `commit` under this profile and passes — per `broker-mcp.md:119` "34 passed").
  So real-temp-repo fixtures are known-good in-sandbox.
- **L7 (code agent capability).** `gleipnir-code` may `edit "*"` except
  `.gleipnir/**`/`.git/**`/`preflight/**`; `tests/**` and `conftest.py` are
  in-grant. Its only test capability is `bin/gleipnir-sandbox test|lint`
  (exact-match). It holds no git. Confirmed from `gleipnir-code.md`.

**Gate rule:** L4 is a hard ordering gate — the operator's `profiles.toml:60`
amendment (Assemble Step 0) must land before `bin/gleipnir-sandbox test`
(broker profile) can measure the new file's coverage. The code agent can author
and self-review the tests before that, but the acceptance coverage number is
only produced once the file is collected.

---

## 4. Assemble — intended build order

Ordered so (i) the Tier-3 collection prerequisite is named up front, (ii) tests
are authored against the read contract, and (iii) coverage is measured in the
sandbox and any residual justified.

**Step 0 — [Tier-3 / operator] Amend `profiles.toml` collection list.** Add
`"tests/test_broker_git_mcp_server.py"` to `[profile.broker].test` (line 60) so
`bin/gleipnir-sandbox test` (broker profile) collects it. **Operator-only
(Tier-3 POLICY, agent-unwritable).** This is the E-COLLECT gate; without it the
new tests are dead. *(If the operator prefers, the list could instead be
broadened to a `tests/test_broker_*.py` glob — but that is an operator design
call on the Tier-3 file, explicitly out of the code agent's scope; the planner
only requires the new file be collectible.)*

**Step 1 — [code] Author `tests/test_broker_git_mcp_server.py`** covering G1–G6
per Trace §"How each gap is driven". Reuse the existing file's fixture pattern
(real temp repo, direct tool-function calls, `json.loads`, `_clear_git_env`).
Use `monkeypatch` of `mcp_server._run_git` / `mcp_server.subprocess.run` only
for the branches not reliably reachable with real git (G3 push arms, G4 staging/
scan/commit failures, G5 exceptions, G6 fallback). Add a module docstring naming
the scope and the D8-style note that `profiles.toml` collection is an operator
prerequisite (mirroring `test_broker_git_commit_guard.py`'s header).

**Step 2 — [code] Amend `tests/conftest.py` `collect_ignore`** to append
`"test_broker_git_mcp_server.py"` (so the lean python profile skip-collects it
when `mcp` is absent).

**Step 3 — [code] Run `bin/gleipnir-sandbox test` (broker profile)** and read
the term-missing coverage for `src/gleipnir/broker/git/mcp_server.py`. Iterate
on tests until line+branch ≥85%. The `if __name__ == "__main__":` block
(416–417) is expected to remain uncovered and is pre-justified (import-time
never runs it).

**Step 4 — [code] Report** pass count + line% + branch% for the target file,
name any residual-uncovered line with justification, and confirm no production
code changed.

**Step 5 — [quality] Blast-radius review** against this plan's Stress-test
checks (no duplication, no production change, gaps covered, target met).

**Step 6 — [git-ops] Commit** the new test file and the `conftest.py` edit.

**Assemble step order (summary):**
`0 (Tier-3 operator: profiles.toml collection amendment) →
1 (code: author test_broker_git_mcp_server.py, G1–G6) →
2 (code: conftest.py collect_ignore) →
3 (code: sandbox test + iterate to ≥85% line+branch) →
4 (code: report) → 5 (quality review) → 6 (git-ops commit)`

---

## 5. Stress-test — acceptance checks

Concrete, checkable criteria the result is validated against.

- **A1 (coverage target met — measured).** `bin/gleipnir-sandbox test` (broker
  profile) term-missing output shows `src/gleipnir/broker/git/mcp_server.py` at
  **≥85% line AND ≥85% branch**. Pass = the measured number in the sandbox
  report, not a claim. Any uncovered line is enumerated with a one-line
  justification; only lines 416–417 (`if __name__ == "__main__":` / `mcp.run`)
  are acceptable residuals without further work.
- **A2 (every gap exercised).** There is at least one test, with a contract
  assertion, for each of: G1 `git_status` (branch, `protected` True arm,
  untracked/staged-only/unstaged-only/both porcelain codes, `clean`); G2
  `git_diff` (default/`--cached`/`target`/`file` + error branch); G3
  `push_current_branch` (first-push success, `-u` retry, both-fail, no-branch);
  G4 `commit_changes` (per-file add fail, `add -A` fail, scan-read fail-closed,
  commit fail); G5 `_run_git` (`TimeoutExpired`, `FileNotFoundError`, generic
  `Exception`); G6 `_current_branch` empty fallback.
- **A3 (no duplication).** The new file does **not** re-test the secret-scan
  refuse/pass paths or the tool-surface/hook-bypass assertions already owned by
  `test_broker_git_commit_guard.py` and `test_broker_tool_surface.py`. Verified
  by reading the new file against those two.
- **A4 (no production change).** `git`-diff of `src/gleipnir/broker/**` is
  empty for this work (verifiable at the git stage). No behaviour was altered;
  only `tests/test_broker_git_mcp_server.py` (new) and `tests/conftest.py`
  (collect_ignore append) changed.
- **A5 (no regression).** The full broker suite (existing five files + the new
  one) passes under the broker profile; the lean python profile still runs
  green with the new file skip-collected (conftest amendment working).
- **A6 (collection prerequisite honoured).** The new file appears in
  `[profile.broker].test` (operator Step 0) — otherwise A1 cannot be produced.
  This check confirms the Tier-3 gate was satisfied before the coverage number
  is trusted.
- **A7 (bug-surfacing discipline).** If any test could only pass by changing
  production code, the code agent STOPPED and surfaced it as a new decision
  (Decision 5) rather than editing `mcp_server.py`. Pass = either no production
  change was needed (expected) or a surfaced decision exists.

---

## 6. Execution Workflow

**For the orchestrator sequencing this plan.** ATLAS/GOTCHA already ran (this
plan). Pipeline from here: `spec-review → test/code → quality → git`. Because
this is **pure test-authoring against existing, unchanged production code**, the
`test` and `code` stages **may be a single `gleipnir-code` delegation** (there
is no production code to write after the tests; the tests are the deliverable).
The one Tier-3 action (Step 0, `profiles.toml`) is an **operator** step that
must precede the coverage measurement.

### Operator-vs-code-agent split (explicit)

| # | Task | Zone | Assemble step |
|---|---|---|---|
| 0 | Add `tests/test_broker_git_mcp_server.py` to `[profile.broker].test` in `.gleipnir/sandbox/profiles.toml` | **Tier-3 / operator only** | 0 |
| 1 | Author `tests/test_broker_git_mcp_server.py` (G1–G6) | bounded `gleipnir-code` | 1 |
| 2 | Append the new file to `tests/conftest.py` `collect_ignore` | bounded `gleipnir-code` | 2 |
| 3 | Run `bin/gleipnir-sandbox test` (broker profile); iterate to ≥85% line+branch | bounded `gleipnir-code` | 3 |
| 4 | Report pass count + line% + branch% + residual justification | bounded `gleipnir-code` | 4 |
| 5 | Quality blast-radius review vs Stress-test | quality-reviewer | 5 |
| 6 | Commit the two files | git-ops | 6 |

### Notes the implementing agent needs (so it does not rediscover context)

- **Driving the tools:** import `from gleipnir.broker.git import mcp_server`;
  the tool functions are directly callable (`mcp_server.git_status(...)`,
  `.git_diff(...)`, `.commit_changes(...)`, `.push_current_branch(...)`), each
  returns a **JSON string** — `json.loads` it. Copy the `repo` fixture and the
  `_git`/`_clear_git_env` helpers' shape from
  `tests/test_broker_git_commit_guard.py` (do not import from it; replicate the
  small helpers, or factor a shared local helper within the new file).
- **Monkeypatch targets:** patch `mcp_server._run_git` (module-level) for the
  scripted-argv paths (G3, G4, G6); patch `mcp_server.subprocess.run` for the
  G5 exception injections. `_run_git` calls `_rejects_hook_bypass` first, so use
  a benign argv when driving G5 through it.
- **Env:** clear `GLEIPNIR_GIT_STRICT`, `GLEIPNIR_GIT_PROTECT_BRANCHES`,
  `GLEIPNIR_GIT_CHECK_DATA_FILES`, `GLEIPNIR_GIT_PROTECTED_BRANCHES` in every
  test that assumes default posture; set them explicitly only for the G1
  `protected: True` test.
- **Run command (exact):** `bin/gleipnir-sandbox test` resolves the broker
  profile per `profiles.toml`; coverage is emitted automatically
  (`--cov=src/gleipnir/broker --cov-branch --cov-report=term-missing`). Read the
  `mcp_server.py` row of the term-missing table for the number and the
  uncovered-line list.
- **If a test only passes by editing `mcp_server.py`:** STOP, report the
  suspected bug as a new decision (do not weaken the test, do not patch). Per
  Decision 5, none is expected.
