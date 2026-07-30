# Design Brief: Should the roster standardize `skill gotcha` loading across all 9 agents?

_Brainstorm stage output. Operator-converged (Approach C, + orchestrator stays
prose-reference). Input for `gleipnir-plan`._

## Problem Statement

GOTCHA is described in `.gleipnir/skills/README.md` and
`.gleipnir/skills/gotcha/SKILL.md` as the framework's core 6-layer methodology
bridging probabilistic LLM reasoning with deterministic execution — seemingly
foundational. Yet a grep across all 9 `.gleipnir/agents/*.md` files (re-verified
this session) shows only **one** agent, `gleipnir-brainstorm`, loads
`skill gotcha` in a Startup section. The `orchestrator` merely *references*
`skills/gotcha/SKILL.md` in prose (citing Amendment 1); the other 7 agents
(session-scribe, quality-reviewer, gleipnir-code, notify, gleipnir-plan,
project-mgr, git-ops) load no skills at all — their disciplines are inlined
directly in their own agent files.

The question surfaced as a byproduct of the `glob-guidance-placement` brainstorm,
which *deliberately deferred* it (that brief, lines 239–248 and 319–322): "whether
to standardise a Startup `Load skill gotcha` line across all roster agents … out
of scope for this glob-placement decision … opened as its own separate, later
brainstorm." This brief is that separate brainstorm.

The real question is **not** "is there a coverage gap?" but **which
discipline-distribution model is correct** for the roster: blanket-load the full
methodology everywhere, load it into a judgment-bounded subset, or keep the
current per-role inlining model (and, if the latter, document it so it stops
re-surfacing as a phantom gap). This is a **material design decision** (a
roster-wide, policy-level tradeoff with a per-turn token-cost dimension that
bears directly on the framework's own stated goal), so it was surfaced to the
operator to converge before this brief was written.

## Constraints

- **Tier-3 write, operator-only.** `.gleipnir/agents/*.md`,
  `.gleipnir/skills/**`, and `.gleipnir/AGENTS.md` are all Tier-3 (operator-only
  writer, G-1). The brainstorm and plan roles are Tier-0 writers; **only the
  operator may apply any actual edit.** This brief and the subsequent plan
  describe the change; they do not (and cannot) perform it.
- **The framework's own goal is the binding metric.** Per `.gleipnir/AGENTS.md`
  ("Goal reminder") and `stage-role-map.md`, Gleipnir optimizes *quality-efficient
  outcomes per LLM token*, scored by the G-4d cost-per-outcome ledger. A skill
  loaded in Startup is re-injected into that agent's context on **every turn** —
  a permanent, recurring token cost. Any distribution model must be justified
  against this, not against a "more coverage is better" intuition.
- **The model-sizing principle is roster policy.** "Opus only where judgment is
  unbounded (plan); Sonnet once ATLAS + tests bound the work; **Haiku for
  mechanical roles**" (`stage-role-map.md`). Four roles (notify, project-mgr,
  git-ops, session-scribe) are Haiku mechanical roles by deliberate design.
- **GOTCHA's content is largely composition/judgment-oriented and partly
  AETOS-specific.** The full skill (349 lines) is a 6-layer architecture
  (Goals/Orchestration/Tools/Context/Hardprompts/Args) + operating protocol
  (check goals/tools manifests, args) + Memory Protocol + Continuous Improvement
  Loop + a graduated Guardrails list + a Pre-Flight Checklist. Several sections
  are explicitly AETOS-project-scoped (`aetos-memory` MCP, `.aetos/tracker/`,
  `pip install -e ".[mcp]"`, `tools/manifest.md`) and do not map onto Gleipnir's
  bounded roster roles.
- **The relevant GOTCHA slices are already inlined per role (verified).** The
  specific guardrails each narrow role needs are already present in its own agent
  file: notify inlines "verify outputs vs inputs / don't fabricate delivery"
  (notify.md:41–43); git-ops inlines "never rebase pushed history, merge not
  rebase" (git-ops.md:92–93); project-mgr inlines "issues at plan time"
  (project-mgr.md:50–52); session-scribe inlines and *expands* verify-against-disk
  (L-C4/L-C8); gleipnir-plan inlines the GOTCHA pre-flight (plan.md:58);
  orchestrator inlines its sequencing/loop-cap discipline and pins it via
  `compaction_survival`. Even the two agents with the strongest GOTCHA case
  (orchestrator, gleipnir-plan) **inline rather than load** — the roster's
  existing pattern is deliberate, not an omission.
