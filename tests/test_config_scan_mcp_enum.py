"""MCP effective tool-set enumeration + single-holder assertion tests
(check 2) for `config_scan.py` -- the most important file in this suite: it
directly re-creates the three real bugs from this session's lessons
L-C12/L-C12b.

Spec: `.gleipnir/plans/config-scoping-preflight.md`, Architect check 2 /
Assemble step 3 / Stress-test ST-3, ST-6, ST-13.

THIS FILE EXTENDS the API from `test_config_scan_grammar.py` (`Finding`,
`FindingSeverity.FAIL`/`WARN`) by adding three new `FindingCheck` members:

    class FindingCheck(Enum):
        GRAMMAR = "grammar"                  # already specified
        SINGLE_HOLDER = "single_holder"       # NEW: >1 holder, or the
                                               # designated holder doesn't
                                               # actually hold it
        FAIL_OPEN = "fail_open"                # NEW: a specific agent that
                                               # should deny a namespace
                                               # does not -- named leak
        OVER_RESTRICTION = "over_restriction"  # NEW: zero agents hold a
                                               # namespace at all (WARN)

and the two check-2 pure-core functions:

    enumerate_effective_tools(
        agents: dict[str, dict],
        jsonc_agent_overrides: dict[str, dict] | None = None,
    ) -> dict[str, set[str]]

        `agents[name]` is that agent's ALREADY-PARSED frontmatter dict (the
        `parse_frontmatter` output shape from `test_config_scan_parse.py`);
        only its top-level `"tools"` key (a `{glob: bool}` map) matters
        here. Returns, per agent name, the EFFECTIVE set of denied
        namespace globs: the UNION of (a) every glob key in the agent's
        own frontmatter `tools` map whose value is `False`, and (b) every
        glob key in `jsonc_agent_overrides.get(name, {})` (the
        `opencode.jsonc` `agent.<name>.tools` block shape, L-C12b's SECOND
        valid deny location) whose value is also `False`. A deny in
        EITHER location denies the namespace for that agent. An absent/
        empty `jsonc_agent_overrides` (matching the LIVE `opencode.jsonc`,
        which has no top-level `agent` key today) is a pure no-op merge.

    assert_single_holders(
        effective: dict[str, set[str]],
        mcp_namespaces: list[str],
        holder_map: dict[str, str],
    ) -> list[Finding]

        For each `namespace` in `mcp_namespaces` (e.g. `"gleipnir-git_*"`),
        compute `non_deniers` = every agent in `effective` whose set does
        NOT contain `namespace`. Then:

          - `len(non_deniers) == 0` -> namespace held by NO ONE ->
            `Finding(OVER_RESTRICTION, WARN, where=namespace, ...)` --
            reported, never forces a nonzero exit by itself (that
            aggregation happens in `decide_config`, specified in the next
            test file -- not reimplemented here).
          - `len(non_deniers) == 1` and it equals
            `holder_map.get(namespace)` -> clean, no Finding.
          - Otherwise (the designated holder is missing from
            `non_deniers`, OR there is more than one) the situation is
            anomalous and is reported from TWO angles simultaneously,
            because they are different risk framings of the same evidence:
              * a `Finding(SINGLE_HOLDER, FAIL, where=namespace, ...)`
                naming EVERY agent in `non_deniers` (the generic "more
                than one holder of a namespace meant to be single-held"
                rule, plan check 2c) -- exactly one per namespace; and
              * for every agent in `non_deniers` OTHER than the
                designated holder (i.e. an unexpected EXTRA non-denier
                beyond whoever is supposed to hold it), an INDIVIDUAL
                `Finding(FAIL_OPEN, FAIL, where=f"{agent}: {namespace}",
                ...)` naming that ONE leaking agent + namespace, detail
                conveying it "would silently gain broker tools on
                restart" (plan check 2a, the quality-reviewer/
                session-scribe near-miss). When `len(non_deniers) == 1`
                but it is NOT the designated holder, only the
                `SINGLE_HOLDER` finding is produced (there is no second,
                "extra" agent to separately name as a leak).

This dual-angle design lets `test_config_scan_mcp_enum.py`'s ST-3 fixture
(one unexpected EXTRA leaking agent beyond the correct holder) and ST-6c
fixture (two agents sharing a namespace) both be produced by the SAME
underlying `>1 non-denier` computation, filtered by `Finding.check`.
"""

