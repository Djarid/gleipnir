# Plan: Armed-Run Dogfood — proving the composed G-5 loop end-to-end

**Stage:** plan. **Author:** gleipnir-plan. **Tier:** 0 (this file), disposable.
**Planned FROM** the operator-converged decision D1–D5 (LOCKED below; captured,
not re-decided). Where D1–D5 name a bounded implementation choice, this plan
decides-and-justifies it; it opens no material tradeoff.

## Converged decisions (LOCKED — captured verbatim in intent)

- **D1** — Advance is **out-of-band**: a test harness / operator-driven caller
  drives the *already-built* Python loop (`Driver.advance` → `engine.step` →
  `write_bridge` re-mint → `EventBus.emit`). Advance is **mechanical** via the
  existing `_trivial_completion_judge` (always-PASS on clean completion,
  **payload-blind** — must NEVER read agent output; that would be
  self-attestation). The live TS `tool.execute.after` hook is a **named next
  seam (Seam 7)**, not built. Advance is explicitly **not** attestation-bound
  (real CI sourcing into G-3.2 is **Seam 8**).
- **D2** — The run forces **at least one real QUALITY→CODE revert** (drive
  forward to QUALITY, then a FAIL judge at QUALITY reverts to CODE) to exercise
  the revert edge + `RevertOccurredEvent` emit + ledger reduce/reconcile.
- **D3** — The dogfood runs preflight under the operator-override
  **PROCEED_UNCLOSED** path with `DEV_MODE_LABEL` (honest: single-uid dev box,
  G-1 not closed), **and separately asserts `run_preflight` REFUSES** given a
  writable enforcement file and/or absent key — proving the gate works even
  though the live run proceeds under override.
- **D4** — Honest cross-language **split** harness: (i) an automated pytest
  exercising the Python loop end-to-end; (ii) the TS armed sequence-gate proven
  via its existing arming + golden-fixture tests **plus** a Python-minted-bridge
  cross-language check. A single harness cannot cleanly run both languages live —
  do not force one.
- **D5** — "Proven" = **end-to-end assertions**, not "it ran". Automatable-now
  assertions **1–6** (restated concretely in Stress-test). Seams **7** (live
  opencode `tool.execute.before/after`) and **8** (real CI verifier feeding
  `attempt_gate`/G-3.2 sourcing) are **named, documented as not-yet-automated,
  and NOT claimed**.

---

## 1. Architect

**Problem (one sentence).** Every piece of the G-5 loop is unit-tested in
isolation, but their *composition* into one armed run — driver-advance →
engine-step → bridge re-mint → bus emit → ledger reduce/reconcile → preflight,
plus the Python↔TS bridge contract — is unproven, and that integration gap is
exactly where a fail-open could hide.

**User.** The operator dogfooding Gleipnir on itself (and, downstream, the
release gate that must trust the composed loop, not just its parts).

**Measurable success.**
1. Assertions **1–6** (Stress-test §5) pass in-sandbox (`bin/gleipnir-sandbox`),
   Python side, plus the node cross-language check.
2. Seams **7** and **8** are present in the plan and in the harness as explicit
   labelled comments/gaps — **claimed as not-yet-automated, never as passing.**
3. The full existing suite stays green (baseline count **confirmed by the
   implementer at build time** via an actual `bin/gleipnir-sandbox test` run —
   see the Stress-test cross-cutting note; do not rely on a cited fixed number,
   which could mask a regression); new work is stdlib-only on the Python side
   and reuses existing TS test infra on the node side.

**Constraints (load-bearing).**
- **No self-attestation.** The advance judge must be **payload-blind**. Forward
  hops use `_trivial_completion_judge` (always-PASS, ignores payload); the forced
  revert uses a **fixed-verdict FAIL judge** that likewise ignores state/payload
  (mirror `test_driver_emits_revert.FixedJudge`). Neither reads agent output.
  The harness asserts this structurally (§5, assertion-blind check).
- **No overclaim.** Assertions are end-to-end value checks, not "no exception
  raised". A passing `reconcile` *is* an assertion (it raises `LedgerError` on
  divergence).
