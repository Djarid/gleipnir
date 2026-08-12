# Gleipnir Framework Scaffold — Step 0

This directory (`.gleipnir/`) is the **Gleipnir framework config directory**
and the **step-0 scaffold**: the agent roster, the methodology skills, and the
stage-to-role map that the enforcement machinery will later stand on. It is
deliberately the *basics only* — the cast and their capability skeleton — built
before the substrate design pass.

**Why `.gleipnir/` and not `.opencode/`.** Gleipnir is its own framework with
its own config surface, kept distinct from any target project's `.opencode/`.
opencode is pointed at this directory via the `OPENCODE_CONFIG_DIR` environment
variable (see `../opencode.jsonc` header), which makes opencode search
`.gleipnir/` for `agents/`, `skills/`, `commands/` and `plugins/` exactly as it
would `.opencode/`. This separation also sets up the future G-1 story: the
framework's guard config lives at one known path (`.gleipnir/`) that the S-2
substrate boundary can make agent-unreachable. The subdirectory names are
plural (`agents/`, `skills/`) per opencode's convention.

**Goal reminder.** Gleipnir exists to produce high-quality, efficient outcomes
with the most efficient use of LLM tokens. Every guard, role and model choice
here is in service of that; the enforcement requirements are the *means*, the
cost-per-outcome ledger (G-4d) is the scoreboard.

## Layout

```
.gleipnir/             <- framework config dir (OPENCODE_CONFIG_DIR)
  AGENTS.md            <- this file
  stage-role-map.md    <- net-new S-1.3.1 artifact: pipeline stage -> role
  agents/              <- the 8-role roster (reference floor, deny-by-default)
    orchestrator.md    <- primary; G-5 engine stand-in (sequences, does not plan)
    gleipnir-brainstorm.md <- design explorer; precept-10 convergence gate (Tier-0 writer)
    gleipnir-plan.md   <- planning FROM converged brief; Tier-0 writer of plans/
    gleipnir-code.md   <- implementation (corrected @aetos-code exemplar)
    quality-reviewer.md<- read-only review (spec-review + quality stages)
    git-ops.md         <- sole git/broker holder (single-holder, G-2)
    project-mgr.md     <- issue/MR lifecycle (single namespace)
    notify.md          <- human notification (single namespace)
  skills/              <- K-2 methodology, inherited-and-amended
    README.md          <- inheritance note + the two named deltas
    gotcha/SKILL.md    <- GOTCHA-as-amended (A1 layer2->G-5, A2 prose->S-2)
    atlas/SKILL.md     <- ATLAS near-verbatim (+ layer-2 caveat)
    brainstorm/SKILL.md<- near-verbatim (Converge = precept-10 decision gate)
    decision-frameworks/SKILL.md <- K-3: 10 frameworks + 12 bias detectors
  goals/               <- K-1 goals library (process-as-data)
    manifest.md        <- goals index ("check goals first")
    plan-format.md     <- required plan/brief structure
    methodology.md     <- ATLAS/GOTCHA-ahead-of-planning workflow goal
    README.md          <- what belongs here + the G-5 no-sequencing rule
  decisions/           <- DURABLE decision records (kept)
    substrate-design-pass.md          <- D-1/D-4 resolutions
    runtime-and-deps.md               <- Python + stdlib-only enforcement core
    gleipnir-layout-and-memory-model.md <- G-6 tiers + memory-write pipeline
  memory/              <- Tier 2 USER_REVIEWED: T-1 concept graph (G-6)
  lessons/             <- Tier 2 USER_REVIEWED: graduated Guardrails (G-4c)
  logs/                <- Tier 1 RETRIEVED: session-observer / G-4 bus output
  keys/                <- Tier 3 POLICY: G-3 key + integrity digests [S-2]
  var/tmp/             <- Tier 0 TEMPORARY: scratch (gitignored)
  var/run/             <- framework-process runtime scratch (sandbox cov/cache; gitignored)
  plans/               <- Tier 0 TEMPORARY: session artifacts (disposable)
    README.md          <- lifecycle policy
```

## Trust tiers (spec G-6)

