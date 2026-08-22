# Tier-3 Control Proposal: `--profile <name>` selector for `bin/gleipnir-sandbox test|lint`

**Skill:** tier3-coach. **Phase:** Detect (handed in) → Locate → Propose → Converge (returned to orchestrator, NOT decided here).
**Standalone gap.** Addressed in parallel with — NOT as part of — the paused
`d5-sidecar-write.md` plan, which remains blocked pending this resolution (or an
operator decision to skip broker-profile verification for that slice). Do not
conflate the two.

---

## Gap

`bin/gleipnir-sandbox test|lint` (dispatch in `src/gleipnir/sandbox/__main__.py`)
resolves the toolchain profile **solely** from the single global
`default_profile` key in the Tier-3 `.gleipnir/sandbox/profiles.toml`
(`_resolve_dispatch_profile` → `resolve_profile(profiles)` with `name=None`, which
always returns `profiles.default_profile`). There is **no per-invocation
selector** — no CLI flag, no env var, nothing (deliberately so for the config
*location*; see "Was this a deliberate safety decision?" below).

**Consequence (workflow, forcing a Tier-3 round-trip):** whenever a test needs a
NON-default profile — `broker` (the only image carrying the MCP SDK) or `node`
(the cross-language `.mjs` seam) instead of the default `python` — the operator
must **hand-edit `default_profile` in the Tier-3 file**, run the suite, then
**hand-edit it back**. This exact manual round-trip is documented across at
least four prior plans:

- `git-enforcement-plugin.md` (lines 502–523): *"the CLI has no `--profile` flag
  and refuses extra selectors on this profile … As shipped today, the ONLY lever
  is `default_profile`"* — operator sets `default_profile = "broker"` for the
  run and *restores* it after.
- `broker-git-coverage-gap.md`, `broker-pm-coverage-gap.md` (Decision 4 in each):
  the broker test list + broker profile selection are flagged as an
  operator-only Tier-3 gate every time a broker test is added.
- `d5-sidecar-write.md` (current, paused): blocked on exactly this.

**Safety vs preference.** This is a **workflow-efficiency gap that cuts against a
stated design goal** ("the system needs to be programming-language agnostic";
`language-agnostic-sandbox.md`), NOT a safety invariant that is currently
unenforced. Nothing is *insecure* today — the manual round-trip is safe but
untenable. The material question the fix raises (does closing it widen the agent's
blast radius?) **is** safety-relevant and is surfaced in Decision Analysis below.

**Was the missing selector a deliberate safety decision?** Partly, and the
distinction matters. `language-agnostic-sandbox.md` (T3, "PROHIBITED") explicitly
foreclosed a `--config-path` / `--config-root` flag and any env-var override —
but that ban is about the **config LOCATION** (which arbiter file is read),
protecting the property "the agent cannot point the arbiter at a config it
controls." A `--profile <name>` selector that chooses **among profiles ALREADY
DECLARED in the fixed Tier-3 file** is a *different* axis and was **not** decided
against — it was simply never designed. Evidence it was anticipated as a clean
extension: `resolve_profile(profiles, name: str | None = None)` already takes an
optional `name`, and the module docstring already frames the agent as able to
influence *which tests run, never what command runs*. Selecting among
operator-blessed profiles is squarely inside that existing envelope.

---

## Correct layer

This gap touches **two layers**, and the split is the whole point:

| Change | Layer | Agent-writable? | Who applies |
|---|---|---|---|
| (i) Add `--profile <name>` flag to `test`/`lint`; validate against the profile names already loaded from the Tier-3 config; pass `name` into `resolve_profile` | **Source tree** (`src/gleipnir/sandbox/__main__.py`, tests) | **Yes** (`gleipnir-code`) | Bounded code agent, test-first |
| (ii) **Widen `gleipnir-code`'s bash allowlist** from exact-match `bin/gleipnir-sandbox test` to enumerated arg-bearing entries (`… test --profile broker`, `… --profile node`, `… --profile python`) so the agent can actually invoke the flag | **Tier-3 POLICY** (`.gleipnir/agents/gleipnir-code.md` — and any other test-running role) | **No** — every roster grant denies `.gleipnir/**` | **Operator** (build mode / escape hatch) |

