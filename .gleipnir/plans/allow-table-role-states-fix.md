# Plan: allow_table ROLE_STATES stale-binding fix

**Stage:** plan (`gleipnir-plan`) → hands to spec-review → test → code.
**Planned from:** `.gleipnir/plans/allow-table-role-states-fix-brainstorm.md`
(Approach B, orchestrator-confirmed; not re-decided here).
**Scope guard:** test-first correctness fix for `gleipnir-code` (Sonnet-tier).
`src/` + `tests/` only. No `.gleipnir/**` edits. No new material tradeoffs.

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Correct binding source | Mirror `stage-role-map.md` exactly: `gleipnir-brainstorm`→`{BRAINSTORM}`, `gleipnir-plan`→`{PLAN}` | Invent a new binding; collapse the two states | Map is authoritative + already converged; TS side (`test_sequence_gate.mjs`) already encodes it. Brief §Constraints |
| 2 | What to edit | Only the authored input `ROLE_STATES` (+ its docstring) | Edit `_derive_allow_table` / `ALLOW_TABLE` / `allowed_agents_for` | Table must stay a *derivation*, not a hand-maintained parallel copy. Brief §Constraints |
| 3 | Parity-test scope | Add role-axis parity guard (Approach B) | Minimal fix only (Approach A) | Closes the exact drift class (L-C20) at negligible cost; extends the module's own SSOT-parity claim from state axis to role axis. Brief §Decision Analysis — not a material tradeoff (all 12 bias detectors ran, none fired) |
| 4 | Untouched artifacts | Leave `test_bridge.py`, `golden_marker.json`, `dogfood_bridge.json`, and the two auto-tracking tests as-is | Edit them "to be safe" | `test_bridge.py:44` signs opaque MAC payload; fixtures are correct PLAN-state markers; `test_driver.py:63` + `test_armed_run_dogfood.py:168` recompute from `allowed_agents_for()` and are the derivation witnesses. Brief §Open Questions / §Scope Sketch |
| 5 | Live stale bridge | Do NOT touch `.gleipnir/var/run/pipeline-state.json` | Read-for-write / repair it | Out of scope (hard); no roster access; logged as L-C19. This delegation fixes the source of truth for *future* mints only. Brief §Constraints |

## Architect

**Problem (one sentence):** `ROLE_STATES` in `src/gleipnir/engine/allow_table.py`
still binds `gleipnir-plan` to both `BRAINSTORM` and `PLAN` and has no
`gleipnir-brainstorm` entry, so a derived allow-table under an armed run makes
the `brainstorm` stage structurally unreachable by its actually-bound role.

**User:** the G-5 pre-tool sequence gate (and, transitively, any armed pipeline
run that dispatches the `gleipnir-brainstorm` role at `BRAINSTORM`).

**Measurable success criteria:**
- `ROLE_STATES["gleipnir-brainstorm"] == frozenset({PipelineState.BRAINSTORM})`
  and `ROLE_STATES["gleipnir-plan"] == frozenset({PipelineState.PLAN})`.
- `allowed_agents_for(PipelineState.BRAINSTORM) == frozenset({"gleipnir-brainstorm"})`
  and `allowed_agents_for(PipelineState.PLAN) == frozenset({"gleipnir-plan"})`.
- A new role-axis parity test asserts a canonical `ROLE_STATES` literal
  (transcribed from `stage-role-map.md`) equals the module's actual `ROLE_STATES`.
- `bin/gleipnir-sandbox test` is green; net new test count = **+2** vs. current
  (10→12 functions): +1 from the split (one stale test replaced by two focused
  tests) + 1 from the new parity test = +2 net.

**Constraints (inherited from the brief, load-bearing):**
- `stage-role-map.md` is authoritative — mirror it, do not invent a binding.
- Edit only the authored projection input (`ROLE_STATES` + docstring); the
  derivation logic (`_derive_allow_table`, `ALLOW_TABLE`, `allowed_agents_for`)
  stays byte-for-byte unchanged.
- `gate` stays absent from `ROLE_STATES` (control state, deny-all — correct).
- `src/` + `tests/` only. No `.gleipnir/**` config edits; no
  `.gleipnir/var/run/pipeline-state.json` access (L-C19).

## Trace

**Artifacts and where they live (source of truth):**

| Artifact | Path | Role in this change |
|---|---|---|
| Authoritative binding | `.gleipnir/stage-role-map.md` (Tier-3, read-only here) | Source of truth the fix mirrors |
| Authored projection input | `src/gleipnir/engine/allow_table.py` `ROLE_STATES` (line 55-62) + docstring (lines 11-14) | **Edited** (impl) |
| Enum members | `src/gleipnir/engine/__init__.py:55-65` (`BRAINSTORM="brainstorm"`, `PLAN="plan"`, distinct members) | Read-only; confirmed distinct |
| Existing allow-table tests | `tests/test_allow_table.py` | **Edited** (test-first): rewrite lines 49-54; fix line 80; add new parity test |

