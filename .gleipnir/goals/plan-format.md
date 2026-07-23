# Goal: Plan Format

**Kind:** artifact/format goal (not sequencing). Legitimate goals-content now.

Every plan written to disk must follow this structure. Writing a plan file IS
planning; it is never blocked by read-only or plan mode, and is never deferred
(inherited ATLAS/GOTCHA discipline).

## Required sections

A plan is an ATLAS brief. It must contain:

1. **Architect** — problem (one sentence), user, measurable success criteria,
   constraints.
2. **Trace** — artifacts and where they live (source of truth), integrations
   map, edge cases.
3. **Link** — what was validated before building (connections, tools, inputs).
4. **Assemble** — intended build order.
5. **Stress-test** — the acceptance checks the result will be validated against.
6. **Execution Workflow** — enough for an implementing agent to act without
   rediscovering the protocol. A plan without this section is incomplete.

## Persistence and lifecycle

- Durable **decision records** (resolutions that later work depends on) go in
  `../decisions/`.
- Transient **session artifacts** (per-session briefs, validation reports) go
  in `../plans/` and are disposable after their work merges (see
  `../plans/README.md`).

## Validation

A plan is complete when every section above is present and the Stress-test
section lists concrete, checkable acceptance criteria (not "it works").
