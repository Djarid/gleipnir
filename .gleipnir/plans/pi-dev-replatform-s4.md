# Plan: S4 — G-5 deterministic engine, re-expressed in TypeScript

> **Role:** `gleipnir-plan` (plan stage). **Planned FROM** the CONVERGED brief
> `.gleipnir/plans/pi-dev-replatform-s4-brainstorm.md` (all six decisions
> D-S4-1..6 decided by the operator, zero divergence). This plan does NOT
> re-derive those decisions; it refines them into concrete Assemble steps and
> an acceptance-check set traceable line-for-line to the Python oracle
> (`src/gleipnir/engine/**` + `tests/test_engine.py` / `test_allow_table.py` /
> `test_judges.py`), all read directly this session (L-C36).

## GOTCHA pre-flight (visible)

- **Goals checked:** `.gleipnir/goals/manifest.md` → `plan-format.md` is the
  binding artifact/format goal; this plan follows its 8 required sections
  including the **Design Principles** Gate-1 section. `methodology.md`
  (ATLAS/GOTCHA-ahead-of-planning) satisfied by this plan's shape.
- **Plan-before-code:** confirmed — no `pi-package/src/engine/**` exists yet
  (glob of `pi-package/src` returns only the five S1–S3 modules). This is a
  plan; it writes only to `.gleipnir/plans/`.
- **GOTCHA layer mapping:** this slice is the **Orchestration** layer (G-5
  deterministic sequencing) re-expressed in the pi substrate. The engine core
  is deterministic code (the "deterministic code" half of the
  probabilistic-LLM↔deterministic-code bridge); the judges are the **Tools**
  layer boundary (injected readers = the only I/O); the router is the
  **Args**/routing-policy layer. No **Hard-prompt** or **Context** layer work.
- **Capability boundary:** I may write ONLY `.gleipnir/plans/**`. This plan
  file is the sole artifact I produce. No code, no tests, no Tier-3.

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-S4-1 | Port fidelity strategy | **Approach C** (structural 1:1 + TS-idiomatic surface, mandatory idiom-mapping table) | A (literal), B (idiomatic w/ separate parity) | Operator-converged (brief §Selected Approach). Keeps auditable test-for-test correspondence while producing TS a pi maintainer would write; idiom table is the falsifiable Design Intent. |
| D-S4-2 | Engine-state persistence home | **Option 2a** in-process module singleton; restart/compaction survival DEFERRED to a named S5 seam | 2b signed-file bridge, 2c appendEntry | Operator-converged. In-process (Open-Q1) removes the fresh-process rationale for `bridge.py`; HMAC is S5. `resume_at` shape still ported as the seam's wiring point. |
| D-S4-3 | Judge re-expression | **Hypothesis A** — port judge SHAPES + grammars now (fake readers); defer live reader wiring | B (wire live judging now) | Operator-converged. Matches `judges.py`'s payload-blind injected-reader design; sidesteps the `--network=none` live-model gap. |
| D-S4-4 | Attestation S4/S5 boundary | **Confirmed boundary** — port `attempt_gate` edge + `Attestation` VALUE type + `AttestationStatus` + refusal suite; NO HMAC/fetch/golden-vectors | (port HMAC into S4) | Operator-converged. `attempt_gate` is the engine contract; real marker verification is S5. `attempt_gate` returns the GATE `StepResult` with no bus (S8), no signing (S5). |
| D-S4-5 | Router re-expression scope | **Option 5a** — re-express router MECHANISM now over a single named literal-set config constant marked "superseded at Tier-3 pi cutover"; do NOT block on the literal supersession | 5b (block S4 on Tier-3 supersession) | Operator-converged. Mechanism (Axis-1/2 logic) and literals (which paths) are separate responsibilities (SRP); S4 owns the mechanism only. |
| D-S4-6 | S1–S3 scope boundary + composition seam | **Confirmed boundary + additive seam in-scope** — build `allowedRolesFor(state)` and the additive consultation point; ZERO edits to the five S1–S3 modules | (modify delegate.ts/enforcement.ts; or defer seam entirely) | Operator-converged. Engine is a distinct sequencing layer above role→tool enforcement. Seam is additive; any diff to the five modules is an Important review divergence. |
| D-S4-P1 | **[PLAN-STAGE JUDGMENT]** Test-port manifest completeness | Port `test_engine.py` (all classes) + `test_allow_table.py` + `test_judges.py`; port a *minimal* `resume_at` rehydration case; `test_driver*.py` / `test_bridge*.py` OUT of scope | (port driver/bridge suites) | Refinement of the brief's Open-Question (brief §Open Questions: "port allow_table + judges-grammar suites; port driver/bridge only insofar as the in-process singleton needs them"). Driver/bridge are the fresh-process + HMAC + G-4 bus machinery deferred to S5/S8 per D-S4-2/D-S4-4. **Flagged for spec-review** (§Open Items). |
| D-S4-P2 | **[PLAN-STAGE JUDGMENT]** `Verdict`/`PipelineState`/`AttestationStatus` TS surface form | `const`-object + derived string-literal-union `type` (frozen) — NOT a TS `enum` | (TS `enum`; bare union) | D-S4-1 leaves "const-object OR string-literal union" open ("per D-S4-1's idiom mapping"). Chose const-object-as-SSOT + `typeof`-derived union because it (a) preserves the Python `str`-Enum's string *values* for the bridge seam and router config, (b) matches the pi-package's existing `Object.freeze` idiom (`roleTable.ts`), (c) avoids TS `enum`'s known runtime/erasure quirks under `--experimental-strip-types`. **Flagged for spec-review** (§Open Items). |
| D-S4-P3 | **[PLAN-STAGE JUDGMENT]** Module decomposition | `state.ts`, `transitions.ts`, `engine.ts`, `attestation.ts`, `allowTable.ts`, `judges.ts`, `router.ts` (7 modules) | (fewer modules; single engine.ts) | The brief's Scope Sketch says "in engine.ts OR a dedicated attestation.ts". Chose dedicated `attestation.ts` for SRP (the attestation value type + `AttestationStatus` is a distinct responsibility from the state-mover `Engine`) and because S5 will extend attestation with HMAC — a clean seam boundary. **Flagged for spec-review** (§Open Items). |

## Architect

**Problem (one sentence).** Re-implement the G-5 deterministic orchestration
engine — pipeline state machine, judged transitions, the global revert budget,
the human gate, the attestation gate, the state→allowed-role projection, the
judge factories/grammars, and the blast-radius router mechanism — natively in
TypeScript inside the pi extension (in-process), such that the TS engine
re-earns every behaviour the Python engine test suite pins.

**User.** The pi extension's orchestrator (which consults `allowedRolesFor` and
drives the engine) and, transitively, the operator whose pipeline is sequenced
by deterministic code rather than narrated by an LLM. Downstream: S5 (HMAC
marker), S8 (G-4 bus) build on this slice's contracts and seams.

