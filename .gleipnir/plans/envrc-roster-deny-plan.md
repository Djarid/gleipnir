# Plan: Roster-wide `.env*` opencode-permission-layer `read`+`edit` deny (narrows O-3(b))

_Author: `gleipnir-plan`. Tier-0 artifact; disposable; NOT authoritative.
Planned FROM the CONVERGED brief `.gleipnir/plans/envrc-roster-deny-brainstorm.md`
(STATUS: CONVERGED). F1–F4 are settled inputs and are NOT re-litigated here.
This plan bounds the implementation; it does not decide material tradeoffs._

**Framing lock (governs every word below).** The change is an
**opencode-permission-layer** control: it denies the LLM's `read`/`edit`
**tool** call for `.env*`-matching paths, refused by opencode's own permission
layer before the tool executes. It is **NOT** a file-permission (chmod/chown) /
OS-level control. The `gleipnir-approval` signer MCP subprocess and every roster
agent's tool-invocation processes run under **one shared OS uid** today; nothing
at the OS layer separates "signer" from "agent." This deny closes only the
**opencode-tool-dispatch path**. Genuine OS-level isolation (signer under a
distinct uid) is a **named, deferred, out-of-scope follow-on**. No sentence in
this plan may soften this back toward implying file-permission / OS-exclusive
protection.

---

## GOTCHA pre-flight (visible)

- **Goals checked** (`../goals/manifest.md`): `plan-format.md` (artifact format)
  and `methodology.md` (ATLAS/GOTCHA ahead of planning) apply. Followed.
- **Order:** plan-before-code. This plan writes only `.gleipnir/plans/**`; the
  Tier-3 edits it specifies are applied by operator / build-mode / `tier3-writer`
  under a fresh token — never by any planning or coding agent.
- **Gaps named:** none blocking. One `[PLAN-STAGE JUDGMENT]` on the `.gitignore`
  question is surfaced below (resolved, with a reviewer flag). One
  verify-at-spec-review item (opencode glob semantics for `.env*`) is carried.
- **Case routing (Design Principles):** this plan's touched-path set `P` is
  `.gleipnir/agents/*.md` (10 files) + `.gleipnir/decisions/tier3-signed-approval.md`
  (prose amendment). `P ∩ X = ∅` (no `src/**`, no `tests/**`, no executable
  artifact) → **case (iii) prose/config-only** → Design Intent only, SOLID/DRY/SRP
  attested N/A. See Design Principles section. The `.gitignore` question resolves
  to **not-in-scope-of-this-plan** (see Decision 6), so `P` gains no
  `.gitignore` entry and case (iii) holds.

---

## Decisions (index)

