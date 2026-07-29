# Design Brief: Pointy git + PM broker MCP servers for Gleipnir

> **Status of this brief.** The material design decisions here are **already
> operator-converged** (via the orchestrator). This brief *records* them with
> verified citations; it does not re-decide them. The `## Decision Analysis`
> section marks the converged items as **RESOLVED** so the orchestrator does not
> re-surface them. Verification (Explore) confirmed every cited fact — see
> "Citation verification" below. No genuinely new material operator tradeoff was
> found; one Link-time technical call is recorded as an open question.

## Architect

**Problem (one sentence).** Gleipnir's `git-ops` and `project-mgr` roles today
do their work through a raw-`git` bash allowlist and a not-yet-existent PM
namespace, which the roster itself flags as the unsound **E-1 seam** (pattern
denies are best-effort *detection*, not *prevention*); Gleipnir needs two
**pointy, purpose-scoped MCP broker servers** — influenced by AETOS's
`aetos-git` / `aetos-pm` pattern, not copied wholesale — that move the guard
from bash-pattern matching to **structural refusal in code**, while keeping the
tool surface deliberately minimal so it does not contaminate agent context.

**User.** The `git-ops` and `project-mgr` roster agents (and, behind them, the
orchestrator sequencing the `git` pipeline stage), plus the operator who owns
the trust-surface decision.

**Measurable success criteria.**
- Two MCP servers exist and register in `opencode.jsonc` under `mcp.<name>`:
  `gleipnir-git` (4 tools) and `gleipnir-pm` (4 tools) — no more.
- `git-ops`'s force-push **bash-pattern denies** (`"git push --force*": deny`,
  `"git push -f*": deny`, `git-ops.md:32-33`) are replaced by a guards module
  that **never constructs a force-push argv** and refuses protected-branch /
  secret-bearing commits structurally in Python.
- `runtime-and-deps.md` is amended to carve the brokers out of the
  "enforcement core" stdlib-only scope and to record the `mcp` dependency (and,
  if the planner confirms it is needed, `python-dotenv`) as a **justified,
  isolated, out-of-core** third-party dependency — per the policy that file
  already states (lines 42-44).
- The pointy scope holds: git = `git_status`, `git_diff`, `commit_changes`,
  `push_current_branch`; PM = `issue_create`, `issue_update`, `issue_comment`,
  `issue_close`. Notify is **deferred** (would add `slack-sdk`).

**Constraints.** See next section.

## Constraints

- **Influence, don't steal.** AETOS `aetos-git`/`aetos-pm` are the *pattern*
  (tool shape, guard structure, platform split) — not a code/dependency import.
  (Operator: "influence, don't steal!")
- **Pointy scope.** "Specific, pointy MCPs to not contaminate the [context] more
  than necessary." opencode's own docs warn MCP servers add to context and
  recommend care about which servers are used — the reason 4 tools each, not
  AETOS's ~21/~27.
- **Trust-surface policy.** `runtime-and-deps.md` mandates stdlib-only for the
  **enforcement core** (G-3.1 verifier, G-5 engine, G-4 bus/ledger,
  memory-write pipeline) and already excludes the TS hook layer. A new
  third-party runtime dependency "requires a recorded justification here and
  enters the S-2 trusted surface explicitly — it is a decision, not a
  convenience" (lines 42-44). Adopting `mcp` (Option B) triggers exactly this.
- **Broker single-holder (G-2 / S-1.3.1).** Credentials/push live only with
  `git-ops`; the PM token surface only with `project-mgr`. The brokers must not
  widen who holds credentials.
- **PM scope already fixed.** `project-mgr.md:33` declares "Issue create /
  update / comment / close, plus time tracking. Milestones and releases are
  deferred." The 4-verb PM broker matches this exactly.
- **Runtime.** Python >= 3.11 (matches `pyproject.toml` and the core language
  decision). MCP servers launched by opencode as stdio subprocesses.

## Trace (artifacts and where they live)

