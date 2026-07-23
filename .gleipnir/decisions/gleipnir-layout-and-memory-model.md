# Decision: `.gleipnir/` trust-tiered layout and memory-write model

**Status:** decided (this session). Durable decision record. Realises spec
requirement **G-6 (Memory is not poisonable)** at the directory-layout and
write-path level. Authored by the operator via the escape hatch (the built-in
`build` agent), because everything it governs is Tier-3 config that no
in-framework agent may write.

## Why this exists

Persistent agent memory is **executable influence stored as text**: a poisoned
memory file behaves like an edited startup script, and the influence survives
across sessions. (See the July 2026 *Bad Memory* result: payloads planted in
file-backed memory affected current and future sessions, and refusal did not
always remove the payload.) Gleipnir therefore treats persistent memory as
**untrusted, versioned input with explicit writers, provenance, review gates
and repeated integrity checks** — not as a trusted store a stronger model can
be relied on to keep clean.

This traces directly to Axiom 2: *a guard must not be reachable, forgeable, or
blindable by the population it guards.* Memory poisoning makes a guard
**reachable via persisted text that outlives the session**. G-6 closes it.

## The reframe

`.gleipnir/` is **not** "config (read-only) + data (writable)". It is four
**trust tiers**. The invariant: **authority decreases as writability
increases, and nothing in a lower tier may alter anything in a higher tier** —
enforced structurally (capability + integrity digest), never by prompt wording.

## The tiers

```
.gleipnir/
  # ── TIER 3: POLICY ── agent-unwritable (G-1). Operator-authored only.
  agents/            per-agent permission maps
  skills/            GOTCHA/ATLAS methodology (the amended SKILL.md set)
  goals/             process-as-data goals (K-1)
  stage-role-map.md  G-5 engine's state->role binding
  decisions/         durable decision records (this file lives here)
  keys/              G-3 HMAC key + approved integrity digests   [S-2 boundary]

  # ── TIER 2: USER_REVIEWED ── writable ONLY via the review-gated pipeline
  memory/            long-term concept graph (T-1)
  lessons/           GOTCHA graduated Guardrails / LESSONS (G-4c graduation)

  # ── TIER 1: RETRIEVED ── framework-writable, provenance-required, low authority
  logs/              session-observer / G-4 bus output

  # ── TIER 0: TEMPORARY ── freely writable, no authority, disposable
  plans/             transient session artifacts (ATLAS briefs, validation)
  var/tmp/           scratch
```

Trust tiers, as code (the authority ladder):

| Tier | Name | Example paths | May influence |
|---|---|---|---|
| 3 | POLICY | `agents/`, `skills/`, `goals/`, `stage-role-map.md`, `decisions/`, `keys/` | everything |
| 2 | USER_REVIEWED | `memory/`, `lessons/` | facts + graduated lessons; never tool permissions or safety policy |
| 1 | RETRIEVED | `logs/` | observation only; no authority over planning/tool use |
| 0 | TEMPORARY | `plans/`, `var/tmp/` | none; disposable |

## The three write paths

1. **Tier 3 (POLICY) — operator-only.** No in-framework agent writes it, ever.
   Authored by the operator via the escape hatch (`/build` or an editor), or a
   future signed policy-change command. This is G-1 unchanged. The roster's
   blanket `.gleipnir/**` deny is *correct* for this tier — the wall we hit is
   the wall working.

2. **Tier 2 (USER_REVIEWED — memory, lessons) — deterministic review-gated
   pipeline.** No agent edits these files directly. An agent may *propose* an
   entry; a deterministic framework component decides whether and where it is
   written. The pipeline (code, not an LLM):
   1. **Receive** a proposed memory entry.
   2. **Classify** its source and trust tier (external content enters a *data*
      field, never a *policy* field).
   3. **Validate** its schema and that the destination is allowed for that
      named writer.
   4. **Review** — a human-readable diff is required for any high-trust change,
      and approval is bound to that exact diff (precept 10 human gate; under
      G-5 this is a pipeline state with no outgoing edge until answered).
   5. **Append an audit event** to the G-4 bus with provenance
      (source, author, reviewed_by, session id, originating turn) and run
      persistence probes.
   Raw external content never lands in a policy file. Old versions are retained
   so a suspicious change can be explained and rolled back.

3. **Tier 1/0 (logs, plans, tmp) — narrow per-path grants.** Framework
   processes (the bus/observer) and bounded roster agents write only their own
   operational path. Tier-1 writes carry provenance; Tier-0 is disposable and
   authority-free. The orchestrator writes `plans/`; a memory-writer component
   writes via the Tier-2 pipeline only; the observer/bus writes `logs/`.

## Reused primitive: G-3.1 IS the integrity-digest defense

The *Bad Memory* "store the approved digest outside the agent-writable
workspace; check it at session start and before high-impact tool calls"
requirement is **already built** as G-3.1 (HMAC over content, key under the
S-2 boundary, fail-closed on mismatch). Applied to memory security:

- Each Tier-3 policy file (agent permission maps, `stage-role-map.md`,
  `AGENTS.md`) and each approved Tier-2 memory file gets a **keyed digest** in
  `keys/`.
- **S-3 preflight** (already specified) verifies those digests at session
  start — this satisfies "check at session start" for free.
- A file whose content does not match its approved digest is **quarantined**
  (fail-closed), exactly as an invalid test marker forces a re-run. The
  digest cannot be forged without the verifier key, which lives outside the
  agent surface.

## Named-writer / trust-tier enforcement (deterministic, not prompt)

- Trust tier is a property of the *path*, encoded in code (an ordered enum),
  not inferred from content.
- A component may write only paths its named-writer grant allows; the model may
  *propose*, a deterministic component *decides destination*.
- Suspicious-influence scanning (`ignore previous`, `disable security`, etc.)
  is a **tripwire that quarantines and escalates**, never a completeness claim:
  a match quarantines; an absence of matches proves nothing.

## Status: authored, not yet closed

At this pre-S-2 stage the tier boundaries are enforced only by opencode
permissions and this prose. They become *structurally* enforced when:
- the **S-2 mount** makes Tier 3 read-only from the agent surface,
- the **keys/** digests + **S-3 preflight** verification are wired,
- the **Tier-2 review-gated memory-write pipeline** is built (with the G-4 bus
  for audit events and the precept-10 human gate for review), and
- the **cross-session persistence conformance tests** (G-6 [D]) are added.

Until then this document is the contract those later steps implement.

## Consequences / to-do captured

- Create the tier directories (`memory/`, `lessons/`, `logs/`, `var/tmp/`,
  `keys/`) with READMEs stating their tier and writer; empty dirs are not
  git-tracked, so each needs a placeholder.
- Update per-agent grants so operational writers (once they exist) target only
  their tier path; the blanket `.gleipnir/**` deny stays for Tier 3.
- Add G-6 to the spec (done in v0.3.10) with its conformance [D].
- Build order: the memory-write pipeline is T-1 work; the digests are G-3.1
  applied; preflight is S-3; all gated on S-2.
