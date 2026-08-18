# Design Brief: Enforcement-path set `E` — same-class gap closure (`.gitattributes`, `.gitmodules`, lock-files)

> **Status: CONVERGED — operator chose Approach B (routed via the orchestrator's
> `question` tool, per the precept-10 gate).** This brief's `## Decision Analysis`
> carried a genuine material tradeoff; it was surfaced to the operator by the
> orchestrator, and the operator's converged choice is recorded in
> **`## Selected Approach (Converge — OPERATOR-CONVERGED)`** below. **Scope of this
> round: enumerate `.gitattributes` + `.gitmodules` into set `E` only; lock-files
> explicitly DEFERRED to a future dedicated convergence (carried forward as an
> open item, not dropped).** Ready to hand to `gleipnir-plan` for the plan stage
> (HARDENED path — this amends `stage-role-map.md ∈ E`). The recommendation in the
> Decision Analysis was advisory; the Selected Approach is the operator's decision.

## Problem Statement

The prose/config-only track's enforcement-path set `E` (`stage-role-map.md`,
Axis 2(a)) enumerates specific repo-root cross-cutting files that are **always
hardened** by exact-path match — currently `.gitignore`, `.envrc`,
`pyproject.toml` (plus the `.gleipnir/**` enforcement paths and
`opencode.jsonc`/`**/opencode.json`). The map explicitly states: *"New repo-root
cross-cutting files join `E` by explicit amendment, not by a predicate."*

Three files/classes sit in the **same blast-radius class** as `.gitignore` —
they govern git behaviour and/or the version-control/audit-trail surface — but
are **not yet enumerated** into `E`:

1. **`.gitattributes`** — governs per-path git behaviour: line-ending
   normalisation, `filter`/`clean`/`smudge` driver bindings, `diff`/`merge`
   driver selection, `export-ignore`, and `-text`/binary treatment. A malicious
   or careless attribute can silently alter how tracked content is stored,
   diffed, or filtered (e.g. a `filter` that rewrites content on
   checkout/checkin). Directly analogous to `.gitignore`'s "governs what reaches
   / how it is treated in version control" rationale. (A prior finding —
   `plans/bin-executable-bit-fix.md` — already established `.gitattributes` has
   real, non-cosmetic git-behaviour reach.)
2. **`.gitmodules`** — declares submodule URLs and paths. A changed submodule URL
   can point a submodule at attacker-controlled content that is then pulled into
   the tree; a submodule path can shadow a tracked directory. Version-control /
   supply-chain relevant, same class.
3. **Lock-files** (`package-lock.json`, `poetry.lock`, `Cargo.lock`,
   `yarn.lock`, `Pipfile.lock`, `pnpm-lock.yaml`, …) — pin exact dependency
   versions/hashes. A silent lock-file edit can swap a pinned dependency for a
   malicious one; this is a well-known supply-chain vector. Same *intent* class
   as `pyproject.toml`'s "dependency ranges bound to the enforcement-core
   constraint" rationale.

**Ground truth (verified this session):** none of `.gitattributes`,
`.gitmodules`, or any `*.lock` file currently exists in this repo — only
`.gitignore` exists. This is therefore a **pre-emptive / future-proofing**
enumeration, not a response to an existing file. That lowers the near-term
consequence but does not remove the value: `E` is the classifier's coverage
map, and the whole point of explicit enumeration (vs a predicate) is that a
file must be *named* before it is covered — so a file added later is
**unprotected until `E` names it**.

## Constraints

- **Tier-3, operator-apply-only.** This change edits `.gleipnir/stage-role-map.md`,
  which is itself in `E` (Axis 2(a)). No roster agent — including any planner —
  may write it; the operator applies the diff. **This change is therefore itself
  enforcement-bearing and MUST run the HARDENED path** (two separate review
  rubrics + negative-check attestation, `attested_by ≠ author`, all five
  SUCCESS-gate clauses). Confirmed below.
- **Determinism is non-negotiable.** The classifier exists to route with **no
  per-plan LLM judgment**. Any addition must be decidable by **exact-path match
  or exact-filename match** — never a fuzzy "is this enforcement-adjacent?"
  predicate. The map explicitly rejects predicates for this reason.
