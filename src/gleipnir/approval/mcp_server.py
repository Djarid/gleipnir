"""Gleipnir Tier-3 approval MCP wrapper (`gleipnir-approval`).

Plan: `.gleipnir/plans/tier3-mcp-approval-launcher.md`, Decisions 10/11/12/
13/14, Trace "Chosen module layout", Assemble Steps 1-2, Stress-test
T-1..T-5/T-8/T-9/T-11. Supersedes `.gleipnir/plans/tier3-signed-approval.md`
Decision 15's "no auto-start": opencode (or any local-MCP-capable launcher)
may now spawn this module as a supervised subprocess, because the security
locus is key-*readability*, not process-*launch* (Decision 3) -- launching
this process confers process-supervision only, never the ability to mint a
token.

This module is a **thin, import-only wrapper** (Decision 13 / the Design
Intent in the plan's Design Principles section):

  * it **imports** `run_server` + `register_default_resolvers` from
    `.server` and calls them, on a **daemon background thread** started at
    process startup (Decision 12) -- it re-implements no HTTP handler, no
    identity resolution, and no mint/validate logic of its own;
  * it exposes exactly one MCP tool, `request_approval`, which **reuses**
    (never re-implements) the existing staging envelope shape
    (`compute_change_hash`/`staged_path_for`/`default_token_dir`, also
    imported from `.server`, Decision 14 DRY) and the `/approve/<hash>` URL
    contract already fixed by `tier3-gate.ts`'s `buildApprovalUrl`
    (`:435-445`);
  * it ends with `mcp.run(transport="stdio")` -- the identical shape as the
    two existing brokers (`broker/git/mcp_server.py:524`,
    `broker/pm/mcp_server.py`); the `mcp` SDK import is confined to this ONE
    file in `approval/` (Decision 8, `decisions/runtime-and-deps.md`).

**CLOSED IMPORT ALLOW-LIST (the "wraps, never mints" boundary -- T-11).**
This module may import ONLY these symbols from `.server`:

    run_server, register_default_resolvers            (launch)
    compute_change_hash, staged_path_for, default_token_dir  (staging/URL reuse)

It MUST NOT import or call `capture_approval` / `mint_approval`
(`server.py:227`) nor `load_key` (`verify/marker.py`). `capture_approval`
mints internally and needs a `remote_ip` for `resolve_identity`'s
`tailscale whois` lookup (`server.py:224-227`); calling it from inside this
process (e.g. with `remote_ip="127.0.0.1"`) would resolve identity against
the *local host* and mint a valid, content-bound approval token with ZERO
human review -- a complete bypass of the separate-authenticated-device
approval property (Decision 3 / the brief's Supersession clause). This is
enforced structurally by `tests/test_approval_mcp_server.py::TestT11...`
(the reverse-import scan).

**Honesty note on what that scan actually proves (spec-review round 2,
non-blocking Moderate finding -- folded in, not skipped):** T-11 is a
name-based source scan aimed at accidental/incremental drift toward
re-introducing minting logic in this wrapper, not adversarial obfuscation --
a deliberately-constructed dynamic reference (string concatenation,
`getattr` with a computed name) would evade it; accepted because the threat
model here is implementer drift, not a malicious wrapper author.

**Port-conflict / fail-closed-key handling (Decision 19 as corrected by
`.gleipnir/plans/approval-listener-fail-loud.md`):** the daemon thread's
target function (`_run_listener`) wraps `register_default_resolvers()` +
`run_server(...)` in a try/except that CLASSIFIES the failure rather than
swallowing every failure alike. The **only** benign case is a bind conflict
on `127.0.0.1:8765` -- an `OSError` whose `errno` is exactly
`errno.EADDRINUSE` (edge case E-3): that is logged at WARNING and the thread
exits quietly, because a second listener already running is the operator's
own doing, not a failure. **Every other failure is fatal** -- including a
fail-closed `KeyUnavailable` when no usable key is configured, any other
`OSError` (`EACCES`, `EADDRNOTAVAIL`, `EMFILE`/`ENFILE`, or `errno is None`),
and any non-`OSError` fault from `register_default_resolvers()`: it is
logged at ERROR and recorded in the module-level listener state, so
`request_approval` refuses loudly (raising `ApprovalListenerUnavailable`,
before staging anything) instead of returning a URL that nothing can serve.
Either way the listener thread exits without propagating into (and
crashing) the MCP process's stdio `request_approval` tool surface -- only
the *classification* of "does this failure make a returned URL meaningless?"
changed, not the "never crash the process" shape.

Run as: ``python -m gleipnir.approval.mcp_server``
"""

from __future__ import annotations

