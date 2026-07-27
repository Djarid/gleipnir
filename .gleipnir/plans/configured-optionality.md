# Plan: Configured Optionality + Option-1 Engine Work

**Stage:** `plan` (owned by `gleipnir-plan`). **Model:** Opus (unbounded-judgment stage).
**Status:** authored, ready to hand to the orchestrator for sequencing into
`spec-review -> test -> code -> quality -> [local commit] -> gate`.

**Scope note (read first).** The design below is **already decided by the
operator** and is recorded here faithfully as LOCKED. This plan's job is to
make that design rigorously executable by the code/test stages — not to
re-open it. Where a durable ruling must survive across sessions it is flagged
for the operator to persist in Tier-3 `decisions/` (see the closing
**Durable-decision hand-off**); this plan itself is a Tier-0 transient artifact.

---

## 1. Architect

**Problem (one sentence).** The G-5 engine today exposes exactly one fixed
autonomy posture with `git` wrongly welded in as a core mainline state; operators
need to *configure* how much human control the pipeline runs under — from
function-level autocomplete to observer-with-veto — while a small set of
structural safety stops remains impossible to remove, and while remote/platform
git is treated as an attachable capability rather than a core assumption.

**User.** The **operator** (human running Gleipnir), who declares a posture once
per pipeline run/session; and, downstream, the **orchestrator** (G-5 driver) and
roster agents, which consume the resulting deterministic gate-set as data.

**Measurable success criteria.**

1. An operator can select an autonomy **preset L2–L5** and the engine expands it
   to a concrete, inspectable gate-set at the correct transitions (§Stress-test
   S1–S4).
2. An operator can **override any single transition's** gate on top of a preset
   (add or remove a review gate), at per-transition granularity (S5).
3. **Structural stops always fire** — the attestation/evidence gate and an
   explicit `NEEDS_HUMAN` verdict — at *every* configuration including L5, and a
   config that tries to disable a structural stop is **refused fail-closed**
   (S6, S7).
4. With **no operator config**, the engine runs the **unconfigured default
   (L4 + review gates ON)**, emits a **loud, unmissable announcement** that it is
   on the default (not a chosen posture), and **does not auto-cross review
   gates** (S8).
5. Git-remote/platform is **absent by capability** when its bolt-on is not
   attached: no `push`/`PR`/`MR` states exist in the pipeline at all (S9). When
   attached, those states are injected **plus a pre-PR/MR HITL gate that is
   default-ON but operator-removable** (not structural) (S10).
6. The gate's **definition-of-done is a configurable evidence rung** 0–4, default
   rung 0, with rungs 2–4 only reachable when the remote bolt-on is attached
   (S11).
7. The existing 49 engine tests' **structural guarantees survive** the refactor:
   no verdict routes into the completion gate; `HUMAN_QUESTION` still has exactly
   one non-`step()` exit; loop caps still escalate at exactly N (S12).

**Constraints.**

- **Determinism (G-5).** Sequencing and gate placement live as *checked-in data
  and code*, never as prose an LLM narrates. Config is compiled to a data
  structure the router consults; the router never inspects free text. This
  extends the existing `TRANSITIONS`-as-data invariant.
- **Fail-closed (Axiom 2 / G-3.2).** Any ambiguity — an unknown preset, a config
  touching a structural stop, a missing rung provider — refuses rather than
  defaulting to "proceed."
- **Capability-shaped absence (G-2 spirit).** Remote git is *removed by absence
  of capability*, not by a prompt telling an agent "don't push." No bolt-on ⇒ no
  state ⇒ no code path ⇒ nothing to bypass.
- **Reuse existing primitives.** Build over the current `HUMAN_QUESTION` state,
  `Verdict.NEEDS_HUMAN`, `attempt_gate`/`Attestation`, and the loop-cap machinery.
  Do **not** invent a parallel control channel.
- **Visibility is intrinsic, not a new subsystem.** Observation = opencode's
  observable subagent sessions (operator drills into any live delegation) + the
  Tier-1 bus audit trail. Veto = operator interrupting the opencode session. **No
  separate visibility layer is built here.**
