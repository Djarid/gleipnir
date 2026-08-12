# Design Brief: allow_table ROLE_STATES stale-binding fix (brainstorm→gleipnir-brainstorm)

## Problem Statement

`src/gleipnir/engine/allow_table.py`'s `ROLE_STATES` table is stale relative to
`.gleipnir/stage-role-map.md`, the authoritative (Tier-3, operator-authored)
stage→role binding. The table predates the roster split that created
`gleipnir-brainstorm` as its own role. Concretely:

- `ROLE_STATES["gleipnir-plan"]` incorrectly maps to
  `{PipelineState.BRAINSTORM, PipelineState.PLAN}` — it should map to `{PLAN}`
  only.
- There is no `"gleipnir-brainstorm"` entry at all — it should map to
  `{BRAINSTORM}`.

Because `ALLOW_TABLE` / `allowed_agents_for()` are *derived* from `ROLE_STATES`,
every bridge marker minted by `Driver.write_bridge()` while the engine is at
`BRAINSTORM` lists only `gleipnir-plan` as dispatchable and never
`gleipnir-brainstorm`. Under an armed run (`GLEIPNIR_PIPELINE=on` +
`.gleipnir/plugins/sequence-gate.ts`), this makes the brainstorm stage
**structurally unreachable by its actually-bound role** — the
`gleipnir-brainstorm` role could never be dispatched at the one state it owns.

This bug was logged this session as candidate lesson **L-C20** (a "derived, not
hand-maintained" table can still silently drift if its authored input isn't
updated when the roster changes). This brief records the fix; it does not
re-litigate L-C20.

## Constraints

- **`stage-role-map.md` is authoritative and already converged** — the correct
  binding is directly derivable from it (brainstorm → gleipnir-brainstorm; plan
  → gleipnir-plan; two distinct roles, specifically so the precept-10
  convergence gate has a dedicated owner). This brief must not invent a new
  binding, only mirror the map.
- **`ROLE_STATES` is the single authored projection input** — `ALLOW_TABLE` and
  `allowed_agents_for()` are computed from it and must remain a derivation, not
  a hand-maintained parallel copy. The fix edits only the authored source (+ its
  docstring), never the derivation logic.
- **`PipelineState.BRAINSTORM` and `PLAN` are distinct enum members**
  (`engine/__init__.py:56-57`) with a distinct `TRANSITIONS` edge
  (BRAINSTORM→PLAN); there is no subtlety collapsing them.
- **`gate` stays absent from `ROLE_STATES`** — it is the orchestrator's own
  bound stage (`Engine.attempt_gate`), a control state, not a `task` delegation
  target; it correctly remains deny-all.
- **Tier boundary:** this change touches only `src/` and `tests/` (Tier-0
  operational code under version control), which is within `gleipnir-code`'s
  and `gleipnir-plan`'s reach. It does **not** touch any Tier-3 `.gleipnir/**`
  config.
- **Out of scope (hard):** `.gleipnir/var/run/pipeline-state.json` — the live
  stale bridge — must not be read-for-write or modified. No roster role has
  access; the capability gap is already logged as **L-C19**. This delegation is
  about the *source of truth for future mints*, not the one stale live artifact.

## Approaches Considered

This task is the **single-recommendation (non-material) case** per the
`brainstorm` skill: the correct binding is directly derivable from the
already-converged authoritative `stage-role-map.md`, and is independently
corroborated by the *already-correct* TypeScript side of the cross-language
handshake (`tests/test_sequence_gate.mjs` already encodes `state: "brainstorm"`
→ `agents: ["gleipnir-brainstorm"]`). There is essentially one right answer, so
genuinely distinct competing strategies do not exist for the *fix itself*.

The one sub-question with any decision content was **how far to strengthen the
parity test** (L-C20's specific recommendation: a test that fails when a roster
role has no `ROLE_STATES` entry it should have, not just one that checks the
enum is fully covered). Two framings were weighed:

