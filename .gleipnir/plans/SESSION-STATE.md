# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

All six enforcement guards (G-1..G-6) have real, tested first slices, plus a
language-agnostic sandbox executor, the session-scribe bookkeeping role, and the
orchestrator interactive-session context-cap feature. Latest committed + pushed
state is on `origin` (`git@github.com:Djarid/gleipnir.git`, branch `main`).
Tests as of the language-agnostic-sandbox slice: **438 passed / 11 skipped / 93%
coverage** (in-sandbox). Context-cap feature verified Tue 28 Jul 2026 (restart
stress-test S1/S2 passed; Approach-B escalation not required).

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

## Open threads / next

**Tue 28 Jul 2026 — session-scribe dispatch (L-C10 closure):**
- Orchestrator sequencing three immediate threads in order:
  1. **End-to-end session-scribe run** — this delegation (proves the L-C10 loop).
  2. **Node profile real-run** — build operator digest-pinned node Containerfile + image, run profile → closes dogfood node cross-lang seam (currently dispatch-proven only).
  3. **S-2 activation (operator)** — dedicated agent uid + chmod OS-ro + G-3 key OS-unreadable + `bin/gleipnir-preflight` before sessions.
- **NEW brainstorm-stage capability:** Interactive-session context-length cap entering pipeline.
  - Limit: **250K tokens** (operator-decided surface; interactive-session only).
  - Scope: primary interactive agents *only* (`/plan`, `/build`, `/orchestrator`).
  - **NOT per-subagent; NOT the G-4d ledger.**

## Open seams (absorbed from the old session-seams-ledger.md; NOT authoritative)

- **Node profile real-run:** needs an operator-built digest-pinned node
  Containerfile + image; until then the node profile is dispatch-proven only.
- **Dogfood node cross-language block** (`tests/test_sequence_gate.mjs`):
  committed but NOT yet agent-run (no roster agent has a node grant; sandbox had
  no node profile image). Statically sound; fixture MAC confirmed Python-side.
- **S-2 activation (operator):** dedicated agent uid + chmod OS-ro + G-3 key
  OS-unreadable + `bin/gleipnir-preflight` (code built, commit `5cd329c`).
- **S-2 mount + terminal closure + S-3 preflight wiring:** the structural
  boundary that makes `.gleipnir/` unwritable (vs today's preflight OS-perms
  floor).
- **G-4 remainder:** observer, novelty triage (G-4c), TS-side emit;
  cost/economic-chain in the ledger (needs S-2 rate-table + token provenance).
- **E-1** broker argument policy; **E-2** platform-webhook receiver; **E-3**
  novelty-triage signal quality.
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
- **quality-reviewer returns EMPTY on plan-review tasks** (observed ~3x this
  session — a reliability seam; the orchestrator had to self-verify plans by
  direct read). Worth a candidate lesson.

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C10 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
