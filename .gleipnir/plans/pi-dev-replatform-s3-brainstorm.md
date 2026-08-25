# Design Brief: pi.dev replatform — Step S3 (delegation model + depth cap; re-express `task`/`subagent_depth`)

> **Status: CONVERGED.** This brief began as the `gleipnir-brainstorm`
> subagent's Explore + Propose + `## Decision Analysis` output. Both material
> decisions (D-S3-A, D-S3-B) have since been converged by the OPERATOR via the
> orchestrator's `question` tool — legitimately, per L-C6 (the operator was
> reached through the orchestrator, NOT self-attested by this subagent). Both
> converged choices match the advisory recommendations exactly (no divergence);
> see the convergence note under `## Decision Analysis`. `gleipnir-plan` plans
> from these converged choices. The central finding — that S3's code-level work
> is essentially already built by S2 — is now an operator-ratified basis for
> closing S3, not merely a subagent recommendation.

## Problem Statement

Step S3 of the pi.dev replatform roadmap is "Delegation model + depth cap
(re-express `task`/`subagent_depth`)." Its build-order goal: *promote S1's
`delegate` proof to the real orchestrator→subagent model — a `delegate` tool
that creates a role-bounded child session, enforces the depth cap, and
guarantees the child inherits enforcement.* Its verbatim exit criterion:

> **"orchestrator can delegate to a bounded role, depth cap refuses runaway
> nesting, child cannot exceed its role's capability table."**

The genuine S3 question this session must answer is **not** "how do we build
delegation" — S2 already built and proved it (operator decision D-A "in-scope
now" pulled the whole `customTools` pass-through + nested-delegation +
end-to-end depth-cap slice of S3 forward into S2). The genuine question is:
**what, if anything, of S3's exit criterion is NOT yet satisfied by the
committed S2 code + tests, and is Open-Q1 (the in-process-vs-process-isolated
delegation boundary) acceptable as the FINAL delegation-isolation answer for S3
or must it be revisited before S3 can be called done?**

Per L-C36 discipline, this brief is grounded in the ACTUAL committed post-S2
code (`pi-package/src/{delegate,depth,activeRole,enforcement,roleTable}.ts` +
`pi-package/test/*.ts` + `pi-package/README.md`, all read directly this
session), not the build-order's or S1 README's now-stale characterization.

## Constraints

- **Scope is fixed by the build-order S3 exit criterion.** S3 must not expand
  beyond it. The criterion is about the delegation edge, the depth cap, and
  role-capability containment — nothing more.
- **S3 does NOT decide Open-Q2 (human-gate policy), Open-Q3 (MCP-broker
  reachability, → S6), or Open-Q4 (cutover, → S9).** Only Open-Q1 is load-bearing
  for S3, and only for S3's *finalisation* (per build-order [ASSUMPTION-2]:
  "it can start on the in-process assumption").
- **No new material tradeoff may be resolved by this subagent.** Anything the
  Decision Analysis surfaces is advisory and routed to the operator.
- **Re-expression, not port** (inherited Approach-B constraint): fit pi.dev's
  real model; do not preserve opencode shape for its own sake.
- **The correctness arbiter is the test suite run in-sandbox**
  (`bin/gleipnir-sandbox {test,lint} --profile pi`) — per the S2 README, 28/28
  green, lint clean, on real SDK code. Any S3 claim of "already proven" rests on
  that arbiter, not on prose.

## Explore Findings (grounded in the committed post-S2 code + tests)

### F1 — Delegation is fully built, in-process only; there is NO `runRpcMode` code anywhere

