# Design Brief: Override Paradigm — DEFAULT-uncaged, OPT-IN caged

> **Status: CONVERGED (Tier-0).** The operator LOCKED the paradigm direction
> (the *whether*) and has now **converged D1–D5** — the operator's choices were
> put to them via the **orchestrator's** `question` tool (the orchestrator can
> reach the operator; this subagent cannot) and handed back for recording. The
> `## Decision Analysis` below remains as the *justification* for each choice;
> the **Selected Approach (Converge)** section records the operator's converged
> decisions. This is NOT a self-attested subagent convergence — provenance is
> the orchestrator-routed operator decision. Recommendations in the Decision
> Analysis stay marked **ADVISORY ONLY**; the Converge section is authoritative.
>
> **This brief authors NO Tier-3 file.** The operator explicitly chose to keep
> authorship of the D3/D5 Tier-3 edits with themselves (even though the new
> default-uncaged paradigm would technically permit an agent to write Tier-3);
> the downstream plan produces ready-to-apply record text + banner diffs FOR THE
> OPERATOR TO APPLY. This brief edits neither `stage-role-map.md`, `AGENTS.md`,
> nor any `decisions/` record.

## Problem Statement

Gleipnir's current thesis treats the S-2 cage (Tier-3 read-only to the agent,
OS wall, unreadable key, agent-cannot-mutate-its-own-boundary) as the **always-on
terminal end-state** — the not-yet-reached goal every guard is marching toward.
The operator has decided to **invert the default**:

- **DEFAULT = UNCAGED.** The single human at the terminal is the trusted owning
  principal. "Build mode, do the work" means the agent may perform any act,
  *including* editing enforcement/Tier-3 config (`agents/`, `keys/`,
  `stage-role-map.md`, `decisions/`, …). This is not a deficiency; it is the
  intended operating posture for the attended, single-principal case.
- **CAGED = OPT-IN.** The operator can deliberately switch ON the high-assurance
  S-2 cage when the threat model calls for it (unattended/autonomous runs,
  sessions ingesting untrusted content, higher-assurance contexts).
- **Caging must NOT be the default.** Explicit reversal of the current
  always-on-goal framing.

The problem is therefore: *design the mode-selection mechanism, its granularity,
the superseding decision record, the honesty labelling, and the threat-model
boundary — reusing the already-built S-2 machinery where it fits, without
letting sunk cost force caged-as-default.*

### Two grounding facts (verified this session)

1. **The switch is largely already built.** The preflight
   (`src/gleipnir/preflight/`) has three verdicts —
   `CLOSED` / `REFUSE` / `PROCEED_UNCLOSED` — and an `--override-ack` flag that
   escalates a NOT-closed boundary to `PROCEED_UNCLOSED` with an honest label
   (`boundary.py:506,559-560`; `__main__.py:56-64,116-127`). That advisory path
   vs. the fail-closed path **is** an uncaged/caged switch in embryo. Crucially,
   `override_ack` can **never** yield `CLOSED` (`boundary.py:530-533`) — the only
   way to reach `CLOSED` is the full OS acts of the S-2 activation
   (`plans/s2-activation.md`, C2). So "caged" at its strongest is inherently an
   **operator-applied OS state**, not an agent-toggleable runtime flag.

2. **Tier-3 protection is DORMANT today.** In this very session the orchestrator
   was able to edit `stage-role-map.md` (a Tier-3 file) and the edit **succeeded**
   — the "Tier-3 = operator only (G-1)" invariant is currently *cooperative
   policy*, not tool-layer enforcement, for the primary agent. So **default-uncaged
   is already the de facto reality.** The paradigm change is partly *ratifying
   reality* and partly *making caged a deliberate opt-in* rather than the
   unbuilt-but-intended default.

## Constraints

- **Enforcement core is stdlib-only** (`decisions/runtime-and-deps.md`). No new
  deps for any toggle mechanism.
