"""Tests for the derived state -> allowed-agents projection table.

Spec context (plan `.gleipnir/plans/engine-wire-in.md`, Assemble step 3): the
table is DATA derived from the engine's ``PipelineState`` enum and the
``stage-role-map.md`` role bindings -- it is a projection, not a second,
independently-editable copy of sequencing logic. ``TRANSITIONS`` (order)
stays the sole authority; this table only says which *role* may legitimately
be dispatched while the engine sits in a given state.
"""

from __future__ import annotations

from gleipnir.engine import PipelineState
from gleipnir.engine.allow_table import (
    ALLOW_TABLE,
    NON_PIPELINE_ROLES,
    ROLE_STATES,
    allowed_agents_for,
)


def test_every_pipeline_state_has_an_entry():
    """SSOT / parity: the table must cover every PipelineState. If a new
    state is ever added to the enum without updating ROLE_STATES, this test
    fails -- forcing the table to track the enum rather than silently
    defaulting to allow or deny."""
    for state in PipelineState:
        assert state in ALLOW_TABLE, f"{state!r} missing from ALLOW_TABLE"


def test_control_and_terminal_states_deny_all():
    for state in (
        PipelineState.HUMAN_QUESTION,
        PipelineState.ESCALATED,
        PipelineState.GATE,
    ):
        assert allowed_agents_for(state) == frozenset()


def test_project_mgr_and_notify_never_allowed():
    for state in PipelineState:
        allowed = allowed_agents_for(state)
        assert "project-mgr" not in allowed
        assert "notify" not in allowed
    for role in NON_PIPELINE_ROLES:
        assert role not in ROLE_STATES


def test_gleipnir_plan_maps_to_plan_exactly():
    assert ROLE_STATES["gleipnir-plan"] == frozenset({PipelineState.PLAN})
    assert "gleipnir-plan" in allowed_agents_for(PipelineState.PLAN)


def test_gleipnir_brainstorm_maps_to_brainstorm_exactly():
    assert ROLE_STATES["gleipnir-brainstorm"] == frozenset(
        {PipelineState.BRAINSTORM}
    )
    assert "gleipnir-brainstorm" in allowed_agents_for(PipelineState.BRAINSTORM)


def test_quality_reviewer_maps_to_spec_review_and_quality_exactly():
    assert ROLE_STATES["quality-reviewer"] == frozenset(
        {PipelineState.SPEC_REVIEW, PipelineState.QUALITY}
    )
    for state in (PipelineState.SPEC_REVIEW, PipelineState.QUALITY):
        assert "quality-reviewer" in allowed_agents_for(state)


def test_gleipnir_code_maps_to_test_and_code_exactly():
    assert ROLE_STATES["gleipnir-code"] == frozenset(
        {PipelineState.TEST, PipelineState.CODE}
    )
    for state in (PipelineState.TEST, PipelineState.CODE):
        assert "gleipnir-code" in allowed_agents_for(state)


def test_git_ops_maps_to_git_exactly():
    assert ROLE_STATES["git-ops"] == frozenset({PipelineState.GIT})
    assert "git-ops" in allowed_agents_for(PipelineState.GIT)


def test_each_state_allows_exactly_its_bound_role_and_no_other():
    expected = {
        PipelineState.BRAINSTORM: {"gleipnir-brainstorm"},
        PipelineState.PLAN: {"gleipnir-plan"},
        PipelineState.SPEC_REVIEW: {"quality-reviewer"},
        PipelineState.TEST: {"gleipnir-code"},
        PipelineState.CODE: {"gleipnir-code"},
        PipelineState.QUALITY: {"quality-reviewer"},
        PipelineState.GIT: {"git-ops"},
        PipelineState.GATE: set(),
        PipelineState.HUMAN_QUESTION: set(),
        PipelineState.ESCALATED: set(),
    }
    for state, roles in expected.items():
        assert allowed_agents_for(state) == frozenset(roles), state


def test_unknown_state_denies_by_default():
    """allowed_agents_for must never default-allow for a value that is not
    a real PipelineState member."""
    assert allowed_agents_for("not-a-real-state") == frozenset()


def test_allow_table_values_are_frozensets():
    for value in ALLOW_TABLE.values():
        assert isinstance(value, frozenset)


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
