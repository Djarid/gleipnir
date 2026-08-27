# Design Brief: Distill — Gleipnir-native tool-output context compression

> **STATUS: SUPERSEDED — DO NOT PLAN FROM THIS FILE.** The D1/D2/D3/D4 Decision
> Analysis below is **WRONG and superseded** by direct operator convergence with
> the orchestrator. The design was **reframed from first principles and narrowed
> to a pilot.** The live, CONVERGED brief is
> **`.gleipnir/plans/git-diff-distill-brainstorm.md`** — plan from that file.
>
> What changed (summary; full detail in the successor's `## Already-converged`):
> - **D1 was axiomatically wrong, not just re-decided.** "A client-side tool an
>   agent calls" is ruled out **permanently**: LLMs don't decide — Axiom 1 / G-5
>   put the trigger in **code**, never model judgment. Compression is triggered
>   deterministically by code, baked into a tool Gleipnir already owns (the git
>   broker). The pi.dev host-hook path is deferred to host built-ins only.
> - **D2 is resolved to "no new tool/MCP surface, ever, for this"** — a global
>   MCP contaminates every session's context (the very problem). Compression is
>   plain internal library code an existing tool calls.
> - **D3 is now a narrower per-field STRUCTURAL rule**, not a path-based blanket:
>   the truncation function receives ONLY diff text and returns diff text; it
>   structurally cannot touch the envelope, verdict, or commit metadata.
> - **D4 is moot**: broker-owned code is always-on above a coded threshold, no
>   opt-in/opt-out axis.
> - **Scope is much narrower:** ONE tool (`git_diff`), diff-shaped truncation,
>   the repo itself is the retrieval path (no CCR store).
>
> The original working-name note is retained below for historical context only.
>
> **Working name (historical).** This draft called the capability **Distill**
> (module `src/gleipnir/distill/`, tool verb `distill`). The successor uses a
> diff-specific module name (e.g. `diff_truncate.py`) and NO tool verb at all.

## Problem Statement

Gleipnir subagents (`gleipnir-code`, `quality-reviewer`, `gleipnir-plan`, and
others) suffer **context contamination**: verbose tool outputs — large git
diffs, `grep`/search dumps, JSON blobs, logs — flood their context windows and
degrade reasoning quality. This is a **quality** concern (bad reasoning from a
polluted context), not a token-cost concern. The fix is a Gleipnir-native
capability that reduces high-verbosity tool output to its signal-bearing
essence (imports/signatures/errors/anomalies preserved; bodies/boilerplate
compressed) before or shortly after it reaches an agent's context.

## Constraints

- **No third-party consumption.** No `headroom-ai` package/binary/MCP
  server/proxy/ML model; no `pip install headroom-ai`; no network fetch of
  ONNX/HuggingFace assets; no spawning their process. (Already-converged item
  1 — trust/exfil + dependency-weight.)
- **Brownfield.** Built directly into the existing `src/gleipnir/**` Python
  codebase, sized to Gleipnir's actual need — not a green-field sub-project.
- **Stdlib-only enforcement-core discipline** (`decisions/runtime-and-deps.md`).
  Python core logic uses only the stdlib (`ast`, `json`, `difflib`, `re`,
  arithmetic). Any non-Python parser dependency (`tree-sitter`) would be a
  bounded, justified, isolated broker-layer dependency following the exact
  `mcp`-SDK precedent — never in the stdlib-only core.
- **`--network=none` sandbox compatible** (`decisions/language-agnostic-sandbox.md`).
- **Least-privilege capability grant.** Must not become a universally-granted
  capability by accident; scoped in the existing per-role `tools:` grant model
  (`decisions/broker-mcp.md`, `stage-role-map.md`).
- **Trust-tier exclusions.** Must never touch `.gleipnir/**` content, broker
  I/O, attestation/HMAC payloads, or review-verdict / plan / decision bodies
  (D3 below).

## Provenance

The following attribution text is authored to survive verbatim into the
eventual module docstring / header comment. It records that the **idea** (not
the code) is drawn from Headroom, satisfies the operator's honesty/provenance
practice, and stays clear of trademark use:

> ```
> Approach inspired by Headroom's SmartCrusher / CodeAwareCompressor
> techniques (https://github.com/headroomlabs-ai/headroom, Apache-2.0).
> This is an independent, Gleipnir-native implementation of the documented
> behaviour — a clean-room reimplementation from Headroom's public
> documentation, NOT a port or derivative of their source. No Headroom code,
> binary, package, model, or network service is consumed. Headroom's
> trademarked names (Headroom, SmartCrusher, CodeCompressor,
> CodeAwareCompressor, Kompress) are NOT used for this module or its
> capabilities; Apache-2.0 §6 grants no trademark rights and none are claimed.
> ```

**License finding (recorded):** clean-room reimplementation from documented
*behaviour* (not from their source) does not trigger Apache-2.0's
redistribution conditions; the attribution above is a voluntary
honesty/provenance practice, not a license obligation. The trademark-avoidance
is a genuine §6 constraint and is load-bearing for naming.

## Already-converged

These were decided directly by the operator through conversation with the
orchestrator (not the `question` tool, but just as real). They are **DECIDED —
not up for re-litigation** in the Decision Analysis below. Recorded here with
reasoning preserved.

1. **Do NOT consume the third-party Headroom system in any form** — no package,
   binary, MCP server, proxy, or ML model; no `pip install`; no network fetch.
   Two load-bearing reasons:
   - **Trust/exfil:** Headroom's `ContentRouter` records ALL compressions to
     "TOIN" (Tool Output Intelligence Network) for **cross-user** learning, and
     CCR retrieval feeds that same loop — a phone-home/cross-user-pattern-
     learning subsystem baked into their default pipeline. Exactly the exfil
     shape the operator is avoiding.
   - **Dependency weight:** their real implementation is Rust
     (`crates/headroom-core`) + ONNX Runtime + a HuggingFace model + optional
     Serena — none of it fits Gleipnir's minimal-trusted-surface identity or
     its `--network=none` sandbox.
2. **Brownfield build** — our own Gleipnir-native reimplementation, directly
   into `src/gleipnir/**`, sized to Gleipnir's actual need (code/JSON/log
   verbosity), not Headroom's full feature surface.
