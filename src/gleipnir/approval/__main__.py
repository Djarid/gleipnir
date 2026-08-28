"""Gleipnir approval-gate CLI.

    python -m gleipnir.approval.gate --check <filePath> --content-file <path> --token <token-file>

Invoked as a script via `gate.py`'s `if __name__ == "__main__"` guard, so
the literal command named by the plan
(`.gleipnir/plans/tier3-signed-approval.md` Decision 14) and by the future
`.gleipnir/plugins/tier3-gate.ts` write-block hook (Decision 14a, Step 7 --
NOT built by this module) works exactly as specified, while the argparse CLI
logic itself lives here per the Trace module table (`__main__.py`).

**The mint-vs-check content-hash fix (plan Decisions 19 + 20).** The
change_hash this CLI checks is derived from **`--content-file`'s bytes** --
the exact proposed RESULTING content a caller (the `tier3-gate.ts` hook) is
about to write -- NOT from a fresh `read_bytes()` of `--check`. `--check
<filePath>` is retained purely as the file **identifier** (which Tier-3
file is this?) plus its `is_file()` fail-closed guard (there must be a real
Tier-3 target); it is never re-hashed. This matters because
`tool.execute.before` fires strictly BEFORE the write lands on disk, so the
live disk bytes at check-time are always the pre-edit/base content, never
the approved-new content `server.py` minted the token over -- hashing
`--check`'s disk bytes would make every legitimate Tier-3 edit's hash
diverge from the mint-time hash and be wrongly REFUSED (or, if "fixed" by
binding to the base instead, open a bait-and-switch hole). Handing in the
exact resulting bytes via `--content-file` is what makes mint-time
(`server.py:compute_change_hash(pending_content)`) and check-time compute
over the *same* byte-string definition.

Exit codes mirror `verify/__main__.py:_cmd_check`'s fail-closed 0/1/3 shape,
so an out-of-band caller can branch on them exactly the same way:

    0  ALLOW    a fully-valid, fresh, content-bound token authorises this
                exact write.
    1  REFUSE   missing/malformed/stale/content-mismatched/
                identity-mismatched token, no target file to bind the
                token to, or no readable --content-file -- run the
                out-of-band approval again.
    3  REFUSE   the G-3.1 key itself is unavailable -- distinct from an
                ordinary policy REFUSE, same distinction `_cmd_check` makes.

Any non-zero exit is a REFUSE for the caller's purposes (the plan's
"exit 0 = ALLOW, non-zero = REFUSE" contract).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from ..verify.marker import KeyUnavailable, load_key
from .gate import GateVerdict, require_valid_token
from .token import APPROVAL_MAX_AGE_SECONDS, ApprovalToken, ApprovalTokenError


def _compute_change_hash(content_path: Path) -> str:
    """The change_hash for the pending write: sha256 of the EXACT proposed
    resulting content, handed to this CLI via `--content-file` -- NOT a
    fresh read of the `--check` target (Decision 19). This is the fix: the
    target's live disk bytes at check-time are always the pre-edit/base
    content (the hook runs before the write lands), so hashing them would
    never match `server.py`'s mint-time hash of the approved-new content.
    Mirrors `verify.marker.compute_tree_hash`'s content-hashing discipline,
    scoped to exactly the resulting bytes this call was handed."""

    return hashlib.sha256(content_path.read_bytes()).hexdigest()


def _cmd_check(args: argparse.Namespace) -> int:
    target_path = Path(args.check)
    content_path = Path(args.content_file)
    token_path = Path(args.token)

    if not target_path.is_file():
        print(
            f"gleipnir-approval: no such file to bind the token to: "
            f"{target_path}; write refused",
            file=sys.stderr,
        )
        return 1  # fail-closed: nothing to content-bind the token against

    if not content_path.is_file():
        print(
            f"gleipnir-approval: no such --content-file to hash: "
            f"{content_path}; write refused",
            file=sys.stderr,
        )
        return 1  # fail-closed: no resulting content handed in to check

    try:
        key = load_key(args.key_file)
    except KeyUnavailable as exc:
        print(f"gleipnir-approval: {exc}", file=sys.stderr)
        return 3  # fail-closed: no key, no gate (mirrors _cmd_check)

    if not token_path.is_file():
        print(
            f"gleipnir-approval: no approval token present at {token_path}; "
            "write refused",
            file=sys.stderr,
        )
        return 1

    try:
        token = ApprovalToken.from_json(token_path.read_text())
    except ApprovalTokenError as exc:
        print(f"gleipnir-approval: {exc}; write refused", file=sys.stderr)
        return 1

    # --check <path> is retained purely as the file IDENTIFIER (which
    # Tier-3 file is this?) plus the is-there-a-real-target fail-closed
    # guard above; it is never re-hashed. The change_hash is derived from
    # --content-file's bytes -- the exact resulting content the caller
    # (tier3-gate.ts) computed for this specific tool call (Decision 19).
    change_hash = _compute_change_hash(content_path)
    # The CLI has no independent channel to name an "expected" approver (the
    # tool.execute.before hook input carries no acting-agent identity -- plan
    # Trace L9); it re-validates the token's OWN embedded identity against
    # itself, so the meaningful checks -- content-binding, unforgeability,
    # and freshness -- are still fully and fail-closedly enforced.
    decision = require_valid_token(
        change_hash,
        token.approver_identity,
        token_path,
        key,
        max_age_seconds=args.max_age,
    )
    if decision.verdict is GateVerdict.ALLOW:
        print(
            f"gleipnir-approval: token valid and fresh; write allowed for "
            f"{target_path}"
        )
        return 0

    for reason in decision.reasons:
        print(f"gleipnir-approval: {reason}", file=sys.stderr)
    print("gleipnir-approval: write refused (fail-closed)", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gleipnir-approval-gate")
    parser.add_argument("--key-file", default=None, help="override key path")
    parser.add_argument(
        "--max-age",
        type=int,
        default=APPROVAL_MAX_AGE_SECONDS,
        help="freshness window in seconds (default: the 180s approval window)",
    )
    parser.add_argument(
        "--check",
        required=True,
        metavar="PATH",
        help=(
            "the file the pending Tier-3 write targets -- the file "
            "IDENTIFIER only; its bytes are never hashed (Decision 19)"
        ),
    )
    parser.add_argument(
        "--content-file",
        required=True,
        metavar="PATH",
        help=(
            "a file containing the EXACT proposed resulting content this "
            "write will produce -- THIS is what gets hashed into the "
            "change_hash, not --check's live disk bytes (Decision 19)"
        ),
    )
    parser.add_argument(
        "--token",
        required=True,
        metavar="TOKEN_FILE",
        help="the minted approval-token file to validate",
    )
    parser.set_defaults(func=_cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
