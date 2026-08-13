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
git-enforcement via layered plugin (config-scan gate) + broker (always-on secret-scan),
lesson corrections/additions (L-C16→L-C17 glob-fix guidance, L-C18 verbatim-reproduction rule),
glob-guidance + GOTCHA-inlining policy (Tier-3 edits applied; take effect next session),
and the orchestrator interactive-session context-cap feature. This session diagnosed
and fixed the root cause of a blocked/inaccessible pipeline session — a stale G-5 bridge
file combined with a stale `ROLE_STATES` binding in `allow_table.py` that predated the
`gleipnir-brainstorm`/`gleipnir-plan` role split (now fixed, commit `58dcbeea`, with an
L-C20 parity-test guard against recurrence). Latest committed + pushed state is on `origin`
(`git@github.com:Djarid/gleipnir.git`, branch `main`).
Tests: **broker profile 51 passed; python self-host 669 passed / 12 skipped; node profile 29 passed**.
All features verified live post-restart (git-ops sees 4 git tools, zero pm tools;
push_current_branch functional in production; dogfood node test 16/16 pass in-container).

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
- **Lesson corrections/additions (commit 4135546, extended this session)** — L-C16 glob-bug
   guidance corrected via L-C17 (the fix: `path` param, not "use read"); L-C18 added
   (orchestrator must reproduce subagent Decision Analysis verbatim, not paraphrase); L-C19
   (no in-framework recovery for stuck G-5 bridge; recovery-path design as required question);
   L-C20 (derivation is only as current as its input; ROLE_STATES parity test guards drift).
   File: `.gleipnir/lessons/session-lessons-candidates.md` (verified: L-C16–L-C20 present).
- **`allow_table.py` ROLE_STATES fix** — commit `58dcbeea`. Split of `gleipnir-brainstorm`
   and `gleipnir-plan` roles was live in stage-role-map.md but ROLE_STATES mapping was stale,
   causing allow-table derivations to fail for brainstorm tasks. Fixed: added entry
   `"gleipnir-brainstorm": frozenset({PipelineState.BRAINSTORM})`. L-C20 parity-test guard
   added to `tests/test_allow_table.py:55` ensures every roster role has an entry.
- **`bin/gleipnir-preflight` permission fix** — commit `9645974`. File was committed with
   mode `100644` (non-executable), blocking the always-active `git-guard.ts` gate which shells
   out to it before every broker git write; restored to `100755`. Regression guard: new test file.
- **`test_bin_executable.py` regression guard** — commit `6283cba`. New test file verifies
   every tracked `bin/*` file committed with executable bit (via `git ls-files -s`, not
   working-tree probe, to catch config-hidden regressions). Skips cleanly in environments
   without usable git tooling (e.g., `bin/gleipnir-sandbox test` in python:3.12-slim).
   Plan: `.gleipnir/plans/bin-executable-bit-fix.md` (Phase 1 B, agent-buildable, now complete).
- **Tier3-coach plans: bridge recovery + bin-executable 2-3 (APPLIED, this session)**
  — Both spec-review APPROVED plans now APPLIED and committed in build mode:
  - **Bridge recovery (L-C19)** — commit `1c91a19`. Adds `bridge-status` / `bridge-reset`
    subcommands to `bin/gleipnir-preflight` to inspect/clear stale G-5 bridge file.
    Implementation: `src/gleipnir/preflight/bridge_recovery.py` (bridge-status reads only,
    classifies as healthy/stale/corrupt-or-tampered/absent; bridge-reset deletes bridge only,
    requires `--confirm-clear` + `GLEIPNIR_OPERATOR_UID` opt-in, never re-mints state,
    refusal guard if invoked by non-operator uid, appends to `.gleipnir/logs/bridge-recovery.log`).
    Dispatch added to `src/gleipnir/preflight/__main__.py`. Companion permission-hardening:
    `gleipnir-code.md` now contains `"src/gleipnir/preflight/**": deny` (recovery tool source
    stays agent-unreachable). Decision record: `.gleipnir/decisions/bridge-recovery-path.md`.
    Tests: 669 passed / 12 skipped (test_bridge_recovery.py, 90% coverage on the new module).
  - **Git-guard diagnosability (bin-executable-bit-fix Phases 2–3)** — commit `42a4de5`.
    Phase 1 (test) was committed earlier; Phases 2–3 (implementation + decision record) now applied.
    `.gleipnir/plugins/git-guard.ts` now distinguishes a broken/missing preflight tool
    (`PreflightUnavailable`, still fail-closed) from a config-scan REFUSE, so a future
    occurrence is one-line "chmod this" fix rather than multi-step investigation.
    Decision record: `.gleipnir/decisions/bin-executable-bit.md`. Node tests 15 pass / 0 fail.
    Both commits spec-review APPROVED and quality APPROVED before commit.
