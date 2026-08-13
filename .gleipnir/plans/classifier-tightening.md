# Plan: Prose/config-only track — classifier tightening (round-3 deferred notes)

**Tier:** Tier-3 amendment to `.gleipnir/stage-role-map.md` (POLICY). **Operator-apply-only** — no roster agent may write `stage-role-map.md`. This plan produces the ready-to-apply diff text; the operator applies it.

**Provenance:** the three notes below were raised in the round-3 spec-review of the original prose/config-only track plan and explicitly deferred as "future tightening pass, not blocking." This plan folds them in without altering the track's core Approach-B structure.

**Self-referential note (dogfood):** this plan is itself **enforcement-bearing** — it amends `stage-role-map.md`, which is in the track's own enforcement-path set `E` (Axis 2(a)). So by the track's OWN rules it must run the **HARDENED path**: two separate review rubrics (spec-conformance + blast-radius) and a negative-check attestation with `attested_by ≠ author`. This is captured in the Execution Workflow below.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | How to fix the correspondence "where applicable" hedge (note 1) | Remove the hedge; make same-file matching **always required** — evidence's target file MUST be the same file named in `grant`. Make detail rule and summary criterion (iv) say the same thing. | Keep the hedge but *define* when same-file is "not applicable" | Every grant/enforcement change names a specific target file, so same-file matching is *always* applicable — the hedge described a case that never occurs. Removing it is both simpler and strictly tighter; string-equality of paths is mechanical. Also eliminates the detail-softer-than-summary inconsistency the reviewer flagged. |
| 2 | Scope of the post-change-state requirement (note 2) | Require evidence be captured against the **applied / post-change state** of the target file, for **all** evidence forms (grep, diff, digest, byte-for-byte quote). | Apply only to grep/diff (leave quote/digest implicit) | A grep against a stale/pre-change copy satisfies substance+correspondence yet proves nothing about what was applied. Stating it once for all forms is uniform and mechanical (the file read/grep/digest must target the post-apply file). |
| 3 | How to handle `.gitignore`, `.envrc`, `pyproject.toml` (note 3) | **Explicit enumeration** into `E` (Axis 2(a)), same mechanism used for `opencode.jsonc`. Add all three, each always-hardened. | (a) A blanket "repo-root dotfiles/config that wire enforcement" rule; (b) making `.gitignore` conditional on touching `.gleipnir/**`/`keys/**` patterns | A blanket rule is a judgment call ("wire enforcement?" is not grep-able) — it reintroduces exactly the non-determinism the classifier exists to remove. Explicit enumeration is mechanical (exact path match) and matches the proven `opencode.jsonc` precedent. Conditional `.gitignore` was rejected because "which patterns count" is itself a judgment surface and a mis-scoped ignore is a silent audit-trail bypass (integrity > efficiency): always-hardened is the safe-side mechanical rule. |
| 4 | Enumerate vs. general rule, overall stance | Enumerate specific known files now; document that new repo-root cross-cutting files are added by explicit amendment (the `opencode.jsonc`/round-1 precedent), not caught by a fuzzy predicate. | Attempt a general mechanical predicate for "cross-cutting repo-root files" | The class ("cross-cutting enforcement-adjacent") is real but not mechanically enumerable without judgment; enumeration keeps the classifier deterministic and honest about its coverage boundary. |

---

## Architect

**Problem (one sentence):** the prose/config-only track's hardened-path evidence rules contain one underdefined hedge, one unstated freshness gap, and one unenumerated file-class gap that let a technically-conformant-but-vacuous attestation pass or route a genuinely enforcement-adjacent change to the light path.

**User:** the `quality-reviewer` (who produces hardened-path attestations) and the future G-5 routing engine (which computes the light/hardened route mechanically); indirectly the operator who trusts the classifier's determinism.

**Measurable success criteria:**
1. The correspondence detail rule (currently lines 155-160) and summary criterion (iv) (currently lines 165-166) assert the *same* same-file requirement — no residual "where applicable" softness, verifiable by grep for `where applicable` returning zero matches in the section.
2. A post-change-state requirement is present and explicitly covers all four evidence forms (grep/diff/digest/quote).
3. `.gitignore`, `.envrc`, and `pyproject.toml` each appear in the `E` set literal (Axis 2(a)), so a plan touching any of them routes hardened by exact path match.
4. All three changes remain **mechanical** (deterministic, grep-able / exact-path / exact-file-read) — no new judgment call introduced. If any could not be made mechanical, the plan says so explicitly (it does not: all three are mechanical).
5. The track's Approach-B structure (Axis 1 disqualifier, Axis 2 (a) path / (b) content, light vs hardened paths, two-rubric non-fusion, negative-check attestation) is unchanged — edits are additive/refining only.