- **True OS-level caging cannot be toggled by the agent.** Dropping to a distinct
  uid needs root (POSIX / macOS `os.setuid`), and `chmod`-ing the enforcement
  subtree read-only is an operator/owner act. Any "caged mode" at the strongest
  (S-2) level is an operator-applied OS state (`plans/s2-activation.md` C2). A
  runtime flag can *select intent and gate launch*, but cannot itself *create*
  the OS wall.
- **The preflight is out-of-framework, operator-run, fail-closed.** Mode selection
  must not route the preflight's invocation into any agent allowlist
  (`s2-g1-closure.md` D4; `boundary.py`).
- **Reversibility asymmetry.** Flipping the *documented default* is a two-way
  door (prose + decision record). Applying the S-2 OS acts (create uid, chmod
  subtree, lock key) is heavier and operator-only, but is *itself* reversible
  (`chmod` back, delete account). The genuinely hard-to-reverse act is
  **publishing a threat-model claim** the framework then rests on (D5).
- **Honesty invariant must survive (non-negotiable).** Whatever the default, the
  operator must always KNOW which mode they are in at launch. The reversal is
  about *how the state is framed* (legitimate default vs. deficiency), never
  about hiding the state.
- **G-2..G-6 are not directly reversed.** This paradigm changes the *default
  posture of G-1's S-2 boundary* and the Tier-3-unwritable *default*. The broker
  single-holder (G-2), keyed evidence (G-3), bus (G-4), deterministic
  orchestration (G-5), and memory-poisoning model (G-6) are not repealed — but
  D2 must decide whether any minimal subset (notably the G-3 key) stays protected
  even in uncaged default.

## Approaches Considered

Three genuinely distinct strategies for *how* default-uncaged / opt-in-caged is
realised. (These are the top-level shape; D1–D5 refine the winner.)

### Approach A: Flip-the-default + reuse the existing preflight switch

**Summary:** Treat the paradigm change as almost entirely a *documentation +
default-flip* exercise. Uncaged is the default operating mode (run opencode
directly, as today); caged is opt-in and *is* the existing S-2 activation
(`plans/s2-activation.md`): run the fail-closed preflight + the operator's OS
acts. No new mechanism — the "mode" is which launch path the operator chooses.

**Tradeoffs:**
- Pro: Near-zero new build. The switch already exists (advisory vs. fail-closed
  preflight; `override-ack` present vs. absent). Ratifies verified reality.
- Pro: Honest by construction — the preflight already labels state every launch.
- Pro: Strongest-cage remains an operator OS state, which matches the hard
  constraint that true caging can't be agent-toggled.
- Con: "Mode" is implicit in *how you launched*, not an explicit recorded
  selection — easy to be unsure which mode a given session is in without reading
  the preflight output.

**Estimated Scope:** Tier-3 decision record (operator-authored) + relabel the
preflight's dev-mode string (D4) + a launch-habit doc. Complexity: **low**.

**Risk:** low — mostly prose + a default-flip; the machinery is proven.

### Approach B: Explicit mode selector (config flag / env var) driving launch

**Summary:** Introduce an explicit, recorded mode selector —
`GLEIPNIR_MODE=uncaged|caged` (env var or a small operator-owned config file) —
read at launch. `uncaged` (default) launches directly; `caged` requires the
fail-closed preflight to report `CLOSED` (and, at the strongest level, the S-2
OS acts to have been applied) or refuses to launch.

**Tradeoffs:**
- Pro: The mode is *explicit and legible* — every session records its intended
  posture; no guessing from launch path.
- Pro: A single obvious knob for the operator; scales to future automation.
- Con: A flag that *claims* caged without the OS acts is a **false-assurance
  trap** — the flag must be bound to the preflight verdict, not trusted alone
  (the flag cannot create the OS wall; see constraints). Adds a real design
  obligation.
- Con: Small new build + a new config surface that is itself enforcement-adjacent
  (who may write `GLEIPNIR_MODE`? — a Tier-3-class question).

**Estimated Scope:** A launch wrapper / env convention + binding the selector to
the preflight verdict + decision record + relabel. Complexity: **medium**.

