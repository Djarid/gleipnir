# Design Brief: S6 — Broker / credential isolation (G-2) reachability from a pi extension

> **Status: NOT CONVERGED — Decision Analysis only (this is a `gleipnir-brainstorm`
> subagent; its `question` tool cannot reach the operator, L-C6).** The
> `## Decision Analysis` below is the INPUT to the operator's convergence (per
> K-3): options + framework + bias check + recommendation, deciding NONE. The
> orchestrator surfaces D-S6-N to the operator via `question`; the operator's
> converged choices are then recorded in `## Selected Approach` (currently
> empty, pending convergence). `gleipnir-plan` plans only from the converged
> brief.
>
> **This brief RESOLVES Open-Q3** (blocked since S2, never durably resolved):
> the reach mechanism IS confirmed viable and is grounded in primary-source
> hands-on Explore this session (per L-C36), not the build-order's summary.

## Open-Q3 resolution — one sentence up front

**A viable reach mechanism IS found: a pi extension can reach the existing
Python `mcp_server.py` git/pm brokers, and the pi SDK offers TWO first-party
primitives to do so (a self-authored custom tool whose `execute` handler
spawns/relays to the broker as an MCP-over-stdio subprocess, OR — for stronger
isolation — the first-party `runRpcMode`/`pi --mode rpc` process boundary),
PLUS a proven third-party `pi-mcp-extension` that already does exactly this
via an `mcp.json` `mcpServers` config; the build-order's "no opencode-style
`mcp:` client config exists" claim is thereby half-refuted — no SDK-native
DECLARATIVE `mcp:` block exists, but MCP-client reachability itself is a
solved, first-party-expressible capability, and in every viable mechanism the
credential can live ONLY in the spawned broker subprocess's `env`, never in
the calling pi role's env/heap (G-2 single-holder preserved).**

## Problem Statement

