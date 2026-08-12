# Plan: Session-resume startup instruction in `.gleipnir/AGENTS.md`

_Planned FROM the converged brief `session-state-startup-instruction-brainstorm.md`
(Approach C, operator-converged). Tier-0 session artifact. This plan produces an
exact, ready-to-apply patch for the operator — `.gleipnir/AGENTS.md` is Tier-3
(POLICY), agent-unwritable; no roster agent (including this planner) can apply it._

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|----------|--------|----------|-----------|
| 1 | Scoping of the resume instruction | Approach C — address orchestrator directly + explicit "subagents skip" line | A (prose-scoped, orchestrator only); B (tell every agent) | Operator-converged in brief. C turns the unavoidable "AGENTS.md loads into every session" fact into an active token saving vs A's passive hope; B imposes recurring per-subagent token cost + over-trust risk. |
| 2 | Placement of the new section | New top-level `## Session resume`, inserted immediately **before** `## Tooling notes` (after `## What this scaffold does NOT include`) | Fold into `## Tooling notes`; append at end of file | Operator-converged in brief: `## Tooling notes` is explicitly scoped to env/tool quirks, not process guidance; process guidance warrants its own section and should precede env quirks. |
| 3 | **Roster list in the "subagents skip" line** | **Correct the brief's stale list**: enumerate all **8** subagents (add `session-scribe`) **but carve `session-scribe` out** of the blanket skip, because it *owns and churns* SESSION-STATE.md and must read disk state first | Paste the brief's 7-name list verbatim (stale — omits `session-scribe`); OR add `session-scribe` to the skip list uncorrected (actively wrong — would tell the file's writer not to read it) | Verified against `.gleipnir/agents/*.md`: 9 agents exist (orchestrator + 8 subagents). Brief's list is stale. `session-scribe.md` L82–127 requires it to read current disk state before churning the file. This is the material correction the plan makes to the brief's exact text. |
| 4 | Relationship to existing `goals/resume.md` | Keep both; the AGENTS.md section is the always-loaded nudge, `goals/resume.md` is the "check goals first" reference — no contradiction | Delete/replace `goals/resume.md`; make AGENTS.md the sole home | `goals/resume.md` is Tier-3 and out of scope for this change. The two are consistent (both point at SESSION-STATE.md, both label it non-authoritative). Stress-test S4 confirms non-contradiction. |
| 5 | Code/test changes | **None anywhere** — pure documentation-as-policy | Any src/ or tests/ edit; `opencode.jsonc` edit | The `instructions:` wiring already loads AGENTS.md into every session (opencode.jsonc L94–96, verified). No behavioural code depends on this prose. |

## Architect

**Problem (one sentence):** A fresh orchestrator session has nothing in its
always-loaded instruction context telling it that `.gleipnir/plans/SESSION-STATE.md`
is a resume entry point, so cross-session in-flight work can only be resumed if
the operator points the session at it manually every time.

**User:** The orchestrator (primary agent) at session start; secondarily the
operator, who is relieved of manually re-pointing each fresh session.

**Measurable success criteria:**
- A new top-level `## Session resume` section exists in `.gleipnir/AGENTS.md`,
  placed immediately before `## Tooling notes`.
- The section addresses the orchestrator to read SESSION-STATE.md at session
  start *if present and describing real prior work*, degrading gracefully to
  "no session to resume" otherwise (never a hard dependency).
- The section labels SESSION-STATE.md a **pointer, not authoritative** (echoing
  its own Tier-0 header), directing to `../decisions/` + the spec as truth.
- The section tells bounded subagents their scoped delegation is authoritative
  and they need not read SESSION-STATE.md — **with `session-scribe` correctly
  excluded from that skip**, because it owns/churns the file.
- Zero changes to code, tests, `opencode.jsonc`, subagent frontmatter, or any
  other file. Pure documentation-as-policy.

**Constraints (inherited from brief, all verified this session):**
- `.gleipnir/AGENTS.md` is Tier-3 POLICY, operator-authored only (G-1). The plan
  delivers ready-to-paste prose + exact diff; it does **not** (and cannot) apply it.
- `opencode.jsonc` `instructions:` (verified L94–96) loads AGENTS.md into every
  session unconditionally — orchestrator and all 8 subagents. Scoping is only
  achievable in the prose, not at the opencode layer.
- Token-efficiency is the framework's stated goal (AGENTS.md L19–22). The
  "subagents skip" line is the active token-saving mechanism.
- SESSION-STATE.md is explicitly NOT authoritative (its own header, verified
  L3–6). The instruction must not cause over-trust.
- Must degrade gracefully on a fresh clone (absent / stale-example file).

## Trace

**Artifacts and where they live (source of truth):**

| Artifact | Path | Status | Role |
|----------|------|--------|------|
| Target instruction file | `.gleipnir/AGENTS.md` | **exists** (168 lines, verified) | Tier-3; the only file loaded into every session. Receives the new section. |
| Resume entry point | `.gleipnir/plans/SESSION-STATE.md` | **exists** (278 lines, verified) | Tier-0 volatile; the file the new section points at. |
| Existing resume goal | `.gleipnir/goals/resume.md` | **exists** (22 lines, verified) | Tier-3 "check goals first" reference; consistent with the new section (Decision 4). |
| opencode instructions wiring | `opencode.jsonc` L93–97 | **exists / verified** | Confirms AGENTS.md loads into every session. **Not modified.** |
| Roster (ground truth for Decision 3) | `.gleipnir/agents/*.md` | **exists** (9 files, verified) | The authoritative subagent list the "skip" line must match. |

**Roster verification (the material correction — Decision 3):**
`glob(pattern="*.md", path=".gleipnir/agents")` returns **9** agents:

1. `orchestrator` — primary; correctly NOT in the skip list (it is the addressee).
2. `gleipnir-brainstorm` — in brief's list ✓
3. `gleipnir-plan` — in brief's list ✓
4. `gleipnir-code` — in brief's list ✓
5. `quality-reviewer` — in brief's list ✓
6. `git-ops` — in brief's list ✓
7. `project-mgr` — in brief's list ✓
8. `notify` — in brief's list ✓
9. **`session-scribe` — MISSING from brief's list.** ⚠️

The brief's proposed skip list (`gleipnir-brainstorm, gleipnir-plan,
gleipnir-code, quality-reviewer, git-ops, project-mgr, notify`) is **stale**: it
omits `session-scribe`. AGENTS.md L30 ("8-role roster") and L98–102 are likewise
stale relative to the 9-agent reality — but *correcting AGENTS.md's roster count
is out of scope for this change* (flagged below as a follow-up, not folded in).

**Why `session-scribe` cannot be added to a blanket "skip" list:**
`session-scribe.md` (verified) says it *owns and churns* SESSION-STATE.md
(L100–127) and is required to **read the current disk state before writing**
(L82–90: "Before writing session state, read the current disk state you are about
to summarise … Never state a slice is 'built' … unless disk confirms it"). A line
telling `session-scribe` to skip reading SESSION-STATE.md would directly
contradict its own agent definition. The correct resolution (Decision 3): list
all 8 subagents for completeness/accuracy, but **explicitly except
`session-scribe`** from the skip (it reads the file to maintain it, not to
resume).

**Integrations map:** None behavioural. The change is inert prose consumed by the
LLM at session start via the `instructions:` load. No component, engine, test, or
tool reads or depends on this section programmatically.

**Edge cases (all handled in the proposed prose):**
- Fresh clone, file absent → "treat as no session to resume, proceed normally."
- File present but only stale-example text → same graceful path ("no real prior work").
- A subagent misreads scoping and reads the file anyway → wasted context only; no
  correctness impact (file is a pointer, and subagents act on their scoped delegation).
- `session-scribe` invoked to churn the file → excepted from skip; reads disk as required.

## Link (validated before building)

- `.gleipnir/AGENTS.md` read in full (168 lines) — insertion point confirmed:
  the file currently ends with `## Tooling notes` (L151–168). The new section
  goes between `## What this scaffold does NOT include` (ends L149) and
  `## Tooling notes` (starts L151), i.e. at the current blank line 150.
- `opencode.jsonc` L93–97 read — `instructions:` array = `[".gleipnir/AGENTS.md",
  ".gleipnir/stage-role-map.md"]`, confirming the every-session load. **No change needed.**
- `.gleipnir/agents/*.md` globbed — 9 agents confirmed; brief's list is stale by one
  (`session-scribe`). Correction routed into Decision 3.
- `session-scribe.md` read in full — confirms it owns/churns SESSION-STATE.md and
  must read it; drives the "except session-scribe" carve-out.
- `.gleipnir/goals/resume.md` read — confirms no contradiction (Decision 4).
- SESSION-STATE.md header read — confirms the Tier-0 / non-authoritative framing
  the new section must echo.

## Assemble (build order)

This is an operator-applied Tier-3 edit; "build order" = the exact application steps.

1. **Operator** opens `.gleipnir/AGENTS.md`.
2. **Operator** inserts the new `## Session resume` section (exact text below) at
   the location shown in the diff — after line 149 (end of `## What this scaffold
   does NOT include`) and before line 151 (`## Tooling notes`), preserving the
   single blank-line separators.
3. **Operator** saves. Change takes effect on the **next** session (instruction
   files load at session start).
4. No other file is touched. No build, no test, no commit gate specific to this
   change (operator may commit the doc edit via normal git-ops flow).

## EXACT ready-to-apply patch

### Insertion point (before/after context)

The new section is inserted at the boundary between the file's final two current
sections. Context lines below are verbatim from the verified file.

**BEFORE (current, lines 149–156):**

```markdown
`session-01-validation.md`, `session-02-*`).

## Tooling notes

Environment tool quirks that affect every agent — *not* framework policy or
guard semantics. Kept here because `.gleipnir/AGENTS.md` is the only file loaded
into every session (via `opencode.jsonc` `instructions:`), so a note here
reaches every agent without per-agent opt-in.
```

**AFTER (with new section inserted; the `## Tooling notes` block is unchanged,
only pushed down):**

```markdown
`session-01-validation.md`, `session-02-*`).

## Session resume

The framework keeps a single resume entry point at
`.gleipnir/plans/SESSION-STATE.md`. Kept here because `.gleipnir/AGENTS.md` is
the only file loaded into every session (via `opencode.jsonc` `instructions:`),
so a resume note here reaches the orchestrator without per-agent opt-in.

- **Orchestrator, at session start:** if `.gleipnir/plans/SESSION-STATE.md` is
  present and describes real prior work, read it first to pick up in-flight
  threads (open items, restart-gated changes, "next" actions) so a fresh session
  can resume without the operator pointing you there manually. If the file is
  absent, or contains only stale-example text with no real prior work (e.g. on a
  fresh clone), treat it as "no session to resume" and proceed normally — it is
  never a hard dependency.
- **It is a pointer, not authoritative.** SESSION-STATE.md is Tier-0, disposable,
  and by its own header **not authoritative**. Use it only to orient and find
  where in-flight work lives; the authoritative homes are `../decisions/`
  (durable decision records) and the spec (Part D E-seams). Never treat its
  contents as ground truth — follow its pointers to the authoritative sources
  before acting on anything material.
- **Subagents: skip this.** If you are a bounded subagent (`gleipnir-brainstorm`,
  `gleipnir-plan`, `gleipnir-code`, `quality-reviewer`, `git-ops`, `project-mgr`,
  `notify`), your delegation is authoritative for your task — you do **not** need
  to read SESSION-STATE.md. Work from the scoped delegation you were handed.
  Reading the resume file wastes context on state your bounded task does not
  need. (**Exception: `session-scribe`.** It *owns and churns* SESSION-STATE.md,
  so it reads the file to maintain it against current disk state — not to resume
  work. This is bookkeeping, not resume, and is expected.)

## Tooling notes

Environment tool quirks that affect every agent — *not* framework policy or
guard semantics. Kept here because `.gleipnir/AGENTS.md` is the only file loaded
into every session (via `opencode.jsonc` `instructions:`), so a note here
reaches every agent without per-agent opt-in.
```

**Unified-diff form (for `patch`/`git apply` — apply against the verified 168-line file):**

```diff
@@ -149,5 +149,34 @@
 `session-01-validation.md`, `session-02-*`).
 
+## Session resume
+
+The framework keeps a single resume entry point at
+`.gleipnir/plans/SESSION-STATE.md`. Kept here because `.gleipnir/AGENTS.md` is
+the only file loaded into every session (via `opencode.jsonc` `instructions:`),
+so a resume note here reaches the orchestrator without per-agent opt-in.
+
+- **Orchestrator, at session start:** if `.gleipnir/plans/SESSION-STATE.md` is
+  present and describes real prior work, read it first to pick up in-flight
+  threads (open items, restart-gated changes, "next" actions) so a fresh session
+  can resume without the operator pointing you there manually. If the file is
+  absent, or contains only stale-example text with no real prior work (e.g. on a
+  fresh clone), treat it as "no session to resume" and proceed normally — it is
+  never a hard dependency.
+- **It is a pointer, not authoritative.** SESSION-STATE.md is Tier-0, disposable,
+  and by its own header **not authoritative**. Use it only to orient and find
+  where in-flight work lives; the authoritative homes are `../decisions/`
+  (durable decision records) and the spec (Part D E-seams). Never treat its
+  contents as ground truth — follow its pointers to the authoritative sources
+  before acting on anything material.
+- **Subagents: skip this.** If you are a bounded subagent (`gleipnir-brainstorm`,
+  `gleipnir-plan`, `gleipnir-code`, `quality-reviewer`, `git-ops`, `project-mgr`,
+  `notify`), your delegation is authoritative for your task — you do **not** need
+  to read SESSION-STATE.md. Work from the scoped delegation you were handed.
+  Reading the resume file wastes context on state your bounded task does not
+  need. (**Exception: `session-scribe`.** It *owns and churns* SESSION-STATE.md,
+  so it reads the file to maintain it against current disk state — not to resume
+  work. This is bookkeeping, not resume, and is expected.)
+
 ## Tooling notes
 
 Environment tool quirks that affect every agent — *not* framework policy or
```

**Deviation from the brief's exact text (intentional, per Decision 3):** the
brief's "Subagents: skip this" bullet listed 7 names and omitted `session-scribe`.
This plan (a) keeps the accurate 7-name skip list, and (b) adds an explicit
`session-scribe` **exception** rather than a naive 8th list entry, because
`session-scribe` must read the file to maintain it. Everything else matches the
brief's converged prose verbatim.

## Stress-test (acceptance checks)

| # | Check | Method | Expected |
|---|-------|--------|----------|
| S1 | New `## Session resume` section present, placed immediately before `## Tooling notes`. | Read AGENTS.md after operator applies. | Section exists between `## What this scaffold does NOT include` and `## Tooling notes`. |
| S2 | No existing AGENTS.md content already claims SESSION-STATE.md is read automatically or contradicts the new instruction. | Grep AGENTS.md for `SESSION-STATE`, `resume`, `session start`. | **Confirmed this session: zero prior mentions of SESSION-STATE.md, "resume", or automatic session-start reads anywhere in the current 168-line AGENTS.md.** No contradiction possible; the new section introduces the concept for the first time. |
| S3 | `## Tooling notes` scope boundary respected (env quirks, not process). | Read: new section is separate, not a `## Tooling notes` bullet. | Process guidance lives in its own section; `## Tooling notes` unchanged. |
| S4 | No contradiction with `goals/resume.md`. | Compare both. | Consistent: both point at SESSION-STATE.md and both label it Tier-0 non-authoritative. AGENTS.md = always-loaded nudge; `goals/resume.md` = "check goals first" reference. `goals/resume.md` currently says "read … to orient" generically (all sessions); the new AGENTS.md section refines *who* (orchestrator resumes; subagents skip). This is a refinement, not a contradiction — but note it as a **follow-up** (see below) if the operator wants the goal's wording aligned. |
| S5 | The "subagents skip" list is accurate against the live roster. | Compare to `glob *.md .gleipnir/agents`. | 8 subagents named/accounted for: 7 in the skip list + `session-scribe` as an explicit exception; `orchestrator` is the addressee, not a subagent. No roster member unaccounted for. |
| S6 | `session-scribe` is NOT told to skip reading the file it owns. | Read the exception clause. | Exception clause present and correct. |
| S7 | Graceful degradation preserved. | Read orchestrator bullet. | "absent / stale-example → no session to resume, proceed normally; never a hard dependency." |
| S8 | No code/test/config change. | `git status` after edit. | Only `.gleipnir/AGENTS.md` modified (plus this plan file). No `src/`, `tests/`, `opencode.jsonc`, or agent-frontmatter change. |

## Follow-ups (out of scope — flagged, not folded in)

These are Tier-3 items the operator may address separately; this plan does NOT
resolve them (they are not material to the converged decision, and folding them
in would exceed the bounded change):

1. **AGENTS.md roster count is stale.** Line 30 says "8-role roster" and the
   `## Roster` / "Tier-0 writers" prose (L77–102) predates `session-scribe`
   (the 9th agent) and does not mention it. This plan does not touch that prose.
   Recommend a separate operator edit to reconcile the roster count/description
   with the 9-agent reality.
2. **`goals/resume.md` wording** currently addresses "any session" generically
   (S4). If the operator wants the who-scoping (orchestrator resumes; subagents
   skip) reflected there too, that is a separate Tier-3 edit. Not required —
   the two files are already non-contradictory.

## Execution Workflow

**This is an operator-applied Tier-3 documentation change. No roster agent can
apply it.** Sequence:

1. **spec-review** (`quality-reviewer`): validate this plan against the brief and
   `plan-format.md` — in particular confirm the Decision-3 roster correction is
   sound (that `session-scribe` genuinely owns SESSION-STATE.md and must not be
   told to skip it) and that the diff context lines match the current file.
2. **Operator applies the patch** to `.gleipnir/AGENTS.md` (the exact text /
   unified diff above). There is no `code` or `test` stage — nothing to
   implement or test; it is inert prose.
3. **Verify (operator, or `quality-reviewer` read-only):** run Stress-test
   S1–S8 against the edited file.
4. **git** (`git-ops`): commit the doc change (`.gleipnir/AGENTS.md`) via the
   normal broker flow if desired.
5. Change is live on the **next** session start (instruction files load then).

No engine sequencing, no G-3 attestation, no build. The plan's deliverable —
the exact patch — is complete and self-contained above.
