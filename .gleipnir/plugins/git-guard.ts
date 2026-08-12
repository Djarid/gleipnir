// Gleipnir git-enforcement wire-in — the config-scan gate (Tier-3 enforcement code).
//
// This opencode plugin runs the config-scoping preflight (`config-scan`) BEFORE
// any git write operation issued through the gleipnir-git broker, and THROWS to
// abort the operation if the agent roster / opencode.jsonc config is mis-scoped.
// It is the enforcement seat named in spec S-1 point 1 (`tool.execute.before`,
// "inspect typed arguments and throw to abort"), the config-integrity half of
// the layered Approach-C design (see .gleipnir/plans/git-enforcement-plugin.md).
// The COMMIT-CONTENT secret-scan is the OTHER half and lives server-side in the
// broker's commit_changes (where the staged diff is visible) — NOT here.
//
// TRUST TIER: this file is Tier-3 enforcement code — operator-authored,
// agent-unwritable. No roster agent (not even gleipnir-code) may edit it. It is
// the guard; it must not be reachable by the guarded (Axiom 2 / G-1).
//
// ALWAYS-ACTIVE (read this first — D9, operator-converged). UNLIKE sequence-gate
// (which is a pure pass-through unless a pipeline is ARMED), this gate is
// ALWAYS-ACTIVE whenever the plugin is loaded. Config integrity is a safety
// invariant that matters regardless of pipeline arming — a mis-scoped agent /
// permission config is dangerous whether or not a gated run is in progress — so
// there is NO GLEIPNIR_PIPELINE / bridge-file arming check here. Do NOT copy
// sequence-gate's arming/bridge-file guard into this plugin.
//
// WHAT IT DOES
//   * pre-tool (`tool.execute.before`): on a `gleipnir-git_commit_changes` or
//     `gleipnir-git_push_current_branch` tool call, shell out to
//     `bin/gleipnir-preflight config-scan` (the single source of truth — the
//     same fail-closed Python scan run everywhere; no TS reimplementation) and
//     act on its exit code:
//       0 = CLOSED           -> config well-scoped; allow the git op (fall through)
//       1 = REFUSE           -> config mis-scoped; THROW to abort the git op
//       2 = PROCEED_UNCLOSED -> operator --override-ack; WARN and allow (the
//                               operator's deliberate escape valve — an
//                               always-active gate must never deadlock an L2/L3
//                               operator, so exit 2 is the release)
//     any other exit / spawn failure -> FAIL-CLOSED: THROW (never silently
//     allow — mirrors sequence-gate's top-level fail-closed discipline).
//
// FAIL-CLOSED: every uncertainty (CLI missing, spawn error, unexpected exit
// code, unreadable repo) is an abort, not an allow. There is no allow-by-default
// path. The one deliberate NON-abort is exit 2 (PROCEED_UNCLOSED), which is the
// operator's own override, not an error.
//
// NOT YET CLOSED (honest scope): this enforces AT THE HOOK. This plugin file and
// the broker source both sit in agent-writable space until the S-2 mount +
// terminal closure make them structurally unreachable — so this is
// cooperative-policy, not a hard boundary, until S-2. The one real structural
// invariant today is the broker's refusal to pass a hook-bypass flag. See
// .gleipnir/plans/git-enforcement-plugin.md and decisions/broker-mcp.md.

import { spawnSync } from "node:child_process"
import { accessSync, constants } from "node:fs"
import { join } from "node:path"

// The two gleipnir-git broker write tools this gate covers. config-scan is a
// whole-config integrity check (no staged diff needed), so gating BOTH commit
// and push is correct: don't commit OR push a repo whose agent config is
// mis-scoped.
const GATED_TOOLS = new Set([
  "gleipnir-git_commit_changes",
  "gleipnir-git_push_current_branch",
])

// The out-of-framework preflight CLI. Resolved from the plugin `directory`
// param exactly as sequence-gate resolves its bridge path — never hardcoded to
// an absolute host path.
const PREFLIGHT_REL = "bin/gleipnir-preflight"

// config-scan exit-code contract (src/gleipnir/preflight/config_scan.py):
//   0 CLOSED / 1 REFUSE / 2 PROCEED_UNCLOSED.
const EXIT_CLOSED = 0
const EXIT_REFUSE = 1
const EXIT_PROCEED_UNCLOSED = 2

class GitGuardAbort extends Error {}

// Distinct from GitGuardAbort-for-REFUSE: the preflight TOOL itself is broken /
// missing / not executable — a broken PREREQUISITE, not a policy rejection.
// Still a GitGuardAbort subclass so the hook's fail-closed catch (below) aborts
// exactly as before; the subclass only lets tests/callers tell the two apart.
// Exported (alongside runConfigScan/decideFromExit) so the test can import it.
export class PreflightUnavailable extends GitGuardAbort {}

