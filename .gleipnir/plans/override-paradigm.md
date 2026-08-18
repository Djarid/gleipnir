# Plan: Override Paradigm — DEFAULT-uncaged, OPT-IN caged (implementation)

> **Stage:** `plan` (ATLAS Architect/Trace/Link/Assemble/Stress-test).
> **Plans FROM:** `.gleipnir/plans/override-paradigm-brainstorm.md` — CONVERGED
> (orchestrator-routed operator decision). D1–D5 are **operator-converged
> inheritances**; this plan does **NOT** re-decide them, it plans HOW to
> implement them.
> **Author:** `gleipnir-plan`. **Tier-0, disposable.**

---

## Routing header — HARDENED-path self-classification

**This plan runs the HARDENED review path.** Self-classified against
`../stage-role-map.md`:

- **Axis-1 eligibility gate:** the touched-path set `P` (see below) contains
  `src/gleipnir/preflight/**` — a member of the disqualifier set `X`
  (`src/**`). **A code member is present ⇒ this plan is NOT prose/config-track
  eligible; it runs the full 8-stage pipeline.** (Eligibility for the
  prose/config track requires `P ∩ X = ∅`; here `P ∩ X ≠ ∅`.)
- **Axis-2 (moot, but recorded):** even setting Axis-1 aside, `P` also matches
  Axis-2(a) enforcement paths — `.gleipnir/decisions/**`, `.gleipnir/AGENTS.md`
  — and Axis-2(b) content (verdict/label/exit-code semantics that gate launch).
  Every independent axis routes hardened.

