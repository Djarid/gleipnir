"""Gleipnir G-5 wire-in — the Python-engine <-> TS-hook state bridge marker.

Adapted from ``src/gleipnir/verify/marker.py`` (G-3.1), **not** reused
verbatim. Per the plan (`.gleipnir/plans/engine-wire-in.md`, Trace ->
"the key design problem"): ``Marker``/``validate`` in ``verify/marker.py``
bind an HMAC to a **tree hash** that is independently recomputable from the
filesystem (``compute_tree_hash``). A pipeline state has no such
independent recompute — there is no "current state" to hash off the tree;
the bridge payload *is* the state. So the tree-binding check is **replaced**,
not merely satisfied, by a direct binding to the state payload itself:

    MAC = HMAC(key, canonical(version, pipeline_state, allowed_agents, minted_at))

What is reused from ``verify/marker.py`` (unchanged, imported, not copied):
  * ``load_key`` — the fail-closed key-loading routine (env var or explicit
    path; empty/missing/unreadable key all raise ``KeyUnavailable``).
  * ``KeyUnavailable`` / the fail-closed-on-key-absence posture generally.
  * The overall shape of "mint requires the key; validate recomputes the MAC
    in constant time and checks freshness; any doubt returns False."

What is **not** reused: ``tree_hash``, ``compute_tree_hash``,
``current_tree_hash`` — there is nothing here to recompute from a tree, so
those have no analogue. ``StateMarker`` carries ``pipeline_state`` and
``allowed_agents`` directly instead of a hash of the source tree.
"""

from __future__ import annotations

import hmac
import json
import time
from dataclasses import asdict, dataclass
from typing import Iterable

from gleipnir.verify.marker import (
    DEFAULT_MAX_AGE_SECONDS,
    DIGEST,
    KeyUnavailable,
    MarkerError,
    load_key,
)

__all__ = [
    "STATE_MARKER_VERSION",
    "DEFAULT_MAX_AGE_SECONDS",
    "StateMarker",
    "StateMarkerError",
    "KeyUnavailable",
    "load_key",
    "mint_state",
    "validate_state",
]

STATE_MARKER_VERSION = 1

# Re-exported under a bridge-local name so callers of this module are not
# forced to know it is, today, the same class as verify/marker.py's. If the
# two error hierarchies ever need to diverge, this is the one place to
# change.
StateMarkerError = MarkerError


@dataclass(frozen=True)
class StateMarker:
    """A signed bridge payload: current pipeline state + allowed-agents
    projection, bound under one MAC.

    ``allowed_agents`` is the current-state -> allowed-role projection
    (``gleipnir.engine.allow_table``), re-emitted alongside the state on
    every write so the TS hook reads it from here rather than embedding a
    static copy (no second sequencing authority; see the plan's Assemble
    step 3).
    """

    version: int
    pipeline_state: str
    allowed_agents: tuple[str, ...]
    minted_at: int
    mac: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @staticmethod
    def from_json(text: str) -> "StateMarker":
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise StateMarkerError(
                f"bridge payload is not valid JSON: {exc}"
            ) from exc
        try:
            allowed_agents_raw = data["allowed_agents"]
            if not isinstance(allowed_agents_raw, (list, tuple)):
                raise TypeError(
                    f"allowed_agents must be a list, got {type(allowed_agents_raw)!r}"
                )
            return StateMarker(
                version=int(data["version"]),
                pipeline_state=str(data["pipeline_state"]),
                allowed_agents=tuple(str(a) for a in allowed_agents_raw),
                minted_at=int(data["minted_at"]),
                mac=str(data["mac"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise StateMarkerError(
                f"bridge payload is missing/invalid fields: {exc}"
            ) from exc


def _canonical_signing_input(
    version: int,
    pipeline_state: str,
    allowed_agents: Iterable[str],
    minted_at: int,
) -> bytes:
    """The exact bytes the MAC covers.

    ``allowed_agents`` is sorted before joining so that an honestly-produced
    marker's wire order never affects validity, while any *content* change
    (an added, removed, or one-byte-mutated agent name) changes the joined
    string and therefore the MAC. Fields are length-delimited by distinct
    control bytes so no field/sub-field boundary can be shifted by choosing
    clever contents (the same concatenation-ambiguity concern
    ``verify/marker.py`` documents).
    """

    agents_joined = "\x1e".join(sorted(str(a) for a in allowed_agents))
    parts = [str(version), pipeline_state, agents_joined, str(minted_at)]
    return b"\x1f".join(p.encode("utf-8") for p in parts)


def mint_state(
    pipeline_state: str,
    allowed_agents: Iterable[str],
    key: bytes,
    minted_at: int | None = None,
) -> StateMarker:
    """Produce a signed bridge marker. Requires the key — the one operation
    an agent without it cannot perform."""

    ts = int(minted_at if minted_at is not None else time.time())
    agents_tuple = tuple(sorted(str(a) for a in allowed_agents))
    signing_input = _canonical_signing_input(
        STATE_MARKER_VERSION, pipeline_state, agents_tuple, ts
    )
    mac = hmac.new(key, signing_input, DIGEST).hexdigest()
    return StateMarker(
        version=STATE_MARKER_VERSION,
        pipeline_state=pipeline_state,
        allowed_agents=agents_tuple,
        minted_at=ts,
        mac=mac,
    )


def validate_state(
    marker: StateMarker,
    key: bytes,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: int | None = None,
) -> bool:
    """Validate a bridge marker. Fail-closed on any doubt.

    Returns True only if the version matches, the HMAC verifies in constant
    time against the marker's own ``pipeline_state``/``allowed_agents``, and
    the marker is fresh. Any failure returns False — never raises for a
    merely-invalid marker (mirrors ``verify/marker.py::validate``).
    """

    if marker.version != STATE_MARKER_VERSION:
        return False

    expected = hmac.new(
        key,
        _canonical_signing_input(
            marker.version,
            marker.pipeline_state,
            marker.allowed_agents,
            marker.minted_at,
        ),
        DIGEST,
    ).hexdigest()
    if not hmac.compare_digest(marker.mac, expected):
        return False

    current = int(now if now is not None else time.time())
    age = current - marker.minted_at
    if age < 0 or age > max_age_seconds:
        return False

    return True
