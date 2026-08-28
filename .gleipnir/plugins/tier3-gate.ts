// Gleipnir Tier-3 write-block gate (Tier-3 enforcement code) — the
// deterministic write-block wiring for the out-of-band signed-approval
// channel.
//
// Spec: `.gleipnir/plans/tier3-signed-approval.md` Decision 5/14/14a, Trace
// "Integrations map" + L9, Edge cases 11-13, Assemble Step 7, Stress-test
// T-21. This opencode plugin is the deterministic BLOCK half of the
// code-enforced Tier-3 write-gate: the gate LOGIC lives in
// `src/gleipnir/approval/gate.py` (a library + CLI choke-point); THIS file
// is the hook that actually stops the write from happening.
//
// **Extended** (`.gleipnir/plans/tier3-approval-ux.md` Decisions P1/P2/P8,
// Trace section A, Stress-test S1/S2/S3/S4/S12): on a genuine policy REFUSE
// (the gate CLI exiting non-zero — the NEW `GateRefused` subclass), this
// hook now ALSO stages the exact resulting content to
// `.gleipnir/var/tmp/pending-<change_hash>.json` and appends a ready-to-visit
// approval URL to the refusal message, so the operator can review-then-
// one-click-approve via `src/gleipnir/approval/server.py`'s
// `GET/POST /approve/<hash>` routes instead of hand-crafting a `curl`. This
// is purely ADDITIVE inside the existing refuse path — `isTier3Path`,
// `resultingContentFor`, `runGateCheck`, and `decideFromExit`'s
// return-"allow"-on-0 / throw-on-non-zero contract are otherwise unchanged.
//
// TRUST TIER: this file is Tier-3 enforcement code — operator-authored,
// agent-unwritable. No roster agent (not even gleipnir-code) may edit it. It
// is the guard; it must not be reachable by the guarded (Axiom 2 / G-1).
// `.gleipnir/plugins/**` is itself in the enforcement-path set `E`
// (`stage-role-map.md`), so this file is applied by operator/build-mode
// ONLY, exactly like `sequence-gate.ts`/`git-guard.ts`/`advance-hook.ts`.
//
// ALWAYS-ACTIVE (read this first, mirrors git-guard.ts's D9 posture). A
// Tier-3 write must be gated in EVERY session, whether or not a pipeline run
// is armed — so, UNLIKE sequence-gate.ts (armed-only), there is NO
// GLEIPNIR_PIPELINE / bridge-file arming check here. Do not add one.
//
// WHAT IT DOES
//   * pre-tool (`tool.execute.before`): on an `edit` or `write` tool call,
//     read the target path (`output.args.filePath` — the same shape the
//     documented `.env`-protection example uses, plan Trace L9). If the
//     target is NOT under the Tier-3 path-set below, RETURN (pass-through —
//     ordinary writes to src/**, tests/**, etc. are never gated, never
//     shelled out to, never throw). If it IS a Tier-3 path, compute the
//     EXACT resulting content this tool call will produce (see
//     RESULTING-CONTENT COMPUTATION below), write it to a temp file, and
//     shell out (`spawnSync`) to the already-built, already-tested
//     approval-gate CLI (`python -m gleipnir.approval.gate --check <filePath>
//     --content-file <temp> --token <token-file>`,
//     `src/gleipnir/approval/__main__.py`) — which hashes the --content-file
//     bytes (NOT a fresh read of --check) — and THROW to abort the tool call
//     on any non-zero exit (fail-closed — exit 0 is the ONLY allow; 1 and 3
//     are both REFUSE per the CLI's documented contract). The temp file is
//     unlinked in a `finally` so a spawn failure never leaks it.
//   * on a genuine policy REFUSE (the non-zero-exit branch, now typed
//     `GateRefused` — see GateRefused below), it ADDITIONALLY stages the
//     exact resulting content to `.gleipnir/var/tmp/pending-<hash>.json`
//     (`stagePendingContent`) and appends a ready-to-visit approval URL
//     (`buildApprovalUrl`) to the re-thrown `GateRefused`'s message. This
//     staging step is skipped entirely for every OTHER abort (a broken
//     prerequisite, or an `edit`/no-content refusal that never reached the
//     gate CLI at all) — see the GateRefused section below.
//
// RESULTING-CONTENT COMPUTATION (plan Decisions 19 + 20 — the mint-vs-check
// content-hash fix). The token was minted by `approval/server.py` over the
// sha256 of the NEW proposed content the operator approved out-of-band (the
// POSTed body). The gate must therefore hash the SAME new content — which
// only this hook knows (it is the tool call's proposed RESULT), not the disk
// (`tool.execute.before` fires BEFORE the write lands, so the disk still
// holds the pre-edit BASE content). So:
//   * `write` — the resulting bytes are exactly `output.args.content`
//     (verified vs opencode `packages/opencode/src/tool/write.ts@dev`:
//     params are `{content, filePath}` and the written bytes are
//     `params.content`). CERTAIN → hand it to the CLI as `--content-file`.
//   * `edit` — FAIL CLOSED (throw). opencode's `edit`
//     (`packages/opencode/src/tool/edit.ts@dev`) is NOT a plain
//     oldString→newString replace: it runs a 9-replacer fuzzy cascade with
//     Levenshtein thresholds + line-ending/BOM normalization + a post-write
//     `format.file()` pass — none reliably reproducible out-of-band in TS. If
//     the hook cannot be CERTAIN of the resulting bytes it MUST REFUSE rather
//     than guess (the plan's fail-closed principle, Decision 5 /
//     `boundary.decide()`); a guessed content that DIFFERS from what opencode
//     actually writes would defeat the content-binding. So a Tier-3 `edit`
//     is refused with a message directing the operator to use `write`
//     (full-file, deterministic) for Tier-3 changes.
//
// ROUTES ON THE TARGET PATH, NOT THE ACTING AGENT (plan Trace L9). The
// before-hook input does not carry the acting-agent's identity (only a
// `task` call exposes the delegated-TO agent via `output.args.subagent_type`,
// the wrong signal for an edit/write) — so gating on "is the target under the
// Tier-3 path-set" is the only reliable form, and it gates EVERY agent's
// write to a Tier-3 path, not merely a future `tier3-writer`'s.
//
// THE TIER-3 PATH-SET (plan Assemble Step 7 — the enforcement-path set `E`
// plus `.gleipnir/plugins/**`, since this very file lives there):
//   .gleipnir/agents/**    .gleipnir/skills/**    .gleipnir/goals/**
//   .gleipnir/decisions/** .gleipnir/keys/**      .gleipnir/stage-role-map.md
//   .gleipnir/plugins/**
//
// TOKEN-FILE RESOLUTION (a plan-stage judgment NOT pinned down verbatim by
// the plan's prose — Decision 17 names the WRITE-side naming convention
// `var/tmp/approval-<change_hash_prefix>.json`, minted by
// `approval/server.py`'s `token_path_for`, but does not specify how a THIRD
// PARTY hook — which does not itself compute the change_hash — should locate
// the right file to pass as `--token`). This hook resolves it by picking the
// most-recently-modified `approval-*.json` file under `.gleipnir/var/tmp/`
// (the one Decision-17 token directory) and lets the ALREADY fail-closed
// `gate.py`/`__main__.py` choke-point (untouched by this file) make the real
// ALLOW/REFUSE call against it — a missing/absent candidate resolves to a
// deterministically-nonexistent path, which the CLI's own "no approval token
// present" fail-closed branch already handles identically to any other
// missing-token case. This hook duplicates NO token-validation logic of its
// own; it is a pure call-site + exit-code mapper, exactly like
// `git-guard.ts`'s relationship to `config-scan`.
//
// GateRefused (`.gleipnir/plans/tier3-approval-ux.md` Trace section A, Edge
// cases E1-E3, Stress-test S12). A NEW `Tier3GateAbort` subclass thrown ONLY
// by `decideFromExit`'s non-zero-exit branch — i.e. ONLY on a genuine policy
// REFUSE returned by the gate CLI. This is the exact classification
// mechanism that distinguishes a genuine policy refusal from every OTHER
// `Tier3GateAbort`:
//   * `PreflightUnavailable` (a broken prerequisite — missing/non-exec
//     interpreter) is a `Tier3GateAbort` but NEVER a `GateRefused` — the
//     gate CLI never even ran, so there is nothing to stage (E1).
//   * `resultingContentFor`'s throw for `edit` (fuzzy-replacer, not
//     reproducible out-of-band) or for a `write` with no string `content` is
//     a `Tier3GateAbort` but NEVER a `GateRefused` — control never reaches
//     `runGateCheck`/`decideFromExit` on these paths, so no `GateRefused` is
//     ever produced (E2/E3).
// Staging (below) is keyed STRICTLY on `err instanceof GateRefused`, not on
// "any `Tier3GateAbort`" — this is a mechanically pinned design constraint,
// not a build-time judgment call.
//
// STAGING ON A GENUINE REFUSE (plan Decisions P1/P2/P8). The ONLY behavior
// change is inside the existing `tool.execute.before` `catch (err)` block.
// Because `resultingContent` is computed at
// `resultingContentFor(input.tool, output.args)` BEFORE `runGateCheck` is
// ever called, it is in scope for the whole `try`/`catch` (hoisted via a
// `let` above the `try`, since a `const` declared inside a `try` block is
// not visible in its `catch`); on any path where `resultingContentFor` itself
// threw (edit, no-string-content), control never reached
// `runGateCheck`/`decideFromExit`, so `resultingContent` stays `undefined`
// and the `instanceof GateRefused` branch is never taken for those aborts
// (E2/E3 — see GateRefused above). On a genuine `GateRefused`:
//   1. `stagePendingContent(directory, input.tool, filePath, resultingContent)`
//      writes the exact resulting bytes to
//      `.gleipnir/var/tmp/pending-<hash>.json` and returns `<hash>`.
//   2. A NEW `GateRefused` is thrown whose message is the original refusal
//      message plus `buildApprovalUrl(hash)` — a ready-to-visit URL (or a
//      graceful relative-hint fallback when `GLEIPNIR_APPROVAL_BASE_URL` is
//      unset, P8).
// Every OTHER `Tier3GateAbort` (`PreflightUnavailable`, the edit/no-content
// throws) falls through the existing `if (err instanceof Tier3GateAbort)
// throw err` rethrow UNCHANGED — no staging, no message rewrite.
//
// FAIL-CLOSED: every uncertainty (python missing/not executable, spawn
// error, unexpected exit code, unreadable repo, an edit/write with no
// classifiable filePath) is an abort, not an allow. There is no
// allow-by-default path — unlike git-guard.ts's exit-2 operator-override
// valve, THIS gate has none: a Tier-3 write with no valid fresh token is
// refused, full stop (plan Decision 5, "no valid fresh token bound to this
// exact change ⇒ no write", no override branch specified).
//
// NOT YET CLOSED (honest scope, mirrors the other three plugins): this
// enforces AT THE HOOK. This plugin file, the gate CLI, and the key all sit
// in agent-writable/agent-adjacent space until the S-2 mount + terminal
// closure make them structurally unreachable — cooperative-policy, not yet a
// hard boundary. See `.gleipnir/plans/tier3-signed-approval.md`. The staged
// file (`pending-<hash>.json`) is likewise Tier-0/disposable, input to
// review, never authority — authority remains the HMAC token minted by
// `capture_approval` (`.gleipnir/plans/tier3-approval-ux.md` Trace section C).

