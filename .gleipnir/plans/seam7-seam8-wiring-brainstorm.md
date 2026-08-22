# Design Brief: Wiring Seam 7 (post-tool advance hook) & Seam 8 (real CI attestation fetch) into the G-5 engine

**Status:** BRAINSTORM output — Clarify / Explore / Propose / **CONVERGED.**
The operator has decided all four material decisions (D1–D4); see
`## Selected Approach` below for the recorded choices, rationale, the
operator-mandated H-b spike precondition, and the two knowingly-accepted interim
tradeoffs. The `## Decision Analysis` sections remain as the *input* that
produced those choices (advisory recommendations preserved for audit; where the
operator overrode them, that is noted in `## Selected Approach`). **This brief is
now ready for `gleipnir-plan`** to plan *from* the converged form below.

**Author:** `gleipnir-brainstorm` (Tier-0 writer). **Skills loaded:**
`brainstorm`, `decision-frameworks` (K-3), `gotcha`.

---

## Problem Statement

The G-5 judge infrastructure is **built, tested, and dormant.**
`src/gleipnir/engine/judges.py` (commit `75b0f88`) ships three real
`Judge` factories — `make_spec_review_judge`, `make_quality_judge`,
`make_test_judge` — and the `Driver.advance(judge=…)` / `Driver.attempt_gate()`
seams work. But **nothing invokes them automatically.** Today:

- `Driver.advance_on_clean_completion` hardcodes `_trivial_completion_judge`,
  which always returns `Verdict.PASS` — the pipeline advances on *any* clean
  tool return, judging no work quality.
- `Driver.attempt_gate` takes a **caller-supplied** `Attestation` — nothing
  fetches a genuine one from real CI, so the G-3.2 gate is only as sound as
  whoever constructs the `Attestation` object.
- The pre-tool half (`sequence-gate.ts`, `tool.execute.before`) *blocks*
  out-of-order delegations, but there is **no `tool.execute.after` handler
  anywhere** (grep-confirmed): the bridge advances only via an out-of-band
  write today.

Two seams close this gap:

- **Seam 7** — a post-tool advance hook: when a stage's delegation completes,
  something must call `Driver.advance(judge=<the real stage judge>)` instead of
  the trivial always-PASS judge, sourcing each judge's evidence honestly.
- **Seam 8** — a real CI attestation fetch: `attempt_gate` must be fed an
  `Attestation` derived from *actual* CI status, by a component an agent cannot
  forge, so that GATE (G-3.2) is reachable only on genuine green CI.

The whole point of both seams is that they must **compose** with the existing
bridge (single source of pipeline truth), the G-4 bus, and the fail-closed
posture — and must **not** open a new agent-forgeable "trust me, it passed"
path. That constraint is what makes this a design decision rather than a
mechanical wiring job.

---

## Constraints

- **Single source of pipeline truth.** The digest-protected bridge
  (`.gleipnir/var/run/pipeline-state.json`, HMAC + freshness, minted by
  `src/gleipnir/engine/bridge.py`) is canonical. Each opencode hook call is a
  **fresh process** — the driver is rehydrated via `Driver.resume_from_bridge`,
  not held in memory across calls. Seam 7 MUST NOT create a second state store.
- **Engine purity.** `Engine.step`/`attempt_gate` are pure in-memory state; **no
  I/O, no bus import, no CI fetch** may enter `engine/__init__.py` (DESIGN.md
  "Non-goals"; g4-bus.md "Engine purity"). All I/O is the driver/caller edge.
- **Judge independence (no self-attestation).** Judges are payload-blind by
  construction. Their evidence is injected by the caller: spec-review/quality
  from the **independent `quality-reviewer` transcript** (never the acting
  agent's self-report); test from the **mechanical
  `bin/gleipnir-sandbox test -- --collect-only` exit code**. Seam 7 must source
  these the same way — the acting agent's narrative is never the judge input.
- **G-3.2 attestation-only gate.** GIT→GATE is reachable *only* via
  `attempt_gate(Attestation)` with `status == GREEN` and matching
  `pipeline_id`. No agent-supplied text may satisfy it (DESIGN.md "Link";
  `engine/__init__.py` `AttestationNotGreen`). Seam 8 must preserve this: the
  fetch must be an agent-unreachable component.
- **Fail-closed, degrade-not-raise split.** The bridge write is
  authority-bearing (fail-closed on key/validation); bus emit is telemetry
  (degrades, never blocks). Seam 7/8 must keep this ordering
  (`write_bridge` before emit; key loaded first).
- **Default-OFF / armed-only.** `sequence-gate.ts` enforces only when armed
  (`GLEIPNIR_PIPELINE=on` AND a bridge exists). Seam 7 must respect the same
  arming: no advance side-effects during ordinary/unarmed use.
- **Tier-3 unreachability of the guard.** The hook file, key, and driver source
  must remain agent-unwritable (Axiom 2 / G-1). Under the uncaged default this
  is cooperative-policy; under caged mode it is structural. Seam 7/8 must not
  add a new agent-writable enforcement seat.
- **stdlib-only enforcement core** (`decisions/runtime-and-deps.md`): any new
  Python must stay stdlib-only. Seam 8's CI query, if Python, cannot pull in a
  GitHub SDK for the core; if it shells out, it must do so at the caller edge.
- **CI surface.** This repo's only CI is `.github/workflows/config-scan.yml`
  (GitHub Actions; runs `bin/gleipnir-preflight config-scan` on push→main and
  PR). That is the sole existing server-side gate — see Open Question Q3 on
  whether it is the correct attestation source. `bin/gleipnir-preflight` is the
  established **agent-unreachable framework CLI** pattern (Seam 8 candidate home).

---

## Clarify — open questions for the operator (surface before planning)

These do not block writing *this* brief (the delegation carried enough context
to Explore and Propose), but each materially shapes the plan and several are
entangled with the material decisions below. I cannot reach the operator; the
orchestrator must surface them.

- **Q1 (Seam 7 evidence sourcing — the crux).** When `tool.execute.after` fires
  on a completed stage delegation, *where does the judge's evidence live at that
  instant?* The spec-review/quality judges need the **independent
  `quality-reviewer` transcript**; the test judge needs the **sandbox
  `--collect-only` exit code**. A post-tool hook sees only *that the tool
  returned* — it does not automatically have the reviewer transcript or a
  sandbox run in hand. Does the operator envision (a) the hook triggering those
  evidence-producing actions itself, (b) the evidence being deposited at a known
  path by the stage's own delegation for the hook to read, or (c) the advance
  being deferred to a distinct out-of-band caller that has the evidence? This is
  the single biggest unknown and it drives D1 and D2.

- **Q2 (which tool completion advances which state?).** The pipeline advances
  per *stage*, but `tool.execute.after` fires on *every* tool call. What is the
  advance trigger — completion of a `task` delegation whose `subagent_type`
  matches the current state's bound role (symmetric with the pre-tool gate's
  agent check)? Or a narrower/explicit signal? Getting this wrong either
  advances on unrelated tool calls or never advances.

