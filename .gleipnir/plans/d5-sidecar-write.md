# Plan: Apply the D5 sidecar `head_sha` write side in `commit_changes` (make GATE reachable in a live run)

**Status:** PLAN — authored by `gleipnir-plan` (Tier-0 writer) FROM the CONVERGED
brief `.gleipnir/plans/judge-wiring-live-caller-brainstorm.md` (`## Convergence`,
Approach A, operator-decided 2026-08-22). This is a disposable Tier-0 session
artifact. Full 8-stage **hardened** pipeline (see § Execution Workflow →
Routing). `gleipnir-plan` has NO write access to `src/**` or `tests/**` and did
not — and must not — apply any of this; it writes only this plan.

**Author:** `gleipnir-plan`. **Methodology:** GOTCHA pre-flight + ATLAS
Architect/Trace/Link/Assemble/Stress-test run ahead of this artifact
(`goals/methodology.md`, `skills/atlas`, `skills/gotcha`).

## GOTCHA pre-flight (visible)

- **Goals / order:** checked `goals/manifest.md`; `plan-format.md` is the binding
  artifact-format goal (followed below, all 8 sections). Plan-before-code order
  honoured: this is the plan; tests are authored before/alongside the
  implementation by `gleipnir-code`; the diff is applied afterward.
- **Boundary:** I may write ONLY `.gleipnir/plans/**`. I did not call
  `edit`/`write` on `src/**` or `tests/**`.
- **No material decision re-opened:** the brief's `## Convergence` fixes Approach
  A, `gleipnir-code` authorship with NO Tier-3 grant change, and the full
  hardened pipeline. D5's mechanism (sidecar, plain-file, no MAC, write in
  `commit_changes`) is operator-converged in `seam7-seam8-wiring.md` D5. I plan
  the bounded work; I decide no material tradeoff. One **non-material** testability
  seam (injectable `run_root` vs `__file__`-resolution) is surfaced for the
  implementing stage exactly as the source diff plan flagged it — named, not
  silently baked in.

**Grounding read before planning (every cited path confirmed to exist on disk
this session):**
- `src/gleipnir/broker/git/mcp_server.py` (417 lines; `commit_changes` at L266–377;
  `_current_branch` at L162–166; imports at L36–42; no `os`/`Path`/`pipeline_id`
  today — verified).
- `src/gleipnir/preflight/advance.py` (767 lines; the READ side
  `read_pipeline_run_identity` at L315–351, `pipeline_run_path` at L307–312,
  `DEFAULT_RUN_ROOT`/`PIPELINE_RUN_FILENAME` at L303–304, `MissingRunIdentity`
  at L354–360, the GIT branch in `advance_main` at L560–575 — verified).
- `.gleipnir/plans/seam8-d5-sidecar-write-diff.md` (the ready-to-apply diff +
  test spec, drafted and quality-reviewed as a plan — verified).
- `.gleipnir/plans/seam7-seam8-wiring.md` (parent plan; D5 CONVERGED section,
  Trace row "Run manifest `head_sha` write side (D5)" at L168 — verified).
- `.gleipnir/agents/gleipnir-code.md` (deny set L11–27: `.gleipnir/**`,
  `.git/**`, `.github/**`, `src/gleipnir/preflight/**` + exact-path allows;
  `src/gleipnir/broker/**` is **absent from the deny set** — verified).
- `.gleipnir/agents/git-ops.md` (L16–18: `edit: deny` / `write: deny` /
  `task: deny` — the agent never writes the sidecar — verified).
