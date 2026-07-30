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

## Persistence and lifecycle

- Durable **decision records** (resolutions that later work depends on) go in
  `../decisions/`.
- Transient **session artifacts** (per-session briefs, validation reports) go
  in `../plans/` and are disposable after their work merges (see
  `../plans/README.md`).

## Validation

A plan is complete when every section above is present (including the
**Decisions (index)** table), the Stress-test section lists concrete, checkable
acceptance criteria (not "it works"), and every path/artifact the plan cites has
been confirmed to exist (or is explicitly marked as to-be-created) — never cite
a file as existing without verifying it (L-C15).
