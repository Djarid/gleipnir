"""D5 sidecar WRITE-side tests for `commit_changes` (`mcp_server.py`).

Plan: `.gleipnir/plans/d5-sidecar-write.md`, Assemble step 1 ("Author
`tests/test_broker_run_manifest.py` ... BEFORE the implementation is
applied"). Target behaviour (does NOT exist yet -- this is the point,
Axiom 1 / test-first): `commit_changes` must, after a successful commit
when ARMED (`GLEIPNIR_PIPELINE_ID` set, non-empty), best-effort-write
`.gleipnir/var/run/pipeline-run.json` = `{"pipeline_id": <env>, "head_sha":
<commit hash>}` via a new module-level helper (`_write_run_manifest_head_sha`,
`_repo_root`, `_PIPELINE_ID_ENV`, `_PIPELINE_RUN_REL` per the plan's Hunk B) --
none of which exist on `mcp_server` yet at test-authoring time.

Stress-test coverage (plan "## Stress-test", 1-8), each test class/method
tagged with its number:
  1. `TestArmedHappyPathWriteAndRoundTrip` -- armed happy path (core).
  2. `TestArmedHappyPathWriteAndRoundTrip` -- round-trip against the REAL
     `advance.read_pipeline_run_identity` (not a reimplementation/mock).
  3. `TestUnarmedNoOp` -- unarmed no-op (incl. pre-existing-file-untouched).
  4. `TestFailSafeWriteFailureNeverFailsCommit` -- fail-safe (write OSError
     never fails the commit).
  5. `TestBothKeysTogetherInvariant` -- both keys always present together.
  6. `TestMissingOrMalformedSidecarStillFailsClosed` -- explicit regression
     guard: the read side's fail-closed contract is unweakened. Exercises
     ONLY already-built code (`advance.py`/`Driver`) -- no dependency on the
     new write side, so it is a genuine regression guard, not a new-feature
     test, and is expected to PASS even before Hunks A-C land.
  7. `TestNoMacPlainFileInvariant` -- exactly `{"pipeline_id", "head_sha"}`,
     no MAC/digest field.
  8. `TestBridgeMarkerUntouchedAndBrokerSurfacePreserved` -- blast-radius:
     no `bridge`/`StateMarker` reference; `commit_changes`'s public
     signature/contract additive-only-preserved.

**T1 resolution (this file's choice).** The plan flags a non-material
testability seam: the write helper resolves its sidecar path from `__file__`
(mirroring `advance.py`'s `_repo_root()`), so a clean `tmp_path` test needs
either (a) tolerate-the-real-root-write-and-clean-up, or (b) an injectable
`run_root=` seam. This file uses a HYBRID that keeps `commit_changes`'s own
agent-facing signature untouched (required by the plan's Interface
Segregation principle / P1 -- no new parameter on that MCP tool schema):
  - The write helper `_write_run_manifest_head_sha(commit_hash, *,
    run_root=None)` gets the T1 Option (b) injectable `run_root` kwarg,
    exercised DIRECTLY (unmonkeypatched) by `TestWriteHelperDirectRunRootInjection`.
  - Every test that drives the FULL `commit_changes()` call (which invokes
    the helper with NO `run_root` override, exactly as production does)
    instead monkeypatches the module-level `_repo_root()` helper (via the
    `patched_repo_root` fixture below) so the helper's own default-path
    resolution lands under `tmp_path` -- no tolerate-and-clean-up needed,
    and no new parameter appears anywhere on the public tool surface.

**Collection-time self-reference (lesson L-C30).** `_write_run_manifest_head_sha`,
`_repo_root`, `_PIPELINE_ID_ENV`, and `_PIPELINE_RUN_REL` do not exist on
`mcp_server` yet. The GENERAL rule this file follows: nothing under test may
be evaluated or called except inside a body that runs at test/fixture
INVOCATION time, never at collection time -- by whatever mechanism collection
would otherwise trigger (module-scope statements, parametrize/fixture-param
argument LISTS, or default-argument expressions). Concretely here: (a) no
`from gleipnir.broker.git.mcp_server import <not-yet-existing-name>` anywhere
(only the module itself is imported at top level; every not-yet-existing
attribute is accessed via `mcp_server.<name>` inside a function/fixture BODY);
(b) `monkeypatch.setattr(mcp_server, "_repo_root", ..., raising=False)` uses
`raising=False` specifically because the attribute does not exist yet; (c)
every `@pytest.mark.parametrize` list below (there are none in this file) and
every fixture default is a plain literal, never a call into the pending
write-side code. `--collect-only` must succeed against this file at all
times, including right now, before Hunks A-C land.

Runs under the **broker profile** (imports `mcp` transitively via
`mcp_server`) -- see `tests/conftest.py` `collect_ignore`. Per the existing
precedent (`tests/test_broker_git_mcp_server.py`, `tests/test_broker_git_commit_guard.py`),
amending `.gleipnir/sandbox/profiles.toml`'s `[profile.broker].test` file
list to add this module is a Tier-3, operator-only action, not performed by
this delegation (`gleipnir-code` denies all of `.gleipnir/**`).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from gleipnir.broker.git import mcp_server
from gleipnir.engine import PipelineState
from gleipnir.engine.driver import Driver
from gleipnir.preflight import advance

# ---------------------------------------------------------------------------
# Shared helpers/fixtures (replicated proven shapes from
# tests/test_broker_git_mcp_server.py and tests/test_advance_entrypoint.py
# rather than imported, per this codebase's established convention of
# per-file-replicated test scaffolding -- see e.g.
# test_broker_git_mcp_server.py's own docstring on this point).
# ---------------------------------------------------------------------------

import subprocess
from typing import List

_GIT_ENV_VARS = (
    "GLEIPNIR_GIT_STRICT",
    "GLEIPNIR_GIT_PROTECT_BRANCHES",
    "GLEIPNIR_GIT_CHECK_DATA_FILES",
    "GLEIPNIR_GIT_PROTECTED_BRANCHES",
)

# P1: the env var `commit_changes` must read `pipeline_id` from (armed-only,
# never an agent-facing tool parameter). A plain literal -- deliberately NOT
# read from `mcp_server._PIPELINE_ID_ENV` at module scope, since that name
# does not exist yet (L-C30 collection safety).
_PIPELINE_ID_ENV_NAME = "GLEIPNIR_PIPELINE_ID"


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset every opt-in broker toggle AND the pipeline-id arming var, so
    each test starts from an unarmed, default-posture baseline and opts in
    explicitly."""
    for var in _GIT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv(_PIPELINE_ID_ENV_NAME, raising=False)


