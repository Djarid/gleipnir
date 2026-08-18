# Plan: go-caged — operator-facing caged-mode runbook + guiding skill

> **Stage:** `plan` (ATLAS Architect/Trace). **Author:** `gleipnir-plan`.
> **Tier-0, disposable.** Plans FROM the CONVERGED brief
> `.gleipnir/plans/caged-mode-runbook-brainstorm.md` (C1–C5 operator-converged).
> This plan does **NOT** re-decide C1–C5; it plans HOW to build the two
> artifacts and carries their full ready-to-apply text for the orchestrator to
> apply.

---

## Routing header — HARDENED self-classification

**Touched-path set `P`** (the artifacts this plan's WORK produces / edits):

1. `.gleipnir/decisions/go-caged-runbook.md` — NEW Tier-3 durable runbook (prose).
2. `.gleipnir/skills/go-caged/SKILL.md` — NEW Tier-3 skill (prose + YAML frontmatter).
3. `.gleipnir/plans/caged-mode-runbook.md` — this Tier-0 plan (the only file
   `gleipnir-plan` writes; the two above are produced AS TEXT here for the
   orchestrator to apply).

**Route = HARDENED path.** Determination against `../stage-role-map.md`:

- **Axis 1 (eligibility gate):** `P` contains zero members of disqualifier set
  `X` — all three are inert `*.md` (no `src/**`, `tests/**`, `bin/**`, no
  Makefile/CI/shell/shebang, no standalone YAML file — the SKILL.md frontmatter
  is embedded YAML in a `.md`, not a standalone `*.yml`/`*.yaml`). So the plan
  is **prose/config-only track-ELIGIBLE** (Axis-1 does not disqualify it).
- **Axis 2(a) — path rule:** `.gleipnir/skills/**` is **NOT** in the explicitly
  enumerated enforcement-path set `E` (`E` = `.gleipnir/agents/**`,
  `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`, `.gleipnir/policy/**`,
  `.gleipnir/keys/**`, `.gleipnir/stage-role-map.md`, `opencode.jsonc`/
  `**/opencode.json`, and the enumerated repo-root cross-cutting files).
  `.gleipnir/decisions/**` is likewise **NOT** in `E` (Axis-2's "low-consequence
  prose" clause explicitly lists `.gleipnir/decisions/** prose` on the LIGHT
  side). So **Axis 2(a) does not, by its literal terms, route this to hardened.**
- **Axis 2(b) — content rule:** the SKILL.md frontmatter carries `name:` /
  `description:` / `metadata:` only — it does **NOT** add a `permission:` or
  `tools:` block, a capability line (`edit|write|task|bash|webfetch` with
  `allow`/`deny`), a JSON(C) enforcement key, a binding-table row, or a
  `keys/**` digest line. So no `G`-pattern match. **Axis 2(b) does not route to
  hardened either.**

**Yet this plan self-classifies HARDENED, on the safe side, by operator
instruction and by the tier-3 nature of the targets.** Both `.gleipnir/skills/`
and `.gleipnir/decisions/` are **Tier-3 POLICY** (`AGENTS.md` trust-tier table:
Tier 3 = `agents/ skills/ goals/ decisions/ stage-role-map.md keys/`). A new
*skill* is enforcement-adjacent (skills shape agent behaviour and the `go-caged`
skill guides a security-critical lockdown; a defective skill misguides the
operator during exactly the moment the threat model requires assurance). The
integrity>efficiency principle that governs the classifier's safe-side calls
(standalone-YAML disqualification, always-hardened `.gitignore`) applies here:
where the literal routing is genuinely borderline for a Tier-3 target, choose
the hardened path. **Consequence:** `quality-reviewer` runs the TWO
NON-FUSING rubrics (spec-conformance PASS/FAIL + adversarial blast-radius /
false-success PASS/FAIL, recorded as two distinct verdicts) plus the
**negative-check attestation** (`attested_by ≠ author`), even though the
mechanical `G`-pattern set is empty. Because `P` has no `permission:`/`tools:`
grant line, the negative-check attestation table has **one row asserting the
absence of any grant/enforcement line** (see Stress-test) rather than per-grant
rows — the honest hardened form when the artifact is Tier-3 prose that adds no
capability grant.

**Authorship under the default-uncaged paradigm.** Per
`../decisions/operating-posture.md` (committed), the DEFAULT posture is
**uncaged**: an agent acting under operator instruction MAY write Tier-3
(`decisions/`, `skills/`). So — unlike pre-paradigm plans that could only
*propose* Tier-3 text — the **orchestrator may draft AND apply** both artifacts
directly on operator instruction. `gleipnir-plan` (this role) remains a Tier-0
writer ONLY: it produces the full text here and does **not** apply it. The
operator has indicated "I write no code, you do it in build" → the orchestrator
applies the two files verbatim from the "Ready-to-apply artifacts" section.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| C1 | Runbook location + authorship | **`.gleipnir/decisions/go-caged-runbook.md`** (Tier-3 durable); orchestrator drafts+applies under uncaged default | `.gleipnir/runbooks/` (new dir), `.gleipnir/plans/` (Tier-0 disposable) | **OPERATOR-CONVERGED** (brief C1: matrix 334>284>211). Runbook is operational POLICY, companion to `operating-posture.md`; must be durable. NOT re-decided. Filename `go-caged-runbook.md` chosen (HOW-detail; matches the `go-caged` skill name + the reference already forward-linked from `operating-posture.md` line 47). |
| C2 | Skill: new vs extend tier3-coach | **NEW sibling skill `go-caged`** at `.gleipnir/skills/go-caged/SKILL.md` | Fold into `tier3-coach` | **OPERATOR-CONVERGED** (brief C2). Boundary named in both skills: tier3-coach DETECTS gaps+PROPOSES controls; go-caged EXECUTES a known lockdown. Reuses tier3-coach's guides-but-operator-applies handoff BY REFERENCE. Skill guides+verifies; operator executes OS acts (needs root). NOT re-decided. |
| C3 | Trigger phrasing | Drafted triggers accepted, primary = **"go caged"** | — | **OPERATOR-CONVERGED** (brief C3). Anchored to the 3 `operating-posture.md` categories: *go caged*, *cage the system*, *lock it down*, *going autonomous/unattended*, *high-assurance mode*, *ingesting untrusted content*. Primary-phrase pin ("go caged") is the carried residual, resolved here. NOT re-opened. |
| C4 | Reference-vs-inline the S-2 commands | **HYBRID** — inline `--mode caged` glue + AC-4 + rollback; **reference** the six OS acts | Approach A (all-reference), Approach B (all-inline) | **OPERATOR-CONVERGED** (brief C4, the primary tradeoff). Drift risk stays single-sourced in the referenced host block; usability stays inline for stable glue. NOT re-decided. Exact split point + currency banner confirmed here (carried residual). |
| C5 | Uncage / rollback | **MINIMAL uncage** = stop requesting caged; OS perms may stay; key mode-600 stays in BOTH modes; full teardown separate | Full teardown as routine uncage | **OPERATOR-CONVERGED** (brief C5). Two-Way Door; leaving the hardened floor is lower-risk. NOT re-decided. |
| P-1 | Skill-loading wiring (carried residual) | **Operator-invoked on demand** — do NOT add `Load skill go-caged` to any roster agent | Add to `gleipnir-brainstorm`/`orchestrator` startup | HOW-detail, not a material tradeoff. The skill loads by trigger phrase on operator request (same on-demand model as tier3-coach, which no agent auto-loads). Auto-loading a security-lockdown skill into every turn is a per-turn token cost against the model-sizing principle. This is a *note*, not a Tier-3 roster edit (none is proposed by this plan). |
| P-2 | Runbook filename (carried residual) | **`go-caged-runbook.md`** under `.gleipnir/decisions/` | `caged-mode-runbook.md`, `caged-runbook.md` | HOW-detail. Matches the skill name `go-caged` and the forward-link already present at `operating-posture.md:47` ("the `go-caged` runbook"). |

All C-rows are **inherited operator-converged decisions** from the brief and are
cited, not re-decided (plan-format §1 requires one row per material decision
including operator-converged ones). P-1/P-2 are the bounded HOW-residuals the
brief explicitly carried to `gleipnir-plan`.

---

## Architect

**Problem (one sentence).** There is no single operator-facing front door that
says *exactly how to satisfy the `operating-posture.md` caged requirement,
step by step, verified against the real box, with a go/no-go gate* — so this
plan assembles the four existing pieces (the built `--mode caged` selector, the
six S-2 C2 OS acts, the AC-4 acceptance test, and the tier3-coach
guides-but-operator-applies handoff) into one durable runbook plus a guiding
skill.

**User.** The operator, at the moment a caged-mode trigger fires (often
mid-incident / under pressure): entering unattended/autonomous operation,
ingesting untrusted content, or a higher-assurance context.

**Measurable success criteria.**
1. The runbook file `.gleipnir/decisions/go-caged-runbook.md` exists and
   INLINES: the `--mode caged` invocation, the AC-4 go/no-go acceptance test,
   and the uncage/rollback steps.
2. The runbook does **NOT** duplicate any of the six OS-act commands
   (dscl/sysadminctl/chmod/chown/chgrp/launch-wrapper) — it REFERENCES
   `s2-activation-control-proposal.md` acts (1)–(6) with a currency banner.
3. The skill `.gleipnir/skills/go-caged/SKILL.md` exists with frontmatter whose
   `description` carries all six C3 trigger phrases, leads with "go caged", and
   names the tier3-coach boundary.
4. Both artifacts name the guides-but-operator-applies boundary and cite
   tier3-coach Anti-Pattern 3 (guide/verify, never execute the OS acts).
5. The runbook states the C5 minimal-uncage policy: stop requesting caged; OS
   perms may stay; key mode-600 stays in BOTH modes; full teardown is a
   separate rare decommission decision.
6. No new dependency (enforcement core stays stdlib-only); no config system,
   generator, or templating (over-engineering guard from the brief).

**Constraints (inherited).**
- **C4 anti-drift:** the six volatile host-specific OS commands are
  single-sourced in `s2-activation-control-proposal.md`; never inlined here.
- **C5 key floor:** `keys/marker.key` mode-600 is NEVER relaxed in either mode.
- **Tier boundary:** runbook + skill are Tier-3; the OS acts are operator/root
  (agent cannot perform them). `gleipnir-plan` writes only Tier-0; the
  orchestrator applies the Tier-3 files under the uncaged default.
- **Assemble, don't reinvent:** the plan cites the four existing pieces; it
  re-authors neither the S-2 procedure nor the preflight semantics.

---

## Trace

**Artifacts and where they live (source of truth):**

| Artifact | Home | Tier | Source-of-truth role |
|---|---|---|---|
| `go-caged-runbook.md` | `.gleipnir/decisions/` | 3 (durable) | **Source of truth** for the go-caged front-door procedure (assembly + inline glue). |
| `go-caged/SKILL.md` | `.gleipnir/skills/go-caged/` | 3 (durable) | Guides the operator through the runbook; the runbook is ITS source of truth (no procedure duplicated in the skill). |
| Six OS acts (1)–(6) | `.gleipnir/plans/s2-activation-control-proposal.md` | 0 | **Source of truth for the OS commands** — REFERENCED by the runbook, never copied. |
| `--mode caged` selector | `src/gleipnir/preflight/__main__.py` + `boundary.py` | (out-of-framework) | The software glue INLINED (invocation) by the runbook; semantics cited, not re-authored. |
| AC-4 acceptance test | `s2-activation.md` AC-4 | 0 | The go/no-go gate INLINED by the runbook. |
| tier3-coach handoff | `.gleipnir/skills/tier3-coach/SKILL.md` (Anti-Pattern 3) | 3 | The guides-but-operator-applies pattern REUSED BY REFERENCE. |
| `operating-posture.md` | `.gleipnir/decisions/` | 3 | The paradigm the runbook operationalises (3 triggers, honesty invariant, key floor). |

**Integrations map.**
- Runbook → REFERENCES → `s2-activation-control-proposal.md` acts (1)–(6) [OS layer].
- Runbook → INLINES → `bin/gleipnir-preflight --mode caged` invocation + AC-4 line + rollback.
- Runbook → CITES → `operating-posture.md` (triggers, honesty label, key floor).
- Skill → REFERENCES → the runbook as single source of truth.
- Skill → CITES BY REFERENCE → tier3-coach Anti-Pattern 3 (handoff + self-attestation discipline).
- `operating-posture.md:47` already forward-links "the `go-caged` runbook" → this plan makes that link resolve.

**Cross-artifact note + open item OI-1 (spec-review R-1 finding — `gleipnir-launch`
is NOT a caged gate as drafted).** The `bin/gleipnir-launch` wrapper drafted in
act (6) of `s2-activation-control-proposal.md` calls the preflight WITHOUT
`--mode caged`, so it runs at the DEFAULT uncaged mode: on a NOT-closed boundary
the uncaged/no-override path returns PROCEED_UNCLOSED under the neutral uncaged
label and **exits 0** (`boundary.py:575-591` + `__main__.py` exit mapping), and
because the wrapper uses `set -e`, exit 0 lets it **drop-and-launch even when the
boundary is not closed**. Only an explicit `--mode caged` turns not-closed into
REFUSE (exit 1). Both ready-to-apply artifacts are corrected to characterise the
wrapper accurately (a launch convenience, not the gate) and to direct the
operator to the explicit `--mode caged` AC-4 check as the ONLY authoritative
gate. **The real fix — amending act (6)'s embedded preflight call to add
`--mode caged`** — is an edit to `s2-activation-control-proposal.md`, which is
**OUTSIDE this plan's touched-path set `P`** (this plan creates only the runbook +
skill). This plan therefore does NOT apply it and RECORDS it as a required
companion follow-up:

> **OI-1 (open item / cross-artifact dependency — required companion follow-up).**
> Amend act (6) in `s2-activation-control-proposal.md` so the `bin/gleipnir-launch`
> embedded preflight call passes `--mode caged`, making the wrapper a genuine
> fail-closed caged gate on every launch. Owner: operator (Tier-3 / `bin/`
> territory; no roster agent can apply it). Until then, the explicit `--mode
> caged` AC-4 check is the only authoritative gate. Surfaced in the runbook's
> "Cross-artifact note" section so it is not lost.

**Verified ground truth (against source, this session):**
- `bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --mode caged` (no
  `--override-ack`) → exit 0 + CLOSED **only if the boundary genuinely holds**;
  caged-not-CLOSED → exit 1 REFUSE (`__main__.py:13-30` exit-code contract;
  `--mode {uncaged,caged}` default uncaged, lines 24-29). `requested_mode` never
  enters `all_closed` (anti-false-assurance). This is the inlined glue — nothing
  to build in software.
- AC-4 requires `sudo` on macOS (setuid to another uid needs root)
  (`s2-activation-control-proposal.md` step (6); `s2-activation.md` AC-4).
- The six OS acts exist verbatim, ready-to-apply, in
  `s2-activation-control-proposal.md` lines 40–143 — REFERENCED, not copied.