3. **Attribute the IDEA to Headroom, not the code** — see `## Provenance`. Do
   NOT use their trademarked names for our modules/capabilities.
4. **Concrete techniques to draw the IDEA from** (confirmed from their docs):
   - **JSON/array compression** ("SmartCrusher"): statistical selection over an
     array — keep first N% / last N% (pagination/recency), keep 100% of
     error-shaped items, keep statistical anomalies (>2 std dev on a numeric
     field — plain arithmetic, no ML), dedup identical items, sample the
     remainder. Their BM25/embedding "relevance-to-query" dimension is the one
     ML-flavoured piece — **SKIP it or replace with a trivial stdlib
     keyword-overlap heuristic** (`difflib`), no embeddings/model.
   - **Code compression** ("CodeAwareCompressor"): AST-aware truncation — parse
     source, ALWAYS preserve imports, function/method signatures, class defs,
     type annotations, decorators, error handlers (try/except); COMPRESS
     function bodies (replace with `# ... (N lines compressed)`) and verbose
     docstrings/comments. Python needs ZERO new deps — stdlib `ast`
     parse/walk/preserve/truncate, re-render via `ast.unparse` (3.9+) or
     line-boundary text manipulation. Non-Python (TS `pi-package` side, if ever
     in scope): stdlib has no parser → either skip non-Python (narrower,
     zero-dep, defensible) or accept a bounded justified `tree-sitter`
     dependency per the `mcp`-SDK precedent.
5. **Explicitly REJECTED — do not resurrect:** TOIN/cross-user telemetry (exfil
   shape); the ML `Kompress` text-compression model (network+ML dependency, out
   of proportion); image compression (irrelevant); `CacheAligner`/output-token
   verbosity-shaping (a different problem — LLM-provider prompt-cache/output-cost,
   not context hygiene; out of scope for this thread).

