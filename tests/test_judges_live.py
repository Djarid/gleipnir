"""Small, clearly-labelled live/contract tests for the three real ``Judge``
factories.

Plan: ``.gleipnir/plans/judge-wiring.md`` (authority, FULLY SPECIFIED) —
Assemble step 4. These tests assert ONLY the *contract*: a real, well-formed
verdict transcript (or a fixture-captured mechanical exit code) routes to the
correct ``Verdict``, and malformed/missing input routes to
``Verdict.NEEDS_HUMAN``. They NEVER assert on specific LLM prose content.

**``test_judge`` is pinned to FIXTURE-ONLY inputs (plan fix, Assemble step
4).** This file does NOT invoke
``bin/gleipnir-sandbox test -- --collect-only`` -- the live tests may
themselves run *inside* the S-2 sandbox container (``--network=none``, no
nested-container access), where spawning the sandbox command is likely
infeasible. The contract under test is the ``int | None -> Verdict``
mapping, fully exercised by a fixture-captured/constructed integer. Real
end-to-end invocation of the collection command is the harness/Seam-7
caller's job, out of scope here.

**Seams named, NOT automated here (never asserted green; mirrors
``tests/test_armed_run_dogfood.py`` L10-20 discipline):**

  * **Seam 7 -- the live opencode advance hook.** Not exercised: no real
    ``tool.execute.after`` handler runs any judge built in this file.
  * **Seam 8 -- real CI attestation into ``attempt_gate`` (G-3.2).** Not
    exercised: these tests never source a genuine CI ``Attestation`` and
    never call ``attempt_gate``; ``GIT``/``GATE`` are never reached.

**MANDATORY deferred-call discipline (same rule as ``tests/test_judges.py``).**
Every ``make_*_judge(...)`` call occurs INSIDE a test/fixture body, never at
module scope, in a ``parametrize`` argument list, a class-body assignment, or
a default-argument-value expression.

**Fixture-asset loading follows the same rule (plan Finding #6, lower
severity).** The fixture-captured transcript/exit-code assets below are
constructed INSIDE their fixture function bodies, never as module-level
constants -- the same collection-time-safety reason: a missing/invalid asset
read at module scope would raise at collection time, not at test-run time.
"""

from __future__ import annotations

import pytest

from gleipnir.engine import PipelineState, Verdict
from gleipnir.engine.judges import make_quality_judge, make_spec_review_judge, make_test_judge


# ---------------------------------------------------------------------------
# Shared malformed-transcript fixture -- used by both reviewer-transcript
# judges' malformed-input contract checks.
# ---------------------------------------------------------------------------


@pytest.fixture
def real_malformed_transcript() -> str:
    """No anchored verdict line of any recognised grammar -- a malformed /
    incomplete review transcript. Built inside the fixture body, not at
    module top level (plan Finding #6)."""

    return "Reviewed the change. Looks fine overall, no verdict line stated."


# ---------------------------------------------------------------------------
# spec_review_judge -- contract-only, real-shaped transcripts.
# ---------------------------------------------------------------------------


class TestSpecReviewJudgeLive:
    """Contract-only: a real transcript's anchored verdict line routes to
    the correct ``Verdict``; never asserts on the transcript's prose."""

    @pytest.fixture
    def real_spec_review_pass_transcript(self) -> str:
        """A real-shaped spec-review verdict transcript (the form
        ``quality-reviewer`` actually emits), constructed inside the fixture
        body -- not a module-level constant."""

        return (
            "Spec-conformance review complete. Reviewed the plan against "
            "the implementation; every acceptance criterion is satisfied.\n"
            "\nSPEC-CONFORM: PASS\n"
        )

    @pytest.fixture
    def real_spec_review_fail_transcript(self) -> str:
        return (
            "Spec-conformance review complete. Two acceptance criteria are "
            "not met by the current diff.\n\nSPEC-CONFORM: FAIL\n"
        )

    def test_real_pass_transcript_routes_to_pass(
        self, real_spec_review_pass_transcript: str
    ) -> None:
        judge = make_spec_review_judge(lambda: real_spec_review_pass_transcript)
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.PASS

    def test_real_fail_transcript_routes_to_fail(
        self, real_spec_review_fail_transcript: str
    ) -> None:
        judge = make_spec_review_judge(lambda: real_spec_review_fail_transcript)
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.FAIL

    def test_malformed_transcript_routes_to_needs_human(
        self, real_malformed_transcript: str
    ) -> None:
        judge = make_spec_review_judge(lambda: real_malformed_transcript)
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.NEEDS_HUMAN

    def test_missing_transcript_routes_to_needs_human(self) -> None:
        judge = make_spec_review_judge(lambda: None)
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.NEEDS_HUMAN


