"""Stdlib-only conformance check for `src/gleipnir/ledger/`.

Plan: `.gleipnir/plans/g4d-ledger-first-slice.md`, Assemble step 5 +
Stress-test check J. Mirrors `tests/test_bus_stdlib_only.py`, with one
deliberate difference: unlike the bus (whose D3 forbade HMAC/the verify
key), the ledger MAY import `hashlib`/`hmac` via `verify.marker`'s
primitives for the rate-table G-3.1 keyed digest (D2) — the rate table IS
authority-bearing config, unlike the bus's telemetry stream. So this test
does NOT forbid `hmac`; it only asserts no THIRD-PARTY top-level imports.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

LEDGER_DIR = Path(__file__).resolve().parents[1] / "src" / "gleipnir" / "ledger"


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


def _ledger_py_files() -> list[Path]:
    files = sorted(LEDGER_DIR.glob("*.py"))
    assert files, f"expected at least one .py file under {LEDGER_DIR}"
    return files


class TestLedgerPackageIsStdlibOnly:
    def test_no_non_stdlib_top_level_imports(self):
        stdlib = set(sys.stdlib_module_names)
        for py_file in _ledger_py_files():
            for root in _top_level_import_roots(py_file):
                if root in ("gleipnir", "__future__"):
                    continue
                assert root in stdlib, (
                    f"{py_file.name} imports non-stdlib module {root!r}; "
                    "the enforcement core is stdlib-only "
                    "(.gleipnir/decisions/runtime-and-deps.md)"
                )

    def test_only_the_expected_ledger_submodules_exist(self):
        names = {p.stem for p in _ledger_py_files()}
        assert {"__init__", "metric", "reduce", "ratetable", "reconcile"} <= names

    def test_metric_module_imports_no_hmac_or_hashlib(self):
        """The D3 honesty types themselves have no business touching crypto
        -- only `ratetable.py` (the digest machinery) does."""

        roots = _top_level_import_roots(LEDGER_DIR / "metric.py")
        assert "hmac" not in roots
        assert "hashlib" not in roots

    def test_reduce_module_imports_no_hmac_or_re(self):
        """The reduction path is pure telemetry reduction -- no crypto, no
        regex/string parsing of bus fields."""

        roots = _top_level_import_roots(LEDGER_DIR / "reduce.py")
        assert "hmac" not in roots
        assert "hashlib" not in roots
        assert "re" not in roots

    def test_ratetable_module_may_import_hmac_via_verify_marker(self):
        """The one deliberate exception to the bus's no-HMAC posture: the
        rate table is Tier-3 authority-bearing config, so its digest
        verification legitimately reuses `verify.marker`'s HMAC primitives."""

        source = (LEDGER_DIR / "ratetable.py").read_text()
        assert "gleipnir.verify.marker" in source
