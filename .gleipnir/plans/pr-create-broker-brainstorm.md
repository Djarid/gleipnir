# Design Brief: PR / MR creation capability for the Gleipnir roster

> **Status: PRE-CONVERGENCE.** This brief is the *input* to the operator's
> convergence decision (brainstorm Phase 4 / precept-10 gate). The
> `## Decision Analysis` below frames options + framework + recommendation for
> each material decision; it decides NONE of them. `## Selected Approach` is
> deliberately left pending — the orchestrator surfaces the decisions to the
> operator and records the converged choice here. `gleipnir-brainstorm` cannot
> reach the operator and has NOT converged.

## Problem Statement

A completed feature slice (S6) is finished and its branch is pushed, but it
needs a pull request opened against `main` — direct commits to `main` are
forbidden here, PRs are required. **No roster role can open a PR/MR.** The two
brokers between them cover issues and local git, but neither exposes any
merge-request verb:

- `gleipnir-pm` broker (`src/gleipnir/broker/pm/`) exposes exactly four verbs:
  `issue_create` / `issue_update` / `issue_comment` / `issue_close`. It holds
  the platform token (`GITHUB_TOKEN`/`GITLAB_TOKEN`) and the REST plumbing.
- `gleipnir-git` broker (`src/gleipnir/broker/git/`) exposes exactly four
  verbs: `git_status` / `git_diff` / `commit_changes` / `push_current_branch`.
  It runs **local git subprocesses only** and holds **no platform token**.

The gap is a genuine capability hole: the branch exists on the remote, but the
act of *creating the PR object* (a platform REST call) has no home. The origin
remote here is GitHub (`git@github.com:Djarid/gleipnir.git`), so GitHub is the
must-work case.

## Constraints

- **`src/**` + `tests/**` are pipeline-owned executable code.** This work runs
  the **full 8-stage pipeline** (brainstorm → plan → spec-review → test → code
  → quality → git → gate). It is NOT prose/config-light-path eligible: the
  disqualifier set `X` (see `stage-role-map.md`) includes `src/**` and
  `tests/**`, and any path in `X` forces the full pipeline. The Tier-3 grant
  edit to `project-mgr.md` is a *separate*, enforcement-bearing hardened-path
  change applied by the operator/build-mode, not by this pipeline.
- **stdlib-only enforcement-core constraint holds.** `platform.py` is
  stdlib-only by design (`os`/`re`/`json`/`urllib`) so it is unit-testable
  without the `mcp` SDK (`tests/test_broker_stdlib_only.py`). A `pr_create`
  must not introduce a new dependency.
- **No live network in tests.** `platform._http_request` is the single HTTP
  seam that tests monkeypatch; a `pr_create` must route through it so the unit
  suite never touches the network.
- **The tool-surface test is set-equality.** `tests/test_broker_tool_surface.py`
  asserts `_tool_names(server) == EXPECTED_PM_TOOLS` (a 4-element set). Adding a
  5th PM tool **must** update `EXPECTED_PM_TOOLS` — the "exactly N tools"
  contract is enforced, so scope (D2) is a hard, test-visible commitment, not a
  soft preference.
- **GitHub/GitLab field-name asymmetry is real and already precedented.** PR:
  GitHub `POST /repos/{owner}/{repo}/pulls` with `title`/`head`/`base`/`body`;
  GitLab MR: `POST /projects/{id}/merge_requests` with
  `source_branch`/`target_branch`/`title`/`description`. This mirrors the
  existing `issue_*` github/gitlab split in `platform.py` exactly.
- **G-2 credential minimisation.** The broker single-holder clause keeps
  credentials in the fewest possible places. Any option that puts a platform
  REST token where one does not currently live *broadens* the credential
  surface and must clear a higher bar.

## Approaches Considered

### Approach A: Add `pr_create` to the `gleipnir-pm` broker (held by `project-mgr`)

**Summary:** Add a `pr_create` verb to `platform.py` (mirroring `issue_create`
exactly — same token resolution, same `_http_request` seam, same github/gitlab
field split) and a thin `pr_create` MCP wrapper in the PM `mcp_server.py`
(mirroring the `issue_create` wrapper + `_remote_or_error`). Grant flows to
`project-mgr`, which already holds the `gleipnir-pm_*` namespace and the token.

**Tradeoffs:**
- Pro: **Zero new credential surface.** The PM broker *already* receives
  `GITHUB_TOKEN`/`GITLAB_TOKEN` (`opencode.jsonc` lines 86–87). A PR uses the
  **same token** as `issue_*`. Nothing new is exposed to any role.
