# Plan: `session-scribe` — a Tier-0-scoped framework-bookkeeping writer + durable resume path

**Tier-0 TEMPORARY session artifact (plan). Disposable after the work merges.**
Authored by `gleipnir-plan` FROM the operator-converged decision (D1–D5, LOCKED
via the orchestrator). This plan **captures** those decisions; it does not
re-open them. The bounded design questions inside the locked frame (model tier,
resume-artifact consolidation, read scope) are decided-and-justified here.

GOTCHA pre-flight ran ahead of this plan (goals checked, plan-format confirmed,
tier discipline confirmed, convergence status confirmed LOCKED). See the chat
turn that produced this file.

---

## 1. Architect

**Problem (one sentence).** Framework-bookkeeping writes — the volatile
session-resume note and the open-seams ledger — have **no reachable
Tier-0-scoped roster writer**, so the orchestrator (which holds no write by
design, L-C9) must round-trip every such write through the unbounded
`/general` escape hatch (L-C10), and a fresh session cannot self-orient because
nothing durable and generic points it at the session-state artifact.

**Users.**
- **The orchestrator delegating bookkeeping** — needs a bounded, capability-safe
  roster actor it can hand a one-verb write ("record session state") to,
  instead of reaching for `/general` (unbounded, per-use operator permission).
- **A fresh session resuming** — needs "check goals first" to lead, via a
  generic durable goal, to a single volatile artifact that orients it (current
  state / built slices / open threads / where to look).

**Measurable success criteria.**
1. The orchestrator can delegate a session-state write to a **Tier-0-scoped
   roster agent** (`session-scribe`) via an ad-hoc bounded delegation —
   **without invoking `/general`** and without holding any write itself.
2. A fresh session following **"check goals first" → the resume goal →
   `plans/SESSION-STATE.md`** orients itself (knows current state, built
   slices, open threads, where to look) with no operator narration.
3. The `session-scribe` **structurally cannot** write any Tier-2 (`memory/`,
   `lessons/`) or Tier-3 (`agents/ skills/ goals/ decisions/
   stage-role-map.md keys/ plugins/ sandbox/ AGENTS.md`) path — its permission
   map has `edit: {"*": deny}` with allow entries ONLY for `.gleipnir/plans/**`
   and `.gleipnir/var/tmp/**`.

**Constraints (all operator-LOCKED).**
- **Tier-3-never for the scribe.** No Tier-3 path ever appears as an `edit`
  allow. (D1, D2, SCOPE.)
- **No Tier-2 writes.** Candidate-lessons stay operator-authored pre-pipeline
  (L-C9, `lessons/README` write-rule) until the G-4c review-gated pipeline
  exists. The scribe never writes `lessons/` or `memory/`. (SCOPE/D2.)
- **No per-session Tier-3 churn.** The resume mechanism's only Tier-3 element (a
  manifest goal) is **generic and static** — authored ONCE, names no
  session-specific content, never touched again. All per-session volatility
  lives in Tier-0 `plans/SESSION-STATE.md`. (D3.)
- **Orchestrator gains no write.** The orchestrator gains only
  `task: session-scribe: allow`; it still holds `edit: deny`, `bash: deny`,
  `webfetch: deny`. (D4.)
- **Do not touch `AGENTS.md`.** (Constraint; also Tier-3.)
- **Bookkeeping is an ad-hoc bounded delegation, not a G-5 pipeline stage.** Not
  added to `stage-role-map.md`. (D4.)

---

## 2. Trace

Artifacts, their tier, their source-of-truth home, and their exact content.

### 2.1 The `session-scribe` roster agent — `.gleipnir/agents/session-scribe.md`

