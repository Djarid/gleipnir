# Plan: Close the test-coverage gap on `broker/pm/mcp_server.py`

> **Stage:** `plan` (gleipnir-plan). **Input:** an operator/orchestrator
> coverage-remediation request (no separate brainstorm brief — this is bounded
> test-authoring against existing, unchanged production code, not a design
> exploration). The target file sits at **25% line coverage** (57 stmts, 39
> missed; missing ranges 42-56, 61-64, 76-80, 100-113, 125-129, 140-144, 148)
> per the last measured run this session. The REST client layer it wraps
> (`platform.py`) is already thoroughly tested by `test_broker_pm_platform.py`,
> and the PM tool-surface conformance (exactly 4 tools, no force param) is
> already covered by `test_broker_tool_surface.py`; neither must be duplicated —
> the gap is that **nothing tests the `mcp_server.py` wrapper layer itself**.
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0). This file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it (the orchestrator
> sequences that; nothing here is executed now). In particular this plan
> **names** one Tier-3 operator prerequisite (a `profiles.toml` amendment); it
> does not write it.
>
> **Sibling precedent.** This plan deliberately mirrors
> `.gleipnir/plans/broker-git-coverage-gap.md` (the git-broker equivalent, which
> reached 99% with only its `__main__` guard uncovered). Naming, fixture shape,
> monkeypatch targets, and the Tier-3 collection gate are all inherited from
> that proven pattern.

---

## Decisions (index)

