"""Phase 1 tests: evidence readers + the Python advance entrypoint (all
three judges wired live). PHASE 3 (this delegation) extends this file with
the Seam-8 live-fetch + GATE GIT-branch wiring tests (see
`TestGitStateGateWiring` below).

Spec: `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble "Phase 1 — evidence
readers + the Python advance entrypoint (test judge first)" and "Phase 3 —
Seam 8 live fetch + GATE". Deliberately a SEPARATE module from
`tests/test_advance_hook.py`, which stays scoped to the Phase-0 D2 spike
proof (capture -> out-of-band deposit -> fresh-process re-read) and is left
untouched. This file covers the Phase-1 additions to
`src/gleipnir/preflight/advance.py`: `read_test_exit_code`,
`build_judge_for_state`, `advance_main`, and the CLI `main`, plus the
`advance` subcommand dispatch in `__main__.py` -- PLUS the Phase-3 additions:
`read_pipeline_run_identity` (the D5 sidecar reader) and `advance_main`'s
GIT-state branch (Seam 8: fetch a real `Attestation`, then
`Driver.attempt_gate`).

Stress-test criteria covered here (plan § Stress-test):
  1. Armed advance, test transition (PASS/FAIL both directions).
  2. Armed advance, spec-review & quality transitions (present -> routes per
     grammar; absent/ambiguous -> NEEDS_HUMAN/HUMAN_QUESTION).
  5. GATE only on GREEN+match (`TestGitStateGateWiring`).
  6. pipeline_id<->SHA correlation (`TestGitStateGateWiring`, the crafted
     mismatch case).
  9. Engine purity preserved (no bus/urllib/subprocess import added to
     `engine/__init__.py`; `driver.py`/`judges.py`/`engine/__init__.py`
     byte-unchanged -- golden-hash regression check, not narrative).
  10. stdlib-only (advance.py's new imports; `__main__.py`'s new import is a
      bare intra-package relative import, already exempted by
      `tests/test_preflight_stdlib_only.py`'s AST scanner).
  12. Bridge byte-stability (the golden-SHA256 test below is unconditional
      and unchanged by Phase 3 -- this delegation makes zero edits to the
      three protected engine files).

**Never a real nested `bin/gleipnir-sandbox test` invocation.** Mirrors
`tests/test_judges_live.py`'s module-docstring discipline: these tests run
themselves *inside* the S-2 sandbox container, where spawning a NESTED
sandbox invocation is likely infeasible. Every `read_test_exit_code`/
`build_judge_for_state`/`advance_main` call in this file that exercises the
TEST-state path injects a fixture `argv` (a tiny `python -c ...` one-liner
setting its own exit code), never the real sandbox binary.

**Never a real network call.** Every GIT-state test in
`TestGitStateGateWiring` injects `fetch_attestation_fn` (a plain Python
callable standing in for the real `fetch_attestation.fetch_attestation`) --
none of them touch `urllib`. The Seam-8 fetch function's own network-boundary
tests live in `tests/test_fetch_attestation.py`.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import sys
from pathlib import Path

import pytest

from gleipnir import engine as engine_pkg
from gleipnir.engine import (
    Attestation,
    AttestationNotGreen,
    AttestationRequired,
    AttestationStatus,
    PipelineState,
    StepResult,
    Verdict,
)
from gleipnir.engine.bridge import StateMarker
from gleipnir.engine.driver import BridgeInvalid, Driver
from gleipnir.engine.judges import make_test_judge
from gleipnir.preflight import __main__ as preflight_main
from gleipnir.preflight import advance
from gleipnir.verify.marker import KeyUnavailable

VERIFIER_KEY = b"verifier-only-secret-key-not-on-agent-surface"
PIPELINE_ID = "pl-advance-entrypoint-test-1"


# ---------------------------------------------------------------------------
# Shared fixtures (mirrors tests/test_driver.py's key_file/bridge_path shape)
# ---------------------------------------------------------------------------


@pytest.fixture
def key_file(tmp_path: Path) -> Path:
    kf = tmp_path / "key"
    kf.write_bytes(VERIFIER_KEY)
    return kf


@pytest.fixture
def bridge_path(tmp_path: Path) -> Path:
    return tmp_path / "var" / "run" / "pipeline-state.json"


def _read_marker(bridge_path: Path) -> StateMarker:
    return StateMarker.from_json(bridge_path.read_text())


def _drive_to(driver: Driver, target: PipelineState) -> None:
    """Advance `driver` to `target` via the trivial always-PASS judge
    (mirrors `tests/test_driver_emits_needs_human_and_gate.py::drive_to`,
    but reuses `Driver.advance_on_clean_completion` since no bus/verdict
    control is needed for these setup hops)."""

    while driver.state is not target:
        driver.advance_on_clean_completion()


def _fixture_argv(exit_code: int) -> list[str]:
    """A tiny real OS subprocess standing in for
    `bin/gleipnir-sandbox test -- --collect-only`, so `read_test_exit_code`
    exercises a genuine `subprocess.run` without spawning the (likely
    infeasible, nested-container) real sandbox binary."""

    return [sys.executable, "-c", f"import sys; sys.exit({exit_code})"]


def _write_sidecar(run_root: Path, pipeline_id: str, head_sha: str) -> None:
    """Write a well-formed D5 sidecar (`pipeline-run.json`) under `run_root`
    -- the plain-file, agent-read-only run-manifest this delegation's
    `read_pipeline_run_identity` reads. Mirrors the shape the (out-of-scope
    here) git broker's `commit_changes` side effect would write."""

    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / advance.PIPELINE_RUN_FILENAME).write_text(
        json.dumps({"pipeline_id": pipeline_id, "head_sha": head_sha}),
        encoding="utf-8",
    )


