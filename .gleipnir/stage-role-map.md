# Stage-to-Role Map

**The net-new artifact required by spec S-1.3.1.** The roster is
inherited-and-audited from AETOS v4; this map is the one piece authored fresh,
because G-5 does not exist in AETOS and its pipeline states must bind to
concrete roles. It is constrained to bind only to roles that exist in the
roster (`.gleipnir/agents/`).

**Status: authored, not yet closed.** In the finished framework the G-5
deterministic engine reads this binding and emits delegations in code. Today
the `orchestrator` agent follows it as prompt-level guidance. When the engine
lands, this file becomes the engine's configuration rather than an agent
instruction.

## Methodology runs ahead of the pipeline

ATLAS and GOTCHA are prerequisites to planning, not stages within it. Before
the `brainstorm`/`plan` stages produce anything, ATLAS Architect/Trace
(`skills/atlas/SKILL.md`) and GOTCHA layering (`skills/gotcha/SKILL.md`) frame
the problem. A plan drafted without them is unbounded — and an unbounded plan
is what forces premium-model spend downstream, against the framework's goal.

## The map

Pipeline (spec G-5): `brainstorm -> plan -> spec-review -> test -> code -> quality -> git -> gate`

| Stage | Bound role | Model tier | Rationale (goal: quality-efficient outcomes per token) |
|---|---|---|---|
| brainstorm | gleipnir-brainstorm | Opus (temp raised) | Divergent framing + the precept-10 human-decision gate: material tradeoffs (via the K-3 decision-frameworks analysis) converge on the operator BEFORE planning. A dedicated role, not the planner |
| plan | gleipnir-plan | **Opus** | Unbounded judgment; ATLAS Architect/Trace. Plans FROM the converged brief; does NOT decide material tradeoffs itself (those are the brainstorm gate's). The one place premium pays for itself |
| spec-review | quality-reviewer | Sonnet | Judgment bounded by the spec as rubric |
| test | gleipnir-code | Sonnet (candidate for uplift) | In test-first, tests *define* correctness — the correctness arbiter. Watch for uplift to Opus if test design proves weak |
| code | gleipnir-code | **Sonnet** | Bounded by plan + ATLAS-Assemble order + pre-written tests. The test is the arbiter, not model IQ — do not pay Opus here |
| quality | quality-reviewer | Sonnet | Blast-radius review against the plan; catching defects here prevents expensive reverts |
| git | git-ops | **Haiku** | Mechanical, structured tool calls; the sole broker role |
| gate | orchestrator | Opus (reads attestation) | Reads authoritative evidence (future G-3.2) and emits pipeline state; near-deterministic once the engine exists |

## Model-sizing principle

Spend the strongest model only where judgment is **unbounded** and errors
compound: **plan**. Once ATLAS and pre-written tests bound the work, the
**code** stage drops to Sonnet — the test, not the model's capability, is what
guarantees correctness (Axiom 1). Value shifts toward **test authoring**,
since tests carry the correctness burden in a test-first pipeline. Mechanical
roles (git, and the future gate/PM/notify calls) run on Haiku. Concrete model
IDs are declared per agent in `.gleipnir/agents/*.md`, mapped to the
aperture-served models available in this environment.

## Binding rules (S-1.3.1)

- A stage may be routed **only** to its bound role. No role performs a stage
  it is not bound to.
- **The orchestrator sequences; it does not perform stages.** Planning
  (brainstorm/plan) is delegated to `gleipnir-plan`, not authored by the
  orchestrator. The orchestrator's only bound stage is `gate` (reading
  attestation and emitting pipeline state), which is near-deterministic; every
  other stage is delegated to its bound role.
- The `git` stage binds to `git-ops` and only `git-ops` — the broker
  single-holder clause. No other role holds git or credentials.
- One verb, object, verification and boundary per delegation; exploration and
  action are separate delegations (task-decomposition isolation).

