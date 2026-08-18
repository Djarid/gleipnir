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
