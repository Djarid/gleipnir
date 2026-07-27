"""Real-OS-permission probe tests for the S-2/G-1 boundary preflight.

Spec: `.gleipnir/plans/s2-g1-closure-first-slice.md`, Assemble step 1 / B2
test-location strategy. These tests use REAL `chmod` and REAL attempted
write/read against real files, which is the only way to genuinely exercise
"denied -> CLOSED" against actual OS permission enforcement.

**Why these are `@pytest.mark.hostonly` and self-skip under root:** the S-2
sandbox container runs `test`/`lint` as root (no `USER` in the Containerfile,
no `--user` in `build_run_argv`), and root bypasses permission bits — a
`chmod 0o444` file is still writable to root. Under root, a "denied" test and
a "writable" test would be observationally identical, which is exactly the
trap `tests/test_bus_emit.py` (~line 109-111) already documents and avoids
via a non-chmod construction. We do NOT claim a chmod-based denied test
passes under root; instead we skip cleanly there and rely on
`tests/test_preflight_decision.py`'s mocked-edge decision tests for
in-sandbox coverage of the same decision logic.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gleipnir.preflight import boundary as pb

hostonly = pytest.mark.hostonly

_RUNNING_AS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0

pytestmark = pytest.mark.skipif(
    _RUNNING_AS_ROOT,
    reason=(
        "hostonly: root bypasses permission bits (chmod-based denied/writable "
        "tests would be observationally identical); genuinely meaningful only "
        "off-root, per plan B2"
    ),
)


# ---------------------------------------------------------------------------
# Real denied case: chmod 0o444 (ro) dir/file + key chmod 0o000 -> real
# probe reports WRITE_DENIED / CLOSED.
# ---------------------------------------------------------------------------

@hostonly
class TestRealDeniedCase:
    def test_real_ro_directory_write_probe_is_denied(self, tmp_path: Path):
        ro_dir = tmp_path / "agents"
        ro_dir.mkdir()
        (ro_dir / "orchestrator.md").write_text("---\n")
        ro_dir.chmod(0o555)  # r-xr-xr-x: no write bit for anyone, including owner
        try:
            result = pb.probe_write_as_agent(ro_dir, os.getuid(), os.getgid())
            assert result.outcome is pb.ProbeOutcome.WRITE_DENIED
            assert pb.classify_probe_result(False, False, False, pb.Posture.RO) is pb.ProbeVerdict.CLOSED
        finally:
            ro_dir.chmod(0o755)

    def test_real_ro_file_write_probe_is_denied(self, tmp_path: Path):
        ro_file = tmp_path / "AGENTS.md"
        ro_file.write_text("# agents\n")
        ro_file.chmod(0o444)
        try:
            result = pb.probe_write_as_agent(ro_file, os.getuid(), os.getgid())
            assert result.outcome is pb.ProbeOutcome.WRITE_DENIED
        finally:
            ro_file.chmod(0o644)

    def test_real_unreadable_key_read_probe_is_denied(self, tmp_path: Path):
        key = tmp_path / "hmac.key"
        key.write_bytes(b"super-secret")
        key.chmod(0o000)
        try:
            result = pb.probe_read_key_as_agent(key, os.getuid(), os.getgid())
            assert result.outcome is pb.ProbeOutcome.WRITE_DENIED
        finally:
            key.chmod(0o600)

    def test_full_decide_reports_closed_with_key_env_var_set(self, tmp_path: Path, monkeypatch):
        root = tmp_path / ".gleipnir"
        (root / "agents").mkdir(parents=True)
        (root / "agents" / "orchestrator.md").write_text("---\n")
        (root / "decisions").mkdir()
        (root / "decisions" / "d1.md").write_text("# d\n")
        (root / "goals").mkdir()
        (root / "goals" / "manifest.md").write_text("# g\n")
        (root / "keys").mkdir()
        key = root / "keys" / "hmac.key"
        key.write_bytes(b"super-secret")
        (root / "plugins").mkdir()
        (root / "plugins" / "sequence-gate.ts").write_text("// gate\n")
        (root / "stage-role-map.md").write_text("# map\n")
        (root / "AGENTS.md").write_text("# agents\n")

        made_ro = []
        try:
            key.chmod(0o000)
            made_ro.append(key)
            for d in ("agents", "decisions", "goals", "keys", "plugins"):
                p = root / d
                p.chmod(0o555)
                made_ro.append(p)
            for f in ("stage-role-map.md", "AGENTS.md"):
                p = root / f
                p.chmod(0o444)
                made_ro.append(p)

            monkeypatch.setenv(pb.KEY_ENV_VAR, str(key))
            decision = pb.run_preflight(root, agent_uid=os.getuid(), agent_gid=os.getgid())
            assert decision.verdict is pb.Verdict.CLOSED, decision.reasons
        finally:
            for p in reversed(made_ro):
                try:
                    p.chmod(0o755 if p.is_dir() else 0o644)
                except FileNotFoundError:
                    pass


# ---------------------------------------------------------------------------
# BLOCKER-1 real-perms proof: `chmod 0o555` on a DIRECTORY alone, leaving a
# pre-existing FILE inside it writable, must NOT report CLOSED. This is the
# exact false-CLOSED the per-file walk exists to close: POSIX requires write
# permission on the FILE itself (not its parent directory) to overwrite
# existing content, so the directory-node probe alone (create+unlink a temp
# entry) would otherwise miss this entirely.
# ---------------------------------------------------------------------------

@hostonly
class TestRealWritableFileInsideRoDirectory:
    def test_ro_directory_containing_writable_file_is_not_closed(self, tmp_path: Path):
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "orchestrator.md"
        md.write_text("---\nname: orchestrator\n---\n")
        md.chmod(0o644)  # the FILE stays writable
        agents.chmod(0o555)  # the DIRECTORY node alone is read-only
        try:
            dir_result = pb.probe_write_as_agent(agents, os.getuid(), os.getgid())
            # The directory node's OWN probe correctly reports denied --
            # this is the exact "would-be false CLOSED" signal a
            # directory-only probe would have stopped at.
            assert dir_result.outcome is pb.ProbeOutcome.WRITE_DENIED

            file_probes = pb._collect_file_probes(
                agents, os.getuid(), os.getgid(), pb.probe_write_as_agent
            )
            assert len(file_probes) == 1
            assert file_probes[0].relpath == "orchestrator.md"
            assert file_probes[0].write_result.outcome is pb.ProbeOutcome.WRITE_OK

            probe = pb.PathProbe(
                "agents/*.md",
                pb.Posture.RO,
                dir_result,
                file_probes=tuple(file_probes),
            )
            verdict, reason = pb.verdict_for_path(probe)
            assert verdict is pb.ProbeVerdict.NOT_CLOSED
            assert "orchestrator.md" in reason
        finally:
            agents.chmod(0o755)
            md.chmod(0o644)

    def test_full_run_preflight_refuses_when_one_file_inside_ro_directory_is_writable(
        self, tmp_path: Path, monkeypatch
    ):
        """The full end-to-end proof (plan REPORT BACK requirement): a
        realistic `.gleipnir`-shaped tree, everything chmod'd read-only
        exactly like `test_full_decide_reports_closed_with_key_env_var_set`
        above -- EXCEPT `agents/orchestrator.md` (the permission map G-1
        protects) is deliberately left writable, simulating
        `chmod 0o555 agents/` without touching the file inside. This MUST
        refuse, never CLOSED."""

        root = tmp_path / ".gleipnir"
        (root / "agents").mkdir(parents=True)
        orchestrator = root / "agents" / "orchestrator.md"
        orchestrator.write_text("---\n")
        (root / "decisions").mkdir()
        (root / "decisions" / "d1.md").write_text("# d\n")
        (root / "goals").mkdir()
        (root / "goals" / "manifest.md").write_text("# g\n")
        (root / "keys").mkdir()
        key = root / "keys" / "hmac.key"
        key.write_bytes(b"super-secret")
        (root / "plugins").mkdir()
        (root / "plugins" / "sequence-gate.ts").write_text("// gate\n")
        (root / "stage-role-map.md").write_text("# map\n")
        (root / "AGENTS.md").write_text("# agents\n")

        made_ro = []
        try:
            key.chmod(0o000)
            made_ro.append(key)
            for d in ("agents", "decisions", "goals", "keys", "plugins"):
                p = root / d
                p.chmod(0o555)
                made_ro.append(p)
            for f in ("stage-role-map.md", "AGENTS.md"):
                p = root / f
                p.chmod(0o444)
                made_ro.append(p)
            # The cardinal false-CLOSED under test: the DIRECTORY is ro,
            # but this pre-existing FILE inside it is left writable.
            orchestrator.chmod(0o644)

            monkeypatch.setenv(pb.KEY_ENV_VAR, str(key))
            decision = pb.run_preflight(root, agent_uid=os.getuid(), agent_gid=os.getgid())
            assert decision.verdict is pb.Verdict.REFUSE, decision.reasons
            assert decision.verdict is not pb.Verdict.CLOSED
            assert any("orchestrator.md" in r for r in decision.reasons)
        finally:
            for p in reversed(made_ro):
                try:
                    p.chmod(0o755 if p.is_dir() else 0o644)
                except FileNotFoundError:
                    pass
            try:
                orchestrator.chmod(0o644)
            except FileNotFoundError:
                pass


# ---------------------------------------------------------------------------
# Real writable case: chmod 0o644/0o755 -> real write succeeds -> NOT_CLOSED.
# ---------------------------------------------------------------------------

@hostonly
class TestRealWritableCase:
    def test_real_writable_directory_write_probe_succeeds(self, tmp_path: Path):
        writable_dir = tmp_path / "plugins"
        writable_dir.mkdir()
        writable_dir.chmod(0o755)
        result = pb.probe_write_as_agent(writable_dir, os.getuid(), os.getgid())
        assert result.outcome is pb.ProbeOutcome.WRITE_OK

    def test_real_writable_file_write_probe_succeeds(self, tmp_path: Path):
        writable_file = tmp_path / "stage-role-map.md"
        writable_file.write_text("# map\n")
        writable_file.chmod(0o644)
        result = pb.probe_write_as_agent(writable_file, os.getuid(), os.getgid())
        assert result.outcome is pb.ProbeOutcome.WRITE_OK


# ---------------------------------------------------------------------------
# Real key-readable case: chmod 0o444 -> real read succeeds -> NOT_CLOSED.
# ---------------------------------------------------------------------------

@hostonly
class TestRealKeyReadableCase:
    def test_real_readable_key_probe_succeeds(self, tmp_path: Path):
        key = tmp_path / "hmac.key"
        key.write_bytes(b"super-secret")
        key.chmod(0o444)
        result = pb.probe_read_key_as_agent(key, os.getuid(), os.getgid())
        assert result.outcome is pb.ProbeOutcome.WRITE_OK


# ---------------------------------------------------------------------------
# Real symlink case: an enforcement path is a real symlink into a real
# writable location -> real resolution detects the escape.
# ---------------------------------------------------------------------------

@hostonly
class TestRealSymlinkEscape:
    def test_symlink_from_ro_enforcement_path_into_writable_dir_is_detected(
        self, tmp_path: Path
    ):
        root = tmp_path / ".gleipnir"
        root.mkdir()
        writable_elsewhere = tmp_path / "writable_elsewhere"
        writable_elsewhere.mkdir()
        escape_target = writable_elsewhere / "AGENTS.md"
        escape_target.write_text("# tampered\n")

        link = root / "AGENTS.md"
        link.symlink_to(escape_target)

        assert pb.target_escapes_subtree(link, root) is True
        # And even though the escape target is genuinely writable, the
        # decision logic must refuse on the escape alone.
        verdict, _ = pb.verdict_for_path(
            pb.PathProbe(
                "AGENTS.md",
                pb.Posture.RO,
                pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),  # even if "denied"
                escapes_subtree=True,
            )
        )
        assert verdict is pb.ProbeVerdict.NOT_CLOSED


# ---------------------------------------------------------------------------
# Real second-uid drop case: self-skips when no second uid is available to
# drop to (the common case in CI/dev). Documents the intended real-drop path
# per plan Trace / B1 without requiring privileged test infrastructure.
# ---------------------------------------------------------------------------

_SECOND_UID_ENV = "GLEIPNIR_TEST_SECOND_UID"
_SECOND_GID_ENV = "GLEIPNIR_TEST_SECOND_GID"


@hostonly
@pytest.mark.skipif(
    _SECOND_UID_ENV not in os.environ,
    reason=(
        f"no second OS uid available for a real privilege-drop test; set "
        f"{_SECOND_UID_ENV}/{_SECOND_GID_ENV} to exercise this for real"
    ),
)
class TestRealSecondUidDrop:
    def test_real_drop_to_second_uid_then_denied_write(self, tmp_path: Path):
        agent_uid = int(os.environ[_SECOND_UID_ENV])
        agent_gid = int(os.environ.get(_SECOND_GID_ENV, agent_uid))
        ro_dir = tmp_path / "agents"
        ro_dir.mkdir()
        ro_dir.chmod(0o555)
        result = pb.probe_write_as_agent(ro_dir, agent_uid, agent_gid)
        assert result.outcome is pb.ProbeOutcome.WRITE_DENIED
