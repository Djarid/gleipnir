# Candidate Lessons (pre-graduation, awaiting review)

**Status:** CANDIDATE. Tier-2 (USER_REVIEWED) content, but written before the
G-4c review-gated pipeline exists. These are *observed* lessons from build
sessions, recorded honestly for later human review + graduation. They are not
yet enforced guardrails. Under G-4c a candidate graduates only if it fires on a
real event, is associated with a measured reduction in the failure it targets,
and stays under a false-positive threshold — none of that measurement exists
yet, so treat these as proposals.

---

## L-C1 — Deferring the substrate is fine until an agent must EXECUTE code; then it is the critical path

**Observed (session 02–03):** verification dead-ended three times in a row —
couldn't run the full suite, couldn't run new tests, couldn't measure
coverage — and each dead-end was the same root cause: the S-2 sandbox wasn't
built. We had *decided* the container substrate (D-4) but kept executing on the
host. The moment agents needed to run arbitrary (test) code, the missing
sandbox became the blocker, and everything resolved at once when it was built.

**Proposed lesson:** the S-2 execution substrate is not "a later step" once any
agent needs to run build/test/lint — at that point it is on the critical path,
because host execution of agent-authored code is precisely the unbounded blast
radius G-2/T-6 remove. Build the sandbox before, not after, the first agent
needs to execute code it wrote.

## L-C2 — "N passed" without coverage is not evidence; branch coverage is the honest arbiter

**Observed:** a manual branch analysis (by the code agent, before coverage
tooling existed) correctly predicted the exact uncovered fail-closed branches
that pytest-cov later confirmed; and the first in-container coverage run
immediately flagged a freshly-written CLI at 0% that "154 passed" had hidden.

**Proposed lesson:** report pass rate AND line+branch coverage on every run;
branch is authoritative for a fail-closed codebase. A green pass count over low
branch coverage means the failure paths — the whole point — are untested. (Now
recorded as the coverage gate, `../decisions/coverage-gate.md`.)

## L-C3 — Delegate minimum-scope TASKS, not GOALS

**Observed (session 03):** a goal-shaped implementation delegation ("make it all
pass, iterate, figure out how to run tests") made the subagent spend effort
fighting its own capability boundary. Minimum-scope tasks (one verb/object/
boundary, exploration separate from action) did not.

**Proposed lesson:** the orchestrator emits one verb, one object, one
verification, one boundary per delegation; exploration and action are separate
delegations. A goal-shaped delegation pushes sequencing/judgment into the
subagent — the exact drift G-5 removes at the joint.

## L-C4 — Subagent delegations sometimes return empty AND/OR do no work; always verify against disk

**Observed (session 03, ~5 times):** `gleipnir-code`/`gleipnir-plan` delegations
frequently returned an empty final message despite having done the work
(files on disk changed) — and at least once completed while doing NO work (no
files changed). Trusting the return value would have been wrong in both
directions.

**Proposed lesson (operational):** never trust a delegation's self-report;
verify the result against disk (files changed, tests green, coverage) before
marking a task done. This is the inherited GOTCHA guardrail "verify subagent
outputs against inputs" confirmed by repeated real occurrence. Candidate for a
structural fix: a post-delegation verification step the orchestrator always
runs.

## L-C5 — The scope-boundary reflex: recognise "outside the boundary by design" vs "a hole to close"

**Observed (earlier sessions, recorded in the v0.3.4/0.3.6 spec history):** the
recurring over-reach was defaulting to "close the hole" when the sound move was
"recognise this is outside the boundary by design" — nearly caging the
operator's escape hatch; nearly making the human merge decision the framework's
concern.

**Proposed lesson:** before caging something, ask whether it is an in-framework
agent action (bind it) or an operator/human action outside the framework
(out of scope by design). The framework binds agents acting within it; it makes
no claim on the operator's choices. (Now in the spec's Part 0 scope clause.)

## L-C6 — A subagent's `question` cannot reach the operator; human-decision gates must live at the orchestrator

