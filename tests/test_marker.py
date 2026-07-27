"""G-3.1 conformance and unit tests for the keyed verification marker.

Spec conformance [D], G-3.1:
  * Have an agent mint a marker by every means available to it, then push:
    tests must run every time.  -> an agent without the key cannot produce a
    marker that validates.
  * Verifier produces a genuine marker, mutate one tree byte, push: tests must
    run.  -> a one-byte tree change invalidates a genuine marker.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from gleipnir.verify import (
    KeyUnavailable,
    Marker,
    compute_tree_hash,
    load_key,
    mint,
    validate,
)


VERIFIER_KEY = b"verifier-only-secret-key-not-on-agent-surface"
AGENT_GUESSED_KEY = b"agent-guessed-key"


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("print('hello')\n")
    (src / "b.py").write_text("x = 1\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_a.py").write_text("def test_ok():\n    assert True\n")
    return tmp_path


def _key_file(tmp_path: Path, contents: bytes = VERIFIER_KEY) -> Path:
    kf = tmp_path / "key"
    kf.write_bytes(contents)
    return kf


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------

def test_genuine_marker_validates(tree: Path):
    th = compute_tree_hash(tree)
    m = mint(th, VERIFIER_KEY)
    assert validate(m, compute_tree_hash(tree), VERIFIER_KEY) is True


def test_marker_roundtrips_through_json(tree: Path):
    th = compute_tree_hash(tree)
    m = mint(th, VERIFIER_KEY)
    m2 = Marker.from_json(m.to_json())
    assert m2 == m
    assert validate(m2, th, VERIFIER_KEY) is True


# --------------------------------------------------------------------------
# G-3.1 conformance: an agent cannot forge a marker (no key)
# --------------------------------------------------------------------------

def test_agent_fabricated_marker_fails(tree: Path):
    """Agent writes a plausible-looking marker JSON by hand. No key => no valid
    MAC => validation fails => tests run."""
    th = compute_tree_hash(tree)
    forged = Marker(
        version=1,
        tree_hash=th,
        minted_at=int(time.time()),
        mac="deadbeef" * 8,  # agent's guess at a MAC
    )
    assert validate(forged, th, VERIFIER_KEY) is False


def test_agent_mints_with_wrong_key_fails(tree: Path):
    """Agent has the code and mints with a key it guessed/holds. Wrong key =>
    MAC won't verify under the verifier key => fails."""
    th = compute_tree_hash(tree)
    agent_marker = mint(th, AGENT_GUESSED_KEY)
    assert validate(agent_marker, th, VERIFIER_KEY) is False


def test_agent_copies_mac_onto_different_tree_fails(tree: Path):
    """Agent lifts a genuine MAC and pastes it onto a marker claiming a
    different tree hash. MAC covers the tree hash, so it won't verify."""
    th = compute_tree_hash(tree)
    genuine = mint(th, VERIFIER_KEY)
    tampered = Marker(
        version=genuine.version,
        tree_hash="0" * 64,  # claim a different tree
        minted_at=genuine.minted_at,
        mac=genuine.mac,  # but reuse the genuine MAC
    )
    assert validate(tampered, "0" * 64, VERIFIER_KEY) is False


# --------------------------------------------------------------------------
# G-3.1 conformance: one-byte tree mutation invalidates a genuine marker
# --------------------------------------------------------------------------

def test_one_byte_mutation_invalidates(tree: Path):
    th = compute_tree_hash(tree)
    genuine = mint(th, VERIFIER_KEY)
    # mutate exactly one byte of one source file
    target = tree / "src" / "a.py"
    data = target.read_text()
    target.write_text(data[:-1] + "!")  # change trailing char
    new_th = compute_tree_hash(tree)
    assert new_th != th
    assert validate(genuine, new_th, VERIFIER_KEY) is False


def test_added_file_invalidates(tree: Path):
    th = compute_tree_hash(tree)
    genuine = mint(th, VERIFIER_KEY)
    (tree / "src" / "c.py").write_text("y = 2\n")
    assert validate(genuine, compute_tree_hash(tree), VERIFIER_KEY) is False


