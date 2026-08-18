# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

**CAGED-MODE OPERATOR-FACING CAPABILITY BUILT & PUSHED.** This session completed
opt-in caged-mode work: built `.gleipnir/decisions/go-caged-runbook.md` (Tier-3,
operator front door for entering caged mode) + `.gleipnir/skills/go-caged/SKILL.md`
(Tier-3, guides operator through runbook vs. real box state, gates on AC-4).
**Critical safety defect CAUGHT + FIXED in spec-review:** `bin/gleipnir-launch`
as drafted calls preflight WITHOUT `--mode caged` → would silently launch uncaged
when operator thinks they're caged. Both artifacts corrected to attribute gate ONLY
to explicit `--mode caged` check; go-caged-runbook.md warns gleipnir-launch is
convenience, not gate, until amended (→ OI-1 pickup item, below).

Hardened-path review: SPEC-CONFORM PASS (after 1 fix round) + BLAST-RADIUS PASS +
negative-check attestation (attested_by=quality-reviewer ≠ author); cognition-layer
honour check no divergence. Operating-posture.md stale forward-ref fixed.

**Commits this session:** 10b7edc (enforce-path E extension), 7b18bb1 (uncaged paradigm),
53be4c4 (S-2 caged docs), 3d136ad (runbook/skill draft), 0f52460 (spec-review fixes +
push). All five now on origin/main; working tree clean, HEAD at `0f52460`.

Tests GREEN: 754 passed, 12 skipped. Cognition layer PROVEN LIVE + VALIDATED
(fired on caged-mode plan; caught safety defect in spec-review).

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
- **Lessons L-C1–L-C26** (graduated through L-C10; L-C11–L-C26 in candidates file; L-C14 fix = Decisions-index shape baked into plan-format.md; L-C19 bridge-recovery design question; L-C20 parity-test guard on allow_table.py ROLE_STATES; L-C24/L-C25 verified against disk discipline + artifact completeness; L-C26 orchestrator completeness-check standing).

**Recent — PARADIGM REVERSAL + CAGED-MODE OPERATOR CAPABILITY (THIS SESSION, PUSHED commit 0f52460):**
- **Operating posture — UNCAGED by default, OPT-IN caged (commit 7b18bb1)** — Durable decision: `decisions/operating-posture.md`. Framework security boundary default REVERSED: single-principal operator is trusted principal; agents under instruction MAY write Tier-3. Caged mode (S-2 boundary + OS acts) is OPT-IN, required ONLY for (i) unattended/autonomous, (ii) untrusted-content ingestion, (iii) higher-assurance. G-3 key stays `mode 600` in BOTH modes (key-protected floor). **Mechanism (tested):** preflight has `RequestedMode {uncaged,caged}` + `--mode` CLI selector. Safety invariant: `requested_mode` NEVER participates in closure — uncaged can be unclosed; caged-requested-but-unclosed REFUSES. Tests 754 passed, 12 skipped; `tests/test_preflight_mode_selector.py` + 23 pre-existing updated. Hardened-path review: SPEC-CONFORM (2 reconciliations) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check: clean.
- **Enforcement-path set E extended (commit 10b7edc)** — Added `.gitattributes` + `.gitmodules` to Axis 2(a) literals (same blast-radius class as `.gitignore`). Rationale per file: `.gitattributes` controls git behaviour (line-ending, filters, diff/merge selection; silent change alters stored content); `.gitmodules` declares submodule URLs (URL change = supply-chain surface). Explicit enumeration per opencode.jsonc precedent. Lock-files deferred (nested subprojects + open-ended basenames). Hardened-path review PASSED.
- **Caged-mode operator-facing capability BUILT & PUSHED (commits 53be4c4 → 3d136ad → 0f52460)** — **Artifacts (Tier-3, now on main):** `.gleipnir/decisions/go-caged-runbook.md` (operator front door; inlines --mode caged invocation, AC-4 gate, rollback; REFERENCES not duplicates six S-2 C2 OS acts). `.gleipnir/skills/go-caged/SKILL.md` (guides + verifies operator through runbook vs. box state, gates on AC-4; operator-executes-acts, hybrid shape like tier3-coach). Sibling to tier3-coach (detects gaps vs. executes lockdown). **Critical safety defect caught in spec-review (commit 0f52460 fix round):** `bin/gleipnir-launch` as drafted called preflight WITHOUT `--mode caged` → would silently launch uncaged when operator thinks caged. BOTH artifacts corrected; gate attributed ONLY to explicit `--mode caged` check. Runbook warns wrapper is convenience, not gate, until amended (→ OI-1, above). Operating-posture.md stale ref fixed. Hardened-path: SPEC-CONFORM (1 fix) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check clean.
- **Cognition layer PROVEN LIVE + VALIDATED** — Not a guard; fills ATLAS/GOTCHA-prose gap. Two plans this session ran Gate 1 + Gate 2 (caged-mode paradigm + enforcement-path plans). Both submitted Design Principles (Gate 1 case-routed). Spec-review intent-quality + quality honour checks both fired (Gate 2 distinct). **Gate 2 CAUGHT 2 reconciliation defects on paradigm plan** (anti-vacuity rule + stale temporaries); gates fire for real, not documentally. Validated structurally live.

## Open threads / next

### ⭐ START HERE NEXT SESSION: Two explicit pickup items

**OI-1 — FIX `bin/gleipnir-launch` wrapper (closes safety defect, Tier-3 `bin/`):**
Spec-review caught that `bin/gleipnir-launch` as drafted in `.gleipnir/plans/s2-activation-control-proposal.md` act (6) calls preflight WITHOUT `--mode caged` → would silently launch uncaged when operator thinks they're caged. **The real fix:** amend the embedded preflight call to add `--mode caged` so wrapper genuinely enforces caged gate on every launch. Small, scoped change; enforces the runbook's safety invariant. Cross-referenced in go-caged-runbook.md "Cross-artifact note" and tracked as OI-1 in `.gleipnir/plans/caged-mode-runbook.md`. Under default-uncaged paradigm orchestrator MAY apply this on operator instruction, OR operator applies directly. Route change hardened (enforcement-adjacent, caged-gate wrapper, safe-side per this session's precedent).

**OI-2 — S-2 C2 activation (operator root OS acts; use `go-caged` skill guide):**
Six acts in `.gleipnir/plans/s2-activation-control-proposal.md` — ready-to-apply (i) create gleipniragent uid/gid 510; (ii) agent-identity.env; (iii) ownership/group layout + root wrapper; (iv) chmod 8 LOCKED ENFORCEMENT_PATHS OS-ro to agent uid; (v) G-3 key `mode 600` owner-only (VERIFIED DONE this session, -rw-------); (vi) preflight 100755 (VERIFIED DONE). AC-4 test: `sudo --preserve-groups gleipniragent preflight` → CLOSED verdict, empty reasons, exit 0. Ground truth: uid/gid 510 free, gleipniragent absent. **Next session:** load `skills/go-caged/SKILL.md` (built this session) — it is the guided front door for walking these acts. Operator executes the root acts; skill verifies each against real box state, gates on AC-4 go/no-go, provides rollback. **DO OI-1 FIRST** so wrapper is correct before it's installed in act (6).

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
