# Plan: content-handler plugin library + diff-truncation handler, wired into `git_diff`

> **Stage:** `plan` (gleipnir-plan). **Input:** the CONVERGED brief
> `git-diff-distill-brainstorm.md` (operator-converged via the orchestrator;
> status CONVERGED, no open D-N decisions). It **supersedes** the dead draft
> `context-crush-brainstorm.md` — that file was NOT read and is NOT planned
> from. This plan does **not** re-decide the eight already-converged items
> (deterministic-only / no-new-MCP-surface / plugin-architecture /
> diff-shaped-rule / structural-safety / stdlib-only / provenance-docstring /
> codegraph-out-of-scope). It plans the *bounded* work those decisions define,
> and resolves only the four plan-stage judgments the brief explicitly
> delegated (module placement, threshold values, call site, test plan).
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0). This file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it — the orchestrator
> sequences that; nothing here is executed now. In particular this plan
> **names** the one Tier-3 edit it requires (`.gleipnir/sandbox/profiles.toml`
> `[profile.broker].test` file-list amendment, adding BOTH new broker test
> files — the handler unit test and the integration test — to that literal
> enumeration); it does not write it.

---

## Decisions (index)

Summary of every decision this plan fixes, in order encountered; full reasoning
for each is in the sections below. Rows 1–8 → the CONVERGED brief
`git-diff-distill-brainstorm.md` (operator-converged; recorded, NOT re-decided).
Rows 9–13 → `[PLAN-STAGE JUDGMENT]` decisions made during Architect/Trace,
flagged for spec-review per the delegation.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Trigger | Deterministic, in broker code, on a coded threshold; zero LLM judgment | Agent-invoked "distill" tool / MCP surface | Axiom 1 / G-5: enforcement is code, never a model's choice to invoke. **Brief item 1/2 — operator-converged, not re-decided.** |
| 2 | Exposure | Plain internal library code `git_diff`'s impl calls before returning | New MCP server / new tool schema in any agent context | A new tool schema contaminates every session's context — the exact failure the fix targets. **Brief item 2 — operator-converged.** |
| 3 | Shape | `Handler` protocol + generic registry/dispatcher (no handler-specific logic) + exactly ONE registered handler | A single hard-coded `diff_truncate(text)->text` function | Future handler must register without editing dispatcher or diff handler — a testable extensibility property. **Brief item 3 — operator-converged.** |
| 4 | Truncation rule | Diff-shaped: keep file list + `+N -M` stat always; hunk body over `T` → first/last `N` + explicit `# ... (K lines truncated)` marker; never silent-drop | Code-shaped AST technique; silent drop | A unified diff is not source code. **Brief items 4/5-of-rule — operator-converged.** |
| 5 | Structural safety | Handler `process(content)` sees ONLY raw content; envelope/verdict/commit-metadata structurally unreachable (function signature cannot reach them) | Docstring-only assertion; handler receiving the response dict | True by construction, not by assertion. **Brief item 5 — operator-converged.** |
| 6 | Dependencies | stdlib-only, zero new runtime dep | Any new dep | Positive property to preserve; broker layer *may* carry justified deps but this needs none. **Brief item 6 — operator-converged.** |
| 7 | Provenance | The brief's `## Provenance` fenced block appears **verbatim** in the module docstring | Paraphrase; omit | Clean-room attribution; no Headroom trademarks. **Brief item 7 — operator-converged; quoted verbatim in Trace.** |
| 8 | codegraph | OUT OF SCOPE — no AST/code handler, no dependency-graph capability built | Building any code handler now | Extensibility exists so a FUTURE codegraph-adjacent handler is addable without redesign; not built now. **Brief item 8 — operator-converged.** |
| 9 | **`[PLAN-STAGE JUDGMENT]`** Module placement | **Inside `broker/git/` as a subpackage `broker/git/content_handlers/`** (protocol + `ProcessedResult` + registry), sibling `broker/git/diff_hunk_handler.py` | New independently-versioned sibling component `src/gleipnir/broker/content_handlers/` with own `pyproject.toml`+VERSION | Only `git_diff` consumes it now; `broker/git/` already sets the exact precedent (`guards.py`: stdlib-only helper imported by `mcp_server.py`); the existing `test_broker_stdlib_only.py` part (ii) already guards it; a new versioned component + profile setup is premature for a single-consumer pilot. **Reuse seam preserved** (importable subpackage, not inlined) so a future promotion to a shared sibling is a move, not a rewrite. Flagged for spec-review. |
| 10 | **`[PLAN-STAGE JUDGMENT]`** Threshold `T` | **`T = 40`** hunk-body lines | 20 (too aggressive; truncates ordinary edits) / 100 (too permissive; large refactors still flood context) | A typical readable hunk is < ~40 lines; pathological machine-generated / lockfile-shaped / vendored diffs run to hundreds/thousands. 40 preserves normal review diffs verbatim while catching the flood case. Tuning param, no operator convergence (brief). Flagged for spec-review. |
| 11 | **`[PLAN-STAGE JUDGMENT]`** First/last-keep `N` | **`N = 8`** (`2N = 16 < T = 40`) | 3 (loses hunk context) / 20 (`2N=40` = `T`, no compression headroom) | 8 lines each end shows the hunk header context + the leading and trailing changed region while guaranteeing `2N < T` so a truncated hunk is strictly smaller than the threshold that triggered it. Tuning param (brief). Flagged for spec-review. |
| 12 | **`[PLAN-STAGE JUDGMENT]`** Line-count basis for `T` | Count **hunk body lines** (the lines under a `@@` header, excluding the `@@` header line and file/`diff --git`/`index`/`---`/`+++` header lines) | Counting whole per-file section incl. headers | Item 4 mandates headers + stat are ALWAYS preserved and never truncation candidates; the threshold must therefore be measured over exactly the truncatable region (the hunk body), or `T` would mis-fire on header-heavy small diffs. Flagged for spec-review. |
| 13 | **`[PLAN-STAGE JUDGMENT]`** Test-collection wiring | **BOTH** new broker test files are added to `.gleipnir/sandbox/profiles.toml` `[profile.broker].test`'s literal file-list (a Tier-3 edit adding TWO filenames): the stdlib-only handler unit/extensibility/structural test `test_broker_git_content_handlers.py` AND the `mcp`-importing integration test `test_broker_git_diff_distill.py`. Additionally, ONLY the integration test (transitive `mcp` import) is added to `tests/conftest.py` `collect_ignore` (code edit) so the lean `python` profile skips it when `mcp` is absent | Assuming the stdlib-only test "runs in both profiles with no `profiles.toml` edit" (FACTUALLY WRONG — `[profile.broker].test` is a literal enumeration with `test_selector_prefix = false`; every existing broker test, stdlib-only ones included, is listed, so an unlisted file is NOT collected under the broker profile); or omitting either file (silent non-collection) | Mirrors the ACTUAL existing convention (verified: `test_broker_git_guards.py`, `test_broker_pm_platform.py`, `test_broker_stdlib_only.py` are ALL enumerated in `[profile.broker].test` despite being stdlib-only). The handler unit test also runs under the default `python` profile (stdlib-only, not in `collect_ignore`), so it is exercised in both — but that dual coverage is a *consequence* of it being stdlib-only, NOT a substitute for listing it in the broker profile. Corrected after spec-review round 1. |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`goals/manifest.md`):** "Plan format" (`plan-format.md`) and
  "Methodology (ATLAS/GOTCHA ahead of planning)" apply. This plan follows the
  required Decisions-index / Architect / Trace / Link / Assemble / Stress-test /
  Execution Workflow / Design Principles structure. No pipeline-sequencing goal
  is authored or implied (G-5 rule respected).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or git are produced here — only this plan file.
