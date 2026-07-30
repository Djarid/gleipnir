"""Fixture-based tests for the accepted-YAML-subset parser (Option A).

Spec: `.gleipnir/plans/config-scoping-preflight.md`, Trace "The accepted-
YAML-subset grammar (Option A)" + Assemble step 1 + Stress-test ST-5(e) /
ST-12.

THIS FILE SPECIFIES THE CONTRACT for the frontmatter-parsing pure-core of
`config_scan.py` (module does not exist yet -- this file is expected to
fail at IMPORT, which is the point per Axiom 1: the test is the correctness
arbiter, and the arbiter must fail loudly on an absent implementation).

Two pure functions, mirroring `boundary.py`'s discriminated-outcome style
(no I/O; fed text, fully unit-testable):

    extract_frontmatter(text: str) -> str | Unparseable
        Isolates the `---`-delimited YAML block at the top of an agent
        `.md` file's raw text (exactly one such block at file start). A
        missing leading fence -> Unparseable(kind=NO_FRONTMATTER); a
        missing/second closing fence -> Unparseable(kind=UNTERMINATED_FENCE).

    parse_frontmatter(block: str) -> dict | Unparseable
        Hand-rolled reader for EXACTLY the accepted subset (plan Trace
        grammar items 1-6: comments/blanks at any indent including
        interleaved; flat scalars typed as str/int/float/bool; a folded
        block scalar `description: >-`; nested maps capped at depth 2,
        i.e. `permission.bash."*"` as the deepest accepted grandchild
        SCALAR; a list block of quoted string items). Any construct
        outside that subset (flow mappings/sequences, anchors/aliases,
        tags, single-quoted-with-escapes, block-literal `|`, tab
        indentation, depth-3+ map nesting) -> Unparseable(kind=
        OUT_OF_SUBSET_YAML). A comment/blank-line PRE-PASS runs BEFORE any
        indent-based structural walking, so a comment line interleaved
        between two sibling map children (the real
        `gleipnir-brainstorm.md:16-19` / `git-ops.md:23-30` shape) is
        invisible to the walker and never trips a false
        OUT_OF_SUBSET_YAML.

The discriminated outcome type this file specifies:

    class UnparseableKind(Enum):
        NO_FRONTMATTER = "no_frontmatter"
        UNTERMINATED_FENCE = "unterminated_fence"
        OUT_OF_SUBSET_YAML = "out_of_subset_yaml"
        INVALID_JSONC = "invalid_jsonc"       # exercised by parse_jsonc,
                                               # not by this file's fixtures
        READ_ERROR = "read_error"             # thin-edge I/O only; not
                                               # exercised by this file

    @dataclass(frozen=True)
    class Unparseable:
        kind: UnparseableKind
        where: str
        detail: str = ""

`parse_jsonc(text: str) -> dict | Unparseable` is the sibling JSONC reader
(comment-strip + stdlib `json.loads`) -- imported here for completeness of
the module's parse-layer surface, but is exercised by its own fixtures in
a later test file, not repeated in depth here.
"""

from __future__ import annotations

from gleipnir.preflight import config_scan as cs


def _fm(body: str) -> str:
    """Wrap `body` in a `---`-delimited frontmatter fence, as a real agent
    `.md` file would have it, followed by a body heading (never
    grammar-checked)."""
    return f"---\n{body}---\n\n# agent body (not grammar-checked)\n"


# ---------------------------------------------------------------------------
# extract_frontmatter: fence isolation (positive + the two fence failures).
# ---------------------------------------------------------------------------

class TestExtractFrontmatterAcceptedFence:
    def test_extracts_the_block_between_the_two_fences(self):
        text = _fm("mode: subagent\nsteps: 10\n")
        block = cs.extract_frontmatter(text)
        assert not isinstance(block, cs.Unparseable)
        assert "mode: subagent" in block
        assert "steps: 10" in block
        # The fences themselves are not part of the returned block, and the
        # body heading after the closing fence must not leak in either.
        assert not block.strip().startswith("---")
        assert "agent body" not in block


class TestExtractFrontmatterFailClosedFences:
    def test_no_frontmatter_at_all_is_unparseable_no_frontmatter(self):
        """ST-5(e): a file with no leading `---` fence anywhere."""
        text = "# just a heading\nno frontmatter fence anywhere in this file\n"
        result = cs.extract_frontmatter(text)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.NO_FRONTMATTER

    def test_unterminated_fence_is_unparseable_unterminated_fence(self):
        """ST-5(b): a leading `---` with no closing `---` anywhere after it."""
        text = "---\nmode: subagent\nsteps: 10\n"  # no closing ---
        result = cs.extract_frontmatter(text)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.UNTERMINATED_FENCE

    def test_empty_file_is_unparseable_no_frontmatter(self):
        result = cs.extract_frontmatter("")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.NO_FRONTMATTER


