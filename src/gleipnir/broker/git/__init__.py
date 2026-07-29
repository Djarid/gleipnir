"""Gleipnir git broker (`gleipnir-git`).

Two modules:
    guards.py      -- stdlib-only pre-commit gate (protected-branch,
                       secret-scan, data-file checks).
    mcp_server.py  -- FastMCP("gleipnir-git") stdio server; the only file in
                       this package that imports `mcp`.
"""

from __future__ import annotations
