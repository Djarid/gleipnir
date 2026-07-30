# Plan: Operator-Configurable Context-Length Cap for the Orchestrator

> **Stage:** `plan` (gleipnir-plan). **Input:** the CONVERGED brief
> `interactive-session-context-cap-brainstorm.md` (operator-converged via the
> orchestrator). This plan does **not** re-decide the four material tradeoffs;
> they are fixed inputs (WHERE / ENFORCEMENT / SCOPE / AT-CAP). It plans the
> *bounded* work those decisions define and sequences the operator-required
> spike as an explicit first gate.
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0). This file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it — the orchestrator
> sequences that; nothing here is executed now.

---

## Decisions (index)

Summary of every decision this plan fixes, in order encountered; full reasoning
for each is in the sections below.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | WHERE the cap lives | Tier-3 policy file under `.gleipnir/` (e.g. `policy/context-cap.jsonc`) with an explicit **"unset = no cap = model default"** comment; "unset" is a first-class documented state | Top-level `opencode.jsonc` as the source of truth; per-agent frontmatter field | A context-cap is a policy knob → correct trust tier is Tier-3 (operator-only, G-1); AgentConfig has no context field. Inherited from brief D1·Opt2 (weighted matrix 304 vs 197 vs 153) |
| 2 | ENFORCEMENT mechanism | `provider.models.<capped-id>.limit.context = 250000` in `opencode.jsonc` + orchestrator `model:` repointed to the capped id; **SPIKE-FIRST** to verify non-leakage before arming | Plugin-enforced per-agent cap (reserved as Approach B, not adopted); native `compaction` tuning only (no true cap) | Real, native, non-experimental key opencode's context machinery already reads; graceful compaction, no hard failure. Inherited from brief D2·HypA |
| 3 | SCOPE | **Orchestrator ONLY** — not `/plan`, not `/build`, not any other agent (all others uncapped locally) | Capping all interactive agents / `/plan` / `/build`; per-subagent budgets; G-4d ledger | Capping only the framework's Tier-3 orchestrator stays wholly inside framework config; the `/plan` + `/build` "escape-hatch" concern is **explicitly retired** since the feature never touches them. Inherited from brief (operator, MATERIAL) |
| 4 | Behaviour AT the cap | Native compaction **+ an AETOS-style `compaction-survival` plugin ported to `.gleipnir/` paths**, re-injecting pinned `compaction_survival` rules under "## Critical Guardrails (preserved across compaction)"; `chat.params` swallow hook hides the custom key | **Hard truncation; fail-closed/refusal**; unguided native compaction alone | Modelled on the real shipped AETOS mechanism (`../aetos/.aetos/plugins/compaction-survival.ts`, `../aetos/opencode.json`, `../aetos/.opencode/agents/aetos.md`): bound tokens AND guarantee the orchestrator's critical rules survive; never silently drop context or block the human. Inherited from brief D3 |
| 5 | Tier-3 authorship split (Trace consequence) | Every write in this feature lands in a Tier-3 path → **no bounded `gleipnir-code` write task**; the only code-agent unit is authoring the plugin source as a reviewable draft outside Tier-3, which the operator places | Treating placement of the plugin / policy file / config as a bounded code-agent task | A bounded agent cannot write `.gleipnir/plugins/`, `.gleipnir/policy/`, `.gleipnir/agents/`, `.gleipnir/decisions/`, or `opencode.jsonc`; all placements are Tier-3 operator actions (tier-integrity, S10) |
| 6 | Tier-3 value-file format | Deferred to Link as a mechanical pick (`.jsonc` fragment vs small policy `.md`) — choose whichever best carries the "unset = no cap" comment and is easiest for the wiring to read | Fixing the format in the plan as if it were material | Mechanical, not a material value-choice; does not affect the converged design |
| 7 | Plugin registration (factual correction) | Rely on opencode **auto-discovery** of `.gleipnir/plugins/*.ts` (evidence: `sequence-gate.ts` already loads this way; no `plugin:` array); the dir already exists — no creation needed | The brief's "add a `plugin:` array to `opencode.jsonc`" + "create `.gleipnir/plugins/` (does not exist)" rows | Corrects mechanical drift in the brief; dropping the file in registers it, so the registration step is dropped (Link L1) |
| 8 | Capped-id declaration form + non-leakage (the spike) & reserved escalation | Establish the capped-id declaration form for this aperture env and prove the cap scopes to the orchestrator only (L0/S0, blocking gate); reserve **Approach-B scoped plugin** as the conditional escalation **only on spike FAIL** | Inventing a new declaration decision here; silently adopting Approach B without operator convergence | The declaration form is a known-unknown resolved by evidence, not an operator value-choice; on FAIL the enforcement change IS operator-facing and must be surfaced, not decided here. **Spike PASSED → Approach B was not needed** |
| 9 | Build ordering (preservation before cap) | Arm the `compaction_survival` preservation plugin + pin the orchestrator's rules (Step 3) **before** arming the cap (Step 4), after the blocking spike (Step 1) | Arming the cap before preservation is in place | So the first at-cap compaction already preserves the orchestrator's critical rules; the spike gates all irreversible wiring |
| 10 | Honesty label (cooperative-policy-until-S2) | Carry the "authored, enforced-at-hook, **not yet closed until S-2/G-1**" label in the decision record; the cap + plugin are cooperative policy, agent-unwritable only after S-2 closure | Presenting the cap/plugin as an unbreakable guard today | Matches the framework's honesty posture; `plugins/**` is in the Tier-3 enforcement path set but OS-ro only after S-2 boundary + G-1 preflight land |
| 11 | Experimental-hook version coupling (acknowledged risk) | Record the validated opencode version in the decision record and treat any opencode upgrade as a re-validation trigger (edge case 6 / S6, S9) | Depending on `experimental.session.compacting` + `chat.params` silently as if stable | These hooks "may change without notice" — the same version-coupling risk AETOS already lives with; making it explicit bounds the risk |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`goals/manifest.md`):** "Plan format" (`plan-format.md`) and
  "Methodology (ATLAS/GOTCHA ahead of planning)" apply. This plan follows the
  required Architect / Trace / Link / Assemble / Stress-test / Execution
  Workflow structure. No pipeline-sequencing goal is authored or implied
  (G-5 rule respected — sequencing stays with the orchestrator/engine).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or git are produced here.
