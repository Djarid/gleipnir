# Plan: Tier-0→Tier-2 lesson-candidate escalation process (Approach A-hybrid)

> **Status: planned (full ATLAS), awaiting spec-review then operator application.**
> Written by `gleipnir-plan` (Tier-0 writer) FROM the operator-converged brief
> `lesson-escalation-process-brainstorm.md` (Approach A-hybrid). This plan does
> **not** re-decide any converged choice: the *mechanism* (Option A grant) is
> fixed by `tier2-escalation-control-proposal.md`; the *process* (A-hybrid,
> immediate-by-default with opportunistic coalescing, uncapped, full discard on
> reject, lightweight footer + session id) is fixed by the brief. Planning here
> resolves only the **bounded** Open Questions the brief handed to
> `gleipnir-plan` (coalescing-window definition, batch `question` shape, L-C
> numbering, delegation granularity, footer placement/source) — none of which is
> a material tradeoff.

## GOTCHA pre-flight (recorded)

- **Goals:** `goals/manifest.md` → `plan-format.md` binds this file's structure
  (Architect/Trace/Link/Assemble/Stress-test/Execution Workflow). Plan-before-code
  order preserved: this is the `plan` stage running from a converged brief.
- **Layering:** Goals = durable lesson discipline without a build-mode round-trip.
  Orchestration = orchestrator sequences propose→(coalesce)→confirm→delegate→verify.
  Tools = `question` (orchestrator-only channel, L-C6) + session-scribe's scoped
  append. Context = the file's strict format + the four fixed sub-positions.
  Hard prompts = standing prose in the two Tier-3 files. Args = the exact YAML
  diff + the footer format. Q2 (timeout out-of-scope) is grounded in `question`'s
  actual tool semantics — a blocking state with no timer / no outgoing edge until
  answered (a directly-observed tool property; see also orchestrator.md's
  compaction-survival item 5 on gated states) — not any citation.
- **Capability:** all writes are Tier-0 plan files (this file + the supersession
  note on the proposal). The two Tier-3 agent edits are authored here as text for
  the **operator** to apply; `gleipnir-plan` does not and cannot write them.

---

## Architect

**Problem (one sentence).** A lesson candidate must be proposable, human-confirmed,
appended to `.gleipnir/lessons/session-lessons-candidates.md`, and verified on
disk — all without an expensive build-mode escape-hatch round-trip — while every
rejected draft leaves zero trace.

**User.**
- **The operator** — who today pays a full mode-switch to record authority-free
  advisory text (observed: L-C1…L-C13 each cost a round-trip), and who wants the
  interrupt cadence kept low (the coalescing refinement).
- **The orchestrator's own future self** — needs a *durable, standing* discipline
  so that "notice a lesson → propose it through the gate" is a bound behaviour, not
  a per-session habit that drifts. **Durability requires a `compaction_survival:`
  frontmatter bullet**, not just body prose: the compaction-survival plugin
  (`.gleipnir/plugins/compaction-survival.ts`, lines 66–81) re-injects **only** the
  exact strings in each agent's `compaction_survival:` YAML array — it never
  re-injects arbitrary body sections. So the escalation obligation survives
  compaction *iff* Trace §(b) adds a frontmatter bullet (it does — see §(b)); the
  body section alone would be summarised away. The recurring failure this closes:
  the orchestrator *mentioning* a lesson in passing and never acting on it.

**Measurable success criteria.**
1. A lesson can be **proposed + operator-confirmed + appended as `L-C<n>`** entirely
   inside a normal orchestrator turn — no build-mode switch, no operator hand-edit
   of the file.
2. A **rejected** draft leaves **no trace anywhere** — no ledger, no Tier-0 scratch,
   no partial write (full discard, Q5).
3. The append is **verified against disk** by session-scribe (read-back confirms the
   entry landed, sequential numbering correct, tombstone section untouched, nothing
   else altered) — never a fabricated "done" (L-C4/L-C8).
4. Every appended entry carries the **lightweight footer + session id** (date;
   `reviewed_by: operator (via question, this session)`; substitution note; session
   id) — honest that this substitutes for the not-yet-built G-4c reviewer.
5. **Coalescing is bounded and non-drifting**: multiple observations noticed together
   in a *single, uninterrupted orchestrator turn* may become one `question`; nothing
   is ever held pending across a turn or a compaction boundary.
