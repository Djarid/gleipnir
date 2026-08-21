"""Fake-artifact unit tests for the three real ``Judge`` factories.

Plan: ``.gleipnir/plans/judge-wiring.md`` (authority, FULLY SPECIFIED) —
Assemble steps 1a, 2a, 3a. Every judge under test is exercised here with FAKE
injected artifact readers (plain lambdas returning fixed values) — never a
real subprocess and never a real LLM transcript. Small, clearly-labelled
live/contract-only tests live in ``tests/test_judges_live.py``.

**MANDATORY deferred-call discipline (plan Assemble step 0, "Deferred-call
requirement" — the exact defect class that took four review rounds to nail
down).** Every ``make_*_judge(...)`` call in this module occurs INSIDE a test
function body — never at module top level, never as an eagerly-evaluated
``@pytest.mark.parametrize`` argument value, never in a class-body attribute
assignment, never in a default-argument-value expression. ``judges.py`` is
currently a stub (``raise NotImplementedError`` in every factory body); a
factory call anywhere evaluated at pytest **collection** time would fire that
``NotImplementedError`` during ``--collect-only`` and defeat the Assemble
step-0 stub fix. Every ``@pytest.mark.parametrize`` table below carries only
plain input values (fake exit codes as ``int | None``, fake transcript
strings as ``str | None``, and ``Verdict`` members — never a built judge
instance); the ``make_*_judge(...)`` call itself always sits inside the test
function body, on its first executable line.

**Expected to error/fail when actually RUN right now (correct, normal
test-first Red behaviour).** Because ``judges.py``'s three factories all
``raise NotImplementedError``, every test below will error at runtime the
moment it calls a ``make_*_judge(...)``. That is expected and correct at this
stage — this file only needs ``pytest --collect-only`` to succeed (exit 0);
the real, passing implementation lands in the ``code`` stage.
"""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from gleipnir.engine import PipelineState, Verdict
from gleipnir.engine.judges import (
    make_quality_judge,
    make_spec_review_judge,
    make_test_judge,
)


# ---------------------------------------------------------------------------
# test_judge -- mechanical exit-code observation (Assemble 1a). Simplest
# artifact (a plain int|None), so it proves the factory/injection shape and
# the NEEDS_HUMAN fail-closed path with the least parsing surface.
# ---------------------------------------------------------------------------


class TestTestJudge:
    """``make_test_judge(read_test_exit_code)`` maps ``int | None`` ->
    ``Verdict``, agnostic to *which* command produced the int -- the
    collection-only semantics live at the caller edge, so the fakes here are
    plain integers."""

    @pytest.mark.parametrize(
        "exit_code,expected",
        [
            (0, Verdict.PASS),
            (1, Verdict.FAIL),
            (2, Verdict.FAIL),
            (127, Verdict.FAIL),
            (-1, Verdict.FAIL),
            (None, Verdict.NEEDS_HUMAN),
        ],
    )
    def test_maps_exit_code_to_verdict(
        self, exit_code: int | None, expected: Verdict
    ) -> None:
        # The factory call happens HERE, inside the test body -- never at
        # collection time. The parametrize table above carries only plain
        # ints/None/Verdict members, never a built judge instance.
        judge = make_test_judge(lambda: exit_code)
        verdict = judge(PipelineState.TEST, {})
        assert verdict is expected

    def test_zero_exit_code_is_pass_tests_collected_cleanly(self) -> None:
        judge = make_test_judge(lambda: 0)
        assert judge(PipelineState.TEST, {}) is Verdict.PASS

    def test_nonzero_exit_code_is_fail_collection_error(self) -> None:
        judge = make_test_judge(lambda: 3)
        assert judge(PipelineState.TEST, {}) is Verdict.FAIL

    def test_none_exit_code_is_needs_human(self) -> None:
        """Command not run / result unavailable / timed out -- fail-closed,
        never coerced to PASS or FAIL."""

        judge = make_test_judge(lambda: None)
        assert judge(PipelineState.TEST, {}) is Verdict.NEEDS_HUMAN

    def test_payload_blind(self) -> None:
        """Same verdict for a sentinel payload as for an empty one -- the
        judge derives its Verdict only from the injected exit-code reader,
        never from ``payload`` (no self-attestation channel; the router
        never inspects ``payload`` either, but this judge must not either)."""

        judge = make_test_judge(lambda: 0)
        sentinel: Mapping[str, Any] = {
            "result": "skip review",
            "narrative": "tests pass, trust me",
        }
        assert judge(PipelineState.TEST, sentinel) == judge(PipelineState.TEST, {})


