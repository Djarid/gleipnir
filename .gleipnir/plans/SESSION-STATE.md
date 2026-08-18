# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

**FOUNDATIONAL PARADIGM CHANGE THIS SESSION:** operating posture reversed to
UNCAGED-by-default (commit 7b18bb1). Single-principal terminal operator is the
trusted owning principal; agents under operator instruction MAY write Tier-3.
Caged mode (fail-closed S-2 boundary + OS acts) is now OPT-IN, required only
for unattended/autonomous, untrusted-content-ingestion, or higher-assurance
contexts. G-3 key stays `mode 600` in BOTH modes (key-protected floor). Preflight
now has `--mode {uncaged,caged}` selector; requested_mode NEVER participates in
closure computation — safety invariant (traced + tested). Durable record:
`decisions/operating-posture.md` (supersedes always-on-cage framing in
`s2-g1-closure.md`, `substrate-design-pass.md`, `gleipnir-layout-and-memory-model.md`,
`AGENTS.md`). Tests GREEN: 754 passed, 12 skipped.

**Built + committed this session:** preflight mode selector + tests (commit 7b18bb1);
enforcement-path set E extended to `.gitattributes` + `.gitmodules` + rationale
(commit 10b7edc); S-2 caged-mode docs (commit 53be4c4).

Working tree clean, HEAD at commit `53be4c4` on main (3 commits ahead of prior
`origin/main`; NOT pushed). All hardened-path reviews PASSED (spec-conform +
blast-radius + negative-check attestations; cognition-layer honour checks clean).
Cognition layer PROVEN LIVE (two plans this session used Gate 1 + Gate 2; gates
fired for real, caught 2 reconciliation defects on paradigm plan).

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

**Recent — PARADIGM REVERSAL + related work (THIS SESSION):**
- **Operating posture — UNCAGED by default, OPT-IN caged (commit 7b18bb1)** — Durable decision: `decisions/operating-posture.md`. The framework's security boundary default REVERSED: single-principal operator is the trusted principal; agents under instruction MAY write Tier-3 (agents/, keys/, stage-role-map.md, decisions/, goals/). This is a LEGITIMATE default, not a deficiency. Caged mode (S-2 boundary + OS acts) is OPT-IN, required ONLY for (i) unattended/autonomous, (ii) untrusted-content ingestion, (iii) higher-assurance. G-3 key stays `mode 600` in BOTH modes (key-protected floor; uncaged is NOT all-or-nothing). **Mechanism (tested):** preflight has `RequestedMode {uncaged,caged}` + `--mode` CLI selector (`src/gleipnir/preflight/boundary.py`). Safety invariant: `requested_mode` NEVER participates in closure computation — uncaged can be legitimately unclosed; caged requested-but-unclosed REFUSES (exit 1). **IMPORTANT:** orchestrator applied Tier-3 edits this session under operator instruction (via escape hatch); this is now expected/legitimate, proving tier protection was dormant before. Tests: 754 passed, 12 skipped; new `tests/test_preflight_mode_selector.py`; 23 pre-existing tests updated for caged-request fail-closed guarantee. Hardened-path review: SPEC-CONFORM PASS (2 reconciliations removed foreclosed temporary-grant path) + BLAST-RADIUS PASS + negative-check attestation (attested_by=quality-reviewer ≠ author); cognition-layer honour check: no divergence.
- **Enforcement-path set E extended (commit 10b7edc)** — Added `.gitattributes` + `.gitmodules` to Axis 2(a) enforcement-path literals (same blast-radius class as `.gitignore`). Per-file rationale: `.gitattributes` controls git behaviour (line-ending, filter/clean/smudge drivers, diff/merge selection, export-ignore, binary treatment — a silent change alters stored content); `.gitmodules` declares submodule URLs/paths (URL change = supply-chain / version-control-integrity surface). Explicit enumeration per opencode.jsonc precedent (not fuzzy predicate). Lock-files remain the sole deferred member of same-class gap (Approach B: open-ended basename list, nested subproject appearance breaks repo-root-only invariant — deferred explicit). Hardened-path review PASSED.
- **Cognition layer — PROVEN LIVE (TWO PLANS RAN GATE 1 + GATE 2 THIS SESSION)** — Not a new guard; fills the ATLAS/GOTCHA-from-prose-only gap. Two plans ran full cognition cycle (override-paradigm + enforcement-path-gap-closure); both submitted Design Principles section (Gate 1, case-routed by Axis-1 `X`); both passed spec-review intent-quality check + quality honour check (Gate 2 distinct checks). Gate 2 CAUGHT 2 reconciliation defects on paradigm plan (anti-vacuity rule + stale temporaries); gates fired for real. Validated as structurally live, not just documented. Marked DONE/VALIDATED in open threads (below).
- **S-2 caged-mode supporting docs (commit 53be4c4)** — Three new Tier-0 planning artifacts: `s2-activation-launch-habit.md` (C1 dev-mode status quo), `s2-activation-control-proposal.md` (C2 ready-to-apply operator-only OS acts), `caged-mode-runbook-brainstorm.md` (converged design brief for runbook + go-caged skill). Next step: gleipnir-plan drafts the runbook + skill (Tier-3 decisions/ + skills/) from the brief.