- **Source of truth for the servers:** new package(s) under
  `src/gleipnir/broker/` (exact module layout is an open question — Link-time
  call for the planner).
- **Guard module:** a Gleipnir `guards`-style module influenced by AETOS
  `git/guards.py` (`is_protected_branch` + `SECRET_PATTERNS` +
  `scan_diff_for_secrets`, wired into a `commit_changes` pre-commit gate). The
  structural refusal — no force-push tool exists to call — is the concrete E-1
  answer.
- **Config integration:** `opencode.jsonc` gains an `mcp` block
  (`mcp.gleipnir-git`, `mcp.gleipnir-pm`, each `type:"local"`, `command:[...]`,
  `environment:{...}`); per-agent tool scoping via `tools:{"name*":true}`.
- **Dependency record:** `runtime-and-deps.md` amendment (Tier-3, operator-owned
   — this brief *names* the amendment; it does not write it).
- **Roster edits:** `git-ops.md` (drop the two bash force-push pattern denies in
  favour of the broker tools) and `project-mgr.md` (bind to the PM broker) — also
  Tier-3, operator-owned; named here, not written.

**Integrations map.** opencode → stdio subprocess (`python -m
gleipnir.broker.git` / `.pm`) → guards module → `git`/platform REST. Platform
token via `GITLAB_TOKEN`/`GITHUB_TOKEN` env (AETOS `pm/platform.py` pattern),
supplied by opencode's `environment` block.

**Edge cases.** Commit attempted on a protected branch (refuse); secret in the
staged diff (refuse, redacted finding); force-push (no tool exists — cannot be
requested); PM call with no platform token (structured error, no crash);
offline (PM broker is stateless for 4 verbs — no local cache, see open
questions).

## Link (validated before building — the Explore/verification pass)

Every cited fact was re-read from the actual files this session. **Citation
verification results:**