6. **Confirmed text is used verbatim** — the appended entry (and any operator edit)
   is the exact confirmed text, never a paraphrase.

**Constraints (inherited from the brief; not re-opened).**
- Mechanism fixed: Option A (session-scribe → one named file; orchestrator
  `question` gate). Do not touch the *who-can-write* decision.
- `question` reaches the operator **only** from the orchestrator (L-C6). All
  confirmation lives at the orchestrator; session-scribe holds no `question`.
- `question` is a blocking state with **no timer / no outgoing edge until answered**
  (a directly-observed `question` tool property; cf. orchestrator.md compaction-survival
  item 5 on gated states) → "no response" cannot silently produce a write.
- session-scribe is **inert without an explicit orchestrator delegation** (no
  `question`/`task`/`bash`/git; 15 steps; Haiku; temp 0).
- File format strict: title / **Observed** / **Proposed lesson**; sequential
  `L-C<n>`; entries inserted **before** the `## Note on placement` tombstone.
- Honesty posture structural: entries are self-labeled CANDIDATE / pre-graduation.
- No throwaway machinery ahead of G-4c (no rejection ledger, no accumulation file,
  no richer-provenance schema).
- Two-Way Door with behavioural stickiness: reversal is prose-only.

---

## Trace

Three artifacts. (a) and (b) are **Tier-3, operator-applied**; (c) is a convention
documented inside (b) and materialised at append time.

### (a) `session-scribe.md` grant extension — REUSED verbatim from the proposal

Source of truth: `tier2-escalation-control-proposal.md` §"Proposed artifact". Do
**not** re-derive — this is the converged mechanism. The exact YAML diff (adds
**one named file** to both `edit` and `write`; explicitly NOT a `lessons/**` glob):

```yaml
  edit:
    "*": deny
    ".gleipnir/plans/**": allow
    ".gleipnir/var/tmp/**": allow
    ".gleipnir/lessons/session-lessons-candidates.md": allow   # ADDED
  write:
    "*": deny
    ".gleipnir/plans/**": allow
    ".gleipnir/var/tmp/**": allow
    ".gleipnir/lessons/session-lessons-candidates.md": allow   # ADDED
```

