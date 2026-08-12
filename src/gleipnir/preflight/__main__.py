"""S-2/G-1 boundary preflight CLI (invoked by `bin/gleipnir-preflight`).

OUT-OF-FRAMEWORK entrypoint: run by the OPERATOR, as the OWNING uid, BEFORE
an opencode session starts — never by an in-framework agent. See
`.gleipnir/plans/s2-g1-closure-first-slice.md` Trace "the preflight as an
out-of-framework wrapper" for why this must not be agent-reachable (a guard
whose activation is validated by the population it guards is the G-3
forgeable-evidence failure applied to activation).

This module is deliberately NOT referenced by any `.gleipnir/agents/*.md`
permission map — that omission is the point, not an oversight.

Exit codes (fail-closed; distinct codes so the launch wrapper can branch):

    0  CLOSED             boundary holds; launch OK
    1  REFUSE             boundary NOT closed and no override; DO NOT launch
    2  PROCEED_UNCLOSED   Part-0 override present; launch, but the session is
                          honestly labelled "G-1 NOT closed (dev-mode)"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import bridge_recovery
from . import config_scan
from .boundary import Verdict, run_preflight


def _repo_root() -> Path:
    # src/gleipnir/preflight/__main__.py -> repo root is three parents up.
    return Path(__file__).resolve().parents[3]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gleipnir-preflight")
    parser.add_argument(
        "--config-root",
        default=None,
        help="OPENCODE_CONFIG_DIR to probe (default: <repo>/.gleipnir)",
    )
    parser.add_argument(
        "--agent-uid",
        type=int,
        required=True,
        help="the in-framework agent's OS uid to drop to for the behavioural probe",
    )
    parser.add_argument(
        "--agent-gid",
        type=int,
        required=True,
        help="the in-framework agent's OS gid to drop to for the behavioural probe",
    )
    parser.add_argument(
        "--override-ack",
        action="store_true",
        help=(
            "Part-0 operator-acknowledged dev-mode override: escalates a "
            "NOT-closed boundary to PROCEED_UNCLOSED with an honest label; "
            "can NEVER produce CLOSED"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch on a leading `config-scan` subcommand token; otherwise fall
    through to the original flat boundary-preflight invocation UNCHANGED
    (exact backward compatibility for `bin/gleipnir-preflight`'s existing
    `--agent-uid`/`--agent-gid`/`--config-root`/`--override-ack` form, which
    predates this subcommand and has no leading positional of its own).

    `config-scan` is a mode/subcommand on this SAME out-of-framework CLI
    (Link-time decision, `.gleipnir/plans/config-scoping-preflight.md`), not
    a second binary -- sharing the fail-closed 0/1/2 exit-code convention.
    Everything after `config-scan` is passed straight through to
    `config_scan.config_scan_main`, which owns its own `--strict`/
    `--override-ack` flags independently of the boundary parser's.
    """

    resolved_argv = sys.argv[1:] if argv is None else argv

    if resolved_argv and resolved_argv[0] == "bridge-status":
        return bridge_recovery.bridge_status_main(list(resolved_argv[1:]))

    if resolved_argv and resolved_argv[0] == "bridge-reset":
        return bridge_recovery.bridge_reset_main(list(resolved_argv[1:]))

    if resolved_argv and resolved_argv[0] == "config-scan":
        config_root = None
        # Support a shared `--config-root` in front of/after the
        # subcommand token, mirroring the boundary parser's own flag, for
        # operator convenience -- but config_scan_main's own argparse
        # instance owns --strict/--override-ack.
        rest = list(resolved_argv[1:])
        if "--config-root" in rest:
            idx = rest.index("--config-root")
            config_root = Path(rest[idx + 1])
            del rest[idx:idx + 2]
        return config_scan.config_scan_main(rest, config_root=config_root)

    args = build_parser().parse_args(resolved_argv)
    config_root = (
        Path(args.config_root) if args.config_root else _repo_root() / ".gleipnir"
    )

    decision = run_preflight(
        config_root,
        args.agent_uid,
        args.agent_gid,
        override_ack=args.override_ack,
    )

    print(
        f"gleipnir-preflight: {decision.verdict.value} -- {decision.label}",
        file=sys.stderr,
    )
    for reason in decision.reasons:
        print(f"  - {reason}", file=sys.stderr)

    if decision.verdict is Verdict.CLOSED:
        return 0
    if decision.verdict is Verdict.PROCEED_UNCLOSED:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
