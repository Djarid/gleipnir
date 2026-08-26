/**
 * verify/marker.ts — SRP: construct + validate a keyed-HMAC `StateMarker`,
 * and nothing else. One reason to change: the marker crypto construction.
 *
 * Ports (oracle, semantics frozen): `src/gleipnir/engine/bridge.py` L54-192
 * (`StateMarker`, `mint_state`, `validate_state`, `_canonical_signing_input`)
 * + `src/gleipnir/verify/marker.py` L86-106 (`load_key` fail-closed shape,
 * reused by `bridge.py`, not re-derived). Byte-parity precedent:
 * `.gleipnir/plugins/sequence-gate.ts` L103-174 (`validateMarker`/
 * `canonicalSigningInput`/`loadKey`), already proven against
 * `tests/fixtures/golden_marker*.json` — this module reproduces the SAME
 * canonical signing input byte-for-byte (idiom-table row 2) and the SAME
 * `timingSafeEqual` equal-length guard (row 4).
 *
 * PURITY (AC-PURITY): imports ONLY `node:crypto` + `node:fs`. No pi
 * runtime, no `engine/*` value import. `enginePersistence.ts` is the ONLY
 * module that imports both this module and the pi runtime (Boundary B,
 * D-S5-P3).
 *
 * Boundary A (Design Principles): this module owns the HMAC `StateMarker`
 * construction and NOTHING about the GATE `Attestation` value; it does not
 * import or construct `engine/attestation.ts`'s `Attestation` (D-S5-P2).
 */

import { createHmac, timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";

/** Frozen wire-contract constants (idiom-table row 6) — values frozen to
 * the Python oracle, never re-derived. */
export const STATE_MARKER_VERSION = 1;
export const FIELD_SEP = "\x1f";
export const AGENT_SEP = "\x1e";
export const DEFAULT_MAX_AGE_SECONDS = 3600;
export const DIGEST = "sha256";

/** The wire/JSON shape (idiom-table row 1) — matches the proven
 * `sequence-gate.ts` `StateMarker` interface exactly, so the golden
 * fixtures parse directly into this shape with no transformation. A plain
 * `interface` (no brand): this is a wire VALUE, not a security-load-bearing
 * runtime tag like `Attestation` — the MAC, not a TS brand, is what makes a
 * `StateMarker` trustworthy. */
export interface StateMarker {
  version: number;
  pipeline_state: string;
  allowed_agents: string[];
  minted_at: number;
  mac: string;
}

/** Base for every marker fault (idiom-table row 7's `from_json` analogue) —
 * a typed `Error` subclass with `.name` set (mirrors `depth.ts`'s
 * `DepthCapExceededError` idiom). */
export class StateMarkerError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StateMarkerError";
  }
}

/** `loadKey` fail-closed (idiom-table row 5): no path / empty file /
 * unreadable file all raise this, never a partial/garbage key. */
export class KeyUnavailable extends StateMarkerError {
  constructor(message: string) {
    super(message);
    this.name = "KeyUnavailable";
  }
}

/**
 * The exact bytes the MAC covers (idiom-table row 2) — byte-identical to
 * `sequence-gate.ts`'s `canonicalSigningInput` (already proven against the
 * golden fixtures) and to `bridge.py::_canonical_signing_input`.
 * `allowed_agents` is sorted before joining so an honestly-produced
 * marker's wire order never affects validity, while any CONTENT change (an
 * added, removed, or one-byte-mutated agent name) changes the joined
 * string and therefore the MAC.
 */
export function canonicalSigningInput(
  version: number,
  pipelineState: string,
  allowedAgents: readonly string[],
  mintedAt: number,
): string {
  const agentsJoined = [...allowedAgents].map(String).sort().join(AGENT_SEP);
  return [String(version), pipelineState, agentsJoined, String(mintedAt)].join(FIELD_SEP);
}

/**
 * Fail-closed key load (idiom-table row 5): read + trim; empty/absent/
 * unreadable all throw `KeyUnavailable`. Mirrors
 * `verify/marker.py::load_key` + `sequence-gate.ts::loadKey` exactly — no
 * key, no mint, no validate.
 */
