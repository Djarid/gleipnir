# Design Brief: git_diff deterministic diff truncation (pilot)

> **Status: CONVERGED.** This entire design is settled through direct operator
> dialogue with the orchestrator (not the `question` tool, but just as real a
> convergence). There are **no open D-N decisions** and no `## Decision
> Analysis` — nothing here remains for the operator to converge. `gleipnir-plan`
> can plan directly from `## Scope for the pilot plan` below.
>
> **Supersedes** the earlier, broader draft `context-crush-brainstorm.md` (the
> "Distill" thread). That draft's D1/D2/D3/D4 Decision Analysis is WRONG and
> superseded — see the note in that file's header. This is a MUCH NARROWER
> pilot: deterministic truncation of ONE broker tool's diff output, baked into
> the broker's own code.

## Problem Statement

`gleipnir-git`'s `git_diff` tool (`src/gleipnir/broker/git/mcp_server.py`)
returns the raw output of `git diff` whole — `json.dumps({"success": True,
"diff": result["stdout"]})`. For a large diff this dumps the entire diff into
the calling agent's context in one call, contaminating the context window and
degrading reasoning quality. This is a **quality** concern (bad reasoning from a
polluted context), not primarily a token-cost concern.

The fix: the broker's own `git_diff` implementation deterministically truncates
oversized diff-hunk bodies **before returning**, keeping the file list and stat
summary intact, so the agent receives a signal-preserving, size-bounded diff —
with the full diff always recoverable from git itself.

## Provenance