**Observed (this session):** the decision-surfacing gate we built to fix
"material decisions never reach the operator" had that exact bug INSIDE it.
`gleipnir-brainstorm` is a subagent; its `question` tool surfaces only within
its own sub-session, never to the operator. So it "converged with itself" and
reported a decision the operator never made — self-attestation, the precise
failure the framework exists to prevent, appearing in the human-decision gate.
If trusted, a Tier-3 durable decision would have enshrined a choice the human
never took.

**Proposed lesson:** only a primary agent (the orchestrator) can reach the
operator; subagents cannot. Human-decision gates must therefore be surfaced BY
the orchestrator, with subagents producing ANALYSIS the orchestrator surfaces —
never a subagent claiming a convergence it structurally cannot obtain. Fixed
structurally in commit 634a81c: convergence is orchestrator-surfaced and the
brainstorm subagent's `question` is denied by capability (not merely
instruction).

## L-C7 — The review gates catch latent defects that no author and no plan caught

**Observed (this session):** the spec-review and quality gates repeatedly caught
real defects nothing upstream did — a vanity-metric framing (spec-review on the
ledger), a latent `ESCALATED`-index crash before a line of code was written
(spec-review on the engine), and most strikingly a CARDINAL false-CLOSED plus
TWO residual variants of it in the G-1 boundary preflight (three quality
rounds), each a genuine way the guard could falsely report "closed."

