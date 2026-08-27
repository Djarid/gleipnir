# Plan: PR / MR lifecycle verbs for the `gleipnir-pm` broker

> **This is an ATLAS brief (`goals/plan-format.md`).** It plans FROM the
> operator-converged brief `.gleipnir/plans/pr-create-broker-brainstorm.md`
> (`## Selected Approach`, D1–D4 CONVERGED). D1–D4 are GIVEN and are NOT
> re-derived here. Pipeline treatment: `src/**` + `tests/**` are in the
> Axis-1 disqualifier set `X`, so this runs the **full 8-stage pipeline**
> (brainstorm → plan → spec-review → test → code → quality → git → gate). The
> Tier-3 grant/config check is a **separate** hardened-path change applied by
> the operator/build-mode, NOT part of this `src/**` slice.

---

## 1. Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Which broker/role holds PR-create | `gleipnir-pm` broker (`src/gleipnir/broker/pm/`), held by `project-mgr` | git broker (B); new third broker (C) | **Operator-converged** (brief `## Selected Approach`). PM broker already holds the platform token + `_http_request` REST seam; a PR/MR is a platform-API object. Zero new credential surface. B would give the sole push-holder a REST-write token (worsens G-2). |
| D2 | Tool-surface scope | FULL five verbs: `pr_create`, `pr_update`, `pr_comment`, `pr_merge`, `pr_close` | `pr_create` only (YAGNI) | **Operator-converged (DIVERGED from brainstorm recommendation).** Operator chose the fuller surface mirroring `issue_*`'s completeness. `pr_merge` carries added blast radius (protected branches) — flagged for blast-radius review, must expose NO force/admin bypass. |
| D3 | Platforms | GitHub + GitLab parity in one slice, GitHub-first | GitHub-only first | **Operator-converged.** Mirror the existing `issue_*` github/gitlab field-map fork; tests use the monkeypatched `_http_request` seam (no live network). Origin is `git@github.com:Djarid/gleipnir.git` → GitHub is the must-work case. |
| D4 | Credential surface | No new surface — all five verbs use the SAME `GITHUB_TOKEN`/`GITLAB_TOKEN` the PM broker already receives via `get_token` | Injecting a new token anywhere | **Operator-converged** (consequence of D1=A). No new credential is introduced. |
| P1 | `pr_create` body/description | Optional `body` arg → maps to GitHub `body` / GitLab `description` (mirrors `issue_create` L218–223). No `draft` flag. | Required body; a `draft` flag | **Plan-stage judgment** (brief Open Questions; delegation-authorized). Mirrors the tested `issue_create` optional-body split exactly; `draft` re-opens D2 scope (YAGNI). **Flag for spec-review.** |
| P2 | `pr_create` head/base | EXPLICIT required `head`/`base` (GitHub) / `source_branch`/`target_branch` (GitLab) — no silent default | Default `base=main` + auto-detect `head` from current branch | **Plan-stage judgment** (brief Open Questions; delegation-authorized). A PR target is never guessed. This is the Design Intent for `pr_create`. **Flag for spec-review.** |
| P3 | `pr_merge` safety | Plain merge only — NO force / squash-admin-override / admin-bypass argument | A `force`/`merge_when_pipeline_succeeds`-style override surface | **Plan-stage judgment** (D2 note; delegation-authorized). Mirrors the git broker's force-push-absent discipline (structurally absent, not merely denied — cf. `test_broker_tool_surface.py:137` `FORBIDDEN_PARAM_NAMES`). This is the falsifiable Design Intent for `pr_merge`. **Flag for blast-radius review.** |
| P4 | New test file vs extend-in-place | Extend the two EXISTING test files in place | Add a new `tests/test_broker_pr_*.py` | **Plan-stage judgment.** `test_broker_pm_platform.py` and `test_broker_pm_mcp_server.py` already exist and are already listed in `profiles.toml` `[profile.broker].test` (L60). Extending in place means **no Tier-3 `profiles.toml` edit is needed** — a new file WOULD require one (operator-only). Keeps this slice inside `src/**`+`tests/**` with zero hardened-path coupling. |

---

## 2. Architect

**Problem (one sentence).** The `gleipnir-pm` broker can create/update/comment/
close *issues* but has no verb to create/update/comment/merge/close a *pull
request / merge request*, so no roster role can open or manage a PR — yet direct
commits to `main` are forbidden and PRs are required.

