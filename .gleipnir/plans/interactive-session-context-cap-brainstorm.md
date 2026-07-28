# Design Brief: Operator-Configurable Context-Length Cap for the Interactive Session

> **Convergence status: CONVERGED (operator, via the orchestrator).** The
> `gleipnir-brainstorm` subagent produced the `## Decision Analysis`; the
> operator then decided each material tradeoff through the orchestrator and the
> converged choices are recorded in "Selected Approach" below. Two operator
> decisions materially changed the original brief: (a) **scope is now the
> `orchestrator` ONLY** (not `/plan`, not `/build`), and (b) **at-cap behaviour
> is modelled on AETOS's context-preservation mechanism**, investigated and
> cited below. This brief is ready to hand to `gleipnir-plan`.

## Problem Statement

The operator wants to bound how large the **interactive session's** context is
allowed to grow, so that the primary interactive agents do not silently consume
a full 1M-token window when a much smaller budget delivers the same
quality-efficient outcome. Today nothing caps interactive context; it grows
until the model's declared limit or opencode's auto-compaction intervenes at a
window the operator never chose. The capability is a **policy knob**: the
operator sets an arbitrary cap (default 250K tokens) that governs the framework
**`orchestrator` agent only**. When the value is **unset/removed**, the artificial
constraint is gone and the orchestrator falls back to the model's default
context limit — "unset" is a first-class, documented state.

## Constraints

**Operator-decided (FIXED inputs — CONVERGED, not re-litigated):**

- **Surface (REVISED — orchestrator only):** the cap applies to the framework's
  `orchestrator` agent **only**. **NOT** `/plan`, **NOT** `/build`, **NOT** any
  other agent. All other agents are **unlimited locally** (remote provider limits
  still apply naturally). **NOT** per-subagent budgets. **NOT** the G-4d ledger.
  *(This overturns the original brief's premise that the cap covered all three
  interactive agents. Because only the `orchestrator` — a framework Tier-3 agent —
  is capped, the "escape hatches outside preflight" concern for `/plan` and
  `/build` no longer applies to this feature at all.)*
- **Default value:** 250K tokens (1M is unnecessary and wasteful; the framework
  goal is quality-efficient outcomes per token).
- **Configurable, not hard-coded:** the operator can set the cap to an arbitrary
  value.
- **Unset = no cap (first-class state):** the Tier-3 policy file must carry an
  explicit comment stating that **removing / unsetting the value removes the
  artificial constraint** — absence of the value means *no cap*, falling back to
  the model's default context limit. "Unset" is a documented, first-class state,
  not an error or an implicit zero.

**Substrate constraints discovered during Explore (grounded, not assumed):**

- opencode's `AgentConfig` (per-agent frontmatter / `agent.<name>` config)
  exposes `model, variant, temperature, top_p, prompt, tools, steps, permission`
  and nothing else. **There is no per-agent "context length" or "token cap"
  field.** (Confirmed against `https://opencode.ai/config.json`, `$defs/AgentConfig`.)
- The only *declared* context window lives at `provider.models.<id>.limit.context`
  (a number) — a **model-level, top-level** value, not per-agent.
- The only native *behaviour-at-fullness* lever is the top-level `compaction`
  object: `auto` (bool), `prune` (bool), `tail_turns`, `preserve_recent_tokens`,
  `reserved`. Compaction triggers off the model's context limit, not an
  operator-chosen sub-limit.
- Plugin hooks that can observe/act on message volume exist:
  `chat.params`, `chat.message`, `event`, and the experimental
  `experimental.chat.messages.transform` / `experimental.session.compacting` /
  `experimental.compaction.autocontinue`. `subagent_depth: 1` is set, so only
  the primary session + one delegation layer exist.
- **Trust tiers (AGENTS.md / gleipnir-layout-and-memory-model):** Tier 3 =
  POLICY (`agents/ skills/ goals/ decisions/ stage-role-map.md keys/`), operator
  only. `plugins/**` is in the **Tier-3 enforcement path set** per
  `s2-g1-closure.md` (OS-ro to the agent uid once S-2 closes). No `plugins/`
  directory exists yet.
- **`orchestrator` is a framework Tier-3 agent** (`.gleipnir/agents/orchestrator.md`),
  so capping *it* (and only it) stays entirely within the framework's own config
  surface. `/plan` and `/build` (Part-0 escape hatches, outside preflight) are
  **out of scope** for this feature per the operator's revised decision — no
  interaction with them.
