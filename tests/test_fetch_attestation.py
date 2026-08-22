"""Tests for Seam 8 live CI attestation fetch
(`src/gleipnir/preflight/fetch_attestation.py`).

Spec: `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble "Phase 3 — Seam 8
live fetch + GATE", and Stress-test criteria 5, 6, 7, 10.

**Never a real network call.** Every `fetch_attestation` test in this file
monkeypatches the module's own single documented seam, `_http_get_json`
("Tests monkeypatch this attribute directly, so no live network call is
ever exercised in the unit-test suite" — module docstring). A separate,
narrower set of tests exercises `_http_get_json` itself by monkeypatching
one level deeper, at `urllib.request.urlopen`, purely to confirm the
Authorization-header behaviour (token present -> header set; token absent
-> header absent) without ever opening a socket.

Stress-test criteria covered here:
  5.  GATE only on GREEN+match — the fetch half: GREEN/RED/PENDING/ABSENT
      construction (`TestFetchAttestationRunFound`,
      `TestFetchAttestationNoRunFound`).
  6.  pipeline_id<->SHA correlation — this module's half of that contract is
      "echo pipeline_id verbatim, never validate it"; the actual mismatch
      REFUSAL is `Engine.attempt_gate`'s job, exercised in
      `tests/test_advance_entrypoint.py::TestGitStateGateWiring`, not here
      (`TestPipelineIdEchoedVerbatim`).
  7.  Status map: every documented GitHub conclusion string maps to the
      correct `AttestationStatus`, table-driven, no live network
      (`TestMapConclusionToStatus`).
  10. stdlib-only: `fetch_attestation.py` imports only `json`, `os`,
      `urllib.*`, `typing` — already covered automatically by
      `tests/test_preflight_stdlib_only.py`'s `_preflight_py_files()`,
      which globs every `*.py` under `src/gleipnir/preflight/` (this file
      included, no extension needed there); `TestStdlibOnly` below re-
      asserts the same fact scoped to this one module, for a failure
      message that points straight at the fetch module.
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
import urllib.error
from pathlib import Path

import pytest

from gleipnir.engine import Attestation, AttestationStatus
from gleipnir.preflight import fetch_attestation as fa

PIPELINE_ID = "pl-fetch-attestation-test-1"
HEAD_SHA = "deadbeef" * 5
OWNER = "acme-org"
REPO = "widget-repo"


def _runs_payload(conclusion: str | None) -> dict:
    return {"workflow_runs": [{"conclusion": conclusion}]}


# ---------------------------------------------------------------------------
# map_conclusion_to_status -- pure, table-driven over the module's own
# documented GitHub conclusion enum (module docstring "GitHub conclusion
# enum -- verified, not guessed").
# ---------------------------------------------------------------------------


class TestMapConclusionToStatus:
    @pytest.mark.parametrize(
        "conclusion,expected",
        [
            ("success", AttestationStatus.GREEN),
            ("failure", AttestationStatus.RED),
            ("cancelled", AttestationStatus.RED),
            ("timed_out", AttestationStatus.RED),
            ("neutral", AttestationStatus.RED),
            ("skipped", AttestationStatus.RED),
            ("action_required", AttestationStatus.RED),
            ("stale", AttestationStatus.RED),
            (None, AttestationStatus.PENDING),
        ],
    )
    def test_documented_conclusion_values_map_correctly(
        self, conclusion: str | None, expected: AttestationStatus
    ) -> None:
        assert fa.map_conclusion_to_status(conclusion) is expected

    def test_unrecognized_but_present_conclusion_maps_to_red_never_green(self) -> None:
        """The fail-closed property this module's docstring names by name:
        a conclusion string outside GitHub's documented enum entirely (a
        hypothetical future value) must NEVER be defaulted to GREEN."""

        assert (
            fa.map_conclusion_to_status("some_future_unknown_conclusion")
            is AttestationStatus.RED
        )

    @pytest.mark.parametrize(
        "conclusion",
        [
            "failure",
            "cancelled",
            "timed_out",
            "neutral",
            "skipped",
            "action_required",
            "stale",
            "brand_new_value_github_might_add_later",
            "SUCCESS",  # case-sensitive: not the literal "success"
            "Success",
        ],
    )
    def test_only_the_literal_string_success_ever_yields_green(
        self, conclusion: str
    ) -> None:
        assert fa.map_conclusion_to_status(conclusion) is not AttestationStatus.GREEN

    @pytest.mark.parametrize(
        "conclusion", [None, "success", "failure", "anything else at all"]
    )
    def test_pure_mapping_function_never_returns_absent(
        self, conclusion: str | None
    ) -> None:
        """ABSENT is assigned only by `fetch_attestation` itself for the
        zero-matching-runs case (a fact about the QUERY, not about any run's
        `conclusion` field) -- per this pure function's own docstring, it
        never returns ABSENT."""

        assert fa.map_conclusion_to_status(conclusion) is not AttestationStatus.ABSENT


# ---------------------------------------------------------------------------
# fetch_attestation -- run found, conclusion present or still-pending
# ---------------------------------------------------------------------------


class TestFetchAttestationRunFound:
    def test_green_when_conclusion_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: _runs_payload("success")
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result == Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.GREEN)

    def test_red_when_conclusion_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: _runs_payload("failure")
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result == Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.RED)

    def test_pending_when_conclusion_is_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`conclusion: null` -- the run exists (`status` is
        `queued`/`in_progress`) but has not completed yet."""

        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: _runs_payload(None)
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result == Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.PENDING)