# ---------------------------------------------------------------------------
# parse_frontmatter: the accepted subset (Assemble step 1, item 1).
# ---------------------------------------------------------------------------

class TestAcceptedFlatScalars:
    def test_unquoted_bareword_scalars(self):
        block = "mode: subagent\ncolor: primary\n"
        parsed = cs.parse_frontmatter(block)
        assert parsed == {"mode": "subagent", "color": "primary"}
        assert isinstance(parsed["mode"], str)

    def test_integer_scalar(self):
        parsed = cs.parse_frontmatter("steps: 30\n")
        assert parsed == {"steps": 30}
        assert isinstance(parsed["steps"], int)
        assert not isinstance(parsed["steps"], bool)

    def test_float_scalar(self):
        parsed = cs.parse_frontmatter("temperature: 0.2\n")
        assert parsed == {"temperature": 0.2}
        assert isinstance(parsed["temperature"], float)

    def test_double_quoted_string_scalar(self):
        parsed = cs.parse_frontmatter('color: "#7ed321"\n')
        assert parsed == {"color": "#7ed321"}
        assert isinstance(parsed["color"], str)

    def test_boolean_true_and_false_scalars_are_real_booleans(self):
        parsed = cs.parse_frontmatter("flag_a: true\nflag_b: false\n")
        assert parsed == {"flag_a": True, "flag_b": False}
        assert isinstance(parsed["flag_a"], bool)
        assert isinstance(parsed["flag_b"], bool)

    def test_allow_deny_ask_barewords_are_strings_not_booleans(self):
        """The typed distinction check 1 (in a later test file) depends on:
        allow/deny/ask are ALWAYS strings, true/false are ALWAYS booleans --
        never conflated by the reader itself."""
        parsed = cs.parse_frontmatter("edit: deny\n")
        assert parsed == {"edit": "deny"}
        assert isinstance(parsed["edit"], str)
        assert not isinstance(parsed["edit"], bool)


class TestAcceptedNestedMapsWithQuotedGlobKeys:
    def test_nested_permission_bash_map_with_quoted_glob_keys(self):
        block = (
            "permission:\n"
            "  bash:\n"
            '    "*": deny\n'
            '    "git status*": allow\n'
        )
        parsed = cs.parse_frontmatter(block)
        assert parsed == {
            "permission": {"bash": {"*": "deny", "git status*": "allow"}}
        }

    def test_unquoted_bareword_child_keys_alongside_quoted_glob_keys(self):
        block = (
            "permission:\n"
            "  edit: deny\n"
            "  tools:\n"
            '    "gleipnir-brainstorm": allow\n'
        )
        parsed = cs.parse_frontmatter(block)
        assert parsed["permission"]["edit"] == "deny"
        assert parsed["permission"]["tools"] == {"gleipnir-brainstorm": "allow"}

    def test_depth_2_cap_is_exactly_permission_bash_star(self):
        """The maximum accepted nesting: top-level key -> child map ->
        grandchild SCALAR. `permission.bash."*"` sitting at a scalar value
        is IN subset (this is the depth the 9 live files actually use)."""
        block = 'permission:\n  bash:\n    "*": deny\n'
        parsed = cs.parse_frontmatter(block)
        assert parsed["permission"]["bash"]["*"] == "deny"


class TestAcceptedBlockScalarDescription:
    def test_folded_block_scalar_is_captured_as_an_opaque_string(self):
        block = (
            "description: >-\n"
            "  The sole git/broker role. Only role that may run git, and\n"
            "  the only holder of push and API credentials.\n"
        )
        parsed = cs.parse_frontmatter(block)
        assert isinstance(parsed["description"], str)
        assert "sole git/broker role" in parsed["description"]
        assert "push and API credentials" in parsed["description"]
        # Prose content is never grammar-checked -- no structural assertion
        # beyond "it's a string containing both lines' text".

    def test_block_scalar_is_terminated_by_a_dedented_sibling_key(self):
        block = (
            "description: >-\n"
            "  First line of prose.\n"
            "  Second line of prose.\n"
            "mode: subagent\n"
        )
        parsed = cs.parse_frontmatter(block)
        assert "First line of prose." in parsed["description"]
        assert "Second line of prose." in parsed["description"]
        assert parsed["mode"] == "subagent"


