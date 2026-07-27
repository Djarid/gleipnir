"""Decision-logic tests for the S-2/G-1 boundary preflight
(`src/gleipnir/preflight/boundary.py`).

Spec: `.gleipnir/plans/s2-g1-closure-first-slice.md`, Assemble step 1 /
Stress-test. Per the plan's B2 test-location strategy, THIS file runs
IN-SANDBOX (under root) — every test here either exercises the PURE decision
logic with the probe edge MOCKED/INJECTED (no reliance on real OS
permissions), or exercises the real fork/pipe thin-edge mechanism with an
INJECTED `attempt` callable (so the outcome is deterministic regardless of
uid/perms — no chmod is relied upon anywhere in this file). The genuinely
permission-dependent "denied -> CLOSED" behaviour is exercised for real in
`tests/test_preflight_probe_hostonly.py` (skipped here under root).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gleipnir.preflight import boundary as pb


# ---------------------------------------------------------------------------
# Fixtures: a fake `.gleipnir`-shaped config root, no real OS perms involved.
# ---------------------------------------------------------------------------

@pytest.fixture
def config_root(tmp_path: Path) -> Path:
    root = tmp_path / ".gleipnir"
    (root / "agents").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("---\nname: orchestrator\n---\n")
    (root / "decisions").mkdir()
    (root / "decisions" / "d1.md").write_text("# decision\n")
    (root / "goals").mkdir()
    (root / "goals" / "manifest.md").write_text("# goals\n")
    (root / "keys").mkdir()
    (root / "keys" / "hmac.key").write_bytes(b"super-secret-key-bytes")
    (root / "plugins").mkdir()
    (root / "plugins" / "sequence-gate.ts").write_text("// gate\n")
    (root / "stage-role-map.md").write_text("# map\n")
    (root / "AGENTS.md").write_text("# agents\n")
    return root


def _key_path(config_root: Path) -> Path:
    return config_root / "keys" / "hmac.key"


def _all_denied_write_probe(target: Path, agent_uid: int, agent_gid: int) -> pb.ProbeResult:
    return pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED, detail="EACCES (fake)")


def _all_denied_read_probe(target: Path, agent_uid: int, agent_gid: int) -> pb.ProbeResult:
    return pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED, detail="EACCES (fake)")


# ---------------------------------------------------------------------------
# decide(): the pure aggregation, fed hand-built PathProbe evidence.
# ---------------------------------------------------------------------------

def _closed_probe(label: str, posture: pb.Posture = pb.Posture.RO) -> pb.PathProbe:
    read_result = None
    if posture is pb.Posture.RO_AND_UNREADABLE:
        read_result = pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED)
    return pb.PathProbe(
        label,
        posture,
        pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
        escapes_subtree=False,
        read_result=read_result,
    )


class TestDecideAllClosed:
    def test_all_closed_and_key_present_yields_closed(self):
        probes = [
            _closed_probe("agents/*.md"),
            _closed_probe("keys/**", pb.Posture.RO_AND_UNREADABLE),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.CLOSED
        assert decision.reasons == ()

    def test_closed_verdict_label_is_honest_about_the_floor(self):
        decision = pb.decide([_closed_probe("agents/*.md")], pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.CLOSED
        assert "OS-perms floor" in decision.label


class TestDecideWritableCaseRefuses:
    def test_one_writable_path_forces_refuse(self):
        probes = [
            _closed_probe("agents/*.md"),
            pb.PathProbe(
                "AGENTS.md",
                pb.Posture.RO,
                pb.ProbeResult(pb.ProbeOutcome.WRITE_OK),
            ),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("AGENTS.md" in r for r in decision.reasons)

    def test_never_closed_when_any_path_is_writable(self):
        """Direct proof of the security invariant: NO combination of other
        evidence can produce CLOSED if one path's write-probe succeeded."""
        probes = [
            _closed_probe("agents/*.md"),
            _closed_probe("decisions/**"),
            pb.PathProbe("plugins/**", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.WRITE_OK)),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is not pb.Verdict.CLOSED


class TestDecideKeyReadableCaseRefuses:
    def test_key_readable_forces_refuse(self):
        probes = [
            _closed_probe("agents/*.md"),
            pb.PathProbe(
                "keys/**",
                pb.Posture.RO_AND_UNREADABLE,
                pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),  # dir unwritable: fine
                read_result=pb.ProbeResult(pb.ProbeOutcome.WRITE_OK),  # but key IS readable
            ),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("keys/**" in r for r in decision.reasons)


