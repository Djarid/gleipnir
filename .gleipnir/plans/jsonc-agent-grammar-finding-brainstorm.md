# Design Brief: Surface a malformed opencode.jsonc `agent:` block in the config preflight

> **Status: DECISION ANALYSIS ONLY — awaiting operator convergence.**
> This brief is produced by `gleipnir-brainstorm` (a subagent). Its `question`
> tool does not reach the operator, so the `## Decision Analysis` below is
> **advisory input** to the convergence gate, not a decision. The RECOMMENDED
> approach and the two material sub-decisions (marked **[OPERATOR DECIDES]**)
> must be surfaced by the orchestrator to the operator. `gleipnir-plan` plans
> only from the operator's converged choice.

## Problem Statement

`src/gleipnir/preflight/config_scan.py` is a fail-closed config-scoping
preflight: it scans opencode agent config and emits a `CLOSED` / `REFUSE` /
`PROCEED_UNCLOSED` verdict via `decide_config`. As of commit `981623b`, a
structurally-malformed `opencode.jsonc` `agent:` block — either the top-level
`agent:` value being a non-dict, or an individual per-agent block being a
non-dict — is **coerced to `{}` crash-safely but emits no operator-facing
finding** (`config_scan_main`, lines 1264–1284; explicit comments at 1270–1273
and 1280–1283 acknowledge "not yet surfaced to the operator").

Consequence: the scan can print `CLOSED` (exit 0) while the operator's
`opencode.jsonc` `agent:` block is malformed and their intended per-agent tool
scoping has been silently dropped. This is precisely the fail-*silent* posture
a fail-closed tool must not have. The question: **should the preflight emit an
operator-facing finding for a malformed jsonc `agent:` block, and if so, how
and at what severity?**

## Grounding facts established during Explore (verified against disk)

1. **Two orthogonal outcome mechanisms exist**, not one:
   - `Unparseable` (`UnparseableKind`: `NO_FRONTMATTER`, `UNTERMINATED_FENCE`,
     `OUT_OF_SUBSET_YAML`, `INVALID_JSONC`, `READ_ERROR`) — *well-formedness /
     "could not parse at all"* failures. `parse_jsonc` already emits
     `INVALID_JSONC` for JSON that will not parse (line 522/527/531).
   - `Finding` (`FindingCheck` enum + `FindingSeverity` FAIL/WARN) — *semantic /
     structurally-parseable-but-wrong* checks.
   - The malformed `agent:` block sits in the **gap between the two**: it parses
     as valid JSON (so it is *not* `Unparseable`), but it is structurally wrong
     for its role (so it belongs in the `Finding` family). This gap is the root
     of the silent-ignore.

2. **`check_grammar` already handles the exact analogous case for
   frontmatter.** Lines 651–663: a present-but-non-dict `tools:` in an agent's
   `.md` frontmatter is a `GRAMMAR`/`FAIL` finding; lines 609–621 do the same
   for a non-dict `permission:`. So the framework has *already decided* that "a
   block that should be a map but is a scalar/list is a `GRAMMAR`/`FAIL`
   problem" — for frontmatter. The jsonc `agent:` block is the same class of
   defect in the other config source. **There is an existing symmetry the
   status quo breaks.**

3. **`check_grammar(parsed: dict)` is frontmatter-shaped, not jsonc-shaped.**
   It walks `permission.*` and `tools.*` keys of a *single agent's* parsed
   frontmatter (called per-.md-file in the loop at line 1248). It never sees
   `opencode.jsonc` and has no notion of a top-level `agent:` map-of-agents.
   Reusing it verbatim on the jsonc `agent:` block is not a drop-in — the shape
   it validates is different (agent-frontmatter vs a map of agent-name → block).

4. **Blast radius of the silent drop is bounded but real.** Per the quality
   review and confirmed at `enumerate_effective_tools` (lines 726–732): a jsonc
   per-agent override can only *ADD* denies (the two sources are UNIONED, line
   729). Dropping a malformed block therefore *removes* intended denies →
   *increases* the non-denier set. For the two single-holder namespaces
   (`gleipnir-git_*`, `gleipnir-pm_*`) this **may** be caught incidentally by
   `assert_single_holders` (SINGLE_HOLDER/FAIL_OPEN) or `check_fail_open`.
   **But** that incidental coverage is partial: it only fires if the dropped
   deny was one of the two holder namespaces; a malformed block that dropped a
   *different* intended deny (or that the operator simply wanted to *inspect as
   correct*) produces no signal at all. Silent-ignore is a genuine coverage
   hole, not a fully-covered redundancy.

