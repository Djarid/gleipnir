"""Generic content-handler plugin library (the reuse seam).

Re-exports the public surface a caller (a broker's `mcp_server.py`) and a
handler author both need: the `Handler` protocol, `ProcessedResult`, and the
dispatcher's `register`/`dispatch` functions. Stdlib-only -- see
`tests/test_broker_stdlib_only.py` part (ii).

Two modules:
    protocol.py  -- `Handler` protocol + `ProcessedResult` dataclass; no
                     handler-specific logic.
    registry.py  -- `register()`/`dispatch()`; no handler-specific logic,
                     no-handler fallback returns content unchanged.

This package currently lives inside `broker/git/` as a single-consumer
pilot (`.gleipnir/plans/git-diff-distill.md`, Decision 9); it is an
importable subpackage rather than inlined code, so promoting it to a shared
sibling component later (if a second broker ever needs it) is a move, not a
rewrite.
"""

from __future__ import annotations

from .protocol import Handler, ProcessedResult
from .registry import dispatch, register

__all__ = ["Handler", "ProcessedResult", "dispatch", "register"]