- **Two-way door.** Adding or removing a Startup `Load skill gotcha` line is a
  cheap-to-reverse Tier-3 edit. This lowers stakes and argues against
  over-engineering; it calibrates the analysis toward the minimal change
  consistent with the framework's token goal.

## Approaches Considered

### Approach A: Standardize-for-all (blanket load)

**Summary:** Add `Load skill gotcha` to the Startup of all 9 agents — the 7 that
currently load no skill gain it, and the orchestrator upgrades its prose
reference to a full load.

**Tradeoffs:**
- Pro: uniform — "every agent has the methodology," a single mental model of the
  roster.
- Pro: a future new agent that copies the Startup pattern inherits GOTCHA for free.
- Con (decisive): directly contradicts the framework's **own token-efficiency
  goal** and its **model-sizing principle**. Loading a 349-line 6-layer doc into
  every turn of a 10-step Haiku `notify` role is a permanent per-turn tax for
  content that role cannot use.
- Con: **redundant** — the relevant GOTCHA guardrail is already inlined in each
  narrow role; A pays tokens to duplicate what is already present.
- Con: **content mismatch** — much of GOTCHA (tool/goal manifests, aetos-memory
  MCP, `pip install`, tracker) is inapplicable to the mechanical roles.

**Estimated scope:** ~8 agent files (Tier 3, operator writes). Low edit complexity
but high recurring runtime cost.
**Risk:** medium-high — the risk is not breakage but a permanent, measurable cost
against the exact G-4d scoreboard the framework optimizes, plus normalization of
"load the big doc everywhere," eroding the model-sizing discipline.

### Approach B: Standardize-for-a-judgment-bounded-subset

**Summary:** Add the load line **only** to the agents doing unbounded / multi-step
composing judgment where GOTCHA's *full* framing (not just a single guardrail)
could earn its tokens: `gleipnir-plan` (already runs the GOTCHA pre-flight),
`orchestrator` (Amendment 1 *is* its identity), and `quality-reviewer`
(spec/blast-radius judgment). Leave the four Haiku mechanical roles and
gleipnir-code as-is with their inlined discipline.

**Tradeoffs:**
- Pro: targets only where the full methodology plausibly pays for itself; keeps
  the mechanical roles cheap — consistent with the model-sizing principle.
- Pro: gives those judgment roles a single canonical discipline home rather than
  a hand-inlined slice.
- Con: those roles **already inline the slice they actually use**, so B's marginal
  reach benefit is small while it still adds a per-turn token cost.
- Con: introduces a **second source** (loaded skill vs inlined discipline) for the
  same roles, which can drift out of sync.
- Con: `quality-reviewer` is read-only — most of GOTCHA (tools/manifests/args)
  is irrelevant to it; its judgment is bounded by the spec rubric, weakening its
  inclusion.

**Estimated scope:** 2–3 agent files (Tier 3, operator writes). Low complexity.
**Risk:** medium — modest token cost for modest benefit; the drift-between-two-
sources concern is real.

### Approach C: Leave-as-is by design, documented as intentional policy (SELECTED)

**Summary:** Keep the status quo — each agent inlines the GOTCHA slice relevant to
its bounded role; only `gleipnir-brainstorm` loads the full skill (because it also
loads `brainstorm` + `decision-frameworks` and genuinely uses the whole
methodology framing). Add a short note documenting that this per-role inlining is
**deliberate policy, not a coverage gap**, so the question stops re-surfacing.
The orchestrator **stays prose-reference-only** (does not switch to loading the
full skill).

**Tradeoffs:**
- Pro: the only option fully consistent with the framework's token-efficiency goal
  *and* its model-sizing principle — mechanical roles stay cheap, each role
  carries exactly the discipline it uses.
- Pro: **no redundancy** — avoids paying tokens to duplicate already-inlined
  guardrails; **single effective source per role**, so no skill-vs-inline drift.
