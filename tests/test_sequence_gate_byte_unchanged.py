"""Seam 7 Phase 2 byte-unchanged proof for sequence-gate.ts.

Spec: `.gleipnir/plans/seam7-seam8-wiring.md` Assemble Phase 2 + the
delegation's "Verify and report" instruction ("confirm sequence-gate.ts is
byte-unchanged (diff/hash evidence, not just a claim)"). `gleipnir-code` has
NO write grant to `.gleipnir/plugins/sequence-gate.ts` and was instructed not
to attempt to edit it -- this test is the executable proof of that, run via
`bin/gleipnir-sandbox test` (the one execution path this delegation's grant
actually permits; the TS test suite itself is host-run and outside this
grant, so this stdlib-only Python golden-hash check is the REAL, agent-
executed evidence for this specific claim, mirroring the golden-hash pattern
`tests/test_advance_entrypoint.py::test_core_engine_files_byte_unchanged`
already uses for the three Python engine core files).

The golden hash below was captured by first asserting against an obviously
wrong placeholder, running `bin/gleipnir-sandbox test`, and reading the real
digest out of the failing assertion message -- the same technique
`test_advance_entrypoint.py`'s own module docstring documents. If a FUTURE,
reviewed change legitimately touches `sequence-gate.ts`, update this hash
deliberately -- never let it drift silently.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def _sequence_gate_ts_path() -> Path:
    # tests/ -> repo root -> .gleipnir/plugins/sequence-gate.ts
    return (
        Path(__file__).resolve().parents[1]
        / ".gleipnir"
        / "plugins"
        / "sequence-gate.ts"
    )


# Captured at Seam-7-Phase-2 authorship time (this delegation made ZERO edits
# to this file -- it only reads two of its three exported bindings from a
# sibling module, advance-hook.ts).
_EXPECTED_SHA256 = "c4a59563df32e77ad7873e3c6ad1bb11d9a63a6985019e8fcf9d1d48bc229422"


def test_sequence_gate_ts_is_byte_unchanged():
    path = _sequence_gate_ts_path()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == _EXPECTED_SHA256, (
        f".gleipnir/plugins/sequence-gate.ts content changed (sha256 {digest} != "
        f"golden {_EXPECTED_SHA256}) -- gleipnir-code has no write grant to this "
        "file and this delegation (Seam 7 Phase 2) must not edit it. If this is a "
        "DIFFERENT, reviewed, Tier-3-authored change intentionally touching this "
        "file, update the golden hash deliberately -- never let it drift silently."
    )
