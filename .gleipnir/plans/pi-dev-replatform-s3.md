# ATLAS Plan / Closure Record: pi.dev replatform — Step S3 (delegation model + depth cap; re-express `task`/`subagent_depth`)

> **Status: PLAN / FORMAL CLOSURE RECORD (Tier-0, transient).** Written by
> `gleipnir-plan` from the **CONVERGED** design brief
> `pi-dev-replatform-s3-brainstorm.md` (both material decisions operator-converged
> via the orchestrator's `question` tool, matching the advisory recommendations
> with no divergence). Per that convergence, **S3 is a convergence-and-closure
> step, not a code step** (D-S3-B): its deliverable is a formal, clause-by-clause
> closure of the build-order S3 exit criterion against the already-passing S2
> evidence, plus the ratification of Open-Q1 (D-S3-A). This plan does NOT re-open
> or re-derive D-S3-A or D-S3-B — they are converged inputs. It adds **no**
> `src/**` / code-level Assemble steps. It does NOT write the Tier-3
> decision-record note it names for the operator (no roster subagent can write
> Tier-3; D-D / L-C27).

## GOTCHA pre-flight (output visibly, per methodology)

- **Goals check (`goals/manifest.md`).** The relevant goal is **Plan format**
  (`goals/plan-format.md`) — followed here (Decisions index, Architect, Trace,
  Link, Assemble, Stress-test, Execution Workflow, Design Principles, case
  (iii)). No pipeline-sequencing goal is invoked (deliberately absent per the
  manifest's G-5 rule; the orchestrator sequences).
- **Order.** Plan-before-code confirmed. This is the `plan` stage. Because S3 is
  convergence-only (D-S3-B, operator-converged), there is no code stage to
  precede — the `test`/`code`/`git`/`gate` transitions carry an attested
  "N/A — no executable artifact" (see Pipeline routing statement).
- **Gaps named.** None in goals. Two **carried residuals** (NOT S3 defects, NOT
  planning gaps) are recorded explicitly in Trace and Stress-test: (a) the
  inherited live-model-turn gap (`--network=none` provider-auth limit); (b)
  arg-level `event.input` enforcement (E-1 seam, deferred to S7). Neither is
  closable by S3, and neither blocks S3 closure.
- **Convergence provenance.** Both decisions (D-S3-A, D-S3-B) come from the
  brief's CONVERGENCE NOTE (operator, via the orchestrator's `question` tool,
  legitimate per L-C6). This subagent did not and cannot converge anything; it
  formalizes what was handed back.
- **Material-tradeoff check (my capability boundary).** No new material tradeoff
  arises in this plan. The one durable act S3 implies — recording Open-Q1's
  ratification in a Tier-3 decision record — is NAMED here for the operator to
  author (§ "Tier-3 decision-record note"), not resolved or written by me.

## Pipeline routing statement (REQUIRED — read before anything else)

**Light path — single collapsed spec-review pass.** `test`/`code`/`git`/`gate`
carry an attested **"N/A — no executable artifact"** transition (per
`stage-role-map.md`'s "Prose/config-only track", the
`plans/lesson-escalation-process.md` precedent).

