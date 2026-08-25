/**
 * judges.ts — SRP: derive a `Verdict` from an injected artifact, and nothing
 * else. One reason to change: a grammar/exit-code contract.
 *
 * Ports (oracle, semantics frozen): `src/gleipnir/engine/judges.py` L1-304
 * (three factories, grammars, exit-code map).
 *
 * `judges.ts` imports ONLY `state.ts`/`transitions.ts` — NO import of
 * `engine.ts` (mirrors `judges.py` L28-33's "no import into engine core").
 * The injected reader is the ONLY I/O boundary, supplied by the caller edge,
 * never by this module.
 *
 * REAL BODIES (Assemble step 5c, code stage): the three factories + the
 * shared anchored-line grammar helper below are implemented against
 * `judges.py` L1-304's behavioural contract, which `test/judges.test.ts`
 * (the structural port of `tests/test_judges.py`) pins 1:1.
 */

import type { PipelineState } from "./state.ts";
import { Verdict, type Judge } from "./transitions.ts";

export type { Judge };

// ---------------------------------------------------------------------------
// Shared anchored-line grammars (oracle `judges.py` L50-66, brittle-but-
// honest). Each pattern matches ONLY a line that consists of the verdict
// token and nothing else -- never a token embedded mid-sentence in unrelated
// prose. Patterns are stored as SOURCE STRINGS, not precompiled `RegExp`
// instances, and a fresh `RegExp` is constructed per call in
// `hasVerdictLine`/`parseVerdictLine` below -- a single shared `g`-flagged
// `RegExp` object carries mutable `lastIndex` state across calls, which
// would silently corrupt repeated matching against different transcripts;
// constructing fresh avoids that footgun entirely (never reused, so never
// stale).
// ---------------------------------------------------------------------------

const SPEC_CONFORM_SOURCE = "^SPEC-CONFORM:\\s+(PASS|FAIL)\\s*$";
const BLAST_RADIUS_SOURCE = "^BLAST-RADIUS:\\s+(PASS|FAIL)\\s*$";
// Alternation ordered so "APPROVED WITH NOTES" is tried before the shorter
// "APPROVED" prefix -- otherwise "APPROVED" would match first and leave
// " WITH NOTES" as unmatched trailing content, failing the anchored `$`.
const STANDARD_VERDICT_SOURCE = "^(APPROVED WITH NOTES|APPROVED|CHANGES REQUIRED)\\s*$";

/** Presence-only check: does at least one line matching `source` exist,
 * regardless of arity? An ambiguous (>1) match must still register as
 * "present" so cross-grammar branches in `makeQualityJudge` fire correctly
 * -- only the single-token EXTRACTION is delegated to `parseVerdictLine`. */
function hasVerdictLine(transcript: string, source: string): boolean {
  return new RegExp(source, "m").test(transcript);
}

/**
 * Return the sole captured verdict token for an anchored-line `source`
 * pattern (oracle `_parse_verdict_line`, `judges.py` L69-94). Shared by
 * every judge grammar that requires EXACTLY ONE anchored verdict line (DRY
 * — one helper, not copy-pasted per judge):
 *
 * * returns the single captured token if exactly one line matched;
 * * returns `null` if zero or more than one line matched (missing or
 *   ambiguous/duplicated) -- the caller maps `null` to `Verdict.NEEDS_HUMAN`
 *   (fail-closed).
 */
function parseVerdictLine(transcript: string, source: string): string | null {
  const matches = [...transcript.matchAll(new RegExp(source, "gm"))];
  if (matches.length !== 1) {
    return null;
  }
  return matches[0][1];
}

/**
 * Build the `Judge` for the `SPEC_REVIEW` transition (oracle
 * `make_spec_review_judge`, `judges.py` L97-139).
 *
 * Grammar: parse for the anchored, per-line `^SPEC-CONFORM:\s+(PASS|FAIL)\s*$`
 * (multiline): exactly one such line -> `PASS`/`FAIL` maps directly; zero
 * matches, more than one match, an empty/`null`/whitespace-only transcript,
 * or the token appearing only inside unrelated prose (not on its own
 * anchored line) -> `Verdict.NEEDS_HUMAN` (fail-closed).
 */
export function makeSpecReviewJudge(
  readReviewerVerdict: () => string | null,
): Judge {
  return (_state: PipelineState, _payload: Readonly<Record<string, unknown>>): Verdict => {
    // Payload-blind by construction: `state`/`payload` are never inspected.
    // The only input consumed is the injected reader.
    const transcript = readReviewerVerdict();
    if (!transcript || !transcript.trim()) {
      return Verdict.NEEDS_HUMAN;
    }

    const token = parseVerdictLine(transcript, SPEC_CONFORM_SOURCE);
    if (token === null) {
      // Zero matches (no line / embedded-in-prose only) or more than one
      // (duplicated/conflicting) -- fail-closed either way.
      return Verdict.NEEDS_HUMAN;
    }

    return token === "PASS" ? Verdict.PASS : Verdict.FAIL;
  };
}