**User.** The `project-mgr` role (the sole holder of the `gleipnir-pm_*`
namespace and the platform token), invoked by the orchestrator when a pushed
feature branch needs a PR opened/managed against `main`.

**Measurable success criteria.**
1. `gleipnir-pm` exposes exactly nine tools: the four existing `issue_*` plus
   the five new `pr_*` (`pr_create`, `pr_update`, `pr_comment`, `pr_merge`,
   `pr_close`) — enforced by the set-equality tool-surface test.
2. For EACH of the five `pr_*` platform verbs: a GitHub happy-path test and a
   GitLab happy-path test (correct method + URL + JSON body) and a token-absent
   structured-error test (no crash, no `_http_request` call) all pass.
3. `pr_merge` exposes NO parameter in `FORBIDDEN_PARAM_NAMES` and no
   force/admin-override argument at all — `test_no_pm_tool_exposes_a_force_parameter`
   stays green.
4. `platform.py` gains no new import root; `test_broker_stdlib_only.py` stays
   green (`platform.py` remains `mcp`-free and stdlib-only).
5. The FastMCP `instructions` text and the `mcp_server.py` module docstring no
   longer say "four tools" — they describe the five new `pr_*` verbs.

**Constraints.**
- **stdlib-only enforcement-core:** `platform.py` may use only the already-imported
  `os`/`re`/`json`/`urllib`. No new import (enforced by `test_broker_stdlib_only.py`
  parts (i)+(ii); `platform.py` must stay `mcp`-free).
- **No live network in tests:** every verb routes through the single
  `_http_request` seam, which tests monkeypatch. The no-token path must return
  a structured error WITHOUT calling `_http_request`.
- **Set-equality tool surface:** `EXPECTED_PM_TOOLS` in
  `test_broker_tool_surface.py` (L40) is asserted by `==`. Adding five tools
  without updating the set fails the suite — this is the test-first contract
  change.
- **`pr_merge` touches protected branches:** no force/admin bypass path (P3),
  mirroring the git broker's force-push-absent discipline.
- **Full 8-stage pipeline:** `src/**`+`tests/**` ∈ Axis-1 `X`; not light-path
  eligible.
- **Tier-3 grant is out of scope for the code stage** (see §4 Link L5).

---

## 3. Trace

### Artifacts and where they live (source of truth)

