// Conformance test for the Seam 7 Phase 2 post-tool advance TRIGGER.
//
// Spec: `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble "Phase 2 — TS
// post-tool handler (the trigger)"; Stress-test criteria 3 (unarmed no-op)
// and 4 (fail-closed on subprocess error).
//
// Mirrors the two established host-run precedents in this repo:
//   * `tests/test_sequence_gate.mjs` — the bridge-arming / MAC-validation
//     temp-dir approach (mintMarker/makeRepo/withEnv).
//   * `tests/test_git_guard.mjs` — the stub-`bin/gleipnir-preflight`-CLI
//     approach for asserting exit-code -> decision behavior without a real
//     preflight run.
//
// **This file is authored by `gleipnir-code` but, per this repo's
// documented host-run-precedent (`.gleipnir/plans/config-scan-precommit-hook.md`
// "Host-run-precedent note"), CANNOT be executed by `gleipnir-code` itself.**
// `gleipnir-code`'s bash grant is `bin/gleipnir-sandbox test|lint` exact-match
// only (tightened when the S-2 sandbox landed); it denies `node*`/`sh*`/
// `bash*`/`*`. Run this file the same way `test_sequence_gate.mjs` /
// `test_git_guard.mjs` are already run — by the build-session/orchestrator
// (which holds `bash`), OUTSIDE the sandbox (the python sandbox image has no
// node):
//
//   node --experimental-strip-types --test tests/test_advance_hook.mjs
//
// (Node 22.6+ for `--experimental-strip-types`, needed because this suite
// imports two `.ts` files. Zero third-party deps — node builtins only.)

import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"
import { mkdtempSync, mkdirSync, writeFileSync, chmodSync, rmSync, existsSync } from "node:fs"
import { tmpdir } from "node:os"
import { createHmac } from "node:crypto"

import {
  AdvanceHook,
  AdvanceHookAbort,
  PreflightUnavailable,
  shouldTriggerAdvance,
  buildAdvanceArgv,
  runAdvance,
} from "../.gleipnir/plugins/advance-hook.ts"
import { isDelegationAllowed } from "../.gleipnir/plugins/sequence-gate.ts"

const here = dirname(fileURLToPath(import.meta.url))
const ADVANCE_HOOK_TS_PATH = join(here, "..", ".gleipnir", "plugins", "advance-hook.ts")

const KEY = Buffer.from("advance-hook-test-key-not-the-golden-key", "utf8")
const PIPELINE_ID = "pl-advance-hook-phase2-test-1"

// ---------------------------------------------------------------------------
// Shared fixture builders (mirrors test_sequence_gate.mjs's mintMarker +
// test_git_guard.mjs's stub-CLI approach, combined for this hook's needs)
// ---------------------------------------------------------------------------

function mintMarker(key, { state, agents, mintedAt }) {
  const agentsJoined = [...agents].sort().join("\x1e")
  const signing = ["1", state, agentsJoined, String(mintedAt)].join("\x1f")
  const mac = createHmac("sha256", key).update(signing, "utf8").digest("hex")
  return { version: 1, pipeline_state: state, allowed_agents: agents, minted_at: mintedAt, mac }
}