`grep` across all of `pi-package/src/*.ts`: the only delegation mechanism is
in-process `createAgentSession` (`delegate.ts` L76, L209). `runRpcMode` /
`--mode rpc` appears in NO source file — it is named only in prose (the original
brainstorm, `activeRole.ts`'s forward-looking comment L20). So the delegation
edge today is **exclusively in-process**, exactly per [ASSUMPTION-1]/[ASSUMPTION-2].
This is the concrete state Open-Q1 must now be judged against.

### F2 — The `delegate` tool is the real orchestrator→subagent model, not a stub

`delegate.ts` (255 lines) is the full model the S3 goal describes:
- `buildDelegateTool()` returns a real `registerTool`-shaped definition with an
  `execute` that creates a role-bounded child via `createAgentSession`, bounds
  it via `resolveChildTools(role)` (base+custom, DRY-sourced from the table),
  and projects `customTools` via `resolveChildCustomTools(role)` (L115–121).
- The self-referential recursion crux is built: a delegate-capable child role
  RECEIVES the real `buildDelegateTool()` definition back (L188–190), so nested
  delegation is reachable end-to-end; a non-delegate child receives `[]`
  (deny-by-default through the pass-through).
- Depth cap wraps every child via `withDepthGuard` (`depth.ts`), refusal is
  graceful (`textResult(err.message)`, L245), and the counter is `finally`-safe.
- Child enforcement is guaranteed by explicit `extensionFactories:
  [enforcementExtension]` re-wiring (D6-settled: there is NO auto-inherit path;
  the explicit wiring is the ONLY mechanism, proven against real SDK code).

### F3 — Every clause of the S3 exit criterion maps to an existing, passing AC

Clause-by-clause (see the verdict table below for citations). The short version:
depth-cap (clause 2) and role-capability containment (clause 3) are **fully
proven end-to-end** on real SDK code (AC-6/7/8/13/14; AC-9/9-E2E/12/16/17/18/19).
Clause 1 ("orchestrator can delegate to a bounded role") is proven **at the
mechanism level** (the `delegate` tool exists, `orchestrator` holds it in its
allow-set, it creates a bounded child) — but the **top-level orchestrator
SESSION actually invoking `delegate` as its live dispatch method is NOT
exercised**, because that needs a model-driven turn (the named `--network=none`
residual gap, S2 README "Live-model-turn gap").

### F4 — The `orchestrator` role is seeded but its live dispatch is untested

`activeRole.ts` + `enforcement.ts` seed `orchestrator` as the top-level role at
`session_start` via `seedActiveRoleIfEmpty(PRIMARY_ROLE)` (AC-15, unit-tested
through the real registered `session_start` handler). So the wiring for "the
orchestrator is the active role and may call `delegate`" is present and tested.
What is NOT tested: a real top-level orchestrator session, under a live model,
choosing to emit a `delegate` tool call that spawns a real bounded child and
runs a real child model turn. This is the SAME residual gap S2 named, not a new
S3 gap — and it is a network/auth limitation of the sandbox, not a
wiring-correctness hole.

### F5 — The named residual gaps are all inherited from S1/S2 and are empirical, not architectural

Per S2 README "Named residual limits": (a) the live-model-turn gap
(`--network=none` blocks provider auth); (b) AC-13/14's nested mechanism is
direct `execute` re-invocation, not `emitToolCall` dispatch (a
description-accuracy caveat `quality-reviewer` already accepted); (c) arg-level
`event.input` enforcement is deferred to S3/S7 as the E-1 seam (recorded as
`bounds` metadata, NOT enforced). **Item (c) is the one place the roadmap's own
S3 wording ("re-express `task`/`subagent_depth`") could be read to demand more
than S2 built** — see D-S3-B below.

## Decision Analysis

> Two decision points fired during Explore/Propose. D-S3-A (Open-Q1
> convergence) is the material decision the delegation brief flagged. D-S3-B
> (is there net-new S3 code work, or is S3 convergence-only) is the "do not
> manufacture busywork" decision. Depth level assumed `standard` (no
> `.aetos/args/defaults.yaml` in this tree): auto-selected primary framework
> per decision, all 12 bias detectors run, ≤3 warnings surfaced. The
> recommendations below were ADVISORY at authoring time; both have since been
> converged by the operator (see the convergence note immediately below).

