"""Shared pytest configuration for the `tests/` suite.

Registers the `hostonly` marker (used by
`tests/test_preflight_probe_hostonly.py`) so pytest does not warn about an
unknown marker. Kept in `tests/` (not `pyproject.toml`) because this slice's
write grant is `tests/**`, `src/gleipnir/preflight/**`, and
`bin/gleipnir-preflight` only.

Also skips collection of the broker MCP-SDK-dependent test modules when the
`mcp` package is not importable. The broker layer (and its `FastMCP` tool-
surface test, plus the commit-guard test) runs only under the dedicated
`broker` sandbox profile (`gleipnir-sandbox-broker` image, which carries
`mcp>=1.0,<2`). The lean `python` self-host image deliberately has NO `mcp`;
without this guard, these modules' top-level `from mcp.server.fastmcp import
FastMCP` (or `from gleipnir.broker.git import mcp_server`, which imports it
transitively) would raise a collection error that aborts the ENTIRE
python-profile run. The stdlib-only broker tests (guards/platform/stdlib-only)
still run everywhere.
"""

from __future__ import annotations

import importlib.util

# Skip-collect the MCP-SDK-dependent broker tests where `mcp` isn't installed
# (the lean python self-host image). They run fully under the broker profile.
collect_ignore = []
if importlib.util.find_spec("mcp") is None:
    collect_ignore.append("test_broker_tool_surface.py")
    collect_ignore.append("test_broker_git_commit_guard.py")
    collect_ignore.append("test_broker_git_mcp_server.py")
    collect_ignore.append("test_broker_pm_mcp_server.py")
    collect_ignore.append("test_broker_run_manifest.py")
    # S6 (`.gleipnir/plans/pi-dev-replatform-s6.md`, AC-WIRE-1): the
    # pure-Python cross-profile wire-protocol confirmation also imports `mcp`
    # transitively (it spawns the real `git/mcp_server.py`). Same guard,
    # same reason.
    collect_ignore.append("test_broker_wire_protocol.py")
    # git-diff-distill (`.gleipnir/plans/git-diff-distill.md`, Decision 13 /
    # Assemble Step 1): the `git_diff` content-handler integration test
    # imports `mcp_server` transitively too. Deliberately NOT adding
    # `test_broker_git_content_handlers.py` here -- that file is stdlib-only
    # and is meant to run under the lean `python` profile as well.
    collect_ignore.append("test_broker_git_diff_distill.py")
    # `.gleipnir/plans/tier3-mcp-approval-launcher.md`, Assemble Step 1: the
    # approval-subsystem MCP wrapper test also imports `mcp` transitively
    # (`from gleipnir.approval import mcp_server` -> `from mcp.server.fastmcp
    # import FastMCP`). Same guard, same reason -- it runs fully under the
    # `broker` sandbox profile instead.
    collect_ignore.append("test_approval_mcp_server.py")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "hostonly: real-OS-permission tests that are only meaningful off-root "
        "(root bypasses permission bits); skipped under root / in-sandbox.",
    )
