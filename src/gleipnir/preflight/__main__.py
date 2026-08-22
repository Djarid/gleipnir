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
    0  PROCEED_UNCLOSED   uncaged default (no --override-ack): legitimate
                          operator-trust posture, launch OK, neutral label
    1  REFUSE             boundary NOT closed; DO NOT launch. Includes a
                          `--mode caged` request that did not reach CLOSED.
    2  PROCEED_UNCLOSED   Part-0 override present (--override-ack); launch, but
                          the session is honestly labelled "G-1 NOT closed
                          (dev-mode)"

Posture selector (`--mode`, default `uncaged`):

    uncaged  legitimate operator-trust default; launch OK (exit 0) with a
             neutral label. The DEFAULT posture per `operating-posture.md`.
    caged    REQUIRE a CLOSED boundary; a caged request that is not CLOSED
             REFUSES (exit 1). The mode can NEVER manufacture CLOSED.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import advance
from . import bridge_recovery
from . import config_scan
from .boundary import RequestedMode, Verdict, run_preflight


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
    parser.add_argument(
        "--mode",
        choices=["uncaged", "caged"],
        default="uncaged",
        help=(
            "intended posture (D1). 'uncaged' (default): legitimate operator-trust "
            "posture, launch OK, neutral label. 'caged': REQUIRE a CLOSED boundary "
            "-- a caged request that is not CLOSED REFUSES (no false assurance). "
            "The mode can never manufacture CLOSED."
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

    if resolved_argv and resolved_argv[0] == "advance":
        # Phase 1 (`.gleipnir/plans/seam7-seam8-wiring.md`, Assemble Phase 1
        # step 1): the real advance entrypoint, mirroring the
        # `bridge-status`/`bridge-reset` leading-token dispatch above.
        # `advance.main` owns its own `--pipeline-id`/`--bridge-path`/
        # `--key-file`/`--log-root`/`--test-timeout` argparse instance.
        return advance.main(list(resolved_argv[1:]))

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

    requested_mode = RequestedMode(args.mode)
    decision = run_preflight(
        config_root,
        args.agent_uid,
        args.agent_gid,
        override_ack=args.override_ack,
        requested_mode=requested_mode,
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
        # Distinguish the legitimate uncaged default (non-failing, exit 0) from
        # the operator-acknowledged override (exit 2). A CAGED request never
        # reaches this branch as a "pass": caged-not-closed is REFUSE below.
        if requested_mode is RequestedMode.UNCAGED and not args.override_ack:
            return 0            # uncaged default: legitimate launch-OK posture
        return 2                # --override-ack: honest dev-mode escalation
    return 1                    # REFUSE (incl. caged-requested-but-not-closed)


if __name__ == "__main__":
    raise SystemExit(main())
