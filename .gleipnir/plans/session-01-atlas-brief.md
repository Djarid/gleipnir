# ATLAS Brief — Session 01 (retroactive)

**Why retroactive.** This session produced spec revisions, the step-0 scaffold,
the substrate design pass, and the G-3.1 marker *before* the ATLAS/GOTCHA
methodology was applied to the work itself. The operator required the
methodology be applied, including retroactively: write the brief that *should*
have driven the work, then validate what was produced against it and fix
discrepancies. This file is that brief. The validation results and fixes are in
`session-01-validation.md`.

---

## A — Architect

**Problem (one sentence).** Take the Gleipnir spec from prose-only to a
working, honest foundation: a right-sized agent roster, the methodology it runs
on, the resolved substrate decisions, and the first real enforcement guard —
without any artifact masquerading as more finished than it is.

**User.** The builder implementing Gleipnir in later build-order steps, and the
future G-5 engine that will consume the stage-to-role map and the goals as
configuration.

**Success (measurable).**
1. Six agents exist as deny-by-default opencode agents bound to the pipeline.
2. GOTCHA/ATLAS inherited-and-amended with the layer-2 collision resolved, and
   the spec records this (K-2.1).
3. D-1 and D-4 resolved in the decision register with the config load path
   fixed.
4. G-3.1 keyed marker implemented with passing conformance [D] tests
   (agent-forge fails; one-byte mutation invalidates; red run mints nothing).
5. Every artifact honestly labelled "authored, not yet closed" where the
   enforcing substrate does not exist yet.
6. Model choices right-sized to the goal (tokens spent where judgment is
   unbounded, cheap models for mechanical roles).

**Constraints.**
- Basics only at step 0; no substrate/broker/bus/engine code beyond G-3.1.
- Models limited to aperture-served IDs in this environment.
- Gleipnir's own code, not lifted from AETOS (operator instruction).
- No secrets committed; `.DS_Store`/venv excluded.
- Methodology is a prerequisite to planning (this brief precedes, not follows).

---

## T — Trace

**Artifacts and where they live (source of truth).**

| Artifact | Path | Kind |
|---|---|---|
| Spec (canonical) | `gleipnir_specification_v0_3_9.md` | doc |
| Roster | `.gleipnir/agents/*.md` | config (enforcement-bearing) |
| Methodology | `.gleipnir/skills/{gotcha,atlas}/SKILL.md` | content |
| Stage-to-role map | `.gleipnir/stage-role-map.md` | config |
| Substrate decisions | `.gleipnir/plans/substrate-design-pass.md` | decision record |
| G-3.1 marker | `src/gleipnir/verify/` | code |
| Tests | `tests/` | code |
| Runtime wiring | `opencode.jsonc`, `.envrc` | config |

**Integrations map.**

| Integration | Purpose | Notes / risk |
|---|---|---|
| opencode runtime | agent host, hooks | S-1 7/8 hooks; #8 = E-2 gap |
| aperture models | per-stage models | opus/sonnet/haiku IDs verified in user config |
| direnv | sets OPENCODE_CONFIG_DIR | confirmed working |
| Python 3.11+/pytest | G-3.1 verifier + tests | venv gitignored |

**Edge cases the work must handle.**
- Agent fabricates a marker (no key) → must fail validation.
- Tree changes by one byte after mint → genuine marker must invalidate.
- Red test run → no marker minted.
- Missing/stale/wrong-version marker → fail-closed (run tests).
- `.gleipnir/` is tree-side today → must be acknowledged as a G-1 fail until
  closure, not silently presented as enforcing.
- No goals manifest exists (K-1 empty) → must be named as a gap.

---

## L — Link (what was validated before/around building)

- Available runtimes checked (python3, node, go) before choosing Python for G-3.1.
- opencode hook surface fetched and mapped to the S-1 contract.
- aperture model IDs read from the live user config.
- direnv `.envrc` allow-status confirmed.

**Not linked (honest gap):** no goals/tools manifest to check, because K-1/T
layers are unbuilt.

---

## A — Assemble (intended build order)

1. Methodology skills (prerequisite) → 2. roster → 3. stage-role map →
4. AGENTS.md + config wiring → 5. substrate decisions → 6. spec revisions
recording all of the above → 7. G-3.1 marker + tests.

Note: in reality methodology/roster/spec were built across turns and G-3.1
last. The retroactive validation checks the *result* against this brief.

---

## S — Stress-test (acceptance criteria to validate against)

See `session-01-validation.md`. Each success criterion above becomes a check;
each edge case becomes a test or a documented status. Discrepancies get fixed.

---

## Plan-persistence note

This brief is written to disk per ATLAS/GOTCHA discipline (writing a plan IS
planning). Going forward, the Architect/Trace brief precedes code; this
retroactive brief closes the gap for session 01.
