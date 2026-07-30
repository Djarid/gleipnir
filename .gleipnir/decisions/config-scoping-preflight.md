# Decision: Config/scoping preflight (`config_scan.py`) — agent/config CONTENT validation

**Status: authored, built, in use; NOT YET WIRED to run automatically.** The
check exists and passes against the live repo, and is available as a
`gleipnir-preflight config-scan` subcommand, but nothing yet runs it on a git
hook or in CI (deferred — see open items). Authored/built via the pipeline;
Tier-3 record authored by the operator via the build-mode escape hatch. Plan of
record: `../plans/config-scoping-preflight.md` (twice spec-reviewed + a
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

- **Not yet enforced automatically.** The check runs only when explicitly
  invoked (`gleipnir-preflight config-scan`). Wiring it into a git pre-commit
  hook and/or CI is a deferred follow-on that needs its own convergence — until
  then it catches the bug class only if someone runs it.
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