| Artifact | File | Change |
|---|---|---|
| Endpoint helpers | `src/gleipnir/broker/pm/platform.py` | ADD `_pulls_endpoint(remote)` + `_mrs_endpoint(remote)` mirroring `_issues_endpoint` (L194). GitHub keys ONLY `pr_comment` off the *issues* endpoint (PR comments post to `/issues/{n}/comments` because PRs ARE issues for comment purposes); `pr_create`/`pr_update`/`pr_merge`/`pr_close` ALL use the *pulls* endpoint (closing a PR is `PATCH /pulls/{n} {state:"closed"}`, an Update-a-PR call — NOT an issues-endpoint op). So: provide the pulls endpoint (GitHub `/repos/{o}/{r}/pulls`) for create/update/merge/close, and reuse `_issues_endpoint` for the `pr_comment` case only. GitLab uses one MR endpoint (`/projects/{enc}/merge_requests`) for all five. (Authoritative per-verb shapes are rows 81–85 + the Stress-test AC table; this corrects a spec-review-noted narrative slip that had listed `pr_close` under the issues endpoint.) |
| `pr_create` | `platform.py` | ADD. GitHub `POST {pulls}` body `{title, head, base, body?}`; GitLab `POST {mrs}` body `{title, source_branch, target_branch, description?}`. Signature: `pr_create(remote, title, head, base, body=None)` — `head`/`base` REQUIRED (P2). |
| `pr_update` | `platform.py` | ADD, mirror `issue_update` (L235). GitHub `PATCH {pulls}/{n}`; GitLab `PUT {mrs}/{iid}`. `pr_update(remote, pr_id, **fields)`. |
| `pr_comment` | `platform.py` | ADD, mirror `issue_comment` (L249). GitHub `POST {issues}/{n}/comments` (PRs are issues); GitLab `POST {mrs}/{iid}/notes`. `pr_comment(remote, pr_id, body)`. |
| `pr_merge` | `platform.py` | ADD (no `issue_*` analog). GitHub `PUT {pulls}/{n}/merge`; GitLab `PUT {mrs}/{iid}/merge`. `pr_merge(remote, pr_id)` — NO force/override arg (P3). Empty/minimal JSON body. |
| `pr_close` | `platform.py` | ADD, mirror `issue_close` (L267). GitHub `PATCH {pulls}/{n}` `{state:"closed"}`; GitLab `PUT {mrs}/{iid}` `{state_event:"close"}`. `pr_close(remote, pr_id)`. |
| MCP wrappers | `src/gleipnir/broker/pm/mcp_server.py` | ADD five `@mcp.tool()` wrappers mirroring `issue_create` (L67): `_remote_or_error(repo_dir)` guard → call `platform.pr_*` → `json.dumps(result, default=str)`. |
| MCP `instructions` + docstring | `mcp_server.py` L3–6 (docstring), L29–36 (`instructions`) | UPDATE: replace "exactly four tools"/four-verb enumeration with the four `issue_*` + five `pr_*` verbs. |
| Platform unit tests | `tests/test_broker_pm_platform.py` | ADD per verb: github happy-path + gitlab happy-path + token-absent structured-error (mirror `TestIssueCreateHappyPath` / `TestIssueOpsWithoutToken` / `TestIssueUpdate` / `TestIssueComment` / `TestIssueClose`). Plus `_pulls_endpoint`/`_mrs_endpoint` shape assertions mirroring `TestApiBaseAndEndpoints`. |
| Wrapper unit tests | `tests/test_broker_pm_mcp_server.py` | ADD per wrapper: error-path returns error WITHOUT calling `platform.pr_*` (`_stub_error_resolve` + `_forbidden`) + happy path delegates to `platform.pr_*` (`_stub_success_resolve` + `_Recorder`), mirroring the existing `issue_*` wrapper tests. |
| Tool-surface contract | `tests/test_broker_tool_surface.py` L40 | UPDATE `EXPECTED_PM_TOOLS` to the 9-element set. The `pr_merge` verb must add NO param in `FORBIDDEN_PARAM_NAMES` (existing `test_no_pm_tool_exposes_a_force_parameter` L137 enforces this — do NOT weaken it). |

### Integrations map

- **Token:** `platform.get_token(remote.platform)` (L116) — SAME `GITHUB_TOKEN`/
  `GITLAB_TOKEN` as `issue_*` (D4). No new resolution.
- **HTTP seam:** every verb calls `_http_request(method, url, token=, platform=,
  json_body=)` (L135) — the one monkeypatched seam.
- **Auth header:** handled inside `_http_request` from the `platform` arg
  (Bearer for github, PRIVATE-TOKEN for gitlab) — verbs pass `platform=
  remote.platform`, nothing new.
- **Remote detection:** wrappers call `_remote_or_error(repo_dir)` (L59) →
  `_detect_remote` → `parse_remote_url`. Unchanged.
- **Sandbox profile:** `[profile.broker].test` (`profiles.toml` L60) ALREADY
  lists both `test_broker_pm_platform.py` and `test_broker_pm_mcp_server.py`.
  Extending them in place needs **no `profiles.toml` edit** (P4). The broker
  image is the only one carrying the `mcp` SDK.

### Edge cases

- **E1 — GitHub PR-comment endpoint asymmetry:** GitHub PR *comments* use the
  **issues** endpoint (`/issues/{n}/comments`), NOT `/pulls/{n}/comments`
  (that is the review-comments endpoint). `pr_comment` github arm must reuse
  `_issues_endpoint`, not `_pulls_endpoint`. GitLab uses MR notes
  (`/merge_requests/{iid}/notes`). This is the one place the github pr/issue
  endpoints diverge from the "pulls for everything" intuition — test it
  explicitly.
- **E2 — `pr_merge` has no `issue_*` analog:** its shape (`PUT .../merge` with
  a minimal/empty body) is new. Assert the URL ends `/merge` and that NO
  force/override key appears in the JSON body.
- **E3 — `pr_create` required head/base (P2):** unlike `issue_create` (only
  `title` required), `pr_create` has three required args. Tests must construct
  it with explicit `head`/`base`; a github body must contain `head`+`base`, a
  gitlab body `source_branch`+`target_branch`.
