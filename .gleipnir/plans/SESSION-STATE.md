# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

**OI-1 CLOSED + OI-2 SUBSTANTIVELY DONE (acts 1–5 verified, AC-4 GO):**

**OI-1 RESOLVED** (commits `b1afa6f` + `be20988`): `bin/gleipnir-launch` wrapper
now correctly passes `--mode caged` on every invocation, genuinely enforcing the
fail-closed caged boundary gate. Stale cross-references in `decisions/go-caged-runbook.md`
and `skills/go-caged/SKILL.md` cleared; both now state wrapper fail-closes while
preserving AC-4 as the authoritative boundary-closure verification.

**OI-2 SUBSTANTIVELY DONE** (this session):
- **Acts 1–5 verified at OS level** (commits `1b4b2f2`, `35493a9`, `f33cee5`):
  - Act 1: gleipniragent uid/gid 510 (non-login, `/usr/bin/false`) — VERIFIED.
  - Act 2: `agent-identity.env` written (uid/gid 510, mode 644, owner jasonh); **now gitignored** (commit `1b4b2f2`).
  - Act 3: ownership/group layout (Tier-0/1/2 dirs group=gleipniragent, g+w; Tier-3 dirs staff, no group write) — VERIFIED.
  - Act 4: enforcement subtree OS-read-only (8 ENFORCEMENT_PATHS all drwxr-xr-x, files 644) — VERIFIED.
  - Act 5: G-3 key `mode 600` owner-only (agent-unreadable) — VERIFIED.
- **AC-4 boundary genuinely CLOSED:** `sudo GLEIPNIR_MARKER_KEY_FILE=... bin/gleipnir-preflight --agent-uid 510 --agent-gid 510 --mode caged` → `Verdict.CLOSED`, empty reasons, exit 0 — verified live this session.
- **Box is CAGED at OS level** (all acts in place; boundary operational).
- **Act 6 (wrapper install):** bin/gleipnir-launch exists in repo (0755 ready); physical install + operator relaunch not yet done (this session remained interactive as jasonh, uncaged).

**Ansible playbook built to codify future re-setup** (commits `f33cee5` + `5539013`):
- **Decision:** `decisions/s2-caged-ansible.md` (D1–D4; operator-converged; durable record of Tool/Scope/Test-fidelity/Execution-timing tradeoffs).
- **Playbook:** `ansible/site.yml` (mechanises acts 1–5, installs act 6, asserts AC-4 on every run; idempotent, re-runnable, self-verifying).
- **Test harness:** `ansible/tests/` (3-layer: static/syntax + `--check` dry-run + real chmod on disposable fixture tree; idempotency verified; AC-4 failure path tested).
- **D4 state:** tests authored but NOT YET EXECUTED — Ansible not installed on this box, no `[profile.ansible]` sandbox. First execution tracked as FU-1.

**Lessons:** L-C1–L-C28 now recorded (L-C27: Tier-3 grant without roster-agent implementation; L-C28: host proposal gitignore treatment gap).

**Commits this session (7 total, verified against disk; all pushed to origin/main):**
1. `b1afa6f` — OI-1 FIX: bin/gleipnir-launch now passes --mode caged
2. `be20988` — Stale go-caged refs cleared (runbook + skill)
3. `0745b85` — L-C27 recorded
4. `1b4b2f2` — .gitignore: agent-identity.env (host-local file now ignored)
5. `35493a9` — L-C28 recorded (OS proposal gitignore treatment)
6. `f33cee5` — bin/gleipnir-launch hardened + Ansible decision & plan (spec-conform PASS; hardened path)
7. `5539013` — Ansible playbook + 3-layer test harness (spec-conform PASS + blast-radius PASS + attestation + cognition honour; GO)

**HEAD at `5539013`; working tree clean.**

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
- **Lessons L-C1–L-C28** (graduated through L-C10; L-C11–L-C28 in candidates file; L-C14 fix = Decisions-index shape baked into plan-format.md; L-C19 bridge-recovery design question; L-C20 parity-test guard on allow_table.py ROLE_STATES; L-C24/L-C25 verified against disk discipline + artifact completeness; L-C26 orchestrator completeness-check standing; L-C27 [THIS SESSION] = no roster agent frontmatter materialises Tier-3 grant; L-C28 [THIS SESSION] = OS proposal gitignore treatment gap).

**THIS SESSION — OI-1 CLOSED + OI-2 DONE + Ansible playbook BUILT (HEAD `5539013`, 7 commits):**

