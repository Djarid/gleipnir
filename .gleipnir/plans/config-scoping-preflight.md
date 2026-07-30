# Plan: config/scoping preflight (agent/config CONTENT validation)

**Stage:** plan (ATLAS Architect/Trace/Link/Assemble/Stress-test + Execution
Workflow). Authored by `gleipnir-plan` FROM an already-converged operator
decision (see "Converged decision" below). Tier-0 artifact under
`.gleipnir/plans/`; disposable after the associated slice merges.

---

## GOTCHA pre-flight (output visibly, per method)

```
PRE-FLIGHT  (plan stage; * = conditional)

[x] Plan file exists on disk (goals/plan-format.md structure)?
    -> THIS file, .gleipnir/plans/config-scoping-preflight.md. Writing it IS planning.

[x] Checked goals/manifest.md for a relevant goal?
    -> plan-format.md (artifact/format) + methodology.md (ATLAS/GOTCHA-ahead-of-planning)
       both apply and are followed. No sequencing goal exists or should (G-5 rule).

[x] Read the full goal before starting?
    -> plan-format.md read; every required section present below.

[n/a] Platform lifecycle / editable-install / consistency-check gates
    -> This is planning, not an implementation block. No code is written by this role.
       Issue/lifecycle creation, if wanted, is the orchestrator's call at plan time.

GAPS NAMED:
  - No YAML parser in the stdlib (confirmed: no `import yaml` anywhere in src/;
    sandbox/profiles.py uses stdlib `tomllib` for TOML, there is no equivalent
    for YAML). This gap is EXACTLY what the converged decision (Option A) resolves.
  - The corpus this checker validates (agent frontmatter) is Tier-3 POLICY;
    this checker READS it out-of-framework, never writes it. No tier violation.
```

Correct order is plan-before-code. This plan is the artifact; the implementing
agent (`gleipnir-code`, Sonnet, test-first) acts from it without re-deriving.

---

## Decisions (index)

Summary of every decision this plan fixes, in order encountered; full reasoning
for each is in the sections below (row 0 → "Converged decision"; rows 1–5 →
Trace "Design Consolidation").

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 0 | Parser approach | Option A — stdlib minimal frontmatter reader, fail-closed on out-of-subset | B (PyYAML as broker-tier tooling), C (piggyback broker's pydantic/pyyaml) | Keeps the check inside the stdlib-pure enforcement core; converged directly with operator via `question`, not a formal brainstorm cycle |
| 1 | Fail-open detection: one function or two? | Two separate paths — assert_single_holders (designated git/pm namespaces) + check_fail_open (generic, any server) | Consolidating into one parametrized detector | Different questions, different populations; disambiguated by where-shape ("{agent}: {namespace}" vs "{namespace}") |
| 2 | Collapse the 4 MCP-reasoning functions? | No — stay separate | Merging into one enumerate-consuming mega-function | Each consumes a different data shape; find_mis_scoped_denies needs the raw tools map, not the reduced effective set |
| 3 | config_scan_main orchestration order | 10-step sequence (documented explicitly in the plan) | — | No test file specified it end-to-end; now made authoritative |
| 4 | Module layout | One file, config_scan.py | Splitting JSONC logic into a sibling module | All 6 test files import through one module; splitting = import churn, no benefit |
| 5 | decide_config arg order | (unparseables, findings, agent_count) — tests are authoritative | Plan's own earlier prose had it backwards | Real bug caught by the design-coherence pass; prose corrected to match code |

---

## Converged decision (FIXED — do NOT re-decide)

**Parser approach = Option A: a stdlib-only minimal frontmatter reader that
fails closed on anything outside a narrow accepted subset.**

- **Source of this decision:** obtained directly between the orchestrator and
  the operator via `question` THIS session (not self-attested, not derived by
  this planner). This plan inherits it as a fixed constraint and plans FROM it.
- **Rejected alternatives (recorded, do not revisit):**
  - **(B)** treat the preflight as broker-tier tooling and allow PyYAML —
    *rejected*: keeps the check in the stdlib-pure enforcement core instead
    (`.gleipnir/decisions/runtime-and-deps.md`).
  - **(C)** piggyback the broker's transitive `pydantic`/`pyyaml` deps —
    *rejected*: avoids coupling the preflight to the broker's dependency tree.
- **Why this is not re-opened here:** the one known material tradeoff (parser
  approach) is already converged. This planner surfaces NO new material
  tradeoff (see the "New material tradeoffs" report at the end — none). Every
  remaining choice below is a bounded Link-time/mechanical detail, resolved
  in-plan as the plan-format allows, not a re-opened material decision.

---

## A — Architect

**Problem (one sentence).** Extend the out-of-framework preflight so it
validates agent/config CONTENT — YAML/JSONC well-formedness, permission-value
grammar, and effective per-agent MCP tool-grant sets — catching the three
restart-only config bugs found this session (L-C12 / L-C12b) BEFORE the
operator has to restart to discover them, rather than only checking OS
write/read permissions as the existing boundary preflight does.

**User.** The **operator**, running the check out-of-framework (as the owning
uid, before/around launching an opencode session) — the same audience and
posture as `bin/gleipnir-preflight` today. NOT an in-framework agent; this
checker is deliberately not referenced by any `.gleipnir/agents/*.md`
permission map, exactly as `preflight/__main__.py` is not (a guard validated
by the population it guards is the G-3 forgeable-evidence failure).

**Measurable success.** Given the current, known-good repo state the checker
exits CLOSED-equivalent (0). Given a fixture reproducing each of the three real
bugs, it exits REFUSE-equivalent (nonzero) with a key-path-precise reason. Given
any frontmatter block it cannot parse under the accepted subset, it FAILS
CLOSED (flags unparseable, exit nonzero) — never silently skips, never guesses.
Concretely: all four Architect check-classes below pass their Stress-test
fixtures, and branch coverage on the pure core is reported (per L-C2, branch is
the honest arbiter for a fail-closed codebase).

**The four checks this plan defines precisely (success criteria).**

1. **Grammar validation.** Every `permission.*` value (whether the direct
   scalar value of `edit:`/`read:`/`bash:`/`write:`/`task:`/`webfetch:`/
   `question:`, or a value inside a nested glob-keyed map under one of those)
   is one of the strings `allow`/`deny`/`ask` — NEVER a boolean. Conversely,
   every top-level agent `tools:` value, and every `opencode.jsonc`
   `tools`/`mcp.*.enabled` boolean-typed field, is an actual boolean — never
   an `allow`/`deny`/`ask` string. Any violation is flagged with key-path
   detail (frontmatter has no post-parse line numbers, so report by key path,
   e.g. `git-ops.md: permission.tools."gleipnir-git*" = true (boolean under
   permission; expected allow/deny/ask)` — this is exactly the L-C12 bug).

2. **Effective MCP tool-set enumeration + single-holder assertion.** For each
   MCP server declared in `opencode.jsonc`'s `mcp` block, compute — for EVERY
   agent file — whether that agent denies the server's namespace (`<server>_*`,
   boolean `false`) or not (absence = enabled, per the now-confirmed working
   model, L-C12b). The effective per-agent deny-set is the **UNION** of two
   valid deny locations (L-C12b): **(a)** the agent's own frontmatter top-level
   `tools:` block, AND **(b)** any `opencode.jsonc`-level `agent.<name>.tools`
   override for that same agent name — a deny in EITHER location denies the
   namespace for that agent (matching the merge already specified in Trace,
   Assemble step 3, and ST-13). Then assert, for a designated single-holder
   namespace (`gleipnir-git` held by `git-ops`; `gleipnir-pm` held by
   `project-mgr`): exactly one agent does NOT deny it, and every other agent
   DOES. Flag:
   - **(a)** a namespace nobody holds explicitly AND multiple agents leave
     un-denied (fail-open leak — the quality-reviewer/session-scribe near-miss);
   - **(b)** a namespace no agent can see at all (possible over-restriction —
     a warning, distinct from a fail-open leak);
   - **(c)** more than one holder of a namespace meant to be single-held.

