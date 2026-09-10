# Design Brief: genuine OS-level signer-uid separation for the `gleipnir-approval` MCP

**Status: BRAINSTORM — Clarify/Explore/Propose COMPLETE. PARTIALLY CONVERGED —
3 of 8 decisions converged (1 split-out, 2 operator-decided); 5 remain open.**
**NOT READY FOR `gleipnir-plan`.** See `## Converged (partial)` below for what
is settled and what is not. Decisions 4–8 (launch mechanism, provisioning
reuse-vs-parallel, launchd spike authorization, caged-mode-only honesty
statement, armed-pipeline-collision scope) are **still open and unresolved**,
and planning cannot start without at least the launch mechanism (Decision 4):
choosing Ed25519 as the end-state settles the *key* question, not the *launch*
question. Every recommendation on a still-open fork remains marked
**[ADVISORY]** and is input to the operator's precept-10 convergence gate, not
a decision. Per the `brainstorm` skill's Phase-4 `[GLEIPNIR]` binding, this
subagent's `question` tool cannot reach the operator; the orchestrator surfaces
these forks and hands back the converged choices — which is exactly how
Decisions 1–3 below arrived.

**Provenance / required reading actually read (verified against disk, not
assumed):** `.gleipnir/decisions/tier3-signed-approval.md` (270 lines, in full,
incl. the "Narrowing" section verbatim), `.gleipnir/decisions/go-caged-runbook.md`
(193 lines), `.gleipnir/decisions/s2-g1-closure.md` (124),
`.gleipnir/decisions/operating-posture.md` (71),
`.gleipnir/decisions/runtime-and-deps.md` (110),
`.gleipnir/plans/s2-activation-control-proposal.md` (164 — the authoritative
six OS acts), `ansible/site.yml` (428) + `ansible/group_vars/all.yml` (110),
`bin/gleipnir-launch` (44), `opencode.jsonc` (108),
`src/gleipnir/approval/{mcp_server,server,gate,__main__}.py`,
`src/gleipnir/verify/marker.py:86-106` (`load_key`),
`.gleipnir/plugins/{sequence-gate,advance-hook,tier3-gate}.ts` (key-read and
spawn sites), `src/gleipnir/preflight/boundary.py` (`RO_AND_UNREADABLE`).

---

## Converged (partial)

**3 of 8 decisions converged: 1 split-out, 2 operator-decided. 5 remain open.**
The convergence below came back from the orchestrator, which put the forks to
the operator in plain conversation this session. Nothing here is
self-attested by this subagent; the still-open items are listed as open, not
quietly filled in from my own advisory recommendations.

### Decision 1 (was item 1, F-1) — SPLIT OUT, tracked elsewhere. NOT resolved here.

F-1 (caged mode silently breaks the approval listener today, §Explore F-1) is
**confirmed as a present, urgent defect and SPLIT OUT of this brief** as its own
separately-planned bug fix. It is being planned right now in a parallel
delegation and is **no longer this brief's concern**.

- **Nature:** this is an **operator-directed split of work**, *not* a design
  choice among the brief's approaches. No approach in Fork 1/2/3 was selected by
  virtue of this split. In particular, splitting F-1 out is **not** a decision to
  adopt 3A: F-1's fix is scoped as a caged-mode bug fix and, per §Fork 3's
  pre-mortem mitigations #1/#2/#4, must be labelled in the honesty ledger as
  delivering **no key confidentiality** and as **not** closing O-3(b).
- **Consequence for this brief:** §Explore F-1 stays as recorded (it is the
  evidence that motivated the split), but F-1's *remedy* is out of scope here.
  Do not plan the F-1 fix from this brief.
- **Attribution:** operator, direct conversation with orchestrator, this session
  (operator-directed split).

### Decision 2 (was item 2, Fork 3 end-state) — CONVERGED: **3C, Ed25519 asymmetric signing.**

**3C — Ed25519 asymmetric signing** is the chosen **end-state** for the
key-sharing problem established by §Explore F-2 (the approval token is a
symmetric HMAC shared by eight readers, so chowning the key to a signer uid
breaks every validator). Chosen over **3A** (narrow / signer-uid-only, key left
readable to the agent uid) and **3B** (exclusive signer key + verify-over-IPC).

- **Rationale as converged:** 3C dissolves F-2 rather than working around it —
  the signer holds the private key, validators hold only a public key that is
  safe to leave world-readable. It is the only option whose cost is **paid
  once**: 3A's cost is permanent false assurance, 3B's is permanent
  availability coupling (§Fork 3 Second-Order Thinking).
