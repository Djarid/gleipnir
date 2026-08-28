"""Pluggable identity-resolution seam (the reuse seam, plan Decision 2/13).

Re-exports the public surface a caller (`approval/server.py`) and a resolver
author both need: the `IdentityResolver` protocol, `ResolvedIdentity` and
`RequestContext` dataclasses, `IdentityUnresolved`, and the dispatcher's
`register`/`resolve_identity` functions. Stdlib-only.

Two modules:
    protocol.py  -- `IdentityResolver` protocol + `ResolvedIdentity` +
                     `RequestContext`; no provider-specific logic.
    registry.py  -- `register()`/`resolve_identity()`; no provider-specific
                     logic; FAIL-CLOSED (raises `IdentityUnresolved`) on
                     no-match -- the deliberate inversion of
                     `content_handlers`'s benign passthrough.

The ONE resolver registered today, `TailscaleResolver`
(`tailscale_resolver.py`), is intentionally NOT re-exported here and NOT
imported by this package's `__init__` -- it is composed (registered) only at
`approval/server.py`'s composition root, so this seam names no concrete
provider (T-15).

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Decision 2/13, Assemble
Step 2.
"""

from __future__ import annotations

from .protocol import IdentityResolver, RequestContext, ResolvedIdentity
from .registry import IdentityUnresolved, register, resolve_identity

__all__ = [
    "IdentityResolver",
    "RequestContext",
    "ResolvedIdentity",
    "IdentityUnresolved",
    "register",
    "resolve_identity",
]