/**
 * Build the `Judge` for the `QUALITY` transition (oracle
 * `make_quality_judge`, `judges.py` L142-242). Three recognised grammars,
 * all fail-closed to `Verdict.NEEDS_HUMAN` on any ambiguity or cross-grammar
 * mix:
 *
 * 1. **Hardened two-pass**: BOTH `SPEC-CONFORM` and `BLAST-RADIUS` present,
 *    each exactly once. Both `PASS` -> `Verdict.PASS`; either `FAIL` ->
 *    `Verdict.FAIL`.
 * 2. **Light-path collapsed**: exactly one `SPEC-CONFORM` line and NO
 *    `BLAST-RADIUS` line -> maps its token directly.
 * 3. **Standard quality verdict**: exactly one anchored
 *    `APPROVED | APPROVED WITH NOTES | CHANGES REQUIRED` line, no
 *    `SPEC-CONFORM`/`BLAST-RADIUS` line present. `APPROVED`/
 *    `APPROVED WITH NOTES` -> `Verdict.PASS` (notes are advisory, not a
 *    block); `CHANGES REQUIRED` -> `Verdict.FAIL`.
 */
export function makeQualityJudge(
  readReviewerVerdict: () => string | null,
): Judge {
  return (_state: PipelineState, _payload: Readonly<Record<string, unknown>>): Verdict => {
    // Payload-blind by construction: `state`/`payload` are never inspected.
    const transcript = readReviewerVerdict();
    if (!transcript || !transcript.trim()) {
      return Verdict.NEEDS_HUMAN;
    }

    const hasSpec = hasVerdictLine(transcript, SPEC_CONFORM_SOURCE);
    const hasBlast = hasVerdictLine(transcript, BLAST_RADIUS_SOURCE);
    const hasStandard = hasVerdictLine(transcript, STANDARD_VERDICT_SOURCE);

    if (hasSpec && hasBlast) {
      // Shape 1: hardened two-pass. A co-occurring standard token, or
      // either line duplicated, is a genuine cross-grammar/duplicate
      // ambiguity -- fail-closed, never "first wins".
      if (hasStandard) {
        return Verdict.NEEDS_HUMAN;
      }
      const specToken = parseVerdictLine(transcript, SPEC_CONFORM_SOURCE);
      const blastToken = parseVerdictLine(transcript, BLAST_RADIUS_SOURCE);
      if (specToken === null || blastToken === null) {
        return Verdict.NEEDS_HUMAN;
      }
      if (specToken === "PASS" && blastToken === "PASS") {
        return Verdict.PASS;
      }
      return Verdict.FAIL;
    }

    if (hasSpec && !hasBlast) {
      // Shape 2: light-path collapsed -- exactly one SPEC-CONFORM line, no
      // BLAST-RADIUS line, no standard token co-occurring.
      if (hasStandard) {
        return Verdict.NEEDS_HUMAN;
      }
      const specToken = parseVerdictLine(transcript, SPEC_CONFORM_SOURCE);
      if (specToken === null) {
        return Verdict.NEEDS_HUMAN;
      }
      return specToken === "PASS" ? Verdict.PASS : Verdict.FAIL;
    }

    if (hasBlast && !hasSpec) {
      // A lone BLAST-RADIUS line with no SPEC-CONFORM pair is neither a
      // complete hardened pair nor the light-path shape -- genuinely
      // ambiguous.
      return Verdict.NEEDS_HUMAN;
    }

    if (hasStandard) {
      // Shape 3: standard quality verdict -- exactly one anchored token, no
      // SPEC-CONFORM/BLAST-RADIUS line present (already ruled out above).
      const standardToken = parseVerdictLine(transcript, STANDARD_VERDICT_SOURCE);
      if (standardToken === null) {
        return Verdict.NEEDS_HUMAN;
      }
      if (standardToken === "CHANGES REQUIRED") {
        return Verdict.FAIL;
      }
      // APPROVED / APPROVED WITH NOTES -- notes are advisory.
      return Verdict.PASS;
    }

    // No recognised verdict line of any of the three grammars.
    return Verdict.NEEDS_HUMAN;
  };
}

/**
 * Build the `Judge` for the `TEST` transition (oracle `make_test_judge`,
 * `judges.py` L245-304). Mechanical exit-code observation, payload-blind:
 * `0` -> `Verdict.PASS`; any non-zero `number` -> `Verdict.FAIL`; `null`
 * (command not run / result unavailable / timed out) -> `Verdict.NEEDS_HUMAN`
 * (fail-closed).
 */
export function makeTestJudge(readTestExitCode: () => number | null): Judge {
  return (_state: PipelineState, _payload: Readonly<Record<string, unknown>>): Verdict => {
    // Payload-blind by construction: `state`/`payload` are never inspected.
    const exitCode = readTestExitCode();
    if (exitCode === null) {
      return Verdict.NEEDS_HUMAN;
    }
    return exitCode === 0 ? Verdict.PASS : Verdict.FAIL;
  };
}

export type { PipelineState };
export { Verdict };