- **OI-1 RESOLVED (commits `b1afa6f` + `be20988`)** — `bin/gleipnir-launch` wrapper now passes `--mode caged` explicitly (line 31, checked on disk), ensuring genuine fail-close on boundary not-closed. Stale cross-refs in `decisions/go-caged-runbook.md` + `skills/go-caged/SKILL.md` cleared to state wrapper now fail-closes, preserving AC-4 as authoritative verification. Reviewed SPEC-CONFORM PASS + BLAST-RADIUS PASS + negative-check attestation (attested_by=quality-reviewer, light path).
- **OI-2 acts 1–5 VERIFIED at OS level + AC-4 boundary GENUINELY CLOSED (commits `1b4b2f2`, `35493a9`, `f33cee5`):**
  - gleipniragent uid/gid 510 created; agent-identity.env written (mode 644) and **gitignored** (commit `1b4b2f2`).
  - Ownership/group layout applied (Tier-0/1/2 dirs group=gleipniragent g+w; Tier-3 staff no group write).
  - 8 ENFORCEMENT_PATHS chmod'd OS-ro (drwxr-xr-x, files 644).
  - G-3 key `mode 600` owner-only; AC-4 preflight run → `Verdict.CLOSED`, exit 0, empty reasons. **Box is CAGED at OS level, verified live this session.**
- **Ansible playbook + test harness BUILT (commits `f33cee5` + `5539013`):**
  - Decision record `decisions/s2-caged-ansible.md` (D1–D4; operator-converged; Tool=Ansible, Scope=acts 1–5 + install 6 + AC-4 assert, Test-fidelity=3-layer, Execution-timing=authored-not-executed; honest labelling).
  - `ansible/site.yml` mechanises the six acts idempotently, install-safe, self-verifying (verified against disk: 252 lines, pre/tasks/roles/post structure per spec).
  - `ansible/tests/{run.sh,layer*.sh}` 3-layer harness (static + dry-run + real chmod on disposable fixture).
  - **D4 state:** tests authored, NOT YET EXECUTED (Ansible not installed; no profile.ansible sandbox). First run tracked as FU-1. SPEC-CONFORM PASS + BLAST-RADIUS PASS + negative-check attestation + cognition honour (J-level per D4). GO.
