# Plan: Wire real judges into the G-5 engine (three judged transitions)

**Stage:** plan (owned by `gleipnir-plan`). **Tier:** 0 (`plans/`, disposable).
**Source of truth:** `.gleipnir/plans/judge-wiring-brainstorm.md` (marked FULLY
CONVERGED). This plan inherits its operator-converged D1–D4 + D2-addendum
verbatim and does **not** re-open any of them. This is an ATLAS brief
(Architect / Trace / Link / Assemble / Stress-test) per
`../goals/plan-format.md`.

**Routing classification (per `../stage-role-map.md`).** The touched-path set
`P` includes `src/**` (new judge module) and `tests/**` (new unit + live
tests). Both are in the Axis-1 disqualifier set `X` → this is **NOT** a
prose/config-only-track plan → the **full 8-stage pipeline is required**.
Bound roles (per `../stage-role-map.md`): `test` → `gleipnir-code`, `code` →
`gleipnir-code`, `quality` → `quality-reviewer`, `git` → `git-ops`. Gate-1
cognition routing: `P ∩ X ≠ ∅` and the touched `X`-members have
function/module structure → **case (i): full SOLID + DRY + SRP + Design
Intent** (see Design Principles).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Scope of first real-judge slice | **All three judged transitions** (`SPEC_REVIEW`, `TEST`, `QUALITY`) in one slice (Option D) | Option A (narrow `QUALITY→GIT` only); B; C (wait for Seam 7/8) | Operator-converged (brainstorm D1, via orchestrator `question` tool — diverged from the brainstorm's Option-A recommendation). Not re-opened. |
| D2 | Evidence provenance for `SPEC_REVIEW`/`QUALITY` | **Structural separation** — judge input is the independent `quality-reviewer` verdict transcript (producer ≠ judged agent) (Option a) | (b) keyed-marker-alone; (c) combination (deferred as maturity target) | Operator-converged (brainstorm D2). A MAC proves integrity, not independence; the load-bearing property is provenance. Not re-opened. |
| D2-add | Evidence class for `TEST` (no separate reviewer role) | **Mechanical exit-code observation** — `bin/gleipnir-sandbox test`'s process exit code, observed directly (option i) | (ii) stand up a test-reviewer role; (iii) drop `TEST` from slice | Operator-converged (brainstorm D2-addendum). Independence-by-mechanical-observation, distinct evidence class; consistent with test-first Axiom 1. Not re-opened. |
| D3 | Judge call location | **Out-of-band via existing `Driver.advance(judge=…)` seam** (Option 2); LLM client / exit-code reader injected at the caller edge | (1) in-process shell-out inside driver; (3) defer to Seam 7 live hook | Operator-converged (brainstorm D3). Engine stays pure/stdlib-only; no Seam-7 dependency. Not re-opened. |
| D4 | Judge vs. cognition layer | **Formalise/consume existing review output** (Option c, starting with b) — judge parses the reviewer's stated verdict grammar; no new bespoke judging LLM | (a) new bespoke engine-side judge LLM | Operator-converged (brainstorm D4). Composes with cognition layer; does NOT amend G-5. Bespoke judge (a) unused — no transition in this slice is reviewer-less. Not re-opened. |
| P1 | Where the judges live in the source tree | **New module `src/gleipnir/engine/judges.py`** | Adding them to `driver.py`; adding them to `engine/__init__.py` | *Planning decision (this plan).* Keeps `engine/__init__.py` pure (no I/O, no LLM/process import — stdlib-only core preserved); keeps `driver.py` focused on bridge/bus I/O. A dedicated module is the natural home for the injectable `Judge` factory. Implementation detail, not a material tradeoff. |
| P2 | Ambiguity/parse-fail/timeout/empty → `Verdict.NEEDS_HUMAN` | **Fail-closed to `NEEDS_HUMAN` for all three judges** | Any new escape hatch; coercing to PASS/FAIL | Inherited hard constraint (brainstorm; reuses existing `HUMAN_QUESTION` gate). Not a tradeoff. |
| P3 | Verdict-parsing grammar strength + set of recognised shapes | **Brittle-but-honest exact-line/anchored-regex match, documented as such; THREE recognised `quality` shapes** (hardened two-pass; light-path lone `SPEC-CONFORM`; standard-quality `APPROVED`/`APPROVED WITH NOTES`/`CHANGES REQUIRED`) | A fuzzy/NLP verdict extractor; recognising only the hardened + light shapes (the original defect — misrouted a clean standard `quality` pass to `NEEDS_HUMAN`) | *Planning decision.* A first slice; a narrow, explicit grammar is auditable and its parse-misses fail closed. The three recognised shapes match the grammars `quality-reviewer` actually emits today (verified: `../agents/quality-reviewer.md` L105–111 + real recorded outcomes `plans/override-paradigm.md` L637–638, `plans/s2-activation.md` R-1). Documented as brittle-by-design. |

**No new material tradeoff surfaced during planning.** Every row above is
either operator-converged (cited) or a bounded implementation detail (P1–P3).
See the report at the end for the explicit statement.

---

## Architect

**Problem (one sentence).** The G-5 engine routes on a `Judge` but the only
wired judge is `_trivial_completion_judge` (always `PASS`, payload-blind); wire
three real judges — `spec_review_judge`, `test_judge`, `quality_judge` — that
consume *independently-produced* artifacts and return genuine
`PASS`/`FAIL`/`NEEDS_HUMAN`, without reintroducing self-attestation and without
touching the engine core.

**User.** The framework harness/caller (and, later, the Seam-7 live hook) that
drives `Driver.advance(judge=…)`; the operator, who relies on the engine making
real accept/reject calls rather than trivial ones.

**Measurable success criteria.**

1. Three new `Judge`-conforming callables exist in `src/gleipnir/engine/judges.py`,
   each typed `Callable[[PipelineState, Mapping[str, Any]], Verdict]` (the exact
   `Judge` alias from `engine/__init__.py` L106).
2. Each is injectable via the existing `Driver.advance(judge=…)` seam
   (`driver.py` L212–251) in place of `_trivial_completion_judge`; the trivial
   judge remains the default (every existing test path untouched).
3. `engine/__init__.py` is **unchanged** — no routing/budget/`TRANSITIONS`/
   `attempt_gate` edit; verified by `git diff` naming zero lines in that file.
4. `spec_review_judge` and `quality_judge` read **only** the independent
   `quality-reviewer` verdict transcript, never the acting agent's self-report;
   `test_judge` reads **only** the mechanical `bin/gleipnir-sandbox test --
   --collect-only` exit code (test-**authoring**/collection validity, per the
   `TEST→CODE` edge semantics — see the `test_judge` Trace §), never
   `gleipnir-code`'s narrative and never a full-suite assertion pass/fail.
5. Every parse-miss / missing artifact / timeout / empty/None input maps to
   `Verdict.NEEDS_HUMAN` (fail-closed) — asserted per judge with fake inputs.
6. A small, clearly-labelled live/integration test set asserts only the
   *contract* (a real transcript with a real PASS/FAIL line → the correct
   `Verdict`; malformed → `NEEDS_HUMAN`) — never LLM prose content.
7. `attempt_gate`/`GATE`/G-3.2 and the `GIT→GATE` edge are provably untouched
   and unreached by this slice.

**Constraints (inherited from the brief — LOCKED).**

- No self-attestation: judge input is never the acting agent's own narrative.
- Do not contradict converged ground: global revert budget, `GIT` has no `PASS`
  edge, router payload-blindness, fail-closed posture are LOCKED.
- No dependency on Seam 7 (live hook) or Seam 8 (real CI attestation).
- Engine stays pure: no I/O, no LLM import, no filesystem in `engine/__init__.py`.
- `NEEDS_HUMAN` is the only ambiguity escape hatch.
- stdlib-only enforcement core (`decisions/runtime-and-deps.md`); any LLM
  client / subprocess reader is injected at the caller edge, outside the core.
- Testable with fakes for all plumbing; a *small* labelled live set for the
  contract only.
- Compose with the cognition layer (`decisions/cognition-layer.md`: review, not
  a guard, orthogonal to G-5) — do not duplicate or amend it.

**Honesty label (inherited, load-bearing).** This slice is
"independently-produced, mechanically-observed / structurally-separated,
hook-scoped." It is explicitly **NOT** a claim of full G-3.2 closure — that
still needs the S-2 substrate boundary + live Seam-7 hook + real CI attestation
fetch (Seam 8), all out of scope and unbuilt. Provenance pre-S-2 is hook-scoped,
carrying the same not-yet-boundary-closed trust the driver itself carries.

---

## Trace

### What gets built (Architect-level artifact map)

| Artifact | Path | Status | Purpose |
|---|---|---|---|
| Judge module | `src/gleipnir/engine/judges.py` | **to be created** | The three `Judge`-shaped callables + their injected-dependency shape. NO import into `engine/__init__.py`. |
| Driver | `src/gleipnir/engine/driver.py` | **existing, UNCHANGED** | `advance(judge=…)` seam (L212–251) already carries any injected judge. No edit needed — the judges are passed *in* by the caller. |
| Engine core | `src/gleipnir/engine/__init__.py` | **existing, UNCHANGED** | `Judge` alias (L106), `Verdict` (L90–98), `TRANSITIONS` (L145–187), revert budget, `attempt_gate` — all preserved. |
| Sandbox entry | `bin/gleipnir-sandbox` | **existing, UNCHANGED** | `test` subcommand propagates pytest's exit code verbatim (verified: `sandbox/__main__.py` L98 `return proc.returncode` → L263 `SystemExit(main())`); passthrough tokens appended after the profile command (L120–144), and the live `python` profile sets `test_selector_prefix = true` (`profiles.toml` L19–26), so `test -- --collect-only` runs `pytest … --collect-only`. `test_judge` observes the **collection-only** exit code (test-authoring validity — see `test_judge` Trace §), NOT a full-suite run. |
| Unit tests (fakes) | `tests/test_judges.py` | **to be created** | Fake-transcript / fake-exit-code / empty-input plumbing tests. |
| Live tests (labelled) | `tests/test_judges_live.py` | **to be created** | Small contract-only live set; Seam-7/8 markers as not-claimed. |

### The `Judge` contract each judge conforms to

`Judge = Callable[[PipelineState, Mapping[str, Any]], Verdict]`
(`engine/__init__.py` L106). The engine calls `judge(self.state, payload or {})`
exactly once (`step`, L392) and requires a `Verdict` member back; anything else
raises `InvalidVerdict` before routing. **The router never inspects `payload`**
— only the judge does. This slice honours that: each judge derives its `Verdict`
from an *injected, independently-sourced artifact*, NOT from `payload` text the
acting agent could populate.

**Design shape (P1).** A single parameterized factory in `judges.py` builds each
judge as a closure over its injected artifact source:

```
def make_spec_review_judge(read_reviewer_verdict: Callable[[], str | None]) -> Judge
def make_quality_judge(read_reviewer_verdict: Callable[[], str | None]) -> Judge
def make_test_judge(read_test_exit_code: Callable[[], int | None]) -> Judge
```

The injected callables (`read_reviewer_verdict`, `read_test_exit_code`) are the
**only** I/O boundary; they live at / are supplied by the caller/harness edge
(the same layer that already does bridge/bus I/O in `driver.py`), never inside
`engine/`'s stdlib-only core. Each returned closure is a **pure function of its
already-sourced artifact → `Verdict`**, with no engine-state mutation, no
network/process call of its own. (Unit tests inject fakes; live tests inject
real readers.) A factory is chosen over three duplicated function bodies to
honour DRY (see Design Principles).

### Per-judge artifact trace

#### `spec_review_judge` — consumes the spec-review subagent verdict transcript

- **Artifact:** the verdict transcript produced by the spec-review stage's
  subagent (`quality-reviewer`, per `../stage-role-map.md`).
- **Source (decide + justify):** an **in-memory string** passed through the
  injected `read_reviewer_verdict` callable, whose *value* the caller sources
  from the reviewer delegation's output. Justification: the brief (D3) sources
  the reviewer artifact out-of-band via the harness; the judge itself must not
  know *how* the string arrived (path vs. captured delegation return) — it only
  parses the string. Binding the artifact to the reviewer delegation +
  pipeline_id/state is the **caller's** responsibility (provenance binding,
  below), keeping the judge a pure parser. (A path-based reader is a valid
  alternative the caller may supply — the injected-callable shape accommodates
  either; the judge is agnostic.)
