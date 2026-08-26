/**
 * enginePersistence.test.ts — the correctness arbiter for the D-S5-3
 * `resumeAt` brand-check hardening AND the `enginePersistence.ts` 4b
 * signed-persistence lifecycle seam (plan Assemble step 3b; AC-BRAND-1..3,
 * AC-PERSIST-1..5).
 *
 * Per the plan's residual (§Trace): the lifecycle hooks fire inside a LIVE
 * pi session, which cannot be exercised under `--network=none` — so these
 * tests register a minimal fake `ExtensionAPI` (`.on`/`.appendEntry`) and a
 * fake `ctx.sessionManager` (`.getEntries()` returning seeded entries),
 * capture the two handlers `enginePersistence.ts` installs, and invoke them
 * directly (the exact `enforcement.test.ts`/`delegate.test.ts` AC-15
 * precedent).
 */

import assert from "node:assert/strict";
import { after, afterEach, before, describe, test } from "node:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { PipelineState, brandState, type BrandedPipelineState } from "../src/engine/state.ts";
import { Engine, InvalidVerdict, Verdict, type Judge } from "../src/engine/engine.ts";
import { allowedRolesFor } from "../src/engine/allowTable.ts";
import { validateState, mintState, type StateMarker } from "../src/verify/marker.ts";
import enginePersistence, {
  STATE_MARKER_ENTRY_TYPE,
  MARKER_KEY_ENV,
  RESUME_REASON,
  mintForState,
  mintOnTransition,
  persistMarker,
  readLatestMarker,
  rehydrate,
  rehydrateFromMarker,
  setCurrentEngine,
  getCurrentEngine,
  resetCurrentEngineForTestOnly,
} from "../src/enginePersistence.ts";

const PIPELINE_ID = "pl-g5-s5-persistence-test";
const KEY = Buffer.from("engine-persistence-test-key-not-a-real-secret", "utf8");
const WRONG_KEY = Buffer.from("a-different-guessed-key", "utf8");

function makePassJudge(): Judge {
  return (_state, _payload) => Verdict.PASS;
}

// ---------------------------------------------------------------------------
// Fakes — the AC-15 precedent (fake ExtensionAPI, no live pi runtime).
// ---------------------------------------------------------------------------

interface FakeEntry {
  customType?: string;
  data?: unknown;
}

type SessionStartHandler = (
  event: { reason?: string },
  ctx: { sessionManager: { getEntries(): FakeEntry[] } },
) => Promise<undefined>;

type BeforeCompactHandler = (
  event: unknown,
  ctx: { sessionManager: { getEntries(): FakeEntry[] } },
) => Promise<undefined>;

function installPersistence(): {
  sessionStart: SessionStartHandler;
  sessionBeforeCompact: BeforeCompactHandler;
  store: FakeEntry[];
} {
  const store: FakeEntry[] = [];
  let sessionStart: SessionStartHandler | undefined;
  let sessionBeforeCompact: BeforeCompactHandler | undefined;
  const fakePi = {
    on(name: string, fn: SessionStartHandler | BeforeCompactHandler) {
      if (name === "session_start") {
        sessionStart = fn as SessionStartHandler;
      } else if (name === "session_before_compact") {
        sessionBeforeCompact = fn as BeforeCompactHandler;
      }
    },
    appendEntry(customType: string, data?: unknown) {
      store.push({ customType, data });
    },
  };
  enginePersistence(fakePi as unknown as Parameters<typeof enginePersistence>[0]);
  assert.ok(sessionStart, "enginePersistence() must register a session_start handler");
  assert.ok(
    sessionBeforeCompact,
    "enginePersistence() must register a session_before_compact handler",
  );
  return {
    sessionStart: sessionStart as SessionStartHandler,
    sessionBeforeCompact: sessionBeforeCompact as BeforeCompactHandler,
    store,
  };
}

function ctxWith(store: FakeEntry[]) {
  return { sessionManager: { getEntries: () => store } };
}

// ---------------------------------------------------------------------------
// AC-BRAND-1..3 — the D-S5-3 resumeAt brand-check hardening.
// ---------------------------------------------------------------------------

describe("resumeAt brand-check hardening (D-S5-3)", () => {
  test("AC-BRAND-1: resumeAt(id, brandState('spec_review')) succeeds; state is spec_review", () => {
    const engine = Engine.resumeAt(PIPELINE_ID, brandState(PipelineState.SPEC_REVIEW));
    assert.equal(engine.state, PipelineState.SPEC_REVIEW);
  });

  test("AC-BRAND-2: resumeAt(id, 'spec_review') (raw same-valued string) throws InvalidVerdict", () => {
    assert.throws(
      () =>
        Engine.resumeAt(
          PIPELINE_ID,
          PipelineState.SPEC_REVIEW as unknown as BrandedPipelineState,
        ),
      InvalidVerdict,
      "a raw string equal to a genuine PipelineState value must now be rejected — this is the S4-deferred gap S5 closes",
    );
  });

  test("AC-BRAND-3: resumeAt(id, 'not_a_state') (non-member string) still throws — no regression", () => {
    assert.throws(
      () => Engine.resumeAt(PIPELINE_ID, "not_a_state" as unknown as BrandedPipelineState),
      InvalidVerdict,
    );
  });
});

