"""Thin-edge (real file I/O) + CLI wiring tests for `config_scan.py`.

Spec: `.gleipnir/plans/config-scoping-preflight.md`, Assemble step 6.

THIS FILE EXTENDS the API from all five prior test files
(`test_config_scan_parse.py`, `test_config_scan_grammar.py`,
`test_config_scan_mcp_enum.py`, `test_config_scan_failopen.py`,
`test_config_scan_decide.py` -- `Unparseable`, `UnparseableKind`, `Finding`,
`FindingSeverity`, `FindingCheck`, `extract_frontmatter`,
`parse_frontmatter`, `parse_jsonc`, `check_grammar`,
`enumerate_effective_tools`, `assert_single_holders`, `check_fail_open`,
`check_global_disable`, `find_mis_scoped_denies`, `ConfigVerdict`,
`ConfigDecision`, `decide_config`, `DEV_MODE_LABEL_CONFIG`) with the ONLY
real I/O in the whole module -- the thin edge -- plus the CLI entrypoint
that wires everything together, mirroring `preflight/__main__.py`'s shape
and exit-code convention exactly (0=CLOSED, 1=REFUSE, 2=PROCEED_UNCLOSED).

    def read_agent_files(agents_dir: Path) -> dict[str, str | Unparseable]:
        Globs `agents_dir/*.md`. For each file, attempts `path.read_text()`.
        Real content -> `{stem: text}`. An `OSError` (permission denied, or
        a file that vanishes between the glob and the read) is CAUGHT --
        never propagated -- and mapped to
        `{stem: Unparseable(READ_ERROR, where=str(path), detail=str(exc))}`.
        A missing/unreadable `agents_dir` itself (its own directory-scan
        `OSError`, e.g. from a nonexistent directory on platforms where
        `Path.glob` raises rather than yielding nothing) is ALSO caught and
        treated as "found zero files" (`{}`) -- an empty agent set is a
        `decide_config`-level concern (forces REFUSE via `agent_count == 0`),
        never a thin-edge crash.

    def read_jsonc(path: Path) -> str | Unparseable:
        Attempts `path.read_text()`. Real content -> the text, verbatim.
        An `OSError` (missing file, permission denied) is caught -- never
        propagated -- and mapped to
        `Unparseable(READ_ERROR, where=str(path), detail=str(exc))`.

    DEFAULT_MCP_NAMESPACES = ["gleipnir-git_*", "gleipnir-pm_*"]
    DEFAULT_HOLDER_MAP = {"gleipnir-git_*": "git-ops", "gleipnir-pm_*": "project-mgr"}
    DEFAULT_MCP_SERVER_BASE_NAMES = ["gleipnir-git", "gleipnir-pm"]

    def config_scan_main(argv: list[str] | None = None, config_root: Path | None = None) -> int:
        The CLI entrypoint (what `preflight/__main__.py`'s eventual
        `config-scan` subcommand calls). `argv` may contain `--strict`
        and/or `--override-ack` (mirroring `preflight/__main__.py`'s own
        flags). `config_root` defaults to `<repo>/.gleipnir` (mirroring
        `boundary.py`'s `_repo_root()` convention: `Path(__file__)
        .resolve().parents[3]` from `config_scan.py`'s own location under
        `src/gleipnir/preflight/`, which resolves to the same repo root
        `boundary.py` uses) when not given. `opencode.jsonc` is read from
        `config_root.parent / "opencode.jsonc"` (repo root, sibling of
        `.gleipnir/`, exactly where the REAL file lives relative to the
        REAL `.gleipnir/`).

        Wires: `read_agent_files` + `read_jsonc` (thin edge) ->
        `extract_frontmatter` -> `parse_frontmatter` -> `check_grammar` ->
        `enumerate_effective_tools` -> `assert_single_holders` ->
        `check_fail_open` -> `parse_jsonc` -> `check_global_disable` ->
        `find_mis_scoped_denies` -> `decide_config`. ANY `READ_ERROR`
        `Unparseable` (missing `opencode.jsonc`, an unreadable agent file)
        flows into `decide_config` exactly like any other `Unparseable` --
        it forces REFUSE, it is never an uncaught exception escaping this
        function. Prints the decision (verdict + label + reasons) to
        stderr, exactly as `preflight/__main__.py.main()` does, and returns:

            0  ConfigVerdict.CLOSED
            2  ConfigVerdict.PROCEED_UNCLOSED
            1  ConfigVerdict.REFUSE
"""

