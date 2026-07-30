# Tier-3 Control Proposal: Tier-0→Tier-2 interim escalation path for lesson candidates

> **Status: operator-converged (Option A), awaiting application.** Written by
> `gleipnir-brainstorm` (Tier-0 writer) after the operator converged on Option A
> via the orchestrator's `question` gate. This is a **proposal**, not an
> implementation — the grant change is a Tier-3 edit the operator applies. The
> Decision Analysis below records the alternatives considered and why Option A
> won; it is the justification for the converged choice, not a re-opening of it.

## Gap

The intended Tier-2 write path (`decisions/gleipnir-layout-and-memory-model.md`
§2: Receive → Classify → Validate → **Review [human diff, precept-10]** →
Append-audit) is documented but its own Status section states it is **"authored,
not yet closed"** — it depends on the G-4 bus, the S-2 mount, and the `keys/`
digests, none of which exist yet. Consequently **no bounded role can append to
`.gleipnir/lessons/session-lessons-candidates.md`**, even though that file is
explicitly *pre-review candidate text* that grants no capability and changes no
enforcement.

**Consequence observed this session:** every candidate lesson (L-C1…L-C13) was
written via the operator's full build-mode escape-hatch round-trip — an
expensive mode switch for genuinely low-stakes advisory content destined for
later human review.

**Safety vs preference:** This is a **workflow-efficiency** gap, not a safety
invariant. The safety invariants the memory model protects — external/untrusted
content must not reach a *policy* field, and any high-trust change needs a
human-bound diff — are preserved regardless, because (a) the destination is a
self-labeled, authority-free candidate file, and (b) human review is retained
via the orchestrator's existing `question` gate (see the converged process
below).

## Correct layer

The grant lives in **Tier-3 POLICY** (`.gleipnir/agents/session-scribe.md`).
Confirmed by investigation:

- `session-scribe` today writes **only** `.gleipnir/plans/**` and
  `.gleipnir/var/tmp/**` (Tier 0). It is already the framework's designated
  Tier-0 bookkeeping writer, already carrying the verify-against-disk /
  never-fabricate append discipline (session-scribe.md lines 57–67).
