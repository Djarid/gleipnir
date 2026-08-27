"""The ONE pilot content handler: deterministic diff-hunk-body truncation.

## Provenance

Diff-shaped structure-preserving truncation. The general idea — keep the
summary/skeleton, collapse the verbose body, mark what was cut — is inspired
by Headroom's CodeAwareCompressor / SmartCrusher concept
(https://github.com/headroomlabs-ai/headroom, Apache-2.0). This is an
independent, Gleipnir-native reimplementation of that BEHAVIOUR for a
unified-diff input (a diff is not source code, so AST techniques do not
apply); it is NOT a port or derivative of Headroom's source. No Headroom
code, binary, package, model, or network service is consumed. Headroom's
trademarked names (Headroom, SmartCrusher, CodeCompressor,
CodeAwareCompressor, Kompress) are NOT used; Apache-2.0 §6 grants no
trademark rights and none are claimed.

## What this module does

Implements the deterministic truncation rule (plan Decision 4): the file
list and every `+N -M` stat/header line are ALWAYS preserved unchanged; any
single hunk body strictly exceeding `THRESHOLD_LINES` lines is truncated to
its first/last `KEEP_LINES` lines, with the removed middle replaced by an
exact `# ... (K lines truncated)` marker (`K` = the exact count removed).
Never a silent drop. `THRESHOLD_LINES = 40`, `KEEP_LINES = 8` (Decisions
10-11; `2 * KEEP_LINES = 16 < THRESHOLD_LINES = 40` guarantees a truncated
hunk body is always strictly smaller than the size that triggered
truncation). Fails safe: input that does not parse into any hunk boundary
is returned unchanged (no crash, no silent corruption).

**Single responsibility (falsifiable, see plan Design Principles):** this
module knows NOTHING about dispatch or handler selection. It does not
import the dispatch mechanism, does not iterate a handler list, and does
not register itself -- registration is the caller's job, performed once at
the composition root (e.g. a broker's `mcp_server.py`).

stdlib-only (`dataclasses`/`typing` via the sibling `content_handlers`
protocol module only) -- see `tests/test_broker_stdlib_only.py` part (ii).

Plan: `.gleipnir/plans/git-diff-distill.md`, Assemble Step 3, Stress-test
T-1..T-5, T-1b/T-2b, T-6b.
"""

from __future__ import annotations

from typing import List

from .content_handlers.protocol import ProcessedResult

# Named module constants (DRY: referenced by name everywhere below, never
# repeated as bare literals). `2 * KEEP_LINES < THRESHOLD_LINES` (16 < 40) is
# the invariant that guarantees truncation always strictly shrinks the hunk
# body that triggered it (plan Decision 11 / edge case 7).
THRESHOLD_LINES = 40
KEEP_LINES = 8

_HUNK_HEADER_PREFIX = "@@"
_FILE_HEADER_PREFIX = "diff --git"


def _truncate_body(body_lines: List[str]) -> List[str]:
    """Return `body_lines` unchanged if at/under `THRESHOLD_LINES`, else the
    first/last `KEEP_LINES` lines with an exact `# ... (K lines truncated)`
    marker replacing the middle. The comparison is strictly `>` (not `>=`):
    a body of exactly `THRESHOLD_LINES` lines is NOT truncated (T-1b); a
    body of `THRESHOLD_LINES + 1` IS (T-2b)."""
    if len(body_lines) <= THRESHOLD_LINES:
        return list(body_lines)
    kept_head = body_lines[:KEEP_LINES]
    kept_tail = body_lines[-KEEP_LINES:]
    removed_count = len(body_lines) - (2 * KEEP_LINES)
    marker = f"# ... ({removed_count} lines truncated)\n"
    return kept_head + [marker] + kept_tail


class DiffHunkTruncationHandler:
    """The one pilot handler: truncates oversized per-hunk diff bodies.

    `can_handle` matches the `"diff"` hint. `process` parses the unified
    diff into file-header ("preamble") sections and per-hunk bodies with a
    single forward pass (no lookahead, no backtracking): a `diff --git` line
    starts a new file's preamble (verbatim, never truncated); an `@@` line
    starts a new hunk (the header line itself is verbatim, never truncated;
    everything between it and the next `@@`/`diff --git`/end-of-input is
    that hunk's body, the only truncation candidate). Input containing no
    `@@` boundary at all round-trips byte-for-byte unchanged as a natural
    consequence of this pass (every line is preamble), which is exactly the
    fail-safe behaviour required for malformed/non-unified-diff input.
    """

    def can_handle(self, content: str, hint: str) -> bool:
        return hint == "diff"

    def process(self, content: str) -> ProcessedResult:
        lines = content.splitlines(keepends=True)
        output: List[str] = []
        body_buffer: List[str] = []
        in_body = False

        def flush_body() -> None:
            if body_buffer:
                output.extend(_truncate_body(body_buffer))

        for line in lines:
            if line.startswith(_HUNK_HEADER_PREFIX):
                flush_body()
                body_buffer.clear()
                output.append(line)
                in_body = True
            elif line.startswith(_FILE_HEADER_PREFIX):
                flush_body()
                body_buffer.clear()
                output.append(line)
                in_body = False
            elif in_body:
                body_buffer.append(line)
            else:
                output.append(line)

        flush_body()
        return ProcessedResult(content="".join(output))