- **Q3 (is `config-scan` the pipeline's attestation, or is there a different CI
  target?).** `.github/workflows/config-scan.yml` validates *config scoping* —
  it is **not** a full test-suite / build gate for a pipeline run's artifact.
  G-3.2's `Attestation` is meant to attest that *this pipeline's work* passed
  CI. Is config-scan the intended attestation surface for now (accepting it
  attests config-integrity, not artifact-correctness), or does the operator want
  a *new, broader* CI workflow (full `pytest` in-sandbox) to be the attestation
  source? This determines whether Seam 8 queries an existing workflow or
  presupposes a new one.

- **Q4 (`pipeline_id` ↔ CI run correspondence).** `attempt_gate` matches
  `attestation.pipeline_id` to the engine's `pipeline_id`. How does a GitHub
  Actions run get correlated to a *specific* pipeline_id? Via the commit SHA the
  git stage produced? A branch naming convention? This correspondence is what
  stops a green run for pipeline A being replayed to gate pipeline B.

- **Q5 (arming & scope for this slice).** Should Seam 7/8 land behind the same
  `GLEIPNIR_PIPELINE=on` arming as the pre-tool gate, and should the first slice
  wire **all** judged transitions (spec-review/test/quality) + the gate, or a
  narrower first cut? (The judge-wiring brief previously converged WIDER — all
  three transitions in one slice — so precedent leans wide, but Seam 7/8 add the
  live-hook + real-CI risk the judge slice explicitly deferred.)

- **Q6 (bridge freshness vs. CI latency).** The bridge freshness window is 1h
  (`DEFAULT_MAX_AGE_SECONDS = 3600`). Real CI runs can take minutes-to-longer,
  and GATE is only attempted after GIT. If the pipeline waits on a CI run, does
  the bridge risk going stale mid-wait (forcing the `bridge-recovery` path)?
  This interacts with whether Seam 8 polls synchronously or is event-driven.

---

## Explore — grounding (what the code actually shows)

- **The advance seam already exists and is judge-agnostic.**
  `Driver.advance(judge=…)` loads the key fail-closed, calls `Engine.step(judge)`,
  writes the bridge, then emits bus events. `advance_on_clean_completion` is just
  `advance(_trivial_completion_judge)`. Swapping in a real judge is a
  *call-site* change, not an engine change — `engine/__init__.py` and
  `driver.py` need **zero** edits for Seam 7's judge selection (confirmed by the
  judge-wiring slice, which added judges with zero engine/driver edits).
- **`attempt_gate` is a driver method that already emits `GateReachedEvent`** on
  success and propagates refusal unchanged. Seam 8 is about *what constructs the
  `Attestation`* passed to it — again a caller-edge concern, not an engine one.
- **`sequence-gate.ts` is the natural sibling for a `tool.execute.after`
  handler.** It already has the bridge-path constant (`BRIDGE_REL`), key load
  (`loadKey`), HMAC validation (`validateMarker`), arming check (`isArmed`), and
  fail-closed discipline. A post-tool half would reuse all of that machinery on
  the *write* side. BUT: the driver (the thing that advances + writes the
  bridge) is **Python**; the plugin is **TypeScript**. A TS post-tool hook
  cannot call the Python `Driver` directly — it would shell out to a Python
  entrypoint (mirroring how `bin/gleipnir-preflight` is invoked), or the advance
  lives in a Python process the hook triggers. This TS↔Python boundary is the
  core architectural fork for Seam 7 (D3).
- **The judges are payload-blind and take an injected reader** (`Callable[[],
  str | None]` / `Callable[[], int | None]`). So Seam 7's real work is: *build
  the reader that sources the reviewer transcript / exit code at hook time*, then
  `make_*_judge(reader)` and pass it to `advance`. The reader is the I/O
  boundary — where the "no self-attestation" property is won or lost.
- **`bin/gleipnir-preflight` is the agent-unreachable CLI precedent.** It hosts
  `config-scan`, `bridge-status`, `bridge-reset`, `--mode caged` boundary
  checks; its source is `src/gleipnir/preflight/**` which `gleipnir-code`'s edit
  grant **denies**. A Seam-8 `fetch-attestation` subcommand there inherits that
  agent-unreachability for free — a strong structural fit.
- **CI reality:** the only workflow is `config-scan.yml`. It has
  `permissions: contents: read`, is stdlib-only, SHA-pinned. It attests *config
  scoping*, not artifact correctness. There is no full-suite CI gate today.
- **Bus composition is settled.** `RevertOccurredEvent`,
  `NeedsHumanRaisedEvent`, `GateReachedEvent` already emit from the driver.
  Seam 7 advancing through real judges will naturally emit reverts (a FAIL
  verdict now actually happens) and NEEDS_HUMAN (a malformed/absent transcript
  routes there) — the bus consumers are ready; no new event kind is strictly
  required for the happy path.