- Pro: matches the roster's existing, deliberate pattern (even the strongest-case
  agents inline rather than load).
- Con: without documentation the "1 of 9 loads gotcha" statistic keeps looking
  like a gap and will re-surface. **Fix:** add a concise intentional-policy note
  (location proposed below) so the model is explicit and settled.
- Con (watch item): a *future* new unbounded-judgment agent must remember to inline
  the relevant GOTCHA slice. This is a small, bounded onboarding cost — far below
  A's recurring per-turn tax — and the policy note mitigates it by making the
  model explicit.

**Estimated scope:** 1 documentation file (Tier 3, operator writes) — no functional
agent change. Low complexity.
**Risk:** low — the only real risk (phantom-gap recurrence) is closed by the
documentation note itself.

### Rejected framings

- **"GOTCHA is foundational, therefore every agent must load it."** Foundational
  *to the framework* ≠ needed in every *role's per-turn context*. GOTCHA's own
  layer model locates the methodology in orchestration/planning, not in mechanical
  execution roles. (Handled as Bandwagon bias below.)
- **Treating "1/9" as under-coverage.** The statistic is real but is evidence of a
  deliberate per-role distribution model, not a hole — 7 of the 9 are bounded
  roles whose relevant discipline is already inlined. (Handled as Availability
  bias below.)

## Decision Analysis

**Framework used:** Primary **Second-Order Thinking** — the crux is a downstream
cost/coverage tradeoff (per-turn token tax vs a phantom gap), not a first-order
missing feature. Cross-checked with a **Weighted Decision Matrix** (three distinct
distribution models to compare objectively) and gated up-front by the
**Reversibility Filter** (all options are two-way doors → analysis calibrated to
the framework's own token goal, not exhaustive over-engineering).

**Reversibility:** Two-Way Door. Adding/removing a Startup line is a cheap Tier-3
edit. Lowers stakes; rules out heavyweight treatment; points toward the minimal
change consistent with the token goal.

### Weighted Decision Matrix

Criteria weighted to the framework's own stated goal (quality-efficient outcomes
per token) and its model-sizing principle (Opus/Sonnet where judgment is unbounded;
Haiku for mechanical roles). Cells are score (0–10) × weight.

