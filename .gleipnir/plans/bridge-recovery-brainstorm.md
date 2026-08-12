# Design Brief: Recovery path for a stuck/stale G-5 pipeline bridge (L-C19)

**Status:** Tier-0 design brief (disposable). Authored by `gleipnir-brainstorm`
after operator convergence via the orchestrator. Produced with `tier3-coach`
(Detect → Locate → Propose → Converge → Handoff) + `decision-frameworks` (K-3).
This brief **does not implement anything** — the artifact it describes is
Tier-3/operator-authored code no roster agent can write. It is input to
`gleipnir-plan` (ATLAS) and, ultimately, an operator build-mode action.

---

## Problem Statement

The G-5 engine's signed pipeline bridge (`.gleipnir/var/run/pipeline-state.json`,
written by `Driver.write_bridge()` in `src/gleipnir/engine/driver.py`,
read/enforced fail-closed by `.gleipnir/plugins/sequence-gate.ts` on every `task`
delegation of an **armed** run — `GLEIPNIR_PIPELINE=on` + bridge present) has
**no in-framework recovery path** when it goes stale, corrupt, or stuck.

This happened for real this session (logged as **L-C19**): a bridge minted ~17
days prior — far past the gate's 1-hour freshness window
(`DEFAULT_MAX_AGE_SECONDS = 3600` in `src/gleipnir/engine/bridge.py`) — would
**fail-closed every `task` delegation** for any armed run. And **no roster
agent's permission grant covers `.gleipnir/var/run/` at all** (confirmed:
`grep var/run .gleipnir/agents/` → zero matches; orchestrator `edit:deny`/
`bash:deny`, git-ops `edit:deny`/`write:deny`, session-scribe scoped to
`plans/`+`var/tmp/`+one lessons file, code/plan/brainstorm deny all `.gleipnir/**`
outside their own `plans/**`). So the operator had to `rm` the file directly,
**outside the framework**, to unblock it.

**The missing control:** *who/what may inspect and safely clear/reset a stuck
bridge — without silently reintroducing the fail-open bug the current design
explicitly forbids.* A fail-closed enforcement mechanism needs a paired,
equally-deliberate **recovery** path, or "blocked" degenerates into "permanently
inaccessible until the operator intervenes out of band," which is a worse failure
mode than the one the gate prevents.

---

## Constraints

1. **The dominant safety invariant (no silent reset).** `driver.py`
   (`resume_from_bridge`, lines ~127-130) and its docstring **explicitly reject
   auto-reset-on-tamper as a fail-open bug**: "a fresh Driver at `BRAINSTORM` is
   never silently returned in place of an untrusted bridge (that would be
   fail-open — resetting the pipeline to the start on any tamper)." Any recovery
   that silently clears/resets on staleness or corruption *without deliberate
   authorization* recreates exactly the vulnerability the design was built to
   prevent (attacker plants a corrupt bridge → gate auto-resets to a permissive
   start → gate defeated). This is a **safety invariant, not a workflow
   preference.**

2. **Capability boundary (G-1 / G-2 / tier model).** The bridge is *enforcement
   evidence*. Its writer grant is the security-critical part — an agent-writable
   bridge makes the gate forgeable. No roster agent may hold write over
   `.gleipnir/var/run/`. The recovery artifact and its activation must live in
   Tier-3/substrate space the agent cannot reach (this is why the output is a
   *proposal*, not an edit).

3. **Precedent to honour.** `bin/gleipnir-preflight` **already exists** as an
   operator-only, out-of-framework CLI shim (identical shape to
   `bin/gleipnir-sandbox`), explicitly **not** granted to any agent's allowlist:
   *"This script is NOT granted to any agent's allowlist … a guard whose
   activation is validated by the population it guards is the G-3
   forgeable-evidence failure applied to activation."* It already dispatches
   subcommands (`config-scan`) over a shared fail-closed 0/1/2 exit-code
   convention (`src/gleipnir/preflight/__main__.py`). A bridge-recovery
   subcommand has a precedented, natural home here.

4. **Honest status (pre-S-2).** Like every guard in this scaffold, the artifact
   is cooperative-policy until the S-2 substrate boundary + terminal closure make
   the enforcement layer structurally agent-unreachable. The brief labels it
   honestly.

---

## Approaches Considered

**Option A — Operator-only audited CLI recovery subcommand**
(`bin/gleipnir-preflight bridge-status` / `bridge-reset`). Formalizes the manual
`rm` into a safe, repeatable, audited action on the *existing* out-of-framework
preflight CLI. `bridge-status` reports state / age / freshness verdict /
stale-or-corrupt diagnosis + the exact next command (read-only). `bridge-reset`
requires explicit confirmation, refuses under an in-framework uid, logs what it
did, and clears the bridge. Never in any agent allowlist. Because the reset is a
*deliberate, authorized operator act*, it does **not** reintroduce the fail-open
bug (the design forbids *silent* auto-reset, not *authorized operator* reset).