// ---------------------------------------------------------------------------
// AC-PERSIST-1 — mint-on-transition round-trip (no pi runtime needed; the
// caller/driver edge is exercised directly with an explicit key).
// ---------------------------------------------------------------------------

describe("mint-on-transition (D-S5-P4 caller/driver edge)", () => {
  afterEach(() => {
    resetCurrentEngineForTestOnly();
  });

  test("AC-PERSIST-1: mints + persists a marker for the new state; allowed_agents matches allowedRolesFor(newState) sorted; validates true", () => {
    const engine = new Engine(PIPELINE_ID);
    setCurrentEngine(engine);
    const result = engine.step(makePassJudge()); // BRAINSTORM -> PLAN
    assert.equal(result.state, PipelineState.PLAN);

    const appended: FakeEntry[] = [];
    const fakePi = {
      appendEntry(customType: string, data?: unknown) {
        appended.push({ customType, data });
      },
    };
    const marker = mintOnTransition(fakePi, KEY);

    assert.ok(marker !== null, "mintOnTransition must mint when an engine is registered");
    assert.equal((marker as StateMarker).pipeline_state, PipelineState.PLAN);
    assert.deepEqual(
      (marker as StateMarker).allowed_agents,
      [...allowedRolesFor(PipelineState.PLAN)].sort(),
    );
    assert.equal(validateState(marker as StateMarker, KEY), true);

    assert.equal(appended.length, 1);
    assert.equal(appended[0].customType, STATE_MARKER_ENTRY_TYPE);
    assert.deepEqual(appended[0].data, marker);
  });

  test("mintOnTransition returns null when no engine is registered (nothing to mint, not an error)", () => {
    resetCurrentEngineForTestOnly();
    assert.equal(getCurrentEngine(), null);
    const fakePi = { appendEntry() {} };
    assert.equal(mintOnTransition(fakePi, KEY), null);
  });

  test("persistMarker calls pi.appendEntry with STATE_MARKER_ENTRY_TYPE and the marker as data", () => {
    const marker = mintForState(PipelineState.CODE, KEY);
    const appended: FakeEntry[] = [];
    persistMarker({ appendEntry: (t, d) => appended.push({ customType: t, data: d }) }, marker);
    assert.equal(appended.length, 1);
    assert.equal(appended[0].customType, STATE_MARKER_ENTRY_TYPE);
    assert.deepEqual(appended[0].data, marker);
  });
});

// ---------------------------------------------------------------------------
// AC-PERSIST-2..5 — the session_start(resume) / session_before_compact
// lifecycle handlers, against the fake ExtensionAPI + ctx.
// ---------------------------------------------------------------------------

