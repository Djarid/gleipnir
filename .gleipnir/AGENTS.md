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
  agents/              <- the 6-role roster (reference floor, deny-by-default)
    orchestrator.md    <- primary; G-5 engine stand-in
    gleipnir-code.md   <- implementation (corrected @aetos-code exemplar)
    quality-reviewer.md<- read-only review (spec-review + quality stages)
    git-ops.md         <- sole git/broker holder (single-holder, G-2)
    project-mgr.md     <- issue/MR lifecycle (single namespace)
    notify.md          <- human notification (single namespace)
  skills/              <- K-2 methodology, inherited-and-amended
    README.md          <- inheritance note + the two named deltas
    gotcha/SKILL.md    <- GOTCHA-as-amended (A1 layer2->G-5, A2 prose->S-2)
    atlas/SKILL.md     <- ATLAS near-verbatim (+ layer-2 caveat)
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
| G-2 (capability removal) | `bash: deny` + allowlist; git isolated to `git-ops` | Broker as separate process/IPC; **E-1 argument policy**; credential isolation |
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
