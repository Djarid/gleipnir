# Plan A spike report — launchd feasibility for the signer uid

**Stage:** Assemble **step 13** `[PLAN]` of
`.gleipnir/plans/signer-uid-separation-plan-a-launchd-spike.md`,
**revised after steps 14–16** to record their real results (see the currency
note below).
**Author:** `gleipnir-plan` (Tier-0 write grant, `.gleipnir/plans/**`).
**Arbiters discharged here:** **SC-13** (outcome matrix), **SC-15** (env
conclusion scoping), **SC-16** (Plan-B verdict), **SC-17** (honesty ledger
verbatim). SC-8b and SC-10 results are recorded here as captured at steps 11b
and 12. **SC-11/SC-20** (teardown, step 14), **SC-12** (`site.yml` regression,
step 15) and **SC-1/SC-2** (final key re-verification, step 16) are recorded
here as captured at those steps.

> **Currency note (revision after step 16).** This document was first written at
> step 13, when steps 14–16 had not yet run. Those steps have since been executed
> on this box in this session; the two sections that previously read
> **"NOT YET RUN"** now carry their observed results, and a step-16 section has
> been added. The step-13 evidence above and below is unchanged. One causal
> statement about arm B stage 2 has also been **weakened** to the hypothesis it
> actually is — see that section.

**What this document is.** The recorded evidence from the real-box launchd
feasibility spike executed on this host this session, and the single Plan-B
verdict that evidence licenses. Every value below was observed on this box; the
primary capture was
`/private/tmp/gleipnir-signer-spike/logs/OUTCOME-MATRIX.txt` plus the step-0/0b
baseline captures. **That scratch capture path no longer exists** — the whole
scratch tree was removed at teardown (step 14), by design — so **this document
is now the surviving record** of those observations. Nothing here is inferred
from documentation — that inference is exactly the Dunning-Kruger flag
parent-brief Decision 6 exists to close.

**Reading guide — three distinct result classes, none of which is a Plan-A
failure.** J4 established up front that the spike records an *outcome matrix*,
not a pass/fail, and that a negative is informative:

- **POSITIVE** — arm B stage 1 (the signer uid genuinely ran, read a key, and
  bound the port).
- **Informative NEGATIVE** — arm A (the gui LaunchAgent domain refused the
  foreign signer uid, `EX_CONFIG`). A valid, informative J4/E-6 finding: it
  *answers* the placement question rather than failing it.
- **Pre-declared INCONCLUSIVE** — arm B stage 2, J19 bucket **(f)**. The
  pre-declared E-8 stdio case. Explicitly **not** a Plan-A failure, and a
  load-bearing Plan-B input. Note the classification is **INCONCLUSIVE by
  design**: it records that no bind was observed and that **no cause was
  established** — the stdio explanation is the leading hypothesis, not a finding.

---

## Real-key baseline (step 0) and AC-4 baseline (step 0b)

### Real production key — `.gleipnir/keys/marker.key`

| Attribute | Baseline value (step 0, pre-spike) |
|---|---|
| sha256 | `eab08f125340ff5c580b6917223a484e202e3e2bf10f1d31267108afb38e272f` |
| mode | `600` |
| owner | `jasonh` (uid **501**) |
| group | `staff` (gid **20**) |
| size | 33 bytes |

**The real key's OUTCOME is unchanged (the invariant is unchanged-outcome, not
never-touched).** No signer-spike step read, copied, moved, re-owned, re-moded,
or derived from `marker.key`; the spike used `<root>/scratch.key` throughout — a
throwaway 32-byte `/dev/urandom` file owned `signer:signer` mode 0600, generated
for the spike, validating nothing, never copied from or derived from
`marker.key`. The **one** step that legitimately touches the key is the
plan-authorized full `site.yml` regression apply (step 15(d)), whose act-5
re-asserts the key's `chmod 600` — a permission-setting operation, not a content
change. The binding guarantee (SC-1) is therefore that after that apply the key
is **byte-, mode-, owner- and group-identical to the step-0 baseline** (verified
below), NOT that no process ever opened it.