def _fake_fetcher(status: AttestationStatus):
    """A plain Python callable standing in for the real
    `fetch_attestation.fetch_attestation` -- echoes `pipeline_id` back
    verbatim into the constructed `Attestation`, exactly like the real
    function does (it never asserts a match itself; `Engine.attempt_gate`
    is what enforces the pipeline_id<->engine correlation, Stress-test #6).
    Never touches `urllib`/the network."""

    def _fetch(pipeline_id: str, head_sha: str) -> Attestation:
        return Attestation(pipeline_id=pipeline_id, status=status)

    return _fetch


# ---------------------------------------------------------------------------
# read_test_exit_code -- the mechanical TEST-judge evidence reader
# ---------------------------------------------------------------------------


class TestReadTestExitCode:
    def test_injected_argv_zero_exit_returns_zero(self):
        assert advance.read_test_exit_code(_fixture_argv(0)) == 0

    def test_injected_argv_nonzero_exit_returns_that_code(self):
        assert advance.read_test_exit_code(_fixture_argv(7)) == 7

    def test_missing_binary_returns_none_not_raise(self):
        assert (
            advance.read_test_exit_code(["/no/such/gleipnir-sandbox-binary"])
            is None
        )

    def test_timeout_returns_none_not_raise(self):
        sleeper = [sys.executable, "-c", "import time; time.sleep(5)"]
        assert advance.read_test_exit_code(sleeper, timeout=0.05) is None

    def test_default_argv_shape_is_the_real_sandbox_collect_only_command(self):
        """Pure path construction -- no I/O, no subprocess spawned -- so
        this is safe to assert without exercising the (possibly-nested-
        infeasible) real binary."""

        argv = advance._default_sandbox_test_argv()
        assert argv[-3:] == ["test", "--", "--collect-only"]
        assert argv[0].endswith("bin/gleipnir-sandbox")


# ---------------------------------------------------------------------------
# build_judge_for_state -- per-state dispatch to the real judge factories
# ---------------------------------------------------------------------------


