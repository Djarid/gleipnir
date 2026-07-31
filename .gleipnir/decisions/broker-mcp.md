# Decision: git + PM broker MCP servers (`gleipnir-git` / `gleipnir-pm`)

**Status: authored, partially closed.** Durable decision record. Realises the
spec T-2 broker / G-2 single-holder tool surface and closes the
**argument-policy half of E-1** for git; leaves the credential-unreachability
half open (S-2). Authored by the operator via the build-mode escape hatch
(Tier-3). Plan of record: `../plans/broker-mcp.md` (spec-review APPROVED, 2
rounds; quality-reviewed). Converged brief: `../plans/broker-mcp-brainstorm.md`.
Dependency amendment: `runtime-and-deps.md`. Sandbox profile:
`language-agnostic-sandbox.md` (broker profile).

## Why

`git-ops` performed git via a raw-`git` bash allowlist whose force-push denies
were **by pattern** — the enumerable-bypass weakness G-2 exists to remove (the
E-1 seam). `project-mgr` had no PM tool at all. AETOS's `aetos-git`/`aetos-pm`
MCP servers were the **pattern to influence from** (operator: "influence, don't
steal") — tool shape, guard structure, platform split — reimplemented fresh for
Gleipnir, not copied.

## What was decided and built (operator-converged)

- **Two pointy brokers, 4 tools each** (no scope creep):
  - `gleipnir-git`: `git_status`, `git_diff` (read); `commit_changes`,
    `push_current_branch` (write, gated).
  - `gleipnir-pm`: `issue_create`, `issue_update`, `issue_comment`,
    `issue_close`. Stateless, no local cache (v0.1 simplification).
- **E-1 argument policy — structural, not pattern-based.** `push_current_branch`
  constructs only `["push","origin",branch]` (+ a `-u` retry). No tool exposes a
  force parameter; `--force`/`-f` appear in no argv — force-push is
  **structurally absent**, verified by `tests/test_broker_tool_surface.py`
  (asserts no tool input schema has a force param) and by code review.
  `commit_changes` runs `guards.precommit_check` on the staged diff AFTER
  staging but BEFORE the `git commit`, and on a secret finding refuses without
  committing (`git reset HEAD` — a mixed, index-wide unstage that never touches
  the working tree). The always-on secret-scan is the only default-blocking
  check; protected-branch/data-file checks stay opt-in via the `GLEIPNIR_GIT_*`
  env vars. (HONESTY NOTE: this in-broker enforcement was NOT true when this
  record was first written — `commit_changes` then ran a plain `git commit` with
  no policy of its own, and the secret-scan reached agent commits only as a
  side-effect of the operator's installed `pre-commit` hook firing. The
  git-enforcement layered design — see
  `../plans/git-enforcement-plugin.md` — moved the secret-scan into the broker
  where the staged diff is visible; this line now reflects the implemented code,
  not an aspiration.)

- **Non-strict by default — the broker must not be so constraining that people
  route around Gleipnir entirely.** A guard that nags more than it protects gets
  bypassed, and then even its real safety value is lost. So the checks are split
  by nature:
  - **Safety (always on):** structural force-push absence + **secret-scan** of
    the staged diff. Committing a live credential is genuine, hard-to-undo harm;
    this is the check that makes the broker worth adopting. Always enforced,
    every branch, every mode.
  - **Workflow/hygiene (opt-in, DEFAULT OFF):** protected-branch refusal
    (`GLEIPNIR_GIT_PROTECT_BRANCHES`, or strict) and data-file detection
    (`GLEIPNIR_GIT_CHECK_DATA_FILES`, or strict). These are preferences, not
    safety invariants. **`GLEIPNIR_GIT_STRICT`** turns both on at once.
  - **Why default OFF matters for autonomy tiers (L2/L3):** a hard
    protected-branch refusal would **deadlock an autonomous operator** — there is
    no human to answer a "switch off main" prompt. And trunk-based developers /
    the operator who commits straight to `main` are doing nothing unsafe;
    refusing them conflates "my preferred workflow" with "safety." Non-strict
    mode lets them work; teams who want the discipline opt into strict.
- **`git-ops` allowlist narrowed, not deleted.** Dropped `git add*`/`git commit*`/
  `git push*` (now the broker's tools) and the two force-push pattern denies;
  **kept** `git status*`/`checkout*`/`switch*`/`branch*`/`merge*`/`fetch*`/
  `pull*` — non-dangerous branch/sync verbs with no MCP replacement, so a
  session left on a protected branch can still move off it (deadlock avoidance
  — caught in spec-review, converged with the operator).
- **Single-holder scoping — DENY-LIST pattern via TOP-LEVEL `tools:` booleans
  (AETOS-proven; twice-corrected).** MCP tools are **enabled globally**
  (`opencode.jsonc` `mcp` block, no top-level `tools` disable), and **each agent
  frontmatter DENIES the namespace(s) it must not hold using its TOP-LEVEL
  `tools:` key with boolean `false`** — NOT `permission.tools` (verified live:
  a `permission.tools: deny` does NOT block MCP tools for a subagent).
  `git-ops` sets `tools: {gleipnir-pm_*: false}` (keeps `gleipnir-git_*`);
  `project-mgr` sets `{gleipnir-git_*: false}` (keeps `gleipnir-pm_*`); every
  other roster agent sets BOTH to `false`. Tool names are `<server>_<tool>`, so
  the glob uses the underscore form `gleipnir-git_*` / `gleipnir-pm_*`. See
  lessons L-C12b.
  **Why not global-disable + per-agent re-allow (the initially-shipped, then
  disproven, approach):** a top-level `tools: {gleipnir-*: false}` global disable
  does NOT get re-enabled for a *subagent* by a `permission.tools: allow` — the
  MCP tools simply never surface to the subagent's function list (verified: the
  broker connected but `git-ops` could not see `commit_changes`). The deny-list
  (enabled-by-default, deny-what-you-shouldn't-hold) is the working form. See
  lessons L-C12 / L-C12b.
- **Each broker is its own independently-versioned component.**
  `src/gleipnir/broker/{git,pm}/` each has its own `pyproject.toml` + `VERSION`
  (starting 0.1.0) and its own **bounded** MCP-SDK compliance range
  `mcp>=1.0,<2`. Decoupled from each other and from the framework version.
- **Dependency: the MCP SDK (FastMCP), broker-layer only.** Recorded and
  justified in `runtime-and-deps.md`. The enforcement core stays stdlib-only;
  `mcp` is imported ONLY in the two `mcp_server.py` files (`guards.py`,
  `platform.py` are stdlib-only), asserted by `tests/test_broker_stdlib_only.py`.

## Version caveat (verified — do not repeat)

The naive `mcp>=1.0.0` resolves to **`mcp 2.0.0`, which REMOVED
`mcp.server.fastmcp`** (FastMCP split out). Each broker manifest therefore pins
the bounded, FastMCP-bearing range **`mcp>=1.0,<2`** (AETOS runs 1.27.1; we
verified 1.29.0 green). Never an open-ended `>=1.0.0`.

## Sandbox: separate broker test image (operator decision)

The broker tests can't run in the lean python self-host image (no `mcp`).
Rather than add `mcp` to the default image (which would put its large transitive
tree — pydantic, starlette, uvicorn, cryptography, httpx — inside the default
test blast radius), a **separate `gleipnir-sandbox-broker` image** was built
(`Containerfile.broker`, digest-pinned) and a `[profile.broker]` added to
`.gleipnir/sandbox/profiles.toml`. `default_profile` stays `python`, so the lean
image is unchanged. A `conftest.py` `collect_ignore` skips the mcp-dependent
`test_broker_tool_surface.py` under the python profile (where `mcp` is absent),
so the two profiles don't collide. See `language-agnostic-sandbox.md`.

## Verification

- Broker profile (`gleipnir-sandbox-broker`, `--network=none`, digest-pinned):
  **34 passed, exit 0**. `guards.py` 96% coverage.
- Python self-host profile: **468 passed, 11 skipped** (the broker
  stdlib-only tests — guards/platform/stdlib-only — run here too; tool-surface
  test skip-collected). No regression from the 438 baseline.
- Orchestrator-verified by direct read: T-A (structural force-push absence),
  gate-before-commit ordering, secret redaction, stdlib-only carve-out, 4+4 tool
  surface, no token leakage in error paths.

## Honesty labels / open items

- **Credential unreachability NOT closed.** The brokers run as opencode-launched
  stdio subprocesses, not a separate address space outside S-2. The PM broker's
  env-injected `GITLAB_TOKEN`/`GITHUB_TOKEN` and the git broker's ambient
  SSH/git-credential-helper reachability are still co-located with the session.
  This decision closes E-1's **argument-policy** half only. S-2 closes the rest.
- **`mcp` is a heavy dependency.** It pulls pydantic, starlette, uvicorn,
  cryptography, httpx — a large trusted surface. Justified as broker-layer (out
  of the stdlib-only enforcement core), isolated to the broker sandbox image,
  and bounded by the per-component compliance range. But it is a real surface to
  audit; a future stdlib JSON-RPC broker (the rejected Option A) would remove it.
- **`mcp_server.py` integration coverage gap (quality note).** The tool bodies
  in `git/mcp_server.py` (13%) and `pm/mcp_server.py` (25%) are thin wiring
  around the well-covered `guards.py` (96%) and `platform.py` (60%); full
  end-to-end tool invocation needs a live MCP client / real git subprocess.
  The correctness-critical logic (the guard, redaction, argv construction) IS
  covered where it lives. **Follow-up:** add integration tests that drive the
  tool functions (subprocess git in a temp repo; mocked REST for pm) to lift
  server coverage. Not blocking (E-1 correctness is verified), but tracked.
- **Restart required.** MCP config is read at opencode startup; the brokers and
  the per-agent tool grants take effect on the next launch (see restart-verify).
- **Cooperative-policy Tier-3.** `opencode.jsonc` is Tier-3 by intent but
  agent-writable today (repo root, outside `.gleipnir/**`); only agent files and
  decision records are capability-enforced. Same posture as `context-cap.md`.
