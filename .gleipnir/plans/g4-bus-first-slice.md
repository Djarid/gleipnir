# Plan: G-4 typed event bus — first slice (schema + emit/JSONL + revert-hop wire-in)

**Status:** planned, not yet built. Tier-0 session artifact (disposable after
merge). Authored by `gleipnir-plan` FROM an operator-converged brief; the four
material decisions (D1–D4, below) are **LOCKED inputs**, not re-opened here.

**Provenance of the converged decisions.** D1 (Event schema = Option C typed
envelope+payload), D2 (transport = Option A per-session JSONL under `logs/`),
D3 (integrity = Option A, no HMAC; Tier-1 observation-only), D4 (slice boundary
= schema + emit/JSONL + the ONE revert-hop consumer) were surfaced by the
orchestrator to the operator and chosen. This plan captures them into an
executable ATLAS brief. It does **not** decide any of them again.

**Governing goal:** `../goals/plan-format.md` (this structure is mandatory).
**Spec anchor:** G-4a (§ line 173) — "Every guard... emits a typed event:
guard identity, enforcement surface, agent, attempted action, session id,
originating turn, artifact reference, timestamp. **The observer consumes the
typed stream and never parses a human-readable string.**" and G-4b (revert
occurred is a named interoceptive fact).

---

## GOTCHA pre-flight (recorded)

- **Goals-first:** `plan-format.md` governs; no pipeline-sequencing goal applies
  (G-5 owns sequencing as code — untouched by this slice).