### AC-4 baseline (step 0b)

```
AC4-BASELINE: PASS
  "AC-4 passed: S-2 caged boundary CLOSED (preflight rc=0)"
```

Captured against the **unmodified tree, before any provisioning**, per J24(d).

> **Consequence, recorded now so it cannot be argued later (E-11 / J14(c)):**
> because step 0b recorded **PASS**, any AC-4 failure at step 15(d) **IS this
> plan's regression**. The "pre-existing failure" escape is foreclosed by this
> baseline — it would be available *only* had step 0b recorded
> `AC4-BASELINE: FAIL` with the *same* assert message. SC-1 and J14(b) remain
> corroborating discriminators only and cannot substitute for this comparison.

### Signer identity

uid/gid **511 / 511** — verified free before use, and distinct from both the
agent uid **510** (`.gleipnir/agent-identity.env`) and the operator uid **501**.
Recorded in `.gleipnir/signer-identity.env` (gitignored per J13; survives
teardown per J10).

### Host-environment adaptations (recorded for reproducibility)

Two deviations from the plan's literal command text, both mechanical, neither
affecting any result:

1. This host provides **GNU coreutils `stat`**, not BSD `stat`. The plan's
   `stat -f '%Sp %Su %Sg %z'` was adapted to the GNU equivalent; the same four
   attributes were captured.
2. `sudo` on this host required `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8` passed
   through explicitly; the plan's bare-`sudo` invocations were adapted
   accordingly.

---

## Preconditions (SC-8, SC-8b) — including any negative