## Prose/config-only track (blast-radius split)

**Status: ratified (Approach B), operator-applied.** A specialisation of the
map above: some plans have **no executable artifact and no test arbiter** — they
touch only prose and declarative config. The default is still the full 8-stage
pipeline; this track is the scoped exception, and it is **split by blast
radius** so the highest-consequence change class is never under-reviewed (L-C7).
The route is **mechanically computable** from a plan's declared touched-path set
`P` — the future G-5 engine routes on it with no per-plan LLM judgment.

### Axis 1 — eligibility gate (the disqualifier)

A plan is track-eligible **only if `P` contains zero executable/interpreted
artifacts.** If any path in `P` matches the disqualifier set `X`, the plan runs
the **full 8-stage pipeline**, no matter how small the code portion:

> `X` = `src/**`, `tests/**`, `hooks/**`, `bin/**`, `**/Makefile`, `**/*.mk`,
> `**/Containerfile*`, `.github/**`, any standalone `**/*.yml`/`**/*.yaml`, any
> `**/*.sh|*.bash|*.py|*.js|*.ts|*.rs|*.go`, any file with mode `+x` or an
> interpreter shebang in added content.

Rationale: a Makefile/CI file/hook *runs*; distinguishing inert data-YAML from
build-executed YAML is not reliably grep-able, so standalone YAML is disqualified
safe-side (integrity > efficiency). This kills the "mostly config but one hook"
trap. Note: `opencode.jsonc`/`opencode.json` are NOT in `X` (declarative, not
executable) but ARE enforcement wiring — they are routed hardened via Axis 2(a),
not disqualified.

### Axis 2 — routing within the eligible set

A track-eligible plan is **enforcement-bearing** (→ hardened path) if EITHER:

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
- **(b) content rule:** an added/changed line matches a grant/enforcement
  pattern `G`, in EITHER its YAML/frontmatter form OR its JSON(C) form:
    - YAML: a `permission:` or `tools:` block, or a capability line
      (`edit|write|task|bash|webfetch` with `allow`/`deny`);
    - JSON(C): a JSON-quoted enforcement key —
      `"permission"|"tools"|"enabled"|"instructions"|"default_agent"|"subagent_depth"|"mcp"`;
    - a new/edited row in this file's binding tables;
    - a keyed digest line under `keys/**` matching `^[0-9a-f]{64}\b`
      (redundant with Axis 2(a); retained as documentation).

Otherwise the plan is **low-consequence prose** (→ light path): paths confined
to `.gleipnir/goals/**`, `.gleipnir/decisions/**` prose, `.gleipnir/plans/**`,
`.gleipnir/logs/**`, `**/*.md` docs, READMEs, comments, with no `G`-pattern
match. (This is the same construction as G-6's trust tiers: *trust is a property
of the path, encoded in code* — see
`decisions/gleipnir-layout-and-memory-model.md`. Axis 2(b) is a content
tripwire: a match forces the hardened path; an absence proves nothing, because
Axis 2(a) already routes every enforcement *path* to the hardened side.)

### Light path (low-consequence prose)

Stages collapse to a **single spec-review pass** by `quality-reviewer`
(`spec-review` and `quality` rubrics run together, since there is no
post-implementation artifact to blast-radius-review); `test`/`code`/`git`/`gate`
carry an attested **"N/A — no executable artifact"** transition. This is the
precedent from `plans/lesson-escalation-process.md`, now ratified **only** for
this low-blast subset.

### Hardened path (enforcement-bearing config)

The two rubrics **do NOT fuse.** `quality-reviewer` runs them as **two separate
passes**, each with its own recorded verdict:

1. **Spec-conformance** (rubric = the plan/spec): `SPEC-CONFORM: PASS/FAIL`.
2. **Blast-radius / false-success** (rubric = *how could this be wrongly
   green?*): an adversarial pass whose job is to find the over-broad / false-
   CLOSED path (L-C7). A single fused "looks fine" verdict is a non-conformance.

