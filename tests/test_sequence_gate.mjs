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


// ---------------------------------------------------------------------------
// ARMING (default-OFF). The gate must be a pass-through unless a run is armed
// (GLEIPNIR_PIPELINE=on AND a bridge exists). These drive the real
// SequenceGate hook against a temp directory.
// ---------------------------------------------------------------------------

import { SequenceGate } from "../.gleipnir/plugins/sequence-gate.ts"
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { createHmac } from "node:crypto"

// Local mint mirroring the canonical signing input (the golden tests above
// prove this matches Python byte-for-byte).
function mintMarker(key, { state, agents, mintedAt }) {
  const agentsJoined = [...agents].sort().join("\x1e")
  const signing = ["1", state, agentsJoined, String(mintedAt)].join("\x1f")
  const mac = createHmac("sha256", key).update(signing, "utf8").digest("hex")
  return { version: 1, pipeline_state: state, allowed_agents: agents, minted_at: mintedAt, mac }
}

function makeRepo({ withBridge, bridgeObj } = {}) {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-gate-"))
  if (withBridge) {
    mkdirSync(join(dir, ".gleipnir", "var", "run"), { recursive: true })
    writeFileSync(join(dir, ".gleipnir", "var", "run", "pipeline-state.json"), JSON.stringify(bridgeObj))
  }
  return dir
}

async function runBefore(dir, subagent_type) {
  const hook = (await SequenceGate({ directory: dir }))["tool.execute.before"]
  await hook({ tool: "task" }, { args: { subagent_type } })
}

async function withEnv(vars, fn) {
  const saved = {}
  for (const [k, v] of Object.entries(vars)) { saved[k] = process.env[k]; if (v === undefined) delete process.env[k]; else process.env[k] = v }
  try { return await fn() } finally { for (const [k, v] of Object.entries(saved)) { if (v === undefined) delete process.env[k]; else process.env[k] = v } }
}

test("UNARMED (no GLEIPNIR_PIPELINE): pass-through — even an out-of-order delegation proceeds", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "brainstorm", agents: ["gleipnir-brainstorm"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge })
  try {
    await withEnv({ GLEIPNIR_PIPELINE: undefined, GLEIPNIR_MARKER_KEY_FILE: undefined }, async () => {
      // git-ops would be illegal at brainstorm, but unarmed => pass-through, no throw
      await runBefore(dir, "git-ops")
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test("UNARMED even with a missing bridge: pass-through, NOT fail-closed", async () => {
  const dir = makeRepo({ withBridge: false })
  try {
    await withEnv({ GLEIPNIR_PIPELINE: undefined, GLEIPNIR_MARKER_KEY_FILE: undefined }, async () => {
      await runBefore(dir, "gleipnir-code")  // no bridge, but unarmed => must NOT throw
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test("ARMED but no bridge yet: still pass-through (arming requires a run in progress)", async () => {
  const dir = makeRepo({ withBridge: false })
  const kf = join(dir, "key"); writeFileSync(kf, KEY)
  try {
    await withEnv({ GLEIPNIR_PIPELINE: "on", GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runBefore(dir, "git-ops")  // armed flag on, but no bridge => not a run => pass-through
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test("ARMED + valid bridge: ALLOWS the in-state delegation", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "brainstorm", agents: ["gleipnir-brainstorm"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge })
  const kf = join(dir, "key"); writeFileSync(kf, KEY)
  try {
    await withEnv({ GLEIPNIR_PIPELINE: "on", GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runBefore(dir, "gleipnir-brainstorm")  // allowed at brainstorm => no throw
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test("ARMED + valid bridge: ABORTS an out-of-order delegation", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "brainstorm", agents: ["gleipnir-brainstorm"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge })
  const kf = join(dir, "key"); writeFileSync(kf, KEY)
  try {
    await withEnv({ GLEIPNIR_PIPELINE: "on", GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await assert.rejects(runBefore(dir, "git-ops"))  // illegal at brainstorm => throw
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test("ARMED + tampered bridge: ABORTS (fail-closed within a run)", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "brainstorm", agents: ["gleipnir-brainstorm"], mintedAt: now })
  bridge.pipeline_state = "git"  // flip state, keep mac
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge })
  const kf = join(dir, "key"); writeFileSync(kf, KEY)
  try {
    await withEnv({ GLEIPNIR_PIPELINE: "on", GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await assert.rejects(runBefore(dir, "git-ops"))
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test("ARMED + bridge but NO key: ABORTS (fail-closed within a run)", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "brainstorm", agents: ["gleipnir-brainstorm"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge })
  try {
    await withEnv({ GLEIPNIR_PIPELINE: "on", GLEIPNIR_MARKER_KEY_FILE: undefined }, async () => {
      await assert.rejects(runBefore(dir, "gleipnir-brainstorm"))
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})


// ---------------------------------------------------------------------------
// Armed-run dogfood cross-language handshake (assertion 5, form 2 -- the
// LIVE-minted bridge, not just the frozen golden fixture above). Plan:
// `.gleipnir/plans/armed-run-dogfood.md` §2.3/§4 step 7/§5 assertion 5.
//
// `dogfood_bridge.json` is a Python-minted PLAN-state bridge produced by a
// live `Driver` driven to PLAN with `key_file=golden_key.bin` and
// `write_bridge(minted_at=1000)` (see
// `tests/test_armed_run_dogfood.py::test_live_driver_mint_at_plan_matches_the_committed_dogfood_fixture`,
// which asserts this file is byte-for-byte what that live driver path
// produces). Loaded here exactly like the golden-marker block above: same
// shared `golden_key.bin`, same symmetric freshness override for the fixed
// `minted_at=1000` (`now: 1001`, `maxAgeSeconds: HUGE`).
// ---------------------------------------------------------------------------

const dogfoodBridge = JSON.parse(readFileSync(join(fixtures, "dogfood_bridge.json"), "utf8"))

test("dogfood: validates the live-driver-minted PLAN bridge (byte-for-byte MAC contract)", () => {
  assert.equal(validateMarker(dogfoodBridge, KEY, { maxAgeSeconds: HUGE, now: NOW }), true)
})

test("dogfood: rejects a one-byte-tampered copy (state changed, mac reused)", () => {
  // Mirrors golden_marker_tampered.json's construction: flip pipeline_state,
  // keep the original mac -- the recomputed HMAC no longer matches.
  const tamperedDogfoodBridge = { ...dogfoodBridge, pipeline_state: "git" }
  assert.notEqual(tamperedDogfoodBridge.pipeline_state, dogfoodBridge.pipeline_state)
  assert.equal(validateMarker(tamperedDogfoodBridge, KEY, { maxAgeSeconds: HUGE, now: NOW }), false)
})

test("dogfood: allow-decision matches the bridge's allowed_agents list", () => {
  assert.equal(isDelegationAllowed(dogfoodBridge, "gleipnir-plan"), true)
  assert.equal(isDelegationAllowed(dogfoodBridge, "git-ops"), false)
})
