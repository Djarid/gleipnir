/**
 * router.ts — SRP: classify a touched-path set into a review route, and
 * nothing else. One reason to change: the routing mechanism (NOT the
 * literals — those are config, per D-S4-5).
 *
 * Re-expresses (oracle-adjacent, but this is a NEW file/suite — the mapping
 * source is `.gleipnir/stage-role-map.md`'s "Prose/config-only track"
 * section, not a Python module): Axis-1 disqualifier set `X`, Axis-2(a)
 * enforcement-path set `E`, Axis-2(b) grant/enforcement content-pattern set
 * `G`, and the hardened-vs-light routing rule.
 *
 * D-S4-5 (Option 5a): the MECHANISM (this file's logic) is in scope now; the
 * LITERALS (which exact paths/patterns) are a single named config constant
 * marked "superseded at Tier-3 pi cutover" — swapping the literals later is
 * a DATA change, not a logic change, and `router.test.ts` asserts routing
 * DECISIONS over representative inputs, never the identity of the literal
 * set, so that later swap keeps the suite green.
 *
 * `router.ts` is standalone: its only data dependency is its own named
 * literal-set config constant below — no import from `state.ts`,
 * `transitions.ts`, `attestation.ts`, or `engine.ts` (a pure classifier over
 * a path-set `P`).
 *
 * REAL BODY (Assemble step 5d, code stage): the Axis-1/Axis-2 classifier
 * below is implemented against `.gleipnir/stage-role-map.md`'s "Prose/
 * config-only track" section, which `test/router.test.ts` (mechanism tests,
 * not literal-identity tests, per D-S4-5) pins.
 */

/** The three routing decisions (mirrors the const-object+union idiom used
 * throughout this engine slice, D-S4-P2, for consistency — even though this
 * module has no Python oracle enum to port). */
export const RouteDecision = Object.freeze({
  FULL_PIPELINE: "full_pipeline",
  HARDENED: "hardened",
  LIGHT: "light",
} as const);

export type RouteDecision = (typeof RouteDecision)[keyof typeof RouteDecision];

/**
 * The input to `routePlan`: a plan's touched-path set `P`, plus (optionally)
 * the flattened added/changed content lines, used for the Axis-1 shebang
 * check and the Axis-2(b) grant-pattern content check.
 */
export interface RouteInput {
  readonly paths: readonly string[];
  readonly addedLines?: readonly string[];
}

// ---------------------------------------------------------------------------
// Axis-1 — the disqualifier set `X` (mechanism; literals named as ONE
// config constant per D-S4-5, marked pending Tier-3 pi-literal supersession
// below). A hit anywhere in `P`, or a shebang in the added content, routes
// the WHOLE plan through the full 8-stage pipeline regardless of how small
// the rest of `P` is.
// ---------------------------------------------------------------------------

/**
 * Axis-1 `X` disqualifier config (D-S4-5, Option 5a): the MECHANISM below
 * (`isAxis1Hit`) is stable; ONLY this constant's contents are pi-literal-
 * specific and are superseded at Tier-3 pi cutover (a data change, never a
 * logic change — see the module header + `router.test.ts`'s literal-
 * agnostic assertions).
 */
export const AXIS1_DISQUALIFIER_CONFIG = Object.freeze({
  /** Directory prefixes that disqualify (executable/interpreted trees). */
  dirPrefixes: Object.freeze(["src/", "tests/", "hooks/", "bin/", ".github/"]),
  /** File extensions that disqualify wherever they appear in `P`. */
  extensions: Object.freeze([
    ".sh",
    ".bash",
    ".py",
    ".js",
    ".ts",
    ".rs",
    ".go",
    ".yml",
    ".yaml",
    ".mk",
  ]),
  /** Basenames that disqualify regardless of directory. */
  basenames: Object.freeze(["Makefile"]),
  /** Basename prefixes that disqualify (e.g. `Containerfile.node`). */
  basenamePrefixes: Object.freeze(["Containerfile"]),
});

function basename(path: string): string {
  const idx = path.lastIndexOf("/");
  return idx === -1 ? path : path.slice(idx + 1);
}