The code half (i) is ordinary `src/` work needing no proposal. **This proposal
exists for half (ii):** the allowlist widening is a Tier-3 grant edit the agent
cannot and must not make — and it is *security-relevant*, not a rubber stamp,
because letting a bounded agent choose `--profile broker`/`--profile node` lets
it choose **which sandboxed IMAGE it runs in**. The `broker` and `node` images
carry a strictly larger trusted surface than the lean default `python` image
(the broker image is the ONLY one with the MCP SDK — pydantic/starlette/etc.).
That is a real blast-radius consideration (surfaced in Decision Analysis).

Confirmed: `gleipnir-code.md` bash allowlist is today **exact-match, no args**
(lines 33–36: `"bin/gleipnir-sandbox test": allow`, `… lint`, `./ ` variants),
with `"*": deny`. An arg-bearing invocation `bin/gleipnir-sandbox test --profile
broker` does **not** match any current allow entry and would be denied — so (i)
without (ii) is inert for the agent. (ii) is a genuine, unavoidable Tier-3 edit.

---

## Proposed artifact

Two artifacts. The code artifact (i) is what the operator's build session hands
to `gleipnir-code`; the Tier-3 artifact (ii) is what the operator applies.

### (i) Source — `--profile` selector (code agent, test-first; shown for completeness)

**Path:** `src/gleipnir/sandbox/__main__.py` (+ `tests/test_sandbox_cli.py`).
**Shape (not final code — the plan stage owns exact form):**

- Add `--profile <name>` to the `test` and `lint` subparsers, `default=None`.
- Thread `args.profile` into `_resolve_dispatch_profile(repo, config_root, name=args.profile)`,
  which passes it to the **already-existing** `resolve_profile(profiles, name)`.