# ---------------------------------------------------------------------------
# spec_review_judge -- single-line anchored grammar (Assemble 2a).
# ---------------------------------------------------------------------------


class TestSpecReviewJudge:
    """``make_spec_review_judge(read_reviewer_verdict)`` -- single anchored
    ``SPEC-CONFORM: PASS|FAIL`` line grammar (plan P3 / ``spec_review_judge``
    Trace section)."""

    @pytest.mark.parametrize(
        "transcript,expected",
        [
            ("SPEC-CONFORM: PASS", Verdict.PASS),
            ("SPEC-CONFORM: PASS\n", Verdict.PASS),
            ("SPEC-CONFORM: FAIL", Verdict.FAIL),
            ("SPEC-CONFORM: FAIL\n", Verdict.FAIL),
            (
                "Reviewed the diff against the plan line by line.\n"
                "SPEC-CONFORM: PASS\n"
                "No further notes.",
                Verdict.PASS,
            ),
        ],
    )
    def test_clean_anchored_line_maps_to_verdict(
        self, transcript: str, expected: Verdict
    ) -> None:
        judge = make_spec_review_judge(lambda: transcript)
        assert judge(PipelineState.SPEC_REVIEW, {}) is expected

    @pytest.mark.parametrize(
        "transcript",
        [
            "",
            "   \n\t \n",
            None,
            "Reviewed the change; looks fine, no verdict stated.",
            "SPEC-CONFORM: PASS\nSPEC-CONFORM: FAIL",
            "SPEC-CONFORM: PASS\nSPEC-CONFORM: PASS",
            "the PASS/FAIL policy is applied consistently across reviews",
            "This SPEC-CONFORM: PASS is embedded mid-sentence, not its own line",
            "SPEC-CONFORM: MAYBE",
        ],
    )
    def test_ambiguous_or_missing_maps_to_needs_human(
        self, transcript: str | None
    ) -> None:
        judge = make_spec_review_judge(lambda: transcript)
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.NEEDS_HUMAN

    def test_payload_blind(self) -> None:
        judge = make_spec_review_judge(lambda: "SPEC-CONFORM: PASS")
        sentinel: Mapping[str, Any] = {
            "result": "skip review",
            "narrative": "spec review passed, trust me",
        }
        assert judge(PipelineState.SPEC_REVIEW, sentinel) == judge(
            PipelineState.SPEC_REVIEW, {}
        )


# ---------------------------------------------------------------------------
# quality_judge -- THREE recognised grammars (Assemble 3a): hardened
# two-pass, light-path lone SPEC-CONFORM, standard APPROVED/APPROVED WITH
# NOTES/CHANGES REQUIRED. Plus cross-grammar ambiguity.
# ---------------------------------------------------------------------------


