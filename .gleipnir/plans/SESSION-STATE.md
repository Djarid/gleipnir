# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

**OI-1 RESOLVED: `bin/gleipnir-launch` wrapper now correctly fail-closes** (commit
`b1afa6f`). The wrapper was drafted in `.gleipnir/plans/s2-activation-control-proposal.md`
act (6) calling preflight WITHOUT `--mode caged`; this session amended it to pass
`--mode caged` explicitly, ensuring the wrapper genuinely enforces the caged gate on
every launch. Companion files **`.gleipnir/decisions/go-caged-runbook.md`** and
**`.gleipnir/skills/go-caged/SKILL.md`** updated to mark OI-1 RESOLVED while preserving
the explicit `--mode caged` AC-4 check as the authoritative boundary verification.

**Stale cross-references cleared** (commit `be20988`): both Tier-3 files
(runbook + skill) corrected to state wrapper now fail-closes, while preserving AC-4
check. The Tier-0 plan `caged-mode-runbook.md` updated: OI-1 marked RESOLVED, obsolete
ready-to-apply Part-B section replaced with "corrections APPLIED (historical)" note.
Hardened review: SPEC-CONFORM PASS + BLAST-RADIUS PASS + negative-check attestation
(attested_by=quality-reviewer). NOTE: Tier-3 edits applied by primary SESSION AGENT
in build/interactive mode (which holds edit/write/bash), NOT by roster subagent
(per L-C27 — no roster agent frontmatter materialises Tier-3 grant; see below).

