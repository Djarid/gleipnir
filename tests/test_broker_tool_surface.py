"""Tool-surface conformance for the two broker MCP servers (T-D, supports T-A).

Plan: `.gleipnir/plans/broker-mcp.md`, Stress-test T-D (exactly 4+4 tools,
set equality so a 5th tool fails) + T-A(i) (no tool exposes a force
parameter -- force-push must be structurally ABSENT, not merely denied).
Target modules (do NOT exist yet -- this is the point, Axiom 1):

    src/gleipnir/broker/git/mcp_server.py   -> FastMCP("gleipnir-git")
    src/gleipnir/broker/pm/mcp_server.py    -> FastMCP("gleipnir-pm")

Introspected LIVE via `server.list_tools()` (per the verified environment
fact: returns `list[Tool]`, each with `.name` and `.inputSchema`, a
JSON-schema dict with parameter names under `inputSchema["properties"]`),
not by grepping source, so a tool registered via decorator is caught even
if a source-level grep would miss it.

ASSUMED ATTRIBUTE NAME (documented per this delegation's requirement): each
`mcp_server.py` module exposes its FastMCP instance as a module-level
attribute named `mcp` -- i.e. `mcp = FastMCP("gleipnir-git")` -- matching
the plan's Assemble Step 4 prose. `_get_server()` below falls back to
scanning the module namespace for the sole FastMCP instance if the
attribute isn't literally named `mcp`, but `mcp` is the preferred/assumed
name the implementer should match.
"""

from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP

# Top-level import: the broker package does not exist yet, so THIS IMPORT
# ITSELF is expected to fail at collection (ModuleNotFoundError) until the
# servers are implemented -- that failure is the point (Axiom 1).
from gleipnir.broker.git import mcp_server as git_mcp_server
from gleipnir.broker.pm import mcp_server as pm_mcp_server


EXPECTED_GIT_TOOLS = {"git_status", "git_diff", "commit_changes", "push_current_branch"}
EXPECTED_PM_TOOLS = {"issue_create", "issue_update", "issue_comment", "issue_close"}

FORBIDDEN_PARAM_NAMES = {"force", "--force", "-f"}


def _get_server(module) -> FastMCP:
    """Locate the module's FastMCP instance (see module docstring)."""
    preferred = getattr(module, "mcp", None)
    if isinstance(preferred, FastMCP):
        return preferred
    candidates = [v for v in vars(module).values() if isinstance(v, FastMCP)]
    assert len(candidates) == 1, (
        f"{module.__name__} must expose exactly one FastMCP instance "
        f"(module-level `mcp = FastMCP(...)` assumed); found {len(candidates)}"
    )
    return candidates[0]


def _tool_names(server: FastMCP) -> set[str]:
    tools = asyncio.run(server.list_tools())
    return {t.name for t in tools}


def _tool_param_names(server: FastMCP) -> set[str]:
    tools = asyncio.run(server.list_tools())
    names: set[str] = set()
    for tool in tools:
        props = (tool.inputSchema or {}).get("properties", {})
        names.update(props.keys())
    return names


class TestGitBrokerToolSurface:
    def test_exactly_the_four_git_tools_are_registered(self):
        server = _get_server(git_mcp_server)
        assert _tool_names(server) == EXPECTED_GIT_TOOLS, (
            "gleipnir-git must expose EXACTLY git_status, git_diff, "
            "commit_changes, push_current_branch -- no more, no less "
            "(T-D: a 5th tool must fail this test)"
        )

    def test_no_git_tool_exposes_a_force_parameter(self):
        server = _get_server(git_mcp_server)
        params = _tool_param_names(server)
        hit = params & FORBIDDEN_PARAM_NAMES
        assert not hit, (
            f"git broker tool surface exposes forbidden param(s) {hit} -- "
            "force-push must be structurally ABSENT (T-A), not merely denied"
        )

    def test_run_git_refuses_hook_bypass_flags(self):
        # The one hard broker invariant: an agent must never be able to skip
        # the operator's git hooks (a Tier-3/G-2 capability-escape). Legitimate
        # argvs pass; --no-verify / -n / -c core.hooksPath are refused at the
        # _run_git choke point.
        reject = git_mcp_server._rejects_hook_bypass
        assert reject(["commit", "-m", "msg"]) is None
        assert reject(["push", "origin", "main"]) is None
        assert reject(["add", "-A"]) is None
        assert reject(["commit", "--no-verify", "-m", "msg"]) is not None
        assert reject(["commit", "-n", "-m", "msg"]) is not None
        assert reject(["-c", "core.hooksPath=/dev/null", "commit", "-m", "m"]) is not None
        assert reject(["-c", "core.hooksPath=", "commit", "-m", "m"]) is not None


class TestPmBrokerToolSurface:
    def test_exactly_the_four_pm_tools_are_registered(self):
        server = _get_server(pm_mcp_server)
        assert _tool_names(server) == EXPECTED_PM_TOOLS, (
            "gleipnir-pm must expose EXACTLY issue_create, issue_update, "
            "issue_comment, issue_close -- no more, no less (T-D)"
        )

    def test_no_pm_tool_exposes_a_force_parameter(self):
        server = _get_server(pm_mcp_server)
        params = _tool_param_names(server)
        hit = params & FORBIDDEN_PARAM_NAMES
        assert not hit, f"pm broker tool surface exposes forbidden param(s) {hit}"
