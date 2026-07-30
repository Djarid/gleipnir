# Decision: Tier-0→Tier-2 lesson-candidate escalation path (A-hybrid)

**Status: authored, in use, NOT YET CLOSED** — a deliberate *interim* substitute
for the not-yet-built G-4c review-gated memory-write pipeline. Cooperative policy
until S-2 boundary + G-1 preflight make Tier-3 config OS-ro to the agent uid;
until then the tier boundary is opencode-permission + this record. Authored by
the operator via the build-mode escape hatch (Tier-3). Plan of record:
`../plans/lesson-escalation-process.md`; converged brief:
`../plans/lesson-escalation-process-brainstorm.md`; the earlier (partially
superseded) mechanism proposal: `../plans/tier2-escalation-control-proposal.md`.

## Why

`gleipnir-layout-and-memory-model.md` designed the Tier-2 (`memory/`,
`lessons/`) write path as "an agent may PROPOSE an entry; a deterministic
framework component decides whether and where it is written" — but that pipeline
is gated on the G-4 bus + S-2 + `keys/` digests, none of which exist. So every
lesson candidate (L-C1..L-C13) was recorded via a full operator build-mode
round-trip — expensive friction for genuinely low-stakes, pre-review advisory
content that grants no capability and changes no enforcement. This decision
provides a narrow interim path that keeps the human-review invariant while
removing the round-trip.

## What was decided (operator-converged)

- **Mechanism (Option A):** `session-scribe`'s grant is extended to exactly ONE
  named file — `.gleipnir/lessons/session-lessons-candidates.md` — in both its
  `edit` and `write` maps. NOT blanket `lessons/`, NOT `lessons/README.md`, NOT
  `memory/`, NOT any other Tier-2/Tier-3 path. `session-scribe` holds no
  `question`/`task`/`bash`, so it cannot self-trigger; it appends only the
  verbatim text an orchestrator delegation hands it.
- **Human review satisfied upstream (the interim substitute for the pipeline's
  deterministic Review step):** the orchestrator confirms the *exact drafted
  text* with the operator via `question` BEFORE delegating the append. This
  reuses the existing precept-10 convergence primitive — no new ambient lever.
  (The operator explicitly rejected a broad `task: general: allow` grant on the
  orchestrator, reasoning that an ambient escalation lever "would break the
  workflow... which is what adds the determinism"; the deliberate per-use
  `question` is that determinism.)
- **Process = A-hybrid** (converged via a weighted decision matrix + bias check
  over four candidates A/A-hybrid/B/C): immediate-by-default, with opportunistic
  coalescing ONLY within a single uninterrupted turn (never held pending across
  a turn or a compaction boundary — this is the bounded, non-drifting definition
  that avoids Approach B's compaction-loss hazard); uncapped (the per-use
  `question` is itself the noise-brake); full discard on reject (no ledger, no
  Tier-0 debris); lightweight provenance footer + session id (no richer schema
  that would need re-shaping when G-4c lands).
- **Durability:** the escalation obligation is pinned as a `compaction_survival:`
  frontmatter bullet in `orchestrator.md` (so it survives context compaction, not
  just as body prose the plugin would summarise away) AND documented as a body
  section ("Lesson-candidate escalation (A-hybrid; standing discipline)").

## Pipeline discipline (the correction it embodies)

This feature was itself a correction: the orchestrator initially self-designed
the process without methodology. It was redone properly — brainstorm (real
alternatives + matrix + bias check) → operator convergence → full ATLAS plan →
spec-review (which caught a real defect: the plan claimed compaction-durability
its own edit didn't implement) → revision → re-review → approved. The lesson
(L-C14, and the escalation feature applied to lesson-capture itself) is that a
good practice living only in habit erodes; move it into the enforced layer.

## Verification

- Both agent-file edits validated (YAML parses; `session-scribe`'s grant covers
  exactly the one named file; `orchestrator.md` has 7 `compaction_survival`
  bullets).
- **Live-use verified end-to-end:** L-C14 was drafted → confirmed via `question`
  → appended by `session-scribe` using its OWN grant, with the orchestrator
  unconstrained by build mode — confirming the mechanism does not depend on
  operator escape-hatch access for routine use. L-C15 followed the same path.
- Committed + pushed: `d72eec3` (mechanism), plus follow-on commits.

## Honesty labels / open items

- **Interim, not the real pipeline.** This is a human-`question` substitute for
  the deterministic Review step. The full G-4c review-gated pipeline (Receive →
  Classify → Validate → Review → audit event on the G-4 bus) remains the target;
  it needs S-2 + the bus + `keys/` digests.
- **Cooperative-policy until S-2.** `session-scribe.md`'s grant and
  `orchestrator.md`'s discipline are Tier-3 by intent but agent-unwritable only
  after S-2/G-1 close.
- **Scope guard.** The single-named-file grant is the explicit guard against
  precedent-creep to blanket `lessons/`/`memory/`; any widening is a fresh
  operator-converged Tier-3 decision.
- **Superseded content:** the 8-step process sketch in
  `tier2-escalation-control-proposal.md` was self-designed and is superseded by
  A-hybrid (marked in place; that file's Option-A *mechanism* decision remains
  valid).