## Approaches Considered

The genuinely open design space is four coupled questions (D1–D4). Each is
analysed in `## Decision Analysis`. The approaches are expressed there as the
options under each decision, since the "approach" for this brief IS the
combination of D1/D2/D3/D4 choices.

## Decision Analysis

### D1 — The seam: where does compression happen?

> **RESOLVED — SUPERSEDED. The analysis below is WRONG; do not act on it.**
> The "client-side tool vs boundary hook" framing was axiomatically wrong (LLMs
> don't decide — the trigger is code, per Axiom 1 / G-5). Resolved by
> `git-diff-distill-brainstorm.md` `## Already-converged` items 1–2:
> compression is triggered deterministically by code, baked into the git broker
> Gleipnir already owns; the pi.dev host-hook path is deferred to host built-ins
> only. Recommendation text below (Option A / A-now-then-B) is DEAD.

**Decision type:** architectural tradeoff, gated on an empirical
host-capability fact → **Second-Order Thinking + Hypothesis-Driven Analysis**
(the auto-selection primary for an architectural tradeoff, plus Hypothesis-
Driven because the whole of Option B hinges on an unverified fact I investigated
directly).

**Options:**

- **(A) Client-side / on-demand tool.** Expose a `distill` tool any granted
  subagent calls AFTER receiving a verbose output, to compress it. Trivial to
  wire — identical shape to any existing bounded tool / the `gleipnir-git`
  broker grant model.
- **(B) Boundary-side / automatic.** Intercept verbose tool output BEFORE it
  reaches the subagent's context via a hook on the tool-output path, rewriting
  the output transparently so the agent never sees the verbose form.
- **(A-now-then-B) Sequenced.** Ship A now (certainly buildable); investigate/
  prototype B as a follow-up (gated on the host-capability finding below).

**Hypothesis (Option B): "If we hook the tool-output path, we can REWRITE the
output content the agent sees."**

Key assumption: the host exposes an after-tool hook whose returned/mutated
value **replaces** the output delivered to the agent's context.

**Evidence — investigated directly against primary sources this session (not
assumption):**

- **opencode `tool.execute.after`** — authoritative pinned type
  (`packages/plugin/src/index.ts@dev`, transcribed in
  `.gleipnir/plans/hook-probe-findings.md` lines 86–97):
  `"tool.execute.after"?: (input, output: { title; output: string; metadata }) => Promise<void>`.
  Return type is **`Promise<void>`** — the after-hook returns nothing. Nothing
  in the probe findings, nor in Gleipnir's own `advance-hook.ts` (the ONLY
  existing `tool.execute.after` consumer), demonstrates that **mutating
  `output.output` propagates back into the agent's context.** `advance-hook.ts`
  *reads* `output.output` (the reviewer transcript) and forwards it to a
  subprocess; it **never writes it back**. There is **no output-rewrite
  precedent** in `.gleipnir/plugins/*.ts`.
- **opencode `tool.execute.before`** — the ONLY documented mutation channel is
  `output.args` (the `.env`-block example rewrites/inspects *input args*). That
  is input-argument rewriting, **not output-content rewriting**, and it fires
  before the tool runs (so the verbose output does not yet exist).
- **pi.dev (`@earendil-works/pi-coding-agent`)** — the in-flight port. The only
  tool hook used anywhere in `pi-package/src` is `pi.on("tool_call", …)` whose
  return shape is strictly `{ block: true, reason } | undefined`
  (`enforcement.ts`) — **block-or-allow only, no output-rewrite channel.** A
  grep of `pi-package/src` finds **no `tool_result`/after-style hook** in use
  at all; the only other registered events are `session_start` and
  `session_before_compact`.

**Confidence in Option B buildability: LOW / NOT CONFIRMED.** On the primary
sources I actually read, **output-content mutation on the after-hook is NOT
confirmed possible** on either host. opencode's after-hook is typed
`=> void` with no demonstrated write-back path; pi's tool hook is
block/allow-only. The orchestrator's recalled pessimistic prior finding is
**corroborated, not overturned**, by what I found. Option B is therefore gated
on a capability that current evidence says is absent — it would require either
(i) a live spike proving `output.output` mutation propagates on the installed
opencode build (contradicting the `=> void` type), or (ii) a different
mechanism entirely (e.g. wrapping the tool itself, or a host feature not
present today).