- **"Authored, not yet closed":** S-2 boundary and G-5 engine do not exist yet.
  Any file placed under a Tier-3 path is *policy-tier by intent* today and
  *OS-enforced* only after S-2 closure.

**AETOS context-preservation mechanism (investigated in `../aetos`, cited):**

- `../aetos/.aetos/plugins/compaction-survival.ts` (v3.19.0) hooks
  **`experimental.session.compacting`**. It scans agent templates, skill
  `SKILL.md` files, rule files, and `src/python/aetos/plugins/*.json` manifests
  for a **`compaction_survival`** frontmatter/JSON key, deduplicates the entries,
  and **re-injects them into `output.context`** under a heading
  `"## Critical Guardrails (preserved across compaction)"` (lines 104–147). It
  does **not** truncate or fail — it lets native compaction run and **pins the
  critical elements back in**.
- A companion **`chat.params`** hook (lines 153–165) *swallows* the custom
  `compaction_survival` key from the outbound request so it never reaches the
  model (Bedrock rejects unknown fields).
- Real usage: `../aetos/.opencode/agents/aetos.md` (the AETOS orchestrator) has a
  `compaction_survival:` block (lines 33–34) listing the hard rules, delegation
  discipline, and a **"SESSION RECOVERY: after context compaction … review recent
  delegation events before resuming"** rule — i.e. the orchestrator's critical
  state is explicitly pinned to survive compaction. `project-mgr.md` and
  `git-ops.md` carry their own `compaction_survival` blocks too.
- Model context limits in AETOS are declared at
  `provider.models.<id>.limit.context` (`../aetos/opencode.json` lines 12–14,
  set to `200000`), and a top-level `compaction` block is tuned (lines 51–59,
  179+). So AETOS's answer to "constrained context" is **cap the window at the
  model-limit level + preserve pinned elements via the plugin**, never hard
  truncation or refusal.

## Approaches Considered

The capability decomposes into three near-orthogonal material questions. Each
approach below is a coherent bundle of one answer to each; the Decision Analysis
then separates them so the operator can mix if desired.

> **Note on scope revision.** Approaches were originally framed around three
> interactive agents. The operator converged on **orchestrator-only** scope,
> which *removes* Approach A's central weakness (model-id leakage across many
> agents) because only one agent — the framework's own Tier-3 `orchestrator` —
> needs the capped model id.

### Approach A: Tier-3 cap value + model-limit override on the orchestrator (SELECTED)

**Summary:** A Tier-3 policy file under `.gleipnir/` holds the cap value (default
250K, with an explicit "unset = no cap" comment). The orchestrator points at a
dedicated capped `provider.models.<id>` whose `limit.context` equals that value,
so opencode's native limit/compaction machinery enforces the 250K window on the
orchestrator only. At-cap behaviour is AETOS-style preservation (Approach detail
below / Decision 3).

**Tradeoffs:**
- Pro: Cap value lives in the **correct trust tier** (Tier-3, operator-only,
  OS-ro once S-2 closes) — a policy knob agents cannot silently change (G-1).
- Pro: Enforcement uses a **real, native, non-experimental key**
  (`limit.context`) — opencode compacts gracefully, no hard failure.
- Pro: **Orchestrator-only scope is clean now** — exactly one agent points at the
  capped model id; no leakage risk to `/plan`, `/build`, or subagents.
- Pro: Arbitrary/configurable — the cap is just a number; "unset" removes it.
- Con: Cap value (Tier-3) and enforcement wiring (`opencode.jsonc` +
  `orchestrator.md` `model:`) live in **two places** — needs a documented link so
  the value stays the single source of truth.
