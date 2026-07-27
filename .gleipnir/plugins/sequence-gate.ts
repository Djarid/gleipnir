// Gleipnir G-5 wire-in — the structural sequencing gate (Tier-3 enforcement code).
//
// This opencode plugin makes the (otherwise inert) G-5 engine actually BLOCK
// out-of-order delegations. It is the enforcement seat named in spec S-1 point 1
// (`tool.execute.before`, "inspect typed arguments and throw to abort").
//
// TRUST TIER: this file is Tier-3 enforcement code — operator-authored,
// agent-unwritable. No roster agent (not even gleipnir-code) may edit it. It is
// the guard; it must not be reachable by the guarded (Axiom 2 / G-1).
//
// WHAT IT DOES
//   * pre-tool (`tool.execute.before`): on a `task` delegation, read the
//     digest-protected bridge file, validate its HMAC + freshness (fail-closed),
//     then check the dispatched `subagent_type` against the allowed-agents set
//     the bridge carries for the current pipeline state. If the agent is not
//     allowed — or ANYTHING is uncertain (missing/corrupt/tampered/stale bridge,
//     bad key, unknown state) — THROW to abort. opencode never spawns the
//     subagent.
//   * post-tool (`tool.execute.after`): on a `task` that returned cleanly,
//     advance the engine via the Python driver (mechanically observed, non-agent
//     — the completion signal is the tool returning, never an agent's report).
//
// CROSS-LANGUAGE MAC CONTRACT (the delicate part, golden-fixture tested):
//   The bridge marker is minted by Python (src/gleipnir/engine/bridge.py). This
//   hook must reproduce that canonical signing input BYTE-FOR-BYTE:
//     agents_joined = sorted(allowed_agents).join("\x1e")
//     signing_input = [version, pipeline_state, agents_joined, minted_at]
//                       .join("\x1f")   (each field UTF-8)
//     mac = HMAC_SHA256(key, signing_input).hex()
//   tests/fixtures/golden_marker.json (+ _tampered) prove this hook validates a
//   genuine Python-minted marker and rejects a one-byte-tampered one.
//
// FAIL-CLOSED: every uncertainty is an abort. There is no allow-by-default path
// and no host/self-report fallback. Any unhandled error also aborts (see the
// top-level try/catch in the hook).
//
// NOT YET CLOSED (honest scope): this enforces AT THE HOOK. The hook file, the
// key, and the driver source still sit in agent-writable space until the S-2
// mount + terminal closure make them structurally unreachable. See
// .gleipnir/plans/engine-wire-in.md and decisions/engine-state-bridge.md.

import { createHmac, timingSafeEqual } from "node:crypto"
import { readFileSync } from "node:fs"
import { join } from "node:path"

// ---- constants mirrored from the Python side (single source of truth is
// Python; these are the wire contract the golden fixture pins) --------------

const STATE_MARKER_VERSION = 1
const FIELD_SEP = "\x1f"
const AGENT_SEP = "\x1e"
const DEFAULT_MAX_AGE_SECONDS = 3600

// Bridge + key locations. The bridge is framework-written, agent-read-only
// (Tier-3-strength). The key lives outside the agent surface (S-2 boundary);
// here it is read from GLEIPNIR_MARKER_KEY_FILE.
const BRIDGE_REL = ".gleipnir/var/run/pipeline-state.json"
const KEY_ENV = "GLEIPNIR_MARKER_KEY_FILE"

interface StateMarker {
  version: number
  pipeline_state: string
  allowed_agents: string[]
  minted_at: number
  mac: string
}

class GateAbort extends Error {}

function canonicalSigningInput(m: StateMarker): string {
  const agentsJoined = [...m.allowed_agents].sort().join(AGENT_SEP)
  return [String(m.version), m.pipeline_state, agentsJoined, String(m.minted_at)].join(
    FIELD_SEP,
  )
}

function loadKey(): Buffer {
  const path = process.env[KEY_ENV]
  if (!path) throw new GateAbort(`sequence-gate: ${KEY_ENV} not set; fail-closed`)
  const raw = readFileSync(path)
  const trimmed = Buffer.from(raw.toString("utf8").trim(), "utf8")
  if (trimmed.length === 0) throw new GateAbort("sequence-gate: key is empty; fail-closed")
  return trimmed
}

function readMarker(directory: string): StateMarker {
  const bridgePath = join(directory, BRIDGE_REL)
  let text: string
  try {
    text = readFileSync(bridgePath, "utf8")
  } catch {
    throw new GateAbort(`sequence-gate: no bridge at ${bridgePath}; fail-closed`)
  }
  let data: any
  try {
    data = JSON.parse(text)
  } catch {
    throw new GateAbort("sequence-gate: bridge is not valid JSON; fail-closed")
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
    throw new GateAbort("sequence-gate: bridge has wrong shape; fail-closed")
  }
  return data as StateMarker
}

// Exported for the golden-fixture conformance test.
export function validateMarker(
  m: StateMarker,
  key: Buffer,
  opts: { maxAgeSeconds?: number; now?: number } = {},
): boolean {
  if (m.version !== STATE_MARKER_VERSION) return false
  const expected = createHmac("sha256", key).update(canonicalSigningInput(m), "utf8").digest("hex")
  const got = Buffer.from(m.mac, "utf8")
  const exp = Buffer.from(expected, "utf8")
  if (got.length !== exp.length) return false
  if (!timingSafeEqual(got, exp)) return false
  const maxAge = opts.maxAgeSeconds ?? DEFAULT_MAX_AGE_SECONDS
  const now = opts.now ?? Math.floor(Date.now() / 1000)
  const age = now - m.minted_at
  if (age < 0 || age > maxAge) return false
  return true
}

// The decision: may `subagent_type` be dispatched given the validated bridge?
// Pure + exported for tests. Any doubt already threw before reaching here; this
// only says allowed/denied against the bridge's own allowed_agents list.
export function isDelegationAllowed(m: StateMarker, subagentType: string): boolean {
  return m.allowed_agents.includes(subagentType)
}

export const SequenceGate = async ({ directory }: { directory: string }) => {
  return {
    "tool.execute.before": async (
      input: { tool: string },
      output: { args: any },
    ) => {
      // Only gate `task` delegations; other tools are out of this gate's scope.
      if (input.tool !== "task") return

      try {
        const subagentType = output?.args?.subagent_type
        if (typeof subagentType !== "string" || subagentType.length === 0) {
          throw new GateAbort("sequence-gate: task without subagent_type; fail-closed")
        }
        const key = loadKey()
        const marker = readMarker(directory)
        if (!validateMarker(marker, key)) {
          throw new GateAbort(
            "sequence-gate: bridge failed MAC/freshness validation; fail-closed",
          )
        }
        if (!isDelegationAllowed(marker, subagentType)) {
          throw new GateAbort(
            `sequence-gate: '${subagentType}' is not an allowed delegation while ` +
              `the pipeline is in state '${marker.pipeline_state}'. Allowed: ` +
              `[${marker.allowed_agents.join(", ")}]. Aborted.`,
          )
        }
        // allowed: fall through, let opencode spawn the subagent.
      } catch (err) {
        // Fail-closed on ANY error path, not only the enumerated GateAborts —
        // a stray exception must abort the delegation, never silently allow it.
        if (err instanceof GateAbort) throw err
        throw new GateAbort(
          `sequence-gate: unexpected error, failing closed: ${(err as Error)?.message ?? err}`,
        )
      }
    },
  }
}
