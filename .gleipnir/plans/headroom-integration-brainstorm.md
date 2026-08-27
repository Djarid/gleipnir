# Design Brief: Headroom as a shared context-hygiene service for Gleipnir

> **Status: CONVERGED (defer/reject) — see `## Selected Approach`.** This is a
> planning-only assessment thread, explicitly separate from the pi.dev
> replatform build-order (S1-S9). It does not touch or depend on S6 (parked).
> The six decisions (D1-D6) below were surfaced to the OPERATOR, who converged
> D1 = defer/reject (no Headroom integration built now); D2-D6 are consequently
> moot. See `## Selected Approach` for the converged decision and rationale.

## Problem Statement

Verbose tool output — large diffs, `grep`/search dumps, JSON blobs, build/test
logs — **contaminates subagent context windows and degrades reasoning quality.**
This is a **context-HYGIENE** problem, not a cost problem: the harm is that a
reasoning agent's window fills with low-signal bulk and its judgment gets worse,
independent of token spend. (Contrast `decisions/context-cap.md`, which *is*
about spend; the shared framing is only "the context window is a scarce,
protectable resource.")

The candidate fix is **Headroom** (`headroomlabs-ai/headroom`, Apache-2.0), a
reversible context-compression layer. The question this brief frames is whether,
and exactly how, Headroom could be adopted as a **shared service available to
ALL Gleipnir subagents** while remaining **strictly outside the trust boundary**
(never touching the enforcement core, the `--network=none` sandbox, attested
evidence, or anything G-1..G-6 depends on).

## Constraints (given, not re-derived)

1. **Goal is hygiene, not cost.** Not a token-reduction exercise. The metric is
   cleaner subagent reasoning, not the G-4d ledger.
2. **Shared service, all roles.** Any bounded role (`gleipnir-code`,
   `quality-reviewer`, `gleipnir-plan`, `git-ops`, …) must be able to reach it.
   Not orchestrator-only; not a per-agent-launch `wrap`/proxy that is blind to
   Gleipnir's per-role delegation boundaries.
3. **Strictly outside the trust boundary — NON-NEGOTIABLE.** Headroom may NEVER
   touch the enforcement core, the sandbox, attested evidence (HMAC markers,
   `canUse`/`decideFromExit`/`validateMarker` decisions), or any G-1..G-6
   dependency. This is a hard invariant, not a tradeoff to weigh.
4. **Dependency weight far exceeds anything currently trusted.** Headroom pulls
   a Rust core (PyO3 `headroom._core`), ONNX Runtime (AVX2 on x86), a
   HuggingFace ModernBERT model (`kompress-v2-base`), optionally Serena, and
   install-time asset fetches from `cdn.pyke.io`/HuggingFace. This is heavier
   than the broker's `mcp` SDK tree (pydantic/starlette/uvicorn/cryptography/
   httpx) — and the broker tree was already treated as a "real surface to audit"
   isolated to its own sandbox image.

## Explore — what the code and docs actually show (grounding)

### E1. The wiring precedent exists and is load-bearing (`broker-mcp.md`)

Gleipnir already wires a stdio MCP server into every role with per-role
reachability, via the exact mechanics the task names:
- `opencode.jsonc` `mcp` block enables the server **globally**;
- **per-agent reachability is a TOP-LEVEL `tools:` boolean DENY-LIST** in agent
  frontmatter (`{server_*: false}`), NOT `permission.tools` (verified NOT to work
  for MCP tools — lessons L-C12/L-C12b);
- a **separate sandbox image/profile** (`Containerfile.broker`,
  `[profile.broker]`) keeps the heavy dependency OUT of the lean default test
  image; `default_profile` stays `python`;
- a **stdlib-only carve-out test** (`test_broker_stdlib_only.py`) proves the dep
  never leaks into the enforcement core.