- **E4 — GitLab field remap:** `body`→`description` (create), `head`/`base`→
  `source_branch`/`target_branch`. Mirror `issue_create`'s
  `test_issue_create_gitlab_with_body_sets_description_not_body` (L286) shape:
  assert github key present / gitlab key present-and-remapped.
- **E5 — token-absent must not touch network:** each verb's no-token path
  returns `_no_token_error(...)` (L166) BEFORE any `_http_request` — proven by
  setting `_http_request`/`platform.pr_*` to an `AssertionError`-raising fake.
- **E6 — set-equality is unforgiving:** forgetting the `EXPECTED_PM_TOOLS`
  update, or a typo in a tool name, fails `test_exactly_the_four_pm_tools_are_registered`
  (which must be renamed/updated to nine). This is intentional (contract).
- **E7 — stdlib-only:** no new import may enter `platform.py`. `_url_quote`
  (already imported, L25) covers GitLab project-path encoding for the MR
  endpoint.

---

## 4. Link (validated before building)

- **L1 — `_http_request` seam exists and is the single HTTP choke point**
  (`platform.py` L135). Confirmed all `issue_*` route through it; tests
  monkeypatch `platform._http_request`. ✓ (read)
- **L2 — `get_token`/`_no_token_error` reusable as-is** (L116, L166). No new
  credential path. ✓ (read)
- **L3 — `_issues_endpoint`/`_api_base`/`_project_path` pattern** (L182–199)
  is the template for `_pulls_endpoint`/`_mrs_endpoint`; GitHub `/repos/{path}/…`
  vs GitLab `/projects/{urlquoted}/…`. ✓ (read)
- **L4 — the three existing test files exist and their patterns are readable:**
  `test_broker_pm_platform.py` (`_RequestRecorder`, `TestIssue*` classes),
  `test_broker_pm_mcp_server.py` (`_Recorder`, `_forbidden`,
  `_stub_error_resolve`/`_stub_success_resolve`), `test_broker_tool_surface.py`
  (`EXPECTED_PM_TOOLS` set-equality + `FORBIDDEN_PARAM_NAMES`). ✓ (read)
- **L5 — Tier-3 grant is NOT this slice's job.** `project-mgr.md` grants the
  PM namespace by DENY-LIST (`tools: {"gleipnir-git_*": false}`, L22–23) — it
  denies the git namespace and keeps everything else, so a new `gleipnir-pm_*`
  tool is auto-covered by the existing grant. **This is the brief's suspicion
  and it looks correct from the frontmatter, but it MUST be verified by the
  operator/build-mode on the hardened path — NOT asserted or edited by the code
  stage.** The `opencode.jsonc` `gleipnir-pm` enable + token injection is
  likewise unchanged (same tokens). Flag both as separate hardened-path checks.
- **L6 — `profiles.toml` needs no edit** because both target test files are
  already listed (L60) and we extend in place (P4). ✓ (read)
- **L7 — no new test file, so no new Tier-3 file-list amendment.** ✓ (consequence
  of P4).

---

## 5. Assemble (build order — TEST-FIRST; each test step must fail RED first)

> Test-first discipline (Axiom 1): the tests are the correctness arbiter and
> are authored/adjusted BEFORE the implementation. Steps 1–3 must be observed
> failing (red) before Step 4 makes them pass (green).

1. **Tool-surface contract (red).** Update `tests/test_broker_tool_surface.py`
   L40 `EXPECTED_PM_TOOLS` to the 9-element set (`issue_*` ×4 + `pr_*` ×5);
   rename/adjust `test_exactly_the_four_pm_tools_are_registered` → nine-tools
   assertion. Leave `test_no_pm_tool_exposes_a_force_parameter` UNCHANGED (it
   must keep passing after Step 4 — proves `pr_merge` added no force param).
   → RED: the PM set-equality test fails (server still exposes only four).
