/**
 * enginePersistence.ts — SRP: wire the signed engine-position persistence
 * lifecycle (mint-on-transition, persist, rehydrate/validate on resume and
 * compaction), and nothing else. One reason to change: the persistence /
 * lifecycle-hook wiring (D-S5-P3).
 *
 * This is the ONLY module that imports BOTH the pure crypto primitive
 * (`verify/marker.ts`) AND the pi `ExtensionAPI`/`ctx` surface — Boundary B
 * (Design Principles): `verify/marker.ts` computes/validates a marker from
 * explicit arguments and imports no pi runtime; this module owns ALL
 * contact with `pi.on`, `pi.appendEntry`, `ctx.sessionManager` and holds NO
 * HMAC construction of its own (it calls `mintState`/`validateState`, never
 * re-derives the canonical signing input).
 *
 * Lifecycle-hook surface CONFIRMED from primary source this session (plan
 * §Trace): `pi.dev/docs/latest/extensions` (`session_start` reasons incl.
 * `"resume"`; `session_before_compact` event/return contract;
 * `pi.appendEntry(customType, data?)`; `ctx.sessionManager.getEntries()`)
 * and `pi.dev/docs/latest/compaction`.
 *
 * D-S5-P4 (mint-on-transition attachment point): the seam does NOT reach
 * into `Engine.step`/`answerHumanQuestion`/`attemptGate` — those stay
 * pi-runtime-free (AC-PURITY) and byte-unchanged. Instead this module holds
 * a small "current engine" REGISTRY (`setCurrentEngine`/`getCurrentEngine`)
 * that a driver/caller sets after constructing or moving an `Engine`; the
 * driver then calls `mintOnTransition` at the caller edge, after `step`
 * returns, to mint+persist the NEW state. `session_before_compact` reads
 * the SAME registry to persist the position live at compaction time. No
 * `pi-package` driver exists yet (per `allowTable.ts`'s own precedent note:
 * this codebase's orchestrator is the `.gleipnir/agents/orchestrator.md`
 * PROMPT role, not `pi-package` TypeScript) — this registry is the additive
 * seam a future driver attaches to, specified now so the lifecycle wiring
 * is provably correct in isolation (tested against a fake `ExtensionAPI`+
 * `ctx`, the `enforcement.test.ts`/`delegate.test.ts` AC-15 precedent).
 *
 * Fail-closed everywhere (plan §Execution Workflow point 6): ANY doubt in
 * `validateState`, in key-loading, or in reading back a persisted marker
 * results in "do NOT rehydrate" — this module never resumes the engine to
 * an unvalidated marker's state. A key-load/parse failure is caught and
 * treated the same as "no marker" (refuse silently), rather than letting an
 * exception escape a lifecycle hook and abort the whole session — refusal,
 * not a crash, is the fail-closed choice here (plan AC-PERSIST-3 permits
 * either "refuse" or "raise"; this module chooses refuse).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import {
  mintState,
  validateState,
  loadKey,
  stateMarkerFromJson,
  type StateMarker,
} from "./verify/marker.ts";
import { Engine } from "./engine/engine.ts";
import { PipelineState, brandState } from "./engine/state.ts";
import { allowedRolesFor } from "./engine/allowTable.ts";

/** The custom `pi.appendEntry` entry type this seam persists under (DRY —
 * named once, never a repeated literal). */
export const STATE_MARKER_ENTRY_TYPE = "gleipnir.stateMarker";

/** Env var naming the HMAC key file this seam signs/validates with. Reuses
 * the SAME env var name as the proven `.gleipnir/plugins/sequence-gate.ts`
 * reference (`GLEIPNIR_MARKER_KEY_FILE`) rather than inventing a second
 * key-location convention (DRY across the two marker consumers). */
export const MARKER_KEY_ENV = "GLEIPNIR_MARKER_KEY_FILE";

/** ARMING (default-OFF), same convention and SAME env var as the proven
 * `.gleipnir/plugins/sequence-gate.ts` reference (read there ~L71-95):
 * arming is a single cross-cutting posture, not a per-module toggle, so this
 * seam reuses the identical `GLEIPNIR_PIPELINE=on` arm-env-var rather than
 * inventing a second one. Unless armed, the lifecycle handlers below are a
 * pure pass-through: no minting, no persisting, no rehydrating — exactly as
 * if this extension were absent. Fail-closed enforcement (the module header's
 * "refuse, not raise" behaviour) applies ONLY within an armed run. */
const ARM_ENV = "GLEIPNIR_PIPELINE";
const ARM_VALUE = "on";

/** Is this seam armed for the current process? Exported so tests can assert
 * the no-op-when-unarmed behaviour without reaching into module internals. */
export function isArmed(): boolean {
  return process.env[ARM_ENV] === ARM_VALUE;
}