The IDEA of structure-preserving truncation — keep the skeleton/summary,
compress the verbose body, and mark explicitly what was cut — is inspired by
Headroom's `CodeAwareCompressor` / `SmartCrusher` concept
(https://github.com/headroomlabs-ai/headroom, Apache-2.0). This pilot is a
**clean-room, Gleipnir-native reimplementation of the documented behaviour**,
adapted for a **diff-shaped input** (a unified diff is not source code, so
Headroom's AST-preserve-signature technique does not directly apply). It is
**not a port or derivative of Headroom's source**, consumes no Headroom code,
binary, package, model, or network service, and does **not** use any of their
trademarked names (Headroom, SmartCrusher, CodeCompressor, CodeAwareCompressor,
Kompress). Apache-2.0 §6 grants no trademark rights and none are claimed.

The following text is authored to survive verbatim into the module docstring:

> ```
> Diff-shaped structure-preserving truncation. The general idea — keep the
> summary/skeleton, collapse the verbose body, mark what was cut — is inspired
> by Headroom's CodeAwareCompressor / SmartCrusher concept
> (https://github.com/headroomlabs-ai/headroom, Apache-2.0). This is an
> independent, Gleipnir-native reimplementation of that BEHAVIOUR for a
> unified-diff input (a diff is not source code, so AST techniques do not
> apply); it is NOT a port or derivative of Headroom's source. No Headroom
> code, binary, package, model, or network service is consumed. Headroom's
> trademarked names (Headroom, SmartCrusher, CodeCompressor,
> CodeAwareCompressor, Kompress) are NOT used; Apache-2.0 §6 grants no
> trademark rights and none are claimed.
> ```

## Already-converged

Decided directly by the operator through conversation with the orchestrator.
**DECIDED — not up for re-litigation.** Reasoning preserved.

1. **"LLMs don't decide" — the trigger is code, never model judgment (D1
   reframed from first principles).** The original D1 framing ("a client-side
   tool an agent calls when it decides to, vs a boundary-side hook") was
   **axiomatically wrong**, not merely a weaker option. Gleipnir's Axiom 1 /
   G-5 deterministic-orchestration principle puts sequencing and enforcement in
   **code**, never in an LLM's judgment call about whether to bother
   compressing. A "tool the agent may call" makes contamination-prevention
   contingent on the model remembering to invoke it — exactly the anti-pattern
   the framework exists to eliminate. **The "client-side opt-in tool" design is
   ruled out permanently, not just for this pilot.**

2. **Corrected D1 resolution: compression is triggered deterministically, by
   code, with zero LLM decision in the loop.** Two theoretically-available
   mechanisms were named:
   - **(a) a host-level hook** that rewrites tool output automatically on a
     coded threshold — needs pi.dev-specific investigation. NOTE: Gleipnir's
     target runtime is **pi.dev, not opencode** (opencode is being retired per
     the S1–S9 build-order's S9 step). An earlier investigation pass wrongly
     centred on opencode's hook limitations; the operator explicitly corrected
     that ("gleipnir is intended to run in pi.dev not opencode!"). This
     mechanism is for tools Gleipnir does **not** implement (host built-ins like
     generic `read`/`grep`/`bash`).
   - **(b) baking the deterministic compression directly into the code of tools
     Gleipnir itself already implements and controls** (the git/pm brokers) —
     no host-hook question at all, because there is no host boundary to cross:
     the tool's own code decides, unconditionally, on a coded rule.

   **The operator chose (b)** as the immediate, buildable path, explicitly
   **deferring (a)'s pi.dev-hook investigation** to if/when it is ever needed
   for host built-in tools Gleipnir does not implement.

3. **D2 resolved: no new tool/MCP surface of any kind — for two independent
   reasons.**
   - *Consequence of (b):* since compression lives inside an existing
     Gleipnir-owned tool's implementation, there is nothing new to expose.
   - *Independent operator objection:* "I don't like MCPs that are globally
     available — they contaminate the context." A globally-registered MCP
     tool's schema/description occupies **every** session's context whether or
     not it is ever called. (Headroom's OWN docs admit this exact failure mode:
     Claude Code's `/usage` attributes context share to the `headroom` MCP
     server even when it is barely used.) Building a new tool surface to fix
     contamination would itself be a contamination source.
   - **Therefore: no separate "distill" tool, no new MCP server/broker, no new
     agent-facing schema, ever, for this.** Compression is **plain internal
     library code** that an existing, Gleipnir-owned tool's implementation calls
     before returning its result. No new schema enters any agent's context.

4. **Pilot scope: `gleipnir-git`'s `git_diff` tool only.** It is the one
   existing broker tool whose output size is genuinely unbounded today (a huge
   diff currently dumps entirely into context). The other seven existing broker
   tools (`git_status`, `commit_changes`, `push_current_branch`, and the four
   `gleipnir-pm` tools) are typically small/bounded already and are **OUT of
   scope** for this pilot.

5. **The compression technique is diff-shaped, not code-shaped.** A unified diff
   is not source code, so the Headroom AST-preserve-signature idea does not
   directly apply. The deterministic rule:
   - **ALWAYS keep unchanged:** the file list and the stat summary (`+N -M` per
     file).
   - For any single file's **hunk body** exceeding a coded line/token
     threshold: keep the **first N and last N lines** of that hunk and
     **collapse the middle** with an **explicit truncation marker** (e.g.
     `# ... (N lines truncated)`).
   - **Never silently drop** content without a visible marker.

6. **Nothing is ever destroyed.** `git-ops` operates on the actual git
   repository, so the full diff is always independently recoverable via
   `git diff` itself. Truncation affects only what the broker returns in **one
   call**, never the underlying source of truth. No CCR-style
   reversible-store/retrieve mechanism is needed for THIS pilot (unlike the
   original Headroom-inspired design) — **the repo itself IS the retrieval
   path.**

7. **Default posture is moot as a separate axis.** Because this is
   deterministic broker-owned code (not an agent-facing opt-in), the original
   D4 "opt-in vs default-on" framing does not apply. It is simply:
   **always-on, unconditionally applied above a fixed coded threshold, no
   configuration, no judgment call anywhere.**

8. **Evidence/trust exclusion is now a per-field, structural concern (narrower
   than the old path-based D3 blanket rule).** Because compression is baked into
   the broker's OWN code by the broker's OWN author — not a generic external
   compressor blindly touching unfamiliar output — the author has full knowledge
   of the output shape. The rule, stated as a **structural** safety property:
   - Truncation touches **ONLY the diff hunk-body text.** It must **NEVER**
     touch the file list, the stat summary, any commit hash, the secret-scan
     verdict/outcome, or any other structured field the broker already returns.
   - **Make this structurally true, not merely asserted:** the truncation
     handler **receives ONLY the raw diff text** (for one file) and **returns
     truncated diff text**; it **never sees or touches** the broker's response
     envelope (`{"success": ..., "diff": ...}`), any verdict field, or any
     commit metadata. The broker dispatches to it on `result["stdout"]` (the
     diff text) alone and re-wraps the result in its own envelope. The envelope,
     the `success` flag, and every other field are assembled by the broker AFTER
     truncation and are structurally out of the handler's reach. (This safety
     property is unchanged by the plugin-library shape in `## Scope`: it is now
     the invariant the `Handler` boundary enforces for the ONE pilot handler and
     any future one.)

## Forward-looking note (out of scope)

**`codegraph` is a tracked future build-order item, not a vague hypothetical.**
AETOS — from which Gleipnir is inherited-and-audited — ships `aetos-codegraph`
as one of its five core MCP servers: an **AST-based, function-level dependency
graph** exposing **6 tools** (`codegraph_context`, `codegraph_impact`,
`codegraph_query`, `codegraph_status`, `codegraph_build`,
`codegraph_quality_scan`), consumed by AETOS's `quality-reviewer` for
blast-radius analysis and for `[D]`-tagged (tool-produced) findings in the
cognition layer. **Gleipnir already acknowledges this as an open gap in its own
durable records:** `.gleipnir/decisions/cognition-layer.md` (~line 61) names
that "AETOS's `codegraph_quality_scan` provider-registry MCP Gleipnir does not
have... the provider registry is not [ported]," and `.gleipnir/agents/
quality-reviewer.md` (~line 99) documents that "Gleipnir has no `codegraph`-style
static-analysis MCP." This is **not a rejection** — Gleipnir is
inherited-and-audited from AETOS, not a mechanical port, and `codegraph` simply
has not been reached yet in the build sequencing (guards → roster → engine →
pi.dev replatform → ...).

**Why the Refinement-1 plugin architecture matters NOW because of this.** A
future Gleipnir-native `codegraph` rebuild would very likely **share the plugin
architecture's AST-parsing / handler machinery** built here. An AST-based code
*content-compression* handler (a future handler on this pilot's registry) and an
AST-based *dependency-graph builder* (codegraph's core) are both "parse code,
walk the tree, do something structural" — the **same underlying capability,
different handlers/consumers.** That shared substrate is the concrete,
non-abstract reason the pilot's extensibility requirement (a second handler must
register without editing the first handler or the dispatcher) has to hold now,
not merely in principle.

**Explicitly:** `codegraph` is **NOT built now** and is **NOT plan-stage scope**
for this pilot (the pilot builds only the plugin library + the one diff-hunk
handler). But it **should be surfaced in `.gleipnir/plans/SESSION-STATE.md`'s
"Open threads / next" as a real future build-order thread** when this pilot's
work is recorded — so it does not silently disappear again (distinct from the
prior draft's vaguer "a future code-graph capability could reuse this" framing).
That SESSION-STATE.md entry is a note for whoever does that bookkeeping later
(**session-scribe's job, not this brief's** — `gleipnir-brainstorm` does not
write SESSION-STATE.md itself); it is recorded here only as the durable pointer
the scribe should act on.

## Scope for the pilot plan

A direct, buildable summary `gleipnir-plan` can work from.

The reusable unit is **not a single hard-coded `diff_truncate(text) -> text`
function.** It is a small **shared library with a content-handler registration
pattern** — a `Handler` protocol/interface plus a lightweight
registry/dispatcher that tools call into. **For THIS pilot, exactly ONE handler
is built and registered: a diff-hunk truncation handler** implementing the
already-converged deterministic rule (item 5). The registration/dispatch
machinery must be **generic enough that a FUTURE handler (e.g. an AST-based code
handler) can register without changing the dispatcher's own code, and without
editing the existing diff handler** — this is a **real, testable extensibility
requirement** for the plan stage, not a nice-to-have (see the extensibility
test below). The library stays **dependency-free (stdlib only)** and
structurally separated from broker response envelopes per item 8 (a handler
receives ONLY the raw content it is asked to process — never verdict,
commit-metadata, or response-envelope fields).

### Handler / registry shape (what the plan must build)

- **`Handler` protocol/interface** with two methods:
  - `can_handle(content, hint) -> bool` — does this handler apply to this
    content? (`hint` is a small, caller-supplied tag such as `"diff"`; the
    dispatcher passes it through but the contract does not depend on any
    particular hint vocabulary.)
  - `process(content) -> ProcessedResult` — transform the raw content; return a
    result carrying the (possibly transformed) content. `content` in and the
    content out are the ONLY things a handler touches (item-8 structural
    separation: no envelope, no verdict, no metadata ever crosses this
    boundary).
- **A lightweight registry/dispatcher** tools call into (e.g. `register(handler)`
  and a `dispatch(content, hint) -> ProcessedResult` that selects the first —
  or best — registered handler whose `can_handle` returns true, with a defined
  no-handler fallback of returning content unchanged). The dispatcher contains
  **no handler-specific logic**; adding a handler is a pure registration, never
  a dispatcher edit.
- **Exactly one handler registered in this pilot:** `DiffHunkTruncationHandler`
  (Gleipnir-native name), implementing the item-5 rule (keep file list + stat
  summary always; truncate hunk bodies past a coded threshold with first/last-N
  + explicit marker; never touch structured fields). It carries the
  `## Provenance` docstring verbatim.

### Touched files

| Area | File | Change |
|---|---|---|
| Shared handler library | **NEW** small module/package, e.g. `src/gleipnir/broker/content_handlers/` (Gleipnir-native name; a shared library, not inlined — see reuse seam) | Pure, stdlib-only. Defines the `Handler` protocol (`can_handle`/`process`), the `ProcessedResult` type, and the registry/dispatcher (`register` / `dispatch`). Contains no handler-specific logic. |
| Diff handler (the ONE pilot handler) | **NEW** in the same library, e.g. `.../diff_hunk_handler.py` | The single registered handler for this pilot: implements the item-5 diff-shaped deterministic rule; takes raw diff text and returns structure-preserving truncated diff text via `process`. Carries the `## Provenance` docstring verbatim. |
| Broker call site | `src/gleipnir/broker/git/mcp_server.py` (`git_diff`, lines ~300–329) | Register the diff handler and dispatch on `result["stdout"]` BEFORE wrapping in the response envelope. The envelope assembly (`{"success": True, "diff": ...}`) is unchanged except that `"diff"` now carries the (possibly truncated) text from the dispatched handler's `ProcessedResult`. No other tool touched. |
| Tests | `tests/` (mirror `test_broker_*` conventions) | Unit tests for the diff handler (golden fixtures: below-threshold pass-through, above-threshold truncation with first/last-N kept + marker, multi-file diff keeps every file's stat line); a stdlib-only assertion; a structural-separation test proving a handler never receives the envelope; and the **extensibility test** (below) proving a second handler registers with no edit to the dispatcher or the diff handler. |

### Deterministic truncation rule (precise enough to implement)

1. Parse the unified diff into per-file sections and, within each file, its
   hunks (standard `diff --git` / `@@` boundaries).
2. **Always preserve, verbatim:** every file header line, every `diff --git`
   line, and the per-file stat summary (`+N -M`). These are never candidates
   for truncation.
3. For each file's hunk body, if its line count exceeds the coded threshold `T`
   (a fixed constant in the module; the exact value is a plan-stage tuning
   parameter, not an operator decision), keep the **first N** and **last N**
   body lines (N is a coded constant, `2N < T`) and replace the middle with a
   single explicit marker line: `# ... (K lines truncated)` where `K` is the
   exact count removed.
4. If the hunk body is at or below `T`, emit it verbatim.
5. Never remove any line without emitting the marker; the marker's `K` must be
   accurate.

### Structural-separation safety property (item 8 — testable)

- A handler's `process(content)` accepts **only the raw content it is asked to
  process** (for the diff handler: a `str`, the raw `git diff` stdout or
  per-file diff text) and returns **only** a `ProcessedResult` carrying
  transformed content of the same kind.
- A handler (and the `Handler`/`ProcessedResult` contract) has **no parameter**
  for, and **no reference to**, the broker's response envelope, the `success`
  flag, any commit hash, or the secret-scan verdict. The dispatcher passes only
  `content` (and the opaque `hint`) across the boundary — never an envelope.
- The broker calls `dispatch(result["stdout"], "diff")` alone and assembles
  `{"success": True, "diff": <truncated>}` itself, **after** dispatch.
- **Test:** assert the handler boundary carries content-only (no envelope/
  verdict/metadata parameter or reference) and that a diff containing text
  resembling a verdict/hash inside a hunk body is still only ever treated as
  hunk-body text (the handler has no concept of those fields), proving the
  envelope/verdict/metadata are structurally unreachable.

### Extensibility requirement + reuse seam (item 10)

- The handler library is a **shared, importable, dependency-free (stdlib-only)**
  plugin surface: a `Handler` protocol, a `ProcessedResult` type, and a
  registry/dispatcher. Do **not** inline any of it into `mcp_server.py`.
- **Testable extensibility property (real requirement, not aspirational):**
  registering a **second** handler must require **no edit to the dispatcher's
  own code and no edit to the existing diff handler.** The plan MUST include a
  test that registers a trivial second stub handler (e.g. one whose
  `can_handle` matches a different `hint`) and asserts (a) it is selected/
  dispatched to for its content, (b) the diff handler still works unchanged, and
  (c) neither the dispatcher module nor the diff-handler module was modified to
  make this pass. This is the concrete proof that a future AST-based code
  handler — and, further out, a Gleipnir-native `codegraph` rebuild sharing this
  AST/handler machinery (see `## Forward-looking note`) — can register cleanly.
- **Still out of scope for this pilot:** only the ONE diff handler is built and
  registered; do **not** build the AST/code handler or the `codegraph`
  capability now. The library just makes them addable later without a redesign.

## Open Questions

None requiring operator convergence. The entire thread is settled. The only
remaining choices are **plan-stage tuning parameters**, not operator decisions:
the exact threshold `T`, the first/last-keep count `N`, and the final
Gleipnir-native module/package and handler filenames. `gleipnir-plan` may fix
these directly.
