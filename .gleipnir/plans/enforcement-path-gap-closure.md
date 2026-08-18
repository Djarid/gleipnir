# Plan: Enforcement-path set `E` — same-class gap closure (`.gitattributes` + `.gitmodules`; lock-files deferred)

**Tier / apply authority:** Tier-3 amendment to `.gleipnir/stage-role-map.md` (POLICY). **Operator-apply-only** — no roster agent, **including this planner (`gleipnir-plan`)**, may write `stage-role-map.md` (see the "Apply authority" finding in Assemble). This plan produces byte-accurate ready-to-apply edit text; the operator applies it.

**Routing self-classification (HARDENED path — dogfood):** This plan's touched-path set `P` includes `.gleipnir/stage-role-map.md`, which is itself a member of enforcement-path set `E` (Axis 2(a)). By the track's OWN rules the plan is therefore **enforcement-bearing → HARDENED path**: spec-review/quality run **two separate rubrics** (SPEC-CONFORM + BLAST-RADIUS, which do NOT fuse) plus a **negative-check attestation** with `attested_by ≠ author` and all five SUCCESS-gate clauses. This mirrors the round-3 `classifier-tightening.md` precedent (a clean dogfood of the same rule). NOT the light path.

**Provenance:** planned FROM the converged brief `.gleipnir/plans/enforcement-path-gap-closure-brainstorm.md`. Q1/Q2/Q3 are **OPERATOR-CONVERGED (Approach B)** and are NOT re-decided here — this plan implements only the bounded work the converged brief defines. Convergence was routed through the orchestrator's `question` tool (precept-10 gate); this planner surfaces no new material tradeoff (see Decisions index).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Which files to enumerate into `E` this round | `.gitattributes` + `.gitmodules` as repo-root always-hardened exact-path literals | Also enumerating lock-files now (Approach A); routing lock-files via `X`/content rule (Approach C) | **OPERATOR-CONVERGED (Approach B)** — brief `## Selected Approach`, Q1=YES/Q2=defer/Q3=moot. Routed to operator via orchestrator `question` tool. Not re-decided here. |
| 2 | Lock-files this round | **Deferred** to a future dedicated convergence; carried forward as a named open item (not silently dropped) | Fold lock-files into this clean-parity edit | **OPERATOR-CONVERGED (Approach B, Q2).** Nestability breaks the repo-root-only invariant and the basename list is open-ended/drifting — a genuine tradeoff deserving its own convergence; folding it in would smuggle an unconverged material decision past the gate. |
| 3 | How the two additions match on-disk | Exact repo-root path match (`.gitattributes`, `.gitmodules`), parity with `.gitignore`/`.envrc`/`pyproject.toml` — never a glob/predicate | `**/`-glob (nestable) or a fuzzy "governs git" predicate | Determinism is non-negotiable; the map explicitly rejects predicates. Both files are repo-root singletons (unlike lock-files), so exact-path parity is correct and drift-free. |
| 4 | Per-file rationale wording | Draft one-line rationale per file in the existing per-file style (git-behaviour / version-control-integrity class, same as `.gitignore`) | Reuse `.gitignore`'s rationale verbatim; omit rationale | Style parity is a brief constraint; each `E` literal carries its own one-line rationale. Wording seeded by the brief's Open-Questions draft, refined here. |
| 5 | Who applies the `stage-role-map.md` edit | **Operator only** — this planner produces ready-to-apply text; does NOT (and cannot) write the file | Planner self-applies | Tier-3 POLICY is operator-only (G-1); `stage-role-map.md` is in this role's explicit `edit` deny list (agent file line 76 + `edit "*": deny`). Confirmed against own agent file — see Assemble "Apply authority". Mirrors `s2-activation.md` C2 handling. |
| 6 | Durable-record capture | **Named for the operator** to optionally persist in a Tier-3 `decisions/` record; not written by this role | Write a `decisions/` entry from this role | `decisions/` is Tier-3 operator-authored; this role cannot write it. `E` membership is a durable enforcement decision, so it is surfaced (Open Items) for the operator to persist. |