export function loadKey(path: string | undefined): Buffer {
  if (!path) {
    throw new KeyUnavailable("verify/marker: no key path supplied; fail-closed");
  }
  let raw: Buffer;
  try {
    raw = readFileSync(path);
  } catch (err) {
    throw new KeyUnavailable(
      `verify/marker: cannot read key at ${path}: ${(err as Error)?.message ?? err}`,
    );
  }
  const trimmed = Buffer.from(raw.toString("utf8").trim(), "utf8");
  if (trimmed.length === 0) {
    throw new KeyUnavailable(`verify/marker: key at ${path} is empty`);
  }
  return trimmed;
}

/**
 * Produce a signed marker. Requires the key — the one operation an agent
 * without it cannot perform (mirrors `bridge.py::mint_state`).
 */
export function mintState(
  pipelineState: string,
  allowedAgents: readonly string[],
  key: Buffer,
  mintedAt?: number,
): StateMarker {
  const ts = mintedAt ?? Math.floor(Date.now() / 1000);
  const agentsSorted = [...allowedAgents].map(String).sort();
  const signingInput = canonicalSigningInput(
    STATE_MARKER_VERSION,
    pipelineState,
    agentsSorted,
    ts,
  );
  const mac = createHmac(DIGEST, key).update(signingInput, "utf8").digest("hex");
  return {
    version: STATE_MARKER_VERSION,
    pipeline_state: pipelineState,
    allowed_agents: agentsSorted,
    minted_at: ts,
    mac,
  };
}

/**
 * Validate a marker. Fail-closed on ANY doubt: returns `false`, never
 * throws, for a merely-invalid marker (mirrors `bridge.py::validate_state`
 * / `sequence-gate.ts::validateMarker`). The `timingSafeEqual` equal-length
 * guard runs BEFORE the constant-time compare (D-S5-2 sub-point —
 * `timingSafeEqual` throws on unequal-length buffers, which would turn a
 * forged/tampered marker into an uncaught exception instead of a clean
 * `false`).
 */
export function validateState(
  marker: StateMarker,
  key: Buffer,
  opts: { maxAgeSeconds?: number; now?: number } = {},
): boolean {
  if (marker.version !== STATE_MARKER_VERSION) return false;

  const signingInput = canonicalSigningInput(
    marker.version,
    marker.pipeline_state,
    marker.allowed_agents,
    marker.minted_at,
  );
  const expected = createHmac(DIGEST, key).update(signingInput, "utf8").digest("hex");
  const got = Buffer.from(marker.mac, "utf8");
  const exp = Buffer.from(expected, "utf8");
  if (got.length !== exp.length) return false;
  if (!timingSafeEqual(got, exp)) return false;

  const maxAge = opts.maxAgeSeconds ?? DEFAULT_MAX_AGE_SECONDS;
  const now = opts.now ?? Math.floor(Date.now() / 1000);
  const age = now - marker.minted_at;
  if (age < 0 || age > maxAge) return false;

  return true;
}

/**
 * JSON round-trip (idiom-table row 7): shape-validate, throw
 * `StateMarkerError` on malformed/missing/wrong-type input — the
 * `from_json` analogue (`test_bridge.py` L153-175).
 */
export function stateMarkerFromJson(text: string): StateMarker {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (err) {
    throw new StateMarkerError(
      `bridge payload is not valid JSON: ${(err as Error)?.message ?? err}`,
    );
  }
  if (typeof data !== "object" || data === null) {
    throw new StateMarkerError("bridge payload is missing/invalid fields: not an object");
  }
  const d = data as Record<string, unknown>;
  if (
    typeof d.version !== "number" ||
    typeof d.pipeline_state !== "string" ||
    !Array.isArray(d.allowed_agents) ||
    !d.allowed_agents.every((a) => typeof a === "string") ||
    typeof d.minted_at !== "number" ||
    typeof d.mac !== "string"
  ) {
    throw new StateMarkerError("bridge payload is missing/invalid fields");
  }
  return {
    version: d.version,
    pipeline_state: d.pipeline_state,
    allowed_agents: [...(d.allowed_agents as string[])],
    minted_at: d.minted_at,
    mac: d.mac,
  };
}

/** `to_json` analogue: a plain, stable JSON serialisation (no ordering
 * guarantee is load-bearing here — `stateMarkerFromJson` shape-validates on
 * the way back in, so key order never matters). */
export function stateMarkerToJson(marker: StateMarker): string {
  return JSON.stringify(marker);
}
