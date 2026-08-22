"""D2 Phase-0 spike proof: capture -> out-of-band deposit -> fresh-process
re-read of a `quality-reviewer` delegation's returned transcript text.

Spec: `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble "Phase 0 — D2 SPIKE".
Tests exactly the H-c mechanism (out-of-band CALLER deposit), never H-b
("reviewer writes its own file" -- already known-impossible: `write: deny` /
`task: deny` on `quality-reviewer`, per `session-02-delegation-smoketest.md`;
not re-tested here).

Each PASS criterion from the plan is covered by a distinct test:

  (a) the text can be captured in-band -- `_SIMULATED_VERDICT` below IS the
      in-band text a `task` tool result would hand the caller; no test
      actually invokes a live subagent delegation (pytest cannot do that),
      per the delegation's own instruction.
  (b) durable out-of-band write to a deterministic path --
      `test_capture_writes_durably_to_deterministic_path`.
  (c) a GENUINELY SEPARATE, fresh process reads it back byte-for-byte --
      `test_fresh_subprocess_reads_back_byte_for_byte` (real
      `subprocess.run`, not an in-process call -- an in-process round-trip
      would not exercise the hook-boundary unknown this spike targets).
  (d) the path is derivable without guessing --
      `test_path_is_derivable_without_guessing`.

Plus the fail-closed absent-verdict case (`read_reviewer_verdict` returns
`None` / the CLI shim exits 1) for symmetry with every other fail-closed
module in this codebase.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from gleipnir.preflight import advance


# A known-format verdict string simulating what a `quality-reviewer` `task`
# delegation would RETURN IN-BAND as its result (criterion (a) -- this is
# the in-band text; no live subagent is invoked from inside this test).
_SIMULATED_VERDICT = (
    "SPEC-CONFORM: PASS\n"
    "BLAST-RADIUS: PASS\n"
    "notes: reviewed the seam7/seam8 D2 spike probe; no over-broad grant "
    "detected.\n"
    "attested_by: quality-reviewer\n"
)

_PIPELINE_ID = "spike-pipeline-0001"
_STATE = "quality"


def _src_dir() -> Path:
    # tests/ -> repo root -> src, so the fresh subprocess can import
    # `gleipnir.preflight.advance` the same way pytest's own
    # `pythonpath = ["src"]` ini option does for the in-process import above.
    return Path(__file__).resolve().parents[1] / "src"


# ---------------------------------------------------------------------------
# (b) durable out-of-band write to a deterministic path
# ---------------------------------------------------------------------------

def test_capture_writes_durably_to_deterministic_path(tmp_path: Path):
    deposited_path = advance.capture_and_deposit_reviewer_transcript(
        _SIMULATED_VERDICT, _STATE, _PIPELINE_ID, log_root=tmp_path
    )

    assert deposited_path.exists()
    assert deposited_path.read_text(encoding="utf-8") == _SIMULATED_VERDICT
    # Same-process read-back also confirms the write actually landed at the
    # SAME path `reviewer_verdict_path` would derive independently.
    assert deposited_path == advance.reviewer_verdict_path(
        _STATE, _PIPELINE_ID, log_root=tmp_path
    )


def test_capture_creates_missing_pipeline_subdirectory(tmp_path: Path):
    # tmp_path itself exists but the pipeline_id subdir does not yet --
    # capture must create it, not assume it pre-exists.
    assert not (tmp_path / _PIPELINE_ID).exists()
    advance.capture_and_deposit_reviewer_transcript(
        _SIMULATED_VERDICT, _STATE, _PIPELINE_ID, log_root=tmp_path
    )
    assert (tmp_path / _PIPELINE_ID).is_dir()


# ---------------------------------------------------------------------------
# (c) a GENUINELY SEPARATE, fresh process reads it back byte-for-byte
# ---------------------------------------------------------------------------

def test_fresh_subprocess_reads_back_byte_for_byte(tmp_path: Path):
    # Deliberately includes a non-ASCII character and internal newlines, so
    # a byte-for-byte comparison is a real test, not a coincidence of a
    # trivial ASCII string.
    verdict_text = _SIMULATED_VERDICT + "unicode-check: \u2713 (checkmark)\n"

    advance.capture_and_deposit_reviewer_transcript(
        verdict_text, _STATE, _PIPELINE_ID, log_root=tmp_path
    )

    # The genuinely-separate process: a real OS subprocess, NOT an in-process
    # function call -- this is what actually exercises the fresh-process /
    # tool.execute.after-boundary unknown under test.
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gleipnir.preflight.advance",
            "--state",
            _STATE,
            "--pipeline-id",
            _PIPELINE_ID,
            "--log-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=False,  # raw bytes -- a genuine byte-for-byte comparison
        env={"PYTHONPATH": str(_src_dir())},
        timeout=30,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == verdict_text.encode("utf-8")


def test_fresh_subprocess_is_a_real_separate_process(tmp_path: Path):
    """Guard against accidentally degrading criterion (c) into an in-process
    call: assert the subprocess actually ran as its own OS process (has its
    own pid, distinct from this test's pid) by having it print its own pid
    alongside the verdict marker via a tiny wrapper invocation, and checking
    that invoking it twice in a row yields two DIFFERENT reported pids (ruling
    out any accidental in-process caching/reuse across calls)."""

    advance.capture_and_deposit_reviewer_transcript(
        _SIMULATED_VERDICT, _STATE, _PIPELINE_ID, log_root=tmp_path
    )

    def _run_once() -> tuple[int, bytes]:
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os, sys; sys.path.insert(0, sys.argv[1]); "
                "from gleipnir.preflight import advance as a; "
                "print(os.getpid()); "
                "sys.stdout.write(a.read_reviewer_verdict(sys.argv[2], sys.argv[3], "
                "log_root=__import__('pathlib').Path(sys.argv[4])))",
                str(_src_dir()),
                _STATE,
                _PIPELINE_ID,
                str(tmp_path),
            ],
            capture_output=True,
            text=False,
            timeout=30,
        )
        first_line, _, rest = proc.stdout.partition(b"\n")
        return int(first_line), rest

    pid_a, verdict_a = _run_once()
    pid_b, verdict_b = _run_once()

    assert pid_a != pid_b, "expected two genuinely distinct OS processes"
    assert verdict_a == _SIMULATED_VERDICT.encode("utf-8")
    assert verdict_b == _SIMULATED_VERDICT.encode("utf-8")


# ---------------------------------------------------------------------------
# (d) the path is derivable without guessing
# ---------------------------------------------------------------------------

def test_path_is_derivable_without_guessing(tmp_path: Path):
    expected = tmp_path / _PIPELINE_ID / f"reviewer-verdict.{_STATE}.txt"
    assert advance.reviewer_verdict_path(_STATE, _PIPELINE_ID, log_root=tmp_path) == expected


def test_path_is_stable_across_repeated_calls(tmp_path: Path):
    # Calling the deriver twice with the same inputs must yield the exact
    # same path -- no hidden randomness (e.g. timestamps, uuids) in the
    # naming convention.
    first = advance.reviewer_verdict_path(_STATE, _PIPELINE_ID, log_root=tmp_path)
    second = advance.reviewer_verdict_path(_STATE, _PIPELINE_ID, log_root=tmp_path)
    assert first == second


def test_default_log_root_is_under_gleipnir_logs():
    # Pure path computation -- no I/O -- so this is safe to assert even
    # though the real `.gleipnir/logs` tree is read-only-mounted inside the
    # S-2 sandbox test container.
    path = advance.reviewer_verdict_path(_STATE, _PIPELINE_ID)
    assert path.parent.parent.name == "logs"
    assert path.parent.parent.parent.name == ".gleipnir"
    assert path.name == f"reviewer-verdict.{_STATE}.txt"


def test_different_state_or_pipeline_id_yields_different_path(tmp_path: Path):
    base = advance.reviewer_verdict_path(_STATE, _PIPELINE_ID, log_root=tmp_path)
    other_state = advance.reviewer_verdict_path("spec_review", _PIPELINE_ID, log_root=tmp_path)
    other_pipeline = advance.reviewer_verdict_path(_STATE, "spike-pipeline-0002", log_root=tmp_path)
    assert base != other_state
    assert base != other_pipeline
    assert other_state != other_pipeline


# ---------------------------------------------------------------------------
# Fail-closed absent-verdict case (symmetry with the rest of the codebase)
# ---------------------------------------------------------------------------

def test_read_reviewer_verdict_returns_none_when_absent(tmp_path: Path):
    assert advance.read_reviewer_verdict(_STATE, _PIPELINE_ID, log_root=tmp_path) is None


def test_cli_shim_exits_1_when_absent(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gleipnir.preflight.advance",
            "--state",
            _STATE,
            "--pipeline-id",
            "no-such-pipeline",
            "--log-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(_src_dir())},
        timeout=30,
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
