"""Shared pytest configuration for the `tests/` suite.

Registers the `hostonly` marker (used by
`tests/test_preflight_probe_hostonly.py`) so pytest does not warn about an
unknown marker. Kept in `tests/` (not `pyproject.toml`) because this slice's
write grant is `tests/**`, `src/gleipnir/preflight/**`, and
`bin/gleipnir-preflight` only.

Also skips collection of the broker MCP-SDK-dependent test module when the
`mcp` package is not importable. The broker layer (and its `FastMCP` tool-
surface test) runs only under the dedicated `broker` sandbox profile
(`gleipnir-sandbox-broker` image, which carries `mcp>=1.0,<2`). The lean
`python` self-host image deliberately has NO `mcp`; without this guard,
`test_broker_tool_surface.py`'s top-level `from mcp.server.fastmcp import
FastMCP` raises a collection error that aborts the ENTIRE python-profile run.
The stdlib-only broker tests (guards/platform/stdlib-only) still run everywhere.
"""

from __future__ import annotations

import importlib.util

# Skip-collect the MCP-SDK-dependent broker test where `mcp` isn't installed
# (the lean python self-host image). It runs fully under the broker profile.
collect_ignore = []
if importlib.util.find_spec("mcp") is None:
    collect_ignore.append("test_broker_tool_surface.py")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "hostonly: real-OS-permission tests that are only meaningful off-root "
        "(root bypasses permission bits); skipped under root / in-sandbox.",
    )
