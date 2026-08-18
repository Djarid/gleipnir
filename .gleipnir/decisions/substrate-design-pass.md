# Substrate Design Pass — Build-Order Step 1

> **SUPERSEDED IN PART by `operating-posture.md` (default-uncaged paradigm).**
> The "guards take effect last / no session over an unverified boundary"
> framing in this record describes the OPT-IN CAGED mode, not the default.
> Gleipnir now operates UNCAGED by default (trusted single-principal terminal);
> the S-2 cage is a deliberate opt-in. This record's mechanisms remain correct
> WITHIN a caged commitment. See `operating-posture.md` for the governing
> thesis, threat envelope, and the three opt-in-caged requirements.

**The load-bearing step.** Per spec build order step 1, D-1 (runtime target)
and D-4 (trust-boundary substrate) are the two load-bearing unknowns and must
be resolved together in one pass, because the trust boundary is expressed in
the runtime's file and permission model. This pass also owns one evidence
item: the **config load path** (package/mount-side vs working-tree), which
flips G-1 between pass and fail for two whole surfaces.

**Status: decisions recorded, implementation not built.** This document
resolves the open decisions on record and verifies the S-1 hook contract
against the chosen runtime. It does not yet build the container, the broker,
or the key store; those are steps 2-4. It turns the step-0 scaffold's
"authored, not yet closed" guards into *specified-and-decided* guards with a
concrete mechanism named for each.

---

## D-1 — Runtime target: **RESOLVED (opencode for v0.1)**

Decision: **opencode**, targeted directly for v0.1, implemented against the
S-1 contract so a later pi.dev/pinion port is a contract-conformance exercise,
not a rewrite. This matches the spec recommendation on record.

### S-1 hook contract verification [D]

The spec requires demonstrating each S-1 hook exists on the chosen runtime, or
documenting a compensating mechanism. Mapped against opencode's plugin/hook
surface:

| # | S-1 requirement | opencode mechanism | Status |
|---|---|---|---|
| 1 | Pre-tool interception, can abort | `tool.execute.before` hook — throws to abort the call | **Present** |
| 2 | Post-tool observation | `tool.execute.after` hook — sees tool, args, result | **Present** |
| 3 | Per-agent capability declaration | agent `permission` map (tool + bash-glob + path globs), runtime-enforced | **Present** |
| 4 | Delegation primitive | `task` tool spawning scoped subagents with fresh context; `subagent_depth` caps nesting | **Present** |
| 5 | Human-question primitive (blocking) | `question` tool — blocks until a human answers | **Present** |
| 6 | Context-compaction hook | `experimental.session.compacting` — re-inject critical rules | **Present (experimental)** |
| 7 | Session-lifecycle events | `session.created` / `session.idle` / `session.deleted` events | **Present** |
| 8 | Platform-event ingress (inbound webhooks) | none — opencode has no persistent inbound receiver | **ABSENT (= E-2)** |

