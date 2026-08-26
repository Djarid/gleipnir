/**
 * marker.test.ts — the correctness arbiter for `verify/marker.ts` (plan
 * `.gleipnir/plans/pi-dev-replatform-s5.md` Assemble step 3a; success
 * criteria 2 + 3; D-S5-6=6a).
 *
 * TWO DISTINCT blocks, kept separate on purpose (D-S5-6 rationale: a
 * byte-drift failure must be diagnosable independently of a logic
 * regression):
 *
 *   1. The ported `StateMarker` UNIT suite — structural port of
 *      `tests/test_bridge.py`'s assertions, syntax-adapted to `node:test`
 *      (same idiom as `engine.test.ts`/`roleTable.test.ts`), exercised
 *      against LOCALLY-MINTED markers.
 *   2. The DISTINCT golden-vector CROSS-LANGUAGE class, modelled on
 *      `tests/test_sequence_gate.mjs`, reusing
 *      `tests/fixtures/golden_marker.json` / `golden_marker_tampered.json` /
 *      `golden_key.bin` IN PLACE (no copy) via a relative path from this
 *      file's own directory.
 */

import assert from "node:assert/strict";
import { describe, test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  STATE_MARKER_VERSION,
  DEFAULT_MAX_AGE_SECONDS,
  type StateMarker,
  StateMarkerError,
  KeyUnavailable,
  mintState,
  validateState,
  loadKey,
  canonicalSigningInput,
  stateMarkerFromJson,
  stateMarkerToJson,
} from "../src/verify/marker.ts";

const VERIFIER_KEY = Buffer.from("verifier-only-secret-key-not-on-agent-surface", "utf8");
const AGENT_GUESSED_KEY = Buffer.from("agent-guessed-key", "utf8");

// ---------------------------------------------------------------------------
// Block 1 — ported StateMarker unit suite (<- tests/test_bridge.py)
// ---------------------------------------------------------------------------

describe("StateMarker unit suite (ported from tests/test_bridge.py, locally-minted markers)", () => {
  test("test_genuine_marker_validates", () => {
    const m = mintState("plan", ["gleipnir-plan"], VERIFIER_KEY);
    assert.equal(validateState(m, VERIFIER_KEY), true);
  });

  test("test_marker_roundtrips_through_json", () => {
    const m = mintState("brainstorm", ["gleipnir-plan"], VERIFIER_KEY);
    const m2 = stateMarkerFromJson(stateMarkerToJson(m));
    assert.deepEqual(m2, m);
    assert.equal(validateState(m2, VERIFIER_KEY), true);
  });

  test("test_allowed_agents_order_does_not_affect_validity", () => {
    // The canonical signing input sorts allowed_agents, so the wire order of
    // an honestly-produced list does not matter.
    const m = mintState("git", ["git-ops"], VERIFIER_KEY);
    assert.equal(validateState(m, VERIFIER_KEY), true);
  });

  test("test_agent_fabricated_marker_fails", () => {
    const forged: StateMarker = {
      version: STATE_MARKER_VERSION,
      pipeline_state: "gate",
      allowed_agents: [],
      minted_at: 1_000_000,
      mac: "deadbeef".repeat(8),
    };
    assert.equal(validateState(forged, VERIFIER_KEY), false);
  });

  test("test_agent_mints_with_wrong_key_fails", () => {
    const m = mintState("plan", ["gleipnir-plan"], AGENT_GUESSED_KEY);
    assert.equal(validateState(m, VERIFIER_KEY), false);
  });

  test("test_one_byte_state_tamper_invalidates", () => {
    const genuine = mintState("plan", ["gleipnir-plan"], VERIFIER_KEY);
    const tampered: StateMarker = {
      ...genuine,
      pipeline_state: "code", // tampered: claim a different state
      mac: genuine.mac, // reuse the genuine MAC
    };
    assert.equal(validateState(tampered, VERIFIER_KEY), false);
  });

  test("test_one_byte_allowed_agents_tamper_invalidates", () => {
    const genuine = mintState("test", ["gleipnir-code"], VERIFIER_KEY);
    const tampered: StateMarker = {
      ...genuine,
      allowed_agents: ["git-ops"], // tampered: widen the allow set
      mac: genuine.mac,
    };
    assert.equal(validateState(tampered, VERIFIER_KEY), false);
  });

  test("test_added_allowed_agent_invalidates", () => {
    const genuine = mintState("spec_review", ["quality-reviewer"], VERIFIER_KEY);
    const tampered: StateMarker = {
      ...genuine,
      allowed_agents: [...genuine.allowed_agents, "git-ops"],
      mac: genuine.mac,
    };
    assert.equal(validateState(tampered, VERIFIER_KEY), false);
  });

  test("test_stale_marker_fails", () => {
    const old = mintState("plan", ["gleipnir-plan"], VERIFIER_KEY, 1000);
    assert.equal(
      validateState(old, VERIFIER_KEY, { maxAgeSeconds: 3600, now: 1_000_000 }),
      false,
    );
  });

  test("test_future_marker_fails", () => {
    const future = mintState("plan", ["gleipnir-plan"], VERIFIER_KEY, 2_000_000);
    assert.equal(validateState(future, VERIFIER_KEY, { now: 1_000_000 }), false);
  });

  test("test_wrong_version_fails", () => {
    const m = mintState("plan", ["gleipnir-plan"], VERIFIER_KEY);
    const bad: StateMarker = { ...m, version: 99 };
    assert.equal(validateState(bad, VERIFIER_KEY), false);
  });

  test("test_malformed_marker_json_raises", () => {
    assert.throws(() => stateMarkerFromJson("{not json"), StateMarkerError);
  });

  test("test_marker_missing_fields_raises", () => {
    assert.throws(
      () => stateMarkerFromJson(JSON.stringify({ version: 1 })),
      StateMarkerError,
    );
  });

  test("test_marker_wrong_types_raises", () => {
    assert.throws(
      () =>
        stateMarkerFromJson(
          JSON.stringify({
            version: 1,
            pipeline_state: "plan",
            allowed_agents: "not-a-list",
            minted_at: 1,
            mac: "abc",
          }),
        ),
      StateMarkerError,
    );
  });

  test("test_key_unavailable_no_path", () => {
    assert.throws(() => loadKey(undefined), KeyUnavailable);
  });

  test("test_key_unavailable_unreadable_path", () => {
    assert.throws(
      () => loadKey("/nonexistent/path/that/should/never/exist/gleipnir-key"),
      KeyUnavailable,
    );
  });

  test("test_canonical_signing_input_matches_the_frozen_byte_contract", () => {
    // Direct proof of idiom-table row 2's byte contract, independent of
    // mint/validate: [version, state, sorted(agents).join("\x1e"), minted_at]
    // .join("\x1f") — byte-identical to bridge.py/sequence-gate.ts.
    const input = canonicalSigningInput(1, "plan", ["gleipnir-plan"], 1000);
    assert.equal(input, "1\x1fplan\x1fgleipnir-plan\x1f1000");
  });

  test("DEFAULT_MAX_AGE_SECONDS and STATE_MARKER_VERSION are frozen to the oracle", () => {
    assert.equal(STATE_MARKER_VERSION, 1);
    assert.equal(DEFAULT_MAX_AGE_SECONDS, 3600);
  });
});