class TestDecideProbeErrorIsFailClosed:
    def test_probe_error_forces_refuse_never_closed(self):
        probes = [
            pb.PathProbe("agents/*.md", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.PROBE_ERROR, "boom")),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE

    def test_empty_path_probes_is_ambiguous_and_refuses(self):
        """No evidence is not evidence of closure."""
        decision = pb.decide([], pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE


class TestB1DropFailedAndUnverifiedNeverCloseAndAlwaysRefuse:
    """The explicit B1 stress-test (plan Stress-test #9): a privilege drop
    that failed, or that could not be verified via the euid/uid read-back,
    must REFUSE and must NEVER be reported as CLOSED — never folded into the
    write-permission signal."""

    def test_drop_failed_forces_refuse_never_closed(self):
        probes = [
            pb.PathProbe(
                "agents/*.md",
                pb.Posture.RO,
                pb.ProbeResult(pb.ProbeOutcome.DROP_FAILED, "setuid: Operation not permitted"),
            ),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is not pb.Verdict.CLOSED
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("drop_failed" in r for r in decision.reasons)

    def test_drop_unverified_forces_refuse_never_closed(self):
        probes = [
            pb.PathProbe(
                "keys/**",
                pb.Posture.RO_AND_UNREADABLE,
                pb.ProbeResult(pb.ProbeOutcome.DROP_UNVERIFIED, "euid=0 uid=0 != agent_uid=501"),
                read_result=pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
            ),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is not pb.Verdict.CLOSED
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("drop_unverified" in r for r in decision.reasons)

    def test_drop_unverified_on_the_read_probe_also_refuses(self):
        probes = [
            pb.PathProbe(
                "keys/**",
                pb.Posture.RO_AND_UNREADABLE,
                pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),  # write side is fine
                read_result=pb.ProbeResult(pb.ProbeOutcome.DROP_UNVERIFIED, "readback mismatch"),
            ),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE

    def test_classify_probe_result_has_no_path_to_closed_via_drop_outcomes(self):
        """`classify_probe_result` itself only ever sees plain booleans (never
        the raw DROP_* outcomes) -- `verdict_for_path` intercepts B1 error
        outcomes before they could reach it. Prove the interception."""
        probe = pb.PathProbe(
            "agents/*.md", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.DROP_FAILED)
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert "write probe drop_failed" in reason


class TestOverrideCanEscalateButNeverReachesClosed:
    def test_override_escalates_not_closed_to_proceed_unclosed_with_honest_label(self):
        probes = [
            pb.PathProbe("AGENTS.md", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.WRITE_OK)),
        ]
        decision = pb.decide(probes, pb.KeyState.PRESENT, override_ack=True)
        assert decision.verdict is pb.Verdict.PROCEED_UNCLOSED
        assert decision.label == pb.DEV_MODE_LABEL
        assert decision.label == "G-1 NOT closed (dev-mode)"

    def test_override_present_but_everything_closed_still_reports_closed_not_dev_mode(self):
        probes = [_closed_probe("agents/*.md")]
        decision = pb.decide(probes, pb.KeyState.PRESENT, override_ack=True)
        assert decision.verdict is pb.Verdict.CLOSED

    def test_override_can_never_produce_closed_from_a_not_closed_input(self):
        """The core invariant: for EVERY not-closed input this module can
        construct, override_ack=True never yields Verdict.CLOSED."""
        not_closed_probe_sets = [
            [pb.PathProbe("a", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.WRITE_OK))],
            [pb.PathProbe("a", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.DROP_FAILED))],
            [pb.PathProbe("a", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.DROP_UNVERIFIED))],
            [pb.PathProbe("a", pb.Posture.RO, pb.ProbeResult(pb.ProbeOutcome.PROBE_ERROR))],
        ]
        for probes in not_closed_probe_sets:
            decision = pb.decide(probes, pb.KeyState.PRESENT, override_ack=True)
            assert decision.verdict is not pb.Verdict.CLOSED
            decision_no_override = pb.decide(probes, pb.KeyState.PRESENT, override_ack=False)
            assert decision_no_override.verdict is pb.Verdict.REFUSE

        for key_state in (pb.KeyState.ABSENT, pb.KeyState.EMPTY):
            decision = pb.decide([_closed_probe("agents/*.md")], key_state, override_ack=True)
            assert decision.verdict is not pb.Verdict.CLOSED


