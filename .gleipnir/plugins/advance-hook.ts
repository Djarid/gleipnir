// Gleipnir Seam 7 Phase 2 (`.gleipnir/plans/seam7-seam8-wiring.md`, Assemble
// "Phase 2 — TS post-tool handler (the trigger)") — the TS `tool.execute.after`
// post-tool ADVANCE TRIGGER, sibling to sequence-gate.ts's pre-tool half.
//
// TRUST TIER: Tier-3 enforcement code, agent-unwritable — same footing as
// sequence-gate.ts. `gleipnir-code`'s permission map grants this ONE file
// under `.gleipnir/plugins/` (`.gleipnir/agents/gleipnir-code.md`:
// "advance-hook.ts: allow") but deliberately NOT sequence-gate.ts (Axiom 2 /
// G-1: the guard that polices the agent must stay unreachable to it).
//
// WHAT IT DOES (only when ARMED, mirroring sequence-gate.ts's default-OFF
// posture — see its own header for the full arming rationale, not repeated
// here):
//   * post-tool (`tool.execute.after`): on a completed `task` delegation
//     whose `subagent_type` is a member of the bridge's CURRENT-STATE
//     `allowed_agents` (D6 — symmetric with sequence-gate.ts's pre-tool
//     `isDelegationAllowed` check), shell out to `bin/gleipnir-preflight
//     advance` (the already-built, already-unit-tested Phase-1 Python
//     entrypoint) and FAIL CLOSED (throw) on any non-zero exit / spawn
//     error. This module holds NO advance/mint/HMAC logic of its own — it
//     is the trigger only (D1: call-site-only; all real work happens in
//     `src/gleipnir/preflight/advance.py`, unmodified by this file).
//
// DRY / IMPORT NOTE — an honest, flagged gap; read before "fixing" it.
// The plan's Design Principles ask this file to "import the shared isArmed /
// loadKey / validateMarker / BRIDGE_REL ... from sequence-gate.ts rather than
// duplicating the bridge contract." Reading sequence-gate.ts (as instructed,
// not assuming) shows it exports EXACTLY THREE bindings:
// `validateMarker`, `isDelegationAllowed`, `SequenceGate`. `isArmed`,
// `loadKey`, `readMarker`, `canonicalSigningInput`, and every bridge-path /
// key-env constant (`BRIDGE_REL`, `KEY_ENV`, `ARM_ENV`, `ARM_VALUE`, ...) are
// module-private (no `export` keyword). This file is `gleipnir-code`'s ONLY
// granted write target under `.gleipnir/plugins/` — there is no grant to add
// the missing exports to sequence-gate.ts, and this delegation is explicitly
// instructed not to attempt that edit. So, concretely:
//   * GENUINELY REUSED (not duplicated): `validateMarker` — the delicate,
//     byte-for-byte cross-language HMAC / canonical-signing-input contract —
//     and `isDelegationAllowed` — the exact allowed-agents-membership check
//     D6 asks this hook to mirror. Both are imported below; this file
//     contains NO HMAC computation and NO canonicalSigningInput logic of its
//     own (verified by `tests/test_advance_hook.mjs`'s source-text checks).
//   * DUPLICATED (small, unavoidable given the current export surface): the
//     `BRIDGE_REL` / `KEY_ENV` / `ARM_ENV` / `ARM_VALUE` constants and the
//     tiny `isArmed` / `loadKey` / `readMarker` function BODIES below, kept
//     byte-for-byte equivalent in shape/behavior to sequence-gate.ts's
//     private versions (same paths, same fail-closed semantics). A future
//     Tier-3-authored change adding `export` to those five bindings in
//     sequence-gate.ts would let this duplication be deleted in favor of a
//     straight import — flagged in this delegation's report as a follow-up
//     for the operator, deliberately NOT built here (outside this file's
//     write grant).
//
// INTERIM pipeline_id SOURCE — Phase-2-scoped; NOT a re-opening of D5.
// D5 (CONVERGED) chose the `.gleipnir/var/run/pipeline-run.json` sidecar as
// the mechanism for Phase 3's pipeline_id<->head_sha SHA-correlation problem
// (feeding `fetch-attestation` / `attempt_gate`) — a Phase-3 concern this
// file does not touch (GIT/GATE remain `UnjudgedState`-refused by the
// unmodified Phase-1 `advance.py`). This Phase-2 hook still needs SOME
// `pipeline_id` value to satisfy `bin/gleipnir-preflight advance`'s existing
// REQUIRED `--pipeline-id` flag (Phase 1, unmodified by this delegation).
// Until Phase 3 teaches `advance.py` to source `pipeline_id` internally from
// the sidecar, this hook reads it from `GLEIPNIR_PIPELINE_ID` — the SAME
// session-scoped env-var pattern already used for
// `GLEIPNIR_MARKER_KEY_FILE` / `GLEIPNIR_PIPELINE` (set once by whoever arms
// the run; inherited by every `tool.execute.after` call in this session).
// Missing -> fails closed (throws), never guessed: an armed run with a
// matching delegation but no configured pipeline_id is a misconfiguration,
// not a silent no-op. Phase 3 can replace this env-var read with a sidecar
// read without changing this file's failure semantics.
//
// FAIL-CLOSED (within an armed run): every uncertainty — a bad/missing
// bridge, a bad/missing key, a missing pipeline_id, a missing/non-executable
// preflight CLI, a spawn error, a non-zero advance exit — aborts (throws).
// There is no silent-allow path. Mirrors sequence-gate.ts's and
// git-guard.ts's discipline exactly.
//
// NOT YET CLOSED (honest scope, same as sequence-gate.ts): this enforces AT
// THE HOOK; the hook file, key, and driver source sit in agent-writable
// space until the S-2 mount + terminal closure make them structurally
// unreachable. See `.gleipnir/plans/seam7-seam8-wiring.md` and
// `decisions/engine-state-bridge.md`.
//
// COMPLETION-PASS CORRECTION (closes quality-review Finding A + a latent
// hook-signature defect discovered while fixing it).
//
// Finding A: `capture_and_deposit_reviewer_transcript`
// (`src/gleipnir/preflight/advance.py`, Phase-0 spike) was only ever
// exercised from test files -- nothing on THIS live path ever called it, so
// `read_reviewer_verdict` always returned `None` in a real armed run and the
// SPEC_REVIEW/QUALITY judges always fell through to `NEEDS_HUMAN` regardless
// of what `quality-reviewer` actually said. This pass wires the missing call.
//
// While investigating the EXACT `tool.execute.after` shape needed to extract
// the delegation's returned text (this delegation's mandatory step 1), a
// SECOND, pre-existing defect surfaced: this file's `subagentType` read used
// `output?.args?.subagent_type` -- but per the authoritative pinned opencode
// plugin type (`packages/plugin/src/index.ts@dev`, transcribed verbatim in
// `.gleipnir/plans/hook-probe-findings.md` lines 86-97), the AFTER-hook's
// real signature is:
//
//   "tool.execute.after"?: (
//     input: { tool: string; sessionID: string; callID: string; args: any },
//     output: { title: string; output: string; metadata: any },
//   ) => Promise<void>
//
// `args` (carrying `subagent_type`) lives on INPUT for the after-hook, NOT
// output -- output has no `.args` field at all (it is `{title, output,
// metadata}`). So the old `output?.args?.subagent_type` read was ALWAYS
// `undefined` at runtime: `shouldTriggerAdvance` ALWAYS returned `false`,
// meaning this hook NEVER triggered a live advance for ANY delegation --
// not just the reviewer-transcript case. Fixed here alongside Finding A,
// because a genuinely-working D6 role-check is a precondition for Finding
// A's fix to be exercisable end-to-end at all (the gate this fix relies on
// must actually gate). `output.output` is the field that carries the
// delegation's RETURNED TEXT (`hook-probe-findings.md` lines 100-104: for a
// completed `task`, `task.ts` returns `{ title, metadata, output:
// renderOutput({state: "completed", ...}) }`, where `renderOutput` emits
// `<task id="…" state="completed"><task_result>…</task_result></task>` --
// the subagent's full returned text, wrapped).
//
// Reviewer-transcript capture: when (a) the just-completed delegation's
// `subagent_type` is LITERALLY `"quality-reviewer"` AND (b) the bridge's
// CURRENT state (which D6's `shouldTriggerAdvance` has already confirmed
// this delegation is the bound role for) is `spec_review` or `quality`, this
// hook reads `output.output` (the reviewer's OWN returned text -- NEVER the
// acting agent under review's self-report) and forwards it VERBATIM over
// STDIN to `bin/gleipnir-preflight advance --reviewer-transcript-stdin`.
// Condition (a) is redundant-by-construction with D6's role-check on a
// correctly-configured bridge (only `quality-reviewer` is ever bound to
// spec_review/quality per `stage-role-map.md`) but is kept as an explicit,
// INDEPENDENT second check -- defense in depth, so a misconfigured
// `allowed_agents` entry can never smuggle a non-reviewer's text into the
// deposit. A TEST-state `gleipnir-code` completion satisfies neither (a) nor
// (b), so it is categorically unaffected (asserted in
// `tests/test_advance_hook.mjs`). If the completion DOES satisfy both
// conditions but `output.output` is not a string, this hook throws
// (fail-closed) rather than silently depositing an empty/absent transcript.
//
// STDIN, not argv: an arbitrary reviewer transcript can contain shell-hostile
// bytes, newlines, and unbounded length; argv-passing has execve
// argument-length limits and shell-quoting/escaping hazards, none of which
// stdin has. `runAdvance`'s new optional `stdinInput` param is forwarded
// verbatim to `spawnSync`'s `input` option -- Node's documented mechanism for
// feeding a child process's stdin without a shell.