class TestAcceptedListBlock:
    def test_compaction_survival_list_of_quoted_strings(self):
        block = (
            "compaction_survival:\n"
            '  - "You SEQUENCE the Gleipnir pipeline."\n'
            '  - "Escalate via \\n question when a gate hits its cap."\n'
        )
        parsed = cs.parse_frontmatter(block)
        assert parsed["compaction_survival"] == [
            "You SEQUENCE the Gleipnir pipeline.",
            "Escalate via \\n question when a gate hits its cap.",
        ]
        # \n stays LITERAL (the compaction-survival plugin un-escapes it at
        # runtime; the checker must not do that itself).
        assert "\\n" in parsed["compaction_survival"][1]


class TestAcceptedBooleansUnderTools:
    def test_top_level_tools_map_has_real_booleans(self):
        block = (
            "tools:\n"
            '  "gleipnir-git_*": false\n'
            '  "gleipnir-pm_*": false\n'
        )
        parsed = cs.parse_frontmatter(block)
        assert parsed["tools"] == {"gleipnir-git_*": False, "gleipnir-pm_*": False}
        for v in parsed["tools"].values():
            assert isinstance(v, bool)


# ---------------------------------------------------------------------------
# ST-12: the DEDICATED interleaved-comment fixture -- its own test, not
# riding along inside a broader positive check.
# ---------------------------------------------------------------------------

class TestInterleavedCommentsPrePassST12:
    """Comment lines indented at CHILD depth, sitting BETWEEN two sibling
    children of a nested map, must be invisible to the structural walker
    (stripped in a pre-pass BEFORE any indent-based structural walking) --
    proving the pre-pass runs first. If the walker instead saw the raw
    `# ...` line it would try to read it as a malformed key and wrongly
    emit OUT_OF_SUBSET_YAML on a genuinely valid file (a false-REFUSE on
    good config) -- exactly the failure mode this fixture guards against."""

    def test_gleipnir_brainstorm_shape_comment_between_webfetch_and_question(self):
        """Mirrors the REAL `gleipnir-brainstorm.md:16-19` construct: a
        comment block sitting between the `webfetch:` and `question:`
        siblings inside `permission:` (verbatim shape, read from the live
        file):

            permission:
              read: allow
              webfetch: allow
              # question is DENIED by capability, not by instruction: a
              # subagent's question cannot reach the operator, so allowing
              # it only invites a fake self-converge. Convergence is
              # surfaced by the orchestrator.
              question: deny
        """
        block = (
            "permission:\n"
            "  read: allow\n"
            "  webfetch: allow\n"
            "  # question is DENIED by capability, not by instruction: a\n"
            "  # subagent's question cannot reach the operator, so allowing\n"
            "  # it only invites a fake self-converge. Convergence is\n"
            "  # surfaced by the orchestrator.\n"
            "  question: deny\n"
        )
        parsed = cs.parse_frontmatter(block)
        assert not isinstance(parsed, cs.Unparseable)
        assert parsed["permission"] == {
            "read": "allow",
            "webfetch": "allow",
            "question": "deny",
        }

    def test_git_ops_shape_comment_between_read_and_bash_siblings(self):
        """Mirrors the REAL `git-ops.md:23-30` construct: several comment
        lines, indented at `permission:`'s child depth, sitting between the
        `read:` (a nested map) and `bash:` (a nested map) siblings
        (verbatim shape, read from the live file):

            permission:
              edit: deny
              write: deny
              task: deny
              webfetch: deny
              read:
                "*": allow
                ".git/**": deny
              # Commit + push move to the gleipnir-git broker (structural E-1
              # argument policy: force-push ABSENT from the tool surface, and
              # _run_git refuses hook-bypass flags). The bash allowlist is
              # NARROWED, not deleted...
              bash:
                "*": deny
                "git status*": allow
        """
        block = (
            "permission:\n"
            "  edit: deny\n"
            "  write: deny\n"
            "  task: deny\n"
            "  webfetch: deny\n"
            "  read:\n"
            '    "*": allow\n'
            '    ".git/**": deny\n'
            "  # Commit + push move to the gleipnir-git broker (structural E-1\n"
            "  # argument policy: force-push ABSENT from the tool surface, and\n"
            "  # _run_git refuses hook-bypass flags). The bash allowlist is\n"
            "  # NARROWED, not deleted -- the non-dangerous branch/sync verbs\n"
            "  # have no MCP replacement and must stay so a session can always\n"
            "  # move branches.\n"
            "  bash:\n"
            '    "*": deny\n'
            '    "git status*": allow\n'
        )
        parsed = cs.parse_frontmatter(block)
        assert not isinstance(parsed, cs.Unparseable)
        assert parsed["permission"]["read"] == {"*": "allow", ".git/**": "deny"}
        assert parsed["permission"]["bash"] == {"*": "deny", "git status*": "allow"}

    def test_indent_zero_comments_and_blank_lines_are_also_ignored(self):
        """Distinct from the interleaved-at-child-depth case above: a
        comment at indent 0, plus blank lines, must equally be stripped by
        the pre-pass -- the rule is "any indent", not just child depth."""
        block = (
            "# a top-level comment, not indented at all\n"
            "\n"
            "mode: subagent\n"
            "\n"
            "steps: 10\n"
        )
        parsed = cs.parse_frontmatter(block)
        assert parsed == {"mode": "subagent", "steps": 10}

    def test_interleaved_comment_never_emits_out_of_subset_yaml(self):
        """Direct negative assertion (belt-and-suspenders on the two shape
        tests above): the interleaved-comment construct must NEVER be
        classified as `OUT_OF_SUBSET_YAML` -- that specific false-positive
        is the exact regression this fixture exists to catch."""
        block = (
            "permission:\n"
            "  webfetch: allow\n"
            "  # an interleaved comment between two map siblings\n"
            "  question: deny\n"
        )
        result = cs.parse_frontmatter(block)
        if isinstance(result, cs.Unparseable):
            assert result.kind is not cs.UnparseableKind.OUT_OF_SUBSET_YAML
        assert not isinstance(result, cs.Unparseable)


