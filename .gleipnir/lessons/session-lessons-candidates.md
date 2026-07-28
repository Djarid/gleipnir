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

## Note on placement

`lessons/` is Tier-2 USER_REVIEWED. Per G-6 the proper path for entries is the
review-gated memory-write pipeline (receive → classify → validate → human-diff
review → audit+probe), which is not built yet. This file is therefore a
*candidate* set authored via the operator escape hatch, explicitly pre-review,
so the observations are not lost. When the pipeline and G-4c graduation exist,
these should flow through it with provenance and measured graduation, not remain
as free-written text.