class TestKeyAbsentVsEmpty:
    def test_key_absent_refuses(self):
        decision = pb.decide([_closed_probe("agents/*.md")], pb.KeyState.ABSENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("absent" in r for r in decision.reasons)

    def test_key_empty_refuses(self):
        decision = pb.decide([_closed_probe("agents/*.md")], pb.KeyState.EMPTY)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("empty" in r for r in decision.reasons)

    def test_key_absent_and_key_empty_are_distinct_reasons(self):
        absent = pb.decide([_closed_probe("agents/*.md")], pb.KeyState.ABSENT)
        empty = pb.decide([_closed_probe("agents/*.md")], pb.KeyState.EMPTY)
        assert absent.reasons != empty.reasons

    def test_check_key_state_absent_when_no_path(self):
        assert pb.check_key_state(None) is pb.KeyState.ABSENT

    def test_check_key_state_absent_when_file_does_not_exist(self, tmp_path: Path):
        assert pb.check_key_state(tmp_path / "no-such-key") is pb.KeyState.ABSENT

    def test_check_key_state_empty_for_zero_byte_key(self, tmp_path: Path):
        kf = tmp_path / "key"
        kf.write_bytes(b"   \n")
        assert pb.check_key_state(kf) is pb.KeyState.EMPTY

    def test_check_key_state_present_for_real_key(self, tmp_path: Path):
        kf = tmp_path / "key"
        kf.write_bytes(b"real-secret")
        assert pb.check_key_state(kf) is pb.KeyState.PRESENT

    def test_check_key_state_unreadable_owner_side_is_treated_as_absent(self, tmp_path: Path):
        """A key path that exists as a directory (unreadable as bytes from
        the owner's own perspective) -> OSError -> ABSENT-class, fail-closed."""
        d = tmp_path / "not-a-key-file"
        d.mkdir()
        assert pb.check_key_state(d) is pb.KeyState.ABSENT


# ---------------------------------------------------------------------------
# Symlink-resolution logic — pure, no real perms needed (symlink creation
# works the same under root as anywhere else).
# ---------------------------------------------------------------------------

class TestSymlinkResolution:
    def test_resolve_final_target_follows_a_symlink(self, tmp_path: Path):
        real = tmp_path / "real.txt"
        real.write_text("x")
        link = tmp_path / "link.txt"
        link.symlink_to(real)
        assert pb.resolve_final_target(link) == real.resolve()

    def test_target_escapes_subtree_false_when_inside(self, tmp_path: Path):
        root = tmp_path / "root"
        root.mkdir()
        f = root / "f.txt"
        f.write_text("x")
        assert pb.target_escapes_subtree(f, root) is False

    def test_target_escapes_subtree_true_for_symlink_pointing_outside(self, tmp_path: Path):
        root = tmp_path / "root"
        root.mkdir()
        outside_writable = tmp_path / "outside_writable"
        outside_writable.mkdir()
        escape_target = outside_writable / "escape.txt"
        escape_target.write_text("x")
        link = root / "enforcement-file.md"
        link.symlink_to(escape_target)
        assert pb.target_escapes_subtree(link, root) is True

    def test_target_escapes_subtree_true_on_unresolvable_symlink_loop(self, tmp_path: Path):
        root = tmp_path / "root"
        root.mkdir()
        a = root / "a"
        b = root / "b"
        a.symlink_to(b)
        b.symlink_to(a)
        assert pb.target_escapes_subtree(a, root) is True

    def test_path_probe_with_escape_never_reaches_closed(self):
        probe = pb.PathProbe(
            "agents/*.md",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
            escapes_subtree=True,
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert "agents/*.md" in reason


# ---------------------------------------------------------------------------
# classify_probe_result: the pure boolean-combination mapping.
# ---------------------------------------------------------------------------

class TestClassifyProbeResult:
    def test_denied_not_escaping_ro_posture_is_closed(self):
        assert (
            pb.classify_probe_result(False, False, False, pb.Posture.RO)
            is pb.ProbeVerdict.CLOSED
        )

    def test_writable_is_not_closed(self):
        assert (
            pb.classify_probe_result(True, False, False, pb.Posture.RO)
            is pb.ProbeVerdict.NOT_CLOSED
        )

    def test_escaping_is_not_closed_even_if_denied(self):
        assert (
            pb.classify_probe_result(False, False, True, pb.Posture.RO)
            is pb.ProbeVerdict.NOT_CLOSED
        )

    def test_key_posture_readable_is_not_closed_even_if_unwritable(self):
        assert (
            pb.classify_probe_result(False, True, False, pb.Posture.RO_AND_UNREADABLE)
            is pb.ProbeVerdict.NOT_CLOSED
        )

    def test_key_posture_unreadable_and_unwritable_is_closed(self):
        assert (
            pb.classify_probe_result(False, False, False, pb.Posture.RO_AND_UNREADABLE)
            is pb.ProbeVerdict.CLOSED
        )

    def test_ro_posture_ignores_read_ok(self):
        """A plain RO path's readability is irrelevant to its own verdict —
        only RO_AND_UNREADABLE paths care about read_ok."""
        assert (
            pb.classify_probe_result(False, True, False, pb.Posture.RO)
            is pb.ProbeVerdict.CLOSED
        )


# ---------------------------------------------------------------------------
# outcome_forces_refuse / outcome_is_op_ok: the B1 outcome->boolean mapping.
# ---------------------------------------------------------------------------

class TestOutcomeMapping:
    @pytest.mark.parametrize(
        "outcome",
        [pb.ProbeOutcome.DROP_FAILED, pb.ProbeOutcome.DROP_UNVERIFIED, pb.ProbeOutcome.PROBE_ERROR],
    )
    def test_error_outcomes_force_refuse(self, outcome):
        assert pb.outcome_forces_refuse(outcome) is True

    @pytest.mark.parametrize("outcome", [pb.ProbeOutcome.WRITE_DENIED, pb.ProbeOutcome.WRITE_OK])
    def test_write_outcomes_do_not_force_refuse(self, outcome):
        assert pb.outcome_forces_refuse(outcome) is False

    def test_only_write_ok_is_op_ok(self):
        assert pb.outcome_is_op_ok(pb.ProbeOutcome.WRITE_OK) is True
        assert pb.outcome_is_op_ok(pb.ProbeOutcome.WRITE_DENIED) is False


# ---------------------------------------------------------------------------
# collect_path_probes: ties ENFORCEMENT_PATHS to an injected fake edge (no
# real perms). Covers the plugins present/absent edge case and confirms the
# canonical enforcement set is used, not inferred by globbing.
# ---------------------------------------------------------------------------

class TestCollectPathProbes:
    def test_all_denied_and_key_unreadable_collects_to_closed(self, config_root: Path):
        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.CLOSED

    def test_plugins_present_and_writable_refuses(self, config_root: Path):
        def write_probe(target: Path, agent_uid: int, agent_gid: int) -> pb.ProbeResult:
            if target.name == "plugins":
                return pb.ProbeResult(pb.ProbeOutcome.WRITE_OK)
            return pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED)

        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("plugins/**" in r for r in decision.reasons)

    def test_plugins_absent_dir_is_tolerated_not_a_failure(self, config_root: Path):
        import shutil

        shutil.rmtree(config_root / "plugins")
        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        labels = [p.label for p in probes]
        assert "plugins/**" not in labels
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.CLOSED

    def test_missing_non_tolerated_path_refuses(self, config_root: Path):
        (config_root / "AGENTS.md").unlink()
        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("missing" in r for r in decision.reasons)

    def test_key_path_absent_at_collect_time_is_probe_error_on_keys_path(self, config_root: Path):
        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=config_root / "keys" / "no-such-key",
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.ABSENT)
        assert decision.verdict is pb.Verdict.REFUSE


