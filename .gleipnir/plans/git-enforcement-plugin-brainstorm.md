# Design Brief: Git-enforcement as an opencode plugin (git-ops workflow layer)

**Stage:** brainstorm (design exploration). **Status:** DECISION ANALYSIS
RETURNED TO ORCHESTRATOR — NOT converged. No approach selected yet; the
operator decides the material tradeoffs below via the orchestrator before this
brief is finalised and before planning proceeds.

**Author:** gleipnir-brainstorm (subagent). My `question` tool does not reach
the operator, so I have NOT converged and have NOT recorded any operator choice.
This brief presents options + a full Decision Analysis with an **advisory**
recommendation for the orchestrator to surface.

---

## Problem Statement

The operator wants git-related **enforcement controls** — the always-on
**secret-scan** and the **config-scan** (agent/config content validation) — to
run automatically at commit/push time, but has **redirected where they must
live**. They must **NOT** live in a git `pre-commit` hook and **MUST NOT** live
in CI. Both of those layers *force behaviour onto anyone using the repo*
(contributors, downstream users). Instead the controls should run as an
**opencode plugin** that fires at a **specific point in the git-ops agent's own
workflow — before any git operation** — enforcing only within the framework's
own agent surface.

**Operator's guiding principle (verbatim intent):** *"we do not force
non-Tier-3 outbreak controls onto users."* A `pre-commit` hook (via
`core.hooksPath=hooks`) and CI both impose the check on every human and every
clone of the repo. An opencode plugin bound to the git-ops tool calls enforces
**only** inside the framework's own agent workflow — the framework polices
itself, it does not police its users.

This is a **tier3-coach-shaped** problem: a control belongs in *a* layer, and
the whole question is *which* layer is correct given the redirection. The
answer is no longer "the VCS layer (hook)"; it is "the framework's own
orchestration/tool-interception surface." That surface — the opencode plugin
seat and the broker — is Tier-3 enforcement code (operator-authored,
agent-unwritable). So the output of this brainstorm is a **proposal for the
operator to converge and then author**, never an implementation by an agent.

---

## Constraints

- **Layer constraint (operator, hard):** enforcement must NOT be in a
  `pre-commit` hook and must NOT be in CI. It runs at the git-ops agent's
  workflow layer (plugin interception of the broker git tool calls), or inside
  the broker itself. Both are framework-internal, not repo/user-facing.
- **Non-forcing principle:** the control must not impose on non-framework
  users of the repo. This rules out `core.hooksPath` hooks and CI jobs for the
  *enforcement* purpose (they may survive only as opt-in human convenience —
  see Tradeoff 4).
- **Reuse existing Python logic:** secret-scan lives in
  `src/gleipnir/broker/git/guards.py` (`scan_diff_for_secrets`,
  `precommit_check`); config-scan lives in `src/gleipnir/preflight/config_scan.py`
  and is invokable as `bin/gleipnir-preflight config-scan`
  (exit codes: **0=CLOSED, 1=REFUSE, 2=PROCEED_UNCLOSED**). Reimplementing
  either in TypeScript would duplicate correctness-critical logic and invite
  drift. **Verified.**
- **Plugin precedent:** `.gleipnir/plugins/sequence-gate.ts` already uses
  `tool.execute.before`, inspects a tool call's typed args, and `throw`s to
  abort — direct precedent that a plugin can block a tool call before it runs.
  `compaction-survival.ts` is a second plugin precedent. **Verified (re-read).**
- **The git operations are broker MCP tool calls:** `gleipnir-git_commit_changes`
  and `gleipnir-git_push_current_branch` (the `gleipnir-git` FastMCP server,
  `src/gleipnir/broker/git/mcp_server.py`). A `tool.execute.before` hook keyed
  on those tool names is the natural "before any git operation" seat. **Verified.**