`.gleipnir/` is four trust tiers; authority decreases as writability increases,
and nothing lower may alter anything higher (see
`decisions/gleipnir-layout-and-memory-model.md`):

| Tier | Name | Paths | Writer |
|---|---|---|---|
| 3 | POLICY | `agents/ skills/ goals/ decisions/ stage-role-map.md keys/` | operator only (G-1) |
| 2 | USER_REVIEWED | `memory/ lessons/` | review-gated pipeline |
| 1 | RETRIEVED | `logs/` | framework processes (bus/observer) |
| 0 | TEMPORARY | `plans/ var/tmp/` | bounded agents; disposable |

## Roster (spec S-1.3.1)

Inherited-and-audited from AETOS v4, expressed as opencode agents with
**deny-by-default** permissions (the reference-floor pattern). `gleipnir-code`
is the **corrected exemplar**: `bash: deny` + explicit build/test/lint
allowlist, closing the AETOS v4 enumerable-bypass hole at the roster level.

The broker single-holder clause (G-2): only `git-ops` holds git; every other
role denies it.

**Separation of sequencing, decision-surfacing, and planning.** Three roles,
three jobs: the `orchestrator` *sequences* and judges (does not author plans);
`gleipnir-brainstorm` runs the `brainstorm` stage and *surfaces material design
decisions to the operator* (Clarify→Explore→Propose→**Converge**, the precept-10
gate, using the K-3 decision-frameworks + bias catalogue); `gleipnir-plan` runs
the `plan` stage *from the converged brief* and does **not** decide material
tradeoffs itself. This split exists because, during the framework's own build,
plan-stage design decisions were made inside the planner and validated by the
review gate but never surfaced to the operator to decide — the convergence gate
closes that.

**Tier-0 writers.** `gleipnir-brainstorm` and `gleipnir-plan` are the concrete
operational-zone writers: each may write `.gleipnir/plans/**` (Tier 0) and
nothing else in `.gleipnir/`, proving the per-path least-privilege write grant
from the memory model. All other roster agents still deny all `.gleipnir/`
writes.

## Model sizing

Right-sized to the goal, mapped to aperture-served models. Full table in
`stage-role-map.md`. Principle: **Opus only where judgment is unbounded
(plan); Sonnet once ATLAS + tests bound the work (code/review/test); Haiku for
mechanical roles (git and future gate/PM/notify).** The `code` stage is
deliberately *not* Opus — in a test-first pipeline the test is the arbiter, so
premium spend there buys nothing.

## Guard status — authored, not yet closed

Per spec G-1 terminal-closure semantics, guards are *authored* early and *take
effect* last, verified from outside. Nothing in this scaffold is an enforcing
guard yet. This table is the honest status so step 0 never masquerades as
enforcement.

| Guard | What step 0 provides | Not yet real (later step) |
|---|---|---|
| G-1 (unreachable guards) | Agents deny edits under `.gleipnir/` | S-2 substrate boundary; terminal closure + S-3 preflight |
| G-2 (capability removal) | `bash: deny` + allowlist; git isolated to `git-ops`; **S-2 sandbox built** — `gleipnir-code` build/test runs in an ephemeral container (`bin/gleipnir-sandbox`, `--network=none`, ro source), not the host (T-6 blast radius real) | Broker as separate process/IPC; **E-1 argument policy**; credential isolation; ro-mount of `.gleipnir/` |
| G-3 (unforgeable evidence) | **G-3.1 built**: keyed HMAC marker (`src/gleipnir/verify/`), tests green; orchestrator instructed not to self-declare done | G-3.1 key *boundary-enforcement* (needs S-2 mount + S-3 preflight); G-3.2 engine attestation binding (needs G-5) |
| G-4 (unblindable senses) | — | Typed event bus, ledger, observer, novelty triage |
| G-5 (deterministic orchestration) | `orchestrator` prompt stand-in + stage-role map; engine stub + tests written (test-first) | Engine implementation; G-3.2 attestation edge |
| G-6 (memory not poisonable) | Trust-tiered `.gleipnir/` layout + memory-write model authored (`decisions/`) | Review-gated pipeline, digest verification (G-3.1 applied), S-3 preflight, persistence tests |