- **Precedent invariant — repo-root-only.** Every current `E` repo-root literal
  (`.gitignore`, `.envrc`, `pyproject.toml`) is a **single repo-root file matched
  by exact path**. `opencode.json` is the one exception, matched by the glob
  `**/opencode.json` (deliberately nestable). Lock-files break the repo-root-only
  invariant: they can legitimately appear **nested** in subprojects
  (`frontend/package-lock.json`, `crates/foo/Cargo.lock`). This is the crux of
  the material tradeoff.
- **Integrity > efficiency.** The section's established stance (standalone-YAML
  disqualification, `.gitignore` always-hardened): when in doubt, over-include
  (a few benign edits get extra review) rather than under-review a possible
  bypass.
- **Style parity.** Each enumerated file in `E` carries its own one-line
  rationale (the existing per-file style). Any addition must match that style.

## Approaches Considered

The decision naturally decomposes into two separable parts, because the two
file-classes differ on the one axis that matters (repo-root-only vs nestable):

- **Part 1 — `.gitattributes` + `.gitmodules`:** repo-root, single-file, exact
  clean parity with `.gitignore`. Low controversy.
- **Part 2 — lock-files:** nestable, multi-ecosystem, an open-ended and
  ecosystem-versioned name list. This is where the genuine tradeoff lives.

The approaches below are framed as whole-decision strategies spanning both parts.

### Approach A: Enumerate all — `.gitattributes` + `.gitmodules` (repo-root exact) AND lock-files (by exact basename, any depth)

**Summary:** Add `.gitattributes` and `.gitmodules` to `E` as repo-root
exact-path literals (parity with `.gitignore`), and add a **closed, explicit
list of lock-file basenames** matched at **any depth** (e.g. `**/package-lock.json`,
`**/poetry.lock`, `**/Cargo.lock`, `**/yarn.lock`, `**/Pipfile.lock`,
`**/pnpm-lock.yaml`), each with its own rationale line.

**Tradeoffs:**
- Pro: Closes the full same-class gap in one amendment — no residual "lock-files
  are still uncovered" note to defer again.
- Pro: `**/basename` globs stay **mechanical** (exact-basename match at any
  depth) — this is the *same glob shape already in `E`* for `**/opencode.json`,
  so it is precedented, not novel.
- Pro: Catches the real supply-chain vector (nested subproject lock-files) that a
  repo-root-only rule would miss.
- Con: The lock-file **basename list is open-ended and ecosystem-versioned** —
  new package managers (or renamed lock-files, e.g. `bun.lockb`, `deno.lock`,
  `composer.lock`, `Gemfile.lock`, `go.sum`) appear over time. The list is a
  maintenance surface that will drift and silently under-cover new ecosystems.
- Con: Departs from the strict repo-root-only invariant the other three literals
  share — though `**/opencode.json` already established the `**/`-glob exception,
  so this is a *widening of an existing exception*, not a brand-new mechanism.

**Estimated Scope:** One edit to the `E` literal in
`.gleipnir/stage-role-map.md` (Axis 2(a)), plus per-file rationale lines. Low
complexity; medium wording care (the lock-file list needs an explicit
"closed list, extend by amendment" note to avoid re-introducing a predicate).

**Risk:** Medium — the open-ended basename list is a standing drift risk; a new
ecosystem's lock-file is uncovered until someone amends `E`. This is the *same*
coverage-boundary honesty problem the map already accepts for repo-root files;
here it is sharper because the lock-file namespace changes faster.

### Approach B: Enumerate the clean pair only — `.gitattributes` + `.gitmodules` now; DEFER lock-files

**Summary:** Add `.gitattributes` and `.gitmodules` to `E` as repo-root
exact-path literals (clean parity with `.gitignore`), each with its own
rationale. **Do not** enumerate lock-files in this pass — leave a sharpened
deferral note explaining *why* (nestability + open-ended list = a distinct
design question deserving its own convergence), rather than folding an
unresolved tradeoff into a "clean parity" amendment.

**Tradeoffs:**
- Pro: The two additions are **exact, uncontroversial parity** with the existing
  precedent — repo-root, single-file, exact-path, `integrity > efficiency`. No
  new mechanism, no invariant broken, no drift surface introduced.