---

## Approaches Considered — Seam 7 (post-tool advance hook)

### Approach 7A: TS post-tool hook shells out to a Python advance entrypoint

**Summary:** Add a `tool.execute.after` handler in `sequence-gate.ts` (or a
sibling plugin) that, when armed and the completed tool is a stage `task`,
invokes a Python entrypoint (e.g. `bin/gleipnir-advance` or a
`bin/gleipnir-preflight advance` subcommand) which rehydrates the driver from
the bridge, builds the real judge for the current state (sourcing evidence via
injected readers), calls `Driver.advance(judge)`, and re-writes the bridge.

**Tradeoffs:**
- Pro: the advance + bridge write stays in **Python**, reusing the tested
  `Driver`/`bridge`/judge code with zero re-implementation; the HMAC minting
  logic is not duplicated in TS (which only *validates*, never mints).
- Pro: the Python entrypoint can live under `src/gleipnir/preflight/**` /
  `bin/**` — **agent-unreachable** by the same grants that protect the existing
  CLI.
- Pro: co-locating the pre- and post-tool halves in one plugin keeps the
  arming/bridge-path/key contract in one place.
- Con: introduces a TS→subprocess→Python hop on every stage completion (latency,
  error-surface); the hook must fail-closed if the subprocess errors.
- Con: the evidence-sourcing (Q1) must be solved *inside* the Python entrypoint —
  it needs to find the reviewer transcript / run the sandbox at that moment.

**Estimated scope:** `.gleipnir/plugins/sequence-gate.ts` (+~post-tool handler),
new `bin/gleipnir-advance` or `src/gleipnir/preflight` subcommand, evidence
readers, tests (TS golden + Python). **Complexity: high.**

**Risk:** medium-high — the TS↔Python boundary and evidence-sourcing are both
new; getting fail-closed right across a subprocess boundary is fiddly.

### Approach 7B: Pure-Python post-tool advance in a driver-side wrapper (no TS advance)

**Summary:** Keep `tool.execute.after` (if used at all) as a thin *trigger only*;
put the real advance logic in a Python "harness" component that the framework
runs — e.g. the driver is owned by a small Python supervisor process that
observes stage-completion signals (deposited at a known Tier-1 path by the
stage delegation) and advances. The TS hook's role shrinks to (optionally)
depositing the completion signal; all judge/advance/bridge logic is Python.

**Tradeoffs:**
- Pro: keeps *all* enforcement logic in one language (Python), matching where
  the engine/driver/judges already live; no cross-language advance contract.
- Pro: the supervisor can hold richer state (e.g. correlate evidence artifacts)
  without cramming it into a stateless hook.
- Con: introduces a **new long-lived component** (a supervisor/observer process)
  that does not exist today — larger surface, lifecycle/ownership questions,
  and it is *not* the opencode-native `tool.execute.after` seat the spec names
  (S-1 point 1 names the hook as the enforcement seat).
- Con: risks a **second source of truth** if the supervisor holds in-memory
  state that can drift from the bridge — must be disciplined to treat the bridge
  as canonical.

**Estimated scope:** new Python supervisor/observer module, signal-deposit
convention, driver wiring, tests. **Complexity: high.**

**Risk:** high — new process lifecycle + the second-source-of-truth trap the
constraints explicitly forbid.

### Approach 7C: Minimal slice — hook advances with the *test* judge only (mechanical evidence), defer reviewer-transcript judges

**Summary:** Recognise that the three judges differ sharply in *how hard their
evidence is to source at hook time*. The **test judge** needs only a mechanical
`--collect-only` exit code (the caller can run the sandbox and read
`returncode`). The **spec-review/quality judges** need an independent
`quality-reviewer` transcript that must already exist somewhere. First slice:
wire the post-tool hook to advance **only the TEST transition** with the real
`make_test_judge` (mechanical, self-contained), and leave spec-review/quality on
the trivial judge (or NEEDS_HUMAN) until Q1's transcript-sourcing is designed.

**Tradeoffs:**
- Pro: ships a genuinely-real judged transition end-to-end with the *least*
  unresolved dependency (mechanical exit code, no transcript plumbing).
- Pro: de-risks the TS↔Python + evidence question by solving it once for the
  easy case before the hard (transcript) case.
- Pro: directly exercises Seam 7's hook plumbing under real conditions, feeding
  E-3 (novelty-triage signal) and revealing latency/fail-closed issues cheaply.
- Con: partial — leaves two of three judged transitions still trivial; the "no
  live caller" gap is only *narrowed*, not closed.
- Con: risks looking like progress while the hardest decision (transcript
  sourcing) stays open.

**Estimated scope:** post-tool hook + test-judge reader (sandbox exec at caller
edge) + arming + tests. **Complexity: medium.**

**Risk:** low-medium — smallest new surface; the deferred part is explicit.

---

## Approaches Considered — Seam 8 (real CI attestation fetch)

### Approach 8A: `bin/gleipnir-preflight fetch-attestation` subcommand (CLI shell-out, polling GitHub API)

**Summary:** Add an agent-unreachable subcommand under
`src/gleipnir/preflight/**` that, given a `pipeline_id`↔commit-SHA correlation,
queries the GitHub Actions status for that SHA (via `gh` CLI or a stdlib
`urllib` call to the REST API using a token the agent cannot read), maps the
conclusion to `AttestationStatus` (success→GREEN, failure→RED, in-progress→
PENDING, none→ABSENT), and returns/constructs the `Attestation`. The
GIT→GATE attempt calls this fetch, never an agent-supplied value.

**Tradeoffs:**
- Pro: inherits agent-unreachability from the existing preflight CLI grants —
  strong structural fit with the "no forgeable path" constraint.
- Pro: polling is simple, stateless, and composes with a fresh-process model;
  no inbound network listener to secure.
- Pro: stdlib `urllib` keeps the core dependency-free (or `gh` at the caller
  edge, outside the core).
