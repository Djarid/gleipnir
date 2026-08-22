# Tier-3 Control Proposal: host-run bash grant for the `.mjs` golden-fixture suites

**Status:** proposal only — Tier-3 grant edit, operator-applied. NOT implemented here.
**Skill:** tier3-coach (Detect → Locate → Propose → Converge → Handoff).

## Gap

No roster agent can host-run the `.mjs` golden-fixture conformance suites
(`tests/test_sequence_gate.mjs`, `tests/test_git_guard.mjs`, and the new
`tests/test_advance_hook.mjs`). These suites are, by an **already-converged**
repo decision, run **directly on the host** with `node --test` — NOT sandboxed
— because the S-2 python sandbox image has no node and no fixture harness
(`config-scan-precommit-hook.md:166-174`, `test_precommit_hook.sh:17-22`, and
each `.mjs` file's own header). This proposal does **not** re-open that
decision; it only closes the missing grant for that already-accepted risk class.

- **What is unenforced / blocked:** `.gleipnir/plans/seam7-seam8-wiring.md`
  Phase 2 cannot be verified — `test_advance_hook.mjs` (19 tests, authored this
  session) has no agent that can run `node --test` against it. Today the run
  falls to the build-session/orchestrator by hand.
- **Safety vs preference:** this is a **capability/workflow gap**, not a safety
  invariant. Nothing dangerous is currently unenforced; a legitimate,
  already-accepted verification action simply has no roster holder.

### Why the node profile does not fix this (fact #1, confirmed)
`.gleipnir/sandbox/profiles.toml` DOES declare `[profile.node]` (line 38-45,
running both `.mjs` files via `node --experimental-strip-types --test …`), but
`src/gleipnir/sandbox/__main__.py::_resolve_dispatch_profile` (L101-108) always
resolves `default_profile` (`"python"`) and passes **no** name override to
`resolve_profile()`. Confirmed against the module docstring (L15-18: "no name
override on the agent-facing path"). The node profile is structurally
**unreachable** via `bin/gleipnir-sandbox test|lint` for agent OR operator, by
explicit design. So the sandbox entrypoint cannot be the vehicle; a direct
host `node` grant is the only path for the host-run class.

## Correct layer

**Tier-3 POLICY** — a roster agent's `permission.bash` allowlist in
`.gleipnir/agents/<role>.md`. Per the tier3-coach layer map and
`.gleipnir/AGENTS.md`, every roster grant denies `.gleipnir/**` edits; no agent
(including the target `gleipnir-code`) can write its own frontmatter. Confirmed:
`gleipnir-code.md` `edit` block denies `.gleipnir/**` (L14). **This is why the
output is a proposal, not an edit** — I cannot and must not write it.

## Verified facts (I confirmed each; did not take them on trust)

1. **Node profile unreachable** — confirmed (see above). ✓
2. **Host-run is already-converged, not re-litigated** — `test_precommit_hook.sh:17-22`
   and `config-scan-precommit-hook.md:166-174` both state the `.mjs` suites are
   host-run directly. Each `.mjs` header repeats it. Not touched by this proposal. ✓
3. **No roster agent grants `node`** — `gleipnir-code.md` bash (L31-43) is
   exact-match `bin/gleipnir-sandbox test|lint` (+ `./`-prefixed) only, explicit
   denies `sh*/bash*/env*/curl*/git*/gh*/glab*`, catch-all `"*": deny`.
   `git-ops.md` bash (L31-43) is git-verbs-only + `sh*/bash*` deny + `"*": deny`.
   Neither grants `node`. ✓
4. **New file exists and needs the run** — `tests/test_advance_hook.mjs` present
   (454 lines, `glob` confirmed), header cites `seam7-seam8-wiring.md` Phase 2,
   invocation `node --experimental-strip-types --test tests/test_advance_hook.mjs`. ✓
5. **All three files import `.ts`** → all three need `--experimental-strip-types`
   (grep confirmed: `test_sequence_gate.mjs:16,66` → `sequence-gate.ts`;
   `test_git_guard.mjs:21` → `git-guard.ts`; `test_advance_hook.mjs:45-46` →
   `advance-hook.ts` + `sequence-gate.ts`). NOTE: `test_git_guard.mjs`'s own
   header comment (L12) says plain `node --test` with no flag — that comment is
   **under-specified**; it imports `git-guard.ts` and so also needs the flag.
   The sandbox `[profile.node]` correctly runs it WITH the flag. ✓
6. **`node --test` accepts multiple file args in one invocation** — the repo's
   own `[profile.node]` test line does exactly this today:
   `["node","--experimental-strip-types","--test","tests/test_sequence_gate.mjs","tests/test_git_guard.mjs"]`.
   So a single combined exact-match line covering all three is viable and is the
   repo's established shape. ✓
7. **Zero third-party deps** — all imports are `node:` builtins + local
   `.ts`/fixture files (grep confirmed). Matches the accepted-risk-class claim:
   no network, pure-function + fixture-based. ✓
8. **UNVERIFIABLE from filesystem — MUST be operator-confirmed:** the **host**
   `node` version. `Containerfile.node` (L6-10, 20-22) pins the *container* to
   `node:22-slim` (needs `--experimental-strip-types`; 23+ makes it default).
   That says nothing about the host. If host node ≥ 23, the flag is redundant
   but harmless; if 22.6–22.x, it is required; if < 22.6, type-stripping is
   unavailable and the suites will not run at all. **Operator must run
   `node --version` before applying.** ✗ (flagged, not assumed)

## Proposed artifact

**Path:** `.gleipnir/agents/gleipnir-code.md` — insert into the `permission.bash`
block (after the existing `bin/gleipnir-sandbox` allows, before the `git*` deny
so last-match-wins semantics grant it and the catch-all `"*": deny` still
denies everything else).

**Content (the single-combined-line shape — recommended):**
```yaml
  bash:
    "*": deny
    "bin/gleipnir-sandbox test": allow
    "bin/gleipnir-sandbox lint": allow
    "./bin/gleipnir-sandbox test": allow
    "./bin/gleipnir-sandbox lint": allow
    # seam7/seam8 (this proposal): host-run the .mjs golden-fixture suites — an
    # ALREADY-CONVERGED host-run risk class (config-scan-precommit-hook.md:166-174),
    # zero third-party deps, node: builtins only, no network. The S-2 node profile
    # is structurally unreachable via the sandbox entrypoint (__main__.py:101-108),
    # so this is the only path for this class. Single exact-match line (node --test
    # takes multiple file args, as [profile.node] itself does) — narrower than three
    # lines. NO trailing wildcard: no compound-command bypass surface.
    "node --experimental-strip-types --test tests/test_sequence_gate.mjs tests/test_git_guard.mjs tests/test_advance_hook.mjs": allow
    "git*": deny
    "gh*": deny
    "glab*": deny
    "sh*": deny
    "bash*": deny
    "env*": deny
    "curl*": deny
```

**Ready-to-apply diff (recommended shape):**
```diff
     "./bin/gleipnir-sandbox test": allow
     "./bin/gleipnir-sandbox lint": allow
+    # seam7/seam8 (this proposal): host-run the .mjs golden-fixture suites — an
+    # ALREADY-CONVERGED host-run risk class (config-scan-precommit-hook.md:166-174),
+    # zero third-party deps, node: builtins only, no network. The S-2 node profile
+    # is structurally unreachable via the sandbox entrypoint (__main__.py:101-108),
+    # so this is the only path for this class. Single exact-match line (node --test
+    # takes multiple file args, as [profile.node] itself does) — narrower than three
+    # lines. NO trailing wildcard: no compound-command bypass surface.
+    "node --experimental-strip-types --test tests/test_sequence_gate.mjs tests/test_git_guard.mjs tests/test_advance_hook.mjs": allow
     "git*": deny
     "gh*": deny
```

**Activation:** operator switches to build (or applies directly, Tier-3 is
operator-authored) and edits `.gleipnir/agents/gleipnir-code.md` per the diff.
No restart-gated wiring beyond opencode re-reading the agent file. **Before
applying, run `node --version` on the host** (fact #8) — if the exact flag/arg
string differs from what the installed node accepts, the exact-match grant will
not match the command the agent issues and the run fails closed (correct
fail-direction, but the operator should align the string to the host node).

**Enforces / bypass semantics:** exact-match, no trailing wildcard — the agent
may issue **only** this precise command string; any deviation (extra flags,
different files, a shell wrapper) does not match and is denied by `"*": deny`.
No compound-command piggyback (same idiom as the `bin/gleipnir-sandbox test`
exact-match). The agent still cannot reach `sh`/`bash`/`env`/git/credentials.
Runs on the **host** (this class is not sandboxed by design), so blast radius is
the host — mitigated by the accepted-risk-class properties (zero deps, no
network, pure/fixture tests). The operator can always run the same command
themselves.

**Honesty label:** **cooperative-policy-until-S-2.** The bash allowlist is an
opencode permission grant honoured by the runtime, not yet a structural
substrate boundary. It becomes structural when S-2 lands. Also: this grant
adds a **host-execution** capability to `gleipnir-code`, whose other build path
(`bin/gleipnir-sandbox`) is deliberately *sandboxed*. That is the material
tradeoff below.

## Decision Analysis

### Decision 1 — which agent holds the grant?

**Options:**
- **A. `gleipnir-code`** — already holds the analogous `bin/gleipnir-sandbox
  test|lint` exact-match grant, authored `test_advance_hook.mjs` this session,
  and "run the tests I just wrote" is its bound job. Cost: it gains a *host*
  execution path alongside its otherwise-sandboxed build surface (a small
  widening of an intentionally-minimal bash surface).
- **B. `git-ops`** — Haiku/mechanical. Cost: category error. Its bash allowlist
  is deliberately git-verbs-only; it holds git + (future) credentials and denies
  everything non-git. Bolting a `node` test-run onto the sole broker role mixes
  "run tests" into "hold git/credentials," widening the highest-value role's
  surface for an unrelated purpose. Rejected.
- **C. a new narrow-purpose role** (e.g. `mjs-runner`) — cleanest separation:
  host-run stays off `gleipnir-code`'s sandboxed surface entirely. Cost: a whole
  new roster entry, model assignment, stage-role-map binding, and orchestration
  edge for a 3-file test run — heavy machinery for a narrow, already-accepted
  action. Over-engineered for the current need; revisit only if host-run test
  targets multiply.

**Framework:** weighted-criteria against the framework goal (quality-efficient
outcomes per token) + least-privilege. Criteria: (1) least surprise / role
coherence, (2) surface minimality of the highest-value roles, (3) token/setup
cost, (4) least-privilege isolation of host execution.

**Recommendation: A (`gleipnir-code`).** It already owns the analogous verify
capability and authored the file; the grant is exact-match and narrow. B is a
category error (never put test-run on the credential-holding broker). C is the
theoretically-cleanest isolation but disproportionate now — note it as the
escalation path if host-run targets grow.

**Bias check (12 detectors):**
- *Status-quo / availability bias:* A is "the obvious one because it's already
  there" — checked by explicitly weighing C (clean separation). A still wins on
  proportionality, not mere convenience.
- *Anchoring:* the delegation pre-suggested `gleipnir-code`; I independently
  considered B and C and rejected B on a substantive (not anchored) ground.
- *Sunk-cost / scope-creep:* resisted inventing role C just because it is
  "more correct" — YAGNI applies; documented as the future escalation instead.
- No confirmation-bias shortcut: I verified the negative (git-ops is *wrong*),
  not just the positive.

### Decision 2 — command-line shape (one combined line vs three)

**Options:**
- **A. Single combined exact-match line** covering all three files (recommended
  content above). Narrowest: ONE grant, ONE command shape, no wildcard. Backed
  by fact #6 (repo's own `[profile.node]` runs multi-file in one `node --test`).
- **B. Three separate exact-match lines**, one per file. More granular per-file
  control, but three grants where one suffices, and it does not match how the
  suites are conventionally run together.

**Recommendation: A.** Fewer grants = smaller surface; matches the repo's
established multi-file `node --test` idiom; still exact-match with no wildcard.
The only caveat is fact #8 — the exact string (flag + file order) must match
what the **host** node accepts, so the operator aligns it after `node --version`.

**Bias check:** *false-economy* — is "one line" actually narrower, or just
fewer lines? Confirmed narrower: it is a single literal command string, so the
agent can issue exactly one command, versus three permitted commands under B.
Genuinely smaller capability, not cosmetic.

## Handoff

This is a **Tier-3 POLICY** control (`.gleipnir/agents/gleipnir-code.md` bash
grant); I cannot write it. **To apply:**
1. Run `node --version` on the host and confirm the flag/arg string matches
   (fact #8) — adjust the literal if the installed node needs a different form.
2. Switch to build (or edit directly as operator) and apply the recommended
   diff above to `.gleipnir/agents/gleipnir-code.md`.
3. Optionally delegate the *execution* afterward to `gleipnir-code` to verify
   `seam7-seam8-wiring.md` Phase 2 (the 19 `test_advance_hook.mjs` tests).

I do not implement the grant, and I did not route it into any layer I can reach.
```