- **No other bounded role can write `.gleipnir/lessons/**` today.** The only two
  mentions of `lessons/` in the roster are exclusionary (session-scribe's own
  deny; gleipnir-plan's explicit "nor lessons/"), and `gleipnir-code`
  explicitly denies `.gleipnir/**` (gleipnir-code.md line 14). No `allow` line in
  any agent targets `lessons/` or `memory/`.
- The candidate file **self-labels** as CANDIDATE / pre-graduation / not-yet-
  enforced in its own header (lines 1–9) — the honesty posture is structural to
  the file's content, independent of who appends.

Per the layer map, Tier-3 POLICY is a **No** row: every roster grant denies
`.gleipnir/**`. This is exactly why the output is a proposal the operator
applies, not an edit any agent (including this one) performs.

## Proposed artifact

**Path:** `.gleipnir/agents/session-scribe.md` (Tier-3; operator-applied)

**Content (the exact diff):**

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

This adds exactly **one named file** to both the `edit` and `write` maps. It is
**not** blanket `.gleipnir/lessons/**`, **not** `.gleipnir/lessons/README.md`,
**not** any other lessons-tier file, and **not** `.gleipnir/memory/**`.

Accompanying prose amendments the operator applies in the same edit:

- Update the `description` frontmatter to name the single-file Tier-2 exception
  (currently it asserts "never any Tier-2 (memory/, lessons/) … path").
- Amend the "Capability boundary" section (lines 44–55) to carve out this ONE
  file as an explicit, human-gated exception — session-scribe still refuses any
  other Tier-2/Tier-3 path, and only writes this file on an explicit
  orchestrator delegation carrying operator-confirmed text.

**Activation:** Operator switches to build and applies the diff + prose
amendments to `session-scribe.md`, then recomputes the `keys/` digest for
`session-scribe.md` (standard Tier-3 edit hygiene, so S-3 preflight does not
quarantine the changed file once digests are wired).

## Enforces / bypass semantics

- The append is gated **upstream** by the orchestrator's existing `question`
  primitive: the orchestrator MUST present the drafted lesson text to the
  operator for explicit per-use confirmation **before** delegating the append.
  This substitutes the existing precept-10 `question` discipline for the
  not-yet-built deterministic "Review" step of the intended pipeline.
- `session-scribe` holds no `task`, no `question`, no `bash`, no git — it
  **cannot self-trigger**. It is inert without an explicit orchestrator
  delegation, and even then writes only the one named file.
- No new *capability* lever is created: this is a low-authority data append to a
  self-labeled candidate file, not a broad grant. It is deliberately **not** an
  ambient/rubber-stampable permission — every use passes through a deliberate,
  per-use human `question` (matching the constraint the operator set when they
  rejected a broad `task: general: allow` grant earlier this session).
- **Reversibility:** two-way door — reversal is deleting the two allowlist lines
  and reverting the prose. No data migration, no external lock-in.

## The converged escalation process

> **⚠️ SUPERSEDED — see `lesson-escalation-process-brainstorm.md` (Approach
> A-hybrid) and its plan `lesson-escalation-process.md`.**
>
> The 8-step process **below** (and Handoff step 2 that points at it) was
> **self-designed by the orchestrator without methodology** — a process decision
> made inside the sequencing role, never explored against alternatives. That is
> the exact failure the brainstorm/convergence gate exists to close (cf. L-C6).
> It has since been redone properly: `gleipnir-brainstorm` ran 2–3 distinct
> process designs through a weighted decision matrix + bias catalogue, and the
> operator converged on **Approach A-hybrid** (immediate-by-default with
> opportunistic coalescing; uncapped; full discard on reject; lightweight footer
> + session id). `gleipnir-plan` then planned it (full ATLAS) into
> `.gleipnir/plans/lesson-escalation-process.md`.
>
> **What is still valid here:** the **mechanism** (WHO can write) — Option A,
> session-scribe's grant extended to the one file
> `.gleipnir/lessons/session-lessons-candidates.md`, human-gated via the
> orchestrator's `question`. That is converged and NOT re-opened. Only the
> *process* sketch below is superseded.
>
> **What is superseded:** the 8-step process in this section, and the reference
> to it in **Handoff step 2**. When the operator applies the `orchestrator.md`
> prose, it must reflect **A-hybrid** (per `lesson-escalation-process.md`'s
> Trace + Execution Workflow), NOT the 8-step sketch preserved below.
>
> The 8-step sketch is retained verbatim below as the historical record of what
> was tried and corrected — do not treat it as the authoritative process.

The grant change alone answers *who can write*; this 8-step process, converged
with the operator, answers *what the escalation process is* — closing the
remaining gap the operator flagged. It is part of what is being proposed and
handed off.

1. **Trigger** — any role (the orchestrator itself, or a subagent's report)
   surfaces a process/reliability observation worth a durable lesson. This is
   the orchestrator's judgment call, the same pattern that produced L-C1…L-C13
   — but the orchestrator must now **act** on it (propose it through this
   process), not merely mention it in passing.
2. **Draft** — the orchestrator writes the candidate entry in the existing L-Cx
   format (title / **Observed** / **Proposed lesson**), including the next
   sequential number (checked against the file's current highest existing L-C
   number).
3. **Present** — the orchestrator calls `question`, showing the **FULL VERBATIM**
   drafted text (never a summary or paraphrase), with options: **Approve as-is /
   Edit / Reject**.
4. **Confirm** —
   - *Approved as-is* → proceed with that exact text.
   - *Edits requested* → incorporate the operator's exact wording (never
     paraphrased), then **one** re-confirm round — capped at **2 rounds total**,
     mirroring the framework's existing loop-cap discipline elsewhere.
   - *Rejected* → discard; nothing is written, no further action.
5. **Provenance stamp** — append a small footer to the entry: the date,
   `reviewed_by: operator (via question, this session)`, and an explicit note
   that this substitutes for the not-yet-built deterministic reviewer step
   (honest, since the real G-4c pipeline does not exist yet) — so there is an
   audit trail even without the G-4 bus.
6. **Delegate** — the orchestrator hands `session-scribe` the **EXACT confirmed
   text** (verbatim, including the provenance stamp) plus the target location:
   append immediately **before** the file's "## Note on placement" tombstone
   section, matching the file's existing structure (each prior L-Cx entry
   appears in that same slot).
