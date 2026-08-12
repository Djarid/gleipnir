# Design Brief: Startup instruction to read SESSION-STATE.md for cross-session resume

## Problem Statement

A fresh session (specifically a fresh **orchestrator**) does not know to check
`.gleipnir/plans/SESSION-STATE.md`, so prior in-flight work cannot be resumed
without the operator manually pointing the session at it every time. This gap
was found live this session: nothing in the always-loaded instruction context
tells the orchestrator that a resume entry point exists. The fix is to add a
startup instruction to `.gleipnir/AGENTS.md` (the only file loaded into every
session via `opencode.jsonc`'s `instructions:` key) so resume becomes
automatic — without imposing that cost on the bounded subagents that don't need
it.

## Constraints

- **`.gleipnir/AGENTS.md` is Tier-3 (POLICY), operator-authored only (G-1).**
  This brief cannot write the file. It must contain the *exact, ready-to-apply*
  prose for the operator to paste in themselves.
- **`opencode.jsonc` `instructions:` loads AGENTS.md into EVERY agent session**
  — primary (orchestrator) *and* all 7 bounded subagents — unconditionally. There
  is no opencode mechanism to scope one instruction-file line to a single role;
  scoping is achievable only in the *prose* (address the orchestrator; tell
  subagents to skip). Confirmed: `opencode.jsonc` lines 93–97,
  `["`.gleipnir/AGENTS.md`", "`.gleipnir/stage-role-map.md`"]`.
- **Token-efficiency is the framework's stated goal** (`AGENTS.md` "Goal
  reminder"; the G-4d cost-per-outcome ledger is the scoreboard). SESSION-STATE.md
  is ~278 lines (~2000+ tokens); nudging every subagent to read it each session
  wastes context for roles whose delegations are already scoped.
- **SESSION-STATE.md is explicitly NOT authoritative** (its own header: Tier-0,
  disposable; authoritative homes are `../decisions/` and the spec). The
  instruction must not cause over-trust of it — it is a *pointer*, not truth.
- **Must degrade gracefully.** On a fresh clone / first-ever session, the file
  may be absent or contain only stale-example text with no real prior work. The
  instruction must not create a hard dependency or failure in that case.
- **Placement precedent:** `## Tooling notes` already exists in AGENTS.md for the
  same "every session needs this" reason — but it is explicitly scoped to
  environment/tool quirks, *not* framework process guidance. A resume instruction
  is process guidance, so it warrants its own section.

## Approaches Considered

### Approach A: Address the orchestrator only (prose-scoped) — NOT SELECTED

**Summary:** The instruction text is addressed to the orchestrator ("The
orchestrator, at session start, should check SESSION-STATE.md…"); subagents read
the same line but, seeing it addressed to a role they aren't, skip it.

**Tradeoffs:**
- Pro: Matches reality — only the orchestrator sequences/resumes work across
  sessions; subagents receive scoped delegations already.
- Pro: Honours the token-efficiency goal — doesn't nudge bounded roles to read a
  ~2000-token file irrelevant to their task.
- Pro: Aligns with the roster's deny-by-default / least-context ethos.
- Con: The text still loads into every session (unavoidable at the opencode
  layer); relies on subagents *self-selecting out* — weakly self-enforcing, a
  subagent could misread the scoping and read the file anyway.

**Estimated Scope:** One new prose section in `.gleipnir/AGENTS.md`.

**Risk:** Low.

**Why not selected:** Sound, but leaves the "text loads everywhere" fact as a
passive hope that subagents skip. Option C converts that same fact into an
*active* skip instruction at negligible extra cost — strictly better on the
token-efficiency axis the operator asked to weigh.

### Approach B: Address every agent ("every session, read SESSION-STATE.md") — NOT SELECTED

**Summary:** A single unscoped instruction telling every session to read the
file at startup.

**Tradeoffs:**
- Pro: Simplest wording; zero ambiguity about who.
- Pro: Fully future-proof if any subagent ever needs resume context.
- Con: Directly nudges 7 bounded subagents to each read a ~2000-token file their
  scoped delegation doesn't need — a recurring per-session, per-subagent token
  cost, against the framework's explicit goal.
- Con: Risks subagents over-trusting a **non-authoritative** file and acting on
  stale global state instead of their scoped delegation — a
  context-poisoning-adjacent smell for roles meant to be narrow.

**Estimated Scope:** One new prose section in `.gleipnir/AGENTS.md`.

**Risk:** Low mechanically; medium against the token-efficiency goal.

**Why not selected:** The only real fix for both of its cons is to *become
Option A* (scope it). It solves a completeness problem that does not exist
today — no roster subagent resumes cross-session state — at a real, recurring
token cost.

### Approach C: Orchestrator addressed directly, PLUS an explicit "subagents skip this" line — SELECTED

**Summary:** Everything in Approach A, plus one line that explicitly tells
subagents their scoped delegation is authoritative and they do not need to read
SESSION-STATE.md — converting the unavoidable "AGENTS.md loads into every
session" fact into an *active* token-saving instruction rather than a passive
hope.

**Tradeoffs:**
- Pro: All of Approach A's alignment (matches reality, honours the goal, fits
  the deny-by-default ethos).
- Pro: Turns "text loads everywhere" from a con into an explicit skip
  instruction — actively saves the tokens instead of hoping subagents
  self-select out.
- Pro: Reinforces the scoped-delegation model already stated in
  `stage-role-map.md` ("one verb, object, verification per delegation").
- Con: Marginally more verbose (two sentences vs one).

**Estimated Scope:** One new top-level `## Session resume` section in
`.gleipnir/AGENTS.md` (operator-applied; agent-unwritable).

**Risk:** Low.

## Decision Analysis

**Framework used:** Reversibility Filter → Pros-Cons-Fixes. The auto-selection
table routes a binary/multi-option scoping choice through the Reversibility
Filter first, then Pros-Cons-Fixes for the A/B/C evaluation. Selected because
Q1 (who the instruction addresses) is the sole material tradeoff — Q2/Q3/Q4 have
clear paths determined by graceful-degradation, the file's own disclaimer, and
existing placement precedent respectively.

**Reversibility:** **Two-Way Door.** Reversal cost is minutes — it is prose in
an instruction file, easily reworded next session. Reversal cost: re-edit one
section of `.gleipnir/AGENTS.md`. Normally a Two-Way Door fast-tracks; the
operator explicitly asked to weigh the token-cost angle, so Pros-Cons-Fixes was
run on the three viable scopings rather than fast-tracking.

**Analysis results (Pros-Cons-Fixes, per option):**

*Option A — orchestrator only (prose-scoped):*

| Con | Fix |
|-----|-----|
| Text loads into every session regardless | Word it as an explicit role-scoped instruction ("orchestrator: …"), matching how AGENTS.md already addresses roles; subagents self-select out |
| A resuming subagent isn't told | No roster subagent resumes cross-session state today; delegations are scoped. Revisit if a role gains that responsibility |

Post-fix verdict: **Viable** — best-aligned with the token-efficiency goal.

*Option B — every agent:*

| Con | Fix |
|-----|-----|
| Token cost across all subagents | Cannot fix without scoping — the fix *is* Option A |
| Over-trust of non-authoritative file | Add "pointer, not authoritative" caveat — but this does not remove the token cost |

Post-fix verdict: **Marginal** — the only real fix for its cons is to become
Option A.

*Option C — orchestrator + explicit "subagents skip" line:*

| Con | Fix |
|-----|-----|
| Marginally more verbose | Accept — two sentences; the added sentence *is* the token-saving mechanism |

Post-fix verdict: **Viable** — strongest completeness, marginally more text;
converts A's residual con into an active instruction.

**Bias warnings:**
- ⚠️ **Status Quo Bias (low):** The `## Tooling notes` precedent makes "just add
  another bullet there, addressed to everyone" the path of least resistance.
  Flagged so the scoping question got real scrutiny rather than defaulting to
  "tell everyone." (The operator's own framing already guarded against this.)
- ⚠️ **Scope Creep Bias (low):** Option B's completeness largely solves a
  problem that does not exist today (no subagent resumes cross-session);
  flagged to avoid expanding this into "make every agent resume-aware."
- Remaining 10 detectors (Anchoring, Confirmation, Sunk Cost, Availability,
  Bandwagon, Dunning-Kruger, IKEA, Survivorship, Recency, Authority): not
  triggered — the options were weighed independently.

**Recommendation:** **Option C**, narrowly over A. Both A and C match the
token-efficiency goal and the reality that only the orchestrator resumes work; C
additionally turns the unavoidable "text loads into every session" fact into an
explicit "subagents, skip this" instruction, actively saving the tokens. B is
not recommended — its only cure for its own cons is to collapse into A.

**Operator convergence:** The operator selected **Option C**, with placement as
a **new top-level `## Session resume` section** (not folded into `## Tooling
notes`, which is scoped to environment/tool quirks, not framework process
guidance). This recommendation was advisory input; the operator decided.

## Selected Approach

**Choice:** Approach C — orchestrator addressed directly to check SESSION-STATE.md
at session start, PLUS an explicit line telling subagents their delegation is
authoritative and they do not need to read it. **Placement:** a new top-level
`## Session resume` section in `.gleipnir/AGENTS.md`.

**Rationale:** Only the orchestrator resumes work across sessions, so it is the
right (and only) role to address. Because `opencode.jsonc` `instructions:` loads
AGENTS.md into every session unconditionally, the "subagents skip this" line
converts an unavoidable token cost into an active saving — strictly better than
Approach A's passive hope, and avoiding Approach B's recurring per-subagent
waste and over-trust risk. The new section (rather than a `## Tooling notes`
bullet) respects that section's explicit scope boundary (tool quirks, not
process). The sub-answers below are folded in as decided:

- **Missing/stale file (Q2):** phrased conditionally ("if present") — degrades
  gracefully on a fresh clone with no real prior work recorded.
- **Wording strength (Q3):** soft-but-clear; SESSION-STATE.md explicitly labelled
  a **pointer, not authoritative**, echoing its own header (authoritative homes
  are `../decisions/` and the spec).

### EXACT proposed text for the operator to paste into `.gleipnir/AGENTS.md`

Add as a new top-level section (suggested placement: immediately before the
existing `## Tooling notes` section, so process guidance precedes environment
quirks). Tone/format modelled on the existing `## Tooling notes` section.

```markdown
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
- **Subagents: skip this.** If you are a bounded subagent (e.g.
  `gleipnir-brainstorm`, `gleipnir-plan`, `gleipnir-code`, `quality-reviewer`,
  `git-ops`, `project-mgr`, `notify`), your delegation is authoritative for your
  task — you do **not** need to read SESSION-STATE.md. Work from the scoped
  delegation you were handed. Reading the resume file wastes context on state
  your bounded task does not need.
```

## Open Questions

- **None material for planning.** The decision is converged and the exact prose
  is ready to apply.
- Minor, for the operator's own judgment (not blocking): exact placement of the
  new section within AGENTS.md (proposed: immediately before `## Tooling notes`).
  The section content is placement-independent.
- Future revisit (not now): if any roster subagent ever gains a genuine
  cross-session resume responsibility, the "subagents skip this" line must be
  narrowed to exclude that role. No such role exists today.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Instruction context (Tier-3, operator-applied) | `.gleipnir/AGENTS.md` — add new `## Session resume` section (exact prose above). **Agent-unwritable; operator pastes it in.** |
| Verification (no code) | None — prose-only change. Optional: a consistency glance that the new section's role list matches the current roster in `agents/`. |
| No other files | No `opencode.jsonc` change (the `instructions:` wiring already loads AGENTS.md everywhere); no subagent frontmatter change; no plans/ policy change. |
