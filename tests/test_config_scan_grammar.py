"""Grammar-validator tests (check 1) for `config_scan.py`.

Spec: `.gleipnir/plans/config-scoping-preflight.md`, Architect check 1 /
Assemble step 2 / Stress-test ST-1, ST-9.

THIS FILE EXTENDS the API contract already established in
`tests/test_config_scan_parse.py` (`UnparseableKind`, `Unparseable`,
`extract_frontmatter`, `parse_frontmatter`) with the two new discriminated
types check 1 needs, mirroring `boundary.py`'s `ProbeOutcome`/`ProbeResult`
naming style:

    class FindingCheck(Enum):
        GRAMMAR = "grammar"
        # SINGLE_HOLDER / FAIL_OPEN / OVER_RESTRICTION are specified by
        # later test files (checks 2-4); not exercised here.

    class FindingSeverity(Enum):
        FAIL = "fail"   # forces a nonzero (REFUSE-equivalent) exit
        WARN = "warn"   # reported, does not by itself force nonzero

    @dataclass(frozen=True)
    class Finding:
        check: FindingCheck
        severity: FindingSeverity
        where: str          # a dotted key path, e.g. permission.tools."gleipnir-git*"
        detail: str = ""    # human-readable reason; frontmatter has no
                             # post-parse line numbers, so `where` (the key
                             # path) IS the location -- never left blank.

And the check-1 grammar validator itself:

    check_grammar(parsed_frontmatter: dict) -> list[Finding]

Walks the ALREADY-PARSED frontmatter dict (the output of
`parse_frontmatter`, never re-parses text) and applies, symmetrically, in
BOTH directions:

  - every `permission.*` value -- whether the DIRECT scalar value of a
    permission verb (`edit`/`read`/`bash`/`write`/`task`/`webfetch`/
    `question`), or a value inside a nested glob-keyed map under one of
    those (e.g. `permission.bash."*"`, `permission.tools."<glob>"`) --
    must be one of the strings `allow`/`deny`/`ask`. A BOOLEAN there is the
    exact L-C12 bug (ST-1) and is a `GRAMMAR`/`FAIL` Finding.
  - every top-level `tools.*` value must be an actual boolean. An
    `allow`/`deny`/`ask` STRING there (ST-9) is the inverse bug and is
    also a `GRAMMAR`/`FAIL` Finding.

`where` is reported as the DOTTED key path with any glob-style key quoted
exactly as it appears in the source (frontmatter has no post-parse line
numbers, so the key path is the only precise locator) -- e.g.
`permission.tools."gleipnir-git*"` or `tools."gleipnir-pm_*"`. A clean,
well-typed agent yields `[]` -- no findings at all.
"""

from __future__ import annotations

from gleipnir.preflight import config_scan as cs


# ---------------------------------------------------------------------------
# ST-1: boolean under permission (the exact L-C12 bug).
# ---------------------------------------------------------------------------