/** Load this seam's signing/validation key from `MARKER_KEY_ENV`, fail-closed
 * (via `verify/marker.ts`'s `loadKey`/`KeyUnavailable`). Exported so tests can
 * exercise the same loader the handlers use, without re-deriving it. */
export function loadMarkerKey(): Buffer {
  return loadKey(process.env[MARKER_KEY_ENV]);
}

// ---------------------------------------------------------------------------
// The "current engine" registry (D-S5-P4's caller/driver edge). A future
// driver constructs/moves an `Engine` and registers it here; this module
// never constructs an `Engine` on its own initiative except when rehydrating
// from a VALIDATED marker (resume/compaction-rebuild).
// ---------------------------------------------------------------------------

let currentEngine: Engine | null = null;

/** The driver/caller registers its `Engine` here after construction or after
 * every successful `step`/`answerHumanQuestion`/`attemptGate` call — the
 * ADDITIVE caller-edge attachment point (D-S5-P4). Never called from inside
 * `engine/engine.ts` itself. */
export function setCurrentEngine(engine: Engine | null): void {
  currentEngine = engine;
}

/** The engine this seam currently believes is live, or `null` if none has
 * been registered (e.g. before the driver's first construction, or after a
 * failed rehydration). */
export function getCurrentEngine(): Engine | null {
  return currentEngine;
}

/** Test-only reset so module-scope registry state does not leak across test
 * cases (mirrors `depth.ts`'s `resetDepth()` idiom). */
export function resetCurrentEngineForTestOnly(): void {
  currentEngine = null;
}

// ---------------------------------------------------------------------------
// Mint + persist
// ---------------------------------------------------------------------------

/**
 * Mint a `StateMarker` for `state`, projecting `allowed_agents` from the S4
 * `allowedRolesFor` derivation (idiom-table row 9) — never a hand-copied
 * state->role list (DRY, the `bridge.py` docstring's "no second sequencing
 * authority").
 */
export function mintForState(
  state: PipelineState,
  key: Buffer,
  mintedAt?: number,
): StateMarker {
  const allowedAgents = [...allowedRolesFor(state)].sort();
  return mintState(state, allowedAgents, key, mintedAt);
}

/** Persist `marker` via the pi runtime's `pi.appendEntry` (the ONLY primitive
 * this seam uses for durable storage — session persistence "survives
 * restarts via `pi.appendEntry()`", per the confirmed primary source). */
export function persistMarker(
  pi: Pick<ExtensionAPI, "appendEntry">,
  marker: StateMarker,
): void {
  pi.appendEntry(STATE_MARKER_ENTRY_TYPE, marker);
}

/**
 * Mint-on-transition at the caller/driver edge (D-S5-P4): mint a marker for
 * the CURRENT registered engine's state and persist it. Returns the minted
 * marker, or `null` if no engine is currently registered (nothing to mint —
 * NOT an error; a driver that has not yet constructed an engine simply has
 * nothing to persist).
 */
export function mintOnTransition(
  pi: Pick<ExtensionAPI, "appendEntry">,
  key: Buffer,
  mintedAt?: number,
): StateMarker | null {
  const engine = getCurrentEngine();
  if (engine === null) return null;
  const marker = mintForState(engine.state, key, mintedAt);
  persistMarker(pi, marker);
  return marker;
}

// ---------------------------------------------------------------------------
// Read-back + rehydrate
// ---------------------------------------------------------------------------

/** The minimal `ctx.sessionManager` surface this seam reads (confirmed
 * primary source: `getEntries()` returns every persisted entry). Narrowed to
 * exactly what is used (Interface Segregation) rather than importing the
 * SDK's full `SessionManager` type. */
export interface MarkerReadableSessionManager {
  getEntries(): ReadonlyArray<{ customType?: string; data?: unknown }>;
}

/**
 * Read the LATEST persisted `StateMarker` entry from `ctx.sessionManager`
 * (filter by `STATE_MARKER_ENTRY_TYPE`, take the last — entries are
 * append-only in arrival order). Returns `undefined` if none is present or
 * if the latest one's payload does not shape-validate (fail-closed via
 * `stateMarkerFromJson`'s JSON round-trip guard: any malformed/missing/
 * wrong-type payload is treated as "no marker", never a thrown surprise out
 * of a read-back helper).
 */
export function readLatestMarker(
  ctx: { sessionManager: MarkerReadableSessionManager },
): StateMarker | undefined {
  const entries = ctx.sessionManager.getEntries();
  for (let i = entries.length - 1; i >= 0; i -= 1) {
    const entry = entries[i];
    if (entry?.customType !== STATE_MARKER_ENTRY_TYPE) continue;
    try {
      // Round-trip through the shape-validating JSON path (never trust the
      // stored `data` shape directly) — `stateMarkerFromJson` throws on
      // malformed/missing/wrong-type input, which this read-back path
      // treats as "no usable marker" rather than propagating.
      return stateMarkerFromJson(JSON.stringify(entry.data));
    } catch {
      return undefined;
    }
  }
  return undefined;
}