**Tier 3 (POLICY). Operator-authored (hand-off item #1) — NOT writable by any
roster agent, including `gleipnir-code` and `gleipnir-plan`.** The full file to
author, modelled on the proven `gleipnir-plan.md` map:

```markdown
---
description: >-
  Framework-bookkeeping scribe. A Tier-0-scoped roster writer the orchestrator
  delegates ad-hoc bounded bookkeeping to (session-state / resume note, seams
  ledger, scratch). Deny-by-default: writes ONLY .gleipnir/plans/** and
  .gleipnir/var/tmp/** (Tier 0). Never code, git, bash, task, webfetch; never
  any Tier-2 (memory/, lessons/) or Tier-3 (agents/ skills/ goals/ decisions/
  stage-role-map.md keys/ plugins/ sandbox/ AGENTS.md) path. Mechanical role —
  cheap model. Not a G-5 pipeline stage.
mode: subagent
model: aperture-anthropic/anthropic.claude-haiku-4-5
temperature: 0
steps: 15
permission:
  read: allow
  webfetch: deny
  task: deny
  bash: deny
  edit:
    "*": deny
    ".gleipnir/plans/**": allow
    ".gleipnir/var/tmp/**": allow
  write:
    "*": deny
    ".gleipnir/plans/**": allow
    ".gleipnir/var/tmp/**": allow
color: "#4a90d9"
---

# session-scribe (Tier-0 bookkeeping writer)

You are the framework's **bookkeeping scribe**. The orchestrator delegates you
one ad-hoc bounded write at a time (one verb, one object, one verification, one
boundary) — e.g. "record session state: write the resume note to
`.gleipnir/plans/SESSION-STATE.md`." You are **not** a G-5 pipeline stage and
you never sequence work; you write exactly the Tier-0 artifact named in your
delegation and report what you wrote.

## Capability boundary (structural, not honour)

- You may write **ONLY** Tier-0 paths: `.gleipnir/plans/**` and
  `.gleipnir/var/tmp/**`.
- You **cannot** write any Tier-2 (`memory/`, `lessons/`) or Tier-3 (`agents/`,
  `skills/`, `goals/`, `decisions/`, `stage-role-map.md`, `keys/`, `plugins/`,
  `sandbox/`, `AGENTS.md`) path. If asked to, you **refuse** and say the write
  is above your tier and must be routed to the operator escape hatch (Tier-3)
  or the review-gated pipeline (Tier-2). Your permission map denies it anyway —
  the refusal is you diagnosing the wrong-writer path, not you being trusted.
- You hold no `bash`, no `task`, no git, no `webfetch`. You `read` (broadly, to
  know current state) and you write Tier-0. Nothing else.

## Verify-against-disk / never-fabricate discipline (L-C4, L-C8)

- Before writing session state, **read the current disk state** you are about to
  summarise (the plans/, decisions/, relevant artifacts). Never state a slice is
  "built" or a seam is "closed" unless disk confirms it.
- After writing, **re-read your own output** and confirm it landed; report the
  path and a one-line summary of what changed. Never report a write you did not
  perform (L-C8) and never trust that a write succeeded without checking disk
  (L-C4).
- You record only what you can verify. Unknown/unverified items are marked as
  such ("unverified"), never asserted as fact.

## SESSION-STATE.md format (the resume artifact you own)

`.gleipnir/plans/SESSION-STATE.md` (Tier-0). Keep it short, current, and
truthful. Structure:

    # Session state (Tier-0, volatile — the resume entry point)
    _Last updated: <date> · session <id> · churned by session-scribe_

    ## Current state
    <one paragraph: where the build is right now>

    ## Built slices (verified against disk)
    - <slice> — <commit / artifact> — <what it proves>

    ## Open threads / next
    - <the next actionable thing(s)>

    ## Open seams
    <the open-seams list — folded in from / absorbing the old
     session-seams-ledger.md; NOT authoritative (decisions/ + spec Part D are)>

    ## Where to look
    - decisions/ : durable decision records (authoritative)
    - plans/     : this + other Tier-0 session artifacts
    - spec Part D: E-seams

You churn this file every session. It is disposable and authority-free (Tier 0);
the authoritative homes remain `../decisions/` and the spec.
```

**Design decision (a) — model tier: Haiku. DECIDED (bounded).** This role is
mechanical: read disk, summarise into a fixed-format Tier-0 markdown file,
verify. No unbounded judgment. Per the model-sizing principle (Opus only where
judgment is unbounded; Haiku for mechanical roles) Haiku is right — cheap, and
correctness here is a conformance-of-format + verify-against-disk discipline,
not model IQ. Matches `git-ops`' Haiku sizing for the same reason.

**Design decision (c) — `read: allow` broad; `edit`/`write` scoped to Tier-0.
DECIDED (bounded, and safe).** The scribe must read broadly to know current
state (which slices are built, which seams are open, what decisions exist).
**Read is not the threat model G-6 addresses — WRITE is.** Tier-3 *read* is
fine (the danger is a lower tier *altering* a higher tier, not observing it);
only Tier-3/Tier-2 *write* is denied. So `read: allow`, with `edit` and `write`
both `{"*": deny}` + Tier-0 allow. (Both `edit` and `write` are pinned so a
create-new-file path is covered as well as an edit-existing path.)

### 2.2 Orchestrator task-allowlist addition — `.gleipnir/agents/orchestrator.md`

**Tier 3 (POLICY). Operator-authored (hand-off item #2).** Add ONE line to the
existing `task` allowlist (between the roster entries), and change nothing else
— the orchestrator still holds `edit: deny`, `bash: deny`, `webfetch: deny`:

```yaml
  task:
    "*": deny
    gleipnir-brainstorm: allow
    gleipnir-plan: allow
    gleipnir-code: allow
    quality-reviewer: allow
    git-ops: allow
    project-mgr: allow
    notify: allow
    session-scribe: allow          # <- the exact line to add (D4)
```

The orchestrator gains the ability to *delegate to* `session-scribe`; it gains
NO write of its own. (D4, and consistent with L-C10's fix pattern: give the
orchestrator a reachable *writer* to delegate to, rather than bouncing work to
the human — here a Tier-0-scoped roster writer, so `/general` is no longer
needed for bookkeeping.)

### 2.3 Manifest resume goal — `.gleipnir/goals/manifest.md`

**Tier 3 (POLICY). Operator-authored (hand-off item #3).** Add ONE generic,
static row to the "Available goals" table. Exact wording (names no
session-specific content, so it is authored once and never churned — D3):

Table row to add:

```markdown
| Session resume (orient at session start) | `resume.md` | workflow |
```

The goal itself is generic. Whether it is a one-line manifest note or a small
`goals/resume.md` file, its **content must be generic and static**, e.g.:

> **Session resume.** At session start, read the current session-state artifact
> `../plans/SESSION-STATE.md` to orient — current state, built slices, open
> threads, and where to look. It is a Tier-0 volatile artifact (the scribe
> churns it); the authoritative homes are `../decisions/` and the spec. If it is
> absent, there is no prior session state to resume.

The goal references the *path* `plans/SESSION-STATE.md`, not any content — so
per-session churn happens entirely in Tier-0, and this Tier-3 goal is touched
exactly once. (D3.)

### 2.4 `.gleipnir/plans/SESSION-STATE.md`

**Tier 0 (TEMPORARY).** The volatile resume artifact, format per §2.1. **Written
by the `session-scribe` itself once it exists** (its native Tier-0 grant), or by
`/general` in the same bootstrap pass (see §2.5 circularity). Churned every
session thereafter by the scribe.

**Design decision (b) — SESSION-STATE.md SUPERSEDES `session-seams-ledger.md` as
the single resume entry point; absorbs its open-seams list. DECIDED (bounded).**
Rationale: one resume artifact is better than two the fresh session must know
to consult. `session-seams-ledger.md` is already Tier-0, explicitly disposable,
and explicitly NON-authoritative (its own header points to `decisions/` + spec
Part D as the real homes). Its open-seams list becomes the **"Open seams"**
section of `SESSION-STATE.md`. On the first churn, the scribe copies the current
open-seams list into `SESSION-STATE.md` and the old ledger may be deleted (or
left as a tombstone pointing at `SESSION-STATE.md`). This keeps the resume path
single-entry: goal → `SESSION-STATE.md` → everything. (Coexistence was the
alternative; rejected because two overlapping Tier-0 resume files invite drift
and a fresh session would not know both exist.)

### 2.5 Integrations map

- **`goals/manifest.md` → `plans/SESSION-STATE.md`**: the resume goal is the
  durable, generic pointer; the artifact is the volatile target. The only cross-
  tier link, and it is by *path* (static), never by content.
- **orchestrator → session-scribe** (`task` grant): the delegation edge. One
  verb/object/verification/boundary per call (L-C3), e.g. "record session
  state: write the resume note to `plans/SESSION-STATE.md`; verify it landed."
- **session-scribe → `plans/**` + `var/tmp/**`**: the only write edges the
  scribe has.
- **A→C graduation (named end-state, NOT built now):** later, scribe delegations
  become plugin-hosted typed bookkeeping tool calls (Option C). The **tier grant
  is unchanged** across A→C — still Tier-0-only write. Captured for the durable
  decision record, deferred here (D5).

### 2.6 Edge cases

- **First-run absence:** `SESSION-STATE.md` does not exist yet → the resume goal
  says "if absent, no prior state to resume." No error, no fabrication.
- **Bootstrap circularity (honest):** the scribe cannot be *used* until it is
  *authored*, and authoring it is a Tier-3 write no roster agent can do. So the
  first-slice Tier-3 items (§2.1–2.3) are authored **out-of-roster** (operator
  escape hatch / `/general` with per-use operator permission). Only *after*
  `session-scribe.md` exists can the scribe write the first `SESSION-STATE.md`.
  Alternatively `/general` writes the first `SESSION-STATE.md` in the same
  bootstrap pass. Thereafter all Tier-0 bookkeeping routes to the scribe.
- **Wrong-writer request:** if the orchestrator (or anyone) hands the scribe a
  Tier-2/Tier-3 write, it fails by capability (map denies it) AND the scribe
  refuses and names the correct writer (L-C9 refusal pattern).
- **Stale/false state:** guarded by the verify-against-disk discipline (L-C4) —
  the scribe never marks a slice built or a seam closed without disk
  confirmation, and never fabricates (L-C8).
- **`session-seams-ledger.md` after absorption:** disposable; delete or leave a
  one-line tombstone pointing at `SESSION-STATE.md`. Not authoritative either
  way.

---

## 3. Link (validated before building)

- **Proven permission-map template exists:** `gleipnir-plan.md` demonstrates the
  exact `edit: {"*": deny, ".gleipnir/plans/**": allow}` pattern in production —
  the scribe extends it with one more Tier-0 allow (`var/tmp/**`) and a `write`
  block mirroring `edit`. Nothing novel in the enforcement path.
- **Tier model confirmed:** `decisions/gleipnir-layout-and-memory-model.md`
  fixes `plans/` + `var/tmp/` as Tier-0 (freely writable, disposable) and the
  Tier-3 set as operator-only. The scribe's grant sits entirely inside Tier-0.
- **Orchestrator task-allowlist shape confirmed:** `orchestrator.md` already
  uses `task: {"*": deny, <roster>: allow}` — adding one line is a known-safe
  edit; the orchestrator's `edit: deny` floor is untouched (L-C9).
- **Read-vs-write threat model confirmed:** the memory-model doc is explicit
  that the invariant is "nothing lower may *alter* anything higher" — a *write*
  constraint — so broad `read` is safe (design decision (c)).
- **Who-writes-Tier-3 confirmed:** roster agents (incl. `gleipnir-code`,
  `gleipnir-plan`) all deny `.gleipnir/**` Tier-3 writes; only the operator
  escape hatch authors POLICY (L-C9, L-C10). This is why §2.1–2.3 are hand-offs.
- **No code dependency:** this slice introduces no runtime code, no new module,
  no test target. It is config (2 Tier-3 edits) + 1 Tier-3 goal + 1 Tier-0
  markdown artifact. Nothing to compile, nothing to import.

---

## 4. Assemble (build order)

Most of this slice is **Tier-3 authoring (out-of-roster)** — not
"agent-buildable" by the pipeline. Order:

1. **[Tier-3 hand-off #1]** Author `.gleipnir/agents/session-scribe.md` exactly
   as §2.1 (deny-by-default; Tier-0-only `edit`+`write`; `read: allow`; Haiku;
   the body incl. verify-against-disk discipline and the explicit Tier-0-only /
   refuse-anything-else statement).
2. **[Tier-3 hand-off #2]** Edit `.gleipnir/agents/orchestrator.md` to add the
   single line `session-scribe: allow` to the `task` allowlist (§2.2). Change
   nothing else; orchestrator keeps `edit: deny`.
3. **[Tier-3 hand-off #3]** Edit `.gleipnir/goals/manifest.md` to add the generic
   static resume-goal row + wording (§2.3). Author once; never churn.
4. **[Tier-0 — scribe or `/general` bootstrap]** Write the first
   `.gleipnir/plans/SESSION-STATE.md` (§2.1 format), **absorbing** the current
   open-seams list from `session-seams-ledger.md` (§2.4 decision (b)). Prefer
   the scribe once it exists (proves the path end-to-end); `/general` acceptable
   in the same bootstrap pass. Then delete/tombstone the old seams ledger.
5. **[Verify]** Run the mock-resume walkthrough (§5) and the permission-map
   conformance checks (§5).

**Testable code?** Essentially none — this is config + a roster agent + a goal +
a markdown artifact. The "test" is a **conformance check** that the scribe's
permission map denies Tier-2/Tier-3 writes, which is verified **structurally** by
the deny-by-default map plus the existing preflight/runtime enforcement floor.
If warranted, this can be a named conformance assertion (§5, the
no-roster-agent-grants-Tier-3-edit assertion extended to cover `session-scribe`).

---

## 5. Stress-test (acceptance checks)

Concrete, checkable:

1. **Scribe map has NO Tier-2/Tier-3 allow.** `grep` `agents/session-scribe.md`:
   under `edit` and `write`, the ONLY allow entries are `.gleipnir/plans/**` and
   `.gleipnir/var/tmp/**`; `"*": deny` is present in both. No occurrence of
   `agents/`, `skills/`, `goals/`, `decisions/`, `stage-role-map.md`, `keys/`,
   `plugins/`, `sandbox/`, `AGENTS.md`, `memory/`, or `lessons/` as an allow.
2. **Scribe reads broadly, writes narrowly.** `read: allow` present; `bash`,
   `task`, `webfetch` all `deny`.
3. **Orchestrator gains delegation, not write.** `orchestrator.md` shows
   `session-scribe: allow` under `task`; `edit: deny`, `bash: deny`,
   `webfetch: deny` unchanged; no new `edit`/`write` allow anywhere.
4. **Resume goal is generic/static.** The manifest goal names only the *path*
   `plans/SESSION-STATE.md` and generic orientation instructions — **zero**
   session-specific content — so it needs no per-session edit (no Tier-3 churn).
5. **SESSION-STATE.md is Tier-0.** Lives under `.gleipnir/plans/`; header marks
   it volatile/disposable and non-authoritative.
6. **Fresh-session mock resume walkthrough (described):** a reader that "checks
   goals first" opens `goals/manifest.md` → sees the Session-resume row → reads
   the resume goal → reads `plans/SESSION-STATE.md` → learns current state,
   built slices, open threads, and where to look. It reaches an oriented state
   with no operator narration. If `SESSION-STATE.md` is absent, the goal tells it
   there is no prior state — clean, no error.
7. **Verify-against-disk / never-fabricate (L-C4/L-C8):** the scribe's body
   requires reading disk before summarising and re-reading its output after
   writing; unverified items are marked "unverified," never asserted. A review
   of a scribe-produced `SESSION-STATE.md` should find every "built"/"closed"
   claim disk-confirmable.
8. **Named conformance assertion (warranted):** extend the existing
   "no roster agent's permission map grants a Tier-3 `edit`/`write`" check to
   include `session-scribe` — an assertion that `session-scribe`'s allow-set,
   intersected with the Tier-3 path set, is empty. This makes the Tier-3-never
   guarantee machine-checkable rather than prose-only.

---

## 6. Execution Workflow (for the implementing actors)

**This slice's implementing actor is NOT a roster pipeline agent for the Tier-3
items.** Route as follows:

- **Tier-3 hand-offs (§2.1, §2.2, §2.3):** authored **via the operator escape
  hatch (`/general` or the operator's editor), with per-use operator
  permission** — NOT by any roster agent, NOT by `gleipnir-code`, NOT by
  `gleipnir-plan`. This is G-1 / the Tier-3 operator-only write path (L-C9,
  L-C10). The orchestrator's role here is to *diagnose* "these three are Tier-3,
  route to the escape hatch," never to bounce them to the human as manual labour
  and never to attempt them itself (it holds no write).
- **First `SESSION-STATE.md` (§2.4):** once `session-scribe.md` exists, the
  orchestrator issues an ad-hoc bounded delegation to `session-scribe`
  ("record session state: write the resume note to `plans/SESSION-STATE.md`,
  absorbing the current open-seams list; verify it landed and report the path").
  Acceptable alternative: `/general` writes it in the same bootstrap pass. This
  is the moment the bootstrap circularity (§2.6) resolves.
- **Delegation shape thereafter:** every future bookkeeping write is a single
  ad-hoc bounded delegation to `session-scribe` — one verb, one object, one
  verification, one boundary (L-C3). It is **not** a G-5 pipeline stage and is
  **not** added to `stage-role-map.md` (D4).
- **Verification before "done":** the orchestrator verifies the scribe's write
  against disk (L-C4) — never trusts the self-report — before considering the
  bookkeeping task complete (L-C8).

### Durable decision to persist (flagged for the operator)

**`/.gleipnir/decisions/session-scribe.md` (Tier 3, operator-authored).** This
plan is Tier-0 and disposable; the following must be captured durably by the
operator, because the scribe's boundary and the A→C path are choices later work
depends on. The decision record should capture:
- **D1** — `session-scribe` roster sub-agent, deny-by-default, `edit`/`write`
  allow ONLY Tier-0 (`plans/**`, `var/tmp/**`); the full Tier-3-never guarantee.
- **D2/SCOPE** — writes Tier-0 only; never Tier-2 (`lessons/`, `memory/`) —
  candidate-lessons stay operator-authored pre-pipeline until the G-4c
  review-gated pipeline exists; never any Tier-3 path.
- **D3** — the resume mechanism: one generic, static manifest goal +
  volatile `plans/SESSION-STATE.md`; no per-session Tier-3 churn.
- **D4** — bookkeeping is an **ad-hoc bounded delegation, NOT a G-5 pipeline
  stage** (the "bookkeeping-is-not-a-stage" ruling); the orchestrator gains
  `task: session-scribe: allow` and NO write of its own.
- **D5** — first slice = the three Tier-3 authoring items + the first
  `SESSION-STATE.md`; **Option C (plugin-hosted typed bookkeeping tools)
  deferred**, with the **A→C graduation path** (scribe delegations become tool
  calls; **tier grant unchanged**) named as the end-state.
- The **model-tier**, **read-scope**, and **supersede-vs-coexist** decisions
  from §2.1/§2.4 (Haiku; broad read / Tier-0 write; SESSION-STATE.md supersedes
  and absorbs the seams ledger).

`gleipnir-plan` cannot write `decisions/` (Tier 3); this is named precisely so
the operator can persist it. No material tradeoff is re-opened here — D1–D5 are
LOCKED; the bounded sub-decisions are recorded, not re-decided.
