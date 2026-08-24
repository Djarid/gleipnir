# ATLAS Plan: pi.dev replatform — Step S2 (full role→capability table + package manifest)

> **Status: PLAN (Tier-0, transient).** Written by `gleipnir-plan` from the
> **CONVERGED** design brief `pi-dev-replatform-s2-brainstorm.md` (all six
> decisions operator-converged; D-A diverged from the brainstorm recommendation
> and is IN-SCOPE). This plan Architects/Traces **HOW** to build S2; it does not
> re-decide any of D-A…D-E or the broker micro-decision — those are converged
> inputs. The one place this plan flags for operator/spec-review attention is the
> **residual live-model-turn empirical limit** carried from S1 (Open Items §),
> not a re-opened decision.

## GOTCHA pre-flight (output visibly, per methodology)

- **Goals check (`goals/manifest.md`).** The relevant goal is **Plan format**
  (`goals/plan-format.md`) — followed here (Decisions index, Architect, Trace,
  Link, Assemble, Stress-test, Execution Workflow, Design Principles). No
  pipeline-sequencing goal is invoked (deliberately absent per the manifest's
  G-5 rule; the orchestrator sequences).
- **Order.** Plan-before-code confirmed. This is the `plan` stage; no code is
  written here. Test-first discipline is specified in Assemble (stubs before
  tests before implementation).
- **Gaps named.** None in goals. One inherited *empirical* gap (not a planning
  gap): the live-model-turn E2E case S1 could not reach under `--network=none`
  (README "D6 finding"). It bounds what the new depth-cap E2E proof can assert;
  named explicitly in Trace edge cases and Open Items.