# ---------------------------------------------------------------------------
# fetch_attestation -- zero runs found / structurally malformed responses
# ---------------------------------------------------------------------------


class TestFetchAttestationNoRunFound:
    def test_zero_runs_returns_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: {"workflow_runs": []}
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result == Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.ABSENT)

    def test_missing_workflow_runs_key_returns_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fa, "_http_get_json", lambda url, token, *, timeout: {})
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    def test_non_dict_payload_returns_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: ["not", "a", "dict"]
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    def test_workflow_runs_not_a_list_returns_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            fa,
            "_http_get_json",
            lambda url, token, *, timeout: {"workflow_runs": "not-a-list"},
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    def test_run_entry_not_a_dict_returns_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            fa,
            "_http_get_json",
            lambda url, token, *, timeout: {"workflow_runs": ["not-a-dict"]},
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    def test_conclusion_field_wrong_type_returns_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A structurally malformed `conclusion` (e.g. an int, not a string
        or null) fails closed rather than being guessed at."""

        monkeypatch.setattr(
            fa,
            "_http_get_json",
            lambda url, token, *, timeout: {"workflow_runs": [{"conclusion": 42}]},
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT


# ---------------------------------------------------------------------------
# fetch_attestation -- network/timeout/malformed-JSON error -> ABSENT
# (fail-closed, never a fabricated completed state)
# ---------------------------------------------------------------------------


class TestFetchAttestationFailClosedOnError:
    def test_network_error_returns_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(url: str, token: str | None, *, timeout: float):
            raise urllib.error.URLError("network unreachable")

        monkeypatch.setattr(fa, "_http_get_json", _raise)
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result == Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.ABSENT)

    def test_timeout_returns_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(url: str, token: str | None, *, timeout: float):
            raise TimeoutError("timed out")

        monkeypatch.setattr(fa, "_http_get_json", _raise)
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    def test_malformed_json_returns_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(url: str, token: str | None, *, timeout: float):
            raise json.JSONDecodeError("bad json", "doc", 0)

        monkeypatch.setattr(fa, "_http_get_json", _raise)
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    def test_generic_os_error_returns_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(url: str, token: str | None, *, timeout: float):
            raise OSError("some unexpected OS-level failure")

        monkeypatch.setattr(fa, "_http_get_json", _raise)
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is AttestationStatus.ABSENT

    @pytest.mark.parametrize(
        "exc",
        [
            urllib.error.URLError("x"),
            TimeoutError("x"),
            OSError("x"),
            ValueError("x"),
            json.JSONDecodeError("x", "doc", 0),
        ],
    )
    def test_every_failure_mode_never_produces_green(
        self, monkeypatch: pytest.MonkeyPatch, exc: Exception
    ) -> None:
        def _raise(url: str, token: str | None, *, timeout: float):
            raise exc

        monkeypatch.setattr(fa, "_http_get_json", _raise)
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.status is not AttestationStatus.GREEN


# ---------------------------------------------------------------------------
# fetch_attestation -- owner/repo unresolvable -> ABSENT WITHOUT querying
# ---------------------------------------------------------------------------


class TestFetchAttestationOwnerRepoUnresolvable:
    def test_no_owner_no_repo_returns_absent_without_querying(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(
            fa, "_http_get_json", lambda *a, **k: calls.append("called") or {}
        )
        monkeypatch.delenv(fa.OWNER_ENV_VAR, raising=False)
        monkeypatch.delenv(fa.REPO_ENV_VAR, raising=False)

        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA)

        assert result == Attestation(pipeline_id=PIPELINE_ID, status=AttestationStatus.ABSENT)
        assert calls == [], "owner/repo unresolvable must short-circuit before any query"

    def test_owner_present_repo_missing_returns_absent_without_querying(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(
            fa, "_http_get_json", lambda *a, **k: calls.append("called") or {}
        )
        monkeypatch.delenv(fa.REPO_ENV_VAR, raising=False)

        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=None)

        assert result.status is AttestationStatus.ABSENT
        assert calls == []

    def test_owner_missing_repo_present_returns_absent_without_querying(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(
            fa, "_http_get_json", lambda *a, **k: calls.append("called") or {}
        )
        monkeypatch.delenv(fa.OWNER_ENV_VAR, raising=False)

        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=None, repo=REPO)

        assert result.status is AttestationStatus.ABSENT
        assert calls == []

    def test_env_vars_resolve_owner_and_repo_when_not_passed_explicitly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(fa.OWNER_ENV_VAR, OWNER)
        monkeypatch.setenv(fa.REPO_ENV_VAR, REPO)
        seen_urls: list[str] = []

        def _capture(url: str, token: str | None, *, timeout: float):
            seen_urls.append(url)
            return _runs_payload("success")

        monkeypatch.setattr(fa, "_http_get_json", _capture)

        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA)

        assert result.status is AttestationStatus.GREEN
        assert seen_urls, "the env-resolved owner/repo path must reach a query"
        assert OWNER in seen_urls[0]
        assert REPO in seen_urls[0]


# ---------------------------------------------------------------------------
# pipeline_id is echoed verbatim, NEVER asserted/validated by this module --
# the pipeline_id<->engine correlation check is `Engine.attempt_gate`'s job.
# ---------------------------------------------------------------------------


class TestPipelineIdEchoedVerbatim:
    @pytest.mark.parametrize(
        "pipeline_id",
        [
            "pl-a",
            "pl-totally-different-run",
            "",
            "weird/id with spaces??",
        ],
    )
    def test_pipeline_id_never_validated_just_echoed_on_the_green_path(
        self, monkeypatch: pytest.MonkeyPatch, pipeline_id: str
    ) -> None:
        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: _runs_payload("success")
        )
        result = fa.fetch_attestation(pipeline_id, HEAD_SHA, owner=OWNER, repo=REPO)
        assert result.pipeline_id == pipeline_id

    def test_pipeline_id_echoed_even_on_the_absent_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(fa.OWNER_ENV_VAR, raising=False)
        monkeypatch.delenv(fa.REPO_ENV_VAR, raising=False)
        result = fa.fetch_attestation("pl-arbitrary-xyz", HEAD_SHA)
        assert result.pipeline_id == "pl-arbitrary-xyz"

    def test_head_sha_never_appears_in_the_returned_attestation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`Attestation` (engine/__init__.py) has exactly two fields,
        `pipeline_id` and `status` -- `head_sha` is consumed only to build
        the query, never carried forward."""

        monkeypatch.setattr(
            fa, "_http_get_json", lambda url, token, *, timeout: _runs_payload("success")
        )
        result = fa.fetch_attestation(PIPELINE_ID, HEAD_SHA, owner=OWNER, repo=REPO)
        assert not hasattr(result, "head_sha")


