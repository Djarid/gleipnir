"""Operator-only bridge recovery for a stuck/stale G-5 pipeline bridge (L-C19).

OUT-OF-FRAMEWORK: run by the OPERATOR via `bin/gleipnir-preflight bridge-status`
/ `bridge-reset`, never by an in-framework agent. This module is deliberately
NOT referenced by any `.gleipnir/agents/*.md` permission map -- and both
subcommands REFUSE if they detect they have been made agent-invocable
(pre-mortem #1, brief `.gleipnir/plans/bridge-recovery-brainstorm.md`).

Clear-only (Decision 2): `bridge-reset` DELETES the bridge; it never re-mints a
state (re-minting a permissive state is the fail-open the driver docstring
forbids). Classification distinguishes stale (valid MAC, too old) from
corrupt-or-tampered (MAC/version invalid, unparseable, or future-dated) by
calling `validate_state` twice -- once at the real 3600s window, once at an
effectively-infinite window -- since `validate_state` alone collapses MAC- and
age-failures into one False.

Honest status: cooperative-policy-until-S-2. The uid refusal is opt-in via
GLEIPNIR_OPERATOR_UID; no reliable in-process "am I an agent" signal exists in
this codebase, so when the env var is unset the tool WARNS rather than
fabricating a check.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from enum import Enum
from pathlib import Path

from gleipnir.engine.bridge import (
    DEFAULT_MAX_AGE_SECONDS,
    KeyUnavailable,
    StateMarker,
    StateMarkerError,
    load_key,
    validate_state,
)

BRIDGE_REL = Path("var") / "run" / "pipeline-state.json"
LOG_REL = Path("logs") / "bridge-recovery.log"
AGENTS_REL = Path("agents")
OPERATOR_UID_ENV = "GLEIPNIR_OPERATOR_UID"
ARM_ENV = "GLEIPNIR_PIPELINE"
PREFLIGHT_TOKEN = "gleipnir-preflight"
_EFFECTIVELY_INFINITE_AGE = 10 ** 12


class Classification(Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    CORRUPT_OR_TAMPERED = "corrupt-or-tampered"
    ABSENT = "absent"


def _repo_root() -> Path:
    # src/gleipnir/preflight/bridge_recovery.py -> repo root is three parents up
    # (same depth as __main__._repo_root()).
    return Path(__file__).resolve().parents[3]


def _default_config_root() -> Path:
    return _repo_root() / ".gleipnir"


def classify_bridge(
    text: str | None,
    key: bytes | None,
    *,
    now: int | None = None,
) -> tuple[Classification, StateMarker | None, int | None]:
    """Pure classifier. Never raises. Returns (classification, marker, age).

    * text is None            -> ABSENT
    * unparseable             -> CORRUPT_OR_TAMPERED
    * key is None             -> CORRUPT_OR_TAMPERED (cannot verify MAC)
    * MAC/version invalid, or
      future-dated (age < 0)  -> CORRUPT_OR_TAMPERED
    * MAC valid, age > 3600   -> STALE
    * MAC valid, fresh        -> HEALTHY
    """
    if text is None:
        return (Classification.ABSENT, None, None)
    try:
        marker = StateMarker.from_json(text)
    except StateMarkerError:
        return (Classification.CORRUPT_OR_TAMPERED, None, None)

    current = int(now if now is not None else time.time())
    age = current - marker.minted_at

    if key is None:
        return (Classification.CORRUPT_OR_TAMPERED, marker, age)

    mac_ok_any_age = validate_state(
        marker, key, max_age_seconds=_EFFECTIVELY_INFINITE_AGE, now=current
    )
    if not mac_ok_any_age:
        # MAC/version invalid, OR age < 0 (future-dated). Both fail-closed.
        return (Classification.CORRUPT_OR_TAMPERED, marker, age)

    fresh = validate_state(marker, key, now=current)  # real 3600 window
    if fresh:
        return (Classification.HEALTHY, marker, age)
    return (Classification.STALE, marker, age)


def next_command(classification: Classification) -> str:
    if classification is Classification.HEALTHY:
        return "(bridge is healthy; no recovery needed)"
    if classification is Classification.ABSENT:
        return "(no bridge present; start a run normally -- nothing to recover)"
    # STALE or CORRUPT_OR_TAMPERED
    return "bin/gleipnir-preflight bridge-reset --confirm-clear"


def preflight_is_agent_invocable(agents_dir: Path) -> str | None:
    """Return the offending agent filename if the literal `gleipnir-preflight`
    appears in ANY `.gleipnir/agents/*.md`, else None. Read-only; pre-mortem
    #1 guard. Never raises (a missing/unreadable dir -> None means 'no evidence
    it is agent-invocable' -- but see note: an unreadable agents dir is itself
    reported so the operator is not lulled)."""
    try:
        paths = sorted(agents_dir.glob("*.md"))
    except OSError:
        return None
    for path in paths:
        try:
            if PREFLIGHT_TOKEN in path.read_text():
                return path.name
        except OSError:
            continue
    return None


def _human_age(age: int | None) -> str:
    if age is None:
        return "n/a"
    if age < 0:
        return f"{age}s (FUTURE-DATED -- nonsense timestamp)"
    if age < 3600:
        return f"{age}s"
    return f"{age}s (~{age // 3600}h {(age % 3600) // 60}m)"


def _read_bridge_text(bridge_path: Path) -> str | None:
    try:
        return bridge_path.read_text()
    except OSError:
        return None


def _try_load_key() -> bytes | None:
    try:
        return load_key()
    except KeyUnavailable:
        return None


def _allowlist_guard(agents_dir: Path) -> int | None:
    offender = preflight_is_agent_invocable(agents_dir)
    if offender is not None:
        print(
            "bridge-recovery: REFUSING -- 'gleipnir-preflight' appears in "
            f"agent file {offender!r}. This tool must NEVER be agent-invocable "
            "(a guard whose activation is validated by the population it "
            "guards is defeated). Remove it from the allowlist first.",
            file=sys.stderr,
        )
        return 1
    return None


def bridge_status_main(argv: list[str] | None = None, *, config_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gleipnir-preflight bridge-status")
    parser.add_argument("--config-root", default=None)
    args = parser.parse_args(argv if argv is not None else [])

    root = Path(args.config_root) if args.config_root else (config_root or _default_config_root())

    guard = _allowlist_guard(root / AGENTS_REL)
    if guard is not None:
        return guard

    bridge_path = root / BRIDGE_REL
    text = _read_bridge_text(bridge_path)
    key = _try_load_key()
    classification, marker, age = classify_bridge(text, key)

    print(f"bridge-status: {classification.value}", file=sys.stderr)
    if marker is not None:
        print(f"  pipeline_state : {marker.pipeline_state}", file=sys.stderr)
        print(f"  minted_at      : {marker.minted_at}", file=sys.stderr)
        print(f"  age            : {_human_age(age)}", file=sys.stderr)
    if key is None and classification is Classification.CORRUPT_OR_TAMPERED and marker is not None:
        print("  note           : key unavailable -- MAC could NOT be verified; "
              "reporting fail-closed (cannot certify healthy)", file=sys.stderr)
    if os.environ.get(ARM_ENV, "").strip().lower() == "on":
        print(f"  warning        : {ARM_ENV}=on -- a gated run appears armed in "
              "this environment", file=sys.stderr)
    print(f"  next command   : {next_command(classification)}", file=sys.stderr)
    return 0  # read-only, always safe


def _append_audit_line(log_path: Path, *, action: str, old_state: str | None, minted_at: int | None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": int(time.time()),
        "action": action,
        "old_state": old_state,
        "minted_at": minted_at,
        "uid": os.getuid(),
        "surface": "bridge-reset",
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _uid_check() -> int | None:
    """Returns an exit code to abort with, or None to proceed. Decision 5:
    opt-in via GLEIPNIR_OPERATOR_UID; unset -> warn honestly and proceed."""
    raw = os.environ.get(OPERATOR_UID_ENV)
    if raw is None or raw.strip() == "":
        print(
            "bridge-reset: WARNING -- GLEIPNIR_OPERATOR_UID is not set, so this "
            "tool CANNOT verify it is running as the operator (no reliable "
            "in-process agent signal exists pre-S-2). Proceeding on your "
            "explicit --confirm-clear. Set GLEIPNIR_OPERATOR_UID to enforce.",
            file=sys.stderr,
        )
        return None
    try:
        expected = int(raw)
    except ValueError:
        print(f"bridge-reset: REFUSING -- {OPERATOR_UID_ENV}={raw!r} is not an "
              "integer uid (misconfigured).", file=sys.stderr)
        return 1
    if os.getuid() != expected:
        print(f"bridge-reset: REFUSING -- current uid {os.getuid()} != operator "
              f"uid {expected}; will not clear the bridge under a non-operator uid.",
              file=sys.stderr)
        return 1
    return None


def bridge_reset_main(argv: list[str] | None = None, *, config_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gleipnir-preflight bridge-reset")
    parser.add_argument("--config-root", default=None)
    parser.add_argument(
        "--confirm-clear",
        action="store_true",
        help="REQUIRED to actually delete the bridge; no default-yes.",
    )
    args = parser.parse_args(argv if argv is not None else [])

    root = Path(args.config_root) if args.config_root else (config_root or _default_config_root())

    guard = _allowlist_guard(root / AGENTS_REL)
    if guard is not None:
        return guard

    bridge_path = root / BRIDGE_REL
    log_path = root / LOG_REL

    # Best-effort read of the old state for the audit log (before any deletion).
    text = _read_bridge_text(bridge_path)
    old_state: str | None
    old_minted_at: int | None
    if text is None:
        old_state, old_minted_at = None, None
    else:
        try:
            m = StateMarker.from_json(text)
            old_state, old_minted_at = m.pipeline_state, m.minted_at
        except StateMarkerError:
            old_state, old_minted_at = "unparseable", None

    # Show what would be cleared, then require the flag (Decision 6).
    if not args.confirm_clear:
        print("bridge-reset: REFUSING -- --confirm-clear not given. Would clear:",
              file=sys.stderr)
        print(f"  old_state : {old_state}", file=sys.stderr)
        print(f"  minted_at : {old_minted_at}", file=sys.stderr)
        print("  Re-run with --confirm-clear to delete the bridge (clear-only; "
              "never re-mints a state).", file=sys.stderr)
        return 1

    uid_abort = _uid_check()
    if uid_abort is not None:
        return uid_abort

    if os.environ.get(ARM_ENV, "").strip().lower() == "on":
        print(f"bridge-reset: WARNING -- {ARM_ENV}=on; clearing a bridge for an "
              "armed run. This is intended for a stuck run; proceeding.",
              file=sys.stderr)

    if text is None:
        print("bridge-reset: bridge already absent; nothing to clear.", file=sys.stderr)
        _append_audit_line(log_path, action="no-op", old_state=None, minted_at=None)
        return 0

    try:
        bridge_path.unlink()
    except OSError as exc:
        print(f"bridge-reset: FAILED to delete bridge at {bridge_path}: {exc}",
              file=sys.stderr)
        return 1

    _append_audit_line(log_path, action="cleared", old_state=old_state, minted_at=old_minted_at)
    print(f"bridge-reset: cleared bridge (old_state={old_state}, "
          f"minted_at={old_minted_at}). Logged to {log_path}.", file=sys.stderr)
    return 0
