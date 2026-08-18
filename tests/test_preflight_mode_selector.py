"""Test-first (RED) contract tests for the D1/D4/P1/P2 override-paradigm
mode selector + conditional relabel.

Spec: `.gleipnir/plans/override-paradigm.md` — §A (`boundary.py` diff), §B
(`__main__.py` diff), the Design Principles "Design Intent" clause, and
Stress-test acceptance criteria 1-10. Plan status: APPROVED,
SPEC-CONFORM-PASSED. Convergence note: P1/P2/P3 are operator-converged
inheritances, not open choices.

**STATUS AT AUTHORING TIME: RED BY DESIGN.** `RequestedMode`,
`UNCAGED_DEFAULT_LABEL`, `decide()`'s `requested_mode` keyword, and
`__main__`'s `--mode` flag do NOT exist yet in
`src/gleipnir/preflight/boundary.py` / `__main__.py` — those two files are
**operator-applied only** (converged P3; `gleipnir-code` DENIES
`src/gleipnir/preflight/**`, verified `.gleipnir/agents/gleipnir-code.md:16`;
no grant path exists for this change). This file is authored entirely under
`tests/**`, which is NOT in that deny list. These tests exist to FAIL now —
via `AttributeError` (the `RequestedMode` enum / `UNCAGED_DEFAULT_LABEL`
constant are absent) or via `SystemExit` (the `--mode` flag is unrecognized
by `argparse`) — and must go GREEN, UNMODIFIED, once the operator applies
the plan's §A/§B diffs (Axiom 1: the test is the arbiter, never weakened to
pass).

Contract pinned here (operator-converged; do not deviate):

  P1 — `requested_mode` NEVER influences the `all_closed`/`CLOSED`
       computation (the anti-false-assurance safety invariant). No mode
       value can turn a not-closed probe set into `CLOSED`, and no mode
       value can produce a caged success exit without a genuine `CLOSED`.
  P2 — the uncaged-default (no explicit caged request), not-closed case
       returns **exit 0** and a NEUTRAL, non-failing label (NOT the old
       "G-1 NOT closed (dev-mode)" deficiency framing).
  D1 — an explicitly-REQUESTED caged run that did NOT reach `CLOSED`
       **REFUSES**: non-zero exit, deficiency label RETAINED.
  D4 — the "NOT closed" deficiency label appears ONLY for the
       requested-caged-failed case; the uncaged-default path always gets
       the neutral label. Both branches are pinned side by side.
  Regression — the existing genuine `CLOSED` case (boundary actually held)
       is UNCHANGED: exit 0, the closed/held label, in BOTH modes.

Conventions inherited from the existing `tests/test_preflight_*.py` family:
`decide()` is exercised with hand-built `PathProbe` evidence (mocked edge,
same shape as `test_preflight_decision.py`'s `_closed_probe` helper — no
reliance on real OS permissions, safe under the root-run S-2 sandbox). CLI
(`__main__.main()`) is exercised with `run_preflight` monkeypatched to a
small recording fake, so the CLI-layer tests pin exactly one thing each: the
`--mode` -> `RequestedMode` -> `run_preflight(requested_mode=...)` binding,
and `main()`'s own verdict -> exit-code mapping — never real permission
bits (which the root-run sandbox would bypass anyway, `test_preflight_probe_
hostonly.py`'s documented trap).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gleipnir.preflight import __main__ as pfm
from gleipnir.preflight import boundary as pb


# ---------------------------------------------------------------------------
# Shared probe fixtures — same construction as test_preflight_decision.py's
# `_closed_probe` helper, kept local so this file has no import-order
# coupling to that module.
# ---------------------------------------------------------------------------

def _closed_probe(label: str, posture: pb.Posture = pb.Posture.RO) -> pb.PathProbe:
    read_result = None
    if posture is pb.Posture.RO_AND_UNREADABLE:
        read_result = pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED)
    return pb.PathProbe(
        label,
        posture,
        pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
        escapes_subtree=False,
        read_result=read_result,
    )


def _all_closed_probes() -> list[pb.PathProbe]:
    return [
        _closed_probe("agents/*.md"),
        _closed_probe("keys/**", pb.Posture.RO_AND_UNREADABLE),
    ]


def _not_closed_probes() -> list[pb.PathProbe]:
    """One genuinely writable path — the boundary did NOT close."""
    return [
        _closed_probe("agents/*.md"),
        pb.PathProbe(
            "AGENTS.md",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_OK),
        ),
    ]


# ---------------------------------------------------------------------------
# P1 / anti-forgery: requested_mode NEVER manufactures CLOSED. This is the
# load-bearing safety test — Design Intent clause (b); Stress-test #4.
# ---------------------------------------------------------------------------

class TestP1RequestedModeNeverInfluencesClosedComputation:
    """The critical adversarial test: pin that NO value of the mode selector
    can turn a not-closed probe set into CLOSED, and that a caged request on
    a not-closed boundary never yields a success verdict."""

    def test_no_requested_mode_value_yields_closed_from_not_closed_probes(self):
        not_closed = _not_closed_probes()
        for mode in pb.RequestedMode:
            decision = pb.decide(not_closed, pb.KeyState.PRESENT, requested_mode=mode)
            assert decision.verdict is not pb.Verdict.CLOSED, (
                f"requested_mode={mode!r} must never manufacture CLOSED from a "
                "not-closed probe set (P1 anti-false-assurance invariant)"
            )

    def test_caged_requested_on_not_closed_probes_never_yields_a_success_verdict(self):
        """The only verdict `main()` maps to a non-zero exit for a
        requested-caged run is REFUSE — pin that a CAGED request on a
        not-closed boundary lands there, never on CLOSED or PROCEED_UNCLOSED
        (the two verdicts that can reach a 0/success-shaped exit)."""
        decision = pb.decide(
            _not_closed_probes(), pb.KeyState.PRESENT, requested_mode=pb.RequestedMode.CAGED
        )
        assert decision.verdict is pb.Verdict.REFUSE
        assert decision.verdict is not pb.Verdict.CLOSED
        assert decision.verdict is not pb.Verdict.PROCEED_UNCLOSED

    def test_closed_requires_all_closed_regardless_of_key_state_and_mode(self):
        """`CLOSED` remains gated SOLELY on real probe evidence + key
        presence — an absent/empty key must still refuse even when caged
        was requested (mode cannot paper over a missing key either)."""
        for key_state in (pb.KeyState.ABSENT, pb.KeyState.EMPTY):
            decision = pb.decide(
                _all_closed_probes(), key_state, requested_mode=pb.RequestedMode.CAGED
            )
            assert decision.verdict is not pb.Verdict.CLOSED


# ---------------------------------------------------------------------------
# D1 / caged-without-CLOSED REFUSES (deficiency label retained).
# ---------------------------------------------------------------------------

class TestD1CagedRequestedWithoutClosedRefuses:
    def test_decide_caged_not_closed_refuses_with_deficiency_label(self):
        decision = pb.decide(
            _not_closed_probes(), pb.KeyState.PRESENT, requested_mode=pb.RequestedMode.CAGED
        )
        assert decision.verdict is pb.Verdict.REFUSE
        assert decision.label == pb.DEV_MODE_LABEL
        assert decision.label != pb.UNCAGED_DEFAULT_LABEL


class _RecordingRunPreflight:
    """A fake `run_preflight` that records the kwargs it was called with and
    returns a canned `PreflightDecision` — used to pin `main()`'s OWN
    `--mode` -> `RequestedMode` -> `run_preflight(...)` binding and its
    verdict -> exit-code mapping, independent of real OS permission bits
    (which the root-run S-2 sandbox bypasses anyway)."""

    def __init__(self, decision: "pb.PreflightDecision") -> None:
        self.decision = decision
        self.calls: list[dict] = []

    def __call__(self, config_root, agent_uid, agent_gid, **kwargs):
        self.calls.append(kwargs)
        return self.decision


def _cli_argv(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "--config-root",
        str(tmp_path),
        "--agent-uid",
        "0",
        "--agent-gid",
        "0",
        *extra,
    ]


class TestD1CLIBindingCagedNotClosedExitsOne:
    def test_cli_mode_caged_requests_requestedmode_caged(self, tmp_path: Path, monkeypatch):
        """Pins the §B binding: `--mode caged` must map to
        `RequestedMode.CAGED` and be threaded into `run_preflight(...,
        requested_mode=...)` — the mechanism, not just the exit code."""
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.REFUSE, pb.DEV_MODE_LABEL, ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path, "--mode", "caged"))
        assert recorder.calls[0]["requested_mode"] is pb.RequestedMode.CAGED
        assert exit_code == 1

    def test_cli_mode_caged_not_closed_exits_1(self, tmp_path: Path, monkeypatch):
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.REFUSE, pb.DEV_MODE_LABEL, ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path, "--mode", "caged"))
        assert exit_code == 1


# ---------------------------------------------------------------------------
# P2 / D4 / uncaged-default exit code = 0, neutral non-failing label.
# ---------------------------------------------------------------------------

class TestP2UncagedDefaultIsNonFailing:
    def test_decide_uncaged_explicit_not_closed_gets_neutral_non_failing_label(self):
        decision = pb.decide(
            _not_closed_probes(), pb.KeyState.PRESENT, requested_mode=pb.RequestedMode.UNCAGED
        )
        assert decision.label == pb.UNCAGED_DEFAULT_LABEL
        assert decision.verdict is not pb.Verdict.REFUSE
        assert decision.label != pb.DEV_MODE_LABEL
        assert "NOT closed" not in decision.label
        assert decision.reasons  # informational reasons retained, not dropped

    def test_decide_default_no_mode_arg_matches_explicit_uncaged(self):
        """The keyword-arg default (`RequestedMode.UNCAGED`) is what every
        existing caller gets for free — pin the no-arg call is identical to
        the explicit UNCAGED call, so the mode can never accidentally be
        CAGED without an explicit operator request."""
        probes = _not_closed_probes()
        default_decision = pb.decide(probes, pb.KeyState.PRESENT)
        explicit_decision = pb.decide(
            probes, pb.KeyState.PRESENT, requested_mode=pb.RequestedMode.UNCAGED
        )
        assert default_decision.verdict == explicit_decision.verdict
        assert default_decision.label == explicit_decision.label

    def test_cli_no_mode_flag_requests_requestedmode_uncaged_by_default(
        self, tmp_path: Path, monkeypatch
    ):
        """Pins the §B default binding: omitting `--mode` entirely must
        still thread `RequestedMode.UNCAGED` into `run_preflight(...)` —
        the safe default direction (mode can never accidentally be CAGED)."""
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.PROCEED_UNCLOSED, pb.UNCAGED_DEFAULT_LABEL, ("info",))
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path))
        assert recorder.calls[0]["requested_mode"] is pb.RequestedMode.UNCAGED
        assert exit_code == 0

    def test_cli_mode_uncaged_default_not_closed_exits_0(self, tmp_path: Path, monkeypatch):
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.PROCEED_UNCLOSED, pb.UNCAGED_DEFAULT_LABEL, ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path))
        assert exit_code == 0

    def test_cli_mode_uncaged_explicit_not_closed_exits_0(self, tmp_path: Path, monkeypatch):
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.PROCEED_UNCLOSED, pb.UNCAGED_DEFAULT_LABEL, ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path, "--mode", "uncaged"))
        assert exit_code == 0


# ---------------------------------------------------------------------------
# D4 / conditional relabel — pin BOTH branches explicitly, side by side.
# ---------------------------------------------------------------------------

class TestD4ConditionalRelabelBothBranches:
    def test_deficiency_label_only_for_requested_caged_failed(self):
        not_closed = _not_closed_probes()
        caged = pb.decide(not_closed, pb.KeyState.PRESENT, requested_mode=pb.RequestedMode.CAGED)
        uncaged = pb.decide(
            not_closed, pb.KeyState.PRESENT, requested_mode=pb.RequestedMode.UNCAGED
        )
        assert caged.label == pb.DEV_MODE_LABEL
        assert uncaged.label == pb.UNCAGED_DEFAULT_LABEL
        assert caged.label != uncaged.label
        assert caged.verdict is pb.Verdict.REFUSE
        assert uncaged.verdict is not pb.Verdict.REFUSE

    def test_override_ack_honesty_preserved_even_when_caged_was_requested(self):
        """Edge case from Trace: `--mode caged --override-ack` on a
        not-closed boundary must NOT be suppressed by the mode — override
        honesty wins, landing on PROCEED_UNCLOSED + the honest
        DEV_MODE_LABEL (the mode does not suppress the override's honest
        labelling)."""
        decision = pb.decide(
            _not_closed_probes(),
            pb.KeyState.PRESENT,
            override_ack=True,
            requested_mode=pb.RequestedMode.CAGED,
        )
        assert decision.verdict is pb.Verdict.PROCEED_UNCLOSED
        assert decision.label == pb.DEV_MODE_LABEL

    def test_cli_mode_caged_override_ack_not_closed_exits_2(self, tmp_path: Path, monkeypatch):
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.PROCEED_UNCLOSED, pb.DEV_MODE_LABEL, ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path, "--mode", "caged", "--override-ack"))
        assert recorder.calls[0]["requested_mode"] is pb.RequestedMode.CAGED
        assert recorder.calls[0]["override_ack"] is True
        assert exit_code == 2

    def test_cli_unknown_mode_value_is_an_argparse_error_not_a_silent_caged(
        self, tmp_path: Path, capsys
    ):
        """Stress-test #9: `argparse` must reject an unknown `--mode` value
        at the CLI boundary — no silent fall-through to `caged`. Asserting
        on the specific `invalid choice` message (rather than merely "some
        nonzero exit") keeps this RED for the right reason now (today's
        message is `unrecognized arguments: --mode zzz`, since the flag
        does not exist at all yet) and makes it a real pin of the eventual
        `choices=["uncaged", "caged"]` constraint, not a coincidental pass."""
        with pytest.raises(SystemExit) as excinfo:
            pfm.main(_cli_argv(tmp_path, "--mode", "zzz"))
        assert excinfo.value.code != 0
        assert "invalid choice" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Regression guard: the existing genuine CLOSED case is UNCHANGED in BOTH
# modes — the one piece of this contract the plan promises is untouched
# (`if all_closed:` at boundary.py:555 is explicitly unchanged by §A).
# ---------------------------------------------------------------------------

class TestRegressionClosedCaseUnchangedInBothModes:
    def test_decide_fully_closed_yields_closed_regardless_of_mode(self):
        for mode in pb.RequestedMode:
            decision = pb.decide(
                _all_closed_probes(), pb.KeyState.PRESENT, requested_mode=mode
            )
            assert decision.verdict is pb.Verdict.CLOSED
            assert "OS-perms floor" in decision.label
            assert decision.reasons == ()

    def test_decide_fully_closed_no_mode_arg_matches_pre_existing_behaviour(self):
        """This one is expected to ALREADY PASS pre-implementation too — it
        exercises no new surface, only confirming the untouched `all_closed`
        branch keeps working exactly as it does today (a true regression
        guard, not a new-feature RED test)."""
        decision = pb.decide(_all_closed_probes(), pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.CLOSED
        assert decision.reasons == ()

    def test_cli_mode_caged_on_closed_verdict_exits_0(self, tmp_path: Path, monkeypatch):
        """Stress-test #7 — the success cage: a CAGED request that DOES
        reach CLOSED exits 0, same as today's default success path."""
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.CLOSED, "G-1 boundary held at the OS-perms floor", ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path, "--mode", "caged"))
        assert recorder.calls[0]["requested_mode"] is pb.RequestedMode.CAGED
        assert exit_code == 0

    def test_cli_closed_verdict_exits_0_with_no_mode_flag_at_all(self, tmp_path: Path, monkeypatch):
        """Genuinely pre-existing behaviour, exercised with NO new surface
        at all (no `--mode`) — expected to ALREADY PASS today and to keep
        passing unmodified after the operator applies §A/§B."""
        recorder = _RecordingRunPreflight(
            pb.PreflightDecision(pb.Verdict.CLOSED, "G-1 boundary held at the OS-perms floor", ())
        )
        monkeypatch.setattr(pfm, "run_preflight", recorder)
        exit_code = pfm.main(_cli_argv(tmp_path))
        assert exit_code == 0


# ---------------------------------------------------------------------------
# CLI flag surface (D1) — direct pin of `build_parser()`'s new `--mode`
# argument, choices and default, independent of the exit-code mapping above.
# ---------------------------------------------------------------------------

class TestCLIModeFlagSurface:
    def test_build_parser_default_mode_is_uncaged(self):
        parser = pfm.build_parser()
        args = parser.parse_args(["--agent-uid", "0", "--agent-gid", "0"])
        assert args.mode == "uncaged"

    def test_build_parser_accepts_mode_caged(self):
        parser = pfm.build_parser()
        args = parser.parse_args(["--agent-uid", "0", "--agent-gid", "0", "--mode", "caged"])
        assert args.mode == "caged"

    def test_build_parser_rejects_an_unknown_mode_choice(self, capsys):
        parser = pfm.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--agent-uid", "0", "--agent-gid", "0", "--mode", "zzz"])
        assert "invalid choice" in capsys.readouterr().err