# ---------------------------------------------------------------------------
# _workflow_runs_url -- pure URL construction (no I/O)
# ---------------------------------------------------------------------------


class TestWorkflowRunsUrlConstruction:
    def test_url_contains_owner_repo_workflow_and_head_sha(self) -> None:
        url = fa._workflow_runs_url(OWNER, REPO, "config-scan.yml", "abc123")
        assert url.startswith("https://api.github.com/repos/")
        assert OWNER in url
        assert REPO in url
        assert "config-scan.yml" in url
        assert "head_sha=abc123" in url
        assert "per_page=1" in url


# ---------------------------------------------------------------------------
# _http_get_json -- the ONE urllib boundary. These tests monkeypatch one
# level deeper (`urllib.request.urlopen`) purely to confirm the
# Authorization-header behaviour without ever opening a socket -- they do
# NOT replace the "tests monkeypatch `_http_get_json` directly" contract
# the rest of this file follows; they exist only to give this one function
# its own direct coverage and to prove the token-never-logged property at
# the actual header-construction site.
# ---------------------------------------------------------------------------


class _FakeUrlopenResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeUrlopenResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


class TestHttpGetJsonRequestConstruction:
    def test_authorization_header_set_when_token_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def _fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
            captured["headers"] = {k.lower(): v for k, v in request.header_items()}
            captured["url"] = request.full_url
            return _FakeUrlopenResponse(b'{"workflow_runs": []}')

        monkeypatch.setattr(fa.urllib.request, "urlopen", _fake_urlopen)

        result = fa._http_get_json(
            "https://api.github.com/x", "secret-token-value", timeout=5.0
        )

        assert result == {"workflow_runs": []}
        assert captured["headers"]["authorization"] == "Bearer secret-token-value"

    def test_no_authorization_header_when_token_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def _fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
            captured["headers"] = {k.lower(): v for k, v in request.header_items()}
            return _FakeUrlopenResponse(b'{"workflow_runs": []}')

        monkeypatch.setattr(fa.urllib.request, "urlopen", _fake_urlopen)

        fa._http_get_json("https://api.github.com/x", None, timeout=5.0)

        assert "authorization" not in captured["headers"]