**Integrations map (what consumes `ROLE_STATES` / the derived table):**
- `_derive_allow_table()` → `ALLOW_TABLE` → `allowed_agents_for()` — pure
  projection; automatically produces the corrected sets once `ROLE_STATES` is
  fixed. **No edit.**
- `tests/test_driver.py:63` (BRAINSTORM) and `tests/test_armed_run_dogfood.py:168`
  recompute expected from `allowed_agents_for(...)` — they track the fix
  automatically and are the derivation-correctness witnesses. **No edit; must
  stay green.** (Confirmed both lines call `allowed_agents_for(...)`.)
- `tests/test_sequence_gate.mjs` (TS handshake side) already encodes
  `brainstorm → ["gleipnir-brainstorm"]`; the fix restores end-to-end
  Python↔TS consistency for BRAINSTORM. **No edit — TS side already correct.**

**Edge cases:**
- `gleipnir-brainstorm` was entirely absent → `allowed_agents_for(BRAINSTORM)`
  currently yields `{"gleipnir-plan"}` (a legal-looking wrong set that passes the
  state-axis parity test). The role-axis guard is what catches this class.
- `PLAN` must end up with `gleipnir-plan` *only* (not also brainstorm) — the
  split must move, not copy, the BRAINSTORM membership.
- `NON_PIPELINE_ROLES` (`project-mgr`, `notify`) and `gate` remain absent from
  `ROLE_STATES` — the new canonical literal must not add them.

## Link (validated before building)

- Confirmed `PipelineState.BRAINSTORM` and `PipelineState.PLAN` are distinct enum
  members with a distinct transition edge (`engine/__init__.py:55-65`).
- Confirmed the stale table is `allow_table.py:55-62` and stale docstring prose
  is lines 11-14 ("brainstorm/plan -> gleipnir-plan").
- Confirmed the two tests encoding the stale binding:
  `test_gleipnir_plan_maps_to_brainstorm_and_plan_exactly` (lines 49-55) and
  the `BRAINSTORM: {"gleipnir-plan"}` row (line 80) inside
  `test_each_state_allows_exactly_its_bound_role_and_no_other`.
- Confirmed the two auto-tracking witnesses call `allowed_agents_for(...)`
  (`test_driver.py:63`, `test_armed_run_dogfood.py:168`) — no edit needed.
- Verification tool is `bin/gleipnir-sandbox test` (ephemeral container per
  scaffold G-2 note).

## Assemble (build order — test-first)

**Step order (do NOT reorder; tests are written and shown red before the impl edit):**

1. **Edit `tests/test_allow_table.py` — rewrite the stale `gleipnir-plan` test.**
   Replace `test_gleipnir_plan_maps_to_brainstorm_and_plan_exactly` (lines 49-54)
   with two focused tests:

   ```python
   def test_gleipnir_plan_maps_to_plan_exactly():
       assert ROLE_STATES["gleipnir-plan"] == frozenset({PipelineState.PLAN})
       assert "gleipnir-plan" in allowed_agents_for(PipelineState.PLAN)


   def test_gleipnir_brainstorm_maps_to_brainstorm_exactly():
       assert ROLE_STATES["gleipnir-brainstorm"] == frozenset(
           {PipelineState.BRAINSTORM}
       )
       assert "gleipnir-brainstorm" in allowed_agents_for(PipelineState.BRAINSTORM)
   ```

2. **Edit `tests/test_allow_table.py` — fix the BRAINSTORM row** in
   `test_each_state_allows_exactly_its_bound_role_and_no_other` (line 80):

   ```python
   #   from:
           PipelineState.BRAINSTORM: {"gleipnir-plan"},
   #   to:
           PipelineState.BRAINSTORM: {"gleipnir-brainstorm"},
   ```
   (`PipelineState.PLAN: {"gleipnir-plan"}` on line 81 is already correct — leave it.)

3. **Add `tests/test_allow_table.py` — the L-C20 role-axis parity guard** (append
   as a new test function):

   ```python
   def test_role_states_matches_canonical_stage_role_map():
       """Role-axis SSOT/parity: ROLE_STATES must mirror stage-role-map.md
       exactly. A future roster/binding change not reflected here fails this
       test immediately (L-C20 — closes the drift class that hid the missing
       gleipnir-brainstorm binding). The literal below is the single audited
       transcription point of .gleipnir/stage-role-map.md's table."""
       canonical = {
           "gleipnir-brainstorm": frozenset({PipelineState.BRAINSTORM}),
           "gleipnir-plan": frozenset({PipelineState.PLAN}),
           "quality-reviewer": frozenset(
               {PipelineState.SPEC_REVIEW, PipelineState.QUALITY}
           ),
           "gleipnir-code": frozenset({PipelineState.TEST, PipelineState.CODE}),
           "git-ops": frozenset({PipelineState.GIT}),
       }
       assert dict(ROLE_STATES) == canonical
   ```
   Steps 1-3 leave the suite **red** (source still stale) — this is the intended
   test-first state, shown before the impl edit.