Brief-converged rows (F1–F4) are cited to the brief and NOT re-decided.
`[PLAN-STAGE JUDGMENT]` rows are this plan's own bounded mechanical resolutions.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Deny glob scope | `.env*` glob | `.envrc`-exact | **Brief F1 CONVERGED** (operator, direct conversation). Brief §"Selected Approach — F1". |
| 2 | Which capabilities denied | **both** `read` AND `edit` (and `write` where a `write` map exists) | read-only; edit-only | **Brief F1 CONVERGED**. Brief §"F1 → `.env*` glob; deny BOTH read and edit". `write` addendum is a [PLAN-STAGE JUDGMENT], row 8. |
| 3 | Which agents | all 10 roster agents, uniformly | only-reachable subset | **Brief F2 CONVERGED**. Brief §"F2 → all 10 roster agents, uniformly". |
| 4 | Which layer | per-agent frontmatter only, now | `boundary.py`/OS layer; both | **Brief F3 CONVERGED**. OS-layer + signer-uid separation explicitly DEFERRED, named follow-ons. Brief §"F3". |
| 5 | Honesty-ledger framing | "opencode-permission-layer enforced," explicitly NOT file-permission / NOT OS-exclusive | any OS/file-permission-grade claim | **Brief F4 CONVERGED**. Brief §"F4" + §"Material correction". |
| 6 | `.gitignore` `.env*` widening | **[PLAN-STAGE JUDGMENT]: OUT OF SCOPE of this plan; flagged for spec-review to ratify or split.** Do NOT widen `.gitignore` in this change. | widen `.gitignore` from `.envrc` to `.env*` now | Different layer (version-control tracking) from the converged concern (opencode tool dispatch). Brief §"precise gap" notes `.gitignore` has no `.env*` glob today and this is a *separate concern*. Widening `.gitignore` would ALSO route the plan into the hardened path via Axis 2(a) (`.gitignore` is always-hardened) — a distinct enforcement surface. Flagged as a genuinely-separable follow-on; NOT bundled. See Trace §Edge cases. |
| 7 | `read` scalar→map rewrite idiom | rewrite scalar `read: allow` → `read: { "*": allow, ".env*": deny }`, mirroring `git-ops`'s existing `read:` MAP shape; last-match-wins puts `.env*: deny` AFTER `"*": allow` | leave scalar (impossible — a scalar cannot carry a per-glob deny) | **[PLAN-STAGE JUDGMENT]** per brief Open-Questions §placement. Confirmed against `git-ops.md:20–22` which already uses a `read:` map. |
| 8 | Also deny `write` where a `write` map exists | add `.env*: deny` to `permission.write` in the 2 agents (`tier3-writer`, `session-scribe`) that carry a separate `write` map, AND rewrite `write: deny` scalar→map for the 4 agents (`quality-reviewer`, `git-ops`, `project-mgr`, `notify`) that have a scalar `write: deny` | `edit`-only | **[PLAN-STAGE JUDGMENT]:** opencode's `edit` and `write` are distinct permission keys; F1's intent ("no agent may write `.env*`") is only fully honoured if BOTH are denied wherever a `write` grant is expressible. `edit: deny`/`write: deny` scalars already block it, but for uniform-auditability (F2's rationale) and to prevent a future scalar→`"*": allow` flip silently reopening it, every agent's `write` surface gets the explicit `.env*: deny` when it has a `write` map, and scalar `write: deny` is left as-is where no map is warranted (see Trace). **Surfaced as this plan's judgment, not a re-decide of F1.** |
| 9 | Attestation granularity | **TWO rows split by risk tier** (spec-review round-2 ruling): **(a)** ONE consolidated row for the **8 uniform-risk files** (every file EXCEPT `gleipnir-code`'s edit map and `git-ops`'s read map) — `read`+`edit`(+`write`) grants, grep-based per-file evidence (8-line evidence table), since none carries a `"*": allow` contamination risk; **(b)** ONE SEPARATE dedicated row for the **2 `"*": allow` files** (`gleipnir-code` edit map, `git-ops` read map) whose evidence field is explicitly the **RUNTIME-PROBE output** (AC-10/AC-11), NOT static grep | one consolidated row for all 10; one full row per file | **[PLAN-STAGE JUDGMENT] + spec-review round-2:** 8 of the 10 files share a genuinely uniform, low-risk profile (no `"*": allow`, so no ordering-instability exposure) → grep evidence satisfies substance+correspondence+post-change-state for them, consolidated. But the 2 files with `"*": allow` carry the distinct, higher-severity ordering-instability risk (the regression class in Defect 1/2 that static grep cannot detect); per the correspondence rule their evidence MUST be the live runtime-probe outcome, not a grep of YAML order. Splitting into (a)+(b) matches evidence type to risk tier. At plan-stage, row (b) describes the REQUIRED evidence shape (the probe outcomes); the actual observed outcome is filled in at quality-stage post-probe, same convention as every attestation row in this repo. |
| 10 | Decision-record amendment shape | AMEND (append, do not replace) `decisions/tier3-signed-approval.md`'s O-3(b)/supersession section (lines 201–214) | new decision file; replace the section | **Brief closing note** ("in the converged scope") + delegation requirement. It is a Tier-3 write, out of THIS plan's write-scope; specified as an instruction for the operator/`tier3-writer` who applies it. See §"Decision-record amendment instruction". |

---

## Architect

**Problem (one sentence).** The approval-listener's key-isolation property rests
on `.envrc`/`.env*` being unreachable via the agent tool surface, but no
dedicated deny exists today — so a roster agent's `read`/`edit` tool call for
`.env*` is currently served by opencode's permission layer, leaving the signing
key's source reachable through opencode's own tool dispatch (O-3(b), the honest
residual gap named in `decisions/tier3-signed-approval.md:201–214`).

**User.** The operator (who authors `.envrc` and owns the signing key) and the
framework's integrity posture; secondarily every future agent added to the
roster, which must inherit the deny.

**What this change IS (framing-locked).** A per-agent frontmatter
`permission.read` + `permission.edit` (+ `permission.write` where a write map
exists) glob deny of `.env*`, applied uniformly to all 10 roster agents. It is
enforced by **opencode's permission layer at tool-call time, in BOTH caged and
uncaged postures** — an **opencode-application-level capability gate**, NOT a
file-permission (chmod/chown) or OS-level control. Because the `gleipnir-approval`
signer MCP and every agent's tool-invocation processes share **one OS uid**
today, no OS mechanism distinguishes signer from agent; this deny closes the
**opencode-tool-dispatch path only**.

**Measurable success criteria (must NOT overclaim).**

1. For **every one of the 10 roster agents**, a `read`-tool call and an
   `edit`-tool call targeting a `.env*`-matching path (e.g. `.envrc`, `.env`,
   `.env.local`, `.env.production`) is **refused by opencode's permission
   layer** before it executes. (NOT: "the key is protected from the agent" as an
   absolute — it is protected *only against the opencode `read`/`edit` tool
   path*.)
2. The deny is present in **all 10** `.gleipnir/agents/*.md` frontmatters, in
   the `permission.read` and `permission.edit` maps (and `permission.write`
   where such a map exists), verifiable by grep.
3. No agent's *existing* legitimate grant is broken: the `.env*: deny` sits at
   the correct last-match-wins position and does not shadow or get shadowed by
   any pre-existing allow (verified per file — see Trace edge cases).
4. The eventual `decisions/tier3-signed-approval.md` amendment records O-3(b) as
   **narrowed to "opencode-permission-layer enforced," explicitly NOT
   file-permission / NOT OS-exclusive**, stating the shared-uid residual plainly
   and naming the signer-uid-separation follow-on. (An amendment that overclaims
   OS/file-permission closure is a FAIL.)
5. **Explicitly NOT claimed:** protection against a future `bash`/`exec`
   capability, a compromised MCP, a compromised opencode, or any OS-level access
   path. Those remain the S-2 / signer-uid-separation seams.

**Constraints (grounded).**

- **Tier-3 enforcement-bearing → FULL hardened 8-stage pipeline.** `P` touches
  `.gleipnir/agents/**` (enforcement-path set `E`, `stage-role-map.md` Axis 2(a))
  and adds `permission`-block capability lines (Axis 2(b) content rule). NOT
  light-track eligible. `quality` must run the dual **SPEC-CONFORM + BLAST-RADIUS**
  passes as two distinct verdicts, plus the negative-check attestation
  (`attested_by ≠ author`) with reproducible, correspondence-correct,
  post-change-state evidence.
- **No in-framework agent may write Tier-3.** All 10 frontmatter edits and the
  decision-record amendment are applied by **operator / build-mode**, or by the
  signature-gated `tier3-writer` behind a fresh content-bound token. `gleipnir-code`
  is NOT used (no `src/` change under the converged frontmatter-only choice).
- **Two grammars exist in this repo (L-C12/L-C12b).** (a) The
  `permission.read`/`permission.edit`/`permission.write` file-path grammar
  (allow/deny, scalar or map) — **this is where the `.env*` deny goes.** (b) The
  top-level `tools:` boolean namespace grammar (`"gleipnir-git_*": false` etc.)
  — governs **MCP broker namespaces only; the `.env*` deny NEVER goes here.**
  Confirmed per-file: all 10 use grammar (a) for `read`/`edit`; the variation is
  scalar-vs-map, resolved in Trace.
- **Framing constraint (F4/correction).** Every artifact this plan produces or
  instructs — plan text, attestation wording, decision-record amendment — must
  label the control opencode-permission-layer, not file-permission / OS-level.
- **opencode glob-semantics verify item (carried from brief F4 bias-check).**
  This plan ASSUMES opencode's permission-glob syntax matches `.env*` against
  `.env`, `.envrc`, `.env.local`, etc. as a single-segment prefix glob.
  **Verify at spec-review** (Link §). If opencode requires a different pattern
  (e.g. `.env**` or a brace form) to catch `.envrc`, the exact pattern string is
  corrected there; the *intent* (match the `.env*` class at repo root) is fixed.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Writer | Change |
|---|---|---|---|
| 10 roster agent frontmatters | `.gleipnir/agents/*.md` | operator / build-mode / `tier3-writer` (Tier-3) | add `.env*: deny` to `permission.read`, `permission.edit`, and `permission.write`-where-a-map-exists |
| O-3(b) honesty-ledger amendment | `.gleipnir/decisions/tier3-signed-approval.md` (append at the END of the file — after its current last line, verified line 215; NOT after line 214) | operator / build-mode / `tier3-writer` (Tier-3) | APPEND the narrowed framing at end-of-file; do NOT replace lines 201–214 and do NOT insert before the file's final line |
| Negative-check attestation | recorded at `quality` (in the plan's execution record / decision trail) | `quality-reviewer` (never author) | TWO rows (Decision 9): (a) consolidated grep-evidence row for the 8 uniform-risk files; (b) dedicated runtime-probe-evidence row for the 2 `"*": allow` files |

This plan file itself: `.gleipnir/plans/envrc-roster-deny-plan.md` (Tier-0).

### The exact per-file edit for all 10 agents

Glob string to insert everywhere: **`".env*": deny`** (verify-at-spec-review the
opencode pattern; intent = the repo-root `.env*` class). Placement rule:
**last-match-wins → the deny must come AFTER any `"*": allow`** in that map and
must NOT be followed by any allow that re-matches `.env*`.

| # | Agent | Grammar for read/edit | READ edit | EDIT edit | WRITE edit |
|---|---|---|---|---|---|
| 1 | `orchestrator` | read **unspecified**; edit scalar `deny` | **ADD a `read:` map**: `read: { "*": allow, ".env*": deny }` (read was default-allow; F2-uniform requires explicit) | leave `edit: deny` scalar — a scalar `deny` already blocks `.env*` edits and no map is otherwise needed; **[JUDGMENT] optional uniformity variant:** may rewrite to `edit: { "*": deny }` but adds nothing — recommend leave scalar | no `write` key present; leave as-is (edit-deny covers it) |
| 2 | `gleipnir-brainstorm` | read scalar `allow`; edit MAP (`"*": deny`, `.gleipnir/plans/**: allow`) | scalar→map: `read: { "*": allow, ".env*": deny }` | ADD `".env*": deny` to the existing edit map (after `"*": deny`; harmless—already denied, but explicit for uniform audit) | no `write` map; n/a |
| 3 | `gleipnir-plan` | read scalar `allow`; edit MAP (`"*": deny`, `.gleipnir/plans/**: allow`) | scalar→map: `read: { "*": allow, ".env*": deny }` | ADD `".env*": deny` to the edit map | no `write` map; n/a |
| 4 | `gleipnir-code` | read scalar `allow`; edit MAP (`"*": allow` + denies + **named-file allows** at the end, `.env*` NOT among them) | scalar→map: `read: { "*": allow, ".env*": deny }` | ADD `".env*": deny` to the edit map. **CRITICAL ordering (edge case E1 below):** place it after `"*": allow` and NOT after the trailing named-file allows in a way that a later allow re-matches — the named allows are `src/gleipnir/preflight/*.py` and `.gleipnir/plugins/advance-hook.ts` (none match `.env*`), so `".env*": deny` may go anywhere after `"*": allow`; recommend immediately after the other path denies, before the named allows, for readability | no `write` map; edit map covers it |
| 5 | `quality-reviewer` | read scalar `allow`; edit scalar `deny`; write scalar `deny` | scalar→map: `read: { "*": allow, ".env*": deny }` | leave `edit: deny` scalar (already blocks) OR uniformity variant `edit: { "*": deny }` — recommend leave scalar | leave `write: deny` scalar (already blocks) — recommend leave scalar |
| 6 | `git-ops` | read **MAP** (`"*": allow`, `.git/**: deny`); edit scalar `deny`; write scalar `deny` | ADD `".env*": deny` to the existing read map (after `"*": allow`; sits alongside `.git/**: deny`) | leave `edit: deny` scalar — recommend leave | leave `write: deny` scalar — recommend leave |
| 7 | `project-mgr` | read scalar `allow`; edit scalar `deny`; write scalar `deny` | scalar→map: `read: { "*": allow, ".env*": deny }` | leave `edit: deny` scalar — recommend leave | leave `write: deny` scalar — recommend leave |
| 8 | `notify` | read scalar `allow`; edit scalar `deny`; write scalar `deny` | scalar→map: `read: { "*": allow, ".env*": deny }` | leave `edit: deny` scalar — recommend leave | leave `write: deny` scalar — recommend leave |
| 9 | `tier3-writer` | read scalar `allow`; edit MAP (`"*": deny` + Tier-3 allows); write MAP (`"*": deny` + Tier-3 allows) | scalar→map: `read: { "*": allow, ".env*": deny }` | ADD `".env*": deny` to the edit map (after `"*": deny`; Tier-3 allows are `.gleipnir/**` paths + `stage-role-map.md`, none match `.env*` at repo root — no collision) | ADD `".env*": deny` to the write map (same reasoning) |
| 10 | `session-scribe` | read scalar `allow`; edit MAP (`"*": deny` + Tier-0/one Tier-2 allow); write MAP (same) | scalar→map: `read: { "*": allow, ".env*": deny }` | ADD `".env*": deny` to the edit map (allows are `.gleipnir/plans/**`, `.gleipnir/var/tmp/**`, one lessons file — none match `.env*`) | ADD `".env*": deny` to the write map (same) |

**Grammar summary confirmed per file:** all 10 use grammar (a)
(`permission.read`/`edit`/`write`) for file access; NONE route `.env*` through
the top-level `tools:` boolean grammar (b). Scalar→map rewrites: `read` on 8
agents (all except `git-ops` which already has a read map, and `orchestrator`
which needs a NEW map since read was unspecified — counted as an add, not a
rewrite). `edit` map-adds on 5 (`brainstorm`, `plan`, `code`, `tier3-writer`,
`session-scribe`); the other 5 keep `edit: deny` scalar. `write` map-adds on 2
(`tier3-writer`, `session-scribe`); 4 keep `write: deny` scalar; 4 have no
`write` key (edit-deny covers).

### Integrations map

- **opencode permission engine** — consumes the frontmatter `permission` maps at
  tool-call time; the sole enforcer of this control. (Verify glob semantics —
  Link.)
- **`decisions/tier3-signed-approval.md`** — the durable home of the O-3(b)
  ledger; receives the narrowing amendment. Cross-references the S-2 mount and
  the (new) signer-uid-separation follow-on.
- **`stage-role-map.md` Axis 2** — routes this plan to the hardened path
  (`.gleipnir/agents/**` ∈ `E`); no code change to it.
- **`.gitignore`** — intentionally NOT touched (Decision 6). A future
  `.gitignore` `.env*` widen is a separate, hardened-path change (`.gitignore`
  is always-hardened).

### Edge cases

- **E1 — `gleipnir-code` edit-map ordering (last-match-wins).** `gleipnir-code`
  is the only agent whose edit map starts `"*": allow`. The `".env*": deny` MUST
  come after it. Its trailing named allows (`src/gleipnir/preflight/*.py`,
  `.gleipnir/plugins/advance-hook.ts`) do not match `.env*`, so no re-allow
  shadows the deny. **Reviewer must confirm no named allow matches `.env*`.**
- **E2 — `orchestrator` unspecified read.** Its `read` is currently default
  (opencode default is allow). F2-uniformity REQUIRES making it explicit — a NEW
  `read:` map, not a rewrite. Without this, the "every agent denies `.env*`"
  audit claim is false for `orchestrator`.
- **E3 — scalar-deny agents (`quality-reviewer`, `project-mgr`, `notify` edit;
  `git-ops` edit/write).** A scalar `edit: deny` already denies `.env*` edits.
  Making it an explicit map adds no capability change and risks a transcription
  slip; recommend leaving scalar and asserting in the attestation that the
  scalar deny covers `.env*`. **This is a [PLAN-STAGE JUDGMENT] the reviewer
  should confirm:** is "scalar `deny` counts as denying `.env*`" acceptable for
  the uniform-audit claim, or must every agent show a literal `.env*` string?
  Flagged for spec-review — if the reviewer requires the literal string
  everywhere, rewrite the 5 edit scalars + 4 write scalars to `{ "*": deny }`
  form. **Named, not silently resolved.**
- **E4 — `.env.example`/`.env.sample` carve-out (brief Open-Question).** No such
  readable example file exists in the repo today (verified: `.gitignore` lists
  only `.envrc` and `agent-identity.env`). Decision: **no carve-out pre-authored**
  — the `.env*` deny stands unqualified; if a readable example is ever needed, an
  exact-path `allow` after the deny (last-match-wins) is the documented, cheap
  escape, mirroring `gleipnir-code`'s named-file allows. Recorded so the reviewer
  knows the omission is deliberate.
- **E5 — `.gitignore` `.env*` widening.** See Decision 6: OUT OF SCOPE, flagged
  for spec-review. `.gitignore` currently ignores `.envrc` by exact name (line
  21) + `agent-identity.env` (line 17); there is no `.env*` glob. Widening it is
  a *version-control-tracking* concern (a new `.env.local` would be
  git-trackable until the glob widens), distinct from the *opencode-tool-dispatch*
  concern this plan closes. Bundling it would (a) mix two layers the brief keeps
  separate and (b) add an always-hardened path to `P` for a different reason.
  **Resolution: do not touch `.gitignore` in this change; recommend a separate
  follow-on to widen `.gitignore` to `.env*` for tracking-hygiene parity. Flagged
  as `[PLAN-STAGE JUDGMENT]` for the reviewer to ratify the split or fold it in.**

---

## Link (validated before building)

1. **All 10 agent frontmatters read in full** — the read/edit/write grammar and
   current values per file are confirmed (Trace table), not assumed. Two grammars
   confirmed; `.env*` belongs only in grammar (a).
2. **`git-ops.md:20–22`** confirmed to already use a `read:` MAP — the idiom the
   scalar→map rewrites mirror (Decision 7 grounded, not invented).
3. **`.gitignore` read** — confirmed line 21 = `.envrc` exact, line 17 =
   `agent-identity.env`; no `.env*` glob (Decision 6 / E5 grounded).
4. **`decisions/tier3-signed-approval.md:201–214`** read — the exact O-3(b)
   supersession text to AMEND (not replace) is confirmed present.
5. **`stage-role-map.md` Axis 2** — confirmed `.gleipnir/agents/**` ∈ `E` →
   hardened path (routing grounded).
6. **TO VERIFY AT SPEC-REVIEW (not yet validated):** opencode's permission-glob
   semantics — that `".env*"` matches `.envrc`, `.env`, `.env.local` as a single
   prefix glob. This is F4's load-bearing claim (brief bias-check flagged it as
   verify-at-plan-or-spec-review). The plan CANNOT self-validate opencode
   internals; the reviewer confirms the pattern string against opencode's
   permission docs before the edits apply. If the pattern differs, correct the
   literal string, keep the intent.

---

## Assemble (intended build order)

1. **spec-review** (`quality-reviewer`): confirm this plan against the brief and
   spec — including (a) the framing is opencode-permission-layer throughout, not
   overclaimed; (b) resolve the three flagged `[PLAN-STAGE JUDGMENT]`s
   (E3 scalar-vs-explicit, E5 `.gitignore` split, Decision 9 attestation
   granularity); (c) **verify opencode `.env*` glob semantics** (Link 6). Emit
   `SPEC-CONFORM: PASS/FAIL` and the intent-quality sub-check on the Design Intent.
2. **test:** N/A — no executable artifact. Attested "N/A — no executable
   artifact" transition.
3. **code:** N/A — no `src/` change (frontmatter-only, Tier-3). Attested N/A.
   The frontmatter edits are NOT a `gleipnir-code` task.
4. **Apply the 10 frontmatter edits** — operator / build-mode / `tier3-writer`
   under a fresh content-bound token (one file at a time; Tier-3). Follow the
   Trace per-file table exactly.
4a. **REQUIRED RUNTIME PROBES (post-application; AC-10 + AC-11).** After the
    edits are live, `gleipnir-code` performs two live tool-call probes and
    records the observed opencode-permission-layer outcome.
    **Probe target — actor / mechanism / timing (fixture resolution).** The
    probes target the **real, already-git-ignored `.envrc`** at repo root
    (confirmed to exist and to be ignored via `.gitignore:21`; it matches the
    `.env*` class), so **the default probe requires NO fixture to be created or
    removed at all** — `gleipnir-code` merely *attempts* `edit`/`write` calls on
    the existing `.envrc` and records REFUSED/ALLOWED. A synthetic
    `.env*`-matching fixture is a *fallback only* if the reviewer judges probing
    the live `.envrc` unsuitable, and it CANNOT be handled by `gleipnir-code`:
    per its current frontmatter (`.gleipnir/agents/gleipnir-code.md`),
    `gleipnir-code` holds **no delete-capable tool whatsoever** — `bash` is
    `"*": deny` with only `bin/gleipnir-sandbox test|lint` allowed (`rm`, `sh*`,
    `bash*`, `env*` all denied), `task: deny`, `webfetch: deny`; its only
    file-mutation lever is `edit`/`write`, which can overwrite content but
    **cannot remove a file from the tree**, and its `edit` map denies
    `.gleipnir/**`, so it cannot even write into the Tier-0 `.gleipnir/var/tmp/`
    disposable path. Therefore a synthetic fixture, IF used, is created **and
    removed by the operator / build-mode as a build act** (NOT by
    `gleipnir-code`, which can neither delete it nor place it in a disposable
    location): the operator creates the fixture immediately before the probe and
    removes it immediately after `gleipnir-code` reports the outcome.
    **Timing gate (hard):** whichever path is used, the tracked tree MUST be
    clean of any probe fixture — i.e. removal complete, or (default path)
    confirmed that no fixture was ever created — **BEFORE Assemble step 6
    (`quality`) begins, and unconditionally before step 7 (`git`).** `quality`
    MUST NOT start while a synthetic fixture remains on disk, and `git` MUST NOT
    commit one. (Probing the real `.envrc` trivially satisfies this: it is
    git-ignored and never entered the tracked tree.)
    The two probes:
    - **Probe A (AC-10, `edit`):** attempt a real `edit` tool call on a
      `.env*` path; record REFUSED / ALLOWED. A live REFUSAL is the ONLY
      evidence closing Success Criterion 1; an ALLOW is a FAIL that blocks `git`.
    - **Probe B (AC-11, `write`):** attempt a real `write` tool call on a
      `.env*` path through `gleipnir-code`; record REFUSED / ALLOWED. If ALLOWED
      (write ungated by `edit: deny`), apply the AC-11 conditional `write`-deny
      addition to all 4 named agents, then re-run Probe B to confirm refusal.
    These are **not optional** — they resolve the two coverage questions
    (ordering-instability regression class; `write`-namespace ground truth)
    that static inspection cannot. The probe outcomes are the evidence for
    attestation **row (b)** — the 2 `"*": allow` files (Decision 9). This is a
    bounded, reversible probe:
    `gleipnir-code` here only *attempts* tool calls and reports; it does not
    apply Tier-3 edits (the AC-11 conditional `write` addition, if triggered, is
    applied by operator / build-mode / `tier3-writer`, same as steps 4/5).
5. **Apply the decision-record amendment** — operator / build-mode /
   `tier3-writer`; APPEND the narrowed framing at the END of the file (after
   its current last line; see §"Decision-record amendment instruction"); do NOT
   replace lines 201–214 and do NOT insert before the file's final line.
6. **quality** (`quality-reviewer`): run the TWO distinct passes against the
   APPLIED post-change state —
   - **Pass 1 SPEC-CONFORM:** every file matches the Trace table; the amendment
     carries the F4 framing without overclaim.
   - **Pass 2 BLAST-RADIUS / false-success:** adversarially seek an over-broad or
     shadowed grant (E1 ordering; a `.env*` deny accidentally widened to `**` or
     `.gleipnir/**`; a named allow re-matching `.env*`; the amendment implying
     OS/file-permission closure). Include the SOLID/DRY dimension → attested N/A
     (case iii).
   - Produce the **negative-check attestation** (Decision 9), split into TWO
     rows by risk tier. `attested_by ≠ author` for both.
     - **Row (a) — 8 uniform-risk files** (all except `gleipnir-code` edit map
       and `git-ops` read map): ONE consolidated intent row + an 8-line per-file
       grep-evidence table. Evidence reproducible (grep/diff on the post-change
       file), testing the named over-broad form, in the named file, against the
       applied state.
     - **Row (b) — 2 `"*": allow` files** (`gleipnir-code` edit map,
       `git-ops` read map): a dedicated row whose `evidence` field is the
       **RUNTIME-PROBE output** (AC-10 `edit` refusal + AC-11 `write` ground-
       truth), quoting the actual observed outcome — NOT a static grep — because
       the correspondence rule requires evidence that tests the ordering-
       instability risk these two files carry, which only a live tool-call
       refusal demonstrates.
7. **git** (`git-ops`): commit the applied changes.
8. **gate** (`orchestrator`): read attestation; emit pipeline state. Any
   quality-found divergence blocks `git` until operator-acknowledged.

---

## Stress-test (acceptance checks)

Concrete, checkable — not "it works":

1. **AC-1 (presence, read):** `grep -c '".env\*": deny'` in the `permission.read`
   map of each of the 10 agent files returns ≥1 for all 10. (`orchestrator` now
   has a `read:` map containing it.)
2. **AC-2 (presence, edit):** each of the 10 agents denies `.env*` edits — either
   an explicit `".env*": deny` in an `edit` map (5 agents) OR a scalar
   `edit: deny` that structurally denies it (5 agents). The attestation records
   which mechanism per file.
3. **AC-3 (presence, write):** the 2 agents with a `write` map
   (`tier3-writer`, `session-scribe`) carry `".env*": deny` in it; the 4 with
   scalar `write: deny` deny it structurally; the 4 with no `write` key are
   covered by `edit: deny`. Recorded per file.
4. **AC-4 (no shadowing / last-match-wins):** in `gleipnir-code`'s edit map and
   `git-ops`'s read map (the two maps with a `"*": allow`), no allow entry AFTER
   `".env*": deny` re-matches `.env*`. Verified by ordered inspection.
5. **AC-5 (grammar correctness):** the `.env*` deny appears ONLY in
   `permission.read`/`edit`/`write` — NEVER in a top-level `tools:` block — in
   all 10 files. (`grep` the `tools:` blocks: zero `.env` matches.)
6. **AC-6 (no overclaim in the amendment):** the appended
   `decisions/tier3-signed-approval.md` text states "opencode-permission-layer
   enforced," explicitly disclaims file-permission / OS-exclusive closure, states
   the shared-uid residual, and names the signer-uid-separation follow-on.
   Reject if any sentence claims the key is OS-protected or the operator has
   exclusive OS control.
7. **AC-7 (glob semantics verified):** spec-review has confirmed the opencode
   pattern string matches `.envrc`, `.env`, `.env.local` (Link 6); if a different
   literal was required, it is applied uniformly across all 10 files.
8. **AC-8 (attestation completeness):** the negative-check attestation exists as
   the TWO risk-tiered rows (Decision 9), each with `attested_by ≠ author`:
   **row (a)** — 8 uniform-risk files with reproducible per-file grep evidence,
   correspondence to the named over-broad form, post-change-state capture;
   **row (b)** — the 2 `"*": allow` files (`gleipnir-code` edit, `git-ops` read)
   whose evidence is the AC-10/AC-11 runtime-probe outcome (live refusal), not
   grep. Both rows honour the hardened-path substance/correspondence/post-change
   rules.
9. **AC-9 (scope containment):** `.gitignore` is UNCHANGED (Decision 6);
   `boundary.py`/`src/**` are UNCHANGED; no signer-uid work performed.
10. **AC-10 (RUNTIME PROBE — `edit` refusal; the ONLY evidence that closes
    Success Criterion 1).** Static YAML/grep inspection (AC-1..AC-5) cannot
    detect the failure class spec-review researched: opencode's docs claim
    last-match-wins evaluation, but the LIVE opencode issue tracker documents
    repeated, recent, unresolved regressions in EXACTLY this construction (a
    broad `"*": allow` plus a narrow deny), including one issue where an agent
    `.md` frontmatter permission pattern **silently never matches** with no
    warning emitted. Therefore, **after** the Tier-3 frontmatter edits are
    applied (Assemble step 4), `gleipnir-code` MUST attempt a real `edit`
    tool call targeting the **real, git-ignored `.envrc`** (default; no fixture
    to create or remove) — or, ONLY if the reviewer judges targeting `.envrc`
    directly unsuitable, a synthetic `.env*`-matching fixture file (e.g.
    `.env.probe-fixture`) that the **operator / build-mode creates before and
    removes after** the probe, since `gleipnir-code` holds no delete-capable
    tool and cannot reach a disposable location for it (see Assemble step 4a,
    "Probe target — actor / mechanism / timing"; any such fixture MUST be gone
    before `quality` and before `git`) — and the
    observed outcome MUST be recorded: did opencode's permission layer
    **actually refuse** the call before it executed? A recorded live REFUSAL
    is the only evidence that closes Success Criterion 1; a recorded ALLOW (or
    silent success) is a FAIL that blocks `git`. This is a **required**
    Assemble/Execution-Workflow step, not optional (see Assemble step 4a).
11. **AC-11 (RUNTIME PROBE — `write` tool ground-truth).** Spec-review found
    conflicting authoritative sources on whether opencode's `write` tool is
    governed by the `edit` permission key or is a **separate namespace**. The
    Trace table's "no write key; edit-deny covers it" assertion for the 4
    agents (`orchestrator`, `gleipnir-brainstorm`, `gleipnir-plan`,
    `gleipnir-code`) is therefore **unverified**. After the edits apply,
    `gleipnir-code` (the one of the 4 with a real file-modification surface)
    MUST attempt a real `write` tool call against the **real, git-ignored
    `.envrc`** (default; no fixture) — or an operator/build-mode-created-and-
    removed synthetic `.env*`-matching fixture if the reviewer deems `.envrc`
    unsuitable (`gleipnir-code` cannot create-or-remove one itself; see Assemble
    step 4a; any fixture gone before `quality`/`git`) — and record whether
    opencode's permission layer refuses it. **Conditional coverage rule (extends Decision 8):** IF the
    probe shows `write` is **ungated** by `edit: deny` for that agent (i.e. the
    `write` tool executes despite `edit: deny`), THEN all 4 of those agents
    (`orchestrator`, `gleipnir-brainstorm`, `gleipnir-plan`, `gleipnir-code`)
    require an explicit `write` deny added — for each, add a `permission.write`
    entry of the map form `write: { "*": allow, ".env*": deny }` (last-match-
    wins, deny after the allow), or the scalar-appropriate `write: { "*": deny }`
    if the agent should write nothing at all — matching each agent's existing
    posture (the 3 non-code agents write nothing operationally, so
    `write: { "*": deny }` for them; `gleipnir-code` writes `src/**`/`tests/**`,
    so `write: { "*": allow, ".env*": deny }` for it). IF the probe shows
    `write` **IS** gated by `edit: deny` (refused), the Trace assertion stands
    and no `write` addition is made to the 4. This is resolved **empirically at
    the probe**, not assumed.

---

## Execution Workflow (for the applying agent / operator)

- **Who applies:** operator / build-mode, or `tier3-writer` behind a fresh
  content-bound signed token (one file per token, `.gleipnir/agents/**` and
  `.gleipnir/decisions/**` are both in its allow-set). NO planning/coding agent
  applies these — they are Tier-3.
- **Per-file protocol:** open the agent file; locate the `permission:` block;
  apply the exact edit from the Trace per-file table; preserve all surrounding
  YAML and comments byte-for-byte; do NOT touch the top-level `tools:` block.
- **Ordering discipline:** for the two maps with `"*": allow`
  (`gleipnir-code` edit, `git-ops` read) place `".env*": deny` AFTER the `"*":
  allow` line (E1/AC-4).
- **Scalar-deny agents:** unless spec-review (E3) rules otherwise, LEAVE
  `edit: deny`/`write: deny` scalars as-is and record in the attestation that the
  scalar covers `.env*`.
- **After all 10:** apply the decision-record APPEND (next section). Then run
  `quality`'s two passes + attestation against the applied state, then commit.
- **If opencode's `.env*` glob semantics differ** (Link 6 / AC-7): apply the
  corrected literal uniformly to all 10; re-run AC-1..AC-5.

### Decision-record amendment instruction (Tier-3, out of this plan's write-scope)

The eventual amendment to `.gleipnir/decisions/tier3-signed-approval.md` MUST be
an **APPEND at the END of the file** — after the file's current last line
(verified at plan-stage to be line 215, `- The full opencode restart that makes
the hook + role live.`; re-confirm the actual last line before applying, as it
may have shifted). Do **NOT** append after line 214: line 215 is an orphaned
bullet that structurally belongs to the earlier list at lines 165–173 (under
"## Status: authored, not yet closed"), separated from its list by the entire
"## Supersession" section; inserting new text after line 214 would wedge the
amendment BETWEEN that residual bullet and its own list, worsening the document
structure. Append at end-of-file so the amendment follows all existing content
cleanly. Do NOT replace the existing O-3(b)/supersession text at lines 201–214.
It must carry the brief's corrected F4 language forward. Quote to carry
(verbatim intent from the brief's converged F4 / correction):

> **O-3(b) — narrowed (not closed).** The roster-wide `.env*` `read`+`edit` deny
> now lands as an **opencode-permission-layer** control: opencode refuses every
> roster agent's `read`/`edit` tool call for a `.env*` path, in both caged and
> uncaged postures. This is **explicitly NOT** file-permission (chmod/chown)
> enforced and **explicitly NOT** OS-exclusive: the `gleipnir-approval` signer
> MCP subprocess and every agent's tool-invocation processes run under **one
> shared OS uid** today, so no OS-level control separates "signer" from "agent."
> The deny closes only the opencode-tool-dispatch path; it does nothing against a
> future `bash`/`exec` capability, a compromised MCP, a compromised opencode, or
> any OS-level access path. Genuine OS-level isolation is the **deferred
> signer-uid-separation follow-on** (dedicated service account + `chown` +
> uid-switched MCP launch, e.g. `sudo -u signer …`) — the same shape as the S-2
> dedicated-agent-uid machinery, inverted — plus the S-2 mount. O-3(b) is
> therefore **narrowed to "opencode-permission-layer enforced," NOT resolved.**

The reviewer at `quality` (AC-6) rejects the amendment if any sentence softens
this toward file-permission / OS-exclusive closure.

---

## Design Principles (Gate 1 — case (iii): prose/config-only, `P ∩ X = ∅`)

**Case routing.** `P` = 10 `.gleipnir/agents/*.md` frontmatters + one
`.gleipnir/decisions/*.md` prose amendment. No path in `P` matches the Axis-1
disqualifier set `X` (`src/**`, `tests/**`, `bin/**`, Makefiles, CI YAML, shell,
shebang-config, etc.). These are declarative YAML frontmatter + markdown prose,
with **no class/function/module structure**. → **case (iii)**.

- **SOLID analysis:** **N/A — no executable artifact.** There is no
  class/function/interface to analyse for Single-Responsibility / Open-Closed /
  Liskov / Interface-Segregation / Dependency-Inversion.
- **DRY analysis:** **N/A — no executable artifact.** (Observation only, not a
  DRY finding: the `.env*: deny` line is intentionally repeated across 10 files;
  this repetition is the *point* — F2's uniform-roster auditability — not
  extractable duplication, and there is no shared config include mechanism for
  agent frontmatter.)
- **SRP check:** **N/A — no object/function structure.**
- **Design Intent (specific, falsifiable — the genuineness proxy):**

  > **Every roster agent's opencode `read`/`edit`(/`write`) tool call for a
  > `.env*`-matching path is refused by opencode's permission layer, uniformly
  > across all 10 agents, WITHOUT broadening any agent's deny beyond the `.env*`
  > class and WITHOUT this plan asserting the control is anything more than an
  > opencode-permission-layer gate (it is NOT file-permission / OS-level).**

  Falsifiable four ways: (1) if any of the 10 agents lacks the `.env*` read/edit
  deny → violated; (2) if any inserted deny is broader than `.env*` (e.g. a bare
  `**` or `.gleipnir/**` slipped in, or a named allow re-matches `.env*`) →
  violated (this is exactly the BLAST-RADIUS pass's target); (3) if the `.env*`
  deny is placed in the top-level `tools:` grammar instead of
  `permission.read`/`edit`/`write` → violated (wrong layer, non-functional); (4)
  if any plan/attestation/amendment sentence claims file-permission or
  OS-exclusive protection → violated (overclaim). A reviewer can point to a
  specific frontmatter line or amendment sentence that violates any of the four —
  it is not a generic "do it cleanly" aspiration.

---

## Material tradeoffs surfaced (for the orchestrator → operator; NOT resolved here)

Per my role, I do not bake material tradeoffs into the plan. F1–F4 are already
converged. The following are the ONLY items with any decision content beyond the
brief; I have named — not silently resolved — each, and flagged them for
spec-review:

1. **`.gitignore` `.env*` widening (E5 / Decision 6).** I resolved it as
   **OUT OF SCOPE of this plan** (a separable version-control-tracking follow-on,
   distinct from the opencode-tool-dispatch concern). This is a bounded
   plan-stage scoping call, not a re-decide of F1–F4 — but if the operator wants
   tracking-hygiene parity landed together, that is an operator call. **Named for
   the reviewer/operator to ratify the split or fold it in.**
2. **Scalar-deny vs explicit-`.env*` on the 5 edit + 4 write scalars (E3).**
   I recommend leaving scalar `deny` (it structurally denies `.env*` already) and
   recording that in the attestation, over rewriting to `{ "*": deny }`. This is
   a mechanical idiom choice, not a capability tradeoff — but it affects whether
   the "every agent shows a literal `.env*`" audit claim is literal or
   structural. **Flagged for spec-review to set the audit standard.**
3. **Also-deny-`write` (Decision 8).** I extended F1's read+edit intent to the
   `write` permission key wherever a `write` map exists, on the reasoning that
   opencode treats `edit` and `write` as distinct keys and F1's "no agent writes
   `.env*`" is only fully expressed by covering both. This is arguably a small
   scope addition beyond the brief's literal "read+edit." **I surface it as this
   plan's judgment rather than assuming it is inside F1** — if the operator reads
   F1 as strictly read+edit-only, drop the `write` map entries; the scalar
   `write: deny`s already cover those 4 agents regardless.

None of the three is a new *material* (hard-to-reverse, viable-alternatives)
design decision of the F1–F4 class — each is a one-line, two-way-door mechanical
choice — so I have planned them with a recommendation AND flagged them for the
spec-review gate rather than routing back to a full brainstorm. If the reviewer
or operator judges any to be material, route it to `gleipnir-brainstorm`.