- Pro: Keeps the amendment **fully mechanical and closed** — nothing in it can
  drift or under-cover later.
- Pro: Isolates the genuinely hard question (lock-files) so it gets a *dedicated*
  decision rather than riding on the coat-tails of an easy one — matching the
  round-3 precedent, which itself deferred exactly this.
- Con: Leaves the lock-file supply-chain gap open (a nested `Cargo.lock` edit
  routes to the *light* path until a later amendment). Given no lock-file exists
  in-repo today, the near-term exposure is nil, but the gap is real the moment
  one is added.
- Con: Requires a *second* future amendment for lock-files (two passes instead of
  one) — mild process overhead.

**Estimated Scope:** Same single-literal edit, but only two repo-root literals
added; plus a sharpened deferral note. Low complexity, low wording risk.

**Risk:** Low — everything added is exact and closed; the only residual is the
*deliberately deferred* lock-file gap, which is documented, not silent.

### Approach C: Enumerate the pair now AND route lock-files structurally via Axis 1 (`X`) or a content rule, not by name

**Summary:** Add `.gitattributes` + `.gitmodules` to `E` (as in B). For
lock-files, instead of an ever-drifting basename list in `E`, address them via a
**structural mechanism**: either (c1) add a generic `**/*.lock` + the known
non-`.lock` names (`package-lock.json`, `pnpm-lock.yaml`, `go.sum`) to Axis 1's
disqualifier set `X` so *any* lock-file forces the **full 8-stage pipeline** (the
strongest route), or (c2) add a content rule (Axis 2(b)) keyed on lock-file
structure.

**Tradeoffs:**
- Pro: `**/*.lock` is a *broad, low-drift* pattern — it catches `Cargo.lock`,
  `poetry.lock`, `Pipfile.lock`, `deno.lock`, `composer.lock`, `Gemfile.lock`,
  `flake.lock`, etc. without naming each. Fewer future amendments.
- Pro: Routing lock-files to the **full pipeline** (c1) is the most conservative
  possible treatment — arguably correct given the supply-chain stakes.
- Con: `**/*.lock` **over-matches** — many non-dependency files use `.lock`
  (editor lock-files, `.terraform.lock.hcl`, arbitrary app lock-files). And it
  **under-matches** the biggest one: `package-lock.json` and `pnpm-lock.yaml` are
  *not* `*.lock` at all. So a single glob is simultaneously too broad and
  incomplete — you still need an explicit name list, defeating the point.
- Con: Putting lock-files in `X` (c1) is arguably a **category error**: `X` is
  "executable/interpreted artifacts that *run*." A lock-file is inert declarative
  data — it does not run. Overloading `X` with "high-consequence inert data"
  blurs the one clean predicate `X` currently has (does-it-execute), which the
  cognition-layer Gate-1 routing *also* keys on. This has cross-cutting
  second-order cost.
- Con: A content rule (c2) for lock-files is not reliably grep-able across
  ecosystems (JSON vs TOML vs YAML vs custom) — reintroduces judgment.

**Estimated Scope:** The pair edit (low) + a *cross-cutting* change to `X` or
Axis 2(b) that ripples into the cognition-layer Gate-1 routing (medium-high).

**Risk:** High — semantic overload of `X` (the does-it-execute predicate),
over/under-match of `**/*.lock`, and coupling into the cognition layer. Highest
blast radius of the three for the least clean result.

## Decision Analysis

**Framework used:** **Reversibility Filter → Pros-Cons-Fixes**, with a
**Second-Order Thinking** overlay for the lock-file / `X`-overload question.
Rationale: the primary shape is a set of near-binary "add / defer" choices
(binary → Reversibility Filter → Pros-Cons-Fixes per the auto-selection table);
the lock-file sub-question has genuine long-term/architectural consequences
(coverage-boundary drift, `X`-predicate purity), which warrants the
Second-Order overlay.

### Reversibility Filter