- **Tier discipline (G-6).** The plan is Tier-0 (`plans/`). The durable ruling is
  Tier-3 (`decisions/`) and is operator-only — this role cannot write it.

---

## 2. Trace

### 2.1 Artifacts and where they live (source of truth)

| Artifact | Path | Tier | Writer | Role in this feature |
|---|---|---|---|---|
| Engine core (refactor target) | `src/gleipnir/engine/__init__.py` | code | `gleipnir-code` | git removed from core states; gates/rungs added as data |
| Engine design record | `src/gleipnir/engine/DESIGN.md` | code | `gleipnir-code` | updated to describe core-vs-bolt-on + config model |
| Engine tests | `tests/test_engine.py` (+ new modules) | code | `gleipnir-code` | acceptance tests S1–S15 authored test-first |
| Config model (new) | `src/gleipnir/engine/config.py` (proposed) | code | `gleipnir-code` | autonomy presets, gate placement, bolt-ons, rung |
| Bolt-on registry (new) | `src/gleipnir/engine/boltons.py` (proposed) | code | `gleipnir-code` | remote-git capability injects states + pre-PR/MR gate |
| Evidence-rung provider iface (new) | `src/gleipnir/engine/evidence.py` (proposed) | code | `gleipnir-code` | rung 0–4 "definition of done" for the gate |
| Stage-role binding | `.gleipnir/stage-role-map.md` | Tier 3 | operator only | may need a follow-up entry for `git-pm`; flag, don't write |
| **Durable decision record** | `.gleipnir/decisions/configured-optionality.md` | **Tier 3** | **operator only** | **this role CANNOT write it — see hand-off** |
| This plan | `.gleipnir/plans/configured-optionality.md` | Tier 0 | `gleipnir-plan` | the only file this role writes |

Concrete filenames under `src/gleipnir/engine/` are *proposed*; the code stage
may consolidate, but the four responsibilities (config model, bolt-on registry,
evidence provider, refactored core) must each have a clear home.

### 2.2 The control model (LOCKED — three layers)

**Layer 1 — STRUCTURAL STOPS (always on, unremovable at every configuration).**
1. The **attestation/evidence gate**: the only edge into completion is
   `attempt_gate(attestation)` against a satisfied evidence rung. Never reachable
   by a routed `Verdict`.
2. An explicit **`NEEDS_HUMAN` verdict**: any stage's judge may raise
   `Verdict.NEEDS_HUMAN`, which routes to `HUMAN_QUESTION`, whose only exit is
   `answer_human_question`. Present at every level, L2 through L5.

These two are **not** expressible as removable config. A config that names either
for removal is rejected fail-closed (§S7).

**Layer 2 — CONFIGURABLE HITL GATES (opt-in, per-transition granularity).**
A **review gate** may be placed at **any transition between pipeline stages**. If
the operator specifies none (and is not on the unconfigured default), there are
**no** review gates beyond the structural stops. A review gate on transition
`X -> Y` means: on the judge returning `PASS` for `X`, the engine routes to a
blocking human-review checkpoint before entering `Y`, implemented as a
`HUMAN_QUESTION`-shaped pause whose only exit is an explicit human answer (reusing
the precept-10 primitive — not a new blocking mechanism).

**Layer 3 — AUTONOMY-LEVEL PRESETS L2–L5 (named starting gate-sets, then
override-able point-by-point).**

| Preset | Meaning | Default gate-set (before overrides) |
|---|---|---|
| **L2** | AI autocomplete at function level; human orchestrates, engine barely drives (e.g. offsec implant work) | Review gate at (effectively) every meaningful transition; human is in the loop continuously. Engine is a minimal driver. |
| **L3** | HITL: gate at **every** stage transition | Review gate on every ordinary transition in the active pipeline |
| **L4** | Gate only at **high-consequence** transitions | Review gates on the high-consequence subset (see §2.4) |
| **L5** | HOTL observer-with-veto | **No** review gates; only the structural stops. Operator watches via opencode sessions and interrupts to veto. |

A preset **expands to a concrete gate-set** which the operator may then override
transition-by-transition (Layer 2). Preset is the *starting point*, not a lock.

