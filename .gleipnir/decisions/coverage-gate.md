# Decision: test coverage gate (two-metric, branch-honest, 85% target)

**Status:** decided (this session). Durable decision record, operator-authored
(Tier-3). Applies to every test run in the framework.

## Why

"N passed" is close to meaningless without coverage: 100% pass at 5% coverage
exercises almost nothing. For a framework whose whole thesis is *fail-closed
edge behaviour*, the coverage that matters is **branch** coverage — a
`NoSuchTransition` / `AttestationNotGreen` / no-CRI-refuse branch that is never
exercised is exactly the hole line coverage hides while looking green.

This was validated the moment it was set: a manual branch analysis (by
`gleipnir-code`, before coverage tooling existed) correctly predicted the exact
uncovered fail-closed branches that `pytest-cov` then confirmed. And on first
in-container run the gate immediately flagged a freshly-written CLI at 0%.

## The rule

1. **Two metrics, always.** Every test run surfaces BOTH the pass rate AND the
   coverage %. Neither alone is sufficient.
2. **Line + branch, branch authoritative.** Coverage is measured with
   `--cov-branch`; branch coverage is the meaningful number.
3. **85% target.** It is a *target*, always *reported*; anything **below 85%**
   must be **justified** by the code/test agents (in the delegation report or a
   recorded note). It is **not yet a hard fail** — soft during bootstrap.
4. **Hardens later.** This graduates into a **C-2 CI hard gate** (a coverage
   job that fails the build below threshold) once the conformance harness runs.
   Until then it is reported-and-justified.
5. **The quality stage drives it.** The post-implementation adversarial review
   (`quality-reviewer`) strives to push coverage as high as possible and must
   surface branch-coverage gaps, not just accept a green pass count.

## Mechanism

The S-2 sandbox entrypoint `bin/gleipnir-sandbox test` runs pytest with
`--cov=src/gleipnir --cov-branch --cov-report=term-missing`, so coverage is a
first-class output of the one command agents use to test. `pytest-cov` ships in
the sandbox image (dev tooling, not a runtime dependency).

## Current standing (at decision time)

Full suite: 154 passed, **93% total** (line+branch), in-container. Below-target
file on record: `src/gleipnir/verify/__main__.py` at **83%** (the G-3.1 CLI;
missing lines are error-branch / `__main__` guard paths) — flagged for a
follow-up test or a recorded justification. All other modules ≥90%.
