"""Generic identity-resolver registry/dispatcher -- FAIL-CLOSED on no-match.

**Single responsibility (falsifiable, plan Design Principles).** Given a
`RequestContext`, select the first registered resolver whose `can_resolve`
is True and return its `resolve(request_ctx)` result; otherwise **raise**
`IdentityUnresolved`. This module contains **no** reference to any
particular identity provider -- no concrete provider name appears anywhere
in its source (see `tests/test_approval_identity_resolver.py
::TestSingleResponsibility`, mirroring
`tests/test_broker_git_content_handlers.py::TestRegistrySingleResponsibility`)
and imports **no** concrete resolver module.

**Open/closed (the extensibility test, T-14).** Adding a new resolver never
requires editing this module -- only a call to `register(...)` from wherever
the new resolver is composed (the caller's composition root, e.g.
`approval/server.py`).

**THE DELIBERATE INVERSION vs `content_handlers/registry.py` (plan Decision
13).** `content_handlers.dispatch` returns content UNCHANGED on no-match --
a benign passthrough, safe because "leave the content alone" has no security
consequence. An identity dispatcher's no-match case is the opposite: there is
no safe default identity, so `resolve_identity` **raises**
`IdentityUnresolved` instead of returning anything -- never defaulting to an
unauthenticated identity (T-13). Same open/closed register/dispatch shape as
`content_handlers/registry.py`, deliberately opposite no-match branch.

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Decision 13, Assemble
Step 2, Stress-test T-13/T-14/T-15.
"""

from __future__ import annotations

from typing import List

from .protocol import IdentityResolver, RequestContext, ResolvedIdentity


class IdentityUnresolved(Exception):
    """Raised when no registered `IdentityResolver` can resolve a
    `RequestContext`. FAIL-CLOSED: the caller (the approval server) must
    reject the approval, never mint a token for an unauthenticated
    identity."""


# Module-level registry: ordered list of registered resolvers. First
# registered, first matched -- `resolve_identity` walks this list in order
# and returns the first resolver whose `can_resolve` is True.
_resolvers: List[IdentityResolver] = []


def register(resolver: IdentityResolver) -> None:
    """Register `resolver`. Order matters: earlier registrations are tried
    first in `resolve_identity`."""
    _resolvers.append(resolver)


def resolve_identity(request_ctx: RequestContext) -> ResolvedIdentity:
    """Return the first matching resolver's resolved identity.

    Walks the registered resolvers in registration order; the first whose
    `can_resolve(request_ctx)` is True wins. If no resolver matches (or none
    is registered), this RAISES `IdentityUnresolved` -- the deliberate
    inversion of `content_handlers.dispatch`'s unchanged-passthrough
    fallback. There is no unauthenticated-identity fallback value."""

    for resolver in _resolvers:
        if resolver.can_resolve(request_ctx):
            return resolver.resolve(request_ctx)
    raise IdentityUnresolved(
        "no registered IdentityResolver could resolve this request -- "
        "refusing rather than defaulting to an unauthenticated identity"
    )