from __future__ import annotations

from pathlib import Path

from gleipnir.preflight import config_scan as cs


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Light sanity re-check: the pure core is filesystem-independent. NOT a
# re-test of everything already covered in test_config_scan_parse.py /
# test_config_scan_grammar.py -- just confirming no Path/real-file
# involvement is needed anywhere in the pure layer.
# ---------------------------------------------------------------------------

class TestPureCoreIsFilesystemIndependentSanityRecheck:
    def test_extract_and_parse_frontmatter_work_on_bare_strings_no_fs(self):
        text = "---\nmode: subagent\nsteps: 5\n---\n\n# body\n"
        block = cs.extract_frontmatter(text)
        assert not isinstance(block, cs.Unparseable)
        parsed = cs.parse_frontmatter(block)
        assert parsed == {"mode": "subagent", "steps": 5}

    def test_check_grammar_works_on_a_hand_built_dict_no_fs(self):
        findings = cs.check_grammar({"permission": {"edit": True}})
        assert len(findings) == 1
        assert findings[0].check is cs.FindingCheck.GRAMMAR

    def test_parse_jsonc_works_on_a_bare_string_no_fs(self):
        parsed = cs.parse_jsonc('{"mcp": {"gleipnir-git": {"enabled": true}}}')
        assert not isinstance(parsed, cs.Unparseable)
        assert parsed == {"mcp": {"gleipnir-git": {"enabled": True}}}

    def test_decide_config_works_on_hand_built_evidence_no_fs(self):
        decision = cs.decide_config([], [], agent_count=1)
        assert decision.verdict is cs.ConfigVerdict.CLOSED


# ---------------------------------------------------------------------------
# read_agent_files: the thin edge, real file I/O, including the READ_ERROR
# fix (item 4 from spec-review) -- an OSError must map to a discriminated
# Unparseable, never propagate uncaught, never be silently skipped.
# ---------------------------------------------------------------------------