- **Lesson L-C27 recorded (commit `0745b85`)** — operating-posture.md grants instructed-agent Tier-3 writes under uncaged default, but NO roster agent materialises that grant (orchestrator denies edit; plan/brainstorm only plans/**; code denies .gleipnir/**; session-scribe only Tier-0 + one named Tier-2 file). Corrects earlier inaccuracy.
- **Lesson L-C28 recorded (commit `35493a9`)** — a ready-to-apply OS/host proposal that creates a host-local file must specify that file's gitignore treatment. Omitting it leaves an accidental-commit gap (observed this session with agent-identity.env; retroactively gitignored in commit `1b4b2f2`). Now a recorded guardrail.

**Prior-session paradigm work (retained; commits 7b18bb1 / 10b7edc / 53be4c4→3d136ad→0f52460):**
- **Operating posture — UNCAGED by default, OPT-IN caged (commit 7b18bb1)** — Durable decision: `decisions/operating-posture.md`. Framework security boundary default REVERSED: single-principal operator is trusted principal; agents under instruction MAY write Tier-3. Caged mode (S-2 boundary + OS acts) is OPT-IN, required ONLY for (i) unattended/autonomous, (ii) untrusted-content ingestion, (iii) higher-assurance. G-3 key stays `mode 600` in BOTH modes (key-protected floor). **Mechanism (tested):** preflight has `RequestedMode {uncaged,caged}` + `--mode` CLI selector. Safety invariant: `requested_mode` NEVER participates in closure — uncaged can be unclosed; caged-requested-but-unclosed REFUSES. Tests 754 passed, 12 skipped; `tests/test_preflight_mode_selector.py` + 23 pre-existing updated. Hardened-path review: SPEC-CONFORM (2 reconciliations) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check: clean.
- **Enforcement-path set E extended (commit 10b7edc)** — Added `.gitattributes` + `.gitmodules` to Axis 2(a) literals (same blast-radius class as `.gitignore`). Rationale per file: `.gitattributes` controls git behaviour (line-ending, filters, diff/merge selection; silent change alters stored content); `.gitmodules` declares submodule URLs (URL change = supply-chain surface). Explicit enumeration per opencode.jsonc precedent. Lock-files deferred (nested subprojects + open-ended basenames). Hardened-path review PASSED.
- **Caged-mode operator-facing capability BUILT & PUSHED (commits 53be4c4 → 3d136ad → 0f52460)** — **Artifacts (Tier-3, now on main):** `.gleipnir/decisions/go-caged-runbook.md` (operator front door; inlines --mode caged invocation, AC-4 gate, rollback; REFERENCES not duplicates six S-2 C2 OS acts). `.gleipnir/skills/go-caged/SKILL.md` (guides + verifies operator through runbook vs. box state, gates on AC-4; operator-executes-acts, hybrid shape like tier3-coach). Sibling to tier3-coach (detects gaps vs. executes lockdown). **Critical safety defect caught in spec-review (commit 0f52460 fix round):** `bin/gleipnir-launch` as drafted called preflight WITHOUT `--mode caged` → would silently launch uncaged when operator thinks caged. BOTH artifacts were corrected to attribute the gate ONLY to the explicit `--mode caged` check, and the runbook warned the wrapper was convenience-not-gate until amended (tracked as OI-1). **OI-1 has since been RESOLVED this session (commit `b1afa6f`, see the "Recent" block above): the wrapper draft now passes `--mode caged` and the stale warnings were cleared (commit `be20988`).** Prior hardened-path: SPEC-CONFORM (1 fix) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check clean.
- **Cognition layer PROVEN LIVE + VALIDATED** — Not a guard; fills ATLAS/GOTCHA-prose gap. Two plans this session ran Gate 1 + Gate 2 (caged-mode paradigm + enforcement-path plans). Both submitted Design Principles (Gate 1 case-routed). Spec-review intent-quality + quality honour checks both fired (Gate 2 distinct). **Gate 2 CAUGHT 2 reconciliation defects on paradigm plan** (anti-vacuity rule + stale temporaries); gates fire for real, not documentally. Validated structurally live.

## Open threads / next

### ⭐ START HERE NEXT SESSION: OI-2 follow-ups (Ansible execution + optional wrapper install)

**OI-2 is SUBSTANTIVELY DONE** (acts 1–5 verified at OS level; AC-4 GO; box is CAGED).
**Remaining follow-ups (optional but encouraged):**

**FU-1 — Run the Ansible playbook tests (D4-FU; first execution)**
- Install Ansible: `brew install ansible` OR `pipx install ansible` (pipx not currently on this box; brew present).
- Run the 3-layer test harness: `ansible/tests/run.sh` (static lint + dry-run + idempotency on fixture tree).
- **Outcome:** Tests run GREEN (or reveal unforeseen issues) for the first time; D4 state transitions from "authored, not executed" to "proven green".
- **Not blocking:** the playbook can run later; this is the proof-of-execute, not a gate.

**FU-2 — (Optional) Build an `[profile.ansible]` sandbox image**
- Alternative to host Ansible install: hardened sandbox profile for running tests in-container (consistent with the rest of the S-2 test infrastructure).
- **Not blocking:** both paths (host install + hardened profile) are equivalent; choose per operator preference.

**FU-3 — Update go-caged-runbook.md Step 1 prose**
- Currently references the six manual acts from s2-activation-control-proposal.md.
- Should point at the Ansible playbook as the **preferred operational delivery** (noted in s2-caged-ansible.md Consequences).
- **Scope:** prose update only; no machinery change.

**FU-4 — (Optional) Actually run caged sessions**
- If operator wants to test caged execution: `sudo bin/gleipnir-launch` (act 6 physical install: chmod 0755 + operator launch).
- **Not blocking:** the boundary is proven closed (AC-4 GO); running a session inside it is optional.

**All four follow-ups are TRACKED for future sessions.** None block the framework's current state (CAGED at OS level; machinery proven; tests authored).

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

**S-2 status THIS SESSION:** Acts 1–5 VERIFIED; AC-4 boundary genuinely CLOSED; box CAGED at OS level. Ansible playbook codifies future re-setup (tested structure; tests authored, not yet executed). See FU-1..FU-4 (optional follow-ups) in "Open threads / next" above.

- **S-2 follow-ups (optional, not blocking):** Ansible test execution (FU-1); hardened sandbox profile (FU-2); runbook prose update (FU-3); caged session execution (FU-4).
- S-2 mount + terminal closure (caging now OS-level; S-3 preflight integration still future).
- E-1 credential-unreachability half (argument-policy closed; credential co-location remains).
- E-2 platform-webhook receiver (no component home).
- E-3 novelty-triage signal quality (Seam 7 + observer).
- G-4 remainder (Seam 7, observer, novelty-triage, cost tracking).
- Engine hybrid-C per-stage escalation + G-5 engine full implementation.
- Live TS `tool.execute.after` advance hook; real-CI attestation feeding `attempt_gate` / G-3.2.
- Rust/C/C++ sandbox profiles + offline-deps fetch-then-seal.
- Option C — plugin-hosted typed bookkeeping tools.
- Lock-files (same blast-radius class as `.gitattributes`/`.gitmodules`; deferred due to nested subproject appearances + open-ended basenames).

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C28 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