- The preflight is out-of-framework, operator-run, fail-closed; never routed
  into any agent allowlist (`__main__.py:1-12`) — the skill must NOT try to run
  it as an agent; it GUIDES the operator to run it.
- **`bin/gleipnir-launch` as drafted (act (6), `s2-activation-control-proposal.md`
  lines 124-126) calls the preflight WITHOUT `--mode caged`** → default uncaged;
  on a not-closed boundary it exits 0 (PROCEED_UNCLOSED, neutral label) and, via
  `set -e`, proceeds to launch. It is NOT a fail-closed caged gate as drafted.
  Only the explicit `--mode caged` invocation refuses. (OI-1 above tracks the fix.)

**Edge cases.**
1. **Caged requested but boundary not CLOSED** → preflight exit 1 REFUSE; the
   runbook's go/no-go gate says: NOT caged, do not launch, fix the failing
   reason. The skill verifies this against real box state, never self-attests.
2. **Stale reference** (six OS acts change in the proposal but runbook not
   re-read): mitigated because the runbook REFERENCES (does not copy) the acts,
   AND the skill's per-step verify reads the current proposal at execution time.
3. **Operator expects uncage to "undo everything"**: the runbook's rollback
   section explicitly states OS perms persist harmlessly and the key floor stays
   — surprise removed (C5).
4. **Key floor accidentally relaxed during uncage**: the runbook states in bold
   that mode-600 on `keys/marker.key` is NEVER relaxed in either mode.
5. **Agent tempted to run the OS acts**: both artifacts state the boundary — the
   agent GUIDES+VERIFIES, the operator executes; cite tier3-coach Anti-Pattern 3.
6. **Skill over-triggers on casual "cage"**: description anchors triggers to the
   three posture categories and the specific phrases, not the bare word "cage".
7. **Operator relies on `gleipnir-launch` as the caged gate** (the R-1 defect):
   the wrapper as drafted does NOT `--mode caged`, so it launches uncaged on a
   not-closed boundary — false assurance at the assurance-critical moment. Both
   artifacts now characterise it accurately and route the operator to the
   explicit `--mode caged` AC-4 check as the ONLY gate; OI-1 tracks amending the
   wrapper to `--mode caged`.

---

## Link (validated before building)

- **Converged brief read in full** — C1–C5 are operator-converged; residuals
  P-1 (skill-loading wiring), P-2 (filename) resolved as HOW-details.
- **All four assembled pieces confirmed to exist** (not merely cited):
  `s2-activation-control-proposal.md` (six acts, lines 40–143),
  `src/gleipnir/preflight/__main__.py` (`--mode caged`, exit contract),
  `s2-activation.md` (AC-4), `skills/tier3-coach/SKILL.md` (Anti-Pattern 3,
  line 155). `operating-posture.md` exists and forward-links go-caged (line 47).