// Build a temp "repo" dir with: (a) an optional bridge file, (b) an optional
// key file, (c) an optional stub `bin/gleipnir-preflight` that only accepts
// the `advance` subcommand, exits `stubExitCode`, and (when it runs)
// captures its full argv (one arg per line) to `captured-argv.txt` AND
// drains+captures whatever was piped to its stdin (if anything) to
// `captured-stdin.txt`, both inside the same dir, so a test can assert both
// the exact CLI shape AND the exact stdin payload the hook built.
function makeRepo({ withBridge, bridgeObj, withStub, stubExitCode = 0 } = {}) {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-advance-hook-"))
  if (withBridge) {
    mkdirSync(join(dir, ".gleipnir", "var", "run"), { recursive: true })
    writeFileSync(join(dir, ".gleipnir", "var", "run", "pipeline-state.json"), JSON.stringify(bridgeObj))
  }
  if (withStub) {
    mkdirSync(join(dir, "bin"), { recursive: true })
    const stub = join(dir, "bin", "gleipnir-preflight")
    const capture = join(dir, "captured-argv.txt")
    const stdinCapture = join(dir, "captured-stdin.txt")
    writeFileSync(
      stub,
      `#!/bin/sh\n` +
        `# stub gleipnir-preflight for advance-hook tests\n` +
        `[ "$1" = "advance" ] || { echo "stub: expected advance, got $1" >&2; exit 99; }\n` +
        `printf '%s\\n' "$@" > "${capture}"\n` +
        `cat > "${stdinCapture}"\n` +
        `exit ${stubExitCode}\n`,
    )
    chmodSync(stub, 0o755)
  }
  return dir
}

function captureFilePath(dir) {
  return join(dir, "captured-argv.txt")
}

function stdinCaptureFilePath(dir) {
  return join(dir, "captured-stdin.txt")
}

// `outputText`, when provided, becomes `output.output` — the field the
// corrected hook reads the delegation's RETURNED TEXT from (see
// advance-hook.ts's COMPLETION-PASS CORRECTION note; confirmed against
// `.gleipnir/plans/hook-probe-findings.md` lines 86-104). `subagent_type`
// is passed via `input.args`, matching the AFTER-hook's real signature
// (`input: { tool, args }`, NOT `output: { args }` — the pre-existing bug
// this delegation fixes).
async function runAfter(dir, tool, subagent_type, outputText) {
  const hook = (await AdvanceHook({ directory: dir }))["tool.execute.after"]
  await hook({ tool, args: { subagent_type } }, { output: outputText })
}

async function withEnv(vars, fn) {
  const saved = {}
  for (const [k, v] of Object.entries(vars)) {
    saved[k] = process.env[k]
    if (v === undefined) delete process.env[k]
    else process.env[k] = v
  }
  try {
    return await fn()
  } finally {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k]
      else process.env[k] = v
    }
  }
}

const ARMED_ENV_BASE = { GLEIPNIR_PIPELINE: "on", GLEIPNIR_PIPELINE_ID: PIPELINE_ID }

// ---------------------------------------------------------------------------
// Stress-test #3: unarmed => pure pass-through, no shell-out, no bridge
// write, no fetch. The stub is set to exit 1 (a code that WOULD throw if
// ever invoked) precisely so a missing throw + a missing capture file
// together prove the stub was never run, not merely that its result was
// ignored.
// ---------------------------------------------------------------------------