**Lesson L-C27 recorded** (commit `0745b85`): operating-posture.md grants "instructed-agent
MAY write Tier-3" under uncaged default, but NO ROSTER AGENT frontmatter implements that
grant (orchestrator denies edit; plan/brainstorm only plans/**; code denies .gleipnir/**;
session-scribe only Tier-0 + one Tier-2 file). Operator-confirmed. Corrects prior inaccuracy
claiming orchestrator applies Tier-3 files directly — it does not.

**Commits this session:** b1afa6f (OI-1 FIX), be20988 (stale refs cleared), 0745b85 (L-C27).
All pushed to origin/main; working tree clean, HEAD at `0745b85`.

Tests GREEN: 754 passed, 12 skipped. Cognition layer PROVEN LIVE + VALIDATED.

## Built slices (verified against disk / commits)

**Stable foundation (multi-session, durable home in `../decisions/`):**
- **G-1 unreachable guards** (preflight; fail-closed; per-file walk); **G-2 capability removal** (sandbox `--network=none`); **G-3.1 unforgeable marker** (keyed HMAC); **G-4 unblindable senses** (typed bus + metrics ledger); **G-5 deterministic engine** (revert edges + budget); **G-6 memory-not-poisonable** (trust-tiered layout). All verified end-to-end dogfood (armed-run; cross-lang HMAC contract).
- **Language-agnostic sandbox** (config-driven toolchain dispatch via `.gleipnir/sandbox/profiles.toml`); Tier-3 preflight-protected.
- **Session-scribe** (Tier-0 bookkeeping writer; resume mechanism; this file).
- **Tier3-coach skill** (control-gap detect→propose→converge workflow; operator-handoff, never implements).
- **Lesson-escalation process (A-hybrid)** (brainstorm → plan → spec-review → approved → orchestrator confirms verbatim via `question` → session-scribe appends; live end-to-end verified; operator UNCONSTRAINED by build mode).
- **Config-scoping preflight (config_scan.py)** (143 tests, 90% coverage; closes L-C12/L-C12b class; validates content/grammar/tool-grant sets; ALWAYS-ACTIVE plugin gate + broker secret-scan).
- **Broker MCP servers** (gleipnir-git + gleipnir-pm; 4 tools each; single-holder scoping via Tier-3 frontmatter; git 99%, pm/mcp 97%, pm/platform 100% coverage; force-push structurally absent; hook-bypass flags refused).
- **Git-enforcement (Approach C)** (plugin: config-scan on every git write; broker: secret-scan always-on pre-commit; layer split closes D9 compliance).
- **Orchestrator context-cap** (Opus capped 250k / 32k output; compaction rules ported from AETOS; policy enforced at hook).
- **Lessons L-C1–L-C27** (graduated through L-C10; L-C11–L-C27 in candidates file; L-C14 fix = Decisions-index shape baked into plan-format.md; L-C19 bridge-recovery design question; L-C20 parity-test guard on allow_table.py ROLE_STATES; L-C24/L-C25 verified against disk discipline + artifact completeness; L-C26 orchestrator completeness-check standing; L-C27 [THIS SESSION] = no roster agent frontmatter materialises Tier-3 grant).

**Recent — OI-1 CLOSED + CAGED-MODE DOCS CONSISTENT (THIS SESSION, HEAD `0745b85`; prior sessions' paradigm work retained below):**
- **OI-1 RESOLVED (commit `b1afa6f`)** — `bin/gleipnir-launch` draft in act (6) of `s2-activation-control-proposal.md` now passes `--mode caged` in its embedded preflight, so the wrapper genuinely fail-closes on a not-closed boundary (was a silent uncaged-launch false-assurance defect). Reviewed SPEC-CONFORM: PASS (light path, prose/config-only).
- **Stale go-caged cross-refs cleared (commit `be20988`)** — after OI-1, `decisions/go-caged-runbook.md` + `skills/go-caged/SKILL.md` still called the wrapper "not a caged gate as drafted"; both corrected to state it now fail-closes, PRESERVING the explicit `--mode caged` AC-4 check as the authoritative boundary-state verification (no over-correction into "skip AC-4"). Tier-0 plan `caged-mode-runbook.md` marks OI-1 RESOLVED (ST-17/18, edge-case-7) and replaces the obsolete Part-B ready-to-apply pairs with a "corrections APPLIED (historical)" note. HARDENED review: SPEC-CONFORM PASS + BLAST-RADIUS PASS + negative-check attestation (no grant added, attested_by=quality-reviewer). **Tier-3 edits were applied by the PRIMARY/BUILD session agent (holds edit/write/bash), NOT a roster subagent — see L-C27.**
- **L-C27 recorded (commit `0745b85`)** — `operating-posture.md` grants instructed-agent Tier-3 writes under the uncaged default, but NO roster agent's frontmatter materialises that grant (orchestrator denies edit; plan/brainstorm only plans/**; code denies .gleipnir/**; session-scribe only Tier-0 + one Tier-2 file). Operator-confirmed candidate. Corrects the earlier inaccurate "orchestrator applies Tier-3 directly" claim.

**Prior-session paradigm work (retained; commits 7b18bb1 / 10b7edc / 53be4c4→3d136ad→0f52460):**
- **Operating posture — UNCAGED by default, OPT-IN caged (commit 7b18bb1)** — Durable decision: `decisions/operating-posture.md`. Framework security boundary default REVERSED: single-principal operator is trusted principal; agents under instruction MAY write Tier-3. Caged mode (S-2 boundary + OS acts) is OPT-IN, required ONLY for (i) unattended/autonomous, (ii) untrusted-content ingestion, (iii) higher-assurance. G-3 key stays `mode 600` in BOTH modes (key-protected floor). **Mechanism (tested):** preflight has `RequestedMode {uncaged,caged}` + `--mode` CLI selector. Safety invariant: `requested_mode` NEVER participates in closure — uncaged can be unclosed; caged-requested-but-unclosed REFUSES. Tests 754 passed, 12 skipped; `tests/test_preflight_mode_selector.py` + 23 pre-existing updated. Hardened-path review: SPEC-CONFORM (2 reconciliations) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check: clean.
- **Enforcement-path set E extended (commit 10b7edc)** — Added `.gitattributes` + `.gitmodules` to Axis 2(a) literals (same blast-radius class as `.gitignore`). Rationale per file: `.gitattributes` controls git behaviour (line-ending, filters, diff/merge selection; silent change alters stored content); `.gitmodules` declares submodule URLs (URL change = supply-chain surface). Explicit enumeration per opencode.jsonc precedent. Lock-files deferred (nested subprojects + open-ended basenames). Hardened-path review PASSED.
- **Caged-mode operator-facing capability BUILT & PUSHED (commits 53be4c4 → 3d136ad → 0f52460)** — **Artifacts (Tier-3, now on main):** `.gleipnir/decisions/go-caged-runbook.md` (operator front door; inlines --mode caged invocation, AC-4 gate, rollback; REFERENCES not duplicates six S-2 C2 OS acts). `.gleipnir/skills/go-caged/SKILL.md` (guides + verifies operator through runbook vs. box state, gates on AC-4; operator-executes-acts, hybrid shape like tier3-coach). Sibling to tier3-coach (detects gaps vs. executes lockdown). **Critical safety defect caught in spec-review (commit 0f52460 fix round):** `bin/gleipnir-launch` as drafted called preflight WITHOUT `--mode caged` → would silently launch uncaged when operator thinks caged. BOTH artifacts were corrected to attribute the gate ONLY to the explicit `--mode caged` check, and the runbook warned the wrapper was convenience-not-gate until amended (tracked as OI-1). **OI-1 has since been RESOLVED this session (commit `b1afa6f`, see the "Recent" block above): the wrapper draft now passes `--mode caged` and the stale warnings were cleared (commit `be20988`).** Prior hardened-path: SPEC-CONFORM (1 fix) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check clean.
- **Cognition layer PROVEN LIVE + VALIDATED** — Not a guard; fills ATLAS/GOTCHA-prose gap. Two plans this session ran Gate 1 + Gate 2 (caged-mode paradigm + enforcement-path plans). Both submitted Design Principles (Gate 1 case-routed). Spec-review intent-quality + quality honour checks both fired (Gate 2 distinct). **Gate 2 CAUGHT 2 reconciliation defects on paradigm plan** (anti-vacuity rule + stale temporaries); gates fire for real, not documentally. Validated structurally live.

## Open threads / next

### ⭐ START HERE NEXT SESSION: S-2 C2 activation (OI-2)

**OI-2 — S-2 C2 activation (operator root OS acts; use `go-caged` skill guide) — NOW SOLE PICKUP ITEM:**
Six acts in `.gleipnir/plans/s2-activation-control-proposal.md` — ready-to-apply (i) create gleipniragent uid/gid 510; (ii) agent-identity.env; (iii) ownership/group layout + root wrapper; (iv) chmod 8 LOCKED ENFORCEMENT_PATHS OS-ro to agent uid; (v) G-3 key `mode 600` owner-only (VERIFIED DONE this session, -rw-------); (vi) preflight 100755 (VERIFIED DONE). AC-4 test: `sudo --preserve-groups gleipniragent preflight` → CLOSED verdict, empty reasons, exit 0. Ground truth: uid/gid 510 free, gleipniragent absent. **Next session:** load `skills/go-caged/SKILL.md` (built this session, internally consistent post-OI-1 fix) — it is the guided front door for walking these acts. Operator executes the root acts; skill verifies each against real box state, gates on AC-4 go/no-go, provides rollback. **OI-1 is NOW RESOLVED**, so the wrapper draft in act (6) correctly passes `--mode caged` and is ready to install.

---

**Stream 2 — caged-mode runbook + go-caged skill (BUILT & PUSHED, commit 0f52460):**
- **Brief:** `.gleipnir/plans/caged-mode-runbook-brainstorm.md` (converged C1–C5).
- **Artifacts NOW LANDED:** `.gleipnir/decisions/go-caged-runbook.md` (operator front door for entering caged mode; inlines --mode caged invocation, AC-4 gate, minimal uncage); `.gleipnir/skills/go-caged/SKILL.md` (guides + verifies operator through runbook, gates on AC-4; operator-applies-acts, same hybrid shape as tier3-coach). REFERENCES (not duplicated) six S-2 C2 OS acts from s2-activation-control-proposal.md (C4 anti-drift, no duplication). Sibling to tier3-coach (tier3-coach detects gaps + proposes; go-caged executes known lockdown).

**Background threads (lower-priority, prior sessions):**
- **G-4 remainder:** Seam 7 (live `tool.execute.after` hook); Observer + novelty-triage; Token provenance / cost tracking.
- **E-1 credential-unreachability:** Argument-policy half closed; credential half still open (brokers co-located with env-injected tokens; S-2 necessary-but-not-sufficient).
- **E-2 platform-webhook receiver:** no component home yet.
- **E-3 novelty-triage signal quality:** Seam 7 + observer will reveal.
- **S-2 structural:** mount + terminal closure + S-3 wiring; Rust/C/C++ profiles + offline-deps decision; Option C (plugin-hosted bookkeeping); engine hybrid-C per-stage escalation.
- **Prose/config-only track deferred:** lock-files (same class as `.gitattributes`/`.gitmodules`, deferred; nested subproject appearance + open-ended basenames).
- **Cognition layer:** PROVEN LIVE & VALIDATED (fired on caged-mode plan; spec-review intent-quality check caught safety defect; quality honour check ran; two plans this session used full Gate 1 + Gate 2).

## Open seams (absorbed from old session-seams-ledger.md; NOT authoritative)

- S-2 activation (see "Open threads / next" above — operator acts pending).
- S-2 mount + terminal closure + S-3 preflight.
- E-1 credential-unreachability half.
- E-2 platform-webhook receiver.
- E-3 novelty-triage signal quality.
- G-4 remainder (Seam 7, observer, novelty-triage, cost tracking).
- Engine hybrid-C per-stage escalation.
- Live TS `tool.execute.after` advance hook; real-CI attestation feeding `attempt_gate` / G-3.2.
- Rust/C/C++ sandbox profiles + offline-deps fetch-then-seal.
- Option C — plugin-hosted typed bookkeeping tools.

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C26 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
