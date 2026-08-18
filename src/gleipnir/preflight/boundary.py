"""S-2/G-1 closure — the fail-closed boundary preflight (pure core + thin edge).

Spec: `.gleipnir/plans/s2-g1-closure-first-slice.md` (Trace "the concrete
mechanism (probe, don't assume)" and B1). This module mirrors the shape of
`gleipnir.sandbox.runtime`: a pure, fully-unit-testable decision core, plus a
thin OS edge (fork + privilege-drop + real write/read attempt) that is
INJECTABLE everywhere the pure core needs it, so the decision logic is
testable without any real permission separation.

Two audiences read a module built for a security boundary differently, so the
shape is deliberately explicit:

  * **Pure core** (`ENFORCEMENT_PATHS`, `Posture`, `resolve_final_target`,
    `target_escapes_subtree`, `ProbeOutcome`, `ProbeResult`,
    `classify_probe_result`, `verdict_for_path`, `check_key_state`,
    `decide`) — no I/O beyond `Path.exists`/`Path.resolve`; every branch is
    driven by data passed in, never by a live probe. Fully unit-testable
    in-sandbox (root), because it never touches OS permission bits itself.
  * **Thin edge** (`probe_write_as_agent`, `probe_read_key_as_agent`, and the
    fork/pipe machinery underneath) — the only place real `os.fork`,
    `os.setuid`/`os.setgid`, and real file writes/reads happen. Genuinely
    exercised (real chmod, real perms) only off-root — see
    `tests/test_preflight_probe_hostonly.py`, `@pytest.mark.hostonly`,
    skipped under root/in-sandbox (root bypasses permission bits, which would
    make a "denied" test observationally indistinguishable from a "writable"
    one — the same trap `tests/test_bus_emit.py` already documents).

**Fail-closed is the only default.** Every ambiguous, missing, or erroring
condition maps to `NOT_CLOSED` at the per-path level and `REFUSE` at the
top-level `decide()` — never "assume fine". `os.access()` is never imported
or used anywhere in this module: the verdict comes only from an *actually
attempted* write/read after a verified privilege drop (see B1 below).

**B1 — the privilege-drop-and-verify CRUX.** A forked child drops
supplementary groups (`os.setgroups([])`) then privilege to the target agent
uid/gid, then *independently verifies* the drop took effect (`os.geteuid()`
AND `os.getuid()` both equal the target uid, `os.getegid()` AND `os.getgid()`
both equal the target gid) BEFORE attempting the real write/read. The drop
and the write/read are two SEPARATE, separately-classified steps — never one
broad `except PermissionError` spanning both — so a failed or unverifiable
drop can never masquerade as "the file is safely read-only". The
discriminated outcome the child reports is exactly: `DROP_FAILED`,
`DROP_UNVERIFIED`, `WRITE_DENIED` (=> closed for that probe), `WRITE_OK`
(=> not closed), or `PROBE_ERROR`. Only `WRITE_DENIED` ever contributes a
CLOSED signal; every other outcome forces that path's verdict to
`NOT_CLOSED`, which in turn can only ever yield `REFUSE` or (with the Part-0
operator override) an honestly labelled `PROCEED_UNCLOSED` — never `CLOSED`.

**The per-file walk (closes the false-CLOSED on directory entries).** For a
DIRECTORY-type enforcement path (`agents/`, `decisions/`, `goals/`, `keys/`,
`plugins/`), the directory node's own write-probe (create+unlink a temp
entry) only proves whether NEW entries can be added to the directory — POSIX
requires write permission on a FILE itself (not its parent directory) to
overwrite that file's existing content, so a read-only directory containing
a still-writable pre-existing file (e.g. `agents/orchestrator.md`, exactly
the permission map G-1 protects) would otherwise report a false `CLOSED`.
`collect_path_probes` therefore recursively walks (`_walk_enforcement_files`)
and write-probes + symlink-resolves EVERY FILE actually present under a
directory entry, AND escape-checks (but never descends into) every symlinked
SUBDIRECTORY encountered along the way — `os.walk(followlinks=False)`
correctly refuses to descend into a symlinked subdir, but still reports it
in `dirnames` (never `filenames`), so without an explicit check it would be
neither write-probed nor escape-checked and nothing behind it walked: a
genuinely-writable subtree reachable only through such a symlinked subdir
would go completely unnoticed while the entry still reads `CLOSED`.
`_collect_file_probes` attaches all of this evidence — per-file probes,
per-symlinked-subdir escape signals, and any surfaced `os.walk` scan error
(see below) — as `PathProbe.file_probes`. `verdict_for_path` folds this in:
the entry is `CLOSED` only if the directory node itself AND every file
underneath it AND every symlinked subdir encountered are all
write-denied/non-escaping/error-free — a single writable file, escaping
file, escaping symlinked subdir, or walk error forces `NOT_CLOSED` for the
whole entry.

**Walk errors are fail-closed, never silently swallowed.** `os.walk`'s
default `onerror=None` silently drops any branch where a mid-walk
`scandir`/`listdir` call fails — files under that branch are simply omitted
from `filenames`, which could hide a writable file entirely (a
fail-open-by-omission, not merely an incomplete scan). `_walk_enforcement_files`
therefore passes an explicit `onerror` callback that records the failure
instead of swallowing it; `_collect_file_probes` turns any recorded walk
error into a synthetic `PROBE_ERROR` `FileProbe`, which `verdict_for_path`
already treats as an unconditional `NOT_CLOSED` (the same B1 discipline as
every other error outcome) — a partial, error-truncated scan is never
reported as "scanned clean".

**Escape hatch (Part 0).** This module's subject set is the in-framework
roster's enforcement paths only. It contains no reference to, enumeration
of, or restriction on the operator's built-in `/plan` / `/build` agents —
see `.gleipnir/plans/s2-g1-closure-first-slice.md` Architect "Explicitly NOT
a user / NOT in scope".
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Sequence

from ..verify.marker import KEY_ENV_VAR

__all__ = [
    "KEY_ENV_VAR",
    "Posture",
    "EnforcementPath",
    "ENFORCEMENT_PATHS",
    "resolve_final_target",
    "target_escapes_subtree",
    "ProbeOutcome",
    "ProbeResult",
    "ProbeVerdict",
    "classify_probe_result",
    "outcome_forces_refuse",
    "outcome_is_op_ok",
    "FileProbe",
    "PathProbe",
    "verdict_for_path",
    "KeyState",
    "check_key_state",
    "Verdict",
    "RequestedMode",
    "DEV_MODE_LABEL",
    "UNCAGED_DEFAULT_LABEL",
    "PreflightDecision",
    "decide",
    "probe_write_as_agent",
    "probe_read_key_as_agent",
    "collect_path_probes",
    "run_preflight",
]


# ---------------------------------------------------------------------------
# The enforcement-path set — data, in code (per Trace: "not inferred by
# globbing writability; the named set above, so a newly-added enforcement
# file that someone forgot to list is caught by review, not silently
# trusted"). Relative to the OPENCODE_CONFIG_DIR (`.gleipnir/`).
# ---------------------------------------------------------------------------

class Posture(Enum):
    """The required OS posture for an enforcement path.

    ``RO``: unwritable to the agent uid suffices (the write-probe alone
    decides). ``RO_AND_UNREADABLE``: unwritable AND unreadable — only the
    `keys/` entry needs this (D3: the HMAC key must not be forgeable, and
    read, not just write, is the threat)."""

    RO = "ro"
    RO_AND_UNREADABLE = "ro_and_unreadable"


@dataclass(frozen=True)
class EnforcementPath:
    """One named enforcement path (Trace's B3-corrected table, as data)."""

    label: str
    relative: str
    posture: Posture
    description: str
    # Only `plugins/` gets this: "tolerates a future-absent case (dir
    # emptied) as not-a-failure-for-absence" — every other path missing
    # entirely is a real failure (a missing guard file is not a closed one).
    tolerate_absent: bool = False


ENFORCEMENT_PATHS: tuple[EnforcementPath, ...] = (
    EnforcementPath(
        "agents/*.md",
        "agents",
        Posture.RO,
        "agent permission maps — the caging permission maps themselves (G-1)",
    ),
    EnforcementPath(
        "stage-role-map.md",
        "stage-role-map.md",
        Posture.RO,
        "G-5 engine's state->role binding",
    ),
    EnforcementPath(
        "decisions/**",
        "decisions",
        Posture.RO,
        "Tier-3 POLICY durable decision records (the LOCKED D1-D5 this "
        "boundary operationalizes)",
    ),
    EnforcementPath(
        "goals/**",
        "goals",
        Posture.RO,
        "Tier-3 POLICY process-as-data goals (K-1); steers planning/methodology",
    ),
    EnforcementPath(
        "keys/**",
        "keys",
        Posture.RO_AND_UNREADABLE,
        "G-3 HMAC key + rate table/toggles/approved digests (D3: key must be "
        "unreadable, not merely unwritable)",
    ),
    EnforcementPath(
        "plugins/**",
        "plugins",
        Posture.RO,
        "guard code/hooks (e.g. sequence-gate.ts) — a live G-1 exposure today",
        tolerate_absent=True,
    ),
    EnforcementPath(
        "sandbox/**",
        "sandbox",
        Posture.RO,
        "the Tier-3 toolchain-dispatch config; the test command it declares "
        "is the Axiom-1 arbiter, so it must be agent-unwritable",
        tolerate_absent=False,
    ),
    EnforcementPath(
        "AGENTS.md",
        "AGENTS.md",
        Posture.RO,
        "framework governing instructions — POLICY-class, enforcement-adjacent",
    ),
)

# Escape-hatch discipline (Part 0): this module's subject set is exactly the
# tuple above. Nothing here enumerates, checks, or restricts the operator's
# built-in escape-hatch agents.


# ---------------------------------------------------------------------------
# Symlink resolution — catch a ro enforcement path symlinked into a writable
# location (Trace item 3: "the symlink-resolution check").
# ---------------------------------------------------------------------------

def resolve_final_target(path: Path) -> Path:
    """Fully resolve symlinks to `path`'s final target.

    `Path.resolve()` follows an arbitrary chain of symlinks and normalises
    the result, so a symlink FROM inside the read-only enforcement subtree
    pointing INTO a writable location is caught by checking the RESOLVED
    target's writability — never the symlink's own (irrelevant) mode bits.
    """

    return path.resolve()


def target_escapes_subtree(path: Path, subtree_root: Path) -> bool:
    """True iff `path`'s fully-resolved final target is NOT inside
    `subtree_root` (also fully resolved) — the symlink-escape bypass this
    check exists to close.

    Any resolution error (symlink loop, unresolvable path) is itself treated
    as an escape (fail-closed): an unresolvable enforcement path is not a
    verifiably-closed one.
    """

    try:
        resolved = resolve_final_target(path)
        resolved_root = resolve_final_target(subtree_root)
    except (OSError, RuntimeError):
        # RuntimeError: Path.resolve() raises this (not OSError) for a
        # detected symlink loop (ELOOP) -- still an unresolvable path, still
        # fail-closed as an escape.
        return True
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return True
    return False


# ---------------------------------------------------------------------------
# B1 — the discriminated probe-result type. The fork child reports exactly
# one of these; the parent maps ONLY WRITE_DENIED into a "closed" signal —
# every other outcome is its own unconditional error case.
# ---------------------------------------------------------------------------

class ProbeOutcome(Enum):
    DROP_FAILED = "drop_failed"
    DROP_UNVERIFIED = "drop_unverified"
    WRITE_DENIED = "write_denied"
    WRITE_OK = "write_ok"
    PROBE_ERROR = "probe_error"


@dataclass(frozen=True)
class ProbeResult:
    """The discriminated result of one attempted-write-or-read probe
    (produced either by the real thin edge, or injected directly in tests)."""

    outcome: ProbeOutcome
    detail: str = ""


def outcome_forces_refuse(outcome: ProbeOutcome) -> bool:
    """B1: `DROP_FAILED`, `DROP_UNVERIFIED` and `PROBE_ERROR` are never
    folded into the normal write_ok/read_ok boolean the rest of the
    decision logic consumes — they are their own unconditional-REFUSE error
    cases. A failed or unverifiable privilege drop must never masquerade as
    "the file is safely read-only"."""

    return outcome in (
        ProbeOutcome.DROP_FAILED,
        ProbeOutcome.DROP_UNVERIFIED,
        ProbeOutcome.PROBE_ERROR,
    )


def outcome_is_op_ok(outcome: ProbeOutcome) -> bool:
    """Only meaningful when `outcome_forces_refuse(outcome)` is False.
    `WRITE_OK` means the attempted write/read landed (NOT closed for that
    probe); `WRITE_DENIED` means it raised `PermissionError` (closed for
    that probe)."""

    return outcome is ProbeOutcome.WRITE_OK


# ---------------------------------------------------------------------------
# Pure per-path classification: combine write/read/symlink facts + posture
# into one CLOSED/NOT_CLOSED verdict for a single enforcement path.
# ---------------------------------------------------------------------------

class ProbeVerdict(Enum):
    CLOSED = "closed"
    NOT_CLOSED = "not_closed"


def classify_probe_result(
    write_ok: bool,
    read_ok: bool,
    resolved_escapes: bool,
    posture: Posture,
) -> ProbeVerdict:
    """Pure mapping from one enforcement path's probed facts to a verdict.

    `CLOSED` only if: the write did NOT succeed (`write_ok` is False), the
    symlink-resolved target does NOT escape the ro subtree, AND — for a
    `RO_AND_UNREADABLE` posture (the key) — the read ALSO did not succeed.
    Any unexpected/ambiguous combination defaults to `NOT_CLOSED`
    (fail-closed default, per plan Trace)."""

    if resolved_escapes:
        return ProbeVerdict.NOT_CLOSED
    if write_ok:
        return ProbeVerdict.NOT_CLOSED
    if posture is Posture.RO_AND_UNREADABLE and read_ok:
        return ProbeVerdict.NOT_CLOSED
    return ProbeVerdict.CLOSED


@dataclass(frozen=True)
class FileProbe:
    """One pre-existing FILE's write-probe evidence, collected when an
    enforcement path is a DIRECTORY (the BLOCKER-1 false-CLOSED fix): the
    directory-node probe alone (create+unlink a temp entry) only tests
    whether NEW entries can be created in the directory — it says nothing
    about whether a file already inside is itself writable (POSIX requires
    write permission on the FILE, not its parent directory, to overwrite
    existing content). `relpath` is this file's path relative to the
    enforcement entry's own root (e.g. `"orchestrator.md"` under the
    `agents/` entry), for human-readable reporting. `escapes_subtree` is the
    per-FILE symlink-escape check (a file inside a ro directory that is
    itself a symlink escaping the subtree)."""

    relpath: str
    write_result: ProbeResult
    escapes_subtree: bool = False


@dataclass(frozen=True)
class PathProbe:
    """One enforcement path's collected evidence, ready for `decide()`.

    `write_result` is the discriminated outcome of the write-probe against
    this path (the directory/file NODE itself). `read_result` is populated
    ONLY for `RO_AND_UNREADABLE` postures (the key) and is the discriminated
    outcome of the read-probe against the actual key file. `escapes_subtree`
    is the pure symlink check's result for this path's own node.
    `file_probes` holds the per-FILE evidence collected for DIRECTORY-type
    entries (empty for plain-file entries) — see `FileProbe`; ANY entry in
    `file_probes` that is writable, escaping, or itself errored forces this
    whole path's verdict to `NOT_CLOSED`, regardless of what the directory
    node's own probe reported."""

    label: str
    posture: Posture
    write_result: ProbeResult
    escapes_subtree: bool = False
    read_result: ProbeResult | None = None
    file_probes: tuple[FileProbe, ...] = ()


def verdict_for_path(probe: PathProbe) -> tuple[ProbeVerdict, str]:
    """Combine one path's write/read/symlink/per-file evidence into a
    verdict + human-readable reason. B1 error outcomes (`DROP_FAILED`,
    `DROP_UNVERIFIED`, `PROBE_ERROR`) on EITHER the write or read probe
    short-circuit straight to `NOT_CLOSED` — they never reach
    `classify_probe_result`'s normal boolean combination, so they can never
    be misread as "closed". Per BLOCKER-1: ANY `FileProbe` in
    `probe.file_probes` that is writable, escaping, or itself errored ALSO
    short-circuits straight to `NOT_CLOSED` — a directory node reporting
    "denied" can never outweigh a single writable file underneath it."""

    if outcome_forces_refuse(probe.write_result.outcome):
        return (
            ProbeVerdict.NOT_CLOSED,
            f"{probe.label}: write probe {probe.write_result.outcome.value} "
            f"({probe.write_result.detail or 'no detail'})",
        )
    write_ok = outcome_is_op_ok(probe.write_result.outcome)

    read_ok = False
    if probe.posture is Posture.RO_AND_UNREADABLE:
        if probe.read_result is None:
            return (
                ProbeVerdict.NOT_CLOSED,
                f"{probe.label}: RO_AND_UNREADABLE posture but no read-probe "
                "result was collected (ambiguous => refuse)",
            )
        if outcome_forces_refuse(probe.read_result.outcome):
            return (
                ProbeVerdict.NOT_CLOSED,
                f"{probe.label}: read probe {probe.read_result.outcome.value} "
                f"({probe.read_result.detail or 'no detail'})",
            )
        read_ok = outcome_is_op_ok(probe.read_result.outcome)

    # BLOCKER-1: the directory node's own probe only proves whether NEW
    # entries can be created in it. Any pre-existing FILE underneath that is
    # itself writable, escaping, or whose probe errored/dropped-unverified
    # forces NOT_CLOSED for the WHOLE entry — this can never be masked by
    # the directory node otherwise reporting "denied".
    for fp in probe.file_probes:
        if outcome_forces_refuse(fp.write_result.outcome):
            return (
                ProbeVerdict.NOT_CLOSED,
                f"{probe.label}: file {fp.relpath!r} write probe "
                f"{fp.write_result.outcome.value} "
                f"({fp.write_result.detail or 'no detail'})",
            )
        if fp.escapes_subtree:
            return (
                ProbeVerdict.NOT_CLOSED,
                f"{probe.label}: file {fp.relpath!r} resolves outside the "
                "enforcement subtree (per-file symlink escape)",
            )
        if outcome_is_op_ok(fp.write_result.outcome):
            return (
                ProbeVerdict.NOT_CLOSED,
                f"{probe.label}: file {fp.relpath!r} is writable "
                "(the directory-node probe alone would have missed this)",
            )

    verdict = classify_probe_result(
        write_ok, read_ok, probe.escapes_subtree, probe.posture
    )
    if verdict is ProbeVerdict.CLOSED:
        return verdict, ""
    return (
        verdict,
        f"{probe.label}: not closed (write_ok={write_ok} read_ok={read_ok} "
        f"escapes_subtree={probe.escapes_subtree})",
    )


# ---------------------------------------------------------------------------
# Key state (owning-principal's view: does a usable key even exist?) — a
# fail-closed classification distinct from the per-path key-UNREADABLE
# check above (which is about the AGENT uid's access, not the owner's).
# ---------------------------------------------------------------------------

class KeyState(Enum):
    ABSENT = "absent"
    EMPTY = "empty"
    PRESENT = "present"


def check_key_state(key_path: Path | None) -> KeyState:
    """From the OWNING principal's perspective (this preflight runs as the
    owner, never the agent): is there a usable key at all? Mirrors
    `verify.marker.load_key`'s fail-closed absent/empty handling, without
    raising — `decide()` needs a classification, not an exception. No marker
    code is imported or changed beyond the shared `KEY_ENV_VAR` name."""

    if key_path is None:
        return KeyState.ABSENT
    try:
        raw = key_path.read_bytes()
    except OSError:
        return KeyState.ABSENT
    if len(raw.strip()) == 0:
        return KeyState.EMPTY
    return KeyState.PRESENT


# ---------------------------------------------------------------------------
# Top-level decision: AND-of-all-CLOSED across every enforcement path + the
# key-state check. Fail-closed on ANY ambiguity. The Part-0 operator
# override can only escalate NOT_CLOSED -> PROCEED_UNCLOSED; it can NEVER
# produce CLOSED.
# ---------------------------------------------------------------------------

class Verdict(Enum):
    CLOSED = "closed"
    PROCEED_UNCLOSED = "proceed_unclosed"
    REFUSE = "refuse"


class RequestedMode(Enum):
    """The operator's INTENDED posture for this launch (D1/D4).

    Influences ONLY the returned label + the CLI's exit-code interpretation.
    It NEVER enters the all_closed computation: a CAGED request cannot
    manufacture CLOSED -- closure stays gated solely on real probe evidence
    (the anti-false-assurance invariant, brief D1)."""

    UNCAGED = "uncaged"
    CAGED = "caged"


DEV_MODE_LABEL = "G-1 NOT closed (dev-mode)"

# D4: the legitimate, non-failing default label. The deficiency label
# (DEV_MODE_LABEL) is retained ONLY for a requested-CAGED run that did not
# reach CLOSED -- never for the uncaged default.
UNCAGED_DEFAULT_LABEL = "uncaged (key-protected floor) -- default operator-trust posture"


@dataclass(frozen=True)
class PreflightDecision:
    verdict: Verdict
    label: str
    reasons: tuple[str, ...] = ()


def decide(
    path_probes: Sequence[PathProbe],
    key_state: KeyState,
    *,
    override_ack: bool = False,
    requested_mode: RequestedMode = RequestedMode.UNCAGED,
) -> PreflightDecision:
    """Aggregate every enforcement path's verdict + the key-state check into
    one `PreflightDecision`. `CLOSED` only if every path is `CLOSED` AND
    `key_state` is `PRESENT` (a present, non-empty key, from the owner's
    view — the per-path key-UNREADABLE check is folded into the `keys/**`
    path's own verdict above). ANY `NOT_CLOSED` path, ANY non-`PRESENT` key
    state, or an empty `path_probes` sequence (itself ambiguous — no
    evidence is not evidence of closure) => fail-closed.

    The Part-0 operator override (`override_ack`) can ONLY escalate a
    not-closed result to `PROCEED_UNCLOSED`, stamped with the honest
    `DEV_MODE_LABEL`. It can never produce `CLOSED` — there is no code path
    from `override_ack=True` to `Verdict.CLOSED` in this function."""

    reasons: list[str] = []
    all_closed = True

    if not path_probes:
        all_closed = False
        reasons.append("no enforcement paths were probed (ambiguous => refuse)")

    for probe in path_probes:
        verdict, reason = verdict_for_path(probe)
        if verdict is not ProbeVerdict.CLOSED:
            all_closed = False
            reasons.append(reason)

    if key_state is KeyState.ABSENT:
        all_closed = False
        reasons.append("key: absent (no key => no closed boundary)")
    elif key_state is KeyState.EMPTY:
        all_closed = False
        reasons.append("key: empty (zero-byte key => no closed boundary)")

    if all_closed:
        return PreflightDecision(
            Verdict.CLOSED, "G-1 boundary held at the OS-perms floor", tuple(reasons)
        )
    if override_ack:
        # override path unchanged: honest DEV_MODE_LABEL, PROCEED_UNCLOSED.
        return PreflightDecision(Verdict.PROCEED_UNCLOSED, DEV_MODE_LABEL, tuple(reasons))
    if requested_mode is RequestedMode.CAGED:
        # A cage was REQUESTED and not reached -- stays loud, fail-closed. Per
        # D4 the deficiency label (DEV_MODE_LABEL) is retained here, and ONLY
        # here (a requested-CAGED run that did not reach CLOSED) -- never for
        # the uncaged default below.
        return PreflightDecision(Verdict.REFUSE, DEV_MODE_LABEL, tuple(reasons))
    # Uncaged default: legitimate, non-failing posture. Reasons retained as
    # INFORMATIONAL, not a deficiency dump.
    return PreflightDecision(
        Verdict.PROCEED_UNCLOSED, UNCAGED_DEFAULT_LABEL, tuple(reasons)
    )


# ---------------------------------------------------------------------------
# Thin edge: real write/read attempts (stdlib `open`) — used by the fork
# child below. `os.access()` is deliberately never used anywhere in this
# module: it must never gate the verdict, and must never gate whether the
# real probe runs.
# ---------------------------------------------------------------------------

def _attempt_write(target: Path) -> bool:
    """Real write attempt against `target`.

    For a directory: create + unlink a uniquely-named temp entry inside it
    (the real OS check for directory writability). For a file: open for
    append then close without writing content — `open(..., "ab")` itself
    raises `PermissionError` if unwritable, which is the real signal.
    A real `PermissionError` propagates to the caller uninterpreted; this
    function's return value is only ever `True` (it never returns `False` —
    any failure is an exception, never a falsy success)."""

    if target.is_dir():
        probe_file = target / f".gleipnir-preflight-probe-{os.getpid()}"
        with open(probe_file, "wb"):
            pass
        probe_file.unlink()
        return True
    with open(target, "ab"):
        pass
    return True


def _attempt_read(path: Path) -> bool:
    """Real read attempt: opens and reads `path`'s bytes. A real
    `PermissionError` propagates uninterpreted. Emptiness is a `KeyState`
    concern (checked separately, from the owner's view) — this function only
    answers "could the agent uid read the bytes at all"."""

    with open(path, "rb") as fh:
        fh.read()
    return True


def _drop_verify_and_attempt(
    agent_uid: int,
    agent_gid: int,
    attempt: Callable[[], bool],
) -> ProbeResult:
    """Runs INSIDE the forked child. The three B1 steps, separately
    classified — never one broad `except PermissionError` spanning drop AND
    write/read:

      1. Drop (supplementary groups via `os.setgroups([])`, then setgid,
         then setuid) — skipped entirely if already running as `agent_uid`
         (the honest single-uid-box path: no drop needed, the write/read is
         attempted as the only uid there is).
      2. Independent euid/uid AND egid/gid read-back verification.
      3. Only then: `attempt()`.
    """

    if os.getuid() != agent_uid:
        try:
            # Drop supplementary groups BEFORE setgid/setuid — a dropped
            # primary gid is meaningless if a supplementary group still
            # grants access. Guarded for platforms without `os.setgroups`
            # (e.g. it is POSIX-only); any failure here (including a
            # permission error) is itself a DROP_FAILED case, same as a
            # failed setgid/setuid — never interpreted as the file being
            # read-only.
            if hasattr(os, "setgroups"):
                os.setgroups([])
            os.setgid(agent_gid)
            os.setuid(agent_uid)
        except (PermissionError, OSError) as exc:
            return ProbeResult(ProbeOutcome.DROP_FAILED, detail=str(exc))

        if (
            os.geteuid() != agent_uid
            or os.getuid() != agent_uid
            or os.getegid() != agent_gid
            or os.getgid() != agent_gid
        ):
            return ProbeResult(
                ProbeOutcome.DROP_UNVERIFIED,
                detail=(
                    f"euid={os.geteuid()} uid={os.getuid()} "
                    f"egid={os.getegid()} gid={os.getgid()} "
                    f"!= agent_uid={agent_uid} agent_gid={agent_gid} after drop"
                ),
            )

    try:
        ok = attempt()
    except PermissionError as exc:
        return ProbeResult(ProbeOutcome.WRITE_DENIED, detail=str(exc))
    except Exception as exc:  # fail-closed: any surprise is an error, never CLOSED
        return ProbeResult(ProbeOutcome.PROBE_ERROR, detail=str(exc))

    if ok:
        return ProbeResult(ProbeOutcome.WRITE_OK)
    return ProbeResult(
        ProbeOutcome.PROBE_ERROR, detail="attempt() returned a falsy result without raising"
    )


def _fork_drop_verify_attempt(
    agent_uid: int,
    agent_gid: int,
    attempt: Callable[[], bool],
) -> ProbeResult:
    """The B1 CRUX, real edge: fork; the child performs
    `_drop_verify_and_attempt` and reports its discriminated `ProbeResult`
    back to the parent over a pipe (never via exit status alone — the
    payload is explicit so there is no ambiguity about *why* the child
    exited). Forking (rather than dropping privilege in this process) is
    what makes the drop safe to attempt at all: `setuid` is irreversible in
    the calling process, so the privilege drop must happen in a disposable
    child.

    `os.pipe()`/`os.fork()` themselves can raise `OSError` (e.g. resource
    exhaustion, `EMFILE`/`ENOMEM`) — both are wrapped and explicitly mapped
    to `ProbeOutcome.PROBE_ERROR` (fail-closed) rather than propagating
    uncaught out of this function."""

    try:
        read_fd, write_fd = os.pipe()
    except OSError as exc:
        return ProbeResult(ProbeOutcome.PROBE_ERROR, detail=f"os.pipe failed: {exc}")

    try:
        pid = os.fork()
    except OSError as exc:
        os.close(read_fd)
        os.close(write_fd)
        return ProbeResult(ProbeOutcome.PROBE_ERROR, detail=f"os.fork failed: {exc}")

    if pid == 0:
        os.close(read_fd)
        result = _drop_verify_and_attempt(agent_uid, agent_gid, attempt)
        payload = f"{result.outcome.value}\x1f{result.detail}".encode("utf-8", "replace")
        try:
            os.write(write_fd, payload)
        finally:
            os.close(write_fd)
        os._exit(0)

    os.close(write_fd)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(read_fd, 4096)
        if not chunk:
            break
        chunks.append(chunk)
    os.close(read_fd)
    _pid, status = os.waitpid(pid, 0)

    raw = b"".join(chunks).decode("utf-8", "replace")
    if "\x1f" not in raw:
        return ProbeResult(
            ProbeOutcome.PROBE_ERROR,
            detail=f"child reported no parseable result (wait status {status})",
        )
    outcome_str, _, detail = raw.partition("\x1f")
    try:
        outcome = ProbeOutcome(outcome_str)
    except ValueError:
        return ProbeResult(
            ProbeOutcome.PROBE_ERROR,
            detail=f"unrecognized child outcome {outcome_str!r}",
        )
    return ProbeResult(outcome, detail=detail)


def probe_write_as_agent(target: Path, agent_uid: int, agent_gid: int) -> ProbeResult:
    """Real thin edge: forks, drops to `(agent_uid, agent_gid)` [verified via
    euid/uid read-back] in the child, then attempts a real write against
    `target`. See B1: the drop and the write are separately classified.

    On a single-uid box (`agent_uid == os.getuid()`) no drop is attempted —
    the write is attempted directly in the child, correctly reporting
    `WRITE_OK` (writable => NOT closed) rather than lying about a boundary
    that does not exist."""

    return _fork_drop_verify_attempt(agent_uid, agent_gid, lambda: _attempt_write(target))


def probe_read_key_as_agent(key_path: Path, agent_uid: int, agent_gid: int) -> ProbeResult:
    """Real thin edge: same drop-verify-attempt sequence as
    `probe_write_as_agent`, but the attempted operation is a real READ of
    the key bytes at `key_path`. Success => the key is readable by the agent
    uid => NOT closed (D3: the key must be unreadable, not merely
    unwritable)."""

    return _fork_drop_verify_attempt(agent_uid, agent_gid, lambda: _attempt_read(key_path))


# ---------------------------------------------------------------------------
# BLOCKER-1 fix (+ the two walk-completeness residuals): the per-file walk
# for DIRECTORY-type enforcement entries. The directory node's own
# write-probe (create+unlink a temp entry) only tests whether NEW entries
# can be created; it says nothing about whether a pre-existing file inside
# is itself writable. Walk and probe every file — and, per the two residual
# gaps this section closes, also escape-check every symlinked SUBDIRECTORY
# `os.walk` reports but never descends into, and surface (never swallow) any
# mid-walk scan error.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _WalkOutcome:
    """One directory entry's raw walk evidence, before any probing.

    `files`: every FILE actually present (recursively, `"**"`-posture full
    recurse) — never includes anything reached only through a symlinked
    subdirectory, since those are never descended into.
    `symlinked_dirs`: every `dirnames` entry `os.walk` reported that is
    itself a symlink — collected (not descended into) so the caller can
    escape-check each one; without this they would otherwise be neither
    write-probed nor escape-checked, and the residual-gap this closes is
    exactly that a genuinely-writable subtree reachable only through one of
    these could exist while the entry still read `CLOSED`.
    `errors`: every `OSError` `os.walk`'s `onerror` hook reported for a
    mid-walk `scandir`/`listdir` failure, as `str(exc)` — surfaced here
    instead of being silently swallowed by the default `onerror=None`
    (which would simply omit files in that branch, a fail-open-by-omission)."""

    files: list[Path]
    symlinked_dirs: list[Path]
    errors: list[str]


def _walk_enforcement_files(target: Path) -> _WalkOutcome:
    """Recursively walk directory `target` (a `"**"`-posture full recurse)
    and return a `_WalkOutcome`: every FILE actually present, every
    symlinked SUBDIRECTORY encountered (never descended into), and any
    mid-walk scan error.

    Uses `os.walk(..., followlinks=False)` so a symlinked SUBDIRECTORY is
    never descended into (avoiding traversal loops/escapes through a
    directory symlink) — but `os.walk` still reports such an entry in
    `dirnames` (never `filenames`), so without collecting it here it would
    go neither write-probed nor escape-checked, and nothing behind it would
    ever be walked (the directory-symlink residual of the false-CLOSED bug
    class: a pre-existing symlinked subdir pointing at a genuinely-writable
    location elsewhere could exist while the entry still read `CLOSED`). A
    symlink that is itself classified as a file (points at a file, or is
    broken) still appears in `filenames` and is walked like any other file
    — the per-file symlink-escape case this module already caught.

    An explicit `onerror` callback is passed to `os.walk` (rather than
    relying on its default `onerror=None`, which silently drops the branch
    and simply omits its files — a fail-open-by-omission) so a mid-walk
    `scandir`/`listdir` failure is recorded in `errors` instead of vanishing."""

    files: list[Path] = []
    symlinked_dirs: list[Path] = []
    errors: list[str] = []

    def _onerror(exc: OSError) -> None:
        errors.append(str(exc))

    for dirpath, dirnames, filenames in os.walk(
        target, followlinks=False, onerror=_onerror
    ):
        dirpath_path = Path(dirpath)
        for name in dirnames:
            candidate = dirpath_path / name
            if candidate.is_symlink():
                symlinked_dirs.append(candidate)
        for name in filenames:
            files.append(dirpath_path / name)

    return _WalkOutcome(sorted(files), sorted(symlinked_dirs), errors)


def _collect_file_probes(
    entry_root: Path,
    agent_uid: int,
    agent_gid: int,
    write_probe: Callable[[Path, int, int], ProbeResult],
) -> list[FileProbe]:
    """Write-probe (via the same injectable `write_probe` edge) AND
    symlink-resolve/escape-check EVERY file actually present under
    `entry_root`; escape-check (but never write-probe, since it is never
    descended into) every symlinked SUBDIRECTORY `_walk_enforcement_files`
    reports; and turn any recorded walk error into a synthetic `PROBE_ERROR`
    `FileProbe`. Any probe error on any file, any escaping symlinked
    subdir, and any walk error is preserved verbatim (or synthesized) in a
    `FileProbe` — `verdict_for_path` is what maps these to `NOT_CLOSED`,
    this function only collects the raw evidence (fail-closed contract kept
    in exactly one place)."""

    file_probes: list[FileProbe] = []
    walk = _walk_enforcement_files(entry_root)

    for file_path in walk.files:
        escapes = target_escapes_subtree(file_path, entry_root)
        result = write_probe(file_path, agent_uid, agent_gid)
        file_probes.append(
            FileProbe(
                relpath=str(file_path.relative_to(entry_root)),
                write_result=result,
                escapes_subtree=escapes,
            )
        )

    # Residual gap 1 (directory-symlink variant of the false-CLOSED bug):
    # a symlinked subdir is never descended into, so it is never
    # write-probed here — but its resolved target IS escape-checked. One
    # that stays inside the ro subtree is fine (its real files are walked
    # via their actual, non-symlink path elsewhere in the tree); one that
    # escapes forces NOT_CLOSED via a synthetic escaping FileProbe (the
    # write_result itself is a placeholder WRITE_DENIED — it is the
    # escapes_subtree flag, checked unconditionally by verdict_for_path,
    # that carries the signal, never the placeholder write outcome).
    for dir_path in walk.symlinked_dirs:
        if target_escapes_subtree(dir_path, entry_root):
            file_probes.append(
                FileProbe(
                    relpath=str(dir_path.relative_to(entry_root)),
                    write_result=ProbeResult(
                        ProbeOutcome.WRITE_DENIED,
                        detail=(
                            "symlinked subdirectory, not descended into "
                            "(followlinks=False); escape-checked only"
                        ),
                    ),
                    escapes_subtree=True,
                )
            )

    # Residual gap 2 (fail-open-by-omission): a mid-walk scan error is
    # never a silent omission — it forces the whole entry to NOT_CLOSED via
    # a synthetic PROBE_ERROR FileProbe (outcome_forces_refuse handles the
    # rest, same as any other per-file PROBE_ERROR).
    for err in walk.errors:
        file_probes.append(
            FileProbe(
                relpath="<walk-error>",
                write_result=ProbeResult(ProbeOutcome.PROBE_ERROR, detail=err),
            )
        )

    return file_probes


# ---------------------------------------------------------------------------
# Orchestration: tie ENFORCEMENT_PATHS + the (injectable) thin edge + decide()
# together. This is the function the CLI (`__main__.py`) calls; its probe
# edges default to the real ones but are overridable so callers/tests can
# inject fakes, exactly as `sandbox.runtime.prepare_sandbox_run` does for
# `subprocess.run`.
# ---------------------------------------------------------------------------

def collect_path_probes(
    config_root: Path,
    agent_uid: int,
    agent_gid: int,
    *,
    key_path: Path | None,
    write_probe: Callable[[Path, int, int], ProbeResult] = probe_write_as_agent,
    read_probe: Callable[[Path, int, int], ProbeResult] = probe_read_key_as_agent,
) -> list[PathProbe]:
    """Walk `ENFORCEMENT_PATHS` under `config_root`, probing each with the
    (injectable) write/read edges, and return the `PathProbe` evidence list
    `decide()` consumes.

    A missing enforcement path is `PROBE_ERROR` (=> refuse) UNLESS its entry
    tolerates absence (only `plugins/**` does, per Trace). `os.access()` is
    never consulted here, and it never gates whether `write_probe`/
    `read_probe` run — both run unconditionally for every present path."""

    probes: list[PathProbe] = []
    for ep in ENFORCEMENT_PATHS:
        target = config_root / ep.relative
        if not target.exists():
            if ep.tolerate_absent:
                continue
            probes.append(
                PathProbe(
                    ep.label,
                    ep.posture,
                    ProbeResult(ProbeOutcome.PROBE_ERROR, detail="enforcement path missing"),
                )
            )
            continue

        escapes = target_escapes_subtree(target, config_root)
        write_result = write_probe(target, agent_uid, agent_gid)

        # BLOCKER-1 fix: the directory node's own probe (just above) only
        # covers whether a NEW entry can be created in it. For a directory
        # entry, ALSO walk and write-probe + escape-check every pre-existing
        # file actually present underneath — a "**" posture means recurse
        # fully. File-type entries (e.g. `stage-role-map.md`, `AGENTS.md`)
        # have no separate files to walk; `target` itself is what was just
        # probed above.
        file_probes: tuple[FileProbe, ...] = ()
        if target.is_dir():
            file_probes = tuple(
                _collect_file_probes(target, agent_uid, agent_gid, write_probe)
            )

        read_result: ProbeResult | None = None
        if ep.posture is Posture.RO_AND_UNREADABLE:
            if key_path is None or not key_path.exists():
                read_result = ProbeResult(ProbeOutcome.PROBE_ERROR, detail="key path absent")
            else:
                read_result = read_probe(key_path, agent_uid, agent_gid)

        probes.append(
            PathProbe(
                ep.label,
                ep.posture,
                write_result,
                escapes_subtree=escapes,
                read_result=read_result,
                file_probes=file_probes,
            )
        )
    return probes


def run_preflight(
    config_root: Path,
    agent_uid: int,
    agent_gid: int,
    *,
    override_ack: bool = False,
    requested_mode: RequestedMode = RequestedMode.UNCAGED,
    key_env_var: str = KEY_ENV_VAR,
    write_probe: Callable[[Path, int, int], ProbeResult] = probe_write_as_agent,
    read_probe: Callable[[Path, int, int], ProbeResult] = probe_read_key_as_agent,
) -> PreflightDecision:
    """The real top-level entrypoint the CLI calls: read the key's location
    from `key_env_var` (default `GLEIPNIR_MARKER_KEY_FILE`, unchanged —
    no marker code is modified), collect every enforcement path's evidence,
    and `decide()`."""

    key_path_str = os.environ.get(key_env_var)
    key_path = Path(key_path_str) if key_path_str else None
    key_state = check_key_state(key_path)

    path_probes = collect_path_probes(
        config_root,
        agent_uid,
        agent_gid,
        key_path=key_path,
        write_probe=write_probe,
        read_probe=read_probe,
    )
    return decide(
        path_probes,
        key_state,
        override_ack=override_ack,
        requested_mode=requested_mode,
    )