import errno
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .server import (
    compute_change_hash,
    default_token_dir,
    register_default_resolvers,
    run_server,
    staged_path_for,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "gleipnir-approval",
    instructions=(
        "Stages pending Tier-3 change content for out-of-band operator "
        "review and returns the /approve/<hash> review URL as a plain "
        "string. Never mints an approval token itself (only the operator, "
        "approving from a separate authenticated device, can do that) and "
        "never opens a browser on this host."
    ),
)

# The env var `buildApprovalUrl` (`tier3-gate.ts:435-445`) reads at call
# time -- read here at call time too, so tests can toggle it per-case and
# so approval readiness never depends on it being set (edge case 2).
_APPROVAL_BASE_URL_ENV = "GLEIPNIR_APPROVAL_BASE_URL"


class ApprovalListenerUnavailable(RuntimeError):
    """Raised by `request_approval` when the in-process listener has
    recorded a fatal failure (plan `.gleipnir/plans/approval-listener-fail-
    loud.md`, Decision 4): the returned message names the underlying cause
    verbatim, so this MCP's tool surface never hands out a `/approve/<hash>`
    URL that nothing is listening to.
    """


# Listener-state holder (Decision 8 / plan Trace step 2): a single
# `Optional[str]` "refusal reason" guarded by a lock, because the listener
# thread WRITES it and the MCP main thread (inside `request_approval`) READS
# it -- the lock is load-bearing, not decorative. `None` means "no fatal
# failure has been recorded" (the initial, and the reset, state).
_listener_state_lock = threading.Lock()
_listener_refusal_reason: Optional[str] = None


def mark_unavailable(reason: str) -> None:
    """Record a fatal listener failure. Called ONLY from `_run_listener`'s
    fatal branch."""
    global _listener_refusal_reason
    with _listener_state_lock:
        _listener_refusal_reason = reason


def refusal_reason() -> Optional[str]:
    """The currently-recorded fatal reason, or `None` if the listener has
    not (yet, or ever) recorded one. Called from `request_approval` as its
    first statement."""
    with _listener_state_lock:
        return _listener_refusal_reason


def reset() -> None:
    """Test-isolation seam (Decision 8) -- clears any recorded refusal
    reason, the same "injectable seam only" convention as `token_dir=`
    above. Production code never calls this; only tests do."""
    global _listener_refusal_reason
    with _listener_state_lock:
        _listener_refusal_reason = None


def _build_approval_url(change_hash: str) -> str:
    """Mirror `buildApprovalUrl` (`tier3-gate.ts:435-445`) EXACTLY (Decision
    14 DRY): the same env var, the same trailing-slash normalization, and
    the same relative-hint fallback text when the env var is unset -- so
    `request_approval` produces the identical artifact shape the hook's
    REFUSE path already produces, not a second URL scheme."""

    base = os.environ.get(_APPROVAL_BASE_URL_ENV)
    if base:
        normalized = base[:-1] if base.endswith("/") else base
        return f"Approve at: {normalized}/approve/{change_hash}"
    return (
        f"Approve at: <your approval listener>/approve/{change_hash} "
        "(set GLEIPNIR_APPROVAL_BASE_URL to show the full URL here)"
    )


def _stage_pending_content(
    content: str,
    file_path: str,
    tool: str,
    *,
    token_dir: Optional[Path] = None,
) -> str:
    """Stage the SAME `pending-<hash>.json` envelope shape
    `stagePendingContent` writes (`tier3-gate.ts:408-426`):
    `{content, filePath, tool, staged_at}`, to the same `.gleipnir/var/tmp/`
    directory (`default_token_dir()`) -- reused BY CONTRACT, never a second
    staging format (Decision 14). Returns the full `change_hash` (the same
    value that keys the staged filename and the approval URL).

    ``token_dir`` is an injectable override (test-isolation seam only, same
    shape as `capture_approval`'s `token_dir=` parameter in `server.py`);
    `request_approval` never passes it -- production always stages to the
    one real `.gleipnir/var/tmp/` directory the hook and listener also use.
    """

    target_dir = token_dir if token_dir is not None else default_token_dir()
    change_hash = compute_change_hash(content.encode("utf-8"))
    envelope = {
        "content": content,
        "filePath": file_path,
        "tool": tool,
        "staged_at": int(time.time()),
    }
    target_dir.mkdir(parents=True, exist_ok=True)
    staged_path_for(target_dir, change_hash).write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    return change_hash