import { spawnSync } from "node:child_process"
import { accessSync, constants, existsSync, readFileSync } from "node:fs"
import { join } from "node:path"

import { validateMarker, isDelegationAllowed } from "./sequence-gate.ts"

// ---- duplicated-by-necessity constants (see DRY / IMPORT NOTE above) ------
const BRIDGE_REL = ".gleipnir/var/run/pipeline-state.json"
const KEY_ENV = "GLEIPNIR_MARKER_KEY_FILE"
const ARM_ENV = "GLEIPNIR_PIPELINE"
const ARM_VALUE = "on"

// ---- Phase-2-scoped interim pipeline_id source (see note above) ----------
const PIPELINE_ID_ENV = "GLEIPNIR_PIPELINE_ID"

// The out-of-framework preflight CLI. Resolved from the plugin `directory`
// param exactly as sequence-gate.ts resolves its bridge path and
// git-guard.ts resolves this same CLI — never hardcoded to an absolute host
// path.
const PREFLIGHT_REL = "bin/gleipnir-preflight"

interface StateMarker {
  version: number
  pipeline_state: string
  allowed_agents: string[]
  minted_at: number
  mac: string
}

export class AdvanceHookAbort extends Error {}

// Distinct subclass: the preflight CLI itself is missing / non-executable,
// or the advance subprocess could not be spawned at all — a broken
// PREREQUISITE, not a policy/verdict outcome. Mirrors git-guard.ts's
// `PreflightUnavailable` split (same reasoning, independently defined here —
// git-guard.ts does not export a generic cross-plugin version of this to
// reuse).
export class PreflightUnavailable extends AdvanceHookAbort {}

