# Design Brief: pi.dev replatform — Step S2 (full role→capability table + package manifest)

> **Status: CONVERGED.** The operator converged (via the orchestrator's
> `question` tool) on all six decision points this brief surfaced (D-A … D-E
> plus the broker-placeholder micro-decision). The recommendations below are
> retained as the *input* to that convergence; each decision's converged choice
> is now recorded in its **Operator convergence** line and in the "Selected
> Approach" table. **Five of six matched this brainstorm's recommendation; D-A
> DIVERGED** — the operator chose "in-scope now" over the recommended
> "out-of-scope for S2, defer to S3." That divergence is recorded honestly
> below, not softened. `gleipnir-plan` plans from these **converged** choices,
> not from the original recommendations.

## Problem Statement

S1 proved the two load-bearing CRUX mechanisms (CRUX 1: a `tool_call` block hook
enforcing a role→capability table; CRUX 2: a depth-capped `createAgentSession`
delegation tool) for **one** role (`gleipnir-code`). S2 must promote that
one-role proof to the **full 8-role deny-by-default roster** consumed by the
enforcement extension, finalise the Pi package manifest + `.pi/settings.json`
project surface, and re-express the per-path/per-arg bounds that opencode's
`permission:` map used to carry — now in the extension's TypeScript block logic,
because the pi host has no permission-map primitive (CRUX 1, mechanism already
proven, now scaled to 8 roles).

**Exit criterion (verbatim from the build-order, not to be expanded or
narrowed):** "every role's allow-set is expressed and tested; the single broker
holder (git-ops) is the only role whose table grants git (G-2 clause preserved
at the table level); deny-by-default proven for each role."

## Constraints

- **Scope is fixed by the build-order.** S2 does NOT re-decide the four
  carried-forward open questions (Q1 sandbox, Q2 human-gate policy, Q3 MCP-broker
  reachability, Q4 cutover sequencing). Q2's *mechanism* was already demonstrated
  in S1 (`ctx.hasUI` fail-closed); S2 does not touch Q1–Q4.
- **G-2 single-broker-holder must survive at the table level.** Only `git-ops`
  may hold git in its allow-set. Every other role denies both broker namespaces.
  This is the load-bearing invariant of the exit criterion.
- **Deny-by-default is the posture.** The S1 `roleTable.ts` already encodes it
  (unset/unknown role, unknown tool → `false`, no implicit-allow path). S2 must
  preserve that property per-role and prove it per-role.
- **Re-expression, not port** (inherited from the converged Approach-B brief):
  do not preserve opencode-shaped structure for its own sake; fit pi.dev's real
  model.
- **The eight roles and their opencode capability sets are the source** (read
  this session): `orchestrator` (primary; task-delegation allowlist, denies
  edit/bash/git/pm), `gleipnir-brainstorm` (read/webfetch/edit-plans-only),
  `gleipnir-plan` (read/webfetch/edit-plans-only), `gleipnir-code`
  (edit-with-.gleipnir-deny, read, sandbox-test/lint bash allowlist, no git),
  `quality-reviewer` (read-only + read-only git-inspection bash), `git-ops`
  (sole git/broker holder; bash git-subcommand allowlist; `.git/**` read deny),
  `project-mgr` (read + pm namespace only), `notify` (read + notify namespace
  only).

## Explore Findings (S2-relevant, grounded in what S1 actually built + verified SDK facts)

### F1 — S1's role table is a single frozen TS object literal, deny-by-default, pi-import-free

`src/roleTable.ts` is pure data + `canUse(role, toolName)`; one role
(`gleipnir-code`) with allow-set `{"read_file","write_file","delegate"}`, frozen,
no pi imports (unit-testable in isolation). Its own docstring states the S2
intent explicitly: *"adding roles/tools in S2 extends this data without touching
`enforcement.ts`'s hook logic — the table is data-driven, the hook is closed to
modification as the roster grows"* (Open/Closed). `enforcement.ts` depends only
on the narrow `canUse(role, tool)` function (Dependency Inversion), so storage
can change in S2 without touching the hook.

### F2 — The SDK's real base tool vocabulary is now verified against the shipped `.d.ts`

Authoritative source (`@earendil-works/pi-coding-agent@0.84.2/dist/core/tools/index.d.ts`,
fetched this session):

```ts
export type ToolName = "read" | "bash" | "edit" | "write" | "grep" | "find" | "ls";
```

Seven base tools — **not eight.** Two corrections to the S1 README's "Known
limitations" note (item 2): (a) S1's `read_file`/`write_file` indeed do NOT
exist — the real names are `read`/`write`; (b) the README's claim that
`powershell` is a base `ToolName` is **incorrect** — there is no `powershell` in
the union. The SDK also ships `createReadOnlyToolDefinitions` and
`createCodingToolDefinitions` helpers, plus `allToolNames: Set<ToolName>` —
directly relevant to expressing read-only roster roles (`quality-reviewer`,
`project-mgr`, `notify`).

