# Plan: bin/* executable-bit prerequisite validation (B + C + D)

**Stage:** plan. **Planned FROM converged brief:**
`.gleipnir/plans/bin-executable-bit-fix-brainstorm.md` (operator-converged:
Build B + C + D; decline A). **Author:** gleipnir-plan. This plan does not
re-decide the operator-converged approach; it plans the bounded work each of the
three selected pieces defines, on the two timelines the brief mandates.

**Two independent timelines, three phases, clearly separated:**

- **Phase 1 — B** (`tests/test_bin_executable.py`): agent-buildable NOW via the
  normal pipeline (plan → spec-review → test/code → quality → git). No Tier-3
  handoff.
- **Phase 2 — C** (`.gleipnir/plugins/git-guard.ts` + `tests/test_git_guard.mjs`):
  Tier-3, operator-authored. This plan produces a **ready-to-apply exact diff**;
  it is NOT executed by any agent. Deferred to an operator build-mode session.
- **Phase 3 — D** (decision-record note): Tier-3, operator-authored. This plan
  produces the **exact proposed text**; deferred to the same operator session.

Phases 2 and 3 are ready-to-apply artifacts, not work items for the pipeline.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Which defense layers to build | B + C + D | A (checkout/merge hook) | Operator-converged in the brief (Decision Analysis / bias check). A has weakest coverage, no help on the fresh-clone vector it targets, masks root cause. |
| 2 | Detection surface for B | New `tests/test_bin_executable.py`, auto-collected via `testpaths=["tests"]` | CI job; standalone script | Brief constraint: no CI exists; `pyproject.toml` `testpaths=["tests"]` makes a new test file real today with zero new infra. |
| 3 | What B asserts | **Committed** git mode via `git ls-files -s bin/` (mode field), executable-bit check | Working-tree `os.access(path, os.X_OK)` only | Brief + `s2-g1-closure.md` rationale: `core.fileMode false` hides a wrong committed mode from a working-tree probe. Must catch the config-hidden regression, not just the working-tree symptom. |
| 4 | B behaviour when no usable git tooling / work tree is present | **Skip** (`pytest.skip`), not fail | Hard fail | The sandbox (`bin/gleipnir-sandbox test`) bind-mounts the whole repo root `:ro` (runtime.py L306-322) — `.git` IS present — but the `python:3.12-slim` base image likely has no `git` binary, so a `git` invocation fails there; a hard `git`-dependent assert would break the whole in-sandbox suite. The guard keys off the OBSERVABLE SYMPTOM (git missing / not a usable work tree in this environment), not any specific mount mechanism. Meaningful on host (usable git); clean skip where git tooling is absent. Resolves brief Open Question #1. |
| 5 | B mode-assertion granularity | Check the **executable bit** within the tracked mode (`int(mode,8) & 0o111`), not exact `== "100755"` equality | Exact `100755` string equality | Brief Open Question #2 recommends tolerating legitimate `100755` variants; an executable-bit mask is the robust invariant. (In practice tracked regular files are `100644`/`100755`; the mask cleanly separates them and is future-proof.) |
| 6 | B failure-message content | Names the exact offending file + both exact fix commands (`chmod +x <f> && git add <f>` and `git update-index --chmod=+x <f>`) | Generic "not executable" | Brief is explicit: the message must be actionable so a future occurrence is a one-line fix, not a multi-step investigation. |
| 7 | C: distinguish tool-broken from policy-reject | Pre-check `fs.accessSync(cli, fs.constants.X_OK)` before spawning + distinct `PreflightUnavailable extends GitGuardAbort` subclass | Inspect `res.error.code` post-spawn only; message-only distinction | Pre-check gives the cleanest, deterministic message (ENOENT and EACCES both surface as "unavailable" uniformly before any spawn); a subclass lets tests/callers branch (brief Open Questions #3, #4). Fail-closed preserved: still throws, still aborts. |
| 8 | D: home of the decision note | **New file** `.gleipnir/decisions/bin-executable-bit.md` | Amend `broker-mcp.md` or `s2-g1-closure.md` | Neither existing record is about executable-bit durability: `broker-mcp.md` is the broker tool surface; `s2-g1-closure.md` is the boundary preflight. The topic is distinct and small; a focused new record is cleaner than diluting either. (Brief Open Question #5 — implementer's call.) |

---

## Architect

**Problem (one sentence).** Nothing prevents or cheaply diagnoses a
non-executable (or otherwise broken) `bin/*` entrypoint, which — because the
always-active `git-guard.ts` gate shells out to `bin/gleipnir-preflight
config-scan` before every broker git write — silently locks the broker out with
an abort indistinguishable from a genuine policy rejection.

**User.** `gleipnir-code` (runs the test suite) and any operator/agent who hits
the broker gate; the operator who applies the Tier-3 pieces.

**Measurable success criteria.**
1. A `bin/*` file committed with a non-executable mode causes a **loud, named,
   actionable** test failure during a normal host test run (Phase 1). ✔ when
   `tests/test_bin_executable.py` fails naming the file + both fix commands.
2. That test **passes** today (both tracked `bin/*` files are `100755` after
   `9645974`) and **skips cleanly** where no usable git tooling is present
   (e.g. in-sandbox, where the base image likely lacks a `git` binary).
3. (Phase 2, deferred) A broken/missing preflight CLI at the gate produces a
   **distinct** "tool broken — chmod this" message/type, not the REFUSE message,
   while still aborting fail-closed. ✔ when the new `test_git_guard.mjs` case
   asserts the distinct type/message on the CLI-missing/non-exec path.
4. (Phase 3, deferred) A decision record captures: durable fix = committed index
   mode (`git update-index --chmod=+x`, applied `9645974`); `.gitattributes` has
   no portable executable-bit directive (explicit caveat); verify `core.fileMode`
   not disabled.

**Constraints (from brief; verified against code).**
- **Fail-closed is invariant.** Phase 2 changes only the *message/type* of the
  abort, never the decision to abort (git-guard.ts L39-42, L85-90).
- **Capability boundary.** The agent may write `tests/**` (Phase 1). It may NOT
  write `.gleipnir/plugins/**` (Tier-3; git-guard.ts header L12-14) nor
  `.gleipnir/decisions/**` (Tier-3; enforcement path set in `s2-g1-closure.md`
  L48). Phases 2–3 are operator-applied.
- **No CI**; `testpaths=["tests"]` (pyproject.toml L18) is the real collection
  path.
- **Sandbox may lack usable git tooling** — it bind-mounts the whole repo root
  `:ro` (runtime.py L306-322, so `.git` IS present) but the `python:3.12-slim`
  base image likely has no `git` binary; Phase 1 test must skip on the
  observable symptom (git unusable), not on an assumed `.git` exclusion.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Status | Tier / writer |
|---|---|---|---|
| B test (NEW) | `tests/test_bin_executable.py` | to-be-created | source tree; `gleipnir-code` |
| C plugin edit (READY-TO-APPLY diff, below) | `.gleipnir/plugins/git-guard.ts` | exists (161 lines, read) | Tier-3; operator only |
| C test case (READY-TO-APPLY, below) | `tests/test_git_guard.mjs` | exists (165 lines, read) | source tree, but applied WITH the plugin edit by the operator (the case exercises the new subclass) |
| D decision record (READY-TO-APPLY text, below) | `.gleipnir/decisions/bin-executable-bit.md` | to-be-created | Tier-3; operator only |
| Enumeration inputs | `bin/gleipnir-preflight`, `bin/gleipnir-sandbox` (the two tracked `bin/*`) | exist, mode `100755` post-`9645974` | — |

### Integrations map

- **`testpaths=["tests"]`** (pyproject.toml L18) auto-collects the new B test —
  it runs inside every `pytest`/`bin/gleipnir-sandbox test` invocation
  `gleipnir-code` already performs. No wiring change.
- **Sandbox mount reality** (runtime.py L306-322): the WHOLE repo root is
  bind-mounted `:ro` at `/work` (so `.git` IS present in-sandbox — there is no
  `.git`-specific exclusion; the existing
  `test_build_run_argv_never_mounts_credentials_git_or_gleipnir` only asserts the
  argv STRING omits `.git`, not that the tree is excluded), plus
  `--network=none`. The likely reason `git` fails in-sandbox is the absence of a
  `git` binary in the `python:3.12-slim` base image — a different mechanism with
  different implications if the image is swapped. → B must detect absence of
  usable git tooling / a usable work tree (the observable symptom) and
  `pytest.skip`, not fail. Meaningful coverage is on the host run (usable git);
  the sandbox run then simply skips.
- **`git ls-files -s bin/`** output format: `<mode> <objectname> <stage>\t<path>`
  — the mode is the first whitespace-delimited field (e.g. `100755`). B parses
  that field. `git ls-files bin/` alone gives the tracked path set (used to
  detect the "no tracked bin files" edge). The `_git()` subprocess helper
  convention is established in `tests/test_broker_git_commit_guard.py` L65-81
  (subprocess.run, capture_output, timeout, assert on returncode).
- **git-guard gate flow** (Phase 2 target): `runConfigScan` (L79-98) does
  `spawnSync(cli, ["config-scan"], …)`; on `res.error` it throws
  `GitGuardAbort` at L87-89 — the SAME class thrown for REFUSE at L111-116 and
  unexpected-code at L120-122. Phase 2 splits the `res.error` (and a pre-check)
  path into a distinct `PreflightUnavailable` subclass.

### Edge cases

- **No git in PATH / not a work tree (sandbox):** skip (Decision 4). Detect via
  `git rev-parse --is-inside-work-tree` returning non-zero or `git` raising
  `FileNotFoundError`.
- **No tracked files under `bin/`:** `git ls-files bin/` empty. Not an error;
  skip or trivially pass (nothing to assert). Prefer `pytest.skip("no tracked
  bin/* files")` so the "0 files silently passes" state is visible, not a green
  no-op.
- **`core.fileMode false` hiding a wrong committed mode:** exactly why B reads
  `git ls-files -s` (the index/committed mode), not the working tree
  (Decision 3).
- **Submodule / gitlink mode `160000`:** not applicable under `bin/` today. The
  test restricts its check to regular blobs (`mode.startswith("100")`), so a
  gitlink is skipped rather than flagged — the `chmod +x` fix would not apply to
  it anyway.
- **Symlink mode `120000`:** plausible under `bin/` (unlike a gitlink). The same
  `mode.startswith("100")` restriction excludes symlinks from the mask, avoiding
  a false-positive on a file for which the `chmod +x` / `git update-index
  --chmod=+x` fix commands don't meaningfully apply.
- **Phase 2 — EACCES vs ENOENT:** the pre-check `fs.accessSync(cli, X_OK)`
  throws for BOTH missing and non-executable, so the distinct message covers
  both "not executable" and "not present" uniformly, before any spawn.
- **Phase 2 — fail-closed on the new path:** `PreflightUnavailable extends
  GitGuardAbort`, and the hook's `catch` (L154) already re-throws any
  `GitGuardAbort` instance — so the subclass is caught and aborts unchanged. No
  allow path is introduced.

---

## Link (validated before building)

- **Read in full:** the brief; `git-guard.ts` (exact throw sites L85-90 /
  L110-116 / L117-122 confirmed); `tests/test_git_guard.mjs` (existing "CLI
  missing" test L122-129 asserts `/could not run|fail-closed/` — the current
  message the new case must be distinguished from); `pyproject.toml`
  (`testpaths`); the two candidate decision homes (`broker-mcp.md`,
  `s2-g1-closure.md`) — neither is about executable-bit durability, confirming
  Decision 8.
- **Confirmed test convention:** `tests/test_broker_git_commit_guard.py`
  `_git()` helper (subprocess + assert) is the in-repo pattern B should mirror.
- **Confirmed sandbox mount reality directly** (runtime.py L306-322): the whole
  repo root is bind-mounted `:ro` (so `.git` IS present in-sandbox); the likely
  cause of a `git` failure there is the absence of a `git` binary in the base
  image, NOT a `.git` exclusion. This is the load-bearing basis for keying
  Phase 1's skip off the observable symptom (git unusable), not off a mount
  claim.
- **Confirmed** both tracked `bin/*` files exist and (per brief `9645974`) are
  `100755`, so B passes today on host.

**No material tradeoff requiring re-convergence surfaced during planning.** The
approach (B+C+D, decline A) and the handoff-timing split were operator-converged
in the brief; every open question the brief flagged (enumeration source, mode
granularity, subclass vs message, pre-check vs post-error, new-file vs
amendment) is an *implementation* choice within the bounded work, resolved above
in the Decisions index — none is a material design tradeoff that changes the
approach. Nothing to route back to the operator.

---

## Assemble (build order)

### Phase 1 — B (NOW, normal pipeline)

1. **Author `tests/test_bin_executable.py`** (test-first; it IS the deliverable —
   no separate implementation file). Structure:

   - Module-level helper to detect a usable git work tree; if absent, set a
     skip. Signature:
     ```python
     def _git(args: list[str]) -> subprocess.CompletedProcess: ...
         # runs ["git", *args] at repo root (Path(__file__).resolve().parents[1]),
         # capture_output=True, text=True, timeout=30; returns the completed proc
         # (does NOT assert returncode — callers decide skip vs read).

     def _tracked_bin_modes() -> list[tuple[str, str]]:
         # returns [(mode, path), ...] parsed from `git ls-files -s bin/`.
         # Each ls-files -s line: "<mode> <sha> <stage>\t<path>".
         # mode = line.split()[0]; path = line.split("\t", 1)[1].
     ```
   - Skip guard (module scope or fixture): run `git rev-parse
     --is-inside-work-tree`; if `git` is missing (`FileNotFoundError`) or the
     command returns non-zero / not "true", `pytest.skip("no usable git tooling /
     not inside a usable git work tree in this environment (e.g. no git binary in
     the sandbox base image) — bin/* committed-mode check skipped")`.
   - Test function:
     ```python
     def test_tracked_bin_files_are_committed_executable():
         entries = _tracked_bin_modes()   # skips upstream if no git
         if not entries:
             pytest.skip("no tracked bin/* files to check")
         # Only regular blobs (mode 100xxx) carry a meaningful executable bit and
         # a fixable +x mode. Skip symlinks (120000) and gitlinks (160000): the
         # `& 0o111` mask would false-positive them, and `chmod +x`/
         # `git update-index --chmod=+x` don't meaningfully apply to those types.
         non_exec = [(mode, path) for mode, path in entries
                     if mode.startswith("100") and not (int(mode, 8) & 0o111)]
         assert not non_exec, _format_failure(non_exec)
     ```
     (May be expressed as a `@pytest.mark.parametrize` over `_tracked_bin_modes()`
     collected at import time instead of a single loop — either is acceptable;
     the parametrize form names the offending file as the failing case id. If
     parametrizing, collect the entries in a module-level call guarded so import
     never raises when git is absent — fall back to an empty list and let the
     skip guard fire.)
   - `_format_failure(non_exec)` builds the actionable message, e.g.:
     ```
     Tracked bin/* file(s) committed WITHOUT the executable bit — the always-active
     git-guard gate shells out to bin/gleipnir-preflight and will fail-closed on a
     non-executable entrypoint, blocking ALL broker commits/pushes. Fix each file:
       chmod +x <path> && git add <path>
       # or, mode-only (no content change):
       git update-index --chmod=+x <path>
     Offending: <mode> <path>[, ...]
     Note: this checks the COMMITTED mode (git ls-files -s), so `core.fileMode
     false` cannot hide the regression.
     ```
2. **Run** `bin/gleipnir-sandbox test` (skips) and a host `pytest` (passes) to
   confirm both success criteria 1–2. On host today: green (both bin files
   100755). To prove the failure path, a reviewer may transiently
   `git update-index --chmod=-x bin/gleipnir-preflight` in a scratch checkout
   and confirm the named, actionable failure — NOT committed.
3. Route through **spec-review → quality → git** as the normal pipeline.

### Phase 2 — C (DEFERRED, operator build-mode; ready-to-apply)

Applied by the operator, together, in one session (the test case depends on the
new subclass export). **Exact diffs below.**

**2a. `.gleipnir/plugins/git-guard.ts`**

Add the subclass after `class GitGuardAbort extends Error {}` (currently L74).
It MUST be `export`ed — the conformance test below imports it:
```ts
class GitGuardAbort extends Error {}

// Distinct from GitGuardAbort-for-REFUSE: the preflight TOOL itself is broken /
// missing / not executable — a broken PREREQUISITE, not a policy rejection.
// Still a GitGuardAbort subclass so the hook's fail-closed catch (below) aborts
// exactly as before; the subclass only lets tests/callers tell the two apart.
// Exported (alongside runConfigScan/decideFromExit) so the test can import it.
export class PreflightUnavailable extends GitGuardAbort {}
```

Change `runConfigScan` (currently L79-98) to pre-check executability and to map
a spawn `res.error` to the new subclass. Replace the body from the `const cli =`
line through the `res.error` block:
```ts
export function runConfigScan(directory: string): { code: number; stderr: string } {
  const cli = join(directory, PREFLIGHT_REL)
  // Pre-check: is the preflight tool present AND executable? A non-executable or
  // missing CLI is a BROKEN PREREQUISITE, not a policy rejection — surface it
  // distinctly (still fail-closed) so it is a one-line fix, not a multi-step
  // investigation. Covers both ENOENT (missing) and EACCES (not +x) uniformly.
  try {
    accessSync(cli, constants.X_OK)
  } catch {
    throw new PreflightUnavailable(
      `git-guard: preflight tool '${cli}' is missing or not executable — run ` +
        `'chmod +x ${PREFLIGHT_REL}' (or 'git update-index --chmod=+x ${PREFLIGHT_REL}' ` +
        `to fix the committed mode). This is a BROKEN PREREQUISITE, not a policy ` +
        `rejection; fail-closed.`,
    )
  }
  const res = spawnSync(cli, ["config-scan"], {
    cwd: directory,
    encoding: "utf8",
  })
  if (res.error) {
    // Spawn still failed after the pre-check (race / exotic error) — treat as a
    // broken prerequisite too, distinct from a policy REFUSE. Fail-closed.
    throw new PreflightUnavailable(
      `git-guard: could not run '${cli} config-scan' (${res.error.message}); ` +
        `broken prerequisite, NOT a policy rejection; fail-closed`,
    )
  }
  // spawnSync sets status to null if the process was killed by a signal.
  if (res.status === null) {
    throw new GitGuardAbort(
      `git-guard: '${cli} config-scan' terminated by signal ${res.signal}; fail-closed`,
    )
  }
  return { code: res.status, stderr: res.stderr ?? "" }
}
```
And add the imports (currently L51-52 import only `spawnSync` and `join`):
```ts
import { spawnSync } from "node:child_process"
import { accessSync, constants } from "node:fs"
import { join } from "node:path"
```

*Fail-closed proof:* `PreflightUnavailable extends GitGuardAbort`; the hook's
`catch` at L154 does `if (err instanceof GitGuardAbort) throw err` — so the new
subclass is re-thrown and the git op aborts exactly as today. No new allow path.

**2b. `tests/test_git_guard.mjs`** — add the import and two cases. Update the
import line (currently L21):
```js
import { GitGuard, decideFromExit, runConfigScan, PreflightUnavailable } from "../.gleipnir/plugins/git-guard.ts"
```
Add a helper that builds a repo whose stub CLI exists but is NOT executable
(next to `makeRepoNoStub`, after L45):
```js
// A temp repo whose bin/gleipnir-preflight EXISTS but is NOT executable — the
// exact regression that locked out the broker (committed mode 100644).
function makeRepoNonExecStub() {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-git-guard-noexec-"))
  mkdirSync(join(dir, "bin"), { recursive: true })
  const stub = join(dir, "bin", "gleipnir-preflight")
  writeFileSync(stub, `#!/bin/sh\nexit 0\n`)
  chmodSync(stub, 0o644) // present but not +x
  return dir
}
```
Add the two distinguishing cases (near the existing "CLI missing" test,
L122-129):
```js
test("preflight NOT executable: aborts with PreflightUnavailable, not a REFUSE", async () => {
  const dir = makeRepoNonExecStub()
  try {
    await assert.rejects(runBefore(dir, COMMIT_TOOL), (err) => {
      assert.ok(err instanceof PreflightUnavailable,
        "must be PreflightUnavailable (broken tool), not a plain REFUSE abort")
      assert.match(err.message, /not executable|missing/)
      assert.doesNotMatch(err.message, /REFUSED/) // NOT a policy rejection
      return true
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("preflight MISSING: also PreflightUnavailable (distinct from REFUSE)", async () => {
  const dir = makeRepoNoStub()
  try {
    await assert.rejects(runBefore(dir, COMMIT_TOOL), (err) => {
      assert.ok(err instanceof PreflightUnavailable)
      assert.doesNotMatch(err.message, /REFUSED/)
      return true
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})
```
Note: the existing L122-129 "CLI missing" test still passes (its regex
`/could not run|fail-closed/` matches the new missing-CLI message, which retains
"fail-closed"); no existing test needs deletion. The operator runs
`node --test tests/test_git_guard.mjs` to confirm all cases green.

### Phase 3 — D (DEFERRED, operator build-mode; ready-to-apply)

Create `.gleipnir/decisions/bin-executable-bit.md` with the **exact text**:

```markdown
# Decision: bin/* executable-bit durability + detection

**Status:** decided and applied (acute fix). Durable decision record (Tier-3,
operator-authored). Converged via the orchestrator-surfaced gate; brief:
`../plans/bin-executable-bit-fix-brainstorm.md`; plan:
`../plans/bin-executable-bit-fix.md`.

## Context

`bin/gleipnir-preflight` was found tracked as mode `100644` (non-executable).
The always-active `plugins/git-guard.ts` gate shells out to
`bin/gleipnir-preflight config-scan` before every broker git write; a
non-executable entrypoint makes `spawnSync` fail and the gate abort fail-closed,
blocking ALL broker commits/pushes with an error indistinguishable from a policy
rejection.

## Decisions

- **The durable fix is the committed index mode.** `chmod +x` on the working
  tree is not enough — the executable bit must be recorded in git's index/tree
  as `100755`. Set it with `git update-index --chmod=+x bin/<file>` (or
  `chmod +x` then `git add`), and verify with `git ls-files -s bin/` (the mode
  is the first field). Applied for `bin/gleipnir-preflight` in commit
  `9645974` (restored `100755`).
- **`.gitattributes` has NO portable executable-bit directive.** A common
  misconception is that a `.gitattributes` entry can force the +x bit
  cross-platform; there is no such attribute. The committed tree mode is the
  only portable carrier of the executable bit. Do not add or rely on a
  `.gitattributes` line for this.
- **Verify `core.fileMode` is not disabled.** With `git config core.fileMode
  false`, git ignores working-tree mode changes, which can hide a wrong
  committed mode from a working-tree `os.access(..., os.X_OK)` check. Detection
  must (and does — see below) assert the COMMITTED mode via `git ls-files -s`,
  not the working-tree bit. Operators should confirm `core.fileMode` is not
  set to false in their environment.

## Detection / diagnosability (implemented separately)

- `tests/test_bin_executable.py` (agent-built, normal pipeline) asserts the
  committed mode of every tracked `bin/*` is executable, failing loudly and
  early with the exact fix command. Skips cleanly where no usable git tooling is
  present (e.g. the `bin/gleipnir-sandbox` test run, whose base image likely has
  no `git` binary).
- `plugins/git-guard.ts` distinguishes a broken/missing preflight tool
  (`PreflightUnavailable`) from a genuine config-scan REFUSE, so a future
  occurrence is a one-line "chmod this" fix rather than a multi-step
  investigation. Fail-closed behaviour is unchanged.

## Honesty label

Cooperative-policy-until-S-2 for the Tier-3 pieces (plugin, this record). The
detection test is real today (no S-2 dependency). None of this loosens the
fail-closed gate; it only makes a self-inflicted broken prerequisite fast to
diagnose and less likely to recur silently.
```

---

## Stress-test (acceptance checks)

**Phase 1 (checkable now):**
1. `tests/test_bin_executable.py` exists and is collected by `pytest` (under
   `testpaths=["tests"]`).
2. On a host checkout (with `.git`), the test **passes** — both tracked `bin/*`
   are committed `100755`.
3. In `bin/gleipnir-sandbox test` (base image likely lacks a `git` binary; the
   repo root including `.git` IS mounted `:ro`), the test **skips** on the
   observable symptom (git unusable) — it does not fail, does not error the suite.
4. Injected regression: with a scratch `git update-index --chmod=-x
   bin/gleipnir-preflight`, the test **fails**, the message **names**
   `bin/gleipnir-preflight`, and includes both `chmod +x … && git add …` and
   `git update-index --chmod=+x …` fix commands. (Not committed.)
5. The test reads the **committed** mode (`git ls-files -s`), verifiable by the
   test still failing on the injected regression even with `git config
   core.fileMode false` set locally.
6. Edge: with no tracked files under `bin/`, the test **skips** with a clear
   reason (not a silent green no-op).

**Phase 2 (checkable by the operator after applying):**
7. `node --test tests/test_git_guard.mjs`: the two new cases pass — a
   non-executable and a missing preflight both reject with `PreflightUnavailable`
   whose message matches `/not executable|missing/` and does **not** match
   `/REFUSED/`.
8. All pre-existing `test_git_guard.mjs` cases still pass (REFUSE still throws
   `/REFUSED/`; exit 0/2 still allow/warn; non-gated tools still pass through;
   ALWAYS-ACTIVE unchanged) — no fail-closed regression.
9. `PreflightUnavailable instanceof GitGuardAbort` holds (subclass), so the
   hook's existing catch aborts it — the git op is still blocked.

**Phase 3 (checkable by the operator after applying):**
10. `.gleipnir/decisions/bin-executable-bit.md` exists and states all three:
    committed-index-mode as durable fix (citing `9645974`), the `.gitattributes`
    no-directive caveat, and the `core.fileMode` verification.

---

## Execution Workflow

**Phase 1 (the only phase the pipeline runs now):**
1. Orchestrator routes this plan → **spec-review** (`quality-reviewer`) against
   the Decisions index + Stress-test as rubric.
2. On APPROVED, route the **test** stage to `gleipnir-code` to author
   `tests/test_bin_executable.py` per Assemble Phase 1 (test-first; the test IS
   the deliverable — there is no separate implementation artifact, so the `code`
   stage is a no-op beyond confirming the suite is green: acceptance checks 1–3
   green, 4–6 demonstrated).
3. Route **quality** (`quality-reviewer`) — blast-radius review (must not touch
   `bin/*`, the plugin, or any gate behaviour; must skip cleanly in-sandbox).
4. Route **git** (`git-ops`) to commit. Broker gate will run the preflight; both
   `bin/*` are executable, so no lockout.

**Phases 2 & 3 (NOT for the pipeline):** hand the ready-to-apply diffs/text
above to the **operator** for a later build-mode session (via the built-in
`/build` escape hatch that may write Tier-3). The operator applies 2a+2b
together (test depends on the exported subclass), runs `node --test
tests/test_git_guard.mjs` (acceptance 7–9), then creates the Phase 3 record
(acceptance 10). No roster agent — including `gleipnir-code` — executes Phases
2–3.

---

## Out of scope

Option A (declined); any change to `bin/*` contents or the git broker; any
loosening of the fail-closed gate; adding a `.gitattributes` executable-bit line
(explicitly rejected in D as non-portable/non-existent).