| # | Claim | Verified against | Result |
|---|-------|------------------|--------|
| 1 | Gleipnir has ZERO MCP servers | `opencode.jsonc` (whole file) | ✅ confirmed — no `mcp` block; the only `mcp` string matches are in `gotcha/SKILL.md` prose |
| 1 | `git-ops` uses a bash git allowlist, not a broker | `git-ops.md:19-33` | ✅ confirmed |
| 1 | E-1 seam flagged: "not an argument policy… do not treat as sound" | `git-ops.md:52-58` | ✅ confirmed (verbatim) |
| 2 | `aetos-git` MCP built with `from mcp.server.fastmcp import FastMCP` | `git/mcp_server.py:53` | ✅ confirmed (line 53) |
| 2 | `aetos-pm` MCP built with FastMCP | `pm/mcp_server.py:50` | ✅ confirmed (line 50) |
| 2 | stdio transport | `git/mcp_server.py:713` (`mcp.run(transport="stdio")`) | ✅ confirmed (line 713) |
| 2 | per-package deps: `mcp>=1.0.0`, `python-dotenv>=0.19.0` | `packages/git/pyproject.toml:17-21`, `packages/pm/pyproject.toml:17-21` | ✅ confirmed (both) |
| 3 | `is_protected_branch()` reads `AETOS_GIT_PROTECTED_BRANCHES`, default `main,master` | `git/guards.py:23-35` | ✅ confirmed |
| 3 | `SECRET_PATTERNS` (Slack/AWS/private key/GitHub/GitLab/OpenAI/Google/password) + `scan_diff_for_secrets()` | `git/guards.py:42-112` | ✅ confirmed (14 patterns; also Google API key + OAuth beyond the cited list) |
| 3 | combined pre-commit gate wired into `commit_changes` | `git/guards.py:209-254` (`pre_commit_checklist`) + `git/mcp_server.py:229-247` | ✅ confirmed — refuses on protected branch / secrets / data files |
| 4 | git tool names `commit_changes`, `push_current_branch` | `git/mcp_server.py:230,251` | ✅ confirmed (Gleipnir reuses these two names) |
| 4 | AETOS git ~21 tools, PM ~27 tools | `git/mcp_server.py:4` (docstring "21 tools"), `pm/mcp_server.py:4` ("27 tools") | ✅ confirmed (docstrings say 21/27; operator's "~25/~28" is a close approximation — noted, not a discrepancy) |
| 4 | PM platform pattern: GitLab/GitHub REST via token env + SQLite cache | `pm/mcp_server.py:15,50-53` (`store`, `platform` imports) | ✅ confirmed |
| 5 | stdlib-only for enforcement core; TS layer excluded; new dep = recorded decision | `runtime-and-deps.md:3-6,25-27,42-44` | ✅ confirmed (verbatim) |
| 6 | `pyproject.toml` `dependencies = []` (stdlib-only) | `pyproject.toml:8` | ✅ confirmed |
| 6 | `mcp` not installed | prior-session `import mcp` failure (not re-run this session) | ⚠️ not re-verified this session — inherited from research; consistent with `dependencies = []` |
| 7 | opencode MCP config shape (`mcp.<name>`, `type:"local"`, per-agent `tools`) | opencode docs (fetched prior session) | ⚠️ not re-fetched this session — inherited; matches `opencode.jsonc` `$schema` |

**Two minor notes (not discrepancies):** (a) AETOS docstrings say **21 / 27**
tools, vs the operator's "~25 / ~28" — an approximation, immaterial to
Gleipnir's fixed 4+4 scope. (b) `guards.py` includes Google API-key/OAuth
patterns and a data-file check beyond the cited enumeration — a *superset* of
what was cited, so the pattern is at least as rich as described.

## Propose (the A/B/C recap — for the record; already converged on B)

### Approach A: Pure-stdlib hand-rolled JSON-RPC MCP server

**Summary:** Implement the MCP stdio handshake by hand in stdlib only; no
`mcp`/FastMCP dependency.

**Tradeoffs:**
- Pro: zero trusted-surface growth — fully consistent with the existing
  stdlib-only rule; nothing new enters the S-2 boundary.
- Pro: complete control over the wire protocol; no version-drift risk from an
  external SDK.
- Con: substantially more code to own, test, and keep conformant with the MCP
  spec as it evolves; the handshake/protocol edge cases are exactly the kind of
  low-value plumbing that buys nothing per the framework goal.

**Estimated Scope:** `src/gleipnir/broker/**` + a hand-written JSON-RPC layer;
medium-to-high complexity.
**Risk:** medium — protocol-conformance bugs; ongoing maintenance burden.

### Approach B: Adopt the `mcp` SDK (FastMCP), isolated & out-of-core — **SELECTED**

**Summary:** Use `from mcp.server.fastmcp import FastMCP` over stdio (the AETOS
pattern), declared as a **justified, isolated** dependency explicitly carved
**out of the enforcement-core stdlib-only scope**.

**Tradeoffs:**
- Pro: battle-tested handshake; far less code to own; matches the influencing
  pattern directly, lowering implementation risk.
- Pro: the brokers are *not* enforcement core (they hold no G-3/G-5/G-4/memory
  logic), so carving them out is principled, not a loophole — and
  `runtime-and-deps.md` already anticipates exactly this ("a decision, not a
  convenience").
- Con: grows the trusted surface with `mcp` (+ possibly `python-dotenv`) — must
  be **recorded** in `runtime-and-deps.md`, never silent.

**Estimated Scope:** `src/gleipnir/broker/**` + `runtime-and-deps.md` amendment
+ `opencode.jsonc` `mcp` block + roster edits; medium complexity.
**Risk:** low-to-medium — dependency-surface growth (mitigated by the recorded
decision + broker-vs-core boundary).

### Approach C: Keep raw bash git, add only a stdlib argument-policy wrapper

**Summary:** No MCP transport; wrap `git` invocation in a stdlib argument policy
that structurally refuses dangerous argv.

**Tradeoffs:**
- Pro: smallest change; no new dependency, no MCP context cost.
- Pro: still upgrades the E-1 pattern-deny to a structural argument check.
- Con: does **not** deliver the "pointy MCP / credential-broker" story the
  operator asked for; no tool surface, no PM broker, no platform split — leaves
  the broker-as-tool goal unmet.

**Estimated Scope:** a wrapper module; low complexity.
**Risk:** low technically, but **fails the actual objective**.

## Selected Approach — CONVERGED (operator, via orchestrator)

**Choice: Approach B.** Adopt the `mcp` SDK (FastMCP) as a declared, isolated,
**out-of-enforcement-core** dependency.

**Scope: git + PM brokers only — CONVERGED.**
- `gleipnir-git`: **4 tools** — `git_status`, `git_diff` (read);
  `commit_changes`, `push_current_branch` (write, gated by an influenced-from-
  AETOS guards module: protected-branch refusal + secret-scan pre-commit gate,
  structural, with no force-push tool ever constructed).
- `gleipnir-pm`: **4 tools** — `issue_create`, `issue_update`, `issue_comment`,
  `issue_close` — matching `project-mgr.md:33`.
- **Notify DEFERRED — CONVERGED.** Would pull in `slack-sdk` (a second new
  dependency); out of scope. Matches `notify.md`'s existing "authored, not yet
  closed" posture, unchanged by this feature.

**Rationale (why B over A and C).** B delivers the pointy-MCP / credential-broker
objective (which C cannot) at a fraction of A's code-ownership cost, and the
one real downside — trusted-surface growth — is exactly the situation
`runtime-and-deps.md:42-44` already provides for: record the dependency as a
justified decision and admit it to the S-2 surface explicitly. The brokers are
not enforcement core, so the stdlib-only rule is amended in scope, not violated.

## Decision Analysis

**Framework used:** Reversibility Filter → Second-Order Thinking (architectural
tradeoff: adopting a third-party runtime dependency into a stdlib-only project is
a long-horizon trust-surface decision). Recorded here for provenance; the
decision itself is **already resolved by the operator**, so this analysis is
documentation, not a live prompt.

**Analysis results:**
- *Reversibility:* Two-Way-Door-leaning. Reversal cost is moderate — removing
  `mcp` later means reverting to Approach A's hand-rolled transport, but the
  guard module, tool shape, and roster wiring survive intact. Not a one-way door
  (no data migration, no external lock-in, no public commitment).
- *Second-order (near term, 3-6 mo):* first-order — E-1 pattern-denies replaced
  by structural refusal; broker tool surface exists. Second-order — `git-ops`
  loses its raw-bash force-push footgun entirely (no argv to construct).
- *Second-order (far term, 1-2 yr):* first-order — `mcp` sits inside the S-2
  trusted surface and must be audited/pinned like any dependency. Second-order —
  precedent set that non-core packages *may* take justified deps; mitigated
  because the boundary ("enforcement core = stdlib-only; brokers = recorded
  deps") is written down, not implicit. Key insight: the risk is **scope
  creep of the exception**, not this dependency itself — the
  `runtime-and-deps.md` amendment must draw the core/non-core line sharply.

**Bias warnings:**
- ⚠️ *Bandwagon Effect (low confidence):* "AETOS uses FastMCP" is influence, not
  justification. **Mitigation already in the framing:** the operator explicitly
  said "influence, don't steal," and B was chosen on code-ownership + objective-
  fit grounds, not popularity. Noted and cleared.
- ⚠️ *IKEA Effect (checked, not triggered):* the stdlib-only rule could bias
  toward the hand-rolled Approach A ("we build our own"). The analysis weighed A
  fairly and rejected it on maintenance cost — the in-house option was *not*
  overvalued. No warning raised.
- No other detectors triggered.

**Status of the decision:** **RESOLVED — operator-converged via the
orchestrator. Do NOT re-surface.**
- Approach = **B** (adopt `mcp`/FastMCP, isolated, out-of-core) — RESOLVED.
- Scope = **git + PM brokers, 4 tools each** — RESOLVED.
- Notify = **deferred** — RESOLVED.

**Genuinely new material tradeoff discovered during verification:** **None.**
The one item that surfaced — whether the broker itself shells out to `git` via
`subprocess` (as AETOS does) or uses a git library, and precisely how the
credential stays unreachable — is a **Link-time technical call** under the
already-converged "structural refusal / G-2 single-holder" decision, not a new
*material operator* tradeoff. It is recorded below as an open question for the
planner, not flagged as blocking.

## Open Questions (for the planner — mechanical/Link-time, not new operator decisions)

- **Package/module layout under `src/gleipnir/broker/`** — e.g.
  `broker/git/` + `broker/pm/` + a shared `broker/guards.py`, vs flat modules.
  Mechanical; planner's call.
- **`python-dotenv` — actually needed?** AETOS bundles it, but its own
  `_load_dotenv` is a hand-rolled stdlib fallback (`git/mcp_server.py:33-51`)
  and opencode launches the subprocess with an `environment:{...}` block that
  supplies env vars directly. Recommendation: **likely not needed** — prefer the
  stdlib `os.environ` path and add `python-dotenv` only if a standalone-dev
  convenience is required. If added, it too must be recorded in
  `runtime-and-deps.md`. Planner to confirm.
- **PM broker local cache?** AETOS PM uses SQLite (`store.py`) for offline
  fallback. For just 4 stateless verbs, recommendation: **no cache — keep the
  PM broker stateless.** Flag as a Link-time technical call, not a material
  tradeoff.
- **How the broker constructs git operations** — `subprocess` to `git` (AETOS
  pattern) vs a library; and the exact mechanism by which the push credential
  stays unreachable from in-sandbox code (ties to the still-unbuilt S-2 boundary
  and E-1 real fix). Structural-refusal decision is converged; the *mechanism*
  is the planner's under G-2.
- **`runtime-and-deps.md` amendment wording** — Tier-3, operator-authored. This
  brief *names* the required amendment (carve brokers out of enforcement-core
  scope; record `mcp` as a justified dependency); the operator persists it.
- **Protected-branch env var name** — Gleipnir equivalent of
  `AETOS_GIT_PROTECTED_BRANCHES` (e.g. `GLEIPNIR_GIT_PROTECTED_BRANCHES`),
  default `main,master`. Mechanical.

## Assemble (intended build order — sketch for the planner)

1. Operator persists the `runtime-and-deps.md` amendment (dependency decision
   must land before the dep is introduced).
2. `broker/guards.py` (protected-branch + secret-scan), with tests, first —
   it is the correctness arbiter for the write path.
3. `gleipnir-git` server (4 tools) wiring the guard into `commit_changes`.
4. `gleipnir-pm` server (4 tools), stateless, token-env platform client.
5. `opencode.jsonc` `mcp` block + per-agent `tools` scoping.
6. Roster edits: drop `git-ops.md` force-push bash denies (superseded by the
   broker's structural refusal); bind `project-mgr` to the PM broker.

## Stress-test (acceptance checks the result will be validated against)

- `commit_changes` **refuses** a commit on a protected branch (structurally, not
  by bash pattern) — test with `main`/`master` and a custom protected list.
- `commit_changes` **refuses** a staged diff containing any `SECRET_PATTERNS`
  match, returning a redacted finding.
- **No force-push is possible** — there is no tool that constructs a
  `--force`/`-f` argv anywhere in the broker.
- `gleipnir-git` exposes **exactly** `git_status`, `git_diff`, `commit_changes`,
  `push_current_branch` — no more.
- `gleipnir-pm` exposes **exactly** `issue_create`, `issue_update`,
  `issue_comment`, `issue_close` — no more.
- Both servers register in `opencode.jsonc` and are per-agent scoped so the
  brokers add minimal context surface.
- The enforcement-core stdlib-only conformance check (the candidate C-3 meta-test
  in `runtime-and-deps.md:58-61`) still passes — i.e. the `mcp` import lives only
  in `broker/**`, never in the core, and the `runtime-and-deps.md` amendment
  records it.
- Notify is untouched (no `slack-sdk` introduced).
