"""Identity-resolver contract: `IdentityResolver` Protocol + `ResolvedIdentity`
+ `RequestContext`.

The generic, reusable half of the pluggable identity-resolution seam (the
other half is `registry.py`'s dispatcher). Mirrors
`src/gleipnir/broker/git/content_handlers/protocol.py` structurally (a
`@runtime_checkable Protocol` + a frozen result dataclass), but see the
inverted no-match posture documented in `registry.py` -- that inversion is
the dispatcher's concern, not this contract's.

**Structural safety by construction (plan Decision 13 / Architect item 6,
Stress-test T-12).** `ResolvedIdentity` carries exactly `{identity, provider}`
-- no `mac`, `token`, `change_hash`, or `key` field exists on this type, so a
resolver CANNOT reach any token/gate internal, not because of a convention
but because the contract does not offer a path to it. `RequestContext`
carries only the raw request facts a resolver needs (`remote_ip`, `headers`)
-- nothing token/gate-reachable either. See
`tests/test_approval_identity_resolver.py::TestStructuralSafety` (a
type/structural test via `inspect.signature`/`dataclasses.fields`, not
merely behavioural), mirroring
`tests/test_broker_git_content_handlers.py::TestStructuralSafety`.

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Decision 13, Assemble
Step 2, Stress-test T-12.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class RequestContext:
    """The raw request facts a resolver needs to decide/resolve an identity.

    Carries ONLY request facts -- no token/gate/key/change_hash field is
    reachable through this type, by construction."""

    remote_ip: str
    headers: Mapping[str, str]


@dataclass(frozen=True)
class ResolvedIdentity:
    """Exactly the identity + provider a resolver asserts, and nothing else.

    No `mac`, `token`, `change_hash`, or `key` field exists on this type --
    structurally unreachable, not just omitted by convention (T-12)."""

    identity: str
    provider: str


@runtime_checkable
class IdentityResolver(Protocol):
    """Minimal identity-resolution contract: exactly two methods.

    `can_resolve(request_ctx)` decides whether this resolver applies;
    `resolve(request_ctx)` performs the resolution. Neither method receives
    or can return anything beyond a `RequestContext`/`ResolvedIdentity` --
    the token, the gate, and the HMAC key are all structurally unreachable
    through this protocol.
    """

    def can_resolve(self, request_ctx: RequestContext) -> bool:
        """Return True if this resolver should attempt `request_ctx`."""
        ...

    def resolve(self, request_ctx: RequestContext) -> ResolvedIdentity:
        """Resolve `request_ctx` to an identity. May raise on failure --
        fail-closed; callers must never substitute a default identity."""
        ...
