"""Shared pytest configuration for the `tests/` suite.

Registers the `hostonly` marker (used by
`tests/test_preflight_probe_hostonly.py`) so pytest does not warn about an
unknown marker. Kept in `tests/` (not `pyproject.toml`) because this slice's
write grant is `tests/**`, `src/gleipnir/preflight/**`, and
`bin/gleipnir-preflight` only.
"""

from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "hostonly: real-OS-permission tests that are only meaningful off-root "
        "(root bypasses permission bits); skipped under root / in-sandbox.",
    )