- **Layer placement (GOTCHA Amendment 1, layer-2 → G-5):** the cap is a
  **Goals/Context** concern (a policy knob + preserved-context behaviour), not
  an orchestration-sequencing concern. It does not touch the G-5 pipeline
  ordering. The at-cap plugin is **Tools-layer enforcement code** (like
  `sequence-gate.ts`), so it inherits the Tier-3 "authored, not yet closed"
  honesty posture.
- **Gaps named:**
  1. **Factual drift in the brief (mechanical, NOT material):** the brief states
     `.gleipnir/plugins/ does not exist yet` (lines 68, 436). It **does** exist
     and already contains `sequence-gate.ts` (a Tier-3 enforcement plugin). The
     plan corrects this: the directory need not be created; the new plugin is
     *added* alongside the existing one. `plugins/**` is confirmed in the Tier-3
     enforcement path set (`decisions/s2-g1-closure.md` line 50, "tolerate-absent").
  2. **Plugin registration mechanism (mechanical):** AETOS uses **no explicit
     `plugin:` array** in `opencode.json` — opencode auto-discovers plugins in
     the config dir's `plugins/`. The existing `sequence-gate.ts` is likewise
     auto-discovered (`opencode.jsonc` has no `plugin:` array). So the brief's
     "Plugin registration → `opencode.jsonc` `plugin:` array" row (line 436) is
     **not required**; dropping the file into `.gleipnir/plugins/` registers it.
     The spike must confirm this holds for this environment.
  3. **Model-id declaration is unknown for this environment (feeds the spike):**
     the current orchestrator `model:` is a bare id
     `aperture-anthropic/anthropic.claude-opus-4-8` — there is **no**
     `provider.models.<id>` block in `opencode.jsonc` (unlike AETOS's explicit
     `litellm` provider with `limit.context`). How a *capped* model id is
     declared against an aperture-served model is exactly what the spike must
     establish. This is a **known unknown**, not a new material tradeoff — the
     converged enforcement mechanism (`limit.context` override) is fixed; only
     its concrete wiring in this environment is unverified.