# ---------------------------------------------------------------------------
# run_preflight: the real top-level glue, exercised with injected edges (no
# real perms/fork needed) plus the real KEY_ENV_VAR lookup.
# ---------------------------------------------------------------------------

class TestWalkEnforcementFiles:
    """Pure recursive file-enumeration helper (BLOCKER-1 + the two
    walk-completeness residuals) -- no real perms needed, symlink/directory
    creation behaves the same under root."""

    def test_walks_nested_files_recursively(self, tmp_path: Path):
        root = tmp_path / "decisions"
        root.mkdir()
        (root / "a.md").write_text("a")
        sub = root / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("b")
        result = pb._walk_enforcement_files(root)
        relnames = {str(f.relative_to(root)) for f in result.files}
        assert relnames == {"a.md", str(Path("sub") / "b.md")}
        assert result.symlinked_dirs == []
        assert result.errors == []

    def test_empty_directory_walks_to_no_files(self, tmp_path: Path):
        root = tmp_path / "plugins"
        root.mkdir()
        result = pb._walk_enforcement_files(root)
        assert result.files == []
        assert result.symlinked_dirs == []
        assert result.errors == []

    def test_does_not_descend_into_a_symlinked_subdirectory(self, tmp_path: Path):
        root = tmp_path / "agents"
        root.mkdir()
        real_sub = tmp_path / "real_sub"
        real_sub.mkdir()
        (real_sub / "escaped.md").write_text("x")
        link = root / "linked_sub"
        link.symlink_to(real_sub)
        result = pb._walk_enforcement_files(root)
        # followlinks=False: the symlinked directory is not descended into,
        # so the file inside it is never walked as a FILE.
        assert result.files == []
        # FINDING 1 (residual false-CLOSED, directory-symlink variant): the
        # symlinked subdir itself IS still collected -- never silently
        # dropped -- so the caller can escape-check it even though it is
        # never descended into.
        assert result.symlinked_dirs == [link]
        assert result.errors == []

    def test_symlinked_subdir_pointing_inside_the_subtree_is_still_collected(
        self, tmp_path: Path
    ):
        """A symlinked subdir whose resolved target stays INSIDE the ro
        subtree is collected the same way -- it is up to the caller's
        escape-check (not this helper) to decide it is fine."""
        root = tmp_path / "agents"
        root.mkdir()
        inside_sub = root / "inside_sub"
        inside_sub.mkdir()
        (inside_sub / "real.md").write_text("x")
        link = root / "linked_sub"
        link.symlink_to(inside_sub)
        result = pb._walk_enforcement_files(root)
        relnames = {str(f.relative_to(root)) for f in result.files}
        assert relnames == {str(Path("inside_sub") / "real.md")}
        assert result.symlinked_dirs == [link]

    def test_onerror_records_scan_failure_instead_of_swallowing_it(
        self, tmp_path: Path, monkeypatch
    ):
        """FINDING 2: the default `onerror=None` would silently omit files
        under a branch where `scandir` fails. An explicit `onerror` hook
        must record the failure instead."""
        root = tmp_path / "decisions"
        root.mkdir()
        (root / "a.md").write_text("a")
        bad_dir = root / "bad"
        bad_dir.mkdir()

        real_scandir = os.scandir

        def failing_scandir(path="."):
            if Path(path) == bad_dir:
                raise OSError("scandir failed (injected)")
            return real_scandir(path)

        monkeypatch.setattr(pb.os, "scandir", failing_scandir)
        result = pb._walk_enforcement_files(root)
        assert len(result.errors) == 1
        assert "scandir failed" in result.errors[0]
        # The rest of the tree is still walked -- only the failing branch
        # is affected, and it is now surfaced rather than silently dropped.
        relnames = {str(f.relative_to(root)) for f in result.files}
        assert "a.md" in relnames