- **Bounded-selection property (the safety hinge):** `name` is validated ONLY
  against `profiles.by_name` loaded from the FIXED Tier-3 file. An unknown name
  raises `ProfileError` → exit 3 (fail-closed), reusing the existing
  `resolve_profile` KeyError path. The agent can select **among operator-declared
  profiles**, and can **NEVER** invent a profile, an image, or a command — the
  strict image rule (`_validate_image`) and argv-list rule still gate every
  profile at load time. `--profile` with no value / omitted → `default_profile`
  (today's behaviour, unchanged).
- **Config LOCATION stays fixed** — this adds NO `--config-path`/`--config-root`
  and NO env override; the `language-agnostic-sandbox.md` prohibition is
  untouched. Only *which already-declared profile* is selectable, not *which file*.

**What it enforces / bypass semantics:** the selector is bounded by the Tier-3
profile set; an agent cannot escape it to an arbitrary image/command. Fail-closed
on unknown name.

### (ii) Tier-3 — `gleipnir-code.md` bash-allowlist widening (OPERATOR applies)

**Path:** `.gleipnir/agents/gleipnir-code.md` (frontmatter `permission.bash`).
**Content (exact enumerated entries — NO wildcard; last-match-wins after `"*": deny`):**

```yaml
  bash:
    "*": deny
    "bin/gleipnir-sandbox test": allow
    "bin/gleipnir-sandbox lint": allow
    "./bin/gleipnir-sandbox test": allow
    "./bin/gleipnir-sandbox lint": allow
    # --- NEW: bounded per-profile selection (this proposal) ---
    "bin/gleipnir-sandbox test --profile python": allow
    "bin/gleipnir-sandbox test --profile broker": allow
    "bin/gleipnir-sandbox test --profile node": allow
    "bin/gleipnir-sandbox lint --profile python": allow
    "bin/gleipnir-sandbox lint --profile broker": allow
    "bin/gleipnir-sandbox lint --profile node": allow
    "./bin/gleipnir-sandbox test --profile python": allow
    "./bin/gleipnir-sandbox test --profile broker": allow
    "./bin/gleipnir-sandbox test --profile node": allow
    "./bin/gleipnir-sandbox lint --profile python": allow
    "./bin/gleipnir-sandbox lint --profile broker": allow
    "./bin/gleipnir-sandbox lint --profile node": allow
    # --- existing denies unchanged ---
    "node --experimental-strip-types --test tests/test_sequence_gate.mjs tests/test_git_guard.mjs tests/test_advance_hook.mjs": allow
    "git*": deny
    ...
```

**Critical property — explicit enumeration, NOT a wildcard.** The entries are
**exact-match, one per (verb × declared profile name)**. There is deliberately
**no** `bin/gleipnir-sandbox test --profile *` pattern: a trailing wildcard would
be the AETOS enumerable-bypass hole this roster exists to close
(`bin/gleipnir-sandbox test --profile python; git push` would prefix-match).
Enumerating the three current profile names means: adding a *fourth* profile
later requires an operator allowlist amendment — which is the correct Tier-3 gate,
not a regression. (Note: exact-match also means `… test --profile broker -- <selector>`
would NOT match — selector passthrough on non-default profiles remains a separate,
already-refused surface. If the operator wants selector passthrough on broker too,
that is a distinct future grant, not folded here.)

**Activation:** operator switches to build (or uses the escape-hatch), edits
`.gleipnir/agents/gleipnir-code.md` to add the six/twelve enumerated lines above,
then (in caged mode) re-runs `bin/gleipnir-preflight` if the agent file is under
an enforcement path. The code half (i) lands first via the normal pipeline; (ii)
is the operator's Tier-3 grant.

**Enforces / bypass semantics:** widens the agent's capability by exactly the
enumerated arg-bearing invocations and no more. The agent gains the ability to
select the `broker`/`node` image for a test run; it gains **nothing** toward an
arbitrary image or command (those are still gated by the Tier-3 profile file +
strict image rule). The operator retains full control of *which* profiles exist.

**Honesty label:** **cooperative-policy-until-S-2** for the allowlist itself (the
`.gleipnir/**` deny is honoured by roster grants today; it becomes a structural
OS boundary only when S-2 lands). The bounded-selection property in the code
(i) is a **hard code property** the moment it ships (validation against the
loaded profile set is not bypassable via the flag).

---

## Decision Analysis (precept-10 — returned to the orchestrator to converge; NOT decided here)

**Decision to surface:** *How much CLI/allowlist surface do we expose to the
bounded `gleipnir-code` agent to end the Tier-3 `default_profile` round-trip — and
is letting the agent choose the `broker`/`node` image (a larger trusted surface
than the lean `python` default) an acceptable blast-radius widening?*

**Decision type:** capability-grant / blast-radius tradeoff (irreversible-ish: a
grant, once relied upon by the pipeline, is sticky). **Framework selected:
Reversible/Irreversible ("one-way vs two-way door") + a lightweight
Security-Blast-Radius weighing.** Rationale for selection: the core tension is
"convenience now" vs "a durable widening of a bounded agent's image-selection
capability" — the canonical door test plus an explicit blast-radius column is the
right lens; a full weighted-matrix is overkill for three options.

### Options

**Option A — `--profile <name>` flag + enumerated allowlist widening (the proposal above).**
- *Pros:* ends the round-trip permanently; language-agnostic goal served;
  bounded by the Tier-3 profile set + strict image rule + explicit enumeration
  (no wildcard); reuses the already-present `resolve_profile(name)` seam.
- *Cons:* genuinely widens `gleipnir-code`'s blast radius — it can now
  self-select the `broker` image (MCP-SDK trusted surface) or `node` image for a
  run. Adding a future profile needs an operator allowlist amendment (a gate, but
  ongoing cost). Two-layer change (code + Tier-3 grant).
- *Door:* mostly two-way — the grant can be narrowed/revoked later, but pipeline
  reliance makes it sticky in practice.

**Option B — code flag, but allowlist limited to `--profile broker` and `--profile node` ONLY (omit `python`).**
- *Pros:* everything in A, but the agent can only *escalate* to a non-default
  profile explicitly, and the default path (`… test` with no flag) still resolves
  `python` — so the common case is unchanged and the grant is minimally
  additive. Slightly smaller enumerated surface.
- *Cons:* asymmetric/subtle (why is `python` selectable-by-omission but not
  by-name?) — a small legibility cost. Functionally near-identical blast radius
  to A (broker+node are the surface-widening ones; python adds nothing).

**Option C — do NOT widen the agent; keep the round-trip an explicit operator step.**
- *Pros:* zero agent blast-radius change; the operator remains the sole selector
  of which image runs; simplest to reason about; honours the "don't hand the
  agent image-selection" instinct maximally.
- *Cons:* the untenable round-trip persists; directly against the stated
  language-agnostic goal and the operator's "this is untenable" flag; keeps
  blocking plans like `d5-sidecar-write.md` on a manual Tier-3 flip every time.
- *Door:* fully reversible (status quo).

### Bias check (12-detector scan — flagged only where live)

- **Status-quo bias:** live on C — "we never had a flag, so don't add one" is
  partly an inertia argument. Countered by the documented 4×-repeated pain and
  the explicit goal it violates. Weigh the goal, not the habit.
- **Confirmation bias:** the handoff framing leans toward A. Guard: B and C are
  presented as genuinely viable, and C's zero-widening virtue is real.
- **Anchoring:** the proposal artifact anchors on A's full enumeration. B (the
  narrower grant) is deliberately surfaced to break that anchor.