**Validation to lift confidence (if B is ever pursued):** a 1-shot probe hook
on the installed opencode build that mutates `output.output` for a known
verbose tool and checks whether the *agent's* subsequent context shows the
mutated or original text. Until that probe returns positive, B is not
buildable.

**Second-order view (why A is not merely a fallback):**
- *Near term (A):* the agent still receives the verbose output once, then calls
  `distill` to get a compressed form it can choose to reason over. Contamination
  is only mitigated to the extent the agent **discards/replaces** the original
  in its own context — which depends on how tool-call results are represented
  in the host's context (on opencode, the original tool result remains in the
  message history; the compressed form is an *additional* message, so A
  **reduces** the agent's reliance on the verbose form but does not *remove* the
  verbose tokens already in context). A is a genuine partial fix, not a no-op:
  it gives the agent a clean artifact to reason from and to carry forward across
  its own summarisation/compaction.
- *Far term (B):* only B removes the verbose form entirely (the agent never sees
  it) — the true fix — but it is gated on the unverified host capability above.
- *Key insight:* A and B are **not** redundant; A is the buildable-today partial
  mitigation and B is the complete fix pending a host capability. Shipping both
  permanently with no reason would be Scope Creep; sequencing them is not.

**Bias check (D1):**
- ⚠️ *Scope Creep Bias* — a permanent A+B hybrid "to be safe" would be deferring
  the choice by building everything. Mitigation: the recommendation is a
  **sequence with an explicit gate** (B only if the probe passes), not a
  permanent hybrid.
- ⚠️ *Dunning–Kruger* (checked, low) — confidence about B's buildability is
  explicitly LOW and grounded in primary-source reads, not asserted.
- Availability/Confirmation: checked — the pessimistic prior was independently
  re-derived from the type signatures this session, not accepted second-hand.

**Recommendation (D1): Option A-now-then-B** — ship **A** (client-side
`distill` tool) now, because it is certainly buildable and is a real partial
mitigation; **defer B** (boundary-side rewrite) to a follow-up **explicitly
gated on a live probe** proving the installed host can rewrite tool-output
content. Do **not** commit to a permanent hybrid. If the operator's priority is
the *complete* contamination fix over shipping-soon, the alternative is to run
the B-probe FIRST and only then choose A-vs-B — surfaced for the operator.

---

### D2 — Where does this live, and how is it reached?

> **RESOLVED — SUPERSEDED. The analysis below is WRONG; do not act on it.**
> Resolved by `git-diff-distill-brainstorm.md` `## Already-converged` item 3:
> **no new tool/MCP surface of any kind, ever, for this** — a global MCP
> contaminates every session's context (the very problem being fixed).
> Compression is plain internal library code an existing Gleipnir-owned tool
> calls before returning. The MCP-broker recommendation below (Option 2) is
> DEAD; the "plain library" idea survives only as "internal library code," NOT
> as any agent-reachable surface.

**Decision type:** architectural placement + capability-exposure → **Weighted
Decision Matrix** (multi-option comparison across placement criteria).

**Options for exposure of the core Python logic (`src/gleipnir/distill/`,
sibling to `broker/ bus/ engine/ ledger/ preflight/ sandbox/ verify/`):**

- **(1) Plain importable library function.** A Python module any Python-side
  tool call imports and calls. No new server, no new grant surface.
- **(2) Broker-shaped MCP stdio server** (`gleipnir-distill`), mirroring
  `broker-mcp.md` exactly: stdio server, tools enabled globally, per-role
  DENY-LIST `tools:` grant (`gleipnir-distill_*: false` for roles that must not
  hold it). Reachable by any host (opencode today, pi tomorrow) through the
  same MCP surface the git/pm brokers already use.
- **(3) Both** — library for Python-internal callers, broker for cross-host
  reach.

