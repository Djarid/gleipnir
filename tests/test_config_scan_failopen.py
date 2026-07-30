"""Generalised fail-open sweep (check 4) + JSONC global-disable detector
tests for `config_scan.py`.

Spec: `.gleipnir/plans/config-scoping-preflight.md`, Architect check 4 /
Assemble step 4 / Stress-test ST-2, ST-7, ST-8.

THIS FILE EXTENDS the API from `test_config_scan_mcp_enum.py` (`Finding`,
`FindingSeverity.FAIL`/`WARN`, `FindingCheck.GRAMMAR`/`SINGLE_HOLDER`/
`FAIL_OPEN`/`OVER_RESTRICTION`, `enumerate_effective_tools`) by adding TWO
new `FindingCheck` members:

    class FindingCheck(Enum):
        GRAMMAR = "grammar"                    # test_config_scan_grammar.py
        SINGLE_HOLDER = "single_holder"         # test_config_scan_mcp_enum.py
        FAIL_OPEN = "fail_open"                 # test_config_scan_mcp_enum.py
        OVER_RESTRICTION = "over_restriction"   # test_config_scan_mcp_enum.py
        GLOBAL_DISABLE = "global_disable"       # NEW: the L-C12b bug-2 pattern
        MIS_SCOPED_GLOB = "mis_scoped_glob"     # NEW: a deny glob that would
                                                 # never actually match a real
                                                 # `<server>_<tool>` name

and THREE check-4 pure-core functions (two named explicitly by this
delegation, plus a third that ST-8's mis-scoped-glob detection requires --
`check_fail_open`'s signature, as specified, only takes the already-reduced
`effective` deny-set map, which by construction never contains a glob that
failed to match `<server>_*` in the first place, so mis-scoped-glob
detection needs its own function operating on the RAW per-agent `tools`
maps):

    check_fail_open(
        mcp_servers: list[str],
        effective: dict[str, set[str]],
        holder_map: dict[str, str],
    ) -> list[Finding]

        `mcp_servers` is EVERY MCP server currently declared in
        `opencode.jsonc`'s `mcp` block, expressed in each server's correct
        deny-glob form (e.g. `"gleipnir-git_*"`, `"gleipnir-pm_*"`, and --
        for the generalisation proof -- a synthetic THIRD
        `"gleipnir-foo_*"`) -- NOT hardcoded to the two named broker
        namespaces. `effective` is `enumerate_effective_tools`'s output
        (agent name -> effective denied-glob set). For each server glob,
        if EVERY agent in `effective` fails to deny it (a totally open
        namespace -- zero deniers, the opposite framing from check 2's
        `OVER_RESTRICTION`, which is zero NON-deniers), emit
        `Finding(FAIL_OPEN, FAIL, where=server_glob, ...)`. `holder_map` is
        consulted only to enrich the detail message (e.g. naming an
        expected holder if one happens to be designated) -- it never
        suppresses or gates the check for an undeclared/non-designated
        server; the rule applies uniformly to every server in
        `mcp_servers`.

    check_global_disable(jsonc_top_level_tools: dict | None) -> list[Finding]

        `jsonc_top_level_tools` is the parsed `opencode.jsonc`'s top-level
        `"tools"` key value (a `{glob: bool}` map), or `None` if that key
        is absent entirely (the LIVE current shape -- confirmed by reading
        `opencode.jsonc` this session: its top-level keys are exactly
        `$schema`, `default_agent`, `subagent_depth`, `mcp`, and
        `instructions` -- there is NO top-level `tools` key today). If
        present and it disables an MCP namespace (`"<server>_*": false`),
        emit `Finding(GLOBAL_DISABLE, FAIL, where=<glob>, ...)` -- the
        known-broken pattern (L-C12b bug 2: a global disable is never
        restored by any per-agent re-allow, so it hides the namespace from
        every subagent regardless of scoping). `None` or an empty dict ->
        `[]` (no finding) -- the regression guard that today's live config
        does not trigger this.

    find_mis_scoped_denies(
        agents: dict[str, dict],
        mcp_servers: list[str],
        jsonc_agent_overrides: dict[str, dict] | None = None,
    ) -> list[Finding]

        `mcp_servers` here are BASE SERVER NAMES (e.g. `"gleipnir-git"`,
        NOT `"gleipnir-git_*"`). Scans every agent's RAW frontmatter
        `tools` map (plus any `jsonc_agent_overrides` entry for that same
        agent) for a glob key that STARTS WITH a known server name but
        does NOT match that server's correct `f"{server}_*"` deny form
        (e.g. `"gleipnir-git*"`, missing the underscore) -- such a key
        would never actually match a real registered `<server>_<tool>` MCP
        tool name (e.g. `gleipnir-git_commit_changes`), so treating it as
        a valid deny would be a silent fail-open. Emits
        `Finding(MIS_SCOPED_GLOB, WARN, where=f"{agent}: {key}", ...)` for
        each such key -- reported, but WARN (not FAIL): it is a suspected
        authoring mistake, not by itself proof the namespace leaked (that
        is `check_fail_open`'s/`assert_single_holders`'s job, operating on
        `effective`, which -- by construction -- never counts a mis-scoped
        key as a deny at all).
"""