- **Glob-guidance + GOTCHA-inlining policy (commits eb5c893, 0b221a3)** — Two
  converged+planned+spec-reviewed threads, applied to Tier-3: `.gleipnir/AGENTS.md`
  gained `## Tooling notes` section (canonical glob/`path` rule); `.gleipnir/agents/session-scribe.md`
  gained reference-only glob pointer bullet; `.gleipnir/skills/README.md` gained
  `## Who loads GOTCHA` intentional-policy note. Plans: `glob-guidance-placement.md`,
  `roster-gotcha-loading.md`. **RESTART-GATED**: take effect next session.
- **jsonc agent-block: crash-fix then GRAMMAR finding (commits 981623b, 98ec0c5, 9837d6d)**
  — First made `config_scan_main` crash-safe on non-dict `agent:` block (residual
  fast-follow, +7 tests). Then added `check_jsonc_agent_grammar` helper emitting
  GRAMMAR/FAIL finding (+13 tests; emit-before-coerce ordering; 91% coverage).
  File: `src/gleipnir/preflight/config_scan.py`, `tests/test_config_scan_grammar.py`,
  `tests/test_config_scan_cli.py`. Durable decisions in plans: `jsonc-agent-grammar-finding.md`.
  **CLOSES**: config_scan hook/CI wiring precursor (now superseded by Approach C);
  residual jsonc fast-follow. **CLOSES**: config_scan not auto-wired note
  (now wired via git-guard plugin, once it takes effect next session).
- **Git-enforcement via layered plugin + broker (Approach C) — commits 9cf8c96, 73f754b**
  — Operator-redirected away from git pre-commit hook/CI (principle: no non-Tier-3
  outbreak controls) toward opencode-plugin + broker split. Approach C: config-scan
  in plugin, secret-scan in broker; D9 compliance: ALWAYS-ACTIVE plugin, exit-2
  escape valve. Delivered:
  - `src/gleipnir/broker/git/mcp_server.py`: `commit_changes` now runs ALWAYS-ON
    secret-scan (guards.precommit_check) POST-STAGE/PRE-COMMIT, reset HEAD on finding.
    +7 broker tests (`test_broker_git_commit_guard.py`). Also fixed 3 false doc-claim
    strings (module docstring, commit_changes docstring, FastMCP instructions).
  - `.gleipnir/plugins/git-guard.ts` (Tier-3, NEW): opencode plugin on `gleipnir-git_*`
    tools; shells out to `bin/gleipnir-preflight config-scan`; exit 0/1/2 semantics
    (0=allow, 1=abort, 2=warn-proceed, other=fail-closed). +13 plugin tests
    (`test_git_guard.mjs`).
  - `Containerfile.broker`: added `git` binary (broker image lacked it; unblocked tests).
    Rebuilt; digest re-pinned in `.gleipnir/sandbox/profiles.toml`.
  - `.gleipnir/decisions/broker-mcp.md`: fixed SECURITY-HONESTY DRIFT (D2) — it falsely
    claimed `commit_changes` ran precommit_check when code ran plain `git commit`;
    now accurate + honesty note that this was aspirational-until-this-change.
  - **Verification**: broker profile 51 passed/0 failed; python 639/11; node 29 passed.
    No regressions. Plans: `git-enforcement-plugin.md` (spec-review approved).
  - **RESTART-GATED**: plugin takes effect next session.
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
- **`## Session resume` section added to `.gleipnir/AGENTS.md`** — Operator-applied in
    build mode this session (commits applied; to take effect next session). Closes the
    gap where a fresh session had no automatic pointer to the resume entry point. The
    new section (lines 151–178) instructs orchestrator to read `.gleipnir/plans/SESSION-STATE.md`
    at session start (conditionally, degrades gracefully if absent/fresh-clone), marks
    the file as a pointer/non-authoritative, and explicitly tells bounded subagents
    to skip it (with session-scribe documented as the exception, since it owns and churns
    the file). Plan: `.gleipnir/plans/session-state-startup-instruction.md` (spec-review
    APPROVED, 2 rounds). **RESTART-GATED** — takes effect on the very next session.
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

