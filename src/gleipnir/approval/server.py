"""Gleipnir approval listener -- stdlib `http.server`, bound `127.0.0.1`.

Spec: `.gleipnir/plans/tier3-signed-approval.md` Decision 7/15, Trace
"Integrations map", Assemble Step 5. The composition root: registers the
ONE resolver (`TailscaleResolver`, Route α) and, per request, builds a
`RequestContext`, resolves an identity (FAIL-CLOSED on no-match --
`IdentityUnresolved` propagates, no token minted), computes the
`change_hash` of the posted pending content, mints an
`ApprovalToken` (180s freshness), and writes it to `token_dir`
(`.gleipnir/var/tmp/`, Tier-0, Decision 17).

**No auto-start (Decision 15).** This module only runs when the operator
starts it, via `bin/gleipnir-approval-server`; it is a cooperative,
long-running process the operator starts manually and Ctrl-C stops -- not a
daemon, not launched by any agent.

**Pure-core / thin-edge split** (mirrors `preflight.boundary` and
`sandbox.runtime`): `capture_approval` is the fully-unit-testable
orchestration core (identity resolution + minting + writing the token,
every edge injectable); `ApprovalRequestHandler`/`run_server` are the thin
HTTP edge that wires real sockets to it. Tests exercise the core directly
with injected fakes (Stress-test T-17) rather than driving live HTTP.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
from pathlib import Path
from typing import Callable, Mapping

from ..verify.marker import load_key
from .identity import IdentityUnresolved, RequestContext, ResolvedIdentity, register, resolve_identity
from .identity.tailscale_resolver import TailscaleResolver
from .token import ApprovalToken, mint_approval

DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 8765


def _repo_root() -> Path:
    # src/gleipnir/approval/server.py -> repo root is three parents up.
    return Path(__file__).resolve().parents[3]


def default_token_dir() -> Path:
    """`.gleipnir/var/tmp/` -- Tier-0, gitignored, disposable (Decision 17)."""
    return _repo_root() / ".gleipnir" / "var" / "tmp"


def compute_change_hash(content: bytes) -> str:
    """sha256 of the exact pending content shown/approved -- the
    content-binding half of the minted token."""
    return hashlib.sha256(content).hexdigest()


def build_request_context(remote_ip: str, headers: Mapping[str, str]) -> RequestContext:
    return RequestContext(remote_ip=remote_ip, headers=dict(headers))


def token_path_for(token_dir: Path, change_hash: str) -> Path:
    return token_dir / f"approval-{change_hash[:16]}.json"


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
        self._send(404, b"not found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/approve":
            self._send(404, b"not found")
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        pending_content = self.rfile.read(length) if length else b""
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
    (Ctrl-C / SIGINT). No auto-start: nothing calls this except the
    operator's explicit shim invocation."""

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