7. **Verify** — `session-scribe` reads the file back after writing, per its own
   existing "always end with a written report" standing instruction, to confirm
   the append landed correctly and that nothing else in the file was altered.
8. **Report** — the orchestrator confirms to the operator: the lesson is
   recorded as L-C<n>.

This process substitutes the human `question` gate (steps 3–4) for the
deterministic reviewer that the G-4c pipeline will eventually provide, and the
provenance stamp (step 5) for the G-4 audit event. Both substitutions are
explicit and honest: when the real pipeline lands, it replaces these steps
without changing the file's honesty posture.

## Honesty label

**cooperative-policy-until-S-2.** Today the tier boundary is enforced by
opencode permissions plus this prose, not structurally. It becomes a hard
boundary when the S-2 mount makes Tier 3 read-only from the agent surface and
the `keys/` digests + S-3 preflight verification are wired. The candidate
file's own header remains the honesty anchor: content stays free-written,
explicitly pre-review, granting no capability; the interim write does **not**
claim to be a "graduated" lesson.

## Decision Analysis

**Decision type:** Architectural tradeoff — a durable change to a role's write
surface plus a workflow. **Framework:** Reversibility Filter → Pros-Cons-Fixes,
with a Pre-Mortem on the leading option.

**Reversibility:** *Two-Way Door.* Reversal = delete two allowlist lines + revert
prose. No data migration, no external lock-in, low reversal cost. The surface it
touches (a Tier-3 grant + a cross-tier escalation precedent) warranted the
deeper Pros-Cons-Fixes + Pre-Mortem below even so.

### Options

**Option A — Extend session-scribe's grant to the one candidate file (CONVERGED)**

Pros:
- Reuses the role already designed as the Tier-0 append writer, already carrying
  the verify-against-disk / never-fabricate discipline a lesson append needs.
- No new role and no new ambient lever; session-scribe stays inert without an
  explicit orchestrator delegation.
- Human confirmation reuses the existing precept-10 `question` gate — deliberate,
  per-use, non-rubber-stampable — matching the operator's stated constraint.
- Narrowest possible surface: ONE file, not a tier.

Cons and Fixes:

| Con | Fix |
|-----|-----|
| session-scribe now touches Tier 2, blurring its "Tier-0-only" identity. | Scope to a single named file + prose naming it an explicit, human-gated exception, not a tier grant. The file's own header keeps the honesty posture. |
| Sets a precedent that Tier-3 grants get widened for convenience. | The convergence gate itself is the guard: each widening is an operator-converged Tier-3 decision, not an ambient default. |
| Pre-S-2 the boundary is cooperative-policy, so a compromised orchestrator could over-invoke it. | True of all pre-S-2 grants; the target is authority-free candidate text and the human `question` gate sits in front. No new capability is granted, only a low-authority append. |

Post-fix verdict: **Viable** (converged).

**Option B — Standalone out-of-framework CLI (`bin/gleipnir-lesson-append`)**

Pros:
- Keeps all roster grants at zero Tier-2; the tier wall stays pristine.
- Closer in shape to the eventual deterministic "decide" component.

Cons and Fixes:

| Con | Fix |
|-----|-----|
| **No bounded role can run it.** session-scribe/gleipnir-code deny arbitrary bash; the orchestrator holds zero bash by deliberate design. So either the operator runs it manually (≈ the build-mode round-trip we are trying to avoid — solves nothing) or a role gains a new bash allowlist entry (a new capability lever, worse than A's data-only append and closer to the ambient grant the operator rejected). | No clean fix pre-S-2 without introducing exactly the kind of lever the constraint forbids. |
| Builds throwaway machinery the real G-4c pipeline will replace, not extend. | — |
| A CLI that writes Tier 2 is itself a Tier-2 writer living outside the tier model's named-writer accounting. | — |

Post-fix verdict: **Marginal** — the "who runs it" problem reintroduces either
the round-trip cost or a bash lever.

**Option C — Do nothing; keep using the build-mode escape hatch**

Pros: zero change; maximal tier purity.
Cons: every candidate note costs a full mode-switch round-trip for authority-free
text — the observed friction. Post-fix verdict: **Not viable as a fix** (it *is*
the problem), though a legitimate baseline if absolute tier purity outranks
friction.

### Pre-Mortem on Option A (assumed failure at 6 months)

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|--------------|------------|--------|------------|
| 1 | Grant quietly widened later ("just add memory/ too") via precedent | M | H | Prose fixes it to ONE named file; any widening is a fresh converged Tier-3 decision |
| 2 | Orchestrator skips the `question` gate and auto-appends | L | M | question-gate is prose today, structural post-S-2; append target is authority-free regardless |
| 3 | Someone treats candidate text as a graduated lesson | L | M | File header self-labels CANDIDATE; graduation stays a separate G-4c path |
| 4 | Digest for session-scribe.md not recomputed after edit → preflight quarantine | M | L | Operator recomputes digest as part of applying (standard Tier-3 edit hygiene) |

Verdict: **Proceed with mitigations.**

### Bias check (top 3)

- ⚠️ **Status Quo Bias** — Option C (keep the escape hatch) was scrutinised as
  hard as A, not given a free pass for being current. C is viable only if tier
  purity outranks friction; the operator's "clearly a case that should have an
  escalation path" signal weighed against C.
- ⚠️ **IKEA Effect** — the recommendation favors extending an existing
  in-framework role over the external CLI. Checked against an "if someone else
  built both" test: the preference survives, because Option B's fatal flaw (no
  bounded runner without a new bash lever) is structural, not aesthetic.
- ⚠️ **Scope Creep Bias** — the guard against "escalation path" quietly becoming
  "give session-scribe `lessons/`" is the single-named-file scoping. Do not relax
  it.

### Recommendation → Converged choice

**Option A**, scoped to the single file
`.gleipnir/lessons/session-lessons-candidates.md`, gated by the orchestrator's
existing per-use `question` confirmation of the drafted text before delegation.
**The operator converged on Option A** via the orchestrator's `question` gate.
Confidence: High.

## Handoff

This is a **Tier-3 POLICY** control; I (a Tier-0 writer) cannot write it. To
apply, the operator switches to build and:

1. **Primary edit — `.gleipnir/agents/session-scribe.md`:** add the two scoped
   allowlist lines (to both `edit` and `write`), update the `description`
   frontmatter to name the single-file exception, amend the "Capability
   boundary" section per the Proposed artifact above, then recompute the
   `keys/` digest for the file.
2. **Additional small edit — `.gleipnir/agents/orchestrator.md`:** ~~document the
   8-step escalation process above~~ **SUPERSEDED** — document the **A-hybrid**
   escalation process (per `.gleipnir/plans/lesson-escalation-process.md`'s Trace
   §(b) + Execution Workflow), NOT the 8-step sketch above, alongside the
   orchestrator's existing convergence-gate discipline for Tier-3 decisions, so
   the standing instruction captures how a lesson candidate is proposed →
   (optionally coalesced) → confirmed → delegated. This is **not a new material
   decision** — it documents the already-converged A-hybrid process — and the
   operator can apply it in the same build session as edit (1).

Then stop — this proposal implements nothing itself.