```
Reversibility: TWO-WAY DOOR (for all three approaches)
Reversal cost: Very low. E is a prose literal in a Tier-3 doc. Adding a file to
  E only ever ROUTES MORE plans to the hardened (more-reviewed) path; it never
  weakens a guard. Removing an over-inclusion later is a one-line operator edit
  with no data loss, no external commitment, no re-architecture. The ONLY
  asymmetry: while a file is ABSENT from E, a plan touching it routes to the
  light path — an under-review window. So the cost is asymmetric toward
  UNDER-inclusion (a real bypass window) vs OVER-inclusion (a little wasted
  review). Integrity > efficiency resolves the asymmetry toward inclusion.
Recommendation: Fast-track the low-controversy part (the pair); apply deeper
  analysis to the lock-file part.
Next framework: Pros-Cons-Fixes (+ Second-Order overlay for lock-files)
```

### Pros-Cons-Fixes — the lock-file sub-decision (the crux)

```
Option: Enumerate lock-files by exact basename at any depth (Approach A's lock part)

Pros:
- Closes the supply-chain gap including nested subproject lock-files.
- Uses the already-precedented **/basename glob shape (same as **/opencode.json).
- Fully mechanical (exact-basename match).

Cons and Fixes:
| Con | Fix |
|-----|-----|
| Open-ended, ecosystem-versioned name list drifts (bun.lockb, deno.lock, go.sum, composer.lock, Gemfile.lock, flake.lock...) | State it as a CLOSED, explicitly-extended-by-amendment list — the same honesty the map already applies to repo-root files. Drift is documented, not silent. Does NOT eliminate the drift, only makes it honest. |
| Breaks the repo-root-only invariant of the other 3 literals | Note that **/opencode.json ALREADY established the nestable-glob exception; this widens an existing exception rather than inventing one. |

Post-fix verdict: VIABLE but with a standing (documented) drift surface.
```

```
Option: Defer lock-files (Approach B's lock part)

Pros:
- Nothing added can drift; the amendment stays exact and closed.
- The genuinely hard question gets its own convergence instead of riding a clean parity edit.
- Matches the round-3 precedent, which deferred exactly this.

Cons and Fixes:
| Con | Fix |
|-----|-----|
| Lock-file supply-chain gap stays open | Sharpen the deferral note so the gap is explicit and the reasoning (nestability + open list) is recorded; near-term exposure is nil (no lock-file exists in-repo today). |
| Requires a second future amendment | Accept the mild process cost; it is the price of not folding an unresolved tradeoff into an "easy" edit. |

Post-fix verdict: VIABLE; leaves a documented (not silent) gap.
```

### Second-Order Thinking — the lock-file / `X`-overload question (Approach C)

```
Decision: Route lock-files via X (the disqualifier) instead of by name in E (Approach C, c1)

Near term (3–6 months):
  First-order: Any lock-file forces the full 8-stage pipeline (strongest route).
  Second-order: X's clean "does-it-execute?" predicate now also means "or is
    high-consequence inert data," blurring the one crisp predicate the classifier
    has — AND the cognition-layer Gate-1 routing keys on the SAME X set, so the
    blur propagates into which Design-Principles form a plan must produce.

Far term (1–2 years):
  First-order: Every future "is this high-consequence inert data?" question gets
    litigated against X, which was designed to answer a different question.
  Second-order: X becomes a catch-all and loses determinism; the exact
    non-determinism the classifier exists to remove creeps back in via X.
  Third-order: The cognition layer inherits the ambiguity (its routing is keyed
    on X), so the rot spreads to a second subsystem.

Key insight: E is the RIGHT home for "high-consequence declarative config" —
  that is precisely what E already holds (.gitignore/.envrc/pyproject.toml are
  all inert declarative config). X is for things that EXECUTE. Lock-files are
  inert → they belong in E (by name), not in X. Approach C solves the drift
  problem by creating a worse semantic-overload problem in a shared predicate.
Verdict: REJECT Approach C — the X/E boundary (execute vs declarative) is a load-
  bearing distinction; do not overload it to dodge a name-list.
```

**Bias warnings:**

- ⚠️ **Status Quo Bias detected (mild):** The "defer lock-files" option is partly
  attractive *because the round-3 pass already deferred it* — a prior deferral is
  not itself a reason to defer again. Checked against merits: the deferral still
  holds on its own logic (nestability + open list are a genuinely distinct design
  question, and no lock-file exists in-repo today), not merely because it is the
  incumbent choice. Warning surfaced so the operator can weigh it independently.