**UNCONFIGURED DEFAULT.** When the operator supplies no config:
- posture = **L4** **AND review gates ON**;
- the engine emits a **VERY CLEAR, unmissable announcement** that it is running on
  the default and this was *not* an explicit operator choice;
- the default **must not auto-cross review gates** — it pauses at them like any
  configured gate.

### 2.3 Classification of every pipeline transition

The **core pipeline** after refactor (git-local is core; remote is bolt-on):

```
BRAINSTORM -> PLAN -> SPEC_REVIEW -> TEST -> CODE -> QUALITY -> LOCAL_COMMIT -> GATE
                          (FAIL loops, capped)   (FAIL loops, capped)
   any main-line state --(NEEDS_HUMAN)--> HUMAN_QUESTION   [structural stop 2]
   SPEC_REVIEW / QUALITY --(cap reached)--> ESCALATED
```

Every transition classified as `{ordinary, review-gate, structural-stop}`.
"review-gate" below means *a gate MAY be configured here* (opt-in); "ordinary"
means no gate placement is offered.

| Transition | Class | High-consequence? (in L4 default set) | Notes |
|---|---|---|---|
| BRAINSTORM -> PLAN | review-gate | no | gateable at L2/L3 |
| PLAN -> SPEC_REVIEW | review-gate | **yes** | plan approval is a natural human checkpoint |
| SPEC_REVIEW -> TEST | review-gate | no | |
| SPEC_REVIEW -> SPEC_REVIEW (FAIL loop) | ordinary | — | loop cap is structural (escalation), not a review gate |
| TEST -> CODE | review-gate | no | |
| CODE -> QUALITY | review-gate | no | |
| QUALITY -> QUALITY (FAIL loop) | ordinary | — | capped -> ESCALATED |
| QUALITY -> LOCAL_COMMIT | review-gate | **yes** | committing to local history is consequential |
| LOCAL_COMMIT -> GATE | **structural-stop** | always | attestation/evidence gate; layer-1 stop 1; never routed |
| any -> HUMAN_QUESTION (`NEEDS_HUMAN`) | **structural-stop** | always | layer-1 stop 2; always present incl. L5 |
| cap-reached -> ESCALATED | **structural-stop** | always | escalation sink; deterministic, unremovable |

**Bolt-on transitions (exist ONLY when the remote bolt-on is attached):**

| Transition | Class | High-consequence? | Notes |
|---|---|---|---|
| LOCAL_COMMIT -> PUSH | review-gate | **yes** | injected by remote bolt-on |
| PUSH -> OPEN_PR_MR | review-gate | **yes** | injected by remote bolt-on |
| **pre-PR/MR gate** (before OPEN_PR_MR) | review-gate, **default-ON, operator-REMOVABLE** | yes | LOCKED: default on, but NOT structural — operator may remove it |
| OPEN_PR_MR -> GATE | structural-stop | always | gate now measures a higher evidence rung (CI/merge) |

When the remote bolt-on is **absent**, none of `PUSH`, `OPEN_PR_MR`, or the
pre-PR/MR gate exist as states or transitions — absence by capability (§S9).

### 2.4 The config surface (how an operator declares posture)

A single declarative config value (dataclass / parsed mapping — checked-in data
shape, not free prose) with these fields:

1. **`autonomy_level`**: one of `L2 | L3 | L4 | L5`. Selects the starting
   gate-set. Absent ⇒ unconfigured-default path (L4 + gates-on + announcement).
2. **`gate_overrides`**: a per-transition map, e.g.
   `{("PLAN","SPEC_REVIEW"): GATE_OFF, ("TEST","CODE"): GATE_ON}`. Applied *on top
   of* the preset's expansion. Per-transition granularity is mandatory. An
   override naming a transition that does not exist in the active pipeline (e.g. a
   PUSH transition when no remote bolt-on) is refused (S13).
3. **`boltons`**: set of attached capability modules, e.g.
   `{REMOTE_GIT}` (push/remote via `git-ops`) and/or `{PLATFORM_PM}` (PR/MR
   lifecycle via `git-pm`). Attaching injects the corresponding states +
   transitions + the default-on-removable pre-PR/MR gate. Empty set ⇒ core-only
   pipeline.
