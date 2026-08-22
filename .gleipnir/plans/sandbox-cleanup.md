# Plan: Sandbox CLI cleanup — module docstring + ISP regression test

**Stage:** `plan` (authored by `gleipnir-plan` from the converged brief).
**Source brief:** `.gleipnir/plans/sandbox-cleanup-brainstorm.md` (converged;
Item 1 → Approach A1, Item 2 → Approach B3). This plan does NOT re-decide
anything the brief fixed — it plans the bounded work the brief defines.

## Pipeline routing (blast-radius classification)

**`P` (touched-path set) = { `src/gleipnir/sandbox/__main__.py`,
`tests/test_sandbox_cli.py` }.**

Both members are in the Axis-1 **disqualifier set `X`** (`src/**` and
`tests/**` respectively). Per `../stage-role-map.md` Axis-1: *any* path in `P`
matching `X` disqualifies the prose/config light path — the plan runs the
**FULL 8-stage pipeline** (`brainstorm → plan → spec-review → test → code →
quality → git → gate`), test-first. This is correct on the merits: the new
test in `tests/test_sandbox_cli.py` is a real executable artifact and IS the
correctness arbiter for Item 2. **NOT the prose/config light path.** No further
Axis-2 routing question arises (Axis 2 only applies to track-eligible plans;
this plan is disqualified at Axis 1).

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Docstring change shape (Item 1) | A1 — minimal targeted sentence(s) appended to the existing "Config-driven dispatch" paragraph | A2 — dedicated standalone paragraph | Brief-converged. Smallest diff; scoped to the one behavior that changed; cannot overstate; preserves docstring structure. (Brief §Selected Approach) |
| 2 | ISP test assertion mechanism (Item 2) | B3 — dual assertion (attribute-absence + `SystemExit`-on-flag) | B1 (SystemExit-only), B2 (attribute-absence-only, unsound standalone) | Brief-converged. Strongest guard; mirrors the closest in-repo precedent (`test_test_subparser_namespace_has_no_image_attribute`, a subcommand carrying its own flag surface, as `image-build` does with `--image`); closes B2's `default=None` gap. Two-Way-Door, fast-tracked, NOT a material tradeoff — no operator convergence owed. (Brief §Decision Analysis) |
| 3 | Assemble order for a purely-additive regression test | Author Item-2 test FIRST; it PASSES against current correct code (proving the ISP invariant already holds); Item-1 docstring is the only source edit | Treat as classic red→green (write a failing test, then change code to pass) | The ISP invariant already holds in `build_parser()` (lines 258–266 register only `--image`); the test is a *regression guard*, not a spec for new behavior. There is no code change that makes it go green — it is green now and must stay green. This asymmetry is stated explicitly per the task. (Planning decision) |
| 4 | Test insertion location | In the `--profile` selector block, after line 374 (`test_bare_test_lint_namespace_has_profile_attribute_defaulting_to_none`) | The `image-build` block near line 137 | Brief §Exact ISP test approach places it alongside the `--profile` parser tests; it is a `--profile`-surface assertion. Confirmed the block spans 331–374 on disk. |
| 5 | Gate-1 Design-Principles case | Case (i) — SOLID+DRY+SRP + Design Intent | Case (ii) executable-non-OOP; case (iii) prose/config-only | `P ∩ X ≠ ∅` AND both touched `X`-members have function/module structure (`__main__.py` is a module of functions; the test file is a module of test functions). The routing key is "does the touched X-member have class/function/module structure?" — yes. See §Design Principles. |

## Architect

**Problem (one sentence):** Close two Minor non-blocking backlog notes from the
`--profile` review — a stale module docstring that omits the new `--profile`
override, and a missing Interface-Segregation regression test asserting
`image-build` does not gain `--profile` — without changing any runtime behavior.

**User:** A future reader/maintainer of `src/gleipnir/sandbox/__main__.py`
(who should learn the `--profile` override from the module docstring without
reading `build_parser()`), and the test suite as a regression tripwire against
a future accidental broadening of `image-build`'s CLI surface.

**Measurable success criteria:**
1. The module docstring's config-driven-dispatch narrative documents: the
   `--profile <name>` override for `test`/`lint`; the fallback-to-
   `default_profile` when omitted; fail-closed-on-unknown-name (exit 3 via
   `resolve_profile`); and the explicit statement that `image-build` does NOT
   accept `--profile`.
