# Design Brief: Wiring the judges' live caller (re-scoped against on-disk reality)

**Stage:** brainstorm (owned by `gleipnir-brainstorm`). **Tier:** 0 (`plans/`,
disposable). **Status: CONVERGED — operator has decided (see `## Convergence`
below).** This brief's central content is a **material discovery**: the task as
delegated rested on a **stale premise**. The "live caller" this task asked to
scope **already exists on disk, fully built**, in a session that ran *after* the
one described in the delegation. The re-scoped decision was surfaced to the
operator via the orchestrator and **converged on Approach A** — see the
`## Convergence` section for the three recorded decisions.

**Convergence was surfaced by the ORCHESTRATOR to the operator, not by this
subagent.** Per the brainstorm skill's Phase-4 constraint, this subagent's
`question` tool does not reach the operator; the `## Decision Analysis` below was
returned to the orchestrator, which put it to the operator and handed the
converged choice back. The `## Convergence` section records that operator
decision (real convergence — not self-attested).

---

## Convergence

**CONVERGED — the operator decided via the orchestrator (real convergence, not
self-attested by this subagent).** Date: 2026-08-22.

The `## Decision Analysis`, `## Approaches Considered`, and `## Open Questions`
sections below are left **intact** as the record of what was considered and how
the decision was reached; this section records only the resolution and
supersedes (does not delete) the earlier "NOT YET CONVERGED / no selected
approach / recommendation only" disclaimers throughout the brief.

1. **Selected approach: A** (not B, not C). Apply the already-drafted,
   already-reviewed **D5 sidecar write-side diff** from
   `.gleipnir/plans/seam8-d5-sidecar-write-diff.md`, plus its tests, to make the
   **GIT→GATE** transition reachable in a live run. This closes the one genuine
   functional gap the brief found by grep: nothing currently writes
   `.gleipnir/var/run/pipeline-run.json`, so `read_pipeline_run_identity`
   returns `None`, `advance_main` raises `MissingRunIdentity` at the GIT state,
   and `attempt_gate` is never reached — GATE is wired-but-inert. Approach C
   (full end-to-end live-run hardening) remains the **sequenced end-state** once
   A lands, NOT this slice.

2. **Doc-correction side task — confirmed required, and in-flight ELSEWHERE.**
   `SESSION-STATE.md`'s stale claim that Seam 7 / Seam 8 / the live caller are
   "not yet built" must be corrected: they are already built on disk
   (`.gleipnir/plugins/advance-hook.ts`,
   `src/gleipnir/preflight/advance.py::advance_main`,
   `src/gleipnir/preflight/fetch_attestation.py`, per the Explore findings in
   this brief). **This doc-fix is being handled by a separate session-scribe
   delegation in parallel — it is NOT part of the Approach-A build slice and
   `gleipnir-plan` does not need to plan it.** It is recorded here so the brief
   and the actual on-disk state stay in sync.

