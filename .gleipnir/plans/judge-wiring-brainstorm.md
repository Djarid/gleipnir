# Design Brief: Wiring a real (LLM-backed) judge into the G-5 engine

**Stage:** brainstorm (owned by `gleipnir-brainstorm`). **Tier:** 0 (`plans/`,
disposable) — the only artifact this role writes. **Status: FULLY CONVERGED —
ready for `gleipnir-plan`.** All four Decision Analyses (D1–D4) **and** the one
NEW material tradeoff surfaced under D1's divergence (the `TEST`-transition
evidence class) are now **OPERATOR-CONVERGED**, via the orchestrator's
`question` tool (real convergence — the orchestrator surfaced the analyses to
the operator, who chose; not self-attested by this subagent). See the
**Selected Approach** section for the recorded choices and the **D2-addendum**
for the `TEST`-transition evidence-class resolution. **D1 diverged from the
recommendation** (operator chose Option D, not Option A) — the divergence and
its structural consequences are recorded in full below; the `TEST`-transition
gap it surfaced is now resolved (option (i): the mechanical test exit code as a
new, independent, non-narrative evidence class). Nothing in this brief remains
PENDING.

---

## Problem Statement

The G-5 deterministic engine (`src/gleipnir/engine/__init__.py`,
`driver.py`, `DESIGN.md`) routes on a `Judge = Callable[[PipelineState,
Mapping], Verdict]`, but the only judge wired today is
`_trivial_completion_judge` in `driver.py` (always `Verdict.PASS` on a clean
tool return, payload-blind). Engine tests validate only the **routing skeleton**
(revert budget, no-self-attestation channel, human gate, attestation-only GATE
edge) using synthetic fixed judges. Nothing yet proves the *system* makes a
correct real-world accept/reject call, because no real judge exists.

The engine's own DESIGN.md anticipates a judge "is free to be… a real LLM call"
— so an LLM-backed judge is the intended design, not a novelty. The missing
piece is the **wiring**: a `Judge`-shaped function, invoked by `Engine.step()`,
fed *real independently-produced artifacts*, that returns a genuine
`PASS/FAIL/NEEDS_HUMAN` — **without** reintroducing self-attestation, and
**without** requiring the full G-3.2 CI-attestation fetch (Seam 8), the G-4 bus,
and the S-2 boundary to all land first.

