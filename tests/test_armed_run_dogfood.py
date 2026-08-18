"""Armed-run dogfood — end-to-end composition proof for the G-5 loop.

Plan: `.gleipnir/plans/armed-run-dogfood.md` (authority). Every piece of the
G-5 loop (`Driver.advance` -> `Engine.step` -> `write_bridge` re-mint ->
`EventBus.emit` -> ledger `reduce`/`reconcile` -> preflight) is unit-tested in
isolation elsewhere in this suite; this module proves their *composition*,
plus the Python<->TS bridge contract, end-to-end. Tests only: no `src/**`,
`.gleipnir/**`, or `plugins/**` change accompanies this file.

**Seams named, NOT automated here (never asserted green):**

  * **Seam 7 -- the live opencode advance hook.** A real `tool.execute.after`
    handler that calls `Driver.advance` in-process during an opencode session
    is not built. This harness drives `Driver.advance` directly,
    out-of-band (plan D1) -- proving the *Python loop* the hook would call,
    not the hook itself.
  * **Seam 8 -- real CI attestation into `attempt_gate` (G-3.2).** This
    harness never sources a genuine `Attestation` from CI and never calls
    `Engine.attempt_gate`/reaches GIT->GATE. GIT has no PASS edge by design;
    attestation-bound gating is a separate, not-yet-automated seam.

**Payload-blind (no self-attestation).** Every judge exercised below --
`_trivial_completion_judge` for every forward hop, `FixedJudge(Verdict.FAIL)`
for the forced revert -- ignores its `payload` argument unconditionally.
`test_judges_are_payload_blind_no_self_attestation_channel` asserts this
structurally: both judges return the same verdict when called with a
sentinel payload as when called with an empty one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import pytest

from gleipnir.bus import Event, EventBus, EventKind, RevertOccurredEvent
from gleipnir.engine import PipelineState, StepResult, Verdict
from gleipnir.engine.allow_table import allowed_agents_for
from gleipnir.engine.bridge import StateMarker, load_key, validate_state
from gleipnir.engine.driver import Driver, _trivial_completion_judge
from gleipnir.ledger.reconcile import reconcile
from gleipnir.ledger.reduce import reduce
from gleipnir.preflight.boundary import (
    DEV_MODE_LABEL,
    KeyState,
    PathProbe,
    Posture,
    ProbeOutcome,
    ProbeResult,
    RequestedMode,
)
from gleipnir.preflight.boundary import Verdict as PreflightVerdict
from gleipnir.preflight.boundary import decide, run_preflight

PIPELINE_ID = "pl-dogfood-armed-run-1"
SESSION_ID = "session-armed-run-dogfood"

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDEN_KEY_PATH = FIXTURES_DIR / "golden_key.bin"
DOGFOOD_BRIDGE_PATH = FIXTURES_DIR / "dogfood_bridge.json"

# The real repo `.gleipnir` config root + its dev-mode marker key, used ONLY
# by the "real default probes" preflight assertion (§2.6's live-boundary
# claim). Everything else in this module stays under `tmp_path`.
REPO_CONFIG_ROOT = Path(__file__).resolve().parents[1] / ".gleipnir"
REPO_KEY_PATH = REPO_CONFIG_ROOT / "keys" / "marker.key"

VERIFIER_KEY = b"dogfood-harness-verifier-key-not-on-agent-surface"

# BRAINSTORM -> PLAN -> SPEC_REVIEW -> TEST -> CODE -> QUALITY: five forward
# PASS hops, per TRANSITIONS (engine/__init__.py) -- no FAIL edge exists on
# any of these, so this reaches QUALITY deterministically (plan §2.4).
_FORWARD_HOP_COUNT = 5


class FixedJudge:
    """Always returns the same verdict, ignoring state and payload (mirrors
    `tests/test_driver_emits_revert.py::FixedJudge`) -- the payload-blind,
    fixed-verdict judge the forced revert uses (plan D2/§2.4)."""

    def __init__(self, verdict: Verdict) -> None:
        self.verdict = verdict

    def __call__(self, _state: PipelineState, _payload: Mapping[str, Any]) -> Verdict:
        return self.verdict


FIXED_FAIL_JUDGE = FixedJudge(Verdict.FAIL)


def _session_log_path(logs_dir: Path) -> Path:
    return logs_dir / f"{SESSION_ID}.jsonl"


def _read_events(logs_dir: Path, session_id: str) -> list[Event]:
    path = logs_dir / f"{session_id}.jsonl"
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    return [Event.from_json_line(line) for line in lines]


def _drive_forward_to_quality(driver: Driver) -> None:
    """Advance BRAINSTORM->...->QUALITY via the payload-blind trivial-PASS
    judge, minting each hop's bridge at a LIVE/current `minted_at`
    (`minted_at=None`, class-2 forward-run bridge, plan §2.3) -- mirrors
    `tests/test_driver_emits_revert.py::drive_to`."""

    while driver.state is not PipelineState.QUALITY:
        driver.advance(_trivial_completion_judge, minted_at=None)


# ---------------------------------------------------------------------------
# Fixtures (arrange scaffolding, plan Assemble step 1).
# ---------------------------------------------------------------------------


@pytest.fixture
def key_file(tmp_path: Path) -> Path:
    kf = tmp_path / "key"
    kf.write_bytes(VERIFIER_KEY)
    return kf


@pytest.fixture
def bridge_path(tmp_path: Path) -> Path:
    return tmp_path / "var" / "run" / "pipeline-state.json"


@pytest.fixture
def logs_dir(tmp_path: Path) -> Path:
    return tmp_path / "logs"


@pytest.fixture
def armed_driver(bridge_path: Path, key_file: Path, logs_dir: Path) -> Driver:
    """A Driver at BRAINSTORM with an injected `EventBus` writing to a
    `tmp_path`-scoped `logs_dir` (plan §2.5) -- ready to be driven through
    the composed loop."""

    bus = EventBus(SESSION_ID, logs_dir=logs_dir)
    driver = Driver(PIPELINE_ID, bridge_path, key_file=key_file, bus=bus)
    driver.write_bridge()
    return driver


# ---------------------------------------------------------------------------
# Assertion 1 -- bridge re-minted correctly at each forward step.
# ---------------------------------------------------------------------------


def test_forward_hops_remint_valid_bridges_at_each_step(
    armed_driver: Driver, bridge_path: Path, key_file: Path
) -> None:
    driver = armed_driver
    key = load_key(key_file)

    for _ in range(_FORWARD_HOP_COUNT):
        result = driver.advance(_trivial_completion_judge, minted_at=None)
        assert isinstance(result, StepResult)

        marker = StateMarker.from_json(bridge_path.read_text())
        # Live/current minted_at -> default now/max_age_seconds passes
        # freshness naturally; no override needed (plan §2.3 class-2).
        assert validate_state(marker, key) is True
        assert marker.pipeline_state == driver.state.value
        assert marker.allowed_agents == tuple(sorted(allowed_agents_for(driver.state)))

        resumed = Driver.resume_from_bridge(PIPELINE_ID, bridge_path, key_file=key_file)
        assert resumed.state is driver.state

    assert driver.state is PipelineState.QUALITY


# ---------------------------------------------------------------------------
# Assertion 2 -- the forced QUALITY->CODE revert emits exactly one correct
# RevertOccurredEvent (and forward hops emit none).
# ---------------------------------------------------------------------------


def test_forced_revert_emits_exactly_one_revert_occurred_event(
    armed_driver: Driver, logs_dir: Path
) -> None:
    driver = armed_driver
    _drive_forward_to_quality(driver)

    # Edge case (plan §2.8): reach QUALITY exactly once, deliberately, before
    # injecting the FAIL judge -- and no revert event was emitted by any
    # forward PASS hop.
    assert driver.state is PipelineState.QUALITY
    assert _read_events(logs_dir, SESSION_ID) == []

    result = driver.advance(FIXED_FAIL_JUDGE, minted_at=None)
    assert result.state is PipelineState.CODE
    assert result.escalated is False
    assert driver.engine.revert_count == 1

    events = _read_events(logs_dir, SESSION_ID)
    revert_events = [e for e in events if e.kind is EventKind.REVERT_OCCURRED]
    assert len(events) == 1
    assert len(revert_events) == 1

    evt = revert_events[0]
    assert isinstance(evt.payload, RevertOccurredEvent)
    assert evt.payload.from_state == PipelineState.QUALITY.value
    assert evt.payload.to_state == PipelineState.CODE.value
    assert evt.payload.escalated is False
    assert evt.payload.revert_count == 1


# ---------------------------------------------------------------------------
# Assertion 3 -- ledger reduce: real (not vacuous) escalation_rate.
# ---------------------------------------------------------------------------


def test_ledger_reduce_reports_real_not_vacuous_escalation_rate(
    armed_driver: Driver, logs_dir: Path
) -> None:
    driver = armed_driver
    _drive_forward_to_quality(driver)
    driver.advance(FIXED_FAIL_JUDGE, minted_at=None)

    report = reduce(_session_log_path(logs_dir))

    assert report.revert_count.value == 1
    assert report.revert_count.denominator == 1
    assert report.escalation_count.value == 0
    assert report.escalation_count.denominator == 1
    # Real measured rate (reverts WERE observed) -- NOT the vacuous
    # value=None/denominator=0 sentinel, which only applies at
    # revert_count==0 (plan §2.8 edge case).
    assert report.escalation_rate.value == 0.0
    assert report.escalation_rate.denominator == 1


# ---------------------------------------------------------------------------
# Assertion 4 -- ledger reconcile agrees (a passing reconcile IS the
# assertion; it raises LedgerError on any divergence).
# ---------------------------------------------------------------------------


def test_ledger_reconcile_agrees_without_raising(
    armed_driver: Driver, logs_dir: Path
) -> None:
    driver = armed_driver
    _drive_forward_to_quality(driver)
    driver.advance(FIXED_FAIL_JUDGE, minted_at=None)

    log_path = _session_log_path(logs_dir)
    report = reduce(log_path)

    reconciled = reconcile(log_path, report)  # raises LedgerError on divergence

    assert reconciled.revert_count == 1
    assert reconciled.escalation_count == 0


# ---------------------------------------------------------------------------
# Assertion 6 -- preflight: PROCEED_UNCLOSED under override, REFUSE on a
# writable enforcement file (no override) and on an absent key.
# ---------------------------------------------------------------------------


def _fake_config_root(tmp_path: Path) -> tuple[Path, Path]:
    """A `.gleipnir`-shaped tree under `tmp_path` (mirrors
    `test_preflight_decision.py::config_root`), returning (root, key_path)."""

    root = tmp_path / ".gleipnir"
    (root / "agents").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("---\nname: orchestrator\n---\n")
    (root / "decisions").mkdir()
    (root / "decisions" / "d1.md").write_text("# decision\n")
    (root / "goals").mkdir()
    (root / "goals" / "manifest.md").write_text("# goals\n")
    (root / "keys").mkdir()
    key_path = root / "keys" / "hmac.key"
    key_path.write_bytes(b"super-secret-key-bytes")
    (root / "plugins").mkdir()
    (root / "plugins" / "sequence-gate.ts").write_text("// gate\n")
    (root / "stage-role-map.md").write_text("# map\n")
    (root / "AGENTS.md").write_text("# agents\n")
    return root, key_path


def test_preflight_proceeds_unclosed_under_override_on_real_default_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(a) The PROCEED_UNCLOSED claim against the REAL default probes -- no
    injected `write_probe`/`read_probe` -- run against the actual repo
    `.gleipnir` enforcement paths (plan §2.6's "framing honesty" fix). This
    is a live claim about THIS boundary, not merely a re-exercise of
    `decide()`'s pure logic (that is `test_preflight_decision.py`'s job).

    Deterministic regardless of host vs. in-sandbox (ro-mounted) execution:
    the real repo `.gleipnir/keys/marker.key` is genuinely readable by this
    process either way, which alone makes the `keys/**` RO_AND_UNREADABLE
    path NOT_CLOSED -- so `override_ack=True` always yields
    `PROCEED_UNCLOSED`/`DEV_MODE_LABEL` here, never `CLOSED`."""

    if not REPO_KEY_PATH.exists():
        pytest.skip("no real .gleipnir/keys/marker.key present in this checkout")

    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(REPO_KEY_PATH))
    decision = run_preflight(
        REPO_CONFIG_ROOT,
        agent_uid=os.getuid(),
        agent_gid=os.getgid(),
        override_ack=True,
    )
    assert decision.verdict is PreflightVerdict.PROCEED_UNCLOSED
    assert decision.label == DEV_MODE_LABEL