- **Must NOT read** anything `gleipnir-plan`/`gleipnir-code` wrote about itself.
  Enforced structurally: the judge has no access to the acting agent's return —
  its only input is the injected reviewer-sourced callable.
- **Grammar (P3, brittle-but-honest):** parse for the established spec-review
  verdict line. The spec-review pass emits `SPEC-CONFORM: PASS` / `SPEC-CONFORM:
  FAIL` (per `../stage-role-map.md` hardened-path rubric). Contract:
  - anchored line-match regex `^SPEC-CONFORM:\s+(PASS|FAIL)\s*$` (multiline,
    per-line) — the token must be its OWN line, not embedded in prose;
  - exactly one such line → its token maps: `PASS → Verdict.PASS`,
    `FAIL → Verdict.FAIL`;
  - zero matches, more than one match, or any other content →
    `Verdict.NEEDS_HUMAN` (fail-closed, P2).
- Documented as brittle-by-design: a first slice pins one explicit line form; a
  reviewer that phrases the verdict differently is treated as ambiguous
  (`NEEDS_HUMAN`), never guessed.

#### `test_judge` — consumes the mechanical test-**collection** exit code (test-authoring validity)

**What mechanical signal `test_judge` checks (revised — reconciled against the
engine's own `TEST --FAIL--> SPEC_REVIEW` semantics).** The `test_judge` fires
at the `TEST → CODE` transition — i.e. *leaving* the test-**authoring** stage,
**before** any implementation exists. The engine encodes this edge's meaning
explicitly (`engine/__init__.py` L163–166, and the module comment L128–132): a
`FAIL` at `TEST` reverts to `SPEC_REVIEW` because *"a failed test-authoring
stage means the spec/plan was inadequate to write good tests against."* It is
**not** "the assertions currently fail against not-yet-written code."

Under correct test-first practice the freshly-authored tests target
not-yet-implemented functionality, so **running the full suite here is EXPECTED
to exit non-zero** (assertion failures against missing implementation). A naïve
`0 → PASS; nonzero → FAIL` over the full `bin/gleipnir-sandbox test` run would
therefore route every *correctly-executed* test-first delegation to `FAIL`,
traversing the `TEST → SPEC_REVIEW` revert edge and burning the single global
`revert_count` for doing exactly the right thing. That is a semantics bug, not a
budget concern.

**The mechanical signal is therefore test-COLLECTION validity, not full-suite
pass/fail.** The caller runs pytest in **collection-only** mode and the judge
maps that exit code:

- **Exact command:** `bin/gleipnir-sandbox test -- --collect-only`. Verified on
  disk this is mechanically supported: the live `python` profile
  (`.gleipnir/sandbox/profiles.toml` L19–26) sets `test_selector_prefix = true`,
  and `_cmd_test` appends passthrough tokens as
  `[*base_cmd, *coverage_args, *extra]` (`sandbox/__main__.py` L120–144), so
  `--collect-only` is appended to `python -m pytest -p no:cacheprovider …`,
  yielding `pytest … --collect-only`. `pytest --collect-only` exits **0** iff
  the test files are syntactically valid and **collectible** (imports resolve,
  fixtures/parametrize expressions evaluate, no collection errors), and non-zero
  on any collection/syntax error — *regardless of whether the assertions inside
  would pass against a not-yet-written implementation.* The process exit code is
  propagated verbatim (`sandbox/__main__.py` L98 `return proc.returncode` → L263
  `SystemExit(main())`).
- **Why this is the right proxy for the edge's stated semantics.** Collection
  validity is precisely "was the spec/plan adequate to write *good, loadable*
  tests against?" — if collection fails, the interfaces/spec were unusable to
  author tests against at all (undefined symbols, unimportable modules,
  malformed fixtures), which is exactly the `TEST → SPEC_REVIEW` revert
  condition. If collection **succeeds**, the test-authoring stage produced valid,
  runnable tests and the pipeline correctly advances to `CODE`, where the *same*
  tests (now run for real, assertions and all) become the correctness arbiter
  that `quality`/`code` are bounded by (Axiom 1). The full assertion-level
  pass/fail is thus deferred to where implementation exists — it is *not* the
  `TEST→CODE` question.
- **Why NOT "scope execution to the pre-existing regression suite only".** The
  review named this alternative; it is **discarded**. Reliably partitioning
  "tests authored for not-yet-implemented functionality in this delegation" from
  "pre-existing regression tests" is not mechanically distinguishable at this
  stage without extra per-delegation bookkeeping (a manifest of which test node
  IDs are new), which this slice does not build and the brief does not mandate.
  Collection-only needs no such bookkeeping and maps cleanly onto the edge's
  stated meaning, so it is chosen outright.
- **Evidence class unchanged (stays within D2-addendum).** This is still a
  **non-narrative mechanical observation** — the sandbox command's own process
  exit code, never `gleipnir-code`'s "tests pass" prose. The refinement is
  purely *which* mechanical exit code (collection, not full-run); the converged
  D2-addendum evidence class ("mechanical exit-code observation, independence by
  mechanical observation") is honoured, not re-opened. See the report for the
  explicit not-a-new-tradeoff statement.
- **How the exit code reaches the judge without narrative filtering:** the
  caller/harness runs `bin/gleipnir-sandbox test -- --collect-only` itself (e.g.
  `subprocess.run([...], ...).returncode`, at the caller edge — NOT inside
  `engine/` or `judges.py`) and passes the integer through the injected
  `read_test_exit_code` callable. The judge receives an `int | None`, never a
  string an agent wrote. Independence comes from the signal being *the machine's
  record of collecting the tests*, not any agent's report of it.
- **Contract:**
  - `0 → Verdict.PASS` (tests collect cleanly → authoring was valid → advance to
    `CODE`);
  - any non-zero int → `Verdict.FAIL` (collection/syntax error → the spec/plan
    was inadequate to author loadable tests → revert `TEST → SPEC_REVIEW`);
  - `None` (command not run / result unavailable / timed-out — see Stress-test)
    → `Verdict.NEEDS_HUMAN` (fail-closed, P2).
- Timeout handling is the **caller's** concern (the injected reader applies a
  timeout to the collection subprocess and returns `None` on timeout); the judge
  maps `None → NEEDS_HUMAN`. This keeps process I/O and its timeout at the edge,
  the judge pure. The judge itself is agnostic to *which* exit code it received
  — it maps `int|None → Verdict`; the collection-only choice is enforced by the
  caller running the `--collect-only` command.
- **KNOWN LIMITATION — exit-code channel conflates two fault classes.** A
  non-zero `--collect-only` exit conflates a genuine pytest collection defect
  with a sandbox-wrapper-level refusal (profile misconfiguration or
  infra/container failure, `sandbox/__main__.py` L118/L121–128/L154–156, all
  returning exit 3). This first slice does not distinguish them; both map to
  `Verdict.FAIL`, which is safe-direction (never false-PASS) but can consume
  revert budget on infra noise unrelated to test-authoring quality. KNOWN
  LIMITATION, not required to fix for this slice (see the Stress-test row).

#### `quality_judge` — consumes the `quality-reviewer` verdict transcript (THREE recognised shapes)

- **Artifact:** `quality-reviewer`'s verdict transcript for the `quality` stage.
- **THREE rubric shapes to handle (verified against `../agents/quality-reviewer.md`
  and real prior transcripts, NOT guessed).** `quality-reviewer` emits different
  verdict grammars depending on which review it ran; all three must be
  recognised, or a *clean* quality pass falls into the ambiguity bucket and
  misroutes to `NEEDS_HUMAN`. The three shapes actually emitted today:

  1. **Hardened two-pass** (enforcement-bearing plans, `../stage-role-map.md`
     "Hardened path"): TWO separate structured verdicts —
     `SPEC-CONFORM: PASS/FAIL` **and** `BLAST-RADIUS: PASS/FAIL` (the two passes
     do not fuse). Confirmed as the emitted form in real recorded outcomes:
     `plans/override-paradigm.md` L637–638 ("Two distinct verdicts recorded:
     `SPEC-CONFORM: PASS` and a separate `BLAST-RADIUS: PASS`") and
     `plans/s2-activation.md` R-1 (Decisions row: "Hardened-path spec-review
     round 1 (SPEC-CONFORM PASS; BLAST-RADIUS 3 fail-safe text/script defects)").
     (Earlier drafts cited `plans/override-paradigm.md` L45–48 and
     `plans/enforcement-path-gap-closure.md`; both were rubric-definition /
     requirement prose, not genuinely emitted verdicts — corrected here.)
  2. **Light-path collapsed** (prose/config-only track): a single
     `SPEC-CONFORM: PASS/FAIL` line (the spec-review and quality rubrics run as
     one collapsed pass — `../stage-role-map.md` "Light path").
  3. **Standard full-pipeline quality verdict** (THE GAP THE REVIEW FLAGGED —
     added). THIS plan is a full 8-stage pipeline plan whose `P` is **NOT**
     enforcement-bearing (`src/**` + `tests/**` only; no path under `E`, no
     `G`-pattern), so per `../stage-role-map.md`'s per-stage cognition table its
     own `quality` stage runs the **standalone "Blast-radius pass … incl. the
     honour check"** review — neither the hardened two-line shape nor the
     light-path single-`SPEC-CONFORM` shape. `../agents/quality-reviewer.md`
     L105–111 **mandates that EVERY review** (all stages, all paths) end with a
     verdict token of **`APPROVED` / `APPROVED WITH NOTES` / `CHANGES
     REQUIRED`**. That token — not a `SPEC-CONFORM`/`BLAST-RADIUS` line — is the
     literal verdict a standard non-enforcement `quality` review emits. It is
     added here as an explicitly-named third recognised grammar case.

- **Contract (all three shapes):**
  - **Hardened:** require BOTH `^SPEC-CONFORM:\s+(PASS|FAIL)\s*$` AND
    `^BLAST-RADIUS:\s+(PASS|FAIL)\s*$` present, each exactly once. Both `PASS`
    → `Verdict.PASS`; either `FAIL` → `Verdict.FAIL`.
  - **Light-path:** exactly one `^SPEC-CONFORM:\s+(PASS|FAIL)\s*$` line and no
    `BLAST-RADIUS` line → map its token (`PASS → Verdict.PASS`,
    `FAIL → Verdict.FAIL`).
  - **Standard quality verdict:** exactly one anchored verdict-token line
    matching the mandated grammar
    `^(APPROVED WITH NOTES|APPROVED|CHANGES REQUIRED)\s*$` (alternation ordered
    so `APPROVED WITH NOTES` is matched before the `APPROVED` prefix) and no
    `SPEC-CONFORM`/`BLAST-RADIUS` line present →
    `APPROVED` **and** `APPROVED WITH NOTES` → `Verdict.PASS`
    (notes are advisory, not a block — L110 groups both as non-`CHANGES
    REQUIRED` outcomes), `CHANGES REQUIRED` → `Verdict.FAIL`.
  - **Any ambiguity across shapes** — no recognised verdict line of any of the
    three grammars; a mix of grammars (e.g. an `APPROVED` token *and* a
    `SPEC-CONFORM` line, or one hardened line present but not its pair); a
    required line missing; or any token absent/duplicated →
    `Verdict.NEEDS_HUMAN` (fail-closed, P2). Fail-closed on a genuinely
    ambiguous mix; the third shape closes the *false*-ambiguity gap where a
    clean standard-quality `APPROVED` was previously unrecognised.
- **Which shape applies is confirmable from the transcript's own grammar, not a
  guess:** each of the three shapes has a *distinct, non-overlapping* verdict
  grammar (`SPEC-CONFORM`+`BLAST-RADIUS`; lone `SPEC-CONFORM`; lone
  `APPROVED`/`CHANGES REQUIRED`), so the judge recognises whichever grammar is
  present without needing to be told the path. If more than one grammar's tokens
  co-occur (a genuinely contradictory transcript) it fails closed to
  `NEEDS_HUMAN` rather than assuming. The caller *may* additionally pass which
  path ran to tighten this (a documented follow-on), but it is not
  first-slice-required now that all three emitted grammars are recognised.
- **Honest note on the `APPROVED WITH NOTES → PASS` mapping.** Mapping
  `APPROVED WITH NOTES` to `Verdict.PASS` treats advisory notes as non-blocking,
  consistent with `quality-reviewer.md` L110 grouping it with `APPROVED` (both
  distinct from `CHANGES REQUIRED`). Should the operator later want notes to
  route to `NEEDS_HUMAN` for human eyes, that is a one-line grammar change and a
  *possible* future material decision — flagged, not silently decided (see
  report). For this slice the honest reading of the agent contract is
  notes-are-advisory → `PASS`.

### Provenance binding (caller responsibility; honesty-labelled)

For `spec_review_judge`/`quality_judge`, the caller must source the transcript
from a handle/path **bound to the reviewer delegation** (not the acting agent's
return), and bound to the current `pipeline_id`/state (reuse the bridge
freshness pattern where practical). For `test_judge`, the caller must source the
exit code from an **actual test run** it invoked. Pre-Seam-7 this binding is
**hook-scoped / not boundary-closed** — honesty-labelled exactly as the driver's
own trust is (`engine-wire-in.md`, `s2-g1-closure.md`). The keyed+fresh marker
over the artifact (D2c and its `TEST` analogue) is the **maturity target, not a
first-slice requirement**.

### Edge cases (all → `Verdict.NEEDS_HUMAN`, fail-closed)

- Empty / `None` / whitespace-only transcript.
- No recognised verdict line.
- Multiple conflicting verdict lines.
- `"PASS"`/`"FAIL"` appearing only inside unrelated prose (not on its own
  anchored line) — must NOT match.
- Wrong-role-produced transcript — **known limitation:** pre-S-2 the judge
  cannot structurally verify the transcript's *origin role*; it trusts the
  caller's provenance binding, which is hook-scoped, not boundary-enforced.
  Flagged honestly (Stress-test §, Design Principles).
- `test_judge`: exit code `None` (unavailable / timed-out).

---

## Link (validated before building)

- **`Judge` alias + signature** — confirmed at `engine/__init__.py` L106; the
  new judges conform exactly.
- **`Driver.advance(judge=…)` injection seam** — confirmed at `driver.py`
  L212–251; `_trivial_completion_judge` is the default (L214), so injecting a
  real judge leaves every existing default-path test untouched. Confirmed the
  brainstorm's "already built" claim.
- **Interface-stub-before-tests ownership** — the minimal `judges.py` stub
  (Assemble step 0) is created by **`gleipnir-code`**, the SAME role bound to
  both the `test` and `code` stages (`../stage-role-map.md`: `test` →
  `gleipnir-code`, `code` → `gleipnir-code`). Confirmed this requires **NO new
  role and NO new bookkeeping** — it is a small addition to the ordering (a
  stub file authored at the head of the stage `gleipnir-code` already runs),
  consistent with the operator-converged option's stated rationale. The stub
  exists solely so `import gleipnir.engine.judges` resolves at pytest
  **collection** time; its `NotImplementedError` bodies are replaced with the
  real factory implementations in the `code` stage (Assemble 1b–3b). The
  `raise NotImplementedError` convention documents the same fail-closed-stub
  intent as the **stale** comment header at `engine/__init__.py` L266 — which,
  verified on disk, no longer describes `Engine`'s current (fully-implemented,
  49/49-passing) state and is not a currently-followed codebase pattern; the
  choice stands on its own fail-closed merits regardless.
- **`TRANSITIONS`, revert budget, `Verdict`** — confirmed unchanged and
  sufficient: a `Verdict.FAIL` from any of the three judges routes through the
  **existing** revert edges (`SPEC_REVIEW→PLAN` L158, `TEST→SPEC_REVIEW` L166,
  `QUALITY→CODE` L177) and increments the single global `revert_count`
  (L411–432). **No budget redesign.**
- **`bin/gleipnir-sandbox test -- --collect-only` exit-code contract** —
  confirmed: `test` returns pytest `proc.returncode` (`sandbox/__main__.py` L98)
  and exits with it (L263); passthrough tokens are appended
  `[*base_cmd, *coverage_args, *extra]` (L120–144); the live `python` profile
  sets `test_selector_prefix = true` (`.gleipnir/sandbox/profiles.toml` L19–26,
  `test = ["python","-m","pytest","-p","no:cacheprovider"]`), so
  `test -- --collect-only` yields `pytest … --collect-only`. `--collect-only`
  exits 0 on valid/collectible test files, non-zero on collection/syntax error —
  **independent of whether the assertions would pass against not-yet-written
  code.** This is the correct mechanical arbiter for `test_judge` at the
  `TEST→CODE` edge (test-authoring validity, reconciled against the
  `TEST --FAIL--> SPEC_REVIEW` semantics at `engine/__init__.py` L128–132,
  L163–166). Full assertion-level pass/fail is deferred to `code`/`quality`,
  where the implementation exists (Axiom 1).
- **`attempt_gate`/`GATE`/G-3.2** — confirmed OUT OF SCOPE: this slice never
  calls `attempt_gate` and never reaches `GIT→GATE` (GIT has no `PASS` edge;
  the judges act on `SPEC_REVIEW`/`TEST`/`QUALITY` only). Untouched and
  unreached.
- **Cognition-layer composition** — confirmed `decisions/cognition-layer.md`
  posture ("review, not a guard, orthogonal to G-5"): the judges *consume* the
  reviewer's verdict; they do not replace the rubric or become a new guard, so
  no G-5 amendment (L-C14 phantom-subsumption gap pre-empted).
- **stdlib-only core** — confirmed the LLM client / subprocess reader are
  injected callables at the caller edge; `judges.py` imports only stdlib (`re`,
  `typing`) + `engine`'s `Verdict`/`PipelineState`/`Judge` types.

### Interactions with existing machinery — NONE of it changes

`Engine.step(judge, payload)`, the global `revert_count`, the `TRANSITIONS`
table, and the human gate are **all unchanged**. This plan adds only new `Judge`
implementations and their injection; it never edits `engine/__init__.py`'s
routing/budget logic. A real judge changes *what produces* the `Verdict`, never
*how the `Verdict` routes*. `attempt_gate`/`GATE`/G-3.2 remain completely out of
scope and untouched.

---

## Assemble (build order)

Build order runs test-first (the `test` stage authors tests before `code`).
Ordering rationale: **`test_judge` first** — its artifact (an integer exit code)
is the simplest to source and fake, so it proves the factory/injection shape and
the `NEEDS_HUMAN` fail-closed path with the least parsing surface; the two
transcript-parsing judges then reuse that proven shape.

0. **Interface-stub step (standard TDD Red-Green-Refactor; runs at the START of
   the `test` stage, before test authoring).** Create a **minimal stub**
   `src/gleipnir/engine/judges.py` containing the three factory signatures
   `make_spec_review_judge`, `make_quality_judge`, `make_test_judge` (exact
   names/shapes per the Trace "Design shape (P1)" §), each with a body that
   `raise NotImplementedError`. **Convention choice — `raise NotImplementedError`,
   not `pass`/placeholder:** it is the fail-closed-correct form for this plan —
   a stub accidentally left in flight can never silently return a fake `Verdict`;
   it explodes loudly instead. A stale comment header at
   `src/gleipnir/engine/__init__.py` L266 ("Stub: every method raises
   NotImplementedError") documents the same fail-closed-stub *intent* this plan
   independently adopts for its own reasons — though that header is **no longer
   descriptive** of `Engine`'s current state (verified on disk: the `Engine`
   class immediately below it is fully implemented, its own docstring records
   "the suite passes 49/49 against this implementation", and no method raises
   `NotImplementedError`). The choice here is correct regardless of whether it
   reflects a currently-live codebase pattern: a stub that explodes loudly on
   any accidental call, rather than silently returning a fake `Verdict`, is the
   right fail-closed choice on its own merits. **Why before test authoring, not concurrent:** the
   stub must exist *first* so `import gleipnir.engine.judges` resolves at pytest
   **collection** time. Collection only imports the module (evaluates the `def`
   statements); it never *calls* the factories, so the `NotImplementedError`
   bodies do not fire during collection. This makes `test_judge`'s
   `bin/gleipnir-sandbox test -- --collect-only` check exit 0 (collection
   succeeds) rather than erroring on `ModuleNotFoundError`/`ImportError` — closing
   the exact dogfooding revert-loop the second re-review flagged (a freshly
   authored `tests/test_judges.py` importing a not-yet-created module would fail
   collection, tripping the `TEST→SPEC_REVIEW` revert independent of
   `--collect-only`). The stub is then fleshed out into the real implementation
   across steps 1b–3b of the `code` stage — the standard Red (stub + failing
   tests) → Green (real bodies) progression. No new role or new bookkeeping: the
   stub is created by `gleipnir-code`, which already owns both the `test` and
   `code` stage bindings (see Link).

   **Deferred-call requirement (MANDATORY — closes the collection-time
   `NotImplementedError` variant).** The reasoning above ("collection only
   imports the module; it never *calls* the factories") holds **only if** every
   `make_spec_review_judge(...)` / `make_quality_judge(...)` /
   `make_test_judge(...)` invocation in `tests/test_judges.py` and
   `tests/test_judges_live.py` occurs **inside a test function or fixture body**
   (the primary, load-bearing requirement) — and **never in any expression
   evaluated at module-import/collection time, by whatever pytest mechanism —
   including but not limited to module top-level statements, class-body attribute
   assignments in a `Test*` class, `@pytest.mark.parametrize` /
   `@pytest.fixture(params=...)` argument-list construction, and
   default-argument-value expressions in a `def` signature; only code that
   executes when the test/fixture body is actually invoked by pytest at runtime
   is permitted.** (The enumeration is illustrative/exhaustive-by-example; the
   affirmative "inside a test function or fixture body" clause is the mechanism
   of enforcement.)
   `pytest --collect-only` imports each test module *and* evaluates module-scope
   expressions (including the argument values passed to `parametrize`
   decorators), so a factory call sitting at module scope — e.g. a
   `CASES = [(make_test_judge(lambda: 0), Verdict.PASS), …]` table built for
   `@pytest.mark.parametrize` — would **call** the stub factory at collection
   time, firing its `NotImplementedError` body and reproducing the exact
   collection-failure class this step exists to close (via
   `NotImplementedError` instead of `ImportError`). If parametrization over
   judge instances is wanted, **parametrize over the factory's INPUT ARGUMENTS**
   (the fake exit code, the fake transcript string) and call the
   `make_*_judge(...)` factory **inside the test-function body**, e.g.
   `@pytest.mark.parametrize("exit_code,expected", [(0, Verdict.PASS), (1,
   Verdict.FAIL), (None, Verdict.NEEDS_HUMAN)])` then
   `judge = make_test_judge(lambda: exit_code)` on the first line of the test
   body. This authoring rule is enforced by the `test`-stage review (the
   `quality-reviewer` pass over the authored test file; see Execution Workflow
   step 3 and the Stress-test row below).
   **Fixture-asset loading follows the same rule (lower severity).** Any
   fixture-asset load — e.g. reading a captured reviewer transcript file for
   `tests/test_judges_live.py` — should likewise occur **inside a test/fixture
   body**, not at module top level, for the same collection-time-safety reason:
   a missing fixture file read at module scope would raise at collection,
   reproducing the collection-failure class (an asset read instead of a factory
   call). This is **lower-severity than the factory-call case** because it
   already fails safely — `test_judge` only observes `--collect-only`'s exit
   code and maps non-zero → `Verdict.FAIL` (never a false PASS), so even an
   uncaught instance fails closed, not green — so it is a one-line note rather
   than a new blocking risk.

1. **`test_judge` (simplest artifact — a collection-only exit code).**
   1a. *Tests (fakes):* `make_test_judge(lambda: 0)` → `PASS` (tests collected
       cleanly); `lambda: 1` (and other non-zero) → `FAIL` (collection/syntax
       error); `lambda: None` → `NEEDS_HUMAN`. Assert payload-blindness (same
       verdict for a sentinel payload as an empty one). The judge maps
       `int|None → Verdict` and is agnostic to *which* command produced the int;
       the collection-only semantics live in the caller running
       `test -- --collect-only`, so the fakes are plain integers.
   1b. *Code:* implement the factory closure mapping `int|None → Verdict`.
2. **`spec_review_judge` (single-line grammar).**
   2a. *Tests (fakes):* fake transcript strings — clean `SPEC-CONFORM: PASS` →
       `PASS`; `SPEC-CONFORM: FAIL` → `FAIL`; empty/`None`/no-line/multi-line/
       `"...PASS..."`-in-prose → `NEEDS_HUMAN`.
   2b. *Code:* anchored-regex parser + fail-closed default.
3. **`quality_judge` (THREE grammars: hardened two-pass + light-path + standard
   quality verdict).**
   3a. *Tests (fakes):* (i) **hardened** — both-pass hardened transcript →
       `PASS`; either-`FAIL` → `FAIL`; one-hardened-line-missing → `NEEDS_HUMAN`.
       (ii) **light-path** — lone `SPEC-CONFORM: PASS`/`FAIL` (no `BLAST-RADIUS`)
       → correct `Verdict`. (iii) **standard quality verdict** — lone
       `APPROVED` → `PASS`; lone `APPROVED WITH NOTES` → `PASS`; lone
       `CHANGES REQUIRED` → `FAIL` (assert `APPROVED WITH NOTES` matches before
       the `APPROVED` prefix). (iv) **cross-grammar ambiguity** — an `APPROVED`
       token co-occurring with a `SPEC-CONFORM` line, or any mixed/duplicated/
       missing form, empty/`None`/prose-only → `NEEDS_HUMAN`. Include a fixture
       modelled on THIS plan's own clean non-enforcement `quality` pass (a lone
       `APPROVED`) → assert `PASS`, the exact false-ambiguity case the review
       flagged.
   3b. *Code:* the shared `_parse_verdict_line` helper plus (a) require both
       hardened lines when a `BLAST-RADIUS` line is present, (b) recognise the
       lone `SPEC-CONFORM` light-path line, (c) recognise the lone
       `APPROVED`/`APPROVED WITH NOTES`/`CHANGES REQUIRED` standard-quality line;
       any co-occurrence across grammars or missing/duplicated token →
       fail-closed default (`NEEDS_HUMAN`).
4. **Live/integration tests (`tests/test_judges_live.py`), clearly labelled.**
   - Inject a **real** reader over a real (fixture-captured) reviewer transcript
     with a real `SPEC-CONFORM: PASS`/`FAIL` line → assert the correct `Verdict`
     (contract only). A malformed real input → `NEEDS_HUMAN`.
   - For `test_judge`: a **fixture-only** exit code — a captured/constructed
     integer (`0` / non-zero) → correct `Verdict`. **Pinned to fixture-only (not
     a live-invoked `bin/gleipnir-sandbox test -- --collect-only`)** because the
     live tests may themselves run *inside* the S-2 sandbox container
     (`--network=none`, no nested-container access), where spawning the sandbox
     command is likely infeasible; the contract under test is `int → Verdict`
     mapping, which a fixture integer exercises fully without needing a real
     nested invocation. Real end-to-end invocation of the collection command is
     the harness/Seam-7 caller's job, out of scope here.
   - **Never assert on LLM prose content** — only that a real transcript's
     verdict line routes to the correct `Verdict`, and malformed → `NEEDS_HUMAN`.
   - Seam-7 (live hook) and Seam-8 (real CI attestation) markers present as
     **not-claimed** (mirroring `test_armed_run_dogfood.py` L10–20 discipline).
5. **Verify non-touch:** `git diff` shows `engine/__init__.py` and `driver.py`
   unchanged; full suite green.

No edit to `engine/__init__.py` or `driver.py` at any step — the judges are
injected *into* `advance` by tests/harness, not wired *inside* the driver.

---

## Stress-test (acceptance checks — adversarial, `DESIGN.md`-style)

Mirroring `DESIGN.md`'s Stress-test table. `[D]` = tool-produced evidence,
`[J]` = judgment.

| Adversarial case | Required behaviour | Judge(s) | Evidence |
|---|---|---|---|
| Transcript with `"PASS"` inside unrelated prose (e.g. "the PASS/FAIL policy is…"), no anchored verdict line | Must NOT match; → `NEEDS_HUMAN` | spec_review, quality | Unit test with prose-only fixture asserts `NEEDS_HUMAN` [D] |
| Anchored verdict line present exactly once | Maps to the correct `Verdict` | spec_review, quality | Unit test [D] |
| Two conflicting verdict lines (`PASS` and `FAIL`) | Ambiguous → `NEEDS_HUMAN` (never "first wins") | spec_review, quality | Unit test [D] |
| Empty / `None` / whitespace-only transcript | → `NEEDS_HUMAN` | spec_review, quality | Unit test [D] |
| Hardened transcript missing one of the two pass lines | → `NEEDS_HUMAN` (both required) | quality | Unit test [D] |
| Transcript claiming PASS but produced by the WRONG role | **KNOWN LIMITATION (honest):** pre-S-2 the judge cannot structurally verify origin role; it trusts the caller's hook-scoped provenance binding. NOT detected structurally by this slice; flagged, not claimed closed. | spec_review, quality | Provenance is caller-bound + hook-scoped, honesty-labelled; keyed-marker (D2c) is the maturity step [J] |
| Freshly-authored tests fail ASSERTIONS against not-yet-written code (correct test-first) | Must NOT `FAIL`: `test_judge` observes `--collect-only`, which exits 0 on valid collection regardless of assertion outcome → `PASS` → advance to `CODE` | test | Unit test: collection exit `0` → `PASS` [D]; reconciled to `TEST→SPEC_REVIEW` semantics `engine/__init__.py` L128–132, L163–166 [J] |
| Freshly-authored `tests/test_judges.py` `import gleipnir.engine.judges` where the module does not yet exist (this plan's OWN dogfooding, since `pyproject.toml` `testpaths = ["tests"]` makes `--collect-only` collect the whole tree) | Interface-stub step (Assemble 0) creates a minimal `judges.py` **before** test authoring, so `import` resolves to the stub at collection time and `--collect-only` exits **0**; any `NotImplementedError` raised by the stub bodies fires only at assertion RUNTIME (never during collection), and runtime assertion failures are irrelevant to `test_judge` (it checks collection only) → transition correctly proceeds to `CODE`, where the stub is fleshed out into the real implementation | test | Assemble step 0 creates the stub; collection succeeds because imports resolve [J]; the `raise NotImplementedError` stub body documents the same fail-closed-stub intent as the **stale** comment header at `engine/__init__.py` L266, which no longer describes `Engine`'s current fully-implemented (49/49-passing) state and is not a currently-followed pattern — the choice stands on its own fail-closed merits [D]; `pyproject.toml` `testpaths = ["tests"]` verified (L18) [D] |
| A `make_*_judge(...)` factory call placed in ANY expression evaluated at module-import/collection time in `tests/test_judges.py`/`tests/test_judges_live.py` — including but not limited to a module top-level statement, a class-body attribute assignment in a `Test*` class, an `@pytest.mark.parametrize` / `@pytest.fixture(params=...)` argument-list value, or a default-argument-value expression in a `def` signature | Must NOT occur: any such call is **evaluated at collection time**, firing the stub's `NotImplementedError` during `--collect-only` and defeating the Assemble step 0 stub fix (the `NotImplementedError` variant of the collection-failure class). Guarded by the Assemble step 0 / Execution Workflow step 1 authoring rule — the load-bearing requirement is that every factory call occurs INSIDE a test/fixture body (only code invoked when the test/fixture body actually runs is permitted); parametrize over the factory's input arguments, not over built judge instances — plus the `test`-stage `quality-reviewer` review of the authored test file | test | Authoring rule mandated in Assemble step 0 + Execution Workflow step 1 [J]; enforced at the `test`-stage spec-review/quality pass over the test file (Execution Workflow step 3) [J]; `pytest --collect-only` imports each module and evaluates module-scope expressions (parametrize/fixture-params argument values, class-body assignments, def default-argument expressions) at collection time [J] |
| Test process hangs / times out (during collection) | Injected reader applies timeout, returns `None`; judge → `NEEDS_HUMAN` | test | Unit test with `lambda: None` [D]; timeout at caller edge [J] |
| Collection/syntax error (non-zero `--collect-only` exit) | → `Verdict.FAIL` = "spec/plan inadequate to author loadable tests" → routes the existing `TEST→SPEC_REVIEW` revert edge, increments global budget (unchanged machinery) | test | Unit test [D]; revert routing already covered by engine suite [D] |
| Collection exit code zero | → `Verdict.PASS` | test | Unit test [D] |
| Non-zero `--collect-only` exit caused by a sandbox-wrapper-level refusal (profile misconfiguration, extra pytest args to a profile without `test_selector_prefix`, or an infra/container-start failure) rather than a genuine pytest collection/syntax defect | **KNOWN LIMITATION (honest):** a non-zero `--collect-only` exit conflates a genuine pytest collection defect with a sandbox-wrapper-level refusal (profile misconfiguration or infra/container failure, `sandbox/__main__.py` L118 / L121–128 / L154–156, all returning exit 3). This first slice does not distinguish them; both map to `Verdict.FAIL`, which is safe-direction (never false-PASS) but can consume `TEST→SPEC_REVIEW` revert budget on infra noise unrelated to test-authoring quality — and at the budget ceiling force a spurious `ESCALATED`. NOT required to fix for this slice; flagged, not claimed closed. | test | `sandbox/__main__.py` exit-3 paths L118/L121–128/L154–156 [D]; single monotonic `revert_count` (unchanged) means transient infra flakiness on this exact command burns revert slots [J] |
| Standard non-enforcement `quality` review emits a lone `APPROVED` (THIS plan's own quality stage) | Recognised (third grammar) → `Verdict.PASS`; must NOT fall into ambiguity → `NEEDS_HUMAN` | quality | Unit test: lone `APPROVED` → `PASS` [D]; grammar per `../agents/quality-reviewer.md` L105–111 [J] |
| Cross-grammar mix (e.g. `APPROVED` token AND a `SPEC-CONFORM` line together) | Genuinely contradictory → `NEEDS_HUMAN` (fail-closed) | quality | Unit test [D] |
| Judge returns a non-`Verdict` value | Engine raises `InvalidVerdict` (existing behaviour) — our judges only ever return `Verdict` members | all | Type-return assertion in unit tests [D]; `engine/__init__.py` L393–396 [D] |
| Payload contains injected `"skip review"` text | Judge ignores `payload` (derives verdict only from injected artifact); router never inspects `payload` | all | Payload-blindness unit test [D]; `DESIGN.md` Trace §, `engine/__init__.py` L101–106 (Judge alias comment: "The router NEVER inspects `payload`") [D] |
| `engine/__init__.py` altered | Must be UNCHANGED | — | `git diff` names zero lines in that file [D] |
| `attempt_gate`/`GATE` reached | Never — this slice does not call `attempt_gate` | — | No `attempt_gate` call in `judges.py`/its tests [D] |

**Acceptance = all of the above pass, the full existing suite stays green, and
`engine/__init__.py` + `driver.py` are unmodified.**

---

## Execution Workflow

For the implementing agents (`gleipnir-code` for `test` then `code`;
`quality-reviewer` for `quality`; `git-ops` for `git`):

1. **`test` stage (gleipnir-code).** **FIRST, create the minimal interface stub
   `src/gleipnir/engine/judges.py`** per Assemble step 0 — the three factory
   signatures (`make_spec_review_judge`, `make_quality_judge`, `make_test_judge`)
   with `raise NotImplementedError` bodies — so `import gleipnir.engine.judges`
   resolves at pytest **collection** time. THEN author `tests/test_judges.py`
   (fakes) and the labelled `tests/test_judges_live.py`, per Assemble steps
   1a–3a, 4. **Every `make_*_judge(...)` call in both test files MUST occur
   inside a test-function or fixture body (the primary, load-bearing
   requirement) — never in any expression evaluated at module-import/collection
   time, by whatever pytest mechanism, including but not limited to module
   top-level statements, class-body attribute assignments in a `Test*` class,
   `@pytest.mark.parametrize` / `@pytest.fixture(params=...)` argument-list
   construction, and default-argument-value expressions in a `def` signature;
   only code that executes when the test/fixture body is actually invoked by
   pytest at runtime is permitted (parametrize over the factory INPUT ARGUMENTS
   and call the factory inside the test body instead)**, per the Assemble step 0
   deferred-call requirement; otherwise the stub's `NotImplementedError` fires at
   collection time and defeats the stub fix.
   Tests define correctness (Axiom 1). Live tests assert contract only,
   never LLM prose. Run the suite via `bin/gleipnir-sandbox test` during
   authoring. (Note: the full-suite run here is the developer's own feedback
   loop; it is NOT what `test_judge` consumes — `test_judge` observes the
   **collection-only** exit code of `bin/gleipnir-sandbox test -- --collect-only`,
   per the `test_judge` Trace §. The stub guarantees that collection succeeds
   even though the real implementation does not land until the `code` stage.)
2. **`code` stage (gleipnir-code).** Flesh out the `src/gleipnir/engine/judges.py`
   stub (created in step 1) — replace each `NotImplementedError` body with the
   real parameterized-factory implementation (`make_spec_review_judge`,
   `make_quality_judge`, `make_test_judge`) per Assemble steps 1b–3b. Import only
   stdlib + `engine` types. Do NOT edit `engine/__init__.py` or `driver.py`. Make
   the pre-written tests pass (Red → Green).
3. **`quality` stage (quality-reviewer).** `P` here is `src/**` + `tests/**`
   (NOT an enforcement path under `E`, no grant/`G`-pattern), so this is NOT the
   two-pass hardened review; it runs the **full pipeline's** standard `quality`
   blast-radius review (SOLID/DRY dimension + the honour check: does the
   implementation honour the Design Intent below?). Per
   `../agents/quality-reviewer.md` L105–111 this review ends with the mandated
   verdict token **`APPROVED` / `APPROVED WITH NOTES` / `CHANGES REQUIRED`** —
   which is exactly the third grammar `quality_judge` now recognises (see the
   `quality_judge` Trace §), so a clean pass here maps to `Verdict.PASS`, not
   `NEEDS_HUMAN`. Confirm `engine/__init__.py`/`driver.py` untouched
   (`git diff`).
4. **`git` stage (git-ops).** Sole broker; commits after gate conditions.
5. Any parse/grammar ambiguity discovered during implementation that is NOT
   covered by the pinned grammar → route to `NEEDS_HUMAN` (never widen the
   grammar to guess); if it looks like a *material* grammar tradeoff, escalate
   to the operator (do not decide it in code).

---

## Design Principles (Gate-1 cognition layer — case (i): OOP/functional code)

`P ∩ X ≠ ∅` (touches `src/**`, `tests/**`) and the touched `X`-members have
function/module structure → **full SOLID + DRY + SRP + Design Intent**.

### SOLID analysis

- **Single Responsibility.** Each judge closure has exactly one reason to
  change: the *verdict grammar / mapping* for its transition. Artifact *sourcing*
  (I/O, subprocess, timeout, provenance binding) is a separate responsibility
  living in the injected reader at the caller edge — it changes for I/O reasons,
  not grammar reasons. Two reasons, two homes.
- **Open/Closed.** Adding a fourth judge (or a bespoke reviewer-less judge, D4
  option a, later) extends `judges.py` with a new factory function; it does not
  modify existing judges, `driver.py`, or `engine/__init__.py`. The `Driver.advance(judge=…)`
  seam is already open for extension (any `Judge` plugs in) and closed for
  modification.
- **Liskov Substitution.** Every judge is substitutable for
  `_trivial_completion_judge` wherever a `Judge` is expected — same signature,
  same `Verdict`-only return contract, honoured by `Engine.step`. A real judge
  never returns a non-`Verdict` (which would break the parent contract and raise
  `InvalidVerdict`).
- **Interface Segregation.** The `Judge` interface is already narrow
  (`(PipelineState, Mapping) -> Verdict`). The injected reader interface is
  equally narrow: `() -> str | None` (transcript) or `() -> int | None` (exit
  code) — a judge depends only on the one reader it needs, not a fat "artifact
  service".
- **Dependency Inversion.** The judges (higher-level: verdict policy) depend on
  an abstraction (an injected callable), not on a concrete filesystem/subprocess/
  LLM client. The concrete I/O is supplied at the caller edge. This is why the
  stdlib-only engine core stays free of I/O.

### DRY analysis

- Shared verdict-line parsing (anchored `^TOKEN:\s+(PASS|FAIL)\s*$` matching,
  the fail-closed default, and the `PASS/FAIL`→`Verdict` mapping) lives in **one
  internal helper** reused by `spec_review_judge` and `quality_judge`'s
  `SPEC-CONFORM`/`BLAST-RADIUS` line handling — not copy-pasted per judge. This
  is the reason P1 chose a factory module over three standalone bodies.
  `quality_judge`'s third grammar (the standard-quality `APPROVED`/`APPROVED
  WITH NOTES`/`CHANGES REQUIRED` token) is a small additional anchored-regex
  branch layered on the same helper's fail-closed discipline, not a duplicated
  parser.
- The `PASS/FAIL`/`NEEDS_HUMAN` tokens and the regex are named constants, not
  repeated literals.
- No duplication of engine logic: routing/budget stay in `engine/__init__.py`;
  the judges reuse the existing `Verdict` enum, never redefine verdict values.

### Single Responsibility check (per component)

- `make_test_judge` → the one responsibility: map a mechanical exit code to a
  `Verdict`.
- `make_spec_review_judge` → map a spec-review verdict transcript to a `Verdict`.
- `make_quality_judge` → map a quality (two-pass or light) verdict transcript to
  a `Verdict`.
- internal `_parse_verdict_line` helper → the one responsibility: anchored-line
  extraction of a single `PASS/FAIL` token, fail-closed.
- (injected readers, at the caller edge) → the one responsibility: source the
  artifact; NOT a judge concern.

### Design Intent (specific, falsifiable — the genuineness proxy)

**Each judge is a pure function of (its already-sourced, independently-produced
artifact) → `Verdict`, with (a) no engine-state mutation, (b) no
network/filesystem/process I/O inside `engine/`'s stdlib-only core — all I/O is
performed by an injected reader at the caller/harness edge, and (c) no read of
the acting agent's self-reported narrative — the only inputs are the injected
reviewer transcript (`SPEC_REVIEW`/`QUALITY`) or the mechanical exit code
(`TEST`); every unparseable/missing/ambiguous/timed-out artifact maps to
`Verdict.NEEDS_HUMAN`.**

This is falsifiable: a reviewer can point to a *violation* if the implementation
(i) imports `subprocess`/`socket`/`urllib`/an LLM SDK or opens a file inside
`judges.py` or `engine/`; (ii) reads `payload` to derive its verdict; (iii)
mutates any `Engine`/`Driver` state; (iv) coerces a parse-miss to `PASS`/`FAIL`
instead of `NEEDS_HUMAN`; or (v) edits `engine/__init__.py`/`driver.py`. Any one
of these is a concrete, checkable breach of the stated intent — not a generic
"clean code" aspiration.

---

## Validation (self-check against `plan-format.md`)

- Decisions (index) table: **present** (D1–D4, D2-add, P1–P3).
- Architect / Trace / Link / Assemble / Stress-test / Execution Workflow:
  **all present.**
- Interface-stub-before-tests step (standard TDD Red-Green-Refactor, operator-
  converged fix for the collection-time `ImportError` dogfooding defect):
  **present** as Assemble step 0, Link ownership bullet (`gleipnir-code`, no new
  role/bookkeeping), Stress-test row, and Execution Workflow step 1.
- Deferred-call requirement (closes the collection-time `NotImplementedError`
  variant — every `make_*_judge(...)` call in the test files must be inside a
  test/fixture body, never at module scope or in an eager `parametrize` table):
  **present** as the MANDATORY block in Assemble step 0, Execution Workflow
  step 1, and a dedicated Stress-test row.
- Design Principles: **present, case (i)** — SOLID + DRY + SRP + a specific,
  falsifiable Design Intent (not a quality aspiration).
- Stress-test lists concrete checkable acceptance criteria (not "it works").
- Every cited path verified to exist (`engine/__init__.py`, `driver.py`,
  `bin/gleipnir-sandbox`, `sandbox/__main__.py`, `DESIGN.md`,
  `test_armed_run_dogfood.py`) or explicitly marked **to be created**
  (`judges.py`, `test_judges.py`, `test_judges_live.py`).
