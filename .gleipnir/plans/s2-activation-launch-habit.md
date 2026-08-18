---
type: plan-artifact
tier: 0
status: active
deliverable: 1
parent-plan: .gleipnir/plans/s2-activation.md
authored-by: gleipnir-plan
---

# S-2 Activation — C1 Launch Habit (per-session preflight)

**What this is.** Deliverable 1 (C1) of the approved plan
`.gleipnir/plans/s2-activation.md` (Assemble step 1, lines 180-192). It is a
**documentation-only, Tier-0** artifact: it describes an operator habit that
runs the *already-existing* advisory (dev-mode) preflight path. **No new code.**
The advisory path already lives in `bin/gleipnir-preflight` and
`src/gleipnir/preflight/boundary.py`; this doc turns it into a per-session
habit so G-1's closure status is surfaced honestly on every launch and never
silently drifts into "permanent dev-mode."

This is a pure two-way door: it lands first to run the C1 shakeout that
de-risks the C2 operator OS acts (Pre-Mortems #1/#2/#3). It changes nothing
under `src/`, `bin/`, or any enforcement path.

---

## The per-session invocation

Run this once at the start of each session, on the current single-uid box:

```
bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --override-ack
```

- Substitute `<uid>`/`<gid>` with the intended agent identity. On the current
  single-uid box these will equal the operator's own uid/gid; that is expected
  in advisory mode (see "Why dev-mode is honest" below).
- `--override-ack` is what selects the **advisory (dev-mode)** behaviour: it
  acknowledges that G-1 is not yet closed and asks preflight to *report and
  proceed* rather than refuse. It is dropped only at the eventual C2 flip
  (see the N≥5 counter below).
- Once C2 is applied, `<uid>`/`<gid>` are sourced from
  `.gleipnir/agent-identity.env` (single-source, per the parent plan's D-F /
  AC-5); until then, pass the intended values directly.

---

## How to read the reasons dump

The preflight prints a single verdict/label line to **stderr**, followed by
**one `  - ` line per reason** (two leading spaces, a dash, a space), also on
stderr. Read them top-to-bottom; each line is a distinct reason the boundary
is not yet closed.

Reference (do **not** modify): `src/gleipnir/preflight/__main__.py` lines
116-127 — the label line is printed first, then `for reason in
decision.reasons: print(f"  - {reason}", file=sys.stderr)`.

On the current single-uid box the reasons list will be **non-empty** (e.g. a
`WRITE_OK`-style probe result, because the agent-uid equals the operator-uid so
the write-probe succeeds and the path is not actually caged). That non-empty
list is the correct, expected advisory-mode signal — **not** a failure.

An **empty** reasons list means CLOSED (see exit code 0). An empty list is
structurally **impossible before the C2 OS acts are applied**: pre-C2 the
agent-uid equals the operator-uid (or a non-root uid-drop fails), so the
write-probe always succeeds and reasons are never empty. Therefore only start
the clean-session streak counter (below) *after* C2 is applied.

---

## Why dev-mode is honest — the healthy line

A healthy advisory-mode launch on the current box prints, to stderr:

```
gleipnir-preflight: proceed_unclosed -- G-1 NOT closed (dev-mode)
```

…followed by a non-empty `  - ` reasons list, and exits with **code 2**.

This is the honest steady state before C2: G-1 is *authored but not closed*,
preflight says so plainly every session, and it proceeds so work can continue.
The point of the habit is that the un-closed status is visible on **every**
launch, so dev-mode can never quietly masquerade as enforcement.

---

## Exit-code meanings

Per `src/gleipnir/preflight/__main__.py` lines 116-127 (cited for verification;
do not modify):

| Exit code | Verdict | Meaning |
|---|---|---|
| **0** | `CLOSED` | Boundary held: G-1 closed at the OS-perms floor. Reasons list is **empty**. This is only reachable after the C2 OS acts are applied. |
| **1** | (refuse / other) | Any verdict that is neither `CLOSED` nor `PROCEED_UNCLOSED` — i.e. a REFUSE. E.g. a `DROP_FAILED`/`DROP_UNVERIFIED`/`PROBE_ERROR` condition where preflight declines to proceed. |
| **2** | `PROCEED_UNCLOSED` | Advisory / dev-mode: G-1 NOT closed, but `--override-ack` was supplied, so preflight reports the reasons and proceeds. **This is the expected exit code for the C1 habit today.** |

Exact mapping in code: `CLOSED → return 0`; `PROCEED_UNCLOSED → return 2`;
otherwise `return 1`.

---

## Editing Tier-3 as the owner is expected, not a bypass (Pre-Mortem #2)

The S-2 boundary cages the **agent uid**. The operator edits Tier-3 files
(`agents/`, `skills/`, `goals/`, `decisions/`, `stage-role-map.md`, `keys/`,
etc.) **as the owner — their own account** — which is *outside* the agent-uid
cage **by construction** (owner ≠ agent-uid). Those operator edits are
therefore unaffected by the boundary and are **expected behaviour, not a
bypass** of G-1.

The habit loop is: **operator edits Tier-3 as owner; the agent (and the
launch-time preflight) runs as the agent-uid.** Two distinct principals, two
distinct authorities. This is exactly the separation the C1 shakeout exists to
prove *before* C2 is applied, so the operator's ordinary doc-editing workflow
is never bricked. (After C2, the ENFORCEMENT_PATHS subtree is OS-read-only to
the agent-uid, but the owner still writes it normally.)

---

## Reminder: confirm the shim is committed mode `100755`

Before relying on the habit, confirm `bin/gleipnir-preflight` is **committed
with git mode `100755`** (executable), per
`decisions/bin-executable-bit.md`.

- Check the tracked mode: `git ls-files -s bin/gleipnir-preflight` — the first
  field should read `100755`.
- If a local `core.fileMode false` setting is hiding the on-disk mode, the
  *committed* mode is still what matters; a shim tracked as non-executable
  would fail to run when invoked as `bin/gleipnir-preflight`.
- Restore if needed with `git update-index --chmod=+x bin/gleipnir-preflight`
  and commit. (This doc does **not** touch `bin/`; the reminder is for the
  operator.)

---

## Start the N≥5 clean-session counter (D-G)

The named C2 exit criterion (parent plan D-G, guarding against camping in
dev-mode forever) is: **N ≥ 5 clean advisory-mode sessions** — sessions whose
preflight reasons list is **empty** — accumulated and operator-confirmed,
**then** flip to hard fail-closed.

Operator action:

1. **Adopt the habit now** — run the invocation each session.
2. **Understand the ordering.** A clean (empty-reasons → CLOSED) session is
   **impossible before the C2 OS acts are applied** (pre-C2 the write-probe
   always succeeds, so reasons are never empty). Today, in C1, every session is
   *un-closed by design* (exit 2, non-empty reasons) — the counter cannot yet
   advance, and that is correct.
3. **Begin counting once C2 lands.** After the C2 acts are applied and the
   first clean **no-override** confirm passes (parent plan step 5 / AC-4, run
   under `sudo`), start the streak. Each subsequent ordinary launch that shows
   an **empty reasons list** increments the counter.
4. **At N ≥ 5**, the flip trigger is met: drop `--override-ack` from the launch
   habit and have the operator author the Tier-3 decision-record amendment
   (D-H) recording activation as **LOCKED**. (Authoring that record is an
   operator/Tier-3 act — not an agent act.)

Until then, keep the counter honest: only empty-reasons sessions count, and the
honest `proceed_unclosed -- G-1 NOT closed (dev-mode)` line every launch is the
guard that dev-mode stays visible.

---

## Acceptance mapping

- **AC-1** — the invocation prints `gleipnir-preflight: proceed_unclosed --
  G-1 NOT closed (dev-mode)` with a non-empty `  - ` reasons list, exit 2:
  documented under "Why dev-mode is honest" and "Exit-code meanings".
- **AC-2** — this doc states the exact invocation, the exit-code meanings
  (0/1/2), the "edit Tier-3 as owner" loop, and the N≥5 counter: all present
  in the sections above.
- **AC-3** (negative) — this file is the sole write; nothing under
  `src/gleipnir/preflight/**`, `bin/**`, or any ENFORCEMENT_PATH is modified.