- **Layer placement (GOTCHA layers):** this is a **Tools-layer** concern (the
  internal implementation of an existing broker tool `git_diff`) with a small
  **Args-layer** structural boundary (the handler signature that cannot reach
  the response envelope). It is explicitly **NOT** enforcement core (no
  G-3/G-5/G-4/memory logic), and does NOT touch G-5 pipeline ordering (the
  `git` stage still binds only to `git-ops`; only `git_diff`'s *output shaping*
  changes). It adds **no new agent-facing tool schema** (item 2).
- **Gaps / factual findings named (mechanical, NOT material):**
  1. **The stdlib-only conformance test already covers the new modules for
     free.** `tests/test_broker_stdlib_only.py` part (ii) asserts that within
     `broker/`, `mcp` is imported ONLY by files named `mcp_server.py`. Placing
     the content-handler library under `broker/git/` (Decision 9) means the new
     `content_handlers/` package and `diff_hunk_handler.py` are automatically
     held to stdlib-only by an EXISTING test — no new conformance test needed
     for the stdlib-only property (item 6). Verified this session.
  2. **The broker test profile is an explicit file list (Tier-3) that
     enumerates EVERY broker test — stdlib-only ones included.**
     `.gleipnir/sandbox/profiles.toml` `[profile.broker].test` is a literal
     filename enumeration with `test_selector_prefix = false`; verified this
     session, its current list contains the stdlib-only tests
     (`test_broker_git_guards.py`, `test_broker_pm_platform.py`,
     `test_broker_stdlib_only.py`) ALONGSIDE the `mcp`-dependent ones. There is
     no counterexample of a stdlib-only broker test omitted from that list.
     Therefore the actual convention is "every broker test file is enumerated in
     `[profile.broker].test`, stdlib-only or not" — a file NOT in the list is
     NOT collected under the broker profile at all. **Both** new broker test
     files (the stdlib-only handler unit test and the `mcp`-importing
     integration test) must therefore be added to that list (one Tier-3 edit,
     two filenames). Separately, only the integration test is added to
     `tests/conftest.py` `collect_ignore` so the lean `python` profile skips it
     when `mcp` is absent; the stdlib-only handler unit test is left OUT of
     `collect_ignore` so it ALSO runs under the default `python` profile
     (dual-run is a bonus of it being stdlib-only, not a reason to omit it from
     the broker list). Corrected after spec-review round 1.
  3. **The exact call site is `git_diff` lines 324–329** — `result =
     _run_git(args, rd)`, success path `return json.dumps({"success": True,
     "diff": result["stdout"]})`. Dispatch is inserted immediately before that
     return, on `result["stdout"]` alone (Trace §call-site). Verified against
     the live source this session.

**New material tradeoff found?** **No.** Every material tradeoff was settled in
the CONVERGED brief. The four items the brief explicitly delegated to the plan
stage (placement, threshold `T`, keep-count `N`, call site + test plan) are
**bounded tuning/wiring choices, not material design tradeoffs** — the brief
names them as "plan-stage tuning parameters requiring no operator convergence"
and "the planner's call." I record them as `[PLAN-STAGE JUDGMENT]` rows and
flag them for spec-review (per the delegation), which is the correct routing:
they are checkable, not operator-convergence-gated. **Nothing here is a
quietly-enshrined cap-model-style decision** — the one arguably-consequential
choice (placement, Decision 9) is explicitly surfaced with its reuse-vs-
simplicity reasoning for spec-review to check, not smuggled.

---

## 1. Architect

**Problem (one sentence):** `git_diff` returns the entire raw `git diff` output
in one call, flooding the calling agent's context and degrading its reasoning
on large diffs; fix it by having the broker's own `git_diff` implementation
deterministically truncate oversized diff-hunk bodies before returning — via a
generic, stdlib-only content-handler plugin library with exactly one registered
diff-truncation handler — keeping the file list and stat summary intact and the
full diff always recoverable from git itself.

**User:** the calling roster agent whose context is currently polluted by large
`git_diff` output (chiefly `quality-reviewer` / any agent reviewing a diff via
`git-ops`); and, structurally, the future maintainer who will register a second
handler (e.g. an AST-based code handler) without touching the dispatcher.

**Measurable success criteria:**

1. A new stdlib-only content-handler library exists under `broker/git/`
   (Decision 9) defining a `Handler` protocol
   (`can_handle(content, hint) -> bool`, `process(content) -> ProcessedResult`),
   a `ProcessedResult` type, and a registry/dispatcher (`register(handler)`,
   `dispatch(content, hint) -> ProcessedResult`) containing **no
   handler-specific logic** and with a no-handler fallback returning content
   unchanged.
2. Exactly **one** handler is registered in this pilot:
   `DiffHunkTruncationHandler`, implementing the item-4 diff-shaped rule with
   `T = 40` and `N = 8` (Decisions 10–12). Its module header docstring carries
   the brief's `## Provenance` block **verbatim**.