- ⚠️ **Scope Creep Bias detected (mild):** Approach A's instinct to "close the
  whole class in one pass" risks folding an unresolved, open-ended sub-problem
  (lock-file name drift) into an otherwise-clean amendment to *avoid* a second
  decision. Forcing the pair/lock-file split (Parts 1 & 2) is the anti-dote —
  each part gets the treatment its actual difficulty warrants.
- (Also considered and NOT triggered: Anchoring — the analysis re-derived each
  option's merits rather than adjusting from the round-3 anchor; Confirmation —
  counter-evidence for the recommended split is explicitly sought via Approach A's
  pros.)

**Recommendation (ADVISORY ONLY — the operator decides at convergence):**

**Approach B** — add `.gitattributes` and `.gitmodules` to `E` now as repo-root
exact-path literals (clean, mechanical, uncontroversial parity with `.gitignore`);
**defer lock-files** to their own dedicated decision with a sharpened deferral
note. Rationale:

1. The pair is a **two-way door with the reversal-cost asymmetry pointing toward
   inclusion** — pure upside, no invariant broken, exact parity with an
   already-ratified precedent.
2. Lock-files carry a **genuine unresolved tradeoff** (nestability breaks the
   repo-root invariant; the basename list is open-ended and drifts). Folding that
   into a "clean parity" edit would smuggle an unconverged material decision past
   the operator — the exact failure the precept-10 gate exists to prevent.
3. Approach C (route lock-files via `X`) is **rejected** on second-order grounds:
   it overloads the load-bearing execute-vs-declarative predicate that both the
   classifier and the cognition layer depend on.

**Secondary note for the operator:** if the operator prefers to close the entire
class in one pass, **Approach A is viable** — provided the lock-file list is
written as an *explicit closed list, extended only by amendment* (never a
predicate), using the already-precedented `**/basename` glob shape, and matched
at any depth to catch nested subproject lock-files. The only real cost of A over
B is accepting a documented, standing name-list drift surface. This is a
legitimate operator call between "close it all now, accept drift" (A) and "add
only the exact/closed parts now, give lock-files their own convergence" (B).

## Selected Approach (Converge — OPERATOR-CONVERGED)

**Convergence provenance.** `gleipnir-brainstorm` is a subagent whose `question`
tool cannot reach the operator, so it did **not** converge this itself. The
`## Decision Analysis` above was returned to the **orchestrator**, which put the
decision to the **operator via its `question` tool** (the precept-10 convergence
gate). The orchestrator handed the operator's converged choice back to this
role, and it is recorded below. This is **not** a self-attested decision by the
subagent — it is the operator's choice, routed through the orchestrator.

**Chosen: Approach B.** Scope of **THIS round** = enumerate `.gitattributes` and
`.gitmodules` into set `E` **only**. Lock-files are **explicitly deferred** to a
future dedicated convergence — carried forward as an open item, not silently
dropped (consistent with how round-3 `classifier-tightening.md` deferred this
same gap before).

**Operator-converged answers to the three questions:**

- **Q1 — `.gitattributes` / `.gitmodules`:** **OPERATOR-CONVERGED — YES, add both
  now** as repo-root **always-hardened** exact-path literals in set `E`, same
  class and rationale as `.gitignore` (git-behaviour / version-control-integrity
  surface). This is the full scope of the amendment this round produces.
- **Q2 — lock-files routing:** **OPERATOR-CONVERGED — Approach B (defer).**
  Lock-files are **NOT** enumerated into `E` this round. They are deferred to
  their own dedicated convergence later, because the genuine tradeoff (nestability
  breaks the repo-root-only invariant; the basename list is open-ended and
  drifts) deserves its own decision rather than riding on this clean-parity edit.
  Approach C (route via `X`) remains advised-against per the Second-Order analysis
  above and was not chosen.
