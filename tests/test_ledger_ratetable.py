"""Tests for the G-4d ledger rate-table loader (`src/gleipnir/ledger/ratetable.py`).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D2 + Assemble step 3 +
Stress-test checks G/H. Written RED-first, before `ratetable.py` existed.

Fixtures supply their OWN rate table + key under `tmp_path` (mirroring
`test_marker.py`) — this module never touches the real Tier-3
`.gleipnir/keys/` home, and never creates the rate-table file or its digest
there (that remains an operator hand-off, plan section 2.4).

Covers:
  - Valid table + matching approved digest -> loads (`ok=True`), but cost
    stays a `Gap` this slice regardless (S-2 deferral, D2).
  - Missing table / missing digest / digest mismatch / key unavailable ->
    each returns a `Gap` with a precise reason; never a guessed rate.
  - The loader never raises into a caller's control flow.
  - No cost NUMBER is ever produced by this module.
"""

from __future__ import annotations

import json
from pathlib import Path

from gleipnir.ledger.metric import Gap
from gleipnir.ledger.ratetable import (
    RateTableLoadResult,
    compute_rate_table_digest,
    load_rate_table,
)

VERIFIER_KEY = b"rate-table-verifier-key-not-on-agent-surface"


def _key_file(tmp_path: Path, contents: bytes = VERIFIER_KEY) -> Path:
    kf = tmp_path / "rate-table-key"
    kf.write_bytes(contents)
    return kf


def _table_file(tmp_path: Path, content: dict | None = None) -> Path:
    table = content if content is not None else {"version": "v1", "rates": {"gpt": 0.002}}
    tf = tmp_path / "rate-table.json"
    tf.write_text(json.dumps(table, sort_keys=True))
    return tf


def _matching_digest_file(tmp_path: Path, table_path: Path, key: bytes = VERIFIER_KEY) -> Path:
    digest = compute_rate_table_digest(table_path.read_bytes(), key)
    df = tmp_path / "rate-table.digest"
    df.write_text(digest)
    return df


# ---------------------------------------------------------------------------
# Happy path: valid table + matching digest -> loads, cost STILL a Gap (D2).
# ---------------------------------------------------------------------------


class TestValidTableAndMatchingDigest:
    def test_loads_ok_true(self, tmp_path: Path):
        key_file = _key_file(tmp_path)
        table_path = _table_file(tmp_path)
        digest_path = _matching_digest_file(tmp_path, table_path)

        result = load_rate_table(
            table_path=table_path, digest_path=digest_path, key_file=key_file
        )

        assert isinstance(result, RateTableLoadResult)
        assert result.ok is True
        assert result.table == {"version": "v1", "rates": {"gpt": 0.002}}

    def test_cost_is_still_a_gap_even_when_digest_verifies(self, tmp_path: Path):
        key_file = _key_file(tmp_path)
        table_path = _table_file(tmp_path)
        digest_path = _matching_digest_file(tmp_path, table_path)

        result = load_rate_table(
            table_path=table_path, digest_path=digest_path, key_file=key_file
        )

        assert isinstance(result.cost_gap, Gap)
        assert result.cost_gap.name == "cost"
        assert "deferred" in result.cost_gap.reason.lower()
        assert "s-2" in result.cost_gap.reason.lower()


# ---------------------------------------------------------------------------
# Fail-closed conditions (Stress-test check G).
# ---------------------------------------------------------------------------


