// Conformance test for the git-guard config-scan plugin.
//
// Proves the TS/JS hook maps the config-scan CLI exit-code contract
// (0=CLOSED/1=REFUSE/2=PROCEED_UNCLOSED) to the right gate decision, is
// ALWAYS-ACTIVE (no arming env var needed, D9), gates only the two gleipnir-git
// broker write tools, and fails closed on any unexpected code / spawn failure.
//
// Driven against a STUB `bin/gleipnir-preflight` in a temp dir (a tiny shell
// script that exits with a controlled code), mirroring test_sequence_gate.mjs's
// temp-dir + real-hook approach — no real config-scan run needed.
//
// Run with:  node --test tests/test_git_guard.mjs
// (Node strips the .ts types on import; the hook + helpers are pure/IO, no opencode.)

import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, mkdirSync, writeFileSync, chmodSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

import { GitGuard, decideFromExit, runConfigScan } from "../.gleipnir/plugins/git-guard.ts"

const COMMIT_TOOL = "gleipnir-git_commit_changes"
const PUSH_TOOL = "gleipnir-git_push_current_branch"

// Build a temp repo dir with a stub `bin/gleipnir-preflight` that exits `code`.
// The stub asserts it was called with the `config-scan` subcommand.
function makeRepoWithStub(code) {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-git-guard-"))
  mkdirSync(join(dir, "bin"), { recursive: true })
  const stub = join(dir, "bin", "gleipnir-preflight")
  writeFileSync(
    stub,
    `#!/bin/sh\n# stub gleipnir-preflight for git-guard tests\n` +
      `[ "$1" = "config-scan" ] || { echo "stub: expected config-scan, got $1" >&2; exit 99; }\n` +
      `echo "stub config-scan (exit ${code})" >&2\nexit ${code}\n`,
  )
  chmodSync(stub, 0o755)
  return dir
}

// Make a temp repo WITHOUT the CLI (to test the spawn-failure fail-closed path).
function makeRepoNoStub() {
  return mkdtempSync(join(tmpdir(), "gleipnir-git-guard-nocli-"))
}

async function runBefore(dir, tool) {
  const hook = (await GitGuard({ directory: dir }))["tool.execute.before"]
  await hook({ tool }, { args: {} })
}

// ---------------------------------------------------------------------------
// Pure decideFromExit contract
// ---------------------------------------------------------------------------

test("decideFromExit: 0 (CLOSED) -> allow", () => {
  assert.equal(decideFromExit(0), "allow")
})

test("decideFromExit: 2 (PROCEED_UNCLOSED) -> warn (operator override)", () => {
  assert.equal(decideFromExit(2), "warn")
})

test("decideFromExit: 1 (REFUSE) -> throws (abort the git op)", () => {
  assert.throws(() => decideFromExit(1), /REFUSED/)
})

test("decideFromExit: unexpected code -> throws (fail-closed)", () => {
  assert.throws(() => decideFromExit(3), /unexpected exit code/)
  assert.throws(() => decideFromExit(42), /unexpected exit code/)
})

// ---------------------------------------------------------------------------
// The real hook, driven against a stub CLI
// ---------------------------------------------------------------------------

test("exit 0 (CLOSED): allows the commit tool (no throw)", async () => {
  const dir = makeRepoWithStub(0)
  try {
    await runBefore(dir, COMMIT_TOOL) // must not throw
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("exit 1 (REFUSE): ABORTS the commit tool", async () => {
  const dir = makeRepoWithStub(1)
  try {
    await assert.rejects(runBefore(dir, COMMIT_TOOL), /REFUSED/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("exit 2 (PROCEED_UNCLOSED): allows (operator escape valve, no throw)", async () => {
  const dir = makeRepoWithStub(2)
  try {
    await runBefore(dir, COMMIT_TOOL) // must not throw — exit 2 is the override
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("exit 1 (REFUSE): ABORTS the push tool too (both git writes gated)", async () => {
  const dir = makeRepoWithStub(1)
  try {
    await assert.rejects(runBefore(dir, PUSH_TOOL), /REFUSED/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("unexpected exit code: ABORTS (fail-closed)", async () => {
  const dir = makeRepoWithStub(7)
  try {
    await assert.rejects(runBefore(dir, COMMIT_TOOL), /unexpected exit code/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("CLI missing: ABORTS (spawn failure fails closed)", async () => {
  const dir = makeRepoNoStub()
  try {
    await assert.rejects(runBefore(dir, COMMIT_TOOL), /could not run|fail-closed/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("non-gated tool: pass-through (never runs config-scan, never throws)", async () => {
  // Stub exits 1 (REFUSE) — but a non-git tool must NOT be gated, so no throw.
  const dir = makeRepoWithStub(1)
  try {
    await runBefore(dir, "task") // not a gated git tool => pass-through
    await runBefore(dir, "read")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("ALWAYS-ACTIVE: gates with NO arming env var set (unlike sequence-gate)", async () => {
  // No GLEIPNIR_PIPELINE, no bridge file — the gate must STILL fire on a git op.
  const savedPipeline = process.env.GLEIPNIR_PIPELINE
  delete process.env.GLEIPNIR_PIPELINE
  const dir = makeRepoWithStub(1)
  try {
    await assert.rejects(runBefore(dir, COMMIT_TOOL), /REFUSED/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
    if (savedPipeline === undefined) delete process.env.GLEIPNIR_PIPELINE
    else process.env.GLEIPNIR_PIPELINE = savedPipeline
  }
})

test("runConfigScan returns the stub's exit code and stderr", () => {
  const dir = makeRepoWithStub(0)
  try {
    const { code, stderr } = runConfigScan(dir)
    assert.equal(code, 0)
    assert.match(stderr, /stub config-scan/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})