import { createHash } from "node:crypto"
import { spawnSync } from "node:child_process"
import {
  accessSync,
  constants,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs"
import { tmpdir } from "node:os"
import { join, relative, resolve, sep } from "node:path"

// The two write tools this gate covers.
const GATED_TOOLS = new Set(["edit", "write"])

// The Tier-3 path-set (plan Assemble Step 7). Directory prefixes are matched
// with a trailing separator so e.g. ".gleipnir/agentsXtra/foo" can never
// false-positive-match the ".gleipnir/agents/" prefix.
const TIER3_DIR_PREFIXES = [
  ".gleipnir/agents/",
  ".gleipnir/skills/",
  ".gleipnir/goals/",
  ".gleipnir/decisions/",
  ".gleipnir/keys/",
  ".gleipnir/plugins/",
]
const TIER3_EXACT_FILES = new Set([".gleipnir/stage-role-map.md"])

// The out-of-framework approval-gate CLI's interpreter. Resolved from the
// plugin `directory` param exactly as git-guard.ts/advance-hook.ts resolve
// `bin/gleipnir-preflight` — never hardcoded to an absolute host path.
// Mirrors `bin/gleipnir-preflight`'s / `bin/gleipnir-approval-server`'s own
// `$repo/.venv/bin/python` convention.
const PYTHON_REL = ".venv/bin/python"
const GATE_MODULE_ARGV = ["-m", "gleipnir.approval.gate"]
const TOKEN_DIR_REL = ".gleipnir/var/tmp"

// The staged-envelope directory (`.gleipnir/plans/tier3-approval-ux.md`
// Trace section A). The SAME Decision-17 Tier-0 dir the minted token lands
// in — aliased, not re-derived, to keep the two in one place (DRY).
const STAGING_DIR_REL = TOKEN_DIR_REL

class Tier3GateAbort extends Error {}

// Distinct from Tier3GateAbort-for-REFUSE: the approval-gate CLI ITSELF is
// broken/missing/not executable — a broken PREREQUISITE, not a policy
// rejection. Still a Tier3GateAbort subclass so the hook's fail-closed catch
// (below) aborts exactly as before; the subclass only lets tests/callers
// tell the two apart. Mirrors git-guard.ts's PreflightUnavailable exactly.
export class PreflightUnavailable extends Tier3GateAbort {}

// A GENUINE policy REFUSE from the gate CLI's non-zero exit — see the
// GateRefused header section above. Staging (`stagePendingContent`) and the
// approval-URL message rewrite are keyed STRICTLY on `instanceof
// GateRefused`, never on any other `Tier3GateAbort` (E1-E3, S12).
export class GateRefused extends Tier3GateAbort {}

// Pure path classifier. Exported for tests. `directory` is the plugin's own
// project root (the `{directory}` param every hook receives); `filePath` is
// the tool call's `output.args.filePath`, which opencode may hand back either
// absolute or relative to `directory` — both are normalized the same way
// `path.resolve` normalizes any relative reference.
export function isTier3Path(directory: string, filePath: string): boolean {
  const abs = resolve(directory, filePath)
  const rel = relative(directory, abs).split(sep).join("/")
  if (rel.startsWith("..")) return false // outside the project root entirely
  if (TIER3_EXACT_FILES.has(rel)) return true
  return TIER3_DIR_PREFIXES.some((prefix) => rel === prefix.slice(0, -1) || rel.startsWith(prefix))
}

// Find the token file to hand the gate CLI. See the TOKEN-FILE RESOLUTION
// header note: this hook does not compute or know the change_hash itself, so
// it hands the CLI the most-recently-written candidate under the
// Decision-17 token directory; an absent/empty directory resolves to a
// deterministically-nonexistent path, which `gate.py`'s own "no approval
// token present" fail-closed branch already handles. Exported for tests.
export function findLatestTokenPath(directory: string): string {
  const tokenDir = join(directory, TOKEN_DIR_REL)
  try {
    const candidates = readdirSync(tokenDir).filter(
      (f) => f.startsWith("approval-") && f.endsWith(".json"),
    )
    if (candidates.length === 0) return join(tokenDir, "approval-none.json")
    let latest = candidates[0]
    let latestMtime = statSync(join(tokenDir, latest)).mtimeMs
    for (const f of candidates.slice(1)) {
      const mtime = statSync(join(tokenDir, f)).mtimeMs
      if (mtime > latestMtime) {
        latest = f
        latestMtime = mtime
      }
    }
    return join(tokenDir, latest)
  } catch {
    return join(tokenDir, "approval-none.json")
  }
}

// Compute the EXACT resulting content this tool call will produce (plan
// Decision 20), or FAIL CLOSED if it cannot be known with certainty.
// Exported for tests. `write` hands the resulting bytes over verbatim as
// `args.content`; `edit` is not reliably reproducible out-of-band (opencode's
// fuzzy-replacer + formatter path), so a Tier-3 `edit` is REFUSED here — the
// operator must use `write` for Tier-3 changes. This is the plan's
// "refuse rather than guess" fail-closed principle applied to content.
export function resultingContentFor(tool: string, args: any): string {
  if (tool === "write") {
    const content = args?.content
    if (typeof content !== "string") {
      throw new Tier3GateAbort(
        "tier3-gate: write to a Tier-3 path carried no string `content` to " +
          "content-bind the approval token against; fail-closed",
      )
    }
    return content
  }
  if (tool === "edit") {
    throw new Tier3GateAbort(
      "tier3-gate: `edit` to a Tier-3 path is refused — opencode's edit uses a " +
        "fuzzy-replacer + formatter cascade whose resulting bytes cannot be " +
        "reproduced out-of-band, so the approval token's content-binding cannot " +
        "be verified against a guess (fail-closed: refuse rather than guess). " +
        "Make Tier-3 changes with `write` (full-file, deterministic content), " +
        "which content-binds exactly.",
    )
  }
  // Defensive: only edit/write reach here (GATED_TOOLS gate upstream).
  throw new Tier3GateAbort(
    `tier3-gate: unexpected gated tool '${tool}'; fail-closed`,
  )
}

// Run the approval-gate CLI against one target file, binding the token to the
// EXACT resulting content `resultingContent` (NOT the target's live disk
// bytes). Writes the content to a throwaway temp file under Node's own
// `os.tmpdir()` (per plan Decision 20: the content-file is a transient
// argument-passing vehicle, not a Gleipnir artifact — keeping it out of
// `.gleipnir/var/tmp/` avoids muddying the token directory the hook scans),
// passes its path as `--content-file`, and ALWAYS unlinks it in a `finally`
// so a spawn failure never leaks proposed-write bytes. Exported for the
// conformance test, which drives it against a stub `.venv/bin/python` in a
// temp dir (mirrors git-guard.ts's `runConfigScan`).
export function runGateCheck(
  directory: string,
  filePath: string,
  resultingContent: string,
): { code: number; stderr: string } {
  const python = join(directory, PYTHON_REL)
  try {
    accessSync(python, constants.X_OK)
  } catch {
    throw new PreflightUnavailable(
      `tier3-gate: python '${python}' is missing or not executable — the ` +
        `approval-gate CLI cannot run. This is a BROKEN PREREQUISITE, not a ` +
        `policy rejection; fail-closed.`,
    )
  }
  const target = resolve(directory, filePath)
  const tokenPath = findLatestTokenPath(directory)
  const scratchDir = mkdtempSync(join(tmpdir(), "gleipnir-tier3-"))
  const contentFile = join(scratchDir, "resulting-content")
  try {
    writeFileSync(contentFile, resultingContent)
    const res = spawnSync(
      python,
      [
        ...GATE_MODULE_ARGV,
        "--check",
        target,
        "--content-file",
        contentFile,
        "--token",
        tokenPath,
      ],
      { cwd: directory, encoding: "utf8" },
    )
    if (res.error) {
      throw new PreflightUnavailable(
        `tier3-gate: could not run the approval-gate CLI (${res.error.message}); ` +
          `broken prerequisite, NOT a policy rejection; fail-closed`,
      )
    }
    if (res.status === null) {
      throw new Tier3GateAbort(
        `tier3-gate: approval-gate CLI terminated by signal ${res.signal}; fail-closed`,
      )
    }
    return { code: res.status, stderr: res.stderr ?? "" }
  } finally {
    // Transient vehicle: remove the whole temp dir regardless of outcome so
    // proposed-write bytes never linger on disk.
    rmSync(scratchDir, { recursive: true, force: true })
  }
}

// Pure decision over an exit code. Exported for tests. Throws `GateRefused`
// (not a bare `Tier3GateAbort`) on any non-zero exit — the classification
// mechanism the staging branch below keys off of (P2/S12(a)). The
// return-"allow"-on-0 contract and the `REFUSED` message text are UNCHANGED
// from the pre-staging version — `GateRefused` is a `Tier3GateAbort`
// subclass carrying the identical message.
export function decideFromExit(code: number): "allow" {
  if (code === 0) return "allow"
  throw new GateRefused(
    `tier3-gate: approval-gate REFUSED (exit ${code}) — no valid fresh signed ` +
      "approval token authorises this Tier-3 write. The write was aborted. " +
      "Approve out-of-band via the tailnet approval listener " +
      "(bin/gleipnir-approval-server), then retry.",
  )
}

// The canonical UTF-8 sha256 of the exact resulting content this write will
// produce (plan Decision P2 — the load-bearing byte-identity contract: this
// MUST byte-match `src/gleipnir/approval/__main__.py`'s
// `_compute_change_hash = sha256(read_bytes())`, where the bytes were
// written by `writeFileSync(contentFile, resultingContent)`, i.e. Node's
// default UTF-8). `"utf8"` here is mandatory, not incidental. Exported for
// the unit test.
export function computeChangeHash(resultingContent: string): string {
  return createHash("sha256").update(resultingContent, "utf8").digest("hex")
}

// Persist the exact resulting content to a Tier-0 staged file the operator
// can review at `GET /approve/<hash>` (plan Decision P1, Trace section A/B).
// The envelope shape `{content, filePath, tool, staged_at}` is the ONLY
// field `content` that the hash/mint touches — `filePath`/`tool`/`staged_at`
// are display-only context for `render_review_page`
// (`src/gleipnir/approval/server.py`). `content` preserves the exact
// string; JSON-encoding the envelope does NOT change what gets hashed — the
// hash is computed over `resultingContent` itself, before it is ever
// embedded in the envelope, and the server independently re-hashes the
// loaded envelope's `content` field the same way (never the serialized
// envelope bytes). Returns the `<hash>` (the same value that keys the
// filename and the approval URL). Exported for the unit test.
export function stagePendingContent(
  directory: string,
  tool: string,
  filePath: string,
  resultingContent: string,
): string {
  const hash = computeChangeHash(resultingContent)
  const envelope = {
    content: resultingContent,
    filePath,
    tool,
    staged_at: Math.floor(Date.now() / 1000),
  }
  const stagingDir = join(directory, STAGING_DIR_REL)
  mkdirSync(stagingDir, { recursive: true })
  const stagedPath = join(stagingDir, `pending-${hash}.json`)
  writeFileSync(stagedPath, JSON.stringify(envelope))
  return hash
}

// Build the refusal message's URL tail (plan Decision P8). Reads
// `GLEIPNIR_APPROVAL_BASE_URL` at call time (not module-load time, so tests
// can toggle it per-case). One trailing slash is stripped from `base_url`
// before joining, so both `https://h.ts.net` and `https://h.ts.net/`
// normalize to the same URL. When unset, returns a graceful relative-hint
// fallback — approval readiness must never depend on this env var being
// set. Exported for the unit test.
export function buildApprovalUrl(hash: string): string {
  const base = process.env.GLEIPNIR_APPROVAL_BASE_URL
  if (base) {
    const normalized = base.endsWith("/") ? base.slice(0, -1) : base
    return `Approve at: ${normalized}/approve/${hash}`
  }
  return (
    `Approve at: <your approval listener>/approve/${hash} ` +
    "(set GLEIPNIR_APPROVAL_BASE_URL to show the full URL here)"
  )
}

export const Tier3Gate = async ({ directory }: { directory: string }) => {
  return {
    "tool.execute.before": async (
      input: { tool: string },
      output: { args: any },
    ) => {
      if (!GATED_TOOLS.has(input.tool)) return

      const filePath = output?.args?.filePath
      if (typeof filePath !== "string" || filePath.length === 0) {
        throw new Tier3GateAbort(
          "tier3-gate: edit/write call carried no filePath to classify; fail-closed",
        )
      }

      if (!isTier3Path(directory, filePath)) return

      let resultingContent: string | undefined

      try {
        resultingContent = resultingContentFor(input.tool, output.args)
        const { code } = runGateCheck(directory, filePath, resultingContent)
        decideFromExit(code)
      } catch (err) {
        if (err instanceof GateRefused) {
          const hash = stagePendingContent(
            directory,
            input.tool,
            filePath,
            resultingContent as string,
          )
          throw new GateRefused(`${err.message} ${buildApprovalUrl(hash)}`)
        }
        if (err instanceof Tier3GateAbort) throw err
        throw new Tier3GateAbort(
          `tier3-gate: unexpected error, failing closed: ${(err as Error)?.message ?? err}`,
        )
      }
    },
  }
}
