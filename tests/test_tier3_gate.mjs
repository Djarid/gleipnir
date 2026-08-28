// Conformance test for the tier3-gate Tier-3 write-block plugin.
//
// Proves the TS/JS hook (a) routes on the TARGET PATH (output.args.filePath),
// not the acting agent; (b) shells out to the approval-gate CLI ONLY for a
// Tier-3-path `write` call, computing the EXACT resulting content
// (`output.args.content`) and passing it to the CLI via a `--content-file`
// temp file (Decisions 19 + 20 -- the mint-vs-check content-hash fix); (c)
// FAILS CLOSED UNCONDITIONALLY for any `edit` call to a Tier-3 path --
// opencode's fuzzy-replacer + formatter `edit` semantics are not reliably
// reproducible out-of-band, so `edit` is refused WITHOUT ever invoking the
// gate CLI, regardless of what the CLI would have returned; (d) maps the
// gate CLI's exit-code contract (0=ALLOW, non-zero=REFUSE) to the right
// decision for `write`; (e) is ALWAYS-ACTIVE (no arming env var, mirroring
// git-guard.ts's D9 posture -- a Tier-3 write must be gated in every
// session); and (f) fails closed on any unexpected condition, including a
// missing/non-executable gate-CLI interpreter, distinct from a policy
// REFUSE.
//
// Driven against a STUB `.venv/bin/python` in a temp dir (a tiny shell script
// that exits with a controlled code, and for the content-binding cases,
// echoes back what it was given) -- mirrors test_git_guard.mjs's
// temp-dir + real-hook + stub-CLI approach exactly. No real approval-gate CLI
// run is needed: the stub speaks only the exit-code contract
// (`src/gleipnir/approval/__main__.py`'s documented 0/1/3 -> ALLOW/REFUSE/
// REFUSE shape, collapsed here to "0 vs non-zero" since the hook itself does
// not distinguish REFUSE reasons -- see tier3-gate.ts's decideFromExit).
//
// Plan: `.gleipnir/plans/tier3-signed-approval.md` Decisions 14a/19/20,
// Trace L9 + L10 + "The content-binding mechanism" + Integrations map +
// Edge cases 11-13, Assemble Step 7, Stress-test T-21/T-22. Mirrors the
// exact source in `.gleipnir/plans/tier3-gate-ts-ready-to-apply.md` (the
// operator/build-mode hand-off draft for `.gleipnir/plugins/tier3-gate.ts`,
// which this test cannot itself write -- see the CAPABILITY-BOUNDS note
// below).
//
// Run with:  node --test tests/test_tier3_gate.mjs
// (Node strips the .ts types on import; the hook + helpers are pure/IO, no
// opencode runtime needed.)
//
// STATUS AT AUTHORING TIME: this test is EXPECTED TO FAIL AT IMPORT (module
// not found) -- `.gleipnir/plugins/tier3-gate.ts` is a Tier-3 artifact named
// verbatim by the plan / the ready-to-apply draft but not yet applied by the
// operator/build-mode (test-first discipline: the test is written and red
// before the guarded artifact lands). `.gleipnir/plugins/**` is Tier-3
// enforcement-path set `E` (`stage-role-map.md`); no in-framework agent --
// not even `gleipnir-code` -- may write it, so this test cannot be turned
// green by this delegation.
//
// CAPABILITY-BOUNDS (honesty note, per the delegation). This test's
// assertions were validated by hand against the exact TypeScript source in
// `.gleipnir/plans/tier3-gate-ts-ready-to-apply.md` (read in full) --
// `isTier3Path`, `findLatestTokenPath`, `resultingContentFor`,
// `runGateCheck(directory, filePath, resultingContent)` (now THREE
// arguments, content-first design), `decideFromExit`, and the
// `Tier3Gate({directory})["tool.execute.before"]` control flow -- but this
// delegation has no sandboxed way to actually EXECUTE that draft as a
// module without writing it to `.gleipnir/plugins/tier3-gate.ts` (a Tier-3
// write this role cannot perform). So: the test's LOGIC is verified against
// the draft's source by inspection; whether `node --test` actually turns
// green once the operator applies the draft is NOT verified by this
// delegation -- only that (i) it currently fails at import for the right
// reason (ENOENT / module not found, exactly like the previous version of
// this file), and (ii) every assertion below matches a control-flow branch
// literally present in the ready-to-apply source, function signature and
// all (e.g. `runGateCheck`'s three-argument order, `resultingContentFor`'s
// per-tool branching, the temp `--content-file` write-then-unlink shape).

import { test } from "node:test"
import assert from "node:assert/strict"
import {
  mkdtempSync,
  mkdirSync,
  writeFileSync,
  chmodSync,
  rmSync,
  readFileSync,
  readdirSync,
  existsSync,
} from "node:fs"
import { createHash } from "node:crypto"
import { tmpdir } from "node:os"
import { join } from "node:path"

