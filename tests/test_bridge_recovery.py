"""Behaviour spec for the operator-only bridge recovery tool (L-C19).

Plan: `.gleipnir/plans/bridge-recovery.md` (Stress-test §, checks 1-22).
Exercises `src/gleipnir/preflight/bridge_recovery.py`:
  * `classify_bridge` (pure, no I/O) -- checks 1-11
  * `bridge_status_main` (injected config_root) -- check 12
  * `bridge_reset_main` (injected config_root) -- checks 13-19
  * `preflight_is_agent_invocable` / allowlist guard -- checks 20-21
Conformance (check 22) lives in `test_preflight_stdlib_only.py`.

All keyed logic delegates to `gleipnir.engine.bridge` (mint/validate); this
test mints real markers with a throwaway key so the MAC actually verifies.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gleipnir.engine.bridge import mint_state
from gleipnir.preflight import bridge_recovery
from gleipnir.preflight.bridge_recovery import (
    BRIDGE_REL,
    LOG_REL,
    OPERATOR_UID_ENV,
    Classification,
    bridge_reset_main,
    bridge_status_main,
    classify_bridge,
    next_command,
    preflight_is_agent_invocable,
)

_KEY = b"test-key-not-a-secret-0123456789"
_NOW = 1_700_000_000


def _mint_text(pipeline_state="plan", allowed=("gleipnir-plan",), minted_at=_NOW):
    marker = mint_state(pipeline_state, list(allowed), _KEY, minted_at=minted_at)
    return marker.to_json()


# --------------------------------------------------------------------------
# Classification (pure) -- Stress-test checks 1-11
# --------------------------------------------------------------------------


def test_check1_fresh_marker_is_healthy():
    text = _mint_text(minted_at=_NOW)
    cls, marker, age = classify_bridge(text, _KEY, now=_NOW)
    assert cls is Classification.HEALTHY
    assert age == 0
    assert marker is not None


def test_check2_valid_mac_4000s_old_is_stale():
    text = _mint_text(minted_at=_NOW - 4000)
    cls, _, age = classify_bridge(text, _KEY, now=_NOW)
    assert cls is Classification.STALE
    assert age == 4000


def test_check3_boundary_just_inside_3599_is_healthy():
    text = _mint_text(minted_at=_NOW - 3599)
    cls, _, _ = classify_bridge(text, _KEY, now=_NOW)
    assert cls is Classification.HEALTHY


def test_check4_boundary_just_outside_3601_is_stale():
    text = _mint_text(minted_at=_NOW - 3601)
    cls, _, _ = classify_bridge(text, _KEY, now=_NOW)
    assert cls is Classification.STALE


def test_check5_one_byte_tampered_mac_is_corrupt():
    data = json.loads(_mint_text())
    # flip one hex char of the mac
    mac = list(data["mac"])
    mac[0] = "0" if mac[0] != "0" else "1"
    data["mac"] = "".join(mac)
    cls, _, _ = classify_bridge(json.dumps(data), _KEY, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED


def test_check6_tampered_state_breaks_mac_is_corrupt():
    data = json.loads(_mint_text(pipeline_state="plan"))
    data["pipeline_state"] = "git"  # mac no longer matches
    cls, _, _ = classify_bridge(json.dumps(data), _KEY, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED


def test_check7_wrong_version_is_corrupt():
    data = json.loads(_mint_text())
    data["version"] = 999
    cls, _, _ = classify_bridge(json.dumps(data), _KEY, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED


def test_check8_malformed_json_is_corrupt_and_never_raises():
    cls, marker, age = classify_bridge("{not valid json", _KEY, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED
    assert marker is None and age is None


def test_check8b_missing_field_is_corrupt():
    cls, _, _ = classify_bridge(json.dumps({"version": 1}), _KEY, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED


def test_check9_future_dated_minted_at_is_corrupt():
    text = _mint_text(minted_at=_NOW + 5000)  # negative age
    cls, _, age = classify_bridge(text, _KEY, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED
    assert age == -5000


def test_check10_absent_text_is_absent():
    cls, marker, age = classify_bridge(None, _KEY, now=_NOW)
    assert cls is Classification.ABSENT
    assert marker is None and age is None


def test_check11_key_unavailable_never_healthy():
    text = _mint_text(minted_at=_NOW)  # would be HEALTHY with the key
    cls, marker, _ = classify_bridge(text, None, now=_NOW)
    assert cls is Classification.CORRUPT_OR_TAMPERED
    assert marker is not None  # marker parsed, but MAC uncheckable


def test_next_command_maps_correctly():
    assert "healthy" in next_command(Classification.HEALTHY)
    assert "nothing to recover" in next_command(Classification.ABSENT)
    assert "bridge-reset --confirm-clear" in next_command(Classification.STALE)
    assert "bridge-reset --confirm-clear" in next_command(
        Classification.CORRUPT_OR_TAMPERED
    )


# --------------------------------------------------------------------------
# Fixtures for CLI tests: an injected config_root with a clean agents/ dir
# --------------------------------------------------------------------------


@pytest.fixture
def config_root(tmp_path: Path) -> Path:
    root = tmp_path / ".gleipnir"
    (root / "agents").mkdir(parents=True)
    # a clean roster file (no gleipnir-preflight token)
    (root / "agents" / "orchestrator.md").write_text("clean roster, no token here")
    return root


def _write_bridge(root: Path, text: str) -> Path:
    p = root / BRIDGE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _no_key(monkeypatch):
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)


def _with_real_key(monkeypatch, tmp_path: Path) -> None:
    """Point GLEIPNIR_MARKER_KEY_FILE at a file holding _KEY so the CLI's own
    load_key() succeeds and bridge_status_main can reach HEALTHY/STALE (not just
    the key-unavailable CORRUPT_OR_TAMPERED branch)."""
    key_file = tmp_path / "marker.key"
    key_file.write_bytes(_KEY)
    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(key_file))


import time as _time


def _fresh_text(pipeline_state="plan"):
    """A marker minted at real 'now' so the CLI (which uses time.time()) sees it
    as fresh/HEALTHY."""
    return _mint_text(pipeline_state=pipeline_state, minted_at=int(_time.time()))


def _stale_text(pipeline_state="plan"):
    """A marker minted well past the freshness window relative to real 'now'."""
    return _mint_text(pipeline_state=pipeline_state, minted_at=int(_time.time()) - 4000)


# --------------------------------------------------------------------------
# bridge-status CLI -- Stress-test check 12
# --------------------------------------------------------------------------


def test_check12_status_is_readonly_and_exits_zero(config_root, monkeypatch, capsys):
    _no_key(monkeypatch)
    bridge_path = _write_bridge(config_root, _mint_text(minted_at=_NOW - 4000))
    before = bridge_path.read_text()

    rc = bridge_status_main([], config_root=config_root)

    assert rc == 0
    # file unchanged on disk after a status run
    assert bridge_path.read_text() == before
    err = capsys.readouterr().err
    assert "bridge-status:" in err
    assert "next command" in err


def test_check12b_status_absent_reports_absent(config_root, monkeypatch, capsys):
    _no_key(monkeypatch)
    rc = bridge_status_main([], config_root=config_root)
    assert rc == 0
    assert "absent" in capsys.readouterr().err


def test_check12c_status_healthy_via_cli_with_real_key(
    config_root, monkeypatch, tmp_path, capsys
):
    """Close the reviewer-flagged gap: drive bridge_status_main end-to-end to
    HEALTHY (needs a real key so load_key succeeds; every other CLI status test
    disables the key and can only reach CORRUPT_OR_TAMPERED)."""
    _with_real_key(monkeypatch, tmp_path)
    _write_bridge(config_root, _fresh_text())
    rc = bridge_status_main([], config_root=config_root)
    assert rc == 0
    assert "bridge-status: healthy" in capsys.readouterr().err


def test_check12d_status_stale_via_cli_with_real_key(
    config_root, monkeypatch, tmp_path, capsys
):
    """Drive bridge_status_main end-to-end to STALE with a real key."""
    _with_real_key(monkeypatch, tmp_path)
    _write_bridge(config_root, _stale_text())
    rc = bridge_status_main([], config_root=config_root)
    assert rc == 0
    assert "bridge-status: stale" in capsys.readouterr().err


def test_check11b_status_key_unavailable_note_printed(config_root, monkeypatch, capsys):
    """Close the reviewer-flagged gap for check 11's second half: when the key
    is unavailable but a real marker is present, the status output carries the
    'key unavailable -- cannot verify MAC' note and never claims healthy."""
    _no_key(monkeypatch)
    _write_bridge(config_root, _fresh_text())  # would be healthy WITH the key
    rc = bridge_status_main([], config_root=config_root)
    assert rc == 0
    err = capsys.readouterr().err
    assert "bridge-status: corrupt-or-tampered" in err
    assert "key unavailable" in err
    assert "MAC could NOT be verified" in err
    assert "cannot certify healthy" in err
    # never falsely claims the bridge is healthy without a verified MAC
    assert "bridge-status: healthy" not in err


# --------------------------------------------------------------------------
# bridge-reset CLI -- Stress-test checks 13-19
# --------------------------------------------------------------------------


def test_check13_reset_without_confirm_refuses(config_root, monkeypatch, capsys):
    _no_key(monkeypatch)
    bridge_path = _write_bridge(config_root, _mint_text())

    rc = bridge_reset_main([], config_root=config_root)

    assert rc == 1
    assert bridge_path.exists()  # still present
    # nothing logged
    assert not (config_root / LOG_REL).exists()


def test_check14_reset_confirm_clears_and_logs(config_root, monkeypatch, capsys):
    _no_key(monkeypatch)
    monkeypatch.delenv(OPERATOR_UID_ENV, raising=False)
    bridge_path = _write_bridge(config_root, _mint_text(pipeline_state="plan"))

    rc = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc == 0
    assert not bridge_path.exists()  # deleted
    log_path = config_root / LOG_REL
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "cleared"
    assert entry["old_state"] == "plan"
    assert entry["minted_at"] == _NOW
    assert "timestamp" in entry
    assert "uid" in entry


def test_check15_reset_confirm_absent_is_noop_but_logged(config_root, monkeypatch):
    _no_key(monkeypatch)
    monkeypatch.delenv(OPERATOR_UID_ENV, raising=False)

    rc = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc == 0
    lines = (config_root / LOG_REL).read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["action"] == "no-op"


def test_check16_operator_uid_mismatch_refuses(config_root, monkeypatch):
    import os

    _no_key(monkeypatch)
    monkeypatch.setenv(OPERATOR_UID_ENV, str(os.getuid() + 1))
    bridge_path = _write_bridge(config_root, _mint_text())

    rc = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc == 1
    assert bridge_path.exists()  # nothing cleared


def test_check17_operator_uid_match_proceeds(config_root, monkeypatch):
    import os

    _no_key(monkeypatch)
    monkeypatch.setenv(OPERATOR_UID_ENV, str(os.getuid()))
    bridge_path = _write_bridge(config_root, _mint_text())

    rc = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc == 0
    assert not bridge_path.exists()


def test_check18_operator_uid_unset_warns_but_proceeds(config_root, monkeypatch, capsys):
    _no_key(monkeypatch)
    monkeypatch.delenv(OPERATOR_UID_ENV, raising=False)
    bridge_path = _write_bridge(config_root, _mint_text())

    rc = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc == 0
    assert not bridge_path.exists()
    assert "GLEIPNIR_OPERATOR_UID is not set" in capsys.readouterr().err


def test_check19_operator_uid_non_int_refuses(config_root, monkeypatch):
    _no_key(monkeypatch)
    monkeypatch.setenv(OPERATOR_UID_ENV, "not-an-int")
    bridge_path = _write_bridge(config_root, _mint_text())

    rc = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc == 1
    assert bridge_path.exists()


# --------------------------------------------------------------------------
# Never-in-allowlist guard -- Stress-test checks 20-21
# --------------------------------------------------------------------------


def test_check20_agent_invocable_detected_and_clean_roster_ok(tmp_path: Path):
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "clean.md").write_text("no token here")
    assert preflight_is_agent_invocable(agents) is None

    (agents / "bad.md").write_text("bash: bin/gleipnir-preflight bridge-reset")
    assert preflight_is_agent_invocable(agents) == "bad.md"


def test_check21_both_subcommands_refuse_when_guard_fires(config_root, monkeypatch):
    _no_key(monkeypatch)
    # make the tool appear agent-invocable
    (config_root / "agents" / "leaky.md").write_text(
        "allow bin/gleipnir-preflight for this agent"
    )
    bridge_path = _write_bridge(config_root, _mint_text())

    rc_status = bridge_status_main([], config_root=config_root)
    rc_reset = bridge_reset_main(["--confirm-clear"], config_root=config_root)

    assert rc_status == 1
    assert rc_reset == 1
    # reset did NOT clear the bridge because the guard fired first
    assert bridge_path.exists()


def test_real_roster_has_no_preflight_token():
    """The live roster must never reference the preflight tool (pre-mortem #1
    invariant holds today)."""
    agents_dir = Path(__file__).resolve().parents[1] / ".gleipnir" / "agents"
    if not agents_dir.exists():
        pytest.skip("no .gleipnir/agents in this environment (e.g. sandbox)")
    assert preflight_is_agent_invocable(agents_dir) is None