5. **Severity mechanics** (`decide_config`, lines 1096–1103): a `FAIL` finding
   forces not-`CLOSED` (→ `REFUSE`, or `PROCEED_UNCLOSED` under `override_ack`).
   A `WARN` is reported but only forces not-`CLOSED` under `--strict`. So the
   FAIL-vs-WARN choice directly controls whether a malformed `agent:` block
   blocks the pipeline by default.

## Constraints

- **Fail-closed philosophy**: the tool's whole reason for existing is to not let
  a malformed/unsafe config report `CLOSED`. Silent-ignore is in tension with
  this.
- **Enum-shape stability**: the `FindingCheck` enum was declared in full up
  front (lines 549–555, comment at 543–546) specifically "to avoid a later
  signature break to an already-shipped enum." Adding a member is a deliberate,
  low-cost act *by design*, but it is still a change to a shipped public enum
  that tests reference by name.
- **Reader-honesty**: the existing code comments explicitly flag the gap
  (`"not yet surfaced to the operator"`), signalling the authors intended this
  to be revisited — not a settled decision.
- **Token/complexity budget** (framework goal G-4d): the fix must be
  proportionate. A whole new check function + enum member + test file is more
  surface than reusing an existing path.
- **Diagnostic quality**: `Finding.where` / `detail` are "never left blank"
  (lines 565–573). Any new finding must carry a precise key path
  (e.g. `agent` or `agent.<name>`) and a human-readable reason.

## Approaches Considered

### Approach A: Extend/generalise the GRAMMAR check to cover jsonc `agent:` shapes

**Summary:** Emit a `GRAMMAR`-check finding for a non-dict `agent:` block and
for each non-dict per-agent block, from within (or adjacent to) the jsonc
handling in `config_scan_main`. Reuse the existing `FindingCheck.GRAMMAR`
member; do not add a new enum value. Either add a small
`check_jsonc_agent_grammar(jsonc_agent_block)` helper that returns
`list[Finding]` with `check=GRAMMAR`, or inline two `Finding(GRAMMAR, ...)`
emissions at the coercion sites (lines 1266 and 1276).

**Tradeoffs:**
- Pro: **Preserves the existing symmetry** — "a block that must be a map but is
  a scalar/list is a GRAMMAR problem" already holds for frontmatter `tools:` /
  `permission:`; this extends the *same* semantic to the jsonc source, so the
  operator sees one consistent finding category for the same defect class.
- Pro: **No shipped-enum change** — `FindingCheck` stays as declared; no member
  churn, no test-name breakage for enum membership.
- Pro: **Small, proportionate token/complexity cost** — a handful of lines at
  the two coercion sites, or one short helper.
- Con: `GRAMMAR`'s current `detail` strings and the `check_grammar` docstring
  are frontmatter-specific ("under permission/tools"); reusing the member for
  a jsonc-source problem slightly overloads its meaning unless the `where`/
  `detail` are written to make the source unambiguous (`where="agent"` /
  `where="agent.<name>"`).
- Con: A future reader filtering findings by `check == GRAMMAR` will now get
  both frontmatter-grammar and jsonc-agent-grammar hits; if any downstream
  logic ever wants to treat them differently, the merge would have to be undone.

**Estimated Scope:** `config_scan.py` (`config_scan_main` around 1264–1284,
optionally one new helper near `check_grammar`); `tests/test_config_scan_grammar.py`
and/or `tests/test_config_scan_cli.py`. Complexity: **low**.

**Risk:** **low** — reuses a proven finding path; the only real risk is
semantic overloading of `GRAMMAR`, mitigated by precise `where`/`detail`.

### Approach B: Add a new dedicated `FindingCheck` member for jsonc structural problems

