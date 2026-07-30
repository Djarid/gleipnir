"""Top-level aggregation tests (check 3 + `decide_config`) for
`config_scan.py`.

Spec: `.gleipnir/plans/config-scoping-preflight.md`, Architect check 3 /
Assemble step 5 / Stress-test ST-4, ST-5, ST-10.

THIS FILE EXTENDS the API from all four prior test files (`Unparseable`,
`UnparseableKind`, `Finding`, `FindingSeverity.FAIL`/`WARN`,
`FindingCheck.GRAMMAR`/`SINGLE_HOLDER`/`FAIL_OPEN`/`OVER_RESTRICTION`/
`GLOBAL_DISABLE`/`MIS_SCOPED_GLOB`, `extract_frontmatter`,
`parse_frontmatter`, `parse_jsonc`, `check_grammar`,
`enumerate_effective_tools`, `assert_single_holders`, `check_fail_open`,
`check_global_disable`, `find_mis_scoped_denies`) with the top-level
aggregation, mirroring `boundary.py`'s `decide()`/`PreflightDecision`
almost exactly (re-read `boundary.decide` this session to confirm the
precise `override_ack` discipline being mirrored):

    class ConfigVerdict(Enum):
        CLOSED = "closed"
        PROCEED_UNCLOSED = "proceed_unclosed"
        REFUSE = "refuse"

    (Named `ConfigVerdict`, NOT `Verdict`, to avoid an import collision
    with `boundary.Verdict` if a caller ever imports both modules -- same
    three values, same semantics, same eventual 0/2/1 CLI exit-code
    mapping.)

    DEV_MODE_LABEL_CONFIG = "config scan NOT CLOSED (override-ack)"

    @dataclass(frozen=True)
    class ConfigDecision:
        verdict: ConfigVerdict
        label: str
        reasons: tuple[str, ...] = ()

    def decide_config(
        unparseables: list[Unparseable],
        findings: list[Finding],
        agent_count: int,
        *,
        strict: bool = False,
        override_ack: bool = False,
    ) -> ConfigDecision:
        ...

`decide_config` mirrors `boundary.decide`'s exact control flow:

    all_closed = True
    if agent_count == 0:                         # mirrors `if not path_probes`
        all_closed = False                        # -- no evidence is not
                                                    #    evidence of closure
    for u in unparseables:                        # ANY Unparseable at all
        all_closed = False                         # forces not-closed
    for f in findings:
        if f.severity is FAIL:
            all_closed = False                     # ANY FAIL forces not-closed
        elif f.severity is WARN and strict:
            all_closed = False                     # WARN only counts if --strict

    if all_closed:
        return ConfigDecision(CLOSED, ...)
    if override_ack:
        return ConfigDecision(PROCEED_UNCLOSED, DEV_MODE_LABEL_CONFIG, ...)
    return ConfigDecision(REFUSE, ...)

The critical invariant (identical to `boundary.decide`): `override_ack` is
consulted ONLY inside the `not all_closed` branch -- there is NO code path
from `override_ack=True` to `ConfigVerdict.CLOSED` when the underlying
evidence is not all-clean. An all-clean input with `override_ack=True`
still honestly reports `CLOSED` (override_ack has no effect when there is
nothing to override).
"""

from __future__ import annotations

from pathlib import Path

from gleipnir.preflight import config_scan as cs


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / ".gleipnir" / "agents"
OPENCODE_JSONC_PATH = REPO_ROOT / "opencode.jsonc"

MCP_NAMESPACES = ["gleipnir-git_*", "gleipnir-pm_*"]
HOLDER_MAP = {"gleipnir-git_*": "git-ops", "gleipnir-pm_*": "project-mgr"}
MCP_SERVER_BASE_NAMES = ["gleipnir-git", "gleipnir-pm"]


# ---------------------------------------------------------------------------
# ST-4: THE LIVE REGRESSION GUARD. Reads the REAL 9 `.gleipnir/agents/*.md`
# files and the REAL `opencode.jsonc` off disk -- NOT fixture text -- and
# runs them through the full pipeline. This is the assertion that the
# ACTUAL current repo is clean.
# ---------------------------------------------------------------------------