Plus an **explicit negative-check attestation** — replacing "fixtures ran once"
— produced by `quality-reviewer` (never self-attested by the author, L-C8), one
row per grant/enforcement change, each asserting: the exact grant, its intended
(narrowest) scope, the specific **over-broad form checked-for-and-ruled-out**,
the **evidence**, the explicit **negative result** ("`<over-broad form>` is
NOT present"), and `attested_by`. Example: for a `lessons/` write grant, the
attestation must assert a `lessons/**` glob is **NOT** present where a single
named file is intended.

**Substance rule:** the `evidence` field must cite a **concrete, reproducible
artifact** — literal command+output (`grep`/`diff`), a digest comparison, or a
byte-for-byte quote of the applied line — NOT a narrative assertion (e.g.
"reviewed it, looks correct"). A schema-complete attestation whose evidence is
substantively vague is the exact false-success L-C7 exists to catch and MUST be
rejected at spec-review.

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

**Post-change-state rule:** the `evidence` MUST be captured against the
**applied / post-change state** of the target file — the state after the plan's
edit is applied — not a stale or pre-change copy. This applies to **all**
evidence forms: a `grep`/`diff` MUST be run against the post-apply file, a
digest MUST be computed over the post-apply bytes, and a byte-for-byte quote
MUST be of the applied line. (The quote form already implies this; this rule
makes it explicit for the grep/diff/digest forms, where a pattern match against
the wrong file *version* would otherwise satisfy the substance and
correspondence rules while proving nothing about what was actually applied.)

An enforcement-bearing prose/config plan may **not** report SUCCESS unless (i)
two distinct pass verdicts exist, (ii) the negative-check attestation is present
with all fields and `attested_by ≠ author`, (iii) every `evidence` field cites a
reproducible artifact, not a narrative, (iv) each `evidence` artifact tests the
specific form named in that row's `over_broad_form_checked`, in the same file
named in that row's `grant` (not an unrelated pattern and not the wrong file),
and (v) every `evidence` artifact was captured against the applied / post-change
state of the target file.

### Cognition layer (AETOS two-gate mechanism — composed, not parallel)

**Status: authored, operator-applied. See `decisions/cognition-layer.md`.**
The cognition layer verifies reasoning was actually done. It is realised as
two gates and COMPOSES with the machinery above — it adds no new guard and
does NOT amend G-5 (it lives in the plan-format artifact-shape layer + this
review-rubric layer).

- **Gate 1 (design-time)** is the required **Design Principles** section in
  `goals/plan-format.md`. Its form is routed in THREE cases, keyed on the SAME
  Axis-1 set `X` above plus one author-declared/reviewer-checkable sub-question
  ("does the touched `X`-member have class/function/module structure?"):
  (i) OOP/functional code (`P ∩ X ≠ ∅`, has OOP structure) → SOLID+DRY+SRP+
  Design Intent; (ii) executable-but-non-OOP (`P ∩ X ≠ ∅`, a Makefile / CI
  YAML / shell / `bin/**` / `hooks/**` / shebang-config) → DRY+Design Intent,
  SOLID/SRP attested `N/A — no object/function structure`; (iii)
  prose/config-only (`P ∩ X = ∅`) → Design Intent only, SOLID/DRY/SRP attested
  `N/A — no executable artifact`. ONE predicate (`X`), one refinement — no
  second classifier. The **Design Intent MUST be specific and falsifiable** (a
  named responsibility/boundary/constraint, not a generic quality aspiration),
  per the anti-vacuity rule mirroring the SUBSTANCE rule above.
- **Gate 2 (review-time)** composes into THIS section's two passes, not as new
  passes:
  - SOLID/DRY/SRP is a checklist **dimension of the "Blast-radius /
    false-success" pass** (2), Important severity, scoped by the Gate-1
    three-case routing (full SOLID/DRY for case (i); DRY-only for case (ii);
    skipped for case (iii)).
  - The **spec-vs-implementation cross-check is TWO distinct checks bound to
    two stages** (the implementation does not exist at spec-review):
    - at **spec-review** it is the **intent-quality check** — a **sub-check of
      the "Spec-conformance" pass** (1) verifying the Design Intent is itself
      specific/falsifiable and not a vacuous aspiration (rejected if vacuous,
      ties to the anti-vacuity rule);
    - at **quality** it is the **honour check** — does the applied
      implementation honour the stated Design Intent/principle? A divergence is
      **Important** severity: it **blocks the `git` stage unless explicitly
      acknowledged by the operator** (the reviewer never self-clears it, L-C8).
    For a prose/config-only-track plan (single collapsed spec-review pass, no
    separate post-implementation stage) both checks run once at that pass
    against the applied edit. The cross-check applies to EVERY plan including
    light-path plans (it is the genuineness proxy).
  - **`[D]`/`[J]` tags** annotate the evidence basis of every finding and every
    negative-check attestation `evidence` entry (`[D]` = tool-produced, e.g.
    `bin/gleipnir-sandbox`; `[J]` = judgment). This formalises the existing
    substance rule; it is not a second mechanism.

**Recording an operator acknowledgement.** A divergence found at `quality` is
Important and blocks `git` until the operator acknowledges it. Because plans
are Tier-0 and disposable, the acknowledgement is NOT recorded only in the
plan: the divergence escalates to the operator, who records the accepted
divergence in the durable decision record (`decisions/cognition-layer.md` or
the change's own decision record). The disposable plan may note it, but the
authoritative home is the Tier-3 decision record.

#### Per-stage cognition binding (coverage — Approach D's documented half)

Every artifact-producing stage's cognition is either an enforced shape or an
explicitly-documented existing binding, so the coverage question cannot
re-surface as a phantom gap (L-C14; the gotcha-loading precedent):

| Stage | Cognition binding | Enforced by |
|---|---|---|
| brainstorm | Clarify → Explore → Propose → Converge + `## Decision Analysis` | `skills/brainstorm` shape + precept-10 gate |
| plan | ATLAS sections + Decisions index + **Design Principles** | `goals/plan-format.md` Validation (Gate 1) |
| spec-review | Spec-conformance pass **incl. the cross-check's intent-quality sub-check** (Design Intent is specific/falsifiable, not vacuous) | this section (Gate 2) |
| test | The pre-written test IS the correctness shape | test-first pipeline (Axiom 1) — bounded, no new shape |
| code | Bounded by plan + ATLAS-Assemble order + pre-written test | the test is the arbiter — bounded, no new shape |
| quality | Blast-radius pass **incl. SOLID/DRY dimension** + the cross-check's **honour check** (applied impl. honours stated intent) | this section (Gate 2) |

`test` and `code` intentionally carry NO new cognitive shape: their cognition
is already bounded by the pre-written test (documenting the existing binding,
per Approach D — NOT inventing a redundant shape).

#### Guard-vocabulary note

Cognition-genuineness is a plan-format-shape + review-rubric concern. It is
**NOT a new guard** and does **NOT amend G-5**: no adversary forges a reasoning
process (the G-1..G-6 guards each close an adversarial hole); a busy LLM fills
a section perfunctorily, which is a quality concern answered by review, not by
a guard. Its only mechanically-enforceable part (shape presence) is already
the `plan-format.md` Validation + G-5 completion edge; its non-mechanical part
(genuineness) is irreducibly review — the cross-check is its enforceable proxy.

#### Model-sizing linkage

The cross-check is what makes the "Opus-at-plan assumes good framing" spend
(see "Model-sizing principle" above) *safe* rather than merely *assumed*: it
converts "we assume the framing is good" into "framing genuineness is an
explicit, recorded review obligation whose divergences block the git stage."