**Option B — Narrow write-grant carve-out to one roster role** for
`.gleipnir/var/run/pipeline-state.json` only, gated to re-mint via the real
`Driver` (never raw-delete). An in-framework role gains the ability to recover
the bridge during a run. **Rejected** (see Decision Analysis): letting a member
of the guarded population write the very state the guard trusts is a G-2
regression and the exact forgeability the bridge MAC + non-agent-writer grant
were designed to prevent.

**Option C — Read-only diagnostic capability** (a role, or the orchestrator,
gets `read` visibility to detect "bridge is stale/corrupt" and *report it clearly
to the operator with the exact recovery command*) with **no** write/clear
capability — recovery stays 100% manual/operator-only, but the diagnosis stops
being invisible. **Subsumed into A** as `bridge-status` (captures C's strongest
property — zero write capability for diagnosis — rather than discarding it).

**Option D — Bridge design change: TTL self-expiry / re-mint semantics** — make
a stale bridge self-clear or be transparently re-minted on next run rather than
fail-closing. **Rejected**: auto-clearing on staleness is *definitionally* the
fail-open the `driver.py` docstring names and forbids.

---

## Decision Analysis

> Reproduced faithfully from the analysis returned to the orchestrator and
> surfaced to the operator at convergence.

### Framework selection

Architectural tradeoff with a safety invariant and an irreversible failure mode
(defeating a security gate). Primary: **Weighted Decision Matrix** (4 distinct
options); followed by a **Pre-Mortem** on the leading option (high-stakes:
failure mode is a silently-defeated enforcement gate). **Reversibility Filter**
applied first.

**Reversibility Filter.** A and C are **Two-Way Doors** (add a CLI subcommand /
a read grant; trivially removable, no lock-in, no data loss). B is closer to a
**One-Way Door** in *risk* terms — once a roster role can write enforcement
evidence, that capability is exercised and depended upon; clawing it back is a
G-2 regression. D is a **One-Way Door**: it changes the security *semantics* of
the gate itself; a mistake is a live fail-open in production enforcement code. →
A/C fast-trackable on reversibility; B and D warrant the full matrix + pre-mortem.

### Weighted Decision Matrix

| Criterion | Weight | A (operator CLI) | B (role write-grant) | C (read-only diagnostic) | D (TTL/self-expiry) |
|---|---|---|---|---|---|
| Preserves fail-closed invariant (no silent reset) | 10 | 9 → **90** | 5 → **50** | 10 → **100** | 2 → **20** |
| Capability-boundary / G-2 integrity (no new agent power over enforcement evidence) | 9 | 10 → **90** | 3 → **27** | 7 → **63** | 9 → **81** |
| Solves the actual pain (un-sticks a blocked run) | 8 | 9 → **72** | 8 → **64** | 5 → **40** | 8 → **64** |
| Auditability of recovery action | 7 | 9 → **63** | 6 → **42** | 6 → **42** | 3 → **21** |
| Simplicity / uses existing precedent | 7 | 9 → **63** | 5 → **35** | 8 → **56** | 4 → **28** |
| Honest-status alignment (matches operator-only, out-of-framework preflight/sandbox pattern) | 6 | 10 → **60** | 4 → **24** | 7 → **42** | 5 → **30** |
| **Total** | | **438** | **242** | **343** | **244** |

**Ranking: A (438) > C (343) > D (244) ≈ B (242).**