def _git(args: List[str], cwd: str) -> str:
    """Run a real `git` command for test setup/verification (NOT the broker)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"test-setup `git {' '.join(args)}` failed in {cwd}: {result.stderr}"
    )
    return result.stdout


@pytest.fixture
def repo(tmp_path: Path) -> str:
    """A real temp git repo, branch `main`, with one prior commit."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    rd = str(repo_dir)
    _git(["init"], rd)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], rd)
    _git(["config", "user.email", "gleipnir-test@example.invalid"], rd)
    _git(["config", "user.name", "Gleipnir Test"], rd)
    (repo_dir / "README.md").write_text("initial\n")
    _git(["add", "README.md"], rd)
    _git(["commit", "-m", "initial commit"], rd)
    return rd


@pytest.fixture
def patched_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """T1 (this file's hybrid resolution, see module docstring): redirect the
    module-level `_repo_root()` helper (NOT the public `commit_changes`
    signature) to a `tmp_path`-rooted stand-in, so a real `commit_changes()`
    call's default-path sidecar write lands under `tmp_path` instead of this
    framework's actual `.gleipnir/var/run/` tree. `raising=False` because
    `_repo_root` does not exist on `mcp_server` yet (test-first)."""
    fake_root = tmp_path / "fake-repo-root"
    monkeypatch.setattr(mcp_server, "_repo_root", lambda: fake_root, raising=False)
    return fake_root


def _sidecar_path(fake_root: Path) -> Path:
    """Mirrors `advance.py`'s `DEFAULT_RUN_ROOT` / `PIPELINE_RUN_FILENAME`
    construction: `<repo_root>/.gleipnir/var/run/pipeline-run.json`."""
    return fake_root / ".gleipnir" / "var" / "run" / "pipeline-run.json"


# ---------------------------------------------------------------------------
# Stress-test #1 + #2 -- armed happy path (core) + round-trip against the
# REAL read_pipeline_run_identity (the assertion that would have caught the
# original gap).
# ---------------------------------------------------------------------------