class TestFailClosedConditions:
    def test_missing_table_gives_gap_with_reason(self, tmp_path: Path):
        key_file = _key_file(tmp_path)
        missing_table = tmp_path / "no-such-table.json"
        digest_path = tmp_path / "irrelevant.digest"
        digest_path.write_text("deadbeef")

        result = load_rate_table(
            table_path=missing_table, digest_path=digest_path, key_file=key_file
        )

        assert result.ok is False
        assert result.table is None
        assert "absent" in result.cost_gap.reason.lower()

    def test_missing_digest_gives_gap_with_reason(self, tmp_path: Path):
        key_file = _key_file(tmp_path)
        table_path = _table_file(tmp_path)
        missing_digest = tmp_path / "no-such-digest.digest"

        result = load_rate_table(
            table_path=table_path, digest_path=missing_digest, key_file=key_file
        )

        assert result.ok is False
        assert result.table is None
        assert "digest" in result.cost_gap.reason.lower()

    def test_digest_mismatch_gives_gap_with_reason_never_a_guessed_rate(
        self, tmp_path: Path
    ):
        key_file = _key_file(tmp_path)
        table_path = _table_file(tmp_path)
        digest_path = tmp_path / "rate-table.digest"
        digest_path.write_text("0" * 64)  # wrong digest

        result = load_rate_table(
            table_path=table_path, digest_path=digest_path, key_file=key_file
        )

        assert result.ok is False
        assert result.table is None
        assert "mismatch" in result.cost_gap.reason.lower()

    def test_corrupt_bytes_digest_file_degrades_to_gap_never_raises(
        self, tmp_path: Path
    ):
        """A digest file with invalid UTF-8 bytes must degrade to a cost Gap,
        not propagate UnicodeDecodeError (a ValueError, not an OSError) into
        the caller -- the loader's 'never raises' contract."""

        key_file = _key_file(tmp_path)
        table_path = _table_file(tmp_path)
        digest_path = tmp_path / "rate-table.digest"
        digest_path.write_bytes(b"\xff\xfe not utf-8")

        result = load_rate_table(  # must not raise
            table_path=table_path, digest_path=digest_path, key_file=key_file
        )

        assert result.ok is False
        assert result.table is None
        assert "digest" in result.cost_gap.reason.lower()

    def test_key_unavailable_gives_gap_with_reason(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
        table_path = _table_file(tmp_path)
        digest_path = tmp_path / "rate-table.digest"
        digest_path.write_text("irrelevant")

        result = load_rate_table(table_path=table_path, digest_path=digest_path, key_file=None)

        assert result.ok is False
        assert result.table is None
        assert "key" in result.cost_gap.reason.lower()

    def test_wrong_key_gives_digest_mismatch_gap(self, tmp_path: Path):
        wrong_key_file = tmp_path / "wrong-key"
        wrong_key_file.write_bytes(b"wrong-key")
        table_path = _table_file(tmp_path)
        digest_path = _matching_digest_file(tmp_path, table_path, key=VERIFIER_KEY)

        result = load_rate_table(
            table_path=table_path, digest_path=digest_path, key_file=wrong_key_file
        )

        assert result.ok is False
        assert "mismatch" in result.cost_gap.reason.lower()

    def test_malformed_table_json_gives_gap_with_reason(self, tmp_path: Path):
        key_file = _key_file(tmp_path)
        table_path = tmp_path / "rate-table.json"
        table_path.write_bytes(b"{ not valid json")
        digest_path = _matching_digest_file(tmp_path, table_path)

        result = load_rate_table(
            table_path=table_path, digest_path=digest_path, key_file=key_file
        )

        assert result.ok is False
        assert result.table is None
        assert "json" in result.cost_gap.reason.lower()

    def test_loader_never_raises_across_all_fail_closed_conditions(self, tmp_path: Path):
        """A defensive sweep: none of the fail-closed conditions above may
        propagate an exception into the caller."""

        attempts = [
            dict(table_path=tmp_path / "nope.json", digest_path=tmp_path / "nope.digest", key_file=_key_file(tmp_path)),
            dict(table_path=_table_file(tmp_path), digest_path=tmp_path / "nope.digest", key_file=_key_file(tmp_path)),
        ]
        for kwargs in attempts:
            result = load_rate_table(**kwargs)  # must not raise
            assert isinstance(result, RateTableLoadResult)
            assert result.ok is False


# ---------------------------------------------------------------------------
# Stress-test check H: no cost number is ever produced by this module.
# ---------------------------------------------------------------------------


class TestNoCostNumberEmitted:
    def test_cost_gap_never_carries_a_numeric_value_field(self, tmp_path: Path):
        key_file = _key_file(tmp_path)
        table_path = _table_file(tmp_path)
        digest_path = _matching_digest_file(tmp_path, table_path)

        result = load_rate_table(
            table_path=table_path, digest_path=digest_path, key_file=key_file
        )

        assert not hasattr(result.cost_gap, "value")
        serialized = result.cost_gap.to_dict()
        assert "value" not in serialized

    def test_digest_helper_is_deterministic_and_keyed(self, tmp_path: Path):
        table_path = _table_file(tmp_path)
        digest_a = compute_rate_table_digest(table_path.read_bytes(), VERIFIER_KEY)
        digest_b = compute_rate_table_digest(table_path.read_bytes(), VERIFIER_KEY)
        digest_wrong_key = compute_rate_table_digest(table_path.read_bytes(), b"other-key")
        assert digest_a == digest_b
        assert digest_a != digest_wrong_key