class TestST4LiveRepoIsTheRegressionGuard:
    def test_the_real_nine_agent_files_exist_on_disk(self):
        """Sanity precondition for everything below: fail loudly (not with
        a silently-empty 0-agent pass) if the roster directory shape ever
        changes unexpectedly."""
        agent_paths = sorted(AGENTS_DIR.glob("*.md"))
        assert len(agent_paths) == 9, (
            f"expected the 9 known roster agent files under {AGENTS_DIR}, "
            f"found {len(agent_paths)}: {[p.name for p in agent_paths]}"
        )

    def test_every_real_agent_file_parses_with_zero_unparseable(self):
        agent_paths = sorted(AGENTS_DIR.glob("*.md"))
        unparseables: list[cs.Unparseable] = []
        for path in agent_paths:
            text = path.read_text()
            block = cs.extract_frontmatter(text)
            if isinstance(block, cs.Unparseable):
                unparseables.append(block)
                continue
            parsed = cs.parse_frontmatter(block)
            if isinstance(parsed, cs.Unparseable):
                unparseables.append(parsed)
        assert unparseables == [], (
            f"unexpected Unparseable result(s) reading the REAL agent files: {unparseables}"
        )

    def test_the_real_opencode_jsonc_parses_cleanly(self):
        text = OPENCODE_JSONC_PATH.read_text()
        parsed = cs.parse_jsonc(text)
        assert not isinstance(parsed, cs.Unparseable), (
            f"the REAL opencode.jsonc failed to parse: {parsed}"
        )
        assert isinstance(parsed, dict)

    def test_full_pipeline_against_the_real_repo_files_yields_decide_config_closed(self):
        """The end-to-end live regression guard: extract_frontmatter ->
        parse_frontmatter -> check_grammar -> enumerate_effective_tools ->
        assert_single_holders -> check_fail_open -> check_global_disable ->
        find_mis_scoped_denies -> decide_config, all against the REAL
        on-disk `.gleipnir/agents/*.md` + `opencode.jsonc` -- zero
        Unparseable, zero FAIL findings, CLOSED-equivalent (exit 0)."""
        agent_paths = sorted(AGENTS_DIR.glob("*.md"))

        unparseables: list[cs.Unparseable] = []
        parsed_agents: dict[str, dict] = {}
        all_findings: list[cs.Finding] = []

        for path in agent_paths:
            text = path.read_text()
            block = cs.extract_frontmatter(text)
            if isinstance(block, cs.Unparseable):
                unparseables.append(block)
                continue
            parsed = cs.parse_frontmatter(block)
            if isinstance(parsed, cs.Unparseable):
                unparseables.append(parsed)
                continue
            parsed_agents[path.stem] = parsed
            all_findings.extend(cs.check_grammar(parsed))

        assert unparseables == []
        assert len(parsed_agents) == 9

        effective = cs.enumerate_effective_tools(parsed_agents)
        all_findings.extend(cs.assert_single_holders(effective, MCP_NAMESPACES, HOLDER_MAP))
        all_findings.extend(cs.check_fail_open(MCP_NAMESPACES, effective, HOLDER_MAP))
        all_findings.extend(cs.find_mis_scoped_denies(parsed_agents, MCP_SERVER_BASE_NAMES))

        jsonc_text = OPENCODE_JSONC_PATH.read_text()
        jsonc_parsed = cs.parse_jsonc(jsonc_text)
        assert not isinstance(jsonc_parsed, cs.Unparseable)
        all_findings.extend(cs.check_global_disable(jsonc_parsed.get("tools")))

        fail_findings = [f for f in all_findings if f.severity is cs.FindingSeverity.FAIL]
        assert fail_findings == [], f"unexpected FAIL findings in the live repo: {fail_findings}"

        decision = cs.decide_config(unparseables, all_findings, agent_count=len(parsed_agents))
        assert decision.verdict is cs.ConfigVerdict.CLOSED


# ---------------------------------------------------------------------------
# ST-5: well-formedness fail-closed negative fixtures (a)-(e). Each must
# yield the correct Unparseable kind AND force decide_config to REFUSE --
# never silently skipped, never guessed at.
# ---------------------------------------------------------------------------