def test_deleted_file_invalidates(tree: Path):
    th = compute_tree_hash(tree, extra_files=("src/a.py",))
    genuine = mint(th, VERIFIER_KEY)
    (tree / "src" / "a.py").unlink()
    new_th = compute_tree_hash(tree, extra_files=("src/a.py",))
    assert new_th != th
    assert validate(genuine, new_th, VERIFIER_KEY) is False


# --------------------------------------------------------------------------
# Freshness and version binding
# --------------------------------------------------------------------------

def test_stale_marker_fails(tree: Path):
    th = compute_tree_hash(tree)
    old = mint(th, VERIFIER_KEY, minted_at=1000)
    assert validate(old, th, VERIFIER_KEY, max_age_seconds=3600, now=1_000_000) is False


def test_future_marker_fails(tree: Path):
    th = compute_tree_hash(tree)
    future = mint(th, VERIFIER_KEY, minted_at=2_000_000)
    assert validate(future, th, VERIFIER_KEY, now=1_000_000) is False


def test_wrong_version_fails(tree: Path):
    th = compute_tree_hash(tree)
    m = mint(th, VERIFIER_KEY)
    bad = Marker(version=99, tree_hash=m.tree_hash, minted_at=m.minted_at, mac=m.mac)
    assert validate(bad, th, VERIFIER_KEY) is False


# --------------------------------------------------------------------------
# Key handling is fail-closed
# --------------------------------------------------------------------------

def test_missing_key_path_raises(monkeypatch):
    monkeypatch.delenv("GLEIPNIR_MARKER_KEY_FILE", raising=False)
    with pytest.raises(KeyUnavailable):
        load_key()


def test_empty_key_raises(tmp_path: Path):
    kf = _key_file(tmp_path, contents=b"   \n")
    with pytest.raises(KeyUnavailable):
        load_key(kf)


def test_key_loaded_from_env(tmp_path: Path, monkeypatch):
    kf = _key_file(tmp_path)
    monkeypatch.setenv("GLEIPNIR_MARKER_KEY_FILE", str(kf))
    assert load_key() == VERIFIER_KEY


def test_malformed_marker_json_raises():
    from gleipnir.verify import MarkerError

    with pytest.raises(MarkerError):
        Marker.from_json("{not json")


# ---------------------------------------------------------------------------
# DEBT: cover the remaining fail-closed / edge branches in marker.py
# ---------------------------------------------------------------------------

def test_marker_from_json_missing_fields_raises():
    """Valid JSON but missing required fields -> MarkerError (not KeyError)."""
    from gleipnir.verify import MarkerError

    with pytest.raises(MarkerError):
        Marker.from_json('{"version": 1}')  # missing tree_hash/minted_at/mac


def test_load_key_unreadable_path_raises(tmp_path: Path):
    """A key path that exists as a directory (unreadable as bytes) -> OSError
    -> KeyUnavailable (fail-closed), not a raw OSError."""
    from gleipnir.verify import KeyUnavailable

    d = tmp_path / "not-a-key-file"
    d.mkdir()
    with pytest.raises(KeyUnavailable):
        load_key(d)


def test_compute_tree_hash_include_is_a_file(tmp_path: Path):
    """An `include` entry that is a file (not a dir) is folded in directly."""
    (tmp_path / "solo.py").write_text("x = 1\n")
    h = compute_tree_hash(tmp_path, include=("solo.py",))
    assert isinstance(h, str) and len(h) == 64  # sha256 hex


def test_compute_tree_hash_extra_file_outside_root(tmp_path: Path):
    """An extra_file resolving outside the root uses the as_posix() fallback
    (the relative_to ValueError branch) rather than crashing."""
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("data\n")
    try:
        h = compute_tree_hash(tmp_path, include=(), extra_files=("../outside.txt",))
        assert isinstance(h, str) and len(h) == 64
    finally:
        outside.unlink()
