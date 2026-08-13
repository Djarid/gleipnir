# Plan: G-4 terminal/interoceptive event kinds + ledger metrics

**Stage:** `plan` (ATLAS Architect/Trace), produced by `gleipnir-plan` FROM the
operator-converged brief `.gleipnir/plans/g4-next-slice-brainstorm.md`
(Candidate 1, OPERATOR-CONVERGED at the precept-10 gate). This plan does **not**
re-decide the converged approach; it decides the concrete artifact set the brief
explicitly delegated to planning ("The plan will decide the exact new
`EventKind` names/payload shapes"). Tier-0 session artifact (disposable).

**Pipeline:** FULL 8-stage (`brainstorm→plan→spec-review→test→code→quality→git→
gate`). This touches `src/**` (executable artifacts: `src/gleipnir/bus/events.py`,
`src/gleipnir/ledger/{reduce,reconcile}.py`, `src/gleipnir/engine/driver.py`,
`tests/**`), so it is disqualified from the prose/config-only track by Axis-1 of
`stage-role-map.md`. Test-first: the test is the arbiter.

---

## ⚠ Material scope discovery for the operator (surfaced, NOT re-decided)

The brief's Selected Approach names three metrics to promote from `Gap` to
`Measured`: **iteration-cap-hit, escalation, and retry**. Verifying against
source (`src/gleipnir/engine/__init__.py`, `engine/DESIGN.md`,
`engine/driver.py`) shows the engine model does **not** supply three distinct
un-emitted facts under those names. This is a *material tradeoff* the brief left
open ("Whether 'retry' is derivable from existing engine state or needs a
distinct driver-observed trigger" — Open Questions) and that source now resolves.
It is surfaced here for operator visibility; the plan proceeds on the honest,
source-grounded subset and does **not** invent metrics with no source fact
(anti-vanity contract, `g4d-ledger.md` D1/D3).

Findings (each cited to source):

1. **Escalation is ALREADY emitted.** `RevertOccurredEvent.escalated: bool`
   (`events.py:110`) already carries the budget-exhausting escalation hop; the
   driver emits it today with `to_state=ESCALATED, escalated=True`
   (`driver.py:256-265`) and the ledger already counts it as `escalation_count`
   / `escalation_rate` (`reduce.py:167-192`). A separate `ESCALATION` `EventKind`
   would be **redundant** with the escalated revert → **scoped OUT** (do not
   create an overlapping kind; brief's own caution, prompt directive).

2. **"Iteration-cap-hit" == the escalated revert in the engine's model.** The
   engine has **no iteration counter**. Its only cap is the *global revert
   budget* (`DEFAULT_REVERT_BUDGET`, `__init__.py:87`); reaching it IS the
   escalation hop already emitted (point 1). The retired self-loop / per-state
   `loop_count` / `LOOPING_STATES` model is explicitly **superseded**
   (`__init__.py:82-87`, `DESIGN.md:130-131`). So there is no separate
   "iteration cap" fact to emit — it collapses into the escalated revert →
   **scoped OUT** as a distinct kind. The `_SEAM_REASONS["iterations"]` entry
   (`reduce.py:51`, reason "no IterationEvent kind on the bus yet") therefore
   describes a fact the engine does not produce; it **stays a `Gap`**, with its
   reason UPDATED to state this honestly (see D6).

3. **"Retry" has no engine source fact.** A "retry" (re-attempting the same
   stage in place) does not exist: `Verdict.FAIL` routes *backward* (a revert),
   never a self-loop (`__init__.py:411-432`, `DESIGN.md:124-131`). The revert
   IS already emitted. There is no distinct retry trigger the driver observes.
   `retries` **stays a `Gap`**, reason UPDATED (D6). **Deferred with rationale —
   not invented.** (Directly answers the brief's Open Question and the prompt's
   "be honest, don't invent a metric with no source fact.")

4. **There ARE genuinely-new un-emitted terminal/interoceptive facts** the
   driver observes in-process, and they are the honest content of this slice:
   - **The human-question gate hop** (`NEEDS_HUMAN` → `HUMAN_QUESTION`): a
     precept-10 interoceptive fact ("work asked for a human"). Currently the
     driver emits **nothing** for it (`driver.py:279-282` branch C; and
     `test_driver_emits_revert.py:185-199` asserts *no revert event*, but no
     event of any kind is emitted). This is a real new fact.
   - **The clean-completion terminal** (`GIT` → `GATE` via
     `Engine.attempt_gate`): a G-3.2 terminal-reached fact. Currently un-emitted.

**Net decision on the metric set (D1–D6 below):** promote **two honest new
`Measured` metrics** the driver can source now — `human_question_count` and
`gate_reached_count` — via **two new `EventKind`s** (`NEEDS_HUMAN_RAISED`,
`GATE_REACHED`); keep `iterations`/`retries`/`escalation`(-as-distinct-kind) out,
with the two lingering seam reasons rewritten to be truthful. This preserves the
brief's converged intent (widen what the senses measure at the ledger's named
plug-in point, engine stays pure, driver emits) while refusing to fabricate the
three brief-named metrics that have no distinct source. **If the operator
requires the literal `iterations`/`retries` names promoted, that needs a prior
engine change (add an iteration/retry concept) — a separate, larger slice — and
should go back through the brainstorm gate; it is NOT buildable now.**

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D0 | Overall approach | Candidate 1: new engine-computed terminal/interoceptive `EventKind`s + matching ledger `reduce()`/`reconcile()` branches (OPERATOR-CONVERGED, brief §Selected Approach) | Observer; TS emission; novelty triage; per-event integrity (brief RICE/matrix) | Operator-converged at precept-10 gate; not re-decided here |
| D1 | Which new `EventKind` members | `NEEDS_HUMAN_RAISED`, `GATE_REACHED` (two members) | `ESCALATION`, `ITERATION_CAP_HIT`, `RETRY` | Escalation/iteration-cap already carried by escalated `RevertOccurredEvent` (redundant); retry has no engine source (see Material Discovery 1–3). These two are the only *new, un-emitted, driver-observable* facts |
| D2 | Payload for `NEEDS_HUMAN_RAISED` | frozen `NeedsHumanRaisedEvent(from_state: str)` | free dict; adding `to_state` (always `human_question`, redundant) | Mirrors `RevertOccurredEvent` (frozen, typed). `from_state` lets the ledger attribute-count which stage raised it; the `to_state` is invariant so omitted |
| D3 | Payload for `GATE_REACHED` | frozen `GateReachedEvent(pipeline_id: str)` | free dict; empty payload | Mirrors the typed pattern; `pipeline_id` gives a countable, attribute-read fact (from `Engine.pipeline_id`). Never string-matched |
| D4 | Where each emits in the driver | `NEEDS_HUMAN_RAISED` from `advance` (extend `_emit_*` after the revert classifier) when `result.state is HUMAN_QUESTION`; `GATE_REACHED` from a new emit call in a NEW driver method wrapping/after `Engine.attempt_gate` | emitting from `Engine.step`/`attempt_gate` (engine impurity) | Engine stays pure (`g4-bus.md` invariant; AST test `test_engine_package_imports_no_bus_module`). Driver is the I/O boundary. Write-bridge-before-emit + degrade-not-raise preserved |
| D5 | New `Measured` metrics in `reduce()`/`LedgerReport` | `human_question_count`, `gate_reached_count` (raw counts, `denominator=1`) | promoting `iterations`/`retries`; a `human_question_rate` | Two honest counts sourced from the two new kinds. No rate this slice (no meaningful denominator convention converged); raw-count convention mirrors `revert_count` (`reduce.py:161-166`) |
| D6 | The `iterations`/`retries` seams | stay `Gap`; rewrite their `_SEAM_REASONS` text to name the true blocker (engine has no iteration/self-loop-retry concept; superseded by revert-edge model) | flip to `Measured` (fabrication — no source fact); silently leave stale reasons | Anti-vanity (`g4d-ledger.md` D1). Honest reason > misleading zero. Keeps the named seam truthful |
| D7 | `reconcile.py` update | add independent re-derivation of the two new counts in `_recount_from_raw_jsonl`; add fields to `ReconciliationReport`; assert equality with the report in `reconcile()` | leave reconcile unchanged (would break the LOCKED two-call-site consistency property) | `g4d-ledger.md` D4: reconcile RE-DERIVES independently and raises `LedgerError` on divergence. New `Measured` metrics MUST be re-derived or the invariant is silently violated |
| D8 | `escalation`(-as-distinct-kind) | scope OUT; keep existing escalated-revert path unchanged | new `ESCALATION` kind | Avoids an overlapping/redundant kind (Material Discovery 1) |
| D9 | Scope-out set (deferred seams) | token-provenance ingress (blocked), cost (S-2-gated), effort attribution, `iterations`/`retries` metrics, Seam-7 live emission | expanding toward "all measured metrics" | Brief §Scoped OUT + Material Discovery; hold the scope-creep line (brief bias check) |

---

## Architect

**Problem (one sentence).** The G-4d ledger has a named plug-in point for
engine-computed terminal/interoceptive metrics that are currently only `Gap`s;
add the buildable-now typed event kinds + driver emission + ledger reduction so
two genuinely-new honest `Measured` facts (a human-gate count and a
clean-completion count) exist at that plug-in point, without fabricating the
metrics that have no engine source.

**User.** The G-4d ledger / future observer (the typed-stream consumers), and
the operator reading honest interoceptive metrics — never a fabricated zero.

**Measurable success criteria.**
1. `EventKind` gains exactly two members (`NEEDS_HUMAN_RAISED`, `GATE_REACHED`),
   each with a frozen payload dataclass and one `_PAYLOAD_CLASSES` row; the
   read-path stays table-driven (no `re`, no `.split`) — the existing static
   AST tests (`test_bus_events.py:255-273`) still pass.
2. The driver emits `NeedsHumanRaisedEvent` on the `NEEDS_HUMAN`→`HUMAN_QUESTION`
   hop and `GateReachedEvent` on the `GIT`→`GATE` (attempt_gate) transition,
   engine unchanged (the `test_engine_package_imports_no_bus_module` AST purity
   test still passes), write-bridge-before-emit ordering preserved, emission
   degrades-not-raises.
3. `reduce()` returns a `LedgerReport` with two new `Measured` fields
   (`human_question_count`, `gate_reached_count`) counted by typed attribute
   access, plus the (now-truthfully-worded) `iterations`/`retries` `Gap`s.
4. `reconcile()` independently re-derives both new counts and raises
   `LedgerError` on any divergence from the report (the two-call-site
   consistency invariant holds for the new metrics too).
5. `bin/gleipnir-sandbox test` green; line+branch coverage ≥ 85% (target from
   `gleipnir-code.md`); no metric is a fabricated zero (`Gap`≠`Measured(0)`
   preserved).

**Constraints (LOCKED invariants — do not violate).**
- **Engine purity** (`g4-bus.md`; `test_engine_package_imports_no_bus_module`,
  `test_driver_emits_revert.py:246-257`): `engine/__init__.py` imports no `bus`,
  has no I/O. All new emission is in the **driver**.
- **Typed-not-prose read path** (`g4-bus.md` D1; `test_bus_events.py:255-273`):
  new payloads are frozen dataclasses; ledger counts by `event.payload.<attr>`
  and `event.kind is EventKind.X`, never a string/regex/substring match.
- **Degrade-not-raise** (`g4-bus.md`; `emit.py`): emission never raises into the
  driver's control flow; `write_bridge()` (authority-bearing) runs before any
  emit.
- **Anti-vanity honesty types** (`g4d-ledger.md` D1/D3): a metric with no source
  fact is a `Gap`, never a fabricated `Measured(0)`. `Gap` and `Measured` stay
  distinct types.
- **Reconciliation re-derives independently** (`g4d-ledger.md` D4): the second
  call site (`reconcile.py`) has its own re-derivation body; new metrics must be
  added there too or the invariant is silently broken.
- **Stdlib-only** (`runtime-and-deps.md`): only `json`/`dataclasses`/`enum` in
  `events.py`; `json`/`dataclasses`/`pathlib` in `reduce.py`/`reconcile.py`. The
  `test_*_stdlib_only.py` tests enforce this.
- **Edit grant:** all touched files are outside `gleipnir-code`'s deny set
  (`.gleipnir/**`, `.git/**`, `src/gleipnir/preflight/**`) — CONFIRMED against
  `.gleipnir/agents/gleipnir-code.md:11-16`. Agent-buildable.

## Trace

**Artifacts and where they live (source of truth = the cited source files).**

| Artifact | File (verified to exist) | Change |
|---|---|---|
| `EventKind` enum | `src/gleipnir/bus/events.py:58-61` | Add `NEEDS_HUMAN_RAISED = "needs_human_raised"`, `GATE_REACHED = "gate_reached"` |
| Payload dataclasses | `src/gleipnir/bus/events.py` (after `RevertOccurredEvent`, ~L111) | Add frozen `NeedsHumanRaisedEvent(from_state: str)`, `GateReachedEvent(pipeline_id: str)` |
| Payload registry | `src/gleipnir/bus/events.py:115-117` | Add two `_PAYLOAD_CLASSES` rows |
| `__all__` / package export | `events.py:33-40`, `bus/__init__.py:12-30` | Export the two new payload classes |
| Driver emit — needs-human | `src/gleipnir/engine/driver.py` `advance` (L226-229) + `_emit_revert_if_any` (L240-293) | Add a needs-human emit (either extend the classifier method or a sibling `_emit_needs_human_if_any`); emit `NEEDS_HUMAN_RAISED` when `result.state is HUMAN_QUESTION` |
| Driver emit — gate reached | `src/gleipnir/engine/driver.py` (NEW method, e.g. `attempt_gate(...)` wrapper) | The driver has no `attempt_gate` wrapper today; add one that calls `self.engine.attempt_gate`, does `write_bridge()`, then emits `GATE_REACHED` on success. Fail-closed key/bridge ordering as in `advance` (L218-224) |
| Ledger reduce | `src/gleipnir/ledger/reduce.py` `reduce()` loop (L144-159), `LedgerReport` (L79-107) | Count the two new kinds; add `human_question_count`/`gate_reached_count` `Measured` fields + `to_dict` rows |
| Seam reasons | `src/gleipnir/ledger/reduce.py:50-66` (`_SEAM_REASONS`) | Rewrite `"iterations"`/`"retries"` reasons (D6); leave them as `Gap`s |
| Reconcile | `src/gleipnir/ledger/reconcile.py` `_recount_from_raw_jsonl` (L57-90), `ReconciliationReport` (L43-54), `reconcile()` (L93-133) | Re-derive both new counts; add report fields; assert equality (raise `LedgerError` on divergence) |
| Honesty types | `src/gleipnir/ledger/metric.py` `Measured` (L113-137) | NO change — construct new metrics via existing `Measured(name,value,denominator=1,provenance=...)` |
| Tests | `tests/test_bus_events.py`, `tests/test_driver_emits_*.py` (new file or extend), `tests/test_ledger_reduce.py`, `tests/test_ledger_reconcile.py`, `tests/test_bus_stdlib_only.py`/`test_ledger_stdlib_only.py` (unchanged, must still pass) | RED-first: see Assemble |

**Integrations map.** Emit flow: `Driver.advance`/`Driver.attempt_gate`
→ `EventBus.emit(kind, payload, ...)` → JSONL line in
`.gleipnir/logs/<session_id>.jsonl` (Tier-1). Read flow: `reduce(log_path)` /
`reconcile(log_path, report)` → `Event.from_json_line` (typed dispatch via
`_PAYLOAD_CLASSES`) → `event.kind is EventKind.X` + `event.payload.<attr>`. The
engine (`Engine.step`, `Engine.attempt_gate`) is **untouched** — it remains the
pure state machine; the driver reads its `StepResult`/state and emits.

**Edge cases.**
- Multiple `NEEDS_HUMAN` hops in one session → each emits one event; ledger
  counts each (raw count, `denominator=1`, mirroring multi-revert
  `test_driver_emits_revert.py:122-143`).
- `GATE_REACHED` should fire only on a *successful* `attempt_gate` (state
  actually became `GATE`); a refused gate (`AttestationNotGreen` etc. — engine
  raises, `driver.py`/`__init__.py:490-496`) emits nothing (no terminal
  reached). Emit only after the engine returns a `StepResult(state=GATE)`.
- Empty/missing log → both new counts are genuine `Measured(0, denominator=1)`
  (a measured zero — distinct from a `Gap`), consistent with `revert_count`'s
  empty-file behaviour (`reduce.py` docstring L126-127).
- Malformed line → folded into `unreadable_line_count` as today
  (`reduce.py:150-152`); new counts unaffected.
- Reconcile divergence on a new count → `LedgerError` (fail-closed contract),
  symmetric with the existing revert/escalation divergence raises
  (`reconcile.py:106-115`).
- Degraded emit (un-writable `logs/`) → `EmitResult(ok=False)`, `dropped++`,
  advance/gate still succeeds (`emit.py:126-128`; `g4-bus.md` degrade-not-raise).

## Link (validated before building)

- **`EventKind` extension pattern verified** — enum member + frozen payload +
  one `_PAYLOAD_CLASSES` row + table-driven `from_json_line` (`events.py`
  read fully). Adding a kind is the documented low-friction extension.
- **Driver emit pattern verified** — `_emit_revert_if_any` (`driver.py:240-293`)
  is the crash-safe classify-then-emit model; write-bridge-before-emit ordering
  at L224-226; `bus is None` no-op guard at L251-252.
- **Engine has NO retry/iteration concept** — verified in `engine/__init__.py`
  (revert-edge model, global budget, retired self-loop) and `DESIGN.md`. This is
  the load-bearing fact behind D1/D6 and the Material Discovery.
- **`attempt_gate` is engine-only today** — the driver has no gate wrapper
  (`driver.py` has `advance`/`advance_on_clean_completion`/`write_bridge`/
  `resume_from_bridge` only); D4 adds one. Verified.
- **Reconcile is a genuinely separate re-derivation body** — `_recount_from_raw_jsonl`
  (`reconcile.py:57-90`) is not a call into `reduce()`; the new counts must be
  added to BOTH bodies (D7). Verified.
- **`Measured`/`Gap` construction** — `Measured(name, value, denominator,
  provenance)`; `Gap(name, reason)` (`metric.py:113-137, 189-199`). New metrics
  use the raw-count convention `denominator=1` like `revert_count`.
- **Edit grant** — all target paths outside `gleipnir-code` deny set
  (`gleipnir-code.md:11-16`). Verified. Sandbox entrypoint
  `bin/gleipnir-sandbox test` is the arbiter.

## Assemble (build order — test-first)

1. **RED: bus schema tests** — extend `tests/test_bus_events.py`: the two new
   `EventKind` members exist and are `str`-valued; `NeedsHumanRaisedEvent`/
   `GateReachedEvent` are frozen, carry their fields, are not free dicts;
   round-trip through `to_json_line`/`from_json_line` into TYPED objects;
   unknown-kind still raises `BusError`. The existing no-`re`/no-`.split` static
   checks must still pass. → then implement in `events.py` (enum, payloads,
   registry, exports) + `bus/__init__.py` export. GREEN.
2. **RED: driver emit tests** — extend/add `tests/test_driver_emits_*.py`:
   (a) a `NEEDS_HUMAN` advance emits exactly one `NEEDS_HUMAN_RAISED` event with
   `from_state` = the raising stage, correct envelope (agent/turn/session/
   artifact_ref), and emits **no** revert event; (b) a full drive to a
   green-attestation gate emits exactly one `GATE_REACHED` with `pipeline_id`;
   (c) a refused gate emits nothing; (d) engine-purity AST test still passes;
   (e) a driver with no bus still works and does not raise on either path;
   (f) write-bridge-still-runs / degrade-not-raise. → then implement driver
   changes (D4): extend the needs-human branch (currently branch C returns with
   no emit, `driver.py:279-282`) and add the `attempt_gate` wrapper. GREEN.
3. **RED: ledger reduce tests** — extend `tests/test_ledger_reduce.py`: a log
   with N needs-human + M gate-reached events yields
   `human_question_count == Measured(N, denominator=1)` /
   `gate_reached_count == Measured(M, denominator=1)`; empty log yields genuine
   `Measured(0,1)` for both (NOT a `Gap`); `iterations`/`retries` remain `Gap`s
   with the new truthful reasons; counting is by typed attribute (a crafted
   payload proves no string-match). → implement `reduce.py` (loop branches,
   `LedgerReport` fields + `to_dict`, `_SEAM_REASONS` reason rewrite). GREEN.
4. **RED: reconcile tests** — extend `tests/test_ledger_reconcile.py`: reconcile
   re-derives both new counts and returns them; a report with a tampered new
   count raises `LedgerError`; the gap enumeration still lists
   `iterations`/`retries`. → implement `reconcile.py` (re-derive in
   `_recount_from_raw_jsonl`, `ReconciliationReport` fields, equality asserts in
   `reconcile()`). GREEN.
5. **Full sandbox run** — `bin/gleipnir-sandbox test`; confirm the whole suite
   (including the untouched engine 49, stdlib-only, and existing bus/ledger/
   driver tests) is green and line+branch coverage ≥ 85%.

## Stress-test (acceptance checks)

- **A. Schema:** `EventKind` has exactly the two new members; each has one
  `_PAYLOAD_CLASSES` row; `from_json_line` reconstructs the correct typed
  payload; an unregistered kind still raises `BusError`.
- **B. Typed-not-prose (LOCKED):** `test_bus_events.py`'s no-`re`-import and
  no-`.split` static checks pass unchanged; the ledger counts the new kinds by
  `event.kind is EventKind.X` + `event.payload.<attr>` (a test with a payload
  whose field value would defeat a naive string-match proves attribute counting).
- **C. Engine purity (LOCKED):** `test_engine_package_imports_no_bus_module`
  passes; `engine/__init__.py` diff is empty (engine untouched).
- **D. Driver emit correctness:** needs-human hop → one `NEEDS_HUMAN_RAISED`,
  no revert event; successful gate → one `GATE_REACHED`; refused gate → none;
  no-bus driver raises on neither path; write-bridge runs before emit;
  degraded emit does not fail the advance/gate.
- **E. Ledger measured (honesty):** new counts are `Measured` with
  `denominator=1`; empty log → `Measured(0,1)` (a measured zero, NOT a `Gap`);
  `iterations`/`retries` are still `Gap`s (assert `isinstance(...);` and the new
  reason text); `Gap` never deserializes/reads as `Measured(0)`.
- **F. Reconcile consistency (LOCKED):** reconcile re-derives both new counts
  independently; a divergence raises `LedgerError`; the two call sites agree on
  every measured value.
- **G. Full suite + coverage:** `bin/gleipnir-sandbox test` green; ≥85%
  line+branch; stdlib-only tests pass.
- **H. Scope honesty:** no `EventKind`/`Measured` for token/cost/effort/
  iteration/retry/escalation-as-distinct-kind was added (grep the diff);
  scope-out set from D9 is untouched.

## Execution Workflow

- **Role/model:** `gleipnir-code` (Sonnet) per the stage-role map — this is
  `test` then `code` stages, both bound to `gleipnir-code`. Test-first: author
  the RED tests, then implement to green; never weaken a test to pass.
- **Verify only via** `bin/gleipnir-sandbox test` (in-container, coverage).
  Report pass count + line+branch coverage%. Host pytest is not granted.
- **Order:** follow Assemble steps 1→5 strictly (schema → driver → reduce →
  reconcile → full run); each step RED before GREEN.
- **Do NOT touch** `engine/__init__.py` (purity), any `.gleipnir/**` file
  (denied; the two decision records `g4-bus.md`/`g4d-ledger.md` are Tier-3 and
  operator-authored — if this slice warrants a new durable decision record for
  the two new kinds, NAME it for the operator, do not write it).
- **Reconcile is not optional** — a `reduce()` metric with no matching
  `reconcile()` re-derivation silently breaks the LOCKED two-call-site
  invariant; both bodies change together (D7).
- **On completion:** report changed files, pass count, coverage%, and confirm
  the engine diff is empty (purity) and reconcile covers the new metrics. Hand
  back to the orchestrator, which routes `quality` → `git` → `gate`.
- **Operator decision pending (from Material Discovery / D6):** if the operator
  wants the literal `iterations`/`retries` metrics promoted to `Measured`, that
  requires FIRST adding an iteration/retry concept to the engine — a separate,
  larger slice that must go back through the brainstorm gate. It is out of scope
  and not buildable now. This plan promotes the two honest facts that DO have an
  engine source.