import {
  Tier3Gate,
  decideFromExit,
  runGateCheck,
  resultingContentFor,
  isTier3Path,
  PreflightUnavailable,
  GateRefused,
  computeChangeHash,
  stagePendingContent,
  buildApprovalUrl,
} from "../.gleipnir/plugins/tier3-gate.ts"

// A representative Tier-3 target under each routed prefix, plus the one
// exact-match file -- used across the integration tests below.
const TIER3_AGENT_FILE = ".gleipnir/agents/tier3-writer.md"
const TIER3_DECISION_FILE = ".gleipnir/decisions/tier3-signed-approval.md"
const TIER3_STAGE_MAP = ".gleipnir/stage-role-map.md"

// A representative NON-Tier-3 target -- ordinary source/test paths must never
// be gated.
const NON_TIER3_FILE = "src/gleipnir/approval/gate.py"

// ---------------------------------------------------------------------------
// Temp-repo builders (mirrors test_git_guard.mjs's makeRepoWithStub /
// makeRepoNoStub / makeRepoNonExecStub shapes exactly, but stubbing
// `.venv/bin/python` -- the interpreter tier3-gate.ts resolves relative to
// `directory`, mirroring bin/gleipnir-preflight's own `$repo/.venv/bin/python`
// convention -- rather than `bin/gleipnir-preflight`).
//
// The stub, when `recordArgvTo` is given, writes its FULL argv to a marker
// file (one arg per line) and echoes the `--content-file` file's own bytes
// to a second marker file -- this is how the content-binding cases (T-21(f))
// verify the hook handed over the exact resulting content, and how the
// edit-fail-closed cases (T-21(e)) prove the CLI was never even spawned (the
// marker file simply never appears).
// ---------------------------------------------------------------------------

// Build a temp repo dir with a stub `.venv/bin/python` that exits `code`.
// The stub asserts it was invoked as `-m gleipnir.approval.gate ...` (the
// literal CLI contract the plan's Decision 14a and __main__.py both name),
// and if `recordDir` is given, records its full argv (one per line) to
// `recordDir/argv.txt` and a copy of whatever `--content-file` pointed at to
// `recordDir/content-file-echo` -- so a test can assert on exactly what the
// hook handed the CLI without needing a real gate run.
function makeRepoWithStub(code, recordDir) {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-"))
  mkdirSync(join(dir, ".venv", "bin"), { recursive: true })
  const stub = join(dir, ".venv", "bin", "python")
  const recordLines = recordDir
    ? [
        `argv_file="${join(recordDir, "argv.txt")}"`,
        `: > "$argv_file"`,
        `for a in "$@"; do echo "$a" >> "$argv_file"; done`,
        // Find the --content-file value (the argument right after the flag)
        // and copy its bytes so the test can assert on them independently
        // of whether the temp file still exists after the hook returns.
        `prev=""`,
        `for a in "$@"; do`,
        `  if [ "$prev" = "--content-file" ]; then`,
        `    cp "$a" "${join(recordDir, "content-file-echo")}" 2>/dev/null || true`,
        `  fi`,
        `  prev="$a"`,
        `done`,
      ].join("\n")
    : ""
  writeFileSync(
    stub,
    `#!/bin/sh\n# stub approval-gate CLI for tier3-gate tests\n` +
      `[ "$1" = "-m" ] || { echo "stub: expected -m gleipnir.approval.gate, got $1" >&2; exit 99; }\n` +
      `${recordLines}\n` +
      `echo "stub approval-gate (exit ${code})" >&2\nexit ${code}\n`,
  )
  chmodSync(stub, 0o755)
  return dir
}

// Make a temp repo WITHOUT the interpreter (to test the spawn/missing-CLI
// fail-closed path).
function makeRepoNoStub() {
  return mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-nocli-"))
}

// A temp repo whose `.venv/bin/python` EXISTS but is NOT executable -- the
// same class of regression git-guard.ts's makeRepoNonExecStub guards
// against (a committed non-executable mode).
function makeRepoNonExecStub() {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-noexec-"))
  mkdirSync(join(dir, ".venv", "bin"), { recursive: true })
  const stub = join(dir, ".venv", "bin", "python")
  writeFileSync(stub, `#!/bin/sh\nexit 0\n`)
  chmodSync(stub, 0o644) // present but not +x
  return dir
}

// Drives the REAL hook with a three-argument tool-call shape: `write` calls
// carry `content`; `edit` calls carry whatever args a caller supplies
// (defaulting to none, since `edit` is refused before any arg is consulted
// beyond `filePath`).
async function runBefore(dir, tool, filePath, extraArgs = {}) {
  const hook = (await Tier3Gate({ directory: dir }))["tool.execute.before"]
  await hook({ tool }, { args: { filePath, ...extraArgs } })
}