- **SKILL.md conventions confirmed** from `tier3-coach/SKILL.md` frontmatter
  (`version`, `name`, `description`, `license`, `metadata:` block with
  `version`/`origin`/`inherited_by`/`inheritance`/`rationale`) and
  `skills/README.md` (origin: gleipnir, inheritance: original for net-new
  skills). The `go-caged` frontmatter matches this shape.
- **Routing validated** against `stage-role-map.md` E-set and Axis-1 `X`:
  eligible, literal routing borderline, self-classified HARDENED safe-side.
- **Nothing to build in software** — the `--mode caged` selector is built and
  confirmed; this is prose assembly only. No dependency added.

---

## Assemble (build order + who applies)

Both artifacts are produced AS FULL TEXT in "Ready-to-apply artifacts" below.
Under the uncaged default the **orchestrator applies them** (operator-instructed);
`gleipnir-plan` writes only this Tier-0 plan.

1. **Apply the runbook** → `.gleipnir/decisions/go-caged-runbook.md` (orchestrator
   writes the full text from §Ready-to-apply artifacts, Artifact 1). Durable
   Tier-3.
2. **Apply the skill** → `.gleipnir/skills/go-caged/SKILL.md` (orchestrator writes
   the full text, Artifact 2). Durable Tier-3.
3. **Cross-reference check** (orchestrator, before handing to review): the skill
   references the runbook; the runbook references the six OS acts + inlines the
   glue; both name the tier3-coach boundary.
4. **HARDENED review** (`quality-reviewer`): two non-fusing rubrics +
   negative-check attestation (see Stress-test).