3. `git_diff`'s success path returns the dispatched (possibly truncated) text as
   its `"diff"` field; the response envelope (`{"success": True, "diff": ...}`)
   is otherwise **unchanged**. No other tool is touched.
4. **Structural safety (item 5) is true by construction:** the handler's
   `process` signature accepts only a `str` (raw diff text) and returns a
   `ProcessedResult` carrying `str`; the `Handler`/`ProcessedResult` contract
   has **no parameter for and no reference to** the envelope, `success` flag,
   any commit hash, or the secret-scan verdict. Provable by a type/structural
   test, not just a behavioural one.
5. **Extensibility is proven by a test (item 3):** registering a second stub
   handler (different `hint`) results in (a) that stub being dispatched to for
   its content, (b) the diff handler still working unchanged, and (c) no edit
   to the dispatcher module or the diff-handler module being required to make it
   pass.
6. The truncation rule is correct: below-`T` hunk bodies pass through verbatim;
   above-`T` hunk bodies keep first `N` + last `N` body lines and replace the
   middle with exactly `# ... (K lines truncated)` where `K` is the exact count
   removed; the file list + `+N -M` stat summary are **never** altered;
   multi-file diffs keep every file's stat line.
7. **No new runtime dependency** (item 6); the new modules import stdlib only,
   held by the existing `test_broker_stdlib_only.py` part (ii).
8. **No new MCP server, no new agent-facing tool schema** (item 2): the library
   is internal code called by `git_diff`'s implementation; the `gleipnir-git`
   tool surface stays exactly the four existing tools.

**Constraints (from the brief — FIXED, not re-litigated):**

- Deterministic-only, zero LLM judgment (item 1); no new MCP/tool surface
  (item 2); plugin architecture with a generic dispatcher + exactly one handler
  (item 3); diff-shaped rule (item 4); structural safety by construction
  (item 5); stdlib-only (item 6); verbatim provenance docstring (item 7);
  codegraph out of scope (item 8).
- Runtime: Python >= 3.11 (matches `broker/git/pyproject.toml`
  `requires-python`). The library is stdlib-only, so `mcp` is irrelevant to it.

---

## 2. Trace

### Chosen module layout (resolves brief open question "module/package placement" — Decision 9)

```
src/gleipnir/broker/git/
  __init__.py            # (edit) update module list docstring to name the new package
  guards.py              # (unchanged) existing stdlib-only precedent
  mcp_server.py          # (edit) git_diff: register handler + dispatch on result["stdout"]
  content_handlers/      # NEW subpackage — the generic, reusable plugin library (stdlib-only)
    __init__.py          # exports Handler, ProcessedResult, register, dispatch (the reuse seam)
    protocol.py          # Handler protocol + ProcessedResult dataclass; NO handler-specific logic
    registry.py          # register()/dispatch(); NO handler-specific logic, no-handler fallback = unchanged
  diff_hunk_handler.py   # NEW — the ONE pilot handler: DiffHunkTruncationHandler (T=40, N=8);
                         #        carries the ## Provenance block VERBATIM in its module docstring
```

**Rationale (Decision 9, `[PLAN-STAGE JUDGMENT]`, flagged for spec-review):**
`broker-mcp.md`'s convention is "each broker is its OWN independently-versioned
component" (`broker/{git,pm}/` each with `pyproject.toml`+`VERSION`). The
question the brief raises is whether the content-handler library should be a
**new sibling component** `src/gleipnir/broker/content_handlers/` (own
`pyproject.toml`+VERSION, reusable by BOTH `git` and `pm`) or live **inside
`broker/git/`**. I choose **inside `broker/git/`** because:

- **Only `git_diff` consumes it now.** No `pm` tool has unbounded output (the PM
  tools are bounded per `broker-mcp.md` Decision 2). Building a shared,
  independently-versioned sibling — with its own `pyproject.toml`, `VERSION`,
  and a `[profile.broker]` coverage/test consideration — is premature setup for
  a single-consumer pilot (YAGNI; the brief's item 8 forward-note explicitly
  says the reuse is *future*, not now).
- **`broker/git/` already establishes the exact precedent.** `guards.py` is a
  stdlib-only helper imported by `mcp_server.py`; the content-handler library is
  the same shape (stdlib-only logic module(s) imported by `mcp_server.py`).
- **The reuse seam is preserved, not sacrificed.** It is an importable
  subpackage (`content_handlers/`), NOT inlined into `mcp_server.py` (item 3 +
  brief §reuse-seam forbid inlining). Promoting it later to a shared sibling
  `src/gleipnir/broker/content_handlers/` is a **move + import-path change**,
  not a rewrite — the protocol/registry/handler boundaries are identical either
  way.
- **The existing stdlib-only conformance test covers it for free.**
  `test_broker_stdlib_only.py` part (ii) already asserts that any file under
  `broker/` importing `mcp` must be named `mcp_server.py`; the new modules
  (not so named) are therefore held stdlib-only by an existing test the moment
  they land under `broker/git/`. A sibling `broker/content_handlers/` would also
  be covered by part (ii) (it globs all of `broker/`), so this is not the
  deciding factor — but it confirms the placement carries no conformance cost.

