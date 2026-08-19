# Decision: Config/scoping preflight (`config_scan.py`) — agent/config CONTENT validation

**Status: authored, built, WIRED on both the broker-plugin path AND the VCS
pre-commit hook; CI wiring still deferred.** The check exists, passes against
the live repo, and is available as a `gleipnir-preflight config-scan`
subcommand. It now runs automatically on **two** paths: (1) the `git-guard.ts`
opencode plugin runs it before every `gleipnir-git` broker write (agent commit
path); and (2) the active `hooks/pre-commit` VCS hook runs it ALWAYS-ON on every
commit (human or agent — the broker cannot pass `--no-verify`), fail-closed on a
REFUSE or a can't-run, mirroring the git-guard exit-contract (0 proceed / 1 block
/ 2 warn+proceed / else+can't-run block). See
`../plans/config-scan-precommit-hook.md` + `tests/test_precommit_hook.sh`
(12-case host shell test, all green). **Still deferred:** running config-scan in
CI (a push/PR-time gate independent of local hook state). Authored/built via the
pipeline; Tier-3 record authored by the operator via the build-mode escape hatch.
Plan of record: `../plans/config-scoping-preflight.md` (twice spec-reviewed + a
design-coherence pass; full ATLAS with the Design Consolidation contract).

## Why

The existing S-2/G-1 boundary preflight (`boundary.py`) verifies OS write/read
*permissions* on the enforcement path set — but never reads config *content*. So
it would happily pass a file whose YAML is valid-but-semantically-wrong: a
`permission.tools: true` (invalid grammar), a global-disable that silently hides
MCP tools from a subagent, or a missing per-agent deny that leaks a broker
namespace. Every one of those was a real, restart-only-observable bug this
session (lessons L-C12 / L-C12b) that cost ~4 restart cycles to find. This
preflight catches that whole class of "authored, looks right, breaks (or
mis-scopes) at restart" defects *before* the operator restarts.

## What was decided (operator-converged + planner Design Consolidation)

- **Parser = Option A (converged):** a stdlib-only minimal frontmatter reader
  that fails closed on anything outside a narrow accepted subset (exactly the
  constructs the live agent files use). Rejected: (B) PyYAML as broker-tier
  tooling, (C) piggyback the broker's transitive `pydantic`/`pyyaml` — both
  would move the check out of the stdlib-pure enforcement core
  (`runtime-and-deps.md`). Note: naive `mcp>=1.0.0`-style assumptions don't
  apply here; there is no YAML in the stdlib, which is *why* Option A hand-rolls
  the narrow subset.
- **What it checks:** (1) grammar — `permission.*` values must be
  allow/deny/ask strings, top-level `tools`/`agent.*.tools` values must be
  booleans, and a present-but-non-dict `permission`/`tools` is itself a FAIL;
  (2) effective per-agent MCP tool-grant enumeration + single-holder assertion
  (only git-ops holds `gleipnir-git_*`, only project-mgr holds `gleipnir-pm_*`,
  all others deny both); (3) well-formedness (fail-closed on unparseable);
  (4) generalised fail-open detection over ANY declared MCP server (not
  hardcoded to git/pm) + reintroduced-global-disable + mis-scoped-glob (WARN).
- **Design Consolidation decisions (planner, from the assembled test contract):**
  (1) the two FAIL_OPEN emitters stay distinct, disambiguated by `where`-shape
  (`"{agent}: {namespace}"` for a single-holder leak vs bare `"{namespace}"` for
  a generalised zero-denier); (2) the four MCP-reasoning functions stay separate
  (different input shapes — raw tools maps vs the reduced effective set);
  (3) `config_scan_main`'s 10-step orchestration made authoritative;
  (4) one module, `config_scan.py`; (5) `decide_config` arg order
  `(unparseables, findings, agent_count, ...)` — the TESTS are authoritative
  (an earlier prose draft had it backwards; corrected).
- **Shape:** mirrors `boundary.py` — pure core + thin file-read edge,
  discriminated outcome types, fail-closed on ambiguity, one deliberate broad
  `except` mapped only to a fail outcome (INVALID_JSONC), no `os.access`
  shortcuts, strictly read-only. Wired as a subcommand on the EXISTING
  `gleipnir-preflight` CLI (leading-token dispatch; zero behaviour change to the
  boundary check when no `config-scan` token is given).

## Verification

