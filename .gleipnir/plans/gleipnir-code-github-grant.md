# Plan: apply the converged `.github/**` deny to `gleipnir-code`'s edit grant

**Status:** plan (session artifact, Tier-0, disposable). Plans the *mechanics*
of applying an already-converged Tier-3 policy change. The A/B/C tradeoff is
**closed** — the operator converged on **Option A** (deny `.github/**` outright)
via the orchestrator's `question` tool, recorded in
`plans/gleipnir-code-github-grant-control-proposal.md` `## Convergence`
(2026-08-20). This plan does **not** re-open it.

**Routing (computed, not judged):** `P = { .gleipnir/agents/gleipnir-code.md }`.
Axis-1: `.md`, not in disqualifier set `X` → track-eligible for the
prose/config-only track. Axis-2(a): `.gleipnir/agents/**` ∈ enforcement-path set
`E` → **hardened path** (two distinct `quality-reviewer` passes +
negative-check attestation), despite there being no executable artifact.

---

## 1. Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Which scope to deny (A/B/C) | **Option A** — `".github/**": deny` | B (`workflows/**` only); C (leave as-is) | **Operator-converged**, not decided here. Cite: `gleipnir-code-github-grant-control-proposal.md` `## Convergence` (2026-08-20). Matches Axis-1 `X` granularity + integrity>efficiency tie-breaker. |
| 2 | Placement/ordering of the new deny line | Between `.git/**` and `src/gleipnir/preflight/**` (dot-config denies grouped before the `src/` deny) | Alphabetical; append-to-end after `src/…preflight` | Matches the existing convention (framework-internal/dot-config denies first, source-tree deny last) AND matches the verbatim block in the converged proposal's `## Convergence`. Minor style call, resolved by matching in-file precedent. |
| 3 | Who applies the edit | **Operator** (build mode), or an agent explicitly instructed by the operator at that moment outside the fixed roster grants | Route to `gleipnir-code` (`code` stage) | No roster grant can write `.gleipnir/**` — the L-C27 gap. `gleipnir-code` self-authoring its own tightened grant is both self-referential and outside its grant. Per `decisions/operating-posture.md` (uncaged default), Tier-3 is operator-applied. |
| 4 | Optional prose comment in the agent body | **Out of scope for this plan** (operator's call, per proposal) | Mandate it | The converged proposal marks the prose note optional and not required for the grant to take effect. This plan applies the minimal one-line grant change; a body comment is a separate, optional operator edit. |

Full reasoning for each row is in the sections below; the table is an index, not
a substitute.

---

## 2. Architect

**Problem (one sentence):** Apply the operator-converged Option A —
insert `".github/**": deny` into `gleipnir-code`'s `edit` permission block in
`.gleipnir/agents/gleipnir-code.md` — correctly and verifiably, changing nothing
else.

**User:** The operator (applies the Tier-3 edit) and `quality-reviewer` (runs
the two hardened-path passes + authors the negative-check attestation). The
downstream beneficiary is the framework's least-privilege posture:
`gleipnir-code`'s capability layer stops over-stating what the role does.

**Measurable success criteria:**
1. `.gleipnir/agents/gleipnir-code.md`'s `edit` block contains the line
   `    ".github/**": deny` positioned between `.git/**` and
   `src/gleipnir/preflight/**`, byte-for-byte matching the converged block.
2. `grep -n '\.github' .gleipnir/agents/gleipnir-code.md` returns exactly the
   one new deny line (no other `.github` occurrence in the file).
3. `git diff HEAD -- .gleipnir/agents/gleipnir-code.md` shows **exactly one added
   line** and **zero other changes** (no reflow, no whitespace churn, no
   accidental edit to the `bash` allowlist or any other block).
4. Two distinct `quality-reviewer` verdicts recorded (`SPEC-CONFORM` +
   blast-radius/false-success) and one negative-check attestation row with
   `attested_by = quality-reviewer` (≠ editor).

**Constraints:**
- Tier-3 POLICY file → no roster agent may write it; operator-applied.
- Hardened path (Axis-2(a), path ∈ `E`) → two separate passes + attestation; the
  two rubrics do NOT fuse.
- The A/B/C decision is closed — do not re-litigate.
- Change is **subtractive on capability** (removes a write capability); it must
  add or narrow **nothing** the role actually uses.
- Honesty label carried forward: **cooperative-policy-until-S-2** — the `edit`
  deny is honoured by opencode's permission layer today, becomes a structural
  boundary only when the S-2 read-only mount lands (same caveat as the existing
  three denies).

---

## 3. Trace

**Artifact and source of truth.**

| Artifact | Path (source of truth) | State | Writer |
|---|---|---|---|
| The grant file (edited) | `.gleipnir/agents/gleipnir-code.md` | exists, 86 lines, read this session; `edit` block at lines 11–19, deny list lines 14–16 | **Operator** (build mode) — Tier-3, no roster path |
| Converged decision record | `.gleipnir/plans/gleipnir-code-github-grant-control-proposal.md` | exists, 233 lines, `## Convergence` at lines 197–233 | (already written; read-only input) |
| This plan | `.gleipnir/plans/gleipnir-code-github-grant.md` | this file | `gleipnir-plan` |

**Exact target block (verified on disk, lines 11–19):**

```yaml
permission:
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    "src/gleipnir/preflight/**": deny
  read: allow
  task: deny
  webfetch: deny
```

**The diff (add one line):**

```diff
   edit:
     "*": allow
     ".gleipnir/**": deny
     ".git/**": deny
+    ".github/**": deny
     "src/gleipnir/preflight/**": deny
   read: allow
```

**Resulting block:**

```yaml
permission:
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    ".github/**": deny
    "src/gleipnir/preflight/**": deny
  read: allow
  task: deny
  webfetch: deny
```

**Placement rationale (Decision #2).** The existing deny list is ordered
framework-internal/dot-config first (`.gleipnir/**`, `.git/**`), then the
source-tree path (`src/gleipnir/preflight/**`). `.github/**` is dot-prefixed
config, so it groups with `.git/**` before the `src/` deny. This matches the
in-file convention AND the verbatim block the operator converged on. (Note: this
is **not** strict alphabetical — `.git` sorts before `.gleipnir`, but the file
lists `.gleipnir/**` first — so "match existing precedent" is the governing
rule, and the precedent is "dot-config denies grouped, source-tree deny last.")

**Integrations map.** The `edit` deny interacts with opencode's permission layer
only. `deny` wins over the `"*": allow` base (same semantics as the existing
three denies). No other file references or depends on this grant line. The
`bash` allowlist, `tools` booleans, and prose body are untouched.

**Edge cases:**
- **YAML validity:** the added line uses the identical 4-space indent and
  `"quoted-glob": deny` shape as its three siblings; no YAML structure change.
- **Glob over-breadth (the thing the attestation must rule out):** `.github/**`
  matches everything under `.github/` and nothing outside it. It does NOT match
  `.githubfoo`, `.git/**` (already separately denied), or any `src/**` path. It
  must NOT be mistyped as `.github*` (would match sibling files like a
  hypothetical `.githubconfig`) or `**/.github/**` (would over-reach into
  nested subprojects — not intended; the role's job is repo-root source/tests).
- **Collateral edit risk:** the single most likely mechanical error is an
  editor reflowing or touching the adjacent `bash` block; the diff-against-HEAD
  check (success criterion #3) is precisely the guard against it.

---

## 4. Link (validated before applying)

- **Target file + line numbers verified** by reading
  `.gleipnir/agents/gleipnir-code.md` this session — `edit` block lines 11–19,
  deny list lines 14–16. Confirmed the block matches the converged proposal's
  quoted block byte-for-byte (pre-edit state).
- **Convergence verified** — `## Convergence` (lines 197–233) records CONVERGED:
  Option A, operator-decided via the `question` tool, dated 2026-08-20. The
  resolved artifact block there matches Trace §3's resulting block.
- **Blast-radius validated by grep** (see §6): no plan/test/workflow relies on
  `gleipnir-code` writing `.github/**`. The one plan touching `.github/**`
  (`config-scan-ci-wiring.md`) explicitly routed authorship to the operator and
  recorded that the routing was NOT because the grant lacked the capability
  (D12; lines 74–75, 161, 273). Removing the capability therefore breaks nothing.
- **Ordering convention validated** by inspecting the existing deny list
  in-file (Decision #2).
- **Writer path validated** — every roster grant, including `gleipnir-code`'s
  own (`.gleipnir/**": deny`, line 14), denies `.gleipnir/**`; confirmed the
  operator is the applying party (Decision #3).

---

## 5. Assemble (intended build order)

1. **spec-review** (`quality-reviewer`, hardened pass 1 — spec-conformance):
   confirm the diff in §3 matches the converged Option-A artifact and this
   plan's stated scope; confirm the Design Intent (§8) is specific/falsifiable
   (intent-quality sub-check).
2. **blast-radius pass** (`quality-reviewer`, hardened pass 2 — false-success):
   adversarially check for over-broad glob, collateral edits, and any reliance
   on the removed capability; produce the negative-check attestation row (§7).
   *(Passes 1 and 2 are two distinct recorded verdicts; they do NOT fuse.)*
3. **apply** (`code` stage, but **operator-applied in build mode**, NOT
   `gleipnir-code`): insert the single `".github/**": deny` line per §3.
4. **git** (`git-ops`): stage and commit the one-line change after the
   diff-against-HEAD verification (§6) confirms exactly one added line.
5. **gate** (`orchestrator`): read the recorded verdicts + attestation and emit
   the pipeline-complete state.

Note the ordering nuance: the negative-check attestation's `evidence` must be
captured against the **applied / post-change** file (hardened-path
post-change-state rule). So the *reproducible-artifact capture* for the
attestation happens **after** step 3 (apply), even though the attestation *row*
is drafted in step 2. Concretely: `quality-reviewer` frames the checks in step
2, then captures the grep/diff evidence against the post-apply file to finalize
the attestation before step 4 (git).

---

## 6. Stress-test (acceptance checks)

Each is concrete and checkable; all run against the **applied/post-change** file
(hardened-path post-change-state rule), before commit.

1. **New line present, correctly placed.**
   `grep -n '\.github' .gleipnir/agents/gleipnir-code.md`
   → MUST return exactly one line, the new `    ".github/**": deny`, and its line
   number MUST fall between the `.git/**` deny and the
   `src/gleipnir/preflight/**` deny. (Zero other `.github` occurrences in the
   file — there were none pre-edit.)
2. **Exactly one line added, nothing else changed.**
   `git diff HEAD -- .gleipnir/agents/gleipnir-code.md`
   → MUST show exactly one `+` line (the new deny) and zero `-` lines and zero
   other `+` lines. Any change to the `bash` allowlist, `tools`, prose body, or
   whitespace elsewhere is a FAIL.
3. **YAML still parses / block shape intact.** The resulting `edit` block MUST
   be the five-entry block in §3 (`"*": allow` + four denies), with `read`,
   `task`, `webfetch` unchanged below it.
4. **No over-broad glob.** The added token MUST be literally `".github/**"` —
   NOT `.github*`, NOT `**/.github/**`, NOT `.github/*` (which would miss nested
   paths the deny intends to cover). Verified by byte-for-byte quote of the
   applied line.
5. **Two distinct reviewer verdicts recorded** (`SPEC-CONFORM: PASS` +
   blast-radius `PASS`), not one fused "looks fine."
6. **Negative-check attestation complete** (§7): all fields present, `evidence`
   is a reproducible artifact (grep/diff output, not narrative), the evidence
   tests the specific over-broad form named in that row and targets *this* file,
   captured against the post-apply state, and `attested_by = quality-reviewer`
   (≠ the editor).
7. **Cognition cross-check (honour check).** The applied edit honours the stated
   Design Intent (§8): a capability was **removed** (`.github/**` write), and
   **no** capability the role uses (`src/**`, `tests/**` write; the
   `bin/gleipnir-sandbox` allowlist) was narrowed. Verified by check #2 (nothing
   else changed).

---

## 7. Negative-check attestation (hardened-path — authored by `quality-reviewer`)

One row per grant/enforcement change. To be completed by `quality-reviewer`
against the **post-apply** file; the editor MUST NOT self-attest (L-C8). Template
with the required fields filled to the extent the plan can pre-specify them:

| Field | Value |
|---|---|
| **grant** | `".github/**": deny` added to the `edit` block in `.gleipnir/agents/gleipnir-code.md` |
| **intended narrowest scope** | Deny `gleipnir-code`'s `edit` tool from writing any path under `.github/` (and nothing outside `.github/`). Matches the Axis-1 `X` granularity exactly. |
| **over-broad form checked-for-and-ruled-out (a)** | The glob is NOT an over-reaching variant: NOT `.github*` (would match sibling `.github…` files), NOT `**/.github/**` (would reach nested-subproject `.github/`), NOT `.github/*` (would miss deep paths). It is exactly `.github/**`. |
| **over-broad form checked-for-and-ruled-out (b)** | NO other roster agent's grant and NO other block in this file was touched (no collateral change to the `bash` allowlist, `tools`, `read/task/webfetch`, or prose body). |
| **evidence** `[D]` | `grep -n '\.github' .gleipnir/agents/gleipnir-code.md` output (shows the single new deny line + its line number between `.git/**` and `src/…preflight`); AND `git diff HEAD -- .gleipnir/agents/gleipnir-code.md` output (shows exactly one `+` line, zero `-`, zero other changes). Both captured against the applied/post-change file. |
| **negative result** | "`.github*`, `**/.github/**`, and `.github/*` are NOT present; the applied token is exactly `.github/**`. No change to any other grant, block, or agent file is present in the diff." |
| **attested_by** | `quality-reviewer` (MUST NOT be the operator/editor who applied it) |

The evidence is `[D]` (tool-produced: `grep`/`git diff`). The correspondence
rule is satisfied: the grep pattern (`\.github`) and the diff both target the
**same file named in `grant`**, and they test the **same over-broad forms named
in the `over_broad_form_checked` rows**.

---

## 8. Design Principles (Gate 1 — case (iii): prose/config-only, `P ∩ X = ∅`)

`P = { .gleipnir/agents/gleipnir-code.md }`; `P ∩ X = ∅` (a `.md` policy file,
no executable/interpreted artifact). Therefore:

- **SOLID analysis:** `N/A — no executable artifact` (no class/function/module
  to analyse).
- **DRY analysis:** `N/A — no executable artifact` (no code logic to duplicate).
- **Single Responsibility check:** `N/A — no executable artifact` (no
  module/class/function).

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**

> `gleipnir-code`'s capability grant must be **no broader than its actual job**
> — authoring source and tests under `src/**` and `tests/**`. This change
> **removes** a write capability (`.github/**`) the role has never legitimately
> needed and which the framework's own routing already treats as
> enforcement-bearing (`.github/**` ∈ Axis-1 disqualifier set `X`), closing a
> least-privilege gap. The intent is strictly **subtractive on capability**: it
> removes `.github/**` write and narrows **no** capability the role uses.

**Why this is falsifiable (not a vacuous aspiration):** a reviewer can point to
a violating implementation choice — e.g. (a) the diff also narrowing or altering
the `src/**`/`tests/**` write path or the `bin/gleipnir-sandbox` bash allowlist
(would violate "narrows no capability the role uses"); (b) the added glob
reaching beyond `.github/` (e.g. `**/.github/**` catching nested subprojects, or
`.github*` catching siblings — would violate "no broader than its job / exactly
the `.github/` tree"); or (c) evidence that some plan/test/workflow actually
relied on the removed capability (would violate "never legitimately needed").
The blast-radius grep in §6 rules out (c); Stress-test checks #2 and #4 rule out
(a) and (b). The honour check (§6 #7, run at the `quality` pass) verifies the
applied edit honours this intent.

---

## 9. Blast-radius finding (documented per the delegation)

**Question:** does denying `.github/**` in `gleipnir-code`'s grant break anything
currently relying on that capability?

**Method:** `grep -n '\.github'` and `grep -n 'gleipnir-code'` across
`.gleipnir/plans/**`.

**Finding: nothing relies on it. Removing the capability is safe.** Evidence:

- **`config-scan-ci-wiring.md`** is the only plan that authors a `.github/**`
  file (`.github/workflows/config-scan.yml`). It **deliberately routed
  authorship to the operator**, and explicitly recorded that the routing was NOT
  because `gleipnir-code` lacked the capability:
  - D12 / line 74–75: "`.github/**` is **NOT** in that deny list, so
    `gleipnir-code` structurally CAN write … today. It is nonetheless routed to
    the [operator]."
  - line 161, 273: same observation restated. So this plan did **not** depend on
    the grant; it worked around it by design.
- **`config-scan-ci-wiring-brainstorm.md`** (line 78): "`.github/**` is outside
  every roster agent's [intended authorship]" — confirms authorship was never
  meant to sit with a roster code agent.
- **SESSION-STATE.md** (lines 43–52, 183, 222): this exact grant gap was recorded
  as a **latent `tier3-coach` candidate**, "explicitly OUT OF SCOPE for this
  session … Worth a future `tier3-coach` look (whether to tighten that grant to
  explicitly exclude `.github/**`)." This plan closes that recorded follow-up.
- No test, Makefile, or CI job invokes `gleipnir-code` to write `.github/**`
  (the sandbox allowlist grants only `bin/gleipnir-sandbox test|lint`; no
  `.github` authorship path exists in any test).

**Conclusion:** the change is purely subtractive on a capability that is unused
and was already being worked around. No plan, test, or documented workflow
regresses. This is a least-privilege tightening, not a functional removal.

---

## 10. Execution Workflow (for the applying operator + reviewer)

1. **Pre-apply (reviewer, spec-review pass 1):** confirm the §3 diff matches the
   converged Option-A block and this plan's scope; confirm §8 Design Intent is
   specific/falsifiable. Record `SPEC-CONFORM: PASS/FAIL`.
2. **Pre-apply (reviewer, blast-radius pass 2):** run the §6 checks adversarially
   *as designed* (framing), and draft the §7 attestation row. Record blast-radius
   `PASS/FAIL`. These are two distinct verdicts; do NOT fuse them.
3. **Apply (operator, build mode — NOT `gleipnir-code`):** open
   `.gleipnir/agents/gleipnir-code.md`; insert `    ".github/**": deny`
   (4-space indent, matching siblings) on its own line **between** the `.git/**`
   deny and the `src/gleipnir/preflight/**` deny. Change nothing else. (The
   optional prose-body comment is the operator's call and out of this plan's
   scope — Decision #4.)
4. **Post-apply verify (reviewer):** run Stress-test checks #1–#4 against the
   applied file; capture the `grep` + `git diff HEAD` output as the §7
   attestation `evidence` (post-change state). Finalize the attestation with
   `attested_by = quality-reviewer`.
5. **git (`git-ops`):** stage only `.gleipnir/agents/gleipnir-code.md`; commit
   with a message naming the converged decision and this plan. Do NOT commit any
   other file.
6. **gate (`orchestrator`):** verify two verdicts + complete attestation +
   cognition honour check (§6 #7) all present; emit pipeline-complete.

**If any Stress-test check fails at step 4** (e.g. the diff shows more than one
added line, or an over-broad glob was typed): STOP, do not proceed to git,
report the deviation to the operator to re-apply. Do not "fix forward" a Tier-3
policy file outside the operator's hand.

**No new material tradeoff** is introduced by this plan. If the reviewer or
operator discovers one during application (e.g. an unexpected dependency on the
removed capability that §9 missed), STOP and route it back to the operator — do
not resolve it inside the mechanics.
