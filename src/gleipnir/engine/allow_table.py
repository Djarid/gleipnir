"""Derived state -> allowed-agents projection (G-5 wire-in, Assemble step 3).

Per the plan (`.gleipnir/plans/engine-wire-in.md`): the pre-tool hook needs
to answer "from the engine's current state S, is dispatching agent X
legitimate?" This module derives that answer from two authorities that
already exist, rather than hand-maintaining a second, independently
editable copy of sequencing logic:

  * ``gleipnir.engine.PipelineState`` — the engine's own enum (order/
    transitions remain ``TRANSITIONS``'s job, untouched here).
  * ``ROLE_STATES`` — the role -> bound-states binding lifted directly from
    ``.gleipnir/stage-role-map.md``'s table (brainstorm -> gleipnir-brainstorm;
    plan -> gleipnir-plan; spec-review/quality -> quality-reviewer;
    test/code -> gleipnir-code; git -> git-ops).

``ALLOW_TABLE`` is *computed* from those two by iterating every
``PipelineState`` member and collecting the roles bound to it — it is a
projection, not a parallel literal. Adding a ``PipelineState`` member without
updating ``ROLE_STATES`` still produces a (correctly empty, deny-by-default)
entry for it, and the SSOT/parity test (`tests/test_allow_table.py`) asserts
every enum member has an entry, so the table cannot silently drift out of
sync with the enum it is built from.

``project-mgr`` and ``notify`` have no bound G-5 pipeline stage
(`stage-role-map.md`), so they are simply absent from ``ROLE_STATES`` —
which means they are structurally absent from every state's allow set,
never a special-cased deny. This is the plan's "(recommended) deny them
while a pipeline is active" resolution: no allow-hole is carved for them.

``gate`` is not included here as a *dispatchable* target: per the stage-role
map's binding rules, ``gate`` is the orchestrator's own bound stage
(``Engine.attempt_gate``), not a ``task`` delegation target. It still gets
a (deny-all) entry in ``ALLOW_TABLE`` because it is a real ``PipelineState``
and the parity test requires every state to be covered.
"""

from __future__ import annotations

from typing import Mapping

from gleipnir.engine import PipelineState

__all__ = [
    "ROLE_STATES",
    "ALLOW_TABLE",
    "NON_PIPELINE_ROLES",
    "allowed_agents_for",
]


# The one place the stage-role-map.md bindings are lifted into code. This is
# the *authored* projection input (mirroring the map's table exactly); the
# per-state table below is *derived* from it, not written by hand a second
# time.
ROLE_STATES: Mapping[str, frozenset[PipelineState]] = {
    "gleipnir-brainstorm": frozenset({PipelineState.BRAINSTORM}),
    "gleipnir-plan": frozenset({PipelineState.PLAN}),
    "quality-reviewer": frozenset(
        {PipelineState.SPEC_REVIEW, PipelineState.QUALITY}
    ),
    "gleipnir-code": frozenset({PipelineState.TEST, PipelineState.CODE}),
    "git-ops": frozenset({PipelineState.GIT}),
}

# Named for the SSOT/parity tests and for documentation: these roster roles
# are known to have no G-5 pipeline stage and must never appear in
# ROLE_STATES or in any ALLOW_TABLE entry (minimal-slice deny, per the plan).
NON_PIPELINE_ROLES: frozenset[str] = frozenset({"project-mgr", "notify"})


def _derive_allow_table() -> dict[PipelineState, frozenset[str]]:
    """Project ``ROLE_STATES`` onto every ``PipelineState`` member.

    Iterating ``PipelineState`` (the engine's own enum) — rather than
    listing states by hand here — is what makes this a *derivation*: a
    state absent from every role's bound-states set (HUMAN_QUESTION,
    ESCALATED, GATE, or any future control state) falls out with the empty
    set automatically, and a state present in the enum but never assigned
    to ``ALLOW_TABLE`` is structurally impossible, since every member is
    visited.
    """

    table: dict[PipelineState, frozenset[str]] = {}
    for state in PipelineState:
        table[state] = frozenset(
            role
            for role, bound_states in ROLE_STATES.items()
            if state in bound_states
        )
    return table


ALLOW_TABLE: Mapping[PipelineState, frozenset[str]] = _derive_allow_table()


def allowed_agents_for(state: object) -> frozenset[str]:
    """The set of roles legitimately dispatchable while the engine is in
    ``state``. Deny-by-default: any value that is not a known
    ``PipelineState`` member (including a plain string, a typo, or a future
    unmapped state) returns the empty set rather than raising or guessing.
    """

    if not isinstance(state, PipelineState):
        return frozenset()
    return ALLOW_TABLE.get(state, frozenset())
