# Design Brief: "go-caged" — operator-facing caged-mode runbook + guiding skill

> **Stage:** `brainstorm` (Clarify → Explore → Propose → **Converge — DONE**).
> **Author:** `gleipnir-brainstorm`. **Tier-0, disposable.**
> **Convergence status: CONVERGED.** The three HIGH-LEVEL scope items (SHAPE,
> RELATIONSHIP, DEPTH) were **operator-LOCKED** and recorded below as constraints.
> The five material **sub-decisions (C1–C5)** in `## Decision Analysis` are now
> **OPERATOR-CONVERGED** — the operator's choices were surfaced through the
> orchestrator's `question` tool (honest provenance; NOT a self-attested subagent
> decision — `gleipnir-brainstorm`'s own `question` cannot reach the operator) and
> are recorded in "Selected Approach (Converge)" below. **This brief is ready to
> hand to `gleipnir-plan`.** The brief authored nothing outside this Tier-0 file:
> it did **not** author the runbook or skill, create any Tier-3 file, or edit any
> skill — it is a design brief only.

---

## Problem Statement

The framework has just adopted a **default-uncaged, opt-in-caged** operating
posture (`plans/override-paradigm.md`; the durable record
`decisions/operating-posture.md` is pending operator authoring — its text lives
in `override-paradigm.md` §C). Under that posture, **caged mode is a REQUIREMENT**
for three triggers: (1) unattended/autonomous/long-running sessions;
(2) any session ingesting untrusted external content; (3) higher-assurance /
hosted / multi-agent operation.

But "go caged" today is scattered across four artifacts an operator would have
to assemble under pressure: the just-built `--mode caged` preflight selector
(`src/gleipnir/preflight/`), the S-2 C2 OS acts
(`plans/s2-activation-control-proposal.md`), the approved S-2 plan
(`plans/s2-activation.md`), and the `tier3-coach` detect→propose→converge→handoff
pattern. There is **no single operator-facing front door** that says *"here is
exactly how you satisfy the caged requirement, step by step, verified against the
real box, with a go/no-go gate."*

The operational answer to *"how do I actually go caged when the posture requires
it?"* does not yet exist as one coherent thing. This is what "go-caged" provides.

## Constraints

### Operator-LOCKED scope (recorded, NOT re-decided)

- **SHAPE = both.** A caged-mode **RUNBOOK** is the single source of truth
  (checklist + acceptance test), PLUS a **SKILL** the agent loads to guide the
  operator through it interactively and verify each step against the real box
  state. **The skill REFERENCES the runbook** so there is never drift between two
  copies of the procedure.
- **RELATIONSHIP = assemble existing pieces** into one "go-caged" front door — do
  NOT re-author from scratch. Pull together: the `--mode caged` preflight
  selector; the S-2 C2 OS acts (`s2-activation-control-proposal.md`); the
  approved S-2 plan (`s2-activation.md`); and the `tier3-coach`
  detect→propose→converge→handoff pattern.
- **DEPTH = full caged mode** = the complete lockdown: `--mode caged`
  (preflight-bound; caged-without-CLOSED REFUSES) AND the operator's S-2 C2 OS
  acts (dedicated agent uid, enforcement paths OS-read-only, key mode-600,
  root-elevated launch wrapper). **The AC-4 acceptance test** — a no-override
  preflight that reports CLOSED with an empty reasons list, exit 0 — **is the
  go/no-go gate.**

### Technical / environment ground truth (verified this session)

- **The `--mode caged` selector is already built and confirmed.** In
  `src/gleipnir/preflight/__main__.py` (`--mode {uncaged,caged}`, default
  `uncaged`) and `boundary.py` (`RequestedMode` enum lines 506–515;
  `UNCAGED_DEFAULT_LABEL` line 523; `decide()` at line ~538). A `caged` request
  that does not reach `CLOSED` returns `Verdict.REFUSE` (exit 1, deficiency label
  retained — `boundary.py:580–585`). **`requested_mode` NEVER enters the
  `all_closed` computation** — the mode can never manufacture `CLOSED`
  (anti-false-assurance invariant, override-paradigm P1). Nothing to build in the
  software layer; the runbook *invokes* it.