### Approach A: Minimal fix only (recommended core)

**Summary:** Fix the source binding and its docstring; update only the two
existing `test_allow_table.py` assertions that hardcode the stale binding so the
suite goes green again.

**Tradeoffs:**
- Pro: smallest diff; strictly mandatory work (the two assertion edits are
  required just to make the suite pass after the source fix).
- Pro: zero design surface — nothing to get wrong.
- Con: leaves the exact class of bug (a role-axis drift) uncaught by tests. The
  existing `test_every_pipeline_state_has_an_entry` guard checks the *state*
  axis only; a missing role like `gleipnir-brainstorm` yields a legal-looking
  empty allow-set and passes today.

**Estimated Scope:** `allow_table.py` (+ docstring), `test_allow_table.py` (two
assertions). Low complexity.

**Risk:** Low — but it does not close L-C20's identified gap, so the same drift
could recur silently on the next roster change.

### Approach B: Minimal fix + role-axis parity guard (SELECTED)

**Summary:** Approach A, plus add a canonical expected `ROLE_STATES` literal
(transcribed from `stage-role-map.md`) asserted equal to the module's actual
`ROLE_STATES`, extending the module's own SSOT-parity claim from the state axis
to the role axis.

**Tradeoffs:**
- Pro: closes the exact class of bug found this session — any future
  roster/binding change not mirrored in `ROLE_STATES` fails a test immediately.
- Pro: it is the SSOT-parity pattern the module's docstring already claims,
  merely extended to the role axis; no new design fork.
- Pro: directly discharges L-C20's recommendation in the same slice, at
  negligible marginal cost (a few lines).
- Con: slightly larger diff, and the canonical literal is itself a transcription
  of `stage-role-map.md` that must be kept accurate — but that is precisely the
  single authoritative check point the guard is meant to be.

**Estimated Scope:** Approach A + one new parity test in `test_allow_table.py`.
Low complexity, low risk.

**Risk:** Low — the canonical literal encodes the authoritative map at one
audited location; if the map changes, the test is the thing that flags the
drift, which is the intent.

## Decision Analysis

**No material tradeoff; single recommendation, orchestrator-confirmed.** Per the
`brainstorm`/`decision-frameworks` workflow allowance for the non-material case:
the fix binding is directly derivable from the already-converged, authoritative
`stage-role-map.md` (and corroborated by the already-correct TS handshake side),
so this is ordinary approach selection, not a precept-10 operator-decision item.