class TestBuildJudgeForState:
    def test_test_state_pass_exit_code_routes_to_pass(self):
        judge = advance.build_judge_for_state(
            PipelineState.TEST,
            pipeline_id=PIPELINE_ID,
            test_argv=_fixture_argv(0),
        )
        assert judge(PipelineState.TEST, {}) is Verdict.PASS

    def test_test_state_nonzero_exit_code_routes_to_fail(self):
        judge = advance.build_judge_for_state(
            PipelineState.TEST,
            pipeline_id=PIPELINE_ID,
            test_argv=_fixture_argv(1),
        )
        assert judge(PipelineState.TEST, {}) is Verdict.FAIL

    def test_test_state_uses_the_real_make_test_judge_factory(self):
        """The returned callable IS what `make_test_judge` builds -- not a
        parallel re-implementation (D1, call-site-only)."""

        judge = advance.build_judge_for_state(
            PipelineState.TEST, pipeline_id=PIPELINE_ID, test_argv=_fixture_argv(0)
        )
        reference = make_test_judge(lambda: 0)
        assert judge(PipelineState.TEST, {}) == reference(PipelineState.TEST, {})

    def test_spec_review_state_pass_transcript_routes_to_pass(self, tmp_path: Path):
        advance.capture_and_deposit_reviewer_transcript(
            "SPEC-CONFORM: PASS\n",
            PipelineState.SPEC_REVIEW.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )
        judge = advance.build_judge_for_state(
            PipelineState.SPEC_REVIEW, pipeline_id=PIPELINE_ID, log_root=tmp_path
        )
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.PASS

    def test_spec_review_state_absent_transcript_routes_to_needs_human(
        self, tmp_path: Path
    ):
        judge = advance.build_judge_for_state(
            PipelineState.SPEC_REVIEW, pipeline_id=PIPELINE_ID, log_root=tmp_path
        )
        assert judge(PipelineState.SPEC_REVIEW, {}) is Verdict.NEEDS_HUMAN

    def test_quality_state_approved_transcript_routes_to_pass(self, tmp_path: Path):
        advance.capture_and_deposit_reviewer_transcript(
            "APPROVED\n",
            PipelineState.QUALITY.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )
        judge = advance.build_judge_for_state(
            PipelineState.QUALITY, pipeline_id=PIPELINE_ID, log_root=tmp_path
        )
        assert judge(PipelineState.QUALITY, {}) is Verdict.PASS

    def test_quality_state_changes_required_transcript_routes_to_fail(
        self, tmp_path: Path
    ):
        advance.capture_and_deposit_reviewer_transcript(
            "CHANGES REQUIRED\n",
            PipelineState.QUALITY.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )
        judge = advance.build_judge_for_state(
            PipelineState.QUALITY, pipeline_id=PIPELINE_ID, log_root=tmp_path
        )
        assert judge(PipelineState.QUALITY, {}) is Verdict.FAIL

    def test_quality_state_ambiguous_transcript_routes_to_needs_human(
        self, tmp_path: Path
    ):
        advance.capture_and_deposit_reviewer_transcript(
            "no anchored verdict line here at all\n",
            PipelineState.QUALITY.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )
        judge = advance.build_judge_for_state(
            PipelineState.QUALITY, pipeline_id=PIPELINE_ID, log_root=tmp_path
        )
        assert judge(PipelineState.QUALITY, {}) is Verdict.NEEDS_HUMAN

    @pytest.mark.parametrize(
        "state",
        [
            PipelineState.BRAINSTORM,
            PipelineState.PLAN,
            PipelineState.CODE,
            PipelineState.GIT,
            PipelineState.GATE,
            PipelineState.HUMAN_QUESTION,
            PipelineState.ESCALATED,
        ],
    )
    def test_every_other_state_raises_unjudged_state(self, state: PipelineState):
        """Phase 1 wires exactly SPEC_REVIEW/QUALITY/TEST. GIT (Phase 3's
        fetch_attestation/attempt_gate path) is deliberately included in
        this refusal set -- Phase 3 is out of THIS delegation's scope."""

        with pytest.raises(advance.UnjudgedState) as excinfo:
            advance.build_judge_for_state(state, pipeline_id=PIPELINE_ID)
        assert excinfo.value.state is state


# ---------------------------------------------------------------------------
# advance_main -- the end-to-end Python advance entrypoint
# ---------------------------------------------------------------------------


class TestAdvanceMainTestTransition:
    def test_pass_exit_code_advances_test_to_code(self, bridge_path, key_file):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.TEST)

        result = advance.advance_main(
            PIPELINE_ID,
            bridge_path,
            key_file=key_file,
            test_argv=_fixture_argv(0),
        )

        assert isinstance(result, StepResult)
        assert result.state is PipelineState.CODE
        assert _read_marker(bridge_path).pipeline_state == PipelineState.CODE.value

    def test_nonzero_exit_code_reverts_test_to_spec_review(self, bridge_path, key_file):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.TEST)

        result = advance.advance_main(
            PIPELINE_ID,
            bridge_path,
            key_file=key_file,
            test_argv=_fixture_argv(1),
        )

        assert result.state is PipelineState.SPEC_REVIEW
        assert (
            _read_marker(bridge_path).pipeline_state
            == PipelineState.SPEC_REVIEW.value
        )