from __future__ import annotations

from gleipnir.preflight import config_scan as cs


MCP_NAMESPACES = ["gleipnir-git_*", "gleipnir-pm_*"]
HOLDER_MAP = {"gleipnir-git_*": "git-ops", "gleipnir-pm_*": "project-mgr"}


def _real_nine_agents() -> dict[str, dict]:
    """The REAL current 9-agent `tools:` shape, read verbatim from the live
    files this session:

      - `git-ops.md` (line ~51):        tools: {"gleipnir-pm_*": false}
      - `project-mgr.md` (line ~23):    tools: {"gleipnir-git_*": false}
      - `orchestrator.md` (lines 45-47): tools: {"gleipnir-git_*": false, "gleipnir-pm_*": false}
      - `quality-reviewer.md` (lines 25-27): same both-denied shape
      - `gleipnir-code.md` (lines 34-36):     same both-denied shape
      - `gleipnir-plan.md` (lines 23-25):     same both-denied shape
      - `gleipnir-brainstorm.md` (lines 28-30): same both-denied shape
      - `notify.md` (lines 19-21):            same both-denied shape
      - `session-scribe.md` (lines 30-32):   same both-denied shape

    i.e. `git-ops` is the only agent that does NOT deny `gleipnir-git_*`
    (it is the designated holder), `project-mgr` is the only agent that
    does NOT deny `gleipnir-pm_*` (it is the designated holder), and every
    other roster agent denies BOTH namespaces."""
    both_denied = {"gleipnir-git_*": False, "gleipnir-pm_*": False}
    return {
        "git-ops": {"tools": {"gleipnir-pm_*": False}},
        "project-mgr": {"tools": {"gleipnir-git_*": False}},
        "orchestrator": {"tools": dict(both_denied)},
        "quality-reviewer": {"tools": dict(both_denied)},
        "gleipnir-code": {"tools": dict(both_denied)},
        "gleipnir-plan": {"tools": dict(both_denied)},
        "gleipnir-brainstorm": {"tools": dict(both_denied)},
        "notify": {"tools": dict(both_denied)},
        "session-scribe": {"tools": dict(both_denied)},
    }


# ---------------------------------------------------------------------------
# ST-6a: the live shape passes with exactly one holder per namespace.
# ---------------------------------------------------------------------------

class TestST6aLiveShapePasses:
    def test_git_ops_is_the_only_non_denier_of_gleipnir_git(self):
        effective = cs.enumerate_effective_tools(_real_nine_agents())
        non_deniers = {
            name for name, denied in effective.items() if "gleipnir-git_*" not in denied
        }
        assert non_deniers == {"git-ops"}

    def test_project_mgr_is_the_only_non_denier_of_gleipnir_pm(self):
        effective = cs.enumerate_effective_tools(_real_nine_agents())
        non_deniers = {
            name for name, denied in effective.items() if "gleipnir-pm_*" not in denied
        }
        assert non_deniers == {"project-mgr"}

    def test_assert_single_holders_returns_zero_findings_for_the_live_shape(self):
        effective = cs.enumerate_effective_tools(_real_nine_agents())
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)
        assert findings == []

    def test_every_non_holder_agent_denies_both_namespaces(self):
        effective = cs.enumerate_effective_tools(_real_nine_agents())
        for name in (
            "orchestrator",
            "quality-reviewer",
            "gleipnir-code",
            "gleipnir-plan",
            "gleipnir-brainstorm",
            "notify",
            "session-scribe",
        ):
            assert effective[name] == {"gleipnir-git_*", "gleipnir-pm_*"}


# ---------------------------------------------------------------------------
# ST-3: the real near-miss -- quality-reviewer's git deny goes missing ->
# fail-open leak, named.
# ---------------------------------------------------------------------------

