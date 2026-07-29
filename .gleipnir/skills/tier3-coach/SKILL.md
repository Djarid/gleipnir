---
version: "1.0"
name: tier3-coach
description: "Detect a Tier-3 / substrate enforcement-control gap, propose the concrete control artifact (git hook, permission change, decision-record amendment, CI/OS setting) with rationale, converge material tradeoffs on the operator, and hand off to build/operator to implement. Proposes only — never implements."
license: MIT
metadata:
  version: "1.0"
  origin: gleipnir
  inherited_by: gleipnir
  inheritance: original
  rationale: "The framework repeatedly REMOVES a control from one layer (e.g. moving git guard policy out of the broker) leaving a gap the operator must fill in a layer the agent cannot reach (git hooks, Tier-3 config, CI, OS). Nothing produced that proposal as a first-class artifact — it happened informally in chat. This skill makes 'here is the control gap, here is the concrete fix, go implement it in build' a repeatable capability."
---

> **GLEIPNIR ORIGINAL SKILL.** Not inherited from AETOS. It encodes a pattern
> the framework's own build kept hitting: an agent, correctly, cannot write the
> place a control actually belongs (a Tier-3 file, a git hook, CI config, an OS
> branch-protection setting). The right move is to **propose** the control
> precisely and hand off — not to smuggle policy into a layer the agent *can*
> reach just because it can reach it. Putting a guard in the wrong layer to
> route around a capability boundary is itself the anti-pattern.

# Tier-3 Control Coaching Skill

Use this skill when a task reveals an **enforcement-control gap in a layer the
agent cannot (and must not) write**: Tier-3 policy config, git hooks, CI
pipelines, OS/remote settings, credential stores. The skill turns "there should
be a control here, but I can't put it here" into a concrete, reviewable
**proposal** the operator applies (typically: agent proposes in plan/normal
mode → operator switches to build → operator or a bounded role implements).

## The core principle (why this exists)

**Controls belong in the layer that owns them, not the layer the agent can
reach.** When the framework removes a policy from an agent-reachable layer (e.g.
moving git secret/branch/data-file checks out of the broker), the control does
not vanish — it **relocates** to where it belongs (a `pre-commit` hook, a CI
job, an OS branch-protection rule). But those layers are, by design, **beyond
the agent's capability boundary**. So the agent must:

1. **Name the gap** — what control was removed/absent, and what now goes
   unenforced.
2. **Locate the correct layer** — where the control *should* live (see the
   layer map below), and confirm the agent cannot write there (that's expected,
   not a bug).
3. **Propose the concrete artifact** — exact file path, exact content, exact
   activation steps. Not "you should add a hook" but "here is
   `hooks/pre-commit`, here is its content, install it with `git config
   core.hooksPath hooks`".
4. **Converge material tradeoffs on the operator** (via the orchestrator — same
   self-attestation discipline as `brainstorm`).
5. **Hand off** — the operator switches to build (or delegates to the bounded
   role that can write that layer) and applies it. The skill NEVER implements.

## Layer map — where controls live and who can write them

| Layer | Examples | Agent-writable? | Who applies the proposal |
|---|---|---|---|
| **Tier-3 POLICY** | `.gleipnir/agents/`, `skills/`, `goals/`, `decisions/`, `stage-role-map.md`, `keys/` | **No** — every roster grant denies `.gleipnir/**` | Operator (build mode / escape hatch) |
| **Substrate / VCS** | `.git/hooks/**`, `.gitattributes`, committed `hooks/` + `core.hooksPath` | **No** — `git-ops` denies all `.git/**`; no role has a hooks grant | Operator, or committed via the git broker + a `core.hooksPath` the operator sets |
| **CI / platform** | CI pipeline YAML, remote branch-protection rules, required checks | **No** — no roster role holds platform-admin credentials | Operator (platform UI / admin API) |
| **OS / credential** | file perms, dedicated uid, secret store, `GLEIPNIR_MARKER_KEY_FILE` | **No** — host-level, outside every tier | Operator (host) |
| Source tree | `src/**`, `tests/**` | Yes (`gleipnir-code`) | Bounded code agent |

If the control belongs in any **No** row, this skill's output is a proposal, and
the handoff target is the operator (or the one bounded role that can reach that
specific layer, e.g. the git broker committing a repo-tracked `hooks/` dir).

## Workflow: Detect → Locate → Propose → Converge → Hand off