def _write_ok(target: Path, agent_uid: int, agent_gid: int) -> ProbeResult:
    return ProbeResult(ProbeOutcome.WRITE_OK)


def test_preflight_proceeds_unclosed_under_override_with_injected_write_ok_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Optional determinism variant (plan §2.6): injected `WRITE_OK` fakes
    over a fake `.gleipnir`-shaped tree. This re-tests `decide()`'s logic
    (already covered by `test_preflight_decision.py`) -- it is labelled here
    as NOT a claim about the live boundary; the real-probes test above
    carries that claim. `WRITE_OK` (never `WRITE_DENIED`) is the correct
    polarity for NOT_CLOSED -- `WRITE_DENIED` + a present key yields
    `CLOSED`, the opposite."""

    root, key_path = _fake_config_root(tmp_path)
    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(key_path))
    decision = run_preflight(
        root,
        agent_uid=os.getuid(),
        agent_gid=os.getgid(),
        override_ack=True,
        write_probe=_write_ok,
        read_probe=_write_ok,
    )
    assert decision.verdict is PreflightVerdict.PROCEED_UNCLOSED
    assert decision.label == DEV_MODE_LABEL


def test_preflight_refuses_on_writable_enforcement_file_without_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(b) A writable (WRITE_OK) enforcement file + `override_ack=False` ->
    REFUSE."""

    root, key_path = _fake_config_root(tmp_path)
    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(key_path))

    def read_denied(target: Path, agent_uid: int, agent_gid: int) -> ProbeResult:
        return ProbeResult(ProbeOutcome.WRITE_DENIED)

    decision = run_preflight(
        root,
        agent_uid=os.getuid(),
        agent_gid=os.getgid(),
        override_ack=False,
        # fail-closed guarantee now lives under requested_mode=CAGED per
        # operating-posture.md default-uncaged flip: this test's intent is
        # "a requested cage that isn't closed must refuse", not the
        # (now legitimate) uncaged default.
        requested_mode=RequestedMode.CAGED,
        write_probe=_write_ok,
        read_probe=read_denied,
    )
    assert decision.verdict is PreflightVerdict.REFUSE


