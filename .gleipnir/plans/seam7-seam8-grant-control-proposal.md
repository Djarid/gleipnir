# Tier-3 Control Proposal: narrow write-grant for seam7/seam8 implementation

**Author:** `gleipnir-brainstorm` (tier3-coach workflow, Detect→Locate→Propose→Converge→Handoff).
**Status:** PROPOSE ONLY — no grant applied. Material tradeoffs surfaced for operator convergence.
**Trigger:** L-C27 gap, now a *live* blocker: the converged, spec-reviewed plan
`.gleipnir/plans/seam7-seam8-wiring.md` cannot be implemented because every file
its `test`/`code` stages must create/edit is outside every roster agent's write
capability.

---

## Gap

The seam7/seam8 plan requires creating/editing four Tier-3-protected artifacts.
**No roster agent can write any of them** (verified below), so the plan — though
converged and spec-reviewed — has no actor who can implement it. The operator
will NOT hand-write the feature bodies (that defeats the framework's delegation
premise) but WILL apply a small, precise Tier-3 *policy/grant* diff (matching the
`.github/**`, `bin/gleipnir-launch`, CI-workflow precedents). This is a
**safety-relevant control** (the grant governs the enforcement surface), not a
workflow preference — so the narrowest safe form matters.

## Correct layer

**Tier-3 POLICY** (`.gleipnir/agents/gleipnir-code.md` permission map) and, for
the target files themselves, **Tier-3 enforcement code** (`.gleipnir/plugins/**`)
and **agent-unreachable core** (`src/gleipnir/preflight/**`). Per the layer map,
no roster grant may write `.gleipnir/**`; the grant *change* itself is
operator-only. I (a subagent) cannot write any of it — which is exactly why this
is a proposal.

### Verified current grant state (read directly, not assumed)

| Target file/path | `gleipnir-code` grant | Any other roster agent? |
|---|---|---|
| `src/gleipnir/preflight/advance.py` (NEW) | `src/gleipnir/preflight/**: deny` (`gleipnir-code.md:17`) → **DENY** | No — see below |
| `src/gleipnir/preflight/fetch_attestation.py` (NEW) | same deny → **DENY** | No |
| `src/gleipnir/preflight/__main__.py` (EXISTING, dispatch add) | same deny → **DENY** | No |
| `.gleipnir/plugins/sequence-gate.ts` OR new `.gleipnir/plugins/advance-hook.ts` | `.gleipnir/**: deny` (`gleipnir-code.md:14`) → **DENY** | No |

`.gleipnir/plugins/**` is under the blanket `.gleipnir/**: deny` — confirmed;
there is no plugins-specific allow anywhere. **No other roster agent can write
these either**, confirmed by reading all nine agent frontmatters:

- `gleipnir-plan` / `gleipnir-brainstorm`: `edit: "*": deny`, only
  `.gleipnir/plans/**: allow` → cannot write `src/**` or `.gleipnir/plugins/**`.
- `quality-reviewer`, `notify`, `project-mgr`, `git-ops`: `edit: deny` +
  `write: deny` wholesale.
- `session-scribe`: only `.gleipnir/plans/**`, `.gleipnir/var/tmp/**`, and one
  named lessons file.
- `orchestrator`: `edit: deny`.

**L-C27 confirmed as a live blocker: the plan is currently unimplementable by
any actor except the operator hand-writing the bodies — which the operator has
refused.** The fix is a narrow write-grant to `gleipnir-code`, applied by the
operator, preserving TDD (same actor writes tests then bodies, in order).

Note the **`bin/gleipnir-sandbox`** entrypoint the tests run against is exact-match
granted in `bash` and unaffected; and `src/gleipnir/broker/git/mcp_server.py`
(the D5 sidecar-write edit) is NOT in `gleipnir-code`'s deny set today — the plan
flags that separately as an out-of-scope Tier-3 question. This proposal does not
touch the broker grant.

---

## Proposed artifacts (per target, narrowest safe form)

The last-match-wins semantics are confirmed by this agent's OWN existing `bash`
block (`gleipnir-code.md:22-33`): a `"*": deny` followed by exact-match `allow`
lines that override it. The same idiom applied to `edit` gives exact-path allow
overrides that must be placed **AFTER** the two deny lines so the later, more
specific match wins.