- **Divergence from this brief's advisory: NONE.** This matches my own
  `[ADVISORY]` recommendation at §Fork 3 ("Then, as its own converged decision:
  3C (Ed25519) as the target end-state"). Recorded as agreement, not as the
  operator overriding an analysis.
- **3B is no longer the fallback.** §Fork 3's advisory made 3B the
  stdlib-preserving fallback *conditional on the crypto dependency being
  refused*. It was not refused (Decision 3), so that condition did not fire and
  3B is off the table as the end-state.
- **Still-live consequences carried forward, NOT settled by this decision:** the
  §Fork 4 residual for 3C (a third-party dependency inside the S-2 trusted
  surface; private-key handling and rotation as a new operational concern), the
  Python/TS cross-language canonical-signing-input contract currently pinned by
  golden fixtures (`sequence-gate.ts:32-40`), and the key-format migration for a
  live subsystem. These are plan-stage work, not open convergence forks.
- **Attribution:** operator, direct conversation with orchestrator, this session.

### Decision 3 (was item 3, crypto dependency) — IMPLICITLY SETTLED as a consequence of Decision 2.

The operator has **accepted a `cryptography` (or equivalent asymmetric-signing)
dependency entering the enforcement core** for this specific, narrow purpose:
**Ed25519 sign/verify** for the Tier-3 approval token. This is recorded as its
own line, not folded into Decision 2, because it is a real and consequential
change to a Tier-3 boundary that the eventual plan and decision-record work must
carry forward honestly.

- **What it changes:** `decisions/runtime-and-deps.md` today constrains the
  enforcement core to **stdlib-only** (§Constraints; `runtime-and-deps.md:41-44`
  forbids exactly this without a recorded decision). Ed25519 has no stdlib
  primitive, so 3C is not implementable without this carve-out. It also touches
  the "G-3.1 reuse / `verify/marker.py` unchanged" commitment
  (`tier3-signed-approval.md:47-52`).
- **Status of the decision:** **implicitly settled — a consequence of choosing
  3C, not a separately re-litigated question.** The operator decided 3C knowing
  the dependency is its precondition; item 3 was not re-argued on its own merits.
- **Discipline it must be written under:** a **narrow, named exception**, scoped
  to asymmetric sign/verify for the approval token and nothing else — the same
  discipline as this session's other stdlib-only carve-out, the `mcp` SDK import
  confined to the single named file `approval/mcp_server.py` (§Constraints). The
  exception must name the permitted purpose and the permitted call sites; it is
  **not** a general relaxation of the stdlib-only rule.
- **Tier-3 work this implies (operator territory, not this brief's to write):**
  an amendment to `decisions/runtime-and-deps.md` recording the named exception,
  and an amendment to `decisions/tier3-signed-approval.md` for the G-3.1-reuse /
  `verify/marker.py`-unchanged commitment. Both are listed in §Scope Sketch under
  "Tier-3 records (operator)".
- **Attribution:** operator, direct conversation with orchestrator, this session
  (as a consequence of Decision 2).

### Still OPEN — 5 decisions, NOT converged, deferred to a future round

Explicitly unresolved. These are **not** answered by Decisions 1–3, and none may
be inferred from them. Numbering matches
§"Items requiring the operator's direct convergence":

| # | Open decision | Why it is not settled by Decisions 1–3 |
|---|---|---|
| **4** | **Fork 2 launch mechanism** — 2A `sudo -u`, 2C `launchd`, or 2D/3B IPC-shaped | Choosing Ed25519 settles *which key primitive*, not *how the signer process comes to run under its own uid*. Still fully open. **This is the item that blocks planning.** |
| **5** | **Fork 1 provisioning** — extend `ansible/site.yml` (1A) or a parallel signer playbook (1B) | Independent of the key primitive; unchanged by Decisions 1–3. |
| **6** | **Is a spike authorised before committing to 2C?** | Dependent on Decision 4; the Dunning-Kruger flag at §Fork 2 (launchd `UserName` with a non-login account and a repo-local `.venv` interpreter is asserted from docs, **not** probed on this host) still stands. |
| **7** | **Is the cross-cutting caged-mode-only honesty statement accepted?** | Not put to the operator. §Fork 4's floor — that signer-uid separation binds meaningfully only in CAGED mode, and O-3(b)'s implied uncaged value must be qualified rather than inherited — remains an unaccepted advisory claim. |
| **8** | **Scope ruling on the adjacent armed-pipeline collision** (`sequence-gate.ts`, `advance-hook.ts` hit the same caged key-read wall when armed, §F-1) — in scope here, or its own tracked item? | Not resolved by the Decision-1 split, which covered the **approval listener** only. The armed-pipeline collision has **no** home yet. |

**Readiness verdict: NOT ready for `gleipnir-plan`.** Decision 4 (launch
mechanism) is a hard blocker — §Scope Sketch's "Launch mechanism" row cannot be
planned while 2A/2C/2D are all live, and Decision 6 (spike) is downstream of it.
Decisions 5, 7 and 8 shape provisioning scope, the honesty ledger, and the
touched-path set respectively. A second convergence round is required.

---

## Problem Statement

The `gleipnir-approval` MCP subprocess is the **signer**: it is the process that
reads `GLEIPNIR_MARKER_KEY_FILE` and, via `server.py:capture_approval` →
`token.mint_approval`, mints the Tier-3 approval tokens that `tier3-gate.ts`
requires before any Tier-3 write lands. Today that signer and every roster
agent's tool-invocation process run under **one shared OS uid**. The two controls
built this session (PR #6's opencode-spawned MCP, PR #7's roster-wide `.env*`
permission deny) are — by their own explicit labels — cooperative /
opencode-application-layer controls, not OS isolation. The operator-established
framing, recorded verbatim at `tier3-signed-approval.md:236-244`, is that an
agent-frontmatter permission deny "is NOT a file-permission (chmod/chown)
control. Real OS file permissions can only separate two processes if they run
under different uids."

The deferred follow-on this brief explores is therefore: **give the signer its
own OS uid**, so that the key's protection becomes a filesystem fact rather than
a cooperative convention.

**What Explore changed about that problem statement.** Two verified findings
(§Explore F-1, F-2) show the problem is *not* the additive hardening the
deferral implies. It is (a) the fix for a collision caged mode **already has
today**, and (b) blocked by a symmetric-key constraint nobody has yet named.
The framing "same primitive, opposite direction, reuse the S-2 machinery" is
structurally **incorrect** as stated, and the brief says so plainly rather than
inheriting it.

---

## Constraints

- **Platform is macOS (`darwin`, confirmed this session).** User creation is
  `dscl`/`sysadminctl`, never `useradd`/`adduser`.
- **Enforcement core is stdlib-only Python** (`runtime-and-deps.md`). The MCP
  SDK carve-out is **one named file** (`approval/mcp_server.py`); `token.py`,
  `gate.py`, `verify/marker.py` must stay dependency-free. This constraint is
  load-bearing on Fork 3 below.
- **G-3.1 reuse is a recorded design commitment**: the approval token reuses
  `verify.marker`'s HMAC key and discipline, and `verify/marker.py` is
  explicitly "reused, NOT modified" (`tier3-signed-approval.md:52`).
- **Default posture is UNCAGED** (`operating-posture.md`); caged is opt-in. The
  `keys/marker.key` `chmod 600` floor is retained in **both** modes.
- **Operator executes OS/root acts**; the agent guides and verifies
  (`go-caged-runbook.md:28-36`, `tier3-coach` Anti-Pattern 3). No in-framework
  agent can create a uid, `chown`, or configure sudoers.
- **opencode spawns MCP servers as child processes** of itself
  (`opencode.jsonc:91-100`, `type: "local"`, `command: [...]`), so an MCP child
  inherits opencode's uid and its environment unless something actively changes
  that.
- Tier-0 write boundary: this brief may only be written to `.gleipnir/plans/**`.
  Naming precedent confirmed by `ls .gleipnir/plans/*brainstorm*` (38 files, all
  `<slug>-brainstorm.md`).

---

## Explore — findings

### F-1 (MATERIAL, UNANTICIPATED): caged mode already breaks the signer today

This is not a hypothetical about future work; it is a present defect reachable
by following the `go-caged` runbook as written.

Chain, each link verified:

1. `bin/gleipnir-launch:37-43` execs opencode via
   `sudo -u "#${GLEIPNIR_AGENT_UID}"` — under caged mode **opencode itself runs
   as the agent uid**.
2. `ansible/site.yml` act 5 (`:375-382`) sets `keys/marker.key` to mode `0600`,
   owner `{{ operator }}`. `boundary.py`'s `RO_AND_UNREADABLE` posture
   (`:995-999`) makes the caged AC-4 gate **require** that the agent uid cannot
   read it. Caged mode is *defined by* the key being unreadable to the agent uid.
3. `opencode.jsonc:91-100` spawns `gleipnir-approval` as an opencode child ⇒
   under caged mode the signer MCP runs **as the agent uid**.
4. `mcp_server.py:206` calls `run_server(...)` → `server.py:398` `load_key(...)`
   → `marker.py:100-103` `Path(path).read_bytes()` → **EACCES**, raising
   `KeyUnavailable`.
5. `mcp_server.py:207-212` catches it broadly (Decision 19 log-and-continue) and
   the listener thread **exits quietly while the `request_approval` tool surface
   stays up**.

**Net effect: in caged mode the approval listener silently fails to bind.**
`request_approval` still returns a plausible `/approve/<hash>` URL (it never
touches the key — enforced by the T-11 reverse-import scan), so the failure
presents as "the approval URL doesn't respond," with the diagnostic buried in a
`logger.warning` on a dead daemon thread. Caged mode is precisely the posture
`operating-posture.md:43-44` names for "handling secrets" — the posture where
signed approval matters most is the one where it is broken.

**Adjacent instance of the same collision (armed pipeline).**
`sequence-gate.ts:120-123` and `advance-hook.ts:200-203` both `readFileSync`
the key from inside the opencode process. Under caged mode those reads also
EACCES; both are fail-closed, so `sequence-gate` would `throw GateAbort` on
**every `task` delegation**. This is gated behind `isArmed` (`GLEIPNIR_PIPELINE=on`
plus a bridge file, `:92-101`), so it bites only an armed caged run — but caged +
armed is exactly the high-assurance configuration the framework is aiming at.

**Why this inverts the deferral's framing.** The recorded framing is "protecting
the signer FROM the agent's uid." Under caged mode the *existing* posture already
denies the signer the key, because the signer is a child of the caged agent
process. The real requirement is not "take the key away from the agent" — caged
mode did that — it is **"get the signer OUT of the agent's uid so it can be
granted the key back."** Same OS primitives, but the design goal is the mirror
image of what the deferral note says.

### F-2 (MATERIAL, UNANTICIPATED): the key is symmetric, so isolating the signer breaks every validator

The approval token is an **HMAC** (`tier3-signed-approval.md:47-52`,
`token.py`). HMAC is symmetric: **validation needs the identical key as
minting.** The deferral's proposed shape ("dedicated service account + `chown`")
implicitly assumes only the signer needs the key. Verified list of processes that
call `load_key`/`loadKey` on the *same* `GLEIPNIR_MARKER_KEY_FILE`:

| Reader | Site | Role | Runs as |
|---|---|---|---|
| approval listener | `server.py:398` | **mint** | opencode MCP child |
| approval **gate CLI** | `approval/__main__.py:92` | **validate** | spawned by `tier3-gate.ts` → inside opencode |
| `sequence-gate.ts` | `:120-123` | validate | in-process opencode plugin |
| `advance-hook.ts` | `:200-203` | validate | in-process opencode plugin |
| engine driver | `engine/driver.py:159,194` | mint+validate | framework process |
| ledger rate-table | `ledger/ratetable.py:109` | validate | framework process |
| bridge recovery | `preflight/bridge_recovery.py:157` | validate | preflight (owner) |
| verify CLI | `verify/__main__.py:42,73` | mint+validate | operator/CI |

`tier3-gate.ts:207-208,337-338` `spawnSync`s `.venv/bin/python -m
gleipnir.approval.gate` **from inside opencode**, so the token *validator* runs
at the agent's uid and must read the key. Therefore:

> `chown signer:signer marker.key && chmod 600` — the literal deferral proposal —
> makes the **gate** unable to validate. Every Tier-3 write then fail-closes
> (exit 3, `KeyUnavailable`, `__main__.py:93-95`). The subsystem stops, in the
> safe direction, but stops.

There is no arrangement of one symmetric key across two uids that gives the
signer exclusivity while leaving the validator working. This is a genuine
**structural blocker**, not a detail — and it means **Fork 3 (scope) must be
answered before Forks 1 and 2 are meaningful**, reversing the ordering implied
by the delegation. Three ways out exist, and choosing among them is Fork 3.

### F-3: macOS-correctness of the existing S-2 machinery — VERIFIED CORRECT

Directly checked against the real files, as a finding rather than a guess:

- `s2-activation-control-proposal.md:38-58` uses `dscl . -list /Users UniqueID`
  to check a free uid, `dscl . -create /Groups/...` for the group, and
  `sudo sysadminctl -addUser ... -UID ... -GID ... -home /var/empty -shell
  /usr/bin/false`, **with an explicit `dscl`-only fallback** at `:51-55`. These
  are the correct macOS tools.
- `ansible/site.yml:98-139` mechanises the same commands via `ansible.builtin.command`,
  with the comment at `:99-101`: "`command:`, not `ansible.builtin.user` (BC-5):
  unreliable on Darwin for a non-login service account." The Darwin constraint
  was consciously handled, not overlooked.
- `bin/gleipnir-launch:34-37` notes root is needed "to setuid to another account
  on macOS" and uses `sudo -u "#uid" -g "#gid"` — portable and correct.
- **No `useradd`/`adduser`/`/etc/passwd`/`chpasswd` anywhere.** Grepped; zero hits.

**Verdict: macOS-correct as written. No pre-existing platform gap to flag.**
Two minor, non-blocking nits worth carrying if a signer account is created by
the same route: (i) `sysadminctl -addUser` creates an account that can surface
in the login window / Users pane unless `IsHidden` is set — cosmetic, not a
security issue; (ii) the `510` uid in the proposal is illustrative and the
"verify free first" instruction is present and correct, so a second account must
pick a *different* free id (e.g. `511`) rather than copy the literal.

### F-4: uncaged-default value — real, but not the "just works" the O-3(b) framing implies

Under the uncaged default, opencode runs as the **operator's own uid** and
`marker.key` is mode 600 owner-only — i.e. **owned by, and readable by, the very
uid opencode runs as.** The `.env*` deny blocks the opencode `read`/`edit` tool
dispatch path, but any future `bash` capability, or a compromised MCP/opencode,
reads the key trivially. So signer-uid separation *does* deliver genuine value
uncaged — it is the only proposed control that makes the key unreadable to agent
`bash` without entering caged mode.

But it does not "just work": chowning the key away from the operator's uid breaks
the validators (F-2) **and** makes the operator's own `verify`/`ledger`/preflight
CLIs require `sudo`. Uncaged benefit is real; uncaged cost is a daily-ergonomics
tax on the operator's own tooling. Honest read: **value is higher in caged mode
(where it fixes F-1's outright breakage) than uncaged (where it trades ergonomics
for a bash-hardening gain).**

### F-5: the inversion is NOT structurally simple (answering the delegation's question directly)

The delegation asks whether reuse is "structurally simple (swap which side gets
the new uid)" or "genuinely different." Verified answer: **genuinely different**,
for three independent reasons.

1. **Direction of privilege.** S-2 creates a *low*-privilege uid and drops
   opencode *into* it (`gleipnir-launch` execs as the agent uid). The signer needs
   a uid that holds something the launching process does **not** — you cannot drop
   into it, you must escalate into it. A privilege *drop* and a privilege
   *acquisition* are not the same operation with a swapped argument.
2. **Who launches.** S-2's drop happens once, at the top, by an operator running
   `sudo`. The signer is spawned **by opencode**, mid-session, from a `command:`
   array in `opencode.jsonc`. An unprivileged opencode process cannot spawn a
   child under a different uid without root/sudo assistance — this is the crux
   Fork 2 exists to resolve.
3. **Key access is inverted.** S-2's whole point is `RO_AND_UNREADABLE` to the
   new uid. The signer's whole point is that the new uid is the **only** reader.
   Reusing one mechanism would require it to express both polarities.

Consequence: the shared surface is only the thin bottom layer — "create a macOS
service account" (`dscl`/`sysadminctl`) and "set ownership/mode." Everything
above that (launch, key polarity, preflight semantics) differs. This directly
shapes Fork 1.

---

## The four forks (plus the prerequisite F-2 fork)

Ordering note: **Fork 3 is logically first** because F-2 makes Forks 1–2 moot
until the symmetric-key question is answered. Presented in the delegation's
numbering for traceability, with the dependency called out.

---

## Fork 1 — reuse the S-2 uid machinery, or a parallel mechanism?

### Approach 1A: extend the existing machinery to "create N special uids"

**Summary:** generalise `agent-identity.env` → an identities file carrying both
`GLEIPNIR_AGENT_UID` and `GLEIPNIR_SIGNER_UID`; add signer acts to `ansible/site.yml`
alongside acts 1–6; one runbook, one playbook, one AC gate.

- Pro: one provisioning entry point; the operator runs one playbook.
- Pro: the macOS account-creation commands (F-5's shared bottom layer) are
  written and idempotency-tested once.
- Pro: `ansible/site.yml`'s existing AC-4-as-failing-assertion pattern extends
  naturally to a signer AC.
- Con: **couples opposite polarities in one artifact.** `site.yml`'s D5/D6
  comments (`:141-163`, `:218-257`) document that this playbook *already* fought
  hard-won idempotency bugs from overlapping perm passes; adding a path that must
  be *readable to signer, unreadable to agent, unreadable to operator-by-default*
  reintroduces exactly that class of overlap on the single most dangerous file.
- Con: an agent-cage regression and a signer regression become
  indistinguishable in one AC surface.
- Con: `group_vars/all.yml`'s AC-nolit / AC-mirror invariants are written around
  one identity; widening them is a real edit to tested enforcement config.

**Scope:** `ansible/site.yml`, `ansible/group_vars/all.yml`, `ansible/tests/*`,
`.gleipnir/agent-identity.env` schema, `go-caged-runbook.md`,
`s2-activation-control-proposal.md`. **Complexity: medium-high.**
**Risk: medium-high** — regression risk against a green, idempotency-hardened
playbook that currently gates caged mode.

### Approach 1B: parallel mechanism, shared primitives only

**Summary:** a separate `signer-identity.env`, a separate provisioning path
(`ansible/signer.yml` or its own control-proposal section), its own AC gate. The
only reuse is the *documented pattern* — the same `dscl`/`sysadminctl` shape,
the same operator-executes handoff, the same failing-assert discipline.

- Pro: matches the actual structure of the problem (F-5): the two mechanisms
  share a thin bottom layer and nothing above it.
- Pro: independently reversible — tearing down the signer account cannot regress
  the agent cage or its AC-4 verdict.
- Pro: no edit to the green, idempotency-tested `site.yml` / `group_vars`
  invariants.
- Pro: honest about polarity — the two files can each state their own key
  posture without a shared abstraction straining to cover both.
- Con: some genuine duplication of the account-creation commands (DRY cost).
- Con: two provisioning steps for the operator, two ACs to keep aligned.
- Con: drift risk — a future macOS change to `sysadminctl` must be fixed twice.

**Scope:** new `ansible/signer.yml` + vars + tests, new control-proposal doc,
runbook cross-reference. **Complexity: medium.** **Risk: low-medium.**

### Decision Analysis — Fork 1

**Framework used:** Reversibility Filter → Pros-Cons-Fixes (binary choice; the
auto-selection table's "Binary choice (A or B)" row).

```
Reversibility: Two-Way Door (but asymmetric)
Reversal cost: 1B → 1A later is a mechanical merge of two working playbooks.
               1A → 1B later means un-picking a shared identities schema and
               re-establishing two ACs, against tested invariants.
Recommendation: Fast-track, but prefer the direction with the cheaper reversal.
```

```
Option 1A — extend existing
Cons and Fixes:
| Con | Fix |
| Polarity coupling reintroduces D5/D6-class overlap | Explicit path-ownership table; but D5/D6 show this is exactly what gets missed |
| Indistinguishable AC surface | Split assertions with distinct fail_msgs — partial fix only |
Post-fix verdict: Marginal

Option 1B — parallel, shared primitives
Cons and Fixes:
| Con | Duplicated account-creation commands | Extract a shared Ansible role/task-file for "create a macOS service account", parameterised by name/uid — removes most duplication without coupling polarity |
| Con | Two ACs to keep aligned | Each AC is narrower and independently meaningful; alignment is a doc cross-reference, not a shared invariant |
Post-fix verdict: Viable
```

**Bias warnings.**
- ⚠️ **Sunk Cost Fallacy** (would favour 1A): "we already built the S-2 uid
  machinery, extend it." Past investment is not a reason. Asking the framework's
  own question — *if starting today with no playbook, would one artifact express
  both polarities?* — the answer is no (F-5).
- ⚠️ **IKEA Effect** (would favour 1A): the S-2 machinery is ours and works, so
  its fit is easy to overrate. Evaluated as if written by someone else, it is a
  privilege-*drop* tool being asked to do privilege-*acquisition*.
- ⚠️ **Scope Creep Bias** (watch on 1A): "one unified mechanism for N uids"
  broadens scope to avoid choosing a polarity, which is deferred
  decision-making rather than a decision.

**Recommendation [ADVISORY — NOT DECIDED]: Approach 1B**, with the con fixed by
extracting one shared, parameterised "create a macOS service account" task-file.
Reasoning: F-5 establishes the mechanisms are genuinely different above a thin
shared layer; 1B has the cheaper reversal; and 1B keeps a green caged-mode gate
out of the blast radius. **For the operator to decide.**

---

## Fork 2 — how does opencode (as the operator's/agent's uid) spawn the signer as a *different* uid?

The crux. All four options assume Fork 3 has been answered such that the signer
holds something others don't.

### Approach 2A: `sudo -u signer` inside `opencode.jsonc`'s `command:`

**Summary:** `command: ["sudo","-u","gleipnirsigner",".venv/bin/python","-m","gleipnir.approval.mcp_server"]`,
with a narrowly-scoped passwordless sudoers rule for exactly that command.

- Pro: smallest diff — one `command:` array; process supervision, lifecycle and
  stdio all keep working exactly as now.
- Pro: mirrors a shape already in the repo (`gleipnir-launch` uses `sudo -u
  "#uid"`), so it is a known-working pattern on this host.
- Pro: survives restarts trivially — opencode respawns the child as always.
- Con: **the sudoers rule is the new attack surface** (Fork 4). A `NOPASSWD`
  rule invocable by the agent's uid is a capability the agent can also invoke.
- Con: sudo's `env_reset` strips `GLEIPNIR_MARKER_KEY_FILE` — the exact trap
  `bin/gleipnir-launch:18-26` and `ansible/site.yml:403-412` both already
  document. Needs `env_keep` or a re-established default, or the signer starts
  keyless and F-1's silent-failure path triggers again.
- Con: `opencode.jsonc` is in the Axis-2(a) enforcement-path set, so this is a
  hardened-path change requiring the two-pass review + negative-check attestation.

**Scope:** `opencode.jsonc`, `/etc/sudoers.d/gleipnir-signer` (operator),
env-passing fix. **Complexity: low-medium.** **Risk: medium** — security rests
entirely on sudoers scoping.

### Approach 2B: setuid wrapper binary

**Summary:** a small C setuid-root (or setuid-signer) wrapper that execs the MCP.

- Pro: no sudoers entry; no reliance on sudo's env semantics.
- Pro: can hard-code argv, so it cannot be repurposed to run arbitrary commands.
- Con: **a setuid binary in the repo tree is a heavier, sharper liability** than
  the sudoers rule it replaces — and introduces C, a compiler and a build step
  into a stdlib-Python/TS project.
- Con: macOS ignores setuid on many mount configurations and hardened-runtime
  contexts; needs empirical verification, not assumption.
- Con: setuid binaries are a classic LPE surface; any argv/env handling bug is a
  root bug.
- Con: contradicts the project's trust-surface-minimisation rationale
  (`runtime-and-deps.md:34-39`).

**Scope:** new C source, build wiring, install perms. **Complexity: high.**
**Risk: high.** Assessed as **overkill**, consistent with the delegation's own
prior.

### Approach 2C: launchd-managed signer + socket, opencode no longer spawns it

**Summary:** a `launchd` plist with `UserName`/`GroupName` runs the listener as
the signer uid, independent of opencode. opencode's MCP either goes away or
becomes a thin client that talks to the already-running listener over the
existing localhost HTTP surface.

- Pro: **the only option where the signer is never a child of the agent process
  at all** — it eliminates F-1's root cause structurally rather than patching
  around it, in both caged and uncaged mode.
- Pro: no sudoers rule and no setuid binary. Privilege is established once, by
  launchd, at load time.
- Pro: `launchd` is the native macOS supervisor: `KeepAlive`, restart-on-crash,
  boot persistence — strictly better lifecycle than an opencode child.
- Pro: survives opencode restarts *better* than today (the current daemon thread
  dies with opencode, `mcp_server.py:224-225`).
- Pro: the listener already binds `127.0.0.1:8765` and already speaks HTTP
  (`server.py:379-408`), so the transport exists.
- Con: **biggest architecture change of the four.** Reopens "who launches it,"
  though `tier3-signed-approval.md:186-199` already settled that the security
  locus is key-*readability*, not process-*launch* — so reopening it is cheap.
- Con: `request_approval` (the staging tool) must either stay an opencode-spawned
  MCP that writes the shared `.gleipnir/var/tmp/` envelope (it needs no key, so
  this is fine and requires no change) or become an HTTP call. Needs a decision.
- Con: a plist is a new operator-managed artifact with its own load/unload
  ergonomics (`launchctl bootstrap`), and is harder to make fully reversible in
  a dev loop.
- Con: two processes to reason about when debugging.

**Scope:** new `~/Library/LaunchAgents/…plist` (operator), `opencode.jsonc`
(possibly `mcp_server.py`'s thread-start removed), runbook. **Complexity:
medium-high.** **Risk: medium.**

### Approach 2D (found during Explore): signer-owned key + verify-over-IPC

**Summary:** the launch question becomes secondary. The signer (by 2A or 2C)
holds the key **exclusively**, and every *validator* stops reading the key
locally — instead calling a new `verify` endpoint on the signer's existing
localhost listener. Sole reader of the key: the signer uid.

- Pro: **the only option that actually achieves the stated goal** — exclusive
  signer key access — while leaving validation working (directly answers F-2).
- Pro: preserves stdlib-only: no crypto dependency, HMAC unchanged, `verify/marker.py`
  untouched, honouring `tier3-signed-approval.md:52`.
- Pro: shrinks the key's reader set from eight processes (F-2 table) to one — a
  large, genuine reduction in trusted surface.
- Con: **availability coupling.** Listener down ⇒ no validation ⇒ fail-closed ⇒
  every Tier-3 write and (if armed) every delegation refused. Arguably the
  correct direction, but it is a real operational sharp edge and an
  availability-as-security-dependency the framework has not taken on before.
- Con: touches `sequence-gate.ts`, `advance-hook.ts`, `approval/__main__.py`,
  `ledger/ratetable.py`, `bridge_recovery.py` — the enforcement core and Tier-3
  plugins. Largest code blast radius of any option here.
- Con: a localhost verify endpoint is itself reachable by the agent uid — it
  moves the boundary from "read the key" to "ask the oracle," and an oracle that
  validates arbitrary submitted tokens must be designed not to become a minting
  or probing surface.
- Con: substantially exceeds "uid separation for the approval MCP" in scope.

**Scope:** all validator call sites + a new endpoint. **Complexity: high.**
**Risk: medium-high.**

### Decision Analysis — Fork 2

**Framework used:** Weighted Decision Matrix (multi-option, 4 candidates), then
Second-Order Thinking on the leader. Weights reflect the framework's stated
priorities: integrity > efficiency, honest labelling, operator ergonomics for a
single-operator dev loop.

| Criterion | W | 2A sudo | 2B setuid | 2C launchd | 2D IPC |
|---|---|---|---|---|---|
| Actually achieves OS isolation | 10 | 6 → 60 | 7 → 70 | 8 → 80 | 10 → 100 |
| Does not create a worse new surface | 9 | 4 → 36 | 2 → 18 | 8 → 72 | 5 → 45 |
| Fixes F-1 (caged breakage) | 9 | 5 → 45 | 5 → 45 | 10 → 90 | 9 → 81 |
| Setup/ergonomic cost (higher=cheaper) | 6 | 9 → 54 | 3 → 18 | 6 → 36 | 3 → 18 |
| Survives restarts cleanly | 6 | 8 → 48 | 8 → 48 | 10 → 60 | 7 → 42 |
| Testable / reversible | 7 | 8 → 56 | 4 → 28 | 6 → 42 | 4 → 28 |
| Blast radius on tested code (higher=smaller) | 7 | 9 → 63 | 7 → 49 | 6 → 42 | 2 → 14 |
| Honours stdlib-only | 8 | 10 → 80 | 6 → 48 | 10 → 80 | 10 → 80 |
| **Total** | | **442** | **324** | **502** | **408** |

**Recommended by matrix: 2C (launchd), 502.**

**Caveats where the winner scores poorly:** 2C's ergonomic cost (6) and
reversibility (6) are its weak axes — a plist is more friction in a dev loop
than a one-line `command:` change. And critically, **2C alone does not resolve
F-2**: it gets the signer out of the agent's uid, but if the key must stay
readable to the validators, the signer's *exclusivity* is not achieved. 2C and
2D compose: 2C is the launch answer, 2D is the exclusivity answer.

```
Second-Order Thinking — 2C
Near term (3–6 months):
  First-order: signer runs as its own uid under launchd; F-1's caged breakage gone.
  Second-order: caged mode becomes genuinely usable for the approval subsystem
    for the first time; the "signer" concept becomes a first-class, separately
    provisioned component rather than an opencode implementation detail.
Far term (1–2 years):
  First-order: a standing, always-on local signing service exists.
  Second-order: it becomes the natural home for the E-2 webhook ingress and for
    Route β (OIDC) — a real architectural asset.
  Third-order: RISK — a standing service is a standing surface. The current
    design deliberately dodged "no standing public inbound port"
    (tier3-signed-approval.md:77-80). launchd + KeepAlive makes the listener
    always-on rather than session-scoped. Tailnet-only binding must be
    re-verified, not inherited.
Key insight: 2C's real value is not sudo-avoidance; it is that the signer stops
  being a descendant of the guarded process. Its real cost is converting a
  session-scoped surface into a standing one.
Verdict: Proceed — monitor the standing-surface effect.
```

**Bias warnings.**
- ⚠️ **Anchoring Bias**: the deferral note names `sudo -u signer …` explicitly
  and was the first option introduced, in the decision record itself. It
  anchors hard. Evaluated independently it ranks **third of four**, and its
  sudoers rule is the very hole Fork 4 exists to name. Weight the record's
  phrasing as an early sketch, not a finding.
- ⚠️ **Authority Bias**: `sudo -u signer …` carries the authority of an applied
  Tier-3 decision record. But that record names it as an *example* ("e.g."), not
  a converged design — it has never been through this gate.
- ⚠️ **Dunning-Kruger**: I have **not** empirically verified macOS setuid
  semantics (2B) or `launchd` `UserName` behaviour with a non-login account and
  a `.venv` interpreter (2C) on this host. Both are asserted from documentation,
  not probed. Confidence in 2C's mechanics is **Medium, not High**; a spike is
  warranted before committing. (Others detected but not surfaced: Status Quo
  Bias favouring today's opencode-spawned shape.)

**Recommendation [ADVISORY — NOT DECIDED]: 2C as the launch mechanism, gated on
a spike** that proves a launchd-managed, non-login-signer-uid process can run
`.venv/bin/python` and bind `127.0.0.1:8765` on this host — **and composed with
whatever Fork 3 decides about the key.** Reject 2B (overkill, and a worse surface
than the one it removes). **For the operator to decide.**

---

## Fork 3 — scope: just the approval MCP's signer, or every Tier-3-adjacent key reader?

**This fork is where F-2 lands, and it is the one that must be answered first.**

The delegation asks whether uid-separating only the approval MCP leaves other
readers same-uid-as-agent, "undermining the isolation claim." Verified answer:
**yes, decisively, and worse than the question implies** — the same-uid readers
are not incidental bystanders, they are the *validators of the very tokens the
signer mints* (F-2 table). Narrow scope does not merely leave a gap; it makes
the isolation claim self-defeating, because the thing you must keep the key from
(the agent's uid) is the thing that must have the key to check the token.

### Approach 3A: narrow — signer uid only, key stays group-readable to the agent uid

**Summary:** create the signer uid, run the MCP as it, but leave `marker.key`
readable by the agent/operator uid so all validators keep working.

- Pro: smallest change; nothing else breaks; F-1's caged breakage is fixed
  (the signer is no longer starved of the key).
- Pro: honest partial win — process separation is real even if key exclusivity is not.
- Con: **delivers no key confidentiality whatsoever.** The agent uid can still
  read the key, so it can still mint tokens. The headline goal — "OS-level
  secret isolation" — is *not* achieved.
- Con: **high false-assurance risk.** "The signer runs under its own uid" reads
  as isolation to any future reader. This is precisely the L-C7 false-success
  class the hardened review path exists to catch.

**Complexity: low. Risk: LOW technically, HIGH for honesty/false-assurance.**

### Approach 3B: exclusive signer key + verify-over-IPC (= 2D)

**Summary:** key readable only by the signer uid; validators call the signer.

- Pro: genuinely achieves the stated goal. Reader set 8 → 1.
- Pro: stdlib-only preserved; HMAC and `verify/marker.py` untouched.
- Con: largest blast radius (enforcement core + two Tier-3 plugins).
- Con: availability coupling; oracle-design care needed.

**Complexity: high. Risk: medium-high.**

### Approach 3C: asymmetric signing (Ed25519) — separate mint and verify keys

**Summary:** replace the approval token's HMAC with a signature. Signer holds
the private key (signer-uid-only, mode 600); validators hold only the public
key, which is safe to leave world-readable.

- Pro: **the textbook-correct answer.** Asymmetry is exactly the primitive the
  problem calls for; it dissolves F-2 rather than working around it.
- Pro: no availability coupling — validators verify locally, offline. No oracle.
- Pro: a public key in the repo is harmless, simplifying the whole perms story.
- Con: **collides head-on with two recorded Tier-3 decisions.** Python's stdlib
  has **no** Ed25519 signing primitive, so this requires a third-party
  dependency (`cryptography`) in the **enforcement core** — the exact thing
  `runtime-and-deps.md:41-44` forbids without a recorded decision, and it enters
  the S-2 trusted surface. It also breaks the "G-3.1 reuse, `verify/marker.py`
  unchanged" commitment (`tier3-signed-approval.md:47-52`).
- Con: asymmetric on the TS side is fine (`node:crypto` has Ed25519), but the
  Python/TS cross-language canonical-signing-input contract — currently
  golden-fixture-pinned (`sequence-gate.ts:32-40`) — must be re-established for
  a new primitive.
- Con: a key-format migration for a live subsystem.

**Complexity: high. Risk: high** (two Tier-3 decision amendments + a crypto
migration).

### Decision Analysis — Fork 3

**Framework used:** Second-Order Thinking → Pre-Mortem (architectural tradeoff
with long-term consequences; the auto-selection table's "Architectural
tradeoff" row).

```
Second-Order Thinking

Decision 3A (narrow):
  Near term: cheap; F-1 fixed; docs say "signer has its own uid."
  Second-order: the honesty ledger must state "no key confidentiality gained,"
    which invites the reasonable question "then why did we do this?" Answer:
    F-1. That is a genuine reason — but it is a BUG FIX, not the isolation
    follow-on, and conflating them is the false-assurance risk.
  Far term: the O-3(b) gap stays open while *appearing* closed. Highest
    long-term risk of the three despite the lowest technical risk.
  Verdict: Caution — acceptable ONLY if labelled as an F-1 bug fix, explicitly
    NOT as the isolation follow-on.

Decision 3B (IPC):
  Near term: real isolation; substantial code change.
  Second-order: the signer becomes a required, always-available dependency of
    every Tier-3 write and every armed delegation. Security via availability.
  Far term: a local signing service is a solid asset (E-2, Route β), but a
    fail-closed dependency on a local daemon will bite during dev.
  Verdict: Proceed with mitigations (clear diagnostics; never silent — F-1's
    log-and-continue is the anti-pattern to avoid repeating).

Decision 3C (Ed25519):
  Near term: two Tier-3 amendments + migration. Slowest start.
  Second-order: dissolves the problem class permanently. No oracle, no
    availability coupling, and every future verifier (CI, remote C-tier
    verifier named in s2-g1-closure) needs only a public key — which is exactly
    what the C-tier "remote verifier" direction wants.
  Far term: strictly the cleanest end-state; one new dependency in the trusted
    surface, deliberately recorded.
  Key insight: 3C is the only option whose cost is PAID ONCE. 3A's cost is
    permanent false assurance; 3B's is permanent availability coupling.
  Verdict: Proceed IF the operator accepts a recorded enforcement-core dependency.
```

```
Pre-Mortem: "we chose 3A (narrow) and it was a failure" — horizon 12 months
| # | Failure mode | Likelihood | Impact | Mitigation |
| 1 | A later reader treats "signer has own uid" as key isolation and builds on it | H | H | Explicit honesty-ledger row: "process separation only; key NOT confidential" |
| 2 | O-3(b) is quietly considered closed and dropped from the follow-on list | M | H | Keep O-3(b) open verbatim; add a NOT-CLOSED-BY-THIS row |
| 3 | An agent with bash reads the key; incident review finds we "did uid separation" | M | H | Only 3B/3C actually prevent this — no mitigation available within 3A |
| 4 | The F-1 fix is bundled and its urgency is lost in the bigger scope debate | M | M | Split F-1 into its own immediate change (see Fork 3 recommendation) |
| 5 | Two half-built isolation stories accumulate | M | M | Decide 3B-vs-3C now, even if built later |
Top risks: #1, #3
Verdict: Proceed only with #1/#2/#4 mitigations, and only if labelled as a bug fix.
```

**Bias warnings.**
- ⚠️ **Scope Creep Bias** — the strongest detector triggered on this fork.
  F-2 legitimately expands scope, and there is a real pull toward "do all of
  3A+3B+3C" or toward re-designing the crypto while nominally uid-separating one
  MCP. The mitigation is to **split** rather than expand: F-1 is an urgent,
  narrow bug fix; the isolation architecture is a separate decision. That is a
  decomposition, not a scope expansion.
- ⚠️ **Confirmation Bias** — having found F-2, I am inclined to favour whichever
  option most vindicates the finding (3C). Counter-evidence sought and recorded:
  3C requires amending two applied Tier-3 records and a live-key migration;
  3A genuinely does fix the concrete present breakage, which is the only
  *observed* failure. F-2 is a reasoned structural claim; F-1 is a demonstrable
  defect. That ordering favours doing 3A's bug-fix half first.
- ⚠️ **Status Quo Bias** — "HMAC + G-3.1 reuse works, don't touch the crypto"
  deserves the same scrutiny as the alternatives. Asked fresh: *if designing the
  approval token today, knowing minting and validation sit on opposite sides of
  a trust boundary, would HMAC be chosen?* Almost certainly not — that is
  exactly the asymmetric-signature use case. The symmetric choice was rational
  when both sides were the same uid; introducing a uid boundary is precisely what
  invalidates its premise.

**Recommendation [ADVISORY — NOT DECIDED]: split this fork in two.**
1. **Immediately, narrow (3A-as-bug-fix):** fix F-1 — get the signer out of the
   caged agent uid so caged mode stops silently breaking — and label it in the
   honesty ledger *unambiguously* as a caged-mode bug fix that delivers **no**
   key confidentiality and does **not** close O-3(b).
2. **Then, as its own converged decision: 3C (Ed25519)** as the target end-state,
   because it is the only option whose cost is paid once, and because it aligns
   with the already-named C-tier remote-verifier direction. It requires the
   operator to accept a recorded `cryptography` dependency in the enforcement
   core — a genuine Tier-3 amendment that only the operator can make. If that
   dependency is refused, **3B (IPC)** is the stdlib-preserving fallback.

**For the operator to decide.**

---

## Fork 4 — the new residual gap (honesty ledger for whatever gets built)

Naming the *new* hole per option, so no outcome can imply "fully closed."

### If 2A (`sudo -u signer`)

- **The sudoers rule IS the new attack surface — confirmed, not hypothetical.**
  A `NOPASSWD` rule permitting the agent's uid to run
  `python -m gleipnir.approval.mcp_server` as the signer is a capability the
  *agent* can also invoke. The agent cannot read the key, but it can start a
  process that can — and can then interact with that process. Whether that
  yields a mint depends entirely on the listener's identity resolution
  (`tailscale whois` against a separate authenticated peer), which becomes
  **load-bearing in a way it was not designed to be**.
- Any argument laxity in the sudoers spec (a wildcard, a writable interpreter
  path, a `PYTHONPATH`/`PYTHONSTARTUP` reachable through `env_keep`) converts to
  arbitrary code execution *as the signer uid*, i.e. as the key holder. Note
  `.venv/bin/python` sits in the repo tree and is agent-writable today —
  **a sudoers rule naming an agent-writable interpreter is a direct
  privilege-escalation path.** This is a concrete finding, and it is exactly the
  E-1 argument-policy weakness the spec already names as unsound-by-pattern.
- Residual to record: *"key confidentiality now rests on sudoers argument
  scoping and on the immutability of the interpreter path it names — a pattern
  deny, which E-1 states is not sound."*

### If 2C (launchd)

- No sudoers rule, no setuid. New surface is the **plist and its referenced
  interpreter**: whoever can write the plist, or the `.venv/bin/python` it
  points at, controls a process running as the key holder. The plist lives
  outside the repo (`~/Library/LaunchAgents/`), which helps; `.venv/` is inside
  it, which does not.
- Residual to record: *"the signer's integrity now depends on the plist and the
  interpreter/venv it references being unwritable by the agent uid — neither is
  covered by the current ENFORCEMENT_PATHS set."*
- Second new surface: **a standing listener** replaces a session-scoped one
  (Second-Order third-order effect above).

### If 3B (IPC)

- The verify endpoint is a **local oracle reachable by the agent uid.** Key
  bytes are protected; key *use* is exposed. Must be designed so it can only
  answer "is this token valid for this exact content hash," never mint, never
  leak, and not serve as a probing surface.
- **Availability becomes a security dependency:** listener down = all Tier-3
  writes refused. Correct direction, real sharp edge.

### If 3C (Ed25519)

- New residual is a **recorded third-party dependency in the enforcement core**,
  inside the S-2 trusted surface, contrary to the current stdlib-only rationale.
  Smallest *conceptual* residual; a real supply-chain one.
- Private-key handling/rotation becomes a new operational concern.

### Cross-cutting residual (applies to ALL options — the honest floor)

Uid separation for the signer is **worthless while the framework runs uncaged
by default**, in this precise sense: uncaged, opencode runs as the operator's
uid, and the *operator's* uid can `sudo`, `chown`, `launchctl unload`, or edit
the plist/sudoers. An agent with bash at the operator's uid inherits all of
that. So — stated plainly, since the delegation asks for exactly this —

> **Signer-uid separation is a control that binds meaningfully only in CAGED
> mode.** Uncaged, it raises the cost of key access from "read a file" to
> "invoke the operator's own privilege" — a real but modest narrowing, not
> isolation. Any record of this work must say so; the F-4 analysis shows the
> O-3(b) framing's implication that it delivers uncaged value must be qualified,
> not inherited.

**Framework used (Fork 4):** Pre-Mortem, applied per-option above (risk
assessment; the auto-selection table's "Risk assessment" row).
**Bias check:** ⚠️ **Availability Heuristic** — the sudoers risk is vivid and
easy to recall, so it may be overweighted relative to the plist/venv-writability
risk, which is structurally similar and less memorable. Both are recorded above
at equal prominence deliberately. No other detector triggered.

---

## Selected Approach

**PARTIALLY SELECTED — see `## Converged (partial)` for the authoritative record.**

Settled (operator, direct conversation with orchestrator, this session):

- **Fork 3 end-state: 3C — Ed25519 asymmetric signing** (Decision 2), matching
  this brief's own advisory recommendation. 3A and 3B are rejected as the
  end-state.
- **The `cryptography`/asymmetric-signing dependency is accepted** into the
  otherwise stdlib-only enforcement core as a **narrow, named exception** scoped
  to Ed25519 sign/verify for the approval token (Decision 3) — a consequence of
  choosing 3C, requiring Tier-3 amendments only the operator can make.
- **F-1's remedy is SPLIT OUT** of this brief and tracked elsewhere (Decision 1)
  — an operator-directed split of work, not a design selection, and explicitly
  not an adoption of 3A.

Still unselected: **Fork 1 (provisioning)**, **Fork 2 (launch mechanism)**, the
**2C spike authorization**, the **Fork 4 caged-mode-only honesty statement**, and
the **armed-pipeline-collision scope ruling** — items 4–8. Those remain material
design decisions returned to the orchestrator for the operator to decide, and are
deliberately left unfilled here; filling them from my own recommendations would
be self-attested convergence — the exact failure the gate exists to prevent.

---

## Items requiring the operator's direct convergence

**Items 1–3 are CONVERGED** (see `## Converged (partial)`); they are retained
below, struck through, for traceability. **Items 4–8 remain OPEN and
unresolved** — they are the agenda for the next convergence round.

1. ~~**Is F-1 accepted as a present, urgent defect, and split out?**~~
   **RESOLVED (Decision 1): YES — split out, tracked elsewhere, not this
   brief's concern.** Operator-directed split of work, not a design choice;
   explicitly not an adoption of 3A.
2. ~~**Fork 3 first, target end-state: 3A-narrow, 3B-IPC, or 3C-Ed25519?**~~
   **RESOLVED (Decision 2): 3C — Ed25519 asymmetric signing**, matching this
   brief's advisory recommendation (no divergence). 3B is no longer the fallback.
3. ~~**Will the operator accept a third-party crypto dependency
   (`cryptography`) in the stdlib-only enforcement core?**~~
   **RESOLVED (Decision 3): YES — accepted as a narrow, named exception** scoped
   to Ed25519 sign/verify for the approval token, implicitly settled as a
   consequence of Decision 2. Requires amending `runtime-and-deps.md` and the
   "G-3.1 reuse / `verify/marker.py` unchanged" commitment in
   `tier3-signed-approval.md` — both Tier-3 records, operator territory.

**— OPEN below this line (items 4–8): next convergence round —**

4. **[OPEN] Fork 2 launch mechanism: 2A `sudo -u`, 2C `launchd`, or 2D/3B IPC-shaped?**
   Note the matrix ranks the decision record's own `sudo -u` example third of
   four, and that a sudoers rule naming the agent-writable `.venv/bin/python` is
   a direct privilege-escalation path (§Fork 4). **Not settled by Decision 2 —
   the key primitive and the launch mechanism are separate questions. This item
   is the blocker on `gleipnir-plan`.**
5. **[OPEN] Fork 1 provisioning: extend `ansible/site.yml` (1A) or a parallel
   signer playbook (1B)?** Extending puts a green, idempotency-hardened,
   caged-mode-gating playbook in the blast radius. Independent of Decisions 1–3.
6. **[OPEN] Is a spike authorised before committing to 2C?** macOS `launchd`
   `UserName` behaviour with a non-login account and a repo-local `.venv`
   interpreter is asserted from documentation, **not** probed on this host
   (Dunning-Kruger flag, §Fork 2). Downstream of item 4.
7. **[OPEN] Is the cross-cutting honesty statement accepted** — that signer-uid
   separation binds meaningfully only in caged mode, and that the O-3(b)
   framing's implied uncaged value must be qualified rather than inherited?
   Not put to the operator; remains an unaccepted advisory claim.
8. **[OPEN] Scope ruling on the adjacent armed-pipeline collision:**
   `sequence-gate.ts` and `advance-hook.ts` hit the same caged key-read wall when
   armed (§F-1). In scope for this follow-on, or its own tracked item? **Not
   covered by the Decision-1 split**, which scoped the approval listener only —
   this collision currently has no home.

---

## Open Questions (for `gleipnir-plan`, after FULL convergence)

**Blocked: `gleipnir-plan` should not start from this brief yet** — items 4–8
above are unresolved, and item 4 (launch mechanism) gates the Launch-mechanism
row of §Scope Sketch.

- Exact signer account name/uid (must be a *different* free id from the agent
  account's; `s2-activation-control-proposal.md:38`'s "verify free first"
  instruction applies).
- Whether `request_approval` (the staging tool, which needs no key) stays an
  opencode-spawned MCP while the *listener* moves to launchd — a clean split
  that 2C makes natural, since the T-11 reverse-import scan already proves the
  staging path never touches the key.
- Whether `mcp_server.py`'s Decision-19 log-and-continue should be changed to
  fail loudly. It is what turns F-1 into a *silent* failure; a warning on a dead
  daemon thread is not an operator-visible signal.
- Whether the caged preflight should gain a positive assertion that the signer
  uid *can* read the key (today `boundary.py` only asserts the agent uid
  *cannot*) — the natural AC for this work, and the thing that would have caught
  F-1 mechanically.
- `sudo`'s `env_reset` handling for `GLEIPNIR_MARKER_KEY_FILE` if 2A is chosen
  (the trap already documented at `bin/gleipnir-launch:18-26` and
  `ansible/site.yml:403-412`).

---

## Scope Sketch

| Area | Files/Modules likely affected |
|---|---|
| Signer account provisioning | `ansible/signer.yml` (1B) or `ansible/site.yml` + `group_vars/all.yml` (1A); `ansible/tests/*` |
| Identity single-source | new `.gleipnir/signer-identity.env`, or extended `agent-identity.env` |
| Launch mechanism | `opencode.jsonc` `mcp."gleipnir-approval"` (2A); `~/Library/LaunchAgents/*.plist` + possibly `mcp_server.py` thread-start (2C) |
| Sudoers (2A only) | `/etc/sudoers.d/gleipnir-signer` — operator-only |
| Key perms | `.gleipnir/keys/marker.key` ownership/mode; `ansible` act-5 equivalent |
| Validators (3B/3C only) | `approval/__main__.py`, `approval/token.py`, `verify/marker.py`, `ledger/ratetable.py`, `preflight/bridge_recovery.py`, `.gleipnir/plugins/{sequence-gate,advance-hook}.ts` + golden fixtures |
| Preflight AC | `src/gleipnir/preflight/boundary.py` (signer-can-read assertion) |
| Tier-3 records (operator) | `decisions/tier3-signed-approval.md`, `decisions/runtime-and-deps.md` (3C), `decisions/go-caged-runbook.md`, new signer decision record |
| Docs/proposal | new `plans/signer-uid-separation-control-proposal.md` (tier3-coach shape) |

**Routing note for `gleipnir-plan`:** the touched-path set includes
`opencode.jsonc`, `.gleipnir/plugins/**`, `.gleipnir/keys/**` and
`ansible/**`/`*.yml` — so this is **not** prose/config-only-track eligible
(Axis-1 disqualifier `X`: standalone YAML, `bin/**`, `src/**`) and, even if it
were, Axis-2(a) routes it hardened. Full 8-stage pipeline, two-pass review, plus
the negative-check attestation with `attested_by ≠ author`.
