# Goal: Plan Format

**Kind:** artifact/format goal (not sequencing). Legitimate goals-content now.

Every plan written to disk must follow this structure. Writing a plan file IS
planning; it is never blocked by read-only or plan mode, and is never deferred
(inherited ATLAS/GOTCHA discipline).

## Required sections

A plan is an ATLAS brief. It must contain:

1. **Decisions (index)** — a scannable table summarising every material/notable
   decision the plan fixes, in the order encountered. Columns:
   `# | Decision | Chosen | Rejected | Rationale`. This is a summary/index near
   the top; the full reasoning for each row lives in the sections below (a row
   is not a substitute for the prose that justifies it). One row per decision —
   including operator-converged decisions (cite the convergence), decisions made
   during planning/spec-review, and any material tradeoff surfaced. (Required
   because it was repeatedly dropped and retrofitted only when the operator
   caught it — see lessons L-C14: a good practice that lives only in habit
   erodes; move it into the enforced format.)
2. **Architect** — problem (one sentence), user, measurable success criteria,
   constraints.
3. **Trace** — artifacts and where they live (source of truth), integrations
   map, edge cases.
4. **Link** — what was validated before building (connections, tools, inputs).
5. **Assemble** — intended build order.
6. **Stress-test** — the acceptance checks the result will be validated against.
7. **Execution Workflow** — enough for an implementing agent to act without
   rediscovering the protocol. A plan without this section is incomplete.
8. **Design Principles** — the design-time cognition gate (AETOS Gate 1;
   adapted). Its form is routed in THREE cases (not binary), keyed on the SAME
   Axis-1 disqualifier set `X` the prose/config-only track uses
   (`../stage-role-map.md`) — there is ONE "produces executable artifact?"
   predicate (`X`), refined by one author-declared, reviewer-checkable
   sub-question ("does the touched `X`-member have class/function/module
   structure?"):
   - **(i) OOP/functional code plan** (`P ∩ X ≠ ∅` AND a touched `X`-member has
     class/function/module structure): all three named sub-analyses, evaluated
     against the proposed design (framing questions faithfully adapted from
     AETOS `aetos-plan.md` L84–99):
     - **SOLID analysis** — Single Responsibility (does each proposed
       function/class have exactly one reason to change?), Open/Closed (can the
       design be extended without modifying existing code?), Liskov Substitution
       (do proposed subclasses/implementations respect their parent contracts?),
       Interface Segregation (are proposed interfaces narrow and focused?),
       Dependency Inversion (are high-level modules decoupled from low-level
       implementation details?).
     - **DRY analysis** — is any logic duplicated across files/functions? are
       there existing helpers to reuse instead of reimplementing? are
       constants/config values repeated without a named reference?
     - **Single Responsibility check** — explicitly name the single
       responsibility of each new module/class/function; if a component has
       more than one, split it.
     - **Design Intent** (also required here) — see the specificity rule below.
   - **(ii) Executable-but-non-OOP plan** (`P ∩ X ≠ ∅` but the touched
     `X`-member has NO object/function structure — a Makefile, `*.mk`,
     `Containerfile*`, `.github/**` CI YAML, `hooks/**`, `bin/**` script, shell
     script, or config-with-a-shebang): **DRY analysis + Design Intent** apply
     (duplication and stated-intent are meaningful for any artifact); **SOLID
     and the class/module SRP are attested `N/A — no object/function structure`
     with a one-line reason** (there is no class/function/interface for a
     Liskov / Interface-Segregation / Dependency-Inversion / SRP analysis).
     [GLEIPNIR ADAPTATION: AETOS applies SOLID uniformly to code; Gleipnir
     splits case (ii) out because Axis-1's `X` answers "produces an executable
     artifact?" — NOT "has OOP structure worth a SOLID analysis" — and the two
     do not always coincide. Forcing SOLID onto a Makefile yields a vacuous
     "N/A, no classes" *inside* the analysis branch, so it is routed to an
     explicit attested N/A instead.]
   - **(iii) Prose/config-only plan** (`P ∩ X = ∅` — no executable artifact):
     SOLID/DRY/SRP do not apply (there is no class/function/module to analyse)
     and are attested **`N/A — no executable artifact`**. In their place, state
     a **Design Intent** (below). This is the artifact the review-time
     spec-vs-implementation cross-check verifies (the track's genuineness
     proxy). [GLEIPNIR ADAPTATION: AETOS has no prose/config track, so this
     case is Gleipnir-specific; rationale — SOLID is meaningless without code,
     but "was the stated intent honoured?" generalises.]

   **Design Intent — specificity / anti-vacuity rule (REQUIRED in all three
   cases; the load-bearing genuineness proxy).** The Design Intent (and, in
   case (i), the Single-Responsibility statement) MUST be a **specific,
   falsifiable claim about the design**: it must name a concrete
   responsibility, boundary, or constraint the implementation must honour, such
   that a reviewer could point to an implementation choice that *violates* it. A
   **generic quality aspiration** — "clean", "correct", "well-structured",
   "follows best practice", "implement this properly", or the like — is NOT a
   Design Intent and MUST be rejected at spec-review, exactly as the hardened
   path's SUBSTANCE rule (`../stage-role-map.md`) rejects narrative,
   non-reproducible attestation evidence. A non-falsifiable intent makes the
   cross-check trivially pass ("any implementation honours it") and collapses
   the whole gate into theatre; this rule is a hard, non-negotiable requirement,
   not advisory. [GLEIPNIR ADAPTATION: mirrors the existing hardened-path
   SUBSTANCE rule; closes the brainstorm's Pre-Mortem risk #1 (rubber-stamp).]

## Persistence and lifecycle

- Durable **decision records** (resolutions that later work depends on) go in
  `../decisions/`.
- Transient **session artifacts** (per-session briefs, validation reports) go
  in `../plans/` and are disposable after their work merges (see
  `../plans/README.md`).

## Validation

A plan is complete when every section above is present (including the
**Decisions (index)** table and the **Design Principles** section — in whichever
of its three case-forms applies: (i) OOP/functional code → SOLID+DRY+SRP+Design
Intent; (ii) executable-but-non-OOP → DRY+Design Intent, SOLID/SRP attested
`N/A — no object/function structure`; (iii) prose/config-only (`P ∩ X = ∅`) →
Design Intent only, SOLID/DRY/SRP attested `N/A — no executable artifact`), the
Stress-test section lists concrete, checkable acceptance criteria (not "it
works"), and every path/artifact the plan cites has been confirmed to exist
(or is explicitly marked as to-be-created) — never cite a file as existing
without verifying it (L-C15). A missing Design Principles section — or a
Design Intent that is a generic quality aspiration rather than a specific,
falsifiable claim (see the anti-vacuity rule) — is an incomplete plan, the same
way a missing ATLAS section is (L-C14: move the good practice from habit into
the enforced artifact-shape).
