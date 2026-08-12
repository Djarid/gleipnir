# Design Brief: bin/* executable-bit prerequisite validation

**Stage:** brainstorm (Clarify → Explore → Propose → Converge). **Status:**
operator-converged. **Convergence:** surfaced by the orchestrator to the
operator; converged choice = **Build B + C + D; decline A**. This brief records
that decision with the Decision Analysis as its justification.

## Problem Statement

`bin/gleipnir-preflight` was found tracked in git as mode `100644`
(non-executable). The always-active commit gate `.gleipnir/plugins/git-guard.ts`
shells out to `bin/gleipnir-preflight config-scan` (via `spawnSync`) before ANY
broker git write. With the mode bit wrong, `spawnSync` returns `res.error`
(EACCES) and the guard throws `GitGuardAbort` — fail-closed — so **ALL broker
commits/pushes were blocked**: a fail-closed gate blocked by its own missing
prerequisite, not by a real policy violation. The operator fixed the acute case
this session (`chmod +x` + commit `9645974` restoring the `100755` mode), but
nothing PREVENTS recurrence, and the failure is not diagnosable at a glance.

Two distinct sub-gaps, confirmed by reading the code:

1. **No prevention / early warning.** Nothing catches a non-executable (or
   otherwise broken) `bin/*` entrypoint before it manifests as an opaque gate
   failure. Recurrence vectors: a fresh clone on a bit-non-preserving
   filesystem/OS; `git config core.fileMode false`; an editor/tool that strips
   the bit; a future `bin/` script committed without `+x`.
2. **The failure is indistinguishable from a policy violation.** In
   `git-guard.ts`, the EACCES spawn failure (lines 85-90) throws
   `GitGuardAbort` — the **same exception class** used for a genuine
   config-scan REFUSE (lines 111-116) and for unexpected exit codes (lines
   120-122). To the calling agent, "the preflight binary is not executable"
   looks identical to "your commit was rejected by config policy." The existing
   `tests/test_git_guard.mjs` "CLI missing" test asserts fail-closed *behavior*
   but does not distinguish *broken-tool* from *policy-reject*. This is why this
   session's diagnosis took multiple steps.

**Safety vs preference.** Sub-gap #1 is a **workflow-availability** concern (a
broken prerequisite causing a denial-of-service on the broker), not a security
invariant going unenforced. Sub-gap #2 is **operability/observability**, not
safety. Neither weakens a safety guard. The fail-closed behavior is **correct
and MUST be preserved** — nothing here makes the gate more permissive; it only
makes it faster to diagnose and less likely to trip on a self-inflicted
prerequisite.

## Constraints

- **Fail-closed is invariant.** No option may make the git-guard gate more
  permissive. C changes only the *message/type* of the abort, never the
  decision to abort.
- **Capability boundary (tier3-coach).** The agent CANNOT write VCS hooks
  (`hooks/**` + `core.hooksPath`), `.gleipnir/plugins/**` (Tier-3,
  operator-authored — `git-guard.ts` header lines 12-14; enforcement-path set
  in `s2-g1-closure.md`), or `.gleipnir/decisions/**` (Tier-3). It CAN write
  `tests/**` (`gleipnir-code`).
- **No CI exists.** There is no `.github/workflows`; a CI job is not a viable
  primary home. However `pyproject.toml` has `testpaths = ["tests"]`, so a new
  `tests/*.py` is auto-collected into the suite `gleipnir-code` already runs —
  making the test-suite variant of the early-check real today with no CI.
- **`core.fileMode false` can hide a wrong committed mode** from a working-tree
  `os.X_OK` check — so the detection check must assert the **committed** mode
  (`git ls-files -s bin/`), not merely the working-tree bit.
- **Cooperative-policy-until-S-2.** The Tier-3 pieces (C, D) are
  operator-authored by policy today; they become structurally agent-unreachable
  only when the S-2 substrate boundary lands.

## Approaches Considered

### Option A — `post-checkout`/`post-merge` hook re-asserting `+x` (DECLINED)
**Path:** `hooks/post-checkout`, `hooks/post-merge` (repo already uses
`core.hooksPath hooks`; precedent: `hooks/pre-commit`). **Mechanism:** on
checkout/merge, `chmod +x` known `bin/*` (or iterate `git ls-files bin/`).
- **Pros:** Automatically *repairs* the bit after the operations most likely to
  drop it. Zero friction. Prevention, not just detection.
- **Cons:** (1) Fires only for users who have opted into `core.hooksPath hooks`
  — a fresh clone does NOT have hooks active until the operator sets it, which
  is the exact moment the bit is most likely wrong, so it does not protect the
  primary recurrence vector. (2) Masks the root cause by silently repairing
  (hides `core.fileMode false`). (3) Adds two more `bin/*`-list-maintenance
  sites that themselves drift.
- **DECLINED** (operator-converged): weakest coverage, doesn't help the
  fresh-clone case it ostensibly targets, and masks the root cause. Recorded as
  considered.