- Con: **polling latency** — GATE may need to wait for CI; interacts with bridge
  freshness (Q6) and needs a PENDING→re-poll loop or a "gate deferred until
  green" state.
- Con: requires a **credential** (GitHub token) reachable by the fetch component
  but not the agent — E-1 credential-unreachability is only cooperative-policy
  until S-2 (co-located token risk).
- Con: **config-scan is not an artifact-correctness gate** (Q3) — if it is the
  queried workflow, the attestation attests config-integrity, not that the
  pipeline's tests pass.

**Estimated scope:** new `src/gleipnir/preflight` subcommand, GH query, status
mapping, `pipeline_id`↔SHA correlation, wiring into the GATE attempt, tests.
**Complexity: high.**

**Risk:** medium-high — credential handling + latency + the config-scan-vs-
correctness semantics.

### Approach 8B: CI writes a signed attestation artifact; the fetch verifies it (webhook/artifact-drop, no live API query)

**Summary:** Instead of the framework polling GitHub, the **CI workflow itself**
(on green) writes a signed attestation (HMAC with the same S-2 key class as the
bridge, or a GH-native signed artifact) to a known location; the GIT→GATE
attempt reads and *verifies* that artifact locally. Mirrors how the bridge
marker is minted-and-verified, extended to a CI→framework channel.

**Tradeoffs:**
- Pro: the framework never needs an outbound GitHub credential or live query —
  it only *verifies* a signature, mirroring the existing HMAC marker model
  (`verify/marker.py`), which the codebase already trusts.
- Pro: unforgeable by construction if the signing key is CI-side and
  agent-unreachable — an agent cannot mint a green attestation without the key
  (same argument as the bridge HMAC).
- Pro: no polling-latency loop in the framework; the artifact either exists-and-
  verifies or it does not (fail-closed).
- Con: requires CI to hold a **signing key** (secret management in GitHub
  Actions) — a new secret surface, and the key must not leak into logs/artifacts.
- Con: needs a **transport** for the artifact from CI back to the framework host
  (commit-back, artifact download, or an inbound receiver — E-2 platform-webhook
  has no component home yet). This is heavier than a read-only poll.
- Con: still must resolve Q3 (what CI actually attests) and Q4 (pipeline_id
  correspondence).

**Estimated scope:** CI workflow signing step, key management, artifact
transport/receiver, local verify, GATE wiring, tests. **Complexity: high (and
touches CI secrets + a transport that has no home yet).**

**Risk:** high — new signing-key surface + the E-2-shaped transport gap.

### Approach 8C: Defer real fetch; formalise the *seam contract* with a fail-closed placeholder fetcher (no live CI yet)

**Summary:** Do not query CI yet. Instead, define the **fetcher interface** — a
single agent-unreachable function `fetch_attestation(pipeline_id) ->
Attestation` — and ship a placeholder that returns `ABSENT`/`PENDING`
(fail-closed: GATE unreachable) while the real backend (8A or 8B) is chosen
separately. GIT→GATE calls the fetcher, so the *no-forgeable-path* property is
established structurally now; the live query lands later behind the same
interface.

**Tradeoffs:**
- Pro: locks in the *architecture* (fetcher is the only Attestation source; agent
  text can never reach `attempt_gate`) without committing to the CI-query
  mechanism, which depends on unresolved Q3/Q4/E-1.
- Pro: keeps GATE fail-closed (ABSENT → refuse) — strictly safe; no false green.
- Pro: cheap, small, reversible (two-way door) — lets Seam 7 proceed without
  being blocked on the CI-fetch decision.
- Con: GATE is **unreachable** until the real fetcher lands — the pipeline can
  reach GIT but never GATE (acceptable if the operator accepts a
  can-reach-GIT-only first slice; not if end-to-end GATE is required now).
- Con: another "built but dormant" artifact, the exact pattern this whole
  exercise is closing — must be honestly labelled as a seam, not a solution.

**Estimated scope:** fetcher interface + fail-closed placeholder + GATE wiring +
tests. **Complexity: low.**

**Risk:** low — but it defers rather than resolves the CI question.

---

## `## Decision Analysis`

> **This section is the INPUT to the operator's convergence decision, not the
> decision.** Per the brainstorm precept-10 gate, `gleipnir-brainstorm` (a
> subagent) cannot reach the operator and must not record a convergence.
> The orchestrator surfaces each material decision below to the operator; only
> the operator's returned choice is authoritative. Recommendations here are
> advisory.

### Decision D-A (foundational): Reversibility Filter on the whole Seam 7/8 effort

**Framework used:** Reversibility Filter (mandated first step for any decision).

**Analysis:**
- Seam 7 *call-site* wiring (which judge, where the hook lives) is largely a
  **Two-Way Door** — no engine change, revertible by pointing `advance` back at
  the trivial judge.
- Seam 8's *attestation-source mechanism* (poll vs. signed-artifact vs. defer)
  is closer to a **One-Way Door**: choosing 8B commits to a CI signing-key +
  transport surface that is expensive to unwind; choosing 8A commits to a
  credential-handling posture. 8C is explicitly reversible.

**Recommendation:** Fast-track the Seam 7 *plumbing* choice; apply deeper
frameworks (below) to the Seam 8 mechanism and to the Seam 7 evidence-sourcing
question (Q1), which is the genuinely consequential part.

---

### Decision D1 (MATERIAL): Where does the Seam 7 post-tool advance logic live — TS-shell-out (7A), Python supervisor (7B), or minimal test-only slice (7C)?

**Decision type:** Architectural tradeoff → **Second-Order Thinking + Pre-Mortem**
(auto-selection: architectural).

**Second-Order Thinking:**
- **7A (TS hook → Python entrypoint):**
  - Near term: reuses all tested Python; one plugin owns pre+post. *Second-order:*
    every stage completion crosses a subprocess boundary — a new latency + error
    surface the fail-closed logic must cover.
  - Far term: the enforcement seat is exactly the opencode-native hook the spec
    names (S-1). *Second-order:* consistent with the pre-tool half; future S-2
    closure protects one plugin + one CLI, not a bespoke process.