4. **`evidence_rung`**: `0..4`. Default `0`. The gate's definition-of-done:
   - **rung 0** = G-3.1 local marker present (core; default; safest)
   - **rung 1** = local commit exists (core)
   - **rung 2** = pushed to remote (requires `REMOTE_GIT` bolt-on)
   - **rung 3** = CI green (requires bolt-on)
   - **rung 4** = merged (requires bolt-on)
   Selecting a rung ≥ 2 without the enabling bolt-on is refused fail-closed (S14).

**Compilation.** A deterministic `compile_config(config) -> EnginePlan` step turns
the config into (a) the active state set + transition table, (b) the resolved
gate placements, (c) the required evidence rung + its provider. The router and
`attempt_gate` consult only this compiled data — never the raw config text and
never `payload`. Structural stops are injected *by the compiler unconditionally*
and cannot be removed by any config input (they are not read from the config's
removable-gate surface at all — §2.5).

### 2.5 The engine refactor (git out of core states)

**Current (wrong):** `PipelineState.GIT` is a fixed mainline state; the only edge
into `GATE` is `attempt_gate` callable *only while state is `GIT`*; `PIPELINE_ORDER`
hard-codes `GIT`.

**Target:**
- Replace the mainline `GIT` state with **`LOCAL_COMMIT`** as the core terminal
  pre-gate state (commit-to-local is inherent). `attempt_gate` becomes callable
  from **whichever state is the compiled pipeline's last pre-gate state**
  (`LOCAL_COMMIT` core-only; `OPEN_PR_MR` when the remote bolt-on is attached),
  determined by the compiled `EnginePlan`, not a hard-coded literal.
- `PUSH` / `OPEN_PR_MR` states and their transitions move **out of the core table**
  into the bolt-on registry, injected only when attached.
- Structural stops (`GATE` reachable only via `attempt_gate`; `HUMAN_QUESTION`
  with sole non-`step()` exit; `ESCALATED` sink) are preserved exactly. The three
  load-bearing structural absences from the current DESIGN.md remain absences.

### 2.6 Edge cases

- **Unknown preset string** (e.g. `"L9"`, `"L1"`) ⇒ refuse fail-closed, not
  "closest match."
- **Override on nonexistent transition** ⇒ refuse (name the invalid transition).
- **Config attempts to remove a structural stop** (names the attestation gate,
  `NEEDS_HUMAN` routing, or the escalation sink in `gate_overrides`) ⇒ refuse;
  these are never read from the removable-gate surface.
- **Rung ≥ 2 without remote bolt-on** ⇒ refuse.
- **Rung 4 (merged) selected but PLATFORM_PM bolt-on absent** ⇒ refuse (merge is a
  platform-lifecycle capability).
- **Pre-PR/MR gate removed by operator** ⇒ allowed (it is default-on but
  non-structural); the attestation gate still fires.
- **L5 + a review-gate override added** ⇒ allowed (override on top of preset);
  structural stops still present.
- **Empty config** ⇒ unconfigured-default path, announcement emitted exactly once,
  gates not auto-crossed.
- **Bolt-on attached but its role is unbound** (`git-pm` not in stage-role-map) ⇒
  flag as a Tier-3 gap for the operator; the engine plan should surface an
  actionable error rather than silently drop the states.

---

## 3. Link (validated before building)

- **Primitives to reuse exist and are green.** Confirmed by reading
  `src/gleipnir/engine/__init__.py`: `HUMAN_QUESTION` + `answer_human_question`
  (precept-10 blocking gate), `Verdict.NEEDS_HUMAN`, `attempt_gate`/`Attestation`
  (G-3.2), and the per-state loop-cap machinery all exist and are exercised by the
  49-test suite. The configurable-gate mechanism is a **routing layer over these**,
  not a new blocking primitive.
- **The refactor point is identified.** `GIT` as a hard-coded mainline state and
  `attempt_gate`'s `state is PipelineState.GIT` precondition (lines ~63–80, ~155–162,
  ~382–419) are the exact spots the core-vs-bolt-on split touches.