Headroom's MCP server (`headroom mcp serve`, stdio, three tools) is the **same
shape** — so this template applies almost directly, but the dependency is much
heavier, so the isolation posture must be **stricter** than the broker's.

### E2. Headroom's MCP-only path is architecturally CLIENT-SIDE (decisive for D1)

From `headroom-docs.vercel.app/docs/mcp` + `/architecture`:
- **MCP only (no proxy):** "The LLM calls `headroom_compress` **on demand**.
  Compression happens locally in the MCP process." i.e. the subagent has
  *already received* the verbose output into its context, then chooses to
  compress it. **The contamination already happened by the time the tool is
  called.** This is the trivially-wireable path, and it is inherently
  client-side.
- **MCP + Proxy:** "The proxy compresses all traffic at the HTTP level (**before
  the LLM sees content**)." This is the true boundary-side fix — but it is the
  `headroom proxy` running as a host-level HTTP shim in front of the provider
  endpoint (`ANTHROPIC_BASE_URL=…`). It is **per-launch, whole-session, and
  blind to Gleipnir's per-role delegation boundaries** — it would compress
  *everything* for *whoever* is behind that base URL, including content the
  trust rules (D4) say must never be routed through Headroom. The proxy also
  sits on the model-call path, which is uncomfortably close to a trust-path
  position even though it is "just" compression.

### E3. There IS a Gleipnir-native boundary-side seam — with one load-bearing unknown

Gleipnir runs on opencode plugins today (`.gleipnir/plugins/*.ts`), and the
enforcement plugins (`sequence-gate.ts`, `git-guard.ts`, `advance-hook.ts`) prove
the two relevant hooks are real and usable:
- **`tool.execute.before(input, output)`** — `output.args` is **mutable**; the
  opencode docs' own `.env` example throws to abort, and the `shescape` example
  MUTATES `output.args.command = escape(...)`. So pre-tool arg rewriting is a
  confirmed, documented capability.
- **`tool.execute.after(input, output)`** where
  `output = { title: string; output: string; metadata: any }` — `output.output`
  carries the tool's RESULT TEXT. `advance-hook.ts` reads it. This is the seat a
  boundary-side transform would use: intercept a verbose tool result **after
  execution, before it lands in the subagent's context**, and replace
  `output.output` with the compressed form.

  **THE UNKNOWN (must be a spike, not an assumption):** the opencode docs show
  `output` mutation working for the **before**-hook (`output.args`) and for
  `shell.env` (`output.env`), but they **never show an after-hook mutating
  `output.output`**, and Gleipnir's own `hook-probe-findings.md` treated the
  after-hook as **observation-only** (it extracts `output.output` to forward a
  reviewer transcript; it never rewrites it). So *whether a mutation of
  `output.output` in `tool.execute.after` actually propagates into the model's
  next context turn* is **UNVERIFIED**. If it does not, Gleipnir-native
  boundary-side compression is **not achievable on the current opencode
  substrate** without the proxy, and D1 collapses toward client-side or
  reject.

- **Mid-port caveat:** Gleipnir is mid-port to pi.dev (S1-S9). A pi extension's
  `tool_call` hook is the *same class* of mechanism as `enforcement.ts`'s
  block-hook, so the seam likely survives the port — but the port is unfinished
  and its output-mutation semantics are equally unverified. Building
  boundary-side wiring now risks doing it twice.

### E4. Headroom's own documented failure modes (directly relevant to safety)

From `/limitations` + `/ccr` + `/architecture`:
- **Fails open by design.** "Every transform … **fails open** — on any error it
  returns the content unchanged." Good for availability; means Headroom is never
  a hard dependency, but also means it silently no-ops rather than erroring — a
  hygiene service that quietly does nothing is a real mode to expect.