Accompanying prose edits in the **same** operator edit (from the proposal):
- Update the `description` frontmatter (currently asserts "never any Tier-2
  (memory/, lessons/) … path") to name this **single-file** Tier-2 exception.
- Amend the "Capability boundary" section (session-scribe.md lines 44–55) to carve
  out this ONE file as an explicit, human-gated exception: session-scribe still
  refuses every other Tier-2/Tier-3 path, and writes this file **only** on an
  explicit orchestrator delegation carrying operator-confirmed text.
- After applying, recompute the `keys/` digest for `session-scribe.md` (standard
  Tier-3 edit hygiene, so S-3 preflight will not quarantine the changed file once
  digests are wired).

### (b) `orchestrator.md` — new standing discipline section (A-hybrid) + a frontmatter `compaction_survival:` bullet

**Two coupled changes, applied in the SAME Tier-3 edit pass** (not a follow-up):

**(b.1) A new `compaction_survival:` frontmatter bullet.** The body section below
is summarised away on compaction unless the obligation is *also* pinned as a
frontmatter array item — the plugin (`compaction-survival.ts` lines 66–81) re-injects
only the `compaction_survival:` strings. Add this one bullet to `orchestrator.md`'s
existing `compaction_survival:` array (currently 6 bullets, lines 20–26), condensed
to match their style/length (cf. how bullet 2 condenses the convergence-gate rule):

```yaml
  - "When you notice a process/reliability observation worth a durable lesson, PROPOSE it via `question` immediately (or coalesced with others noticed in the SAME turn) — do not just mention it in passing and move on. A noticed-but-unproposed lesson is a planning failure, not a completed observation. Never hold a candidate pending across a turn or compaction; one confirmed lesson = one session-scribe append, verified against disk."
```

This must be added in the **same** operator edit as the body section (b.2) — it is
not a separate later step. It is the durability guarantee the Architect relies on.

**(b.2) A new body section** parallel to the existing "You are the human's only
reachable channel (the convergence gate)" section (orchestrator.md lines 80–96),
written as standing instructions. **It must not contradict that section** — it
*reuses* the same `question`-is-orchestrator-only fact. Proposed prose for the
operator to apply:

> ## Lesson-candidate escalation (A-hybrid; standing discipline)
>
> When you (or a subagent's report) surface a process/reliability observation worth
> a durable lesson, you **act on it** through this gate — you do not merely mention
> it in passing. This is the interim path until the G-4c review-gated pipeline
> exists; the `question` confirmation below substitutes for that pipeline's
> deterministic Review step, and the footer for its audit event. Both substitutions
> are explicit and honest — the entry never claims to be a graduated lesson.
>
> 1. **Notice → draft.** Draft the candidate in the file's exact format (title /
>    **Observed** / **Proposed lesson**). Read the file first to get the current
>    highest `L-C<n>` (assign numbers at **draft** time from that read).
> 2. **Coalescing rule (bounded, non-drifting).** If **several** candidates are
>    noticed **together within this same single, uninterrupted turn/response**, you
>    MAY present them in **one** `question`. A **lone** observation is presented
>    **immediately** (immediate-by-default). You **never hold a candidate pending**
>    across turns or across a compaction boundary: a candidate noticed in a *later*
>    turn is proposed immediately in that turn, never queued to join an earlier one.
>    (This is deliberately narrower than the rejected Approach-B "checkpoint": no
>    state is carried across a checkpoint, so there is no compaction-loss hazard.)
> 3. **Present (verbatim).** Call `question` showing the **FULL VERBATIM** drafted
>    text — never a summary/paraphrase — with options **Approve as-is / Edit /
>    Reject**. When coalescing, present the batch as one `question` with a clear
>    per-item Approve / Edit / Reject for each; an edit or reject applies to **that
>    item only**.
> 4. **Confirm (2-round cap).** Approve-as-is → use that exact text. Edit → fold in
>    the operator's **exact wording** (never paraphrased) and re-confirm; capped at
>    **2 rounds total** per item (mirrors the framework's loop-cap discipline; when
>    the cap is hit, stop and re-`question`, do not loop past it). Reject → discard
>    that item; **nothing is written for it, no record kept** (full discard).
> 5. **Provenance stamp.** Append the lightweight footer (format in the convention
>    below) to each confirmed entry, including this session's id.
> 6. **Delegate (one delegation per confirmed item).** Hand `session-scribe` the
>    **EXACT confirmed text incl. footer** and the target: append immediately
>    **before** the `## Note on placement` tombstone. **One confirmed lesson = one
>    session-scribe delegation** (one verb/object/verification/boundary,
>    S-1.3.1). For a coalesced batch of N, emit N sequential single-entry
>    delegations, re-reading the current highest `L-C<n>` before each so numbering
>    stays correct even if reads interleave — never a single multi-entry append.
> 7. **Verify.** session-scribe reads the file back and confirms the entry landed,
>    the number is sequential, the tombstone is untouched, and nothing else changed.
>    You verify session-scribe's report against disk expectation (L-C4).
> 8. **Report.** Confirm to the operator: recorded as `L-C<n>`.
>
> Uncapped: there is no limit on proposals per session — the per-use `question` is
> itself the noise-brake. Timeout is out of scope: `question` simply blocks with no
> timer, so an absent operator means the append never happens (the correct
> fail-safe), never a silent unreviewed write.

**Consistency with the existing convergence-gate section:** both rest on the same
invariant — *only the orchestrator can `question` the operator*. The escalation
section is a **specific application** of the general gate, not a competing rule; it
adds no new channel and overrides nothing. (Link validates this explicitly.) The
new frontmatter bullet (b.1) is likewise consistent with the existing 6: it neither
duplicates nor contradicts them, and its "never hold pending across a turn or
compaction" clause reinforces (does not weaken) bullet 6's session-recovery rule.

### (c) Footer / provenance format (the convention; materialised at append time)

Appended **inside** each entry, after the **Proposed lesson** paragraph, before the
next entry / the tombstone. Lightweight + session id (Q4), honest substitution note:

```
_Provenance: reviewed_by operator (via question, this session) · date <YYYY-MM-DD> ·
session <session-id> · interim gate — substitutes for the not-yet-built G-4c
deterministic reviewer; this is CANDIDATE text, not a graduated lesson._
```

- **session-id source:** the orchestrator stamps the same session id it already
  uses for `SESSION-STATE.md` (`_… · session <id> · churned by session-scribe_`,
  session-scribe.md line 75). No new id machinery — reuse the existing session id.
  If no stable id is available in a given run, stamp `session unknown` rather than
  fabricate one (honesty > completeness).
- The footer is **one token's worth** of richness beyond pure Approach A — no
  triggering-source, no task id (those risk re-shaping when G-4c lands).
- **Entry separator (`---`) convention — unambiguous instruction for session-scribe.**
  The target file is mixed: L-C1–L-C10 have **no** `---` rule between entries, but
  L-C11 onward each sit between `---` rules (the more recent convention). The **new
  L-C14 entry MUST use the `---`-separated format** — i.e. it is inserted as a
  `---`-delimited block, matching L-C11–L-C13, and placed immediately before the
  `## Note on placement` tombstone (which is itself already preceded by a `---`).
  The delegation to session-scribe must state this explicitly so the append is
  unambiguous, not left to infer from the file's inconsistent older entries.

### Edge cases (Trace)

- **Interleaved appends / stale highest-number read.** Guarded by (b) step 6:
  one single-entry delegation at a time, re-reading the highest `L-C<n>` before
  each. No concurrent multi-entry append that could double-assign a number.
- **Operator edits one item in a coalesced batch.** Only that item re-confirms
  (step 3/4); the others are unaffected — the 2-round cap is **per item**.
- **Partial batch outcome.** In a coalesced batch, some items approved, some
  rejected → approved items each get their own delegation + number; rejected items
  vanish with no trace. Numbers are assigned only to survivors, in confirmation order.
- **session-scribe read-back shows a mismatch.** session-scribe reports the mismatch
  (does not retry blindly, does not fabricate success — L-C8); the orchestrator
  re-drafts/re-delegates. No silent correction.
- **Tombstone drift.** If the `## Note on placement` section is ever renamed, the
  delegation's "insert before the tombstone" instruction must name the current
  heading; session-scribe verifies the tombstone is intact post-write.
- **Acknowledged residual risk — mid-turn compaction before a draft is presented.**
  The "within a single uninterrupted turn" bound does **not** fully close one soft
  edge: a long orchestrator turn (`steps: 40`, spanning many delegations) could hit
  the 250K context-cap compaction trigger *after* a candidate is drafted internally
  but *before* it is shown to the operator via `question`. If that draft lived only
  in volatile turn context, it could be lost in the compaction (the "immediate-by-
  default" rule shrinks but does not eliminate this window). This is named plainly
  as an **acknowledged soft edge**, mirroring the brief's own honesty that "same
  short window" is a judgment call — **not** a solved problem and **not** to be
  over-engineered here. The failure is fail-safe (a lost draft = a lesson not
  recorded = the correct "no unreviewed write"), and the frontmatter bullet (b.1)
  makes the *obligation* survive compaction even if a specific in-flight draft does
  not, so the orchestrator re-notices and re-proposes. No fix is added; the residual
  is accepted.

---

## Link (validate before this is "live")

Prerequisite checks, in order, before the process is treated as active:

1. **Grant is exactly one file, not a glob.** After the operator applies (a),
   confirm `session-scribe.md` `edit`/`write` maps contain the literal
   `.gleipnir/lessons/session-lessons-candidates.md` — **not** `.gleipnir/lessons/**`,
   **not** `session-lessons-candidates.md` without the path, **not** a trailing
   `/*`, **not** `README.md` or any other lessons file, **not** `memory/**`. A
   typo'd glob would silently over-grant (the exact Scope-Creep risk the proposal's
   bias check flagged). Read the applied file and eyeball both maps.
2. **Digest recomputed.** Confirm the `keys/` digest for `session-scribe.md` was
   recomputed after the edit (else S-3 preflight would quarantine it once digests
   are wired — Pre-Mortem failure #4 in the proposal).
3. **No contradiction with the convergence-gate section.** Read the applied
   `orchestrator.md`: the new escalation section must (a) not introduce a second
   operator channel, (b) not weaken "subagents cannot reach the operator" (L-C6),
   (c) not conflict with the compaction-survival Critical Guardrails (the
   `question`-is-orchestrator-only and loop-cap rules) — the 2-round cap here is
   an *instance* of the existing "honour loop caps" rule, consistent by design.
4. **Format anchor present.** Confirm the target file still ends with the
   `## Note on placement` tombstone (the insertion anchor) and that L-C13 is the
   current highest number (so the first new entry is L-C14).
5. **session-id availability.** Confirm the orchestrator has a stable session id to
   stamp (the same one used for `SESSION-STATE.md`); if not, the `session unknown`
   fallback (Trace (c)) applies — not a blocker, just a known degradation.

---

## Assemble (build order)

There is no source code — only Tier-3 config/prose + a first real-use test. Order:

1. **[done] Supersession note** — prepend "SUPERSEDED — see
   `lesson-escalation-process-brainstorm.md`" to the 8-step section (and Handoff
   step 2) of `tier2-escalation-control-proposal.md`. **Completed by `gleipnir-plan`
   in this planning turn** (Tier-0 write, in-bounds). No operator action.
2. **spec-review** (`quality-reviewer`) — review THIS plan against the brief:
   confirm no converged choice was re-decided, the coalescing definition is
   bounded/non-drifting, the two Tier-3 edit texts are faithful to their sources
   (proposal §Proposed artifact for (a); brief for (b)), and Link checks are sound.
3. **[operator, Tier-3] Apply (a)** — the session-scribe grant extension + prose +
   digest recompute. Then run Link checks 1–2.
4. **[operator, Tier-3] Apply (b)** — the orchestrator escalation-discipline
   section, in the same build session as (3). Then run Link check 3.
5. **Live-use verification (the "test")** — propose **ONE real lesson** through the
   full A-hybrid flow (see below) and run the Stress-test checks against the result.
6. Run Link checks 4–5 as part of step 5's first real append.

**Steps (3) and (4) are the only Tier-3 edits and are operator-applied.** The only
**bounded-agent** action in the whole feature is session-scribe's actual
append-on-delegation in step 5 (Execution Workflow spells the split out).

### First real lesson to propose (step 5)

A genuine, non-synthetic candidate exists and is ideal for the first real use:
**"Plan-stage supersession must be explicit — a self-designed process left standing
looks authoritative."** (Observed: this very feature; the orchestrator's 8-step
sketch sat in a converged proposal file reading as authoritative until a
methodology-run brief + plan superseded it, and the supersession had to be written
explicitly rather than assumed.) It would be drafted as `L-C14`, presented verbatim
via `question`, and — if the operator approves/edits — appended with the footer. If
the operator prefers a different first lesson, any real observation works; the point
of step 5 is to exercise the *flow*, not to mandate this specific text.

