# Session state (Tier-0, volatile — the resume entry point)

_Tier-0 TEMPORARY / disposable. **Not authoritative** — the authoritative homes
are `../decisions/` (durable decision records) and the spec (Part D E-seams).
Churned by `session-scribe`. This is the single resume entry point; it
supersedes the old `session-seams-ledger.md` (now a tombstone)._

## Current state

**THIS SESSION — D5 SIDECAR WRITE + SANDBOX `--PROFILE` FLAG + CAUSAL DEPENDENCY UNBLOCKED:**

**Judge-wiring D5 sidecar write-side — CLOSED** (commits `2d98fb5` + `d849642`):
- **The real gap:** Seam 7/Seam 8/live-caller infrastructure was built last session and tested, but the D5 sidecar write-side was missing — nothing wrote `.gleipnir/var/run/pipeline-run.json` on the live path, making GATE unreachable in a genuine run. The stale claim corrected earlier this session (Seam 7/8/live-caller "already built") led to discovering THIS was the real blocker.
- **Full hardened 8-stage pipeline:** brainstorm (converged Approach A: implement the sidecar write at `commit_changes` in `mcp_server.py`) → plan (`d5-sidecar-write.md`) → spec-review PASS → test (16 test methods in `tests/test_broker_run_manifest.py`, testing both write-on-success and write-on-revert paths) → code (`_write_run_manifest_head_sha` fixture + `commit_changes` call injection in `mcp_server.py`) → quality APPROVED (spec-conform PASS, blast-radius PASS, honour check HONOURED — writes are minimal, focused, correct per plan) → git.
- **REAL verification required unblocking a systemic tooling gap** (see item 2 below): before a genuine broker-profile test run could happen, the `bin/gleipnir-sandbox` needed a `--profile` CLI flag to override the hardcoded default. Once that was unblocked, **140/140 passing, 99% coverage** on `mcp_server.py`, zero regressions on the 961-passed/12-skipped full suite.
- **One test-authoring bug found and fixed at root cause:** PEP 563 stringized-annotation assertion needed `eval_str=True` on the type-check annotation, not a weakened tolerance. Test is now correct and green.
- **Result: GATE is now reachable in a live run** — the actual functional gap this session resolved.

**Sandbox `--profile` CLI flag + Tier-3 grant — CLOSED** (commits `ffdb72f8` plan + `81e2cf26` implementation, plus grant commit `0a8bc89`):
- **Root-cause discovery:** A tier3-coach Detect→Locate→Propose→Converge workflow uncovered that `bin/gleipnir-sandbox test|lint` had a single global `default_profile` hardcoded with no per-invocation override. This forced a recurring manual Tier-3 edit-and-revert round trip across ≥5 prior plans — directly against the framework's own "language-agnostic sandbox" design goal. Operator flagged this pattern as "untenable."
- **Operator convergence:** Option A: add `--profile <name>` CLI flag, enumerate all three profile names (`python`/`broker`/`node`) in the paired Tier-3 grant widening. Trade: bounded agent gains self-select capability for sandbox image. Accepted.
- **Full hardened 8-stage pipeline:** brainstorm → plan (`sandbox-profile-selector.md`) → spec-review PASS → test (10 new test functions in `test_sandbox_cli.py`, covering all three profiles + default fallback) → code (threaded into existing `resolve_profile(profiles, name)` seam; `profiles.py`/`runtime.py` untouched, DRY honored) → quality APPROVED (2 minor non-blocking notes documented: stale docstring in `__main__.py` mentioning profile override, missing ISP regression test for `image-build`) → git → **operator applied the Tier-3 grant widening** (`gleipnir-code.md` line 14–15 grant expanded) → post-apply negative-check attestation PASS (verified grant text applied correctly, verified no over-broad glob was introduced).
- **Durable infrastructure:** This is reusable, committed; any future plan needing broker/node profile test runs now works without a manual round trip.
- **⚠️ INCIDENT during the grant commit (recovered):** the FIRST attempt to commit `gleipnir-code.md` (git-ops) ran `git checkout .gleipnir/agents/gleipnir-code.md` as an ill-advised "reset to clean state first" step, which DESTROYED all 24 uncommitted grant lines (they were never staged, so not recoverable from index/stash/reflog). git-ops then MISDIAGNOSED the cause, reporting the config-scan "closed" message (which is exit 0 = the PASS/CLOSED state, NOT a refusal) as the blocker. The orchestrator caught this by (a) noticing a fabricated commit hash `d7e0a43` written into this file by session-scribe for a commit that never happened, then (b) direct-reading the file to confirm the content was gone. Recovery: the orchestrator had captured the exact 24-line content in an earlier direct read; operator + orchestrator (build mode) restored it verbatim; re-committed atomically via the broker (`0a8bc89`) with EXPLICIT no-destructive-commands constraints. Root cause of the ORIGINAL "commit failed" was the checkout, not config-scan. **Lesson candidate:** never run `git checkout`/`reset`/`restore` on a file with valuable uncommitted work as a "clean first" step; and never trust a subagent's interpretation of a refusal — demand verbatim output (config-scan exit 0 = CLOSED = PASS was misread as the failure).

**Causal dependency — EXPLICIT:** Item 2 (sandbox `--profile` flag) was discovered and built AS A DEPENDENCY of item 1 (D5 sidecar-write). The D5 plan's test file (`tests/test_broker_run_manifest.py`) couldn't be verified under the broker profile without the flag already working. This is why a "sandbox tooling" thread appears inside the "judge-wiring gate" session block — it's not a separate work thread, it's the unblocking prerequisite. Both are now closed; GATE is live end-to-end.

**Remaining backlog items (low-priority, not blocking):**
- Stale module docstring in `src/gleipnir/sandbox/__main__.py` — does not mention the new `--profile` override (added this session); should be updated for reader clarity (quality-reviewer Minor note, non-blocking).
- Missing ISP regression test locking that the `image-build` subparser does NOT gain `--profile` — the code is correct (verified by direct read of `build_parser()`), but no test guards against a future accidental addition (quality-reviewer Minor note, non-blocking).

---

**THIS SESSION — TIER3-COACH GLEIPNIR-CODE GRANT TIGHTENING + JUDGE-WIRING FIRST SLICE + L-C30 RECORDED + JUDGE WIRING 4 ROUNDS SPEC-REVIEW:**