**Proposed lesson:** for a guard whose failure mode is a false SUCCESS (a false
"closed", a fabricated metric, a "passed" that didn't), adversarial multi-round
review is not overhead — it is the mechanism that finds the false-success paths,
because they are invisible to a green test count. Weight review effort by blast
radius: security/evidence boundaries warrant multiple adversarial rounds.

## L-C8 — A reviewer must refuse to fabricate evidence it cannot obtain

**Observed (this session):** asked to run `make test` and report the result, the
quality-reviewer correctly REFUSED — its own permission floor is `bash: deny` —
rather than invent a pass/coverage number, and routed execution to the role
holding the `bin/gleipnir-sandbox test` grant, requiring the raw output be
attached before sign-off. Separately, a `gleipnir-plan` subagent refused a write
task routed to it above its tier rather than fabricate a persistence it could
not perform.

**Proposed lesson:** a reviewer that fabricates a "tests pass" it did not
observe — or an agent that reports a write it did not perform — is the exact
false-positive the guard exists to prevent. Verification evidence must come from
the capability holder and be attached; an agent without the capability reports
that honestly rather than guessing. Anti-self-attestation applied to the guards
themselves.

## L-C9 — Sequencing/action separation is real, and enforced by tier, not honour

**Observed (this session):** the orchestrator role must delegate action, not
perform it (it holds no git/edit/bash) — fixes go to `gleipnir-code`, commits to
`git-ops`, each within capability, and the git holder flagged an unexpected
untracked file rather than silently staging it. Separately, routing a Tier-2/
Tier-3 WRITE to a roster subagent failed by capability: no roster agent can
write `lessons/` or `decisions/`; only the operator's built-in escape-hatch
agent (running as the operator, outside the framework floor) can. Two roster
agents in a row correctly refused writes above their tier.

**Proposed lesson:** the tier boundary is structural, not advisory — the writer
of each tier is fixed (Tier-0 bounded agents; Tier-2 review pipeline; Tier-3
operator only), and an agent asked to write above its tier refuses by absence of
capability. The sequencing role must not hold action capabilities; the escape
hatch that writes POLICY is the operator's built-in agent, never a roster role.
This is G-5's separation-of-sequencing-from-action and G-6's memory-tier writers
confirmed by the runtime refusing the wrong-writer path.

## L-C10 — The pipeline needs a reachable Tier-3/operator writer; the orchestrator must diagnose "no reachable writer," never bounce work to the human

**Observed (this session):** a slice legitimately needed a Tier-3 artifact created *within* a pipeline run (a self-host `.gleipnir/sandbox/profiles.toml`, and durable decision records). But the orchestrator's `task` allowlist covered only the seven roster agents, and ALL of them deny Tier-3 `.gleipnir/**` writes by design (G-6). So there was NO actor the orchestrator could reach to write Tier-3 — a structural dead-end. The orchestrator (correctly holding no write/edit/bash of its own — that IS its floor) repeatedly mis-attributed this as "the operator should author it by hand," bouncing the work to the human four times before diagnosing the real gap. The fix was to grant the orchestrator `task: general: allow` (with explicit per-use human permission) so operator/Tier-3 artifacts route to an unbound `/general` worker.

**Proposed lesson:** the orchestrator never writes or executes (that is its correct capability floor); when a task needs work no roster agent can do (notably a Tier-3/operator-authored artifact), the honest move is to delegate to an unbound worker (`/general`, gated by explicit operator permission per use) — NOT to hand the work to the human out of band. A framework whose pipeline has no reachable writer for a tier it legitimately must produce has a capability gap, not a human-labour requirement. Two corollaries observed the same session: (a) the build caught a CIRCULAR DEPENDENCY — the framework's own test entrypoint was made to require a Tier-3 config file that no pipeline actor could create, bricking `make test` until it existed; dogfooding surfaced it before commit. (b) `git-ops`'s allowlist lacks `git diff`/`git log`, so read-only commit inspection isn't possible through the broker — a minor capability gap worth closing.

---

## L-C11 — A hunk-split commit delegation can DESTROY uncommitted work; stage-by-path is safe, interactive `git add -p` is not (for an agent)

**Observed (this session):** the orchestrator delegated a three-commit,
hunk-split commit to `git-ops` (splitting three files whose diffs spanned
features, via interactive `git add -p`). The subagent hit its step cap
mid-split and, in the process, **12 already-tracked files were reverted to
their last-committed state** — every in-place edit made that session to an
existing file was lost (untracked *new* files survived; HEAD never moved; no
stash; not recoverable from git objects or opencode snapshots). Recovery was
possible only because the edits were all documented in surviving decision
records/plans and could be rebuilt by hand — an hour of avoidable rework, and
had they been undocumented, permanent loss.

**Proposed lesson:** (a) **Never route an interactive/`-p` hunk-split through an
agent with a step cap** — a partial `git add -p` session interleaved with other
git state manipulation is a data-loss hazard, not just a failed task. (b)
Prefer **commit-by-whole-path** (`git add <path>`); when hunk-splitting is truly
wanted, pre-split with **patch files** (`git diff > x.patch` → `git apply
--cached`) authored by the orchestrator, so the broker only runs mechanical,
idempotent staging — never destructive interactive editing. (c) **Commit early**:
a large body of uncommitted, entangled work is itself the risk; had the node
profile + context-cap-unset been committed when done, the blast radius of the
failed split would have been one feature, not three. (d) The broker should
**never discard working-tree edits as a side effect of staging** — a real
`git-ops` safety property to build (refuse `checkout --`/`restore`/`reset --hard`
against a dirty tree; treat the working tree as append-only during a commit
task). Corollary to L-C4: verify against disk after EVERY git delegation, not
just code ones.

---

## L-C12 — `permission.tools` takes allow/deny/ask; top-level `tools` takes true/false — mixing them fails config validation at restart

**Observed (this session):** the broker MCP wiring granted each single-holder
its tool namespace with `permission.tools: { "gleipnir-git*": true }` in the
agent frontmatter. opencode **failed to start** — config validation rejected it
(`Expected PermissionActionConfig, got true`). Two different keys with two
different value grammars were conflated:

| Key | Valid values |
|---|---|
| `tools:` (top-level, in opencode.jsonc) | `true` / `false` |
| `permission.tools:` (agent frontmatter) | `allow` / `deny` / `ask` |
| `permission.{edit,write,bash,...}:` | `allow` / `deny` / `ask` |

The value-grammar rule: booleans ONLY under top-level `tools`; `allow/deny/ask`
everywhere under `permission`. The bug used `true` where `allow` was required.
(NOTE: the mechanism this entry originally recommended — "disable globally then
re-enable the one holder with `permission.tools: allow`" — was subsequently
DISPROVEN; see L-C12b. The correct single-holder mechanism is the deny-list in
L-C12b, not global-disable-then-allow.)

**Proposed lesson:** (a) config edits that only take effect at restart are
**unverifiable from inside the running session** — a whole class of "authored,
looks right, breaks on load" bugs (cf. the context-cap alias). Where possible,
**validate the config against opencode's schema before declaring done** (e.g. a
schema check in a preflight/CI step), rather than discovering it at the operator's
next restart. (b) Remember the grammar split: booleans only under top-level
`tools`; `allow/deny/ask` everywhere under `permission`. (c) This is a candidate
for a cheap automated guard — a lint that flags a boolean under any
`permission.*` key in an agent file.

