"""Gleipnir G-5 wire-in — the engine driver (Assemble step 2).

Owns an ``Engine`` instance and is the Python-side half of the state bridge:
it can read the current state, advance the engine on a mechanically
observed clean ``task`` completion, and persist the digest-protected bridge
payload (state + allow-table projection, one MAC) via
``gleipnir.engine.bridge``.

**Who calls this.** Per the plan, the driver is invoked by framework/runtime
code — the Tier-3 post-tool hook (`tool.execute.after`) or an equivalent
framework process — never by a roster agent via a bash grant. This module
only builds the driver's Python API so that caller can use it; it does not
wire the hook invocation itself (that is the TS/Tier-3 hand-off, out of
scope for this delegation).

**Trivial completion judge.** For the minimal slice, "the task tool returned
cleanly" is the only completion signal the driver's caller has mechanically
observed (per the plan's Trace: post-tool observation cannot judge work
quality, only that the tool returned without error). So
``advance_on_clean_completion`` steps the engine with a judge that always
returns ``Verdict.PASS`` — richer per-stage verdicts (real spec-review/
quality outcomes, CI attestation) are a later, separate wiring of
``Engine.step``/``Engine.attempt_gate``, unchanged here.

**Fail-closed on the key.** Every operation that would publish a bridge
(``write_bridge``, and therefore ``advance_on_clean_completion``) loads the
verifier key *before* doing anything else. If the key is unavailable, the
call raises ``KeyUnavailable`` and neither the bridge file nor (for
``advance_on_clean_completion``) the in-memory engine state changes — a
half-advanced-but-unpublished driver would itself be a fail-open bug.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from gleipnir.engine import Engine, PipelineState, StepResult, Verdict
from gleipnir.engine.allow_table import allowed_agents_for
from gleipnir.engine.bridge import KeyUnavailable, StateMarker, load_key, mint_state

__all__ = ["Driver"]


def _trivial_completion_judge(
    _state: PipelineState, _payload: Mapping[str, Any]
) -> Verdict:
    """The minimal slice's only completion signal: the task tool returned
    without error. Never inspects payload text (no self-attestation
    channel); always PASS."""

    return Verdict.PASS


class Driver:
    """Owns one ``Engine`` for a live pipeline and publishes it to the
    bridge file the (Tier-3, out-of-scope-here) pre-tool hook reads.
    """

    def __init__(
        self,
        pipeline_id: str,
        bridge_path: str | os.PathLike[str],
        key_file: str | os.PathLike[str] | None = None,
    ) -> None:
        self.engine = Engine(pipeline_id)
        self.bridge_path = Path(bridge_path)
        self._key_file = key_file

    @property
    def state(self) -> PipelineState:
        """Read-only current state. Changes only via ``step``-driving
        methods on this class, which delegate to ``Engine``."""

        return self.engine.state

    def _load_key(self) -> bytes:
        # Fail-closed: no key path, missing file, or empty file all raise
        # KeyUnavailable here, before any state change or file write.
        return load_key(self._key_file)

    def write_bridge(self, minted_at: int | None = None) -> StateMarker:
        """Mint and persist a bridge marker for the *current* engine state.

        Requires the key; raises ``KeyUnavailable`` and writes nothing if
        it cannot be loaded.
        """

        key = self._load_key()
        allowed = sorted(allowed_agents_for(self.engine.state))
        marker = mint_state(
            self.engine.state.value, allowed, key, minted_at=minted_at
        )
        self.bridge_path.parent.mkdir(parents=True, exist_ok=True)
        self.bridge_path.write_text(marker.to_json())
        return marker

    def advance_on_clean_completion(
        self, minted_at: int | None = None
    ) -> StepResult:
        """Advance the engine off a mechanically observed clean completion
        (the trivial PASS judge) and republish the bridge.

        The key is loaded *first*, fail-closed, before ``Engine.step`` is
        called — so a missing key leaves the engine's in-memory state
        untouched as well as leaving the bridge unwritten. This method is
        the only place ``Engine.step`` is driven for the minimal slice;
        richer per-stage verdicts are a later wiring, not a change to this
        contract.
        """

        # Fail-closed *before* touching engine state: an unpublishable
        # advance must not happen at all, not happen-but-not-be-visible.
        self._load_key()

        result = self.engine.step(_trivial_completion_judge)
        self.write_bridge(minted_at=minted_at)
        return result