class TestAdvanceMainSpecReviewAndQualityTransitions:
    def test_present_pass_transcript_advances_spec_review_to_test(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)

        advance.capture_and_deposit_reviewer_transcript(
            "SPEC-CONFORM: PASS\n",
            PipelineState.SPEC_REVIEW.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )

        result = advance.advance_main(
            PIPELINE_ID, bridge_path, key_file=key_file, log_root=tmp_path
        )

        assert result.state is PipelineState.TEST

    def test_absent_transcript_routes_spec_review_to_human_question(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)

        result = advance.advance_main(
            PIPELINE_ID, bridge_path, key_file=key_file, log_root=tmp_path
        )

        assert result.state is PipelineState.HUMAN_QUESTION

    def test_present_approved_transcript_advances_quality_to_git(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.QUALITY)

        advance.capture_and_deposit_reviewer_transcript(
            "APPROVED\n",
            PipelineState.QUALITY.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )

        result = advance.advance_main(
            PIPELINE_ID, bridge_path, key_file=key_file, log_root=tmp_path
        )

        assert result.state is PipelineState.GIT

    def test_ambiguous_transcript_routes_quality_to_human_question(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.QUALITY)

        advance.capture_and_deposit_reviewer_transcript(
            "SPEC-CONFORM: PASS\nBLAST-RADIUS: PASS\nAPPROVED\n",
            PipelineState.QUALITY.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )

        result = advance.advance_main(
            PIPELINE_ID, bridge_path, key_file=key_file, log_root=tmp_path
        )

        assert result.state is PipelineState.HUMAN_QUESTION


class TestAdvanceMainFailClosed:
    def test_unjudged_state_raises_and_does_not_touch_bridge(
        self, bridge_path, key_file
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.PLAN)
        before = bridge_path.read_bytes()

        with pytest.raises(advance.UnjudgedState):
            advance.advance_main(PIPELINE_ID, bridge_path, key_file=key_file)

        assert bridge_path.read_bytes() == before
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.PLAN

    def test_missing_key_raises_key_unavailable(self, bridge_path, key_file):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()

        with pytest.raises(KeyUnavailable):
            advance.advance_main(PIPELINE_ID, bridge_path, key_file=None)

    def test_corrupt_bridge_raises_bridge_invalid(self, bridge_path, key_file):
        bridge_path.parent.mkdir(parents=True, exist_ok=True)
        bridge_path.write_text("not json at all")

        with pytest.raises(BridgeInvalid):
            advance.advance_main(PIPELINE_ID, bridge_path, key_file=key_file)


# ---------------------------------------------------------------------------
# read_pipeline_run_identity -- the D5 sidecar reader (Phase 3)
# ---------------------------------------------------------------------------


class TestReadPipelineRunIdentity:
    def test_absent_file_returns_none(self, tmp_path: Path):
        assert advance.read_pipeline_run_identity(run_root=tmp_path) is None

    def test_well_formed_returns_pipeline_id_and_head_sha(self, tmp_path: Path):
        _write_sidecar(tmp_path, "pl-123", "deadbeef" * 5)
        assert advance.read_pipeline_run_identity(run_root=tmp_path) == (
            "pl-123",
            "deadbeef" * 5,
        )

    def test_malformed_json_returns_none(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / advance.PIPELINE_RUN_FILENAME).write_text("not json at all")
        assert advance.read_pipeline_run_identity(run_root=tmp_path) is None

    def test_non_dict_json_returns_none(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / advance.PIPELINE_RUN_FILENAME).write_text(
            json.dumps(["not", "a", "dict"])
        )
        assert advance.read_pipeline_run_identity(run_root=tmp_path) is None

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"pipeline_id": "pl-1"},
            {"head_sha": "abc123"},
            {"pipeline_id": "", "head_sha": "abc123"},
            {"pipeline_id": "pl-1", "head_sha": ""},
            {"pipeline_id": 5, "head_sha": "abc123"},
            {"pipeline_id": "pl-1", "head_sha": None},
        ],
    )
    def test_missing_or_malformed_fields_return_none(
        self, tmp_path: Path, payload: dict
    ):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / advance.PIPELINE_RUN_FILENAME).write_text(json.dumps(payload))
        assert advance.read_pipeline_run_identity(run_root=tmp_path) is None

    def test_pipeline_run_path_default_is_under_var_run(self):
        path = advance.pipeline_run_path()
        assert path.name == "pipeline-run.json"
        assert path.parent.name == "run"
        assert path.parent.parent.name == "var"
        assert path.parent.parent.parent.name == ".gleipnir"