**Compensating mechanism for the one gap (#8, = seam E-2).** opencode is an
ephemeral, outbound client; platform events (revert on main, MR closed
unmerged, merge-against-red) arrive when no session runs. The compensating
mechanism is a **separate persistent process** that receives webhooks and
writes typed events onto the G-4 bus's second ingress class (S-1.8). This is
not a runtime hook and does not need to be one; it is deferred to the G-4
build (step 5) and tracked as E-2. It does not block the substrate pass
because none of G-1/G-2/G-3 depend on it.

**Caveat on #6.** The compaction hook is `experimental` in opencode and may
change without notice. Compensating posture: keep the compaction-survival set
small (G-5 already removes sequencing state from the context window), so a
degraded compaction hook loses less.

**Verdict:** 7 of 8 hooks present and usable; the eighth has a specified
compensating mechanism and is tracked as E-2. S-1 conformance holds for the
enforcement-bearing hooks (1-7). Build may proceed.

---

## D-4 — Trust-boundary substrate: **RESOLVED (B as core, C as hardening tier)**

Decision: **Option B (container read-only mount) as Gleipnir-core; Option C
(remote verifier/broker) as the hardening tier for hosted/multi-agent
operation; Option A (OS user + ACLs) only where containers are unavailable.**
This matches the spec recommendation and the existing Podman/Hephaestus
direction. The options compose.

### What B decides, concretely

- **Where guard config and code live:** read-only bind-mount (or a separate
  image layer) inside the agent container. `.gleipnir/` (and the enforcement
  subset within it) is mounted read-only, so no in-container write can alter
  it — this is the mechanism behind G-1, replacing the step-0 prose "agents
  deny edits under `.gleipnir/`".
- **Where the G-3 key lives:** under the same read-only boundary, readable
  only by the verifier process, never by the agent surface (G-3.1).
- **Where weakening toggles live:** outside the repo and outside the
  container's writable surface, human-set only (G-1).
- **The G-2 sandbox:** the same container is the bounded-blast-radius
  environment (T-6 folded into S-2). General bash (build/test/lint) runs
  where dangerous targets are absent or unwritable.
- **The broker boundary (G-2):** under B, the broker is reached over a
  socket/network endpoint crossing the container boundary; credentials live
  only in the broker's address space, never in the container as a mount, env
  var, or readable file. **E-1 remains open:** the broker must also enforce
  argument policy (refuse force, protected-branch writes, non-feature pushes),
  not merely hold the credential. Container isolation closes credential theft;
  it does not close the dangerous-verb-via-broker path. E-1 is a step-4
  obligation.

### Hardening tier (C), when it applies

Hosted or multi-agent operation promotes the broker/keys/credentials into a
separate process or host (secret-store backed), reached only via RPC, so root
inside the agent environment yields nothing. Higher build cost and an
availability dependency; adopt only when the threat model needs it.

---

## Config load path — **RESOLVED (mount-side / package-side, never tree-side)**

The pass's own evidence item. Decision: **agent permission definitions and
guard configs are loaded from the read-only mount (or installed package),
never from the agent-writable working tree.** Tree-side loading of anything
enforcement-bearing is a G-1 fail regardless of substrate option.

**Consequence for the step-0 scaffold.** Today `.gleipnir/` sits in the
working tree, loaded via `OPENCODE_CONFIG_DIR=.gleipnir`. That is correct for
step 0 (authored, not yet closed) but is a **G-1 fail as-is**, because an
in-framework agent with edit capability could write it. The closure step (see
below) must relocate the enforcement-bearing subset of `.gleipnir/` to the
read-only mount so the load path is mount-side. The non-enforcement content
(goals, plans, non-guard skills) may remain tree-side.

**Split to implement at closure:**

| `.gleipnir/` content | Load path after closure | Why |
|---|---|---|
| agent frontmatter / permission maps | mount-side, read-only | enforcement-bearing (G-1) |
| guard code / hooks / plugins | mount-side, read-only | enforcement-bearing (G-1) |
| G-3 key, rate table, weakening toggles | outside repo / mount-side | enforcement-bearing (G-1, G-4d) |
| goals, plans, methodology skill *content* | tree-side OK | not enforcement-bearing |

---

## Terminal closure and S-3 preflight (G-1 activation)

Per the G-1 terminal-closure invariant, guards are authored throughout build
and *take effect last*, verified from outside before each session. This pass
specifies the closure mechanism:

1. **Closure act:** mount the enforcement-bearing subset read-only (B), place
   the key and toggles outside the agent surface, remove raw dangerous-verb
   capability from the container.
2. **Verification from outside (S-3 preflight):** before any agent session
   starts, an out-of-framework check confirms guard paths are unwritable, the
   key is unreadable, hooks are registered, required tools present, and the
   bus is reachable. Fail-closed: no session starts over an unverified
   boundary.
3. **Not a control on the operator's escape hatch:** closure cages
   in-framework agents only. The operator's built-in `/plan` and `/build`
   agents are out of scope by the Part 0 scope clause; preflight neither
   checks nor restricts them.

---

## What this pass unblocks (spec build order)

- **Step 2 (G-3.1 keyed marker):** now has its key location — under the B
  read-only boundary, readable only by the verifier. Buildable next.
- **Step 3 (G-5 engine + G-3.2):** independent of the broker; the stage-role
  map (`.gleipnir/stage-role-map.md`) becomes the engine's config.
- **Step 4 (T-layer, delivers G-2):** the broker's IPC boundary and
  single-holder grant are specified; **E-1 argument policy** is the explicit
  step-4 obligation, not assumed closed by container isolation.
- **Step 5 (G-4 bus/ledger/observer):** the E-2 webhook receiver is the
  compensating mechanism for S-1 hook #8 and lands here.

## Decisions register delta (for a future spec revision)

| # | Was | Now |
|---|---|---|
| D-1 | Open | **Resolved: opencode for v0.1, S-1 verified (7/8 hooks, #8 compensated via E-2)** |
| D-4 | Open (P11-class) | **Resolved: B core / C hardening / A fallback; config load path mount-side** |

D-5 (licence) and D-6 (notional human rate) remain open; neither gates the
substrate. These D-1/D-4 resolutions should be folded into the decision
register in the next spec revision (candidate v0.3.9).