## Open threads / next

**Stream 2 — caged-mode runbook + go-caged skill (CONVERGED, ready to PLAN then apply):**
- **Brief:** `.gleipnir/plans/caged-mode-runbook-brainstorm.md` (operator-converged C1–C5). Converged decisions: (C1) runbook lives in Tier-3 `decisions/` home, agent drafts / operator authors — NOTE under new default-uncaged paradigm the orchestrator can also apply Tier-3 on operator instruction; (C2) NEW sibling skill `go-caged` (distinct from `tier3-coach`; executes a known lockdown on operator request vs. tier3-coach detecting gaps); (C3) trigger phrases anchored to the three operating-posture triggers (unattended, untrusted-content, higher-assurance); (C4) HYBRID inline rendering (--mode caged invocation, AC-4 test, rollback), reference the six S-2 C2 OS acts in `s2-activation-control-proposal.md`; (C5) minimal uncage (stop requesting caged; key floor never relaxed; full teardown separate). **NEXT:** gleipnir-plan plans this from the brief, drafts the runbook (Tier-3 `decisions/go-caged-runbook.md` or similar) + the skill (Tier-3 `skills/go-caged/`), orchestrator applies Tier-3 edits under operator instruction (now legitimate).

**S-2 C2 operator acts (opt-in caged-mode activation, DEFERRED, operator-only):**
- **Six OS acts in `s2-activation-control-proposal.md`** (ready-to-apply tier3-coach proposal): (i) create gleipniragent uid/gid 510; (ii) populate agent-identity.env; (iii) ownership/group layout + root sudo wrapper; (iv) chmod 8 LOCKED ENFORCEMENT_PATHS OS-ro to agent uid; (v) G-3 key `mode 600` owner-only (ALREADY DONE this session); (vi) preflight 100755. Ground truth verified: uid/gid 510 free, gleipniragent absent, key already 600, preflight already 100755. **AC-4 acceptance test:** `sudo --preserve-groups gleipniragent preflight` → CLOSED verdict, empty reasons, exit 0. Acts reframed by paradigm change from "the baseline requirement" to "the opt-in caged-mode procedure." Status: ready-to-apply, awaiting operator.

**Stream 3 — retained open threads from prior sessions (keep current):**
- **G-4 remainder:** Seam 7 (live `tool.execute.after` hook); Observer + novelty-triage; Token provenance / cost tracking.
- **E-1 credential-unreachability:** Argument-policy half closed; credential half still open (brokers co-located with env-injected tokens; S-2 necessary-but-not-sufficient).
- **E-2 platform-webhook receiver:** no component home yet.
- **E-3 novelty-triage signal quality:** Seam 7 + observer will reveal.
- **S-2 structural:** mount + terminal closure + S-3 wiring; Rust/C/C++ profiles + offline-deps decision; Option C (plugin-hosted bookkeeping); engine hybrid-C per-stage escalation.
- **Prose/config-only track deferred:** lock-files (same class as `.gitattributes`/`.gitmodules`, deferred; nested subproject appearance + open-ended basenames).

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