# ---------------------------------------------------------------------------
# quality_judge -- contract-only, standard-quality grammar (this plan's own
# quality-pass shape: a lone APPROVED / a lone CHANGES REQUIRED).
# ---------------------------------------------------------------------------


class TestQualityJudgeLive:
    """Contract-only: a real quality-review transcript's verdict token
    routes to the correct ``Verdict``; never asserts on prose content."""

    @pytest.fixture
    def real_quality_approved_transcript(self) -> str:
        return (
            "Blast-radius review complete against the applied diff. SOLID/"
            "DRY dimension checked; no divergence from the stated Design "
            "Intent found.\n\nAPPROVED\n"
        )

    @pytest.fixture
    def real_quality_changes_required_transcript(self) -> str:
        return (
            "Blast-radius review found a divergence from the stated Design "
            "Intent that must be fixed before this can land.\n\n"
            "CHANGES REQUIRED\n"
        )

    def test_real_approved_transcript_routes_to_pass(
        self, real_quality_approved_transcript: str
    ) -> None:
        judge = make_quality_judge(lambda: real_quality_approved_transcript)
        assert judge(PipelineState.QUALITY, {}) is Verdict.PASS

    def test_real_changes_required_transcript_routes_to_fail(
        self, real_quality_changes_required_transcript: str
    ) -> None:
        judge = make_quality_judge(lambda: real_quality_changes_required_transcript)
        assert judge(PipelineState.QUALITY, {}) is Verdict.FAIL

    def test_malformed_transcript_routes_to_needs_human(
        self, real_malformed_transcript: str
    ) -> None:
        judge = make_quality_judge(lambda: real_malformed_transcript)
        assert judge(PipelineState.QUALITY, {}) is Verdict.NEEDS_HUMAN


# ---------------------------------------------------------------------------
# test_judge -- FIXTURE-ONLY exit code (never a live-invoked
# `bin/gleipnir-sandbox test -- --collect-only`; see module docstring).
# ---------------------------------------------------------------------------


class TestTestJudgeLive:
    """Contract-only, fixture-captured mechanical exit codes standing in for
    a real ``bin/gleipnir-sandbox test -- --collect-only`` run -- never a
    live-invoked nested subprocess (module docstring rationale)."""

    @pytest.fixture
    def fixture_captured_clean_collection_exit_code(self) -> int:
        """Stands in for a captured exit code from a clean collection run
        (0). Built inside the fixture body -- never a module-level
        constant."""

        return 0

    @pytest.fixture
    def fixture_captured_collection_error_exit_code(self) -> int:
        """Stands in for a captured non-zero exit code from a collection
        failure (e.g. an unimportable test module)."""

        return 2

    def test_fixture_zero_exit_code_routes_to_pass(
        self, fixture_captured_clean_collection_exit_code: int
    ) -> None:
        judge = make_test_judge(lambda: fixture_captured_clean_collection_exit_code)
        assert judge(PipelineState.TEST, {}) is Verdict.PASS

    def test_fixture_nonzero_exit_code_routes_to_fail(
        self, fixture_captured_collection_error_exit_code: int
    ) -> None:
        judge = make_test_judge(lambda: fixture_captured_collection_error_exit_code)
        assert judge(PipelineState.TEST, {}) is Verdict.FAIL

    def test_missing_exit_code_routes_to_needs_human(self) -> None:
        """Command not run / result unavailable / timed out -- fail-closed."""

        judge = make_test_judge(lambda: None)
        assert judge(PipelineState.TEST, {}) is Verdict.NEEDS_HUMAN