---

## L-C12b — Single-holder MCP scoping is a DENY-LIST (enable globally, deny per-agent); global-disable does NOT re-enable for a subagent

**Observed (this session):** after fixing L-C12's boolean bug, the broker MCP
tools *connected* (opencode `mcp list` showed both servers green) but the
`git-ops` **subagent still could not see** its `commit_changes`/`push_current_branch`
tools — they were absent from its function list. Root cause: the wiring used a
top-level `tools: { "gleipnir-git*": false }` **global disable** and tried to
re-enable it for the one holder via `permission.tools: { ...: allow }`. That
re-enable does NOT surface a globally-disabled MCP tool to a *subagent*. The
working pattern (AETOS, `../aetos/opencode.json`): **enable MCP tools globally
(no top-level disable), and have each agent DENY the namespaces it must not
hold.** git-ops denies `gleipnir-pm_*` (keeps git); project-mgr denies
`gleipnir-git_*` (keeps pm); every other agent denies BOTH. Net effect is the
same single-holder guarantee, but it actually works.

**The scoping goes in the TOP-LEVEL `tools:` frontmatter key with BOOLEAN values
(`false` = deny), NOT `permission.tools`.** Verified live this session: a
`permission.tools: {gleipnir-pm_*: deny}` on git-ops did NOT block the pm tools
(git-ops could still see and call them); moving it to a top-level `tools:
{gleipnir-pm_*: false}` (the AETOS form, `../aetos/opencode.json` git-ops) is
what actually denies. So the two-grammar rule from L-C12 has a THIRD facet: MCP
per-agent tool visibility is controlled ONLY by the top-level `tools:` booleans
(both in opencode.jsonc `agent.<name>.tools` and in a frontmatter agent's
top-level `tools:` key) — `permission.tools` does not gate MCP tool visibility
for a subagent at all.

**Proposed lesson:** (a) For per-agent MCP scoping use the **deny-list**
(enabled-by-default, deny-what-you-shouldn't-hold) via the **top-level `tools:`
key with booleans** — NOT global-disable, NOT `permission.tools`. (b) MCP tool
names are `<server>_<tool>`; the namespace glob therefore needs the
**underscore** form `gleipnir-git_*`, not `gleipnir-git*`.
(c) **A newly-added deny-list is a fail-OPEN change**: enabling tools globally
means every agent that isn't explicitly denied silently GAINS them — the review
that caught quality-reviewer/session-scribe missing their deny-lines (they'd
have gained commit/push + issue tools on restart) shows why the whole roster,
not just the two holders, must be checked when adding a globally-enabled MCP.
(d) Reinforces L-C12(a): this was again only observable at restart — a
schema/scoping preflight that enumerates each agent's effective tool set would
have caught both the non-visibility and the fail-open exposure before restart.

---

## L-C13 — The "empty return" is a no-trailing-text failure, not a step cap; fix it with a standing "end with a written report" rule in every subagent file

**Observed (this + an earlier session):** subagent delegations repeatedly
returned with **zero text** — `quality-reviewer` on a plan/implementation review,
`gleipnir-code` on a test-writing task, `gleipnir-plan` mid-plan-write. L-C4
recorded the *symptom* ("verify against disk"). The **root cause**, isolated this
session: the agent's LAST action in the turn was a tool call (a `read`, an
`edit`, a `git` call) with no concluding prose, so the harness surfaced an empty
result — the work often HAD landed on disk, but was invisible to the
orchestrator. This is distinct from a step-cap exhaustion (which narrates
"reached the maximum step limit" and is fixed by raising `steps`, cf. L-C11 /
the git-ops 15→30 bump). Two different failures with two different fixes; don't
conflate them.