- **Security-theatre / over-provisioning:** live on A — enumerating `python`
  adds a grant that buys nothing (default already resolves python). B removes
  exactly that over-provision. Flagged for the operator.
- **Availability bias:** the broker/node need feels urgent because
  `d5-sidecar-write` is blocked *right now*; don't let one blocked slice justify
  a broader grant than the recurring pattern warrants (it does warrant broker+node).
- Remaining detectors (sunk-cost, framing, bandwagon, overconfidence, recency,
  authority, groupthink): not materially live here.

### Recommendation (advisory — the operator decides)

**Option B** — code `--profile` flag with the allowlist widened to
`--profile broker` and `--profile node` **only** (omit the redundant
`--profile python`, since bare `… test` already resolves `python`). It ends the
round-trip and serves the language-agnostic goal (like A) while making the grant
**minimally additive** and dodging the one over-provisioning bias flag against A.
The blast-radius widening (agent can select broker/node image) is real and
identical between A and B — so if the operator judges that widening
**unacceptable**, the honest choice is **C** (keep the operator round-trip), NOT
a false-comfort middle. The recommendation is explicitly *contingent on the
operator accepting that a bounded agent may self-select the broker/node image
within the Tier-3 profile set.* That acceptance is the operator's call — it is
the one material judgment this proposal cannot make for them.

---

## Handoff

This is a **two-layer** change and I (a brainstorm subagent) can write **neither**
half — I may write only `.gleipnir/plans/**`.

1. **Converge first:** the orchestrator relays the Decision Analysis above to the
   operator via `question`; the operator picks A / B / C (and, for A/B, explicitly
   accepts or rejects the agent-selects-broker/node-image blast-radius widening).
2. **If A or B:** the code half (i) — the `--profile` flag in
   `src/gleipnir/sandbox/__main__.py` + `tests/` — runs the normal pipeline
   (plan → spec-review → test → code → quality → git) via `gleipnir-plan` →
   `gleipnir-code`; it is ordinary `src/` work. The Tier-3 half (ii) — the
   `gleipnir-code.md` bash-allowlist widening — is an **operator action**: switch
   to build and add the enumerated (broker/node[/python per A]) allow lines shown
   above, then re-run `bin/gleipnir-preflight` if caged.
3. **If C:** no change; the operator continues the documented `default_profile`
   round-trip, and `d5-sidecar-write.md` proceeds only if the operator chooses to
   flip `default_profile` manually for that slice (or skips broker verification
   for it).
4. **Persist the decision:** whichever option, the outcome (especially an A/B
   acceptance of the blast-radius widening) belongs in a durable Tier-3 decision
   record — either appended to `.gleipnir/decisions/language-agnostic-sandbox.md`
   (its natural home) or its own record — since this plan is Tier-0 disposable.
   Operator-authored.

I do not implement either half. Proposal ends here.

---

## Convergence

**CONVERGED: Option A — add the `--profile <name>` CLI flag to
`bin/gleipnir-sandbox test|lint`, with `gleipnir-code`'s bash allowlist widened
to enumerate ALL THREE profile names explicitly (`--profile python`,
`--profile broker`, `--profile node`) for symmetry. Decided by the operator via
the orchestrator's `question` tool (real convergence — NOT self-attested by this
subagent).**

Date: 2026-08-22.