- **Touched-path set `P`** (what this plan's execution actually writes):
  - `.gleipnir/plans/pi-dev-replatform-s3.md` — **this closure-record plan
    itself** (Tier-0, my writable path). Created by this delegation.
  - *(named, NOT written by me)* a Tier-3 decision-record note the operator
    authors to make the Open-Q1 ratification durable — see § "Tier-3
    decision-record note". **This is NOT in `P`**: I neither write it nor can
    write it (Tier-3, operator-only per D-D / L-C27). It is listed as a named,
    to-be-created-by-operator artifact, not a path this plan touches.

  So the effective `P` this plan touches is exactly **`{ .gleipnir/plans/pi-dev-replatform-s3.md }`**.

- **Axis-1 disqualifier check (`X`).** `P ∩ X = ∅`. The single member of `P` is
  a `.gleipnir/plans/**` markdown file — no `src/**`, no `tests/**`, no
  `hooks/**`, no `bin/**`, no Makefile/`*.mk`/`Containerfile*`, no `.github/**`,
  no standalone `*.yml`/`*.yaml`, no `*.sh|*.bash|*.py|*.js|*.ts|*.rs|*.go`, no
  `+x`/shebang content. **Zero executable/interpreted artifacts** → the plan IS
  track-eligible (contrast S2, which was code and ran the full 8-stage
  pipeline).
- **Axis-2(a) enforcement-path set `E` check — STATED EXPLICITLY (per the
  delegation).** `P` contains **NO** member of `E`. Confirmed by exact-path
  inspection of the single touched file:
  - it is **not** under `.gleipnir/agents/**`, `.gleipnir/plugins/**`,
    `.gleipnir/sandbox/**`, `.gleipnir/policy/**`, `.gleipnir/keys/**`;
  - it is **not** `stage-role-map.md` itself (this plan does NOT amend the
    stage-role map);
  - it is **not** `AGENTS.md` (this plan does NOT amend AGENTS.md);
  - it is **not** any agent frontmatter (this plan touches no `agents/*.md`);
  - it is **not** `opencode.jsonc` / `**/opencode.json`;
  - it is **not** any enumerated repo-root cross-cutting file (`.gitignore`,
    `.envrc`, `pyproject.toml`, `.gitattributes`, `.gitmodules`).
- **Axis-2(b) content-rule check.** The closure record contains **no**
  grant/enforcement pattern `G`: no `permission:`/`tools:` block, no
  `edit|write|task|bash|webfetch` capability line with `allow`/`deny`, no
  JSON(C) enforcement key, no new/edited row in a `stage-role-map.md` binding
  table, no `keys/**` digest line. It only *cites* AC names and *describes* the
  already-committed S2 table in prose — it declares no grant. (It DISCUSSES the
  role table; it does not RE-EXPRESS or edit it. Discussion of an enforcement
  fact in a closure record is not an enforcement grant.)
- **Routing consequence.** Track-eligible (Axis-1) + no `E`-set path (Axis-2(a))
  + no `G`-pattern (Axis-2(b)) = **low-consequence prose → LIGHT PATH.** Stages
  collapse to a **single `quality-reviewer` spec-review pass** (the
  `spec-review` and `quality` rubrics run together — there is no
  post-implementation executable artifact to blast-radius-review);
  `test`/`code`/`git`/`gate` each carry an attested **"N/A — no executable
  artifact"** transition. The hardened-path two-non-fusing-rubric +
  negative-check-attestation machinery does **NOT** apply (that is for
  enforcement-bearing config edits; this plan edits none).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-S3-A | Open-Q1: is in-process `createAgentSession` the FINAL delegation-isolation answer for S3? | **(a) Ratify in-process as S3-final; RPC (`runRpcMode`) is S6-conditional future work, tracked, not built now** | (b) Require RPC now before S3 closes; (c) Hybrid per-role isolation now | **Operator-converged (via orchestrator, L-C6; matches brainstorm recommendation, no divergence).** Reversibility Filter (a = Two-Way Door; b = high-cost One-Way-ish) → Regret Minimisation (max regret 4 for (a) vs 8 for (b), 6 for (c)) → Second-Order (isolation is derived from the S6/Open-Q3 broker boundary, still undecided — deciding it now is the "decide from a not-yet-existing input" antipattern, L-C20). The `delegate.ts` SRP boundary + `activeRole.ts` per-process stack were built to make an RPC variant additive. Full reasoning: brief §D-S3-A |
| D-S3-B | Is there net-new S3 code work, or is S3 convergence-only? | **Convergence-only** — ratify Open-Q1, formally close the exit criterion clause-by-clause against passing S2 ACs, record the two carried residuals; NO new delegation code | Treat S3 as net-new code work (manufacture an artifact to justify the stage) | **Operator-converged (via orchestrator, L-C6; matches recommendation, no divergence).** Reversibility Filter → Pros-Cons-Fixes, grounded in the clause-by-clause verdict: 2 of 3 clauses fully proven E2E, clause 1 proven at the mechanism level with one inherited empirical gap unclosable by ANY S3 code under `--network=none`. Manufacturing net-new code (option 1) fails its own fix (the only genuine candidate, arg-level enforcement, would EXPAND the exit criterion and is legitimately S7). Scope-Creep + IKEA-Effect biases named and ruled out. Full reasoning: brief §D-S3-B |
| P-S3-1 | Pipeline routing for this closure record | **Light path** — single collapsed spec-review pass; `test`/`code`/`git`/`gate` attested "N/A — no executable artifact" | Full 8-stage (S2's routing); hardened path (two rubrics + negative-check attestation) | Plan-stage Trace computation on `P` (per the delegation's point 5). `P ∩ X = ∅` (Axis-1 track-eligible), zero `E`-set path (Axis-2(a)), zero `G`-pattern (Axis-2(b)) → low-consequence prose. Full derivation: Pipeline routing statement above |
| P-S3-2 | Where the Open-Q1 durable record lives + who writes it | **A NEW Tier-3 decision record `decisions/pi-replatform-open-q1.md`, authored by the OPERATOR** (this plan NAMES its exact required content, does not write it) | Write it in this Tier-0 plan (non-durable); amend an existing decision record; a roster subagent writes it | Plan-stage decision from the converged brief's Open-Questions §. Tier-0 plans are disposable — a durable ratification cannot rest only here. No roster subagent can write Tier-3 (D-D / L-C27), so the write routes to the operator. A dedicated new record (vs amending `s2-sandbox.md`/`broker-mcp.md`) keeps the Open-Q1 resolution single-purpose and citable by S4/S6. Full content: § "Tier-3 decision-record note" |

> Every row's full reasoning is in the sections below. Rows D-S3-A / D-S3-B cite
> the operator convergence (they are NOT re-decided here); rows P-S3-1 / P-S3-2
> are plan-stage computations the brief explicitly left to `gleipnir-plan`
> (routing on `P`; the durable-record naming), neither material.

---

## Architect

**Problem (one sentence).** Formally close the build-order S3 exit criterion
clause-by-clause against the already-committed, already-passing S2 evidence
(28/28 green), ratify Open-Q1 as "in-process `createAgentSession` is the final
delegation-isolation answer for S3," record the two carried residuals as
non-defects, and name (for operator authorship) the Tier-3 decision record that
makes the Open-Q1 ratification durable — with **no** net-new delegation code
(D-S3-B, operator-converged).

**User.** The operator (who ratifies Open-Q1 and authors the named Tier-3
record); `quality-reviewer` (single collapsed light-path spec-review pass);
downstream steps that consume a *closed, stable* delegation edge — **S4** (the
G-5 engine sequences over this delegation edge; a closed S3 is its dependency,
per the build-order dependency graph) and **S6** (which will consult the Open-Q1
ratification's S6-conditional future-work item when deciding broker isolation).

**Measurable success criteria.**

1. Each of the three exit-criterion clauses has an explicit CLOSED verdict with a
   specific AC/test citation (clause 1 → AC-5/AC-9/AC-9-E2E/AC-15 + carried
   residual; clause 2 → AC-6/AC-7/AC-8/AC-13/AC-14; clause 3 →
   AC-9/AC-9-E2E/AC-12/AC-16/AC-17/AC-18/AC-19). No clause without a verdict;
   no verdict without a citation. (This is the falsifiability hook — see Design
   Principles.)
2. Open-Q1 is recorded as ratified = **in-process `createAgentSession`, final
   for S3**, with the S6-conditional RPC future-work item stated verbatim (see
   § "Open-Q1 ratification (exact text)").
3. The two carried residuals are recorded **as residuals, not as resolved and
   not as S3 defects**: (a) the live-model-turn gap; (b) arg-level `event.input`
   enforcement (E-1 seam, → S7).
4. The Tier-3 decision-record note is named precisely (path + exact required
   content) such that the operator can author it without re-deriving anything;
   it is NOT written by this plan.
5. The pipeline routing is stated as **light path** with the four attested
   "N/A — no executable artifact" transitions.
6. No `src/**` change is proposed; no code-level Assemble step exists; the
   already-passing S2 code + tests are cited, not modified (verified: this plan's
   `P` = `{ this .md file }`).

**Constraints (from the two converged decisions + the build-order exit
criterion).**

- **Exit criterion (verbatim, the thing being closed):** *"orchestrator can
  delegate to a bounded role, depth cap refuses runaway nesting, child cannot
  exceed its role's capability table."* S3's closure must satisfy this clause by
  clause; S3 must not expand beyond it.
- **D-S3-B scope wall:** NO net-new delegation code. Do not manufacture an
  artifact to justify the stage. The clause-by-clause verdict + Open-Q1
  ratification ARE the deliverable.
- **D-S3-A ratification:** in-process is S3-final; the RPC variant is
  S6-conditional future work, NOT built now. Do not re-open this.
- **Tier boundary:** the durable Open-Q1 record is Tier-3, operator-authored.
  This plan (Tier-0) NAMES it; it does not write it (D-D / L-C27).
- **Arg-level enforcement stays S7.** Pinning it into S3 would EXPAND the exit
  criterion (which is coarse tool-presence containment, already proven); the
  `bounds` metadata is already in place per S2. Recorded as a carried residual,
  not absorbed.
- **Evidence discipline (L-C36):** every closure verdict rests on the in-sandbox
  test arbiter (`bin/gleipnir-sandbox {test,lint} --profile pi`, 28/28 green per
  the S2 README), cited by AC, not on prose.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Status | Role in S3 closure |
|---|---|---|---|
| **S3 closure record (this file)** | `.gleipnir/plans/pi-dev-replatform-s3.md` | **to-be-created by this delegation** (Tier-0, my writable path) | The S3 deliverable: the clause-by-clause exit-criterion closure + Open-Q1 ratification + carried-residual record + the named Tier-3 artifact |
| Build-order S3 section | `.gleipnir/plans/pi-dev-replatform-build-order.md` §S3 (L122–139) | exists (read this session) | Source of the verbatim exit criterion + [ASSUMPTION-2] this closure discharges |
| Converged design brief | `.gleipnir/plans/pi-dev-replatform-s3-brainstorm.md` | exists, CONVERGED (read this session) | The evidentiary basis: F1–F5 findings + the D-S3-B grounding table this plan formalizes |
| S2 plan | `.gleipnir/plans/pi-dev-replatform-s2.md` | exists (read this session) | The D-A pull-forward context: WHY S3's delegation code was built at S2 |
| S2 evidence (AC→test map + residual limits) | `pi-package/README.md` | exists, **28/28 green, lint clean** (read this session) | The authoritative AC citations every clause verdict rests on |
| Committed delegation code (cited, NOT modified) | `pi-package/src/{delegate,depth,activeRole,enforcement,roleTable}.ts` | exists, proven by S2 (F1–F5) | The mechanism the closure certifies; **no change proposed** |
| Committed tests (cited, NOT modified) | `pi-package/test/{delegate,enforcement,roleTable}.test.ts` | exists, 28/28 green | The arbiter the closure cites; **no new test proposed** |
| **Open-Q1 durable record** | `.gleipnir/decisions/pi-replatform-open-q1.md` | **to-be-created by the OPERATOR** (Tier-3; NOT written by this plan; confirmed absent this session in `decisions/`) | Makes the Open-Q1 ratification durable; named precisely below, authored by operator |

### The formal closure — clause-by-clause exit-criterion verdict (THE S3 DELIVERABLE)

Verbatim exit criterion: *"orchestrator can delegate to a bounded role, depth
cap refuses runaway nesting, child cannot exceed its role's capability table."*
Each clause is closed below against the committed post-S2 code + passing ACs
(per the brief's F3 / D-S3-B grounding table; every AC verified present in
`pi-package/README.md`'s AC→test map, 28/28 green).

| # | Exit-criterion clause | Verdict | Citation (committed S2 code + passing tests, per `pi-package/README.md`) |
|---|---|---|---|
| **1** | **"orchestrator can delegate to a bounded role"** | **CLOSED at the mechanism level** — with one inherited empirical gap carried as a RESIDUAL (not a defect blocking closure) | The `delegate` tool exists and creates a role-bounded child: **AC-5** (`resolveChildTools` bounds the child to exactly its role's tool set), **AC-9** (the child's explicitly re-wired enforcement extension blocks a denied tool), **AC-9-E2E** (`delegate.ts`'s real `execute` builds a real `createAgentSession` child, real `_extensionRunner.emitToolCall` dispatch, blocks `write` / allows `read` for `gleipnir-code`). The `orchestrator` role holds `delegate` in its allow-set (`roleTable.ts`) and is seeded as the top-level active role at `session_start`: **AC-15** (guarded seed, does not clobber a pushed child role). **CARRIED RESIDUAL (inherited, empirical, NOT architectural, NOT an S3 defect):** a *live-model-driven* top-level orchestrator session emitting a real `delegate` call and running a real child model turn is not exercised — the `--network=none` provider-auth limit (S2 README "Live-model-turn gap"). This is unclosable by ANY S3 delegation code; see § "Carried residuals". |
| **2** | **"depth cap refuses runaway nesting"** | **CLOSED — fully proven, end-to-end** | **AC-6** (delegation at `depth === cap` is refused), **AC-7** (nested delegation caught by the same cap), **AC-8** (the depth counter is `finally`-restored after a child throws), **AC-13/AC-14** (a real nested re-invocation of `delegate.ts`'s own captured `execute`, from inside a stubbed `prompt`, is refused past the cap; `getDepth()` restored to 0). No carried residual on this clause. |
| **3** | **"child cannot exceed its role's capability table"** | **CLOSED — fully proven, end-to-end** | **AC-9** + **AC-9-E2E** (a real child's real `ExtensionRunner` blocks a denied tool `write`, allows `read`, for role `gleipnir-code`), **AC-12** (deny-by-default through the `customTools` pass-through — a non-delegate child receives `[]` and cannot re-delegate), **AC-16** (deny-by-default proven for all 8 roles), **AC-17** (G-2 git-broker sole-holder: `git-ops` is the only non-empty `brokerTools`), **AC-18** (SDK `ToolName` vocabulary fidelity), **AC-19** (frozen table, no runtime widening). No carried residual on this clause. |

**Closure summary:** all three clauses are CLOSED. Clauses 2 and 3 are fully
proven end-to-end; clause 1 is closed at the mechanism level with one inherited,
empirical (network/auth), non-architectural residual that is unclosable in the
current `--network=none` sandbox regardless of what S3 builds. Per D-S3-B
(operator-converged), this closes S3 — the residual is a carried sandbox-regime
limit, not an open S3 defect.

### Open-Q1 ratification (exact text)

**Open-Q1 is ratified for S3 as follows (operator-converged via D-S3-A):**

> **In-process `createAgentSession` is the final delegation-isolation answer for
> S3.** The S3 delegation edge is in-process only; there is no `runRpcMode` /
> process-isolated variant, and none is required for S3 to close. **Tracked
> future-work item (S6-conditional):** *if the S6 sandbox/broker convergence
> (Open-Q3) requires process isolation for any role, add a `runRpcMode` variant
> to the delegation edge at S6 — this is additive, not a rebuild, because
> `delegate.ts` is SRP-scoped to "construct + bound + run a child session, and
> nothing else (does NOT decide in-process-vs-RPC isolation — that is Open-Q1)"
> (module header) and `activeRole.ts`'s per-process stack model "does not need
> to change" under a move to `runRpcMode` (each process gets its own module
> instance). The trigger to revisit is the S6/Open-Q3 convergence; until then,
> in-process is S3-final.*

This ratification does NOT decide Open-Q2 (human-gate policy), Open-Q3
(MCP-broker reachability, → S6), or Open-Q4 (cutover, → S9) — only Open-Q1, and
only for S3's finalisation, per the brief's Constraints.

### Carried residuals (recorded as residuals — NOT S3 defects, NOT resolved)

Both are explicitly NOT defects blocking S3 closure and NOT things S3 code can
close. Recorded so a reader cannot mistake a carried limit for an open S3 hole.

1. **Live-model-turn gap (inherited from S1/S2, unchanged; sandbox/network
   limitation).** A real top-level orchestrator session, under a live model,
   emitting a real `delegate` call and running a real child model turn is not
   exercised: `createAgentSession`'s body calls `ModelRuntime.create` /
   `findInitialModel` against provider auth, which is unreachable under
   `--network=none` with no in-container credentials (S2 README "Why `prompt`
   had to be stubbed"). This is a **network/auth limitation, not a
   wiring-correctness one** — the wiring is settled yes on real SDK code
   (AC-9-E2E). It is **unclosable by any delegation code S3 could write.** If the
   operator ever wants it closed, that is an **Open-Q1 / S-2 sandbox-regime
   question** (a network/auth-in-sandbox decision — e.g. relaxing
   `--network=none` or provisioning in-container credentials for a live-turn
   test profile), NOT a delegation-model one. Tracked as such; out of S3 scope.

2. **Arg-level `event.input` enforcement (E-1 seam, deferred to S7).** The
   enforcement hook enforces COARSE tool-presence allow/deny via
   `canUse(role, toolName)` (reads `event.toolName` only). The *fine-grained*
   per-path/per-arg bounds (e.g. "`gleipnir-code` may `edit` but not under
   `.gleipnir/**`"; "`git-ops` may `read` but not `.git/**`";
   "`quality-reviewer`'s bash is `git {diff,log,show,status}` only") are already
   **recorded as `bounds` metadata in `roleTable.ts`** per S2 — captured, not
   enforced. Fine-grained `event.input` inspection is the **E-1 argument-policy
   seam, legitimately deferred to S7** (the config-preflight / over-broad-grant
   step). The S3 exit criterion says nothing about arg-level bounds (it is
   coarse tool-presence containment, already proven at clause 3); pinning
   arg-level enforcement into S3 would EXPAND the exit criterion and is NOT done
   (D-S3-B, Pros-Cons-Fixes: the only genuine net-new candidate, ruled out as
   scope expansion). `bounds` metadata already in place per S2 — the S7 step has
   its source.

### Tier-3 decision-record note (NAMED precisely for the OPERATOR to author — NOT written by this plan)

**This plan does NOT write this note** (Tier-3 is operator-only; no roster
subagent can write it, D-D / L-C27). It is named here with its exact required
content so the operator can author it directly without re-deriving anything.

- **Path (recommended, to-be-created):** `.gleipnir/decisions/pi-replatform-open-q1.md`
  (confirmed ABSENT in `.gleipnir/decisions/` this session — a NEW record, not an
  amendment). A dedicated single-purpose record (rather than amending
  `s2-sandbox.md` or `broker-mcp.md`) keeps the Open-Q1 resolution citable by S4
  and S6 as one thing. *(If the operator prefers, it may instead be an amendment
  to an existing decision record; the REQUIRED CONTENT below is the same either
  way.)*
- **Tier / writer:** Tier-3 (POLICY), **operator-authored**. Under the default
  uncaged posture the operator (or an agent acting under explicit operator
  instruction) may write it; a bounded roster subagent may not (D-D / L-C27).
- **REQUIRED CONTENT (exactly what it must contain):**
  1. **The Open-Q1 ratification (verbatim intent):** "Open-Q1 (in-process
     `createAgentSession` vs process-isolated `runRpcMode` delegation boundary)
     is **RESOLVED for S3 = in-process `createAgentSession`.** This is the final
     delegation-isolation answer for S3; the S3 delegation edge is in-process
     only and requires no RPC variant to close." Cite the converging authority:
     operator, via the orchestrator's `question` tool (L-C6), matching the
     `pi-dev-replatform-s3-brainstorm.md` §D-S3-A recommendation with no
     divergence.
  2. **The S6-conditional future-work item (verbatim):** "If the S6
     sandbox/broker convergence (Open-Q3) requires process isolation for any
     role, add a `runRpcMode` variant to the delegation edge **at S6** — this is
     **additive, not a rebuild**, because `delegate.ts` is SRP-scoped to
     construct/bound/run a child session and explicitly does NOT decide
     in-process-vs-RPC isolation, and `activeRole.ts`'s per-process stack model
     does not need to change under a move to `runRpcMode`. The trigger to
     revisit Open-Q1 is the S6/Open-Q3 convergence; until then, in-process is
     final for S3." Mark this item as TRACKED FUTURE WORK, S6-conditional.
  3. **The two carried residuals, recorded as non-defects** (so the durable
     record carries them, not just this disposable plan): (a) the
     live-model-turn gap is a `--network=none` sandbox/auth limit, unclosable by
     delegation code, revisited only as an Open-Q1 / S-2 sandbox-regime question
     if ever wanted; (b) arg-level `event.input` enforcement (E-1 seam) is
     legitimately deferred to S7, with `bounds` metadata already in place per S2.
  4. **Scope note:** this record resolves Open-Q1 ONLY; it does not touch
     Open-Q2 / Open-Q3 / Open-Q4.
  5. **Supersession/linkage note:** cite `pi-dev-replatform-s3.md` (this closure
     record) and `pi-dev-replatform-s3-brainstorm.md` (§D-S3-A) as the
     derivation, and note the record is consulted by S4 (stable-edge dependency)
     and S6 (the RPC-variant trigger).

### Integrations map

```
build-order §S3 exit criterion ──closed-by──> this closure record (clause-by-clause verdict table)
        │                                             │
        │  clause 1 ──> AC-5, AC-9, AC-9-E2E, AC-15  (+ carried residual: live-model-turn)
        │  clause 2 ──> AC-6, AC-7, AC-8, AC-13, AC-14
        │  clause 3 ──> AC-9, AC-9-E2E, AC-12, AC-16, AC-17, AC-18, AC-19
        │                                             │
        │                            all ACs 28/28 green (pi-package/README.md)
        │
Open-Q1 (D-S3-A, operator-converged) ──ratified──> in-process = S3-final
        │                                             │
        │                          S6-conditional future-work item (RPC variant, additive)
        │                                             │
        └──named-for-operator──> decisions/pi-replatform-open-q1.md  [Tier-3, operator writes]
                                                      │
                                consulted by ──> S4 (stable edge), S6 (RPC trigger)
```

### Edge cases

1. **A reader treats the live-model-turn gap as an open S3 defect.** Mitigated:
   it is recorded explicitly as a CARRIED RESIDUAL (inherited, empirical,
   network/auth, unclosable by delegation code) in both the clause-1 verdict and
   § "Carried residuals" — not as a defect blocking closure (D-S3-B).
2. **A reader treats arg-level enforcement as an S3 gap.** Mitigated: recorded as
   legitimately-deferred-to-S7 (E-1 seam), with `bounds` metadata already in
   place per S2; pinning it into S3 would expand the exit criterion (explicitly
   NOT done, D-S3-B).
3. **The Tier-3 record is mistaken for something this plan writes.** Mitigated:
   it is NAMED as operator-authored, NOT in `P`, with a boundary statement
   (D-D / L-C27); this plan's `P` = `{ this .md file }`.
4. **An AC citation is wrong or a clause lacks a citation.** Mitigated: every
   cited AC was verified present in `pi-package/README.md`'s AC→test map this
   session; the Design-Intent falsifiability hook (below) makes a missing/ wrong
   citation the explicit failure condition a reviewer checks.
5. **Open-Q1 recorded as anything other than in-process-final-for-S3.**
   Mitigated: the exact ratification text is fixed in § "Open-Q1 ratification"
   and required verbatim in the named Tier-3 record; the Design-Intent hook
   makes any other recording a falsification.

---

## Link (validate before "building")

There is no code to build; "Link" here is the evidence-and-boundary validation
the closure rests on. All confirmed this session:

1. **Every cited AC exists and is green.** Confirmed against
   `pi-package/README.md`'s AC→test map (L221–247): AC-5, AC-6, AC-7, AC-8, AC-9,
   AC-9-E2E, AC-12, AC-13/AC-14, AC-15, AC-16, AC-17, AC-18, AC-19 all present
   and mapped to real tests; README states 28/28 pass, lint clean, in-sandbox on
   real SDK code. ✓
2. **The two carried residuals are the ones the S2 README already names.**
   Confirmed against `pi-package/README.md` "Named residual limits carried into
   S2" (L176–211): the live-model-turn gap and arg-level-enforcement deferral are
   both there verbatim. ✓ (This closure INHERITS them; it does not invent new
   ones.)
3. **No `runRpcMode` code exists (F1).** Per the brief's F1 grep finding: the
   only delegation mechanism in `pi-package/src/*.ts` is in-process
   `createAgentSession`; `runRpcMode` appears only in prose. This is the concrete
   state Open-Q1 is ratified against. ✓
4. **The Tier-3 target record does not yet exist.** Confirmed:
   `.gleipnir/decisions/` listing (this session) contains no
   `pi-replatform-open-q1.md` — so naming it is a to-be-created NEW record, not a
   phantom-existing-file citation (L-C15). ✓
5. **`P` touches no `E`-set file.** Confirmed by exact-path inspection: the
   single member of `P` is `.gleipnir/plans/pi-dev-replatform-s3.md`, under
   `.gleipnir/plans/**` (Tier-0, my writable path), matching no `E` member. ✓

---

## Assemble (intended "build" order — NO code; this is the closure-record authoring order)

**No `src/**` / code-level steps exist (D-S3-B: convergence-only).** The
"assembly" is authoring this closure record in the order its sections certify
the exit criterion. Since the record IS this file, the order below is the order
in which its load-bearing content is laid down and self-checked.

1. **State the pipeline routing first** (light path; the four "N/A — no
   executable artifact" transitions) — done in the Pipeline routing statement, so
   the reviewer knows the rubric before reading the deliverable.
2. **Lay down the Decisions index** citing the two operator-converged decisions
   (D-S3-A, D-S3-B) as inputs, not re-decisions — done.
3. **Write the clause-by-clause closure verdict table** (Trace § "The formal
   closure"), each clause CLOSED with its specific AC citations, clause 1
   carrying the named residual — done; the S3 deliverable.
4. **Fix the Open-Q1 ratification text verbatim** (Trace § "Open-Q1
   ratification") — done.
5. **Record the two carried residuals as non-defects** (Trace § "Carried
   residuals") — done.
6. **Name the Tier-3 decision-record note precisely** (path + exact required
   content), explicitly NOT writing it (Trace § "Tier-3 decision-record note") —
   done.
7. **Self-check against the Design-Intent falsifiability hooks** (Design
   Principles): every clause has a verdict + citation; no residual is
   mischaracterized as resolved; Open-Q1 is recorded as in-process-final-for-S3
   and nothing else — done.

Hand back to the orchestrator, which routes this plan to the single collapsed
`quality-reviewer` spec-review pass (light path).

---

## Stress-test (acceptance checks the closure record is validated against)

Concrete, checkable — the light-path spec-review pass validates each:

1. **Clause coverage + citation.** Each of the 3 exit-criterion clauses has an
   explicit CLOSED verdict AND at least one specific AC/test citation. FAIL if
   any clause lacks a verdict or a citation. *(Check: the clause verdict table in
   Trace — clause 1 → AC-5/9/9-E2E/15; clause 2 → AC-6/7/8/13/14; clause 3 →
   AC-9/9-E2E/12/16/17/18/19.)*
2. **Citation validity.** Every cited AC exists in `pi-package/README.md`'s
   AC→test map and is within the 28/28-green set. FAIL if any citation names a
   nonexistent or failing AC. *(Verified this session against README L221–247.)*
3. **Residual honesty.** The live-model-turn gap and arg-level enforcement are
   each recorded as a CARRIED RESIDUAL / deferred item, NOT as resolved and NOT
   as an S3 defect. FAIL if either is characterized as resolved, or as an open
   S3 hole blocking closure. *(Check: § "Carried residuals" + clause-1 verdict.)*
4. **Open-Q1 recording.** Open-Q1 is recorded as ratified = in-process
   `createAgentSession`, final for S3, with the S6-conditional RPC future-work
   item. FAIL if Open-Q1 is recorded as anything other than in-process-final-for-
   S3, or if the S6-conditional future-work item is missing. *(Check: § "Open-Q1
   ratification".)*
5. **No re-decision.** D-S3-A and D-S3-B are cited as converged inputs, not
   re-derived or re-opened. FAIL if the plan re-opens either. *(Check: Decisions
   index rows cite the operator convergence; no competing option is entertained.)*
6. **No code scope creep.** `P` contains no `src/**` / executable artifact; no
   code-level Assemble step exists; the S2 code/tests are cited, not modified.
   FAIL if any code change or new test is proposed. *(Check: `P` = `{ this .md
   file }`; Assemble has no code step.)*
7. **Tier boundary.** The Tier-3 decision-record note is NAMED (path + exact
   required content) but NOT written by this plan, and is NOT in `P`. FAIL if the
   plan writes Tier-3 or omits the naming. *(Check: § "Tier-3 decision-record
   note" + routing statement.)*
8. **Routing correctness.** The plan states light path with the four attested
   "N/A — no executable artifact" transitions, and shows `P ∩ X = ∅`, zero
   `E`-set path, zero `G`-pattern. FAIL if routing is misstated or the derivation
   is absent. *(Check: Pipeline routing statement.)*

---

## Execution Workflow (for the orchestrator + the single reviewer)

Enough to act without rediscovering the protocol:

1. **Orchestrator:** route this plan to `quality-reviewer` for a **single
   collapsed light-path spec-review pass** (the `spec-review` and `quality`
   rubrics run together — there is no post-implementation executable artifact to
   blast-radius-review). Do NOT run `test`/`code`/`git` as producing stages;
   each carries an attested **"N/A — no executable artifact"** transition, and
   `gate` reads that attestation.
2. **`quality-reviewer` (light-path pass):** validate this closure record against
   the 8 Stress-test acceptance checks above. The rubric is (a) spec-conformance
   — does the record close each exit-criterion clause with a valid citation and
   ratify Open-Q1 correctly? — and (b) the cross-check's intent-quality +
   honour check: is the Design Intent specific/falsifiable (it is — see below),
   and does the record honour it (every clause cited, no residual
   mischaracterized, Open-Q1 recorded as in-process-final-for-S3)? Because this
   is light-path prose/config with no `E`-set touch and no `G`-pattern, the
   hardened-path two-non-fusing-rubric + negative-check-attestation machinery
   does NOT apply.
3. **On PASS:** the orchestrator emits the S3 pipeline state as closed; the
   `test`/`code`/`git`/`gate` transitions are recorded "N/A — no executable
   artifact." **Then surface to the operator** (this is the one operator action
   S3 leaves): author the named Tier-3 record
   `decisions/pi-replatform-open-q1.md` with the exact required content in Trace
   § "Tier-3 decision-record note", to make the Open-Q1 ratification durable
   (Tier-0 plans are disposable; the ratification must not rest only here).
4. **On FAIL:** return the specific failing Stress-test check(s); the closure
   record is corrected (it is prose — no code cycle) and re-reviewed. No divergence
   from D-S3-A/D-S3-B is entertained (they are converged; a re-opening would be a
   material tradeoff routed back to the brainstorm/convergence gate, not resolved
   here).

---

## Design Principles (Gate 1)

**Routing (case (iii) — prose/config-only).** This plan's touched-path set
`P = { .gleipnir/plans/pi-dev-replatform-s3.md }`, so `P ∩ X = ∅` — **no
executable artifact.** Per `plan-format.md` case (iii):

- **SOLID analysis:** `N/A — no executable artifact` (no class/function/module
  to analyse; this plan produces a prose closure record).
- **DRY analysis:** `N/A — no executable artifact` (no logic to duplicate; the
  plan cites the single canonical AC source `pi-package/README.md` rather than
  restating test internals).
- **Single Responsibility check:** `N/A — no executable artifact`.

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy).**
*This closure record must (1) give an explicit CLOSED verdict for each of the
three build-order S3 exit-criterion clauses, each verdict carrying at least one
specific AC/test citation from the committed, 28/28-green post-S2 evidence
(`pi-package/README.md`), grounded in the actual committed state per L-C36; (2)
record Open-Q1 as ratified = in-process `createAgentSession`, final for S3, with
the S6-conditional RPC future-work item stated; (3) record the two carried
residuals (live-model-turn gap; arg-level `event.input` enforcement) as
residuals/deferred-work, NOT as resolved and NOT as S3 defects; and (4) name —
but not write — the Tier-3 Open-Q1 decision record with its exact required
content, staying within the Tier-0 write boundary.*

A reviewer can **falsify** this by finding: (a) any exit-criterion clause without
a CLOSED verdict or without an AC citation; (b) any citation naming a nonexistent
or non-green AC; (c) either carried residual characterized as resolved, or as an
open S3 defect blocking closure; (d) Open-Q1 recorded as anything other than
in-process-final-for-S3, or the S6-conditional future-work item missing; (e) the
plan re-opening/re-deriving D-S3-A or D-S3-B (they are converged inputs); (f) any
`src/**` / code-level change or new test proposed (D-S3-B: convergence-only); or
(g) the plan writing the Tier-3 record itself, or `P` containing any `E`-set
path (a Tier-3 write or an enforcement-path touch this plan disclaims). This is a
concrete, checkable claim — not a generic "close S3 correctly" aspiration — and
maps one-to-one to the Stress-test acceptance checks.