> **CONVERGENCE NOTE (operator-via-orchestrator, legitimate per L-C6 — NOT
> self-attested).** After this brief was authored, the orchestrator put both
> material decisions to the operator via its `question` tool (a subagent's
> `question` cannot reach the operator; the orchestrator's can). The operator
> converged both, matching the advisory recommendations exactly (no divergence):
> - **D-S3-A → (a) "Ratify in-process as final for S3."** In-process
>   `createAgentSession` is S3's final delegation-isolation answer. An RPC
>   (`runRpcMode`) variant is tracked as S6-conditional future work only, NOT
>   built now.
> - **D-S3-B → Option 2 "Convergence-only."** S3 closes as a convergence/closure
>   step: ratify Open-Q1, formally close the exit criterion clause-by-clause
>   against the already-passing S2 evidence, record the live-model-turn gap as a
>   carried sandbox-regime residual, and defer arg-level enforcement to S7. No
>   new delegation code.
>
> The analysis below is UNCHANGED from authoring — this note records the
> operator's converged choices; it does not revise the reasoning that produced
> the recommendations.

---

### D-S3-A — Open-Q1: is in-process `createAgentSession` the FINAL delegation-isolation answer for S3?

**Decision:** does the operator (a) **ratify in-process `createAgentSession`
as the final delegation-isolation answer for S3**, accepting that a future
process-isolation (`runRpcMode`) variant, if the S6 sandbox/broker convergence
demands it, is tracked as future work and does NOT block S3's closure now; **vs.**
(b) **require process-isolation (`runRpcMode`) NOW** before S3 can close; **vs.**
(c) **a hybrid** (in-process for some roles, RPC for the roles that will
eventually reach brokers/untrusted content).

**Type:** Go/no-go with irreversibility asymmetry → **Reversibility Filter →
Regret Minimisation** (primary per auto-selection: go/no-go), with a
**Second-Order Thinking** cross-check (architectural, long-horizon consequence).

**Reversibility Filter:**

- **Reversal cost of (a) ratify in-process:** LOW → **Two-Way Door.** Adding an
  RPC variant later is *additive*: `delegate.ts` is explicitly SRP-scoped to
  "construct + bound + run a child session, and nothing else (does NOT decide
  in-process-vs-RPC isolation — that is Open-Q1)" (module header L1–6), and
  `activeRole.ts` L20–22 already records that its stack model "does not need to
  change" under a move to `runRpcMode` because each process gets its own module
  instance. So the code was deliberately built to make the isolation choice a
  later, swappable decision. No data migration, no external commitment, no
  API lock-in. Reversal = introduce a second `execute` path guarded by a
  per-role flag; the enforcement table, depth cap, and active-role model are
  all isolation-agnostic and unchanged.
- **Reversal cost of (b) require RPC now:** HIGH → **One-Way-ish Door** *in
  effort terms.* It re-opens the entire delegation edge that S2 just proved
  green (28/28), adds a subprocess/JSONL transport, a cross-process depth-cap
  and active-role propagation problem (the in-process module-scope counter no
  longer spans a process boundary), and cross-process enforcement re-wiring —
  before any concrete requirement for it exists (Open-Q3 broker reachability is
  still undecided; S6 is where isolation-for-brokers actually becomes load-
  bearing). It front-loads S6-shaped work into S3 against no proven need.
- **Verdict:** (a) is a Two-Way Door; (b) is a high-cost, low-current-need
  One-Way-ish Door. → Fast-track toward (a); confirm with Regret Minimisation
  given the "final answer for S3" framing raises the stakes.

**Regret Minimisation (regret horizon: the S3→S6 window, ~the rest of the
replatform):**

| Option | Regret if wrong | Regret if not chosen | Max regret |
|---|---|---|---|
| (a) Ratify in-process as S3-final; track RPC as S6-conditional future work | **4** — if S6 later proves some role MUST be process-isolated (e.g. a broker-reaching or untrusted-content role), S3's edge needs an added RPC variant. But this is *additive* (per the SRP boundary above), tracked, and lands where the requirement actually is (S6) — not a rebuild, and the in-process edge stays valid for every role that does not need isolation | 3 — a later step must add the RPC variant; but that is expected, flagged work, not a surprise | **4** |
| (b) Require RPC now before S3 closes | **8** — re-opens a green, proven edge; solves an isolation problem no converged requirement yet demands (Open-Q3/S6 undecided); cross-process depth-cap + active-role + enforcement propagation is net-new complexity built speculatively; delays S3 (which unblocks S4 engine) on S6-shaped work | 2 — if isolation turns out genuinely needed, doing it now would have saved a later pass — but only *if* it's needed, which is unproven | **8** |
| (c) Hybrid (in-process default + RPC for broker/untrusted roles) | **6** — encodes a per-role isolation policy BEFORE the S6/Open-Q3 convergence that would tell us WHICH roles need it; risks guessing the partition wrong and building transport for roles that never need it | 4 — if the eventual answer is "some roles need RPC," a hybrid was the right shape — but the partition can't be drawn correctly until Open-Q3 is decided | **6** |