**Summary:** Add e.g. `JSONC_GRAMMAR = "jsonc_grammar"` (or
`MALFORMED_AGENT_BLOCK`) to `FindingCheck`, and emit it for the non-dict
`agent:` / per-agent-block cases via a dedicated
`check_jsonc_agent_grammar(...)` function.

**Tradeoffs:**
- Pro: **Cleanest separation of concerns** — jsonc structural defects are
  reported under their own category, distinguishable from frontmatter grammar
  at a glance and by any downstream filter.
- Pro: **Future-proof** — if more jsonc-shape checks arrive (top-level `tools:`
  shape, `mcp:` block shape, etc.), they have a natural home under this member.
- Pro: Enum was *designed* to be extended up front, so adding a member is a
  sanctioned, low-friction act.
- Con: **Highest surface/token cost** of the emitting options — new enum member,
  new function, new tests, and a docstring establishing the new category. For a
  single defect class this may be over-engineering (Scope-Creep watch).
- Con: **Shipped-enum change** — the full-enum-up-front comment's intent was to
  *avoid* enum churn; adding a member is allowed but still touches a public
  surface that tests reference by name.
- Con: Splitting "block should be a map but is a scalar" into two categories
  (frontmatter vs jsonc) fragments a single conceptual defect across two enum
  values, which an operator may find *more* confusing, not less.

**Estimated Scope:** `config_scan.py` (enum + new function + wiring in
`config_scan_main`); new/expanded test coverage, likely a new test module or a
new section in `test_config_scan_grammar.py`. Complexity: **medium**.

**Risk:** **low–medium** — mechanically safe, but the added surface must be
justified by an actual near-term need for multiple jsonc-shape checks; if that
need does not materialise, it is standing complexity.

### Approach C: Emit via the closest existing check without a new enum member (non-GRAMMAR)

**Summary:** Report the malformed block by reusing whichever *other* existing
member is "closest" — e.g. an `OVER_RESTRICTION`/`WARN` (the malformation
effectively drops intended restrictions) — without adding an enum member and
without touching the GRAMMAR path.

**Tradeoffs:**
- Pro: No enum change and no new function.
- Pro: Arguably ties the finding to the *effect* (denies were dropped) rather
  than the *cause* (bad shape).
- Con: **Semantically wrong** — `OVER_RESTRICTION` means "nobody holds a
  namespace"; a malformed block is a *shape* defect, not an over-restriction.
  Overloading an unrelated member is worse than overloading GRAMMAR (which at
  least already means "bad shape").
- Con: Misleading `where`/`detail` for whichever member is borrowed; degrades
  diagnostic quality, which the codebase explicitly protects.
- Con: Loses the frontmatter/jsonc symmetry that makes Approach A coherent.

**Estimated Scope:** `config_scan.py` small; tests small. Complexity: **low**.

**Risk:** **medium** — cheap to write but semantically misleading; likely to be
reverted or reclassified later, making it net-negative.

### Approach D: Accept silent-ignore (status quo) — document why incidental coverage suffices

**Summary:** Emit no finding. Rely on `assert_single_holders` /
`check_fail_open` catching the *effect* (dropped denies → extra non-deniers) for
the two single-holder namespaces, and document this as intentional.

**Tradeoffs:**
- Pro: **Zero code change / zero token cost.**
- Pro: For the *specific* case where the dropped deny was a single-holder
  namespace, the effect *is* caught downstream, so the config would still not
  report `CLOSED` in that case.
- Con: **Coverage is partial and accidental**, not by design: a malformed block
  that drops a *non-holder* intended deny, or that the operator wanted verified
  as correct, produces **no signal** and the scan can report `CLOSED`.
- Con: **Violates the fail-closed contract's spirit** — a fail-closed tool
  should name the malformation, not depend on a side-effect check happening to
  fire.
- Con: The existing in-code comments already flag this as unfinished
  ("not yet surfaced to the operator"), so "document why it is fine" would be
  arguing against the authors' own stated intent.

**Estimated Scope:** documentation/comment only. Complexity: **trivial**.

**Risk:** **medium (latent)** — no immediate breakage, but a real silent-failure
hole that undercuts the tool's purpose; the risk is a future malformed config
sailing through as `CLOSED`.