**The counter-argument, stated honestly for spec-review:** the long-term-correct
home *if* a `pm` (or other) consumer ever appears is the independently-versioned
sibling. If spec-review judges that future near-certain (item 8's codegraph
note leans that way), the sibling is defensible. I judge single-consumer
simplicity wins for the pilot and the seam makes promotion cheap; spec-review
should confirm or overturn.

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Source-of-truth role |
|---|---|---|---|---|
| Handler protocol + `ProcessedResult` | NEW `src/gleipnir/broker/git/content_handlers/protocol.py` | source tree (under `src/`, outside `.gleipnir/**`) | bounded `gleipnir-code` | The generic contract: `can_handle`/`process`, content-only boundary. stdlib-only. |
| Registry/dispatcher | NEW `src/gleipnir/broker/git/content_handlers/registry.py` | source tree | bounded `gleipnir-code` | `register()`/`dispatch()`; no handler-specific logic; no-handler fallback. stdlib-only. |
| Library package init (reuse-seam export) | NEW `src/gleipnir/broker/git/content_handlers/__init__.py` | source tree | bounded `gleipnir-code` | Re-exports `Handler`, `ProcessedResult`, `register`, `dispatch`. |
| The ONE pilot handler | NEW `src/gleipnir/broker/git/diff_hunk_handler.py` | source tree | bounded `gleipnir-code` | `DiffHunkTruncationHandler` (item-4 rule, `T=40`/`N=8`). **Carries `## Provenance` verbatim.** stdlib-only. |
| Broker call site | EDIT `src/gleipnir/broker/git/mcp_server.py` (`git_diff`, lines ~300–329) | source tree | bounded `gleipnir-code` | Register the diff handler; dispatch on `result["stdout"]` before wrapping the envelope. |
| Package docstring update | EDIT `src/gleipnir/broker/git/__init__.py` | source tree | bounded `gleipnir-code` | Name the new modules alongside `guards.py`/`mcp_server.py`. |
| Handler unit + extensibility + structural tests | NEW `tests/test_broker_git_content_handlers.py` | source tree | bounded `gleipnir-code` | stdlib-only (no `mcp` import). MUST be added to `[profile.broker].test` (see below) to be collected under the broker profile; also runs under the default `python` profile (left out of `collect_ignore`). The arbiter for the truncation rule, structural safety, and extensibility. |
| `git_diff` integration test | NEW `tests/test_broker_git_diff_distill.py` | source tree | bounded `gleipnir-code` | Imports `mcp_server` (transitive `mcp`) → broker-profile only. Round-trips a large fixture diff through the real `git_diff` tool. |
| Broker test profile file-list | EDIT `.gleipnir/sandbox/profiles.toml` `[profile.broker].test` | **Tier-3 POLICY** | **operator only** | Add **BOTH** new broker test filenames — `tests/test_broker_git_content_handlers.py` AND `tests/test_broker_git_diff_distill.py` — to the literal enumeration (`test_selector_prefix = false`), matching the existing convention that every broker test, stdlib-only or not, is listed. One Tier-3 edit, two filenames. |
| `conftest.py` collect-ignore | EDIT `tests/conftest.py` `collect_ignore` | source tree (under `tests/`, outside `.gleipnir/**`) | bounded `gleipnir-code` | Add ONLY `test_broker_git_diff_distill.py` (the `mcp`-importing integration test) so the lean `python` profile skips it when `mcp` is absent. Do NOT add the stdlib-only handler unit test — it is meant to run under the `python` profile too. |

**Critical Trace consequence:** the feature is almost entirely bounded
`gleipnir-code` territory (all `src/gleipnir/broker/git/**` modules, both test
files, and the `tests/conftest.py` edit — all under `src/` or `tests/`, outside
`.gleipnir/**`). The **only** Tier-3 operator action is the
`.gleipnir/sandbox/profiles.toml` `[profile.broker].test` amendment — a single
edit that adds **two** filenames (the handler unit test AND the integration
test) to the literal file-list, matching the existing convention that every
broker test is enumerated there. This is made explicit in the Execution
Workflow split table.

### The `## Provenance` docstring (item 7 — reproduce VERBATIM in `diff_hunk_handler.py`)

The following fenced block, quoted exactly from the brief's `## Provenance`
section, MUST appear verbatim in the `diff_hunk_handler.py` module header
docstring:

```
Diff-shaped structure-preserving truncation. The general idea — keep the
summary/skeleton, collapse the verbose body, mark what was cut — is inspired
by Headroom's CodeAwareCompressor / SmartCrusher concept
(https://github.com/headroomlabs-ai/headroom, Apache-2.0). This is an
independent, Gleipnir-native reimplementation of that BEHAVIOUR for a
unified-diff input (a diff is not source code, so AST techniques do not
apply); it is NOT a port or derivative of Headroom's source. No Headroom
code, binary, package, model, or network service is consumed. Headroom's
trademarked names (Headroom, SmartCrusher, CodeCompressor,
CodeAwareCompressor, Kompress) are NOT used; Apache-2.0 §6 grants no
trademark rights and none are claimed.
```

(The implementing agent must copy this block character-for-character; a
spec-review check confirms verbatim presence — see Stress-test T-7.)

### Integrations map

```
git_diff(...)  [mcp_server.py]
   │  args = ["diff", ...]; result = _run_git(args, rd)
   │  on success:
   │     ┌─────────────────────────────────────────────────────────────┐
   │     │ dispatch(result["stdout"], "diff")   # content_handlers.registry │
   │     │    → DiffHunkTruncationHandler.can_handle(content,"diff")→True  │
   │     │    → .process(content) → ProcessedResult(content=<truncated>)   │
   │     └─────────────────────────────────────────────────────────────┘
   │  return json.dumps({"success": True, "diff": <processed .content>})
```

- The handler receives **only** `result["stdout"]` (a `str`) and the opaque
  `hint` `"diff"`. It never sees the envelope, `success`, any hash, or the
  secret-scan verdict (item 5 — structurally unreachable).
- Registration happens once at module import of `mcp_server.py` (a module-level
  `register(DiffHunkTruncationHandler())` call), so dispatch is ready when
  `git_diff` runs. (Implementing agent: prefer a single module-level registry
  populated at import; keep it deterministic and side-effect-free beyond the
  registration itself.)
- **No credential, no network, no new subprocess** — this is pure in-process
  string transformation on already-captured `git diff` stdout.

### Exact call site (resolves brief delegation "where in `git_diff` this gets called")

Current `mcp_server.py` `git_diff` (verified this session):

```python
    result = _run_git(args, rd)
    if not result.get("success"):
        return json.dumps(
            {"success": False, "error": result.get("error") or result.get("stderr", "")}
        )
    return json.dumps({"success": True, "diff": result["stdout"]})   # <- lines 325-329
```

The dispatch is inserted **between the success check and the final return**, on
`result["stdout"]` alone:

```python
    result = _run_git(args, rd)
    if not result.get("success"):
        return json.dumps(
            {"success": False, "error": result.get("error") or result.get("stderr", "")}
        )
    processed = dispatch(result["stdout"], "diff")           # NEW: content-only boundary
    return json.dumps({"success": True, "diff": processed.content})
```

The error path (`success: False`) is **untouched** — truncation only applies to
successful, non-empty diff output; the no-handler fallback and an empty/small
diff both round-trip unchanged.

### Edge cases

1. **Below-threshold hunk** (body ≤ `T`) → emitted verbatim; no marker.
2. **Empty diff** (`result["stdout"] == ""`) → `can_handle` may match but
   `process` returns the empty string unchanged; no crash, no marker.