**Caveats where the winner scores <10.** A scores 9 (not 10) on the fail-closed
invariant because a `bridge-reset` *does* write enforcement evidence — its safety
rests entirely on it being (a) operator-only/out-of-framework and (b)
confirmation-gated; if either erodes (e.g. someone later adds it to an allowlist
"for convenience"), it degrades toward B's risk. That is the pre-mortem's job to
fence. C's perfect 10 on the invariant (holds *no* write capability) comes with a
lower "solves the pain" score (5): C alone still leaves recovery a manual `rm` —
it removes the *blindness*, not the *manual step*. **A and C are not mutually
exclusive** — A's `bridge-status` *is* C's diagnostic. The strongest package is
**A (subsuming C's diagnosis via `bridge-status`), rejecting B and D.**

### Pre-Mortem on Option A (chosen path failed at 6 months)

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | `bridge-reset` gets added to an agent allowlist "for convenience," so the guarded population can clear the guard | M | **Critical** | Bake "NEVER agent-invocable" into the CLI header *and* a preflight/CI self-check that fails if `bin/gleipnir-preflight` appears in any `.gleipnir/agents/*.md` — same self-check pattern the file's own header already asserts |
| 2 | `bridge-reset` runs without confirmation (scripted / stray) and clears a legitimately mid-run bridge | M | High | Require explicit `--confirm-clear` (no default-yes); print old state + age; refuse if `GLEIPNIR_PIPELINE=on` in current env unless forced |
| 3 | Operator can't tell *why* it's stuck, resets a healthy bridge, masks a real tamper | M | High | `bridge-status` distinguishes **stale** (age > window, MAC valid) from **corrupt/tampered** (MAC invalid) from **healthy**; on tamper, warn loudly rather than offer one-touch reset |
| 4 | Reset re-mints a bridge at the wrong state (e.g. BRAINSTORM mid-pipeline) → silent pipeline reset, the exact fail-open | L | **Critical** | Default action is **clear (delete)**, forcing the next armed run to establish state deliberately — NOT re-mint. (Re-mint-at-state variant NOT adopted — see Selected Approach.) |
| 5 | The log of what reset did is itself unwritten/agent-writable → no audit trail | L | Medium | Log to `.gleipnir/logs/` (Tier-1, framework-process writer) with old state/minted_at/action/timestamp; CLI runs as owning uid so it can write there |

**Top risks:** #1 and #4 — both are "the recovery tool becomes the fail-open."
Both are mitigatable structurally (self-check that it's never in an allowlist;
default-to-clear-not-re-mint). **Verdict: Proceed with mitigations.** The
mitigations directly encode the design's own stated invariant.

### Bias check (12 detectors run; top 3 surfaced)

⚠️ **Status Quo Bias** — The current recovery (manual `rm`, out of band) could
get a free pass as "fine, the operator can just delete it." Under equal scrutiny
the manual `rm` is undiagnosed (operator had to investigate to find the file and
reason about the 1-hour window), unaudited, and error-prone (a wrong `rm` or a
by-hand re-mint could itself fail-open). "It worked once by hand" is not a
designed recovery path — which is L-C19's point.

⚠️ **IKEA / Availability Bias** — Option A is attractive partly *because*
`bin/gleipnir-preflight` already exists and the `rm` incident is fresh. Guard: A
wins the matrix on the *invariant* and *boundary* criteria (highest weights), and
wins even if you zero out the "uses existing precedent" row (438−63=375 vs C
343−56=287). Precedent strengthens A but is not what carries it.

⚠️ **Confirmation Bias** — Counter-evidence deliberately sought: **Option D is
the only option that removes the human from the loop** and is the most "elegant"
— and it is *correctly* near-last because auto-clearing on staleness is
definitionally the fail-open the docstring forbids. Its low score is a feature of
the constraint, not neglect. **Option C is genuinely competitive** and is not
dismissed — it is *folded into* A's `bridge-status`, capturing its strongest
property (zero write capability for diagnosis).

(Others checked, not strongly triggered: Sunk Cost — no; Anchoring — options
scored independently; Bandwagon/Authority — n/a.)

### Recommendation (advisory)

**Option A**, scoped to *subsume Option C*; **reject B and D.** (This is the
recommendation the operator converged on — see Selected Approach.)

---

## Selected Approach (operator-converged)

**Option A, scoped to subsume C — clear-only default. B and D explicitly
rejected.** Converged by the operator via the orchestrator; the operator did not
reconsider B and did not request the re-mint-at-named-state variant. Extend the
existing operator-only, out-of-framework `bin/gleipnir-preflight` CLI (over
`src/gleipnir/preflight`) with two subcommands:

- **`bin/gleipnir-preflight bridge-status`** — read-only diagnostic (= Option C).
  Reads `.gleipnir/var/run/pipeline-state.json` and reports: current
  `pipeline_state`, `minted_at`, **age vs the 1-hour freshness window**, and a
  classification of **healthy / stale / corrupt-or-tampered** (stale = age >
  window with a valid MAC; corrupt-or-tampered = MAC invalid; healthy =
  fresh + valid). Prints the **exact next command** to run. Safe to run anytime;
  holds no write capability.

- **`bin/gleipnir-preflight bridge-reset`** — audited recovery (Option A).
  - **Default action = clear (delete)** the bridge file. **Never re-mints at a
    state by default** (avoids the fail-open of resurrecting a permissive state;
    forces the next armed run to establish state deliberately). The
    re-mint-at-named-state variant is **NOT adopted.**
  - Requires an explicit **`--confirm-clear`** flag (no default-yes).
  - **Refuses to run under an in-framework uid** (operator/owning-uid only).
  - **Logs** old-state / `minted_at` / action / timestamp to `.gleipnir/logs/`
    (Tier-1, framework-process writer).
  - **Never in any agent allowlist**, guarded by a **self-check that fails if
    `bin/gleipnir-preflight` ever appears in any `.gleipnir/agents/*.md`** (the
    same "activation not validated by the guarded population" discipline the
    preflight header already asserts).

This turns "blocked → permanently inaccessible until an out-of-band `rm`" into
"blocked → operator runs one audited, confirmation-gated, out-of-framework
command that diagnoses (`bridge-status`) and, if needed, clears (`bridge-reset
--confirm-clear`)" — the paired *deliberate* recovery path L-C19 says every
fail-closed mechanism needs, without weakening the fail-closed posture.

### Correct layer & handoff (tier3-coach)

This is a **Tier-3 / substrate** control on two counts: the recovery-actor
question is a G-2 capability decision, and the code artifact lives in
operator-authored, agent-unwritable space (`bin/gleipnir-preflight`,
`src/gleipnir/preflight/`, plus the `.gleipnir/agents/*.md` self-check and a
preflight/CI wiring). **No roster agent can write or apply it.** This brief is a
proposal; implementation and activation are the **operator's** action in build
mode. Nothing here is implemented.

---

## Durable Tier-3 artifact to name (operator-authored)

Name for hand-off (the brief does not create it):

- **Decision record:** `.gleipnir/decisions/bridge-recovery-path.md` (Tier-3,
  operator-only). Records: the L-C19 gap; the converged **Option A
  (subsuming C), clear-only, B/D rejected** decision; the constraint that no
  *silent* reset is permitted (only a deliberate, operator-only, out-of-framework
  authorized clear); the pre-mortem mitigations (esp. #1 the never-in-allowlist
  self-check and #4 clear-not-re-mint); and the honest status
  (cooperative-policy until S-2 makes the enforcement layer structurally
  agent-unreachable).
- **Code artifacts (operator build-mode, no roster agent may write):**
  the `bridge-status` / `bridge-reset` subcommands on `bin/gleipnir-preflight`
  (thin shim) + their logic under `src/gleipnir/preflight/` (stdlib-only, per
  `decisions/runtime-and-deps.md`), and the allowlist self-check wiring.

**Next stage:** `gleipnir-plan` should run **ATLAS Architect/Trace** on this
converged brief to produce a **ready-to-apply plan with exact code** (subcommand
dispatch mirroring the existing `config-scan` pattern in
`src/gleipnir/preflight/__main__.py`; the classification logic against
`validate_state`/freshness; the uid refusal; the `.gleipnir/logs/` audit write;
the allowlist self-check; test-first coverage of the fail-closed / refusal /
clear-only paths), for the **operator to apply themselves in build mode**. Build
timing is deferred — the plan is prepared now, applied later by the operator.

---

## Open Questions

1. **Freshness window (1 hour) — NOT decided.** The incident involved a
   17-day-stale bridge; the current window is `DEFAULT_MAX_AGE_SECONDS = 3600`
   (`src/gleipnir/engine/bridge.py`). The operator has **not** made a call on
   whether 1 hour is the intended window. **Left explicitly open** for later — do
   not decide it in the recovery-path work. (Flagged, not scoped in.)
2. **Whether `bridge-status` should be a first slice on its own.** The operator
   converged on both subcommands; noting that a pure-diagnostic first slice
   (zero new write surface) remains a valid staging option if `gleipnir-plan`
   finds the reset ergonomics warrant separate delivery.
3. **B revisited later?** The operator did not want an in-framework recovery
   actor now. If a future persistent-session / self-healing model makes
   operator-presence-free recovery desirable, the G-2 cost of B would need
   re-evaluation then — out of scope now.

---

## Scope Sketch

**In scope (to be planned by `gleipnir-plan`, applied by operator):**
- `bin/gleipnir-preflight bridge-status` (read-only diagnostic; classification;
  exact-next-command output).
- `bin/gleipnir-preflight bridge-reset` (clear-only default; `--confirm-clear`;
  in-framework-uid refusal; `.gleipnir/logs/` audit; never re-mint).
- Allowlist self-check: fail if `bin/gleipnir-preflight` appears in any
  `.gleipnir/agents/*.md`.
- The `.gleipnir/decisions/bridge-recovery-path.md` durable record (operator
  writes).
- Test-first coverage: fail-closed paths, uid refusal, confirmation gating,
  clear-only behaviour, status classification (healthy/stale/corrupt).

**Out of scope:**
- The re-mint-at-named-state variant (explicitly not adopted).
- Any in-framework/roster-agent write grant to `.gleipnir/var/run/` (Option B,
  rejected).
- Any auto-clear/TTL/self-expiry change to the bridge/driver (Option D,
  rejected).
- Changing the 1-hour freshness window (open question #1 — undecided).
- S-2 substrate mount / terminal closure that makes the layer structurally
  agent-unreachable (later step; brief is honest about cooperative-policy
  status).

**Honesty label:** cooperative-policy-until-S-2. The operator-only /
out-of-framework property of `bin/gleipnir-preflight` is honoured by the roster
grants today (the shim is in no allowlist) and becomes *structural* only when the
S-2 boundary lands.
