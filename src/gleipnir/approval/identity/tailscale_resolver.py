"""`TailscaleResolver` -- the ONE registered `IdentityResolver` (Route α).

Spec: `.gleipnir/plans/tier3-signed-approval.md` Decision 1/16, Trace
"The resolver seam contract/dispatcher", Stress-test T-18. Resolves a
tailnet identity via the already-deployed Tailscale infrastructure by
shelling out to the locally-installed `tailscale` CLI's `whois --json`
subcommand -- **stdlib `subprocess` only, no new Python dependency**. The
`tailscale` CLI itself is a system-side environmental prerequisite (an
operator hand-off), not a Python package (plan L8).

**Fail-closed everywhere.** Any subprocess spawn error, non-zero exit,
unparseable JSON, or missing/empty login field means `can_resolve` returns
False and `resolve` raises `TailscaleResolutionError` -- NEVER a default
identity (Edge case 8).

**Registered only at the composition root** (`approval/server.py`), never
inside `identity/registry.py` -- the dispatcher must import no concrete
resolver (T-15). This module MAY (and does) reference "tailscale"; that is
the point of this module, in contrast to `registry.py`/`gate.py`/`token.py`,
which must not.
"""

from __future__ import annotations

import json
import subprocess
from typing import Callable

from .protocol import RequestContext, ResolvedIdentity

PROVIDER = "tailscale"

# `tailscale whois` is a local LocalAPI round-trip; a few seconds is ample
# and bounds a hung/misbehaving CLI from blocking the listener indefinitely.
DEFAULT_WHOIS_TIMEOUT_SECONDS = 5.0


class TailscaleResolutionError(Exception):
    """Any failure resolving a tailnet identity. Fail-closed: raised, never
    swallowed into a default identity."""


class TailscaleResolver:
    """Route α: resolve a tailnet identity via `tailscale whois --json`.

    `subprocess.run` is injectable (the `run` constructor parameter) so
    tests can supply a fake without invoking a real `tailscale` CLI --
    mirroring `preflight.boundary`'s injectable thin-edge pattern and this
    plan's own "the subprocess/network edges are injectable so tests use
    fakes" note (Assemble Step 5).
    """

    def __init__(
        self,
        *,
        run: Callable[..., "subprocess.CompletedProcess[str]"] = subprocess.run,
        timeout: float = DEFAULT_WHOIS_TIMEOUT_SECONDS,
    ) -> None:
        self._run = run
        self._timeout = timeout

    def can_resolve(self, request_ctx: RequestContext) -> bool:
        try:
            self._whois_login(request_ctx.remote_ip)
        except TailscaleResolutionError:
            return False
        return True

    def resolve(self, request_ctx: RequestContext) -> ResolvedIdentity:
        login = self._whois_login(request_ctx.remote_ip)
        return ResolvedIdentity(identity=login, provider=PROVIDER)

    def _whois_login(self, remote_ip: str) -> str:
        """Invoke `tailscale whois --json <remote_ip>` and parse the login.

        Stress-test T-18: the exact invocation shape is
        `["tailscale", "whois", "--json", remote_ip]`; a non-zero exit or
        unparseable output raises `TailscaleResolutionError` -- fail-closed,
        never a silent default identity."""

        try:
            result = self._run(
                ["tailscale", "whois", "--json", remote_ip],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise TailscaleResolutionError(
                f"tailscale whois failed to run: {exc}"
            ) from exc

        if result.returncode != 0:
            raise TailscaleResolutionError(
                f"tailscale whois exited {result.returncode}: {result.stderr!r}"
            )

        try:
            data = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise TailscaleResolutionError(
                f"tailscale whois returned unparseable JSON: {exc}"
            ) from exc

        try:
            login = data["UserProfile"]["LoginName"]
        except (KeyError, TypeError) as exc:
            raise TailscaleResolutionError(
                f"tailscale whois JSON missing UserProfile.LoginName: {exc}"
            ) from exc

        if not login:
            raise TailscaleResolutionError(
                "tailscale whois returned an empty login -- refusing"
            )
        return str(login)