class TestReadAgentFilesThinEdge:
    def test_reads_real_md_files_into_a_name_to_text_map(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "foo.md").write_text("---\nmode: subagent\n---\n")
        (agents_dir / "bar.md").write_text("---\nmode: subagent\n---\n")

        result = cs.read_agent_files(agents_dir)

        assert set(result.keys()) == {"foo", "bar"}
        assert result["foo"] == "---\nmode: subagent\n---\n"
        assert result["bar"] == "---\nmode: subagent\n---\n"

    def test_only_md_files_are_picked_up(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "foo.md").write_text("---\nmode: subagent\n---\n")
        (agents_dir / "README.txt").write_text("not an agent file\n")

        result = cs.read_agent_files(agents_dir)
        assert set(result.keys()) == {"foo"}

    def test_empty_directory_yields_an_empty_map(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        assert cs.read_agent_files(agents_dir) == {}

    def test_nonexistent_agents_dir_yields_an_empty_map_never_raises(self, tmp_path: Path):
        """A missing `agents/` directory entirely must never raise out of
        this thin edge -- the resulting EMPTY agent set is a
        `decide_config`-level concern (forces REFUSE via `agent_count ==
        0`), not a thin-edge crash."""
        result = cs.read_agent_files(tmp_path / "does-not-exist")
        assert result == {}

    def test_os_error_on_one_file_read_maps_to_read_error_never_raised(
        self, tmp_path: Path, monkeypatch
    ):
        """The item-4 fix: a permission-denied (or vanished-mid-glob) file
        must map to a discriminated `Unparseable(READ_ERROR, ...)` --
        mirroring `boundary.py`'s `_fork_drop_verify_attempt`'s
        `os.pipe`/`os.fork` `OSError`-wrapping pattern: catch the SPECIFIC
        expected exception (`OSError`), map it to a fail-closed outcome,
        never let it propagate uncaught."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "good.md").write_text("---\nmode: subagent\n---\n")
        (agents_dir / "bad.md").write_text("---\nmode: subagent\n---\n")

        real_read_text = Path.read_text

        def flaky_read_text(self: Path, *args, **kwargs):
            if self.name == "bad.md":
                raise OSError("permission denied (injected)")
            return real_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", flaky_read_text)

        result = cs.read_agent_files(agents_dir)

        assert result["good"] == "---\nmode: subagent\n---\n"
        assert isinstance(result["bad"], cs.Unparseable)
        assert result["bad"].kind is cs.UnparseableKind.READ_ERROR
        assert "permission denied" in result["bad"].detail
        assert "bad.md" in result["bad"].where

    def test_an_os_error_on_every_file_still_yields_one_read_error_per_file(
        self, tmp_path: Path, monkeypatch
    ):
        """Never silently skipped: EVERY unreadable file gets its OWN
        discriminated `READ_ERROR`, not a single collapsed failure that
        loses track of how many files actually failed."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "a.md").write_text("x")
        (agents_dir / "b.md").write_text("y")

        def always_raise(self: Path, *args, **kwargs):
            raise OSError("vanished mid-glob (injected)")

        monkeypatch.setattr(Path, "read_text", always_raise)

        result = cs.read_agent_files(agents_dir)
        assert len(result) == 2
        assert all(isinstance(v, cs.Unparseable) for v in result.values())
        assert all(v.kind is cs.UnparseableKind.READ_ERROR for v in result.values())


# ---------------------------------------------------------------------------
# read_jsonc: the same thin-edge discipline for the single opencode.jsonc
# read.
# ---------------------------------------------------------------------------

class TestReadJsoncThinEdge:
    def test_reads_real_file_text_verbatim(self, tmp_path: Path):
        p = tmp_path / "opencode.jsonc"
        p.write_text('{"mcp": {}}')
        assert cs.read_jsonc(p) == '{"mcp": {}}'

    def test_nonexistent_path_maps_to_read_error_never_raises(self, tmp_path: Path):
        result = cs.read_jsonc(tmp_path / "does-not-exist.jsonc")
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.READ_ERROR

    def test_monkeypatched_os_error_maps_to_read_error_not_raised(
        self, tmp_path: Path, monkeypatch
    ):
        p = tmp_path / "opencode.jsonc"
        p.write_text('{"mcp": {}}')

        def raise_os_error(self: Path, *args, **kwargs):
            raise OSError("EACCES (injected)")

        monkeypatch.setattr(Path, "read_text", raise_os_error)

        result = cs.read_jsonc(p)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.READ_ERROR
        assert "EACCES" in result.detail

    def test_permission_error_subclass_is_also_caught_never_propagates(
        self, tmp_path: Path, monkeypatch
    ):
        """`PermissionError` is an `OSError` subclass -- confirming the
        catch is broad enough to cover it, not narrowly typed to the base
        class only by coincidence."""
        p = tmp_path / "opencode.jsonc"

        def raise_permission_error(self: Path, *args, **kwargs):
            raise PermissionError("denied (injected)")

        monkeypatch.setattr(Path, "read_text", raise_permission_error)

        result = cs.read_jsonc(p)
        assert isinstance(result, cs.Unparseable)
        assert result.kind is cs.UnparseableKind.READ_ERROR


# ---------------------------------------------------------------------------
# config_scan_main: the CLI entrypoint. Live-repo smoke test (real thin
# edge, real FS) + REFUSE-exit-code fixture tests.
# ---------------------------------------------------------------------------

class TestConfigScanMainLiveRepoSmokeTest:
    def test_real_repo_config_root_returns_exit_code_0(self):
        """The same live-repo assertion as ST-4
        (`test_config_scan_decide.py`), but through the FULL CLI
        entrypoint -- including the REAL thin edge (`read_agent_files` /
        `read_jsonc` against actual disk), not just the pure core called
        directly."""
        exit_code = cs.config_scan_main([], config_root=REPO_ROOT / ".gleipnir")
        assert exit_code == 0

    def test_default_config_root_also_resolves_to_the_real_repo(self):
        """No `config_root` override at all -- `config_scan_main` must
        default to the real repo's `.gleipnir` (mirroring
        `preflight/__main__.py`'s `_repo_root()` convention) and still
        report CLOSED for the current, clean live repo."""
        exit_code = cs.config_scan_main([])
        assert exit_code == 0

    def test_none_argv_is_equivalent_to_an_empty_list(self):
        exit_code = cs.config_scan_main(None, config_root=REPO_ROOT / ".gleipnir")
        assert exit_code == 0


class TestConfigScanMainReturnsRefuseExitCode:
    def test_boolean_under_permission_fixture_returns_exit_code_1(self, tmp_path: Path):
        """ST-1's exact bug, run through the full CLI: a boolean under
        `permission.tools."<glob>"` must surface as a nonzero (REFUSE)
        exit code, never 0."""
        config_root = tmp_path / ".gleipnir"
        agents_dir = config_root / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "broken-agent.md").write_text(
            "---\n"
            "permission:\n"
            "  tools:\n"
            '    "gleipnir-git*": true\n'
            "---\n\n# broken agent\n"
        )
        (config_root.parent / "opencode.jsonc").write_text('{"mcp": {}}')

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_missing_opencode_jsonc_refuses_rather_than_crashing(self, tmp_path: Path):
        """A missing `opencode.jsonc` is a `READ_ERROR` `Unparseable` (thin
        edge), which forces REFUSE via `decide_config` -- never an
        uncaught exception escaping the CLI entrypoint."""
        config_root = tmp_path / ".gleipnir"
        agents_dir = config_root / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "clean-agent.md").write_text("---\nmode: subagent\n---\n")
        # No opencode.jsonc written at all.

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_empty_agents_directory_refuses(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        (config_root / "agents").mkdir(parents=True)
        (config_root.parent / "opencode.jsonc").write_text('{"mcp": {}}')

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_unreadable_agent_file_via_injected_os_error_also_refuses(
        self, tmp_path: Path, monkeypatch
    ):
        """A `READ_ERROR` on an agent file (not just a grammar bug) must
        ALSO refuse -- the item-4 fix, exercised through the full CLI."""
        config_root = tmp_path / ".gleipnir"
        agents_dir = config_root / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "unreadable.md").write_text("---\nmode: subagent\n---\n")
        (config_root.parent / "opencode.jsonc").write_text('{"mcp": {}}')

        def raise_os_error(self: Path, *args, **kwargs):
            raise OSError("permission denied (injected)")

        monkeypatch.setattr(Path, "read_text", raise_os_error)

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_override_ack_flag_escalates_refuse_to_exit_code_2(self, tmp_path: Path):
        """`--override-ack` mirrors `preflight/__main__.py`'s own flag:
        escalates a REFUSE to PROCEED_UNCLOSED (exit 2), never to CLOSED
        (exit 0)."""
        config_root = tmp_path / ".gleipnir"
        agents_dir = config_root / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "broken-agent.md").write_text(
            "---\npermission:\n  edit: true\n---\n\n# broken agent\n"
        )
        (config_root.parent / "opencode.jsonc").write_text('{"mcp": {}}')

        exit_code = cs.config_scan_main(["--override-ack"], config_root=config_root)
        assert exit_code == 2
        assert exit_code != 0