test("UNARMED (no GLEIPNIR_PIPELINE): pass-through, never shells out", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 1 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv(
      { GLEIPNIR_PIPELINE: undefined, GLEIPNIR_PIPELINE_ID: undefined, GLEIPNIR_MARKER_KEY_FILE: kf },
      async () => {
        await runAfter(dir, "task", "gleipnir-code") // matching delegation, but unarmed
      },
    )
    assert.equal(existsSync(captureFilePath(dir)), false, "the stub must never have run")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("UNARMED even with a missing bridge: pass-through, NOT fail-closed", async () => {
  const dir = makeRepo({ withBridge: false, withStub: true, stubExitCode: 1 })
  try {
    await withEnv(
      { GLEIPNIR_PIPELINE: undefined, GLEIPNIR_PIPELINE_ID: undefined, GLEIPNIR_MARKER_KEY_FILE: undefined },
      async () => {
        await runAfter(dir, "task", "gleipnir-code")
      },
    )
    assert.equal(existsSync(captureFilePath(dir)), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED but no bridge yet: still pass-through (arming requires a run in progress)", async () => {
  const dir = makeRepo({ withBridge: false, withStub: true, stubExitCode: 1 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", "gleipnir-code")
    })
    assert.equal(existsSync(captureFilePath(dir)), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED but tool is not 'task': pass-through, never validates the bridge or shells out", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 1 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "read", "gleipnir-code") // not a task tool => out of scope
    })
    assert.equal(existsSync(captureFilePath(dir)), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// D6: wrong subagent_type for the bridge's current state => no-op, not an
// error (distinct from "unarmed" — this IS an armed run with a valid bridge).
// ---------------------------------------------------------------------------

test("ARMED + valid bridge + subagent_type NOT the bound role for the state: no-op (D6)", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 1 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", "git-ops") // bound role at TEST is gleipnir-code, not git-ops
    })
    assert.equal(existsSync(captureFilePath(dir)), false, "wrong-role completion must not trigger advance")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + valid bridge + missing subagent_type: no-op, not an abort", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 1 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", undefined)
    })
    assert.equal(existsSync(captureFilePath(dir)), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// The armed, matching, real-shell-out path (success + Stress-test #4
// fail-closed-on-error)
// ---------------------------------------------------------------------------

test("ARMED + matching delegation + advance exits 0: resolves without throwing, shells out with the right argv", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", "gleipnir-code") // must NOT throw
    })
    const captured = readFileSync(captureFilePath(dir), "utf8").trim().split("\n")
    assert.equal(captured[0], "advance")
    assert.equal(captured[1], "--pipeline-id")
    assert.equal(captured[2], PIPELINE_ID)
    assert.equal(captured[3], "--bridge-path")
    assert.ok(captured[4].endsWith(join(".gleipnir", "var", "run", "pipeline-state.json")))
    assert.equal(captured[5], "--key-file")
    assert.equal(captured[6], kf)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + matching delegation + advance exits non-zero: THROWS (Stress-test #4, fail-closed)", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 1 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await assert.rejects(runAfter(dir, "task", "gleipnir-code"), AdvanceHookAbort)
    })
    // The delegation must NOT silently proceed: the abort must have actually
    // been thrown (asserted above) — and the stub DID run (proving this is a
    // "ran, then correctly failed closed on its result" case, not a
    // never-ran no-op, which the earlier tests already cover separately).
    assert.equal(existsSync(captureFilePath(dir)), true)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + tampered bridge: THROWS before ever reaching the shell-out", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  bridge.pipeline_state = "git" // flip state, keep mac -- classic one-byte tamper
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await assert.rejects(runAfter(dir, "task", "gleipnir-code"), AdvanceHookAbort)
    })
    assert.equal(existsSync(captureFilePath(dir)), false, "must fail closed before shelling out")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + bridge but NO key file configured: THROWS (fail-closed)", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: undefined }, async () => {
      await assert.rejects(runAfter(dir, "task", "gleipnir-code"), AdvanceHookAbort)
    })
    assert.equal(existsSync(captureFilePath(dir)), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + matching + no GLEIPNIR_PIPELINE_ID configured: THROWS (misconfiguration, fail-closed)", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv(
      { GLEIPNIR_PIPELINE: "on", GLEIPNIR_PIPELINE_ID: undefined, GLEIPNIR_MARKER_KEY_FILE: kf },
      async () => {
        await assert.rejects(runAfter(dir, "task", "gleipnir-code"), /GLEIPNIR_PIPELINE_ID/)
      },
    )
    assert.equal(existsSync(captureFilePath(dir)), false, "must fail closed before shelling out")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + matching + preflight CLI missing: THROWS PreflightUnavailable, not a generic abort", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: false }) // no stub at all
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await assert.rejects(runAfter(dir, "task", "gleipnir-code"), (err) => {
        assert.ok(err instanceof PreflightUnavailable, "must be PreflightUnavailable, not a plain abort")
        assert.doesNotMatch(err.message, /exited/) // NOT a policy/verdict outcome
        return true
      })
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + matching + preflight CLI present but not executable: PreflightUnavailable", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  chmodSync(join(dir, "bin", "gleipnir-preflight"), 0o644) // present but not +x
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await assert.rejects(runAfter(dir, "task", "gleipnir-code"), PreflightUnavailable)
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// Reviewer-transcript capture (closes quality-review Finding A).
//
// A completed `quality-reviewer` task delegation's RETURNED TEXT
// (`output.output`, per the corrected hook signature — see advance-hook.ts's
// COMPLETION-PASS CORRECTION note, sourced from
// `.gleipnir/plans/hook-probe-findings.md` lines 86-104) must be captured
// and forwarded VERBATIM over stdin to `bin/gleipnir-preflight advance
// --reviewer-transcript-stdin`, ONLY for a SPEC_REVIEW/QUALITY-bound
// delegation from the LITERAL `quality-reviewer` subagent — never for a
// different subagent_type, and never for a TEST-state delegation.
// ---------------------------------------------------------------------------

