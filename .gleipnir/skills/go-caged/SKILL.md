---
version: "1.0"
name: go-caged
description: "Guide the operator through entering full CAGED MODE — the opt-in high-assurance S-2 lockdown — on request: go caged, cage the system, lock it down, going autonomous/unattended, high-assurance mode, ingesting untrusted content (the operating-posture.md caged requirements). GUIDES + VERIFIES each step against real box state and gates on the AC-4 acceptance test; the OPERATOR executes the OS/root acts (same handoff shape as tier3-coach). Boundary: tier3-coach DETECTS control gaps and PROPOSES controls; go-caged EXECUTES a known, already-designed lockdown. References the go-caged runbook as its single source of truth."
license: MIT
metadata:
  version: "1.0"
  origin: gleipnir
  inherited_by: gleipnir
  inheritance: original
  rationale: "The default-uncaged / opt-in-caged posture (operating-posture.md) makes caged mode a REQUIREMENT for three triggers, but 'go caged' was scattered across four artifacts an operator had to assemble under pressure. This skill is the interactive front door: it walks the operator through the go-caged runbook, verifies each step against the real box, and gates on AC-4 — while the operator (not the agent) performs the root OS acts."
---

> **GLEIPNIR ORIGINAL SKILL.** Sibling to `tier3-coach`, distinct from it.
> **The boundary (named in both skills):** `tier3-coach` DETECTS a control gap
> and PROPOSES a control (Detect → Locate → Propose → Converge → Hand off);
> `go-caged` EXECUTES a KNOWN, already-designed lockdown on operator request —
> the gap is already found and the control already designed (the runbook + the
> six S-2 OS acts exist). Different verbs: *discover-and-propose* vs
> *guide-through-and-verify*.

# go-caged: enter opt-in caged mode

Use this skill when the operator signals intent to enter the required
high-assurance lockdown — **"go caged"**, "cage the system", "lock it down",
"we're going autonomous / unattended", "high-assurance mode", or "we're
ingesting untrusted content" (the three `operating-posture.md` caged
requirements). It walks the operator through the **go-caged runbook** and
verifies each step against the real box.

## Single source of truth

**The runbook [`../../decisions/go-caged-runbook.md`](../../decisions/go-caged-runbook.md)
is this skill's single source of truth.** This skill does **NOT** duplicate the
procedure or the commands — it references the runbook and guides the operator
through it, so there is never drift between two copies.

## The core boundary (why the operator, not the agent, executes)

**The agent GUIDES + VERIFIES; the OPERATOR EXECUTES the OS acts.** The six S-2
acts (create a dedicated agent uid, set OS-read-only enforcement perms, key
mode-600, a root-elevated launch wrapper) need **root** — no in-framework agent
can perform them, and the preflight is out-of-framework and operator-run. This
is the **same guides-but-operator-applies handoff shape as
[`../tier3-coach/SKILL.md`](../tier3-coach/SKILL.md) Anti-Pattern 3** (propose /
guide, never implement), reused here **by reference**, not re-derived. The same
**self-attestation discipline** applies (tier3-coach Anti-Pattern 5): a
subagent's `question` cannot reach the operator, so this skill never records a
box state or a convergence it did not actually observe — it verifies against the
real box and reports what it saw.

## Workflow: Guide → Verify → Gate

Follow the runbook's steps; for each, GUIDE the operator to run it and then
VERIFY the result against the real box.

1. **OS-layer setup (once).** Point the operator to acts (1)–(6) in
   `../../plans/s2-activation-control-proposal.md` (the runbook's Step 1).
   **Verify** each against the real box (uid exists; enforcement paths
   OS-read-only to the agent uid; `keys/marker.key` mode-600). Read the current
   proposal at execution time — this catches a stale reference.
2. **Software layer.** Guide the operator to run the explicit
   `sudo bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --mode caged`
   (no `--override-ack`) as the authoritative go/no-go — this is the ONE command
   that enforces the gate. Remind them that **the explicit `--mode caged`
   invocation** REFUSES (exit 1) if the boundary is not genuinely CLOSED — the
   mode can never manufacture CLOSED. **Do NOT present `sudo bin/gleipnir-launch`
   as an equivalent gate:** as drafted (act (6) of the control-proposal) the
   wrapper calls the preflight WITHOUT `--mode caged`, so on a not-closed
   boundary it exits 0 and launches under the neutral uncaged label — it does NOT
   refuse. Treat the wrapper as a launch convenience only, and always run the
   explicit `--mode caged` check first, until act (6) is amended to pass
   `--mode caged` (runbook Cross-artifact note).
3. **GO/NO-GO gate (AC-4).** Verify the no-override preflight reports `closed`,
   an **empty reasons list**, **exit 0**. That is the ONLY go signal. Anything
   else ⇒ NOT caged; report the failing reasons and stop — do not declare caged.
4. **Uncage (when asked).** Guide the minimal uncage: stop requesting caged
   (drop `--mode caged` / the wrapper). State that OS perms may harmlessly stay
   and **the key mode-600 floor stays in BOTH modes and is never relaxed**. A
   full teardown is a separate, rare decommission decision — never the routine
   uncage.

## Anti-Patterns

**Anti-Pattern 1: Execute the OS acts.** This skill GUIDES + VERIFIES. It never
runs `dscl`/`sysadminctl`/`chmod`/`chown`/`chgrp` or installs the launch
wrapper — those need root and are the operator's action (same as tier3-coach
Anti-Pattern 3).

**Anti-Pattern 2: Run the preflight as an agent.** The preflight is
out-of-framework, operator-run, fail-closed, and never routed into any agent
allowlist. Guide the operator to run it; do not try to invoke it in-framework.

**Anti-Pattern 3: Declare caged without the AC-4 gate.** "Looks set up" is not
caged. Only `closed` + empty reasons + exit 0 is caged. No self-attested state.

**Anti-Pattern 4: Duplicate the runbook.** The runbook is the single source of
truth. Reference it; never fork the procedure or the six OS-act commands into
this skill.

**Anti-Pattern 5: Relax the key floor on uncage.** `keys/marker.key` mode-600
stays in BOTH modes. Uncaging never `chmod`s it looser.

## Resilience

If this skill cannot be loaded, fall back to: open the runbook
`.gleipnir/decisions/go-caged-runbook.md`, guide the operator through its steps,
verify each against the real box, and gate on AC-4. Never execute the OS acts
for the operator, and never declare caged without the AC-4 go signal.

## Status

**Authored, cooperative-policy-until-AC-4.** The lockdown this skill guides
becomes a hard OS boundary only once the operator performs the six S-2 acts and
the no-override preflight reports CLOSED. Until then the session is honestly
labelled uncaged / dev-mode. This skill's discipline — guide + verify, never
execute; gate on AC-4; never self-attest — is what keeps "go caged" honest.