3. **D5 write authorship/routing — route to `gleipnir-code` as-is, NO Tier-3
   grant change.** The D5 sidecar `head_sha` write side lands in
   `src/gleipnir/broker/git/mcp_server.py`'s `commit_changes`, per the parent
   plan's existing D5 convergence, and is **authored by `gleipnir-code`** and
   reviewed via the normal **hardened-path** pipeline (two-pass spec-review +
   quality blast-radius + negative-check attestation). **No change is made to
   `gleipnir-code`'s deny set for `src/gleipnir/broker/**` at this time.** This
   is explicitly **NOT** a re-opening of D5's mechanism (the sidecar mechanism
   stays converged); it only confirms `gleipnir-code` is the author with no
   grant change. The latent Tier-3 grant question (whether to extend
   `gleipnir-code`'s deny set to `src/gleipnir/broker/**`) is **deferred** — a
   separate `tier3-coach` convergence if the operator ever wants it, not part of
   this slice.

---

## Problem Statement (as delegated)

The delegation states: the three `Judge`-shaped factories in
`src/gleipnir/engine/judges.py` (commit `75b0f88`) are built but have **NO LIVE
CALLER** — nothing invokes `Driver.advance(judge=…)` in a real running pipeline.
It asks me to scope "wire the judges' live caller" into a plannable brief,
treating **Seam 7** (live `tool.execute.after` hook) and **Seam 8** (real CI
attestation fetch) as *not-yet-built* dependencies, and to decide the scope
boundary, caller location, evidence source, and G-3.2 relationship.

## The material discovery (why this brief re-scopes the problem)

**The premise is stale. Seam 7 and Seam 8 are already built and wired.** During
Explore I grepped the repo for `tool.execute.after`, `Seam 7`, `Seam 8`, and the
`advance` entrypoint, then read the artifacts. The live caller the delegation
asks to design **exists end-to-end**:

| Component the delegation asks to "scope" | On-disk reality | File |
|---|---|---|
| Seam 7 live `tool.execute.after` hook (the trigger) | **BUILT** — a Tier-3 plugin that, on a completed `task` whose `subagent_type` is the bridge state's bound role (and only when armed), shells out to `bin/gleipnir-preflight advance`, fail-closed | `.gleipnir/plugins/advance-hook.ts` (437 lines) |
| The live caller of `Driver.advance(judge=…)` | **BUILT** — `advance_main` rehydrates the `Driver` from the bridge, dispatches the REAL judge for the current state via `build_judge_for_state`, calls `Driver.advance(judge)` | `src/gleipnir/preflight/advance.py` (767 lines) |
| The `advance` CLI subcommand the hook invokes | **BUILT + dispatched** | `src/gleipnir/preflight/__main__.py` L114–120 |
| Evidence readers (the "evidence source" question) | **BUILT** — `read_test_exit_code` (runs `bin/gleipnir-sandbox test -- --collect-only`), `read_reviewer_verdict` (reads the deposited `quality-reviewer` transcript), the caller-side transcript deposit | `advance.py` L258–279, L206–222, L182–203 |
| Seam 8 real CI attestation fetch | **BUILT** — `fetch_attestation` queries GitHub Actions REST for `config-scan.yml`'s status at `head_sha`, maps conclusion→`AttestationStatus`, stdlib-only `urllib` | `src/gleipnir/preflight/fetch_attestation.py` (267 lines) |
| G-3.2 GIT→GATE branch | **BUILT** — `advance_main` special-cases `PipelineState.GIT`, fetches a real `Attestation`, calls `Driver.attempt_gate` | `advance.py` L560–575 |
| Tests | **PRESENT** — `tests/test_advance_hook.py`, `tests/test_advance_entrypoint.py`, `tests/test_advance_hook.mjs`, `tests/test_fetch_attestation.py`, `tests/test_sequence_gate_byte_unchanged.py` | `tests/` |
| The converged plan + brief for this work | **PRESENT** | `.gleipnir/plans/seam7-seam8-wiring{,-brainstorm}.md` |

In other words, a later session ran a full brainstorm→plan→build for
`seam7-seam8-wiring` (operator-converged D1–D5, hardened pipeline) and landed
the live caller, the two hooks, the fetch, and the GATE branch. The
`SESSION-STATE.md` block the delegation quotes ("no live caller yet; requires
Seam 7 + Seam 8") is from *before* that session and was never updated to reflect
the seam7-seam8 work. **The delegation is asking me to design something that is
already done.**

**The genuine remaining gap (found by grep, not assumed).** The Seam-8 GIT→GATE
branch reads run identity from a D5 sidecar file
`.gleipnir/var/run/pipeline-run.json` via `read_pipeline_run_identity`
(`advance.py` L315–351). That is the **read** side. The **write** side — the
code that actually creates/updates that sidecar with `{pipeline_id, head_sha}`
at commit time — is **NOT built**:

- `grep -r "pipeline-run\|pipeline_run\|head_sha\|PIPELINE_RUN" src/gleipnir/broker`
  → **zero matches** (verified this session).
- The converged parent plan (`seam7-seam8-wiring.md`, Trace table + Assemble
  Phase 3 step 5) assigns that write side to the git broker's `commit_changes`
  (`src/gleipnir/broker/git/mcp_server.py`).
- A dedicated follow-on plan, `.gleipnir/plans/seam8-d5-sidecar-write-diff.md`,
  drafted the **ready-to-apply diff** for that write side, and records that
  quality-review "confirmed this side effect was never actually added — a
  genuine spec-conformance gap against that step." That diff was drafted but,
  per the broker grep above, **never applied**.

**Consequence (the real, functional gap).** Because nothing writes the sidecar,
`read_pipeline_run_identity` returns `None` on every real run → `advance_main`
raises `MissingRunIdentity` at the GIT state → **`attempt_gate` is never reached
→ GATE is unreachable in a live run.** The three *judged* transitions
(SPEC_REVIEW / TEST / QUALITY) are fully wired and reachable; the **GATE
(G-3.2 close-out) transition is wired-but-inert** because its one input (the
sidecar) is never produced.

## Constraints (inherited from the built body of work — LOCKED, not re-opened)

These are already operator-converged in `seam7-seam8-wiring.md` and must not be
re-litigated by any next slice:

- **D5 mechanism = sidecar** (`.gleipnir/var/run/pipeline-run.json`,
  framework-written / agent-read-only). `StateMarker` must stay byte-identical
  (D5-marker rejected); no second HMAC/digest for the sidecar (plain-file
  integrity from the existing `.gleipnir/var/run/` agent-unwritable grant class).
- **The sidecar's `head_sha` write side belongs in the git broker's
  `commit_changes`** (framework-process write, not a `git-ops` agent tool call),
  sourcing `pipeline_id` from `GLEIPNIR_PIPELINE_ID` per the Phase-2 convention.
- **Engine purity**: zero edits to `engine/__init__.py`, `driver.py`,
  `judges.py` (call-site-only). stdlib-only enforcement core.
- **No self-attestation**; fail-closed on any uncertainty; default-OFF /
  armed-only; Tier-3 unreachability of hook/key/driver/fetch subcommand.
- **The two D3 honest caveats stand**: config-scan attests config-scoping, not
  full artifact correctness; E-1 credential isolation is cooperative-policy
  (structural only under S-2).

## Approaches Considered

Because the primary deliverable the delegation asked for **already exists**, the
approaches are not "how to build the live caller" — they are "**given the caller
is built, what is the correct next action?**" The decision point is a
prioritisation / go-no-go among genuinely distinct next steps.

### Approach A: Report the stale premise; scope ONLY the real gap (D5 sidecar write side)

**Summary:** Surface to the operator that Seam 7/8 + the live caller are already
built, and re-scope the "next slice" to the one genuine functional gap: apply
the already-drafted D5 sidecar `head_sha` write side in `commit_changes` (per
`seam8-d5-sidecar-write-diff.md`) + its tests, so the GIT→GATE branch becomes
live rather than inert.

**Tradeoffs:**
- Pro: Targets the *actual* gap found by grep (write side absent → GATE
  unreachable), not a phantom one. Highest integrity value per unit effort:
  turns a wired-but-inert G-3.2 close-out into a functioning one.
- Pro: The diff is already drafted and quality-reviewed as a plan
  (`seam8-d5-sidecar-write-diff.md`); this is largely an apply-and-test slice,
  small blast radius, all material tradeoffs (D5) already converged.
- Pro: Honours the operator's time — does not re-plan work that exists.
- Con: Touches `src/gleipnir/broker/git/mcp_server.py`, which is
  enforcement-bearing broker code (E-1 surface) and — per the parent plan — NOT
  in `gleipnir-code`'s deny set today, so the orchestrator must route that edit
  as enforcement code (a routing fact, flagged in the parent plan).

**Estimated Scope:** `src/gleipnir/broker/git/mcp_server.py` (write side), a new
`tests/test_*` for it; a doc/status correction. Complexity: **low–medium**.

**Risk:** low — the design is converged; the main risk is the E-1 routing of the
broker edit, which the parent plan already flagged.

### Approach B: Verify-and-attest only — confirm the built caller is genuinely green, correct stale docs, build nothing

**Summary:** Treat the finding as "the work is done but the records lied."
Run/confirm the existing seam7-seam8 test suite is green, correct
`SESSION-STATE.md` and any decision record that still says "no live caller /
Seam 7-8 not built," and explicitly record the D5-write-side gap as a known open
item — but do not apply the write side in this slice.

**Tradeoffs:**
- Pro: Cheapest; pure bookkeeping + verification; zero enforcement-code edits.
- Pro: Closes the *documentation* integrity gap (stale SESSION-STATE misled this
  very delegation — a real cost), and makes the D5-write gap explicit and
  tracked.
- Con: Leaves the functional GATE gap open — the GIT→GATE branch stays inert.
  Defers the only substantive remaining work.
- Con: A "verify + fix docs" slice may under-deliver against what the operator
  actually wants (a *working* end-to-end gated run).

**Estimated Scope:** `SESSION-STATE.md`, possibly a `decisions/` status line;
no `src/**`. Complexity: **low**.

**Risk:** low — but risks being judged too thin if the operator wanted the GATE
gap closed.

### Approach C: Full end-to-end live-run hardening (apply D5 write side + drive a real armed gated run + close residual seams)

**Summary:** The maximal slice: apply the D5 write side (Approach A), then
actually **arm and drive a real gated pipeline run end-to-end** (set
`GLEIPNIR_PIPELINE=on`, real bridge, real `GLEIPNIR_PIPELINE_ID`, real CI on a
commit), confirm the hook fires, the judges advance, the sidecar is written at
commit, and GATE is reached on genuine green CI — plus address any residual seams
that surface (e.g. the `advance-hook.ts` DRY duplication follow-up flagged in its
own header; the `gleipnir-code` deny-set-for-`src/gleipnir/broker/**` Tier-3
question the parent plan flagged).

**Tradeoffs:**
- Pro: Delivers the thing the delegation's *spirit* points at — a genuinely
  live, end-to-end gated run, not just wired components.
- Pro: Would be the first true dogfood of the whole G-5 + G-3.2 stack running
  live, which is high proof-value.
- Con: Large blast radius and multiple dependencies (real CI, real arming, S-2
  interactions, credential reachability E-1). Several sub-parts are
  multi-session and some are structural-only-under-S-2.
- Con: Scope-creep risk — bundles the converged small gap (D5 write) with
  open-ended live-run hardening and residual Tier-3 grant decisions that are
  themselves separate convergences.

**Estimated Scope:** broker write side + a live-run harness/runbook + residual
seam follow-ups + Tier-3 grant decisions. Complexity: **high**.

**Risk:** medium–high — depends on live CI + arming + possibly S-2; bundles
several independent decisions into one slice.

---

## Decision Analysis

**Framework selected:** **RICE Scoring** (prioritisation among distinct next
actions), cross-checked with the **Reversibility Filter** (is committing to one
next-action a two-way door?). Rationale: with the primary deliverable already
built, the live question is "which of A/B/C delivers the most real value per unit
effort right now," which is a reach/impact/confidence/effort ranking; the
Reversibility Filter confirms we can start narrow and widen.

**Reversibility pre-check:** Choosing A (or B) first, then widening to C later,
is a **Two-Way Door** — A is an additive, converged, well-bounded change; B is
pure bookkeeping; neither forecloses C. C-first is the only
harder-to-reverse path (it commits effort to open-ended live-run hardening before
the cheap functional gap is closed). → Fast-track eligible; RICE used to *rank*,
not to gate.

**RICE scores** (Reach = how much of the pipeline's proof-value it unlocks;
Impact = how much it moves "the gated pipeline actually works end-to-end";
Confidence = how sure the work is buildable *now* with converged decisions;
Effort in person-days, judgment estimates):

| Option | Reach | Impact | Confidence | Effort | RICE |
|---|---|---|---|---|---|
| A (apply D5 sidecar write side + tests) | 4 | 3 | 90% | 2 | **5.4** |
| B (verify + correct stale docs, build nothing) | 2 | 1 | 95% | 0.5 | 3.8 |
| C (full end-to-end live-run hardening) | 6 | 3 | 45% | 12 | 0.68 |

**Recommendation (advisory — the operator decides):** **Approach A**, with
Approach B's doc-correction folded in as a required side task (correct the stale
`SESSION-STATE.md`/records regardless of which build slice is chosen — the stale
record is what mis-scoped this very task and must be fixed). Treat **C** as the
sequenced end-state once A lands and a real armed run can be attempted, not as
this slice. A closes the one genuine functional gap (GATE is unreachable until
the sidecar is written), reuses an already-drafted-and-reviewed diff, keeps blast
radius small, and every material tradeoff it touches (D5) is already converged.

**Bias warnings:**
- ⚠️ *Scope Creep Bias detected (on Approach C):* "do the full end-to-end live
  run and clean up every residual seam" expands scope to avoid choosing the
  narrow, converged gap. C bundles the small converged D5-write change with
  open-ended live-run hardening and two separate Tier-3 grant decisions
  (`gleipnir-code` deny-set for `src/gleipnir/broker/**`; the `advance-hook.ts`
  DRY export follow-up) that are their own convergences. The recommendation
  forces the narrow choice (A) and names C's parts as *sequenced* follow-ons.
- ⚠️ *Sunk Cost / IKEA Effect detected (guarding Approach A itself):* "the diff
  is already drafted, so just apply it" is a pull toward A regardless of merit.
  Checked: A is recommended on its *future* value (it is the only option that
  makes GATE reachable), not because effort was already spent drafting the diff.
  The drafted diff lowers A's effort, but A would still be the highest-RICE
  option if the diff had to be written from scratch (Effort 3 → RICE 3.6, still
  above B and C).
- ⚠️ *Availability Heuristic detected (noted, not surfaced in full):* the D5
  write gap is salient precisely because I just found it by grep this session.
  Judged representative because it is a standing, load-bearing gap (GATE
  unreachable), not a one-off — but flagged so the operator can weigh it.

**A second, smaller decision the operator should also see (does the D5-write
slice go to the git broker at all, or is the sidecar write relocated?):** The
parent plan converged the sidecar write into `commit_changes`
(`src/gleipnir/broker/git/mcp_server.py`). That file is enforcement-bearing
broker code and — per the parent plan's own flag — is NOT in `gleipnir-code`'s
deny set today, so applying the write there raises a routing/authorship question
(who edits it) and a latent Tier-3 grant question (should `gleipnir-code`'s deny
set be extended to `src/gleipnir/broker/**`?). This is **not** a re-opening of D5
(the *mechanism* is converged); it is the authorship/routing consequence of D5
that the operator may want to rule on before the slice runs. It is surfaced here,
not decided.

---

## Open Questions (for the operator to resolve at convergence, relayed by the orchestrator)

1. **Which next action?** A (apply the converged D5 sidecar write side + tests,
   making GATE reachable), B (verify + correct stale records only), or C (full
   end-to-end live-run hardening)? *(Recommendation: A, with B's doc-correction
   folded in.)*
2. **Authorship/routing of the broker write (if A or C):** the D5 sidecar write
   lands in `src/gleipnir/broker/git/mcp_server.py` (enforcement-bearing, E-1
   surface, currently NOT in `gleipnir-code`'s deny set). Should that edit be
   routed as operator/Tier-3-authored enforcement code, and should
   `gleipnir-code`'s deny set be tightened to `src/gleipnir/broker/**`? *(A
   separate Tier-3 grant decision — candidate for a `tier3-coach` pass; flagged,
   not decided.)*
3. **Stale-record correction is required regardless:** `SESSION-STATE.md` (and
   any decision record still stating "no live caller / Seam 7-8 not built") must
   be corrected, because that stale record is what mis-scoped this task. Confirm
   the operator wants this done as part of whichever slice is chosen.

## Open Questions (for `gleipnir-plan` — Trace-stage detail only, once converged)

- The exact content of the D5 write side is already drafted in
  `.gleipnir/plans/seam8-d5-sidecar-write-diff.md` (read it; it sources
  `pipeline_id` from `GLEIPNIR_PIPELINE_ID`, writes `{pipeline_id, head_sha}`
  after the successful commit's `git rev-parse HEAD`). `gleipnir-plan` should
  plan from that diff, not re-derive it.
- Test shape for the write side: assert the sidecar is written with the correct
  `{pipeline_id, head_sha}` after a commit; assert `git-ops` the agent cannot
  write it (grant check); assert the read side (`read_pipeline_run_identity`)
  round-trips what the write side produces (the read side already has tests).
- Whether the durable seam7-seam8 + D5-write decisions should be persisted by the
  operator to a `decisions/` record (candidate:
  `decisions/engine-live-advance-wiring.md`), reconciling with
  `engine-state-bridge`, `engine-revert-edges`, `cognition-layer`, and the
  judge-wiring records.

## Scope Sketch (for the recommended Approach A, plan stage — not now)

| Area | Files/Modules Likely Affected |
|------|------|
| D5 sidecar write side (the real gap) | `src/gleipnir/broker/git/mcp_server.py::commit_changes` — write `{pipeline_id, head_sha}` to `.gleipnir/var/run/pipeline-run.json` after a successful commit (per the drafted diff) |
| Tests | `tests/` — new test for the write side + round-trip against `read_pipeline_run_identity`; grant-check that `git-ops` cannot write the sidecar |
| Stale-record correction (required) | `.gleipnir/plans/SESSION-STATE.md`; any `decisions/` line still stating Seam 7/8 unbuilt |
| Engine / driver / judges | **unchanged** (call-site-only; byte-stability acceptance check) |
| Bridge marker / golden fixture | **unchanged** (D5-marker rejected; MAC signing input byte-identical) |
| Tier-3 grant follow-up (flagged, separate convergence) | `.gleipnir/agents/gleipnir-code.md` deny set — whether to add `src/gleipnir/broker/**` (a `tier3-coach` decision, NOT this slice) |

---

_Convergence was surfaced by the ORCHESTRATOR to the operator (not by this
subagent), and the operator's decision is recorded in the `## Convergence`
section near the top: **Approach A selected** (apply the drafted D5 sidecar
write-side diff + tests to make GATE reachable), the stale-record doc-fix
confirmed required and in-flight under a separate session-scribe delegation, and
the D5 write routed to `gleipnir-code` as-is with no Tier-3 grant change. The
central finding — that the delegated "build the live caller" work is already
done on disk, and the one genuine remaining gap is the unbuilt D5 sidecar write
side (GATE currently unreachable in a live run) — plus the `## Decision
Analysis` above, are the deliberation record left intact behind that
convergence. Nothing here is planned or built by `gleipnir-brainstorm`; the
converged slice is handed to `gleipnir-plan`._