**The core tension.** If a judge-LLM is fed a *self-reported* payload (an agent's
own claim "tests passed"/"this is correct"), that is self-attestation with extra
ceremony — exactly what G-3 exists to prevent, and exactly what the whole
mechanical-observation design (`decisions/engine-state-bridge.md`,
`armed-run-dogfood.md` D1) was built to close. A genuine judge must evaluate
**real, independently-produced artifacts** (actual test exit codes; a *different*
subagent's transcript; a keyed marker), not the acting agent's narrative about
its own work.

**Seed observation (load-bearing).** In *this very orchestrator session*, an LLM
— the `quality-reviewer` subagent — has already been doing real judging at every
hardened-path stage: reading actual diffs/plans/files on disk and returning real
`SPEC-CONFORM: PASS/FAIL` and `BLAST-RADIUS: PASS/FAIL` verdicts, which the
orchestrator reads and routes on. So "an LLM capable of understanding the work
and deciding whether the step is complete" **already exists and already works**,
via `quality-reviewer` + orchestrator-as-router. The open question is purely how
to wire *that same kind of judgment* into the `src/gleipnir/engine/` code path
(the `Judge` invoked by `Engine.step()`), fed real artifacts, self-attestation-
free, incrementally.

---

## Constraints

- **No self-attestation (hard, load-bearing).** The judge input must not be the
  acting agent's own narrative about its own work. This is the invariant every
  prior engine/bridge/dogfood decision protects (`decisions/engine-state-bridge.md`
  item 3; `armed-run-dogfood.md` D1 "payload-blind… must NEVER read agent
  output"). A judge that reads a self-report is a regression, not a feature.
- **Do not contradict converged ground.** Global revert budget
  (`decisions/engine-revert-edges.md`), `GIT` has no `PASS` edge (GATE reached
  only via `attempt_gate` on a real `Attestation`), payload-blindness of the
  router, and the fail-closed posture are LOCKED. This brief builds *on* them.
- **Do not require Seam 7 / Seam 8 to land first.** `armed-run-dogfood.md`
  already named **Seam 7** (live `tool.execute.after` advance hook) and **Seam
  8** (real CI `Attestation` → `attempt_gate`, G-3.2 sourcing) as not-yet-built,
  multi-session dependencies. A first real-judge slice must be buildable without
  either, or it inherits their entire blast radius.
- **Determinism of the router is untouched.** The judge returns a `Verdict`
  enum; the router never inspects `payload`. A real judge changes *what produces
  the Verdict*, never *how the Verdict routes* (`DESIGN.md` "Trace").
- **The engine stays pure.** `engine/__init__.py` has no I/O, no LLM import, no
  filesystem. Any LLM call lives in the driver/caller layer or an injected judge
  object — never inside `Engine.step()` (mirrors the bus-emit seam discipline:
  the engine stays pure, the driver does I/O).
- **`NEEDS_HUMAN` is the only ambiguity escape hatch.** The engine already models
  it; a real judge must route ambiguity there, never invent a new path.
- **stdlib-only for the enforcement core** (`decisions/runtime-and-deps.md`). An
  LLM call is I/O at the driver/caller edge, not in the pure engine; any HTTP/SDK
  dependency must sit outside the stdlib-only core and be injected.
- **Testability without asserting LLM output.** A real LLM judge is
  non-deterministic; the plumbing (input sourcing, unforgeable-evidence
  provenance, `Verdict`-type contract, ambiguity→`NEEDS_HUMAN`) must be testable
  with fakes exactly as today, with a *small* number of clearly-labelled
  live/integration tests for the real judge.
- **Compose with the cognition layer, do not duplicate it.**
  `decisions/cognition-layer.md` is explicitly *review, not a guard*, orthogonal
  to G-5. A real engine judge must be reconciled against it (Decision 4), not
  built as a rival mechanism.

---

## Approaches Considered

The problem decomposes into **four material tradeoffs** (mapping to the
orchestrator's exploration prompts #1–#4). Rather than three monolithic
end-to-end approaches, the genuinely distinct design choices live at these four
decision points; each has its own `## Decision Analysis` below. The
"approaches" are the option-sets within each. Failure/ambiguity handling (#5)
and testability (#6) are cross-cutting constraints resolved in the analyses, not
separate tradeoffs (both have a single clearly-correct answer: reuse
`NEEDS_HUMAN`; keep fakes for plumbing + a few labelled live tests).

- **Decision 1 — Scope of the first real slice** (which transition(s), and
  "real but partial" vs waiting for the full G-3.2/G-4/S-2 stack).
- **Decision 2 — What counts as unforgeable-enough evidence for a first slice**
  (structural separation vs keyed marker vs combination).
- **Decision 3 — Where the judge call happens structurally** (in-process
  shell-out vs driver/caller-mediated vs deferred-hook), and how invoked without
  Seam 7.
- **Decision 4 — Relationship to the cognition-layer / `quality-reviewer`
  rubric** (new machinery vs formalise-what-exists vs both-at-maturity-stages).

---

## Decision Analysis 1 — Scope of the first real judge slice

**Decision type:** Prioritisation / go-no-go on a first buildable increment.
**Framework selected:** RICE Scoring (prioritisation across options) →
cross-checked with the Reversibility Filter (is a first slice a two-way door?).
Rationale: the question is "which of several buildable-now slices delivers the
most proven-real-judgment per unit effort without pulling in Seam 7/8," which is
exactly a reach/impact/confidence/effort ranking; the Reversibility Filter
confirms whether we can start narrow and widen.

**Reversibility pre-check:** Wiring a real judge for *one* transition, injected,
alongside the existing trivial judge, is a **Two-Way Door** — it adds a judge
object without removing the fixed-judge test path, and a later widening or
rescoping costs days, not a migration. → Fast-track eligible; deeper RICE used
only to *rank* the candidate first-slices, not to gate the go decision.

**Options (candidate first slices):**

- **A — `QUALITY → GIT`, fed the `quality-reviewer` transcript/verdict text as
  the artifact.** The one transition where a *different* subagent
  (`quality-reviewer`) has already produced an independent verdict on disk
  (a diff/plan review). The judge reads that transcript (not the acting agent's
  self-report) and maps it to `PASS/FAIL/NEEDS_HUMAN`. `attempt_gate` stays
  attestation-gated and untouched (GIT→GATE is unchanged; this is the
  `QUALITY→GIT` PASS edge, which already exists in `TRANSITIONS`).
- **B — `SPEC_REVIEW → TEST` / `SPEC_REVIEW → PLAN`,** fed the spec-review
  subagent's verdict. Structurally identical evidence story to A (a separate
  reviewer subagent), but at the spec-review stage, and it exercises a *revert*
  edge (FAIL→PLAN) as well as forward.
- **C — Wait: build no real judge until Seam 8 (real CI `Attestation`) and/or
  Seam 7 (live hook) land, then wire a real judge everywhere at once.**
- **D — All judged transitions at once** (spec-review, test, quality) in one
  slice, each fed its own independent reviewer artifact.

**RICE scores** (Reach = how many pipeline transitions/proof-value it unlocks;
Impact = how much it moves "system proven to make real accept/reject calls";
Confidence = how sure we are it is buildable now without Seam 7/8; Effort in
person-days, judgment estimates):

| Option | Reach | Impact | Confidence | Effort | RICE |
|---|---|---|---|---|---|
| A (`QUALITY→GIT`, reviewer transcript) | 2 | 3 | 90% | 3 | **1.80** |
| B (`SPEC_REVIEW` edges) | 3 | 3 | 80% | 4 | 1.80 |
| C (wait for Seam 8/7) | 5 | 3 | 30% | 20 | 0.23 |
| D (all judged transitions) | 6 | 3 | 55% | 9 | 1.10 |

A and B tie on RICE (1.80). The tie-breaker is **evidence maturity and blast
radius**: A targets the single transition where an independent artifact
(`quality-reviewer`'s verdict) *already exists on disk in this session* (the seed
observation), is a forward PASS edge (no revert-budget interaction to reason
about in the first slice), and leaves `attempt_gate` completely untouched. B is
an equally clean evidence story but additionally couples the first slice to a
revert edge (FAIL→PLAN increments the global budget), widening what the first
slice must prove. So A is the narrower, lower-blast-radius first cut with the
same score.

**Recommendation:** **Option A** — wire a real judge for `QUALITY → GIT` first,
fed the independent `quality-reviewer` artifact, keeping `attempt_gate`
attestation-gated and every fixed-judge test path intact. Treat B as the
immediate follow-on (same evidence pattern, adds the revert edge), D as the
end-state once A+B prove the pattern, and C as explicitly rejected as a first
slice (its 0.23 RICE reflects that waiting for Seam 8/7 buys nothing now and
blocks all proof for many sessions — the operator has flagged the *current*
absence as the critical gap).

**Bias warnings:**
- ⚠️ *Scope Creep Bias detected (on Option D):* "wire it everywhere at once"
  expands scope to avoid choosing the narrow first slice. The recommendation
  deliberately forces the narrow choice (A) and names B/D as *sequenced*
  follow-ons, not a single big-bang.
- ⚠️ *Status Quo Bias detected (on Option C):* "wait until the full stack lands"
  gives the do-nothing path a free pass. The RICE + the operator's own
  critical-gap flag apply equal scrutiny: C's low confidence (30%) is because it
  is blocked on two unbuilt multi-session seams, so "wait" is the *higher*-risk
  option here, not the safe one.
- (Also detected, not surfaced in full: Availability Heuristic — Option A is
  salient precisely because the `quality-reviewer` artifact is in front of us
  *this session*; noted so the operator can weigh whether that salience is
  representative. It is judged representative here because the artifact is a
  standing pipeline output, not a one-off.)

---

## Decision Analysis 2 — What counts as unforgeable-enough evidence for a first slice

**Decision type:** Architectural tradeoff with security consequences.
**Framework selected:** Weighted Decision Matrix (3 options across
security/cost/reuse criteria) → Pre-Mortem on the leading option. Rationale:
this is a multi-option comparison where the criteria (actual strength of
guarantee, complexity, reuse of built machinery, honesty of the claim) must be
weighed explicitly; a Pre-Mortem then stress-tests the winner because "evidence
that looks unforgeable but isn't" is the exact failure class here.

**Options:**
- **(a) Structural separation** — require the judge's input artifact to come from
  a *different* subagent invocation than the one whose work is being judged
  (mirrors today's `quality-reviewer` + orchestrator split; the acting agent
  cannot be the source of its own verdict).
- **(b) Keyed marker/digest** — the artifact is HMAC-signed over its content with
  the G-3.1 verifier key (`src/gleipnir/verify/marker.py`), and the judge (or its
  caller) validates the MAC before trusting it — reusing the exact mechanism the
  state bridge already uses.
- **(c) Combination** — structural separation **and** a keyed marker over the
  separate reviewer's artifact.

**Weighted matrix** (weights reflect: integrity > everything, then honesty of
claim, then cost/reuse; scores 0–10, cell = score×weight):

| Criterion | Weight | (a) Separation | (b) Keyed marker | (c) Combination |
|---|---|---|---|---|
| Actual strength of guarantee (first-slice, pre-S-2) | 10 | 6 → 60 | 5 → 50 | 8 → 80 |
| Honesty of the claim (no false "unforgeable") | 9 | 8 → 72 | 5 → 45 | 8 → 72 |
| Reuse of built machinery | 6 | 7 → 42 | 9 → 54 | 7 → 42 |
| Low complexity / small blast radius | 7 | 8 → 56 | 6 → 42 | 5 → 35 |
| Buildable now without Seam 7/8/S-2 | 8 | 9 → 72 | 7 → 56 | 7 → 56 |
| **Total** | | **302** | **247** | **285** |

**Recommended (matrix):** **(a) Structural separation** (302), with **(c)** a
close second (285) as the maturity target.

**Key caveat the matrix surfaces (why (b) alone scores lowest on honesty):** a
keyed marker proves *the artifact was not altered after signing* — it does **not**
prove the artifact was *independently produced*. If the *acting agent* could
cause its own self-report to be signed, the MAC makes a self-attestation
*tamper-evident*, not *non-self-attesting*. So (b) alone can produce a false
sense of "unforgeable" while leaving the actual G-3 hole (self-attestation) open.
The load-bearing property for *this* problem is **provenance/independence**
(who produced it), which is exactly what (a) delivers and (b) does not. (b)'s
value is integrity-in-transit, which composes on top of (a) — hence (c) as the
target, not (b) alone.

**Pre-Mortem on the leading option (a), assumed failed at 6 months:**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | "Different subagent" is enforced only by orchestrator prose, so a future path lets the acting agent's own output be relabelled as the reviewer's | M | H | The judge's caller must source the artifact from a path/handle bound to the *reviewer* delegation, not from the acting agent's return; record this as the invariant the wiring must structurally honour (pre-S-2 it is hook-scoped, exactly like the driver's own not-yet-closed trust, `engine-wire-in.md`). |
| 2 | Separation holds but the artifact is stale (a prior reviewer's verdict re-used for a new state) | M | M | Bind the artifact to the current pipeline_id/state (reuse the bridge freshness pattern) — this is where (b)'s keyed+fresh marker earns its place → motivates the (c) maturity target. |
| 3 | The claim is oversold as "unforgeable" when pre-S-2 it is only "independently-produced + hook-scoped" | M | H | Honesty-label it exactly as `engine-wire-in.md`/`s2-g1-closure.md` label the driver's own trust: *authored/hook-scoped, not yet boundary-closed*. Never claim G-3 closure from a first slice. |
| 4 | Structural separation adds a hidden dependency on Seam 7 (live hook) to know "which invocation was the reviewer" | L | H | The first slice sources the reviewer artifact out-of-band (Decision 3, Option 2) — a test harness / driver call passes the reviewer artifact path explicitly; no live hook needed. |

**Verdict:** Proceed with **(a)** for the first slice, honesty-labelled, with the
artifact bound to the reviewer delegation and to pipeline_id/state; adopt **(c)**
(add the keyed+fresh marker over the separate reviewer artifact) as the
maturity step once the first slice is proven. Reject **(b)-alone** as the
first-slice basis because it can mask, rather than close, the self-attestation
hole.

**Bias warnings:**
- ⚠️ *IKEA Effect detected (on (b)):* the keyed-marker machinery is ours,
  already built (G-3.1), and attractive to reuse — but reuse-because-we-built-it
  must not override the finding that a MAC proves integrity, not independence.
  Evaluate (b) as if someone else built it: it still does not close
  self-attestation on its own.
- ⚠️ *Confirmation Bias detected:* the seed observation (`quality-reviewer`
  already separates producer from judge) predisposes us to (a). The matrix
  deliberately scored (b) and (c) on the same criteria and named (a)'s failure
  modes (Pre-Mortem #1–#4) to seek counter-evidence rather than only confirming
  the separation story.

---

## Decision Analysis 2 — ADDENDUM: evidence class for the `TEST` transition (OPERATOR-CONVERGED)

**Why this addendum exists.** Working through D1's operator-chosen Option D
(all three judged transitions in one slice) surfaced a genuine NEW material
tradeoff that D2 never scored: **the `TEST` transition has no separate reviewer
role.** Per `stage-role-map.md`, `test` is bound to `gleipnir-code` — the SAME
role bound to `code` — so D2(a)'s structural-separation-by-different-subagent
(producer ≠ judge), which covers `SPEC_REVIEW` and `QUALITY` because a distinct
`quality-reviewer` produces those verdicts, does **not** apply to `TEST` for
free. This was flagged for the orchestrator and NOT resolved by this subagent.

**Operator convergence (via the orchestrator's `question` tool — real
convergence, not self-attested by this subagent).** The operator chose option
**(i): source a mechanical arbiter signal as the independent artifact for the
`TEST` transition.** Specifically:

> For the `TEST` transition, the judge's input is the **mechanical test-run exit
> code / result**, sourced **independently of any subagent's narrative** — i.e.
> the judge (or its caller) **runs or observes the actual test execution result
> directly** (e.g. via `bin/gleipnir-sandbox test`'s own process exit code),
> rather than trusting `gleipnir-code`'s self-report that "tests pass." The
> pass/fail that feeds the `TEST` judge is the objective outcome of *running the
> tests*, read from the mechanical result, never from the acting agent's prose.

**This satisfies the self-attestation concern via a DIFFERENT mechanism than
D2(a).** D2(a) closes self-attestation by **structural separation**: the
artifact is produced by a *different subagent role* than the one being judged
(the reviewer's verdict transcript for `SPEC_REVIEW`/`QUALITY`). The `TEST`
transition closes the SAME hole by a **different route**: the independence comes
not from a separate reviewer role, but from the artifact being a **mechanical,
non-narrative observation** — the actual exit code of executing the tests. There
is no narrative to trust and no producing-agent to collapse into the judged
agent, because the signal is *the machine's own record of what happened when the
tests ran*, not any agent's claim about it. Independence-by-mechanical-
observation, not independence-by-separate-reviewer.

**This is explicitly a NEW evidence class, distinct from D2's
separate-subagent-verdict class.** D2's matrix scored options (a)/(b)/(c) for
the *separate-subagent-verdict* case (spec-review/quality). The
**mechanical-exit-code-observation** class was never surfaced or scored there.
It is recorded here as a first-class, distinct member of the "independently-
produced artifact" family:

| Evidence class | Independence comes from | Applies to (this slice) |
|---|---|---|
| Separate-subagent verdict (D2(a)) | Producer is a *different role* (`quality-reviewer`) than the judged agent | `SPEC_REVIEW`, `QUALITY` |
| **Mechanical exit-code observation (this addendum)** | Artifact is a *non-narrative machine observation* (test-run exit code), not any agent's claim | `TEST` |

**Consistency with test-first Axiom 1.** The operator accepted this as fully
consistent with the test-first pipeline: **the test IS the arbiter** (Axiom 1,
`stage-role-map.md`). In test-first, correctness is defined by the pre-written
test's objective pass/fail, not by the model's capability or its narrative —
so consuming the mechanical test result as the `TEST` judge's input is not a
workaround, it is the *canonical* correctness signal for that transition. The
`TEST` judge formalises/consumes an arbiter signal that already exists
mechanically, exactly as D4(b) has the engine judge formalise the existing
review output rather than duplicate it.

**Honesty label (unchanged posture).** As with D2(a), the first slice's `TEST`
evidence is honesty-labelled: the mechanical exit code is a genuine independent
observation, but pre-S-2 its *sourcing path* (who invoked the sandbox, from
where) is hook-scoped / not-yet-boundary-closed — the same not-yet-closed trust
the driver itself carries (`engine-wire-in.md`, `s2-g1-closure.md`). The claim
is "independently-produced, mechanically-observed, hook-scoped," never "G-3
closed." The D2(c) keyed+fresh-marker maturity target applies here too (a keyed
marker over the mechanical result binds it to pipeline_id/state and makes it
tamper-evident) — a maturity step, not a first-slice requirement.

**Failure/ambiguity handling (unchanged).** A missing, unparseable, or timed-
out test result maps to `Verdict.NEEDS_HUMAN` (fail-closed), exactly as every
other ambiguous artifact does (D3). A clean non-zero exit is `Verdict.FAIL` and
routes through the unchanged global revert-budget machinery (see Selected
Approach). No new escape hatch.

---

## Decision Analysis 3 — Where the judge call happens structurally (and how invoked without Seam 7)

**Decision type:** Architectural tradeoff.
**Framework selected:** Second-Order Thinking (long-horizon structural
consequences) → Pros-Cons-Fixes on the leading option. Rationale: where the LLM
call lives has compounding downstream effects on engine purity, the stdlib-only
constraint, and whether the first slice drags in Seam 7 — second-order effects
are the crux.

**Options:**
- **1 — In-process Python judge that itself shells out to an LLM API.** A `Judge`
  callable inside the driver process makes the LLM call directly and returns a
  `Verdict`.
- **2 — Driver/caller-mediated, out-of-band judge invocation.** An explicit
  CLI/test-harness (or the driver's existing `advance(judge=…)` seam) constructs
  the judge, sources the *independent reviewer artifact* (Decision 2a) by path,
  invokes the LLM, and feeds the resulting `Verdict` into `Engine.step()`. The
  live `tool.execute.after` hook (Seam 7) is **not** required — the same
  out-of-band advance path `armed-run-dogfood.md` already uses (D1) carries the
  real judge instead of the trivial one.
- **3 — Defer entirely until the live hook (Seam 7) exists,** then invoke the
  judge only from the post-tool hook.

**Second-order analysis:**

*Option 1 (in-process shell-out judge):*
- Near term: fastest to a working real verdict; one function.
- Second-order: puts a network/SDK dependency and non-determinism *inside* the
  driver's judge path, and risks blurring the "engine stays pure / stdlib-only
  core" line if the judge is not cleanly injected. Every advance now potentially
  does network I/O.
- Far term: couples the judge lifecycle to the driver process; harder to test in
  isolation; the LLM dependency creeps toward the enforcement core.

*Option 2 (driver/caller-mediated, out-of-band):*
- Near term: reuses the *already-built* `Driver.advance(judge=…)` injection seam
  (confirmed in `driver.py` L212–251 and exercised by `armed-run-dogfood.md`).
  The real judge is just a different injected `Judge` object; the trivial judge
  stays the default.
- Second-order: the LLM call sits at the caller/harness edge (correct GOTCHA
  layering — I/O at the edge, pure engine at the core); testable with a fake
  judge exactly as today; **no dependency on Seam 7**; when Seam 7 lands, the
  hook simply becomes another caller of the same injected-judge path.
- Far term: the judge is a first-class injectable object with a stable contract
  — Seam 7 and a future resident-service model both consume it unchanged. This
  is the shape the existing code already reaches toward.

*Option 3 (defer to hook):*
- Near term: builds nothing; the critical gap the operator flagged stays open.
- Second-order/far term: couples the *first* real judge to Seam 7's entire
  blast radius — the exact coupling Constraint #3 forbids.

**Leading option: 2. Pros-Cons-Fixes:**

Pros:
- Reuses the built `advance(judge=…)` injection seam; the trivial judge remains
  the default so every existing test path is untouched.
- Keeps the LLM call at the caller/harness edge — engine stays pure, stdlib-only
  core preserved, non-determinism isolated to the injected object.
- Zero dependency on Seam 7 or Seam 8; when they land they reuse this contract.

Cons and Fixes:
| Con | Fix |
|---|---|
| Out-of-band invocation is not "live in a real session" yet | Honesty-label it exactly as the dogfood does (Seam 7 named, not claimed); the first slice proves the *judge wiring*, not live-session autonomy. |
| The judge object still needs a non-stdlib LLM client | Inject the client into the judge; keep it out of `engine/` and out of the stdlib-only *core* — the client lives at the caller/harness/driver-adapter layer, the same layer that already does bus/bridge I/O. |
| A real judge is non-deterministic — can't assert output in unit tests | Keep the fixed/fake `Judge` for all plumbing tests (input sourcing, provenance binding, `Verdict`-type contract, ambiguity→`NEEDS_HUMAN`); add a *small*, clearly-labelled live/integration test set that asserts the *contract* (returns a valid `Verdict`, routes correctly), never specific LLM prose. |

**Recommendation:** **Option 2** — invoke the real judge via the existing
driver/caller `advance(judge=…)` out-of-band path, LLM client injected at the
caller edge, engine pure, no Seam 7 dependency; Seam 7 later becomes just another
caller of the same injected-judge contract. Reject 1 (drags non-determinism/
network toward the core and blurs purity) and 3 (couples the first slice to Seam
7, violating Constraint #3).

**Ambiguity/failure handling (#5), resolved here, not a separate tradeoff:** the
real judge maps an ambiguous/partial/unparseable reviewer artifact to
**`Verdict.NEEDS_HUMAN`**, which the engine *already* routes to `HUMAN_QUESTION`
(sole exit `answer_human_question`). No new escape hatch is invented — this is a
hard constraint, not an option.

**Bias warnings:**
- ⚠️ *Status Quo Bias detected:* Option 2 leans on the existing `advance(judge=…)`
  seam, which could be a free pass to "what we already have." Scrutiny applied:
  it wins on second-order grounds (purity, testability, Seam-7 independence), not
  merely because it exists — Option 1 was evaluated on the same criteria and
  loses on core-purity and the stdlib-only line.
- ⚠️ *Dunning-Kruger Effect detected:* wiring an LLM API call feels simple
  ("just call the model"), which risks underestimating retry/timeout/parse-
  failure/cost handling. The fix (map all such failures to `NEEDS_HUMAN`, test
  the contract not the content) is named so the unknowns are surfaced, not
  assumed away.

---

## Decision Analysis 4 — Relationship to the cognition-layer / `quality-reviewer` rubric

**Decision type:** Architectural tradeoff (avoid building a rival mechanism).
**Framework selected:** Pros-Cons-Fixes (the catch-all for a design-shape
choice) → Opportunity Cost Analysis (what each option forgoes). Rationale: the
risk here is duplicating an existing, deliberately-orthogonal mechanism
(`decisions/cognition-layer.md`: "review, not a guard, does not amend G-5"); the
question is what a "real judge" *is* relative to what already runs.

**Options:**
- **(a) New machinery** — the real judge is a *new* LLM call from Python with a
  freshly-engineered prompt, standing beside the `quality-reviewer` subagent.
- **(b) Formalise what already happens** — the real judge is a `Judge`-shaped
  function that *consumes the structured verdict a separate reviewer subagent
  already produces* (parses `SPEC-CONFORM/BLAST-RADIUS: PASS/FAIL` from the
  reviewer's on-disk transcript) and maps it to a `Verdict`. No new reviewing LLM
  — it wires the *existing* review output into the engine's routing.
- **(c) Both, at different maturity stages** — start with (b) (formalise the
  existing review output into the `Judge` contract); allow (a) (a bespoke
  engine-side judge LLM) later only where no independent reviewer subagent
  produces an artifact for that transition.

**Pros-Cons-Fixes:**

*Option (b) — formalise the existing review output:*
- Pro: reuses the *already-working, already-independent* `quality-reviewer` output
  (the seed observation) — the producer/judge separation of Decision 2(a) is
  free, because the reviewer *is* a different subagent.
- Pro: does not duplicate the cognition layer; the engine judge becomes the
  *consumer* of the cognition layer's verdict, so the two **compose** (cognition
  layer = the review rubric that produces the verdict; engine judge = the wiring
  that routes it). No rival mechanism, no G-5 amendment.
- Pro: cheapest and lowest blast radius; the LLM "judgment" already happened in a
  separate, capability-bounded role.
- Con: depends on the reviewer emitting a machine-parseable verdict line.
  Fix: the `quality-reviewer` template already mandates a stated verdict
  (`APPROVED / CHANGES REQUIRED`, `SPEC-CONFORM: PASS/FAIL`,
  `BLAST-RADIUS: PASS/FAIL`); pin a small, explicit verdict grammar the judge
  parses, and map any parse-miss to `NEEDS_HUMAN` (fail-closed).

*Option (a) — new bespoke engine judge LLM:*
- Pro: works for transitions where no reviewer subagent produces an artifact.
- Con: risks a *second* judging LLM alongside `quality-reviewer` — duplicated
  cost, and (worse) if the bespoke judge reads the *acting agent's* output it
  reintroduces self-attestation (Decision 2's hole). Fix: only ever feed it an
  independently-produced artifact; but where such an artifact exists, (b) already
  covers it more cheaply — so (a) is justified only for genuinely
  reviewer-less transitions, which the first slice (Decision 1: `QUALITY→GIT`)
  is not.

**Opportunity cost:**

| Option not chosen | What we forgo | Value |
|---|---|---|
| (a) alone | The free producer/judge separation from the existing reviewer; risk relitigating self-attestation | High cost avoided by not choosing (a) alone |
| (b) alone | Coverage of future transitions that have no reviewer subagent | Low near-term cost (first slice has a reviewer); deferrable |

Choosing **(c)** forgoes almost nothing: (b) covers the first slice and every
transition that has an independent reviewer; (a) is held in reserve for
reviewer-less transitions, gated on the same "independently-produced artifact
only" rule.

**Recommendation:** **Option (c) — both at different maturity stages, starting
with (b).** The first real judge is a `Judge`-shaped function that *formalises
the existing `quality-reviewer` output* into the engine's `Verdict` contract
(composing with, not duplicating, the cognition layer). A bespoke engine-side
judge LLM (a) is admitted later *only* for transitions with no independent
reviewer artifact, under the unbroken rule that it never reads the acting
agent's self-report. This makes the engine judge the *consumer/wiring* of
judgment that the cognition layer + `quality-reviewer` already *produce* — the
"real judge already exists, wire it in" reading of the seed observation.

**Explicit reconciliation note for the plan:** the cognition layer
(`decisions/cognition-layer.md`) stays "review, not a guard, orthogonal to G-5."
Wiring a real engine judge does **not** amend that: the judge *routes on* the
review verdict; it does not replace the review rubric or become a new guard. The
plan must state this composition explicitly so the phantom "does the engine judge
subsume the cognition layer?" gap cannot re-surface (the L-C14 discipline).

**Bias warnings:**
- ⚠️ *IKEA Effect detected (on (a)):* a shiny new engine-side judge LLM is
  tempting to build; the analysis shows the *existing* reviewer output already
  delivers the independent judgment more cheaply for the first slice — build the
  wiring, not a second judge.
- ⚠️ *Scope Creep Bias detected (on (a)-first):* jumping to a general bespoke
  judge for all transitions expands scope past the narrow, provable first slice.
  (c) forces the narrow (b)-first start and defers (a) to where it is genuinely
  needed.

---

## Selected Approach

**OPERATOR-CONVERGED** (via the orchestrator's `question` tool — real
convergence, not self-attested by this subagent). The four material tradeoffs
D1–D4 **and** the D2-addendum (`TEST`-transition evidence class) are all
decided. **The first slice is now fully resolved — no open material tradeoff
remains.** Decided as follows:

- **D1 — scope of first slice: Option D, "All judged transitions at once."**
  **⚠️ THIS DIVERGES FROM THE RECOMMENDATION.** `gleipnir-brainstorm`
  recommended **Option A** (the narrow `QUALITY → GIT` single-edge slice). The
  operator chose **Option D** instead: wire a real judge for **`SPEC_REVIEW`,
  `TEST`, AND `QUALITY` transitions together in one slice**, not a narrow
  single-edge cut. Each of the three transitions is fed **its own independent
  artifact** — spec-review's own subagent verdict, the **mechanical test-run
  exit code** for `TEST` (D2-addendum), and `quality-reviewer`'s verdict
  respectively. The D2/D3/D4 choices below all still apply, now across three
  transitions rather than one.
- **D2 — evidence provenance: Option (a), "Structural separation"** (matches
  recommendation) **for `SPEC_REVIEW` and `QUALITY`**. The judge's input
  artifact must come from a *different* subagent invocation (`quality-reviewer`)
  than the one whose work is being judged; honesty-labelled as
  independently-produced + hook-scoped (not yet boundary-closed pre-S-2);
  artifact bound to the reviewer delegation + pipeline_id/state. (c)
  keyed+fresh marker remains the maturity target; (b)-alone rejected. **Not
  re-opened.**
- **D2-addendum — evidence class for `TEST`: mechanical exit-code observation**
  (OPERATOR-CONVERGED; see the D2-addendum section). Because `TEST` is bound to
  `gleipnir-code` (no separate reviewer role), its judge is fed the **mechanical
  test-run exit code / result** — a genuinely independent, *non-narrative*
  signal (e.g. `bin/gleipnir-sandbox test`'s own exit code), observed directly
  rather than trusting `gleipnir-code`'s self-report. This closes the
  self-attestation concern via a **different mechanism** than D2(a): independence
  by mechanical observation, not by a separate reviewer role. It is a **NEW
  evidence class**, distinct from the separate-subagent-verdict class covering
  `SPEC_REVIEW`/`QUALITY`, and accepted as consistent with test-first Axiom 1
  (the test IS the arbiter). **Resolved — not re-opened.**
- **D3 — judge call location: Option 2, "Out-of-band via the existing
  `advance(judge=…)` seam"** (matches recommendation). LLM client injected at
  the caller edge, engine stays pure, no Seam 7 dependency; ambiguity →
  `NEEDS_HUMAN`. **Not re-opened.**
- **D4 — judge vs. cognition layer: Option (c) starting with (b)** (matches
  recommendation). "Formalise the existing review output first; bespoke
  judge-LLM only later, only for reviewer-less transitions." The engine judge
  *formalises/consumes* existing review output (the `quality-reviewer` verdict
  for `SPEC_REVIEW`/`QUALITY`) and the existing mechanical arbiter signal (the
  test exit code for `TEST`) — it does **not** duplicate either. It composes
  with the cognition layer and does not amend G-5. **A bespoke engine-side
  judge-LLM would only ever be needed for a genuinely reviewer-less transition —
  and none of the three transitions in this slice are reviewer-less now that
  `TEST` has its mechanical-exit-code answer** (`SPEC_REVIEW`/`QUALITY` consume
  the `quality-reviewer` verdict; `TEST` consumes the mechanical result). So (a)
  is not exercised at all in the first slice. **Not re-opened.**

### What the D1 divergence means for scope (Option D, not Option A)

The first slice is **no longer the pure forward `QUALITY → GIT` PASS edge**. It
now covers **three transitions**, each of which must be supplied its own
independent reviewer artifact:

| Transition | Independent artifact (provenance) | Evidence class | Edge character |
|---|---|---|---|
| `SPEC_REVIEW` | spec-review subagent's own verdict transcript (`quality-reviewer` in the spec-review stage) | separate-subagent verdict (D2(a)) | forward PASS **+ revert** `SPEC_REVIEW --FAIL--> PLAN` |
| `TEST` | **mechanical test-run exit code / result** (e.g. `bin/gleipnir-sandbox test`), observed directly — not `gleipnir-code`'s self-report | **mechanical exit-code observation (D2-addendum)** | forward PASS **+ revert** `TEST --FAIL--> SPEC_REVIEW` |
| `QUALITY` | `quality-reviewer`'s verdict transcript | separate-subagent verdict (D2(a)) | forward PASS **+ revert** `QUALITY --FAIL--> CODE` |

**Structural consequence #1 — revert-budget interaction (must be addressed by
`gleipnir-plan`).** The original D1 RICE flagged Option D at Reach=6, Impact=3,
Confidence=55%, Effort=9 — a **wider blast radius** than Option A. Critically,
the wider slice **necessarily includes revert edges** — in fact **all three**
judged transitions carry one (`SPEC_REVIEW --FAIL--> PLAN`, `TEST --FAIL-->
SPEC_REVIEW`, `QUALITY --FAIL--> CODE`, per `decisions/engine-revert-edges.md`).
A real judge returning `Verdict.FAIL` therefore **traverses a backward revert
hop and increments the global monotonic `revert_count`** — something the narrow
Option A (a pure forward PASS edge with no revert-budget interaction) never had
to reason about. The plan **must** confirm that a real judge's `FAIL` verdict
routes through the **unchanged, already-built** global-revert-budget machinery
(`decisions/engine-revert-edges.md`: single per-engine monotonic budget, +1 per
backward FAIL hop, never reset, escalates to `ESCALATED` at exactly N). **The
plan must NOT redesign the budget** — it is decided and implemented; the plan
only confirms the real judge's FAIL is just another producer of the *same*
`Verdict.FAIL` the router already handles, so the revert path is exercised, not
changed. (The engine reinterprets `FAIL` as "traverse this state's revert
edge"; the real judge changes *what produces* the Verdict, never *how it
routes* — Constraint "Determinism of the router is untouched" holds.)

**Structural consequence #2 — three independent artifacts, not one, spanning
two evidence classes.** Option A leaned on the single artifact already on disk
this session (the seed observation). Option D requires an independent,
provenance-bound artifact for **each** of the three transitions — but they are
**not all the same evidence class**: `SPEC_REVIEW` and `QUALITY` use the
separate-subagent-verdict class (D2(a)); `TEST` uses the mechanical
exit-code-observation class (D2-addendum). The plan must supply the sourcing +
provenance-binding for all three: the reviewer-transcript path/handle for the
two verdict-class transitions, and the mechanical test-run result (e.g.
`bin/gleipnir-sandbox test`'s exit code) observed directly for `TEST`.

### RESOLVED — the `TEST`-transition evidence gap (operator-converged)

The NEW material tradeoff that Option D's wider scope surfaced — **`TEST` has
no separate reviewer role, so D2(a) structural separation does not apply to it
for free** — was flagged for the orchestrator and is now **OPERATOR-CONVERGED**
(via the orchestrator's `question` tool). **Resolution: option (i) — the `TEST`
judge is fed the mechanical test-run exit code / result as its independent,
non-narrative artifact.** The full analysis and the "different mechanism than
D2(a)" reasoning are recorded in the **Decision Analysis 2 — ADDENDUM** section
above. In short: independence-by-mechanical-observation (the actual pass/fail of
*running* the tests, read from the exit code) rather than
independence-by-separate-reviewer; a new evidence class distinct from the
separate-subagent-verdict class; consistent with test-first Axiom 1 (the test IS
the arbiter). Options (ii) (stand up a test-reviewer role) and (iii) (drop
`TEST` from the slice) were **not** chosen — all three transitions stay in
scope, and none is reviewer-less now that `TEST` has its mechanical-exit-code
answer.

**All three FAIL verdicts route through the existing revert-budget machinery —
no redesign.** Confirmed again for the fully-resolved slice: a `Verdict.FAIL`
from any of the three judges (spec-review verdict = FAIL; test exit code
non-zero; quality verdict = FAIL) is just another *producer* of the same
`Verdict.FAIL` the router already handles. Each traverses its state's backward
revert edge (`SPEC_REVIEW --FAIL--> PLAN`, `TEST --FAIL--> SPEC_REVIEW`,
`QUALITY --FAIL--> CODE`) and increments the **single, unchanged, already-built**
global monotonic `revert_count` (`decisions/engine-revert-edges.md`: +1 per
backward FAIL hop, never reset, escalates to `ESCALATED` at exactly N). **The
plan must NOT redesign the budget** — the real judges change *what produces* the
Verdict, never *how it routes* (the "Determinism of the router is untouched"
constraint holds).

*(Any durable ruling from D1–D4, plus the D2-addendum, should
be persisted by the operator to `decisions/` (candidate:
`decisions/engine-real-judge-wiring.md`), reconciling with
`engine-state-bridge`, `engine-revert-edges`, and `cognition-layer`.)*

## Open Questions (for `gleipnir-plan` — Trace-stage detail only, NOT material tradeoffs)

**All material tradeoffs are converged.** The items below are implementation/
Trace questions for `gleipnir-plan` to answer during planning; none is an
undecided design tradeoff.

- Exact verdict grammar the judge parses from the reviewer transcript (for
  `SPEC_REVIEW`/`QUALITY`), and the fail-closed parse-miss → `NEEDS_HUMAN`
  mapping (pin it as data, not prose).
- For `TEST`: how the caller sources the **mechanical exit code / result**
  (e.g. capturing `bin/gleipnir-sandbox test`'s process exit status) and maps
  it to `Verdict` — zero → `PASS`, non-zero → `FAIL`, missing/unparseable/
  timed-out → `NEEDS_HUMAN` (fail-closed). A wiring detail, not a tradeoff (the
  evidence class is decided in the D2-addendum).
- The provenance-binding mechanism: how the caller proves the verdict-class
  artifact came from the *reviewer* delegation (path/handle bound to that
  delegation), and the `TEST` mechanical result came from an actual test run,
  pre-Seam-7 — and how each is honesty-labelled as hook-scoped/not-boundary-
  closed.
- Whether the maturity-step keyed marker (Decision 2c, and its `TEST`-result
  analogue in the D2-addendum) reuses the bridge's `StateMarker` adaptation or
  a fresh artifact marker — a `gleipnir-plan` Trace question, not a material
  tradeoff.
- Which durable decision record the operator's D1–D4 + D2-addendum convergence
  should be persisted to (candidate: a new `decisions/engine-real-judge-wiring.md`,
  reconciling with `engine-state-bridge`, `engine-revert-edges`, `cognition-layer`).
- Whether a durable ruling is needed that the real judge is the *consumer* of
  the cognition-layer verdict and the mechanical arbiter signal (composition),
  to pre-empt the phantom-subsumption gap.

## Scope Sketch

| Area | Files/Modules Likely Affected (plan stage, not now) |
|------|------|
| Real judge object (new) | `src/gleipnir/engine/` new module (e.g. `judge.py`) — a `Judge`-shaped function/adaptor; LLM client injected, NOT imported into `engine/__init__.py` |
| Driver/caller wiring | `src/gleipnir/engine/driver.py` — real judge passed via existing `advance(judge=…)`; trivial judge stays default (no engine core change) |
| Reviewer-artifact sourcing (`SPEC_REVIEW`/`QUALITY`) | caller/harness layer — reads the independent `quality-reviewer` transcript by delegation-bound path; provenance + freshness binding |
| Mechanical-result sourcing (`TEST`) | caller/harness layer — captures the independent, non-narrative test-run result (e.g. `bin/gleipnir-sandbox test`'s process exit code); zero→PASS, non-zero→FAIL, missing/timeout→`NEEDS_HUMAN` (D2-addendum evidence class) |
| Tests (plumbing) | `tests/` — fixed/fake `Judge` for input-sourcing, provenance, `Verdict`-contract, ambiguity→`NEEDS_HUMAN` (as today) |
| Tests (live, labelled) | `tests/` — small live/integration set asserting the *contract* (valid `Verdict`, correct routing), never LLM prose; Seam-7/8 markers as not-claimed |
| Engine core | `src/gleipnir/engine/__init__.py` — **unchanged**; router/`Verdict`/`attempt_gate`/revert budget all preserved |
| Cognition-layer reconciliation | `decisions/` (operator) — durable note that the engine judge *composes with* (consumes) the cognition-layer verdict; not a new guard, does not amend G-5 |

---

_Convergence was surfaced by the ORCHESTRATOR to the operator (not by this
subagent), who converged D1–D4 **and** the D2-addendum (the `TEST`-transition
evidence class) as recorded in Selected Approach. D1 diverged from the
recommendation (operator chose Option D). The one NEW material tradeoff surfaced
under D1 (the `TEST`-transition independent-reviewer gap) is now **RESOLVED** —
operator chose option (i), the mechanical test exit-code observation as a new,
independent, non-narrative evidence class. **The brief is FULLY CONVERGED —
ready for `gleipnir-plan`. No material tradeoff remains open; nothing is
PENDING.**_