| Criterion | Weight | A (all 9) | B (subset) | C (leave-as-is, documented) |
|---|---|---|---|---|
| Token efficiency (goal-critical; recurring per-turn cost) | 9 | 2 → 18 | 7 → 63 | 10 → 90 |
| Discipline actually reaches roles that need it | 8 | 8 → 64 | 9 → 72 | 7 → 56 |
| Content fit (GOTCHA relevant to the role's actual work) | 8 | 3 → 24 | 8 → 64 | 9 → 72 |
| Drift resistance (single source vs N Startup lines / two sources) | 6 | 5 → 30 | 5 → 30 | 7 → 42 |
| Consistency with model-sizing principle (Haiku = mechanical) | 7 | 2 → 14 | 9 → 63 | 9 → 63 |
| Avoids redundancy with already-inlined discipline | 6 | 2 → 12 | 7 → 42 | 9 → 54 |
| **Total** | | **162** | **334** | **377** |

**Ranking: C (377) > B (334) ≫ A (162).**

- **A is decisively bottom.** It pays a permanent per-turn token cost for six
  roles that cannot use most of GOTCHA's content, contradicting both the
  framework's goal and its model-sizing principle; and the relevant guardrails
  are already inlined, so the cost buys duplication.
- **C leads** because the roster already practices "inline the applicable slice,"
  deliberately — even `gleipnir-plan` (runs the GOTCHA pre-flight) and
  `orchestrator` (whose identity *is* Amendment 1) inline rather than load. The
  status quo is the model-sizing principle correctly applied, not an accident.
- **B is a legitimate middle** and genuinely stronger than A — it targets only the
  unbounded-judgment roles. Its weakness vs C: those roles already inline what
  they use, so the marginal reach is small while it still adds per-turn tokens and
  a second (skill-vs-inline) source that can drift.

### Second-Order Thinking (the crux)

- **Near-term (A):** every agent "has GOTCHA." **Second-order:** every turn of
  every mechanical role carries hundreds of tokens of unusable methodology → a
  measurable, permanent cost against the G-4d cost-per-outcome ledger.
  **Third-order:** normalizes "load the big doc everywhere," eroding the
  model-sizing discipline that keeps Haiku roles cheap.
- **Near-term (C):** nothing changes at runtime; residual risk that the "gap"
  re-surfaces. **Second-order:** *mitigated by documenting* the inline model as
  intentional — converts a recurring false-gap into settled policy.
  **Third-order (watch item):** a future new unbounded-judgment agent needs its
  GOTCHA slice inlined at authoring time — a small, bounded, one-time cost per new
  agent, far below A's recurring tax.
- **Key insight:** This looks like a coverage gap but is a **distribution-model**
  question, and the framework's own goal (tokens) *and* its own model-sizing
  principle both point away from blanket loading. "1 of 9 loads gotcha" is not
  under-coverage — it is evidence of per-role inlining, the cheaper correct
  pattern for bounded roles.

### Bias checks (12 detectors run; top 3 surfaced)

- ⚠️ **Availability Heuristic (moderate) — on the triggering framing.** The finding
  arrived as a vivid "1 of 9!" statistic, making "standardize for all" feel like
  the natural fix. Base-rate reality: 7 of the 9 are *bounded* roles whose
  discipline is correctly inlined. Judged on content-fit and token base-rates,
  not the memorable ratio.
- ⚠️ **Bandwagon / "foundational-so-everyone" (moderate) — on Approach A.**
  "GOTCHA is core, therefore every agent should load it" is fitness-by-popularity.
  Grounded rebuttal: foundational-to-the-framework ≠ needed-in-every-role's
  context; GOTCHA's own layer model puts the methodology in orchestration/planning,
  not mechanical execution.
- ⚠️ **Status Quo Bias (checked, low) — on Approach C.** C is the incumbent, so it
  got extra scrutiny: "would we choose per-role inlining if starting fresh?" Yes —
  it's the token-cheapest way to give each role exactly its relevant discipline,
  consistent with the model-sizing principle. C wins on merits, not by default.
  Note: this exact question was *deliberately deferred* by the prior
  (glob-guidance-placement) brainstorm to this session, so C is the live question,
  not an un-scrutinized default.

**Checked, not triggered:** Anchoring (A is anchored first in the prompt yet ranks
last — ordering did not drive scores); Confirmation (the genuine pro-load case —
the orchestrator's Amendment-1 tie — was sought and survives only as a point *for
B*, not A); Sunk Cost / IKEA (no prior investment in either model drives the call);
Authority (the prior brainstorm's own Authority-Bias note is instructive — an
earlier operator premise that "gotcha loads unconditionally for every agent" was
grep-falsified; re-verified false this session, so it is not deferred to);
Dunning-Kruger, Survivorship, Recency, Scope-Creep (B draws a principled line and
does not sprawl to "all").

**Recommendation (advisory — the operator decided):** Approach C, with a documented
intentional-policy note; orchestrator stays prose-reference-only. B was the
principled fallback; A not recommended.

## Selected Approach

**Choice: Approach C (operator-converged)** — leave the per-role inlining model
as-is (it is the correct, token-cheap pattern, not an accidental gap), and
**document it as intentional policy** so it stops re-surfacing as a phantom gap.

**Orchestrator load-vs-reference sub-question (operator-converged): the orchestrator
STAYS prose-reference-only.** It continues to *reference* `skills/gotcha/SKILL.md`
(Amendment 1) in prose rather than loading the full skill in Startup. Its
sequencing/loop-cap discipline is already inlined and `compaction_survival`-pinned;
loading the full 6-layer doc every turn would add recurring tokens for content it
already carries in the form it needs. This pairs with C.

**Rationale:** C tops the Weighted Decision Matrix (377), is the only option fully
consistent with the framework's token-efficiency goal *and* its model-sizing
principle, avoids redundancy with already-inlined discipline, and correctly treats
the "1/9" finding as evidence of a deliberate per-role distribution model rather
than under-coverage. A was rejected as a permanent per-turn tax on six roles that
cannot use most of GOTCHA's content; B was a principled fallback but adds a
second, drift-prone source for roles that already inline what they use.

### The ACTION for `gleipnir-plan`: where the intentional-policy documentation should live

Approach C's only concrete change is **documentation** (no functional agent/config
edit). Proposed canonical home, in priority order:

**1. PRIMARY — `.gleipnir/skills/README.md` (a new short subsection).** This is the
best fit and the proposed single source of truth. That file already frames
GOTCHA's inheritance and its "load-bearing point: layer 2 (Orchestration)"; a note
on *who loads GOTCHA and why the roster inlines rather than loads* is the same
content category and belongs beside it. Proposed subsection (exact wording is the
operator's to finalise at Tier-3 write time; this is the converged intent + a
ready-to-apply draft):

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
  (quality-efficient outcomes per token) and its model-sizing principle
  ("Haiku for mechanical roles").
- **Judgment roles also inline, not load.** Even `gleipnir-plan` (runs the GOTCHA
  pre-flight) and the `orchestrator` (whose identity *is* Amendment 1) inline
  their relevant discipline rather than load the whole skill; the orchestrator
  *references* this file in prose deliberately.

So "only 1 of 9 agents loads gotcha" is the expected, correct state — evidence of
per-role inlining, not under-coverage. Do not "fix" it by blanket-adding
`Load skill gotcha` to every agent. (Decided at the roster-gotcha-loading
brainstorm; see `plans/roster-gotcha-loading-brainstorm.md`.)
```

**2. SECONDARY (optional reinforcement, reference-only) — `.gleipnir/AGENTS.md`
"Roster" section.** AGENTS.md already discusses model-sizing and inlined
discipline; a one-line pointer there ("GOTCHA is loaded only by
`gleipnir-brainstorm`; other roles inline their relevant slice by design — see
`skills/README.md`") would reinforce it at the governance level. Per the
drift-resistance discipline from the glob-guidance brief, this must be a
**reference, not a copy** — it points to the skills/README.md canonical note and
does not restate the rationale, so there is one source of truth. This secondary
note is optional; `gleipnir-plan` and the operator may decide it is unnecessary
given the primary note.

**Tier note for `gleipnir-plan`:** both candidate files are Tier-3
(operator-authored). The plan describes the documentation edit(s) and their
verification (e.g. a consistency check that the AGENTS.md pointer, if added, stays
reference-only); the operator applies them. This is a *documentation* change, not
a functional one — no agent frontmatter or Startup section is modified.

## Open Questions

- **One home or two?** PRIMARY (`skills/README.md`) alone, or PRIMARY + the
  optional reference-only pointer in `AGENTS.md`? (Operator/plan to decide; does
  not change the converged approach. Default recommendation: PRIMARY alone keeps
  it simplest and drift-free.)
- **Exact insertion point in `skills/README.md`.** After the "The named deltas"
  section, or immediately after "The load-bearing point: layer 2"? (Anchor choice;
  does not change the approach.)
- **Consistency-test coverage.** If the optional AGENTS.md pointer is added, should
  a consistency check assert it stays reference-only (no duplication of the
  rationale)? Deferred to plan/quality — not a material design decision.
- **Future-agent onboarding (watch item, not a decision now).** When a new
  unbounded-judgment agent is added, its relevant GOTCHA slice must be inlined at
  authoring time. Noted so the policy is applied prospectively; no action required
  under this brief.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Canonical intentional-policy note (PRIMARY) | `.gleipnir/skills/README.md` — new short subsection documenting the per-role inlining model (Tier 3, operator writes) |
| Optional reinforcement pointer (SECONDARY, reference-only) | `.gleipnir/AGENTS.md` — one-line pointer in the Roster section back to the README note (Tier 3, operator writes) |
| Consistency (optional, plan/quality) | consistency check asserting the AGENTS.md pointer, if added, stays reference-only |
| No functional change | No agent frontmatter / Startup section is modified; orchestrator stays prose-reference-only |

**Tier note for `gleipnir-plan`:** the target files are Tier-3 (operator-authored).
The plan describes the documentation edit and its verification; the operator
applies it. Because C's action is documentation (not code/config), a light ATLAS
pass is sufficient — the change is a single-source policy note with an optional
reference-only pointer, both two-way doors.