The A/B/C tradeoff writeup in `## Decision Analysis` above is left **intact** as
the record of what was considered; this section records only the resolution. The
earlier "recommendation only / NOT decided here / contingent on operator
acceptance" disclaimers in the Decision Analysis and Handoff sections describe
the state *before* this convergence — they are **superseded by this section, not
deleted**, so the deliberation record stays honest about how the decision was
reached.

**Not the recommended Option B, and not Option C.** This subagent recommended B
(omit the redundant `--profile python`); the operator chose **A**, explicitly
electing full three-name enumeration for **symmetry/legibility** over B's
minimal-grant narrowing. The over-provisioning bias flagged against A (enumerating
`python` buys nothing functionally, since bare `… test` already resolves `python`)
was surfaced and **knowingly accepted** by the operator in favour of a uniform,
predictable allowlist shape. Option C (keep the operator-mediated round-trip) was
rejected.

**Blast-radius widening — accepted.** The one material judgment this proposal
could not make (per the Decision Analysis: *is it acceptable for the bounded
`gleipnir-code` agent to self-select the `broker`/`node` sandbox image — a larger
trusted surface than the lean `python` default?*) is **resolved YES** by this
convergence. The operator accepts that the code agent may self-select the
broker/node image **within the fixed Tier-3 profile set** (still gated by the
strict image rule + argv-list rule + explicit no-wildcard enumeration).

**Resolved artifacts (Option A):**

1. **Code half (i) — agent-writable `src/`, normal pipeline.** Add `--profile
   <name>` to the `test` and `lint` subparsers (`default=None`), thread it into
   `resolve_profile(profiles, name)` (the already-present optional-`name` seam).
   Validate `name` ONLY against the profiles loaded from the FIXED Tier-3 file;
   unknown name → `ProfileError` → exit 3 (fail-closed). NO `--config-path`/
   `--config-root` and NO env override — the config LOCATION stays fixed (the
   `language-agnostic-sandbox.md` prohibition is untouched); only *which
   already-declared profile* becomes selectable. Bare `test`/`lint` (no flag) →
   `default_profile`, unchanged.

2. **Tier-3 half (ii) — operator applies to `.gleipnir/agents/gleipnir-code.md`,
   exactly as written in "Proposed artifact" above, ALL THREE names (Option A):**

```yaml
  bash:
    "*": deny
    "bin/gleipnir-sandbox test": allow
    "bin/gleipnir-sandbox lint": allow
    "./bin/gleipnir-sandbox test": allow
    "./bin/gleipnir-sandbox lint": allow
    "bin/gleipnir-sandbox test --profile python": allow
    "bin/gleipnir-sandbox test --profile broker": allow
    "bin/gleipnir-sandbox test --profile node": allow
    "bin/gleipnir-sandbox lint --profile python": allow
    "bin/gleipnir-sandbox lint --profile broker": allow
    "bin/gleipnir-sandbox lint --profile node": allow
    "./bin/gleipnir-sandbox test --profile python": allow
    "./bin/gleipnir-sandbox test --profile broker": allow
    "./bin/gleipnir-sandbox test --profile node": allow
    "./bin/gleipnir-sandbox lint --profile python": allow
    "./bin/gleipnir-sandbox lint --profile broker": allow
    "./bin/gleipnir-sandbox lint --profile node": allow
```

   **Explicit enumeration, NO wildcard** — a trailing `--profile *` would reopen
   the AETOS enumerable-bypass hole. Adding a FUTURE profile requires an operator
   allowlist amendment (the correct Tier-3 gate, by design).

**Still a two-layer change I cannot apply.** The Handoff section above remains
correct: half (i) runs the normal hardened pipeline via `gleipnir-plan` →
`gleipnir-code`; half (ii) is a Tier-3 POLICY edit to
`.gleipnir/agents/gleipnir-code.md` that every roster grant denies — applied by
the **operator** (or the operator-instructed-agent path under the uncaged-default
posture, `decisions/operating-posture.md`), and being enforcement-bearing it goes
through the two-pass spec-review + negative-check attestation the hardened track
requires. This convergence should also be persisted to a durable Tier-3 decision
record (append to `.gleipnir/decisions/language-agnostic-sandbox.md` or its own
record), since this plan is Tier-0 disposable. I did **NOT** touch
`src/**` or `.gleipnir/agents/gleipnir-code.md`; both edits are out of scope for
this subagent.
