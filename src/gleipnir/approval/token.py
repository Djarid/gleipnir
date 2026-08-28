"""Gleipnir Tier-3 approval token -- reuses the G-3.1 HMAC discipline.

Spec: `.gleipnir/plans/tier3-signed-approval.md` Decision 3/11/12, Trace
"The G-3.1 primitives this reuses". A Tier-3 write's authority must rest on
a fresh, content-bound, identity-bound, HMAC-signed token minted only by an
out-of-band authenticated approval event -- not a session's self-report.

**Reuse, not modify, `verify/marker.py`.** This module mirrors
`verify.marker`'s `mint`/`validate`/`_canonical_signing_input` shape exactly
(length-prefixed `\\x1f`-joined canonical input, `hmac.new(...).hexdigest()`,
`hmac.compare_digest` for the mac AND every bound field) and imports its
`DIGEST` constant for genuine reuse of the digest choice -- but does NOT
import or call `mint`/`validate`/`Marker` themselves, because identity is a
first-class token field here, not smuggled into a `Marker`'s `tree_hash`
(Decision 11). `verify/marker.py` is never edited.

**Single responsibility (falsifiable, plan Design Principles).** This
module knows NOTHING about identity resolution or the network: it contains
no reference to how an approver's identity was captured, and does not
import the resolver registry or `http.server`. It also names no concrete
identity provider (T-15): a source-scan for any concrete provider name
finds none.
"""

from __future__ import annotations

import hmac
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

from ..verify.marker import DIGEST

# Named constants (plan Decision 12): never a magic literal.
APPROVAL_TOKEN_VERSION = 1
# The operator-converged 3-minute freshness window (plan brief + Decision 4).
# Distinct from `verify.marker.DEFAULT_MAX_AGE_SECONDS` (3600s) -- that
# window is for the G-3.1 test-skip marker, not this approval token.
APPROVAL_MAX_AGE_SECONDS = 180


class ApprovalTokenError(Exception):
    """Base for all approval-token faults. All faults are fail-closed: a
    malformed/unparseable token never validates."""


@dataclass(frozen=True)
class ApprovalToken:
    """A signed out-of-band approval token.

    `change_hash` binds the token to the exact pending Tier-3 content;
    `approver_identity` + `provider` bind it to the out-of-band-authenticated
    approver; `mac` is HMAC(key, canonical(version, change_hash,
    approver_identity, provider, minted_at)). Because the MAC covers every
    other field, the tuple is inseparable: you cannot lift the mac onto a
    different change, a different approver, or a different provider, and you
    cannot produce a mac at all without the key.
    """

    version: int
    change_hash: str
    approver_identity: str
    provider: str
    minted_at: int
    mac: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @staticmethod
    def from_json(text: str) -> "ApprovalToken":
        try:
            data: dict[str, Any] = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise ApprovalTokenError(f"token is not valid JSON: {exc}") from exc
        try:
            return ApprovalToken(
                version=int(data["version"]),
                change_hash=str(data["change_hash"]),
                approver_identity=str(data["approver_identity"]),
                provider=str(data["provider"]),
                minted_at=int(data["minted_at"]),
                mac=str(data["mac"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ApprovalTokenError(
                f"token is missing/invalid fields: {exc}"
            ) from exc


def _canonical_signing_input(
    version: int,
    change_hash: str,
    approver_identity: str,
    provider: str,
    minted_at: int,
) -> bytes:
    """The exact bytes the MAC covers. Stable and unambiguous.

    Fields are length-prefixed (via the `\\x1f` separator) so no field
    boundary can be shifted by choosing clever field contents -- the same
    discipline as `verify.marker._canonical_signing_input`, extended with
    the two extra identity-binding fields."""

    parts = [str(version), change_hash, approver_identity, provider, str(minted_at)]
    return b"\x1f".join(p.encode("utf-8") for p in parts)


def mint_approval(
    change_hash: str,
    approver_identity: str,
    provider: str,
    key: bytes,
    minted_at: int | None = None,
) -> ApprovalToken:
    """Produce a signed approval token.

    Requires the key -- the same G-3.1 `GLEIPNIR_MARKER_KEY_FILE` key, read
    by the caller (never by this function, which takes `key` as bytes) via
    `verify.marker.load_key`. Calling this is the act of the out-of-band
    approval server certifying the exact content + identity it captured.
    """

    ts = int(minted_at if minted_at is not None else time.time())
    signing_input = _canonical_signing_input(
        APPROVAL_TOKEN_VERSION, change_hash, approver_identity, provider, ts
    )
    mac = hmac.new(key, signing_input, DIGEST).hexdigest()
    return ApprovalToken(
        version=APPROVAL_TOKEN_VERSION,
        change_hash=change_hash,
        approver_identity=approver_identity,
        provider=provider,
        minted_at=ts,
        mac=mac,
    )


def validate_approval(
    token: ApprovalToken,
    change_hash: str,
    approver_identity: str,
    key: bytes,
    max_age_seconds: int = APPROVAL_MAX_AGE_SECONDS,
    now: int | None = None,
) -> bool:
    """Validate a token against the exact change + identity. Fail-closed on
    any doubt.

    Returns True only if:
      * the version matches,
      * the token's `change_hash` equals the given `change_hash`
        (content-binding),
      * the token's `approver_identity` equals the given `approver_identity`
        (identity-binding),
      * the HMAC verifies under the key (constant-time, unforgeability), and
      * the token is fresh (age in `[0, max_age_seconds]`).

    Any failure returns False -- this never raises for a merely-invalid
    token; it mirrors `verify.marker.validate`'s discipline exactly, extended
    with the identity-binding check.
    """

    if token.version != APPROVAL_TOKEN_VERSION:
        return False

    # Content-binding: the approved content must be the content in front of
    # us now.
    if not hmac.compare_digest(token.change_hash, change_hash):
        return False

    # Identity-binding: the approved identity must be the identity we expect.
    if not hmac.compare_digest(token.approver_identity, approver_identity):
        return False

    # Unforgeability: recompute the MAC and compare in constant time.
    expected = hmac.new(
        key,
        _canonical_signing_input(
            token.version,
            token.change_hash,
            token.approver_identity,
            token.provider,
            token.minted_at,
        ),
        DIGEST,
    ).hexdigest()
    if not hmac.compare_digest(token.mac, expected):
        return False

    # Freshness (the 180s window, or an explicit override).
    current = int(now if now is not None else time.time())
    age = current - token.minted_at
    if age < 0 or age > max_age_seconds:
        return False

    return True
