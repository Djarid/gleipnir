# Plan A — signer service-account provisioning + the launchd feasibility spike

**Stage:** `plan` (`gleipnir-plan`). **This document is a clean rewrite**, authored
from the converged briefs rather than patched from an earlier draft. It
deliberately reuses none of the prior draft's numbering or structure.

**Input briefs (read in full this session, unpatched sources of truth):**

- `.gleipnir/plans/signer-uid-separation-brainstorm.md` (1786 lines) — the parent
  brief, **8 of 8 decisions converged**, including both amendments to Decisions 4
  and 8 (read in their current amended form).
- `.gleipnir/plans/signer-key-construction-scope-brainstorm.md` (964 lines) —
  **CONVERGED on Approach D** (per-construction Ed25519 scoping via predicate P).
  Its `## Relationship to Plan A` (`:901-917`) states, verified: *"Nothing in
  this brief changes Plan A's scope."*
- Style precedent: `.gleipnir/plans/tier3-mcp-approval-launcher.md` and
  `.gleipnir/plans/approval-listener-fail-loud.md` (both shipped through real
  spec-review + `quality` this session).

**What Plan A is.** Two things, and nothing else:

1. Provision a dedicated non-login **signer** macOS service account + group via a
   new, parallel `ansible/signer.yml` (brief Decision 5 / 1B), sharing
   account-creation logic with `site.yml` through **one extracted, parameterised
   task-file both playbooks consume** (operator approval **OA-1**, "genuine
   adoption", not a duplicated fallback).
2. Run a **launchd feasibility spike** proving — or disproving — on **this actual
   host** that a launchd-managed process running as that signer uid can execute
   `.venv/bin/python -m gleipnir.approval.mcp_server` and bind `127.0.0.1:8765`,
   testing **both** plausible plist placements with **no pre-asserted winner**.

**What Plan A is NOT.** It touches **no cryptographic construction, no key
format, no reader call site, and not `opencode.jsonc`**. The Ed25519 migration
(Approach D, constructions #1/#2) is **Plan B** — named here, not planned here.
Plan A also delivers **no key confidentiality and no isolation**; see the
§Honesty ledger.

---

## Decisions (index)

Rows **C1–C6** are converged decisions this plan **records and cites, never
re-decides**. Rows **J1–J25** are `[PJ]` (`[PLAN-STAGE JUDGMENT]`) calls made
during Architect/Trace, each flagged for spec-review; **J8, J10 and J14 are
called out for explicit operator acknowledgement** (see §Judgment calls needing
operator acknowledgement). Full reasoning for every row is in the sections below.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| C1 | Launch mechanism | **2C — launchd** (`UserName`/`GroupName`); the signer is never a child of the agent process | 2A `sudo -u` + sudoers; 2B setuid wrapper | Parent brief **Decision 4** (matrix winner, 502). 2A's `NOPASSWD` rule is invocable by the agent uid; 2B is a sharper liability than what it replaces. **Recorded, not re-decided.** |
| C2 | Provisioning shape | **1B — a parallel `ansible/signer.yml`**; `group_vars/all.yml`'s single-identity invariants NOT widened | 1A — extending `ansible/site.yml`'s acts | Parent brief **Decision 5**, grounded in F-5: `site.yml` performs a privilege **DROP**, the signer needs a privilege **ACQUISITION**. Keeps the green caged AC-4 gate out of the blast radius. **Recorded, not re-decided.** |
| C3 | Spike status | **REQUIRED, AUTHORIZED first step** — not optional, not deferrable | Committing implementation effort to 2C on documentation alone | Parent brief **Decision 6**. Closes the brief's own Dunning-Kruger flag: launchd `UserName` with a non-login account + a repo-local `.venv` interpreter was asserted from docs and **never probed on this host**. **Recorded, not re-decided.** |
| C4 | Honesty constraint | Signer-uid separation binds meaningfully **only in caged mode**; O-3(b)'s implied uncaged value is **qualified, not inherited** | Letting any artifact imply uncaged isolation | Parent brief **Decision 7**, explicitly accepted and binding on this plan stage. See §Honesty ledger. **Recorded, not re-decided.** |
| C5 | Ed25519 migration scope | **Approach D — per-construction, via predicate P**: #1/#2 migrate; #3/#4 stay symmetric but isolated. **Entirely Plan B; out of scope here** | Folding any part of it into Plan A | Sibling brief `## Converged` (`:563-594`). Plan A touches no construction, so nothing here depends on it. **Named as a follow-on only.** |
| C6 | Shared-task adoption | **OA-1 — one extracted, parameterised task-file that BOTH `signer.yml` and `site.yml` consume** ("genuine adoption") | A signer-only copy of the account-creation commands, leaving `site.yml` duplicating them | Operator approval OA-1, this session, discharging Decision 5's *mandated* fix for 1B's DRY con ("extract one shared, parameterised 'create a macOS service account' task-file"). A signer-only copy would leave the con unpaid. **Consequence: `site.yml` IS edited — exactly once, at act 1.** See J8/J14. |
| J1 | **`[PJ]`** Scratch-artifact location + creation semantics | **All spike artifacts under `/private/tmp/gleipnir-signer-spike/`**, created by a bare `mkdir` (no `-p`, no `creates:`) so a pre-existing path **fails EEXIST** | Anywhere inside the repo (incl. `.gleipnir/var/tmp/`); a `stat`-then-create check | Verified: `site.yml` act-3 applies `owner: {{ operator }} … recurse: true` to **`{{ repo }}`** entire (`site.yml:165-171`) and `chgrp`+`g+w` recursively to `.gleipnir/var/tmp` (`:209-216`, `group_vars/all.yml:34`). A scratch key anywhere in the tree would be **silently re-owned by a later `site.yml` apply**. `mkdir(2)` is atomic, so bare `mkdir` is genuine exclusive creation; check-then-use can silently adopt a path a prior aborted run left behind. |
| J2 | **`[PJ]`** Spike structure | **Two stages: (1) a capability probe, then (2) the real module** — stage 2 runs only on a placement stage 1 proved runs at the signer uid | One attempt that runs `-m gleipnir.approval.mcp_server` and infers everything from it | Under launchd `stdin` is `/dev/null`, so `mcp.run(transport="stdio")` reads EOF and returns, and the listener is a **daemon** thread that dies with the process — a single attempt cannot separate "launchd could not run this at the signer uid" from "the module exited because its stdio peer was absent". The probe answers uid / interpreter / env / key-readability / port-bind unambiguously; stage 2 then answers the module-specific question honestly. **An early stage-2 exit attributable to stdio EOF is a Plan-B input, not a Plan-A failure** — but only when **J18**'s evidence and **J19**'s taxonomy positively establish that attribution. |
| J3 | **`[PJ]`** Probe authorship + home | The probe (`signer-probe.py`) is **operator-authored into the scratch dir**; its content is given verbatim in §Ready-to-apply artifacts | Adding it to the repo tree for `gleipnir-code` to author | It must not live in the repo (J1: `site.yml` would re-own it; it is throwaway). No in-framework agent can write outside the repo, so this is an operator act by capability, not by convention. |
| J4 | **`[PJ]`** Placement testing | **Two arms, no pre-asserted winner** — arm A `~/Library/LaunchAgents/` (gui domain), arm B `/Library/LaunchDaemons/` (system domain). Result recorded as an **outcome matrix**, not pass/fail | Testing only the placement documentation suggests; recording a single boolean | Decision 6 exists precisely because neither placement was ever probed here. A criterion requiring a *specific* arm to win would convert an informative empirical result into a manufactured failure. **"Wrong uid" and "neither arm ran as the signer" are valid, informative NEGATIVE findings.** |
| J5 | **`[PJ]`** F-1-class negative control, **CONDITIONAL on a baseline existing** | A **4-step ordered protocol**: working baseline → deliberately break key access → capture the **specific** permission denial → restore and re-prove the baseline. **Precondition: at least one candidate achieved a working signer-uid execution.** If none did, the control is **N/A-BY-DESIGN** with an explicit "attempted; no baseline existed to break" record | A single "make it fail and check it failed" step; **or** an unconditional MUST-PASS | A control that only ever observes a failure cannot distinguish "the break caused it" from "it never worked" — hence the required *specific* `Errno 13` **plus the exact key path**. But the conditionality is **logically forced**: J4 accepts "neither arm ran as the signer uid" as a valid negative finding, and in that world **step 1 (the working baseline) is unobtainable**, so an unconditional MUST-PASS would be **mandatory-but-unattainable** — it would convert J4's honest negative into a manufactured Plan-A failure, the exact contradiction J4 exists to prevent. **N/A-BY-DESIGN is an honestly-reported outcome, NOT a silent skip and NOT a FAIL**; where a baseline DOES exist the four steps remain **mandatory and unweakened**. |
| J6 | **`[PJ]`** Env-inheritance test + conclusion scope | **Two arms**: E1 a plist-**declared** variable; E2 a variable set **only in the bootstrapping shell** and NOT declared. Conclusions scoped to exactly these two | Testing only the declared form and concluding "launchd does not inherit shell env" | With the shell variable never set, the declared-only test supports **no** claim about inheritance — only about declaration. E2 is what licenses an inheritance conclusion at all. In **no** case may either arm license a claim about opencode's own environment. |
| J7 | **`[PJ]`** Inter-attempt hygiene | Between **any** two attempts (different arm, different stage, or a retry): explicitly `bootout` the previous label, then prove `127.0.0.1:8765` is free, **before** bootstrapping the next | Assuming a prior attempt released the port | A port left occupied by a prior attempt (or by the session's own opencode-spawned listener) would be recorded as the next candidate's own inability to bind. **An occupied port at attempt start is a TEST-SETUP failure and the attempt is void** — never a candidate's feasibility result. |
| J8 | **`[PJ]`** Account/group guard | **Three-way**: absent → create; present-and-all-attributes-match → skip (`changed=false`); present-with-ANY-mismatch → **`fail` naming the attribute, expected vs found**. Applied **uniformly** in the shared task-file | The naive two-way `dscl_query.rc != 0` guard (today's `site.yml:103-139` shape), which silently adopts a mismatched account | Silently adopting a wrong account is the failure worth a loud stop: it is how a signer uid ends up with a login shell or the wrong gid and nobody notices. **⚠️ Consequence needing operator acknowledgement:** because `site.yml` adopts the same task-file (C6), this **upgrades `site.yml` act-1's guard from 2-way to 3-way**, adding a new fail path to the caged-gate playbook. Alternative considered and rejected: a `svc_strict_attributes` flag defaulting false for `site.yml` — rejected because a per-caller strictness knob is exactly the "shared abstraction straining to cover both polarities" Decision 5 warns about, and because fail-loud is this repo's standing posture. **Named, not buried.** |
| J9 | **`[PJ]`** Teardown shape | A separate **`ansible/signer-teardown.yml`**, gated on a **creation manifest** (`created.env`) written by `signer.yml`, removing **only** what that run created — account **and** group, scratch root, both plists, both launchd labels | Destructive tags inside `signer.yml`; or an unconditional teardown that removes whatever it finds | "Remove only what this execution created" is unimplementable without a record of what was created; guessing would delete a pre-existing group. **Manifest absence is resolved by the THREE receipt states (J21), not by a flat refusal:** `created.env` **present** ⇒ perform the gated **teardown**; `created.env` **absent + the receipt `/private/tmp/gleipnir-signer-spike.torndown` present** ⇒ a **VERIFIED clean no-op** (quote the receipt, remove nothing, exit 0); `created.env` **absent AND the receipt absent** ⇒ **REFUSE LOUDLY** rather than guessing. The fail-loud-on-unknown-state posture is unchanged — it is the *unknown* case (both absent) that refuses; a receipt makes the state **known**. |
| J10 | **`[PJ]`** `.gleipnir/signer-identity.env` survives teardown | **Retained** — it records the chosen free uid/gid so Plan B reuses the same identity. Explicitly excluded from teardown's absence checks | Deleting it with everything else | It is a *record of a chosen number*, not a created OS object, and nothing is held open by its existence. **⚠️ Named for operator acknowledgement** because it is one of **THREE** deliberate exceptions to "verify absence of everything created" — the others being the **teardown completion receipt** `/private/tmp/gleipnir-signer-spike.torndown` (J21, placed outside the scratch root *so that* it survives) and any **retired-receipt** `…torndown.retired-<UTC>` from step 11a. Those three, and only those three, are the legitimate survivors; an unexplained surviving file outside that set is exactly what a teardown criterion should catch. |
| J11 | **`[PJ]`** `signer.yml` idempotency is **scoped** | Idempotent for every act **except** the deliberately-exclusive scratch-root act: re-run with `--skip-tags spike_scratch` ⇒ `changed=0`; re-run **with** it ⇒ **must FAIL EEXIST** (that failure is a PASS of the exclusivity criterion) | Claiming blanket idempotency; or making the scratch act idempotent | Exclusive creation and idempotent re-run are genuinely in tension, and J1 resolves the tension in favour of exclusivity. A blanket "idempotent" claim would be false; the scoped claim is checkable in both directions. |
| J12 | **`[PJ]`** Who authors vs who runs `signer-static.sh` | **`gleipnir-code` AUTHORS** it (and the broken fixtures); the **OPERATOR RUNS** it and captures pass/fail | Having `gleipnir-code` run it and report | **Verified capability fact:** `gleipnir-code.md:34-62` is `bash: "*": deny` with an allowlist containing **only** `bin/gleipnir-sandbox test\|lint [--profile python\|broker\|node\|pi]`. There is **no route** for it to execute `sh ansible/tests/signer-static.sh`, and no `ansible` sandbox profile is granted. Authoring is `edit`, which it does hold (`ansible/**` is outside its deny list, `:12-28`). |
| J13 | **`[PJ]`** `.gitignore` addition | Exactly **one** new line, `.gleipnir/signer-identity.env`; **operator-applied** | A `.gleipnir/*.env` or `*.env` glob; leaving the file trackable | Verified: `.gitignore:17` ignores `.gleipnir/agent-identity.env` by **exact path**, not a glob — the precedent is exact-path. A glob would silently start ignoring future `.env` files, including any that ought to be audited. `.gitignore` is an **always-hardened exact-path member of enforcement-path set `E`** (`stage-role-map.md` Axis 2(a)), so it is operator/build-mode territory. |
| J14 | **`[PJ]`** `site.yml` regression proof | Three layers: (a) `sh ansible/tests/run.sh` all green; (b) real-box `site.yml --tags act1` applied **twice**, both `changed=0`; (c) **one** full real-box `sudo ansible-playbook site.yml`, AC-4's verdict recorded — and the **authoritative** real-key re-verification immediately after (c) | Only the fixture harness; or a pre-change/post-change pair of full real-box applies | (a)+(b) isolate the changed act (act 1 is the only edited act) and prove the present-and-matches skip survived the extraction. (c) is retained because it is **the one place a mistake could actually touch the real key** — `site.yml` carries the real recursive ownership/permission tasks and act-5's key lock. **⚠️ Named for operator acknowledgement:** (c) mutates real repo ownership/permissions and runs the caged AC-4 assertion; a *pre-existing* AC-4 failure may surface here — but it may be **CALLED** pre-existing **ONLY** by comparison against **step 0b's recorded `AC4-BASELINE:`** (§Assemble step 0b), i.e. **only if step 0b recorded `AC4-BASELINE: FAIL` with the SAME assert message**. If step 0b recorded `AC4-BASELINE: PASS`, a failure here **IS this plan's regression**. If step 0b was never captured, the question is **permanently unanswerable** and **no** pre-existing claim may be made. **SC-1 and (b) are CORROBORATING discriminators only — neither, alone or together, licenses a pre-existing attribution without the step-0b baseline comparison.** |
| J15 | **`[PJ]`** Pipeline routing | **FULL 8-stage pipeline**, **plus** the hardened-path review obligations: two distinct `quality` verdicts and a **5-row negative-check attestation** with `attested_by ≠ author` | The light prose/config track; the hardened prose/config track | Mechanical (`stage-role-map.md` Axis 1): `P` contains standalone `*.yml` **and** `*.sh`, both explicit members of disqualifier set `X` ⇒ full pipeline; Axis 2 is not reached (it routes only *track-eligible* plans). The attestation is imported **deliberately** as a plan-level acceptance criterion because `P` also touches `.gitignore` ∈ `E` and because account provisioning **creates real OS-level privilege** — the exact class the attestation exists to catch. See §Routing. |
| J16 | **`[PJ]`** Honesty ledger | Plan A claims **zero** key confidentiality, **zero** isolation, and does **not** close O-3(b) or fix `caged + armed`; the named `caged + armed` interim gap is carried verbatim | Letting "the signer has its own uid now" stand unqualified | C4 is binding, and the sibling brief's Q2 acceptance is **conditional on the gap being documented as a NAMED gap** for the whole interim. An unqualified claim here is a **non-conformance**, not a stylistic quibble. |
| J17 | **`[PJ]`** Preserve AC-nolit's coverage after the extraction | Extend `layer1-static.sh`'s AC-nolit file list to include `ansible/tasks/create-service-account.yml` | Leaving AC-nolit pointed only at `site.yml` + `group_vars/all.yml` | **Real finding:** AC-nolit (`layer1-static.sh:73-80`) greps only `site.yml` and `group_vars/all.yml` for a numeric uid literal. The extraction **moves the uid/gid-bearing lines out of both files**, so the invariant would silently stop covering the code it exists to guard — a hollowed-out green test. One-line fix; `ansible/tests/**` is `gleipnir-code` territory. |
| J18 | **`[PJ]`** Stage 2 must supply the env var the **real** module reads, and must be independently observable | Stage 2's plist declares **`GLEIPNIR_MARKER_KEY_FILE`** (pointing at the **scratch** key), and stage 2 launches the module through a thin operator-authored **wrapper** (`<root>/stage2-wrap.sh`) recording argv, uid/gid, `sys.executable`, which key env vars are present, and the module's **exit status** | Declaring stage 1's `GLEIPNIR_SPIKE_KEY_FILE`; launching `-m gleipnir.approval.mcp_server` directly and inferring the exit cause from silence | **Verified fact:** the module resolves its key via `load_key(None)` → `os.environ.get(KEY_ENV_VAR)` with `KEY_ENV_VAR = "GLEIPNIR_MARKER_KEY_FILE"` (`src/gleipnir/verify/marker.py:40,95-99`). `GLEIPNIR_SPIKE_KEY_FILE` is read by **nothing but the throwaway probe** (`signer-probe.py`), so a stage-2 plist declaring only that name supplies the real module **no key at all**: it dies of `KeyUnavailable`, and that missing-key artifact would be misread as launchd/stdio evidence — destroying stage 2's whole purpose. The wrapper is required because **the only diagnostics specified anywhere are the probe's**, and stage 2 does not run the probe: without it nothing observes the real module's uid, interpreter path or exit cause, so "it exited early" is attributable to nothing. The wrapper touches **no production source** — a throwaway scratch-root file, same class as the probe (J3). |
| J19 | **`[PJ]`** Stage-2 exit-cause taxonomy — missing-key ≠ stdio-EOF, and **exit-status-0 proves nothing** | Every stage-2 attempt is classified into **exactly one** of **six** named outcomes, each with its own required evidence: **(a) SETUP-DEFECT/missing-key**, **(b) SETUP-DEFECT/key-unreadable**, **(c) NEGATIVE/wrong-uid-or-exec**, **(d) EXPECTED/stdio-EOF-with-healthy-listener**, **(e) POSITIVE/bound**, **(f) INCONCLUSIVE** — the attempt produced neither a listener-level discriminator line nor a bind observation, so nothing is attributable. **(e) requires BOTH correct-uid AND live-bind** (J25's identity gate: a bind at the wrong uid is **(c)**, never **(e)**) | A binary "started / exited early" reading; **or a five-way taxonomy with no INCONCLUSIVE bucket**; **or letting an unconditional bind observation classify a wrong-uid attempt as (e)** | (a) and (d) are exactly the collapse this taxonomy prevents: a `KeyUnavailable` and a clean stdio-EOF return are **both** "the process exited quickly **with status 0**", but (a) is a **defect in the attempt** (VOID; fix the plist and re-run) while (d) is the **pre-declared informative** result. **Verified in source, and this is the load-bearing fact:** `_run_listener` (`mcp_server.py:298-314`) wraps `register_default_resolvers()` + `run_server(...)` in `except Exception`, and on a fatal `KeyUnavailable` it logs at ERROR, calls `mark_unavailable()`, and **returns normally without re-raising** — the daemon thread exits and the process does **not** crash. `__main__` (`:348-350`) starts that thread and then calls `mcp.run(transport="stdio")` on a **separate code path**; under launchd `stdin` is `/dev/null`, so `mcp.run` reads EOF and returns, and the process **exits 0**. Therefore **"the process exited cleanly" is NOT evidence that the key loaded or the listener started** — the two paths never interact. The only positive discriminators are (i) the listener's own stderr line (`logger.error`/`logger.warning` reach stderr via `logging.lastResort`, which is level WARNING, even with no logging config): `"listener thread exiting fatally"` ⇒ (a)/(b), `"exiting without a bound listener"` ⇒ EADDRINUSE ⇒ a J7 test-setup fault, and (ii) a live `lsof` bind observation ⇒ (e). **(f) exists because neither is guaranteed to appear:** the listener runs on a *daemon* thread, and if `mcp.run` returns on EOF before that thread reaches its `except`, the interpreter tears the daemon thread down and **no line is written at all**. E-8 already allows exactly this ("otherwise it is inconclusive and recorded as such"); without an (f) bucket the taxonomy would force that real case into (d), re-creating the very collapse it exists to prevent. |
| J20 | **`[PJ]`** Per-attempt log isolation | **Every arm/stage/attempt gets its OWN log destination**: `<root>/logs/<attempt-id>/` where `<attempt-id>` = `NN-<arm>-<stage>-<UTC timestamp>`, created fresh per attempt; the plist's `StandardOutPath`/`StandardErrorPath` are **rewritten per attempt** to point into it | Reusing `agent.{out,err}` / `daemon.{out,err}` across attempts | **Real defect this closes:** every presence-based check in this plan ("the log contains `Errno 13`", "the log evidences the signer uid") is satisfiable by a **stale line from an earlier, unrelated attempt** if the file is reused — a false pass by construction, and the negative control (J5) is the most exposed because its whole discriminator is a specific string appearing or not appearing. A fresh directory per attempt makes a check satisfiable **only** by that attempt's own output. Also fixes the arm-B plist/collection **filename mismatch** (template wrote `agent.*`, collection read `daemon.*` — under J20 both derive from the same `<attempt-id>`, so they cannot disagree). Proven by **SC-19**. |
| J21 | **`[PJ]`** Teardown completion receipt lives OUTSIDE the scratch root | Teardown writes **`/private/tmp/gleipnir-signer-spike.torndown`** (a small receipt: UTC timestamp + the account/group/root/plist/label names it removed + the `created.env` it consumed, **copied verbatim into the receipt**) as its **final** act; a second teardown run reads the receipt and reports a **verified** clean no-op | Keeping the manifest inside the scratch root and treating "manifest absent" as "successfully torn down" | **The manifest is deleted by the very teardown that needs it**: `created.env` is inside `<root>`, and teardown removes `<root>` entire — so a second run has neither manifest nor any way to tell "already clean" from "unknown state". Treating absence as success would **invert** the manifest's fail-loud-on-unknown-state purpose (J9), which is the one property that stops teardown guessing. **Option (a) chosen over any in-scratch or state-database mechanism because it is strictly simpler**: one file, one path, written once, outside the blast radius, and it makes the three states genuinely distinguishable — manifest present ⇒ **teardown**; manifest absent + receipt present ⇒ **verified no-op**; manifest absent + receipt absent ⇒ **REFUSE LOUDLY** (unchanged J9 posture). The receipt is in `/private/tmp`, never the repo, and is removed only by the operator. |
| J22 | **`[PJ]`** Provenance covers the operator-created plists/labels too, and survives reruns | `created.env` is **append-only provenance**, written in **two phases**: phase 1 by `signer.yml` (`ACCOUNT_CREATED`, `GROUP_CREATED`, `ROOT_CREATED`), phase 2 by the **operator**, in **two separately-triggered halves**: `PLIST_x_CREATED`/`PLIST_x_PATH` recorded ONLY after **that plist FILE write itself** succeeded, and `LABEL_x_CREATED` recorded ONLY after **that `launchctl bootstrap` call itself** succeeded — **never both at once, and never at file-write time**. A **pre-existing-collision check runs BEFORE each write/bootstrap**, and a **bootout/bootstrap against an already-present label additionally requires an INDEPENDENT `LABEL_x_CREATED=true` check for that specific label** — plist-file ownership is **NEVER** sufficient authorization for a label operation (see §Label ownership). A rerun **CONFIRMS an already-recorded flag, never overwrites it** | A manifest written once by the playbook and never extended; no collision check; **recording `PLIST_x_CREATED` and `LABEL_x_CREATED` in the SAME step at plist-write time, before any bootstrap has been attempted**; authorizing a label bootout/bootstrap from `PLIST_x_PATH`/`PLIST_x_CREATED` alone; reruns free to recompute flags | The plists and labels are created by the **operator, after** phase 1 exists — so under the original shape teardown removed plists whose provenance it never recorded, i.e. exactly the "delete something pre-existing" failure `created.env` exists to prevent (J9). The collision check (`test -e <plist path>`; `launchctl print <domain>/<label>`) must precede creation, because **after** creation the two cases are indistinguishable. The rerun rule is the L-C7-class trap: a second `signer.yml` run finds the account **present-and-matching** and would naturally record `ACCOUNT_CREATED=false`, **flipping a true record to false** and stranding a real account teardown would then refuse to remove. Hence: **first writer wins; a rerun asserts agreement and fails loudly on disagreement.** Proven by **SC-20**. |
| J23 | **`[PJ]`** Broken fixtures are **complete, otherwise-passing trees**, and the harness asserts the **specific** reason | Each of the **7** broken fixtures is a **full copy of the correct fixture tree** differing by **exactly one** deliberate defect; `signer-static.sh` emits a **reason token** per failing check (`FAIL[S<n>/<reason>]`), and the harness asserts **that exact token** — plus asserts **every other check PASSED** in that fixture | Minimal single-file fixtures containing only the defect; asserting a nonzero exit status | **The defect this closes is a false-positive test suite.** `signer-static.sh` examines **four** files per run; a fixture containing only its one defective file makes **every other check FAIL for absence** — so all four original fixtures would have gone red **without the intended check ever detecting anything**, and the suite would have "proven" checks that could be entirely broken. A complete tree + exact-token assertion + "all other checks green" is what makes each fixture prove **its named check catches its named defect**. New fixtures **F5/F6** cover the S4 mismatch-guard control-flow check and **F7** the S6 provenance/removal-gating check — both previously **uncovered** by any fixture. |
| J24 | **`[PJ]`** SC-12's regression proof must actually execute the changed code path | (a) **explicit `-i inventory.ini` on every act-1 command**; (b) the include carries **`apply: tags: [act1, user_create, destructive]`** so the shared file's tasks are genuinely selected, **plus** an **execution-transcript** proof (step 15(b2)) that the query/attribute-comparison tasks **genuinely executed and were NOT skipped** — superseding this row's original `--list-tasks` proposal, which is **verified unable** to expand dynamic `include_tasks` bodies; (c) the existing **`--skip-tags destructive`** / check-mode fixture pattern preserved verbatim; (d) an AC-4 failure is **never** labelled "pre-existing" without a **before/after** comparison | `--tags act1` with no inventory; trusting tag inheritance through `include_tasks`; assuming an AC-4 failure here is unrelated; accepting *"the task was selected into the run"* as *"the task's guard logic executed"* | **Three verified defects.** (a) `site.yml`'s own documented invocation is `ansible-playbook -i inventory.ini site.yml` (`:20-21`) and the play targets `hosts: local`, defined **only** in `inventory.ini` (`:7-8`) — without `-i` the play matches **no host**, so `changed=0` means *"nothing ran"*, not *"nothing needed changing"*: a **vacuous pass**. (b) **Verified Ansible semantics:** tag inheritance does **not** apply to dynamic `include_tasks` — "tags on an `include_*` task apply only to the include itself, not to any tasks within the included file"; the documented workarounds are `apply:` or a wrapping `block:`. So a bare `--tags act1` include would run the include and **skip every task inside it** — reporting `changed=0` while never executing the extracted guard/provisioning logic **at all**, the precise hollow-green this proof exists to prevent. (c) `layer3-idempotency.sh:46-60` relies on `--skip-tags destructive` to exclude act-1's uid/gid creation from the fixture runs (`:6-7,16-21`); the extracted tasks **must** keep the `destructive` tag (via `apply:`) or that harness silently starts trying to create real OS accounts. (d) AC-4 asserts the **whole** caged boundary, not just act 1, so a failure here is **not** self-evidently unrelated to this change. |
| J25 | **`[PJ]`** The stage-2 classifier must be an ORDERED, MUTUALLY-EXCLUSIVE procedure; **no silence may be promoted to success**; **a SETUP FAULT must be voided before any result-bearing row**; and **the IDENTITY check must precede any row that can terminate as POSITIVE** | The §`stage2-classify.md` table is an **ordered decision procedure — first matching row wins** — so no attempt can satisfy two rows or receive two classes. The order is **setup-fault → identity → bind**: **ROW 1 is the EADDRINUSE/setup-fault VOID gate** (it fires even when the uid is also wrong — that pairing is a *port-conflict harness fault*, and voiding is right whatever uid it ran as), **ROW 2 is the uid/identity gate**, ahead of the bind row, and the POSITIVE row **additionally restates the identity conditions in its own right**: a genuinely positive class requires **BOTH correct-uid AND live-bind**. A **healthy/positive** class requires **AFFIRMATIVE evidence the listener bound**: `WRAP-BIND-LIVE yes`, i.e. **this child's own PID** observed holding a LISTEN socket on `127.0.0.1:8765` **while the child was still alive** (`lsof -nP -p <child> -a -iTCP:8765 -sTCP:LISTEN`, polled from the wrapper **before** `wait`). Bucket **(d)** is reachable **only** as a refinement of that bind-plus-identity row; everything unaffirmed is **(f) INCONCLUSIVE**. The post-`wait` `WRAP-BIND-AFTER` port check is **REMOVED as unsound** | An unordered table with overlapping rows; classifying "correct uid + executable interpreter + readable key + no fatal line + no bind" as **(d) healthy**; **accepting a bind observation UNCONDITIONALLY in the first row and deferring the wrong-uid discriminator to a later row a live-bind result would never reach — which would classify a WRONG-UID bind as POSITIVE**; **or hoisting the identity gate ABOVE the setup-fault row, which lets a wrong-uid-AND-no-bind attempt (the port-conflict signature) be filed as a candidate `(c)` instead of VOIDED**; inferring a bind from a port check taken **after** `wait` reaped the child | **Three distinct defects, all fixed here.** (1) **Contradictory rows:** the earlier table simultaneously required INCONCLUSIVE when neither a bind nor a listener line existed *and* classified essentially that same unobserved-listener case as **(d) healthy** — two rows overlapping and **disagreeing**. Ordering + first-match-wins makes exclusivity structural rather than a matter of reading order. (2) **(d) was silence promoted to success:** the wrapper's `WRAP-UID` / `WRAP-SYS-EXECUTABLE` / `WRAP-KEY-READABLE` lines are all emitted **before** the child runs, so they are **evidence about the wrapper's environment, not about the listener**. A module-level import failure (`ModuleNotFoundError`, or any exception on a path that never reaches the listener's own `logger`) satisfies **every** stated (d) condition with **no listener ever started** — so (d) certified a healthy listener from its absence of complaint. (3) **`WRAP-BIND-AFTER` did not prove what it claimed:** run *after* `wait`, the child is reaped and its sockets closed, so a non-zero count may be **any other process** (notably the session's own approval MCP — the very thing J7 detects) and a zero count is equally consistent with "bound, then exited". It answered a different question than the one asked and is deleted, replaced by the PID-intersected live poll. |
| J26 | **`[PJ]`** The complete broken fixture trees must be EXCLUDED from the EXISTING production `ansible-lint` pass | Add an **`exclude_paths:`** key to **`ansible/.ansible-lint`** naming **exactly** `ansible/tests/fixtures/broken/` (the one deliberately-broken tree), leaving `skip_list: [name[casing]]` and every lint **rule** untouched | Globally suppressing the offending rules (`ignore-errors`, etc.) in `skip_list`; leaving the fixtures in the lint path and letting the production pass go red; deleting the fixtures | **A real, verified conflict this plan otherwise creates.** Verified on disk: `ansible/tests/layer1-static.sh:37-47` runs **`ansible-lint "$root"`** where `root=$(cd "$here/.." && pwd)` (`:17`) — i.e. the **whole `ansible/` directory**, recursively — and the real `ansible/.ansible-lint` (31 lines, read) contains **only** `skip_list: [name[casing]]` with **no `exclude_paths` key at all**. J23 makes the seven fixtures **complete trees** of real playbook YAML under `ansible/tests/fixtures/broken/`, and F6's defect is literally **`ignore_errors: true`** — a rule the repo deliberately does **NOT** suppress (`.ansible-lint:24-29` explicitly records that `ignore-errors` is *"intentionally NOT in this list"* because the real violation was fixed in code). So the intentionally-broken fixtures would land squarely in the existing production lint's discovery path and turn **AC-lint red**, while this plan simultaneously requires that pass to **stay green** (SC-12(a)). Both requirements are real; only a **scoped path exclusion** satisfies both. A `skip_list` suppression is rejected outright: it would disable the rule for `site.yml` and every future playbook, silently undoing `.ansible-lint`'s recorded BUG-4 decision — trading a fixture problem for a **production** blind spot. Proven by **SC-22**. **Step-4 amendment:** `ansible-lint` resolves `exclude_paths` relative to the **invocation cwd (repo root)**, not the config-file directory — verified at step 4 (`tests/fixtures/broken/` excluded nothing, 58 violations remained; `ansible/tests/fixtures/broken/` gave exit 0); operator converged on **`ansible/tests/fixtures/broken/`**, still exactly the single broken subtree (no broadening). |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`goals/manifest.md`):** "Plan format" (`plan-format.md`) and
  "Methodology (ATLAS/GOTCHA ahead of planning)" apply and are followed —
  Decisions index / Architect / Trace / Link / Assemble / Stress-test /
  Execution Workflow / Design Principles all present. No pipeline-sequencing
  goal is authored or assumed (G-5 rule respected).
- **Order:** plan-before-code confirmed. This is the `plan` stage; it produces
  **only** this file. No YAML, no shell, no OS act, no Tier-3 write here.
- **Layer placement (GOTCHA):** primarily a **Tools/Args-layer** change — a new
  provisioning artifact and a launchd process definition, with a real Args-layer
  concern (the plist's `EnvironmentVariables` is the *only* channel by which a
  launchd-started process learns a key path; getting it wrong re-triggers F-1's
  silent keyless-start path). It touches the **S-2/G-1 posture** (it creates the
  uid a future caged posture would grant the key to) but **closes no guard**, and
  does **not** amend G-5.
- **Gaps and factual findings named (mechanical, not material tradeoffs):**
  1. **`ansible/tasks/` does not exist** (verified: `ansible/` contains
     `site.yml`, `group_vars/all.yml`, `inventory.ini`, `.ansible-lint`,
     `README.md`, `tests/`). The shared task-file is its first member —
     **to be created**.
  2. **`.gleipnir/signer-identity.env` does not exist** (verified: the only
     `*identity*` match under `.gleipnir/` is `agent-identity.env`) —
     **to be created, by the operator**.
  3. **`.gitignore` has no entry that would cover it** (verified,
     `.gitignore:1-26`; `agent-identity.env` is ignored at `:17` by exact path).
     ⇒ J13.
  4. **AC-nolit's coverage is hollowed out by the extraction** (verified,
     `layer1-static.sh:73-80`). ⇒ J17. This is a genuine defect the extraction
     *introduces*, found here rather than after the fact.
  5. **`.venv/bin/python` exists** (verified: `.venv/bin/` contains `python`,
     `python3`, `python3.14`). **`.venv/` is gitignored** (`.gitignore:2`), so
     `site.yml`'s `chmod -R a+rX src` never touches it and **nothing has ever
     verified that a second uid can traverse to and execute it**. ⇒ a hard
     precondition check before the first bootstrap (SC-8b).
  6. **The agent uid is 510** (`.gleipnir/agent-identity.env:1-2`); the test
     fixture deliberately uses 9999
     (`ansible/tests/fixtures/agent-identity.env`). The signer must take a
     **different free** id from both; the operator verifies free-ness per
     `s2-activation-control-proposal.md:38`.
  7. **`site.yml` recursively owns the whole repo** (`:165-171`) — the fact
     behind J1.
  8. **`gleipnir-code` cannot run any of this** (`gleipnir-code.md:34-62`) and
     **cannot write any `.gleipnir/**` path** (`:14`, with narrow exact-path
     exceptions for `advance-hook.ts` and three `preflight/` files only — none
     relevant here). ⇒ J12, and the spike report / identity file are not its
     work.

**New material tradeoff found?** **No new design fork.** Three plan-stage
judgments carry consequences the operator should acknowledge before `code` runs —
**J8** (the shared task-file upgrades `site.yml` act-1's guard), **J10** (one
file deliberately survives teardown) and **J14(c)** (a real-box full `site.yml`
apply). They are named in the Decisions index and again in §Judgment calls
needing operator acknowledgement. Everything else is bounded by the converged
briefs.

---

## Routing

Mechanical derivation, per `stage-role-map.md`:

- **Axis 1 (eligibility).** `P` (below) contains `ansible/signer.yml`,
  `ansible/signer-teardown.yml`, `ansible/tasks/create-service-account.yml` and
  `ansible/site.yml` — **standalone `*.yml`** — plus `ansible/tests/signer-static.sh`
  and an edit to `ansible/tests/layer1-static.sh` — **`*.sh`**. Both are explicit
  members of disqualifier set `X`. ⇒ **NOT prose/config-track eligible; the FULL
  8-stage pipeline runs.** Axis 2 is never reached. (`ansible/.ansible-lint`, the
  J26 fixture exclusion, is a **dot-file YAML lint config**, not a standalone
  `*.yml` playbook; it is noted for completeness but changes nothing — the routing
  is already the full pipeline on the playbooks and shell scripts alone.)
- **Hardened review obligations imported deliberately.** The full pipeline's
  `quality` stage already carries the dual SPEC-CONFORM / BLAST-RADIUS passes;
  because `P` additionally touches `.gitignore` (an always-hardened exact-path
  member of `E`) **and because this creates real OS-level privilege**, this plan
  makes the **negative-check attestation a Class-1 acceptance criterion**
  (§Negative-check attestation), with `attested_by ≠ author` and the substance /
  correspondence / post-change-state rules all binding.
- **Design Principles case:** `P ∩ X ≠ ∅`, and no touched `X`-member has
  class/function/module structure (Ansible YAML, POSIX `sh`) ⇒ **case (ii)**:
  DRY + Design Intent apply; SOLID and the class/module SRP are attested
  `N/A — no object/function structure`.

---

## 1. Architect

**Problem (one sentence).** The converged design puts the Tier-3 signer under
`launchd` at its own non-login uid (Decision 4 / 2C), but **no signer account
exists** and **launchd's `UserName` behaviour with a non-login account and a
repo-local `.venv` interpreter has never been probed on this host** (Decision 6's
recorded Medium-not-High confidence) — so Plan A provisions that account through
a parallel, `site.yml`-sharing playbook and converts the launch mechanism's
feasibility from an assertion into recorded evidence, **without touching a single
key, construction, reader, or `opencode.jsonc` line**.

**Users.**

- The **operator**, who executes every OS act (account creation, `launchctl`,
  plist placement, the playbook runs) and who is the only party who can read the
  spike's evidence and decide whether 2C survives contact with the host.
- **Whoever plans Plan B**, whose entire launch premise is this spike's verdict:
  if 2C does not hold on this host, Plan B's launch half must be re-opened with
  the operator before any Ed25519 work is scoped.
- The **`quality-reviewer`**, who must be able to tell a genuine negative
  empirical finding from a defect — which is why acceptance is split into
  **Class 1** (must pass) and **Class 2** (recorded outcomes that may be
  negative).

**Measurable success criteria** (each maps to a numbered check in §Stress-test):

1. A signer account **and** its group exist at a uid/gid distinct from the
   agent's 510, non-login (`/usr/bin/false`, `/var/empty`), created by
   `ansible/signer.yml` through the shared task-file. Arbiter: **SC-7**.
2. The account-creation logic exists in **exactly one place**, and `site.yml`
   genuinely consumes it — zero inline `sysadminctl -addUser` /
   `dscl . -create /Users` invocations remain outside the shared file.
   Arbiter: **SC-6**.
3. `ansible/signer.yml` and `ansible/signer-teardown.yml` write **no path inside
   the repository working tree**. Arbiter: **SC-3**.
4. All spike scratch state lives under a path created by **exclusive** `mkdir`,
   which **fails** if the path already exists. Arbiters: **SC-2**, **SC-5**.
5. The real production key `.gleipnir/keys/marker.key` is **byte-, mode-, owner-
   and group-identical** to its pre-spike baseline, verified after the **final**
   `site.yml` apply. Arbiter: **SC-1**.
6. Both plist placements are attempted and an **outcome matrix** is recorded —
   observed uid/gid, interpreter path, port-bind result, env visibility, log
   paths — with no criterion demanding a particular winner. Arbiter: **SC-13**.
7. **If** any candidate achieved a working signer-uid execution, the **F-1 bug
   class is reproduced and operator-visible**: the 4-step ordered control yields a
   log containing the exact scratch-key path **and** a specific permission denial,
   bracketed by a working baseline before and after. **If no candidate achieved a
   working baseline, this criterion is `N/A-BY-DESIGN`** and honestly recorded as
   such (J5). Arbiter: **SC-10**.
8. Env-var behaviour under launchd is tested in **both** the plist-declared and
   shell-only forms, and the written conclusion is scoped to exactly those two.
   Arbiter: **SC-15**.
9. Every attempt is preceded by a recorded `bootout` + free-port proof.
   Arbiter: **SC-9**.
10. The log directory launchd writes into exists and is **proven writable by the
    signer uid before the first bootstrap**. Arbiter: **SC-8**.
11. Teardown removes the account, the group, the scratch root, both plists and
    both launchd labels — and **only** what this run created, per the two-phase
    provenance manifest — and a **second** teardown run verifies "already clean"
    from the external receipt rather than assuming it. Arbiters: **SC-11**,
    **SC-20**.
12. `site.yml`'s existing behaviour is unregressed, proven by a run that
    **demonstrably executed the extracted tasks**. Arbiter: **SC-12**.
13. `ansible/tests/signer-static.sh` PASSES on the real files and, on each of
    **seven complete single-defect fixture trees**, FAILS **with that fixture's
    specific reason token** while every other check passes. Arbiters:
    **SC-3..SC-6** (fixture halves) and **SC-21**.
15. Every attempt's evidence is **attributable to that attempt alone** — no check
    is satisfiable by a stale log line from a prior attempt. Arbiter: **SC-19**.
14. A spike report exists at
    `.gleipnir/plans/signer-uid-separation-plan-a-spike-report.md` stating a
    verdict for Plan B: **2C viable / 2C not viable as designed / viable with
    named conditions**. Arbiter: **SC-16**.

**Constraints (verified against disk, not assumed).**

- **Platform is macOS/darwin.** Account creation is `dscl`/`sysadminctl`, never
  `useradd` (`site.yml:98-139`; the brief's F-3 verdict is "macOS-correct as
  written").
- **`command:`, not `ansible.builtin.user`** for Darwin service accounts — the
  existing, documented BC-5 constraint (`site.yml:99-101`: *"unreliable on Darwin
  for a non-login service account"*). The shared task-file inherits this.
- **No numeric uid/gid literal anywhere.** Both playbooks and the shared
  task-file read identities from an identity `.env` file and template them
  (`group_vars/all.yml:6-9`'s P3/BC-6 invariant; AC-nolit).
- **`group_vars/all.yml` is NOT widened** (C2). Signer-specific values live in
  `signer.yml`'s own `vars:` block. Note that `group_vars/all.yml` is inherited
  read-only by any play under `ansible/` — inheriting is not widening.
- **The operator executes all OS/root acts**; the agent guides and verifies
  (`go-caged-runbook.md`, `tier3-coach` Anti-Pattern 3). No in-framework agent
  can create a uid, `chown`, or `launchctl bootstrap`.
- **`gleipnir-code` holds no shell route to Ansible or to `ansible/tests/*.sh`**
  (`gleipnir-code.md:34-62`) and **no write to `.gleipnir/**`** (`:14`).
- **Plan A adds no dependency** of any kind: no Python, no Node, no
  `pyproject.toml` change. `cryptography`/Ed25519 is **Plan B's** carve-out
  (parent brief Decision 3) and nothing here anticipates it.
- **Port `8765` is the existing listener's port** (`server.py:49-50`,
  `DEFAULT_BIND_HOST`/`DEFAULT_BIND_PORT`) and may be held by the session's own
  opencode-spawned `gleipnir-approval` MCP. J7's pre-attempt check is what makes
  that a *detected test-setup condition* instead of a phantom result.

### Honesty ledger (binding, from C4 / J16)

> **Signer-uid separation binds meaningfully ONLY in caged mode.** O-3(b)'s
> implied **uncaged-mode** value must be **QUALIFIED, not fully inherited** by any
> record that follows this work. Uncaged, opencode runs as the operator's own uid,
> which can `sudo`, `chown`, `launchctl bootout`, or edit the plist — so the
> control raises the cost of key access from "read a file" to "invoke the
> operator's own privilege": a real but **modest narrowing, not isolation**.

> **Plan A itself delivers NO key confidentiality and NO isolation.** It creates
> an OS account and records launch-mechanism evidence. It changes no key's owner,
> mode, or content; no validator's behaviour; and no posture. The claim "the
> signer now has its own uid, therefore the key is protected" is **false** at the
> end of Plan A, and asserting it is a non-conformance.

> **Known gap — `caged + armed` is non-functional until the construction-#1/#2
> Ed25519 migration ships.** Under caged mode the marker key becomes
> signer-uid-only mode 600. `sequence-gate.ts` (`:69,120-127`) and
> `advance-hook.ts` (`:154,200-207`) load that key **in-process at the agent uid**
> on the armed path (`sequence-gate.ts:204`, `advance-hook.ts:350`), so the read
> fails EACCES and the armed run aborts. This **fails closed** (abort, not
> bypass) — the gap is an availability/usability gap, not a security hole. It is
> closed by migrating construction #2 to Ed25519 (Plan B), after which the
> plugins hold only the PUBLIC key and the agent-uid read is legitimate.

**Residuals named, NOT closed by Plan A** (from the brief's §Fork 4): the **plist
and `.venv` interpreter writability** gap (neither is covered by the current
`ENFORCEMENT_PATHS` set — SC-8b makes the `.venv` half concrete); and the
conversion of a **session-scoped** listener into a **standing** one, which Plan A
does not perform but whose feasibility it establishes.

**Explicitly NOT in scope:** any cryptographic construction, key format, signing
input, or reader call site; `opencode.jsonc`; `.gleipnir/plugins/**`;
`src/gleipnir/**`; `bin/**`; `boundary.py`'s prospective signer-can-read
assertion; the Ed25519 keypair and its distribution; predicate P's durable Tier-3
record (sibling brief Q3 — operator territory); construction #2's mint-uid
question (sibling brief Q5 — a live Plan-B escalation).

---

## 2. Trace

### Touched-path set `P`

| Path | Status | Writer | Change |
|---|---|---|---|
| `ansible/tasks/create-service-account.yml` | **NEW** (`ansible/tasks/` does not exist) | `gleipnir-code` | The single, parameterised "create a macOS service account" task-file: 3-way guard (J8) + group record + user record. Params: `svc_account_name`, `svc_uid`, `svc_gid`, `svc_fullname`, `svc_home`, `svc_shell`. Asserts every param is defined (no `default()` fallbacks). |
| `ansible/signer.yml` | **NEW** | `gleipnir-code` | Reads `.gleipnir/signer-identity.env`; includes the shared task-file with signer params; exclusively creates the scratch root (`spike_scratch` tag); creates `logs/`, the scratch key, and `created.env`. **Writes nothing inside the repo.** |
| `ansible/signer-teardown.yml` | **NEW** | `gleipnir-code` | Reads `created.env` and branches on the **THREE** states (J21), never two: **manifest present ⇒ teardown** (remove only flagged-created objects — account, group, scratch root, both plists, both labels — verify absence, then write the receipt as the **final** act); **manifest absent + receipt `/private/tmp/gleipnir-signer-spike.torndown` present ⇒ VERIFIED clean no-op** (quote the receipt, remove nothing, exit 0); **manifest absent AND receipt absent ⇒ REFUSE LOUDLY** (unknown state, remove nothing). |
| `ansible/site.yml` | **EXISTS** (428 lines, verified) | `gleipnir-code` | **One edit, at act 1 only:** replace the four inline `dscl`/`sysadminctl` tasks (`:103-139`) with an `include_tasks` of the shared file, passing the agent params. Acts 3/4/5/6 and AC-4 **byte-unchanged**. |
| `ansible/tests/signer-static.sh` | **NEW** (mirrors `layer1-static.sh`'s shape) | `gleipnir-code` **authors**; **operator runs** (J12) | Checks S1–S6 (below). Takes an optional root-directory argument so the broken fixtures can be pointed at it. **Emits one machine-greppable reason token per failing check** (`FAIL[S4/mismatch-guard-bypassed]`) so a fixture can assert *which* check fired, not merely that something did (J23). |
| `ansible/tests/fixtures/broken/` — **7 COMPLETE fixture TREES** | **NEW** | `gleipnir-code` | **Each fixture is a full copy of the otherwise-correct tree** (`signer.yml` + `signer-teardown.yml` + `tasks/create-service-account.yml` + `site.yml`) with **exactly ONE** deliberate defect (J23). F1 hardcoded `-UID`; F2 a repo **write** path; F3 `mkdir -p`; F4 `site.yml` with the include removed and the inline commands restored; **F5** a creation task whose `when:` bypasses the mismatch sentinel; **F6** `ignore_errors: true` on the mismatch `fail`; **F7** an ungated plist removal in teardown. |
| `ansible/tests/layer1-static.sh` | **EXISTS** (151 lines, verified) | `gleipnir-code` | **TWO small, narrow, bounded edits to this one file — and nothing else in it.** **(1)** AC-nolit's file list gains `tasks/create-service-account.yml` (J17). **(2)** The `ansible-lint` invocation (`:37-47`) gains an **explicit config-file argument**: `ansible-lint --config-file "$root/.ansible-lint" "$root"` (was `ansible-lint "$root"`). Edit (2) exists because J26's `exclude_paths:` is only effective if the config is actually **loaded**: relying on `ansible-lint`'s auto-discovery is an **unverified assumption** about which directory it searches relative to its invocation cwd, and this plan verified no such behaviour. Passing `--config-file` explicitly makes the exclusion load **regardless of auto-discovery behaviour or cwd** — turning a "probably discovered" into a guarantee. Both edits are additive one-liners; no check logic, no other line, and no lint **rule** is altered. Arbiter: **SC-22**. |
| `ansible/.ansible-lint` | **EXISTS** (31 lines, verified) | `gleipnir-code` | **One narrowly-scoped addition (J26): a new `exclude_paths:` key listing EXACTLY `ansible/tests/fixtures/broken/`** (repo-root-relative — `ansible-lint` resolves `exclude_paths` against the invocation cwd, verified at step 4)**.** Required, not optional: `layer1-static.sh:37-47` runs `ansible-lint "$root"` over the **whole `ansible/` tree** (`root` = `ansible/`, `:17`), and the file today has **no `exclude_paths` key**, so J23's complete-but-deliberately-broken fixture trees — F6's defect is literally `ignore_errors: true`, a rule this repo pointedly does **not** suppress (`.ansible-lint:24-29`) — would turn the **existing production** AC-lint pass red, which SC-12(a) requires to stay green. **`skip_list` is NOT touched**; no lint **rule** is suppressed globally. Arbiter: **SC-22**. |
| `ansible/README.md` | **EXISTS** (verified) | `gleipnir-code` | Act-1's description updated to say it now `include_tasks`es the shared file, with a pointer to `signer.yml` as the second consumer. Documentation currency only. |
| `.gitignore` | **EXISTS** (26 lines, verified) | **operator / build-mode ONLY** (∈ `E`) | **One** exact-path line: `.gleipnir/signer-identity.env` (J13). |
| `.gleipnir/signer-identity.env` | **NEW** | **operator ONLY** | `GLEIPNIR_SIGNER_UID=<free>` / `GLEIPNIR_SIGNER_GID=<free>`. `gleipnir-code` denies all `.gleipnir/**` writes (`gleipnir-code.md:14`), so this is operator work by capability. Survives teardown (J10). |
| `.gleipnir/plans/signer-uid-separation-plan-a-launchd-spike.md` | **THIS FILE** | `gleipnir-plan` | The plan. |
| `.gleipnir/plans/signer-uid-separation-plan-a-spike-report.md` | **NEW** | `gleipnir-plan` (Tier-0 grant) | The spike's recorded evidence, outcome matrix and Plan-B verdict. **Not** `gleipnir-code`'s — it cannot write `.gleipnir/**`. |

**Outside the repo entirely (operator-authored, never tracked, never
agent-written):**

```
/private/tmp/gleipnir-signer-spike/     <- exclusive mkdir (J1); the scratch root
  signer-probe.py                       <- the stage-1 capability probe (J3)
  stage2-wrap.sh                        <- the stage-2 observability wrapper (J18)
  scratch.key                           <- 32 throwaway random bytes, signer:signer 0600
  logs/                                 <- launchd StandardOut/ErrorPath parent
    NN-<arm>-<stage>-<UTC>/             <- ONE FRESH DIR PER ATTEMPT (J20): out, err
  created.env                           <- the APPEND-ONLY provenance manifest (J9/J22)
  outcome/                              <- captured evidence, one file per attempt
~/Library/LaunchAgents/dev.gleipnir.signer.spike.agent.plist    <- arm A
/Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist   <- arm B

/private/tmp/gleipnir-signer-spike.torndown   <- teardown completion receipt (J21),
                                                 OUTSIDE the scratch root by design,
                                                 so it survives the root's removal
```

**Why the receipt is outside the root (J21).** `created.env` lives inside `<root>`
and `<root>` is what teardown removes — so the manifest a *second* teardown would
need is destroyed by the *first*. The receipt is the only artifact deliberately
placed outside, and it exists solely so "already torn down cleanly" is a
**verified** state rather than an assumption drawn from absence.

**The scratch key is NOT the real key.** It is freshly generated from
`/dev/urandom`, is never copied from or derived from `.gleipnir/keys/marker.key`,
and validates nothing. It exists only so the probe can prove *"a mode-600 file
owned by the signer uid is readable by the launchd-started process"*, and so J5's
negative control has something safe to break.

### Integrations map

```
OPERATOR
  |- authors .gleipnir/signer-identity.env   (uid/gid, verified free)
  |- sudo ansible-playbook -i inventory.ini signer.yml
  |     |- pre: read + parse signer-identity.env        (fail fast if absent)
  |     |- include_tasks tasks/create-service-account.yml
  |     |     3-way guard -> create | skip | FAIL-on-mismatch          (J8)
  |     |- [tag spike_scratch] /bin/mkdir <root>   EEXIST => FAIL      (J1/J11)
  |     |- create <root>/logs, chown signer, verify signer-writable    (SC-8)
  |     |- dd if=/dev/urandom -> <root>/scratch.key, signer:signer 0600
  |     `- write <root>/created.env PHASE 1
  |            {ACCOUNT_CREATED,GROUP_CREATED,ROOT_CREATED}          (J22 phase 1)
  |- authors <root>/signer-probe.py, <root>/stage2-wrap.sh, both plists
  |- BEFORE each plist write: collision check  (J22, §Plist ownership)
  |     `- test -e <plist path>; launchctl print <domain>/<label>
  |        (1) nothing there            => create
  |        (2) exists AND this run's created.env records PLIST_x_PATH=<p>
  |                                     => WE OWN IT; authorized rewrite
  |        (3) exists and NOT recorded  => UNRELATED PRE-EXISTING => STOP
  |     `- append PLIST_x_{CREATED,PATH} ONLY after the FILE write succeeded
  |- BEFORE any bootout/bootstrap of an ALREADY-PRESENT label: an INDEPENDENT
  |     label-ownership check (J22, §Label ownership) --
  |     `- this run's created.env has LABEL_x_CREATED=true for THAT label?
  |            yes => authorized (our own earlier attempt);  no => STOP
  |     `- plist-file ownership is NEVER authorization for a LABEL operation
  |     `- append LABEL_x_CREATED=true ONLY after `bootstrap` itself succeeded
  |            (append-only; first writer wins; the two flags are recorded at
  |             two DIFFERENT moments, never together at file-write time)
  |- per attempt (J7 + J20):  mkdir <root>/logs/<attempt-id>/ ->
  |        rewrite the plist's StandardOut/ErrorPath into it ->
  |        bootout prior -> prove 8765 free -> bootstrap
  |     arm A: launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/...agent.plist
  |     arm B: sudo launchctl bootstrap system /Library/LaunchDaemons/...daemon.plist
  |        `- launchd --UserName/GroupName--> <repo>/.venv/bin/python <root>/signer-probe.py
  |              writes uid/gid, sys.executable, env visibility, key-read result,
  |              bind result -> <root>/logs/<attempt-id>/{out,err}    (stage 1, J2)
  |        `- stage 2 (only on an arm proved to run as the signer):
  |              plist declares GLEIPNIR_MARKER_KEY_FILE=<root>/scratch.key  (J18)
  |              <root>/stage2-wrap.sh -> logs argv/uid/gid/exe/env, then
  |                 LAUNCHES .venv/bin/python -m gleipnir.approval.mcp_server
  |                 as a CHILD (never `exec` -- an exec would replace the
  |                 wrapper and leave nothing to capture the exit status),
  |                 POLLS the live child's own PID for a LISTEN socket on
  |                 8765 (WRAP-BIND-LIVE), then `wait`s and records
  |                 WRAP-CHILD-EXIT                                     (J18/J25)
  |              `- classify into exactly ONE J19 bucket by walking the
  |                 ORDERED 7-row table, first match wins  (stage 2, J2/J25):
  |                   row 1 EADDRINUSE / setup fault            => VOID (J7)
  |                   row 2 IDENTITY GATE (wrong uid/exec)      => (c)
  |                   row 3 BIND-LIVE yes AND correct uid       => (e)
  |                   rows 4/5 fatal line + key discriminator   => (a)/(b)
  |                   row 6 fatal line, cause unattributable    => (f)
  |                   row 7 catch-all (healthy-looking, no bind)=> (f)
  |                 (d) is reachable ONLY as a refinement of row 3.
  |                 Setup faults are VOIDED first, whatever uid they
  |                 ran as; then identity is checked BEFORE a bind can
  |                 terminate as POSITIVE: a bind at the WRONG uid is
  |                 (c), never (e).
  |- negative control, in order (J5): baseline OK -> break key -> capture Errno 13
  |                                   on the exact path -> restore -> baseline OK
  |- sudo ansible-playbook signer-teardown.yml       (J9: account+group+root+plists)
  |     `- final act: write /private/tmp/gleipnir-signer-spike.torndown  (J21)
  |     `- 2nd run: receipt present => VERIFIED clean no-op;
  |            no manifest AND no receipt => REFUSE LOUDLY
  `- regression proof (J14): run.sh -> site.yml --tags act1 x2 -> site.yml full
                                                   -> RE-VERIFY the real key (SC-1)
```

Deliberately untouched by every path above: `.gleipnir/keys/marker.key` (verified
identical, twice), `opencode.jsonc`, `.gleipnir/plugins/**`, `src/gleipnir/**`,
`bin/**`, `ansible/group_vars/all.yml`, and `ansible/site.yml` acts 3–6 + AC-4.

### `signer-static.sh` checks (S1–S6)

| # | Check | Falsified by |
|---|---|---|
| S1 | Every line in `signer.yml` / the shared task-file matching `UniqueID`, `PrimaryGroupID`, `-UID` or `-GID` contains a `{{ … }}` template and no bare digit run | fixture **F1** (a hardcoded `-UID`) |
| S2 | **WRITE targets only** (see the classifier below). Every **write**-module path (`ansible.builtin.file`/`copy`/`template`/`lineinfile`/`blockinfile` `path:`/`dest:`, and `command:`-module shell redirections) in `signer.yml`/`signer-teardown.yml` either (i) begins with the scratch-root variable `{{ spike_root }}`, or (ii) is one of the **THREE enumerated external paths**: the two plist paths `~/Library/LaunchAgents/dev.gleipnir.signer.spike.agent.plist` and `/Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist`, **or (iii) the teardown completion receipt `/private/tmp/gleipnir-signer-spike.torndown` (J21)**. **READ-only references are explicitly permitted and NOT flagged** | fixture **F2** (a `.gleipnir/var/tmp` **write** path) |
| S3 | The scratch-root task invokes `mkdir` with **neither** `-p` **nor** a `creates:` key | fixture **F3** (`mkdir -p`) |
| S4 | **Control-flow check, not comment presence.** In `create-service-account.yml`: (i) a `fail` task exists on the mismatch branch; (ii) **every** task whose name/`when:` participates in account or group *creation* carries a `when:` containing the **absent-sentinel** (`svc_present is false` / the registered query's `rc != 0` **conjoined** with a mismatch-free assertion); (iii) **zero** creation tasks have a `when:` that can be true while a mismatch is true; (iv) the `fail` task is **not** guarded by `ignore_errors`, `failed_when: false`, or placed inside a `rescue:` that swallows it; (v) the `fail` precedes every creation task in file order | fixtures **F5** (a creation task whose `when:` bypasses the mismatch sentinel) and **F6** (`ignore_errors: true` on the `fail`) |
| S5 | `site.yml` contains an `include_tasks` of `tasks/create-service-account.yml` **and** zero occurrences of `sysadminctl -addUser` or `dscl . -create /Users` | fixture **F4** (inline commands restored) |
| S6 | `signer-teardown.yml` references the account, the group **and** the scratch root; **every** removal is gated on a `created.env` flag (including the **plist/label** removals on their `PLIST_*_CREATED`/`LABEL_*_CREATED` flags, J22); and the completion receipt (J21) is written **outside** `{{ spike_root }}` as the final task | fixture **F7** (an ungated plist removal), or dropping the group removal |

**The S2 read/write classifier (this is what makes S2 sound).** A blanket
"zero mentions of `.gleipnir`" check is **wrong**: `signer.yml` legitimately
**reads** `.gleipnir/signer-identity.env`, which is under `.gleipnir/` by
necessity (E-1). S2 therefore classifies each match before judging it:

| Form | Class | S2 verdict |
|---|---|---|
| `ansible.builtin.slurp: src:` / `stat: path:` / `command: dscl . -read …` / a `when:`/`assert:` referencing a path | **READ** | **ALLOWED** — never flagged. `stat` is a *read-only* module; treating its `path:` as a write target is a category error and would flag the mandatory E-1 identity check as a violation |
| `file:`/`copy:`/`template:`/`lineinfile:`/`blockinfile:` `path:`/`dest:`; `command:`/`shell:` with `>`/`>>`/`tee`; `file: state: absent` | **WRITE** | Must satisfy S2's (i) scratch-root **or** (ii) enumerated-plist rule |
| The two plist paths `~/Library/LaunchAgents/dev.gleipnir.signer.spike.agent.plist`, `/Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist` | **WRITE, external, EXPECTED** | **ALLOWED by explicit enumeration** — teardown *must* remove them (J9), and they are outside both the repo **and** the scratch root by design (J4). They are matched as **exact literals**, so the exception cannot widen |
| The teardown receipt `/private/tmp/gleipnir-signer-spike.torndown` (**J21**) | **WRITE, external, EXPECTED** | **ALLOWED by explicit enumeration — the THIRD and final external write target.** It is outside the scratch root **by necessity**: teardown removes `<root>` entire, so a receipt inside it would be destroyed by the very run that writes it (J21). **Without this enumeration a correctly-built teardown would FAIL S2's own check** — S2 would flag the mandatory receipt write as a violation. Matched as an **exact literal**, so the exception cannot widen |

**Corrected claim.** The earlier formulation *"every write path begins with the
scratch-root variable"* is **false as written** and is replaced by: **"every
write path is either scratch-root-relative, or one of the two enumerated
external plist paths, or the one enumerated external teardown receipt; no write
path resolves inside the repository working tree."** The repo-exclusion is the
load-bearing invariant; scratch-root-prefixing is the rule for *scratch* writes
only. The **three** external paths (two plists + the receipt) are a **named,
enumerated** exception — not a hole, because teardown removing the plists and
writing the receipt are both *requirements*, and an unenumerated external write
still fails S2.

`signer-static.sh` needs **no** Ansible toolchain (pure text, like
`layer1-static.sh`'s AC-* half), so it genuinely runs today; it degrades honestly
if pointed at a missing file (**FAIL**, not SKIP).

### Edge cases

| # | Case | Handling |
|---|---|---|
| E-1 | `.gleipnir/signer-identity.env` absent | `signer.yml` pre-task **fails fast**, naming the file and the "verify a free uid first" instruction — the same shape as `site.yml:72-82` does for `agent-identity.env`. It never bootstraps a numeric id itself (that would reintroduce an AC-nolit literal). |
| E-2 | Chosen signer uid collides with 510 or an existing account | The 3-way guard fires: an existing account of that name whose `UniqueID` differs from the requested one is a **mismatch ⇒ FAIL**. A *different* account already holding the numeric id is caught by the operator's pre-step `dscl . -list /Users UniqueID` check (SC-7's precondition). |
| E-3 | Scratch root already exists | Bare `mkdir` **fails EEXIST**. Intended (J1/J11), not a bug: the remedy is `signer-teardown.yml`, never a silent adopt. |
| E-4 | `8765` occupied at attempt start (including by the session's own approval MCP) | **TEST-SETUP failure** (J7): the attempt is void, not recorded as a candidate result. Remedy: bootout the prior label, or run the spike with the session listener down. |
| E-5 | The signer uid cannot traverse to / execute `.venv/bin/python` | Caught **before** the first bootstrap by SC-8b's explicit `sudo -u '#<signer-uid>' <repo>/.venv/bin/python -c 'print(1)'` probe. A failure is a **recorded precondition finding** and a genuine, informative negative for 2C — since 2C depends on that interpreter being executable by a second uid. It is **not** a plan defect; it goes in the outcome matrix and the report's verdict. |
| E-6 | An arm bootstraps but the process runs as the **wrong** uid (e.g. the operator's) | A **valid NEGATIVE finding** (J4). Recorded with the observed uid; that arm is marked unsuitable and stage 2 is not run on it. If **both** arms do this, the report's verdict is "2C not viable as designed on this host" and Plan B's launch half returns to the operator. |
| E-7 | `launchctl bootstrap` fails outright (bad plist, denied domain, SIP) | Recorded verbatim (command + exit status + stderr) as that arm's outcome. Not a plan defect. |
| E-8 | Stage 2 exits immediately on stdio EOF | Expected and pre-declared (J2), but **(d) requires an AFFIRMATIVE bind observation, never merely an absence of errors (J25).** Recorded as **J19 (d) EXPECTED/stdio-EOF-with-healthy-listener** **only if** the attempt's own log carries **`WRAP-BIND-LIVE yes`** — this child's **own PID** observed holding a LISTEN socket on `127.0.0.1:8765` **while alive** — **AND `WRAP-UID` = the signer uid** (the identity gate is table **row 2** — row 1 is the EADDRINUSE/setup-fault VOID gate — and it sits ahead of the bind row: **a bind at the WRONG uid is `(c) NEGATIVE`, never (d)/(e)**), with `WRAP-CHILD-EXIT 0` and no fatal line; it is then written up as **(e) POSITIVE/bound, stdio-EOF variant**. Signer uid + interpreter path + readable key + no fatal line are **NOT sufficient**: all three wrapper lines are captured **before** the child runs, so a module-level import failure satisfies every one of them with **no listener ever started**. Without `WRAP-BIND-LIVE yes` the attempt is **J19 (f) INCONCLUSIVE** and recorded as such. **Verified: exit status 0 does NOT discriminate** — `_run_listener` catches a fatal `KeyUnavailable`, records it, and returns without raising (`mcp_server.py:298-314`), after which the **separate** `mcp.run(transport="stdio")` path (`:348-350`) hits EOF and the process exits 0. Never recorded as a launch failure, and never as (d)/(e), without the positive bind evidence. |
| E-9 | `created.env` absent when teardown runs | **Depends on the receipt — the three states (J21), not a flat refusal.** Manifest absent **+ receipt `/private/tmp/gleipnir-signer-spike.torndown` present** ⇒ a **VERIFIED clean no-op**: teardown quotes the receipt (its timestamp and the verbatim `created.env` it consumed) as positive evidence of *why* the box is clean, removes nothing, exits 0. Manifest absent **AND receipt absent** ⇒ teardown **REFUSES LOUDLY** (J9) and removes nothing; the operator reconciles by hand. The plan never licenses guess-based deletion, and never infers "clean" from absence alone. |
| **E-9b** | A **STALE receipt from a PRIOR run** is still present when a NEW run provisions | **Closed by step 11a, and this is why that step exists.** Nothing retires a receipt automatically, so an old one would otherwise persist indefinitely. The dangerous sequence: a new run creates the account, then fails **before** writing `created.env`; teardown then sees "manifest absent + receipt present" and reports a **VERIFIED clean no-op** — certifying as clean a **real leftover account from THIS run** that the old receipt says nothing about. Step 11a forecloses it: at the very start of provisioning, any existing receipt must be (i) **confirmed** against the live box (account, group, root, plists, labels all genuinely absent) and (ii) **moved aside** to `…torndown.retired-<UTC>`. If (i) fails, the receipt is lying about the current box ⇒ **STOP**, reconcile by hand, do not provision. With no receipt present at provisioning time, the failure sequence above lands in state (3) **REFUSE LOUDLY** — the correct answer for an unknown state. Verified by **SC-20(vi)**. |
| E-10 | Teardown leaves the group behind because the account removal took it | Verified explicitly: SC-11 checks `dscl . -read /Groups/<name>` **and** `dscl . -read /Users/<name>` both fail. "Account gone" is not accepted as evidence the group is gone. |
| E-11 | A pre-existing AC-4 failure surfaces during J14(c) / step 15(d) | Attributable to **pre-existing** **ONLY** via the **step-0b** `AC4-BASELINE:` comparison (§Assemble step 0b): **only if step 0b recorded `AC4-BASELINE: FAIL` with the SAME assert message**. If step 0b recorded `AC4-BASELINE: PASS`, the failure **IS this plan's regression**. If step 0b was never captured, the question is **permanently unanswerable** and **no** pre-existing claim may be made. **SC-1 (the real key is unchanged) and J14(b) (act-1 is `changed=0` twice) are CORROBORATING discriminators only — neither, alone or together, licenses the attribution without the step-0b baseline comparison**, because both are consistent with a *newly introduced* AC-4 regression (the extraction can break AC-4's precondition without touching the key and while act-1 still converges). Recorded in the report either way; never silently attributed to this plan, and never silently dismissed. |

---

## 3. Link — validated before building

Every item below was opened and read during this planning stage. Nothing in this
plan cites a path or line that was not verified (L-C15).

- **`ansible/site.yml` — 428 lines, read.** Act 1's four inline tasks at
  `:103-139` (the extraction target); the two-way guard `dscl_query.rc != 0`
  (`:113,123,129,137`) that J8 replaces; act-3's repo-wide recursive `owner`
  (`:165-171`) and the `.gleipnir/var/tmp` `g+w` recurse (`:209-216`) that
  together justify J1; act-5's key lock (`:375-382`); AC-4's
  `environment: GLEIPNIR_MARKER_KEY_FILE` fix (`:406-417`) and its failing
  assertion (`:419-428`).
- **`ansible/group_vars/all.yml` — 110 lines, read.** The P3/BC-6 no-numeric-id
  invariant (`:6-9`), `marker_key_relpath` (`:28`), `tier012_writable_dirs`
  including `.gleipnir/var/tmp` (`:32-37`), and the 8 LOCKED enforcement paths
  (`:78-110`) — none of which this plan modifies.
- **`ansible/tests/layer1-static.sh` — 151 lines, read.** AC-nolit's two-file
  grep at `:73-80` (⇒ J17); AC-order (`:49-61`), AC-env (`:63-71`), AC-mirror
  (`:82-105`) — all untouched. The PASS/FAIL/SKIP shape `signer-static.sh`
  mirrors.
- **`ansible/tests/run.sh` (49 lines) and `ansible/tests/README.md` (90 lines) —
  read.** The 3-layer harness is green with Ansible installed (ansible-core
  2.21.3, ansible-lint 26.8.0) and degrades to SKIP without it. Fixture runs
  deliberately never use uid 510, `sudo`, or the real account.
- **`ansible/` directory listing — verified.** `site.yml`, `group_vars/all.yml`,
  `inventory.ini`, `.ansible-lint`, `README.md`, `tests/`. **No `tasks/`
  directory exists** — the shared task-file creates it.
- **`.gleipnir/agent-identity.env` — 2 lines, read.** `GLEIPNIR_AGENT_UID=510`,
  `GLEIPNIR_AGENT_GID=510`. The signer must differ from both.
- **`.gitignore` — 26 lines, read.** `.gleipnir/agent-identity.env` ignored at
  `:17` **by exact path** (the J13 precedent); `.venv/` at `:2`; `.envrc` at
  `:21`; `.gleipnir/keys/*.key` at `:13`.
- **`.gleipnir/keys/` — verified:** exactly `marker.key` and `README.md`. The
  SC-1 baseline target.
- **`.venv/bin/` — verified:** contains `python`, `python3`, `python3.14`. The
  interpreter 2C needs exists; its executability **by a second uid has never been
  tested** ⇒ SC-8b.
- **`src/gleipnir/approval/server.py:49-50` — read.**
  `DEFAULT_BIND_HOST = "127.0.0.1"`, `DEFAULT_BIND_PORT = 8765` — the port the
  spike must find free.
- **`opencode.jsonc:91-100` — read** (via grep, `:91`, `:96`): the
  `gleipnir-approval` local MCP with `{env:GLEIPNIR_MARKER_KEY_FILE}`. **Read
  only to confirm it is NOT touched** and to identify the likely holder of port
  8765 during a session.
- **`.gleipnir/agents/gleipnir-code.md` — 117 lines, read.** `edit` allows
  `ansible/**` (`:12-28`, no matching deny) and denies `.gleipnir/**` (`:14`);
  `bash: "*": deny` with a sandbox-only allowlist (`:34-62`). ⇒ J12 and the
  authorship split.
- **`bin/gleipnir-launch` — 44 lines, read.** The `sudo`/`env_reset` trap
  documented at `:18-26` — the same class of trap the plist's
  `EnvironmentVariables` must avoid (J6's motivation). **Not touched.**
- **`.gleipnir/plans/s2-activation-control-proposal.md:34-58` — read.** The
  authoritative `dscl`/`sysadminctl` shape, the "verify a free uid first"
  instruction, and the `dscl`-only fallback the shared task-file mirrors.
- **`stage-role-map.md` Axis 1/2 — read.** `*.yml` and `*.sh` are members of `X`;
  `.gitignore` is an always-hardened exact-path member of `E`. ⇒ J15.

**Not validated, and deliberately so — this is what the spike is for:** whether
launchd honours `UserName` for a non-login account here; whether either domain
can exec a repo-local `.venv` interpreter; whether the resulting process can bind
`127.0.0.1:8765`; and what env it actually sees. Asserting any of these from
documentation is precisely the Dunning-Kruger flag Decision 6 exists to close.

---

## 4. Assemble — build order

Split by **who applies what**. `[CODE]` = `gleipnir-code`; `[OP]` = operator;
`[REV]` = `quality-reviewer`; `[PLAN]` = `gleipnir-plan` (Tier-0 write).

| Step | Actor | Work | Gate before proceeding |
|---|---|---|---|
| 0 | `[OP]` | **Baseline the real key.** Record `shasum -a 256 .gleipnir/keys/marker.key` and `stat -f '%Sp %Su %Sg %z'` for it. Store the four values in the spike report's baseline block. | The baseline exists in writing. **No later step may run without it** — SC-1 is uncheckable otherwise. |
| **0b** | `[OP]` | **Baseline AC-4 — BEFORE any provisioning, any account creation, and any `site.yml` apply (J24(d)).** Run the AC-4 assertion against today's unmodified tree and record its verdict verbatim: `sudo ansible-playbook -i inventory.ini site.yml --tags ac4` (the `ac4` tag isolates the pre-tasks + the AC-4 command/assert pair — the same isolation `layer3-idempotency.sh:99-102` uses), capturing the full output and exit status into the spike report's baseline block as **`AC4-BASELINE: PASS`** or **`AC4-BASELINE: FAIL — <verbatim assert message>`**. **This step is what makes "the AC-4 failure at step 15(d) is pre-existing" a checkable claim rather than an excuse:** E-11 and J24(d) both require a **before/after comparison**, and without this capture there is no "before" — the question becomes permanently unanswerable and any pre-existing-failure claim is unfalsifiable. | An `AC4-BASELINE:` line exists in writing, captured **before** step 10/11 ran anything. **Step 15(d)'s AC-4 verdict may not be interpreted without it.** |
| 1 | `[REV]` | **`spec-review`** of this plan: the 6 converged rows are cited-not-re-decided; the 17 `[PJ]` rows are sound; the Design Intent is specific and falsifiable (intent-quality sub-check); the J15 routing derivation is correct; J8/J10/J14 are surfaced, not buried. | **FAIL stops the pipeline.** |
| 2 | `[OP]` | **Acknowledge J8, J10, J14(c)** (§Judgment calls needing operator acknowledgement). A `quality`-stage divergence on any of these blocks `git` unless acknowledged; getting it now avoids a late block. | Three explicit acknowledgements recorded. |
| 3 | `[CODE]` | **`test` stage — author the arbiter first.** `ansible/tests/signer-static.sh` (S1–S6), emitting **one machine-greppable reason token per failing check** (`FAIL[S<n>/<reason>]`), **and all SEVEN broken fixture TREES** under `ansible/tests/fixtures/broken/{F1..F7}/` — **each a FULL COPY of the otherwise-correct tree** (`signer.yml` + `signer-teardown.yml` + `tasks/create-service-account.yml` + `site.yml`) differing by **exactly ONE** deliberate defect (J23): F1 hardcoded `-UID`; F2 a repo **write** path; F3 `mkdir -p`; F4 `site.yml` inline commands restored; **F5** a creation `when:` bypassing the mismatch sentinel; **F6** `ignore_errors: true` on the mismatch `fail`; **F7** an ungated plist removal. Also **BOTH** narrow `layer1-static.sh` edits — (1) the one-line AC-nolit widening (J17) **and (2) the explicit config-file argument** `ansible-lint --config-file "$root/.ansible-lint" "$root"` (so J26's exclusion loads regardless of auto-discovery behaviour or cwd) — **and, in the SAME step, because the fixtures cannot exist without it, the J26 `exclude_paths:` addition to `ansible/.ansible-lint` naming exactly `ansible/tests/fixtures/broken/`** (repo-root-relative — resolved against the invocation cwd, verified at step 4) (verified necessary: `layer1-static.sh:37-47` lints the whole `ansible/` tree and the config has no `exclude_paths` key today, so these deliberately-broken trees would otherwise turn the **existing production** lint pass red — F6's defect is literally `ignore_errors: true`). **Do NOT add any rule to `skip_list`.** **Authoring only — `gleipnir-code` cannot run these** (J12). | **SEVEN** fixture directories exist, each a **complete** tree (not a single defective file — a minimal fixture makes every *other* check fail for absence, so the fixture would go red without the intended check firing at all: J23's whole point); `signer-static.sh` emits a distinct `FAIL[S<n>/<reason>]` token per check; **`ansible/.ansible-lint` carries `exclude_paths: [ansible/tests/fixtures/broken/]` and an UNCHANGED `skip_list`** (SC-22). |
| 4 | `[OP]` | **Run the arbiter against today's tree, and against each of the SEVEN fixtures — asserting the SPECIFIC token, not merely "it failed".** (i) `sh ansible/tests/signer-static.sh` against the real tree must **FAIL** (the real artifacts do not exist yet). (ii) For **each** of F1…F7: `sh ansible/tests/signer-static.sh ansible/tests/fixtures/broken/F<n>` must (a) emit **that fixture's own expected token** — F1 ⇒ `FAIL[S1/…]`, F2 ⇒ `FAIL[S2/…]`, F3 ⇒ `FAIL[S3/…]`, F4 ⇒ `FAIL[S5/…]`, F5 ⇒ `FAIL[S4/mismatch-guard-bypassed]`, F6 ⇒ `FAIL[S4/…]` (the `ignore_errors` variant), F7 ⇒ `FAIL[S6/…]` — **and (b) show every OTHER check PASSING in that same run** (`grep -c '^FAIL\[' == 1`). A fixture emitting the wrong token, or more than one `FAIL[` line, proves the checker is firing for the wrong reason (or for absence) and is a **test-authoring defect to fix before step 5**. **(iii) Prove the J26 exclusion works AND is load-bearing — two runs, per SC-22(i)+(iv):** first run `sh ansible/tests/layer1-static.sh` and confirm its `ansible-lint` check reports **PASS** with the seven broken fixture trees on disk; then run the **positive control** — temporarily comment out `exclude_paths:` in `ansible/.ansible-lint`, re-run the same discovery-based scan, and confirm it now **FLAGS `ansible/tests/fixtures/broken/F6`** with an `ignore-errors` finding; restore the key and re-confirm PASS. **The green pass alone does not discharge SC-22** — without the observed FAIL, a vacuous exclusion (one guarding against a violation that never fires) is indistinguishable from a working one. **Do NOT substitute `ansible-lint <F6 path>` run directly: F6 is INSIDE the excluded subtree, so that command proves nothing about discovery scoping.** | **Seven** recorded runs, each with its expected token **and** a verified single-`FAIL[` line. Arbiter: **SC-21**. A nonzero exit status alone is **NOT** an accepted gate here. **Plus: `layer1-static.sh`'s `ansible-lint` check PASSES with the broken fixtures present** (SC-22) — if it goes red, the J26 exclusion is wrong or missing and must be fixed before step 5. |
| 5 | `[CODE]` | **`code` stage — the shared task-file.** `ansible/tasks/create-service-account.yml`: param asserts, the **3-way** guard (J8), group record, user record, `dscl`-only fallback comment. No numeric literal. | — |
| 6 | `[CODE]` | **`site.yml` adoption (C6).** Replace `:103-139`'s four inline tasks with one `include_tasks` passing the agent params. **Nothing else in `site.yml` changes.** | A `git diff` confined to act 1. |
| 7 | `[CODE]` | **`ansible/signer.yml`.** Identity pre-tasks (fail-fast, E-1); shared-task include with signer params; `spike_scratch`-tagged exclusive `mkdir`; `logs/` + signer-writability verification; scratch key from `/dev/urandom` at signer:signer 0600; `created.env`. | — |
| 8 | `[CODE]` | **`ansible/signer-teardown.yml`.** `created.env`-gated removal of account, group, scratch root, both plists, both labels; absence verification; **and the FULL THREE-STATE entry logic (J21) — not a two-state "manifest absent ⇒ refuse"**: (1) **manifest present** ⇒ perform the gated teardown, and as its **final** task write the receipt `/private/tmp/gleipnir-signer-spike.torndown` (UTC timestamp + the account/group/root/plist/label names removed + the consumed `created.env` **copied verbatim into the receipt**); (2) **manifest absent + receipt present** ⇒ report a **VERIFIED clean no-op** (exit 0), quoting the receipt's timestamp and contents as the evidence of *why* it is clean, removing nothing; (3) **manifest absent AND receipt absent** ⇒ **REFUSE LOUDLY** and remove nothing (unknown state, J9's fail-loud posture intact). Plus the `ansible/README.md` act-1 currency edit. | The playbook distinguishes all **three** states; state (2) is a *verified* no-op citing the receipt, **never** an inference from absence; state (3) refuses. A two-state implementation is a defect (it would make (2) refuse, or make (3) silently pass). Arbiter: **SC-20**. |
| 9 | `[OP]` | **Run the arbiter again + the existing harness.** `sh ansible/tests/signer-static.sh` PASSES on the real files and still FAILS on **all SEVEN** fixtures **with each fixture's own specific token and a single `FAIL[` line** (the step-4(ii) assertion, re-run against the now-real tree); `sh ansible/tests/run.sh` is green (SKIPs read as SKIPs) — **including `layer1-static.sh`'s `ansible-lint` check over the whole `ansible/` tree (now invoked with the explicit `--config-file "$root/.ansible-lint"`), which must PASS with all seven broken fixture trees on disk (SC-22, the J26 exclusion working end-to-end), and with `skip_list` still `[name[casing]]` only**. | Both recorded, the seven token assertions included. **SC-22(iv)'s with/without positive control from step 4(iii) is cited here, not re-derived.** **A red harness, or a fixture failing with the wrong token, stops here.** **An `ansible-lint` FAIL caused by the broken fixtures means the J26 exclusion is missing/mis-scoped — fix the exclusion, never the lint rule.** |
| 10 | `[OP]` | **Author the Tier-3 / operator artifacts.** Choose a free signer uid/gid (`dscl . -list /Users UniqueID`, `dscl . -list /Groups PrimaryGroupID`; must differ from 510); write `.gleipnir/signer-identity.env`; add the single exact-path `.gitignore` line (J13). | `git status` shows `signer-identity.env` untracked-and-ignored. |
| **11a** | `[OP]` | **RETIRE ANY STALE TEARDOWN RECEIPT — before provisioning anything (the receipt-reconciliation gap).** `test -e /private/tmp/gleipnir-signer-spike.torndown`. **If it exists, it is from a PRIOR run and nothing has retired it**, so it must be reconciled *now*, before this run can create any side effect: (i) confirm the clean starting state it claims — `dscl . -read /Users/<name>` fails, `dscl . -read /Groups/<name>` fails, `<root>` absent, both plists absent, both labels absent from `launchctl print`; (ii) then **move it aside**: `sudo mv /private/tmp/gleipnir-signer-spike.torndown /private/tmp/gleipnir-signer-spike.torndown.retired-$(date -u +%Y%m%dT%H%M%SZ)`. If (i) does **not** hold, the receipt is **lying about the current box** — **STOP** and reconcile by hand; do not provision on top of it. **Why this step exists:** an old receipt is a certificate about a *previous* run's cleanup. If it survives into a new run, and that new run creates the account and then fails **before** writing `created.env`, teardown would hit state (2) "manifest absent + receipt present" and report a **VERIFIED clean no-op** — certifying as clean a real leftover account the old receipt knows nothing about. Retiring the receipt at the start makes that state (3) **REFUSE LOUDLY** instead, which is the correct answer for an unknown state. | No `*.torndown` receipt exists at the moment provisioning begins. **A receipt present ⇒ this step has not been done ⇒ do not proceed to 11b.** |
| 11b | `[OP]` | **Provision + precondition checks.** `sudo ansible-playbook -i inventory.ini signer.yml`. Then SC-8b: `sudo -u '#<signer-uid>' <repo>/.venv/bin/python -c 'print(1)'` and a signer-uid write into `<root>/logs/`. Then re-run `signer.yml --skip-tags spike_scratch` (⇒ `changed=0`) and once **with** the tag (⇒ **must FAIL EEXIST**), per J11. | Account+group exist; both precondition probes recorded (pass **or** fail — E-5 is informative); both idempotency behaviours observed. |
| 12 | `[OP]` | **The spike itself** — §Spike protocol, in order: probe + **the stage-2 wrapper** + both plists authored (each plist write preceded by the §Plist ownership check); arm A and arm B stage 1, each preceded by the **full per-attempt preamble** (fresh `$aid` log dir + J7 hygiene); **stage 2 only on a qualifying arm, via `stage2-wrap.sh` with `GLEIPNIR_MARKER_KEY_FILE` declared** (J18), classified into exactly one J19 bucket **including (f) INCONCLUSIVE** using the listener-level discriminators — **never** from exit status alone; the J6 env arms; then the J5 negative control **beginning with its step-6.0 baseline-existence BRANCH** — if no arm produced `PROBE-UID <signer-uid>` **and** `PROBE-KEYREAD-OK`, record SC-10 as **N/A-BY-DESIGN** with the citing matrix rows and **do not run steps 6.1–6.4**; otherwise run all four, mandatory and unweakened. Capture every artifact into `<root>/outcome/`. | Every attempt has its own fresh log dir + bootout + free-port record (SC-9, SC-19). Every stage-2 attempt carries exactly one J19 class. **The step-6.0 branch decision is recorded in writing either way** (SC-10). |
| 13 | `[PLAN]` | **Write the spike report** to `.gleipnir/plans/signer-uid-separation-plan-a-spike-report.md`: baseline block, outcome matrix, negative-control transcript, env-arm conclusions scoped per J6, and the **Plan-B verdict** (viable / not viable as designed / viable with named conditions). | SC-13, SC-15, SC-16. |
| 14 | `[OP]` | **Teardown — and prove all THREE receipt states (J21).** (i) `sudo ansible-playbook -i inventory.ini signer-teardown.yml` with `created.env` **present** ⇒ state (1): the gated teardown runs; then verify absence: `dscl . -read /Users/<name>` fails, `dscl . -read /Groups/<name>` fails, scratch root gone, both plists gone, both labels absent from `launchctl print`. `.gleipnir/signer-identity.env` **remains** (J10). Confirm the receipt `/private/tmp/gleipnir-signer-spike.torndown` now **exists** and contains the timestamp + removed-object names + the verbatim `created.env` copy. (ii) Re-run teardown ⇒ **state (2)**: manifest absent (the first run removed `<root>` and the manifest with it) + receipt present ⇒ a **VERIFIED clean no-op** that **quotes the receipt** as its evidence, removing nothing, exiting 0. (iii) **Prove state (3) too:** move the receipt aside (`sudo mv …torndown …torndown.saved`) and re-run ⇒ teardown **REFUSES LOUDLY** and removes nothing; then move it back. Without (iii), nothing distinguishes a correct three-state implementation from one that treats *any* absence as success. | SC-11 **and SC-20**. All three states observed and recorded; (ii) must cite the receipt, **not** infer cleanliness from absence; (iii) must refuse. |
| 15 | `[OP]` | **`site.yml` regression proof (J14), with the inventory and an EXECUTION transcript (J24).** (a) `sh ansible/tests/run.sh` green. (b) **`sudo ansible-playbook -i inventory.ini site.yml --tags act1` — TWICE, `-i inventory.ini` MANDATORY on both** (`site.yml`'s play targets `hosts: local`, defined **only** in `inventory.ini:7-8`; without `-i` the play matches **no host** and `changed=0` means *"nothing ran"* — a vacuous pass). Both must report `changed=0`. (c) **Prove the extracted tasks ACTUALLY EXECUTED**, per (b2) below. (d) **One** full `sudo ansible-playbook -i inventory.ini site.yml`; record AC-4's verdict **and compare it to step 0b's `AC4-BASELINE:`** — a FAIL here may be called "pre-existing" **only if** `AC4-BASELINE: FAIL` was recorded at step 0b with the **same** assert message; if the baseline was PASS, a failure here **is this plan's regression** (E-11/J24(d)). | SC-12. **(b) without `-i inventory.ini` is a vacuous pass and does not count. (c)'s transcript is required — `changed=0` alone does not discharge SC-12. (d) without the step-0b comparison may not be labelled "pre-existing".** |
| **15(b2)** | `[OP]` | **The execution proof for step 15(c) — a VERBOSE transcript, NOT `--list-tasks`, and NOT merely "the tasks appeared".** Run `sudo ansible-playbook -i inventory.ini site.yml --tags act1 -v` and capture the transcript. **Why not `--list-tasks`: verified Ansible behaviour — it does NOT expand the bodies of *dynamic* `include_tasks` (they are resolved at run time, not at list time), so it would list the include task and none of the tasks inside it.** J24(b)'s `--list-tasks` proposal is **superseded by this transcript requirement**. Two distinct assertions: **(1) SELECTION** — the transcript contains the extracted task-file's **own task names** as task headers (e.g. `TASK [query existing service account …]`), proving the include body was **entered**, not merely that the include itself ran; **(2) GENUINE EXECUTION of the GUARD LOGIC — the load-bearing half.** On a run where **the account already exists and all attributes match** (the steady-state case, which is the run that yields `changed=0`), the **query and attribute-comparison tasks MUST show a real `ok:` result, NOT a `skipping:` line.** Concretely: the `dscl`-query task and the present-and-matching comparison/assert task must each appear as **`ok: [localhost]`** — for the query, `changed=false` with **registered output visible in `-v`**; for the comparison, an `ok:` evaluation of the actual-vs-expected attributes. **A `skipping: [localhost]` on EITHER of those two tasks FAILS this proof.** (**The per-task host label is `localhost`, not `local`** — verified `ansible/inventory.ini:7-8`: `[local]` is the **group** name and `localhost` is the **host**, so Ansible's per-task result lines read `ok: [localhost]`. `site.yml`'s play targets the *group* `local`; the transcript reports the *host*.) By contrast the **creation** tasks (`sysadminctl -addUser`, `dscl . -create`) are **CORRECTLY expected to show `skipping:`** in this scenario — that skip is the guard working, and it is required, not a defect. **The distinction is the whole point: "the task was SELECTED into the run" is NOT "the task's guard logic RAN and produced a result."** If every query/comparison task skips, the transcript proves only that Ansible considered them — the attribute-matching logic that J8's 3-way guard depends on would never have executed, and a broken comparison would sail through invisibly. Additionally assert the `apply:` tags took effect: the extracted tasks appear under `--tags act1` (so `apply: tags: [act1, user_create, destructive]` is present — **tag inheritance does NOT propagate through dynamic `include_tasks`**), **and** they are **absent** under `--skip-tags destructive` (so `layer3-idempotency.sh:46-60`'s exclusion of real account creation still holds). | A transcript in which (1) the extracted task **names** appear under `--tags act1`; (2) **the query task and the present-and-matching comparison task each show `ok:` with an observable result — NOT `skipping:`** — on an already-exists-and-matches run, while the **creation** tasks correctly show `skipping:`; and (3) all extracted tasks are absent under `--skip-tags destructive`. **A transcript in which the query/comparison tasks are SKIPPED does NOT discharge this step, even though every task name appears.** **A `--list-tasks` output is NOT accepted.** Arbiter: **SC-12**. |
| 16 | `[OP]` | **SC-1 FINAL — the authoritative key re-verification.** **Immediately after step 15(d)** — the **full** `sudo ansible-playbook -i inventory.ini site.yml` apply, which is the **last and only** step that can touch the real key (act-3's recursive repo `chown`/`chmod` + act-5's `chmod 600` on the key) — recompute the key's hash/mode/owner/group and compare to step 0. **Ordering is unambiguous: step 15's mutating apply is (d), NOT (c); (c) is the non-mutating execution transcript (15(b2)). This step runs after 15(d) and after nothing else.** **This comparison, not step 12's, is what discharges SC-1.** | **Any mismatch is a Class-1 safety failure.** |
| 17 | `[REV]` | **`quality` stage.** Two separate recorded verdicts: `SPEC-CONFORM: PASS/FAIL`, and the adversarial BLAST-RADIUS pass (incl. the DRY dimension and the honour half of the cross-check). Then author the 5-row negative-check attestation (§Negative-check attestation), `attested_by ≠ author`. | Both verdicts + a complete attestation. |
| 18 | `[OP]`/`git-ops` | **`git`.** Commit the `ansible/**` artifacts and the `.gitignore` line. `.gleipnir/signer-identity.env` is ignored and never committed. | Nothing untracked-but-intended left behind. |

**Why the arbiter is authored before the artifacts (steps 3–4 precede 5–8).**
Test-first (Axiom 1): a static checker written *after* the YAML tends to encode
whatever the YAML happens to do. Step 4's required FAIL is what proves it
asserts something.

### Spike protocol (step 12, in order)

**The per-attempt preamble — MANDATORY before every single `bootstrap` below.**
Every numbered step that bootstraps anything executes this preamble first; it is
written once here rather than repeated, and an attempt missing any part of its
record is VOID (SC-9/SC-19):

- **P-a. Mint the attempt id (J20).** `aid=$(printf '%02d-%s-%s-%s' "$n" "$arm"
  "$stage" "$(date -u +%Y%m%dT%H%M%SZ)")`; then `mkdir "<root>/logs/$aid"` —
  **bare `mkdir`, fresh directory, never reused.** No attempt ever writes into
  another attempt's directory, and no check may be satisfied by another
  attempt's line.
- **P-b. Plist-ownership check, THEN write (J22, and the STOP/rewrite
  distinction).** Run the check in §Plist ownership below and only then write
  this attempt's plist, substituting `ATTEMPT_ID` → `$aid` in
  `StandardOutPath`/`StandardErrorPath` (and, for stage 2, the wrapper
  `ProgramArguments` + `GLEIPNIR_MARKER_KEY_FILE`).
- **P-c. J7 hygiene — gated on LABEL ownership, not plist ownership.** If
  `launchctl print <domain>/<L>` shows the label already present, first run the
  **label-authorization gate** in §Label ownership below: proceed **only** if
  this run's own `created.env` records `LABEL_x_CREATED=true` for **that specific
  label**; otherwise **STOP** (an unrelated pre-existing job is not ours to
  bootout). Then `bootout` the previous label; then prove `8765` free with
  `lsof -nP -iTCP:8765 -sTCP:LISTEN` (empty). Record all of it, command +
  status, into `<root>/outcome/attempt-$aid.txt`. **A non-empty `lsof` here means
  the attempt is a TEST-SETUP failure and is VOID** — never a candidate result
  (E-4).
- **P-d. Bootstrap** (itself gated by the same label-authorization check when the
  label is already present), **then record `LABEL_x_CREATED=true` — and ONLY if
  that `bootstrap` call itself genuinely succeeded** (exit 0 and a subsequent
  `launchctl print <domain>/<L>` showing the job). **Then collect from
  `<root>/logs/$aid/{out,err}`** — *this attempt's own directory and no other
  file* — into `<root>/outcome/attempt-$aid.txt`, and `bootout`.

#### Plist ownership — the STOP rule vs. the authorized rewrite (J22)

The pre-write collision check and the per-attempt plist rewrite are **not** in
conflict, because they are asking about **two different things**. Before each
plist write, at path `<p>`, for the arm's label `<L>`:

```sh
# (1) Nothing there at all -> free to create, then record provenance.
if [ ! -e "$p" ] && ! launchctl print "$domain/$L" >/dev/null 2>&1; then
    : write the plist FILE
    # PLIST_x_CREATED records the FILE write, and is appended ONLY after that
    # write itself genuinely succeeded (nonzero exit / partial write => do NOT
    # record). NOTHING about the LABEL is recorded here -- no bootstrap has
    # been attempted yet, let alone succeeded.
    : if the plist file write succeeded:
    :     append PLIST_x_CREATED=true / PLIST_x_PATH="$p"
    :       to <root>/created.env    # first writer wins (J22)

# (2) It exists AND THIS RUN's own manifest records that WE created it
#     -> WE OWN IT. Overwriting is EXPECTED and authorized; no STOP.
elif grep -q "^PLIST_x_PATH=$p\$" <root>/created.env 2>/dev/null \
  && grep -q '^PLIST_x_CREATED=true$' <root>/created.env 2>/dev/null; then
    : rewrite the plist in place for this attempt (new ATTEMPT_ID, new
    : ProgramArguments for stage 2, ...) -- provenance ALREADY recorded, so
    : do NOT re-append; CONFIRM agreement instead (J22: first writer wins).

# (3) It exists and THIS RUN's manifest does NOT record it as ours
#     -> UNRELATED PRE-EXISTING ARTIFACT. STOP.
else
    : STOP. Record the path, its mtime and its Label verbatim. Do NOT
    : overwrite it, do NOT adopt it, do NOT record it in created.env, and do
    : NOT let teardown remove it -- it is not ours to remove (J9).
fi
```

- **Case (3) is what "never overwrite" means:** an artifact **this run did not
  create**. Adopting it would let teardown delete a pre-existing launchd job.
- **Case (2) is the authorized rewrite:** the manifest is the **authorization
  record**. Once `created.env` says we created `<p>`, every later attempt in the
  same run may rewrite `<p>` freely — a new `ATTEMPT_ID`, stage-1→stage-2
  `ProgramArguments`, the J6 env arms — because rewriting a file we already own
  and have already taken responsibility for removing creates **no new** teardown
  obligation. The naive "if it exists, STOP" rule applied to case (2) would make
  the **second** attempt of a run trip over the **first** attempt's own plist,
  which is why the two cases are separated here explicitly.
- If `created.env` is **absent** when a plist already exists, that is case (3)
  by construction (no manifest ⇒ no proof of ownership) ⇒ **STOP**.

#### Label ownership is a SEPARATE authorization from plist-file ownership (J22)

**A plist file and a launchd label are two distinct created objects, with two
distinct provenance flags and two distinct authorization checks.** Conflating
them is a real adoption hole: a plist file this run wrote at path `<p>` says
**nothing** about whether this run created the launchd **label** `<L>` — the
label may have been bootstrapped by a previous run, by another tool, or by the
user, from a *different* plist path entirely. The two flags therefore have
different write moments and different readers:

| Flag | Recorded ONLY after | Never recorded at |
|---|---|---|
| `PLIST_x_CREATED=true` (+ `PLIST_x_PATH=<p>`) | the **plist FILE write itself** genuinely succeeded | any point before the file exists on disk |
| `LABEL_x_CREATED=true` | the **`launchctl bootstrap` call itself** genuinely succeeded (exit 0, **and** `launchctl print <domain>/<L>` subsequently shows the job) | plist-file-write time — writing a file and starting a service are **different steps**, and the file write cannot vouch for the bootstrap |

Writing the plist and starting the service are separated deliberately: the plist
write legitimately precedes the bootstrap, so `PLIST_x_CREATED=true` may exist
for a long time (and across several attempts) while `LABEL_x_CREATED` is still
unset — that is the normal, correct intermediate state, and it must not be
papered over by recording both flags at once.

**The label-authorization gate.** Before **ANY** `bootout` or `bootstrap`
operation that targets a label already present in its domain — i.e. wherever
`launchctl print <domain>/<L>` shows something already there — run this
**independent** check, which reads the **`LABEL_x_CREATED` flag and nothing
else**:

```sh
# Does THIS RUN's own manifest record that WE own THIS SPECIFIC label?
if launchctl print "$domain/$L" >/dev/null 2>&1; then
    if grep -q "^LABEL_${x}_CREATED=true\$" <root>/created.env 2>/dev/null; then
        : WE OWN IT -- from an earlier attempt in THIS SAME run.
        : bootout/bootstrap against <L> is AUTHORIZED (this is J7 hygiene
        : operating on our own job, exactly as intended).
    else
        : STOP. Either created.env does not mention this label at all, or the
        : only record of it belongs to a DIFFERENT run's leftover. Do NOT
        : bootout it, do NOT bootstrap over it, do NOT record it, and do NOT
        : let teardown remove it. Record <L>, its domain and its `launchctl
        : print` output verbatim, and reconcile by hand.
    fi
fi
```

- **`PLIST_x_CREATED` / `PLIST_x_PATH` are NOT accepted as authorization here,
  and this is the whole point of the separation.** Plist-file ownership must
  **NEVER** be treated as sufficient authorization for a **label** operation. A
  run that wrote `<p>` has authority over the **file** `<p>`; it acquires
  authority over the **label** `<L>` only by having successfully bootstrapped it
  and recorded `LABEL_x_CREATED=true`.
- **The dangerous sequence this closes:** this run writes its plist (so
  `PLIST_A_CREATED=true` exists), then finds label
  `dev.gleipnir.signer.spike.agent` already loaded — from a *prior* run whose
  teardown never completed. Under a plist-only check the run would read its own
  `PLIST_A_CREATED=true`, conclude "we own this", `bootout` an unrelated job, and
  record the label as ours — after which **teardown would remove a launchd job
  this run never created**, the exact failure `created.env` exists to prevent
  (J9).
- **A label present with no `LABEL_x_CREATED=true` in this run's manifest is
  always a STOP**, whether the manifest omits it, the manifest is absent
  entirely, or the manifest records it as belonging to a different run. Absence
  of a positive ownership record is never read as permission.

Then, in order:

1. **Author the probe** (`<root>/signer-probe.py`), **the stage-2 wrapper**
   (`<root>/stage2-wrap.sh`, `chmod 755`, owned readable/executable by the signer
   uid), and both plists (per the P-b ownership check).
2. **Arm A, stage 1.** Preamble P-a…P-d with `arm=A stage=1` → collect
   **`<root>/logs/$aid/{out,err}`** → record the matrix row.
3. **Arm B, stage 1.** Preamble P-a…P-d with `arm=B stage=1`, bootstrapping via
   `sudo launchctl bootstrap system
   /Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist` → collect
   **`<root>/logs/$aid/{out,err}`** — **the same `{out,err}` filenames arm A
   collects, because both arms' plists now write to
   `logs/<attempt-id>/{out,err}` and the collection command is derived from the
   same `$aid`** (J20 closes the old `agent.*`-written / `daemon.*`-read
   mismatch) → record the row.
4. **Stage 2**, on each arm whose stage 1 showed `os.getuid() == <signer-uid>`:
   1. Rewrite that arm's plist to the **STAGE 2** template above — via the P-b
      ownership check, which lands in **case (2)** (our own manifest records this
      plist) so the rewrite is authorized and no STOP fires.
   2. Confirm, **before bootstrapping**, that the plist declares
      **`GLEIPNIR_MARKER_KEY_FILE`** (the name the real module reads) pointed at
      `<root>/scratch.key`, and that `ProgramArguments` invokes
      **`/bin/sh <root>/stage2-wrap.sh <repo>/.venv/bin/python`** — **not** a bare
      `-m gleipnir.approval.mcp_server`. A stage-2 attempt that bootstraps the
      module directly, or declares `GLEIPNIR_SPIKE_KEY_FILE`, is **VOID** (J18):
      it observes nothing and supplies the module no key.
   3. Preamble P-a…P-d with `arm=<A|B> stage=2`.
    4. **Classify with the listener-level discriminators, not the exit status —
      VOID setup faults FIRST, then check IDENTITY before letting a bind result
      terminate classification.** The table's **row 1 is the EADDRINUSE/setup-fault
      void gate** (an attempt showing `exiting without a bound listener` is VOID
      **whatever uid it ran as** — that pairing is a port-conflict harness fault,
      not a launchd finding); **row 2 is the uid/interpreter identity gate**, ahead
      of the bind row; and the POSITIVE row restates those identity conditions
      itself:
      **a bind achieved at the WRONG uid is `(c) NEGATIVE/wrong-uid-or-exec`, not
      `(e) POSITIVE`** — launchd failing to honour `UserName` is exactly the
      negative the spike is looking for, so it must never be short-circuited by a
      successful bind. A positive class requires **BOTH** correct-uid **AND**
      live-bind.
      The bind question is answered **only** by the wrapper's **`WRAP-BIND-LIVE`**
      line — an `lsof -nP -p <child-pid> -a -iTCP:8765 -sTCP:LISTEN` poll that
      intersects **this child's own PID** with the listening socket **while the
      child is still alive**, before `wait` reaps it. Also grep this attempt's
      `err` for the two listener strings `listener thread exiting fatally` and
      `exiting without a bound listener`. Then assign **exactly one** J19 class by
      walking the §`stage2-classify.md` **ordered** table top-to-bottom and taking
      the **first matching row**, recording which row number decided it.
      **`WRAP-CHILD-EXIT 0` alone establishes nothing** — verified: a fatal
      `KeyUnavailable` is caught inside `_run_listener` and returns normally
      (`mcp_server.py:298-314`), after which the **separate**
      `mcp.run(transport="stdio")` path (`:348-350`) hits EOF on launchd's
      `/dev/null` stdin and the process exits 0. A clean exit is therefore
      produced by (a), (d) **and** (f) alike.
      **No post-mortem port check may be used:** a port probe run *after* `wait`
      cannot attribute a listener to this child (its sockets are closed and any
      match may be another process entirely), which is why the old
      `WRAP-BIND-AFTER` line was **removed** rather than merely down-weighted.
   5. **If `WRAP-BIND-LIVE` is not `yes`, the attempt CANNOT be positive or
      healthy.** With no affirmative bind observation, classification falls
      through to a fatal-line row or to the **(f) INCONCLUSIVE** catch-all
      (E-8) — and healthy-looking uid/interpreter/key lines **do not** rescue it,
      because all three are captured *before* the child runs. It may **not** be
      written up as (d) "stdio-EOF with a healthy listener": (d) is reachable
      **only** as a refinement of the POSITIVE row's bind-**and**-correct-uid
      observation (table row 3). Concluding a healthy
      listener from the absence of an error is exactly the silence-promoted-to-
      success failure J25 forbids.
   *If no arm qualified, stage 2 is correctly SKIPPED and the report says so —
   a negative finding, not a gap.*
5. **Env arms (J6).** E1: a plist-declared `GLEIPNIR_SPIKE_DECLARED=declared-ok`
   — does the probe see it? E2: `GLEIPNIR_SPIKE_SHELLONLY=shell-only` exported in
   the bootstrapping shell and **absent** from the plist — does the probe see it?
   Each arm runs the full preamble (its own `$aid`, its own log dir, its own
   hygiene record). Conclusions are written about **exactly these two variables
   and nothing else**.
6. **Negative control (J5) — FIRST the baseline-existence branch, then the four
   steps.** This step is **conditional by design**, and the branch is taken
   explicitly and recorded, never assumed:

   **Step 6.0 — BRANCH: does a working baseline exist?** Inspect the recorded
   stage-1 matrix rows from steps 2–3. A **working baseline** exists iff **at
   least one arm** produced an attempt whose own log dir shows **both**
   `PROBE-UID <signer-uid>` (the signer uid, not the operator's) **and**
   `PROBE-KEYREAD-OK`.

   - **If NO arm qualifies ⇒ take the N/A-BY-DESIGN branch and STOP here.**
     Record verbatim in the report, under §F-1 negative control: *"ATTEMPTED;
     no working baseline existed to break — no arm ran as the signer uid with a
     successful key read (see the outcome matrix rows). SC-10 is
     **N/A-BY-DESIGN** per J5, not skipped and not failed."* Cite the specific
     matrix rows that establish it. **Do not run steps 6.1–6.4** — without a
     baseline they cannot distinguish "the break caused the denial" from "it
     never worked at all", which is precisely what J5 forbids. This is an
     honestly-reported outcome and **SC-10 passes in its N/A form**.
   - **If at least one arm qualifies ⇒ steps 6.1–6.4 below are MANDATORY and
     UNWEAKENED**, on a qualifying arm. Record which arm and which matrix row
     established the baseline.

   Then, in this order and no other:
   1. **Baseline:** with `<root>/scratch.key` at signer:signer 0600, run the
      preamble and bootstrap the probe, and confirm **this attempt's own**
      `logs/$aid/out` records a **successful** key read (byte count and the
      path). *If this fresh baseline does not succeed, the control is void — do
      not proceed to step 2.*
   2. **Break:** `sudo chmod 000 <root>/scratch.key` (owner unchanged, so the
      break is unambiguously a permission break).
   3. **Capture:** preamble, bootstrap, and confirm **this attempt's own**
      `logs/$aid/err` contains **both** the exact path `<root>/scratch.key`
      **and** a specific permission denial (`Errno 13` / `Permission denied`).
      A generic failure, a traceback without the errno, or a silent exit
      **fails** this control. **Because the log directory is fresh (J20/P-a),
      a match here cannot be a stale line from step 1 or from any earlier
      attempt** — which is the whole reason the control is trustworthy.
   4. **Restore:** `sudo chmod 600 <root>/scratch.key`, preamble, bootstrap,
      and confirm the successful read again **in the restored attempt's own log
      dir**. *Without this fourth step the control cannot distinguish "the break
      caused it" from "it stopped working for another reason."*

---

## 5. Stress-test — acceptance criteria

**Class 1 (MUST PASS).** A Class-1 failure means Plan A is **not done**.
**Class 2 (RECORDED OUTCOME).** These record what the host actually did; a
negative result is a legitimate finding and does **not** fail Plan A.

| # | Class | Criterion | Evidence |
|---|---|---|---|
| **SC-1** | **1 (safety)** | `.gleipnir/keys/marker.key` is byte-, mode-, owner- and group-identical to the step-0 baseline, verified **after step 15(d)** — the **full** `site.yml` apply, which is the **last and only** step that can touch it (act-3's recursive repo `chown`/`chmod`, act-5's key `chmod 600`). **Not 15(c): that is the non-mutating execution transcript** | `shasum -a 256` + `stat -f '%Sp %Su %Sg %z'` pairs, before and after, quoted in the report. **Step 12's earlier check is a convenience; step 16's — run immediately after 15(d) — is authoritative.** SC-1 is **INCOMPLETE (⇒ Plan A not done)** if the **post-step-15(d)** comparison is absent |
| **SC-2** | 1 (safety) | No spike artifact — scratch key, logs, manifest, probe, wrapper, plists, receipt — is inside the repo working tree | `find <repo> -newer <baseline-marker> -not -path '*/.git/*'` shows **only** the intended set, enumerated exhaustively: `ansible/**` (the four new/edited playbook artifacts + `tests/signer-static.sh` + the seven fixture trees + `tests/layer1-static.sh` + `README.md`), `.gitignore`, `.gleipnir/plans/**` (this plan + the spike report), **and `.gleipnir/signer-identity.env`** — the operator-authored identity file, which **is** a legitimate expected repo-tree write (it is gitignored, never committed, and survives teardown per J10). Its omission from this expected set would make a **correct** run fail SC-2. Anything else `find` reports is a violation |
| **SC-3** | 1 | `signer.yml`/`signer-teardown.yml` contain **no** repo-resident write path | `signer-static.sh` S2 PASSES on the real files and FAILS on fixture F2 |
| **SC-4** | 1 | No hardcoded numeric uid/gid in any new or edited Ansible artifact | `signer-static.sh` S1 PASSES / FAILS on F1; **and** `layer1-static.sh`'s widened AC-nolit (J17) covers `tasks/create-service-account.yml` |
| **SC-5** | 1 | The scratch root is created **exclusively** | S3 PASSES / FAILS on F3; **plus** the observed EEXIST failure of the second `signer.yml` run with `spike_scratch` (J11) |
| **SC-6** | 1 | The account-creation logic exists **once**, and `site.yml` genuinely consumes it | S5 PASSES / FAILS on F4; **plus** `grep -c 'sysadminctl -addUser' ansible/site.yml` == 0 and `grep -c 'dscl \. -create /Users' ansible/site.yml` == 0 |
| **SC-7** | 1 | The signer account **and** group exist, non-login, at a uid/gid ≠ 510 | `dscl . -read /Users/<name> UniqueID PrimaryGroupID UserShell NFSHomeDirectory` shows the templated ids, `/usr/bin/false`, `/var/empty`; `dscl . -read /Groups/<name> PrimaryGroupID` matches |
| **SC-8** | 1 | The launchd log directory **exists and is signer-writable BEFORE the first bootstrap** | `stat` of `<root>/logs` + a successful `sudo -u '#<signer-uid>' touch <root>/logs/.probe` **timestamped before** the first `bootstrap` |
| **SC-8b** | **2** | Whether the signer uid can execute `<repo>/.venv/bin/python` | `sudo -u '#<signer-uid>' <repo>/.venv/bin/python -c 'print(1)'` output/exit recorded. **A failure is an informative negative (E-5), not a plan defect** — it goes in the matrix and shapes the verdict |
| **SC-9** | 1 | **Every** attempt was preceded by a `bootout` and a free-port proof | Per-attempt `<root>/outcome/attempt-NN.txt` containing the `bootout` command+status and the `lsof -nP -iTCP:8765 -sTCP:LISTEN` empty result. **An attempt lacking this record is VOID** and may not appear in the matrix as a result |
| **SC-10** | 1 (**CONDITIONAL** — see the branch) | The F-1 negative control is discharged in **exactly one** of two mutually-exclusive forms, and **which form applies is determined by the recorded step-6.0 branch, not by the author's convenience**: **(FORM A — a working baseline EXISTS)** at least one arm recorded `PROBE-UID <signer-uid>` **and** `PROBE-KEYREAD-OK` ⇒ the four-step control ran in the **prescribed order** and produced a **specific** denial. **(FORM B — NO working baseline exists)** no arm did ⇒ the criterion is **`N/A-BY-DESIGN`** with an honest written record | **FORM A (mandatory and UNWEAKENED):** four transcripts, **each from its own attempt-scoped log dir** (J20) — baseline-success (with byte count), the `chmod 000`, the failure log containing **both** `<root>/scratch.key` **and** `Errno 13`/`Permission denied`, and the restored-success. A missing bracket step, or a generic failure, is a **FAIL**. **FORM B:** the report states *"ATTEMPTED; no working baseline existed to break"*, **citing the specific outcome-matrix rows** that establish no arm ran as the signer uid with a successful key read, and explicitly records SC-10 as `N/A-BY-DESIGN` per J5. **FORM B is a PASS, not a skip and not a FAIL** — J4 accepts "neither arm ran as the signer" as a valid negative finding, so demanding four transcripts unconditionally would be **mandatory-but-unattainable** and would convert an honest negative into a manufactured failure. **What is NOT permitted:** claiming FORM B while a qualifying baseline row exists in the matrix (that is an evasion, and a **FAIL**), or leaving the branch unrecorded |
| **SC-11** | 1 | Teardown is complete and idempotent, and removed **only** what this run created | `dscl . -read /Users/<name>` fails; `dscl . -read /Groups/<name>` fails (checked **separately** — E-10); scratch root absent; both plists absent; both labels absent from `launchctl print`; a second teardown is a **receipt-verified** clean no-op (SC-20); **`.gleipnir/signer-identity.env` still present** (J10, deliberate) |
| **SC-12** | 1 | `site.yml` is unregressed, **proven by a run that DEMONSTRABLY EXECUTED the extracted tasks** | (a) `sh ansible/tests/run.sh` shows no FAIL; (b) two consecutive **`site.yml --tags act1` runs, each invoked WITH `-i inventory.ini`**, both reporting `changed=0` — **a `changed=0` from a run without `-i` is a VACUOUS PASS and is rejected** (the play targets `hosts: local`, defined only in `inventory.ini:7-8`, so without it the play matches no host); (c) **an EXECUTION TRANSCRIPT (step 15(b2)) proving the GUARD LOGIC ACTUALLY RAN, not merely that tasks were selected**: under `--tags act1`, the extracted task-file's own task names appear **and** — on an already-exists-and-attributes-match run — **the `dscl`-query task and the present-and-matching comparison task each show a real `ok:` result (`changed=false`, with the registered/compared values visible under `-v`), NOT a `skipping:` line**, while the **creation** tasks correctly **do** show `skipping:`; **plus** their absence under `--skip-tags destructive`. **Two `changed=0` runs alone do NOT discharge this criterion**, because a dropped `apply:` tag would skip every task inside the dynamic `include_tasks` and still report `changed=0` (tag inheritance does **not** propagate through `include_tasks`). **Nor does a transcript in which the query/comparison tasks are SKIPPED discharge it** — every task name would still appear, so "the tasks were **selected** into the run" would masquerade as "the attribute-matching guard **executed and produced a result**". If every query/attribute-check task skips, J8's 3-way guard was never exercised and a broken comparison is invisible; that is the second, subtler hollow green this criterion exists to catch. **A `--list-tasks` output is explicitly NOT accepted** — verified: it does not expand dynamic `include_tasks` bodies, so it cannot show the extracted tasks at all; (d) the full real-box apply's task summary + AC-4 verdict recorded **and compared against step 0b's `AC4-BASELINE:`** — an AC-4 FAIL may be labelled "pre-existing" **only** on a matching baseline FAIL; a FAIL against a `PASS` baseline **is a regression** (E-11/J24(d)) |
| **SC-13** | **2** | The **outcome matrix** is complete: for each of arm A / arm B — observed uid, observed gid, `sys.executable`, port-bind result, env visibility (E1/E2), log paths, and the exact `bootstrap` command + exit status | The matrix table in the report, one row per arm per stage. **A row reading "did not run as the signer uid" or "neither arm worked" is a COMPLETE, VALID row** (J4) |
| **SC-14** | 1 | Stage 2 was attempted on **every** arm that qualified, and skipped only on arms that did not | Per-arm justification in the report, each citing the stage-1 uid observation |
| **SC-15** | **2** | The env conclusion is **scoped to what was tested** | The report states results for `GLEIPNIR_SPIKE_DECLARED` and `GLEIPNIR_SPIKE_SHELLONLY` **by name**. A conclusion of the form "launchd does not inherit shell env" is only permitted if E2 actually ran; **no** conclusion about opencode's own environment is permitted at all |
| **SC-16** | 1 | The spike report exists and states a **Plan-B verdict** | `.gleipnir/plans/signer-uid-separation-plan-a-spike-report.md` contains exactly one of: *2C viable* / *2C not viable as designed* / *2C viable with named conditions* — with the conditions enumerated in the third case |
| **SC-17** | 1 | The honesty ledger survived into the report | The report carries the three §Honesty ledger blockquotes **verbatim**, and makes no isolation or key-confidentiality claim |
| **SC-18** | 1 | The hardened negative-check attestation is complete | All 5 rows present, `attested_by ≠ author`, every `evidence` field a reproducible artifact satisfying the substance, correspondence and post-change-state rules |
| **SC-19** | 1 (integrity of evidence) | **Every attempt's evidence is attributable to that attempt ALONE** — no check in this plan is satisfiable by a stale line from a prior attempt (J20) | (i) `ls <root>/logs/` shows **one directory per attempt**, named `NN-<arm>-<stage>-<UTC>`, with a count **equal to** the number of recorded attempts (including the void ones); (ii) **no** `<root>/logs/agent.{out,err}` or `<root>/logs/daemon.{out,err}` file exists — a flat shared log file anywhere under `logs/` is a **FAIL**; (iii) every quoted transcript in the report cites its `<attempt-id>` path, and each of SC-10's four transcripts comes from a **different** `<attempt-id>`; (iv) each collected `{out,err}` path is derived from the **same** `$aid` the plist's `StandardOutPath`/`StandardErrorPath` were rewritten to — so the arm-A/arm-B **written-vs-read filename mismatch cannot recur** (both arms write and read `logs/<attempt-id>/{out,err}`) |
| **SC-20** | 1 | **Teardown's three receipt states are all implemented and all observed** (J21/J22), and a stale receipt cannot certify a new run | (i) State (1): teardown with `created.env` present performs the gated removal and writes `/private/tmp/gleipnir-signer-spike.torndown` as its **final** act, containing the UTC timestamp, the removed object names, and the consumed `created.env` **verbatim**; (ii) State (2): a second run with the manifest gone + receipt present reports a **VERIFIED clean no-op quoting the receipt**, exits 0, removes nothing — **an inference from absence alone is a FAIL**; (iii) State (3): with the receipt moved aside, a run **REFUSES LOUDLY** and removes nothing; (iv) `created.env` provenance is **append-only, first-writer-wins** — a rerun **confirms** an already-recorded flag and fails loudly on disagreement, never flips `true`→`false`; (v) plist/label removals are each gated on their own `PLIST_*_CREATED`/`LABEL_*_CREATED` flag (S6/F7); (vi) **step 11a ran** — no pre-existing `*.torndown` receipt was present when provisioning began (a stale receipt surviving into a new run could certify that run's leftovers as clean) |
| **SC-21** | 1 | **`signer-static.sh` is proven to assert what it claims** — seven complete fixture trees, each failing with its OWN specific reason token while every other check passes (J23) | For **each** of F1…F7: the fixture directory is a **complete** copy of the correct tree (all four files present — `signer.yml`, `signer-teardown.yml`, `tasks/create-service-account.yml`, `site.yml`); running `sh ansible/tests/signer-static.sh <fixture>` emits **that fixture's expected `FAIL[S<n>/<reason>]` token** (F1⇒S1, F2⇒S2, F3⇒S3, F4⇒S5, F5⇒S4/mismatch-guard-bypassed, F6⇒S4/ignore_errors, F7⇒S6); **and** `grep -c '^FAIL\[' == 1` for that run, proving **every other check PASSED**. **A nonzero exit status is NOT sufficient evidence**, and a fixture emitting 2+ `FAIL[` lines is a **FAIL of this criterion** — it means checks are firing for **absence** rather than for the intended defect, which is the false-positive suite J23 exists to prevent |
| **SC-22** | 1 | **The complete broken fixture trees coexist with a GREEN existing production `ansible-lint` pass, via a NARROWLY-SCOPED path exclusion and no global rule suppression** (J26) | (i) `sh ansible/tests/layer1-static.sh` reports **PASS: ansible-lint** with **all seven** broken fixture trees present on disk — verified necessary because `layer1-static.sh:37-47` lints **`"$root"` = the whole `ansible/` tree** (`:17`) and `ansible/.ansible-lint` had **no `exclude_paths` key** before this change, so F6's deliberate `ignore_errors: true` (a rule this repo pointedly does **not** suppress, `.ansible-lint:24-29`) would otherwise turn the **production** pass red; (ii) `git diff ansible/.ansible-lint` shows **exactly one** added key, `exclude_paths:`, whose **only** member is `ansible/tests/fixtures/broken/` (repo-root-relative, per the J26 step-4 amendment) — a broader value (`tests/`, `fixtures/`, `.`, `**`) is a **FAIL**, since it would stop linting real playbook code; (iii) **`skip_list` is byte-unchanged** — still exactly `[name[casing]]`; adding `ignore-errors` (or any rule) to it is a **FAIL of this criterion**, because it would disable the rule for `site.yml` and all future playbooks, silently reversing `.ansible-lint`'s recorded BUG-4 decision and trading a fixture problem for a production blind spot; (iv) **The exclusion is proven to be LOAD-BEARING by a DISCOVERY-BASED positive control — two runs of the SAME real invocation, differing ONLY in whether the exclusion is configured.** **Both runs use the actual discovery-based command `layer1-static.sh` runs** — `ansible-lint --config-file "$root/.ansible-lint" "$root"`, scanning the whole `ansible/` tree with the seven fixture trees on disk: **(iv-a) WITH `exclude_paths:` configured ⇒ F6 is NOT flagged** (no `ignore-errors` finding naming any path under `ansible/tests/fixtures/broken/`); **(iv-b) with the `exclude_paths:` key temporarily commented out and NOTHING else changed ⇒ the SAME scan DOES flag F6**, emitting an `ignore-errors` finding that **names `tests/fixtures/broken/F6`** — then the key is restored and (iv-a) re-observed. **Why (iv-b) is mandatory and why the earlier "lint F6 directly" form was REPLACED as UNSOUND:** the prior clause invoked `ansible-lint ansible/tests/fixtures/broken/F6` and described it as running *"outside the excluded discovery path"*, which is **false — F6 IS inside the excluded subtree `tests/fixtures/broken/`**, so that command tests a path the config excludes and its result is governed by whether an explicitly-named target overrides `exclude_paths` (an **unverified** `ansible-lint` behaviour this plan never established). It therefore proved nothing about discovery scoping. The real risk (iv) exists to close is the **vacuous exclusion**: a green (i) is equally consistent with *"the exclusion works"* and with *"F6 never tripped `ansible-lint` in the first place, so the exclusion is untested scaffolding"* — and in the latter world J26's whole justification is fiction and the exclusion could be silently mis-scoped forever. Only the **with/without contrast on the discovery-based command** discriminates those two worlds, which is the same "prove the test asserts something" discipline as step 4's required FAIL and J23's fixtures. **A green (i) WITHOUT (iv-b)'s observed FAIL does NOT discharge SC-22** |

### What would make this plan a failure

- **Class 1 (safety).** The real key differs in any of hash/mode/owner/group at
  step 16; or any spike artifact is found inside the repo tree; or the scratch
  root was adopted rather than exclusively created.
- **Class 1 (integrity of the evidence).** An attempt recorded as a candidate
  result without its J7 hygiene record; the negative control run out of order or
  producing only a generic failure; a stage-2 conclusion drawn without uid +
  interpreter evidence in the log; an env conclusion wider than what E1/E2
  tested.
- **Class 1 (regression).** `site.yml`'s act-1 no longer converges to
  `changed=0`, or the fixture harness goes red.
- **NOT a failure.** Either or both plist arms failing to run as the signer uid;
  no port bind; the signer being unable to exec `.venv/bin/python`; a stage-2
  stdio-EOF exit. These are the **findings the spike exists to produce**, and
  recording them honestly is a **PASS** of Plan A with a negative verdict for
  2C.

---

## 6. Negative-check attestation (hardened obligation — authored by `quality-reviewer`, never the author)

One row per grant/privilege-bearing change. `attested_by` **must not** be the
author. Each `evidence` field must be a literal command+output, diff, or
byte-for-byte quote, captured against the **post-change** state of the **named**
file, testing the **named** over-broad form (L-C7's substance / correspondence /
post-change-state rules).

| # | grant | intended (narrowest) scope | over_broad_form_checked | evidence (`[D]`/`[J]`) | negative result | attested_by |
|---|---|---|---|---|---|---|
| 1 | The signer OS account/group created by `ansible/signer.yml` via the shared task-file | One non-login account + one group, at the uid/gid in `.gleipnir/signer-identity.env`, shell `/usr/bin/false`, home `/var/empty`, **no `admin`/`wheel`/privileged-`staff` membership and NO sudo privilege** | Membership of `admin`, of `wheel`, or of a **privileged** `staff` grouping; **any** sudo privilege; a real login shell; a real home directory | `[D]` **all five**, post-creation, so the evidence covers the WHOLE claim rather than only the `admin` half: (i) `dscl . -read /Users/<name> UniqueID PrimaryGroupID UserShell NFSHomeDirectory`; (ii) `dsmemberutil checkmembership -U <name> -G admin`, `… -G wheel`, `… -G staff` — the **authoritative** membership test (it resolves nested/implicit membership, which a raw `GroupMembership` read does **not**); (iii) `id -Gn <name>` — the account's **complete** resolved group list, so a privileged group outside the three named above is still visible; (iv) `sudo -l -U <name>` — the **direct** sudo-privilege test, expected to report that the user is **not allowed to run sudo commands**; (v) `sudo grep -rn '<name>' /etc/sudoers /etc/sudoers.d/` — no sudoers rule names the account | `dsmemberutil` reports **"user is not a member"** for `admin` **and** `wheel` **and** `staff`; `id -Gn` lists **only** the signer's own group; `sudo -l -U <name>` reports **no** sudo privilege; **zero** sudoers matches; `UserShell` is `/usr/bin/false`, **not** a login shell; `NFSHomeDirectory` is `/var/empty` | *(reviewer)* |
| 2 | `ansible/signer.yml`'s write surface | **WRITE** targets confined to the scratch root, plus the three enumerated external paths (two plists + the receipt); **READS** of `.gleipnir/signer-identity.env` are legitimate and expected | A **write**-module path resolving into the repo — a `file`/`copy`/`template`/`lineinfile`/`blockinfile` `path:`/`dest:`, or a `command:`/`shell:` redirection (`>`/`>>`/`tee`), pointing at `{{ repo }}`/`.gleipnir`/`keys/` | `[D]` **the read/write distinction is the point — a blanket whole-file grep is WRONG here** and would flag the mandatory E-1 identity read as a violation. **This applies to item (i) itself, not merely to item (iii): a bare `grep -nE '^[[:space:]]*(path\|dest):'` catches EVERY `path:`/`dest:` line regardless of enclosing module — including `stat: path: "{{ repo }}/.gleipnir/signer-identity.env"`, a READ-only check — so applying the write-target restriction to that raw match set would flag the mandatory E-1 identity read as a violation. Item (i) therefore CLASSIFIES FIRST and restricts SECOND, using the SAME §S2 read/write classifier item (iii) uses (no second, divergent classification is invented here).** So: **(i) — a THREE-PHASE method, in this order.** **(i-a) ENUMERATE candidates:** `grep -nE '^[[:space:]]*(path\|dest\|src):' ansible/signer.yml ansible/signer-teardown.yml` — the raw match set, **not yet subject to any restriction**. **(i-b) CLASSIFY each match by its ENCLOSING ANSIBLE MODULE**, per the §S2 read/write classifier table: for each matched line, walk **upwards** to the nearest enclosing module key of its task and record that module name (`ansible.builtin.` prefixes and bare short names both count). **READ-ONLY modules — `stat`, `slurp` (plus a `when:`/`assert:` reference, which is not a module target at all) — are EXCLUDED ENTIRELY from the write-target check**, and are carried instead into item (iii)'s read adjudication. **WRITE-CAPABLE modules — `copy`, `template`, `file`, `lineinfile`, `blockinfile`, `unarchive`, `get_url`, `ini_file`, and `command:`/`shell:` with a redirection (item (ii)) — are RETAINED.** **(i-c) RESTRICT only the retained (write-capable-module) set:** every remaining match must begin with `{{ spike_root }}` **or** be one of the **three** enumerated external literals (the two plist paths + the teardown receipt). **A `stat`/`slurp` match reaching phase (i-c) is a METHOD error, not a finding** — it means the classification step was skipped, and the attestation must be redone rather than reported as a violation. (ii) `grep -nE '(>>?[[:space:]]*\|tee )' ansible/signer.yml ansible/signer-teardown.yml` — no shell redirection to a repo path. (iii) `grep -nE '\{\{ *repo *\}\}\|\.gleipnir\|keys/' ansible/signer.yml ansible/signer-teardown.yml` — **matches are EXPECTED, not forbidden**; for each match, confirm from its surrounding task that it is under a **read-only** module (`slurp: src:`, `stat: path:`, a `when:`/`assert:`) per the §S2 classifier, and that **none** is under a write module. `[J]` the per-match read/write adjudication in (i-b) and (iii) — **the same classifier applied at both points, so the two items cannot disagree** | **Every RETAINED (write-capable-module) target from (i-c)** is scratch-root-relative or one of the three enumerated external literals; **zero** write-module paths and **zero** shell redirections resolve inside the repo working tree. **The `stat`/`slurp` matches EXCLUDED at (i-b) — in particular `stat: path:` on `.gleipnir/signer-identity.env` — are READ-only, correctly present, and NOT subject to the write-target restriction**; their absence would be the defect (E-1), not their presence. The item (iii) matches agree with (i-b)'s classification | *(reviewer)* |
| 3 | The `.gitignore` addition (∈ `E`) | Exactly one exact-path line, `.gleipnir/signer-identity.env` | A glob — `.gleipnir/*.env`, `*.env`, `*.env*`, `.gleipnir/*` — silently ignoring future env files | `[D]` `git diff .gitignore` **and** `grep -nE '(^\|/)\*[^/]*\.env\|^\*\.env\|\.gleipnir/\*[^/]*\.env\|^\.gleipnir/\*$' .gitignore` on the applied file. **The regex is deliberately anchored on a literal `*` glob metacharacter** — the earlier form `^\**\.env\|\.gleipnir/\*` **false-positives on the legitimate pre-existing `.envrc` entry** (verified: `.gitignore:21` is `.envrc`; `^\**\.env` matches it with **zero** `*`s, since `\**` accepts the empty string), which would make the attestation report a violation that does not exist. This form requires an **actual** `*` adjacent to `.env` (or the bare `.gleipnir/*` form), so it catches `*.env`, `*.env*`, `.gleipnir/*.env` and `.gleipnir/*` while **never** matching `.envrc` or `.gleipnir/agent-identity.env` | **Zero** matches: no glob form is present. `.envrc` (`:21`) and `.gleipnir/agent-identity.env` (`:17`) are **legitimate pre-existing exact-path entries and are correctly NOT matched**. `git diff` adds **exactly one** line, `.gleipnir/signer-identity.env`, by exact path | *(reviewer)* |
| 4 | `site.yml`'s adoption of the shared task-file | One `include_tasks` at act 1; acts 3/4/5/6 and AC-4 byte-unchanged | Collateral edits outside act 1 (esp. act-5's key lock or AC-4's assertion) | `[D]` `git diff ansible/site.yml` — reviewed hunk by hunk | No hunk touches acts 3–6 or AC-4; the diff is confined to act 1 | *(reviewer)* |
| 5 | The shared task-file's 3-way guard | Absent→create, matching→skip, mismatch→**fail** | A silent-adopt path: any branch that proceeds on a mismatch, or a bare `rc != 0` two-way guard | `[D]` **a textual grep for a `MISMATCH-GUARD` comment proves only that a comment exists near something — it establishes NOTHING about control flow**, so the evidence is the **executable** proof instead: (i) the **fixture F5 run** — `sh ansible/tests/signer-static.sh ansible/tests/fixtures/broken/F5` emits **`FAIL[S4/mismatch-guard-bypassed]`** with `grep -c '^FAIL\[' == 1`, proving S4 actually **detects** a creation task whose `when:` bypasses the mismatch sentinel; (ii) the **fixture F6 run** — same shape, emitting S4's `ignore_errors` token, proving S4 detects a swallowed `fail`; (iii) `sh ansible/tests/signer-static.sh` **PASSES S4 on the applied real file** — so the check that demonstrably catches both bypass forms finds none in the shipped artifact; (iv) `grep -nE '^[[:space:]]*when:' ansible/tasks/create-service-account.yml` — every creation task's `when:` enumerated and each confirmed to carry the absent-sentinel conjunction. **(i)+(ii) are what make (iii) meaningful**: without a fixture proving S4 fires, an S4 PASS is indistinguishable from an S4 that asserts nothing | S4 **fires** on F5 and F6 with their specific tokens (so the control-flow check is live, not vacuous) and **passes** on the applied file; **zero** creation tasks have a `when:` satisfiable while a mismatch is true; the mismatch `fail` carries **no** `ignore_errors`/`failed_when: false` and is not inside a swallowing `rescue:` | *(reviewer)* |

---

## 7. Execution Workflow

Enough for each actor to act without rediscovering the protocol.

### Capability split (verified, not assumed)

| Actor | May do | May NOT do |
|---|---|---|
| `gleipnir-plan` | Write `.gleipnir/plans/**` — this plan and the spike report | Everything else. No code, no OS act, no Tier-3 write |
| `gleipnir-code` | `edit` `ansible/**` (playbooks, shared task-file, tests, fixtures, README) | **Run** any of it (`bash: "*": deny` + a sandbox-only allowlist, `gleipnir-code.md:34-62`); write **any** `.gleipnir/**` path (`:14`); touch `.gitignore` (∈ `E`) |
| `quality-reviewer` | Read everything; issue the two `quality` verdicts; author the negative-check attestation | Author the artifacts it reviews; self-clear a divergence (L-C8) |
| **operator** | Every OS act: `dscl`/`sysadminctl` (via the playbooks), `launchctl`, plist placement, `chmod`/`chown`, running Ansible, running `ansible/tests/*.sh`, authoring `.gleipnir/signer-identity.env`, the `.gitignore` line, the probe and plists | — |
| `git-ops` | The `git` stage | Anything else |

### Standing rules for the operator during the spike

1. **Never skip J7 hygiene.** Before every bootstrap: `bootout` the previous
   label, then prove `8765` free. An attempt without that record is VOID
   (SC-9) — recording it as a result is the exact false-success this plan
   guards against.
2. **Never adopt an existing scratch root.** `mkdir` failing EEXIST is correct
   behaviour. Run `signer-teardown.yml`; never `mkdir -p`.
3. **The scratch key is never the real key.** Generate it from `/dev/urandom`.
   Never copy, symlink, or derive it from `.gleipnir/keys/marker.key`. `chmod`
   the **scratch** key only.
4. **Record negatives as negatives.** "Ran as the wrong uid", "did not bind",
   "neither arm worked", "cannot exec the interpreter" are the spike's *output*.
   Do not retry until you get the answer you expected, and do not adjust the
   arms to manufacture a pass.
5. **Keep every conclusion inside its evidence.** Especially J6: only the two
   named variables were tested; nothing about opencode's environment follows.
6. **Step 16 is not optional.** The final key re-verification, after the full
   `site.yml` apply, is what discharges SC-1. Skipping it leaves SC-1
   INCOMPLETE and Plan A **not done**, even if everything else passed.

### Ready-to-apply artifacts (operator; shapes, not agent-written code)

**`.gleipnir/signer-identity.env`** — mirrors `agent-identity.env`'s shape:

```
GLEIPNIR_SIGNER_UID=<free id, verified with `dscl . -list /Users UniqueID`, != 510>
GLEIPNIR_SIGNER_GID=<free id, verified with `dscl . -list /Groups PrimaryGroupID`>
```

**`.gitignore`** — one appended line (J13):

```
# host-local signer service-account identity (per-machine uid/gid; never committed)
.gleipnir/signer-identity.env
```

**`<root>/signer-probe.py`** — the stage-1 capability probe (J3). Everything it
prints goes to stdout/stderr, which launchd captures into
`StandardOutPath`/`StandardErrorPath`:

```python
# /private/tmp/gleipnir-signer-spike/signer-probe.py — THROWAWAY spike probe.
# Prints, in order: uid/gid, interpreter, cwd, the two named env vars, the
# scratch-key read result, and the 127.0.0.1:8765 bind result. Never touches
# the real key. Never imports gleipnir.
import os, socket, sys

print("PROBE-UID", os.getuid(), "GID", os.getgid(), flush=True)
print("PROBE-EXE", sys.executable, flush=True)
print("PROBE-CWD", os.getcwd(), flush=True)
print("PROBE-ENV-DECLARED", repr(os.environ.get("GLEIPNIR_SPIKE_DECLARED")), flush=True)
print("PROBE-ENV-SHELLONLY", repr(os.environ.get("GLEIPNIR_SPIKE_SHELLONLY")), flush=True)

key = os.environ.get("GLEIPNIR_SPIKE_KEY_FILE", "")
print("PROBE-KEYPATH", key, flush=True)
try:
    with open(key, "rb") as fh:
        print("PROBE-KEYREAD-OK bytes", len(fh.read()), flush=True)
except OSError as exc:
    # The specific errno + the exact path is what SC-10 requires.
    print("PROBE-KEYREAD-FAIL", key, repr(exc), file=sys.stderr, flush=True)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", 8765))
    s.listen(1)
    print("PROBE-BIND-OK 127.0.0.1:8765", flush=True)
except OSError as exc:
    print("PROBE-BIND-FAIL", repr(exc), file=sys.stderr, flush=True)
finally:
    s.close()
print("PROBE-DONE", flush=True)
```

**`<root>/stage2-wrap.sh`** — the stage-2 observability wrapper (J18). **This is
what stage 2's plist executes, NOT the module directly.**

> **Why it must NOT `exec`.** `exec` **replaces the shell's own process image**
> with the module's: after `exec .venv/bin/python -m …` there is no wrapper
> process left to run *any* subsequent line, so **nothing can observe or record
> the child's exit status** — the single most important thing the wrapper exists
> to capture (J18). The wrapper therefore runs the module as a **genuine child**
> (`"$py" -m … &` then `wait "$pid"`, capturing `$?`), stays alive, and writes
> its record **after** the child is reaped.

```sh
#!/bin/sh
# /private/tmp/gleipnir-signer-spike/stage2-wrap.sh -- THROWAWAY spike wrapper.
# Runs the REAL module as a CHILD (never `exec` -- see the plan: `exec` would
# replace this process and leave nothing to record the exit status) and writes
# a WRAP-* record to stdout/stderr, which launchd captures into the
# attempt-scoped StandardOutPath/StandardErrorPath.
#
# $1 = the interpreter path (REPO/.venv/bin/python), passed from the plist.
set -u
py="$1"
root=/private/tmp/gleipnir-signer-spike

echo "WRAP-ARGV $0 $*"
echo "WRAP-UID $(id -u) GID $(id -g)"
echo "WRAP-INTERP-ARG $py"
# Interpreter path AS THE CHILD SEES IT -- proves which python actually ran.
echo "WRAP-SYS-EXECUTABLE $("$py" -c 'import sys; print(sys.executable)' 2>&1)"
# Which key env vars are PRESENT (names + whether set), never contents.
echo "WRAP-ENV-MARKER_KEY_FILE ${GLEIPNIR_MARKER_KEY_FILE-<unset>}"
echo "WRAP-ENV-SPIKE_KEY_FILE ${GLEIPNIR_SPIKE_KEY_FILE-<unset>}"
# Is the key path the module will read actually readable AT THIS UID? This is
# the J19 (b)-vs-(a) discriminator, captured BEFORE the module runs.
if [ -r "${GLEIPNIR_MARKER_KEY_FILE-/nonexistent}" ]; then
    echo "WRAP-KEY-READABLE yes ${GLEIPNIR_MARKER_KEY_FILE-}"
else
    echo "WRAP-KEY-READABLE no ${GLEIPNIR_MARKER_KEY_FILE-<unset>}"
fi

# --- the module as a CHILD, not an exec ---------------------------------
"$py" -m gleipnir.approval.mcp_server &
child=$!
echo "WRAP-CHILD-PID $child"

# --- LIVE bind observation: poll THIS CHILD's OWN sockets WHILE IT LIVES --
# This is the ONLY sound positive bind evidence. A post-`wait` port check is
# WORTHLESS: by then the child is reaped and its sockets are closed, so a
# match could be ANY other process and a miss proves nothing about what this
# child did while alive. `lsof -p <child> -a -i TCP:8765 -sTCP:LISTEN`
# intersects (-a = AND) the PID with the listening socket, so a hit is
# attributable to THIS PID and no other. Poll because the bind is racing the
# wrapper: up to ~50 x 0.1s = 5s, exiting the loop the instant it is seen.
bind_seen=no
bind_at=
i=0
while [ "$i" -lt 50 ]; do
    # Child already gone? Stop polling -- nothing more can bind.
    kill -0 "$child" 2>/dev/null || break
    if lsof -nP -p "$child" -a -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
        bind_seen=yes
        bind_at="poll-$i"
        break
    fi
    i=$((i + 1))
    sleep 0.1
done
# WRAP-BIND-LIVE is the load-bearing discriminator for J19 (e). `yes` means
# THIS child's PID held a LISTEN socket on 8765 while it was alive.
echo "WRAP-BIND-LIVE $bind_seen ${bind_at:-none} pid=$child"
# Was the child still alive when polling ended? Separates "exited before it
# could bind" from "alive but never bound within the window".
if kill -0 "$child" 2>/dev/null; then
    echo "WRAP-CHILD-ALIVE-AT-POLL-END yes"
else
    echo "WRAP-CHILD-ALIVE-AT-POLL-END no"
fi

wait "$child"
status=$?
# The wrapper is STILL ALIVE here -- this line is impossible after an `exec`.
echo "WRAP-CHILD-EXIT $status"
echo "WRAP-DONE"
```

> **Why there is no `WRAP-BIND-AFTER` line.** An earlier draft ended the wrapper
> with a post-`wait` `lsof -iTCP:8765` count. That check is **removed as
> unsound, not merely weak**: `wait` has already reaped the child, so the
> child's sockets are closed by the time it runs. A non-zero count could be
> **any other** listener (in particular the session's own opencode-spawned
> approval MCP, which is exactly what J7 exists to detect), and a zero count is
> equally consistent with "bound perfectly, then exited". It therefore
> establishes **nothing about what THIS child did while alive** — the only
> question stage 2 asks. It is replaced by **`WRAP-BIND-LIVE`**, which
> intersects the child's **own PID** with the listening socket **while the
> child is still running**. Only `WRAP-BIND-LIVE yes` may be read as a bind
> observation; **no post-mortem port state may ever be promoted to J19 (e)**.

> **The wrapper's record is necessary but NOT sufficient — read `WRAP-CHILD-EXIT
> 0` as evidence of NOTHING about the listener.** Verified in
> `src/gleipnir/approval/mcp_server.py`: a fatal key failure is caught inside
> `_run_listener` (`:298-314`), logged, recorded via `mark_unavailable()`, and
> the function **returns without raising**; the process then proceeds down the
> **separate** `mcp.run(transport="stdio")` path (`:348-350`), reads EOF from
> launchd's `/dev/null` stdin, and **exits 0**. So a clean exit is exactly what
> both (a) "no key at all" and (d) "healthy listener, absent stdio peer" produce.
> **Classification MUST be driven by the listener-level discriminators below, not
> by `WRAP-CHILD-EXIT`.**

**`<root>/stage2-classify.md`** — the operator's classification rule, applied to
each stage-2 attempt's `<attempt-id>/{out,err}` (J19's six buckets).

**This table is an ORDERED DECISION PROCEDURE, evaluated top-to-bottom, and the
FIRST matching row WINS and terminates classification.** The order is what makes
the rows **mutually exclusive**: every row's conditions are read as *"this row's
test matches AND no earlier row's test matched"*, so no attempt can satisfy two
rows, and the buckets cannot disagree with one another. Exactly one class is
assigned per attempt (J19), and the assignment must record **which row number**
produced it.

**The governing rule — NO SILENCE IS EVER PROMOTED TO SUCCESS (J25).** A
healthy/positive classification requires **POSITIVE, AFFIRMATIVE evidence that
the listener actually bound** — i.e. `WRAP-BIND-LIVE yes`, an observation of
**this child's own PID** holding a LISTEN socket **while it was alive**. The
absence of failure evidence is **not** evidence of success. "Correct uid +
executable interpreter + readable key + no fatal line + no bind" is **silence
about the listener**, and silence classifies as **(f) INCONCLUSIVE** — never as
a healthy bucket.

**The second governing rule — A BIND IS ONLY POSITIVE IF THE RIGHT UID ACHIEVED
IT (J25).** `WRAP-BIND-LIVE yes` answers *"did something bind?"*; it does **not**
answer *"did the SIGNER bind?"*, and only the latter is evidence for 2C. The
identity gate therefore **precedes the bind row** — it is **row 2**, immediately
after the setup-fault void row (see the third governing rule) — and the POSITIVE
row carries the identity conditions itself, so **correct-uid and live-bind are
evaluated together**. A
bind at the operator's uid, at `root`, or at any uid that is not the signer's is
**`(c) NEGATIVE/wrong-uid-or-exec`** — it means launchd did not honour
`UserName`, which is the negative finding the spike exists to surface, not a
success.

**The IDENTITY GATE precedes the BIND row — a bind observation may NEVER
terminate classification as POSITIVE before the uid has been checked.** This is a
**second ordering defect, distinct from the silence-promoted-to-success one
above**: in an earlier revision of this table the bind row came first, accepted
`WRAP-BIND-LIVE yes` **unconditionally**, and stopped there, while the wrong-uid
discriminator sat far below. Because the procedure is first-match-wins, an
attempt that **successfully bound the port while running as the WRONG uid** (the
operator's, or `root`, or anything that is not the signer account) would be
classified **(e) POSITIVE** and **never reach** the wrong-uid check at all —
certifying as a success the exact thing the spike exists to disprove. A bind by
the wrong uid is **not** evidence that 2C works; it is evidence that launchd
ignored `UserName`, which is a **negative** finding (J4). Hence: **identity is
evaluated BEFORE any row can terminate as POSITIVE, AND the POSITIVE row carries
the identity conditions in its own right** — belt and braces, so the guarantee
does not depend on row order alone. **A genuinely positive classification
requires BOTH correct-uid AND live-bind.**

**The third governing rule — A SETUP FAULT IS VOIDED BEFORE ANY RESULT-BEARING
ROW, INCLUDING THE IDENTITY GATE. The EADDRINUSE/setup-fault check is ROW 1.**
This closes a **third ordering defect**, introduced by the identity-before-bind
fix above and found on a later pass: when the identity gate was hoisted to row 1
it landed **ahead of the EADDRINUSE row**, so an attempt exhibiting **BOTH** a
wrong uid **AND** `exiting without a bound listener` matched the identity row
first and was recorded as a **candidate NEGATIVE `(c)`** — never reaching the
setup-fault row that should have caught it. But that pairing is precisely the
**signature of a port-conflict TEST-SETUP fault** (J7/E-4): the port was already
held, so the process could not bind, and **whatever uid it happened to run as is
irrelevant** — the attempt produced **no result about 2C in either direction**
and must be **VOID**, not filed as a feasibility finding. Recording it as `(c)`
would put a **test-harness defect into the outcome matrix as evidence about
launchd**, contaminating the very verdict the matrix feeds. Hence the ordering is
**(1) setup fault ⇒ VOID, (2) identity ⇒ `(c)`, (3) bind ⇒ `(e)`**, which
preserves **both** guarantees simultaneously: **a setup-fault attempt is voided
regardless of what uid it ran as**, *and* **a wrong-uid attempt can never be
classified POSITIVE**. Voiding is always the conservative answer — a void attempt
is simply re-run after the port is freed, whereas a mis-filed `(c)` silently
becomes a false negative in the report.

| Row | Observed in the attempt's OWN log dir (first match wins) | J19 class |
|---|---|---|
| **1** | **SETUP-FAULT VOID GATE — evaluated FIRST, before ANY result-bearing row including the identity gate.** stderr contains `exiting without a bound listener` (EADDRINUSE) | **J7 TEST-SETUP fault** — attempt **VOID** (SC-9), not a candidate result **in either direction**. **This row fires even when `WRAP-UID` is ALSO wrong:** that pairing is the *signature* of a port-conflict setup fault, and the uid the faulted attempt happened to run as is **irrelevant** — a harness defect must never enter the outcome matrix as a `(c)` finding about launchd. Re-run the attempt after freeing the port |
| **2** | **IDENTITY GATE — evaluated before any bind observation may terminate classification.** `WRAP-UID` ≠ the signer uid, **or** `WRAP-SYS-EXECUTABLE` shows the interpreter could not be executed | **(c) NEGATIVE/wrong-uid-or-exec** — a genuine, informative negative for 2C (J4). **This row fires even when `WRAP-BIND-LIVE yes` is also present:** a bind achieved at the wrong uid is a wrong-uid finding, **never** a POSITIVE one, because launchd failing to honour `UserName` is precisely the negative the spike is looking for |
| **3** | `WRAP-BIND-LIVE yes` — this child's **own PID** held a LISTEN socket on `127.0.0.1:8765` **while it was alive** — **AND** `WRAP-UID` = the signer uid **AND** `WRAP-SYS-EXECUTABLE` = the `.venv` python (identity re-asserted **in this row's own conditions**, not merely inherited from row 2 having failed to match) | **(e) POSITIVE/bound** — the **only** positive bucket, and it requires **BOTH** the affirmative bind line **AND** correct identity, evaluated together |
| **4** | stderr contains `listener thread exiting fatally` **and** `WRAP-ENV-MARKER_KEY_FILE <unset>` | **(a) SETUP-DEFECT/missing-key** — **VOID**; fix the plist (declare `GLEIPNIR_MARKER_KEY_FILE`, J18) and re-run |
| **5** | stderr contains `listener thread exiting fatally` **and** `WRAP-KEY-READABLE no` (the env var **is** set) | **(b) SETUP-DEFECT/key-unreadable** — **VOID** *unless* this attempt **is** the J5 step-6.3 break, in which case it is the control's expected result |
| **6** | stderr contains `listener thread exiting fatally` with **neither** row 4's nor row 5's key discriminator | **(f) INCONCLUSIVE** — a fatal listener exit whose *cause* is unattributable. Recorded as (f), **not** as (a) or (b) by guesswork |
| **7** | **Everything else** — in particular `WRAP-UID` = signer uid **and** `WRAP-SYS-EXECUTABLE` = the `.venv` python **and** `WRAP-KEY-READABLE yes` **and** no fatal line **and** `WRAP-BIND-LIVE no`. The uid/interpreter/key facts are all healthy, but **nothing affirms a listener ever existed** | **(f) INCONCLUSIVE** — the catch-all. See the (d) rule immediately below: this combination is **NOT** (d) |

**Why this order, stated explicitly so a re-order cannot silently break it.**
The ordering is **setup-fault → identity → bind**, and **each of the three
adjacencies is load-bearing:**

- **Row 1 (EADDRINUSE/setup fault) precedes row 2 (identity)** because an attempt
  that both ran at the wrong uid **and** failed to bind is a **port-conflict
  harness fault**, not a launchd finding: voiding it is correct, and filing it as
  `(c)` would inject a test-setup defect into the outcome matrix as evidence about
  `UserName`. Voiding is the conservative answer — the remedy is to free the port
  and re-run, at no cost to the verdict.
- **Row 1 also precedes row 3 (bind)** safe-side: a port conflict is a *setup*
  condition (in practice these two are mutually exclusive — a child that held the
  LISTEN socket did not fail to bind it).
- **Row 2 (identity) precedes row 3 (bind)** because a bind at the wrong uid must
  classify as **(c)**, not **(e)**.

Rows 4–6 (fatal-line causes) follow the positive row because they are refinements
of *failure*, and row 7 is the catch-all. **Moving row 3 above row 2 would
reintroduce exactly the wrong-uid-misclassified-as-POSITIVE defect** — and even
then row 3's own conditions would still reject it, which is why the identity
conditions are restated there. **Moving row 2 above row 1 would reintroduce the
setup-fault-misclassified-as-`(c)` defect**, which has no belt-and-braces
backstop: nothing in row 2's own conditions can detect a port conflict, so **row
1's position is the only thing protecting that property** and it must not be
moved.

**Bucket (d) `EXPECTED/stdio-EOF-with-healthy-listener` is reachable ONLY as a
refinement of row 3 (the POSITIVE row), and is otherwise UNREACHABLE.** An
attempt may be recorded as (d) **iff** it matched **row 3** — i.e.
`WRAP-BIND-LIVE yes` (the listener demonstrably bound) **and** the correct signer
uid **and** the `.venv` interpreter — **and** `WRAP-CHILD-EXIT 0` with no fatal
line, i.e. the process **provably had a healthy bound listener, at the right
uid,** and *then* returned from `mcp.run(transport="stdio")` on launchd's
`/dev/null` stdin. In that case (d) and (e) describe the same attempt from two
angles — the bind is the finding, the stdio-EOF return is the explanation of the
early exit — and the report records **(e) POSITIVE/bound, stdio-EOF variant**.
**An attempt that matched row 2 (wrong uid) can NEVER be (d)**, regardless of
what it bound or how cleanly it exited — and **an attempt that matched row 1 (a
setup fault) is VOID and carries no bucket at all**, (d) included.

**What is explicitly FORBIDDEN, and was the defect in the earlier table:**
classifying row 7's combination — healthy uid, healthy interpreter, readable
key, no fatal line, **no bind observation** — as (d). That is *"the listener
must have been fine because nothing said it wasn't"*, which is a **conclusion
drawn from silence**. Concretely: **a module-level import failure, a
`ModuleNotFoundError`, an exception on a path that never reaches the listener's
own `logger`, or a daemon thread torn down before it could log, all satisfy every
one of row 7's stated conditions while NO LISTENER EVER STARTED** — the wrapper's
uid/interpreter/key lines are all captured **before** the child runs, so they say
nothing whatever about what happened inside it. Such an attempt is **(f)
INCONCLUSIVE** (E-8), and an INCONCLUSIVE stage 2 is an honest outcome: it means
the module-level question is **unanswered** and the report says so, feeding Plan B
as an open question rather than a false green. **Equally forbidden, and the newer
defect:** classifying a `WRAP-BIND-LIVE yes` attempt as (e)/(d) **without
checking `WRAP-UID`** — a bind is only positive evidence *for 2C* if the process
that achieved it was running as the signer.

**Candidate plists** — identical bodies, different labels and locations, so the
only variable is the placement/domain (J4). Two variants: **stage 1** runs the
probe, **stage 2** runs the wrapper (J18). `<attempt-id>` is rewritten per
attempt (J20).

```xml
<!-- STAGE 1 (the capability probe).
     arm A: ~/Library/LaunchAgents/dev.gleipnir.signer.spike.agent.plist
     arm B: /Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist
     (Label must match the filename: ...spike.agent / ...spike.daemon) -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key>            <string>dev.gleipnir.signer.spike.agent</string>
  <key>UserName</key>         <string>SIGNER_ACCOUNT_NAME</string>
  <key>GroupName</key>        <string>SIGNER_GROUP_NAME</string>
  <key>ProgramArguments</key> <array>
    <string>REPO/.venv/bin/python</string>
    <string>/private/tmp/gleipnir-signer-spike/signer-probe.py</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>GLEIPNIR_SPIKE_KEY_FILE</key>
      <string>/private/tmp/gleipnir-signer-spike/scratch.key</string>
    <key>GLEIPNIR_SPIKE_DECLARED</key><string>declared-ok</string>
    <!-- GLEIPNIR_SPIKE_SHELLONLY is DELIBERATELY absent (J6 arm E2) -->
  </dict>
  <key>RunAtLoad</key>        <true/>
  <key>KeepAlive</key>        <false/>
  <!-- J20: ATTEMPT-SCOPED. <attempt-id> = NN-<arm>-<stage>-<UTC>, rewritten
       before EVERY bootstrap; NEVER the shared logs/agent.{out,err}. -->
  <key>StandardOutPath</key>  <string>/private/tmp/gleipnir-signer-spike/logs/ATTEMPT_ID/out</string>
  <key>StandardErrorPath</key><string>/private/tmp/gleipnir-signer-spike/logs/ATTEMPT_ID/err</string>
</dict></plist>
```

```xml
<!-- STAGE 2 (the REAL module, via the wrapper). Same Label/placement as the
     stage-1 plist for that arm; ONLY ProgramArguments, the key env var and
     ATTEMPT_ID differ. -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key>            <string>dev.gleipnir.signer.spike.agent</string>
  <key>UserName</key>         <string>SIGNER_ACCOUNT_NAME</string>
  <key>GroupName</key>        <string>SIGNER_GROUP_NAME</string>
  <!-- J18: through the WRAPPER, never the bare module -- the wrapper is what
       survives the child to record its uid/interpreter/exit status. -->
  <key>ProgramArguments</key> <array>
    <string>/bin/sh</string>
    <string>/private/tmp/gleipnir-signer-spike/stage2-wrap.sh</string>
    <string>REPO/.venv/bin/python</string>
  </array>
  <key>WorkingDirectory</key> <string>REPO</string>
  <key>EnvironmentVariables</key><dict>
    <!-- J18: the name the REAL module reads (verify/marker.py:40 KEY_ENV_VAR),
         pointed at the SCRATCH key. Declaring GLEIPNIR_SPIKE_KEY_FILE here
         instead would supply the module NO key and stage 2 would die of
         KeyUnavailable -- a setup defect masquerading as launchd evidence. -->
    <key>GLEIPNIR_MARKER_KEY_FILE</key>
      <string>/private/tmp/gleipnir-signer-spike/scratch.key</string>
    <key>PYTHONPATH</key>       <string>REPO/src</string>
    <key>PYTHONUNBUFFERED</key> <string>1</string>
  </dict>
  <key>RunAtLoad</key>        <true/>
  <key>KeepAlive</key>        <false/>
  <key>StandardOutPath</key>  <string>/private/tmp/gleipnir-signer-spike/logs/ATTEMPT_ID/out</string>
  <key>StandardErrorPath</key><string>/private/tmp/gleipnir-signer-spike/logs/ATTEMPT_ID/err</string>
</dict></plist>
```

`KeepAlive` is **false** deliberately: a restart loop would make "did it bind?"
and "is this the same attempt?" unanswerable, and would fight J7's hygiene.
`PYTHONUNBUFFERED=1` is load-bearing for stage 2: without it a short-lived
child's stdout can be lost, and a lost line is indistinguishable from a line
never written — which would force otherwise-classifiable attempts into J19 (f).

### Spike-report skeleton (step 13)

```
# Plan A spike report — launchd feasibility for the signer uid
## Real-key baseline (step 0) and final re-verification (step 16)
## Preconditions (SC-8, SC-8b) — including any negative
## Outcome matrix (SC-13) — arm A / arm B x stage 1 / stage 2
## Env arms (SC-15) — GLEIPNIR_SPIKE_DECLARED, GLEIPNIR_SPIKE_SHELLONLY only
## F-1 negative control (SC-10) — four ordered transcripts
## Teardown verification (SC-11)
## site.yml regression (SC-12)
## Honesty ledger (verbatim, SC-17)
## VERDICT for Plan B (SC-16): viable | not viable as designed | viable with conditions
```

### Follow-on work — named, NOT planned here

- **Plan B — the Ed25519 migration** (Approach D / predicate P): constructions
  #1 and #2 migrate; #3 and #4 stay symmetric with isolated key material.
  Its launch premise **is this spike's verdict**.
- **Tier-3, operator-authored:** a durable record of **predicate P** (sibling
  brief Q3 — mandatory under Approach D, candidate home
  `.gleipnir/decisions/key-material-model.md`); the `runtime-and-deps.md`
  Ed25519 carve-out (parent Decision 3); a signer decision record carrying the
  C4 honesty qualification.
- **Live Plan-B escalations, unresolved and NOT resolved here:** which uid runs
  the Driver, i.e. who holds construction #2's private minting key (sibling
  brief Q5); and how a construction whose validator later *moves* to the agent
  uid — flipping predicate P false→true — would be detected (sibling brief Q6).

---

## 8. Design Principles (Gate 1 — case (ii): executable-but-non-OOP)

`P ∩ X ≠ ∅` (standalone `*.yml`, `*.sh`), and no touched `X`-member has
class/function/module structure. Therefore:

- **SOLID:** `N/A — no object/function structure.` Ansible task-files and POSIX
  `sh` scripts have no classes, interfaces, or subtype relationships, so Liskov,
  Interface-Segregation and Dependency-Inversion have nothing to range over.
- **Class/module SRP:** `N/A — no object/function structure.` The
  responsibility-per-artifact discipline is expressed as the Design Intent
  below instead.
- **DRY analysis (applies):**
  1. **The one real duplication in scope is account creation, and it is
     eliminated, not tolerated.** `dscl`/`sysadminctl` account creation exists in
     **exactly one file** (`ansible/tasks/create-service-account.yml`) which
     **both** `signer.yml` and `site.yml` consume (C6/OA-1). This is the DRY
     obligation Decision 5 *mandated* as the fix for 1B's con; a signer-local
     copy would have left it unpaid. Falsifiable by SC-6: any surviving inline
     `sysadminctl -addUser` or `dscl . -create /Users` outside the shared file
     is a DRY violation.
  2. **Identity values are single-sourced.** Numeric uid/gid appear in **no**
     playbook — each is read at play start from its own `.env` file and
     templated (the existing P3/BC-6 invariant). Falsifiable by SC-4 (S1 +
     the widened AC-nolit).
  3. **Existing helpers are reused, not reimplemented.** `signer-static.sh`
     mirrors `layer1-static.sh`'s PASS/FAIL/SKIP shape; the pre-task fail-fast
     mirrors `site.yml:66-82`; the `dscl`-only fallback comment mirrors
     `s2-activation-control-proposal.md:50-55`.
  4. **One constant, one home.** The scratch root appears as a single variable
     in `signer.yml` and is referenced by every downstream task; the plist paths,
     the launchd labels and the teardown receipt path each appear once.
     Falsifiable by S2's actual rule: **"every write path is either
     scratch-root-relative, or one of the two enumerated external plist paths, or
     the one enumerated external teardown receipt path
     (`/private/tmp/gleipnir-signer-spike.torndown`, J21) — and no write path
     resolves inside the repository working tree."** (The older phrasing "every
     write path begins with the scratch-root variable" is **false as written**:
     it would condemn the two plist writes teardown is *required* to make and
     the receipt write J21 *requires*. The repo-exclusion is the load-bearing
     half; the three external paths are exact literals, so the exception cannot
     widen.)
  5. **Accepted, deliberate non-duplication:** `signer-teardown.yml` is a
     *separate* playbook rather than destructive tags inside `signer.yml`. This
     duplicates a little identity plumbing, and that is the intended trade — a
     removal path that cannot be reached by a stray tag on a provisioning run.

**Design Intent (specific and falsifiable — the load-bearing claim).**

> **The invariant Plan A actually delivers is an OUTCOME invariant, not a
> naming prohibition: `.gleipnir/keys/marker.key` is byte-, mode-, owner- and
> group-IDENTICAL after the entire spike to what it was before it, PROVEN by the
> step-0 / step-16 comparison (SC-1).**
>
> It is stated that way deliberately, because an absolute *"nothing Plan A
> creates or edits may name, read, `chmod`, `chown` or write the key, nor write
> any path inside the repo tree"* would be **violated by Plan A's own required
> work** — and an intent the plan's mandatory steps contradict is worse than no
> intent, because a reviewer checking it would have to either fail a correct
> implementation or quietly ignore the clause. Three distinct boundaries, each
> with its own honest scope:
>
> **(i) The NEW signer artifacts (`signer.yml`, `signer-teardown.yml`,
> `tasks/create-service-account.yml`) have a genuinely narrow write boundary.**
> Every **write** target is exactly one of, exhaustively enumerated:
>   - anything under the single scratch root `/private/tmp/gleipnir-signer-spike/`
>     (`{{ spike_root }}`-relative), created exclusively by bare `mkdir` (J1);
>   - the **two** enumerated external plist paths
>     `~/Library/LaunchAgents/dev.gleipnir.signer.spike.agent.plist` and
>     `/Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist` — teardown
>     is *required* to remove them (J9);
>   - the **one** enumerated external teardown receipt
>     `/private/tmp/gleipnir-signer-spike.torndown` — required by J21, and
>     required to be **outside** the scratch root, since teardown removes the root
>     entire.
>
>   **Reads are a separate category and are legitimate:** `signer.yml` **must**
>   `slurp`/`stat` `.gleipnir/signer-identity.env` (E-1) — that is under
>   `.gleipnir/`, it is mandatory, and forbidding it would forbid the plan. What
>   is forbidden is a **write** resolving into the repo working tree. These
>   artifacts still **never** name, read, `chmod`, `chown` or write
>   `.gleipnir/keys/marker.key` — that narrower prohibition holds absolutely and
>   is where the strong claim genuinely belongs.
>
> **(ii) The repo-tree writes this plan DOES make, named rather than denied.**
> `ansible/**` (the four playbook artifacts, `tests/signer-static.sh`, the seven
> fixture trees, the `layer1-static.sh` one-line AC-nolit widening, `README.md`),
> `.gitignore` (one exact-path line, J13), `.gleipnir/plans/**` (this plan + the
> spike report), and **`.gleipnir/signer-identity.env`** (operator-authored,
> gitignored, survives teardown per J10). That last one is a real repo-tree write
> the earlier "no path inside the repository working tree" phrasing silently
> contradicted; **SC-2's expected-changed-file-set includes it explicitly**, so a
> correct run passes. The `site.yml` edit is scoped to **act 1 only** — replacing
> four inline account-creation tasks with one `include_tasks`; acts 3, 4, 5, 6 and
> AC-4 remain **byte-identical**.
>
> **(iii) The regression-proof execution DOES touch real permissions — that is
> expected, separately authorized, and exactly why SC-1 exists.** Step 15(d)'s
> full `sudo ansible-playbook -i inventory.ini site.yml` runs act-3's recursive
> repo `chown`/`chmod` **and** act-5's `chmod 600` on the real key. Plan A does
> **not** pretend otherwise: J14(c) names it, and the operator acknowledges it
> (§Judgment calls, item 3). The control is not a prohibition on touching — it is
> the **before/after comparison at step 16**, which is why SC-1's authoritative
> check is placed *after* that apply rather than before it. "Nothing touches the
> key" would be a false claim; "the key's bytes, mode, owner and group are
> unchanged, and we prove it by comparison after the one apply that could have
> changed them" is a true and checkable one.

**How a reviewer falsifies it.** Any of these is a violation: **any**
hash/mode/owner/group difference in `.gleipnir/keys/marker.key` between step 0
and step 16 (SC-1 — the primary falsifier); a **write**-module `path:`/`dest:` or
shell redirection in `signer.yml`/`signer-teardown.yml` resolving inside the repo
tree, or to any external path other than the three enumerated literals (SC-3/S2,
attestation row 2); any reference to `.gleipnir/keys/marker.key` in **any** new
signer artifact, in **any** module, read or write (the absolute clause in (i)); a
`git diff ansible/site.yml` hunk outside act 1 (SC-6, attestation row 4); a
changed file in the repo tree outside SC-2's enumerated expected set; a `mkdir -p`
or `creates:` on the scratch root (SC-5/S3); or a step-16 comparison that was
never performed (SC-1 **INCOMPLETE** ⇒ Plan A not done). Each clause has a
mechanical check, and **no clause is contradicted by a step this plan requires** —
which is the property the earlier phrasing lacked. It is not a quality
aspiration.

**Cross-check bindings.** At **spec-review**, the intent-quality sub-check
confirms the Design Intent above is specific and falsifiable (not "clean" or
"correct"). At **quality**, the honour check confirms the *applied* artifacts
honour it; a divergence is **Important** and **blocks the `git` stage unless the
operator explicitly acknowledges it** — the reviewer never self-clears it
(L-C8), and any accepted divergence's durable home is a Tier-3 decision record,
not this disposable plan.

---

## 9. Judgment calls needing operator acknowledgement

Named here, not buried. None is a new design fork; each has a consequence the
operator should accept before `code` runs.

1. **J8 — the shared task-file's 3-way guard changes `site.yml`'s behaviour.**
   Adopting one task-file (C6/OA-1) means `site.yml` act-1's guard is **upgraded
   from 2-way to 3-way**: an agent account that exists with a *mismatched*
   attribute will now **fail the playbook** where today it is silently skipped.
   That is a strictly safer posture and it is why the extraction is worth doing —
   but it is a **new fail path in the playbook that gates caged mode**, and the
   operator should know that before the first real-box run. Rejected alternative:
   a `svc_strict_attributes` flag defaulting to false for `site.yml` — rejected
   because a per-caller strictness knob is exactly the shared-abstraction strain
   Decision 5 warns about, and because it would preserve the silent-adopt bug on
   the more dangerous of the two callers.
2. **J10 — `.gleipnir/signer-identity.env` deliberately survives teardown.**
   Every OS object and scratch artifact the spike creates is removed and its
   absence verified; this file is kept, so Plan B reuses the same verified-free
   identity. **The full set of legitimate teardown survivors is THREE artifacts,
   named together so none looks like an oversight:** (i)
   `.gleipnir/signer-identity.env` (this row — the chosen uid/gid record); (ii)
   the **teardown completion receipt** `/private/tmp/gleipnir-signer-spike.torndown`,
   which J21 places **outside** the scratch root *precisely so it survives* the
   root's removal and makes "already torn down cleanly" a verified state; and
   (iii) any **retired-receipt** file `…torndown.retired-<UTC>` left by step 11a's
   reconciliation. All three are records, not created OS objects, and nothing is
   held open by their existence — so "verify absence of everything created"
   applies to the account, group, scratch root, plists and labels, and to nothing
   else. If the operator prefers a fully clean teardown of the identity file,
   SC-11's last clause inverts — a one-line change, but the operator's call, not
   the planner's. (The receipt is removed only by the operator, by design, and
   must never be auto-deleted: that is what step 11a's retire-not-delete
   discipline rests on.)
3. **J14(c) — one full real-box `site.yml` apply is required.** The delegation
   is right that the final `site.yml` adoption run is the one place a mistake
   could actually touch the real key, so the regression proof includes a full
   apply, not just the fixture harness and the act-1 tag. That apply **mutates
   real repo ownership/permissions** and **runs the caged AC-4 assertion**. A
   *pre-existing* AC-4 failure may surface here — but per E-11 it may be
   **called** pre-existing **ONLY** by comparison against **step 0b's recorded
   `AC4-BASELINE:`** (§Assemble step 0b), i.e. **only if step 0b recorded
   `AC4-BASELINE: FAIL` with the SAME assert message**. If step 0b recorded
   `AC4-BASELINE: PASS`, a failure here **IS this plan's regression**; if step 0b
   was never captured, the question is **permanently unanswerable** and no
   pre-existing claim may be made. **SC-1 and J14(b) are CORROBORATING
   discriminators only — neither, alone or together, licenses the attribution
   without the step-0b baseline comparison.** This is why step 0b runs **before**
   any provisioning: the operator should be prepared both for that outcome and
   for the fact that SC-1's authoritative check comes **after** this step.

**A fourth item, for awareness rather than decision:** SC-8b may return a
negative — the signer uid may be unable to traverse to or execute
`.venv/bin/python`, since `.venv/` is gitignored and no `site.yml` act grants
read/traverse into it. That is a genuine, informative finding about 2C's
feasibility (it would mean 2C needs an interpreter outside the repo-local venv,
or a permission grant Plan B must design), and it is **recorded, not fixed,
here**. If it lands, it belongs in the report's verdict as a **named condition**,
and any remedy is Plan B's to converge with the operator.