# ---------------------------------------------------------------------------
# Token never hardcoded or logged (grep-shaped static check, mirrors the
# module's own D3(b) honest-tradeoff docstring claim).
# ---------------------------------------------------------------------------


class TestTokenNeverHardcodedOrLogged:
    def test_module_source_contains_no_print_calls(self) -> None:
        """This module never prints anything -- there is no output
        statement anywhere in it that could leak a header/token."""

        source = inspect.getsource(fa)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", (
                    "fetch_attestation.py must never print -- the token is "
                    "reachable here and a print call is exactly how it "
                    "could leak"
                )

    def test_module_source_has_no_hardcoded_token_literal(self) -> None:
        source = inspect.getsource(fa)
        for banned_prefix in ("ghp_", "github_pat_", "gho_", "ghu_", "ghs_"):
            assert banned_prefix not in source, (
                f"found a hardcoded-looking GitHub token literal prefix "
                f"{banned_prefix!r} in fetch_attestation.py"
            )

    def test_token_is_read_from_environ_not_a_literal(self) -> None:
        source = inspect.getsource(fa._query_workflow_run_conclusion)
        assert "os.environ.get(GITHUB_TOKEN_ENV_VAR)" in source


# ---------------------------------------------------------------------------
# stdlib-only (Stress-test #10) -- already covered automatically by
# tests/test_preflight_stdlib_only.py's glob over every *.py file under
# src/gleipnir/preflight/ (fetch_attestation.py included, no extension
# needed there). Re-asserted here, scoped to this one module, so a
# regression here fails with a message that names this file directly.
# ---------------------------------------------------------------------------


class TestStdlibOnly:
    def test_only_stdlib_top_level_imports(self) -> None:
        fetch_attestation_path = Path(fa.__file__)
        tree = ast.parse(fetch_attestation_path.read_text())
        stdlib = set(sys.stdlib_module_names)
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                if node.module:
                    roots.add(node.module.split(".")[0])
        for root in roots:
            if root in ("gleipnir", "__future__"):
                continue
            assert root in stdlib, (
                f"fetch_attestation.py imports non-stdlib module {root!r}; "
                "the enforcement core is stdlib-only "
                "(.gleipnir/decisions/runtime-and-deps.md)"
            )
        # The three modules the docstring names by name must actually be
        # among the resolved roots -- guards against the check above
        # vacuously passing because nothing was parsed.
        assert {"json", "os", "urllib"} <= roots