from __future__ import annotations

from gleipnir.preflight import config_scan as cs


def _real_nine_agents() -> dict[str, dict]:
    """The REAL current 9-agent `tools:` shape (same fixture as
    `test_config_scan_mcp_enum.py`'s `_real_nine_agents`, read verbatim
    from the live files earlier this session): `git-ops` denies only
    `gleipnir-pm_*`; `project-mgr` denies only `gleipnir-git_*`; every
    other roster agent denies BOTH. None of the 9 files mention any
    `gleipnir-foo_*` namespace at all -- there is no third server today."""
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
# ST-7: generalised fail-open -- a future/synthetic THIRD MCP server that
# nobody denies anywhere must FAIL, proving the sweep iterates every
# declared server generically rather than being hardcoded to git/pm.
# ---------------------------------------------------------------------------

class TestST7GeneralisedFailOpenForAThirdServer:
    def test_synthetic_third_server_left_undenied_by_everyone_fails(self):
        agents = _real_nine_agents()
        effective = cs.enumerate_effective_tools(agents)
        # No agent's frontmatter (and no jsonc override) mentions
        # gleipnir-foo_* at all -- it is a synthetic THIRD server.
        servers = ["gleipnir-git_*", "gleipnir-pm_*", "gleipnir-foo_*"]
        holder_map = {"gleipnir-git_*": "git-ops", "gleipnir-pm_*": "project-mgr"}

        findings = cs.check_fail_open(servers, effective, holder_map)

        foo_findings = [f for f in findings if "gleipnir-foo_*" in f.where]
        assert len(foo_findings) == 1
        finding = foo_findings[0]
        assert finding.check is cs.FindingCheck.FAIL_OPEN
        assert finding.severity is cs.FindingSeverity.FAIL

    def test_the_two_known_broker_namespaces_do_not_also_trigger_fail_open(self):
        """The live shape's git/pm namespaces each have exactly ONE
        non-denier (their designated holder) -- NOT zero -- so they must
        NOT be flagged by the total-fail-open sweep. Only the truly
        zero-denier synthetic server should be."""
        agents = _real_nine_agents()
        effective = cs.enumerate_effective_tools(agents)
        servers = ["gleipnir-git_*", "gleipnir-pm_*", "gleipnir-foo_*"]
        holder_map = {"gleipnir-git_*": "git-ops", "gleipnir-pm_*": "project-mgr"}

        findings = cs.check_fail_open(servers, effective, holder_map)

        assert not any("gleipnir-git_*" in f.where for f in findings)
        assert not any("gleipnir-pm_*" in f.where for f in findings)

    def test_generalisation_holds_with_no_holder_map_entry_at_all(self):
        """`gleipnir-foo_*` has NO entry in `holder_map` whatsoever (it is
        not one of the two designated single-holder namespaces) -- the
        rule must still fire; `holder_map` never gates or suppresses the
        check for an undeclared server."""
        agents = _real_nine_agents()
        effective = cs.enumerate_effective_tools(agents)

        findings = cs.check_fail_open(["gleipnir-foo_*"], effective, holder_map={})
        assert len(findings) == 1
        assert findings[0].check is cs.FindingCheck.FAIL_OPEN
        assert findings[0].severity is cs.FindingSeverity.FAIL
        assert "gleipnir-foo_*" in findings[0].where

    def test_a_server_denied_by_at_least_one_agent_is_not_fail_open(self):
        """Sanity check on the boundary condition: even a SINGLE agent
        denying the synthetic server is enough to avoid the totally-open
        classification (whether or not that single agent is a sensible
        "holder" is check 2's concern, not check 4's)."""
        agents = _real_nine_agents()
        agents["notify"]["tools"]["gleipnir-foo_*"] = False
        effective = cs.enumerate_effective_tools(agents)

        findings = cs.check_fail_open(["gleipnir-foo_*"], effective, holder_map={})
        assert findings == []


# ---------------------------------------------------------------------------
# ST-8: a mis-scoped deny glob (missing the underscore) must WARN, never
# be silently treated as a valid deny.
# ---------------------------------------------------------------------------