**Consequence for the roster:** the opencode roster's capabilities do not map
1:1 onto these 7 base tools. `task` (delegation), `webfetch`, `question`, and the
broker MCP namespaces (`gleipnir-git_*`, `gleipnir-pm_*`) are NOT base
`ToolName`s — they are Gleipnir-built custom tools (`delegate`) or
not-yet-reachable primitives (MCP brokers = Open-Q3, S6). So the S2 table's
vocabulary is a **union of** (i) the 7 SDK base tools, (ii) Gleipnir custom
tools like `delegate`, and (iii) placeholder names for capabilities whose
reach mechanism is still an open question (the broker namespaces). This union
shape is a design question feeding D-B and D-C.

### F3 — No `.pi/` project surface exists yet

`glob .pi/**` → no files. S1 finalised only `package.json`'s `pi` key
(`extensions: ["./src/enforcement.ts","./src/delegate.ts"]`) + peerDependencies;
it never created `.pi/settings.json`. So "finalise the manifest and
`.pi/settings.json` project surface" (S2 goal item 2) is genuinely net-new
surface, not an edit of an existing one — which sharpens D-E (what does
"finalise" cover when nothing exists to extend?).

### F4 — `customTools: []` in `delegate.ts` blocks end-to-end nested delegation

`delegate.ts` passes `customTools: []` to every child unconditionally. Since
`delegate` is itself a custom tool (not a base `ToolName`), a child never
receives it — so a child can never re-invoke `delegate` in a real unstubbed
system, even though `gleipnir-code`'s allow-set lists `"delegate"`. AC-7's
"nested delegation" is proven only at the `depth.ts` counter level. This is the
S1 README limitation (item 1) that feeds D-A directly.

### F5 — The stage-role-map / AGENTS.md opencode literals are the D-D surface

`stage-role-map.md` Axis-1 `X` and Axis-2(a) `E` sets contain opencode-tied
literals: `opencode.jsonc`/`**/opencode.json`, `.gleipnir/plugins/**`
(opencode-plugin path), JSON(C) enforcement keys `default_agent`/
`subagent_depth`/`mcp`. `AGENTS.md` carries the `OPENCODE_CONFIG_DIR` framing and
the "Why `.gleipnir/` and not `.opencode/`" rationale. The build-order
supersession table says these are "enacted at S2" (rows 3 & 4). BUT both are
**Tier-3 policy files** — outside the pi-package Tier-0 code change, and outside
this brainstorm's own writer grant. This tension (Tier-0 code vs Tier-3 policy
edit in one delegation) is exactly D-D.

## Decision Analysis

> Five distinct decision points (D-A … D-E) plus one micro-decision (broker
> placeholder in the table) fired during Explore/Propose. Each got its own
> framework + bias check + recommendation per the decision-frameworks skill;
> those recommendations were surfaced to the operator by the orchestrator and
> the operator has now **converged on all six** (recorded in each decision's
> **Operator convergence** line below). Depth level assumed `standard` (no
> `.aetos/args/defaults.yaml` in this tree): auto-selected primary framework per
> decision, all 12 bias detectors run, ≤3 warnings surfaced. The frameworks and
> recommendations are retained verbatim as the input to convergence; they were
> advisory, and the operator's recorded choices are authoritative.

---

### D-A — Nested delegation scope