- Pro: **Maximal code reuse / lowest risk.** `pr_create` is a near-verbatim
  clone of `issue_create`; the HTTP seam, error shape, token-absent structured
  error, and endpoint-helper pattern all exist and are tested.
- Pro: **Conceptually correct.** A PR/MR is a platform-API object (like an
  issue), created via REST + token — squarely the PM/platform broker's job, not
  a local-git-subprocess job.
- Con: Semantically a PR is "about git branches", so a reader might expect it in
  the git broker. (Fix: it operates on *remote platform objects via REST*, not
  on the local working tree — the git broker has neither the token nor a REST
  client. The seam is token+REST, which is the PM broker's, so the naming
  intuition is superseded by the capability boundary.)

**Estimated Scope:** `platform.py` (+~30 lines, one function), PM
`mcp_server.py` (+~20 lines, one wrapper + instructions text update), tests
(`test_broker_pm_platform.py`, `test_broker_pm_mcp_server.py`,
`test_broker_tool_surface.py` set update). Complexity: **low**.

**Risk:** **low** — pure additive mirror of a tested pattern; no new
dependency, no new credential, no new process.

### Approach B: Add `pr_create` to the `gleipnir-git` broker (held by `git-ops`)

**Summary:** Add PR-creation to the git broker on the intuition that "a PR is a
git thing." This requires giving the git broker a **platform REST client and a
platform token** it does not currently have.

**Tradeoffs:**
- Pro: Co-locates "branch pushed" and "PR opened" in one role, so a single
  `git-ops` delegation could both push and open the PR.
- Pro: Matches a naive mental model where PRs live "next to" branches.
- Con: **Broadens `git-ops`'s credential surface — against G-2.** The git
  broker today holds **no platform token** and does only local subprocess ops.
  Injecting `GITHUB_TOKEN` into the git broker gives the sole push-holder *also*
  a REST-write credential it never had, concentrating more capability in one
  role — the opposite of single-holder minimisation.
- Con: **Duplicates plumbing.** The git broker has no `_http_request` seam,
  `RemoteInfo`, `parse_remote_url`, `_api_base`, or `get_token`; all of it would
  be duplicated from `platform.py` or cross-imported, muddying the git broker's
  "local-subprocess-only" boundary.
- Con: Contradicts the existing decision record's framing (PM broker owns the
  platform REST API; git broker owns local git).

**Estimated Scope:** git `mcp_server.py` + a new REST client (or a cross-package
import), `opencode.jsonc` token injection into `gleipnir-git`, git-ops grant,
new tests. Complexity: **medium**. Plus a **credential-surface expansion** that
is itself an enforcement-bearing change.

**Risk:** **medium–high** — new credential surface on the push-holder;
duplicated plumbing; a security-relevant blast-radius change to the most
capability-sensitive role.

### Approach C: A new third broker (`gleipnir-mr` or similar) held by a new/existing role

**Summary:** Stand up a dedicated PR/MR broker separate from both existing
brokers, with its own MCP server, token wiring, namespace, and holder.

**Tradeoffs:**
- Pro: Clean single-responsibility separation of "merge-request lifecycle" from
  "issue lifecycle."
- Pro: Would scale cleanly if MR operations grow into a large independent
  surface (review threads, approvals, merge, etc.).
- Con: **Heavyweight for a one-verb need.** A whole new broker process,
  `pyproject`/VERSION/enable-wiring, namespace glob, and a holder-role decision,
  to add a single `pr_create` — massive over-build (YAGNI).
- Con: **Third token co-location.** The new broker needs the same platform
  token again, adding a *third* place the credential lives (worse than A on
  G-2, comparable to B).
- Con: Duplicates the entire `platform.py` REST/token/remote plumbing a third
  time.

**Estimated Scope:** a whole new `src/gleipnir/broker/mr/` package + server +
tests, `opencode.jsonc` mcp block + token, a holder-role grant, namespace
denies on every other role. Complexity: **high**.

**Risk:** **medium** — not risky to correctness, but a large, mostly-wasted
scope and a new credential co-location for no near-term benefit.

## Decision Analysis

Four material decisions were surfaced (D1–D4). D1 and D4 are tightly coupled
(the credential-surface analysis *is* the deciding factor for the holder), so
they share a framework pass; D2 and D3 are scoped independently.

---

### D1 — Which broker/role holds PR-create? (+ D4 — credential-surface concern)

**Options:** (A) `gleipnir-pm` broker / `project-mgr`; (B) `gleipnir-git`
broker / `git-ops`; (C) new third broker.