class TestST8MisScopedGlobWarnsNotSilentPass:
    def test_missing_underscore_glob_produces_a_warn_finding(self):
        agents = {
            "some-agent": {"tools": {"gleipnir-git*": False}},  # NO underscore
        }
        findings = cs.find_mis_scoped_denies(agents, ["gleipnir-git", "gleipnir-pm"])
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check is cs.FindingCheck.MIS_SCOPED_GLOB
        assert finding.severity is cs.FindingSeverity.WARN
        assert finding.severity is not cs.FindingSeverity.FAIL
        assert "some-agent" in finding.where
        assert "gleipnir-git*" in finding.where
        assert "match" in finding.detail.lower()

    def test_mis_scoped_glob_does_not_count_as_a_valid_deny_in_effective_tools(self):
        """The key requirement: a mis-scoped glob must NOT satisfy check
        2/4's single-holder or fail-open requirements the way a correctly
        formed `"gleipnir-git_*": false` would -- `enumerate_effective_tools`
        must never fold it into that agent's effective denied-glob set."""
        agents = {"some-agent": {"tools": {"gleipnir-git*": False}}}
        effective = cs.enumerate_effective_tools(agents)
        assert "gleipnir-git_*" not in effective["some-agent"]
        assert effective["some-agent"] == set()

    def test_mis_scoped_glob_leaves_the_agent_counted_as_a_non_denier(self):
        """End-to-end proof: because the mis-scoped glob does not count,
        an agent relying on it alone is STILL a non-denier of the real
        `gleipnir-git_*` namespace in `check_fail_open`'s eyes -- i.e. the
        mis-scoping does not accidentally close the very leak it was
        meant to close."""
        agents = _real_nine_agents()
        # session-scribe's REAL deny is replaced with the mis-scoped form.
        agents["session-scribe"] = {"tools": {"gleipnir-git*": False, "gleipnir-pm_*": False}}
        effective = cs.enumerate_effective_tools(agents)
        assert "gleipnir-git_*" not in effective["session-scribe"]

        findings = cs.check_fail_open(
            ["gleipnir-git_*", "gleipnir-pm_*"],
            effective,
            {"gleipnir-git_*": "git-ops", "gleipnir-pm_*": "project-mgr"},
        )
        # Still not a TOTAL fail-open (git-ops correctly denies nothing --
        # it's the holder -- and every other real agent still correctly
        # denies gleipnir-git_*), but the mis-scoped glob is separately
        # WARNed by find_mis_scoped_denies, never silently accepted.
        mis_scoped = cs.find_mis_scoped_denies(agents, ["gleipnir-git", "gleipnir-pm"])
        assert any("session-scribe" in f.where for f in mis_scoped)

    def test_a_correctly_formed_glob_is_never_flagged_as_mis_scoped(self):
        agents = _real_nine_agents()
        findings = cs.find_mis_scoped_denies(agents, ["gleipnir-git", "gleipnir-pm"])
        assert findings == []

    def test_jsonc_override_can_also_carry_a_mis_scoped_glob(self):
        """The mis-scoping check must apply to BOTH valid deny locations
        (L-C12b) -- an `opencode.jsonc` `agent.<name>.tools` override with
        the same missing-underscore mistake must also WARN."""
        agents = {"some-agent": {"tools": {}}}
        overrides = {"some-agent": {"gleipnir-pm*": False}}
        findings = cs.find_mis_scoped_denies(agents, ["gleipnir-git", "gleipnir-pm"], overrides)
        assert len(findings) == 1
        assert "some-agent" in findings[0].where
        assert "gleipnir-pm*" in findings[0].where


# ---------------------------------------------------------------------------
# ST-2: the reintroduced global-disable pattern (L-C12b bug 2) must FAIL;
# the current real opencode.jsonc (no such block) must NOT trigger it.
# ---------------------------------------------------------------------------

class TestST2GlobalDisablePatternDetection:
    def test_reintroduced_top_level_tools_global_disable_fails(self):
        jsonc_top_level_tools = {"gleipnir-git_*": False}
        findings = cs.check_global_disable(jsonc_top_level_tools)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check is cs.FindingCheck.GLOBAL_DISABLE
        assert finding.severity is cs.FindingSeverity.FAIL
        assert "gleipnir-git_*" in finding.where

    def test_multiple_globally_disabled_namespaces_each_get_their_own_finding(self):
        jsonc_top_level_tools = {"gleipnir-git_*": False, "gleipnir-pm_*": False}
        findings = cs.check_global_disable(jsonc_top_level_tools)
        assert len(findings) == 2
        wheres = {f.where for f in findings}
        assert "gleipnir-git_*" in "".join(wheres)
        assert all(f.check is cs.FindingCheck.GLOBAL_DISABLE for f in findings)
        assert all(f.severity is cs.FindingSeverity.FAIL for f in findings)

    def test_current_real_opencode_jsonc_shape_does_not_trigger_this_regression_guard(self):
        """Confirmed by reading `opencode.jsonc` this session: its
        top-level keys are exactly `$schema`, `default_agent`,
        `subagent_depth`, `mcp`, `instructions` -- there is NO top-level
        `tools` key at all. `parse_jsonc`'s output for the real file would
        therefore yield `None` (or a missing key) for
        `jsonc_top_level_tools`, and this must NOT trigger a
        GLOBAL_DISABLE finding -- the fix (removing the pattern) must stay
        fixed."""
        findings = cs.check_global_disable(None)
        assert findings == []

    def test_empty_top_level_tools_dict_also_does_not_trigger(self):
        findings = cs.check_global_disable({})
        assert findings == []

    def test_a_top_level_tools_entry_that_is_not_a_disable_does_not_trigger(self):
        """Only a `False`-valued (disabling) entry is the known-broken
        pattern; a `True`-valued entry (were one ever present) is not the
        bug this check exists to catch."""
        findings = cs.check_global_disable({"gleipnir-git_*": True})
        assert findings == []
