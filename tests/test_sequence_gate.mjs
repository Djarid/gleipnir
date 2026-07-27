// Golden-fixture cross-language conformance test for the sequence-gate hook.
//
// Proves the TS/JS hook validates a marker MINTED BY PYTHON (byte-for-byte MAC
// contract) and rejects a one-byte-tampered copy. If this passes, the pre-tool
// gate can be trusted to accept genuine bridges and refuse forged ones.
//
// Run with:  node --test tests/test_sequence_gate.mjs
// (Node strips the .ts types on import; validateMarker is pure, no opencode.)

import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

import { validateMarker, isDelegationAllowed } from "../.gleipnir/plugins/sequence-gate.ts"

const here = dirname(fileURLToPath(import.meta.url))
const fixtures = join(here, "fixtures")

const KEY = readFileSync(join(fixtures, "golden_key.bin"))
const genuine = JSON.parse(readFileSync(join(fixtures, "golden_marker.json"), "utf8"))
const tampered = JSON.parse(readFileSync(join(fixtures, "golden_marker_tampered.json"), "utf8"))

// The fixtures were minted with minted_at=1000; use a `now` in-window so the
// MAC check (not freshness) is what these assert.
const NOW = 1001
const HUGE = 10 ** 12

test("validates a genuine Python-minted marker (byte-for-byte MAC contract)", () => {
  assert.equal(validateMarker(genuine, KEY, { maxAgeSeconds: HUGE, now: NOW }), true)
})

test("rejects a one-byte-tampered marker (state changed, mac reused)", () => {
  assert.equal(validateMarker(tampered, KEY, { maxAgeSeconds: HUGE, now: NOW }), false)
})

test("rejects a genuine marker under the wrong key", () => {
  const wrong = Buffer.from("not-the-golden-key", "utf8")
  assert.equal(validateMarker(genuine, wrong, { maxAgeSeconds: HUGE, now: NOW }), false)
})

test("rejects a stale marker (freshness)", () => {
  // genuine minted_at=1000; a now far past the max age must fail.
  assert.equal(validateMarker(genuine, KEY, { maxAgeSeconds: 60, now: 1000 + 999999 }), false)
})

test("rejects a future-dated marker", () => {
  assert.equal(validateMarker(genuine, KEY, { maxAgeSeconds: HUGE, now: 500 }), false)
})

test("allow-decision matches the bridge's allowed_agents list", () => {
  // golden marker: state=plan, allowed=["gleipnir-plan"]
  assert.equal(isDelegationAllowed(genuine, "gleipnir-plan"), true)
  assert.equal(isDelegationAllowed(genuine, "git-ops"), false)
  assert.equal(isDelegationAllowed(genuine, "gleipnir-code"), false)
})