**No new material tradeoff is introduced by this planning pass.** Every material choice is inherited operator-converged (rows 1–2) or is a mechanical/style consequence of the converged scope (rows 3–4) or a capability-boundary fact (rows 5–6). Nothing here requires a return to the brainstorm gate.

---

## Architect

**Problem (one sentence):** two repo-root files in the same blast-radius class as `.gitignore` — `.gitattributes` (governs per-path git behaviour) and `.gitmodules` (declares submodule URLs/paths) — are not yet enumerated into enforcement-path set `E`, so a plan touching either would route to the light (under-reviewed) path until `E` names them.

**User:** the `quality-reviewer` (who computes a plan's route and produces hardened-path attestations) and the future G-5 routing engine (which computes light/hardened mechanically, with no per-plan LLM judgment); indirectly the operator who trusts the classifier's determinism and coverage honesty.

**Measurable success criteria:**
1. `.gitattributes` and `.gitmodules` each appear in the `E` set literal (Axis 2(a)) as **exact repo-root path** entries, so a plan touching either routes hardened by exact-path match.
2. Each new entry carries its own **one-line rationale** in the existing per-file style (parity with `.gitignore`/`.envrc`/`pyproject.toml`).
3. Both additions remain **mechanical** — decidable by exact-path match, no glob, no fuzzy "governs git" predicate.
4. Lock-files are **explicitly named as deferred** (a future dedicated convergence), carried forward as an open item — **not** silently dropped and **not** enumerated this round.
5. The track's Approach-B structure (Axis 1 disqualifier `X`, Axis 2 (a) path / (b) content, light vs hardened paths, two-rubric non-fusion, negative-check attestation, the five SUCCESS-gate clauses) is **unchanged** — the edit is purely additive to the Axis 2(a) enumeration.
6. The amendment is applied by the **operator** (Tier-3); this plan emits ready-to-apply text and this role does not (and cannot) write `stage-role-map.md`.

**Constraints (inherited from the converged brief):**
- **Tier-3, operator-apply-only.** This change edits `stage-role-map.md ∈ E`; itself enforcement-bearing → HARDENED path.
- **Determinism non-negotiable.** Exact-path match only; the map explicitly rejects predicates.
- **Precedent invariant — repo-root-only.** Both `.gitattributes` and `.gitmodules` are repo-root singletons (parity with the other three literals). Lock-files break this invariant (they can nest) — the crux reason they are deferred, per the brief.
- **Integrity > efficiency.** When in doubt, over-include (extra review) rather than under-review a bypass.
- **Style parity.** Each `E` literal carries its own one-line rationale.
- **L-C15.** Every cited path confirmed to exist or explicitly marked to-be-created (see Link — the two subject files do NOT exist in-repo today; this is a pre-emptive enumeration, as the brief records).

---

## Trace

**Artifact (single source of truth):** `.gleipnir/stage-role-map.md`, section `## Prose/config-only track (blast-radius split)`, sub-section `### Axis 2 — routing within the eligible set`, the `- **(a) path rule:**` block — **current lines 95–118** (read fresh this session; captured verbatim in Assemble Edit A "BEFORE").

**Touched-path set `P` for THIS plan:** `{ .gleipnir/stage-role-map.md, .gleipnir/plans/enforcement-path-gap-closure.md }`.
- `stage-role-map.md` ∈ `E` → Axis 2(a) → **hardened** (dogfood; also drives the Design-Principles Axis-1 routing below — `P ∩ X = ∅`, since neither path is in the disqualifier set `X`).
- `.gleipnir/plans/**` is Tier-0, non-enforcement; does not change the route.

**Integrations map:**
- The `E` set literal (Axis 2(a)) is consumed by the future G-5 engine and by `quality-reviewer` when computing a plan's route. Adding two exact-path literals **extends coverage**; it changes no existing entry and cannot narrow any route (a file added to `E` can only ever route *more* plans hardened — the two-way-door / reversal-cost-asymmetry-toward-inclusion property the brief's Reversibility Filter established).
- The Axis-1 disqualifier set `X`, the content rule Axis 2(b), the light/hardened path definitions, the two-rubric non-fusion, the attestation schema, and the five SUCCESS-gate clauses are **not touched**.
- No code, no test, no config-with-behaviour is touched — a prose amendment to a policy doc only.

