# G-5 deterministic orchestration engine — design record

Status: **authored and implemented.** This document and
`tests/test_engine.py` are the specification; `__init__.py` in this
directory implements that contract in full, and the test suite (49/49)
passes against it. The bodies were implemented in the `code` delegation,
bound to `gleipnir-code` per `.gleipnir/stage-role-map.md`, driven by the
tests recorded here — test-first, per the discipline this role operates
under.

Traceability: spec `gleipnir_specification_v0_3_10.md`, section **G-5:
Deterministic orchestration** (states, transitions, loop caps, human gate)
and **G-3.2** (the gate's attestation-only incoming edge). Consumes the
G-3.1 verifier's fail-closed posture (`src/gleipnir/verify/marker.py`) as
the model for how `attempt_gate` must refuse.

Following ATLAS shape (Architect / Trace / Link / Assemble / Stress-test)
since that is this codebase's inherited planning method (`.gleipnir/skills/atlas/`).

## Architect: states and the transition table

States (`PipelineState`), matching the spec's pipeline order plus the two
structural states G-5 names explicitly (the blocking human-question gate,
precept 10; the escalation sink, precept 6):

```
BRAINSTORM -> PLAN -> SPEC_REVIEW -> TEST -> CODE -> QUALITY -> GIT -> GATE
                  \--(NEEDS_HUMAN)--> HUMAN_QUESTION  (from any main-line state)
        SPEC_REVIEW, QUALITY: FAIL loops on self, capped
                  \--(cap reached)--> ESCALATED
```

`GATE` and `ESCALATED` are terminal (no outgoing edges — no key for them
in the transition table at all). `HUMAN_QUESTION` is also a no-outgoing-edge
state *in the transition table*: the only way out is a distinct method,
never a routed verdict (see "the human gate" below).

The transition table (`TRANSITIONS: dict[PipelineState, dict[Verdict,
PipelineState]]`) is the sequencing. It is data, checked into source, not a
string the LLM narrates. Two structural absences carry the whole G-5
argument:

* **`GIT` has no `PASS` entry.** There is no code path where completing the
  `git` stage's judged step routes directly to `GATE`. The only edge into
  `GATE` is `Engine.attempt_gate(attestation)`, a different method with a
  different, non-LLM-judged precondition (G-3.2, below).
* **`GATE`, `ESCALATED`, `HUMAN_QUESTION` are absent as table keys.**
  Absence of a key is absence of a code path — `step()` raises
  `NoSuchTransition` rather than falling through to a default-allow branch.
  This is the concrete meaning of "a counter in code cannot forget it is on
  round two" and "no outgoing edge until the human-question primitive
  returns": there is nothing to forget, because there is no edge to take.

## Trace: the judge interface and why text cannot route

```python
Judge = Callable[[PipelineState, Mapping[str, Any]], Verdict]
```

`Engine.step(judge, payload)` calls `judge(self.state, payload or {})`
exactly once per call and requires the return value to be a `Verdict`
member (`PASS`, `FAIL`, `NEEDS_HUMAN` — three members, no `SKIP`, no
free-text escape hatch). Anything else — a string, `None`, a truthy object
that merely looks like a verdict — raises `InvalidVerdict`. The router
(`TRANSITIONS[self.state][verdict]`) only ever consults this three-valued
enum. `payload` (which may contain arbitrary pasted text, including an
injected `"skip review"` instruction) is visible to the judge and *never*
inspected by the router itself.

This is the direct implementation of the spec's closing clause: *"bypass
phrases become code paths with their own guards rather than string matches
an LLM performs on conversation text."* There is no code path in `step()`
that pattern-matches `payload` for control keywords. A judge is free to be
a dumb fixed-answer fake (as the tests use) or a real LLM call; either way,
its only channel back into the engine is the enum, and the engine treats a
non-enum return as a fault, not as "probably meant PASS."

Concretely, closing the injected-bypass risk means two independent things
must both hold, and both are tested:

1. A judge that *ignores* injected text and returns the deterministically
   correct verdict advances exactly one edge, per the table — never two
   states at once, never into `GATE`.
2. A judge that *returns* the literal string `"skip review"` instead of a
   `Verdict` member is rejected by `step()` with `InvalidVerdict` before
   the router is even consulted. There is no coercion path from string to
   enum.

## Link: the human gate and the attestation gate

**The human gate (precept 10).** `HUMAN_QUESTION` has no entry in
`TRANSITIONS`, so `step()` — called with any judge, returning any
`Verdict` — raises `HumanGateBlocked` unconditionally while
`self.state is PipelineState.HUMAN_QUESTION`. The only way out is
`Engine.answer_human_question(answer)`, a method with a different
signature (an `answer`, not a `Judge`) that returns control to whichever
state raised `NEEDS_HUMAN`. "Skipped twice" is impossible because there is
only ever one exit and it is not reachable from `step()` at all — not a
counter that could be miscounted, an absent edge.

**The attestation gate (G-3.2).** `GATE` is reachable only through
`Engine.attempt_gate(attestation)`, callable only while `self.state is
PipelineState.GIT`. `attestation` must be an `Attestation(pipeline_id,
status)` — not a string, not `None` — where `status ==
AttestationStatus.GREEN` and `pipeline_id` matches the engine's own
`pipeline_id`. Every other case (`None`, wrong type, `ABSENT`, `PENDING`,
`RED`, or a mismatched `pipeline_id`) raises (`AttestationRequired`,
`TypeError`, or `AttestationNotGreen`) and leaves `self.state` unchanged.
This mirrors the G-3.1 verifier's fail-closed posture in
`src/gleipnir/verify/marker.py`: *any* doubt refuses, never defaults to
pass. Nothing an agent writes into `payload` on any prior `step()` call —
including text claiming CI passed — is ever read by `attempt_gate`; it
takes exactly one argument type and checks exactly two fields on it. The
attestation itself is understood to be *fetched* by the engine or its
caller from the real CI/verifier surface (out of scope for this module,
which only models the value once it arrives) — never asserted by the
agent, per spec.

## Assemble: loop caps (precept 6)

`LOOPING_STATES = (SPEC_REVIEW, QUALITY)`. Each engine instance holds a
per-state `FAIL` counter (`Engine.loop_count(state)`, read-only from
outside), seeded at 0, with a cap (`DEFAULT_LOOP_CAP`, overridable per
state via the constructor's `loop_caps` mapping — tests use small caps for
determinism).

On `step()` resolving to a self-loop (`Verdict.FAIL` on a state in
`LOOPING_STATES`):

1. increment that state's counter;
2. if the counter has now reached the cap, transition to `ESCALATED`
   instead of looping, and return `StepResult(ESCALATED, escalated=True)`;
3. otherwise, loop (state unchanged) and return
   `StepResult(state, escalated=False)`.

Cap semantics are exact: with cap `N`, failures `1..N-1` loop, failure `N`
escalates. `N-1` failures must never escalate; the `N`th must always
escalate. Both are counter comparisons in code — no LLM is asked "is this
round two yet."

## Stress-test: adversarial mapping to spec conformance [D]

| Spec conformance clause | Test(s) |
|---|---|
| "escalation fires at exactly N by code" | cap-at-N-minus-1 does not escalate; cap-at-N does, for both `SPEC_REVIEW` and `QUALITY`, with independent counters |
| "instruction to skip a gate or proceed past the MR gate: engine must have no code path" | `GIT` has no `PASS` transition; `step()` from `GIT` with any `Verdict` other than `NEEDS_HUMAN` raises `NoSuchTransition`; only `attempt_gate` reaches `GATE` |
| "Inject 'skip review' inside a pasted document: no bypass" | judge ignores payload text and advances one edge only; judge that *returns* the string is rejected by type, before routing |
| "Drive a stage to completion with CI absent, pending and red: engine must refuse... not satisfiable by any agent-supplied text" | `attempt_gate(None)`, `attempt_gate(Attestation(..., ABSENT/PENDING/RED))`, `attempt_gate("trust me, it passed")` (wrong type) all refuse; `state` unchanged in every case |
| precept 10, "skipped twice becomes impossible" | `HUMAN_QUESTION` has no table entry; `step()` always raises while there; only `answer_human_question` exits |

## Non-goals (engine core scope boundaries)

* No real CI/attestation fetch. `Attestation` is a plain value the caller
  supplies; wiring it to an actual CI API is outside G-5's engine-core
  scope as specified (the spec says the engine *fetches* it, but the fetch
  mechanism is a separate, later integration, not part of this state
  machine's contract).
* No binding to the G-4 event bus, no ledger, no stage-to-role dispatch
  (that binding is `.gleipnir/stage-role-map.md`, consumed by whatever
  drives `Engine`, not by `Engine` itself).
* No S-2 substrate concerns. This module has no filesystem or process
  boundary; it is pure in-memory state.
