"""Gleipnir G-4 event bus — emit / JSONL append API.

Plan: `.gleipnir/plans/g4-bus-first-slice.md`, §2.3, §2.6 edge case 3.

``EventBus`` owns one session's append-only JSONL stream under
``.gleipnir/logs/<session_id>.jsonl`` (Tier-1 RETRIEVED — observation-only;
see `.gleipnir/decisions/gleipnir-layout-and-memory-model.md`). It assigns
the monotonic per-bus ``sequence`` and stamps ``timestamp``/``version`` so
callers never invent provenance ordering.

**Degrade, never raise, on an un-writable `logs/`.** `logs/` is Tier-1
observation-only: emission is telemetry, not a gate. A telemetry write that
raised could take down a legitimate higher-tier advance (the driver's
engine step + bridge write), inverting the authority ladder. So `emit`
catches `OSError` (mkdir/open/write failures), returns a failure signal
(`EmitResult(ok=False, ...)`), and increments `self.dropped` so the drop is
observable rather than silent.

Stdlib-only (`.gleipnir/decisions/runtime-and-deps.md`): only ``os``,
``pathlib`` and ``datetime`` beyond what ``events.py`` already uses. No
import of ``verify/marker.py``, no HMAC, no S-2 key (D3).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gleipnir.bus.events import EVENT_VERSION, Envelope, Event, EventKind

__all__ = ["EmitResult", "EventBus", "DEFAULT_LOGS_DIR"]

# Tier-1 RETRIEVED (`.gleipnir/decisions/gleipnir-layout-and-memory-model.md`).
DEFAULT_LOGS_DIR = Path(".gleipnir") / "logs"


@dataclass(frozen=True)
class EmitResult:
    """The outcome of one ``EventBus.emit`` call.

    ``ok`` is ``False`` on a degraded (un-writable ``logs/``) emit — this is
    a failure SIGNAL the caller may observe, never an exception. ``event``
    is the fully-built ``Event`` regardless of whether the append landed
    (so a caller/test can inspect what *would* have been written), and
    ``reason`` carries the underlying error text on failure.
    """

    ok: bool
    event: Event | None = None
    reason: str | None = None


class EventBus:
    """Owns one session's append-only JSONL event stream.

    Construction does not touch the filesystem — the ``logs_dir`` is
    created lazily, on first ``emit``, matching
    ``Driver.write_bridge``'s ``parent.mkdir(parents=True, exist_ok=True)``
    pattern.
    """

    def __init__(
        self,
        session_id: str,
        logs_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.session_id = session_id
        self.logs_dir = Path(logs_dir) if logs_dir is not None else DEFAULT_LOGS_DIR
        self.path = self.logs_dir / f"{session_id}.jsonl"
        self._sequence = 0
        # Tier-1 telemetry drop counter (edge case 3): incremented, never
        # silently absorbed, whenever an emit degrades instead of landing.
        self.dropped = 0

    def emit(
        self,
        kind: EventKind,
        payload: Any,
        *,
        emitter: str,
        enforcement_surface: str,
        action: str,
        agent: str | None = None,
        originating_turn: int = 0,
        artifact_ref: str | None = None,
    ) -> EmitResult:
        """Build one ``Event`` (stamping ``version``/``sequence``/
        ``timestamp``) and append it as one JSONL line.

        Never raises: an un-writable ``logs_dir`` (mkdir or append failure)
        degrades to ``EmitResult(ok=False, ...)`` and increments
        ``self.dropped`` (§2.6 edge case 3) rather than propagating into the
        caller's control flow.
        """

        self._sequence += 1
        envelope = Envelope(
            emitter=emitter,
            enforcement_surface=enforcement_surface,
            agent=agent,
            action=action,
            session_id=self.session_id,
            originating_turn=originating_turn,
            artifact_ref=artifact_ref,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=EVENT_VERSION,
            sequence=self._sequence,
            kind=kind,
        )
        event = Event(envelope=envelope, payload=payload)

        try:
            # Serialize + append. Catch OSError (un-writable logs) AND
            # TypeError/ValueError (a future payload type with a
            # non-JSON-serializable field): telemetry must NEVER raise into the
            # caller's control flow — it degrades to dropped++, honouring the
            # module contract even for a not-yet-existing bad payload kind.
            line = event.to_json_line()
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
        except (OSError, TypeError, ValueError) as exc:
            self.dropped += 1
            return EmitResult(ok=False, event=event, reason=str(exc))

        return EmitResult(ok=True, event=event)