| Criterion | Weight | (1) Library | (2) MCP broker | (3) Both |
|---|---|---|---|---|
| Reachable by ALL subagents incl. future pi/TS side | 9 | 3→27 | 9→81 | 9→81 |
| Fits existing least-privilege grant model (`tools:` deny-list) | 8 | 4→32 | 9→72 | 6→48 |
| Minimal new trusted surface (no new `mcp` server process) | 7 | 9→63 | 4→28 | 3→21 |
| Implementation simplicity / smallest blast radius | 7 | 9→63 | 5→35 | 4→28 |
| Precedent already ratified in codebase | 6 | 5→30 | 9→54 | 6→36 |
| **Total** | | **215** | **270** | **214** |

**Recommended: Option (2) MCP broker** (score 270), **but with a strong
caveat** tied to D1. The matrix favours the broker because it is the *only*
option that cleanly satisfies "reachable by all subagents including the future
pi side" AND "expressed in the existing per-role deny-list grant model" — the
exact two properties `broker-mcp.md` was built to provide. HOWEVER: if D1
converges on **A-only for now** and the immediate callers are Python-side, the
**library (Option 1)** is materially simpler and adds no new server to the
trusted surface — its only loss is cross-host reach, which is not yet needed if
the pi port has not landed compression callers.

**The D1↔D2 coupling (surfaced for the operator):** the broker's value is
"reachable by every role across hosts through one grant surface." That value is
only *realised* if compression is invoked as a tool by agents across hosts
(the A seam) — which is exactly D1(A). If D1 chose B (boundary hook), the core
logic would be called by the *plugin/framework code*, not by agents, and a
plain library (Option 1) would suffice with no broker at all. So:
- **D1 = A (tool)** → **D2 = (2) broker** (agents call it; needs the grant
  surface).
- **D1 = B (hook)** → **D2 = (1) library** (framework code calls it; no agent
  grant needed).
- **D1 = A-now-then-B** → start **(1) library** as the shared core, and add the
  **(2) broker** *thin wrapper* around it when A ships as a tool — the library
  is the reusable core either way, so this ordering wastes nothing.

**Bias check (D2):**
- ⚠️ *IKEA Effect* — building our own broker because we *can* mirror the
  precedent. Mitigation: the matrix explicitly credits the library's smaller
  surface; the recommendation is conditional on D1, not "broker because ours."
- ⚠️ *Bandwagon* (checked) — "the git/pm brokers are MCP so this should be too."
  Mitigation: fitness-for-purpose weighed via the D1 coupling, not precedent
  alone.

**Recommendation (D2):** build the **core as a plain library** in
`src/gleipnir/distill/` regardless (it is the reusable heart of every seam
choice), and **expose it as a `gleipnir-distill` MCP broker with a per-role
deny-list grant IF AND WHEN D1(A) ships it as an agent-callable tool.** Do not
build the broker if D1 converges on B-only. **Grant scope:** deny by default
for every role; allow `gleipnir-distill_*` only for the roles with genuinely
verbose inputs — candidate set `gleipnir-code`, `quality-reviewer`,
`gleipnir-plan` (see D4 for whether even they get it on-demand vs always).

---

### D3 — Evidence/trust exclusion rule

> **RESOLVED — SUPERSEDED. The analysis below is WRONG scope; do not act on it.**
> Resolved by `git-diff-distill-brainstorm.md` `## Already-converged` item 8:
> the path-based allowlist/denylist blanket below is replaced by a **narrower
> per-field STRUCTURAL rule**. Because compression is baked into the broker's
> OWN code by its OWN author, the truncation function receives ONLY raw diff
> text and returns diff text — it structurally never sees or touches the
> response envelope, verdict fields, or commit metadata. The `is_compressible`
> path predicate below is DEAD.

**Decision type:** risk-assessment / safety-invariant → **Pre-Mortem** (assume
the rule failed and something integrity-critical was mangled).

