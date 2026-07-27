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

**G-4 bus wire-in (`.gleipnir/plans/g4-bus-first-slice.md`).** The driver
optionally owns an ``EventBus`` (constructor-injected; ``None`` = no emit).
After each ``advance``-driven ``Engine.step``, the driver observes the
returned ``StepResult`` and — crash-safely, per the plan's §2.4.1
classification — emits a ``RevertOccurredEvent`` for a genuine backward
revert or the budget-exhausting escalation hop. This is the discharge of
the SEAM recorded in ``engine/__init__.py`` (~L418-425): the engine stays
pure (no bus import, no filesystem/process boundary there); the driver,
which already performs I/O (bridge writes, key loads), is the emit site.
Emission is telemetry — it degrades rather than raising (`bus/emit.py`) and
never alters this module's fail-closed key/bridge ordering.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from gleipnir.bus import EventBus, EventKind, RevertOccurredEvent
from gleipnir.engine import (
    Engine,
    Judge,
    PIPELINE_ORDER,
    PipelineState,
    StepResult,
    Verdict,
)
from gleipnir.engine.allow_table import allowed_agents_for
from gleipnir.engine.bridge import (
    KeyUnavailable,
    StateMarker,
    StateMarkerError,
    load_key,
    mint_state,
    validate_state,
)

__all__ = ["Driver", "BridgeInvalid"]


