# Plan: Document the roster's per-role GOTCHA-inlining model as intentional policy

_Plan stage output. Planned FROM the operator-converged brief
`plans/roster-gotcha-loading-brainstorm.md` (Approach C; orchestrator stays
prose-reference-only). This is a **documentation-only** change — no functional
agent/config edit. Light ATLAS pass per the brief (all changes are two-way
doors). Target files are **Tier-3 (operator-only)**; this plan describes the
edits for the operator to apply — `gleipnir-plan` (Tier-0) cannot and does not
apply them._

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Discipline-distribution model for the roster | **Approach C** — keep per-role GOTCHA inlining; only `gleipnir-brainstorm` loads the full skill; document the model as intentional policy | A (blanket-load all 9); B (load a judgment-bounded subset) | Operator-converged in the brief. C tops the weighted matrix (377 vs B 334 ≫ A 162); only option fully consistent with the token-efficiency goal *and* the model-sizing principle; avoids redundancy with already-inlined discipline. Not re-decided here. |
| 2 | Orchestrator load-vs-reference | **Orchestrator STAYS prose-reference-only** (references `skills/gotcha/SKILL.md` per Amendment 1; does not load the full skill) | Upgrade orchestrator to `Load skill gotcha` in Startup | Operator-converged in the brief. Its sequencing/loop-cap discipline is already inlined and `compaction_survival`-pinned; loading 349 lines every turn buys nothing it does not already carry. Not re-decided here. |
| 3 | One documentation home or two? (brief Open Question a) | **PRIMARY only** — add the note to `.gleipnir/skills/README.md`; do **not** add the optional `AGENTS.md` pointer | PRIMARY + reference-only `AGENTS.md` pointer | Plan-level call (delegated to plan by the brief, not material). PRIMARY-only is simplest, single-source, drift-free (matches the brief's own default recommendation). The `AGENTS.md` Roster section already discusses inlined discipline and model-sizing; a second pointer adds a maintenance surface for marginal reinforcement. Reversible two-way door — add later if the phantom gap ever re-surfaces from the governance file specifically. |
| 4 | Exact insertion point in `skills/README.md` (brief Open Question b) | **After "The named deltas" section, immediately before `## Status`** (after line 83) | Immediately after "The load-bearing point: layer 2" (after line 51) | Plan-level call (anchor choice, not material). The new note is about *who loads GOTCHA and why the roster inlines*; it is the same content category as the GOTCHA amendment subsections that live inside "The named deltas," and grouping it there (as the last subsection before Status) keeps all GOTCHA-distribution content contiguous. Placing it after layer-2 would split it from the amendments it depends on. |

All four decisions above are **not** material tradeoffs left open. #1 and #2 are
operator-converged (cited); #3 and #4 are the brief's explicitly plan-level Open
Questions, resolved here with reasoning. No new material tradeoff surfaced during
planning — see the closing report.

## Architect

- **Problem (one sentence):** The roster's "only 1 of 9 agents loads
  `skill gotcha`" state repeatedly re-surfaces as a phantom coverage gap; document
  that per-role GOTCHA inlining is intentional policy so it stops recurring.
- **User:** The operator (applies the Tier-3 edit) and every future reader/agent
  author who would otherwise re-open the "standardize gotcha loading" question.
- **Measurable success criteria:**
  1. `.gleipnir/skills/README.md` contains a subsection that (a) states only
     `gleipnir-brainstorm` loads the full skill and why, (b) explains bounded/
     mechanical roles inline their relevant slice, (c) explains judgment roles
     (including orchestrator, which stays prose-reference-only) also inline, and
     (d) explicitly says "1 of 9" is the expected correct state, not a gap.
  2. The note cites its provenance (`plans/roster-gotcha-loading-brainstorm.md`).
  3. No functional agent change: no agent frontmatter or Startup section is
     modified; orchestrator remains prose-reference-only.
  4. Single source of truth: the rationale lives in exactly one place
     (`skills/README.md`); no duplicate rationale elsewhere (PRIMARY-only, per
     Decision #3).
- **Constraints:**
  - **Tier-3, operator-only writer.** `.gleipnir/skills/**` and
    `.gleipnir/AGENTS.md` are Tier-3 (G-1). `gleipnir-plan` is a Tier-0 writer
    (`plans/**` only) and **must not** apply these edits. The operator applies.
  - **Token-efficiency goal is binding** — the documented model must justify
    itself against quality-efficient-outcomes-per-token, not "more coverage."
  - **Two-way door** — cheap to reverse; calibrate to the minimal change.

## Trace

- **Artifacts and source of truth:**
  - `.gleipnir/skills/README.md` — **source of truth** for GOTCHA distribution
    policy after this change (the new subsection). Tier-3.
  - `.gleipnir/AGENTS.md` — **not edited** (Decision #3: PRIMARY-only). Its
    existing Roster/model-sizing prose already implicitly reflects the inlining
    model; no pointer added.
  - `.gleipnir/plans/roster-gotcha-loading-brainstorm.md` — the converged brief,
    cited as provenance by the note.
  - This plan: `.gleipnir/plans/roster-gotcha-loading.md` (Tier-0, this file).
- **Integrations map:** None functional. The note is prose only; it does not bind
  to any Startup loader, frontmatter, engine, or guard. It documents existing
  behavior (each agent's already-inlined slice), which the brief verified:
  notify (notify.md:41–43), git-ops (git-ops.md:92–93), project-mgr
  (project-mgr.md:50–52), session-scribe (L-C4/L-C8), gleipnir-plan (plan.md:58),
  orchestrator (`compaction_survival`-pinned). No verification of those line
  numbers is required by *this* plan — they are the brief's evidence for a
  decision already converged; the note paraphrases them, it does not assert them
  as live citations.
- **Edge cases:**
  - **Future new unbounded-judgment agent** (watch item, not an action now): its
    relevant GOTCHA slice must be inlined at authoring time. The note makes the
    model explicit so this is a known onboarding step, not a rediscovered gap.
  - **Anchor drift:** the exact insertion point (after line 83, before
    `## Status`) is stated against README.md's current content (verified this
    session, 91 lines). If the file changes before the operator applies, the
    anchor is described semantically ("after the ATLAS layer-2 caveat / plan-
    persistence subsection, immediately before the `## Status` heading") so it
    survives minor edits.

## Link (validated before "building")

- **Verified `.gleipnir/skills/README.md` exists** and read in full (91 lines).
  Confirmed the anchor sections: "The named deltas" (lines 53–83, containing
  GOTCHA Amendment 1, Amendment 2, the Productive link, and the ATLAS layer-2
  caveat), followed directly by `## Status` (line 85). The insertion point after
  line 83 / before line 85 is confirmed real.
- **Verified the converged brief exists** and read in full; extracted the
  ready-to-apply draft markdown (brief lines 301–326) and the two Open Questions
  (brief lines 345–356).
- **Confirmed target-file tier:** `skills/**` and `AGENTS.md` are Tier-3 per
  `.gleipnir/AGENTS.md` trust-tier table. `gleipnir-plan` may write only
  `plans/**`. No attempt to write Tier-3 is made by this plan.
- **Confirmed this plan's own path** `.gleipnir/plans/roster-gotcha-loading.md`
  did not pre-exist (glob returned none) — this is a fresh Tier-0 write.

## Assemble (intended build order)

Because this is documentation-only and Tier-3, "build" = operator applies one
edit. Order:

1. **[operator, Tier-3]** Insert the PRIMARY subsection into
   `.gleipnir/skills/README.md` at the specified anchor (exact text in the
   Execution Workflow below).
2. **[operator or quality-reviewer]** Run the Stress-test consistency checks
   (below).
3. **No step 3.** `AGENTS.md` is deliberately not touched (Decision #3). No
   agent file, frontmatter, or Startup section is modified.

## Stress-test (acceptance checks)

Concrete, checkable criteria the applied change must satisfy:

1. **Presence & anchor:** `.gleipnir/skills/README.md` contains a new `##`
   subsection titled exactly `## Who loads GOTCHA — the per-role inlining model
   (intentional, not a gap)`, located after the ATLAS layer-2/plan-persistence
   subsection and immediately before the `## Status` heading.
2. **Content completeness:** the subsection states (a) only `gleipnir-brainstorm`
   loads the full skill + why; (b) bounded/mechanical Haiku roles inline their
   slice; (c) judgment roles (incl. orchestrator, prose-reference-only) inline;
   (d) "1 of 9" is expected/correct, not a gap, and must not be "fixed" by
   blanket-adding `Load skill gotcha`.
3. **Provenance:** the subsection cites
   `plans/roster-gotcha-loading-brainstorm.md`.
4. **No functional change (grep):** `git diff` touches only
   `.gleipnir/skills/README.md`. No `.gleipnir/agents/*.md` file changes; no
   Startup section or frontmatter is added/removed anywhere. Specifically,
    `grep -rl 'Load .skill gotcha.' .gleipnir/agents/` returns **only**
   `gleipnir-brainstorm.md` after the change (unchanged from before).
5. **Single source of truth (PRIMARY-only):** `.gleipnir/AGENTS.md` is unchanged
   (no new GOTCHA-loading pointer). The rationale appears in exactly one file.
6. **Reference-only consistency check (conditional):** *If* the operator elects
   to add the optional `AGENTS.md` pointer despite Decision #3, that pointer must
   be a **reference, not a copy** — it may name where GOTCHA is loaded and point
   to `skills/README.md`, but must **not** restate the rationale (the token-cost
   / model-sizing justification). Check: the added `AGENTS.md` line contains a
   pointer to `skills/README.md` and does **not** duplicate phrases like "349-line"
   or the per-turn-token-cost argument. (Under the plan's PRIMARY-only decision
   this check is vacuously satisfied because no pointer is added; it is retained
   so the constraint is on record if the operator overrides.)

## Execution Workflow

**Actor: the operator (Tier-3 write). `gleipnir-plan` cannot perform this.**

### The single edit — insert into `.gleipnir/skills/README.md`

**Location:** after the "The named deltas" section — i.e. immediately after the
ATLAS layer-2 caveat / plan-persistence subsection that ends at the current line
83 (`plan-format requirement (K-1).`), and immediately **before** the `## Status`
heading (current line 85). Insert a blank line, then the block below.

**Exact text to insert (word-for-word):**

```markdown
## Who loads GOTCHA — the per-role inlining model (intentional, not a gap)

Only `gleipnir-brainstorm` loads `skill gotcha` in its Startup — and only because
it also loads `brainstorm` + `decision-frameworks` and uses the full 6-layer
methodology framing. This is **deliberate**, not an oversight:

- **Bounded/mechanical roles inline the slice they use.** notify, project-mgr,
  git-ops, and session-scribe (Haiku, per the model-sizing principle) each carry
  the one or two GOTCHA guardrails relevant to their narrow job directly in their
  own agent file (e.g. notify's "verify outputs vs inputs"; git-ops's "merge, not
  rebase"; session-scribe's verify-against-disk). Loading the full 349-line skill
  into every turn of a mechanical role would be a permanent per-turn token cost
  for content the role cannot use — against the framework's own goal
  (quality-efficient outcomes per LLM token) and its model-sizing principle
  ("Haiku for mechanical roles").
- **Judgment roles also inline, not load.** Even `gleipnir-plan` (runs the GOTCHA
  pre-flight) and the `orchestrator` (whose identity *is* Amendment 1) inline
  their relevant discipline rather than load the whole skill; the orchestrator
  *references* this file in prose deliberately, and stays prose-reference-only.

So "only 1 of 9 agents loads gotcha" is the expected, correct state — evidence of
per-role inlining, not under-coverage. Do not "fix" it by blanket-adding
`Load skill gotcha` to every agent. (Decided at the roster-gotcha-loading
brainstorm; see `plans/roster-gotcha-loading-brainstorm.md`.)
```

**Refinements applied to the brief's draft (intent preserved):**
- In the second bullet, added "**and stays prose-reference-only**" to the
  orchestrator clause. This makes the operator-converged orchestrator sub-decision
  (Decision #2) explicit *in the note itself*, closing the loop so a reader cannot
  infer the orchestrator should upgrade to loading. Otherwise the brief's draft is
  preserved verbatim.

### After applying

- Run the Stress-test checks (§ above). In particular check #4's grep:
  `grep -rl 'Load .skill gotcha.' .gleipnir/agents/` → only
  `gleipnir-brainstorm.md`.
- No commit sequencing is prescribed here — that is the `git` stage's job
  (git-ops), sequenced by the orchestrator, not this plan.

### Explicit non-actions

- **Do NOT** edit `.gleipnir/AGENTS.md` (Decision #3: PRIMARY-only).
- **Do NOT** add `Load skill gotcha` to any agent Startup (Decision #1).
- **Do NOT** modify the orchestrator's load-vs-reference behavior (Decision #2).
- **`gleipnir-plan` does NOT and cannot apply the README.md edit** — it is Tier-3,
  operator-only. This plan describes it; the operator writes it.
