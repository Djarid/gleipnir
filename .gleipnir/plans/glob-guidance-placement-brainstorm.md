# Design Brief: Where the corrected glob-usage guidance (L-C16/L-C17) should live

_Brainstorm stage output. Operator-converged (Approach C). Input for `gleipnir-plan`._

## Problem Statement

The `glob` tool's `pattern` parameter returns **zero matches** whenever a
dot-prefixed directory segment is embedded directly in the pattern string (e.g.
`pattern=".gleipnir/agents/*.md"`) — even though the directory is real and named
literally. This is a reproducible false negative isolated to `glob` (not `read`,
not the filesystem). The corrected fix is to pass the dot-prefixed portion via
the separate `path` parameter, with `pattern` reduced to a bare wildcard (e.g.
`pattern="*.md", path=".gleipnir/agents"`).

The finding is diagnosed and fixed (recorded as L-C16, initial/imprecise, and
L-C17, corrected diagnosis + guidance). The **open question is placement**:
where should this guidance live so that *every agent that globs under
`.gleipnir/` (or any dot-prefixed directory) benefits* — not just this session's
lesson-candidate memory. Today it exists only as a lesson candidate; a
lesson-candidate file is not loaded as operating instruction by the agents that
glob, so the finding does not yet reach them.

This is a **material design decision** (a placement tradeoff with lasting
maintainability consequences), so it was surfaced to the operator to converge
before this brief was written.

## Constraints

- **Tier-3 write.** `.gleipnir/AGENTS.md`, `.gleipnir/agents/*.md`, and
  `.gleipnir/skills/**` are all Tier-3 (operator-only writer, G-1). The
  brainstorm and plan roles are Tier-0 writers; **only the operator may apply
  the actual edits**. This brief and the subsequent plan describe the change;
  they do not (and cannot) perform it.
- **Must reach every globbing agent.** The core requirement: agents that
  discover `.gleipnir/` state via `glob` (verified: ~7 of 9 roster agents) must
  receive the rule, ideally through a load path that does not depend on each
  agent remembering to opt in.
- **Drift resistance.** The guidance has already mutated once (L-C16 → L-C17);
  any placement that duplicates the rule across N files creates N places to keep
  in sync and is policed by consistency tests.
- **Content-category fit.** `AGENTS.md` is currently framework *governance*
  (layout, trust tiers, roster, guard-status). A tactical tool-usage note is a
  different content category and must be quarantined so it does not erode that
  file's purpose.
- **Two-way door.** Any placement is cheap to reverse (delete/move a section),
  which calibrates the analysis against over-engineering (e.g. rules out
  `compaction_survival` treatment for a low-stakes tooling tip).

## Approaches Considered

### Approach A: Canonical note in `AGENTS.md` (universal config-level auto-load)

**Summary:** Add a short, factual `## Tooling notes` section to
`.gleipnir/AGENTS.md`, which is loaded into *every* session via
`opencode.jsonc`'s `instructions:` block.

**Tradeoffs:**
- Pro: genuinely loaded in every session automatically (config-level guarantee,
  engine-driven) — no on-demand gap, no per-agent duplication, single source of
  truth.
- Pro: the finding is objectively universal (~7/9 agents glob `.gleipnir/`); a
  universal fact belongs in the universal file.
- Pro: cheapest to keep correct — one edit if the guidance changes again (and it
  already has: L-C16 → L-C17).
