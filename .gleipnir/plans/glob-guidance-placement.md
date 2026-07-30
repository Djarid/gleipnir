# Plan: Place the corrected glob-usage guidance (L-C16/L-C17)

_Plan stage output (`gleipnir-plan`). Planned FROM the operator-converged
brainstorm brief `.gleipnir/plans/glob-guidance-placement-brainstorm.md`
(Approach C). This plan does **not** re-decide placement; it specifies the two
edits, their exact text and insertion points, and their verification._

**Tier / writer note (read first).** Both target files are **Tier-3**
(operator-only writer, G-1): `.gleipnir/AGENTS.md` and
`.gleipnir/agents/session-scribe.md`. `gleipnir-plan` is a **Tier-0 writer** —
it may write only `.gleipnir/plans/**` and therefore **cannot apply these
edits**. This plan *describes* the edits so the **operator** (or the operator's
build-mode escape hatch) applies them, or so a future
`gleipnir-code` → `quality` delegation applies them **if and only if** the
operator explicitly authorizes that Tier-3 path. Nothing here writes Tier-3.

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|----------|--------|----------|-----------|
| 1 | Where the canonical glob rule lives | Hybrid (Approach **C**): canonical `## Tooling notes` in `.gleipnir/AGENTS.md` + one **reference-only** pointer in `session-scribe.md` | A (AGENTS.md only), B (per-agent `## Discipline` on ~7 agents), D (amend `gotcha/SKILL.md`), plus `compaction_survival` frontmatter and a `goals/` entry | **Operator-converged** (brief §Selected Approach). C tied top of the weighted matrix (288 vs A 286, D 219, B 185): single config-level source of truth via `AGENTS.md` `instructions:` auto-load (no drift), plus role-local reinforcement exactly where a glob false-negative becomes a fabrication risk (session-scribe, L-C16's origin). D rejected on grep-verified reach (gotcha loads for only 1 of ~7 affected agents). |
| 2 | Session-scribe entry form: pointer vs copy | **Reference-only** pointer ("see AGENTS.md `## Tooling notes`"), explicit "Do not restate it here" | A second copy of the rule mechanics | **Inherited from the converged brief, not a fresh plan-stage decision:** the "reference (not a copy)" pointer is part of Approach C's very definition (brainstorm.md L96–110, L252–259). Its rationale — drift resistance (the rule already mutated once, L-C16 → L-C17; a copy is a second place to keep in sync) — is likewise the brief's (L103–110). Reference-only is what keeps C a single source of truth. |
| 3 | Insertion point of `## Tooling notes` in `AGENTS.md` | As the **final section**, appended after `## What this scaffold does NOT include` (current last section, ends line 149) | Immediately after the guard-status table (mid-file) | Bounded editorial choice, NOT a material design decision (brief §Open Questions leaves it to the plan). Placing it last keeps the governance narrative (layout → tiers → roster → model sizing → guard status → seams → scaffold-scope) uninterrupted and treats the tooling note as a clearly-fenced appendix, reinforcing the "not framework policy" quarantine. Two-way door: trivially movable. |
| 4 | Consistency-test coverage of the reference-only invariant | Specify a **manual consistency check** in Stress-test now; flag an automated check as a **deferred, optional** follow-up for quality/test | Build an automated consistency test as part of this change | Brief §Open Questions defers this to plan/quality and calls it "not a material design decision." A manual check is sufficient for a two-file, low-stakes change; an automated grep assertion is worth noting but not blocking. |

> **No new material tradeoff surfaced during planning.** Every material choice
> was resolved by the operator at the brainstorm gate (row 1); rows 2–4 are
> bounded refinements within the converged intent. If an implementing agent
> finds a genuine tradeoff, stop and route it back to the operator — do not bake
> it in.

## Architect

- **Problem (one sentence).** The corrected glob-usage guidance (dot-prefixed
  directory segments embedded in a `glob` `pattern` return zero matches; the fix
  is to pass the dot-prefixed portion via the separate `path` parameter) exists
  only as a lesson candidate (L-C16 → L-C17) that no globbing agent loads as
  operating instruction, so the finding does not reach the ~7 of 9 roster agents
  that glob under `.gleipnir/`.
- **User.** Every roster agent that discovers `.gleipnir/` (or any `.`-prefixed)
  state via `glob` — most acutely `session-scribe`, `quality-reviewer`, and
  `gleipnir-code`, where a false "not found" can drive a wrong action
  (fabrication / re-creating an existing file — the L-C16 inverse hazard).
- **Measurable success criteria.**
  1. `.gleipnir/AGENTS.md` contains a single canonical `## Tooling notes`
     section stating the glob dot-prefix false-negative and the `path`-parameter
     fix, fenced with a one-line "environment tool quirks, not framework policy"
     scope statement.
  2. `.gleipnir/agents/session-scribe.md`'s existing
     `## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)` section
     contains exactly **one** new bullet that **references** the canonical rule
     and does **not** restate its mechanics.
  3. The rule text (the `pattern`/`path` mechanics) appears in **exactly one**
     place across `.gleipnir/` (AGENTS.md); session-scribe holds only a pointer.
  4. The AGENTS.md governance narrative is unchanged except for the appended
     section; no governance content is edited or reordered.
- **Constraints.**
  - **Tier-3 write barrier.** Both files are operator-only (G-1). `gleipnir-plan`
    cannot and does not apply the edits.
  - **Single source of truth / drift resistance.** No duplication of the rule
    across files (the L-C16 → L-C17 churn is direct evidence it mutates).
  - **Content-category quarantine.** A tactical tool-usage note must be visibly
    fenced from `AGENTS.md`'s governance content (layout, tiers, roster, guards).
  - **Two-way door.** Every edit is cheap to reverse (delete/move a section);
    calibrates against over-engineering.

## Trace

**Artifacts and where they live (source of truth).**

| Artifact | Path | Tier / writer | Source-of-truth role |
|----------|------|---------------|----------------------|
| Canonical glob rule + `path` fix | `.gleipnir/AGENTS.md` → new `## Tooling notes` | Tier 3 (operator) | **The** authoritative statement of the rule; the only copy. |
| Role-local reference | `.gleipnir/agents/session-scribe.md` → new bullet in the verify-against-disk section | Tier 3 (operator) | Pointer only; carries no rule mechanics. |
| This plan | `.gleipnir/plans/glob-guidance-placement.md` | Tier 0 (`gleipnir-plan`) | Describes the change; disposable after edits merge. |
| Brainstorm brief | `.gleipnir/plans/glob-guidance-placement-brainstorm.md` | Tier 0 | Converged decision record this plan inherits. |
| Lesson-candidate history | `.gleipnir/lessons/session-lessons-candidates.md` (L-C16/L-C17) | Tier 2 | Historical record of the finding; **not** edited by this change (its *placement* question is what this plan resolves). |

**Integrations map (why placement reaches the users).**

- `.gleipnir/AGENTS.md` is loaded into **every** session via `opencode.jsonc`'s
  `instructions:` block — the config-level, engine-driven load path that gives
  the canonical rule universal reach without per-agent opt-in.
- `session-scribe.md` is that agent's own operating prompt; the new bullet loads
  whenever session-scribe runs, reinforcing the rule precisely at the
  fabrication-risk site.
- **Not** integrating via `gotcha/SKILL.md` (Approach D): grep-verified, only
  `gleipnir-brainstorm` loads `skill gotcha` in Startup; the other agents do
  not — so gotcha reaches 1 of ~7 globbing agents. Rejected as primary home
  (Decision row 1). The roster-wide "standardise gotcha-loading" question is a
  **separate future brainstorm, explicitly out of scope here** (brief §Open
  Questions; do not fold it in).

**Exact insertion points (verified on disk this session).**

- `AGENTS.md`: file is **149 lines**; last section is
  `## What this scaffold does NOT include` (heading line 140, body ends line
  149). The new section is **appended after line 149** (a blank line, then the
  section). No existing line is edited.
- `session-scribe.md`: the target section
  `## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)` is at
  **line 82**; its bullets run lines 84–92; the next heading
  `## SESSION-STATE.md format (the resume artifact you own)` is line 94. The new
  bullet is **appended as the last bullet of that section**, after the current
  final bullet (line 92, "...never asserted as fact."), before the blank line
  preceding line 94. No existing bullet is edited.

**Edge cases.**

- **Pointer drifts into a duplicate.** Mitigated by reference-only phrasing that
  names the canonical location and says "Do not restate it here" (Decision row
  2; verified in Stress-test).
- **Content-category creep in AGENTS.md.** Mitigated by the `## Tooling notes`
  scope disclaimer ("environment tool quirks — not framework policy or guard
  semantics") (Decision row 3).
- **Someone edits the rule in session-scribe instead of AGENTS.md.** The
  reference-only bullet has no mechanics to edit, so there is nothing there to
  change — updates are forced back to the single source.
- **Future globbing agent.** Automatically covered by the AGENTS.md auto-load;
  no per-agent action required.
- **L-C16/L-C17 files.** Left untouched; this change resolves their placement,
  not their content.

## Link (validated before building)

- ✅ Brainstorm brief read in full; Approach **C** is operator-converged
  (brief lines 94, 194, 250–267). Placement is settled; not re-decided.
- ✅ `plan-format.md` structure confirmed, including the **required**
  `## Decisions (index)` table — present above.
- ✅ `AGENTS.md` tail read; confirmed 149 lines and last section identity for a
  precise, non-destructive append point.
- ✅ `session-scribe.md` read in full; confirmed the exact verify-against-disk
  section heading (line 82) and its current final bullet (line 92) for a precise
  append point.
- ✅ Tier map confirmed: both targets Tier-3 (AGENTS.md AGENTS.md trust-tier
  table; session-scribe frontmatter denies `AGENTS.md` and `agents/`). `gleipnir-plan`
  is Tier-0 — cannot write either. This plan describes only.
- ✅ Draft text from the brief's "Exact content to apply" section reviewed and
  lightly refined for flow (below) while preserving the converged intent:
  canonical rule in AGENTS.md, reference-only pointer in session-scribe.

## Assemble (intended build order)

The two edits are independent (different files, no ordering dependency), but a
sensible order for the operator is **canonical first, pointer second**, so the
pointer's target already exists when it is written:

1. **Edit 1 — `.gleipnir/AGENTS.md` (operator, Tier-3).** Append the new
   `## Tooling notes` section verbatim (see below) after the current final line
   (149), preceded by one blank line. Do not touch any existing section.
2. **Edit 2 — `.gleipnir/agents/session-scribe.md` (operator, Tier-3).** Append
   the single reference-only bullet verbatim (see below) as the last bullet of
   the `## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)`
   section (after line 92, before the blank line preceding line 94). Do not edit
   any existing bullet.
3. **Verify (any reader / quality).** Run the Stress-test checks below.

### Edit 1 — word-for-word text to append to `.gleipnir/AGENTS.md`

Append after the last line of the file (after line 149), preceded by a single
blank line:

```markdown
## Tooling notes

Environment tool quirks that affect every agent — *not* framework policy or
guard semantics. Kept here because `.gleipnir/AGENTS.md` is the only file loaded
into every session (via `opencode.jsonc` `instructions:`), so a note here
reaches every agent without per-agent opt-in.

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

_Refinement note: one clause added to the scope sentence ("so a note here
reaches every agent without per-agent opt-in") to make the quarantine
rationale explicit; rule mechanics unchanged from the brief draft._

### Edit 2 — word-for-word text to append to `.gleipnir/agents/session-scribe.md`

Append as the final bullet of the
`## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)` section
(after the current line 92 "...never asserted as fact." bullet):

```markdown
- When verifying a path exists via `glob`, beware the dot-prefixed-directory
  false negative: a `glob` whose `pattern` embeds a `.gleipnir/`-style segment
  can wrongly report "not found" for a real file — the inverse fabrication risk
  (falsely denying truth), which is exactly how L-C16 arose. **Reference only:**
  see the canonical rule and the `path`-parameter fix in `.gleipnir/AGENTS.md`
  `## Tooling notes`. Do not restate the mechanics here.
```

_Refinement note: kept strictly reference-only. Wording tightened for flow
("which is exactly how L-C16 arose"; "Do not restate the mechanics here") while
carrying **no** `pattern`/`path` how-to — the pointer names the fix's existence
and its canonical location, never the fix itself._

## Stress-test (acceptance checks)

After the operator applies both edits, the change is accepted iff **all** hold:

1. **Canonical section present & fenced.** `.gleipnir/AGENTS.md` contains a
   `## Tooling notes` heading whose first paragraph states it is "not framework
   policy or guard semantics." (`rg -n "## Tooling notes" .gleipnir/AGENTS.md`
   returns exactly one hit.)
2. **Rule mechanics in exactly one file.** The `path`-parameter fix phrasing
   (e.g. `path=".gleipnir/agents"` or "pass the dot-prefixed portion via the
   separate `path` parameter") appears in `.gleipnir/AGENTS.md` and **nowhere
   else** under `.gleipnir/agents/` or `.gleipnir/skills/`.
   (`rg -n 'separate .path. parameter' .gleipnir/` → single file:
   AGENTS.md.)
3. **Pointer present & reference-only.** `.gleipnir/agents/session-scribe.md`'s
   `## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)` section
   contains exactly one new bullet that (a) names
   `` .gleipnir/AGENTS.md `## Tooling notes` `` as the canonical location and
   (b) contains **no** `pattern=`/`path=` example or "skip hidden entries"
   mechanics. Consistency invariant: the string
   `path=".gleipnir/agents"` (or any `pattern=`/`path=` example) does **not**
   appear in `session-scribe.md`.
4. **No collateral edits.** `git diff` shows only (a) an appended section in
   `AGENTS.md` (no existing line changed) and (b) one appended bullet in
   `session-scribe.md`'s verify section (no existing bullet changed). Governance
   sections, roster, trust-tier table, and guard-status table are byte-identical.
5. **L-C16/L-C17 untouched.** `.gleipnir/lessons/session-lessons-candidates.md`
   is unchanged by this plan.

**Deferred / optional (flag to quality/test, not blocking):** an automated
consistency test asserting invariant #3 (session-scribe holds no rule mechanics;
grep for `pattern=`/`path=` examples in `session-scribe.md` must be empty). Noted
per brief §Open Questions; a two-file manual check suffices for this low-stakes,
two-way-door change.

## Execution Workflow

For the agent/operator applying this plan:

1. **Confirm the writer path.** These are **Tier-3** edits. Only the operator
   (or the operator's build-mode escape hatch) may apply them; a
   `gleipnir-code`/`quality` delegation may do so **only if the operator
   explicitly authorizes** that path. `gleipnir-plan` and `gleipnir-brainstorm`
   (Tier-0) must not.
2. **Apply Edit 1** to `.gleipnir/AGENTS.md`: append the `## Tooling notes` block
   verbatim after line 149 (blank line first). Re-read the tail to confirm it
   landed and that no prior section changed.
3. **Apply Edit 2** to `.gleipnir/agents/session-scribe.md`: append the single
   reference-only bullet as the last bullet of the verify-against-disk section
   (after line 92, before the blank line preceding the `## SESSION-STATE.md`
   heading). Re-read the section to confirm it landed and is reference-only.
4. **Run the Stress-test checks** (1–5 above). If any fails — especially #2/#3
   (rule appears in >1 file, or the pointer carries mechanics) — stop and fix
   before considering the change done.
5. **Do not touch** L-C16/L-C17 in
   `.gleipnir/lessons/session-lessons-candidates.md`; this change resolves their
   placement, not their content.
6. **Out of scope — do not fold in:** the roster-wide "standardise a Startup
   `Load skill gotcha` line across all agents" question (the Approach-D
   reframing). It is its own future brainstorm (brief §Open Questions). If it
   arises, route it to the operator, do not add it here.
7. **On any material tradeoff** discovered mid-application (not merely an
   editorial phrasing choice), stop and route it back to the operator via the
   brainstorm/convergence gate — do not resolve it inline.