**Minimum-regret choice: (a)** — max regret 4, and its downside is *additive,
tracked, lands-where-needed* work, not a rebuild.

**Second-Order Thinking cross-check (architectural):**

- **Near term (S3→S4):** (a) keeps the proven edge, unblocks the S4 engine
  immediately. **Second-order:** the engine (S4) sequences over a *stable*
  delegation edge rather than one being simultaneously re-architected — lower
  compounding risk.
- **Far term (S6→S9):** **the key insight** — the isolation requirement is
  *derived from the broker/untrusted-content boundary (S6/Open-Q3)*, which is
  itself undecided. Deciding delegation isolation NOW (option b/c) means
  deciding a *downstream-dependent* question before its input exists — the
  same "decide from a not-yet-existing input" antipattern L-C20 warns about.
  Ratifying in-process now, with an explicit "RPC variant is S6-conditional
  future work" tracked item, sequences the decision to WHERE its input arrives.
  The SRP boundary in `delegate.ts` is what makes this safe: isolation is not
  yet baked in, so deferring it costs nothing structurally.
- **Verdict: Proceed with (a); monitor the S6/Open-Q3 convergence as the
  trigger to revisit.**

**Bias warnings:**
- ⚠️ **Sunk Cost Fallacy (checked, does NOT bind):** ratifying in-process could
  look like "we already built it, so keep it." But the case for (a) is NOT
  past investment — it is the *future-value* asymmetry: (b) builds speculative
  cross-process complexity against no converged requirement, and the SRP
  boundary means (a) forecloses nothing. Asked "if we were starting today with
  no S2 code, which would we choose?" — still (a): you would not build RPC
  transport before the broker boundary that needs it is decided. The bias is
  named and ruled out, not silently relied on.
- ⚠️ **Status Quo Bias (checked, low confidence):** in-process is the current
  state, which could get a free pass. Scrutinised: it is not inertia — the
  Reversibility + Second-Order analyses independently favour (a) on merit
  (Two-Way Door, downstream-dependent input). Applied equal scrutiny to (b)/(c)
  and they lose on *current* merits, not on change-cost alone.
- ⚠️ **Scope Creep Bias (checked, applies to (c)):** the hybrid (c) expands S3
  to encode a per-role isolation policy that belongs to the S6/Open-Q3
  convergence — deferring the real decision by broadening scope. Forcing the
  choice now, (a) is the narrowest that closes S3.

