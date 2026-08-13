"""Gleipnir G-4 event bus — first slice.

Public API surface. Mirrors the ``verify/`` and ``engine/`` package layout
(`.gleipnir/plans/g4-bus-first-slice.md` §2.1): ``events.py`` owns the typed
schema, ``emit.py`` owns the append/JSONL transport. Stdlib-only; no HMAC, no
import of ``verify/marker.py``, no S-2 key in this path (D3).
"""

from __future__ import annotations

from gleipnir.bus.emit import EmitResult, EventBus
from gleipnir.bus.events import (
    EVENT_VERSION,
    BusError,
    Envelope,
    Event,
    EventKind,
    GateReachedEvent,
    NeedsHumanRaisedEvent,
    RevertOccurredEvent,
)

__all__ = [
    "EVENT_VERSION",
    "BusError",
    "Envelope",
    "Event",
    "EventKind",
    "RevertOccurredEvent",
    "NeedsHumanRaisedEvent",
    "GateReachedEvent",
    "EmitResult",
    "EventBus",
]
