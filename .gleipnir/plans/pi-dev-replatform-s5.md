# Plan: S5 — G-3.1 attestation (HMAC marker) in TypeScript, + full 4b signed-persistence wiring

> **Role:** `gleipnir-plan` (plan stage). **Planned FROM** the CONVERGED brief
> `.gleipnir/plans/pi-dev-replatform-s5-brainstorm.md` (all six decisions
> D-S5-1..6 decided by the operator; **D-S5-4 DIVERGED to the WIDER scope 4b** —
> full signed-persistence lifecycle wiring, not primitive-only). This plan does
> NOT re-derive those decisions; it refines them into concrete Assemble steps
> and an acceptance-check set traceable line-for-line to the Python oracle
> (`src/gleipnir/engine/bridge.py` + `src/gleipnir/verify/marker.py` +
> `tests/test_bridge.py`) and grounded in the PROVEN TS reference
> (`.gleipnir/plugins/sequence-gate.ts` + `tests/test_sequence_gate.mjs`), all
> read directly this session (L-C36).

## GOTCHA pre-flight (visible)

- **Goals checked:** `.gleipnir/goals/manifest.md` → `plan-format.md` is the
  binding artifact/format goal; this plan follows its 8 required sections
  including the **Design Principles** Gate-1 section (case (i), OOP/functional
  TS). `methodology.md` (ATLAS/GOTCHA-ahead-of-planning) satisfied by this
  plan's shape.
- **Plan-before-code:** confirmed. `pi-package/src/verify/` does NOT yet exist
  (glob of `pi-package/src` returns only `roleTable/enforcement/delegate/depth/
  activeRole.ts` + `engine/*`). `pi-package/test/marker.test.ts` does NOT exist.
  This is a plan; it writes only to `.gleipnir/plans/`.
- **GOTCHA layer mapping:** this slice spans two GOTCHA layers. The marker
  primitive (`verify/marker.ts`) is the **Tools**-layer crypto boundary (the
  keyed HMAC that produces *unforgeable evidence* — the "deterministic code"
  half of the probabilistic↔deterministic bridge). The lifecycle wiring
  (`session_before_compact`/`session_start(resume)`/`pi.appendEntry`) is the
  **Orchestration**-layer persistence seam (engine position survives restart/
  compaction under a signed marker). No **Hard-prompt** or **Context** work.
- **Capability boundary:** I may write ONLY `.gleipnir/plans/**`. This plan file
  is the sole artifact I produce. No code, no tests, no Tier-3.
- **`session_before_compact` verification (MANDATORY Trace, per delegation +
  L-C36): CONFIRMED against primary source** — see §Link and §Trace. The full
  4b wiring is buildable; NO `## BLOCKING` section is required.

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-S5-1 | Which marker construct S5 ports | **Option B** — port `bridge.py`'s `StateMarker` construction; tree-hash `Marker` DEFERRED | A (verifier `Marker` only), C (both) | Operator-converged (brief §Selected Approach). The golden fixtures ARE `StateMarker` vectors; B directly meets the exit criterion; byte-parity already proven in `sequence-gate.ts`. Tree-hash has no in-process pi consumer (building-ahead-of-need). ASSUMPTION-3 resolved: byte-for-byte, no re-spec. |
| D-S5-2 | Node crypto module | **Node built-in `node:crypto`** (`createHmac("sha256")` + `timingSafeEqual` with equal-length guard) | npm HMAC package | Operator-converged. stdlib-only-core (`runtime-and-deps.md`); matches proven `sequence-gate.ts` exactly. |
| D-S5-3 | `resumeAt` raw-string brand-check scope | **Option 3b → IN SCOPE** (coupled to 4b) | 3c (standalone follow-up) | Operator-converged. Because D-S5-4=4b wires the signed rehydration path, an unvalidated raw-string `resumeAt` at that entry would be a hole; the brand-check lands in the same slice. |
| D-S5-4 | Signed-persistence scope | **Option 4b — primitive + FULL signed-persistence wiring NOW** (mint-on-transition + `pi.appendEntry` + rehydrate/validate on `session_before_compact` + `session_start(resume)`) | 4a (primitive-only, wiring deferred to S8/S5.5) | **Operator-converged; DIVERGED from brainstorm recommendation (4a).** Operator chose the wider scope. S5 delivers end-to-end restart+compaction survival. |
| D-S5-5 | Module placement | **Option 5a — new `pi-package/src/verify/marker.ts`** | 5b (fold into attestation.ts), 5c (primitive + explicit attestation binding) | Operator-converged. Honours the SRP `attestation.ts` documents (its one reason to change is the attestation SHAPE, not crypto); mirrors Python `verify/` module + the proven reference's separation. |
| D-S5-6 | Test-port manifest | **Option 6a — ported `test_bridge.py` unit suite + DISTINCT golden-vector class** (fixtures reused in-place) | 6b (single combined file), 6c (also port tree-hash `test_marker.py`) | Operator-converged. Unit suite proves logic with locally-minted markers; golden class proves cross-language byte-parity. Kept separate so a byte-drift failure is diagnosable independently of a logic regression. |
| D-S5-P1 | **[PLAN-STAGE JUDGMENT]** Which boundary rule governs touching S4 modules (`state.ts`/`engine.ts`) | The additive-only rule from **D-S4-6's *spirit*** applies, but **D-S4-6's literal "zero edits to the five S1–S3 modules" does NOT** — `state.ts`/`engine.ts` are **S4-built** engine modules, not the five S1–S3 modules (`roleTable/enforcement/delegate/depth/activeRole.ts`). The genuine governing constraint is the brief's Constraint "No scope-creep into S4's engine": S5 must NOT alter `attemptGate` refusal logic, `TRANSITIONS`, the revert budget, or the five S1–S3 modules. The `resumeAt` brand-check is an **ADDITIVE hardening of `resumeAt`'s existing guard** (tighten the reject, add nothing to the state-mover surface) — permitted. | (misapply D-S4-6 and treat S4 modules as untouchable; or freely rewrite engine internals) | The delegation explicitly flagged this: verify which boundary rule genuinely governs. See §Trace "Boundary analysis". **Flagged for spec-review** (§Open Items). |
| D-S5-P2 | **[PLAN-STAGE JUDGMENT]** `Attestation` binding shape (marker ↔ `Attestation`) | **Parallel, NO explicit binding** — the `StateMarker` (persisted-position integrity) and the `Attestation` (GATE evidence value) stay separate concerns; `verify/marker.ts` does NOT import or construct `Attestation`, and `attemptGate`'s refusal logic is untouched. | (feed a validated `StateMarker` into `Attestation` construction now) | The brief's Open Question left this open. The GATE `Attestation` is G-3.2 evidence about CI/verifier status; the `StateMarker` is engine-position integrity. Coupling them now would (a) add a second reason-to-change to `verify/marker.ts` and (b) risk touching `attemptGate`. D-S5-1=B + D-S5-5=5a both point to keeping them parallel. **Flagged for spec-review** (§Open Items). |
| D-S5-P3 | **[PLAN-STAGE JUDGMENT]** Persistence-seam module placement (where the lifecycle wiring lives) | A NEW module `pi-package/src/enginePersistence.ts` (the pi-runtime-facing seam: registers `session_start`/`session_before_compact` handlers, calls `pi.appendEntry`, mint/validate via `verify/marker.ts`, rehydrate via `Engine.resumeAt`). The pure `verify/marker.ts` imports NO pi runtime; the pure `engine/*` imports NO pi runtime (AC-PURITY preserved). The impure seam is isolated in its own module. | (put the wiring inside `engine.ts` — breaks engine purity; or inside `delegate.ts`/`enforcement.ts` — S1–S3 modules) | SRP + the S4 AC-PURITY precedent (`engine.ts` imports no pi runtime). The pi-facing I/O is a distinct responsibility. Mirrors how `delegate.ts` isolates the session-construction I/O away from `roleTable.ts`'s pure data. **Flagged for spec-review** (§Open Items). |
| D-S5-P4 | **[PLAN-STAGE JUDGMENT]** Mint-on-transition attachment point | At the **driver/caller edge**, NOT inside `Engine.step`/`attemptGate`. The persistence seam wraps engine mutation: after a successful `step`/`answerHumanQuestion`/`attemptGate` returns a new state, the seam mints a `StateMarker` for that state + its `allowedRolesFor(state)` projection and calls `pi.appendEntry`. `Engine.step`'s signature and body are UNCHANGED. | (add persistence calls inside `Engine.step`) | The brief's "Newly-surfaced risk" item 4 + D-S5-4 both require mint-on-transition be ADDITIVE at the caller edge, not by rewriting engine internals. Preserves AC-PURITY and the "only step/answer/attemptGate move the engine" invariant. **Flagged for spec-review** (§Open Items). |