describe("signed-persistence lifecycle (session_start/session_before_compact)", () => {
  let tmpDir: string;
  let keyPath: string;

  before(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "gleipnir-enginepersistence-"));
    keyPath = join(tmpDir, "key");
    writeFileSync(keyPath, KEY);
    process.env[MARKER_KEY_ENV] = keyPath;
    // These tests exercise the ARMED behaviour of the session_start /
    // session_before_compact handlers directly — the unarmed no-op path is
    // covered separately below ("arming (default-off, GLEIPNIR_PIPELINE)").
    // Literal env var name, matching tests/test_sequence_gate.mjs's
    // convention (the arm-env-var is not exported by either module under
    // test — tests set it by its known name, same as the sequence-gate
    // test suite does).
    process.env["GLEIPNIR_PIPELINE"] = "on";
  });

  after(() => {
    delete process.env[MARKER_KEY_ENV];
    delete process.env["GLEIPNIR_PIPELINE"];
    rmSync(tmpDir, { recursive: true, force: true });
  });

  afterEach(() => {
    resetCurrentEngineForTestOnly();
  });

  test("AC-PERSIST-2: session_start(resume) with a seeded valid marker rehydrates the engine at marker.pipeline_state", async () => {
    const { sessionStart, store } = installPersistence();
    const marker = mintState(PipelineState.QUALITY, ["quality-reviewer"], KEY);
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: marker });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    const engine = getCurrentEngine();
    assert.ok(engine !== null, "a valid seeded marker must result in a rehydrated engine");
    assert.equal((engine as Engine).state, PipelineState.QUALITY);
  });

  test("AC-PERSIST-3a: session_start(resume) with a forged marker (bogus MAC) does NOT rehydrate", async () => {
    const { sessionStart, store } = installPersistence();
    const forged: StateMarker = {
      version: 1,
      pipeline_state: PipelineState.GATE,
      allowed_agents: [],
      minted_at: Math.floor(Date.now() / 1000),
      mac: "deadbeef".repeat(8),
    };
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: forged });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    assert.equal(getCurrentEngine(), null, "a forged marker must never rehydrate the engine");
  });

  test("AC-PERSIST-3b: session_start(resume) with a stale marker does NOT rehydrate", async () => {
    const { sessionStart, store } = installPersistence();
    // minted_at far in the past relative to real now; default max age (3600s)
    // makes this unconditionally stale.
    const stale = mintState(PipelineState.PLAN, ["gleipnir-plan"], KEY, 1000);
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: stale });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    assert.equal(getCurrentEngine(), null, "a stale marker must never rehydrate the engine");
  });

  test("AC-PERSIST-3c: session_start(resume) with a tampered marker (pipeline_state flipped, mac reused) does NOT rehydrate", async () => {
    const { sessionStart, store } = installPersistence();
    const genuine = mintState(PipelineState.PLAN, ["gleipnir-plan"], KEY);
    const tampered: StateMarker = { ...genuine, pipeline_state: PipelineState.GIT, mac: genuine.mac };
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: tampered });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    assert.equal(getCurrentEngine(), null, "a tampered marker must never rehydrate the engine");
  });

  test("AC-PERSIST-3d: session_start(resume) with a marker minted under the wrong key does NOT rehydrate", async () => {
    const { sessionStart, store } = installPersistence();
    const wrongKeyed = mintState(PipelineState.PLAN, ["gleipnir-plan"], WRONG_KEY);
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: wrongKeyed });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    assert.equal(getCurrentEngine(), null, "a wrong-key marker must never rehydrate the engine");
  });

  test("AC-PERSIST-3e: session_start(resume) with NO persisted marker does NOT rehydrate", async () => {
    const { sessionStart, store } = installPersistence();
    // store deliberately left empty.
    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    assert.equal(getCurrentEngine(), null, "no marker present must never rehydrate the engine");
  });

  test("AC-PERSIST-4: session_before_compact persists the current position (and does not cancel compaction); a subsequent read+validate+resumeAt recovers the exact pre-compaction state", async () => {
    const { sessionBeforeCompact, store } = installPersistence();

    const engine = new Engine(PIPELINE_ID);
    engine.step(makePassJudge()); // -> PLAN
    engine.step(makePassJudge()); // -> SPEC_REVIEW
    setCurrentEngine(engine);
    const preCompactState = engine.state;

    const returnValue = await sessionBeforeCompact(undefined, ctxWith(store));
    assert.equal(returnValue, undefined, "must not cancel compaction ({cancel:true})");
    assert.equal(store.length, 1, "session_before_compact must persist exactly one marker entry");
    assert.equal(store[0].customType, STATE_MARKER_ENTRY_TYPE);

    // Simulate the rebuild side: the in-memory registry is gone (a fresh
    // process/session), recovery must come ONLY from the persisted marker.
    resetCurrentEngineForTestOnly();
    assert.equal(getCurrentEngine(), null);

    const rehydrated = rehydrate(ctxWith(store), PIPELINE_ID);
    assert.ok(rehydrated !== null, "the rebuild side must recover a valid persisted marker");
    assert.equal((rehydrated as Engine).state, preCompactState);
  });

  test("AC-PERSIST-5: session_start(reason in {startup, new, fork}) does NOT rehydrate even with a valid seeded marker", async () => {
    for (const reason of ["startup", "new", "fork"] as const) {
      const { sessionStart, store } = installPersistence();
      const marker = mintState(PipelineState.CODE, ["gleipnir-code"], KEY);
      store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: marker });

      await sessionStart({ reason }, ctxWith(store));

      assert.equal(
        getCurrentEngine(),
        null,
        `reason "${reason}" must not rehydrate from a prior marker`,
      );
      resetCurrentEngineForTestOnly();
    }
  });
});

// ---------------------------------------------------------------------------
// Direct unit coverage of the read-back / rehydrate helpers (independent of
// the handler wiring above — proves the helpers themselves, not just their
// composition through the handlers).
// ---------------------------------------------------------------------------

