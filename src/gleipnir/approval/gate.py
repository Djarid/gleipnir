"""Gleipnir Tier-3 write-gate -- the fail-closed choke-point.

Spec: `.gleipnir/plans/tier3-signed-approval.md` Decision 5/14/19/20, Trace
"The `boundary.decide()` fail-closed pattern this mirrors" + "The
content-binding mechanism -- mint-time vs check-time hash source".
`require_valid_token` is the single choke-point discipline of
`preflight.boundary.decide()` and mirrors `verify/__main__.py:_cmd_check`'s
REFUSE-on-any-doubt shape: missing token, stale token, content-mismatch,
identity-mismatch, wrong version, or an unreadable/malformed token file all
return `GateVerdict.REFUSE` -- never `ALLOW` on any doubt.

**The gate LOGIC lives here; the deterministic BLOCK is wired elsewhere
(Decision 14a).** This module is a library + CLI choke-point
(`python -m gleipnir.approval.gate --check <path> --content-file <path>
--token <file>`, see `__main__.py`); the actual write-blocking hook
(`.gleipnir/plugins/tier3-gate.ts`) that shells out to this CLI and throws
to abort a tool call is a separate Tier-3 artifact (Step 7 of the plan, NOT
built by this module).

**The `--content-file` contract (Decisions 19 + 20 -- the mint-vs-check
hash-source fix).** `require_valid_token` itself is unchanged by this fix --
it always took `change_hash` as an already-computed parameter. What changed
is *where the CLI derives that parameter from*: `__main__.py` now hashes
**`--content-file`'s bytes** -- the exact resulting content a caller (the
`tier3-gate.ts` hook) is about to write -- and passes that hash in as
`change_hash`. `--check <path>` is retained purely as the file
**identifier** (which Tier-3 file is this?) plus the
is-there-a-real-target fail-closed guard; the CLI never re-hashes `--check`'s
live disk bytes. This matters because `tool.execute.before` fires strictly
BEFORE the write lands on disk, so a fresh read of the `--check` target at
check-time would always be the pre-edit/base content -- never the
approved-new content `server.py` minted the token over -- and every
legitimate Tier-3 edit would be wrongly REFUSED (or, worse, "fixed" by
binding the token check to the base content, which is a bait-and-switch
hole that verifies nothing about what actually gets written). See
`__main__.py`'s module docstring and the plan's Trace section for the full
mint-time-vs-check-time byte-string-definition argument.

**Single responsibility (falsifiable, plan Design Principles).** This
module knows NOTHING about how identity was captured or how the token was
transported -- it does not resolve identity itself and does not mint
tokens; it only re-validates one already-minted token against an exact
change + identity. It names no concrete identity provider (T-15).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .token import (
    APPROVAL_MAX_AGE_SECONDS,
    ApprovalToken,
    ApprovalTokenError,
    validate_approval,
)

__all__ = ["GateVerdict", "GateDecision", "require_valid_token"]


class GateVerdict(Enum):
    ALLOW = "allow"
    REFUSE = "refuse"


@dataclass(frozen=True)
class GateDecision:
    """The gate's decision: `ALLOW` only for a fully-valid, fresh,
    content+identity-bound token; `REFUSE` for everything else, with
    human-readable `reasons`."""

    verdict: GateVerdict
    reasons: tuple[str, ...] = ()


def require_valid_token(
    change_hash: str,
    approver_identity: str,
    token_path: str | Path,
    key: bytes,
    *,
    max_age_seconds: int = APPROVAL_MAX_AGE_SECONDS,
    now: int | None = None,
) -> GateDecision:
    """Fail-closed re-validation choke-point for a Tier-3 write.

    Reads the token at `token_path`, and returns `GateVerdict.REFUSE` on
    ANY of: a missing token file, a malformed/unparseable token, or a token
    that fails `validate_approval` against the exact `change_hash` +
    `approver_identity` given (wrong version, content-mismatch,
    identity-mismatch, unforgeability failure, or staleness). Only a fully
    valid, fresh, content+identity-bound token returns `GateVerdict.ALLOW`.

    Mirrors `verify/__main__.py:_cmd_check` (missing marker => fail-closed)
    and `preflight/boundary.decide()` (REFUSE-on-any-doubt, never
    "assume fine")."""

    path = Path(token_path)
    if not path.is_file():
        return GateDecision(
            GateVerdict.REFUSE,
            (f"no approval token present at {path}; write refused",),
        )

    try:
        token: ApprovalToken = ApprovalToken.from_json(path.read_text())
    except ApprovalTokenError as exc:
        return GateDecision(
            GateVerdict.REFUSE, (f"token unreadable/malformed: {exc}",)
        )

    if validate_approval(
        token,
        change_hash,
        approver_identity,
        key,
        max_age_seconds=max_age_seconds,
        now=now,
    ):
        return GateDecision(GateVerdict.ALLOW, ())

    return GateDecision(
        GateVerdict.REFUSE,
        (
            "token invalid, stale, content-mismatched, or "
            "identity-mismatched -- refusing (fail-closed)",
        ),
    )


if __name__ == "__main__":
    # Literal invocation the plan (Decision 14/19) and the future
    # `.gleipnir/plugins/tier3-gate.ts` hook (Decision 14a, Step 7 -- NOT
    # built by this module) both name exactly:
    #     python -m gleipnir.approval.gate --check <path> --content-file <path> --token <file>
    # The argparse CLI logic itself lives in `__main__.py` per the Trace
    # module table; this guard delegates to it so that literal command works.
    from .__main__ import main

    raise SystemExit(main())