class TestArmedHappyPathWriteAndRoundTrip:
    def test_armed_commit_writes_sidecar_with_correct_shape(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stress-test #1: with `GLEIPNIR_PIPELINE_ID` set, a real temp git
        repo, and a successful `commit_changes(...)`, the returned JSON has
        `success: True` and a non-empty `hash`, AND the sidecar (at the
        resolved run root) contains `pipeline_id == <env value>` and
        `head_sha == <returned hash>`."""
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-happy-path-1")

        (Path(repo) / "changed.txt").write_text("v1\n")
        raw = mcp_server.commit_changes(message="armed commit", repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert result["hash"]

        sidecar = _sidecar_path(patched_repo_root)
        assert sidecar.is_file(), (
            "expected the D5 sidecar to be written on a successful armed commit"
        )
        written = json.loads(sidecar.read_text(encoding="utf-8"))
        assert written == {"pipeline_id": "pl-happy-path-1", "head_sha": result["hash"]}

    def test_round_trip_against_real_read_pipeline_run_identity(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stress-test #2 (strongest): feeds the just-written sidecar to the
        REAL, already-built `advance.read_pipeline_run_identity` -- imported
        and called directly, NOT reimplemented/mocked -- so this proves the
        write side this stage authors genuinely interoperates with the
        already-built read side, at the exact path/keys/shape contract."""
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-roundtrip-2")

        (Path(repo) / "changed2.txt").write_text("v1\n")
        raw = mcp_server.commit_changes(
            message="armed commit for roundtrip", repo_dir=repo
        )
        result = json.loads(raw)
        assert result["success"] is True

        identity = advance.read_pipeline_run_identity(
            run_root=patched_repo_root / ".gleipnir" / "var" / "run"
        )
        assert identity == ("pl-roundtrip-2", result["hash"])


# ---------------------------------------------------------------------------
# Stress-test #3 -- unarmed no-op.
# ---------------------------------------------------------------------------


class TestUnarmedNoOp:
    def test_unarmed_commit_writes_no_sidecar(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`GLEIPNIR_PIPELINE_ID` unset -> `commit_changes` succeeds and NO
        `pipeline-run.json` is created; return JSON unchanged in shape."""
        _clear_env(monkeypatch)

        (Path(repo) / "unarmed.txt").write_text("v1\n")
        raw = mcp_server.commit_changes(message="unarmed commit", repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert result["hash"]
        assert set(result.keys()) == {"success", "hash", "message", "branch"}

        sidecar = _sidecar_path(patched_repo_root)
        assert not sidecar.exists(), "unarmed commit must never write the D5 sidecar"

    def test_unarmed_commit_leaves_a_pre_existing_sidecar_untouched(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pre-existing sidecar (from an earlier armed run) is left
        byte-for-byte untouched by a later UNARMED commit."""
        _clear_env(monkeypatch)
        sidecar = _sidecar_path(patched_repo_root)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        pre_existing = json.dumps({"pipeline_id": "stale", "head_sha": "stale-sha"})
        sidecar.write_text(pre_existing, encoding="utf-8")

        (Path(repo) / "unarmed2.txt").write_text("v1\n")
        raw = mcp_server.commit_changes(message="unarmed commit 2", repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert sidecar.read_text(encoding="utf-8") == pre_existing


# ---------------------------------------------------------------------------
# Stress-test #4 -- fail-safe: a sidecar-write failure NEVER fails the
# already-succeeded commit.
# ---------------------------------------------------------------------------


class TestFailSafeWriteFailureNeverFailsCommit:
    def test_write_text_oserror_does_not_fail_the_commit(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulates the write path raising `OSError` at the final
        `Path.write_text` step (mirrors the read side's `Path.read_text`
        idiom in `advance.py`, and the plan's stated `os`/`pathlib.Path`
        imports) -> `commit_changes` still returns `success: True` with the
        correct hash. The write helper is documented (plan Design
        Principles) to swallow its OWN failure, so `commit_changes` itself
        needs no try/except around the call site."""
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-failsafe-3")

        (Path(repo) / "failsafe.txt").write_text("v1\n")

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("simulated disk failure")

        monkeypatch.setattr(Path, "write_text", _boom, raising=True)

        raw = mcp_server.commit_changes(message="failsafe commit", repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert result["hash"]

    def test_mkdir_oserror_does_not_fail_the_commit(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same fail-safe contract, but the simulated failure is at the
        parent-directory-creation step (e.g. a permissions error on
        `.gleipnir/var/run`) rather than the final write."""
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-failsafe-4")

        (Path(repo) / "failsafe2.txt").write_text("v1\n")

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("simulated permission failure")

        monkeypatch.setattr(Path, "mkdir", _boom, raising=True)

        raw = mcp_server.commit_changes(message="failsafe commit 2", repo_dir=repo)
        result = json.loads(raw)

        assert result["success"] is True
        assert result["hash"]


# ---------------------------------------------------------------------------
# Stress-test #5 -- both-keys-together invariant.
# ---------------------------------------------------------------------------


class TestBothKeysTogetherInvariant:
    def test_written_sidecar_has_both_pipeline_id_and_head_sha_non_empty(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When armed, the written file ALWAYS contains BOTH `pipeline_id`
        and `head_sha` as non-empty strings -- never one alone. Catches a
        regression that writes only `head_sha` (or only `pipeline_id`)."""
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-bothkeys-5")

        (Path(repo) / "bothkeys.txt").write_text("v1\n")
        mcp_server.commit_changes(message="bothkeys commit", repo_dir=repo)

        sidecar = _sidecar_path(patched_repo_root)
        written = json.loads(sidecar.read_text(encoding="utf-8"))
        assert isinstance(written.get("pipeline_id"), str) and written["pipeline_id"]
        assert isinstance(written.get("head_sha"), str) and written["head_sha"]


# ---------------------------------------------------------------------------
# Stress-test #6 -- explicit regression guard: missing/malformed sidecar
# STILL fail-closes as MissingRunIdentity. Exercises ONLY already-built code
# (advance.py / Driver) -- no dependency on the not-yet-built write side.
# ---------------------------------------------------------------------------


class TestMissingOrMalformedSidecarStillFailsClosed:
    """Regression guard: this write-side addition must NOT weaken the read
    side's existing fail-closed contract. Every test in this class is
    expected to PASS right now, before Hunks A-C land, because it touches
    only already-built code."""

    def test_missing_sidecar_read_returns_none(self, tmp_path: Path) -> None:
        assert advance.read_pipeline_run_identity(run_root=tmp_path) is None

    def test_malformed_sidecar_read_returns_none(self, tmp_path: Path) -> None:
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / advance.PIPELINE_RUN_FILENAME).write_text(
            "not json at all", encoding="utf-8"
        )
        assert advance.read_pipeline_run_identity(run_root=tmp_path) is None

    def test_advance_main_raises_missing_run_identity_at_git_state(
        self, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"verifier-only-secret-key-not-on-agent-surface")
        bridge_path = tmp_path / "var" / "run" / "pipeline-state.json"

        driver = Driver("pl-regression-guard-6", bridge_path, key_file=key_file)
        driver.write_bridge()
        while driver.state is not PipelineState.GIT:
            driver.advance_on_clean_completion()
        before = bridge_path.read_bytes()

        with pytest.raises(advance.MissingRunIdentity):
            advance.advance_main(
                "pl-regression-guard-6",
                bridge_path,
                key_file=key_file,
                run_root=tmp_path / "no-such-run-root",
            )

        # Fail-closed means the bridge is left exactly as it was -- no
        # silent advance to GATE just because a sidecar happens to be absent.
        assert bridge_path.read_bytes() == before

    def test_advance_main_raises_missing_run_identity_on_malformed_sidecar(
        self, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"verifier-only-secret-key-not-on-agent-surface")
        bridge_path = tmp_path / "var" / "run" / "pipeline-state.json"

        driver = Driver("pl-regression-guard-7", bridge_path, key_file=key_file)
        driver.write_bridge()
        while driver.state is not PipelineState.GIT:
            driver.advance_on_clean_completion()

        run_root = tmp_path / "run-root"
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / advance.PIPELINE_RUN_FILENAME).write_text(
            "{not valid json", encoding="utf-8"
        )

        with pytest.raises(advance.MissingRunIdentity):
            advance.advance_main(
                "pl-regression-guard-7",
                bridge_path,
                key_file=key_file,
                run_root=run_root,
            )


# ---------------------------------------------------------------------------
# Stress-test #7 -- no-MAC / plain-file invariant (D5).
# ---------------------------------------------------------------------------


class TestNoMacPlainFileInvariant:
    def test_written_sidecar_keys_are_exactly_pipeline_id_and_head_sha(
        self, repo: str, patched_repo_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The written JSON object has EXACTLY the keys {"pipeline_id",
        "head_sha"} and no signature/digest/MAC field -- guards against a
        future regression re-adding a second integrity scheme."""
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-nomac-8")

        (Path(repo) / "nomac.txt").write_text("v1\n")
        mcp_server.commit_changes(message="nomac commit", repo_dir=repo)

        sidecar = _sidecar_path(patched_repo_root)
        written = json.loads(sidecar.read_text(encoding="utf-8"))
        assert set(written.keys()) == {"pipeline_id", "head_sha"}


# ---------------------------------------------------------------------------
# Stress-test #8 -- bridge/marker untouched + broker surface preserved
# (blast-radius).
# ---------------------------------------------------------------------------


class TestBridgeMarkerUntouchedAndBrokerSurfacePreserved:
    """The full existing broker test files (`test_broker_tool_surface.py`,
    `test_broker_stdlib_only.py`) are the actual, already-passing guard for
    the no-argv/no-new-tool half of this assertion; this class adds a
    static, source-level check specific to the D5 write side's blast
    radius, run from THIS file so it is part of the D5 slice's own arbiter."""

    def test_module_source_has_no_bridge_or_statemarker_reference(self) -> None:
        source = inspect.getsource(mcp_server)
        assert "bridge" not in source.lower()
        assert "StateMarker" not in source

    def test_commit_changes_signature_and_contract_preserved(self) -> None:
        """Additive-only (Design Intent (a)): `commit_changes`'s public
        signature gains no new parameter -- in particular no `pipeline_id`
        and no `run_root` on the agent-facing MCP tool schema.

        `eval_str=True` (Python 3.10+) is required here because `mcp_server.py`
        has `from __future__ import annotations` (PEP 563): every annotation in
        that module, including this return annotation, is stored as an
        un-evaluated string. Without `eval_str=True`,
        `sig.return_annotation` would be the string `'str'`, never the live
        `str` type object, and `is str` would always be False regardless of
        the module's actual contract -- a test-authoring gap, not a defect in
        `commit_changes` itself. Resolving it via `eval_str=True` genuinely
        evaluates the stringized annotation back to the live type, which is a
        STRONGER check than a raw string comparison (`== "str"`) would be: it
        actually confirms the name `str` resolves, in this module's
        namespace, to the builtin type -- not merely that the source text
        happens to read "str"."""
        sig = inspect.signature(mcp_server.commit_changes, eval_str=True)
        params = list(sig.parameters.keys())
        assert params == ["message", "files", "repo_dir"]
        assert sig.parameters["message"].default is inspect.Parameter.empty
        assert sig.parameters["files"].default == ""
        assert sig.parameters["repo_dir"].default == ""
        assert sig.return_annotation is str


# ---------------------------------------------------------------------------
# T1 direct coverage -- the write helper's own injectable `run_root=` seam
# (Option (b)), exercised in isolation (not through `commit_changes`, and
# not via the `patched_repo_root` monkeypatch).
# ---------------------------------------------------------------------------


class TestWriteHelperDirectRunRootInjection:
    def test_helper_writes_to_the_injected_run_root_when_armed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_env(monkeypatch)
        monkeypatch.setenv(_PIPELINE_ID_ENV_NAME, "pl-direct-helper-9")
        run_root = tmp_path / "direct-run-root"

        mcp_server._write_run_manifest_head_sha("deadbeefcafe", run_root=run_root)

        written = json.loads(
            (run_root / "pipeline-run.json").read_text(encoding="utf-8")
        )
        assert written == {
            "pipeline_id": "pl-direct-helper-9",
            "head_sha": "deadbeefcafe",
        }

    def test_helper_is_a_no_op_when_unarmed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_env(monkeypatch)
        run_root = tmp_path / "direct-run-root-unarmed"

        mcp_server._write_run_manifest_head_sha("deadbeefcafe", run_root=run_root)

        assert not (run_root / "pipeline-run.json").exists()