function isAxis1PathHit(path: string): boolean {
  const cfg = AXIS1_DISQUALIFIER_CONFIG;
  if (cfg.dirPrefixes.some((prefix) => path.startsWith(prefix))) {
    return true;
  }
  const base = basename(path);
  if (cfg.basenames.includes(base)) {
    return true;
  }
  if (cfg.basenamePrefixes.some((prefix) => base.startsWith(prefix))) {
    return true;
  }
  if (cfg.extensions.some((ext) => path.endsWith(ext))) {
    return true;
  }
  return false;
}

/** Any added/changed line beginning with a `#!` shebang disqualifies (an
 * interpreter shebang in added content, per the stage-role-map `X` set),
 * independent of which specific path it landed in. */
function hasShebang(addedLines: readonly string[]): boolean {
  return addedLines.some((line) => line.startsWith("#!"));
}

function isAxis1Hit(paths: readonly string[], addedLines: readonly string[]): boolean {
  return paths.some(isAxis1PathHit) || hasShebang(addedLines);
}

// ---------------------------------------------------------------------------
// Axis-2(a) — the enforcement-path set `E` (mechanism; literals named as
// ONE config constant, same D-S4-5 treatment as Axis-1's).
// ---------------------------------------------------------------------------

export const AXIS2A_ENFORCEMENT_PATH_CONFIG = Object.freeze({
  dirPrefixes: Object.freeze([
    ".gleipnir/agents/",
    ".gleipnir/plugins/",
    ".gleipnir/sandbox/",
    ".gleipnir/policy/",
    ".gleipnir/keys/",
  ]),
  exactPaths: Object.freeze([
    ".gleipnir/stage-role-map.md",
    "opencode.jsonc",
    "opencode.json",
    ".gitignore",
    ".envrc",
    "pyproject.toml",
    ".gitattributes",
    ".gitmodules",
  ]),
  /** Any-depth `opencode.json` (the plan's `** /opencode.json` clause). */
  basenames: Object.freeze(["opencode.json"]),
});

function isAxis2aPathHit(path: string): boolean {
  const cfg = AXIS2A_ENFORCEMENT_PATH_CONFIG;
  if (cfg.dirPrefixes.some((prefix) => path.startsWith(prefix))) {
    return true;
  }
  if (cfg.exactPaths.includes(path)) {
    return true;
  }
  if (cfg.basenames.includes(basename(path))) {
    return true;
  }
  return false;
}

function isAxis2aHit(paths: readonly string[]): boolean {
  return paths.some(isAxis2aPathHit);
}

// ---------------------------------------------------------------------------
// Axis-2(b) — the grant/enforcement content-pattern set `G` (mechanism over
// added/changed lines; content, not paths).
// ---------------------------------------------------------------------------

const YAML_BLOCK_KEY_RE = /^\s*(permission|tools):\s*/;
const YAML_CAPABILITY_LINE_RE = /^\s*(edit|write|task|bash|webfetch):\s*(allow|deny)\b/;
const JSON_ENFORCEMENT_KEY_RE =
  /"(permission|tools|enabled|instructions|default_agent|subagent_depth|mcp)"\s*:/;
const KEYS_DIGEST_LINE_RE = /^[0-9a-f]{64}\b/;

function isAxis2bLineHit(line: string): boolean {
  return (
    YAML_BLOCK_KEY_RE.test(line) ||
    YAML_CAPABILITY_LINE_RE.test(line) ||
    JSON_ENFORCEMENT_KEY_RE.test(line) ||
    KEYS_DIGEST_LINE_RE.test(line)
  );
}

function isAxis2bHit(addedLines: readonly string[]): boolean {
  return addedLines.some(isAxis2bLineHit);
}

/**
 * Classify a plan's touched-path set `P` (+ optional added content lines)
 * into a review route: `FULL_PIPELINE` (Axis-1 `X` disqualifier hit),
 * `HARDENED` (track-eligible AND an Axis-2(a) `E`-path hit OR an Axis-2(b)
 * `G`-content hit), or `LIGHT` (track-eligible, no `E`/`G` hit).
 */
export function routePlan(input: RouteInput): RouteDecision {
  const paths = input.paths;
  const addedLines = input.addedLines ?? [];

  if (isAxis1Hit(paths, addedLines)) {
    return RouteDecision.FULL_PIPELINE;
  }

  if (isAxis2aHit(paths) || isAxis2bHit(addedLines)) {
    return RouteDecision.HARDENED;
  }

  return RouteDecision.LIGHT;
}
