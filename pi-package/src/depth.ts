/**
 * depth.ts — SRP: the delegation depth counter + cap, and nothing else
 * (D4: in-extension module-scope counter; persistence via `pi.appendEntry`
 * is deferred to S3, not needed to prove the cap mechanism in-process).
 *
 * `withDepthGuard` is the safety-critical shape: the counter is decremented
 * in a `finally` block so it is restored even if the guarded function
 * throws (AC-8) — including nested delegation, where each level's `enter()`
 * is paired with its own `finally`-guaranteed `exit()` (AC-7).
 */

export class DepthCapExceededError extends Error {
  constructor(depth: number, cap: number) {
    super(
      `delegate: depth cap (${cap}) exceeded at depth ${depth}; refusing to create another child session`,
    );
    this.name = "DepthCapExceededError";
  }
}

const DEFAULT_CAP = 3;

let depth = 0;
let cap = DEFAULT_CAP;

/** Current delegation depth (0 = no delegation in flight). */
export function getDepth(): number {
  return depth;
}

/** Current cap. */
export function getCap(): number {
  return cap;
}

/** Test-only override of the cap (S1 proof needs a small cap to exercise it). */
export function setCap(newCap: number): void {
  if (!Number.isInteger(newCap) || newCap < 0) {
    throw new RangeError("depth cap must be a non-negative integer");
  }
  cap = newCap;
}

/** Test-only reset between test cases so state does not leak across them. */
export function resetDepth(): void {
  depth = 0;
}

/**
 * Enter one delegation level. Throws `DepthCapExceededError` (refusing,
 * not silently allowing) once `depth === cap`. Does NOT increment on
 * refusal.
 */
export function enter(): void {
  if (depth >= cap) {
    throw new DepthCapExceededError(depth, cap);
  }
  depth += 1;
}

/** Exit one delegation level. Never goes negative. */
export function exit(): void {
  if (depth > 0) {
    depth -= 1;
  }
}

/**
 * Run `fn` guarded by the depth cap: `enter()` before, `exit()` in a
 * `finally` after — so the counter is restored even if `fn` throws
 * (AC-8), and refusal (`enter()` throwing) propagates to the caller
 * before `fn` ever runs.
 */
export async function withDepthGuard<T>(fn: () => Promise<T>): Promise<T> {
  enter();
  try {
    return await fn();
  } finally {
    exit();
  }
}
