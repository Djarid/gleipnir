# Plan: G-4d metrics ledger — first slice (reduction skeleton + one real metric)

**Stage:** plan (authored by `gleipnir-plan` FROM a converged operator decision).
**Status:** ready for spec-review. Session artifact (Tier-0, disposable after merge).
**Spec anchor:** G-4d (`gleipnir_specification_v0_3_12.md` §183–207), incl. the
"triple reading, plus a system-state fourth" (the revert-on-main baseline that
G-3.2's engine-side binding is meant to reduce) and Conformance [D] "bus-emission gap".
**Depends on:** the G-4 bus (`.gleipnir/decisions/g4-bus.md`;
`src/gleipnir/bus/{events,emit}.py`) — the typed stream this ledger consumes.

## Provenance: this plan captures a LOCKED operator decision — it does not re-decide

The scope was converged by the operator via the orchestrator's decision gate.
The four decisions below are **captured, not re-opened**. `gleipnir-plan` did
not choose the slice boundary, the cost-deferral posture, the discriminated
honesty type, or the reconciliation shape — the operator did. This plan turns
them into executable, test-first work. One genuinely-bounded design question
(read-on-demand vs. live subscribe) is decided-and-justified below (§Trace,
D-Q1); it is judged non-material and is flagged as such rather than escalated.

### Converged decisions (LOCKED — capture verbatim in the Tier-3 record)

- **D1 — First-slice boundary = Option C: deterministic reduction skeleton +
  ONE real metric.** Build an event→metric reduction framework that reads the
  bus JSONL and reduces typed events to metrics; wire **exactly one** real
  measured metric — the **revert-derived baseline** (reverts per session +
  escalation rate, from the `RevertOccurredEvent` stream: count reverts, count
  `escalated=True`). This is the spec's named G-3.2 baseline ("how often work
  reached a terminal and had to be undone"). **All other metrics** (iterations,
  retries-as-distinct-kind, token usage, cost, effort attribution, efficiency,
  uplift) are **NAMED SEAMS reported as explicit "bus-emission gaps", never
  fabricated zeros.**