**Recommendation (ADVISORY at authoring; since CONVERGED by operator — see convergence note above):** **(a) Ratify in-process
`createAgentSession` as the final delegation-isolation answer for S3**, with an
explicit tracked future-work item: *"if the S6 sandbox/broker convergence
(Open-Q3) requires process isolation for any role, add an RPC (`runRpcMode`)
variant to the delegation edge at S6 — the `delegate.ts` SRP boundary and the
`activeRole.ts` per-process stack were built to make this additive."* This is
the minimum-regret (4), Two-Way-Door, downstream-input-respecting choice, and
it unblocks S4 without re-opening a proven edge. (b) is affirmatively NOT
recommended (speculative rebuild against no converged requirement). (c) is
premature (can't partition roles correctly until Open-Q3 is decided).

---

### D-S3-B — Is there genuinely NET-NEW code-level work for S3, or is S3 convergence-only?

**Decision:** given S2's overlap, does S3 have (1) **genuine net-new code work**
(e.g. the orchestrator's real session dispatch wiring; arg-level enforcement;
an RPC variant), or is S3 (2) **convergence-only** — ratify Open-Q1 (D-S3-A) and
formally close the exit criterion against the already-passing S2 ACs, with no
new code?

**Type:** Binary choice (net-new work vs convergence-only) → **Reversibility
Filter → Pros-Cons-Fixes** (primary per auto-selection), grounded in the
clause-by-clause exit-criterion verdict below.

**Grounding — clause-by-clause verdict (the load-bearing evidence):**

| Exit-criterion clause | Verdict | Citation (committed S2 code + passing tests) |
|---|---|---|
| **1. "orchestrator can delegate to a bounded role"** | **ALREADY PROVEN at the mechanism level; one inherited empirical gap at the live-session level** | `delegate` tool exists + creates a role-bounded child: AC-5, AC-9, **AC-9-E2E** (real `createAgentSession` child, real `ExtensionRunner.emitToolCall` dispatch). `orchestrator` holds `delegate` in its allow-set (`roleTable.ts` L134) and is seeded as the top-level active role: AC-15. **GAP (inherited, empirical, not architectural):** a *live-model-driven* top-level orchestrator session emitting a real `delegate` call is not exercised — the `--network=none` provider-auth limit (S2 README "Live-model-turn gap"). |
| **2. "depth cap refuses runaway nesting"** | **FULLY PROVEN, end-to-end** | AC-6 (refusal at depth===cap), AC-7 (nested caught by same cap), AC-8 (counter `finally`-restored on throw), **AC-13/AC-14** (real nested re-invocation of the real `delegate` execute refused past cap; counter restored to 0). |
| **3. "child cannot exceed its role's capability table"** | **FULLY PROVEN, end-to-end** | AC-9 + **AC-9-E2E** (real child's real `ExtensionRunner` blocks a denied tool `write`, allows `read`, for role `gleipnir-code`), AC-12 (deny-by-default through the `customTools` pass-through — a non-delegate child cannot re-delegate), AC-16 (deny-by-default all 8 roles), AC-17 (G-2 sole-holder), AC-18 (SDK vocab), AC-19 (frozen table, no runtime widening). |

So: **2 of 3 clauses are fully proven end-to-end; clause 1 is proven at the
mechanism level with one inherited, empirical (network/auth), non-architectural
gap** that is unclosable in the current `--network=none` sandbox regardless of
what S3 builds.

**Reversibility Filter:** declaring S3 convergence-only is a **Two-Way Door** —
if a genuine net-new gap is later found, an S3-supplement slice is cheap to add.
Manufacturing net-new code to justify a stage (option 1 without a real gap) is
the harder-to-undo direction: it widens blast radius against no requirement and
invites the exact "manufacture busywork" antipattern the delegation warned
against. → toward convergence-only, confirmed by Pros-Cons-Fixes.

**Pros-Cons-Fixes:**

*Option 1 — treat S3 as net-new code work:*
- Pro: would let S3 close the clause-1 live-session gap IF that gap were
  closable. *Fix attempt:* it is NOT closable in `--network=none` (no provider
  auth in-container) — so this "pro" is unreachable without changing the sandbox
  regime, which is Open-Q1/S-2 territory, not S3 delegation work. Fix fails.
- Pro: arg-level enforcement (E-1 seam) is nominally "S3/S7." *Fix:* but the
  exit criterion says nothing about arg-level bounds; `roleTable.ts` explicitly
  defers `event.input` inspection to "S3/S7" as the E-1 seam and records bounds
  as *metadata*. Folding arg-level enforcement into S3's *closure* would EXPAND
  the exit criterion (which is coarse tool-presence containment, already
  proven). It is legitimately deferrable to S7, and pinning it to S3 is a scope
  decision for `gleipnir-plan`/the operator, not a gap in the exit criterion.
- Con: there is no net-new *delegation* code the exit criterion demands that S2
  did not build. *Fix:* none — this is the honest finding, not a defect.

*Option 2 — treat S3 as convergence-only (recommended):*
- Pro: matches the honest evidence — all three clauses are satisfied to the
  limit the sandbox allows; the only unclosed item is an inherited empirical
  gap no S3 code can close.
- Pro: avoids manufacturing busywork to justify a stage (the delegation's
  explicit caution).
- Pro: S3's real remaining act — ratifying Open-Q1 (D-S3-A) and formally
  closing the exit criterion — is genuine, load-bearing work (it unblocks S4
  and settles a carried-forward open question), just not *code* work.
- Con: "a stage with no code" may look like a skipped stage. *Fix:* it is not
  skipped — it is a convergence + formal-closure stage. The clause-by-clause
  verdict IS S3's deliverable; the operator's Open-Q1 ratification IS its gate.
- Con: the inherited live-model-turn gap remains open after S3 "closes."
  *Fix:* record it explicitly as a carried, sandbox-regime-bound residual (it
  is already named in the S2 README); it is not an S3 delegation defect and
  cannot be closed by delegation code.

**Post-fix verdict:** Option 2 (convergence-only) is Viable and honest; Option 1
is Not Viable *as delegation work* (its only genuine candidate — arg-level
enforcement — would expand the exit criterion and is legitimately S7).

**Bias warnings:**
- ⚠️ **Scope Creep Bias (primary):** the pull to "find net-new code for S3" so
  the stage has an artifact is exactly scope-expansion-to-avoid-a-clean-finding.
  The exit criterion is satisfied; expanding S3 to arg-level enforcement or a
  speculative RPC variant is deferred-decision-making with compounded cost.
- ⚠️ **IKEA Effect (checked, low confidence):** "S3 should build something" can
  be a builder's-bias to produce code. Evaluated on merit: the evidence says the
  code exists and passes; the honest deliverable is a verdict + a convergence,
  not more code.
- ⚠️ **Sunk Cost Fallacy (inverse, checked):** the D-A divergence at S2 ("pull
  S3's delegation forward") was a real operator investment; there could be a
  pull to "get S3's money's worth" by finding more for it to do. Ruled out: the
  D-A pull-forward is precisely WHY S3 is now convergence-only — that was the
  operator's chosen consequence, honestly recorded, not a reason to backfill S3.

**Recommendation (ADVISORY at authoring; since CONVERGED by operator — see convergence note above):** **Option 2 — S3 is
CONVERGENCE-ONLY.** S3's code-level delegation work was already built and proven
by S2 (the D-A "in-scope now" pull-forward). S3's genuine remaining work is:
(i) the operator's Open-Q1 ratification (D-S3-A), and (ii) formally closing the
exit criterion against the already-passing S2 ACs, recording the inherited
live-model-turn gap as a sandbox-regime-bound residual and arg-level enforcement
as legitimately-deferred-to-S7. Do NOT manufacture net-new delegation code to
justify the stage. **Flag for `gleipnir-plan` (NOT this subagent's to decide):**
because S3 touches only prose/config (a closure record, possibly a decision-
record amendment — no `src/**` change), the "prose/config-only track" of
`stage-role-map.md` likely applies, which would make S3's plan very thin (a
single spec-review pass, or the hardened path if it amends a Tier-3 policy file).
That routing is a Trace/plan-stage computation on the touched-path set, not a
brainstorm decision — named here only so the plan is scoped realistically.

---

## Selected Approach (per-decision — OPERATOR-CONVERGED)

| Decision | Converged choice | Framework | Status |
|---|---|---|---|
| **D-S3-A** Open-Q1 isolation | **(a) Ratify in-process as S3-final; RPC is S6-conditional future work** | Reversibility Filter → Regret Minimisation + Second-Order cross-check | **CONVERGED — operator, via orchestrator (matches recommendation, no divergence)** |
| **D-S3-B** net-new vs convergence-only | **Option 2 — S3 is convergence-only; no net-new delegation code** | Reversibility Filter → Pros-Cons-Fixes | **CONVERGED — operator, via orchestrator (matches recommendation, no divergence)** |

Both recommendations point the same way: **S3 is a convergence-and-closure step,
not a code step.** The single most important thing to surface to the operator is
that the honest finding is "S3's code is already done" — and to confirm the
operator accepts closing S3 on that basis (D-S3-B) after ratifying the
in-process isolation answer (D-S3-A).

## Open Questions (for `gleipnir-plan`, from the converged choices)

- **[D-S3-A follow-through]** If the operator ratifies (a), the plan must record
  the tracked S6-conditional RPC future-work item somewhere durable (a decision-
  record amendment naming Open-Q1 as "resolved for S3 = in-process; revisit at
  S6 iff Open-Q3 demands isolation"). Whether that durable record is written now
  or at S6 is a plan/operator call; note no roster subagent can write Tier-3
  (D-D/L-C27), so any decision-record write routes to the operator/primary
  session.
- **[D-S3-B follow-through] Prose/config-only-track routing is a plan-stage
  Trace computation, not a brainstorm decision.** `gleipnir-plan` must compute
  S3's touched-path set `P` and route per `stage-role-map.md` Axis-1/Axis-2: if
  S3 touches only `plans/**` + a `decisions/**` prose record (no `src/**`, no
  `E`-set enforcement path), it is light-path (single collapsed spec-review
  pass); if it amends `stage-role-map.md` itself or another `E`-set file, it is
  hardened path (two non-fusing rubrics + negative-check attestation). Flagged,
  not decided.
- The inherited **live-model-turn gap** (a real top-level orchestrator session,
  under a live model, emitting a real `delegate` call and running a real child
  model turn) cannot be closed under `--network=none`. The plan should record it
  as a carried, sandbox-regime-bound residual — NOT as an S3 delegation defect,
  and NOT something S3 code can close. (If the operator ever wants it closed,
  that is an Open-Q1/S-2 sandbox-regime question — a network/auth-in-sandbox
  decision — not a delegation-model one.)
- **Arg-level (`event.input`) enforcement** (the E-1 seam; per-path/per-arg
  bounds currently `bounds` *metadata* in `roleTable.ts`) is legitimately
  deferred to S7. If the operator or plan wants any of it pulled into S3, that
  is a scope decision expanding the exit criterion — surface it explicitly, do
  not silently absorb it (the D-A precedent: a pull-forward must be named).

## Scope Sketch

| Area | Artifact / expectation for S3 |
|---|---|
| Delegation code (`delegate.ts`, `depth.ts`, `activeRole.ts`) | **No change expected** — already built + proven by S2 (F1–F5). S3 does not re-open the proven edge. |
| Enforcement / role table (`enforcement.ts`, `roleTable.ts`) | **No change expected** — role-capability containment (clause 3) already proven; arg-level enforcement is S7. |
| Tests (`pi-package/test/*.ts`) | **No new delegation tests expected** — the exit criterion's clauses map to existing passing ACs (AC-5/6/7/8/9/9-E2E/12/13/14/15/16/17/18/19). |
| S3 closure record | The genuine S3 deliverable: a formal exit-criterion closure (clause-by-clause verdict) + the operator's Open-Q1 ratification. Path/tier decided by `gleipnir-plan` (Tier-0 plan/closure vs Tier-3 decision-record amendment — the latter operator-authored). |
| Open-Q1 durable record | A decision-record note resolving Open-Q1 for S3 (= in-process), with the S6-conditional RPC future-work item. Tier-3, operator-authored (no roster subagent can write it). |

## Design Principles (Gate 1)

**Routing:** this brief is **prose-only** (`P = { this .md file }`, `P ∩ X = ∅`
— no executable artifact). Per `plan-format.md` case (iii), SOLID/DRY/SRP are
**`N/A — no executable artifact`**.

**Design Intent (specific, falsifiable):** *This brief must (1) give a
clause-by-clause verdict on the build-order S3 exit criterion, each clause
marked ALREADY-PROVEN (with an AC/test citation from the committed post-S2 code)
or GENUINELY-STILL-OPEN (with the named gap), grounded in the ACTUAL committed
code per L-C36 (not the stale build-order/README characterization); (2) surface
Open-Q1 (D-S3-A) with a named framework + a run of the 12 bias detectors + an
advisory recommendation, WITHOUT converging it (a subagent cannot reach the
operator, L-C6); and (3) state plainly whether S3 has net-new code work or is
convergence-only (D-S3-B), without manufacturing busywork to justify the stage.*
A reviewer can falsify this by finding: (a) any exit-criterion clause without a
proven/open verdict or without a citation; (b) any verdict contradicted by the
actual committed code/tests; (c) Open-Q1 recorded as converged (self-attested)
rather than surfaced; (d) a manufactured net-new-code recommendation with no
genuine gap in the exit criterion behind it; or (e) the brief expanding S3's
scope beyond the exit criterion (e.g. pinning arg-level enforcement or an RPC
variant into S3 as required, rather than flagging them as S7/S6-conditional).
