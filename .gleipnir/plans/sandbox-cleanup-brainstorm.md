# Design Brief: Sandbox CLI cleanup — docstring + ISP regression test

## Problem Statement

Last session added a `--profile <name>` CLI flag to `bin/gleipnir-sandbox`
(threaded through `resolve_profile(profiles, name)` /
`_resolve_dispatch_profile(...)` in `src/gleipnir/sandbox/__main__.py`), giving
per-invocation profile selection over the config-driven `default_profile`.
Quality review passed but logged two Minor, non-blocking backlog notes:

1. **Stale module docstring.** The module-level docstring in
   `src/gleipnir/sandbox/__main__.py` (lines 1–36) documents config-driven
   dispatch, config-location fixity, the `config_root` test seam, and
   fail-closed behavior — but never mentions the new `--profile` override
   capability. Its dispatch narrative ("resolved to the `default_profile`, and
   dispatched") now reads as if the *only* resolution target is
   `default_profile`, which is incomplete.

2. **Missing ISP (Interface Segregation) regression test.** No test asserts
   that the `image-build` subparser does **not** gain a `--profile` option.
   `build_parser()` was verified correct by direct read (lines 258–266:
   `image-build` registers only `--image`, never `--profile`), but nothing
   guards against a future accidental addition broadening `image-build`'s
   interface. The other `--profile` tests for `test`/`lint` live in
   `tests/test_sandbox_cli.py` (lines 331–519).

This is mechanical cleanup: no runtime behavior changes, no new capability, no
enforcement surface touched.

## Constraints

- **Read-only exploration already done; no code changed in this stage.**
- **In-repo precedent must be followed, not reinvented.** The negative-flag
  assertion pattern already exists twice in `tests/test_sandbox_cli.py`:
  `test_lint_subparser_has_no_image_flag` (115–120) and
  `test_test_subparser_namespace_has_no_image_attribute` (123–134). New tests
  should match that style and rationale-docstring convention.
- **Structural fact that makes the test sound:** `image-build`'s subparser has
  **no `argparse.REMAINDER` positional** (unlike `test`, which has
  `pytest_args`). Therefore an unrecognized `--profile` is a *genuine* argparse
  parse error → `SystemExit(2)`, not a token silently swallowed into a
  positional. This is the exact reasoning the `lint`/`--image` precedent test
  documents, and it applies identically here.
- **Blast-radius routing:** touched paths are `src/gleipnir/sandbox/__main__.py`
  (docstring only) and `tests/test_sandbox_cli.py` — both in disqualifier set
  `X` (`src/**`, `tests/**`), so this plan runs the **full 8-stage pipeline**
  (test-first), not the prose/config light path. Correct: the test is a real
  executable artifact and IS the correctness arbiter.
- **Docstring change must not overstate.** The override changes *which* profile
  resolves; it does **not** weaken the config-location fixity, the
  agent-unwritable Tier-3 guarantee, or the "image comes solely from the
  resolved profile" invariant. Wording must preserve those.

## Approaches Considered

The two items are independent; each is documented, then the one genuine (but
non-material) fork — the ISP test's assertion mechanism — is analysed below.

### Item 1 — Docstring update

### Approach A1: Minimal targeted sentence (recommended)

**Summary:** Add one sentence to the existing config-driven-dispatch paragraph
(around lines 16–19) noting that `test`/`lint` accept an optional `--profile
<name>` that overrides the config's `default_profile` for that one invocation,
while every other invariant (fixed config location, image-from-profile,
fail-closed) is unchanged.

**Tradeoffs:**
- Pro: Smallest diff; slots into the paragraph that already explains resolution.
- Pro: Preserves the docstring's existing structure and tone.
- Pro: Cannot overstate — it is scoped to the one behavior that changed.
- Con: Reader must already be reading that paragraph to find it.

**Estimated Scope:** 1 file (`__main__.py`), ~1–2 lines, complexity low.

**Risk:** low — prose only; the full pipeline's test stage is unaffected by
docstring text.

### Approach A2: Dedicated docstring paragraph

**Summary:** Add a short standalone paragraph titled to call out the
`--profile` override explicitly, parallel to the existing "Config-driven
dispatch" paragraph.

**Tradeoffs:**
- Pro: Higher visibility for the new flag.
- Con: Larger diff; risks duplicating resolution wording already present.
- Con: Slight redundancy with the argparse `help=` strings (which already
  document the flag at lines 238–243 / 254).

**Estimated Scope:** 1 file, ~4–6 lines, complexity low.

**Risk:** low.

### Item 2 — ISP regression test (the genuine fork)

### Approach B1: `SystemExit`-on-flag assertion (matches `lint`/`--image` precedent) (recommended)

**Summary:** Add a test asserting
`pytest.raises(SystemExit)` when `build_parser().parse_args(["image-build",
"--profile", "whatever"])` is called — a byte-for-byte parallel to
`test_lint_subparser_has_no_image_flag`.

**Tradeoffs:**
- Pro: Exact in-repo precedent (`lint`/`--image`), including the "no REMAINDER
  → real parse error" rationale, which transfers verbatim.
- Pro: Tests the *actual observable contract* an accidental broadening would
  break (a user/agent passing `--profile` to `image-build` must be rejected).
- Pro: Robust to argparse-internal representation changes.
- Con: `SystemExit` alone does not, by itself, distinguish "flag absent" from
  some *other* parse error — mitigated by the parse being otherwise valid
  (`image-build` alone parses fine), so the only variable is the flag.

**Estimated Scope:** 1 file (`tests/test_sandbox_cli.py`), 1 test (~8 lines),
complexity low.

**Risk:** low.

### Approach B2: Namespace-attribute absence assertion

**Summary:** Parse `["image-build"]` and assert `not hasattr(args, "profile")`.

**Tradeoffs:**
- Pro: Directly asserts the namespace shape (no `profile` attribute).
- Con: Weaker guard — an accidental `--profile` added with `default=None` would
  still leave `hasattr(args, "profile")` **True** even when the flag is not
  passed, so this alone would NOT catch the exact regression it targets. It
  proves the default namespace shape, not that the flag is unaccepted.

**Estimated Scope:** 1 file, 1 test, complexity low.

**Risk:** medium — can pass while the interface is silently broadened.

### Approach B3: Dual assertion (attribute-absence + SystemExit-on-flag) — matches `test`/`--image` precedent

**Summary:** Combine B2 and B1 in one test, mirroring
`test_test_subparser_namespace_has_no_image_attribute` (lines 123–134):
`assert not hasattr(args, "profile")` on a bare `image-build` parse, **plus**
`pytest.raises(SystemExit)` when `--profile` is passed.

**Tradeoffs:**
- Pro: Strongest guard — proves both the clean namespace shape AND that the
  flag is actively rejected (closes B2's gap via B1's half).
- Pro: Mirrors the closest existing precedent for a subcommand that (like
  `image-build`) carries its own distinct flag surface.
- Con: Marginally larger than B1 alone.

**Estimated Scope:** 1 file, 1 test (~10 lines), complexity low.

**Risk:** low.

## Decision Analysis

**This is surfaced per the task's instruction to flag any genuine fork — but it
is explicitly NOT a material tradeoff requiring operator convergence.** It is a
trivial, cheaply-reversible test-authoring choice with a clear precedent-driven
answer.

**Framework used:** Reversibility Filter (the catalog's mandated first step),
then Pros-Cons-Fixes as the A/B(/C) follow-up — per the auto-selection table
for a binary/multi-option choice that the filter fast-tracks.

**Analysis results:**

```
Reversibility: Two-Way Door
Reversal cost: The assertion mechanism of one test in one file. Changing it
  later is a few lines, no data loss, no external commitment, no API lock-in,
  no downstream dependency. Cheapest possible reversal class.
Recommendation: Fast-track
Next framework: Pros-Cons-Fixes (below), no deeper analysis warranted
```

```
Option B1 (SystemExit-on-flag):
  Pros: exact lint/--image precedent; tests the observable contract; robust.
  Cons and Fixes:
    | Con | Fix |
    | SystemExit alone is not flag-specific | image-build parses cleanly on its
      own, so the flag is the only variable — non-issue in practice |
  Post-fix verdict: Viable (recommended, or as the core of B3)

Option B2 (attribute-absence only):
  Pros: directly asserts namespace shape.
  Cons and Fixes:
    | Con | Fix |
    | Misses the regression if flag added with default=None | Add the
      SystemExit half — which turns B2 into B3 |
  Post-fix verdict: Not viable standalone (its fix IS Approach B3)

Option B3 (dual: attribute-absence + SystemExit):
  Pros: strongest; mirrors the closest precedent (test/--image, a subcommand
    with its own flag surface); closes B2's gap.
  Cons and Fixes:
    | Con | Fix |
    | Slightly larger than B1 | Negligible; ~2 extra lines |
  Post-fix verdict: Viable (strongest guard)
```

**Bias warnings:**
- ⚠️ *Status Quo Bias (mild, checked and dismissed):* the recommendation leans
  on the in-repo precedent. Applying equal scrutiny: the precedent is followed
  because it is *correct and directly applicable* (same "no REMAINDER → real
  parse error" structural fact), not merely because it exists — so the lean is
  justified, not a free pass.
- No other detectors triggered. (Docstring Approach A1 vs A2 is a pure
  prose-verbosity preference with no tradeoff worth a framework — Reversibility
  Filter fast-tracks it as a Two-Way Door; A1 recommended for minimal diff.)

**Recommendation:** **Approach B3** for the ISP test (dual assertion) — it is
the strongest guard, mirrors the closest existing precedent
(`test_test_subparser_namespace_has_no_image_attribute`, the subcommand-with-
own-flags case that `image-build` matches), and closes the gap that makes B2
unsound standalone. B1 alone is an acceptable lighter alternative. For the
docstring, **Approach A1** (minimal targeted sentence).

## Selected Approach

**Choice:** Item 1 → **Approach A1** (minimal targeted docstring sentence);
Item 2 → **Approach B3** (dual attribute-absence + SystemExit-on-flag ISP test).

**Rationale:** Both are the precedent-aligned, lowest-risk options for a
mechanical cleanup. The ISP-test fork was surfaced (B1/B2/B3) and analysed, but
is a Two-Way Door test-authoring choice — fast-tracked, **no material tradeoff
and no operator convergence required.** B3 is chosen over B1 because it exactly
mirrors the closest in-repo precedent (a subcommand carrying its own distinct
flag surface, as `image-build` does with `--image`) and is strictly a stronger
guard for negligible extra cost; B2 is rejected standalone as unsound.

### Exact docstring wording change (Item 1, Approach A1)

In the "Config-driven dispatch" paragraph (currently ending ~line 19 with
"…never *what command* runs."), append a sentence of this shape (final wording
to be applied at the code stage; content fixed here):

> Both `test` and `lint` additionally accept an optional `--profile <name>`
> that selects a specific configured profile for that one invocation,
> overriding the config's `default_profile`; omitting it (or passing no
> `--profile`) resolves `default_profile` exactly as before. `--profile` only
> chooses *among the profiles the Tier-3 config already defines* — an unknown
> name fails closed (exit 3) via the existing `resolve_profile` path, and it
> does not affect the fixed config location, the image-from-resolved-profile
> rule, or any fail-closed behavior. `image-build` does **not** accept
> `--profile`.

The final clause deliberately documents the very invariant Item 2's test
guards, keeping the docstring and the regression test mutually reinforcing.

### Exact ISP test approach (Item 2, Approach B3)

- **File:** `tests/test_sandbox_cli.py`, in the `--profile` selector block
  (after the existing parser tests around lines 331–374, i.e. alongside
  `test_profile_flag_parses_before_remainder_and_stripping_still_works` and
  `test_bare_test_lint_namespace_has_profile_attribute_defaulting_to_none`).
- **Test name:** `test_image_build_subparser_has_no_profile_flag`
  (parallels the existing `test_lint_subparser_has_no_image_flag` /
  `test_test_subparser_namespace_has_no_image_attribute` naming).
- **Assertion mechanism (dual):**
  1. `args = cli.build_parser().parse_args(["image-build"])` then
     `assert not hasattr(args, "profile")` — proves the clean `image-build`
     namespace carries no `profile` attribute (interface not broadened at rest).
  2. `with pytest.raises(SystemExit): cli.build_parser().parse_args(
     ["image-build", "--profile", "whatever"])` — proves the flag is actively
     **rejected**, not silently tolerated.
- **Why it correctly proves absence:** `image-build`'s subparser has **no
  `argparse.REMAINDER` positional** (contrast `test`'s `pytest_args` at line
  245). With no REMAINDER to absorb it, an unrecognized `--profile` is a real
  argparse error → `SystemExit(2)` — it cannot be swallowed as a positional.
  This is the identical structural reasoning the existing
  `test_lint_subparser_has_no_image_flag` docstring relies on (lines 116–118),
  transferred to `image-build`/`--profile`. The attribute-absence half
  additionally rules out the `default=None`-broadening regression that a
  SystemExit-only test would miss (the exact gap that makes Approach B2 unsound
  standalone). The test docstring should cite this "no REMAINDER → real parse
  error" fact explicitly, matching the precedent's convention.

## Open Questions

- None material. Final exact prose of the docstring sentence and the test
  docstring is applied at the code stage from the fixed content above; neither
  is a design decision.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Docstring (Item 1, A1) | `src/gleipnir/sandbox/__main__.py` — module docstring only (lines 1–36 region) |
| ISP regression test (Item 2, B3) | `tests/test_sandbox_cli.py` — one new test in the `--profile` selector block |
| Pipeline routing | Full 8-stage (test-first): both paths are in disqualifier set `X` (`src/**`, `tests/**`); NOT the prose/config light path |
| Untouched (must stay so) | `build_parser()` logic, `resolve_profile`, profiles config, all runtime/fail-closed paths |