**Decision type:** Multi-option comparison **and** architectural tradeoff with
a security (credential-surface) dimension. Per the auto-selection table:
multi-option → **Weighted Decision Matrix**; architectural/security →
cross-checked with **Second-Order Thinking**. Primary framework: **Weighted
Decision Matrix**.

**Framework used:** Weighted Decision Matrix. Criteria weighted by the
framework's stated goals (G-2 credential minimisation is weighted highest
because it is a security invariant, not a preference).

| Criterion | Weight | A (pm/project-mgr) | B (git/git-ops) | C (new broker) |
|---|---|---|---|---|
| Credential-surface minimisation (G-2) | 10 | 10 → **100** | 3 → **30** | 4 → **40** |
| Code reuse / implementation risk | 8 | 10 → **80** | 5 → **40** | 3 → **24** |
| Conceptual correctness (PR = platform REST object) | 7 | 9 → **63** | 5 → **35** | 8 → **56** |
| Scope economy (fits a one-verb need) | 7 | 9 → **63** | 6 → **42** | 2 → **14** |
| Future extensibility (MR surface grows) | 4 | 6 → **24** | 5 → **20** | 9 → **36** |
| **Total** | | **330** | **167** | **170** |

**Recommended (input to convergence): Option A** (score 330, decisive margin).

**Second-Order cross-check (why the margin is real, not just arithmetic):**
- **D4 restated as the deciding fact:** PR-create uses the **same token
  already held by the PM broker** (`opencode.jsonc` injects
  `GITHUB_TOKEN`/`GITLAB_TOKEN` into `gleipnir-pm` today; the git broker gets
  none). Under Option A there is **no new credential surface whatsoever** — the
  token, the REST client, `RemoteInfo`, `parse_remote_url`, and the
  `_http_request` seam all already exist in `platform.py`. Under Option B,
  `git-ops` (the sole push-holder) gains a REST-write token it never had —
  concentrating push + REST-write in one role, a *second-order* expansion of
  the most capability-sensitive seat, directly against G-2. Under Option C, a
  *third* co-location of the same token appears.
- Near term A ships in a low-risk additive PR; far term A keeps the
  issue/PR platform surface unified in the role that already owns platform REST,
  with no credential drift.

**Bias warnings:**
- ⚠️ *Status Quo Bias (checked, not triggering):* A is not being favoured
  merely because "the token is already there" as inertia — the same-token fact
  is a *genuine G-2 security advantage*, independently scored. Applied equal
  scrutiny to A; it still wins on the weighted security criterion.
- ⚠️ *Anchoring Bias (checked, low):* The delegation pre-suggested A is likely
  correct. Re-scored B and C independently from scratch; B's credential
  expansion and C's over-build are real, framework-surfaced demerits, not
  anchoring artifacts.
- No other detectors triggered (IKEA/Bandwagon/Sunk-Cost N/A — nothing built
  yet).

**Honesty note (per delegation):** This decision is **clear-cut on
credential-minimisation grounds.** Option A is not a close call — B actively
worsens the G-2 posture and C over-builds. This is the one D-N where the
recommendation is strong enough that convergence is likely a confirmation
rather than a genuine deliberation. The operator should still confirm it (it is
material — it touches roster capability and the credential boundary), but the
analysis does not leave it genuinely open.

---

### D2 — Tool-surface scope: just `pr_create`, or also `pr_update`/`pr_comment`/`pr_merge`/`pr_close`?

**Options:** (i) `pr_create` only (the immediate need); (ii) the full PR
lifecycle set, mirroring `issue_*`'s completeness.

**Decision type:** Binary/prioritisation → **Reversibility Filter →
Pros-Cons-Fixes**.

**Framework used:** Reversibility Filter, then Pros-Cons-Fixes.

- **Reversibility:** **Two-Way Door.** Adding `pr_update`/`pr_merge`/etc. later
  is a purely additive change of the same shape as `pr_create` — no migration,
  no lock-in. Reversal/extension cost is low (hours).
- **Pros-Cons-Fixes (Option i — `pr_create` only):**
  - Pro: Meets the actual, demonstrated need (S6 needs a PR *opened*).
  - Pro: Smallest blast radius; the set-equality tool-surface test grows by
    exactly one entry.
  - Pro: YAGNI — no speculative `pr_merge` (which is itself a
    higher-consequence, protected-branch-adjacent operation deserving its own
    convergence).
  - Con: Asymmetric with `issue_*`'s 4-verb completeness. **Fix:** the
    Two-Way-Door classification means the remaining verbs can be added in a
    later slice with no rework when a real need appears; asymmetry now is
    cheap and reversible.

