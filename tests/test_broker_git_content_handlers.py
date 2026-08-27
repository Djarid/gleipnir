"""Unit + structural + extensibility tests for the content-handler plugin
library and its ONE pilot handler, `DiffHunkTruncationHandler`.

Plan: `.gleipnir/plans/git-diff-distill.md`, Assemble Step 1, Stress-test
T-1..T-10. stdlib-only (no `mcp` import) -- runs under BOTH the default
`python` profile and, once `.gleipnir/sandbox/profiles.toml`
`[profile.broker].test` is amended (Tier-3, operator-only, Assemble Step 5),
the `broker` profile too.

Test-first note (Axiom 1): at authoring time
`src/gleipnir/broker/git/content_handlers/` and
`src/gleipnir/broker/git/diff_hunk_handler.py` do not exist yet, so every
test below is EXPECTED TO FAIL (ImportError) until Assemble Steps 2-3
implement them. That failure is the point.
"""

from __future__ import annotations

import inspect

import pytest

from gleipnir.broker.git.content_handlers import (
    Handler,
    ProcessedResult,
    dispatch,
    register,
)
from gleipnir.broker.git.content_handlers import registry as registry_module
from gleipnir.broker.git.diff_hunk_handler import (
    KEEP_LINES,
    THRESHOLD_LINES,
    DiffHunkTruncationHandler,
)

# ---------------------------------------------------------------------------
# Fixture diff builders
# ---------------------------------------------------------------------------

_HEADER_A = (
    "diff --git a/a.txt b/a.txt\n"
    "index 1111111..2222222 100644\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
)
_HEADER_B = (
    "diff --git a/b.txt b/b.txt\n"
    "index 3333333..4444444 100644\n"
    "--- a/b.txt\n"
    "+++ b/b.txt\n"
)


def _hunk(body_line_count: int, *, start: int = 1) -> str:
    """Build one `@@ ... @@` hunk header + `body_line_count` context lines."""
    header = f"@@ -{start},{body_line_count} +{start},{body_line_count} @@\n"
    body = "".join(f" line {i}\n" for i in range(1, body_line_count + 1))
    return header + body


