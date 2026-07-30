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
role with Tier-0→Tier-2 lesson-escalation process (A-hybrid; live-verified end-to-end),
config-scoping preflight (config_scan.py; 143 tests, full coverage, closes L-C12/L-C12b class),
and the orchestrator interactive-session context-cap feature. Latest committed + pushed
state is on `origin` (`git@github.com:Djarid/gleipnir.git`, branch `main`).
Tests: **broker profile 43 passed; config-scan 143 passed; python self-host 476 passed /
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
- **Pre-commit hook enforcement (git-ops guard policy)** — APPLIED and verified
   this session. Git hooks installed (`hooks/pre-commit`, activated via
   `core.hooksPath=hooks`). Runtime verification: secret-scan REFUSED untrusted
   content; clean commit PASSED; strict branch-protection (no explicit push to
   main) enforced; operator `--no-verify` bypass works; agent cannot bypass
   (flag-injection defended + message-text false-positive fixed, commit `abc7def`).
   Scope: local/opt-in/per-clone, verified no auto-install, no CI enforcement.
   See `.gleipnir/decisions/broker-mcp.md` and updated
   `.gleipnir/plans/precommit-hook-control-proposal.md` (team-impact note).
- **git-ops step budget raised 15→30** — During hunk-split commit (`git add -p`),
   a 15-step cap exhaustion destroyed 12 tracked files' uncommitted edits
   mid-task (blast-radius incident). Budget raised to 30 post-recovery;
   reversion testing green. Lesson L-C11 graduated.
   Commits: merged into main, pushed.
- **Tier-0→Tier-2 lesson-escalation process (A-hybrid)** — Thu 30 Jul 2026. FULLY LANDED.
   Extends session-scribe's write grant to `.gleipnir/lessons/session-lessons-candidates.md`
   (single named file, not blanket lessons/) as interim substitute for not-yet-built G-4c
   review-gated pipeline. Human review satisfied upstream: orchestrator confirms drafted
   lesson text via `question` (2-round cap) before delegating append to session-scribe.
   Full pipeline: brainstorm (alternatives A/A-hybrid/B/C + weighted decision matrix + bias
   check) → plan (ATLAS Architect/Trace) → spec-review (caught defect: plan claimed
   compaction-durability not in edit; fixed and re-reviewed) → approved. Live end-to-end
   verified: L-C14 appended through new process using session-scribe's grant with
   orchestrator UNCONSTRAINED by build mode. Orchestrator body section ("Lesson-candidate
   escalation (A-hybrid; standing discipline)") + compaction_survival frontmatter bullet
   (durability) now in `.gleipnir/agents/orchestrator.md`. 8-step process documented:
    notice→draft, coalesce-within-one-turn (never pending), present verbatim, confirm,
    provenance stamp, delegate, verify, report. Superseded earlier tier2-escalation-control-proposal.md
    sketch (mechanism decision Option A remains valid). Commits: d72eec3 (mechanism) +
    0b3b0f7 (bundled with config-scan plan). Durable decision record:
    `.gleipnir/decisions/lesson-escalation.md`; Tier-0 plan docs:
    `.gleipnir/plans/lesson-escalation-process.md`, `.gleipnir/plans/lesson-escalation-process-brainstorm.md`,
    `.gleipnir/plans/tier2-escalation-control-proposal.md`.
- **Config-scoping preflight (config_scan.py) — FULLY IMPLEMENTED.** Thu 30 Jul 2026.
   Closes L-C12/L-C12b class (restart-only-observable config bugs) by validating agent/config
   CONTENT (YAML grammar, effective per-agent MCP tool-grant sets) vs OS write/read perms alone.
   ATLAS plan `.gleipnir/plans/config-scoping-preflight.md` (8 findings fixed, 2 spec-review
   rounds) + dedicated design-coherence pass (caught argument-order mismatch: tests declared
   authoritative). Test-first: 6 files, 143 tests (full API specification + incremental build).
    Implementation: `src/gleipnir/preflight/config_scan.py` (new), wired as `config-scan`
    subcommand into `src/gleipnir/preflight/__main__.py` (leading-token dispatch, zero behaviour
    change to boundary check). Two real defects fixed: (a) cross-file glob inconsistency violated
    Design Consolidation Decision 2; (b) malformed-but-grammar-legal tools:/permission non-dict
    value crashed uncaught — fixed at primary checkpoint (check_grammar) + defense-in-depth
    guards with 15 regression tests. Final: 143 tests, 90% line+branch coverage, 619 passed /
    11 skipped, zero regressions, quality-APPROVED. NOT yet wired to run automatically (git hook,
    CI) — deferred, needs convergence. Residual fast-follow (non-blocking): config_scan_main
    jsonc "agent" block assumes dict; malformed opencode.jsonc could raise. Commits: 0b3b0f7
    (plan+tests) + c3c93ea (implementation). Durable decision record:
    `.gleipnir/decisions/config-scoping-preflight.md`; Tier-0 plan:
    `.gleipnir/plans/config-scoping-preflight.md`.

## Open threads / next

**Thu 30 Jul 2026 — Post-config-scan + lesson-escalation session:**
- Lesson-escalation process live and end-to-end verified; config_scan.py fully tested & implemented (143 tests, 90% coverage).
- **Small/immediate:** Bake the `## Decisions (index)` table into `goals/plan-format.md` as a required plan section — from L-C14's own proposed lesson (Tier-3, needs build mode, not yet done).
- **Deferred convergence items:**
   - Config_scan hook/CI wiring (follow-on, needs dedicated convergence for when/where to enforce).
   - Stage-role-map precedence question for prose/config-only plans (flagged during escalation-process plan, not yet ratified).
- **Confirmed FIXED:**
   - Empty-return reliability seam (L-C13) FIXED post-restart — last several quality-reviewer/session-scribe delegations this session ended with proper written reports, not empty returns.
   - Git-ops git diff/log gap (E-seam residual) FIXED and pushed earlier this session (commits included in main).
- **S-2 activation still deferred** (operator call) — unchanged.

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
- ~~**Broker guard policy enforcement:** secret-scan / branch-protection / data-file
   checks NOT enforced by broker (avoids AETOS's false-positive lockup problem) —
   they belong in git hooks. See `.gleipnir/plans/precommit-hook-control-proposal.md`
   (proposal; not yet operator-applied — a tier3-coach output).~~ **CLOSED** — pre-commit
   hook applied, activated, and verified (see Built slices).

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C10 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