@mcp.tool()
def request_approval(content: str, file_path: str = "", tool: str = "") -> str:
    """Stage pending Tier-3 change content and return the review URL.

    Writes the same `pending-<hash>.json` staging envelope the TypeScript
    hook writes on REFUSE, then returns the `/approve/<hash>` URL as a
    plain string (O-4/B1) -- it does **not** mint a token itself and does
    **not** open a browser on this host. The operator opens the returned
    URL on a separate authenticated tailnet device to review and approve.

    **Fails loudly instead of staging** (plan `.gleipnir/plans/approval-
    listener-fail-loud.md`, Decision 4/5) when the in-process listener has
    recorded a fatal failure: raises `ApprovalListenerUnavailable` as the
    FIRST statement, before any staging, naming the captured cause verbatim.
    Scoped precisely (Decision 13): this refusal means only that *this
    process's* `request_approval` tool will not mint or make available a
    review URL via its own in-process listener -- it is not a claim that no
    approval can be minted at all. A separately run, healthy manual
    listener (`bin/gleipnir-approval-server`) at another uid is unaffected
    and may still be serving.

    Args:
        content: the exact pending Tier-3 change content to stage -- the
            bytes that will be hashed and, on operator approval, minted.
        file_path: the on-disk path this content targets (display-only
            context on the review page; never hashed/minted).
        tool: the name of the tool/action that produced this content
            (display-only context on the review page).

    Raises:
        ApprovalListenerUnavailable: the in-process listener has recorded a
            fatal failure (anything other than a benign `EADDRINUSE` port
            conflict) -- nothing is staged.
    """
    reason = refusal_reason()
    if reason is not None:
        raise ApprovalListenerUnavailable(
            "gleipnir-approval's in-process listener is unavailable, so "
            "this MCP's request_approval tool cannot mint or make "
            f"available a review URL via that listener: {reason} -- this "
            "process's request_approval tool will keep refusing for the "
            "life of this process; it does NOT mean no approval can be "
            "minted at all -- a separately run, healthy manual listener "
            "(bin/gleipnir-approval-server) at another uid is unaffected "
            "and may still be serving; if so, use its URL instead, or fix "
            "and restart this process's in-process listener."
        )
    change_hash = _stage_pending_content(content, file_path, tool)
    return _build_approval_url(change_hash)


def _run_listener(
    *,
    key_file: Optional[str] = None,
    token_dir: Optional[Path] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """Daemon-thread target (Decision 12): registers the default resolvers
    then starts the existing `server.py` listener, UNCHANGED, on this
    thread. `serve_forever()` blocks here for the life of the thread.

    Failure classification (Decision 2, plan `.gleipnir/plans/approval-
    listener-fail-loud.md`): the **only** benign failure is an `OSError`
    whose `errno` is exactly `errno.EADDRINUSE` (edge case E-3, Decision
    19's named case -- a second listener already bound is the operator's
    own doing, not a security regression) -- that is logged at WARNING and
    the state is left untouched, so `request_approval` keeps working
    exactly as before. **Every other failure is fatal** -- any other
    `OSError` (`EACCES`, `EADDRNOTAVAIL`, `EMFILE`/`ENFILE`, or `errno is
    None`, edge case E-3b), a fail-closed `KeyUnavailable` when no usable
    key is configured (edge case E-1/E-2), or any other exception from
    `register_default_resolvers()` (edge case E-7) -- logged at ERROR and
    recorded via `mark_unavailable()`, so `request_approval` refuses loudly
    instead of returning a dead URL. Either way this function returns
    without raising, so the thread exits WITHOUT ever propagating into (and
    crashing) the MCP process's stdio `request_approval` tool surface --
    only the classification changed, not the never-crash shape.
    """

    kwargs = {}
    if host is not None:
        kwargs["host"] = host
    if port is not None:
        kwargs["port"] = port
    try:
        register_default_resolvers()
        run_server(key_file=key_file, token_dir=token_dir, **kwargs)
    except Exception as exc:  # noqa: BLE001 -- classified below, not swallowed
        if isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE:
            logger.warning(
                "gleipnir-approval listener thread exiting without a bound "
                "listener (tool surface remains up): %s",
                exc,
            )
            return
        logger.error(
            "gleipnir-approval listener thread exiting fatally -- "
            "request_approval will refuse until this is fixed: %s",
            exc,
        )
        mark_unavailable(str(exc))


def start_listener_thread(
    *,
    key_file: Optional[str] = None,
    token_dir: Optional[Path] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> threading.Thread:
    """Start the HTTP listener on a daemon background thread (Decision 12).

    Daemon so the listener dies with the MCP process (edge case 3) -- no
    orphaned `127.0.0.1:8765` listener survives an opencode shutdown.
    ``host``/``port``/``key_file``/``token_dir`` are test-injection seams
    only; production (the `__main__` block below) calls this with no
    overrides, so the listener binds `127.0.0.1:8765` unchanged.
    """

    thread = threading.Thread(
        target=_run_listener,
        kwargs={
            "key_file": key_file,
            "token_dir": token_dir,
            "host": host,
            "port": port,
        },
        daemon=True,
        name="gleipnir-approval-listener",
    )
    thread.start()
    return thread


if __name__ == "__main__":
    start_listener_thread()
    mcp.run(transport="stdio")
