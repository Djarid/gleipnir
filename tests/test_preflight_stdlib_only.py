"""Stdlib-only conformance check for `src/gleipnir/preflight/`.

Plan: `.gleipnir/plans/s2-g1-closure-first-slice.md`, Link "stdlib-only
(runtime-and-deps.md): confirmed the whole src/gleipnir/ core is stdlib-only
today; new module must stay so". Mirrors `tests/test_bus_stdlib_only.py`'s
grep/AST meta-test pattern.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PREFLIGHT_DIR = Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "preflight"


def _top_level_import_roots(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text())
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # relative import (e.g. `from .boundary import X`) -- an
                # intra-package reference, not an external dependency.
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _preflight_py_files() -> list[Path]:
    files = sorted(PREFLIGHT_DIR.glob("*.py"))
    assert files, f"expected at least one .py file under {PREFLIGHT_DIR}"
    return files


class TestPreflightPackageIsStdlibOnly:
    def test_no_non_stdlib_top_level_imports(self):
        stdlib = set(sys.stdlib_module_names)
        for py_file in _preflight_py_files():
            for root in _top_level_import_roots(py_file):
                if root in ("gleipnir", "__future__"):
                    continue
                assert root in stdlib, (
                    f"{py_file.name} imports non-stdlib module {root!r}; "
                    "the enforcement core is stdlib-only "
                    "(.gleipnir/decisions/runtime-and-deps.md)"
                )

    def test_preflight_never_reimplements_hmac_or_modifies_marker(self):
        """No marker code change (plan constraint): boundary.py may REUSE the
        existing `KEY_ENV_VAR` name from verify.marker, but this package must
        never import `hmac` directly (it delegates all keyed-verification
        concerns to the existing, unmodified marker module) nor redefine
        `load_key`/`mint`/`validate`."""
        for py_file in _preflight_py_files():
            roots = _top_level_import_roots(py_file)
            assert "hmac" not in roots, (
                f"{py_file.name} imports hmac directly -- the preflight boundary "
                "reuses verify.marker's KEY_ENV_VAR only; it does not "
                "reimplement keyed verification"
            )
            source = py_file.read_text()
            for forbidden in ("def load_key(", "def mint(", "def validate("):
                assert forbidden not in source, (
                    f"{py_file.name} redefines {forbidden.strip('( ')} -- "
                    "marker.py must not be duplicated"
                )

    def test_only_the_expected_preflight_submodules_exist(self):
        names = {p.stem for p in _preflight_py_files()}
        assert {"__init__", "boundary", "__main__"} <= names

    def test_no_os_access_usage_anywhere_in_the_package(self):
        """Reviewer-enforced constraint (plan Assemble step 3 / Execution
        Workflow item 3): `os.access` must never gate the verdict or the
        probe. Parses the AST for an actual `os.access(...)` CALL (not a
        docstring mention explaining why it's banned, which several
        docstrings legitimately do by name)."""
        for py_file in _preflight_py_files():
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                is_os_access = (
                    isinstance(func, ast.Attribute)
                    and func.attr == "access"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                )
                assert not is_os_access, (
                    f"{py_file.name} calls os.access(...) -- banned from the "
                    "decision path AND from gating the probe (real-uid "
                    "pitfalls, root-always-true behaviour)"
                )