// ---------------------------------------------------------------------------
// Block 2 — DISTINCT golden-vector cross-language class (<- tests/test_sequence_gate.mjs)
// ---------------------------------------------------------------------------

describe("StateMarker golden-vector cross-language conformance (Python-minted fixtures, reused in place)", () => {
  const here = dirname(fileURLToPath(import.meta.url));
  // Reuse-in-place (D-S5-6 / plan Open Item 6): NOT copied under
  // pi-package/test/fixtures/ — read directly from the single source of
  // truth at tests/fixtures/, exactly as tests/test_sequence_gate.mjs does
  // (there: "../.gleipnir/plugins/..." + "fixtures/..."; here the relative
  // path from pi-package/test/ is "../../tests/fixtures/").
  const fixtures = join(here, "..", "..", "tests", "fixtures");

  const KEY = readFileSync(join(fixtures, "golden_key.bin"));
  const genuine: StateMarker = JSON.parse(
    readFileSync(join(fixtures, "golden_marker.json"), "utf8"),
  );
  const tampered: StateMarker = JSON.parse(
    readFileSync(join(fixtures, "golden_marker_tampered.json"), "utf8"),
  );

  // The fixtures were minted with minted_at=1000; use a `now` in-window so
  // the MAC check (not freshness) is what these assert — mirrors
  // test_sequence_gate.mjs's NOW=1001 / HUGE=1e12.
  const NOW = 1001;
  const HUGE = 10 ** 12;

  test("AC-GOLDEN-1: validates a genuine Python-minted marker (byte-for-byte MAC contract)", () => {
    assert.equal(validateState(genuine, KEY, { maxAgeSeconds: HUGE, now: NOW }), true);
  });

  test("AC-GOLDEN-2: rejects the one-byte-tampered marker (state changed, mac reused)", () => {
    assert.equal(validateState(tampered, KEY, { maxAgeSeconds: HUGE, now: NOW }), false);
  });

  test("AC-GOLDEN-3: rejects a genuine marker under the wrong key", () => {
    const wrong = Buffer.from("not-the-golden-key", "utf8");
    assert.equal(validateState(genuine, wrong, { maxAgeSeconds: HUGE, now: NOW }), false);
  });

  test("AC-GOLDEN-4: rejects a stale marker and a future-dated marker", () => {
    // stale: now far past minted_at + a small max age
    assert.equal(validateState(genuine, KEY, { maxAgeSeconds: 60, now: 1000 + 999_999 }), false);
    // future: now before minted_at
    assert.equal(validateState(genuine, KEY, { maxAgeSeconds: HUGE, now: 500 }), false);
  });
});