def _diff_one_file(body_line_count: int, *, header: str = _HEADER_A) -> str:
    return header + _hunk(body_line_count)


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give each test a fresh, empty registry list.

    The registry is module-level global state (by design -- `mcp_server.py`
    registers once at import for production use). Tests isolate themselves
    by swapping in a fresh list rather than requiring any product-code reset
    API, so this fixture requires zero edits to `registry.py`.
    """
    monkeypatch.setattr(registry_module, "_handlers", [])


# ---------------------------------------------------------------------------
# Truncation rule (item 4 / T-1..T-5)
# ---------------------------------------------------------------------------


class TestTruncationRule:
    def test_below_threshold_hunk_passes_through_byte_for_byte(self) -> None:
        handler = DiffHunkTruncationHandler()
        diff = _diff_one_file(10)
        result = handler.process(diff)
        assert result.content == diff
        assert "truncated" not in result.content

    def test_above_threshold_hunk_is_truncated_with_exact_k(self) -> None:
        handler = DiffHunkTruncationHandler()
        diff = _diff_one_file(100)
        result = handler.process(diff)
        assert "# ... (84 lines truncated)" in result.content
        assert " line 1\n" in result.content
        assert " line 8\n" in result.content
        assert " line 93\n" in result.content
        assert " line 100\n" in result.content
        assert " line 50\n" not in result.content
        assert len(result.content) < len(diff)
        # Headers preserved verbatim.
        assert _HEADER_A in result.content

    def test_multi_file_diff_truncates_only_the_oversized_file(self) -> None:
        handler = DiffHunkTruncationHandler()
        small = _diff_one_file(5, header=_HEADER_A)
        large = _diff_one_file(100, header=_HEADER_B)
        diff = small + large
        result = handler.process(diff)
        assert _HEADER_A in result.content
        assert _HEADER_B in result.content
        assert " line 5\n" in result.content  # small file's body, verbatim
        assert "# ... (84 lines truncated)" in result.content
        # Small file's own hunk body must appear unbroken (no marker inside it).
        small_processed_start = result.content.index(_HEADER_A)
        small_processed_end = result.content.index(_HEADER_B)
        assert (
            "truncated" not in result.content[small_processed_start:small_processed_end]
        )

    def test_multi_hunk_file_truncates_only_the_oversized_hunk(self) -> None:
        handler = DiffHunkTruncationHandler()
        diff = _HEADER_A + _hunk(5, start=1) + _hunk(100, start=200)
        result = handler.process(diff)
        assert "# ... (84 lines truncated)" in result.content
        # The small hunk's 5 lines all survive unmarked.
        for i in range(1, 6):
            assert f" line {i}\n" in result.content

    def test_malformed_non_diff_input_returns_unchanged(self) -> None:
        handler = DiffHunkTruncationHandler()
        garbage = "this is not a unified diff at all\njust some text\n"
        result = handler.process(garbage)
        assert result.content == garbage

    def test_empty_diff_returns_unchanged_no_crash(self) -> None:
        handler = DiffHunkTruncationHandler()
        result = handler.process("")
        assert result.content == ""

    def test_never_silent_drop_marker_present_whenever_lines_removed(self) -> None:
        handler = DiffHunkTruncationHandler()
        diff = _diff_one_file(60)
        result = handler.process(diff)
        assert "truncated" in result.content
        assert len(result.content.splitlines()) < len(diff.splitlines())


# ---------------------------------------------------------------------------
# Boundary-value cases (T-1b / T-2b) -- pins `>` not `>=`
# ---------------------------------------------------------------------------


class TestBoundaryValues:
    def test_t1b_exactly_threshold_lines_unchanged_no_marker(self) -> None:
        """A hunk body of EXACTLY T=40 lines passes through unchanged."""
        handler = DiffHunkTruncationHandler()
        assert THRESHOLD_LINES == 40
        diff = _diff_one_file(40)
        result = handler.process(diff)
        assert result.content == diff
        assert "truncated" not in result.content

    def test_t2b_exactly_threshold_plus_one_is_truncated(self) -> None:
        """A hunk body of EXACTLY T+1=41 lines IS truncated: 41 - 16 = 25."""
        handler = DiffHunkTruncationHandler()
        assert THRESHOLD_LINES == 40
        assert KEEP_LINES == 8
        diff = _diff_one_file(41)
        result = handler.process(diff)
        assert "# ... (25 lines truncated)" in result.content
        assert " line 1\n" in result.content
        assert " line 8\n" in result.content
        assert " line 34\n" in result.content
        assert " line 41\n" in result.content
        assert " line 9\n" not in result.content
        assert " line 33\n" not in result.content


# ---------------------------------------------------------------------------
# Structural safety (item 5 / T-6, T-6b)
# ---------------------------------------------------------------------------


class TestStructuralSafety:
    def test_process_signature_takes_exactly_one_str_content_parameter(self) -> None:
        sig = inspect.signature(DiffHunkTruncationHandler.process)
        params = [p for name, p in sig.parameters.items() if name != "self"]
        assert len(params) == 1, (
            f"process() must take exactly one non-self parameter, got {params}"
        )
        (only_param,) = params
        assert only_param.annotation in (str, "str"), (
            f"process()'s sole parameter must be annotated str, got "
            f"{only_param.annotation!r}"
        )

    def test_processed_result_has_no_envelope_or_verdict_fields(self) -> None:
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(ProcessedResult)}
        forbidden = {"success", "error", "hash", "commit_hash", "secrets", "verdict"}
        assert field_names.isdisjoint(forbidden), (
            f"ProcessedResult must not expose envelope/verdict fields, found "
            f"{field_names & forbidden}"
        )
        assert field_names == {"content"}

    def test_handler_protocol_exposes_no_envelope_or_verdict_members(self) -> None:
        protocol_members = {
            name for name in dir(Handler) if not name.startswith("_")
        }
        forbidden = {"success", "error", "hash", "commit_hash", "secrets", "verdict"}
        assert protocol_members.isdisjoint(forbidden)
        assert protocol_members == {"can_handle", "process"}

    def test_hunk_body_containing_verdict_shaped_text_is_only_body_text(
        self,
    ) -> None:
        """A hunk body that happens to contain hash/verdict-shaped text is
        treated only as ordinary hunk-body text -- the handler has no
        concept of a secret-scan verdict, commit hash, or envelope field."""
        handler = DiffHunkTruncationHandler()
        body_lines = [f" line {i}\n" for i in range(1, 39)]
        body_lines.append(' "success": true, "hash": "deadbeef"\n')
        diff = _HEADER_A + "@@ -1,39 +1,39 @@\n" + "".join(body_lines)
        result = handler.process(diff)
        # 39 lines <= 40 -> unchanged, and the verdict-shaped text is inert.
        assert result.content == diff


# ---------------------------------------------------------------------------
# Extensibility (item 3, MANDATORY -- T-8)
# ---------------------------------------------------------------------------


class _StubHandler:
    """Defined entirely in this test module -- proves registration is pure
    and external: NEITHER `registry.py` NOR `diff_hunk_handler.py` needs any
    edit to make this handler dispatchable."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def can_handle(self, content: str, hint: str) -> bool:
        return hint == "stub-hint"

    def process(self, content: str) -> ProcessedResult:
        self.calls.append(content)
        return ProcessedResult(content=content.upper())


