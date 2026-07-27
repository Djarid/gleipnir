"""Gleipnir G-4d metrics ledger — the discriminated honesty types (D3).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D3 + Assemble step 1 +
Stress-test checks C/D/E/F. Built and tested BEFORE any reducer or number
exists — the anti-vanity guarantee precedes the numbers (spec section 185:
"an unlabelled estimate is a vanity metric").

Three genuinely distinct dataclass kinds, mirroring the bus's typed-not-
stringly discipline (`gleipnir.bus.events`):

  * ``Measured`` — a deterministically-off-the-bus quantity. No calibration
    requirement. ``denominator`` is always inspectable (the escalation-rate
    0/0 convention lives in `reduce.py`, not here).
  * ``Estimated`` — FAIL-CLOSED at construction: requires a
    ``CalibrationBand``; and, when ``kind is EstimateKind.UPLIFT``, requires
    a versioned ``NotionalHumanRate``. The uplift precondition is gated by
    the TYPED ``EstimateKind`` discriminant, identity-checked
    (``is EstimateKind.UPLIFT``) — never a field-string equality check on the
    literal word "uplift". Keying
    a fail-closed rule off a string inside the very type built to eliminate
    stringly-typing would reintroduce the defect the type exists to close.
  * ``Gap`` — the explicit "bus-emission gap": a metric whose source event
    kind does not exist yet. A DISTINCT type, never ``Measured(0)`` — a
    consumer can never mistake an absence for a real measured zero.

Every serialized form carries a ``kind`` discriminant
(``"measured"``/``"estimated"``/``"gap"``), mirroring the bus's
``EventKind``-on-the-envelope discipline, so a gap/estimate can never be
mistaken for a measurement on read-back.

Stdlib-only (`.gleipnir/decisions/runtime-and-deps.md`): only ``dataclasses``
and ``enum``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = [
    "LedgerError",
    "EstimateKind",
    "CalibrationBand",
    "NotionalHumanRate",
    "Measured",
    "Estimated",
    "Gap",
    "metric_from_dict",
]


class LedgerError(Exception):
    """Fail-closed construction/contract error for a ledger metric type.

    This is a programmer/contract error (an uncalibrated ``Estimated``, or an
    ``UPLIFT`` estimate with no versioned rate) — not a telemetry fault — so
    raising here is correct, symmetric with ``attempt_gate`` refusing a null
    attestation.
    """


class EstimateKind(str, Enum):
    """The TYPED discriminant that gates ``Estimated``'s extra construction
    requirement. ``UPLIFT`` is the only kind this slice's fail-closed rule
    inspects; other kinds exist so the discriminant is genuinely an enum
    (extensible), not a disguised boolean."""

    UPLIFT = "uplift"
    # Placeholder for a future non-uplift estimate kind (e.g. a calibrated
    # efficiency projection). Its presence proves the versioned-rate
    # requirement is gated by `kind`, not by "any Estimated".
    GENERIC = "generic"


@dataclass(frozen=True)
class CalibrationBand:
    """A calibration range backing an ``Estimated`` value: the honest
    uncertainty band, not a point guess dressed up as precision."""

    low: float
    high: float
    sample_n: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "low": self.low,
            "high": self.high,
            "sample_n": self.sample_n,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class NotionalHumanRate:
    """A versioned, logged notional human rate — the load-bearing assumption
    behind an uplift estimate (spec section 198-199). Versioned so a later
    audit can see exactly which assumption a historical uplift figure used."""

    rate: float
    currency: str
    version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rate": self.rate,
            "currency": self.currency,
            "version": self.version,
        }


@dataclass(frozen=True)
class Measured:
    """A metric with real inputs. No calibration requirement.

    ``denominator`` is always inspectable — for a raw count (e.g.
    ``revert_count``) it is conventionally ``1``; for a derived rate (e.g.
    ``escalation_rate``) it is the count the rate was divided by, and is the
    hook a consumer must check before trusting ``value`` (the zero-
    denominator convention lives in `reduce.py`, not here — this type just
    guarantees the field always exists and is readable).
    """

    name: str
    value: float | int | None
    denominator: int
    provenance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "measured",
            "name": self.name,
            "value": self.value,
            "denominator": self.denominator,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class Estimated:
    """A calibrated estimate. FAIL-CLOSED construction (D3).

    Raises ``LedgerError`` if constructed without a ``CalibrationBand``.
    Raises ``LedgerError`` if ``kind is EstimateKind.UPLIFT`` and no versioned
    ``NotionalHumanRate`` is supplied. Any other ``EstimateKind`` does NOT
    require a ``NotionalHumanRate`` — the requirement is gated strictly by
    the typed discriminant, not by "being an estimate" in general.
    """

    name: str
    value: float
    kind: EstimateKind
    calibration: CalibrationBand | None = None
    notional_human_rate: NotionalHumanRate | None = None

    def __post_init__(self) -> None:
        if self.calibration is None:
            raise LedgerError(
                f"Estimated({self.name!r}) requires a CalibrationBand — "
                "an uncalibrated estimate is a vanity metric (spec section 185)"
            )
        # Typed discriminant, identity-checked -- NOT a name/field string
        # equality check against the literal word "uplift".
        if self.kind is EstimateKind.UPLIFT and self.notional_human_rate is None:
            raise LedgerError(
                f"Estimated({self.name!r}, kind=EstimateKind.UPLIFT) requires "
                "a versioned NotionalHumanRate — uplift's load-bearing "
                "assumption must be logged (spec section 198-199)"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "estimated",
            "name": self.name,
            "value": self.value,
            "estimate_kind": self.kind.value,
            "calibration": (
                None if self.calibration is None else self.calibration.to_dict()
            ),
            "notional_human_rate": (
                None
                if self.notional_human_rate is None
                else self.notional_human_rate.to_dict()
            ),
        }


@dataclass(frozen=True)
class Gap:
    """The explicit "bus-emission gap": a metric with no source event kind
    yet. A DISTINCT type from ``Measured`` — never equals, and never
    serializes as, a numeric ``0``."""

    name: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "gap", "name": self.name, "reason": self.reason}


def metric_from_dict(data: dict[str, Any]) -> Measured | Estimated | Gap:
    """Dispatch on the ``kind`` discriminant to reconstruct the correct
    metric type. A ``gap``/``estimated`` dict can never deserialize into a
    ``Measured`` — there is no code path here that constructs ``Measured``
    from anything but a ``kind == "measured"`` dict, and ``Measured``'s
    required fields (``denominator``, ``provenance``) are structurally
    absent from a gap/estimated dict.
    """

    discriminant = data.get("kind")
    if discriminant == "measured":
        return Measured(
            name=data["name"],
            value=data["value"],
            denominator=data["denominator"],
            provenance=data["provenance"],
        )
    if discriminant == "gap":
        return Gap(name=data["name"], reason=data["reason"])
    if discriminant == "estimated":
        calibration = None
        raw_calibration = data.get("calibration")
        if raw_calibration is not None:
            calibration = CalibrationBand(
                low=raw_calibration["low"],
                high=raw_calibration["high"],
                sample_n=raw_calibration["sample_n"],
                updated_at=raw_calibration["updated_at"],
            )
        notional_human_rate = None
        raw_rate = data.get("notional_human_rate")
        if raw_rate is not None:
            notional_human_rate = NotionalHumanRate(
                rate=raw_rate["rate"],
                currency=raw_rate["currency"],
                version=raw_rate["version"],
            )
        return Estimated(
            name=data["name"],
            value=data["value"],
            kind=EstimateKind(data["estimate_kind"]),
            calibration=calibration,
            notional_human_rate=notional_human_rate,
        )
    raise LedgerError(f"unknown metric discriminant kind={discriminant!r}")