4. **Edit `src/gleipnir/engine/allow_table.py` — split the stale entry.**
   Replace line 56:

   ```python
   #   from:
       "gleipnir-plan": frozenset({PipelineState.BRAINSTORM, PipelineState.PLAN}),
   #   to:
       "gleipnir-brainstorm": frozenset({PipelineState.BRAINSTORM}),
       "gleipnir-plan": frozenset({PipelineState.PLAN}),
   ```
   (Leave lines 57-62 — `quality-reviewer`, `gleipnir-code`, `git-ops` — unchanged.)

5. **Edit `src/gleipnir/engine/allow_table.py` — fix the stale docstring prose**
   (lines 12-14). Change the parenthetical binding list from
   `brainstorm/plan -> gleipnir-plan;` to reflect the split, e.g.:

   ```
   ``ROLE_STATES`` — the role -> bound-states binding lifted directly from
   ``.gleipnir/stage-role-map.md``'s table (brainstorm -> gleipnir-brainstorm;
   plan -> gleipnir-plan; spec-review/quality -> quality-reviewer;
   test/code -> gleipnir-code; git -> git-ops).
   ```

6. **Run verification** (Stress-test below). Suite goes green.

## Stress-test (acceptance checks)

Run: `bin/gleipnir-sandbox test`

Concrete, checkable criteria:
- **AC1** `test_gleipnir_plan_maps_to_plan_exactly` passes.
- **AC2** `test_gleipnir_brainstorm_maps_to_brainstorm_exactly` passes.
- **AC3** `test_each_state_allows_exactly_its_bound_role_and_no_other` passes
  with the corrected BRAINSTORM row.
- **AC4** `test_role_states_matches_canonical_stage_role_map` passes.
- **AC5** State-axis parity (`test_every_pipeline_state_has_an_entry`) and
  deny-all controls (`test_control_and_terminal_states_deny_all`,
  `test_project_mgr_and_notify_never_allowed`) still pass — `gate`,
  `project-mgr`, `notify` unchanged.
- **AC6** The two auto-tracking witnesses pass **without edits**:
  `tests/test_driver.py` (BRAINSTORM marker → `{"gleipnir-brainstorm"}`) and
  `tests/test_armed_run_dogfood.py` (minted `allowed_agents` follows the
  correction).
- **AC7** Whole suite green; **net test count delta = +2** (10→12 functions):
  +1 from the split (one stale test replaced by two focused tests) + 1 from the
  new parity test.
- **AC8** No diff outside `src/gleipnir/engine/allow_table.py` and
  `tests/test_allow_table.py`. Specifically unchanged: `_derive_allow_table`,
  `ALLOW_TABLE`, `allowed_agents_for`, `NON_PIPELINE_ROLES`, `test_bridge.py`,
  `tests/fixtures/golden_marker.json`, `tests/fixtures/dogfood_bridge.json`,
  `tests/test_sequence_gate.mjs`, and any `.gleipnir/**` file.

## Execution Workflow

For the implementing agent (`gleipnir-code`, test → code stages):

1. **test stage:** apply Assemble steps 1-3 to `tests/test_allow_table.py`.
   Run `bin/gleipnir-sandbox test` and confirm the suite is **red** on the new
   /rewritten assertions (test-first: the tests must fail before the source is
   fixed, proving they bind the correction).
2. **code stage:** apply Assemble steps 4-5 to
   `src/gleipnir/engine/allow_table.py` (split entry + docstring only).
3. Re-run `bin/gleipnir-sandbox test`; confirm **all** acceptance checks AC1-AC8,
   green suite, +1 net test count.
4. **Do not** edit any auto-tracking test, fixture, `.mjs` file, derivation
   logic, or any `.gleipnir/**` path (including `var/run/pipeline-state.json`).
   If a change appears needed outside the two named files, **stop** — that is a
   scope signal to route back, not to absorb.

## Non-goals (hard boundaries)

- No edit to `_derive_allow_table` / `ALLOW_TABLE` / `allowed_agents_for` —
  the fix edits authored input only.
- No edit to `test_bridge.py:44`, `golden_marker.json`, `dogfood_bridge.json`,
  `test_sequence_gate.mjs`, `test_driver.py`, `test_armed_run_dogfood.py`.
- No touch to `.gleipnir/var/run/pipeline-state.json` or any `.gleipnir/**` file
  (L-C19 / Tier-3 boundary).
- No new roster role, no binding invention — mirror `stage-role-map.md` only.