**Constraints:**
- Tier-3, operator-apply-only. Plan outputs ready-to-apply diff text against the CURRENT lines 63-167 (read fresh this session; file is 167 lines total).
- Purely additive/edit; do not alter core structure.
- Classifier stays mechanical.
- L-C15: every cited file confirmed to exist (done — see Link).

---

## Trace

**Artifact (single source of truth):** `.gleipnir/stage-role-map.md`, section `## Prose/config-only track (blast-radius split)`, current lines 63-167.

**Touched-path set `P` for THIS plan:** `{ .gleipnir/stage-role-map.md, .gleipnir/plans/classifier-tightening.md }`.
- `stage-role-map.md` ∈ `E` → Axis 2(a) → **hardened**. (Dogfood.)
- `.gleipnir/plans/**` is Tier-0, non-enforcement; does not change the route.

**Integrations map:**
- The `E` set literal (Axis 2(a), lines 95-100) is consumed by the future G-5 engine and by `quality-reviewer` when computing a plan's route. Adding three literals extends coverage; changes no existing entry.
- The correspondence rule + summary criterion (iv) are consumed by `quality-reviewer` when validating a hardened-path attestation. Tightening them raises the rejection bar; does not change the attestation schema fields.
- No code, no test, no config-with-behavior is touched — prose amendment to a policy doc only.