// Run `bin/gleipnir-preflight config-scan` in the repo dir and return its exit
// code. Pure-ish (does IO); exported for the golden-fixture conformance test,
// which drives it against a stub CLI in a temp dir.
export function runConfigScan(directory: string): { code: number; stderr: string } {
  const cli = join(directory, PREFLIGHT_REL)
  // Pre-check: is the preflight tool present AND executable? A non-executable or
  // missing CLI is a BROKEN PREREQUISITE, not a policy rejection — surface it
  // distinctly (still fail-closed) so it is a one-line fix, not a multi-step
  // investigation. Covers both ENOENT (missing) and EACCES (not +x) uniformly.
  try {
    accessSync(cli, constants.X_OK)
  } catch {
    throw new PreflightUnavailable(
      `git-guard: preflight tool '${cli}' is missing or not executable — run ` +
        `'chmod +x ${PREFLIGHT_REL}' (or 'git update-index --chmod=+x ${PREFLIGHT_REL}' ` +
        `to fix the committed mode). This is a BROKEN PREREQUISITE, not a policy ` +
        `rejection; fail-closed.`,
    )
  }
  const res = spawnSync(cli, ["config-scan"], {
    cwd: directory,
    encoding: "utf8",
  })
  if (res.error) {
    // Spawn still failed after the pre-check (race / exotic error) — treat as a
    // broken prerequisite too, distinct from a policy REFUSE. Fail-closed.
    throw new PreflightUnavailable(
      `git-guard: could not run '${cli} config-scan' (${res.error.message}); ` +
        `broken prerequisite, NOT a policy rejection; fail-closed`,
    )
  }
  // spawnSync sets status to null if the process was killed by a signal.
  if (res.status === null) {
    throw new GitGuardAbort(
      `git-guard: '${cli} config-scan' terminated by signal ${res.signal}; fail-closed`,
    )
  }
  return { code: res.status, stderr: res.stderr ?? "" }
}

// Pure decision over an exit code. Exported for tests. Returns:
//   "allow"  -> let the git op proceed
//   "warn"   -> let the git op proceed, but emit a warning (exit 2 override)
// and THROWS GitGuardAbort for REFUSE (1) or any unexpected code (fail-closed).
export function decideFromExit(code: number): "allow" | "warn" {
  switch (code) {
    case EXIT_CLOSED:
      return "allow"
    case EXIT_PROCEED_UNCLOSED:
      return "warn"
    case EXIT_REFUSE:
      throw new GitGuardAbort(
        "git-guard: config-scan REFUSED — the agent roster / opencode.jsonc is " +
          "mis-scoped (fail-open MCP scoping, single-holder violation, malformed " +
          "config, or similar). The git operation was aborted. Fix the finding " +
          "reported above, or the operator may re-run with --override-ack.",
      )
    default:
      // Any other exit code is unexpected for the config-scan contract —
      // fail-closed rather than guess.
      throw new GitGuardAbort(
        `git-guard: config-scan returned unexpected exit code ${code}; fail-closed`,
      )
  }
}

export const GitGuard = async ({ directory }: { directory: string }) => {
  return {
    "tool.execute.before": async (
      input: { tool: string },
      _output: { args: any },
    ) => {
      // Only gate the two gleipnir-git broker write tools; everything else is
      // out of this gate's scope and passes through untouched.
      if (!GATED_TOOLS.has(input.tool)) return

      // ALWAYS-ACTIVE (D9): no arming check. The gate runs on every gated git
      // op in every session.
      try {
        const { code, stderr } = runConfigScan(directory)
        const decision = decideFromExit(code) // throws GitGuardAbort on REFUSE / bad code
        if (decision === "warn") {
          // exit 2 PROCEED_UNCLOSED — the operator's deliberate override. Allow,
          // but surface the not-closed status rather than swallowing it.
          console.warn(
            "git-guard: config-scan reported PROCEED_UNCLOSED (--override-ack); " +
              "allowing the git operation on the operator's override.\n" +
              stderr,
          )
        }
        // "allow" (exit 0) or "warn" (exit 2): fall through, let the git op run.
      } catch (err) {
        // Fail-closed on ANY error path, not only enumerated GitGuardAborts — a
        // stray exception must abort the git op, never silently allow it.
        if (err instanceof GitGuardAbort) throw err
        throw new GitGuardAbort(
          `git-guard: unexpected error, failing closed: ${(err as Error)?.message ?? err}`,
        )
      }
    },
  }
}