**Measurable success criteria.**
1. A TS test suite structurally ports `test_engine.py` (all test classes, same
   test names, same assertions, syntax-adapted only) and passes under
   `node --experimental-strip-types --test test/engine*.test.ts` inside
   `bin/gleipnir-sandbox --profile pi` (`--network=none`).
2. The `test_allow_table.py` suite and `test_judges.py` suite are likewise
   ported and pass (fake readers only).
3. A minimal `resume_at` rehydration test passes (the S5 seam's wiring point).
4. The router mechanism (Axis-1 `X` / Axis-2(a) `E` / Axis-2(b) `G` /
   hardened-vs-light) is tested independent of the specific path literals, so a
   later literal swap is a data change with an unchanged, still-green test.
5. `allowedRolesFor(state)` exists and is deny-by-default; the additive
   composition seam is specified (and, if a call site is added, added WITHOUT
   editing any of the five S1–S3 modules).
6. Zero edits to `roleTable.ts`, `enforcement.ts`, `delegate.ts`, `depth.ts`,
   `activeRole.ts`. Zero touch of any Axis-2(a) `E`-set file.
7. The idiom-mapping table (§Design Principles) is honoured by every surface
   choice (the review honour-check).

**Constraints.**
- **Oracle-bound** (semantics frozen to the Python engine; only syntax adapts —
  D-S4-1=C).
- **In-process** (Open-Q1 resolved = `createAgentSession`; the engine holds
  state in a live module singleton like `activeRole.ts`/`depth.ts` — D-S4-2).
- **No HMAC / no fetch / no golden-vectors** (S5 — D-S4-4).
- **No live judging** (fake readers only; live wiring is the caller edge —
  D-S4-3).
- **Router mechanism only, not the literal supersession** (D-S4-5).
- **No scope-creep into S1–S3** (D-S4-6).
- **stdlib/SDK-free engine core** — the engine core imports no pi runtime
  symbols (mirrors `judges.py`'s "no import into engine core" discipline and
  `roleTable.ts`'s compile-time-only `ToolName` import); judges take injected
  readers as the only I/O boundary.

## Trace

### Artifacts and where they live (source of truth)

All NEW files under `pi-package/src/engine/` and `pi-package/test/`. The
**source of truth for behaviour** is the Python oracle (cited per module); the
**source of truth for TS surface idiom** is the idiom-mapping table
(§Design Principles) + the existing pi-package modules.

| TS artifact (to be created) | Ports / derives from (oracle) | Responsibility |
|---|---|---|
| `pi-package/src/engine/state.ts` | `__init__.py` L55–79 (`PipelineState`, `PIPELINE_ORDER`) + `DEFAULT_REVERT_BUDGET` L87 | The 10-member state SSOT + main-line order tuple + default budget constant. |
| `pi-package/src/engine/transitions.ts` | `__init__.py` L90–98 (`Verdict`), L145–187 (`TRANSITIONS`) | `Verdict` (3 values) + frozen `TRANSITIONS` data preserving ALL structural absences. |
| `pi-package/src/engine/attestation.ts` | `__init__.py` L196–212 (`AttestationStatus`, `Attestation`) | The attestation VALUE type + status enum. VALUE/CONTRACT only (S5 extends). |
| `pi-package/src/engine/engine.ts` | `__init__.py` L214–511 (`StepResult`, error classes, `Engine`) | `StepResult`, the typed error classes, and the `Engine` class (the only state-movers). |
| `pi-package/src/engine/allowTable.ts` | `allow_table.py` L1–105 (`ROLE_STATES`, derived `ALLOW_TABLE`, `allowed_agents_for`) | `ROLE_STATES` lifted from stage-role-map; `ALLOW_TABLE` DERIVED by projection; `allowedRolesFor(state)` — the composition-seam entry point. |
| `pi-package/src/engine/judges.ts` | `judges.py` L1–304 (three factories, grammars, exit-code map) | The three judge factories as pure functions over an injected reader; anchored-line grammars; TEST exit-code map. |
| `pi-package/src/engine/router.ts` | `stage-role-map.md` "Prose/config-only track" (Axis-1 `X`, Axis-2(a) `E`, Axis-2(b) `G`, hardened/light) | The blast-radius classifier MECHANISM over a touched-path set `P`; literals as ONE named config constant marked pending-Tier-3-supersession. |
| `pi-package/test/engine.test.ts` | `tests/test_engine.py` (all classes) | Structural port (§AC table). |
| `pi-package/test/allowTable.test.ts` | `tests/test_allow_table.py` | Structural port. |
| `pi-package/test/judges.test.ts` | `tests/test_judges.py` | Structural port (fake readers). |
| `pi-package/test/router.test.ts` | (new; mechanism tests) | Router logic tested independent of literals (D-S4-5). |

### Integrations map

- **`allowTable.ts` → the composition seam (D-S4-6).** `allowTable.ts` imports
  `PipelineState`/`PIPELINE_ORDER` from `state.ts` and lifts `ROLE_STATES` from
  the stage-role-map bindings (the same five bindings `allow_table.py` L55–63
  encodes). `allowedRolesFor(state)` is the additive entry point the
  orchestrator consults **before** calling `delegate`. **The seam is
  additive-only:** the current `delegate.ts` `execute` (L194) unconditionally
  `pushActiveRole(params.role)`; the consultation point sits *upstream* of
  `delegate` — the orchestrator (or a thin new wrapper the orchestrator calls)
  checks `allowedRolesFor(engineState).has(role)` before dispatching. **No edit
  to `delegate.ts`, `enforcement.ts`, or `activeRole.ts`.** See §Design
  Principles honour-check anchor.
- **`judges.ts` → `transitions.ts`/`state.ts` only** (imports `Verdict`,
  `PipelineState`; NO import of `engine.ts`, mirroring `judges.py` L28–33's "no
  import into engine core"). The injected reader (`() => string | null` for
  reviewer transcripts; `() => number | null` for the test exit code) is the
  ONLY I/O boundary — supplied by the caller edge, never by these modules.
- **`engine.ts` → `state.ts`, `transitions.ts`, `attestation.ts`** (pure core;
  no pi runtime imports, no filesystem, no bus). Matches `__init__.py`'s
  no-I/O purity (`DESIGN.md` L175–186 non-goals).
- **`router.ts` → standalone** (a pure classifier over a path-set `P`; its only
  data dependency is its own named literal-set config constant).
- **NO integration** with `roleTable.ts`/`enforcement.ts`/`delegate.ts`/
  `depth.ts`/`activeRole.ts` source (D-S4-6). `allowTable.ts`'s `ROLE_STATES`
  is a *different axis* from `roleTable.ts`'s role→tool sets (state→role vs
  role→tool — brief L74–77); it does not import or modify `roleTable.ts`.

### Edge cases (all pinned by the oracle tests — this is the exhaustive list the port must re-earn)

Structural-table absences (the load-bearing G-5 argument):
- `GIT` has **no `PASS` edge** (`__init__.py` L180–183; `test_git_has_no_pass_edge` L205).
- `GATE`, `ESCALATED`, `HUMAN_QUESTION` **absent as `TRANSITIONS` keys**
  (`__init__.py` L184–187; tests L193–203).
- The **exactly-3 revert (`FAIL`) edges, verified directions from the real
  source**: `SPEC_REVIEW → PLAN` (`__init__.py` L158), `TEST → SPEC_REVIEW`
  (L166 — backward, NOT forward to CODE), `QUALITY → CODE` (L177). Pinned by
  `test_revert_edges_target_the_defined_earlier_stage` (L147) and
  `test_revert_edges_are_strictly_backward_by_pipeline_order` (L157).
- Only those three states have a `FAIL` edge (`test_only_the_three_gate_stages_have_a_fail_edge` L179).
- No `FAIL` edge self-loops (`test_no_fail_edge_self_loops` L171).
- Nothing routes directly into `GATE` (`test_no_state_transitions_directly_into_gate` L212).

Behavioural edges:
- `NEEDS_HUMAN` from any main-line state → `HUMAN_QUESTION`; `step()` while at
  `HUMAN_QUESTION` raises `HumanGateBlocked` (before even calling the judge);
  only `answerHumanQuestion` exits; answering twice raises; answering outside
  the gate raises (`__init__.py` L386–460; `TestHumanGate` L525).
- Global revert budget: monotonic, **never reset by PASS/re-entry/reaching a
  target**; escalates at **exactly N** (`__init__.py` L411–432). The
  **cycle-thrash N=4** anti-thrash proof repositions `_state` directly to
  exercise SR/Q/SR/Q across different edges (`test_cycle_thrash...` L452) — the
  TS port must reproduce this (accessing the private state field via a
  test-only accessor or equivalent; see §Open Items D-S4-P4).
- `NEEDS_HUMAN` does not consume revert budget (`test_needs_human_does_not_consume_revert_budget` L433).
- Attestation refusal matrix (`TestAttestationGate` L704): `None` →
  `AttestationRequired`; non-green (ABSENT/PENDING/RED) → `AttestationNotGreen`;
  green-but-wrong-`pipeline_id` → `AttestationNotGreen`; **dict-lookalike /
  string / `True` / `42`** → rejected by type (`AttestationRequired` or
  `TypeError`); `attempt_gate` before GIT → `EngineError`; state UNCHANGED on
  every refusal; GATE terminal after reached; refused attempt is non-destructive
  (retry to green still works).
- `InvalidVerdict`: a judge returning a bare string (`string_judge`) is rejected
  before routing; state unchanged (`test_judge_returning_raw_skip_text...` L622).
- Text-injection: payload text ("skip review"/"skip gate") never changes routing
  (`TestTextInjectionCannotRoute` L589); no public `Engine` method name contains
  skip/override/bypass (`test_no_bypass_method_exists_on_engine` L633 — a
  structural check the TS port re-expresses over the class's own method names).
- `resume_at`: reconstructs at a given state and is live; rejects a
  non-`PipelineState` value (`TestResumeAt` L796).

Judge grammar edges (`judges.py` + `test_judges.py`):
- SPEC_REVIEW: exactly-one anchored `^SPEC-CONFORM: PASS|FAIL$` line →
  PASS/FAIL; zero/>1/embedded-in-prose/empty/None/whitespace/`MAYBE` →
  NEEDS_HUMAN.
- QUALITY three grammars: (1) hardened two-pass (both SPEC-CONFORM +
  BLAST-RADIUS, each once); (2) light-path lone SPEC-CONFORM; (3) standard
  `APPROVED | APPROVED WITH NOTES | CHANGES REQUIRED` (alternation ordered so
  `APPROVED WITH NOTES` matches before the `APPROVED` prefix). Cross-grammar mix
  / lone BLAST-RADIUS / ambiguity → NEEDS_HUMAN.
- TEST: `0 → PASS`, non-zero int → FAIL, `None → NEEDS_HUMAN`; payload-blind.

Allow-table edges (`test_allow_table.py`):
- Every `PipelineState` has an entry (parity); control/terminal states
  (HUMAN_QUESTION/ESCALATED/GATE) deny-all; `project-mgr`/`notify` never
  allowed; each state allows exactly its bound role; unknown/non-state value →
  empty set (deny-by-default); values are frozen; `ROLE_STATES` mirrors the
  canonical stage-role-map exactly.

## Link (what was validated before building)

Validated directly this session (read in full, not inferred — L-C36):
- **Python oracle read in full:** `engine/__init__.py` (511 L), `allow_table.py`
  (105 L), `judges.py` (304 L), `bridge.py` (192 L), `driver.py` (419 L),
  `engine/DESIGN.md` (186 L).
- **Oracle test suites read in full:** `tests/test_engine.py` (806 L, all test
  classes — the 49-case core), `tests/test_allow_table.py` (125 L, 13 tests),
  `tests/test_judges.py` (326 L). (Confirmed `test_judges_live.py`,
  `test_driver*.py`, `test_bridge*.py` exist and are the OUT-of-scope live/
  driver/bridge suites.)
- **S1–S3 pi layer read in full:** `roleTable.ts`, `enforcement.ts`,
  `activeRole.ts`, `depth.ts`, `delegate.ts` — establishing the composition
  seam (D-S4-6: `delegate.ts` L194 `pushActiveRole` is the additive
  consultation upstream point) and the TS idioms the port adopts (typed `Error`
  subclasses with `.name`; `Object.freeze`/`ReadonlySet`; module-singleton
  state; `RoleName = string`; exported const literals for DRY; `readonly`
  arrays).
- **pi test harness idiom confirmed** (`test/roleTable.test.ts`):
  `import { test } from "node:test"`, `import assert from "node:assert/strict"`,
  `.ts` import extensions, `assert.deepEqual`/`assert.throws`/`assert.equal`.
  (This is the target shape for the ported suites — the port adapts pytest
  classes/`@parametrize` into `node:test` `test(...)` calls with inline arrays.)
- **Open-Q1 decision read:** `decisions/pi-replatform-open-q1.md` — confirms the
  in-process delegation edge is FINAL for S3/S4; S4 consumes the stability
  guarantee and does not reopen it. Also names the inherited live-model-turn gap
  (why live judging is out — D-S4-3).
- **Router mechanism source read:** `stage-role-map.md` "Prose/config-only
  track" — the exact Axis-1 `X` disqualifier set, Axis-2(a) `E` enforcement-path
  set, Axis-2(b) `G` grant/enforcement content patterns, and the
  hardened-vs-light routing rule that `router.ts` re-expresses.
- **Pipeline routing confirmed** (see §Pipeline Routing): this plan touches
  executable TypeScript with class/module structure → **full 8-stage hardened
  pipeline**; zero Axis-2(a) `E`-set file touched.

## Assemble (intended build order)

**Discipline (L-C30 general-timing rule): interface stub BEFORE tests, real
bodies AFTER tests.** The pi test harness collects at import time; a test file
importing a not-yet-existing module fails at collection (the same defect
`judges.py` L8–13 records for the Python stub). So each module lands as a
**typed interface stub first** (real exported types/signatures, bodies that
`throw new Error("not implemented")`), so `test/*.test.ts` imports resolve at
collection; then tests are authored (Red); then real bodies replace the stubs
(Green). Data-only modules (`state.ts`, `transitions.ts`, `attestation.ts`)
have no "stub" phase distinct from their real value — their data IS the
implementation, so they are written real up front (a frozen const cannot
meaningfully throw).

Order:

1. **Data SSOT modules (real, no stub phase).**
   - **1a `state.ts`** — `PipelineState` (const-object + derived union per
     D-S4-P2, values matching the Python string values `"brainstorm"`,
     `"plan"`, `"spec_review"`, … from `__init__.py` L56–65), `PIPELINE_ORDER`
     (the 8 main-line members, frozen), `DEFAULT_REVERT_BUDGET = 3`.
   - **1b `transitions.ts`** — `Verdict` (3 values `"pass"/"fail"/"needs_human"`),
     frozen `TRANSITIONS` reproducing `__init__.py` L145–187 **exactly**,
     including every structural absence (no GIT.PASS; GATE/ESCALATED/
     HUMAN_QUESTION absent as keys; the 3 backward FAIL edges with verified
     directions).
   - **1c `attestation.ts`** — `AttestationStatus` (4 values), `Attestation`
     value type (`{ pipelineId, status }`, frozen at construction). VALUE only.

2. **Engine core interface stub.**
   - **2a `engine.ts` stub** — export `StepResult` type; the typed error classes
     (idiom-mapped names, §idiom table); the `Engine` class shape with method
     signatures (`step`, `answerHumanQuestion`, `attemptGate`, static
     `resumeAt`, `state` getter, `revertCount` getter, constructor) — bodies
     `throw new Error("not implemented")`. This makes `engine.test.ts` import
     resolve at collection.

3. **Projection + judges + router interface stubs.**
   - **3a `allowTable.ts` stub** — export `ROLE_STATES`, `ALLOW_TABLE`,
     `NON_PIPELINE_ROLES`, `allowedRolesFor` signature (stub body).
   - **3b `judges.ts` stub** — export `makeSpecReviewJudge`, `makeQualityJudge`,
     `makeTestJudge` signatures (stub bodies), matching `judges.py`'s
     injected-reader signatures.
   - **3c `router.ts` stub** — export the classifier function signature
     (`routePlan(paths: readonly string[]): RouteDecision`) + the named
     literal-set config constant shape (stub bodies).

4. **Author the ported test suites (Red — test stage arbiter).**
   - **4a `test/engine.test.ts`** — structural port of ALL `test_engine.py`
     classes (§AC table). Same test names, same assertions, `node:test` idiom.
   - **4b `test/allowTable.test.ts`** — structural port of `test_allow_table.py`.
   - **4c `test/judges.test.ts`** — structural port of `test_judges.py` (fake
     readers = plain arrow fns returning fixed values, mirroring the Python
     lambdas). Preserve the payload-blind and Verdict-instance checks.
   - **4d `test/router.test.ts`** — NEW mechanism tests: Axis-1 disqualifier
     hits (an `src/**`/`hooks/**`/standalone-YAML path in `P` → full pipeline),
     Axis-2(a) `E`-path hits (`.gleipnir/agents/**` → hardened), Axis-2(b) `G`
     content-pattern hits (a `permission:`/`tools:` line → hardened), and the
     light path (prose-only `P`, no `G` match). **Tests assert the routing
     DECISION over representative inputs, never the specific literal set** — so
     a later literal swap keeps them green (D-S4-5 fix).

5. **Real bodies (Green — code stage), bounded by the tests above.**
   - **5a `engine.ts`** — implement `Engine` against `__init__.py` L272–511
     semantics: constructor at BRAINSTORM, monotonic single revert counter;
     `step` (HumanGateBlocked-before-judge; InvalidVerdict on non-`Verdict`;
     NoSuchTransition on missing edge; FAIL→increment→escalate-at-exactly-N;
     NEEDS_HUMAN→record origin→HUMAN_QUESTION; PASS→advance);
     `answerHumanQuestion` (only exit; origin restore; raise off-gate/double);
     `attemptGate` (GIT-only; None→required; wrong type→TypeError-analogue;
     non-green/wrong-id→notGreen; state unchanged on refusal; GATE on success);
     static `resumeAt` (reject non-state; counter resets to 0 — the honestly-
     flagged gap, `__init__.py` L330–335).
   - **5b `allowTable.ts`** — `ALLOW_TABLE` DERIVED by iterating `PipelineState`
     and collecting bound roles (a projection, NOT a hand-copied second table —
     `allow_table.py` L71–93); `allowedRolesFor` deny-by-default.
   - **5c `judges.ts`** — the three factories + the shared anchored-line
     grammar helper (`judges.py` L69–94 `_parse_verdict_line` — reused, not
     copy-pasted per judge: DRY); the QUALITY three-grammar branch logic; the
     TEST int→Verdict map.
   - **5d `router.ts`** — the Axis-1/Axis-2 classifier over `P`; the named
     literal-set config constant with the explicit comment binding it to the
     pending Tier-3 pi-literal supersession (D-S4-5).

6. **Composition seam wiring (additive).** Specify (and, only if genuinely
   needed, add) the orchestrator's consultation of `allowedRolesFor(state)`
   before `delegate`. **Default: prose/design specification** — the orchestrator
   agent consults `allowedRolesFor(engineState)` and refuses to delegate to a
   role not in the set. **If a code call site is genuinely needed**, add it in a
   NEW file (e.g. a thin `engine/consultSeam.ts` the orchestrator entrypoint
   calls) — **never** by editing `delegate.ts`/`enforcement.ts`/`activeRole.ts`.
   Justification for either choice recorded at implementation; the blast-radius
   pass + honour-check flag any diff to the five S1–S3 modules as Important.

**Step order rationale.** Data SSOT first (everything depends on `state.ts`/
`transitions.ts`); stubs before tests (collection-time import resolution,
L-C30); tests before real bodies (test-first, the test is the arbiter); seam
last (it consumes `allowedRolesFor`, which must exist and be tested first).

## Stress-test (acceptance checks — the AC→test-port mapping)

The acceptance set IS the structural port of the oracle suites. Every AC below
is traceable to a named Python test; the TS test keeps the **same name** and
**same assertion** (syntax-adapted only, D-S4-1=C). "≈N" counts pytest
parametrize expansions.

### Core engine (`test/engine.test.ts` ← `tests/test_engine.py`, ~49 cases)

| Python test class | Python test names (ported 1:1, same names) | Asserts |
|---|---|---|
| `TestTransitionTableIsTheSpec` (11) | `test_pipeline_order_matches_spec`, `test_verdict_has_exactly_three_members_no_skip`, `test_revert_edges_target_the_defined_earlier_stage`, `test_revert_edges_are_strictly_backward_by_pipeline_order`, `test_no_fail_edge_self_loops`, `test_only_the_three_gate_stages_have_a_fail_edge`, `test_gate_has_no_outgoing_edge`, `test_escalated_has_no_outgoing_edge`, `test_human_question_has_no_outgoing_edge`, `test_git_has_no_pass_edge`, `test_no_state_transitions_directly_into_gate` | The structural-absence invariants over the ported `TRANSITIONS`/`Verdict`/`PIPELINE_ORDER`. |
| `TestHappyPathProgression` (4) | `test_linear_progression_through_all_judged_stages`, `test_gate_reached_only_after_git_via_attempt_gate`, `test_judge_is_called_with_current_state`, `test_judge_receives_the_supplied_payload_verbatim` | Linear PASS walk; GATE only via `attemptGate`; judge invocation contract. |
| `TestRevertEdges` (5) | `test_spec_review_fail_reverts_to_plan`, `test_quality_fail_reverts_to_code`, `test_test_fail_reverts_to_spec_review_and_increments_budget`, `test_fail_from_a_non_gate_state_has_no_transition`, `test_revert_target_is_data_not_narrated_text` | Each revert edge's direction; NoSuchTransition off the three gate states; payload cannot redirect. |
| `TestRevertBudgetExactness` (≈8) | `test_reverts_below_budget_do_not_escalate` (×2 param), `test_revert_at_exactly_budget_escalates`, `test_default_budget_applies_when_not_overridden`, `test_escalated_is_terminal`, `test_budget_never_resets_across_pass_or_reentry`, `test_needs_human_does_not_consume_revert_budget`, `test_cycle_thrash_escalates_at_exactly_n_concrete_budget_4` | Exactly-N escalation; monotonic never-reset counter; the load-bearing N=4 cross-edge cycle-thrash proof. |
| `TestHumanGate` (6) | `test_needs_human_verdict_enters_human_question`, `test_step_is_blocked_while_awaiting_human_answer`, `test_step_blocked_even_with_an_answer_shaped_payload`, `test_answer_human_question_is_the_only_exit`, `test_answer_human_question_outside_the_gate_raises`, `test_cannot_answer_twice_without_a_fresh_question` | The precept-10 gate: one exit, blocked otherwise, no payload bypass. |
| `TestTextInjectionCannotRoute` (4) | `test_skip_review_text_in_payload_does_not_change_routing` (×6 param), `test_judge_returning_raw_skip_text_is_rejected_not_interpreted`, `test_no_bypass_method_exists_on_engine`, `test_no_path_from_quality_directly_to_gate` | Text cannot route; bare-string verdict rejected (InvalidVerdict); no skip/override/bypass method name. |
| `TestNoGateBypass` (3) | `test_step_from_git_with_pass_has_no_transition`, `test_step_from_git_with_fail_has_no_transition`, `test_attempt_gate_before_git_is_refused` | GIT has no judged exit; `attemptGate` refused pre-GIT. |
| `TestAttestationGate` (≈8) | `test_absent_attestation_object_refused`, `test_non_green_status_refused` (×3 param), `test_green_status_for_a_different_pipeline_id_refused`, `test_agent_supplied_text_or_lookalike_cannot_satisfy_the_gate` (×4 param), `test_green_and_matching_pipeline_id_is_accepted`, `test_gate_is_terminal_after_being_reached`, `test_refused_attempt_leaves_git_state_untouched_for_retry` | The full G-3.2 refusal matrix; VALUE/type checks (dict-lookalike rejected by type); non-destructive refusal. |
| `TestResumeAt` (2) | `test_resume_at_reconstructs_at_given_state`, `test_resume_at_rejects_non_pipelinestate` | Rehydration shape (the S5 seam wiring point) + fail-closed on non-state. |

**Type-check adaptation note (D-S4-1=C surface mapping, not a semantic change):**
Python `test_agent_supplied_text_or_lookalike_cannot_satisfy_the_gate` passes a
dict/string/bool/int and expects `(AttestationRequired, TypeError)`. In TS the
"is this a genuine `Attestation` instance?" check is a runtime brand/instanceof
check (see §idiom table row "Python `isinstance` → TS runtime brand check"); the
ported test asserts the TS refusal error is thrown and state is unchanged — the
SAME assertion adapted to the TS type-guard idiom. Flagged in §Open Items
(D-S4-P2) because the brand mechanism is a surface choice.

### Allow-table (`test/allowTable.test.ts` ← `tests/test_allow_table.py`, 13 cases)

Ported 1:1 (same names): `test_every_pipeline_state_has_an_entry`,
`test_control_and_terminal_states_deny_all`,
`test_project_mgr_and_notify_never_allowed`,
`test_gleipnir_plan_maps_to_plan_exactly`,
`test_gleipnir_brainstorm_maps_to_brainstorm_exactly`,
`test_quality_reviewer_maps_to_spec_review_and_quality_exactly`,
`test_gleipnir_code_maps_to_test_and_code_exactly`,
`test_git_ops_maps_to_git_exactly`,
`test_each_state_allows_exactly_its_bound_role_and_no_other`,
`test_unknown_state_denies_by_default`,
`test_allow_table_values_are_frozensets` (→ TS: values are frozen Sets),
`test_role_states_matches_canonical_stage_role_map`. Plus a positive-control
that `ALLOW_TABLE` is a *derivation* (adding a hypothetical unmapped state
yields the empty set — the `allow_table.py` L71–90 projection property).

### Judges (`test/judges.test.ts` ← `tests/test_judges.py`)

Ported 1:1 (same names / same parametrize rows as plain inline arrays):
`TestTestJudge` (`test_maps_exit_code_to_verdict` ×6, `test_zero...`,
`test_nonzero...`, `test_none...`, `test_payload_blind`); `TestSpecReviewJudge`
(`test_clean_anchored_line_maps_to_verdict` ×5, `test_ambiguous_or_missing...`
×9, `test_payload_blind`); `TestQualityJudge` (hardened ×5, lone-blast,
light-path ×2, standard ×3, `test_approved_with_notes_matches_before_approved_prefix`,
`test_this_plans_own_clean_quality_pass_fixture`, ambiguous/mixed ×9,
`test_payload_blind`); `TestJudgesReturnVerdictMembersOnly` (×3 instance
checks). Fake readers only.

### Router (`test/router.test.ts` — NEW, mechanism-not-literals)

- Axis-1 disqualifier: a `P` containing any `X`-member (`src/**`, `hooks/**`,
  `bin/**`, `Makefile`, `.github/**`, standalone `*.yml`, a `*.sh/*.py/*.ts`,
  shebang content) → **full 8-stage** decision.
- Axis-2(a): a track-eligible `P` containing an `E`-member (`.gleipnir/agents/**`,
  `opencode.jsonc`, the enumerated repo-root files) → **hardened**.
- Axis-2(b): a track-eligible `P` where an added line matches `G` (a
  `permission:`/`tools:` block, a capability line, a JSON enforcement key, a
  `keys/**` digest line) → **hardened**.
- Light: a prose-only `P` (`goals/**`, `decisions/**` prose, `plans/**`, `*.md`)
  with no `G` match → **light**.
- **Literal-agnostic:** each test feeds representative paths and asserts the
  decision; none asserts the identity of the literal set (D-S4-5 fix — a later
  opencode→pi literal swap changes only the config constant, tests stay green).

### Cross-cutting ACs

- **AC-ROUTE:** `bin/gleipnir-sandbox --profile pi` runs
  `node --experimental-strip-types --test test/engine.test.ts test/allowTable.test.ts test/judges.test.ts test/router.test.ts` green under `--network=none`.
- **AC-NOTOUCH:** `git diff --name-only` shows ZERO changes to `roleTable.ts`,
  `enforcement.ts`, `delegate.ts`, `depth.ts`, `activeRole.ts`, and ZERO changes
  to any Axis-2(a) `E`-set file (including `stage-role-map.md` itself). This is
  the D-S4-6 honour-check + the blast-radius pass's over-broad-form check.
- **AC-IDIOM:** every surface deviation from Python is a row in the idiom table
  (§Design Principles) — the honour-check rejects any un-tabled surface choice.
- **AC-PURITY:** `engine.ts` imports no pi runtime symbol, no `node:fs`, no bus
  (grep the import block — mirrors `DESIGN.md` non-goals + `judges.py` L28–33).

## Execution Workflow

For the implementing agents (test stage + code stage, both `gleipnir-code`):

1. **Read this plan + the cited oracle lines** (do NOT re-derive semantics from
   the brief's summary; the Python source at the cited line numbers is the
   contract).
2. **Build in the Assemble order.** Data SSOT (1) → engine stub (2) →
   projection/judges/router stubs (3) → **author ported tests (4, Red)** →
   real bodies (5, Green) → seam (6).
3. **Test-first is enforced by the pipeline.** The `test` stage authors
   `test/*.test.ts` against the stubs (must collect clean =
   `--experimental-strip-types --test` exits 0 at collection even while bodies
   throw — the L-C30 stub-before-tests property). The `code` stage then makes
   them green. The test is the arbiter (Axiom 1); do not "improve" semantics
   beyond what the ported assertion pins.
4. **Honour the idiom table.** Any surface choice not in the §Design Principles
   idiom table is a divergence to escalate, not to silently make.
5. **The seam is additive.** If you touch any of the five S1–S3 modules, STOP —
   that is the D-S4-6 Important divergence; the seam goes in a new file or in
   the orchestrator's prose consultation.
6. **Out-of-scope is out.** Do NOT port `bridge.py`/`driver.py`/`marker.py`, do
   NOT add HMAC/fetch/bus/golden-vectors/live judging. If a ported test seems to
   need them, it is mis-ported — re-check against the oracle.
7. **Verdicts:** hardened path → two separate review passes (spec-conformance +
   blast-radius) + negative-check attestation (see §Pipeline Routing).

## Pipeline Routing

**Full 8-stage HARDENED pipeline.** This plan's touched-path set `P` =
`pi-package/src/engine/{state,transitions,attestation,engine,allowTable,judges,router}.ts`
+ `pi-package/test/{engine,allowTable,judges,router}.test.ts` (+ possibly one
new `engine/consultSeam.ts`). These are **executable TypeScript with
class/function/module structure** → they are Axis-1 `X`-members (the
`**/*.ts` disqualifier; the S2 plan's own precedent routes `pi-package` TS
through the full pipeline). Therefore:

- **Track:** NOT the prose/config light track — the **full 8-stage pipeline**
  (`brainstorm → plan → spec-review → test → code → quality → git → gate`), test
  arbiter present.
- **Gate-1 case:** **(i) OOP/functional code** — full SOLID+DRY+SRP+Design
  Intent required (§Design Principles), each falsifiable.
- **Axis-2(a) `E`-set touch: ZERO.** No file in `P` is under
  `.gleipnir/agents/**`, `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`,
  `.gleipnir/policy/**`, `.gleipnir/keys/**`, is `stage-role-map.md` itself, is
  `opencode.jsonc`/`**/opencode.json`, or is an enumerated repo-root file. In
  particular: **`router.ts` re-expresses the stage-role-map MECHANISM as engine
  config in a NEW file — it does NOT edit `stage-role-map.md`** (a different
  file; explicitly confirmed). So no plan-level `E`-set amendment is in scope.
- **Hardened obligations (informational, discharged at the `git`/quality gates,
  not by me):** because this is code, the hardened review discharges via the
  test arbiter + the SOLID/DRY dimension of the blast-radius pass + the
  spec-vs-implementation honour-check (does the applied engine honour the
  idiom-table Design Intent?). The specific negative-check the blast-radius pass
  must run: **AC-NOTOUCH** (the five S1–S3 modules + every `E`-set file are
  byte-unchanged — the over-broad form "an engine change quietly widened
  role→tool enforcement or edited the router SSOT" checked-for-and-ruled-out).

## Design Principles (Gate 1 — case (i): OOP/functional code)

### Design Intent (falsifiable — the idiom-mapping table is the anchor)

**The falsifiable Design Intent of this slice is: the TS engine is a
STRUCTURAL 1:1 port of the Python oracle whose ONLY deviations from the Python
source are the surface transformations enumerated in the idiom-mapping table
below — no behavioural difference exists that is not a table row.** This is
falsifiable in the exact sense the anti-vacuity rule requires: a reviewer can
point to any TS behaviour that differs from the cited Python line AND is not a
tabled surface mapping, and that is a violation. (Concrete falsifiers: a 4th
`Verdict` value; a `GIT`→`GATE` PASS edge; a per-state revert counter; escalate
at N-1 or N+1; a judge that inspects `payload`; `allowedRolesFor` that
default-allows; a router that asserts a specific literal; an edit to any S1–S3
module.)

**Note on the one tabled *behavioural* deviation (idiom-table row 15 — L-C14
phantom-gap discipline).** Row 15 records a genuine behavioural difference, not
a surface-only mapping: TS `resumeAt(id, "spec_review")` with a raw string
SUCCEEDS where Python `resume_at` RAISES, because the converged const-object-
enum idiom (row 1) makes `PipelineState` values plain runtime strings, so the
`isPipelineState` guard cannot reject a same-valued raw string. **This is a
KNOWN, TABLED, operator-ACKNOWLEDGED accepted deviation** — an inherent
consequence of the D-S4-1 idiom choice, with hardening deferred to S5 as a named
seam-hardening item (durable acknowledgment in
`.gleipnir/decisions/pi-replatform-open-q1.md`). It therefore satisfies the
Design Intent's "no un-tabled behavioural difference" clause (it IS tabled). A
future reviewer MUST NOT re-flag this specific `resumeAt` raw-string-acceptance
deviation as a fresh honour-check violation: it is already surfaced, tabled, and
accepted here.

**Idiom-mapping table (Python → TS surface mapping — every deviation named):**

| # | Python surface | TS surface | Rationale |
|---|---|---|---|
| 1 | `class PipelineState(str, Enum)` (10 str members) | `const`-object `{ BRAINSTORM: "brainstorm", … }` + `type PipelineState = typeof PipelineState[keyof …]` string-literal union, `Object.freeze`'d | Preserves the string *values* (bridge/router config need them); matches `roleTable.ts` `Object.freeze` idiom; avoids TS `enum` erasure quirks under `--experimental-strip-types` (D-S4-P2). |
| 2 | `class Verdict(str, Enum)` (3 members) | same const-object+union pattern, frozen; exactly 3 keys | 3-value channel preserved; `test_verdict_has_exactly_three_members_no_skip` re-earns it. |
| 3 | `class AttestationStatus(str, Enum)` (4) | same const-object+union pattern | Preserved. |
| 4 | `TRANSITIONS: dict[PipelineState, dict[Verdict, PipelineState]]` | frozen nested record (`Object.freeze` on the outer + each inner) preserving every structural absence | The absences ARE the spec; freezing prevents runtime widening (`roleTable.ts` AC-19 precedent). |
| 5 | Custom exception classes (`EngineError`, `InvalidVerdict`, `NoSuchTransition`, `HumanGateBlocked`, `AttestationRequired`, `AttestationNotGreen`) | TS `Error` subclasses with `.name` set (idiom from `depth.ts` `DepthCapExceededError`), mirroring the Python *names* (NOT the literal Python names — the TS class names ARE these names, which happen to match; they are idiom-mapped, not string-copied) | Fail-closed refusal = a thrown typed error; `.name` set per `depth.ts`. Tests assert `assert.throws(fn, InvalidVerdict)` etc. |
| 6 | Python `TypeError` on wrong-type attestation | TS runtime **brand/instanceof check** on `Attestation`; a non-`Attestation` (dict-lookalike/string/bool/int) throws the TS type-refusal error | Python's `isinstance` has no direct TS equivalent for a structural value; a brand (private symbol) or class instance check is the TS idiom (D-S4-P2). Same assertion: refused + state unchanged. |
| 7 | `@dataclass(frozen=True)` value types (`Attestation`, `StepResult`) | plain `interface` + a frozen constructed object (`Object.freeze`) OR a `readonly`-field class | Immutability preserved; matches pi-package `readonly`/`Object.freeze` idiom. |
| 8 | `frozenset[str]` (allow-table values) | frozen `ReadonlySet<string>` (`Object.freeze(new Set(...))`) | Matches `roleTable.ts` `SDK_BASE_TOOL_NAMES: ReadonlySet`. `test_allow_table_values_are_frozensets` → asserts frozen Sets. |
| 9 | `snake_case` methods (`answer_human_question`, `attempt_gate`, `resume_at`, `revert_count`) | `camelCase` (`answerHumanQuestion`, `attemptGate`, `resumeAt`, `revertCount`) | TS convention (pi-package uniformly camelCase). Semantics identical. |
| 10 | `pipeline_id` field | `pipelineId` | camelCase; string value identity preserved for the attestation-id match. |
| 11 | Injected reader `Callable[[], str \| None]` / `Callable[[], int \| None]` | `() => string \| null` / `() => number \| null` | Python `None` → TS `null`; the sole I/O boundary preserved (`judges.py` L28–33). |
| 12 | `re.compile(..., re.MULTILINE)` anchored grammars | JS `RegExp` with `m` flag, same patterns (`^SPEC-CONFORM:\s+(PASS\|FAIL)\s*$` etc.) | Grammar preserved byte-for-byte; the shared `_parse_verdict_line` helper → one TS helper (DRY, not per-judge copy). |
| 13 | pytest classes + `@pytest.mark.parametrize` | `node:test` `test(name, fn)` with inline arrays (`for (const [in,out] of [...]) test(...)`) | Harness idiom (`roleTable.test.ts`); same test names preserved for auditable diff. |
| 14 | Module-private `_state`/`_revert_count` (leading underscore) | `#private` fields OR module convention; a **test-only accessor** for the cycle-thrash `_state` repositioning (D-S4-P4) | The N=4 test needs to reposition state directly; expose a narrow test-only setter, not a general state setter (preserves "only step/answer/attemptGate move the engine"). |
| 15 | `Engine.resume_at(id, state)` type-rejects a non-`PipelineState` via `isinstance(state, PipelineState)` (`__init__.py` ~L338): a `str, Enum` member is a distinct runtime type from a bare `str`, so a **same-valued plain string** (e.g. `resume_at(id, "spec_review")`) **RAISES** | `resumeAt`'s `isPipelineState` guard (`state.ts` ~L66–87, consumed by `engine.ts`) can only reject values that are **not one of the ten legitimate state strings at all**; because the const-object-enum idiom (row 1, D-S4-1/D-S4-P2) makes `PipelineState` values **plain strings at runtime**, the guard **CANNOT distinguish a raw string from an "enum member"** — so TS `resumeAt(id, "spec_review")` **SUCCEEDS** where Python RAISES | **ACCEPTED, OPERATOR-ACKNOWLEDGED** consequence of the converged D-S4-1 const-object-enum idiom (row 1): the very idiom that preserves the string *values* for the bridge/router seam also erases the Python `str, Enum` distinct-runtime-type property, so no runtime brand exists at the `resumeAt` entry point to reject a same-valued raw string. This is a genuine fail-closed *weakening* at the (future S5) rehydration seam's entry point, not a surface-only mapping. Hardening it — a **runtime brand/tag on state to reject raw-string input at `resumeAt`** — is DEFERRED to **S5 as a named seam-hardening item**. The durable acknowledgment is recorded by the operator in `.gleipnir/decisions/pi-replatform-open-q1.md`; this row points there for the authoritative decision. |

### SOLID analysis (evaluated against the proposed design)

- **Single Responsibility.** Each module has exactly one reason to change:
  `state.ts` = the state vocabulary; `transitions.ts` = the sequencing data +
  verdict vocabulary; `attestation.ts` = the attestation value contract;
  `engine.ts` = the state-mover behaviour; `allowTable.ts` = the state→role
  projection; `judges.ts` = the verdict-derivation grammars; `router.ts` = the
  blast-radius classification mechanism. (This mirrors the Python oracle's own
  module split, which is why it holds.)
- **Open/Closed.** Adding a `PipelineState` extends `state.ts` data; the
  `allowTable.ts` derivation picks it up automatically (empty set, deny-by-
  default) without editing the projection logic — exactly `allow_table.py`'s
  property. The router's literal-set is config data, swappable without touching
  the classifier (D-S4-5). The engine is closed to modification as states grow
  (sequencing is `TRANSITIONS` data, not branches).
- **Liskov.** The `Judge` type is a structural function type (`(state, payload)
  => Verdict`); every judge factory returns a value substitutable wherever a
  `Judge` is expected (fakes in tests, real readers at the edge). No subtype
  narrows the contract.
- **Interface Segregation.** The injected reader interfaces are minimal
  (zero-arg thunks returning a single value); the `Engine`'s public surface is
  exactly the four state-movers + two read-only getters — no fat interface.
- **Dependency Inversion.** `engine.ts` depends only on the data modules
  (`state`/`transitions`/`attestation`), not on any I/O; `judges.ts` depends on
  the injected reader abstraction, not on a concrete subprocess/transcript
  source (the caller edge supplies it). The engine core is decoupled from pi
  runtime entirely (AC-PURITY).

### DRY analysis

- **No duplicated sequencing.** `ALLOW_TABLE` is DERIVED from `ROLE_STATES` +
  `PipelineState` (a projection), never a hand-copied second table
  (`allow_table.py` L71–93). Enforced by the ported parity/derivation tests.
- **One grammar helper.** The anchored-line extraction is ONE shared TS helper
  reused by the spec-review and quality judges (mirrors `judges.py`
  `_parse_verdict_line`), not copy-pasted per judge.
- **Named literal constants.** State string values, the revert budget, the
  router literal-set, and any test probe literals are single named constants
  (the `roleTable.ts` `GIT_BROKER_TOOL`/`UNIVERSALLY_DENIED` DRY precedent) —
  not repeated inline.
- **Reuse existing idioms, don't reinvent.** Typed `Error` + `.name` (from
  `depth.ts`), `Object.freeze` (from `roleTable.ts`), module-singleton state
  (from `activeRole.ts`/`depth.ts`) are reused, not re-designed.

### Single Responsibility statement (per new module)

- `state.ts`: define the pipeline state vocabulary + main-line order + default
  budget. One reason to change: the set of states.
- `transitions.ts`: define the verdict vocabulary + the sequencing data. One
  reason to change: the transition topology.
- `attestation.ts`: define the attestation value contract. One reason to
  change: the attestation shape (S5 extends it).
- `engine.ts`: move engine state per the deterministic rules. One reason to
  change: the state-mover behaviour.
- `allowTable.ts`: project state→allowed-roles. One reason to change: the
  stage-role binding.
- `judges.ts`: derive a `Verdict` from an injected artifact. One reason to
  change: a grammar/exit-code contract.
- `router.ts`: classify a touched-path set into a review route. One reason to
  change: the routing mechanism (NOT the literals — those are config).

---

## Open Items (for spec-review attention — plan-stage judgment calls, per my standing discipline of not silently deciding material tradeoffs)

These are **refinements of converged decisions**, not new material tradeoffs —
but each is a place where I exercised planning judgment beyond a pure derivation
from the brief, so I name them precisely for the spec-review gate to confirm (or
route back to the operator if any is judged material):

1. **D-S4-P1 — Test-port manifest boundary.** I scoped the port as
   `test_engine.py` (all classes) + `test_allow_table.py` + `test_judges.py` +
   ONE minimal `resume_at` case, with `test_driver*.py` / `test_bridge*.py`
   **OUT** (they exercise the fresh-process bridge, HMAC signing, and G-4 bus
   emit — all deferred to S5/S8 per D-S4-2/D-S4-4). The brief's Open-Questions
   section recommended exactly this ("port driver/bridge only insofar as the
   in-process singleton needs them"); I have concluded the in-process singleton
   needs **none** of them (it holds live state; no bridge read/write, no key,
   no bus in S4). **Confirm:** is zero driver/bridge port correct, or is any
   `driver.py` behaviour (e.g. the `resume_from_bridge` fail-closed shape) part
   of the S4 contract? My read: no — `resume_from_bridge` is HMAC+freshness
   validation = S5. Only the pure `Engine.resume_at` shape is S4.

2. **D-S4-P2 — Enum surface form + the wrong-type refusal mechanism.** I chose
   `const`-object + derived string-literal union (not TS `enum`), and a runtime
   **brand/instanceof** check as the TS analogue of Python's `isinstance`
   TypeError on a dict-lookalike attestation. Both are surface choices D-S4-1
   left open ("const-object OR string-literal union per the idiom mapping").
   **Confirm:** the brand mechanism satisfies `test_agent_supplied_text_or_lookalike_cannot_satisfy_the_gate`
   (dict with the "right" keys must be rejected **by type**, not re-parsed) —
   this is the security-load-bearing case, so the TS type-guard must be a true
   brand check, not a structural duck-type that a lookalike dict could satisfy.

3. **D-S4-P3 — Dedicated `attestation.ts` module.** The brief said "in engine.ts
   OR a dedicated attestation.ts"; I chose dedicated for SRP + the S5 seam.
   **Confirm** the extra module is warranted (low-risk; purely organisational).

4. **D-S4-P4 — Test-only `_state` accessor for the cycle-thrash proof.** The N=4
   anti-thrash test (`test_engine.py` L493) reaches into the private `_state`
   field to reposition the engine across different revert edges. The TS port
   needs an equivalent. I propose a **narrow test-only accessor** (not a general
   public state setter — that would violate "only step/answer/attemptGate move
   the engine", the very invariant `test_no_bypass_method_exists_on_engine`
   protects). **Confirm** the test-only accessor is acceptable (it must not
   appear as a public state-mover the bypass-resistance test would flag; suggest
   naming/placing it so `test_no_bypass_method_exists_on_engine`'s ported form
   still passes — e.g. a `#`-private field with a clearly test-scoped setter, or
   reconstructing via `resumeAt` to the needed state where reachability allows).

5. **Composition-seam realisation (D-S4-6, Assemble step 6).** I specified the
   seam as **prose/orchestrator-consultation by default**, with a NEW-file call
   site only if genuinely needed — explicitly never editing the five S1–S3
   modules. **Confirm** the additive-only realisation is what the operator
   intended by "additive wiring" (brief D-S4-6), and that a computed-but-lightly-
   consumed `allowedRolesFor` in S4 is acceptable (fuller enforcement wiring can
   be a later slice).

None of these five is, in my judgment, a *material* tradeoff between viable
architectures (they are refinements within the converged approach); but per my
standing discipline I surface them rather than bake them in silently. If
spec-review judges any of them material, it routes back to the operator via the
brainstorm/convergence gate.
