/**
 * allowTable.test.ts — structural port of `tests/test_allow_table.py` (13
 * cases, same names). The table is DATA derived from the engine's
 * `PipelineState` vocabulary and the `stage-role-map.md` role bindings — a
 * projection, never a second, independently-editable copy of sequencing
 * logic. `TRANSITIONS` (order) stays the sole authority; this table only
 * says which ROLE may legitimately be dispatched while the engine sits in a
 * given state.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { PipelineState } from "../src/engine/state.ts";
import {
  ALLOW_TABLE,
  NON_PIPELINE_ROLES,
  ROLE_STATES,
  allowedRolesFor,
} from "../src/engine/allowTable.ts";

const ALL_STATES: PipelineState[] = Object.values(PipelineState);

test("test_every_pipeline_state_has_an_entry", () => {
  // SSOT / parity: the table must cover every PipelineState. If a new state
  // is ever added without updating ROLE_STATES, this test fails.
  for (const state of ALL_STATES) {
    assert.ok(state in ALLOW_TABLE, `${state} missing from ALLOW_TABLE`);
  }
});

test("test_control_and_terminal_states_deny_all", () => {
  for (const state of [PipelineState.HUMAN_QUESTION, PipelineState.ESCALATED, PipelineState.GATE]) {
    assert.deepEqual(allowedRolesFor(state), new Set());
  }
});

test("test_project_mgr_and_notify_never_allowed", () => {
  for (const state of ALL_STATES) {
    const allowed = allowedRolesFor(state);
    assert.ok(!allowed.has("project-mgr"));
    assert.ok(!allowed.has("notify"));
  }
  for (const role of NON_PIPELINE_ROLES) {
    assert.ok(!(role in ROLE_STATES));
  }
});

test("test_gleipnir_plan_maps_to_plan_exactly", () => {
  assert.deepEqual(ROLE_STATES["gleipnir-plan"], new Set([PipelineState.PLAN]));
  assert.ok(allowedRolesFor(PipelineState.PLAN).has("gleipnir-plan"));
});

test("test_gleipnir_brainstorm_maps_to_brainstorm_exactly", () => {
  assert.deepEqual(ROLE_STATES["gleipnir-brainstorm"], new Set([PipelineState.BRAINSTORM]));
  assert.ok(allowedRolesFor(PipelineState.BRAINSTORM).has("gleipnir-brainstorm"));
});

test("test_quality_reviewer_maps_to_spec_review_and_quality_exactly", () => {
  assert.deepEqual(
    ROLE_STATES["quality-reviewer"],
    new Set([PipelineState.SPEC_REVIEW, PipelineState.QUALITY]),
  );
  for (const state of [PipelineState.SPEC_REVIEW, PipelineState.QUALITY]) {
    assert.ok(allowedRolesFor(state).has("quality-reviewer"));
  }
});

test("test_gleipnir_code_maps_to_test_and_code_exactly", () => {
  assert.deepEqual(ROLE_STATES["gleipnir-code"], new Set([PipelineState.TEST, PipelineState.CODE]));
  for (const state of [PipelineState.TEST, PipelineState.CODE]) {
    assert.ok(allowedRolesFor(state).has("gleipnir-code"));
  }
});

test("test_git_ops_maps_to_git_exactly", () => {
  assert.deepEqual(ROLE_STATES["git-ops"], new Set([PipelineState.GIT]));
  assert.ok(allowedRolesFor(PipelineState.GIT).has("git-ops"));
});

test("test_each_state_allows_exactly_its_bound_role_and_no_other", () => {
  const expected = new Map<PipelineState, Set<string>>([
    [PipelineState.BRAINSTORM, new Set(["gleipnir-brainstorm"])],
    [PipelineState.PLAN, new Set(["gleipnir-plan"])],
    [PipelineState.SPEC_REVIEW, new Set(["quality-reviewer"])],
    [PipelineState.TEST, new Set(["gleipnir-code"])],
    [PipelineState.CODE, new Set(["gleipnir-code"])],
    [PipelineState.QUALITY, new Set(["quality-reviewer"])],
    [PipelineState.GIT, new Set(["git-ops"])],
    [PipelineState.GATE, new Set()],
    [PipelineState.HUMAN_QUESTION, new Set()],
    [PipelineState.ESCALATED, new Set()],
  ]);
  for (const [state, roles] of expected) {
    assert.deepEqual(allowedRolesFor(state), roles, state);
  }
});

test("test_unknown_state_denies_by_default", () => {
  // allowedRolesFor must never default-allow for a value that is not a real
  // PipelineState member.
  assert.deepEqual(allowedRolesFor("not-a-real-state"), new Set());
});

test("test_allow_table_values_are_frozensets", () => {
  // TS analogue (idiom-table row 8): values are frozen Sets, not frozensets.
  for (const value of Object.values(ALLOW_TABLE)) {
    assert.ok(value instanceof Set);
    assert.ok(Object.isFrozen(value));
  }
});

test("test_role_states_matches_canonical_stage_role_map", () => {
  // Role-axis SSOT/parity: ROLE_STATES must mirror stage-role-map.md
  // exactly. The literal below is the single audited transcription point of
  // .gleipnir/stage-role-map.md's table.
  const canonical = new Map<string, Set<PipelineState>>([
    ["gleipnir-brainstorm", new Set([PipelineState.BRAINSTORM])],
    ["gleipnir-plan", new Set([PipelineState.PLAN])],
    ["quality-reviewer", new Set([PipelineState.SPEC_REVIEW, PipelineState.QUALITY])],
    ["gleipnir-code", new Set([PipelineState.TEST, PipelineState.CODE])],
    ["git-ops", new Set([PipelineState.GIT])],
  ]);
  assert.deepEqual(new Set(Object.keys(ROLE_STATES)), new Set(canonical.keys()));
  for (const [role, states] of canonical) {
    assert.deepEqual(ROLE_STATES[role], states, role);
  }
});

test("positive control: ALLOW_TABLE is a derivation, not a hand-copied table", () => {
  // allow_table.py L71-90's projection property: a state absent from every
  // role's bound-states set falls out with the empty set automatically. The
  // two control/terminal states below are exactly that case -- neither
  // appears in ROLE_STATES, yet both have a correct (deny-all) entry.
  for (const state of [PipelineState.GATE, PipelineState.HUMAN_QUESTION, PipelineState.ESCALATED]) {
    for (const boundStates of Object.values(ROLE_STATES)) {
      assert.ok(!boundStates.has(state), `${state} must not be bound to any role`);
    }
    assert.deepEqual(allowedRolesFor(state), new Set());
  }
});