// The staged `pending-<hash>.json` files that currently exist under a repo's
// `.gleipnir/var/tmp/` staging dir (plan Trace section A's `STAGING_DIR_REL`)
// -- used by the S12 tests below to assert staging happened (or, decisively,
// did NOT happen) for a given caught-error class.
function stagedFilesIn(dir) {
  const stagingDir = join(dir, ".gleipnir", "var", "tmp")
  if (!existsSync(stagingDir)) return []
  return readdirSync(stagingDir).filter(
    (f) => f.startsWith("pending-") && f.endsWith(".json"),
  )
}

// ---------------------------------------------------------------------------
// Pure decideFromExit contract
// ---------------------------------------------------------------------------

test("decideFromExit: 0 (ALLOW) -> allow", () => {
  assert.equal(decideFromExit(0), "allow")
})

test("decideFromExit: 1 (REFUSE) -> throws (abort the write)", () => {
  assert.throws(() => decideFromExit(1), /REFUSED/)
})

test("decideFromExit: 3 (key-unavailable REFUSE) -> throws", () => {
  assert.throws(() => decideFromExit(3), /REFUSED/)
})

test("decideFromExit: any other non-zero code -> throws (fail-closed, not distinguished from REFUSE)", () => {
  assert.throws(() => decideFromExit(42), /REFUSED/)
})

// ---------------------------------------------------------------------------
// NEW subclass `GateRefused` (`.gleipnir/plans/tier3-approval-ux.md` Trace
// section A, Stress-test S12(a)). `decideFromExit` must throw `GateRefused`
// -- not a bare `Tier3GateAbort` -- on every non-zero exit, so staging can be
// keyed strictly on `instanceof GateRefused` downstream. Its return-"allow"-
// on-0 contract and `REFUSED` message text are UNCHANGED (the existing
// `/REFUSED/` assertions above still pass because `GateRefused` is a
// `Tier3GateAbort` subclass carrying the same message).
// ---------------------------------------------------------------------------

test("S12(a): decideFromExit(non-zero) throws an error that IS instanceof GateRefused, for every REFUSE code", () => {
  for (const code of [1, 3, 42]) {
    assert.throws(
      () => decideFromExit(code),
      (err) => {
        assert.ok(
          err instanceof GateRefused,
          `code ${code}: the thrown error must be instanceof GateRefused`,
        )
        assert.match(err.message, /REFUSED/)
        return true
      },
    )
  }
})

test("S12(a): decideFromExit(0) is unaffected by the GateRefused change -- still returns \"allow\"", () => {
  assert.equal(decideFromExit(0), "allow")
})

// ---------------------------------------------------------------------------
// Pure isTier3Path contract
// ---------------------------------------------------------------------------

test("isTier3Path: directory-prefix members match (agents/, decisions/, ...)", () => {
  assert.equal(isTier3Path("/repo", ".gleipnir/agents/tier3-writer.md"), true)
  assert.equal(isTier3Path("/repo", ".gleipnir/skills/gotcha/SKILL.md"), true)
  assert.equal(isTier3Path("/repo", ".gleipnir/goals/manifest.md"), true)
  assert.equal(isTier3Path("/repo", ".gleipnir/decisions/tier3-signed-approval.md"), true)
  assert.equal(isTier3Path("/repo", ".gleipnir/keys/marker.key"), true)
  assert.equal(isTier3Path("/repo", ".gleipnir/plugins/tier3-gate.ts"), true)
})

test("isTier3Path: the one exact-match file (stage-role-map.md)", () => {
  assert.equal(isTier3Path("/repo", ".gleipnir/stage-role-map.md"), true)
})

test("isTier3Path: non-Tier-3 paths do not match (src/, tests/, .gleipnir/plans/, .gleipnir/AGENTS.md)", () => {
  assert.equal(isTier3Path("/repo", "src/gleipnir/approval/gate.py"), false)
  assert.equal(isTier3Path("/repo", "tests/test_tier3_gate.mjs"), false)
  assert.equal(isTier3Path("/repo", ".gleipnir/plans/tier3-signed-approval.md"), false)
  assert.equal(isTier3Path("/repo", ".gleipnir/AGENTS.md"), false)
})

test("isTier3Path: a lookalike name is NOT swallowed by prefix matching (agentsX vs agents/)", () => {
  assert.equal(isTier3Path("/repo", ".gleipnir/agentsXtra/not-really.md"), false)
})

test("isTier3Path: works given an absolute filePath under directory (opencode may hand back either shape)", () => {
  assert.equal(isTier3Path("/repo", "/repo/.gleipnir/agents/tier3-writer.md"), true)
  assert.equal(isTier3Path("/repo", "/repo/src/gleipnir/approval/gate.py"), false)
})

// ---------------------------------------------------------------------------
// Pure resultingContentFor contract (Decision 20)
// ---------------------------------------------------------------------------

test("resultingContentFor: write returns args.content verbatim (CERTAIN)", () => {
  assert.equal(resultingContentFor("write", { content: "hello tier-3" }), "hello tier-3")
  assert.equal(resultingContentFor("write", { content: "" }), "")
})

