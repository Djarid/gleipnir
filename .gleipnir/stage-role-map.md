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
  itself, or the root opencode config `opencode.jsonc` / `**/opencode.json`
  (it loads this map via `instructions`, gates the MCP brokers via `enabled`,
  and sets `default_agent`); **or**
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
claims to. The pattern/target in `evidence` must be the **same over-broad form
named in `over_broad_form_checked`** (and, where applicable, the same file as
`grant`) — grepping for an unrelated pattern is reproducible but proves nothing
and MUST be rejected. (E.g. a `lessons/**`-absent claim requires `evidence` that
greps for `lessons/**` specifically, not some other string.)

An enforcement-bearing prose/config plan may **not** report SUCCESS unless (i)
two distinct pass verdicts exist, (ii) the negative-check attestation is present
with all fields and `attested_by ≠ author`, (iii) every `evidence` field cites a
reproducible artifact, not a narrative, and (iv) each `evidence` artifact tests
the specific form named in that row's `over_broad_form_checked` (not an unrelated
pattern).