# ---------------------------------------------------------------------------
# advance_main -- the Phase-3 GIT-state branch (Seam 8: fetch + attempt_gate)
# ---------------------------------------------------------------------------


class TestGitStateGateWiring:
    def test_missing_sidecar_raises_missing_run_identity_and_does_not_touch_bridge(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        before = bridge_path.read_bytes()

        with pytest.raises(advance.MissingRunIdentity):
            advance.advance_main(
                PIPELINE_ID,
                bridge_path,
                key_file=key_file,
                run_root=tmp_path / "no-such-run-root",
            )

        assert bridge_path.read_bytes() == before
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.GIT

    def test_malformed_sidecar_raises_missing_run_identity(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / advance.PIPELINE_RUN_FILENAME).write_text("not json")

        with pytest.raises(advance.MissingRunIdentity):
            advance.advance_main(
                PIPELINE_ID, bridge_path, key_file=key_file, run_root=tmp_path
            )

    def test_green_matching_attestation_advances_git_to_gate(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        _write_sidecar(tmp_path, PIPELINE_ID, "sha-abc123")

        result = advance.advance_main(
            PIPELINE_ID,
            bridge_path,
            key_file=key_file,
            run_root=tmp_path,
            fetch_attestation_fn=_fake_fetcher(AttestationStatus.GREEN),
        )

        assert result.state is PipelineState.GATE
        assert _read_marker(bridge_path).pipeline_state == PipelineState.GATE.value

    @pytest.mark.parametrize(
        "status",
        [AttestationStatus.RED, AttestationStatus.PENDING, AttestationStatus.ABSENT],
    )
    def test_non_green_attestation_refuses_and_stays_at_git(
        self, bridge_path, key_file, tmp_path, status: AttestationStatus
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        _write_sidecar(tmp_path, PIPELINE_ID, "sha-abc123")
        before = bridge_path.read_bytes()

        with pytest.raises(AttestationNotGreen):
            advance.advance_main(
                PIPELINE_ID,
                bridge_path,
                key_file=key_file,
                run_root=tmp_path,
                fetch_attestation_fn=_fake_fetcher(status),
            )

        assert bridge_path.read_bytes() == before
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.GIT

    def test_pipeline_id_mismatch_refuses_even_when_green(
        self, bridge_path, key_file, tmp_path
    ):
        """Stress-test #6: a GREEN run recorded for a DIFFERENT pipeline_id
        (the sidecar's own, stale or otherwise) must NOT gate THIS engine's
        run. The fake fetcher echoes the sidecar's pipeline_id into the
        Attestation exactly like the real `fetch_attestation` does; the
        correlation refusal comes from `Engine.attempt_gate` itself
        (engine/__init__.py L490-496, unchanged), not from any check added
        here."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        # The sidecar names a DIFFERENT pipeline_id than the one this
        # driver/bridge was resumed with.
        _write_sidecar(tmp_path, "pl-some-other-run", "sha-belongs-to-other-run")
        before = bridge_path.read_bytes()

        with pytest.raises(AttestationNotGreen):
            advance.advance_main(
                PIPELINE_ID,
                bridge_path,
                key_file=key_file,
                run_root=tmp_path,
                fetch_attestation_fn=_fake_fetcher(AttestationStatus.GREEN),
            )

        assert bridge_path.read_bytes() == before
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.GIT

    def test_head_sha_and_run_pipeline_id_are_passed_through_to_the_fetcher(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        _write_sidecar(tmp_path, PIPELINE_ID, "sha-xyz789")

        captured: list[tuple[str, str]] = []

        def _capturing_fetcher(pipeline_id: str, head_sha: str) -> Attestation:
            captured.append((pipeline_id, head_sha))
            return Attestation(pipeline_id=pipeline_id, status=AttestationStatus.GREEN)

        advance.advance_main(
            PIPELINE_ID,
            bridge_path,
            key_file=key_file,
            run_root=tmp_path,
            fetch_attestation_fn=_capturing_fetcher,
        )

        assert captured == [(PIPELINE_ID, "sha-xyz789")]

    def test_default_fetcher_is_the_real_fetch_attestation_module_function(
        self, bridge_path, key_file, tmp_path, monkeypatch
    ):
        """No `fetch_attestation_fn` override -> `advance_main` reaches the
        REAL `fetch_attestation.fetch_attestation` (D1/DRY: no parallel
        reimplementation). Monkeypatches that attribute on the module
        `advance.py` itself imports (`advance.fetch_attestation`), so this
        never touches the network."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.GIT)
        _write_sidecar(tmp_path, PIPELINE_ID, "sha-default-path")

        calls: list[tuple[str, str]] = []

        def _stub(pipeline_id: str, head_sha: str) -> Attestation:
            calls.append((pipeline_id, head_sha))
            return Attestation(pipeline_id=pipeline_id, status=AttestationStatus.GREEN)

        monkeypatch.setattr(advance.fetch_attestation, "fetch_attestation", _stub)

        result = advance.advance_main(
            PIPELINE_ID, bridge_path, key_file=key_file, run_root=tmp_path
        )

        assert result.state is PipelineState.GATE
        assert calls == [(PIPELINE_ID, "sha-default-path")]

    def test_other_states_still_unaffected_by_the_git_branch(
        self, bridge_path, key_file
    ):
        """Guard against the GIT branch accidentally short-circuiting every
        other state: SPEC_REVIEW must still dispatch through
        `build_judge_for_state` -- absent transcript -> NEEDS_HUMAN, exactly
        as Phase 1 built it, never reaching the GIT/sidecar/fetch code path
        at all."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)

        result = advance.advance_main(PIPELINE_ID, bridge_path, key_file=key_file)

        assert result.state is PipelineState.HUMAN_QUESTION


# ---------------------------------------------------------------------------
# main(argv) -- the CLI wrapper (never exercises the real TEST-state path,
# to avoid a nested `bin/gleipnir-sandbox` invocation from inside the
# sandbox test container -- see module docstring)
# ---------------------------------------------------------------------------


class TestCliMain:
    def test_success_exit_zero_and_reports_new_state(
        self, bridge_path, key_file, tmp_path, capsys
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)
        advance.capture_and_deposit_reviewer_transcript(
            "SPEC-CONFORM: PASS\n",
            PipelineState.SPEC_REVIEW.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
                "--log-root",
                str(tmp_path),
            ]
        )

        assert rc == 0
        err = capsys.readouterr().err
        assert "advanced to test" in err

    def test_unjudged_state_exit_nonzero(self, bridge_path, key_file, capsys):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()  # BRAINSTORM -- unjudged in Phase 1

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
            ]
        )

        assert rc == 1
        assert "refusing" in capsys.readouterr().err

    def test_bad_key_file_exit_nonzero(self, bridge_path, key_file, tmp_path, capsys):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(tmp_path / "no-such-key"),
            ]
        )

        assert rc == 1
        assert "refusing" in capsys.readouterr().err

    def test_escalated_suffix_is_reported(self, monkeypatch, bridge_path, key_file, capsys):
        """Unit-tests the CLI's presentation of `StepResult.escalated`
        without contriving a real revert-budget exhaustion through the
        engine -- `advance_main` is monkeypatched to return a
        pre-constructed escalated `StepResult`, isolating the string-
        formatting behaviour under test."""

        monkeypatch.setattr(
            advance,
            "advance_main",
            lambda *a, **k: StepResult(state=PipelineState.ESCALATED, escalated=True),
        )

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
            ]
        )

        assert rc == 0
        assert "(ESCALATED)" in capsys.readouterr().err

    def test_dispatched_via_preflight_main_advance_subcommand(
        self, bridge_path, key_file, tmp_path, capsys
    ):
        """The `advance` leading-token dispatch added to
        `src/gleipnir/preflight/__main__.py` (mirroring `bridge-status`/
        `bridge-reset`) reaches this same `advance.main`."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)
        advance.capture_and_deposit_reviewer_transcript(
            "SPEC-CONFORM: PASS\n",
            PipelineState.SPEC_REVIEW.value,
            PIPELINE_ID,
            log_root=tmp_path,
        )

        rc = preflight_main.main(
            [
                "advance",
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
                "--log-root",
                str(tmp_path),
            ]
        )

        assert rc == 0
        assert "advanced to test" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Completion-pass addition: the `--reviewer-transcript-stdin` CLI flag +
# `advance_main`'s `reviewer_transcript` param (closes quality-review
# Finding A on the PYTHON side -- the TS-side capture/forward is covered by
# `tests/test_advance_hook.mjs`). Genuinely end-to-end, not mocked: each test
# drives the SAME `read_reviewer_verdict`/`capture_and_deposit_reviewer_
# transcript` functions the real SPEC_REVIEW/QUALITY judges call, reading
# back from the SAME `log_root` the deposit was written to, within one test.
# ---------------------------------------------------------------------------


class TestReviewerTranscriptCliWiring:
    def test_stdin_flag_round_trips_through_deposit_and_is_read_back_by_the_judge(
        self, bridge_path, key_file, tmp_path, monkeypatch, capsys
    ):
        """End-to-end: CLI `--reviewer-transcript-stdin` -> `advance_main`
        deposits via `capture_and_deposit_reviewer_transcript` -> the REAL
        `make_spec_review_judge` (via `build_judge_for_state`, unmocked)
        reads it back via `read_reviewer_verdict` and advances on it -- all
        within this single test, proving the deposit genuinely exists by the
        time the judge runs (not merely that the two functions work in
        isolation)."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)

        transcript_text = "SPEC-CONFORM: PASS\n"
        monkeypatch.setattr(sys, "stdin", io.StringIO(transcript_text))

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
                "--log-root",
                str(tmp_path),
                "--reviewer-transcript-stdin",
            ]
        )

        assert rc == 0
        assert "advanced to test" in capsys.readouterr().err
        # The deposit landed at exactly the path the judge read from -- read
        # it back via the SAME function `build_judge_for_state` wires to the
        # judge, proving genuine end-to-end closure of Finding A.
        assert (
            advance.read_reviewer_verdict(
                PipelineState.SPEC_REVIEW.value, PIPELINE_ID, log_root=tmp_path
            )
            == transcript_text
        )
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.TEST

    def test_stdin_flag_quality_changes_required_reverts_via_the_real_deposit(
        self, bridge_path, key_file, tmp_path, monkeypatch, capsys
    ):
        """Same end-to-end shape as above, but for QUALITY + a FAIL-grammar
        transcript -- proves the wiring carries the judge's actual verdict
        through (a revert), not just a hardcoded PASS path."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.QUALITY)

        transcript_text = "CHANGES REQUIRED\n"
        monkeypatch.setattr(sys, "stdin", io.StringIO(transcript_text))

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
                "--log-root",
                str(tmp_path),
                "--reviewer-transcript-stdin",
            ]
        )

        assert rc == 0
        assert (
            advance.read_reviewer_verdict(
                PipelineState.QUALITY.value, PIPELINE_ID, log_root=tmp_path
            )
            == transcript_text
        )
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        # Verdict.FAIL at QUALITY reverts to CODE (engine TRANSITIONS table,
        # unchanged -- mirrors `test_quality_state_changes_required_
        # transcript_routes_to_fail`'s verdict, carried through the CLI/
        # stdin/deposit path this test exercises end-to-end).
        assert resumed.state is PipelineState.CODE

    def test_stdin_flag_for_a_non_transcript_state_refuses_before_any_deposit(
        self, bridge_path, key_file, tmp_path, monkeypatch, capsys
    ):
        """Fail-closed (ReviewerTranscriptMisuse): a bridge resumed at a
        state with no transcript-based judge (BRAINSTORM) must refuse BEFORE
        depositing anything -- asserted by confirming `read_reviewer_verdict`
        finds nothing afterward, not merely that the exit code is non-zero."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()  # BRAINSTORM

        monkeypatch.setattr(sys, "stdin", io.StringIO("irrelevant text\n"))

        rc = advance.main(
            [
                "--pipeline-id",
                PIPELINE_ID,
                "--bridge-path",
                str(bridge_path),
                "--key-file",
                str(key_file),
                "--log-root",
                str(tmp_path),
                "--reviewer-transcript-stdin",
            ]
        )

        assert rc == 1
        assert "reviewer-transcript capture/deposit failed" in capsys.readouterr().err
        assert (
            advance.read_reviewer_verdict(
                PipelineState.BRAINSTORM.value, PIPELINE_ID, log_root=tmp_path
            )
            is None
        )
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.BRAINSTORM

    def test_advance_main_reviewer_transcript_param_deposits_before_the_judge_reads_it(
        self, bridge_path, key_file, tmp_path
    ):
        """Direct `advance_main` call (bypassing the CLI/stdin layer
        entirely) -- proves the deposit->judge ordering holds at the
        function-call boundary too, using the REAL `driver.state` (never a
        caller-asserted one) to pick the deposit path."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.QUALITY)

        result = advance.advance_main(
            PIPELINE_ID,
            bridge_path,
            key_file=key_file,
            log_root=tmp_path,
            reviewer_transcript="APPROVED\n",
        )

        assert result.state is PipelineState.GIT
        assert (
            advance.read_reviewer_verdict(
                PipelineState.QUALITY.value, PIPELINE_ID, log_root=tmp_path
            )
            == "APPROVED\n"
        )

    def test_reviewer_transcript_misuse_for_non_transcript_state_raises_before_deposit(
        self, bridge_path, key_file, tmp_path
    ):
        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.TEST)

        with pytest.raises(advance.ReviewerTranscriptMisuse):
            advance.advance_main(
                PIPELINE_ID,
                bridge_path,
                key_file=key_file,
                log_root=tmp_path,
                reviewer_transcript="should never be accepted for TEST\n",
                test_argv=_fixture_argv(0),
            )

        assert (
            advance.read_reviewer_verdict(
                PipelineState.TEST.value, PIPELINE_ID, log_root=tmp_path
            )
            is None
        )
        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.TEST

    def test_reviewer_transcript_deposit_failure_raises_before_the_judge_runs(
        self, bridge_path, key_file, tmp_path, monkeypatch
    ):
        """Fail-closed on a genuine OSError during deposit (e.g. disk/
        permission failure): `ReviewerTranscriptDepositFailed`, and
        `Driver.advance`/the judge must never be reached."""

        driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file)
        driver.write_bridge()
        _drive_to(driver, PipelineState.SPEC_REVIEW)

        def _boom(*args, **kwargs):
            raise OSError("disk full (simulated)")

        monkeypatch.setattr(advance, "capture_and_deposit_reviewer_transcript", _boom)

        with pytest.raises(advance.ReviewerTranscriptDepositFailed):
            advance.advance_main(
                PIPELINE_ID,
                bridge_path,
                key_file=key_file,
                log_root=tmp_path,
                reviewer_transcript="SPEC-CONFORM: PASS\n",
            )

        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is PipelineState.SPEC_REVIEW