**Evidence it's a discipline issue, not a resource one:** the one time an ad-hoc
"end with a written summary report — do not return empty" line was added to a
`gleipnir-code` delegation prompt, that task returned a full report immediately.
The fix generalises that: a standing **"Always end with a written report (never
return empty)"** section was added to ALL 8 subagent files (quality-reviewer,
gleipnir-code, gleipnir-plan, gleipnir-brainstorm, git-ops, project-mgr, notify,
session-scribe), each tailored to that role's output (verdict; files+coverage;
plan path; decision analysis; commit/push result; issue id; delivery outcome;
diff summary), and each saying: if low on steps, STOP and write the report with
what you have.

**Proposed lesson:** (a) A subagent's turn must never end on a bare tool call —
the concluding text IS the return value; without it the work is lost to the
pipeline regardless of what hit disk. Bake this into the agent template, not
per-delegation prompts. (b) Keep L-C4's "verify against disk after every
delegation" as the orchestrator-side backstop — belt and braces. (c) This is a
candidate for a cheap automated guard: detect a subagent turn whose final event
is a tool call with no trailing text and flag/re-prompt it. (d) Note the fix is
restart-gated like all agent-file changes — takes effect next session.

---

## L-C14 — The plan-format's decisions-index table is not enforced, so it gets dropped until the operator catches it

**Observed (this session):** three plans (`interactive-session-context-cap.md`, `broker-mcp.md`, `config-scoping-preflight.md`) were completed, spec-reviewed, and treated as "done" without the scannable `## Decisions (index)` table that summarizes every decision the plan fixes — added only retroactively when the operator asked "what about the score cards... there is usually a table of decisions." Each retrofit was accurate and cheap, but the table was absent the first time in every case. The pattern also recurred for methodology itself (running brainstorm/ATLAS was skipped or truncated twice this session and caught by the operator, not the process) — a common root: a good practice that lives only in intent/habit, not in an enforced artifact, silently erodes.

**Proposed lesson:** bake the `## Decisions (index)` table into `goals/plan-format.md` as a REQUIRED section (columns: # | Decision | Chosen | Rejected | Rationale), so `gleipnir-plan` authors it the first time rather than the operator retrofitting it. More broadly: when a repeatedly-dropped good practice is identified, the durable fix is to move it from "orchestrator/planner remembers to do it" into the enforced plan-format/agent-instruction layer — the same principle L-C13 applied to the empty-return discipline and this escalation feature applied to lesson-capture itself.

_Provenance: reviewed_by operator (via question, this session) · date 2026-07-30 · session current · interim gate — substitutes for the not-yet-built G-4c review-gated pipeline; this is a CANDIDATE, not a graduated lesson._

---

## Note on placement

`lessons/` is Tier-2 USER_REVIEWED. Per G-6 the proper path for entries is the
review-gated memory-write pipeline (receive → classify → validate → human-diff
review → audit+probe), which is not built yet. This file is therefore a
*candidate* set authored via the operator escape hatch, explicitly pre-review,
so the observations are not lost. When the pipeline and G-4c graduation exist,
these should flow through it with provenance and measured graduation, not remain
as free-written text.