**Risk:** medium — the flag-without-substance false-assurance path is the thing
to design out; if done wrong it re-creates a prose guard.

### Approach C: Per-tier granular posture (partial cage even in default)

**Summary:** Reject the single global toggle. Define posture *per Tier-3 subpath*:
a minimal always-protected set stays caged even in the uncaged default (candidate:
`keys/` — the G-3 key stays OS-unreadable), while the rest of Tier-3
(`stage-role-map.md`, `agents/`, `decisions/`, `goals/`) is agent-writable by
default. Full caged mode is then "extend the always-protected set to all of
Tier-3 + apply S-2."

**Tradeoffs:**
- Pro: Keeps the *cheapest, highest-value* protection (unforgeable-evidence key)
  even in the permissive default — a defense-in-depth floor.
- Pro: Matches the real threat asymmetry: an agent editing `stage-role-map.md`
  under operator instruction is intended; an agent reading the HMAC key silently
  defeats G-3 evidence for *all* sessions, which the operator likely never intends.
- Con: More moving parts — a per-path posture map is more to specify, test, and
  keep honest than a single toggle.
- Con: Partial protection can *feel* like caged when it isn't — labelling must be
  precise about "uncaged default WITH key-floor" vs. "fully caged."

**Estimated Scope:** Per-path posture definition + key-floor OS act (a subset of
the S-2 acts) + decision record + relabel. Complexity: **medium**.

**Risk:** medium — the value is real but the labelling/expectation-management is
the hazard; a "half-caged" state must never read as fully caged.

---

## Decision Analysis

Five material sub-decisions. Each is surfaced for **operator convergence** — the
recommendations are **ADVISORY ONLY**. The top-level Approach (A/B/C) is itself a
decision the operator makes, informed by D1–D2.

### D1 — Mode-selection mechanism

**Decision type:** Architectural tradeoff (long-term consequences) →
**Second-Order Thinking** primary, with a **Reversibility Filter** pre-pass.
**Bias watch:** Status-Quo Bias (defending old always-caged), Sunk-Cost
(over-reusing the built S-2 path just because it exists), Scope-Creep (adding a
flag *and* a per-tier map *and* the OS acts to avoid choosing).

**Reversibility Filter:**
- Choosing the *selection mechanism* (launch-path vs. env flag vs. per-tier map)
  is a **Two-Way Door** — swappable later with prose + a small wrapper change.
- The one **One-Way-Door-ish** element is the *false-assurance surface* a flag
  introduces: once operators trust `GLEIPNIR_MODE=caged` as meaning "safe," a
  later discovery that the flag was unbound is a trust breach. Bind it or don't
  introduce it.

**Options (Second-Order):**

| Option | 1st-order effect | 2nd-order (near) | 2nd-order (far) |
|---|---|---|---|
| (a) Launch-path only (Approach A) — caged = run S-2 activation; uncaged = run direct | Zero new surface; mode = how you launched | Operator must read preflight output to know mode | Simplest to keep honest; mode legibility depends on discipline |
| (b) Env/config flag `GLEIPNIR_MODE` (Approach B) | Explicit recorded intent | Must bind flag→preflight or it lies | If unbound, becomes a prose guard (the exact anti-pattern) |
| (c) opencode agent-permission profiles (a "caged" agent set vs default set) | Selects capability posture in-config | Only governs *agent* tool grants, NOT the OS wall or the key | Can *never* be the strong cage; useful only as a **coarse capability layer atop** (a)/(b) |
| (d) Combination: (a) launch-path as the substance + (b) a thin explicit selector for legibility | Explicit intent AND real substance | Selector must be bound to the preflight verdict | Cleanest legibility if the binding is designed in |

**Honest constraint (load-bearing):** true OS-level caging (S-2) requires the
operator's root acts and **cannot be toggled by the agent**. Any flag/profile is
at best *intent + launch-gate*; the wall itself is operator-applied OS state.
So (c) alone is insufficient (it governs agent tool grants, not the OS boundary
or key readability), and (b) alone is dangerous unless bound to the preflight.

