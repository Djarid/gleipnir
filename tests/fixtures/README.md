# Test fixtures

## Golden cross-language MAC fixtures (sequence-gate)

`golden_key.bin`, `golden_marker.json`, `golden_marker_tampered.json` prove the
TypeScript sequence-gate hook (`.gleipnir/plugins/sequence-gate.ts`) validates a
`StateMarker` **minted by Python** (`src/gleipnir/engine/bridge.py`) byte-for-byte,
and rejects a one-byte-tampered copy. See `tests/test_sequence_gate.mjs`.

**`golden_key.bin` is NOT a secret.** It is a deliberately-throwaway test
constant (`golden-fixture-key-do-not-use-in-prod`). Real verifier keys live
outside the repo under the S-2 boundary (`GLEIPNIR_MARKER_KEY_FILE`) and are
gitignored (`.gleipnir/keys/*.key`). This fixture key exists only so the
conformance test is reproducible and self-contained.

Regenerate with:

    PYTHONPATH=src python -c "
    from gleipnir.engine.bridge import mint_state
    import dataclasses, pathlib
    KEY=b'golden-fixture-key-do-not-use-in-prod'
    m=mint_state('plan',['gleipnir-plan'],KEY,minted_at=1000)
    p=pathlib.Path('tests/fixtures')
    (p/'golden_key.bin').write_bytes(KEY)
    (p/'golden_marker.json').write_text(m.to_json())
    (p/'golden_marker_tampered.json').write_text(dataclasses.replace(m,pipeline_state='git').to_json())
    "
