"""Stdlib-only + no-HMAC/no-verify-key conformance check for `src/gleipnir/bus/`.

Plan: `.gleipnir/plans/g4-bus-first-slice.md`, Stress-test check 11.
Candidate C-3 meta-test per `.gleipnir/decisions/runtime-and-deps.md`
§Conformance: grep/AST the package for non-stdlib top-level imports.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BUS_DIR = Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "bus"


def _top_level_import_roots(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text())
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _bus_py_files() -> list[Path]:
    files = sorted(BUS_DIR.glob("*.py"))
    assert files, f"expected at least one .py file under {BUS_DIR}"
    return files


class TestBusPackageIsStdlibOnly:
    def test_no_non_stdlib_top_level_imports(self):
        stdlib = set(sys.stdlib_module_names)
        for py_file in _bus_py_files():
            for root in _top_level_import_roots(py_file):
                if root in ("gleipnir", "__future__"):
                    continue
                assert root in stdlib, (
                    f"{py_file.name} imports non-stdlib module {root!r}; "
                    "the enforcement core is stdlib-only "
                    "(.gleipnir/decisions/runtime-and-deps.md)"
                )

    def test_bus_never_imports_verify_marker_or_hmac(self):
        for py_file in _bus_py_files():
            roots = _top_level_import_roots(py_file)
            assert "hmac" not in roots, (
                f"{py_file.name} imports hmac -- D3: no HMAC/S-2 key in the "
                "telemetry path this slice"
            )
            source = py_file.read_text()
            assert "verify.marker" not in source, (
                f"{py_file.name} references verify.marker -- D3 forbids the "
                "bus from importing the S-2 verifier key module"
            )
            assert "verify import" not in source

    def test_only_the_expected_bus_submodules_exist(self):
        names = {p.stem for p in _bus_py_files()}
        assert {"__init__", "events", "emit"} <= names
