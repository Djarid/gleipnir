"""Tests for the G-4d ledger honesty types (`src/gleipnir/ledger/metric.py`).

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, D3 + Assemble step 1 +
Stress-test checks C/D/E/F. Written RED-first, before `metric.py` existed.

Covers:
  - `Measured` constructs freely (no calibration requirement); `denominator`
    is always inspectable.
  - `Gap` is a DISTINCT type from `Measured` — never equals/serializes as a
    numeric `0` (check C).
  - `Estimated` RAISES `LedgerError` without a `CalibrationBand`; RAISES
    without a versioned `NotionalHumanRate` when `kind is
    EstimateKind.UPLIFT`; does NOT raise for a non-uplift kind with no rate
    (check D) — and the uplift precondition is proven to be gated by the
    TYPED `EstimateKind` discriminant, not a `name == "uplift"` string
    (AST/grep meta-test).
  - Serialization of each kind carries the `kind` discriminant, and a
    gap/estimated dict can never deserialize into a `Measured` (check F).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

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
from gleipnir.ledger import metric as metric_module

METRIC_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "ledger" / "metric.py"
)


# ---------------------------------------------------------------------------
# Measured — constructs freely, denominator always inspectable (check E).
# ---------------------------------------------------------------------------


class TestMeasured:
    def test_constructs_with_no_calibration_requirement(self):
        m = Measured(name="revert_count", value=3, denominator=1, provenance="bus")
        assert m.value == 3

    def test_denominator_is_inspectable(self):
        m = Measured(name="escalation_rate", value=0.5, denominator=2, provenance="bus")
        assert m.denominator == 2

    def test_is_frozen(self):
        m = Measured(name="x", value=1, denominator=1, provenance="bus")
        with pytest.raises(Exception):
            m.value = 2  # type: ignore[misc]

    def test_serializes_with_measured_discriminant(self):
        m = Measured(name="revert_count", value=3, denominator=1, provenance="bus")
        d = m.to_dict()
        assert d["kind"] == "measured"
        assert d["name"] == "revert_count"
        assert d["value"] == 3
        assert d["denominator"] == 1


# ---------------------------------------------------------------------------
# Gap — a DISTINCT type, never Measured(0) (check C).
# ---------------------------------------------------------------------------


class TestGapIsDistinctFromMeasuredZero:
    def test_gap_is_not_a_measured_instance(self):
        gap = Gap(name="cost", reason="no event kind yet")
        assert not isinstance(gap, Measured)

    def test_gap_never_equals_a_measured_zero(self):
        gap = Gap(name="cost", reason="no event kind yet")
        zero = Measured(name="cost", value=0, denominator=1, provenance="n/a")
        assert gap != zero

    def test_gap_has_no_numeric_value_field(self):
        gap = Gap(name="cost", reason="no event kind yet")
        assert not hasattr(gap, "value")

    def test_gap_serializes_with_gap_discriminant_not_zero(self):
        gap = Gap(name="cost", reason="no event kind yet")
        d = gap.to_dict()
        assert d["kind"] == "gap"
        assert "value" not in d
        assert d["reason"] == "no event kind yet"

    def test_gap_reason_is_non_empty(self):
        gap = Gap(name="cost", reason="no event kind yet")
        assert gap.reason


# ---------------------------------------------------------------------------
# Estimated — FAIL-CLOSED construction (check D).
# ---------------------------------------------------------------------------


class TestEstimatedFailClosed:
    def test_raises_without_calibration_band(self):
        with pytest.raises(LedgerError):
            Estimated(name="uplift_estimate", value=1.5, kind=EstimateKind.UPLIFT)

    def test_uplift_kind_raises_without_notional_human_rate(self):
        band = CalibrationBand(low=0.5, high=2.0, sample_n=10, updated_at="2026-01-01")
        with pytest.raises(LedgerError):
            Estimated(
                name="uplift_estimate",
                value=1.5,
                kind=EstimateKind.UPLIFT,
                calibration=band,
            )

    def test_uplift_kind_constructs_with_calibration_and_rate(self):
        band = CalibrationBand(low=0.5, high=2.0, sample_n=10, updated_at="2026-01-01")
        rate = NotionalHumanRate(rate=75.0, currency="USD", version="2026-01-rate-v1")
        est = Estimated(
            name="uplift_estimate",
            value=1.5,
            kind=EstimateKind.UPLIFT,
            calibration=band,
            notional_human_rate=rate,
        )
        assert est.value == 1.5

    def test_non_uplift_kind_does_not_require_notional_human_rate(self):
        """The rate requirement is gated by the TYPED discriminant, not by
        "any Estimated" -- a non-uplift kind constructs fine with no rate."""
        band = CalibrationBand(low=0.5, high=2.0, sample_n=10, updated_at="2026-01-01")
        est = Estimated(
            name="future_efficiency_projection",
            value=1.2,
            kind=EstimateKind.GENERIC,
            calibration=band,
        )
        assert est.notional_human_rate is None
        # Serialize the no-rate branch: it emits null, never a fabricated rate.
        d = est.to_dict()
        assert d["kind"] == "estimated"
        assert d["estimate_kind"] == "generic"
        assert d["notional_human_rate"] is None

    def test_serializes_with_estimated_discriminant_and_estimate_kind(self):
        band = CalibrationBand(low=0.5, high=2.0, sample_n=10, updated_at="2026-01-01")
        rate = NotionalHumanRate(rate=75.0, currency="USD", version="2026-01-rate-v1")
        est = Estimated(
            name="uplift_estimate",
            value=1.5,
            kind=EstimateKind.UPLIFT,
            calibration=band,
            notional_human_rate=rate,
        )
        d = est.to_dict()
        assert d["kind"] == "estimated"
        assert d["estimate_kind"] == "uplift"
        assert d["calibration"]["sample_n"] == 10
        assert d["notional_human_rate"]["version"] == "2026-01-rate-v1"


# ---------------------------------------------------------------------------
# Serialization round-trip (check F): gap/estimated can never deserialize
# into a Measured.
# ---------------------------------------------------------------------------


class TestSerializationRoundTrip:
    def test_measured_round_trips(self):
        m = Measured(name="revert_count", value=3, denominator=1, provenance="bus")
        reconstructed = metric_from_dict(m.to_dict())
        assert isinstance(reconstructed, Measured)
        assert reconstructed == m

    def test_gap_round_trips(self):
        gap = Gap(name="cost", reason="deferred until S-2")
        reconstructed = metric_from_dict(gap.to_dict())
        assert isinstance(reconstructed, Gap)
        assert reconstructed == gap

    def test_estimated_round_trips(self):
        band = CalibrationBand(low=0.5, high=2.0, sample_n=10, updated_at="2026-01-01")
        rate = NotionalHumanRate(rate=75.0, currency="USD", version="v1")
        est = Estimated(
            name="uplift_estimate",
            value=1.5,
            kind=EstimateKind.UPLIFT,
            calibration=band,
            notional_human_rate=rate,
        )
        reconstructed = metric_from_dict(est.to_dict())
        assert isinstance(reconstructed, Estimated)
        assert reconstructed == est

    def test_gap_dict_cannot_construct_a_measured(self):
        """A gap dict is structurally missing Measured's required fields
        (`denominator`, `provenance`) -- it can never be mistaken for one."""
        gap_dict = Gap(name="cost", reason="deferred").to_dict()
        payload = {k: v for k, v in gap_dict.items() if k != "kind"}
        with pytest.raises(TypeError):
            Measured(**payload)  # type: ignore[arg-type]

    def test_estimated_dict_cannot_construct_a_measured(self):
        band = CalibrationBand(low=0.5, high=2.0, sample_n=10, updated_at="2026-01-01")
        est_dict = Estimated(
            name="uplift_estimate", value=1.5, kind=EstimateKind.UPLIFT,
            calibration=band, notional_human_rate=NotionalHumanRate(75.0, "USD", "v1"),
        ).to_dict()
        payload = {k: v for k, v in est_dict.items() if k != "kind"}
        with pytest.raises(TypeError):
            Measured(**payload)  # type: ignore[arg-type]

    def test_unknown_discriminant_raises(self):
        with pytest.raises(LedgerError):
            metric_from_dict({"kind": "not-a-real-kind"})


# ---------------------------------------------------------------------------
# AST/grep meta-test: the uplift precondition is gated by the TYPED
# EstimateKind discriminant, never a `name == "uplift"` string branch.
# ---------------------------------------------------------------------------


class TestUpliftPreconditionIsNotStringly:
    def test_source_contains_no_uplift_string_equality_branch(self):
        source = METRIC_SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            literal_uplift_compared = any(
                isinstance(operand, ast.Constant) and operand.value == "uplift"
                for operand in operands
            )
            if literal_uplift_compared:
                pytest.fail(
                    "found a string-literal 'uplift' comparison in metric.py "
                    "-- the uplift precondition must be gated by the TYPED "
                    "EstimateKind discriminant (`is EstimateKind.UPLIFT`), "
                    "never a name/field string equality check"
                )

    def test_source_has_no_name_equals_uplift_grep_hit(self):
        source = METRIC_SOURCE_PATH.read_text()
        assert 'name == "uplift"' not in source
        assert "name == 'uplift'" not in source

    def test_post_init_uses_identity_check_against_estimate_kind(self):
        post_init_source = inspect.getsource(Estimated.__post_init__)
        assert "EstimateKind.UPLIFT" in post_init_source
        assert "is EstimateKind.UPLIFT" in post_init_source or " is self.kind" in post_init_source
