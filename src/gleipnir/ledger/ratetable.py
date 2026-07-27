"""Gleipnir G-4d metrics ledger — rate-table loader + G-3.1 keyed digest (D2).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D2 + Assemble step 3 +
Stress-test checks G/H.

The rate table (once the operator authors it, Tier-3 POLICY) is what would
let the ledger compute a cost NUMBER. This slice builds the loader and its
G-3.1 keyed-digest verification NOW, so the machinery is ready and provably
fail-closed — but emits NO cost number this slice, UNCONDITIONALLY, even
when the digest verifies (D2: publishing cost pre-S-2 would assert an
unforgeability guarantee the substrate does not yet back — spec section 193).

Reuses `verify.marker`'s `load_key` and HMAC-with-`compare_digest` PRIMITIVES
— NOT the full `Marker`/`validate` freshness pipeline (that pipeline binds to
a source-tree hash and a mint timestamp, neither of which apply to a static
Tier-3 config file).

FAIL-CLOSED on any doubt: missing table, missing/unreadable key, or digest
mismatch all return a `Gap` with a precise reason. This loader NEVER raises
into a caller's reduction and NEVER returns a guessed rate.

The table file and its approved digest are Tier-3 POLICY (operator hand-off,
`.gleipnir/keys/`) — this module does not create or write them; tests supply
their own fixtures under `tmp_path`.

Stdlib-only (`.gleipnir/decisions/runtime-and-deps.md`): ``hmac``, ``json``,
plus `verify.marker`'s `load_key` (which itself uses only stdlib).
"""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gleipnir.ledger.metric import Gap
from gleipnir.verify.marker import KeyUnavailable, load_key

__all__ = [
    "DEFAULT_RATE_TABLE_PATH",
    "DEFAULT_RATE_TABLE_DIGEST_PATH",
    "RateTableLoadResult",
    "compute_rate_table_digest",
    "load_rate_table",
]

DIGEST_ALGO = "sha256"

# Tier-3 POLICY home (operator hand-off; NOT created by this module or its
# tests -- see plan section 2.4). Overridable per-call for tests.
DEFAULT_RATE_TABLE_PATH = Path(".gleipnir") / "keys" / "rate-table.json"
DEFAULT_RATE_TABLE_DIGEST_PATH = Path(".gleipnir") / "keys" / "rate-table.digest"

_COST_GAP_NAME = "cost"
_DEFERRED_REASON = (
    "cost deferred until the S-2 mount makes the rate table structurally "
    "agent-unwritable (spec section 193) -- digest verified, but the number "
    "is withheld unconditionally this slice"
)


@dataclass(frozen=True)
class RateTableLoadResult:
    """The fail-closed outcome of one rate-table load attempt.

    ``ok`` is True only when the table, digest and key all resolve AND the
    keyed HMAC matches. ``cost_gap`` is ALWAYS populated -- even when
    ``ok`` is True, the cost slot stays a `Gap` this slice (D2: the
    deferral is unconditional, not contingent on the digest). ``table`` is
    populated only when ``ok`` is True (proving the digest verified), but
    no caller in this slice reads a cost number out of it.
    """

    ok: bool
    cost_gap: Gap
    table: dict[str, Any] | None = None


def compute_rate_table_digest(table_bytes: bytes, key: bytes) -> str:
    """HMAC-SHA256 over the raw table bytes, keyed by the G-3.1 verifier
    key. Reuses the HMAC primitive directly (mirroring `verify/marker.py`'s
    pattern) -- not `mint`/`validate`, whose tree-hash + freshness binding
    is specific to the source/test tree, not a static config file.
    """

    return hmac.new(key, table_bytes, DIGEST_ALGO).hexdigest()


def load_rate_table(
    table_path: str | Path | None = None,
    digest_path: str | Path | None = None,
    key_file: str | Path | None = None,
) -> RateTableLoadResult:
    """Load and verify the Tier-3 rate table. FAIL-CLOSED on any doubt.

    Never raises into the caller's control flow. Never returns a guessed
    rate. Never emits a cost number -- ``cost_gap`` is always the returned
    signal for the cost slot, regardless of whether verification succeeded.
    """

    resolved_table_path = Path(table_path) if table_path is not None else DEFAULT_RATE_TABLE_PATH
    resolved_digest_path = (
        Path(digest_path) if digest_path is not None else DEFAULT_RATE_TABLE_DIGEST_PATH
    )

    try:
        key = load_key(key_file)
    except KeyUnavailable as exc:
        return RateTableLoadResult(
            ok=False,
            cost_gap=Gap(_COST_GAP_NAME, f"marker key unavailable: {exc}"),
        )

    try:
        table_bytes = resolved_table_path.read_bytes()
    except OSError as exc:
        return RateTableLoadResult(
            ok=False,
            cost_gap=Gap(
                _COST_GAP_NAME, f"rate table absent at {resolved_table_path}: {exc}"
            ),
        )

    try:
        # UnicodeDecodeError is a ValueError, NOT an OSError -- a
        # corrupt-bytes digest file must degrade to a cost Gap, never raise
        # into the caller (the loader's "never raises" contract).
        approved_digest = resolved_digest_path.read_text(encoding="utf-8").strip()
    except (OSError, ValueError) as exc:
        return RateTableLoadResult(
            ok=False,
            cost_gap=Gap(
                _COST_GAP_NAME,
                f"rate table digest unreadable at {resolved_digest_path}: {exc}",
            ),
        )

    computed_digest = compute_rate_table_digest(table_bytes, key)
    if not hmac.compare_digest(computed_digest, approved_digest):
        return RateTableLoadResult(
            ok=False,
            cost_gap=Gap(
                _COST_GAP_NAME, "rate table digest mismatch -- refusing to emit cost"
            ),
        )

    try:
        table = json.loads(table_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return RateTableLoadResult(
            ok=False,
            cost_gap=Gap(_COST_GAP_NAME, f"rate table is not valid JSON: {exc}"),
        )

    return RateTableLoadResult(ok=True, cost_gap=Gap(_COST_GAP_NAME, _DEFERRED_REASON), table=table)
