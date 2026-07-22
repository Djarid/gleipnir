# Gleipnir G-3.1 — Keyed Verification Marker

Gleipnir's own implementation of spec requirement **G-3.1** (build-order step
2). Built from the spec, not inherited from AETOS.

## What it does

Replaces a forgeable "tests passed" marker with one that **only the verifier
process can produce**, because minting requires an HMAC key the agent never
holds. Validation is **fail-closed**: an invalid, missing, stale, or
tree-mismatched marker means *run the tests*.

- `marker.py` — the mechanism: `compute_tree_hash`, `mint` (verifier-only,
  needs the key), `validate` (constant-time HMAC + tree-binding + freshness),
  `load_key` (fail-closed key read).
- `__main__.py` — the verifier CLI:
  - `verify -- <test cmd>` runs the tests and mints a marker **only on green**.
  - `check` validates an existing marker, exit 0 = genuine, non-zero = run tests.

## Why an agent can't forge it

- **No key, no MAC.** The key is read from `GLEIPNIR_MARKER_KEY_FILE`, which
  lives under the S-2 boundary (read-only mount / outside the agent surface
  once closure lands). An agent can write a JSON file that looks like a marker,
  but without the key its HMAC won't validate.
- **Tree-bound.** The MAC covers a hash of the source/test/config tree, so a
  one-byte change, an added file, or a deleted file all invalidate a genuine
  marker. A MAC cannot be lifted onto a different tree.
- **Fresh.** Stale or future-dated markers fail.

## Usage

```sh
# Verifier process (holds the key):
GLEIPNIR_MARKER_KEY_FILE=/mount/keys/marker.key \
  python -m gleipnir.verify --root . verify -- pytest -q

# Later, decide whether to re-run:
GLEIPNIR_MARKER_KEY_FILE=/mount/keys/marker.key \
  python -m gleipnir.verify --root . check   # exit 0 => skip, non-0 => run
```

## Status

Real and tested (`tests/test_marker.py`, `tests/test_cli.py`), covering the
spec's G-3.1 conformance [D] cases: agent-fabricated marker fails, wrong-key
mint fails, MAC-lift fails, one-byte mutation invalidates, red run mints
nothing, missing marker fails closed.

**Not yet closed:** the key currently lives wherever `GLEIPNIR_MARKER_KEY_FILE`
points. Its unreachability from the agent surface is only real once the S-2
substrate (build-order step 1 decision: container read-only mount) is built and
S-3 preflight verifies it. Until then the mechanism is sound but its key
location is not yet boundary-enforced.