- **Honesty label:** pre-S-2, plugins/** and the broker source sit in
  agent-writable space; enforcement is **cooperative-policy**, not a hard
  boundary, until the S-2 mount + G-1 preflight make `plugins/**` and broker
  source OS-read-only to the agent uid (`.gleipnir/decisions/s2-g1-closure.md`).
  `sequence-gate.ts` carries the same label. The brief must not overclaim.
- **stdlib-only enforcement core:** the Python scan logic is stdlib-only by
  decision (`runtime-and-deps.md`); a shell-out preserves that, a TS reimpl
  abandons the single source of truth.

---

## Ground truth established during exploration (state plainly)

1. **The existing `hooks/pre-commit` (46 lines, active via `core.hooksPath=hooks`)**
   runs an **always-on secret-scan** on the staged `+`-added diff plus **opt-in**
   branch/data-file checks. Its header comment states enforcement lives in the
   VCS layer (the hook), NOT the broker, and that the broker cannot pass
   `--no-verify` so the agent cannot bypass it. **Verified (re-read).**

2. **CRITICAL DRIFT — the broker does NOT run `precommit_check`.** The decision
   record `.gleipnir/decisions/broker-mcp.md` (line ~34) claims *"`commit_changes`
   evaluates `guards.precommit_check` and refuses BEFORE constructing any commit
   argv (`reset HEAD` on refusal)."* **This is false against the actual code.**
   `src/gleipnir/broker/git/mcp_server.py` `commit_changes` runs a **plain
   `git commit -m …`** and imposes **NO commit policy of its own**; its module
   docstring and inline comments say so explicitly ("The broker imposes NO
   commit policy of its own"). `guards` is imported only for the **advisory**
   `protected` field in `git_status`. So today the secret-scan reaches
   agent-driven commits **only because the broker's `git commit` fires the
   installed `pre-commit` hook** — which is exactly the layer the operator now
   wants to stop relying on. This drift is material to Tradeoff 1 and must be
   surfaced. (I am a brainstorm subagent and cannot edit source or the record;
   this is flagged for the operator/orchestrator.)

3. **The broker already refuses hook-bypass** (`--no-verify`/`-n`/
   `-c core.hooksPath`) at the `_run_git` choke point — a real structural
   invariant. Force-push is structurally absent. **Verified.**

4. **Config-scan is built, tested, in use, but NOT auto-wired** to any hook or
   CI (`config-scoping-preflight.md` open items). Its own record already names
   "wiring it into a git pre-commit hook and/or CI" as a *deferred follow-on
   that needs its own convergence" — this brainstorm IS that convergence, and
   the operator's redirection changes the target away from hook/CI. **Verified.**

5. **Plugins run in the opencode (Node) process at the host cwd** — they can
   `readFileSync`, and (like any Node code) can shell out. A plugin fires for
   the tool call regardless of which agent issued it, so keying on the broker
   tool names gates the operation, not the agent identity.

---

## Approaches Considered

### Approach A: opencode plugin on `tool.execute.before`, keyed on broker git tools, shelling out to the existing Python CLIs

**Summary:** A new Tier-3 plugin (`.gleipnir/plugins/git-guard.ts`) hooks
`tool.execute.before`. When `input.tool` is `gleipnir-git_commit_changes` (and
optionally `_push_current_branch`), it runs the existing Python scan logic
(shell out to a dedicated preflight subcommand for the secret-scan over
`git diff --cached`, and to `gleipnir-preflight config-scan` for the
config-scan), and `throw`s to abort on a REFUSE/secret-found. Mirrors
`sequence-gate.ts` exactly — same seat, same throw-to-abort, same fail-closed
discipline — but keyed on the git broker tool names instead of `task`.

**Tradeoffs:**
- Pro: **Directly realises the operator's redirection** — enforcement lives in
  the framework's own agent-workflow surface (the plugin seat), fires "before
  any git operation," and imposes nothing on repo users or CI.
- Pro: **Reuses the existing, tested Python logic** via shell-out — no
  reimplementation, no drift, stdlib-only core preserved. Single source of truth.
- Pro: **Exact, proven precedent** (`sequence-gate.ts`) — same hook, same
  `throw`, same fail-closed pattern; low novelty risk.
- Pro: Enforcement is **agent-scoped by construction** — it only ever runs for
  the broker tool calls the agent uses; a human running `git commit` in a
  terminal is untouched (satisfies "don't force onto users").
- Con: **Diff visibility at hook time.** The plugin sees the tool *args*, not
  the staged tree. For the secret-scan it must obtain the staged diff itself
  (shell out to `git diff --cached`) — but `commit_changes` stages files as its
  *first* action (the broker runs `git add` then `git commit`), so at
  `tool.execute.before` the intended files may **not yet be staged**. The plugin
  would need to reproduce the broker's staging semantics (parse the `files` arg,
  or `git add -A` dry-run) to scan the right content. This is the sharpest
  design risk — analysed in Open Questions.
- Con: **Shell-out latency + environment coupling** — invokes Python
  (`.venv/bin/python`) per commit; must locate the venv/CLI reliably from the
  Node process cwd.
- Con: **Two seats now enforce git policy** (this plugin + the broker's
  hook-bypass refusal) — more surface to keep coherent; and it leaves the
  broker's own `commit_changes` still policy-free (the drift in ground-truth #2
  persists unless separately addressed).

**Estimated Scope:** 1 new Tier-3 file (`.gleipnir/plugins/git-guard.ts`),
possibly 1 new thin preflight subcommand for the staged-diff secret-scan
(`bin/gleipnir-preflight secret-scan` / `commit-scan`), tests + golden fixtures
mirroring `sequence-gate`'s. Amend `broker-mcp.md` / the pre-commit lineage
record. **Complexity: medium.**

**Risk:** medium — the staged-diff-visibility problem is real and must be solved
before this is sound; get it wrong and the secret-scan silently scans nothing
(a false-CLOSED, the worst failure mode).

---

### Approach B: move enforcement INTO the broker guard (server-side, on every broker git tool call)

**Summary:** Make the `gleipnir-git` broker actually enforce, restoring the
behaviour its decision record already (wrongly) claims. `commit_changes` calls
`guards.precommit_check(branch, staged_diff, staged_files)` **after staging but
before `git commit`**, and refuses (with `reset HEAD`) on a secret finding; and
optionally invokes the config-scan. The broker already intercepts every git
tool call server-side and already has the diff available (it can run
`git diff --cached` between its `add` and `commit` steps), so the
staged-visibility problem (Approach A's main con) **does not exist here**.

**Tradeoffs:**
- Pro: **The broker already intercepts every git write** and controls staging
  order — it is the natural, drift-free choke point; the diff is trivially
  available post-stage, pre-commit.
- Pro: **Closes the ground-truth #2 drift** — the record and code would finally
  agree; the secret-scan stops depending on an installed `pre-commit` hook (the
  layer the operator wants to stop relying on).
- Pro: **stdlib-only, no shell-out, no TS reimpl** — `guards.py` is right there;
  `precommit_check` already exists and is 96%-covered.
- Pro: Enforcement is framework-internal and agent-scoped (only broker tool
  calls) — satisfies "don't force onto users" as well as the plugin does.
- Con: **tier3-coach tension.** The prior decision lineage deliberately moved
  guard *policy* OUT of the broker into the VCS layer, to avoid AETOS-style
  false-positive lockups and to keep the broker "nearly invisible." Putting it
  back into the broker partially reverses that — and risks re-creating the
  deadlock concern (a hard refusal with no human to answer, for L2/L3). Must
  scope carefully to *safety-only, always-on* (secret-scan), keeping
  branch/data-file opt-in, to avoid the lockup this lineage warned against.
- Con: **The broker is agent-*writable* today** (pre-S-2) just like the plugin,
  so this is not more "unbypassable" than Approach A right now — but it IS the
  layer that runs regardless of the opencode plugin host, so it is arguably a
  more fundamental seat.
- Con: **Does not, by itself, match the operator's stated mechanism** ("an
  opencode plugin … part of the git-ops agent's workflow"). The operator named
  a plugin specifically; B is a legitimate *alternative the operator asked me to
  analyse*, not the mechanism they proposed. Surfacing B honestly is required;
  choosing it overrides the stated mechanism and must be an explicit operator
  decision.

**Estimated Scope:** edit `src/gleipnir/broker/git/mcp_server.py` (wire
`precommit_check` into `commit_changes`; optionally a config-scan call),
tests for the enforcing path, amend `broker-mcp.md` to match reality.
**Complexity: low-medium** (the logic exists; it is wiring + tests).

**Risk:** low-medium — well-trodden code; main risk is re-introducing the
false-positive/deadlock behaviour the lineage removed, mitigated by keeping it
safety-only + always-on and hygiene opt-in.

---

### Approach C: layered — plugin as the "before any git operation" gate (config-scan) + broker guard for the commit-content secret-scan

**Summary:** Split by *what each layer can see best*. The **plugin**
(`tool.execute.before` on `gleipnir-git_commit_changes` and
`_push_current_branch`) runs the **config-scan** — which operates over
`.gleipnir/agents/**` + `opencode.jsonc` and needs **no staged diff**, so the
plugin's arg-only visibility is not a limitation there; it `throw`s on a REFUSE
(exit 1). The **broker** runs the **secret-scan** server-side post-stage
pre-commit (Approach B's secret path), where the staged diff is available. Each
control lives in the layer where its inputs are naturally visible.

**Tradeoffs:**
- Pro: **Each check runs where its data lives** — config-scan needs only files
  on disk (plugin-friendly); secret-scan needs the staged diff (broker-friendly).
  Eliminates Approach A's staged-visibility problem for the secret-scan while
  still giving the operator a genuine plugin at the "before any git op" seat.
- Pro: Uses the config-scan CLI's exit-code contract cleanly (plugin: 0 pass /
  1 throw / 2 warn-and-proceed) and reuses `precommit_check` server-side.
- Pro: The config-scan gate (a whole-config integrity check) is arguably a
  *better* fit for the "before any git operation" framing than a per-diff
  secret-scan — you don't want to commit *any* change while the agent/permission
  config is mis-scoped, regardless of the diff content.
- Con: **Most moving parts** — two enforcement seats in two languages, two test
  suites, two records to keep coherent. Highest coordination cost.
- Con: **Scope-creep risk** (bias flag below) — "do both in both places" can be
  a way to avoid choosing; must be justified by the data-visibility argument,
  not chosen to dodge Tradeoff 1.
- Con: Still leaves the plugin unable to secret-scan (by design here), so if the
  operator's mental model is "the plugin does the secret-scan too," C reframes
  that.

**Estimated Scope:** 1 plugin (config-scan gate) + broker edit (secret-scan) +
both test suites + record amendments. **Complexity: medium-high.**

**Risk:** medium — coordination and coherence cost; two seats to reason about
for every future change.

---

## Decision Analysis

**Decision points detected:** four distinct material tradeoffs (see the four
subsections). This is an **architectural tradeoff with long-term consequences**
(where an enforcement control permanently lives), so per the auto-selection
table the primary framework is **Second-Order Thinking → Pre-Mortem**, with a
**Weighted Decision Matrix** for the multi-option mechanism choice (Tradeoff 1)
and a **Reversibility Filter** applied first.

### Reversibility Filter (applied first)

- **Tradeoff 1 (mechanism):** Two-Way Door, *leaning* one-way. A plugin or a
  broker edit can be reverted in hours, but each establishes a *precedent* for
  "where git enforcement lives" that future controls will follow — so the
  precedent is sticky even though the code is reversible. Treat as **effectively
  one-way for the precedent**, warranting the full matrix + pre-mortem.
- **Tradeoff 2 (which tools to gate):** Two-Way Door — fast-track adjustable.
- **Tradeoff 3 (shell-out vs reimplement):** One-Way-ish — a TS reimplementation
  creates a durable second source of truth that is expensive to unwind. Shell-out
  is the reversible, low-regret default.
- **Tradeoff 4 (fate of the hook + record amendment):** Two-Way Door for the
  hook (keep/retire is reversible); the record amendment is a **must** either
  way because the record currently contradicts the code (ground-truth #2).

### Weighted Decision Matrix — Tradeoff 1 (enforcement mechanism)

Options: **A** = plugin + shell-out; **B** = broker guard; **C** = layered
(plugin config-scan + broker secret-scan). Scores 0–10, weighted; cell = score×weight.

| Criterion | Weight | A (plugin) | B (broker) | C (layered) |
|---|---|---|---|---|
| Matches operator's stated mechanism (plugin at git-ops workflow) | 9 | 10 → 90 | 3 → 27 | 8 → 72 |
| Correctness of inputs (can it see what it must scan?) | 10 | 5 → 50 | 9 → 90 | 9 → 90 |
| Reuses existing Python logic, no drift | 8 | 8 → 64 | 10 → 80 | 8 → 64 |
| Fixes the record/code drift (ground-truth #2) | 6 | 3 → 18 | 10 → 60 | 8 → 48 |
| Low coordination / few moving parts | 6 | 7 → 42 | 9 → 54 | 3 → 18 |
| "Don't force onto users" (framework-internal only) | 9 | 10 → 90 | 9 → 81 | 10 → 90 |
| Avoids re-introducing broker deadlock/false-positive lockup | 7 | 9 → 63 | 6 → 42 | 7 → 49 |
| **Total** | | **417** | **434** | **431** |

**Matrix result:** near-tie, **B (434) ≈ C (431) > A (417)**. The matrix says
the two options that put the *secret-scan in the broker* (where the diff is
visible) edge out the pure-plugin option — driven almost entirely by the
"correctness of inputs" criterion (A's staged-diff-visibility problem). But
**A wins decisively on "matches the operator's stated mechanism,"** and C nearly
ties B while still giving the operator a real plugin. The scores are close
enough that this is a **judgment call for the operator, not a matrix mandate**
(anti-pattern 3: do not let 434 vs 431 vs 417 dictate).

### Second-Order Thinking (mechanism precedent)

- **A, near term:** plugin gates git ops; operator's mechanism honoured.
  **Far term:** establishes "git enforcement = an opencode plugin" as the
  framework precedent; every future git control follows suit. Second-order: the
  broker's `commit_changes` stays policy-free and the record/code drift persists
  unless separately fixed — a latent honesty gap.
- **B, near term:** broker enforces; drift closed. **Far term:** re-establishes
  the broker as a policy seat — reversing the deliberate "policy out of broker"
  lineage; second-order risk of the false-positive/deadlock lockup that lineage
  removed, unless scoped to safety-only always-on.
- **C, near term:** each check in its natural layer. **Far term:** two
  precedents coexist ("config integrity → plugin; commit content → broker"),
  which is coherent *if* documented as a principle ("enforce where the data
  lives"), but is more surface to maintain.

**Key insight:** the operator's redirection is fundamentally about **who the
control is imposed on** (framework-internal, not repo users) — and **all three**
options satisfy that (all are agent-workflow-internal; none touch CI or the
`core.hooksPath` hook's user-facing role). The *remaining* differentiator is
**where each check can actually see its inputs** — and that is what pushes the
secret-scan toward the broker (B/C) and leaves the config-scan equally at home
in a plugin (A/C). This suggests **C is the design the data argues for**, while
**A is the design the operator's words argue for**, and B is the
lowest-moving-parts correctness play that partly overrides the stated mechanism.

### Pre-Mortem (top failure modes across options)

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Plugin secret-scan scans an unstaged/empty tree → **false-CLOSED**, secret ships | H (for A) | H | Don't run secret-scan in the plugin (choose B/C for the secret path), or make the plugin reproduce the broker's exact staging before scanning |
| 2 | Broker enforcement re-creates false-positive lockup / L2-L3 deadlock | M (B/C) | M | Scope broker enforcement to safety-only, always-on (secret-scan); keep branch/data-file opt-in as today |
| 3 | Shell-out can't find `.venv`/CLI from Node cwd → fail-open or spurious fail | M | H | Fail-CLOSED on any invocation error (mirror `sequence-gate`); pin CLI path resolution from `directory` like the bridge path |
| 4 | Record/code drift (#2) left unfixed → future reader trusts a false claim | H (if unaddressed) | M | Amend `broker-mcp.md` regardless of chosen approach — this is mandatory, not optional |
| 5 | Overclaiming "unbypassable" pre-S-2 | M | M | Carry the cooperative-policy honesty label verbatim from `sequence-gate.ts`; state plugins/broker are agent-writable until S-2 |

**Verdict:** Proceed with mitigations — but the choice between A/B/C is the
operator's, because it trades "honour the exact stated mechanism" (A) against
"put each check where its inputs are visible / close the drift" (B, C).

### Bias warnings (12 detectors run)

- ⚠️ **Status Quo Bias** — the existing "enforcement in the VCS layer, not the
  broker" lineage (and the drift-claiming record) may get a free pass. The
  operator's redirection explicitly reopens it; do not defend the hook-layer
  placement on inertia. *Applied: I re-scrutinised the hook placement rather
  than assuming it.*
- ⚠️ **Scope Creep Bias** — Approach C ("do both in both layers") can be a way
  to avoid choosing between A and B. It is justified *only* by the
  data-visibility argument (config-scan needs no diff; secret-scan needs the
  diff). If that argument doesn't hold for the operator, C collapses to
  indecision — force the choice.
- ⚠️ **IKEA Effect** — the broker guard logic (`guards.py`) is internally built
  and well-covered; there's a pull to route everything through it (B) *because
  we built it*. Weighed against the operator's explicit plugin mechanism, this
  must be a merit choice, not a "use what we made" choice.
- (Also checked and not triggered: Anchoring, Confirmation, Sunk Cost,
  Availability, Bandwagon, Dunning-Kruger, Survivorship, Recency, Authority.)

### Recommendation (ADVISORY — for the operator to converge, NOT a decision)

**Recommended: Approach C (layered), with the config-scan in the plugin and the
secret-scan in the broker** — *if* the operator accepts that the secret-scan
belongs where the staged diff is visible (the broker). Rationale: it honours the
operator's stated mechanism (a real `tool.execute.before` plugin at the git-ops
workflow, gating "before any git operation" with the config integrity check),
while putting the secret-scan where it can actually see what it must scan
(closing Approach A's false-CLOSED risk *and* the ground-truth #2 drift). It
scored within 3 points of the matrix leader.

**Strong fallback: Approach A (pure plugin)** — if the operator wants a single,
uniform mechanism ("everything in the plugin") and is willing to solve the
staged-diff-visibility problem (plugin reproduces the broker's staging before
scanning, or the secret-scan runs against `git diff --cached` only for a caller
that stages first). A is the *only* option that matches the operator's words
100%.

**Not recommended as the sole mechanism: Approach B** — it is the cleanest
correctness play and closes the drift, but on its own it overrides the
operator's explicitly stated plugin mechanism, so it should only be chosen if
the operator, seeing the analysis, decides the broker seat is what they actually
want.

*This recommendation is input to the operator's convergence. I have not decided.*

---

## Material tradeoffs the ORCHESTRATOR must surface to the operator

1. **Enforcement mechanism** — (A) opencode plugin on `tool.execute.before`
   shelling out to the Python CLIs; (B) move enforcement into the broker guard
   (`commit_changes` runs `precommit_check`); (C) layered — plugin runs the
   config-scan, broker runs the secret-scan. *Advisory rec: C, fallback A. The
   key fact the operator needs: the plugin cannot easily see the **staged diff**
   at `tool.execute.before` (the broker stages files as its first action), so a
   secret-scan is safer in the broker; the config-scan needs no diff and is at
   home in the plugin.*

2. **Which git tool calls to gate** — commit only (`gleipnir-git_commit_changes`),
   or commit **and** push (`_push_current_branch`), or push only. *Advisory:
   gate the config-scan on **both** (don't push a repo whose agent config is
   mis-scoped); gate the secret-scan on **commit** (that's where content enters
   history). Two-Way Door — easily adjusted later.*

3. **How the plugin/broker invokes the existing Python scan logic** — shell out
   to `bin/gleipnir-preflight config-scan` + a (new, thin) staged-diff
   secret-scan subcommand, vs reimplement in TypeScript. *Advisory: **shell
   out** — preserves the single source of truth and the stdlib-only enforcement
   core; a TS reimplementation is a durable second source of truth prone to
   drift (a near-one-way door). Note the config-scan exit-code contract:
   0=CLOSED→pass, 1=REFUSE→throw/abort, 2=PROCEED_UNCLOSED→warn-and-proceed.*

4. **Fate of the existing `hooks/pre-commit` + the "enforcement in VCS layer"
   record** — retire the hook / keep it as an opt-in **human-facing convenience**
   / replace it. AND: the decision-record lineage that says "enforcement lives
   in the VCS layer (the hook), NOT the broker" **must be amended** because the
   operator's redirection reverses part of it — *and independently because
   `broker-mcp.md` already contains a **false claim** (ground-truth #2:
   `commit_changes` does NOT run `precommit_check`; it runs a plain `git commit`).*
   *Advisory: keep `hooks/pre-commit` as an **opt-in human convenience** (it does
   not force anyone — humans choose whether to set `core.hooksPath`; it is not
   the framework's enforcement seat anymore), and amend both `broker-mcp.md` (to
   match reality) and the pre-commit header/lineage (to record that framework
   enforcement moved to the plugin/broker workflow layer). The record amendment
   is Tier-3 and operator-authored — I cannot write it.*

---

## Honesty label (tier3-coach)

**Cooperative-policy until S-2, on every option.** The plugin seat
(`.gleipnir/plugins/**`) and the broker source (`src/gleipnir/broker/**`) are
agent-*writable* today; a `throw`/refuse is genuinely agent-*unbypassable* only
once the S-2 mount + G-1 preflight make those paths OS-read-only to the agent
uid (`.gleipnir/decisions/s2-g1-closure.md`). Until then, enforcement rests on
the roster capability denies + this discipline, exactly like `sequence-gate.ts`.
The brief must not claim any of A/B/C is a hard boundary pre-S-2. What IS real
today: the broker structurally cannot pass `--no-verify`, so whichever seat
enforces, the agent cannot bypass it via a hook-skip flag.

All three options satisfy the operator's core principle ("do not force
non-Tier-3 outbreak controls onto users"): none touches CI, and none makes the
`core.hooksPath` hook a requirement for repo users — enforcement runs only
inside the framework's own git-ops agent workflow.

## Open Questions (for gleipnir-plan, after convergence)

- **Staged-diff visibility (the crux of Approach A):** at
  `tool.execute.before` on `commit_changes`, the intended files are not yet
  staged (the broker stages as its first action). Resolve: (a) choose B/C so the
  secret-scan runs post-stage in the broker; or (b) have the plugin reproduce
  the broker's staging semantics (parse the `files` arg / `git add -A` preview)
  before `git diff --cached`. Plan must pick and justify.
- **CLI path resolution from the Node plugin** — how the plugin locates
  `.venv/bin/python` / `bin/gleipnir-preflight` from `directory` (mirror
  `sequence-gate`'s bridge-path resolution); fail-CLOSED on any error.
- **Arm/opt-out posture** — should this git-guard be default-on, or
  armed-only like `sequence-gate` (which is default-OFF, enforcing only when
  `GLEIPNIR_PIPELINE=on`)? Secret-scan is a safety invariant (argues default-on);
  config-scan REFUSE could deadlock an L2/L3 operator (argues arm-able / exit-2
  warn-and-proceed). Needs an explicit posture decision.
- **Whether to also fix the `broker-mcp.md` drift regardless of chosen approach**
  (recommended: yes, unconditionally).

## Scope Sketch

| Area | Files/Modules Likely Affected |
|---|---|
| Plugin seat (A, C) | `.gleipnir/plugins/git-guard.ts` (new, Tier-3, operator-authored) |
| Broker enforcement (B, C) | `src/gleipnir/broker/git/mcp_server.py` (`commit_changes` wires `precommit_check`) |
| Secret-scan CLI (A) | new `bin/gleipnir-preflight secret-scan` subcommand + `src/gleipnir/preflight/` |
| Config-scan reuse (A, C) | `bin/gleipnir-preflight config-scan` (exists; invoked, not modified) |
| Existing hook | `hooks/pre-commit` (retire / keep as opt-in human convenience) |
| Tier-3 records (operator-authored) | amend `.gleipnir/decisions/broker-mcp.md` (fix drift), pre-commit lineage, possibly new `git-enforcement-seat.md` |
| Tests | plugin golden-fixture tests (mirror `tests/` for `sequence-gate`); broker enforcing-path tests |