class TestST5NegativeFixturesForceRefuse:
    def test_a_no_fence_at_all_forces_refuse(self):
        result = cs.extract_frontmatter("# heading only, no frontmatter fence\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.NO_FRONTMATTER
        decision = cs.decide_config([result], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_b_unterminated_fence_forces_refuse(self):
        result = cs.extract_frontmatter("---\nmode: subagent\nsteps: 10\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.UNTERMINATED_FENCE
        decision = cs.decide_config([result], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_c_flow_mapping_forces_refuse(self):
        result = cs.parse_frontmatter("permission: {edit: deny}\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML
        decision = cs.decide_config([result], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_d_tab_indented_frontmatter_forces_refuse(self):
        result = cs.parse_frontmatter("permission:\n\tedit: deny\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML
        decision = cs.decide_config([result], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_e_depth_3_nested_map_forces_refuse(self):
        block = (
            "permission:\n"
            "  bash:\n"
            '    "*":\n'
            "      nested: deny\n"
        )
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML
        decision = cs.decide_config([result], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_one_bad_file_among_many_otherwise_clean_ones_still_refuses(self):
        """Never silently skipped: a single Unparseable among an otherwise
        large, clean agent count must still force REFUSE for the whole run
        -- it must never be dropped from the count and forgotten."""
        bad = cs.extract_frontmatter("no fence anywhere in this file\n")
        assert isinstance(bad, cs.Unparseable)
        decision = cs.decide_config([bad], [], agent_count=9)
        assert decision.verdict is cs.ConfigVerdict.REFUSE
        assert len(decision.reasons) >= 1


# ---------------------------------------------------------------------------
# ST-10: fail-closed aggregation, mirroring boundary.decide's control flow
# exactly.
# ---------------------------------------------------------------------------

class TestST10FailClosedAggregation:
    def test_any_single_unparseable_forces_refuse(self):
        u = cs.Unparseable(cs.UnparseableKind.NO_FRONTMATTER, where="some-agent.md")
        decision = cs.decide_config([u], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_any_single_fail_finding_forces_refuse(self):
        finding = cs.Finding(
            cs.FindingCheck.GRAMMAR, cs.FindingSeverity.FAIL, where="x", detail="bad"
        )
        decision = cs.decide_config([], [finding], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_empty_agent_set_forces_refuse_mirroring_boundarys_empty_path_probes_rule(self):
        """Mirrors `boundary.decide`'s `if not path_probes: all_closed =
        False` exactly: no evidence is not evidence of closure, even with
        zero Unparseable and zero findings otherwise."""
        decision = cs.decide_config([], [], agent_count=0)
        assert decision.verdict is cs.ConfigVerdict.REFUSE
        assert any("agent" in r.lower() for r in decision.reasons)

    def test_all_clean_input_is_closed(self):
        decision = cs.decide_config([], [], agent_count=9)
        assert decision.verdict is cs.ConfigVerdict.CLOSED
        assert decision.verdict is not cs.ConfigVerdict.REFUSE

    def test_warn_only_over_restriction_is_closed_by_default_non_strict(self):
        warn = cs.Finding(
            cs.FindingCheck.OVER_RESTRICTION,
            cs.FindingSeverity.WARN,
            where="gleipnir-git_*",
            detail="held by nobody",
        )
        decision = cs.decide_config([], [warn], agent_count=9)
        assert decision.verdict is cs.ConfigVerdict.CLOSED

    def test_warn_only_mis_scoped_glob_is_also_closed_by_default_non_strict(self):
        warn = cs.Finding(
            cs.FindingCheck.MIS_SCOPED_GLOB,
            cs.FindingSeverity.WARN,
            where="some-agent: gleipnir-git*",
            detail="may not match real tool names",
        )
        decision = cs.decide_config([], [warn], agent_count=9)
        assert decision.verdict is cs.ConfigVerdict.CLOSED

    def test_warn_only_with_strict_forces_a_non_closed_result(self):
        warn = cs.Finding(
            cs.FindingCheck.OVER_RESTRICTION,
            cs.FindingSeverity.WARN,
            where="gleipnir-git_*",
            detail="held by nobody",
        )
        decision = cs.decide_config([], [warn], agent_count=9, strict=True)
        assert decision.verdict is not cs.ConfigVerdict.CLOSED
        assert decision.verdict is cs.ConfigVerdict.REFUSE

    def test_strict_has_no_effect_on_an_already_all_clean_result(self):
        decision = cs.decide_config([], [], agent_count=9, strict=True)
        assert decision.verdict is cs.ConfigVerdict.CLOSED

    def test_strict_has_no_effect_on_fail_severity_findings_already_refusing(self):
        """`strict` only changes WARN's treatment -- a FAIL-severity
        finding refuses regardless of `strict`'s value."""
        fail = cs.Finding(
            cs.FindingCheck.GRAMMAR, cs.FindingSeverity.FAIL, where="x", detail="bad"
        )
        for strict in (True, False):
            decision = cs.decide_config([], [fail], agent_count=9, strict=strict)
            assert decision.verdict is cs.ConfigVerdict.REFUSE


# ---------------------------------------------------------------------------
# override_ack: mirrors boundary.decide's exact discipline -- can ONLY
# escalate a not-closed result to PROCEED_UNCLOSED; NEVER produces CLOSED.
# ---------------------------------------------------------------------------

class TestOverrideAckMirrorsBoundaryDecideExactly:
    def test_override_escalates_a_fail_finding_refuse_to_proceed_unclosed(self):
        fail = cs.Finding(
            cs.FindingCheck.GRAMMAR, cs.FindingSeverity.FAIL, where="x", detail="bad"
        )
        decision = cs.decide_config([], [fail], agent_count=1, override_ack=True)
        assert decision.verdict is cs.ConfigVerdict.PROCEED_UNCLOSED
        assert decision.verdict is not cs.ConfigVerdict.CLOSED
        assert decision.label == cs.DEV_MODE_LABEL_CONFIG

    def test_override_escalates_an_unparseable_refuse_to_proceed_unclosed(self):
        u = cs.Unparseable(cs.UnparseableKind.OUT_OF_SUBSET_YAML, where="agent.md")
        decision = cs.decide_config([u], [], agent_count=1, override_ack=True)
        assert decision.verdict is cs.ConfigVerdict.PROCEED_UNCLOSED
        assert decision.verdict is not cs.ConfigVerdict.CLOSED

    def test_override_escalates_an_empty_agent_set_refuse_to_proceed_unclosed(self):
        decision = cs.decide_config([], [], agent_count=0, override_ack=True)
        assert decision.verdict is cs.ConfigVerdict.PROCEED_UNCLOSED
        assert decision.verdict is not cs.ConfigVerdict.CLOSED

    def test_override_present_but_everything_clean_still_honestly_reports_closed(self):
        """The critical mirrored invariant: `override_ack` is consulted
        ONLY inside the `not all_closed` branch of `boundary.decide`'s
        control flow -- when the input IS all-clean, `override_ack` has NO
        EFFECT and the honest `CLOSED` result stands (it never gets
        rewritten to some dev-mode label just because the flag was set)."""
        decision = cs.decide_config([], [], agent_count=9, override_ack=True)
        assert decision.verdict is cs.ConfigVerdict.CLOSED

    def test_override_can_never_produce_closed_from_any_not_closed_input(self):
        """Direct, parametrised proof of the core invariant across EVERY
        kind of not-closed evidence this module can construct -- mirrors
        `boundary.py`'s own
        `test_override_can_never_produce_closed_from_a_not_closed_input`."""
        not_closed_cases: list[tuple[list[cs.Unparseable], list[cs.Finding], int]] = [
            ([cs.Unparseable(cs.UnparseableKind.NO_FRONTMATTER, where="a")], [], 1),
            (
                [],
                [cs.Finding(cs.FindingCheck.GRAMMAR, cs.FindingSeverity.FAIL, where="a", detail="d")],
                1,
            ),
            ([], [], 0),  # empty agent set
        ]
        for unparseables, findings, agent_count in not_closed_cases:
            decision = cs.decide_config(
                unparseables, findings, agent_count=agent_count, override_ack=True
            )
            assert decision.verdict is not cs.ConfigVerdict.CLOSED

            decision_no_override = cs.decide_config(
                unparseables, findings, agent_count=agent_count, override_ack=False
            )
            assert decision_no_override.verdict is cs.ConfigVerdict.REFUSE

    def test_override_ack_never_affects_a_strict_promoted_warn_only_result_either(self):
        """A WARN-only result promoted to not-closed by `strict=True` is
        just another not-closed input -- `override_ack` may escalate it to
        `PROCEED_UNCLOSED` but must never produce `CLOSED`."""
        warn = cs.Finding(
            cs.FindingCheck.OVER_RESTRICTION,
            cs.FindingSeverity.WARN,
            where="gleipnir-git_*",
            detail="held by nobody",
        )
        decision = cs.decide_config(
            [], [warn], agent_count=9, strict=True, override_ack=True
        )
        assert decision.verdict is cs.ConfigVerdict.PROCEED_UNCLOSED
        assert decision.verdict is not cs.ConfigVerdict.CLOSED


class TestConfigDecisionShape:
    """The `ConfigDecision` result itself must be a fully-populated,
    discriminated record -- mirroring `boundary.PreflightDecision`'s
    shape (`verdict`, `label`, `reasons`)."""

    def test_closed_decision_has_a_nonempty_label(self):
        decision = cs.decide_config([], [], agent_count=9)
        assert isinstance(decision.label, str) and decision.label

    def test_refuse_decision_has_reasons_explaining_why(self):
        fail = cs.Finding(
            cs.FindingCheck.GRAMMAR, cs.FindingSeverity.FAIL, where="x", detail="bad"
        )
        decision = cs.decide_config([], [fail], agent_count=1)
        assert isinstance(decision.reasons, tuple)
        assert len(decision.reasons) >= 1

    def test_verdict_is_always_one_of_the_three_configverdict_members(self):
        for unparseables, findings, agent_count in (
            ([], [], 9),
            ([cs.Unparseable(cs.UnparseableKind.NO_FRONTMATTER, where="a")], [], 1),
        ):
            decision = cs.decide_config(unparseables, findings, agent_count=agent_count)
            assert decision.verdict in (
                cs.ConfigVerdict.CLOSED,
                cs.ConfigVerdict.PROCEED_UNCLOSED,
                cs.ConfigVerdict.REFUSE,
            )