**The rule (allowlist-in, re-derived here — not cited from the superseded
brief):** Distill compresses **only** content it is explicitly allowed to
touch, and refuses (passes through untouched) everything else. Allowlist-in is
correct over denylist-out for the standard safety reason: a denylist silently
fails **open** on any category the author forgot to enumerate, and the cost of
that failure here is corrupting integrity-critical evidence; an allowlist fails
**closed** (an unrecognised input is passed through verbatim, never compressed),
which is the safe direction. Re-derived independently; consistent with the
general safety principle, no reliance on the superseded file.

**Allowlist (what MAY be compressed):** tool outputs of a small, named set of
**high-verbosity, non-authoritative** tool classes only — e.g. `read` of source
files, `grep`/`glob` result dumps, generic large `bash`-command stdout that is
NOT broker I/O, log text. Each allowed class is enumerated explicitly; anything
not on the list is passed through verbatim.

**Hard exclusions (NEVER compressed, even if large — asserted as an explicit
deny that takes precedence over any allow):**
- any content whose source path is under `.gleipnir/**`;
- broker tool I/O — any `gleipnir-git_*` / `gleipnir-pm_*` (and a future
  `gleipnir-distill_*`) tool input or output;
- attestation / HMAC marker payloads (the bridge marker, `verify/` marker
  text);
- spec-review / quality **verdict** text;
- plan / decision-record bodies (`.gleipnir/plans/**`, `.gleipnir/decisions/**`
  — already covered by the `.gleipnir/**` rule, restated for clarity).

**Pre-Mortem (assume the exclusion failed at 6 months):**

| # | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | A denylist gap let broker output through and a commit-diff secret-scan verdict got truncated, hiding a finding | M (if denylist) → L (allowlist) | H | Allowlist-in: broker I/O is simply never on the allow-list; unrecognised = pass-through |
| 2 | Compressor mangled an HMAC/attestation payload, breaking the cross-language MAC | L | H | Explicit hard-exclude of marker/attestation payloads; allowlist would already exclude by default |
| 3 | A reviewer verdict got "distilled" and the truncated form changed the judged outcome | L | H | Verdict text hard-excluded; allowlist covers by default |
| 4 | `.gleipnir/**` plan/decision body compressed, losing a load-bearing clause a downstream stage relied on | L | M | `.gleipnir/**`-path hard-exclude, allowlist default |
| 5 | Allowlist too aggressive → compresses something an agent needed verbatim, degrading (not corrupting) reasoning | M | M | Compression is lossy-by-design; make it **opt-in / thresholded** (see D4) and always report "N lines compressed" so the agent knows to re-fetch if needed |

**Top risks:** #1, #3 — both integrity-critical and both closed by
allowlist-in + explicit hard-exclude precedence. **Verdict: Proceed with
allowlist-in + explicit hard-exclusions.**

**Checkable form (for the eventual plan/tests):** a single `is_compressible(source_class, source_path) -> bool`
predicate that returns True only for an enumerated allow-set AND False for any
hard-excluded path/namespace, with the hard-exclude checked FIRST (deny takes
precedence). Unit-testable with one row per allow class and one per exclusion;
mirrors the `stage-role-map.md` "trust is a property of the path, encoded in
code" construction.

**Bias check (D3):**
- ⚠️ *Status Quo / Anchoring* (checked) — the superseded brief also preferred
  allowlist; I re-derived rather than inherited. No anchor accepted uncritically.
- No other detector triggered.

**Recommendation (D3):** **allowlist-in**, with an explicit hard-exclusion set
checked with **deny-precedence**, realised as one testable predicate. This is a
genuine safety invariant (see D4).

---

### D4 — Default posture: opt-in vs default-on

> **RESOLVED — SUPERSEDED (MOOT). The analysis below is WRONG; do not act on it.**
> Resolved by `git-diff-distill-brainstorm.md` `## Already-converged` item 7:
> the "opt-in vs default-on" axis does not apply. Because this is deterministic
> broker-OWNED code (not an agent-facing opt-in), it is simply always-on above a
> fixed coded threshold — no configuration, no carve-out, no judgment call. The
> opt-in-baseline-plus-carve-out recommendation below is DEAD.