Summary of every decision this plan fixes, in order encountered; full reasoning
is in the sections below. Rows 1–3 are planning-stage decisions; row 4 is a
material sequencing constraint surfaced to the operator (not decided by the
planner); row 5 records the Trace finding that **no production bug was found**.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Where the new tests live | **One new file** `tests/test_broker_pm_mcp_server.py`, mirroring the naming of `tests/test_broker_git_mcp_server.py` | Extending `test_broker_pm_platform.py`; or extending `test_broker_tool_surface.py` | A new file keeps the platform-layer tests and tool-surface tests untouched (no duplication) and names its scope in its own docstring. The naming mirrors the git-broker coverage-gap file, so the operator/`profiles.toml` gate is analogous and predictable. |
| 2 | How to mock the two boundaries | **`monkeypatch.setattr(platform, "issue_*", fake)`** for the happy-path / field-building tests (one layer up from where `test_broker_pm_platform.py` mocks `_http_request`), and **`monkeypatch.setattr(mcp_server.subprocess, "run", fake)`** for `_detect_remote`'s own raise / non-zero-returncode branches | A pure real-network / real-git approach; or mocking `_http_request` (too deep — would re-exercise `platform`'s already-covered logic) | Mocking at the `platform.*` verb boundary means no live network AND no re-testing of `platform` internals — the new file exercises ONLY the wrapper's own remote-resolve → serialize logic. Mocking `mcp_server.subprocess.run` (the name as bound in the target module, not the bare module) is the deterministic, offline way to drive `_detect_remote`'s exception and non-zero-returncode arms — the exact pattern `test_broker_git_mcp_server.py` uses for the git broker's `subprocess.run`. |
| 3 | Coverage target & measurement | **≥85% line+branch on `mcp_server.py`**, measured by `bin/gleipnir-sandbox test` (broker profile, which already runs `--cov=src/gleipnir/broker --cov-branch`); the `if __name__ == "__main__":` guard (line 148) is the one expected residual miss (same shape as the git server's line 417) and is pre-justified | Claiming a number without the sandbox measuring it; targeting line-only | 85% is the standing target in `gleipnir-code.md`. The broker profile already emits line+branch term-missing coverage, so the number is measured, not asserted. The plan enumerates every currently-uncovered range so ≥85% is achievable; line 148 is import-unreachable and pre-justified, mirroring the git server's 99% (only-`__main__`-uncovered) result. |
| 4 | **[MATERIAL — surfaced to operator, NOT decided here]** Test-file collection under the broker profile | Flag that `.gleipnir/sandbox/profiles.toml` (Tier-3, operator-only) **must be amended** to add `tests/test_broker_pm_mcp_server.py` to `[profile.broker].test` (line 60) before `bin/gleipnir-sandbox test` will collect it | Silently assuming the runner picks up the new file | `profiles.toml:60` hardcodes an EXPLICIT list of broker test files; it is Tier-3 POLICY, agent-unwritable. The new file is NOT auto-collected. This is the **same gate** the git-broker file already went through (its name is already on line 60 — the new PM file is NOT). **Operator action; the planner names it, does not perform it.** |
| 5 | Production-code changes | **None anticipated** — Trace confirmed every uncovered path in the gap list is reachable and behaves correctly; this is pure test-authoring | Silently "fixing" any code | Per the delegation's standing instruction: if a genuine bug requiring a production fix were found, it would be flagged here as a decision, not silently fixed. Trace found none (see Trace §"Bug-hunt result"). If `gleipnir-code` discovers one while making a test pass, it must STOP and surface it, not weaken the test or patch silently. |

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
  server (`gleipnir-pm`). This work adds **no** behaviour; it adds **tests**
  that exercise existing tool functions and their error branches. It touches no
  enforcement core (G-3/G-5/G-4/memory) and does not change G-5 pipeline
  ordering. The PM broker carries no Args-layer force-push analogue (its tool
  surface is issue verbs only, already conformance-tested).
- **Gaps / factual findings named (mechanical, verified this session against
  the actual source):**
  1. **`profiles.toml` hardcodes the broker test list (Decision 4).**
     `.gleipnir/sandbox/profiles.toml:60` lists **six** broker test files
     explicitly — and `tests/test_broker_git_mcp_server.py` is already among
     them, but `tests/test_broker_pm_mcp_server.py` is **not**. The new file
     will **not** be collected by `bin/gleipnir-sandbox test` (broker profile)
     until an operator adds it. Tier-3, operator-only. Surfaced, not decided.
  2. **The gap is the wrapper layer, not the client layer.**
     `test_broker_pm_platform.py` mocks `platform._http_request` and thoroughly
     tests `platform.parse_remote_url` / token resolution / `issue_*` verbs. It
     never imports or calls `mcp_server.py`. So `mcp_server.py`'s own remote-
     resolve-or-error wrapping and JSON serialization are entirely unexercised —
     this is why coverage is 25%.
  3. **The tool functions are directly callable.** `issue_create`/`issue_update`/
     `issue_comment`/`issue_close` are plain functions decorated with
     `@mcp.tool()` (FastMCP returns the original callable), directly importable
     and callable — the identical pattern proven in
     `test_broker_git_mcp_server.py` (git tools) and relied on by
     `test_broker_tool_surface.py`. Each returns a **JSON string**, parsed via
     `json.loads`.
  4. **`_remote_or_error` catches exactly `RuntimeError`**, which is exactly
     what `_detect_remote` raises on both its failure arms — so the error-path
     mapping is sound and reachable (no bug).
- **New material tradeoff found?** **One (Decision 4), surfaced to the
  operator — the `profiles.toml` amendment is a Tier-3 action a bounded agent
  cannot perform.** It is a hard sequencing gate, not a design choice the
  planner resolves. Everything else is bounded, mechanical test-authoring.

---

## 1. Architect

**Problem (one sentence):** Raise line+branch coverage of
`src/gleipnir/broker/pm/mcp_server.py` from 25% to ≥85% by authoring targeted
tests for the currently-unexercised wrapper functions and error branches
(`_detect_remote`'s subprocess-raise / non-zero-returncode / success arms,
`_remote_or_error`'s success and error arms, and the four `@mcp.tool()`
wrappers `issue_create`/`issue_update`/`issue_comment`/`issue_close` including
`issue_update`'s conditional field-building logic) — **without duplicating** the
already-covered `platform.py` client tests and PM tool-surface tests and
**without changing production code**.

**User:** the maintainers of the `gleipnir-pm` broker (and the framework's own
CI/coverage scoreboard, G-4d cost-per-outcome ledger) who need the broker's
correctness-critical wrapper wiring — the remote-detection-then-delegate seam,
not just the `platform.py` REST logic — actually exercised. This mirrors the
git-broker follow-up already closed in
`.gleipnir/plans/broker-git-coverage-gap.md`.

**Measurable success criteria:**

1. `bin/gleipnir-sandbox test` (broker profile) reports **≥85% line coverage
   AND ≥85% branch coverage** for `src/gleipnir/broker/pm/mcp_server.py`; any
   residual uncovered line is named and justified in the code agent's report
   (the `if __name__ == "__main__":` guard at **line 148** is the one expected
   residual and is pre-justified — it only runs under `python -m …`, not import,
   same as the git server's line 417).
2. Every gap enumerated in Trace §"Coverage gaps (verified)" has at least one
   test that exercises it and asserts the observable contract (the returned
   JSON `success`/`error` shape or the field/kwargs passed to the mocked
   `platform.*` verb), not merely "it ran".
3. All existing broker tests still pass (no regression; the new file adds
   coverage, it does not modify `test_broker_pm_platform.py`,
   `test_broker_tool_surface.py`, or any other existing broker test file).
4. **No production code under `src/gleipnir/broker/pm/` is changed** (Decision
   5). If a genuine bug is found, it is surfaced as a new decision, not fixed
   silently.

**Constraints:**

- **Test-authoring only.** No behaviour change to `mcp_server.py`,
  `platform.py`, or any broker module. This is the `test` stage and (since it is
  pure test-authoring against unchanged code) may be the same delegation as
  `code` — see Execution Workflow.
- **No duplication.** Do not re-test `platform.parse_remote_url`, token
  resolution, or the `platform.issue_*` REST behaviour
  (`test_broker_pm_platform.py` owns those), and do not re-test the 4-tool set /
  force-param absence (`test_broker_tool_surface.py` owns those). New tests
  target only the uncovered `mcp_server.py` wrapper functions/branches.
- **Sandbox-only execution.** Tests run via `bin/gleipnir-sandbox test`
  (broker profile) — the only test capability `gleipnir-code` holds. No host
  pytest. Coverage is `--cov=src/gleipnir/broker --cov-branch` (per
  `profiles.toml:62`).
- **Broker profile only.** The new file imports
  `gleipnir.broker.pm.mcp_server`, which transitively imports `mcp` (via
  `from mcp.server.fastmcp import FastMCP`), so it must be skip-collected under
  the lean python profile. This is handled by `conftest.py` `collect_ignore` —
  the new file must be added there too (see Trace edge case E-COLLECT). This is
  the **same import shape** as `test_broker_git_mcp_server.py`, which is already
  in `collect_ignore`.
- **No live network or git needed.** Happy-path/field-building tests mock at the
  `platform.*` verb boundary; `_detect_remote`'s error arms mock
  `mcp_server.subprocess.run`. The success arm of `_detect_remote` can be driven
  either by a real temp git repo (`git init` + `git remote add origin <url>`) OR
  by mocking `subprocess.run` to return a scripted stdout — see Trace.

---

## 2. Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Role |
|---|---|---|---|---|
| **New** coverage test file | new: `tests/test_broker_pm_mcp_server.py` | source tree (under `tests/`, outside `.gleipnir/**`) | **bounded `gleipnir-code`** | The deliverable: tests for the uncovered wrapper functions + error branches. |
| `conftest.py` `collect_ignore` amendment | `tests/conftest.py` (edit) | source tree | **bounded `gleipnir-code`** | Append the new file to `collect_ignore` when `mcp` is absent (so the lean python profile does not abort collection). |
| Target under test (UNCHANGED) | `src/gleipnir/broker/pm/mcp_server.py` | source tree | (unchanged) | The 148-line PM broker server whose coverage is being raised. Read-only for this work. |
| REST client layer (UNCHANGED) | `src/gleipnir/broker/pm/platform.py` | source tree | (unchanged) | Provides `RemoteInfo`, `parse_remote_url`, `issue_create/update/comment/close`; called by the target. Already thoroughly covered by `test_broker_pm_platform.py`. |
| Broker sandbox profile — **operator amendment** | `.gleipnir/sandbox/profiles.toml` (edit line 60) | **Tier-3 POLICY** | **operator only** | Add `tests/test_broker_pm_mcp_server.py` to `[profile.broker].test` so `bin/gleipnir-sandbox test` collects it. **Decision 4 — a code agent cannot write this.** |
| Existing tests (NOT modified) | `tests/test_broker_pm_platform.py`, `tests/test_broker_tool_surface.py` | source tree | (unchanged) | Already-covered scope; the new file must not duplicate them. |

### Coverage gaps (verified against the actual source, line-referenced)

Each row is a distinct uncovered function/branch; the "verified" column records
the source lines confirming the branch exists and is reachable. Line numbers are
from the actual 148-line `mcp_server.py` read this session.

| Gap | Function | What's uncovered | Source lines (verified) |
|---|---|---|---|
| G1 | `_detect_remote` | (a) `subprocess.run` **raises** → `RuntimeError("Could not run git: …")`; (b) **non-zero returncode** → `RuntimeError("Could not determine the origin remote URL")`; (c) **success** → parses `result.stdout` via `platform.parse_remote_url` and returns a `RemoteInfo` | 40–56 (try/except 42–51; returncode check 53–54; success return 56) |
| G2 | `_remote_or_error` | (a) **success** arm → `{"remote": RemoteInfo}`; (b) **error** arm → catches `RuntimeError`, returns `{"error": {"success": False, "error": str(exc)}}` | 59–64 (success 62; except 63–64) |
| G3 | `issue_create` | (a) remote-resolve **fails** → returns `json.dumps(error)` WITHOUT calling `platform.issue_create`; (b) **happy path** → calls `platform.issue_create(remote, title, body or None)` and returns `json.dumps(result, default=str)` | 67–80 (error early-return 77–78; happy 79–80) |
| G4 | `issue_update` | (a) remote-resolve **fails** → early error return; (b) **field-building logic** — only non-empty `title`/`body`/`state` become kwargs in `fields`; (c) **happy path** → calls `platform.issue_update(remote, issue_id, **fields)`, serializes | 83–113 (error 101–102; fields build 104–110; call+serialize 112–113) |
| G5 | `issue_comment` | (a) remote-resolve **fails** → early error return; (b) **happy path** → calls `platform.issue_comment(remote, issue_id, body)`, serializes | 116–129 (error 126–127; happy 128–129) |
| G6 | `issue_close` | (a) remote-resolve **fails** → early error return; (b) **happy path** → calls `platform.issue_close(remote, issue_id)`, serializes | 132–144 (error 141–142; happy 143–144) |
| — | module-entry guard | `if __name__ == "__main__": mcp.run(transport="stdio")` — **expected residual miss** (import never runs it under pytest, same as git server's 417) | 147–148 |

### How each gap is driven (test design — enough for the code agent)

Two mocking boundaries, chosen per Decision 2:

- **`platform.*` verb boundary** — `monkeypatch.setattr(platform, "issue_create",
  fake)` etc. — for the four wrappers' happy paths and `issue_update`'s field
  logic. The `fake` records its positional/keyword args and returns a canned
  dict (mirroring `_RequestRecorder` in `test_broker_pm_platform.py`, but one
  layer up). This exercises ONLY the wrapper's resolve→delegate→serialize seam,
  never `platform`'s internals.
- **`mcp_server.subprocess.run` boundary** — `monkeypatch.setattr(
  mcp_server.subprocess, "run", fake)` (the name as bound in the target module,
  NOT the bare `subprocess` module) — for `_detect_remote`'s raise / non-zero
  arms. This mirrors `TestRunGitExceptionBranchesViaGitDiff` in
  `test_broker_git_mcp_server.py`.

For the wrapper error-path tests (G3a/G4a/G5a/G6a), the cleanest driver is to
`monkeypatch mcp_server._remote_or_error` to return `{"error": {...}}` — OR to
monkeypatch `mcp_server._detect_remote` to raise `RuntimeError` (which
`_remote_or_error` will convert). Either proves the wrapper returns the
serialized error WITHOUT touching `platform.*`. To additionally guarantee no
`platform` call happens on the error path, set the corresponding `platform.*`
verb to a fake that raises `AssertionError` (the "network-forbidden" pattern
already used at `test_broker_pm_platform.py:133`).

- **G1 `_detect_remote`** (patch `mcp_server.subprocess.run`):
  - **(a) raise:** `fake` raises `OSError("boom")` (or any `Exception`); assert
    `_detect_remote(...)` raises `RuntimeError` whose message starts with
    `"Could not run git: "` (`pytest.raises(RuntimeError, match=...)`).
  - **(b) non-zero returncode:** `fake` returns an object with
    `returncode=1` (e.g. a `types.SimpleNamespace(returncode=1, stdout="",
    stderr="fatal: no such remote")`); assert `RuntimeError` with message
    `"Could not determine the origin remote URL"`.
  - **(c) success:** either (i) `fake` returns
    `SimpleNamespace(returncode=0, stdout="https://github.com/owner/repo.git\n",
    stderr="")` and assert the returned `RemoteInfo` has
    `platform == "github"`, `owner == "owner"`, `repo == "repo"`; OR (ii) a real
    temp git repo (`git init`; `git remote add origin
    https://github.com/owner/repo.git`) driven with the real `subprocess.run`.
    The mock route (i) is deterministic and offline — prefer it; a real-repo
    variant is an optional bonus. *(Note: `subprocess.run(..., text=True)` yields
    a `CompletedProcess` with string `stdout`/`returncode`; the `SimpleNamespace`
    stub only needs `.returncode` and `.stdout`.)*
- **G2 `_remote_or_error`** (patch `mcp_server._detect_remote`):
  - **(a) success:** `fake` returns a `platform.RemoteInfo(...)`; assert
    `_remote_or_error("") == {"remote": <that RemoteInfo>}`.
  - **(b) error:** `fake` raises `RuntimeError("nope")`; assert the return is
    `{"error": {"success": False, "error": "nope"}}`. *(This also transitively
    exercises the wrappers' error arms, but each wrapper still gets its own
    direct test below so the JSON-serialization of the error is asserted per
    tool.)*
- **G3 `issue_create`:**
  - **(a) error path:** patch `mcp_server._remote_or_error` to return
    `{"error": {"success": False, "error": "no remote"}}`, and patch
    `platform.issue_create` to a fake that raises `AssertionError` if called;
    assert `json.loads(mcp_server.issue_create("t"))` equals
    `{"success": False, "error": "no remote"}` and the fake was NOT called.
  - **(b) happy path:** patch `mcp_server._remote_or_error` to return
    `{"remote": RemoteInfo(...)}` (or patch `_detect_remote` to return one), and
    patch `platform.issue_create` to a recorder returning
    `{"success": True, "data": {"number": 1}}`; call
    `mcp_server.issue_create("My title", body="body text", repo_dir="")`; assert
    the recorder was called once with the `RemoteInfo`, `"My title"`, and
    `"body text"` (note the wrapper passes `body or None`, so also add a case
    with `body=""` asserting the recorder received `None`), and that the
    returned JSON round-trips to the recorder's canned dict.
- **G4 `issue_update`** — the field-building logic needs three cases (per the
  delegation):
  - **all-three-set:** `issue_update("7", title="T", body="B", state="closed")`
    → recorder receives kwargs `{"title": "T", "body": "B", "state": "closed"}`.
  - **none-set / all-omitted:** `issue_update("7")` → recorder receives **no**
    field kwargs (empty `**fields`), proving the conditional inclusion.
  - **one-set-others-omitted:** `issue_update("7", state="closed")` → recorder
    receives exactly `{"state": "closed"}` (proving `title`/`body` are excluded
    when empty). Plus the **error path** (patch `_remote_or_error` → error;
    assert `platform.issue_update` NOT called and the serialized error is
    returned).
- **G5 `issue_comment`:**
  - **error path** (as G3a): `platform.issue_comment` not called, serialized
    error returned.
  - **happy path:** recorder receives `(RemoteInfo, "7", "the comment body")`;
    returned JSON round-trips to the canned dict.
- **G6 `issue_close`:**
  - **error path** (as G3a): `platform.issue_close` not called, serialized
    error returned.
  - **happy path:** recorder receives `(RemoteInfo, "7")`; returned JSON
    round-trips to the canned dict.

### Bug-hunt result (Trace obligation, Decision 5)

Read the full 148-line target and the 271-line `platform.py`. **No production
bug found.** Every uncovered path is reachable and returns the documented
contract:

- `_detect_remote`'s `except Exception` (line 50) correctly re-wraps ANY
  subprocess failure as `RuntimeError` (surfaced structurally, not raised
  raw); the non-zero-returncode arm (53–54) raises the second `RuntimeError`;
  the success arm delegates to `platform.parse_remote_url`.
- `_remote_or_error` catches **exactly** `RuntimeError` (line 63) — which is the
  only exception type `_detect_remote` raises — so no failure escapes as a
  crash and no unrelated exception is silently swallowed. Sound.
- The four wrappers each check `if "error" in resolved` (77/101/126/141) and
  early-return the serialized error before any `platform.*` call — so the
  no-remote path never hits the network. Sound.
- `issue_update`'s conditional field build (104–110) correctly omits empty
  `title`/`body`/`state`, so `platform.issue_update` is called with only the
  fields the caller set. Sound.
- `json.dumps(result, default=str)` (80/113/129/144) uses `default=str` so any
  non-JSON-native value in `platform`'s return (unlikely — it returns plain
  dicts) serializes without raising. Defensive, not buggy.

**One benign observation (not a bug):** `issue_create` passes `body or None`, so
an empty-string `body` is normalized to `None` before reaching `platform`
(matching `platform.issue_create`'s `body: Optional[str] = None` signature).
This is intended and is **documented** by the `body=""` → `None` happy-path
assertion (G3b) — not changed. **If `gleipnir-code` uncovers a genuine bug while
writing a test, it must STOP and surface it as a new decision (do not weaken the
test, do not patch silently).**

### Edge cases

1. **E-COLLECT — profile collection (Decision 4, hard gate).** The new file
   imports `mcp` transitively; the broker profile's `test` command
   (`profiles.toml:60`) is an **explicit file list** that includes
   `test_broker_git_mcp_server.py` but **not** the new PM file. Two things must
   both happen: (a) **operator** adds `tests/test_broker_pm_mcp_server.py` to
   `[profile.broker].test`; (b) **code agent** adds the same file to
   `conftest.py` `collect_ignore` so the lean python profile skip-collects it.
   Without (a) the new tests never run in the sandbox; without (b) the
   python-profile run aborts at collection (top-level `from mcp.server.fastmcp
   import FastMCP` raises `ModuleNotFoundError`).
2. **`monkeypatch` target scoping:** patch `mcp_server.subprocess.run`,
   `mcp_server._detect_remote`, `mcp_server._remote_or_error`, and
   `platform.issue_*` — the names as looked up where they are used, NOT the
   global `subprocess`. Patch where it is looked up.
3. **`body or None` normalization (G3b):** include the `body=""` case asserting
   the recorder received `None`, so the `or None` branch is exercised (this is a
   real conditional expression on line 79).
4. **`RemoteInfo` construction in fakes:** use
   `platform.RemoteInfo(host="github.com", owner="owner", repo="repo",
   platform="github")` (all four fields are required — it is a dataclass with no
   defaults) when a fake needs to return one.
5. **No secret/token leakage:** the wrapper tests never need a real token — they
   mock at the `platform.*` verb boundary, above where `get_token` runs. Do not
   set `GITHUB_TOKEN`/`GITLAB_TOKEN`; the mocked verbs never inspect them.
6. **`SimpleNamespace` vs `CompletedProcess`:** `_detect_remote` only reads
   `.returncode` and `.stdout` off the `subprocess.run` result, so a
   `types.SimpleNamespace(returncode=..., stdout=...)` stub is sufficient and
   avoids constructing a real `CompletedProcess`.

---

## 3. Link — what must be validated BEFORE building

Every fact below was re-read from the actual files this session:

- **L1 (target contract).** `mcp_server.py` read in full (148 lines); the six
  gap functions and their branches confirmed at the line numbers cited in
  Trace. The tool functions are directly callable (FastMCP returns the wrapped
  function) — confirmed by `test_broker_tool_surface.py` introspecting the same
  module and by the git-broker precedent calling tools directly.
- **L2 (no duplication).** `test_broker_pm_platform.py` (read in full) mocks
  `platform._http_request` and tests `parse_remote_url`, token resolution, and
  the `issue_*` REST verbs — it never touches `mcp_server.py`.
  `test_broker_tool_surface.py` (read in full) covers the 4-PM-tool set and
  force-param absence via `list_tools()`. The new file targets only the six
  wrapper gaps, which do **not** overlap those.
- **L3 (platform API used by the target).** Confirmed signatures in
  `platform.py`: `RemoteInfo(host, owner, repo, platform)` dataclass (line 32);
  `parse_remote_url(url) -> RemoteInfo` (67); `issue_create(remote, title,
  body=None)` (206); `issue_update(remote, issue_id, **fields)` (230);
  `issue_comment(remote, issue_id, body)` (242); `issue_close(remote,
  issue_id)` (258). The wrapper calls match these exactly.
- **L4 (broker profile — MEASUREMENT & COLLECTION).** `profiles.toml`
  `[profile.broker]` uses a digest-pinned `gleipnir-sandbox-broker` image
  (`--network=none`), runs `pytest` over an **explicit six-file list** (line 60,
  which already includes `test_broker_git_mcp_server.py` but NOT the new PM
  file), and sets coverage `--cov=src/gleipnir/broker --cov-branch
  --cov-report=term-missing` (line 62). **Consequence:** the new file must be
  added to line 60 (Tier-3 operator) or it is not collected — the hard gate in
  Decision 4 / E-COLLECT.
- **L5 (conftest collect_ignore).** `tests/conftest.py:27–31` skip-collects
  `test_broker_tool_surface.py`, `test_broker_git_commit_guard.py`, and
  `test_broker_git_mcp_server.py` when `mcp` is absent. The new file must be
  appended to that `collect_ignore` list (code agent, `tests/**` in grant). Its
  import shape (`from gleipnir.broker.pm import mcp_server`, which transitively
  imports `mcp`) is identical to the git file's, so it needs the identical
  treatment.
- **L6 (real git in the broker image, if the optional G1c real-repo variant is
  used).** The broker image (python:3.12-slim) provides `git`; the existing
  broker suite already does real `git` operations under this profile. But the
  recommended G1c route mocks `subprocess.run`, so real git is NOT a hard
  dependency for this plan.
- **L7 (code agent capability).** `gleipnir-code` may `edit "*"` except
  `.gleipnir/**`/`.git/**`/`preflight/**`; `tests/**` and `conftest.py` are
  in-grant. Its only test capability is `bin/gleipnir-sandbox test|lint`
  (exact-match). It holds no git. (Same capability profile relied on by the
  git-broker coverage-gap plan.)

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
`"tests/test_broker_pm_mcp_server.py"` to `[profile.broker].test` (line 60) so
`bin/gleipnir-sandbox test` (broker profile) collects it. **Operator-only
(Tier-3 POLICY, agent-unwritable).** This is the E-COLLECT gate; without it the
new tests are dead. *(If the operator prefers, the list could instead be
broadened to a `tests/test_broker_*.py` glob — but that is an operator design
call on the Tier-3 file, explicitly out of the code agent's scope; the planner
only requires the new file be collectible.)*

**Step 1 — [code] Author `tests/test_broker_pm_mcp_server.py`** covering G1–G6
per Trace §"How each gap is driven". Mock `platform.issue_*` for the happy /
field-building paths and `mcp_server.subprocess.run` for `_detect_remote`'s
error arms; use `_detect_remote`/`_remote_or_error` monkeypatching for the
wrapper error paths, with an `AssertionError`-raising `platform.*` fake to prove
no delegation happens on the error path. Add a module docstring naming the scope
and a note (mirroring the git file's header) that `profiles.toml` collection is
an operator prerequisite.

**Step 2 — [code] Amend `tests/conftest.py` `collect_ignore`** to append
`"test_broker_pm_mcp_server.py"` (so the lean python profile skip-collects it
when `mcp` is absent), alongside the existing three entries.

**Step 3 — [code] Run `bin/gleipnir-sandbox test` (broker profile)** and read
the term-missing coverage for `src/gleipnir/broker/pm/mcp_server.py`. Iterate on
tests until line+branch ≥85%. The `if __name__ == "__main__":` block (147–148)
is expected to remain uncovered and is pre-justified (import-time never runs it).

**Step 4 — [code] Report** pass count + line% + branch% for the target file,
name any residual-uncovered line with justification, and confirm no production
code changed.

**Step 5 — [quality] Blast-radius review** against this plan's Stress-test
checks (no duplication, no production change, gaps covered, target met).

**Step 6 — [git-ops] Commit** the new test file and the `conftest.py` edit.

**Assemble step order (summary):**
`0 (Tier-3 operator: profiles.toml collection amendment) →
1 (code: author test_broker_pm_mcp_server.py, G1–G6) →
2 (code: conftest.py collect_ignore) →
3 (code: sandbox test + iterate to ≥85% line+branch) →
4 (code: report) → 5 (quality review) → 6 (git-ops commit)`

---

## 5. Stress-test — acceptance checks

Concrete, checkable criteria the result is validated against.

- **A1 (coverage target met — measured).** `bin/gleipnir-sandbox test` (broker
  profile) term-missing output shows `src/gleipnir/broker/pm/mcp_server.py` at
  **≥85% line AND ≥85% branch**. Pass = the measured number in the sandbox
  report, not a claim. Any uncovered line is enumerated with a one-line
  justification; only line 148 (`if __name__ == "__main__":` / `mcp.run`) is an
  acceptable residual without further work (same shape as the git server's 99%
  result).
- **A2 (every gap exercised).** There is at least one test, with a contract
  assertion, for each of: G1 `_detect_remote` (subprocess-raise → RuntimeError,
  non-zero returncode → RuntimeError, success → parsed RemoteInfo); G2
  `_remote_or_error` (success `{"remote": …}` arm and error
  `{"error": {"success": False, "error": …}}` arm); G3 `issue_create`
  (error-no-delegation path + happy path, including `body=""` → `None`); G4
  `issue_update` (error path + field-building all-three-set / none-set /
  one-set-others-omitted + happy delegation); G5 `issue_comment` (error path +
  happy path); G6 `issue_close` (error path + happy path).
- **A3 (no duplication).** The new file does **not** re-test
  `platform.parse_remote_url`, token resolution, the `platform.issue_*` REST
  behaviour, or the tool-surface / force-param assertions already owned by
  `test_broker_pm_platform.py` and `test_broker_tool_surface.py`. Verified by
  reading the new file against those two.
- **A4 (no production change).** `git`-diff of `src/gleipnir/broker/**` is empty
  for this work (verifiable at the git stage). No behaviour was altered; only
  `tests/test_broker_pm_mcp_server.py` (new) and `tests/conftest.py`
  (collect_ignore append) changed.
- **A5 (no regression).** The full broker suite (existing six files + the new
  one = seven) passes under the broker profile; the lean python profile still
  runs green with the new file skip-collected (conftest amendment working).
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
| 0 | Add `tests/test_broker_pm_mcp_server.py` to `[profile.broker].test` in `.gleipnir/sandbox/profiles.toml` | **Tier-3 / operator only** | 0 |
| 1 | Author `tests/test_broker_pm_mcp_server.py` (G1–G6) | bounded `gleipnir-code` | 1 |
| 2 | Append the new file to `tests/conftest.py` `collect_ignore` | bounded `gleipnir-code` | 2 |
| 3 | Run `bin/gleipnir-sandbox test` (broker profile); iterate to ≥85% line+branch | bounded `gleipnir-code` | 3 |
| 4 | Report pass count + line% + branch% + residual justification | bounded `gleipnir-code` | 4 |
| 5 | Quality blast-radius review vs Stress-test | quality-reviewer | 5 |
| 6 | Commit the two files | git-ops | 6 |

### Notes the implementing agent needs (so it does not rediscover context)

- **Driving the tools:** import `from gleipnir.broker.pm import mcp_server` and
  `from gleipnir.broker.pm import platform`. The tool functions are directly
  callable (`mcp_server.issue_create(...)`, `.issue_update(...)`,
  `.issue_comment(...)`, `.issue_close(...)`), each returns a **JSON string** —
  `json.loads` it. `_detect_remote` and `_remote_or_error` are module-level and
  directly callable/patchable.
- **Mocking boundaries (Decision 2):**
  - `monkeypatch.setattr(platform, "issue_create", recorder)` (and `issue_update`
    / `issue_comment` / `issue_close`) — a recorder that stores its
    positional+keyword args and returns a canned dict. Mirror the
    `_RequestRecorder` shape from `test_broker_pm_platform.py:152`, but adapted
    to each verb's signature.
  - `monkeypatch.setattr(mcp_server.subprocess, "run", fake)` — for
    `_detect_remote`'s raise / non-zero arms. Return a
    `types.SimpleNamespace(returncode=…, stdout=…)`; `_detect_remote` reads only
    `.returncode` and `.stdout`.
  - For wrapper error paths: `monkeypatch.setattr(mcp_server, "_remote_or_error",
    lambda repo_dir: {"error": {"success": False, "error": "…"}})` (or patch
    `_detect_remote` to raise `RuntimeError`), plus set the target
    `platform.*` verb to a fake that raises `AssertionError` if called (the
    "network-forbidden" pattern at `test_broker_pm_platform.py:133`) to prove no
    delegation on the error path.
- **`RemoteInfo` in fakes:** `platform.RemoteInfo(host="github.com",
  owner="owner", repo="repo", platform="github")` — all four fields required.
- **`body or None` (G3b):** add a `body=""` case asserting the recorder received
  `None`, exercising the `or None` conditional on line 79.
- **No tokens needed:** mocking at the `platform.*` verb boundary is above
  `get_token`, so no `GITHUB_TOKEN`/`GITLAB_TOKEN` env setup is required.
- **Run command (exact):** `bin/gleipnir-sandbox test` resolves the broker
  profile per `profiles.toml`; coverage is emitted automatically
  (`--cov=src/gleipnir/broker --cov-branch --cov-report=term-missing`). Read the
  `pm/mcp_server.py` row of the term-missing table for the number and the
  uncovered-line list.
- **If a test only passes by editing `mcp_server.py`:** STOP, report the
  suspected bug as a new decision (do not weaken the test, do not patch). Per
  Decision 5, none is expected.