// ---- duplicated-by-necessity helpers (byte-for-byte-equivalent in shape to
// sequence-gate.ts's private isArmed/loadKey/readMarker; see DRY / IMPORT
// NOTE above) ----------------------------------------------------------------

function isArmed(directory: string): boolean {
  if (process.env[ARM_ENV] !== ARM_VALUE) return false
  try {
    // a run is in progress only if the bridge exists; existsSync avoids
    // throwing here (absence => not armed => pass-through, not fail-closed).
    return existsSync(join(directory, BRIDGE_REL))
  } catch {
    return false
  }
}

function loadKey(): Buffer {
  const path = process.env[KEY_ENV]
  if (!path) throw new AdvanceHookAbort(`advance-hook: ${KEY_ENV} not set; fail-closed`)
  const raw = readFileSync(path)
  const trimmed = Buffer.from(raw.toString("utf8").trim(), "utf8")
  if (trimmed.length === 0) throw new AdvanceHookAbort("advance-hook: key is empty; fail-closed")
  return trimmed
}

function readMarker(directory: string): StateMarker {
  const bridgePath = join(directory, BRIDGE_REL)
  let text: string
  try {
    text = readFileSync(bridgePath, "utf8")
  } catch {
    throw new AdvanceHookAbort(`advance-hook: no bridge at ${bridgePath}; fail-closed`)
  }
  let data: any
  try {
    data = JSON.parse(text)
  } catch {
    throw new AdvanceHookAbort("advance-hook: bridge is not valid JSON; fail-closed")
  }
  if (
    typeof data !== "object" ||
    data === null ||
    typeof data.version !== "number" ||
    typeof data.pipeline_state !== "string" ||
    !Array.isArray(data.allowed_agents) ||
    typeof data.minted_at !== "number" ||
    typeof data.mac !== "string"
  ) {
    throw new AdvanceHookAbort("advance-hook: bridge has wrong shape; fail-closed")
  }
  return data as StateMarker
}

