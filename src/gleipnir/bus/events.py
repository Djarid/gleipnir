"""Gleipnir G-4 event bus — typed event schema (Envelope + EventKind + payload).

Spec anchor: G-4a ("Every guard... emits a typed event: guard identity,
enforcement surface, agent, attempted action, session id, originating turn,
artifact reference, timestamp. The observer consumes the typed stream and
never parses a human-readable string.") and G-4b (a "revert occurred" is a
named interoceptive fact).

Plan: `.gleipnir/plans/g4-bus-first-slice.md`, §2.2 (D1, Option C: typed
envelope + typed per-kind payload — never a free-string dict).

**Read-path contract (binding).** ``Event.from_json_line`` reconstructs a
TYPED object: it dispatches on ``kind`` to a registered payload dataclass via
a lookup table (``_PAYLOAD_CLASSES``) and returns real dataclass instances. A
consumer reads ``evt.payload.from_state`` by attribute access. This module
does not import ``re`` and does not call ``str.split`` on any message field
— see ``tests/test_bus_events.py`` for the static check that enforces this
as more than a comment.

**Stdlib-only** (`.gleipnir/decisions/runtime-and-deps.md`): only ``json``,
``dataclasses`` and ``enum`` are used. No HMAC, no key, no import of
``verify/marker.py`` — integrity is deliberately out of scope this
slice (D3); ``version`` reserves the slot for later.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

__all__ = [
    "EVENT_VERSION",
    "BusError",
    "EventKind",
    "Envelope",
    "RevertOccurredEvent",
    "NeedsHumanRaisedEvent",
    "GateReachedEvent",
    "Event",
]

# Schema version stamped on every envelope. Reserved integrity slot (D3):
# a later ledger slice may add a keyed digest without a format break.
EVENT_VERSION = 1


class BusError(Exception):
    """A read-path fault: malformed JSON, an unknown/future ``EventKind``, or
    missing/invalid envelope fields. Fail-closed on read — this is a
    corrupt-log / version-skew condition, never a routing decision."""


# ---------------------------------------------------------------------------
# EventKind — str-valued like PipelineState/Verdict, extensible.
# ---------------------------------------------------------------------------


class EventKind(str, Enum):
    REVERT_OCCURRED = "revert_occurred"  # G-4b named interoceptive fact
    # G-4/precept-10 interoceptive fact: a stage's judge asked for a human
    # (`.gleipnir/plans/g4-terminal-events.md` D1/D2).
    NEEDS_HUMAN_RAISED = "needs_human_raised"
    # G-3.2 terminal fact: the GIT -> GATE clean-completion transition
    # (`Engine.attempt_gate` succeeding) (`g4-terminal-events.md` D1/D3).
    GATE_REACHED = "gate_reached"
    # Future kinds (NOT this slice): GUARD_TRIGGERED, TASK_ABANDONED, ...


# ---------------------------------------------------------------------------
# Envelope — the eight G-4a common fields + version/sequence/kind.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Envelope:
    """The eight G-4a common fields, plus the schema-evolution/ordering
    fields this slice adds (D1 + D2).

    ``agent`` and ``artifact_ref`` are always structurally present (the
    field exists on every Envelope) but nullable-VALUED (``str | None``) —
    the envelope *shape* is fixed; individual values may be absent.
    """

    emitter: str
    enforcement_surface: str
    agent: str | None
    action: str
    session_id: str
    originating_turn: int
    artifact_ref: str | None
    timestamp: str
    version: int
    sequence: int
    kind: EventKind


# ---------------------------------------------------------------------------
# Per-kind typed payloads.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RevertOccurredEvent:
    """Payload for ``EventKind.REVERT_OCCURRED``.

    ``escalated`` lets a consumer distinguish the terminal
    budget-exhausting revert (to ``PipelineState.ESCALATED``) from an
    ordinary backward revert by TYPED FIELD, never by string-matching
    ``to_state``.
    """

    from_state: str
    to_state: str
    revert_count: int
    escalated: bool = False


@dataclass(frozen=True)
class NeedsHumanRaisedEvent:
    """Payload for ``EventKind.NEEDS_HUMAN_RAISED``.

    ``from_state`` names the main-line stage whose judge returned
    ``Verdict.NEEDS_HUMAN`` (precept 10's interoceptive "work asked for a
    human" fact). The engine's transition table always routes this hop to
    ``PipelineState.HUMAN_QUESTION`` — that target is an invariant, not a
    variable fact, so no ``to_state`` field is carried (mirrors D2's
    rationale in `.gleipnir/plans/g4-terminal-events.md`).
    """

    from_state: str


@dataclass(frozen=True)
class GateReachedEvent:
    """Payload for ``EventKind.GATE_REACHED``.

    ``pipeline_id`` names which pipeline reached the G-3.2 clean-completion
    terminal (a successful ``Engine.attempt_gate``), read from
    ``Engine.pipeline_id`` by attribute — never string-matched.
    """

    pipeline_id: str


# kind -> payload dataclass, for typed dispatch on read. Adding a new
# EventKind means adding one entry here, not a branch of string parsing.
_PAYLOAD_CLASSES: dict[EventKind, type] = {
    EventKind.REVERT_OCCURRED: RevertOccurredEvent,
    EventKind.NEEDS_HUMAN_RAISED: NeedsHumanRaisedEvent,
    EventKind.GATE_REACHED: GateReachedEvent,
}


# ---------------------------------------------------------------------------
# Event — Envelope + typed payload, composed. Serialization.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """A complete event: the provenance ``Envelope`` plus a typed
    per-kind ``payload``. ``kind`` (on ``envelope``) and the payload's type
    are kept consistent by construction and by ``from_json_line``'s kind ->
    class dispatch table."""

    envelope: Envelope
    payload: Any

    @property
    def kind(self) -> EventKind:
        return self.envelope.kind

    def to_json_line(self) -> str:
        """Exactly one JSON line (no embedded newline), canonical form —
        mirrors ``verify/marker.py`` / ``engine/bridge.py``'s
        ``json.dumps(..., sort_keys=True, separators=(",", ":"))`` pattern."""

        data: dict[str, Any] = asdict(self.envelope)
        data["kind"] = self.envelope.kind.value
        data["payload"] = asdict(self.payload)
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def from_json_line(line: str) -> "Event":
        """Reconstruct a TYPED ``Event`` from one JSONL line.

        Dispatches on ``kind`` to the registered payload dataclass (a dict
        lookup, never a string/regex/substring parse) and returns real
        dataclass instances so a consumer reads fields by attribute access.
        Fail-closed (raises ``BusError``) on malformed JSON, an
        unknown/unregistered ``kind``, or missing/invalid fields.
        """

        try:
            data = json.loads(line)
        except (ValueError, TypeError) as exc:
            raise BusError(f"event line is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise BusError(f"event line is not a JSON object: {data!r}")

        try:
            kind = EventKind(data["kind"])
        except KeyError as exc:
            raise BusError(f"event line missing 'kind': {exc}") from exc
        except ValueError as exc:
            raise BusError(f"event line names an unknown EventKind: {exc}") from exc

        payload_cls = _PAYLOAD_CLASSES.get(kind)
        if payload_cls is None:
            raise BusError(f"no payload dataclass registered for kind {kind!r}")

        try:
            payload_data = data["payload"]
            if not isinstance(payload_data, dict):
                raise TypeError(f"payload must be a JSON object, got {type(payload_data)!r}")
            payload = payload_cls(**payload_data)
        except (KeyError, TypeError) as exc:
            raise BusError(f"malformed payload for kind {kind!r}: {exc}") from exc

        try:
            agent_raw = data["agent"]
            artifact_ref_raw = data["artifact_ref"]
            envelope = Envelope(
                emitter=str(data["emitter"]),
                enforcement_surface=str(data["enforcement_surface"]),
                agent=(None if agent_raw is None else str(agent_raw)),
                action=str(data["action"]),
                session_id=str(data["session_id"]),
                originating_turn=int(data["originating_turn"]),
                artifact_ref=(None if artifact_ref_raw is None else str(artifact_ref_raw)),
                timestamp=str(data["timestamp"]),
                version=int(data["version"]),
                sequence=int(data["sequence"]),
                kind=kind,
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise BusError(
                f"event line missing/invalid envelope fields: {exc}"
            ) from exc

        return Event(envelope=envelope, payload=payload)