class TestCollectFileProbes:
    """`_collect_file_probes` ties `_walk_enforcement_files` to the
    injectable write-probe edge + the per-file escape check."""

    def test_calls_write_probe_once_per_file_with_correct_paths(self, tmp_path: Path):
        root = tmp_path / "decisions"
        root.mkdir()
        (root / "d1.md").write_text("x")
        (root / "d2.md").write_text("y")
        seen: list[Path] = []

        def write_probe(target: Path, agent_uid: int, agent_gid: int) -> pb.ProbeResult:
            seen.append(target)
            return pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED)

        file_probes = pb._collect_file_probes(root, 999, 999, write_probe)
        assert {p.name for p in seen} == {"d1.md", "d2.md"}
        assert {fp.relpath for fp in file_probes} == {"d1.md", "d2.md"}
        assert all(fp.write_result.outcome is pb.ProbeOutcome.WRITE_DENIED for fp in file_probes)
        assert all(fp.escapes_subtree is False for fp in file_probes)

    def test_flags_a_per_file_symlink_that_escapes_the_entry_subtree(self, tmp_path: Path):
        root = tmp_path / "agents"
        root.mkdir()
        outside = tmp_path / "outside_writable"
        outside.mkdir()
        escape_target = outside / "evil.md"
        escape_target.write_text("tampered")
        (root / "orchestrator.md").symlink_to(escape_target)

        file_probes = pb._collect_file_probes(root, 999, 999, _all_denied_write_probe)
        assert len(file_probes) == 1
        assert file_probes[0].relpath == "orchestrator.md"
        assert file_probes[0].escapes_subtree is True

    def test_flags_a_symlinked_subdir_that_escapes_the_entry_subtree(self, tmp_path: Path):
        """FINDING 1: a symlinked SUBDIR (not a file) inside a directory
        entry, whose resolved target escapes the ro subtree, must surface
        as an escaping FileProbe even though it is never write-probed
        (never descended into)."""
        root = tmp_path / "agents"
        root.mkdir()
        outside = tmp_path / "writable_elsewhere"
        outside.mkdir()
        link = root / "link"
        link.symlink_to(outside)

        file_probes = pb._collect_file_probes(root, 999, 999, _all_denied_write_probe)
        assert len(file_probes) == 1
        assert file_probes[0].relpath == "link"
        assert file_probes[0].escapes_subtree is True

    def test_does_not_flag_a_symlinked_subdir_that_stays_inside_the_subtree(
        self, tmp_path: Path
    ):
        """A symlinked subdir whose resolved target stays INSIDE the ro
        subtree must not be flagged as escaping -- its real files are
        walked via their actual path elsewhere in the tree."""
        root = tmp_path / "agents"
        root.mkdir()
        inside = root / "inside_sub"
        inside.mkdir()
        (inside / "real.md").write_text("x")
        link = root / "linked_sub"
        link.symlink_to(inside)

        file_probes = pb._collect_file_probes(root, 999, 999, _all_denied_write_probe)
        # Only the real file is probed; the symlinked subdir contributes no
        # synthetic escaping entry since it does not escape.
        assert {fp.relpath for fp in file_probes} == {str(Path("inside_sub") / "real.md")}
        assert all(fp.escapes_subtree is False for fp in file_probes)

    def test_walk_error_becomes_a_synthetic_probe_error_file_probe(
        self, tmp_path: Path, monkeypatch
    ):
        """FINDING 2: a mid-walk scan failure must surface as a synthetic
        PROBE_ERROR FileProbe, never a silent omission."""
        root = tmp_path / "decisions"
        root.mkdir()
        (root / "a.md").write_text("a")
        bad_dir = root / "bad"
        bad_dir.mkdir()

        real_scandir = os.scandir

        def failing_scandir(path="."):
            if Path(path) == bad_dir:
                raise OSError("scandir failed (injected)")
            return real_scandir(path)

        monkeypatch.setattr(pb.os, "scandir", failing_scandir)
        file_probes = pb._collect_file_probes(root, 999, 999, _all_denied_write_probe)
        error_probes = [fp for fp in file_probes if fp.write_result.outcome is pb.ProbeOutcome.PROBE_ERROR]
        assert len(error_probes) == 1
        assert "scandir failed" in error_probes[0].write_result.detail