## Architect

**Problem (one sentence).** Re-express `bridge.py`'s keyed-HMAC `StateMarker`
natively in TypeScript inside the pi extension (reproducing the committed golden
fixtures byte-for-byte via `node:crypto`), and wire the full signed-persistence
lifecycle (mint-on-transition → `pi.appendEntry` → validate+rehydrate on
`session_before_compact` and `session_start(resume)`), plus harden `resumeAt`'s
entry against a raw-string state — so the S4 engine's in-process position
becomes **unforgeable, restart-and-compaction-surviving evidence** rather than
volatile in-memory state.

**User.** The pi extension's engine/persistence seam (which mints on transition
and rehydrates on restart/compaction) and, transitively, the operator whose
pipeline position survives a pi restart or an auto-compaction under a signed
marker rather than being silently lost. Downstream: S8 (G-4 bus/ledger/attested
events) consumes the same `verify/marker.ts` primitive; the S8 slice's scope
correspondingly SHRINKS (it no longer owns engine-position persistence wiring —
that moved earlier into S5 per the 4b divergence; brief §Selected Approach
D-S5-4 consequence 2). **The build-order annotation recording this S5←S8 move is
a separate Tier-0 edit for the orchestrator to enact — this plan does not edit
the build-order (I cannot write it); it is named in §Open Items.**

**Measurable success criteria.**
1. `pi-package/src/verify/marker.ts` exports `StateMarker` (type),
   `mintState`, `validateState`, `loadKey`, `canonicalSigningInput`, and the
   constants (`STATE_MARKER_VERSION=1`, `FIELD_SEP="\x1f"`, `AGENT_SEP="\x1e"`,
   `DEFAULT_MAX_AGE_SECONDS=3600`), using only `node:crypto` (no npm dep).
2. A DISTINCT golden-vector cross-language test class validates
   `tests/fixtures/golden_marker.json` byte-for-byte (`validateState` → true)
   and rejects `golden_marker_tampered.json` (→ false), reusing
   `tests/fixtures/golden_key.bin` IN PLACE — modelled on
   `tests/test_sequence_gate.mjs`.