- **7B (Python supervisor):**
  - Near term: single-language, richer state. *Second-order:* a new long-lived
    process with its own lifecycle/ownership — and an in-memory state that can
    **drift from the bridge** (the second-source-of-truth the constraints
    forbid).
  - Far term: diverges from the opencode-hook enforcement model; more to secure
    under S-2.
- **7C (minimal test-only slice):**
  - Near term: ships one *real* judged transition (TEST) with mechanical
    evidence, deferring the hard transcript-sourcing (Q1). *Second-order:* proves
    the hook plumbing cheaply; the deferred part stays explicit.
  - Far term: sets the plumbing pattern that 7A completes for the transcript
    judges — 7C is essentially "7A, but only the easy judge first."

**Pre-Mortem (assume the chosen approach failed at 6 months):**
| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | 7B supervisor's in-memory state drifted from the bridge; pipeline advanced on stale state | M | H | Forbid supervisor state; bridge is canonical — but this is *designing around* 7B's core weakness → favours 7A/7C |
| 2 | 7A subprocess errored and the hook fail-opened (advanced anyway) | M | H | Fail-closed on any non-zero subprocess exit; golden-fixture test the error path |
| 3 | Evidence-sourcing (Q1) unsolved, so spec-review/quality judges silently fell back to trivial-PASS | H | H | 7C makes the fallback *explicit* (only TEST is real); 7A must solve Q1 before its transcript judges are trustworthy |
| 4 | Hook advanced on unrelated tool calls (Q2 mis-scoped) | M | M | Gate advance on `task` + `subagent_type == role-for-state`, symmetric with pre-tool gate |

**Bias check (12 detectors):**
- ⚠️ **IKEA Effect** — the tested Python `Driver`/judges are ours and recently
  built; 7A/7B both lean on reusing them. Re-ask: is reuse the *right* boundary,
  or are we over-valuing in-house code? (Verdict: reuse is genuinely correct
  here — the alternative is re-implementing HMAC minting in TS, which is worse —
  but flag it so the operator weighs it.)
- ⚠️ **Scope Creep Bias** — 7A+8-full-in-one-slice risks doing everything at
  once to avoid choosing a first cut. 7C is the forcing function that resists it.
- ⚠️ **Status Quo Bias** — the pre-tool gate is TS; defaulting Seam 7 to "also
  TS" (7A) may be momentum rather than merit. Weighed against: S-1 does name the
  hook as the seat, so it is *also* on the merits.

**Recommendation (advisory):** **7C now (minimal test-only slice), on the 7A
plumbing pattern** — i.e. a `tool.execute.after` hook that shells to a Python
advance entrypoint, wired first for the *mechanical* TEST judge only, with
spec-review/quality explicitly deferred pending Q1's transcript-sourcing design.
Reject 7B (second-source-of-truth risk; new process lifecycle; diverges from the
named enforcement seat). This ships a genuinely-real judged transition with the
least unresolved dependency and de-risks the TS↔Python boundary before the hard
transcript case. **The operator decides**; the tension is *scope* — 7C is
narrower than the judge-wiring slice's WIDER precedent (Q5), so the operator may
prefer full 7A across all three judges if they accept solving Q1 up front.

---

### Decision D2 (MATERIAL): Seam 7 evidence-sourcing for the reviewer-transcript judges — how does the hook obtain the independent `quality-reviewer` transcript without reintroducing self-attestation? (This is Q1, elevated.)

**Decision type:** Uncertainty about facts / mechanism → **Hypothesis-Driven
Analysis** (auto-selection: novel, evidence-thin).

**Hypotheses:**
- **H-a (hook triggers the reviewer):** *If* the post-tool hook itself invokes
  the `quality-reviewer` delegation and captures its transcript, *then* the
  judge has independent evidence, *because* the reviewer is a separate subagent.
  - Key assumption: a hook can spawn a delegation and capture its output
    synchronously. Evidence against: hooks are `tool.execute.after` callbacks,
    not orchestration drivers — spawning a subagent from a hook is architecturally
    unusual and may re-enter the gate. **Confidence: Low.**
- **H-b (stage deposits transcript at a known path):** *If* the spec-review /
  quality stage delegation writes its verdict transcript to a known Tier-1 path,
  *then* the hook's injected reader just reads that file, *because* the transcript
  already exists by the time the stage's tool returns.
  - Key assumption: the `quality-reviewer` output is durably deposited (not just
    returned in-band to the orchestrator). Evidence for: the judges' readers are
    *designed* as `Callable[[], str | None]` reading an already-sourced string —
    this matches a file-drop. Evidence against: requires a deposit convention
    that does not exist yet. **Confidence: Medium-High.**
- **H-c (advance is deferred to an out-of-band caller with the evidence):** *If*
  the advance is not done by the hook at all but by the orchestrator/harness that
  *already holds* the reviewer transcript, *then* no new sourcing is needed,
  *because* the evidence is in hand at the advance site.
  - Key assumption: an out-of-band caller is acceptable as the Seam-7 "hook"
    (blurs the S-1 hook-as-seat model). **Confidence: Medium**, but partly a
    re-statement of 7B.

**Bias check:**
- ⚠️ **Confirmation Bias** — H-b fits the judges' existing reader shape so
  neatly that it is tempting to declare it correct without checking whether the
  transcript is actually deposited today (it is *not* — grep shows no such
  convention). Flag: this needs the operator's Q1 answer, not our assumption.
- ⚠️ **Dunning-Kruger** — confidence about opencode hook capabilities (can a
  hook spawn a subagent? H-a) exceeds demonstrated knowledge of the runtime.
  Recommend a spike before committing to H-a.