The one sub-question (parity-test scope) was evaluated as a potential decision
point and resolved as a **clear extension, not a genuine tradeoff**: the minimal
assertion edits (Approach A's two changes) are *already mandatory* just to make
the suite green, and the role-axis parity guard (Approach B's addition) is the
directly-recommended L-C20 companion check at negligible marginal cost, using a
pattern the module's docstring already claims. All 12 bias detectors were run;
**none fired**. The nearest candidate, Scope Creep, does **not** apply — the
parity guard is not scope-expansion-to-avoid-a-choice but the specific guard the
failure itself demands.

**Recommendation:** Approach B. Confirmed by the orchestrator (exercising
judgment to confirm the single directly-derivable correct answer rather than
surfacing a one-answer call to the operator).

## Selected Approach

**Choice:** Approach B (minimal fix + role-axis parity guard),
orchestrator-confirmed. The plan stage implements exactly these five points:

1. **Fix `src/gleipnir/engine/allow_table.py`:** split
   `ROLE_STATES["gleipnir-plan"]` into
   `"gleipnir-brainstorm": frozenset({PipelineState.BRAINSTORM})` and
   `"gleipnir-plan": frozenset({PipelineState.PLAN})`; correct the stale
   docstring prose (lines 11-14) that currently says
   "brainstorm/plan -> gleipnir-plan".
2. **Update `tests/test_allow_table.py`:** fix
   `test_gleipnir_plan_maps_to_brainstorm_and_plan_exactly` (split into a
   gleipnir-plan-maps-to-plan-exactly assertion + a new
   gleipnir-brainstorm-maps-to-brainstorm-exactly assertion) and
   `test_each_state_allows_exactly_its_bound_role_and_no_other`'s
   `BRAINSTORM: {"gleipnir-plan"}` expectation (must become
   `{"gleipnir-brainstorm"}`).
3. **Add the L-C20-recommended role-axis parity guard:** a canonical expected
   `ROLE_STATES` literal (transcribed from `stage-role-map.md`) asserted equal
   to the module's actual `ROLE_STATES`, so a future roster/binding change that
   isn't mirrored here fails a test immediately (closes the exact class of bug
   found this session).
4. **Leave `test_bridge.py:44`, `tests/fixtures/golden_marker.json`,
   `tests/fixtures/dogfood_bridge.json` untouched** — confirmed
   harmless/correct: `test_bridge.py:44` signs opaque MAC payload (not a binding
   assertion), and the fixtures are already-correct PLAN-state markers
   (`allowed_agents=["gleipnir-plan"]`).
5. **Do not touch `.gleipnir/var/run/pipeline-state.json`** — out of scope, no
   access, already logged as L-C19.

**Rationale:** The binding is directly derivable from the authoritative map and
corroborated by the already-correct TS side; points 1–2 are mandatory to make
the suite green; point 3 discharges L-C20 at negligible cost and closes the drift
class; points 4–5 are explicit non-goals confirmed during Explore to prevent
scope creep and boundary violations.

## Open Questions

- **None blocking.** The fix binding, the affected test set, the non-goals, and
  the parity-guard shape are all resolved. Two notes for the planner, not
  decisions:
  - The two tests that recompute expected from `allowed_agents_for(...)` —
    `tests/test_driver.py:63` (BRAINSTORM) and
    `tests/test_armed_run_dogfood.py:168` — track the fix automatically and need
    **no edit**; they are, in fact, the tests that prove the driver's minted
    marker follows the correction. The planner should keep them as-is and treat
    them as the derivation-correctness witnesses, not touch them.
  - After the fix, the Python-derived allow set and the hand-written TS side of
    the cross-language bridge handshake (`tests/test_sequence_gate.mjs`) will be
    consistent for BRAINSTORM (both → `gleipnir-brainstorm`); today they are
    inconsistent. No TS edit is required — the TS side is already correct — but
    the planner may note this as the end-to-end consistency the fix restores.

## Scope Sketch

| Area | Files/Modules Likely Affected | Nature of change |
|------|-------------------------------|------------------|
| Source binding | `src/gleipnir/engine/allow_table.py` | Split `gleipnir-plan` entry into `gleipnir-brainstorm`→`{BRAINSTORM}` + `gleipnir-plan`→`{PLAN}`; correct docstring lines 11-14 |
| Existing tests (update) | `tests/test_allow_table.py` | Rewrite the `gleipnir-plan`-maps assertion (split + add `gleipnir-brainstorm` case); fix `BRAINSTORM` expectation in the exact-role test |
| New guard (add) | `tests/test_allow_table.py` | New role-axis parity test: canonical `ROLE_STATES` literal == module `ROLE_STATES` |
| Auto-tracking tests (no edit) | `tests/test_driver.py:63`, `tests/test_armed_run_dogfood.py:168` | Recompute expected from `allowed_agents_for(...)`; verify green, do not touch |
| Untouched (confirmed) | `tests/test_bridge.py:44`, `tests/fixtures/golden_marker.json`, `tests/fixtures/dogfood_bridge.json` | Opaque MAC payload / correct PLAN-state fixtures — no change |
| Out of scope (hard) | `.gleipnir/var/run/pipeline-state.json` | Do not touch — L-C19; no access |
| Derivation logic (unchanged) | `_derive_allow_table()`, `ALLOW_TABLE`, `allowed_agents_for()` | No change — the fix edits only the authored input |