**Bias warnings:**
- ⚠️ *Sunk-Cost watch:* the S-2 activation work is built and approved — that is a
  reason it *fits* as the caged path, **not** a reason to keep caged as default.
  Evaluated on future value, reusing the fail-closed preflight for the *opt-in*
  path is genuinely the least-build correct answer; keeping it *always-on* is the
  thing the operator is rejecting. The reuse is legitimate; the default is not.
- ⚠️ *Scope-Creep watch:* "do (a) and (b) and (c)" is tempting. Force the choice:
  substance lives in (a); (b) is only worth it for legibility *if bound*.

**Recommendation (ADVISORY ONLY):** **(d) — launch-path substance (Approach A)
as the real mechanism, optionally + a thin bound selector for legibility.** The
existing fail-closed-vs-advisory preflight already *is* the switch; the only
genuine open question is whether to add an explicit `GLEIPNIR_MODE` for
legibility, and if so it **must** be bound to the preflight verdict (a `caged`
selector that launches without a `CLOSED` verdict must REFUSE, never proceed).
Start with (a); add the bound selector only if the operator wants explicit
per-session mode recording.

### D2 — Granularity (global toggle vs. per-tier; minimal always-protected set)

**Decision type:** Architectural tradeoff → **Pros-Cons-Fixes** +
**Second-Order**. **Bias watch:** Status-Quo (all-or-nothing because that's how
S-2 was framed), Scope-Creep.

**Core question:** In the *uncaged default*, is there a **minimal always-protected
set** — or is uncaged truly all-or-nothing?

**Candidate always-protected floor:** `keys/` (the G-3 HMAC key stays
OS-unreadable to the agent even in default).

| Option | Pros | Cons | Fix |
|---|---|---|---|
| Global all-or-nothing (uncaged = *everything* writable incl. key) | Simplest to reason about + label | Agent reading the HMAC key silently defeats G-3 evidence for **all** sessions — a poisoning/forgery surface the operator almost never intends | Carve out the key as an always-protected floor → becomes the per-tier option |
| Per-tier: `keys/` always caged; `stage-role-map.md`/`agents/`/`decisions/`/`goals/` writable by default (Approach C) | Keeps cheapest highest-value protection always on; matches real threat asymmetry | More to specify/test; "half-caged" mislabel risk | Precise labelling: "uncaged (key-floor)" vs "fully caged"; the key-floor is a *subset* of the S-2 acts, cheap to apply |

