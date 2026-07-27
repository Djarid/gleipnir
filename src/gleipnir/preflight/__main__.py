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
    args = build_parser().parse_args(argv)
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
