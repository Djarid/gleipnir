# ATLAS Stress-test — Session 01 Validation Report

Validates what session 01 produced against `session-01-atlas-brief.md`. This is
the ATLAS S-step run retroactively. Method: check each Architect success
criterion and each Trace edge case against the artifacts on disk; record pass /
fail; fix fails.

## Success criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Six deny-by-default agents bound to pipeline | PASS | 6 agent files, 1 primary + 5 subagent, all with permission maps |
| 2 | GOTCHA/ATLAS amended, layer-2 resolved, K-2.1 in spec | PASS | K-2.1 present in v0.3.9; skills carry `[GLEIPNIR A1/A2]` markers |
| 3 | D-1/D-4 resolved with config load path fixed | PASS | both "Resolved (v0.3.9)" in register; load path mount-side |
| 4 | G-3.1 implemented, conformance tests pass | PASS | 20/20 tests green incl. forge/mutate/red-run cases |
| 5 | Honest "authored, not yet closed" labelling | **FAIL (fixed)** | guard-status table under-claimed G-3 after G-3.1 shipped |
| 6 | Models right-sized to goal | PASS | opus@plan, sonnet@code/test/review, haiku@git/pm/notify |

## Edge cases (Trace)

| Edge case | Covered? | Evidence |
|---|---|---|
| Agent fabricates marker (no key) | PASS | `test_agent_fabricated_marker_fails` |
| One-byte tree change post-mint | PASS | `test_one_byte_mutation_invalidates` |
| Red test run | PASS | `test_verify_red_mints_nothing` |
| Missing/stale/wrong-version marker | PASS | `test_check_missing_marker_fails_closed`, stale/version tests |
| `.gleipnir/` tree-side = G-1 fail acknowledged | PASS | substrate doc + register closure obligation |
| No goals manifest (K-1 empty) named as gap | **FAIL (fixed)** | not previously named; pre-flight now records it |

## Discrepancies found and fixed

1. **Stale spec-version reference.** `plans/step-0-scaffold.md` said "spec
   (v0.3.7)"; canonical is now v0.3.9. → generalised to avoid version drift.
2. **Incomplete see-also pointer.** `AGENTS.md` pointed only to
   `step-0-scaffold.md`; the substrate pass and this brief/validation now exist.
   → pointer expanded to the plans directory.
3. **Stale guard-status row (the important one).** `AGENTS.md` guard-status
   table still showed G-3 as "Orchestrator instructed not to self-declare done"
   with "HMAC marker key (G-3.1)" listed as *not yet real*. G-3.1 is now built
   and tested. → row updated to reflect G-3.1 shipped (mechanism real; key
   boundary-enforcement still pending S-2), G-3.2 still pending.
4. **Unnamed goals-manifest gap.** GOTCHA pre-flight expects a goals manifest;
   `.gleipnir/goals/` is empty (K-1 unbuilt). → named as a known gap in the
   pre-flight record and here, not silently skipped.

## Methodology-process finding (the meta-point)

The original session used opencode's todo tool and wrote plan files as records,
but did not run ATLAS Architect/Trace *before* building, nor output the GOTCHA
pre-flight checklist. At the current pre-engine stage the orchestrator is
necessarily a prose sequencer (the G-5 engine that would drive this
deterministically is build-order step 3, unbuilt), so some prose orchestration
is unavoidable now — but the ATLAS brief-to-disk and GOTCHA pre-flight
disciplines were available and were skipped. This retroactive pass closes that
for session 01; going forward the brief precedes code.

## Verdict

All acceptance criteria pass after the four fixes. No functional defect was
found in the G-3.1 code (tests were already green); the discrepancies were
documentation-consistency and honesty-labelling drift — exactly what the
GOTCHA consistency checklist exists to catch.