class BridgeInvalid(Exception):
    """The bridge could not be trusted on resume (missing/corrupt/tampered/
    stale/unknown-state). Fail-closed: a caller that catches this must NOT
    proceed as if the pipeline were in any particular state."""


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
        bus: "EventBus | None" = None,
    ) -> None:
        self.engine = Engine(pipeline_id)
        self.bridge_path = Path(bridge_path)
        self._key_file = key_file
        # Optional G-4 bus (None-safe: existing construction without a bus
        # is unchanged). See module docstring "G-4 bus wire-in".
        self._bus = bus

    @classmethod
    def resume_from_bridge(
        cls,
        pipeline_id: str,
        bridge_path: str | os.PathLike[str],
        key_file: str | os.PathLike[str] | None = None,
        max_age_seconds: int | None = None,
        bus: "EventBus | None" = None,
    ) -> "Driver":
        """Rehydrate a Driver at the bridge's *current* state — the
        cross-process path the post-tool hook uses.

        Each opencode hook call is a fresh process, so the canonical pipeline
        state is the persisted bridge, not an in-memory engine. This reads the
        bridge, **validates it fail-closed** (key required; MAC + freshness
        must pass; state must be a known ``PipelineState``), and reconstructs
        the engine at that state via ``Engine.resume_at``.

        Fail-closed: a missing/corrupt/tampered/stale bridge, an unavailable
        key, or an unknown state all raise (``KeyUnavailable`` or
        ``BridgeInvalid``) — a fresh Driver at ``BRAINSTORM`` is **never**
        silently returned in place of an untrusted bridge (that would be
        fail-open — resetting the pipeline to the start on any tamper).
        """

        driver = cls.__new__(cls)
        driver.bridge_path = Path(bridge_path)
        driver._key_file = key_file
        # None-safe: a resumed driver may also emit; existing callers pass no
        # bus and get the same no-emit behaviour as a fresh Driver.
        driver._bus = bus

        key = load_key(key_file)  # KeyUnavailable if absent -> fail-closed

        try:
            text = driver.bridge_path.read_text()
        except OSError as exc:
            raise BridgeInvalid(f"cannot read bridge at {bridge_path}: {exc}") from exc
        try:
            marker = StateMarker.from_json(text)
        except StateMarkerError as exc:
            raise BridgeInvalid(f"bridge is not a valid marker: {exc}") from exc

        kwargs = {} if max_age_seconds is None else {"max_age_seconds": max_age_seconds}
        if not validate_state(marker, key, **kwargs):
            raise BridgeInvalid("bridge failed MAC/freshness validation")

        try:
            state = PipelineState(marker.pipeline_state)
        except ValueError as exc:
            raise BridgeInvalid(
                f"bridge names an unknown pipeline state {marker.pipeline_state!r}"
            ) from exc

        driver.engine = Engine.resume_at(pipeline_id, state)
        return driver

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

    def advance(
        self,
        judge: Judge = _trivial_completion_judge,
        *,
        minted_at: int | None = None,
        agent: str | None = None,
        originating_turn: int = 0,
    ) -> StepResult:
        """Advance the engine one step under ``judge``, republish the bridge,
        and (if a bus is injected) emit a G-4 ``RevertOccurredEvent`` for a
        backward revert — including the budget-exhausting hop.

        The key is loaded *first*, fail-closed, before ``Engine.step`` is
        called — so a missing key leaves the engine's in-memory state
        untouched as well as the bridge unwritten.

        Emit classification is crash-safe (plan §2.4.1). ``PIPELINE_ORDER``
        excludes ``ESCALATED`` and ``HUMAN_QUESTION``, so those are NEVER
        passed to ``.index()`` — the escalated hop is detected by
        ``StepResult.escalated`` and the normal-revert branch is guarded by
        explicit ``in PIPELINE_ORDER`` membership before any index compare.
        Emission is telemetry: it degrades (never raises) and never blocks the
        advance (the bridge write above is the authority-bearing act).
        """

        # Fail-closed *before* touching engine state: an unpublishable
        # advance must not happen at all, not happen-but-not-be-visible.
        self._load_key()

        from_state = self.engine.state
        result = self.engine.step(judge)
        self.write_bridge(minted_at=minted_at)

        self._emit_revert_if_any(
            from_state, result, agent=agent, originating_turn=originating_turn
        )
        return result

    def advance_on_clean_completion(
        self, minted_at: int | None = None
    ) -> StepResult:
        """Thin wrapper over ``advance`` with the trivial PASS judge — the
        mechanically-observed clean-completion path. Kept for callers/tests
        that predate the generalized ``advance``."""

        return self.advance(_trivial_completion_judge, minted_at=minted_at)

    def _emit_revert_if_any(
        self,
        from_state: PipelineState,
        result: StepResult,
        *,
        agent: str | None,
        originating_turn: int,
    ) -> None:
        """Crash-safe revert classification + emit (plan §2.4.1). No-op when
        no bus is injected. Never raises (emit degrades on its own)."""

        if self._bus is None:
            return

        to_state = result.state

        if result.escalated:
            # (A) The budget-exhausting hop. `to_state` is ESCALATED (excluded
            # from PIPELINE_ORDER) -> use the explicit constant, never index().
            # This IS the Nth revert and the most important to log.
            payload = RevertOccurredEvent(
                from_state=from_state.value,
                to_state=PipelineState.ESCALATED.value,
                revert_count=self.engine.revert_count,
                escalated=True,
            )
        elif (
            from_state in PIPELINE_ORDER
            and to_state in PIPELINE_ORDER
            and PIPELINE_ORDER.index(to_state) < PIPELINE_ORDER.index(from_state)
        ):
            # (B) A normal backward revert (FAIL routed to an earlier stage).
            payload = RevertOccurredEvent(
                from_state=from_state.value,
                to_state=to_state.value,
                revert_count=self.engine.revert_count,
                escalated=False,
            )
        else:
            # (C) Forward PASS, NEEDS_HUMAN/HUMAN_QUESTION, or any non-revert:
            # not a revert -> emit nothing. Must not raise (no index() reached
            # a non-member state, because the (B) guards short-circuit first).
            return

        self._bus.emit(
            EventKind.REVERT_OCCURRED,
            payload,
            emitter="gleipnir-engine-driver",
            enforcement_surface="g5-engine",
            action="revert",
            agent=agent,
            originating_turn=originating_turn,
            artifact_ref=self.engine.pipeline_id,
        )
