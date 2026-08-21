# Tier-3 Control Proposal: exclude `.github/**` from `gleipnir-code`'s edit grant

## Gap

`gleipnir-code`'s `edit` grant (`.gleipnir/agents/gleipnir-code.md`, lines
11–16) is permissive-base-minus-denies: `"*": allow` with explicit `deny` on
`.gleipnir/**`, `.git/**`, and `src/gleipnir/preflight/**` **only**. It does
**not** exclude `.github/**`. Verbatim, from disk:

```yaml
permission:
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    "src/gleipnir/preflight/**": deny
  read: allow
  task: deny
  webfetch: deny
```

**Consequence (unenforced):** `gleipnir-code` can *write* CI workflow files
(e.g. `.github/workflows/*.yml`) as a matter of raw capability. CI config is
enforcement-bearing — `.github/**` is in the Axis-1 disqualifier set `X`
(`stage-role-map.md`), which forces the full 8-stage hardened pipeline for any
plan that touches it. But that is a **pipeline-routing** control on the *plan*,
not a **capability** control on the *role's grant*. The two are different
layers: routing decides which stages run; the grant decides what the agent's
`edit` tool can physically touch. Today the routing control exists and the
capability control does not.

**Classification: workflow / defense-in-depth preference, NOT a live safety
invariant.** Honest assessment — the practical risk is already substantially
mitigated by three independent layers:

1. **Routing (Axis-1 `X`):** any plan whose touched-path set includes
   `.github/**` is disqualified from the light track and runs the full hardened
   8-stage pipeline (two-pass spec-review + blast-radius + negative-check
   attestation). A CI-file edit cannot slip through as low-consequence prose.
2. **No push path (G-2 broker single-holder):** `gleipnir-code` holds no git
   and no credentials (`bash: git*/gh*/glab* : deny`; `tools: gleipnir-git_*:
   false`). It cannot commit or push. Any file it writes is inert on the
   working tree until `git-ops` — a separate role, on a separate delegation —
   stages and commits it. A rogue/erroneous CI edit does not reach the remote
   by this agent's own action.
3. **Bounded delegation:** `gleipnir-code` acts only within the verb/object/
   boundary of a single delegation; it is not roaming the tree editing
   arbitrary files.

So this is **not** a "secret leaked to history / nothing stops it" safety hole.
It is a **least-privilege tightening**: the capability layer should match the
role's actual job (source + tests under `src/**`, `tests/**`), and a code agent
has no legitimate reason to author CI/platform config — that authorship is
enforcement-bearing and belongs to the operator/build step (which is exactly
what the config-scan CI wiring plan did deliberately). Closing the gap makes the
grant *say what we already do*, and adds a capability-layer backstop under the
routing-layer control (defense in depth: if a future plan-routing bug ever
mis-classified a `.github/**` touch, the grant would still refuse the write).

## Correct layer

**Tier-3 POLICY.** The grant lives in `.gleipnir/agents/gleipnir-code.md`, which
is Tier-3 (`agents/`). Per the layer map, Tier-3 is **not agent-writable**:
every roster grant denies `.gleipnir/**`, and `gleipnir-code` itself explicitly
denies `.gleipnir/**` (line 14) — so it **cannot write its own tightened
grant**. No roster agent can (all deny `.gleipnir/**`; the only `.gleipnir/`
writers — `gleipnir-plan`, `gleipnir-brainstorm`, `session-scribe` — are scoped
to `.gleipnir/plans/**` / `var/tmp/**` and one named lessons file, never
`agents/`). This must be applied by the **operator (build mode)**. That the
agent cannot write it is correct-by-design, not a bug — which is exactly why the
output here is a proposal, not an edit.

## Proposed artifact

**Path:** `.gleipnir/agents/gleipnir-code.md`

