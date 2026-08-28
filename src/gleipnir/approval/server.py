"""Gleipnir approval listener -- stdlib `http.server`, bound `127.0.0.1`.

Spec: `.gleipnir/plans/tier3-signed-approval.md` Decision 7/15, Trace
"Integrations map", Assemble Step 5. The composition root: registers the
ONE resolver (`TailscaleResolver`, Route α) and, per request, builds a
`RequestContext`, resolves an identity (FAIL-CLOSED on no-match --
`IdentityUnresolved` propagates, no token minted), computes the
`change_hash` of the posted pending content, mints an
`ApprovalToken` (180s freshness), and writes it to `token_dir`
(`.gleipnir/var/tmp/`, Tier-0, Decision 17).

**Launch supervision (Decision 15, superseded by
`.gleipnir/plans/tier3-mcp-approval-launcher.md`).** This module's listener
may be started either by the operator's manual shim
(`bin/gleipnir-approval-server`, a cooperative process the operator starts
and Ctrl-C stops) or as a supervised subprocess spawned by opencode's
`gleipnir-approval` local MCP (`gleipnir.approval.mcp_server`, which imports
`run_server` and calls it on a background thread). Either launch path is
fine: the security property this module provides was never *who launches
the process* but that the HMAC signing key stays unreachable to the agent
tool surface (Decision 3) -- launching confers process-supervision only,
never the ability to mint a token.

**Pure-core / thin-edge split** (mirrors `preflight.boundary` and
`sandbox.runtime`): `capture_approval` is the fully-unit-testable
orchestration core (identity resolution + minting + writing the token,
every edge injectable); `ApprovalRequestHandler`/`run_server` are the thin
HTTP edge that wires real sockets to it. Tests exercise the core directly
with injected fakes (Stress-test T-17) rather than driving live HTTP.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import http.server
import json
import re
from pathlib import Path
from typing import Callable, Mapping

from ..verify.marker import load_key
from .identity import IdentityUnresolved, RequestContext, ResolvedIdentity, register, resolve_identity
from .identity.tailscale_resolver import TailscaleResolver
from .token import ApprovalToken, mint_approval

DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 8765

# The full-hash form a staged `pending-<hash>.json` filename may carry (P1/E7)
# -- lowercase hex sha256, exactly 64 chars. Validated BEFORE any filesystem
# join so a malformed/`../`-shaped `<hash>` URL segment can never escape
# `token_dir` (E7/S7).
_CHANGE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

_APPROVE_PREFIX = "/approve/"


def _repo_root() -> Path:
    # src/gleipnir/approval/server.py -> repo root is three parents up.
    return Path(__file__).resolve().parents[3]


def default_token_dir() -> Path:
    """`.gleipnir/var/tmp/` -- Tier-0, gitignored, disposable (Decision 17)."""
    return _repo_root() / ".gleipnir" / "var" / "tmp"


_NO_STAGED_CHANGE_MESSAGE = (
    b"no staged change for this hash -- it may be stale, already approved, "
    b"or the URL is wrong"
)


def _read_target_bytes(file_path: object) -> bytes | None:
    """Best-effort read of the envelope's `filePath` for the review-page
    diff base (P5/E5) -- display-only, NEVER hashed/minted (see the
    Deliberately-deferred non-blocker note: `filePath` reaches only a
    display read, unlike `<hash>`, which reaches a filesystem join and is
    therefore validated, E7). Returns `None` (not an exception) on any
    fault -- absent file, wrong type, unreadable -- so a poisoned/odd
    `filePath` can at worst degrade the diff to "new file", never crash the
    review page."""

    if not isinstance(file_path, str) or not file_path:
        return None
    target = _repo_root() / file_path
    try:
        return target.read_bytes()
    except OSError:
        return None


def compute_change_hash(content: bytes) -> str:
    """sha256 of the exact pending content shown/approved -- the
    content-binding half of the minted token."""
    return hashlib.sha256(content).hexdigest()


def build_request_context(remote_ip: str, headers: Mapping[str, str]) -> RequestContext:
    return RequestContext(remote_ip=remote_ip, headers=dict(headers))


def token_path_for(token_dir: Path, change_hash: str) -> Path:
    return token_dir / f"approval-{change_hash[:16]}.json"


def staged_path_for(token_dir: Path, change_hash: str) -> Path:
    """`pending-<change_hash>.json` -- the FULL hash (distinct from
    `token_path_for`'s 16-char prefix for the minted token; do not
    conflate). Written by the hook on REFUSE (P1), read here by
    `load_staged`."""

    return token_dir / f"pending-{change_hash}.json"


def load_staged(token_dir: Path, change_hash: str) -> dict | None:
    """Read + JSON-parse the staged envelope; `None` on any fault (absent,
    unparseable, or a malformed `<hash>`) -- the caller maps that to a 404
    (P7). Pure, unit-testable.

    **Explicit UTF-8 read (REQUIRED, not implicit):** reads the file as
    `read_bytes()` then `json.loads(raw)` -- `json.loads` decodes UTF-8 per
    the JSON spec -- NEVER a bare `Path.read_text()` with no encoding
    argument, whose decode is locale/platform-dependent and could corrupt
    multibyte content before it is hashed (P2/S13).

    **No path traversal (E7):** `<change_hash>` is validated as
    `[0-9a-f]{64}` BEFORE `staged_path_for` ever builds a path from it, so a
    `../` segment (or any other non-hex shape) can never reach the
    filesystem join -- it 404s here instead.
    """

    if not _CHANGE_HASH_RE.match(change_hash):
        return None
    path = staged_path_for(token_dir, change_hash)
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def render_review_page(envelope: dict, current_on_disk: bytes | None) -> bytes:
    """Pure HTML builder for `GET /approve/<hash>` -- no I/O, no minting.

    HTML-escapes `envelope["content"]` for display (P4) -- the bytes that
    get hashed/minted are ALWAYS `envelope["content"]` itself, never this
    escaped display copy (the what-you-sign invariant, Design Intent). Shows
    a `difflib.unified_diff` against `current_on_disk` (decoded UTF-8,
    `errors="replace"`) when given, or a "new file" notice when `None`
    (P5/E5). Emits a `<form method="POST" action="/approve/<hash>">` with a
    single submit button and NO content field (P3) -- `<hash>` is
    RECOMPUTED from `envelope["content"]` here (the same sha256 that keyed
    the staged filename and the approval URL), never passed in separately,
    so the form action can never diverge from what was actually staged.
    """

    content = envelope["content"]
    file_path = str(envelope.get("filePath", ""))
    tool = str(envelope.get("tool", ""))
    staged_at = str(envelope.get("staged_at", ""))
    change_hash = compute_change_hash(content.encode("utf-8"))
    escaped_content = html.escape(content, quote=True)

    if current_on_disk is None:
        diff_html = "<p><em>new file (no on-disk base to diff against)</em></p>"
    else:
        base_text = current_on_disk.decode("utf-8", errors="replace")
        diff_lines = list(
            difflib.unified_diff(
                base_text.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=file_path or "on-disk",
                tofile="staged",
            )
        )
        if diff_lines:
            escaped_diff = "".join(
                html.escape(line, quote=True) for line in diff_lines
            )
            diff_html = f"<pre>{escaped_diff}</pre>"
        else:
            diff_html = "<p><em>no textual difference from the on-disk file</em></p>"

    body = (
        "<html><body>"
        "<h1>Gleipnir Tier-3 change review</h1>"
        f"<p>tool: {html.escape(tool, quote=True)} | "
        f"filePath: {html.escape(file_path, quote=True)} | "
        f"staged_at: {html.escape(staged_at, quote=True)}</p>"
        "<h2>Diff against on-disk</h2>"
        f"{diff_html}"
        "<h2>Full staged content</h2>"
        f"<pre>{escaped_content}</pre>"
        f'<form method="POST" action="/approve/{change_hash}">'
        '<button type="submit">Approve</button>'
        "</form>"
        "</body></html>"
    )
    return body.encode("utf-8")


def capture_approval(
    *,
    remote_ip: str,
    headers: Mapping[str, str],
    pending_content: bytes,
    key: bytes,
    resolve: Callable[[RequestContext], ResolvedIdentity] = resolve_identity,
    minted_at: int | None = None,
    token_dir: Path | None = None,
) -> ApprovalToken:
    """The server's core orchestration -- injectable for tests.

    Builds a `RequestContext`, resolves an identity (raises
    `IdentityUnresolved` -- FAIL-CLOSED -- on no-match; propagates
    uncaught, no token minted), computes the `change_hash` of
    `pending_content`, mints a token bound to that content + identity, and
    writes it to `token_dir`. Returns the minted token.
    """

    ctx = build_request_context(remote_ip, headers)
    identity = resolve(ctx)  # IdentityUnresolved propagates -- fail-closed
    change_hash = compute_change_hash(pending_content)
    token = mint_approval(
        change_hash, identity.identity, identity.provider, key, minted_at=minted_at
    )
    target_dir = token_dir if token_dir is not None else default_token_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    token_path_for(target_dir, change_hash).write_text(token.to_json())
    return token


class ApprovalRequestHandler(http.server.BaseHTTPRequestHandler):
    """Thin HTTP edge over `capture_approval`.

    `GET /` serves a minimal instructions page. `POST /approve` reads the
    request body as the raw bytes of the pending Tier-3 content, calls
    `capture_approval`, and responds 200 with the minted token's
    change_hash/identity/provider on success, or 403 on an unresolvable
    identity (never a default identity, never a 200 without a minted
    token). Per-instance configuration (`key`/`resolve`/`token_dir`) is
    threaded through class attributes set by `make_handler_class`, since
    `http.server.HTTPServer` instantiates one handler object per request
    from a class, not from a pre-built instance.
    """

    key: bytes = b""
    resolve: Callable[[RequestContext], ResolvedIdentity] = staticmethod(resolve_identity)
    token_dir: Path | None = None

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler convention)
        if self.path in ("/", "/approve"):
            body = (
                b"<html><body><p>Gleipnir Tier-3 approval listener.</p>"
                b"<p>POST the pending change content to /approve to mint a "
                b"fresh, content-bound approval token.</p></body></html>"
            )
            self._send(200, body, content_type="text/html")
            return
        if self.path.startswith(_APPROVE_PREFIX):
            change_hash = self.path[len(_APPROVE_PREFIX) :]
            token_dir = self._resolve_token_dir()
            envelope = load_staged(token_dir, change_hash)
            if envelope is None:
                self._send(404, _NO_STAGED_CHANGE_MESSAGE, content_type="text/plain")
                return
            current_on_disk = _read_target_bytes(envelope.get("filePath"))
            body = render_review_page(envelope, current_on_disk)
            self._send(200, body, content_type="text/html")
            return
        self._send(404, b"not found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/approve":
            length = int(self.headers.get("Content-Length", "0") or "0")
            pending_content = self.rfile.read(length) if length else b""
            self._mint_and_respond(pending_content)
            return
        if self.path.startswith(_APPROVE_PREFIX):
            change_hash = self.path[len(_APPROVE_PREFIX) :]
            token_dir = self._resolve_token_dir()
            envelope = load_staged(token_dir, change_hash)
            if envelope is None:
                self._send(404, _NO_STAGED_CHANGE_MESSAGE, content_type="text/plain")
                return
            self._mint_and_respond(envelope["content"].encode("utf-8"))
            return
        self._send(404, b"not found")

    def _resolve_token_dir(self) -> Path:
        token_dir = type(self).token_dir
        return token_dir if token_dir is not None else default_token_dir()

    def _mint_and_respond(self, pending_content: bytes) -> None:
        """Shared POST core (P3, DRY): the SAME `capture_approval` call site
        for both the existing raw-body `/approve` and the new hash-scoped
        `/approve/<hash>` -- reused unchanged, never duplicated."""

        try:
            token = capture_approval(
                remote_ip=self.client_address[0],
                headers=self.headers,
                pending_content=pending_content,
                key=type(self).key,
                resolve=type(self).resolve,
                token_dir=type(self).token_dir,
            )
        except IdentityUnresolved as exc:
            self._send(
                403,
                json.dumps({"status": "rejected", "reason": str(exc)}).encode(),
                content_type="application/json",
            )
            return
        self._send(
            200,
            json.dumps(
                {
                    "status": "approved",
                    "change_hash": token.change_hash,
                    "identity": token.approver_identity,
                    "provider": token.provider,
                }
            ).encode(),
            content_type="application/json",
        )

    def _send(self, code: int, body: bytes, *, content_type: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Quiet by default -- the operator runs this shim in a foreground
        # terminal; suppress BaseHTTPRequestHandler's default stderr access
        # log noise. Override in a subclass for verbose operator debugging.
        pass


def make_handler_class(
    *,
    key: bytes,
    resolve: Callable[[RequestContext], ResolvedIdentity] = resolve_identity,
    token_dir: Path | None = None,
) -> type[ApprovalRequestHandler]:
    """Bind a fresh `ApprovalRequestHandler` subclass to `(key, resolve,
    token_dir)`. `http.server.HTTPServer` instantiates one handler object
    per request FROM A CLASS, so per-server-run configurable state is
    threaded through via a dedicated subclass rather than mutable module
    globals (which would leak across concurrent/successive server runs)."""

    class _BoundHandler(ApprovalRequestHandler):
        pass

    _BoundHandler.key = key
    _BoundHandler.resolve = staticmethod(resolve)
    _BoundHandler.token_dir = token_dir
    return _BoundHandler


def register_default_resolvers() -> None:
    """The ONE resolver registered today (Route α). Called only at this
    composition root -- never inside `identity/registry.py`."""
    register(TailscaleResolver())


def run_server(
    host: str = DEFAULT_BIND_HOST,
    port: int = DEFAULT_BIND_PORT,
    *,
    key_file: str | None = None,
    token_dir: Path | None = None,
) -> None:
    """The real entrypoint `bin/gleipnir-approval-server` execs into.

    Registers `TailscaleResolver`, loads the G-3.1 key (fail-closed --
    `KeyUnavailable` propagates, refusing to start rather than serving
    without a usable key), and serves forever until interrupted
    (Ctrl-C / SIGINT). May be called either by the operator's explicit shim
    invocation or by `gleipnir.approval.mcp_server` on a background thread
    when opencode supervises the listener -- both launch paths are equally
    safe because the key stays unreachable to the agent tool surface
    (Decision 3), not because of who calls this function."""

    register_default_resolvers()
    key = load_key(key_file)
    handler_class = make_handler_class(
        key=key, resolve=resolve_identity, token_dir=token_dir
    )
    httpd = http.server.HTTPServer((host, port), handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gleipnir-approval-server")
    parser.add_argument("--host", default=DEFAULT_BIND_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_BIND_PORT)
    parser.add_argument("--key-file", default=None, help="override key path")
    parser.add_argument(
        "--token-dir",
        default=None,
        help="override the token write directory (default: .gleipnir/var/tmp)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token_dir = Path(args.token_dir) if args.token_dir else None
    run_server(args.host, args.port, key_file=args.key_file, token_dir=token_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