2. **Platform unit tests (red).** Add to `tests/test_broker_pm_platform.py`:
   for each of `pr_create`, `pr_update`, `pr_comment`, `pr_merge`, `pr_close` —
   a github happy-path (method+URL+body), a gitlab happy-path (method+URL+
   remapped body), and a token-absent structured-error (no `_http_request`
   call). Add `_pulls_endpoint`/`_mrs_endpoint` shape assertions
   (mirror `TestApiBaseAndEndpoints`). Cover E1 (github pr_comment uses issues
   endpoint), E2 (pr_merge URL ends `/merge`, no force key), E3 (pr_create
   required head/base), E4 (gitlab remap).
   → RED: `AttributeError`/failures — `platform.pr_*` do not exist.
3. **Wrapper unit tests (red).** Add to `tests/test_broker_pm_mcp_server.py`:
   for each of the five wrappers — error-path (`_stub_error_resolve` +
   `platform.pr_* = _forbidden`, assert no delegation) and happy-path
   (`_stub_success_resolve` + `_Recorder`, assert delegation + `json.dumps`).
   → RED: the `pr_*` wrappers do not exist.
4. **Implementation (green).** In dependency order:
   1. `platform.py`: add `_pulls_endpoint` + `_mrs_endpoint` (mirror
      `_issues_endpoint`), then `pr_create`, `pr_update`, `pr_comment`
      (github→issues endpoint per E1), `pr_close`, `pr_merge` (no override arg).
      No new import.
   2. `mcp_server.py`: add the five `@mcp.tool()` wrappers (mirror
      `issue_create` L67); update the module docstring (L3–6) and FastMCP
      `instructions` (L29–36) to describe nine tools.
   → GREEN: Steps 1–3 pass; `test_broker_stdlib_only.py` (platform.py mcp-free)
   and `test_no_pm_tool_exposes_a_force_parameter` stay green.