- Test-first: 6 files, 143 tests specifying the full public API (types + 13
  functions), built incrementally in 6 parts.
- Two real defects caught DURING build (not assumed away): (a) a cross-file
  inconsistency — a mis-scoped glob wasn't filtered out of the effective-tools
  set, contradicting Design Consolidation Decision 2 — fixed; (b) a
  quality-review finding — a malformed-but-grammar-legal non-dict `tools:`/
  `permission:` value crashed uncaught instead of a discriminated Finding —
  fixed at the primary checkpoint (`check_grammar`) AND via defense-in-depth
  guards, with 15 regression tests, and independently traced by quality review
  to introduce no false-CLOSED path.
- Final: 143 config-scan tests, 90% line+branch coverage on `config_scan.py`,
  619 passed / 11 skipped across the full suite, zero regressions,
  quality-APPROVED. Live-repo regression guard (ST-4) confirms the current repo
  passes CLOSED.
- Committed + pushed: `0b3b0f7` (plan + tests), `c3c93ea` (implementation).

## Honesty labels / open items

- **Enforced automatically on commit + broker write; CI still deferred.** The
  check now runs (a) via `git-guard.ts` before every `gleipnir-git` broker write,
  and (b) via the ALWAYS-ON `hooks/pre-commit` VCS hook on every commit
  (fail-closed; operator-converged, plan `../plans/config-scan-precommit-hook.md`,
  hardened-reviewed GO). The remaining deferred piece is a **CI** gate (push/PR
  time, independent of local hook state) — its own future convergence. Before
  this wiring the check caught the bug class only if someone ran it manually;
  that gap is now closed for the commit + broker paths.
- **Durable design notes from the pre-commit wiring** (the Tier-0 plan is
  disposable; these decisions are kept here so they survive it):
  - **Fail-closed on can't-run, not just on REFUSE (operator-converged).** If
    config-scan cannot execute at all (missing/non-executable CLI, absent venv,
    infra error) the hook REFUSES the commit — it does not fail-open with a
    warning. Matches config-scan's own fail-closed design and the framework
    posture; a human may `git commit --no-verify`, but the `gleipnir-git` broker
    cannot pass `--no-verify`, so agents cannot bypass it.
  - **Exit-contract single-sourced with `git-guard.ts`.** The hook mirrors the
    plugin's mapping exactly (0 proceed / 1 block / 2 warn+proceed / any other
    code or can't-run → fail-closed block), so the broker-write path and the
    VCS-commit path agree. Mapping duplicated across the TS plugin and the POSIX
    hook is accepted (two runtimes, cannot share code); a review-time drift check
    guards it rather than a shared module.
  - **Host shell tests execute OUTSIDE the roster grant (reusable insight).**
    Spec-review caught that the plan initially mis-routed test *execution*
    (`sh tests/test_precommit_hook.sh`) to `gleipnir-code`, whose bash grant
    denies `sh*`/`bash*`/`*` (only `bin/gleipnir-sandbox test|lint` exact-match).
    No roster subagent can run a raw host shell test; the executor is the
    operator or a build session holding `bash`. The `test_git_guard.mjs` /
    `test_sequence_gate.mjs` "host-run" precedent is a *where-it-runs* precedent,
    not an *executed-by-the-agent* one — that grant was tightened when the sandbox
    landed. Any future host-shell test must name a real executor, not assume a
    roster agent can run it. (See also L-C29 for the secret-fixture-at-runtime
    rule the same test surfaced.)
- **Residual fast-follow (non-blocking):** `config_scan_main`'s
  `jsonc_agent_overrides` comprehension assumes each `opencode.jsonc` `agent`
  block is a dict; a malformed agent entry (e.g. `"agent": {"foo": true}`) could
  raise there — a different call site than the one already hardened. Logged for
  a future pass.
- **Precedent, not yet ratified:** how prose/config-only plans (no source code)
  map onto the fixed G-5 pipeline stages was flagged during the escalation-
  process plan as something `stage-role-map.md` should eventually ratify as a
  standing rule, rather than each plan re-deciding it.
- **Accepted-subset scope:** the parser deliberately covers only the constructs
  the live agent files use; a legal-but-unused YAML construct (or a blanket
  `tools: {"*": false}`) is out of scope and fails closed / is not
  namespace-checked — consistent with the "scoped to what the files contain"
  philosophy, not a general YAML validator.