### Option B — `tests/test_bin_executable.py` loud early self-check (SELECTED — agent-buildable now)
**Path:** `tests/test_bin_executable.py` (agent-writable; auto-collected via
`testpaths`). **Mechanism:** enumerate every tracked `bin/*` (`git ls-files
bin/`), assert the **committed git mode** is executable (`100755` via
`git ls-files -s bin/`, not merely working-tree `os.access(path, os.X_OK)`); on
failure emit an actionable message naming the file and the exact
`chmod +x` / `git update-index --chmod=+x` fix.
- **Pros:** Fails LOUDLY and EARLY — during the routine test run `gleipnir-code`
  already executes, long before any broker commit attempt. Fully actionable
  message. Auto-covers *future* `bin/*` (no per-file list). Asserting the
  committed mode defeats a `core.fileMode false` false-pass. No operator
  handoff — real today.
- **Cons:** Detection, not prevention (tells you it's broken, doesn't fix it).
  Only fires when tests run (an operator who clones and immediately commits
  without testing still hits the raw lockout — a smaller window).
- **Honesty label:** hard check within the test suite; real today (no S-2 dep).

### Option C — Improve `git-guard.ts` to distinguish "tool broken" from "policy reject" (SELECTED — Tier-3 handoff)
**Path:** `.gleipnir/plugins/git-guard.ts` (Tier-3, operator-authored).
**Mechanism:** in `runConfigScan`, detect the not-executable/missing case
specifically (`res.error.code === "EACCES"` / `"ENOENT"`, or an
`fs.accessSync(cli, fs.constants.X_OK)` pre-check) and throw a *distinct*,
unambiguous message, e.g. `git-guard: preflight tool bin/gleipnir-preflight is
not executable — run 'chmod +x bin/gleipnir-preflight'. This is a broken
prerequisite, NOT a policy rejection.` Ideally a distinct exception subclass so
tests/callers can tell it apart from `GitGuardAbort`-for-REFUSE. Update
`tests/test_git_guard.mjs` with a case distinguishing broken-tool from REFUSE.
- **Pros:** Defense-in-depth — even if B is absent/bypassed, the next
  occurrence is instantly diagnosable (one-line "chmod this" instead of a
  multi-step investigation). Fixes sub-gap #2 at its source. Preserves
  fail-closed exactly (still aborts).
- **Cons:** Does NOT prevent recurrence (still a lockout, just legible).
  Requires operator handoff (Tier-3 plugin). Touches the always-active
  enforcement plugin — needs care + conformance-test update.
- **Honesty label:** cooperative-policy-until-S-2.

### Option D — Decision-record note on the durable git-mode fix (SELECTED — Tier-3 handoff)
**Path:** `.gleipnir/decisions/<name>.md` (new file or amendment — implementer's
call). **Mechanism:** record that the durable fix is the committed index mode
(`git update-index --chmod=+x`, already applied in `9645974`); that
`.gitattributes` has NO portable executable-bit directive (common
misconception — note explicitly); and to verify `core.fileMode` is not disabled.
- **Pros:** Near-free; captures institutional knowledge; points at the *real*
  durable fix (committed index mode). **Cons:** Pure documentation — enforces
  nothing; relies on humans reading it.
- **Honesty label:** cooperative-policy-until-S-2 (Tier-3 decision record).

## Decision Analysis

### Framework selection
These are NOT mutually exclusive — this is a **defense-in-depth layering**
decision, not a single-choice selection. A/B/C/D operate at different points in
the failure timeline and are complementary:

```
future bin/* added / clone / fileMode=false  ->  test run  ->  broker commit attempt
   A: repair-on-checkout          B: loud fail here      C: legible abort here
   (prevention, if hooks set)     (early detection)      (diagnosability, last line)
   D: documents the durable committed-mode fix (spans all)
```

The material decision is **"which layers of the defense to build now,"** framed
as a **cost/coverage stack** (effort-vs-coverage / ICE lens), not "pick one."

### Bias check (12 detectors)
- **Single-option / false-dichotomy bias — FLAGGED and corrected.** The "A/B/C/D"
  phrasing invited pick-one; that is a false dichotomy — the strongest posture
  is B AND C (and cheaply D). Surfaced rather than forced.
- **Availability bias:** the vivid recent lockout could over-motivate heavyweight
  prevention (A) when cheap detection+diagnosability (B+C) covers realistic
  vectors better. Noted.
- **Sunk-cost / status-quo:** none — no prior control exists here.
- **Over-engineering / gold-plating:** Option A carries the highest complexity
  for the WEAKEST incremental coverage (doesn't help the fresh-clone case it
  targets). Guarded against — A declined.
- **Action bias:** the acute fix (`9645974`) already landed, so there is no
  urgency pressure to over-build; these controls are about recurrence.
- **Confirmation bias:** the indistinguishability claim was verified by reading
  the actual `GitGuardAbort` throw sites, not assumed.