class TestNonDictAgentBlockNeverRaises:
    """Regression for the SAME uncaught-exception class as
    `TestNonDictToolsNeverRaisesDefenseInDepth`
    (`test_config_scan_mcp_enum.py`), but for the top-level `agent:` key in
    `opencode.jsonc` (`config_scan.py:1265-1268`). `config_scan_main` builds
    `jsonc_agent_overrides` via
    `{name: block.get("tools", {}) for name, block in
    jsonc.get("agent", {}).items()}` -- if `agent:` is present but is NOT a
    dict, `.items()` raises `AttributeError` and the CLI crashes instead of
    returning a normal exit code. A non-dict `agent:` block must be treated
    benignly (coerced to "no overrides"), exactly like the existing
    non-dict `tools:`/`permission:` defense-in-depth handling -- never an
    uncaught exception escaping `config_scan_main`. Modeled on
    `TestConfigScanMainReturnsRefuseExitCode.
    test_missing_opencode_jsonc_refuses_rather_than_crashing`: it must
    complete and return an `int` exit code rather than propagating."""

    def _write_clean_fixture(self, config_root: Path, jsonc_agent_value: str) -> None:
        agents_dir = config_root / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "clean-agent.md").write_text("---\nmode: subagent\n---\n")
        (config_root.parent / "opencode.jsonc").write_text(
            '{"mcp": {}, "agent": ' + jsonc_agent_value + "}"
        )

    def test_top_level_agent_as_a_list_does_not_raise(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "[]")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)

    def test_top_level_agent_as_a_string_does_not_raise(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, '"not-a-dict"')

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)

    def test_top_level_agent_as_null_does_not_raise(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "null")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)

    def test_top_level_agent_as_a_bool_does_not_raise(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "true")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)

    def test_top_level_agent_as_an_int_does_not_raise(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "1")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)

    def test_top_level_agent_as_a_float_does_not_raise(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "1.5")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)

    def test_per_agent_block_that_is_a_non_dict_bool_does_not_raise(self, tmp_path: Path):
        """The secondary crash point: `agent:` IS a dict, but an individual
        per-agent block value is not -- `block.get("tools", {})` then
        raises `AttributeError` on the bool."""
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, '{"clean-agent": true}')

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert isinstance(exit_code, int)


