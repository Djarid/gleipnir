"""Coverage for the G-3.1 verifier CLI error branches (verify/__main__.py).

test_cli.py already covers the happy paths (green -> mint -> check passes, red
mints nothing, tree mutation invalidates, wrong key). This file closes the
fail-closed ERROR branches that were previously uncovered: no command, key
unavailable (both subcommands), and a malformed marker file. Driven through
``main([...])`` so the argparse wiring is exercised too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gleipnir.verify.__main__ import main


KEY = b"verifier-only-secret"


def _key_file(tmp_path: Path) -> Path:
    kf = tmp_path / "key"
    kf.write_bytes(KEY)
    return kf


# ---------------------------------------------------------------------------
# verify: no command, and key unavailable
# ---------------------------------------------------------------------------

def test_verify_with_no_command_exits_2(tmp_path: Path):
    # `verify` with an empty command list -> "no test command given" -> exit 2
    rc = main(
        [
            "--key-file",
            str(_key_file(tmp_path)),
            "--root",
            str(tmp_path),
            "--marker",
            str(tmp_path / "m.json"),
            "verify",
        ]
    )
    assert rc == 2


def test_verify_with_no_key_exits_3(tmp_path: Path, monkeypatch):
    # No key path anywhere -> KeyUnavailable -> exit 3, fail-closed, no marker.
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    marker = tmp_path / "m.json"
    rc = main(
        [
            "--root",
            str(tmp_path),
            "--marker",
            str(marker),
            "verify",
            "--",
            "true",
        ]
    )
    assert rc == 3
    assert not marker.exists()


# ---------------------------------------------------------------------------
# check: missing marker, key unavailable, malformed marker
# ---------------------------------------------------------------------------

def test_check_missing_marker_exits_1(tmp_path: Path):
    rc = main(
        [
            "--key-file",
            str(_key_file(tmp_path)),
            "--root",
            str(tmp_path),
            "--marker",
            str(tmp_path / "absent.json"),
            "check",
        ]
    )
    assert rc == 1


def test_check_with_no_key_exits_3(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    marker = tmp_path / "m.json"
    marker.write_text('{"version":1,"tree_hash":"x","minted_at":0,"mac":"y"}')
    rc = main(
        [
            "--root",
            str(tmp_path),
            "--marker",
            str(marker),
            "check",
        ]
    )
    assert rc == 3


def test_check_malformed_marker_exits_1(tmp_path: Path):
    marker = tmp_path / "m.json"
    marker.write_text("{ this is not valid json")
    rc = main(
        [
            "--key-file",
            str(_key_file(tmp_path)),
            "--root",
            str(tmp_path),
            "--marker",
            str(marker),
            "check",
        ]
    )
    assert rc == 1