class TestST3FailOpenLeakIsTheRealNearMiss:
    def test_quality_reviewer_missing_git_deny_is_a_fail_open_fail(self):
        agents = _real_nine_agents()
        # The exact near-miss: quality-reviewer's OWN frontmatter still
        # denies gleipnir-pm_*, but its "gleipnir-git_*": false line is
        # gone -- it would silently gain the git broker's tools.
        agents["quality-reviewer"] = {"tools": {"gleipnir-pm_*": False}}

        effective = cs.enumerate_effective_tools(agents)
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)

        fail_open = [f for f in findings if f.check is cs.FindingCheck.FAIL_OPEN]
        assert len(fail_open) == 1
        finding = fail_open[0]
        assert finding.severity is cs.FindingSeverity.FAIL
        assert "quality-reviewer" in finding.where
        assert "gleipnir-git_*" in finding.where
        assert "would silently gain broker tools on restart" in finding.detail

    def test_git_ops_the_correct_holder_is_never_itself_flagged(self):
        """The designated holder (`git-ops`) legitimately not denying
        `gleipnir-git_*` must never itself be named as a leaker -- only the
        UNEXPECTED extra non-denier (`quality-reviewer`) is."""
        agents = _real_nine_agents()
        agents["quality-reviewer"] = {"tools": {"gleipnir-pm_*": False}}

        effective = cs.enumerate_effective_tools(agents)
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)

        fail_open = [f for f in findings if f.check is cs.FindingCheck.FAIL_OPEN]
        assert all("git-ops" not in f.where for f in fail_open)

    def test_session_scribe_missing_pm_deny_is_also_a_named_fail_open_leak(self):
        """The near-miss generalises to the OTHER namespace/agent pairing
        too -- not hardcoded to quality-reviewer/gleipnir-git specifically."""
        agents = _real_nine_agents()
        agents["session-scribe"] = {"tools": {"gleipnir-git_*": False}}  # pm deny dropped

        effective = cs.enumerate_effective_tools(agents)
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)

        fail_open = [f for f in findings if f.check is cs.FindingCheck.FAIL_OPEN]
        assert len(fail_open) == 1
        assert "session-scribe" in fail_open[0].where
        assert "gleipnir-pm_*" in fail_open[0].where


# ---------------------------------------------------------------------------
# ST-6c: two agents both hold (fail to deny) the same single-holder
# namespace -> SINGLE_HOLDER FAIL naming both.
# ---------------------------------------------------------------------------

class TestST6cMultipleHoldersFails:
    def test_project_mgr_and_git_ops_both_keeping_pm_is_a_single_holder_fail(self):
        agents = _real_nine_agents()
        # git-ops additionally stops denying gleipnir-pm_* -- now BOTH
        # project-mgr (the designated holder) and git-ops fail to deny it.
        agents["git-ops"] = {"tools": {}}

        effective = cs.enumerate_effective_tools(agents)
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)

        single_holder = [
            f
            for f in findings
            if f.check is cs.FindingCheck.SINGLE_HOLDER and "gleipnir-pm_*" in f.where
        ]
        assert len(single_holder) == 1
        finding = single_holder[0]
        assert finding.severity is cs.FindingSeverity.FAIL
        assert "project-mgr" in finding.detail
        assert "git-ops" in finding.detail

    def test_git_ops_also_produces_its_own_fail_open_leak_for_pm(self):
        """The same fixture ALSO produces a FAIL_OPEN finding naming
        `git-ops` as the unexpected extra non-denier of `gleipnir-pm_*`
        (the designated holder `project-mgr` is never itself named as a
        leak) -- the two Finding checks coexist for one violation."""
        agents = _real_nine_agents()
        agents["git-ops"] = {"tools": {}}

        effective = cs.enumerate_effective_tools(agents)
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)

        fail_open = [
            f
            for f in findings
            if f.check is cs.FindingCheck.FAIL_OPEN and "gleipnir-pm_*" in f.where
        ]
        assert len(fail_open) == 1
        assert "git-ops" in fail_open[0].where
        assert "project-mgr" not in fail_open[0].where


# ---------------------------------------------------------------------------
# ST-6d: every agent denies a namespace -> OVER_RESTRICTION WARN, not FAIL.
# ---------------------------------------------------------------------------