### Phase 1: Detect
State the gap in one or two sentences: *what control is missing, and what is now
unenforced as a result.* Be concrete about the risk (e.g. "the broker no longer
blocks committed secrets; nothing does, until a pre-commit hook exists").
Distinguish **safety invariants** (must be enforced somewhere) from **workflow
preferences** (operator's choice whether to enforce at all).

### Phase 2: Locate
Identify the correct layer from the map above and **confirm the agent cannot
write it** — this is the whole reason a proposal (not an edit) is the right
output. If the control could legitimately live in an agent-writable layer
without weakening it, say so — do not manufacture a Tier-3 proposal for
something that belongs in `src/`.

### Phase 3: Propose
Produce a **complete, ready-to-apply artifact**, not a gesture at one:
- Exact **path** (e.g. `hooks/pre-commit`, `.gleipnir/decisions/<name>.md`).
- Exact **content** (the full hook script / the config diff / the record text).
- Exact **activation** (`git config core.hooksPath hooks && chmod +x ...`; or
  "operator switches to build and writes this file"; or "set in the platform's
  branch-protection UI").
- **What it enforces, and its bypass semantics** — e.g. "runs for humans and
  agents; the operator can bypass with their own `--no-verify` (their call); the
  broker cannot pass `--no-verify` so the agent cannot bypass it."
- **Honesty label** — is this a hard boundary or cooperative policy today?
  (Pre-S-2, most of these are cooperative-policy: real once the substrate
  boundary lands.)

### Phase 4: Converge (only if a material tradeoff exists)
If the proposal embeds a **material decision** (strict vs permissive default;
which checks are safety vs preference; blocking vs advisory), surface it to the
operator **through the orchestrator** — you (a subagent) cannot reach the
operator, and must not self-attest a convergence. Return the options +
recommendation; let the orchestrator put it to the operator. (Same rule as the
`brainstorm` skill's Converge phase.) A purely mechanical control (no tradeoff)
skips this phase.

### Phase 5: Hand off
State plainly: **"This is a `<layer>` control; I cannot write it. To apply:
switch to build and [exact steps], or delegate to [role]."** Then stop. Do not
implement. Do not route the control into an agent-reachable layer to avoid the
handoff.

## Output Format

Write the proposal to `.gleipnir/plans/<name>-control-proposal.md` (Tier 0 —
the one place a brainstorm subagent may write) with:

```markdown
# Tier-3 Control Proposal: <title>

## Gap
<What control is missing / was removed, and what is now unenforced. Safety vs preference.>

## Correct layer
<Which layer it belongs in, per the layer map; confirmation the agent cannot write it.>

## Proposed artifact
**Path:** <exact path>
**Content:**
​```
<the full, ready-to-apply content>
​```
**Activation:** <exact commands / operator steps>
**Enforces / bypass semantics:** <what it catches; who can bypass and how>
**Honesty label:** <hard boundary | cooperative-policy-until-S-2>

## Decision Analysis  (only if a material tradeoff exists)
<options + framework + bias check + recommendation — for the operator to converge>

## Handoff
<"Switch to build and run … " OR "delegate to <role> which can write <layer>">
```

## Anti-Patterns

**Anti-Pattern 1: Route the control into a reachable layer to dodge the handoff.**
The whole point is that the control belongs in a layer the agent can't write.
Putting it somewhere the agent *can* write (e.g. baking git policy back into the
broker) to avoid asking the operator is the exact mistake this skill prevents.

**Anti-Pattern 2: Vague proposal.** "You should add a pre-commit hook" is not a
proposal. The output is the *actual artifact* — full content, exact path, exact
activation — reviewable and ready to apply verbatim.

**Anti-Pattern 3: Implement it.** This skill proposes. It never writes the
Tier-3/substrate artifact itself, even in build mode by a subagent that lacks
the grant. Implementation is the operator's action (or a bounded role's).

**Anti-Pattern 4: Enforce a preference as if it were safety.** Separate "must be
enforced somewhere" (a real secret leaked to history) from "a workflow opinion"
(feature branches). Propose safety controls as needed; propose preference
controls as opt-in, default-off, and say which is which.

**Anti-Pattern 5: Self-attest convergence.** A subagent's `question` cannot
reach the operator. For a material tradeoff, return the analysis to the
orchestrator; never record an operator decision you did not receive.

## Resilience

If this skill cannot be loaded, fall back to: name the gap, name the correct
layer, write the fullest concrete proposal you can to `.gleipnir/plans/`, and
hand off to the operator. Never silently drop a control, and never route it into
the wrong layer to avoid the handoff.

## Status

**Authored, cooperative-policy.** The layers this skill proposes into (Tier-3,
git hooks, CI, OS) become *structurally* agent-unreachable only when the S-2
substrate boundary lands. Until then the capability denies (`.gleipnir/**`,
`.git/**`) are honoured by the roster grants, and this skill's discipline —
propose, don't route around — is what keeps controls in their proper layer.