- **Determinism invariant reconfirmed.** DESIGN.md's "sequencing lives in
  `TRANSITIONS` as data; the router never inspects `payload`" is the invariant the
  config compiler must extend — config compiles *to* such data.
- **Tier boundary validated.** Per `decisions/gleipnir-layout-and-memory-model.md`,
  `decisions/` is Tier-3 operator-only; `plans/` is Tier-0 and this role's sole
  writable path. The durable ruling is therefore a **hand-off**, not a write.
- **Evidence rung 0 already has its provider.** Rung 0 = G-3.1 local marker,
  already built in `src/gleipnir/verify/marker.py` (per DESIGN.md traceability).
  Rungs 2–4 need a real fetch surface — out of Option-1 scope, deferred.
- **Visibility need validated as already-met.** opencode observable subagent
  sessions + Tier-1 bus = the observation surface; interrupt = veto. No new
  component to design.

---

## 4. Assemble (build order)

**Option 1 is FIRST and is the whole of this delegation's build.** Later
interfaces (evidence providers beyond rung 0, the bus binding) are named as
follow-on steps, not built here.

**Step 1 — Core-vs-bolt-on engine refactor (test-first).**
   1a. Author tests asserting: `GIT` no longer a core mainline state; core
       pipeline is `... -> QUALITY -> LOCAL_COMMIT -> GATE`; `attempt_gate` is
       driven by the compiled last-pre-gate state, not a hard-coded `GIT`; and the
       three structural absences still hold (S12).
   1b. Refactor `__init__.py`: rename/replace `GIT` with `LOCAL_COMMIT`; move
       `PUSH`/`OPEN_PR_MR` out of the core table; parameterise `attempt_gate`'s
       precondition on the compiled plan. Keep all existing structural guarantees.

**Step 2 — Config model + compiler (test-first).**
   2a. Author tests S1–S8, S13 against the config surface (§2.4).
   2b. Implement `config.py`: `AutonomyLevel` enum (L2–L5), `gate_overrides` map,
       `boltons` set, `evidence_rung` (default 0); `compile_config -> EnginePlan`.
       Preset→gate-set expansion tables for L2/L3/L4/L5 as **checked-in data**.
       Unconfigured-default path (L4 + gates-on + announcement, no auto-cross).

**Step 3 — Configurable-gate routing over `HUMAN_QUESTION` (test-first).**
   3a. Author tests: a review gate on `X -> Y` pauses at a `HUMAN_QUESTION`-shaped
       checkpoint whose only exit is an explicit answer; structural `NEEDS_HUMAN`
       remains independently available (S2, S5).
   3b. Implement gate routing: the compiled plan marks gated transitions; on a
       gated `PASS`, route to the blocking checkpoint instead of directly to the
       target. Reuse the precept-10 exit contract; do not add a second exit path.

**Step 4 — Bolt-on registry + pre-PR/MR gate (test-first).**
   4a. Author tests S9, S10: no bolt-on ⇒ no PUSH/PR/MR states exist; bolt-on
       attached ⇒ states injected + pre-PR/MR gate present, default-ON, removable.
   4b. Implement `boltons.py`: `REMOTE_GIT` and `PLATFORM_PM` inject their states,
       transitions, and the default-on-removable pre-PR/MR gate into the plan.

**Step 5 — Structural-stop enforcement + refusals (test-first).**
   5a. Author tests S6, S7, S11, S14: structural stops fire at every level incl.
       L5; a config removing a structural stop is refused; evidence-rung selection
       validated (default 0; rung ≥ 2 requires the bolt-on).
   5b. Implement the compiler's fail-closed validation: structural stops injected
       unconditionally and never read from the removable-gate surface; rung/bolt-on
       cross-checks refuse fail-closed.

**Step 6 — DESIGN.md update + config surface documentation (code stage).**
   Update `src/gleipnir/engine/DESIGN.md` to describe core-vs-bolt-on, the config
   model, and the three control layers. (Tier-3 `stage-role-map.md` and the durable
   `decisions/` record are operator hand-offs, not written by the pipeline.)