class TestMalformedJsoncAgentBlockRefuses:
    """Sibling to `TestNonDictAgentBlockNeverRaises` above (that class's
    crash-safety guarantees are untouched) -- this class strengthens the
    assertion from "does not raise" to "actually forces a not-CLOSED
    verdict". A malformed opencode.jsonc `agent:` block (non-dict
    top-level, or a non-dict per-agent block) must surface as a
    GRAMMAR/FAIL finding that flows through `decide_config` to REFUSE
    (exit 1) by default, or PROCEED_UNCLOSED (exit 2, never 0) under
    `--override-ack`.

    Spec: `.gleipnir/plans/jsonc-agent-grammar-finding.md`, Assemble step 2
    / Stress-test items 1-2."""

    def _write_clean_fixture(self, config_root: Path, jsonc_agent_value: str) -> None:
        """Deliberately DIFFERENT from
        `TestNonDictAgentBlockNeverRaises._write_clean_fixture`: that class
        only needs crash-safety (any int exit code), so its bareword
        `clean-agent.md` is fine even though it leaves both MCP
        namespaces fail-open (WARN-only there is irrelevant to
        `isinstance(exit_code, int)`). THIS class asserts an EXACT verdict
        (`exit_code == 1`), so the fixture must otherwise be `CLOSED` on
        its own merits -- the single agent denies BOTH default MCP
        namespaces (`gleipnir-git_*`/`gleipnir-pm_*`), so absent the
        malformed `agent:` block the only findings would be
        `OVER_RESTRICTION`/`WARN` (non-strict, does not force refuse) --
        isolating `exit_code == 1` as caused SOLELY by the malformed jsonc
        `agent:` block under test, not by an unrelated fail-open finding."""
        agents_dir = config_root / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "clean-agent.md").write_text(
            "---\n"
            "tools:\n"
            '  "gleipnir-git_*": false\n'
            '  "gleipnir-pm_*": false\n'
            "---\n\n# clean agent\n"
        )
        (config_root.parent / "opencode.jsonc").write_text(
            '{"mcp": {}, "agent": ' + jsonc_agent_value + "}"
        )

    def test_top_level_agent_as_a_list_refuses(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "[]")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_top_level_agent_as_a_string_refuses(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, '"not-a-dict"')

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_top_level_agent_as_a_bool_refuses(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "true")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_top_level_agent_as_an_int_refuses(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "1")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_top_level_agent_as_null_refuses(self, tmp_path: Path):
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "null")

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_per_agent_block_non_dict_refuses(self, tmp_path: Path):
        """`agent:` IS a dict, but an individual per-agent block value is
        not -- must ALSO refuse, not just avoid crashing."""
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, '{"clean-agent": true}')

        exit_code = cs.config_scan_main([], config_root=config_root)
        assert exit_code == 1

    def test_override_ack_escalates_malformed_top_level_agent_to_exit_code_2(
        self, tmp_path: Path
    ):
        """`--override-ack` mirrors the existing REFUSE-escalation
        convention: PROCEED_UNCLOSED (exit 2), never CLOSED (exit 0)."""
        config_root = tmp_path / ".gleipnir"
        self._write_clean_fixture(config_root, "[]")

        exit_code = cs.config_scan_main(["--override-ack"], config_root=config_root)
        assert exit_code == 2
        assert exit_code != 0