/**
 * Validate `marker` under `key` and, if (and ONLY if) it validates, rehydrate
 * a fresh `Engine` positioned at `marker.pipeline_state` via
 * `Engine.resumeAt` + `brandState` (D-S5-3). Fail-closed: any doubt
 * (`marker` absent, invalid MAC, stale, wrong version, or a `pipeline_state`
 * value that has since stopped being a genuine `PipelineState` member)
 * returns `null` — the seam NEVER rehydrates to an unvalidated marker's
 * state.
 */
export function rehydrateFromMarker(
  marker: StateMarker | undefined,
  key: Buffer,
  pipelineId: string,
  opts: { maxAgeSeconds?: number; now?: number } = {},
): Engine | null {
  if (marker === undefined) return null;
  if (!validateState(marker, key, opts)) return null;
  // `brandState` itself re-validates via `isPipelineState` and throws on a
  // non-member value (defence in depth: a VALIDATED marker's
  // `pipeline_state` should already be a genuine member, since minting only
  // ever writes real `PipelineState` values — but this seam still does not
  // trust that invariant blindly).
  try {
    return Engine.resumeAt(pipelineId, brandState(marker.pipeline_state as PipelineState));
  } catch {
    return null;
  }
}

/**
 * The full fail-closed read+validate+rehydrate path a `session_start(resume)`
 * or a post-compaction rebuild uses (same path both times, per the plan).
 * On success, registers the rehydrated engine as `currentEngine` (so a
 * subsequent `mintOnTransition`/`session_before_compact` call has something
 * to persist) and returns it; on any failure returns `null` and leaves the
 * registry untouched (refuse, not raise — see module header).
 */
export function rehydrate(
  ctx: { sessionManager: MarkerReadableSessionManager },
  pipelineId: string,
  opts: { maxAgeSeconds?: number; now?: number } = {},
): Engine | null {
  let key: Buffer;
  try {
    key = loadMarkerKey();
  } catch {
    return null;
  }
  const marker = readLatestMarker(ctx);
  const engine = rehydrateFromMarker(marker, key, pipelineId, opts);
  if (engine !== null) {
    setCurrentEngine(engine);
  }
  return engine;
}

// ---------------------------------------------------------------------------
// The extension entrypoint
// ---------------------------------------------------------------------------

/** `session_start` reasons that rehydrate from a persisted marker. Per the
 * confirmed primary source + plan AC-PERSIST-5: ONLY `"resume"` — a
 * fresh/new/forked session does not inherit a resumed position, and
 * `"startup"`/`"reload"` are left as no-ops here too (not named by any
 * plan AC; a narrower default is the fail-closed direction). Named once
 * (DRY) rather than repeated as a literal in the handler and in tests. */
export const RESUME_REASON = "resume";

/**
 * Register the two lifecycle handlers (Boundary B: the ONLY pi-runtime
 * contact point for the marker machinery).
 *
 * - `session_start`: on `reason === RESUME_REASON`, read back the latest
 *   persisted marker, validate it, and rehydrate — fail-closed on any doubt
 *   (does NOT throw out of the handler; a failed rehydration simply leaves
 *   no engine registered, per module header).
 * - `session_before_compact`: mint+persist the CURRENT registered engine's
 *   position (if any) BEFORE compaction discards volatile context, then
 *   returns `undefined` (does not cancel compaction). The rebuild side reads
 *   this same persisted marker back via the identical `rehydrate` path.
 */
export default function enginePersistence(pi: ExtensionAPI): void {
  pi.on("session_start", async (event: { reason?: string }, ctx: any) => {
    // DEFAULT-OFF: unless the operator has armed this run
    // (GLEIPNIR_PIPELINE=on, the SAME arm-env-var as sequence-gate.ts), this
    // handler is a pure no-op — no read-back, no validation, no rehydration.
    if (!isArmed()) return undefined;
    if (event?.reason !== RESUME_REASON) return undefined;
    if (!ctx?.sessionManager) return undefined;
    const engine = getCurrentEngine();
    const pipelineId = engine?.pipelineId ?? "resumed-pipeline";
    rehydrate(ctx, pipelineId);
    return undefined;
  });

  pi.on("session_before_compact", async (_event: unknown, ctx: any) => {
    // DEFAULT-OFF: same arming gate as session_start above — unarmed, this
    // handler mints nothing and persists nothing.
    if (!isArmed()) return undefined;
    try {
      const key = loadMarkerKey();
      mintOnTransition(pi, key);
    } catch {
      // Fail-closed: a key/mint failure at compaction time must not abort
      // compaction itself — it simply means this transition's position was
      // not durably persisted (the rebuild side's read-back will then find
      // no fresher marker than the last successful mint, which is the
      // correct degraded behaviour, not a crash).
    }
    return undefined;
  });
}