**FOLLOW-ON steps (named, NOT part of Option 1):**
- **Evidence-provider interface** for rungs 2–4 (pushed / CI-green / merged): a
  real fetch surface behind the rung abstraction. Rung 0 (G-3.1 marker) and rung 1
  (local commit) are the only providers Option 1 wires; 2–4 stay stubbed/absent
  until the remote surface exists.
- **G-4 bus binding**: emit gate-crossing, override-application, and
  default-announcement events onto the Tier-1 audit bus. Option 1 leaves the audit
  emission points marked but unbound.
- **Stage-role binding for `git-pm`**: operator adds a `git-pm` row to
  `stage-role-map.md` (Tier 3) if PLATFORM_PM is to be routable.

---

## 5. Stress-test (acceptance checks the code stage must satisfy)

Concrete, checkable. The code stage authors these as tests *before* implementing.

- **S1 — L3 gates every ordinary transition.** Config `L3` ⇒ every ordinary
  stage-to-stage transition in the active pipeline carries a review gate.
- **S2 — L5 gates nothing but structural stops.** Config `L5` ⇒ zero review gates;
  the compiled plan's gated-transition set (excluding structural stops) is empty.
- **S3 — L4 gates exactly the high-consequence subset.** Config `L4` ⇒ review gates
  present at PLAN→SPEC_REVIEW and QUALITY→LOCAL_COMMIT (and the bolt-on
  high-consequence transitions when attached), and absent elsewhere.
- **S4 — L2 keeps the human continuously in the loop.** Config `L2` ⇒ gates at (at
  least) every meaningful transition; engine acts as a minimal driver.
- **S5 — Per-transition override on top of a preset.** `L4` + override removing the
  PLAN→SPEC_REVIEW gate ⇒ that gate is absent; all other L4 gates unchanged. `L5` +
  override adding a TEST→CODE gate ⇒ exactly that one gate present.
- **S6 — Structural stops fire even at L5.** At `L5`: (a) a judge returning
  `NEEDS_HUMAN` routes to the blocking human checkpoint; (b) the completion gate is
  reachable only via `attempt_gate` with a satisfied rung — no routed verdict
  enters it.
- **S7 — Config disabling a structural stop is refused.** A `gate_overrides` entry
  naming the attestation gate, the `NEEDS_HUMAN` routing, or the escalation sink ⇒
  `compile_config` refuses fail-closed; state/plan unchanged.
- **S8 — Unconfigured default.** No config ⇒ (a) posture is L4; (b) review gates are
  ON; (c) an unmissable "running on DEFAULT, not a chosen config" announcement is
  emitted (exactly once); (d) the engine does **not** auto-cross any review gate.
- **S9 — No remote bolt-on ⇒ no push/PR/MR states.** With `boltons` empty, the
  compiled plan contains **no** `PUSH`, `OPEN_PR_MR`, or pre-PR/MR gate states, and
  no transitions referencing them. Core last-pre-gate state is `LOCAL_COMMIT`.
- **S10 — Remote bolt-on attached ⇒ states injected + pre-PR/MR gate present and
  removable.** With `REMOTE_GIT` (and/or `PLATFORM_PM`) attached: `PUSH`/`OPEN_PR_MR`
  states exist; a pre-PR/MR review gate is present **by default**; an override
  removing it succeeds (proving non-structural); the attestation gate still fires.
- **S11 — Evidence rung default and semantics.** Default `evidence_rung` is 0
  (G-3.1 marker). `attempt_gate` succeeds only when the configured rung's provider
  is satisfied; a higher rung not satisfied ⇒ gate refuses fail-closed.
- **S12 — Refactor preserves structural guarantees.** After git leaves core: (a) no
  `Verdict` routes into `GATE`; (b) `HUMAN_QUESTION` still has exactly one exit
  (`answer_human_question`), unreachable from `step()`; (c) loop caps still escalate
  at exactly N for SPEC_REVIEW and QUALITY with independent counters; (d) the
  existing 49 tests (adapted for the `GIT`→`LOCAL_COMMIT` rename) still pass.
- **S13 — Override on a nonexistent transition is refused.** e.g. an override on a
  PUSH transition with no `REMOTE_GIT` bolt-on ⇒ refuse, naming the invalid
  transition.
