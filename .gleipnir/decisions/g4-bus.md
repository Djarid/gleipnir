# Decision: G-4 event bus — first slice (typed bus + emit + revert-hop consumer)

**Status:** decided and implemented. Durable decision record (Tier-3,
operator-authored). Converged via the orchestrator-surfaced decision gate
(brainstorm Decision Analysis → operator convergence). Plan of record:
`../plans/g4-bus-first-slice.md` (spec-review approved, 2 rounds; quality-gated).

## Scope (first slice only)

Realises the minimal, useful first slice of spec G-4: a **typed event bus +
`emit()` + persistence to Tier-1 `logs/`**, with **one real consumer** wired
(the engine revert-hop). Everything else in G-4 is explicitly **deferred as a
named seam**, not built: the metrics ledger (G-4d), novelty triage (G-4c, spec
says last — needs signal history), platform-webhook ingress (E-2, no component
home), the observer/consumers, TS-side emission, and per-event integrity.

## Converged decisions (operator-decided)

- **D1 — Event schema/typing = Option C.** A frozen `Event` **envelope**
  (the eight G-4a fields — emitter, enforcement_surface, agent, action,
  session_id, originating_turn, artifact_ref, timestamp — plus `version`,
  `sequence`, `kind`) composed with a **typed per-kind payload dataclass**
  (`RevertOccurredEvent` for this slice), NOT a free-string dict. `from_json_line`
  dispatches `kind → payload class` and reconstructs typed objects, so the
  observer reads fields by attribute — never string/regex/substring parsing
  (the AETOS failure). Enforced by AST/grep tests, not just prose. `action` is
  a **short tag, never a parse target**. `agent` and `artifact_ref` are always
  structurally present but nullable-valued (`str | None`) — a deliberate D1
  reading.
- **D2 — Transport = Option A.** Python append-only JSONL, one file per session
  at `.gleipnir/logs/<session_id>.jsonl`; `EventBus.emit` stamps
  `version`/`sequence`/`timestamp` and appends one line. **TS-side emission is a
  documented seam, not built** (the one concrete consumer this slice — the
  revert hop — is Python). `session_id` + `originating_turn` + monotonic
  `sequence` + `version` are in the schema from day one so the TS seam and the
  future ledger slot in without a format break. Single Python writer this slice;
  multi-writer coordination is a named deferred concern.
- **D3 — Integrity = Option A (no HMAC).** `logs/` is Tier-1 RETRIEVED —
  observation-only, cannot escalate into policy (the authority ladder is the
  defence). The bridge/marker needed an HMAC because they *gate agents / skip
  work* (authority-bearing); bus events only *inform*. So append-only +
  provenance is sufficient; **no HMAC, no `verify/marker.py` import, no S-2 key
  in the telemetry path.** The `version` field reserves the slot to add
  integrity later *if* the ledger makes suppression an economic-gaming vector.
- **D4 — Slice boundary.** schema + `emit()`/JSONL + wire the revert-hop as the
  one real consumer; everything else deferred (above).

## Engine purity (implementation invariant)

Emission is wired in the **driver** (`Driver.advance` / `_emit_revert_if_any`),
**never** in `Engine.step`. The engine stays pure/in-memory (no I/O, no bus
import) — a documented, tested invariant the 49 engine tests rely on. The
`EventBus` is constructor-injected and **None-safe**: `Driver()` and
`Driver.resume_from_bridge()` without a bus behave exactly as before (no emit).

**Crash-safe revert classification** (the spec-review BLOCKER that was fixed):
`PIPELINE_ORDER` excludes `ESCALATED` and `HUMAN_QUESTION`, so `.index()` is
never called on them. The driver classifies by `StepResult.escalated` first
(the budget-exhausting hop → emit with `to_state = ESCALATED.value` as an
explicit constant, `escalated=True` — this IS the Nth revert and the most
important to log), then a normal-revert branch guarded by `in PIPELINE_ORDER`
membership before any index compare, else emit nothing (NEEDS_HUMAN / forward
PASS) without raising.

## Degrade-not-raise (Tier-1 discipline)

`EventBus.emit` **never raises into the caller's control flow**: an un-writable
`logs/` (or a serialization error from a future bad payload) degrades to
`EmitResult(ok=False, …)` and increments a `dropped` counter (observable, not a
silent swallow). In `Driver.advance`, the authority-bearing `write_bridge()`
runs *before* emit, so a telemetry failure structurally cannot block a
higher-tier advance.

## Discharges

This discharges the revert-hop logging **obligation/seam** recorded in
`engine-revert-edges.md` (§mitigation #1) and at the engine revert site: each
revert hop is now emitted as a `RevertOccurredEvent`. The engine comment is
updated to point at the driver as the discharge site (engine stays pure).

## Verification

`src/gleipnir/bus/{events,emit}.py` + driver wiring, in-sandbox: 220 passed,
97% coverage (line+branch); `emit.py` 100%, `driver.py` 100%, engine untouched
(49 tests green). Typed-not-prose, crash-safe classify (incl. the ESCALATED and
NEEDS_HUMAN cases), and degrade-not-raise all covered by real assertions.
Quality-gated.

## Known not-yet-closed / seams

- TS-side emission (post-tool hook telemetry) — deferred.
- Ledger (G-4d), triage (G-4c), observer, platform-webhook ingress (E-2) —
  deferred; the bus provides the typed stream they will consume.
- Per-event integrity — deferred; `version` slot reserved; revisit at the
  ledger if suppression becomes an economic-gaming vector.
- Multi-writer append coordination — single Python writer this slice.