---

## Decision Analysis

**Decision type:** Multi-option comparison (A/B/C/D) with a material
architectural sub-question (enum shape) and a material severity sub-question.
Per the auto-selection table: **Weighted Decision Matrix** (primary, for the
4-way comparison), with a **Reversibility Filter** pre-screen and a
**Second-Order Thinking** cross-check on the enum-shape choice.

### Reversibility pre-screen

- Reversibility: **Two-Way Door** for the *emit-vs-not* choice and for A/C
  (reuse existing member — trivially revertible).
- The **enum-shape** choice (A/C reuse vs B new member) is **weakly one-way**:
  once `JSONC_GRAMMAR` ships in the public enum and tests/consumers reference
  it, *removing* it is a public-surface change. Adding it later (start with A,
  add B's member if a second jsonc-shape check appears) is the cheaper
  direction. This asymmetry favours starting minimal.
- Severity (FAIL vs WARN) is **Two-Way Door** — flipping a `FindingSeverity` is
  a one-line change; but it changes default pipeline behaviour, so it is
  material enough to surface.

### Weighted Decision Matrix

Criteria weighted for the framework goal (quality-efficient outcomes per token):
fail-closed correctness is paramount; token/complexity cost and enum-surface
stability matter; semantic clarity guards future maintenance.

| Criterion | Weight | A: extend GRAMMAR | B: new enum member | C: reuse other member | D: status quo |
|---|---|---|---|---|---|
| Closes the fail-closed hole | 10 | 9 → **90** | 9 → **90** | 7 → **70** | 1 → **10** |
| Semantic correctness / clarity | 8 | 7 → **56** | 9 → **72** | 2 → **16** | 3 → **24** |
| Preserves frontmatter/jsonc symmetry | 6 | 9 → **54** | 5 → **30** | 2 → **12** | 4 → **24** |
| Low token / complexity cost | 7 | 8 → **56** | 4 → **28** | 8 → **56** | 10 → **70** |
| Enum-surface stability (no shipped churn) | 5 | 9 → **45** | 4 → **20** | 9 → **45** | 10 → **50** |
| Diagnostic quality (where/detail honest) | 6 | 8 → **48** | 9 → **54** | 3 → **18** | 2 → **12** |
| **Total** | | **349** | **294** | **217** | **190** |

**Ranked:** A (349) > B (294) > C (217) > D (190).

### Second-Order Thinking cross-check (enum-shape: A vs B)

- **A near-term:** one consistent "bad shape" category; minimal surface. **A
  far-term:** if several more jsonc-shape checks arrive, `GRAMMAR` becomes a
  mixed bag; *then* promote to B by adding a member and reclassifying — a
  cheap, additive migration because A used honest `where="agent[.<name>]"`
  values that make the reclassification mechanical.
- **B near-term:** clean category but standing surface for a single defect.
  **B far-term:** pays off *only if* multiple jsonc-shape checks materialise;
  otherwise it is permanent over-structure fragmenting one conceptual defect
  across two enum values.
- **Key insight:** A is the reversible-into-B path; B is not cheaply
  reversible-into-A. Start at A unless the operator already knows more
  jsonc-shape checks are imminent (in which case B amortises).

### Bias warnings

- ⚠️ **Status Quo Bias (on D):** D's only real strength is "no change." Applying
  equal scrutiny, D leaves a genuine fail-closed hole the authors already
  flagged as unfinished — "no change" is a cost here (a silent `CLOSED` on a
  malformed config), not a saving. D should not get a free pass for being the
  current state.
- ⚠️ **Scope-Creep Bias (on B):** Reaching for a whole new enum member +
  function + test module for a *single* defect class risks broadening surface
  to feel thorough rather than making the minimal correct choice. B is
  justified only if multiple jsonc-shape checks are genuinely imminent.
- ⚠️ **IKEA Effect (mild, on A):** A reuses the team's own `check_grammar`
  path, which could bias toward it. Countercheck: A wins the matrix on
  *symmetry + cost + reversibility*, not merely because it is the in-house
  path — and its one weakness (semantic overload of GRAMMAR) is explicitly
  scored (7/8 on clarity) and mitigable via precise `where`/`detail`. The
  preference survives independent scrutiny.
- (Others checked — Anchoring, Confirmation, Sunk Cost, Availability — none
  materially triggered; the four options were scored on forward value, not on
  order of presentation or prior investment.)

### Recommendation (ADVISORY — the operator decides at convergence)

**RECOMMENDED: Approach A — extend the GRAMMAR check to cover the jsonc
`agent:` block**, emitting a `FindingCheck.GRAMMAR` finding with
`where="agent"` (non-dict top-level block) or `where="agent.<name>"` (non-dict
per-agent block) and a `detail` naming the jsonc source explicitly. This closes
the fail-closed hole, preserves the existing frontmatter/jsonc symmetry, costs
the least surface/tokens, keeps the shipped enum stable, and — critically — is
the reversible path *into* Approach B should more jsonc-shape checks later
justify a dedicated category. Reject C (semantically misleading) and D (leaves
a real silent-failure hole the authors already flagged).

## Material sub-decisions that MUST go to the operator

1. **[OPERATOR DECIDES] Which approach** — A (recommended), B, C, or D. The
   matrix favours A, but B is defensible *if the operator already intends
   several more jsonc-shape checks soon* (that intent is information only the
   operator holds and would flip the second-order calculus toward B).

2. **[OPERATOR DECIDES] Severity: FAIL vs WARN** for the malformed-jsonc-`agent`
   finding. This is material because it directly controls default pipeline
   behaviour (`decide_config` lines 1096–1103):
   - **FAIL** → a malformed `agent:` block forces not-`CLOSED` → `REFUSE` by
     default (or `PROCEED_UNCLOSED` under `override_ack`). This matches the
     precedent that frontmatter non-dict `tools:`/`permission:` is
     `GRAMMAR`/**FAIL** (lines 613, 656, 670) — the *symmetry argument says
     FAIL*.
     Argued default given the fail-closed philosophy and the frontmatter
     precedent.
   - **WARN** → reported, but only blocks under `--strict`. Softer; risks the
     scan still printing `CLOSED` on a malformed config in non-strict runs,
     which partially re-opens the very hole being closed.
   *Advisory lean:* **FAIL**, to preserve symmetry with the frontmatter grammar
   precedent and honour fail-closed — but this is the operator's call because it
   changes default blocking behaviour.

3. **[OPERATOR DECIDES — only if Approach B is chosen] Enum member name** —
   e.g. `JSONC_GRAMMAR` vs `MALFORMED_AGENT_BLOCK` vs another. Naming a shipped
   public-enum member is a durable, hard-to-rename choice. (Not applicable
   under A/C/D.)

## Open Questions (for `gleipnir-plan`, after convergence)

- Should the emission live in a small dedicated helper
  (`check_jsonc_agent_grammar(jsonc_agent_block) -> list[Finding]`, called from
  `config_scan_main` before the coercion) or be inlined at the two coercion
  sites (lines 1266, 1276)? A helper is more testable in isolation; inlining is
  fewer lines. (Non-material — a plan/implementation detail, defer to plan.)
- Exact `where`/`detail` wording (must be non-blank and name the jsonc source
  and the expected map shape, mirroring the frontmatter `detail` style).
- Test placement: extend `tests/test_config_scan_grammar.py` (co-locate with the
  symmetric frontmatter grammar tests — natural under Approach A) vs
  `tests/test_config_scan_cli.py` (end-to-end that a malformed jsonc `agent:`
  block drives a non-`CLOSED` verdict).
- Whether the per-agent-block malformation should also carry the agent name in
  `where` when the block is non-dict (recommended: yes — `agent.<name>`).

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Finding emission | `src/gleipnir/preflight/config_scan.py` — `config_scan_main` (~1264–1284); optional new helper near `check_grammar` (~583) |
| Enum (Approach B only) | `FindingCheck` (~549–555) |
| Unit tests | `tests/test_config_scan_grammar.py` (symmetric grammar coverage) |
| End-to-end tests | `tests/test_config_scan_cli.py` / `tests/test_config_scan_decide.py` (verdict flips to not-`CLOSED` on malformed `agent:`) |
