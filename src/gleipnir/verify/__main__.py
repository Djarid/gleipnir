"""Gleipnir G-3.1 verifier CLI.

Two subcommands, mirroring the two sides of the marker:

    verify  --root . --marker .gleipnir/.tmp/marker.json -- <test command...>
        Run the test command. On a green exit code, compute the tree hash and
        mint a signed marker. This is the ONLY path that produces a valid
        marker, and it requires the key. A red test run mints nothing.

    check   --root . --marker .gleipnir/.tmp/marker.json
        Validate an existing marker against the current tree. Exit 0 if the
        marker is genuine, fresh and tree-bound; non-zero otherwise. A non-zero
        exit means "run the tests" (fail-closed). Missing marker => non-zero.

The key is read from GLEIPNIR_MARKER_KEY_FILE. The agent never holds it; only
the verifier process (running this CLI outside the agent surface) does.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .marker import (
    KeyUnavailable,
    Marker,
    MarkerError,
    compute_tree_hash,
    load_key,
    mint,
    validate,
)


def _cmd_verify(args: argparse.Namespace) -> int:
    if not args.command:
        print("gleipnir-verify: no test command given", file=sys.stderr)
        return 2
    try:
        key = load_key(args.key_file)
    except KeyUnavailable as exc:
        print(f"gleipnir-verify: {exc}", file=sys.stderr)
        return 3  # fail-closed: no key, no marker

    result = subprocess.run(args.command)
    if result.returncode != 0:
        print(
            f"gleipnir-verify: tests failed (exit {result.returncode}); "
            "no marker minted",
            file=sys.stderr,
        )
        return result.returncode

    tree_hash = compute_tree_hash(
        args.root, include=args.include, extra_files=args.extra_file
    )
    marker = mint(tree_hash, key)
    marker_path = Path(args.marker)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(marker.to_json())
    print(f"gleipnir-verify: tests green; marker minted at {marker_path}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    marker_path = Path(args.marker)
    if not marker_path.is_file():
        print("gleipnir-verify: no marker present; run the tests", file=sys.stderr)
        return 1  # fail-closed
    try:
        key = load_key(args.key_file)
    except KeyUnavailable as exc:
        print(f"gleipnir-verify: {exc}", file=sys.stderr)
        return 3

    try:
        marker = Marker.from_json(marker_path.read_text())
    except MarkerError as exc:
        print(f"gleipnir-verify: {exc}; run the tests", file=sys.stderr)
        return 1

    current = compute_tree_hash(
        args.root, include=args.include, extra_files=args.extra_file
    )
    if validate(marker, current, key, max_age_seconds=args.max_age):
        print("gleipnir-verify: marker valid; safe to skip re-running tests")
        return 0
    print("gleipnir-verify: marker invalid or stale; run the tests", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gleipnir-verify")
    parser.add_argument("--key-file", default=None, help="override key path")
    parser.add_argument("--root", default=".", help="tree root to hash")
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        help="dir/file to include in the tree hash (repeatable; default src,tests)",
    )
    parser.add_argument(
        "--extra-file",
        action="append",
        default=[],
        help="extra file to fold into the tree hash (repeatable)",
    )
    parser.add_argument(
        "--marker",
        default=".gleipnir/.tmp/marker.json",
        help="marker file path",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_verify = sub.add_parser("verify", help="run tests then mint on green")
    p_verify.add_argument("command", nargs=argparse.REMAINDER)
    p_verify.set_defaults(func=_cmd_verify)

    p_check = sub.add_parser("check", help="validate an existing marker")
    p_check.add_argument("--max-age", type=int, default=3600)
    p_check.set_defaults(func=_cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.include is None:
        args.include = ["src", "tests"]
    # verify subcommand: strip a leading "--" separator from REMAINDER
    if getattr(args, "command", None) and args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not hasattr(args, "max_age"):
        args.max_age = 3600
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
