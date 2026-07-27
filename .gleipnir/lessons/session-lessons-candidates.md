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

---

## Note on placement

`lessons/` is Tier-2 USER_REVIEWED. Per G-6 the proper path for entries is the
review-gated memory-write pipeline (receive → classify → validate → human-diff
review → audit+probe), which is not built yet. This file is therefore a
*candidate* set authored via the operator escape hatch, explicitly pre-review,
so the observations are not lost. When the pipeline and G-4c graduation exist,
these should flow through it with provenance and measured graduation, not remain
as free-written text.
