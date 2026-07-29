# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

All six enforcement guards (G-1..G-6) have real, tested first slices, plus a
language-agnostic sandbox executor (node profile + broker profile live),
two broker MCP servers (gleipnir-git / gleipnir-pm with single-holder scoping),
the tier3-coach skill for control-gap proposals, the session-scribe bookkeeping
role, and the orchestrator interactive-session context-cap feature. Latest
committed + pushed state is on `origin` (`git@github.com:Djarid/gleipnir.git`,
branch `main`). Tests: **broker profile 43 passed; python self-host 476 passed /
11 skipped**. All features verified live post-restart (git-ops sees 4 git tools,
zero pm tools; push_current_branch functional in production; dogfood node test
16/16 pass in-container).

## Built slices (verified against disk / commits)

- **G-1 unreachable-guards closure** — fail-closed boundary preflight
  (`src/gleipnir/preflight/`, `bin/gleipnir-preflight`); commit `5cd329c` (+
  `356eb05`). OS-perms floor; behavioural-probe, fail-closed; per-file walk.
- **G-2 capability removal** — ephemeral sandbox (`--network=none`, ro source);
  `src/gleipnir/sandbox/`, `Containerfile`.
- **G-3.1 unforgeable marker** — keyed HMAC (`src/gleipnir/verify/`).
- **G-4 unblindable senses** — typed event bus + G-4d metrics ledger
  (`src/gleipnir/bus/`, `src/gleipnir/ledger/`); commits `2011737`, `7f4cc13`.
- **G-5 deterministic engine** — engine + revert edges + global revert budget
  (`src/gleipnir/engine/`); commit `3751163`.
- **G-6 memory-not-poisonable** — trust-tiered `.gleipnir/` layout + write model
  (`decisions/gleipnir-layout-and-memory-model.md`).
- **Armed-run dogfood** — the G-5 loop composes end-to-end (Python side verified;
  node cross-lang block committed but not-agent-run); commit `4ae2c36`.
- **Language-agnostic sandbox** — config-driven toolchain dispatch; the Tier-3
  arbiter (`.gleipnir/sandbox/profiles.toml`) is preflight-protected; commit
  `91d1127`. Corrects the "Python-only" mislabeling — Gleipnir guards
  multi-language targets.
- **session-scribe** (this slice) — Tier-0-scoped bookkeeping writer + the
  resume mechanism (this file). See `../decisions/session-scribe.md`.
- **Orchestrator interactive-session context-cap** — Tue 28 Jul 2026.
   Orchestrator runs on capped model `aperture-anthropic/anthropic.claude-opus-4-8-capped`
   (limit.context 250000 / output 32000, declared in `opencode.jsonc`);
   `gleipnir-plan` and `gleipnir-brainstorm` remain uncapped (scope verified, no leak).
   Single source of truth: `.gleipnir/policy/context-cap.jsonc` (cap_tokens 250000).
   At-cap compaction rules: `.gleipnir/plugins/compaction-survival.ts` (ported from AETOS).
   Durable record: `.gleipnir/decisions/context-cap.md` (policy enforced-at-hook, not yet G-1 closed).
   Operator restart-verified: Stress-test S1/S2 passed; 250000 window confirmed.
   **Observed seam:** gleipnir-code enforces grant denies ALL `.gleipnir/**` writes
   (no Tier-0 `var/tmp` carve-out), vs AGENTS.md narrating `var/tmp` as agent-writable —
   candidate lesson on doc-vs-grant discrepancy.
- **Node profile real-run (language-agnostic sandbox, this session)** — CLOSED.
   `Containerfile.node` (FROM node:22-slim, digest-pinned) built to
   `localhost/gleipnir-sandbox-node`. Live profile `[profile.node]` in
   `.gleipnir/sandbox/profiles.toml`, digest-pinned. `tests/test_sequence_gate.mjs`
   **16 passed, exit 0** under `--network=none` in-container, INCLUDING the dogfood
   block (Python↔JS HMAC contract verified byte-for-byte). No regression: python
   self-host green. Decision record: `.gleipnir/decisions/language-agnostic-sandbox.md`.
