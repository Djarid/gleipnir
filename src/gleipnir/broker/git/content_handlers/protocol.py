"""Content-handler contract: `Handler` protocol + `ProcessedResult`.

The generic, reusable half of the content-handler plugin library (the other
half is `registry.py`'s dispatcher). Both halves are stdlib-only and contain
**no** handler-specific logic -- see `tests/test_broker_stdlib_only.py`
part (ii) and this plan's Design Principles (SRP falsifiable claims).

**Structural safety by construction (item 5).** `Handler.process` accepts
only a `str` (raw content) and returns a `ProcessedResult` carrying only a
`str`. Neither type has any parameter, attribute, or member named for the
broker's response envelope, a `success` flag, a commit hash, or a
secret-scan verdict -- so a handler CANNOT reach any of that, not because of
a convention, but because the contract does not offer a path to it. See
`tests/test_broker_git_content_handlers.py::TestStructuralSafety` (a
type/structural test via `inspect.signature`, not merely behavioural).

Plan: `.gleipnir/plans/git-diff-distill.md`, Assemble Step 2, Stress-test T-6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ProcessedResult:
    """The sole return type of `Handler.process`: transformed content, and
    nothing else. No envelope, `success` flag, commit hash, or secret-scan
    verdict field exists on this type -- structurally unreachable, not just
    omitted by convention."""

    content: str


@runtime_checkable
class Handler(Protocol):
    """Minimal content-handler contract: exactly two methods, content in,
    content (wrapped in `ProcessedResult`) out.

    `can_handle(content, hint)` decides whether this handler applies;
    `process(content)` performs the transformation. Neither method receives
    or can return anything beyond raw string content -- the broker's
    response envelope, `success` flag, commit metadata, and secret-scan
    verdict are all structurally unreachable through this protocol.
    """

    def can_handle(self, content: str, hint: str) -> bool:
        """Return True if this handler should process `content` for `hint`."""
        ...

    def process(self, content: str) -> ProcessedResult:
        """Transform `content`, returning the (possibly unchanged) result."""
        ...