3. A ported `StateMarker` unit suite (`test_bridge.py`'s assertions) passes with
   locally-minted markers: roundtrip, forge-without-key fails, wrong-key fails,
   one-byte state-tamper fails, agent-added/widened fails, stale/future/
   wrong-version fails, malformed/missing-field/wrong-type JSON raises,
   key-load fail-closed.
4. `resumeAt` rejects a raw string that is not a `PipelineState` member — the
   D-S5-3 brand-check — with a NEW test proving raw-non-member rejected /
   genuine member accepted (the existing S4 same-valued-raw-string limitation is
   documented separately; see §Trace boundary analysis + §Open Items).
5. The signed-persistence seam (`enginePersistence.ts`) mints on transition,
   persists via `pi.appendEntry`, and on `session_start(reason:"resume")` /
   `session_before_compact` reads the persisted marker, `validateState`s it, and
   rehydrates via `Engine.resumeAt` (rejecting an invalid/forged/stale marker
   fail-closed). A persistence round-trip + rehydration-validation test passes.
6. All tests run green under `node --experimental-strip-types --test` inside
   `bin/gleipnir-sandbox --profile pi` (`--network=none`) — HMAC/key/persistence
   tests are pure/offline (fixtures + key are committed; the lifecycle-hook
   handlers are exercised against a fake/minimal `ExtensionAPI`+`ctx`, the
   `enforcement.test.ts`/`delegate.test.ts` precedent).
7. ZERO edits to the five S1–S3 modules (`roleTable/enforcement/delegate/depth/
   activeRole.ts`); ZERO change to `attemptGate` refusal logic, `TRANSITIONS`,
   or the revert budget. Edits to `state.ts`/`engine.ts` are ADDITIVE hardening
   only (the `resumeAt` guard), diffed and justified.
8. The idiom-mapping table (§Design Principles) is honoured by every surface
   choice (the review honour-check).

**Constraints.**
- **Oracle-bound** — `StateMarker` semantics frozen to `bridge.py`; only syntax
  adapts. Byte-for-byte reproduction of `golden_marker*.json` is mandatory.
- **`node:crypto` only, no new dependency** (`runtime-and-deps.md`; D-S5-2).
- **No scope-creep into S4's engine** (brief Constraint): no change to
  `attemptGate` refusal logic, `TRANSITIONS`, revert budget, or the five S1–S3
  modules. The `resumeAt` hardening is additive (D-S5-P1).
- **Engine + marker cores stay pi-runtime-free** (AC-PURITY, S4 precedent):
  `verify/marker.ts` and `engine/*` import no pi runtime; the pi-facing I/O is
  isolated in `enginePersistence.ts` (D-S5-P3).
- **`timingSafeEqual` equal-length guard preserved** (D-S5-2 sub-point;
  `sequence-gate.ts` L167: `if (got.length !== exp.length) return false` BEFORE
  the constant-time compare).
- **Per L-C36:** all file shapes + the pi lifecycle-hook surface were read
  directly this session (§Link).

## Trace

### `session_before_compact` verification (MANDATORY step — primary source)

Per the delegation and L-C36, I verified hands-on (NOT via the brief's own
summary table, which the brief flagged unconfirmed) whether the two lifecycle
hooks the 4b wiring depends on are real, documented, and expose an accessible
payload/rebind surface. **Result: CONFIRMED for both.**

| Hook / primitive | Status | Primary-source citation |
|---|---|---|
| `session_before_compact` | **CONFIRMED — first-class extension event** | `pi.dev/docs/latest/extensions` §Session Events → "session_before_compact / session_compact / session_compact_failed": `pi.on("session_before_compact", async (event, ctx) => {...})`; event carries `{ preparation, branchEntries, customInstructions, reason, willRetry, signal }`; return `{ cancel: true }` or `{ compaction: { summary, firstKeptEntryId, tokensBefore, usage?, details? } }`. Corroborated by `pi.dev/docs/latest/compaction` §"Custom Summarization via Extensions → session_before_compact", which documents `details` accepts "any JSON-serializable data". The lifecycle overview diagram shows `/compact or auto-compaction → session_before_compact → session_compact`. |
| `session_start(reason:"resume")` | **CONFIRMED — documented reason value** | `pi.dev/docs/latest/extensions` §Session Events → "session_start": `event.reason - "startup" \| "reload" \| "new" \| "resume" \| "fork"`; `event.previousSessionFile - present for "new", "resume", and "fork"`. The `session_before_switch`/lifecycle notes state: "reestablish any in-memory state in `session_start`" — the explicit rehydration surface. `/resume` path in the lifecycle diagram: `session_before_switch → session_shutdown → session_start { reason: "resume", previousSessionFile }`. |
| `pi.appendEntry(customType, data?)` (persist primitive) | **CONFIRMED** | `pi.dev/docs/latest/extensions` §ExtensionAPI Methods → `pi.appendEntry(customType, data?)`; §key-capabilities: "Session persistence — Store state that survives restarts via `pi.appendEntry()`". |
| Rehydration READ surface | **CONFIRMED** | `pi.dev/docs/latest/extensions` §ctx.sessionManager: `ctx.sessionManager.getEntries()` (all entries), `getBranch()`, `buildContextEntries()`, `getLeafId()`. This is how the seam reads back the most-recent persisted `StateMarker` entry (filter by the custom entry type, take the latest). |

**Conclusion:** the full 4b wiring is buildable as the operator converged it. No
narrowing, no `## BLOCKING` section. (Had `session_before_compact` been
unconfirmed, this plan would instead carry a `## BLOCKING — needs operator
convergence` section per the delegation; it does not.)

**One residual, flagged NOT blocking (for spec-review awareness):** the
lifecycle hooks fire inside a *live* pi session; a fully live end-to-end
compaction/resume cannot be exercised under `--network=none` (the same inherited
live-model-turn gap S2/S3 documented — `pi-package/README.md` "D6 finding"). S5
tests therefore exercise the handlers against a **fake minimal `ExtensionAPI` +
`ctx`** (the exact `enforcement.test.ts`/`delegate.test.ts` precedent: capture
the registered handler, invoke it with a synthetic event + a fake
`sessionManager` whose `getEntries()` returns a seeded marker entry). This
proves handler *wiring correctness* offline; the live-session firing is the same
class of inherited residual, not an S5 defect.

### Boundary analysis (D-S5-P1 — which rule governs touching `state.ts`/`engine.ts`)

The delegation explicitly warned not to misapply D-S4-6. The genuine picture:

- **D-S4-6's literal clause** is "ZERO edits to the five S1–S3 modules"
  (`roleTable.ts`, `enforcement.ts`, `delegate.ts`, `depth.ts`,
  `activeRole.ts`) — confirmed by reading `pi-dev-replatform-s4.md` D-S4-6 (row)
  + AC-NOTOUCH. `state.ts` and `engine.ts` are **NOT** in that five; they are
  **S4-built engine modules**. So D-S4-6's literal untouchability does **not**
  govern them.
- **The rule that genuinely governs** is the S5 brief's Constraint: *"No
  scope-creep into S4's engine. S5 must not alter `attemptGate`'s refusal logic,
  `TRANSITIONS`, the revert budget, or the five S1–S3 modules."* Touching an S4
  engine module is permitted **iff** the change is ADDITIVE and does not alter
  those named behaviours.
- **The `resumeAt` brand-check IS additive-compatible.** `state.ts` already
  ships `isPipelineState` (L85–87) and `engine.ts`'s `resumeAt` already calls it
  (L130–132) and throws `InvalidVerdict` on a non-member. The S4 code's OWN
  header (state.ts L66–84) documents the KNOWN limitation: because the
  const-object-enum idiom makes states plain runtime strings, `isPipelineState`
  cannot reject a *same-valued* raw string (only genuinely-non-member values).
  **The D-S5-3 hardening tightens exactly this**: introduce a runtime brand so a
  raw string (even a same-valued one) supplied at `resumeAt` entry is rejected,
  mirroring Python's `isinstance(state, PipelineState)`. This ADDS a reject
  path; it removes no accept path for genuine engine-minted state, and it does
  NOT touch `attemptGate`/`TRANSITIONS`/budget. **Therefore permitted under the
  governing rule** — recorded as D-S5-P1, flagged for spec-review.

**Brand mechanism (the hardening's concrete shape, D-S5-3).** The engine must be
able to hand `resumeAt` a value that IS branded (so genuine rehydration still
works) while a raw external string is not. Options the code stage will choose
between (surface choice, idiom-table row): (a) a `brandState(value):
BrandedPipelineState` factory returning a boxed/tagged object the engine holds
and `resumeAt` accepts, rejecting bare strings; or (b) `resumeAt` accepts only a
value obtained from a `PipelineState`-producing function guarded by a private
`Symbol` tag. Both reproduce Python's "a bare `str` is not a `PipelineState`
member" refusal. This is a genuine surface choice → idiom-table row 8, flagged.
(The persistence seam rehydrates from a *validated* `StateMarker.pipeline_state`
string; the seam is where the raw string is converted to a branded state via the
factory — so the brand-check protects the seam entry, exactly the coupling the
brief's D-S5-3 rationale names.)

### Artifacts and where they live (source of truth)

Behaviour source of truth is the Python oracle (cited per module); the proven TS
reference (`sequence-gate.ts`) is the byte-parity precedent; TS surface idiom
source of truth is the idiom-mapping table (§Design Principles) + existing
pi-package modules.

| TS artifact | Status | Ports / derives from | Responsibility (SRP) |
|---|---|---|---|
| `pi-package/src/verify/marker.ts` | **NEW** | `bridge.py` L54–192 (`StateMarker`, `mint_state`, `validate_state`, `_canonical_signing_input`) + `verify/marker.py` L86–106 (`load_key`) + proven `sequence-gate.ts` L103–174 (`validateMarker`/`canonicalSigningInput`/`loadKey`) | The HMAC `StateMarker` primitive: type, mint/validate, key-load, canonical signing input. Pi-runtime-free. One reason to change: the marker crypto construction. |
| `pi-package/src/enginePersistence.ts` | **NEW** | pi lifecycle docs (§Link) + `bridge.py`'s mint-on-write intent + S4 `Engine.resumeAt` | The pi-facing persistence seam: register `session_start`/`session_before_compact` handlers; mint-on-transition; `pi.appendEntry`; read-back + `validateState` + `Engine.resumeAt` rehydration (fail-closed). One reason to change: the persistence/lifecycle wiring. |
| `pi-package/src/engine/state.ts` | **EDIT (additive)** | — | ADD the `PipelineState` brand + `brandState` factory backing the `resumeAt` hardening (D-S5-3/D-S5-P1). No change to the state vocabulary/order/budget. |
| `pi-package/src/engine/engine.ts` | **EDIT (additive)** | `__init__.py` `resume_at` `isinstance` refusal | TIGHTEN `resumeAt` to require a branded state (reject raw strings). No change to `step`/`answerHumanQuestion`/`attemptGate` bodies or signatures, `TRANSITIONS`, or budget. |
| `pi-package/test/marker.test.ts` | **NEW** | `tests/test_bridge.py` (unit) + `tests/test_sequence_gate.mjs` (golden, DISTINCT class) | The `StateMarker` unit suite + the DISTINCT golden-vector cross-language class (D-S5-6=6a). |
| `pi-package/test/enginePersistence.test.ts` | **NEW** | (new; seam tests) + S4 `test/engine.test.ts` resumeAt case | Persistence round-trip (mint→appendEntry→read→validate→resumeAt), rehydration-validation (forged/stale/tampered marker rejected fail-closed), and the `resumeAt` brand-check rejection. |

**Fixture reuse (D-S5-6):** reuse `tests/fixtures/golden_marker.json`,
`golden_marker_tampered.json`, and `golden_key.bin` **IN PLACE** via a relative
path from `pi-package/test/` (exactly as `tests/test_sequence_gate.mjs`
resolves `../.gleipnir/plugins/...` and `fixtures/...` — here the relative path
is `../../tests/fixtures/`). Single source of truth; NO copy that could drift.
The plan pins the exact relative path in §Open Items for the test author to
confirm at collection.

### Integrations map

- **`verify/marker.ts` → standalone + `node:crypto` only.** Imports
  `createHmac`, `timingSafeEqual` from `node:crypto`; `readFileSync` from
  `node:fs` (for `loadKey`, mirroring `sequence-gate.ts` L54). NO import of any
  `engine/*` module, NO pi runtime. (It may import `PipelineState`'s *type* for
  a typed `pipeline_state` field, compile-time only — but treats the value as a
  plain string on the wire, exactly as `bridge.py` stores `pipeline_state: str`.)
- **`enginePersistence.ts` → `verify/marker.ts` + `engine/*` + pi runtime.** The
  ONLY module that imports BOTH the pure crypto primitive AND the pi
  `ExtensionAPI`/`ctx` surface. Imports `mintState`/`validateState`/`loadKey`
  from `verify/marker.ts`; `Engine`/`PipelineState`/`brandState`/`resumeAt` from
  `engine/*`; `allowedRolesFor` from `engine/allowTable.ts` (to build the
  marker's `allowed_agents` projection — mirroring `bridge.py`'s docstring: the
  marker re-emits the current-state→allowed-role projection). Registers
  `pi.on("session_start", …)` and `pi.on("session_before_compact", …)`; calls
  `pi.appendEntry(STATE_MARKER_ENTRY_TYPE, marker)`; reads
  `ctx.sessionManager.getEntries()` and selects the latest marker entry.
- **`engine/state.ts` + `engine/engine.ts` → additive edit ONLY.** The brand +
  the tightened `resumeAt`. No new state-mover; the brand factory is not a
  public state setter. `_setStateForTestOnly` (S4) is unchanged.
- **NO integration** with `roleTable.ts`/`enforcement.ts`/`delegate.ts`/
  `depth.ts`/`activeRole.ts` (the five S1–S3 modules — AC-NOTOUCH carries into
  S5). NO change to `engine/attestation.ts` (D-S5-P2: marker and `Attestation`
  stay parallel). NO change to `engine/transitions.ts`/`allowTable.ts`/
  `judges.ts`/`router.ts` (read-only imports at most).

### Edge cases (pinned by the oracle + the proven reference — the exhaustive list the port must re-earn)

**`StateMarker` byte-parity (golden, from `sequence-gate.ts` + fixtures):**
- Genuine Python-minted `golden_marker.json` validates true under
  `golden_key.bin` (`minted_at=1000`, use `now` in-window, `maxAgeSeconds`
  large — mirror `test_sequence_gate.mjs` L26–31: `NOW=1001`, `HUGE=1e12`).
- `golden_marker_tampered.json` (state flipped `plan`→`git`, MAC reused) → false.
- Genuine marker under the wrong key → false.
- Stale marker (now far past max age) → false; future-dated (now before
  `minted_at`) → false.

**`StateMarker` logic (unit, from `test_bridge.py`):**
- `mintState(...)` then `validateState(...)` → true (roundtrip).
- Roundtrip through JSON (`to_json`/`from_json` analogue) preserves + validates.
- `allowed_agents` wire-order does not affect validity (sorted before signing).
- Agent-fabricated marker (bogus MAC) → false.
- Minted with wrong key → false under the right key.
- One-byte `pipeline_state` tamper (MAC reused) → false.
- One-byte `allowed_agents` tamper / added agent (MAC reused) → false.
- `version != 1` → false.
- Malformed JSON / missing fields / wrong types → raises `StateMarkerError`
  (the TS `from_json` analogue throws; `test_bridge.py` L153–175).
- `loadKey` fail-closed: no path / empty file / unreadable → throws
  `KeyUnavailable` analogue (mirrors `verify/marker.py` L86–106 +
  `sequence-gate.ts` L120–127).

**`resumeAt` brand-check (D-S5-3, NEW):**
- `resumeAt(id, brandState("spec_review"))` (a branded genuine state) → succeeds.
- `resumeAt(id, "spec_review")` (a RAW same-valued string) → throws
  (`InvalidVerdict`), reproducing Python's `isinstance` refusal — the exact
  weakening the S4 header (state.ts L66–84) flagged as deferred to S5.
- `resumeAt(id, "not_a_state")` (non-member string) → still throws (already
  works in S4; the hardening must not regress it).

**Signed-persistence lifecycle (4b, NEW):**
- **Mint-on-transition:** after a successful engine transition, the seam mints a
  `StateMarker{version:1, pipeline_state: <new state>, allowed_agents:
  allowedRolesFor(newState) sorted, minted_at: now, mac}` and calls
  `pi.appendEntry`. The minted marker validates true (round-trip).
- **`session_start(reason:"resume")`:** the seam reads the latest persisted
  marker entry, `validateState`s it under the key; if valid+fresh →
  `Engine.resumeAt(id, brandState(marker.pipeline_state))` rehydrates at that
  state; if invalid/forged/stale/wrong-key/missing → fail-closed (do NOT
  rehydrate to an attacker-chosen state; the seam either refuses to rehydrate or
  raises — the test pins the fail-closed choice).
- **`session_start(reason ∈ {"startup","new","fork"})`:** no rehydration from a
  prior marker (a fresh/new/forked session does not inherit a resumed position);
  only `"resume"` (and the compaction path) rehydrate. (Pinned so the handler
  does not over-fire.)
- **`session_before_compact`:** the seam ensures the current engine position is
  persisted (mint + `appendEntry`) BEFORE compaction discards volatile context,
  and returns without cancelling compaction (`return undefined` / no `{cancel}`).
  On the *rebuild* side, position is recovered from the persisted marker (same
  read+validate+resumeAt path as resume). Test: a compaction event handler
  invocation persists a valid marker; a subsequent read+validate+resumeAt
  recovers the exact pre-compaction state.
- **Tamper across the seam:** a persisted marker whose `pipeline_state` is
  altered after minting (MAC unchanged) is rejected on read-back (fail-closed) —
  the seam does NOT rehydrate to the tampered state. (This is the whole point of
  signing the persisted position.)

## Link (what was validated before building)

Validated directly this session (read in full / fetched from primary source —
L-C36):
- **Python oracle read in full:** `src/gleipnir/engine/bridge.py` (192 L —
  `StateMarker`, `mint_state`, `validate_state`, `_canonical_signing_input`,
  `to_json`/`from_json`, the `verify/marker.py` reuse of `load_key`/`DIGEST`/
  `KeyUnavailable`); `src/gleipnir/verify/marker.py` (222 L — `load_key`
  fail-closed, `DIGEST=sha256`, `DEFAULT_MAX_AGE_SECONDS=3600`, `MarkerError`/
  `KeyUnavailable`; the tree-hash `Marker` DEFERRED per D-S5-1).
- **Oracle test read in full:** `tests/test_bridge.py` (182 L — the unit oracle
  for the ported suite: happy path, tamper/forgery, freshness/version, malformed
  input, key-reuse assertion).
- **Proven TS reference read in full:** `.gleipnir/plugins/sequence-gate.ts`
  (229 L — `validateMarker`/`canonicalSigningInput`/`loadKey`, `node:crypto`
  `createHmac`+`timingSafeEqual` with the equal-length guard L167) and
  `tests/test_sequence_gate.mjs` (212 L — the golden-vector class template:
  validates `golden_marker.json`, rejects tampered/wrong-key/stale/future,
  `NOW`/`HUGE` freshness override, fixture-reuse-in-place pattern).
- **Golden fixtures read directly:** `tests/fixtures/golden_marker.json`
  (`{"allowed_agents":["gleipnir-plan"],"mac":"2707c101…","minted_at":1000,
  "pipeline_state":"plan","version":1}`) and `golden_marker_tampered.json`
  (identical but `pipeline_state":"git"`, same MAC). Confirms the fixtures are
  `StateMarker` vectors (D-S5-1 ASSUMPTION-3 grounding).
- **S4 modules S5 attaches to, read in full:** `pi-package/src/engine/state.ts`
  (87 L — `PipelineState` const-object + `isPipelineState` + the documented
  same-valued-raw-string limitation the D-S5-3 hardening closes),
  `pi-package/src/engine/engine.ts` (283 L — `resumeAt` L129–136 calls
  `isPipelineState`; `attemptGate` refusal logic L219–253 which S5 must NOT
  touch; `_setStateForTestOnly`), `pi-package/src/engine/attestation.ts` (63 L —
  the VALUE contract whose header says "S5 extends it with real HMAC marker
  verification — VALUE/CONTRACT only here"; D-S5-P2 keeps marker and
  `Attestation` parallel).
- **pi test-harness + extension idiom read:** `pi-package/package.json` (test
  script `node --experimental-strip-types --test test/*.test.ts`; peer deps
  include `@earendil-works/pi-coding-agent`), `pi-package/.pi/settings.json`
  (`extensions: [enforcement.ts, delegate.ts]` — where a new persistence
  extension would register), `pi-package/src/delegate.ts` (the
  `ExtensionAPI`-facing seam precedent: import types from
  `@earendil-works/pi-coding-agent`, isolate pi I/O away from pure data),
  `pi-package/src/enforcement.ts` refs (registers `pi.on("session_start", …)` —
  the exact handler-registration idiom the persistence seam reuses; tested via
  AC-15 by capturing the registered handler and invoking it with a synthetic
  event — the offline-handler-test precedent).
- **pi lifecycle-hook surface CONFIRMED from primary source** (§Trace table):
  `pi.dev/docs/latest/extensions` (fetched: `session_start` reasons incl.
  `"resume"`; `session_before_compact` event+return contract;
  `pi.appendEntry(customType, data?)`; `ctx.sessionManager.getEntries()`) and
  `pi.dev/docs/latest/compaction` (fetched: `session_before_compact`
  `details`=JSON-serializable, `branchEntries`, cancel/custom-summary return).

## Assemble (intended build order)

**Discipline (L-C30): interface stub BEFORE tests, real bodies AFTER tests.**
The pi harness collects at import time, so a test importing a not-yet-existing
module fails at collection. Each new module lands as a typed interface stub
first (real exported signatures, bodies `throw new Error("not implemented")`),
so `test/*.test.ts` imports resolve at collection; then tests (Red); then real
bodies (Green). The additive `state.ts`/`engine.ts` edits are small tightenings,
applied in the real-body phase alongside their tests.

Order:

1. **Marker primitive interface stub.**
   - **1a `verify/marker.ts` stub** — export the `StateMarker` type, the
     constants (`STATE_MARKER_VERSION`, `FIELD_SEP`, `AGENT_SEP`,
     `DEFAULT_MAX_AGE_SECONDS`, `DIGEST="sha256"`), and the signatures
     `mintState`, `validateState`, `loadKey`, `canonicalSigningInput`,
     `stateMarkerFromJson` (bodies throw). Makes `marker.test.ts` import resolve.

2. **State brand + persistence-seam interface stubs.**
   - **2a `engine/state.ts`** — ADD `brandState(value): PipelineState`
     factory + the private brand (real, small — it is data/guard, not a
     throwing stub). Export it. Do NOT alter existing exports.
   - **2b `enginePersistence.ts` stub** — export the seam entrypoint (an
     `ExtensionAPI` default-export factory registering the two handlers) + the
     helper signatures (`mintForState`, `persist`, `readLatestMarker`,
     `rehydrateFromMarker`) with stub bodies + the `STATE_MARKER_ENTRY_TYPE`
     constant. Makes `enginePersistence.test.ts` import resolve.

3. **Author the tests (Red — test stage arbiter).**
   - **3a `test/marker.test.ts`** —
     (i) the ported `StateMarker` **unit suite** (`test_bridge.py` assertions,
     `node:test` idiom, locally-minted markers); and
     (ii) the DISTINCT **golden-vector cross-language class** (a clearly-labelled
     separate `describe`/block) reusing `../../tests/fixtures/golden_marker*.json`
     + `golden_key.bin` in place, modelled on `test_sequence_gate.mjs`
     (validate genuine true, reject tampered/wrong-key/stale/future false).
   - **3b `test/enginePersistence.test.ts`** — the `resumeAt` brand-check
     rejection (raw string throws, branded state succeeds); mint-on-transition
     round-trip; `session_start(resume)` rehydration-validation (valid → resume;
     forged/stale/tampered/missing → fail-closed); `session_before_compact`
     persist-then-recover; `session_start(startup/new/fork)` does NOT rehydrate.
     Handlers exercised against a fake minimal `ExtensionAPI`+`ctx` whose
     `sessionManager.getEntries()` returns seeded entries (the AC-15 precedent).

4. **Real bodies + additive edits (Green — code stage), bounded by the tests.**
   - **4a `verify/marker.ts`** — implement against `bridge.py`:
     `canonicalSigningInput` = `[String(version), pipeline_state,
     sorted(allowed_agents).join("\x1e"), String(minted_at)].join("\x1f")`
     (byte-identical to `sequence-gate.ts` L113–118 + `bridge.py` L128–130);
     `mintState` = `createHmac("sha256", key).update(input,"utf8").digest("hex")`
     over the sorted-agents tuple; `validateState` = version check →
     recompute+`timingSafeEqual` **with the equal-length guard first** →
     freshness (`age<0 || age>max` → false); `loadKey` = read+trim, empty/absent
     fail-closed; `stateMarkerFromJson` = shape-validate, throw on
     malformed/missing/wrong-type (the `from_json` analogue).
   - **4b `engine/engine.ts` (additive)** — tighten `resumeAt` to require a
     branded state (reject a raw string via the brand from 2a), preserving the
     existing non-member rejection. NO other change; `attemptGate`/`step`/
     `TRANSITIONS`/budget byte-unchanged.
   - **4c `enginePersistence.ts`** — implement the handlers: mint-on-transition
     via `mintState` + `allowedRolesFor(state)` projection + `pi.appendEntry`;
     `session_start` handler routes on `event.reason` (resume/compaction-rebuild
     → read latest marker via `ctx.sessionManager.getEntries()`, `validateState`,
     `Engine.resumeAt(id, brandState(marker.pipeline_state))`; else no-op);
     `session_before_compact` handler persists current position then returns
     without cancelling. All uncertainty fail-closed (invalid marker → do not
     rehydrate).

5. **Wire the extension (additive).** Add `./src/enginePersistence.ts` to
   `pi-package/package.json`'s `pi.extensions` array and `.pi/settings.json`'s
   `extensions` array — **[SCOPE FLAG]** these two files are declarative config,
   NOT in the five S1–S3 modules, but they ARE enforcement-adjacent wiring
   (`package.json`/`settings.json` govern which extensions load). Per the
   stage-role-map Axis-2 rules, editing them is enforcement-bearing config → the
   hardened review path already applies to this whole plan (it touches
   `src/**`). The test author/code stage adds these two lines additively; the
   blast-radius pass verifies no OTHER extension entry or grant changed.
   (Whether the persistence extension should be armed default-off like
   `sequence-gate.ts` is a §Open Items question for spec-review.)

**Step order rationale.** Marker primitive first (everything depends on
`mintState`/`validateState`); the state brand before the seam (the seam
rehydrates through `brandState`); stubs before tests (collection-time import
resolution, L-C30); tests before real bodies (test-first, the test is the
arbiter); extension wiring last (it consumes the finished seam).

## Stress-test (acceptance checks)

### Marker unit suite (`test/marker.test.ts` unit block ← `tests/test_bridge.py`)

| Python test (ported, adapted name) | Asserts |
|---|---|
| `test_genuine_marker_validates` | `mintState`→`validateState` true. |
| `test_marker_roundtrips_through_json` | JSON round-trip preserves + validates. |
| `test_allowed_agents_order_does_not_affect_validity` | wire order irrelevant (sorted before signing). |
| `test_agent_fabricated_marker_fails` | bogus MAC → false. |
| `test_agent_mints_with_wrong_key_fails` | wrong-key mint → false under right key. |
| `test_one_byte_state_tamper_invalidates` | state flipped, MAC reused → false. |
| `test_one_byte_allowed_agents_tamper_invalidates` / `test_added_allowed_agent_invalidates` | agent set mutated/widened, MAC reused → false. |
| `test_stale_marker_fails` / `test_future_marker_fails` | freshness both directions → false. |
| `test_wrong_version_fails` | `version!=1` → false. |
| `test_malformed_marker_json_raises` / `test_marker_missing_fields_raises` / `test_marker_wrong_types_raises` | `from_json` analogue throws `StateMarkerError`. |
| `test_key_unavailable_*` | `loadKey` fail-closed (no path/empty/unreadable) throws. |

### Golden-vector cross-language class (`test/marker.test.ts` DISTINCT golden block ← `tests/test_sequence_gate.mjs`)

- **AC-GOLDEN-1:** `validateState(golden_marker, key, {maxAgeSeconds:HUGE,
  now:1001})` === true (byte-for-byte MAC contract vs Python-minted fixture).
- **AC-GOLDEN-2:** `validateState(golden_marker_tampered, …)` === false.
- **AC-GOLDEN-3:** genuine marker under a wrong key === false.
- **AC-GOLDEN-4:** stale (now ≫ minted_at+maxAge) === false; future
  (now < minted_at) === false.
- **AC-GOLDEN-REUSE:** the fixtures are read from `../../tests/fixtures/` IN
  PLACE (no copy under `pi-package/test/fixtures/`); a `git diff --name-only`
  shows no new fixture copy.

### Persistence + brand-check (`test/enginePersistence.test.ts`)

- **AC-BRAND-1:** `resumeAt(id, brandState("spec_review"))` succeeds; state is
  `spec_review`.
- **AC-BRAND-2:** `resumeAt(id, "spec_review")` (raw string) throws
  `InvalidVerdict` (the D-S5-3 hardening; the S4 same-valued-raw-string
  limitation is now closed).
- **AC-BRAND-3:** `resumeAt(id, "not_a_state")` still throws (no regression).
- **AC-PERSIST-1 (mint-on-transition round-trip):** after a transition the seam
  mints + persists a marker for the new state whose `allowed_agents` ===
  `allowedRolesFor(newState)` sorted, and `validateState` on it === true.
- **AC-PERSIST-2 (resume rehydration, valid):** `session_start(reason:"resume")`
  with a seeded valid marker → engine rehydrated at `marker.pipeline_state`.
- **AC-PERSIST-3 (resume, fail-closed):** a seeded forged / stale / tampered /
  wrong-key / missing marker → the seam does NOT rehydrate to the marker's state
  (fail-closed; the test pins refuse-or-raise).
- **AC-PERSIST-4 (compaction survival):** the `session_before_compact` handler
  persists the current position (and does not cancel compaction); a subsequent
  read+validate+resumeAt recovers the exact pre-compaction state.
- **AC-PERSIST-5 (no over-fire):** `session_start(reason ∈
  {"startup","new","fork"})` does NOT rehydrate from a prior marker.

### Cross-cutting ACs

- **AC-ROUTE:** `bin/gleipnir-sandbox --profile pi` runs
  `node --experimental-strip-types --test test/marker.test.ts test/enginePersistence.test.ts`
  green under `--network=none`.
- **AC-NOTOUCH:** `git diff --name-only` shows ZERO changes to
  `roleTable.ts`, `enforcement.ts`, `delegate.ts`, `depth.ts`, `activeRole.ts`,
  and ZERO change to `engine/attestation.ts`, `engine/transitions.ts`,
  `engine/allowTable.ts`, `engine/judges.ts`, `engine/router.ts`. Edits are
  confined to NEW files + additive `engine/state.ts`/`engine/engine.ts` + the
  two extension-registration lines (package.json/.pi/settings.json).
- **AC-ADDITIVE:** the `engine/engine.ts` diff shows ONLY the `resumeAt`
  tightening (no change to `step`/`answerHumanQuestion`/`attemptGate` bodies or
  signatures, `TRANSITIONS`, or the revert budget). The over-broad form checked-
  and-ruled-out: "the persistence work quietly changed `attemptGate` refusal
  logic or widened the state-mover surface."
- **AC-PURITY:** `verify/marker.ts` imports only `node:crypto`/`node:fs` (no pi
  runtime, no `engine/*` value import); `engine/*` imports no pi runtime. Only
  `enginePersistence.ts` imports the pi `ExtensionAPI`/`ctx` surface. (grep the
  import blocks.)
- **AC-NODEP:** no new entry in `pi-package/package.json` `dependencies`/
  `peerDependencies` for HMAC (D-S5-2; `node:crypto` only).
- **AC-IDIOM:** every surface deviation from the Python oracle is a row in the
  idiom table (§Design Principles) — the honour-check rejects any un-tabled
  surface choice.

## Execution Workflow

For the implementing agents (test stage + code stage, both `gleipnir-code`):

1. **Read this plan + the cited oracle/reference lines** (`bridge.py` L54–192,
   `verify/marker.py` L86–106, `test_bridge.py`, `sequence-gate.ts` L103–174,
   `test_sequence_gate.mjs`, the golden fixtures). Do NOT re-derive the MAC
   construction from prose — the byte contract is `sequence-gate.ts`'s
   `canonicalSigningInput` (already proven against the fixtures).
2. **Build in the Assemble order.** Marker stub (1) → state brand + seam stub
   (2) → author tests (3, Red) → real bodies + additive edits (4, Green) →
   extension wiring (5).
3. **Test-first is enforced by the pipeline.** The `test` stage authors both
   test files against the stubs (must collect clean); the `code` stage makes
   them green. The test is the arbiter (Axiom 1); do not "improve" the MAC
   semantics beyond what the ported assertion + golden fixtures pin.
4. **Byte-parity is non-negotiable.** If a golden-vector assertion fails, the
   canonical signing input diverged from `bridge.py`/`sequence-gate.ts` — fix
   the TS to match the Python bytes, never adjust the fixture.
5. **Additive-only into S4.** If you change `attemptGate`/`step`/`TRANSITIONS`/
   the budget, or touch any of the five S1–S3 modules or `attestation.ts`, STOP
   — that is a boundary violation (D-S5-P1 governing rule); the change belongs
   in a NEW file or is out of scope.
6. **Fail-closed everywhere.** Any uncertainty in `validateState` returns false;
   any uncertainty in the rehydration seam does NOT rehydrate to the marker's
   state (mirrors `sequence-gate.ts`'s fail-closed posture + `verify/marker.py`
   L187–198). A signed-but-unvalidated rehydration path is the exact hole D-S5-3
   closes — never open it.
7. **Marker and `Attestation` stay parallel** (D-S5-P2): `verify/marker.ts` does
   not import or construct `engine/attestation.ts`'s `Attestation`.
8. **Verdicts:** hardened path (this plan touches `src/**`) → two separate
   review passes (spec-conformance + blast-radius) + negative-check attestation
   (§Pipeline Routing).

## Pipeline Routing

**Full 8-stage HARDENED pipeline.** Touched-path set `P` =
`pi-package/src/verify/marker.ts`, `pi-package/src/enginePersistence.ts`,
`pi-package/src/engine/state.ts`, `pi-package/src/engine/engine.ts`,
`pi-package/test/marker.test.ts`, `pi-package/test/enginePersistence.test.ts`,
plus additive edits to `pi-package/package.json` + `pi-package/.pi/settings.json`.

- **Axis-1 (`X`) disqualifier hit:** `P` contains `pi-package/src/**` and
  `pi-package/test/**` — **executable TypeScript with class/function/module
  structure** (`**/*.ts`). → NOT the prose/config light track; the **full
  8-stage pipeline** (`brainstorm → plan → spec-review → test → code → quality →
  git → gate`), test arbiter present. (Same routing as the S4 plan.)
- **Gate-1 case:** **(i) OOP/functional code** — full SOLID+DRY+SRP+Design
  Intent required (§Design Principles), each falsifiable.
- **Axis-2(a) `E`-set touch: NONE of the always-hardened enforcement PATHS.**
  No file in `P` is under `.gleipnir/agents/**`, `.gleipnir/plugins/**`,
  `.gleipnir/sandbox/**`, `.gleipnir/policy/**`, `.gleipnir/keys/**`, nor is it
  `stage-role-map.md`, `opencode.jsonc`/`**/opencode.json`, nor an enumerated
  repo-root file. **Note `pi-package/package.json` and `pi-package/.pi/
  settings.json`:** these are NOT the repo-root `pyproject.toml`/`opencode.json`
  in the `E` set; they are the pi-package's own manifest/settings. They ARE
  enforcement-adjacent (they select which extensions load), so the code stage's
  edit to them is treated as enforcement-bearing config and the blast-radius
  pass verifies the diff adds ONLY the persistence-extension registration line
  and changes no other extension entry, permission, or grant. Because `P`
  already routes hardened via Axis-1 (`src/**`), no separate light/hardened
  determination is needed — the whole plan is hardened.
- **Hardened obligations (discharged at spec-review/quality/git, not by me):**
  the test arbiter (golden + unit + persistence ACs) + the SOLID/DRY dimension
  of the blast-radius pass + the honour-check (does the applied code honour the
  idiom-table Design Intent?). The specific negative-checks the blast-radius pass
  must run: **AC-NOTOUCH** + **AC-ADDITIVE** (the over-broad form "the
  persistence/marker work quietly changed `attemptGate` refusal logic, widened a
  grant, or altered another extension's registration" checked-and-ruled-out) and
  **AC-PURITY** (the marker/engine cores did not acquire a pi-runtime import).

## Design Principles (Gate 1 — case (i): OOP/functional code)

### Design Intent (falsifiable — the idiom-mapping table + the boundary are the anchors)

**The falsifiable Design Intent of this slice is: (1) `verify/marker.ts` is a
STRUCTURAL 1:1 port of `bridge.py`'s `StateMarker` construction whose canonical
signing input is BYTE-IDENTICAL to the proven `sequence-gate.ts`
`canonicalSigningInput` (so it validates the committed golden fixtures
byte-for-byte), its ONLY deviations from the Python source being the surface
transformations enumerated in the idiom-mapping table; and (2) the two SRP
boundaries below are honoured exactly.**

Two named, specific SRP boundaries a reviewer can point to a violation of:

- **Boundary A — `verify/marker.ts` (crypto primitive) vs `engine/attestation.ts`
  (attestation VALUE contract).** `verify/marker.ts` owns the HMAC `StateMarker`
  construction and NOTHING about the GATE `Attestation` value; `attestation.ts`
  owns the `Attestation` VALUE contract and NOTHING about HMAC/keys. **Falsifier:**
  `verify/marker.ts` imports or constructs `Attestation`, or `attestation.ts`
  gains an HMAC/`node:crypto`/key-loading line. (This is the SRP `attestation.ts`
  explicitly documents — its "one reason to change: the attestation shape" —
  and why D-S5-5=5a + D-S5-P2 keep them parallel.)
- **Boundary B — marker-minting (`verify/marker.ts`, pure crypto) vs
  lifecycle-hook wiring (`enginePersistence.ts`, pi-facing I/O).**
  `verify/marker.ts` computes/validates a marker from explicit arguments and
  imports NO pi runtime; `enginePersistence.ts` owns ALL contact with the pi
  `ExtensionAPI`/`ctx` (`pi.on`, `pi.appendEntry`, `ctx.sessionManager`) and the
  lifecycle-event routing, and holds NO HMAC construction of its own (it calls
  `mintState`/`validateState`). **Falsifier:** `verify/marker.ts` imports
  `@earendil-works/pi-*` or reads `ctx.sessionManager`; or
  `enginePersistence.ts` inlines a `createHmac`/signing-input construction
  instead of calling `verify/marker.ts`.

Both are falsifiable exactly as the anti-vacuity rule requires: a reviewer can
point to a concrete import/line that violates the boundary. (Further concrete
falsifiers: a marker MAC that does not match the golden fixture; a
`validateState` missing the `timingSafeEqual` equal-length guard; a `resumeAt`
that accepts a raw same-valued string; a rehydration path that resumes to an
unvalidated marker's state; a change to `attemptGate` refusal logic; an npm HMAC
dependency added.)

**Note on the S4 `resumeAt` same-valued-raw-string limitation (idiom-table
row 8 — L-C14 phantom-gap discipline).** S4 tabled+acknowledged that
`resumeAt(id, "spec_review")` (raw string) SUCCEEDS where Python RAISES, with
hardening deferred to S5 (durable ack: `decisions/pi-replatform-open-q1.md`; S4
idiom-table row 15). **This S5 plan CLOSES that deferred item** via the D-S5-3
brand-check (AC-BRAND-2). A reviewer must NOT re-flag the S4 acceptance as a
fresh violation *and* must confirm S5 actually closes it (AC-BRAND-2 is the
proof). This is the tabled resolution of a known, surfaced gap — not a new one.

**Idiom-mapping table (Python `bridge.py`/`verify/marker.py` → TS surface — every deviation named):**

| # | Python surface | TS surface | Rationale |
|---|---|---|---|
| 1 | `@dataclass(frozen=True) class StateMarker` (`version, pipeline_state, allowed_agents: tuple, minted_at, mac`) | `interface StateMarker { version: number; pipeline_state: string; allowed_agents: string[]; minted_at: number; mac: string }` (matches the proven `sequence-gate.ts` L103–109 shape exactly) | The wire/JSON shape must match the fixtures byte-for-byte; `sequence-gate.ts` already pins this interface and validates the fixtures. Plain interface (no brand needed — it is a wire value, not a security-load-bearing runtime tag like `Attestation`). |
| 2 | `_canonical_signing_input`: `"\x1f".join([str(version), pipeline_state, "\x1e".join(sorted(agents)), str(minted_at)])`, UTF-8 | `[String(version), pipeline_state, [...allowed_agents].sort().join("\x1e"), String(minted_at)].join("\x1f")` (byte-identical to `sequence-gate.ts` L113–118) | The MAC covers these exact bytes; any deviation breaks golden byte-parity. Constants `FIELD_SEP="\x1f"`, `AGENT_SEP="\x1e"`. |
| 3 | `hmac.new(key, input, sha256).hexdigest()` | `createHmac("sha256", key).update(input, "utf8").digest("hex")` | `node:crypto` stdlib-equivalent (D-S5-2); matches `sequence-gate.ts` L164. |
| 4 | `hmac.compare_digest(mac, expected)` (constant-time) | `timingSafeEqual(Buffer.from(mac,"utf8"), Buffer.from(expected,"utf8"))` **with `if (got.length !== exp.length) return false` FIRST** | `timingSafeEqual` throws on unequal lengths; the equal-length guard (sequence-gate.ts L167) preserves constant-time semantics + fail-closed (D-S5-2 sub-point). |
| 5 | `load_key(path)`: read bytes, `.strip()`, empty/absent → `KeyUnavailable` | `loadKey()`: `readFileSync(path)`, `.toString("utf8").trim()`, empty/absent → throw (a `KeyUnavailable`-named TS `Error` subclass) | Fail-closed key load; matches `sequence-gate.ts` L120–127 + `verify/marker.py` L86–106. |
| 6 | `mac` compared as hex string; `DIGEST="sha256"`; `DEFAULT_MAX_AGE_SECONDS=3600`; `STATE_MARKER_VERSION=1` | same values as named `const`s | Named constants (DRY), values frozen to the oracle. |
| 7 | `StateMarker.from_json` / `to_json` (JSON round-trip, shape-validate, `StateMarkerError` on bad input) | `stateMarkerFromJson(text): StateMarker` (JSON.parse + shape guard, throw a `StateMarkerError`-named error) / `JSON.stringify` for `to_json` | The malformed/missing/wrong-type refusals (`test_bridge.py` L153–175) map to a thrown TS error; mirrors `sequence-gate.ts`'s `readMarker` shape-guard (L143–154). |
| 8 | `Engine.resume_at` type-rejects a non-`PipelineState` via `isinstance` — a same-valued plain `str` RAISES | `resumeAt` requires a **branded** `PipelineState` from `brandState(...)`; a raw string (even same-valued) throws `InvalidVerdict` | Closes the S4-deferred limitation (state.ts L66–84 / S4 idiom row 15) — the D-S5-3 hardening. The brand is the TS analogue of Python's distinct `str,Enum` runtime type. (Concrete brand mechanism — boxed tag vs private `Symbol` — is the code stage's surface choice within this row.) |
| 9 | `bridge.py` mints on write; the marker re-emits the state→allowed-role projection (`allowed_agents`) | `enginePersistence.ts` mints on transition at the caller edge, building `allowed_agents` from `allowedRolesFor(state)` sorted | Additive mint-on-transition (D-S5-P4); the projection source is the S4 `allowTable.ts`, not a hand-copied list (DRY). |
| 10 | (Python has no pi lifecycle; the TS side is net-new integration) | `pi.on("session_start", …)` + `pi.on("session_before_compact", …)` + `pi.appendEntry(STATE_MARKER_ENTRY_TYPE, marker)` + `ctx.sessionManager.getEntries()` | The 4b lifecycle wiring, confirmed against pi primary source (§Trace). Net-new (no Python analogue) — documented as an integration, not a port deviation. |

### SOLID analysis (evaluated against the proposed design)

- **Single Responsibility.** `verify/marker.ts` = the HMAC `StateMarker` crypto
  construction (one reason to change: the marker crypto). `enginePersistence.ts`
  = the pi-facing persistence/lifecycle wiring (one reason to change: the
  persistence wiring / lifecycle-hook surface). `engine/state.ts`'s addition
  (the brand) belongs to the state-vocabulary module (a state's runtime
  identity is a state concern). `attestation.ts` is UNCHANGED (its one reason to
  change — the attestation shape — is not touched; D-S5-P2). This is Boundaries
  A and B above.
- **Open/Closed.** Adding a `PipelineState` needs no marker/persistence change
  (the marker treats `pipeline_state` as an opaque string; the projection reads
  `allowedRolesFor` which already derives from state data). A new lifecycle hook
  is a new handler registration in `enginePersistence.ts`, not a rewrite. The
  marker's max-age/version are config constants, tunable without touching the
  validate logic.
- **Liskov.** The persisted marker read from `ctx.sessionManager.getEntries()`
  is validated to the same `StateMarker` shape before use; a marker that does
  not satisfy the shape/validate contract is rejected (never a narrower subtype
  silently substituted).
- **Interface Segregation.** `mintState`/`validateState`/`loadKey`/
  `canonicalSigningInput` are separate narrow exports; a caller that only
  validates need not import mint. `enginePersistence.ts` depends on the small
  `mintState`/`validateState` surface, not on marker internals.
- **Dependency Inversion.** `enginePersistence.ts` (high-level lifecycle policy)
  depends on the `verify/marker.ts` abstraction (mint/validate) and the
  `Engine.resumeAt` abstraction, not on `node:crypto` directly; `verify/marker.ts`
  (low-level crypto) depends on nothing above it. The pi runtime is injected via
  the `ExtensionAPI`/`ctx` the handlers receive — not reached into by the pure
  cores (AC-PURITY).

### DRY analysis

- **One canonical signing input.** The `\x1f`/`\x1e` join is defined ONCE in
  `verify/marker.ts` (`canonicalSigningInput`) and used by both `mintState` and
  `validateState` — never re-inlined (mirrors `bridge.py`'s single
  `_canonical_signing_input`).
- **One key loader.** `loadKey` is the single fail-closed key-read; the seam and
  tests call it, not a re-implemented read (mirrors `bridge.py` importing
  `verify/marker.py`'s `load_key`).
- **Projection reused, not copied.** `allowed_agents` is built from the S4
  `allowedRolesFor(state)` derivation, not a hand-duplicated state→role table
  (the `bridge.py` docstring's "no second sequencing authority").
- **Fixtures reused in place.** The golden fixtures + key are read from
  `tests/fixtures/` directly (single source of truth; D-S5-6), never copied.
- **Named constants.** `STATE_MARKER_VERSION`, `FIELD_SEP`, `AGENT_SEP`,
  `DEFAULT_MAX_AGE_SECONDS`, `DIGEST`, `STATE_MARKER_ENTRY_TYPE` are single named
  constants, not repeated literals.
- **Reuse existing idioms.** `node:crypto` `createHmac`+`timingSafeEqual`
  (from `sequence-gate.ts`), the `ExtensionAPI` handler-registration idiom (from
  `enforcement.ts`/`delegate.ts`), typed `Error` subclasses with `.name` (from
  `depth.ts`) are reused, not re-designed.

### Single Responsibility statement (per new/edited module)

- `verify/marker.ts`: construct + validate a keyed-HMAC `StateMarker`. One
  reason to change: the marker crypto construction.
- `enginePersistence.ts`: wire the signed engine-position persistence lifecycle
  (mint-on-transition, persist, rehydrate/validate on resume/compaction). One
  reason to change: the persistence/lifecycle-hook wiring.
- `engine/state.ts` (edit): define the pipeline state vocabulary + the runtime
  brand for a genuine state. One reason to change: the set of states / their
  runtime identity.
- `engine/engine.ts` (edit): move engine state per the deterministic rules;
  `resumeAt` now requires a branded state. One reason to change: the state-mover
  behaviour (the `resumeAt` hardening is within this responsibility, not a new
  one).

---

## Open Items (for spec-review attention — plan-stage judgment calls)

These are **refinements of converged decisions**, not new material tradeoffs —
each is a place where I exercised planning judgment beyond a pure derivation, so
I name them precisely for spec-review to confirm (or route back to the operator
if any is judged material):

1. **D-S5-P1 — the governing boundary rule for touching `state.ts`/`engine.ts`.**
   I concluded D-S4-6's literal "five S1–S3 modules untouchable" does NOT govern
   these S4-built engine modules; the governing rule is the S5 brief's "no
   scope-creep into S4's engine" (no change to `attemptGate`/`TRANSITIONS`/
   budget/the five modules), under which the `resumeAt` brand-check is a
   permitted ADDITIVE tightening. **Confirm** this is the correct boundary
   reading and that an additive `resumeAt` tightening is in-scope.
2. **D-S5-P2 — marker/`Attestation` stay parallel (no explicit binding).** I
   kept the `StateMarker` (persisted-position integrity) and the `Attestation`
   (GATE evidence) as separate concerns, with no import between them. The brief
   left this open. **Confirm** parallel is intended, or whether the operator
   wants a validated `StateMarker` to feed `Attestation` construction (which
   would risk touching `attemptGate` — I judged that out of scope).
3. **D-S5-P3 — the persistence seam lives in a NEW `enginePersistence.ts`.** I
   isolated all pi-facing I/O there to preserve engine + marker purity.
   **Confirm** the new module (vs folding into an existing extension) is
   warranted.
4. **D-S5-P4 — mint-on-transition at the caller/driver edge.** The seam wraps
   engine mutation; `Engine.step` is unchanged. **Confirm** the additive
   caller-edge attachment (vs any change inside the engine) is what "additive,
   at the driver/caller edge" (brief) intends.
5. **Extension arming / default-off.** `sequence-gate.ts` is armed default-off
   (`GLEIPNIR_PIPELINE=on` + a bridge file). **Confirm** whether the persistence
   seam should likewise be default-off (only persist/rehydrate within an armed
   gated run) or always-on — this affects whether an unarmed ordinary session
   pays the mint-on-transition cost. I did NOT decide this; it is a posture
   choice for the operator if spec-review judges it material.
6. **Golden-fixture relative path from `pi-package/test/`.** I specified
   reuse-in-place at `../../tests/fixtures/golden_marker*.json` +
   `golden_key.bin`. **Confirm** this relative path resolves under the
   sandbox test runner's cwd (the test author verifies at collection; if it does
   not resolve, the fallback is a `node:path` join off `import.meta.url`, as
   `test_sequence_gate.mjs` does — NOT a fixture copy).
7. **Build-order annotation (Tier-0, not mine to write).** The 4b divergence
   moves engine-position persistence wiring from S8 into S5 (brief §Selected
   Approach D-S5-4 consequence 2). The build-order
   (`pi-dev-replatform-build-order.md`) must be annotated to record this move
   (S8's scope shrinks). **This is a Tier-0 edit for the orchestrator/operator
   to enact — I cannot write it.** Named here so it is not lost.
8. **`session_compact_failed` handling.** Primary source shows a
   `session_compact_failed` event exists (fires on aborted/failed compaction).
   The plan persists BEFORE compaction (in `session_before_compact`), so a
   failed compaction does not lose position; I did NOT add a
   `session_compact_failed` handler. **Confirm** no handler is needed (my read:
   the pre-compaction persist already covers it).

None of these is, in my judgment, a *material* tradeoff between viable
architectures (they are refinements within the converged 4b approach); but per
my standing discipline I surface them rather than bake them in silently. If
spec-review judges any material, it routes back to the operator via the
brainstorm/convergence gate.
