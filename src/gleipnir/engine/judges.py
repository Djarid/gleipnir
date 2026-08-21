"""Real ``Judge`` factories for the G-5 engine.

Plan: ``.gleipnir/plans/judge-wiring.md`` (authority, FULLY SPECIFIED after
four spec-conformance rounds + a blast-radius pass, both PASSED). This module
was authored in two delegations: the **Assemble step 0 interface stub**
(``test`` stage, three ``raise NotImplementedError`` bodies, so
``import gleipnir.engine.judges`` resolved at pytest **collection** time
before the real implementation existed) followed by the **``code`` stage**
(Assemble steps 1b–3b), which replaced each stub body with the real
parameterized-factory implementation below. The stub's fail-closed rationale
(a stub accidentally left in flight must explode loudly, not silently return
a fake ``Verdict``) motivated using ``NotImplementedError`` during that
interim window; it no longer applies now that real bodies are in place.

Wires the three judged transitions converged in
``.gleipnir/plans/judge-wiring-brainstorm.md`` (D1 Option D — all three
transitions in one slice) and detailed in ``judge-wiring.md``'s Trace section:

* ``SPEC_REVIEW`` — separate-subagent verdict (D2(a)): the independent
  ``quality-reviewer`` transcript for the spec-review stage.
* ``TEST`` — mechanical exit-code observation (D2-addendum): the
  ``bin/gleipnir-sandbox test -- --collect-only`` process exit code, sourced
  by the caller, never ``gleipnir-code``'s narrative.
* ``QUALITY`` — separate-subagent verdict (D2(a)): the independent
  ``quality-reviewer`` transcript for the quality stage, recognising THREE
  grammars (hardened two-pass, light-path, standard quality verdict).

No import into ``engine/__init__.py``; this module imports only stdlib +
``engine``'s public ``Judge``/``Verdict``/``PipelineState`` types (P1, Design
Principles — Dependency Inversion / stdlib-only core preserved). The injected
readers (``read_reviewer_verdict`` / ``read_test_exit_code``) are the *only*
I/O boundary and are supplied by the caller/harness edge — never by this
module and never by ``engine/``'s pure core.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from gleipnir.engine import Judge, PipelineState, Verdict

__all__ = [
    "make_spec_review_judge",
    "make_quality_judge",
    "make_test_judge",
]


# ---------------------------------------------------------------------------
# Shared anchored-line grammars (plan P3, brittle-but-honest). Each pattern
# matches ONLY a line that consists of the verdict token and nothing else
# (leading label, then whitespace, then the token, then optional trailing
# whitespace) -- never a token embedded mid-sentence in unrelated prose.
# ``re.MULTILINE`` makes ``^``/``$`` match per-line, not just at the start/
# end of the whole transcript.
# ---------------------------------------------------------------------------

_SPEC_CONFORM_RE = re.compile(r"^SPEC-CONFORM:\s+(PASS|FAIL)\s*$", re.MULTILINE)
_BLAST_RADIUS_RE = re.compile(r"^BLAST-RADIUS:\s+(PASS|FAIL)\s*$", re.MULTILINE)
# Alternation ordered so "APPROVED WITH NOTES" is tried before the shorter
# "APPROVED" prefix -- otherwise "APPROVED" would match first and leave
# " WITH NOTES" as unmatched trailing content, failing the anchored ``$``.
_STANDARD_VERDICT_RE = re.compile(
    r"^(APPROVED WITH NOTES|APPROVED|CHANGES REQUIRED)\s*$", re.MULTILINE
)


def _parse_verdict_line(transcript: str, pattern: "re.Pattern[str]") -> str | None:
    """Return the sole captured verdict token for an anchored-line ``pattern``.

    Shared by every judge grammar that requires **exactly one** anchored
    verdict line (plan Assemble step 3b: "one internal helper... reused by
    ``spec_review_judge`` and ``quality_judge``... not copy-pasted per
    judge"). Runs ``pattern.findall(transcript)`` and:

    * returns the single captured token if exactly one line matched;
    * returns ``None`` if zero or more than one line matched (missing or
      ambiguous/duplicated) -- the caller maps ``None`` to
      ``Verdict.NEEDS_HUMAN`` (P2, fail-closed).

    **Presence-only checks stay separate.** ``make_quality_judge`` also needs
    to know *which* grammar shape is in play (cross-grammar detection) before
    it knows whether that shape's arity is valid. A >1-match ambiguity must
    still register as "this grammar's marker is present" so the cross-grammar
    branch fires correctly -- collapsing presence into this helper's ``None``
    return would conflate "absent" with "ambiguous" and change behaviour.
    Callers needing presence-only use ``pattern.search(transcript) is not
    None`` directly; only the single-token *extraction* is shared here.
    """
    matches = pattern.findall(transcript)
    if len(matches) != 1:
        return None
    return matches[0]


def make_spec_review_judge(read_reviewer_verdict: Callable[[], str | None]) -> Judge:
    """Build the ``Judge`` for the ``SPEC_REVIEW`` transition.

    **Artifact (D2(a), separate-subagent verdict).** ``read_reviewer_verdict``
    is an injected, zero-argument callable whose *value* the caller sources
    from the independent spec-review-stage ``quality-reviewer`` delegation's
    output — never from the acting agent's (``gleipnir-plan``/``gleipnir-code``)
    own self-report. The returned ``Judge`` is a pure function of the
    already-sourced string (or ``None``) it reads; it performs no I/O itself.

    **Grammar (plan P3, brittle-but-honest).** Parse for the anchored,
    per-line regex ``^SPEC-CONFORM:\\s+(PASS|FAIL)\\s*$`` (multiline):

    * exactly one such line → ``PASS`` maps to ``Verdict.PASS``, ``FAIL``
      maps to ``Verdict.FAIL``;
    * zero matches, more than one match, an empty/``None``/whitespace-only
      transcript, or the token appearing only inside unrelated prose (not on
      its own anchored line) → ``Verdict.NEEDS_HUMAN`` (fail-closed, P2).

    :param read_reviewer_verdict: Injected reader returning the independent
        spec-review verdict transcript, or ``None`` if unavailable. The ONLY
        input this judge consumes; ``payload`` passed to the returned
        ``Judge`` is never inspected (no self-attestation channel).
    :returns: A ``Judge`` — ``Callable[[PipelineState, Mapping[str, Any]],
        Verdict]`` — conforming exactly to ``engine/__init__.py`` L106.
    """

    def _judge(state: PipelineState, payload: Mapping[str, Any]) -> Verdict:
        # Payload-blind by construction: `state`/`payload` are never
        # inspected. The only input consumed is the injected reader.
        transcript = read_reviewer_verdict()
        if not transcript or not transcript.strip():
            return Verdict.NEEDS_HUMAN

        token = _parse_verdict_line(transcript, _SPEC_CONFORM_RE)
        if token is None:
            # Zero matches (no line / embedded-in-prose only) or more than
            # one (duplicated/conflicting) -- fail-closed either way (P2).
            return Verdict.NEEDS_HUMAN

        return Verdict.PASS if token == "PASS" else Verdict.FAIL

    return _judge


def make_quality_judge(read_reviewer_verdict: Callable[[], str | None]) -> Judge:
    """Build the ``Judge`` for the ``QUALITY`` transition.

    **Artifact (D2(a), separate-subagent verdict).** Same shape as
    ``make_spec_review_judge``: ``read_reviewer_verdict`` is sourced from the
    independent ``quality``-stage ``quality-reviewer`` delegation's output,
    never the acting agent's self-report.

    **Grammar — THREE recognised shapes (plan P3, ``quality_judge`` Trace
    section), all fail-closed to ``Verdict.NEEDS_HUMAN`` on any ambiguity or
    cross-grammar mix:**

    1. **Hardened two-pass** (enforcement-bearing plans): BOTH
       ``^SPEC-CONFORM:\\s+(PASS|FAIL)\\s*$`` AND
       ``^BLAST-RADIUS:\\s+(PASS|FAIL)\\s*$`` present, each exactly once.
       Both ``PASS`` → ``Verdict.PASS``; either ``FAIL`` → ``Verdict.FAIL``.
    2. **Light-path collapsed**: exactly one ``^SPEC-CONFORM:\\s+(PASS|FAIL)
       \\s*$`` line and NO ``BLAST-RADIUS`` line → maps its token directly.
    3. **Standard quality verdict** (the mandated
       ``../agents/quality-reviewer.md`` L105–111 grammar): exactly one
       anchored line matching
       ``^(APPROVED WITH NOTES|APPROVED|CHANGES REQUIRED)\\s*$`` (alternation
       ordered so ``APPROVED WITH NOTES`` is matched before the ``APPROVED``
       prefix) and no ``SPEC-CONFORM``/``BLAST-RADIUS`` line present.
       ``APPROVED`` and ``APPROVED WITH NOTES`` → ``Verdict.PASS`` (notes are
       advisory, not a block); ``CHANGES REQUIRED`` → ``Verdict.FAIL``.

    Any ambiguity across shapes (no recognised line of any of the three
    grammars; a mix of grammars co-occurring; a required line missing; any
    token absent/duplicated; empty/``None``/whitespace-only input) →
    ``Verdict.NEEDS_HUMAN`` (fail-closed, P2).

    :param read_reviewer_verdict: Injected reader returning the independent
        quality-stage verdict transcript, or ``None`` if unavailable. The
        ONLY input this judge consumes; ``payload`` is never inspected.
    :returns: A ``Judge`` — ``Callable[[PipelineState, Mapping[str, Any]],
        Verdict]`` — conforming exactly to ``engine/__init__.py`` L106.
    """

    def _judge(state: PipelineState, payload: Mapping[str, Any]) -> Verdict:
        # Payload-blind by construction: `state`/`payload` are never
        # inspected. The only input consumed is the injected reader.
        transcript = read_reviewer_verdict()
        if not transcript or not transcript.strip():
            return Verdict.NEEDS_HUMAN

        # Presence-only checks: does at least one line of each grammar
        # exist, regardless of arity. An ambiguous (>1) match must still
        # register as "present" so the cross-grammar branches below fire
        # correctly -- only the single-token *extraction* is delegated to
        # the shared ``_parse_verdict_line`` helper (see its docstring).
        has_spec = _SPEC_CONFORM_RE.search(transcript) is not None
        has_blast = _BLAST_RADIUS_RE.search(transcript) is not None
        has_standard = _STANDARD_VERDICT_RE.search(transcript) is not None

        if has_spec and has_blast:
            # Shape 1: hardened two-pass. A co-occurring standard token, or
            # either line duplicated, is a genuine cross-grammar/duplicate
            # ambiguity -- fail-closed, never "first wins".
            if has_standard:
                return Verdict.NEEDS_HUMAN
            spec_token = _parse_verdict_line(transcript, _SPEC_CONFORM_RE)
            blast_token = _parse_verdict_line(transcript, _BLAST_RADIUS_RE)
            if spec_token is None or blast_token is None:
                return Verdict.NEEDS_HUMAN
            if spec_token == "PASS" and blast_token == "PASS":
                return Verdict.PASS
            return Verdict.FAIL

        if has_spec and not has_blast:
            # Shape 2: light-path collapsed -- exactly one SPEC-CONFORM
            # line, no BLAST-RADIUS line, no standard token co-occurring.
            if has_standard:
                return Verdict.NEEDS_HUMAN
            spec_token = _parse_verdict_line(transcript, _SPEC_CONFORM_RE)
            if spec_token is None:
                return Verdict.NEEDS_HUMAN
            return Verdict.PASS if spec_token == "PASS" else Verdict.FAIL

        if has_blast and not has_spec:
            # A lone BLAST-RADIUS line with no SPEC-CONFORM pair is neither
            # a complete hardened pair nor the light-path shape -- genuinely
            # ambiguous.
            return Verdict.NEEDS_HUMAN

        if has_standard:
            # Shape 3: standard quality verdict -- exactly one anchored
            # token, no SPEC-CONFORM/BLAST-RADIUS line present (already
            # ruled out above).
            standard_token = _parse_verdict_line(transcript, _STANDARD_VERDICT_RE)
            if standard_token is None:
                return Verdict.NEEDS_HUMAN
            if standard_token == "CHANGES REQUIRED":
                return Verdict.FAIL
            # APPROVED / APPROVED WITH NOTES -- notes are advisory.
            return Verdict.PASS

        # No recognised verdict line of any of the three grammars.
        return Verdict.NEEDS_HUMAN

    return _judge


def make_test_judge(read_test_exit_code: Callable[[], int | None]) -> Judge:
    """Build the ``Judge`` for the ``TEST`` transition.

    **Artifact (D2-addendum, mechanical exit-code observation — a NEW
    evidence class distinct from D2(a)'s separate-subagent-verdict class,
    since ``test`` has no independent reviewer role).**
    ``read_test_exit_code`` is an injected, zero-argument callable whose
    value the caller sources by actually running
    ``bin/gleipnir-sandbox test -- --collect-only`` itself (e.g.
    ``subprocess.run([...]).returncode``, at the caller edge — NEVER inside
    ``engine/`` or this module) and reading its raw process exit code.
    Independence comes from the signal being the machine's own record of
    *collecting* the tests, never any agent's narrative claim that "tests
    pass."

    **Why collection-only, not a full-suite run (plan ``test_judge`` Trace
    section, reconciled against ``engine/__init__.py`` L128–132, L163–166).**
    This judge fires at the ``TEST → CODE`` edge, i.e. *leaving*
    test-**authoring**, before any implementation exists — so under correct
    test-first practice a full-suite run is *expected* to exit non-zero
    (assertions against not-yet-written code). The mechanical signal is
    therefore ``pytest --collect-only``'s exit code: whether the
    freshly-authored tests are syntactically valid and collectible (imports
    resolve, fixtures/parametrize expressions evaluate), independent of
    whether their assertions would currently pass.

    **Contract:**

    * ``0`` → ``Verdict.PASS`` (tests collect cleanly → authoring was valid
      → advance to ``CODE``);
    * any non-zero ``int`` → ``Verdict.FAIL`` (collection/syntax error →
      the spec/plan was inadequate to author loadable tests → revert
      ``TEST → SPEC_REVIEW``);
    * ``None`` (command not run / result unavailable / timed out) →
      ``Verdict.NEEDS_HUMAN`` (fail-closed, P2).

    Timeout handling is the **caller's** concern: the injected reader applies
    its own timeout to the collection subprocess and returns ``None`` on
    timeout; this judge only ever maps ``int | None`` → ``Verdict`` and is
    agnostic to *which* command produced the int — the collection-only
    semantics are enforced by the caller running ``-- --collect-only``, not
    by this judge.

    :param read_test_exit_code: Injected reader returning the mechanical
        ``bin/gleipnir-sandbox test -- --collect-only`` exit code, or
        ``None`` if unavailable/timed out. The ONLY input this judge
        consumes; ``payload`` is never inspected.
    :returns: A ``Judge`` — ``Callable[[PipelineState, Mapping[str, Any]],
        Verdict]`` — conforming exactly to ``engine/__init__.py`` L106.
    """

    def _judge(state: PipelineState, payload: Mapping[str, Any]) -> Verdict:
        # Payload-blind by construction: `state`/`payload` are never
        # inspected. The only input consumed is the injected reader.
        exit_code = read_test_exit_code()
        if exit_code is None:
            return Verdict.NEEDS_HUMAN
        return Verdict.PASS if exit_code == 0 else Verdict.FAIL

    return _judge
