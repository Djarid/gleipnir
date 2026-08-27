"""Gleipnir git broker (`gleipnir-git`).

Modules:
    guards.py             -- stdlib-only pre-commit gate (protected-branch,
                              secret-scan, data-file checks).
    content_handlers/     -- stdlib-only generic content-handler plugin
                              library (Handler protocol, ProcessedResult,
                              register/dispatch); no handler-specific logic.
    diff_hunk_handler.py  -- stdlib-only pilot handler: deterministic
                              diff-hunk-body truncation for `git_diff`'s
                              output (`.gleipnir/plans/git-diff-distill.md`).
    mcp_server.py         -- FastMCP("gleipnir-git") stdio server; the only
                              file in this package that imports `mcp`.
"""

from __future__ import annotations
