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

> **`gleipnir-launch` now enforces the caged gate.** As of commit `b1afa6f`, act
> (6) of `s2-activation-control-proposal.md` passes **`--mode caged`** in the
> wrapper's embedded preflight, so the wrapper itself fail-closes: on a NOT-closed
> boundary the `--mode caged` path returns REFUSE (exit 1) and, because the
> wrapper uses `set -e`, it stops before dropping-and-launching. It will not
> launch when caged is requested but the boundary does not hold. **Even so, still
> run the explicit Step 3 `--mode caged` AC-4 check** as the authoritative
> verification of the boundary state: the wrapper enforces the gate mechanically,
> but confirming you are caged means reading `closed` + an empty reasons list +
> exit 0 (AC-4), not merely observing that a launch did not abort.

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
for every session that must be caged. `sudo bin/gleipnir-launch` now also
fail-closes on `--mode caged` (as of commit `b1afa6f`), but AC-4 remains the way
you *confirm* the boundary genuinely holds (reading `closed` + empty reasons +
exit 0), not merely that a launch did not abort. The `go-caged` skill re-verifies
acts (1)–(6) against the real box before declaring you caged — it never
self-attests a state it did not observe (a subagent's `question` cannot reach
you; same discipline as tier3-coach Anti-Pattern 5).

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

## Cross-artifact note — the `gleipnir-launch` wrapper (OI-1, RESOLVED)

**RESOLVED (commit `b1afa6f`).** The `bin/gleipnir-launch` wrapper drafted in act
(6) of `../plans/s2-activation-control-proposal.md` originally called the preflight
WITHOUT `--mode caged`, so it launched under the default uncaged mode and did NOT
fail-closed on a not-closed boundary. Act (6)'s embedded preflight call now passes
`--mode caged`, so the wrapper genuinely enforces the caged gate on every launch,
matching this paradigm. This closes open item OI-1 (tracked in
`../plans/caged-mode-runbook.md`). The explicit Step 3 `--mode caged` AC-4 check
remains the authoritative *verification* of the boundary state (reading `closed` +
empty reasons + exit 0), which the wrapper's mechanical fail-close does not
replace.

## Assembled pieces (provenance — none re-authored here)

- `--mode caged` selector: `src/gleipnir/preflight/__main__.py` + `boundary.py`.
- Six OS acts (source of truth): `../plans/s2-activation-control-proposal.md`.
- AC-4 go/no-go gate: `../plans/s2-activation.md`.
- Guides-but-operator-applies handoff: `../skills/tier3-coach/SKILL.md`
  (Anti-Pattern 3).
- Paradigm + triggers + honesty invariant + key floor:
  [`operating-posture.md`](./operating-posture.md).