**Recommended (input to convergence): Option (i) — `pr_create` only.** YAGNI +
reversibility make this the disciplined choice; `pr_merge` in particular is a
protected-branch-touching operation that should NOT be smuggled in under a
"parity" rationale — it warrants its own decision if/when needed.

**Bias warnings:**
- ⚠️ *Scope Creep Bias (checked):* The "match issue_*'s completeness"
  temptation is exactly the pattern this detector guards — expanding scope to
  achieve symmetry rather than to meet a need. The Two-Way-Door finding defuses
  it: symmetry can be achieved later at low cost.
- No other detectors triggered.

**Honesty note:** Recommendation is clear (YAGNI + reversibility), but this is
a genuine judgment call the operator may reasonably override if they *know* the
other verbs are imminently needed. Worth an explicit operator confirmation.

---

### D3 — GitHub-first vs GitHub+GitLab parity in one slice?

**Options:** (i) GitHub-only first (the actual need — origin is GitHub); (ii)
GitHub + GitLab in one slice (parity, mirroring the existing `issue_*` split).

**Decision type:** Binary → **Reversibility Filter → Pros-Cons-Fixes**.

**Framework used:** Reversibility Filter, then Pros-Cons-Fixes.

- **Reversibility:** **Two-Way Door.** The GitLab branch is a small `if
  remote.platform == "github" / else` fork inside one function — identical in
  shape to `issue_create`'s existing split. Adding GitLab later is trivial.
- **Pros-Cons-Fixes (Option ii — ship both):**
  - Pro: **Precedent parity** — every existing `issue_*` verb already handles
    both platforms in the *same function* via the field-name split; a
    GitHub-only `pr_create` would be the *odd one out* in `platform.py`.
  - Pro: The GitLab code is nearly free — the split pattern is copy-adapt from
    `issue_create` (`body`→`description`, plus `head`/`base`→
    `source_branch`/`target_branch`), and tests monkeypatch `_http_request` so
    there is no live-network cost to testing the GitLab path.
  - Con: GitLab is not the demonstrated need (origin is GitHub). **Fix:**
    because the GitLab arm is ~5 lines mirroring an established, tested pattern
    and carries no network-test cost, the marginal effort is negligible and it
    preserves module-wide consistency — the usual YAGNI argument is weak here
    because the cost is near-zero and the *inconsistency* has its own carrying
    cost.

**Recommended (input to convergence): Option (ii) — GitHub + GitLab parity in
one slice, GitHub prioritised as the must-work/tested-live case.** This is the
rare case where matching precedent is *cheaper and cleaner* than the minimal
option: the split already exists for `issue_*`, the GitLab arm is near-free, and
GitHub-only would make `pr_create` the sole platform-asymmetric verb in the
module. Note this is the *opposite* disposition from D2 — because there the
extra verbs are genuinely separate operations (esp. `pr_merge`), whereas here
the "extra" is one field-mapping fork of the *same* operation.

**Bias warnings:**
- ⚠️ *Bandwagon / "parity for its own sake" (checked):* Guard against choosing
  (ii) merely because "issue_* did it." The justification here is concrete —
  near-zero marginal cost + module consistency + the tested `_http_request`
  seam — not mere conformity. Passes.
- ⚠️ *Scope Creep Bias (checked):* Unlike D2, (ii) does not add a *new
  operation* — it completes the platform-handling of the *one* operation being
  added. Not scope creep in the decision-avoidance sense.
- No other detectors triggered.

**Honesty note:** Genuinely worth operator input — reasonable people could
prefer strict GitHub-only YAGNI (D3-i). The recommendation leans (ii) on the
near-zero-cost + consistency argument, but this is the least clear-cut of the
four and the operator's call should decide it.

---

### D4 — Credential-surface / blast-radius concern

Folded into D1 above (it is the deciding criterion of the D1 matrix, not an
independent choice). Restated for the record: **under the recommended D1=A there
is NO new credential surface** — `pr_create` reuses the PM broker's
already-injected `GITHUB_TOKEN`/`GITLAB_TOKEN` and the existing `_http_request`
seam. This is the explicit reason A is safer than B: B would grant the sole
push-holder (`git-ops`) a REST-write token it has never held, concentrating
capability against G-2. No framework re-run needed; D4's answer is a consequence
of D1's.

## Selected Approach

**CONVERGED** by the operator via the orchestrator's `question` tool
(operator-via-orchestrator, L-C6-legitimate — NOT self-attested). Recorded here
as the authoritative input `gleipnir-plan` plans from:

