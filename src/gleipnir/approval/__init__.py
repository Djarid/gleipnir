"""Gleipnir Tier-3 out-of-band signed-approval subsystem.

Spec: `.gleipnir/plans/tier3-signed-approval.md`. A new sibling subsystem
(alongside `broker/`, `verify/`, `preflight/`, `engine/`) providing:

  * `token.py` -- `mint_approval`/`validate_approval`, reusing the G-3.1
    HMAC discipline (content-bound + identity-bound + freshness-bound at
    `APPROVAL_MAX_AGE_SECONDS = 180`).
  * `identity/` -- the pluggable `IdentityResolver` seam (fail-closed on
    no-match) + the ONE registered `TailscaleResolver` (Route α).
  * `gate.py` -- the fail-closed write-gate `require_valid_token`, plus a
    CLI entry point (`__main__.py`,
    `python -m gleipnir.approval.gate --check <path> --content-file <path>
    --token <file>` -- the CLI hashes `--content-file`'s bytes, the exact
    proposed resulting content, never a fresh read of `--check`'s target;
    Decision 19).
  * `server.py` -- the stdlib `http.server` localhost listener that
    captures an out-of-band approval and mints the token.

stdlib-only: no new Python runtime dependency. `verify/marker.py` and
`preflight/boundary.py` are reused, never modified.

Re-exports the public surface this subsystem's callers need.
"""

from __future__ import annotations

from .gate import GateDecision, GateVerdict, require_valid_token
from .identity import (
    IdentityResolver,
    IdentityUnresolved,
    RequestContext,
    ResolvedIdentity,
    register,
    resolve_identity,
)
from .token import (
    APPROVAL_MAX_AGE_SECONDS,
    APPROVAL_TOKEN_VERSION,
    ApprovalToken,
    ApprovalTokenError,
    mint_approval,
    validate_approval,
)

__all__ = [
    "GateDecision",
    "GateVerdict",
    "require_valid_token",
    "IdentityResolver",
    "IdentityUnresolved",
    "RequestContext",
    "ResolvedIdentity",
    "register",
    "resolve_identity",
    "APPROVAL_MAX_AGE_SECONDS",
    "APPROVAL_TOKEN_VERSION",
    "ApprovalToken",
    "ApprovalTokenError",
    "mint_approval",
    "validate_approval",
]