- Existing broker tests: `tests/test_broker_git_mcp_server.py`,
  `tests/test_broker_tool_surface.py`, `tests/test_broker_git_commit_guard.py`,
  `tests/test_broker_stdlib_only.py` (must stay green — verified present).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| C1 | Which next action | **Approach A** — apply the drafted D5 sidecar write-side diff + tests so GIT→GATE becomes reachable | B (verify/doc-only, build nothing); C (full end-to-end live-run hardening) | **Operator-converged** (brief `## Convergence` #1). A closes the one genuine functional gap (GATE unreachable until the sidecar is written) with a converged, already-drafted diff. C is the sequenced end-state, not this slice. Not re-opened. |
| C2 | Authorship / routing of the broker edit | **`gleipnir-code` authors it as-is; NO change to its deny set** | Route as operator/Tier-3-authored; tighten deny set to `src/gleipnir/broker/**` | **Operator-converged** (brief `## Convergence` #3). `src/gleipnir/broker/**` is NOT in `gleipnir-code`'s deny set (verified L11–27), so by current grant the code agent may edit it. The latent Tier-3 grant question is **deferred** to a separate `tier3-coach` pass, not this slice. Not re-opened. |
| C3 | Pipeline routing (light vs hardened) | **Full 8-stage hardened pipeline** | Prose/config light track | `.gleipnir/broker/**` — and here `src/gleipnir/broker/**` executable code — is enforcement-bearing (E-1 surface; the broker is the single git holder / G-2). Axis-1 disqualifier `X` includes `src/**`, so this is categorically NOT the light track. Two separate review passes + negative-check attestation + cognition honour-check apply. |
| D5 | Sidecar mechanism (inherited, LOCKED) | Plain file `.gleipnir/var/run/pipeline-run.json` = `{pipeline_id, head_sha}`; write side in `commit_changes`; `pipeline_id` from `GLEIPNIR_PIPELINE_ID` env; NO own MAC; `StateMarker` byte-unchanged | D5-marker (extend `StateMarker`); env-var-only pipeline_id; a second HMAC/digest for the sidecar | **Operator-converged** in `seam7-seam8-wiring.md` D5. This plan implements it exactly as decided; it does NOT re-open the mechanism. |
| P1 | `pipeline_id` source at commit time | `GLEIPNIR_PIPELINE_ID` env var (armed-only), NOT an agent-facing tool parameter | Add a `pipeline_id` tool arg to `commit_changes` | Inherited from `seam8-d5-sidecar-write-diff.md` FINDING. A tool arg would make the correlation identity **agent-controllable** — exactly the forgery `attempt_gate`'s pipeline_id-mismatch refusal exists to prevent. Env-var read preserves "framework-written, agent-read-only." Structurally forced: the read side fail-closes unless BOTH keys are non-empty, so `head_sha` cannot be written alone. |
| T1 | Testability seam for the write helper | **Add an injectable `run_root` keyword** to the write helper (mirrors `advance.py`'s `run_root=`), defaulting to the `__file__`-resolved real path; `commit_changes` calls it with no arg (production default) | `__file__`-only resolution (test writes land at the source-tree repo root, needing cleanup) | **Non-material testability decision for the implementing stage** (flagged, not an operator tradeoff — same as the source diff plan's recommended Option (b)). Injection gives the write side the SAME test-isolation the read side already has, so the round-trip test points both sides at one `tmp_path`. If `gleipnir-code`/reviewer prefer Option (a) (tolerate + clean up the real-root write), that is an acceptable equivalent; the plan requires only that the happy-path test can assert against a known, writable location. |

---

## Architect

**Problem (one sentence).** Nothing currently writes the D5 run-manifest sidecar
`.gleipnir/var/run/pipeline-run.json`, so `read_pipeline_run_identity` returns
`None` on every live run, `advance_main` raises `MissingRunIdentity` at the GIT
state, and `Driver.attempt_gate` is never reached — GATE is wired-but-inert; this
slice adds the write side to the git broker's `commit_changes` (the process that
already computes the new HEAD) so a successful armed commit stamps
`{pipeline_id, head_sha}` and GIT→GATE becomes reachable.

**User.** The framework operator running an *armed* gated pipeline
(`GLEIPNIR_PIPELINE_ID` set, a bridge at the GIT state). Secondary: the already-
built Seam-8 read/fetch/GATE path (`advance.py`), which is the sole consumer of
the file this write produces.

**Measurable success criteria.**
1. After a successful commit through `commit_changes` **when armed**
   (`GLEIPNIR_PIPELINE_ID` set, non-empty), `.gleipnir/var/run/pipeline-run.json`
   contains a JSON object with `pipeline_id == <the env value>` and
   `head_sha == <the commit's `git rev-parse HEAD`>` — both non-empty strings.
2. Feeding that written file to the already-built
   `advance.py::read_pipeline_run_identity` returns exactly
   `(<env pipeline_id>, <commit hash>)` — the write and read sides agree on
   path/keys/shape (the round-trip test that would have caught the original gap).
3. When **unarmed** (`GLEIPNIR_PIPELINE_ID` unset/empty), `commit_changes`
   writes NO sidecar and behaves byte-for-byte as today.
4. A sidecar-write failure (e.g. `OSError`) NEVER converts an already-succeeded
   commit into a reported failure — the commit's return contract is preserved.
5. The written object has EXACTLY the keys `{pipeline_id, head_sha}` — no
   signature/digest/MAC field (D5: plain file); the bridge marker /
   `StateMarker` are untouched (no import from `bridge.py`, no marker
   constructed) — the golden-fixture MAC contract stays byte-identical.
6. A missing OR malformed sidecar STILL fail-closes as `MissingRunIdentity` on
   the read side (existing behavior preserved — the write does not weaken the
   read's fail-closed contract; regression-guarded by test).
7. The full existing test suite (incl. all four broker test files) stays green;
   `gleipnir-code`'s grants are unchanged (no deny-set edit).

**Constraints (inherited, binding — NOT re-opened).**
- D5 CONVERGED: sidecar is a **plain file**, protected only by the existing
  `.gleipnir/var/run/` agent-unwritable grant class; **no** own HMAC/digest; do
  NOT extend `StateMarker` (D5-marker rejected).
- `pipeline_id` from `GLEIPNIR_PIPELINE_ID` env (armed-only), never an
  agent-facing tool parameter (P1).
- Framework-written / agent-read-only: this is the broker **process's** write;
  `git-ops` the agent has `edit: deny`/`write: deny` and never writes it.
- Additive-only: `commit_changes`'s signature, return value, and every existing
  failure branch preserved byte-for-byte; the write is best-effort (swallows
  `OSError`) and reached only on the already-successful commit path.
- stdlib-only enforcement core (`os`, `json`, `pathlib` — all stdlib).

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | New / changed | Source-of-truth role |
|---|---|---|---|
| Sidecar write side (D5) | `src/gleipnir/broker/git/mcp_server.py` — Hunk A (imports `os`, `pathlib.Path`), Hunk B (`_PIPELINE_ID_ENV`, `_PIPELINE_RUN_REL`, `_repo_root`, `_write_run_manifest_head_sha` after `_current_branch` at L166), Hunk C (one call in `commit_changes` after `commit_hash` is computed at L367–368, before the `return` at L370) | **changed** (broker server-side code — framework process, NOT a `git-ops` agent tool call) | Writes `{pipeline_id, head_sha}` to the sidecar after a successful armed commit. THE write side that pairs with the built read side. |
| Sidecar file (D5, converged) | `.gleipnir/var/run/pipeline-run.json` = `{"pipeline_id": <str>, "head_sha": <str>}` | **produced at runtime** (Tier-0 framework-written, agent-read-only; plain file, no own MAC) | Run *identity* only; the bridge stays canonical for *position*. Consumed by `advance.py::read_pipeline_run_identity`. |
| Read side (already built — CONTRACT this write must satisfy) | `src/gleipnir/preflight/advance.py::read_pipeline_run_identity` (L315–351) | **unchanged** (verify only) | Fail-closes to `None` unless the file is a JSON object with BOTH `pipeline_id` AND `head_sha` as non-empty strings, at `DEFAULT_RUN_ROOT / PIPELINE_RUN_FILENAME`. |
| Tests | `tests/test_broker_run_manifest.py` (new) — the 8-assertion spec below | **new** | The correctness arbiter (test-first). Keeps existing broker test files intact. |

### Integrations map

```
[armed run: GLEIPNIR_PIPELINE_ID set once at arming, inherited by the broker process]
        |
        v
commit_changes(message, files, repo_dir)   (src/gleipnir/broker/git/mcp_server.py)
   - stage -> always-on secret-scan -> git commit  (UNCHANGED)
   - commit_hash = git rev-parse HEAD               (UNCHANGED, L367-368)
   - _write_run_manifest_head_sha(commit_hash)      (NEW — Hunk C)
        |                                            best-effort, armed-only
        v
   .gleipnir/var/run/pipeline-run.json = {"pipeline_id": <env>, "head_sha": <hash>}
        |
        v  (later, fresh process, GIT-state bridge)
advance_main -> read_pipeline_run_identity(run_root=...)   (advance.py L560-575)
   - None  -> MissingRunIdentity (fail-closed; GATE unreachable)  <-- today's bug
   - (pid, sha) -> fetch_attestation -> Driver.attempt_gate       <-- fixed by this write
```

**Contract the write MUST satisfy (verified against `advance.py`):**
- **Path:** `<repo_root>/.gleipnir/var/run/pipeline-run.json`
  (`DEFAULT_RUN_ROOT / PIPELINE_RUN_FILENAME`, advance.py L303–304, L307–312).
- **Shape:** a JSON **object**, UTF-8.
- **Keys (exact):** `"pipeline_id"` and `"head_sha"`, both non-empty `str`, or
  the reader returns `None` (advance.py L344–351).
- **No MAC/digest/signature** in the file (D5 CONVERGED).

The write emits exactly `{"pipeline_id": <str>, "head_sha": <str>}` — nothing
more, so the reader accepts it and no extra field can be misread as identity.

### Edge cases

- **Unarmed** (`GLEIPNIR_PIPELINE_ID` unset/empty): helper returns immediately;
  no sidecar written; `commit_changes` identical to today.
- **`commit_hash` empty** (rev-parse failed): helper returns without writing (a
  well-formed sidecar requires a non-empty `head_sha`).
- **Write raises `OSError`** (dir unwritable, disk full): swallowed; the
  already-succeeded commit still returns `success: True`. The read side then
  fail-closes to `None` → `MissingRunIdentity` — the correct fail-closed outcome
  (never a false green, never a false commit failure).
- **Malformed pre-existing sidecar**: not this write's concern — the read side
  already fail-closes on malformed JSON / missing keys (advance.py L336–351);
  regression-guarded by test #6 below.
- **Bridge/`StateMarker`**: untouched — this diff imports nothing from
  `bridge.py` and constructs no `StateMarker`; MAC contract byte-unaffected.

---

## Link (what must be validated BEFORE building)

1. **Read-side contract confirmed (done during Trace):** exact path, keys,
   non-empty-string requirement, no-MAC — all read directly from
   `advance.py` L303–351 this session. The write is planned to that contract.
2. **`pipeline_id` availability confirmed (done):** `commit_changes` has NO
   `pipeline_id` today; the broker sources config from env elsewhere
   (`guards.py` uses `GLEIPNIR_GIT_*`), and `mcp_server.py` does not yet import
   `os` — so Hunk A adds `os`/`Path`. `pipeline_id` comes from
   `GLEIPNIR_PIPELINE_ID` (P1), the same convention `advance-hook.ts` established.
3. **Grant facts confirmed (done):** `src/gleipnir/broker/**` is NOT in
   `gleipnir-code`'s deny set (verified) → C2 authorship stands with no grant
   change. `git-ops` has `edit: deny`/`write: deny` → the agent never writes the
   sidecar; the broker process does.
4. **Testability seam identified (T1):** the read side takes an injectable
   `run_root=`; the write helper should mirror it so the round-trip test points
   both at one `tmp_path`. To be confirmed/finalised by `gleipnir-code` at the
   test-authoring step (a non-material choice, either T1 Option (b) [inject,
   recommended] or Option (a) [tolerate real-root write + clean up]).

---

## Assemble (intended build order)

**Test-first (the test is the arbiter).** Author the test interfaces before the
implementation body; never weaken a test to make it green.

1. **Author `tests/test_broker_run_manifest.py`** (`gleipnir-code`, under
   `tests/**`) covering the 8 assertions in Stress-test below — at minimum the
   armed happy-path write, the round-trip against `read_pipeline_run_identity`,
   the unarmed no-op, and the fail-safe (write-failure does not fail the commit)
   BEFORE the implementation is applied. Decide T1 here (inject `run_root` vs
   tolerate real-root write).
2. **Apply Hunk A** — add `import os` and `from pathlib import Path` to
   `mcp_server.py` imports (L36–42 region).
3. **Apply Hunk B** — add module-level `_PIPELINE_ID_ENV`, `_PIPELINE_RUN_REL`,
   `_repo_root`, and `_write_run_manifest_head_sha(commit_hash, *, run_root=None)`
   immediately after `_current_branch` (after L166), with the D5 rationale
   docstring/comment (plain file, armed-only, best-effort, no MAC).
4. **Apply Hunk C** — insert the single call
   `_write_run_manifest_head_sha(commit_hash)` in `commit_changes` after
   `commit_hash` is computed (after L368) and BEFORE the existing `return`
   (L370). Existing signature/return/failure branches untouched.
5. **Run `bin/gleipnir-sandbox test`** — full suite green (all four existing
   broker test files + the new one), coverage at/above target for the new code.

**Authorship/routing:** all of steps 1–4 are authored by `gleipnir-code` (C2).
`src/gleipnir/broker/git/mcp_server.py` is enforcement-bearing broker code
(E-1 surface) — the orchestrator routes it through the **hardened** review path
(below), but no deny-set change is made.

---

## Stress-test (acceptance checks — concrete and checkable)

Mirrors the source diff plan's §4 test spec; these are the checks the result is
validated against.

1. **Armed happy path (core):** with `GLEIPNIR_PIPELINE_ID` set (via
   `monkeypatch.setenv`), a real temp git repo (`git init`, a staged change), and
   `commit_changes(message, repo_dir=<tmp>)` invoked → returned JSON has
   `success: True` and a non-empty `hash`, AND `pipeline-run.json` (at the
   resolved run root) contains `pipeline_id == <env value>` and
   `head_sha == <returned hash>`.
2. **Round-trip against the real reader (strongest):** feed the written file to
   `advance.py::read_pipeline_run_identity(run_root=<test run dir>)` → returns
   exactly `(<env pipeline_id>, <commit hash>)`. This is the assertion that would
   have caught the original gap.
3. **Unarmed no-op:** `GLEIPNIR_PIPELINE_ID` unset → `commit_changes` succeeds and
   NO `pipeline-run.json` is created (or a pre-existing one is left untouched);
   return JSON unchanged.
4. **Fail-safe (contract preservation):** simulate the write path raising
   `OSError` (monkeypatch `Path.write_text`, or make the run dir unwritable) →
   `commit_changes` still returns `success: True` with the correct hash.
5. **Both-keys-together invariant:** when armed, the written file ALWAYS contains
   BOTH `pipeline_id` and `head_sha` as non-empty strings (never one alone) —
   mirrors the read side's fail-closed contract; catches a regression that writes
   only `head_sha`.
6. **Missing/malformed sidecar still fail-closes as `MissingRunIdentity`
   (existing behavior preserved):** with NO file (or a malformed JSON / missing-key
   file) at the run root, `read_pipeline_run_identity` returns `None` and
   `advance_main` (GIT state) raises `MissingRunIdentity`. Asserts the write does
   not weaken the read's fail-closed contract. (May reuse/extend existing
   `advance.py` read tests; the point is an explicit regression guard.)
7. **No-MAC / plain-file invariant (D5):** the written JSON object has EXACTLY the
   keys `{"pipeline_id", "head_sha"}` and no signature/digest/MAC field — guards
   against a future regression re-adding a second integrity scheme.
8. **Bridge/marker untouched + broker surface preserved (blast-radius):**
   `mcp_server` imports nothing from `engine.bridge` and constructs no
   `StateMarker` (grep/attribute check); `tests/test_broker_tool_surface.py`
   (no `--force`, no `--no-verify` reachable) and `tests/test_broker_stdlib_only.py`
   still pass unchanged (the diff adds no argv, no new tool, only stdlib imports).

---

## Execution Workflow (for the implementing pipeline)

- **Routing / classification:** full **8-stage hardened** pipeline. `.gleipnir/`
  broker enforcement surface + `src/gleipnir/broker/**` executable code → NOT the
  prose/config light track (Axis-1 `X` includes `src/**`). `quality-reviewer`
  runs **two separate passes**: (1) **spec-conformance** (`SPEC-CONFORM:
  PASS/FAIL`, rubric = this plan) and (2) **blast-radius / false-success** (the
  adversarial "how could this be wrongly green?" pass, incl. the SOLID/DRY
  dimension), PLUS the **negative-check attestation** — attested by the reviewer,
  never self-attested by the author (L-C8), with reproducible `[D]`/`[J]`-tagged
  evidence per the Hardened-path substance/correspondence/post-change-state rules.
- **Cognition honour-check (Gate 2, at `quality`):** verify the applied
  implementation honours this plan's Design Intent (below). A divergence is
  **Important** and blocks the `git` stage until the operator acknowledges it
  (recorded in the durable decision record, not only in this disposable plan).
- **Order:** plan (this) → spec-review → test → code → quality (two passes +
  attestation + honour-check) → git → gate. **No Phase-0 spike gates this slice**
  — D5 is CONVERGED and the write side has no transcript/spike dependency (unlike
  the seam7/seam8 parent slice). It is a small, converged, apply-and-test change.
- **Test-first:** author `tests/test_broker_run_manifest.py` interfaces before the
  implementation body (Assemble step 1). Never weaken a test to make it green.
- **Verification:** `bin/gleipnir-sandbox test` (in-container, coverage).
- **Authorship (C2, verified grant fact):** `gleipnir-code` authors the
  `mcp_server.py` diff AND the test file. `src/gleipnir/broker/**` is NOT in its
  deny set (`gleipnir-code.md` L11–27), so this is within its current grant. It is
  enforcement-bearing broker code (E-1 surface): the orchestrator routes it
  through the hardened review path above, but **makes NO deny-set change**. The
  latent Tier-3 question (whether to add `src/gleipnir/broker/**` to the deny set)
  is a separate `tier3-coach` convergence, out of this slice (brief `## Convergence`
  #3).
- **One flagged non-material seam (T1), NOT an operator tradeoff:** the write
  helper resolves its path from `__file__`; a clean `tmp_path` test needs either
  an injectable `run_root=` seam (recommended, mirrors `advance.py`) or
  tolerate-and-clean-up. Named for the implementing stage to settle at
  test-authoring; not baked in here.
- **Doc-correction (brief #2) is NOT part of this slice** — it is handled by a
  separate `session-scribe` delegation in parallel; this plan does not plan it.

---

## Design Principles (Gate 1 — cognition layer; CASE (i): OOP/functional code)

`P ∩ X ≠ ∅` (touches `src/gleipnir/broker/git/mcp_server.py` and `tests/**`) and
the touched member has function/module structure (a Python module with
functions). → full **SOLID + DRY + SRP + Design Intent**.

**Single Responsibility (name each new component's one responsibility):**
- `_write_run_manifest_head_sha(commit_hash, *, run_root=None)` — *one job:*
  best-effort, armed-only persistence of `{pipeline_id, head_sha}` to the D5
  sidecar. It does NOT commit (that already happened), does NOT decide success
  (it swallows its own failure), and does NOT read/validate the file (that is the
  read side's job in `advance.py`). One reason to change: the sidecar's write
  shape.
- `_repo_root()` — *one job:* resolve the repo root from `__file__` (four parents
  up: `.../src/gleipnir/broker/git/mcp_server.py`), matching the read side's
  path-anchoring approach. No I/O beyond `Path.resolve`.
- `_PIPELINE_ID_ENV` / `_PIPELINE_RUN_REL` — *one job each:* single named
  definitions of the env-var name and the repo-root-relative sidecar path, so the
  value/shape lives in exactly one place (no re-literaling).
- `commit_changes` (existing) — its responsibility is UNCHANGED (stage →
  secret-scan → commit → return hash); it gains exactly one call to the new
  helper as a side effect, adding no new reason for `commit_changes` itself to
  change beyond "the commit succeeded, so stamp identity."

**SOLID.**
- **SRP:** as above — write-shape, path-resolution, and the commit flow are three
  separate reasons to change in three separate places.
- **Open/Closed:** `commit_changes`'s existing behavior is *extended* by one
  additive call, not modified — every existing branch (staging failure, secret
  finding, diff-read failure, commit/hook failure) is untouched; the new code is
  reached only on the already-successful path. The read side (`advance.py`) is
  not modified at all (it already consumes the contract). Provable by Stress-test
  #4/#8 (contract + surface preserved).
- **Liskov:** N/A in the strict subtype sense — no class hierarchy is introduced
  or altered; the module-level helpers introduce no subtype whose contract could
  weaken a parent's. (Named explicitly rather than skipped: there is no
  inheritance surface here.)
- **Interface Segregation:** the helper exposes the minimal shape the write needs
  — `(commit_hash, *, run_root=None)` — no wider parameter surface; crucially it
  adds **no** parameter to the agent-facing `commit_changes` MCP tool schema
  (P1), so the agent-facing interface stays exactly as narrow as today.
- **Dependency Inversion:** the write depends only on stdlib (`os` env read,
  `json`, `pathlib`) at the broker's own caller edge; it depends on NOTHING from
  `engine/` (no `bridge`/`StateMarker` import), keeping the enforcement core
  pure — the sidecar is a plain data file, decoupled from the digest-protected
  bridge.

**DRY.**
- The sidecar's path/keys/shape are defined to MATCH the single existing read-side
  definition in `advance.py` (`DEFAULT_RUN_ROOT`, `PIPELINE_RUN_FILENAME`,
  `{"pipeline_id","head_sha"}`) — the write does not invent a second convention;
  it targets the one the reader already owns. (The two live in separate packages
  by the framework-write/agent-read split, so the *values* are re-stated in the
  broker rather than imported from `preflight/**` — a deliberate, documented
  coupling verified by the round-trip test #2, which is the DRY-preserving guard:
  a drift between write and read shapes fails that test.)
- `pipeline_id` sourcing reuses the EXACT `GLEIPNIR_PIPELINE_ID` convention
  `advance-hook.ts` established (P1) — no new arming mechanism.
- The env-read-for-config pattern reuses the broker's own existing idiom
  (`guards.py` reads `GLEIPNIR_GIT_*`) rather than introducing a new config channel.

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**
> *The write side adds exactly one best-effort, armed-only side effect to the
> already-successful commit path, producing a plain two-key JSON file
> `{"pipeline_id", "head_sha"}` at the exact path/shape the built read side
> consumes, and it (a) NEVER alters `commit_changes`'s signature, return value,
> or any existing failure branch; (b) NEVER makes `pipeline_id` an agent-facing
> tool parameter; (c) NEVER converts a sidecar-write failure into a commit
> failure; (d) NEVER imports from `engine.bridge` or constructs a `StateMarker`;
> and (e) NEVER writes any key beyond `pipeline_id`/`head_sha` (no MAC/digest).
> Any implementation that violates (a)–(e) VIOLATES this intent and must be
> rejected at review.*

This is falsifiable: a reviewer can (a) `git diff` `commit_changes`'s signature
and return dict (must be unchanged); (b) grep the MCP tool schema for a
`pipeline_id` parameter (must be absent); (c) trace the `except OSError: return`
swallow and confirm the write call sits after `commit_hash` and before `return`;
(d) grep `mcp_server.py` for `bridge`/`StateMarker` imports (must be zero); (e)
assert the written object's keys are exactly `{"pipeline_id", "head_sha"}`
(Stress-test #7).

---

## Return-to-orchestrator note

This plan is written to `.gleipnir/plans/d5-sidecar-write.md`. It plans FROM the
converged brief (Approach A) and the ready-to-apply diff in
`seam8-d5-sidecar-write-diff.md`; it re-opens NO material decision. The single
flagged item (T1: injectable `run_root` vs `__file__`-only for test isolation) is
an explicitly **non-material** testability choice for the implementing stage, not
an operator tradeoff — named, not baked in. No material design tradeoff remains
open. The latent Tier-3 grant question (`src/gleipnir/broker/**` in
`gleipnir-code`'s deny set) is deferred to a separate `tier3-coach` pass per the
brief's convergence, and is NOT part of this slice.