- **D2 — Rate table = author its Tier-3 POLICY home + a loader + a G-3.1 keyed
  digest verified at load (fail-closed on mismatch) NOW — but DEFER the cost
  NUMBER.** Do not compute or emit any cost figure until the S-2 mount makes the
  rate table structurally agent-unwritable. The skeleton has a cost slot that
  stays a **gap**. Publishing cost pre-S-2 would assert an unforgeability
  guarantee that is not yet true (spec §193: "the rate table is configuration
  under the S-2 boundary so no agent can understate cost by editing rates").
- **D3 — Measured-vs-estimated honesty type = a discriminated type.** `Measured`
  vs. `Estimated` as **genuinely distinct types** (NOT a bool flag on a shared
  struct), mirroring the bus's typed-not-stringly discipline. `Estimated`
  **cannot be constructed without a `CalibrationBand`** (plus a versioned
  `notional_human_rate` for uplift specifically) — construction **RAISES**
  otherwise (fail-closed, like `attempt_gate` refusing a null attestation).
  Serialization always carries the discriminant, so an estimate can never be
  mistaken for a measurement. **Build + TEST this now** even though **no estimate
  (uplift) is emitted this slice** — it is the anti-vanity structural guarantee
  (spec §185: "an unlabelled estimate is a vanity metric").
- **D4 — Reconciliation = re-derive the one measured (revert) metric directly
  from the raw bus JSONL and assert equality** with the ledger's reported value;
  AND emit an explicit **"bus-emission gap" report** for every metric whose
  input event kind does not yet exist (report GAP, never a misleading 0). This
  operationalises Conformance [D] "bus-emission gap" at slice scale.

---

## 1. Architect

**Problem (one sentence).** Build the deterministic first slice of the G-4d
metrics ledger: a reduction framework over the typed bus JSONL that produces
**one honestly-measured metric** (the revert/escalation baseline) and reports
**every other G-4d metric as an explicit bus-emission gap**, with the
anti-vanity structural guarantees (discriminated Measured/Estimated type,
fail-closed rate-table digest, cost deferred) in place from day one.

**User.** (1) The framework operator, who needs a *trustworthy* baseline for the
system-state fourth reading (the revert-on-main rate that G-3.2 must later
reduce) and a scoreboard that never flatters the system. (2) Future ledger
slices and G-3.2 conformance, which will fill the named seams and consume the
same reduction path. (3) The spec's own value claims (§203 meta-purpose), which
demand the ledger carry its own measurement.

**Measured success criteria** (checkable; the anti-vanity properties are
first-class success, not nice-to-haves):

1. `reduce(session_log_path) -> LedgerReport` reads the bus JSONL **via the
   bus's typed read path** (`Event.from_json_line`) — never a hand-rolled JSON
   parse, never a string/substring/regex parse of any field.
2. The revert baseline is computed from the typed `RevertOccurredEvent` stream:
   `revert_count` = number of revert events; `escalation_count` = number with
   `payload.escalated is True` (read by **typed attribute**, not string match);
   `escalation_rate` derived from those two.
3. **No fabricated numbers.** Every G-4d metric that has no source event kind
   yet (iterations, retries, tokens, cost, effort, efficiency, uplift) appears
   in the report as an explicit **GAP with a reason**, distinguishable in type
   from a real measured value of `0`.
4. **Estimate type refuses uncalibrated construction.** `Estimated(...)` raises
   without a `CalibrationBand` (and, for uplift, without a versioned
   `notional_human_rate`); `Measured(...)` carries no such requirement.
   Serialization of any metric carries the `Measured`/`Estimated` discriminant.
5. **Cost is deferred.** No cost *number* is computed or emitted this slice; the
   cost slot is a GAP whose reason names the S-2 precondition. The rate-table
   loader nonetheless exists, and it **verifies a G-3.1 keyed digest and fails
   closed** (missing key, missing table, or digest mismatch → cost stays a GAP
   with a clear reason, never a guessed rate).
6. Reconciliation re-derives the revert metric **directly from the raw JSONL**
   and asserts equality with the `LedgerReport` value; the report also lists a
   bus-emission gap for every not-yet-emitted metric.
7. **Stdlib-only** (a C-3 grep/AST meta-test proves it, mirroring
   `tests/test_bus_stdlib_only.py`); the existing **220 tests stay green**.

**Constraints.**

- **Stdlib-only** enforcement core (`.gleipnir/decisions/runtime-and-deps.md`).
  The ledger CODE may import `hashlib`/`hmac` **via `verify/marker.py`** for the
  rate-table digest (this is legitimate — unlike the bus, whose D3 forbade it,
  the ledger's rate table IS authority-bearing config).
- **Reuse the bus typed read path.** `Event.from_json_line` is the only door in;
  do not re-parse JSON, do not string-parse. (Enforced by test + by the
  no-`re`/no-`.split` discipline the bus already models.)
- **Trust tiers** (`.gleipnir/decisions/gleipnir-layout-and-memory-model.md`):
  the ledger *code* lives in agent-writable `src/` (Tier-3 write boundary does
  **not** apply to code). The rate-table **file** and its **digest** are **Tier-3
  POLICY** (`operator-only`) — this plan **flags** them as an operator hand-off;
  `gleipnir-plan` cannot and must not write them.
- **Pre-S-2 honesty.** No claim of unforgeability the substrate cannot yet back:
  hence cost deferred (D2). Reads only Tier-1 `logs/` (observation-only); emits
  no authority.
- **No new runtime deps.** No third-party imports.

---

## 2. Trace

### 2.1 Module layout (proposed — `gleipnir-plan`'s call, bounded by stdlib-only)

New package **`src/gleipnir/ledger/`** (agent-writable `src/`), mirroring the
`bus/` package shape:

```
src/gleipnir/ledger/
  __init__.py          # exports the public surface (reduce, LedgerReport, Measured, Estimated, ...)
  metric.py            # D3: the discriminated Measured / Estimated / Gap types + EstimateKind + CalibrationBand
  reduce.py            # D1: reduce(session_log_path) -> LedgerReport; the reduction framework + revert reducer
  ratetable.py         # D2: rate-table schema + loader + G-3.1 digest check (fail-closed); cost stays a GAP
  reconcile.py         # D4: re-derive revert metric from raw JSONL; assert equality; build the gap report
```

**Source of truth for each artifact:**

- **Input event stream** — `.gleipnir/logs/<session_id>.jsonl` (Tier-1
  RETRIEVED), read **only** through `gleipnir.bus.events.Event.from_json_line`.
  The reducer opens the file, iterates lines, and calls `from_json_line` per
  line. No other read path exists.
- **Metric types** (`metric.py`) — the D3 discriminated type. Three concrete
  kinds (all frozen dataclasses; a shared ABC/`Protocol` gives the serialization
  discriminant but **no shared mutable state that could blur measured vs.
  estimated**):
  - `Measured(name, value, denominator, provenance)` — a deterministically-off-
    the-bus quantity. No calibration requirement. `denominator` is **always
    inspectable** (see the escalation-rate 0/0 convention in edge case 6).
  - `Estimated(name, value, kind: EstimateKind, calibration: CalibrationBand, notional_human_rate: NotionalHumanRate | None)`
    — construction (`__post_init__`) **raises `LedgerError`** if `calibration`
    is absent; and it raises if `notional_human_rate` is absent **when
    `kind is EstimateKind.UPLIFT`** (spec §198–199: uplift's load-bearing
    assumption is a versioned, logged parameter). The uplift precondition keys
    off a **TYPED discriminant, `EstimateKind`** — an enum on the `Estimated`
    type — **NOT** a `name == "uplift"` string check. Keying a fail-closed rule
    off a string inside the very type built to eliminate stringly-typing would
    reintroduce the defect the type exists to close; the discriminant is
    enumerated and checked by identity. (Chosen: an `EstimateKind` enum field
    over a dedicated `UpliftEstimated` subtype — it keeps a single `Estimated`
    type with one construction contract and one serialization path, so the
    honesty discriminant and the uplift discriminant compose without a class
    hierarchy; the enum is trivially extensible as future estimate kinds land.)
  - `Gap(name, reason)` — the explicit "bus-emission gap": a metric whose source
    event kind does not exist yet. **`Gap` is a distinct TYPE**, so a consumer
    can never read it as `value == 0`. Serialization tags it `"gap"` with its
    reason (e.g. `"no TokenUsageEvent kind on the bus yet"`,
    `"cost deferred until S-2 mount makes rate table agent-unwritable"`).
  - `CalibrationBand(low, high, sample_n, updated_at)` and
    `NotionalHumanRate(rate, currency, version)` — value objects that make the
    D3 fail-closed contract enforceable by construction.
  - Each metric serializes with a **`kind` discriminant** field
    (`"measured"`/`"estimated"`/`"gap"`), mirroring the bus's
    `EventKind`-on-the-envelope discipline, so serialized output can never
    mistake an estimate for a measurement (spec §185).
- **`LedgerReport`** (`reduce.py`) — frozen dataclass: `session_id`, the one
  `Measured` revert metric, and the list of `Gap`s for every named seam
  (iterations, retries, token_usage, cost, effort_attribution, efficiency,
  uplift). Also carries `unreadable_line_count` (see edge cases) and a
  `to_json`/from-JSON pair using the marker/bus canonical form
  (`sort_keys=True, separators=(",", ":")`).
- **Rate table** (`ratetable.py` loader) — schema + loader + G-3.1 digest check.
  The **loader is code (`src/`)**; the **table file + its approved digest are
  Tier-3 POLICY** and are an **operator hand-off** (see §2.4). The loader:
  reads the table path (default under Tier-3; overridable for tests), computes a
  content hash, and validates it against an approved keyed digest using
  `verify.marker` primitives (`load_key`, HMAC compare). On **any** doubt
  (missing table, missing/unreadable key, digest mismatch) it returns a
  fail-closed signal that makes the cost metric a `Gap` with a precise reason —
  it **never** returns a guessed rate and **never** raises into the reduction's
  control flow (the reduction still completes; cost is simply a gap).
- **Reconciliation** (`reconcile.py`) — a standalone re-derivation: independently
  iterate the raw JSONL via `Event.from_json_line`, recount reverts/escalations,
  and assert equality with the `LedgerReport`'s `Measured` value; produce the
  gap report enumerating every not-yet-emitted metric. This is the executable
  form of Conformance [D] at slice scale.

### 2.2 D-Q1 — the one real design question: WHERE and WHEN does the ledger read? (DECIDED, non-material)

**Decision: read-on-demand.** The public entry point is a **pure function**
`reduce(session_log_path: Path) -> LedgerReport` over a single session's JSONL
file. The ledger does **not** subscribe to a live bus stream this slice.

**Justification (why this is bounded, not material — so decided here, not
escalated).**

- **Testability.** A pure `file -> report` function is trivially testable with
  fixture JSONL files (empty, revert-only, malformed-line), needs no running bus,
  no event loop, no time source — exactly the property that let the bus's own
  first slice stay clean.
- **Matches the substrate.** The bus already persists append-only JSONL per
  session (D2 of `g4-bus.md`); the natural consumer of a durable log is a
  reduction over the durable log. Live subscription would couple the ledger to
  the writer's process lifetime for no slice benefit.
- **No lasting lock-in.** A future live/observer path can wrap the same pure
  reducer (feed it accumulated lines, or fold incrementally) — the reduction
  core is reusable either way. This is why it is **non-material**: the choice is
  cheaply reversible and does not foreclose the live path. Per the brief's own
  steer, `read-on-demand` is "almost certainly right"; this plan concurs and
  records it as a bounded planner decision, not an operator escalation.

### 2.3 Integrations map

| This slice reads/uses | From | How |
|---|---|---|
| `Event`, `EventKind`, `RevertOccurredEvent`, `BusError`, `Event.from_json_line` | `gleipnir.bus.events` | typed read path — the ONLY door into the JSONL |
| `load_key`, HMAC/compare primitives | `gleipnir.verify.marker` | rate-table G-3.1 digest verify (fail-closed) |
| `.gleipnir/logs/<session>.jsonl` | Tier-1 RETRIEVED | input file(s), read-only |
| rate-table file + approved digest | Tier-3 POLICY (`keys/`, operator-authored) | **operator hand-off** — loader consumes; plan does not write them |

**What this slice does NOT integrate (named seams, reported as `Gap`s):** any
`IterationEvent`/`RetryEvent`/`TokenUsageEvent`/effort/efficiency event kind
(none exist on the bus yet — `EventKind` has only `REVERT_OCCURRED`); uplift
emission (the `Estimated` type is built and tested but **no uplift value is
produced** this slice); the live observer; TS-side emission.

### 2.4 Tier-3 operator hand-off (I cannot write these — flagged, not authored)

`gleipnir-plan` may write only `.gleipnir/plans/**`. The following are **Tier-3
POLICY, operator-only**, and are required before the *cost* metric could ever
move off `Gap` (which is post-S-2 anyway):

1. **Durable decision record** `.gleipnir/decisions/g4d-ledger.md` capturing
   D1–D4, the rate-table Tier-3 path + digest scheme, the cost-deferred-until-S-2
   posture, and the named metric seams. (Spelled out in §6 for the operator.)
2. **Rate-table file home** — exact path proposed for operator adoption:
   `.gleipnir/keys/rate-table.json` **or** a Tier-3 config path the operator
   chooses; and its **approved keyed digest** stored under `.gleipnir/keys/`
   (the G-3.1 digest home named in the memory-model decision, §"Reused
   primitive"). The loader must accept the path by configuration so it works in
   tests without touching Tier-3.

The ledger **code** is ordinary `src/` and is in scope for the implementing
agent; only the **files above** are the operator's.

### 2.5 Edge cases (each becomes a test in §4/§5)

1. **Empty or missing session log** — no events. Result: a `LedgerReport` with
   the revert metric = `Measured(revert_count=0, escalation_count=0, ...)`
   **iff** the file exists and is empty (a real measured zero), or — if the file
   is **missing** — the plan's call: treat a missing file as **zero events**
   (empty reduction), not an error, because a session that never emitted is a
   legitimate observation; `LedgerReport` still lists all seam `Gap`s. **Not an
   exception.** (Decide-and-justify: a missing Tier-1 log is an absence-of-
   telemetry fact, not a fault; raising would invert the authority ladder the
   bus's degrade-not-raise discipline established.)
2. **Log with only revert events** — the one metric computes normally; **every
   other metric is a `Gap`** (no other event kinds present). Assert the report
   *says gap*, not `0`.
3. **Malformed line** — `Event.from_json_line` raises `BusError`. **Decision:
   skip-with-count (robust), not fail.** For an OBSERVATION-tier reduction over
   Tier-1 telemetry, robustness beats brittleness: catch `BusError` per line,
   increment `LedgerReport.unreadable_line_count`, keep reducing, and **report
   the count** in the output. **Justification:** (a) it mirrors the bus's own
   Tier-1 degrade-not-raise posture (`emit` never raises; drops are *counted*,
   not silently swallowed); (b) one corrupt line must not blind the ledger to
   every valid line before/after it — that would make suppression easy; (c) the
   count is itself observable signal (a spike in unreadable lines is
   diagnostic). Silence is the failure mode we reject; a *counted* skip is not.
4. **Rate table missing / digest mismatch / key unavailable** — **fail-closed:
   cost stays a `Gap`** whose reason names the exact condition (`"rate table
   digest mismatch — refusing to emit cost"`, `"rate table absent"`, `"marker
   key unavailable"`). **Never** a guessed rate, never a raise into the
   reduction. (This is the D2 posture made concrete; note cost is a `Gap` this
   slice *regardless*, because of S-2 deferral — the digest machinery is built
   and tested so it is ready, and so the honesty property is provable now.)
5. **`Estimated` constructed without calibration** (or `kind=EstimateKind.UPLIFT`
   without a versioned notional rate) — **raises `LedgerError`** at construction.
   The uplift precondition is gated by the **typed `EstimateKind` discriminant**,
   never a `name == "uplift"` string. This is a programmer/contract error (not
   telemetry), so raising is correct here — it is the anti-vanity guarantee,
   symmetric with `attempt_gate` refusing a null attestation.
6. **Escalation-rate zero denominator (`escalation_rate = escalation_count /
   revert_count` with `revert_count == 0`)** — the 0/0 (and n/0) case. **Convention
   (stated, not implicit):** the `escalation_rate` `Measured` must carry an
   **inspectable `denominator == 0`**, and its numeric `value` must be a
   **non-misleading sentinel** — recommend **`value = None`** (with
   `denominator = 0`) so a consumer plainly sees the rate is **vacuous**, not a
   real positive float. A fabricated `0.0` would be a misleading rate (it reads
   as "0% escalation" when in truth *no reverts were observed at all*), which
   violates the "no fabricated numbers" principle. The convention is: **whenever
   `denominator == 0`, `value` is the vacuous sentinel (`None`) and the
   denominator is exposed for inspection** — the consumer must look at the
   denominator, never trust a bare rate. (This applies even in the
   revert-only-but-zero-escalated case only where reverts exist: there
   `revert_count > 0`, so the rate is a genuine `Measured` float — the sentinel
   is reserved strictly for `revert_count == 0`.)

### 2.6 Reconciliation scope honesty (note only — does not change behaviour)

**This slice's reconciliation is SELF-CONSISTENCY**, not cross-source. It
re-derives the revert metric from the **same** bus JSONL via the **same** typed
read path (`Event.from_json_line`) and asserts equality — so it catches a
**divergence between two call sites**, but **NOT a bug shared by both** (e.g. a
misread of the typed payload that both the reducer and the re-derivation would
make identically), because there is **no second ground-truth source yet**
(runtime usage logs / the rate table are not wired as reconciliation inputs).
**Cross-source reconciliation** — the full form in spec Conformance [D] — is a
**named seam** for when those independent inputs land. This note does not
overstate the guarantee: self-consistency now, cross-source later.

---

## 3. Link (validated before building)

- **Bus read path exists and is typed.** Confirmed: `Event.from_json_line`
  (`src/gleipnir/bus/events.py`:149) dispatches `kind -> payload class` and
  returns typed `RevertOccurredEvent` with `escalated: bool`
  (events.py:110) — so `payload.escalated` is a real typed attribute, no string
  parsing needed. `BusError` (events.py:47) is raised on malformed lines — the
  hook for edge case 3.
- **Digest primitives exist.** `verify/marker.py` provides `load_key`
  (fail-closed on missing/empty key, marker.py:86) and HMAC-with-`compare_digest`
  patterns (marker.py:204–213) plus the canonical `json.dumps(sort_keys=True,
  separators=(",", ":"))` serialization form — reusable for the rate-table digest
  without inventing crypto.
- **Tier map confirmed.** `logs/` = Tier-1 (read-only observation source);
  `keys/` + `decisions/` = Tier-3 POLICY (operator-only) — so the rate-table file
  and digest are hand-offs, and `.gleipnir/keys/` currently has no tracked files
  (confirmed by glob), consistent with the operator authoring them.
- **Stdlib-only precedent.** `tests/test_bus_stdlib_only.py` is the exact
  meta-test shape to copy for `src/gleipnir/ledger/` (AST top-level import roots
  vs. `sys.stdlib_module_names`, allowing `gleipnir`/`__future__`).
- **Baseline test count.** 220 tests currently green (per `g4-bus.md`
  Verification); this slice must keep them green and add ledger tests on top.
- **`EventKind` has only `REVERT_OCCURRED`** (events.py:58–61) — confirming that
  every non-revert metric legitimately has **no source kind**, i.e. is a genuine
  bus-emission gap, not a lazy omission.

---

## 4. Assemble (test-first build order)

Each step writes the test(s) first, watches them fail, then the minimal code to
pass. Steps are ordered so the anti-vanity guarantees are locked before any
number is produced.

1. **D3 metric types (`metric.py`), tests first.** Write tests asserting:
   `Estimated` **raises** without a `CalibrationBand`; an `Estimated` with
   `kind=EstimateKind.UPLIFT` **raises** without a versioned `NotionalHumanRate`
   while a non-uplift `EstimateKind` does **not** (the rate requirement is gated
   by the **typed `EstimateKind` discriminant**, never a `name == "uplift"`
   string); `Measured` constructs freely and exposes an inspectable
   `denominator`; `Gap` is a **distinct type** and never equals/serializes
   as a numeric `0`; serialization of each carries the `measured`/`estimated`/
   `gap` **discriminant**. Then implement the frozen dataclasses + the
   `EstimateKind` enum + `__post_init__` fail-closed checks. *(Locks the honesty
   type before any reducer exists.)*
2. **Revert reducer + `reduce()` skeleton (`reduce.py`), tests first.** Fixture
   JSONL: (a) revert-only stream → `Measured` revert_count/escalation_count
   correct, `escalation_count` from `payload.escalated`; (b) empty file → real
   `Measured(0,0)` + all seam `Gap`s; (c) missing file → empty reduction + all
   `Gap`s, no raise; (d) malformed line among valid ones → valid lines still
   reduced, `unreadable_line_count` incremented, no raise; (e) **`zero-revert`**
   (no reverts) → `escalation_rate` `Measured` with inspectable `denominator == 0`
   and vacuous `value` sentinel (`None`), NOT `0.0`; (f)
   **`revert-only-but-zero-escalated`** (reverts present, none escalated) →
   `escalation_rate` a genuine `Measured` `0.0` with `denominator > 0` (per edge
   case 6 / §5.A2). Then implement
   `reduce(session_log_path) -> LedgerReport` reading **only** via
   `Event.from_json_line`, assembling the one `Measured` metric and the full
   list of seam `Gap`s (with reasons).
3. **Rate-table loader + G-3.1 digest (`ratetable.py`), tests first.** Tests:
   valid table + matching approved digest → loads (but cost is *still* a `Gap`
   this slice, reason = S-2 deferral); missing table → `Gap` with reason;
   digest mismatch → `Gap` with reason, **no guessed rate**; key unavailable →
   `Gap` with reason; loader **never raises** into reduction, **never emits a
   cost number**. Then implement using `verify.marker` primitives + a temp key
   file fixture (as `test_marker.py` does).
4. **Reconciliation (`reconcile.py`), tests first.** Test independently
   re-derives revert_count/escalation_count from the raw JSONL and asserts
   equality with the `LedgerReport` value; test that the gap report enumerates
   **every** non-revert metric as a gap (asserting the report *says gap*).
   Then implement the re-derivation + gap-report builder.
5. **Stdlib-only meta-test (`test_ledger_stdlib_only.py`).** Copy the bus
   meta-test; allow `gleipnir`/`__future__`; assert only expected submodules
   exist. (Ledger *may* import `hashlib`/`hmac` via `verify.marker` — so, unlike
   the bus test, do **not** forbid `hmac`; do assert no third-party roots.)
6. **Full-suite green.** Run the whole suite in-sandbox; confirm the prior 220
   tests are untouched-and-green and the new ledger tests pass. Confirm **no cost
   number** appears anywhere in output (a test grepping the serialized
   `LedgerReport` for a cost value asserts the cost slot is `gap`).

---

## 5. Stress-test (concrete acceptance checks)

A. **Revert metric re-derived from raw JSONL equals the reducer's value.**
   `reconcile` independently counts reverts off the raw log and asserts equality
   with `LedgerReport`'s `Measured` revert_count. Divergence fails. *(Scope
   honesty: this is **self-consistency** re-derivation — see the note under §2.6;
   it catches a divergence between two call sites, not a bug shared by both.)*
A2. **Escalation-rate zero-denominator convention (0/0 is vacuous, never a
   fabricated rate).** Two fixtures exercise the convention of edge case 6:
   - **`zero-revert`** — a session log with **no `RevertOccurredEvent`s** at all
     (`revert_count == 0`). Assert the `escalation_rate` `Measured` has an
     **inspectable `denominator == 0`** and `value` equal to the stated vacuous
     sentinel (`None`) — **never** a misleading `0.0` positive float.
   - **`revert-only-but-zero-escalated`** — a session log with `RevertOccurredEvent`s
     present but **none `escalated=True`** (`revert_count > 0`,
     `escalation_count == 0`). Assert this yields a **genuine `Measured` rate of
     `0.0`** with `denominator == revert_count > 0` (a real measured zero, since
     reverts *were* observed) — distinguishing it in type/value from the vacuous
     `zero-revert` case above.
   Both assert the `denominator` is inspectable and the `value` follows the
   stated convention (consistent with "no fabricated numbers").
B. **Escalation counted via `payload.escalated` (typed), NOT string parse.**
   A fixture with mixed `escalated=True`/`False` reverts yields the correct
   escalation_count; a test asserts the ledger source contains no `re` import
   and no `.split(`/substring parse of event fields (AST/grep, mirroring the bus
   discipline).
C. **Every non-revert metric reports an explicit GAP — assert the report SAYS
   gap, not 0.** For iterations, retries, token_usage, cost,
   effort_attribution, efficiency, uplift: assert each entry is a `Gap` instance
   with a non-empty reason, and assert it is **not** a `Measured(value=0)`
   (type check, not value check).
D. **`Estimated` RAISES if constructed without a calibration band (+ versioned
   rate for the UPLIFT KIND), keyed off the TYPED discriminant.** `Estimated(...)`
   without `CalibrationBand` → `LedgerError`. An `Estimated` with
   `kind=EstimateKind.UPLIFT` and no versioned `NotionalHumanRate` → `LedgerError`;
   an `Estimated` of a **non-uplift `EstimateKind`** with no `NotionalHumanRate`
   **constructs** (proving the rate requirement is gated by the typed
   discriminant, not by all estimates and not by any `name` string). A test
   asserts the uplift precondition is driven by `EstimateKind` identity — the
   ledger source contains **no `name == "uplift"`** (or equivalent field-string)
   branch controlling construction (AST/grep, mirroring the no-stringly-typing
   discipline).
E. **`Measured` carries no such requirement.** `Measured(...)` constructs with
   no calibration and no rate, and its `denominator` is inspectable.
F. **Serialization carries the discriminant.** Round-trip each metric kind;
   assert the serialized form tags `measured`/`estimated`/`gap` and that a
   `gap`/`estimated` can never deserialize into a `Measured`.
G. **Rate-table loader verifies the G-3.1 digest and fails closed.** Mismatch,
   missing table, and unavailable key each leave cost a `Gap` with a precise
   reason; valid+matching still yields cost = `Gap` (S-2 deferral) this slice.
H. **NO cost number emitted this slice.** No code path produces a cost figure;
   the serialized report's cost slot is `gap`. (Grep-the-output test.)
I. **Empty log → real `Measured(0,0)` + seam gaps; missing log → empty
   reduction + seam gaps, no raise; malformed line → counted in
   `unreadable_line_count`, reduction continues, no raise.**
J. **Stdlib-only.** AST meta-test: no third-party top-level imports in
   `src/gleipnir/ledger/`.
K. **Existing 220 tests remain green;** full suite passes in-sandbox.

---

## 6. Execution Workflow

**For the implementing agent (`gleipnir-code`, test stage then code stage,
Sonnet), in the S-2 sandbox (`bin/gleipnir-sandbox`):**

1. **Read** this plan, `g4-bus.md`, `runtime-and-deps.md`, and
   `src/gleipnir/bus/events.py` + `src/gleipnir/verify/marker.py` before writing
   anything. The bus read path and the marker primitives are **reused, not
   reinvented**.
2. **Build strictly test-first in the §4 order.** The test IS the arbiter
   (Axiom 1) — write the failing test, watch it fail, then the minimal code.
   Do not implement a reducer before the D3 honesty type's fail-closed tests are
   green (order matters: the guarantee precedes the numbers).
3. **Hard invariants — do not violate:**
   - Read JSONL **only** through `Event.from_json_line`. No `json.loads` of a
     bus line by hand, no string/regex parse of any field. `payload.escalated`
     is read by **typed attribute**.
   - Emit **no cost number**. The cost slot is a `Gap` this slice, unconditionally
     (S-2 deferral), even when the rate table loads and its digest verifies.
   - Fabricate **no zeros** for absent event kinds. Absence → `Gap` with a
     reason. A real measured `0` (empty-but-present revert stream) is the *only*
     legitimate zero and it is a `Measured`, typed distinctly from a `Gap`.
   - Tier-1 reduction is **robust**: catch `BusError` per line, count it, keep
     going. The D3 type constructor is **strict**: raise on uncalibrated
     construction. (Robust on telemetry, fail-closed on contract — the two
     postures are deliberate, not inconsistent.)
   - Do **not** write anything under `.gleipnir/agents|skills|goals|decisions|
     keys` or `stage-role-map.md`. The rate-table file, its digest, and the
     `g4d-ledger.md` decision record are **operator/Tier-3 hand-offs**.
4. **Rate-table path is configurable.** The loader takes the table path and key
   path by argument (defaults may point at the Tier-3 home) so tests supply temp
   fixtures without touching Tier-3 — exactly as `test_marker.py` supplies a temp
   key file.
5. **Verify** in-sandbox: full suite green (prior 220 + new), coverage on the new
   package, and the §5 checks all pass. Do **not** self-declare done; hand the
   attestation to the gate.
6. **Hand back** to the orchestrator with: the passing suite, the new
   `src/gleipnir/ledger/` package, and an explicit note that the following
   **Tier-3 operator hand-offs remain open** (the operator, not the pipeline,
   authors them):
   - `.gleipnir/decisions/g4d-ledger.md` — durable record of **D1–D4**, the
     **rate-table Tier-3 path + G-3.1 digest scheme**, the
     **cost-deferred-until-S-2** posture, and the **named metric seams**
     (iterations, retries, token usage, cost, effort attribution, efficiency,
     uplift — each a bus-emission gap awaiting its event kind).
   - the **rate-table file** (proposed `.gleipnir/keys/rate-table.json` or an
     operator-chosen Tier-3 path) and its **approved keyed digest** under
     `.gleipnir/keys/`.

**Escalation trigger.** If, during build, a *material* tradeoff surfaces that
D1–D4 do not already resolve (e.g. a second real metric turns out to need an
event kind that would change the bus schema), **stop and route it back to the
brainstorm/convergence gate** — do not bake a new material decision into the
ledger. The only design question this plan resolved itself (D-Q1, read-on-demand)
was judged bounded and cheaply reversible; anything with lasting consequence is
the operator's.