class TestST1BooleanUnderPermissionFails:
    def test_boolean_under_nested_permission_tools_glob_is_a_grammar_fail(self):
        parsed = {
            "permission": {
                "tools": {
                    "gleipnir-git*": True,
                }
            }
        }
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check is cs.FindingCheck.GRAMMAR
        assert finding.severity is cs.FindingSeverity.FAIL
        assert finding.where == 'permission.tools."gleipnir-git*"'
        assert "boolean under permission" in finding.detail
        assert "allow/deny/ask" in finding.detail

    def test_boolean_under_permission_tools_false_value_also_fails(self):
        """The bug is about the TYPE (boolean), not the truthiness of the
        specific `True`/`False` value -- both must be flagged."""
        parsed = {"permission": {"tools": {"gleipnir-pm_*": False}}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == 'permission.tools."gleipnir-pm_*"'
        assert findings[0].severity is cs.FindingSeverity.FAIL


# ---------------------------------------------------------------------------
# ST-9: string under top-level tools: (the inverse bug).
# ---------------------------------------------------------------------------

class TestST9StringUnderToolsFails:
    def test_string_under_top_level_tools_is_a_grammar_fail(self):
        parsed = {"tools": {"gleipnir-pm_*": "deny"}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check is cs.FindingCheck.GRAMMAR
        assert finding.severity is cs.FindingSeverity.FAIL
        assert finding.where == 'tools."gleipnir-pm_*"'
        assert "boolean" in finding.detail

    def test_allow_and_ask_strings_under_tools_also_fail(self):
        """Not just `deny` -- ANY allow/deny/ask string under `tools:` is
        wrong (a boolean is required there), so all three must be caught."""
        for bad_value in ("allow", "deny", "ask"):
            parsed = {"tools": {"gleipnir-git_*": bad_value}}
            findings = cs.check_grammar(parsed)
            assert len(findings) == 1, f"expected exactly one finding for {bad_value!r}"
            assert findings[0].where == 'tools."gleipnir-git_*"'


# ---------------------------------------------------------------------------
# Clean agent -> zero findings. Uses the REAL `quality-reviewer.md`
# permission/tools shape (read from the live file this session).
# ---------------------------------------------------------------------------

class TestCleanAgentPassesWithNoFindings:
    def test_quality_reviewer_shaped_agent_has_no_grammar_findings(self):
        parsed = {
            "permission": {
                "edit": "deny",
                "write": "deny",
                "task": "deny",
                "webfetch": "deny",
                "read": "allow",
                "bash": {
                    "*": "deny",
                    "git diff*": "allow",
                    "git log*": "allow",
                    "git show*": "allow",
                    "git status*": "allow",
                },
            },
            "tools": {
                "gleipnir-git_*": False,
                "gleipnir-pm_*": False,
            },
        }
        findings = cs.check_grammar(parsed)
        assert findings == []

    def test_git_ops_shaped_agent_with_nested_read_map_has_no_findings(self):
        """A second real shape (`git-ops.md`): a nested `permission.read`
        map alongside a nested `permission.bash` map, plus a top-level
        `tools:` map with a single boolean deny."""
        parsed = {
            "permission": {
                "edit": "deny",
                "write": "deny",
                "task": "deny",
                "webfetch": "deny",
                "read": {"*": "allow", ".git/**": "deny"},
                "bash": {
                    "*": "deny",
                    "git status*": "allow",
                    "git diff*": "allow",
                    "git log*": "allow",
                },
            },
            "tools": {"gleipnir-pm_*": False},
        }
        findings = cs.check_grammar(parsed)
        assert findings == []

    def test_agent_with_neither_permission_nor_tools_key_has_no_findings(self):
        """Absence of `permission`/`tools` entirely is not itself a grammar
        violation -- there is nothing to type-check. (A `tools`-absent
        agent is a check-2 single-holder/fail-open concern, specified in a
        later test file -- not a check-1 grammar concern.)"""
        findings = cs.check_grammar({"mode": "subagent", "steps": 10})
        assert findings == []


# ---------------------------------------------------------------------------
# Generalised (reverse-direction) coverage: check 1 must not be hardcoded to
# ONLY the two named ST-1/ST-9 key paths -- every permission verb (direct OR
# nested-glob) and every tools glob is checked, symmetrically.
# ---------------------------------------------------------------------------

class TestGeneralisedAcrossEveryPermissionVerb:
    def test_boolean_under_a_direct_permission_verb_fails(self):
        """`permission.edit` given as a boolean, not nested under a glob
        map at all -- the direct-scalar case ST-1's own fixture does not
        cover, but check 1 must catch all the same."""
        parsed = {"permission": {"edit": True}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == "permission.edit"
        assert findings[0].check is cs.FindingCheck.GRAMMAR
        assert findings[0].severity is cs.FindingSeverity.FAIL

    def test_boolean_under_permission_bash_star_fails(self):
        parsed = {"permission": {"bash": {"*": False}}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == 'permission.bash."*"'

    def test_boolean_under_permission_read_nested_glob_fails(self):
        parsed = {"permission": {"read": {".git/**": True}}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == 'permission.read.".git/**"'

    def test_boolean_under_permission_question_fails(self):
        """Every permission verb named in the Trace grammar -- not just
        `edit`/`bash`/`tools` -- is covered symmetrically."""
        parsed = {"permission": {"question": False}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == "permission.question"

    def test_multiple_boolean_leaks_each_produce_their_own_finding(self):
        parsed = {
            "permission": {
                "edit": True,
                "bash": {"*": False},
                "read": {".git/**": True},
            }
        }
        findings = cs.check_grammar(parsed)
        assert len(findings) == 3
        wheres = {f.where for f in findings}
        assert wheres == {
            "permission.edit",
            'permission.bash."*"',
            'permission.read.".git/**"',
        }
        assert all(f.check is cs.FindingCheck.GRAMMAR for f in findings)
        assert all(f.severity is cs.FindingSeverity.FAIL for f in findings)

    def test_mixed_permission_and_tools_violations_both_reported(self):
        """A single agent with BOTH bug classes at once (a boolean under
        `permission.*` AND a string under `tools.*`) must report both --
        check 1 is not "first violation wins"."""
        parsed = {
            "permission": {"edit": True},
            "tools": {"gleipnir-pm_*": "deny"},
        }
        findings = cs.check_grammar(parsed)
        assert len(findings) == 2
        wheres = {f.where for f in findings}
        assert wheres == {"permission.edit", 'tools."gleipnir-pm_*"'}


class TestGeneralisedAcrossEveryToolsGlob:
    def test_only_the_bad_tools_glob_is_flagged_not_its_well_typed_sibling(self):
        parsed = {
            "tools": {
                "gleipnir-git_*": False,          # well-typed: real boolean
                "gleipnir-pm_*": "deny",          # bug: string, not boolean
            }
        }
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == 'tools."gleipnir-pm_*"'

    def test_integer_under_tools_is_also_not_a_valid_boolean(self):
        """Python's `bool` is a subtype of `int`, so the checker must not
        accidentally accept a plain integer as "boolean enough"."""
        parsed = {"tools": {"gleipnir-git_*": 1}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == 'tools."gleipnir-git_*"'


# ---------------------------------------------------------------------------
# Regression: `tools:`/`permission:` present but NOT a map at all (a
# bareword scalar, or a `- "..."` list) -- both are legal top-level YAML
# shapes elsewhere in the accepted grammar subset, so a naive
# `isinstance(..., dict)`-only check silently emits ZERO findings and lets
# the malformed value propagate to `enumerate_effective_tools`/
# `find_mis_scoped_denies`, which then crash with an uncaught
# AttributeError on `.items()`. This is the earliest checkpoint: catch it
# here as a GRAMMAR/FAIL Finding instead.
# ---------------------------------------------------------------------------

class TestNonMapToolsOrPermissionIsAGrammarFailNotASilentPass:
    def test_bareword_bool_under_top_level_tools_is_a_grammar_fail(self):
        """`tools: true` -- a bareword boolean scalar where a glob-keyed
        map is required."""
        parsed = {"tools": True}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check is cs.FindingCheck.GRAMMAR
        assert finding.severity is cs.FindingSeverity.FAIL
        assert finding.where == "tools"
        assert "map" in finding.detail.lower()

    def test_bareword_scalar_under_permission_is_a_grammar_fail(self):
        """`permission: deny` -- a bareword string scalar where a
        verb-keyed map is required."""
        parsed = {"permission": "deny"}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check is cs.FindingCheck.GRAMMAR
        assert finding.severity is cs.FindingSeverity.FAIL
        assert finding.where == "permission"
        assert "map" in finding.detail.lower()

    def test_list_under_top_level_tools_is_also_a_grammar_fail(self):
        """A `- "..."` list mistakenly used under `tools:` instead of a
        map -- also non-dict, also caught here, not just the bool/scalar
        case."""
        parsed = {"tools": ["gleipnir-git_*", "gleipnir-pm_*"]}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == "tools"
        assert findings[0].check is cs.FindingCheck.GRAMMAR
        assert findings[0].severity is cs.FindingSeverity.FAIL

    def test_list_under_permission_is_also_a_grammar_fail(self):
        parsed = {"permission": ["allow", "deny"]}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 1
        assert findings[0].where == "permission"
        assert findings[0].check is cs.FindingCheck.GRAMMAR
        assert findings[0].severity is cs.FindingSeverity.FAIL

    def test_non_dict_permission_and_non_dict_tools_together_both_reported(self):
        """Both keys malformed at once must each produce their own
        Finding -- not "first violation wins"."""
        parsed = {"permission": True, "tools": 1}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 2
        wheres = {f.where for f in findings}
        assert wheres == {"permission", "tools"}
        assert all(f.check is cs.FindingCheck.GRAMMAR for f in findings)
        assert all(f.severity is cs.FindingSeverity.FAIL for f in findings)

    def test_non_dict_tools_never_raises_even_though_it_is_flagged(self):
        """The whole point: check_grammar must never propagate an
        uncaught exception on this input -- it returns a clean
        discriminated Finding instead."""
        for bad_value in (True, False, 1, 1.5, "deny", ["a", "b"]):
            findings = cs.check_grammar({"tools": bad_value})
            assert len(findings) == 1
            assert findings[0].where == "tools"


class TestFindingShapeIsAlwaysFullyPopulated:
    """Every Finding this check produces must be a fully-populated,
    discriminated record -- never a bare/ambiguous result."""

    def test_every_grammar_finding_has_the_grammar_check_and_fail_severity(self):
        parsed = {"permission": {"edit": True}, "tools": {"gleipnir-git_*": "allow"}}
        findings = cs.check_grammar(parsed)
        assert len(findings) == 2
        for f in findings:
            assert f.check is cs.FindingCheck.GRAMMAR
            assert f.severity is cs.FindingSeverity.FAIL
            assert isinstance(f.where, str) and f.where
            assert isinstance(f.detail, str) and f.detail