- **The S-2 C2 acts are already drafted, ready-to-apply, operator-only.**
  `plans/s2-activation-control-proposal.md` carries the six steps verbatim:
  (1) create agent uid/gid (`dscl`/`sysadminctl`); (2) `agent-identity.env`
  single-source-of-truth; (3) ownership/group layout; (4) `chmod` enforcement
  paths OS-read-only; (5) key mode-600 owner-only; (6) root-elevated launch
  wrapper (`bin/gleipnir-launch`). **No roster agent can perform these** (OS/host
  + Tier-3 layer; tier3-coach Anti-Pattern 3).
- **AC-4 is the named go/no-go gate.** `sudo bin/gleipnir-preflight --agent-uid
  <uid> --agent-gid <gid>` (**no** `--override-ack`) → `closed`, empty reasons,
  exit 0. `sudo` is required on macOS (setuid to a different uid needs root)
  (`s2-activation.md` AC-4, review round R-1).
- **The preflight is out-of-framework, operator-run, fail-closed** — it must
  never be routed into any agent allowlist (`__main__.py:1–12`).
- **Enforcement core is stdlib-only** — the runbook adds no dependency; it only
  documents/invokes existing tools and OS commands.
- **The agent GUIDES; the OPERATOR applies.** The OS acts need the operator's
  root; the agent cannot perform them. The skill's job is to *guide + verify each
  step against real box state*, not to execute — the identical handoff shape as
  `tier3-coach` Anti-Pattern 3 and the same self-attestation discipline
  (a subagent's `question` cannot reach the operator).

### Capability boundary for THIS work

- `gleipnir-brainstorm` may write **only** `.gleipnir/plans/**` (Tier 0). This
  brief is the only artifact produced now.
- Where the runbook and skill ultimately live is **C1/C2 below** — surfaced for
  operator convergence, because it decides a trust tier and an authorship owner.

## Approaches Considered

The high-level SHAPE (both runbook + skill, skill references runbook) is LOCKED,
so the "approaches" here are genuinely-distinct **assembly topologies** for how
the front door is composed — not alternatives to the shape.

### Approach A: Thin runbook + guiding skill, everything by REFERENCE

**Summary:** The runbook is a compact operator checklist whose OS-layer steps
are pure cross-references to the already-existing
`s2-activation-control-proposal.md` (the six acts) and to the built `--mode
caged` selector. The skill references the runbook. No procedure text is
duplicated anywhere.

**Tradeoffs:**
- Pro: Maximal DRY — one source of truth per fact; the classifier's single-source
  preference is honoured; a future edit to the C2 acts propagates with zero drift.
- Pro: Smallest new artifact; strongest "assemble, don't reinvent" fidelity.
- Pro: The skill + runbook + proposal form a clean citation chain the reviewer
  can trace.
- Con: An operator following the runbook **under pressure** (going caged *because*
  a requirement fired — often mid-incident) must open 2–3 files and jump between
  them to get the actual commands. Reference-chasing is exactly what fails under
  load.

**Estimated Scope:** 1 runbook file + 1 skill file (later `build`, not now); low
complexity.

**Risk:** low technically; **medium operationally** — a self-referential runbook
that isn't self-contained can be hard to execute in the moment it's most needed.

### Approach B: Self-contained runbook + guiding skill (inline the commands, cite the source)

**Summary:** The runbook **inlines** the six C2 acts' exact commands and the
`--mode caged` invocation so it is executable top-to-bottom without leaving the
page, while **citing** `s2-activation-control-proposal.md` as the authoritative
source (a "sync-checked copy", not an independent fork). The skill references the
runbook.

**Tradeoffs:**
- Pro: An operator under pressure runs the runbook start-to-finish in one file —
  the single most important property of a runbook you follow during an incident.
- Pro: Still has ONE authoritative source (the C2 proposal); the inline copy is
  labelled a mirror with a currency/sync note, mirroring the precedent already
  set by `s2-activation-control-proposal.md` itself (which inlines the plan's C2
  section and back-links to it).
- Con: Two copies of the command text exist → drift risk if the C2 acts change
  and the runbook mirror isn't re-synced. Mitigable with an explicit "source of
  truth = the proposal; re-sync on change" banner + a currency note.

**Estimated Scope:** 1 (larger) runbook file + 1 skill file (later `build`); low–
medium complexity.

**Risk:** medium — drift between the inline mirror and the C2 proposal if a future
change updates one and not the other; the currency banner + the skill's
"verify against real box state" step both catch a stale mirror at execution time.

### Approach C: Hybrid — inline the software-layer + go/no-go + rollback; reference the OS acts

**Summary:** Split by *who owns the step and how it changes*. **Inline** the parts
that are stable, short, and where flow-under-pressure matters most — the `--mode
caged` invocation, the AC-4 go/no-go test, the uncage/rollback steps, and the
honesty label. **Reference** the six OS acts (the long, host-specific, operator-
owned block that already lives, ready-to-apply, in
`s2-activation-control-proposal.md`) with a one-line "run acts (1)–(6) from
`s2-activation-control-proposal.md`, then return here for the go/no-go test".

**Tradeoffs:**
- Pro: The high-frequency / high-pressure steps (invoke, verify, roll back) are
  self-contained; the long host-specific OS block stays single-sourced where it
  already is (no dscl/chmod command is ever duplicated → no drift on the volatile,
  host-tailored part).
- Pro: Best DRY-vs-usability balance — duplicates only the short stable glue,
  references the long volatile block. Matches how operators actually use a runbook
  (the OS acts are a one-time setup; the invoke/verify/rollback is the repeated
  operational surface).
- Pro: Keeps the tier3-coach citation intact for the exact part that is an
  operator-only OS/Tier-3 control.
- Con: A reader must still open the C2 proposal once, for the OS acts — so it is
  not *fully* self-contained; the split point ("inline the stable glue, reference
  the volatile host block") is a judgment the operator should sign off on.

**Estimated Scope:** 1 runbook file + 1 skill file (later `build`); low–medium
complexity.

**Risk:** low–medium — the only duplicated text is short and stable (the
invocation + the AC-4 line, which already appear verbatim in multiple plans);
the volatile OS block is never duplicated.

## Decision Analysis

> **[GLEIPNIR] These analyses are the INPUT to the operator's convergence, not
> the decision.** `gleipnir-brainstorm` is a subagent; its `question` tool does
> NOT reach the operator. All recommendations below are **advisory only** and are
> returned to the orchestrator to put to the operator. The brief's "Selected
> Approach" is written **only after** the operator's converged choices come back.

**Decision-point count:** five material sub-decisions (C1–C5). C4 is the primary
DRY-vs-self-contained tradeoff (it maps to Approaches A/B/C above). C1 is a
one-way-door trust-tier/authorship choice. C2 is an architectural boundary. C3
and C5 are lower-stakes but each carries a real tradeoff worth surfacing.

---

### C1 — Where does the runbook live? (trust tier + authorship)

**Framework used:** Reversibility Filter → Weighted Decision Matrix.
*Selection rationale:* choosing a home is partly a **one-way door** (a
"source-of-truth" runbook placed in a disposable tier and later depended on is
expensive to relocate once links accrete), so it warrants a scored comparison
across durability, authorship-fit, and effort.

**Reversibility:** One-Way-Door-ish. Reversal cost = re-homing an artifact that
other files (the skill, the posture record) will link to. → apply deeper analysis.

**Options:**
- **Option 1 — `.gleipnir/decisions/` (Tier-3 durable, operator-authored).** A
  caged-mode runbook is operational **POLICY** ("how you satisfy the caged
  requirement"); it is the operational companion to the pending
  `decisions/operating-posture.md`. Tier-3 is durable and non-disposable, and it
  is operator-authored — matching that the caged acts are themselves
  operator-owned.
- **Option 2 — a new `.gleipnir/runbooks/` directory.** A dedicated home
  signalling "operational procedure, distinct from decision records."
- **Option 3 — `.gleipnir/plans/` (Tier-0, alongside the S-2 plans).** Nearest to
  the assembled pieces, and agent-writable now. **But Tier-0 is disposable** —
  the plans/README lifecycle policy treats these as session artifacts to be
  cleaned up after merge. A source-of-truth runbook must NOT be disposable.

| Criterion | Weight | Opt 1 `decisions/` | Opt 2 `runbooks/` | Opt 3 `plans/` |
|---|---|---|---|---|
| Durability (not disposable) | 10 | 10 → 100 | 10 → 100 | 2 → 20 |
| Authorship fit (operator owns caged acts) | 8 | 10 → 80 | 7 → 56 | 4 → 32 |
| "Source of truth" signalling | 7 | 8 → 56 | 10 → 70 | 3 → 21 |
| Minimal new structure (no new dir/tier concept) | 6 | 9 → 54 | 3 → 18 | 8 → 48 |
| Proximity to assembled pieces | 4 | 6 → 24 | 5 → 20 | 10 → 40 |
| Tier-3 write cost (operator-only, not agent-draftable) | 5 | 4 → 20 | 4 → 20 | 10 → 50 |
| **Total** | | **334** | **284** | **211** |

**Recommended (advisory):** **Option 1 — `.gleipnir/decisions/`** (Tier-3
durable, operator-authored). A caged-mode runbook is operational policy of lasting
consequence and belongs with `operating-posture.md`, not in a disposable tier.
Caveat the matrix surfaces: Option 1 scores lowest on "minimal write cost"
because Tier-3 is operator-only — the runbook is **not agent-draftable**; the
agent proposes its text (as this brief's successor would), the operator authors
it. That is the *correct* consequence, not a defect (it mirrors the C2 OS acts).
Option 2 is a close, legitimate second if the operator wants operational
procedures visibly separated from decision records — the tradeoff is a new
Tier-3 concept/dir to maintain.

**Bias warnings:**
- ⚠️ *Scope-Creep Bias (watch):* Option 2 introduces a whole new directory/tier
  concept for a single artifact. Prefer an existing home unless the operator
  foresees several runbooks. Do not manufacture a subsystem where a file placed
  in an existing tier suffices.

---

### C2 — New skill vs. extend `tier3-coach` (architectural boundary)

**Framework used:** Pros-Cons-Fixes (binary A/B with a clear boundary question),
after a Reversibility Filter (Two-Way Door — a skill can be split/merged later
cheaply).

**The boundary question:** `tier3-coach` is about **detecting a control GAP and
proposing a control** (Detect → Locate → Propose → Converge → Hand off). "go-caged"
is about **EXECUTING a known, already-designed lockdown on operator request** —
the gap is already found, the control already designed (the C2 proposal exists).
Different verbs: *discover-and-propose* vs *guide-through-and-verify*.

- **Option 1 — a NEW sibling skill (`go-caged`).** Guides the operator through the
  known lockdown and verifies each step against real box state.
  - Pro: Clean SRP — one skill = one responsibility. `tier3-coach` keeps "find
    gaps, propose controls"; `go-caged` owns "execute the known caged lockdown."
  - Pro: A distinct, memorable trigger surface ("go caged", "lock it down") that
    would be noise inside tier3-coach's gap-detection description.
  - Pro: References the runbook (per the LOCKED SHAPE) without bloating
    tier3-coach.
  - Con: Two adjacent skills a reader must understand as related-but-distinct.
    *Fix:* each skill's frontmatter/body names the other and states the boundary
    ("tier3-coach FINDS+PROPOSES; go-caged EXECUTES a known lockdown"); a one-line
    cross-reference removes the confusion.
  - Con: Some shared DNA (the agent-guides/operator-applies handoff; the
    self-attestation discipline). *Fix:* go-caged **reuses** tier3-coach's
    handoff pattern by reference rather than re-deriving it — the skill body cites
    "same handoff shape as tier3-coach Anti-Pattern 3."
- **Option 2 — fold "go-caged" into `tier3-coach`.**
  - Pro: One skill, one place to look.
  - Con: Violates SRP — merges *gap-detection/proposal* with *known-lockdown
    execution*; the description would have to trigger on both "I found a control
    gap" and "operator says go caged," blurring the tool. *Fix:* none clean —
    the two jobs genuinely differ; folding them is the Scope-Creep failure.
  - Con: tier3-coach explicitly "proposes, never implements"; go-caged is
    execution-guidance (still operator-applies, but the *posture* is
    walk-me-through-this, not here-is-a-proposal). Overloading one skill with both
    postures muddies its clearest anti-pattern.

**Post-fix verdict:** Option 1 = **Viable**; Option 2 = **Marginal** (fixable only
by not really merging them).

**Recommended (advisory):** **Option 1 — a NEW sibling skill**, adjacent to
`tier3-coach`, that (a) references the runbook as its single source of truth, and
(b) reuses tier3-coach's agent-guides/operator-applies handoff + self-attestation
discipline **by reference**. Name the boundary explicitly in both skills. The
agent-guides-but-operator-applies split is preserved: the OS acts need the
operator's root, so the skill GUIDES + VERIFIES and the operator EXECUTES.

**Bias warnings:**
- ⚠️ *IKEA Effect (watch, mild):* tier3-coach is a home-grown Gleipnir-original;
  there may be a pull to extend it because "we built it and it's ours." Evaluate
  on SRP fitness, not authorship — a clean sibling wins on responsibility
  separation regardless of who built tier3-coach.
- ⚠️ *Scope-Creep Bias (watch):* folding execution into a detection skill is the
  "expand one thing to swallow the other" pattern. A sibling that references
  keeps each skill's scope tight.

---

### C3 — Skill trigger phrasing (description / load trigger)

**Framework used:** Pros-Cons-Fixes (Two-Way Door — trigger phrasing is trivially
revisable; per Anti-Pattern 1, do not over-analyse a reversible naming choice).

**Consideration:** The skill must load when the operator signals intent to enter
the required high-assurance lockdown. Candidate phrases the operator would
naturally use: *"go caged"*, *"cage the system"*, *"lock it down"*, *"we're going
autonomous / unattended"*, *"high-assurance mode"*, *"we're ingesting untrusted
content"* (the last two map directly to the `operating-posture.md` triggers).
The description should also make the load-trigger discoverable to the agent
without over-matching (e.g. not firing on casual mentions of "cage").

**Draft description/trigger line (advisory, for operator sign-off):**
> "Guide the operator through entering full **caged mode** (the opt-in
> high-assurance S-2 lockdown) on request, verifying each step against real box
> state and gating on the AC-4 acceptance test. Triggers on: *go caged*, *cage
> the system / cage it*, *lock it down*, *going autonomous / unattended*,
> *high-assurance mode*, *we're ingesting untrusted content* — i.e. the
> `operating-posture.md` caged requirements. GUIDES + VERIFIES; the operator
> applies the OS/root acts (same handoff shape as tier3-coach). References the
> caged-mode runbook as its single source of truth."

**Recommended (advisory):** Adopt the draft, anchoring the triggers to the three
`operating-posture.md` requirement categories so the phrase list is principled
(it mirrors *when caging is required*), not arbitrary. Confirm the operator's
preferred primary phrase ("go caged" vs "cage the system").

**Bias warnings:** None material. (Reversible, low-stakes; per decision-frameworks
Anti-Pattern 1 this is fast-tracked and not over-analysed.)

---

### C4 — Runbook structure + reference-vs-inline the S-2 commands (the primary tradeoff)

**Framework used:** Second-Order Thinking (this is the architectural DRY-vs-
usability tradeoff with downstream drift/usability consequences), cross-checked
against the Approaches A/B/C above.

**Proposed section skeleton (advisory — the shape, not the content):**
1. **Purpose + honesty label** — what caged mode is, that it is opt-in-REQUIRED
   for the three triggers, and the honest state it produces.
2. **Preconditions** — operator has root; on macOS; repo present; a free uid/gid
   chosen; key file exists.
3. **Software-layer step** — the `--mode caged` invocation and its
   preflight-bound semantics (caged-without-CLOSED REFUSES; the mode can never
   manufacture CLOSED).
4. **OS-layer steps** — the six S-2 C2 acts (create uid/gid → `agent-identity.env`
   → ownership/group layout → `chmod` enforcement paths OS-ro → key mode-600 →
   root-elevated launch wrapper). **Reference-vs-inline is the tradeoff below.**
5. **Go/no-go acceptance test (AC-4)** — `sudo bin/gleipnir-preflight --agent-uid
   <uid> --agent-gid <gid>` (no override) → `closed`, empty reasons, exit 0. This
   is the gate: no CLOSED-with-empty-reasons ⇒ NOT caged.
6. **Flip / verification** — adopt `bin/gleipnir-launch` for sessions; confirm the
   posture holds.
7. **Rollback / how-to-uncage** — (detailed in C5).
8. **Honesty label** — hard-OS-boundary-once-AC-4-passes vs cooperative-until-then.

**The reference-vs-inline tradeoff (second-order):**

*Decision:* how to render the OS-layer step (#4) — inline the exact commands, or
reference `s2-activation-control-proposal.md`?

- **Reference (Approach A):**
  - Near-term first-order: perfect DRY, one source of truth, zero drift.
  - Near-term second-order: an operator going caged **under pressure** (a
    requirement fired mid-incident) reference-chases across files → slower,
    error-prone exactly when reliability matters most.
- **Inline (Approach B):**
  - Near-term first-order: fully executable in one file.
  - Far-term second-order: two copies of dscl/chmod commands → drift when the C2
    acts change and the mirror isn't re-synced → a *stale runbook is worse than a
    referenced one* (it looks authoritative but is wrong).
- **Hybrid (Approach C):**
  - Inline the short, stable, high-pressure glue (the `--mode caged` invocation,
    the AC-4 line, rollback); reference the long, volatile, host-specific OS block.
  - Second-order: the only duplicated text is short + stable (already appears
    verbatim across multiple plans), so drift risk is confined to text that rarely
    changes; the volatile host block stays single-sourced. **Best balance.**

**Key insight:** The drift risk is concentrated in the *host-specific OS block*
(dscl/chmod/uid — long, tailored, occasionally revised); the usability need is
concentrated in the *invoke/verify/rollback glue* (short, stable, run under
pressure). Hybrid aligns each rendering choice with the property that dominates
that block.

**Recommended (advisory):** **Approach C (Hybrid)** — inline the software-layer
invocation, the AC-4 go/no-go test, and the rollback steps; **reference** the six
OS acts in `s2-activation-control-proposal.md` (with a one-line "run acts (1)–(6)
there, then return for the go/no-go"). Add a currency banner: *"source of truth
for the OS acts = `s2-activation-control-proposal.md`; the skill's per-step verify
catches a stale reference at execution time."* If the operator prioritises
absolute single-source purity, Approach A is the fallback; if they prioritise
one-file-execute-under-pressure above all, Approach B with a hard sync banner.

**Bias warnings:**
- ⚠️ *Over-Engineering (watch):* do NOT design a config system or a generated
  runbook here. What was asked is a **checklist + a guiding skill**. Keep #1–#8 as
  prose/checklist; resist adding templating, variable-substitution machinery, or a
  runbook-generator.
- ⚠️ *Scope-Creep Bias (watch):* this is assembly. The skeleton must *assemble*
  the four existing pieces, not re-author the S-2 procedure or the preflight
  semantics.

---

### C5 — Uncage / rollback (reversing caged mode)

**Framework used:** Reversibility Filter → Pros-Cons-Fixes.

**Reversibility:** caged→uncaged is a **Two-Way Door** by construction — the
uncaged default is a legitimate posture (`operating-posture.md`), so returning to
it is not a failure state, just a mode change.

**The question:** is uncaging simply *"stop requesting caged"* (drop `--mode
caged` / stop launching via the root wrapper), or does it need explicit steps?

- **Software layer:** trivially reversible — launch without `--mode caged`
  (or without `bin/gleipnir-launch`) and the session runs uncaged. No OS change
  required to uncage the *software posture*.
- **OS layer:** the S-2 acts (agent uid, OS-ro enforcement paths, group layout)
  **can safely stay in place** while running uncaged — they are a hardened *floor*,
  not a blocker to uncaged operation (the operator/owner is outside the agent cage
  by construction; owner ≠ agent-uid). Leaving them costs nothing and speeds a
  future re-cage.
- **Key floor:** `keys/marker.key` mode-600 **stays in BOTH modes** — it is the
  retained key-protected floor of the uncaged default (`operating-posture.md`
  D2). Uncaging must NOT relax it.

**Options:**
- **Option 1 — "uncage = just stop requesting caged" (minimal).** Drop `--mode
  caged`/the wrapper; leave OS perms and key floor as-is.
  - Pro: Simplest; matches the Two-Way-Door reality; re-caging is instant.
  - Pro: No accidental relaxation of the key floor (nothing is touched).
  - Con: The operator might *expect* uncaging to "undo everything" and be
    surprised the OS perms persist. *Fix:* the runbook states explicitly that OS
    perms are a harmless persistent floor and the key floor is retained by design.
- **Option 2 — "uncage = full teardown" (relax OS perms, remove agent uid).**
  - Pro: Returns the box to a pristine pre-caged state.
  - Con: Pointless churn for a Two-Way Door; destroys the hardened floor that
    makes re-caging cheap; risks fat-fingering the key floor down. *Fix:* only do
    a full teardown if decommissioning the agent account entirely — a separate,
    rare operation, not the normal uncage.

**Recommended (advisory):** **Option 1 — minimal uncage.** Uncaging is "stop
requesting caged" (drop `--mode caged` / the root wrapper); the OS perms may stay
as a harmless hardened floor and the **key mode-600 floor stays in both modes**.
The runbook's rollback section states this explicitly so the operator is not
surprised the OS perms persist, and flags that a *full* teardown (remove uid,
relax perms) is a separate rare decommission step — never the routine uncage.

**Bias warnings:**
- ⚠️ *Status Quo Bias (inverted — watch):* do not treat "tear it all down" as the
  safe/clean default; for a Two-Way Door, leaving the hardened floor in place is
  the lower-risk choice. Scrutinise the teardown urge.

---

### Cross-cutting bias check (whole-brief)

- ⚠️ *Scope-Creep Bias:* the dominant risk across C1–C5. This is **assembly of
  four existing pieces**, not a new subsystem. Every recommendation above favours
  reusing/referencing existing artifacts (the C2 proposal, the built selector,
  the tier3-coach pattern) over re-authoring.
- ⚠️ *Over-Engineering:* what was asked is a **runbook (checklist + acceptance
  test) + a guiding skill that references it**. No config system, no generator, no
  new tooling. The AC-4 test already exists as the gate; the `--mode caged`
  selector already exists as the software step.

---

## Selected Approach (Converge)

**OPERATOR-CONVERGED.** All five sub-decisions were surfaced to the operator
**through the orchestrator's `question` tool** (the primary agent that *can* reach
the operator) and the operator's choices were handed back to `gleipnir-brainstorm`
to record here. **Honest provenance:** this is the operator's decision routed via
the orchestrator per the precept-10 convergence-gate discipline — it is **NOT** a
self-attested subagent decision (`gleipnir-brainstorm`'s own `question` tool
surfaces only inside its sub-session and cannot reach the operator; recording an
un-received decision would be the exact self-attestation failure the gate closes).

The advisory recommendations from the Decision Analysis were **accepted in full**.

### C1 — Runbook location — **OPERATOR-CONVERGED**

**Choice:** `.gleipnir/decisions/` (Tier-3 durable, operator-authored). The
caged-mode runbook is operational **POLICY** — the companion to
`operating-posture.md` — and therefore lives in the durable, non-disposable
Tier-3 layer, **NOT** in Tier-0 `.gleipnir/plans/` (which is disposable).

**Consequence (authorship split):** the runbook is **not agent-authored**. The
**agent DRAFTS** the runbook text; the **OPERATOR authors** it into Tier-3. This
mirrors the S-2 OS-acts handoff exactly (agent proposes ready-to-apply content,
operator applies it into the layer the agent cannot write).

### C2 — Skill structure — **OPERATOR-CONVERGED**

**Choice:** a **NEW sibling skill `go-caged`**, distinct from `tier3-coach`.
**Boundary (named in both skills):** `tier3-coach` *detects control gaps and
proposes controls*; `go-caged` *executes a known, already-designed lockdown on
operator request*. `go-caged` **reuses tier3-coach's guides-but-operator-applies
handoff BY REFERENCE** (it cites, not re-derives, the same handoff shape and the
same self-attestation discipline). **The skill GUIDES + VERIFIES each step against
real box state; the OPERATOR executes the OS acts** — the agent cannot, because
they need root (dedicated uid, OS-ro perms, key mode-600, root-elevated launch).

### C3 — Trigger phrasing — **OPERATOR-CONVERGED**

**Choice:** accept the drafted triggers, anchored to the three
`operating-posture.md` requirement categories: **"go caged"**, **"cage the
system"**, **"lock it down"**, **"going autonomous/unattended"**, **"high-assurance
mode"**, **"ingesting untrusted content"**. (Primary-phrase pinning carried to
`gleipnir-plan` as a residual — see Open Questions.)

### C4 — Reference-vs-inline (the primary tradeoff) — **OPERATOR-CONVERGED**

**Choice:** **HYBRID (Approach C).** **INLINE** the short/stable/high-pressure
glue — the `--mode caged` invocation, the **AC-4 go/no-go acceptance test**, and
the **uncage/rollback** steps — so an operator going caged under pressure runs
them from one file. **REFERENCE** the long/volatile/host-specific **six S-2 C2 OS
acts** in `.gleipnir/plans/s2-activation-control-proposal.md` ("run acts (1)–(6)
there, then return here for the go/no-go"). Rationale: **drift risk stays
single-sourced** in the referenced host block (dscl/chmod/uid — the part that
changes and is host-tailored), while **usability stays inline** for the stable
glue (the part run repeatedly and under pressure).

### C5 — Uncage / rollback — **OPERATOR-CONVERGED**

**Choice:** **MINIMAL uncage** = "stop requesting caged" — drop `--mode caged` /
stop launching via the root launch wrapper. The **OS perms MAY stay** as a
harmless hardened floor (owner ≠ agent-uid; leaving them speeds a future re-cage).
The **key mode-600 floor STAYS in BOTH modes** and is **never relaxed** (it is the
retained key-protected floor of the uncaged default, `operating-posture.md` D2).
A **full teardown** (remove the agent uid, relax OS perms) is a **SEPARATE, rare
decommission decision — never the routine uncage.**

### Converged summary

| # | Sub-decision | Operator-converged choice |
|---|---|---|
| C1 | Runbook location | `.gleipnir/decisions/` (Tier-3 durable); **agent drafts, operator authors** |
| C2 | Skill structure | New sibling skill `go-caged`; reuses tier3-coach handoff **by reference**; guides+verifies, operator executes OS acts |
| C3 | Trigger phrasing | Drafted triggers accepted, anchored to the three `operating-posture.md` categories |
| C4 | Reference-vs-inline | **Hybrid** — inline the `--mode caged` glue + AC-4 + rollback; **reference** the six OS acts |
| C5 | Uncage / rollback | Minimal uncage (stop requesting caged); OS perms may stay; **key mode-600 floor stays in both modes**; full teardown is separate |

**Handoff:** this converged brief is ready for `gleipnir-plan`. The plan stage
plans HOW to assemble these pieces (it does **not** re-decide C1–C5); the carried
plan-stage items are in Open Questions below.

## Open Questions

**C1–C5 are RESOLVED (OPERATOR-CONVERGED — see "Selected Approach (Converge)").**
The material design decisions are closed. The items below are **carried forward to
`gleipnir-plan`** — they are HOW-to-implement / wiring details bounded by the
converged decisions, not re-openings of C1–C5.

- **C1 — RESOLVED.** Runbook home = `.gleipnir/decisions/` (Tier-3, agent-drafts /
  operator-authors). *Carried to plan:* the exact **Tier-3 authorship split** —
  the plan drafts the ready-to-apply runbook text for the operator to author into
  Tier-3 (mirrors the S-2 OS-acts handoff); confirm the drafted text is complete
  and apply-ready.
- **C2 — RESOLVED.** New sibling skill `go-caged`, boundary vs tier3-coach named,
  handoff reused by reference. *(No residual — the boundary is fixed.)*
- **C3 — RESOLVED.** Drafted triggers accepted. *Carried to plan:* pin the
  **primary** trigger phrase ("go caged" vs "cage the system" vs "lock it down")
  so the skill description leads with it — cosmetic, within the converged set.
- **C4 — RESOLVED.** Hybrid. *Carried to plan:* confirm the **exact inline/
  reference split point** (inline the `--mode caged` glue + AC-4 + rollback;
  reference the six OS acts) and the currency/sync banner wording on the reference.
- **C5 — RESOLVED.** Minimal uncage; key mode-600 floor stays in both modes; full
  teardown separate. *(No residual — the rollback policy is fixed.)*
- **(Carried to plan) Skill-loading wiring:** does `go-caged` need to be added to
  the roster's skill-loading (which agent(s) load it — e.g. `gleipnir-brainstorm`
  / `orchestrator`) or is it operator-invoked on demand? A Tier-3 wiring question
  for the plan stage / operator — not a material design decision, not decided here.
- **(Carried to plan) Naming:** confirm the final skill name (`go-caged`) and the
  runbook filename under `.gleipnir/decisions/` before authoring.

## Scope Sketch

| Area | Files/Modules Likely Affected (at build, NOT now) |
|------|----------------------------------------------------|
| Runbook (source of truth) | Per C1: `.gleipnir/decisions/<caged-runbook>.md` (Tier-3, **operator-authored**) — OR a new `.gleipnir/runbooks/` file if C1 Option 2 |
| Guiding skill | Per C2: new `.gleipnir/skills/go-caged/SKILL.md` (Tier-3, **operator-authored**), references the runbook |
| Assembled-by-reference (unchanged) | `src/gleipnir/preflight/__main__.py` + `boundary.py` (the built `--mode caged` selector); `plans/s2-activation-control-proposal.md` (the six OS acts); `plans/s2-activation.md` (AC-4 gate); `skills/tier3-coach/SKILL.md` (handoff pattern) |
| Durable posture record (context) | `decisions/operating-posture.md` (pending operator authoring) — the runbook is its operational companion |
| Capability note | Runbook + skill are **Tier-3, operator-authored, agent-proposed**; the agent GUIDES + VERIFIES, the operator APPLIES the OS/root acts. No agent writes any of these. |