---

## Stress-test (acceptance checks)

Concrete, checkable — these fixtures ARE the "test" for a config/prose feature
(there is no unit-testable code). Each must pass on a real run:

1. **Immediate case (1 observation → 1 question).** A lone candidate fires exactly
   **one** `question` immediately; not queued, not batched.
2. **Coalescing case (2 observations in one turn → 1 question).** Two candidates
   noticed together in the same uninterrupted turn are presented as **one**
   `question` with per-item options — **not** two separate `question` calls.
3. **No cross-turn queuing.** A candidate noticed in a *later* turn is proposed
   immediately in that turn — verify it is **not** held to join an earlier one, and
   that nothing was carried across the turn/compaction boundary (no pending state).
4. **Rejection → zero trace.** Reject a drafted candidate; verify **nothing** is
   written to the candidate file, to `plans/`, to `var/tmp/`, or anywhere — grep
   confirms no residue, no orphan number consumed.
5. **Edit-then-approve uses verbatim text.** Request an edit; verify the appended
   entry contains the operator's **exact** wording, not a paraphrase, and that only
   the edited item re-confirmed (others in a batch unaffected).
6. **2-round cap honoured.** Verify a third edit round does not silently loop — it
   stops and re-`question`s (or escalates), never loops past the cap.
7. **Footer present and correct.** The real append carries the footer with: today's
   date, `reviewed_by operator (via question, this session)`, the substitution note,
   and the session id (or `session unknown` if none) — placed after **Proposed
   lesson**, before the next entry/tombstone.
