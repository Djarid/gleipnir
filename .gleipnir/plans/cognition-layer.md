# Plan: Cognition layer — the AETOS two-gate mechanism, adapted to Gleipnir

_Plan stage output (`gleipnir-plan`). Plans FROM the operator-converged brief
`.gleipnir/plans/cognition-layer-brainstorm.md` — **Approach D with the AETOS
two-gate mechanism as concrete content**. The Selected Approach in that brief is
LOCKED and is not re-decided here; this plan produces the exact, ready-to-apply
Tier-3 edits and their verification. **All edits are operator-applied** — every
target is Tier-3 (`goals/`, `agents/`, `stage-role-map.md`, `decisions/`); no
roster agent (including this planner) writes them. This planner only specifies
diff-shaped text against freshly-read current content (L-C15)._

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Where the design-time gate binds | New **required "Design Principles" section** in `.gleipnir/goals/plan-format.md`, bound to the `plan` stage, adjacent to the existing ATLAS + Decisions-index sections | A new skill file; a per-agent-only instruction | Mirrors how the Decisions-index and ATLAS skeleton already live in `plan-format.md` as enforced artifact-shape (the L-C14 move). `plan-format.md` is the single source the `plan` artifact is validated against; that is where a required section belongs. Operator-converged brief adaptation (a). |
| 2 | **Code-plan vs prose/config-plan split** (brief adaptation (c)) | SOLID/DRY/SRP are **code-plan-only**, gated by **reuse of the track's Axis-1 disqualifier set `X`**: if `P ∩ X ≠ ∅` the plan MUST carry the full SOLID/DRY/SRP analysis; otherwise (prose/config-only, `P ∩ X = ∅`) the section takes the **intent-only form** — a stated **Design Intent** the review-time cross-check verifies — and SOLID/DRY/SRP are attested **`N/A — no executable artifact`**. | Requiring SOLID/DRY of all plans (meaningless for prose); dropping the section entirely for prose plans (loses the genuineness proxy); inventing a *new* prose classifier | There is no class/function/module to analyse for SOLID in a prose plan, but "stated design intent honoured by what was applied" DOES generalise (it is the track's genuineness proxy). Routing MUST be mechanical and reuse the *existing* classifier, not a parallel one — `X` already exists in `stage-role-map.md` Axis 1 and is the exact "produces an executable artifact?" predicate needed. Operator-converged brief adaptation (c). **This plan is itself the live test:** it touches only Tier-3 `.md` files → `P ∩ X = ∅` → intent-only form (see the Design Principles / Design Intent section below). |
| 3 | **Review-time rubric — extend the hardened path, don't parallel it** (brief adaptation (d)) | SOLID/DRY/SRP become an **added checklist dimension folded INTO the existing hardened-path "Blast-radius / false-success" pass** (NOT a third rubric). The **spec-vs-implementation cross-check** becomes a **named sub-check of the existing "Spec-conformance" pass**. AETOS's **`[D]`/`[J]` tags** are adopted as the naming of the *already-required* evidence basis and are **added to the negative-check attestation `evidence` discipline** (`[D]` = deterministic tool output, e.g. `bin/gleipnir-sandbox` lint/test; `[J]` = LLM judgment). | A standalone third "SOLID/DRY" rubric; a parallel `[D]/[J]` mechanism; a separate cognition attestation | The hardened path already runs two non-fusing verdicts (spec-conformance + blast-radius) plus a negative-check attestation with substance/correspondence/post-change-state rules. The brief's adaptation (d) explicitly requires *reusing* this, not standing up a second mechanism. SOLID/DRY *is* blast-radius reasoning; the cross-check *is* spec-conformance. `[D]/[J]` formalises the evidence-basis the substance rule already demands. Minimal composition. |
| 4 | Cross-check severity + effect | **Important** severity: a design-intent divergence **blocks the `git` stage unless explicitly acknowledged by the operator.** "Explicitly acknowledged" = an **operator acknowledgement** whose authoritative home is the durable Tier-3 decision record, NOT the disposable plan (refined by the "Recording an operator acknowledgement" paragraph in Step C below and Stress-test #14; Gleipnir routes material decisions to the operator; the reviewer cannot self-clear it, L-C8). | Critical (over-strong: a divergence is not a crash/security hole); Minor (too weak: it is the genuineness proxy); reviewer-acknowledged (would let the gate clear itself) | Adopts AETOS's exact framing ("Important — blocks merge unless acknowledged", `code-quality-review.md` line 59; `quality-reviewer.md` step 1.5). "Blocks merge" maps to Gleipnir's pipeline as a `quality`-stage verdict that blocks the `git` stage. Acknowledgement must reach the operator because Gleipnir has no "the team" — the operator is the decision authority (brief Constraints; adaptation of AETOS's "acknowledged by the team"). |
| 5 | New guard identifier? Decision record? | **No new guard identifier** (confirms brief Question-4 finding: does NOT amend G-5; lives in the plan-format/artifact-shape + review-rubric layer). **Yes, a durable decision record is warranted** — this is a framework-level methodology change spanning three Tier-3 files. **Named for the operator to author: `.gleipnir/decisions/cognition-layer.md`.** This planner does NOT write it (Tier-3). | Elevating to "G-7" (rejected in the brief's Decision Analysis as over-engineering — a review concern is not an adversary/guard concern); leaving it undocumented (phantom-gap recurrence, the L-C14/gotcha-loading failure) | The brief's matrix ranked the "G-7 guard" option last precisely because cognition-genuineness is not an adversary problem. But a methodology change touching `plan-format.md` + `quality-reviewer` + `stage-role-map.md` must have a durable home so the coverage decision cannot re-surface as a phantom gap (brief Pre-Mortem risk #5). Decision records are Tier-3, operator-authored (`decisions/` is not in this planner's write grant). |
| 6 | **Three-case routing for the design-time gate** (spec-review Finding 2 — refinement of adaptation (c)) | The Gate-1 form is **three cases**, not binary: **(i) OOP/functional code plan** (an `X`-member with class/function/module structure) → full **SOLID + DRY + SRP + Design Intent**; **(ii) executable-but-non-OOP plan** (an `X`-member with no object/function structure — Makefile, `*.mk`, `Containerfile*`, `.github/**` CI YAML, `hooks/**`, `bin/**`, shell script, config-with-shebang) → **DRY + Design Intent**, with **SOLID/SRP attested `N/A — no object/function structure` + a one-line reason**; **(iii) prose/config-only plan** (`P ∩ X = ∅`) → **Design Intent only**, SOLID/DRY/SRP attested `N/A — no executable artifact`. Routing stays mechanical: case (i)-vs-(ii) is "does the touched `X`-member contain class/function/module structure?" (author-declared, reviewer-checkable); case (iii) is `P ∩ X = ∅`. | The original binary code-vs-prose split (forces a Makefile/CI/shell plan into a full SOLID/Liskov/Interface-Segregation analysis with no referent → vacuous boilerplate "N/A, no classes" *inside* the branch meant to carry genuine analysis) | Axis-1's set `X` answers "produces an executable artifact?" (its original purpose: disqualify from the light track), which does NOT coincide with "has OOP structure worth a SOLID analysis" (Decision #2's repurposed use). SOLID/Liskov/Interface-Segregation/SRP need classes/functions/modules; a Makefile/CI-YAML/shell script has none, so forcing them yields a vacuous pass. DRY (duplication) and the Design Intent + cross-check apply to ANY artifact, so they are retained in case (ii). This is a refinement of the LOCKED adaptation (c), not a new mechanism. |
| 7 | **The cross-check is TWO distinct checks across two stages, not one check run twice** (spec-review Finding 3 — coherence of adaptation (d)) | At **spec-review (pre-implementation)** the cross-check is an **intent-quality check**: "is the stated Design Intent itself coherent, specific and non-vacuous?" (the implementation does not exist yet). At **quality (post-implementation)** the cross-check is the **honour check**: "does the applied implementation honour the stated Design Intent?" at **Important/git-blocking** severity. These are two different checks sharing a theme. For a **prose/config-only-track plan** (collapses to a single spec-review pass, no separate post-implementation stage), both fuse into that single pass, run once against the applied edit. | The original wording (cross-check = a single sub-check of "the Spec-conformance pass") which is incoherent for a full-pipeline code plan — "does the implementation honour intent" cannot run at spec-review because code is authored stages later | For an ordinary code plan in the 8-stage pipeline, spec-review precedes code by several stages; the implementation literally does not exist to cross-check. Splitting into intent-quality (pre) + honour (post) makes the binding coherent and ties the pre-check to Finding-1's anti-vacuity rule. Refinement of the LOCKED adaptation (d) — the honour check and its severity are unchanged; only the stage binding is made coherent. |
| 8 | **Anti-vacuity / specificity rule for the Design Intent** (spec-review Finding 1, PRIMARY — closes brief Pre-Mortem risk #1) | The **Design Intent** (and the SRP intent, where present) MUST be a **specific, falsifiable claim about the design** — it must name a concrete responsibility / boundary / constraint the implementation must honour, such that a reviewer can point to an implementation choice that *violates* it. A **generic quality aspiration** ("clean", "correct", "well-structured", "follows best practice", "implement this properly") is **REJECTED at spec-review** exactly as vacuous attestation evidence is rejected under the hardened path's SUBSTANCE rule. Stated in BOTH `plan-format.md` (Gate 1, where the intent is authored) AND `quality-reviewer.md` (Gate 2, where the reviewer must reject a vacuous intent rather than rubber-stamp it). | Requiring only that the intent be "in checkable terms" (the original wording — carries none of the substance/falsifiability teeth, so a vacuous intent trivially "passes" the cross-check → rubber-stamp) | The brief's Pre-Mortem named this risk #1 as "load-bearing, must be a hard non-negotiable requirement, or D collapses into A." Without falsifiability the cross-check is theatre: any implementation "honours" a vacuous intent. Mirrors the hardened path's existing SUBSTANCE rule (concrete/reproducible, not narrative) — reuse, not new machinery. This is the single most important fix. |

---

## Architect

**Problem (one sentence).** Gleipnir structurally requires the *shape* of good
reasoning (ATLAS sections in `plan-format.md`) but nothing verifies the shape
was *genuinely reasoned* rather than perfunctorily filled — so add AETOS's two
gates (a design-time Design Principles section on the plan, and a review-time
SOLID/DRY checklist + spec-vs-implementation cross-check) adapted to Gleipnir's
stages and its prose/config-only track.

**User.** The framework's own pipeline roles — `gleipnir-plan` (must author the
new section), `quality-reviewer` (must run the extended rubric at spec-review
and quality), and the operator (acknowledges divergences, applies all Tier-3
edits). Downstream, the beneficiary is the framework's goal: the "Opus-at-plan
assumes good framing" spend becomes *validated* rather than *assumed*.

**Measurable success criteria.**
1. `plan-format.md` has a new required "Design Principles" section whose
   Validation clause makes its absence block plan completion (mechanically
   detectable, per L-C14 shape enforcement).
2. The section is code-plan-scoped for SOLID/DRY/SRP and intent-only for
   prose/config plans, routed by the **existing** Axis-1 `X` set (no new
   classifier introduced).
3. `quality-reviewer` runs the SOLID/DRY dimension folded into the existing
   blast-radius pass (scoped by the three-case routing), and the cross-check as
   TWO stage-bound checks (intent-quality at spec-review, honour at quality) —
   **with no third rubric and no parallel `[D]/[J]` mechanism**.
4. A design-intent divergence (honour check, at `quality`) is Important-severity,
   blocks the `git` stage unless operator-acknowledged, with the acknowledgement
   recorded in the durable Tier-3 decision record (not the disposable plan).
5. No new guard identifier is introduced; a decision record is *named* for the
   operator (not written by this planner).
6. Every Tier-3 edit is expressed as before/after diff-shaped text against the
   freshly-read current file content.

**Constraints.**
- **Tier-3, operator-only.** This planner writes only this plan file
  (`.gleipnir/plans/**`). All edits below are applied by the operator.
- **Honesty about enforceability.** The mechanical half (section present,
  cross-check performed-and-recorded) is enforceable; the non-mechanical half
  (was the reasoning genuine) is *reviewed*, never claimed as mechanised. This
  plan proposes no mechanised-thinking (brief Constraints; Second-Order insight).
- **Compose, don't duplicate.** The review-time additions extend the existing
  hardened-path machinery (`stage-role-map.md` §"Prose/config-only track") — a
  parallel mechanism is a non-conformance (brief adaptation (d)).
- **Faithful reproduction (L-C15).** AETOS framing questions are faithfully
  adapted/paraphrased from source (compressed to inline form, meaning
  preserved); Gleipnir-specific adaptations (the three-case routing, the
  prose/config split, operator-acknowledgement, the compose-into-hardened-path
  mapping) are marked as adaptations with rationale, because AETOS has no
  prose/config track.

## Trace

**Artifacts and where they live (source of truth).**

| Artifact | File (Tier) | Change | Source authority |
|---|---|---|---|
| Design-time gate (Gate 1) | `.gleipnir/goals/plan-format.md` (T3) | ADD required "Design Principles" section + Validation clause update | AETOS `aetos-plan.md` L79–99 (framing faithfully adapted) |
| Review-time gate (Gate 2) | `.gleipnir/agents/quality-reviewer.md` (T3) | ADD the extended review discipline (checklist dimension + cross-check + `[D]/[J]`) | AETOS `code-quality-review.md` L54–99; `quality-reviewer.md` step 1.5 |
| Track composition + coverage table + guard note | `.gleipnir/stage-role-map.md` (T3) | ADD cross-check-to-track rule, SOLID/DRY code-plan-only gate, per-stage cognition-binding table, guard-vocabulary note, model-sizing linkage | Composes with existing §"Prose/config-only track" (verified current content) |
| Durable decision record | `.gleipnir/decisions/cognition-layer.md` (T3, **NEW**) | Operator authors (NOT this planner) | Named per Decision #5 |

**Integrations map.**
- `plan-format.md` (Gate 1) → `quality-reviewer` (Gate 2) reads the plan's
  Design Principles / Design Intent to run the cross-check in its two forms:
  intent-quality at `spec-review` (is the Design Intent falsifiable?), honour at
  `quality` (was it honoured?) → `quality` verdict gates the `git` stage
  (Decisions #3, #4, #7).
- Gate 2's SOLID/DRY dimension composes INTO `stage-role-map.md`'s hardened-path
  "Blast-radius / false-success" pass; the cross-check composes INTO the
  "Spec-conformance" pass; `[D]/[J]` composes INTO the negative-check
  attestation `evidence` field.
- The code-plan/prose split (Decision #2) **reuses** `stage-role-map.md` Axis 1
  set `X` — the single source of the "produces an executable artifact?"
  predicate. No second classifier.
- Deterministic `[D]` findings come from `bin/gleipnir-sandbox` lint/test output
  where a code plan exists (verified: the sandbox is the S-2 build/test runner
  per `AGENTS.md`); AETOS's `codegraph_quality_scan` MCP tool is **NOT** ported
  (Gleipnir has no such tool — adaptation, see edge cases).

**Edge cases.**
- **Three-case Gate-1 routing (Decision #6).** (i) OOP/functional code →
  SOLID+DRY+SRP+Design Intent; (ii) executable-but-non-OOP (Makefile / CI YAML /
  shell / `bin/**` / `hooks/**` / shebang-config) → DRY+Design Intent, SOLID/SRP
  attested `N/A — no object/function structure`; (iii) prose/config-only
  (`P ∩ X = ∅`) → Design Intent only, SOLID/DRY/SRP `N/A — no executable
  artifact`. *This plan is case (iii).*
- **Vacuous Design Intent (Decision #8, PRIMARY).** A generic quality aspiration
  ("clean", "correct", "well-structured", "follows best practice") is NOT a
  Design Intent and is rejected at spec-review's intent-quality check, exactly
  as vacuous attestation evidence is rejected under the SUBSTANCE rule. Without
  this the cross-check is theatre (brief Pre-Mortem risk #1).
- **No `[D]` provider available** — Gleipnir has no `codegraph`. `[D]` findings
  are limited to whatever `bin/gleipnir-sandbox` lint/test emits for a code
  plan; for prose/config plans there are no `[D]` findings, and the attestation
  `evidence` is `[J]`/grep-based per the existing substance rule. The absence of
  a static-analysis MCP is a documented Gleipnir/AETOS difference, not a gap.
- **Light-path (low-consequence prose) plans** — the cross-check still applies
  (it is the track's genuineness proxy, brief adaptation (c)); it runs inside
  the single fused spec-review pass the light path already collapses to.
  SOLID/DRY/SRP are `N/A` (no executable artifact by construction of the light
  path).
- **Divergence found but operator unavailable** — the `git` stage stays blocked;
  the reviewer cannot self-acknowledge (L-C8). This is the intended fail-closed.
  The acknowledgement, when given, is recorded in the durable decision record
  (Tier-3), not the disposable plan (Decision #4 refinement / minor Finding 5).
- **Cross-check at the wrong stage** — for a full-pipeline code plan the honour
  check CANNOT run at spec-review (the implementation does not exist yet); only
  the intent-quality check runs there. The honour check runs at `quality`
  (Decision #7). For a prose/config-only-track plan both fuse into the single
  collapsed spec-review pass, run once against the applied edit.
- **Section present but the SOLID/DRY analysis is vacuous** — narrowed by the
  three-case routing (case (ii) no longer forces a hollow SOLID pass) and by the
  anti-vacuity rule on the Design Intent. The residual the brief accepts remains:
  presence is mechanical, genuineness is reviewed — the cross-check + substance
  rule bound it, they do not eliminate it.

## Link (validated before building)

- ✅ AETOS Gate-1 content read at source: `aetos-plan.md` L79–99 (SOLID 5
  principles + framing questions; DRY 3 questions; SRP check) — reproduced in
  this plan as a faithful paraphrase (compressed to inline form), not a
  character-for-character copy.
- ✅ AETOS Gate-2 content read: `code-quality-review.md` — 7 categories (L62–72),
  3 severities with pipeline effects (L54–60, Important = "blocks merge unless
  acknowledged"), two-phase `[D]/[J]` workflow (L79–99).
- ✅ AETOS cross-check read: `quality-reviewer.md` step 1.5 (L258–264) — divergence
  from a stated Design Principle flagged Important, blocks merge unless
  explicitly acknowledged.
- ✅ Gleipnir targets read fresh (current content): `plan-format.md` (47 lines),
  `quality-reviewer.md` (55 lines), `stage-role-map.md` (201 lines) incl. the
  ratified §"Prose/config-only track" with Axis-1 set `X`, Axis-2, light/hardened
  paths, two-verdict pattern, negative-check attestation + substance/
  correspondence/post-change-state rules.
- ✅ `decisions/` naming convention confirmed (kebab-case topic names) →
  `cognition-layer.md` fits.
- ✅ Confirmed: `bin/gleipnir-sandbox` is the S-2 build/test runner (AGENTS.md
  G-2 row) — the natural `[D]` source for code plans; Gleipnir has no
  `codegraph`-equivalent MCP (so AETOS's provider registry is not ported).
- ✅ Confirmed this plan's own routing: `P` = {four `.md` Tier-3 files} → none in
  `X` → `P ∩ X = ∅` → prose/config-only, intent-only Design Principles form.
  (Routes hardened via Axis 2(a): `agents/**`, `stage-role-map.md`, and — for
  `plan-format.md` — Axis 2(b) grant patterns are absent but the plan edits the
  binding tables in `stage-role-map.md`, so hardened path applies.)

## Assemble (build order — all steps operator-applied)

1. **Step A — `plan-format.md`** (Gate 1): add the required "Design Principles"
   section + update the Validation clause. Do this first: it defines the
   artifact shape the reviewer (Step B) checks against.
2. **Step B — `quality-reviewer.md`** (Gate 2): add the extended review
   discipline that consumes the Step-A section. Second, because it references
   the shape Step A creates.
3. **Step C — `stage-role-map.md`**: add the code-plan/prose split rule
   (Decision #2, reusing `X`), the hardened-path composition note (Decision #3),
   the cross-check severity/effect (Decision #4), the per-stage cognition-binding
   table, the guard-vocabulary note (Decision #5), and the model-sizing linkage.
   Third, because it ties Steps A and B together and documents the coverage.
4. **Step D — operator authors `.gleipnir/decisions/cognition-layer.md`**
   (Decision #5): the durable record. Named here, NOT written by any agent.

---

## The exact Tier-3 edits (diff-shaped, against freshly-read current content)

### Step A — `.gleipnir/goals/plan-format.md`

**A.1 — Add a new required section (renumber nothing; append after item 7).**
Current items 1–7 end at line 31 (Execution Workflow). Insert a new **item 8**
before the "## Persistence and lifecycle" heading (line 33).

> **BEFORE** (lines 30–33):
> ```
> 7. **Execution Workflow** — enough for an implementing agent to act without
>    rediscovering the protocol. A plan without this section is incomplete.
>
> ## Persistence and lifecycle
> ```
>
> **AFTER:**
> ```
> 7. **Execution Workflow** — enough for an implementing agent to act without
>    rediscovering the protocol. A plan without this section is incomplete.
> 8. **Design Principles** — the design-time cognition gate (AETOS Gate 1;
>    adapted). Its form is routed in THREE cases (not binary), keyed on the SAME
>    Axis-1 disqualifier set `X` the prose/config-only track uses
>    (`../stage-role-map.md`) — there is ONE "produces executable artifact?"
>    predicate (`X`), refined by one author-declared, reviewer-checkable
>    sub-question ("does the touched `X`-member have class/function/module
>    structure?"):
>    - **(i) OOP/functional code plan** (`P ∩ X ≠ ∅` AND a touched `X`-member has
>      class/function/module structure): all three named sub-analyses, evaluated
>      against the proposed design (framing questions faithfully adapted from
>      AETOS `aetos-plan.md` L84–99):
>      - **SOLID analysis** — Single Responsibility (does each proposed
>        function/class have exactly one reason to change?), Open/Closed (can the
>        design be extended without modifying existing code?), Liskov Substitution
>        (do proposed subclasses/implementations respect their parent contracts?),
>        Interface Segregation (are proposed interfaces narrow and focused?),
>        Dependency Inversion (are high-level modules decoupled from low-level
>        implementation details?).
>      - **DRY analysis** — is any logic duplicated across files/functions? are
>        there existing helpers to reuse instead of reimplementing? are
>        constants/config values repeated without a named reference?
>      - **Single Responsibility check** — explicitly name the single
>        responsibility of each new module/class/function; if a component has
>        more than one, split it.
>      - **Design Intent** (also required here) — see the specificity rule below.
>    - **(ii) Executable-but-non-OOP plan** (`P ∩ X ≠ ∅` but the touched
>      `X`-member has NO object/function structure — a Makefile, `*.mk`,
>      `Containerfile*`, `.github/**` CI YAML, `hooks/**`, `bin/**` script, shell
>      script, or config-with-a-shebang): **DRY analysis + Design Intent** apply
>      (duplication and stated-intent are meaningful for any artifact); **SOLID
>      and the class/module SRP are attested `N/A — no object/function structure`
>      with a one-line reason** (there is no class/function/interface for a
>      Liskov / Interface-Segregation / Dependency-Inversion / SRP analysis).
>      [GLEIPNIR ADAPTATION: AETOS applies SOLID uniformly to code; Gleipnir
>      splits case (ii) out because Axis-1's `X` answers "produces an executable
>      artifact?" — NOT "has OOP structure worth a SOLID analysis" — and the two
>      do not always coincide. Forcing SOLID onto a Makefile yields a vacuous
>      "N/A, no classes" *inside* the analysis branch, so it is routed to an
>      explicit attested N/A instead.]
>    - **(iii) Prose/config-only plan** (`P ∩ X = ∅` — no executable artifact):
>      SOLID/DRY/SRP do not apply (there is no class/function/module to analyse)
>      and are attested **`N/A — no executable artifact`**. In their place, state
>      a **Design Intent** (below). This is the artifact the review-time
>      spec-vs-implementation cross-check verifies (the track's genuineness
>      proxy). [GLEIPNIR ADAPTATION: AETOS has no prose/config track, so this
>      case is Gleipnir-specific; rationale — SOLID is meaningless without code,
>      but "was the stated intent honoured?" generalises.]
>
>    **Design Intent — specificity / anti-vacuity rule (REQUIRED in all three
>    cases; the load-bearing genuineness proxy).** The Design Intent (and, in
>    case (i), the Single-Responsibility statement) MUST be a **specific,
>    falsifiable claim about the design**: it must name a concrete
>    responsibility, boundary, or constraint the implementation must honour, such
>    that a reviewer could point to an implementation choice that *violates* it. A
>    **generic quality aspiration** — "clean", "correct", "well-structured",
>    "follows best practice", "implement this properly", or the like — is NOT a
>    Design Intent and MUST be rejected at spec-review, exactly as the hardened
>    path's SUBSTANCE rule (`../stage-role-map.md`) rejects narrative,
>    non-reproducible attestation evidence. A non-falsifiable intent makes the
>    cross-check trivially pass ("any implementation honours it") and collapses
>    the whole gate into theatre; this rule is a hard, non-negotiable requirement,
>    not advisory. [GLEIPNIR ADAPTATION: mirrors the existing hardened-path
>    SUBSTANCE rule; closes the brainstorm's Pre-Mortem risk #1 (rubber-stamp).]
>
> ## Persistence and lifecycle
> ```

**A.2 — Update the Validation clause** (current lines 42–47) so the new section
is required for completion.

> **BEFORE** (lines 42–47):
> ```
> A plan is complete when every section above is present (including the
> **Decisions (index)** table), the Stress-test section lists concrete, checkable
> acceptance criteria (not "it works"), and every path/artifact the plan cites has
> been confirmed to exist (or is explicitly marked as to-be-created) — never cite
> a file as existing without verifying it (L-C15).
> ```
>
> **AFTER:**
> ```
> A plan is complete when every section above is present (including the
> **Decisions (index)** table and the **Design Principles** section — in whichever
> of its three case-forms applies: (i) OOP/functional code → SOLID+DRY+SRP+Design
> Intent; (ii) executable-but-non-OOP → DRY+Design Intent, SOLID/SRP attested
> `N/A — no object/function structure`; (iii) prose/config-only (`P ∩ X = ∅`) →
> Design Intent only, SOLID/DRY/SRP attested `N/A — no executable artifact`), the
> Stress-test section lists concrete, checkable acceptance criteria (not "it
> works"), and every path/artifact the plan cites has been confirmed to exist
> (or is explicitly marked as to-be-created) — never cite a file as existing
> without verifying it (L-C15). A missing Design Principles section — or a
> Design Intent that is a generic quality aspiration rather than a specific,
> falsifiable claim (see the anti-vacuity rule) — is an incomplete plan, the same
> way a missing ATLAS section is (L-C14: move the good practice from habit into
> the enforced artifact-shape).
> ```

### Step B — `.gleipnir/agents/quality-reviewer.md`

**B.1 — Extend the "Discipline" section** (current lines 40–46) with the Gate-2
review discipline. Insert a new subsection after the existing Discipline
bullets, before "## Always end with a written report".

> **BEFORE** (lines 46–48):
> ```
> - Never edit anything under `.gleipnir/`.
>
> ## Always end with a written report (never return empty)
> ```
>
> **AFTER:**
> ```
> - Never edit anything under `.gleipnir/`.
>
> ## Cognition review (AETOS Gate 2, adapted — COMPOSES with the hardened path)
>
> This EXTENDS the existing hardened-path machinery in
> `../stage-role-map.md` §"Prose/config-only track"; it does NOT add a parallel
> mechanism. Concretely:
>
> - **SOLID/DRY/SRP is a checklist DIMENSION folded INTO the hardened path's
>   existing "Blast-radius / false-success" pass** — NOT a third rubric. Scope it
>   by the Gate-1 three-case routing: for an **(i) OOP/functional code plan**,
>   work the AETOS 7 categories against each changed implementation file (skip
>   test files): SOLID, DRY, naming/readability/maintainability, error handling,
>   architecture, performance anti-patterns, security. For an **(ii)
>   executable-but-non-OOP plan** (Makefile / CI YAML / shell / `bin/**` /
>   `hooks/**` / config-with-shebang) apply the **DRY** dimension only and accept
>   the attested `N/A — no object/function structure` for SOLID/SRP. For a
>   **(iii) prose/config-only plan** (`P ∩ X = ∅`) SOLID/DRY/SRP are `N/A` and
>   this dimension is skipped. **SOLID/DRY violations are Important severity —
>   they block the `git` stage unless the operator acknowledges them** (AETOS
>   `code-quality-review.md` L59).
> - **The spec-vs-implementation cross-check is TWO distinct checks, bound to two
>   stages — not one check run twice** (AETOS `quality-reviewer.md` step 1.5,
>   adapted for Gleipnir's multi-stage pipeline where the implementation does not
>   exist yet at spec-review):
>   - **At `spec-review` (pre-implementation) — the intent-quality check.** The
>     implementation does not exist yet, so you canNOT check honour. Instead check
>     the **Design Intent itself**: is it a specific, falsifiable claim (names a
>     concrete responsibility / boundary / constraint), or a generic quality
>     aspiration? A vacuous Design Intent ("clean", "correct", "well-structured",
>     "follows best practice") MUST be flagged and rejected here — do NOT
>     rubber-stamp it — exactly as you reject narrative, non-reproducible
>     attestation evidence under the SUBSTANCE rule. This is a spec-conformance
>     finding (the plan is not complete until its Design Intent is falsifiable).
>   - **At `quality` (post-implementation) — the honour check.** Read the plan's
>     Design Principles / Design Intent, then check what was applied against the
>     stated intent. A divergence from a stated design principle or Design Intent
>     is flagged **Important — it blocks the `git` stage unless explicitly
>     acknowledged by the OPERATOR** (never self-cleared by you, L-C8; the
>     operator is Gleipnir's decision authority, replacing AETOS's "the team").
>   - **For a prose/config-only-track plan** (which collapses to a single
>     spec-review pass, with no separate post-implementation stage), both checks
>     run once at that single pass, against the applied edit: reject a vacuous
>     Design Intent, then check the applied edit honours it.
>   The cross-check (in one or both of its forms) applies to EVERY plan,
>   including prose/config-only and light-path plans — it is the genuineness
>   proxy for the un-mechanisable "was the reasoning real?" question.
> - **`[D]`/`[J]` tags formalise the evidence basis the hardened path already
>   requires.** Tag every finding and every negative-check attestation `evidence`
>   entry: `[D]` = deterministic (a tool produced it — e.g. `bin/gleipnir-sandbox`
>   lint/test output for a code plan), `[J]` = judgment (your reasoning). This is
>   the naming of the existing substance rule's "concrete reproducible artifact
>   vs narrative" distinction, not a new mechanism. Gleipnir has no
>   `codegraph`-style static-analysis MCP, so `[D]` findings come only from the
>   sandbox where a code plan exists; prose/config plans have `[J]`/grep-based
>   evidence only. [GLEIPNIR ADAPTATION: AETOS routes `[D]` through a provider
>   registry MCP that Gleipnir does not have; the tag semantics are adopted, the
>   provider registry is not.]
>
> ## Always end with a written report (never return empty)
> ```

### Step C — `.gleipnir/stage-role-map.md`

**C.1 — Add the cognition-layer composition rules to the hardened-path section.**
Append a new subsection at the END of the file (after the current line-194–201
SUCCESS-gate paragraph), so it sits with the machinery it composes into.

> **AFTER** the current final paragraph (line 201), append:
> ```
>
> ### Cognition layer (AETOS two-gate mechanism — composed, not parallel)
>
> **Status: authored, operator-applied. See `decisions/cognition-layer.md`.**
> The cognition layer verifies reasoning was actually done. It is realised as
> two gates and COMPOSES with the machinery above — it adds no new guard and
> does NOT amend G-5 (it lives in the plan-format artifact-shape layer + this
> review-rubric layer).
>
> - **Gate 1 (design-time)** is the required **Design Principles** section in
>   `goals/plan-format.md`. Its form is routed in THREE cases, keyed on the SAME
>   Axis-1 set `X` above plus one author-declared/reviewer-checkable sub-question
>   ("does the touched `X`-member have class/function/module structure?"):
>   (i) OOP/functional code (`P ∩ X ≠ ∅`, has OOP structure) → SOLID+DRY+SRP+
>   Design Intent; (ii) executable-but-non-OOP (`P ∩ X ≠ ∅`, a Makefile / CI
>   YAML / shell / `bin/**` / `hooks/**` / shebang-config) → DRY+Design Intent,
>   SOLID/SRP attested `N/A — no object/function structure`; (iii)
>   prose/config-only (`P ∩ X = ∅`) → Design Intent only, SOLID/DRY/SRP attested
>   `N/A — no executable artifact`. ONE predicate (`X`), one refinement — no
>   second classifier. The **Design Intent MUST be specific and falsifiable** (a
>   named responsibility/boundary/constraint, not a generic quality aspiration),
>   per the anti-vacuity rule mirroring the SUBSTANCE rule above.
> - **Gate 2 (review-time)** composes into THIS section's two passes, not as new
>   passes:
>   - SOLID/DRY/SRP is a checklist **dimension of the "Blast-radius /
>     false-success" pass** (2), Important severity, scoped by the Gate-1
>     three-case routing (full SOLID/DRY for case (i); DRY-only for case (ii);
>     skipped for case (iii)).
>   - The **spec-vs-implementation cross-check is TWO distinct checks bound to
>     two stages** (the implementation does not exist at spec-review):
>     - at **spec-review** it is the **intent-quality check** — a **sub-check of
>       the "Spec-conformance" pass** (1) verifying the Design Intent is itself
>       specific/falsifiable and not a vacuous aspiration (rejected if vacuous,
>       ties to the anti-vacuity rule);
>     - at **quality** it is the **honour check** — does the applied
>       implementation honour the stated Design Intent/principle? A divergence is
>       **Important** severity: it **blocks the `git` stage unless explicitly
>       acknowledged by the operator** (the reviewer never self-clears it, L-C8).
>     For a prose/config-only-track plan (single collapsed spec-review pass, no
>     separate post-implementation stage) both checks run once at that pass
>     against the applied edit. The cross-check applies to EVERY plan including
>     light-path plans (it is the genuineness proxy).
>   - **`[D]`/`[J]` tags** annotate the evidence basis of every finding and every
>     negative-check attestation `evidence` entry (`[D]` = tool-produced, e.g.
>     `bin/gleipnir-sandbox`; `[J]` = judgment). This formalises the existing
>     substance rule; it is not a second mechanism.
>
> **Recording an operator acknowledgement.** A divergence found at `quality` is
> Important and blocks `git` until the operator acknowledges it. Because plans
> are Tier-0 and disposable, the acknowledgement is NOT recorded only in the
> plan: the divergence escalates to the operator, who records the accepted
> divergence in the durable decision record (`decisions/cognition-layer.md` or
> the change's own decision record). The disposable plan may note it, but the
> authoritative home is the Tier-3 decision record.
>
> #### Per-stage cognition binding (coverage — Approach D's documented half)
>
> Every artifact-producing stage's cognition is either an enforced shape or an
> explicitly-documented existing binding, so the coverage question cannot
> re-surface as a phantom gap (L-C14; the gotcha-loading precedent):
>
> | Stage | Cognition binding | Enforced by |
> |---|---|---|
> | brainstorm | Clarify → Explore → Propose → Converge + `## Decision Analysis` | `skills/brainstorm` shape + precept-10 gate |
> | plan | ATLAS sections + Decisions index + **Design Principles** | `goals/plan-format.md` Validation (Gate 1) |
> | spec-review | Spec-conformance pass **incl. the cross-check's intent-quality sub-check** (Design Intent is specific/falsifiable, not vacuous) | this section (Gate 2) |
> | test | The pre-written test IS the correctness shape | test-first pipeline (Axiom 1) — bounded, no new shape |
> | code | Bounded by plan + ATLAS-Assemble order + pre-written test | the test is the arbiter — bounded, no new shape |
> | quality | Blast-radius pass **incl. SOLID/DRY dimension** + the cross-check's **honour check** (applied impl. honours stated intent) | this section (Gate 2) |
>
> `test` and `code` intentionally carry NO new cognitive shape: their cognition
> is already bounded by the pre-written test (documenting the existing binding,
> per Approach D — NOT inventing a redundant shape).
>
> #### Guard-vocabulary note
>
> Cognition-genuineness is a plan-format-shape + review-rubric concern. It is
> **NOT a new guard** and does **NOT amend G-5**: no adversary forges a reasoning
> process (the G-1..G-6 guards each close an adversarial hole); a busy LLM fills
> a section perfunctorily, which is a quality concern answered by review, not by
> a guard. Its only mechanically-enforceable part (shape presence) is already
> the `plan-format.md` Validation + G-5 completion edge; its non-mechanical part
> (genuineness) is irreducibly review — the cross-check is its enforceable proxy.
>
> #### Model-sizing linkage
>
> The cross-check is what makes the "Opus-at-plan assumes good framing" spend
> (see "Model-sizing principle" above) *safe* rather than merely *assumed*: it
> converts "we assume the framing is good" into "framing genuineness is an
> explicit, recorded review obligation whose divergences block the git stage."
> ```

### Step D — `.gleipnir/decisions/cognition-layer.md` (operator authors — NOT this planner)

**Named for the operator (Decision #5). This planner does NOT write it** (Tier-3
is operator-only). Suggested content skeleton for the operator: the converged
Approach-D-with-AETOS-mechanism decision; the code/prose split rule (Decision
#2); the compose-into-hardened-path mapping (Decision #3); the
Important/operator-acknowledged cross-check effect (Decision #4); and the
explicit "no new guard, does not amend G-5" ruling (Decision #5), so the
recategorisation-as-G-7 question is pre-empted in a durable home.

---

## Stress-test (acceptance checks the result is validated against)

1. **Gate-1 presence is enforced.** After Step A, `plan-format.md` item 8
   exists and its Validation clause names Design Principles as completion-
   blocking. Check: `grep -n "Design Principles" .gleipnir/goals/plan-format.md`
   returns both the section and the Validation reference.
2. **Code/prose split reuses `X`, not a new classifier.** The Design Principles
   section and the `stage-role-map.md` Gate-1 note both reference the Axis-1 set
   `X` by name; no new "is this a code plan?" predicate is defined anywhere.
   Check: `grep -n "P ∩ X" .gleipnir/goals/plan-format.md .gleipnir/stage-role-map.md`
   shows the same predicate in both; `grep` finds no second disqualifier list.
3. **SOLID framing is a faithful adaptation of AETOS.** The five SOLID framing
   questions in Step A preserve the meaning of `aetos-plan.md` L84–89
   (Single Responsibility, Open/Closed, Liskov, Interface Segregation,
   Dependency Inversion), compressed to inline form — a faithful paraphrase, not
   a character-for-character copy. No principle is dropped, added, or softened.
4. **No third rubric.** After Step B/C, `quality-reviewer.md` and
   `stage-role-map.md` describe SOLID/DRY as a *dimension of* the existing
   blast-radius pass and the cross-check as a *sub-check of* the existing
   spec-conformance pass — NOT as new passes. Check: the hardened path still
   lists exactly two passes (1. Spec-conformance, 2. Blast-radius/false-success);
   no "3." pass is added.
5. **No parallel `[D]/[J]` mechanism.** `[D]/[J]` is described as annotating the
   *existing* negative-check attestation `evidence` field and findings, with no
   new attestation schema and no ported provider-registry MCP.
6. **Cross-check severity + effect.** A design-intent divergence is Important
   and blocks the `git` stage unless operator-acknowledged; the reviewer cannot
   self-clear (L-C8 preserved).
7. **No new guard.** No "G-7" (or any new G-n) token is introduced; the
   guard-vocabulary note explicitly states it is not a guard and does not amend
   G-5. Check: `grep -n "G-7" .gleipnir/**` returns nothing.
8. **Coverage table covers every artifact-producing stage.** The per-stage
   cognition table lists every artifact-producing stage in `stage-role-map.md`
   §"The map" (brainstorm, plan, spec-review, test, code, quality) with no
   drift; `git` and `gate` are correctly omitted (they produce no cognitive
   artifact) — Pre-Mortem risk #4.
9. **Decision record named, not written by an agent.** `decisions/cognition-layer.md`
   appears in this plan as operator-to-author; no agent write touches
   `decisions/`.
10. **This plan is a valid live test of Decision #2/#6.** This plan touches only
    Tier-3 `.md` files (`P ∩ X = ∅`), so it carries the intent-only Design
    Principles form (below, case (iii)) and attests SOLID/DRY/SRP `N/A` —
    demonstrating the prose/config branch it designs.
11. **Three-case routing is mechanically stated (Decision #6).** `plan-format.md`
    item 8 and the `stage-role-map.md` Gate-1 note both enumerate exactly three
    cases keyed on `X` + the OOP-structure sub-question; case (ii) attests
    SOLID/SRP `N/A — no object/function structure` while retaining DRY + Design
    Intent. Check: `grep -n "no object/function structure"` finds the case-(ii)
    attestation in both files.
12. **Cross-check is two stage-bound checks (Decision #7).** `quality-reviewer.md`
    and `stage-role-map.md` bind the intent-quality check to `spec-review` and
    the honour check to `quality`; no wording places the honour check at
    spec-review for a full-pipeline code plan. Check: the per-stage table's
    spec-review row reads "intent-quality" and its quality row reads "honour".
13. **Design Intent anti-vacuity rule is present and hard (Decision #8).** Both
    `plan-format.md` and `quality-reviewer.md` require the Design Intent be a
    specific, falsifiable claim and direct rejection of a generic aspiration.
    Check: `grep -n "falsifiable"` and `grep -n "follows best practice"` (the
    rejected-example list) appear in both files; the rule is stated as
    non-negotiable, not advisory.
14. **Acknowledgement has a durable home (minor Finding 5).** The
    operator-acknowledgement of a `quality` divergence is recorded in the Tier-3
    decision record, not the disposable plan. Check: `stage-role-map.md`'s
    "Recording an operator acknowledgement" paragraph names the decision record
    as the authoritative home.

---

## Design Principles (this plan — intent-only form, per Decision #2)

**This plan's touched-path set** `P` = { `.gleipnir/goals/plan-format.md`,
`.gleipnir/agents/quality-reviewer.md`, `.gleipnir/stage-role-map.md`,
`.gleipnir/decisions/cognition-layer.md` } — all Tier-3 `.md` files. **`P ∩ X = ∅`**
(none are under `src/`, `tests/`, `bin/`, `hooks/`, no Makefile/CI/shebang/`+x`,
no standalone YAML). Therefore this is a **prose/config-only plan** and the
Design Principles section takes the **intent-only form**:

- **SOLID analysis:** `N/A — no executable artifact.` (No class/function/module
  is produced; SOLID has nothing to analyse.)
- **DRY analysis:** `N/A — no executable artifact.` (But note, as a prose-DRY
  observation informing the design: the SAME Axis-1 set `X` is reused for the
  code/prose split rather than duplicating a classifier — Decision #2 — and the
  review additions COMPOSE into the existing hardened-path passes rather than
  duplicating rubric machinery — Decision #3. Non-duplication was a first-order
  design constraint here, which is why it is called out even though formal DRY
  is N/A.)
- **Single Responsibility check:** `N/A — no executable artifact.`
- **Design Intent (the checkable proxy the review cross-check verifies):**
  1. *Gate 1 binds where the shape already lives.* Add ONE required section to
     `plan-format.md`; do not create a new skill or a parallel classifier.
  2. *Gate 2 composes, never parallels.* SOLID/DRY = a dimension of the existing
     blast-radius pass; cross-check = a sub-check of the existing spec-conformance
     pass; `[D]/[J]` = annotation of the existing attestation evidence. If the
     applied edits stand up a third rubric or a second attestation schema, the
     intent was NOT honoured (a dispositive Important divergence).
  3. *No mechanised thinking, no new guard.* The applied edits must state the
     non-mechanical half is reviewed (not enforced) and that this is not a guard
     and does not amend G-5. If an applied edit introduces a "G-7" or claims to
     make reasoning deterministic, the intent was NOT honoured.
  4. *Faithful AETOS reproduction.* SOLID/DRY/SRP framing questions are a
     faithful paraphrase of `aetos-plan.md` (meaning preserved, no principle
     dropped/added/softened); every Gleipnir-specific deviation (the three-case
     routing, the prose/config split, operator-acknowledgement,
     compose-into-hardened-path) is marked as an adaptation with rationale. An
     unmarked deviation or a softened/invented rubric line is NOT honoured.
  5. *Gate-1 routing is three cases, not binary (Decision #6).* An
     executable-but-non-OOP plan (Makefile/CI/shell) MUST reach the
     DRY+Design-Intent form with SOLID/SRP attested `N/A — no object/function
     structure`, NOT be forced through a full SOLID branch. If an applied edit
     forces a Makefile-only plan into a SOLID/Liskov analysis, the intent was
     NOT honoured.
  6. *The cross-check is two stage-bound checks (Decision #7).* The applied
     `quality-reviewer.md` MUST bind the intent-quality check to `spec-review`
     and the honour check to `quality`; if an applied edit places the honour
     check ("implementation honours intent") at spec-review for a full-pipeline
     code plan (where no implementation exists yet), the intent was NOT honoured.
  7. *The Design Intent anti-vacuity rule is a hard requirement (Decision #8).*
     Both `plan-format.md` and `quality-reviewer.md` MUST require the Design
     Intent be a specific, falsifiable claim and MUST direct rejection of a
     generic aspiration. If an applied edit states the intent need only be "in
     checkable terms" without the falsifiability/rejection teeth, the intent was
     NOT honoured (this fix would have regressed).

*(This section is itself the live test named in Stress-test #10: a prose/config
plan producing the intent-only form the plan designs. Its Design Intents are
themselves specific/falsifiable — each names an implementation choice that would
violate it — exemplifying the anti-vacuity rule the plan now mandates.)*

---

## Execution Workflow

**Routing (mechanical, per `stage-role-map.md`).** This plan is
enforcement-bearing: `P` includes `.gleipnir/agents/quality-reviewer.md` and
`.gleipnir/stage-role-map.md` (Axis 2(a) enforcement paths) and edits this
file's binding tables (Axis 2(b)). So even though `P ∩ X = ∅` (track-eligible,
no executable artifact), it routes to the **HARDENED path**, NOT the light path.

**Spec-review therefore runs the hardened path in full:**
1. **Spec-conformance pass** (`SPEC-CONFORM: PASS/FAIL`) — including the new
   cross-check sub-check this plan designs, verifying the applied edits honour
   the Design Intent above.
2. **Blast-radius / false-success pass** — adversarial: could these edits be
   wrongly green? (e.g. did SOLID/DRY quietly become a third rubric? did a
   parallel `[D]/[J]` schema sneak in? was `X` duplicated?)
3. **Negative-check attestation** — one row per enforcement change, produced by
   `quality-reviewer` (`attested_by ≠ author`, L-C8), with `[D]/[J]`-tagged
   `evidence` obeying the substance / correspondence / post-change-state rules.
   Example rows the reviewer must produce against the **applied** files:
   - *Grant/edit:* `plan-format.md` item 8 added. *Over-broad form checked:* the
     section does NOT require SOLID/DRY of prose/config plans (would break the
     track). *Evidence `[J]`:* `grep -n "N/A — no executable artifact"
     .gleipnir/goals/plan-format.md` shows the prose branch present.
     *Negative result:* an unconditional SOLID-required line is NOT present.
   - *Grant/edit:* `quality-reviewer.md` cognition subsection. *Over-broad form
     checked:* no THIRD rubric / no new pass introduced. *Evidence `[J]`:*
     `grep -n "third rubric\|3\. " .gleipnir/agents/quality-reviewer.md` and the
     hardened-path section still lists exactly two passes. *Negative result:* a
     "3." pass is NOT present.
   - *Grant/edit:* `stage-role-map.md` guard-vocabulary note. *Over-broad form
     checked:* no new guard token. *Evidence `[J]`:* `grep -n "G-7"
     .gleipnir/stage-role-map.md` returns empty. *Negative result:* `G-7` is NOT
     present.

**Tier discipline.** All four steps (A–D) are Tier-3 and **operator-applied**.
No roster agent — including `gleipnir-code` and this planner — writes them. The
planner's role ends at this plan file (`.gleipnir/plans/**`). The operator
applies A–C and authors D; `quality-reviewer` runs the hardened spec-review
against the applied state.

**Stop-and-flag (per the planner's boundary).** No new material tradeoff was
discovered that requires re-convergence: Decisions #1–#5 are all direct
instantiations of the LOCKED converged brief (Approach D + AETOS mechanism +
the four required adaptations). One **AETOS-vs-Gleipnir difference** was found
and resolved *within* the brief's adaptation (d), NOT escalated as a new
decision: AETOS's `[D]` findings flow from a `codegraph_quality_scan` MCP /
provider registry that **Gleipnir does not have**. Resolution: adopt the
`[D]/[J]` *tag semantics* (they formalise the existing substance rule) but do
NOT port the provider-registry MCP — `[D]` findings come from
`bin/gleipnir-sandbox` for code plans, and prose/config plans have `[J]`/grep
evidence only. This is a faithful adaptation, not a softening, and is marked as
such in Steps B and C. If the operator judges a static-analysis provider worth
building, that is a *separate* future plan, not part of this one.
