# Design Brief: S-2 Activation — turning the verified boundary ON

> **STATUS: awaiting operator convergence.** This is a `gleipnir-brainstorm`
> subagent output. Per the precept-10 gate, the `## Decision Analysis` below is
> the **input to the operator's decision**, not the decision. The subagent's
> `question` tool cannot reach the operator, so no convergence is recorded here.
> The orchestrator must reproduce the `## Decision Analysis` **verbatim** to the
> operator and hand the converged choice back before this brief's "Selected
> Approach" is filled in and planning proceeds.

## Problem Statement

Gleipnir's S-2/G-1 machinery is **built and fail-closed but not activated**. The
preflight (`src/gleipnir/preflight/boundary.py` + `bin/gleipnir-preflight`)
behaviourally probes — as the agent uid, via a verified `fork`+`setgroups([])`+
`setgid`+`setuid` privilege drop — whether every enforcement path is OS-read-only
and the G-3 key OS-unreadable, and **REFUSES to launch** if not. The execution
sandbox (`bin/gleipnir-sandbox`, `--network=none`, ro source) bounds test/build
blast radius. But on the current **single-uid macOS dev box**, there is no OS
separation, so the preflight honestly reports `NOT_CLOSED` and the whole
`.gleipnir/` tree is still agent-writable in principle. Enforcement today is
**cooperative policy** (roster `deny` maps + prose), not a structural boundary.

**Activation** = performing the OS-level acts the preflight checks for, so that
enforcement stops being a promise the agent could break and becomes a wall the
OS enforces. This unblocks a chain of deferred items all gated on S-2: the
Tier-2 review-gated memory-write pipeline, the G-4d cost ledger's real cost
figure (rate table must be agent-unwritable), `keys/` digest + S-3 verification,
and the "root inside yields nothing" C-hardening direction.