**SC-8b — can the signer uid execute the repo-local `.venv` interpreter?**
This was never tested by anything before this spike (`.venv/` is gitignored, so
`site.yml`'s `chmod -R a+rX src` has never covered it).

| Probe | Command | Result | Verdict |
|---|---|---|---|
| SC-8b | `sudo -u '#511' <repo>/.venv/bin/python -c 'print(1)'` | ran; observed uid **511**; exit **0** | **PASS** |

The E-5 negative did **not** materialise: a second uid can traverse to and
execute `<repo>/.venv/bin/python`. This is a genuine precondition for 2C and it
holds on this host.

---

## Outcome matrix (SC-13) — arm A / arm B × stage 1 / stage 2

One row per arm per stage, per SC-13. Arm A = `~/Library/LaunchAgents/`
(**gui** domain, `gui/501`); arm B = `/Library/LaunchDaemons/` (**system**
domain). No winner was pre-asserted (J4).

| Arm | Placement / domain | Stage | Bootstrap result | Observed uid/gid | `sys.executable` | Key read | Port bind `127.0.0.1:8765` | Env visibility | Class |
|---|---|---|---|---|---|---|---|---|---|
| **A** | `~/Library/LaunchAgents/…agent.plist` — **gui/501** | 1 (probe) | `bootstrap` **rc=0** (job loaded), but launchd reports **`last exit code = 78` (`EX_CONFIG`)**; state = **not running**; **no `out` and no `err` written** | **not observed** — the probe never executed | **not observed** | **not observed** | **not observed** | **not observed** | **informative NEGATIVE (c)** |
| **A** | same | 2 (real module) | **NOT RUN — correctly.** Stage 2 runs only on an arm stage 1 proved runs at the signer uid (J2). Arm A did not, so stage 2 was withheld | n/a | n/a | n/a | n/a | n/a | **n/a by design** |
| **B** | `/Library/LaunchDaemons/…daemon.plist` — **system** | 1 (probe) | loaded and **ran**; `username=gleipnirsigner`; **last exit = 0** | **`PROBE-UID 511` / `GID 511`** | `/Users/jasonh/git/gleipnir/.venv/bin/python` | **`PROBE-KEYREAD-OK`, 32 bytes** | **`PROBE-BIND-OK 127.0.0.1:8765`** | `PROBE-ENV-DECLARED 'declared-ok'` | **POSITIVE** |
| **B** | same | 2 (real `gleipnir.approval.mcp_server` via the J18 wrapper, `GLEIPNIR_MARKER_KEY_FILE=<root>/scratch.key`) | ran; child exited | **`WRAP-UID 511`** | `<repo>/.venv/bin/python` | **`WRAP-KEY-READABLE yes`** — a **pre-child readability probe**, *not* proof the module itself read the key | **`WRAP-BIND-LIVE no`** (= **no bind observed in the poll window**, not proof none occurred); `WRAP-CHILD-ALIVE-AT-POLL-END no` | declared var supplied via plist | **J19 (f) INCONCLUSIVE — pre-declared E-8** |

### Arm A — the informative negative, read out

launchd's **gui** domain is bound to the **logged-in user (501)**. A `UserName`
naming a *different, non-login* uid (511) is **not honoured** there: the job
loads, then dies with `78 EX_CONFIG` before the program runs — which is why no
`out`/`err` was produced at all. This is a **valid, informative NEGATIVE**
(J4 / E-6), not a defect and not a Plan-A failure: it *answers* the placement
question that Decision 6 opened. Consequence: **arm A is unsuitable and stage 2
was correctly not run on it.**

### Arm B stage 1 — the positive baseline

Every one of 2C's premises held simultaneously on this arm: launchd honoured
`UserName` for a non-login account in the **system** domain; the process ran as
**uid 511 / gid 511**; it executed the **repo-local** `.venv/bin/python`; it
**read** a mode-0600 signer-owned key (32 bytes); and it **bound
`127.0.0.1:8765`**. This row is what establishes 2C's capability on this host,
and it is also what **satisfies the J5 negative-control precondition** (a
working baseline exists to break).

Observed launchd requirement, recorded because Plan B must honour it: the
**system-domain plist must be `root:wheel` mode `0644`** or launchd refuses to
load it.

### Arm B stage 2 — the pre-declared inconclusive, read out via the J19 ordered walk

The classifier is an **ordered, first-match-wins** procedure (J25). The walk, as
executed:

| Row | Test | Observed | Outcome |
|---|---|---|---|
| 1 | EADDRINUSE / setup fault? | **no** — port was proven free at attempt start | not voided; continue |
| 2 | identity gate — wrong uid/exec? | **no** — `WRAP-UID 511`, correct interpreter | not (c); continue |
| 3 | `WRAP-BIND-LIVE yes` **AND** correct uid? | **NO** — `WRAP-BIND-LIVE no` | **not (e)**; continue |
| 4 | fatal line + missing-key discriminator? | **no fatal line** | not (a); continue |
| 5 | fatal line + unreadable-key discriminator? | **no fatal line** (`WRAP-KEY-READABLE yes`) | not (b); continue |
| 6 | fatal line, cause unattributable? | **no fatal line at all**; `err` empty | not (f)-via-row-6; continue |
| 7 | catch-all — healthy-looking, no bind | **matches** | **(f) INCONCLUSIVE** |

**What was actually observed, and why it is (f) rather than a failure.** The
module ran **as the signer** (`WRAP-UID 511`), the key was **readable at the
signer uid** (`WRAP-KEY-READABLE yes`), the child **exited 0**
(`WRAP-CHILD-EXIT 0`), `err` was **empty** (no fatal line), and **no bind was
observed** (`WRAP-BIND-LIVE no`). Those five are the observations; everything
past them is interpretation.

> **Causal claim, explicitly downgraded to a hypothesis (revision note).** An
> earlier draft of this section asserted that the module "read the key and
> exited because of EOF before binding." That **overstates the evidence** and is
> corrected here:
>
> - `WRAP-KEY-READABLE yes` is a **pre-child readability probe** — it proves the
>   key was readable *at the signer uid before the child ran*. It is **not**
>   evidence that the module itself opened or read the key.
> - `WRAP-BIND-LIVE no` / `WRAP-CHILD-ALIVE-AT-POLL-END no` record **no observed
>   bind within the poll window**. That is **not** proof the process never bound.
> - `WRAP-CHILD-EXIT 0` plus an empty `err` rules out an *emitted fatal*; it does
>   not identify a cause.
>
> **Leading hypothesis (plausible and source-supported, NOT established).** Under
> launchd `stdin` is `/dev/null`, and the `mcp_server.py` source path runs
> `mcp.run(transport="stdio")`, which would read **EOF on a `/dev/null` stdin and
> return** — returning before any listener bound 8765. This is **consistent with**
> every observation above (exit 0, no fatal line, no observed bind) and is the
> **most probable** explanation on the evidence plus the source. It was **not
> instrumented and not proven** in this spike: no observation distinguishes it
> from other no-observed-bind paths (e.g. a bind that occurred and was torn down
> outside the poll window, or a return before the key was ever read). Treat it as
> the **leading hypothesis**, not as fact.

No fatal line was emitted, so nothing is attributable to a key or identity
fault — which is precisely why the row lands in the catch-all.

Per J19/J25 this is classified **(f) INCONCLUSIVE and not (d)**, because
**(d)/(e) require an AFFIRMATIVE bind observation** (`WRAP-BIND-LIVE yes`) and
there is none: signer uid + correct interpreter + readable key + no fatal line
are captured **before** the child runs and are therefore **not sufficient**.
Recording this as "healthy" would be precisely the false-success J25 exists to
prevent. Equally, **exit status 0 discriminates nothing** — `_run_listener`
catches a fatal error, records it, and returns without raising, on a code path
that never interacts with `mcp.run`.

**This is the pre-declared E-8 case (J2), NOT a Plan-A failure — and it IS a
load-bearing Plan-B input.** The spike proved the **capability** (stage 1's
probe bound 8765 as uid 511); what stage 2 established is that the **current
module, run unmodified under launchd, did not produce an observed bind** — with
its **stdio lifecycle the leading (unproven) explanation**. Either way the
Plan-B consequence is the same and does not rest on the hypothesis: the standing
service must not depend on stdio staying open (condition 3 below). Nothing here
implicates launchd or uid separation.

---

## Env arms (SC-15) — `GLEIPNIR_SPIKE_DECLARED`, `GLEIPNIR_SPIKE_SHELLONLY` only

Both J6 arms ran. Testing only the declared form would have licensed no
inheritance claim at all; E2 is what makes the conclusion below sayable.

| Arm | Variable (by name) | How set | Visible to the launchd-started process? |
|---|---|---|---|
| **E1** | **`GLEIPNIR_SPIKE_DECLARED`** | declared in the plist's `EnvironmentVariables` | **VISIBLE** — value `'declared-ok'` |
| **E2** | **`GLEIPNIR_SPIKE_SHELLONLY`** | set **only** in the bootstrapping shell; **not** declared in the plist | **NOT visible** — `None` |

**Conclusion, scoped to exactly these two named variables:** launchd did **not**
propagate `GLEIPNIR_SPIKE_SHELLONLY` from the bootstrapping shell's environment
into the started process, while it **did** deliver the plist-declared
`GLEIPNIR_SPIKE_DECLARED`. On the evidence of these two variables, **launchd
does not inherit the bootstrapping shell's environment; only plist-declared
`EnvironmentVariables` reach the process.**

> **Scope limits, binding (J6 / SC-15).** This conclusion covers **only** the two
> variables named above. **No claim whatsoever is made about opencode's own
> environment**, about any other variable, or about any other launchd
> configuration. The Args-layer consequence for Plan B is stated as a *named
> condition* below, not as a general law.

---

## F-1 negative control (SC-10) — FORM A, four ordered transcripts

**Branch decision, recorded (step 6.0):** arm B stage 1 produced **both**
`PROBE-UID 511` **and** `PROBE-KEYREAD-OK` (see the arm-B stage-1 matrix row) ⇒
a working baseline **exists** ⇒ **FORM A applies**, mandatory and unweakened.
FORM B (`N/A-BY-DESIGN`) is **not** available here, and claiming it would be an
evasion.

All four steps ran **in the prescribed order**, each from **its own fresh
per-attempt log directory** (J20 / SC-19) — so no check below is satisfiable by
a stale line from another attempt.

**Attempt-id attribution (honest scope).** Every attempt in this spike wrote to
a fresh per-attempt directory named on the scheme
**`NN-<arm>-<stage>-<UTC>`** under
`/private/tmp/gleipnir-signer-spike/logs/`. The attempt-id **forms** recorded
this session were:

| Attempt-id form | What ran |
|---|---|
| `04-B-1-<UTC>` | arm B stage 1 (positive baseline) |
| `05-B-E2-<UTC>` | env arm E2 (shell-only variable) |
| `06-B-2-<UTC>` | arm B stage 2 (the (f) INCONCLUSIVE attempt) |
| `07-B-negctl-baseline-<UTC>` | negative control step 1 (baseline) |
| `08-B-negctl-broken-<UTC>` | negative control step 3 (the specific denial) |
| `09-B-negctl-restored-<UTC>` | negative control step 4 (restored baseline) |

**What is and is not recoverable.** The `NN-<arm>-<stage>` prefixes above are
the ids as recorded this session and are exact. The **`<UTC>` suffixes are not
reproduced here**: the scratch tree — including
`/private/tmp/gleipnir-signer-spike/logs/` and every per-attempt directory in
it — was **removed at teardown (step 14)**, so the live capture path no longer
exists and the exact timestamps are **not recoverable from the box**. They are
deliberately **not** reconstructed or guessed. What the structure still
establishes is the property SC-19 needs: the three negative-control transcripts
came from **three distinct per-attempt directories** (`07-…`, `08-…`, `09-…`),
so no line below is satisfiable by a stale line from another attempt.

| Step | Act | Observed | Attribution (per-attempt dir) |
|---|---|---|---|
| 1 | **Baseline** — scratch key at 0600, signer-owned | **`PROBE-KEYREAD-OK`, 32 bytes** | `07-B-negctl-baseline-<UTC>` |
| 2 | **Break** — `chmod 000 <root>/scratch.key` (**owner unchanged**, so only the mode varies) | mode applied | — (host act, no attempt dir) |
| 3 | **Capture the specific denial** | **`PROBE-KEYREAD-FAIL /private/tmp/gleipnir-signer-spike/scratch.key` — `PermissionError(13, 'Permission denied')`** | `08-B-negctl-broken-<UTC>` |
| 4 | **Restore** — `chmod 0600` and re-prove the baseline | **`PROBE-KEYREAD-OK`, 32 bytes** | `09-B-negctl-restored-<UTC>` |

**VERDICT: SC-10 FORM A — PASS.** The control satisfies its discriminator
exactly: the failure is **the specific `Errno 13`** on **the exact key path**,
and it is **bracketed by a working baseline before and after**. That bracketing
is what proves the *break* caused the denial rather than the path never having
worked — the one thing an unbracketed "make it fail" step can never establish.
The F-1 bug class is therefore reproduced and operator-visible.

---

## Teardown verification (SC-11, SC-20) — step 14, **COMPLETED**

**All three receipt states were proven on the real box.** SC-11 and SC-20 are
discharged, not deferred.

| Receipt state | Precondition on the box | Teardown behaviour observed | Removed anything? |
|---|---|---|---|
| **(1) manifest present** | provisioning manifest on disk | **gated removal performed** — signer account, signer group, scratch root, and **both** plists (arm A + arm B) removed; **completion receipt written** | **yes** — exactly the manifest-recorded set |
| **(2) manifest absent, receipt present** | prior completion receipt on disk, manifest gone | **VERIFIED clean no-op**, **quoting the receipt** as its evidence | **no** — removed nothing |
| **(3) both absent** | no manifest, no receipt | **REFUSED LOUDLY** | **no** — removed nothing |

State (3) is the load-bearing one: with no manifest and no receipt the script has
**no authority to say what it may remove**, and it refused rather than guessing.
That is the SC-20 proof, and it removed nothing.

**End state on the box:** signer account (**uid 511**) removed, signer group
removed, scratch tree (`/private/tmp/gleipnir-signer-spike/`, including all
per-attempt log directories) removed. **`.gleipnir/signer-identity.env`
SURVIVED**, as required by **J10**.

**VERDICT: SC-11 PASS, SC-20 PASS.**

> **Defect found and fixed during step 14 (recorded, not hidden).** Teardown
> initially **hung** on `launchctl`. Cause: the **arm-A bootout** was issued
> against a **gui domain resolved under `sudo`**, which yields **root's** gui uid
> rather than the operator's — so the bootout targeted the wrong domain and hung.
> Fixed by (i) resolving the **operator uid** explicitly for the gui-domain
> target (the **E-5** resolution path), (ii) adding **load-check guards** so a
> bootout is only attempted against a job actually loaded, and (iii) using the
> **manifest-recorded `PLIST_*_PATH`** values rather than re-deriving the paths.
> After the fix the three-state matrix above was proven. This is a teardown-script
> defect, corrected in-session; it changes no spike result.

## `site.yml` regression (SC-12) — step 15, **COMPLETED — NO regression**

Executed per J14 / J24. Four sub-results:

| Sub-step | Act | Observed |
|---|---|---|
| **(a)** | `sh ansible/tests/run.sh` | **exit 0**; all **3 layers green** |
| **(b)** | `site.yml --tags act1` with `-i inventory.ini`, run **TWICE** | **`changed=0` both runs** — idempotent |
| **(b2)** | execution transcript (`-v`) inspected | **the extracted guard logic GENUINELY RAN** — see below |
| **(d)** | one full `sudo ansible-playbook site.yml` apply | **`failed=0`**; AC-4 = **"S-2 caged boundary CLOSED (preflight rc=0)"** |

**(b2) — why `changed=0` is not vacuous.** `changed=0` alone is satisfiable by
tasks that never ran at all, so the `-v` transcript was read to discriminate. It
showed the shared task-file's **query task** and the **attribute-compare task**
producing real **`ok:`** results — the compare emitting
**`attrs_mismatch: false`** — **not `skipping:`**. The **creation tasks**
correctly showed **`skipping:`**. That is the guard **working**: the guard logic
executed and evaluated, and it then suppressed the creation path. Had the query
and compare tasks themselves shown `skipping:`, `changed=0` would have proven
nothing.

**(d) — the E-11 comparison, performed.** Step 0b recorded
**`AC4-BASELINE: PASS`**. Step 15(d) records AC-4 **PASS** with the same assert
message (*"S-2 caged boundary CLOSED (preflight rc=0)"*). PASS → PASS is
therefore **NO regression** (E-11 / J24(d)). The "pre-existing failure" escape
was already foreclosed by the baseline and was not needed.

**VERDICT: SC-12 PASS.**

## Final key re-verification (SC-1, SC-2) — step 16, **COMPLETED**

Run **after** the full step-15(d) apply, compared against the step-0 baseline
block above.

| Attribute | Step-0 baseline | Step-16 final (post-apply) | Match |
|---|---|---|---|
| sha256 | `eab08f125340ff5c580b6917223a484e202e3e2bf10f1d31267108afb38e272f` | `eab08f125340ff5c580b6917223a484e202e3e2bf10f1d31267108afb38e272f` | **identical** |
| mode | `600` | `600` | **identical** |
| owner | `jasonh` (uid **501**) | `jasonh` (uid **501**) | **identical** |
| group | `staff` (gid **20**) | `staff` (gid **20**) | **identical** |
| size | 33 bytes | 33 bytes | **identical** |

`.gleipnir/keys/marker.key` is **BYTE-, MODE-, OWNER- and GROUP-IDENTICAL** to
its pre-spike baseline. No signer-spike step read, copied, moved, re-owned,
re-moded, or derived from it; the only step that touches it is the
plan-authorized full `site.yml` apply (step 15(d), act-5's `chmod 600`
permission re-assertion), after which this comparison confirms the
unchanged-outcome invariant holds.

**VERDICT: SC-1 PASS.** **SC-2 PASS** as well — **no spike artifacts remain in
the repo tree** (the sole retained file, `.gleipnir/signer-identity.env`, is
gitignored per J13 and retained by design per J10).

---

## Honesty ledger (verbatim, SC-17)

The three §Honesty ledger blockquotes from the plan, reproduced **verbatim**:

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

**This report makes no isolation and no key-confidentiality claim.** Plan A
provisioned an OS account and recorded launch-mechanism evidence, and that is
all it did. It changed no key's content; no validator's behaviour; and no
posture. The real key's OUTCOME is unchanged after the authorized `site.yml`
apply — byte-, mode-, owner- and group-identical to the step-0 baseline (SC-1
above; act-5's `chmod 600` re-assertion is a permission set, not a content
change). The scratch key is a throwaway `/dev/urandom` file that validates
nothing.

---

## VERDICT for Plan B (SC-16)

> ## **2C viable with named conditions**

Exactly one of the three SC-16 options, stated once. The conditions, enumerated
— each traceable to a specific observation above:

1. **Placement MUST be arm B — the system LaunchDaemon (`/Library/LaunchDaemons/`).
   NOT arm A.** The gui LaunchAgent domain **refused** the foreign signer uid
   with `78 EX_CONFIG` (the gui domain is bound to the logged-in user 501, and a
   `UserName` naming a different non-login uid is not honoured there). Arm B ran
   correctly as uid/gid 511/511. *Evidence: arm-A and arm-B stage-1 matrix rows.*

2. **The plist MUST declare `GLEIPNIR_MARKER_KEY_FILE` in
   `EnvironmentVariables`.** launchd does **not** inherit the bootstrapping
   shell's environment — on the evidence of the two named J6 variables, only
   plist-declared variables reach the process. Relying on shell export would
   supply the module **no key path at all**, re-triggering F-1's silent
   keyless-start class. *Evidence: env arms E1/E2, scoped as above.*

3. **The standing signer service MUST NOT depend on stdio staying open.** Under
   launchd `stdin` is `/dev/null`, and the current `mcp_server`'s
   `mcp.run(transport="stdio")` would **read EOF on that stdin and return** —
   the **leading hypothesis** for the observed stage-2 result (exit 0, no fatal
   line, **no observed bind**), consistent with the source path but **not
   instrumented or proven** (see the stage-2 downgrade note above). The
   condition holds **regardless of which no-observed-bind mechanism was
   actually at work**: a `/dev/null` stdin is a fact of the launchd
   environment, so depending on stdio staying open is unsafe either way. Plan B
   must therefore run the module in a **non-stdio / keepalive** mode — e.g. a
   run mode that keeps the process alive independently of stdio, or `KeepAlive`
   in the plist **plus** a non-stdio server entrypoint.
   **The spike proved the CAPABILITY** — the probe bound `127.0.0.1:8765` as uid
   511 on arm B — **so what needs adapting is the current module's stdio
   lifecycle, not launchd or uid separation.** *Evidence: arm-B stage-1 POSITIVE
   row vs. arm-B stage-2 (f) row.*

4. **The system-domain plist must be `root:wheel` mode `0644`** — a launchd
   load requirement, observed on this host during arm B.

### What the verdict does and does not license

- **Licensed:** Plan B may proceed on the 2C launch premise, subject to
  conditions 1–4. The premise is no longer an assertion from documentation —
  Decision 6's Medium-not-High confidence is discharged by recorded on-box
  evidence.
- **NOT licensed:** any claim that the signer's key is now protected, that
  isolation exists, that O-3(b) is closed, or that the `caged + armed` gap is
  fixed. All three honesty-ledger qualifications above remain in force
  verbatim, and the `caged + armed` gap remains a **named** gap for the whole
  interim until the construction-#1/#2 Ed25519 migration ships.
- **Unchanged and still open:** the plist and `.venv`-interpreter writability
  residual (neither is covered by the current `ENFORCEMENT_PATHS` set — SC-8b
  made the `.venv` half concrete by proving a second uid *can* execute it), and
  the session-scoped→standing listener conversion, whose feasibility this spike
  establishes but which Plan A does not perform.

---

## Known limitations of the spike playbooks (spike-grade, for Plan B to supersede)

**Status: operator-converged.** These `ansible/` artifacts (`signer.yml`,
`signer-teardown.yml`, `tasks/create-service-account.yml`, plus the
`signer-static.sh` arbiter + fixtures) are **feasibility-spike scaffolding**, not
a production account-management library. Their purpose was to make the launchd
2C launch mechanism executable end-to-end on a real box so the spike verdict
could be recorded from evidence — which it was (verdict above, macOS + Linux).
They passed three adversarial `quality` review rounds that fixed the load-bearing
correctness (the substring-guard→exact-guard, fabricated→lifecycle provenance,
None/LIST handling, unbounded-deletion→path-bounded teardown, arbiter
self-hardening, evidence de-overclaiming) and are **runtime-proven** for the
core paths (matching-account skip, absent-account provision, fresh→rerun→EEXIST→
teardown full cycle, SC-1 key byte/mode/owner-identical). A third review then
surfaced progressively more marginal edge-cases; the operator converged to
**commit these spike-grade and have Plan B author production account/teardown
logic from scratch**, informed by everything here, rather than asymptotically
harden throwaway scaffolding. The open items, recorded so Plan B closes them:

1. **Missing-group-with-present-user is not repaired.** The three group-creation
   tasks in `tasks/create-service-account.yml` are gated `when: not user_present
   and not attrs_mismatch`, so if the user exists-and-matches but its named group
   has been deleted, no task recreates or rejects the group. Plan B: handle group
   absence independently (create-or-fail on the inconsistent user-present/
   group-absent state).
2. **`account_provisioned`/`group_provisioned` are tautological.** `(user_present
   or user_absent)` is true for every outcome that survives the operational-error
   fails, so the "recorded-true but object now absent" contradiction check in
   `signer.yml` cannot actually fire. Plan B: base lifecycle membership on real
   post-provisioning presence evidence and make the contradiction check live.
3. **Arbiter S4 first-fail fallback.** `signer-static.sh` falls back to the first
   `fail:` task when no `attrs_mismatch`-referencing fail is found, so *removing*
   the mismatch-fail entirely can still pass S4. Plan B (or an arbiter follow-up):
   fail S4 when no mismatch-fail exists (drop the fallback).
4. **Arbiter S2 provenance is window-token-based, not expression-bound.** The
   `{{ plist_a_path }}`/`{{ plist_b_path }}` provenance check searches nearby
   lines for `regex_search`/`manifest_raw`/`set_fact` tokens independently rather
   than binding them to the one assignment expression, so a contrived unrelated
   assignment could satisfy the tokens. (The actual teardown assignment IS
   correctly manifest-derived; the gap is only in the checker's strength.)
5. **Teardown absence-verification treats any nonzero query as absence.** The
   account/group absence probes before the receipt reject only `rc == 0`; a
   Directory Services *operational* error would be accepted as "absent" (the same
   absent-vs-error distinction the provisioning guard now handles explicitly).
   Plan B: require the clean not-found result; fail on other query errors.
6. **Post-bootout label-absence probe deferred** (accepted): omitted for
   proportionality and to avoid reintroducing the `launchctl`-hang class;
   bootouts are load-gated and plist files are verified absent.

None of these affects the spike **verdict** (2C viable, conditions 1–4), which
rests on the recorded launch-mechanism evidence, not on the playbooks being
production-grade.