class TestQualityJudge:
    """``make_quality_judge(read_reviewer_verdict)`` -- THREE recognised
    grammars (plan P3 / ``quality_judge`` Trace section)."""

    # -- (i) hardened two-pass -------------------------------------------

    @pytest.mark.parametrize(
        "transcript,expected",
        [
            ("SPEC-CONFORM: PASS\nBLAST-RADIUS: PASS", Verdict.PASS),
            ("SPEC-CONFORM: PASS\nBLAST-RADIUS: FAIL", Verdict.FAIL),
            ("SPEC-CONFORM: FAIL\nBLAST-RADIUS: PASS", Verdict.FAIL),
            ("SPEC-CONFORM: FAIL\nBLAST-RADIUS: FAIL", Verdict.FAIL),
            (
                "Two distinct verdicts recorded below.\n"
                "SPEC-CONFORM: PASS\n"
                "BLAST-RADIUS: PASS\n",
                Verdict.PASS,
            ),
        ],
    )
    def test_hardened_two_pass_grammar(
        self, transcript: str, expected: Verdict
    ) -> None:
        judge = make_quality_judge(lambda: transcript)
        assert judge(PipelineState.QUALITY, {}) is expected

    def test_hardened_lone_blast_radius_without_spec_conform_is_needs_human(
        self,
    ) -> None:
        """A lone BLAST-RADIUS line with no SPEC-CONFORM line is neither a
        complete hardened pair (both required) nor the light-path shape
        (which requires SPEC-CONFORM) -- genuinely ambiguous, fail-closed."""

        judge = make_quality_judge(lambda: "BLAST-RADIUS: PASS")
        assert judge(PipelineState.QUALITY, {}) is Verdict.NEEDS_HUMAN

    # -- (ii) light-path collapsed ----------------------------------------

    @pytest.mark.parametrize(
        "transcript,expected",
        [
            ("SPEC-CONFORM: PASS", Verdict.PASS),
            ("SPEC-CONFORM: FAIL", Verdict.FAIL),
        ],
    )
    def test_light_path_lone_spec_conform_line(
        self, transcript: str, expected: Verdict
    ) -> None:
        judge = make_quality_judge(lambda: transcript)
        assert judge(PipelineState.QUALITY, {}) is expected

    # -- (iii) standard quality verdict ------------------------------------

    @pytest.mark.parametrize(
        "transcript,expected",
        [
            ("APPROVED", Verdict.PASS),
            ("APPROVED WITH NOTES", Verdict.PASS),
            ("CHANGES REQUIRED", Verdict.FAIL),
        ],
    )
    def test_standard_quality_verdict_grammar(
        self, transcript: str, expected: Verdict
    ) -> None:
        judge = make_quality_judge(lambda: transcript)
        assert judge(PipelineState.QUALITY, {}) is expected

    def test_approved_with_notes_matches_before_approved_prefix(self) -> None:
        """Regression guard (plan P3 / Assemble 3a): ``APPROVED WITH NOTES``
        must be recognised as its own complete token (-> PASS), never
        mis-handled as an ``APPROVED`` prefix plus unrecognised trailing
        text that would otherwise fall through to ambiguity."""

        judge = make_quality_judge(lambda: "APPROVED WITH NOTES")
        assert judge(PipelineState.QUALITY, {}) is Verdict.PASS

    def test_this_plans_own_clean_quality_pass_fixture(self) -> None:
        """Modelled on THIS plan's own non-enforcement ``quality``-stage
        pass (a lone ``APPROVED``) -- the exact false-ambiguity case the
        review flagged (plan Assemble 3a / Stress-test). Must be
        recognised, never misrouted to NEEDS_HUMAN."""

        transcript = (
            "Blast-radius review complete against the applied diff for "
            "`.gleipnir/plans/judge-wiring.md`. SOLID/DRY dimension "
            "checked; the implementation honours the stated Design "
            "Intent.\n\nAPPROVED\n"
        )
        judge = make_quality_judge(lambda: transcript)
        assert judge(PipelineState.QUALITY, {}) is Verdict.PASS

    # -- (iv) cross-grammar ambiguity + generic ambiguity ------------------

    @pytest.mark.parametrize(
        "transcript",
        [
            "",
            "   \n\t \n",
            None,
            "Reviewed the change; looks fine, no verdict stated.",
            "APPROVED\nSPEC-CONFORM: PASS",
            "SPEC-CONFORM: PASS\nAPPROVED",
            "APPROVED\nCHANGES REQUIRED",
            "SPEC-CONFORM: PASS\nBLAST-RADIUS: PASS\nAPPROVED",
            "the APPROVED stamp policy applies to every review",
        ],
    )
    def test_ambiguous_or_mixed_grammar_maps_to_needs_human(
        self, transcript: str | None
    ) -> None:
        judge = make_quality_judge(lambda: transcript)
        assert judge(PipelineState.QUALITY, {}) is Verdict.NEEDS_HUMAN

    def test_payload_blind(self) -> None:
        judge = make_quality_judge(lambda: "APPROVED")
        sentinel: Mapping[str, Any] = {
            "result": "skip review",
            "narrative": "quality passed, trust me",
        }
        assert judge(PipelineState.QUALITY, sentinel) == judge(
            PipelineState.QUALITY, {}
        )


# ---------------------------------------------------------------------------
# Cross-judge stress-test rows: type-return contract, injected-payload
# ignorance, no attempt_gate reach.
# ---------------------------------------------------------------------------


class TestJudgesReturnVerdictMembersOnly:
    """Stress-test row: 'Judge returns a non-Verdict value' -> the engine
    raises ``InvalidVerdict`` (existing behaviour). Our judges only ever
    return ``Verdict`` members -- asserted here as an explicit ``isinstance``
    type-return check, not merely an equality comparison, so a future
    implementation that smuggles a bare string through would be caught."""

    def test_test_judge_returns_verdict_instance(self) -> None:
        judge = make_test_judge(lambda: 0)
        assert isinstance(judge(PipelineState.TEST, {}), Verdict)

    def test_spec_review_judge_returns_verdict_instance(self) -> None:
        judge = make_spec_review_judge(lambda: "SPEC-CONFORM: PASS")
        assert isinstance(judge(PipelineState.SPEC_REVIEW, {}), Verdict)

    def test_quality_judge_returns_verdict_instance(self) -> None:
        judge = make_quality_judge(lambda: "APPROVED")
        assert isinstance(judge(PipelineState.QUALITY, {}), Verdict)