- **Q3 — lock-file seed list:** **MOOT this round.** Because Q2 resolved to
  Approach B (defer), **no seed list is applied now.** The seed list
  (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`,
  `Pipfile.lock`, `Cargo.lock`) is **retained in this brief as a starting point
  for the FUTURE dedicated lock-files convergence only** and is **explicitly NOT
  applied** in this round's amendment.

**Deferred open item (carry forward — do not drop).** Lock-file enumeration into
`E` remains an **open, deferred design decision** requiring its own convergence.
It should stay on the same open-items ledger where the round-3
`classifier-tightening.md` deferral already recorded it (SESSION-STATE "same-class
gap" note), now narrowed: `.gitattributes`/`.gitmodules` are being closed this
round; **lock-files remain the sole outstanding member of the same-class gap.**

**Rationale (as converged):** the pair is a two-way door with reversal-cost
asymmetry pointing toward inclusion — exact, mechanical, uncontroversial parity
with an already-ratified precedent, no invariant broken. Deferring lock-files
keeps this amendment fully exact and closed (nothing added can drift) and gives
the genuinely hard sub-question its own dedicated convergence — avoiding smuggling
an unconverged material tradeoff past the gate.

## Open Questions

- **Q1–Q3** — **RESOLVED at convergence** (see Selected Approach): Q1 = add both;
  Q2 = Approach B (defer lock-files); Q3 = moot this round (seed list retained for
  the future lock-files pass, not applied now).
- **DEFERRED (carry forward):** lock-file enumeration into `E` — its own dedicated
  convergence, using the retained seed list as a starting point. Sole remaining
  member of the same-class gap after this round closes `.gitattributes`/`.gitmodules`.
- **Per-file rationale wording** (for `gleipnir-plan` to draft — scope: the two
  converged files only this round),
  matching the existing per-file style in `E`:
  - `.gitattributes` — *"governs per-path git behaviour (line-ending
    normalisation, `filter`/`clean`/`smudge` drivers, `diff`/`merge` driver
    selection, `export-ignore`, binary treatment); a changed attribute can
    silently alter how tracked content is stored, filtered, or diffed — same
    version-control-behaviour class as `.gitignore`."*
  - `.gitmodules` — *"declares submodule URLs/paths; a changed URL can point a
    submodule at attacker-controlled content pulled into the tree — a
    supply-chain / version-control-integrity surface, same class as
    `.gitignore`."*
  - (If A) lock-files — *"pin exact dependency versions/hashes; a silent
    lock-file edit is a known supply-chain vector — same intent class as
    `pyproject.toml`'s dependency-range rationale; matched by exact basename at
    any depth (nested subproject lock-files are in scope), extended only by
    explicit amendment (a closed list, never a predicate)."*
- **Enforcement-bearing routing confirmation (see Scope Sketch):** this change
  edits `stage-role-map.md ∈ E` → Axis 2(a) → **HARDENED path**. `gleipnir-plan`
  must carry the hardened Execution Workflow (two rubrics + negative-check
  attestation, `attested_by ≠ author`, all five SUCCESS-gate clauses) — exactly
  as the round-3 `classifier-tightening.md` plan did (clean dogfood precedent).
- **Whether to also record the outcome in a durable decision record.** The
  round-3 change was captured in SESSION-STATE (Tier-0). Because `E` membership
  is a durable enforcement decision, the operator may wish the converged outcome
  recorded in a Tier-3 `decisions/` record (operator-authored), not only in a
  disposable plan. Named here for the operator to persist.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| The amendment target | `.gleipnir/stage-role-map.md` — the `E` literal in Axis 2(a) (currently the `.gitignore`/`.envrc`/`pyproject.toml` clause), plus per-file rationale lines in the same style |
| Routing self-classification | This change touches `stage-role-map.md ∈ E` → **HARDENED path** (Axis 2(a)); NOT light path. Confirmed against the map's own rules. |
| Apply authority | Tier-3, **operator-apply-only** — no roster agent (incl. `gleipnir-plan`) writes `stage-role-map.md`; the plan produces ready-to-apply diff text, the operator applies it |
| Precedent to mirror | `plans/classifier-tightening.md` round-3 Edit A (the `.gitignore`/`.envrc`/`pyproject.toml` enumeration) — same mechanism, same hardened-dogfood workflow |
| Cross-cutting (only if Approach C) | `X` disqualifier set + cognition-layer Gate-1 routing (keyed on `X`) — **advised against for exactly this coupling** |
| Possible durable record | operator-authored `.gleipnir/decisions/` entry for `E` membership (named for the operator; not writable by this role) |