**Recommendation (advisory):** Pursue **H-b (stage deposits transcript at a
known Tier-1 path; hook's reader reads it)** as the leading hypothesis — it
matches the judges' injected-reader design and preserves independence (the
transcript is the *reviewer's*, not the acting agent's). But this is **blocked
on operator Q1** and needs a small spike to confirm opencode can deposit +
read the transcript deterministically. If Q1 resolves against a deposit
convention, fall back to H-c (out-of-band caller). **Do not** proceed on H-a
without a spike (hook-spawns-subagent is unverified). This is *why* D1's
recommendation defers the transcript judges (7C): D2 is genuinely unresolved.

---

### Decision D3 (MATERIAL): Seam 8 attestation-source mechanism — poll GitHub (8A), CI-signed artifact (8B), or defer behind a fail-closed fetcher interface (8C)?

**Decision type:** Architectural + risk + go/no-go → **Weighted Decision Matrix**
then **Pre-Mortem** on the leader.

**Weighted Decision Matrix** (score 0–10, ×weight; higher total better):

| Criterion | Weight | 8A poll | 8B signed-artifact | 8C defer/interface |
|---|---|---|---|---|
| Unforgeability / no agent path (the point of G-3.2) | 10 | 7 → 70 | 9 → 90 | 8 → 80 |
| Composes with fresh-process + bridge model | 7 | 6 → 42 | 5 → 35 | 9 → 63 |
| Avoids new credential/secret surface (E-1) | 8 | 3 → 24 | 3 → 24 | 9 → 72 |
| Avoids new transport with no home (E-2) | 6 | 8 → 48 | 3 → 18 | 9 → 54 |
| Attests artifact correctness (not just config-scan) | 7 | 5 → 35 | 6 → 42 | 3 → 21 |
| Reversibility (two-way door) | 5 | 4 → 20 | 3 → 15 | 10 → 50 |
| Ships end-to-end GATE reachability now | 6 | 7 → 42 | 6 → 36 | 2 → 12 |
| **Total** | | **281** | **260** | **352** |

**Leader: 8C (defer behind a fail-closed fetcher interface), 352.** Caveat where
the winner scores poorly: 8C scores lowest on *"ships GATE reachability now"* (2)
and *"attests artifact correctness"* (3) — 8C deliberately leaves GATE
unreachable until a real backend lands. If the operator's hard requirement is
end-to-end GATE **this slice**, 8C fails that requirement and 8A becomes the
leader among the *live* options.

**Pre-Mortem on 8C (assume it failed):**
| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | 8C became a permanent "dormant artifact" — the very pattern being closed | M | M | Time-box the real-fetcher decision; label 8C explicitly as a seam with a named next step |
| 2 | Operator actually needed live GATE and 8C blocked it | M | H | Surface Q3/Q6 first; if GATE-now is required, choose 8A |
| 3 | The fetcher interface was designed too narrowly and the real backend didn't fit | L | M | Design the interface as `fetch_attestation(pipeline_id) -> Attestation` — the minimal shape both 8A and 8B satisfy |

**Bias check:**
- ⚠️ **Status Quo Bias** — 8C is the "change nothing risky yet" option; it may
  be getting a free pass because it is safe. Counter: it *does* establish the
  no-forgeable-path architecture structurally, which is real progress, not
  inaction.
- ⚠️ **Scope Creep Bias** — 8B pulls in CI signing keys + a transport with no
  home (E-2); that is expanding scope to a full solution rather than choosing a
  first cut.
- ⚠️ **Availability Heuristic** — config-scan is the CI we *have in mind*, so 8A
  is tempted to just query it; but config-scan attests config, not correctness
  (Q3). Don't let the available workflow substitute for the right attestation.

**Recommendation (advisory):** **8C (defer behind a fail-closed fetcher
interface)** *unless* the operator requires end-to-end GATE this slice — in which
case **8A (poll)**, scoped to accept that config-scan attests config-integrity
(Q3) as an interim, with the pipeline_id↔SHA correlation (Q4) resolved first.
**Reject 8B for now** — it drags in a CI signing-key surface and an E-2-shaped
transport that has no component home; revisit it only if a stronger
unforgeability guarantee than 8A's read-only poll is later required. **The
operator decides**, and D3 is tightly coupled to Q3/Q4/Q6.

---

### Decision D4 (MATERIAL): Slice scope & arming — how much of Seam 7/8 lands together, and behind what arming? (This is Q5, elevated.)

**Decision type:** Prioritisation / go-no-go → **Opportunity Cost + Regret
Minimisation.**

**Opportunity Cost:**
- Choosing **7C + 8C** (narrowest) forgoes end-to-end GATE now, but buys the
  cheapest proof of the hook plumbing + the no-forgeable-path architecture, and
  keeps the transcript-sourcing (D2) and CI-mechanism (D3) decisions
  independent and reversible.
- Choosing **7A-full + 8A** (widest) forgoes reversibility and forces solving
  Q1/Q3/Q4 immediately, but delivers a fully live judged pipeline.

