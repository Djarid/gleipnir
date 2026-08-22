# Plan: Wiring Seam 7 (post-tool advance hook) & Seam 8 (live CI attestation fetch)

**Status:** PLAN — authored by `gleipnir-plan` from the CONVERGED design brief
`.gleipnir/plans/seam7-seam8-wiring-brainstorm.md` (`## Selected Approach`, the
authoritative operator-decided input; D1–D4 are NOT re-opened here). This is a
Tier-0 session artifact (disposable). Full 8-stage **hardened** pipeline (see
§ Execution Workflow → "Routing / classification").

**Author:** `gleipnir-plan` (Tier-0 writer). **Skills/methodology:** GOTCHA
pre-flight + ATLAS Architect/Trace/Link/Assemble/Stress-test run ahead of this
artifact (`goals/methodology.md`, `skills/atlas`, `skills/gotcha`).

**Grounding read before planning (files confirmed to exist on disk):**
`src/gleipnir/engine/__init__.py` (Engine, `attempt_gate`, `Attestation`,
`AttestationStatus`, `PipelineState`, `PIPELINE_ORDER`),
`src/gleipnir/engine/driver.py` (`Driver.advance`, `resume_from_bridge`,
`attempt_gate`, `write_bridge`), `src/gleipnir/engine/judges.py`
(`make_spec_review_judge`/`make_quality_judge`/`make_test_judge`),
`src/gleipnir/engine/bridge.py` (`mint_state`/`validate_state`/`StateMarker`),
`.gleipnir/plugins/sequence-gate.ts` (pre-tool gate, `isArmed`, `loadKey`,
`validateMarker`), `src/gleipnir/preflight/__main__.py` (subcommand dispatch
pattern), `bin/gleipnir-preflight` / `bin/gleipnir-sandbox` (thin shims),
`.github/workflows/config-scan.yml` (the only CI surface),
`.gleipnir/agents/gleipnir-code.md` (grants: `.gleipnir/**` and
`src/gleipnir/preflight/**` both `deny`).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D4 | Scope / arming | WIDE — all three judged transitions (spec-review, quality, test) via Seam 7 **and** Seam 8 8A live poll; GATE reachable via genuine CI this slice | Narrow first slice (7C+8C) | **Operator-converged** (brief `## Selected Approach` D4). Advisory recommended narrow (max-regret 5 vs 8); operator accepted wider regret for end-to-end live GATE now. Not re-opened. |
| D1 | Seam 7 architecture | 7A — TS `tool.execute.after` handler shells out to a Python advance entrypoint that rehydrates `Driver` from bridge, builds the real judge, calls `Driver.advance(judge)`, re-writes bridge | 7B (Python supervisor; second-source-of-truth) | **Operator-converged** (brief D1). Reuses tested `Driver`/`bridge`/`judges.py` untouched (call-site only); no HMAC minting in TS. Not re-opened. |
| D2 | Evidence sourcing for spec-review/quality judges | **H-c (out-of-band caller deposit)** — `quality-reviewer` (which has `write: deny`/`task: deny` and CANNOT write a file itself) returns its verdict transcript **in-band as the `task` delegation result**; the write-capable *caller* (the framework advance entrypoint / hook) captures that returned text and deposits it out-of-band at a known Tier-1 path, which the hook's injected reader then reads — **GATED BY A MANDATORY SPIKE (Phase 0)** | H-b (reviewer writes its own transcript — **REJECTED as impossible**: `quality-reviewer.md` grants `edit: deny`/`write: deny`/`task: deny`, empirically confirmed in `plans/session-02-delegation-smoketest.md:59`); H-a (hook-spawns-subagent, unverified) | **Operator-converged** (brief D2 selected H-b's *intent* — reviewer-independent transcript at a Tier-1 path — but H-b's literal "reviewer writes it" is unrealisable given the read-only reference-floor grant; the realisable form of the same intent is H-c: the caller, not the reviewer, performs the deposit). Independence is preserved because the deposited text is the reviewer's own returned verdict, never the acting agent's self-report. Operator-mandated spike-before-commit. This plan CANNOT run the spike (planning stage has no bash); Phase 0 is that spike with an explicit go/no-go that BLOCKS the transcript-judge steps that follow. |
| D3 | Seam 8 mechanism | 8A — agent-unreachable `bin/gleipnir-preflight fetch-attestation` subcommand under `src/gleipnir/preflight/**`; stdlib `urllib` GitHub Actions REST query; conclusion→`AttestationStatus` map | 8B (CI signing-key + no-home transport, E-2) | **Operator-converged** (brief D3). Inherits agent-unreachability from the existing preflight CLI grant. Not re-opened. |
| D5 | **`pipeline_id` persistence & Q4 correlation mechanism** (NOT resolved by the brief — the brief named Q4 as *a plan deliverable*) | **D5-sidecar + plain-file integrity** (OPERATOR-CONVERGED). Sidecar run-manifest file `.gleipnir/var/run/pipeline-run.json` (framework-written, agent-read-only) carrying `{pipeline_id, head_sha}`; the bridge marker (digest-protected canonical payload) is **left byte-unchanged**. Sidecar is a **plain file protected only by the existing `.gleipnir/var/run/` agent-unwritable grant class** — NO new HMAC/digest scheme. | (a) D5-marker: extend `StateMarker` to carry `pipeline_id`+`head_sha` under the MAC — **REJECTED by operator** (changes the cross-language MAC signing input, breaks every golden fixture / the TS `canonicalSigningInput`); (b) env-var-only pipeline_id (not durable across the fresh-process hook boundary); (c) a second HMAC/digest just for the sidecar — **REJECTED by operator** (integrity sub-question converged on filesystem-permission protection only) | **OPERATOR-CONVERGED** — see "D5 — CONVERGED" below for both choices verbatim + rationale. Resolves Q4 *without* mutating the digest-protected bridge (single-source-of-truth constraint) or touching the golden-fixture MAC contract. Reconciled: the sidecar carries only *run identity* (which run, at which commit), NOT *pipeline position* — the bridge stays sole canonical position authority and the sidecar cannot advance the pipeline, so it is not a second position store. Integrity: the sidecar joins the same agent-unwritable grant class already protecting the rest of `.gleipnir/var/run/`; no roster agent can tamper `head_sha`, so a second digest scheme would be redundant machinery. |
| D6 | Advance trigger (Q2) | Advance fires on completion of a `task` delegation whose `subagent_type` equals the bound role for the current bridge state (symmetric with the pre-tool gate's agent check), and only when `isArmed` | Advance on every tool return; advance on a narrower explicit signal | Planner decision during Trace. Symmetry with the pre-tool gate reuses the existing allow-table projection; any other tool return is out of scope and must be a no-op (fail-safe: wrong trigger either over-advances or never advances). |
| D7 | PENDING handling / bridge-freshness vs CI latency (Q6) | GIT→GATE attempt on PENDING/ABSENT **refuses (does not advance), leaves bridge at GIT, degrades not raises**; re-poll is a *separate* later hook invocation (no in-hook blocking wait). A stale bridge mid-wait routes to the existing `bridge-recovery` path — unchanged | In-hook synchronous long-poll (risks blocking the tool boundary and bridge staleness within one call) | Planner decision during Trace. Keeps each hook call a bounded fresh process; PENDING is fail-closed (no false green) and simply not-yet-GATE. |

---

## Architect

**Problem (one sentence).** The G-5 judge infrastructure and CI-attestation gate
are built and tested but dormant; this slice wires all three judged transitions
live via a post-tool advance hook (Seam 7) and feeds `attempt_gate` a genuine
GitHub-Actions-derived `Attestation` (Seam 8), so the pipeline advances on real
judged evidence and GATE is reachable only on genuine CI status — without
creating a second state store, without letting any agent forge the path, and
without adding an agent-writable enforcement seat.

**User.** The framework operator running an *armed* gated pipeline
(`GLEIPNIR_PIPELINE=on` + a bridge exists). Secondary: the future G-5 engine,
which will one day own the sequencing this hook approximates.

**Measurable success criteria.**
1. When armed, completion of a stage `task` delegation whose `subagent_type`
   matches the current bridge state's bound role causes exactly one
   `Driver.advance(<real judge for that state>)`, re-minting the bridge — for
   **all three** judged transitions (spec-review, quality, test), not just test.
2. The spec-review/quality judges' evidence comes ONLY from the independent
   `quality-reviewer` transcript at a known Tier-1 path (never the acting
   agent's self-report); the test judge's evidence is the mechanical
   `bin/gleipnir-sandbox test -- --collect-only` exit code.
3. GIT→GATE succeeds **only** via `attempt_gate(Attestation)` where
   `status == GREEN` and `pipeline_id` matches the current run's pipeline_id;
   the `Attestation` is produced by the agent-unreachable `fetch-attestation`
   subcommand querying real GitHub Actions status for the run's commit SHA.
4. Nothing advances, fetches, or side-effects when unarmed (pure pass-through).
5. The hook fails **closed** on any subprocess error / uncertainty (mirrors the
   pre-tool gate); the bus emit path degrades, never blocks.
6. No new agent-writable file under the enforcement surface; `gleipnir-code`
   still cannot write `.gleipnir/**` or `src/gleipnir/preflight/**`.
7. The full existing test suite stays green; new tests cover the advance
   trigger, each judge's live wiring, the fetch→status map, the pipeline_id↔SHA
   correlation, PENDING/ABSENT fail-closed, and the unarmed no-op.

**Constraints (inherited verbatim from the brief; binding).** Single source of
pipeline truth (bridge canonical; NO second state store — see D5 reconciliation);
engine purity (zero I/O/bus/CI-fetch in `engine/__init__.py`); no
self-attestation; G-3.2 attestation-only gate; fail-closed (authority-bearing
bridge write) / degrade-not-raise (telemetry bus emit) split; default-OFF /
armed-only (`isArmed`); Tier-3 unreachability of hook/key/driver/fetch subcommand;
stdlib-only enforcement core (`urllib`, not a GitHub SDK; `gh` only ever at the
caller edge, never a core import).

---

## D5 — CONVERGED (operator-decided)

**Status: CONVERGED.** This was the one material tradeoff this plan surfaced to
the operator (Q4 `pipeline_id`↔commit-SHA persistence). The operator has decided
BOTH the mechanism and its integrity sub-question. Recorded here verbatim; the
planner does not re-open it.

**Why it needed the operator (retained for the record).** The brief made Q4
*a plan deliverable* but did **not** decide *where `pipeline_id` is persisted*.
Grounding the Trace surfaced a hard fact: **`pipeline_id` is stored nowhere
today** — not in the bridge marker (`StateMarker` carries only `version`,
`pipeline_state`, `allowed_agents`, `minted_at`, `mac` — confirmed in `bridge.py`
L63–80 and the TS `canonicalSigningInput` L113–118), not in `var/run/`. Every
existing `Driver`/`resume_from_bridge` call takes `pipeline_id` as a
caller-supplied constant (tests pass a literal `PIPELINE_ID`); `judge-wiring.md`
L155 records "pipeline_id/state is the caller's responsibility." So the live
advance hook AND the fetch-attestation subcommand both need a `pipeline_id`
(and, for Q4, its associated commit SHA) that survives the fresh-process hook
boundary. Choosing the persistence mechanism was material because one option
(D5-marker) touches the digest-protected canonical payload — a hard-to-reverse,
cross-language contract change.

### Operator's converged decision (verbatim)

- **D5 mechanism: D5-sidecar.** Build the new
  `.gleipnir/var/run/pipeline-run.json` = `{pipeline_id, head_sha}` sidecar file,
  framework-written and agent-read-only. The bridge marker stays byte-identical;
  the golden-fixture MAC contract is untouched. **D5-marker (extending
  `StateMarker`) is REJECTED — operator confirmed, do not build it.**
- **D5 integrity sub-question: plain file, filesystem-permission-protected
  only.** No new HMAC/digest scheme for the sidecar. It relies on the same
  agent-unwritable grant class that already protects the rest of
  `.gleipnir/var/run/`. **Do not build a second digest/MAC mechanism for it.**

### Rationale (planner's reconciliation, cited for the record)

- **Sidecar is run-identity, not run-position.** The "single source of pipeline
  truth" constraint is about *pipeline position/state*, and the bridge remains
  the sole authority for that. The sidecar carries only *run identity* (which
  run, at which commit) — a fact the bridge has never carried. It is **NOT a
  second position store** and **cannot advance the pipeline** (only
  `Driver.advance`/`attempt_gate` re-mint the digest-protected bridge). So
  admitting the sidecar does not violate single-source: it adds a run-identity
  fact alongside the canonical position store, not a competing position store.
- **Plain-file integrity is acceptable given the existing `var/run/` grant
  class.** The residual attack surface I flagged (a tampered `head_sha` pointing
  the fetch at the wrong commit) is closed by the *same* mechanism that already
  protects the rest of `.gleipnir/var/run/`: no roster agent holds a write grant
  to that path (`gleipnir-code` denies `.gleipnir/**`). Under that grant class,
  an agent cannot tamper the sidecar's `head_sha` in the first place, so a second
  HMAC/digest would guard against a writer that does not exist — redundant
  machinery, not added assurance. (The uncaged-default honesty caveat: this rests
  on the same *cooperative grant discipline* as the D3(b) credential-isolation
  caveat below; it becomes structural under S-2, and this plan claims no stronger
  guarantee — see § Execution Workflow.) Should S-2 or a later change ever grant
  an agent write access under `var/run/`, the integrity sub-question re-opens as
  a new material decision; that is a future trigger, not an open item now.

**Build status:** Phase 3 is **no longer operator-gated.** It proceeds per the
plan's existing sequencing (see Assemble / Execution Workflow). The only blocking
gate that remains is the Phase-0 D2 spike, which gates Phase 1's transcript-judge
steps (Phase 3's fetch/GATE path does not depend on the transcript judges).

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | New / changed | Source-of-truth role |
|---|---|---|---|
| Post-tool advance handler | `.gleipnir/plugins/sequence-gate.ts` (add `tool.execute.after`) OR a sibling `.gleipnir/plugins/advance-hook.ts` | **changed/new** (Tier-3, agent-unwritable) | The advance *trigger* only; delegates all advance/mint logic to Python via shell-out. Reuses `isArmed`, `loadKey`, `validateMarker`, `BRIDGE_REL`. |
| Python advance entrypoint | `src/gleipnir/preflight/advance.py` + `advance` subcommand dispatch in `src/gleipnir/preflight/__main__.py` | **new** (agent-unreachable: `src/gleipnir/preflight/**` denied to `gleipnir-code`) | Rehydrates `Driver.resume_from_bridge(pipeline_id, ...)`, builds the real judge for the current state with an evidence reader, calls `Driver.advance(judge)`. Zero edits to `driver.py`/`engine/__init__.py`/`judges.py`. |
| Evidence readers | inside `src/gleipnir/preflight/advance.py` (caller edge) | **new** | The ONLY I/O boundary for judge evidence. spec-review/quality: read the `quality-reviewer` transcript at the Tier-1 path (D2, spike-confirmed). test: `subprocess.run(["bin/gleipnir-sandbox","test","--","--collect-only"]).returncode`. |
| `quality-reviewer` transcript deposit (written by the CALLER, not the reviewer) | `.gleipnir/logs/<...>/reviewer-verdict.<state>.txt` (Tier-1 RETRIEVED) — **exact path is a Phase-0 spike deliverable** | **new convention** | The write-capable caller — the Python advance entrypoint (`src/gleipnir/preflight/advance.py`, agent-unreachable) invoked by the TS hook — captures the `quality-reviewer` delegation's **returned in-band transcript text** and writes it here out-of-band (H-c shape). The reviewer (`write: deny`/`task: deny`) cannot and does not write it. The deposited content is the independent reviewer's own returned verdict, never the acting agent's self-report. Deterministic capture→deposit→re-read across the fresh-process hook boundary is exactly what Phase 0 must confirm. |
| `fetch-attestation` subcommand | `src/gleipnir/preflight/fetch_attestation.py` + `fetch-attestation` dispatch in `__main__.py` | **new** (agent-unreachable) | Queries GitHub Actions REST status for the run's `head_sha` via stdlib `urllib`; maps conclusion→`AttestationStatus`; constructs `Attestation(pipeline_id, status)`. Token from env, reachable by this subcommand, NOT by any roster agent (E-1 cooperative-policy — see honest caveat). |
| GATE attempt wiring | `src/gleipnir/preflight/advance.py` (GIT-state branch) — calls the fetcher, then `Driver.attempt_gate(attestation)` | **new** | The ONLY path text can never satisfy: `attempt_gate` refuses unless `status==GREEN` and `pipeline_id` matches (engine `__init__.py` L490–496, unchanged). |
| Run manifest (D5, **converged**) | `.gleipnir/var/run/pipeline-run.json` = `{pipeline_id, head_sha}` | **new** (Tier-0 framework-written, agent-read-only; **plain file, no own MAC** — protected by the existing `.gleipnir/var/run/` agent-unwritable grant class) | Run *identity* only; bridge stays canonical for *position*. See "D5 — CONVERGED." |
| Run manifest `head_sha` **write side** (D5) | `src/gleipnir/broker/git/mcp_server.py::commit_changes` (add a sidecar-update side effect after a successful commit) | **changed** (git broker server-side code — framework process, NOT a roster-agent tool call) | Writes/updates `head_sha` in the sidecar at the git stage. `commit_changes` already computes the new HEAD via `git rev-parse HEAD` (`mcp_server.py:367-368`); it persists that value into `.gleipnir/var/run/pipeline-run.json` in the same call. This is the broker *process's* write; `git-ops` the agent has `edit: deny`/`write: deny` and never writes the sidecar. Consistent with "framework-written, agent-read-only" (D5). |
| Tests | `tests/test_advance_hook.py`, `tests/test_fetch_attestation.py`, extend the TS golden-fixture test | **new/changed** | The correctness arbiter (test-first). |

### Integrations map

```
[stage task delegation completes]
        |
        v  (opencode tool.execute.after; only if isArmed)
[TS handler in sequence-gate.ts / advance-hook.ts]
   - reads bridge, validateMarker (fail-closed), gets pipeline_state
   - subagent_type == bound role for pipeline_state ?  (D6)
        | yes                                          | no -> no-op
        v
   shell out: bin/gleipnir-preflight advance   (fail-closed on non-zero exit)
        |
        v  (Python, agent-unreachable)
[src/gleipnir/preflight/advance.py]
   - pipeline_id, head_sha  <- read run manifest sidecar (D5, converged)
   - Driver.resume_from_bridge(pipeline_id, BRIDGE, key_file=...)
   - state == GIT ?
        | no  -> build judge for state:
        |          SPEC_REVIEW -> make_spec_review_judge(read_reviewer_verdict)
        |          QUALITY     -> make_quality_judge(read_reviewer_verdict)
        |          TEST        -> make_test_judge(read_test_exit_code)
        |        Driver.advance(judge)  -> re-mints bridge (authority-bearing)
        |                                  -> bus emit degrades-not-raises
        | yes -> attestation = fetch_attestation(pipeline_id, head_sha)  (8A)
        |          Driver.attempt_gate(attestation)   [GREEN+match only]
        |          PENDING/ABSENT/RED -> refuse, bridge stays at GIT (D7)
        v
[bridge re-minted by Python mint_state]  <- single source of truth (position)
        ^
        |  (next tool call, fresh process)
[TS pre-tool gate reads the new bridge]
```

GitHub Actions integration (Seam 8): stdlib `urllib.request` GET against
`GET /repos/{owner}/{repo}/commits/{head_sha}/check-runs` (or
`/actions/runs?head_sha=...`) with `Authorization: Bearer <token from env>`;
parse the `config-scan` workflow's `status`/`conclusion`; map
`completed+success→GREEN`, `completed+failure/timed_out/cancelled→RED`,
`queued/in_progress→PENDING`, `no matching run→ABSENT`.

### Edge cases

- **Unarmed:** TS handler returns immediately (pass-through); Python never runs.
- **Wrong `subagent_type` for current state:** no-op advance (D6); not an error.
- **Non-stage `task` / non-`task` tool:** out of scope; no-op.
- **Subprocess (Python advance) errors / non-zero exit:** TS handler throws
  (fail-closed), exactly like the pre-tool gate's catch-all.
- **Reviewer transcript absent/malformed/ambiguous:** judges already map this to
  `Verdict.NEEDS_HUMAN` → `HUMAN_QUESTION` (judges.py; no change needed).
- **Test collection non-zero:** `make_test_judge` → `Verdict.FAIL` → revert
  TEST→SPEC_REVIEW (engine table, unchanged).
- **CI PENDING/ABSENT at GATE attempt:** refuse, bridge stays GIT (D7); no false
  green; re-poll is a later, separate hook invocation.
- **CI RED:** `attempt_gate` raises `AttestationNotGreen`; bridge NOT rewritten
  (driver.py L284–292, unchanged); handler surfaces the refusal.
- **`pipeline_id` mismatch (run A's green replayed to gate run B):** `attempt_gate`
  refuses on `pipeline_id != self.pipeline_id` (engine L490–496) — the whole
  point of resolving Q4. The correlation is only sound if the run manifest's
  `head_sha` is bound to the *same* pipeline_id the engine was resumed with.
- **Bridge goes stale during a CI wait (Q6):** `resume_from_bridge` fail-closes
  (`BridgeInvalid`); operator uses `bridge-status`/`bridge-reset` (unchanged).
- **GitHub token absent:** fetch subcommand fails closed → `ABSENT` → GATE
  unreachable (never a fabricated GREEN).
- **Network error / GitHub 5xx:** fetch maps to `PENDING` or `ABSENT`
  (fail-closed), never GREEN.

---

## Link (what must be validated BEFORE building)

1. **[PHASE 0 — MANDATORY D2 SPIKE, go/no-go]** the framework caller can
   deterministically **capture the `quality-reviewer` delegation's returned
   in-band transcript, deposit it out-of-band to a known Tier-1 path, and
   re-read it byte-for-byte** across the `tool.execute.after` fresh-process hook
   boundary (the H-c shape — the caller writes it, NOT the read-only reviewer).
   This plan's stage has no bash/execution, so the spike is the FIRST
   implementation step, not run here. See Assemble Phase 0 for its explicit
   pass/fail criteria and the escalation-on-fail rule.
   **This checkpoint BLOCKS every subsequent plan step that carries the
   cognition honour-check for the spec-review/quality transcript-judge wiring
   (Phase 1's transcript readers).**
2. **[D5 — CONVERGED, no longer a gate]** the `pipeline_id`-persistence
   mechanism is decided: **D5-sidecar** (`.gleipnir/var/run/pipeline-run.json`,
   framework-written, agent-read-only), **plain file, no own HMAC** — integrity
   from the existing `.gleipnir/var/run/` agent-unwritable grant class. See
   "D5 — CONVERGED." Phase 3 no longer waits on operator convergence; it is
   ready per the plan's sequencing. (Retained as a validation item only in the
   sense that the *build* must honor these converged choices — build the sidecar
   as a plain file, do NOT extend `StateMarker`, do NOT add a second digest.)
3. **Confirm** (already done during Trace): `StateMarker` carries no
   `pipeline_id`; `resume_from_bridge` takes it as an argument;
   `gleipnir-code` denies `.gleipnir/**` and `src/gleipnir/preflight/**`;
   `config-scan.yml` is the only workflow and uses `permissions: contents:
   read` (a *read* token is insufficient to see check-runs on private repos —
   validate the token scope the fetcher needs as a Phase-3 sub-step).
4. **Validate** the GitHub Actions REST response shape (which field carries the
   config-scan run's conclusion for a given SHA) against a real run before
   finalizing the status map — a Phase-3 sub-step, mirroring the brief's open
   spike candidate (c).

---

## Assemble (intended build order)

**Phase 0 — D2 SPIKE (go/no-go; BLOCKS Phase 1 transcript wiring).**
The spike tests the H-c mechanism (out-of-band caller deposit), NOT the
unrealisable H-b "reviewer writes its own file" (`quality-reviewer` has
`write: deny`/`task: deny`; that question is already answered — it cannot).
Author a minimal probe: a `quality-reviewer` `task` delegation that **returns**
a known-format verdict line **in-band as its result**; the write-capable caller
(the framework advance entrypoint / hook side) then **captures that returned
text and writes it** to a candidate Tier-1 path; confirm a *subsequent* fresh
`tool.execute.after` process can re-read it. The REAL unknown under test is the
framework's **capture→deposit→re-read across the fresh-process hook boundary**,
not the reviewer's (already-known-absent) write capability.
- **PASS criteria (ALL required):** (a) the caller can reliably **capture the
  `quality-reviewer` delegation's returned transcript text** in-band (the task
  result is available to the caller/orchestrator); (b) the caller durably
  **writes** that captured text to a deterministic, known Tier-1 path
  out-of-band; (c) a later `tool.execute.after` invocation (fresh process) reads
  that file's content **byte-for-byte** equal to what was captured; (d) the path
  is derivable by the hook without guessing (stable naming keyed on
  pipeline_id/state). Record the exact path convention.
- **FAIL:** if any of (a)–(d) fails, **STOP**. Do **not** substitute H-a
  silently. **Escalate back through brainstorm/orchestrator** with the spike
  evidence; D2 must be re-converged before the transcript-judge wiring proceeds.
- **Explicitly:** this checkpoint blocks the plan-stage cognition
  honour-check-carrying steps in Phase 1 (the spec-review/quality reader wiring).
  Phases 2's test-judge path and Phase 3 do not depend on Phase 0.

**Phase 1 — evidence readers + the Python advance entrypoint (test judge first).**
1. Add the `advance` subcommand dispatch to `src/gleipnir/preflight/__main__.py`
   (mirror the existing `bridge-status`/`config-scan` leading-token dispatch).
2. `src/gleipnir/preflight/advance.py`: `read_test_exit_code` (runs
   `bin/gleipnir-sandbox test -- --collect-only` at the caller edge), build
   `make_test_judge`, `Driver.resume_from_bridge` + `Driver.advance`. **Test
   transition wired first** (mechanical, no transcript dependency — de-risks the
   TS↔Python + fail-closed boundary before the hard case).
3. **[D2-spike-gated]** `read_reviewer_verdict` (reads the Phase-0-confirmed
   transcript path), build `make_spec_review_judge` / `make_quality_judge`, wire
   the SPEC_REVIEW and QUALITY branches.

**Phase 2 — TS post-tool handler (the trigger).**
4. Add `tool.execute.after` to `sequence-gate.ts` (or sibling `advance-hook.ts`):
   `isArmed` guard → read+validate bridge → `subagent_type == bound role for
   state` (D6) → shell out to `bin/gleipnir-preflight advance` → fail-closed on
   non-zero exit / any error (reuse the pre-tool catch-all pattern).

**Phase 3 — Seam 8 live fetch + GATE (D5 CONVERGED; no operator gate; does NOT depend on the D2 spike).**
5. **[D5 CONVERGED — build the sidecar as decided]** run-identity persistence via
   the `.gleipnir/var/run/pipeline-run.json` sidecar (framework-written,
   agent-read-only, **plain file, no own MAC** — integrity from the existing
   `.gleipnir/var/run/` grant class); wire the advance entrypoint to source
   `pipeline_id`+`head_sha` from it. Do **NOT** extend `StateMarker` (D5-marker
   rejected) and do **NOT** add a second digest scheme (integrity sub-question
   converged on filesystem-permission protection only). **The sidecar's
   `head_sha` is written by the git broker's server-side code** — the
   `commit_changes` tool in `src/gleipnir/broker/git/mcp_server.py` — as a side
   effect of the commit it already performs: that function already computes the
   new HEAD via `git rev-parse HEAD` (`mcp_server.py:367-368`) after a successful
   commit, so it writes that value into `.gleipnir/var/run/pipeline-run.json` in
   the same call. This is the broker *process's* write, NOT a `git-ops` agent
   tool call — `git-ops.md` grants `edit: deny`/`write: deny`, so the agent
   cannot and does not write the sidecar; the broker MCP server (framework
   server-side code, the same process that already holds the write path to
   `.gleipnir/var/run/`) does. This keeps the sidecar framework-written /
   agent-read-only, consistent with D5's converged grant class.
6. `src/gleipnir/preflight/fetch_attestation.py` + `fetch-attestation` dispatch:
   stdlib `urllib` GitHub Actions query for `head_sha`; conclusion→
   `AttestationStatus` map; construct `Attestation(pipeline_id, status)`; token
   from env (agent-unreachable).
7. GIT-state branch in the advance entrypoint: call the fetcher, then
   `Driver.attempt_gate(attestation)`; PENDING/ABSENT/RED → refuse, no advance
   (D7).

**Phase 4 — tests + honest docs.**
8. `tests/test_advance_hook.py`, `tests/test_fetch_attestation.py`; extend the
   TS golden-fixture test for the post-tool path; assert unarmed no-op,
   fail-closed on subprocess error, each judge's live wiring, status map,
   pipeline_id↔SHA correlation refusal, PENDING/ABSENT fail-closed.
9. Write the two D3 honest-tradeoff caveats into the code/docstrings (they are
   stated in this plan below and must land in the artifact text, not only here).

---

## Stress-test (acceptance checks — concrete and checkable)

1. **Armed advance, test transition:** with a PLAN/TEST-state bridge and a
   completed `gleipnir-code` `task`, the hook shells out; the bridge re-mints to
   the mapped next state; `bin/gleipnir-sandbox test -- --collect-only` exit 0 →
   PASS advance, non-zero → FAIL revert. Verified by `tests/test_advance_hook.py`.
2. **Armed advance, spec-review & quality transitions:** with the Phase-0
   transcript present, `SPEC-CONFORM: PASS` / two-pass grammar advances; absent
   or ambiguous transcript → `NEEDS_HUMAN`/`HUMAN_QUESTION`. (Gated on Phase 0.)
3. **Unarmed no-op:** `GLEIPNIR_PIPELINE` unset OR no bridge → handler never
   shells out; no bridge write; no fetch. Asserted explicitly.
4. **Fail-closed on subprocess error:** advance entrypoint exits non-zero → TS
   handler throws → delegation aborts (no silent allow).
5. **GATE only on GREEN+match:** `fetch-attestation` returns GREEN with matching
   `pipeline_id` → `attempt_gate` → GATE; RED/PENDING/ABSENT or mismatched
   `pipeline_id` → refuse, bridge stays GIT. `tests/test_fetch_attestation.py`.
6. **pipeline_id↔SHA correlation (Q4):** a GREEN run for SHA-A / pipeline A does
   NOT gate a pipeline B resumed with a different pipeline_id — `attempt_gate`
   refuses on mismatch. Asserted with a crafted mismatch.
7. **Status map:** each GitHub conclusion string maps to the correct
   `AttestationStatus` (table-driven test with fixture responses; no live
   network in the test — inject the parsed response).
8. **Tier-3 unreachability preserved:** `gleipnir-code`'s grants still deny
   `.gleipnir/**` and `src/gleipnir/preflight/**`; the new files live only under
   those denied paths + `bin/`; no grant is weakened. (Blast-radius attestation.)
9. **Engine purity preserved:** `git grep -n "import"` in `engine/__init__.py`
   shows no bus/urllib/subprocess import added; `driver.py`/`judges.py`/
   `engine/__init__.py` are byte-unchanged (call-site-only per D1).
10. **stdlib-only core:** the fetch module imports only stdlib (`urllib`, `json`,
    `os`); no GitHub SDK; `gh`, if used at all, only via `subprocess` at the edge.
11. **Full suite green** in the sandbox (`bin/gleipnir-sandbox test`), coverage
    at/above the 85% target for the new modules.
12. **Bridge byte-stability (D5-sidecar converged — this now unconditionally
    applies):** `tests/fixtures/golden_marker.json` and the TS
    `canonicalSigningInput` are unchanged; the golden-fixture conformance test
    still passes. (D5-marker was rejected, so `StateMarker`/the MAC signing
    input MUST stay byte-identical — this is now a hard acceptance check, not a
    conditional one.)

---

## Execution Workflow (for the implementing pipeline)

- **Routing / classification (see next section):** full 8-stage **hardened**
  pipeline. `quality-reviewer` runs BOTH the spec-conformance pass AND the
  blast-radius/false-success pass, PLUS the negative-check attestation (one row
  per grant/enforcement-touching change).
- **Order:** Phase 0 (spike) → go/no-go checkpoint → Phases 1–2 → Phase 3 →
  Phase 4. **One blocking gate remains:** the Phase-0 spike gates Phase 1's
  transcript-judge steps. **D5 is CONVERGED and no longer gates Phase 3**;
  Phase 3 does not depend on the transcript judges either, so it is ready to
  proceed per this sequencing.
- **One escalation that is NOT a silent fallback:** a failed D2 spike escalates
  D2 back through brainstorm/orchestrator (never auto-substitute H-a). D2 is
  already converged on H-c (caller deposits the reviewer's returned transcript);
  the spike verifies that H-c mechanism works, and a failure re-opens D2, it
  does not silently swap in H-a. (D5's earlier escalation is closed — the
  operator converged on D5-sidecar + plain-file integrity.)
- **Test-first:** author `tests/test_advance_hook.py` /
  `tests/test_fetch_attestation.py` interfaces before the implementation bodies
  (the test is the arbiter). Never weaken a test to make it green.
- **Verification:** `bin/gleipnir-sandbox test` (in-container, coverage). The
  `gleipnir-code` agent cannot write the Tier-3 files (`.gleipnir/plugins/**`,
  `src/gleipnir/preflight/**`) — those edits are operator/Tier-3-authored; the
  agent authors only `tests/**` and any non-denied `src/**`. **This split is
  itself a routing fact the orchestrator must honor:** those enforcement-code
  edits do not go to `gleipnir-code`.
- **The D5 broker edit is a distinct authorship case (verified grant fact).**
  The `head_sha` sidecar-write side effect lands in
  `src/gleipnir/broker/git/mcp_server.py`, which is **NOT** in `gleipnir-code`'s
  deny set (`gleipnir-code.md:12-17` denies `.gleipnir/**`, `.git/**`,
  `.github/**`, `src/gleipnir/preflight/**` — the broker path is absent), so by
  the current grant the code agent *can* edit it. It is nonetheless
  enforcement-bearing broker code (E-1 surface). The orchestrator should treat
  this edit as enforcement code and route it accordingly; whether to tighten
  `gleipnir-code`'s deny set to include `src/gleipnir/broker/**` is a Tier-3
  grant decision for the operator, out of this plan's Tier-0 scope — flagged
  here, not decided.

### The two D3 honest tradeoffs — STATED IN THIS PLAN'S OWN TEXT (must also land in the artifact docstrings)

- **(a) config-scan attests config-scoping, not full artifact correctness.**
  `.github/workflows/config-scan.yml` is the only CI surface today and it runs
  `bin/gleipnir-preflight config-scan` — it verifies the enforcement roster /
  `opencode.jsonc` is well-scoped, NOT that the pipeline's tests pass. Feeding
  its conclusion into the `Attestation` therefore attests **config-integrity,
  not that this pipeline's work is correct.** This is a **knowingly-accepted
  interim tradeoff.** GATE-on-green here means "config is well-scoped and CI
  ran green," not "the delivered artifact is fully verified." A broader
  full-`pytest`-in-sandbox CI workflow would be a separate later slice.
- **(b) E-1 credential isolation is cooperative-policy, not structural.** The
  GitHub token must be reachable by the `fetch-attestation` subcommand but NOT
  by any roster agent. Under the uncaged default this rests on the **same grant
  discipline** as the existing preflight CLI (`src/gleipnir/preflight/**` denied
  to `gleipnir-code`, token in an env var not exposed to agent tool calls) — it
  is **cooperative-policy, co-located**, NOT a structural boundary. E-1 becomes
  structural only under S-2 (credential unreachability via the substrate mount).
  **This plan claims no stronger guarantee than that.**

---

## Design Principles (Gate 1 — cognition layer; CASE (i): OOP/functional code)

`P ∩ X ≠ ∅` (touches `src/gleipnir/preflight/**`, `.gleipnir/plugins/**`,
`bin/**`, `tests/**`) and the touched members have class/function/module
structure (Python modules + functions; the TS handler). → full **SOLID + DRY +
SRP + Design Intent**.

**Single Responsibility (name each new component's one responsibility):**
- `advance.py::advance_main` — *one job:* rehydrate the driver at the bridge's
  current state and drive exactly one advance/gate step for that state. It does
  NOT source evidence itself (delegates to injected readers) and does NOT decide
  routing (the engine's `TRANSITIONS` does).
- `advance.py::read_test_exit_code` — *one job:* run the sandbox collect-only and
  return its raw exit code (or `None`). No verdict logic (that's the judge).
- `advance.py::read_reviewer_verdict` — *one job:* read the transcript file at
  the known Tier-1 path and return its text (or `None`). No parsing (the judge
  owns the grammar).
- `fetch_attestation.py::fetch_attestation(pipeline_id, head_sha) ->
  Attestation` — *one job:* query GitHub Actions status for `head_sha`, map
  conclusion→`AttestationStatus`, construct the `Attestation`. It does NOT call
  `attempt_gate` (that is the advance entrypoint's GIT branch) and does NOT
  persist state.
- `fetch_attestation.py::_map_conclusion(status, conclusion) ->
  AttestationStatus` — *one job:* the pure conclusion→status mapping (unit-
  testable without a network).
- TS post-tool handler — *one job:* decide "should this completed `task` trigger
  an advance?" and shell out; it holds NO advance/mint logic (that stays Python).

**SOLID.**
- **SRP:** as above — each component has exactly one reason to change (evidence
  format, GitHub API shape, trigger rule, and routing are four separate reasons
  living in four separate places).
- **Open/Closed:** the engine, driver, and judges are **not modified** (D1: call-
  site-only). New behavior is added by *new* modules that *use* the existing
  public `Driver`/judge APIs — extension without modification, provable by
  Stress-test #9 (byte-unchanged core files).
- **Liskov:** `fetch_attestation` returns an `Attestation` honoring the exact
  frozen contract `attempt_gate` already consumes (engine L462–499); no subtype
  substitution weakens the GREEN+match precondition.
- **Interface Segregation:** the judges' injected-reader interfaces
  (`Callable[[], str | None]` / `Callable[[], int | None]`) are already narrow;
  the new readers implement exactly those, nothing wider. The fetcher exposes a
  single `fetch_attestation(pipeline_id, head_sha)` — the minimal shape the GATE
  branch needs, matching the brief's "minimal shape both live options satisfy."
- **Dependency Inversion:** the high-level advance flow depends on the abstract
  `Judge` / reader callables, not on concrete evidence I/O; the I/O
  (subprocess, file read, urllib) is injected at the caller edge. `engine/`
  stays pure (no I/O, no bus, no urllib import — Stress-test #9).

**DRY.**
- Reuse `Driver.resume_from_bridge` / `advance` / `attempt_gate` / `write_bridge`
  and the three `make_*_judge` factories **unchanged** — zero re-implementation
  of advance, HMAC minting, or judge grammar (the brief's core D1 argument).
- Reuse the TS `isArmed` / `loadKey` / `validateMarker` / `BRIDGE_REL` from the
  existing pre-tool half rather than duplicating the bridge contract in a second
  place (co-locate pre+post in one plugin, or import the shared helpers).
- Reuse the `__main__.py` leading-token subcommand dispatch pattern for both new
  subcommands rather than a second CLI.
- The conclusion→status map lives in ONE named function `_map_conclusion`,
  reused by both the live path and its unit tests (no per-call-site copy).
- Constants (bridge path, key env, transcript path convention) are referenced
  from their single existing definitions, not re-literaled.

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**
> *The live advance/fetch wiring adds exactly one new I/O boundary per evidence
> class (transcript file read; sandbox exit code; GitHub status query) at the
> caller edge, and adds ZERO lines to `engine/__init__.py`, `driver.py`, and
> `judges.py`. Any implementation that (a) imports `subprocess`, `urllib`, or
> the bus into `engine/__init__.py`; or (b) edits `driver.py`/`judges.py` to
> change advance/judge behavior; or (c) lets an acting agent's self-reported
> text (rather than the independent `quality-reviewer` transcript or the
> mechanical sandbox exit code) reach a judge; or (d) constructs an
> `Attestation` from anything other than the `fetch-attestation` subcommand's
> GitHub-derived status — VIOLATES this intent and must be rejected at review.*

This is falsifiable: a reviewer can `git diff --stat` the three core files
(must be zero-changed), grep `engine/__init__.py` imports, and trace every
`Attestation(...)` construction and every judge's reader to its source.

---

## Return-to-orchestrator note

This plan is written to `.gleipnir/plans/seam7-seam8-wiring.md`. The one material
tradeoff it surfaced (D5, `pipeline_id` persistence) is now **CONVERGED**: the
operator decided **D5-sidecar** (build `.gleipnir/var/run/pipeline-run.json`,
framework-written/agent-read-only; D5-marker rejected) with **plain-file
integrity only** (no second HMAC/digest; relies on the existing
`.gleipnir/var/run/` agent-unwritable grant class). No material tradeoff remains
open. The only remaining blocking gate is the **Phase-0 D2 spike** — a hard
go/no-go that blocks Phase 1's transcript-judge steps; a spike failure escalates
D2 back through brainstorm/orchestrator, not a silent fallback (this is a
build-stage go/no-go, NOT an unresolved design decision for the operator). The
two D3 honest caveats are stated in this plan's own text (§ Execution Workflow)
and are required to land in the artifact docstrings.