**Touched-path set `P` (what the plan's outputs, once applied, will change):**

| Path | Class | Who applies |
|---|---|---|
| `src/gleipnir/preflight/boundary.py` | code (`X`; deny for `gleipnir-code`) | operator only (converged P3; no grant path) |
| `src/gleipnir/preflight/__main__.py` | code (`X`; deny for `gleipnir-code`) | operator only (converged P3; no grant path) |
| `tests/test_preflight_*.py` (new/extended) | code (`X`; **NOT** in preflight deny) | `gleipnir-code` (test-first) OR operator |
| `.gleipnir/decisions/operating-posture.md` (new) | Tier-3 POLICY | **operator only** |
| `.gleipnir/decisions/s2-g1-closure.md` (banner) | Tier-3 POLICY | **operator only** |
| `.gleipnir/decisions/substrate-design-pass.md` (banner) | Tier-3 POLICY | **operator only** |
| `.gleipnir/decisions/gleipnir-layout-and-memory-model.md` (banner) | Tier-3 POLICY | **operator only** |
| `.gleipnir/AGENTS.md` (trust-tier/guard framing) | Tier-3 POLICY | **operator only** |
| `.gleipnir/keys/marker.key` (mode/perms, no content) | Tier-3 OS act (`chmod 600`) | **operator only** |
| `.gleipnir/plans/s2-activation.md` (Tier-0 framing note) | Tier-0 | roster writer OR operator |

**Two non-fusing review rubrics are REQUIRED** at review (the hardened-path
contract, `../stage-role-map.md`):

1. **SPEC-CONFORM pass** (rubric = this plan + the converged brief):
   `SPEC-CONFORM: PASS/FAIL`. Includes the Gate-2 intent-quality sub-check
   (the Design Intent below is specific/falsifiable, not vacuous).
2. **BLAST-RADIUS / false-success pass** (rubric = *how could this be wrongly
   green?*): adversarial. Includes the Gate-2 SOLID/DRY dimension (case (i),
   below) at Important severity, and — at the `quality` stage — the honour
   check (does the applied code honour the stated Design Intent?).

**Negative-check attestation is REQUIRED** — one row per grant/enforcement
change, `attested_by ≠ author`, each with a concrete reproducible artifact
(`grep`/`diff`/quote) captured against the **applied / post-change** file, the
`over_broad_form_checked` matching the evidence pattern in the **same file**
named in `grant`, and a `[D]`/`[J]` basis tag. A schema-complete-but-vague or
wrong-file/wrong-pattern attestation is a spec-review non-conformance. The
attestation skeleton is provided in the Stress-test section; the reviewer (not
the author) fills the evidence.

---

## Decisions (index)

All five (D1–D5) are **operator-converged inheritances** from the brief's
"Selected Approach (Converge)" (provenance: orchestrator-routed operator
decision via the precept-10 gate). This plan carries them unchanged and plans
their implementation; it does not re-open them.

**Convergence note (P1/P2/P3 — operator-converged after the plan was drafted).**
Three plan-stage items were subsequently converged by the operator and are now
recorded as resolved inheritances, NOT open choices: **P1** — `requested_mode`
is threaded through but NEVER participates in the `all_closed`/`CLOSED`
computation (the anti-false-assurance safety invariant); **P2** — the
uncaged-default not-closed case returns **exit 0** (legitimate launch success);
**P3** — the operator applies the `src/` code diffs directly, with **no grant
path** for this change (the former apply-path B — a temporary `preflight/**`
grant — is foreclosed and removed throughout this plan). These are not
re-decided here.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| **D1** | Mode-selection mechanism | Launch-path substance (caged = the S-2 activation OS acts, reusing the existing fail-closed preflight path) **+ a thin optional preflight-bound selector**: requesting `caged` without a `CLOSED` verdict **REFUSES** | opencode permission profiles alone; an unbound flag | Operator-converged (brief D1). Lowest new build; the selector's binding to `CLOSED` is the load-bearing obligation — a caged claim without the OS acts must never proceed (no false assurance). |
| **D2** | Granularity / floor | `keys/marker.key` stays `chmod 600` owner-only **even in uncaged default**; uncaged is NOT all-or-nothing; default posture labelled **"uncaged (key-protected floor)"** | Global all-or-nothing (key writable/readable in default) | Operator-converged (brief D2). Key compromise is silent/cross-session and defeats G-3 evidence; the floor is one `chmod`. |
| **D3** | Superseding record + authorship | New **operator-authored** `decisions/operating-posture.md` + supersession banners on `s2-g1-closure.md`, `substrate-design-pass.md`, `gleipnir-layout-and-memory-model.md`, and `AGENTS.md` framing | In-place thesis rewrites; agent-authored Tier-3 edits | Operator-converged (brief D3/D5). Operator explicitly kept Tier-3 authorship even though default-uncaged would technically permit an agent write — honored. |
| **D4** | Honesty labelling | **Conditional relabel:** uncaged-default → neutral, legitimate, **non-failing** label + informational reasons; retain the "NOT closed (dev-mode)" deficiency language ONLY for an explicitly-requested caged run that did not reach `CLOSED` | Blanket-keep the current `"G-1 NOT closed (dev-mode)"` framing for the default | Operator-converged (brief D4). Preserves the honesty invariant exactly where it matters (a *requested* cage that didn't hold) while ending the "default = broken" mis-frame. Label lives in `boundary.py`/`__main__.py` (deny for `gleipnir-code`). |
| **D5** | Threat-model envelope | Envelope (*session access = full operator authority AND no untrusted content in context*) + three opt-in-caged triggers as **REQUIREMENTS** (unattended/autonomous, untrusted-content ingestion, higher-assurance/hosted/multi-agent), recorded in `operating-posture.md` | Blanket-safety assertion with no stated envelope | Operator-converged (brief D5). An unstated envelope is the actual risk. |
| **P1** | mechanism binding D4+D1 in code — **OPERATOR-CONVERGED** | Thread an explicit **`requested_mode` enum (`UNCAGED`/`CAGED`)** into `decide()`/`run_preflight()`/CLI; the mode selects **label framing + exit-code interpretation only**, and **NEVER participates in the `all_closed`/`CLOSED` computation** (closure stays gated solely on real probe evidence) | Reusing/overloading `override_ack` as the mode signal; a free-standing mode string trusted independent of the verdict; the mode influencing closure | **Operator-converged (P1).** Consistent with D1's "must be bound to the verdict" and D4's "conditional on intended mode". The never-influences-`CLOSED` clause is the load-bearing safety invariant (anti-false-assurance). No longer open. |
| **P2** | uncaged-default not-closed exit code — **OPERATOR-CONVERGED** | The uncaged-default not-closed case returns **exit 0** (legitimate launch-OK posture), distinct from `REFUSE` (1) and the `--override-ack` escalation (2) | A distinct new non-failing exit code (e.g. `3`) | **Operator-converged (P2).** Uncaged default is a legitimate "go" state, so the launch wrapper treats it as success. No longer open. |
| **P3** | who applies the `src/` code diffs — **OPERATOR-CONVERGED** | **Operator applies** the `boundary.py`/`__main__.py` diffs directly; **no grant path exists** for this change | A narrow temporary grant letting a code stage edit `src/gleipnir/preflight/**` (the former apply-path B) | **Operator-converged (P3).** `gleipnir-code` denies `src/gleipnir/preflight/**`; P3 forecloses any temporary grant. Apply-path B is retired everywhere in this plan. No longer open. |

---

## Architect

**Problem (one sentence).** Make Gleipnir's *default* operating posture uncaged
(the trusted single-principal terminal) while keeping the S-2 cage as a
deliberate opt-in, by (a) relabelling the preflight so the uncaged default is a
legitimate non-failing state, (b) adding a preflight-verdict-**bound** optional
mode selector that refuses a caged request lacking a `CLOSED` verdict, (c)
keeping the G-3 key OS-protected even in the default, and (d) recording the new
thesis + threat envelope in an operator-authored Tier-3 record with supersession
banners on the records the change contradicts.

**User.** The operator at the terminal (runs the out-of-framework preflight and
chooses the launch posture). NOT an in-framework agent — the preflight is
deliberately not agent-reachable (`__main__.py` docstring; `bin/gleipnir-preflight`
comment).

**Measurable success criteria** (full checkable list in Stress-test):
- A default (uncaged) preflight run reports a **neutral, non-failing** label and
  exit code (not the "NOT closed (dev-mode)" deficiency framing).
- An **explicitly-requested caged** run that does **not** reach `CLOSED`
  **REFUSES** (distinct non-zero exit) and retains the deficiency language.
- There is **no code path** by which the mode selector produces `CLOSED` —
  `CLOSED` remains gated solely on real probe evidence + present key.
- `keys/marker.key` is mode `600` owner-only, verifiable in the default posture.
- `decisions/operating-posture.md` exists (operator-applied) stating the thesis,
  the two-condition envelope, and the three opt-in triggers as REQUIREMENTS; the
  four superseded records carry banners pointing to it.

**Constraints** (inherited from the brief + verified against code):
- **Enforcement core is stdlib-only** (`decisions/runtime-and-deps.md`) — the
  selector/relabel add no dependency (they are `enum` + `argparse`, both stdlib,
  already used in `boundary.py`/`__main__.py`).
- **True OS-level caging cannot be toggled by the agent** — the selector is
  *intent + launch-gate* only; `CLOSED` still requires the operator's OS acts
  (verified: `decide()` reaches `CLOSED` only via `all_closed` from real probes,
  `boundary.py:555-558`; there is no `override_ack→CLOSED` path, `:530-533`).
- **The preflight is out-of-framework, operator-run, fail-closed** — the mode
  selector is added to the SAME out-of-framework CLI (`__main__.py`), NOT routed
  into any agent allowlist. It must not become agent-reachable.
- **Honesty invariant is non-negotiable** — relabelling changes *how the state
  is framed*, never whether the operator knows the state; the reasons list is
  retained (informational) in the uncaged case.
- **`gleipnir-code` DENIES `src/gleipnir/preflight/**`** (verified
  `.gleipnir/agents/gleipnir-code.md:16`) — the `boundary.py`/`__main__.py`
  edits are **operator-applied** (converged P3; no grant path exists for this
  change). See the who-applies split in Assemble.

**Explicitly NOT in scope.** Repealing G-2..G-6; changing the enforcement-path
*set* (`ENFORCEMENT_PATHS`); the probe/fork/drop-verify machinery (B1); the
`config-scan`/`bridge-*` subcommands; the operator's built-in escape-hatch
agents. This plan touches label framing, one new mode input, the key `chmod`,
and Tier-3 prose — nothing in the probe decision logic.

---

## Trace

### Artifacts and where they live (source of truth)

1. **D4 conditional relabel + P1 mode input — `src/gleipnir/preflight/boundary.py`.**
   - Source of truth for the label constant: `DEV_MODE_LABEL` (`boundary.py:506`,
     verified `= "G-1 NOT closed (dev-mode)"`).
   - `decide()` (`:516-563`) is the pure aggregator. Today it takes
     `override_ack: bool`; it has **no notion of intended mode**. The plan
     threads a **`requested_mode`** input (an `enum` — `Posture`-style, e.g.
     `RequestedMode.UNCAGED | RequestedMode.CAGED`, default `UNCAGED`).
   - **The load-bearing invariant (do not weaken):** `requested_mode` influences
     ONLY the returned `label` and (via the CLI) the exit-code *interpretation*.
     It MUST NOT enter the `all_closed` computation. Concretely: the `if
     all_closed:` branch (`:555`) is unchanged; only the **not-closed** branches
     (`:559-563`) gain mode-conditional labels:
       - `requested_mode == UNCAGED` (default) → a **new neutral label**
         (proposed constant `UNCAGED_DEFAULT_LABEL = "uncaged (key-protected
         floor) — default operator-trust posture"`) + reasons retained as
         *informational*; the top-level result is a **non-failing** posture
         (see the CLI exit-code mapping below).
       - `requested_mode == CAGED` and not closed → **retain** `DEV_MODE_LABEL`
         semantics / the `REFUSE` deficiency label; the operator asked for the
         wall and did not get it — that stays loud.
   - **Key-floor sub-verdict (D2 residual, brief Open-Questions):** the uncaged
     label names the key-protected floor. Whether to surface a *distinct*
     key-floor sub-verdict line is a **presentation detail**, resolved here as:
     include an informational reason confirming `keys/**` posture in the uncaged
     label's reasons list, reusing the existing `keys/**` `PathProbe` evidence —
     **no new probe, no `ENFORCEMENT_PATHS` change.**
2. **D1 preflight-bound selector — `src/gleipnir/preflight/__main__.py`.**
   - New CLI flag on the existing `build_parser()` (`:37-65`), e.g.
     `--mode {uncaged,caged}` (default `uncaged`), mapped to the
     `RequestedMode` enum and passed to `run_preflight(...)`.
   - **The binding (D1's load-bearing obligation):** the CLI maps the verdict to
     an exit code such that a **`caged` request that did not reach `CLOSED`
     exits with the REFUSE code (1)** — i.e. `caged` + not-`CLOSED` can never
     exit 0/success. `uncaged` default + not-`CLOSED` exits with the **new
     non-failing code** (see below). The `CLOSED` verdict still exits 0 in both
     modes (a `caged` request that *did* reach `CLOSED` is the success case).
   - **Exit-code semantics (extend the documented 0/1/2 table without breaking
     it):** `0 = CLOSED` (unchanged); `1 = REFUSE` (unchanged; now also the
     result of `caged`-requested-but-not-closed); `2 = PROCEED_UNCLOSED`
     (unchanged, the `--override-ack` path). The **uncaged default not-closed**
     case maps to a **defined non-failing exit** — resolved here as **exit 0
     with the neutral label** (uncaged default is a legitimate launch-OK
     posture, so the launch wrapper treats it as "go"), distinct from `REFUSE`.
     *(If review judges "uncaged-default should be its own exit code, not 0" a
     material tradeoff, that is a routing-back item — see Open items.)*
   - Update the help text (`:56-64`) and the module docstring exit-code table
     (`:13-19`) to describe `--mode` and the mode-conditional framing.
3. **D2 key-floor OS act — `.gleipnir/keys/marker.key`.** A one-time operator
   `chmod 600` (owner-only). Verified the file exists. This is a strict subset
   of the S-2 activation acts (`plans/s2-activation.md` step 5). **No code
   change** — it is an OS/filesystem state the preflight already probes via the
   `keys/**` `RO_AND_UNREADABLE` posture.
4. **D3/D5 Tier-3 record — `.gleipnir/decisions/operating-posture.md` (new).**
   Operator-authored. Ready-to-apply text provided below.
5. **D3 supersession banners** — top-of-file banners on `s2-g1-closure.md`,
   `substrate-design-pass.md`, `gleipnir-layout-and-memory-model.md`, and the
   `AGENTS.md` trust-tier/guard-status framing. Operator-authored. Ready-to-apply
   text below.
6. **Tests — `tests/test_preflight_*.py`.** The D4/D1 behaviour change is a
   testable contract (verdict/label/exit-code). Test-first (Axiom 1). Tests live
   under `tests/**` which is **NOT** in the `preflight/**` deny — so
   `gleipnir-code` MAY author/extend them even though it may not touch
   `boundary.py`/`__main__.py`. See Assemble.
7. **Tier-0 framing note — `.gleipnir/plans/s2-activation.md`.** A note that the
   N≥5-clean anti-drift gate now applies *within an opt-in caged commitment*,
   not to the default (brief residual). Disposable.

### Integrations map

- `bin/gleipnir-preflight` (shim, verified) — execs `python -m
  gleipnir.preflight "$@"`, so the new `--mode` flag flows through unchanged; no
  shim edit needed.
- `boundary.decide()` ← called by `boundary.run_preflight()` ← called by
  `__main__.main()`. The `requested_mode` value is threaded along this exact
  chain; each hop passes it as a keyword arg with an `UNCAGED` default so every
  existing caller (and every existing test) keeps its current behaviour unless
  it opts into `caged`.
- `keys/marker.key` — consumed by the `keys/**` `RO_AND_UNREADABLE` probe and by
  `verify.marker` (via `KEY_ENV_VAR`). The `chmod 600` does not change the key
  *contents*, so marker/HMAC behaviour is untouched.

### Edge cases (fail-closed discipline preserved)

- **`caged` requested, boundary `CLOSED`** → exit 0, success (the intended
  high-assurance launch).
- **`caged` requested, NOT closed** → `REFUSE`, exit 1, deficiency label
  retained. **This is the anti-false-assurance case — must never soften.**
- **`caged` requested + `--override-ack`** → the existing `PROCEED_UNCLOSED`
  path (exit 2, honest `DEV_MODE_LABEL`); the mode does not suppress the
  override's honest labelling. *(Interaction to test explicitly.)*
- **`uncaged` (default), NOT closed** → neutral non-failing label, informational
  reasons, defined non-failing exit.
- **`uncaged` (default), fully `CLOSED`** → exit 0; the neutral label may note
  the boundary is in fact closed (a legitimate, not contradictory, state).
- **Unknown `--mode` value** → `argparse` rejects it (fail-closed at the CLI
  boundary; no silent default to `caged`).
- **`requested_mode` defaulting** → every internal function defaults to
  `UNCAGED`, so the mode can never accidentally be `CAGED` without an explicit
  operator request (the false-assurance direction is the guarded one).

---

## Link — what must be validated before building

- **VALIDATED — `gleipnir-code` deny of `src/gleipnir/preflight/**`.** Read
  `.gleipnir/agents/gleipnir-code.md:16` — `"src/gleipnir/preflight/**": deny`.
  The `boundary.py`/`__main__.py` edits are therefore **operator-applied**
  (converged P3; no grant path for this change). Tests under `tests/**` are NOT
  denied.
- **VALIDATED — `DEV_MODE_LABEL` and `decide()` shape.** Read `boundary.py`;
  confirmed `DEV_MODE_LABEL` at `:506`, `decide(...)` at `:516`, `override_ack`
  is a distinct concept, no `override_ack→CLOSED` path (`:530-533`, `:555-563`).
- **VALIDATED — no existing mode/`--mode` surface.** Read `__main__.py`; the
  parser (`:37-65`) has `--config-root/--agent-uid/--agent-gid/--override-ack`
  only. `--mode` is genuinely new; exit-code table at `:13-19`.
- **VALIDATED — the four supersession targets + key + shim exist.** `glob`
  confirmed `decisions/s2-g1-closure.md`, `decisions/substrate-design-pass.md`,
  `decisions/gleipnir-layout-and-memory-model.md`, `keys/marker.key`,
  `bin/gleipnir-preflight`; `AGENTS.md` read directly.
- **TO CONFIRM AT BUILD (not blocking the plan):** the exact current test files
  under `tests/` that exercise `decide()`/`run_preflight()`/`main()`, so the
  new mode default (`UNCAGED`) is proven not to regress them (the keyword-arg
  default is designed to preserve them, but the test run is the arbiter).

---

## Assemble — build order (test-first; split by WHO APPLIES)

Ordered so the correctness arbiter (tests) is written before the code, and the
capability boundary is explicit at every step.

**Phase 0 — operator confirmation (blocking gate).**
0.1 P1 and P2 are **operator-converged** (see the Convergence note in the
    Decisions index): P1 = `requested_mode` is threaded through and **never**
    participates in the `all_closed`/`CLOSED` computation; P2 = the
    uncaged-default not-closed case returns **exit 0** (legitimate launch-OK).
    No re-decision is needed — these are inheritances.
0.2 The `boundary.py`/`__main__.py` edits are **operator-applied directly** (the
    operator applies the ready-to-apply §A/§B code diffs), per converged **P3**.
    **No grant path exists for this change** — `gleipnir-code` denies
    `src/gleipnir/preflight/**`, and P3 forecloses any temporary grant. Operator
    application is the sole path, matching the operator-authorship stance chosen
    for the Tier-3 records.

**Phase 1 — TEST-FIRST (agent-buildable: `gleipnir-code`, tests only).**
1.1 Extend/author `tests/test_preflight_*.py` to encode the D4/D1 contract as
    failing tests **before** any `boundary.py`/`__main__.py` edit:
    - `decide(..., requested_mode=CAGED)` with a not-closed probe set →
      `REFUSE` verdict, deficiency label retained.
    - `decide(..., requested_mode=UNCAGED)` (default) with a not-closed probe set
      → neutral non-failing label, reasons retained, and **assert the label is
      NOT `DEV_MODE_LABEL` / not the deficiency string**.
    - `decide(...)` with a fully-closed probe set + present key → `CLOSED` in
      BOTH modes (mode does not gate closure).
    - **Negative/anti-forgery test:** no `requested_mode` value yields `CLOSED`
      from a not-closed probe set (assert `CLOSED` requires `all_closed`).
    - CLI (`main()`): `--mode caged` not-closed → exit 1; `--mode uncaged`
      not-closed → the defined non-failing exit; `--mode caged` + `CLOSED` →
      exit 0; unknown `--mode` → argparse error (non-zero, no silent caged).
    - Interaction: `--mode caged --override-ack` not-closed → `PROCEED_UNCLOSED`
      (exit 2), honest label preserved.
    - Regression: existing `decide()`/`main()` callers with no mode arg behave
      exactly as before (the `UNCAGED` default).
    Run via `bin/gleipnir-sandbox test`; expect RED (feature absent).

**Phase 2 — CODE the relabel + selector (operator-applied, per converged P3).**
Apply the ready-to-apply diffs (below) to
`boundary.py` (new `RequestedMode` enum + neutral label constant + threaded
`requested_mode` into `decide()`, not-closed branches only) and `__main__.py`
(`--mode` flag, exit-code mapping, help/docstring). Re-run
`bin/gleipnir-sandbox test`; expect GREEN. Report pass count + line/branch
coverage (≥85% target).

**Phase 3 — D2 key-floor OS act (operator only).** `chmod 600
.gleipnir/keys/marker.key`. Verify `stat` shows `600` owner-only.

**Phase 4 — D3/D5 Tier-3 prose (OPERATOR ONLY — ready-to-apply text below).**
4.1 Operator creates `.gleipnir/decisions/operating-posture.md`.
4.2 Operator adds the four supersession banners.
4.3 Operator applies the `AGENTS.md` trust-tier/guard-status re-framing.

**Phase 5 — Tier-0 framing note (roster writer or operator).** Add the
`s2-activation.md` note (anti-drift applies within an opt-in caged commitment,
not to the default).

**Phase 6 — HARDENED review (`quality-reviewer`).** Two non-fusing passes
(SPEC-CONFORM + BLAST-RADIUS) + the negative-check attestation
(`attested_by ≠ author`) covering: the mode input cannot manufacture `CLOSED`;
the `caged`-not-closed path still REFUSEs; `keys/marker.key` is `600`; the
banners point to the new record; and — since P3 forecloses any grant — that no
`preflight/**` allow was introduced into `gleipnir-code.md` (the deny remains
the sole entry).

### Who-applies-what (explicit capability split)

| Item | Buildable by | Why / capability note |
|---|---|---|
| `tests/test_preflight_*.py` | **`gleipnir-code`** (agent-buildable) | `tests/**` is NOT in the preflight deny; test-first arbiter |
| `boundary.py` / `__main__.py` relabel + selector | **operator-applied** (converged P3; no grant path) | `gleipnir-code` **DENIES `src/gleipnir/preflight/**`** — cannot touch these; the operator applies the ready-to-apply diffs below directly |
| `chmod 600 keys/marker.key` | **operator only** | OS/owner act; agents cannot chmod Tier-3 |
| `decisions/operating-posture.md` (new) | **operator only** | Tier-3 POLICY; operator kept authorship (D3) |
| 4× supersession banners + `AGENTS.md` framing | **operator only** | Tier-3 POLICY |
| `s2-activation.md` note | roster writer OR operator | Tier-0, disposable |

---

## Ready-to-apply artifacts (for the operator)

> These are the concrete texts/diffs to apply. This plan does **not** apply them
> (Tier-0 write boundary). Line numbers are against the files as read this
> session.

### A. `boundary.py` — D4 relabel + P1 mode input (code diff, deny-gated)

Add near the `Verdict` enum (`:500`) a requested-mode enum and neutral label:

```python
class RequestedMode(Enum):
    """The operator's INTENDED posture for this launch (D1/D4).

    Influences ONLY the returned label + the CLI's exit-code interpretation.
    It NEVER enters the all_closed computation: a CAGED request cannot
    manufacture CLOSED — closure stays gated solely on real probe evidence
    (the anti-false-assurance invariant, brief D1)."""

    UNCAGED = "uncaged"
    CAGED = "caged"


# D4: the legitimate, non-failing default label. The deficiency label
# (DEV_MODE_LABEL) is retained ONLY for a requested-CAGED run that did not
# reach CLOSED — never for the uncaged default.
UNCAGED_DEFAULT_LABEL = "uncaged (key-protected floor) — default operator-trust posture"
```

Change `decide()`'s signature and its **not-closed** branches only (the
`all_closed` computation and the `CLOSED` return at `:555-558` are UNCHANGED):

```python
def decide(
    path_probes: Sequence[PathProbe],
    key_state: KeyState,
    *,
    override_ack: bool = False,
    requested_mode: RequestedMode = RequestedMode.UNCAGED,   # NEW, defaults UNCAGED
) -> PreflightDecision:
    # ... unchanged all_closed computation ...
    if all_closed:
        return PreflightDecision(
            Verdict.CLOSED, "G-1 boundary held at the OS-perms floor", tuple(reasons)
        )
    if override_ack:
        # override path unchanged: honest DEV_MODE_LABEL, PROCEED_UNCLOSED
        return PreflightDecision(Verdict.PROCEED_UNCLOSED, DEV_MODE_LABEL, tuple(reasons))
    if requested_mode is RequestedMode.CAGED:
        # A cage was REQUESTED and not reached — stays loud, fail-closed.
        return PreflightDecision(
            Verdict.REFUSE, "G-1 boundary NOT closed; refusing to launch", tuple(reasons)
        )
    # Uncaged default: legitimate, non-failing posture. Reasons retained as
    # INFORMATIONAL, not a deficiency dump.
    return PreflightDecision(
        Verdict.PROCEED_UNCLOSED, UNCAGED_DEFAULT_LABEL, tuple(reasons)
    )
```

> **Design note for the reviewer (honour check target):** the uncaged-default
> not-closed case returns `Verdict.PROCEED_UNCLOSED` (reusing the existing
> "launch OK but not the strong cage" verdict) with the *neutral* label, so the
> CLI's exit-code path stays simple. The mode-conditional part is the **label**
> (`UNCAGED_DEFAULT_LABEL` vs `DEV_MODE_LABEL`) and the **`CAGED`→`REFUSE`
> branch**. Alternative (uncaged-default gets a brand-new `Verdict` member) is
> deliberately NOT chosen — it would widen the verdict enum and the CLI mapping
> for no behavioural gain. If review prefers a distinct verdict, that is a
> routing-back item.

Thread `requested_mode` through `run_preflight()` (`:985-1012`) as a keyword arg
(default `UNCAGED`) passed into `decide()`.

### B. `__main__.py` — D1 `--mode` selector + exit-code binding (code diff, deny-gated)

Add to `build_parser()` (`:37-65`):

```python
parser.add_argument(
    "--mode",
    choices=["uncaged", "caged"],
    default="uncaged",
    help=(
        "intended posture (D1). 'uncaged' (default): legitimate operator-trust "
        "posture, launch OK, neutral label. 'caged': REQUIRE a CLOSED boundary "
        "— a caged request that is not CLOSED REFUSES (no false assurance). "
        "The mode can never manufacture CLOSED."
    ),
)
```

Map to the enum and pass through in `main()` (`:104-114`):

```python
from .boundary import RequestedMode, Verdict, run_preflight
# ...
requested_mode = RequestedMode(args.mode)
decision = run_preflight(
    config_root,
    args.agent_uid,
    args.agent_gid,
    override_ack=args.override_ack,
    requested_mode=requested_mode,
)
```

Exit-code mapping (replace `:123-127`) — the D1 binding lives here:

```python
if decision.verdict is Verdict.CLOSED:
    return 0
if decision.verdict is Verdict.PROCEED_UNCLOSED:
    # Distinguish the legitimate uncaged default (non-failing, exit 0) from the
    # operator-acknowledged override (exit 2). A CAGED request never reaches
    # this branch as a "pass": caged-not-closed is REFUSE below.
    if requested_mode is RequestedMode.UNCAGED and not args.override_ack:
        return 0            # uncaged default: legitimate launch-OK posture
    return 2                # --override-ack: honest dev-mode escalation
return 1                    # REFUSE (incl. caged-requested-but-not-closed)
```

Update the module docstring exit-code table (`:13-19`) to document `--mode` and
the uncaged-default exit-0 semantics.

> **The D1 binding, stated for the reviewer:** a `caged` request reaches exit 0
> **only** through `Verdict.CLOSED`, which `decide()` produces **only** from
> `all_closed` (real probe evidence). `caged` + not-closed falls to the final
> `return 1` (REFUSE). There is no path from `--mode caged` alone to a success
> exit. This is the anti-false-assurance property; the Phase-1 negative test
> asserts it.

### C. `decisions/operating-posture.md` (NEW — operator authors verbatim)

```markdown
# Decision: Operating posture — UNCAGED by default, OPT-IN caged

**Status:** decided (operator, via the built-in escape hatch). Durable Tier-3
decision record. Converged via the orchestrator-surfaced precept-10 gate
(brief: `../plans/override-paradigm-brainstorm.md`). This record SUPERSEDES the
always-on-cage framing in `s2-g1-closure.md`, `substrate-design-pass.md`,
`gleipnir-layout-and-memory-model.md`, and the `AGENTS.md` trust-tier/guard
framing (each now carries a banner pointing here).

## Thesis

Gleipnir operates UNCAGED by default. The single human at the terminal is the
trusted owning principal; an agent acting under operator instruction may perform
any act, INCLUDING editing Tier-3 enforcement config (`agents/`, `keys/`,
`stage-role-map.md`, `decisions/`, `goals/`). This is the intended posture for
the attended single-principal case — a legitimate default, NOT a deficiency and
NOT a not-yet-reached end-state.

The S-2 cage (Tier-3 read-only to the agent, OS wall, unreadable key, agent
cannot mutate its own boundary) is a deliberately OPT-IN high-assurance MODE the
operator switches on when the threat model requires it.

## Threat-model envelope (the assumption the default rests on)

The uncaged default is safe ONLY within this envelope, stated so the tradeoff is
eyes-open:

> Session access equals full operator authority, AND no untrusted content enters
> the agent's context during the session.

Under those two conditions an agent editing Tier-3 is the operator editing Tier-3
by proxy — no privilege boundary is crossed. Outside the envelope, caged mode is
REQUIRED (below).

## Opt-in caged triggers (REQUIREMENTS, not suggestions)

Caged mode (run the fail-closed preflight to a CLOSED verdict + the operator's
S-2 OS acts) is REQUIRED for:

1. **Unattended / autonomous / long-running sessions** (no human watching).
2. **Any session ingesting untrusted external content** (web fetch of untrusted
   pages, third-party repos, pasted/attached content of unknown provenance).
3. **Higher-assurance contexts** — handling secrets, producing attested
   artifacts others rely on, or multi-agent / hosted operation (C-tier).

## Key-protected floor (retained even in the uncaged default)

Even in the uncaged default, `.gleipnir/keys/marker.key` stays `chmod 600`
owner-only. The G-3 HMAC key's compromise is silent, cross-session, and defeats
the evidence the framework uses to prove work happened — so it is protected in
BOTH modes. The default posture is therefore labelled **"uncaged (key-protected
floor)"**, not "everything open". Uncaged is NOT all-or-nothing.

## Honesty invariant (both modes)

The operator ALWAYS knows which mode a session runs in. The preflight labels the
state at every launch: the uncaged default gets a neutral, legitimate label + an
informational reasons list; an explicitly-requested caged run that does not reach
CLOSED keeps the loud "NOT closed" deficiency language and REFUSES. Relabelling
changed how the default is FRAMED, never whether the state is disclosed.

## What is NOT changed

G-2 (broker single-holder), G-3 (keyed evidence — floor retained above), G-4
(bus), G-5 (deterministic orchestration), and G-6 (memory-poisoning model) are
not repealed. This record changes the DEFAULT posture of G-1's S-2 boundary and
the Tier-3-unwritable DEFAULT only.
```

### D. Supersession banners (operator adds at top of each file, below the H1)

**`decisions/s2-g1-closure.md`, `decisions/substrate-design-pass.md`,
`decisions/gleipnir-layout-and-memory-model.md`** — add:

```markdown
> **SUPERSEDED IN PART by `operating-posture.md` (default-uncaged paradigm).**
> The always-on / terminal-closure / Tier-3-unwritable framing in this record
> describes the OPT-IN CAGED mode, not the default. Gleipnir now operates
> UNCAGED by default (trusted single-principal terminal); the S-2 cage is a
> deliberate opt-in. This record's mechanisms remain correct WITHIN a caged
> commitment. See `operating-posture.md` for the governing thesis, threat
> envelope, and the three opt-in-caged requirements.
```

*(Tailor the middle sentence per file: for `substrate-design-pass.md` name the
"guards take effect last / no session over an unverified boundary" phrasing; for
`gleipnir-layout-and-memory-model.md` name the "Tier-3 agent-unwritable
invariant"; for `s2-g1-closure.md` name the "pending operator activation toward
always-on" phrasing.)*

**`.gleipnir/AGENTS.md`** — reframe the trust-tier table note and the
guard-status G-1 row to state that Tier-3-unwritable and terminal closure are
the **caged-mode** posture, default is uncaged, and point to
`decisions/operating-posture.md`. (Operator edits AGENTS.md; it is Tier-3.)

### E. `plans/s2-activation.md` — Tier-0 framing note (roster writer or operator)

Add a short note: the N≥5-clean-session anti-drift gate (D-G) applies only
*within an opt-in caged commitment* — under the new paradigm, staying uncaged is
a legitimate default, not drift to escape.

---

## Stress-test — acceptance criteria (concrete, checkable)

Each is a pass/fail check the result is validated against.

**Behavioural (code — the test-first arbiter):**
1. `decide(<not-closed probes>, key_state, requested_mode=CAGED)` →
   `verdict == REFUSE` AND label is the deficiency label (not the neutral one).
2. `decide(<not-closed probes>, key_state, requested_mode=UNCAGED)` (and the
   no-arg default) → label == `UNCAGED_DEFAULT_LABEL`, reasons list retained,
   verdict is the non-failing posture (`PROCEED_UNCLOSED`), **NOT `REFUSE`** and
   **NOT** the deficiency label.
3. `decide(<fully-closed probes + present key>, key_state, requested_mode=X)` →
   `verdict == CLOSED` for **both** `X ∈ {UNCAGED, CAGED}` (mode never gates
   closure).
4. **Anti-forgery:** there is no `requested_mode` value for which a not-closed
   probe set yields `CLOSED` (assert `CLOSED` ⟺ `all_closed`).
5. CLI `--mode caged` on a not-closed boundary → **exit 1** (REFUSE).
6. CLI `--mode uncaged` (default) on a not-closed boundary → **exit 0**
   (defined non-failing), neutral label printed.
7. CLI `--mode caged` on a fully-closed boundary → **exit 0** (the success cage).
8. CLI `--mode caged --override-ack` on a not-closed boundary → **exit 2**,
   honest `DEV_MODE_LABEL` (override honesty preserved).
9. CLI unknown `--mode zzz` → argparse error, non-zero exit, no silent caged.
10. **Regression:** all pre-existing preflight tests pass unchanged with the new
    `UNCAGED` default (no caller regressed).
11. Coverage ≥ 85% line+branch on the changed functions (report actual).

**OS state (D2):**
12. After Phase 3, `stat` on `.gleipnir/keys/marker.key` shows mode `600`,
    owner-only (group/other have no bits).

**Documentation-integrity (Tier-3, operator-applied):**
13. `decisions/operating-posture.md` exists and contains: the thesis, the
    two-condition envelope verbatim, and the three opt-in triggers labelled as
    REQUIREMENTS.
14. Each of `s2-g1-closure.md`, `substrate-design-pass.md`,
    `gleipnir-layout-and-memory-model.md` carries a banner naming
    `operating-posture.md`; `AGENTS.md` framing points to it.

**HARDENED-review gate (Phase 6):**
15. Two distinct verdicts recorded: `SPEC-CONFORM: PASS` and a separate
    `BLAST-RADIUS: PASS`.
16. Negative-check attestation present, `attested_by ≠ author`, every row with a
    concrete reproducible artifact captured against the applied file, matching
    `over_broad_form_checked` in the same `grant` file, each tagged `[D]`/`[J]`.

**Negative-check attestation skeleton (reviewer fills evidence — do NOT
self-attest, L-C8):**

| grant | intended narrowest scope | over_broad_form_checked | evidence `[D]/[J]` | negative result | attested_by |
|---|---|---|---|---|---|
| `boundary.py` mode input | mode alters label/exit only | mode reachable in `all_closed` / a `CLOSED` return | `grep -n "requested_mode" boundary.py` shows no use inside `all_closed`/the `CLOSED` branch `[D]` | `requested_mode` is NOT referenced in the `all_closed`/`CLOSED` path | (reviewer) |
| `__main__.py` `--mode` | caged-not-closed → exit 1 | `--mode caged` reaching a success exit without CLOSED | run `--mode caged` on a not-closed root; capture exit `[D]` | exit == 1, NOT 0/2 | (reviewer) |
| `keys/marker.key` chmod | `600` owner-only | group/other read or write bits present | `stat -f "%Sp" keys/marker.key` (or `ls -l`) `[D]` | no group/other bits | (reviewer) |
| ~~Phase-0.2(B) grant~~ | **N/A — foreclosed by P3, not reachable** | — | — | — | — |

---

## Execution Workflow (for the implementing/applying actors)

1. **Orchestrator** routes Phase 0 to the **operator** (confirm the converged
   P1/P2/P3 inheritances). P1/P2/P3 are already operator-converged; if a NEW
   material tradeoff surfaces, route back to `gleipnir-brainstorm`.
2. **Orchestrator → `gleipnir-code`** for Phase 1 (tests only — `tests/**` is
   allowed; `preflight/**` is denied). Verify RED via `bin/gleipnir-sandbox
   test`. `gleipnir-code` reports pass/fail + coverage; it does NOT touch
   `boundary.py`/`__main__.py`.
3. **Phase 2 code:** the **operator** applies the §A/§B diffs directly, per
   converged P3 (no grant path exists — `gleipnir-code` denies
   `src/gleipnir/preflight/**`). Verify GREEN + coverage.
4. **Operator** does Phase 3 (`chmod 600`) and Phase 4 (§C new record, §D
   banners, `AGENTS.md` reframe) — all Tier-3, operator-only.
5. **Roster writer or operator** adds the Phase 5 `s2-activation.md` note.
6. **Orchestrator → `quality-reviewer`** for Phase 6: two non-fusing passes +
   the negative-check attestation (reviewer fills evidence; `attested_by ≠
   author`). A single fused "looks fine" verdict is a non-conformance. A
   divergence from the Design Intent found at `quality` is Important and blocks
   the `git` stage until the operator acknowledges it (recorded in the durable
   decision record, not just this Tier-0 plan).
7. **git stage (`git-ops`)** only after both review verdicts pass and the
   attestation is complete.

**Open items — all RESOLVED (operator-converged; recorded here, not re-decided):**
- **P1 — RESOLVED.** Threading `requested_mode` such that it **never** participates
  in the `all_closed`/`CLOSED` computation is the operator-converged mechanism
  (safety invariant). Not open.
- **P2 — RESOLVED.** The uncaged-default not-closed case returns **exit 0**
  (legitimate launch-OK) — operator-converged. Not open.
- **P3 — RESOLVED.** The `src/` code diffs are **operator-applied**; no grant
  path exists for this change (the former apply-path B is foreclosed). Not open.

No open items remain. If a NEW material tradeoff surfaces during build, route it
back to the brainstorm gate.

---

## Design Principles (Gate-1 design-time cognition)

**Case routing (per `../goals/plan-format.md` §8, keyed on disqualifier set
`X`):** `P` contains `src/gleipnir/preflight/boundary.py` and `__main__.py` —
members of `X` (`src/**`) — so this is **NOT** case (iii) prose/config-only. The
touched `X`-members are **Python modules with function/enum/module structure**
(`decide()`, `run_preflight()`, `main()`, `build_parser()`, the `Verdict`/new
`RequestedMode` enums). Therefore **CASE (i) — OOP/functional code plan** →
full **SOLID + DRY + SRP + Design Intent** required. (The Tier-3 prose artifacts
in `P` are non-executable, but a single `X`-member with structure selects case
(i) for the plan as a whole.)

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy).**
The conditional-relabel + selector logic MUST distinguish an *uncaged-default,
legitimate* boundary state from a *requested-caged, failed-to-close* boundary
state **using an explicit `requested_mode` input that never participates in the
`all_closed` / `CLOSED` computation**, such that: (a) a `caged` request that did
not reach `CLOSED` REFUSES (exit 1) with the deficiency label retained, and (b)
no value of `requested_mode` can cause a not-closed probe set to return `CLOSED`
or a caged success exit. *Falsifiable:* the intent is violated if a reviewer can
point to any code path where `requested_mode` (or the `--mode` flag) influences
whether `all_closed`/`CLOSED` is reached, or where `--mode caged` yields a
success exit without a real `CLOSED` verdict. (This is exactly the D1
false-assurance surface; the Phase-1 anti-forgery test #4 and CLI test #5/#7 are
its executable checks.)

**Single Responsibility (per new/changed component):**
- `RequestedMode` (new enum) — one responsibility: *name the operator's intended
  posture*. It carries no logic; it does not decide closure.
- `decide()` (changed) — one reason to change: *how probe evidence + key state
  aggregate into a verdict + label*. The mode input adds label-framing branches
  only; it must NOT acquire a second responsibility (deciding closure). If a
  reviewer finds mode logic entangled with `all_closed`, SRP is violated.
- `main()` / `build_parser()` (changed) — one responsibility: *parse operator
  input and map a verdict to an exit code*. The `--mode`→exit-code binding lives
  here, correctly separated from `decide()`'s verdict logic.

**SOLID analysis:**
- **Single Responsibility** — as above; the design deliberately keeps
  *closure decision* (`decide()`) separate from *intent naming* (`RequestedMode`)
  and *exit-code interpretation* (`main()`), rather than overloading `decide()`.
- **Open/Closed** — the change extends behaviour by adding an enum + a keyword
  arg with a safe default and new label branches; it does **not** modify the
  `all_closed`/`CLOSED` path or the existing `override_ack` path. Existing
  callers/tests bind unchanged (extension without modification of the closure
  core).
- **Liskov** — no new subclassing; `RequestedMode`/`Verdict` are flat enums, no
  parent contract to violate.
- **Interface Segregation** — the new surface is one narrow enum + one keyword
  arg + one CLI flag; callers that don't care get the `UNCAGED` default and are
  not forced to know about caged mode.
- **Dependency Inversion** — `decide()` remains a pure function over injected
  probe evidence (`PathProbe`) and now an intent enum; it depends on no new
  low-level/IO detail (the CLI, not `decide()`, owns exit codes and argparse).

**DRY analysis:** the neutral label is a **single named constant**
(`UNCAGED_DEFAULT_LABEL`), not a repeated string literal; the deficiency label
reuses the existing `DEV_MODE_LABEL` constant (no duplication). The exit-code
mapping lives in exactly one place (`main()`), reusing the existing `Verdict`
branch structure rather than re-deriving verdicts. No probe/`ENFORCEMENT_PATHS`
logic is duplicated — the key-floor reason reuses the existing `keys/**`
`PathProbe` evidence rather than adding a parallel probe.
```