- **S14 — Rung/bolt-on cross-check.** `evidence_rung` ≥ 2 without `REMOTE_GIT` ⇒
  refuse; rung 4 (merged) without `PLATFORM_PM` ⇒ refuse.
- **S15 — Determinism / no-text-routing preserved.** No config field or `payload`
  is pattern-matched by the router or `attempt_gate`; a `payload` containing
  `"skip gate"` or `"autonomy=L5"` never alters routing. Config is consulted only
  via the compiled `EnginePlan`.

---

## 6. Execution Workflow

**For the orchestrator (sequencing).** Route this plan through the pipeline in the
locked stage order: `spec-review` (`quality-reviewer`, Sonnet) validates this plan
against the spec/decisions as rubric → `test` and `code` (`gleipnir-code`, Sonnet)
execute Steps 1–6 **test-first**, one ATLAS-Assemble step per delegation, tests
authored before implementation in each step → `quality` (`quality-reviewer`) blast-
radius review against this plan → `[local commit]` (core) → `gate` (orchestrator
reads attestation at the configured rung). Remote push/PR/MR states appear only if
a bolt-on is attached; otherwise the pipeline has none (S9).

**For the implementing agent (`gleipnir-code`).**
1. Work the Assemble steps **in order**; each step is test-first — author its
   Stress-test items as failing tests, then implement to green.
2. Preserve every structural absence documented in the current `DESIGN.md`; the
   refactor renames `GIT`→`LOCAL_COMMIT` and *relocates* remote states to the
   bolt-on registry — it must not weaken any structural stop (S12).
3. Config compiles to data (`EnginePlan`); the router and `attempt_gate` read only
   that compiled data — never raw config text, never `payload` (S15).
4. Structural stops are injected by the compiler unconditionally and are **not**
   read from the removable-gate surface, so no config input can reach them (S7).
5. The unconfigured-default announcement must be **unmissable and emitted exactly
   once**, and the default must not auto-cross gates (S8).
6. Do **not** build a visibility layer — observation is opencode sessions + the
   Tier-1 bus; veto is operator interrupt.
7. Do **not** wire rung 2–4 providers or the G-4 bus binding in this delegation —
   they are named follow-on steps.
8. On completion, hand the durable-decision content (below) to the operator; do not
   attempt to write `.gleipnir/decisions/` or `.gleipnir/stage-role-map.md`.

**Definition of done for this feature-set.** All of S1–S15 green; DESIGN.md updated;
the durable-decision record handed off to the operator.

---

## Durable-decision hand-off (Tier-3 — operator must persist)

This plan is Tier-0 and disposable. The following ruling is **durable** and later
work depends on it, so per `goals/plan-format.md` and the trust-tier model it must
be persisted in **Tier-3 `decisions/`**, which **`gleipnir-plan` cannot write**.

- **Proposed path:** `.gleipnir/decisions/configured-optionality.md`
- **Proposed title:** *Decision: Configured optionality — three-layer control
  model, git core-vs-bolt-on, and evidence rungs*
- **Content the operator should capture (all LOCKED here):**
  1. The **three control layers** (structural stops always-on; opt-in per-transition
     HITL gates; L2–L5 presets expanding to override-able gate-sets).
  2. The **unconfigured default = L4 + review-gates-ON + unmissable announcement +
     no auto-cross** rule.
  3. The **git model**: local commit is core; remote push (`git-ops`) and platform
     PR/MR (`git-pm`) are attachable bolt-ons; the pre-PR/MR gate is default-ON but
     operator-removable (non-structural).
  4. The **evidence rungs** 0–4, default 0; rungs 2–4 require the remote bolt-on.
  5. The **engine-refactor ruling**: git is removed from core G-5 states
     (`GIT`→`LOCAL_COMMIT`); remote states are bolt-on-injected — a change to the
     record in `src/gleipnir/engine/DESIGN.md`'s premise.
- **Related Tier-3 follow-up (operator):** add a `git-pm` row to
  `stage-role-map.md` if PLATFORM_PM is to be routable (currently unbound — flagged
  as an edge case in §2.6).