- **D1 (holder): CONVERGED → Approach A — `gleipnir-pm` broker / `project-mgr`.**
  MATCHES recommendation. The PM broker already holds the platform token +
  `_http_request` REST seam; a PR/MR is a platform-API object. Zero new
  credential surface. Approach B (git-ops) REJECTED — it would give the
  sole-push-holder a REST-write token it never had (worsens G-2 minimisation).
- **D2 (scope): CONVERGED → FULL pr_* set — `pr_create`, `pr_update`,
  `pr_comment`, `pr_merge`, `pr_close`.** DIVERGED from the recommendation
  (which was `pr_create` only, YAGNI). The operator chose the fuller surface,
  mirroring the `issue_*` set's completeness. **NOTE the added blast radius:**
  `pr_merge` touches protected branches (it merges into the base branch) — the
  plan MUST treat `pr_merge` with extra care in the blast-radius review, and
  the merge must NOT provide any force / admin-override path (mirrors the git
  broker's force-push-absent discipline). Each of the five verbs is a
  monkeypatched-`_http_request` mirror of the corresponding REST call.
- **D3 (platforms): CONVERGED → GitHub + GitLab parity, GitHub-first.** MATCHES
  recommendation. Both platforms in one slice, mirroring the existing `issue_*`
  both-platform field-map fork; tests use the monkeypatched HTTP seam (no live
  network). GitHub is the must-work case (origin is
  `git@github.com:Djarid/gleipnir.git`).
- **D4 (credential surface): CONVERGED → no new surface (consequence of D1=A).**
  All five pr_* verbs use the SAME `GITHUB_TOKEN`/`GITLAB_TOKEN` the PM broker
  already receives; no new credential is introduced.

**Rationale:** the operator converged on the credential-minimising holder (A),
the fuller tool surface (all five pr_* verbs, accepting the `pr_merge`
blast-radius flagged above), and cross-platform parity. The Decision Analysis
above is the justification; the one divergence (D2) is the operator's explicit
choice of completeness over YAGNI.

## Open Questions

- **PR body / draft support:** Should `pr_create` accept an optional `body`
  (GitHub) / `description` (GitLab) — yes, mirroring `issue_create`'s optional
  `body`. Should it support a `draft` flag? (Suggest: defer `draft` — YAGNI, and
  it re-opens D2's scope question.) For the operator to note, not block on.
- **Head/base defaults:** Should `base` default to `main` and `head` default to
  the current branch (detected like `push_current_branch` does), or be required
  explicit args? (Suggest: explicit `head`/`base` args with no silent default,
  so a PR target is never guessed — but confirm.)
- **The tool-surface set-equality test** (`EXPECTED_PM_TOOLS`) MUST be updated
  in the same slice or the suite fails; the plan stage must sequence the test
  update ahead of / with the implementation (test-first).

## Scope Sketch

| Area | Files/Modules Likely Affected | Pipeline treatment |
|---|---|---|
| REST verb | `src/gleipnir/broker/pm/platform.py` (add `pr_create` + a `_pulls_endpoint`/`_mrs_endpoint` helper, mirroring `_issues_endpoint`) | `src/**` → **full 8-stage pipeline** |
| MCP wrapper | `src/gleipnir/broker/pm/mcp_server.py` (add `pr_create` tool + update `instructions` text from "four tools" to "five") | `src/**` → **full 8-stage pipeline** |
| Unit tests | `tests/test_broker_pm_platform.py` (pr_create github+gitlab, token-absent error), `tests/test_broker_pm_mcp_server.py` (wrapper), `tests/test_broker_tool_surface.py` (**update `EXPECTED_PM_TOOLS`** to include `pr_create` — set-equality) | `tests/**` → **full 8-stage pipeline** (test-first: authored before code) |
| Tier-3 grant | `.gleipnir/agents/project-mgr.md` — the PM role already holds `gleipnir-pm_*` by deny-list, so `pr_create` is auto-granted by the existing namespace glob; **verify** no frontmatter change is actually needed (likely a docs/scope-note update only) | **Enforcement-bearing hardened path**, applied SEPARATELY by operator/build-mode |
| Broker enable wiring | `opencode.jsonc` — `gleipnir-pm` already enabled with tokens injected; **no change expected** (confirm) | Enforcement wiring — hardened path if touched |

**Note on the Tier-3 / config edits:** these are NOT part of the `src/**`
pipeline slice. They are enforcement-bearing config on the hardened path,
applied separately by the operator/build-mode with the two-pass review +
negative-check attestation (`stage-role-map.md` hardened path). The likely
outcome is that **no grant change is needed at all** because the deny-list glob
(`gleipnir-pm_*`) already covers a new `pr_create` tool — this must be
*verified*, not assumed, at that stage.