2. A new test `test_image_build_subparser_has_no_profile_flag` exists in
   `tests/test_sandbox_cli.py`, dual-asserting (a) no `profile` attribute on the
   parsed `image-build` namespace and (b) `SystemExit` when `--profile` is
   passed to `image-build`.
3. The new test **passes against current unmodified `build_parser()`** (it
   guards an invariant that already holds).
4. The full existing sandbox-CLI suite still passes (no regression).
5. No change to `build_parser()` logic, `resolve_profile`,
   `_resolve_dispatch_profile`, profiles config, or any runtime/fail-closed path.

**Constraints (from brief, carried verbatim in intent):**
- Docstring must NOT overstate: `--profile` changes *which* profile resolves; it
  does not weaken config-location fixity, the Tier-3 agent-unwritable guarantee,
  or the image-from-resolved-profile invariant. Wording must preserve those.
- In-repo precedent must be followed, not reinvented: the new test mirrors
  `test_test_subparser_namespace_has_no_image_attribute` (lines 123–134) and its
  "no REMAINDER → real parse error" rationale-docstring convention.
- Structural fact making the test sound: `image-build`'s subparser has no
  `argparse.REMAINDER` positional, so an unrecognized `--profile` is a genuine
  argparse parse error → `SystemExit`, not a token swallowed into a positional.

## Trace

**Artifacts and where they live (source of truth):**

| Artifact | File | Line region (verified on disk) | Change |
|---|---|---|---|
| Module docstring | `src/gleipnir/sandbox/__main__.py` | Config-driven-dispatch paragraph, lines 11–21 (ends "…on this dispatch path." at line 21) | Append sentence(s) per Item-1 exact wording below |
| ISP regression test | `tests/test_sandbox_cli.py` | New function after line 374, inside the `--profile` selector block (starts line 331) | Add `test_image_build_subparser_has_no_profile_flag` |

**Note on a brief line-reference correction (L-C15 diligence):** the brief says
to append to the paragraph "currently ending ~line 19 with '…never *what
command* runs.'" On disk that phrase is at **line 19 mid-paragraph**; the
config-driven-dispatch paragraph actually runs lines **11–21** and ends at line
21 with "…there is no `--image` flag and no `SANDBOX_IMAGE` constant read on
this dispatch path." The append target is the **end of that paragraph (after
line 21)**, keeping the new sentence in the same paragraph that explains
resolution — the brief's intent (A1: "slots into the paragraph that already
explains resolution") is honored; only the exact end-line is corrected. This is
a factual correction, not a design change.

**Integrations map:**
- `resolve_profile(profiles, name)` / `_resolve_dispatch_profile(...)` — the
  fail-closed-on-unknown-name path (exit 3) the docstring references. No code
  change; referenced by name in prose only.
- `build_parser()` (lines 228–268) — `image-build` subparser (258–266) registers
  only `--image`; `test`/`lint` (232–256) register `--profile`. The test asserts
  against this existing structure; **no edit.**
- Existing precedent tests: `test_lint_subparser_has_no_image_flag` (115–120),
  `test_test_subparser_namespace_has_no_image_attribute` (123–134) — the new
  test parallels the latter's dual-assertion shape and rationale docstring.