**Decision type:** go/no-go on always-on enforcement → **Reversibility Filter →
Regret Minimisation**, judged against the `broker-mcp.md` principle ("only
genuine safety invariants are always-on; preferences are opt-in").

**Reversibility:** posture is a **Two-Way Door** — a config/threshold flip,
trivially reversible per role/session. This argues against over-analysing, but
the *quality* stakes (contaminated reasoning) warrant a considered default.

**The core question the operator must weigh:** is "prevent contamination"
closer to a **safety invariant** (always-on, like the secret-scan) or a
**preference** (opt-in, like protected-branch refusal)?

- Argument for **safety-invariant / default-on:** bad reasoning from a
  contaminated context is a real, silent quality-degradation risk; unlike a
  secret commit it is not catastrophic-irreversible, but it is *pervasive and
  invisible* — the agent does not know its context is polluted.
- Argument for **preference / opt-in:** compression is **lossy**. A wrong
  compression can *remove signal the agent needed*, which is itself a
  quality-degradation — so default-on trades one quality risk for another.
  `broker-mcp.md`'s principle is explicit: only *genuine safety invariants*
  (hard-to-undo harm, e.g. a committed credential) are always-on; everything
  else is opt-in to avoid a guard that "nags more than it protects" and gets
  routed around.

**Regret Minimisation (horizon: the framework's operating life):**

| Option | Regret if wrong | Regret if not chosen | Max regret |
|---|---|---|---|
| Default-ON (all verbose tools) | 7 — lossy compression silently drops needed signal; agents can't tell; erodes trust in the tool → gets disabled wholesale | 3 — some contamination persists that an always-on rule would have caught | 7 |
| Opt-in per role/session | 3 — some contamination persists until a role opts in | 4 — under-adoption; the fix exists but isn't used | 4 |
| **Default-on ONLY for a narrow, named, thresholded verbose class** (e.g. compress only when a `git_diff`/large-read/`grep` output exceeds a token threshold, for the roles in D2's candidate set) | 4 — a mis-tuned threshold occasionally over-compresses, but scoped and observable | 3 — narrow scope misses some contamination outside the named classes | 4 |

**Minimum-regret choice: opt-in as the baseline, with a narrow thresholded
default-on carve-out** — the third row and the second row tie at max-regret 4,
and they compose: opt-in everywhere, plus a *named, thresholded* auto-compress
for a small set of known-pathological classes (large `git_diff` from git-ops,
large file reads / `grep` dumps for the reviewer) where the verbosity is
reliably high and the signal-preservation (imports/errors/anomalies kept) makes
lossy compression low-risk.

**Alignment with `broker-mcp.md`:** this mirrors the git broker exactly —
**safety-critical piece always-on** (there: secret-scan; here: nothing is truly
safety-critical, so *nothing* is unconditionally always-on), **preferences
opt-in** (there: protected-branch; here: general compression), with a **narrow
thresholded default** only where the verbosity is reliably pathological and the
loss is bounded and reported. Contamination is judged **closer to a strong
preference than a hard safety invariant** — because the mitigation (compression)
is itself lossy, it fails the "hard-to-undo harm justifies removing operator
choice" test that secret-committing passes.

**Bias check (D4):**
- ⚠️ *Availability Heuristic* (checked) — "contamination is bad, so always
  compress" overweights the vivid contamination case and underweights the
  equally-real lossy-compression case. Mitigation: Regret Minimisation forces
  both regret directions onto the table.
- ⚠️ *Scope Creep* (checked, low) — the thresholded carve-out is narrow and
  named, not "compress everything by default."
- No other detector triggered.

**Recommendation (D4):** **Opt-in per role/session as the baseline** (the
`broker-mcp.md` default-OFF-for-preferences posture), **plus a narrow,
named, token-thresholded default-on carve-out** for a small set of reliably-
pathological verbose classes for the D2 candidate roles. Nothing is
unconditionally always-on, because the mitigation is lossy — contamination is a
strong preference, not a hard safety invariant. The exact threshold and the
carve-out class list are plan-stage tuning parameters, surfaced to the operator
for the go/no-go on whether ANY default-on carve-out is wanted at all (the fully
conservative alternative is pure opt-in, max-regret 4, also acceptable).

---

**Cross-cutting bias note:** across D1–D4, the two most relevant recurring
detectors were **Scope Creep** (resisted: D1 sequences rather than permanent-
hybrids; D4 carve-out is narrow) and **IKEA Effect** (resisted: D2 matrix
credits the smaller-surface library, D2 broker is conditional on D1). No
detector was suppressed; all 12 were checked.

## Selected Approach

**CONVERGED ELSEWHERE — see `.gleipnir/plans/git-diff-distill-brainstorm.md`.**
The operator converged this thread directly with the orchestrator, reframing it
from first principles and narrowing it to a pilot. The converged design is NOT
recorded here (this file is superseded); it lives in the successor brief's
`## Already-converged` and `## Scope for the pilot plan` sections. None of the
D1–D4 recommendations above is the decision — each is DEAD (see the RESOLVED
banners on their headings).

## Open Questions

> **SUPERSEDED — these are NOT open. Do not act on them.** All questions below
> are resolved or made moot by `git-diff-distill-brainstorm.md`, which has NO
> open decisions. Retained for history only.

- **D1 gating fact:** boundary-side rewrite (B) is **NOT confirmed buildable**
  on either host from primary sources; a live probe on the installed opencode
  build is required before B can be committed to. Operator to decide whether to
  ship A now or run the B-probe first.
- **D2↔D1 coupling:** D2's broker-vs-library choice is downstream of D1's
  seam choice (see the coupling table). The library core is built regardless.
- **D4 carve-out:** whether ANY default-on thresholded carve-out is wanted, or
  pure opt-in; and if a carve-out, the token threshold and the exact verbose-
  class list (plan-stage tuning).
- **Non-Python code compression:** in-scope now (accept bounded `tree-sitter`)
  or deferred/skipped (Python-only, zero-dep)? Only relevant once pi/TS-side
  callers exist.
- **Naming:** confirm/replace the working name **Distill** (`src/gleipnir/distill/`,
  tool `distill`). Pure rename if changed.

## Scope Sketch

> **SUPERSEDED — this scope is DEAD. Do not build from it.** The broad
> `src/gleipnir/distill/` + MCP-broker + boundary-hook scope below is superseded
> by the much narrower pilot scope in `git-diff-distill-brainstorm.md`
> `## Scope for the pilot plan` (one tool, one small module, diff-shaped
> truncation, no broker, no hook). Retained for history only.

| Area | Files/Modules Likely Affected |
|---|---|
| Core compression library | NEW `src/gleipnir/distill/` (sibling to broker/bus/engine/ledger/preflight/sandbox/verify) — `code.py` (stdlib `ast`), `arrays.py` (statistical JSON, stdlib), `predicate.py` (D3 `is_compressible`), `__init__.py` |
| Provenance | Module header docstring carrying the `## Provenance` attribution text verbatim |
| Broker exposure (IF D1=A) | NEW `src/gleipnir/broker/distill/` mirroring `broker/{git,pm}/` (own `pyproject.toml`+`VERSION`, `mcp>=1.0,<2` if MCP-shaped) — thin wrapper over the library |
| Grant wiring (IF broker) | `opencode.jsonc` `mcp` enable; per-role `tools: {gleipnir-distill_*: false}` deny-list in `.gleipnir/agents/*.md` for non-holders (Tier-3, enforcement-bearing — hardened review path) |
| Boundary hook (IF D1=B, gated on probe) | NEW `.gleipnir/plugins/distill-hook.ts` (Tier-3 enforcement code) — ONLY if the live probe confirms output-content rewrite is possible |
| Decision record | NEW `.gleipnir/decisions/distill.md` recording the converged D1–D4 (operator-authored Tier-3) |
| Tests | `is_compressible` predicate (allow/exclude rows), `ast` code-compressor golden fixtures, array-selection statistical cases, stdlib-only assertion (mirror `test_broker_stdlib_only.py`) |