**Decision:** pass `customTools` through to children (enabling real nested
delegation) **vs.** explicitly declare nested delegation out-of-scope for S2
(matching S1's disclosed limitation, deferring the wider question).

**Type:** Binary choice → **Reversibility Filter → Pros-Cons-Fixes** (primary
per auto-selection).

**Reversibility Filter:** **Two-Way Door.** Declaring nested delegation
out-of-scope for S2 and adding pass-through later (S3, which owns the real
delegation model) is cheap to reverse — it is additive, no data migration, no
external commitment. Passing `customTools` through *now* is the harder-to-undo
direction: it widens blast radius (a child gains the ability to spawn
grandchildren) and re-opens the depth-cap stress questions S1 deliberately left
at the counter level. → Fast-track *toward the reversible option*, but the
blast-radius asymmetry warrants the Pros-Cons-Fixes pass.

**Pros-Cons-Fixes:**

*Option A1 — pass `customTools` through now:*
- Pro: makes `gleipnir-code`'s existing `"delegate"` allow-set entry actually
  reachable end-to-end (closes the F4 architectural gap).
- Pro: real nested delegation is eventually needed (orchestrator → subagent →
  … is the pipeline shape).
- Con: widens blast radius during S2 (a table-only slice) and re-opens depth-cap
  stress + the child-hook-binding question under nesting. *Fix:* gate
  pass-through behind the already-proven depth cap — but the cap was only proven
  at the counter level (AC-7), not end-to-end, so the fix is itself unproven at
  S2.
- Con: S3 is the build-order's designated owner of "the real orchestrator→
  subagent model"; doing it at S2 conflates two steps. *Fix:* none clean — it
  is a scope boundary, not a defect.

*Option A2 — declare nested delegation out-of-scope for S2 (recommended):*
- Pro: matches S1's disclosed limitation exactly; keeps S2 a pure table+manifest
  slice; blast radius stays narrow.
- Pro: hands the wider question to S3, its designated owner (per build-order S3
  goal: "promote S1's `delegate` proof to the real orchestrator→subagent model").
- Con: `gleipnir-code`'s `"delegate"` allow-set entry stays architecturally
  unreachable end-to-end through S2. *Fix:* document it as a known-and-intended
  deferral in the S2 exit notes (it already is disclosed), and have the S2 table
  keep `delegate` in the allow-set as *data* (the capability is declared;
  reachability is an S3 concern).

**Post-fix verdict:** A2 (defer) is Viable and narrowest-blast-radius; A1 is
Marginal at S2 (its key con — conflating S2 with S3 — has no clean fix).

**Bias warnings:**
- ⚠️ **Scope Creep Bias** — A1 expands S2 to include delegation-architecture work
  that the build-order assigns to S3. Forcing that in "because we're touching the
  table anyway" is deferred-decision-making with compounded cost. The build-order
  drew the S2/S3 line deliberately.
- ⚠️ **Status Quo Bias (inverted, low confidence)** — A2 is "keep S1's
  limitation," which could get a free pass; scrutinise that it is *intentional
  deferral to S3*, not just inertia. It is: S3 owns delegation.

**Recommendation (advisory):** **A2 — declare nested delegation out-of-scope for
S2.** Keep `delegate` in the relevant roles' allow-sets as *declared capability*
(data), but do not add `customTools` pass-through until S3, its designated owner.
This keeps S2 a pure table+manifest slice and blast radius narrowest.

**Operator convergence: A1 — "in-scope now" (DIVERGES from the recommendation).**
The operator explicitly chose to pass `customTools` through to delegated children
**now**, enabling real nested delegation **within S2 itself**, rather than
deferring it to S3. This is a conscious divergence from the recommended A2, not
an agreement — recorded honestly per L-C8/the honour-check discipline. The
operator's reasons override the Reversibility-Filter and Scope-Creep-Bias
cautions that favoured deferral; those cautions stand as recorded advice that was
weighed and set aside, not as unraised concerns.

**What this means for the plan stage (`gleipnir-plan` MUST design these, not
silently absorb them):**
1. **`customTools` pass-through mechanism is now an S2-plan design element.** S2
   must design *which children/roles receive `delegate`* in their passed-through
   custom-tool set (i.e. `delegate.ts` no longer passes `customTools: []`
   unconditionally — it must project each child role's declared custom-tool
   capability, DRY-sourced from the same role table, into the child's
   `customTools`). Only roles whose allow-set declares `delegate` should receive
   it; deny-by-default still governs — a child role without `delegate` in its
   allow-set must NOT get it passed through.
2. **Depth-cap interaction under real nested re-invocation must be designed and
   tested end-to-end, not just at the counter level.** The S1 cap was proven only
   at `depth.ts`'s enter/exit counter (AC-7); enabling real nested `delegate`
   re-invocation means the cap must now be exercised through an actual child that
   itself calls `delegate`. The plan must specify how `depth.ts`'s module-scope
   counter behaves across a real (in-process `createAgentSession`) nesting chain
   and add the end-to-end test that S1 explicitly could not run.
3. **The "S2 is a pure table+manifest slice" framing no longer holds.** The
   Reversibility Filter above reasoned on the assumption S2 stays table-only;
   A1-converged makes S2 *also* a delegation-mechanism slice. `gleipnir-plan`
   must name this explicitly: **part of S3's scope (the real orchestrator→
   subagent delegation model, specifically the `customTools` pass-through and
   its end-to-end depth-cap proof) is pulled forward into S2.** This must appear
   as a named S2-plan design element and a named S2/S3 re-scoping note — it must
   not be silently woven into the table work. The build-order's S3 step
   definition should be read with this pull-forward in mind (S3 retains the
   in-process-vs-RPC isolation question and the broader delegation model; the
   `customTools` reachability piece is now S2's).

---

### D-B — Tool vocabulary reconciliation

**Decision:** rename `roleTable.ts`'s allow-set entries to the SDK's real base
`ToolName`s now (`read`/`write`, breaking/fixing S1's already-tested shapes)
**vs.** keep S1's `read_file`/`write_file` vocabulary and add a translation
layer **vs.** a hybrid surfaced here.

**Type:** Multi-option comparison → **Weighted Decision Matrix** (primary), with
**Hypothesis-Driven Analysis** on the "what is the table's vocabulary domain?"
question (fallback, because the fact base was thin until F2 verified the real
`ToolName` union).

**Grounding fact (F2, now verified):** the real base `ToolName` union is exactly
`read | bash | edit | write | grep | find | ls`. S1's `read_file`/`write_file`
do not exist as base tools; `read`/`write` are the real names. But the roster
also needs to express `delegate` (a Gleipnir custom tool), and eventually the
broker MCP namespaces (`gleipnir-git_*`/`gleipnir-pm_*`, Open-Q3/S6) — neither is
a base `ToolName`. So the table's vocabulary is inherently a **union of base +
custom + (deferred) broker** names, not a pure `ToolName` set.

Options:
- **B1 — rename to real base names now** (`read_file`→`read`, `write_file`→`write`),
  keep `delegate` as a custom-tool name in the same flat allow-set.
- **B2 — keep `read_file`/`write_file`, add a translation layer** mapping
  Gleipnir vocabulary → SDK `ToolName` at the `tool_call` hook boundary.
- **B3 — real base names now + an explicit typed vocabulary** that partitions the
  allow-set namespace into `baseTools: ToolName`, `customTools: string`, and
  (deferred) `brokerTools: string`, so the union is documented in the type, not
  implicit.

| Criterion | Weight | B1 (rename flat) | B2 (translation layer) | B3 (rename + typed partition) |
|---|---|---|---|---|
| Fidelity to real SDK `ToolName` (F2) | 9 | 9 → 81 | 4 → 36 | 9 → 81 |
| Minimises new moving parts / seam risk | 8 | 8 → 64 | 3 → 24 | 6 → 48 |
| Deny-by-default clarity per role | 8 | 7 → 56 | 5 → 40 | 9 → 72 |
| Cost to fix S1's already-tested shapes | 6 | 6 → 36 (rename tests) | 8 → 48 (tests untouched) | 5 → 30 (rename + type) |
| Expresses the base+custom+broker union honestly | 7 | 5 → 35 | 5 → 35 | 9 → 63 |
| Maintainability as roster grows to 8 | 7 | 6 → 42 | 4 → 28 | 8 → 56 |
| **Total** | | **314** | **211** | **350** |

**Hypothesis-Driven cross-check:** *If the table's vocabulary domain is "SDK
tool names," then a translation layer (B2) is pure overhead because the table
should just speak SDK names (B1/B3).* Evidence for: `enforcement.ts` reads
`event.toolName`, which is the SDK's own name — a translation layer would have to
translate at exactly the hook boundary, adding a seam in the hot path for no
enforcement benefit. Evidence against B2: none material. → B2's translation
layer is a solution to a problem that only exists because S1 chose non-SDK names;
the right fix is to align the names, not to bridge them. Confidence: High (the
`.d.ts` is authoritative).

**Bias warnings:**
- ⚠️ **Sunk Cost Fallacy** — B2 (keep `read_file`/`write_file` + translate) is
  partly attractive because *"S1 already tested those shapes."* Past test
  investment is not a reason to keep a wrong vocabulary; the tests are cheap to
  rename (mechanical). Judge by future value: the table should speak the host's
  real language.
- ⚠️ **Scope Creep Bias (low confidence)** — B3 adds a typed partition; guard that
  it is genuine clarity (base vs custom vs deferred-broker is a real distinction,
  per F2), not gold-plating. It is real: without it, `delegate` and a future
  `gleipnir-git_commit` sit namelessly next to `read` with no signal that they
  resolve differently.

**Recommendation (advisory):** **B3 — rename to real base names now AND express
the base/custom/(deferred-broker) partition explicitly** (highest matrix score,
350; B1 close behind at 314). B3 fixes S1's vocabulary against the verified SDK
truth (F2) *and* honestly encodes that the roster's allow-sets span more than the
7 base tools. If the operator prefers minimal change, **B1 (flat rename)** is the
safe fallback — it fixes the vocabulary without the typed partition, accepting a
flat allow-set where custom/broker names sit undistinguished. **B2 is not
recommended** (it institutionalises the wrong vocabulary behind a hot-path seam).
Either B1 or B3 also corrects the README's `powershell` error (drop it — not a
real `ToolName`).

**Operator convergence: B3 — full typed partition (MATCHES the recommendation).**
The table renames to the real SDK `ToolName`s (`read`/`write`, etc.) now AND
expresses the explicit `baseTools`/`customTools`/(deferred) `brokerTools`
partition; the README's `powershell` claim is dropped as not a real `ToolName`.

---

### D-C — Table shape / structure

**Decision:** single flat TS object literal for all 8 roles **vs.** per-role
files **vs.** data-driven external config (JSON/TOML consumed at load).

**Type:** Architectural tradeoff → **Second-Order Thinking → Pre-Mortem**
(primary per auto-selection), informed by the maintainability + per-role
deny-by-default proof burden + the "table consumed by the enforcement extension"
language in the S2 goal.

Options:
- **C1 — single flat TS object literal** (extend S1's `ROLE_ALLOW_SETS`
  `Object.freeze({...})` to 8 keys).
- **C2 — per-role TS files** (one module per role, aggregated into the table).
- **C3 — external data-driven config** (`.pi/` JSON/TOML parsed at load).

**Second-Order Thinking:**
- **C1 near term:** trivial extension of the proven S1 shape; one file, frozen,
  pi-import-free, unit-testable. **Second-order:** as the roster/tools grow (S3
  adds delegation semantics, S6 adds broker namespaces), one file stays the
  single source of truth — easy to diff, easy to prove deny-by-default over in
  one test loop. Risk: the file grows; but 8 roles × small allow-sets is small.
- **C2 near term:** more files, more import wiring. **Second-order:** per-role
  files invite per-role *drift* (a role file quietly gaining a tool without the
  aggregate test noticing) and dilute the "one table" mental model the exit
  criterion leans on ("every role's allow-set is expressed and tested" is easiest
  to audit in one place). SRP argument for C2 is weak here — a role's allow-set
  is *data*, not behavior; splitting data by row is not an SRP win.
- **C3 near term:** externalises the table to JSON/TOML. **Second-order — the key
  insight:** an **externally-editable enforcement table is a Tier-3 escalation
  surface.** Under Gleipnir's trust-tier model the role→capability table IS
  enforcement policy; if it lives in a parsed `.pi/*.json` an agent (or a
  malformed untrusted-project load) could alter capability grants without a code
  change and without passing `tsc`. That directly weakens G-1/G-6. TS-as-data
  (C1) keeps the table inside the type-checked, review-gated, code-tier artifact.

**Pre-Mortem (on the leading option C1, and on C3 as the tempting alternative):**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | C1 file grows unwieldy as tools multiply | L | L | 8 roles is bounded; split only if it exceeds readability, not preemptively |
| 2 | C3 external config becomes a capability-grant bypass (agent edits JSON, no `tsc`, no review) | M | **H** | Do NOT externalise the enforcement table; keep it TS-as-data (C1) |
| 3 | C3 malformed `.pi/*.json` under untrusted-project load silently drops a deny | M | **H** | Same — C1 avoids the parse-time failure class entirely |
| 4 | C2 per-role drift: a role file gains a tool the aggregate test doesn't cover | M | M | If C2 chosen, a single aggregate deny-by-default test over all roles is mandatory |

**Top risks:** #2, #3 — both are C3-specific and both are High impact
(capability-grant integrity). **Verdict: reject C3** for the *enforcement* table.
(Note: `.pi/settings.json` still exists for pi's own project surface per D-E —
but the capability *table* is not that surface.)

**Bias warnings:**
- ⚠️ **IKEA Effect (low confidence)** — C1 is "keep extending what S1 built";
  guard that it wins on merit, not authorship. It does: the Second-Order + the
  Tier-3 integrity argument (risk #2/#3) are independent of who wrote S1.
- ⚠️ **Bandwagon Effect (low confidence)** — "data-driven config (C3) is the
  modern/clean pattern" is an industry-consensus pull; but for an *enforcement
  policy table* it is exactly wrong (integrity > flexibility, per the framework's
  own stage-role-map "standalone-YAML disqualified safe-side" precedent).

**Recommendation (advisory):** **C1 — single flat TS object literal**, extending
S1's proven `ROLE_ALLOW_SETS` shape to 8 roles. It is the lowest-risk, keeps the
enforcement table inside the type-checked/review-gated code tier (closing the
C3 integrity failure class), matches the "one table consumed by the extension"
language, and makes the per-role deny-by-default proof a single auditable test
loop. **C3 is affirmatively rejected** for the enforcement table (Tier-3 bypass
risk). C2 is available if the operator wants stronger per-role isolation, but
only with a mandatory single aggregate deny-by-default test.

**Operator convergence: C1 — single flat TS object literal (MATCHES the
recommendation).** The 8-role enforcement table extends S1's `ROLE_ALLOW_SETS`
`Object.freeze({...})` shape, staying inside the type-checked/review-gated code
tier. Note the D-B=B3 convergence means the flat literal now carries the typed
base/custom/(deferred-broker) partition per role.

---

### D-D — stage-role-map.md / AGENTS.md supersession timing

**Decision:** the S2 plan itself amends `stage-role-map.md` (Axis-1 `X` /
Axis-2(a) `E`) and `AGENTS.md` (`OPENCODE_CONFIG_DIR` framing) now, as the
build-order supersession table literally says ("enact at S2") **vs.** S2 builds
the pi-side artifacts only and explicitly defers the Tier-3 amend of those two
policy files to a separate follow-up plan.

**Type:** Binary choice with irreversibility asymmetry → **Reversibility Filter →
Regret Minimisation** (go/no-go on bundling a Tier-3 policy edit into a Tier-0
code slice).

**Reversibility Filter:** Amending the Tier-3 policy files is a **One-Way-ish
Door** in *blast-radius* terms (not in edit terms): a stage-role-map `E`/`X` edit
changes what the prose/config-only blast-radius router hardens vs. light-paths —
i.e. it changes *how future plans are reviewed*. Getting it wrong (e.g. removing
an opencode literal before the pi literal that replaces it is real, leaving a gap
where neither surface is hardened) is exactly the "half-enforced state" the
build-order's own Design Intent forbids. → Apply deeper analysis.

**Regret Minimisation (regret horizon: the S2→S3 window):**

| Option | Regret if wrong | Regret if not chosen | Max regret |
|---|---|---|---|
| D1 — amend Tier-3 files inside the S2 plan | **8** — a Tier-0 code slice and a Tier-3 policy edit in one delegation violates task-decomposition isolation (S-1.3.1: one verb/object/boundary); and premature `E`/`X` edits could de-harden a path while opencode is still the live enforcement surface (Q4/S9 not yet decided → opencode artifacts are still inert-but-present) | 3 — the supersession table says "enact at S2," so deferring risks the roadmap looking unfollowed | 8 |
| D2 — build pi artifacts only; defer Tier-3 amend to a follow-up plan | 3 — the two files stay opencode-framed a little longer (harmless while opencode is still the live surface pre-S9) | 4 — must track the deferral so it is not forgotten | 4 |

**Key insight:** the build-order's "enact at S2" means *S2 is the step at which
these become due* — it does **not** mandate that the *same delegation* that
writes the pi-package code also performs the Tier-3 edit. Gleipnir's own
task-decomposition isolation (one verb/object/verification/boundary) and the
Tier-0-vs-Tier-3 writer split argue for **two delegations**: (1) S2 pi-package
code (Tier-0, `gleipnir-code`), (2) the stage-role-map/AGENTS.md amend
(Tier-3, operator-authored per the memory model — `gleipnir-plan`/`gleipnir-code`
cannot write Tier-3 at all). In fact the capability model *forces* the split:
**no roster subagent can write `stage-role-map.md` or `AGENTS.md`** (Tier-3,
operator-only in caged mode; and even uncaged it is a distinct
enforcement-bearing edit that the hardened-path review must gate separately). So
bundling them into "the S2 plan" is not just risky — the executing agent
structurally cannot do the Tier-3 half.

**Bias warnings:**
- ⚠️ **Authority Bias** — "the build-order table says enact at S2" is being read
  as a mandate to bundle. The build-order is a Tier-0 transient roadmap; it names
  *when a change becomes due*, not *how to decompose the delegation*. Evaluate
  the decomposition on task-isolation merits, not on the table's phrasing.
- ⚠️ **Scope Creep Bias** — folding a Tier-3 policy amend into a Tier-0 code slice
  is scope expansion that avoids the clean two-delegation boundary.

**Recommendation (advisory):** **D2 — S2 builds the pi-package artifacts only;
the stage-role-map.md / AGENTS.md Tier-3 amend is a SEPARATE follow-up plan**
(sequenced immediately after S2's code lands, so the roadmap's "enact at S2"
intent is honoured at the step level without conflating tiers). **This keeps
blast radius narrowest** (lowest max-regret, 4 vs 8) AND respects the hard
capability fact that no roster subagent can write Tier-3 files — so the amend
*must* be its own operator-gated unit regardless. Flag to the operator: the
amend must be careful not to remove opencode `E`/`X` literals until Q4/S9 cutover
is decided (else a half-enforced window opens while opencode is still the live
surface).

**Operator convergence: D2 — separate follow-up plan (MATCHES the
recommendation).** S2 builds the pi-package artifacts only; the Tier-3 amend of
`stage-role-map.md` (`X`/`E`) and `AGENTS.md` (`OPENCODE_CONFIG_DIR` framing) is
deferred to its own follow-up plan, NOT bundled into the S2 delegation. The
flagged caution stands: that follow-up amend must not remove opencode `E`/`X`
literals until Q4/S9 cutover is decided.

---

### D-E — manifest / `.pi/settings.json` scope

**Decision:** what exactly S2's manifest finalization covers — is a minimal but
complete `package.json` `pi` key + one `.pi/settings.json` example sufficient
exit evidence, **or** does "finalise" imply something broader (per-role settings,
skills/prompts dirs)?

**Type:** Prioritisation / scope-boundary call → **RICE Scoring** on the
candidate scope items, framed by the exit criterion (which is about the *role
table*, not the manifest breadth).

**Grounding (F3):** no `.pi/` surface exists yet; S1 finalised only the
`package.json` `pi.extensions` array + peerDeps. The exit criterion says nothing
about manifest breadth — it is entirely about the role table
("every role's allow-set is expressed and tested… deny-by-default proven"). So
the manifest/`.pi` work is *supporting* the table slice, not the slice's proof.

RICE over candidate scope items (Reach = how much of the S2 exit it serves;
Impact 0.25–3; Confidence; Effort person-days):

| Item | Reach | Impact | Confidence | Effort | RICE |
|---|---|---|---|---|---|
| E-i: `package.json` `pi` key complete (extensions list incl. the role table module) | high | 3 | 100% | 0.5 | high |
| E-ii: one `.pi/settings.json` wiring the enforcement extension + declaring project trust posture | high | 2 | 90% | 0.5 | high |
| E-iii: per-role `.pi/settings.json` entries | low | 0.5 | 50% | 2 | low |
| E-iv: `skills/`/`prompts/`/`themes/` dirs populated | low | 0.25 | 60% | 3 | very low |

**Priority order:** E-i, E-ii ≫ E-iii, E-iv. E-iii (per-role settings) is low
Reach because the *role→capability enforcement lives in the TS table + hook*
(CRUX 1), NOT in pi's settings — pi has no per-agent permission primitive (the
whole reason for the extension). Putting per-role capability data in
`.pi/settings.json` would either duplicate the table (DRY violation) or, worse,
create a second capability surface that could disagree with the table (an
integrity seam, same class as D-C risk #2). E-iv (skills/prompts) is separate
work not gated by the S2 exit criterion (skills port near-1:1 per the brief, but
that is not S2's proof burden).

**Bias warnings:**
- ⚠️ **Scope Creep Bias** — "finalise the manifest" invites gold-plating
  (E-iii/E-iv) that the exit criterion does not ask for. Force the boundary:
  finalise means *complete enough to load and enforce the 8-role table*, not
  *populate every convention dir.*
- ⚠️ **Confirmation Bias (low confidence)** — the recommendation to keep it
  minimal aligns with the "narrowest blast radius" theme running through D-A/D-C/
  D-D; guard that E-ii is genuinely sufficient. It is: a settings file that
  loads the extension + sets trust posture is the complete project surface the
  table needs to function.

**Recommendation (advisory):** **Minimal-but-complete: E-i + E-ii only.** S2's
manifest finalization = a complete `package.json` `pi` key (extensions list
including the role-table-consuming enforcement module) + one `.pi/settings.json`
that wires the enforcement extension and declares the project-trust posture —
sufficient exit evidence. **E-iii (per-role settings) is affirmatively excluded**
(capability enforcement lives in the TS table, not pi settings — a second surface
would be a DRY/integrity seam). **E-iv (skills/prompts/themes dirs) is out of
scope for S2** (not gated by the exit criterion; separate porting work).
Recommended scope boundary: *"finalise" = complete enough to load and enforce the
8-role table; nothing broader.*

**Operator convergence: Minimal-but-complete (E-i + E-ii only) (MATCHES the
recommendation).** S2's manifest finalization is a complete `package.json` `pi`
key + one `.pi/settings.json` (wire the enforcement extension + declare the
project-trust posture). E-iii (per-role settings) is excluded; E-iv
(skills/prompts/themes dirs) is out of scope for S2.

---

### Micro-decision — broker placeholder representation in the table

**Decision (from the Open Questions section):** how the table represents the
broker namespaces (`gleipnir-git_*`/`gleipnir-pm_*`) given Open-Q3/S6 (real
broker reachability) is unresolved — as **inert declared name(s) now** (so
`git-ops`'s sole-holder git grant is *expressed* per the exit criterion) vs.
**omit until S6**.

**Operator convergence: inert declared name now (MATCHES the default-framing
recommendation).** `git-ops`'s table entry declares its git-related broker
capability name(s) now, as an **inert declared name** in the (D-B=B3) `brokerTools`
partition — present in the table so the exit criterion's "the single broker
holder (git-ops) is the only role whose table grants git" is satisfied at the
table level, but not yet wired to real broker reachability (that is S6, gated on
Open-Q3). No other role's table carries a broker name (G-2 sole-holder preserved
at the table level). **Plan-stage note:** because the capability is declared-inert,
the S2 deny-by-default proof must assert that every non-`git-ops` role denies the
broker name(s), and that `git-ops`'s declared broker name is inert (not yet
reachable) — a declared name is a capability *grant* in the table even before its
reach mechanism exists.

---

## Selected Approach (per-decision — OPERATOR-CONVERGED)

| Decision | Operator-converged choice | vs. recommendation | Blast-radius note |
|---|---|---|---|
| **D-A** nested delegation | **A1 — IN-SCOPE NOW** (pass `customTools` through to children within S2; enable real nested delegation) | **DIVERGES** (recommended A2 = defer to S3) | Widened — pulls part of S3's delegation scope forward into S2 |
| **D-B** tool vocabulary | **B3 — rename to real SDK names + typed base/custom/(deferred-broker) partition** | Matches (recommended B3) | Medium (renames tested shapes; mechanical) |
| **D-C** table shape | **C1 — single flat TS object literal** (extend S1's `ROLE_ALLOW_SETS`, now carrying the B3 typed partition) | Matches (recommended C1) | Narrowest; C3 rejected on integrity |
| **D-D** supersession timing | **D2 — pi artifacts only; Tier-3 amend as a SEPARATE follow-up plan** | Matches (recommended D2) | Narrowest (lowest regret) |
| **D-E** manifest scope | **Minimal-but-complete (E-i + E-ii only)** | Matches (recommended E-i+E-ii) | Narrowest; E-iii/E-iv excluded |
| **Micro** broker placeholder | **Inert declared name now** (git-ops declares its broker name in `brokerTools`, inert until S6) | Matches (default framing) | Narrow; satisfies the exit criterion's G-2 clause at the table level |

**Convergence summary:** five of six matched the recommendation; **D-A diverged.**
The operator chose to enable real nested delegation *within S2* (pass
`customTools` through now) rather than deferring it to S3. This **changes the S2
framing** the recommendations were built on: S2 is no longer a pure
table+manifest slice — it now also carries the `customTools` pass-through
mechanism and its end-to-end depth-cap proof (part of S3's scope pulled forward,
per the D-A "What this means for the plan stage" note above). The other five
retain the **narrowest-blast-radius** theme; D-A deliberately widens it, with the
Reversibility-Filter/Scope-Creep cautions recorded as weighed-and-overridden.

## Open Questions (for `gleipnir-plan`, from the converged choices)

- **[D-A follow-through] The `customTools` pass-through mechanism is now an
  S2-plan design element (converged A1).** `gleipnir-plan` must design: (a) which
  roles receive `delegate` in their passed-through `customTools` (DRY-sourced from
  the role table's `customTools` partition; deny-by-default still governs — a role
  without `delegate` in its allow-set must not receive it); (b) the end-to-end
  depth-cap behaviour under real nested `delegate` re-invocation (the AC-7 counter
  proof is no longer sufficient — an actual child that itself calls `delegate`
  must be exercised); (c) the explicit S2/S3 re-scoping note (this piece of S3 is
  pulled forward). Name it as a design element, do not silently absorb it.
- Whether the S2 deny-by-default proof should be **one aggregate test over all 8
  roles** (a single loop asserting every unlisted tool is denied for every role)
  or **per-role tests** — a plan-stage ATLAS Assemble decision, not material.
  Note the proof must now also cover: the G-2 sole-git-holder assertion; the
  inert-declared broker name (every non-`git-ops` role denies it; `git-ops`'s is
  present-but-inert); and — per the D-A convergence — that `customTools`
  pass-through respects deny-by-default (no child receives `delegate` unless its
  role declares it).
- The broker-placeholder representation is **converged (inert declared name
  now)** — see the Micro-decision above. Remaining for `gleipnir-plan` to Trace:
  the exact inert-name string(s) for git-ops's `brokerTools` entry and how the
  hook treats an inert (declared-but-unreachable) name pre-S6.
- The `orchestrator` role is `mode: primary` in opencode; the pi re-expression's
  "active role" model (`activeRole.ts` stack) must represent the top-level
  orchestrator session — confirm how the stack is seeded at `session_start` for
  the primary role. Plan-stage Trace.

## Scope Sketch

| Area | Artifact / module likely affected |
|------|-----------------------------------|
| Role table (D-C=C1, D-B=B3) | `pi-package/src/roleTable.ts` — extend to 8 roles; rename to real `ToolName`s; typed base/custom/(deferred-broker) partition |
| Enforcement hook | `pi-package/src/enforcement.ts` — unchanged logic (depends only on `canUse`); benefits from the vocabulary fix |
| Delegation (D-A=A1, CONVERGED IN-SCOPE) | `pi-package/src/delegate.ts` — `customTools: []` is REPLACED by a role-scoped pass-through projecting each child role's declared `customTools` (deny-by-default preserved); design + end-to-end depth-cap proof under real nested re-invocation. **Part of S3's scope pulled forward into S2 — name it explicitly.** |
| Tests | `pi-package/test/*.test.ts` — rename `read_file`/`write_file` → `read`/`write`; add per-role (or aggregate) deny-by-default proof for all 8 roles; G-2 sole-git-holder assertion; inert-broker-name assertion; **end-to-end nested-`delegate` depth-cap proof (new, from D-A=A1)** |
| Manifest (D-E) | `pi-package/package.json` `pi` key (complete) + NEW `.pi/settings.json` (wire enforcement extension + trust posture) — E-i + E-ii only |
| Tier-3 amend (D-D=D2) | `stage-role-map.md` (`X`/`E`) + `AGENTS.md` (`OPENCODE_CONFIG_DIR`) — **SEPARATE follow-up plan, NOT this slice**; operator-authored (no roster subagent can write Tier-3) |
| Source-of-truth roster | `.gleipnir/agents/*.md` (all 8, read this session) — the capability sets the TS table must re-express |

## Design Principles (Gate 1)

**Routing:** this brief is **prose-only** (`P = { this .md file }`, `P ∩ X = ∅`).
Per `plan-format.md` case (iii), SOLID/DRY/SRP are **`N/A — no executable
artifact`**.

**Design Intent (specific, falsifiable):** *This brief must (1) surface all five
S2 decision points (D-A…D-E) plus the broker-placeholder micro-decision with a
named framework and a run of the 12 bias detectors and a recommendation for
each, AND (2) record the operator's CONVERGED choice for each — where those
choices were converged by the OPERATOR via the ORCHESTRATOR's `question` tool,
NOT self-attested by this subagent (a subagent's own `question` cannot reach the
operator, so a subagent must never invent a convergence; it may only transcribe
one the orchestrator hands back). Divergences from the recommendation (D-A) must
be recorded honestly as divergences, not softened into agreement.* A reviewer
can falsify this by finding: (a) any of the six decisions missing its framework
or bias check or recommendation; (b) any converged choice recorded that the
orchestrator did not hand back (a self-attested/invented convergence); (c) the
D-A divergence softened, hidden, or mislabelled as a match; (d) the brief
expanding/narrowing S2's build-order-fixed scope beyond what the converged
choices entail — noting that the converged D-A=A1 legitimately pulls the
`customTools` pass-through slice of S3 forward into S2, which the brief must name
explicitly (not silently absorb) rather than treat as scope creep; or (e)
dropping the G-2 sole-git-holder exit requirement.
