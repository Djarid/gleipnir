"""End-to-end tests for the G-3.1 verifier CLI (the verifier process)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gleipnir.verify.__main__ import main


VERIFIER_KEY = b"verifier-only-secret-key"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("assert True\n")
    kf = tmp_path / "key"
    kf.write_bytes(VERIFIER_KEY)
    return tmp_path


def _args(project: Path, *rest: str) -> list[str]:
    return [
        "--key-file",
        str(project / "key"),
        "--root",
        str(project),
        "--marker",
        str(project / ".tmp" / "marker.json"),
        *rest,
    ]


def test_verify_green_mints_then_check_passes(project: Path):
    # green test command
    rc = main(_args(project, "verify", "--", "true"))
    assert rc == 0
    assert (project / ".tmp" / "marker.json").is_file()

    rc = main(_args(project, "check"))
    assert rc == 0


def test_verify_red_mints_nothing(project: Path):
    rc = main(_args(project, "verify", "--", "false"))
    assert rc != 0
    assert not (project / ".tmp" / "marker.json").exists()


def test_check_missing_marker_fails_closed(project: Path):
    rc = main(_args(project, "check"))
    assert rc == 1


def test_check_fails_after_tree_mutation(project: Path):
    assert main(_args(project, "verify", "--", "true")) == 0
    assert main(_args(project, "check")) == 0
    # mutate one byte
    src = project / "src" / "a.py"
    src.write_text(src.read_text() + "\n")
    assert main(_args(project, "check")) == 1


def test_check_fails_with_wrong_key(project: Path):
    assert main(_args(project, "verify", "--", "true")) == 0
    wrong = project / "wrongkey"
    wrong.write_bytes(b"not-the-verifier-key")
    rc = main(
        [
            "--key-file",
            str(wrong),
            "--root",
            str(project),
            "--marker",
            str(project / ".tmp" / "marker.json"),
            "check",
        ]
    )
    assert rc == 1