**New material tradeoff found?** **No.** Everything above is mechanical wiring
or factual correction. The four converged decisions stand unchanged. One item
(gap 3) is a hard technical uncertainty that the operator already anticipated
by mandating the spike-first gate — it is resolved by evidence, not by an
operator value-choice. If the spike returns the leakage result (see
Stress-test S0), the plan routes to the reserved escalation path rather than
inventing a new decision. **See the "Escalation / conditional decision" note in
Assemble Step 1 — that branch, if hit, IS an operator-facing decision and must
be surfaced, not decided here.**

---

## 1. Architect

**Problem (one sentence):** Bound the framework `orchestrator` agent's
interactive context window to an operator-set cap (default 250K tokens, unset =
no cap = model default) enforced by opencode's native `limit.context`
machinery, with AETOS-style `compaction_survival` re-injection preserving the
orchestrator's critical rules at the cap — and touching no other agent.

**User:** the framework **operator**, who wants quality-efficient outcomes per
token and a policy knob that agents cannot silently change (G-1 posture).

**Measurable success criteria:**

1. The `orchestrator`'s effective context window is the capped value (default
   250 000 tokens), verified by the substrate reading `limit.context` for the
   orchestrator's model id.
2. **No other agent or subagent is capped locally** — `gleipnir-plan`,
   `gleipnir-code`, `quality-reviewer`, `git-ops`, etc. retain their base
   model's context window (remote provider limits still apply naturally).
   *(This is the spike's pass condition.)*
3. **Unset is a first-class, documented state:** with the cap value
   removed/commented in the Tier-3 policy file (and the override backed out of
   `opencode.jsonc`), the orchestrator falls back to its model's default context
   limit. The policy file carries an explicit comment saying so.
4. **Configurable:** the cap is an arbitrary number the operator edits in one
   place (the Tier-3 policy file), with a documented one-line propagation to the
   `opencode.jsonc` override (single source of truth by convention + comment).
5. **At the cap:** native compaction runs and the orchestrator's pinned
   `compaction_survival` entries survive it (re-injected under
   "## Critical Guardrails (preserved across compaction)"). **No hard
   truncation, no fail-closed.**
6. The custom `compaction_survival` frontmatter key never reaches the model
   (swallowed by the `chat.params` hook).

**Constraints (from the brief — FIXED, not re-litigated):**

- **WHERE:** Tier-3 policy file under `.gleipnir/` holds the cap value, with the
  explicit "unset = no cap = model default" comment. Unset is first-class.
- **ENFORCEMENT:** `provider.models.<capped-id>.limit.context = 250000` in
  `opencode.jsonc`; orchestrator's `model:` points at the capped id. **Spike
  first** — a capped id assigned to the orchestrator must NOT leak the cap to
  subagents (they stay uncapped locally).
- **SCOPE:** **orchestrator ONLY.** Not `/plan`, not `/build`, not any other
  agent. (Escape-hatch concern retired — feature stays inside framework config.)
- **AT-CAP:** native compaction + ported AETOS `compaction-survival` plugin on
  `experimental.session.compacting` (+ `chat.params` swallow hook). No
  truncation, no fail-closed.
- **Trust tiers:** the Tier-3 policy file, `opencode.jsonc`, and
  `orchestrator.md` are **operator-authority (Tier-3)** — a bounded code agent
  MUST NOT write them. The plugin under `.gleipnir/plugins/**` is Tier-3
  enforcement-bearing code — **authored, enforced-at-hook, not yet closed**
  until S-2/G-1 land.
- **Experimental-hook coupling:** `experimental.session.compacting` and
  `chat.params` are experimental opencode hooks ("may change without notice") —
  a documented version-coupling risk, the same one AETOS already lives with.

---

## 2. Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Source-of-truth role |
|---|---|---|---|---|
| Cap **value** (policy knob + "unset=no-cap" comment) | new: `.gleipnir/policy/context-cap.jsonc` *(format TBD in Link — jsonc vs md)* | **Tier-3 POLICY** | **operator only** | The canonical cap number the operator edits. Present-and-numeric ⇒ cap applies; absent/commented ⇒ model default. |
| Native **enforcement** override | `opencode.jsonc` — `provider.models.<capped-id>.limit.context` | **Tier-3** (repo-root config; operator-authority) | **operator only** | The value opencode's context machinery actually reads. Mirrors the policy value; comment links back to it as the single source of truth. |
| Orchestrator **wiring** | `.gleipnir/agents/orchestrator.md` frontmatter `model:` (repoint to capped id) + new `compaction_survival:` block | **Tier-3 POLICY** | **operator only** | Binds the capped id to the orchestrator and lists the pinned rules. |
| At-cap **preservation** plugin | new: `.gleipnir/plugins/compaction-survival.ts` (port of `../aetos/.aetos/plugins/compaction-survival.ts`, paths adapted) | **Tier-3 enforcement code** | **operator only** (agent-unwritable, like `sequence-gate.ts`) | The hook that re-injects pinned entries on compaction and swallows the custom key. |
| Durable **decision record** | new: `.gleipnir/decisions/context-cap.md` | Tier-3 | **operator only** | The kept record with the honesty label. |

**Critical Trace consequence:** **every** write in this feature lands in a
Tier-3 path. **There is no bounded `gleipnir-code` write task in this feature.**
`gleipnir-code`'s role is limited to *authoring the plugin source as a
draft/proposal* that the operator reviews and places (a code agent cannot write
`.gleipnir/plugins/**`). This is made explicit in the Execution Workflow's
operator-vs-code-agent split.

### Integrations map

- **opencode config loader** reads `.gleipnir/` (via `OPENCODE_CONFIG_DIR`),
  auto-discovering `plugins/*.ts` and merging `opencode.jsonc`. → the capped
  model id must be a valid, loadable id in this environment (spike).
- **opencode context/compaction machinery** reads
  `provider.models.<id>.limit.context` to decide the window and when to compact.
  → enforcement point for the cap.
- **`experimental.session.compacting` hook** fires when opencode compacts; the
  plugin pushes the deduped `compaction_survival` entries into `output.context`.
  → preservation point. **Experimental — version-coupling risk.**
- **`chat.params` hook** fires per outbound model request; the plugin deletes
  the `compaction_survival` key from `output.options` (and defensively the top
  level) so the provider never sees an unknown field. → aperture/Bedrock-style
  strict-schema safety.
- **Existing `sequence-gate.ts`** shares `.gleipnir/plugins/`. The new plugin
  must **coexist** (both auto-discovered, distinct owned concerns; no shared
  state). → no modification to `sequence-gate.ts`.

### Edge cases

1. **Unset / removed value.** Cap key absent or commented in the policy file
   AND the override backed out of `opencode.jsonc` ⇒ orchestrator uses the base
   model's default limit. Must be a clean, documented, first-class state — not
   an error, not an implicit 0 (a 0/empty `limit.context` must never be written
   as "unset"; "unset" means the override line is absent).
2. **Cap value present but override not propagated (drift).** Because the value
   lives in two files by design, they can diverge. Mitigation: the policy file's
   comment names `opencode.jsonc` as the mirror and the decision record documents
   the one-line propagation; the Stress-test verifies they match.
3. **Capped id leaks to subagents (the spike's failure mode).** If assigning the
   capped model id to the orchestrator also caps any agent/subagent sharing the
   base model, success criterion 2 fails ⇒ **escalate to the reserved Approach-B
   scoped plugin** (this is an operator-facing conditional decision — surface it).
4. **`compaction_survival` block malformed** (bad YAML list / wrong indent). The
   AETOS extractor is defensive (`try/catch`, returns `[]`), so a malformed block
   silently yields no preserved entries rather than crashing — but that means
   *silent loss of preservation*. Stress-test must assert the entries actually
   appear, not merely that nothing throws.
5. **`chat.params` swallow misses a key surface.** Some opencode versions surface
   the spread key at the top level, not under `options`. The AETOS plugin already
   deletes both; the port must keep both deletions.
6. **Experimental hook renamed/removed by an opencode upgrade.** Version-coupling
   risk: the hook may change without notice. Mitigation: pin/record the opencode
   version the plugin was validated against in the decision record; treat an
   opencode upgrade as a trigger to re-validate the hook (Stress-test S6).
7. **Path adaptation bug in the port.** AETOS scans `.opencode/agents/*.md`,
   `.opencode/skills/*/SKILL.md`, `.opencode/rules/*.md`, and
   `src/python/aetos/plugins/*.json`. The gleipnir port must scan `.gleipnir/`
   paths and **drop** the AETOS-specific `rules/` and python-manifest scans
   (gleipnir has no `rules/` dir and no such manifests) unless the operator wants
   them — scanning nonexistent dirs is harmless (returns `[]`) but the intent
   should be explicit. Minimal correct scope: `.gleipnir/agents/*.md` and
   `.gleipnir/skills/*/SKILL.md`.

---

## 3. Link — what must be validated BEFORE building

**The spike is the first gate (operator-mandated).** No enforcement wiring is
committed until the spike returns a clean result. Concretely, before any
Assemble step past Step 1:

- **L0 (SPIKE — blocking):** In this environment, determine how a **capped model
  id** is declared and whether assigning it to the orchestrator caps **only** the
  orchestrator. Because there is currently **no `provider.models` block** and the
  model id is a bare aperture id, the spike must first establish the *declaration
  form* (e.g. whether an aperture-served model can carry a
  `provider.models.<id>.limit.context` override at all, or whether a distinct
  capped id must be minted), then prove non-leakage to subagents. **Read-only
  investigation + a throwaway config probe; no committed change.** Output: a
  written spike result appended to this plan or a sibling `-spike.md` note.
- **L1:** Confirm opencode **auto-discovers** `.gleipnir/plugins/*.ts` (evidence:
  `sequence-gate.ts` is already loaded this way; no `plugin:` array exists). If
  auto-discovery is confirmed, no `opencode.jsonc` `plugin:` registration is
  needed.
- **L2:** Confirm the `experimental.session.compacting` and `chat.params` hook
  signatures the AETOS plugin uses are present in this environment's opencode
  plugin API version. Record the version.
- **L3:** Confirm the `compaction_survival` frontmatter format the AETOS
  extractor expects (`  - "…"` list items with `\n` escapes) is what will be
  authored on `orchestrator.md`.

**Gate rule:** L0 must return **PASS (cap scopes to orchestrator only)** before
Assemble Steps 2–5 run. On **FAIL**, stop and surface the reserved-escalation
decision to the operator (do not silently adopt Approach B).

---

## 4. Assemble — intended build order

Ordered so the blocking spike gates all irreversible wiring, and preservation is
in place before the cap is armed (so the first compaction at the cap already
preserves rules).

**Step 0 — Author the plugin source as a reviewable draft.** *(bounded
`gleipnir-code` MAY author the source text; it CANNOT place it in
`.gleipnir/plugins/**` — that is an operator action in Step 4.)* Port
`../aetos/.aetos/plugins/compaction-survival.ts` with paths adapted to
`.gleipnir/` (`findMdFiles(".gleipnir/agents/*.md")`, skills dir
`.gleipnir/skills`), dropping the AETOS `rules/` and python-manifest scans (or
keeping harmless no-op scans, operator's call in Link L3). Keep both hooks
(`experimental.session.compacting` + `chat.params`) and both swallow-deletions.
No behavioural changes from the reference. *Draft only — not enforcing yet.*

**Step 1 — SPIKE (blocking gate, L0).** Run the model-id-scoping spike. This is
the first hard gate. **If FAIL → STOP and surface the escalation decision to the
operator** (Approach-B scoped plugin) — an operator-facing conditional decision,
not one this plan resolves. Steps 2–5 proceed **only on PASS**.

> **Escalation / conditional decision (operator-facing, do NOT decide here):**
> if the spike shows the model-limit override cannot scope to the orchestrator
> alone, the enforcement mechanism must change to the reserved Approach-B plugin.
> That is a material change to the converged ENFORCEMENT decision and belongs at
> the convergence gate, surfaced by the orchestrator to the operator. The plan
> names it; it does not pre-decide it.

**Step 2 — Author the Tier-3 policy value file** (`.gleipnir/policy/context-cap.jsonc`
or chosen form, per Link L-format). Contains the cap number (250000) and the
mandatory **"unset = no cap = model default"** comment. *(operator action.)*

**Step 3 — Place the preservation plugin + pin the orchestrator's rules.**
Operator places the Step-0 draft at `.gleipnir/plugins/compaction-survival.ts`
and adds the `compaction_survival:` block to `.gleipnir/agents/orchestrator.md`
(delegation discipline, convergence-gate rules, session-recovery — modelled on
`aetos.md` lines 33–34, adapted to gleipnir roles/paths). **Preservation is
armed before the cap** so the first at-cap compaction already preserves rules.
*(operator action — both are Tier-3 paths.)*

**Step 4 — Arm the cap (enforcement wiring).** Operator adds
`provider.models.<capped-id>.limit.context = 250000` to `opencode.jsonc` (using
the declaration form the spike established) and repoints
`.gleipnir/agents/orchestrator.md` `model:` to the capped id, with a comment
mirroring the Tier-3 value as single source of truth. *(operator action —
Tier-3.)*

**Step 5 — Record the durable decision.** Operator authors
`.gleipnir/decisions/context-cap.md` with the honesty label ("authored,
enforced-at-hook, not yet closed until S-2/G-1"), the validated opencode version
(hook coupling), the spike result, and the single-source-of-truth propagation
note. *(operator action — Tier-3.)*

**Assemble step order (summary):**
`0 (code-agent draft plugin) → 1 (SPIKE gate) → 2 (Tier-3 value file) → 3 (place plugin + pin rules) → 4 (arm cap) → 5 (decision record)`

---

## 5. Stress-test — acceptance checks

- **S0 (spike, blocking):** With the capped id assigned to the orchestrator only,
  the orchestrator reports the capped `limit.context` AND at least one subagent
  (`gleipnir-code`) reports its **base** (uncapped) local window. If the subagent
  is also capped ⇒ **FAIL → escalate** (Approach B). *(This gates all wiring.)*
- **S1 (cap applied):** Orchestrator's effective `limit.context` == the configured
  value (default 250000).
- **S2 (scope):** No agent other than `orchestrator` has its local context window
  altered. Grep `opencode.jsonc` + agent frontmatter: exactly one `model:` points
  at the capped id.
- **S3 (unset = no cap, first-class):** With the override line removed from
  `opencode.jsonc` and the value commented in the policy file, the orchestrator
  uses its base model's default limit; no error, no implicit 0. The policy file
  visibly documents this state.
- **S4 (configurable):** Changing the value in the policy file + the mirrored
  `opencode.jsonc` line changes the enforced window; the two match (no drift).
- **S5 (preservation, positive assertion):** On compaction, the block
  "## Critical Guardrails (preserved across compaction)" appears in context and
  contains the orchestrator's pinned entries — assert the entries are *present*,
  not merely that nothing threw (edge case 4).
- **S6 (key swallowed):** The `compaction_survival` key does not appear in the
  outbound request `options` nor at its top level (edge case 5). No provider
  rejection of an unknown field.
- **S7 (coexistence):** `sequence-gate.ts` is unmodified and both plugins load.
- **S8 (no truncation / no fail-closed):** At the cap the session continues
  (compacts) rather than truncating hard or refusing.
- **S9 (honesty label present):** The decision record carries the "authored,
  enforced-at-hook, not yet closed until S-2/G-1" label and the validated
  opencode version (edge case 6 / hook coupling).
- **S10 (tier integrity):** No bounded agent wrote any Tier-3 path; all placements
  in Steps 2–5 were operator actions. (Verifiable by authorship.)

---

## 6. Execution Workflow

**For the orchestrator sequencing this plan.** ATLAS/GOTCHA already ran (this
plan). The pipeline from here: `spec-review → (spike) → [operator actions]`.
Note this feature is **operator-heavy**: only the plugin *source draft* is a
bounded `gleipnir-code` deliverable; every placement is a Tier-3 operator action.

### OPERATOR tasks (Tier-3 — a bounded code agent CANNOT do these)

1. **Run / commission the spike (Step 1).** Read-only + throwaway probe.
   Establish the capped-id declaration form for this environment and prove
   non-leakage to subagents. Record the result. **Gate: PASS required.**
2. **On spike FAIL:** decide (at the convergence gate) whether to adopt the
   reserved Approach-B scoped plugin. Do **not** let a subagent decide this.
3. **Author the Tier-3 policy value file** with the "unset = no cap" comment
   (Step 2).
4. **Place the preservation plugin** at `.gleipnir/plugins/compaction-survival.ts`
   and add the `compaction_survival:` block to `orchestrator.md` (Step 3).
5. **Arm the cap** in `opencode.jsonc` + repoint `orchestrator.md` `model:`
   (Step 4).
6. **Author the durable decision record** with the honesty label + validated
   opencode version (Step 5).
7. Run the Stress-test checks S0–S10.

### Bounded `gleipnir-code` task (the ONLY code-agent unit here)

- **Author the ported plugin source as a draft** (Step 0) — a proposal the
  operator reviews and places. Constraints: port `compaction-survival.ts` with
  `.gleipnir/` paths, keep both hooks and both swallow-deletions, no behavioural
  change, no new dependencies. **The code agent writes the draft outside Tier-3
  paths (e.g. as a plan attachment / scratch), never into `.gleipnir/plugins/`,
  `.gleipnir/policy/`, `.gleipnir/agents/`, `.gleipnir/decisions/`, or
  `opencode.jsonc`.** One verb, one object: *author plugin source*. Verification:
  matches the reference behaviour with adapted paths (reviewer check).

### Honesty labels to carry forward (bake into the decision record)

- **`.gleipnir/plugins/compaction-survival.ts`** is Tier-3 enforcement-bearing
  code: **authored, enforced-at-hook, not yet closed** — it is cooperative policy
  until S-2 boundary + G-1 preflight make `plugins/**` OS-ro to the agent uid
  (`decisions/s2-g1-closure.md`). It is *not* an unbreakable guard today.
- The cap is **cooperative policy**, not yet OS-enforced: Tier-3 by intent,
  agent-unwritable only after S-2 closure.
- **Experimental-hook version coupling:** `experimental.session.compacting` and
  `chat.params` "may change without notice." Record the validated opencode
  version; an opencode upgrade is a re-validation trigger.

### Deferred / out of scope (do not bundle — brief-excluded)

- G-4d ledger integration, per-subagent budgets, session-level ad-hoc override
  (brief Open Question — defer to a follow-up if the operator raises it).
- `/plan` and `/build` scoping — explicitly out of scope (orchestrator only).

---

## New material tradeoff report (to the operator)

**None found.** The converged design holds. Three items surfaced that are
**mechanical / factual**, not material value-choices, and are handled inline:
(1) `.gleipnir/plugins/` already exists (`sequence-gate.ts`) — no dir creation,
no `plugin:` array needed (auto-discovery); (2) the Tier-3 file format (jsonc
vs md) is a Link-time mechanical pick; (3) the exact capped-model-id declaration
form in this aperture environment is a **known unknown resolved by the
spike**, not a new decision.

**One conditional decision is *reserved for the operator*, not decided here:**
if **Spike S0 FAILS** (the model-limit override leaks the cap to subagents),
the ENFORCEMENT mechanism must switch to the reserved Approach-B scoped plugin —
a material change to a converged decision. Per role boundary, this plan **names
it and stops**; the orchestrator must surface it at the convergence gate for the
operator to decide.