- **Code and grep results mostly pass through.** Code is passthrough unless
  AST-compression is explicitly enabled (off by default), and is *protected* when
  the user message contains "analyze/review/explain/fix/debug"; grep/search
  results are "already minimal." So on **coding-agent workloads the headline win
  is only 15-20%** — the biggest contamination sources for `gleipnir-code`
  (source, grep) are largely *not* what Headroom compresses. The wins are
  concentrated in **JSON tool outputs and build/test logs** (60-95%).
- **CCR is lossy-until-retrieved with a TTL.** Compression is reversible only
  while the original sits in the local store: **1-hour TTL** (MCP-local);
  **30-min** proxy default; **5-min** for proxy content per the troubleshooting
  page. After expiry the hash is dead. The compressed marker in context is a
  *pointer*; if the agent needs the detail after expiry, it is gone.
- **Retrieval can malform.** Gemini OpenAI-compat endpoints can return
  `MALFORMED_FUNCTION_CALL` after CCR retrieval (tracked issue #2041). Not our
  primary provider, but it shows CCR's retrieval path has live edge failures.
- **MCP results themselves occupy context.** The docs explicitly warn that
  Claude Code `/usage` attributes a large share to the `headroom` MCP server
  because "MCP tool calls and MCP tool results" are kept in session context, and
  "subagent-heavy" workflows amplify this. For a hygiene goal, calling a
  client-side compress tool *adds* a tool-call + result round-trip to the very
  window you are trying to keep clean.

### E5. Dependency category — Headroom is NOT "broker class"

`runtime-and-deps.md` names three categories: enforcement-core (stdlib-only),
TS hook layer, and broker/integration (`src/gleipnir/broker/**`, MAY carry
declared justified deps, isolated to its own sandbox image, in-session stdio
subprocess). Headroom fits none cleanly: it is far heavier than the broker's
`mcp` tree, needs network at install time (incompatible with `--network=none`),
and provides no enforcement function. It most honestly needs a **NEW fourth
category: "external, operator-installed, host-level optional service — NEVER in
any sandbox image, NEVER a peer/runtime dependency of any Gleipnir component."**
Flagged for a dedicated `runtime-and-deps.md` amendment if adopted.

---

## Approaches Considered (the shape of the decision space)

### Approach A: Client-side compress-tool (MCP, broker-shaped wiring)

**Summary:** Wire `headroom mcp serve` as an operator-installed stdio MCP
server, enabled globally in `opencode.jsonc`, reachable per-role via the
top-level `tools:` deny-list, isolated as a NEW host-level dependency category
(never in any sandbox). Subagents call `headroom_compress` on demand.

**Tradeoffs:**
- Pro: near-zero new Gleipnir code — reuses the proven `broker-mcp.md` template
  end-to-end; graceful absence (no Headroom installed ⇒ tools just don't appear).
- Pro: trivially outside the trust boundary — it is just another optional MCP
  tool the agent may or may not call; no interception of anything.
- Pro: reversible / low-risk to try (two-way door): deny it in one frontmatter
  line to remove it.
- Con: **does not actually solve the stated problem.** The contamination has
  already occurred by the time the agent calls compress — the verbose output is
  already in the window. It cleans up *after* the damage.
- Con: adds MCP-tool-call + result round-trips that themselves occupy context
  (E4).

**Estimated Scope:** `opencode.jsonc` `mcp` block; every agent frontmatter
`tools:` line; a `runtime-and-deps.md` amendment (new category); a stdlib-only
leak test analogue. Low complexity.

**Risk:** Low technical risk, but **high risk of not meeting the goal** — it is
the easy build that doesn't fix contamination.

### Approach B: Boundary-side pre-context compression (opencode `tool.execute.after` transform)

**Summary:** A Tier-3 opencode plugin intercepts verbose tool RESULTS in
`tool.execute.after` and replaces `output.output` with a compressed form
(calling Headroom's library/MCP out-of-band) **before the result enters the
subagent's context.**

**Tradeoffs:**
- Pro: **the true fix** — compresses before contamination, exactly matching the
  stated goal; works uniformly for every role because it lives at the delivery
  seam, not per-agent.
- Pro: the seam is real and already used by enforcement plugins
  (`advance-hook.ts` reads `output.output`).
- Con: **UNVERIFIED that mutating `output.output` in the after-hook propagates
  into context** (E3) — the docs only demonstrate mutation on the before-hook
  and `shell.env`; Gleipnir's probe used the after-hook read-only. If it does
  not propagate, this approach is impossible on the current substrate.
- Con: architecturally heavier and **closer to a trust-path transform** — even
  though it is "just" compression, it is code that rewrites tool output on the
  path to a reasoning agent. It must be provably confined to non-evidence
  content (D4) or it violates Constraint 3.
- Con: mid-port to pi.dev risks building it twice; the pi `tool_call` hook's
  mutation semantics are equally unverified.

**Estimated Scope:** a new Tier-3 plugin (agent-unwritable), a spike to verify
mutation propagation, a content-exclusion allowlist (D4), the dependency
category, a fail-open contract. Medium-high complexity.

**Risk:** **High** — one load-bearing unverified assumption (mutation
propagation) and a genuine trust-boundary-proximity concern.

### Approach C: Defer / reject (do nothing now)

**Summary:** Conclude that the trust-boundary + dependency-weight cost exceeds
the hygiene benefit on current evidence, and defer until either (a) the pi.dev
port settles the boundary-side seam, or (b) a lighter compressor with a
verified output-mutation path appears.

**Tradeoffs:**
- Pro: preserves the minimal trusted surface that is itself a G-1/G-2 asset
  (`runtime-and-deps.md`: "fewer dependencies = smaller trusted surface").
- Pro: the biggest coding-agent contamination sources (source, grep) are
  largely NOT what Headroom compresses (E4) — the fit for Gleipnir's heaviest
  workload is weak; the strong wins (JSON, logs) are a narrower slice.
- Pro: avoids building boundary-side wiring twice across the pi.dev port.
- Con: leaves the real hygiene problem unaddressed for JSON/log-heavy
  delegations where Headroom genuinely would help.
- Con: status-quo has its own cost (do not let it get a free pass — see bias
  check).

**Estimated Scope:** none (a decision record only).

**Risk:** Low — fully reversible; the assessment can be re-run when the substrate
or the tool changes.

---

## Decision Analysis

> Six decisions. D1 is the lead (architectural tradeoff → Second-Order Thinking +
> Pre-Mortem + a Hypothesis on the load-bearing unknown). D2/D6 are bounded
> choices (Weighted Matrix / Reversibility+Pros-Cons-Fixes). D3/D4/D5 are
> constraint-shaped (the trust invariant fixes much of D3/D4). All
> recommendations are ADVISORY input to the operator's convergence, never the
> decision.

### D1 — Compression seam: client-side vs boundary-side vs hybrid vs reject

**Framework:** Architectural tradeoff → **Second-Order Thinking + Pre-Mortem**,
plus a **Hypothesis-Driven** gate on the one load-bearing unknown.

**Hypothesis (the gate):** *If* we mutate `output.output` in a
`tool.execute.after` plugin, *then* the subagent's context receives the
compressed text instead of the raw output, *because* opencode applies hook
`output` mutations to the value it forwards. **Key assumption:** after-hook
`output.output` is a mutable transform seat, not observation-only.
**Evidence for:** before-hook `output.args` and `shell.env` `output.env` are
documented as mutable; the hook signatures are symmetric. **Evidence against:**
the docs NEVER show an after-hook mutating `output.output`;
`hook-probe-findings.md` and `advance-hook.ts` treat it read-only.
**Confidence: LOW.** **Validation: a required spike** — a throwaway plugin that
rewrites `output.output` for one tool and inspects whether the model's next turn
sees the rewritten text. Boundary-side is **not decidable without this spike.**

**Second-order (Approach B, boundary-side):**
- Near-term first-order: cleaner windows before contamination. Second-order: a
  Tier-3 transform now sits on the tool→agent path; every future reviewer must
  reason about whether it touched evidence.
- Far-term first-order: a reusable hygiene seam. Second-order: it becomes a
  place where a bug (or a poisoned compression backend) can silently alter what
  an agent reasons over — a G-6-adjacent influence surface, even though
  compression is not "memory." Third-order: if the pi.dev port changes hook
  semantics, the seam must be re-verified or it fails open silently.

**Pre-Mortem (assume boundary-side shipped and failed at 6 months):**
| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | `output.output` mutation never propagated; "compression" was a silent no-op | H | H | The D1 spike — gate the whole approach on it |
| 2 | Compression fired on evidence content (a verdict, a diff feeding attestation) and altered a reasoning input | M | H | D4 exclusion allowlist enforced IN the plugin, fail-closed on any `.gleipnir/**`-sourced or broker-sourced output |
| 3 | CCR TTL expired; agent retrieved a dead hash mid-delegation | M | M | D5 scope: within-delegation only; never hand a hash across delegations |
| 4 | pi.dev port changed hook shape; seam silently fails open | M | M | Defer boundary-side until port settles (ties to D1=reject-for-now) |
| 5 | Heavy dep destabilised an operator box (ONNX/AVX2/model fetch) | M | M | D3: host-level optional, never in any image, graceful absence |

**Options & recommendation:**
- **Client-side (A):** trivial, safe, but does not fix contamination.
- **Boundary-side (B):** the real fix, but gated on an unverified assumption and
  carries trust-path-proximity.
- **Hybrid (both):** ⚠️ see Scope Creep bias — "do both" is often decision
  avoidance. A *sequenced* hybrid is legitimate ONLY as "spike B; ship A as the
  interim if B is blocked" — not as "wire both permanently."
- **Reject/defer (C):** honest given LOW confidence in B's feasibility + weak
  fit for the heaviest (code/grep) workload.

**Recommendation (ADVISORY):** **Run the D1 spike FIRST.** If the spike shows
`output.output` mutation propagates → **boundary-side (B)** is the approach that
matches the goal. If it does not → **defer/reject (C)**, because client-side (A)
does not solve the stated hygiene problem and is not worth a new heavy dependency
category on its own. Do **not** ship a permanent hybrid.

**Bias warnings:**
- ⚠️ *Scope Creep Bias:* "both/hybrid" is the tempting non-choice. Force the
  spike-gated sequence instead of wiring both.
- ⚠️ *Bandwagon Effect:* Headroom lists opencode and pi.dev as supported targets;
  "it supports us" is not "it fits our per-role bounded-delegation model" — the
  proxy explicitly does not (E2).

### D2 — Reachability form: Headroom's MCP server vs thin Gleipnir wrapper vs proxy

**Framework:** **Weighted Decision Matrix.**

| Criterion | Weight | Headroom MCP server | Thin GL wrapper (lib) | Proxy |
|---|---|---|---|---|
| Fits shared-service / per-role model | 9 | 9 (81) | 8 (72) | 2 (18) |
| Minimises new Gleipnir trusted code | 8 | 9 (72) | 4 (32) | 7 (56) |
| Reuses `broker-mcp.md` precedent | 7 | 9 (63) | 6 (42) | 2 (14) |
| Keeps Headroom outside trust boundary | 10 | 8 (80) | 6 (60) | 3 (30) |
| Boundary-side capable (D1=B) | 6 | 4 (24) | 7 (42) | 9 (54) |
| **Total** | | **320** | **248** | **172** |

**Recommendation (ADVISORY):** **Headroom's own MCP server**, wired exactly per
`broker-mcp.md`, for the client-side/on-demand form. If D1 converges
boundary-side, the plugin calls Headroom out-of-band (library or the same MCP
server invoked by framework code, not by the agent). **Reject the proxy** —
per-launch, whole-session, blind to per-role boundaries, and sits on the
model-call path (trust-proximity). **Reject a thin wrapper** unless boundary-side
needs a library call the MCP server can't provide — it adds Gleipnir-owned code
around the same heavy dependency for little gain.

**Bias warnings:** ⚠️ *IKEA Effect* pre-empted — do NOT build a wrapper just to
"own" the interface; the external MCP server is less Gleipnir code to trust.

### D3 — Dependency / trust-boundary posture (isolation model)

**Framework:** constraint-shaped (Constraint 3 fixes the answer) → **Pros-Cons-Fixes.**

**Proposed isolation model:** Headroom is an **OPTIONAL, operator-installed,
host-level service** in a **NEW `runtime-and-deps.md` dependency category:
"external host-level optional service."** Concretely:
- **NEVER** in any sandbox image (lean or broker) — it needs network at install
  time, incompatible with `--network=none`; the sandbox stays Headroom-free.
- **NEVER** a peer/runtime dependency of the enforcement core, the brokers, or
  any Gleipnir component (`import headroom` appears nowhere in `src/gleipnir/**`).
- **Not even broker-class** — brokers run as in-session stdio subprocesses inside
  the session boundary; Headroom is a separate operator-managed install the
  per-role grants merely *point at IF present*.
- **Graceful absence** = the default posture: no Headroom installed ⇒ the MCP
  tools simply never surface (existing deny-list mechanics), and any
  boundary-side plugin fails open to raw output.

| Con | Fix |
|---|---|
| Heavy dep could destabilise operator boxes | Optional + graceful absence; the operator opts in per box |
| A new category dilutes the clean 3-category model | Draw it as sharply as the broker amendment; add a leak test that `headroom` never imports into `src/gleipnir/**` |
| Host-level service is un-sandboxed | Acceptable ONLY because it never touches evidence/enforcement (enforced by D4) and never enters the sandbox |

**Recommendation (ADVISORY):** adopt the "external host-level optional service"
category with the four rules above; require the new `runtime-and-deps.md`
amendment + a `test_headroom_no_leak.py` analogue before any wiring merges.

### D4 — Evidence/trust rule (G-3/G-6 safety) — concrete and falsifiable

**Framework:** **Pre-Mortem-derived exclusion rule** (must be reviewer-checkable).

**Proposed rule (falsifiable, greppable):** Headroom compression MUST NOT be
invoked on — and any boundary-side plugin MUST fail-closed-to-raw (never
compress) for — content in ANY of these classes:
1. **Any content read from `.gleipnir/**`** (plans, decisions, agents, skills,
   keys, logs, memory, lessons, stage-role-map) — the evidence/policy path.
2. **Any tool output from the `gleipnir-git_*` or `gleipnir-pm_*` broker tools**
   (commit/push/issue results — evidence-adjacent, and E-1-relevant).
3. **Any HMAC marker / attestation payload / bridge file** (`pipeline-state.json`,
   `keys/**` digests, `validateMarker`/`decideFromExit`/`canUse` inputs/outputs).
4. **Any spec-review / quality verdict text** (the reviewer transcript
   `advance-hook.ts` forwards — compressing it would corrupt the judge input).
5. **Plan/decision-record file bodies** being read for authoring.

**Enforcement form:** for boundary-side (B), the plugin's transform is
**allowlist-in, not denylist-out**: it compresses ONLY tool outputs from an
explicit set of known-verbose, non-evidence tools (e.g. generic `read` of
non-`.gleipnir` JSON/logs, test-runner output) and passes everything else
through untouched. For client-side (A), it is a documented agent instruction
plus the same source-path check where the plugin can see it. A reviewer checks
the rule by grepping the plugin for the `.gleipnir/**` and broker-tool source
guards and confirming the allowlist is closed.

**Recommendation (ADVISORY):** adopt classes 1-5 as a hard exclusion; implement
boundary-side as allowlist-in (fail-closed to raw for anything not explicitly
allowed). This keeps Constraint 3 falsifiable rather than "be careful."

**Bias warnings:** ⚠️ *Availability Heuristic* — do not scope the rule only to
the evidence types we happen to recall (HMAC markers); the allowlist-in form is
safe against the ones we forgot.

### D5 — CCR retrieval semantics vs bounded delegations

**Framework:** **Pros-Cons-Fixes** over scope options (within-delegation vs
across-delegation).

**Analysis:** Headroom's local store TTL is 1 hour (MCP), 30 min (proxy). A
Gleipnir subagent delegation is typically short-lived (well under an hour); the
orchestrator's session spans many delegations. A hash minted in one delegation
and handed to a later one risks (a) TTL expiry between delegations, (b) the
compressed marker travelling as a *pointer to state in a host-level service the
receiving agent may not even share*, and (c) an evidence-provenance muddle if a
hash ever pointed at excluded content.

| Scope | Con | Fix |
|---|---|---|
| Across delegations | TTL expiry; cross-agent store sharing; provenance muddle | Don't — forbid handing hashes across delegation boundaries |
| Within a single delegation | Retrieval only useful while that agent runs | Matches CCR's 1h TTL comfortably; the agent that compressed can retrieve |

**Recommendation (ADVISORY):** **scope CCR retrieval to WITHIN a single
delegation's lifetime.** A hash is a private, ephemeral detail of the agent that
minted it; it is NEVER part of a delegation's returned result and is NEVER handed
to another agent or the orchestrator. This aligns with the TTL and keeps
compressed pointers out of the cross-delegation evidence flow.

### D6 — Default posture / reversibility

**Framework:** **Reversibility Filter → Regret Minimisation**, against the
`broker-mcp.md` principle "a guard/tool that nags more than it helps gets routed
around."

**Reversibility:** Two-way door. Default-off ↔ default-on is one frontmatter/
config line; nothing persists.

| Option | Regret if wrong | Regret if not chosen | Max |
|---|---|---|---|
| Default-off (opt-in per session/role) | 3 (some hygiene left on the table) | 2 | 3 |
| Default-on for known-verbose classes | 7 (silent compression of something it shouldn't, or noise) on a NEW heavy unproven dep | 4 | 7 |

**Recommendation (ADVISORY):** **default-OFF**, operator opts in per-session or
per-role. Rationale: Headroom is new, heavy, fails open silently, and its fit for
Gleipnir's heaviest workload (code/grep) is weak; making it default-on would put
an unproven transform on-by-default over a non-negotiable trust constraint. The
`broker-mcp.md` "don't nag" principle argues for keeping the safety-critical
default conservative and letting willing operators opt in, exactly as the broker's
hygiene checks are opt-in while only its true-safety check is always-on.

**Bias warnings:** ⚠️ *Status Quo Bias* checked — default-off is recommended on
its merits (new/heavy/unproven/weak-fit), not merely because off is the current
state; a JSON/log-heavy operator SHOULD turn it on.

---

## Selected Approach

**CONVERGED: D1 = Defer/reject. No Headroom integration is built now, in any
form (neither client-side MCP tool nor boundary-side hook).** This is the
brainstorm's own recommended option (Approach C), converged by the operator with
the orchestrator via the `question` tool this session.

**Operator's rationale (three reasons, matching the D1 analysis above):**

1. **Boundary-side (Approach B) is not proven buildable on the current pi.dev
   substrate.** The load-bearing unknown from E3/D1 is unresolved: the pi.dev
   `tool_call` hook is documented as **block/allow-only**, with **no demonstrated
   output-content rewrite path**. Without a verified way to mutate the tool
   result before it enters the subagent's context, the "true fix" is not
   achievable — this is exactly the LOW-confidence hypothesis the D1 spike was
   meant to gate, and the substrate evidence resolves it against B.
2. **Client-side (Approach A) does not actually fix the stated contamination
   problem.** By the time the agent could call a compress tool, it has **already
   seen the verbose output** — the contamination has already happened. A is the
   easy build that does not address the hygiene goal (per Approach A's own con
   and the D1 recommendation).
3. **The git-diff-distill pilot already covers the sharpest concrete pain
   point.** A separate, already-shipped PR (git-diff-distill) already addresses
   the sharpest concrete case — large git diffs — so the strongest slice of the
   real problem is already being handled without a new heavy dependency category.

**Consequence — D2-D6 are MOOT.** Each of D2 (reachability form), D3 (dependency
posture), D4 (evidence/trust exclusion rule), D5 (CCR retrieval scope), and D6
(default posture) was downstream of or conditional on D1 producing a "build"
outcome. With D1 = reject, none of them applies; their ADVISORY recommendations
above stand only as the historical analysis, not as decisions to act on.

**This is a decision to REVISIT, not a permanent closure.** Per the brief's own
D1 analysis (Approach C is fully reversible; the assessment can be re-run when
the substrate or the tool changes), this non-build decision can be reopened if
either:
- **(a)** the pi.dev port ever demonstrates a **working output-rewrite hook**
  (i.e. a verified path to mutate tool-result content before it reaches the
  subagent's context — resolving the E3/D1 unknown in B's favour); or
- **(b)** a **lighter-weight compressor with a verified mutation path** appears
  (removing both the heavy-dependency-category cost of D3/D5 and the
  unproven-mechanism risk of B).

**Follow-up (NOT done now): author a durable Tier-3 decision record.** This
converged non-build decision SHOULD eventually be recorded in a durable Tier-3
decision record — e.g. `.gleipnir/decisions/headroom-integration.md` — capturing
D1 = defer/reject, the three reasons above, the two reopen triggers, and D2-D6
as moot. **This is NOT done here:** no roster role holds Tier-3 write access —
including the orchestrator in the current session — so the durable record cannot
be authored now. This is a **named follow-up for the operator or a future
build-mode session**, flagged so the decision is not lost when this Tier-0
(disposable) brief is eventually cleaned up.

## Open Questions (RESOLVED-BY-DEFERRAL — no longer pending)

With D1 = defer/reject, the questions below are **resolved by deferral**: none
requires an answer now, because nothing is being built. They are retained as the
conditions that would need revisiting **if** the decision is reopened per trigger
(a) or (b) above.

- **D1 spike (mutation propagation)** — no longer a live prerequisite: the pi.dev
  substrate evidence (block/allow-only `tool_call` hook, no output-rewrite path)
  already resolves the boundary-side question against B. The spike would only be
  revisited under reopen-trigger (a).
- **Timing vs the pi.dev port (S1-S9)** — moot now; subsumed into reopen-trigger
  (a) (revisit only once the port demonstrates a working output-rewrite hook).
- **Weak fit for code/grep workloads (E4)** — resolved: it reinforced defer, and
  the sharpest concrete case (large git diffs) is already covered by
  git-diff-distill.
- **New `runtime-and-deps.md` "external host-level optional service" category** —
  not authored: it was only needed if something was being built. Revisit only on
  reopen.

## Scope Sketch

| Area | Files/Modules Likely Affected (IF adopted) |
|---|---|
| MCP wiring (A) | `opencode.jsonc` `mcp` block; every `.gleipnir/agents/*.md` `tools:` line |
| Boundary-side (B) | NEW Tier-3 `.gleipnir/plugins/headroom-hygiene.ts` (agent-unwritable); a D1 spike plugin (throwaway) |
| Dependency policy (D3) | `decisions/runtime-and-deps.md` amendment (new category); `tests/test_headroom_no_leak.py` |
| Trust rule (D4) | exclusion allowlist inside the plugin + reviewer-checkable grep guards |
| Decision record | a new `decisions/headroom-*.md` recording the operator's converged D1-D6 |
```