describe("readLatestMarker / rehydrateFromMarker helpers", () => {
  test("readLatestMarker returns undefined when the store has no marker entries", () => {
    const ctx = ctxWith([{ customType: "something-else", data: { a: 1 } }]);
    assert.equal(readLatestMarker(ctx), undefined);
  });

  test("readLatestMarker returns the LATEST marker entry when multiple are present", () => {
    const older = mintState(PipelineState.PLAN, ["gleipnir-plan"], KEY, 1000);
    const newer = mintState(PipelineState.CODE, ["gleipnir-code"], KEY, 2000);
    const ctx = ctxWith([
      { customType: STATE_MARKER_ENTRY_TYPE, data: older },
      { customType: "unrelated", data: {} },
      { customType: STATE_MARKER_ENTRY_TYPE, data: newer },
    ]);
    assert.deepEqual(readLatestMarker(ctx), newer);
  });

  test("readLatestMarker returns undefined for a malformed marker payload (fail-closed, not a throw)", () => {
    const ctx = ctxWith([{ customType: STATE_MARKER_ENTRY_TYPE, data: { version: 1 } }]);
    assert.equal(readLatestMarker(ctx), undefined);
  });

  test("rehydrateFromMarker returns null for an undefined marker", () => {
    assert.equal(rehydrateFromMarker(undefined, KEY, PIPELINE_ID), null);
  });

  test("rehydrateFromMarker returns a live Engine for a genuine marker, positioned at pipeline_state", () => {
    const marker = mintState(PipelineState.TEST, ["gleipnir-code"], KEY);
    const engine = rehydrateFromMarker(marker, KEY, PIPELINE_ID);
    assert.ok(engine !== null);
    assert.equal((engine as Engine).state, PipelineState.TEST);
    // and it is a LIVE engine, not a frozen snapshot: it can still step.
    const result = (engine as Engine).step(makePassJudge());
    assert.equal(result.state, PipelineState.CODE);
  });
});

// ---------------------------------------------------------------------------
// AC-ARM-1..3 — the ARMED-DEFAULT-OFF wiring (operator-converged fix): the
// two lifecycle handlers must no-op (no mint, no persist, no rehydrate)
// unless GLEIPNIR_PIPELINE === "on" at call time — the SAME arm-env-var/
// value pair as the proven `.gleipnir/plugins/sequence-gate.ts` reference,
// asserted here the same way `tests/test_sequence_gate.mjs` asserts its
// own UNARMED pass-through cases.
// ---------------------------------------------------------------------------

describe("arming (default-off, GLEIPNIR_PIPELINE) — enginePersistence.ts lifecycle handlers", () => {
  let tmpDir: string;
  let keyPath: string;

  before(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "gleipnir-enginepersistence-armtest-"));
    keyPath = join(tmpDir, "key");
    writeFileSync(keyPath, KEY);
    process.env[MARKER_KEY_ENV] = keyPath;
  });

  after(() => {
    delete process.env[MARKER_KEY_ENV];
    rmSync(tmpDir, { recursive: true, force: true });
  });

  afterEach(() => {
    resetCurrentEngineForTestOnly();
    delete process.env["GLEIPNIR_PIPELINE"];
  });

  test("AC-ARM-1: session_start(resume) with a VALID seeded marker does NOT rehydrate when GLEIPNIR_PIPELINE is unset", async () => {
    delete process.env["GLEIPNIR_PIPELINE"];
    const { sessionStart, store } = installPersistence();
    const marker = mintState(PipelineState.QUALITY, ["quality-reviewer"], KEY);
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: marker });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    assert.equal(
      getCurrentEngine(),
      null,
      "unarmed session_start must never rehydrate, even with a genuine, fresh, correctly-keyed marker present",
    );
  });

  test("AC-ARM-2: session_before_compact does NOT mint or call pi.appendEntry when GLEIPNIR_PIPELINE is unset", async () => {
    delete process.env["GLEIPNIR_PIPELINE"];
    const { sessionBeforeCompact, store } = installPersistence();

    const engine = new Engine(PIPELINE_ID);
    engine.step(makePassJudge()); // BRAINSTORM -> PLAN
    setCurrentEngine(engine);

    const returnValue = await sessionBeforeCompact(undefined, ctxWith(store));
    assert.equal(returnValue, undefined, "must not cancel compaction even while unarmed");
    assert.equal(
      store.length,
      0,
      "unarmed session_before_compact must not call pi.appendEntry / persist any marker entry",
    );
  });

  test("AC-ARM-3: arming reversibility — the SAME seeded marker DOES rehydrate once GLEIPNIR_PIPELINE=\"on\"", async () => {
    process.env["GLEIPNIR_PIPELINE"] = "on";
    const { sessionStart, store } = installPersistence();
    const marker = mintState(PipelineState.QUALITY, ["quality-reviewer"], KEY);
    store.push({ customType: STATE_MARKER_ENTRY_TYPE, data: marker });

    await sessionStart({ reason: RESUME_REASON }, ctxWith(store));

    const engine = getCurrentEngine();
    assert.ok(engine !== null, "armed session_start with a valid marker must rehydrate");
    assert.equal((engine as Engine).state, PipelineState.QUALITY);
  });
});