**Regret Minimisation (horizon: the framework's completion):**
| Option | Regret if wrong | Regret if not chosen | Max regret |
|---|---|---|---|
| 7C + 8C (narrow) | 4 (partial, but explicit + safe) | 5 (slower to full live pipeline) | 5 |
| 7A-full + 8A (wide) | 8 (shipped forgeable/false-green or fail-open under unsolved Q1/Q3) | 3 | 8 |

**Bias check:**
- ⚠️ **Scope Creep Bias** (again) — the widest option is the "do it all" avoidance
  of a first-cut choice.
- ⚠️ **Bandwagon / precedent** — the judge-wiring slice went WIDER; that is a
  precedent, not a proof the same width fits here (Seam 7/8 carry live-hook +
  real-CI risk the judge slice explicitly deferred).

**Recommendation (advisory):** **Narrow first slice (7C + 8C), behind the same
`GLEIPNIR_PIPELINE=on` arming as the pre-tool gate**, with spec-review/quality
transcript judges (D2) and the live CI mechanism (D3/8A) as explicit,
named next slices. Lowest max-regret; preserves reversibility on the two
genuinely one-way-door questions. **The operator may override toward width** if
they accept solving Q1/Q3/Q4 up front and want live GATE this slice.

---

## Selected Approach

**CONVERGED — operator-decided (recorded verbatim below).** The operator
surfaced `## Decision Analysis` via the orchestrator and returned the four
choices below. Where a choice **overrides** this brief's advisory
recommendation, that is noted explicitly — the operator's choice governs; the
advisory analysis is retained above for audit only. `gleipnir-plan` plans from
this section.

### D4 (scope / arming): **WIDE.**

Full Seam 7 (all three judged transitions: **spec-review, quality, test**) +
Seam 8 **8A** (live GitHub Actions poll) land in **this slice**. GATE **must be
reachable via genuine CI status by the end of this slice**, not deferred.

*Rationale (from the brief's own analysis):* This **overrides** the D4 advisory
recommendation (narrow first slice, 7C + 8C — lowest max-regret, Regret
Minimisation table scoring narrow's max-regret 5 vs. wide's 8). The operator has
accepted the wider regret exposure in exchange for a fully live judged pipeline
with end-to-end GATE reachability now, consistent with the judge-wiring slice's
WIDER precedent (Q5). The Pre-Mortem row-3 risk this raises — "evidence-sourcing
(Q1) unsolved, so spec-review/quality judges silently fell back to trivial-PASS"
(likelihood H, impact H) — is **not** left unmitigated at wide scope: it is
bound by the D2 spike precondition below (H-b must be confirmed before it is
built into the committed design). The Scope Creep / Bandwagon-precedent bias
flags on D4 were surfaced to the operator and knowingly accepted.

### D1 (Seam 7 architecture): **7A.**

TS `tool.execute.after` hook (in `sequence-gate.ts` or a sibling plugin) shells
out to a Python advance entrypoint (e.g. `bin/gleipnir-advance` or a
`bin/gleipnir-preflight advance` subcommand) that rehydrates the driver from the
bridge, builds the real judge for the current state, calls `Driver.advance(judge)`,
and re-writes the bridge. **Wired for ALL THREE judges** (spec-review / quality /
test), not just the mechanical test judge. **Rejected: 7B** (Python supervisor —
second-source-of-truth risk).

*Rationale (from the brief's own analysis):* 7A keeps the advance + bridge write
in **Python**, reusing the tested `Driver` / `bridge` / judge code with zero
re-implementation and never duplicating the HMAC-minting logic in TS (which only
validates, never mints); the Python entrypoint lives under
`src/gleipnir/preflight/**` / `bin/**`, **agent-unreachable** by the same grants
that protect the existing CLI; and it sits at exactly the opencode-native hook
enforcement seat the spec names (S-1), co-locating the pre- and post-tool halves
in one plugin. 7B is rejected on its Second-Order and Pre-Mortem row-1 weakness:
a new long-lived supervisor process whose in-memory state can **drift from the
bridge** — the second-source-of-truth the constraints explicitly forbid — plus
a lifecycle/ownership surface that diverges from the named enforcement seat. The
IKEA-Effect bias flag (over-valuing our own recently-built Python) was surfaced
and judged genuinely correct here (the alternative, re-implementing HMAC minting
in TS, is worse). This **extends beyond** the D1 advisory (which recommended the
7A *plumbing pattern* but wired only the mechanical TEST judge first, 7C): the
operator wires all three judges now, consistent with D4 WIDE, gated by the D2
spike precondition below.

### D2 (evidence sourcing for spec-review / quality judges): **H-b as primary.**

The `quality-reviewer` stage delegation deposits its verdict transcript at a
known Tier-1 path; the post-tool hook's injected reader (`Callable[[], str |
None]`) reads that file to build `make_spec_review_judge` / `make_quality_judge`.

**Operator-mandated precondition (spike-before-commit):** a **spike must run
BEFORE H-b is built into the plan's committed design** — it must confirm
opencode can deterministically **deposit-then-read** a transcript across the
hook boundary (per the brief's open spike candidate (b): "is the
`quality-reviewer` transcript durably deposited at a readable path, or only
returned in-band"). **If the spike falsifies H-b, escalate back through
brainstorm / orchestrator before proceeding** to H-a or H-c; **do not silently
substitute.**

*Rationale (from the brief's own analysis):* H-b was the leading hypothesis at
**Medium-High** confidence in the Hypothesis-Driven Analysis, because it matches
the judges' *designed* injected-reader shape (`Callable[[], str | None]` reading
an already-sourced string ≈ a file-drop) and preserves independence — the
transcript is the **reviewer's**, never the acting agent's self-report (the
no-self-attestation constraint). The analysis also flagged the **Confirmation
Bias** risk that H-b fits the reader shape so neatly it is tempting to declare it
correct without checking that the transcript is actually deposited today (grep
showed **no such convention exists yet**). The operator's spike-before-commit
precondition is the direct answer to that flag: it converts the assumption into
a verified fact before the design is committed. H-a stays rejected-without-a-spike
(hook-spawns-subagent unverified, Dunning-Kruger flag); H-c (out-of-band caller)
is the named fallback only via escalation, not silent substitution.

### D3 (Seam 8 mechanism): **8A — live poll.**

Add an **agent-unreachable** `bin/gleipnir-preflight fetch-attestation` (or
equivalent) subcommand under `src/gleipnir/preflight/**` that queries GitHub
Actions status for a commit SHA and maps conclusion→`AttestationStatus`
(**success→GREEN, failure→RED, in-progress→PENDING, none→ABSENT**). **Rejected:
8B** (CI signing-key + no-home transport, E-2).

**Knowingly-accepted interim tradeoffs (recorded honestly, not papered over):**

1. **config-scan as the attestation surface (Q3).** `.github/workflows/config-scan.yml`
   is the only CI surface today and it attests **config-scoping, not full
   artifact correctness**. This is an interim tradeoff **knowingly accepted** —
   the attestation attests config-integrity, not that the pipeline's tests pass.
   The plan must state this honestly.
2. **E-1 credential isolation is cooperative-policy, not structural.** The GitHub
   token must be **reachable by the fetch subcommand but NOT by any roster
   agent**. Under the uncaged default this is **cooperative-policy** (the token
   and the fetcher are co-located; agent-unreachability rests on the same grant
   discipline as the existing preflight CLI), **not structural** — E-1 becomes
   structural only under S-2. The plan **must state this honestly and not claim a
   stronger guarantee than exists**.

**`pipeline_id`↔commit-SHA correlation (Q4) must be resolved by the plan.**

*Rationale (from the brief's own analysis):* This **overrides** the D3 advisory
leader. The Weighted Decision Matrix scored 8C highest (352) but the brief's own
caveat states the winner scores poorly exactly where it matters here: 8C scores
2/10 on "ships GATE reachability now" and 3/10 on "attests artifact correctness"
— *"If the operator's hard requirement is end-to-end GATE this slice, 8C fails
that requirement and 8A becomes the leader among the live options."* D4 WIDE
makes end-to-end GATE this-slice a hard requirement, so 8A is selected on the
matrix's own terms. 8A inherits **agent-unreachability** from the existing
preflight CLI grants (`src/gleipnir/preflight/**` is denied to `gleipnir-code`) —
the strong structural fit with the no-forgeable-path constraint (matrix
unforgeability 7/10) — and its polling is stateless, composing with the
fresh-process model with no inbound listener to secure. 8B is rejected per the
matrix + Scope-Creep bias flag: it drags in a **CI signing-key secret surface**
and an **E-2-shaped transport that has no component home yet** (matrix
avoids-new-transport 3/10, avoids-new-credential 3/10). The two accepted
tradeoffs above are the brief's own Q3 (Availability-Heuristic flag: "config-scan
is the CI we have in mind… but it attests config, not correctness") and the 8A
Con on E-1 credential co-location — surfaced to the operator and knowingly
accepted, not silently substituted. The **latency / bridge-freshness** interaction
(Q6) and the **PENDING→re-poll / gate-deferred** state remain for the plan to
resolve, alongside Q4.

### Cross-cutting consequences for the plan

- **D4 WIDE + D1 all-three-judges are gated by the D2 spike.** The plan must
  sequence the H-b deposit-then-read spike **before** committing the
  spec-review / quality transcript-judge design; a falsified spike escalates
  back through brainstorm / orchestrator (it does **not** silently fall back).
- **Two accepted interim tradeoffs must be stated honestly in the plan**:
  config-scan attests config-scoping (not artifact correctness); E-1 credential
  isolation is cooperative-policy (not structural) until S-2.
- **Q4 (`pipeline_id`↔commit-SHA correlation) is a plan deliverable**, not
  deferred — it is what stops a green run for pipeline A gating pipeline B.
- **Arming** reuses the pre-tool gate's `GLEIPNIR_PIPELINE=on` + bridge-exists
  contract (`isArmed`); no advance/fetch side-effects when unarmed.

---

## Open Questions

- **Q1–Q6 above** (evidence sourcing, advance trigger, CI-as-attestation,
  pipeline_id↔run correlation, slice scope/arming, bridge-freshness-vs-CI-latency)
  — all require operator input or a spike; Q1/Q3/Q4 are entangled with D2/D3.
- **Spike candidates** (pre-plan, if the operator wants confidence before
  committing): (a) can an opencode `tool.execute.after` hook shell out to a
  Python entrypoint and fail-closed on its exit code? (b) is the
  `quality-reviewer` transcript durably deposited at a readable path, or only
  returned in-band (drives D2/H-b vs H-c)? (c) what GitHub Actions API shape +
  credential posture would 8A need, and does config-scan's `conclusion` map
  cleanly to GREEN/RED/PENDING/ABSENT?
- **E-1 (credential unreachability)** and **E-2 (webhook receiver has no home)**
  are pre-existing open seams that 8A and 8B respectively lean on; neither is
  closed today. Any plan choosing 8A/8B must state its reliance honestly.
- **Bridge freshness (1h)** interaction with CI wait time (Q6) — may force
  either an async/deferred-gate state or a documented "re-arm on CI completion"
  step; flagged for the plan.

---

## Scope Sketch

| Area | Files/Modules Likely Affected (depends on converged D1–D4) |
|------|-------------------------------------------------------------|
| Seam 7 post-tool hook (7A/7C) | `.gleipnir/plugins/sequence-gate.ts` (+ `tool.execute.after`) or sibling plugin; golden-fixture TS tests |
| Seam 7 Python advance entrypoint | new `bin/gleipnir-advance` **or** `src/gleipnir/preflight/**` subcommand (agent-unreachable); evidence readers; Python tests |
| Seam 7 judge selection | call-site only — `make_*_judge(reader)` → `Driver.advance(judge)`; **no** edits to `engine/__init__.py` or `driver.py` |
| Seam 7 evidence deposit (D2/H-b) | Tier-1 transcript-deposit convention (new); `quality-reviewer` output path |
| Seam 8 fetcher interface (8C) | new `fetch_attestation(pipeline_id) -> Attestation` (agent-unreachable); fail-closed placeholder; GATE-attempt wiring |
| Seam 8 live fetch (8A, if chosen) | `src/gleipnir/preflight/**` GH-status query (stdlib `urllib` or `gh` at edge); status→`AttestationStatus` map; `pipeline_id`↔SHA correlation; credential posture (E-1) |
| Seam 8 CI (8A/8B, if chosen) | possibly a new full-suite CI workflow (Q3) beyond `config-scan.yml` |
| Bus composition | none required for happy path — reverts/NEEDS_HUMAN/GateReached already emit from the driver |
| Arming | reuse `GLEIPNIR_PIPELINE=on` + bridge-exists check (`isArmed`) |
| Decision records | on convergence: durable Tier-3 record (operator-authored) capturing D1–D4 |