3. **Multi-file diff, one file large** → only the oversized file's hunk body is
   truncated; every file's `diff --git`/header/stat line is preserved; small
   files pass through verbatim.
4. **Multiple hunks in one file, some large some small** → each hunk body is
   evaluated independently against `T`; small hunks verbatim, large hunks
   truncated with their own accurate `K`.
5. **A hunk body containing text that resembles a secret/hash/verdict** → it is
   only ever treated as hunk-body text; the handler has no concept of those
   fields (item 5). The secret-scan verdict lives on `commit_changes`, not
   `git_diff`, and is never in this handler's reach regardless.
6. **Malformed / non-unified-diff input** (e.g. `git diff` output that does not
   parse into `@@` hunks) → the handler must **fail safe: return the content
   unchanged** rather than raise or drop. Truncation is best-effort
   size-reduction; correctness of the returned diff-as-text must never be
   sacrificed. (Implementing agent: a parse that finds no `@@` hunks yields the
   input verbatim.)
7. **A truncated hunk must stay smaller than the trigger** — `2N < T`
   guaranteed by Decision 11 (`16 < 40`), so truncation always reduces size.
8. **`K` accuracy** — the marker's `K` must equal the exact number of body lines
   removed (`body_line_count - 2N`); an off-by-one here is a correctness defect
   the unit test must catch (Stress-test T-3).
9. **No-handler fallback** — `dispatch(content, hint)` with no matching handler
   returns `ProcessedResult(content=content)` unchanged (item 3); the extensibility
   test's stub proves the selection path, and this proves the empty-registry path.

---

## 3. Link — what must be validated BEFORE building

Every fact below was re-read from the actual files this session:

- **L1 (call site verified).** `git_diff` is `mcp_server.py` lines 300–329; the
  success return is line 329 `return json.dumps({"success": True, "diff":
  result["stdout"]})`. The dispatch insertion point is unambiguous (Trace
  §call-site). Confirmed against live source.
- **L2 (stdlib-only conformance is already enforced).**
  `tests/test_broker_stdlib_only.py` part (ii)
  (`test_mcp_imported_only_by_mcp_server_modules`) globs all of `broker/` and
  fails any non-`mcp_server.py` file importing `mcp`. The new modules land under
  `broker/git/` and are stdlib-only by requirement (item 6); this existing test
  covers them with **no new conformance test required**. Confirmed by reading
  the test.
- **L3 (test-collection split is real and must be honoured — corrected after
  spec-review round 1).** `tests/conftest.py` `collect_ignore` skip-collects
  `mcp`-importing broker test files when `mcp` is absent (lean `python`
  profile). The `git_diff` integration test imports `mcp_server` transitively,
  so it goes in `collect_ignore` (code edit); the stdlib-only handler unit test
  does NOT (it is meant to run under the `python` profile too). **Both** new
  test files must be added to `.gleipnir/sandbox/profiles.toml`
  `[profile.broker].test` (Tier-3 operator edit) — see L4 — or they will not be
  collected under the broker profile. My round-1 claim that the stdlib-only
  handler unit test "runs in both profiles with no `profiles.toml` edit" was
  factually wrong (see L4). Confirmed by reading both files.
- **L4 (broker profile test list is an explicit enumeration that lists EVERY
  broker test).** `[profile.broker].test` is a literal list of test filenames;
  scoping is `test_selector_prefix = false`, so files not in the list do not run
  under the broker profile. **Verified this session:** the list currently
  includes the stdlib-only broker tests (`test_broker_git_guards.py`,
  `test_broker_pm_platform.py`, `test_broker_stdlib_only.py`) alongside the
  `mcp`-dependent ones — there is no stdlib-only broker test omitted from it. So
  the convention is "every broker test file is enumerated," and **both** new
  test files (handler unit test + integration test) must be appended. Confirmed.
- **L5 (test conventions to mirror).** `tests/test_broker_git_mcp_server.py`
  gives the house style: real temp git repo fixture (`git init` +
  `symbolic-ref HEAD refs/heads/main` + `config user.*` + initial commit),
  tool functions called directly (FastMCP `@mcp.tool()` returns a JSON string),
  parsed via `json.loads`, `_make_stubbed_run_git` for argv-scripted `_run_git`,
  `_clear_git_env` to normalise the opt-in toggles. The integration test reuses
  this fixture shape; the handler unit tests need NO git at all (pure string
  transformation). Confirmed by reading the test file.
- **L6 (no existing content-handler / dispatcher).** No `content_handlers`,
  `Handler`, `ProcessedResult`, `dispatch`, or registry exists anywhere under
  `src/gleipnir/` (this is a net-new library). Built fresh; nothing to reuse or
  collide with. Confirmed by search this session.
- **L7 (`broker/git/` component manifest unaffected).**
  `broker/git/pyproject.toml` declares `dependencies = ["mcp>=1.0,<2"]` and
  `dynamic=["version"]`. The new modules add **no** dependency (stdlib-only), so
  this manifest is **not** edited — a positive property confirming item 6.
  Confirmed by reading the manifest.

**Gate rule:** No hard Tier-3-ordering gate as in `broker-mcp.md` (no new
dependency, so no runtime-and-deps amendment is needed — L7). The only ordering
constraint is the standard test-first one (Assemble): tests precede
implementation; the `profiles.toml` amendment must land before the broker-profile
run of the integration test is expected to collect it.

---

## 4. Assemble — intended build order

Ordered so (i) tests precede implementation (Axiom 1 — the test is the arbiter),
(ii) the generic library lands before the handler that implements against it,
(iii) the call-site wiring lands after the library it calls, and (iv) the one
Tier-3 wiring edit (the `[profile.broker].test` amendment adding both new test
filenames) is sequenced explicitly.