## Open seams carried from the spec (Part D, E-1..E-5)

- **E-1** broker argument policy — `git-ops` denies force-push *by pattern*,
  which is exactly the weakness G-2 removes. Real fix needs structural
  argument policy + credential unreachability. **Do not trust the pattern
  denies as sound.**
- **E-2** platform-webhook receiver has no component home.
- **E-3** novelty-triage signal quality.
- **E-4** build-order vs G-3 ranking wording.
- **E-5** methodology amendments authored, bindings (G-5 engine, S-2, G-4c) not built.

## What this scaffold does NOT include

No S-2 container/mount, no G-2 broker/IPC, no G-3 key store, no G-4 bus, no
implemented G-5 engine (stub + tests only), no G-6 memory-write pipeline or
digest verification, no conformance harness wiring. Those are the substrate
pass and later build-order steps. Durable resolutions live in `decisions/`
(`substrate-design-pass.md`, `runtime-and-deps.md`,
`gleipnir-layout-and-memory-model.md`); transient session records live in
`plans/` (`step-0-scaffold.md`, `session-01-atlas-brief.md`,
`session-01-validation.md`, `session-02-*`).

## Session resume

The framework keeps a single resume entry point at
`.gleipnir/plans/SESSION-STATE.md`. Kept here because `.gleipnir/AGENTS.md` is
the only file loaded into every session (via `opencode.jsonc` `instructions:`),
so a resume note here reaches the orchestrator without per-agent opt-in.

- **Orchestrator, at session start:** if `.gleipnir/plans/SESSION-STATE.md` is
  present and describes real prior work, read it first to pick up in-flight
  threads (open items, restart-gated changes, "next" actions) so a fresh session
  can resume without the operator pointing you there manually. If the file is
  absent, or contains only stale-example text with no real prior work (e.g. on a
  fresh clone), treat it as "no session to resume" and proceed normally — it is
  never a hard dependency.
- **It is a pointer, not authoritative.** SESSION-STATE.md is Tier-0, disposable,
  and by its own header **not authoritative**. Use it only to orient and find
  where in-flight work lives; the authoritative homes are `../decisions/`
  (durable decision records) and the spec (Part D E-seams). Never treat its
  contents as ground truth — follow its pointers to the authoritative sources
  before acting on anything material.
- **Subagents: skip this.** If you are a bounded subagent (`gleipnir-brainstorm`,
  `gleipnir-plan`, `gleipnir-code`, `quality-reviewer`, `git-ops`, `project-mgr`,
  `notify`), your delegation is authoritative for your task — you do **not** need
  to read SESSION-STATE.md. Work from the scoped delegation you were handed.
  Reading the resume file wastes context on state your bounded task does not
  need. (**Exception: `session-scribe`.** It *owns and churns* SESSION-STATE.md,
  so it reads the file to maintain it against current disk state — not to resume
  work. This is bookkeeping, not resume, and is expected.)

## Tooling notes

Environment tool quirks that affect every agent — *not* framework policy or
guard semantics. Kept here because `.gleipnir/AGENTS.md` is the only file loaded
into every session (via `opencode.jsonc` `instructions:`), so a note here
reaches every agent without per-agent opt-in.

- **`glob` and dot-prefixed directories (`.gleipnir/`, any `.`-prefixed path).**
  A dot-prefixed directory segment embedded directly in the `pattern` string
  (e.g. `pattern=".gleipnir/agents/*.md"`) returns **zero matches** even though
  the directory is real and named literally — the glob engine applies its
  "skip hidden entries" convention to a segment typed literally in the pattern,
  where it should not. **Fix:** pass the dot-prefixed portion via the separate
  `path` parameter and reduce `pattern` to a bare wildcard — e.g.
  `pattern="*.md", path=".gleipnir/agents"`. "File not found by glob" is **not**
  proof of absence for dot-prefixed paths; when the pattern embeds a
  dot-segment, re-run with `path` before concluding a file is missing.
  (Recorded as L-C16 → L-C17.)
