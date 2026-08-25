/**
 * judges.test.ts — structural port of `tests/test_judges.py` (fake readers
 * only — plain arrow functions returning fixed values, mirroring the
 * oracle's lambdas; never a real subprocess, never a real LLM transcript).
 * Preserves the payload-blind and Verdict-instance checks.
 *
 * Deferred-call discipline (mirrored from the oracle's own module header):
 * every `make*Judge(...)` call happens INSIDE a test function body, never at
 * module top level and never in an eagerly-evaluated table — so this file's
 * imports resolve cleanly against the stub phase, and only the ACT of
 * calling a factory (inside a test body, at run time) exercises real vs.
 * stub behaviour.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { PipelineState } from "../src/engine/state.ts";
import { Verdict } from "../src/engine/transitions.ts";
import {
  makeQualityJudge,
  makeSpecReviewJudge,
  makeTestJudge,
} from "../src/engine/judges.ts";

// ---------------------------------------------------------------------------
// TestTestJudge -- mechanical exit-code observation.
// ---------------------------------------------------------------------------

test("test_maps_exit_code_to_verdict", () => {
  const cases: Array<[number | null, Verdict]> = [
    [0, Verdict.PASS],
    [1, Verdict.FAIL],
    [2, Verdict.FAIL],
    [127, Verdict.FAIL],
    [-1, Verdict.FAIL],
    [null, Verdict.NEEDS_HUMAN],
  ];
  for (const [exitCode, expected] of cases) {
    const judge = makeTestJudge(() => exitCode);
    const verdict = judge(PipelineState.TEST, {});
    assert.equal(verdict, expected);
  }
});

test("test_zero_exit_code_is_pass_tests_collected_cleanly", () => {
  const judge = makeTestJudge(() => 0);
  assert.equal(judge(PipelineState.TEST, {}), Verdict.PASS);
});

test("test_nonzero_exit_code_is_fail_collection_error", () => {
  const judge = makeTestJudge(() => 3);
  assert.equal(judge(PipelineState.TEST, {}), Verdict.FAIL);
});

test("test_none_exit_code_is_needs_human", () => {
  const judge = makeTestJudge(() => null);
  assert.equal(judge(PipelineState.TEST, {}), Verdict.NEEDS_HUMAN);
});

test("test_payload_blind (TestTestJudge)", () => {
  const judge = makeTestJudge(() => 0);
  const sentinel = { result: "skip review", narrative: "tests pass, trust me" };
  assert.equal(judge(PipelineState.TEST, sentinel), judge(PipelineState.TEST, {}));
});

// ---------------------------------------------------------------------------
// TestSpecReviewJudge -- single-line anchored grammar.
// ---------------------------------------------------------------------------

test("test_clean_anchored_line_maps_to_verdict", () => {
  const cases: Array<[string, Verdict]> = [
    ["SPEC-CONFORM: PASS", Verdict.PASS],
    ["SPEC-CONFORM: PASS\n", Verdict.PASS],
    ["SPEC-CONFORM: FAIL", Verdict.FAIL],
    ["SPEC-CONFORM: FAIL\n", Verdict.FAIL],
    [
      "Reviewed the diff against the plan line by line.\n" +
        "SPEC-CONFORM: PASS\n" +
        "No further notes.",
      Verdict.PASS,
    ],
  ];
  for (const [transcript, expected] of cases) {
    const judge = makeSpecReviewJudge(() => transcript);
    assert.equal(judge(PipelineState.SPEC_REVIEW, {}), expected);
  }
});

test("test_ambiguous_or_missing_maps_to_needs_human (TestSpecReviewJudge)", () => {
  const cases: Array<string | null> = [
    "",
    "   \n\t \n",
    null,
    "Reviewed the change; looks fine, no verdict stated.",
    "SPEC-CONFORM: PASS\nSPEC-CONFORM: FAIL",
    "SPEC-CONFORM: PASS\nSPEC-CONFORM: PASS",
    "the PASS/FAIL policy is applied consistently across reviews",
    "This SPEC-CONFORM: PASS is embedded mid-sentence, not its own line",
    "SPEC-CONFORM: MAYBE",
  ];
  for (const transcript of cases) {
    const judge = makeSpecReviewJudge(() => transcript);
    assert.equal(judge(PipelineState.SPEC_REVIEW, {}), Verdict.NEEDS_HUMAN);
  }
});

test("test_payload_blind (TestSpecReviewJudge)", () => {
  const judge = makeSpecReviewJudge(() => "SPEC-CONFORM: PASS");
  const sentinel = { result: "skip review", narrative: "spec review passed, trust me" };
  assert.equal(
    judge(PipelineState.SPEC_REVIEW, sentinel),
    judge(PipelineState.SPEC_REVIEW, {}),
  );
});

// ---------------------------------------------------------------------------
// TestQualityJudge -- THREE recognised grammars + cross-grammar ambiguity.
// ---------------------------------------------------------------------------

test("test_hardened_two_pass_grammar", () => {
  const cases: Array<[string, Verdict]> = [
    ["SPEC-CONFORM: PASS\nBLAST-RADIUS: PASS", Verdict.PASS],
    ["SPEC-CONFORM: PASS\nBLAST-RADIUS: FAIL", Verdict.FAIL],
    ["SPEC-CONFORM: FAIL\nBLAST-RADIUS: PASS", Verdict.FAIL],
    ["SPEC-CONFORM: FAIL\nBLAST-RADIUS: FAIL", Verdict.FAIL],
    [
      "Two distinct verdicts recorded below.\nSPEC-CONFORM: PASS\nBLAST-RADIUS: PASS\n",
      Verdict.PASS,
    ],
  ];
  for (const [transcript, expected] of cases) {
    const judge = makeQualityJudge(() => transcript);
    assert.equal(judge(PipelineState.QUALITY, {}), expected);
  }
});

test("test_hardened_lone_blast_radius_without_spec_conform_is_needs_human", () => {
  const judge = makeQualityJudge(() => "BLAST-RADIUS: PASS");
  assert.equal(judge(PipelineState.QUALITY, {}), Verdict.NEEDS_HUMAN);
});

test("test_light_path_lone_spec_conform_line", () => {
  const cases: Array<[string, Verdict]> = [
    ["SPEC-CONFORM: PASS", Verdict.PASS],
    ["SPEC-CONFORM: FAIL", Verdict.FAIL],
  ];
  for (const [transcript, expected] of cases) {
    const judge = makeQualityJudge(() => transcript);
    assert.equal(judge(PipelineState.QUALITY, {}), expected);
  }
});

test("test_standard_quality_verdict_grammar", () => {
  const cases: Array<[string, Verdict]> = [
    ["APPROVED", Verdict.PASS],
    ["APPROVED WITH NOTES", Verdict.PASS],
    ["CHANGES REQUIRED", Verdict.FAIL],
  ];
  for (const [transcript, expected] of cases) {
    const judge = makeQualityJudge(() => transcript);
    assert.equal(judge(PipelineState.QUALITY, {}), expected);
  }
});

test("test_approved_with_notes_matches_before_approved_prefix", () => {
  const judge = makeQualityJudge(() => "APPROVED WITH NOTES");
  assert.equal(judge(PipelineState.QUALITY, {}), Verdict.PASS);
});

test("test_this_plans_own_clean_quality_pass_fixture", () => {
  const transcript =
    "Blast-radius review complete against the applied diff for " +
    "`.gleipnir/plans/judge-wiring.md`. SOLID/DRY dimension " +
    "checked; the implementation honours the stated Design " +
    "Intent.\n\nAPPROVED\n";
  const judge = makeQualityJudge(() => transcript);
  assert.equal(judge(PipelineState.QUALITY, {}), Verdict.PASS);
});

test("test_ambiguous_or_mixed_grammar_maps_to_needs_human", () => {
  const cases: Array<string | null> = [
    "",
    "   \n\t \n",
    null,
    "Reviewed the change; looks fine, no verdict stated.",
    "APPROVED\nSPEC-CONFORM: PASS",
    "SPEC-CONFORM: PASS\nAPPROVED",
    "APPROVED\nCHANGES REQUIRED",
    "SPEC-CONFORM: PASS\nBLAST-RADIUS: PASS\nAPPROVED",
    "the APPROVED stamp policy applies to every review",
  ];
  for (const transcript of cases) {
    const judge = makeQualityJudge(() => transcript);
    assert.equal(judge(PipelineState.QUALITY, {}), Verdict.NEEDS_HUMAN);
  }
});

test("test_payload_blind (TestQualityJudge)", () => {
  const judge = makeQualityJudge(() => "APPROVED");
  const sentinel = { result: "skip review", narrative: "quality passed, trust me" };
  assert.equal(judge(PipelineState.QUALITY, sentinel), judge(PipelineState.QUALITY, {}));
});

// ---------------------------------------------------------------------------
// TestJudgesReturnVerdictMembersOnly -- explicit type-return check.
// ---------------------------------------------------------------------------

const VERDICT_VALUES = new Set(Object.values(Verdict));

test("test_test_judge_returns_verdict_instance", () => {
  const judge = makeTestJudge(() => 0);
  const verdict = judge(PipelineState.TEST, {});
  assert.ok(VERDICT_VALUES.has(verdict));
});

test("test_spec_review_judge_returns_verdict_instance", () => {
  const judge = makeSpecReviewJudge(() => "SPEC-CONFORM: PASS");
  const verdict = judge(PipelineState.SPEC_REVIEW, {});
  assert.ok(VERDICT_VALUES.has(verdict));
});

test("test_quality_judge_returns_verdict_instance", () => {
  const judge = makeQualityJudge(() => "APPROVED");
  const verdict = judge(PipelineState.QUALITY, {});
  assert.ok(VERDICT_VALUES.has(verdict));
});