# ---------------------------------------------------------------------------
# Stress-test check 9: engine purity + byte-unchanged core files
# ---------------------------------------------------------------------------


def test_engine_package_imports_no_bus_urllib_or_subprocess():
    """Static check (not narrative): `engine/__init__.py` must gain no
    bus/urllib/subprocess import as part of this Phase-1 wiring -- the
    engine core stays pure; all new I/O lives in `advance.py` at the caller
    edge. Mirrors `tests/test_driver_emits_revert.py::
    test_engine_package_imports_no_bus_module`, extended to the two other
    I/O modules this plan's Design Intent names."""

    source = inspect.getsource(engine_pkg)
    tree = ast.parse(source)
    banned = ("bus", "urllib", "subprocess")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(b in alias.name for b in banned), alias.name
        if isinstance(node, ast.ImportFrom):
            if node.module:
                assert not any(b in node.module for b in banned), node.module


def _engine_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "engine"


# Golden SHA-256 hashes captured at Phase-1 authorship time (via
# `bin/gleipnir-sandbox test`, reading the mismatch from a first failing
# run -- these are NOT computed from anything this delegation edited; the
# delegation makes ZERO edits to these three files, call-site-only per D1).
# If a FUTURE, reviewed change legitimately touches one of these files,
# update its hash here deliberately -- never let it drift silently.
_EXPECTED_CORE_FILE_SHA256 = {
    "__init__.py": "d15dc20086e84122a8c9369bce1e4ac89362d27bfbe5e7c3f576a59ad0aafc7b",
    "driver.py": "792d4b213deed56cdd960e0408de5de1ac8e615abe26259e9729dc2a34a7773a",
    "judges.py": "5e77f85aeb82ad2f211118464a2bd463a65ad939969ab1d813a913ebaed5a9a1",
}


@pytest.mark.parametrize("relpath", sorted(_EXPECTED_CORE_FILE_SHA256))
def test_core_engine_files_byte_unchanged(relpath: str):
    path = _engine_dir() / relpath
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = _EXPECTED_CORE_FILE_SHA256[relpath]
    assert digest == expected, (
        f"engine/{relpath} content changed (sha256 {digest} != golden "
        f"{expected}) -- Phase 1 (.gleipnir/plans/seam7-seam8-wiring.md) is "
        "call-site-only (D1): driver.py/judges.py/engine/__init__.py must "
        "stay byte-unchanged by this delegation. If this is a DIFFERENT, "
        "reviewed change intentionally touching this file, update the "
        "golden hash deliberately -- never let it drift silently."
    )