**Step 1 — [code] Write FAILING tests first (test-first, Axiom 1).**
- `tests/test_broker_git_content_handlers.py` (stdlib-only, no `mcp`):
  - **Truncation rule (item 4):** below-`T` hunk passes through verbatim;
    above-`T` hunk keeps first/last `N` + exact `# ... (K lines truncated)`
    marker with correct `K`; multi-file diff preserves every file's
    `diff --git`/header/stat line; multi-hunk file truncates only oversized
    hunks; malformed/non-diff input returns unchanged (edge case 6).
  - **Boundary-value cases (explicit — guards the `>` vs `>=` off-by-one):**
    a hunk body of **exactly `T = 40`** body lines passes through **unchanged
    with no marker** (the comparison is strictly `>`, so `== T` is NOT
    truncated); a hunk body of **exactly `T + 1 = 41`** body lines **IS
    truncated** (keeps first 8 + `# ... (25 lines truncated)` + last 8). These
    two adjacent cases pin the comparison operator; see Stress-test T-1b/T-2b.
  - **Structural safety (item 5) — a type/structural test, not just
    behavioural:** assert `DiffHunkTruncationHandler.process`'s signature takes
    exactly one content parameter (a `str`) and returns `ProcessedResult`; assert
    the `Handler` protocol and `ProcessedResult` expose **no** attribute/parameter
    named for the envelope, `success`, a commit hash, or a verdict (introspect
    via `inspect.signature` / dataclass fields / protocol members). Plus a
    behavioural companion: a diff whose hunk body contains verdict/hash-shaped
    text is still treated only as hunk-body text.
  - **Extensibility (item 3) — the mandatory test:** register a trivial second
    stub handler matching a *different* `hint`; assert (a) `dispatch(content,
    stub_hint)` selects the stub, (b) `dispatch(diff, "diff")` still selects and
    correctly truncates via `DiffHunkTruncationHandler`, and (c) neither
    `content_handlers/registry.py` nor `diff_hunk_handler.py` was modified to make
    it pass (the stub is defined *in the test module*, proving registration is
    pure and external).
  - **No-handler fallback:** `dispatch` on an empty registry (or a non-matching
    hint) returns content unchanged (edge case 9).
- `tests/test_broker_git_diff_distill.py` (imports `mcp_server`; broker-profile):
  - Round-trip a **large fixture diff** through the real `git_diff` tool (real
    temp repo per L5 fixture, or a monkeypatched `_run_git` returning a large
    fixture `stdout`): assert the returned `"diff"` is truncated (contains the
    marker, is smaller than input), the `"success": True` envelope is intact,
    and the file/stat lines survive. A **small** diff round-trips unchanged.
- Add **only** `test_broker_git_diff_distill.py` (the `mcp`-importing
  integration test) to `tests/conftest.py` `collect_ignore` (so the lean
  `python` profile skips it when `mcp` is absent). Do NOT add
  `test_broker_git_content_handlers.py` — it is stdlib-only and is meant to run
  under the `python` profile. This is a code edit (under `tests/`).
- These MUST fail (modules absent) at authoring — that is the point.

**Step 2 — [code] Implement the generic library** `broker/git/content_handlers/`
(stdlib-only) to satisfy the protocol/registry/extensibility tests:
- `protocol.py`: `Handler` protocol (`can_handle(content, hint) -> bool`,
  `process(content) -> ProcessedResult`); `ProcessedResult` dataclass carrying
  `content: str` (and nothing that could reach an envelope — item 5 by
  construction).
- `registry.py`: module-level registry list; `register(handler)`;
  `dispatch(content, hint)` selecting the first registered handler whose
  `can_handle` returns True, else the unchanged-content fallback. **No
  handler-specific logic.**
- `__init__.py`: re-export `Handler`, `ProcessedResult`, `register`, `dispatch`.

**Step 3 — [code] Implement the ONE handler** `broker/git/diff_hunk_handler.py`
(stdlib-only) to satisfy the truncation tests:
- Module header docstring carries the `## Provenance` block **verbatim** (Trace
  §Provenance / item 7).
- `DiffHunkTruncationHandler` with `T = 40`, `N = 8` as named module constants;
  `can_handle(content, hint)` matches `hint == "diff"`; `process(content)` parses
  the unified diff into per-file sections and `@@` hunks, preserves all
  headers + stat lines verbatim, truncates each hunk body over `T` to first/last
  `N` + accurate `# ... (K lines truncated)` marker, fails safe (unchanged) on
  unparseable input.
