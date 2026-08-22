"""D2 Phase-0 spike (capture -> out-of-band deposit -> fresh-process re-read)
PLUS the Phase-1 Python advance entrypoint that builds on it.

Spec: `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble "Phase 0 — D2 SPIKE"
and "Phase 1 — evidence readers + the Python advance entrypoint". The Phase-0
section below (`reviewer_verdict_path` / `capture_and_deposit_reviewer_transcript`
/ `read_reviewer_verdict` / the spike-only CLI shim) is UNCHANGED from the
spike that already PASSED go/no-go — it is reused, not rewritten, per the
delegation's "build ON it, do not duplicate or contradict" instruction. Phase
1 ADDS: the mechanical test-judge evidence reader (`read_test_exit_code`),
the per-state judge dispatcher (`build_judge_for_state`), and the advance
entrypoint itself (`advance_main` / the CLI `main`) that rehydrates the
`Driver` at the bridge's current state and drives exactly one advance step
using the REAL judge factories from `gleipnir.engine.judges` — never a
default/trivial judge, so no state this module doesn't yet know how to
judge is silently advanced. Phase 2 (the TS `tool.execute.after` trigger)
was built separately (`.gleipnir/plugins/advance-hook.ts`).

**Phase 3 (this delegation) ADDS Seam 8: the live GIT→GATE branch.** Per
the plan's D5-CONVERGED decision, `read_pipeline_run_identity` reads the
plain-file, agent-read-only run-manifest sidecar
(`.gleipnir/var/run/pipeline-run.json`) for `(pipeline_id, head_sha)`, and
`advance_main` now intercepts `PipelineState.GIT` BEFORE reaching
`build_judge_for_state`: it fetches a real `Attestation` via
`fetch_attestation.fetch_attestation` and calls `Driver.attempt_gate`
instead of raising `UnjudgedState` for that one state.
`build_judge_for_state` ITSELF is left otherwise unchanged — it still
raises `UnjudgedState` for GIT (and every other state outside
`{SPEC_REVIEW, QUALITY, TEST}`) if called directly, because GIT has no
`Judge`-shaped transition at all (`attempt_gate` consumes an `Attestation`,
never a `Verdict`); only `advance_main`'s own dispatch now special-cases
GIT ahead of that call, so it never reaches `build_judge_for_state` for
that state on the live path.

**Completion-pass addition (quality-review Finding A, closes the live-
capture gap).** `capture_and_deposit_reviewer_transcript` (Phase-0 spike,
below) was, until now, only ever exercised from test files — nothing on the
live path ever called it, so `read_reviewer_verdict` always returned
`None` in a real armed run and the SPEC_REVIEW/QUALITY judges always fell
through to `NEEDS_HUMAN` regardless of what `quality-reviewer` actually
said. This pass wires the missing call: `advance_main` now accepts an
optional `reviewer_transcript: str | None` parameter; when provided, it is
deposited via `capture_and_deposit_reviewer_transcript` (using the
resumed driver's OWN current state, never a caller-asserted one)
IMMEDIATELY after `Driver.resume_from_bridge` and BEFORE the GIT branch /
`build_judge_for_state` dispatch — so the deposit genuinely exists by the
time any judge reads it back. The corresponding CLI flag,
`--reviewer-transcript-stdin`, reads the payload from stdin rather than an
argv value: an arbitrary reviewer transcript can contain shell-hostile
bytes, newlines, and unbounded length, none of which argv-passing (execve
argument-length limits, shell quoting/escaping) handles safely; stdin is
the caller-agnostic, size-unbounded, escaping-free channel already used by
`.gleipnir/plugins/advance-hook.ts`'s peer, `bin/gleipnir-preflight`'s
`spawnSync(..., {input: ...})`. Two new exceptions
(`ReviewerTranscriptMisuse`, `ReviewerTranscriptDepositFailed`) keep this
fail-closed: a transcript supplied for a state that has no
transcript-based judge (misuse), or a deposit that raises `OSError`
(disk/permission failure), both refuse BEFORE reaching
`build_judge_for_state`/`Driver.advance` — there is no path from "the
deposit didn't genuinely happen" to "the judge ran anyway."

**Phase-0 docstring, retained verbatim below.** This section tests exactly
ONE mechanism: H-c, the out-of-band CALLER deposit. `quality-reviewer` has
`write: deny` / `task: deny` (see `session-02-delegation-smoketest.md`) so it
can never write its own verdict file (H-b is already known-impossible, not
re-tested here). What this module proves is that the WRITE-CAPABLE CALLER
(the framework advance entrypoint / hook side, this module) can:

  (a) receive a `quality-reviewer` `task` delegation's returned text IN-BAND
      (the caller already holds this as an ordinary Python string — see
      `capture_and_deposit_reviewer_transcript`'s `task_result_text` param);
  (b) durably WRITE that text to a deterministic, known Tier-1 path,
      OUT-OF-BAND from the reviewer's own (denied) write capability;
  (c) have a LATER, GENUINELY SEPARATE process (simulating the
      `tool.execute.after` hook boundary) re-read that file's bytes,
      identical to what was captured;
  (d) derive that path with NO guessing — stable naming keyed on exactly
      `pipeline_id` + `state`.

**Path convention (Tier-1 RETRIEVED, per `.gleipnir/logs/README.md`):**

    <log_root>/<pipeline_id>/reviewer-verdict.<state>.txt

`log_root` defaults to `<repo_root>/.gleipnir/logs` (the real Tier-1
destination this framework already documents as "framework-process-written,
not roster-agent-written" — this module IS that framework process, invoked
out-of-band from the `quality-reviewer` delegation, never by the reviewer
itself). `log_root` is an INJECTABLE parameter (mirrors `config_root` in
`boundary.py` / `scratch_dir` in `sandbox/runtime.py`) so tests can point it
at a real, genuinely-writable directory (`tmp_path`) instead of the real
`.gleipnir/logs` tree, which is read-only-mounted inside the S-2 sandbox test
container (`bin/gleipnir-sandbox test` mounts the whole repo `:ro` at
`/work` — see `sandbox/runtime.py` `build_run_argv`). The production advance
entrypoint (Phase 1/2, NOT built here) runs OUTSIDE that container, as the
TS `tool.execute.after` hook's shelled-out process, where the real
`.gleipnir/logs/` tree is genuinely writable to the framework-process uid.

**Why a CLI shim lives in this same file.** The fresh-process re-read
(criterion (c)) is only genuinely tested by an actual OS-level separate
process — an in-process round-trip would not exercise the hook boundary this
spike targets. `_read_verdict_cli`/`__main__` is that separate process's
entrypoint, invokable as `python -m gleipnir.preflight.advance --state ...
--pipeline-id ... --log-root ...`, deliberately narrow (spike-only): it does
nothing but call `read_reviewer_verdict` and print the raw text (or exit
nonzero if absent). It is replaced by the real Phase-1 `advance` subcommand
dispatch in `__main__.py`, not extended in place.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

from gleipnir.engine import (
    Attestation,
    AttestationNotGreen,
    AttestationRequired,
    Judge,
    PipelineState,
    StepResult,
)
from gleipnir.engine.bridge import KeyUnavailable
from gleipnir.engine.driver import BridgeInvalid, Driver
from gleipnir.engine.judges import (
    make_quality_judge,
    make_spec_review_judge,
    make_test_judge,
)
from . import fetch_attestation

__all__ = [
    "DEFAULT_LOG_ROOT",
    "reviewer_verdict_path",
    "capture_and_deposit_reviewer_transcript",
    "read_reviewer_verdict",
    "DEFAULT_TEST_TIMEOUT_SECONDS",
    "read_test_exit_code",
    "UnjudgedState",
    "build_judge_for_state",
    "DEFAULT_RUN_ROOT",
    "PIPELINE_RUN_FILENAME",
    "pipeline_run_path",
    "read_pipeline_run_identity",
    "MissingRunIdentity",
    "ReviewerTranscriptMisuse",
    "ReviewerTranscriptDepositFailed",
    "advance_main",
    "main",
]


def _repo_root() -> Path:
    # src/gleipnir/preflight/advance.py -> repo root is three parents up
    # (mirrors __main__.py's _repo_root, kept independent/duplicated rather
    # than imported, since this module must stay a minimal, standalone spike
    # probe -- Phase 1 is where the two get unified for real).
    return Path(__file__).resolve().parents[3]


# Tier-1 RETRIEVED destination (`.gleipnir/logs/README.md`): framework-process
# writes only, never a roster agent. This module IS that framework process.
DEFAULT_LOG_ROOT = _repo_root() / ".gleipnir" / "logs"


def reviewer_verdict_path(
    state: str, pipeline_id: str, *, log_root: Path | None = None
) -> Path:
    """Pure path construction — no I/O. The stable, no-guessing convention
    (criterion (d)): `<log_root>/<pipeline_id>/reviewer-verdict.<state>.txt`.
    `log_root` defaults to the real Tier-1 `.gleipnir/logs` tree; tests
    inject a `tmp_path`-based override so the write actually lands somewhere
    genuinely writable inside the read-only-mounted S-2 sandbox."""

    root = log_root if log_root is not None else DEFAULT_LOG_ROOT
    return root / pipeline_id / f"reviewer-verdict.{state}.txt"


def capture_and_deposit_reviewer_transcript(
    task_result_text: str,
    state: str,
    pipeline_id: str,
    *,
    log_root: Path | None = None,
) -> Path:
    """(a)+(b): `task_result_text` is the in-band text the caller already
    holds (e.g. a `task` tool result string) -- capture is simply "the
    caller has this string", nothing more is needed to demonstrate (a).
    This function performs (b): durably WRITE it, out-of-band from the
    reviewer's own (denied) write capability, to the deterministic path
    `reviewer_verdict_path` computes. Returns that path.

    Writes UTF-8 text via `Path.write_text` (mirrors `boundary.py`'s "real
    stdlib I/O, no interpretation" discipline) after creating the
    `pipeline_id` subdirectory if absent."""

    path = reviewer_verdict_path(state, pipeline_id, log_root=log_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(task_result_text, encoding="utf-8")
    return path


def read_reviewer_verdict(
    state: str, pipeline_id: str, *, log_root: Path | None = None
) -> str | None:
    """(c)+(d): read back the deposited text from the SAME derived path
    (criterion (d): no guessing, keyed only on `state`/`pipeline_id`).
    Returns `None` if absent -- fail-closed reporting, never raises for the
    ordinary "not deposited yet" case. Genuinely exercising the
    fresh-process claim (criterion (c)) requires calling this function from
    an actually-separate OS process; see `_read_verdict_cli` below and
    `tests/test_advance_hook.py`, which spawns exactly that via
    `subprocess.run([sys.executable, "-m", "gleipnir.preflight.advance", ...])`."""

    path = reviewer_verdict_path(state, pipeline_id, log_root=log_root)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Phase 1 -- the mechanical TEST-judge evidence reader.
#
# `read_test_exit_code` is the caller-edge I/O this judge needs: it actually
# runs `bin/gleipnir-sandbox test -- --collect-only` (see
# `gleipnir.engine.judges.make_test_judge`'s docstring for why collect-only,
# not a full run) and hands back its raw process exit code. Never inside
# `engine/` or `judges.py` -- this module IS the caller edge.
#
# `argv` is an INJECTABLE override (mirrors `log_root` above): tests inject a
# fixture command instead of the real sandbox binary, because these tests
# themselves typically run *inside* the S-2 sandbox container
# (`bin/gleipnir-sandbox test`, `--network=none`), where spawning a NESTED
# sandbox invocation is likely infeasible -- the same reasoning
# `tests/test_judges_live.py`'s module docstring already states for why that
# file is fixture-only, never a live-invoked nested subprocess.
# ---------------------------------------------------------------------------

# Generous default: a real `bin/gleipnir-sandbox test` run (container
# start-up + the full suite) is not fast; a short timeout here would turn an
# honest slow-but-passing run into a fabricated NEEDS_HUMAN.
DEFAULT_TEST_TIMEOUT_SECONDS = 300.0


def _default_sandbox_test_argv() -> list[str]:
    return [
        str(_repo_root() / "bin" / "gleipnir-sandbox"),
        "test",
        "--",
        "--collect-only",
    ]


def read_test_exit_code(
    argv: Sequence[str] | None = None,
    *,
    timeout: float | None = DEFAULT_TEST_TIMEOUT_SECONDS,
) -> int | None:
    """Run `bin/gleipnir-sandbox test -- --collect-only` (or the injected
    `argv`, for tests) as a real OS subprocess and return its raw exit code.

    Mechanical evidence only -- no parsing, no verdict logic (that is
    `make_test_judge`'s job; this function's one responsibility is sourcing
    the raw int). Fail-closed reporting, mirroring `read_reviewer_verdict`:
    returns `None` -- never raises -- if the subprocess cannot be started
    (missing binary, permission error) or times out, so a caller-side
    problem routes to `Verdict.NEEDS_HUMAN`, never a fabricated PASS/FAIL.
    """

    command = list(argv) if argv is not None else _default_sandbox_test_argv()
    try:
        completed = subprocess.run(command, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.returncode


# ---------------------------------------------------------------------------
# Phase 3 -- D5 sidecar read side (run-identity persistence; D5 CONVERGED).
#
# `.gleipnir/var/run/pipeline-run.json` = `{"pipeline_id": ..., "head_sha":
# ...}` is a FRAMEWORK-WRITTEN, agent-read-only PLAIN FILE (no own
# HMAC/digest -- integrity comes from the existing `.gleipnir/var/run/`
# agent-unwritable grant class; see the plan's "D5 -- CONVERGED" section).
# This module only ever READS it via `read_pipeline_run_identity` -- the
# write side is the git broker's `commit_changes`
# (`src/gleipnir/broker/git/mcp_server.py`), out of THIS delegation's scope
# per the plan's Trace table. `run_root` is an INJECTABLE override (mirrors
# `log_root` above) so tests point it at a genuinely-writable `tmp_path`
# instead of the real `.gleipnir/var/run/` tree, which -- like
# `.gleipnir/logs/` -- is read-only-mounted inside the S-2 sandbox test
# container.
# ---------------------------------------------------------------------------

# Tier-0 framework-written destination (D5 CONVERGED): plain file, no own
# MAC. `gleipnir-code` denies `.gleipnir/**`, so this module (agent-
# unreachable per the plan's grant table) is the only roster-adjacent code
# path that ever reads it; nothing under this package ever writes it.
DEFAULT_RUN_ROOT = _repo_root() / ".gleipnir" / "var" / "run"
PIPELINE_RUN_FILENAME = "pipeline-run.json"


def pipeline_run_path(*, run_root: Path | None = None) -> Path:
    """Pure path construction -- no I/O. `run_root` defaults to the real
    `.gleipnir/var/run/` tree; tests inject a `tmp_path`-based override."""

    root = run_root if run_root is not None else DEFAULT_RUN_ROOT
    return root / PIPELINE_RUN_FILENAME


def read_pipeline_run_identity(
    *, run_root: Path | None = None
) -> tuple[str, str] | None:
    """Read the D5 sidecar and return `(pipeline_id, head_sha)`, or `None`
    if the file is absent, unreadable, not valid JSON, not a JSON object, or
    missing/non-string/empty `pipeline_id`/`head_sha` fields.

    Fail-closed by construction (mirrors `read_reviewer_verdict`): the
    GIT-state branch in `advance_main` treats `None` as "GATE cannot be
    attempted" and refuses (`MissingRunIdentity`) -- it NEVER invents a
    fallback `pipeline_id` or `head_sha`. This function itself never raises
    for the ordinary "sidecar not written yet" case; it only ever returns
    `None` or a well-formed pair.
    """

    path = pipeline_run_path(run_root=run_root)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    pipeline_id = data.get("pipeline_id")
    head_sha = data.get("head_sha")
    if not isinstance(pipeline_id, str) or not pipeline_id:
        return None
    if not isinstance(head_sha, str) or not head_sha:
        return None

    return pipeline_id, head_sha


class MissingRunIdentity(Exception):
    """Raised by `advance_main` when the resumed bridge's current state is
    `PipelineState.GIT` but `read_pipeline_run_identity` returned `None`
    (the D5 sidecar is absent or malformed). Fail-closed, mirroring
    `UnjudgedState`: GATE cannot be attempted without a trustworthy run
    identity, so no `Driver.attempt_gate` call is made and the bridge is
    left exactly as it was on resume (still at GIT)."""


# ---------------------------------------------------------------------------
# Phase 1 -- per-state judge dispatch + the advance entrypoint itself.
#
# `build_judge_for_state` is the ONLY place that decides which real judge
# factory + evidence reader applies to the bridge's current state. It
# deliberately knows about exactly the three judged transitions this plan's
# Phase 1 wires (SPEC_REVIEW, QUALITY, TEST) and refuses (`UnjudgedState`)
# for every other state if called directly -- GIT included, because GIT has
# no `Judge`-shaped transition at all (`Engine.attempt_gate` consumes an
# `Attestation`, never a `Verdict`). Phase 3's `advance_main` now special-
# cases GIT ahead of this dispatcher (see below) rather than ever falling
# back to a default/trivial-PASS judge, which would be exactly the
# silent-advance/self-attestation shape this plan forbids.
# ---------------------------------------------------------------------------


class UnjudgedState(Exception):
    """Raised by `build_judge_for_state` when the bridge's current state has
    no REAL judge wired (`SPEC_REVIEW`/`QUALITY`/`TEST` are the only three).
    `advance_main`/`main` treat this as a fail-closed refusal: no
    `Driver.advance` call is made, so nothing is written and the bridge is
    left exactly as it was on resume. `PipelineState.GIT` is deliberately
    NOT exempted from this raise when `build_judge_for_state` is called
    directly (it categorically has no Judge) -- `advance_main`'s own
    dispatch intercepts GIT before ever reaching this function, so the live
    advance path never triggers this exception for that state."""

    def __init__(self, state: "PipelineState") -> None:
        super().__init__(
            f"no Phase-1 judge is wired for pipeline state {state.value!r}"
        )
        self.state = state


def _bound_test_exit_code_reader(
    argv: Sequence[str] | None, timeout: float | None
) -> Callable[[], int | None]:
    """Bind `read_test_exit_code`'s caller-supplied `argv`/`timeout` into the
    zero-argument `Callable[[], int | None]` shape `make_test_judge` expects
    (`gleipnir.engine.judges.make_test_judge`'s parameter contract)."""

    return lambda: read_test_exit_code(argv, timeout=timeout)


def _bound_reviewer_verdict_reader(
    state: str, pipeline_id: str, log_root: Path | None
) -> Callable[[], str | None]:
    """Bind `read_reviewer_verdict`'s caller-supplied `state`/`pipeline_id`/
    `log_root` into the zero-argument `Callable[[], str | None]` shape
    `make_spec_review_judge`/`make_quality_judge` expect."""

    return lambda: read_reviewer_verdict(state, pipeline_id, log_root=log_root)


def build_judge_for_state(
    state: "PipelineState",
    *,
    pipeline_id: str,
    log_root: Path | None = None,
    test_argv: Sequence[str] | None = None,
    test_timeout: float | None = DEFAULT_TEST_TIMEOUT_SECONDS,
) -> "Judge":
    """Dispatch: build the REAL `Judge` for `state`, wiring each factory in
    `gleipnir.engine.judges` to its Phase-1 evidence reader --
    `read_reviewer_verdict` (the D2-spike-confirmed transcript path) for
    `SPEC_REVIEW`/`QUALITY`, `read_test_exit_code` (the mechanical sandbox
    exit code) for `TEST`. Raises `UnjudgedState` for any other state.

    Zero edits to `judges.py`: this function only CALLS the existing
    `make_spec_review_judge`/`make_quality_judge`/`make_test_judge`
    factories with a caller-edge-bound reader (call-site-only wiring, D1).
    """

    if state is PipelineState.TEST:
        return make_test_judge(_bound_test_exit_code_reader(test_argv, test_timeout))
    if state is PipelineState.SPEC_REVIEW:
        return make_spec_review_judge(
            _bound_reviewer_verdict_reader(state.value, pipeline_id, log_root)
        )
    if state is PipelineState.QUALITY:
        return make_quality_judge(
            _bound_reviewer_verdict_reader(state.value, pipeline_id, log_root)
        )
    raise UnjudgedState(state)


class ReviewerTranscriptMisuse(Exception):
    """Raised by `advance_main` when a caller-supplied `reviewer_transcript`
    is provided but the resumed driver's CURRENT state is not one of
    `PipelineState.SPEC_REVIEW`/`PipelineState.QUALITY` -- the only two
    states with a transcript-based judge (`build_judge_for_state`). Fail-
    closed by construction (mirrors `UnjudgedState`/`MissingRunIdentity`):
    depositing a transcript for the wrong state would either be silently
    discarded (masking a caller/hook bug) or deposited to a path a
    *different* state's later judge could stumble on -- neither is
    acceptable, so this refuses outright, before any deposit is attempted
    and before `build_judge_for_state`/`Driver.advance` is ever reached."""


class ReviewerTranscriptDepositFailed(Exception):
    """Raised by `advance_main` when `capture_and_deposit_reviewer_transcript`
    itself fails (an `OSError` writing the Tier-1 log file -- e.g. a
    permissions or disk-space problem). Fail-closed by construction: wraps
    the underlying `OSError` so `main()` reports a specific, non-generic
    refusal and exits non-zero WITHOUT ever reaching
    `build_judge_for_state`/`Driver.advance` -- there is no path from a
    failed deposit to a judge call that would silently read whatever stale
    transcript (or nothing) happened to already be on disk."""


def advance_main(
    pipeline_id: str,
    bridge_path: str | Path,
    *,
    key_file: str | Path | None = None,
    log_root: Path | None = None,
    run_root: Path | None = None,
    test_argv: Sequence[str] | None = None,
    test_timeout: float | None = DEFAULT_TEST_TIMEOUT_SECONDS,
    fetch_attestation_fn: Callable[..., "Attestation"] | None = None,
    reviewer_transcript: str | None = None,
) -> "StepResult":
    """The advance entrypoint's one job (Design Principles, Gate 1):
    rehydrate the `Driver` at the bridge's CURRENT state and drive exactly
    one advance/gate step, using the REAL judge (or, for GIT, the REAL
    `Attestation`) for that state.

    Does NOT source evidence itself (delegates entirely to
    `build_judge_for_state` / `fetch_attestation` + the injected readers)
    and does NOT decide routing (the engine's `TRANSITIONS` table /
    `Engine.attempt_gate` does, inside `Driver.advance`/`Driver.attempt_gate`
    -- unchanged, call-site-only per D1).

    **Phase 3 ADDS the GIT branch.** If the resumed driver's current state
    is `PipelineState.GIT`, this function does NOT call
    `build_judge_for_state` (which would raise `UnjudgedState` for that
    state) -- it reads the D5 run-identity sidecar
    (`read_pipeline_run_identity`), fetches a genuine `Attestation` via
    `fetch_attestation_fn` (defaults to the real Seam-8
    `fetch_attestation.fetch_attestation`, injectable for tests), and calls
    `Driver.attempt_gate(attestation)` -- the ONLY path into GATE (G-3.2).
    A missing/malformed sidecar raises `MissingRunIdentity` (fail-closed,
    mirrors `UnjudgedState`) before any fetch or gate attempt is made. Every
    other state is unaffected: it still dispatches through
    `build_judge_for_state` + `Driver.advance`, exactly as Phase 1 built it.

    Fails closed by construction: every exception --
    `BridgeInvalid`/`KeyUnavailable` from `Driver.resume_from_bridge`,
    `UnjudgedState` from `build_judge_for_state`, `MissingRunIdentity` from
    the GIT branch's sidecar read, `AttestationRequired`/
    `AttestationNotGreen` from `Engine.attempt_gate` (RED/PENDING/ABSENT
    status OR a `pipeline_id` mismatch), or any `EngineError` from
    `Engine.step` -- propagates to the caller UNCHANGED. `Driver.advance`/
    `Driver.attempt_gate` is called AT MOST ONCE, with the one real judge or
    `Attestation` this function built; there is no fallback path that calls
    either again with a different (e.g. trivial-PASS or fabricated-GREEN)
    value.

    **Completion-pass addition: `reviewer_transcript`.** When not `None`,
    this is the just-captured, in-band `quality-reviewer` `task` delegation
    result text (sourced by the caller -- the TS `tool.execute.after` hook
    -- NEVER by the acting agent under review). It is deposited via
    `capture_and_deposit_reviewer_transcript` using the RESUMED DRIVER'S OWN
    `driver.state` (never a value the caller separately asserts), and this
    happens IMMEDIATELY after `Driver.resume_from_bridge` -- strictly
    BEFORE the GIT branch and BEFORE `build_judge_for_state` -- so the
    deposit genuinely exists by the time any judge reads it back. If
    `driver.state` is not `SPEC_REVIEW`/`QUALITY` (the only two states with
    a transcript-based judge), this raises `ReviewerTranscriptMisuse`
    without depositing anything. If the deposit's own file write fails,
    this raises `ReviewerTranscriptDepositFailed` (wrapping the `OSError`)
    -- again before any judge is built or `Driver.advance` is called.
    """

    driver = Driver.resume_from_bridge(pipeline_id, bridge_path, key_file=key_file)

    if reviewer_transcript is not None:
        if driver.state not in (PipelineState.SPEC_REVIEW, PipelineState.QUALITY):
            raise ReviewerTranscriptMisuse(
                f"a --reviewer-transcript-stdin payload was supplied but the "
                f"resumed bridge's current state is {driver.state.value!r}, "
                "which has no transcript-based judge (only spec_review/"
                "quality do) -- refusing before any deposit is attempted"
            )
        try:
            capture_and_deposit_reviewer_transcript(
                reviewer_transcript,
                driver.state.value,
                pipeline_id,
                log_root=log_root,
            )
        except OSError as exc:
            raise ReviewerTranscriptDepositFailed(
                f"failed to deposit the reviewer transcript for state "
                f"{driver.state.value!r}: {exc}"
            ) from exc

    if driver.state is PipelineState.GIT:
        identity = read_pipeline_run_identity(run_root=run_root)
        if identity is None:
            raise MissingRunIdentity(
                "no usable .gleipnir/var/run/pipeline-run.json sidecar -- "
                "GATE cannot be attempted without a trustworthy run identity "
                "(D5 CONVERGED; see .gleipnir/plans/seam7-seam8-wiring.md)"
            )
        run_pipeline_id, head_sha = identity
        fetcher = (
            fetch_attestation_fn
            if fetch_attestation_fn is not None
            else fetch_attestation.fetch_attestation
        )
        attestation = fetcher(run_pipeline_id, head_sha)
        return driver.attempt_gate(attestation)

    judge = build_judge_for_state(
        driver.state,
        pipeline_id=pipeline_id,
        log_root=log_root,
        test_argv=test_argv,
        test_timeout=test_timeout,
    )
    return driver.advance(judge)


def _build_advance_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gleipnir-preflight-advance",
        description=(
            "Phase 1 advance entrypoint: rehydrate the Driver at the "
            "bridge's current state, build the real judge for that state "
            "(the mechanical sandbox exit code for TEST; the independent "
            "quality-reviewer transcript for SPEC_REVIEW/QUALITY), and "
            "advance exactly one step. Fails closed -- non-zero exit, no "
            "bridge write -- for any other state or any error; never falls "
            "back to a default PASS judge."
        ),
    )
    parser.add_argument("--pipeline-id", required=True)
    parser.add_argument("--bridge-path", required=True)
    parser.add_argument(
        "--key-file",
        default=None,
        help="path to the bridge verifier key (default: GLEIPNIR_MARKER_KEY_FILE env)",
    )
    parser.add_argument(
        "--log-root",
        default=None,
        help="Tier-1 reviewer-verdict log root (default: <repo>/.gleipnir/logs)",
    )
    parser.add_argument(
        "--run-root",
        default=None,
        help=(
            "D5 sidecar run-manifest root, i.e. the directory containing "
            "pipeline-run.json (default: <repo>/.gleipnir/var/run)"
        ),
    )
    parser.add_argument(
        "--test-timeout",
        type=float,
        default=DEFAULT_TEST_TIMEOUT_SECONDS,
        help="seconds before the sandbox collect-only subprocess is treated as unavailable",
    )
    parser.add_argument(
        "--reviewer-transcript-stdin",
        action="store_true",
        default=False,
        help=(
            "read the just-completed quality-reviewer task delegation's "
            "returned text VERBATIM from stdin and deposit it (via "
            "capture_and_deposit_reviewer_transcript) BEFORE building the "
            "judge for the bridge's current state. A flag, not a value, so "
            "an arbitrary transcript's length/bytes never need argv quoting "
            "or escaping. Only valid when the bridge's current state is "
            "spec_review/quality -- refuses otherwise (ReviewerTranscriptMisuse)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper over `advance_main`: parse args, invoke it, and turn every
    outcome into a fail-closed exit code -- never a silent 0 on an error
    path. This is the function `bin/gleipnir-preflight advance ...` reaches
    (via `__main__.py`'s subcommand dispatch); it is also directly callable
    with an explicit `argv` list for tests.

    Deliberately narrow catches, most specific first, so a genuinely novel
    engine fault is still reported (not swallowed) while never being
    treated as success.
    """

    args = _build_advance_parser().parse_args(argv)
    log_root = Path(args.log_root) if args.log_root else None
    run_root = Path(args.run_root) if args.run_root else None

    reviewer_transcript: str | None = None
    if args.reviewer_transcript_stdin:
        try:
            reviewer_transcript = sys.stdin.read()
        except Exception as exc:  # e.g. stdin closed/unavailable -- fail closed
            print(
                "gleipnir-preflight advance: refusing -- failed to read "
                f"--reviewer-transcript-stdin payload from stdin: {exc}",
                file=sys.stderr,
            )
            return 1

    try:
        result = advance_main(
            args.pipeline_id,
            args.bridge_path,
            key_file=args.key_file,
            log_root=log_root,
            run_root=run_root,
            test_timeout=args.test_timeout,
            reviewer_transcript=reviewer_transcript,
        )
    except (UnjudgedState, MissingRunIdentity) as exc:
        print(f"gleipnir-preflight advance: refusing -- {exc}", file=sys.stderr)
        return 1
    except (ReviewerTranscriptMisuse, ReviewerTranscriptDepositFailed) as exc:
        print(
            f"gleipnir-preflight advance: refusing, reviewer-transcript "
            f"capture/deposit failed: {exc}",
            file=sys.stderr,
        )
        return 1
    except (BridgeInvalid, KeyUnavailable) as exc:
        print(
            f"gleipnir-preflight advance: refusing, bridge/key invalid: {exc}",
            file=sys.stderr,
        )
        return 1
    except (AttestationRequired, AttestationNotGreen) as exc:
        print(
            f"gleipnir-preflight advance: refusing, attestation not green/matching: {exc}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # pragma: no cover -- see note below
        # Every state this module dispatches a judge for (SPEC_REVIEW,
        # QUALITY, TEST) has a TRANSITIONS entry for all three `Verdict`
        # members (engine/__init__.py), so `Engine.step` cannot raise
        # `NoSuchTransition`/`InvalidVerdict` for any state actually reached
        # here. GIT never reaches `Engine.step` at all (it is routed to
        # `Engine.attempt_gate` instead, whose only refusal modes are the
        # `AttestationRequired`/`AttestationNotGreen` branch caught above).
        # This branch is a deliberate defensive fail-closed backstop for a
        # genuinely unanticipated fault, not a reachable path under the
        # current TRANSITIONS table. Honest coverage note (Phase 0
        # precedent): not exercised by the test suite for that reason.
        print(f"gleipnir-preflight advance: advance failed: {exc}", file=sys.stderr)
        return 1

    escalated_suffix = " (ESCALATED)" if result.escalated else ""
    print(
        f"gleipnir-preflight advance: advanced to {result.state.value}{escalated_suffix}",
        file=sys.stderr,
    )
    return 0


# ---------------------------------------------------------------------------
# Spike-only CLI shim: the genuinely-separate-process side of criterion (c).
# Deliberately narrow -- this is the Phase-0 spike probe's own entrypoint
# (invoked via `python -m gleipnir.preflight.advance --state ...`), kept
# UNCHANGED and separate from the real Phase-1 `main`/`advance_main` above.
# The real advance entrypoint is reached via `bin/gleipnir-preflight advance`
# (`__main__.py`'s subcommand dispatch calling this module's `main`), never
# via this module's own `__main__` block.
# ---------------------------------------------------------------------------

def _build_spike_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gleipnir-preflight-advance-spike",
        description=(
            "D2 Phase-0 spike-only probe: read back a previously-deposited "
            "reviewer verdict from a genuinely separate process and print it "
            "verbatim to stdout (no trailing newline added), so a parent "
            "process can compare stdout byte-for-byte to what it captured."
        ),
    )
    parser.add_argument("--state", required=True)
    parser.add_argument("--pipeline-id", required=True)
    parser.add_argument("--log-root", required=True)
    return parser


def _read_verdict_cli(argv: list[str] | None = None) -> int:
    """Exit 0 with the verdict text written verbatim to stdout if found;
    exit 1 (no stdout) if absent -- fail-closed for this probe's purposes."""

    args = _build_spike_cli_parser().parse_args(argv)
    verdict = read_reviewer_verdict(
        args.state, args.pipeline_id, log_root=Path(args.log_root)
    )
    if verdict is None:
        return 1
    sys.stdout.write(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(_read_verdict_cli())