class TestBlockerOneFalseClosedOnDirectoryEntries:
    """BLOCKER-1 -- the cardinal false-CLOSED: a directory node's own
    write-probe (create+unlink a temp entry) only proves whether NEW
    entries can be added; it says nothing about a pre-existing FILE inside
    (POSIX: overwriting an existing file needs write perm on the FILE, not
    its parent directory). `chmod 0o555 agents/` while leaving
    `orchestrator.md` writable must NOT report CLOSED."""

    def test_verdict_for_path_writable_file_inside_denied_directory_is_not_closed(self):
        probe = pb.PathProbe(
            "agents/*.md",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),  # the DIRECTORY node: denied
            file_probes=(
                pb.FileProbe(
                    "orchestrator.md", pb.ProbeResult(pb.ProbeOutcome.WRITE_OK)
                ),  # the FILE inside: writable
            ),
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert "orchestrator.md" in reason

    def test_decide_refuses_when_directory_node_denied_but_a_file_inside_is_writable(
        self, config_root: Path
    ):
        """Full integration through `collect_path_probes` + `decide()`: the
        directory-node write-probe reports denied for every entry, but the
        pre-existing `agents/orchestrator.md` file -- exactly the G-1
        permission-map file this boundary exists to protect -- reports
        WRITE_OK, simulating `chmod 0o555 agents/` with the `.md` file
        itself left writable. This MUST refuse, never CLOSED."""

        def write_probe(target: Path, agent_uid: int, agent_gid: int) -> pb.ProbeResult:
            if target.name == "orchestrator.md":
                return pb.ProbeResult(pb.ProbeOutcome.WRITE_OK)
            return pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED)

        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert decision.verdict is not pb.Verdict.CLOSED
        assert any("orchestrator.md" in r for r in decision.reasons)

    def test_no_over_triggering_when_directory_node_and_every_file_are_denied(
        self, config_root: Path
    ):
        """The counter-case: when the directory node AND every file inside
        it are genuinely denied, the entry is (correctly) CLOSED -- the fix
        must not over-trigger on the honest all-denied case."""
        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.CLOSED

    def test_per_file_symlink_escape_forces_not_closed(self):
        """A file inside an otherwise-denied directory that is itself a
        symlink escaping the entry's subtree must force NOT_CLOSED, even
        though its own write-probe reports denied."""
        probe = pb.PathProbe(
            "agents/*.md",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
            file_probes=(
                pb.FileProbe(
                    "orchestrator.md",
                    pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
                    escapes_subtree=True,
                ),
            ),
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert "symlink escape" in reason

    def test_decide_refuses_on_real_per_file_symlink_escape_end_to_end(
        self, config_root: Path
    ):
        """End-to-end (pure, no chmod needed): a REAL symlink replacing
        `agents/orchestrator.md`, pointing outside the config root, must be
        caught by the per-file walk's escape check and refuse -- even
        though every write-probe in this test reports denied."""
        escape_target = config_root.parent / "escape.md"
        escape_target.write_text("tampered")
        orchestrator = config_root / "agents" / "orchestrator.md"
        orchestrator.unlink()
        orchestrator.symlink_to(escape_target)

        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert any("orchestrator.md" in r and "escape" in r for r in decision.reasons)

    @pytest.mark.parametrize(
        "outcome",
        [pb.ProbeOutcome.DROP_FAILED, pb.ProbeOutcome.DROP_UNVERIFIED, pb.ProbeOutcome.PROBE_ERROR],
    )
    def test_file_probe_error_outcomes_also_force_not_closed_never_closed(self, outcome):
        """B1 discipline extends to per-file evidence too: a file-probe
        DROP_FAILED/DROP_UNVERIFIED/PROBE_ERROR must never be folded into
        the write-permission signal any more than the directory-node's own
        equivalent outcomes are."""
        probe = pb.PathProbe(
            "agents/*.md",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
            file_probes=(
                pb.FileProbe("orchestrator.md", pb.ProbeResult(outcome, "boom")),
            ),
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert verdict is not pb.ProbeVerdict.CLOSED
        assert outcome.value in reason


class TestResidualFalseClosedSymlinkedSubdirEscape:
    """FINDING 1 -- the residual false-CLOSED, directory-symlink variant:
    a pre-existing symlinked SUBDIR inside a directory enforcement entry
    (e.g. `agents/link -> /writable/elsewhere`) is never descended into
    (correctly), but must still be escape-checked -- otherwise a genuinely
    writable subtree behind it could exist while the entry still reads
    CLOSED. End-to-end through `collect_path_probes` + `decide()`, with
    every real write-probe reporting denied, must REFUSE, never CLOSED."""

    def test_decide_refuses_on_symlinked_subdir_escaping_the_ro_subtree(
        self, config_root: Path
    ):
        writable_elsewhere = config_root.parent / "writable_elsewhere"
        writable_elsewhere.mkdir()
        (config_root / "agents" / "link").symlink_to(writable_elsewhere)

        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert decision.verdict is not pb.Verdict.CLOSED
        assert any("link" in r and "escape" in r for r in decision.reasons)

    def test_verdict_for_path_is_not_closed_when_a_file_probe_records_a_dir_escape(self):
        """Direct unit-level proof: a FileProbe representing an escaping
        symlinked subdir (as `_collect_file_probes` synthesizes) forces
        NOT_CLOSED even when the directory node's own probe reports
        denied."""
        probe = pb.PathProbe(
            "agents/*.md",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
            file_probes=(
                pb.FileProbe(
                    "link",
                    pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED, detail="symlinked subdir"),
                    escapes_subtree=True,
                ),
            ),
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert "link" in reason


class TestResidualFailOpenByOmissionWalkError:
    """FINDING 2 -- a mid-walk `scandir` failure must never be a silent
    omission: it must force the entry to NOT_CLOSED, end-to-end through
    `collect_path_probes` + `decide()`."""

    def test_decide_refuses_when_a_scan_failure_occurs_mid_walk(
        self, config_root: Path, monkeypatch
    ):
        bad_dir = config_root / "decisions" / "bad"
        bad_dir.mkdir()
        real_scandir = os.scandir

        def failing_scandir(path="."):
            if Path(path) == bad_dir:
                raise OSError("scandir failed (injected)")
            return real_scandir(path)

        monkeypatch.setattr(pb.os, "scandir", failing_scandir)
        probes = pb.collect_path_probes(
            config_root,
            agent_uid=999,
            agent_gid=999,
            key_path=_key_path(config_root),
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        decision = pb.decide(probes, pb.KeyState.PRESENT)
        assert decision.verdict is pb.Verdict.REFUSE
        assert decision.verdict is not pb.Verdict.CLOSED
        assert any("scandir failed" in r for r in decision.reasons)

    def test_verdict_for_path_is_not_closed_for_a_synthetic_walk_error_file_probe(self):
        probe = pb.PathProbe(
            "decisions/**",
            pb.Posture.RO,
            pb.ProbeResult(pb.ProbeOutcome.WRITE_DENIED),
            file_probes=(
                pb.FileProbe(
                    "<walk-error>",
                    pb.ProbeResult(pb.ProbeOutcome.PROBE_ERROR, detail="scandir failed"),
                ),
            ),
        )
        verdict, reason = pb.verdict_for_path(probe)
        assert verdict is pb.ProbeVerdict.NOT_CLOSED
        assert "probe_error" in reason


class TestB1GidReadbackAndSetgroups:
    """FIX-2: the B1 drop-and-verify contract also drops supplementary
    groups and independently verifies egid/gid, not just euid/uid. All os
    identity/privilege calls are monkeypatched (never real) so these tests
    are safe to run in-process without actually altering this test
    process's privileges."""

    def test_setgroups_called_before_setgid_before_setuid(self, monkeypatch):
        calls: list[tuple[str, object]] = []
        monkeypatch.setattr(pb.os, "getuid", lambda: 500)
        monkeypatch.setattr(
            pb.os, "setgroups", lambda groups: calls.append(("setgroups", tuple(groups)))
        )
        monkeypatch.setattr(pb.os, "setgid", lambda gid: calls.append(("setgid", gid)))
        monkeypatch.setattr(pb.os, "setuid", lambda uid: calls.append(("setuid", uid)))
        monkeypatch.setattr(pb.os, "geteuid", lambda: 500)
        monkeypatch.setattr(pb.os, "getegid", lambda: 500)
        monkeypatch.setattr(pb.os, "getgid", lambda: 500)

        pb._drop_verify_and_attempt(501, 501, lambda: True)

        assert calls[0] == ("setgroups", ())
        assert calls[1] == ("setgid", 501)
        assert calls[2] == ("setuid", 501)

    def test_setgroups_failure_is_drop_failed_not_write_denied(self, monkeypatch):
        monkeypatch.setattr(pb.os, "getuid", lambda: 500)

        def raise_setgroups(groups):
            raise PermissionError("setgroups: Operation not permitted (injected)")

        monkeypatch.setattr(pb.os, "setgroups", raise_setgroups)
        result = pb._drop_verify_and_attempt(501, 501, lambda: True)
        assert result.outcome is pb.ProbeOutcome.DROP_FAILED
        assert "setgroups" in result.detail

    def test_gid_mismatch_after_drop_is_drop_unverified_even_when_uid_matches(
        self, monkeypatch
    ):
        """The cardinal FIX-2 proof: euid/uid can match post-drop while
        egid/gid does NOT -- this must be DROP_UNVERIFIED, never silently
        treated as a verified drop (the plan's "gid likewise" clause)."""

        calls = {"getuid": 0}

        def fake_getuid():
            calls["getuid"] += 1
            # 1st call = precondition ("already agent_uid?" -> no); 2nd call
            # = the post-drop read-back -> uid matches.
            return 500 if calls["getuid"] == 1 else 501

        monkeypatch.setattr(pb.os, "getuid", fake_getuid)
        monkeypatch.setattr(pb.os, "setgroups", lambda groups: None)
        monkeypatch.setattr(pb.os, "setgid", lambda gid: None)
        monkeypatch.setattr(pb.os, "setuid", lambda uid: None)
        monkeypatch.setattr(pb.os, "geteuid", lambda: 501)  # euid: matches
        monkeypatch.setattr(pb.os, "getegid", lambda: 999)  # egid: MISMATCH
        monkeypatch.setattr(pb.os, "getgid", lambda: 999)  # gid: MISMATCH

        result = pb._drop_verify_and_attempt(501, 501, lambda: True)
        assert result.outcome is pb.ProbeOutcome.DROP_UNVERIFIED
        assert "egid=999" in result.detail
        assert "gid=999" in result.detail

    def test_verified_gid_and_uid_match_proceeds_to_attempt(self, monkeypatch):
        calls = {"getuid": 0}

        def fake_getuid():
            calls["getuid"] += 1
            return 500 if calls["getuid"] == 1 else 501

        monkeypatch.setattr(pb.os, "getuid", fake_getuid)
        monkeypatch.setattr(pb.os, "setgroups", lambda groups: None)
        monkeypatch.setattr(pb.os, "setgid", lambda gid: None)
        monkeypatch.setattr(pb.os, "setuid", lambda uid: None)
        monkeypatch.setattr(pb.os, "geteuid", lambda: 501)
        monkeypatch.setattr(pb.os, "getegid", lambda: 501)
        monkeypatch.setattr(pb.os, "getgid", lambda: 501)

        result = pb._drop_verify_and_attempt(501, 501, lambda: True)
        assert result.outcome is pb.ProbeOutcome.WRITE_OK


class TestForkPipeOSErrorHandling:
    """FIX-3: `os.pipe()`/`os.fork()` themselves can raise `OSError`; both
    are now caught explicitly and mapped to `PROBE_ERROR` rather than
    propagating uncaught."""

    def test_fork_oserror_returns_probe_error(self, monkeypatch):
        def raising_fork():
            raise OSError("fork failed (injected)")

        monkeypatch.setattr(pb.os, "fork", raising_fork)
        result = pb._fork_drop_verify_attempt(os.getuid(), os.getgid(), lambda: True)
        assert result.outcome is pb.ProbeOutcome.PROBE_ERROR
        assert "fork failed" in result.detail

    def test_pipe_oserror_returns_probe_error(self, monkeypatch):
        def raising_pipe():
            raise OSError("pipe failed (injected)")

        monkeypatch.setattr(pb.os, "pipe", raising_pipe)
        result = pb._fork_drop_verify_attempt(os.getuid(), os.getgid(), lambda: True)
        assert result.outcome is pb.ProbeOutcome.PROBE_ERROR
        assert "pipe failed" in result.detail


class TestRunPreflight:
    def test_run_preflight_closed_when_all_denied_and_key_env_points_at_key(
        self, config_root: Path, monkeypatch
    ):
        monkeypatch.setenv(pb.KEY_ENV_VAR, str(_key_path(config_root)))
        decision = pb.run_preflight(
            config_root,
            agent_uid=999,
            agent_gid=999,
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        assert decision.verdict is pb.Verdict.CLOSED

    def test_run_preflight_refuses_when_key_env_unset(self, config_root: Path, monkeypatch):
        monkeypatch.delenv(pb.KEY_ENV_VAR, raising=False)
        decision = pb.run_preflight(
            config_root,
            agent_uid=999,
            agent_gid=999,
            write_probe=_all_denied_write_probe,
            read_probe=_all_denied_read_probe,
        )
        assert decision.verdict is pb.Verdict.REFUSE

    def test_run_preflight_override_never_reaches_closed(self, config_root: Path, monkeypatch):
        monkeypatch.delenv(pb.KEY_ENV_VAR, raising=False)

        def writable(target: Path, agent_uid: int, agent_gid: int) -> pb.ProbeResult:
            return pb.ProbeResult(pb.ProbeOutcome.WRITE_OK)

        decision = pb.run_preflight(
            config_root,
            agent_uid=999,
            agent_gid=999,
            override_ack=True,
            write_probe=writable,
            read_probe=writable,
        )
        assert decision.verdict is pb.Verdict.PROCEED_UNCLOSED
        assert decision.verdict is not pb.Verdict.CLOSED


# ---------------------------------------------------------------------------
# Real thin edge (fork + pipe), exercised in-sandbox with an INJECTED
# `attempt` callable so the outcome is deterministic without real perms.
# Uses agent_uid == os.getuid() so no actual setuid/setgid occurs (the
# honest single-uid-box path) -- this genuinely runs the fork/pipe IPC.
# ---------------------------------------------------------------------------

class TestRealForkEdgeWithInjectedAttempt:
    def test_write_ok_via_real_fork_same_uid(self):
        result = pb._fork_drop_verify_attempt(os.getuid(), os.getgid(), lambda: True)
        assert result.outcome is pb.ProbeOutcome.WRITE_OK

    def test_write_denied_via_real_fork_same_uid(self):
        def raise_permission_error():
            raise PermissionError("EACCES (injected)")

        result = pb._fork_drop_verify_attempt(os.getuid(), os.getgid(), raise_permission_error)
        assert result.outcome is pb.ProbeOutcome.WRITE_DENIED
        assert "injected" in result.detail

    def test_probe_error_on_unexpected_exception(self):
        def raise_value_error():
            raise ValueError("unexpected (injected)")

        result = pb._fork_drop_verify_attempt(os.getuid(), os.getgid(), raise_value_error)
        assert result.outcome is pb.ProbeOutcome.PROBE_ERROR

    def test_probe_error_on_falsy_attempt_without_raising(self):
        result = pb._fork_drop_verify_attempt(os.getuid(), os.getgid(), lambda: False)
        assert result.outcome is pb.ProbeOutcome.PROBE_ERROR

    def test_probe_write_as_agent_real_write_succeeds_same_uid(self, tmp_path: Path):
        result = pb.probe_write_as_agent(tmp_path, os.getuid(), os.getgid())
        assert result.outcome is pb.ProbeOutcome.WRITE_OK

    def test_probe_read_key_as_agent_real_read_succeeds_same_uid(self, tmp_path: Path):
        key = tmp_path / "key"
        key.write_bytes(b"secret")
        result = pb.probe_read_key_as_agent(key, os.getuid(), os.getgid())
        assert result.outcome is pb.ProbeOutcome.WRITE_OK


# ---------------------------------------------------------------------------
# Escape hatch (Part 0): never enumerated, checked, or restricted.
# ---------------------------------------------------------------------------

class TestEscapeHatchNeverEnumerated:
    def test_enforcement_paths_contain_no_escape_hatch_reference(self):
        for ep in pb.ENFORCEMENT_PATHS:
            haystack = f"{ep.label} {ep.relative} {ep.description}".lower()
            assert "/plan" not in haystack
            assert "/build" not in haystack
            assert "escape" not in haystack or "escape_hatch" not in haystack

    def test_module_exposes_no_operator_agent_enumeration(self):
        names = [n.lower() for n in pb.__all__]
        for forbidden in ("plan_agent", "build_agent", "escape_hatch", "operator_agent"):
            assert not any(forbidden in n for n in names)

    def test_no_function_or_constant_references_plan_or_build_agents(self):
        """The functional surface (not prose/docstrings, which legitimately
        name the Part-0 constraint) contains no `/plan`/`/build` agent
        reference: no ENFORCEMENT_PATHS entry, no function name, no enum
        member names either escape-hatch agent."""
        names = [n.lower() for n in dir(pb)]
        for forbidden in ("plan", "build"):
            # "plan"/"build" as whole tokens only -- avoid false positives on
            # unrelated words; none of this module's public names are or
            # contain these tokens as agent references.
            assert forbidden not in names