test("resultingContentFor: write with no string content throws (fail-closed)", () => {
  assert.throws(() => resultingContentFor("write", {}), Error)
  assert.throws(() => resultingContentFor("write", { content: 42 }), Error)
  assert.throws(() => resultingContentFor("write", { content: null }), Error)
})

test("resultingContentFor: edit ALWAYS throws regardless of args -- not reproducible out-of-band (Decision 20)", () => {
  assert.throws(
    () => resultingContentFor("edit", { filePath: "x", oldString: "a", newString: "b" }),
    Error,
  )
  // Even a trivial/no-op-looking edit request still throws -- the plugin
  // cannot be CERTAIN of opencode's fuzzy-replacer + formatter output, so it
  // refuses unconditionally, never attempting to guess.
  assert.throws(() => resultingContentFor("edit", {}), Error)
  assert.throws(() => resultingContentFor("edit", { oldString: "x", newString: "x" }), Error)
})

test("resultingContentFor: an unexpected tool name throws defensively", () => {
  assert.throws(() => resultingContentFor("bash", {}), Error)
})

// ---------------------------------------------------------------------------
// T-21(e) -- an `edit` to a Tier-3 path ALWAYS fails closed, and the gate CLI
// is NEVER invoked -- proven via a stub that would ALLOW (exit 0) if it were
// ever called. If the hook mistakenly spawned the CLI for `edit`, this test
// would still pass on the throw (since resultingContentFor always throws for
// edit before any spawn) -- so the decisive proof is the argv marker file
// NEVER appearing, confirming the CLI process was truly never started.
// ---------------------------------------------------------------------------

test("T-21(e): edit to a Tier-3 path always refuses/throws, EVEN IF the stub CLI would ALLOW (exit 0)", async () => {
  const recordDir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-record-"))
  const dir = makeRepoWithStub(0, recordDir) // stub would ALLOW if invoked
  try {
    await assert.rejects(
      runBefore(dir, "edit", TIER3_AGENT_FILE, { oldString: "a", newString: "b" }),
      Error,
    )
    // Decisive proof the CLI was never spawned: the argv marker file the
    // stub would have written on any invocation simply does not exist.
    assert.equal(
      existsSync(join(recordDir, "argv.txt")),
      false,
      "the gate CLI must never be spawned for an edit to a Tier-3 path",
    )
  } finally {
    rmSync(dir, { recursive: true, force: true })
    rmSync(recordDir, { recursive: true, force: true })
  }
})