- Con: `AGENTS.md` is currently framework governance, not tactical tool-usage; a
  "how to call glob" note is a different content category and risks a precedent
  that erodes the file's purpose. **Fix:** quarantine under a clearly-labelled
  `## Tooling notes` section with a one-line scope statement ("environment tool
  quirks, not framework policy").

**Estimated scope:** 1 file (`.gleipnir/AGENTS.md`), Tier 3. Low complexity.
**Risk:** low — only risk is content-category creep, mitigated by quarantining.

### Approach B: Per-agent `## Discipline` note on the ~7 globbing agents

**Summary:** Add one bullet to the existing `## Discipline` section of each
agent that globs `.gleipnir/` (and to session-scribe's verify-against-disk
section).

**Tradeoffs:**
- Pro: lands the note directly in the context each agent already loads, phrased
  for that role.
- Pro: reuses an established, consistent pattern (`## Discipline` exists in 6
  agent files already).
- Con: ~7× duplication → drift risk. The L-C16 → L-C17 correction is direct
  evidence this guidance mutates; N copies = N places to fix, policed by
  consistency tests.
- Con: easy to miss an agent, or for a future new globbing agent to never get
  the note.

**Estimated scope:** ~7 files, Tier 3. Medium complexity (duplication).
**Risk:** medium — drift, already demonstrated by the L-C16 → L-C17 churn.

### Approach C: Hybrid — canonical `AGENTS.md` note + reference-only pointer in `session-scribe` (SELECTED)

**Summary:** Put the authoritative rule once in `AGENTS.md` (Approach A), and add
a single **reference** (not a copy) in `session-scribe`'s verify-against-disk
discipline section, because that is where a glob false-negative becomes a
*fabrication risk* (L-C16 was born from exactly that: "file not found by glob" ≠
"file does not exist").

**Tradeoffs:**
- Pro: single source of truth (no drift) plus role-local reinforcement exactly
  where a false negative could corrupt a report.
- Pro: the pointer references, not duplicates, the canonical rule — updates stay
  in one place.
- Con: slightly more surface than A alone; the pointer must be phrased as a
  reference ("see AGENTS.md `## Tooling notes`") so it never becomes a second
  copy that can drift. **Fix:** enforce reference-only phrasing (no restatement
  of the rule mechanics in session-scribe).

**Estimated scope:** 2 files (`.gleipnir/AGENTS.md` +
`.gleipnir/agents/session-scribe.md`), Tier 3. Low complexity.
**Risk:** low — only risk is the pointer drifting into a duplicate, mitigated by
reference-only phrasing.

### Approach D: Amend `gotcha/SKILL.md` (`## Guardrails` operating-discipline item)

**Summary:** Add the canonical glob rule as an operating-discipline item in
`gotcha/SKILL.md`'s `## Guardrails` list. Re-opened and given full rigor after
operator push-back (the operator's premise was that `gotcha` loads
unconditionally for every agent).

**Tradeoffs:**
- Pro: `gotcha`'s `## Guardrails` section is *explicitly* for "mistakes and
  learned behaviours" — the glob rule is exactly that content category (best
  semantic fit of the four).
- Pro: *if* the roster later standardises on every agent loading `gotcha` in
  Startup, this becomes a strong single-source universal-reach option.
- Con (decisive): **`gotcha` does not currently reach the agents that need it.**
  Grep-verified across all 9 agent files: only `gleipnir-brainstorm` loads
  `skill gotcha` in its Startup (line 51); the `orchestrator` merely *references*
  the file in prose (line 59), and the other 7 agents load no skills at all.
  Placing the rule here reaches **1 of ~7** affected agents today. The operator's
  premise ("gotcha loads unconditionally for every agent") is **not true as the
  roster stands**.
- Con: the load path is an **agent-authored convention** (a Startup line each
  agent must author), strictly weaker than A's config-level `instructions:`
  guarantee — a future globbing agent that omits the `skill gotcha` line (as 7
  of 9 current agents do) silently never gets the rule.