5. **Full broker suite.** Run `./bin/gleipnir-sandbox test --profile broker`
   (or the pipeline's sandboxed equivalent); confirm the whole
   `tests/test_broker_*.py` set is green, including the untouched issue/git
   tests (regression guard).

**Separate hardened-path track (NOT this pipeline slice — operator/build-mode):**
verify `project-mgr.md`'s deny-list grant auto-covers `gleipnir-pm_pr_*`
(expected yes; L5) and that `opencode.jsonc` needs no change; if any grant edit
IS required it runs the two-pass + negative-check attestation hardened path.

---

## 6. Stress-test (acceptance criteria — checkable, traceable to each verb × platform × token-absent)

**Tool surface.**
- AC-S1: `_tool_names(pm server) == {issue_create, issue_update, issue_comment,
  issue_close, pr_create, pr_update, pr_comment, pr_merge, pr_close}` (exactly
  nine; set-equality).
- AC-S2: `_tool_param_names(pm server) & {"force","--force","-f"} == ∅` (P3 /
  `pr_merge` exposes no force param).

**Per-verb × platform × token-absent (the 5×3 matrix):**

| Verb | GitHub happy-path AC | GitLab happy-path AC | Token-absent AC |
|---|---|---|---|
| `pr_create` | AC-C1: `POST …/pulls`, body has `title`,`head`,`base`,(`body`) | AC-C2: `POST …/merge_requests`, body has `title`,`source_branch`,`target_branch`,(`description`); NO `head`/`base`/`body` keys | AC-C3: `{success:False, error:str}`, `_http_request` NOT called |
| `pr_update` | AC-U1: `PATCH …/pulls/{n}`, fields passed through | AC-U2: `PUT …/merge_requests/{iid}`, fields passed through | AC-U3: structured error, no network |
| `pr_comment` | AC-M1: `POST …/issues/{n}/comments` (E1!), body `{body:…}` | AC-M2: `POST …/merge_requests/{iid}/notes`, body `{body:…}` | AC-M3: structured error, no network |
| `pr_merge` | AC-G1: `PUT …/pulls/{n}/merge`; JSON body has NO force/override key | AC-G2: `PUT …/merge_requests/{iid}/merge`; NO force/override key | AC-G3: structured error, no network |
| `pr_close` | AC-L1: `PATCH …/pulls/{n}` `{state:"closed"}` | AC-L2: `PUT …/merge_requests/{iid}` `{state_event:"close"}` | AC-L3: structured error, no network |

**Endpoint helpers.**
- AC-E1: `_pulls_endpoint(github)` starts `https://api.github.com/repos/…/pulls`
  and GHE custom-domain uses `/api/v3/…`.
- AC-E2: `_mrs_endpoint(gitlab)` starts `https://…/api/v4/projects/{urlquoted}/merge_requests`.

**Non-regression / invariants.**
- AC-R1: `test_broker_stdlib_only.py` green — `platform.py` imports no new root,
  stays `mcp`-free.
- AC-R2: all pre-existing `issue_*` and git tests still green.
- AC-R3: `mcp_server.py` docstring + FastMCP `instructions` mention the five
  `pr_*` verbs and no longer claim "four tools" (grep the applied file).
- AC-R4: no `profiles.toml` edit was required (both test files already listed).

**Cognition cross-check (Gate-2 honour check, at quality stage):**
- AC-X1 (P2 honoured): `pr_create` has NO default for `head`/`base` — a caller
  omitting them is a type error, never a silently-guessed target.
- AC-X2 (P3 honoured): `pr_merge` signature/schema exposes no parameter that
  could bypass branch protection or force a merge (grep the applied wrapper +
  platform verb; confirm against `FORBIDDEN_PARAM_NAMES` and the absence of any
  `force`/`squash`/`merge_when_*`/admin arg).

---

## 7. Execution Workflow (for the implementing agents)

- **Roles/stages:** `test` and `code` both bind to `gleipnir-code` (Sonnet);
  `spec-review` and `quality` to `quality-reviewer`; `git` to `git-ops`;
  `gate` to the orchestrator. Full 8-stage pipeline.
- **test stage:** author Steps 1–3 exactly; run the broker profile and CONFIRM
  RED (the `pr_*` symbols/tools do not yet exist). Do not implement.
- **code stage:** implement Step 4 in the stated dependency order until Steps
  1–3 go green and AC-R1/AC-R2 hold. Touch ONLY `platform.py` +
  `mcp_server.py`. No new imports in `platform.py`. Do NOT touch
  `.gleipnir/**` (agents, profiles, opencode.jsonc) — that is the operator's
  hardened-path track.
- **Mirror, don't invent:** every `pr_*` verb is a shape-clone of its `issue_*`
  analog except `pr_merge` (new shape, `PUT .../merge`, no override) and the
  `pr_comment` github→issues-endpoint asymmetry (E1). When in doubt, copy the
  `issue_*` structure and remap fields.
- **spec-review:** verify P1/P2/P3 judgments (this plan flags them), the
  intent-quality of the Design Intents below (§8), and the test matrix
  completeness (5×3 + endpoints + E1/E2).
- **quality (blast-radius, adversarial):** focus on `pr_merge` — confirm NO
  force/admin/override path exists (AC-X2, AC-S2), i.e. protected-branch safety
  is STRUCTURAL, not a denied flag. Run the honour check (AC-X1/AC-X2).
- **git/gate:** standard; the `git` stage cannot skip hooks (broker invariant).
- **Sandbox:** all test runs go through `bin/gleipnir-sandbox` broker profile
  (`--network=none`, ro source) — the broker image is the only one with `mcp`.

---

## 8. Design Principles (Gate-1 — case (i): OOP/functional Python code)

`P ∩ X ≠ ∅` (touches `src/**`, `tests/**`) and the touched `X`-members
(`platform.py`, `mcp_server.py`) have function/module structure → **case (i):
SOLID + DRY + SRP + Design Intent all apply.**

### SOLID (evaluated against the proposed design)
- **Single Responsibility:** each new function has exactly one reason to change.
  `pr_create` changes only if PR-creation field-mapping changes; `_pulls_endpoint`
  only if the GitHub pulls URL shape changes; `_mrs_endpoint` only if the GitLab
  MR URL shape changes. Each MCP wrapper's sole responsibility is
  argument-marshalling + `_remote_or_error` guard + `json.dumps` — the REST
  logic lives in `platform.py`, not the wrapper.
- **Open/Closed:** the design EXTENDS `platform.py` by adding functions; it does
  NOT modify `issue_*`, `_http_request`, `get_token`, `_api_base`,
  `_issues_endpoint`, or `_no_token_error`. The five verbs are added the same
  way `issue_*` were — the module is open to new verbs, closed against edits to
  the tested existing ones.
- **Liskov:** no subclassing introduced (functional module + a `RemoteInfo`
  dataclass reused unchanged). N/A within the design; no parent contract is
  altered.
- **Interface Segregation:** each MCP tool exposes a narrow, verb-specific
  signature — `pr_merge(pr_id, repo_dir)` does NOT accept create-only args;
  `pr_create(title, head, base, body, repo_dir)` does not carry merge args. No
  fat "do-everything PR" tool.
- **Dependency Inversion:** the verbs depend on the `_http_request` seam
  abstraction (the monkeypatch point), not on `urllib` directly at the call
  site — high-level PR logic is decoupled from the HTTP transport, exactly as
  `issue_*` already are. Tests substitute the seam.

### DRY
- The five verbs REUSE the existing token-check (`get_token` + `_no_token_error`),
  the `_http_request` seam, `_api_base`, and `_project_path` — none is
  reimplemented. The github/gitlab branching is added ONLY where the field/URL
  genuinely differs (the same asymmetry `issue_*` already established), not
  duplicated wholesale.
- `_pulls_endpoint`/`_mrs_endpoint` are the named single source of the two new
  URL shapes — no verb hand-builds a `/pulls` or `/merge_requests` URL inline.
- `pr_comment` (github) REUSES `_issues_endpoint` rather than duplicating the
  issues-URL construction (E1), because a GitHub PR comment genuinely IS an
  issue comment.
- **DRY boundary (deliberate non-abstraction):** the five verbs are NOT collapsed
  into one generic `_pr_op(method, url_fn, body_fn)` helper. Reason: that mirrors
  the EXISTING `issue_*` style (four separate functions), keeps each verb
  independently readable/testable, and avoids inventing an abstraction the tested
  precedent does not use. Matching precedent > premature meta-helper.

### Single Responsibility (named, per new component)
- `_pulls_endpoint(remote)` → build the GitHub pulls collection URL.
- `_mrs_endpoint(remote)` → build the GitLab merge-requests collection URL.
- `pr_create` → issue one PR/MR-create REST call, remapping fields per platform.
- `pr_update` → issue one PR/MR-update REST call.
- `pr_comment` → issue one PR-comment/MR-note REST call.
- `pr_merge` → issue one plain PR/MR-merge REST call (no override).
- `pr_close` → issue one PR/MR-close REST call.
- each `@mcp.tool()` wrapper → marshal args, guard the remote, delegate to one
  `platform.pr_*`, serialise the result.

### Design Intent (specific, falsifiable — the load-bearing genuineness proxy)

1. **`pr_create` never guesses a PR target (P2).** *Falsifiable claim:*
   `pr_create` exposes `head`/`base` (GitHub) / `source_branch`/`target_branch`
   (GitLab) as REQUIRED arguments with NO default value; there is no code path
   that infers the base branch as `main` or auto-detects `head` from the current
   branch. *A reviewer could violate this* by adding `base: str = "main"` or a
   `_current_branch()` fallback — either would falsify the intent.

2. **`pr_merge` exposes no argument that bypasses branch protection or forces a
   merge (P3).** *Falsifiable claim:* the `pr_merge` MCP tool signature and the
   `platform.pr_merge` function accept only a PR/MR identifier (and `repo_dir`);
   they carry NO `force`, `--force`, `-f`, `squash`-admin-override,
   `merge_when_pipeline_succeeds`-bypass, or any admin-override parameter, and
   the JSON body sent to the merge endpoint contains no such key. *A reviewer
   could violate this* by adding any override parameter or force key — it would
   be caught by `test_no_pm_tool_exposes_a_force_parameter` (for the enumerated
   names) and by AC-X2's grep (for the broader override class). This mirrors the
   git broker's force-push-ABSENT discipline: safety is structural, not a denied
   flag.

3. **The `pr_*` verbs add no new credential surface (D4).** *Falsifiable claim:*
   every `pr_*` verb resolves its token via the existing
   `get_token(remote.platform)` and passes it through the existing
   `_http_request` seam; no new env var, no new token parameter, no new
   auth-header logic is introduced. *A reviewer could violate this* by reading a
   new env var or accepting a token argument — either would falsify it.

---

## Persistence note
This is a Tier-0 transient session artifact (`plans/`), disposable after the
work merges. The converged D1–D4 live in the brainstorm brief; if any durable
resolution emerges (e.g. the confirmed Tier-3 auto-cover fact), the operator
records it in `decisions/`.
