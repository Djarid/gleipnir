"""Gleipnir PM broker (`gleipnir-pm`).

Two modules:
    platform.py    -- stdlib-only remote/token detection + GitHub/GitLab REST
                       client for the 4 issue verbs.
    mcp_server.py  -- FastMCP("gleipnir-pm") stdio server; the only file in
                       this package that imports `mcp`.
"""

from __future__ import annotations
