"""Config-scoping preflight — the accepted-YAML-subset + JSONC parse layer.

Spec: `.gleipnir/plans/config-scoping-preflight.md` ("The accepted-YAML-subset
grammar (Option A)" + "Design Consolidation" -> "The consolidated public API").
This module mirrors `boundary.py`'s shape: pure, fully-unit-testable core
functions returning discriminated outcomes, fail-closed on any ambiguity, no
silent defaults.

**THIS FILE IS PART 1 OF 6 (types + parse-foundation layer only).** It
implements exactly: `UnparseableKind`, `Unparseable`, `extract_frontmatter`,
`parse_frontmatter`, `parse_jsonc`. Everything else the consolidated API names
(`FindingCheck`, `FindingSeverity`, `Finding`, `ConfigVerdict`,
`ConfigDecision`, `check_grammar`, `enumerate_effective_tools`,
`assert_single_holders`, `check_fail_open`, `check_global_disable`,
`find_mis_scoped_denies`, `decide_config`, `read_agent_files`, `read_jsonc`,
`config_scan_main`, and the `DEFAULT_*` constants) is deliberately NOT here
yet — later delegated parts add them.

**Why a hand-rolled reader and not PyYAML (Option A).** The stdlib has no YAML
support (only `json`/`tomllib`); this module is the enforcement core, which is
stdlib-only by policy (`.gleipnir/decisions/runtime-and-deps.md`). Rather than
add a third-party dependency to a security-boundary tool, the reader accepts
ONLY the narrow grammar subset the 9 live agent files actually use, and fails
CLOSED (`OUT_OF_SUBSET_YAML`) on anything outside it — never guesses, never
silently degrades to "best effort". A stricter reader is the safer choice: it
can never silently accept a construct it was never validated against.

**The interleaved-comment pre-pass (ST-12).** Comment lines (first non-space
char `#`, at ANY indent) and blank lines are stripped in a PRE-PASS, before
any indent-based structural walking. Real files (`git-ops.md:23-30`,
`gleipnir-brainstorm.md:16-19`) have comment lines sitting between two
sibling children of a nested map; if the structural walker saw the raw `#
...` line it would try to read it as a malformed key and wrongly emit
`OUT_OF_SUBSET_YAML` on genuinely valid config — a false REFUSE on good
config. Stripping first makes the interleaved comment invisible to the
walker.

**Depth cap.** Map nesting is capped at depth 2: top-level key -> child map ->
grandchild SCALAR (e.g. `permission.bash."*"`). A third level of map nesting
is out of subset and fails closed — this keeps the "scoped to what the files
contain" claim honest rather than silently accepting an unvalidated deeper
structure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "UnparseableKind",
    "Unparseable",
    "extract_frontmatter",
    "parse_frontmatter",
    "parse_jsonc",
    "FindingCheck",
    "FindingSeverity",
    "Finding",
    "check_grammar",
    "enumerate_effective_tools",
    "assert_single_holders",
    "check_fail_open",
    "check_global_disable",
    "find_mis_scoped_denies",
    "ConfigVerdict",
    "DEV_MODE_LABEL_CONFIG",
    "ConfigDecision",
    "decide_config",
    "DEFAULT_MCP_NAMESPACES",
    "DEFAULT_HOLDER_MAP",
    "DEFAULT_MCP_SERVER_BASE_NAMES",
    "read_agent_files",
    "read_jsonc",
    "config_scan_main",
]


# ---------------------------------------------------------------------------
# The discriminated "could not parse" outcome — mirrors boundary.py's
# ProbeOutcome/ProbeResult shape. `INVALID_JSONC` and `READ_ERROR` are not
# produced by this part's functions yet (parse_jsonc produces INVALID_JSONC;
# READ_ERROR is a thin-edge-only outcome for a later part) but the full enum
# is declared now since later parts and the test suite reference it by name.
# ---------------------------------------------------------------------------

class UnparseableKind(Enum):
    NO_FRONTMATTER = "no_frontmatter"
    UNTERMINATED_FENCE = "unterminated_fence"
    OUT_OF_SUBSET_YAML = "out_of_subset_yaml"
    INVALID_JSONC = "invalid_jsonc"
    READ_ERROR = "read_error"


@dataclass(frozen=True)
class Unparseable:
    """A discriminated "could not parse" outcome. `where` and `detail`
    together always carry SOME non-empty diagnostic — a fail-closed security
    tool never fails silently/unexplained."""

    kind: UnparseableKind
    where: str
    detail: str = ""


# ---------------------------------------------------------------------------
# extract_frontmatter — fence isolation.
# ---------------------------------------------------------------------------

def extract_frontmatter(text: str) -> str | Unparseable:
    """Isolate the `---`-delimited YAML block at the top of an agent `.md`
    file's raw text. The opening fence must be the file's very first line
    (a "leading" fence, per grammar item 1) -- a `---` appearing later in a
    file whose first line is not itself `---` does not count. A missing
    leading fence -> `Unparseable(NO_FRONTMATTER)`; a leading fence with no
    subsequent closing `---` line -> `Unparseable(UNTERMINATED_FENCE)`.
    """

    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return Unparseable(
            UnparseableKind.NO_FRONTMATTER,
            where="<file start>",
            detail="no leading '---' frontmatter fence found",
        )

    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return Unparseable(
            UnparseableKind.UNTERMINATED_FENCE,
            where="<frontmatter>",
            detail="opening '---' fence found but no closing '---' fence",
        )

    block_lines = lines[1:closing_idx]
    return "\n".join(block_lines) + ("\n" if block_lines else "")


# ---------------------------------------------------------------------------
# parse_frontmatter — the accepted-subset reader.
# ---------------------------------------------------------------------------

class _SubsetError(Exception):
    """Internal signal: some construct fell outside the accepted subset.
    Always caught at the `parse_frontmatter` boundary and mapped to
    `Unparseable(OUT_OF_SUBSET_YAML)` -- never allowed to propagate, and
    never mapped to a silent "pass"."""

    def __init__(self, detail: str, where: str = ""):
        super().__init__(detail)
        self.detail = detail
        self.where = where


def _leading_ws(line: str) -> str:
    """The leading run of space/tab characters (tabs included deliberately,
    so tab-indentation can be detected instead of silently miscounted)."""

    i = 0
    while i < len(line) and line[i] in (" ", "\t"):
        i += 1
    return line[:i]


def _leading_spaces(line: str) -> int:
    """Count of leading SPACE characters. Only ever called on lines already
    verified tab-free by `_prepass_strip`, so counting spaces alone is a
    safe, unambiguous indent measure at this point."""

    return len(line) - len(line.lstrip(" "))


def _prepass_strip(block: str) -> list[str]:
    """ST-12: strip comment lines (first non-space-or-tab char `#`, at ANY
    indent) and blank lines, BEFORE any indent-based structural walking.
    Also the single place tab-indentation is detected and fails closed
    (raised as `_SubsetError`) -- every surviving line is guaranteed
    tab-free, so downstream indent arithmetic can safely count spaces only.
    """

    kept: list[str] = []
    for i, line in enumerate(block.split("\n")):
        if line.strip() == "":
            continue
        leading = _leading_ws(line)
        content = line[len(leading):]
        if content.startswith("#"):
            continue
        if "\t" in leading:
            raise _SubsetError(
                "tab character used for indentation", where=f"line {i}"
            )
        kept.append(line)
    return kept


_INT_RE = re.compile(r"[+-]?\d+")
_FLOAT_RE = re.compile(r"[+-]?\d+\.\d+")


def _parse_scalar_value(value: str, where: str) -> object:
    """Parse ONE inline scalar value per grammar item 3: bareword string,
    int, float, bool, or double-quoted string. Every explicitly-out-of-subset
    construct (flow mapping/sequence, anchor, alias, tag, single-quoted
    string, block-literal `|`) is rejected here, fail-closed."""

    if value == "":
        raise _SubsetError("empty scalar value", where=where)
    if value.startswith('"'):
        if len(value) < 2 or not value.endswith('"'):
            raise _SubsetError(f"malformed double-quoted value {value!r}", where=where)
        inner = value[1:-1]
        if '"' in inner:
            raise _SubsetError(
                f"embedded quote in double-quoted value not in subset: {value!r}",
                where=where,
            )
        return inner
    if value.startswith("'"):
        raise _SubsetError(
            f"single-quoted string not in accepted subset: {value!r}", where=where
        )
    if value.startswith("{") or value.startswith("["):
        raise _SubsetError(
            f"flow mapping/sequence not in accepted subset: {value!r}", where=where
        )
    if value.startswith("&"):
        raise _SubsetError(
            f"YAML anchor not in accepted subset: {value!r}", where=where
        )
    if value.startswith("*"):
        raise _SubsetError(
            f"YAML alias reference not in accepted subset: {value!r}", where=where
        )
    if value.startswith("!"):
        raise _SubsetError(f"YAML tag not in accepted subset: {value!r}", where=where)
    if value.startswith("|"):
        raise _SubsetError(
            f"block literal style ('|') not in accepted subset: {value!r}",
            where=where,
        )
    if value in ("true", "True", "TRUE"):
        return True
    if value in ("false", "False", "FALSE"):
        return False
    if _INT_RE.fullmatch(value):
        return int(value)
    if _FLOAT_RE.fullmatch(value):
        return float(value)
    # Bareword string fallback -- e.g. allow/deny/ask/subagent/primary.
    return value


def _split_key_value(content: str, where: str) -> tuple[str, str]:
    """Split one dedented line into (key, inline-value-string). Handles both
    double-quoted keys (glob patterns) and unquoted bareword keys."""

    if content.startswith('"'):
        end = content.find('"', 1)
        if end == -1:
            raise _SubsetError(f"unterminated quoted key in {content!r}", where=where)
        key = content[1:end]
        remainder = content[end + 1:]
        if not remainder.startswith(":"):
            raise _SubsetError(
                f"expected ':' immediately after quoted key {key!r}", where=where
            )
        value = remainder[1:].strip()
        return key, value

    if ":" not in content:
        raise _SubsetError(
            f"line has no ':' -- not a recognizable key: value pair: {content!r}",
            where=where,
        )
    key, _, value = content.partition(":")
    key = key.strip()
    value = value.strip()
    if not key:
        raise _SubsetError(f"empty key in {content!r}", where=where)
    return key, value


def _parse_list_block(lines: list[str], idx: int, indent: int) -> tuple[list[str], int]:
    """Parse a YAML list block: sibling `- "..."` items at exactly `indent`.
    Only double-quoted string items are in subset (grammar item 6)."""

    items: list[str] = []
    n = len(lines)
    while idx < n:
        line = lines[idx]
        cur_indent = _leading_spaces(line)
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise _SubsetError(
                "unexpected indent increase inside list block", where=f"line {idx}"
            )
        content = line[indent:].rstrip()
        if not content.startswith("- "):
            break
        item_str = content[2:].strip()
        if not (item_str.startswith('"') and item_str.endswith('"') and len(item_str) >= 2):
            raise _SubsetError(
                f"list item is not a double-quoted string: {item_str!r}",
                where=f"line {idx}",
            )
        inner = item_str[1:-1]
        if '"' in inner:
            raise _SubsetError(
                f"embedded quote in list item not in subset: {item_str!r}",
                where=f"line {idx}",
            )
        items.append(inner)
        idx += 1
    return items, idx


def _parse_block_scalar(lines: list[str], idx: int, indent: int) -> tuple[str, int]:
    """Parse a folded block scalar's (`>-`) continuation lines: every line
    more-indented than `indent`, joined with a single space, terminated by
    the first line dedented back to <= `indent` (a sibling key) or EOF.
    Content is captured opaque -- never grammar-checked, it is prose."""

    n = len(lines)
    collected: list[str] = []
    block_indent: int | None = None
    while idx < n:
        line = lines[idx]
        cur_indent = _leading_spaces(line)
        if cur_indent <= indent:
            break
        if block_indent is None:
            block_indent = cur_indent
        collected.append(line[block_indent:].rstrip())
        idx += 1
    return " ".join(collected), idx


def _parse_map_body(
    lines: list[str], idx: int, indent: int, depth: int
) -> tuple[dict, int]:
    """Parse zero or more sibling `key: value` entries all at exactly
    `indent` spaces, starting at `lines[idx]`. `depth` is the nesting level
    of THIS map itself (0 = the top-level frontmatter map, 1 = a map that is
    the value of a top-level key, 2 = a map that is the value of a depth-1
    map's key -- the maximum accepted; its children must be scalars only).
    Returns the parsed dict and the index of the first line NOT consumed
    (either a dedent below `indent`, or EOF)."""

    result: dict = {}
    n = len(lines)
    while idx < n:
        line = lines[idx]
        cur_indent = _leading_spaces(line)
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise _SubsetError(
                "unexpected indent increase without a parent key",
                where=f"line {idx}",
            )

        content = line[indent:].rstrip()
        if content.startswith("- "):
            raise _SubsetError(
                "list item found where a mapping key was expected",
                where=f"line {idx}",
            )

        key, value = _split_key_value(content, where=f"line {idx}")

        if value == "":
            # No inline value: a nested map, or a list block. Look ahead at
            # the next line to decide which (or fail if there is nothing
            # indented beneath it at all -- an ambiguous "key with nothing
            # under it" is never guessed).
            next_idx = idx + 1
            if next_idx >= n:
                raise _SubsetError(
                    f"key {key!r} has no inline value and no children",
                    where=f"line {idx}",
                )
            child_line = lines[next_idx]
            child_indent = _leading_spaces(child_line)
            if child_indent <= indent:
                raise _SubsetError(
                    f"key {key!r} has no inline value and no indented children",
                    where=f"line {idx}",
                )
            child_content = child_line[child_indent:].rstrip()
            if child_content.startswith("- "):
                items, idx = _parse_list_block(lines, next_idx, child_indent)
                result[key] = items
                continue
            if depth + 1 > 2:
                raise _SubsetError(
                    f"nesting exceeds the depth-2 cap at key {key!r}",
                    where=f"line {idx}",
                )
            child_map, idx = _parse_map_body(lines, next_idx, child_indent, depth + 1)
            result[key] = child_map
            continue

        if value in (">-", ">"):
            text, idx = _parse_block_scalar(lines, idx + 1, indent)
            result[key] = text
            continue

        result[key] = _parse_scalar_value(value, where=f"line {idx}")
        idx += 1

    return result, idx


def parse_frontmatter(block: str) -> dict | Unparseable:
    """Hand-rolled reader for EXACTLY the accepted YAML subset (plan Trace
    "The accepted-YAML-subset grammar", items 1-6). Any construct outside
    that subset -> `Unparseable(OUT_OF_SUBSET_YAML)`, fail-closed -- when in
    doubt, this function refuses rather than guesses."""

    try:
        lines = _prepass_strip(block)
    except _SubsetError as exc:
        return Unparseable(UnparseableKind.OUT_OF_SUBSET_YAML, where=exc.where, detail=exc.detail)

    try:
        parsed, idx = _parse_map_body(lines, 0, indent=0, depth=0)
    except _SubsetError as exc:
        return Unparseable(UnparseableKind.OUT_OF_SUBSET_YAML, where=exc.where, detail=exc.detail)

    if idx != len(lines):
        return Unparseable(
            UnparseableKind.OUT_OF_SUBSET_YAML,
            where=f"line {idx}",
            detail="trailing content the parser could not consume as a sibling key",
        )

    return parsed


# ---------------------------------------------------------------------------
# parse_jsonc — comment-strip + stdlib json.loads.
# ---------------------------------------------------------------------------

def _strip_jsonc_comments(text: str) -> str:
    """Strip `//` line comments and `/* */` block comments, WITHOUT
    disturbing `//` occurring inside a JSON string literal (e.g.
    `"https://opencode.ai/..."`). A small state machine tracks whether the
    scanner is currently inside a string (respecting backslash-escapes), and
    only recognises comment-openers outside of one."""

    result: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        c = text[i]

        if in_string:
            result.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue

        if c == '"':
            in_string = True
            result.append(c)
            i += 1
            continue

        if c == "/" and i + 1 < n and text[i + 1] == "/":
            nl = text.find("\n", i)
            if nl == -1:
                break
            result.append("\n")
            i = nl + 1
            continue

        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                # Unterminated block comment -- stop stripping here; the
                # subsequent json.loads will (correctly) fail closed on the
                # truncated/invalid result rather than this function
                # guessing at intent.
                break
            i = end + 2
            continue

        result.append(c)
        i += 1

    return "".join(result)


def parse_jsonc(text: str) -> dict | Unparseable:
    """Strip JSONC comments, then `json.loads`. Any failure -- an unclosed
    string, invalid JSON after stripping, or a non-object top-level value --
    is `Unparseable(INVALID_JSONC)`, fail-closed rather than a lenient
    parse."""

    try:
        stripped = _strip_jsonc_comments(text)
    except Exception as exc:  # fail-closed: any surprise is INVALID_JSONC, never a pass
        return Unparseable(UnparseableKind.INVALID_JSONC, where="<jsonc>", detail=str(exc))

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return Unparseable(UnparseableKind.INVALID_JSONC, where="<jsonc>", detail=str(exc))

    if not isinstance(parsed, dict):
        return Unparseable(
            UnparseableKind.INVALID_JSONC,
            where="<jsonc>",
            detail="top-level JSON value is not an object",
        )

    return parsed


# ---------------------------------------------------------------------------
# PART 2 OF 6: check_grammar (check 1) + its supporting discriminated types.
#
# Spec: `.gleipnir/plans/config-scoping-preflight.md`, "Design Consolidation"
# -> "The consolidated public API" declares the FULL eventual `FindingCheck`
# enum now (only `GRAMMAR` is exercised by this part's check; the remaining
# members are specified by later checks/parts and declared here to avoid a
# later signature break to an already-shipped enum).
# ---------------------------------------------------------------------------

class FindingCheck(Enum):
    GRAMMAR = "grammar"
    SINGLE_HOLDER = "single_holder"
    FAIL_OPEN = "fail_open"
    OVER_RESTRICTION = "over_restriction"
    GLOBAL_DISABLE = "global_disable"
    MIS_SCOPED_GLOB = "mis_scoped_glob"


class FindingSeverity(Enum):
    FAIL = "fail"  # forces a nonzero (REFUSE-equivalent) exit
    WARN = "warn"  # reported, does not by itself force nonzero


@dataclass(frozen=True)
class Finding:
    """A discriminated preflight finding -- mirrors `Unparseable`'s shape.
    `where` is the dotted/quoted key path (frontmatter has no post-parse
    line numbers, so the key path IS the location) and is never left blank;
    `detail` is a human-readable reason, also never left blank."""

    check: FindingCheck
    severity: FindingSeverity
    where: str
    detail: str = ""


def _quoted(key: object) -> str:
    """Render a nested map key exactly as it would appear quoted in the
    source frontmatter, e.g. `"gleipnir-git*"` or `".git/**"`."""

    return f'"{key}"'


def check_grammar(parsed: dict) -> list[Finding]:
    """Check 1 (ST-1 / ST-9): walk the ALREADY-PARSED frontmatter dict and
    apply, symmetrically, in BOTH directions:

      - every `permission.*` value -- the direct scalar value of a
        permission verb, or a value inside a nested glob-keyed map under
        one -- must be an allow/deny/ask STRING. A boolean there (the
        L-C12 bug, ST-1) is a `GRAMMAR`/`FAIL` Finding.
      - every top-level `tools.*` value must be an actual boolean. A
        string there (the inverse bug, ST-9) is also a `GRAMMAR`/`FAIL`
        Finding.
      - if `permission` or `tools` is PRESENT at all but its value is not
        a map (e.g. `tools: true`, `permission: deny`, or a `- "..."`
        list mistakenly used where a map is required) that is itself a
        `GRAMMAR`/`FAIL` Finding, `where="permission"`/`where="tools"` --
        this is the earliest checkpoint that catches a malformed-but-
        grammar-legal scalar/list before any downstream `.items()` call
        would otherwise crash on it.

    Never re-parses text; never raises on well-formed-but-wrong-typed
    input -- a clean, well-typed agent yields `[]`.
    """

    findings: list[Finding] = []

    permission = parsed.get("permission")
    if permission is not None and not isinstance(permission, dict):
        findings.append(
            Finding(
                check=FindingCheck.GRAMMAR,
                severity=FindingSeverity.FAIL,
                where="permission",
                detail=(
                    "non-map value under permission: where a map of "
                    "verb -> allow/deny/ask (or nested glob map) is "
                    "expected"
                ),
            )
        )
    elif isinstance(permission, dict):
        for verb, value in permission.items():
            if isinstance(value, dict):
                for glob_key, inner in value.items():
                    if isinstance(inner, bool):
                        findings.append(
                            Finding(
                                check=FindingCheck.GRAMMAR,
                                severity=FindingSeverity.FAIL,
                                where=f"permission.{verb}.{_quoted(glob_key)}",
                                detail=(
                                    "boolean under permission where an "
                                    "allow/deny/ask string is expected"
                                ),
                            )
                        )
            elif isinstance(value, bool):
                findings.append(
                    Finding(
                        check=FindingCheck.GRAMMAR,
                        severity=FindingSeverity.FAIL,
                        where=f"permission.{verb}",
                        detail=(
                            "boolean under permission where an "
                            "allow/deny/ask string is expected"
                        ),
                    )
                )

    tools = parsed.get("tools")
    if tools is not None and not isinstance(tools, dict):
        findings.append(
            Finding(
                check=FindingCheck.GRAMMAR,
                severity=FindingSeverity.FAIL,
                where="tools",
                detail=(
                    "non-map value under tools: where a map of "
                    "glob -> boolean is expected"
                ),
            )
        )
    elif isinstance(tools, dict):
        for glob_key, value in tools.items():
            if not isinstance(value, bool):
                findings.append(
                    Finding(
                        check=FindingCheck.GRAMMAR,
                        severity=FindingSeverity.FAIL,
                        where=f"tools.{_quoted(glob_key)}",
                        detail=(
                            "non-boolean value under tools: where an "
                            "actual boolean is expected"
                        ),
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# PART 3 OF 6: enumerate_effective_tools + assert_single_holders (check 2).
#
# Spec: `.gleipnir/plans/config-scoping-preflight.md`, "Design Consolidation"
# Decision 1 (the dual `FAIL_OPEN` where-shape disambiguation) and Decision 3
# (the `config_scan_main` orchestration sequence these two functions feed
# into -- context only, not implemented here).
# ---------------------------------------------------------------------------

def enumerate_effective_tools(
    agents: dict[str, dict],
    jsonc_agent_overrides: dict[str, dict] | None = None,
) -> dict[str, set[str]]:
    """Reduce each agent's ALREADY-PARSED frontmatter (plus an optional
    `opencode.jsonc` `agent.<name>.tools` override block, L-C12b's SECOND
    valid deny location) to the set of namespace globs it effectively
    denies. A deny in EITHER location denies the namespace for that agent --
    the two sources are UNIONED, never one replacing the other. An absent or
    empty `jsonc_agent_overrides` (matching the live no-`agent`-key
    `opencode.jsonc`) is a pure no-op merge.

    Design Consolidation Decision 2: a mis-scoped glob (e.g. `"gleipnir-git*"`,
    missing the underscore) can never match a real `<server>_<tool>` name and
    so must never enter `effective` at all -- only a `False`-valued key that
    structurally COULD match a real tool name (i.e. ends with the literal
    `"_*"`) is counted as a deny."""

    overrides = jsonc_agent_overrides or {}

    effective: dict[str, set[str]] = {}
    for name, frontmatter in agents.items():
        own_tools = frontmatter.get("tools", {})
        if not isinstance(own_tools, dict):
            # Defense-in-depth (never trust check_grammar ran first): a
            # present-but-non-dict `tools` value (bareword bool/int/float,
            # or a list) must never reach `.items()` -- treat it as
            # "denies nothing" rather than raising. `check_grammar` is
            # what actually flags this to the operator.
            own_tools = {}
        denied = {
            glob for glob, value in own_tools.items()
            if value is False and glob.endswith("_*")
        }

        override_tools = overrides.get(name, {})
        if not isinstance(override_tools, dict):
            override_tools = {}
        denied |= {
            glob for glob, value in override_tools.items()
            if value is False and glob.endswith("_*")
        }

        effective[name] = denied

    return effective


def assert_single_holders(
    effective: dict[str, set[str]],
    mcp_namespaces: list[str],
    holder_map: dict[str, str],
) -> list[Finding]:
    """Check 2c: for each namespace meant to be held by exactly one
    designated agent (per `holder_map`), verify that is actually the case
    against the `effective` deny-sets computed by `enumerate_effective_tools`.

    Per namespace, `non_deniers` is every agent in `effective` that does NOT
    deny it:

      - zero non-deniers -> nobody holds it (not even the designated
        holder) -> `OVER_RESTRICTION`/`WARN`, `where` = the namespace alone.
      - exactly one non-denier and it IS the designated holder -> clean, no
        Finding.
      - exactly one non-denier but it is NOT the designated holder -> a
        single, but WRONG, holder. Only a `SINGLE_HOLDER`/`FAIL` Finding is
        produced -- there is no second "extra" agent beyond the lone
        non-denier to separately name as a leak.
      - more than one non-denier -> anomalous, reported from TWO angles: one
        `SINGLE_HOLDER`/`FAIL` Finding (`where` = the namespace alone)
        naming EVERY non-denier, PLUS one individual `FAIL_OPEN`/`FAIL`
        Finding per non-denier OTHER than the designated holder, `where` =
        EXACTLY `f"{agent}: {namespace}"`. The designated holder is NEVER
        itself named in a `FAIL_OPEN` Finding.
    """

    findings: list[Finding] = []

    for namespace in mcp_namespaces:
        non_deniers = {
            name for name, denied in effective.items() if namespace not in denied
        }
        designated = holder_map.get(namespace)

        if not non_deniers:
            findings.append(
                Finding(
                    check=FindingCheck.OVER_RESTRICTION,
                    severity=FindingSeverity.WARN,
                    where=namespace,
                    detail=(
                        f"no agent holds {namespace!r} -- not even the "
                        f"designated holder {designated!r} -- the "
                        "namespace is over-restricted"
                    ),
                )
            )
            continue

        if len(non_deniers) == 1 and designated in non_deniers:
            continue  # clean: exactly the designated holder, nobody else

        holders_desc = ", ".join(sorted(non_deniers))
        findings.append(
            Finding(
                check=FindingCheck.SINGLE_HOLDER,
                severity=FindingSeverity.FAIL,
                where=namespace,
                detail=(
                    f"{namespace!r} is meant to be held by exactly one "
                    f"designated agent ({designated!r}) but is not denied "
                    f"by: {holders_desc}"
                ),
            )
        )

        if len(non_deniers) == 1:
            # A lone but WRONG holder -- no separate "extra" leaker exists
            # to name individually beyond what SINGLE_HOLDER already names.
            continue

        for agent in sorted(non_deniers):
            if agent == designated:
                continue
            findings.append(
                Finding(
                    check=FindingCheck.FAIL_OPEN,
                    severity=FindingSeverity.FAIL,
                    where=f"{agent}: {namespace}",
                    detail=(
                        f"{agent!r} does not deny {namespace!r} and would "
                        "silently gain broker tools on restart"
                    ),
                )
            )

    return findings


# ---------------------------------------------------------------------------
# PART 4 OF 6: check_fail_open + check_global_disable + find_mis_scoped_denies
# (check 4).
#
# Spec: `.gleipnir/plans/config-scoping-preflight.md`, "Design Consolidation"
# Decision 1 (the dual `FAIL_OPEN` `where`-shape disambiguation --
# `assert_single_holders` above names `f"{agent}: {namespace}"`; the
# `check_fail_open` below names JUST `namespace`, glob-only, so the two
# `FAIL_OPEN` emitters are always distinguishable in aggregated output) and
# Decision 2 (why these stay separate pure functions with distinct input
# shapes -- `check_fail_open` consumes the already-REDUCED `effective` map,
# `find_mis_scoped_denies` consumes the RAW per-agent `tools` maps, since a
# mis-scoped glob never survives into `effective` in the first place).
# ---------------------------------------------------------------------------

def check_fail_open(
    mcp_servers: list[str],
    effective: dict[str, set[str]],
    holder_map: dict[str, str],
) -> list[Finding]:
    """Check 4 (ST-7): for EVERY declared MCP server namespace glob (not
    hardcoded to the two named broker namespaces -- generic over whatever
    `mcp_servers` lists, including a synthetic/future server with no
    `holder_map` entry at all), check across ALL agents in `effective`
    whether AT LEAST ONE denies it. Zero deniers -> the namespace is
    totally open -> `Finding(FAIL_OPEN, FAIL, where=<namespace glob alone>,
    ...)`. This is the opposite extreme from `assert_single_holders`'
    `SINGLE_HOLDER`/`FAIL_OPEN` pair (which reacts to *too many*
    non-deniers of a *designated* namespace); this function reacts to
    *zero* deniers of *any* namespace, designated or not.

    `holder_map` is consulted ONLY to enrich `detail` (naming the intended
    holder, when one happens to be designated) -- it is NEVER used to gate
    or skip the check. A namespace absent from `holder_map` entirely is
    still checked, and can still FAIL.

    The `where`-shape is deliberately JUST the namespace glob (e.g.
    `"gleipnir-foo_*"`), never `f"{agent}: {namespace}"` -- that agent-named
    shape belongs exclusively to `assert_single_holders`' `FAIL_OPEN`
    Findings. Keeping the two shapes distinct is Decision 1's load-bearing
    contract.
    """

    findings: list[Finding] = []

    for namespace in mcp_servers:
        deniers = {name for name, denied in effective.items() if namespace in denied}
        if deniers:
            continue

        designated = holder_map.get(namespace)
        if designated is not None:
            detail = (
                f"no agent in the roster denies {namespace!r} -- the "
                f"intended holder {designated!r} would need every other "
                "agent to deny it, but nobody does; the namespace is "
                "totally fail-open"
            )
        else:
            detail = (
                f"no agent in the roster denies {namespace!r} and it has "
                "no designated holder -- the namespace is totally "
                "fail-open"
            )

        findings.append(
            Finding(
                check=FindingCheck.FAIL_OPEN,
                severity=FindingSeverity.FAIL,
                where=namespace,
                detail=detail,
            )
        )

    return findings


def check_global_disable(jsonc_top_level_tools: dict | None) -> list[Finding]:
    """Check 4 (ST-2): scan `opencode.jsonc`'s top-level `"tools"` block
    (a `{glob: bool}` map, or `None`/`{}` when the key is absent -- the
    LIVE current shape) for the known-broken L-C12b bug-2 pattern: a
    `False`-valued top-level entry globally disables a namespace for every
    subagent, and that disable is never restored by any per-agent
    re-allow, so it hides the namespace regardless of any correct
    per-agent scoping done elsewhere. `None`/`{}` -> `[]` -- the regression
    guard that today's live config (which has no top-level `tools` key at
    all) does not trigger this.
    """

    if not jsonc_top_level_tools:
        return []

    findings: list[Finding] = []
    for glob_key, value in jsonc_top_level_tools.items():
        if value is False:
            findings.append(
                Finding(
                    check=FindingCheck.GLOBAL_DISABLE,
                    severity=FindingSeverity.FAIL,
                    where=glob_key,
                    detail=(
                        f"top-level tools.{glob_key!r}: false globally "
                        "disables this namespace for every subagent -- no "
                        "per-agent re-allow can restore it, so it hides "
                        "the namespace regardless of scoping elsewhere "
                        "(L-C12b bug 2)"
                    ),
                )
            )

    return findings


def _mis_scoped_finding(agent: str, glob_key: str, base_names: list[str]) -> Finding | None:
    """Helper: if `glob_key` starts with one of `base_names` but is not
    exactly that server's correct `f"{server}_*"` deny form, return the
    `MIS_SCOPED_GLOB`/`WARN` Finding for it; otherwise `None` (either it
    matches no known server at all, or it is already correctly formed)."""

    for server in base_names:
        if not glob_key.startswith(server):
            continue
        correct_form = f"{server}_*"
        if glob_key == correct_form:
            return None
        return Finding(
            check=FindingCheck.MIS_SCOPED_GLOB,
            severity=FindingSeverity.WARN,
            where=f"{agent}: {glob_key}",
            detail=(
                f"{glob_key!r} starts with server {server!r} but does not "
                f"match the correct deny form {correct_form!r} -- it would "
                "never actually match a real registered "
                f"{server}_<tool> MCP tool name"
            ),
        )

    return None


def find_mis_scoped_denies(
    agents: dict[str, dict],
    mcp_servers: list[str],
    jsonc_agent_overrides: dict[str, dict] | None = None,
) -> list[Finding]:
    """Check 4 (ST-8): scan the RAW per-agent `tools` maps -- both each
    agent's own frontmatter `tools` dict AND any `jsonc_agent_overrides`
    entry for that same agent (L-C12b's two valid deny locations) -- for a
    glob key that STARTS WITH a known server base name (`mcp_servers` here
    are BASE names, e.g. `"gleipnir-git"`, NOT `"gleipnir-git_*"`) but does
    NOT match that server's correct `f"{server}_*"` deny form (e.g.
    `"gleipnir-git*"`, missing the underscore).

    This operates on RAW input deliberately (Decision 2): `enumerate_
    effective_tools` (Part 3) only ever sees globs that already correctly
    matched `<server>_*` by construction of how its output is consumed --
    a mis-scoped glob is invisible to `check_fail_open`/
    `assert_single_holders`, which is exactly why this needs its own
    function reading the raw maps.

    Emits `Finding(MIS_SCOPED_GLOB, WARN, where=f"{agent}: {key}", ...)`
    per such key -- WARN, not FAIL: a suspected authoring mistake, not by
    itself proof of a leaked namespace (that is `check_fail_open`'s job).
    """

    overrides = jsonc_agent_overrides or {}
    findings: list[Finding] = []

    for name, frontmatter in agents.items():
        own_tools = frontmatter.get("tools", {}) or {}
        if not isinstance(own_tools, dict):
            # Defense-in-depth (never trust check_grammar ran first): a
            # present-but-non-dict `tools` value must never be iterated
            # as if it were a glob-keyed map -- treat it as "no globs to
            # check" rather than raising. `check_grammar` is what
            # actually flags this to the operator.
            own_tools = {}
        for glob_key in own_tools:
            finding = _mis_scoped_finding(name, glob_key, mcp_servers)
            if finding is not None:
                findings.append(finding)

        override_tools = overrides.get(name, {}) or {}
        if not isinstance(override_tools, dict):
            override_tools = {}
        for glob_key in override_tools:
            finding = _mis_scoped_finding(name, glob_key, mcp_servers)
            if finding is not None:
                findings.append(finding)

    return findings


# ---------------------------------------------------------------------------
# PART 5 OF 6: decide_config (check 3 / top-level aggregation) + its
# discriminated result types -- mirrors `boundary.py`'s `Verdict` /
# `DEV_MODE_LABEL` / `PreflightDecision` / `decide()` almost exactly.
#
# Spec: `.gleipnir/plans/config-scoping-preflight.md`, "Design Consolidation"
# item 5 (the CORRECTED `decide_config` argument order --
# `(unparseables, findings, agent_count, *, strict=False,
# override_ack=False)`, unparseables FIRST -- the tests are authoritative)
# and Decision 3 step 10 (the orchestration call shape a later part's
# `config_scan_main` will use).
#
# Named `ConfigVerdict`, not `Verdict`, to avoid an import collision with
# `boundary.Verdict` if a caller ever imports both modules -- same three
# values, same semantics, same eventual 0/2/1 CLI exit-code mapping.
# ---------------------------------------------------------------------------

class ConfigVerdict(Enum):
    CLOSED = "closed"
    PROCEED_UNCLOSED = "proceed_unclosed"
    REFUSE = "refuse"


DEV_MODE_LABEL_CONFIG = "config scan NOT CLOSED (override-ack)"


@dataclass(frozen=True)
class ConfigDecision:
    """Mirrors `boundary.PreflightDecision`'s shape exactly."""

    verdict: ConfigVerdict
    label: str
    reasons: tuple[str, ...] = ()


def decide_config(
    unparseables: list[Unparseable],
    findings: list[Finding],
    agent_count: int,
    *,
    strict: bool = False,
    override_ack: bool = False,
) -> ConfigDecision:
    """Aggregate every well-formedness/check-1..4 outcome into one
    `ConfigDecision` -- mirrors `boundary.decide`'s exact control flow.
    `CLOSED` only if there is at least one agent AND zero `Unparseable`
    results AND zero `FAIL`-severity findings (and, when `strict=True`,
    zero `WARN`-severity findings too). An empty `agent_count` (no evidence
    at all) is itself ambiguous and is NEVER treated as closed, exactly
    mirroring `boundary.decide`'s `if not path_probes: all_closed = False`.

    The Part-0-style operator override (`override_ack`) can ONLY escalate a
    not-closed result to `PROCEED_UNCLOSED`, stamped with the honest
    `DEV_MODE_LABEL_CONFIG`. It can never produce `CLOSED` -- there is no
    code path from `override_ack=True` to `ConfigVerdict.CLOSED` in this
    function; the `override_ack` check happens strictly after, and only
    within, the `not all_closed` branch below.
    """

    reasons: list[str] = []
    all_closed = True

    if agent_count == 0:
        all_closed = False
        reasons.append(
            "no agents were parsed (ambiguous => refuse, mirrors "
            "boundary.decide's empty-path_probes rule)"
        )

    for u in unparseables:
        all_closed = False
        reasons.append(f"unparseable: {u.kind.value} at {u.where}: {u.detail}")

    for f in findings:
        if f.severity is FindingSeverity.FAIL:
            all_closed = False
            reasons.append(f"FAIL[{f.check.value}] at {f.where}: {f.detail}")
        elif f.severity is FindingSeverity.WARN:
            if strict:
                all_closed = False
            reasons.append(f"WARN[{f.check.value}] at {f.where}: {f.detail}")

    if all_closed:
        return ConfigDecision(
            ConfigVerdict.CLOSED,
            "config scan boundary CLOSED",
            tuple(reasons),
        )
    if override_ack:
        return ConfigDecision(
            ConfigVerdict.PROCEED_UNCLOSED, DEV_MODE_LABEL_CONFIG, tuple(reasons)
        )
    return ConfigDecision(
        ConfigVerdict.REFUSE,
        "config scan NOT CLOSED; refusing",
        tuple(reasons),
    )


# ---------------------------------------------------------------------------
# PART 6 OF 6: the thin edge (read_agent_files, read_jsonc) + config_scan_main
# -- the CLI composition entrypoint.
#
# Spec: `.gleipnir/plans/config-scoping-preflight.md`, Design Consolidation
# Decision 3 (the authoritative 10-step orchestration sequence, reproduced
# below step-by-step). Mirrors `boundary.py`'s injectable-thin-edge shape:
# every real I/O call here is an `OSError`-catching wrapper around
# `Path.read_text`/`Path.glob`, never letting a real filesystem failure
# propagate uncaught -- mapped instead to a discriminated
# `Unparseable(READ_ERROR, ...)`, exactly as `_fork_drop_verify_attempt`
# wraps `os.pipe`/`os.fork`.
# ---------------------------------------------------------------------------

# The single-holder in-code data (Integrations map: "single-holder map
# (in-code data)"). Namespace globs are the FULL `<server>_*` deny form;
# base names are the bare server name used by `find_mis_scoped_denies` to
# spot a glob that starts with a known server but is missing the
# underscore/star suffix.
DEFAULT_MCP_NAMESPACES: list[str] = ["gleipnir-git_*", "gleipnir-pm_*"]
DEFAULT_HOLDER_MAP: dict[str, str] = {
    "gleipnir-git_*": "git-ops",
    "gleipnir-pm_*": "project-mgr",
}
DEFAULT_MCP_SERVER_BASE_NAMES: list[str] = ["gleipnir-git", "gleipnir-pm"]


def read_agent_files(agents_dir: Path) -> dict[str, str | Unparseable]:
    """Thin edge: glob `agents_dir/*.md` and read each file's raw text.

    Success -> `{stem: text}`. A per-file `OSError` (permission denied, or a
    file that vanishes between the glob and the read) is caught -- never
    propagated -- and mapped to `{stem: Unparseable(READ_ERROR, where=str(
    path), detail=str(exc))}`, one per failing file (never collapsed, never
    silently skipped). A missing/unreadable `agents_dir` itself (its own
    directory-scan `OSError`, on platforms where `Path.glob` raises rather
    than yielding nothing) is ALSO caught and treated as "found zero files"
    (`{}`) -- an empty agent set is a `decide_config`-level concern (forces
    REFUSE via `agent_count == 0`), never a thin-edge crash.
    """

    try:
        paths = sorted(agents_dir.glob("*.md"))
    except OSError:
        return {}

    result: dict[str, str | Unparseable] = {}
    for path in paths:
        try:
            result[path.stem] = path.read_text()
        except OSError as exc:
            result[path.stem] = Unparseable(
                UnparseableKind.READ_ERROR, where=str(path), detail=str(exc)
            )
    return result


def read_jsonc(path: Path) -> str | Unparseable:
    """Thin edge: read `opencode.jsonc`'s raw text. An `OSError` (missing
    file, permission denied -- `PermissionError` is an `OSError` subclass
    and is caught by the same clause) is caught -- never propagated -- and
    mapped to `Unparseable(READ_ERROR, where=str(path), detail=str(exc))`.
    """

    try:
        return path.read_text()
    except OSError as exc:
        return Unparseable(UnparseableKind.READ_ERROR, where=str(path), detail=str(exc))


def _default_config_root() -> Path:
    # src/gleipnir/preflight/config_scan.py -> repo root is three parents up,
    # exactly the same depth `preflight/__main__.py`'s `_repo_root()` uses
    # from its own (sibling) location.
    return Path(__file__).resolve().parents[3] / ".gleipnir"


def config_scan_main(argv: list[str] | None = None, config_root: Path | None = None) -> int:
    """The CLI entrypoint composing the full pipeline (Design Consolidation
    Decision 3's authoritative 10-step orchestration sequence). Prints the
    decision (verdict + label + reasons) to stderr, mirroring
    `preflight/__main__.py.main()`'s style, and returns 0/2/1 for
    CLOSED/PROCEED_UNCLOSED/REFUSE.
    """

    parser = argparse.ArgumentParser(prog="gleipnir-preflight config-scan")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="promote WARN-severity findings to failures (never allow CLOSED with them)",
    )
    parser.add_argument(
        "--override-ack",
        action="store_true",
        help=(
            "Part-0 operator-acknowledged dev-mode override: escalates a "
            "NOT-closed config scan to PROCEED_UNCLOSED with an honest "
            "label; can NEVER produce CLOSED"
        ),
    )
    args = parser.parse_args(argv if argv is not None else [])

    if config_root is None:
        config_root = _default_config_root()

    unparseables: list[Unparseable] = []
    findings: list[Finding] = []
    parsed_agents: dict[str, dict] = {}

    # Step 1.
    agents = read_agent_files(config_root / "agents")

    # Step 2.
    for stem, value in agents.items():
        if isinstance(value, Unparseable):
            unparseables.append(value)
            continue
        block = extract_frontmatter(value)
        if isinstance(block, Unparseable):
            unparseables.append(block)
            continue
        parsed = parse_frontmatter(block)
        if isinstance(parsed, Unparseable):
            unparseables.append(parsed)
            continue
        parsed_agents[stem] = parsed
        findings.extend(check_grammar(parsed))

    # Step 3 + 4: read + parse opencode.jsonc; treat jsonc-derived inputs as
    # absent/None on any failure, never letting a READ_ERROR/INVALID_JSONC
    # short-circuit the rest of the pipeline.
    jsonc_top_level_tools: dict | None = None
    jsonc_agent_overrides: dict[str, dict] = {}

    jsonc_text = read_jsonc(config_root.parent / "opencode.jsonc")
    if isinstance(jsonc_text, Unparseable):
        unparseables.append(jsonc_text)
    else:
        jsonc = parse_jsonc(jsonc_text)
        if isinstance(jsonc, Unparseable):
            unparseables.append(jsonc)
        else:
            jsonc_top_level_tools = jsonc.get("tools")
            jsonc_agent_block = jsonc.get("agent", {})
            if not isinstance(jsonc_agent_block, dict):
                # Defense-in-depth: a present-but-non-dict `agent` value must
                # never reach `.items()` -- treat it as "no per-agent
                # overrides" rather than raising. This coercion is
                # crash-safe only: unlike the frontmatter `tools`/`permission`
                # case, no grammar Finding is emitted for a malformed jsonc
                # `agent` shape, so it is not yet surfaced to the operator.
                jsonc_agent_block = {}
            jsonc_agent_overrides = {}
            for name, block in jsonc_agent_block.items():
                if not isinstance(block, dict):
                    # Same defense-in-depth: a per-agent block value that is
                    # not a dict must never reach `.get("tools", {})` --
                    # treat it as "no tools override" rather than raising.
                    # Crash-safe only: no grammar Finding is emitted here,
                    # so this malformed shape is not yet surfaced to the
                    # operator.
                    block = {}
                jsonc_agent_overrides[name] = block.get("tools", {})

    # Step 5.
    effective = enumerate_effective_tools(parsed_agents, jsonc_agent_overrides)

    # Step 6.
    findings += assert_single_holders(effective, DEFAULT_MCP_NAMESPACES, DEFAULT_HOLDER_MAP)

    # Step 7.
    findings += check_fail_open(DEFAULT_MCP_NAMESPACES, effective, DEFAULT_HOLDER_MAP)

    # Step 8.
    findings += check_global_disable(jsonc_top_level_tools)

    # Step 9.
    findings += find_mis_scoped_denies(
        parsed_agents, DEFAULT_MCP_SERVER_BASE_NAMES, jsonc_agent_overrides
    )

    # Step 10.
    decision = decide_config(
        unparseables,
        findings,
        agent_count=len(parsed_agents),
        strict=args.strict,
        override_ack=args.override_ack,
    )

    print(
        f"gleipnir-preflight config-scan: {decision.verdict.value} -- {decision.label}",
        file=sys.stderr,
    )
    for reason in decision.reasons:
        print(f"  - {reason}", file=sys.stderr)

    if decision.verdict is ConfigVerdict.CLOSED:
        return 0
    if decision.verdict is ConfigVerdict.PROCEED_UNCLOSED:
        return 2
    return 1
