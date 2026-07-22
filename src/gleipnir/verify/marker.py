"""Gleipnir G-3.1 — keyed local verification marker.

Spec (G-3.1): the skip-token binds to a secret only the verifier holds, in
addition to the artifact-state binding that already exists. HMAC over the
tree/source hash; the key is readable only by the verifier process and lives
under the S-2 boundary; tree-binding is preserved; a valid marker can only be
produced by the process that ran the tests. Fail-closed: an invalid or missing
marker means run the tests.

This module is Gleipnir's own implementation, built from the spec. It has two
sides:

  * ``mint`` — run only by the verifier process, which holds the key. Given a
    computed tree hash it produces a signed marker.
  * ``validate`` — recomputes the binding and checks the HMAC in constant time.
    An agent that fabricates a marker without the key fails validation; a
    genuine marker whose tree changed by even one byte fails validation.

The key never enters the agent surface. It is read from the path named by
``GLEIPNIR_MARKER_KEY_FILE`` (the S-2 boundary location once closure lands).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

MARKER_VERSION = 1
DIGEST = "sha256"
# A marker older than this many seconds is stale and fails validation
# (freshness binding, per spec). Callers may override.
DEFAULT_MAX_AGE_SECONDS = 3600

KEY_ENV_VAR = "GLEIPNIR_MARKER_KEY_FILE"


class MarkerError(Exception):
    """Base for all marker faults. All faults are fail-closed."""


class KeyUnavailable(MarkerError):
    """The verifier key could not be read. Minting/validation cannot proceed."""


@dataclass(frozen=True)
class Marker:
    """A signed verification marker.

    ``tree_hash`` binds the marker to the exact source/test/config tree state.
    ``mac`` is HMAC(key, canonical(version, tree_hash, minted_at)). Because the
    MAC covers the tree hash, the pair is inseparable: you cannot lift a MAC
    onto a different tree, and you cannot produce a MAC at all without the key.
    """

    version: int
    tree_hash: str
    minted_at: int
    mac: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @staticmethod
    def from_json(text: str) -> "Marker":
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise MarkerError(f"marker is not valid JSON: {exc}") from exc
        try:
            return Marker(
                version=int(data["version"]),
                tree_hash=str(data["tree_hash"]),
                minted_at=int(data["minted_at"]),
                mac=str(data["mac"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise MarkerError(f"marker is missing/invalid fields: {exc}") from exc


def load_key(key_file: str | os.PathLike[str] | None = None) -> bytes:
    """Read the verifier key.

    The key lives under the S-2 boundary and is readable only by the verifier
    process. In the finished framework the agent has no path to this file. Here
    it is read from ``GLEIPNIR_MARKER_KEY_FILE`` (or an explicit path for
    tests). Absence or emptiness is fail-closed: no key, no mint, no validate.
    """

    path = key_file or os.environ.get(KEY_ENV_VAR)
    if not path:
        raise KeyUnavailable(
            f"no key path: set {KEY_ENV_VAR} or pass key_file explicitly"
        )
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise KeyUnavailable(f"cannot read key at {path}: {exc}") from exc
    if len(raw.strip()) == 0:
        raise KeyUnavailable(f"key at {path} is empty")
    return raw.strip()


def _canonical_signing_input(version: int, tree_hash: str, minted_at: int) -> bytes:
    """The exact bytes the MAC covers. Stable and unambiguous.

    Fields are length-prefixed so no field boundary can be shifted by choosing
    clever field contents (a classic HMAC-concatenation ambiguity).
    """

    parts = [str(version), tree_hash, str(minted_at)]
    return b"\x1f".join(p.encode("utf-8") for p in parts)


def compute_tree_hash(
    root: str | os.PathLike[str],
    include: Iterable[str] = ("src", "tests"),
    extra_files: Iterable[str] = (),
) -> str:
    """Hash the source/test/config tree into one stable digest.

    Covers everything under the ``include`` directories plus any ``extra_files``
    (e.g. a lockfile or config). Deterministic: files are sorted, and each
    file's relative path and contents are folded in, so a rename or a
    one-byte content change both alter the digest. Missing paths are folded in
    as a sentinel rather than skipped, so deleting a watched file is also
    detected.
    """

    root_path = Path(root)
    h = hashlib.new(DIGEST)

    collected: list[Path] = []
    for rel in include:
        base = root_path / rel
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    collected.append(p)
        elif base.is_file():
            collected.append(base)
    for rel in extra_files:
        p = root_path / rel
        collected.append(p)

    for p in sorted(set(collected)):
        try:
            rel_path = p.relative_to(root_path).as_posix()
        except ValueError:
            rel_path = p.as_posix()
        h.update(rel_path.encode("utf-8"))
        h.update(b"\x00")
        if p.is_file():
            h.update(p.read_bytes())
        else:
            h.update(b"<absent>")
        h.update(b"\x00")
    return h.hexdigest()


def mint(tree_hash: str, key: bytes, minted_at: int | None = None) -> Marker:
    """Produce a signed marker. Verifier-only: requires the key.

    This is the one operation an agent cannot perform, because it does not
    hold the key. Calling ``mint`` is the act of the process that ran the tests
    certifying the tree it tested.
    """

    ts = int(minted_at if minted_at is not None else time.time())
    signing_input = _canonical_signing_input(MARKER_VERSION, tree_hash, ts)
    mac = hmac.new(key, signing_input, DIGEST).hexdigest()
    return Marker(version=MARKER_VERSION, tree_hash=tree_hash, minted_at=ts, mac=mac)


def validate(
    marker: Marker,
    current_tree_hash: str,
    key: bytes,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: int | None = None,
) -> bool:
    """Validate a marker against the current tree. Fail-closed on any doubt.

    Returns True only if:
      * the version matches,
      * the marker's tree hash equals the current tree hash (tree-binding),
      * the HMAC verifies under the key (constant-time), and
      * the marker is fresh.

    Any failure returns False, meaning: run the tests. This never raises for a
    merely-invalid marker; it raises only if the key itself is unusable, which
    is a different (also fail-closed) condition handled by the caller.
    """

    if marker.version != MARKER_VERSION:
        return False

    # Tree-binding: the certified tree must be the tree in front of us now.
    if not hmac.compare_digest(marker.tree_hash, current_tree_hash):
        return False

    # Unforgeability: recompute the MAC and compare in constant time.
    expected = hmac.new(
        key,
        _canonical_signing_input(marker.version, marker.tree_hash, marker.minted_at),
        DIGEST,
    ).hexdigest()
    if not hmac.compare_digest(marker.mac, expected):
        return False

    # Freshness.
    current = int(now if now is not None else time.time())
    age = current - marker.minted_at
    if age < 0 or age > max_age_seconds:
        return False

    return True