**Content (diff):** add one `deny` line to the existing `edit` block, matching
the established permissive-base-minus-denies style (there is **no** prior
`.github/**` precedent in any roster agent — this is the first; the style
precedent is `gleipnir-code`'s own existing deny list, lines 14–16):

```diff
   edit:
     "*": allow
     ".gleipnir/**": deny
     ".git/**": deny
+    ".github/**": deny
     "src/gleipnir/preflight/**": deny
   read: allow
```

Resulting block:

```yaml
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    ".github/**": deny
    "src/gleipnir/preflight/**": deny
  read: allow
```

Optionally (recommended for durability), add a one-line comment in the agent's
prose body noting why (mirrors the existing "Never attempt to edit anything
under `.gleipnir/`" note in Discipline). Not required for the grant to take
effect; the operator's call.

**Activation:** operator switches to build mode and applies the one-line edit
above to `.gleipnir/agents/gleipnir-code.md`, then commits it via the normal
git stage (`git-ops`). No restart semantics beyond opencode re-reading the agent
config. This is itself an enforcement-bearing Tier-3 change, so applying it
should go through the hardened pipeline / operator review it describes.

**Enforces / bypass semantics:** once applied, `gleipnir-code`'s `edit` tool
refuses any path under `.github/**` by capability (deny wins over the `"*":
allow` base, same as the existing three denies). The agent cannot bypass it —
it is a grant the agent cannot rewrite (it denies `.gleipnir/**`). The operator
can always change the grant (it is their policy file). This is a **capability**
control, distinct from and additive to the existing **routing** control.

**Honesty label:** **cooperative-policy-until-S-2.** The `edit` deny is honoured
by opencode's permission layer today, but becomes a *structural* boundary only
when the S-2 substrate read-only mount lands (same status caveat as the existing
`.gleipnir/**` deny — see the agent's "Status: authored, partially closed"
note). It is real policy now, hard boundary later.

## Decision Analysis

A material tradeoff is embedded: **how broadly to deny.** `.github/**` contains
both enforcement-bearing content (`workflows/**`, `actions/**`) and benign
non-executable content (`ISSUE_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md`,
`CODEOWNERS`, `FUNDING.yml`, `dependabot.yml`). Denying the whole tree is
safe-side but slightly over-broad; scoping to `workflows/**` is precise but
leaves other enforcement-adjacent files (`dependabot.yml`, `CODEOWNERS`, custom
`actions/**`) writable. This is not mine to decide — returning to the
orchestrator for operator convergence.

**Decision type:** reversible, low-cost, security-defaults (least-privilege
scope). **Framework:** Reversible/Type-2 + Safety-vs-Convenience default bias.
**Bias check:** watch for *false-precision bias* (scoping to `workflows/**`
feels surgical but under-covers `dependabot.yml`/`actions/**`, which are equally
enforcement-bearing supply-chain surfaces); watch for *status-quo bias* (Option
C = do nothing rests on "routing already covers it," which conflates two layers).
The framework's own stated tie-breaker is **integrity > efficiency** and
"always-hardened over-includes a few benign edits but never under-reviews"
(the standalone-YAML and `.gitignore` precedents in `stage-role-map.md`).

**Options:**

- **Option A — deny `.github/**` outright (recommended).** One line, matches the
  Axis-1 `X` set exactly (`.github/**` is already the disqualifier granularity),
  matches the framework's established "over-include benign edits rather than
  under-cover enforcement" posture. Cost: `gleipnir-code` also cannot edit issue
  templates / `CODEOWNERS` — but it has no legitimate job authoring those either
  (they are repo-governance config, not source/tests). Over-inclusion here costs
  essentially nothing because the agent's real job is `src/**` + `tests/**`.

- **Option B — deny only `.github/workflows/**`.** Surgical: blocks CI workflow
  authorship (the specific flagged concern) while leaving the rest of `.github/`
  writable. Cost: under-covers `dependabot.yml` (supply-chain), `actions/**`
  (custom composite actions = executable CI), and `CODEOWNERS` (governs review
  routing) — all enforcement-bearing. Reintroduces a "which `.github/` files are
  enforcement-adjacent?" judgment call, the exact non-determinism the Axis-1 `X`
  set deliberately removed by disqualifying all of `.github/**`.

- **Option C — leave the grant as-is; rely on routing + review + no-push.** Do
  nothing to the capability layer. Rests entirely on the three mitigating layers
  in the Gap section. Defensible (the practical risk *is* substantially
  mitigated), but leaves the capability layer saying more than the role's job
  requires, with no capability backstop if a routing mis-classification ever
  occurs. Status-quo; declines the cheap defense-in-depth.

**Recommendation: Option A.** It is one line, costs the agent no capability it
legitimately needs, aligns the grant granularity exactly with the Axis-1 `X`
set already in force, and follows the framework's own repeatedly-stated
integrity-over-efficiency / over-include-rather-than-under-cover tie-breaker. B's
surgical precision is a *false* economy here — it reintroduces the per-file
judgment call the `X` set exists to eliminate and under-covers real
enforcement-bearing `.github/` files. C is honest about the low practical risk
but declines a near-zero-cost backstop. **This is a recommendation only — the
operator decides A vs B vs C. No convergence has occurred; I have not decided
this.**

## Handoff

**This is a Tier-3 POLICY control; I (a subagent) cannot write it** — every
roster grant, including `gleipnir-code`'s own, denies `.gleipnir/**`. To apply:
the **operator switches to build mode** and (per the operator's A/B/C choice
above) edits the `edit` block in `.gleipnir/agents/gleipnir-code.md` — for the
recommended Option A, add the single line `".github/**": deny` alongside the
existing denies — then commits it via the normal hardened pipeline (this is
itself an enforcement-bearing Tier-3 change and should go through the two-pass
spec-review + negative-check attestation it describes). I do not implement it,
and I do not route it into any layer I can reach.

## Convergence

**CONVERGED: Option A — deny `.github/**` outright. Decided by the operator via the orchestrator's `question` tool (real convergence — not self-attested by this subagent).**

Date: 2026-08-20.

The A/B/C tradeoff writeup in `## Decision Analysis` above is left **intact** as
the record of what was considered; this section records only the resolution. The
earlier "recommendation only / no convergence has occurred" disclaimers in the
Decision Analysis and Handoff sections describe the state *before* this
convergence — they are superseded by this section, not deleted, so the
deliberation record stays honest about how the decision was reached.

**Resolved artifact (Option A):** add the single `deny` line to the `edit` block
in `.gleipnir/agents/gleipnir-code.md`, exactly as written in "Proposed
artifact" above:

```yaml
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    ".github/**": deny
    "src/gleipnir/preflight/**": deny
  read: allow
```

**Still a Tier-3 change I cannot apply.** The Handoff section above remains
correct: this is a Tier-3 POLICY edit to `.gleipnir/agents/gleipnir-code.md`,
which every roster grant (including `gleipnir-code`'s own) denies. The
**operator** — or the mechanism the framework uses for Tier-3 edits under the
uncaged-default operating posture (`decisions/operating-posture.md`, where an
operator-instructed agent may write Tier-3) — applies the actual edit and
commits it via the normal hardened pipeline (this is itself an
enforcement-bearing Tier-3 change and should go through the two-pass spec-review
+ negative-check attestation it describes). I did **not** touch
`.gleipnir/agents/gleipnir-code.md`; that edit is out of scope for this subagent.
