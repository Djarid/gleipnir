# Decision: Operating posture — UNCAGED by default, OPT-IN caged

**Status:** decided (operator, via the built-in escape hatch). Durable Tier-3
decision record. Converged via the orchestrator-surfaced precept-10 gate
(brief: `../plans/override-paradigm-brainstorm.md`). This record SUPERSEDES the
always-on-cage framing in `s2-g1-closure.md`, `substrate-design-pass.md`,
`gleipnir-layout-and-memory-model.md`, and the `AGENTS.md` trust-tier/guard
framing (each now carries a banner pointing here).

## Thesis

Gleipnir operates UNCAGED by default. The single human at the terminal is the
trusted owning principal; an agent acting under operator instruction may perform
any act, INCLUDING editing Tier-3 enforcement config (`agents/`, `keys/`,
`stage-role-map.md`, `decisions/`, `goals/`). This is the intended posture for
the attended single-principal case — a legitimate default, NOT a deficiency and
NOT a not-yet-reached end-state.

The S-2 cage (Tier-3 read-only to the agent, OS wall, unreadable key, agent
cannot mutate its own boundary) is a deliberately OPT-IN high-assurance MODE the
operator switches on when the threat model requires it.

## Threat-model envelope (the assumption the default rests on)

The uncaged default is safe ONLY within this envelope, stated so the tradeoff is
eyes-open:

> Session access equals full operator authority, AND no untrusted content enters
> the agent's context during the session.

Under those two conditions an agent editing Tier-3 is the operator editing Tier-3
by proxy — no privilege boundary is crossed. Outside the envelope, caged mode is
REQUIRED (below).

## Opt-in caged triggers (REQUIREMENTS, not suggestions)

Caged mode (run the fail-closed preflight to a CLOSED verdict + the operator's
S-2 OS acts) is REQUIRED for:

1. **Unattended / autonomous / long-running sessions** (no human watching).
2. **Any session ingesting untrusted external content** (web fetch of untrusted
   pages, third-party repos, pasted/attached content of unknown provenance).
3. **Higher-assurance contexts** — handling secrets, producing attested
   artifacts others rely on, or multi-agent / hosted operation (C-tier).

The operational procedure for entering caged mode is the `go-caged` runbook
(a companion Tier-3 record) and its guiding skill — converged and planned; see
`../plans/caged-mode-runbook-brainstorm.md` until the runbook record lands.

## Key-protected floor (retained even in the uncaged default)

Even in the uncaged default, `.gleipnir/keys/marker.key` stays `chmod 600`
owner-only. The G-3 HMAC key's compromise is silent, cross-session, and defeats
the evidence the framework uses to prove work happened — so it is protected in
BOTH modes. The default posture is therefore labelled **"uncaged (key-protected
floor)"**, not "everything open". Uncaged is NOT all-or-nothing.

## Honesty invariant (both modes)

The operator ALWAYS knows which mode a session runs in. The preflight labels the
state at every launch: the uncaged default gets a neutral, legitimate label + an
informational reasons list; an explicitly-requested caged run that does not reach
CLOSED keeps the loud "NOT closed" deficiency language and REFUSES. Relabelling
changed how the default is FRAMED, never whether the state is disclosed.

## What is NOT changed

G-2 (broker single-holder), G-3 (keyed evidence — floor retained above), G-4
(bus), G-5 (deterministic orchestration), and G-6 (memory-poisoning model) are
not repealed. This record changes the DEFAULT posture of G-1's S-2 boundary and
the Tier-3-unwritable DEFAULT only.