### Target 1 & 2 — the two genuinely NEW files (advance.py, fetch_attestation.py)

**Recommendation: exact-path allow, placed after the `preflight/**: deny`.** These
are net-new files the plan author must create; there is no safer indirection
(they don't exist to be written by any other mechanism). Exact-path (not glob)
keeps the grant to precisely the two named files.

### Target 3 — `__main__.py` (EXISTING file, dispatch add) — MATERIAL TRADEOFF #1

Two options, weighed (I did NOT default to "just allow the existing file"):

- **Option 3a — narrow allow on the existing `__main__.py`.** Simple; one more
  exact-path line. Cost: `gleipnir-code` gains write to the live dispatch file
  that already routes the agent-unreachable preflight subcommands
  (`bridge-status`, `bridge-reset`, `config-scan`, boundary preflight). A
  malformed edit there could disturb existing agent-unreachable entrypoints, and
  it widens the agent's reach into the existing preflight CLI surface by one
  live file.
- **Option 3b — dispatch-registration indirection.** Keep `__main__.py` fully
  denied; the two new subcommands (`advance`, `fetch-attestation`) register via a
  NEW file `gleipnir-code` CAN write (e.g.
  `src/gleipnir/preflight/_subcommands_seam78.py`), imported by `__main__.py`.
  Problem: `__main__.py` still needs a one-line `import` + two `if
  resolved_argv[0] == ...` dispatch branches added to its `main()` (lines
  107-124 are hand-rolled leading-token `if` branches, NOT a registry) — so
  **`__main__.py` must still be edited regardless**, unless we also refactor its
  dispatch into a registry first. That refactor is itself an edit to
  `__main__.py`. So 3b does NOT actually avoid touching `__main__.py` given the
  current hand-rolled dispatch; it adds a file and a refactor for no net
  reduction in the existing-file edit.

**My recommendation: 3a (narrow exact-path allow on `__main__.py`).** Given the
dispatch is hand-rolled `if` branches (verified: `__main__.py:107-124`), 3b
cannot avoid editing `__main__.py` without a prior registry refactor — so 3b buys
no safety, only added surface. 3a with an **exact-path** allow (not the `**`
glob) is the least-privilege form: exactly one existing file, still leaving the
rest of `preflight/**` denied. The blast-radius review at the hardened
spec-review pass covers the dispatch edit for the "disturbs existing
entrypoints" risk. **Surface this to the operator: 3a vs 3b.**

### Target 4 — the TS post-tool hook — MATERIAL TRADEOFF #2 (self-modifying-the-gate)

**FLAGGED EXPLICITLY, not defaulted past.** `sequence-gate.ts` is the file that
enforces the PRE-tool gate against `gleipnir-code`'s own `task` delegations. Its
own header (lines 7-9) states: *"No roster agent (not even gleipnir-code) may
edit it. It is the guard; it must not be reachable by the guarded (Axiom 2 /
G-1)."* Lines 28-30 note the post-tool advance hook is "NOT YET BUILT (parked)"
— i.e. exactly what this plan wires.

- **Option 4a — grant write to `sequence-gate.ts`.** The agent whose delegations
  the gate polices could edit the gate that polices it. This is a **direct Axiom
  2 / G-1 violation** and contradicts the file's own invariant. **Reject.**
- **Option 4b — NEW sibling `.gleipnir/plugins/advance-hook.ts`.** The plan
  explicitly allows this (`Trace` artifact table, line 161; `Assemble` Phase 2,
  line 315). `gleipnir-code` gets narrow write to the NEW post-tool file only;
  `sequence-gate.ts` (the pre-tool gate policing this same agent) stays **fully
  denied**. The guard that judges `gleipnir-code` remains unreachable by
  `gleipnir-code`. The post-tool advance hook is a distinct concern (the advance
  trigger, delegating all mint logic to Python) and cleanly separates.
  Trade-off: the shared helpers (`isArmed`, `loadKey`, `validateMarker`,
  `BRIDGE_REL`) currently live in `sequence-gate.ts`; the sibling must import
  them (opencode plugins can share modules) rather than duplicate — a DRY point
  for the code stage, not a grant concern.

**My recommendation: 4b (new sibling `advance-hook.ts`), materially safer.** It
keeps the pre-tool gate that polices `gleipnir-code` structurally unreachable by
`gleipnir-code`, honoring the file's own stated invariant and Axiom 2. Present
BOTH so the operator converges with the self-modification risk explicit.

### MATERIAL TRADEOFF #3 — temporary/session-scoped vs durable grant

- **Temporary loosening** (apply now, revert after the slice lands): minimizes
  the window the grant exists. Cost: a manual-revert obligation that is *itself*
  a control-hygiene risk — easy to forget, leaving an un-reverted widening on the
  enforcement surface with no record of why. There is no framework mechanism
  today that auto-reverts or even reminds.
- **Durable narrow allow** (add to `gleipnir-code.md` permanently): the grant is
  least-privilege *by exact path* — a small, fixed, named set of files
  (`advance.py`, `fetch_attestation.py`, `__main__.py`, `advance-hook.ts`). Once
  these files exist, the agent legitimately owns their maintenance (future test
  fixes, refactors) under the same pipeline. It is self-documenting (the grant
  lines sit in the frontmatter with the reason), and there is no forgotten-revert
  risk. Cost: the widening is permanent, so it must be genuinely minimal and
  exact-path (never glob).

**My recommendation: DURABLE, exact-path.** For a small fixed named set, durable
exact-path least-privilege is safer long-term than a session hack with a
forgotten-revert failure mode — provided the allows are exact paths (never
`preflight/**` or `plugins/**` globs). This matches the framework's own
"trust-is-a-property-of-the-path, encoded" model. Surface temporary-vs-durable to
the operator; if they prefer temporary, the same diff applies and they track the
revert.

---

## Ready-to-apply diff text (recommended path: 3a + 4b + durable exact-path)

Apply to `.gleipnir/agents/gleipnir-code.md`. The `edit:` block currently reads
(lines 12-17):

```yaml
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    ".github/**": deny
    "src/gleipnir/preflight/**": deny
```

Replace it with (the four exact-path allows placed AFTER their governing deny
lines, so last-match-wins grants exactly these files and nothing broader):

```yaml
  edit:
    "*": allow
    ".gleipnir/**": deny
    ".git/**": deny
    ".github/**": deny
    "src/gleipnir/preflight/**": deny
    # seam7/seam8 (L-C27): exact-path allows for the ONLY files this slice needs.
    # Placed after the preflight/** and .gleipnir/** denies so last-match-wins
    # grants exactly these named files. NOT globs — the rest of preflight/** and
    # .gleipnir/plugins/** stay denied. sequence-gate.ts (the pre-tool gate that
    # polices this agent) is deliberately NOT granted (Axiom 2 / G-1): the new
    # post-tool trigger lives in a sibling advance-hook.ts instead.
    "src/gleipnir/preflight/advance.py": allow
    "src/gleipnir/preflight/fetch_attestation.py": allow
    "src/gleipnir/preflight/__main__.py": allow
    ".gleipnir/plugins/advance-hook.ts": allow
```

**What this grants:** write to exactly four files —
`src/gleipnir/preflight/advance.py`, `.../fetch_attestation.py`,
`.../__main__.py` (existing, for the two dispatch branches), and the NEW
`.gleipnir/plugins/advance-hook.ts`. **What it leaves denied:** everything else
under `src/gleipnir/preflight/**` and ALL of `.gleipnir/**` including
`sequence-gate.ts`, `git-guard.ts`, `compaction-survival.ts`, keys, agents,
skills, decisions.

**Activation:** operator applies this edit to `.gleipnir/agents/gleipnir-code.md`
(build mode / operator hand — same handoff shape as prior Tier-3 grant edits). No
command beyond saving the file; opencode reloads the permission map for the next
`gleipnir-code` delegation.

**Enforces / bypass semantics:** the permission map is enforced by opencode's
tool-permission layer at delegation time. `gleipnir-code` still cannot reach git,
credentials, the pre-tool gate, or any other enforcement file. Under the uncaged
default this is cooperative-grant discipline (honest label below); it becomes
structural under S-2.

**Honesty label:** cooperative-policy-until-S-2. The deny/allow map is honored by
the roster grants today; the S-2 mount makes `.gleipnir/**` + the un-granted
`preflight/**` structurally unreachable later. This proposal claims no stronger
guarantee.

### If the operator instead chooses 3b (dispatch indirection)

Add a fifth allow for the new registration file and DROP the `__main__.py` allow
— but note (per Tradeoff #1) `__main__.py` must still be edited given its
hand-rolled dispatch, so 3b requires *either* a prior registry refactor of
`__main__.py` (still an edit) *or* keeping the `__main__.py` allow anyway (then
3b adds a file for no safety gain). I do not recommend 3b for this reason.

### If the operator chooses 4a (edit sequence-gate.ts directly)

Replace the `advance-hook.ts` allow line with
`".gleipnir/plugins/sequence-gate.ts": allow`. **I recommend against this** — it
grants the guarded agent write to its own pre-tool gate (Axiom 2 / G-1
violation, contra the file's own header). Presented only for completeness.

---

## Decision Analysis (for the operator to converge)

**Framework: least-privilege + reversibility/blast-radius (K-3).** Each choice is
"narrowest grant that unblocks the plan without weakening an invariant."

| Decision | Options | Recommendation | Why |
|---|---|---|---|
| #1 `__main__.py` edit | 3a narrow exact-path allow · 3b dispatch-indirection new file | **3a** | 3b can't avoid editing `__main__.py` (hand-rolled `if` dispatch), so it adds surface for no safety gain. 3a exact-path is least-privilege. |
| #2 TS hook location | 4a edit `sequence-gate.ts` · 4b new sibling `advance-hook.ts` | **4b** | 4a lets the guarded agent edit its own pre-tool gate (Axiom 2 / G-1 violation, contra the file's header). 4b keeps the gate unreachable. |
| #3 grant lifetime | temporary/session · durable exact-path | **durable exact-path** | Small fixed named set; durable exact-path avoids the forgotten-revert hygiene risk of a temporary loosening. Not a glob. |

**Bias check (12 detectors, salient ones):**
- *Default/status-quo bias:* actively resisted — I did NOT default to "just allow
  the existing file/glob"; 3a is chosen on merit (3b's indirection is illusory
  here), and globs are explicitly rejected in favor of exact paths.
- *Convenience-over-safety:* the 4a option (simplest — one file, no sibling) is
  rejected on the Axiom-2 invariant, not chosen for convenience.
- *Omission bias (temporary "feels safer"):* flagged — a temporary grant *feels*
  safer but carries a real forgotten-revert failure mode with no framework
  reminder; durable exact-path is argued as the genuinely lower-risk option.
- *Scope creep:* guarded against — every allow is an exact path; nothing under
  `preflight/**` or `plugins/**` is opened by glob.

**Recommendation summary: 3a + 4b + durable exact-path**, diff above.

---

## Handoff

This is a **Tier-3 POLICY** control (a permission-map edit to
`.gleipnir/agents/gleipnir-code.md`). I cannot write it — no subagent can. **To
apply:** the operator (build mode / operator hand, same as prior Tier-3 grant
edits) replaces the `edit:` block in `gleipnir-code.md` with the recommended
block above. Then the seam7/seam8 plan is implementable end-to-end by
`gleipnir-code` under the normal test-first pipeline (same actor writes
`tests/test_advance_hook.py` / `tests/test_fetch_attestation.py` first, then the
bodies, preserving TDD).

**Converge-worthy questions to put to the operator (with my recommendation):**
1. `__main__.py` dispatch edit — **3a** narrow exact-path allow (recommended) vs
   3b indirection?
2. TS post-tool hook — **4b** new sibling `advance-hook.ts` (recommended,
   materially safer) vs 4a edit `sequence-gate.ts` (self-modifying-the-gate
   risk)?
3. Grant lifetime — **durable exact-path** (recommended) vs temporary/session?

I do not implement. Diff is ready to apply verbatim for the recommended path
(3a + 4b + durable); the two alternative-path diff fragments are provided above
if the operator diverges on #1 or #2.