- Con: the `## Guardrails` list is slated to become **G-4c measured-graduation**
  content, not manual appends (per gotcha's own GLEIPNIR link note) — a
  hand-added tip is mildly against its declared future mechanism.

**Estimated scope:** 1 file (`.gleipnir/skills/gotcha/SKILL.md`), Tier 3. Low
complexity, but reach-limited.
**Risk:** medium — *looks* universal but under-delivers reach today; the false
sense of coverage is the real hazard (see Decision Analysis, second-order note).

### Rejected before the matrix

- **`compaction_survival` frontmatter bullet** (prompt Approach 4): Reversibility
  Filter classes this a two-way-door, low-stakes tooling fact.
  `compaction_survival` is reserved for hard non-negotiable pipeline rules (only
  the orchestrator carries it). Applying it to a glob tip is over-engineering.
- **`goals/` entry** (prompt Approach 5): goals are read only by planning agents
  and, per the GOTCHA layer model, hold *what to achieve*, not *how to call a
  tool*. Wrong content category and wrong reach.

## Decision Analysis

**Decision type:** Multi-option placement with a maintainability/reach tradeoff.
Primary framework **Weighted Decision Matrix** (multi-option comparison),
cross-checked with **Second-Order Thinking** (drift/false-coverage is the crux)
and the **Reversibility Filter** (all options are two-way doors → analysis
calibrated, not exhaustive).

**Reversibility:** Two-Way Door. Any placement is cheap to undo. Lowers stakes;
argues against over-engineering (rules out compaction-survival treatment).

### Weighted Decision Matrix (final, four options)

Criteria and weights held constant across both passes; D scored on the
grep-verified loading reality.

| Criterion | Weight | A (AGENTS.md) | B (per-agent Discipline) | C (hybrid A+scribe) | D (gotcha skill) |
|---|---|---|---|---|---|
| Reaches every globbing agent automatically | 9 | 10 → 90 | 6 → 54 | 10 → 90 | 2 → 18 |
| Low duplication / drift resistance | 8 | 10 → 80 | 3 → 24 | 8 → 64 | 9 → 72 |
| Fits existing content conventions | 6 | 5 → 30 | 9 → 54 | 7 → 42 | 9 → 54 |
| Maintenance cost when guidance changes | 7 | 10 → 70 | 3 → 21 | 8 → 56 | 9 → 63 |
| Role-local reinforcement where stakes highest | 4 | 4 → 16 | 8 → 32 | 9 → 36 | 3 → 12 |
| **Total** | | **286** | **185** | **288** | **219** |

**Ranking:** C (288) ≈ A (286) at the top; D (219) third — genuinely stronger
than B, best-in-class on content fit and drift resistance, but disqualified from
the top by the reach criterion (18/90, the most heavily weighted). B (185) trails
badly on drift/maintenance — its core weakness, already demonstrated by the
L-C16 → L-C17 churn.

**A vs C** is within noise. The real material question surfaced to the operator
was whether the single role-local *pointer* in session-scribe is worth the small
extra surface — justified because session-scribe is where a glob false-negative
becomes a fabrication risk (L-C16's origin). **The operator converged on C.**

**Second-Order Thinking (the crux).** Near-term, any option makes agents glob
correctly. The far-term dominant effect is maintainability: guidance in N places
drifts (2nd-order: an agent follows stale advice; 3rd-order: a false "file
missing" conclusion drives a wrong action — re-creating an existing file, the
L-C16 inverse-fabrication hazard). This is why A and C (single source) dominate B
decisively. For **D specifically**: amending gotcha *looks* like a clean
single-source fix, but 7/9 globbing agents never load gotcha, so the bug keeps
biting session-scribe/reviewers/code — and worse, the "we fixed it in gotcha"
belief *suppresses* placing it where it is actually read. That false-coverage
third-order effect is why D ranks below A/C despite better content fit.

### Bias checks (both passes)

**Pass 1 (A/B/C):**
- ⚠️ **Scope Creep Bias (low-moderate) — on C:** C accommodates two placements.
  Defensible *only* because session-scribe's case is a genuinely distinct,
  higher-stakes discipline (fabrication risk), not a generic copy. A-alone
  remains the clean minimal alternative. (Operator confirmed C, accepting this.)
- ⚠️ **IKEA Effect (low) — on B:** the `## Discipline` pattern is an in-house
  convention; B is attractive partly because the pattern already exists.
  Evaluated on merits, the pattern's drift cost outweighs its familiarity here.
- Checked, not triggered: Anchoring (option ordering did not drive the ranking),
  Status Quo (no incumbent placement to protect).

**Pass 2 (adds D, after operator push-back):**
- ⚠️ **Confirmation Bias — flagged against my own prior:** my first pass
  dismissed "a skill" as a category. Counter-evidence was deliberately sought:
  D's content fit is genuinely the *best* of the four (gotcha's Guardrails is
  purpose-built for exactly this), and its drift resistance ties the top. D
  loses **only** on the empirically-verified reach fact (1 of 7 agents load
  gotcha) — not on my earlier reasoning. The low rank is grounded in the grep,
  not in the prior.
- ⚠️ **Authority Bias (toward the operator):** the operator asserted "gotcha is
  loaded unconditionally by every agent." Authoritative-sounding but
  **grep-falsified** — only `gleipnir-brainstorm` loads it in Startup; the other
  7 agents load no skills, and the orchestrator only references the file in
  prose. D was scored on the real load reality, not the assumed one. The premise
  did not hold; the analysis followed the evidence.
- ⚠️ **Scope Creep Bias (low) — on C, unchanged:** as pass 1.
- Checked, not triggered: Anchoring (operator's option-ordering did not drive
  scores), Status Quo (no incumbent), IKEA (gotcha's convention familiarity did
  not inflate D — evidence did).

### Constructive reframing of D (Pros-Cons-Fixes "Fix")

D's fatal flaw is *reach, not fit*. If the intent is "make gotcha the universal
discipline home," the Fix is a **larger, separate decision**: standardise a
Startup `Load skill gotcha` line across all roster agents (turning the
agent-authored convention into a roster-wide norm). That touches 7 agent files
and changes the discipline-distribution model — **out of scope for this
glob-placement decision**, and correctly deferred to its own later brainstorm
(the operator has opted to open that separately). Folding it in here would be
Scope Creep.

## Selected Approach

**Choice: Approach C (operator-converged).** Canonical `## Tooling notes` section
in `.gleipnir/AGENTS.md` carrying the glob rule + `path`-parameter fix, PLUS one
**reference-only** pointer (not a duplicate) in `session-scribe`'s existing
verify-against-disk discipline section pointing back to the canonical AGENTS.md
note. Approach D (amend gotcha) is explicitly **rejected as the primary home
today** (reaches only 1/7 agents); the roster-wide "standardise gotcha-loading"
question is being opened as its own separate, later brainstorm and is **not part
of this brief**.

**Rationale:** C ties for the top matrix score (288), gives a single
config-level source of truth (no drift) via the `instructions:`-loaded
`AGENTS.md`, and adds role-local reinforcement precisely where a glob
false-negative turns into a fabrication risk (session-scribe, L-C16's origin).
The pointer is phrased as a reference so it can never drift into a second copy.
D was fully re-evaluated with equal rigor and rejected on the grep-verified fact
that gotcha reaches only 1 of ~7 affected agents.

### Exact content to apply (for `gleipnir-plan` to plan the change, operator to write)

> Note: exact wording is the operator's to finalise at write time (Tier-3).
> The following is the converged intent and a ready-to-apply draft.

**1. New section in `.gleipnir/AGENTS.md`** (placed after the existing
governance sections; heading and one-line scope disclaimer quarantine it from
governance content):

```markdown
## Tooling notes

Environment tool quirks that affect every agent — *not* framework policy or
guard semantics. Kept here because `.gleipnir/AGENTS.md` is the only file loaded
into every session (via `opencode.jsonc` `instructions:`).

- **`glob` and dot-prefixed directories (`.gleipnir/`, any `.`-prefixed path).**
  A dot-prefixed directory segment embedded directly in the `pattern` string
  (e.g. `pattern=".gleipnir/agents/*.md"`) returns **zero matches** even though
  the directory is real and named literally — the glob engine applies its
  "skip hidden entries" convention to a segment typed literally in the pattern,
  where it should not. **Fix:** pass the dot-prefixed portion via the separate
  `path` parameter and reduce `pattern` to a bare wildcard — e.g.
  `pattern="*.md", path=".gleipnir/agents"`. "File not found by glob" is **not**
  proof of absence for dot-prefixed paths; when the pattern embeds a
  dot-segment, re-run with `path` before concluding a file is missing.
  (Recorded as L-C16 → L-C17.)
```

**2. Reference-only pointer in `.gleipnir/agents/session-scribe.md`**, appended
to the existing `## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)`
section (reference only — must not restate the rule mechanics, so it cannot
drift):

```markdown
- When verifying a path exists via `glob`, beware the dot-prefixed-directory
  false negative: a `glob` whose `pattern` embeds a `.gleipnir/`-style segment
  can wrongly report "not found" for a real file (the inverse fabrication risk —
  falsely denying truth). See the canonical rule and the `path`-parameter fix in
  `.gleipnir/AGENTS.md` `## Tooling notes`. Do not restate it here.
```

## Open Questions

- **Exact placement of `## Tooling notes` within `AGENTS.md`.** After the
  guard-status table, or a different anchor? (Operator/plan to decide the
  insertion point; does not change the converged approach.)
- **Consistency-test coverage.** Should a consistency check assert the
  session-scribe pointer stays reference-only (no duplication of the rule text)?
  Deferred to plan/quality — not a material design decision.
- **Separate future brainstorm (out of scope here):** whether to standardise a
  Startup `Load skill gotcha` line across all roster agents (the D reframing).
  Being handled as its own brainstorm; noted only so `gleipnir-plan` does not
  fold it in.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Canonical rule (universal auto-load) | `.gleipnir/AGENTS.md` — new `## Tooling notes` section (Tier 3, operator writes) |
| Role-local reference (fabrication-risk site) | `.gleipnir/agents/session-scribe.md` — one bullet in existing verify-against-disk section (Tier 3, operator writes) |
| Consistency (optional, plan/quality) | consistency test asserting the session-scribe pointer stays reference-only |
| Lesson bookkeeping | L-C16/L-C17 remain the historical lesson-candidate record; this brief resolves their *placement* question |

**Tier note for `gleipnir-plan`:** both target files are Tier-3
(operator-authored). The plan describes the two edits and their verification;
the operator applies them. Full ATLAS is warranted — this is a real Tier-3 change
touching two files with a cross-file consistency concern.
