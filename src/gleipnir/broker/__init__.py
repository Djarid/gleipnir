"""Gleipnir broker layer.

`broker/` is the out-of-enforcement-core Tools-layer that hosts the MCP
(FastMCP) stdio servers -- `gleipnir-git` (`broker/git/`) and `gleipnir-pm`
(`broker/pm/`). Per `.gleipnir/decisions/runtime-and-deps.md`, this layer is
the ONE place the `mcp` SDK may be imported; the enforcement core
(`bus/`, `engine/`, `ledger/`, `preflight/`, `sandbox/`, `verify/`) stays
stdlib-only. Within `broker/`, `mcp` may be imported only by files literally
named `mcp_server.py` -- see `tests/test_broker_stdlib_only.py`.
"""

from __future__ import annotations