- **Broker MCP servers: gleipnir-git + gleipnir-pm** — Completed this session.
   Two pointy stdio MCP servers, 4 tools each (git: `git_status`, `git_diff`,
   `commit_changes`, `push_current_branch`; pm: `issue_create`, `issue_update`,
   `issue_comment`, `issue_close`). Each independently versioned (0.1.0) in
   `src/gleipnir/broker/{git,pm}/` with own `pyproject.toml` + bounded `mcp>=1.0,<2`.
   **E-1 argument-policy half CLOSED structurally:** force-push absent from tool
   surface (no code path exists); `_run_git` refuses hook-bypass flags
   (`--no-verify`/`-n`/`-c core.hooksPath`), so agents cannot bypass operator git
   hooks. Credential-unreachability half still open (S-2 boundary). Single-holder
   scoping via TOP-LEVEL `tools:` frontmatter key with BOOLEAN values (`false`=deny),
   verified live post-restart: git-ops sees 4 git tools + ZERO pm tools;
   push_current_branch deployed to production (3 commits pushed). Guard policy
   (secret-scan/branch-protection/data-file) NOT enforced by broker; belongs in git
   hooks (see `.gleipnir/plans/precommit-hook-control-proposal.md`, proposal not yet
   operator-applied). Broker sandbox: `Containerfile.broker` + `[profile.broker]`
   isolate MCP SDK transitive tree; default_profile stays python; `conftest.py`
   skip-gates mcp-dependent test where mcp is absent. Tests: broker profile **43
   passed**; python self-host **476 passed / 11 skipped**. Decision record:
   `.gleipnir/decisions/broker-mcp.md`. Plan: `.gleipnir/plans/broker-mcp.md`
   (spec-review approved, 2 rounds). Commits: ad32280 (features), a bool-fix commit,
   c8050da (scoping fix) — all pushed to origin/main.
- **Tier3-coach skill (originated gleipnir; not AETOS-inherited)** — Added to
   `.gleipnir/skills/tier3-coach/SKILL.md`. Loaded by gleipnir-brainstorm when
   an enforcement-control gap in an agent-unreachable layer is found.
   Detect→Locate→Propose→Converge→Handoff workflow; never implements. See
   `.gleipnir/skills/tier3-coach/SKILL.md` for full methodology.

## Open threads / next

**Wed 29 Jul 2026 — Post-broker-MCP session:**
- Broker MCP servers live; single-holder scoping verified; E-1 argument-policy structurally closed (credential half open).
- **MCP-scoping incident (3 distinct bugs found+fixed, session seam):**
   - Bug 1: `permission.tools` requires `allow/deny/ask`, not booleans (operator caught; fixed).
   - Bug 2: global-disable-then-per-agent-`permission.tools:allow` does NOT surface MCP tools to subagent (discovered live via git-ops probe; unverified: commit tool missing from function list).
   - Bug 3: `permission.tools: deny` does NOT gate MCP visibility for a subagent either (discovered via SECOND live probe: git-ops saw pm tools despite deny). Working fix: per-agent scoping ONLY in TOP-LEVEL `tools:` key with booleans (enable globally, deny per-agent).
   - **Lesson records:** L-C12 (boolean/allow-deny grammar split), L-C12b (deny-list scoping pattern, subagent tool visibility triple-check).
- **Blast-radius near-miss:** hunk-split commit via `git add -p` DESTROYED 12 tracked files' uncommitted edits mid-task (subagent step cap hit). Recovered by hand-rebuilding from decision records. See lessons L-C11, L-C12, L-C12b for full detail.
- **Immediate next:** S-2 activation (operator) — dedicated agent uid + chmod OS-ro + G-3 key OS-unreadable + `bin/gleipnir-preflight` enforcement.

## Open seams (absorbed from the old session-seams-ledger.md; NOT authoritative)

- **S-2 activation (operator):** dedicated agent uid + chmod OS-ro + G-3 key
   OS-unreadable + `bin/gleipnir-preflight` (code built, commit `5cd329c`).
- **S-2 mount + terminal closure + S-3 preflight wiring:** the structural
   boundary that makes `.gleipnir/` unwritable (vs today's preflight OS-perms
   floor).
- **E-1 credential-unreachability half:** brokers run as opencode stdio subprocesses,
   not outside S-2; SSH/git-credential-helper and env-injected GITLAB_TOKEN/GITHUB_TOKEN
   still co-located with session. Argument-policy half closed (no force-push path).
- **E-2** platform-webhook receiver; **E-3** novelty-triage signal quality.
- **G-4 remainder:** observer, novelty triage (G-4c), TS-side emit;
   cost/economic-chain in the ledger (needs S-2 rate-table + token provenance).
- **Engine hybrid-C per-stage escalation:** deferred (global revert budget is
   the current trigger).
- **Live TS `tool.execute.after` advance hook** (armed-run dogfood seam 7);
   real-CI attestation feeding `attempt_gate` / G-3.2 sourcing (seam 8).
- **Rust/C/C++ sandbox profiles** + the offline-deps fetch-then-seal decision.
- **`bin/gleipnir-sandbox lint`** fails writing `__pycache__` under the ro `src`
   mount (pre-existing, all files).
- **git-ops allowlist** lacks `git diff`/`git log` (read-only inspection gap).
- **Option C — plugin-hosted typed bookkeeping tools** (the session-scribe
   graduation target; not built).
- **quality-reviewer returns EMPTY on plan-review tasks** (observed ~3x earlier
   session — a reliability seam; the orchestrator had to self-verify plans by
   direct read). Worth a candidate lesson.
- **Broker guard policy enforcement:** secret-scan / branch-protection / data-file
   checks NOT enforced by broker (avoids AETOS's false-positive lockup problem) —
   they belong in git hooks. See `.gleipnir/plans/precommit-hook-control-proposal.md`
   (proposal; not yet operator-applied — a tier3-coach output).

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C10 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