- **Layer separation:** this slice adds a **Tool** (`emit()`/JSONL append) and a
  **Context** type (the typed `Event`). It adds **no Orchestration** (the G-5
  engine's `TRANSITIONS` are not touched) and **no new agent authority**. The
  engine's layer-2 purity ("pure in-memory state, no filesystem or process
  boundary" — `engine/DESIGN.md` lines 185–186) is a load-bearing invariant and
  is preserved: emit lives in the **driver**, not `Engine.step` (see the
  resolved design question below).
- **Authority ladder:** `logs/` is Tier-1 RETRIEVED, observation-only; it cannot
  escalate into policy, which is exactly why D3 (no HMAC) is sound this slice.

---

## 1. Architect

**Problem (one sentence).** Gleipnir has no G-4 event bus, so the deterministic
signals the framework already produces — starting with the engine's revert hops
— vanish unobserved (the recorded SEAM at `engine/__init__.py` ~L418–425); this
slice gives those signals a typed, append-only, provenance-stamped channel and
wires the first real emitter.

**User.** The (future) G-4c novelty-triage / G-4d ledger / session-observer
consumers, which must read **typed fields** off the stream — never parse prose
(the AETOS failure G-4 exists to close: reword an error string and the signal
silently disappears). Immediate consumer this slice: none automated; the
acceptance test *is* the stand-in observer that reads typed fields.

**Measurable success.**
1. An `Event` envelope exists carrying **all eight G-4a common fields** + an
   `EventKind` enum + a `version` field + a monotonic `sequence`, composed with
   a **typed per-kind payload** (frozen dataclass), never a free-string dict.
2. `emit(event)` appends exactly one valid JSON line to
   `.gleipnir/logs/<session_id>.jsonl` (one file per session), creating `logs/`
   if absent.
3. The engine's revert hop emits a `RevertOccurredEvent` carrying
   `from_state`, `to_state`, `revert_count` + full envelope provenance — via the
   **driver**, with `Engine.step` unchanged and still pure.
4. Stdlib-only; the existing 181-test suite stays green.

**Constraints.**
- **Stdlib-only** (`../decisions/runtime-and-deps.md`): `json`, `dataclasses`,
  `enum`, `time`/`datetime`, `pathlib`, `os`, `itertools`/an int counter, `typing`.
- **Typed, not prose** (G-4a): the read path must be field access, not
  `str.split`/regex/substring on a message.
- **No HMAC / no S-2 key in the telemetry path** (D3): do NOT import
  `verify/marker.py` or the bridge key here. Reserve `version` (and note an
  optional-integrity slot) so integrity CAN be added at the ledger slice; do not
  build it now.
- **Engine purity preserved** (`engine/DESIGN.md`): `Engine.step` must remain
  I/O-free and its unit tests must still hold.
- **Forward-compatible schema** (D2): `session_id` + `originating_turn` +
  monotonic `sequence` present from day one so the TS-hook ingress seam slots in
  later with no format break.
- **Tier boundary:** writes go only to `.gleipnir/logs/**` (Tier-1). No other
  `.gleipnir/` path is written by the bus.

---

## 2. Trace

### 2.1 Where it lives (source of truth)

New package: **`src/gleipnir/bus/`** (stdlib-only, mirrors `verify/` and
`engine/` layout).

| File | Responsibility |
|---|---|
| `src/gleipnir/bus/__init__.py` | Public API: `Event`, `EventKind`, `Envelope`, the per-kind payloads (`RevertOccurredEvent`), `emit`, `EventBus`, `BusError`. Re-export surface. |
| `src/gleipnir/bus/events.py` | The frozen `Envelope` dataclass, `EventKind` enum, the per-kind payload dataclasses, the composed `Event`, and `to_json_line()` / `from_json_line()`. |
| `src/gleipnir/bus/emit.py` | `EventBus` (owns the per-session path + monotonic sequence) and the `emit()` append API; `logs/` auto-create; degrade-vs-raise policy. |
| `tests/test_bus_events.py` | Schema + typed-read + serialization tests. |
| `tests/test_bus_emit.py` | JSONL append, per-session path, dir auto-create, sequence, un-writable policy. |
| `tests/test_driver_emits_revert.py` (or extend `tests/test_driver.py`) | Driver emits `RevertOccurredEvent` on an observed revert; engine purity untouched. |

Consumers/ledger/triage/webhook/TS-emit are **NOT** files in this slice (see
§2.5 deferred seams).

### 2.2 The `Event` — envelope + EventKind + typed payload (D1, Option C)

**`EventKind` enum** (str-valued, like `PipelineState`/`Verdict`), extensible;
this slice defines at minimum:
```
class EventKind(str, Enum):
    REVERT_OCCURRED = "revert_occurred"   # G-4b named interoceptive fact
    # (future kinds: GUARD_TRIGGERED, HUMAN_ESCALATION, TASK_ABANDONED, ... — not this slice)
```

**`Envelope`** — frozen dataclass carrying the **eight G-4a common fields**
(spec line 173), verbatim mapping:

| G-4a field (spec) | Envelope field | Notes |
|---|---|---|
| guard / emitter identity | `emitter: str` | who emitted (e.g. `"engine.driver"`); G-4a "guard identity" generalised to emitter identity per D1 |
| enforcement surface | `enforcement_surface: str` | e.g. `"engine"` / `"post_tool_hook"` |
| agent | `agent: str \| None` | roster agent in play, if any |
| attempted action / kind-specific action | `action: str` | a **SHORT TAG**, never a parse target — a future consumer must NOT reintroduce prose-parsing on it (see §7); routing/meaning comes from `kind` + typed `payload`, not from splitting `action` |
| session id | `session_id: str` | provenance (G-4c attribution) |
| originating turn | `originating_turn: int` | provenance (G-4c attribution) |
| artifact reference | `artifact_ref: str \| None` | e.g. pipeline_id / file / MR ref |
| timestamp | `timestamp: str` | ISO-8601 UTC (`datetime.now(timezone.utc).isoformat()`); stable, sortable, unambiguous |

Plus the schema-evolution / ordering fields (D1 + D2):
- `version: int` (schema version; reserved integrity slot — see D3),
- `sequence: int` (monotonic per session; ordering + gap-detection),
- `kind: EventKind` (selects the payload type).

**Structural presence vs value (deliberate D1 reading).** `agent` and
`artifact_ref` are **always structurally present** on every `Envelope` but are
**nullable-VALUED** (`str | None`): the field always exists (so the read path is
uniform field access), but its value may be `None` when no agent / no artifact
applies. This is a deliberate D1 reading — "typed envelope" means the *shape* is
fixed, not that every field is non-null.

**Per-kind payloads** — a small frozen dataclass **per kind**, selected by
`kind`. This slice defines:
```
@dataclass(frozen=True)
class RevertOccurredEvent:          # payload for EventKind.REVERT_OCCURRED
    from_state: str                 # PipelineState.value at revert source (the stage that failed)
    to_state: str                   # PipelineState.value at revert target;
                                    #   == PipelineState.ESCALATED.value on the budget-exhausting hop
    revert_count: int               # engine.revert_count AFTER this hop (never re-derived)
    escalated: bool = False         # True iff this hop is the budget-exhausting revert (to ESCALATED)
```
The `escalated` field lets a consumer distinguish the terminal
budget-exhausting revert from an ordinary backward revert **by typed field**,
not by string-matching `to_state` (see §2.4.1).
**`Event`** = frozen dataclass composing `Envelope` + `kind` + a typed
`payload` field. `kind` and `payload` type are consistent (a `REVERT_OCCURRED`
event carries a `RevertOccurredEvent`). Selection on read is by `kind` →
dataclass, **never** by string-parsing a message field.

**Serialization (`to_json_line` / `from_json_line`).** Follows
`verify/marker.py` / `bridge.py` patterns: `json.dumps(..., sort_keys=True,
separators=(",", ":"))` producing exactly one line (no embedded newlines);
`from_json_line` reconstructs the envelope, reads `kind`, and dispatches to the
correct payload dataclass by a `kind -> payload-class` table (a dict), so the
round-trip yields a typed object and the read path is **field access, not prose
parsing**. Malformed/unknown-kind lines raise `BusError` (fail-closed on read;
this is a corrupt-log condition, not a routing decision).

### 2.3 `emit()` / JSONL append API + per-session path + provenance supply (D2)

**`EventBus`** owns:
- `session_id` and the per-session path `logs_dir / f"{session_id}.jsonl"`
  (default `logs_dir = .gleipnir/logs`, injectable for tests via `tmp_path`),
- a **monotonic `sequence`** counter (starts at 0 or 1, +1 per emit), so the
  caller does not supply ordering,
- an `emit(kind, payload, *, emitter, enforcement_surface, agent,
  action, originating_turn, artifact_ref)` method that builds the `Envelope`
  (stamping `version`, `sequence`, `timestamp`), composes the `Event`, and
  appends one line.

**How provenance is supplied.** `session_id` is `EventBus` construction state
(one bus per session). `sequence` is bus-owned (monotonic). `timestamp`/`version`
are stamped by `emit`. `originating_turn`, `agent`, `emitter`,
`enforcement_surface`, `action`, `artifact_ref` are **passed by the caller**
(the driver knows them for the revert hop; `pipeline_id` is the natural
`artifact_ref`). This keeps the bus free of any authority to *invent*
provenance — it records what its caller states.

**Append mechanics.** Open in append mode (`"a"`), write
`event.to_json_line() + "\n"`, flush. Single Python writer this slice.

### 2.4 Wiring the revert hop WITHOUT giving the engine new authority

**The engine stays pure. The driver emits.** (Design question resolved below —
recommended, not merely picked; it is an implementation detail *bounded* by D4,
not a re-opening of a converged decision.)

- `Engine.step` already returns a `StepResult(state, escalated)` and exposes
  `engine.revert_count`. The **driver** — `src/gleipnir/engine/driver.py`, which
  already owns the `Engine` and already performs I/O (bridge writes, key loads)
  — is the natural, already-impure emit site.
- The driver gains an **optional** `EventBus` (constructor-injected; `None` = no
  emit, preserving all existing driver tests that construct without one). The
  engine gains **nothing** — no bus, no filesystem, no import of `bus`.
- The recorded SEAM comment in `engine/__init__.py` (~L418–425) is **updated**
  to point at the driver as the emit site (the obligation is discharged in the
  driver, not the engine core). The engine's own docstring invariant stays true.

#### 2.4.1 Crash-safe revert detection (BLOCKER-2 fix — mandatory algorithm)

`PIPELINE_ORDER` (`engine/__init__.py` L70–79) contains **only the eight
main-line stages**. It EXCLUDES `PipelineState.ESCALATED` and
`PipelineState.HUMAN_QUESTION`, which are *both* real `Engine.step()` outcomes
(`step` returns `StepResult(state=ESCALATED, escalated=True)` on the
budget-exhausting hop — L428–429 — and routes to `HUMAN_QUESTION` on a
`NEEDS_HUMAN` verdict — L406–409). Therefore **any algorithm that bare-indexes
`to_state` via `PIPELINE_ORDER.index(...)` CRASHES with `ValueError` on exactly
the escalation hop** that `engine-revert-edges.md` calls the most important to
log. The following classification is the required, crash-safe replacement.

The driver **observes** each `step()` it drives: it captures
`from_state = engine.state` *before* `step`, calls `step`, and classifies the
returned `StepResult` **using `StepResult.escalated` and explicit
`PipelineState` membership checks — never a bare index of a possibly-side-state**:

```
# In the driver, after `result = engine.step(judge)`:
to_state = result.state

if result.escalated:
    # (A) The BUDGET-EXHAUSTING hop. StepResult.escalated is True and
    #     to_state == PipelineState.ESCALATED (engine L427-429). This IS
    #     the Nth (final, most-important) revert: the FAIL that would have
    #     reverted instead tripped the global budget. DO NOT crash, DO NOT
    #     skip. Emit a RevertOccurredEvent with from_state = the stage that
    #     failed (the pre-step state), the escalation flagged explicitly,
    #     and revert_count = engine.revert_count (== budget). See below.
    emit RevertOccurredEvent(
        from_state = from_state.value,
        to_state   = PipelineState.ESCALATED.value,   # explicit constant, not index-derived
        revert_count = engine.revert_count,           # engine-owned; never re-derived
        escalated  = True,
    )

elif (
    from_state in PIPELINE_ORDER
    and to_state in PIPELINE_ORDER
    and PIPELINE_ORDER.index(to_state) < PIPELINE_ORDER.index(from_state)
):
    # (B) A NORMAL backward revert: a FAIL routed to an earlier main-line
    #     stage. BOTH states are guaranteed in PIPELINE_ORDER by the two
    #     membership guards ABOVE the index() calls, so index() cannot raise.
    emit RevertOccurredEvent(
        from_state = from_state.value,
        to_state   = to_state.value,
        revert_count = engine.revert_count,           # engine-owned; never re-derived
        escalated  = False,
    )

else:
    # (C) NOT a revert for this slice's consumer:
    #       * to_state == PipelineState.HUMAN_QUESTION (NEEDS_HUMAN hop), or
    #       * a normal FORWARD PASS transition (index(to) > index(from)), or
    #       * any other non-backward outcome.
    #     These may earn their own EventKinds in later slices (out of scope
    #     now). Emit NOTHING. MUST NOT raise. Note that the membership guards
    #     in branch (B) mean a HUMAN_QUESTION to_state (absent from
    #     PIPELINE_ORDER) falls through here safely rather than reaching index().
    pass
```

**The escalating-hop emit DECISION (stated explicitly, per BLOCKER-2):**
the budget-exhausting hop **STILL emits a `RevertOccurredEvent`** — recommended
YES. It is the final, most-important revert (the one `engine-revert-edges.md`
§mitigation #1 singles out); dropping it would blind the observer to the exact
event the SEAM exists to capture. It is captured with `from_state` = the stage
that failed (pre-step state), `to_state = ESCALATED`, `revert_count = N` (the
budget), and a dedicated boolean field `escalated=True` on the payload so a
consumer can distinguish the terminal escalation from an ordinary backward
revert without string-parsing. `to_state` for this hop is the **explicit
constant `PipelineState.ESCALATED.value`**, never derived by indexing.

**Invariant for the implementer:** `PIPELINE_ORDER.index(x)` is only ever
called on an `x` already proven to be `in PIPELINE_ORDER` by a membership guard
in the same boolean expression. `ESCALATED` and `HUMAN_QUESTION` are never
indexed. The revert count is read from `engine.revert_count`, never
re-derived by the driver.

#### 2.4.2 Named driver change + test-drive API (MINOR fix — no open ends)

The current driver's only `step`-driving method,
`advance_on_clean_completion` (L165–185), hard-wires `_trivial_completion_judge`
(always `Verdict.PASS`, L59–66), so **no revert can occur on that path** and the
emit logic could never be exercised. The **named** driver change is:

- **Generalize the advance to accept an injected judge.** Add a method (or
  generalize `advance_on_clean_completion`) `advance(self, judge: Judge = _trivial_completion_judge, *, minted_at=None) -> StepResult`
  — the documented **default remains `_trivial_completion_judge`**, so every
  existing caller and every existing driver test is unchanged. The judge is the
  injection point: the acceptance test supplies a `FAIL`-returning judge to
  drive a real revert (mirroring `test_engine.py`'s `FixedJudge(Verdict.FAIL)`),
  the escalation path drives it to exactly the budget, and a `NEEDS_HUMAN` judge
  drives the HUMAN_QUESTION path. Keep `advance_on_clean_completion` as a thin
  wrapper delegating to `advance(_trivial_completion_judge)` for source
  compatibility.
- **The observe/emit block of §2.4.1 lives inside this method**, wrapping the
  existing `self.engine.step(judge)` call (currently L183): capture `from_state`
  before, classify the `result` after, emit through `self._bus` (the optional
  injected `EventBus`) iff `self._bus is not None`, then proceed to
  `write_bridge` unchanged. Emit is a telemetry side-effect and MUST NOT alter
  the method's return value or the fail-closed key/bridge ordering (§2.6 edge 3).
- **Provenance supply for the emitted event** (removing the "fixed values are
  fine" open end): `session_id` is `EventBus` construction state;
  `sequence`/`timestamp`/`version` are bus-stamped; `emitter="engine.driver"`,
  `enforcement_surface="engine"`, `artifact_ref=self.engine.pipeline_id`. The
  two remaining caller-context fields, **`agent` and `originating_turn`, are
  supplied to the driver at the advance call**: add optional parameters
  `agent: str | None = None` and `originating_turn: int = 0` to the `advance`
  method (defaults keep existing callers working), and the driver passes them
  straight through to `bus.emit(...)`. The acceptance test passes explicit
  values and asserts they arrive on the emitted event; it does not rely on
  implementation-time invention.

> **Note for the implementer:** the current minimal driver only drives
> `Verdict.PASS`, so the emit logic must be wired at the generalized `advance`
> method's `step`-observation point (§2.4.1) so that a `FAIL`- or
> `NEEDS_HUMAN`-returning judge, once injected, is classified correctly. The
> acceptance tests drive reverts, an at-budget escalation, and a NEEDS_HUMAN
> step **through the driver with the injected judge** — they do not require the
> trivial judge to change.

### 2.5 Explicitly deferred seams (D4 — named, not built)

- **G-4d metrics ledger** — reads the stream; not built.
- **G-4c novelty triage** — reads correction/abandonment clusters; not built.
- **Platform-webhook ingress (E-2)** — the second bus ingress class; not built.
- **Observer / any automated consumer** — the acceptance test is the stand-in;
  no consumer daemon built.
- **TS-side hook emission** — the runtime ingress; DOCUMENTED SEAM. The schema's
  `session_id`/`originating_turn`/`sequence` exist precisely so this slots in
  later without a format break.
- **Per-event integrity (HMAC)** — reserved via `version` (D3); NOT built, and
  the S-2 key is deliberately kept out of the telemetry path.
- **Multi-writer concurrency** — see edge cases; single Python writer this slice.

### 2.6 Edge cases

1. **`logs/` dir missing.** `emit` calls `logs_dir.mkdir(parents=True,
   exist_ok=True)` before the first append. (Matches `driver.write_bridge`'s
   `parent.mkdir(parents=True, exist_ok=True)` pattern.)
2. **Concurrent append.** This slice has a **single Python writer** — safe. The
   TS-hook ingress (deferred) introduces a **multi-writer hazard** onto one
   per-session file (Python engine-driver + TS post-tool hook appending
   concurrently). **Flagged here as a named risk for the TS-join seam**;
   candidate resolutions (single-writer daemon, per-writer files merged on read,
   OS append-atomicity within a size bound, or a lock) are a decision for that
   later slice, not this one. Do not build cross-writer coordination now.
3. **Un-writable `logs/`** (permission error / mkdir fails / append fails).
   **Decision: DEGRADE, do not raise into the caller's control flow.** Justified:
   `logs/` is Tier-1 **observation-only** — emission is *telemetry, not a gate*
   (contrast the bridge/marker path, which is fail-CLOSED because it gates state
   transitions). A telemetry write that raises could take down a legitimate
   engine advance, inverting the authority ladder (a Tier-1 failure must never
   block higher-tier work). So `emit` **swallows the OSError and returns a
   failure signal** (e.g. returns `False` / an `EmitResult(ok=False, reason=...)`)
   rather than propagating — and, so the failure is not *silent*, it records the
   drop count on the bus (`bus.dropped: int`) for later observability. The engine
   driver's advance must proceed regardless of emit outcome. (Rationale recorded
   so a reviewer does not "fix" this into a raise.)
4. **Unknown/forward `EventKind` or `version` on read** (`from_json_line`). This
   is a *read-path corruption/version-skew* condition, not a live control path →
   raise `BusError` (fail-closed on read). Note: read is not exercised by the
   engine path this slice; it is exercised by the acceptance/observer test.

---

## 3. Link (validated before building)

- **Eight G-4a fields** confirmed verbatim from spec v0.3.12 line 173 (mapped in
  §2.2). "Observer never parses a human-readable string" is the binding
  constraint on the read path.
- **`logs/` is Tier-1** (`../decisions/gleipnir-layout-and-memory-model.md`;
  `logs/README.md`): observation-only, provenance-required, framework-writer —
  validates D2/D3 and the degrade-not-raise edge decision.
- **Engine purity is load-bearing** (`engine/DESIGN.md` L185–186: "no filesystem
  or process boundary; pure in-memory state"; `engine/__init__.py` L1–17) — the
  emit-location decision must not break it.
- **Driver already does I/O** (`engine/driver.py`: bridge writes, key loads,
  `mkdir(parents=True, exist_ok=True)`) — validated as the correct, already-impure
  emit site.
- **The SEAM is real and located** (`engine/__init__.py` L418–425;
  `../decisions/engine-revert-edges.md` §"blunt-signal mitigation" #1): the
  revert-hop bus event is a *recorded obligation* this slice discharges.
- **Serialization patterns exist to mirror** (`verify/marker.py`,
  `engine/bridge.py`: frozen dataclass, `to_json`/`from_json`, `json.dumps`
  canonical form) — but NOT their HMAC (D3).
- **Stdlib-only is a policy with a candidate meta-test**
  (`../decisions/runtime-and-deps.md`).
- **Baseline suite = 181 tests** (per `../decisions/engine-revert-edges.md`
  §Verification) — must stay green.

---

## 4. Assemble (test-first build order)

Test-first throughout (Axiom 1: the test is the arbiter). Build in-sandbox.

1. **Write `tests/test_bus_events.py` (RED first).** Assert: `Envelope` carries
   all eight G-4a fields + `version` + `sequence` + `kind`; `EventKind` has
   `REVERT_OCCURRED`; `RevertOccurredEvent` carries `from_state`/`to_state`/
   `revert_count`; `Event` round-trips through `to_json_line`/`from_json_line`;
   **the reconstructed object is read by typed field access and a test asserts no
   string-parsing is needed** (e.g. reconstruct → `evt.payload.from_state` is a
   real attribute, `evt.kind is EventKind.REVERT_OCCURRED`); one JSON line, no
   embedded newline; malformed/unknown-kind line raises `BusError`.
2. **Implement `src/gleipnir/bus/events.py`** to green step 1.
3. **Write `tests/test_bus_emit.py` (RED).** Assert (using `tmp_path`):
   `emit` appends exactly one valid JSONL line to `<session_id>.jsonl`; a second
   emit appends a second line with `sequence` incremented; `logs/` dir is
   auto-created when absent; the file is per-session (two sessions → two files);
   **un-writable dir → `emit` degrades (returns failure, does not raise) and
   increments `dropped`**; stdlib-only.
4. **Implement `src/gleipnir/bus/emit.py` + `bus/__init__.py`** to green step 3.
5. **Write `tests/test_driver_emits_revert.py` (RED).** Drive steps through the
   driver via the injected judge (§2.4.2) and assert all of:
   - (a) a **normal backward revert** (FAIL judge, below budget) emits a
     `RevertOccurredEvent` with correct `from_state`, `to_state`,
     `escalated is False`, `revert_count`, and the passed-through
     `agent`/`originating_turn` provenance;
   - (b) the **budget-exhausting hop** (FAIL to EXACTLY the budget, mirroring
     `test_engine.py::test_revert_at_exactly_budget_escalates`) does **not raise**
     and emits per the §2.4.1 escalation decision (`to_state == ESCALATED`,
     `escalated is True`, `revert_count == budget`);
   - (c) a **NEEDS_HUMAN step** (`to_state == HUMAN_QUESTION`) does **not raise**
     and emits **no** revert event;
   - (d) a driver constructed **without** a bus still works (emit is optional);
   - (e) **`Engine.step` was not modified** to reach the bus (engine imports no
     `bus`; engine unit tests unchanged).
6. **Wire the emit into `driver.py`** — add the optional injected `EventBus`,
   generalize the advance to accept an injected judge (default
   `_trivial_completion_judge`) plus optional `agent`/`originating_turn`
   (§2.4.2), and add the crash-safe observe/classify/emit block (§2.4.1: guard
   membership before any `PIPELINE_ORDER.index`; classify via
   `StepResult.escalated` + explicit `PipelineState` checks) — to green step 5.
   Update the SEAM comment in `engine/__init__.py` to point at the driver
   (comment-only; no engine logic change).
7. **Full suite in-sandbox:** confirm 181 prior tests + the new bus/driver tests
   all green; run the stdlib-only check (grep/AST for non-stdlib top-level
   imports in `src/gleipnir/bus/`).

---

## 5. Stress-test (concrete acceptance checks)

A reviewer/CI validates the slice against each of these — all must hold:

1. **All 8 G-4a fields present.** `Envelope` has `emitter`,
   `enforcement_surface`, `agent`, `action`, `session_id`, `originating_turn`,
   `artifact_ref`, `timestamp` — a test enumerates them.
2. **`version` + `sequence` present** on every emitted event; `sequence`
   strictly increases per session.
3. **Typed, not prose.** A test reconstructs an event from its JSONL line and
   reads `evt.kind is EventKind.REVERT_OCCURRED` and
   `evt.payload.revert_count == N` by **attribute access**. The "never parses a
   human-readable string" guarantee (G-4a) is enforced by an **actual check, not
   a comment** — either (a) a runtime assertion in the test that the read path
   yields typed objects (e.g. `isinstance(evt.payload, RevertOccurredEvent)` and
   the fields are read as attributes), **or** (b) a **static (grep/AST) check
   over the read path** (`from_json_line` and its dispatch) asserting no
   `.split(`/`re.`/substring-slicing of a message field appears. A comment alone
   does NOT satisfy this check.
4. **Valid JSONL append.** `emit` produces exactly one line per event (no
   embedded newline), parseable by `json.loads`, appended to
   `.gleipnir/logs/<session_id>.jsonl`; N emits → N lines.
5. **Per-session file.** Two distinct `session_id`s produce two distinct files.
6. **Revert-hop emit correctness (normal backward revert).** Driving a
   `Verdict.FAIL` revert through the driver (injected FAIL judge, below budget)
   emits a `RevertOccurredEvent` with `from_state`/`to_state` matching the actual
   PIPELINE_ORDER backward hop, `escalated is False`, and
   `revert_count == engine.revert_count` after the hop.
7. **Budget-exhausting (ESCALATED) hop — no crash, emits per decision.** A case
   driving reverts to **EXACTLY the budget through the driver** (mirroring
   `test_engine.py::test_revert_at_exactly_budget_escalates` — inject
   `FixedJudge(Verdict.FAIL)` `budget` times, walking forward via a PASS judge
   between each) asserts the driver's observe/emit handles the `ESCALATED` hop
   (`StepResult.escalated is True`, `to_state == ESCALATED`) **WITHOUT raising**
   (specifically: no `ValueError` from `PIPELINE_ORDER.index`), and emits a
   `RevertOccurredEvent` with `from_state` = the failed stage,
   `to_state == PipelineState.ESCALATED.value`, `escalated is True`, and
   `revert_count == budget` (== `engine.revert_count`).
8. **NEEDS_HUMAN hop — no crash, no revert event.** A case driving a
   `Verdict.NEEDS_HUMAN` step through the driver (injected NEEDS_HUMAN judge;
   `to_state == HUMAN_QUESTION`, which is ABSENT from `PIPELINE_ORDER`) asserts
   the driver **does not raise** and emits **no** `RevertOccurredEvent` for this
   slice's revert consumer.
9. **`logs/` auto-created** when absent (test starts with no dir, emit creates it).
10. **Un-writable `logs/` degrades, does not raise** — `emit` returns a failure
    signal and increments `dropped`; a simulated engine advance still completes.
11. **Stdlib-only** — no non-stdlib top-level import in `src/gleipnir/bus/`
    (grep/AST check); no import of `verify/marker.py`, no HMAC, no S-2 key in the
    bus path.
12. **Engine purity preserved** — `engine/__init__.py` imports no `bus`; emit is
    in the driver; the engine's existing unit tests are unchanged and green;
    the driver without an injected bus behaves exactly as before.
13. **181 prior tests still green** + the new tests green (full in-sandbox run).

---

## 6. Execution Workflow (for the implementing agent)

- **Role/stages:** test authoring and code both bind to `gleipnir-code`
  (Sonnet); this slice is test-first, so the tests carry the correctness burden.
  Review binds to `quality-reviewer`. Sequencing is the orchestrator's.
- **Build in-sandbox** (`bin/gleipnir-sandbox`): all pytest runs go through the
  ephemeral container, not the host (G-2 blast-radius).
- **Order:** follow §4 exactly — RED test → implement → green, three times
  (events → emit → driver wiring), then the full-suite + stdlib-only gate.
- **Do NOT:**
  - modify `Engine.step` or `TRANSITIONS` (engine purity; only a comment update
    to the SEAM is permitted);
  - import `verify/marker.py` / add HMAC / touch the S-2 key in the bus (D3);
  - build any deferred seam in §2.5 (ledger, triage, webhook ingress, consumer
    daemon, TS emit, per-event integrity, multi-writer coordination);
  - make `emit` raise on an un-writable `logs/` (edge case 3 — degrade, and
    record the drop);
  - write anything outside the **allowed-write list** below.
- **Allowed writes (exact scope — the ONLY files this slice may create/modify):**
  - `src/gleipnir/bus/**` — the new package (`__init__.py`, `events.py`, `emit.py`);
  - `tests/**` — the new/extended test files (`test_bus_events.py`,
    `test_bus_emit.py`, `test_driver_emits_revert.py` or the `test_driver.py`
    extension);
  - `src/gleipnir/engine/driver.py` — **scoped exactly to**: (1) adding an
    optional, `None`-safe injected `EventBus` parameter to the driver
    constructor; (2) generalizing the advance to accept an injected judge with
    the documented `_trivial_completion_judge` default plus optional
    `agent`/`originating_turn` params (§2.4.2); and (3) the step-observation /
    classify / emit block (§2.4.1). No other driver behavior changes; the
    fail-closed key/bridge ordering is preserved;
  - `src/gleipnir/engine/__init__.py` — **the ONE comment-line update only** to
    the SEAM at ~L418–425 (point it at the driver as the discharged emit site).
    The engine stays pure: NO logic change, NO `bus` import, `Engine.step` and
    `TRANSITIONS` untouched.
- **Provenance for the revert emit:** `emitter="engine.driver"`,
  `enforcement_surface="engine"`, `artifact_ref=pipeline_id`; `agent` and
  `originating_turn` are passed by the driver's caller (the driver may accept
  them; for the test, fixed values are fine).
- **Definition of done:** all 13 Stress-test checks pass in-sandbox; no capability
  or authority added to the engine; the SEAM comment now points at the discharged
  obligation.

---

## 7. Durable decision to persist (Tier-3 — operator action required)

`gleipnir-plan` **cannot** write Tier-3. The following should be persisted by
the operator as **`.gleipnir/decisions/g4-bus.md`** (durable record), capturing
what this slice makes load-bearing for later G-4 work:

- **D1 typed envelope+payload (Option C)** is the bus schema of record: eight
  G-4a fields + `EventKind` + `version` + `sequence` + typed per-kind payload;
  the read path is field access, never prose parsing (G-4a). The `action` field
  is a **SHORT TAG, never a parse target** — routing/meaning comes from `kind` +
  typed `payload`, and a future consumer must not quietly reintroduce
  prose-parsing on `action`. `agent` and `artifact_ref` are **always
  structurally present but nullable-VALUED** (`str | None`) — a deliberate D1
  reading: the envelope *shape* is fixed, individual values may be `None`.
- **D2 per-session JSONL under `logs/`** is the transport of record; the TS-hook
  ingress is a documented seam; `session_id`/`originating_turn`/`sequence` are
  present from day one so it slots in without a format break.
- **D3 no HMAC this slice**; `logs/` Tier-1 observation-only makes append-only +
  provenance sufficient; `version` reserves the integrity slot for the ledger
  slice **if** suppression becomes an economic-gaming vector; the S-2 key stays
  out of the telemetry path.
- **Emit-location invariant:** the G-4 bus emits from the **driver**, never from
  `Engine.step` — preserving the engine's documented pure-in-memory property.
  This is the standing rule for all future emitters near the engine core.
- **Named deferred seams:** ledger (G-4d), triage (G-4c), webhook ingress (E-2),
  observer/consumers, TS emit, per-event integrity, multi-writer coordination.
- Supersedes the "recorded obligation" status of the revert-hop bus event in
  `../decisions/engine-revert-edges.md` §mitigation #1: **discharged** (in the
  driver) once this slice merges.