- **Stdlib-only** for the Python harness (`decisions/runtime-and-deps.md`):
  `pathlib`, `os`, `json` at most; no third-party deps. Uses `pytest` as the
  existing test runner (already the suite's runner), and only the already-built
  `gleipnir.*` modules.
- **TS side uses existing infra** — `node --test`, the existing
  `tests/test_sequence_gate.mjs`, and the existing `tests/fixtures/golden_*`.
- **Advance is NOT attestation-bound.** The dogfood drives `Driver.advance`/
  `Engine.step`; it does **not** call `attempt_gate` with a real attestation
  (that is Seam 8). If the run reaches GIT, `attempt_gate` is out of scope for the
  automated assertions — GIT has no PASS edge by design.

**Explicitly NOT in scope (named, not silently dropped).**
- Building the live `tool.execute.after` post-tool advance hook (**Seam 7**).
- Sourcing a real CI/verifier `Attestation` into `attempt_gate` (**Seam 8**,
  G-3.2 binding).
- Any edit to Tier-3 (`plugins/`, `agents/`, `keys/`, `decisions/`) or to
  `src/` engine/bus/ledger/preflight modules — this delegation adds **tests
  only**. The harness is the composition proof over code that already exists.

---

## 2. Trace

### 2.1 Artifacts and where they live (source of truth)

| Artifact | Path | New / existing |
|---|---|---|
| Python end-to-end dogfood harness | `tests/test_armed_run_dogfood.py` | **new** |
| Python-minted PLAN-state bridge fixture (written by the harness at runtime) | `tests/fixtures/dogfood_bridge.json` (written under a `tmp_path`, then a *committed* golden copy — see 2.3) | **new (runtime + optional committed golden)** |
| Cross-language node assertion | extend `tests/test_sequence_gate.mjs` (new `test(...)` block) | **edit (test-only, Tier-0-equivalent test file)** |
| Shared key fixture | reuse `tests/fixtures/golden_key.bin` (`golden-fixture-key-do-not-use-in-prod`, NOT a secret — see `tests/fixtures/README.md`) | **existing** |
| Consumed source (unchanged) | `src/gleipnir/engine/{__init__,driver,bridge,allow_table}.py`, `src/gleipnir/bus/{emit,events}.py`, `src/gleipnir/ledger/{reduce,reconcile}.py`, `src/gleipnir/preflight/boundary.py`, `.gleipnir/plugins/sequence-gate.ts` | **existing, read-only** |

The plan file itself is **Tier-0** (`.gleipnir/plans/`), the only thing this
planning stage writes. All harness code is authored later by the bound
implementation role, per the pipeline.

### 2.2 Integration map — the composed loop the harness drives

```
[preflight]  run_preflight(config_root, uid, gid, override_ack=True, write_probe=fake->WRITE_OK)
      │  PROCEED_UNCLOSED (dev-mode)          run_preflight(..., writable-file+override_ack=False / absent-key) -> REFUSE
      ▼
[Driver(pipeline_id, bridge_path, key_file=shared_key, bus=EventBus(session, logs_dir=tmp))]
      │  advance(_trivial_completion_judge)  x N   (BRAINSTORM->PLAN->...->QUALITY)
      │      each hop: engine.step -> write_bridge re-mint -> (no emit; forward)
      │      assertion 1: validate each re-minted bridge (validate_state / resume_from_bridge)
      │  advance(FIXED_FAIL_JUDGE)  at QUALITY
      │      engine.step FAIL -> QUALITY(5)->CODE(4) revert; write_bridge re-mint;
      │      _emit_revert_if_any -> ONE RevertOccurredEvent to session JSONL
      ▼
[.gleipnir/logs/<session>.jsonl]  (here: tmp logs_dir)
      │  reduce(session_log) -> LedgerReport (assertion 3)
      │  reconcile(session_log, report) -> agrees or raises LedgerError (assertion 4)
      ▼
[cross-language handshake]  Driver.write_bridge at PLAN -> dogfood_bridge.json (on disk)
      │  (Python side, this run's key = golden_key.bin)
      ▼
[node test]  validateMarker(loaded_bridge, golden_key) == true; tampered == false;
             isDelegationAllowed(bridge,"git-ops")==false; ("gleipnir-plan")==true   (assertion 5)
```

### 2.3 The cross-language handshake — decided mechanism (D4-b resolved)

**Decision: on-disk, Python-minted bridge + shared key fixture; the node test
loads it.** This matches exactly how the existing golden fixtures already work
(`test_sequence_gate.mjs` loads a Python-minted `golden_marker.json` and the
Python `golden_key.bin`). No in-process cross-language call is attempted (Python
cannot cleanly call the TS `validateMarker` in-process, and forcing it would be
the "single harness runs both languages live" trap D4 forbids). The two sides
**meet at the on-disk bridge + a shared key fixture** — that is the contract.

Concretely there are **two provably-equivalent forms**, and the plan takes both,
cheaply:

1. **Already-covered form (no new bytes needed to be true today).** The existing
   `golden_marker.json` *is* a Python-minted bridge at **state `plan`**,
   `allowed_agents=["gleipnir-plan"]`, signed with `golden_key.bin`. The existing
   `test_sequence_gate.mjs` **already asserts** `validateMarker(genuine)==true`,
   `validateMarker(tampered)==false`, `isDelegationAllowed(genuine,"gleipnir-plan")==true`,
   and `isDelegationAllowed(genuine,"git-ops")==false`. **Assertion 5 is therefore
   already met by committed, passing tests** — the plan's job is to *name* this as
   the cross-language proof, not to re-invent it.
2. **Live-mint form (proves the loop, not just the frozen fixture).** The Python
   dogfood harness, running its own `Driver` with `GLEIPNIR_MARKER_KEY_FILE`
   pointed at `golden_key.bin`, drives the engine to **PLAN** and calls
   `Driver.write_bridge(minted_at=1000)`, writing the marker to
   `tests/fixtures/dogfood_bridge.json` (regeneration is idempotent; committed so
   the node test is self-contained and reproducible, exactly like
   `golden_marker.json`). A **new `test(...)` block in `test_sequence_gate.mjs`**
   loads `dogfood_bridge.json` + `golden_key.bin` and re-asserts the same four
   facts. This proves the *live driver mint path* — not just a frozen fixture —
   satisfies the TS validator byte-for-byte.

The plan **requires form 1** (it is free and already green) and **recommends
form 2** as the honest "the live loop, not a hand-frozen file, meets the TS
gate" proof. Both use the same `golden_key.bin` on both sides — **that shared key
fixture is the answer to D4-a: yes, the Python harness sets
`GLEIPNIR_MARKER_KEY_FILE` (or passes `key_file=`) to `golden_key.bin`, and the
same file feeds the node check.**

> Note (honest, minted_at — **fixed vs current, and the SYMMETRIC freshness
> override both sides must apply**): there are two distinct classes of bridge in
> this harness, and only one needs a freshness override:
>
> 1. **Committed cross-language fixture (FIXED `minted_at=1000`).** Both
>    `golden_marker.json` and the live-minted-but-committed `dogfood_bridge.json`
>    are minted at `minted_at=1000` so their bytes are stable and the node test
>    is reproducible. Because `1000` is far in the past relative to real
>    wall-clock `now (~1.7e9)`, **every freshness-checking call against these
>    fixtures — on BOTH languages — must override the freshness window**, or the
>    MAC-valid marker is (correctly) rejected as stale:
>    - **Node side:** pass `validateMarker(marker, key, { maxAgeSeconds: HUGE,
>      now: 1001 })` — as the existing golden test already does — so the MAC (not
>      freshness) is what is asserted.
>    - **Python side (the previously-silent half):** `validate_state(marker, key,
>      now=1001)` (its signature is `validate_state(marker, key,
>      max_age_seconds=DEFAULT_MAX_AGE_SECONDS, now=None)`; passing `now=1001`
>      makes `age = 1001 - 1000 = 1` well within the 3600s default — symmetric to
>      the node `now: 1001`). Equivalently `validate_state(marker, key,
>      max_age_seconds=10**12)` works; the plan specifies **`now=1001`** as the
>      canonical override for the Python fixed-`minted_at` checks. **Without this
>      override the assertion FAILS**: `validate_state`'s default `now=time.time()`
>      makes `age = now(~1.7e9) - 1000 >> 3600` => returns `False`.
>    - **`resume_from_bridge` against the fixed fixture:** its signature is
>      `resume_from_bridge(pipeline_id, bridge_path, key_file=None,
>      max_age_seconds=None, bus=None)` — it has **NO `now=` parameter**; it
>      forwards only `max_age_seconds` to `validate_state` (and lets `now` default
>      to real wall-clock). So a `resume_from_bridge` call against a
>      fixed-`minted_at=1000` bridge **must pass a large `max_age_seconds`** (e.g.
>      `max_age_seconds=10**12`); it cannot use the `now=` trick. This is the one
>      place the two override forms diverge and the implementer must not
>      copy-paste `now=1001` where only `max_age_seconds` is accepted.
> 2. **Forward-run bridges (LIVE/current `minted_at`).** The forward-run part of
>    the harness (Assertion 1, re-mint at each hop) does **not** need any
>    override: mint those bridges with a realistic/current `minted_at` (i.e. call
>    `advance(...)` / `write_bridge()` with `minted_at=None` so it defaults to
>    `int(time.time())`), and their `validate_state` / `resume_from_bridge` checks
>    pass freshness **naturally** with default `now`/`max_age_seconds`. Only the
>    committed fixed-`minted_at=1000` fixture (class 1) needs the explicit
>    override.

### 2.4 How the QUALITY→CODE revert is forced (D2, D-question-c resolved)

- Drive forward BRAINSTORM→…→QUALITY with `Driver.advance()` using the default
  `_trivial_completion_judge` (payload-blind PASS). Per `PIPELINE_ORDER` and
  `TRANSITIONS`, this reaches QUALITY without any FAIL edge (BRAINSTORM→PLAN→
  SPEC_REVIEW→TEST→CODE→QUALITY are all PASS hops).
- At QUALITY, call `driver.advance(FIXED_FAIL_JUDGE)` where `FIXED_FAIL_JUDGE`
  is a fixed-verdict judge returning `Verdict.FAIL` **ignoring state and payload**
  (reuse the shape of `tests/test_driver_emits_revert.FixedJudge(Verdict.FAIL)`).
  `TRANSITIONS[QUALITY][FAIL] == CODE` (backward, 5→4), so `engine.step`
  increments `revert_count` to 1 (default budget 3, no escalation), transitions to
  CODE, `write_bridge` re-mints at CODE, and `_emit_revert_if_any` emits **exactly
  one** `RevertOccurredEvent(from_state="quality", to_state="code",
  revert_count=1, escalated=False)`.
- **Confirmed payload-blind (no self-attestation):** the FAIL judge is injected
  via `Driver.advance(judge=...)` (the driver's `advance` already accepts an
  injected judge, defaulting to `_trivial_completion_judge`), and it ignores its
  `state`/`payload` args entirely — it is a *fixed verdict*, not a reading of
  work output. Forward hops likewise use the payload-blind trivial judge.

### 2.5 How the EventBus is wired + where the session JSONL lands

- Construct `EventBus(session_id=<test-session>, logs_dir=<tmp_path>/logs)` and
  pass it to `Driver(..., bus=bus)`. Per `bus/emit.py`, the JSONL lands at
  `<tmp_path>/logs/<session_id>.jsonl`. Using a `tmp_path` `logs_dir` keeps the
  dogfood out of the real Tier-1 `.gleipnir/logs/` and makes reduce/reconcile read
  a single-session file the test fully controls.
- Read events back with `Event.from_json_line` (typed read path) for assertion 2,
  exactly as `test_driver_emits_revert._read_events` does.

### 2.6 How preflight is exercised (D3 resolved)

- **PROCEED_UNCLOSED path:** call `run_preflight(config_root, agent_uid,
  agent_gid, override_ack=True, write_probe=<fake returning **WRITE_OK**>,
  read_probe=<fake returning **WRITE_OK**>)` with `GLEIPNIR_MARKER_KEY_FILE`
  pointed at a present non-empty key so `check_key_state` is `PRESENT`. **The
  probe MUST return `WRITE_OK`, not `WRITE_DENIED`** — WRITE_OK honestly
  represents a *writable* enforcement file / no uid separation on a single-uid
  dev box, i.e. the boundary is NOT closed. Per `boundary.py` `decide()` +
  `classify_probe_result`, `WRITE_OK` => `ProbeVerdict.NOT_CLOSED` => (with
  `override_ack=True`) `Verdict.PROCEED_UNCLOSED` stamped `DEV_MODE_LABEL`;
  `decide()` has **no code path from `override_ack=True` to `CLOSED`**, so this
  can never accidentally read as CLOSED. (Note the polarity: all-denied
  (`WRITE_DENIED`) + present key => `CLOSED`, the *opposite* of what this test
  wants — cf. the existing passing
  `test_run_preflight_closed_when_all_denied_and_key_env_points_at_key`, which
  uses `WRITE_DENIED` fakes precisely to reach CLOSED. This override path mirrors
  `test_run_preflight_override_never_reaches_closed`, which uses a `WRITE_OK`
  fake.) Injected probe edges keep this deterministic and root-independent.

  > **Framing honesty (MINOR fix — pick REAL probes to make the claim live).**
  > This sub-assertion is authored with a **first, no-injection call to the REAL
  > default probes** (`run_preflight(config_root, agent_uid=os.getuid(),
  > agent_gid=os.getgid(), override_ack=True)` — omit `write_probe`/`read_probe`
  > so the real `probe_write_as_agent`/`probe_read_key_as_agent` fork-edge runs
  > against the actual repo `.gleipnir` enforcement paths). On a single-uid box
  > the drop is skipped and the real writes land `WRITE_OK` => NOT_CLOSED =>
  > under override `PROCEED_UNCLOSED` — the genuine dev-box verdict, an honest
  > claim about the live boundary (not merely re-exercising `decide()`'s pure
  > logic, which `test_preflight_decision.py` already covers). The
  > injected-`WRITE_OK`-fake variant, if kept, is retained **only** for
  > determinism and is labelled in the harness as re-testing `decide()`'s logic,
  > **not** a claim about the live boundary. (Real-probes-once is the chosen
  > resolution; the fake variant is optional and, if present, so-labelled.)
- **REFUSE path (proves the gate bites):** call `run_preflight(...,
  override_ack=False, write_probe=<fake returning WRITE_OK for an enforcement
  file>)` → verdict **`REFUSE`** (writable file, no override); and separately
  with an **absent key** (`GLEIPNIR_MARKER_KEY_FILE` unset / pointing at a
  missing file → `KeyState.ABSENT`) → verdict **`REFUSE`**. This is assertion 6.
  (These two REFUSE sub-assertions were already correct and are unchanged.)

### 2.7 D-question-a resolved (shared key fixture)

**Yes.** The Python harness sets `GLEIPNIR_MARKER_KEY_FILE` to (or passes
`key_file=`) the shared `tests/fixtures/golden_key.bin` so `write_bridge` /
`validate_state` round-trip, **and the same file feeds the node cross-language
check.** `write_bridge` and `resume_from_bridge` both `load_key` fail-closed, so
a present shared key is required for the round-trip and for the on-disk handshake
to validate on both sides. (The preflight REFUSE-on-absent-key sub-case
deliberately uses a *different*, absent key env to exercise the failure — it is a
separate call, not the loop's key.)

### 2.8 Edge cases

- **Reaching QUALITY exactly once before the revert** — assert `driver.state is
  PipelineState.QUALITY` before injecting the FAIL judge, so the revert is from
  the intended edge, not an accidental earlier state.
- **Exactly one revert event** — after the single FAIL advance, assert the JSONL
  has exactly one `REVERT_OCCURRED` line (forward PASS hops emit nothing, per
  `_emit_revert_if_any` branch C).
- **Vacuous vs real escalation_rate** — with `revert_count==1, escalation_count==0`,
  `reduce` yields a **real** `escalation_rate` `Measured(value=0.0, denominator=1)`
  (NOT the vacuous `value=None` sentinel, which only applies at
  `revert_count==0`). Assertion 3 checks `value == 0.0` and `denominator == 1`.
- **`minted_at` determinism + symmetric freshness override** — pass
  `minted_at=1000` to `write_bridge` **only** for the committed cross-language
  handshake bridge (class-1, §2.3) so `dogfood_bridge.json` is byte-stable; then
  **both** language sides must override freshness against it — node
  `{ maxAgeSeconds: HUGE, now: 1001 }`, Python `validate_state(..., now=1001)`
  (or `resume_from_bridge(..., max_age_seconds=10**12)`, which has no `now=`) —
  or the stale MAC-valid marker is (correctly) rejected. The forward-run bridges
  (Assertion 1) instead use a live/current `minted_at` and need no override.
- **tmp isolation** — everything writable (bridge, logs, preflight fixtures) lives
  under `pytest`'s `tmp_path`, except the two committed fixtures
  (`golden_key.bin` existing; `dogfood_bridge.json` if form 2 is committed).

---

## 3. Link — validated before building

- **Confirmed** `Driver.advance(judge=..., *, minted_at, agent, originating_turn)`
  accepts an injected judge and defaults to `_trivial_completion_judge`
  (payload-blind). ✓ (`engine/driver.py` L193-238)
- **Confirmed** `TRANSITIONS[QUALITY][FAIL] == CODE`, backward 5→4, counts once
  against the global budget (default 3 → no escalation on the first FAIL). ✓
  (`engine/__init__.py` L173-179, L411-435)
- **Confirmed** `_emit_revert_if_any` emits `RevertOccurredEvent(from="quality",
  to="code", revert_count, escalated=False)` for a normal backward revert. ✓
  (`driver.py` L240-293)
- **Confirmed** `reduce` produces `revert_count/escalation_count/escalation_rate`
  and the vacuous-vs-real rate convention; `reconcile` raises `LedgerError` on
  divergence and a passing reconcile is the assertion. ✓ (`ledger/reduce.py`,
  `ledger/reconcile.py`)
- **Confirmed** `run_preflight(..., override_ack=..., write_probe=, read_probe=)`
  with injectable probe edges yields `PROCEED_UNCLOSED`/`REFUSE`/`CLOSED`, and
  `DEV_MODE_LABEL` on the override path. ✓ (`preflight/boundary.py` L977-1004,
  L508-555)
- **Confirmed the probe polarity (BLOCKER-2 fix):** in `decide()` +
  `classify_probe_result`, a `WRITE_OK` write-probe => `ProbeVerdict.NOT_CLOSED`
  => (with `override_ack=True`) `Verdict.PROCEED_UNCLOSED`/`DEV_MODE_LABEL`,
  never `CLOSED`; whereas all-`WRITE_DENIED` + present key => `CLOSED`. So the
  PROCEED_UNCLOSED test uses a **`WRITE_OK`** probe. ✓ (`boundary.py` L317-337,
  L508-555; matched by existing `test_run_preflight_override_never_reaches_closed`
  (WRITE_OK→PROCEED_UNCLOSED) vs
  `test_run_preflight_closed_when_all_denied_and_key_env_points_at_key`
  (WRITE_DENIED→CLOSED))
- **Confirmed the freshness signatures (BLOCKER-1 fix):**
  `validate_state(marker, key, max_age_seconds=DEFAULT_MAX_AGE_SECONDS,
  now=None)` — a fixed-`minted_at=1000` fixture requires `now=1001` (or large
  `max_age_seconds`) or `age = time.time() - 1000 >> 3600` returns False.
  `resume_from_bridge(pipeline_id, bridge_path, key_file=None,
  max_age_seconds=None, bus=None)` has **no `now=`** and forwards only
  `max_age_seconds` to `validate_state` (letting `now` default to wall-clock), so
  a fixed-fixture `resume_from_bridge` must pass `max_age_seconds=10**12`.
  Forward-run bridges minted at current `minted_at` need no override. ✓
  (`engine/bridge.py` L157-192; `engine/driver.py` L108-163, L177-191)
- **Confirmed** the TS gate reads its runtime bridge from
  `.gleipnir/var/run/pipeline-state.json` (irrelevant to the on-disk fixture
  handshake, which loads a file path directly) and exports pure
  `validateMarker` / `isDelegationAllowed` for tests. ✓ (`plugins/sequence-gate.ts`)
- **Confirmed** `golden_marker.json` = Python-minted PLAN-state bridge
  (`allowed_agents=["gleipnir-plan"]`, `minted_at=1000`) under `golden_key.bin`
  (`golden-fixture-key-do-not-use-in-prod`, not a secret). ✓
  (`tests/fixtures/README.md`, `golden_marker.json`)
- **Confirmed** existing `test_sequence_gate.mjs` already asserts assertion-5's
  four facts against the genuine/tampered golden markers. ✓ (L30-57)
- **Confirmed** the `FixedJudge`/`drive_to`/`_read_events`/`key_file`/`bridge_path`
  patterns already exist in `test_driver_emits_revert.py` and are reusable. ✓

**Nothing new needs a network or external service.** Everything runs in-sandbox
(`bin/gleipnir-sandbox`, `--network=none`) with the committed fixtures.

---

## 4. Assemble — test-first build order

The harness **is** the test; there is no production code to write. Structure it
as one file, `tests/test_armed_run_dogfood.py`, with one clearly-named test
function per assertion, each in arrange / act / assert form. Reuse the existing
helper shapes (`FixedJudge`, `drive_to`, `_read_events`) rather than inventing
new ones.

1. **Fixtures/helpers (arrange scaffolding).** `key_file` → `golden_key.bin`
   contents (or reuse a `tmp_path` copy); `bridge_path`, `logs_dir` under
   `tmp_path`; a `PASS` judge (trivial) and `FIXED_FAIL_JUDGE =
   FixedJudge(Verdict.FAIL)` (payload-blind); a `drive_to(driver, target)` loop.
2. **Assertion 1 — bridge re-mint validity at each step.** Drive
   BRAINSTORM→…→QUALITY, minting each hop's bridge with a **current/live
   `minted_at`** (call `advance(...)` with `minted_at=None` so it defaults to
   `int(time.time())` — these are class-2 forward-run bridges, §2.3). After
   *each* `advance`, read the bridge and assert `validate_state(marker, key)` is
   True **with default `now`/`max_age_seconds`** (freshness passes naturally — no
   override needed, because the bridge was just minted at current time),
   `marker.pipeline_state` equals the engine's current state, and
   `marker.allowed_agents == tuple(sorted(allowed_agents_for(state)))`. Also
   assert `resume_from_bridge(pipeline_id, bridge_path, key_file=...)`
   reconstructs a Driver at the same state (again default freshness — a live
   `minted_at` needs no `max_age_seconds` override).
3. **Assertion 2 — the forced revert emits exactly one correct event.** At
   QUALITY, `advance(FIXED_FAIL_JUDGE)`; read the session JSONL via
   `Event.from_json_line`; assert exactly one `REVERT_OCCURRED` with
   `from_state=="quality"`, `to_state=="code"`, `escalated is False`,
   `revert_count==1`.
4. **Assertion 3 — ledger reduce.** `reduce(session_log)` →
   `revert_count.value==1`, `escalation_count.value==0`,
   `escalation_rate.value==0.0` and `denominator==1` (real, not vacuous).
5. **Assertion 4 — ledger reconcile agrees.** `reconcile(session_log, report)`
   returns without raising (a passing reconcile *is* the assertion); optionally
   assert its `revert_count==1`.
6. **Assertion 6 — preflight.** (a) The PROCEED_UNCLOSED claim is made against
   the **REAL default probes** (no injection) at `agent_uid=os.getuid()`,
   `override_ack=True`, present key → on a single-uid box the real writes land
   `WRITE_OK` => NOT_CLOSED => `PROCEED_UNCLOSED`, label `DEV_MODE_LABEL` (the
   genuine dev-box verdict; §2.6). An optional injected-`WRITE_OK`-fake variant
   may accompany it for determinism, labelled as re-testing `decide()`'s logic
   (not a live-boundary claim). **The probe returns `WRITE_OK`, never
   `WRITE_DENIED`** (WRITE_DENIED + present key => CLOSED, the opposite). Then two
   REFUSE calls with injected edges: (b) one `WRITE_OK` enforcement file +
   `override_ack=False` → `REFUSE`; (c) absent key → `REFUSE`.
7. **Assertion 5 — cross-language handshake.** In the Python harness, drive a
   fresh driver to PLAN with `key_file=golden_key.bin`,
   `write_bridge(minted_at=1000)` to `tests/fixtures/dogfood_bridge.json` (this is
   a **class-1 committed FIXED-`minted_at` fixture**, §2.3, so its bytes are
   byte-stable for the node test). Because `minted_at=1000` is stale relative to
   real `now`, assert `validate_state(marker, key, now=1001)` accepts it (the
   explicit Python-side freshness override, symmetric to the node
   `now: 1001` — **omitting it makes the assertion fail on staleness, not MAC**);
   `marker.allowed_agents==("gleipnir-plan",)`. Then **extend
   `tests/test_sequence_gate.mjs`** with a `test(...)` that loads
   `dogfood_bridge.json` + `golden_key.bin` and asserts `validateMarker(marker,
   key, { maxAgeSeconds: HUGE, now: 1001 })==true`,
   `isDelegationAllowed(...,"gleipnir-plan")==true`,
   `isDelegationAllowed(...,"git-ops")==false`, and the tampered/one-byte case
   `false`. (Form 1 — the existing golden-marker assertions — already covers the
   frozen-fixture proof; form 2 adds the live-mint proof.)
8. **Seam markers.** Add two explicit comments/`pytest`-skip-with-reason (or a
   `# SEAM 7 / SEAM 8` docstring block) naming the live `tool.execute.after`
   advance hook and the real-CI `Attestation`→`attempt_gate` sourcing as
   **not-yet-automated**, never asserted green.

Build order rationale: assertions 1→2→3→4 follow the data as it flows through the
loop (mint → emit → reduce → reconcile); 6 (preflight) is independent and can be
authored in parallel; 5 (cross-language) is authored last because it depends on a
committed Python-minted bridge produced by the same driver path 1 exercises.

---

## 5. Stress-test — acceptance checks (the 6 assertions, concrete)

**Assertion 1 — bridge re-minted correctly at each step.** For every hop
BRAINSTORM→PLAN→SPEC_REVIEW→TEST→CODE→QUALITY, each minted with a **live/current
`minted_at`** (`minted_at=None` => `int(time.time())`, class-2 §2.3):
`validate_state(marker, key)` is True **with default `now`/`max_age_seconds`**
(freshness passes naturally — these bridges are minted at current time, so NO
override is used here); `marker.pipeline_state == driver.state.value`;
`marker.allowed_agents == tuple(sorted(allowed_agents_for(driver.state)))`;
`resume_from_bridge` (default freshness) rebuilds a Driver at that same state.

**Assertion 2 — exactly one revert event, correct fields.** After the single
QUALITY `advance(FIXED_FAIL_JUDGE)`, the session JSONL contains **exactly one**
`EventKind.REVERT_OCCURRED` whose typed payload has `from_state=="quality"`,
`to_state=="code"`, `escalated is False`, `revert_count==1`. No revert event was
emitted for any forward PASS hop.

**Assertion 3 — ledger reduce.** `reduce(session_log)` reports
`revert_count.value==1`, `escalation_count.value==0`, and `escalation_rate`
is the **real** measured rate `value==0.0`, `denominator==1` (the vacuous
`value=None`/`denominator=0` sentinel is correctly NOT used, because reverts were
observed).

**Assertion 4 — reconcile agrees.** `reconcile(session_log, report)` returns a
`ReconciliationReport` **without raising** (a passing reconcile is the assertion;
it raises `LedgerError` on any divergence between the two independent call sites).

**Assertion 5 — cross-language contract.** A Python-minted bridge at state
`plan`, FIXED `minted_at=1000` (both the committed `golden_marker.json` and the
live-minted-but-committed `dogfood_bridge.json` — class-1 §2.3), loaded on the
node side with the shared `golden_key.bin` under the freshness override
`{ maxAgeSeconds: HUGE, now: 1001 }`: `validateMarker(genuine)==true`;
`validateMarker(tampered)==false`; `isDelegationAllowed(bridge,"gleipnir-plan")==true`;
`isDelegationAllowed(bridge,"git-ops")==false`. The Python side asserts the same
fixture with `validate_state(marker, key, now=1001)` (symmetric override; a
`resume_from_bridge` check against this fixed fixture instead uses
`max_age_seconds=10**12`, since it has no `now=` parameter). (Form 1 already
green in `test_sequence_gate.mjs`; form 2 adds the live-mint block.)

**Assertion 6 — preflight bites.** `run_preflight` returns `PROCEED_UNCLOSED`
(label `DEV_MODE_LABEL`) under `override_ack=True` on a NOT_CLOSED boundary —
where NOT_CLOSED comes from a **`WRITE_OK`** probe result (writable enforcement
file / no uid separation), asserted against the **real default probes** on the
single-uid dev box (§2.6), since `WRITE_OK` + `override_ack=True` =>
`PROCEED_UNCLOSED` and never `CLOSED` per `decide()`; and returns `REFUSE`
(i) given a writable (`WRITE_OK`) enforcement file with `override_ack=False`, and
(ii) given an absent key.

**Cross-cutting checks:**
- **Full suite green:** the existing suite still passes; the new harness and the
  extended `.mjs` add tests, break none. **The baseline test count must be
  confirmed by the implementer against an actual current `bin/gleipnir-sandbox
  test` run at build time** — NOT cited as a fixed number here (a stale figure
  could mask a regression). The bar is: the real current count stays green and
  the new dogfood tests pass on top of it.
- **Stdlib-only (Python):** `tests/test_armed_run_dogfood.py` imports only
  `gleipnir.*`, `pathlib`, `os`, `json`, `pytest` — no third-party runtime dep
  (a `test_ledger_stdlib_only.py`-style static check is optional but the import
  list is the acceptance bar).
- **Payload-blind advance (no self-attestation):** assert structurally that
  forward hops use `_trivial_completion_judge` and the revert uses a fixed-verdict
  FAIL judge — neither inspects `payload`. (E.g. call both judges with a payload
  carrying a "should be ignored" sentinel and assert the returned verdict is
  unchanged: PASS / FAIL regardless of payload content.)

**Seams (documented, NOT claimed):**
- **Seam 7 — live opencode advance hook.** The mechanical post-tool advance via
  `tool.execute.after` (and the pre-tool gate already exists in
  `sequence-gate.ts`) driving `Driver.advance` in-process during a real opencode
  session is **not built and not asserted**. The dogfood proves the *Python loop*
  the hook would call, out-of-band. Tracking: extend `sequence-gate.ts` with a
  `tool.execute.after` handler + wire `Driver.advance`.
- **Seam 8 — real CI attestation → `attempt_gate` (G-3.2).** The dogfood does
  **not** source a real green `Attestation` from CI and does **not** exercise the
  GIT→GATE `attempt_gate` transition with genuine evidence. That binding
  (G-3.2 sourcing) is a separate seam, **not asserted here.**

---

## 6. Execution Workflow (for the implementing agent)

1. **Read the ground-truth modules** listed in Trace §2.1 (all already exist;
   change none of `src/**` or `.gleipnir/plugins/**` or `.gleipnir/decisions/**`).
   This delegation is **tests-only.**
2. **Author `tests/test_armed_run_dogfood.py`** with one test per assertion (§4
   build order). Reuse `FixedJudge`, `drive_to`, `_read_events` shapes from
   `tests/test_driver_emits_revert.py`. Put all writable artifacts under
   `tmp_path`; use `golden_key.bin` as the shared loop key.
3. **Force the revert exactly as §2.4 specifies:** drive to QUALITY with the
   trivial PASS judge, then `advance(FixedJudge(Verdict.FAIL))`. Assert exactly
   one `RevertOccurredEvent`.
4. **Wire the EventBus** with a `tmp_path` `logs_dir` (§2.5); reduce + reconcile
   over that session file (§4 steps 4–5).
5. **Exercise preflight** (§2.6): (a) the PROCEED_UNCLOSED claim against the
   **real default probes** (no injection, `agent_uid=os.getuid()`,
   `override_ack=True`, present key) — a `WRITE_OK`/NOT_CLOSED live dev-box
   verdict → `PROCEED_UNCLOSED`/`DEV_MODE_LABEL` (optional injected-`WRITE_OK`
   variant, labelled as re-testing `decide()`); (b) injected `WRITE_OK` +
   `override_ack=False` → `REFUSE`; (c) absent key → `REFUSE`. **Probe polarity
   is load-bearing: use `WRITE_OK` (not `WRITE_DENIED`) wherever NOT_CLOSED is
   intended** — `WRITE_DENIED` + present key yields `CLOSED`, the opposite.
6. **Produce the handshake bridge:** drive a fresh driver to PLAN with
   `key_file=golden_key.bin`, `write_bridge(minted_at=1000)` →
   `tests/fixtures/dogfood_bridge.json` (commit it, mirroring `golden_marker.json`;
   this is the class-1 FIXED-`minted_at` fixture). On the Python side assert it
   with the freshness override `validate_state(marker, key, now=1001)` (or, for a
   `resume_from_bridge` check against it, `max_age_seconds=10**12` — no `now=`
   param exists there), §2.3.
7. **Extend `tests/test_sequence_gate.mjs`** with a node `test(...)` loading
   `dogfood_bridge.json` + `golden_key.bin` and asserting the four assertion-5
   facts (use `{ maxAgeSeconds: HUGE, now: 1001 }` — the symmetric node-side
   freshness override for the fixed `minted_at=1000`).
8. **Add the Seam-7 / Seam-8 markers** as explicit not-yet-automated
   comments/docstrings (§4 step 8) — never assert them green.
9. **Run in-sandbox:** `bin/gleipnir-sandbox` runs the Python suite
   (`pytest`) and `node --test tests/test_sequence_gate.mjs`. Acceptance: all
   assertions 1–6 pass and the full existing suite stays green. **Confirm the
   green baseline count from an actual `bin/gleipnir-sandbox test` run at build
   time** (record the real current number then; do not treat any number quoted
   in this plan as authoritative) — the pass criterion is *that current count
   stays green AND the new dogfood tests pass*, so a regression cannot be masked
   by a stale figure.
10. **Hand back to the orchestrator.** No git, no Tier-3 writes, no `src/` edits
    performed by planning; the orchestrator sequences the test/code/quality/git
    stages the plan defines.

### Durable-decision flag (Tier-3)

**None required.** This is a Tier-0 harness proving composition; the seams it
names (live TS advance hook; real-CI attestation sourcing) are **already
recorded** in existing decision records
(`decisions/engine-revert-edges.md`, `g4-bus.md`, `g4d-ledger.md`,
`s2-g1-closure.md`, and the engine-state-bridge notes referenced by
`sequence-gate.ts`). **If the dogfood surfaces a durable finding** — e.g. the
composed loop reveals a fail-open the unit tests missed, or the on-disk
handshake exposes a MAC/canonicalization drift between Python and TS — that
finding must be **named for the operator to persist to `decisions/`**; the
implementing/review roles do not author Tier-3 themselves.