- Does NOT register itself at import (keep the handler module free of dispatch
  concerns — SRP; registration is the caller's job, done in `mcp_server.py`).

**Step 4 — [code] Wire the call site** in `broker/git/mcp_server.py`:
- Import `register`, `dispatch` from `content_handlers` and
  `DiffHunkTruncationHandler` from `diff_hunk_handler`.
- Register the handler once at module level: `register(DiffHunkTruncationHandler())`.
- In `git_diff`, insert `processed = dispatch(result["stdout"], "diff")` before
  the success return and return `processed.content` as `"diff"` (Trace
  §call-site). Error path untouched.
- Update `broker/git/__init__.py` docstring to name the new modules.
- Run the Step-1 tests to green (handler unit tests under `python` profile).

**Step 5 — [Tier-3 / operator] Amend the broker test profile.** Add **BOTH**
new broker test filenames —
`"tests/test_broker_git_content_handlers.py"` AND
`"tests/test_broker_git_diff_distill.py"` — to
`.gleipnir/sandbox/profiles.toml` `[profile.broker].test`'s literal file list
(matching the existing convention that every broker test is enumerated there,
stdlib-only or not) so the broker profile collects both. Then run the
broker-profile suite (`bin/gleipnir-sandbox test`, broker profile) to green.

**Assemble step order (summary):**
`1 (code: FAILING tests first — handler unit + extensibility + structural +
integration + conftest collect-ignore) → 2 (code: generic content_handlers
library) → 3 (code: DiffHunkTruncationHandler + verbatim provenance) →
4 (code: mcp_server git_diff call-site wiring + __init__ docstring) →
5 (Tier-3 operator: profiles.toml [profile.broker].test amendment adding BOTH
new test filenames + broker-profile run)`

---

## 5. Stress-test — acceptance checks

Each is a concrete, checkable criterion (not "it works"). "unit" = stdlib-only,
runs under the default `python` profile (and, once listed in
`[profile.broker].test`, ALSO under the broker profile); "broker" = requires
`mcp`, runs only under the broker profile. Both new test files are listed in
`[profile.broker].test` per Decision 13 (spec-review-corrected).

- **T-1 (below-threshold pass-through) — unit.** A hunk body of ≤ 40 lines
  round-trips **byte-for-byte unchanged** through `process`; no marker inserted.
- **T-1b (lower boundary, exactly `T` — pass-through) — unit.** A hunk body of
  **exactly `T = 40`** body lines passes through **byte-for-byte unchanged with
  NO marker** (the trigger is strictly `> T`, so `body == 40` is not truncated).
  Pins the `>` (not `>=`) comparison at the boundary; an implementation using
  `>=` fails this test.
- **T-2 (above-threshold truncation) — unit.** A hunk body of, e.g., 100 lines
  returns first 8 + `# ... (84 lines truncated)` + last 8 body lines; the output
  hunk body is strictly smaller than the input; all file/`diff --git`/`@@`
  header and stat lines are preserved verbatim.
- **T-2b (upper boundary, exactly `T + 1 = 41` — truncation triggers) — unit.**
  A hunk body of **exactly `41`** body lines **IS truncated**: first 8 +
  `# ... (25 lines truncated)` + last 8 (`41 - 2·8 = 25`). Together with T-1b
  this pins the exact boundary (40 → unchanged, 41 → truncated), guarding the
  `>` vs `>=` off-by-one.
- **T-3 (`K` is exact) — unit.** For a body of `B > 40` lines, the marker reads
  exactly `# ... (B-16 lines truncated)`; an off-by-one fails the test.
- **T-4 (multi-file diff) — unit.** A diff with a small file A and a large file
  B keeps A verbatim, truncates only B's oversized hunk body, and preserves both
  files' stat summaries (`+N -M`) and headers.
- **T-5 (never silent-drop) — unit.** Any removal of body lines is accompanied
  by the marker; asserting the marker's presence whenever output body line count
  < input body line count (item 4: never silently drop).
- **T-6 (structural safety, type-level — item 5) — unit.** `inspect.signature`
  of `DiffHunkTruncationHandler.process` has exactly one non-self parameter
  annotated `str`; `ProcessedResult`'s fields are content-only; neither the
  `Handler` protocol nor `ProcessedResult` exposes any member named for
  `success`/envelope/hash/verdict. **Pass = the envelope is unreachable by
  construction, not by convention.**
- **T-6b (structural safety, behavioural companion) — unit.** A hunk body
  containing hash/verdict-shaped text is treated only as hunk-body text (never
  specially handled), confirming the handler has no concept of those fields.
- **T-7 (provenance verbatim — item 7) — doc/grep check.** The exact `##
  Provenance` fenced block appears in `diff_hunk_handler.py`'s module docstring,
  character-for-character (a `grep`/diff of the block against the brief's text);
  none of the Headroom trademarked names appears *as a claimed name of this
  module* (they appear only inside the attribution sentence that disclaims them).
- **T-8 (extensibility — item 3, MANDATORY) — unit.** Registering a second stub
  handler (different `hint`, defined in the test): (a) `dispatch` selects the
  stub for its hint, (b) the diff handler still truncates correctly for `"diff"`,
  (c) **no edit** to `registry.py` or `diff_hunk_handler.py` was needed —
  demonstrated by the stub living entirely in the test module. **This is the
  concrete proof a future handler registers cleanly.**
- **T-9 (no-handler fallback) — unit.** `dispatch(content, hint)` with an empty
  registry (or non-matching hint) returns `ProcessedResult(content=content)`
  unchanged.
- **T-10 (stdlib-only preserved — item 6) — meta-test (existing).** The existing
  `tests/test_broker_stdlib_only.py` part (ii) passes: the new
  `content_handlers/**` and `diff_hunk_handler.py` (not named `mcp_server.py`) do
  **not** import `mcp`; and part (i) still shows `mcp` has not leaked into the
  enforcement core. No new conformance test is added; the existing one is the
  arbiter (finding L2).
- **T-11 (no new MCP surface / no new dependency — item 2/6) — doc/grep check.**
  `gleipnir-git` still exposes exactly the four existing tools (no new
  `@mcp.tool()`), and `broker/git/pyproject.toml` is unchanged
  (`dependencies = ["mcp>=1.0,<2"]`, no addition). `git_diff`'s response envelope
  keys are unchanged (`{"success", "diff"}` / `{"success", "error"}`).
- **T-12 (integration round-trip) — broker.** Through the real `git_diff` tool: a
  large diff returns a truncated `"diff"` (marker present, smaller than input)
  inside an intact `{"success": True, ...}` envelope with file/stat lines
  surviving; a small diff round-trips unchanged; the error path
  (`success: False`) is untouched. Requires the Step-5 `profiles.toml`
  amendment to be collected.
- **T-13 (tier integrity) — authorship check.** No bounded `gleipnir-code` agent
  wrote any Tier-3 path. The **only** Tier-3 edit
  (`.gleipnir/sandbox/profiles.toml` `[profile.broker].test`, adding BOTH new
  broker test filenames — the handler unit test and the integration test) was an
  operator action (Step 5); all code and test writes were confined to
  `src/gleipnir/broker/git/**` and `tests/**` (both outside `.gleipnir/**`).

---

## 6. Execution Workflow

**For the orchestrator sequencing this plan.** ATLAS/GOTCHA already ran (this
plan). The pipeline from here: `spec-review → test → code → quality → git →
gate`, with the one Tier-3 operator edit (`profiles.toml`) sequenced at
Assemble Step 5 (before the broker-profile test run). This feature is **almost
entirely bounded `gleipnir-code`** — the sole Tier-3 action is the
`[profile.broker].test` file-list amendment, which adds **two** filenames (the
handler unit test AND the integration test) to the literal enumeration,
matching the existing convention that every broker test is listed there.

### Operator-vs-code-agent split (explicit)

| # | Task | Zone | Assemble step |
|---|---|---|---|
| 1 | Write failing tests (handler unit + extensibility + structural + integration) + `conftest.py collect_ignore` entry | bounded `gleipnir-code` (under `tests/`) | 1 |
| 2 | Implement `content_handlers/` generic library (protocol + registry) | bounded `gleipnir-code` (under `src/`) | 2 |
| 3 | Implement `diff_hunk_handler.py` (`T=40`/`N=8`, verbatim provenance) | bounded `gleipnir-code` (under `src/`) | 3 |
| 4 | Wire `git_diff` call site + `__init__.py` docstring | bounded `gleipnir-code` (under `src/`) | 4 |
| 5 | Amend `.gleipnir/sandbox/profiles.toml` `[profile.broker].test` to add BOTH new broker test filenames (handler unit test `test_broker_git_content_handlers.py` + integration test `test_broker_git_diff_distill.py`) | **Tier-3 / operator only** | 5 |

### Notes for the implementing agent

- **The test is the arbiter (Axiom 1).** Do not weaken a test to make code pass;
  the truncation rule, structural safety, and extensibility properties are the
  correctness contract. If a test seems wrong, escalate — do not edit it to
  green.
- **Verbatim provenance is non-negotiable (item 7 / T-7).** Copy the `##
  Provenance` block character-for-character into `diff_hunk_handler.py`'s module
  docstring. Do not paraphrase, reflow, or "improve" it.
- **stdlib-only (item 6 / T-10).** The new modules import Python stdlib only. Do
  not add any dependency to `broker/git/pyproject.toml`.
- **No new tool schema (item 2 / T-11).** Do not add an `@mcp.tool()`. The
  library is internal code `git_diff` calls; the `gleipnir-git` surface stays at
  four tools.
- **codegraph is out of scope (item 8).** Build only the generic library + the
  one diff handler. Do not add any AST/code handler or dependency-graph code,
  even speculatively. The extensibility test (T-8) is the *only* nod to future
  handlers.

---

## 7. Design Principles (cognition-layer Gate 1)

**Routing (case (i)).** `P` touches `src/gleipnir/broker/git/**` — executable
Python with real class/function/module structure (a `Handler` protocol, a
`ProcessedResult` dataclass, a registry, a handler class). Axis-1 `X` fires
(`src/**`) AND the touched members have OOP/functional structure → **Gate-1
case (i): full SOLID + DRY + SRP + Design Intent required, specific and
falsifiable.**

### Single Responsibility (the load-bearing falsifiable claim)

The single most important falsifiable claim for this plan — the whole point of
the plugin architecture:

- **The dispatcher (`content_handlers/registry.py`) knows NOTHING about diffs.**
  Its single responsibility is: given `(content, hint)`, select the first
  registered handler whose `can_handle` is True and return its
  `process(content)` result, else return content unchanged. It contains **no**
  reference to diffs, hunks, `@@`, `T`, `N`, truncation, or any handler class.
  **Falsifiable:** if `registry.py` contains the string `diff`, `hunk`, `@@`, a
  threshold constant, or an `import` of `diff_hunk_handler`, this claim is
  violated and the design is wrong.
- **The diff handler (`diff_hunk_handler.py`) knows NOTHING about dispatch.**
  Its single responsibility is: transform raw diff text per the item-4 rule. It
  contains **no** registry/selection logic and does **not** register itself.
  **Falsifiable:** if `diff_hunk_handler.py` imports the registry, iterates a
  handler list, or performs any handler-selection, this claim is violated.
- **`ProcessedResult` (`content_handlers/protocol.py`)** carries transformed
  content and nothing else. **Falsifiable:** if it grows a `success`/envelope/
  hash/verdict field, item-5 structural safety and its SRP are both violated.
- **`DiffHunkTruncationHandler.process`** has one reason to change: the diff
  truncation rule. **Falsifiable:** if it also assembles a response envelope or
  reads commit metadata, it has more than one responsibility and must be split.

### SOLID analysis (evaluated against the proposed design)

- **Single Responsibility** — as above: dispatcher = selection only; handler =
  transformation only; `ProcessedResult` = content carrier only. Each has
  exactly one reason to change.
- **Open/Closed** — the dispatcher is **open for extension** (register a new
  handler) and **closed for modification** (no dispatcher edit to add a handler);
  this is exactly the extensibility property T-8 proves. Adding the future
  codegraph-adjacent handler requires zero edits to existing code.
- **Liskov Substitution** — every registered handler is substitutable through
  the `Handler` protocol: the dispatcher depends only on `can_handle`/`process`,
  so any conforming handler (the diff handler, the test stub, a future handler)
  works identically in the dispatch loop. The stub-handler extensibility test is
  a direct Liskov check.
- **Interface Segregation** — the `Handler` protocol is minimal: exactly two
  methods (`can_handle`, `process`). No handler is forced to implement anything
  it does not need; there is no fat interface.
- **Dependency Inversion** — `mcp_server.py` (high-level policy: "shape
  `git_diff`'s output") depends on the **abstraction** (`dispatch` +
  the `Handler` protocol), not on `DiffHunkTruncationHandler` concretely for the
  dispatch mechanism (it only names the concrete class at the single
  registration site, which is the correct composition-root location). The
  dispatcher depends on the `Handler` abstraction, never on a concrete handler.

### DRY analysis

- The threshold `T` and keep-count `N` are **named module constants** in
  `diff_hunk_handler.py`, referenced by name — not repeated literals (avoids the
  "constant repeated without a named reference" smell).
- Diff-parsing logic lives in exactly one place (the handler); the dispatcher
  does not duplicate any parsing.
- The integration test reuses the **existing** `tests/test_broker_git_mcp_server.py`
  temp-repo fixture *shape* (per house convention, replicated not imported — the
  established broker-test pattern) rather than inventing a new one; handler unit
  tests need no git fixture at all (pure string transformation), avoiding
  unnecessary duplication of git setup.
- No new stdlib-only-conformance test is written — the existing
  `test_broker_stdlib_only.py` already covers the new modules (finding L2),
  avoiding a duplicate meta-test.

### Design Intent (specific, falsifiable — the genuineness proxy)

**Intent:** A future content handler (e.g. an AST-based code handler, and
further out a Gleipnir-native codegraph rebuild sharing this handler machinery)
can be added to `git_diff`'s output-shaping path by writing ONE new handler
module and ONE registration line, with **zero edits to
`content_handlers/registry.py` and zero edits to `diff_hunk_handler.py`** — AND
no handler can ever read or mutate the broker's response envelope, `success`
flag, commit metadata, or secret-scan verdict, because the `process(content:
str) -> ProcessedResult` signature structurally cannot reach them.

This is **falsifiable**, not a quality aspiration: it is violated if (a) adding
the extensibility-test stub required editing the dispatcher or the diff handler
(T-8 fails), OR (b) the dispatcher contains any diff-specific token (SRP claim
above), OR (c) `ProcessedResult`/`Handler`/`process` exposes any envelope/
verdict/hash/`success` member (T-6 fails). A reviewer can point to any of these
implementation choices and declare the intent violated — which is exactly what
the honour-check at the `quality` stage will do.
