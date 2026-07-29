"""Broker-scoped `mcp`-import-boundary conformance test (T-F).

Plan: `.gleipnir/plans/broker-mcp.md`, Link L6 + Stress-test T-F. Mirrors
`tests/test_bus_stdlib_only.py` / `tests/test_preflight_stdlib_only.py`'s
grep/AST meta-test pattern, but is scoped differently from those: the
existing per-directory stdlib-only tests each hardcode their OWN single
`*_DIR` (`bus/`, `ledger/`, `preflight/`) and glob only that directory --
none of them scans the whole `src/gleipnir/` tree or looks at `broker/` at
all (verified this session, plan Link L6). Introducing `import mcp` under
`broker/` would NOT silently fail any of those three existing meta-tests.
This test closes that gap explicitly rather than relying on omission:

  (i) POSITIVE guard that the carve-out hasn't leaked: every existing
      enforcement-core package under `src/gleipnir/` (every subpackage
      EXCEPT `broker/`) never imports `mcp` at module top level. This is
      real and enforceable TODAY, before `broker/` exists -- it protects
      the existing core the whole time this feature is being built.

  (ii) The `broker/**`-internal boundary: within `src/gleipnir/broker/`,
      `mcp` may be imported ONLY by files literally named `mcp_server.py`.
      `guards.py` and `platform.py` must stay stdlib-only so they remain
      unit-testable without the `mcp` SDK installed.

Test-first note (Axiom 1): `src/gleipnir/broker/` does not exist yet, so
part (ii) below asserts on its presence and is EXPECTED TO FAIL until the
broker package is implemented -- that failure is the point. Part (i) is a
real, already-enforceable invariant over the EXISTING core packages and is
expected to pass today; it does not depend on broker/ existing.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_GLEIPNIR_DIR = Path(__file__).resolve().parents[1] / "src" / "gleipnir"
BROKER_DIR = SRC_GLEIPNIR_DIR / "broker"

# Packages this test currently knows must exist and must stay `mcp`-free.
# _core_package_dirs() is dynamic (iterdir-based, excludes "broker"), so a
# newly added core package is picked up automatically; this set is a pinned
# floor so silent removal of one of these dirs is also caught.
EXPECTED_CORE_PACKAGES = {"bus", "engine", "ledger", "preflight", "sandbox", "verify"}


def _top_level_import_roots(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text())
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import -- intra-package, not third-party
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _core_package_dirs() -> list[Path]:
    """Every immediate subpackage of src/gleipnir/ EXCEPT broker/."""
    dirs = [
        p
        for p in SRC_GLEIPNIR_DIR.iterdir()
        if p.is_dir() and p.name != "broker" and p.name != "__pycache__"
    ]
    assert dirs, f"expected at least one core subpackage under {SRC_GLEIPNIR_DIR}"
    return sorted(dirs)


def _py_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


# ---------------------------------------------------------------------------
# (i) mcp has not leaked into the enforcement core
# ---------------------------------------------------------------------------


class TestEnforcementCoreNeverImportsMcp:
    def test_no_core_package_imports_mcp(self):
        for pkg_dir in _core_package_dirs():
            for py_file in _py_files(pkg_dir):
                roots = _top_level_import_roots(py_file)
                assert "mcp" not in roots, (
                    f"{py_file.relative_to(SRC_GLEIPNIR_DIR)} imports `mcp` -- "
                    "the mcp SDK carve-out (.gleipnir/decisions/"
                    "runtime-and-deps.md) applies to broker/** ONLY; it must "
                    "not leak into the enforcement core"
                )

    def test_core_package_set_includes_the_expected_floor(self):
        names = {p.name for p in _core_package_dirs()}
        assert EXPECTED_CORE_PACKAGES <= names


# ---------------------------------------------------------------------------
# (ii) within broker/, mcp is imported ONLY by mcp_server.py modules
# ---------------------------------------------------------------------------


class TestBrokerMcpImportBoundary:
    def test_broker_package_exists(self):
        """Test-first (Axiom 1): broker/ does not exist yet, so this FAILS
        until Assemble Step 4 implements it. That failure is expected and
        is the point of writing this test before the implementation."""
        assert BROKER_DIR.is_dir(), (
            f"{BROKER_DIR} does not exist yet -- expected until the broker "
            "feature (.gleipnir/plans/broker-mcp.md) is implemented"
        )

    def test_mcp_imported_only_by_mcp_server_modules(self):
        assert BROKER_DIR.is_dir(), f"{BROKER_DIR} does not exist yet"
        broker_files = _py_files(BROKER_DIR)
        assert broker_files, f"expected at least one .py file under {BROKER_DIR}"
        for py_file in broker_files:
            roots = _top_level_import_roots(py_file)
            if "mcp" in roots:
                assert py_file.name == "mcp_server.py", (
                    f"{py_file.relative_to(SRC_GLEIPNIR_DIR)} imports `mcp` "
                    "but is not named mcp_server.py -- only the FastMCP "
                    "server modules may import the SDK; guards.py/"
                    "platform.py must stay stdlib-only"
                )

    def test_guards_and_platform_modules_are_present_and_stdlib_only(self):
        guards = BROKER_DIR / "git" / "guards.py"
        platform = BROKER_DIR / "pm" / "platform.py"
        for module_path in (guards, platform):
            assert module_path.is_file(), f"expected {module_path} to exist"
            roots = _top_level_import_roots(module_path)
            assert "mcp" not in roots, (
                f"{module_path.relative_to(SRC_GLEIPNIR_DIR)} imports `mcp` -- "
                "it must remain unit-testable without the mcp SDK installed"
            )