- Authority / anchoring / framing / recency / groupthink / optimism: no material
  distortion detected.

### Recommendation (as surfaced)
Build **B + C**, record **D**, **decline A**. B is the highest-value,
lowest-cost, agent-buildable piece (loud+early, auto-covers future `bin/*`, no
handoff, real today) — the primary defense against *silent* recurrence. C is the
cheap high-value diagnosability fix turning any future occurrence into a one-line
fix while preserving fail-closed. D is near-free and captures the durable
committed-mode fix + the `.gitattributes` caveat + the `core.fileMode` check. A
is the weakest addition (complexity, coverage gap on the fresh-clone path,
root-cause masking).

## Selected Approach (operator-converged)

**Build B + C + D; decline A.** Converged by the operator via the orchestrator.

- **B — `tests/test_bin_executable.py`** — assert the **committed git mode**
  (`git ls-files -s bin/`, not just working-tree `os.access(..., os.X_OK)`) is
  executable (`100755`) for every tracked `bin/*` file, with an actionable
  failure message naming the file and the exact
  `chmod +x` / `git update-index --chmod=+x` fix.
- **C — `.gleipnir/plugins/git-guard.ts`** — in `runConfigScan`, distinguish the
  EACCES/ENOENT "tool broken" case from a genuine config-scan REFUSE, with a
  distinct actionable message and (ideally) a distinct exception subclass so
  tests/callers can tell them apart; add the corresponding `test_git_guard.mjs`
  case. Fail-closed behavior preserved.
- **D — decision-record note** (new file or amendment, implementer's call)
  documenting: durable fix = committed index mode
  (`git update-index --chmod=+x`, already applied in `9645974`);
  `.gitattributes` has no portable executable-bit directive (note explicitly as
  a common misconception); verify `core.fileMode` is not disabled.
- **A — DECLINED.** Considered; declined for weakest coverage, no help on the
  fresh-clone case, and root-cause masking. Kept in the record, not in scope.

### Handoff-timing split (routing — the orchestrator must route these separately)

| Piece | Layer | Agent-buildable? | Timing / routing |
|---|---|---|---|
| **B** | `tests/**` (source tree) | **Yes** (`gleipnir-code`) | **NOW — normal pipeline**: plan → spec-review → code → quality → git. No Tier-3 handoff. |
| **C** | `.gleipnir/plugins/**` (Tier-3) | **No** — operator-authored | **DEFERRED — Tier-3 handoff**: ready-to-apply plan for the operator's later build-mode session. |
| **D** | `.gleipnir/decisions/**` (Tier-3) | **No** — operator-authored | **DEFERRED — Tier-3 handoff**: ready-to-apply plan for the operator's later build-mode session. |

B and C/D are planned/executed on **different timelines**: B proceeds through the
normal pipeline immediately; C and D are prepared as ready-to-apply proposals for
a later operator build-mode session (this brainstorm proposes; it does not
implement, per tier3-coach).

## Open Questions

1. **B — enumeration source.** Use `git ls-files bin/` for the tracked-file set,
   and `git ls-files -s bin/` for the committed mode. Confirm the test invokes
   git via `subprocess` (no `git ls-files`-based test exists yet in `tests/`);
   ensure it degrades gracefully (skip vs fail) if run outside a git work tree.
2. **B — mode assertion granularity.** Assert exactly `100755` (or the executable
   bit within the tracked mode)? Recommend checking the executable bit rather
   than exact-`100755` equality to tolerate legitimate `100755` variants.
3. **C — subclass surface.** Introduce a distinct subclass (e.g.
   `PreflightUnavailable extends GitGuardAbort`) vs. a message-only distinction?
   Subclass is preferred (callers/tests can branch) but is an implementation
   decision for the C plan.
4. **C — pre-check vs post-error.** Pre-check with `fs.accessSync(cli, X_OK)` for
   a clean message, vs. inspecting `res.error.code`? Either is fine; pre-check
   gives the cleanest message. Decide in the C plan.
5. **D — new file vs amendment.** New `.gleipnir/decisions/bin-executable-bit.md`
   vs. amending an existing record (e.g. `broker-mcp.md` / `s2-g1-closure.md`).
   Implementer's call at build time.

## Scope Sketch

- **B (now):** one new test file `tests/test_bin_executable.py` (~1 test,
  parametrized over `git ls-files bin/`); actionable assertion message; no
  changes to `bin/*` or the plugin. Planned + executed through the normal
  pipeline.
- **C (deferred):** edit `.gleipnir/plugins/git-guard.ts` (`runConfigScan`
  branch + optional subclass) + a new case in `tests/test_git_guard.mjs`.
  Ready-to-apply plan handed to the operator; applied in build mode.
- **D (deferred):** one short decision-record note (new file or amendment).
  Ready-to-apply text handed to the operator; applied in build mode.
- **Out of scope:** Option A (declined); any change to the git broker; any
  loosening of the fail-closed gate.