class TestST6dOverRestrictionIsWarnNotFail:
    def test_every_agent_denying_gleipnir_git_is_a_warning(self):
        agents = _real_nine_agents()
        # git-ops (the designated holder) ALSO starts denying its own
        # namespace -- now every one of the 9 agents denies gleipnir-git_*.
        agents["git-ops"] = {"tools": {"gleipnir-git_*": False, "gleipnir-pm_*": False}}

        effective = cs.enumerate_effective_tools(agents)
        assert all("gleipnir-git_*" in denied for denied in effective.values())

        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)
        git_findings = [f for f in findings if "gleipnir-git_*" in f.where]
        assert len(git_findings) == 1
        finding = git_findings[0]
        assert finding.check is cs.FindingCheck.OVER_RESTRICTION
        assert finding.severity is cs.FindingSeverity.WARN
        assert finding.severity is not cs.FindingSeverity.FAIL

    def test_over_restriction_alone_carries_no_fail_severity_finding(self):
        """Forward-reference only to this function's OWN output (full
        `decide_config` aggregation is specified in the next test file):
        an over-restriction-only result must contain zero FAIL-severity
        findings, since `decide_config` treats WARN-only as CLOSED-
        equivalent by default (non-strict)."""
        agents = _real_nine_agents()
        agents["git-ops"] = {"tools": {"gleipnir-git_*": False, "gleipnir-pm_*": False}}

        effective = cs.enumerate_effective_tools(agents)
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)
        assert all(f.severity is cs.FindingSeverity.WARN for f in findings)


# ---------------------------------------------------------------------------
# ST-13: the opencode.jsonc `agent.<name>.tools` override merge (L-C12b's
# SECOND valid deny location).
# ---------------------------------------------------------------------------

class TestST13aJsoncOverrideSuppliesTheMissingDeny:
    def test_override_only_deny_counts_as_denied_no_false_leak(self):
        agents = _real_nine_agents()
        # quality-reviewer's OWN frontmatter is missing the git deny --
        # exactly the ST-3 shape -- but this time an opencode.jsonc-shaped
        # `agent.<name>.tools` override (a plain dict, mirroring the real
        # opencode.jsonc `agent` key's shape) supplies it instead.
        agents["quality-reviewer"] = {"tools": {"gleipnir-pm_*": False}}
        jsonc_agent_overrides = {
            "quality-reviewer": {"gleipnir-git_*": False},
        }

        effective = cs.enumerate_effective_tools(agents, jsonc_agent_overrides)
        assert "gleipnir-git_*" in effective["quality-reviewer"]

        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)
        assert findings == []

    def test_override_for_one_agent_does_not_affect_any_other_agent(self):
        agents = _real_nine_agents()
        agents["quality-reviewer"] = {"tools": {"gleipnir-pm_*": False}}
        jsonc_agent_overrides = {"quality-reviewer": {"gleipnir-git_*": False}}

        effective = cs.enumerate_effective_tools(agents, jsonc_agent_overrides)
        assert effective["git-ops"] == {"gleipnir-pm_*"}
        assert effective["session-scribe"] == {"gleipnir-git_*", "gleipnir-pm_*"}

    def test_frontmatter_only_deny_with_no_matching_override_key_still_counts(self):
        """The inverse merge direction: an agent with NO entry at all in
        `jsonc_agent_overrides` must still get full credit for its own
        frontmatter-level denies (the override is additive, never a
        replacement)."""
        agents = _real_nine_agents()
        jsonc_agent_overrides = {"quality-reviewer": {}}  # present but empty

        effective = cs.enumerate_effective_tools(agents, jsonc_agent_overrides)
        assert effective["notify"] == {"gleipnir-git_*", "gleipnir-pm_*"}


class TestST13bNoOpMergeOnTheLiveNoAgentKeyConfig:
    def test_none_overrides_is_a_pure_no_op(self):
        effective_with_none = cs.enumerate_effective_tools(_real_nine_agents(), None)
        effective_without_arg = cs.enumerate_effective_tools(_real_nine_agents())
        assert effective_with_none == effective_without_arg

    def test_empty_dict_overrides_is_also_a_pure_no_op(self):
        effective_empty = cs.enumerate_effective_tools(_real_nine_agents(), {})
        effective_none = cs.enumerate_effective_tools(_real_nine_agents(), None)
        assert effective_empty == effective_none

    def test_live_nine_agent_shape_still_passes_with_the_real_no_agent_key_config(self):
        """The REAL current `opencode.jsonc` has no top-level `agent` key
        at all -- the merge must be a no-op and the live 9-agent shape
        from ST-6a must still pass with zero Findings."""
        effective = cs.enumerate_effective_tools(_real_nine_agents(), {})
        findings = cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP)
        assert findings == []