def test_preflight_refuses_when_key_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(c) An absent key (`GLEIPNIR_MARKER_KEY_FILE` unset / pointing at a
    missing file) -> REFUSE, even with every path otherwise closed."""

    root, key_path = _fake_config_root(tmp_path)
    key_path.unlink()
    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(key_path))  # points at nothing

    def write_denied(target: Path, agent_uid: int, agent_gid: int) -> ProbeResult:
        return ProbeResult(ProbeOutcome.WRITE_DENIED)

    decision = run_preflight(
        root,
        agent_uid=os.getuid(),
        agent_gid=os.getgid(),
        override_ack=False,
        # fail-closed guarantee now lives under requested_mode=CAGED per
        # operating-posture.md default-uncaged flip: this test's intent is
        # "an absent key + a requested cage must refuse", not the
        # (now legitimate) uncaged default.
        requested_mode=RequestedMode.CAGED,
        write_probe=write_denied,
        read_probe=write_denied,
    )
    assert decision.verdict is PreflightVerdict.REFUSE
    assert any("absent" in r for r in decision.reasons)


def test_override_ack_has_no_code_path_to_closed() -> None:
    """Confirm no override->CLOSED path (plan §2.6's invariant): even with
    `override_ack=True`, a NOT_CLOSED input can never yield `CLOSED`."""

    probes = [
        PathProbe("AGENTS.md", Posture.RO, ProbeResult(ProbeOutcome.WRITE_OK)),
    ]
    decision = decide(probes, KeyState.PRESENT, override_ack=True)
    assert decision.verdict is not PreflightVerdict.CLOSED
    assert decision.verdict is PreflightVerdict.PROCEED_UNCLOSED


# ---------------------------------------------------------------------------
# Assertion 5 -- cross-language handshake (Python side). The node side is
# `tests/test_sequence_gate.mjs`'s new dogfood-bridge block.
# ---------------------------------------------------------------------------


def test_dogfood_bridge_fixture_mac_validates_against_golden_key() -> None:
    """The committed `tests/fixtures/dogfood_bridge.json` (a Python-minted
    PLAN-state bridge, FIXED `minted_at=1000`, class-1 §2.3) validates
    against the shared `golden_key.bin` under the symmetric freshness
    override `now=1001` (`age = 1001 - 1000 = 1`, well within the default
    max age) -- the explicit override the fixed-`minted_at` fixture needs,
    per plan §2.3/Assemble step 7."""

    key = load_key(GOLDEN_KEY_PATH)
    marker = StateMarker.from_json(DOGFOOD_BRIDGE_PATH.read_text())

    assert validate_state(marker, key, now=1001) is True
    assert marker.pipeline_state == "plan"
    assert marker.allowed_agents == ("gleipnir-plan",)


def test_dogfood_bridge_fixture_resumes_via_resume_from_bridge_with_max_age_override() -> None:
    """`resume_from_bridge` has no `now=` parameter (it forwards only
    `max_age_seconds`, letting `now` default to real wall-clock) -- so the
    fixed-`minted_at=1000` fixture needs `max_age_seconds=10**12` here,
    NOT `now=1001` (plan §2.3's documented divergence between the two
    override forms)."""

    resumed = Driver.resume_from_bridge(
        "pl-dogfood-cross-lang-resume",
        DOGFOOD_BRIDGE_PATH,
        key_file=GOLDEN_KEY_PATH,
        max_age_seconds=10**12,
    )
    assert resumed.state is PipelineState.PLAN


def test_live_driver_mint_at_plan_matches_the_committed_dogfood_fixture(
    tmp_path: Path,
) -> None:
    """D4 form 2 (plan §2.3): the committed `dogfood_bridge.json` is not a
    hand-frozen file -- it is exactly what a live `Driver`, driven to PLAN
    with `key_file=golden_key.bin` and minted at `minted_at=1000`, produces.
    Proves the live driver mint path meets the TS gate's byte-for-byte MAC
    contract, not just a frozen fixture."""

    bridge_path = tmp_path / "dogfood-live-mint.json"
    driver = Driver("pl-dogfood-cross-lang-mint", bridge_path, key_file=GOLDEN_KEY_PATH)

    result = driver.advance(_trivial_completion_judge, minted_at=1000)  # BRAINSTORM -> PLAN
    assert result.state is PipelineState.PLAN
    assert driver.state is PipelineState.PLAN

    minted = StateMarker.from_json(bridge_path.read_text())
    committed = StateMarker.from_json(DOGFOOD_BRIDGE_PATH.read_text())
    assert minted == committed


# ---------------------------------------------------------------------------
# Payload-blind structural assertion (no self-attestation channel).
# ---------------------------------------------------------------------------


def test_judges_are_payload_blind_no_self_attestation_channel() -> None:
    """Neither the forward trivial-PASS judge nor the fixed-verdict FAIL
    judge ever inspects `payload` -- both return the same verdict whether
    called with an empty payload or one carrying a sentinel an
    attestation-reading judge would (wrongly) key off of."""

    sentinel_payload = {"result": "should be completely ignored", "quality": "garbage"}

    assert _trivial_completion_judge(PipelineState.CODE, {}) is Verdict.PASS
    assert _trivial_completion_judge(PipelineState.CODE, sentinel_payload) is Verdict.PASS
    assert (
        _trivial_completion_judge(PipelineState.CODE, {})
        == _trivial_completion_judge(PipelineState.CODE, sentinel_payload)
    )

    assert FIXED_FAIL_JUDGE(PipelineState.QUALITY, {}) is Verdict.FAIL
    assert FIXED_FAIL_JUDGE(PipelineState.QUALITY, sentinel_payload) is Verdict.FAIL
    assert (
        FIXED_FAIL_JUDGE(PipelineState.QUALITY, {})
        == FIXED_FAIL_JUDGE(PipelineState.QUALITY, sentinel_payload)
    )