// ---- the decision: should this completed delegation trigger an advance? ---
// Pure + exported for tests. GENUINELY reuses `isDelegationAllowed` (D6): the
// same allowed-agents-membership check the pre-tool gate uses to permit a
// dispatch is reused here, symmetrically, to decide whether the
// just-completed delegation is the one the bridge's CURRENT state expects.
// Assumes the caller has already confirmed `tool === "task"` (the hook does
// this before calling in); this function's own job is only the
// subagent_type <-> bound-role check.
export function shouldTriggerAdvance(marker: StateMarker, subagentType: unknown): boolean {
  if (typeof subagentType !== "string" || subagentType.length === 0) return false
  return isDelegationAllowed(marker, subagentType)
}

// Pure argv construction for `bin/gleipnir-preflight advance ...` — exported
// so tests can assert the exact CLI shape without spawning a process.
// `reviewerTranscriptStdin`: when true, appends the `--reviewer-transcript-
// stdin` flag (a flag, not a value — see the STDIN-not-argv note above for
// why the transcript TEXT itself is never an argv element). Omitted/false
// reproduces the exact pre-existing argv shape byte-for-byte (backward
// compatible with the TEST-transition path, which never carries a
// transcript).
export function buildAdvanceArgv(opts: {
  pipelineId: string
  bridgePath: string
  keyFile: string
  reviewerTranscriptStdin?: boolean
}): string[] {
  const argv = [
    "advance",
    "--pipeline-id",
    opts.pipelineId,
    "--bridge-path",
    opts.bridgePath,
    "--key-file",
    opts.keyFile,
  ]
  if (opts.reviewerTranscriptStdin) {
    argv.push("--reviewer-transcript-stdin")
  }
  return argv
}

// Run `bin/gleipnir-preflight <argv>` in `directory` and return its exit
// code + stderr. Exported for the golden-fixture-style test, which drives it
// against a stub CLI in a temp dir (mirrors git-guard.ts's `runConfigScan`).
// `stdinInput`, when provided, is forwarded VERBATIM to `spawnSync`'s
// `input` option — the captured `quality-reviewer` transcript text, piped to
// the child's stdin (never an argv element; see the STDIN-not-argv note
// above). When omitted, this reproduces the EXACT pre-existing spawn options
// (no `input` key at all) so the TEST-transition path's already-covered
// behavior is untouched.
export function runAdvance(
  directory: string,
  argv: string[],
  stdinInput?: string,
): { code: number; stderr: string } {
  const cli = join(directory, PREFLIGHT_REL)
  // Pre-check: is the preflight tool present AND executable? A non-executable
  // or missing CLI is a BROKEN PREREQUISITE, not a policy rejection — surface
  // it distinctly (still fail-closed), mirroring git-guard.ts's identical
  // pre-check for the same CLI.
  try {
    accessSync(cli, constants.X_OK)
  } catch {
    throw new PreflightUnavailable(
      `advance-hook: preflight tool '${cli}' is missing or not executable — run ` +
        `'chmod +x ${PREFLIGHT_REL}' to fix. This is a BROKEN PREREQUISITE, not a ` +
        `policy rejection; fail-closed.`,
    )
  }
  const spawnOpts: { cwd: string; encoding: "utf8"; input?: string } = {
    cwd: directory,
    encoding: "utf8",
  }
  if (stdinInput !== undefined) {
    spawnOpts.input = stdinInput
  }
  const res = spawnSync(cli, argv, spawnOpts)
  if (res.error) {
    throw new PreflightUnavailable(
      `advance-hook: could not run '${cli} ${argv.join(" ")}' (${res.error.message}); ` +
        `broken prerequisite, NOT a policy rejection; fail-closed`,
    )
  }
  // spawnSync sets status to null if the process was killed by a signal.
  if (res.status === null) {
    throw new AdvanceHookAbort(
      `advance-hook: '${cli} ${argv.join(" ")}' terminated by signal ${res.signal}; fail-closed`,
    )
  }
  return { code: res.status, stderr: res.stderr ?? "" }
}