5. **No `test`/`code`/`git` executable stages** for the artifacts' content
   (prose/config-only track members carry an attested "N/A — no executable
   artifact" transition); the `git` stage commits the two applied files via
   `git-ops` after review passes.

**Who applies what:** orchestrator applies both Tier-3 files (uncaged default,
operator-instructed). The OS acts (1)–(6) are NOT applied by this plan or the
orchestrator — they remain the OPERATOR's root-required action, guided by the
skill and gated by AC-4, exactly as `s2-activation-control-proposal.md` states.

---

## Stress-test (concrete acceptance criteria)

Each is checkable by `grep`/read against the APPLIED files (post-change state).

**Runbook (`.gleipnir/decisions/go-caged-runbook.md`):**
- **ST-1 (no OS-act duplication — the C4 anti-drift invariant).** The runbook
  contains **NO** `dscl`, `sysadminctl`, `chgrp`, or the `chmod 644 agents/*.md`
  / `chmod -R a+rX,go-w agents decisions goals keys` command bodies. Evidence:
  `grep -nE 'dscl|sysadminctl|chgrp|a\+rX,go-w' .gleipnir/decisions/go-caged-runbook.md`
  → **no match**. It REFERENCES "acts (1)–(6) in
  `s2-activation-control-proposal.md`" instead. `grep -n
  's2-activation-control-proposal.md' …` → **match present**.
- **ST-2 (inlines the `--mode caged` invocation).** `grep -n 'gleipnir-preflight'
  … | grep -- '--mode caged'` → match; the exact invocation
  `sudo bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --mode caged`
  is present inline.
- **ST-3 (inlines the AC-4 go/no-go gate).** The runbook states the gate:
  no-override preflight → `closed`, empty reasons, exit 0 ⇒ caged; anything else
  ⇒ NOT caged, do not launch. `grep -niE 'AC-4|go/no-go|empty reasons|exit 0'` → match.
- **ST-4 (inlines rollback / minimal uncage — C5).** Section states: uncage =
  drop `--mode caged` / the launch wrapper; OS perms MAY stay; **key mode-600
  stays in BOTH modes, never relaxed**; full teardown is a separate rare
  decommission decision. `grep -niE 'uncage|mode 600|teardown'` → match, incl.
  the "never relaxed" clause.
- **ST-5 (names the tier3-coach boundary + guides-but-operator-applies).** The
  runbook states the agent GUIDES+VERIFIES and the OPERATOR executes the OS acts
  (root), citing tier3-coach Anti-Pattern 3. `grep -ni 'tier3-coach'` → match.
- **ST-6 (honesty label).** States cooperative-until-AC-4-passes → hard OS
  boundary once AC-4 passes; cites `operating-posture.md` honesty invariant.
- **ST-7 (currency banner on the reference).** A banner states: source of truth
  for the OS acts = `s2-activation-control-proposal.md`; the skill's per-step
  verify catches a stale reference at execution time.
- **ST-17 (`gleipnir-launch` accurately characterised — NOT a caged gate; R-1
  fix).** The runbook does **NOT** claim `bin/gleipnir-launch` runs the same
  no-override/caged preflight or enforces the gate. Instead it WARNS that, as
  drafted, the wrapper calls the preflight without `--mode caged`, exits 0 on a
  not-closed boundary, and is a launch convenience only — and directs the
  operator to the explicit `--mode caged` AC-4 check as the ONLY authoritative
  gate. Evidence: `grep -niE 'NOT a caged gate|launch convenience|WITHOUT .*--mode caged'`
  → match; `grep -ni 'runs this same no-override preflight'` → **no match** (the
  false-assurance sentence is removed). The runbook also has a **Cross-artifact
  note** recording OI-1 (`grep -ni 'Cross-artifact note'` → match).
- **ST-18 (OI-1 recorded as a named cross-artifact follow-up in the plan).** The
  plan's Trace section names **OI-1**: amend act (6) in
  `s2-activation-control-proposal.md` to pass `--mode caged`; owner = operator;
  outside `P`; not applied by this plan. `grep -ni 'OI-1'` on the plan → match.

**Skill (`.gleipnir/skills/go-caged/SKILL.md`):**
- **ST-8 (C3 triggers, primary = "go caged").** Frontmatter `description`
  contains all six phrases: *go caged*, *cage the system*, *lock it down*,
  *going autonomous/unattended*, *high-assurance mode*, *ingesting untrusted
  content*, and leads with "go caged". `grep -ni 'go caged'` → match in
  description; visual check of the phrase list.
- **ST-9 (references the runbook as single source of truth).** `grep -n
  'go-caged-runbook.md'` → match; the skill body says the runbook is its source
  of truth and it does NOT duplicate the procedure.
- **ST-10 (names the tier3-coach boundary).** Frontmatter + body state:
  tier3-coach DETECTS gaps + PROPOSES controls; go-caged EXECUTES a known,
  already-designed lockdown. `grep -ni 'tier3-coach'` → match.
- **ST-11 (guides+verifies, operator executes; reuses handoff by reference).**
  Body cites "same handoff shape as tier3-coach Anti-Pattern 3" and the
  self-attestation discipline (a subagent's `question` cannot reach the
  operator). The skill NEVER runs the OS acts. `grep -ni 'Anti-Pattern 3'` → match.
- **ST-12 (frontmatter shape matches conventions).** `version`, `name:
  go-caged`, `description`, `license`, `metadata` block with `origin: gleipnir`,
  `inheritance: original` — matches tier3-coach + skills/README conventions.
- **ST-19 (skill does NOT present `gleipnir-launch` as an equivalent gate; R-1
  fix).** Workflow step 2 guides the operator to the explicit `--mode caged`
  invocation as the authoritative go/no-go, attributes the REFUSE (exit 1)
  behaviour ONLY to the explicit `--mode caged` invocation, and explicitly says
  the wrapper is NOT an equivalent gate (calls preflight without `--mode caged`,
  exits 0 on a not-closed boundary). Evidence: `grep -ni 'Do NOT present .*gleipnir-launch'`
  → match; the skill does NOT say `--mode caged` REFUSES via `gleipnir-launch`.

**HARDENED review obligations (both artifacts, per `stage-role-map.md`):**
- **ST-13 (two non-fusing rubrics).** `quality-reviewer` records TWO distinct
  verdicts: `SPEC-CONFORM: PASS/FAIL` and a separate adversarial blast-radius /
  false-success `PASS/FAIL` (not one fused "looks fine").
- **ST-14 (negative-check attestation, `attested_by ≠ author`).** Because `P`
  adds **no** `permission:`/`tools:`/capability grant line, the attestation has
  **one row** asserting exactly that:
  - `grant`: (none — the two files add no capability grant to any agent).
  - `over_broad_form_checked`: any `permission:`/`tools:` block or
    `edit|write|task|bash|webfetch` `allow`/`deny` line, or a
    `stage-role-map.md` binding-table row edit, or a `keys/**` digest line.
  - `evidence` `[D]`: `grep -nE 'permission:|tools:|(edit|write|task|bash|webfetch).*(allow|deny)' .gleipnir/decisions/go-caged-runbook.md .gleipnir/skills/go-caged/SKILL.md`
    run against the APPLIED files → **empty output**.
  - `negative_result`: "No grant/enforcement/capability line is present in
    either artifact; both are Tier-3 prose that changes no agent capability."
  - `attested_by`: `quality-reviewer` (NOT the author).

**Cognition cross-check (both stages):**
- **ST-15 (spec-review intent-quality).** The Design Intent below is verified
  specific/falsifiable (not a vacuous aspiration).
- **ST-16 (quality honour-check).** The applied artifacts honour the Design
  Intent: single front door, glue inline + six acts by reference (no
  duplication), skill guides+verifies against the runbook, never executes.

---

## Execution Workflow

For the orchestrator applying this plan (uncaged default, operator-instructed):

1. Read the two full-text artifacts in §Ready-to-apply artifacts.
2. Write Artifact 1 verbatim to `.gleipnir/decisions/go-caged-runbook.md`
   (create; do not overwrite an existing file without operator confirmation).
3. Write Artifact 2 verbatim to `.gleipnir/skills/go-caged/SKILL.md` (create the
   `go-caged/` dir).
4. Run the cross-reference check (Assemble step 3).
5. Delegate HARDENED review to `quality-reviewer`: two non-fusing rubrics +
   the single-row negative-check attestation (ST-13, ST-14) + cognition
   cross-check (ST-15/16). `attested_by` must be the reviewer, not the author.
6. On PASS both verdicts, delegate `git` to `git-ops` to commit the two files.
   The `test`/`code` stages carry the attested "N/A — no executable artifact"
   transition (prose/config-only track).
7. Do **NOT** apply the six OS acts and do **NOT** run the preflight as an
   agent — those are the operator's root actions the skill guides.

**If review FAILS:** the reviewer returns the failing rubric; the orchestrator
routes a correction back through `gleipnir-plan` (text amendment) — the plan is
the editable source of the artifact text.

---

## Design Principles (Gate 1 — AETOS design-time cognition gate)

**Case routing: CASE (iii) — prose/config-only (`P ∩ X = ∅`).** `P` =
{`.gleipnir/decisions/go-caged-runbook.md`, `.gleipnir/skills/go-caged/SKILL.md`,
this Tier-0 plan} — all inert markdown; none is a member of disqualifier set `X`
(no `src/**`, `tests/**`, `bin/**`, Makefile, CI YAML, shell, shebang, or
standalone `*.yml`/`*.yaml`). Therefore:

- **SOLID analysis:** **N/A — no executable artifact** (no class/function/module
  to analyse for SRP/OCP/LSP/ISP/DIP).
- **DRY analysis:** **N/A — no executable artifact** (formally attested N/A per
  case (iii)). *Note:* the DRY-shaped concern that DOES matter here —
  non-duplication of the six OS-act commands — is captured as the falsifiable
  **Design Intent** below and as ST-1, not as a code-DRY analysis.
- **Single Responsibility check:** **N/A — no executable artifact.**

**Design Intent (specific, falsifiable — the case-(iii) genuineness proxy):**

> The `go-caged-runbook.md` MUST be the **single operator-facing front door**
> that ASSEMBLES the already-built pieces — INLINING only the short, stable,
> high-pressure glue (the `--mode caged` invocation, the AC-4 go/no-go gate, the
> uncage/rollback steps) and REFERENCING the six volatile, host-specific S-2 OS
> acts in `s2-activation-control-proposal.md` **without duplicating any of those
> six command bodies** (the C4 anti-drift constraint); AND the `go-caged` skill
> MUST **guide + verify** the operator against that runbook while the **operator
> executes** the OS/root acts — the skill **never executes them itself** (the C2
> boundary), reusing tier3-coach's guides-but-operator-applies handoff by
> reference.

**Why this is falsifiable (not a vacuous aspiration):** a reviewer can point to
a concrete violation of each clause —
- *duplication:* any `dscl`/`sysadminctl`/`chgrp`/`chmod -R a+rX,go-w …` command
  body appearing inline in the runbook violates the "reference, don't duplicate"
  clause (falsified by ST-1);
- *front-door assembly:* the runbook omitting any of {`--mode caged` invocation,
  AC-4 gate, rollback} inline violates the "inline the glue" clause (falsified by
  ST-2/ST-3/ST-4);
- *C2 boundary:* the skill instructing the AGENT to run the OS acts or the
  preflight (rather than guiding the operator to) violates the "guide+verify,
  operator executes" clause (falsified by ST-11).

A generic "the runbook should be clear and correct" would be non-falsifiable and
is explicitly rejected; the intent above names concrete boundaries
(inline-set, reference-set, no-duplication, agent-never-executes) a reviewer can
test against the applied files.

---

## Ready-to-apply artifacts

> **For the orchestrator.** Apply each block verbatim to its target path. These
> are Tier-3; under the uncaged default the orchestrator applies them on operator
> instruction. `gleipnir-plan` does not apply them (Tier-0 writer only).

### Artifact 1 — `.gleipnir/decisions/go-caged-runbook.md`

```markdown
# Runbook: go-caged — entering opt-in caged mode

**Status:** durable Tier-3 operational-policy record. The operator-facing front
door for satisfying the caged-mode requirement in
[`operating-posture.md`](./operating-posture.md). Converged + planned:
`../plans/caged-mode-runbook-brainstorm.md` (C1–C5) → `../plans/caged-mode-runbook.md`.

> **What this is.** ONE place that says *how you actually go caged when the
> posture requires it* — assembled from the already-built pieces, not
> re-authored. It **inlines** the short, stable, high-pressure glue (the
> `--mode caged` invocation, the AC-4 go/no-go gate, the uncage/rollback steps)
> and **references** the six volatile, host-specific OS acts. The guiding skill
> `go-caged` walks you through it and verifies each step against the real box.

## When caged mode is REQUIRED (not optional)

Per [`operating-posture.md`](./operating-posture.md), caged mode is a
REQUIREMENT — not a suggestion — for any of the three triggers:

1. **Unattended / autonomous / long-running sessions** (no human watching).
2. **Any session ingesting untrusted external content** (untrusted web fetch,
   third-party repos, pasted/attached content of unknown provenance).
3. **Higher-assurance contexts** — handling secrets, producing attested
   artifacts others rely on, or multi-agent / hosted operation.

Outside these, the default UNCAGED (key-protected floor) posture is legitimate.

## Who does what (the boundary — read this first)

The agent (via the `go-caged` skill) **GUIDES you and VERIFIES each step against
the real box state**. **YOU (the operator) EXECUTE the OS acts** — they need
root (create a dedicated uid, set OS-read-only perms, key mode-600, a
root-elevated launch wrapper) and **no in-framework agent can perform them**.
This is the identical guides-but-operator-applies handoff as
[`../skills/tier3-coach/SKILL.md`](../skills/tier3-coach/SKILL.md) Anti-Pattern 3
(propose/guide, never implement) — reused here by reference, not re-derived.

## Preconditions

- You are on macOS, at the terminal, with `sudo`/root available.
- The repo is present; `OPENCODE_CONFIG_DIR=.gleipnir` (see `.envrc`).
- `.gleipnir/keys/marker.key` exists (the G-3 marker key).
- A free uid/gid chosen for the agent account (verify free first — see the OS
  acts reference).

## Step 1 — OS-layer setup (the six S-2 acts) — REFERENCE, run once

Run acts **(1)–(6)** exactly as written in
[`../plans/s2-activation-control-proposal.md`](../plans/s2-activation-control-proposal.md):

1. Create the dedicated agent uid/gid.
2. `agent-identity.env` single source of truth for the drop target.
3. Ownership / group layout (agent reads source; writes Tier-0/1/2 only).
4. `chmod` the ENFORCEMENT_PATHS subtree OS-read-only to the agent uid.
5. Place the G-3 key mode-600, owner-only.
6. Install the root-elevated launch wrapper `bin/gleipnir-launch`.

> **Source of truth for these six commands = `s2-activation-control-proposal.md`.**
> They are deliberately NOT copied here: they are long, host-specific, and
> occasionally revised, so a second copy would drift. This runbook references
> them; the `go-caged` skill re-reads that file and **verifies each step against
> the real box at execution time**, catching a stale reference. Do these once
> per host; Steps 2–4 below are the repeated operational surface.

## Step 2 — Software-layer: the `--mode caged` invocation (INLINE)

Caged mode binds the session to a genuinely-CLOSED boundary. Run the fail-closed
preflight as the OWNER (setuid to another uid needs root → `sudo`):

    sudo bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --mode caged

Semantics (do not re-derive — this is the built selector,
`src/gleipnir/preflight/`): `--mode caged` **REQUIRES** a CLOSED boundary. A
caged request that does not reach CLOSED returns **REFUSE (exit 1)** — the mode
can **NEVER** manufacture CLOSED (the requested mode never enters the
`all_closed` computation; anti-false-assurance). Do **not** pass
`--override-ack` when going caged: an override is the uncaged dev-mode path, not
caged.

For live sessions there is the launch wrapper installed in act (6):

    sudo bin/gleipnir-launch

> **WARNING — `gleipnir-launch` is NOT a caged gate as currently drafted.** As
> drafted in act (6) of `s2-activation-control-proposal.md`, the wrapper invokes
> the preflight **WITHOUT `--mode caged`** (i.e. at the DEFAULT uncaged mode). On
> a NOT-closed boundary the uncaged/no-override path returns PROCEED_UNCLOSED
> under the neutral uncaged label and **exits 0** — and because the wrapper uses
> `set -e`, exit 0 lets it proceed to drop-and-launch **even when the boundary is
> NOT closed**. It does NOT refuse. Only the **explicit `--mode caged`**
> invocation turns a not-closed boundary into REFUSE (exit 1). Therefore: **always
> run the explicit Step 3 `--mode caged` AC-4 check first as the go/no-go gate;
> treat `gleipnir-launch` as a launch convenience only, never a substitute for
> the gate — UNLESS the wrapper is amended to pass `--mode caged`** (see the
> Cross-artifact note below). Until that amendment lands, the explicit `--mode
> caged` check in Step 3 is the ONLY authoritative caged gate.

## Step 3 — GO/NO-GO acceptance test (AC-4) — INLINE, the gate

Run the no-override preflight and read the verdict:

    sudo bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --mode caged

- **GO (caged):** verdict `closed`, an **empty reasons list**, **exit 0**.
- **NO-GO (NOT caged):** anything else — a non-empty reasons list, or exit 1
  REFUSE. **Do not launch.** Read the reasons, fix the failing OS act, re-run.

`closed` + empty reasons + exit 0 is the ONLY caged go signal. No
CLOSED-with-empty-reasons ⇒ you are NOT caged, full stop. (This is the AC-4 gate
from `../plans/s2-activation.md`.)

## Step 4 — Verify the posture holds

Re-run the explicit Step 3 `--mode caged` AC-4 check as the authoritative gate
for every session that must be caged; `sudo bin/gleipnir-launch` is a launch
convenience, not the gate (see the Step 2 warning), until act (6)'s embedded
preflight call is amended to pass `--mode caged` (Cross-artifact note). The
`go-caged` skill re-verifies acts (1)–(6) against the real box before declaring
you caged — it never self-attests a state it did not observe (a subagent's
`question` cannot reach you; same discipline as tier3-coach Anti-Pattern 5).

## Uncage / rollback (MINIMAL — the routine reversal)

Uncaging is a **Two-Way Door**: the uncaged default is a legitimate posture, not
a failure. To uncage:

- **Just stop requesting caged.** Launch WITHOUT `--mode caged` (or without
  `sudo bin/gleipnir-launch`) and the session runs uncaged. No OS change is
  needed to reverse the software posture.
- **OS perms MAY stay in place.** The dedicated agent uid, OS-read-only
  enforcement paths, and group layout are a **harmless hardened floor** while
  running uncaged (owner ≠ agent-uid, so you are outside the agent cage by
  construction). Leaving them costs nothing and speeds a future re-cage.
- **The key floor STAYS in BOTH modes — NEVER relaxed.**
  `.gleipnir/keys/marker.key` stays `chmod 600` owner-only whether caged or
  uncaged (the retained key-protected floor of the uncaged default,
  `operating-posture.md`). Uncaging must NOT `chmod` it looser.

**Full teardown** (remove the agent uid, relax the OS-read-only perms) is a
**SEPARATE, RARE decommission decision** — used only when retiring the agent
account entirely, NOT the routine uncage. It destroys the hardened floor that
makes re-caging cheap; do it deliberately, as its own operation, never as a
reflex "undo everything".

## Honesty label

**Cooperative-policy-until-AC-4-passes → hard OS boundary once AC-4 passes.**
Until you perform the OS acts and the no-override preflight reports CLOSED with
an empty reasons list, the boundary is cooperative dev-mode, honestly labelled
`G-1 NOT closed (dev-mode)` every session. Once AC-4 passes, caged mode is a real
OS wall: the agent uid cannot write the enforcement subtree, cannot read the
key, and cannot `setuid` back to the owner. The operator ALWAYS knows which mode
a session runs in (`operating-posture.md` honesty invariant).

## Cross-artifact note — the `gleipnir-launch` wrapper needs amending

The `bin/gleipnir-launch` wrapper drafted in act (6) of
`../plans/s2-activation-control-proposal.md` calls the preflight WITHOUT
`--mode caged`, so it launches under the default uncaged mode and does NOT
fail-closed on a not-closed boundary (see the Step 2 warning). **The real fix is
to amend act (6)'s embedded preflight call to add `--mode caged`** so the
wrapper genuinely enforces the caged gate on every launch, matching this
paradigm. That edit is to `s2-activation-control-proposal.md`, which is OUTSIDE
this runbook's authorship — it is a **required companion follow-up**, tracked in
the plan (`../plans/caged-mode-runbook.md`, open item OI-1). **Until the wrapper
is amended, the explicit `--mode caged` AC-4 check in Step 3 is the ONLY
authoritative caged gate** — never rely on `gleipnir-launch` as the gate.

## Assembled pieces (provenance — none re-authored here)

- `--mode caged` selector: `src/gleipnir/preflight/__main__.py` + `boundary.py`.
- Six OS acts (source of truth): `../plans/s2-activation-control-proposal.md`.
- AC-4 go/no-go gate: `../plans/s2-activation.md`.
- Guides-but-operator-applies handoff: `../skills/tier3-coach/SKILL.md`
  (Anti-Pattern 3).
- Paradigm + triggers + honesty invariant + key floor:
  [`operating-posture.md`](./operating-posture.md).
```

### Artifact 2 — `.gleipnir/skills/go-caged/SKILL.md`

```markdown
---
version: "1.0"
name: go-caged
description: "Guide the operator through entering full CAGED MODE — the opt-in high-assurance S-2 lockdown — on request: go caged, cage the system, lock it down, going autonomous/unattended, high-assurance mode, ingesting untrusted content (the operating-posture.md caged requirements). GUIDES + VERIFIES each step against real box state and gates on the AC-4 acceptance test; the OPERATOR executes the OS/root acts (same handoff shape as tier3-coach). Boundary: tier3-coach DETECTS control gaps and PROPOSES controls; go-caged EXECUTES a known, already-designed lockdown. References the go-caged runbook as its single source of truth."
license: MIT
metadata:
  version: "1.0"
  origin: gleipnir
  inherited_by: gleipnir
  inheritance: original
  rationale: "The default-uncaged / opt-in-caged posture (operating-posture.md) makes caged mode a REQUIREMENT for three triggers, but 'go caged' was scattered across four artifacts an operator had to assemble under pressure. This skill is the interactive front door: it walks the operator through the go-caged runbook, verifies each step against the real box, and gates on AC-4 — while the operator (not the agent) performs the root OS acts."
---

> **GLEIPNIR ORIGINAL SKILL.** Sibling to `tier3-coach`, distinct from it.
> **The boundary (named in both skills):** `tier3-coach` DETECTS a control gap
> and PROPOSES a control (Detect → Locate → Propose → Converge → Hand off);
> `go-caged` EXECUTES a KNOWN, already-designed lockdown on operator request —
> the gap is already found and the control already designed (the runbook + the
> six S-2 OS acts exist). Different verbs: *discover-and-propose* vs
> *guide-through-and-verify*.

# go-caged: enter opt-in caged mode

Use this skill when the operator signals intent to enter the required
high-assurance lockdown — **"go caged"**, "cage the system", "lock it down",
"we're going autonomous / unattended", "high-assurance mode", or "we're
ingesting untrusted content" (the three `operating-posture.md` caged
requirements). It walks the operator through the **go-caged runbook** and
verifies each step against the real box.

## Single source of truth

**The runbook [`../../decisions/go-caged-runbook.md`](../../decisions/go-caged-runbook.md)
is this skill's single source of truth.** This skill does **NOT** duplicate the
procedure or the commands — it references the runbook and guides the operator
through it, so there is never drift between two copies.

## The core boundary (why the operator, not the agent, executes)

**The agent GUIDES + VERIFIES; the OPERATOR EXECUTES the OS acts.** The six S-2
acts (create a dedicated agent uid, set OS-read-only enforcement perms, key
mode-600, a root-elevated launch wrapper) need **root** — no in-framework agent
can perform them, and the preflight is out-of-framework and operator-run. This
is the **same guides-but-operator-applies handoff shape as
[`../tier3-coach/SKILL.md`](../tier3-coach/SKILL.md) Anti-Pattern 3** (propose /
guide, never implement), reused here **by reference**, not re-derived. The same
**self-attestation discipline** applies (tier3-coach Anti-Pattern 5): a
subagent's `question` cannot reach the operator, so this skill never records a
box state or a convergence it did not actually observe — it verifies against the
real box and reports what it saw.

## Workflow: Guide → Verify → Gate

Follow the runbook's steps; for each, GUIDE the operator to run it and then
VERIFY the result against the real box.

1. **OS-layer setup (once).** Point the operator to acts (1)–(6) in
   `../../plans/s2-activation-control-proposal.md` (the runbook's Step 1).
   **Verify** each against the real box (uid exists; enforcement paths
   OS-read-only to the agent uid; `keys/marker.key` mode-600). Read the current
   proposal at execution time — this catches a stale reference.
2. **Software layer.** Guide the operator to run the explicit
   `sudo bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --mode caged`
   (no `--override-ack`) as the authoritative go/no-go — this is the ONE command
   that enforces the gate. Remind them that **the explicit `--mode caged`
   invocation** REFUSES (exit 1) if the boundary is not genuinely CLOSED — the
   mode can never manufacture CLOSED. **Do NOT present `sudo bin/gleipnir-launch`
   as an equivalent gate:** as drafted (act (6) of the control-proposal) the
   wrapper calls the preflight WITHOUT `--mode caged`, so on a not-closed
   boundary it exits 0 and launches under the neutral uncaged label — it does NOT
   refuse. Treat the wrapper as a launch convenience only, and always run the
   explicit `--mode caged` check first, until act (6) is amended to pass
   `--mode caged` (runbook Cross-artifact note).
3. **GO/NO-GO gate (AC-4).** Verify the no-override preflight reports `closed`,
   an **empty reasons list**, **exit 0**. That is the ONLY go signal. Anything
   else ⇒ NOT caged; report the failing reasons and stop — do not declare caged.
4. **Uncage (when asked).** Guide the minimal uncage: stop requesting caged
   (drop `--mode caged` / the wrapper). State that OS perms may harmlessly stay
   and **the key mode-600 floor stays in BOTH modes and is never relaxed**. A
   full teardown is a separate, rare decommission decision — never the routine
   uncage.

## Anti-Patterns

**Anti-Pattern 1: Execute the OS acts.** This skill GUIDES + VERIFIES. It never
runs `dscl`/`sysadminctl`/`chmod`/`chown`/`chgrp` or installs the launch
wrapper — those need root and are the operator's action (same as tier3-coach
Anti-Pattern 3).

**Anti-Pattern 2: Run the preflight as an agent.** The preflight is
out-of-framework, operator-run, fail-closed, and never routed into any agent
allowlist. Guide the operator to run it; do not try to invoke it in-framework.

**Anti-Pattern 3: Declare caged without the AC-4 gate.** "Looks set up" is not
caged. Only `closed` + empty reasons + exit 0 is caged. No self-attested state.

**Anti-Pattern 4: Duplicate the runbook.** The runbook is the single source of
truth. Reference it; never fork the procedure or the six OS-act commands into
this skill.

**Anti-Pattern 5: Relax the key floor on uncage.** `keys/marker.key` mode-600
stays in BOTH modes. Uncaging never `chmod`s it looser.

## Resilience

If this skill cannot be loaded, fall back to: open the runbook
`.gleipnir/decisions/go-caged-runbook.md`, guide the operator through its steps,
verify each against the real box, and gate on AC-4. Never execute the OS acts
for the operator, and never declare caged without the AC-4 go signal.

## Status

**Authored, cooperative-policy-until-AC-4.** The lockdown this skill guides
becomes a hard OS boundary only once the operator performs the six S-2 acts and
the no-override preflight reports CLOSED. Until then the session is honestly
labelled uncaged / dev-mode. This skill's discipline — guide + verify, never
execute; gate on AC-4; never self-attest — is what keeps "go caged" honest.
```