- **Convergence provenance.** Six converged decisions come from the brief's
  **Operator convergence** lines (converged by the operator via the
  orchestrator's `question` tool). This subagent did not and cannot converge
  anything itself; it plans from what was handed back.

## Pipeline routing statement (REQUIRED — read before anything else)

**Full 8-stage hardened pipeline.** `brainstorm → plan → spec-review → test →
code → quality → git → gate`, no collapse to the prose/config-only light track.

- **Touched-path set `P`** (what this plan's implementation will change). Note
  (D2 re-baseline): most of these files ALREADY exist on disk with substantial
  S2 work from a prior interrupted session; "edit" below means the remaining
  DELTA, and the two paths the S1 README would have called "new" are in fact
  already present:
  - `pi-package/src/roleTable.ts` (edit — D1 `baseTools` fix; already 8-role typed)
  - `pi-package/src/delegate.ts` (verify — pass-through already built)
  - `pi-package/test/roleTable.test.ts` (edit — **already exists, untracked**; add D1 positive cases)
  - `pi-package/test/delegate.test.ts` (edit — fix D1-inverted negative cases)
  - `pi-package/test/enforcement.test.ts` (edit — fix D1-invalidated `bash` deny probe)
  - `pi-package/package.json` (verify — `pi` key + description already present)
  - `pi-package/.pi/settings.json` (verify — **already exists**)
  - `pi-package/README.md` (edit — supersede "Known limitations for S2",
    extend AC table, note the D1 coarse-presence correction)
  - `pi-package/src/enforcement.ts` (verify — already S2-vocab + seed handler;
    logic unchanged)
- **Axis-1 disqualifier check.** `pi-package/**` is NOT one of the literal `X`
  members in `stage-role-map.md` (which enumerate opencode-era paths:
  `src/**`, `tests/**`, `.github/**`, etc.). **However**, `pi-package/src/**`
  and `pi-package/test/**` are **executable/interpreted TypeScript with a real
  test arbiter** (`node --test`, `tsc --noEmit`), i.e. functionally equivalent
  to `src/**`/`tests/**`. Per the operator's routing instruction (point 6),
  they are treated as `X`-equivalent → the plan is **NOT track-eligible** →
  **full 8-stage pipeline**. The `.pi/settings.json` and `package.json` edits do
  not rescue eligibility: eligibility is disqualified by the presence of ANY
  executable artifact in `P`, and TS source is present.
- **Axis-2(a) enforcement-path set `E` check.** `P` contains **NO** member of
  `E`. Confirmed by exact-path inspection: no `.gleipnir/agents/**`, no
  `.gleipnir/plugins/**`, no `.gleipnir/sandbox/**`, no `.gleipnir/policy/**`,
  no `.gleipnir/keys/**`, **not `stage-role-map.md` itself**, not
  `opencode.jsonc`/`**/opencode.json`, and none of the enumerated repo-root
  cross-cutting files (`.gitignore`, `.envrc`, `pyproject.toml`,
  `.gitattributes`, `.gitmodules`). **The Tier-3 amend of `stage-role-map.md`
  (`X`/`E`) and `AGENTS.md` (`OPENCODE_CONFIG_DIR`) is explicitly OUT of this
  plan** (D-D=D2 convergence: it is a SEPARATE operator-authored follow-up plan;
  no roster subagent can write Tier-3 regardless). This plan touches zero
  `E`-set files.
- **Consequence for review.** Because it is executable code (not the light
  track) it runs the full pipeline; the hardened-path negative-check attestation
  machinery in `stage-role-map.md` is about *enforcement-bearing config* edits —
  this plan is code, so its arbiter is the **pre-written test suite** (Axiom 1),
  reviewed at `spec-review` (test design) and `quality` (blast-radius +
  SOLID/DRY + honour-check). Note nonetheless: `roleTable.ts` **is the
  enforcement policy table** in content, even though its path is not in `E`; the
  `quality` blast-radius pass MUST treat a wrongly-widened allow-set (esp. a
  second role gaining git, or a role gaining `delegate` it should not) as the
  false-success class L-C7 exists to catch.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-A | Nested delegation scope in S2 | **IN-SCOPE now** — `delegate.ts` passes each child's declared `customTools` through; real nested `delegate` re-invocation enabled + depth-cap proven E2E | Defer to S3 (the brainstorm recommendation A2) | **Operator-converged (DIVERGES from recommendation).** Recorded honestly. Pulls part of S3's delegation-model scope forward into S2 (named in Trace §S2/S3 re-scoping) |
| D-B | Tool vocabulary | **Real SDK `ToolName`s + typed `baseTools`/`customTools`/`brokerTools` partition** | Keep `read_file`/`write_file` (B1 flat / B2 translation) | Operator-converged (matches). Fidelity to verified `.d.ts` union `read\|bash\|edit\|write\|grep\|find\|ls`; drops the README's `powershell` error |
| D-C | Table shape | **Single flat frozen TS object literal** (extend `ROLE_ALLOW_SETS` to 8 roles, carrying the D-B partition) | Per-role files (C2); external JSON/TOML config (C3) | Operator-converged (matches). C3 rejected: an externally-editable enforcement table is a Tier-3 bypass (no `tsc`, no review) |
| D-D | stage-role-map/AGENTS.md supersession timing | **Separate follow-up plan** — S2 builds pi-package artifacts only | Amend Tier-3 files inside this S2 plan (D1) | Operator-converged (matches). Task-decomposition isolation + hard fact: no roster subagent can write Tier-3 |
| D-E | Manifest / `.pi/settings.json` scope | **Minimal-but-complete: complete `package.json` `pi` key + one `.pi/settings.json`** | Per-role settings (E-iii); skills/prompts/themes dirs (E-iv) | Operator-converged (matches). E-iii excluded: a second capability surface = DRY/integrity seam vs the TS table |
| Micro | Broker placeholder in table | **Inert declared name in `git-ops.brokerTools` now** | Omit until S6 | Operator-converged (matches default framing). Satisfies exit criterion's G-2 clause at table level; not wired to real reachability (S6/Open-Q3) |
| P1 | Deny-by-default proof shape | **One aggregate table-driven proof over all 8 roles** + targeted per-invariant assertions (G-2 sole-git; inert-broker; delegate-pass-through) | Only per-role tests | Plan-stage ATLAS Assemble choice (brief flagged this as non-material). Aggregate loop is the single auditable place the exit criterion's "every role, deny-by-default" is proven; targeted assertions cover the named invariants |
| P2 | `question`/`webfetch`/`notify`/pm representation in the table | **Named custom-tool strings in `customTools` where a role's opencode set grants them; NOT `brokerTools`** | Put pm/notify in `brokerTools`; omit them | Plan-stage Trace choice. `brokerTools` is reserved (Micro) for the **G-2 git broker sole-holder** proof; pm/notify/webfetch/question are non-git capabilities and must not dilute the "only git-ops has a broker name" assertion. See Trace §capability mapping for the exact per-role strings and the reversal note |
| P3 | Child `customTools` derivation source | **DRY-projected from the same role table** (`resolveChildCustomTools(role)` reads `ROLE_ALLOW_SETS[role].customTools`) | Hand-duplicate a pass-through list in `delegate.ts` | Plan-stage Design (DRY). The allow-set is defined once; `delegate.ts` projects it, mirroring the existing `resolveChildTools` pattern |
| P4 | Active-role seed for the primary `orchestrator` | **`session_start` seeds the stack with `orchestrator`** via `setActiveRole` | Leave the stack empty (deny-by-default everything at top level) | Plan-stage Trace (brief Open Q). The top-level session IS the orchestrator; without a seed every top-level tool call denies. See Trace §activeRole seeding |

> Every row's full reasoning is in the sections below. Rows D-A…Micro cite the
> operator convergence; rows P1…P4 are plan-stage decisions (Assemble/Trace/
> Design choices the brief explicitly left to the plan, none material — P2 and
> P4 are the two worth spec-review scrutiny).

---

## Architect

**Problem (one sentence).** Promote S1's one-role, wrong-vocabulary
proof-of-mechanism to the full 8-role deny-by-default Gleipnir roster expressed
in the SDK's real tool vocabulary with a typed base/custom/broker partition,
finalise the minimal Pi package manifest + `.pi/settings.json` surface, and —
per the D-A convergence — make each role's declared `delegate` capability
actually reachable end-to-end by projecting child `customTools` from the table,
proving the depth cap holds under real nested re-invocation.

**User.** The enforcement extension (`enforcement.ts`, unchanged logic) and the
delegation tool (`delegate.ts`) at runtime; the operator and downstream steps
(S3 delegation model, S4 engine, S6 broker, S7 preflight) that consume the
8-role table as the canonical capability surface; `quality-reviewer` auditing
deny-by-default per role.

**Measurable success criteria.**

1. `ROLE_ALLOW_SETS` contains all 8 roster roles (`orchestrator`,
   `gleipnir-brainstorm`, `gleipnir-plan`, `gleipnir-code`, `quality-reviewer`,
   `git-ops`, `project-mgr`, `notify`), each with a typed
   `{ baseTools, customTools, brokerTools }` allow-set, frozen.
2. Vocabulary is the real SDK `ToolName` union for `baseTools`
   (`read | bash | edit | write | grep | find | ls`); no `read_file`/
   `write_file`/`powershell` anywhere. **Coarse-presence rule honoured (D1):**
   a capability that is PRESENT-but-scoped in a role's frontmatter appears in
   that role's `baseTools` (coarse: can-ever-call = yes), with its path/arg
   restriction recorded in `bounds` — `edit` for `gleipnir-brainstorm`/
   `gleipnir-plan` (scoped to `.gleipnir/plans/**`); `bash` for `gleipnir-code`/
   `quality-reviewer`/`git-ops` (arg-allowlisted). A capability that is
   genuinely DENIED (absent, not scoped) is correctly out of `baseTools`
   (`orchestrator`, `project-mgr`, `notify` hold no `edit`/`bash`).
3. `git-ops` is the **only** role whose `brokerTools` is non-empty (carries the
   inert git-broker name); every other role's `brokerTools` is empty (G-2 at the
   table level).
4. Deny-by-default proven **per role**: for every role, every tool NOT in its
   union allow-set resolves to `false` via `canUse`.
5. `delegate.ts` no longer passes `customTools: []` unconditionally; it projects
   each child role's declared `customTools` from the table (DRY), so a child
   whose role declares `delegate` receives it and a child whose role does not,
   does not.
6. The depth cap holds under **real nested `delegate` re-invocation** end-to-end
   (a real child that itself invokes the real `delegate` execute), refusing past
   the cap — the AC-7 counter-only proof is superseded/augmented by an E2E proof
   using the same real-`createAgentSession` + `prompt`-stub technique S1's
   AC-9-E2E established.
7. `package.json` `pi` key is complete (extensions list resolves the enforcement
   + delegate modules); one `.pi/settings.json` wires the enforcement extension
   and declares the project-trust posture.
8. `tsc --noEmit` clean and `node --test` green in
   `bin/gleipnir-sandbox {test,lint} --profile pi`.

**Constraints (from the 6 converged decisions + build-order exit criterion).**

- **Exit criterion (verbatim, ADDED-to by D-A, never narrowed):** "every role's
  allow-set is expressed and tested; the single broker holder (`git-ops`) is the
  only role whose table grants git (G-2 clause preserved at the table level);
  deny-by-default proven for each role" **PLUS** (D-A convergence) "real nested
  delegation end-to-end proven for at least the roles whose allow-set includes
  `delegate`, with the depth cap holding under that real path."
- **G-2 single-broker-holder** must survive at the table level: only `git-ops`
  carries a broker name.
- **Deny-by-default** is the posture — no implicit-allow path; unset/unknown
  role and unknown tool → `false` (preserve S1's `canUse` semantics).
- **Re-expression, not port** — fit pi.dev's real model; do not preserve
  opencode-shaped structure for its own sake.
- **C3 rejected**: the enforcement table stays TS-as-data inside the
  type-checked/review-gated code tier (never external parsed config).
- **D-D scope wall**: NO edit to `stage-role-map.md` or `AGENTS.md` in this
  plan (Tier-3, separate follow-up, operator-authored).
- **Per-path/per-arg opencode `permission:` bounds** (e.g. `gleipnir-code`'s
  `.gleipnir/**` edit-deny, its bash allowlist; `git-ops`'s `.git/**` read-deny
  + branch/sync bash allowlist; reviewer's read-only git bash) are **NOT
  expressible as base-tool grants** — a base `ToolName` grant is coarse
  (tool present/absent). Per S2's goal ("re-express the per-path/per-arg bounds
  the opencode `permission:` map used to carry, now in the extension's block
  logic"), these bounds are recorded as **table metadata / block-logic
  obligations**, NOT silently dropped. See Trace §per-arg bounds for exactly how
  S2 handles them vs. what it defers to S3/S7.

---

## Trace

### Artifacts and where they live (source of truth)

**Status column re-baselined (D2) against the actual working tree, not the S1
README.** Most artifacts already carry substantial S2 work from a prior
interrupted session (operator-confirmed); the "Status" now states what is
ALREADY on disk and what the remaining DELTA is.

| Artifact | Path | Status (current-actual → DELTA) | Source of truth it re-expresses |
|---|---|---|---|
| Role→capability table | `pi-package/src/roleTable.ts` | **already the 8-role typed partition on disk**; DELTA = fix D1 `baseTools` omission (add `edit` to brainstorm/plan; `bash` to code/reviewer/git-ops) | `.gleipnir/agents/*.md` frontmatter `permission:`/`tools:` blocks (all 8, read this session) |
| Enforcement hook | `pi-package/src/enforcement.ts` | **already S2-vocab + registers `session_start` seed**; logic unchanged; DELTA = none (verify) | S1; depends only on `canUse` (Dependency Inversion) |
| Delegation tool | `pi-package/src/delegate.ts` | **already exports `resolveChildCustomTools`/`buildDelegateTool` + projects `customTools` pass-through**; DELTA = verify green post-D1 | S1; D-A convergence |
| Active-role state | `pi-package/src/activeRole.ts` | **already exports guarded `seedActiveRoleIfEmpty`**; logic unchanged; DELTA = none (verify) | S1 |
| Depth cap | `pi-package/src/depth.ts` | logic unchanged; exercised E2E by AC-13/14 (already present) | S1 |
| Role-table tests | `pi-package/test/roleTable.test.ts` | **already EXISTS (untracked)** with AC-16/17/18/19; DELTA = add named D1 positive cases (`canUse` true for the new `edit`/`bash`) | success criteria 1–4, Micro, P1 |
| Enforcement tests | `pi-package/test/enforcement.test.ts` | **already S2-vocab + AC-15/AC-16(hook)**; DELTA = fix the `"bash"` universal-deny probe D1 invalidates | S1 AC-1..AC-4 |
| Delegation tests | `pi-package/test/delegate.test.ts` | **already has AC-11/12/12b/13/14 + AC-9-E2E**; DELTA = fix any `bash`-denied-for-code negative case D1 inverts; sweep stale flat-iterable assertions | S1 AC-5..AC-9-E2E |
| Package manifest | `pi-package/package.json` | **`pi` key + description already present/correct**; DELTA = verify only | build-order S2 goal; D-E |
| Project surface | `pi-package/.pi/settings.json` | **already EXISTS**; DELTA = verify valid JSON + minimal-but-complete | D-E (E-ii) |
| Package README | `pi-package/README.md` | edit (supersede "Known limitations for S2"; extend AC table AC-11..AC-21; note the D1 coarse-presence correction) | S1 README |

### Capability mapping — opencode roster → pi-native typed partition (the load-bearing Trace)

Each role's `.gleipnir/agents/*.md` `permission:`/`tools:` block, re-expressed
into `{ baseTools: ToolName[], customTools: string[], brokerTools: string[] }`.
**`baseTools`** = the SDK's 7 real base `ToolName`s the role may call.
**`customTools`** = Gleipnir/host custom tools the role may call (`delegate`,
and — per P2 — the non-base host capabilities `webfetch`/`question`/`notify`/pm
that are neither base `ToolName`s nor the git broker). **`brokerTools`** =
reserved for the git broker sole-holder (Micro/G-2); non-empty ONLY for
`git-ops`.

| Role | opencode source (frontmatter) | `baseTools` | `customTools` | `brokerTools` | Per-arg/per-path bound (metadata; see §per-arg) |
|---|---|---|---|---|---|
| `orchestrator` | edit/bash/webfetch **deny**; `question` allow; `task` allow→8 subagents; both broker ns **false** | `[]` | `["delegate","question"]` | `[]` | `question` (host UI) also grantable — see P2 note; primary session seed (P4). edit/bash **genuinely absent** (denied, not scoped) → correctly out of `baseTools` |
| `gleipnir-brainstorm` | read allow; webfetch allow; **edit `*`:deny / `.gleipnir/plans/**`:allow** (edit capability PRESENT, path-scoped); question/task/bash deny; brokers false | `["read","edit"]` | `["webfetch"]` | `[]` | **edit present but scoped to `.gleipnir/plans/**` only** (coarse `edit` in `baseTools`; the path restriction is the fine-grained bound, arg-level S3/S7) |
| `gleipnir-plan` | read allow; webfetch allow; **edit `.gleipnir/plans/**` only** (edit capability PRESENT, path-scoped); task/bash deny; brokers false | `["read","edit"]` | `["webfetch"]` | `[]` | **edit present but scoped to `.gleipnir/plans/**` only** (coarse `edit` in `baseTools`; the path restriction is the fine-grained bound, arg-level S3/S7) |
| `gleipnir-code` | edit `*`:allow / `.gleipnir/**`,`.git/**`,`.github/**`,`preflight/**`:deny (+ exact-path allows); read allow; **bash sandbox-allowlist** (bash capability PRESENT, arg-scoped); task/webfetch deny; brokers false; **delegate** in S1 allow-set | `["read","edit","bash"]` | `["delegate"]` | `[]` | edit path-denies (`.gleipnir/**` etc.); **bash present but allowlisted** to `bin/gleipnir-sandbox {test,lint}` + profiles (coarse `bash` in `baseTools`; the arg allowlist is the fine-grained bound, arg-level S3/S7) |
| `quality-reviewer` | edit/write deny; read allow; **bash `git {diff,log,show,status}*` allow** (bash capability PRESENT, arg-scoped); task/webfetch deny; brokers false | `["read","bash"]` | `[]` | `[]` | edit/write genuinely absent → out of `baseTools`; **bash present but allowlisted** to read-only `git {diff,log,show,status}` (coarse `bash` in `baseTools`; the arg allowlist is the fine-grained bound, arg-level S3/S7) |
| `git-ops` | edit/write deny; read `*`:allow/`.git/**`:deny; **bash branch/sync allowlist** (bash capability PRESENT, arg-scoped); git broker **kept**, pm **false** | `["read","bash"]` | `[]` | `["gleipnir-git_*"]` (inert) | read `.git/**`-deny (path bound); **bash present but allowlisted** to branch/sync verbs (status/diff/log/checkout/switch/branch/merge/fetch/pull); commit+push move to the broker (coarse `bash` in `baseTools`; the arg allowlist is the fine-grained bound, arg-level S3/S7) |
| `project-mgr` | edit/write/bash/task/webfetch deny; read allow; pm broker **kept**, git **false** | `["read"]` | `["gleipnir-pm_*"]` (see P2 note) | `[]` | edit/write/bash genuinely absent (denied, not scoped) → correctly out of `baseTools`. pm namespace is a broker in opencode but represented in `customTools` here to keep `brokerTools` = git-only for the G-2 proof |
| `notify` | edit/write/bash/task/webfetch deny; read allow; both broker ns false; holds notify namespace | `["read"]` | `["notify"]` | `[]` | edit/write/bash genuinely absent (denied, not scoped) → correctly out of `baseTools`. notify namespace (host tool) in `customTools` |

**D1 correction note (coarse-presence vs fine-grained bound — read carefully; this fixes the spec-review D1 defect).** A base `ToolName` grant is **coarse**: it answers "can this role EVER call this tool?" — present or absent. The plan's own Architect Constraints require that when a capability is present-but-path/arg-scoped, the coarse presence lives in `baseTools` and the fine-grained restriction is recorded as `bounds` metadata (unenforced by S2, deferred to S3/S7), **NOT silently dropped**. The plan already applied this correctly for `gleipnir-code`'s `edit` (present in `baseTools`, `.gleipnir/**`-deny recorded in `bounds`). The five rows above now extend that same treatment to the capabilities that were previously wrong:
- **`gleipnir-brainstorm`, `gleipnir-plan`** — each has a real `edit` grant scoped to `.gleipnir/plans/**` (their frontmatter is `edit "*": deny; ".gleipnir/plans/**": allow`). The coarse answer to "can this role call `edit`?" is **yes**, so `edit` MUST appear in `baseTools`; the `.gleipnir/plans/**`-only restriction is the `bounds` metadata. (Previously `baseTools: ["read"]` only — the coarse/fine principle violated.)
- **`gleipnir-code`, `quality-reviewer`, `git-ops`** — each has a real, arg-scoped `bash` allowlist. The coarse answer to "can this role call `bash`?" is **yes**, so `bash` MUST appear in `baseTools`; the allowlist (`bin/gleipnir-sandbox {test,lint}` for code; `git {diff,log,show,status}` for reviewer; branch/sync verbs for git-ops) is the `bounds` metadata. (Previously `bash` omitted entirely from all three.)

`orchestrator`, `project-mgr`, `notify` deliberately keep no `edit`/`bash` in `baseTools` because those capabilities are **genuinely denied** in their frontmatter (absent, not scoped) — the coarse answer there is legitimately "no". The corrected `baseTools` per affected role, in one line each: `gleipnir-brainstorm` → `["read","edit"]`; `gleipnir-plan` → `["read","edit"]`; `gleipnir-code` → `["read","edit","bash"]`; `quality-reviewer` → `["read","bash"]`; `git-ops` → `["read","bash"]`.

> **Consequence the implementing agent MUST propagate (D1 ripple into tests).**
> Because `bash` is now a real `baseTools` member for three roles,
> `enforcement.test.ts`'s existing "AC-16 (hook)" test — which uses `"bash"` as
> its *universal* deny probe across all 8 roles (`const universallyDenied =
> "bash"`) — is now **FALSE and will fail** (`bash` is allowed for
> `gleipnir-code`/`quality-reviewer`/`git-ops`). The universal deny probe MUST
> switch to a name absent from **every** role's union allow-set (e.g. the
> `UNIVERSALLY_DENIED = "totally_unregistered_tool_xyz"` constant already used
> in `roleTable.test.ts`). Similarly any AC-2/AC-9 case that asserts
> `gleipnir-code` DENIES `bash` (e.g. `enforcement.test.ts` AC-1/AC-4,
> `delegate.test.ts` AC-9/AC-9-E2E "bash is deliberately absent") is now
> **inverted** — `bash` is ALLOWED for `gleipnir-code`; those negative cases
> must pick a tool that is genuinely still denied for the role under test
> (e.g. `write`, or the unregistered probe) to remain valid. This is a direct,
> mechanical consequence of the D1 fix and is folded into Assemble step 3.

**P2 reversal note (spec-review, read carefully).** In opencode, `git-ops` holds
`gleipnir-git_*` and `project-mgr` holds `gleipnir-pm_*` — both are MCP broker
namespaces of the SAME structural class. This plan deliberately places ONLY the
git broker name in `brokerTools`, and puts the pm namespace in
`project-mgr.customTools`. **Rationale:** the exit criterion's G-2 clause is
specifically *"git-ops is the only role whose table grants git"* — the
load-bearing invariant is about **git**, and the cleanest falsifiable assertion
is "exactly one role has a non-empty `brokerTools`, and it is `git-ops`." If pm
also lived in `brokerTools`, that assertion would need weakening to
"only-git-in-brokerTools" (a substring check), which is a weaker, more
error-prone proof. **This is a plan-stage modelling choice, not a capability
change** — `project-mgr` still gets its pm namespace (in `customTools`), no
other role does, and git-ops still uniquely holds git. If spec-review judges
that pm belongs in `brokerTools` for honesty about its broker nature, the
alternative is: keep both in `brokerTools` and change the G-2 assertion to
"`git-ops` is the only role whose `brokerTools` contains a `gleipnir-git*`
name." Either is defensible; **surfaced here for spec-review to confirm, not
silently chosen.** (Both preserve deny-by-default and G-2; the difference is
only which partition carries the pm string and how the assertion is phrased.)
This is the one modelling decision in the plan a reviewer should actively
ratify.

**`question` for orchestrator (P2, minor).** `question` is a host UI primitive
(orchestrator-only, the operator channel). It is not a base `ToolName` and not a
broker. It may be listed in `orchestrator.customTools` for completeness, or
noted as a host-UI capability outside the table's enforcement scope. Recommended:
list it in `customTools` for a faithful re-expression, since `canUse` governs
whether a role may invoke a named tool and only the orchestrator should be able
to invoke `question`. Non-material; spec-review may confirm.

### Per-arg / per-path bounds — what S2 does vs. defers (S2 goal item 3)

S2's goal says to "re-express the per-path/per-arg bounds the opencode
`permission:` map used to carry, now in the extension's block logic." The
honest scope split:

- **In S2 (this plan):** record each role's per-arg/per-path bound as
  **table metadata** alongside its allow-set (a `bounds` field or a documented
  comment per role), so the information is captured in the canonical table and
  not lost. The `canUse(role, toolName)` **coarse** allow/deny is what S2's hook
  enforces (a tool is present or absent for a role) — this is unchanged S1
  mechanism proven at 8-role scale.
- **Deferred (named, not silently dropped):** the *fine-grained* enforcement of
  those bounds — e.g. "`gleipnir-code` may `edit` but NOT under `.gleipnir/**`",
  "`git-ops` may `read` but NOT `.git/**`", "`quality-reviewer`'s bash is
  `git diff|log|show|status` only" — requires the hook to inspect `event.input`
  (path/argv), not just `event.toolName`. S1's `enforcement.ts` reads only
  `event.toolName`. **Extending the hook to argument-level inspection is
  S3/S7-shaped work** (S7 is the config-preflight/over-broad-grant scanner; the
  argument-policy is the E-1 seam). **S2 does NOT build argument-level
  enforcement** — it captures the bounds as data so the later step has a
  source, and the coarse tool-presence enforcement is what S2 proves. This
  boundary is stated so a reviewer does not mistake "bounds recorded as
  metadata" for "bounds enforced." If the operator wants argument-level
  enforcement inside S2, that is a **material scope expansion beyond the
  converged brief** and must go back to the brainstorm gate — this plan does
  NOT assume it.

  > **Flag for spec-review/operator:** the brief's Constraints list the per-arg
  > bounds as context but the six converged decisions (D-A…D-E, Micro) do NOT
  > include "build argument-level enforcement in S2." The exit criterion is
  > about allow-*set* expression + deny-by-default + G-2 + nested-delegate, all
  > of which are tool-presence-level. This plan therefore treats argument-level
  > enforcement as **out of S2 scope, captured-as-metadata**, and flags it
  > rather than deciding to build it. See Open Items §1.

### `customTools` pass-through mechanism (D-A convergence — named design element)

**This is the S3-scope-pulled-forward-into-S2 element. Named explicitly, not
absorbed.** (See §S2/S3 re-scoping note below.)

> **CURRENT-STATE BASELINE (D2 re-baseline — read `pi-package/src/*` on disk,
> this session, before trusting any "S1 today" phrasing).** The stale S1-README
> framing ("`delegate.ts` passes `customTools: []` unconditionally";
> "`roleTable.ts` has one role") is **FALSE against the actual working tree**.
> Uncommitted working-tree changes from a prior interrupted session (operator-
> confirmed, KNOWN — not a mystery) have already built substantial S2 machinery
> on disk. What is ACTUALLY present right now:
> - `roleTable.ts` — **already the full 8-role typed
>   `{baseTools,customTools,brokerTools,bounds}` partition** with `RoleAllowSet`,
>   `SDK_BASE_TOOL_NAMES`, `GIT_BROKER_TOOL`/`PM_BROKER_TOOL`, `unionAllowSet`,
>   deep-freeze, and the S2-vocabulary `canUse`. It is **NOT** the one-role
>   `read_file`/`write_file` table the S1 README describes. It carries the D1
>   defect (brainstorm/plan lack `edit`; code/reviewer/git-ops lack `bash` in
>   `baseTools`) — that is what D1 above fixes IN PLACE.
> - `delegate.ts` — **already exports `resolveChildCustomTools`,
>   `DELEGATE_TOOL_NAME`, `buildDelegateTool`**, and its `execute` **already
>   projects `childCustomTools` from the table** (`resolveChildCustomTools` →
>   `[buildDelegateTool()]` iff the role declares `"delegate"`, else `[]`) and
>   passes it as `customTools` into `createAgentSession` — it does **NOT** pass
>   `customTools: []` unconditionally. The pass-through mechanism this section
>   describes is largely BUILT.
> - `activeRole.ts` — **already has `seedActiveRoleIfEmpty`** (the P4 guarded
>   seed) with the empty-stack guard.
> - `enforcement.ts` — **already registers the `session_start` seed handler**
>   (`seedActiveRoleIfEmpty(PRIMARY_ROLE)`) and the `tool_call` block-hook in S2
>   vocabulary.
> - `test/roleTable.test.ts` — **already EXISTS** (untracked): AC-16/17/18/19
>   coverage over the 8-role table. `test/delegate.test.ts` — already has
>   AC-11/AC-12/AC-12b/AC-13/AC-14 and the AC-9-E2E technique.
>   `test/enforcement.test.ts` — already has AC-15 + AC-16(hook), BUT uses
>   `"bash"` as its universal deny probe (the D1 ripple: now wrong).
> - `package.json` `pi` key + `.pi/settings.json` — **already present** (D-E
>   largely done).
>
> **Therefore S2 is a DELTA on a mostly-built tree, not a build-from-S1.** The
> Assemble steps below are re-framed as the delta between this current-actual
> state and the target state. The "S1 today" bullets retained below are kept
> ONLY as the historical origin narrative (why the mechanism exists); the
> authoritative "what needs doing" is the delta in Assemble.

- **S1 origin (historical — why this mechanism exists, NOT current state):** in
  the S1 proof-of-mechanism `delegate.ts` passed `customTools: []` to every
  child unconditionally → a child never received `delegate` → nested delegation
  was architecturally unreachable end-to-end (F4). The prior interrupted session
  already replaced this; see the current-state baseline above.
- **S2 mechanism (largely BUILT on disk — verify, don't re-add):**
  `export function resolveChildCustomTools(role: RoleName): string[]` exists in
  `delegate.ts` (mirroring `resolveChildTools`), reads
  `ROLE_ALLOW_SETS[role].customTools` (DRY — sourced from the table, not
  hand-duplicated). `createAgentSession`'s `customTools` argument is already
  passed the projected definition list (`[buildDelegateTool()]` when the child
  declares `"delegate"`, else `[]`) instead of `[]`. The DELTA the implementing
  agent must confirm/finish: (a) that this projection is correct after the D1
  `baseTools` edit, (b) that the tests exercising it are green post-D1.
- **Deny-by-default preserved:** a child role whose `customTools` does NOT
  include `"delegate"` (e.g. `git-ops`, `quality-reviewer`, `notify`,
  `project-mgr`, both brainstorm/plan) will NOT receive `delegate` — the
  projection copies only what the role's table entry declares. Only
  `orchestrator` and `gleipnir-code` (the two roles whose `customTools` includes
  `"delegate"`) get it passed through.
- **Wiring detail (Link must validate):** `customTools` on `createAgentSession`
  expects **tool definitions** (`defineTool(...)`/registered custom tools), not
  bare name strings (per build-order primitive table: `defineTool()` +
  `customTools:[…]`). `resolveChildCustomTools` returns the role's declared
  custom-tool **names**; the pass-through must map each declared name to its
  actual custom-tool definition. For S2 the only custom tool that is a real,
  registerable delegation tool is `delegate` itself (the module under edit);
  `webfetch`/`question`/`notify`/pm are host/broker primitives without a
  `defineTool` definition in this package. **Therefore the S2 pass-through
  concretely projects `delegate` (the one custom tool this package defines)
  when the child role declares it, and treats the host/broker custom names as
  declared-capability metadata only** (same inert-until-reachable treatment as
  the broker name). This keeps the mechanism honest: a child gets the *actual*
  `delegate` tool definition iff its role declares `"delegate"`; it does not
  fabricate definitions for host primitives that do not exist in this package.
  **Link step MUST verify** against the real `.d.ts` that `customTools` takes
  definitions and confirm the exact shape a self-referential `delegate`
  definition must take to be re-passable to grandchildren (the
  `delegate`-defines-and-passes-`delegate` recursion is the crux of the E2E
  proof).
- **Self-reference / collection-time hazard (L-C30):** because `delegate.ts`
  must now pass a `delegate` tool definition into children, and the E2E test
  references `delegate.ts`'s own exports, the **general timing rule** applies:
  any test module that references a not-yet-built export (e.g.
  `resolveChildCustomTools`) will fail at *collection time* if that export does
  not yet exist. Assemble step 0 (stub-before-tests) exists to prevent this —
  the exports are stubbed first so test collection resolves, then tests are
  written red, then implemented. (Stating the general rule per the operator's
  instruction; no enumerated example list.)

### Depth-cap E2E proof under real nested re-invocation (D-A convergence)

- **S1 origin (historical):** AC-7 proved the cap at the `depth.ts` counter
  level only (`withDepthGuard` nesting), because `customTools: []` blocked a
  real child from ever calling `delegate`. AC-9-E2E proved a real child's hook
  enforces, via the `AgentSession.prototype.prompt` monkey-patch technique (real
  `createAgentSession`, real `_extensionRunner.emitToolCall`, only `prompt`
  stubbed — the `--network=none` limit).
- **Current state on disk (D2 re-baseline):** `test/delegate.test.ts` **already
  contains AC-13/AC-14** — a nested-real-re-invocation test that captures
  `delegate.ts`'s real `execute` via a `registerTool`-capturing shim and, inside
  a stubbed `prompt`, re-enters the real `execute` as a nested `delegate` call,
  asserting refusal past `getCap()` and `getDepth()` restored to 0. So the S2
  E2E proof is BUILT; the DELTA is verifying it is GREEN after the D1 edit (the
  test drives `role: "gleipnir-code"`, whose `baseTools` changes under D1) and
  that no AC-13/14 assertion depended on `bash` being denied to `gleipnir-code`.
- **S2 new proof (`AC-13`, see AC table):** compose the two techniques. A real
  `createAgentSession` child, built by `delegate.ts`'s real `execute` with the
  new pass-through so the child's `customTools` actually contains the `delegate`
  definition, whose stubbed `prompt` drives `this._extensionRunner.emitToolCall`
  for a `delegate` tool call — which, being present in the child, re-enters the
  real `delegate` execute → real `withDepthGuard` → increments the module-scope
  `depth` counter → and at `depth === cap` the real `DepthCapExceededError` is
  raised and surfaced as the graceful refusal `textResult`. The assertion: the
  cap refuses the nested real re-invocation, and `getDepth()` returns to 0 after
  (counter restored via `finally`).
- **What the E2E proof CAN assert** (given the S1 empirical limit): everything up
  to and including the real `emitToolCall` dispatch and the real
  `withDepthGuard`/`depth.ts` counter behaviour across a real nested chain,
  driven through the stubbed `prompt`. **What it CANNOT assert** (named residual
  gap, unchanged from S1): a fully model-driven live turn (no `prompt` stub)
  cannot run under `--network=none` with no provider auth. The E2E proof
  therefore closes the *wiring + counter-under-real-nesting* question; the
  *live-model-turn* remains the one named residual empirical gap (Open Items §2).

### `activeRole` seeding for the primary orchestrator (P4, brief Open Q)

- The `orchestrator` is `mode: primary`; the top-level session IS the
  orchestrator. The `activeRole` stack starts empty (deny-by-default until a
  role is set). If the top-level session's stack is empty, every top-level tool
  call denies (correct fail-safe, but the orchestrator could not even invoke
  `delegate`).
- **S2 design (current state on disk — D2 re-baseline: BUILT):**
  `activeRole.ts` **already exports `seedActiveRoleIfEmpty(role)`** (the guarded
  seed, not the clobbering `setActiveRole`), and `enforcement.ts` **already
  registers `pi.on("session_start", …)` calling `seedActiveRoleIfEmpty(
  PRIMARY_ROLE)`** with `PRIMARY_ROLE = "orchestrator"`. `test/enforcement.test.ts`
  **already has AC-15** proving the seed fills an empty stack and does NOT
  clobber a pushed child role. This is a **wiring** already present, NOT a change
  to `activeRole.ts`'s core logic; the DELTA is confirming AC-15 stays green
  post-D1 (it does not touch `bash`/`edit`, so it should). **Link step MUST verify** the `session_start`
  event shape (build-order confirms `session_start` fires on startup/new/resume/
  fork) and that seeding there does not clobber a child's pushed role (children
  push/pop within a delegate call, which runs after session_start). The seed is
  additive to the stack model: top-level = `orchestrator`; a delegate pushes the
  child role, pops back to `orchestrator` on completion.
- **Non-material** (a wiring choice the brief left to plan-stage Trace);
  recorded for spec-review. If seeding proves to interact with the child-session
  `session_start` (a child `createAgentSession` might also fire `session_start`,
  which would wrongly re-seed `orchestrator` over the pushed child role), the
  seed handler must guard against re-seeding when the stack is non-empty — a
  test case covers this (AC-15).

### Integrations map

```
session_start ──seed──> activeRole(orchestrator)           [P4]
                              │
tool_call event ──> enforcement.ts hook ──> canUse(activeRole, event.toolName)
                              │                     │
                              │              roleTable.ts (8-role typed table)  [D-B,D-C]
                              │
delegate invocation ──> delegate.ts execute
      │                       │
      │        resolveChildTools(role) ──> ROLE_ALLOW_SETS[role] base+custom names
      │        resolveChildCustomTools(role) ──> ROLE_ALLOW_SETS[role].customTools  [D-A,P3]
      │                       │
      │        withDepthGuard ──> depth.ts (module-scope counter)
      │                       │
      │        createAgentSession({ tools, customTools: <projected defs> })
      │                       │
      │        child's DefaultResourceLoader + extensionFactories:[enforcementExtension]  [S1 D6]
      │                       │
      └── nested delegate (child calls delegate) ──> re-enters execute ──> withDepthGuard
                              └── depth === cap ──> DepthCapExceededError ──> graceful refuse  [AC-13]
```

### Edge cases

1. **Unknown role in `canUse`** → `false` (S1 semantics preserved at 8 roles).
2. **Unset active role at top level** → without P4 seed, every call denies;
   with P4 seed, top-level resolves to `orchestrator`'s set. Test both.
3. **`git-ops` reads `.git/**`** → opencode denies it; S2 captures as metadata,
   coarse `read` grant remains (argument-level deferred — see §per-arg). Test
   asserts the metadata is recorded, NOT that `.git/**` read is blocked (that is
   S3/S7).
4. **Inert broker name in `git-ops.brokerTools`** → present in the table
   (capability declared), NOT reachable (S6). `canUse("git-ops",
   "gleipnir-git_commit")` behaviour: the hook treats a `brokerTools` name as a
   declared-but-inert capability — **decision needed:** does `canUse` return
   `true` for an inert broker name (capability declared) or `false` (not yet
   reachable)? **Plan choice:** `canUse` returns `true` for a name present in
   ANY of the role's three partitions (the table declares the capability; reach
   mechanism is separate). The inertness is that no real `gleipnir-git_*` tool
   is *registered/reachable* yet (S6), not that the table denies it. The proof
   asserts: `canUse("git-ops", <broker name>)` is `true` and
   `canUse(<any-other-role>, <broker name>)` is `false` (G-2). This matches the
   brief's Micro plan-stage note ("a declared name is a capability grant in the
   table even before its reach mechanism exists").
5. **Child role without `delegate`** (e.g. `git-ops`) is delegated to → its
   projected `customTools` excludes `delegate` → it cannot re-delegate
   (deny-by-default preserved through the pass-through). Test (AC-12).
6. **Nested `delegate` past the cap** via real child re-invocation → refused
   (AC-13); counter restored (AC-14, extends S1 AC-8).
7. **Child `session_start` re-seeding hazard** (P4) → seed guards against
   overwriting a non-empty stack (AC-15).
8. **`customTools` definition shape** — passing bare name strings where the SDK
   wants tool definitions would `tsc`-fail or runtime-fail; Link validates the
   shape (see §pass-through wiring detail).

### S2/S3 re-scoping note (D-A convergence — REQUIRED explicit statement)

**Part of S3's converged scope is deliberately pulled forward into S2, per
operator convergence on D-A.** Specifically:

- **Pulled into S2:** the `customTools` pass-through mechanism (making a child
  role's declared `delegate` capability actually reachable) AND its end-to-end
  depth-cap proof under real nested re-invocation.
- **Retained by S3** (per build-order S3 definition, read with this pull-forward
  in mind): the broader "real orchestrator→subagent delegation model," the
  in-process (`createAgentSession`) vs process-isolated (`runRpcMode`) isolation
  question (Open-Q1, [ASSUMPTION-2]), the child-inherits-enforcement guarantee
  as a *model* (S1 answered the *wiring* mechanism; S3 owns it as the delegation
  contract), and argument-level enforcement of per-arg bounds (see §per-arg).
- **Why this is not scope creep:** it is an operator-converged divergence (D-A =
  A1), recorded as a deliberate widening with the Reversibility-Filter/
  Scope-Creep cautions weighed-and-overridden (brief §D-A Operator convergence).
  This plan names it as a distinct design element (the two sub-bullets above are
  tracked as their own Assemble steps 6–7 and AC-11..AC-14), so it is neither
  silently woven into the table work nor mistaken for the whole S3 step.

---

## Link (validate before building)

The implementing agent MUST confirm these against reality (via
`bin/gleipnir-sandbox lint --profile pi` / in-container introspection) **before**
writing implementation, since a wrong shape wastes the delegation:

1. **`customTools` argument shape** on `createAgentSession` — confirm it takes
   tool **definitions** (from `defineTool`/registered tools), not bare strings,
   and determine the exact definition object the `delegate` tool must present so
   it can be passed into a child and re-invoked there (the recursion at the heart
   of AC-13). Source: the shipped `.d.ts` for `createAgentSession` +
   `defineTool` (build-order primitive table cites `docs/sdk.md`,
   `dynamic-tools.ts`).
2. **`session_start` event** exists and its handler signature (`pi.on(
   "session_start", …)`), and that it fires for the top-level session — for the
   P4 orchestrator seed. Source: build-order primitive table (session lifecycle
   row) + the real `.d.ts`.
3. **`AgentSession.prototype.prompt` monkey-patch technique still valid** for
   AC-13 (it was validated in S1 AC-9-E2E; confirm the SDK version is unchanged
   and `_extensionRunner.emitToolCall` still dispatches as S1 found).
4. **`Object.freeze` nested-object semantics** — the typed partition is a nested
   object (`{ baseTools, customTools, brokerTools }`) per role; confirm the
   freeze covers the nested arrays/sets so the table cannot be mutated at runtime
   (S1 froze a `Set`; the partition needs the nested structures frozen too — a
   deep-freeze helper or `Object.freeze` on each partition array). This is a
   correctness detail for the "frozen table" property.
5. **`tsc` acceptance of the typed partition** — the `RoleName`-keyed record now
   maps to a `RoleAllowSet` interface; confirm the SDK's `ToolName` type can be
   imported and used to type `baseTools` (fidelity to F2's verified union) so a
   typo like `read_file` becomes a compile error, not a silent string.

Everything else (the `canUse` deny-by-default semantics, `resolveChildTools`,
`depth.ts`, `activeRole` stack, the enforcement hook logic) is S1-proven and
reused unchanged — no re-validation needed beyond the vocabulary rename.

---

## Assemble (DELTA build order — against the CURRENT working tree, not S1)

**D2 re-baseline: this is a DELTA on a mostly-built tree.** The prior
interrupted session already built the 8-role typed table, the pass-through, the
seed, `.pi/settings.json`, the `pi` manifest key, and most tests (see the
current-state baseline in Trace §customTools pass-through). The steps below
describe the DELTA between current-actual-state and target-state, **not** a
build-from-S1. Steps that are already done on disk are marked **[likely
already-built — VERIFY, don't re-create]**; the real net-new work is fixing D1's
omission, the D1 test ripple, and confirming green.

**Test-first, stub-before-tests (L-C30 collection-time discipline) still holds
for any genuinely-new export.**

- **Step −1 (MANDATORY FIRST ACT — do this before treating ANY step below as
  satisfied).** Run `bin/gleipnir-sandbox test --profile pi` and
  `bin/gleipnir-sandbox lint --profile pi` and **report the actual current
  pass/fail state** before editing anything. **Rationale:** the working tree is
  ahead of the S1 README but the existing (unchanged) `test/delegate.test.ts`/
  `test/enforcement.test.ts` reference S2 vocabulary AND some may still carry
  stale assumptions from the interrupted session; the suite is **very likely RED
  right now** (e.g. any lingering assertion that treats `ROLE_ALLOW_SETS[role]`
  as a flat iterable — `assert.deepEqual(new Set(tools), new Set(ROLE_ALLOW_SETS[
  "gleipnir-code"]))` — throws `TypeError: … is not iterable` against the
  object-shaped `{baseTools,customTools,brokerTools,bounds}` data). **Do not
  assume any test is green; measure it.** This anchors every subsequent "delta"
  claim to a real red/green baseline instead of the stale README.
- **Step 0 (stub-before-tests — only for genuinely-new exports).** Verify every
  export the test files import already exists (most do). If any test you add
  references a not-yet-built export, add its signature stub first so collection
  resolves. **General rule:** any test referencing a not-yet-built export fails
  at collection time.
1. **Fix the D1 `baseTools` omission in `roleTable.ts` [NET-NEW — the core
   fix].** The table is already the 8-role typed partition; the DELTA is: add
   `edit` to `gleipnir-brainstorm.baseTools` and `gleipnir-plan.baseTools`
   (→ `["read","edit"]`); add `bash` to `gleipnir-code.baseTools`
   (→ `["read","edit","bash"]`), `quality-reviewer.baseTools`
   (→ `["read","bash"]`), and `git-ops.baseTools` (→ `["read","bash"]`). Leave
   the `bounds` field on each unchanged (it already carries the fine-grained
   path/arg restriction as metadata — that is exactly the coarse-presence +
   documented-bound treatment the plan requires). Do NOT touch
   `orchestrator`/`project-mgr`/`notify` `baseTools` (their `edit`/`bash` are
   genuinely denied). Vocabulary/freeze/`canUse` are **[likely already-built —
   VERIFY]**.
2. **`roleTable.test.ts` [likely already-built — VERIFY + extend for D1].** The
   file already exists with AC-16/17/18/19. The DELTA: after step 1, add/confirm
   a positive assertion that the newly-present `baseTools` members ARE allowed —
   e.g. `canUse("gleipnir-brainstorm","edit") === true`,
   `canUse("gleipnir-code","bash") === true`, `canUse("quality-reviewer","bash")
   === true`, `canUse("git-ops","bash") === true` — so the D1 fix is proven by
   test, not just asserted in prose (the existing AC-16 union-positive loop
   already covers this generically; add the named cases for explicitness and to
   pin the D1 fix). Confirm AC-18's negative check (no `read_file`/`write_file`/
   `powershell`) still passes.
3. **Fix the D1 test ripple in `enforcement.test.ts` + `delegate.test.ts`
   [NET-NEW — direct consequence of step 1].** The existing "AC-16 (hook)" test
   in `enforcement.test.ts` uses `const universallyDenied = "bash"` — now FALSE
   for three roles. Switch the universal deny probe to a name absent from every
   role's union (e.g. `"totally_unregistered_tool_xyz"`, matching
   `roleTable.test.ts`'s `UNIVERSALLY_DENIED`). Audit every AC that asserts
   `gleipnir-code` (or reviewer/git-ops) DENIES `bash`
   (`enforcement.test.ts` AC-1/AC-4; `delegate.test.ts` AC-9/AC-9-E2E "bash is
   deliberately absent") and switch those negative cases to a tool STILL denied
   for that role (e.g. `write` for `gleipnir-code`, or the unregistered probe).
   Also sweep for any remaining flat-iterable assumption surfaced by step −1
   (`new Set(ROLE_ALLOW_SETS[role])` → must destructure the partitions) and any
   surviving `read_file`/`write_file` string. Do NOT weaken a test to green it:
   these edits correct assertions to match the (now-correct) capability truth,
   they do not relax coverage.
4. **`resolveChildCustomTools` + pass-through in `delegate.ts` [likely
   already-built — VERIFY].** The projection + `customTools: childCustomTools`
   pass-through already exists. DELTA: confirm it is unaffected by the D1
   `baseTools` change (it projects `customTools`, not `baseTools`, so it should
   be) and that `resolveChildTools` (which DOES read `baseTools`) now returns the
   added `edit`/`bash` for the affected roles — check no test pinned the old
   base-only tool list for a delegate-role child.
5. **Pass-through tests in `delegate.test.ts` (AC-11, AC-12) [likely
   already-built — VERIFY].** AC-11/AC-12/AC-12b already exist. DELTA: confirm
   they still pass post-D1 (they assert on `customTools`, which D1 does not
   change).
6. **E2E depth-cap under real nested re-invocation (AC-13, AC-14) [likely
   already-built — VERIFY].** Already present. DELTA: confirm green post-D1
   (drives `role: "gleipnir-code"`; D1 adds `bash`/`edit` to its `baseTools` but
   the nested-refusal assertion keys on the depth cap + graceful message, not on
   `bash` being denied — verify no incidental dependency).
7. **P4 `session_start` orchestrator seed + test (AC-15) [already-built —
   VERIFY].** `seedActiveRoleIfEmpty` + the `session_start` handler + AC-15 all
   exist. DELTA: confirm AC-15 green post-D1 (it is orthogonal to `bash`/`edit`).
8. **Finalise the manifest (D-E) [likely already-built — VERIFY].**
   `package.json` `pi.extensions` (`./src/enforcement.ts` + `./src/delegate.ts`)
   and `.pi/settings.json` already exist. DELTA: confirm `pi.extensions` still
   resolves the 8-role table via imports (no new extension module needed —
   `roleTable.ts` is imported, not an entrypoint); confirm the `description` is
   off the S1-only wording (it already is); confirm `.pi/settings.json` is valid
   JSON wiring the enforcement extension + trust posture (minimal-but-complete;
   NO per-role E-iii, NO skills/prompts/themes E-iv). If all present and correct,
   this step is a no-op beyond verification.
9. **Update `README.md`.** Supersede "Known limitations for S2" (limitation #1
   resolved by the pass-through; limitation #2 resolved by the D-B vocabulary
   fix); extend the AC table with AC-11..AC-21 (continue S1's numbering; AC-10
   was the last S1 AC). Note the D1 correction (coarse `edit`/`bash` presence
   with documented bounds) so the README's capability description matches the
   corrected table.
10. **Verify (FINAL — the arbiter).** `bin/gleipnir-sandbox lint --profile pi`
    (tsc clean) and `bin/gleipnir-sandbox test --profile pi` (all green, report
    pass count + coverage%). Compare against the step −1 baseline: report which
    tests went red→green as a result of the D1 fix + ripple corrections.

---

## Stress-test (acceptance checks — AC→test mapping, continuing S1's numbering from AC-10)

**Extends, does not replace, the S1 README AC table.** S1 ended at AC-10
(package validity). New S2 ACs start at AC-11.

| AC | Assertion (checkable, not "it works") | Test | File |
|---|---|---|---|
| **AC-11** | `resolveChildCustomTools(role)` returns exactly the role's declared `customTools` for a delegate-role (`orchestrator`, `gleipnir-code` → includes `"delegate"`); DRY-sourced from `ROLE_ALLOW_SETS`, no hand-duplicated list | "AC-11: child custom-tools projected from the table for a delegate-role" | `test/delegate.test.ts` |
| **AC-12** | For a NON-delegate role (`git-ops`, `quality-reviewer`, `notify`, `project-mgr`, brainstorm, plan), `resolveChildCustomTools` excludes `"delegate"` — deny-by-default preserved through the pass-through | "AC-12: a non-delegate child role does not receive delegate (deny-by-default through pass-through)" | `test/delegate.test.ts` |
| **AC-13** | A **real** `createAgentSession` child (built by `delegate.ts`'s real `execute`, `customTools` now carrying the real `delegate` def), driven via the stubbed `prompt`/`emitToolCall` technique to make a **nested** `delegate` call, is refused once `depth === cap` with the graceful `DepthCapExceededError` message — real nested re-invocation, not counter-only | "AC-13: end-to-end nested delegation is refused past the depth cap via a real re-invoked delegate" | `test/delegate.test.ts` |
| **AC-14** | After the AC-13 nested chain (including a refusal), `getDepth()` returns to 0 — the module-scope counter is restored across the real nested path (extends S1 AC-8 to the E2E case) | "AC-14: depth counter restored to 0 after real nested delegation chain" | `test/delegate.test.ts` |
| **AC-15** | `session_start` seeds the active-role stack with `orchestrator` on an empty stack; does NOT overwrite a non-empty stack (child-pushed role survives) | "AC-15: session_start seeds orchestrator without clobbering a pushed child role" | `test/delegate.test.ts` (or a new `test/activeRole.test.ts`) |
| **AC-16** | Deny-by-default proven **per role** (all 8): aggregate loop asserts every tool absent from a role's union allow-set → `canUse` false; representative denied tool blocks through the real hook per role | "AC-16: deny-by-default holds for every one of the 8 roles" | `test/roleTable.test.ts` |
| **AC-17** | **G-2 at the table level:** exactly one role (`git-ops`) has a non-empty `brokerTools`; every other role's `brokerTools` is empty; `canUse("git-ops", <inert git-broker name>)` is `true` and `canUse(<any other role>, <inert git-broker name>)` is `false` | "AC-17: git-ops is the sole broker (git) holder; inert name granted only to it" | `test/roleTable.test.ts` |
| **AC-18** | Vocabulary fidelity: no `read_file`/`write_file`/`powershell` appears in `roleTable.ts`; `baseTools` values are all within the SDK `ToolName` union (`tsc` enforces via the `ToolName` type; a runtime test asserts each base name ∈ the SDK's `allToolNames`/union) | "AC-18: base-tool vocabulary matches the real SDK ToolName union" | `test/roleTable.test.ts` |
| **AC-19** | Table is frozen (deep): mutating a role's `baseTools`/`customTools`/`brokerTools` at runtime throws / is a no-op (the enforcement table cannot be widened at runtime — the C3-integrity property in code form) | "AC-19: the 8-role table (incl. nested partitions) is frozen" | `test/roleTable.test.ts` |
| **AC-20** | Manifest validity: `package.json` `pi.extensions` resolves; no pi peer under `dependencies`; `.pi/settings.json` is valid JSON wiring the enforcement extension + declaring trust posture (minimal-but-complete; no per-role/skills/prompts entries) | manual + a JSON-parse assertion | `package.json`, `.pi/settings.json` |
| **AC-21** | **D1 coarse-presence fix (present-but-scoped capabilities are in `baseTools`, not dropped):** `canUse("gleipnir-brainstorm","edit")` and `canUse("gleipnir-plan","edit")` are `true` (edit present, `.gleipnir/plans/**`-scoped in `bounds`); `canUse("gleipnir-code","bash")`, `canUse("quality-reviewer","bash")`, `canUse("git-ops","bash")` are all `true` (bash present, arg-allowlisted in `bounds`); AND the genuinely-denied cases stay `false`: `canUse("orchestrator","edit")`, `canUse("orchestrator","bash")`, `canUse("project-mgr","bash")`, `canUse("notify","bash")`. Each affected role's `bounds` field is non-empty (the fine-grained restriction is recorded as metadata, not silently dropped) | "AC-21: present-but-scoped capabilities appear in baseTools with their bound recorded; genuinely-denied ones stay absent" | `test/roleTable.test.ts` |

> **Key new rows for the orchestrator report:** AC-11/AC-12 (pass-through +
> deny-by-default through it), AC-13/AC-14 (real nested depth-cap E2E — the D-A
> deliverable), AC-16 (per-role deny-by-default — the exit criterion core),
> AC-17 (G-2 sole-git-holder + inert broker name — the exit criterion's G-2
> clause), AC-18 (vocabulary fidelity — D-B), **AC-21 (the D1 coarse-presence
> fix — present-but-scoped `edit`/`bash` in `baseTools` with bounds recorded;
> genuinely-denied capabilities stay absent).**

**Full acceptance = exit criterion satisfied:** AC-16 (every role expressed +
deny-by-default) + AC-17 (G-2) + AC-11..AC-14 (D-A: nested delegation reachable
+ depth-cap E2E) + AC-21 (D1 coarse-presence correction) + lint/test green
(AC-20 + step 10).

---

## Execution Workflow (for the implementing `gleipnir-code` agent)

1. **FIRST ACT — measure the current suite (Assemble step −1), THEN Link.**
   Before editing OR treating any Assemble step as satisfied, run
   `bin/gleipnir-sandbox test --profile pi` AND `bin/gleipnir-sandbox lint
   --profile pi` and **report the actual current pass/fail state**. The working
   tree is ahead of the S1 README (a prior interrupted session built most of S2
   on disk, operator-confirmed) and the suite is **very likely RED** right now
   (stale assertions, e.g. a flat-iterable `new Set(ROLE_ALLOW_SETS["gleipnir-
   code"])` throwing `TypeError` against the object-shaped data). Do NOT assume
   any test is green. Only after this baseline, confirm the five Link items
   (especially the `customTools` definition shape and `session_start` signature)
   via lint / an in-container introspection probe. Do NOT write implementation
   against an assumed shape OR an assumed-green baseline.
2. **Follow Assemble −1→10 in order — as a DELTA, not a build-from-S1.** Most
   src/test/manifest artifacts already exist on disk; VERIFY the "[likely
   already-built]" steps rather than re-creating them, and focus net-new effort
   on: the D1 `baseTools` fix (step 1), the D1 test ripple (step 3, esp. the
   `"bash"` universal-deny probe that D1 invalidates), and reaching green. Write
   any genuinely-new assertion red before it passes; do not weaken a test to
   green it (per `gleipnir-code` discipline) — the step-3 edits CORRECT
   assertions to match the now-correct capability truth, they do not relax
   coverage.
3. **The test is the arbiter (Axiom 1).** All ACs are `node --test` cases except
   the manual manifest check (AC-20's peer-vs-dependencies inspection). Report
   pass count + line/branch coverage% from `bin/gleipnir-sandbox test --profile
   pi`; aim ≥85%, justify below.
4. **Stay inside the boundary.** `P` is `pi-package/**` only. Do NOT touch
   `.gleipnir/**` (you cannot — capability-denied), do NOT touch
   `stage-role-map.md`/`AGENTS.md` (D-D: separate follow-up), do NOT build
   argument-level enforcement (§per-arg: out of S2 scope — if it seems needed,
   STOP and report, do not expand scope).
5. **Escalate, do not decide.** If Link reveals the `customTools` shape makes the
   `delegate`-passes-`delegate` recursion infeasible in-process (e.g. requires
   RPC), that is Open-Q1/S3 territory — STOP and report to the orchestrator for
   operator convergence; do NOT silently switch to `runRpcMode` (a material
   isolation decision the brief did not converge).
6. **Report** (never end on a tool call): files changed, verification (pass
   count + coverage%), which ACs pass, and any Link finding that changed the
   plan's assumptions.

**Handback:** on green, report to the orchestrator, which routes `quality`
(blast-radius: is any allow-set wrongly widened? does the applied table honour
the Design Intent below? SOLID/DRY dimension) then `git` to `git-ops`.

---

## Design Principles (Gate 1 — case (i): OOP/functional code, full SOLID+DRY+SRP+Design Intent)

**Routing:** `P ∩ X ≠ ∅` (executable TS, treated as `X`-equivalent per the
routing statement) AND the touched members (`roleTable.ts`, `delegate.ts`,
`activeRole.ts`) have module/function structure → **case (i): all three
sub-analyses required, each falsifiable.**

### SOLID analysis (against the proposed design)

- **Single Responsibility** — `roleTable.ts` remains *capability DATA + the
  `canUse` lookup, nothing else* (S1's stated SRP, preserved); the typed
  partition adds *structure to the data*, not a second responsibility.
  `delegate.ts` remains *construct + bound + run a child session*; the new
  `resolveChildCustomTools` is the same responsibility as the existing
  `resolveChildTools` (projecting the table into a child-session argument), not
  a new one. `activeRole.ts` remains the *current-role state model*; the P4 seed
  is a caller wiring the state, not new state logic. **Falsifiable:** if
  `delegate.ts` starts *deciding* which roles may delegate (rather than
  projecting the table's declaration), that is a second responsibility and a
  violation — flag it.
- **Open/Closed** — S1's load-bearing property: adding roles/tools extends
  `ROLE_ALLOW_SETS` **data** without modifying `enforcement.ts`'s hook logic.
  S2 exercises exactly this (8 roles added as data; the hook is untouched).
  **Falsifiable:** if promoting to 8 roles requires editing `enforcement.ts`'s
  decision logic (not just vocabulary), Open/Closed is violated — flag it.
  (The vocabulary rename touches strings the hook compares, not its control
  flow; the hook still only calls `canUse(role, event.toolName)`.)
- **Liskov Substitution** — every role's allow-set is the SAME `RoleAllowSet`
  shape (three partitions); `canUse` treats all roles uniformly (no role is a
  special subtype with different lookup rules). **Falsifiable:** if `git-ops` (or
  any role) needs a bespoke `canUse` branch rather than uniform partition
  membership, the uniform contract is broken — flag it. (Edge case 4's inert
  broker name is handled by the *same* union-membership rule, not a git-ops
  special case — this is deliberate to preserve LSP.)
- **Interface Segregation** — `enforcement.ts` depends only on the narrow
  `canUse(role, tool): boolean` (S1 Dependency Inversion), not on the table's
  internal `RoleAllowSet` structure; the typed partition is an implementation
  detail behind `canUse`. **Falsifiable:** if `enforcement.ts` starts importing
  `RoleAllowSet`/reaching into partitions directly, the narrow interface is
  breached — flag it.
- **Dependency Inversion** — high-level modules (`enforcement.ts`,
  `delegate.ts`) depend on the abstractions `canUse`/`resolveChild*`, not on the
  concrete table storage. **Falsifiable:** the same as ISE — a direct reach past
  `canUse`/`resolveChild*` into `ROLE_ALLOW_SETS` internals from the hook is a
  violation.

### DRY analysis

- The allow-set is defined **once** in `ROLE_ALLOW_SETS`; `resolveChildTools`
  (existing) and `resolveChildCustomTools` (new) are the ONLY projections of it
  into pi's `tools`/`customTools` shapes — no hand-duplicated pass-through list
  (P3). **Falsifiable:** a literal `["delegate"]` written directly in the
  `createAgentSession` call (instead of `resolveChildCustomTools(role)`) is a DRY
  violation duplicating table data — flag it.
- The inert-broker-name string and the base `ToolName` union are referenced from
  their single sources (the table entry; the SDK's `ToolName` type / `allToolNames`),
  not re-typed as bare string literals scattered across tests. **Falsifiable:** a
  test hard-coding `"gleipnir-git_commit"` in three places instead of referencing
  one constant duplicates a config value.
- The 8 role names appear once as the `ROLE_ALLOW_SETS` keys; the aggregate
  deny-by-default loop iterates `Object.keys(ROLE_ALLOW_SETS)` rather than a
  re-listed role array. **Falsifiable:** a second hand-maintained role-name list
  in the test is a DRY/drift hazard (C2's drift risk in miniature).

### Single Responsibility check (per new/changed component)

- `RoleAllowSet` (new type) — *the shape of one role's capability declaration.*
- `resolveChildCustomTools(role)` (new fn) — *project a role's declared
  `customTools` into the child-session `customTools` argument.* One reason to
  change: the child-`customTools` projection rule.
- `roleTable.ts` (changed) — *capability data + `canUse` lookup* (unchanged
  responsibility; more data).
- `delegate.ts` (changed) — *construct/bound/run a child* (unchanged; the
  pass-through is part of "bound").
- `session_start` seed handler (new wiring) — *seed the top-level active role.*
  One reason to change: how the primary session's role is established.

### Design Intent (specific, falsifiable — the load-bearing genuineness proxy)

**Design Intent:** *The 8-role table must be the single, type-checked,
runtime-frozen source of every role's capability, such that (a) deny-by-default
is a property of `canUse` for every role and every unlisted tool (no
implicit-allow path, no per-role special-case), (b) `git-ops` is the unique
holder of a git-broker name and no other role's `brokerTools` is non-empty, and
(c) a child session receives the `delegate` capability if and only if its role's
table entry declares it — the pass-through PROJECTS the table's declaration and
never widens it.*

**How a reviewer can falsify it** (concrete implementation choices that violate
it): (a) any code path where an unlisted tool resolves to allowed for some role,
or a role gets a bespoke `canUse` branch that bypasses union membership; (b) a
second role with a non-empty `brokerTools`, or the pm namespace leaking into
`brokerTools` such that the G-2 assertion must be weakened (see the P2 reversal
note — this is the specific over-broad form the `quality` blast-radius pass must
rule out); (c) `delegate.ts` passing `delegate` to a child whose role does not
declare it (a widened pass-through), or hand-duplicating the pass-through list
instead of projecting `resolveChildCustomTools` (DRY); (d) the table (or a
nested partition) being mutable at runtime (AC-19 falsifies); (e) building
argument-level enforcement inside S2 (scope beyond the converged brief — §per-arg
flags this as escalate-not-build).

This Design Intent is NOT a generic aspiration ("clean table", "correct
enforcement"): it names three concrete, checkable invariants (deny-by-default
per role; git-broker sole-holder; project-don't-widen pass-through) each tied to
a specific AC (AC-16, AC-17, AC-11/AC-12) and a specific violation a reviewer can
point at.

---

## Open Items (for spec-review / operator attention BEFORE code begins)

1. **Argument-level (per-arg/per-path) enforcement is treated as OUT of S2
   scope, captured-as-metadata (§per-arg / Trace edge case 3).** The six
   converged decisions do not include building it; the exit criterion is
   tool-presence-level. This plan flags it rather than deciding to build it. **If
   the operator intends argument-level enforcement inside S2, that is a material
   scope expansion that must go back to the brainstorm gate** — the plan does not
   assume it. (Highest-value item to confirm.)
2. **Residual live-model-turn empirical gap (inherited from S1, unchanged).** The
   AC-13 E2E proof closes wiring + counter-under-real-nesting, but a fully
   model-driven live turn cannot run under `--network=none` with no provider
   auth. This is a network/auth limit, not a wiring-correctness one; named so the
   `quality` reviewer and operator do not read AC-13 as proving more than it
   does.
3. **P2 broker-partition modelling choice (pm in `customTools` vs `brokerTools`).**
   The plan places only the git broker in `brokerTools` and pm in
   `project-mgr.customTools`, to make the G-2 assertion a clean "exactly one
   non-empty `brokerTools`." **Spec-review should ratify this** (or choose the
   alternative: pm also in `brokerTools`, G-2 assertion phrased as
   "only-git-in-brokerTools"). Both preserve G-2 + deny-by-default; only the
   phrasing/partition differs. This is the one modelling decision worth an
   explicit reviewer nod.
4. **P4 `session_start` seed interaction with child sessions.** If a child
   `createAgentSession` fires its own `session_start`, the seed must not re-seed
   `orchestrator` over a pushed child role (AC-15 covers it, but Link must
   confirm the child-session `session_start` behaviour empirically — S1 could not
   exercise a live child session start under `--network=none`, so this may be a
   second named empirical gap if the introspection cannot reach it).

None of these re-open a converged decision; items 1 and 3 need a spec-review/
operator nod, items 2 and 4 are named empirical limits the reviewer must not
mistake for defects.