8. **Read-back verification real.** session-scribe's report shows it re-read the file
   and confirms: entry present, number sequential (first new = `L-C14`), tombstone
   intact, nothing else changed (L-C4/L-C8) — not a fabricated "done."
9. **Sequential numbering under coalescing.** A coalesced batch of 2 approved items
   yields consecutive `L-C<n>`/`L-C<n+1>` with no gap and no collision, each from a
   fresh highest-number read.
10. **Grant scope (from Link 1).** The applied session-scribe grant matches the one
    named file exactly — a negative check that a `lessons/**` glob is NOT present.
11. **Uncapped is actually shipped (static check, not live-use).** Read the applied
    `orchestrator.md` escalation section (b.2) and frontmatter bullet (b.1) and
    confirm they contain **no** per-session limit / counter / "max N proposals"
    logic — a negative check proving "uncapped" (Q3) is the shipped behaviour, not
    merely a claim in this plan. (The only cap present is the per-item **2-round
    edit** cap, which is not a session proposal cap.)

---

## Execution Workflow (operator-vs-agent split)

Enough for an implementing actor to act without rediscovering the protocol.

**Pipeline for this feature (no code/test/quality stages in the usual sense):**

    brainstorm  -> plan -> spec-review -> [operator applies Tier-3 edits] -> live-use verification
    (done)      (this)   (quality-       (steps 3–4 of Assemble)          (step 5; Stress-test
                          reviewer)                                         fixtures ARE the test)