# ---------------------------------------------------------------------------
# Out-of-subset constructs -> Unparseable(kind=OUT_OF_SUBSET_YAML), fail
# closed. Flow map, anchor, tab indent, and depth-3 nesting are the plan's
# explicitly named fixtures; a couple of extra out-of-subset constructs
# round out the set per the Trace "explicitly OUT of subset" list.
# ---------------------------------------------------------------------------

class TestOutOfSubsetYamlFailsClosed:
    def test_flow_mapping_is_out_of_subset(self):
        """ST-5(c): `permission: {edit: deny}` -- a flow mapping."""
        result = cs.parse_frontmatter("permission: {edit: deny}\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_yaml_anchor_is_out_of_subset(self):
        result = cs.parse_frontmatter("mode: &m subagent\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_yaml_alias_reference_is_out_of_subset(self):
        block = "defaults: &defaults\n  edit: deny\npermission: *defaults\n"
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_tab_indentation_is_out_of_subset(self):
        """ST-5(d): a frontmatter block using a tab character for
        indentation instead of spaces."""
        block = "permission:\n\tedit: deny\n"
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_depth_3_map_nesting_is_out_of_subset(self):
        """ST-5(e) / Assemble step 1: the maximum accepted depth is
        `permission.bash."*"` (a GRANDCHILD SCALAR). A THIRD level of map
        nesting -- `"*"` itself holding a map rather than a scalar --
        exceeds the depth-2 cap and must fail closed, never guessed."""
        block = (
            "permission:\n"
            "  bash:\n"
            '    "*":\n'
            "      nested: deny\n"
        )
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_block_literal_pipe_style_is_out_of_subset(self):
        """Only the FOLDED block scalar (`>-`) is in subset; the literal
        block style (`|`) is explicitly out of subset per Trace."""
        block = "description: |\n  literal block style, not folded\n"
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_single_quoted_string_with_escape_is_out_of_subset(self):
        block = "color: 'it''s escaped'\n"
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML

    def test_yaml_tag_is_out_of_subset(self):
        block = "steps: !!str 30\n"
        result = cs.parse_frontmatter(block)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.OUT_OF_SUBSET_YAML


class TestUnparseableCarriesDiagnosticDetail:
    """Every Unparseable outcome must carry SOME non-empty diagnostic (never
    a bare, unexplained fail) -- exact `where`/`detail` wording is an
    implementation choice for the next (code) stage, but silence is not
    acceptable for a fail-closed security tool."""

    def test_no_frontmatter_result_is_discriminated_not_a_bare_none(self):
        result = cs.extract_frontmatter("no fence here\n")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.NO_FRONTMATTER
        assert isinstance(result.where, str)
        assert isinstance(result.detail, str)

    def test_out_of_subset_has_nonempty_where_or_detail(self):
        result = cs.parse_frontmatter("permission: {edit: deny}\n")
        assert isinstance(result, cs.Unparseable)
        assert result.where or result.detail