export const AdvanceHook = async ({ directory }: { directory: string }) => {
  return {
    "tool.execute.after": async (
      input: { tool: string; args?: any },
      output: { output?: string },
    ) => {
      // Only this hook's one trigger shape is in scope: a completed `task`
      // delegation. Everything else (reads, edits, other tools) is out of
      // scope and must pass through untouched — mirrors sequence-gate.ts's
      // own `if (input.tool !== "task") return` ordering, checked BEFORE the
      // arming check so an unrelated tool's completion during an armed run
      // never even reaches the fail-closed bridge validation below.
      if (input.tool !== "task") return

      // DEFAULT-OFF, mirroring sequence-gate.ts: unarmed => pure pass-through
      // — never inspects, never shells out, never fails closed (Stress-test
      // #3).
      if (!isArmed(directory)) return

      try {
        const key = loadKey()
        const marker = readMarker(directory)
        if (!validateMarker(marker, key)) {
          throw new AdvanceHookAbort(
            "advance-hook: bridge failed MAC/freshness validation; fail-closed",
          )
        }

        // input.args, not output.args (see the COMPLETION-PASS CORRECTION
        // note above — output has no .args field on the AFTER hook).
        const subagentType = input?.args?.subagent_type
        if (!shouldTriggerAdvance(marker, subagentType)) {
          // Out of scope for this trigger: a malformed task (no/blank
          // subagent_type) or a subagent_type that is NOT the bound role for
          // the bridge's CURRENT state (D6). Not an error — a no-op, exactly
          // as the plan's edge-case table specifies.
          return
        }

        const pipelineId = process.env[PIPELINE_ID_ENV]
        if (!pipelineId) {
          throw new AdvanceHookAbort(
            `advance-hook: ${PIPELINE_ID_ENV} not set; an armed run with a matching ` +
              "delegation but no configured pipeline_id is a misconfiguration, not a " +
              "silent no-op (see the INTERIM pipeline_id SOURCE note above); fail-closed",
          )
        }
        // loadKey() above already proved GLEIPNIR_MARKER_KEY_FILE is set and
        // its content is readable and non-empty; forward the same PATH
        // (never the raw key bytes) to the CLI, which re-reads it itself.
        const keyFilePath = process.env[KEY_ENV] as string
        const bridgePath = join(directory, BRIDGE_REL)

        // Reviewer-transcript capture (closes Finding A) — see the
        // COMPLETION-PASS CORRECTION note above for the full rationale.
        // Two INDEPENDENT conditions, both required: (a) the bridge's
        // CURRENT state (D6 already confirmed subagentType is its bound
        // role) is one of the two transcript-judged states, and (b) the
        // completed delegation's subagent_type is LITERALLY
        // "quality-reviewer" — never the acting agent under review's own
        // self-report (e.g. a TEST-state gleipnir-code completion satisfies
        // neither).
        const isTranscriptJudgedState =
          marker.pipeline_state === "spec_review" || marker.pipeline_state === "quality"
        let reviewerTranscript: string | undefined = undefined
        if (isTranscriptJudgedState && subagentType === "quality-reviewer") {
          if (typeof output?.output !== "string") {
            throw new AdvanceHookAbort(
              "advance-hook: quality-reviewer completion for a transcript-judged " +
                `state (${marker.pipeline_state}) but no output.output string was ` +
                "available to capture; fail-closed rather than deposit nothing " +
                "(never proceed to the judge without a genuine transcript capture)",
            )
          }
          reviewerTranscript = output.output
        }

        const argv = buildAdvanceArgv({
          pipelineId,
          bridgePath,
          keyFile: keyFilePath,
          reviewerTranscriptStdin: reviewerTranscript !== undefined,
        })
        const { code, stderr } = runAdvance(directory, argv, reviewerTranscript)
        if (code !== 0) {
          throw new AdvanceHookAbort(
            `advance-hook: 'bin/gleipnir-preflight advance' exited ${code}; fail-closed, ` +
              `delegation aborted. stderr:\n${stderr}`,
          )
        }
        // exit 0: the Python advance entrypoint succeeded. Its own
        // "advanced to <state>" reporting already covers BOTH a PASS
        // advance and a judged FAIL/NEEDS_HUMAN revert — only a genuine
        // refusal (UnjudgedState / BridgeInvalid / KeyUnavailable / an
        // unanticipated engine fault) exits non-zero, handled above.
      } catch (err) {
        // Fail-closed on ANY error path, not only the enumerated aborts — a
        // stray exception must abort the delegation, never silently allow
        // it. Mirrors sequence-gate.ts's / git-guard.ts's top-level
        // catch-all.
        if (err instanceof AdvanceHookAbort) throw err
        throw new AdvanceHookAbort(
          `advance-hook: unexpected error, failing closed: ${(err as Error)?.message ?? err}`,
        )
      }
    },
  }
}