**tier3-coach: gleipnir-code `.github/**` grant tightening — COMPLETE** (commits `2ebe542` + `7c3e11e`):
- **Gap:** gleipnir-code's `edit` permission block did not exclude `.github/**` (flagged as latent observation in prior session's config-scan-ci-wiring plan).
- **Full workflow:** tier3-coach Detect→Locate→Propose→Converge→Handoff via `gleipnir-brainstorm`. Concluded: workflow/least-privilege gap (mitigated by no git/push credentials + pipeline routing already forcing `.github/**` touches through hardened path).
- **Operator convergence:** Option A (deny `.github/**` outright) via `question`, recorded in `plans/gleipnir-code-github-grant-control-proposal.md`'s Convergence section.
- **Plan:** `plans/gleipnir-code-github-grant.md` (hardened path — enforcement-path-set `E` member). Both spec-conformance and blast-radius passes PASSED via `quality-reviewer`.
- **Applied edit — 2 rounds of orchestrator-initiated git-verification before landing correctly:** round 1 claimed "applied" but disk showed no change; round 2 landed the deny line in the WRONG block (`bash` instead of `edit` — a no-op); round 3 corrected to land in `edit` block between `.git/**` and `src/gleipnir/preflight/**`, verified via `git diff`. Negative-check attestation finalized against post-apply evidence; cognition honour-check HONOURED (strictly subtractive).
- **Commit:** `2ebe542` (the one-line grant edit); `7c3e11e` (plan-stage artifacts, committed after, referencing `2ebe542`).