S6 must make the **inert** `git-ops.brokerTools = ["gleipnir-git_*"]` entry in
`pi-package/src/roleTable.ts` (the S2 "inert declared name" placeholder, `pi-dev-replatform-s2.md`
L95 Micro-decision) into a REAL, reachable capability: the `git-ops` role (and
`project-mgr` for the pm namespace, held in `customTools` per S2's P2 modelling)
must be able to invoke the existing Python brokers —
`src/gleipnir/broker/{git,pm}/mcp_server.py` — WITHOUT the calling role ever
holding the underlying credential (the platform token for pm; ambient git push
credentials for git). This preserves the **G-2 single-holder clause** (only one
role reaches each broker namespace) and leaves room for the **E-1
argument-policy seam** (the broker itself already screens hook-bypass flags at
its `_run_git` choke point; S6 must not undermine that).

The build-order (`pi-dev-replatform-build-order.md` L172-186) flagged S6 as
**BLOCKED on Open-Q3** because the surveyed SDK exports "show no opencode-style
`mcp:` client config," and named three candidate mechanisms — documented MCP
client / RPC / custom-tool socket wrapper — none confirmed. This brief performs
the hands-on Explore the block demanded and resolves which are viable.

## The brokers' ACTUAL transport (read directly this session — decisive)

Both brokers are **MCP-over-stdio servers** (not sockets, not HTTP):

- `src/gleipnir/broker/git/mcp_server.py` L507-508: `mcp.run(transport="stdio")`
  via `FastMCP("gleipnir-git")`. Four tools: `git_status`, `git_diff` (read),
  `commit_changes`, `push_current_branch` (write). The one hard invariant
  (no hook-bypass: `--no-verify`/`-n`/`-c core.hooksPath` refused at `_run_git`)
  is enforced INSIDE the Python process — a reach mechanism cannot weaken it.
  Git push credentials are **ambient** (git's own credential helper / SSH
  agent / `~/.git-credentials`), reached only by the broker subprocess.
- `src/gleipnir/broker/pm/mcp_server.py` L147-148: `mcp.run(transport="stdio")`
  via `FastMCP("gleipnir-pm")`. Four tools: `issue_{create,update,comment,close}`.
  **Credential is `GITLAB_TOKEN`/`GITHUB_TOKEN` read from the broker process's
  own `os.environ`** (L11-13, `platform.py`) — "env-injected by opencode; no
  python-dotenv." This is the load-bearing fact for credential isolation: the
  token is read from the *broker subprocess's* environment, so if that env is
  populated ONLY in the spawned child and never in the pi role's process, the
  role never holds the secret.

**Why MCP-over-stdio changes the analysis:** the build-order's third candidate
was a "custom-tool **socket** wrapper." But the brokers are **stdio** servers —
spawned as `python -m gleipnir.broker.git.mcp_server` with the MCP JSON-RPC
handshake over the child's stdin/stdout. So "reach a broker" means "be an
MCP-over-stdio *client* to a spawned subprocess," which is exactly what
`pi-mcp-extension` does and exactly what a self-authored custom-tool `execute`
handler can do in Node. No socket server needs to be added to the brokers.

## The pi SDK reach surface (verified against primary source this session)

Per L-C36 (verify hands-on against primary source, not the build-order's
summary). The SDK is a `"*"` peer-dep (`pi-package/package.json`), not vendored
locally, so verification is against pi.dev / earendil-works/pi primary docs:

| SDK primitive | Verified fact | Source |
|---|---|---|
| Custom tool `execute` handler | `pi.registerTool({name,label,description,parameters,execute})` / `defineTool()`; `execute(toolCallId, params, signal, onUpdate, ctx)` runs arbitrary Node — can spawn a subprocess or open a stream | `docs/sdk.md` §Custom Tools; `docs/extensions.md` §Key capabilities |
| Extension spawns subprocess | Extensions can register tools that connect to external processes; `pi-mcp-extension` spawns **stdio MCP subprocesses** with per-server `command`/`args`/`env` | `docs/extensions.md`; `pi-mcp-extension` package page |
| **`runRpcMode` (first-party!)** | `runRpcMode(runtime)` is a **documented SDK export**; CLI `pi --mode rpc --no-session`. SDK's own guidance: **"RPC mode is preferred when: you want process isolation"** | `docs/sdk.md` §Run Modes / §RPC Mode Alternative / §Exports |
| MCP client extension (3rd-party) | `pi-mcp-extension` v1.5.0 (11K/mo): "Connect Pi to any MCP server… stdio subprocesses, streamable-http, sse"; config `~/.pi/agent/mcp.json` or `.pi/mcp.json` with `mcpServers:{ name:{command,args,env,transport} }`; registers tools as `mcp_<server>_<tool>` | `pi-mcp-extension` package page |
| MCP adapter (3rd-party) | `pi-mcp-adapter` v2.28.0 (607.9K/mo) proves the pattern at scale; "register any MCP tool as a native pi tool" | `pi-mcp-adapter` package page |
| First-party stance | earendil issue #563 "Add MCP extension example" — **closed** because `nicobailon` shipped `pi-mcp-adapter`; earendil chose NOT to ship a first-party MCP example, deferring to the ecosystem package | GitHub earendil-works/pi#563 |
| `setActiveTools` | Runtime tool add/remove (`pi.setActiveTools`) — how the MCP extension activates/deactivates bridged tools without churn | `docs/sdk.md`; issue #563 |
| Session state | `pi.appendEntry()` (survives restart) for any extension-held state | `docs/extensions.md` |

**The build-order's specific claim, adjudicated:** "the surveyed pi SDK exports
show no opencode-style `mcp:` client config" (L46, L179). **VERDICT: literally
true but materially misleading as a blocker.** There is no SDK-native
*declarative* `mcp:` config block the way opencode's `opencode.jsonc` has one.
BUT MCP-client reachability is a first-class, proven capability reachable three
ways (self-authored custom tool; first-party `runRpcMode`; third-party
`pi-mcp-extension`'s `mcp.json`). The absence of a declarative block is NOT the
absence of reachability — the block is replaced by IMPERATIVE registration in an
extension. Open-Q3's real content ("CAN a pi extension reach the brokers, and
how, without leaking the credential") is answered YES.

## Credential-isolation mechanism (the G-2-preserving core, common to all viable options)

For EVERY viable option below, the credential-isolation design is the same
shape and it is SOUND:

1. The credential (`GITLAB_TOKEN`/`GITHUB_TOKEN`; git push creds) is injected
   **only into the spawned broker subprocess's environment** — the `env:{}` map
   of the stdio-spawn (whether from `mcp.json`, or the `child_process.spawn`
   options inside a self-authored custom tool, or the RPC-subprocess launch).
2. The pi extension process (and therefore the calling role's heap/env) **never
   contains the token**. The role calls a tool (`gleipnir-git_commit_changes`);
   the tool relays MCP JSON-RPC to the child over stdin/stdout; the child reads
   its OWN `os.environ["GITHUB_TOKEN"]` (exactly as `platform.py` already does)
   and makes the REST/git call. The token crosses no boundary back to the role.
3. **G-2 single-holder is preserved at the reachability layer, not just the
   table layer:** only the role whose capability table grants the broker
   namespace can invoke the relaying tool (S2's `canUse` gate + the `tool_call`
   block hook already enforce this); no other role can name the tool. The git
   broker's own `_run_git` hard invariant (no `--no-verify`/hooksPath bypass)
   stays intact because the reach mechanism only *relays* MCP calls to the
   unmodified Python server — it cannot inject argv past the broker's screen.
4. **This is strictly BETTER than the opencode status quo**, where the token was
   env-injected by opencode into the broker's environment. The pi re-expression
   keeps the identical "token only in the broker child's env" property; the
   reach mechanism does not need to see it.

The one credential-isolation *sharp edge* to flag: the pi extension process is
the one that SPAWNS the child, so it is the process that must SET the child's
`env`. It can do so by **passing through** a value from its own environment
(then the value transits the extension process momentarily — weaker) OR by
having the child inherit from a launch context the extension never reads (e.g.
the operator's shell env inherited by `spawn` without the extension reading it,
or a credential the child fetches itself from a keychain). The stronger designs
(D-S6-3) keep the extension from ever reading the secret even to forward it.

## Approaches Considered (the overarching S6 reach-mechanism shape)

Three genuinely distinct overall strategies. As with S5, the sub-decisions
(D-S6-1..5) are then analysed individually because each is separable.

### Approach A: Self-authored first-party custom-tool MCP-stdio client (no new dependency)

**Summary:** Gleipnir writes its own `pi-package/src/broker/` extension that
registers `gleipnir-git_*` / `gleipnir-pm_*` custom tools whose `execute`
handlers are a **minimal MCP-over-stdio client** (hand-rolled JSON-RPC over
`child_process.spawn("python", ["-m","gleipnir.broker.git.mcp_server"], {env})`,
or Node's `@modelcontextprotocol/sdk` client if a dependency is acceptable),
relaying the role's tool call to the spawned Python broker and returning its
result. The child's `env` carries the credential; the extension does not.

**Tradeoffs:**
- Pro: **Zero third-party runtime dependency** if hand-rolled (honours the
  stdlib-only-core / trust-surface-minimisation posture, `runtime-and-deps.md`)
  — the whole reach path is Gleipnir-owned auditable code inside the S-2 boundary.
- Pro: **Tightest G-2 binding** — the tool is registered only for the sole-holder
  role; the same `tool_call` block hook + `canUse` that gate every other tool
  gate this one; the inert `gleipnir-git_*` name becomes real with no config
  surface an untrusted project could tamper with.
- Pro: Reuses the brokers UNCHANGED (they already speak MCP-over-stdio); no
  socket server, no Python edits.
- Con: We write and maintain an MCP-stdio client (JSON-RPC framing, lifecycle,
  cancellation) — non-trivial if fully hand-rolled; the `pi-mcp-extension`
  feature list (pagination, reconnection, health checks, `list_changed`) shows
  the corners a naive client skips. Mitigated: our brokers are a FIXED, tiny
  4-tool surface we control — we need only the `initialize` + `tools/call`
  subset, not the full generic client.
- Con: In-process spawn means the credential-bearing child is a child of the pi
  extension process (see D-S6-3 on how tightly the env is scoped).

**Estimated Scope:** `pi-package/src/broker/{gitBroker,pmBroker,mcpStdioClient}.ts`
+ tests; roleTable `brokerTools`/`customTools` wiring already present.
Complexity: **medium-high** (the stdio client is the cost).
**Risk:** **medium** — correctness of a self-authored MCP client; mitigated by
the fixed 4-tool broker surface and golden round-trip tests.

### Approach B: Adopt the third-party `pi-mcp-extension` with an `mcp.json` config

**Summary:** Install `pi-mcp-extension` (or `pi-mcp-adapter`) as a package
peer/dependency; declare the two brokers in `.pi/mcp.json` `mcpServers` with
`command:"python"`, `args:["-m","gleipnir.broker.git.mcp_server"]`,
`transport:"stdio"`, and `env:{GITHUB_TOKEN:...}`. The extension bridges each
broker tool as `mcp_gleipnir-git_<tool>`; S2's role table grants those names to
the sole-holder role.

**Tradeoffs:**
- Pro: **Least code** — a proven, 11K/mo (or 607.9K/mo for the adapter),
  MIT, spec-compliant MCP client does all the framing/lifecycle/reconnection.
- Pro: Matches the "established `mcp.json` format used by Claude Code and other
  harnesses" (issue #563) — familiar, documented config surface.
- Pro: The per-server `env:{}` block is exactly the credential-isolation lever
  we need (token only in the child's env).
- Con: **A third-party runtime dependency enters the enforcement trust surface**
  — directly against `runtime-and-deps.md`'s stdlib-only-core / "fewer
  dependencies = smaller trusted surface to audit = directly serves G-1/G-2."
  The MCP client would be relaying the *most sensitive* capability (git push,
  issue writes) through code Gleipnir does not own or audit line-by-line.
- Con: **`mcp.json` is a NEW enforcement-config surface** an untrusted project
  could carry (`.pi/mcp.json` is project-scoped). This collides with the S7
  preflight/G-1 concern that "resources load only after project trust" — a
  project-supplied `mcp.json` could point a broker `command` at attacker code,
  or add a rogue server. The stage-role-map Axis-2(a) `E` set would have to grow
  to cover `.pi/mcp.json` as enforcement-bearing config, and preflight must scan
  it. (This is a real, material new attack surface, not a config convenience.)
- Con: Tool naming (`mcp_<server>_<tool>`) is the extension's, not ours —
  couples our role-table `brokerTools` literal to a third-party naming scheme.

**Estimated Scope:** `.pi/mcp.json` + package dep + roleTable literal alignment
+ **new S7 preflight scan rule for `.pi/mcp.json`** + stage-role-map `E`
amendment. Complexity: **medium** (little code, but real policy-surface growth).
**Risk:** **medium-high** — trust-surface expansion on the highest-consequence
capability; new untrusted-config attack surface.

### Approach C: First-party `runRpcMode` process-isolated broker delegation (reopens Open-Q1)

**Summary:** Instead of (or in addition to) an in-process custom-tool client,
run the broker-holding role (`git-ops`) as a **process-isolated `runRpcMode`
subprocess** (`pi --mode rpc --no-session`), so the credential-bearing work
lives in a separate OS process from the orchestrator/other roles. The broker
custom tool lives inside that RPC child; the credential is injected only into
that child's env. This is the mechanism Open-Q1's decision record explicitly
named as its **S6 revisit trigger**.

**Tradeoffs:**
- Pro: **Strongest isolation** — OS-process boundary between the
  credential-holding role and everything else, not just a heap/module boundary.
  If a non-git-ops role is compromised, it is in a different process from the
  token.
- Pro: **First-party, documented SDK primitive** (`runRpcMode`, `pi --mode rpc`)
  — no third-party dependency; the SDK itself recommends RPC "when you want
  process isolation."
- Pro: `delegate.ts`/`activeRole.ts` were BUILT (S3, D-S3-A) to make an RPC
  variant **additive** — the SRP boundary is already drawn for exactly this.
- Con: **Reopens Open-Q1** (in-process vs process-isolated delegation), an
  already-closed, operator-ratified decision (`decisions/pi-replatform-open-q1.md`).
  That record explicitly permits this ("if S6/Open-Q3 requires process
  isolation, add a `runRpcMode` variant AT S6 — additive, not a rebuild") — but
  reopening a ratified decision is itself a material decision to surface, NOT to
  do quietly.
- Con: **Largest net-new integration** — cross-process depth-cap, active-role
  propagation, enforcement-hook binding across the RPC boundary (the S3
  brainstorm's own reason for NOT doing RPC speculatively). Genuinely new
  machinery, not a port.
- Con: The live-model-turn / auth-in-sandbox residual (Open-Q1 record, Carried
  residual #1) intersects here — an RPC child still needs provider auth to run
  a model turn, unreachable under `--network=none`.
**Estimated Scope:** `runRpcMode` launch wiring + cross-process delegation edge
+ the RPC broker-tool host + all of A's or B's client inside the child.
Complexity: **high**.
**Risk:** **high** — speculative isolation the S3 analysis deliberately deferred;
reopens a ratified decision; largest surface.

## Decision Analysis

> **Not converged. Each D-S6-N below is options + framework + bias check +
> recommendation, to be surfaced to the operator by the orchestrator. The
> recommendation is the INPUT to convergence, per K-3 — never the decision.**

Five material decisions. **D-S6-1 (which reach mechanism) is the central one**
and conditions the rest; it embeds the Open-Q3 resolution. D-S6-2 (Open-Q1
reopening) and D-S6-4 (sequencing / ASSUMPTION-4) are the two the delegation
specifically flagged as separate material decisions.

### D-S6-1 — Which reach mechanism does S6 use? (THE central decision; resolves Open-Q3's real content)

**Framework used:** Reversibility Filter → Weighted Decision Matrix
(multi-option architectural choice with long-lived, security-critical
consequences — the git/pm brokers are the highest-blast-radius capability in
the roster).

**Reversibility:** One-Way Door (soft). The reach mechanism becomes the audited
path for the framework's most sensitive capability; a third-party dependency,
once in the trust surface and shipping, is costly to remove, and an `mcp.json`
policy surface, once blessed, is hard to un-bless. Full analysis warranted.

**The Open-Q3 reproduction analysis actually performed** (the delegation asked
for grounding, not a guess): reading both `mcp_server.py` files confirmed
**MCP-over-stdio** transport with the pm credential read from the broker
child's own `os.environ`; reading the pi SDK primary docs confirmed
(i) custom-tool `execute` runs arbitrary Node incl. `child_process.spawn`,
(ii) `runRpcMode` is a first-party process-isolation export, and (iii)
`pi-mcp-extension` already bridges stdio MCP servers with per-server `env`.
**Conclusion of the reproduction analysis: reachability is ACHIEVABLE and the
credential-isolation property (token only in the child's env) is PRESERVABLE in
all three mechanisms. Open-Q3 is resolved AFFIRMATIVELY; the remaining choice is
WHICH mechanism, traded off on trust-surface vs isolation-strength vs cost.**

**Analysis results:**

| Criterion | Weight | A (self-authored custom-tool stdio client) | B (3rd-party `pi-mcp-extension` + `mcp.json`) | C (first-party `runRpcMode` process isolation) |
|---|---|---|---|---|
| Preserves credential isolation (token never in role) | 10 | 9 → 90 | 8 → 80 | 10 → 100 |
| Trust-surface minimisation (runtime-and-deps.md) | 10 | 10 → 100 | 3 → 30 | 8 → 80 |
| No NEW untrusted-config attack surface (G-1/S7) | 9 | 9 → 81 | 3 → 27 | 7 → 63 |
| G-2 single-holder cleanly enforced at reach layer | 9 | 9 → 81 | 6 → 54 | 8 → 72 |
| First-party / no dependency on external maintainer | 8 | 10 → 80 | 2 → 16 | 10 → 80 |
| Low net-new integration cost (not building ahead of need) | 7 | 6 → 42 | 9 → 63 | 2 → 14 |
| Does NOT reopen a ratified decision (Open-Q1) | 6 | 9 → 54 | 9 → 54 | 2 → 12 |
| Reuses brokers unchanged (MCP-over-stdio) | 5 | 10 → 50 | 10 → 50 | 8 → 40 |
| **Total** | | **578** | **374** | **461** |

**Recommended (D-S6-1): Approach A — a self-authored first-party custom-tool
MCP-over-stdio client, scoped to the fixed 4-tool broker surface, with the
credential injected ONLY into the spawned Python broker child's `env`.** A wins
decisively on the two highest-weighted, framework-defining criteria
(trust-surface minimisation and no-new-untrusted-config-surface) that
`runtime-and-deps.md` ties directly to G-1/G-2 — the whole reach path stays
Gleipnir-owned, auditable, and inside the S-2 boundary, with the inert
`gleipnir-git_*` name made real via the same `canUse` + `tool_call` gate that
governs every other tool. **C (`runRpcMode`) is the recommended FALLBACK / future
hardening** IF the operator judges the OS-process boundary necessary for the
credential-holding role (it scores highest on isolation but reopens Open-Q1 and
is the largest build — see D-S6-2). **B is NOT recommended** despite the least
code: it puts a third-party dependency on the most sensitive capability's path
and introduces `.pi/mcp.json` as a new untrusted-project-tamperable enforcement
surface — the exact trust-surface expansion `runtime-and-deps.md` forbids for
the enforcement core. **The decision the operator must make: A vs C** (whether
in-process-with-tight-env-scoping suffices, or the OS-process boundary is
required for the token-holding role). Choose B only if minimising Gleipnir-owned
code decisively outweighs the trust-surface and untrusted-config costs — the
matrix says it does not.

**Bias check:**
- ⚠️ *IKEA Effect (candidate, checked for A):* "build our own client" could be
  self-build bias. Ruled out — the recommendation rests on the RECORDED
  trust-surface decision (`runtime-and-deps.md`), not attachment; and the
  scope is bounded by a FIXED 4-tool surface we already own, not a general
  client.
- ⚠️ *Bandwagon (candidate, ruled out for B):* `pi-mcp-adapter`'s 607.9K/mo
  downloads and "everyone uses mcp.json" is popularity, not fitness — the
  detector says evaluate against OUR constraints (trust-surface, untrusted
  config), where B scores poorly. Correctly resisted.
- ⚠️ *Scope Creep (candidate, ruled out for C):* C folds OS-process isolation
  into "reach the broker" — building isolation machinery the S3 analysis
  deliberately deferred as speculative. The detector says force the narrower
  boundary (A) unless a converged requirement demands isolation. No other
  detector fires decisively.

### D-S6-2 — Does S6 reopen Open-Q1 (in-process vs process-isolated delegation)? (SEPARATE material decision — reopening a ratified decision)

**Framework used:** Reversibility Filter → Regret Minimisation (a go/no-go on
reopening an already-closed, operator-ratified decision — exactly the asymmetric-
downside shape Regret Minimisation is for).

**The coupling is LIVE and explicitly named.** `decisions/pi-replatform-open-q1.md`
L31-49 states its OWN revisit trigger: *"If the S6 sandbox/broker convergence
(Open-Q3) requires process isolation for any role, add a `runRpcMode` variant to
the delegation edge AT S6 — this is additive, not a rebuild."* So whether S6
reopens Open-Q1 is **conditional on D-S6-1**: if D-S6-1 = C, Open-Q1 IS reopened
(and the record's S6-conditional future-work item is enacted); if D-S6-1 = A or
B, Open-Q1 stays closed (in-process remains final) and the RPC variant remains
tracked-but-unbuilt.

**Regret analysis (regret horizon = the framework's productionisation):**

| Option | Regret if wrong (1–10) | Regret if not chosen (1–10) | Max regret |
|---|---|---|---|
| Keep Open-Q1 closed; A/B in-process reach (recommended if D-S6-1≠C) | 4 — if isolation later proves needed, add the RPC variant then (the record made it additive, so late is cheap) | 3 — if isolation was never needed, we saved a large speculative build | **4** |
| Reopen Open-Q1 now; adopt C process isolation | 8 — large speculative build for isolation no converged requirement yet demands; reopens a ratified decision; the S3 analysis's exact deferred risk | 2 — if a compromised-role-vs-token threat is real and imminent, doing it now would have been right | **8** |

**Recommended (D-S6-2): Do NOT reopen Open-Q1 in S6 UNLESS the operator's D-S6-1
choice is C.** If D-S6-1 converges to A (recommended), Open-Q1 stays closed:
in-process reach with tight env-scoping (D-S6-3) is sufficient, and the
`runRpcMode` variant remains the tracked, additive S6-conditional item the
Open-Q1 record already anticipates — built later IF a converged isolation
requirement emerges, at low marginal cost because `delegate.ts`/`activeRole.ts`
were shaped for it. **This is a decision the operator must make CONSCIOUSLY, not
by default:** reopening a ratified decision (choosing C) is legitimate and
pre-authorised by the Open-Q1 record, but it must be an explicit operator call,
surfaced here, not slipped in via the mechanism choice. **If the operator DOES
choose C**, this brief flags that `decisions/pi-replatform-open-q1.md` must be
AMENDED (Tier-3, operator-authored) to record the trigger firing and Open-Q1's
resolution moving to process-isolated for `git-ops` — the brainstorm does not
edit `decisions/`.

**Bias check:** ⚠️ *Status Quo (candidate, checked):* recommending "keep Open-Q1
closed" could be status-quo bias. Ruled out — the recommendation applies the
SAME scrutiny to both (the Regret matrix), and the "keep closed" call rests on
the record's own additive-later design + the S3 second-order analysis, not on
"changing is a cost." ⚠️ *Sunk Cost (candidate, N/A):* the S3 in-process
investment is not the reason — future value is (late RPC is cheap by design).

### D-S6-3 — Credential-injection scoping (how tightly is the child's `env` isolated from the pi role?)

**Framework used:** Pre-Mortem (a security-critical mechanism where the failure
mode — token leak to a role — is the exact harm G-2 exists to prevent).

**The precise question:** in Approach A/C, the pi extension process spawns the
credential-bearing broker child, so IT sets the child's `env`. How does the
token reach the child's `env` WITHOUT the extension (and thus a potentially
broader blast radius) ever holding it in a readable form?

**Pre-Mortem (assume: the token leaked to a non-holder role):**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Extension reads `process.env.GITHUB_TOKEN` to forward it into the child's `env` → token is in the extension's heap, reachable by any code in that process | M | H | **Child inherits the token from a launch context the extension never reads** — spawn WITHOUT passing `env` for the secret, letting the child inherit it from the operator's shell env (present only because the operator launched pi with it), or have the CHILD fetch it from a credential store the extension has no path to. The extension names the var; it does not read its value. |
| 2 | Token logged / echoed in a tool result or error surfaced to the calling role | M | H | Broker already returns STRUCTURED results (never raises, redacts); the client relay must not echo `env`; add a test asserting no secret substring in any relayed payload |
| 3 | A non-holder role registers/reaches the broker tool | L | H | S2 `canUse` + `tool_call` block hook: only the sole-holder role's table lists the tool; deny-by-default everywhere else (already enforced) |
| 4 | `mcp.json` (Approach B only) lets an untrusted project redirect `command` to attacker code with the real `env` | M | H | (B-specific) S7 preflight must scan `.pi/mcp.json`; "load only after trust" must gate it — a reason A/C are preferred |

**Top risks:** #1 (the core credential-isolation sharp edge) and #2.
**Verdict: Proceed with mitigations — specifically, the child must obtain the
credential by INHERITANCE or self-fetch, NOT by the extension reading and
forwarding it.**

**Recommended (D-S6-3): the broker child obtains its credential WITHOUT the pi
extension ever reading the secret value.** Preferred mechanism: the extension
spawns `python -m gleipnir.broker...` and the child inherits the token from the
process launch environment the OPERATOR established (the same "env-injected"
model the brokers already assume, `platform.py` L11-13) — the extension
specifies WHICH vars pass through by NAME, never reading their VALUES into its
own heap; and no relayed tool result or error may contain the secret (tested).
This keeps the token's readable lifetime confined to the broker child, closing
Pre-Mortem #1/#2. **Operator confirms** the inheritance-not-forwarding model
(recommended: yes), OR directs a stronger store-backed fetch (child pulls from
an OS keychain the extension cannot reach) if the launch-env inheritance is
judged too broad. Under Approach C the same rule holds inside the RPC child.

**Bias check:** ⚠️ *Availability (checked, ruled out):* the "env-injection"
model is the brokers' EXISTING documented assumption, not a vivid recent
example — base-rate/primary-source grounded. None fires decisively.

### D-S6-4 — Sequencing: does the finding change S6's build-order position? (resolves ASSUMPTION-4)

**Framework used:** Second-Order Thinking + the build-order's own dependency
graph (S2/S3 → S6, off the S4/S5 critical path).

**The precise question:** the build-order's [ASSUMPTION-4] placed S6 after the
engine "for sequencing only," noting: *"if brokers turn out to need a custom-tool
socket wrapper, that wrapper is itself a pi custom tool (S3-shaped) and may pull
earlier."* Does the Explore finding trigger that pull-earlier clause?

**Second-order analysis:**
- The finding is that the reach mechanism (recommended Approach A) IS an
  S3-shaped pi **custom tool** (a `registerTool` with an `execute` handler) —
  exactly the shape [ASSUMPTION-4] anticipated. So the clause's PREDICATE is
  met (it is a custom-tool wrapper).
- BUT the clause's pull-earlier RATIONALE was "if the engine or other steps
  DEPEND on the broker being reachable." Checking the dependency graph
  (`build-order.md` L233-242): S6 depends only on S2 (`git-ops` role) and S3
  (delegation boundary), both DONE. Nothing downstream (S4 engine, S5
  attestation, S7 preflight, S8 bus) depends on S6 — S6 sits on its own branch
  off S2/S3, and S4/S5 are already CLOSED without it. So there is no
  dependency-driven reason to pull S6 earlier; it was never blocking the
  critical path, and the critical path is now past it.
- Near-term: build S6 now (its deps are met; Open-Q3 is resolved). Far-term: no
  reordering needed — [ASSUMPTION-4]'s "may pull earlier" was a hedge against a
  dependency that did not materialise.

**Key insight:** the custom-tool shape [ASSUMPTION-4] worried about DID
materialise, but the dependency it worried about did NOT — S4/S5 closed without
needing the broker. So [ASSUMPTION-4] is **discharged, not triggered**: S6 stays
where it is (buildable NOW, its S2/S3 deps met), and no build-order reordering is
required.

**Recommended (D-S6-4): [ASSUMPTION-4] is DISCHARGED — S6 keeps its build-order
position and is buildable now that Open-Q3 is resolved. No reordering.** The
reach mechanism is the S3-shaped custom tool the assumption predicted, but
because nothing downstream depended on broker reachability (S4/S5 closed without
it), the "may pull earlier" clause does not fire. **Operator confirms** S6
proceeds in place (recommended: yes). If the operator chooses Approach C
(`runRpcMode`), note the sequencing interacts with the Open-Q1 reopening
(D-S6-2) but still does not move S6 earlier — it enlarges S6, it does not
reorder it.

**Bias check:** None fires decisively. (⚠️ *Anchoring* on [ASSUMPTION-4]'s "may
pull earlier" phrasing checked — the recommendation re-derived from the actual
dependency graph, not the phrasing.)

### D-S6-5 — Scope of the E-1 argument-policy seam in S6 (enforce arg-level bounds now, or defer to S7?)

**Framework used:** Pros-Cons-Fixes + the S2/S3 precedent (arg-level enforcement
was explicitly deferred to S7).

**The precise question:** the git broker's own `_run_git` choke point already
refuses hook-bypass flags INSIDE Python (unchanged, sound). But the pi-side
E-1 argument-policy seam (per-path/per-arg bounds recorded as `bounds` metadata
in `roleTable.ts`, e.g. "git-ops read denied under `.git/**` to protect the
token") is, per S2/S3 (`decisions/pi-replatform-open-q1.md` Carried residual #2),
**"legitimately deferred to S7."** Does making the broker REACHABLE in S6
force any arg-level enforcement into S6?

**Options:**
- **Option 5a — S6 enforces coarse tool-presence reachability only; arg-level
  bounds stay deferred to S7** (matches the S2/S3 residual). S6 makes the broker
  tool callable by the sole-holder role and preserves the broker's OWN internal
  invariants (which are Python-side, not pi-side); the pi-side arg policy
  (`event.input` inspection) lands in S7 with the rest of the E-1 seam.
- **Option 5b — S6 pulls the broker-relevant arg bounds forward** (e.g. screen
  the relayed MCP `tools/call` params at the pi tool boundary now).
- **Option 5c — S6 adds a thin pi-side pass-through screen** only for the
  hook-bypass class the broker already refuses, as defence-in-depth.

**Analysis:** the broker's hard invariant (no `--no-verify`/hooksPath) is
enforced Python-side at `_run_git` and CANNOT be bypassed by the reach mechanism
(the relay passes MCP tool params, not raw argv — `commit_changes(message,...)`,
not `git commit --no-verify`). So the SAFETY-critical invariant is already sound
without any S6 arg policy. The pi-side arg-level bounds (path/arg restrictions
recorded as `bounds`) are a SEPARATE, broader E-1 concern the framework already
committed to S7. Pulling them into S6 would expand S6's exit criterion and
duplicate the S7 seam — the exact scope-discipline the S2/S3 residual protects.

**Recommended (D-S6-5): Option 5a — S6 enforces coarse broker REACHABILITY
(the sole-holder role can call the broker tool; deny-by-default everywhere else)
and relies on the broker's OWN unchanged Python-side hard invariant for
hook-bypass safety; the pi-side E-1 arg-level bounds stay DEFERRED to S7 with
the rest of the argument-policy seam (matching the S2/S3 Carried-residual-#2
commitment).** This keeps S6 scoped to reachability + credential isolation (its
stated goal) and does not fork the E-1 seam across two steps. **Operator
confirms** (recommended: 5a). One point to flag: the relay MUST pass only
structured MCP tool params (never raw argv) so the broker's `_run_git` screen
stays the authoritative choke point — this is a correctness constraint on the
reach mechanism, tested, not a new arg policy.

**Bias check:** ⚠️ *Scope Creep (candidate, ruled out for 5a):* 5b/5c would fold
the S7 arg seam into S6 "while we're touching the broker path" — the detector
says force the narrower boundary; the safety invariant is already Python-side.
Correctly resisted.

### Bias warnings summary (across all five)

- ⚠️ **Scope Creep** (D-S6-1 C, D-S6-5): surfaced twice — each recommendation
  forces the narrower boundary (self-authored in-process reach over speculative
  RPC isolation; reachability-only over pulling the S7 arg seam forward).
- ⚠️ **IKEA Effect** (D-S6-1 A, checked): "build our own client" rests on the
  recorded trust-surface decision + a fixed 4-tool surface, not attachment.
- ⚠️ **Bandwagon** (D-S6-1 B, ruled out): `mcp.json`/`pi-mcp-adapter` popularity
  is not fitness for OUR trust-surface constraints.
- ⚠️ **Status Quo** (D-S6-2, checked): "keep Open-Q1 closed" applies equal
  scrutiny via the Regret matrix; not a free pass to the status quo.
- ⚠️ **Availability** (D-S6-3, ruled out): the env-injection model is the
  brokers' existing documented assumption, primary-source grounded.
- No other detectors triggered.

## Selected Approach

**CONVERGED by the operator (via the orchestrator's `question` tool;
operator-via-orchestrator, L-C6-legitimate — NOT self-attested). All FIVE
choices MATCHED the brainstorm recommendation — no divergence this round.**
These are the decided choices `gleipnir-plan` plans from:

- **D-S6-1: CONVERGED → Approach A (self-authored first-party custom-tool
  MCP-stdio client).** MATCHES recommendation. Gleipnir writes its own
  `pi-package` custom tool(s) whose `execute` handler is a minimal
  MCP-over-stdio client relaying the sole-holder role's tool call to the
  spawned Python broker (`python -m gleipnir.broker.{git,pm}.mcp_server`,
  already `transport="stdio"`). **Zero third-party runtime dependency**
  (if hand-rolled — see the flagged tension in the scope summary below) and the
  **tightest G-2 single-holder binding** (the tool is registered only for the
  sole-holder role; the same `canUse` + `tool_call` block hook that gates every
  other tool gates this one). The inert `GIT_BROKER_TOOL = "gleipnir-git_*"`
  (roleTable.ts L105) becomes real with no config surface an untrusted project
  could tamper with. Approach B (third-party `pi-mcp-extension` + `.pi/mcp.json`)
  is REJECTED — it puts a third-party dependency on the most sensitive
  capability's path and introduces a new untrusted-project-tamperable
  enforcement surface (against `runtime-and-deps.md`). Approach C (`runRpcMode`
  process isolation) is NOT chosen (see D-S6-2).
- **D-S6-2: CONVERGED → Do NOT reopen Open-Q1.** MATCHES recommendation.
  **Because D-S6-1 = A (not C), the Open-Q1 revisit-trigger condition — "the S6
  sandbox/broker convergence requires process isolation for any role" — was NOT
  met.** In-process reach with tight credential-env-scoping (D-S6-3) is
  sufficient; the `runRpcMode` variant remains the tracked, additive,
  S6-conditional item the Open-Q1 record already anticipates, built later ONLY
  IF a converged isolation requirement ever emerges. **`decisions/pi-replatform-open-q1.md`
  remains AS-IS, UNAMENDED** — no Tier-3 edit is required or authorised by this
  convergence. This is stated explicitly to CLOSE OFF the decision path: Open-Q1
  is settled (in-process, final for S3, and now confirmed sufficient for S6);
  it is NOT left lingering as an ambiguous "might still reopen." The trigger did
  not fire; the record stands.
- **D-S6-3: CONVERGED → Broker child inherits/self-fetches the credential; the
  calling pi extension/role NEVER reads or forwards the credential value.**
  MATCHES recommendation. The credential (`GITHUB_TOKEN`/`GITLAB_TOKEN` for pm,
  read from the broker child's own `os.environ` per `platform.py` L11-13;
  ambient git push creds for git) lives ONLY in the spawned broker subprocess's
  own environment/config. The extension specifies WHICH env vars pass through by
  NAME (or the child self-fetches from a store the extension cannot reach); it
  never reads the VALUE into its own heap. This closes the Pre-Mortem #1/#2
  token-leak-to-role failure modes and preserves G-2 at the reachability layer,
  not just the table layer. A test MUST assert no secret substring appears in
  any relayed tool result or error.
- **D-S6-4: CONVERGED → Keep S6 in its current build-order position.** MATCHES
  recommendation. **[ASSUMPTION-4] is CONFIRMED DISCHARGED, not a blocker.** The
  S3-shaped custom-tool wrapper the assumption predicted DID materialise, but
  because nothing downstream depended on broker reachability (S4/S5 closed
  without it — S6 sits on its own branch off S2/S3), the "may pull earlier"
  clause does NOT fire. S6 is buildable now (its S2/S3 deps are met; Open-Q3 is
  resolved). No resequencing.
- **D-S6-5: CONVERGED → Defer E-1 argument-level policy to S7.** MATCHES
  recommendation (Option 5a). S6 builds ONLY coarse broker REACHABILITY (the
  sole-holder role can call the broker tool; deny-by-default everywhere else)
  + credential isolation. The broker's OWN unchanged Python-side hard invariant
  (`_run_git`'s refusal of `--no-verify`/`-n`/`-c core.hooksPath`) remains the
  AUTHORITATIVE enforcement for hook-bypass safety until S7. The pi-side
  arg-level bounds (path/arg restrictions recorded as `bounds` metadata in
  roleTable.ts) stay DEFERRED to S7 with the rest of the E-1 argument-policy
  seam (matching the S2/S3 Carried-residual-#2 commitment). **Correctness
  constraint on the reach mechanism (tested, not a new arg policy):** the relay
  MUST pass only structured MCP tool params (e.g. `commit_changes(message,...)`),
  NEVER raw argv, so the broker's `_run_git` screen stays the authoritative
  choke point.

## Converged scope summary (for `gleipnir-plan` ATLAS Architect/Trace)

### (1) What needs building — the custom-tool MCP-stdio client architecture

- A `pi-package` extension module (sketch: `pi-package/src/broker/` — e.g.
  `gitBroker.ts` / `pmBroker.ts` + a shared `mcpStdioClient.ts`) that
  `registerTool`s the broker tools whose `execute` handler:
  1. spawns the existing Python broker as an MCP-over-stdio subprocess
     (`python -m gleipnir.broker.git.mcp_server` / `...pm.mcp_server` — both
     ALREADY `mcp.run(transport="stdio")`, reused UNCHANGED, no Python edits);
  2. performs the minimal MCP JSON-RPC handshake + `tools/call` relay over the
     child's stdin/stdout (the FIXED 4-tool surface per broker:
     git = `git_status`/`git_diff`/`commit_changes`/`push_current_branch`;
     pm = `issue_{create,update,comment,close}`);
  3. returns the child's structured result to the calling role.
- **Wiring into the existing S2 typed partition (`roleTable.ts`):** the real
  tools are wired to the SAME roles the S2 table already declares, with NO
  widening:
  - **`git-ops`** holds the git broker — its `brokerTools = [GIT_BROKER_TOOL]`
    where `GIT_BROKER_TOOL = "gleipnir-git_*"` (roleTable.ts L105, L182-190) is
    the ONLY non-empty `brokerTools` in the whole table (the G-2 sole-holder
    proof, AC-17). S6 makes that inert glob REACHABLE.
  - **`project-mgr`** holds the pm broker — modelled in
    `project-mgr.customTools = [PM_BROKER_TOOL]` where
    `PM_BROKER_TOOL = "gleipnir-pm_*"` (roleTable.ts L107-109, L193-198), per the
    S2 P2 modelling note (both are MCP broker namespaces of the same class; git
    goes in `brokerTools` for the clean G-2 assertion, pm in `customTools`).
    (NB: the role is named `project-mgr` in the pi roleTable, not `pm-manager`.)
  - Deny-by-default is preserved by construction: `canUse` returns `true` only
    for the sole-holder; the `tool_call` block hook denies every other role.
- **AC to earn:** the S2-style G-2 proof extended from table-entry to REAL
  reachability — "exactly one role can actually invoke each broker namespace, and
  it is `git-ops` (git) / `project-mgr` (pm); all others are blocked."

### (2) Credential-isolation mechanism (confirmed)

- The token lives ONLY in the spawned broker child's environment/config. The
  child obtains it by **inheritance from the launch context / self-fetch**, NOT
  by the extension reading `process.env.<TOKEN>` and forwarding the value. The
  extension names which vars pass through; it never holds the secret value in
  its own heap. No relayed result/error may contain the secret (tested).
- This is identical in strength to the opencode status quo (token env-injected
  into the broker child) and is strictly better than any design where the reach
  layer sees the secret.

### (3) Explicitly OUT of scope for S6

- **E-1 argument-level policy → DEFERRED to S7.** S6 does coarse reachability +
  credential isolation only; the pi-side `event.input` arg/path bounds land in
  S7. The broker's Python-side `_run_git` hard invariant is the authoritative
  hook-bypass enforcement in the interim.
- **Open-Q1 → NOT reopened.** No `runRpcMode` variant is built in S6; no
  `decisions/pi-replatform-open-q1.md` amendment. In-process reach is final and
  sufficient.
- **The brokers themselves → UNCHANGED.** No socket server, no Python edits;
  they are reused exactly as they ship (already MCP-over-stdio).

### Hands-on verification `gleipnir-plan` MUST do before committing the plan (L-C36)

1. **⚠️ THE CENTRAL TENSION — the MCP-stdio client library choice vs
   stdlib-only-core.** The converged Approach A says "zero third-party
   dependency IF hand-rolled." But an MCP client is NOT Node stdlib: the two
   realistic options are (a) **hand-roll** a minimal JSON-RPC-over-stdio client
   covering ONLY the `initialize` + `tools/call` subset our fixed 4-tool brokers
   need (zero dep, honours `runtime-and-deps.md`'s trust-surface-minimisation,
   but we own the framing/lifecycle/cancellation correctness), or (b) add the
   **`@modelcontextprotocol/sdk`** TypeScript client as a dependency (correct and
   maintained, but a NEW runtime dependency on the enforcement core's most
   sensitive path — which `decisions/runtime-and-deps.md` explicitly warns
   against: "fewer dependencies = smaller trusted surface to audit = directly
   serves G-1/G-2"). **`gleipnir-plan` must verify: is any MCP TS SDK ALREADY a
   `pi-package` dependency? (Confirmed NOT, this session: `package.json`
   peerDeps are only the four `@earendil-works/pi-*` packages + `typebox`; no
   MCP client.)** So option (b) introduces a genuinely new dependency. **This is
   a material sub-decision that may need to route BACK to the operator** — the
   convergence chose Approach A on the STRENGTH of "zero third-party dep," so
   silently adopting `@modelcontextprotocol/sdk` would diverge from the basis of
   the operator's choice. Recommended framing for the plan: default to (a)
   hand-rolled minimal client (honours the basis of the convergence); surface
   (b) to the operator ONLY if the hand-rolled client proves infeasibly complex.
   Note the Python brokers use `FastMCP` (the `mcp` PyPI package) on the SERVER
   side — that is the server, already shipped; it does not dictate the client.
2. **Broker child lifecycle:** spawn-per-call vs long-lived child (perf /
   resource / cancellation-signal semantics — the SDK's `execute` receives an
   `AbortSignal` that must propagate to the child).
3. **`env`-passthrough-by-name mechanism** (D-S6-3): the exact
   `child_process.spawn` `env` construction that lets the child inherit the
   token WITHOUT the extension reading the value — verify the chosen pattern
   actually keeps the value out of the extension heap.
4. **Glob-to-concrete-tool mapping:** how `"gleipnir-git_*"` (a glob in the S2
   table) maps to the four concrete relayed tool names for `canUse` — does the
   glob suffice, or must the concrete names be registered? (S2 modelled it as a
   glob; the plan must state how real tools match.)
5. **Test harness:** round-trip against a mock/real stdio broker under
   `bin/gleipnir-sandbox --profile pi` (`--network=none`) — note the pm broker's
   live REST call and git push need network/creds unreachable in-sandbox, so the
   round-trip test likely uses a MOCK stdio broker for the transport/relay proof
   (the same sandbox/auth-residual pattern as the S3/S4 live-turn gap).

## Open-Q1 coupling flag (explicit, per the delegation)

**Resolving Open-Q3 CAN reopen Open-Q1 — and this is a SEPARATE material
decision (D-S6-2), not a quiet consequence.** `decisions/pi-replatform-open-q1.md`
names the S6/Open-Q3 broker convergence as its OWN revisit trigger: if S6
requires process isolation for the credential-holding role, the tracked
`runRpcMode` variant is enacted and Open-Q1's resolution moves from in-process to
process-isolated for `git-ops`. Under the recommended D-S6-1 = A, Open-Q1 stays
closed (in-process reach suffices; the RPC variant remains tracked-but-unbuilt).
Under D-S6-1 = C, Open-Q1 IS reopened and its decision record must be amended
(Tier-3, operator-authored). The operator must make this consciously.

## Open Questions (for `gleipnir-plan`, AFTER convergence)

- **Exact MCP-stdio client surface** (if D-S6-1 = A): hand-rolled minimal
  JSON-RPC (`initialize` + `tools/call` subset only) vs Node
  `@modelcontextprotocol/sdk` client (a dependency — re-check against
  `runtime-and-deps.md` if chosen). The plan pins which, with the trust-surface
  rationale, as the falsifiable Design Intent.
- **Broker child spawn shape:** exact `child_process.spawn` args
  (`python -m gleipnir.broker.git.mcp_server`), cwd, lifecycle (spawn-per-call
  vs long-lived child), and the env-passthrough-by-name (D-S6-3) mechanism —
  and a test asserting no secret substring appears in any relayed payload.
- **Role-table literal alignment:** the `GIT_BROKER_TOOL = "gleipnir-git_*"`
  glob (roleTable.ts L105) and `PM_BROKER_TOOL` (L109) — how the reach mechanism
  maps the glob to the four concrete tool names, and whether `brokerTools` needs
  the concrete names or the glob suffices for `canUse` (S2 modelled it as a glob;
  the plan states how the real tools match).
- **If D-S6-1 = B:** the `.pi/mcp.json` schema, the stage-role-map Axis-2(a) `E`
  amendment adding `.pi/mcp.json` as enforcement-bearing, and the S7 preflight
  scan rule — all NEW policy surface the plan must sequence.
- **If D-S6-1 = C:** the cross-process depth-cap / active-role / enforcement-hook
  propagation over the RPC boundary; the Open-Q1 record amendment; the
  live-model-turn/auth-in-sandbox residual intersection.
- **G-2 test:** the AC that proves exactly one role reaches each broker namespace
  (mirroring S2's AC-17 "exactly one role has non-empty `brokerTools`, and it is
  `git-ops`"), now extended to REAL reachability, not just the table entry.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Broker reach mechanism (new, if A) | `pi-package/src/broker/{gitBroker,pmBroker}.ts` + `mcpStdioClient.ts` — `registerTool` custom tools relaying MCP-over-stdio to the spawned Python brokers; credential via env-passthrough-by-name (D-S6-3) |
| Role-table wiring (present, made real) | `pi-package/src/roleTable.ts` — the inert `GIT_BROKER_TOOL`/`PM_BROKER_TOOL` become reachable; no widening (deny-by-default preserved) |
| Delegation edge (if C) | `pi-package/src/delegate.ts`/`activeRole.ts` — additive `runRpcMode` variant (the SRP boundary built in S3 for exactly this); Open-Q1 record amendment |
| Config surface (if B only) | `.pi/mcp.json` + `pi-mcp-extension` dep + `stage-role-map.md` Axis-2(a) `E` amendment + S7 preflight scan rule |
| Brokers (UNCHANGED) | `src/gleipnir/broker/{git,pm}/mcp_server.py` — reused as-is (already MCP-over-stdio; their `_run_git` hard invariant stays authoritative) |
| Tests | reachability (sole-holder can call, others denied — G-2), credential-non-leak (no secret substring in any relayed payload), round-trip against a mock/real stdio broker, under `bin/gleipnir-sandbox --profile pi` |

## Design Principles (Gate 1 — brainstorm artifact)

**Routing:** this artifact is **prose-only** (`P = { this .md file }`,
`P ∩ X = ∅`). Per `plan-format.md` case (iii), SOLID/DRY/SRP are
**`N/A — no executable artifact`**.

**Design Intent (specific, falsifiable):** *This brief must (a) RESOLVE Open-Q3
by grounding the reach-mechanism finding in primary source — the brokers' actual
transport read from `mcp_server.py`, and the pi SDK's actual MCP/custom-tool/RPC
surface verified against pi.dev/earendil docs, NOT the build-order's summary
(L-C36) — stating plainly whether a viable mechanism exists; (b) surface every
S6 material decision the delegation named (reach mechanism, credential isolation,
Open-Q1 reopening, sequencing/ASSUMPTION-4, E-1 seam scope) as an explicit
D-S6-N with options + framework + recommendation, deciding NONE; and (c) show,
for each viable mechanism, HOW the credential stays out of the calling role
(G-2 preserved).* Falsifiable by: any named decision missing or silently
decided; an Open-Q3 finding not grounded in the actual `mcp_server.py` transport
+ actual SDK docs (it is — MCP-over-stdio confirmed at L507-508/L147-148, SDK
`runRpcMode`/custom-tool/`pi-mcp-extension` confirmed against primary source);
or a mechanism recommended without a credential-isolation account (each has one
in D-S6-3 + the common-core section).

## Decision Frameworks Note
Frameworks applied: Reversibility Filter + Weighted Decision Matrix (D-S6-1),
Reversibility Filter + Regret Minimisation (D-S6-2), Pre-Mortem (D-S6-3),
Second-Order Thinking (D-S6-4), Pros-Cons-Fixes (D-S6-5). Bias detectors run
across all five; Scope Creep (×2), IKEA Effect, Bandwagon, Status Quo, and a
ruled-out Availability check surfaced and are addressed. Per the K-3 binding,
these analyses are the INPUT to the operator's convergence, not the decision.
