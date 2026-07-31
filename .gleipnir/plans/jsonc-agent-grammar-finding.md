# Plan: Surface a malformed opencode.jsonc `agent:` block as a GRAMMAR/FAIL finding

**Source brief:** `.gleipnir/plans/jsonc-agent-grammar-finding-brainstorm.md`
(operator-converged: Approach A + FAIL severity).
**Stage owner for implementation:** `gleipnir-code` (this is a code change in
`src/gleipnir/preflight/config_scan.py` + tests — **NOT** a Tier-3 / substrate
/ guard edit; no `.gleipnir/agents|skills|goals|decisions|keys` touched).
**Tier:** this plan is a Tier-0 session artifact; the change it plans lands in
`src/` and `tests/`.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Approach for surfacing a malformed jsonc `agent:` block | **A — extend the existing GRAMMAR check** to the jsonc source; emit `FindingCheck.GRAMMAR` with `where="agent"` / `where="agent.<name>"` | B (new enum member), C (reuse an unrelated member e.g. `OVER_RESTRICTION`), D (status quo / silent-ignore) | **OPERATOR-CONVERGED** (brief §"Material sub-decisions" #1; matrix 349 > 294/217/190). Preserves frontmatter↔jsonc symmetry, no shipped-enum churn, minimal surface, reversible into B later |
| 2 | Severity of the new finding | **FAIL** | WARN | **OPERATOR-CONVERGED** (brief §#2). Mirrors the frontmatter non-dict `tools:`/`permission:` precedent (`config_scan.py:613,656,670`); a `FAIL` forces not-`CLOSED` → `REFUSE` by default (`decide_config:1096-1099`), honouring fail-closed |
| 3 | Enum member name | **N/A — no new member** (`FindingCheck.GRAMMAR` reused) | `JSONC_GRAMMAR` / `MALFORMED_AGENT_BLOCK` | **OPERATOR-CONVERGED as a consequence of #1** (brief §#3 applies "only if Approach B"). Enum stays as declared at `config_scan.py:549-555` |
| 4 | Emission mechanism: dedicated helper vs inline | **Dedicated helper** `check_jsonc_agent_grammar(jsonc_agent_block: object) -> list[Finding]` near `check_grammar` (~line 583); called from `config_scan_main` | Inlining two `Finding(...)` emissions at the coercion sites (1266, 1276) | **PLAN-LEVEL** (brief Open Q a, non-material). A helper is unit-testable in isolation (symmetric with `check_grammar`), keeps `config_scan_main` readable, and makes the emit-before-coerce ordering explicit at one call site. Cost is a few extra lines — proportionate |
| 5 | `where`/`detail` wording | Top-level: `where="agent"`; per-agent: `where="agent.<name>"`. `detail` names the **opencode.jsonc** source + expected **map** shape, mirroring the frontmatter detail phrasing | Blank/terse detail; omitting the source name | **PLAN-LEVEL** (brief Open Q b). Diagnostic-quality constraint: `where`/`detail` "never left blank" (`config_scan.py:565-573`). Exact strings fixed in Trace below so tests can assert substrings |
| 6 | Per-agent malformation carries the agent name | **Yes** — `where=f"agent.{name}"` | Flat `where="agent"` for per-agent cases | **PLAN-LEVEL** (brief Open Q d; brief recommended "yes"). Precise locator; distinguishes which agent's block is malformed |
| 7 | Test placement | **Both**: symmetric unit tests in `tests/test_config_scan_grammar.py` (against the new helper), AND an end-to-end assertion in `tests/test_config_scan_cli.py` (malformed jsonc `agent:` → exit 1 / REFUSE) | Only one of the two | **PLAN-LEVEL** (brief Open Q c). Unit tests pin the helper's `where`/`detail`/severity contract; the e2e test proves the finding flows through `decide_config` to a not-`CLOSED` verdict — the thing the fail-closed hole is actually about |
| 8 | Ordering vs the shipped crash-safety coercion (981623b) | **Emit-before-coerce**: call `check_jsonc_agent_grammar` on the raw `jsonc.get("agent", {})` value **before** the `if not isinstance(...): jsonc_agent_block = {}` coercion, and on each raw per-agent `block` **before** its `block = {}` coercion. **Do NOT remove the coercions** | Emit after coercion (finding lost — value already `{}`); or replace the coercion with the finding (re-opens the crash) | **PLAN-LEVEL, CRITICAL** (task requirement). The finding must be *reported* AND the pipeline must stay *crash-safe*. See Trace §Ordering for exact placement |

No new material tradeoff was discovered during planning (see Stress-test
§"Material-decision check"). All eight rows are either operator-converged
(#1–3) or non-material plan/implementation detail (#4–8).

---

## Architect

**Problem (one sentence):** `config_scan_main` silently coerces a
structurally-malformed opencode.jsonc `agent:` block (non-dict top-level, or a
non-dict per-agent block) to `{}` and emits **no** operator-facing finding, so
the fail-closed preflight can print `CLOSED` while the operator's per-agent tool
scoping has been dropped.

**User:** the operator running the config-scoping preflight, who relies on it to
never report `CLOSED` on a malformed/unsafe config.

**Measurable success criteria:**
1. A non-dict top-level `agent:` value emits exactly one
   `Finding(check=GRAMMAR, severity=FAIL, where="agent", detail=<names jsonc + map>)`.
2. Each non-dict per-agent block (when `agent:` *is* a dict) emits exactly one
   `Finding(check=GRAMMAR, severity=FAIL, where="agent.<name>", detail=<names jsonc + map>)`.
3. A well-formed `agent:` block (dict-of-dicts, or absent) yields zero new
   findings.
4. `decide_config` returns not-`CLOSED` (→ `REFUSE`, exit 1) for each malformed
   variant by default; `--override-ack` escalates to `PROCEED_UNCLOSED` (exit 2),
   never to `CLOSED`/exit 0.
5. The existing crash-safety coercion still holds: no malformed variant raises
   an uncaught exception out of `config_scan_main` (the
   `TestNonDictAgentBlockNeverRaises` guarantees remain green).
6. The `FindingCheck` enum is unchanged (no new member).

**Constraints:**
- Fail-closed philosophy; diagnostic-quality (`where`/`detail` never blank).
- Enum-shape stability: reuse `GRAMMAR`, add no member.
- Proportionate token/complexity cost (framework goal G-4d).
- **Must not remove** the shipped crash-safety coercion (commit 981623b).
- Test-first: tests written before implementation.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Status |
|---|---|---|
| Implementation | `src/gleipnir/preflight/config_scan.py` | EXISTS — edit `config_scan_main` (~1264–1284) + add helper near `check_grammar` (~583) |
| Unit tests | `tests/test_config_scan_grammar.py` | EXISTS — append a new test class |
| End-to-end tests | `tests/test_config_scan_cli.py` | EXISTS — strengthen/extend `TestNonDictAgentBlockNeverRaises` (or add a sibling class) |
| Enum | `FindingCheck` (`config_scan.py:549-555`) | EXISTS — **unchanged** |

**Verified against disk this session:** the coercion sites are at
`config_scan.py:1264-1284` (top-level `agent:` coercion at 1266–1273;
per-agent block coercion at 1276–1283). The frontmatter non-dict precedent is
`check_grammar` at lines 609–621 (`permission`), 652–663 (`tools`).
`decide_config`'s FAIL→not-CLOSED logic is at 1096–1099. The existing
crash-safety-only tests are `TestNonDictAgentBlockNeverRaises`
(`test_config_scan_cli.py:359-433`), which currently assert only
`isinstance(exit_code, int)`.

### The new helper (contract to implement)

```python
def check_jsonc_agent_grammar(jsonc_agent_block: object) -> list[Finding]:
    """Check the opencode.jsonc top-level `agent:` block shape, symmetric
    with check_grammar's frontmatter non-dict handling. Emits a
    GRAMMAR/FAIL Finding for a non-dict top-level `agent:` value
    (where="agent"), and one per non-dict per-agent block
    (where="agent.<name>"). A well-formed dict-of-dicts (or the default {})
    yields []. Never raises."""
```

Behaviour:
- If `jsonc_agent_block` is **not** a `dict`: return a single
  `Finding(GRAMMAR, FAIL, where="agent", detail=DETAIL_TOP)`.
- Else, iterate `.items()`; for each `name, block` where `block` is **not** a
  `dict`, append `Finding(GRAMMAR, FAIL, where=f"agent.{name}", detail=DETAIL_PER)`.
  A well-typed block contributes nothing.

### Exact `where`/`detail` wording (fixed here so tests can assert)

- `DETAIL_TOP` (top-level non-dict `agent:`):
  `"non-map value under opencode.jsonc agent: where a map of agent-name -> per-agent config block is expected"`
- `DETAIL_PER` (per-agent non-dict block):
  `"non-map value under opencode.jsonc agent.<name> where a per-agent config map is expected"`
  (implemented with the literal agent name substituted, e.g.
  `... agent.foo where a per-agent config map is expected`).

Both name the **opencode.jsonc** source and the **map** shape, mirroring the
frontmatter detail style (`"non-map value under tools: where a map of ... is
expected"`). Tests assert substrings — see Stress-test — so minor wording
polish by `gleipnir-code` is fine **as long as** the asserted substrings
(`"opencode.jsonc"`, `"agent"`, `"map"`) remain present and detail is non-blank.

### Ordering vs the crash-safety coercion (CRITICAL — emit-before-coerce)

Current code (1264–1284) — annotated with the required insertion points:

```python
jsonc_top_level_tools = jsonc.get("tools")
jsonc_agent_block = jsonc.get("agent", {})
# >>> INSERT #1: emit BEFORE the top-level coercion, on the RAW value.
findings.extend(check_jsonc_agent_grammar(jsonc_agent_block))
if not isinstance(jsonc_agent_block, dict):
    # crash-safety coercion — UNCHANGED, still runs.
    jsonc_agent_block = {}
jsonc_agent_overrides = {}
for name, block in jsonc_agent_block.items():
    # NOTE: per-agent non-dict findings are ALREADY emitted by the helper
    # above (it iterates the raw block once); do NOT re-emit here.
    if not isinstance(block, dict):
        # crash-safety coercion — UNCHANGED, still runs.
        block = {}
    jsonc_agent_overrides[name] = block.get("tools", {})
```

**Key ordering guarantees:**
1. `check_jsonc_agent_grammar` runs on the **raw** `jsonc.get("agent", {})`
   value *before* any `{}` coercion, so it sees (and reports) the malformation.
2. Because the helper iterates the raw block's `.items()` itself for the
   per-agent case, the finding emission for per-agent blocks happens **before**
   the coercion loop — the single `findings.extend(...)` call at INSERT #1
   covers **both** the top-level and per-agent cases in one place. No emission
   is added inside the coercion loop (avoids double-emit).
3. Both `if not isinstance(...): ... = {}` coercions are **retained verbatim** —
   crash-safety is untouched. When `agent:` is a non-dict, the helper returns
   the top-level finding and the coercion makes `.items()` safe (empty). When a
   per-agent block is a non-dict, the helper already recorded it and the loop's
   coercion keeps `block.get(...)` safe.

Rationale for helper-iterates-once (vs emitting per-agent findings inside the
existing loop): keeps *all* grammar-emission logic in the helper (mirrors
`check_grammar` owning all frontmatter grammar), and keeps the coercion loop
purely defensive. The helper safely handles a non-dict top-level value (returns
before iterating) so it never raises.

### Integrations map

- `config_scan_main` → `check_jsonc_agent_grammar` (new call) → `findings` list
  → `decide_config` (existing FAIL→not-CLOSED path) → exit code.
- No change to `enumerate_effective_tools`, `assert_single_holders`,
  `check_fail_open`, `check_global_disable`, `find_mis_scoped_denies`,
  `decide_config`, or `FindingCheck`.

### Edge cases

- `agent:` **absent** → `jsonc.get("agent", {})` returns `{}` (a dict) → helper
  returns `[]`. No finding. ✓ (Correct: absence is not a malformation.)
- `agent:` present as `null`/`true`/`1`/`1.5`/`"str"`/`[]` → non-dict →
  one top-level `where="agent"` finding. ✓
- `agent:` a dict with a mix of good and bad per-agent blocks → one finding per
  bad block, keyed `agent.<name>`; good blocks contribute nothing. ✓
- `agent:` a dict whose per-agent block is a valid dict but missing `tools:` →
  no finding (existing `block.get("tools", {})` behaviour unchanged). ✓
- Multiple bad per-agent blocks → multiple findings (not first-wins), symmetric
  with `check_grammar`'s multi-finding behaviour. ✓
- `bool` is an `int` subclass, but here we test `isinstance(x, dict)`, so
  `True`/`1`/`1.5` all correctly count as non-dict. ✓

---

## Link (validated before building)

- **Coercion sites confirmed** at `config_scan.py:1264-1284` (read this session).
- **Frontmatter precedent confirmed**: non-dict `tools:`/`permission:` →
  `GRAMMAR`/`FAIL` (`check_grammar`, 609–663).
- **Severity mechanics confirmed**: `decide_config:1096-1099` — a `FAIL` sets
  `all_closed = False` → `REFUSE` (or `PROCEED_UNCLOSED` under `override_ack`).
- **Enum confirmed**: `FindingCheck.GRAMMAR` exists (line 550); reuse, no member.
- **Existing crash-safety tests confirmed**: `TestNonDictAgentBlockNeverRaises`
  (`test_config_scan_cli.py:359-433`) assert only `isinstance(exit_code, int)`;
  our new e2e assertions (`exit_code == 1`) strengthen without contradicting them.
- **Test fixture pattern confirmed**: `_write_clean_fixture(config_root,
  jsonc_agent_value)` writes `{"mcp": {}, "agent": <value>}` to `opencode.jsonc`
  and a clean agent `.md`; reusable for the e2e assertions.
- **`Finding` fields confirmed** (`config_scan.py:570-573`): `check`, `severity`,
  `where`, `detail`.

---

## Assemble (build order — test-first)

1. **Write unit tests** in `tests/test_config_scan_grammar.py` (new class
   `TestJsoncAgentBlockGrammar`) against `cs.check_jsonc_agent_grammar(...)`:
   - non-dict top-level values (`True`, `1`, `1.5`, `"x"`, `[]`, `None`) each →
     exactly one finding, `check is GRAMMAR`, `severity is FAIL`,
     `where == "agent"`, `"opencode.jsonc" in detail`, `"map" in detail.lower()`,
     detail non-blank.
   - dict with one non-dict per-agent block (e.g. `{"foo": True}`) → one finding,
     `where == "agent.foo"`, `check/severity` as above, detail names
     `opencode.jsonc`/`map`.
   - dict with multiple bad blocks (`{"foo": True, "bar": [1]}`) → two findings,
     `{f.where for f} == {"agent.foo", "agent.bar"}`.
   - dict with a mix (`{"good": {"tools": {}}, "bad": 1}`) → exactly one finding,
     `where == "agent.bad"`.
   - well-formed (`{}`, `{"foo": {"tools": {}}}`) → `[]`.
   - never-raises loop over the non-dict value set (mirrors
     `test_non_dict_tools_never_raises_even_though_it_is_flagged`).
2. **Write end-to-end tests** in `tests/test_config_scan_cli.py`: add a class
   `TestMalformedJsoncAgentBlockRefuses` (sibling to
   `TestNonDictAgentBlockNeverRaises`, reusing its `_write_clean_fixture` shape):
   - top-level `agent:` as `[]`, `"str"`, `true`, `1`, `null` → `exit_code == 1`
     (REFUSE) — not merely `isinstance(int)`.
   - per-agent block non-dict (`{"clean-agent": true}`) → `exit_code == 1`.
   - `--override-ack` on a malformed top-level `agent:` → `exit_code == 2`
     (PROCEED_UNCLOSED), asserting `!= 0`.
   - **Do NOT delete** the existing `TestNonDictAgentBlockNeverRaises` tests —
     they remain valid crash-safety regressions.
3. **Run the new tests → confirm they FAIL** (helper does not yet exist / no
   finding emitted / exit is 0 today for some variants). This proves the tests
   bite.
4. **Implement `check_jsonc_agent_grammar`** near `check_grammar` (~line 583),
   per the contract in Trace.
5. **Wire it into `config_scan_main`** at INSERT #1 (emit-before-coerce), keeping
   both crash-safety coercions verbatim; add the "already emitted; do not
   re-emit" comment in the loop.
6. **Update the two stale in-code comments** at 1270–1273 and 1280–1283 (which
   say "no grammar Finding is emitted ... not yet surfaced to the operator") to
   reflect that the finding is now emitted by `check_jsonc_agent_grammar` before
   coercion, and the coercion remains for crash-safety only.
7. **Run the full test suite → all green.**

---

## Stress-test (acceptance checks — RUNNABLE)

Run from repo root `/Users/jasonh/git/gleipnir`. (Verify the test module is
discoverable first; adjust the runner invocation to the project's convention if
`pytest` is fronted by a wrapper.)

1. **New unit tests pass:**
   ```
   pytest tests/test_config_scan_grammar.py -k JsoncAgentBlockGrammar -v
   ```
   Expect: all `TestJsoncAgentBlockGrammar` cases pass.

2. **New e2e REFUSE tests pass:**
   ```
   pytest tests/test_config_scan_cli.py -k MalformedJsoncAgentBlockRefuses -v
   ```
   Expect: every malformed-variant case returns exit 1 (or 2 under
   `--override-ack`), never 0.

3. **Existing crash-safety regressions still pass (no regression):**
   ```
   pytest tests/test_config_scan_cli.py -k NonDictAgentBlockNeverRaises -v
   ```
   Expect: all green — the coercions were not removed.

4. **Full config_scan suite green:**
   ```
   pytest tests/test_config_scan_grammar.py tests/test_config_scan_cli.py tests/test_config_scan_decide.py -v
   ```

5. **Enum unchanged (no new member):**
   ```
   grep -n "GRAMMAR\|SINGLE_HOLDER\|FAIL_OPEN\|OVER_RESTRICTION\|GLOBAL_DISABLE\|MIS_SCOPED_GLOB" src/gleipnir/preflight/config_scan.py
   ```
   Expect: the `FindingCheck` block (lines ~549–555) shows the same six members,
   no additions.

6. **Emit-before-coerce ordering present in source** (the helper call precedes
   the coercion — verified by line ordering, not just presence):
   ```
   grep -n "check_jsonc_agent_grammar\|jsonc_agent_block = {}\|jsonc.get(\"agent\"" src/gleipnir/preflight/config_scan.py
   ```
   Expect: the `check_jsonc_agent_grammar(...)` call line number is **greater
   than** the `jsonc.get("agent"` assignment and **less than** the
   `jsonc_agent_block = {}` coercion line number.

7. **Coercions retained** (crash-safety intact):
   ```
   grep -n "jsonc_agent_block = {}" src/gleipnir/preflight/config_scan.py
   grep -n "block = {}" src/gleipnir/preflight/config_scan.py
   ```
   Expect: both coercion lines still present.

8. **Stale "not yet surfaced" comment removed/updated:**
   ```
   grep -rn "not yet surfaced to the operator" src/gleipnir/preflight/config_scan.py
   ```
   Expect: **zero** matches after implementation (the comment described the gap
   this change closes).

9. **Live-repo smoke (real `.gleipnir/` + real `opencode.jsonc`) still CLOSED
   or its prior verdict — no accidental new finding on the real config:**
   ```
   pytest tests/test_config_scan_cli.py -k live -v
   ```
   Expect: the existing live-repo smoke tests keep their prior verdict (the real
   `opencode.jsonc` `agent:` block is a well-formed dict-of-dicts, so the helper
   contributes zero findings on it).

**Material-decision check (planner self-audit):** I looked for any *new*
material tradeoff (a choice with lasting/hard-to-reverse consequences, or a
tradeoff between genuinely viable approaches not already converged). The helper
-vs-inline, wording, test-placement, agent-name-in-`where`, and emit-order calls
are all reversible, low-blast-radius implementation details explicitly delegated
by the brief as non-material. The two material axes (approach, severity) were
operator-converged. **No new material decision surfaced.**

---

## Execution Workflow (for `gleipnir-code`)

1. This is a **code** stage change; implement in `src/gleipnir/preflight/config_scan.py`
   and `tests/`. No `.gleipnir/` policy files are touched. No git/broker action
   is part of this stage (that is the later `git` stage, `git-ops`).
2. **Test-first, strictly:** complete Assemble steps 1–3 (write and run the new
   tests, confirm they FAIL) *before* writing any implementation. The failing
   tests are the arbiter of correctness.
3. Implement the helper (Assemble 4), wire it emit-before-coerce (Assemble 5),
   update the stale comments (Assemble 6).
4. Assert `where`/`detail` via **substring** checks (`"opencode.jsonc"`,
   `"agent"`, `"map"`, non-blank) — not exact-string equality on `detail` — so
   wording polish does not create brittle tests. `where` **is** asserted exactly
   (`"agent"`, `"agent.<name>"`).
5. Do **not** add a `FindingCheck` member; do **not** remove either crash-safety
   coercion.
6. Run the full Stress-test command list; all must pass before handing back.
7. If, while implementing, a genuinely new material tradeoff appears (e.g. the
   real `opencode.jsonc` turns out to contain a shape the helper would falsely
   flag, forcing a semantics choice), **stop and surface it** to the
   orchestrator for operator convergence rather than deciding it inline.