This is a **material, partly-irreversible, operator-judgment decision**: a
botched boundary either **fails-open silently** (worst case — a false "CLOSED"
that isn't) or **bricks the operator's own workflow** (Tier-3 edits, which the
operator does routinely — including *this* session — now require stepping
outside the boundary). Hence the full K-3 treatment and the convergence gate.

## What is ALREADY DECIDED (do NOT reopen)

These are LOCKED in the decision records; activation must conform to them, not
relitigate them:

- **D-4 (`substrate-design-pass.md`):** Option B (container ro-mount) is the
  architectural core; Option A (OS uid + perms) is sanctioned "where containers
  are unavailable"; Option C (remote verifier) is the later hardening tier. They
  compose.
- **The v0.1 reframe (`s2-g1-closure.md` D1):** because opencode runs on the
  **host** (the container is only a build/test *executor*, not the agent's home),
  the v0.1 close is the **relocate-and-deny hybrid = Option A floor**, NOT
  containerising the session. B-literal is explicitly deferred to C-tier.
- **The CRUX:** uid separation verified by a **fail-closed** preflight. Already
  built; only `WRITE_DENIED` after a *verified* drop yields a CLOSED signal.
- **The enforcement-path set** (`boundary.py::ENFORCEMENT_PATHS`): `agents/*.md`,
  `stage-role-map.md`, `decisions/**`, `goals/**`, `keys/**`
  (`RO_AND_UNREADABLE`), `plugins/**` (tolerate-absent), `sandbox/**`,
  `AGENTS.md`. Skill *bodies* deliberately stay writable (methodology prose).
- **The escape hatch is out of scope (Part 0):** the preflight neither checks
  nor restricts the operator's built-in `/plan` `/build` agents.
- **Config-load-path (D2):** single `OPENCODE_CONFIG_DIR`, per-subtree perms;
  symlink escapes force `NOT_CLOSED`; per-file probing (a ro dir can hold a
  writable file).
- **Operator override:** the Part-0 `--override-ack` can only escalate
  `NOT_CLOSED → PROCEED_UNCLOSED` with an honest "dev-mode" label; it can NEVER
  manufacture `CLOSED`.

**Item 2 from the tasking (which subset is the S-2 ro-subset) is therefore
already RESOLVED, with one thing to confirm, not decide** — see "Confirmations,
not decisions" below.

## Constraints (environment ground truth — darwin, be concrete)

- **Host:** macOS 26.5.2, arm64 (Apple Silicon). opencode runs **on the host as
  the operator's user**, via `.envrc` `export OPENCODE_CONFIG_DIR=.gleipnir`.
- **macOS is real BSD-Unix at the host level:** `chmod`, POSIX file perms, and
  multiple local uids are genuine. `os.setuid`/`os.setgid`/`os.setgroups([])`
  (the preflight's drop) are POSIX and work on the macOS host. **Dropping to a
  *different* uid requires the launching process to be root** (or have the
  privilege) — a plain user cannot `setuid` to an arbitrary other uid. This is
  the central darwin feasibility fact for the uid-separation option.
- **Containers on macOS run inside a Linux VM** (podman `applehv`,
  `podman-machine-default`). So "B-literal, run the whole opencode session in a
  container" means running opencode **inside the Linux VM**, not on the host the
  operator drives — a materially different UX and a heavier lift. The sandbox
  already lives there for execution; the *session* does not.
- **macOS lacks Linux user-namespaces on the host** for cheap rootless uid
  remapping; real uid separation on the host means an actual second local
  account (`dscl`/`sysadminctl`-created user) and running opencode as it —
  which needs an elevated launch step.
- **Enforcement core is stdlib-only** (`runtime-and-deps.md`); no new deps.
- **Preflight is out-of-framework, run by the operator as the owning principal
  before each session, fail-closed** — already true; activation must not route
  its invocation into any agent allowlist.

## Approaches Considered (Item 1 — the activation TOPOLOGY)

Three genuinely distinct topologies for *where* the boundary is established on
this darwin host. All keep the already-built preflight as the verifier; they
differ in what OS separation they establish for it to verify.

### Approach A: Dedicated agent uid on the host + chmod OS-ro subtree

**Summary:** Create a second local macOS account (the "agent uid"), make the
operator the owner of the enforcement subtree, `chmod` that subtree ro (and the
key unreadable) to the agent uid, and launch opencode **as the agent uid** (via
an elevated wrapper). The preflight — run by the operator (owner) — drops to the
agent uid and verifies real denial.

**Tradeoffs:**
- Pro: This is exactly the model the preflight was **built and tested for**
  (`WRITE_DENIED` after a *real* cross-uid drop). Highest-fidelity `CLOSED`.
- Pro: Matches the resolved "Option A where containers are unavailable" (the v0.1
  reframe). No new architecture; it's the sanctioned floor.
- Pro: opencode still runs on the host — operator's editor/terminal UX unchanged;
  only the *account it runs as* changes.
- Con: **Requires an elevated launch step** (only root can `setuid` opencode to
  the agent uid). The operator must run opencode via a privileged wrapper, or
  pre-drop. This is real friction and a new failure surface.
- Con: A second account is macOS admin overhead (home dir, PATH, `.venv`
  ownership, git identity, keychain). The agent uid must still be able to *read*
  everything it needs and write only Tier 0/1/2 paths — perms must be gotten
  exactly right or the agent breaks.
- Con: Operator Tier-3 edits now require the operator to act as **owner** (their
  own account), which they already are — so this is actually the *cleanest*
  escape hatch (see Item 4).

**Estimated Scope:** OS acts (account creation, chmod script, launch wrapper) +
a decision-record amendment; no `src/` change (preflight already supports it).
Medium complexity, concentrated in operator/OS layer (tier3-coach territory).

**Risk:** Medium — the failure modes are "perms too tight → agent can't work"
(loud, safe) and "elevated wrapper misconfigured → drop doesn't happen"
(caught by the preflight's `DROP_UNVERIFIED`, which fails closed).

### Approach B: B-literal — run the whole opencode session inside the container/VM

**Summary:** Run opencode itself inside the Linux VM/container with the
enforcement subset ro-bind-mounted, per the literal Option-B "agent runs inside
the container" model. In-container writes to the mount are denied by the mount,
not by uid perms.

**Tradeoffs:**
- Pro: Strongest isolation story and the stated long-term direction (C-tier);
  "root inside the container yields nothing" becomes reachable.
- Pro: uid separation becomes unnecessary — the ro *mount* is the wall, which is
  conceptually cleaner than juggling macOS accounts.
- Con: **On macOS this means the operator drives opencode inside a Linux VM.**
  Major UX change: editor integration, terminal, git credentials, MCP brokers,
  keychain, and the operator's whole workflow relocate into the VM. This is the
  heavy lift the reframe **explicitly deferred** to C-tier.
- Con: The preflight was reframed *away* from this for v0.1 precisely because the
  host-run model made Option A the right floor. Choosing B now reverses a settled
  sequencing decision without the C-tier need being present yet.
- Con: Higher build cost, an availability dependency (VM must be up), and the
  broker/credential-isolation half (E-1) is still not closed by this alone.

**Estimated Scope:** Large — session-in-VM plumbing, mount layout, credential
relocation, MCP-over-boundary. High complexity. Effectively brings C-tier work
forward.

**Risk:** High — big surface, reverses a settled decision, and the darwin-VM UX
tax is borne every session by the operator. Over-scoped for "activate the floor".

### Approach C: Staged hybrid — advisory activation now, uid-floor next, B-literal deferred

**Summary:** Treat activation as a **ramp**, not a switch. (C1) First run the
preflight in **advisory/dev-mode** every session (`--override-ack`, honest
`PROCEED_UNCLOSED` "G-1 NOT closed (dev-mode)" label) so the operator *sees* the
real verdict and reasons on every launch without being blocked — a shakeout
period that surfaces any perms/UX problem before it can brick anything. (C2)
Then perform the Approach-A uid-floor acts and flip the launch to **hard
fail-closed** (drop `--override-ack`). (C3) B-literal/C-tier stays deferred until
a threat model needs it. This is A's endpoint, reached via a reversible on-ramp.

**Tradeoffs:**
- Pro: **Reversibility is maximised** — C1 changes nothing structural (the
  override can never fabricate `CLOSED`, so honesty is preserved), and it's a
  pure two-way door; only the C2 flip is the one-way-ish act, and by then the
  perms are proven.
- Pro: Directly de-risks the two pre-mortem catastrophes: a silent fail-open is
  impossible (C1 prints the real `NOT_CLOSED` reasons every session), and a
  bricked workflow is caught during C1 before hard-enforcement bites.
- Pro: Lets the operator experience the post-activation workflow (Item 4) *before*
  committing to it — the escape-hatch/edit-loop friction is measured, not guessed.
- Con: The intermediate state is **honestly-labelled cooperative policy, not a
  closed boundary** — an observer could mistake "we run the preflight" for "the
  boundary is closed". Mitigation: the `DEV_MODE_LABEL` is explicit and the
  override can never yield `CLOSED`.
- Con: Requires discipline to actually make the C2 flip and not camp in dev-mode
  indefinitely (status-quo drift). Mitigation: a named exit criterion / date.

**Estimated Scope:** C1 is near-zero (invoke existing preflight with a flag as a
launch habit) + a decision-record amendment; C2 = Approach A's scope later.
Low-now, medium-later. Concentrated in operator/OS + decision record.

**Risk:** Low for C1 (nothing structural changes, honest label); Medium for C2
(same as A, but now with a proven perms layout). Lowest aggregate risk of the
three.

## Decision Analysis

**Reversibility Filter (run first, per K-3):**
- **C1 advisory activation:** Two-Way Door — nothing structural changes; the
  override cannot fabricate `CLOSED`; revert = stop passing the flag. Fast-track.
- **A / C2 uid-floor flip (chmod ro + run-as-agent-uid + hard fail-closed):**
  **One-Way-ish Door** — reversible in *minutes* by `chmod`-ing back and dropping
  the wrapper, BUT the second macOS account, key relocation, and any perms the
  agent workflow comes to depend on make a *clean* revert non-trivial. Not truly
  irreversible, but high enough reversal-friction to warrant the deep frameworks.
- **B-literal:** One-Way Door in *practice* — relocating the operator's whole
  session into a VM reshapes credentials, MCP wiring, and habits; unwinding is a
  re-architecture, not a `chmod`. → Apply deeper analysis. (Done below.)

**Framework used:** Weighted Decision Matrix for the topology choice
(multi-option, A/B/C), then Pre-Mortem on the leading option (high-stakes,
irreversible failure modes: silent fail-open vs. bricked workflow), plus
Second-Order Thinking on the operator-workflow consequence. Selected per the K-3
auto-selection table (multi-option → Weighted Matrix; architectural/irreversible
→ Second-Order → Pre-Mortem).

### Weighted Decision Matrix (topology)

Criteria weighted by the framework's own priorities: **integrity > efficiency**
(a false-CLOSED is the worst outcome), honesty of the intermediate state, and
not-bricking the operator. Scores 0–10; cells show score×weight.

| Criterion | Weight | A: uid-floor | B: B-literal | C: staged hybrid |
|---|---|---|---|---|
| Fidelity of `CLOSED` (no silent fail-open) | 10 | 9 → 90 | 10 → 100 | 9 → 90 |
| Conformance to LOCKED decisions (v0.1 reframe = A floor) | 9 | 10 → 90 | 3 → 27 | 10 → 90 |
| Reversibility / low blast radius if wrong | 8 | 6 → 48 | 2 → 16 | 9 → 72 |
| Operator workflow preserved (darwin host UX) | 8 | 7 → 56 | 2 → 16 | 8 → 64 |
| Feasibility on this darwin box (no VM-session lift) | 7 | 8 → 56 | 3 → 21 | 8 → 56 |
| Minimal first-slice scope (activate the floor, not C-tier) | 7 | 7 → 49 | 2 → 14 | 9 → 63 |
| Unblocks the S-2-gated chain (memory pipeline, G-4d, digests) | 6 | 9 → 54 | 9 → 54 | 8 → 48 |
| **Total** | | **443** | **248** | **483** |

**Recommended by the matrix: Approach C (staged hybrid), 483**, narrowly over
Approach A (443); Approach B (248) is dominated. C wins because it reaches A's
endpoint while dominating on reversibility and workflow-preservation — the two
criteria where an activation mistake actually hurts. B loses decisively for
reversing the settled v0.1 reframe and imposing a VM-session tax with no present
C-tier threat justifying it.

**Caveat:** C's win over A is *entirely* the on-ramp; the destination is
identical (the uid-floor). If the operator has no appetite for a staged rollout
and wants the wall up now, A is the correct choice and only ~9% lower — the
matrix does not mandate C over a clear operator preference for A-now.

### Pre-Mortem (on the recommended path: C → uid-floor endpoint)

Assumed outcome at the 6-month horizon: **FAILURE.** Ways it went wrong:

| # | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Silent fail-open** — preflight prints `CLOSED` but a path is actually writable | Low | **Critical** | Already mitigated in code: only `WRITE_DENIED` after a *verified* drop yields CLOSED; `DROP_UNVERIFIED`/`PROBE_ERROR`/walk-error all force `NOT_CLOSED`. C1 dev-mode adds a human-visible reasons dump every session. Add: at C2 flip, operator eyeballs the reasons list is empty. |
| 2 | **Bricked operator workflow** — Tier-3 edits blocked; every doc tweak needs a privileged detour | Medium | High | The operator edits Tier-3 **as the owner (their own account)**, which is *outside* the agent uid the boundary cages — so their edits are unaffected (see Item 4). C1 shakeout proves this before C2. Document the exact "edit as owner, agent runs as agent-uid" loop. |
| 3 | **Elevated-launch misconfig** — wrapper fails to drop, opencode runs as owner, boundary silently absent | Medium | High | The preflight drops to the *agent* uid independently and would report `WRITE_OK` (owner can write) → `NOT_CLOSED` → REFUSE. So a mis-drop is caught, not hidden — *provided the preflight's `--agent-uid` matches the account opencode actually runs as*. Mitigation: derive both from one source; assert equality at launch. |
| 4 | **Camp in dev-mode forever** — C1 never advances to C2; "activated" is a fiction | Medium | Medium | Name an explicit C2 exit criterion + date in the decision record; the `DEV_MODE_LABEL` keeps the honest status visible so drift is not silent. |
| 5 | **Key relocation breaks marker/verify** — G-3 HMAC key made unreadable to agent also becomes unreadable to the verifier path that needs it | Low | High | `RO_AND_UNREADABLE` is agent-uid-unreadable; the verifier runs as owner. Confirm the verify/marker read path runs as owner (or a principal that can read the key) before the C2 flip; C1 surfaces a `key: ...` reason if not. |
| 6 | **Second macOS account rot** — `.venv`, PATH, git identity, keychain under the agent account drift and the agent breaks in confusing ways | Medium | Medium | Keep the agent account minimal; the agent needs read of source + write of Tier 0/1/2 only. Prefer running from the shared repo with the operator owning files and the agent-uid having group/other read. Document ownership/group layout. |

**Top risks:** #1 (silent fail-open — Critical) and #3 (mis-drop — the way #1
actually happens in practice). Both are structurally mitigated by the existing
fail-closed design *and* by C1's per-session reasons dump. **Verdict: Proceed
with mitigations** — the staged ramp exists precisely to exercise these before
hard enforcement.

### Second-Order Thinking (Item 4 — operator workflow post-activation)

- **First-order (near term):** enforcement becomes structural; the agent can no
  longer write Tier-3 even if a prompt convinces it to. The operator edits Tier-3
  as owner, unaffected. **Second-order:** the "switch to build mode to edit
  Tier-3" escape hatch we relied on *this very session* (to apply stage-role-map
  edits) becomes "edit as the owning account, which is what the operator already
  is" — arguably *simpler*, because owner ≠ agent-uid means the operator's normal
  editor already sits outside the cage. The clean escape hatch is **file
  ownership**, not a mode toggle, and it does not reintroduce the hole (the agent
  uid still can't write; only the owner can).
- **Far term (1–2 years):** the uid-floor is the stepping stone to C-tier
  (session-in-VM, remote verifier). **Second-order:** committing to the uid-floor
  now trains the operator's muscle memory on "owner edits, agent runs caged,"
  which is exactly the mental model B-literal/C-tier also use — so A/C is *not* a
  throwaway; it's the on-ramp to the endpoint, not a detour. **Third-order:** the
  S-2-gated chain (Tier-2 memory pipeline, G-4d real cost, digest verification)
  can only assert unforgeability *once this floor holds*; delaying activation
  keeps all of them honestly-labelled gaps.
- **Key insight:** the operator's escape hatch is **already** structurally clean
  under Approach A/C — because owner (operator) and agent-uid (opencode) are
  different principals, the operator's normal editing is *outside* the boundary
  by construction. No new "hole" is needed; the danger is only in getting perms
  and the launch-as-agent-uid wiring exactly right (Pre-Mortem #3, #5, #6).
- **Verdict: Proceed** — the workflow consequence is a net simplification, not a
  tax, provided the ownership/group layout is documented.

### Bias check (all 12 detectors run; top 3 surfaced)

- ⚠️ **Sunk Cost Fallacy** — "the preflight is built and tested for cross-uid
  drop, so we must do Approach A." *Guard:* the preflight supporting A is a
  genuine future-value argument (it's the tested path, lowest fidelity risk), not
  merely "we already built it." But state it as future value, not sunk cost. If
  starting fresh on darwin today, the uid-floor is *still* the right v0.1 floor —
  so the conclusion survives the sunk-cost test.
- ⚠️ **Status Quo Bias** — C's dev-mode on-ramp risks becoming a permanent
  resting place ("we run the preflight, good enough"), giving the *un*closed
  status quo a free pass. *Guard:* Pre-Mortem #4 + a named C2 exit criterion; the
  honest `DEV_MODE_LABEL` denies it the disguise of "closed."
- ⚠️ **Scope Creep Bias** — the temptation to fold B-literal/C-tier, credential
  isolation (E-1), and the digest/S-3 wiring into "activation" and thereby never
  ship the floor. *Guard:* the recommendation deliberately scopes activation to
  the **uid-floor only** (Item 5), with everything else named as explicitly
  deferred, later slices.

Others checked, not triggered strongly: Anchoring (the "Option B core" anchor is
correctly re-derived for host-run via the reframe, not blindly followed);
Confirmation, Availability, Bandwagon, Dunning-Kruger, IKEA, Survivorship,
Recency, Authority — no strong match.

**Recommendation (advisory — the operator decides):** **Approach C (staged
hybrid), landing on the Approach-A uid-floor.** Run the preflight in honest
dev-mode (`--override-ack`, `PROCEED_UNCLOSED`) as a launch habit **now** (a
pure two-way door, zero structural change), use that shakeout to prove the
perms/ownership layout and the launch-as-agent-uid wiring, then flip to hard
fail-closed once the reasons list is clean. Keep B-literal and C-tier deferred
until a threat model demands them. If the operator prefers no on-ramp, Approach
A (uid-floor now, hard fail-closed) is the correct fallback and is only ~9%
lower on the matrix — the choice between C-then-A and A-now is a genuine
operator-judgment call about appetite for a staged rollout vs. flipping the wall
up immediately.

## Confirmations, not decisions (Item 2 and Item 3 — already resolved; verify only)

These do **not** need operator convergence — they are settled and need only a
confirmation during planning:

- **Item 2 — the S-2 ro-subset:** `ENFORCEMENT_PATHS` in `boundary.py` **is** the
  authoritative set and already matches the classifier's Tier-3 `E` set in
  spirit. **One confirmation for the planner:** the preflight set covers
  `.gleipnir/`-internal enforcement paths but the classifier's `E` also names
  repo-root cross-cutting files (`opencode.jsonc`, `.gitignore`, `.envrc`,
  `pyproject.toml`) and the guard code under `src/gleipnir/{preflight,verify,
  engine,bus,ledger}`. **Surfaced mismatch:** these repo-root + `src/` guard
  files are *not* in the preflight's `ENFORCEMENT_PATHS`, because the preflight's
  subject is `OPENCODE_CONFIG_DIR` (`.gleipnir/`), while `src/` is (today) the
  agent-writable code tree that the sandbox and roster govern. This is a
  **known, intended** scoping (the reframe put the boundary at `.gleipnir/`; the
  `src/` guard code is protected by *not granting write* + sandbox, not by the
  config-dir ro mount). It is worth **naming for the operator** as a residual
  seam — "the guard *code* under `src/` is not yet under an OS-ro boundary; only
  its *config* is" — but it is not part of this activation slice and needs no
  decision here. (Deferred: extend the boundary to guard code when `src/` gets
  its own ro-mount, a C-tier item.)
- **Item 3 — G-3 key placement:** already decided (D3) — the key lives under the
  ro boundary, `RO_AND_UNREADABLE` to the agent uid via the existing
  `GLEIPNIR_MARKER_KEY_FILE`; no marker code change. Activation act = place the
  key file with owner-only read perms (mode `600`, owner = operator, not the
  agent uid) and point `GLEIPNIR_MARKER_KEY_FILE` at it. The `keys/` digests +
  S-3 verification wiring is a **separate, later slice** gated on this floor (per
  `gleipnir-layout-and-memory-model.md` lines 123–144) — name it, don't build it
  here.

## Scope / sequencing (Item 5 — the minimal first ACTIVATION slice)

**Minimal first slice (recommended):** the **advisory activation (C1)** — make
running `bin/gleipnir-preflight --agent-uid … --agent-gid … --override-ack` a
per-session launch habit, so the real `NOT_CLOSED` reasons are visible every
session, with the honest `DEV_MODE_LABEL`. Near-zero cost, pure two-way door,
zero structural change, and it turns the built-but-dormant preflight into a
live signal. This is the "dry-run / advisory activation intermediate" the
tasking asked about — and it already exists in the code (the override path).

**Second slice (the actual close, C2 = Approach A acts):** create the agent
account, lay out ownership/group + `chmod` the enforcement subtree ro to the
agent uid, place the key owner-read-only, wire the launch-as-agent-uid wrapper,
and flip to hard fail-closed (drop `--override-ack`). This is where a
**tier3-coach control proposal** is the right artifact: these are OS/account +
launch-wrapper acts the agent **cannot** perform — they must be a concrete,
ready-to-apply proposal handed to the operator (exact `dscl`/`sysadminctl` and
`chmod` commands, the wrapper, the key perms), never implemented by an agent.

**Explicitly deferred to later slices (do NOT fold into activation — Scope-Creep
guard):**
- B-literal session-in-VM + C-tier remote verifier.
- E-1 broker credential-unreachability half.
- `keys/` digest + S-3 preflight verification wiring, the Tier-2 review-gated
  memory-write pipeline, and the G-4d real cost figure — all gated on this floor
  and unblocked *by* it, but each its own slice.
- Extending an OS-ro boundary to guard *code* under `src/`.

## Selected Approach

**Choice:** Approach **C (staged hybrid), landing on the Approach-A uid-floor.**

**Convergence:** **OPERATOR-CONVERGED** at the precept-10 gate — the operator
decided via the orchestrator's `question` tool; this brief records that decision,
it was not made by the `gleipnir-brainstorm` subagent (whose `question` cannot
reach the operator). The converged choice matches the Decision Analysis's
advisory recommendation exactly. (Same convergence convention as
`prose-config-only-track-brainstorm.md` and `jsonc-agent-grammar-finding.md`.)

**What was converged, concretely:**

1. **Topology / ramp — Approach C (staged hybrid).** Run the already-built
   preflight in **honest dev-mode NOW** as a per-session launch habit:
   `bin/gleipnir-preflight --agent-uid … --agent-gid … --override-ack` →
   `PROCEED_UNCLOSED`, with the honest `DEV_MODE_LABEL` ("G-1 NOT closed
   (dev-mode)") and the full per-session reasons dump visible. This is the **C1
   slice** — a **pure two-way door**: nothing structural changes, and the
   override can never fabricate `CLOSED`, so the un-closed status stays honest.
   The C1 shakeout is used to prove the perms/ownership layout and the
   launch-as-agent-uid wiring. Then flip to **hard fail-closed (C2)** — perform
   the Approach-A uid-floor acts and drop `--override-ack` — once the per-session
   reasons list is clean.

2. **B-literal and C-tier stay DEFERRED.** Running the whole opencode session
   inside the container/VM (B-literal) and the remote verifier / "root inside
   yields nothing" (C-tier) are **explicitly deferred until a threat model
   demands them.** They are not part of S-2 activation; folding them in is the
   Scope-Creep failure the analysis guarded against.

3. **A named C2 exit criterion is REQUIRED** (Pre-Mortem #4 / Status-Quo-bias
   guard — the operator accepted this as a condition of choosing the staged
   ramp). C1 dev-mode **must not become a permanent resting place.** The flip
   from dev-mode to hard fail-closed (C2) is **gated on the preflight's reasons
   list being empty** — no `DROP_UNVERIFIED`, no `PROBE_ERROR`, no walk-error,
   and every enforcement path reporting `WRITE_DENIED` after a *verified* drop.
   Until that flip, the honest `DEV_MODE_LABEL` keeps the un-closed status
   continuously visible every session, so the intermediate state can never be
   mistaken for a closed boundary. The **specific date/trigger** for the flip is
   a plan-level detail for `gleipnir-plan` to propose; what is LOCKED here is
   that a named exit criterion is mandatory — dev-mode is a ramp, not a home.

**Rationale (Decision Analysis as justification):** the Weighted Decision Matrix
scored C highest (483) over A (443) and B (248); C reaches A's identical endpoint
(the uid-floor) while dominating on the two criteria where an activation mistake
actually hurts — **reversibility** and **operator-workflow preservation**. The
Pre-Mortem's two catastrophes (silent fail-open #1/#3, bricked workflow #2) are
structurally mitigated by the existing fail-closed design *and* by C1's
per-session reasons dump, which the staged ramp exists to exercise before hard
enforcement bites. Second-Order Thinking established that the operator's escape
hatch is *already* structurally clean under A/C (owner ≠ agent-uid → the
operator's normal Tier-3 editing is outside the cage by construction), so C is
the on-ramp to the endpoint, not a detour. The bias check's Status-Quo warning is
answered by requirement (3); Scope-Creep by the deferral in (2); Sunk-Cost by
noting the uid-floor is the right v0.1 floor even starting fresh.

## Next-stage handoff (`gleipnir-plan`, from this converged brief)

`gleipnir-plan` runs **ATLAS Architect/Trace** on this converged brief and does
**not** re-decide any material tradeoff (those are converged above). It produces
two coupled artifacts plus the exit criterion:

- **(a) The C1 advisory-activation slice as a buildable plan** — what is
  implementable *now, within the boundary*: the dev-mode launch habit and any
  within-boundary launch-wrapper or doc/scaffolding that makes running
  `bin/gleipnir-preflight … --override-ack` a per-session reflex and surfaces its
  reasons dump. No `src/` change to the preflight is needed (the override path
  already exists); this slice is launch-wiring + documentation, not new guard
  code.

- **(b) A tier3-coach-style control proposal for the C2 OS-level acts** — these
  are **Tier-3 / substrate acts that NO roster agent (including `gleipnir-plan`)
  can perform**; they must be a concrete, ready-to-apply proposal handed to the
  **operator**, never implemented by an agent (tier3-coach Anti-Pattern 3). The
  proposal must specify, ready-to-apply: create the dedicated agent OS uid (macOS
  `dscl` / `sysadminctl`); `chmod` the `ENFORCEMENT_PATHS` subtree OS-read-only
  to that agent uid; place the G-3 key `RO_AND_UNREADABLE` (owner-only, mode
  `600`, via the existing `GLEIPNIR_MARKER_KEY_FILE` — no marker code change);
  the launch-as-agent-uid wrapper (with `--agent-uid`/`--agent-gid` derived from
  a single source of truth so the preflight and the actual run agree —
  Pre-Mortem #3); and the ownership/group layout so the agent uid reads source +
  writes Tier 0/1/2 while Tier 3 is ro (Pre-Mortem #6). Written to
  `.gleipnir/plans/*-control-proposal.md` (Tier 0).

- **(c) The named C2 exit criterion** — recorded per requirement (3) above:
  reasons-list-clean gates the dev-mode → hard-fail-closed flip; `gleipnir-plan`
  proposes the specific date/trigger.

Everything else (B-literal/C-tier, E-1 credential half, `keys/` digest + S-3
wiring, Tier-2 memory pipeline, G-4d real cost, extending an OS-ro boundary to
guard code under `src/`) remains **explicitly deferred to later slices** and must
not be folded into activation.

## Open Questions (for `gleipnir-plan`, after convergence)

- Exact ownership/group model for the shared repo so the agent uid reads source
  and writes Tier 0/1/2 while Tier 3 is ro (Pre-Mortem #6).
- Where the launch-as-agent-uid wrapper lives and how `--agent-uid`/`--agent-gid`
  are derived from one source of truth so the preflight and the actual run agree
  (Pre-Mortem #3).
- Confirm the verify/marker read path runs as a principal that can read the
  owner-only key before the C2 flip (Pre-Mortem #5).
- Whether the C2 acts want a companion decision-record amendment recording the
  activation as LOCKED (they do — it's Tier-3).

## Scope Sketch

| Area | Files / artifacts likely affected |
|---|---|
| Advisory activation (C1) | Operator launch habit invoking existing `bin/gleipnir-preflight … --override-ack`; no code change |
| uid-floor acts (C2) | **tier3-coach control proposal** (`.gleipnir/plans/*-control-proposal.md`): agent account creation, chmod script, key perms, launch wrapper — operator-applied |
| Decision record | New/amended `.gleipnir/decisions/*.md` recording the activation (Tier-3, operator-authored via escape hatch) |
| Verify (confirm only) | `src/gleipnir/verify/marker.py` read path runs as key-readable principal (no change expected) |
| No change | `boundary.py`, `bin/gleipnir-preflight`, `ENFORCEMENT_PATHS`, sandbox — all already support this |
