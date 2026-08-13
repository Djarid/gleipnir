# Plan: S-2 Activation — turning the verified boundary ON (staged hybrid, Approach C)

> **Source brief:** `.gleipnir/plans/s2-activation-brainstorm.md`
> (**OPERATOR-CONVERGED**, precept-10 gate: **Approach C — staged hybrid landing
> on the Approach-A uid-floor**). This plan runs ATLAS Architect/Trace on that
> converged brief and does **not** re-decide any material tradeoff locked there.
>
> **Routing (blast-radius classifier):** this plan touches the S-2/G-1
> enforcement boundary. Its own review is the **HARDENED path** (Axis 2(a): the
> C2 proposal describes acts against `.gleipnir/keys/**`, `agents/**`,
> `decisions/**`, `stage-role-map.md`, and the launch/config wiring; a companion
> Tier-3 decision-record amendment is an `E`-set write). Two distinct
> spec-conformance + blast-radius passes and the negative-check attestation
> apply.
>
> **Two clearly-separated deliverables** (kept distinct throughout):
> - **Deliverable 1 — C1 advisory-activation slice.** Buildable now,
>   within-boundary. Finding: **almost nothing is agent-buildable** (see below).
> - **Deliverable 2 — C2 tier3-coach control proposal.** OS-level acts; **no
>   roster agent can perform them**; operator-applied.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D-A | Activation topology / ramp | **Approach C** (staged hybrid → Approach-A uid-floor) | Approach A (uid-floor now), Approach B (session-in-VM) | **OPERATOR-CONVERGED** (brief "Selected Approach"). Weighted matrix C=483 > A=443 > B=248; C dominates on reversibility + workflow-preservation. NOT re-decided here. |
| D-B | Does C1 need new code? | **No new code** — C1 is a documented launch habit + a Tier-0 doc + a Tier-3 decision-record amendment | Build a new `bin/` wrapper; add a reasons-dump feature | **Finding (verified against source):** `--override-ack` → `PROCEED_UNCLOSED` + `DEV_MODE_LABEL` + full per-session reasons dump already exist (`__main__.py:56-64,116-127`; `boundary.py:506,559-560`). Nothing to build. |
| D-C | Who can build C1's parts? | Doc under `.gleipnir/plans/` = **within-boundary** (Tier-0, a roster writer could draft); the decision-record amendment + any `bin/` wrapper + preflight source = **operator-only** | Have `gleipnir-code` add a `bin/` launcher | `gleipnir-code` **denies** `src/gleipnir/preflight/**` (agent file line 16) and `.gleipnir/**` (line 14); `bin/` is operator territory (this-session flag + shim is deliberately out-of-framework). The honest answer is "almost nothing is agent-buildable." |
| D-D | C1 wrapper — build one now? | **Defer the executable wrapper to C2** (operator-owned); C1 is a *manual* documented launch invocation | Build a host `bin/` wrapper in C1 | A `bin/` executable that runs the preflight is (a) operator/Tier-3 territory and (b) only meaningful once `--agent-uid`/`--agent-gid` have a real target (C2). Building it in C1 would fold C2 wiring forward (scope-creep guard). |
| D-E | C2 acts — who performs them | **Operator only**, via a tier3-coach control proposal | Any roster agent (incl. `gleipnir-plan`) | tier3-coach Anti-Pattern 3: this skill **proposes**, never implements. OS uid creation, `chmod`, key perms, elevated launch are OS/host-layer — outside every tier. |
| D-F | Single source of truth for the drop target | **One config file** (`.gleipnir/agent-identity.env`, operator-owned) sourced by BOTH the preflight invocation and the launch-as-agent-uid wrapper | Hard-code uid/gid in two places | Pre-Mortem #3: if the preflight's `--agent-uid` ≠ the account opencode actually runs as, a mis-drop is either falsely CLOSED or wrongly NOT_CLOSED. Single-source + assert-equality removes the divergence. |
| D-G | Named C2 exit criterion (Pre-Mortem #4 / Status-Quo guard) | **Trigger = N clean advisory-mode sessions** (N≥5) with an empty reasons list, operator-confirmed, then flip | A calendar date; "whenever" | Brief requirement (3) LOCKS that a named criterion is mandatory; leaves the specific trigger to this plan. A clean-reasons streak is a *behavioural* gate tied to the actual acceptance test, not an arbitrary date. Recorded so dev-mode cannot silently become permanent. |
| D-H | Companion decision-record amendment | **Yes** — amend `.gleipnir/decisions/s2-g1-closure.md` (or new `s2-activation.md` record) at C2 flip, operator-authored | Leave the flip undocumented | Open Question 4 in the brief: the C2 acts want a Tier-3 record marking activation as LOCKED. Operator-authored (Tier-3), not agent. |
| D-I | Explicitly deferred | B-literal/C-tier, E-1 credential isolation, `keys/` digests + S-3 wiring, Tier-2 memory pipeline, G-4d real cost, OS-ro boundary over `src/` guard code | Folding any into activation | Scope-Creep guard (brief bias check + Item 5). Each is its own later slice, gated on this floor. |
| R-1 | Hardened-path spec-review round 1 (SPEC-CONFORM PASS; BLAST-RADIUS 3 fail-safe text/script defects) | **Three in-place fixes:** (1) add `sudo` to the C2 no-override acceptance test (Assemble step 5 + AC-4); (2) reword the circular "Ordering rationale" so N≥5 gates the **flip** (step 6), not the initial application (steps 4-5); (3) extend explicit `go-w`/`a+rX` dir-node hardening to include `agents/` and `keys/` so all 8 LOCKED ENFORCEMENT_PATHS are hardened by the script | Leaving the test unsatisfiable, the ordering circular, and 2 of 8 paths on default-umask luck | Text/script corrections, **not design changes** — nothing re-decided. macOS `os.setuid()` to a different uid needs root (so the test needs `sudo`); a clean session is impossible before step 4 (so N≥5 can only gate the flip); explicit hardening of all 8 paths beats umask luck. Citations unchanged (reviewer verified all exact). |

---

## Architect

**Problem (one sentence):** Gleipnir's S-2/G-1 boundary is built and fail-closed
but *dormant* on a single-uid macOS box; activation is the staged ramp (C1
advisory dev-mode now → C2 OS uid-floor + hard fail-closed) that turns the
preflight from a built-but-silent verifier into a live signal and then a real
wall — without silently failing open or bricking the operator's workflow.

**User:** the **operator** (the owning principal), who runs
`bin/gleipnir-preflight` before each opencode session and, at C2, performs the
OS-level acts. **Not** any roster agent — the preflight is deliberately
out-of-framework and unreachable by any agent allowlist (`__main__.py:1-12`,
`bin/gleipnir-preflight:10-13`).

**Measurable success criteria:**
- **C1 (now):** every session launch runs
  `bin/gleipnir-preflight --agent-uid … --agent-gid … --override-ack`, which
  prints `proceed_unclosed -- G-1 NOT closed (dev-mode)` plus the full reasons
  list to stderr (exit code 2), and the operator has a documented one-liner /
  habit that makes this a reflex. Zero structural change; a pure two-way door.
- **C2 exit gate (the flip trigger):** the preflight, run WITHOUT `--override-ack`
  after the OS acts, reports `closed -- G-1 boundary held at the OS-perms floor`
  with an **empty reasons list** (exit code 0) — no `DROP_UNVERIFIED`, no
  `DROP_FAILED`, no `PROBE_ERROR`, no `<walk-error>`, and every ENFORCEMENT_PATH
  `WRITE_DENIED` after a *verified* drop (`keys/**` also read-denied). That IS
  the C2 acceptance test.
- **Anti-drift:** the flip is gated on **N≥5 clean advisory sessions**
  (empty reasons list every time), operator-confirmed; the `DEV_MODE_LABEL`
  keeps the un-closed status visible on every launch until then.

**Constraints (environment ground truth — darwin, verified against the brief):**
- Host: macOS 26.5.2, arm64. opencode runs **on the host as the operator's
  user** via `.envrc` `OPENCODE_CONFIG_DIR=.gleipnir`.
- **Dropping to a *different* uid requires the launching process to be root**
  (POSIX). A plain user cannot `setuid` to another uid. → C2's launch step needs
  an elevated (root) wrapper that setuids to the agent account.
- **Real uid separation on macOS host = an actual second local account**
  (`dscl`/`sysadminctl`), not a Linux user-namespace remap (macOS lacks host
  user-namespaces).
- Containers on macOS run in a Linux VM → B-literal = session-in-VM, explicitly
  **deferred** (D-I).
- Enforcement core is **stdlib-only** (`decisions/runtime-and-deps.md`); no new
  deps. (C2 uses only `dscl`/`sysadminctl`/`chmod`/`chown`/shell — all base OS.)
- The preflight is **out-of-framework, operator-run, fail-closed** — activation
  must not route its invocation into any agent allowlist.

**Explicitly NOT a user / NOT in scope:** the operator's built-in `/plan`
`/build` escape-hatch agents (Part 0 — the preflight never checks or restricts
them; boundary.py:87-91,222-224).

---

## Trace

### Artifacts and where they live (source of truth)

**Already built — NO change (verified, L-C15):**

| Artifact | Path | Verified fact |
|---|---|---|
| Boundary decision core + thin edge | `src/gleipnir/preflight/boundary.py` | `ENFORCEMENT_PATHS` (8 entries), `DEV_MODE_LABEL="G-1 NOT closed (dev-mode)"` (line 506), override can never yield CLOSED (`decide`, lines 516-563). **DENIED to `gleipnir-code`.** |
| Preflight CLI | `src/gleipnir/preflight/__main__.py` | flags `--config-root`, `--agent-uid` (required), `--agent-gid` (required), `--override-ack` (lines 39-64); prints verdict+label+every reason to stderr (116-127); exit 0/1/2 (123-127). **Reasons dump already exists.** **DENIED to `gleipnir-code`.** |
| Preflight shim | `bin/gleipnir-preflight` | thin `exec`; deliberately NOT in any agent allowlist (lines 10-13). Committed mode `100755` (`decisions/bin-executable-bit.md`). |
| Key env var | `src/gleipnir/verify/marker.py:40` | `KEY_ENV_VAR = "GLEIPNIR_MARKER_KEY_FILE"`. `load_key` (86-106) is **verifier/owner-run** — a mode-600 owner-readable key is readable to it (Pre-Mortem #5 holds). |

**ENFORCEMENT_PATHS — the LOCKED set (cite, do not invent), relative to
`OPENCODE_CONFIG_DIR` = `.gleipnir/` (boundary.py:166-220):**
`agents/` (RO) · `stage-role-map.md` (RO) · `decisions/` (RO) · `goals/` (RO) ·
`keys/` (**RO_AND_UNREADABLE**) · `plugins/` (RO, tolerate-absent) ·
`sandbox/` (RO) · `AGENTS.md` (RO). Skill *bodies* deliberately stay writable.

**To be created (Tier-0, within-boundary — Deliverable 1):**

| Artifact | Path | Who | Kind |
|---|---|---|---|
| Launch-habit doc (C1) | `.gleipnir/plans/s2-activation-launch-habit.md` (Tier-0) | roster writer OR operator | The documented per-session invocation + how to read the reasons dump. **The one within-boundary agent-draftable artifact.** |

**To be created (operator-only — Deliverable 2):**

| Artifact | Path | Who | Kind |
|---|---|---|---|
| tier3-coach control proposal (C2) | `.gleipnir/plans/s2-activation-control-proposal.md` (Tier-0) | **`gleipnir-plan` drafts the proposal text (Tier-0 is in grant); the OPERATOR applies it** | Ready-to-apply OS acts (dscl/chmod/key perms/wrapper). |
| Agent-identity single source | `.gleipnir/agent-identity.env` (operator-owned, at C2) | **operator** | uid/gid single source of truth (D-F). |
| Launch-as-agent-uid wrapper | `bin/gleipnir-launch` OR operator shell function (at C2) | **operator** (bin/ = Tier-3/operator) | Elevated (root) wrapper: preflight-then-setuid-then-exec-opencode. |
| Decision-record amendment | `.gleipnir/decisions/s2-g1-closure.md` amend, or new `s2-activation.md` (at C2 flip) | **operator** (Tier-3) | Records activation as LOCKED (D-H). |

### Integrations map

- **preflight ↔ agent account:** the preflight's `--agent-uid`/`--agent-gid`
  MUST equal the uid/gid opencode actually runs as. Both derive from
  `.gleipnir/agent-identity.env` (D-F). The launch wrapper sources the same file
  and asserts equality before exec.
- **preflight ↔ key:** `GLEIPNIR_MARKER_KEY_FILE` points at the key placed
  mode-600 owner-only; the preflight drops to the agent uid and confirms it is
  **unreadable** there (RO_AND_UNREADABLE); the verifier (`load_key`, owner-run)
  can still read it.
- **git-guard ↔ preflight (context, NOT this slice):**
  `plugins/git-guard.ts` already shells `bin/gleipnir-preflight config-scan`
  before broker git writes (`decisions/bin-executable-bit.md`). That is the
  `config-scan` mode, distinct from the boundary probe; activation does not
  touch it. Noted so the operator knows the shim's mode `100755` matters here too.
- **decision record ↔ boundary:** the C2 amendment is itself an ENFORCEMENT_PATH
  (`decisions/**`), so it must be authored via the operator escape hatch (owner),
  not by an agent — consistent with owner ≠ agent-uid (Second-Order insight).

### Edge cases (each mapped to a Pre-Mortem row + its mitigation)

| Edge case | Handling |
|---|---|
| **Silent fail-open** (PM #1) — CLOSED but a path writable | Structurally impossible: only `WRITE_DENIED` after a *verified* drop yields CLOSED; `DROP_*`/`PROBE_ERROR`/walk-error force NOT_CLOSED (boundary.py:292-303,401-460). C1 prints the real reasons every session. C2 gate = operator eyeballs empty reasons list. |
| **Bricked workflow** (PM #2) — Tier-3 edits blocked | Operator edits Tier-3 **as owner** (their own account), which is *outside* the agent-uid cage by construction (owner ≠ agent-uid). C1 shakeout proves it before C2. Documented in the launch-habit doc + the proposal's ownership layout. |
| **Elevated-launch misconfig** (PM #3) — wrapper fails to drop, opencode runs as owner | Preflight drops to the *agent* uid independently → owner-writable path reports `WRITE_OK` → NOT_CLOSED → REFUSE. Caught, not hidden — **provided `--agent-uid` matches the run account** (D-F single source + assert-equality). |
| **Camp in dev-mode forever** (PM #4) | D-G named exit criterion (N≥5 clean sessions) + honest `DEV_MODE_LABEL` every launch. Recorded in the decision-record amendment (D-H). |
| **Key relocation breaks verify** (PM #5) | `RO_AND_UNREADABLE` is agent-uid-unreadable; `load_key` runs as owner (verified marker.py:86-106). Confirm the verify/marker read path runs as owner before the flip; C1 surfaces a `key: …` reason if not. |
| **Second-account rot** (PM #6) | Agent account kept minimal: reads source + writes Tier 0/1/2 only. Ownership/group layout documented in the proposal (operator owns files; agent-uid has group/other read of source, write of Tier 0/1/2 only). |
| Missing enforcement path | Non-`plugins` missing path → `PROBE_ERROR` → refuse (boundary.py:937-947). `plugins/` tolerates absent. No action; documented expectation. |
| `core.fileMode false` hiding shim mode | Out of this slice, but the launch-habit doc reminds the operator to confirm `bin/gleipnir-preflight` is `100755` (`decisions/bin-executable-bit.md`). |

---

## Link (validated before building)

- **C1 dev-mode path exists end-to-end** — verified in `__main__.py` (flags +
  reasons dump + exit 2) and `boundary.py` (`DEV_MODE_LABEL`, override→
  PROCEED_UNCLOSED, no path to CLOSED). ✓ → **D-B: no new code.**
- **`gleipnir-code` cannot touch the preflight or `.gleipnir/`** — verified
  agent file lines 14,16. ✓ → **D-C: almost nothing agent-buildable.**
- **`bin/gleipnir-preflight` is out-of-framework** — verified lines 10-13. ✓
- **`ENFORCEMENT_PATHS` set** — verified boundary.py:166-220 (exact 8). ✓
- **`KEY_ENV_VAR`** — verified marker.py:40 = `GLEIPNIR_MARKER_KEY_FILE`. ✓
- **verify read path is owner-run** — verified `load_key` marker.py:86-106. ✓
- **darwin uid-drop needs root** — brief constraint (lines 71-87); consistent
  with `os.setuid` semantics in boundary.py:606-652. ✓
- **No new deps** — C2 uses base-OS tools only; C1 uses the existing CLI. ✓

---

## Assemble (intended build order)

**Deliverable 1 — C1 (do first; low blast, reversible):**

1. **Write the C1 launch-habit doc** `.gleipnir/plans/s2-activation-launch-habit.md`
   (Tier-0). Content: the exact per-session invocation
   `bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid> --override-ack`,
   how to read the reasons dump (stderr, one `  - ` line per reason), what a
   healthy dev-mode line looks like (`proceed_unclosed -- G-1 NOT closed
   (dev-mode)`, exit 2), the "edit Tier-3 as owner" note (PM #2), and the
   confirm-`bin/` mode `100755` reminder. **This is within-boundary and
   agent-draftable** (Tier-0). *No preflight/`bin`/`src` change.*
2. **Adopt the habit** — operator begins running the invocation each session and
   starts the N≥5-clean-session counter (D-G).

**Deliverable 2 — C2 (draft the proposal now; operator applies later):**

3. **Write the tier3-coach control proposal**
   `.gleipnir/plans/s2-activation-control-proposal.md` (Tier-0) — the full
   ready-to-apply artifact (content in the "C2 Control Proposal" section below).
   `gleipnir-plan` may draft this Tier-0 file; **the operator applies it.**
4. **[OPERATOR]** Apply the proposal: create agent uid/gid → write
   `agent-identity.env` → `chown`/`chmod` ownership+group layout → `chmod` the
   ENFORCEMENT_PATHS subtree OS-ro to agent → place key mode-600 owner-only,
   point `GLEIPNIR_MARKER_KEY_FILE` at it → install the elevated launch wrapper.
5. **[OPERATOR]** Run the C2 acceptance test: `sudo bin/gleipnir-preflight
   --agent-uid <uid> --agent-gid <gid>` (**no** `--override-ack`) → expect
   `closed`, empty reasons, exit 0. **`sudo` is required:** on macOS
   `os.setuid()` to a *different* uid needs root, so a non-root operator process
   always hits `DROP_FAILED` (EPERM) → REFUSE regardless of correct perms. This
   matches the launch wrapper, whose embedded preflight already runs under root
   so the drop succeeds (Fix from review round R-1).
6. **[OPERATOR]** After the first clean no-override confirm (step 5 / AC-4)
   **and then** N≥5 further clean advisory-mode sessions accumulated during the
   ordinary launch habit (D-G), **flip**: drop `--override-ack` from the launch
   habit; author the Tier-3 decision-record amendment (D-H) recording activation
   as LOCKED.

**Ordering rationale (corrected, review round R-1):** C1 is a pure two-way door
and lands first to run the shakeout that de-risks C2 (PM #1/#2/#3). The true
required sequence is: **apply the OS acts (step 4)** — account + `chown`/`chmod`
+ key perms + wrapper — **then** the **first clean no-override confirm (step 5 /
AC-4, run under `sudo`)** — **then** N≥5 further clean sessions accumulate during
ordinary use — **then** flip to hard fail-closed (step 6). A clean session
(empty reasons → CLOSED) is structurally **impossible before step 4**: pre-step-4
the agent-uid equals the operator-uid (or a non-root drop fails), so the
write-probe always succeeds and reasons are never empty. Therefore the **N≥5
streak gates the FLIP (step 6), NOT the initial application (steps 4-5)** — the
flip is the one-way-ish act, and it cannot precede at least one CLOSED result.

---

## Stress-test (acceptance checks — concrete, checkable)

**Deliverable 1 (C1):**
- **AC-1:** Running `bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid>
  --override-ack` on the current single-uid box prints
  `gleipnir-preflight: proceed_unclosed -- G-1 NOT closed (dev-mode)` and a
  non-empty `  - ` reasons list to stderr, exit code **2**. (Behaviour already
  in code; the doc makes it a habit.)
- **AC-2:** The launch-habit doc states the exact invocation, the exit-code
  meanings (0/1/2), the "edit Tier-3 as owner" loop, and the N≥5 counter.
- **AC-3 (negative):** No file under `src/gleipnir/preflight/**`, `bin/**`, or
  any ENFORCEMENT_PATH is modified by Deliverable 1 — it is doc-only. Verify:
  `git diff --name-only` shows only `.gleipnir/plans/s2-activation*.md`.

**Deliverable 2 (C2) — the named exit criterion IS the acceptance test:**
- **AC-4 (the C2 gate):** After the operator applies the proposal, running
  `sudo bin/gleipnir-preflight --agent-uid <uid> --agent-gid <gid>` (**no
  override**) reports `closed -- G-1 boundary held at the OS-perms floor`, an
  **empty** reasons list, exit code **0**. No
  `DROP_UNVERIFIED`/`DROP_FAILED`/`PROBE_ERROR`/`<walk-error>` in reasons; every
  ENFORCEMENT_PATH `WRITE_DENIED` after a verified drop; `keys/**` also
  read-denied. **`sudo` is required** (review round R-1): on macOS
  `os.setuid()` to a different uid needs root, so a non-root run always hits
  `DROP_FAILED` (EPERM) → REFUSE and the test could never pass regardless of
  correct perms. This matches how the launch wrapper invokes the embedded
  preflight (under root, so the drop succeeds).
- **AC-5 (single-source, PM #3):** `--agent-uid`/`--agent-gid` in both the
  preflight invocation and the launch wrapper are sourced from
  `.gleipnir/agent-identity.env`; the wrapper asserts the exec'd account's uid
  equals that value before launching opencode.
- **AC-6 (PM #5):** With the key at mode 600 owner-only, `load_key` (owner-run
  verify path) still succeeds; the agent-uid read-probe reports read-denied.
- **AC-7 (anti-drift, D-G):** The decision-record amendment names the exit
  trigger (N≥5 clean sessions), states dev-mode must not become permanent, and
  is authored as owner (Tier-3), not by an agent.
- **AC-8 (deferrals intact, D-I):** The plan and proposal name B-literal/C-tier,
  E-1, `keys/` digests + S-3, Tier-2 memory pipeline, G-4d, and `src/` guard-code
  boundary as **out of scope**; none is built or folded in.

---

## Execution Workflow

**For the roster writer of Deliverable 1 (within-boundary):** write only
`.gleipnir/plans/s2-activation-launch-habit.md` (Tier-0). Do **not** touch
`src/`, `bin/`, or any `.gleipnir/` enforcement path. There is **no code and no
test** to author — the dev-mode behaviour is already in the shipped preflight
(D-B). This deliverable is documentation only.

**For `gleipnir-plan` (this role) on Deliverable 2:** draft the control proposal
Tier-0 file (below) and **stop** — do not apply it. Applying is the operator's
act (tier3-coach Anti-Pattern 3 + D-E).

**For the operator on Deliverable 2:** follow Assemble steps 4-6; the exact
commands are in the "C2 Control Proposal" section. The flip (step 6) is gated on
AC-4 passing AND the N≥5 clean-session streak (D-G).

**Hard boundaries honoured:** no roster agent writes `src/gleipnir/preflight/**`,
`bin/**`, any ENFORCEMENT_PATH, or `.gleipnir/keys/**`. The only agent-writable
artifacts in this whole plan are the two Tier-0 `.gleipnir/plans/*.md` files.

---

## C2 Control Proposal (tier3-coach — for `.gleipnir/plans/s2-activation-control-proposal.md`)

> This is the ready-to-apply content the proposal file will carry. It is
> reproduced here so the plan is self-contained; the separate Tier-0 proposal
> file is the artifact the operator applies.

### Gap
The S-2/G-1 boundary is verified-but-dormant: on the single-uid host every
ENFORCEMENT_PATH is agent-writable in principle and the key agent-readable, so
enforcement is **cooperative policy**, not an OS wall. The missing controls (a
dedicated agent uid, OS-ro perms on the enforcement subtree, an unreadable key,
and an elevated launch that runs opencode as that uid) are **safety invariants**
that must be enforced somewhere — today nothing does. This is safety, not
preference.

### Correct layer
**OS / host layer** (uid creation, file perms, launch-as-uid) + **Tier-3 POLICY**
(the decision-record amendment). Per the tier3-coach layer map both are **No**
rows — no roster agent (including `gleipnir-plan`) can write them. Confirmed:
`gleipnir-code` denies `src/gleipnir/preflight/**` and `.gleipnir/**`; `bin/` is
operator territory; OS acts are outside every tier. → **proposal, not edit.**

### Proposed artifacts (ready-to-apply; adjust names/uids to the host)

Assume: operator = owner (`$(whoami)`); repo at `$REPO`; agent account name
`gleipniragent`. Pick a free uid/gid (e.g. `510`); verify free first with
`dscl . -list /Users UniqueID` and `dscl . -list /Groups PrimaryGroupID`.

**(1) Create the dedicated agent gid + uid (macOS `dscl`/`sysadminctl`):**
```sh
# Group first (so the user's PrimaryGroupID exists):
sudo dscl . -create /Groups/gleipniragent
sudo dscl . -create /Groups/gleipniragent PrimaryGroupID 510
sudo dscl . -create /Groups/gleipniragent RecordName gleipniragent

# User (non-login, no admin) — sysadminctl is the supported modern path:
sudo sysadminctl -addUser gleipniragent -UID 510 -GID 510 \
  -fullName "Gleipnir Agent" -home /var/empty -shell /usr/bin/false
# (Equivalent low-level dscl form if sysadminctl is unavailable:)
#   sudo dscl . -create /Users/gleipniragent
#   sudo dscl . -create /Users/gleipniragent UniqueID 510
#   sudo dscl . -create /Users/gleipniragent PrimaryGroupID 510
#   sudo dscl . -create /Users/gleipniragent UserShell /usr/bin/false
#   sudo dscl . -create /Users/gleipniragent NFSHomeDirectory /var/empty
# Verify:
dscl . -read /Users/gleipniragent UniqueID PrimaryGroupID
```

**(2) Single source of truth for the drop target (Pre-Mortem #3, D-F):**
```sh
# .gleipnir/agent-identity.env  — operator-owned, owner-writable only:
printf 'GLEIPNIR_AGENT_UID=510\nGLEIPNIR_AGENT_GID=510\n' \
  | sudo tee "$REPO/.gleipnir/agent-identity.env" >/dev/null
sudo chown "$(whoami)":staff "$REPO/.gleipnir/agent-identity.env"
sudo chmod 644 "$REPO/.gleipnir/agent-identity.env"   # readable, owner-write only
```

**(3) Ownership / group layout (Pre-Mortem #6):** operator owns all files; the
agent uid gets **group/other read of source**, and **write of Tier-0/1/2 only**
(`plans/`, `var/tmp/`, `logs/`, `memory/`, `lessons/`), while Tier-3 stays ro.
```sh
# Owner owns the whole repo:
sudo chown -R "$(whoami)":staff "$REPO"
# Source + config readable to all (agent needs to READ these):
sudo chmod -R a+rX "$REPO/src" "$REPO/.gleipnir"
# Tier-0/1/2 the agent may WRITE — grant the agent's group write there:
for d in .gleipnir/plans .gleipnir/var/tmp .gleipnir/logs .gleipnir/memory .gleipnir/lessons; do
  sudo chgrp -R gleipniragent "$REPO/$d" && sudo chmod -R g+w "$REPO/$d"
done
```

**(4) `chmod` the ENFORCEMENT_PATHS subtree OS-read-only to the agent uid**
(the LOCKED set — boundary.py:166-220; do not invent). Owner keeps write; group
+ other get **read + traverse only** (no write):
```sh
cd "$REPO/.gleipnir"
# File-level: agents/*.md, stage-role-map.md, AGENTS.md — owner rw, go read-only.
sudo chmod 644 agents/*.md stage-role-map.md AGENTS.md
# Directory-node hardening: explicitly go-w-strip (no new entries by group/other)
# and grant read+traverse (a+rX) to EVERY directory-type enforcement path — all
# 8 LOCKED ENFORCEMENT_PATHS treated explicitly, not by default-umask luck
# (review round R-1 added agents/ and keys/ to this line — previously only
# decisions/goals/sandbox/plugins were explicitly hardened here).
sudo chmod -R a+rX,go-w agents decisions goals keys sandbox plugins 2>/dev/null || true
# (plugins/ tolerates absence — the `|| true` covers an empty/absent dir.)
# NOTE: keys/ gets its dir-node hardened here (go-w, no group/other write of new
# entries); the KEY FILE ITSELF is then locked owner-only mode 600 in step (5)
# below — RO_AND_UNREADABLE requires the tighter file-level mode, which (5) sets
# AFTER this recursive dir pass so the 600 is not loosened by the a+rX above.
```

**(5) Place the G-3 key RO_AND_UNREADABLE — mode 600, owner-only (D3, PM #5):**
```sh
# The key lives under the ro boundary; only the OWNER (verifier) may read it.
sudo chown "$(whoami)":staff "$REPO/.gleipnir/keys/marker.key"
sudo chmod 600 "$REPO/.gleipnir/keys/marker.key"       # agent uid: no read, no write
export GLEIPNIR_MARKER_KEY_FILE="$REPO/.gleipnir/keys/marker.key"   # confirmed env var name
```
The verifier's `load_key` runs as owner (marker.py:86-106) → still readable to
it; the agent-uid read-probe reports read-denied → `keys/**` RO_AND_UNREADABLE
satisfied.

**(6) Launch-as-agent-uid wrapper (elevated; single-sourced uid/gid):**
```sh
# bin/gleipnir-launch  — operator-owned; run under sudo (root needed to setuid
# to another account on macOS). Sources the SAME agent-identity.env as the
# preflight (D-F) and asserts the exec'd account matches before launching.
#!/bin/sh
set -eu
here=$(cd "$(dirname "$0")" && pwd); repo=$(cd "$here/.." && pwd)
. "$repo/.gleipnir/agent-identity.env"          # GLEIPNIR_AGENT_UID / _GID (one source)

# 1. Fail-closed preflight AS OWNER, no override — must be CLOSED to proceed:
"$repo/bin/gleipnir-preflight" \
  --agent-uid "$GLEIPNIR_AGENT_UID" --agent-gid "$GLEIPNIR_AGENT_GID"
# (exit 0 = CLOSED; the wrapper stops here on 1/2 because of `set -e`.)

# 2. Drop to the agent account and exec opencode. `sudo -u#uid` requires root;
#    the assert below guarantees the run uid == the preflight's drop target.
exec sudo -u "#${GLEIPNIR_AGENT_UID}" -g "#${GLEIPNIR_AGENT_GID}" \
  /bin/sh -c '
    if [ "$(id -u)" != "'"$GLEIPNIR_AGENT_UID"'" ]; then
      echo "gleipnir-launch: run uid $(id -u) != drop target '"$GLEIPNIR_AGENT_UID"'" >&2
      exit 1
    fi
    exec opencode
  '
```
Install: `sudo chown "$(whoami)":staff bin/gleipnir-launch && sudo chmod 755
bin/gleipnir-launch`, then launch sessions with `sudo bin/gleipnir-launch`.
**bin/ is Tier-3/operator territory — the operator creates this file, not an
agent (D-C, D-D).**

### Enforces / bypass semantics
Enforces real OS denial of writes to the enforcement subtree and reads of the
key **by the agent uid**. The operator (owner) can still edit Tier-3 normally —
that is the intended, structurally-clean escape hatch (owner ≠ agent-uid;
Second-Order insight), **not** a bypass of the agent cage. The agent cannot
`chmod` back (it does not own the files) and cannot `setuid` to the owner
(needs root). The elevated launch requires root once, by the operator.

### Honesty label
**Cooperative-policy-until-applied → hard OS boundary once AC-4 passes.** Until
the operator performs these acts and the no-override preflight reports CLOSED
with an empty reasons list, the boundary is dev-mode (C1) — honestly labelled
`G-1 NOT closed (dev-mode)` every session.

### Handoff
This is an **OS/host + Tier-3** control; no roster agent can write it. To apply:
the operator runs steps (1)-(6) above, then the AC-4 acceptance test, then flips
per D-G/step 6. `gleipnir-plan` drafts this proposal file and stops (does not
implement — tier3-coach Anti-Pattern 3).

---

## Explicitly deferred (named, NOT planned — Scope-Creep guard, D-I)

- **B-literal / C-tier** — session-in-VM + remote verifier / "root inside yields
  nothing." Deferred until a threat model demands it.
- **E-1 credential isolation** — the broker/credential-unreachability half.
- **`keys/` digests + S-3 preflight verification wiring.**
- **Tier-2 review-gated memory-write pipeline.**
- **G-4d real cost figure** (rate table agent-unwritable).
- **Extending an OS-ro boundary to guard *code* under `src/`** — the guard code
  is protected today by not-granting-write + sandbox, not the config-dir ro
  boundary (brief Item 2 residual seam).

All are gated on this floor and unblocked *by* it, but each is its own later
slice and MUST NOT be folded into activation.