**Edge cases:**
- `parse_args(["image-build"])` must succeed cleanly (it does — `image-build`
  parses on its own), so the ONLY variable in the `SystemExit` half is the
  `--profile` flag — this is what makes the `SystemExit` assertion flag-specific
  in practice (mitigates B1's noted con).
- `hasattr(args, "profile")` on the bare `image-build` namespace must be
  **False** — `image-build` never registers `--profile`, so no attribute is set.
  This rules out the `default=None`-broadening regression a SystemExit-only test
  would miss.
- The docstring append must not introduce a claim the code does not honor (e.g.
  must not imply `image-build` *could* take `--profile`) — the final clause
  states it does NOT, reinforcing Item 2's test.

## Link (validated before building)

- **Files exist and line regions confirmed** by direct read this session:
  `src/gleipnir/sandbox/__main__.py` (281 lines; docstring 1–36, dispatch
  paragraph 11–21, `build_parser` 228–268, `image-build` subparser 258–266) and
  `tests/test_sandbox_cli.py` (684 lines; precedent tests 115–134, `--profile`
  selector block 331–374).
- **Invariant already holds:** `image-build` (258–266) registers only `--image`,
  never `--profile` — so the Item-2 test will pass against current code
  (confirmed by read, not assumption).
- **Precedent shape confirmed:** `test_test_subparser_namespace_has_no_image_attribute`
  (123–134) is the exact dual-assertion template (`assert not hasattr(...)` +
  `pytest.raises(SystemExit)` with a rationale docstring). The new test copies
  its structure, substituting `image-build`/`profile` for `test`/`image`.
- **Tooling:** tests run in the S-2 sandbox via `bin/gleipnir-sandbox test`
  (config-driven; the `code`/`test` stages run against the ephemeral container,
  not the host). No new dependency, no new fixture, no import beyond what the
  test module already imports (`cli`, `pytest`).

## Assemble (intended build order)

**One-line summary:** write the additive ISP regression test FIRST (it passes
green against current code, proving the invariant already holds), then apply the
single docstring source edit; run the full suite to confirm no regression.

1. **[test stage] Write the ISP regression test** in `tests/test_sandbox_cli.py`
   after line 374 (end of the `--profile` selector block), following the
   `test_test_subparser_namespace_has_no_image_attribute` template. **Asymmetry
   note (explicit, per task):** unlike the neighboring `--profile` selector
   tests — which were authored test-first as *failing* specs for a
   not-yet-built flag (see the block header, lines 322–328) — THIS test guards
   an invariant that **already holds**, so it **passes immediately against
   current unmodified code**. There is no red→green transition and no code
   change makes it green: it is green now and must remain green as a regression
   tripwire. Run it in isolation to confirm it passes green (not errors, not
   xfails).
2. **[code stage] Apply the single docstring edit** in
   `src/gleipnir/sandbox/__main__.py` — append the Item-1 wording (below) to the
   end of the config-driven-dispatch paragraph (after line 21). This is the ONLY
   source edit in the whole plan. No `build_parser()` / runtime / config change.
3. **[code stage] Run the full sandbox-CLI suite** (`bin/gleipnir-sandbox test`
   selectors for `tests/test_sandbox_cli.py`, or the full suite) — confirm the
   new test passes and no existing test regressed. Docstring text does not
   affect any test, so step 2 cannot break step 1; this run confirms the
   additive test integrates cleanly.

## Exact wording to apply

### Item 1 — docstring append (source of truth for `gleipnir-code`)

Append the following to the **end of the config-driven-dispatch paragraph**
(after the current line 21 "…on this dispatch path."), as continuation prose in
that same paragraph. This is the brief's fixed content (§"Exact docstring
wording change"), lightly finalized; apply it verbatim:

> Both `test` and `lint` additionally accept an optional `--profile <name>`
> that selects a specific configured profile for that one invocation,
> overriding the config's `default_profile`; omitting `--profile` resolves
> `default_profile` exactly as before. `--profile` only chooses *among the
> profiles the Tier-3 config already defines* — an unknown name fails closed
> (exit 3) via the existing `resolve_profile` path — and it does not affect the
> fixed config location, the image-from-resolved-profile rule, or any
> fail-closed behavior. `image-build` does **not** accept `--profile`.

(The final clause deliberately documents the very invariant Item 2's test
guards, keeping docstring and regression test mutually reinforcing — brief
§Selected Approach.)

### Item 2 — ISP regression test (source of truth for `gleipnir-code`)

Add this function after line 374, matching the in-repo style
(`test_test_subparser_namespace_has_no_image_attribute`). Final exact wording of
the rationale docstring is applied at the code stage; the content and both
assertions are fixed here:

```python
def test_image_build_subparser_has_no_profile_flag():
    """`--profile` is a `test`/`lint` dispatch-selector only; `image-build`
    must NOT gain it (ISP: `image-build` carries its own distinct flag
    surface — `--image` — and its interface must not silently broaden to the
    `--profile` capability the dispatch verbs have). A bare `image-build`
    parse carries no `profile` attribute, and `--profile` is actively
    rejected: `image-build` has no `argparse.REMAINDER` positional (contrast
    `test`'s `pytest_args`), so an unrecognized `--profile` is a real parse
    error (SystemExit), not a token swallowed as a positional — the same
    "no REMAINDER -> real parse error" reasoning as
    `test_lint_subparser_has_no_image_flag`. The attribute-absence half also
    rules out a `default=None`-broadening regression a SystemExit-only test
    would miss."""
    args = cli.build_parser().parse_args(["image-build"])
    assert not hasattr(args, "profile")
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["image-build", "--profile", "whatever"])
```

## Stress-test (acceptance checks)

Concrete, checkable — the `quality` and `gate` stages validate against these:

1. `test_image_build_subparser_has_no_profile_flag` exists in
   `tests/test_sandbox_cli.py`, located within the `--profile` selector block
   (after line 374 as authored).
2. The test contains BOTH assertions: (a) `assert not hasattr(args, "profile")`
   on a `parse_args(["image-build"])` namespace, and (b)
   `pytest.raises(SystemExit)` around `parse_args(["image-build", "--profile",
   "whatever"])`. A single-assertion form is a non-conformance (B3, not B1/B2).
3. The test **passes** (green) against the current unmodified `build_parser()` —
   NOT errored, NOT xfail. (Verifiable: run the single test node; expect PASS.)
4. The module docstring in `src/gleipnir/sandbox/__main__.py` now contains, in
   the config-driven-dispatch paragraph: the `--profile <name>` override; the
   `default_profile` fallback-when-omitted; fail-closed-on-unknown-name (exit 3
   via `resolve_profile`); and the explicit "`image-build` does not accept
   `--profile`" clause. (Verifiable: `grep` for `--profile`, `resolve_profile`,
   `default_profile`, and `image-build` within the docstring region.)