test("T-21(e): edit to the exact-match stage-role-map.md target also refuses without invoking the CLI", async () => {
  const recordDir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-record-"))
  const dir = makeRepoWithStub(0, recordDir)
  try {
    await assert.rejects(runBefore(dir, "edit", TIER3_STAGE_MAP, { oldString: "a", newString: "b" }))
    assert.equal(existsSync(join(recordDir, "argv.txt")), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
    rmSync(recordDir, { recursive: true, force: true })
  }
})

test("T-21(e): edit to a Tier-3 path refuses even with NO stub CLI present at all (no spawn attempted)", async () => {
  // If the hook tried to spawn here it would hit PreflightUnavailable
  // (missing interpreter) rather than a plain Tier3GateAbort -- asserting a
  // generic throw (not narrowing to PreflightUnavailable) and, more
  // decisively, that the rejection happens even though the repo has no
  // `.venv/bin/python` at all proves resultingContentFor's throw happens
  // BEFORE runGateCheck would ever try (and fail differently).
  const dir = makeRepoNoStub()
  try {
    await assert.rejects(runBefore(dir, "edit", TIER3_DECISION_FILE, {}))
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// T-21(a) -- write to a Tier-3 path, gate CLI exits non-zero (no/expired
// token) => THROWS
// ---------------------------------------------------------------------------

test("T-21(a): Tier-3-path write with the gate CLI REFUSING (non-zero exit) ABORTS the write", async () => {
  const dir = makeRepoWithStub(1)
  try {
    await assert.rejects(
      runBefore(dir, "write", TIER3_AGENT_FILE, { content: "proposed new content" }),
      /REFUSED/,
    )
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("T-21(a): aborts on the exact-match stage-role-map.md target too", async () => {
  const dir = makeRepoWithStub(1)
  try {
    await assert.rejects(
      runBefore(dir, "write", TIER3_STAGE_MAP, { content: "proposed" }),
      /REFUSED/,
    )
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// T-21(b) -- same write, gate CLI exits 0 (valid fresh token) => PROCEEDS
// ---------------------------------------------------------------------------

test("T-21(b): Tier-3-path write with the gate CLI ALLOWING (exit 0) proceeds (no throw)", async () => {
  const dir = makeRepoWithStub(0)
  try {
    await runBefore(dir, "write", TIER3_AGENT_FILE, { content: "proposed new content" }) // must not throw
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("T-21(b): also proceeds for a write to the decisions/ Tier-3 prefix on a valid fresh token", async () => {
  const dir = makeRepoWithStub(0)
  try {
    await runBefore(dir, "write", TIER3_DECISION_FILE, { content: "proposed" }) // must not throw
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// T-21(f) -- content-binding wiring: a `write` to a Tier-3 path passes the
// EXACT resulting content (`output.args.content`) via `--content-file`, and
// the temp file is unlinked afterward. Verified via a stub that echoes back
// the `--content-file` bytes it was handed.
// ---------------------------------------------------------------------------

test("T-21(f): write's --content-file carries EXACTLY output.args.content, and argv includes --content-file", async () => {
  const recordDir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-record-"))
  const dir = makeRepoWithStub(0, recordDir)
  const proposedContent = "the exact resulting content this write will produce\nwith a newline"
  try {
    await runBefore(dir, "write", TIER3_AGENT_FILE, { content: proposedContent })

    const argv = readFileSync(join(recordDir, "argv.txt"), "utf8").split("\n").filter(Boolean)
    assert.ok(argv.includes("--content-file"), "argv must include --content-file")
    assert.ok(argv.includes("-m"), "argv must include the -m module invocation")
    assert.ok(argv.includes("gleipnir.approval.gate"), "argv must invoke the gate module")
    assert.ok(argv.includes("--check"), "argv must still include --check as the file identifier")
    assert.ok(argv.includes("--token"), "argv must include --token")

    const echoed = readFileSync(join(recordDir, "content-file-echo"), "utf8")
    assert.equal(echoed, proposedContent, "the --content-file bytes must equal output.args.content exactly")
  } finally {
    rmSync(dir, { recursive: true, force: true })
    rmSync(recordDir, { recursive: true, force: true })
  }
})

test("T-21(f): the temp content-file no longer exists after the call (unlinked in finally)", async () => {
  const recordDir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-record-"))
  const dir = makeRepoWithStub(0, recordDir)
  try {
    await runBefore(dir, "write", TIER3_AGENT_FILE, { content: "proposed" })
    const argv = readFileSync(join(recordDir, "argv.txt"), "utf8").split("\n").filter(Boolean)
    const idx = argv.indexOf("--content-file")
    assert.ok(idx >= 0)
    const contentFilePath = argv[idx + 1]
    assert.equal(
      existsSync(contentFilePath),
      false,
      "the temp content-file must be unlinked (in a finally) after the gate call returns",
    )
  } finally {
    rmSync(dir, { recursive: true, force: true })
    rmSync(recordDir, { recursive: true, force: true })
  }
})

test("T-21(f): the temp content-file is unlinked even when the gate CLI REFUSES (non-zero exit)", async () => {
  const recordDir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-record-"))
  const dir = makeRepoWithStub(1, recordDir)
  try {
    await assert.rejects(runBefore(dir, "write", TIER3_AGENT_FILE, { content: "proposed" }), /REFUSED/)
    const argv = readFileSync(join(recordDir, "argv.txt"), "utf8").split("\n").filter(Boolean)
    const idx = argv.indexOf("--content-file")
    assert.ok(idx >= 0)
    const contentFilePath = argv[idx + 1]
    assert.equal(existsSync(contentFilePath), false)
  } finally {
    rmSync(dir, { recursive: true, force: true })
    rmSync(recordDir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// T-21(c) -- non-Tier-3 path => pass-through; the gate CLI is NEVER invoked
// ---------------------------------------------------------------------------

test("T-21(c): non-Tier-3 path is pass-through -- gate CLI never invoked, never throws", async () => {
  // The stub is wired to REFUSE (exit 1) if it is ever called. A non-Tier-3
  // edit/write must therefore NOT throw -- the only way that can be true is
  // if the stub was never invoked at all, since exit 1 always throws when
  // runGateCheck/decideFromExit actually run (proven by the T-21(a) tests
  // above). Absence of a throw here is the proof of "never invoked".
  const dir = makeRepoWithStub(1)
  try {
    await runBefore(dir, "edit", NON_TIER3_FILE, { oldString: "a", newString: "b" })
    await runBefore(dir, "write", "tests/test_approval_gate.py", { content: "x" })
    await runBefore(dir, "write", ".gleipnir/plans/tier3-signed-approval.md", { content: "x" })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("T-21(c): non-edit/write tools are pass-through regardless of target path", async () => {
  const dir = makeRepoWithStub(1)
  try {
    await runBefore(dir, "read", TIER3_AGENT_FILE)
    await runBefore(dir, "task", TIER3_AGENT_FILE)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// T-21(d) -- missing / non-executable gate CLI => fail-closed throw, distinct
// from a policy REFUSE (mirrors makeRepoNonExecStub's pattern in
// test_git_guard.mjs). Exercised via `write` (the only tool that reaches
// runGateCheck at all -- `edit` never gets this far, per T-21(e) above).
// ---------------------------------------------------------------------------

test("T-21(d): python interpreter MISSING -> PreflightUnavailable, not a policy REFUSE", async () => {
  const dir = makeRepoNoStub()
  try {
    await assert.rejects(runBefore(dir, "write", TIER3_AGENT_FILE, { content: "x" }), (err) => {
      assert.ok(
        err instanceof PreflightUnavailable,
        "must be PreflightUnavailable (broken prerequisite), not a plain REFUSE abort",
      )
      assert.match(err.message, /missing or not executable/)
      assert.doesNotMatch(err.message, /REFUSED/) // NOT a policy rejection
      return true
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("T-21(d): python interpreter present but NOT executable -> PreflightUnavailable", async () => {
  const dir = makeRepoNonExecStub()
  try {
    await assert.rejects(runBefore(dir, "write", TIER3_DECISION_FILE, { content: "x" }), (err) => {
      assert.ok(err instanceof PreflightUnavailable)
      assert.match(err.message, /missing or not executable/)
      assert.doesNotMatch(err.message, /REFUSED/)
      return true
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("T-21(d): a broken/missing CLI is fail-closed even for the exact-match stage-role-map.md target", async () => {
  const dir = makeRepoNoStub()
  try {
    await assert.rejects(runBefore(dir, "write", TIER3_STAGE_MAP, { content: "x" }), (err) => {
      assert.ok(err instanceof PreflightUnavailable)
      return true
    })
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// ALWAYS-ACTIVE: no arming env var needed (unlike sequence-gate.ts)
// ---------------------------------------------------------------------------

test("ALWAYS-ACTIVE: gates with NO arming env var set (mirrors git-guard.ts's D9 posture)", async () => {
  const savedPipeline = process.env.GLEIPNIR_PIPELINE
  delete process.env.GLEIPNIR_PIPELINE
  const dir = makeRepoWithStub(1)
  try {
    await assert.rejects(runBefore(dir, "write", TIER3_AGENT_FILE, { content: "x" }), /REFUSED/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
    if (savedPipeline === undefined) delete process.env.GLEIPNIR_PIPELINE
    else process.env.GLEIPNIR_PIPELINE = savedPipeline
  }
})

// ---------------------------------------------------------------------------
// runGateCheck: THREE-ARGUMENT shape (directory, filePath, resultingContent)
// -- returns the stub's exit code and stderr (mirrors test_git_guard.mjs's
// runConfigScan smoke test). This is the shape change from the earlier
// two-argument draft: runGateCheck now takes the resulting content directly
// and is responsible for writing/unlinking the temp --content-file itself.
// ---------------------------------------------------------------------------

test("runGateCheck(directory, filePath, resultingContent): returns the stub's exit code and stderr", () => {
  const dir = makeRepoWithStub(0)
  try {
    const { code, stderr } = runGateCheck(dir, TIER3_AGENT_FILE, "some resulting content")
    assert.equal(code, 0)
    assert.match(stderr, /stub approval-gate/)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("runGateCheck: propagates a non-zero exit code without throwing itself (decideFromExit is the throwing layer)", () => {
  const dir = makeRepoWithStub(1)
  try {
    const { code } = runGateCheck(dir, TIER3_AGENT_FILE, "some resulting content")
    assert.equal(code, 1)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// Edge case: write with no filePath at all -- fail closed rather than
// silently assume non-Tier-3 (not an explicit plan edge case, but consistent
// with the "fail closed everywhere" Notes-for-the-implementing-agent
// discipline; documented here so a regression toward silent pass-through is
// caught).
// ---------------------------------------------------------------------------

test("write with no filePath to classify: fails closed (does not silently pass through)", async () => {
  const dir = makeRepoWithStub(1) // would REFUSE if the gate CLI were ever reached
  try {
    const hook = (await Tier3Gate({ directory: dir }))["tool.execute.before"]
    await assert.rejects(hook({ tool: "write" }, { args: { content: "x" } }))
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// computeChangeHash / stagePendingContent / buildApprovalUrl -- pure unit
// tests (`.gleipnir/plans/tier3-approval-ux.md` Assemble Step 4, Trace
// section A, P1/P2/P8).
// ---------------------------------------------------------------------------

test("computeChangeHash: known UTF-8 sha256 vector (P2) -- matches an independent node:crypto computation", () => {
  const content = "hello tier-3"
  assert.equal(
    computeChangeHash(content),
    createHash("sha256").update(content, "utf8").digest("hex"),
  )
})

test("computeChangeHash: multibyte content hashes the UTF-8 bytes, not code units (P2)", () => {
  const content = "α<b>\n"
  assert.equal(
    computeChangeHash(content),
    createHash("sha256").update(content, "utf8").digest("hex"),
  )
})

test("stagePendingContent: writes pending-<hash>.json under .gleipnir/var/tmp with the {content, filePath, tool, staged_at} envelope (P1), filename keyed by the hash", () => {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-stage-"))
  try {
    const content = "proposed tier-3 content\nsecond line"
    const hash = stagePendingContent(dir, "write", TIER3_DECISION_FILE, content)
    assert.equal(hash, computeChangeHash(content), "the returned hash must be sha256(content, utf8)")

    const stagedPath = join(dir, ".gleipnir", "var", "tmp", `pending-${hash}.json`)
    assert.ok(existsSync(stagedPath), "stagePendingContent must write pending-<hash>.json")

    const envelope = JSON.parse(readFileSync(stagedPath, "utf8"))
    assert.equal(envelope.content, content)
    assert.equal(envelope.filePath, TIER3_DECISION_FILE)
    assert.equal(envelope.tool, "write")
    assert.equal(typeof envelope.staged_at, "number")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("stagePendingContent: is idempotent for identical content -- same hash, same filename, harmless overwrite (E4)", () => {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-stage-"))
  try {
    const content = "same content twice"
    const hash1 = stagePendingContent(dir, "write", TIER3_AGENT_FILE, content)
    const hash2 = stagePendingContent(dir, "write", TIER3_AGENT_FILE, content)
    assert.equal(hash1, hash2)
    assert.equal(stagedFilesIn(dir).length, 1)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("buildApprovalUrl: GLEIPNIR_APPROVAL_BASE_URL set -- full URL, one trailing slash stripped (P8)", () => {
  const saved = process.env.GLEIPNIR_APPROVAL_BASE_URL
  process.env.GLEIPNIR_APPROVAL_BASE_URL = "https://h.ts.net/"
  try {
    const hash = "a".repeat(64)
    assert.equal(buildApprovalUrl(hash), `Approve at: https://h.ts.net/approve/${hash}`)
  } finally {
    if (saved === undefined) delete process.env.GLEIPNIR_APPROVAL_BASE_URL
    else process.env.GLEIPNIR_APPROVAL_BASE_URL = saved
  }
})

test("buildApprovalUrl: GLEIPNIR_APPROVAL_BASE_URL unset -- graceful relative-hint fallback (P8)", () => {
  const saved = process.env.GLEIPNIR_APPROVAL_BASE_URL
  delete process.env.GLEIPNIR_APPROVAL_BASE_URL
  try {
    const hash = "b".repeat(64)
    assert.equal(
      buildApprovalUrl(hash),
      `Approve at: <your approval listener>/approve/${hash} (set GLEIPNIR_APPROVAL_BASE_URL to show the full URL here)`,
    )
  } finally {
    if (saved === undefined) delete process.env.GLEIPNIR_APPROVAL_BASE_URL
    else process.env.GLEIPNIR_APPROVAL_BASE_URL = saved
  }
})

// ---------------------------------------------------------------------------
// S12 -- staging is keyed STRICTLY on `instanceof GateRefused`, not on "any
// Tier3GateAbort" (`.gleipnir/plans/tier3-approval-ux.md` Stress-test S12(b)-
// (d), Trace "Wiring point", edge cases E1-E3). This is the mechanism-level
// proof that closes the review's "outer catch treats all Tier3GateAbort the
// same" gap: a genuine policy REFUSE stages a file; a broken prerequisite
// (PreflightUnavailable) and an edit-tool-call refusal do NOT, even though
// both are also Tier3GateAbort instances.
// ---------------------------------------------------------------------------

test("S12(b): a genuine policy REFUSE (stub CLI exits non-zero) stages pending-<hash>.json AND the thrown error is GateRefused carrying the approval URL", async () => {
  const dir = makeRepoWithStub(1)
  const proposedContent = "S12 refuse-path staged content\nwith a newline"
  try {
    await assert.rejects(
      runBefore(dir, "write", TIER3_AGENT_FILE, { content: proposedContent }),
      (err) => {
        assert.ok(err instanceof GateRefused, "the thrown error must be instanceof GateRefused")
        assert.match(err.message, /\/approve\//, "the message must contain the approval URL")
        return true
      },
    )
    const staged = stagedFilesIn(dir)
    assert.equal(staged.length, 1, "exactly one staged file must appear for a genuine REFUSE")
    const expectedHash = computeChangeHash(proposedContent)
    assert.equal(staged[0], `pending-${expectedHash}.json`)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("S12(b-negative): a stub exiting 0 (ALLOW) stages NOTHING -- there is no error, so nothing to key staging off", async () => {
  const dir = makeRepoWithStub(0)
  try {
    await runBefore(dir, "write", TIER3_AGENT_FILE, { content: "allowed content, never staged" }) // must not throw
    assert.deepEqual(stagedFilesIn(dir), [], "an ALLOW must never stage a pending file")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("S12(c): PreflightUnavailable (missing interpreter) never stages -- it is a Tier3GateAbort but NOT a GateRefused", async () => {
  const dir = makeRepoNoStub()
  try {
    await assert.rejects(
      runBefore(dir, "write", TIER3_AGENT_FILE, { content: "would-be staged content" }),
      (err) => {
        assert.ok(err instanceof PreflightUnavailable, "must be PreflightUnavailable")
        assert.ok(!(err instanceof GateRefused), "PreflightUnavailable must NOT be a GateRefused")
        return true
      },
    )
    assert.deepEqual(stagedFilesIn(dir), [], "no staged file for a broken prerequisite (E1)")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("S12(c'): PreflightUnavailable via a present-but-non-executable interpreter also never stages", async () => {
  const dir = makeRepoNonExecStub()
  try {
    await assert.rejects(
      runBefore(dir, "write", TIER3_DECISION_FILE, { content: "x" }),
      (err) => {
        assert.ok(err instanceof PreflightUnavailable)
        assert.ok(!(err instanceof GateRefused))
        return true
      },
    )
    assert.deepEqual(stagedFilesIn(dir), [])
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("S12(d): an edit-tool-call refusal to a Tier-3 path never stages -- resultingContentFor's throw is a Tier3GateAbort but NOT a GateRefused", async () => {
  const dir = makeRepoWithStub(0) // would ALLOW if ever invoked -- proves the CLI is never reached either
  try {
    await assert.rejects(
      runBefore(dir, "edit", TIER3_AGENT_FILE, { oldString: "a", newString: "b" }),
      (err) => {
        assert.ok(!(err instanceof GateRefused), "an edit refusal must NOT be a GateRefused")
        return true
      },
    )
    assert.deepEqual(stagedFilesIn(dir), [], "no staged file for an edit refusal (E2)")
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("S12(d'): a write with no string content (E3) also never stages -- resultingContentFor's throw is NOT a GateRefused", async () => {
  const dir = makeRepoWithStub(0)
  try {
    await assert.rejects(
      runBefore(dir, "write", TIER3_AGENT_FILE, {}),
      (err) => {
        assert.ok(!(err instanceof GateRefused))
        return true
      },
    )
    assert.deepEqual(stagedFilesIn(dir), [])
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

// ---------------------------------------------------------------------------
// S13 (TS half) -- cross-language JSON round-trip fidelity, multibyte/
// astral (`.gleipnir/plans/tier3-approval-ux.md` Stress-test S13). Drives
// the REAL `computeChangeHash`/`stagePendingContent` with the literal SAME
// content string as the Python-side S13 test
// (`tests/test_approval_server.py::TestCrossLanguageJSONRoundTripFidelity.X`)
// -- keep these two literals in sync if either changes -- and asserts both
// against an independently-computed `sha256(X, utf8)` via `node:crypto`,
// which is the exact same canonical UTF-8 SHA-256 value
// `hashlib.sha256(X.encode("utf-8")).hexdigest()` produces on the Python
// side for the identical string (S1's byte-identity contract, applied here
// through the REAL JSON.stringify -> disk -> (Python) json.loads envelope
// round trip that S1/S8 bypass).
// ---------------------------------------------------------------------------

// Byte-for-byte the SAME literal as
// tests/test_approval_server.py::TestCrossLanguageJSONRoundTripFidelity.X.
const S13_MULTIBYTE_CONTENT = "emoji \u2705\u{1F510}\n multibyte \u03b1\u03b2\u03b3"

test("S13 (TS half): computeChangeHash(X) matches an independent sha256(X, utf8) computation for multibyte/astral content", () => {
  const expected = createHash("sha256").update(S13_MULTIBYTE_CONTENT, "utf8").digest("hex")
  assert.equal(computeChangeHash(S13_MULTIBYTE_CONTENT), expected)
})

test("S13 (TS half): stagePendingContent writes a REAL pending-<hash>.json whose on-disk envelope round-trips the exact multibyte/astral string through JSON.stringify -> disk -> JSON.parse", () => {
  const dir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-gate-s13-"))
  try {
    const hash = stagePendingContent(dir, "write", TIER3_AGENT_FILE, S13_MULTIBYTE_CONTENT)
    const expectedHash = createHash("sha256").update(S13_MULTIBYTE_CONTENT, "utf8").digest("hex")
    assert.equal(hash, expectedHash, "the filename hash must equal the independent sha256(X, utf8)")

    const stagedPath = join(dir, ".gleipnir", "var", "tmp", `pending-${hash}.json`)
    assert.ok(
      existsSync(stagedPath),
      "stagePendingContent must write pending-<hash>.json under .gleipnir/var/tmp",
    )

    const raw = readFileSync(stagedPath, "utf8")
    const envelope = JSON.parse(raw)
    assert.equal(
      envelope.content,
      S13_MULTIBYTE_CONTENT,
      "the envelope content must round-trip byte-for-byte through JSON.stringify -> disk -> JSON.parse",
    )
    assert.equal(envelope.filePath, TIER3_AGENT_FILE)
    assert.equal(envelope.tool, "write")
    assert.equal(typeof envelope.staged_at, "number")

    // The identical re-hash a Python-side `read_bytes()` + `json.loads` +
    // `envelope["content"].encode("utf-8")` + `compute_change_hash(...)`
    // path would independently compute -- this is the exact envelope round
    // trip S13 exercises (not S1's direct-string path, nor S8's in-memory
    // Python-dict path).
    const rehash = createHash("sha256").update(envelope.content, "utf8").digest("hex")
    assert.equal(rehash, expectedHash)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})