3. **Well-formedness.** Every `.gleipnir/agents/*.md` frontmatter block parses
   under the Option-A reader OR is explicitly flagged unparseable (fail closed,
   never silently skipped); `opencode.jsonc` parses as valid JSONC.

4. **Generalised fail-open detector.** ANY globally-enabled tool/MCP namespace
   with ZERO agents denying it is flagged — even if it is not one of the two
   known broker namespaces. This must generalise to future MCP servers added to
   `opencode.jsonc`'s `mcp` block (check 2 is the two named cases; check 4 is
   the general rule that subsumes them for any server).

**Constraints.**
- **Stdlib-only** (the enforcement core; `runtime-and-deps.md`). Confirmed:
  Python stdlib has `json`/`tomllib` but no YAML — Option A supplies the narrow
  reader by hand. JSONC is JSON-with-comments; `opencode.jsonc` uses only
  `//` line comments and no trailing commas in the sampled file, so a
  comment-stripping pre-pass + stdlib `json.loads` suffices (see Trace edge
  cases for the fail-closed handling if a construct outside that is hit).
- **Fail-closed is the only default**, mirroring `boundary.py`: every
  ambiguous / missing / erroring / out-of-subset condition maps to a
  discriminated failure outcome and a nonzero exit — never "assume fine". The
  precise invariant on broad excepts (mirroring `boundary.py:654-659`): catch
  *specific* exceptions where the failure mode is known (e.g. `json.JSONDecodeError`,
  `OSError`), and where an outer boundary needs a catch-all, exactly one
  deliberate broad `except Exception` is acceptable **iff it can only ever map
  to a fail outcome, never to a pass** — the `boundary.py:658` pattern
  (`except Exception as exc: # fail-closed: any surprise is an error, never CLOSED`).
  A broad except that could yield "clean" is the defect; a broad except that
  can only yield a discriminated FAIL is the correct fail-closed catch-all.
- **Pure core + thin edge**, mirroring `boundary.py`'s structure (see Trace).
- **Accepted-YAML-subset is scoped to what the 9 live agent files actually
  contain** — NOT a general YAML spec. Anything outside the subset is a
  fail-closed "unparseable", not an attempt to parse more.
- **This slice does not change any Tier-3 content.** It only reads and reports.
  Whether it later becomes a git pre-commit hook / CI check is a NOTED
  follow-on, explicitly OUT of this slice's scope (see Assemble / follow-ons).

**Explicitly NOT in scope (Part-0 discipline).**
- Not restricting or enumerating the operator's built-in `/plan`, `/build`,
  `/general` escape-hatch agents — same escape-hatch discipline as `boundary.py`.
- Not writing/repairing any config — this is a read-and-report checker.
- Not turning the check into a hook/CI gate in this slice (follow-on only).
- Not validating the full opencode config schema — only the four checks above
  (a targeted content check for the observed bug classes, not a schema linter).

---

## T — Trace

### Where the artifact lives (source of truth)

New module `src/gleipnir/preflight/config_scan.py` (pure core + thin file-read
edge), sibling to the existing `boundary.py` in the same package. The CLI
surface is a **subcommand/flag on the existing `preflight/__main__.py`** rather
than a second binary — see the Link-time decision below (a mechanical
consistency choice, not a material tradeoff).

The **source of truth this checker reads** (never writes):
- `.gleipnir/agents/*.md` — the 9 agent files (frontmatter is the subject).
- `opencode.jsonc` (repo root) — the `mcp` block (server declarations); the
  absence of a top-level `tools` disable; AND an optional `agent.<name>.tools`
  block. **The per-agent MCP visibility override has TWO valid locations
  (L-C12b): the top-level `tools:` key in an agent's OWN frontmatter, AND an
  `opencode.jsonc`-level `agent.<name>.tools` block.** Today `opencode.jsonc`
  has no `agent` key, so the second location is empty — but the checker MUST
  read it and merge it into the effective-tool-set computation (Link-time
  decision (a), chosen over silently ignoring it: an unread override location
  is a latent false result for a security tool — see check 2 below and the
  edge-case entry). Both locations are boolean-valued (`<server>_*: false` =
  deny), never `allow/deny/ask` strings.
