"""Generic content-handler registry/dispatcher.

**Single responsibility (falsifiable, see plan Design Principles):** given
`(content, hint)`, select the first registered handler whose `can_handle` is
True and return its `process(content)` result; otherwise return `content`
unchanged. This module contains **no** reference to any particular content
format, no format-specific threshold or keep-count constant, and no
handler-specific logic of any kind; it does not import any concrete handler
module. The falsifiable check (see the sibling handler module's own
docstring and the test suite) is that this file's source text never names a
specific content format or names a concrete handler module by import.

**Open/closed (the extensibility test).** Adding a new handler never
requires editing this module -- only a call to `register(...)` from wherever
the new handler is composed (the caller's composition root, e.g. a broker's
`mcp_server.py`).

Plan: the pilot content-handler plan under `.gleipnir/plans/`, Assemble
Step 2, Stress-test T-8/T-9.
"""

from __future__ import annotations

from typing import List

from .protocol import Handler, ProcessedResult

# Module-level registry: ordered list of registered handlers. First
# registered, first matched -- `dispatch` walks this list in order and
# returns the first handler whose `can_handle` is True.
_handlers: List[Handler] = []


def register(handler: Handler) -> None:
    """Register `handler`. Order matters: earlier registrations are tried
    first in `dispatch`."""
    _handlers.append(handler)


def dispatch(content: str, hint: str) -> ProcessedResult:
    """Return the first matching handler's processed result.

    Walks the registered handlers in registration order; the first whose
    `can_handle(content, hint)` is True wins. If no handler matches (or none
    is registered), `content` is returned unchanged -- the no-handler
    fallback."""
    for handler in _handlers:
        if handler.can_handle(content, hint):
            return handler.process(content)
    return ProcessedResult(content=content)