**Edge cases considered:**
- **Note 1 edge:** is there ever a grant with *no* target file (so same-file is genuinely N/A)? Reviewed the attestation schema (lines 141-146): every row asserts "the exact grant" which is always a line in a specific file (`agents/*.md`, `keys/**`, this file's tables, etc.). No grant is fileless → the hedge covers an empty set → safe to remove. Documented in Decision 1 rationale so a future reader knows the removal was deliberate, not an oversight.
- **Note 3 edge — `.gitignore` conditional vs always:** a `.gitignore` edit that touches *only* `*.pyc` is low-consequence in substance, but "which ignore patterns are enforcement-adjacent" is not grep-able without judgment (is `.gleipnir/var/run/` enforcement-adjacent? `.coverage`?). Always-hardened over-includes a few benign `.gitignore` edits but stays mechanical and never under-reviews an audit-trail bypass. Chosen safe-side, consistent with the section's existing "integrity > efficiency" stance (line 85, standalone-YAML disqualification).
- **Note 3 edge — `.envrc`/`pyproject.toml` already in `X`?** Checked Axis 1 disqualifier set `X` (lines 79-82): `.envrc` is not `*.sh`/`*.bash` and carries no guaranteed shebang/`+x` (verified: 8 lines, no shebang) so it is NOT disqualified by `X` — it needs Axis 2(a). `pyproject.toml` is TOML, not in `X`, not disqualified — needs Axis 2(a). Neither is double-counted.
- **Ordering edge:** `.gitignore`/`.envrc` are repo-root (no `.gleipnir/` prefix); `pyproject.toml` is repo-root. The `E` literal already mixes `.gleipnir/**` paths with repo-root `opencode.jsonc`/`**/opencode.json`, so adding repo-root files is consistent with the existing list shape.

---

## Link (validated before building)

- **CURRENT section text** read fresh this session: `stage-role-map.md` lines 63-167 (167 total). Exact strings for the edits captured (see Assemble diff blocks).
- **`.gitignore`** exists (19 lines): confirms `*.key`/`*.secret` ignored (lines 13-14), `*.digest` NOT ignored, and comment "policy + digest manifests are versioned" (line 12). Note 3's G-3-bypass claim is accurate.
- **`.envrc`** exists (8 lines): `export OPENCODE_CONFIG_DIR=.gleipnir` (line 8), no shebang, no `+x` guarantee. Note 3 claim accurate; confirms not disqualified by `X`.
- **`pyproject.toml`** exists (21 lines): `dependencies = []`, `requires-python >=3.11`, dev pins `pytest>=8,<9`/`pytest-cov>=5,<6`, cites `decisions/runtime-and-deps.md`. Note 3 claim accurate.
- **`decisions/runtime-and-deps.md`** exists (103 lines): confirms stdlib-only enforcement-core constraint that makes `pyproject.toml` dependency ranges enforcement-adjacent.
- **`keys/README.md`** confirms digest manifests are versioned as the integrity audit trail — reinforcing the `.gitignore`/`*.digest` bypass reasoning.
- No tools/connections beyond read+write-plan needed; this is a prose amendment.

---

## Assemble (intended build order → ready-to-apply diff text)

The operator applies these edits to `.gleipnir/stage-role-map.md`. Each block shows the exact CURRENT text and its replacement. Apply in order.

### Edit A — Note 3: extend the `E` set (Axis 2(a), current lines 95-100)

**BEFORE (current lines 95-100):**
```
- **(a) path rule:** any path in `P` is under the enforcement-path set `E` =
  `.gleipnir/agents/**`, `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`,
  `.gleipnir/policy/**`, `.gleipnir/keys/**`, `.gleipnir/stage-role-map.md`
  itself, or the root opencode config `opencode.jsonc` / `**/opencode.json`
  (it loads this map via `instructions`, gates the MCP brokers via `enabled`,
  and sets `default_agent`); **or**
```

**AFTER:**
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

### Edit B — Note 1: remove the correspondence hedge, tighten to always-same-file (current lines 155-160)

**BEFORE (current lines 155-160):**
```
**Correspondence rule:** the cited artifact must actually test the form it
claims to. The pattern/target in `evidence` must be the **same over-broad form
named in `over_broad_form_checked`** (and, where applicable, the same file as
`grant`) — grepping for an unrelated pattern is reproducible but proves nothing
and MUST be rejected. (E.g. a `lessons/**`-absent claim requires `evidence` that
greps for `lessons/**` specifically, not some other string.)
```

**AFTER:**
```
**Correspondence rule:** the cited artifact must actually test the form it
claims to, in the right file. The pattern/target in `evidence` MUST be the
**same over-broad form named in `over_broad_form_checked`**, AND the file the
evidence targets MUST be the **same file named in `grant`**. (There is no
"where applicable" exception: every grant names a specific target file, so
same-file matching always applies — a grant with no target file does not
occur.) Grepping for an unrelated pattern, or grepping the right pattern in the
wrong file, is reproducible but proves nothing and MUST be rejected. (E.g. a
`lessons/**`-absent claim requires `evidence` that greps for `lessons/**`
specifically, in the file the grant applies to, not some other string or file.)
```

### Edit C — Note 2: add the post-change-state requirement (insert after the correspondence rule, before the summary paragraph — i.e. between current line 160 and line 162)

**INSERT (new paragraph, placed after Edit B's block and before the `An enforcement-bearing prose/config plan may not report SUCCESS...` paragraph):**
```

**Post-change-state rule:** the `evidence` MUST be captured against the
**applied / post-change state** of the target file — the state after the plan's
edit is applied — not a stale or pre-change copy. This applies to **all**
evidence forms: a `grep`/`diff` MUST be run against the post-apply file, a
digest MUST be computed over the post-apply bytes, and a byte-for-byte quote
MUST be of the applied line. (The quote form already implies this; this rule
makes it explicit for the grep/diff/digest forms, where a pattern match against
the wrong file *version* would otherwise satisfy the substance and
correspondence rules while proving nothing about what was actually applied.)
```

### Edit D — Note 1 (summary consistency): tighten criterion (iv) to match the detail rule (current lines 162-167)

**BEFORE (current lines 162-167):**
```
An enforcement-bearing prose/config plan may **not** report SUCCESS unless (i)
two distinct pass verdicts exist, (ii) the negative-check attestation is present
with all fields and `attested_by ≠ author`, (iii) every `evidence` field cites a
reproducible artifact, not a narrative, and (iv) each `evidence` artifact tests
the specific form named in that row's `over_broad_form_checked` (not an unrelated
pattern).
```

**AFTER:**
```
An enforcement-bearing prose/config plan may **not** report SUCCESS unless (i)
two distinct pass verdicts exist, (ii) the negative-check attestation is present
with all fields and `attested_by ≠ author`, (iii) every `evidence` field cites a
reproducible artifact, not a narrative, (iv) each `evidence` artifact tests the
specific form named in that row's `over_broad_form_checked`, in the same file
named in that row's `grant` (not an unrelated pattern and not the wrong file),
and (v) every `evidence` artifact was captured against the applied / post-change
state of the target file.
```

---

## Stress-test (acceptance checks)

Applied to `stage-role-map.md` after the operator applies Edits A-D:

1. **Note 1 consistency:** `grep -n "where applicable" .gleipnir/stage-role-map.md` returns **zero** matches within the track section. The correspondence detail rule and summary criterion (iv) both assert same-file matching (grep both mention "same file"/"same file named in ... `grant`").
2. **Note 1 tightness:** the correspondence rule states same-file matching **always** applies and explicitly rejects "right pattern, wrong file."
3. **Note 2 presence + coverage:** a "Post-change-state rule" paragraph exists and names all four forms (grep, diff, digest, quote); summary criterion (v) exists and references post-change state.
4. **Note 3 enumeration:** the `E` literal contains `.gitignore`, `.envrc`, and `pyproject.toml`; each has a one-clause rationale; `.gitignore` is stated always-hardened; the "explicit enumeration not fuzzy predicate" justification is present.
5. **Mechanical check:** none of the four edits introduces a term requiring judgment. Verify each is decidable by exact-path match (Edit A), string/path equality (Edit B/D), or file-state-of-record (Edit C) — no "if enforcement-adjacent" style predicate remains.
6. **Structure preserved:** Axis 1, Axis 2(a)/(b), light path, hardened path, two-rubric non-fusion, and the attestation schema fields are all still present and unmodified except by the additive tightening above.
7. **Line-count sanity:** the section grew (additive) and no BEFORE block content was deleted except the removed hedge clause and the reworded criterion (iv).

**All three notes stay mechanical** — no note required introducing a judgment call. (Explicitly checked per constraint: Note 1 = path/string equality; Note 2 = file-state-of-record + form enumeration; Note 3 = exact-path enumeration. None uses a fuzzy predicate.)

---

## Execution Workflow (HARDENED path — dogfood of the track's own rule)

This plan touches `stage-role-map.md` ∈ `E`, so it MUST run the hardened path. The operator/orchestrator sequences:

1. **plan** (this file) — done.
2. **spec-review — TWO SEPARATE rubrics** by `quality-reviewer` (they do NOT fuse):
   - **(a) Spec-conformance** (rubric = this plan + the notes): `SPEC-CONFORM: PASS/FAIL`. Does each edit resolve its note exactly as the Decisions table states?
   - **(b) Blast-radius / false-success** (rubric = *how could this be wrongly green?*): adversarial pass hunting the over-broad form. Specifically check: does Edit A's `E` extension accidentally widen routing beyond the three named files (e.g. a glob that catches unintended paths)? Does Edit B's hedge-removal accidentally forbid a legitimate case? A single fused "looks fine" verdict is a non-conformance.
3. **Negative-check attestation** by `quality-reviewer` (`attested_by ≠ author`), one row per enforcement change. At minimum:
   - **Row — `E` extension (Edit A):** grant = "add `.gitignore`, `.envrc`, `pyproject.toml` to `E` as exact-path literals in `stage-role-map.md`"; intended narrowest scope = those three exact repo-root paths; over_broad_form_checked = "a glob (e.g. `*.toml`, `.*rc`, or `.gitignore*`) that would catch files beyond the three named ones"; evidence = literal grep of the applied section showing the three appear as exact strings and NO glob/wildcard form is present; negative result = "no wildcard/glob form of these three paths is present"; captured against the **post-apply** `stage-role-map.md`.
   - **Row — correspondence tightening (Edit B/D):** grant = "require same-file matching always"; over_broad_form_checked = "residual `where applicable` softness"; evidence = `grep -n "where applicable"` over the post-apply section returning zero matches (correspondence rule: the grep pattern `where applicable` is the exact form named, run in the exact file amended).
   - Each `evidence` field: concrete reproducible artifact (command+output), captured against the applied/post-change `stage-role-map.md` (per the very rule this plan adds).
4. **test / code / git / gate:** carry the attested **"N/A — no executable artifact"** transition (prose/policy amendment; the `git` stage is the operator's apply of the Tier-3 file, since no roster agent may write `stage-role-map.md`).
5. **SUCCESS gate:** may report SUCCESS only if (i) two distinct pass verdicts exist, (ii) attestation present with all fields and `attested_by ≠ author`, (iii) evidence reproducible not narrative, (iv) evidence tests the named form in the named file, (v) evidence captured post-change — i.e. the exact five-clause gate this plan installs.

**Operator apply:** because `stage-role-map.md` is Tier-3, the operator applies Edits A-D by hand (or via an operator-run tool); no roster agent — including this planner — writes the file.