- The **designated single-holder map** — `{gleipnir-git: git-ops, gleipnir-pm:
  project-mgr}` — is data IN this checker's code, mirroring how `boundary.py`
  hard-codes `ENFORCEMENT_PATHS` as a named tuple ("caught by review, not
  silently trusted"). A future MCP server added to `opencode.jsonc` with no
  entry here still gets check-4's generalised fail-open sweep; promoting it to
  a *single-holder* assertion (check 2) requires a reviewed edit to this map.

### Pure-core / thin-edge split (mirrors boundary.py's discipline; extends the severity taxonomy)

This module **mirrors `boundary.py`'s discriminated-outcome discipline and
fail-closed contract**, and **deliberately extends its severity taxonomy** where
the check classes genuinely differ: `boundary.decide` is strictly binary
(CLOSED / not), because every enforcement-path probe is a pass-or-fail with no
middle risk class. This checker adds a `WARN` tier (over-restriction and
mis-scoped-glob checks) because those are a DIFFERENT risk class from a
fail-open leak — an over-restriction is a possible operator inconvenience, not
a security hole, so it is reported without forcing REFUSE (unless `--strict`).
This is a considered extension, NOT accidental drift from the exemplar; a later
quality reviewer should read the WARN tier as intentional.

`boundary.py` is: pure core (`ENFORCEMENT_PATHS`, `Posture`, `ProbeOutcome`,
`classify_probe_result`, `verdict_for_path`, `decide`, all pure/data-driven and
fully unit-testable at root) + thin OS edge (`probe_write_as_agent` etc., the
only place real I/O happens, injectable). The new module mirrors this:

- **Pure core (no I/O; fully unit-testable by feeding in text/parsed data):**
  - **Frontmatter split** — `extract_frontmatter(text) -> str | Unparseable`:
    isolate the `---`-delimited YAML block at the top of an agent `.md`. A
    missing/second/unterminated `---` fence is a discriminated `Unparseable`
    outcome, never a guess.
  - **Minimal YAML reader (Option A)** — `parse_frontmatter(block) ->
    dict | Unparseable`: hand-rolled reader for EXACTLY the accepted subset
    (grammar below). Every construct outside the subset -> `Unparseable`
    (fail closed).
  - **JSONC reader** — `parse_jsonc(text) -> dict | Unparseable`: strip `//`
    line comments (respecting `//` inside string literals), then stdlib
    `json.loads`. Any residual `JSONDecodeError`, or any comment/whitespace
    construct the stripper does not handle, -> `Unparseable` (fail closed).
  - **Value-type discriminators** — pure predicates: `is_permission_value_ok`
    (string in `{allow,deny,ask}`), `is_tools_value_ok` (bool), applied by
    walking the parsed structure.
  - **Grammar validator** — `check_grammar(parsed_agent) -> tuple[Finding,...]`
    (check 1).
  - **MCP enumeration + single-holder** — `enumerate_effective_tools(agents,
    mcp_servers, holder_map, jsonc_agent_overrides) -> ToolScopeReport`;
    `assert_single_holders(...) -> tuple[Finding,...]` (checks 2a/2b/2c). The
    effective per-agent deny-set is the UNION of the agent's own frontmatter
    top-level `tools:` denies AND any `opencode.jsonc` `agent.<name>.tools`
    denies for that same agent name (both locations are valid per L-C12b; a
    deny in EITHER location denies the namespace for that agent). This merge is
    pure — `jsonc_agent_overrides` is a plain dict passed in, so it is fully
    unit-testable without a real `opencode.jsonc`.
  - **Generalised fail-open sweep** — `check_fail_open(mcp_servers, effective,
    holder_map) -> list[Finding]` (check 4); plus `check_global_disable(
    jsonc_top_level_tools) -> list[Finding]` (JSONC-side, ST-2) and
    `find_mis_scoped_denies(agents, mcp_servers, jsonc_agent_overrides=None) ->
    list[Finding]` (ST-8). **See Design Consolidation Decision 2 for why these
    stay separate pure functions, and Decision 1 for the dual `FAIL_OPEN`
    `where`-shape convention** (`check_fail_open` keys on the namespace glob
    only; `assert_single_holders`' `FAIL_OPEN` keys on `"{agent}: {namespace}"`).
  - **Aggregate decision** — `decide_config(unparseables, findings, agent_count,
    *, strict=False, override_ack=False) -> ConfigDecision`: fail-closed
    AND-of-all-clean, mirroring `boundary.decide` (any Finding of severity FAIL,
    any Unparseable, or `agent_count == 0` => REFUSE-equivalent; nothing
    clean-but-empty is ever "passed"). **NOTE the argument order — `unparseables`
    FIRST, then `findings`, then keyword `agent_count=` — is the as-built test
    contract (decide.py/cli.py), authoritative over any earlier prose.**
- **Thin edge (the only I/O; injectable exactly as boundary's probes are):**
  - `read_agent_files(agents_dir) -> dict[str, str | Unparseable]` and
    `read_jsonc(path) -> str | Unparseable` (an `OSError` maps to
    `Unparseable(READ_ERROR, ...)`, never propagates — see below). Production
    defaults read the real files; tests inject fixture text so the entire
    decision core is exercised without any real filesystem layout (the same
    pattern `collect_path_probes` uses with its injectable `write_probe`/
    `read_probe`). The composition entrypoint is `config_scan_main(argv=None,
    config_root=None) -> int` (Design Consolidation Decision 3).
  - **I/O error handling (mandatory, mirroring `boundary.py:687-697`).** The
    real read of an agent file or `opencode.jsonc` can raise `OSError`
    (permission denied, file vanished mid-glob — an agent file removed between
    the directory glob and the read — or a broken symlink). Every such read is
    wrapped: an `OSError` is caught at the edge and mapped to an
    `Unparseable(kind=READ_ERROR, where=<path>, detail=str(exc))` — exactly as
    `_fork_drop_verify_attempt` wraps `os.pipe`/`os.fork` `OSError` into
    `ProbeOutcome.PROBE_ERROR` rather than letting it propagate. Per the plan's
    own fail-closed constraint, a read failure must map to a discriminated fail
    outcome (forcing REFUSE via `decide_config`), NEVER propagate uncaught out
    of the tool and NEVER be silently skipped (a skipped-because-unreadable
    agent file is precisely a fail-open-by-omission — the same hazard
    `boundary.py`'s walk-error handling closes).

### Discriminated outcome types (fail-closed catch-all only — boundary.py discipline)

Mirror `ProbeOutcome`/`ProbeResult`/`Verdict`:

- `Unparseable(kind, where, detail)` — `kind` an enum: `NO_FRONTMATTER`,
  `UNTERMINATED_FENCE`, `OUT_OF_SUBSET_YAML`, `INVALID_JSONC`, `READ_ERROR`.
  `where` is the file + key-path (or fence location). This is the fail-closed
  "I refuse to guess" signal. `READ_ERROR` is the thin-edge I/O failure case
  (see below) — a file that could not be read is treated exactly like a file
  that could not be parsed: a discriminated fail, never a silent skip.
- `Finding(check, severity, where, detail="")` — `check` enum: `GRAMMAR`,
  `SINGLE_HOLDER`, `FAIL_OPEN`, `OVER_RESTRICTION`, `GLOBAL_DISABLE`,
  `MIS_SCOPED_GLOB` (the last two added by the check-4/JSONC and mis-scoped-glob
  test files). `severity` enum: `FAIL` (forces nonzero) / `WARN` (reported, does
  not by itself force nonzero — over-restriction and mis-scoped-glob are WARN,
  not leaks). `where` is a key-path (or `"{agent}: {namespace}"` for a named
  leak — Design Consolidation Decision 1).
- `ConfigDecision(verdict, label, reasons=())` — named `ConfigVerdict` (NOT
  `Verdict`) with a distinct `DEV_MODE_LABEL_CONFIG` to avoid an import collision
  with `boundary`'s `Verdict`/`DEV_MODE_LABEL`; `verdict` reuses the SAME
  three-value convention (`CLOSED` / `PROCEED_UNCLOSED` / `REFUSE`) so the CLI
  exit-code mapping is shared and consistent (0/2/1). A `--override-ack` escape
  (present, mirroring `boundary`) can only escalate a non-clean result to
  PROCEED_UNCLOSED, never
  produce CLOSED — same invariant as `boundary.decide`.

### The accepted-YAML-subset grammar (Option A) — scoped to the 9 live files

This is the exact set of constructs the 9 agent files contain (inventoried from
`git-ops.md`, `orchestrator.md`, `quality-reviewer.md`, `gleipnir-plan.md`,
`gleipnir-code.md`, `gleipnir-brainstorm.md`, `project-mgr.md`, `notify.md`,
`session-scribe.md`). The reader accepts ONLY these; anything else ->
`OUT_OF_SUBSET_YAML` (fail closed).

1. **Document fence:** the frontmatter is the text between a leading `---` line
   and the next `---` line. Exactly one such block at file start.
2. **Comments (at ANY indent, including interleaved between map children):** a
   line whose first non-space char is `#` is a comment; ignored — regardless of
   its indentation. This explicitly INCLUDES **interleaved comments**: comment
   lines indented to match a nested map's child indent, sitting BETWEEN sibling
   `key: value` children inside that map. This construct is real and common in
   the live files — e.g. `git-ops.md:23-30` (comment lines between children of
   `permission:` — they precede the `bash:` key, sitting between the `read:`
   and `bash:` siblings) and `gleipnir-brainstorm.md:16-19` (comment lines
   indented at child depth between `webfetch:` and `question:` inside
   `permission:`). It is DISTINCT from the indent-0 comments this rule also
   covers, and must not be confused with the flat/nested-map key rules (3/5).
   **Mechanism (mandatory):** comment lines (and blank lines) are removed in a
   **pre-pass, BEFORE any indent-based structural walking**. If the structural
   walker saw an interleaved comment line it would try to read `# ...` as a
   malformed key and wrongly emit `OUT_OF_SUBSET_YAML` on a genuinely valid
   file (a false-positive fail-closed flag — a false REFUSE on good config).
   Stripping first makes the interleaved comment invisible to the walker, so
   the surviving children parse as ordinary siblings. Inline `#` AFTER a value
   on the same line is NOT stripped (none of the 9 files rely on a trailing
   inline comment that changes a value's meaning; verify in the well-formedness
   fixture; treat conservatively if one ever appears). Blank lines ignored.
3. **Flat scalar keys** at indent 0: `key: value` where value is:
   - an unquoted bareword (`subagent`, `primary`, `allow`, `deny`, `ask`,
     `true`, `false`, `deny`), an integer (`steps: 30`), a float
     (`temperature: 0.2`), or a double-quoted string (`color: "#7ed321"`).
   - `true`/`false` are parsed as booleans; integer/float literals as numbers;
     `allow`/`deny`/`ask` and other barewords as strings. (This typed
     distinction is what checks 1 depends on.)
4. **Block scalar** `description: >-` (folded) followed by more-indented
   continuation lines — captured as an opaque string; its content is never
   grammar-checked (it is prose).
5. **Nested map** — a key at indent 0 with no inline value (`permission:`,
   `tools:`), followed by indented `key: value` children. Children keys may be:
   - unquoted barewords (`edit:`, `read:`, `bash:`, `write:`, `task:`,
     `webfetch:`, `question:`, `gleipnir-brainstorm:`), OR
   - double-quoted strings, INCLUDING glob patterns (`"*"`, `".git/**"`,
     `"git status*"`, `".gleipnir/plans/**"`, `"gleipnir-pm_*"`).
   - A child value is itself either a scalar (per #3) OR a further-indented
     nested map (e.g. `permission:` -> `bash:` -> `"*": deny`). **Nesting is
     capped at depth 2** (top-level key -> child map -> grandchild scalar, i.e.
     `permission.bash."*"`) — the maximum the 9 live files actually contain. A
     THIRD level of map nesting is OUT of subset and fails closed
     (`OUT_OF_SUBSET_YAML`). This keeps the "scoped to what the files contain,
     not a general YAML spec" claim precise and honest: a stricter reader is
     the safer choice for a security-boundary tool — it can never silently
     accept a deeper structure it was never validated against, and a future
     file that genuinely needs depth 3 fails LOUDLY (prompting a reviewed
     grammar extension) rather than being parsed on a guess.
6. **List block** — a key at indent 0 (`compaction_survival:`) followed by
   indented `- "..."` items (double-quoted string items). Captured as a list of
   strings. `\n` inside those strings stays literal (the extractor plugin
   un-escapes them at runtime; the checker does not need to).

Explicitly OUT of subset (=> fail closed if ever seen): YAML anchors/aliases
(`&`/`*` refs), flow mappings/sequences (`{a: b}` / `[a, b]`), multi-document
streams, tags (`!!str`), single-quoted-with-escapes edge cases, block literals
`|`, and any tab-indentation. None appear in the 9 files.

### Integrations map

| Reads | Purpose | Format | Notes |
|---|---|---|---|
| `.gleipnir/agents/*.md` | subject of checks 1-4 | YAML frontmatter (Option-A subset) | 9 files today; glob the dir, do not hardcode the 9 names — a new agent file must be picked up |
| `opencode.jsonc` | `mcp` servers (check 2/4); absence of top-level `tools` disable; optional `agent.<name>.tools` per-agent override (merged into check 2) | JSONC | comment-strip + json.loads; `agent` key absent today but read-and-merged so a future addition is not a latent false result |
| single-holder map (in-code data) | check 2 assertion targets | Python tuple/dict | reviewed edit to extend, per boundary.py's named-set discipline |

No network, no DB, no credentials, no writes. The only external dependency is
the local filesystem, read-only, as the owning uid.

### Edge cases (documented, all fail-closed)

- **No frontmatter / unterminated fence** in an agent file -> `Unparseable`
  (NO_FRONTMATTER / UNTERMINATED_FENCE), REFUSE. Never treated as "no rules =>
  fine".
- **A new agent file** appears with no `tools:` deny for a broker namespace ->
  check 2/4 flags it as a fail-open leak (this is the quality-reviewer/
  session-scribe near-miss generalised).
- **An `opencode.jsonc` `agent.<name>.tools` override exists** (the SECOND
  valid deny location, L-C12b) -> merged into that agent's effective deny-set
  in check 2, so a namespace denied ONLY at the opencode.jsonc level (and not
  in the agent's own frontmatter) is correctly counted as denied — and,
  conversely, a holder that is denied there is correctly flagged. Today this
  block is absent; the checker reads it as empty and the merge is a no-op, but
  the code path exists so a future `agent` key is never a latent false result.
- **A boolean under `permission.*`** (L-C12) -> GRAMMAR FAIL, key-path detail.
- **An `allow`/`deny`/`ask` string under top-level `tools:`** -> GRAMMAR FAIL.
- **The now-removed global-disable pattern** (`tools: {ns: false}` at the
  opencode.jsonc top level) — NOT PRESENT in the current config (bug 2 is fixed
  by removal). The checker must STILL flag it if reintroduced: if
  `opencode.jsonc` grows a top-level `tools` key that disables an MCP namespace
  globally, that is the known-broken pattern (globally-disabled MCP tools are
  invisible to subagents regardless of per-agent re-allow) -> FAIL. This is a
  check on the JSONC side, complementing the per-agent checks.
- **A namespace glob written as `gleipnir-git*` instead of `gleipnir-git_*`**
  (missing underscore, L-C12b(b)) — the MCP tool names are `<server>_<tool>`,
  so a deny glob without the underscore may not match; flag a suspected
  mis-scoped deny glob (WARN) so it is not silently a fail-open.
- **JSONC with a construct the stripper does not handle** (block comments,
  trailing commas) -> `INVALID_JSONC` fail-closed, not a lenient parse.
- **Thin-edge read failure** — an agent file or `opencode.jsonc` read raises
  `OSError` (permission denied, vanished mid-glob, broken symlink) -> caught at
  the edge and mapped to `Unparseable(READ_ERROR)`, forcing REFUSE. Never
  propagates uncaught; never silently skipped (a skipped-because-unreadable
  file is a fail-open-by-omission). Mirrors `boundary.py:687-697`.
- **Empty agent set** (glob matched nothing) -> REFUSE (no evidence is not
  evidence of a clean config), mirroring `decide`'s empty-`path_probes` rule.
- **A `WARN`-only run** (e.g. only an over-restriction) -> exits CLOSED-
  equivalent by default UNLESS a `--strict` flag promotes warnings to failures
  (Link-time flag decision, not material).

---

### Design Consolidation (added post-test-authoring — the assembled-whole review)

**Context.** The six test files (`test_config_scan_{parse,grammar,mcp_enum,
failopen,decide,cli}.py`) were authored across six independent delegations and
together *specify the complete public API* of the not-yet-built
`config_scan.py`. This subsection reconciles that assembled whole into ONE
deliberate contract — the design decisions no single file-at-a-time author was
positioned to make. It is an Architect-judgment consolidation, NOT a re-opening
of the converged Option-A parser decision or the three real-bug Stress-tests
(ST-1/2/3), which stay fixed. Where a decision here contradicts a test's
assumption, it is named explicitly at the end (none do — the suite is
coherent).

**The consolidated public API (authoritative — implement exactly this).**

Types (all frozen dataclasses / `Enum`, `boundary.py`-style):
`UnparseableKind` (`NO_FRONTMATTER`, `UNTERMINATED_FENCE`, `OUT_OF_SUBSET_YAML`,
`INVALID_JSONC`, `READ_ERROR`); `Unparseable(kind, where, detail="")`;
`FindingCheck` (`GRAMMAR`, `SINGLE_HOLDER`, `FAIL_OPEN`, `OVER_RESTRICTION`,
`GLOBAL_DISABLE`, `MIS_SCOPED_GLOB`); `FindingSeverity` (`FAIL`, `WARN`);
`Finding(check, severity, where, detail="")`; `ConfigVerdict` (`CLOSED`,
`PROCEED_UNCLOSED`, `REFUSE`); `ConfigDecision(verdict, label, reasons=())`;
module constant `DEV_MODE_LABEL_CONFIG`.

Pure core: `extract_frontmatter(text) -> str | Unparseable`;
`parse_frontmatter(block) -> dict | Unparseable`;
`parse_jsonc(text) -> dict | Unparseable`;
`check_grammar(parsed) -> list[Finding]`;
`enumerate_effective_tools(agents, jsonc_agent_overrides=None) -> dict[str, set[str]]`;
`assert_single_holders(effective, mcp_namespaces, holder_map) -> list[Finding]`;
`check_fail_open(mcp_servers, effective, holder_map) -> list[Finding]`;
`check_global_disable(jsonc_top_level_tools) -> list[Finding]`;
`find_mis_scoped_denies(agents, mcp_servers, jsonc_agent_overrides=None) -> list[Finding]`;
`decide_config(unparseables, findings, agent_count, *, strict=False, override_ack=False) -> ConfigDecision`.

Thin edge (only I/O): `read_agent_files(agents_dir) -> dict[str, str | Unparseable]`;
`read_jsonc(path) -> str | Unparseable`; `config_scan_main(argv=None, config_root=None) -> int`.
Module constants `DEFAULT_MCP_NAMESPACES`, `DEFAULT_HOLDER_MAP`,
`DEFAULT_MCP_SERVER_BASE_NAMES`.

**Decision 1 — `assert_single_holders` deliberately emits BOTH `SINGLE_HOLDER`
and `FAIL_OPEN`; the two fail-open code paths stay DISTINCT (option (a)).**
There are two fail-open-detecting paths and they are kept separate on purpose,
because they answer two *different questions* about two *different populations*:
  - `assert_single_holders` reasons about the **designated single-holder
    namespaces** (git/pm, via `holder_map`). Its anomaly is "*more than the one
    expected* agent fails to deny a namespace that is supposed to be held by
    exactly one." From this one `>1 non-denier` computation it emits, for one
    violation, BOTH a single `SINGLE_HOLDER`/FAIL (the "not single-held" framing,
    naming every non-denier) AND a per-*extra*-agent `FAIL_OPEN`/FAIL naming
    each unexpected non-denier beyond the designated holder (the
    quality-reviewer/session-scribe near-miss framing). The designated holder is
    NEVER itself named as a leak. This dual emission is what lets ST-3 (one
    extra leaker) and ST-6c (two holders) both fall out of the same evidence,
    filtered by `Finding.check`.
  - `check_fail_open` reasons about **every declared MCP server generically**
    (including future/synthetic ones with no `holder_map` entry at all). Its
    anomaly is the opposite extreme: "*zero* agents deny this namespace" — a
    totally-open namespace. It emits `FAIL_OPEN`/FAIL keyed on the server glob
    (not on an agent), and `holder_map` only *enriches the message*, never
    gates the check.
  These are genuinely different semantic checks (a "single-holder violation of
  a designated namespace" is not the same finding as "a namespace nobody in the
  entire roster denies"), even though both wear the `FAIL_OPEN` tag when they
  name a leak. Consolidating them into one parametrised detector (option (b))
  was REJECTED: it would force one function to carry both the
  designated-holder-aware branch and the generic zero-denier branch, muddying
  two cleanly-separable pure functions — the opposite of `boundary.py`'s
  many-small-single-purpose-functions style. **Disambiguation the two `FAIL_OPEN`
  emitters guarantee (so a reader is never confused): `assert_single_holders`'
  `FAIL_OPEN` findings ALWAYS have a `where` of the form `"{agent}: {namespace}"`
  (they name a specific leaking agent); `check_fail_open`'s `FAIL_OPEN` findings
  ALWAYS have a `where` of just `"{namespace}"` (glob only, no agent — nobody
  denies it).** This `where`-shape convention is load-bearing and the tests
  already assume it (mcp_enum.py:185-186 asserts agent+namespace in `where`;
  failopen.py:135-136,168 asserts glob-only in `where`); implement it exactly so
  the two are distinguishable in aggregated output.

**Decision 2 — the four MCP-reasoning functions stay as four separate,
independently-testable public pure functions (matches boundary.py; do NOT
collapse).** `enumerate_effective_tools`, `assert_single_holders`,
`check_fail_open`, `check_global_disable`, `find_mis_scoped_denies` each have a
single, distinct job and a distinct input shape (respectively: raw parsed
agents+override -> effective deny-sets; effective deny-sets vs designated
holders; effective deny-sets vs every server; the *jsonc top-level* tools map;
the *raw* per-agent tools maps for glob-form checking). Crucially they consume
DIFFERENT data: `assert_single_holders`/`check_fail_open` consume the *reduced*
`effective` set (globs that already matched `<server>_*`), while
`find_mis_scoped_denies` MUST consume the *raw* `tools` maps — a mis-scoped glob
(`gleipnir-git*`, no underscore) never enters `effective` at all (by
construction it fails to match), so a detector operating on `effective` could
never see it. That data-shape difference alone justifies separate functions.
This mirrors `boundary.py`'s own decomposition (`classify_probe_result`,
`verdict_for_path`, `check_key_state`, `decide` — small pure functions, each
independently unit-tested, composed by an orchestrator). Collapsing into one
`enumerate`-consuming mega-function was REJECTED: it would sacrifice the
per-function fixture isolation the six test files rely on and hide the raw-vs-
reduced input distinction. The composition lives in `config_scan_main`
(Decision 3), exactly as `run_preflight` composes `boundary.py`'s pure pieces.

**Decision 3 — `config_scan_main`'s authoritative orchestration sequence.**
No single test file drove the full end-to-end wiring; `config_scan_main`
(cli.py) and ST-4 (decide.py:132-175) each sketch it, and they AGREE. The
authoritative sequence the implementer must follow:

1. `agents = read_agent_files(config_root / "agents")` — thin edge; returns
   `dict[str, str | Unparseable]` (a `READ_ERROR` per unreadable file, never a
   raise).
2. For each `(stem, value)` in `agents`: if `value` is an `Unparseable`
   (a `READ_ERROR`), collect it into `unparseables` and continue. Else
   `block = extract_frontmatter(value)`; if `Unparseable`, collect + continue;
   else `parsed = parse_frontmatter(block)`; if `Unparseable`, collect +
   continue; else store `parsed_agents[stem] = parsed` and
   `findings += check_grammar(parsed)`.
3. `jsonc_text = read_jsonc(config_root.parent / "opencode.jsonc")` — thin edge;
   if `Unparseable` (`READ_ERROR`, missing file), collect into `unparseables`
   and treat the jsonc-derived inputs (top-level `tools`, `agent.*.tools`) as
   absent/`None` for the remaining checks. Else `jsonc = parse_jsonc(jsonc_text)`;
   if `Unparseable` (`INVALID_JSONC`), collect + treat jsonc inputs as absent.
4. Derive from parsed `jsonc` (when present): `jsonc_top_level_tools =
   jsonc.get("tools")`; `jsonc_agent_overrides = { name: block.get("tools", {})
   for name, block in jsonc.get("agent", {}).items() }` (the `agent.<name>.tools`
   shape). Both default to `None`/`{}` when the `agent`/`tools` keys are absent
   — the live no-`agent`-key no-op case.
5. `effective = enumerate_effective_tools(parsed_agents, jsonc_agent_overrides)`.
6. `findings += assert_single_holders(effective, DEFAULT_MCP_NAMESPACES,
   DEFAULT_HOLDER_MAP)`.
7. `findings += check_fail_open(DEFAULT_MCP_NAMESPACES, effective,
   DEFAULT_HOLDER_MAP)`.
8. `findings += check_global_disable(jsonc_top_level_tools)`.
9. `findings += find_mis_scoped_denies(parsed_agents, DEFAULT_MCP_SERVER_BASE_NAMES,
   jsonc_agent_overrides)`.
10. `decision = decide_config(unparseables, findings, agent_count=len(parsed_agents),
    strict=<--strict>, override_ack=<--override-ack>)`. Print verdict+label+
    reasons to stderr (as `preflight/__main__.py.main()` does); return
    `0`/`2`/`1` for `CLOSED`/`PROCEED_UNCLOSED`/`REFUSE`.

Cross-check against the six files (consistency confirmed): ST-4
(decide.py:139-175) runs this exact sequence manually and asserts CLOSED on the
live repo; cli.py:54-67 specifies the same wiring and the same 0/1/2 mapping;
`agent_count` is `len(parsed_agents)` (NOT the raw file count), so a `READ_ERROR`
file both (i) adds an `Unparseable` forcing REFUSE and (ii) is excluded from
`parsed_agents` — an all-unreadable run yields `agent_count == 0` AND
unparseables, both independently forcing REFUSE (belt-and-braces, consistent
with cli.py:315-321 empty-dir and cli.py:323-340 unreadable-file tests). No test
assumes a different order or a different inter-stage data shape.

**Decision 4 — module layout: ONE file, `src/gleipnir/preflight/config_scan.py`.**
Every one of the six test files imports `from gleipnir.preflight import
config_scan as cs` and references the JSONC pieces (`parse_jsonc`,
`check_global_disable`, `read_jsonc`) through that same module. Splitting JSONC
handling into a sibling module (e.g. `config_scan_jsonc.py`) would either break
those imports or require re-exporting everything back through `config_scan` —
churn with no benefit at this size. `parse_jsonc` is ~one function
(comment-strip + `json.loads`); `check_global_disable` is a handful of lines.
Keep them in the one module, sibling to `boundary.py`, matching `boundary.py`'s
own single-file layout. (Link-time mechanical decision, not material.)

**Decision 5 — coherence issues found reading the six as a whole.**
- **(resolved, Decision 1) The dual `FAIL_OPEN` `where`-shape convention** —
  the single most important cross-file coherence point: two functions emit
  `FAIL_OPEN`, and only the `where` shape (`"{agent}: {namespace}"` vs
  `"{namespace}"`) distinguishes them in aggregated output. Both conventions
  are already assumed by the tests; Decision 1 elevates it from an implicit
  test assumption to an explicit, documented contract so the implementer does
  not accidentally make the two `where` shapes collide.
- **(resolved, Decision 3) `agent_count` semantics** — must be
  `len(parsed_agents)` (successfully-parsed agents), not the on-disk file
  count; otherwise a repo where every file `READ_ERROR`s would report a nonzero
  `agent_count` and mask the empty-evidence REFUSE. The tests are consistent
  with `len(parsed_agents)` (decide.py:174, cli.py empty/unreadable cases).
- **(naming, consistent) `ConfigVerdict` not `Verdict`; `DEV_MODE_LABEL_CONFIG`
  not `DEV_MODE_LABEL`** — deliberately distinct names from `boundary.py`'s
  `Verdict`/`DEV_MODE_LABEL` to avoid an import collision if a caller ever
  imports both modules (decide.py:23-28 states this rationale). Same three
  values, same 0/2/1 mapping. Keep the distinct names.
- **(parameter ORDER, watch item) `decide_config(unparseables, findings,
  agent_count, ...)`** — every call site (decide.py, cli.py) passes
  `unparseables` FIRST, then `findings`, then keyword `agent_count=`. Note this
  is the OPPOSITE order from the prose sketch in an earlier Trace draft
  ("findings, unparseables"); the TESTS are authoritative — implement
  `(unparseables, findings, agent_count, *, strict=False, override_ack=False)`.
  This is the one spot where the original prescriptive Trace wording and the
  as-built test contract diverge; the test contract wins (it is the arbiter).
  No test needs changing — only the plan's earlier prose, corrected below.
- **No signature mismatches or type-used-differently issues remain** across the
  six files: `Finding`/`Unparseable`/the enums are constructed identically
  everywhere; `enumerate_effective_tools`'s two-arg form and its `None`/`{}`
  no-op are consistent between mcp_enum.py and failopen.py; `holder_map` is
  consulted-but-never-gating in `check_fail_open` consistently. The suite is
  coherent as a whole.

**No test file needs a fix before code can proceed.** Every consolidated
decision above matches what the six files already assume; the only correction
is to the plan's own earlier prose (the `decide_config` argument order and the
`ConfigDecision(reasons)` field name — fixed in the Trace/Assemble edits
accompanying this subsection), not to any test.

---

## L — Link (validated BEFORE building)

Everything the plan asserts was verified this session by reading the actual
files (citations are live, not assumed):

- [x] **Stdlib has no YAML** — confirmed: `sandbox/profiles.py` uses stdlib
  `tomllib`; there is no `import yaml` in `src/`. Option A is therefore the
  route that keeps the enforcement core stdlib-pure. (Validated by reading
  `profiles.py` + the runtime-and-deps constraint.)
- [x] **`boundary.py` shape** — read in full: pure core + injectable thin edge,
  discriminated `ProbeOutcome`, fail-closed `decide`, named `ENFORCEMENT_PATHS`
  tuple, `os.access` deliberately never used. The new module mirrors this shape
  1:1 (validated by reading all 1012 lines).
- [x] **`preflight/__main__.py` CLI convention** — read in full: exit codes
  0=CLOSED / 1=REFUSE / 2=PROCEED_UNCLOSED, argparse, out-of-framework
  (operator-run, not agent-referenced). The new check reuses this convention
  and CLI. **Link-time decision (mechanical, not material): the config scan is
  a subcommand/mode on the existing `gleipnir-preflight` CLI** (e.g.
  `gleipnir-preflight --check=config` or an argparse subparser
  `config-scan`), sharing the fail-closed exit-code mapping — for operator
  consistency and one out-of-framework entrypoint. Rationale: both checks are
  the same audience, same posture, same fail-closed contract; a second binary
  would fragment that. This is exactly the kind of Link-time detail the
  delegation says is the planner's call, not a re-opened material decision.
- [x] **`opencode.jsonc` shape** — read in full: `mcp` block with two servers
  (`gleipnir-git`, `gleipnir-pm`), each `"enabled": true`; NO top-level `tools`
  disable (the known-broken pattern is absent, per bugs 2/3). `//` comments
  only; no block comments or trailing commas in the sampled file. Validated.
- [x] **The accepted-YAML-subset grammar** — inventoried against ALL 9 agent
  files (see Trace grammar section); every construct in the subset is one that
  actually appears, and the OUT-of-subset list is constructs that do NOT appear.
  Validated by reading each file's frontmatter.
- [x] **The three real bugs** — read from `session-lessons-candidates.md` L-C12
  and L-C12b verbatim; each maps to a concrete Stress-test fixture below.
- [x] **Single-holder ground truth** — confirmed from the live files:
  `git-ops.md` denies `gleipnir-pm_*` (keeps git); `project-mgr.md` denies
  `gleipnir-git_*` (keeps pm); orchestrator/quality-reviewer/gleipnir-code/
  gleipnir-plan/gleipnir-brainstorm/notify/session-scribe all deny BOTH. So the
  correct expected state is exactly one non-denier per namespace. Validated.

No live connection to test (no network/DB/creds) — the Link surface here is the
filesystem read, which is exercised by the thin edge + fixtures.

---

## A — Assemble (intended build order)

Test-first (the test is the correctness arbiter, per stage-role-map; the
pure/data-driven core makes this cheap). Build order — data/parse foundation
first, then the checks that consume it, CLI last (mirrors boundary.py's own
bottom-up construction):

> **STATUS UPDATE (post-test-authoring).** All six test files below ARE now
> written on disk (steps 1–6's test halves are done); they collectively specify
> the complete public API. What remains is the **code** stage: implement
> `config_scan.py` against the **authoritative consolidated contract in Trace →
> Design Consolidation** (the single source of truth for signatures, the dual
> `FAIL_OPEN` `where`-shape, and `config_scan_main`'s orchestration). The
> step-by-step "then implement X" notes below remain the intended
> implementation order; where an early step's prose named a rough signature,
> Design Consolidation supersedes it.

1. **Discriminated types + accepted-subset grammar spec, as tests first.**
   Write `tests/test_config_scan_parse.py`: fixtures for every accepted-subset
   construct (flat scalars, quoted glob keys, nested `permission.bash` maps,
   `description: >-` block scalar, `compaction_survival` list, booleans under
   `tools:`) AND for every OUT-of-subset construct (flow map, anchor, tab
   indent, unterminated fence, no frontmatter, **depth-3 map nesting**)
   asserting each yields the right `Unparseable` kind. **Include a DEDICATED
   interleaved-comment fixture** (item-1 construct): a `permission:` map with
   comment lines indented at child depth BETWEEN two sibling children (the
   real `gleipnir-brainstorm.md:16-19` / `git-ops.md:23-30` shape), asserting
   it parses CLEANLY (surviving children read as ordinary siblings) and does
   NOT emit `OUT_OF_SUBSET_YAML` — proving the comment-stripping pre-pass runs
   before structural walking. Do not rely on this riding along inside the
   aggregate ST-4 positive check; it gets its own unit fixture here. THEN
   implement `extract_frontmatter` (with the comment/blank-line pre-pass) +
   `parse_frontmatter` + `parse_jsonc` + the outcome dataclasses to make them
   pass.
2. **Grammar validator (check 1).** Tests: boolean-under-permission FAILs with
   key-path; string-under-`tools` FAILs; a clean agent passes. Then implement
   `check_grammar` + the value-type predicates.
3. **MCP enumeration + single-holder assertion (check 2).** Tests: the live
   9-agent shape passes (exactly one holder each); a missing deny on one agent
   -> 2a fail-open FAIL; two holders -> 2c FAIL; a namespace denied by all ->
   2b over-restriction WARN. **Plus the `agent.<name>.tools` merge (item 2):**
   a fixture where an agent's OWN frontmatter lacks a deny but an
   `opencode.jsonc` `agent.<name>.tools` block supplies it -> the agent counts
   as denied (no false 2a leak); and the inverse (deny only in frontmatter,
   empty opencode override) -> still denied. Assert the live no-`agent`-key
   case is a no-op merge. Then implement `enumerate_effective_tools` (taking
   `jsonc_agent_overrides` and unioning both deny locations) +
   `assert_single_holders` + the in-code holder map.
4. **Generalised fail-open sweep (check 4) + JSONC global-disable + mis-scoped
   glob.** Tests: a synthetic third MCP server left un-denied by everyone ->
   FAIL; a reintroduced top-level `tools: {ns:false}` in opencode.jsonc -> FAIL;
   a missing-underscore deny glob -> WARN. Then implement the THREE separate pure
   functions (Design Consolidation Decision 2): `check_fail_open` (keyed on the
   namespace glob), `check_global_disable` (consumes the JSONC top-level `tools`
   map), and `find_mis_scoped_denies` (consumes the RAW per-agent `tools` maps +
   overrides — NOT `effective`, since a mis-scoped glob never enters `effective`).
5. **Well-formedness aggregation (check 3) + `decide_config`.** Tests: any
   `Unparseable` forces REFUSE; `agent_count == 0` forces REFUSE; all-clean ->
   CLOSED; WARN-only -> CLOSED unless `--strict`; `override_ack` can only
   escalate to PROCEED_UNCLOSED, never CLOSED. Then implement `decide_config(
   unparseables, findings, agent_count, *, strict=False, override_ack=False)`
   mirroring `boundary.decide`'s control flow (note the argument order — Design
   Consolidation Decision 5).
6. **Thin file-read edge + CLI wiring.** Tests inject fixture text into the pure
   core (no real FS); the thin edge is exercised with `tmp_path` + a monkeypatched
   `Path.read_text` raising `OSError` -> `Unparseable(READ_ERROR)`. Then implement
   `read_agent_files`/`read_jsonc` (OSError-wrapping, never propagating) and
   `config_scan_main(argv, config_root)` composing the full pipeline (Design
   Consolidation Decision 3), wired as the `config-scan` subcommand into
   `preflight/__main__.py`, sharing the 0/1/2 exit-code mapping. A CLI smoke
   test asserts the real current repo exits 0 (CLOSED-equivalent) — the live
   regression guard.
7. **Coverage report.** Run under the sandbox (`bin/gleipnir-sandbox test`);
   report line + BRANCH coverage on `config_scan.py` (branch is the arbiter for
   this fail-closed module, L-C2). Every `Unparseable`/`FAIL` branch must be
   hit by a fixture.

Build the parse/data foundation before the checks that consume it, and the CLI
last — the same "don't build the surface for structures that don't exist yet"
discipline ATLAS Assemble prescribes.

---

## S — Stress-test (concrete, fixture-based acceptance checks)

Each check is a named fixture + expected discriminated outcome. "It works" is
not acceptance; these are.

### The three real bugs found this session

- **ST-1 (L-C12: boolean-under-permission).** Fixture agent file with
  `permission:\n  tools:\n    "gleipnir-git*": true`. **Expect:** GRAMMAR FAIL,
  `where = <file>: permission.tools."gleipnir-git*"`, detail names "boolean
  under permission; expected allow/deny/ask". Exit nonzero (REFUSE-equivalent).
- **ST-2 (L-C12b bug 2: global-disable hides tools — NOT-APPLICABLE-POST-FIX
  but must still flag on reintroduction).** The current `opencode.jsonc` has NO
  top-level `tools` disable, so the live config does NOT trigger this (that is
  the fix). Fixture: an `opencode.jsonc` variant that REINTRODUCES
  `"tools": { "gleipnir-git_*": false }` at the top level (global disable).
  **Expect:** FAIL flagging the known-broken global-disable pattern (globally
  disabled MCP tools are invisible to subagents; per-agent re-allow does not
  restore them). Also assert the CURRENT real `opencode.jsonc` does NOT trigger
  this (regression guard that the fix stays fixed).
- **ST-3 (L-C12b bug 3 / bug (c): missing-deny fail-open leak).** Fixture: the
  9-agent set with `quality-reviewer.md` (or `session-scribe.md`) MISSING its
  `"gleipnir-git_*": false` deny line — the exact near-miss caught in review.
  **Expect:** check 2a fail-open FAIL naming the leaking agent + namespace
  ("would silently gain broker tools on restart"). Exit nonzero.

### Well-formedness + generalised checks

- **ST-4 (well-formedness, positive).** All 9 CURRENT agent files parse cleanly
  under the Option-A reader; `opencode.jsonc` parses as valid JSONC. **Expect:**
  no `Unparseable`, checks pass, exit 0.
- **ST-5 (well-formedness, fail-closed negative).** Fixtures: (a) an agent file
  with no `---` fence; (b) an unterminated fence; (c) frontmatter using a flow
  mapping `permission: {edit: deny}` (out of subset); (d) tab-indented
  frontmatter; (e) a depth-3 nested map (out of subset per the depth-2 cap).
  **Expect:** each yields the correct `Unparseable` kind (`(e)` ->
  `OUT_OF_SUBSET_YAML`) and forces REFUSE — NEVER silently skipped, NEVER
  guessed.
- **ST-6 (single-holder, all three sub-flags).** (a) live shape -> exactly one
  holder per namespace, pass; (b) two agents un-deny `gleipnir-git_*` ->
  fail-open FAIL (2a); (c) two agents both hold `gleipnir-pm` -> 2c FAIL; (d)
  every agent denies a namespace -> 2b over-restriction WARN (not FAIL unless
  `--strict`).
- **ST-7 (generalised fail-open, future MCP server).** Fixture: `opencode.jsonc`
  with a third server `gleipnir-foo`, and NO agent denying `gleipnir-foo_*`.
  **Expect:** check 4 FAIL (generalises beyond the two known broker namespaces)
  — proving the rule is not hardcoded to git/pm.
- **ST-8 (mis-scoped deny glob, WARN).** Fixture: an agent denying
  `"gleipnir-git*": false` (no underscore). **Expect:** WARN that the glob may
  not match the `<server>_<tool>` names (L-C12b(b)), so it is not a silent
  fail-open.
- **ST-9 (grammar, string-under-tools).** Fixture: `tools:\n  "gleipnir-pm_*":
  deny` (string where boolean required). **Expect:** GRAMMAR FAIL.
- **ST-12 (interleaved comment parses clean — item 1).** Fixture: a
  `permission:` map with comment lines indented at child depth between two
  sibling children (the real `gleipnir-brainstorm.md:16-19` shape). **Expect:**
  parses cleanly, NO `OUT_OF_SUBSET_YAML`, the surrounding children validate as
  normal — proving the comment-stripping pre-pass runs before structural
  walking (a regression guard against a false-REFUSE on valid config).
- **ST-13 (`agent.<name>.tools` override merge — item 2).** Fixtures: (a) an
  agent whose own frontmatter lacks a broker deny but whose `opencode.jsonc`
  `agent.<name>.tools` block supplies it -> NOT a fail-open leak (merged deny
  counts); (b) the live no-`agent`-key `opencode.jsonc` -> merge is a no-op and
  the live 9-agent shape still passes. **Expect:** the effective deny-set is the
  union of both locations; neither location alone produces a false result.

### Aggregate + coverage

- **ST-10 (fail-closed aggregation).** Any single `Unparseable` OR any `FAIL`
  Finding OR an empty agent set forces REFUSE (exit 1); `--override-ack` (if
  implemented for parity) can only escalate to PROCEED_UNCLOSED (exit 2), never
  CLOSED (exit 0) — assert no code path from override to CLOSED, mirroring
  `boundary.decide`.
- **ST-11 (branch coverage).** Report line + branch coverage on
  `config_scan.py`; every `Unparseable` kind (including `READ_ERROR`, exercised
  by injecting a `ReadError`/raising `OSError` into the thin edge) and every
  `Finding` severity/check branch is exercised by a fixture above. A green pass
  count over unhit fail-closed branches is not acceptance (L-C2).

---

## Execution Workflow (for the implementing agent — act without re-deriving)

**Stage sequence from here (orchestrator sequences; this section tells the
implementer the protocol):**

1. **spec-review** (quality-reviewer): review THIS plan against the four
   Architect checks and the fail-closed/pure-core-thin-edge constraints before
   any code. This is a guard whose failure mode is a false SUCCESS (a checker
   that says "config clean" when it is not, or that silently skips an
   unparseable file) — so per L-C7 it warrants adversarial review weighted by
   blast radius. Specifically probe: can any input make the checker exit 0 while
   a real bug is present? (false-CLOSED, the boundary.py bug class.)
2. **test** (gleipnir-code): author the fixtures + tests in Assemble order
   (steps 1-6), tests FIRST. The tests ARE the correctness definition. Run in
   the S-2 sandbox (`bin/gleipnir-sandbox test`) — never on the host; attach raw
   output + coverage (the reviewer cannot fabricate a pass it did not observe,
   L-C8).
3. **code** (gleipnir-code): implement `config_scan.py` (pure core + thin edge)
   and the `preflight/__main__.py` subcommand to make the tests green. Mirror
   `boundary.py`'s discriminated-outcome and fail-closed discipline: catch
   specific exceptions where the failure mode is known; where an outer boundary
   needs a catch-all, exactly one deliberate broad `except Exception` mapped
   ONLY to a fail outcome is correct (the `boundary.py:654-659` pattern) — a
   broad except that could yield "clean" is the defect.
4. **quality** (quality-reviewer): blast-radius review against this plan +
   coverage; specifically re-check every fail-closed branch is hit and no
   `except Exception` swallows a would-be FAIL into a pass.
5. **git** (git-ops): commit via the broker (`commit_changes`), whole-path
   staging (L-C11 — never an agent-driven `-p` hunk-split); push via
   `push_current_branch`. Commit the module + tests together.
6. **gate** (orchestrator): read authoritative evidence (tests green + coverage
   attached); do not self-declare done.

**Key implementation invariants (non-negotiable, from the mirrored exemplar):**
- Each failure is its own discriminated outcome; a parse/read error must never
  be indistinguishable from a "clean" result. Broad-except rule (per
  `boundary.py:654-659`): catch specific exceptions where the failure mode is
  known; a single deliberate broad `except Exception` at an outer boundary is
  acceptable IFF it can only ever map to a fail outcome, never a pass. The
  defect is a broad except that could yield "clean" — not the broad except
  itself.
- `os.access` is not the model here; there is no privilege probe — but the
  *fail-closed spirit* is identical: ambiguity => REFUSE.
- The pure core takes text/parsed-data arguments and is fully unit-testable
  with fixture strings; the file-read edge is the only I/O and is injectable.
- The single-holder map and the accepted-subset grammar are DATA in code,
  changed only by a reviewed edit — not inferred, not globbed permissively.
- Report by key-path (frontmatter has no post-parse line numbers).

**Definition of done for this slice:** all ST-1..ST-11 pass in the sandbox with
branch coverage reported; the current real repo exits 0 through the new
subcommand; the three real bugs (via fixtures) and the generalised fail-open
each produce a nonzero exit with a key-path-precise reason.

---

## Follow-ons (flagged, NOT decided, NOT in this slice)

- **Hook / CI wiring.** Whether this content-preflight becomes a **git
  pre-commit hook** and/or a **CI check** (so restart-only config bugs are
  caught at commit/CI time, not merely when an operator remembers to run it) is
  a **noted follow-on requiring its own convergence** — L-C12(a)/L-C12b(d) both
  point at exactly this ("validate the config against opencode's schema before
  declaring done ... a schema/scoping preflight ... would have caught both ...
  before restart"). It is deliberately OUT of this slice's scope: this slice
  delivers the checker; where it is *invoked from* is a separate decision
  (hook vs CI vs both vs operator-run-only has real tradeoffs — false-positive
  lockups on hooks, per the broker-hook history). **Do not decide it in this
  plan; surface it for operator convergence when the checker exists.**
- **Deeper opencode schema validation** (beyond the four checks) — a possible
  future superset; explicitly not attempted here.

---

## New material tradeoffs hit while planning

**NONE.** The one known material tradeoff — the parser approach — is already
CONVERGED (Option A, source: orchestrator↔operator `question` this session) and
is planned FROM, not re-decided. Every other choice made in this plan (config
scan as a subcommand on the existing CLI; sharing the 0/1/2 exit-code
convention; `--strict` promoting WARN->FAIL; an optional `--override-ack` for
parity) is a bounded Link-time / mechanical detail, resolved in-plan as the
plan-format permits — not a re-opened material decision. The hook/CI-wiring
question IS a future material decision, but it is explicitly deferred as a
follow-on for the operator to converge later, NOT decided here.