test("ARMED + quality-reviewer completion at QUALITY state: captures output.output and forwards it via --reviewer-transcript-stdin + stdin", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "quality", agents: ["quality-reviewer"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  const transcriptText = "SPEC-CONFORM: PASS\nBLAST-RADIUS: PASS\nAPPROVED\n"
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", "quality-reviewer", transcriptText) // must NOT throw
    })
    const captured = readFileSync(captureFilePath(dir), "utf8").trim().split("\n")
    assert.ok(
      captured.includes("--reviewer-transcript-stdin"),
      "argv must include the --reviewer-transcript-stdin flag",
    )
    const capturedStdin = readFileSync(stdinCaptureFilePath(dir), "utf8")
    assert.equal(capturedStdin, transcriptText, "stdin payload must be the captured text VERBATIM")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + quality-reviewer completion at SPEC_REVIEW state: same capture+forward behavior", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "spec_review", agents: ["quality-reviewer"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  const transcriptText = "SPEC-CONFORM: PASS\n"
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", "quality-reviewer", transcriptText)
    })
    const captured = readFileSync(captureFilePath(dir), "utf8").trim().split("\n")
    assert.ok(captured.includes("--reviewer-transcript-stdin"))
    assert.equal(readFileSync(stdinCaptureFilePath(dir), "utf8"), transcriptText)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + DIFFERENT subagent_type (not quality-reviewer) at a SPEC_REVIEW-bound state: never captures a transcript", async () => {
  const now = Math.floor(Date.now() / 1000)
  // Contrived allowed_agents (both roles bound at spec_review) so
  // shouldTriggerAdvance/D6 passes for "gleipnir-plan" too -- this isolates
  // the SECOND, independent literal-"quality-reviewer" check from the D6
  // role-check, proving it is a genuinely separate gate, not a restatement.
  const bridge = mintMarker(KEY, {
    state: "spec_review",
    agents: ["quality-reviewer", "gleipnir-plan"],
    mintedAt: now,
  })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      await runAfter(dir, "task", "gleipnir-plan", "some self-report text, not a reviewer verdict\n")
    })
    const captured = readFileSync(captureFilePath(dir), "utf8").trim().split("\n")
    assert.ok(
      !captured.includes("--reviewer-transcript-stdin"),
      "argv must NOT include --reviewer-transcript-stdin for a non-quality-reviewer completion",
    )
    assert.equal(
      readFileSync(stdinCaptureFilePath(dir), "utf8"),
      "",
      "stdin must be empty -- no transcript captured for a non-quality-reviewer subagent_type",
    )
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + gleipnir-code completion at TEST state: unaffected by the transcript-capture path", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "test", agents: ["gleipnir-code"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      // Even if the delegation's "output" happens to carry text (any task
      // returns SOME text), a TEST-state gleipnir-code completion must never
      // be treated as a reviewer transcript.
      await runAfter(dir, "task", "gleipnir-code", "sandbox test run finished, exit 0\n")
    })
    const captured = readFileSync(captureFilePath(dir), "utf8").trim().split("\n")
    assert.ok(!captured.includes("--reviewer-transcript-stdin"))
    assert.equal(readFileSync(stdinCaptureFilePath(dir), "utf8"), "")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ARMED + quality-reviewer completion at QUALITY state but output.output is NOT a string: THROWS fail-closed, never shells out with an empty/absent deposit", async () => {
  const now = Math.floor(Date.now() / 1000)
  const bridge = mintMarker(KEY, { state: "quality", agents: ["quality-reviewer"], mintedAt: now })
  const dir = makeRepo({ withBridge: true, bridgeObj: bridge, withStub: true, stubExitCode: 0 })
  const kf = join(dir, "key")
  writeFileSync(kf, KEY)
  try {
    await withEnv({ ...ARMED_ENV_BASE, GLEIPNIR_MARKER_KEY_FILE: kf }, async () => {
      // outputText left undefined -- output.output is missing entirely.
      await assert.rejects(runAfter(dir, "task", "quality-reviewer", undefined), AdvanceHookAbort)
    })
    assert.equal(
      existsSync(captureFilePath(dir)),
      false,
      "must fail closed BEFORE ever shelling out to the preflight CLI",
    )
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// Pure-function unit tests (no process spawned) — shouldTriggerAdvance /
// buildAdvanceArgv
// ---------------------------------------------------------------------------

test("shouldTriggerAdvance: true only for a non-empty subagent_type in allowed_agents", () => {
  const now = Math.floor(Date.now() / 1000)
  const marker = mintMarker(KEY, { state: "quality", agents: ["quality-reviewer"], mintedAt: now })
  assert.equal(shouldTriggerAdvance(marker, "quality-reviewer"), true)
  assert.equal(shouldTriggerAdvance(marker, "gleipnir-code"), false)
  assert.equal(shouldTriggerAdvance(marker, ""), false)
  assert.equal(shouldTriggerAdvance(marker, undefined), false)
  assert.equal(shouldTriggerAdvance(marker, 123), false)
})

test("buildAdvanceArgv: exact CLI shape bin/gleipnir-preflight advance expects", () => {
  const argv = buildAdvanceArgv({
    pipelineId: "pl-x",
    bridgePath: "/repo/.gleipnir/var/run/pipeline-state.json",
    keyFile: "/keys/verifier",
  })
  assert.deepEqual(argv, [
    "advance",
    "--pipeline-id",
    "pl-x",
    "--bridge-path",
    "/repo/.gleipnir/var/run/pipeline-state.json",
    "--key-file",
    "/keys/verifier",
  ])
})

test("runAdvance: returns the stub's exit code and stderr directly (no interpretation)", () => {
  const dir = makeRepo({ withStub: true, stubExitCode: 0 })
  try {
    const { code } = runAdvance(dir, ["advance", "--pipeline-id", "x", "--bridge-path", "y", "--key-file", "z"])
    assert.equal(code, 0)
    assert.equal(existsSync(captureFilePath(dir)), true)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("buildAdvanceArgv: reviewerTranscriptStdin=true appends the flag; omitted/false reproduces the exact prior shape", () => {
  const withFlag = buildAdvanceArgv({
    pipelineId: "pl-x",
    bridgePath: "/repo/.gleipnir/var/run/pipeline-state.json",
    keyFile: "/keys/verifier",
    reviewerTranscriptStdin: true,
  })
  assert.deepEqual(withFlag, [
    "advance",
    "--pipeline-id",
    "pl-x",
    "--bridge-path",
    "/repo/.gleipnir/var/run/pipeline-state.json",
    "--key-file",
    "/keys/verifier",
    "--reviewer-transcript-stdin",
  ])

  const withoutFlag = buildAdvanceArgv({
    pipelineId: "pl-x",
    bridgePath: "/repo/.gleipnir/var/run/pipeline-state.json",
    keyFile: "/keys/verifier",
    reviewerTranscriptStdin: false,
  })
  assert.deepEqual(withoutFlag, [
    "advance",
    "--pipeline-id",
    "pl-x",
    "--bridge-path",
    "/repo/.gleipnir/var/run/pipeline-state.json",
    "--key-file",
    "/keys/verifier",
  ])
})

test("runAdvance: forwards stdinInput verbatim to the child process's stdin", () => {
  const dir = makeRepo({ withStub: true, stubExitCode: 0 })
  try {
    const { code } = runAdvance(
      dir,
      ["advance", "--pipeline-id", "x", "--bridge-path", "y", "--key-file", "z", "--reviewer-transcript-stdin"],
      "SPEC-CONFORM: PASS\n",
    )
    assert.equal(code, 0)
    assert.equal(readFileSync(stdinCaptureFilePath(dir), "utf8"), "SPEC-CONFORM: PASS\n")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// Golden-fixture-style DRY proof: the shared-helper imports genuinely come
// FROM sequence-gate.ts (not a duplicate reimplementation of the delicate
// HMAC/canonical-signing-input contract). Source-text assertion, not just
// behavior — per this delegation's explicit instruction.
// ---------------------------------------------------------------------------

test("DRY proof: advance-hook.ts imports validateMarker/isDelegationAllowed FROM sequence-gate.ts", () => {
  const source = readFileSync(ADVANCE_HOOK_TS_PATH, "utf8")
  assert.match(
    source,
    /import\s*\{\s*validateMarker\s*,\s*isDelegationAllowed\s*\}\s*from\s*["']\.\/sequence-gate\.ts["']/,
    "expected a direct import of validateMarker+isDelegationAllowed from ./sequence-gate.ts",
  )
})

test("DRY proof: advance-hook.ts does NOT reimplement the HMAC/canonical-signing-input contract", () => {
  const source = readFileSync(ADVANCE_HOOK_TS_PATH, "utf8")
  // The delicate cross-language MAC contract lives ONLY in sequence-gate.ts's
  // canonicalSigningInput + createHmac/timingSafeEqual. advance-hook.ts must
  // never CALL/IMPORT any of these itself -- proving validateMarker is
  // genuinely reused, not recomputed in a second place. Matched as an actual
  // invocation/import shape (a trailing "(" or an import-list membership),
  // NOT a bare substring match -- this file's own header prose legitimately
  // discusses these identifiers BY NAME (to explain what it does NOT do),
  // which a bare-substring check would misfire on.
  assert.doesNotMatch(source, /\bcreateHmac\s*\(/)
  assert.doesNotMatch(source, /\btimingSafeEqual\s*\(/)
  assert.doesNotMatch(source, /\bcanonicalSigningInput\s*\(/)
  assert.doesNotMatch(source, /from\s*["']node:crypto["']/)
})

test("behavioral cross-check: shouldTriggerAdvance agrees with the imported isDelegationAllowed on every case", () => {
  // Not just a source-text claim -- exercise both the real imported
  // isDelegationAllowed (from sequence-gate.ts) and shouldTriggerAdvance
  // (from advance-hook.ts) against the same inputs and require identical
  // results, proving shouldTriggerAdvance is a thin wrapper, not an
  // independently-reimplemented decision that happens to usually agree.
  const now = Math.floor(Date.now() / 1000)
  const marker = mintMarker(KEY, {
    state: "spec_review",
    agents: ["quality-reviewer", "gleipnir-plan"],
    mintedAt: now,
  })
  for (const candidate of ["quality-reviewer", "gleipnir-plan", "gleipnir-code", "git-ops"]) {
    assert.equal(shouldTriggerAdvance(marker, candidate), isDelegationAllowed(marker, candidate))
  }
})