**Edge cases considered:**
- **Are `.gitattributes` / `.gitmodules` already disqualified by `X` (so `E` would be redundant)?** No. `X` is executable/interpreted artifacts + standalone YAML. `.gitattributes` and `.gitmodules` are inert declarative git-config files (git's own INI-ish/attribute syntax), not `*.yml`/`*.yaml`, no shebang, no `+x`. They are NOT in `X` → they need Axis 2(a) to route hardened. Not double-counted. (Same reasoning the round-3 plan applied to `.envrc`/`pyproject.toml`.)
- **Nestability.** Unlike lock-files, `.gitattributes` *can* technically appear in subdirectories, but the **enforcement-relevant** one is the repo-root file (git applies nested `.gitattributes` only within their subtree, and the audit/behaviour surface of concern is the top-level one). Enumerating the **repo-root exact path** keeps parity with the other three literals and preserves the repo-root-only invariant. A future pass may revisit nested `.gitattributes` alongside the deferred lock-file convergence if warranted — noted, not decided here. `.gitmodules` is canonically repo-root only.
- **Ordering / list-shape.** The `E` literal already mixes `.gleipnir/**` paths, the nestable `**/opencode.json` glob, and repo-root exact paths (`.gitignore`, `.envrc`, `pyproject.toml`). Appending two more repo-root exact paths to the existing "repo-root cross-cutting files" clause is consistent with the current list shape — no structural change.
- **Lock-file deferral honesty.** The deferral must be *recorded*, not silent (brief Q2 + the round-3 precedent). Captured as an explicit Open Item and a Stress-test check, narrowed to "lock-files are the sole remaining member of the same-class gap after this round."
- **Pre-emptive enumeration.** Neither subject file exists in-repo today (brief ground-truth, re-confirmed in Link). The value is coverage-map completeness: an exact-enumeration classifier covers a file only once named, so naming it now closes the window *before* the file is ever added.

---

## Link (validated before building)

- **CURRENT `E` block** read fresh this session: `stage-role-map.md` lines **95–118** (file is 291 lines total). Exact strings for the edit captured verbatim in Assemble Edit A "BEFORE" — the insertion is byte-accurate against the applied post-round-3 state.
- **Round-3 precedent** `plans/classifier-tightening.md` read (219 lines): confirms the mechanism (explicit exact-path enumeration into `E`), the hardened-path Execution Workflow, the operator-apply-only handling, and that the round-3 pass **deferred exactly this same-class gap** (the deferral this plan now partially closes for `.gitattributes`/`.gitmodules`).
- **Converged brief** `plans/enforcement-path-gap-closure-brainstorm.md` read (428 lines): Q1/Q2/Q3 operator-converged answers, the deferred-open-item instruction, and the seeded per-file rationale wording (Open Questions section) — all inherited, not re-decided.
- **Ground truth (brief-recorded, honoured here):** none of `.gitattributes`, `.gitmodules`, or any `*.lock` file exists in this repo today — only `.gitignore` exists. This plan therefore marks the two subject files as **to-be-covered-pre-emptively**, satisfying L-C15 (not cited as existing; explicitly a future-proofing enumeration).
- **Own agent file** `agents/gleipnir-plan.md` read (96 lines): `edit "*": deny` with only `.gleipnir/plans/**: allow`; line 76 explicitly lists `stage-role-map.md` in the deny set. **Confirms this role cannot write the target file** — see Assemble "Apply authority".
- No tools/connections beyond read + write-plan needed; this is a prose amendment producing ready-to-apply text.

---

## Assemble (intended build order → ready-to-apply text)

**Apply authority (confirmed finding — Decision 5):** `stage-role-map.md` is Tier-3 POLICY. `.gleipnir/AGENTS.md` states Tier-3 is *"operator only (G-1)."* This role's agent file (`agents/gleipnir-plan.md`) sets `edit "*": deny` and allows only `.gleipnir/plans/**`, and line 76 names `stage-role-map.md` explicitly in the deny set. **Therefore `gleipnir-plan` does NOT hold write access to `stage-role-map.md`; the actual application of this edit is OPERATOR-ONLY.** This plan produces the ready-to-apply text below; the operator applies it by hand (or an operator-run tool), exactly as `s2-activation.md`'s C2 proposal was handled and as the round-3 `classifier-tightening.md` plan handled its Tier-3 edits.

**Build order (single edit):**

### Edit A — extend the Axis 2(a) `E` enumeration (repo-root cross-cutting files) to add `.gitattributes` + `.gitmodules`

Two changes within the one block: (1) add the two filenames to the enumerated list on the "or the repo-root cross-cutting files" line; (2) insert their per-file rationale immediately after the `pyproject.toml` rationale sentence and before the "These are enumerated **explicitly**" sentence, matching the existing per-file rationale style.

**BEFORE (current lines 95–118, verbatim):**
```
- **(a) path rule:** any path in `P` is under the enforcement-path set `E` =
  `.gleipnir/agents/**`, `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`,
  `.gleipnir/policy/**`, `.gleipnir/keys/**`, `.gleipnir/stage-role-map.md`
  itself; the root opencode config `opencode.jsonc` / `**/opencode.json`
  (it loads this map via `instructions`, gates the MCP brokers via `enabled`,
  and sets `default_agent`); or the repo-root cross-cutting files
  `.gitignore`, `.envrc`, and `pyproject.toml` — each **always** hardened by
  exact-path match. Rationale, per file: `.gitignore` governs what reaches
  version control, including whether the `.gleipnir/keys/**` integrity digests
  (the G-3 audit trail — versioned by policy, see `keys/README.md`) keep being
  committed; a plan silently adding `*.digest` there is an audit-trail bypass.
  `.envrc` sets `OPENCODE_CONFIG_DIR=.gleipnir`, wiring which config dir
  opencode loads at all. `pyproject.toml` carries the dependency ranges bound
  to the stdlib-only enforcement-core constraint
  (`decisions/runtime-and-deps.md`). These are enumerated **explicitly** (the
  `opencode.jsonc`/round-1 precedent), not via a fuzzy "repo-root files that
  wire enforcement" predicate: that predicate is a judgment call, not
  grep-able, and would reintroduce the non-determinism the classifier exists to
  remove. New repo-root cross-cutting files join `E` by explicit amendment, not
  by a predicate. `.gitignore` is always-hardened (not conditional on which
  patterns it touches) because "which ignore patterns are enforcement-adjacent"
  is itself a judgment surface — always-hardened over-includes a few benign
  edits but never under-reviews an audit-trail bypass (integrity > efficiency,
  as with the standalone-YAML disqualification above); **or**
```

**AFTER (apply verbatim):**
```
- **(a) path rule:** any path in `P` is under the enforcement-path set `E` =
  `.gleipnir/agents/**`, `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`,
  `.gleipnir/policy/**`, `.gleipnir/keys/**`, `.gleipnir/stage-role-map.md`
  itself; the root opencode config `opencode.jsonc` / `**/opencode.json`
  (it loads this map via `instructions`, gates the MCP brokers via `enabled`,
  and sets `default_agent`); or the repo-root cross-cutting files
  `.gitignore`, `.envrc`, `pyproject.toml`, `.gitattributes`, and
  `.gitmodules` — each **always** hardened by exact-path match. Rationale, per
  file: `.gitignore` governs what reaches
  version control, including whether the `.gleipnir/keys/**` integrity digests
  (the G-3 audit trail — versioned by policy, see `keys/README.md`) keep being
  committed; a plan silently adding `*.digest` there is an audit-trail bypass.
  `.envrc` sets `OPENCODE_CONFIG_DIR=.gleipnir`, wiring which config dir
  opencode loads at all. `pyproject.toml` carries the dependency ranges bound
  to the stdlib-only enforcement-core constraint
  (`decisions/runtime-and-deps.md`). `.gitattributes` governs per-path git
  behaviour (line-ending normalisation, `filter`/`clean`/`smudge` drivers,
  `diff`/`merge` driver selection, `export-ignore`, binary treatment); a
  changed attribute can silently alter how tracked content is stored, filtered,
  or diffed — same version-control-behaviour class as `.gitignore`.
  `.gitmodules` declares submodule URLs/paths; a changed URL can point a
  submodule at attacker-controlled content pulled into the tree — a
  supply-chain / version-control-integrity surface, same class as `.gitignore`.
  These are enumerated **explicitly** (the
  `opencode.jsonc`/round-1 precedent), not via a fuzzy "repo-root files that
  wire enforcement" predicate: that predicate is a judgment call, not
  grep-able, and would reintroduce the non-determinism the classifier exists to
  remove. New repo-root cross-cutting files join `E` by explicit amendment, not
  by a predicate. `.gitignore` is always-hardened (not conditional on which
  patterns it touches) because "which ignore patterns are enforcement-adjacent"
  is itself a judgment surface — always-hardened over-includes a few benign
  edits but never under-reviews an audit-trail bypass (integrity > efficiency,
  as with the standalone-YAML disqualification above). Lock-files
  (`package-lock.json`, `poetry.lock`, `Cargo.lock`, `yarn.lock`,
  `Pipfile.lock`, `pnpm-lock.yaml`, …) are in the **same blast-radius class**
  (a silent lock-file edit is a known supply-chain vector) but are
  **deliberately NOT enumerated here yet** — they are DEFERRED to their own
  dedicated convergence because they can appear **nested** in subprojects
  (breaking the repo-root-only invariant of every other literal above) and
  their basename list is open-ended and ecosystem-versioned; folding that
  unresolved tradeoff into this clean-parity amendment is explicitly avoided.
  Lock-files remain the sole outstanding member of this same-class gap after
  this amendment; **or**
```

**Notes on the AFTER text:**
- The two filenames are added to the existing enumeration line as **exact repo-root paths** (no glob), preserving the repo-root-only invariant and determinism.
- The two per-file rationales are inserted in list-order after `pyproject.toml` and before "These are enumerated **explicitly**", in the same one-sentence-per-file style; wording is the brief's seeded draft, lightly refined.
- The **lock-file deferral** is recorded inline (Decision 2 / brief Q2), so the coverage boundary is honest in the artifact itself — not merely in a disposable plan. It uses "DEFERRED … dedicated convergence" language and states the *reason* (nestability + open list), matching the round-3 deferral style.
- **No other line in the section changes.** Axis 2(b), the light/hardened paths, the two-rubric non-fusion, the attestation schema, and the five SUCCESS-gate clauses are untouched.

**No durable-record write by this role.** If the operator wants `E` membership recorded in a Tier-3 `decisions/` entry (the brief names this as an option), the operator authors it; this role cannot (Decision 6).

---

## Stress-test (acceptance checks)

Applied to `stage-role-map.md` **after** the operator applies Edit A (captured against the post-apply file, per the track's own post-change-state rule):

1. **Enumeration present:** the Axis 2(a) `E` literal enumeration line lists `.gitattributes` and `.gitmodules` as exact repo-root paths, alongside the existing `.gitignore`/`.envrc`/`pyproject.toml`. Verify: `grep -n "\.gitattributes\`\|\`\.gitmodules" .gleipnir/stage-role-map.md` shows both within the Axis 2(a) block.
2. **Per-file rationale present + style parity:** each of `.gitattributes` and `.gitmodules` has its own one-line rationale in the same style as the other three literals (each names the git-behaviour / version-control-integrity concern and the "same class as `.gitignore`" tie).
3. **Mechanical / no predicate:** the additions are decidable by **exact repo-root path match** only — no glob (no `**/.gitattributes`, no `*.git*`) and no fuzzy "governs git" predicate. Verify no wildcard form of either filename appears.
4. **Lock-files deferred, not dropped:** the block explicitly states lock-files are the same class but **DEFERRED to a dedicated convergence** (with the nestability + open-list reason), and names them the sole remaining member of the same-class gap. Verify the words "DEFERRED"/"deferred" and "lock-file" co-occur in the block.
5. **Structure preserved:** Axis 1 (`X`), Axis 2(a)/(b), light path, hardened path, two-rubric non-fusion, attestation schema, and the five SUCCESS-gate clauses are all still present and unmodified except the additive enumeration + rationale + deferral note above.
6. **No route narrowed:** the change is purely additive to `E`; no existing `E` entry is removed or altered, so no previously-hardened plan becomes light-path (coverage only widens).
7. **Additive line-count:** the section grew; no BEFORE content was deleted (the only edit to existing text is inserting two names into the enumeration line and re-wrapping that sentence; all prior rationale sentences are preserved verbatim).

**All checks stay mechanical** — exact-path enumeration (check 1/3), style/presence (check 2/4), structural diff (check 5/6/7). No check requires a judgment call.

---

## Execution Workflow (HARDENED path — dogfood of the track's own rule)

This plan touches `stage-role-map.md ∈ E`, so it MUST run the hardened path. Sequencing (orchestrator/operator):

1. **plan** (this file) — done.
2. **spec-review — TWO SEPARATE rubrics** by `quality-reviewer` (they do NOT fuse):
   - **(a) Spec-conformance** (rubric = this plan + the converged brief): does Edit A add exactly `.gitattributes` + `.gitmodules` as repo-root exact-path literals with per-file rationale, defer lock-files (not enumerate them), and change nothing else? `SPEC-CONFORM: PASS/FAIL`. **Includes the cognition cross-check's intent-quality sub-check**: is the Design Intent (below) specific/falsifiable, not a vacuous aspiration?
   - **(b) Blast-radius / false-success** (rubric = *how could this be wrongly green?*): adversarial pass. Specifically check: does the AFTER text accidentally introduce a **glob** (e.g. `**/.gitattributes`, `*.git*`) that would widen routing beyond the two named repo-root files? Does it accidentally enumerate a lock-file (violating the converged defer)? Does it delete or reword any existing rationale sentence? Does it alter Axis 2(b) or the SUCCESS-gate clauses? **Includes the SOLID/DRY dimension** — scoped by the Gate-1 case below (case (iii) → SOLID/DRY/SRP skipped, N/A). A single fused "looks fine" verdict is a non-conformance.
3. **Negative-check attestation** by `quality-reviewer` (`attested_by ≠ author`), one row for the enforcement change. At minimum:
   - **Row — `E` extension (Edit A):** grant = "add `.gitattributes` and `.gitmodules` to `E` as exact repo-root path literals in `stage-role-map.md`"; intended narrowest scope = those two exact repo-root paths only; `over_broad_form_checked` = "a glob/wildcard form (e.g. `**/.gitattributes`, `**/.gitmodules`, `*.git*`) that would catch files beyond the two named repo-root ones, OR an accidental lock-file enumeration"; `evidence` = literal `grep` of the **post-apply** `stage-role-map.md` showing (i) both filenames appear as exact strings in the Axis 2(a) block, (ii) NO `**/`-glob or `*`-wildcard form of either appears, (iii) no `*.lock`/lock-file basename was added to `E`; `negative_result` = "no wildcard/glob form of `.gitattributes`/`.gitmodules` is present, and no lock-file was enumerated into `E`"; captured against the **post-apply** file; tag `[D]` (tool-produced grep).
   - Each `evidence` field: concrete reproducible artifact (command + output), same pattern named in `over_broad_form_checked`, same file named in `grant` (`stage-role-map.md`), captured against the applied/post-change state (per the very rule the track installs).
4. **test / code / git / gate:** carry the attested **"N/A — no executable artifact"** transition (prose/policy amendment; the `git` stage is the operator's apply of the Tier-3 file, since no roster agent — including this planner — may write `stage-role-map.md`).
5. **quality — honour check** (cognition cross-check, quality-stage half): does the applied edit honour the stated Design Intent (below)? A divergence is **Important** and **blocks `git` until the operator acknowledges it** (the reviewer never self-clears — L-C8).
6. **SUCCESS gate:** may report SUCCESS only if (i) two distinct pass verdicts exist, (ii) attestation present with all fields and `attested_by ≠ author`, (iii) evidence reproducible not narrative, (iv) evidence tests the named form in the named file, (v) evidence captured post-change — the exact five-clause gate the track defines.

**Operator apply:** because `stage-role-map.md` is Tier-3, the operator applies Edit A by hand (or an operator-run tool); no roster agent — including this planner — writes the file.

---

## Design Principles (Gate 1 — design-time cognition gate)

**Axis-1 routing (which of the three cases):** This plan's touched-path set is `P = { .gleipnir/stage-role-map.md, .gleipnir/plans/enforcement-path-gap-closure.md }`. Neither path is a member of the Axis-1 disqualifier set `X` (no `src/**`, `tests/**`, `bin/**`, Makefile, `*.mk`, Containerfile, `.github/**`, standalone `*.yml`/`*.yaml`, shell/`*.py`/`*.js`/…, no `+x` file, no shebang). `stage-role-map.md` and the plan file are both **inert markdown**. Therefore **`P ∩ X = ∅` → case (iii) prose/config-only.**

**SOLID analysis:** **N/A — no executable artifact.** (No class/function/module/interface exists to analyse for Single-Responsibility / Open-Closed / Liskov / Interface-Segregation / Dependency-Inversion; the change is a prose edit to a policy document.)

**DRY analysis:** **N/A — no executable artifact.** (No logic, helper, or constant is defined; the per-file rationale sentences are intentionally parallel prose, not duplicated code.)

**Single Responsibility check:** **N/A — no executable artifact.** (No module/class/function is introduced.)

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**

> This amendment closes the **`.gitattributes` + `.gitmodules` half** of the same-blast-radius-class gap first named and deferred in round-3 `classifier-tightening.md`, by enumerating **exactly those two files** into enforcement-path set `E` (Axis 2(a)) as **repo-root exact-path literals** — matching the `.gitignore`/`.envrc`/`pyproject.toml` precedent — such that a plan touching either routes to the hardened path by exact-path match. It does so **without** (a) enumerating lock-files (their nestability breaks the repo-root-only invariant and their basename list is open-ended, so they are explicitly recorded as the sole remaining deferred member of the same-class gap, not silently dropped), and **without** (b) introducing any glob or fuzzy "governs git" predicate in place of the two explicit repo-root literals (which would reintroduce the non-determinism the classifier exists to remove).

**Why this Design Intent is falsifiable (not a generic aspiration):** a reviewer can point to a concrete violation of any clause — e.g. the AFTER text enumerates a lock-file basename (violates the "without (a)" clause); or it uses `**/.gitattributes` / `*.git*` instead of the two exact repo-root paths (violates the "without (b)" clause and the repo-root-only invariant); or it drops the deferral note so lock-files vanish silently (violates the "not silently dropped" clause); or it reroutes/removes an existing `E` entry (violates "closes … by enumerating exactly those two files"). Each is a specific, checkable failure — this is the quality-stage honour check's rubric.

---

## Open Items (carry forward — do not drop)

- **DEFERRED: lock-file enumeration into `E`.** Remains an open, deferred design decision requiring its **own dedicated convergence**, using the brief's retained seed list (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Pipfile.lock`, `Cargo.lock`) as a starting point. After this amendment, lock-files are the **sole remaining member** of the same-class gap. Stays on the same open-items ledger as the round-3 deferral (SESSION-STATE "same-class gap" note), now narrowed.
- **Possible durable record.** `E` membership is a durable enforcement decision; the operator may wish to record the converged outcome in a Tier-3 `decisions/` entry (operator-authored). Named here for the operator to persist — this role cannot write `decisions/`.
- **Nested `.gitattributes` (noted, not decided).** Only the repo-root `.gitattributes` is enumerated (repo-root-only invariant). Whether nested subdirectory `.gitattributes` files warrant coverage is a future question that could ride the deferred lock-file convergence (both concern nestability). Surfaced, not decided.