**Second-Order insight:** editing `stage-role-map.md`/`agents/` under operator
instruction is the *intended* uncaged behaviour (that's the whole paradigm). But
the **G-3 key is different in kind**: its compromise is silent, cross-session,
and defeats the very evidence the framework uses to prove work happened (G-3.2,
memory integrity in `gleipnir-layout-and-memory-model.md`). The cost of keeping
it protected in default is one `chmod 600` (a strict subset of S-2 step 5).

**Bias warnings:**
- ⚠️ *Status-Quo (inverted form):* don't reflexively make uncaged "everything
  open" just because caged was "everything closed." The symmetry is a framing
  artifact, not a requirement. Evaluate the key on its own merits.
- ⚠️ *Scope-Creep watch:* resist expanding the always-protected floor beyond the
  key without a named threat justifying each addition — a big floor re-creates
  caged-by-default through the back door.

**Recommendation (ADVISORY ONLY):** **Per-tier with a minimal key-floor
(Approach C's core idea), not global all-or-nothing.** Keep `keys/` OS-unreadable
even in uncaged default (a `chmod 600` — subset of S-2); leave the rest of Tier-3
agent-writable by default. Label precisely as *"uncaged (key-protected floor)."*
This is a genuine operator tradeoff between minimalism (pure global toggle,
simplest) and defense-in-depth (key-floor). **The operator should decide whether
the key-floor is worth the small complexity/label cost.**

### D3 — What the superseding decision record must supersede + its thesis

**Decision type:** Documentation-integrity / scope enumeration (not a framework
choice) — but material, because a missed supersession leaves a contradictory
Tier-3 record standing. **Bias watch:** none dominant; completeness is the risk.

**Records / framings that flip from "always-on goal" → "opt-in mode"** (the
operator authors the superseding record; this brief only enumerates):

| Record / framing | Current thesis | Under new paradigm |
|---|---|---|
| `decisions/s2-g1-closure.md` | S-2/G-1 closure is the goal; single-uid box "fails closed: honest, no false claim"; "Pending operator activation" toward always-on | S-2 is the **opt-in caged mode**; uncaged default is legitimate, not "pending" |
| `decisions/substrate-design-pass.md` | "guards … *take effect last* … no session starts over an unverified boundary" (terminal closure as end-state) | Terminal closure is the *caged-mode* posture; default sessions run uncaged by design |
| `decisions/gleipnir-layout-and-memory-model.md` | "Tier 3 POLICY — agent-unwritable (G-1). Operator-authored only" as invariant | Tier-3-unwritable is the *caged-mode* property; uncaged default permits operator-directed agent Tier-3 writes (D2 may keep a key-floor) |
| `AGENTS.md` trust-tier table + guard-status "authored, not yet closed" | Tier-3 = "operator only (G-1)"; caging is the unbuilt end-state | Re-framed: default uncaged; caged is an available mode. **Operator edits AGENTS.md (Tier-3), not an agent** |
| `stage-role-map.md` (tier framing references) | implies always-on hardening | note the mode duality (no binding-table change needed for the paradigm itself) |
| `plans/s2-activation.md` D-G ("camp in dev-mode forever" as an anti-drift *failure*) | dev-mode is a temporary deficiency to escape via N≥5-clean flip | Under new paradigm, staying uncaged is a *legitimate default*, not drift — the anti-drift framing is superseded for the default case (still valid *within* an opt-in caged commitment) |

**Draft thesis statement (for the operator's new record — ADVISORY draft only):**
> *Gleipnir operates UNCAGED by default: the single human at the terminal is the
> trusted owning principal, and an agent under operator instruction may perform
> any act, including editing Tier-3 enforcement config. The S-2 cage (Tier-3
> read-only, OS wall, unreadable key, agent cannot mutate its own boundary) is a
> deliberately OPT-IN high-assurance MODE the operator switches on when the threat
> model requires it — not the default and not a not-yet-reached end-state. The
> uncaged default is a legitimate posture, not a deficiency; the honesty
> invariant (the operator always knows which mode a session runs in) is preserved
> in both modes.*

**Recommendation (ADVISORY ONLY):** The new record should be authored (operator,
Tier-3) as either a **new** `decisions/operating-posture.md` **or** a top-of-file
supersession banner added to each of the four records above pointing at it. A
single new authoritative record + short banners is cleaner than editing four
theses in place. **Operator authors it; no agent may.**

### D4 — Honesty labelling (uncaged-default must not read as "broken")

**Decision type:** Design of a user-facing signal → **Pros-Cons-Fixes**.
**Bias watch:** none dominant; the trap is *losing the honest signal* while
relabelling.

**Current state:** the preflight labels the advisory path
`"G-1 NOT closed (dev-mode)"` (`boundary.py:506`) and `__main__.py` describes it
as "dev-mode" with a reasons dump. Under the old thesis this correctly flagged a
*deficiency*. Under the new paradigm, uncaged is a *legitimate default* — calling
it "NOT closed (dev-mode)" mis-frames the intended posture as broken.

**Requirement (from the constraints):** keep the honest signal — the operator
must always know which mode — **without** framing the default as a failure.

| Option | Pros | Cons | Fix |
|---|---|---|---|
| Keep current label | Zero change; already honest about state | Frames the intended default as a deficiency; contradicts the paradigm | Relabel (below) |
| Relabel advisory verdict to a neutral mode name, e.g. `UNCAGED (default posture)` with the reasons list retained as *informational*, and reserve deficiency-language only for a caged-run that *failed* to close | Honest AND correctly-framed; preserves the reasons dump | Requires touching the preflight label strings (operator/Tier-3-class source? — see note) | Change is a string/label + exit-code-semantics doc, not a verdict-logic change; `REFUSE`/`CLOSED`/`PROCEED_UNCLOSED` machinery stays |

**Critical honesty distinction to encode:**
- **Uncaged default** → neutral, legitimate label (e.g. `UNCAGED — default
  operator-trust posture`), reasons list = *informational* ("these paths are
  agent-writable in this mode"), exit code non-failing.
- **Caged run that failed to close** → *this* keeps the deficiency language and
  fail-closed `REFUSE`. The operator asked for the wall and didn't get it — that
  IS an error and must stay loud.

So the relabel is **conditional on intended mode**, not a blanket softening.
That preserves the honest signal exactly where it matters (a *requested* cage
that didn't hold) while removing the false "broken" framing from the *default*.

**Note on who changes the label:** the label lives in
`src/gleipnir/preflight/boundary.py` (`DEV_MODE_LABEL`). `gleipnir-code` **denies**
`src/gleipnir/preflight/**` (per `s2-activation.md` D-C). So the relabel is a
source change gated to the operator / an explicitly-granted path — **surface this
as an implementation-routing item for the plan stage**, not an agent free-write.

**Recommendation (ADVISORY ONLY):** **Relabel conditionally.** Neutral,
legitimate label for uncaged-default (informational reasons list, non-failing
exit); retain fail-closed deficiency language ONLY for a *requested-caged* run
that fails to reach `CLOSED`. This keeps the honesty invariant while ending the
"default = broken" mis-frame. The exact strings are a plan-stage detail; the
*principle* (mode-conditional labelling) is the decision.

### D5 — Threat-model boundary (the assumption the default rests on)

**Decision type:** Risk assessment / go-no-go on a stated assumption →
**Pre-Mortem**. **Bias watch:** Availability (recent "the edit succeeded"
finding driving over- or under-reaction), Confirmation (only seeking evidence the
default is safe).

**The assumption the uncaged default explicitly rests on (must be stated in the
record so the tradeoff is eyes-open):**
> *Session access equals full operator authority, AND no untrusted content enters
> the agent's context during the session.* Under those two conditions, an agent
> editing Tier-3 is the operator editing Tier-3 by proxy — no privilege boundary
> is crossed.

**Pre-Mortem (assume the uncaged default caused a security failure):**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Untrusted content (a fetched page, a poisoned memory/log, a pasted payload) enters context and steers the agent to edit Tier-3 / read the key | **M** | **H** | The two named triggers to opt into caged mode: *ingesting untrusted content* and *unattended runs*. D2 key-floor blunts the key-read case even in default |
| 2 | Operator runs an *unattended/autonomous* session under the uncaged default, assuming attended-mode safety | M | H | Record states unattended runs REQUIRE caged mode; make it the first named opt-in trigger |
| 3 | Memory/log poisoning persists across sessions (the *Bad Memory* class, `gleipnir-layout-and-memory-model.md`) and later steers an uncaged session | L–M | H | G-6 memory model still applies; the key-floor (D2) preserves G-3 digest integrity so poisoning is detectable |
| 4 | Operator loses track of which mode a session is in and assumes caged | M | M | D4 mode-conditional labelling + (optionally) D1's bound explicit selector |
| 5 | "Uncaged default" is read by a *future* multi-agent/hosted deployment as license to skip caging where it's actually required | L | H | Record scopes the default explicitly to the **single-human-attended-terminal** case; hosted/multi-agent inherits the C-tier hardening direction (unchanged) |

**Top risks:** #1 and #2 — both are exactly the cases the opt-in caged mode
exists for. The mitigation is **naming the opt-in triggers precisely in the
decision record**, so the default's safety envelope is explicit.

**When the operator SHOULD opt into caged mode (for the record):**
- Unattended / autonomous / long-running agent sessions (no human watching).
- Any session that ingests untrusted external content (web fetch of untrusted
  pages, third-party repos, pasted/attached content of unknown provenance).
- Higher-assurance contexts (handling secrets, producing attested artifacts that
  others rely on, multi-agent or hosted operation → C-tier).

**Bias warnings:**
- ⚠️ *Availability watch:* the vivid "the Tier-3 edit succeeded this session"
  finding proves the default is *already de facto true* — it should inform the
  ratification, not stampede the threat model into either complacency or panic.
  The default is safe *within its stated envelope*; the record must state the
  envelope, not assert blanket safety.
- ⚠️ *Confirmation watch:* actively sought the counter-cases (#1, #3) rather than
  only cataloguing why the default is fine — that is why the opt-in triggers are
  named as hard requirements, not suggestions.

**Recommendation (ADVISORY ONLY):** **Proceed with the uncaged default, gated on
the record explicitly stating (a) the two-condition safety envelope and (b) the
three named opt-in triggers as REQUIREMENTS (not suggestions) for caged mode.**
The default is legitimate *only* with its envelope written down; an unstated
envelope is the actual risk. Pair with D2's key-floor for cheap defense-in-depth.

---

## Selected Approach (Converge)

**OPERATOR-CONVERGED.** The paradigm direction (default-uncaged / opt-in-caged)
was LOCKED by the operator; D1–D5 below were surfaced to the operator via the
orchestrator's `question` tool (the precept-10 gate — the orchestrator can reach
the operator, this subagent cannot) and the operator's converged choices were
handed back for recording. Provenance: **orchestrator-routed operator decision,
NOT a self-attested subagent convergence.** `gleipnir-plan` plans FROM these
choices and does NOT re-decide them.

| # | Decision | OPERATOR-CONVERGED choice | Rejected | Note for the plan |
|---|---|---|---|---|
| **D1** | Mode-selection mechanism | **Launch-path substance + preflight-bound selector.** Caged = run the S-2 activation OS acts, reusing the existing preflight fail-closed path; add a thin **optional** selector that MUST be bound to the preflight verdict — requesting "caged" without a `CLOSED` verdict **REFUSES** (no false assurance). Lowest new build. | opencode permission profiles **alone** (insufficient — govern tool grants, not the OS wall/key); an unbound flag (false-assurance) | The selector's binding to the `CLOSED` verdict is the load-bearing design obligation — a caged claim without the OS acts must REFUSE, never proceed. |
| **D2** | Granularity | **`keys/` protected floor kept even in uncaged default.** The G-3 key stays `chmod 600` owner-only even in the default uncaged posture (its compromise is silent / cross-session / defeats G-3 evidence; costs one `chmod`). Uncaged is **NOT** all-or-nothing. Label the default posture **"uncaged (key-protected floor)"**. | Global all-or-nothing (key writable/readable in default) | The key-floor is a one-time operator `chmod` (subset of the S-2 acts), applied even in uncaged default. |
| **D4** | Honesty labelling | **Conditional relabel.** Uncaged-default → neutral, legitimate label + informational reasons list + **non-failing** exit (NOT reported as a deficiency). Retain the fail-closed "NOT closed" deficiency language **ONLY** when a run **explicitly requested caged mode and did not reach `CLOSED`**. | Blanket-keep the current `"G-1 NOT closed (dev-mode)"` deficiency framing for the default | **Routing (carry into the plan):** the label text lives in `src/gleipnir/preflight/boundary.py`, which `gleipnir-code` **DENIES** — this sub-item is **operator-applied or requires an explicit grant**; the plan MUST flag it as such (hardened path). |
| **D3/D5** | Superseding record + threat model + authorship | **New operator-authored `decisions/operating-posture.md`** stating: the new thesis (default = agent unconstrained on operator instruction; caged = opt-in high-assurance mode); the threat-model envelope (*session access = full operator authority AND no untrusted content enters the context*); and the **three named opt-in-caged triggers as REQUIREMENTS** — (1) unattended/autonomous runs, (2) untrusted-content ingestion, (3) higher-assurance/hosted/multi-agent contexts. PLUS supersession banners on the four affected records: `decisions/s2-g1-closure.md`, `decisions/substrate-design-pass.md`, `decisions/gleipnir-layout-and-memory-model.md`, and the `.gleipnir/AGENTS.md` trust-tier/guard-status framing. | In-place thesis rewrites without a single authoritative record; agent-authored Tier-3 edits | **The OPERATOR authors these Tier-3 edits** — the operator explicitly chose to keep authorship with themselves even though default-uncaged would technically permit an agent write. The plan produces **ready-to-apply record text + banner diffs FOR THE OPERATOR TO APPLY**, not agent-applied. |

**Converged top-level shape:** Approach A (flip-the-default + reuse the existing
preflight switch) as the substance, refined by D2's `keys/` floor (Approach C's
core) and D1's preflight-bound optional selector (Approach B, bound not unbound).

## Open Questions (all D1–D5 RESOLVED; residual plan-stage items only)

- **D1 — RESOLVED** (launch-path substance + preflight-bound selector). Residual
  plan-stage detail: the exact mechanism binding `caged` selection to a `CLOSED`
  preflight verdict so a caged request without the OS acts REFUSES.
- **D2 — RESOLVED** (`keys/` protected floor kept even in uncaged default).
  Residual plan-stage detail: whether the preflight surfaces a distinct
  "key-floor" sub-verdict in the uncaged-default label.
- **D3 — RESOLVED** (new operator-authored `decisions/operating-posture.md` +
  supersession banners on the four records; operator-applied).
- **D4 — RESOLVED** (conditional relabel). Residual plan-stage **routing** item:
  the label lives in `src/gleipnir/preflight/boundary.py` (`DEV_MODE_LABEL`),
  which `gleipnir-code` DENIES — operator-applied or explicit-grant; hardened
  path. The plan MUST flag this.
- **D5 — RESOLVED** (threat-model envelope + three opt-in triggers as
  REQUIREMENTS, recorded in `operating-posture.md`).
- **Residual (not a D1–D5 item):** `s2-activation.md` D-G reconciliation — the
  N≥5-clean-session anti-drift gate was designed to *escape* dev-mode; under the
  new paradigm it applies only *within an opt-in caged commitment*, not to the
  default. The plan should note this framing update (Tier-0 note).

## Scope Sketch

| Area | Files/Modules Likely Affected | Who |
|---|---|---|
| New Tier-3 decision record (paradigm thesis, envelope, opt-in triggers) | `decisions/operating-posture.md` (new) + supersession banners on `s2-g1-closure.md`, `substrate-design-pass.md`, `gleipnir-layout-and-memory-model.md` | **Operator only (Tier-3)** |
| Trust-tier / guard-status re-framing | `AGENTS.md` trust-tier table + guard-status wording | **Operator only (Tier-3)** |
| Preflight relabel (mode-conditional honesty) — D4 | `src/gleipnir/preflight/boundary.py` (`DEV_MODE_LABEL`), `__main__.py` help text | Operator / explicitly-granted path (NOT default `gleipnir-code`) |
| Optional explicit mode selector — D1(b/d) | launch wrapper / env convention (`bin/`, operator territory) | **Operator** |
| Key-floor OS act — D2 | one-time `chmod 600` on `keys/marker.key` (subset of S-2) | **Operator** |
| Launch-habit / mode doc | `.gleipnir/plans/*.md` (Tier-0) | roster writer OR operator |
| Reconcile `s2-activation.md` framing (opt-in, not end-state) | note in `plans/s2-activation.md` (Tier-0) | roster writer / operator |

**Blast-radius note for the plan stage:** the paradigm's substantive edits land
on Tier-3 (`decisions/`, `AGENTS.md`) and enforcement-bearing source
(`preflight/`) → the plan runs the **HARDENED review path** (two distinct
spec-conformance + blast-radius passes + negative-check attestation), and the
Tier-3 edits are **operator-applied**, not agent writes.
