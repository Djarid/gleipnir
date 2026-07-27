"""Gleipnir G-4d metrics ledger — first slice.

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`. Public API surface.
Mirrors the `bus/`/`verify/` package layout: `metric.py` owns the
discriminated honesty types (D3), `reduce.py` owns the reduction skeleton +
the one real (revert-derived) metric (D1), `ratetable.py` owns the rate-table
loader + G-3.1 keyed digest (D2, cost deferred), `reconcile.py` owns the
self-consistency re-derivation + gap-report (D4).

Stdlib-only (`.gleipnir/decisions/runtime-and-deps.md`); the ledger MAY
import `hashlib`/`hmac` via `verify.marker` for the rate-table digest
(unlike the bus, whose D3 forbade it — the rate table IS authority-bearing
config).
"""

from __future__ import annotations

from gleipnir.ledger.metric import (
    CalibrationBand,
    EstimateKind,
    Estimated,
    Gap,
    LedgerError,
    Measured,
    NotionalHumanRate,
    metric_from_dict,
)
from gleipnir.ledger.ratetable import (
    DEFAULT_RATE_TABLE_DIGEST_PATH,
    DEFAULT_RATE_TABLE_PATH,
    RateTableLoadResult,
    compute_rate_table_digest,
    load_rate_table,
)
from gleipnir.ledger.reconcile import ReconciliationReport, reconcile
from gleipnir.ledger.reduce import SEAM_NAMES, LedgerReport, build_seam_gaps, reduce

__all__ = [
    "CalibrationBand",
    "EstimateKind",
    "Estimated",
    "Gap",
    "LedgerError",
    "Measured",
    "NotionalHumanRate",
    "metric_from_dict",
    "LedgerReport",
    "build_seam_gaps",
    "reduce",
    "SEAM_NAMES",
    "DEFAULT_RATE_TABLE_DIGEST_PATH",
    "DEFAULT_RATE_TABLE_PATH",
    "RateTableLoadResult",
    "compute_rate_table_digest",
    "load_rate_table",
    "ReconciliationReport",
    "reconcile",
]