**Why no `code`/`test`/`quality` in the usual sense.** There is **no source code** —
only Tier-3 config (the YAML grant) and standing prose (the orchestrator section) +
a convention (the footer). The stage-role-map's `test`/`code`/`quality` stages
presuppose an executable artifact and a test arbiter; here the **Stress-test
fixtures are the lightweight equivalent of the test** (run once, live, in step 5),
and `spec-review` (a real bound stage) plays the quality role by checking this plan
and the two edit texts against their sources. This is the honest lighter-weight
mapping, not a skipped stage.

**Follow-on recommendation (precedent, do NOT self-decide here).** This
stage-mapping — skipping `test`/`code`/`git`/`gate` and letting `quality-reviewer`
serve both `spec-review` and the quality role for a prose/config-only feature — is
a reasonable and transparent interpretation, but it is **precedent-setting**: every
future prose-only or config-only plan will face the same question, and it should not
be re-decided ad hoc per plan. **Recommend the operator/orchestrator eventually
ratify a standing rule in `stage-role-map.md`** (a documented "prose/config-only
track" that names which stages collapse and how the Stress-test-as-test substitution
works) rather than each plan improvising it. `gleipnir-plan` does **not** decide that
standing rule here — that is a material process decision for the brainstorm/
convergence gate + operator; this note only names it as a follow-on so it is not
silently established by repetition.

**Who does what:**

| Actor | Action | Tier / capability |
|---|---|---|
| `gleipnir-plan` (me) | Supersession note + this plan | Tier-0 writes (in-bounds) |
| `quality-reviewer` | spec-review of this plan vs the brief | read-only, no writes |
| **Operator** (build mode) | Apply (a) session-scribe grant + prose + digest | **Tier-3** — operator only (G-1/G-6) |
| **Operator** (build mode) | Apply (b) orchestrator escalation section — **both** the frontmatter `compaction_survival:` bullet (b.1) **and** the body section (b.2), in one edit | **Tier-3** — operator only |
| Orchestrator | At live-use: draft, `question`, confirm, stamp footer, delegate, verify, report | holds `question` + `task`; no edit/write/bash |
| **session-scribe** | The **only** bounded-agent write: append the one confirmed entry to the candidate file on delegation, read back, report | Tier-0-role with the single-file Tier-2 exception from (a); no `question`/`task`/`bash`/git |

**The append is the sole bounded-agent action.** Everything upstream (drafting,
confirming, coalescing judgment, footer stamping) is orchestrator judgment gated by
`question`; the two structural changes are Tier-3/operator. session-scribe's
append-on-delegation — one confirmed lesson per delegation, verified against disk —
is the only place a roster agent touches the Tier-2 file, and only on an explicit
orchestrator delegation carrying operator-confirmed verbatim text.

**Reversibility.** Two-way door: reversing the process = delete the orchestrator
section; reversing the mechanism = delete the two allowlist lines + revert prose +
recompute digest. No data migration, no external lock-in.