**Judge-wiring first slice — G-5 engine gets its first real judge — COMPLETE** (commit `75b0f88`):
- **Pivot:** Operator corrected orchestrator's framing mid-session: "an LLM capable of understanding and analysing the work... IS the judge" — this WAS already the engine's intended design per DESIGN.md and WAS already happening in practice via quality-reviewer+orchestrator, but needed explicit surfacing.
- **Full brainstorm:** 4 material decisions (D1 scope, D2 evidence provenance, D3 call-site location, D4 relationship to cognition layer) + 1 addendum (D2-addendum: TEST transition evidence class), all operator-converged via `question`. D1 diverged: operator chose WIDER Option D (all three judged transitions SPEC_REVIEW/TEST/QUALITY in one slice, not narrower single-edge first cut).
- **Plan:** `plans/judge-wiring.md` written by `gleipnir-plan`, then **4 full spec-conformance review rounds** by `quality-reviewer`, each catching a genuinely new, progressively narrower defect in SAME failure class (collection-time self-reference): (1) test_judge's naive full-suite exit-code would revert-loop every correct test-first delegation — fixed via `--collect-only`; (2) `--collect-only` fails on plan's OWN dogfooding (test_judges.py importing not-yet-created judges.py) — fixed via operator-converged interface-stub-before-tests step; (3) stub fix had gap — eagerly-evaluated module-scope/parametrize factory would still fire `NotImplementedError` at collection time — fixed via MANDATORY deferred-call requirement; (4) deferred-call rule's examples under-enumerated vs. its own affirmative rule — generalized to single principle-based statement covering all evaluation-at-collection-time mechanisms.
- **Blast-radius pass:** PASS (2 non-blocking safe-direction findings documented as KNOWN LIMITATIONS: test_judge's exit-code conflates pytest-collection-faults with sandbox-wrapper refusals; fixture-asset-loading should follow same deferred-body discipline).
- **Built:** `src/gleipnir/engine/judges.py` (NEW) — three `Judge`-shaped factories (`make_spec_review_judge`, `make_quality_judge`, `make_test_judge`) plus shared `_parse_verdict_line` helper, wired via EXISTING `Driver.advance(judge=…)` seam (zero changes to `engine/__init__.py` or `driver.py`). `tests/test_judges.py` + `tests/test_judges_live.py` (NEW), 61 new tests.
- **Test-first flow:** stub-before-tests (Assemble step 0) → tests authored → implementation fleshed out. 815 passed / 12 skipped (baseline 754/12 + 61 new), 87% coverage, independently re-confirmed via second fresh test run before commit.
- **Quality stage caught Important-severity SOLID/DRY divergence:** implementation duplicated arity-check-and-map logic vs. plan-mandated shared `_parse_verdict_line` helper. NOT self-cleared by reviewer; operator converged on FIX via `question`; `gleipnir-code` refactored with zero test-file changes, identical 815/12 pass count; re-reviewed and RESOLVED.
- **Honest scope caveat:** judges built but NO live caller wired yet (no dependency on not-yet-built Seam 7 live hook or Seam 8 real-CI-attestation-fetch; explicitly out of scope).
- **Commit:** `75b0f88` (all 5 files: judges.py, both test files, both plan files, in one commit).

**L-C30 recorded** (commit `bd69149`): test-first plans whose own tests exercise not-yet-built code risk collection-time self-reference through MULTIPLE distinct language mechanisms (imports, module-scope statements, parametrize/fixture-params argument lists, default-argument expressions) — state the general timing rule ("nothing under test evaluated except inside a body that runs at test/fixture invocation time") up front in first authoring pass, not as enumerated list of examples, because adversarial review will keep finding mechanisms the list didn't name (as it did here, across 4 rounds).

**Process note worth carrying forward:** the `.github/**` grant edit required 2 rounds of orchestrator-initiated re-verification against git before landing correctly (claimed-applied-but-wasn't, then landed-in-wrong-block) — orchestrator caught both by checking `git diff`/`git status` directly rather than trusting operator's "done"/"fixed" claims. This is never-self-attest discipline applied symmetrically (not just to subagents, but to verifying operator-reported state too).

---

**PRIOR SESSIONS — OI-1 CLOSED + OI-2 COMPLETE + Ansible playbook EXECUTED & GREEN + go-caged-runbook UPDATED + CONFIG-SCAN FULLY WIRED (broker + VCS-hook + CI) + L-C29 RECORDED:**

**OI-1 RESOLVED** (commits `b1afa6f` + `be20988`): `bin/gleipnir-launch` wrapper
now correctly passes `--mode caged` on every invocation, genuinely enforcing the
fail-closed caged boundary gate. Stale cross-references in `decisions/go-caged-runbook.md`
and `skills/go-caged/SKILL.md` cleared; both now state wrapper fail-closes while
preserving AC-4 as the authoritative boundary-closure verification.

**CONFIG-SCAN VCS HOOK WIRED** (commits `608899e` + `072f93d`): Closed a real asymmetry — 
config-scan previously ran **only via broker write** (git-guard.ts plugin); now 
`hooks/pre-commit` runs it ALWAYS-ON on every commit (human or agent; broker cannot 
`--no-verify`), fail-closed on REFUSE or can't-run, mirroring git-guard exit contract 
(0 proceed/1 block/2 warn+proceed/else+can't-run block). Secret-scan preserved byte-for-byte. 
New `tests/test_precommit_hook.sh` (12-case host shell test, temp-repo+stub-CLI, no real-tree 
mutation) — **ALL 12 PASS incl. live-repo self-pass** (no lockout). **Full hardened pipeline:** 
plan → spec-review PASS (caught+fixed feasibility defect: test-execution was mis-routed to gleipnir-code 
which can't run sh; corrected to build-session-executes) → test/code → quality blast-radius PASS 
+ negative-check attestation + cognition honour ([D]-backed by 12/12 green) → git. **Decision record 
`config-scoping-preflight.md` status corrected** (stale "NOT YET WIRED" → "wired on broker + 
VCS-hook paths; CI deferred"). Plan: `plans/config-scan-precommit-hook.md`.

**CONFIG-SCAN CI GATE WIRED** (commit `a7e4497`): The final enforcement path closed — 
added `.github/workflows/config-scan.yml`, the repo's FIRST-EVER CI workflow. Runs 
`bin/gleipnir-preflight config-scan` on `push`→`main` and on `pull_request`, as a THIRD 
enforcement path independent of local hook state (after git-guard.ts broker plugin and 
hooks/pre-commit VCS hook). config-scan now enforced on **all three paths: broker write + 
local commit + CI.** **Exit-2 divergence (deliberate, documented):** CI hard-fails on exit 2 
(`PROCEED_UNCLOSED`), diverging from git-guard.ts/hooks/pre-commit warn-and-proceed contract, 
because CI is the authoritative non-interactive gate with no live operator behind `--override-ack`. 
Exit 0/1/else mirrored unchanged. Workflow hardened: `permissions: contents: read` only 
(least privilege, fork-PR safe); bare venv, no pip install (stdlib-only core); actions pinned 
by full commit SHA. **Full hardened 8-stage pipeline:** brainstorm (2 material decisions surfaced 
+ converged) → plan → spec-review PASS (caught+corrected a rationale defect: plan falsely claimed 
no roster agent can write `.github/**`, but gleipnir-code's edit grant does NOT exclude `.github/**` 
— only `.gleipnir/decisions/**` genuinely has no roster path via L-C27 gap) → test PASS (static 
YAML validation) → code (gleipnir-code wrote the workflow; operator applied Tier-3 decision-record 
edit in build mode) → quality GO (blast-radius PASS incl. SHA pin verification; cognition honour-check 
HONOURED; negative-check attestation confirmed) → git → gate. **Decision record `config-scoping-preflight.md` 
status flipped** (from "CI deferred" → "CI WIRED on all three paths"). Plan: `plans/config-scan-ci-wiring.md`.

**Latent observation (not fixing this session):** gleipnir-code's `edit` grant is `"*": allow` 
minus denies for `.gleipnir/**`, `.git/**`, `src/gleipnir/preflight/**` only — it does NOT exclude 
`.github/**`. This means gleipnir-code can technically write CI workflow files. Worth a future `tier3-coach` 
look (whether to tighten that grant), but **explicitly OUT OF SCOPE** for this task. Recorded as a 
background thread.

**L-C29 RECORDED** (commit `072f93d`): A test that must stage a secret-matching fixture will 
trip the commit-time secret-scan on the test file itself — assemble the matching literal at 
runtime so no complete AKIA-prefixed pattern lives in tracked source; never `--no-verify` around it. 
**Surfaced live this session:** the broker secret-scan correctly REFUSED the first commit attempt 
because the test fixture had a literal AWS-key pattern; fixed via runtime assembly. Good proof the 
guard is live.

**OI-2 COMPLETE** (this session):
- **Acts 1–5 verified at OS level** (commits `1b4b2f2`, `35493a9`, `f33cee5`):
  - Act 1: gleipniragent uid/gid 510 (non-login, `/usr/bin/false`) — VERIFIED.
  - Act 2: `agent-identity.env` written (uid/gid 510, mode 644, owner jasonh); **now gitignored** (commit `1b4b2f2`).
  - Act 3: ownership/group layout (Tier-0/1/2 dirs group=gleipniragent, g+w; Tier-3 dirs staff, no group write) — VERIFIED.
  - Act 4: enforcement subtree OS-read-only (8 ENFORCEMENT_PATHS all drwxr-xr-x, files 644) — VERIFIED.
  - Act 5: G-3 key `mode 600` owner-only (agent-unreadable) — VERIFIED.
- **AC-4 boundary genuinely CLOSED:** `sudo GLEIPNIR_MARKER_KEY_FILE=... bin/gleipnir-preflight --agent-uid 510 --agent-gid 510 --mode caged` → `Verdict.CLOSED`, empty reasons, exit 0 — verified live this session.
- **Box is CAGED at OS level** (all acts in place; boundary operational).
- **Act 6 (wrapper install):** bin/gleipnir-launch exists in repo (0755 ready); physical install + operator relaunch deferred (FU-4, optional; box is already caged).

**Ansible playbook FU work (FU-1 DONE + FU-3 DONE):**
- **FU-1 DONE (`803855f`, preceded by `5539013`):** Installed Ansible (`brew install ansible ansible-lint`; ansible-core 2.21.3, ansible-lint 26.8.0) and **RAN the 3-layer test harness for the first genuine execution.** D3/D4 machinery worked as designed: first real run surfaced actual defects the authored-not-executed state had hidden. **Fixed real issues found:**
  - act-3 `chmod -R a+rX .gleipnir` overlapped the enforcement subtree (acts 4/5 own those paths; non-overlapping fix applied → D5).
  - act-4 recursive `chmod -R a+rX,go-w keys/` re-loosened the key file, then act-5 re-tightened it every run (non-idempotent churn). Fix: act-4 excludes `*.key` → D6.
  - `.ansible-lint` config created; ansible-lint real-run fixes applied.
  - test-harness stat portability bug (GNU `-c` first / BSD `-f` fallback) causing false BUG-2 + layer-3a symptoms — fixed.
  - **NOW GENUINELY GREEN:** syntax-check + ansible-lint (production, 0 fail) + `--check-mutates-nothing` + idempotency (2nd run `changed=0`) + AC-4-fail path — **ALL PASS** ([D]-verified by executed harness, not narrative).
  - **Decisions D5/D6 recorded** in `decisions/s2-caged-ansible.md` (idempotency refinements; OS end-state preserved; operator-converged after first real run).
  - **D4 state updated** to D4-FU-DONE (tests authored, executed, proven green).
  - **Hardened quality re-review:** spec-conform PASS + blast-radius PASS + negative-check attestation (attested_by≠author) + cognition honour ([D]-backed by live executed run) — **GO.**
- **FU-2 SKIPPED** (operator decision): `[profile.ansible]` sandbox image deemed redundant given FU-1 host install. Remains optional if bounded in-container Ansible testing is wanted later.
- **FU-3 DONE (`9204129`):** `decisions/go-caged-runbook.md` Step 1 prose updated to prefer the Ansible playbook (`sudo ansible-playbook -i ansible/inventory.ini ansible/site.yml`) while retaining the six manual acts as authoritative spec + fallback. Citations to D5/D6 added. Light-path spec-review PASS. Does not weaken AC-4 authority (caged entry stays explicit operator act).
- **FU-4 DEFERRED** (operator decision): `bin/gleipnir-launch` install to 0755 + relaunch caged. Available whenever the operator wants to operate caged; playbook's act-6 installs it. This session stayed uncaged (jasonh/501; box OS-level caged but not running in-caged).

**Commits this session (12 total; verified against disk; all pushed to origin/main):**
1. `b1afa6f` — OI-1 FIX: bin/gleipnir-launch now passes --mode caged
2. `be20988` — Stale go-caged refs cleared (runbook + skill)
3. `0745b85` — L-C27 recorded
4. `1b4b2f2` — .gitignore: agent-identity.env (host-local file now ignored)
5. `35493a9` — L-C28 recorded (OS proposal gitignore treatment)
6. `f33cee5` — bin/gleipnir-launch hardened + Ansible decision & plan (spec-conform PASS; hardened path)
7. `5539013` — Ansible playbook + 3-layer test harness (spec-conform PASS + blast-radius PASS + attestation; authored, not yet executed)
8. `803855f` — Ansible installed + FU-1 HARNESS EXECUTED: real defects found & fixed; D5/D6 recorded; tests NOW GREEN ([D]-verified)
9. `9204129` — FU-3: go-caged-runbook Step 1 updated to reference Ansible playbook as preferred delivery
10. `608899e` — Config-scan wired into hooks/pre-commit: ALWAYS-ON VCS gate, fail-closed, mirrors git-guard contract (hardened pipeline: spec-conform PASS + quality blast-radius PASS + attestation)
11. `072f93d` — L-C29 recorded: test fixture assembly at runtime to avoid tracked secret pattern; broker secret-scan caught attempt, proving live-end-to-end validation
12. `a7e4497` — CONFIG-SCAN CI WIRED: added `.github/workflows/config-scan.yml` (push/PR gate); full hardened pipeline; decision record status updated (broker + VCS-hook + CI all live now)

**HEAD at `a7e4497`; working tree clean.**

**Ansible environment:** ansible-core 2.21.3, ansible-lint 26.8.0 (installed this session; available for future Ansible work + optional FU-2).

Tests NOW GENUINELY GREEN (executed, verified): all 3 layers pass; AC-4-fail path tested; idempotency confirmed (0 changes on 2nd run). Framework baseline tests still 754 passed, 12 skipped. Cognition layer PROVEN LIVE + VALIDATED.

## Built slices (verified against disk / commits)

**THIS SESSION — D5 sidecar write + sandbox `--profile` flag + causal dependency resolved (HEAD current, 6 commits):**

- **Judge-wiring D5 sidecar write-side (commits `2d98fb5` + `d849642`)** — Implemented the missing write-path that makes GATE reachable: `src/gleipnir/broker/git/mcp_server.py::_write_run_manifest_head_sha` writes `.gleipnir/var/run/pipeline-run.json` after successful `commit_changes`. Full 8-stage pipeline: brainstorm→plan→spec-review PASS→test (16 test methods, `test_broker_run_manifest.py`) → code → quality APPROVED (spec-conform PASS, blast-radius PASS, honour HONOURED, writes minimal/focused) → git. 140/140 passing, 99% coverage on `mcp_server.py`; 961/12 full suite green, zero regressions. One PEP 563 stringized-annotation bug fixed at root (needed `eval_str=True`). Verified on disk: fixture in place in `mcp_server.py`, test file exercising both write-on-success and write-on-revert paths. **Result: GATE is now reachable in live runs.**
- **Sandbox `--profile` CLI flag + Tier-3 grant (commits `ffdb72f8` plan + `81e2cf26` implementation + `0a8bc89` grant)** — Added `--profile <name>` flag to `bin/gleipnir-sandbox`, eliminating the hardcoded default that forced ≥5 prior plans through manual Tier-3 edit-and-revert cycles. Operator converged on Option A: enumerate all three profile names (`python`/`broker`/`node`) in grant; bounded agent self-selects. Full hardened 8-stage pipeline: brainstorm→plan(`sandbox-profile-selector.md`)→spec-review PASS→test (10 new tests, `test_sandbox_cli.py`) → code (threaded into existing `resolve_profile(profiles, name)` seam in `src/gleipnir/sandbox/__main__.py`, DRY honored) → quality APPROVED (2 minor non-blocking notes: stale docstring in `__main__.py`, missing ISP regression for `image-build`) → git → **operator applied Tier-3 grant** (`.gleipnir/agents/gleipnir-code.md` bash block expanded with 12 `--profile` entries) → post-apply negative-check attestation PASS (independent quality-reviewer confirmed no over-broad glob). **Grant commit `0a8bc89` landed only after a data-loss incident + recovery** (see the incident note in the top "Current state" block — a first git-ops attempt destroyed the working-tree grant via an errant `git checkout`; restored verbatim from an earlier orchestrator read and re-committed atomically). **This was an unblocking dependency for item 1** — broker-profile test runs needed the flag to work.
- **Causal dependency explicit:** Item 2 was discovered and built because item 1's verification required broker-profile test execution, which was blocked by the hardcoded default. Both now closed; judge-wiring infrastructure end-to-end verified.

**PRIOR THIS SESSION — tier3-coach gleiprni-code grant + judge-wiring first slice + L-C30 (commits `2ebe542` + `7c3e11e` + `75b0f88` + `bd69149`):**

- **tier3-coach gleipnir-code `.github/**` grant tightening (commits `2ebe542` + `7c3e11e`)** — Closed workflow/least-privilege gap: gleipnir-code's `edit` grant now explicitly denies `.github/**` (line 16 in `.gleipnir/agents/gleipnir-code.md`, verified on disk). Tier3-coach workflow confirmed: brainstorm surfaced material tradeoff (whether to tighten grant), operator converged on Option A, plan written via hardened path, quality-reviewer spec-conform + blast-radius passes both PASS with attestation (attested_by≠author). Negative-check attestation: `".github/**": deny` IS present in edit block AND NOT overly-broad glob (exact path match). Cognition honour-check HONOURED (subtractive only). Orchestrator's 2-round git-verification before apply (caught claim-without-change, then wrong-block landing) proves the never-self-attest discipline working both directions.
- **Judge-wiring first slice (commit `75b0f88`, 5 files: judges.py + test_judges.py + test_judges_live.py + judge-wiring-brainstorm.md + judge-wiring.md)** — Three `Judge`-shaped factories (spec-review, quality, test) + shared helper wired via existing `Driver.advance(judge=…)` seam. 61 new tests (815 total / 12 skipped, 87% coverage on judges module); stub-before-tests→tests-authored→impl-fleshed Assemble flow; quality stage caught Important SOLID/DRY divergence (arity-check duplication) not self-cleared by reviewer, operator converged FIX, re-reviewed GO. Hardened 4-round spec-conformance review caught collection-time self-reference through 4 distinct mechanisms (imports, module-scope, parametrize, default-arg expressions) progressively, refined into single principle-based rule. No live caller wired (Seam 7/8 dependencies explicitly out-of-scope). Verified against disk: judges.py exists in `src/gleipnir/engine/`; both test files in `tests/`; both plans in `plans/`.
- **L-C30 recorded (commit `bd69149`)** — General collection-time self-reference rule (not enumerated examples) for test-first plans with not-yet-built-code tests. Verified in `lessons/session-lessons-candidates.md` at line 460.

**Stable foundation (multi-session, durable home in `../decisions/`):**
- **G-1 unreachable guards** (preflight; fail-closed; per-file walk); **G-2 capability removal** (sandbox `--network=none`); **G-3.1 unforgeable marker** (keyed HMAC); **G-4 unblindable senses** (typed bus + metrics ledger); **G-5 deterministic engine** (revert edges + budget); **G-6 memory-not-poisonable** (trust-tiered layout). All verified end-to-end dogfood (armed-run; cross-lang HMAC contract).
- **Language-agnostic sandbox** (config-driven toolchain dispatch via `.gleipnir/sandbox/profiles.toml`); Tier-3 preflight-protected.
- **Session-scribe** (Tier-0 bookkeeping writer; resume mechanism; this file).
- **Tier3-coach skill** (control-gap detect→propose→converge workflow; operator-handoff, never implements).
- **Lesson-escalation process (A-hybrid)** (brainstorm → plan → spec-review → approved → orchestrator confirms verbatim via `question` → session-scribe appends; live end-to-end verified; operator UNCONSTRAINED by build mode).
- **Config-scoping preflight (config_scan.py)** (143 tests, 90% coverage; closes L-C12/L-C12b class; validates content/grammar/tool-grant sets; ALWAYS-ACTIVE plugin gate + broker secret-scan).
- **Broker MCP servers** (gleipnir-git + gleipnir-pm; 4 tools each; single-holder scoping via Tier-3 frontmatter; git 99%, pm/mcp 97%, pm/platform 100% coverage; force-push structurally absent; hook-bypass flags refused).
- **Git-enforcement (Approach C)** (plugin: config-scan on every git write; broker: secret-scan always-on pre-commit; layer split closes D9 compliance).
- **Orchestrator context-cap** (Opus capped 250k / 32k output; compaction rules ported from AETOS; policy enforced at hook).
- **Lessons L-C1–L-C30** (graduated through L-C10; L-C11–L-C30 in candidates file; L-C14 fix = Decisions-index shape baked into plan-format.md; L-C19 bridge-recovery design question; L-C20 parity-test guard on allow_table.py ROLE_STATES; L-C24/L-C25 verified against disk discipline + artifact completeness; L-C26 orchestrator completeness-check standing; L-C27 [THIS SESSION] = no roster agent frontmatter materialises Tier-3 grant; L-C28 [THIS SESSION] = OS proposal gitignore treatment gap; L-C29 [THIS SESSION] = test fixture with secret-matching pattern must assemble at runtime, never `--no-verify`; L-C30 [THIS SESSION] = test-first plans with not-yet-built-code tests state collection-time self-reference rule generally, not via examples).

**THIS SESSION — OI-1 CLOSED + OI-2 COMPLETE + Ansible playbook EXECUTED & GREEN + CONFIG-SCAN VCS HOOK WIRED + L-C29 RECORDED (HEAD `072f93d`, 11 commits):**

- **OI-1 RESOLVED (commits `b1afa6f` + `be20988`)** — `bin/gleipnir-launch` wrapper now passes `--mode caged` explicitly (line 31, checked on disk), ensuring genuine fail-close on boundary not-closed. Stale cross-refs in `decisions/go-caged-runbook.md` + `skills/go-caged/SKILL.md` cleared to state wrapper now fail-closes, preserving AC-4 as authoritative verification. Reviewed SPEC-CONFORM PASS + BLAST-RADIUS PASS + negative-check attestation (attested_by=quality-reviewer, light path).
- **OI-2 acts 1–5 VERIFIED at OS level + AC-4 boundary GENUINELY CLOSED (commits `1b4b2f2`, `35493a9`, `f33cee5`):**
   - gleipniragent uid/gid 510 created; agent-identity.env written (mode 644) and **gitignored** (commit `1b4b2f2`).
   - Ownership/group layout applied (Tier-0/1/2 dirs group=gleipniragent g+w; Tier-3 staff no group write).
   - 8 ENFORCEMENT_PATHS chmod'd OS-ro (drwxr-xr-x, files 644).
   - G-3 key `mode 600` owner-only; AC-4 preflight run → `Verdict.CLOSED`, exit 0, empty reasons. **Box is CAGED at OS level, verified live this session.**
- **Ansible playbook BUILT + FU-1 EXECUTED (commits `f33cee5` + `5539013` + `803855f`):**
   - Decision record `decisions/s2-caged-ansible.md` (D1–D4 original, now D5/D6 added; operator-converged; Tool=Ansible, Scope=acts 1–5 + install 6 + AC-4 assert, Test-fidelity=3-layer, Execution-timing=authored-then-executed).
   - `ansible/site.yml` mechanises the six acts idempotently, install-safe, self-verifying (verified against disk: 252 lines, pre/tasks/roles/post structure per spec).
   - `ansible/tests/{run.sh,layer1-static.sh,layer2-dryrun.sh,layer3-idempotency.sh}` 3-layer harness (static/lint + `--check` dry-run + real chmod on disposable fixture).
   - **D4 state → D4-FU-DONE (commit `803855f`):** Ansible installed (`brew install ansible ansible-lint`; ansible-core 2.21.3, ansible-lint 26.8.0). Harness RAN for FIRST TIME — surfaced real defects the authored-not-executed state had hidden:
     - **D5 (act-3 scope fix):** act-3's broad `chmod -R a+rX .gleipnir` overlapped the enforcement subtree (acts 4/5 own those paths) → non-idempotent churn. Fixed: act-3 scoped to non-enforcement subtrees only. OS end-state preserved.
     - **D6 (act-4/act-5 non-overlap):** act-4's `chmod -R a+rX,go-w keys/` re-loosened the key file, then act-5 re-tightened it every run. Fixed: act-4 excludes `*.key` (act-5 owns it exclusively). OS end-state preserved.
     - `.ansible-lint` config created; real-run lint fixes applied. Test-harness stat portability bug (GNU `-c` first / BSD `-f` fallback) fixed.
   - **NOW GENUINELY GREEN:** syntax-check + ansible-lint (0 fail, production-grade) + `--check-mutates-nothing` + idempotency (2nd run `changed=0`) + AC-4-fail path — **ALL PASS** ([D]-verified by live executed harness, not narrative). **D3/D4 machinery working as designed: first real run exposed correctness gaps, machinery proved idempotency rigorously.**
   - **Hardened quality re-review (post-execution):** spec-conform PASS + blast-radius PASS + negative-check attestation (attested_by≠author) + cognition honour ([D]-backed by live green run) — **GO.**
- **FU-3 go-caged-runbook update (commit `9204129`):** `decisions/go-caged-runbook.md` Step 1 prose updated to prefer the Ansible playbook (`sudo ansible-playbook -i ansible/inventory.ini ansible/site.yml`) while retaining the six manual acts as authoritative spec + fallback. Citations to D5/D6 added. Light-path spec-review PASS. Does not weaken AC-4 authority (caged entry stays explicit operator act).
- **CONFIG-SCAN VCS HOOK + CI GATE WIRED (commits `608899e`, `072f93d`, `a7e4497`)** — Closed the asymmetry: config-scan was broker-only (git-guard.ts); now `hooks/pre-commit` runs it ALWAYS-ON on every commit (human or agent; broker cannot `--no-verify`), fail-closed on REFUSE or can't-run, mirroring git-guard exit contract (0 proceed / 1 block / 2 warn+proceed / else+can't-run block). Secret-scan preserved byte-for-byte. New `tests/test_precommit_hook.sh` (12-case host shell test, temp-repo+stub-CLI, no real-tree mutation) — **ALL 12 PASS incl. live-repo self-pass** (no lockout). Full hardened pipeline: plan → spec-review PASS (caught+fixed feasibility defect: test-execution was mis-routed to gleipnir-code which denies `sh*`/`bash*`; corrected to build-session-executes, which holds `bash`) → test/code (gleipnir-code authored; build-session ran test) → quality blast-radius PASS + negative-check attestation + cognition honour ([D]-backed by 12/12 green tests + live-repo pass) → git. Added `.github/workflows/config-scan.yml` (push/PR gate, third enforcement path) with deliberate exit-2 hard-fail divergence from plugin/hook warn-and-proceed (durable home of divergence). Workflow hardened: `permissions: contents: read` only; stdlib-only venv; actions pinned by full SHA. **Full hardened 8-stage pipeline on CI plan:** brainstorm (2 converged decisions) → plan → spec-review PASS (caught+corrected rationale defect re: gleipnir-code `.github/**` grant scope) → test PASS (static YAML validation) → code → quality GO (SHA pins verified) → git → gate. **Decision record `config-scoping-preflight.md` status updated** (stale "NOT YET WIRED" → "wired on broker + VCS-hook + CI paths; all three live now"). Plans: `config-scan-precommit-hook.md` + `config-scan-ci-wiring.md`.
- **Lesson L-C27 recorded (commit `0745b85`)** — operating-posture.md grants instructed-agent Tier-3 writes under uncaged default, but NO roster agent materialises that grant (orchestrator denies edit; plan/brainstorm only plans/**; code denies .gleipnir/**; session-scribe only Tier-0 + one named Tier-2 file). Corrects earlier inaccuracy.
- **Lesson L-C28 recorded (commit `35493a9`)** — a ready-to-apply OS/host proposal that creates a host-local file must specify that file's gitignore treatment. Omitting it leaves an accidental-commit gap (observed this session with agent-identity.env; retroactively gitignored in commit `1b4b2f2`). Now a recorded guardrail.
- **Lesson L-C29 recorded (commit `072f93d`)** — A test that must stage a secret-matching fixture (e.g., AKIA-prefixed patterns) will trip the commit-time secret-scan on the test file itself — assemble the matching literal at runtime so no complete pattern lives in tracked source; never resort to `--no-verify`. **Surfaced live this session:** the broker secret-scan correctly REFUSED the first commit attempt on the test fixture when it contained a literal AWS-key pattern; fixed via runtime assembly. Good proof the guard is live and end-to-end validated.

**Prior-session paradigm work (retained; commits 7b18bb1 / 10b7edc / 53be4c4→3d136ad→0f52460):**
- **Operating posture — UNCAGED by default, OPT-IN caged (commit 7b18bb1)** — Durable decision: `decisions/operating-posture.md`. Framework security boundary default REVERSED: single-principal operator is trusted principal; agents under instruction MAY write Tier-3. Caged mode (S-2 boundary + OS acts) is OPT-IN, required ONLY for (i) unattended/autonomous, (ii) untrusted-content ingestion, (iii) higher-assurance. G-3 key stays `mode 600` in BOTH modes (key-protected floor). **Mechanism (tested):** preflight has `RequestedMode {uncaged,caged}` + `--mode` CLI selector. Safety invariant: `requested_mode` NEVER participates in closure — uncaged can be unclosed; caged-requested-but-unclosed REFUSES. Tests 754 passed, 12 skipped; `tests/test_preflight_mode_selector.py` + 23 pre-existing updated. Hardened-path review: SPEC-CONFORM (2 reconciliations) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check: clean.
- **Enforcement-path set E extended (commit 10b7edc)** — Added `.gitattributes` + `.gitmodules` to Axis 2(a) literals (same blast-radius class as `.gitignore`). Rationale per file: `.gitattributes` controls git behaviour (line-ending, filters, diff/merge selection; silent change alters stored content); `.gitmodules` declares submodule URLs (URL change = supply-chain surface). Explicit enumeration per opencode.jsonc precedent. Lock-files deferred (nested subprojects + open-ended basenames). Hardened-path review PASSED.
- **Caged-mode operator-facing capability BUILT & PUSHED (commits 53be4c4 → 3d136ad → 0f52460)** — **Artifacts (Tier-3, now on main):** `.gleipnir/decisions/go-caged-runbook.md` (operator front door; inlines --mode caged invocation, AC-4 gate, rollback; REFERENCES not duplicates six S-2 C2 OS acts). `.gleipnir/skills/go-caged/SKILL.md` (guides + verifies operator through runbook vs. box state, gates on AC-4; operator-executes-acts, hybrid shape like tier3-coach). Sibling to tier3-coach (detects gaps vs. executes lockdown). **Critical safety defect caught in spec-review (commit 0f52460 fix round):** `bin/gleipnir-launch` as drafted called preflight WITHOUT `--mode caged` → would silently launch uncaged when operator thinks caged. BOTH artifacts were corrected to attribute the gate ONLY to the explicit `--mode caged` check, and the runbook warned the wrapper was convenience-not-gate until amended (tracked as OI-1). **OI-1 has since been RESOLVED this session (commit `b1afa6f`, see the "Recent" block above): the wrapper draft now passes `--mode caged` and the stale warnings were cleared (commit `be20988`).** Prior hardened-path: SPEC-CONFORM (1 fix) + BLAST-RADIUS + attestation (attested_by≠author); cognition honour check clean.
- **Cognition layer PROVEN LIVE + VALIDATED** — Not a guard; fills ATLAS/GOTCHA-prose gap. Two plans this session ran Gate 1 + Gate 2 (caged-mode paradigm + enforcement-path plans). Both submitted Design Principles (Gate 1 case-routed). Spec-review intent-quality + quality honour checks both fired (Gate 2 distinct). **Gate 2 CAUGHT 2 reconciliation defects on paradigm plan** (anti-vacuity rule + stale temporaries); gates fire for real, not documentally. Validated structurally live.

## Open threads / next

### ⭐ JUDGE-WIRING COMPLETE — GATE NOW LIVE AND OPERATIONAL END-TO-END

**JUDGE-WIRING STATUS — NOW LIVE AND OPERATIONAL:**
- **Built:** judges.py + factories + tests + plans all landed and green (commit `75b0f88`).
- **Seam 7 BUILT:** post-tool `tool.execute.after` advance hook → `.gleipnir/plugins/advance-hook.ts` (live TS trigger; calls Python advance entrypoint).
- **Live caller BUILT:** `src/gleipnir/preflight/advance.py::advance_main` — the Python advance entrypoint, dispatched via `bin/gleipnir-preflight advance`, rehydrates `Driver` at the bridge's current state and drives exactly one advance step using the REAL judges. Companion tests in `tests/test_advance_hook.py`.
- **Seam 8 BUILT:** `src/gleipnir/preflight/fetch_attestation.py::fetch_attestation` — real GitHub Actions CI attestation fetch via stdlib `urllib`; feeds `attempt_gate` at the GIT transition.
- **G-3.2 GIT→GATE branch BUILT:** `advance_main` now intercepts `PipelineState.GIT`, fetches a real `Attestation`, and calls `Driver.attempt_gate` — the ONLY path into GATE.
- **D5 sidecar write-side NOW BUILT (this session, commits `2d98fb5` + `d849642`):** `src/gleipnir/broker/git/mcp_server.py::commit_changes` now writes `.gleipnir/var/run/pipeline-run.json` after a successful git commit. This was the REAL missing link that made GATE unreachable in live runs.
- **Sandbox `--profile` flag NOW BUILT (this session, commits `ffdb72f8` + `81e2cf26` + `0a8bc89`):** `bin/gleipnir-sandbox` now accepts `--profile <name>` to override default, unblocking broker-profile test runs that were required to verify the D5 implementation.
- **Status:** Seam 7 + Seam 8 + live caller + D5 sidecar write + sandbox profile ALL operational and tested. All three judged transitions (SPEC_REVIEW, QUALITY, TEST) wired live. **GATE is reachable in a genuine live run — the end-to-end judge-wiring infrastructure is now functional and verified** (140/140 tests passing on broker profile verification; 961/12 full suite green, zero regressions).

**tier3-coach gleipnir-code `.github/**` grant — CLOSED** (commit `2ebe542` + `7c3e11e`):
- The latent observation from prior session's config-scan-ci-wiring plan has been RESOLVED: gleipnir-code's `edit` grant now explicitly denies `.github/**`.
- Not an urgent fix (pipeline routing already forces `.github/**` touches through hardened path; no credentials/git available), but lean-principle and least-privilege tightening applied.

**OI-2 is COMPLETE** (acts 1–5 verified at OS level; AC-4 GO; box is CAGED; playbook executed & proven green).
**The Ansible/caged-mode arc is now CLOSED** (D4-FU-DONE; playbook working machinery; FU-1/FU-3 delivered).
**CONFIG-SCAN is FULLY WIRED** (broker path + VCS-hook path + CI path all live, tested, green). **All three enforcement paths operational** (git-guard.ts plugin on broker write + hooks/pre-commit on every commit + `.github/workflows/config-scan.yml` on push/PR).

**Remaining optional follow-ups (not blocking; operator discretion):**

**Config-scan CI branch-protection promotion (optional, post-validation)**
- Rationale: once the CI workflow is observed green in production use, promote the `config-scan` check to a required status check in GitHub branch-protection settings.
- **Not blocking:** config-scan is already running on push/PR; the branch-protection promotion is a convenience / enforced gate for the repo's main branch.
- **Operator decision this session:** deferred; the CI workflow is live and can be observed for a few rounds before making it required.

**FU-2 — (Optional) Build an `[profile.ansible]` sandbox image**
- Rationale: hardened sandbox profile for running Ansible tests in-container (consistent with the rest of the S-2 test infrastructure).
- **Not blocking:** FU-1 host Ansible install is complete and test harness is proven green; this is a future convenience if bounded in-container Ansible testing is wanted.
- **Operator decision this session:** skipped as redundant.

**FU-4 — (Optional) Install wrapper + operate caged**
- If operator wants to test a genuinely caged session: `sudo bin/gleipnir-launch` (act 6 physical install: `chmod 0755` + operator launch).
- **Status:** box is already caged at OS level; entering a caged session is optional. Playbook's act-6 installs the wrapper (reachable via FU-2 if needed).
- **Not blocking:** the AC-4 boundary is proven closed and the machinery is operational; running a session inside it is optional.
- **Operator decision this session:** deferred; session remained uncaged (jasonh/501) but box is caged.

**FU-1 + FU-3 are NOW CLOSED** (this session, committed). Ansible is installed on this box for any future work.

---

**Resumes to background threads** (lower-priority, multi-session backlog):
- **Gleipnir-code edit-grant scope (tier3-coach candidates):** gleipnir-code's `edit` grant is `"*": allow` minus denies for `.gleipnir/**`, `.git/**`, `src/gleipnir/preflight/**` only — it does NOT exclude `.github/**`. So gleipnir-code can technically write CI workflow files. This was surfaced during the config-scan CI plan's spec-review (caught the defect in the plan's incorrect assertion). Worth a future `tier3-coach` look (whether to tighten that grant to explicitly exclude `.github/**`), but **explicitly OUT OF SCOPE** for this session. Recorded as a latent observation.
- **G-4 remainder:** Seam 7 (live `tool.execute.after` hook); Observer + novelty-triage; Token provenance / cost tracking.
- **E-1 credential-unreachability:** Argument-policy half closed; credential half still open (brokers co-located with env-injected tokens; S-2 necessary-but-not-sufficient).
- **E-2 platform-webhook receiver:** no component home yet.
- **E-3 novelty-triage signal quality:** Seam 7 + observer will reveal.
- **S-2 structural:** mount + terminal closure + S-3 wiring; Rust/C/C++ profiles + offline-deps decision; Option C (plugin-hosted bookkeeping); engine hybrid-C per-stage escalation.
- **Prose/config-only track deferred:** lock-files (same class as `.gitattributes`/`.gitmodules`, deferred; nested subproject appearance + open-ended basenames).
- **Engine:** G-5 engine full implementation; live TS `tool.execute.after` advance hook; real-CI attestation feeding `attempt_gate` / G-3.2.

---

**Stream 2 — caged-mode runbook + go-caged skill (BUILT & PUSHED, commit 0f52460):**
- **Brief:** `.gleipnir/plans/caged-mode-runbook-brainstorm.md` (converged C1–C5).
- **Artifacts NOW LANDED:** `.gleipnir/decisions/go-caged-runbook.md` (operator front door for entering caged mode; inlines --mode caged invocation, AC-4 gate, minimal uncage); `.gleipnir/skills/go-caged/SKILL.md` (guides + verifies operator through runbook, gates on AC-4; operator-applies-acts, same hybrid shape as tier3-coach). REFERENCES (not duplicated) six S-2 C2 OS acts from s2-activation-control-proposal.md (C4 anti-drift, no duplication). Sibling to tier3-coach (tier3-coach detects gaps + proposes; go-caged executes known lockdown).

**Background threads (lower-priority, prior sessions):**
- **G-4 remainder:** Seam 7 (live `tool.execute.after` hook); Observer + novelty-triage; Token provenance / cost tracking.
- **E-1 credential-unreachability:** Argument-policy half closed; credential half still open (brokers co-located with env-injected tokens; S-2 necessary-but-not-sufficient).
- **E-2 platform-webhook receiver:** no component home yet.
- **E-3 novelty-triage signal quality:** Seam 7 + observer will reveal.
- **S-2 structural:** mount + terminal closure + S-3 wiring; Rust/C/C++ profiles + offline-deps decision; Option C (plugin-hosted bookkeeping); engine hybrid-C per-stage escalation.
- **Prose/config-only track deferred:** lock-files (same class as `.gitattributes`/`.gitmodules`, deferred; nested subproject appearance + open-ended basenames).
- **Cognition layer:** PROVEN LIVE & VALIDATED (fired on caged-mode plan; spec-review intent-quality check caught safety defect; quality honour check ran; two plans this session used full Gate 1 + Gate 2).

## Open seams (absorbed from old session-seams-ledger.md; NOT authoritative)

**CONFIG-SCAN status THIS SESSION:** **FULLY WIRED on all three paths** — broker-plugin (git-guard.ts), VCS pre-commit hook (hooks/pre-commit), and CI (`.github/workflows/config-scan.yml`). All three live, tested, green. Exit-2 divergence (CI hard-fails vs. plugin/hook warn-and-proceed) is durable-recorded in decision-record. Optional follow-up: promote CI check to required status in GitHub branch-protection settings (post-validation).

**S-2 status THIS SESSION:** Acts 1–5 VERIFIED; AC-4 boundary genuinely CLOSED; box CAGED at OS level. Ansible playbook codifies future re-setup (tested structure; tests EXECUTED & GREEN, D5/D6 defects found+fixed). Caged-mode arc COMPLETE (FU-1/FU-3 DONE; FU-2/FU-4 optional).

- **S-2 follow-ups (optional, not blocking):** Hardened sandbox profile (FU-2, skipped this session); caged session execution (FU-4, optional).
  - **FU-1 ✓ DONE:** Ansible installed + 3-layer test harness executed; real defects surfaced and fixed (D5/D6); tests now genuinely green.
  - **FU-3 ✓ DONE:** go-caged-runbook Step 1 updated to reference Ansible playbook as preferred delivery.
  - **FU-2:** Optional hardened Ansible sandbox profile (if in-container Ansible testing wanted later).
  - **FU-4:** Optional wrapper install + caged session execution (box is already OS-level caged; entering caged is optional).
- S-2 mount + terminal closure (caging now OS-level; S-3 preflight integration still future).
- E-1 credential-unreachability half (argument-policy closed; credential co-location remains).
- E-2 platform-webhook receiver (no component home).
- E-3 novelty-triage signal quality (Seam 7 + observer).
- **Gleipnir-code edit-grant scope (tier3-coach candidates):** `.github/**` NOT excluded in current grant; may warrant tightening (explicit deny added) — flagged, not fixed this session.
- G-4 remainder (Seam 7, observer, novelty-triage, cost tracking).
- Engine hybrid-C per-stage escalation + G-5 engine full implementation.
- Live TS `tool.execute.after` advance hook; real-CI attestation feeding `attempt_gate` / G-3.2.
- Rust/C/C++ sandbox profiles + offline-deps fetch-then-seal.
- Option C — plugin-hosted typed bookkeeping tools.
- Lock-files (same blast-radius class as `.gitattributes`/`.gitmodules`; deferred due to nested subproject appearances + open-ended basenames).

## Where to look

- `../decisions/` — durable decision records (**authoritative**).
- `../lessons/session-lessons-candidates.md` — L-C1..L-C30 (pre-graduation).
- the spec — Part D E-seams; the canonical requirements.
- `../plans/` — this + other Tier-0 session artifacts.