5. The docstring does NOT weaken or contradict the existing invariants
   (config-location fixity, Tier-3 agent-unwritability, image-from-resolved-
   profile). (Verifiable: those sentences remain present and unaltered; the
   append only adds, never edits, prior claims.)
6. `git diff` touches EXACTLY two files (`src/gleipnir/sandbox/__main__.py`,
   `tests/test_sandbox_cli.py`), with `__main__.py` changes confined to the
   docstring (no change to any `def`, `add_argument`, or `set_defaults` line).
   (Verifiable: `git diff --stat` = 2 files; `git diff src/...` shows only
   docstring lines.)
7. The full existing `tests/test_sandbox_cli.py` suite passes (no regression).

## Design Principles (Gate 1 — cognition, design-time)

**Case applied: (i) OOP/functional code plan.** Justification: `P ∩ X ≠ ∅`
(both touched paths are in `X`), AND both touched `X`-members have
class/function/module structure — `__main__.py` is a module of functions
(`build_parser`, `main`, `_cmd_*`, `resolve_profile`), and `test_sandbox_cli.py`
is a module of test functions. The routing sub-question ("does the touched
`X`-member have class/function/module structure?") is answered **yes**, so
case (i) applies: full SOLID + DRY + SRP + Design Intent. (Not case (ii): these
are function-bearing Python modules, not a Makefile/CI-YAML/shell script. Not
case (iii): there IS an executable artifact.)

**SOLID analysis (against the proposed change):**
- **Single Responsibility:** The new test function has exactly one reason to
  change — the `image-build` `--profile`-absence contract. The docstring append
  has one reason to change — the documented `--profile` override surface. Each
  edit is single-purpose.
- **Open/Closed:** The change is purely additive — a new test function and
  appended docstring prose. No existing function, subparser, or test is modified;
  the test module is extended without editing existing tests. Satisfied.
- **Liskov Substitution:** No subclass/implementation hierarchy is introduced or
  altered; not exercised by this change (no inheritance touched).
- **Interface Segregation (the load-bearing principle here):** This is the exact
  principle the change *defends*. `image-build`'s CLI interface is deliberately
  narrower than `test`/`lint`'s — it exposes `--image` and specifically NOT the
  `--profile` dispatch-selector. The new test is the regression tripwire that
  keeps that interface segregated: it fails loudly if a future edit widens
  `image-build` to accept `--profile`. The plan adds an ISP guard; it does not
  violate ISP.
- **Dependency Inversion:** No dependency direction is introduced or changed; the
  test depends only on the already-imported `cli.build_parser` public surface,
  exactly as its precedent neighbors do. Not exercised.

**DRY analysis:** The test reuses the established in-repo pattern rather than
reinventing a new assertion idiom — it mirrors
`test_test_subparser_namespace_has_no_image_attribute` (the dual
attribute-absence + `SystemExit` shape) and `test_lint_subparser_has_no_image_flag`
(the "no REMAINDER → real parse error" rationale). No new helper is needed; the
`cli`/`pytest` imports and `build_parser()` entry point are already present. The
docstring append references the existing `resolve_profile` path by name rather
than re-explaining fail-closed logic already documented elsewhere in the module.
No logic or constant is duplicated.

**Single Responsibility (named, per new component):**
- `test_image_build_subparser_has_no_profile_flag` — single responsibility:
  assert `image-build`'s parser interface neither carries nor accepts
  `--profile`. Nothing else.
- Docstring append — single responsibility: document the `--profile` override
  surface (and `image-build`'s exclusion from it) in the module's own docs.

**Design Intent (specific, falsifiable — the genuineness proxy):**

Two named, falsifiable intents this change must honor:

1. **ISP boundary (Item 2):** *`image-build`'s CLI interface must remain
   segregated from the `test`/`lint` dispatch surface — specifically, it must
   NOT silently grow the `--profile` capability that `test`/`lint` carry.* This
   is falsifiable: an implementation that registered `--profile` on
   `image-build`'s subparser (making `hasattr(args, "profile")` True on a bare
   parse, or making `parse_args(["image-build", "--profile", "x"])` succeed)
   would VIOLATE it, and the new test would catch that violation. A reviewer can
   point to a concrete code change (`p_image_build.add_argument("--profile", ...)`)
   that breaks this intent.
2. **Docs-CLI synchronization (Item 1):** *The module docstring must stay
   synchronized with the module's public CLI surface — a reader must be able to
   learn that `--profile` overrides `default_profile` for `test`/`lint` (and that
   `image-build` is excluded) from the docstring alone, without reading
   `build_parser()`.* This is falsifiable: a docstring that still described only
   `default_profile` resolution (omitting the `--profile` override), or that
   claimed `image-build` accepts `--profile`, would VIOLATE it. A reviewer can
   check the docstring text against the actual `add_argument` calls and point to
   the specific missing/wrong sentence.

Neither intent is a generic quality aspiration ("clean", "correct"); each names a
concrete boundary (ISP: no `--profile` on `image-build`) or constraint
(docs-CLI sync: the docstring must state the override and the exclusion) that a
specific implementation choice could be shown to violate.

## Execution Workflow

For the implementing agents (`gleipnir-code` at test + code stages, then
`quality-reviewer`, `git-ops`, `orchestrator`-gate):

1. **test stage (`gleipnir-code`):** Add the Item-2 test function verbatim from
   §"Exact wording to apply / Item 2" after line 374 of
   `tests/test_sandbox_cli.py`. Run just that test node in the S-2 sandbox
   (`bin/gleipnir-sandbox test`) and confirm it **PASSES** green against current
   unmodified code (this is the additive-regression asymmetry — no red phase).
   If it does NOT pass green, STOP: the invariant the brief asserts (that
   `image-build` lacks `--profile`) does not hold as believed — escalate before
   any source edit.
2. **code stage (`gleipnir-code`):** Apply the Item-1 docstring append verbatim
   from §"Exact wording to apply / Item 1" to the end of the config-driven-
   dispatch paragraph (after line 21) of `src/gleipnir/sandbox/__main__.py`.
   Touch ONLY docstring lines — no `def`/`add_argument`/`set_defaults`. Then run
   the full `tests/test_sandbox_cli.py` suite in the sandbox; confirm all pass.
3. **quality stage (`quality-reviewer`):** Verify all seven Stress-test
   acceptance checks; run the Gate-2 honour check (does the applied change honor
   the two stated Design Intents — ISP boundary preserved, docstring synchronized
   with the CLI surface?). Confirm `git diff --stat` shows exactly two files and
   `__main__.py`'s diff is docstring-only.
4. **git stage (`git-ops`):** Commit the two-file change.
5. **gate (`orchestrator`):** Read attestation; emit pipeline state.

**Escalation:** No material tradeoff is open in this plan — the brief converged
both items and the ISP-test fork is an explicitly non-material Two-Way-Door
choice. If the implementing agent discovers the ISP invariant does NOT already
hold (step 1 test fails green), that is a factual surprise, not a design
tradeoff, and should be reported to the operator/orchestrator before proceeding.

## Open Questions

None material. Final exact prose of the docstring sentence and the test
rationale docstring is applied at the code stage from the fixed content above;
neither is a design decision (brief §Open Questions).