class TestExtensibility:
    def test_second_stub_handler_is_dispatched_for_its_own_hint(self) -> None:
        stub = _StubHandler()
        register(stub)
        result = dispatch("hello", "stub-hint")
        assert result.content == "HELLO"
        assert stub.calls == ["hello"]

    def test_diff_handler_still_dispatches_correctly_alongside_the_stub(
        self,
    ) -> None:
        stub = _StubHandler()
        register(stub)
        register(DiffHunkTruncationHandler())
        diff = _diff_one_file(100)
        result = dispatch(diff, "diff")
        assert "# ... (84 lines truncated)" in result.content
        # The stub was not invoked for the "diff" hint.
        assert stub.calls == []

    def test_no_edit_to_registry_or_handler_module_was_needed(self) -> None:
        """Documentary assertion: `_StubHandler` above satisfies the `Handler`
        protocol using ONLY the public `register`/`dispatch` surface imported
        from `content_handlers`. No import of, or reference to, an
        extension point inside `registry.py` or `diff_hunk_handler.py` is
        required -- their public surface (`register`, `dispatch`, the
        `Handler` protocol) is sufficient for a brand-new handler."""
        assert isinstance(_StubHandler(), Handler)


# ---------------------------------------------------------------------------
# No-handler fallback (T-9)
# ---------------------------------------------------------------------------


class TestNoHandlerFallback:
    def test_dispatch_with_empty_registry_returns_content_unchanged(self) -> None:
        result = dispatch("some content", "diff")
        assert result == ProcessedResult(content="some content")

    def test_dispatch_with_non_matching_hint_returns_content_unchanged(self) -> None:
        register(DiffHunkTruncationHandler())
        result = dispatch("some content", "not-a-known-hint")
        assert result.content == "some content"


# ---------------------------------------------------------------------------
# Single-responsibility falsifiable claims (Design Principles) -- source scan
# ---------------------------------------------------------------------------


class TestRegistrySingleResponsibility:
    def test_registry_module_source_contains_no_diff_specific_tokens(self) -> None:
        import gleipnir.broker.git.content_handlers.registry as reg_mod

        source = inspect.getsource(reg_mod)
        forbidden_substrings = ("diff", "hunk", "@@", "diff_hunk_handler")
        lowered = source.lower()
        for token in forbidden_substrings:
            assert token.lower() not in lowered, (
                f"registry.py contains forbidden diff-specific token {token!r} "
                "-- violates the dispatcher's single-responsibility claim"
            )

    def test_diff_handler_module_source_contains_no_dispatch_logic(self) -> None:
        """The diff handler MAY import `ProcessedResult`/`Handler` from the
        `content_handlers` protocol (it must return/implement that contract)
        but must NOT import or reference the registry/dispatcher itself, and
        must not call `register(...)` on itself (registration is the
        caller's job -- see plan Assemble Step 3)."""
        import gleipnir.broker.git.diff_hunk_handler as handler_mod

        source = inspect.getsource(handler_mod)
        assert "registry" not in source.lower(), (
            "diff_hunk_handler.py must not reference the registry module"
        )
        assert "def dispatch" not in source
        assert "register(" not in source, (
            "diff_hunk_handler.py must not self-register -- registration "
            "is the caller's (mcp_server.py's) job"
        )