- Con: A capped model id is a slightly indirect construct — a spike must confirm
  assigning it to the orchestrator does **not** bleed into any agent sharing the
  base model (operator's spike-first caveat).

**Estimated Scope:** new Tier-3 file (e.g. `.gleipnir/policy/context-cap.jsonc`);
`opencode.jsonc` `provider.models.<capped-id>.limit.context`; `orchestrator.md`
frontmatter `model:`; AETOS-style `compaction_survival` on `orchestrator.md`
(Decision 3). Low complexity.

**Risk:** low-medium — model-id indirection is the only real risk, retired by the
spike; scope collapsed to one agent removes the leakage con entirely.

### Approach B: Tier-3 policy file + custom plugin enforcement hook

**Summary:** The Tier-3 file holds the cap; a plugin under `.gleipnir/plugins/`
reads it and enforces per-agent via `chat.params` /
`experimental.session.compacting`, scoped to the `orchestrator` by name.

**Tradeoffs:**
- Pro: Correct trust tier, and the plugin can express **any** at-cap behaviour
  and read the value at load.
- Pro: Per-agent scoping is explicit in code (no reliance on model-id identity).
- Con: Requires **net-new machinery** — a `plugins/` dir (does not exist) and
  reliance on `experimental.*` hooks that "may change without notice"
  (substrate-design-pass caveat on #6).
- Con: A plugin is **enforcement-bearing code** — under G-1 it must be covered by
  S-2 closure + preflight, which are "not yet closed" (policy-by-intent only now).

**Estimated Scope:** new `.gleipnir/plugins/context-cap.(ts|js)`, Tier-3 value,
`opencode.jsonc` wiring. Medium complexity; touches the enforcement boundary.

**Risk:** medium-high — experimental hooks + pre-closure boundary. **Reserved as
the escalation path** if the spike shows the model-limit override can't scope to
the orchestrator cleanly, or if a future at-cap behaviour outgrows native
compaction. *(A `.gleipnir/plugins/compaction-survival.(ts)` port of the AETOS
plugin is a separate, complementary piece — see Decision 3 — and does not require
adopting Approach B's enforcement model.)*

### Approach C: Native `compaction` tuning only (no discrete cap)

**Summary:** No numeric ceiling; tune the top-level `compaction` block so the
session compacts aggressively. Rejected — `compaction` has no "cap at 250K" field
and is global, so it cannot deliver an arbitrary orchestrator-scoped cap. Kept
only as the honest "native-only, no cap" baseline.

**Risk:** low technically, high requirement-risk (does not meet the constraints).

## Decision Analysis

Three material tradeoffs are surfaced. Each is presented as options +
recommendation for the **operator** to converge. (Frameworks: Reversibility
Filter first, then per decision type.)

---

### Material Decision 1 — WHERE the cap is declared/read

**Reversibility:** Two-Way Door (config location is cheap to move). Framework:
**Weighted Decision Matrix** (multi-option, trust-tier is the dominant criterion).

| Criterion | Weight | Opt 1: top-level `opencode.jsonc` | Opt 2: Tier-3 file under `.gleipnir/` | Opt 3: per-agent frontmatter |
|---|---|---|---|---|
| Correct trust tier (policy = operator-only, G-1) | 9 | 3 (27) — repo-root, outside boundary | 9 (81) — Tier-3, operator-only | 6 (54) — `orchestrator.md` is Tier-3, but no context field |
| Reaches the orchestrator cleanly | 8 | 7 (56) — via its model id | 8 (64) — value read + wired to its model id | 5 (40) — Tier-3 but no context field to hold the value |
| Uses a real config key (no new machinery) | 7 | 8 (56) | 6 (42) — value file + native `limit.context`, no plugin needed | 2 (14) — no context field in AgentConfig |
| Single source of truth | 6 | 5 (30) | 9 (54) | 4 (24) |
| Supports a first-class "unset = no cap" state | 7 | 4 (28) — awkward in shared config | 9 (63) — documented, commented, first-class | 3 (21) |
| **Total** | | **197** | **304** | **153** |

**CONVERGED:** **Option 2 — a Tier-3 policy file under `.gleipnir/`** (operator's
recommendation, confirmed). A context-cap is a *policy knob*; the memory model
puts policy in Tier-3, operator-only — the right home for a knob an agent must
not silently change. The value is read and wired to the orchestrator's capped
model id (Decision 2, native `limit.context` — no plugin required).

**Operator's added requirement (unset = no cap, first-class):** The Tier-3 file
**must carry an explicit comment** stating that *removing / unsetting the value
removes the artificial constraint* — absence of the value = **no cap**, falling
back to the model's default context limit. The file is designed so "unset" is a
documented, first-class state (e.g. the key present-and-numeric ⇒ cap applies;
key absent/commented-out ⇒ orchestrator uses the model default). This is why Opt 2
now also scores highest on the new "unset" criterion.

**Bias check:**
- ⚠️ *IKEA Effect (mild):* the Tier-3 recommendation aligns with the framework's
  own G-1 story — verify it is chosen for the operator's benefit (a knob agents
  can't alter) and not merely because it flatters the architecture. It survives
  that test: an operator-only policy knob is genuinely the right control class.
- Status-quo / anchoring: the 250K default is an operator-fixed input, not an
  anchor this analysis introduced — no distortion.

---

### Material Decision 2 — What "context length" maps to, and how it is read/enforced

**Framework:** **Hypothesis-Driven Analysis** (uncertainty about what the
substrate can actually do). Confirmed fact: **there is no native per-agent
context-cap key** — so a *true, arbitrary, agent-scoped 250K cap* requires
either a model-limit override or a plugin.

- **Hypothesis A — Model-limit override:** *If* we set
  `provider.models.<capped-id>.limit.context = 250000` and point **the
  orchestrator** at that model id, *then* opencode enforces a 250K window via its
  own compaction, *because* limit.context is the value all context machinery
  reads. Key assumption: assigning the capped model id to the orchestrator does
  **not** leak the cap to other agents/subagents that use the base model.
  Evidence for: it is a real, documented, non-experimental key; AETOS uses
  exactly this key (`../aetos/opencode.json` lines 12–14). Evidence against:
  model-scoped not agent-scoped — a distinct capped model id must be reserved for
  the orchestrator. **Confidence: High** that it works; **High** that it scopes
  cleanly now that scope is a *single* agent (the leakage risk that lowered this
  under three-agent scope is gone).
- **Hypothesis B — Plugin reads Tier-3 value, enforces per-agent:** *If* a
  plugin reads the cap and hooks `chat.params`/`experimental.session.compacting`
  scoped by agent name, *then* we get an arbitrary, agent-scoped cap with chosen
  behaviour, *because* the hook sees the session and message volume. Key
  assumption: the experimental hooks are stable enough to depend on. Evidence
  for: hooks exist and are listed as present (substrate-design-pass #6). Evidence
  against: marked **experimental, "may change without notice"**; enforcement code
  before S-2 closure is authored-not-enforced. **Confidence: Medium.**
- **Hypothesis C — Compaction tuning only:** no true cap; **rejected** as not
  meeting the arbitrary-cap constraint (see Approach C).

**CONVERGED:** **Hypothesis A — `limit.context = 250000` model-limit override**
(operator's recommendation, confirmed), with the *value* sourced from the Tier-3
policy file of Decision 1 and wired to a capped model id assigned to the
orchestrator only. Escalate to a plugin (Hypothesis B) **only if** the spike
shows the model-limit override can't scope to the orchestrator cleanly, or a
future at-cap behaviour outgrows native compaction. **Spike-first caveat stands
(operator):** before committing, confirm a distinct capped model id can be
assigned to `orchestrator` **without** leaking to any other agent/subagent that
shares the base model.

**Bias check:**
- ⚠️ *Dunning-Kruger:* confidence about the experimental hooks (the plugin
  escalation path) in a substrate area the framework flags as unstable — the
  "spike before committing" mitigation is deliberately attached.
- ⚠️ *Scope Creep:* resist bundling this with the G-4d ledger or per-subagent
  budgets — both are operator-excluded. Hold the line at the **orchestrator
  only**.

---

### Material Decision 3 — Behaviour AT the cap (AETOS-grounded)

**Operator directive:** do NOT assume native summarise/compact; base the
behaviour on **how AETOS preserves key context elements** under constraint.
Investigated `../aetos` (readable) and grounded the design in real files:

**What AETOS actually does (cited):**

1. **Model window is capped at the model-limit level.**
   `../aetos/opencode.json` (lines 12–14) declares each model with
   `"limit": { "context": 200000, ... }`. AETOS does **not** run to 1M; it caps
   the window in provider-model config — the same `limit.context` key this brief
   uses for enforcement (Decision 2).
2. **Native compaction runs, but critical elements are pinned and re-injected.**
   `../aetos/.aetos/plugins/compaction-survival.ts` (v3.19.0) hooks
   **`experimental.session.compacting`** (lines 104–147): it scans agent
   templates, skill `SKILL.md`, rule files, and `plugins/*.json` manifests for a
   **`compaction_survival`** key, dedupes the entries, and **pushes them back
   into `output.context`** under the heading
   `"## Critical Guardrails (preserved across compaction)"`. So when the window
   is constrained and opencode compacts, the operator/agent does **not** lose the
   critical rules — they are re-pinned every compaction.
3. **The custom key is swallowed before it reaches the model.** A `chat.params`
   hook (lines 153–165) deletes `compaction_survival` from the outbound request
   so the provider never sees an unknown field.
4. **Real usage on the orchestrator.** `../aetos/.opencode/agents/aetos.md`
   (the AETOS orchestrator) carries a `compaction_survival:` block (lines 33–34)
   pinning its hard rules, delegation discipline, and explicitly a
   **"SESSION RECOVERY: after context compaction … review recent delegation
   events before resuming"** rule. `project-mgr.md` and `git-ops.md` pin their
   own critical rules too.

**AETOS's answer, in one line:** *cap the window at the model-limit level, let
native compaction run, and preserve the critical context elements by
re-injecting pinned `compaction_survival` entries on every compaction* — never
hard truncation, never refusal/fail-closed.

**Framework — Pre-Mortem** applied to the four candidate behaviours, now judged
against the AETOS pattern:

| # | Behaviour | Verdict vs AETOS | Why |
|---|---|---|---|
| a | Hard truncation | **Reject** | AETOS never silently drops context; it preserves the critical set |
| b | Refusal / fail-closed | **Reject** | AETOS never blocks the session; the human keeps working |
| c | Native compaction, unguided | **Insufficient alone** | AETOS does compact, but *does not trust* raw compaction to keep the critical elements — that is the whole reason the plugin exists |
| **AETOS** | **Compaction + `compaction_survival` re-injection** | **SELECTED** | Bounds tokens (goal met) AND guarantees the orchestrator's critical rules survive the constrained window |

**CONVERGED at-cap behaviour (modelled on AETOS):** When the orchestrator reaches
the 250K cap, **native compaction runs, and a `compaction-survival` plugin
re-injects the orchestrator's pinned `compaction_survival` entries** so its
critical operating rules (delegation discipline, convergence-gate rules, session
recovery) survive the constrained window. This is a **port of the AETOS
`compaction-survival.ts` plugin**, adapted to `.gleipnir/` paths (scan
`.gleipnir/agents/*.md`, `.gleipnir/skills/*/SKILL.md`), plus a
`compaction_survival:` block on `.gleipnir/agents/orchestrator.md`. No hard
truncation; no fail-closed.

**Bias check:**
- ⚠️ *Availability / Recency:* the earlier "fail-closed = safe" instinct is
  explicitly rejected — AETOS's real, shipped behaviour is preservation, not
  blocking. Grounding in the cited files (not the guard-mindset heuristic)
  corrects the anchor.
- ⚠️ *IKEA Effect (checked):* the plugin is *ported from AETOS*, not invented
  here — it is chosen because it is the operator-requested, battle-tested sibling
  mechanism, not because we built it.

---

### G-1 / "authored-not-closed" interaction (cross-cutting)

- The cap value lives **Tier-3** (Decision 1, Opt 2): *policy-by-intent* today,
  **OS-unwritable by agents** once S-2 closes — the correct end state. The
  ported **`compaction-survival` plugin** is enforcement-bearing code and MUST
  land under `.gleipnir/plugins/**`, already in the Tier-3 enforcement path set
  (`s2-g1-closure.md`), so closure covers it for free.
- **Escape-hatch concern retired.** Because scope is **orchestrator-only**, this
  feature does not touch `/plan` or `/build` — the "escape hatches outside
  preflight" concern from the original brief **no longer applies** to this
  feature. The orchestrator is a framework Tier-3 agent; capping it stays wholly
  inside the framework's own config surface.
- **Honest label:** what is built now is *authored, not enforced* until S-2
  closure — the cap is cooperative policy, not yet unbreakable. The eventual
  `decisions/` record must carry this label, matching the framework's honesty
  posture. The `experimental.session.compacting` hook is `experimental` (may
  change without notice) — same caveat AETOS already lives with (#6 in
  substrate-design-pass).

---

**Overall converged design:**
Tier-3 policy file holds the cap value with an explicit **"unset = no cap"**
comment (D1·Opt2) → read and wired to a capped model id assigned to the
**orchestrator only** via native `limit.context = 250000` (D2·HypA, spike-first)
→ at-cap behaviour is **AETOS-style compaction + `compaction_survival`
re-injection** (ported plugin), never hard-truncate or fail-closed (D3).
Default 250K, arbitrary, unset ⇒ model default, orchestrator only.

## Selected Approach

**Choice: Approach A — Tier-3 cap value + native `limit.context` model-limit
override on the orchestrator, with AETOS-style `compaction_survival` preservation
at the cap.** (Operator-converged via the orchestrator.)

**The converged design, concretely:**

1. **WHERE (D1 → Opt 2, Tier-3):** the cap value lives in a new operator-only
   Tier-3 file under `.gleipnir/` (e.g. `.gleipnir/policy/context-cap.jsonc`).
   The file **must carry an explicit comment** stating: *removing / unsetting the
   value removes the artificial constraint — absence = no cap = fall back to the
   model's default context limit.* "Unset" is a first-class, documented state
   (key present-and-numeric ⇒ cap applies; key absent/commented ⇒ model default).
2. **ENFORCEMENT (D2 → Hyp A):** a dedicated capped `provider.models.<capped-id>`
   with `limit.context = <cap>` (default 250000) in `opencode.jsonc`; the
   `orchestrator` agent's `model:` points at that capped id. **Spike first**
   (operator caveat): confirm the capped id binds to the orchestrator only and
   does **not** leak to other agents/subagents sharing the base model.
3. **SCOPE (operator, MATERIAL):** **orchestrator only.** NOT `/plan`, NOT
   `/build`, NOT any other agent. All other agents unlimited locally (remote
   provider limits still apply naturally).
4. **AT-CAP BEHAVIOUR (D3 → AETOS):** native compaction runs and a
   **`compaction-survival` plugin ported from AETOS**
   (`../aetos/.aetos/plugins/compaction-survival.ts`) re-injects the
   orchestrator's pinned `compaction_survival` entries so its critical operating
   rules survive the constrained window. Add a `compaction_survival:` block to
   `.gleipnir/agents/orchestrator.md`. **No hard truncation; no fail-closed.**

**Rationale:** This bundle satisfies every operator-fixed input — arbitrary/
configurable (a number), 250K default, orchestrator-only, unset ⇒ no cap — while
placing the knob in the correct trust tier (Tier-3, weighted-matrix winner
304 vs 197 vs 153) and using a real, non-experimental enforcement key. The at-cap
behaviour is not invented: it is the sibling AETOS mechanism the operator asked
for, grounded in the cited files, which preserves the orchestrator's critical
context rather than truncating or blocking it.

## Open Questions (for `gleipnir-plan` to resolve during planning — none are material tradeoffs)

- **Spike outcome (blocking the enforcement choice):** does assigning the capped
  model id to the orchestrator leak to any agent/subagent sharing the base model?
  If yes, escalate to the reserved Approach-B scoped plugin. `gleipnir-plan`
  should sequence this spike in ATLAS-Link before the build order.
- **Tier-3 file format:** `.jsonc` value fragment vs a small policy `.md` — pick
  the form that best carries the required "unset = no cap" comment and is easiest
  for the enforcement wiring to read. (Mechanical, not material.)
- **`compaction_survival` content set:** which orchestrator rules to pin
  (delegation discipline, convergence-gate rules, session recovery) — model on
  AETOS `aetos.md` lines 33–34.
- Does the operator want a **session-level override** to raise the cap ad hoc, or
  is the configured value fixed per launch? (Defer to a follow-up if raised.)

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Cap value (policy knob, unset=no-cap comment) | New Tier-3 file under `.gleipnir/` (e.g. `policy/context-cap.jsonc`) — operator-authored |
| Native enforcement (D2·HypA) | `opencode.jsonc` — `provider.models.<capped-id>.limit.context` |
| Orchestrator wiring (scope = orchestrator only) | `.gleipnir/agents/orchestrator.md` frontmatter `model:` (Tier-3, operator-authored) + `compaction_survival:` block |
| At-cap preservation (D3, ported from AETOS) | New `.gleipnir/plugins/compaction-survival.(ts)` (Tier-3, enforcement-bearing) — port of `../aetos/.aetos/plugins/compaction-survival.ts`; hooks `experimental.session.compacting` + `chat.params` swallow |
| Plugin registration | `opencode.jsonc` `plugin:` array (+ create `.gleipnir/plugins/`, does not exist yet) |
| Durable outcome | A `decisions/` record (operator-authored) with the "authored, not enforced until S-2" honesty label |