**Wed 12 Aug 2026 (continued) — Prose/config-only track + broker test coverage:**
- **Prose/config-only pipeline track — APPLIED + VERIFIED this session (build mode).** Converged on Approach B (brainstorm file `.gleipnir/plans/prose-config-only-track-brainstorm.md`). Plan `.gleipnir/plans/prose-config-only-track.md` (571 lines) spec-review APPROVED WITH NOTES (final, three rounds). Amendment now APPLIED to `.gleipnir/stage-role-map.md`: file grew from 61 to 167 lines; new "Prose/config-only track" section at line 63; byte-for-byte match to reviewed plan block confirmed. Purely additive — no existing lines altered. **Three non-blocking notes for FUTURE tightening pass** (not this plan's scope, remain open): (a) correspondence gate's "where applicable" same-file hedge is underdefined; (b) check pattern/target but not explicitly post-change artifact state; (c) fresh same-class non-blocking gap: repo-root `.gitignore` (governs key/digest git-tracking) also unenumerated by both axes, alongside noted `.envrc`/`pyproject.toml`. **Status: CLOSED — APPLIED + VERIFIED.**
- **Broker git MCP server coverage gap — COMPLETE + MEASURED this session.** Test file `tests/test_broker_git_mcp_server.py` (~612 lines) per spec-reviewed plan `.gleipnir/plans/broker-git-coverage-gap.md` (verdict: APPROVED WITH NOTES). Both operator actions completed: (a) `.gleipnir/sandbox/profiles.toml` line 60 now includes `tests/test_broker_git_mcp_server.py` (6 files in broker profile); (b) broker profile run in pinned sandbox image measured coverage. **RESULT: 78 passed / 0 failed; `src/gleipnir/broker/git/mcp_server.py` coverage rose from 52% to 99% (124 stmts / 1 missed / 58 branch / 1 partial).** Only miss is line 417 (`if __name__=="__main__"` entry guard, unreachable under pytest). Comfortably clears ≥85% target. New test file added 27 tests, all green; no regression in other 5 broker test files. **NOTE:** aggregate broker TOTAL was 77% after this work because SEPARATE `pm/mcp_server.py` was at 25% — the pre-existing "pm broker coverage" follow-up item, distinct from the git-server gap (now closed 52%→99%). **SEE NEXT ITEM: pm-broker gap is now COMPLETE.**
- **Broker pm MCP server coverage gap — COMPLETE + MEASURED this session.** Follow-on to the git-server coverage work (the pre-existing "pm broker coverage" follow-up, now closed). Test file `tests/test_broker_pm_mcp_server.py` (16 tests) per spec-reviewed plan `.gleipnir/plans/broker-pm-coverage-gap.md` (verdict: APPROVED WITH NOTES; 3 doc-precision nits folded in). Covers the previously-untested pm wrapper layer: `_detect_remote` (subprocess-error / non-zero-returncode / success arms), `_remote_or_error` (both arms), and the four `issue_*` tool wrappers including `issue_update`'s conditional field-building. Both wiring edits applied (build mode): `.gleipnir/sandbox/profiles.toml` broker test list (now 7 files) + `tests/conftest.py` collect_ignore (now 4 entries). **RESULT: 94 passed / 0 failed; `src/gleipnir/broker/pm/mcp_server.py` coverage rose from 25% to 97% (57 stmts / 1 missed / 18 branch / 1 partial).** Sole miss is line 148 (`if __name__=="__main__"` guard). Clears ≥85% target. No regressions. Aggregate broker TOTAL now 86% (up from 77%); remaining low spot is the SEPARATE `pm/platform.py` at 60% — a distinct, still-open follow-up, not part of this gap. Committed `c2654d3` (not yet pushed at time of this note).
- **Broker pm platform.py coverage gap + GHE auth bug fix — COMPLETE this session.** Started as a pure coverage task (`platform.py` was at 60%) but spec-review found a REAL production bug: `_http_request` selected the auth header via `if "github" in url:` (case-sensitive URL substring) instead of by `remote.platform`, so a GitHub Enterprise host with a custom domain lacking the literal "github" substring (e.g. `git.mycorp.com`) — correctly detected as platform=="github" and routed to the `/api/v3` GHE base everywhere else — would get the WRONG auth header (PRIVATE-TOKEN instead of Bearer), breaking GHE-custom-domain auth. Operator converged (via `question`) on FIX-AND-COVER. **The fix:** added a required keyword-only `platform: str` param to `_http_request`, header now keys off `platform == "github"` → Bearer else PRIVATE-TOKEN; all 4 issue_* call sites pass `platform=remote.platform`. Plan `.gleipnir/plans/broker-pm-platform-coverage.md` (2 spec-review rounds: R1 CHANGES REQUESTED surfaced the bug, R2 APPROVED WITH NOTES on the fix design; post-implementation quality review APPROVED, no findings). Extended existing `tests/test_broker_pm_platform.py` (no new file, no profiles.toml/conftest change — already collected). **RESULT: 699 passed / 12 skipped; `src/gleipnir/broker/pm/platform.py` now 100% line + 100% branch (128 stmts/0 miss, 46 branch/0 partial).** GHE fix proven two ways (direct-seam + full-path with urllib mocked, asserting corrected Bearer behavior). Exactly two files changed (platform.py + its test); no scope creep, no weakened tests. Commit pending. **This closes the last of the broker coverage follow-ups** — git/mcp_server 99%, pm/mcp_server 97%, pm/platform 100%.
- **L-C23 recorded (this round).** Lesson candidate appended: "A long Decision Analysis embedded inside the `question` tool's field makes the options inaccessible; print it as response text first, then ask a short question." Fix: print analysis verbatim as response text first, then call `question` with SHORT prompt ("Given the analysis above, which option do you converge on?"). This satisfies L-C18 (verbatim reproduction, via "immediately precede" clause) while keeping question UI usable. Dated 2026-08-12, same provenance pattern as L-C19–L-C22 (operator-confirmed via question, interim gate).
- **S-2 activation — ATLAS plan APPROVED, C2 control proposal drafted, awaiting operator application of OS acts.** S-2 is the biggest remaining item: turning enforcement from cooperative-policy into a structural OS boundary. Brainstorm brief `.gleipnir/plans/s2-activation-brainstorm.md` (~502 lines), operator-converged on **Approach C (staged hybrid), landing on the Approach-A uid-floor**. ATLAS plan `.gleipnir/plans/s2-activation.md` (461 lines) **APPROVED after hardened-path spec-review** (2 rounds: R1 CHANGES REQUESTED on 3 blast-radius defects — missing `sudo` on the acceptance test, a circular C1→C2 ordering rationale, and incomplete dir-hardening for `agents/`/`keys/` — R2 APPROVED with negative-check attestation confirming no LOCKED enforcement path is in the write-grant loop and the key ends RO_AND_UNREADABLE). **KEY FINDING: C1 is NOT new code** — the dev-mode path (`--override-ack` → PROCEED_UNCLOSED, DEV_MODE_LABEL, full per-session reasons dump) already exists in `bin/gleipnir-preflight`/`boundary.py` (verified source lines cited in plan). The only agent-buildable artifact is the Tier-0 launch-habit doc; everything with teeth (the C2 OS acts) is operator-only. **C2 acts are operator-only and NOT yet applied** — they form a ready-to-apply tier3-coach control proposal inside the plan: create dedicated agent uid (dscl/sysadminctl), chmod the 8 LOCKED ENFORCEMENT_PATHS OS-ro to the agent uid, place the G-3 key mode-600 RO_AND_UNREADABLE, install the sudo-invoked launch-as-agent-uid wrapper, set ownership/group layout. macOS-specific: dropping to a different uid requires the launcher to be root (sudo). **C1→C2 flip gate (D-G):** N≥5 clean advisory-mode sessions (empty reasons list) after OS acts applied, THEN flip to hard fail-closed. DEV_MODE_LABEL keeps un-closed status visible every launch. **Status: plan APPROVED, awaiting operator application of the C2 OS acts.** No roster agent can perform them. Everything downstream (Tier-2 memory pipeline, G-4d real cost, keys/ digests + S-3) stays gated until the floor holds. Commit pending.rator can apply. Several deferred items (Tier-2 memory pipeline, G-4d cost ledger, digest verification) are all "gated on S-2" and unblock once the floor holds.
- **`bin/gleipnir-sandbox lint` read-only-mount bug — FIXED this session.** `python -m compileall` wrote `.pyc` into `src/**/__pycache__/` which failed on the read-only `/work` mount (`OSError: Read-only file system`) for every file. Fix (D1): `_cmd_lint` now passes `extra_env=[("PYTHONPYCACHEPREFIX", "/work/.scratch/pycache")]` into `prepare_sandbox_run`, redirecting bytecode output into the existing rw scratch mount; keeps the real byte-compile check, writes nothing under the ro mount. Fixes both python and broker compileall profiles via the profile-agnostic `_cmd_lint` (no Tier-3 profiles.toml change — D2); inert for the node `--check` profile. Verified live: lint now runs clean (exit 0, no OSErrors). Plan `.gleipnir/plans/sandbox-lint-fix.md` (spec-review APPROVED WITH NOTES, 3 D4/blast-radius notes folded in). Tests: `tests/test_sandbox_cli.py` +3 (python-profile redirect assertion, broker-profile redirect assertion, exit-code-propagation regression guard); full sandbox suite 701 passed / 12 skipped. **The suspected "Bug 2" (lint false-green: exit 0 despite errors) was found NOT to exist** — it was a `| tail` measurement artifact in the orchestrator's own diagnostic; compileall + lint propagate exit codes correctly (see corrected D4 in the plan; L-C25). **Two lesson candidates recorded this round:** L-C24 (empty subagent return hid an orphaned broken fixture left in the live src/ tree — verify against disk; a blast-radius cleanup condition must be verified not trusted) and L-C25 (a bug report can be a measurement artifact — reproduce the raw signal before planning a fix). Commit pending.
- **Prose/config-only track — 3 tightening notes APPLIED this session (hardened-path dogfood).** The three non-blocking round-3 review notes on the track are now folded into `.gleipnir/stage-role-map.md` (grew 167→201 lines): (1) removed the correspondence rule's underdefined "where applicable" hedge — same-file matching is now ALWAYS required, and summary criterion (iv) reconciled to match the detail rule; (2) added a "Post-change-state rule" requiring attestation evidence be captured against the applied/post-change file state (all 4 evidence forms), with new summary criterion (v); (3) enumerated `.gitignore`, `.envrc`, `pyproject.toml` into the enforcement-path set `E` (explicit enumeration, the opencode.jsonc precedent, not a fuzzy predicate) — each always-hardened by exact-path match. Plan: `.gleipnir/plans/classifier-tightening.md`. **Notably: this plan was itself enforcement-bearing (it amends stage-role-map.md ∈ E), so it ran the track's OWN hardened path — a clean dogfood.** Hardened review: quality-reviewer ran TWO separate non-fusing rubrics (SPEC-CONFORM: PASS + BLAST-RADIUS: PASS) plus a negative-check attestation; orchestrator (in build mode) applied the 4 edits by text-match and re-ran the post-apply negative-check attestation against the LIVE file (per the very post-change-state rule the plan installs): both rows PASS (E-set has the 3 exact literals, NO over-broad glob form; operative "where applicable" hedge absent). All 5 SUCCESS-gate clauses satisfied. Non-blocking future-round candidates named by review: `.gitattributes`/`.gitmodules`/lock-files are the same class, not yet enumerated (accepted per the explicit-enumeration tradeoff). Commit pending.
- **G-4 next slice — terminal-events + ledger metrics — BUILT this session.** Brainstormed the next G-4 slice; operator converged on Candidate 1 (new engine-computed terminal/interoceptive event kinds + ledger metrics). During ATLAS planning, gleipnir-plan found the brief's premise was partly WRONG (verified in engine source): the engine has NO iteration/retry concept (FAIL routes backward = a revert, already emitted; escalation already captured by RevertOccurredEvent.escalated; only cap is the global revert budget). Operator was re-consulted (via `question`) and converged on the buildable-now substitute the planner found: two genuinely-new driver-observable terminal facts. DELIVERED: (1) two new EventKinds `NEEDS_HUMAN_RAISED` + `GATE_REACHED` with typed frozen payloads in `src/gleipnir/bus/events.py`; (2) driver emits them (`src/gleipnir/engine/driver.py`) via a SEPARATE `_emit_needs_human_if_any` sibling method + an `attempt_gate` wrapper — engine stays PURE (no bus import; AST invariant test green), write-bridge-before-emit + degrade-not-raise preserved; (3) two new honest `Measured` metrics `human_question_count` + `gate_reached_count` in the ledger (`reduce.py`), raw counts (denominator=1, empty log → Measured(0,1) not Gap); (4) reconcile.py updated with matching INDEPENDENT re-derivation (LOCKED g4d-ledger.md D4 consistency preserved). The ledger's `iterations`/`retries` seams stay honest Gaps but with CORRECTED reasons (the true blocker: engine has no iteration/retry concept — not the old misleading "no XEvent kind yet"). No redundant escalation metric added. Pipeline: brainstorm → plan → spec-review (APPROVED WITH NOTES) → code (test-first) → quality (APPROVED WITH NOTES). Tests: 732 passed / 12 skipped (+31 from the slice); coverage bus/events 95%, driver 98%, reduce 96%, reconcile 95%. **Known constraint (accepted):** these metrics are test-exercised only until Seam 7 (the live tool.execute.after advance hook) lands — this widens WHAT the senses measure, not whether emission lands live. **Tier-3 doc drift FIXED:** `g4-bus.md` line ~62 (said the driver emits nothing on NEEDS_HUMAN — now inaccurate) was amended in build mode to reflect the new sibling-method emit, history preserved. **Process note:** gleipnir-code returned EMPTY 3x this session on this slice (work landed on disk each time but no report) — verified against disk each time per L-C24; the ledger half was initially skipped (caught by disk-verify) then completed on re-delegation. Deferred (gated): token-provenance/cost/effort (need Seam 7 / S-2), novelty triage (needs signal history). Commit pending.

---

**Wed 12 Aug 2026 — Post-bridge-recovery diagnosis session:**
- Session found and fixed the root cause of a blocked/inaccessible pipeline session: stale G-5 bridge
  + stale ROLE_STATES binding predating the brainstorm/plan split. **Root-cause commits:**
  `58dcbeea` (allow_table.py fix), `9645974` (bin/gleipnir-preflight perm fix), `6283cba`
  (test_bin_executable.py regression guard).
- **L-C19 and L-C20 recorded in lessons file** — now formally captured as candidate lessons:
   L-C19 (recovery-path as required design question for fail-closed gates); L-C20 (parity test
   guards drift in "derived, not duplicated" projections). Both dated 2026-08-12. **L-C21 and
   L-C22 also appended this session:** L-C21 (SESSION-STATE.md's "next" list can go stale
   relative to Tier-3 disk state — verify the target artifact directly before treating a
   carried-forward item as still open); L-C22 (the orchestrator should delegate a SESSION-STATE.md
   update immediately after verified work, not wait for the operator to ask). Both dated 2026-08-12,
   same provenance pattern as L-C19/L-C20 (operator-confirmed via question tool this session).
- **Bridge-recovery Open Question #1 (RESOLVED, 2026-08-12)** — 1-hour freshness window on the
   G-5 bridge. Operator converged (via orchestrator `question` tool) to keep it unchanged,
   reasoning that the built recovery tooling (commit `1c91a19`) resolves L-C19 pain
   (staleness is diagnosable/clearable, not a dead end), so a short window keeps the security
   invariant tight without the earlier cost.
- **`## Session resume` section in `.gleipnir/AGENTS.md` now live (RESTART-GATED)** — Applied to Tier-3;
   takes effect on the very next session start. The next orchestrator session will be the first to
   exercise the new auto-resume instruction (read SESSION-STATE.md conditional on real prior work).
- **`## Decisions (index)` table in plan-format.md — VERIFIED COMPLETE this session.**
   Disk re-verify found the table already present in `.gleipnir/goals/plan-format.md` (lines 13–22)
   as Required Section #1, with exact column spec and L-C14 rationale cite. SESSION-STATE.md had
   stale claim that this was "not yet done" — a discrepancy flagged as candidate lesson on verifying
   "next" items against disk before treating them as still open.
- **Stage-role-map precedence for prose/config-only plans — RESOLVED (see "Prose/config-only pipeline track — APPLIED + VERIFIED this session" above).** The question was flagged during the escalation-process plan brainstorm; converged and ratified as Approach B, spec-reviewed APPROVED, and applied to stage-role-map.md (lines 63–167).
- **S-2 activation plan APPROVED; C2 control proposal drafted** — awaiting operator application of OS acts.
- **RESTART-GATED changes — NOW CONFIRMED LIVE this session (not still pending):**
   All four Tier-3 edits verified on-disk and active:
   - `.gleipnir/AGENTS.md` `## Tooling notes` section (glob/`path` guidance) — present and live.
   - `.gleipnir/agents/session-scribe.md` glob-pointer bullet (reference to Tooling-notes rule) — present and live.
   - `.gleipnir/skills/README.md` `## Who loads GOTCHA` policy section (intentional per-role inlining) — present and live.
   - `.gleipnir/plugins/git-guard.ts` git-guard plugin with ALWAYS-ACTIVE config-scan gate on `gleipnir-git_commit_changes` / `gleipnir-git_push_current_branch` — present and wired.

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
- **Option C — plugin-hosted typed bookkeeping tools** (the session-scribe
   graduation target; not built).
- ~~**Broker guard policy enforcement:** secret-scan / branch-protection / data-file
   checks NOT enforced by broker (avoids AETOS's false-positive lockup problem) —
   they belong in git hooks. See `.gleipnir/plans/precommit-hook-control-proposal.md`
   (proposal; not yet operator-applied — a tier3-coach output).~~ **CLOSED** — pre-commit
   hook applied, activated, verified (see Built slices). **EVOLVED** — git-enforcement
   now layered (config-scan in plugin, secret-scan in broker) per Approach C (commits
   9cf8c96, 73f754b); takes effect next session after restart.
- ~~**quality-reviewer returns EMPTY on plan-review tasks** (observed ~3x earlier
   session — a reliability seam; the orchestrator had to self-verify plans by
   direct read). Worth a candidate lesson.~~ **CLOSED** — empty-return discipline
   baked into all 8 subagent files (L-C13 fix), verified this session.

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C10 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
