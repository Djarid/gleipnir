# Decision: signer launch mechanism — platform-independent contract, and per-OS spike boundary

**Status:** decided (this session). Durable Tier-3 decision record. Captures the
**platform-independent** part of the Plan A signer work (the OS-supervisor-launched
non-login signer principal) so it survives the disposable plan, records the
**two platforms spiked with real evidence** (arm64 macOS + Debian 12 x64), and
draws the explicit boundary that **each OS family needs its own spike** before a
build on it. Authored by the operator via the escape hatch (Tier-3, build mode),
per the `pi-replatform-open-q1.md` precedent (no roster subagent writes
`decisions/`).

Derivation: `../plans/signer-uid-separation-plan-a-launchd-spike.md` (Plan A, the
macOS launchd spike) and `../plans/signer-uid-separation-plan-a-spike-report.md`
(the macOS spike report), plus a real Linux/systemd mechanism-only spike run on
`charon.angler-pike.ts.net` (Debian 12.15 x86_64) this session.

## The platform-independent signer contract (OS-agnostic requirements)

Independent of any OS, the signer mechanism must satisfy these — this is the
durable requirement-shape (the "what", not the "how"):

1. **Separate principal.** The signer runs under a *dedicated, non-login*
   OS identity (uid on POSIX; SID/service account on Windows), distinct from
   both the agent identity and the operator's own identity.
2. **OS-supervisor-launched, not agent-child.** The signer process is started
   by the operating system's service supervisor (launchd / systemd / Windows
   SCM), never as a child of the agent process — so the agent uid cannot be its
   parent, inherit its descriptors, or trivially impersonate it.
3. **Key readable only by the signer principal.** The signing key is owned by
   and readable only by the signer identity (mode 0600 owner-only on POSIX; ACL
   to the service SID on Windows). The agent uid cannot read it.
4. **Environment delivered by the supervisor, not inherited from a shell.**
   The key path (and any config) reaches the process only via the supervisor's
   own declared-environment channel; the launching shell's environment is NOT
   inherited. (Verified true on BOTH launchd and systemd — see below.)
5. **No dependency on stdio staying open.** The service must remain alive and
   functional when its stdin is `/dev/null` / closed. A stdio-transport server
   that blocks on stdin will receive EOF immediately under an OS supervisor and
   exit. (This is the load-bearing cross-platform finding — see below.)

## Platforms spiked (with real evidence, not inference)

### arm64 macOS (launchd) — Plan A, tested this session

- Dedicated non-login signer via `dscl`/`sysadminctl`, uid 511, `/usr/bin/false`,
  `/var/empty`.
- **Arm A (gui/501 LaunchAgent): NEGATIVE** — launchd's gui domain refuses to run
  a foreign non-login uid (`last exit code = 78 EX_CONFIG`). The gui domain is
  bound to the logged-in user.
- **Arm B (system LaunchDaemon): POSITIVE** — `UserName` honored, ran as uid 511,
  executed the repo `.venv` interpreter, read the signer-owned key, bound
  `127.0.0.1:8765`.
- **Env (J6):** plist-declared `EnvironmentVariables` visible; shell-only var NOT
  inherited.
- **Stdio finding:** the real `gleipnir.approval.mcp_server` under launchd was
  observed to exit 0 with no bind observed in the poll window and no fatal log
  line — classified **(f) INCONCLUSIVE** in the spike (no cause was
  instrumented or proven). The **leading, source-supported hypothesis** is that
  `mcp.run(transport="stdio")` reads EOF on launchd's `/dev/null` stdin and
  returns before the daemon listener thread binds; this is plausible and
  consistent with the observations but was **not established** as the cause.
  Regardless of mechanism, `/dev/null` stdin under an OS supervisor is an
  environment fact, so contract requirement #5 (below) holds on that fact alone,
  not on this hypothesis being confirmed.
- Full detail: `../plans/signer-uid-separation-plan-a-spike-report.md`.

### Debian 12 x64 (systemd) — mechanism-only spike, `charon.angler-pike.ts.net`, this session

Debian 12.15, x86_64, kernel 6.1, systemd 252, python3 3.11.2. A **mechanism-only**
spike (the repo/module/venv are not on that host, so the real module was not run —
by design; this tested the *launch mechanism*, the true analog of macOS stage-1 +
the portable finding). Fully torn down afterward (account, group, unit, scratch
tree all removed; verified clean).

- Dedicated non-login signer via `useradd --system`, uid/gid 811,
  `/usr/sbin/nologin`, `/nonexistent` home (contract #1: PASS).
- **systemd `User=` in an installed system unit: POSITIVE** — `Result=success`,
  ran as uid 811, read the signer-owned key, bound `127.0.0.1:8765`. Also
  confirmed via a transient `systemd-run --uid` unit. (contract #2/#3: PASS.)
- **Env:** `Environment=`-declared var visible; a shell-only var NOT inherited —
  systemd does not inherit the caller's shell env, same as launchd (contract #4:
  PASS).
- **Stdio ENVIRONMENT FACT confirmed on Linux (directly observed):** under
  systemd's default `StandardInput=null`, a `sys.stdin.read()` returns EOF
  (len 0) immediately — so a stdio-transport server that blocks on stdin would
  receive EOF and exit. This is the systemd analog of launchd's `/dev/null`
  stdin. **Scope of what is proven vs hypothesised (contract #5):** the
  *environment fact* — an OS supervisor gives the service a closed/EOF stdin —
  is directly observed on **both** launchd (`/dev/null`) and systemd
  (`StandardInput=null`). What was NOT proven on either is that the real
  `gleipnir.approval.mcp_server` exits *because* of that EOF before binding:
  on macOS that was the leading hypothesis for an INCONCLUSIVE stage-2 (never
  instrumented), and on Linux the real module was not run at all
  (mechanism-only spike). Contract #5 rests on the confirmed environment fact,
  which holds on both supervisors regardless of the module-causation
  hypothesis — NOT on a claim that the module's EOF-exit was demonstrated.
- **Notably simpler than macOS:** systemd has no gui/system domain split, so
  there is no arm-A-style `EX_CONFIG` refusal — `User=` in a system unit just
  works. The macOS "must use the system LaunchDaemon, not the gui LaunchAgent"
  condition has no Linux analog.

## Decision

1. **The five-point contract above is the durable, OS-independent specification
   of the signer launch mechanism.** Any per-OS build must satisfy all five; the
   contract is the review rubric.

2. **Do NOT write speculative per-OS build specs ahead of a spike on that OS.**
   Plan A's founding rationale (Decision 6 / the Dunning-Kruger flag) is that a
   launch mechanism "asserted from docs and never probed" is untrustworthy — the
   macOS spike found two things docs would not have told you (the gui-domain
   `EX_CONFIG` refusal; and that the real module's stage-2 run under launchd was
   INCONCLUSIVE — exited 0 with no observed bind — surfacing the closed-stdin
   environment fact behind contract #5). A Linux or Windows build spec
   written from documentation alone would carry the exact unverified-assertion
   risk Plan A exists to eliminate. Per-OS build detail is written FROM that OS's
   spike, not before it.

3. **The three target OS families share the contract, but share ZERO
   implementation artifacts.** macOS (launchd plist + `dscl`/`sysadminctl`),
   Linux (systemd unit + `useradd --system`/`systemd-sysusers`), and Windows
   (SCM service + `New-LocalUser`/gMSA/SID) are distinct designs, not ports of
   one another. There is no "portable core" module to build once — only the
   contract to satisfy three times.

4. **Per-OS spike boundary (explicit, so macOS evidence is never mistaken for
   cross-platform evidence):**
   - **arm64 macOS:** spiked, POSITIVE (system LaunchDaemon), real module tested
     (Plan A).
   - **x64 macOS:** NOT spiked. Very likely identical to arm64 (launchd
     domain/uid/env semantics are architecture-independent; only the interpreter
     arch differs, which the mechanism does not depend on) — but this is
     inference, not evidence. A confirmatory spike is cheap if an x64 Mac is ever
     a target.
   - **Linux/systemd:** launch mechanism spiked POSITIVE on Debian 12 x64
     (charon) this session; the **real module** was NOT run there (mechanism-only).
     A full-fidelity Linux build still needs: the repo+interpreter present on the
     target, the real module run under the unit, and a non-stdio run mode
     (contract #5).
   - **Windows/SCM:** NOT spiked; architecturally alien (no POSIX uid, no
     launchd/systemd, service-account/SID model). Needs its own spike and its own
     design before any build.

## Consequences / linkage

- **Plan B (the Ed25519 migration + standing signer service) inherits contract
  requirement #5 as a hard design input on every OS:** the standing signer must
  run in a non-stdio / keepalive mode (e.g. a non-stdio server entrypoint, plus
  `KeepAlive` on macOS / an appropriate `Restart=`/`Type=` on systemd). This is
  now proven necessary on both launchd and systemd.
- **macOS-specific conditions do NOT transfer:** "system LaunchDaemon not gui
  LaunchAgent" and "declare the key path in the plist" are launchd artifacts.
  Their Linux analog is "a system unit with `User=` and `Environment=`"; the
  Windows analog is undetermined (needs the Windows spike).
- **This record does not commit Gleipnir to multi-OS support.** The framework's
  current documented posture is single-host macOS (`s2-caged-ansible.md`,
  `go-caged-runbook.md`, Plan A `:246`). Whether Linux/Windows become supported
  targets is a separate scope decision (plausibly surfacing via the pi.dev
  replatform's eventual deployment surface) and belongs at a brainstorm
  convergence gate, not here. This record only preserves the portable knowledge
  and the evidence gathered, and fixes the boundary so future work starts from
  facts.

## Provenance

macOS evidence: Plan A Assemble steps 0–12 executed on the operator's arm64 Mac
this session (build mode), recorded in
`../plans/signer-uid-separation-plan-a-spike-report.md`. Linux evidence: a
mechanism-only systemd spike run over Tailscale SSH on `charon.angler-pike.ts.net`
(Debian 12.15 x86_64) this session, created and fully torn down (dedicated system
account uid 811 + installed system unit + transient `systemd-run` unit + scratch
tree; all removed and verified clean afterward). Operator-directed ("do 1 AND
then build it against charon … a debian 12 x64 system"). No real signing key was
touched on either host; both spikes used throwaway `/dev/urandom` scratch keys.

---

## Addendum: provisioning-lifecycle provenance semantics + spike-grade commit (operator-converged)

Two operator-converged decisions from Plan A's `quality`-remediation, recorded
here durably (the implementation comments in `ansible/signer.yml` are not the
authoritative record):

### 1. `*_CREATED` flags mean "provisioning-lifecycle membership", not "created by this invocation"

Plan A's J22 (append-only, fail-on-disagreement provenance) and J11 (a
`--skip-tags spike_scratch` rerun must be `changed=0`) were in tension: if a
`*_CREATED` flag meant "created by THIS invocation", then after the first
provisioning run records `ACCOUNT_CREATED=true`, a normal rerun (account now
present) would compute `false` and a strict disagreement-check would FAIL the
rerun — contradicting J11.

**Resolution (converged):** a `created.env` `*_CREATED=true` flag records that the
object **belongs to the signer provisioning lifecycle** — i.e. it is present as a
result of provisioning and is therefore teardown's to remove — **NOT** that this
particular invocation created it. Consequences:
- A rerun that finds the object already present **confirms** the recorded flag
  (no re-creation, no disagreement-fail) → `changed=0` (J11 satisfied).
- Teardown still removes exactly the lifecycle-provisioned objects (J22's intent
  — teardown correctness — preserved).
- A genuine **contradiction** worth failing on is: the manifest records an object
  as provisioned (`=true`) but the object is now **absent** — a real
  inconsistency (something removed a lifecycle object out of band).

This **amends the interpretation** of J9/J22/SC-11 and the "run-created-only"
wording at `plans/signer-uid-separation-plan-a-launchd-spike.md:64,879`. The plan
is Tier-0/disposable; this decision record is the durable home. (A known
limitation remains that the spike playbooks' `account_provisioned`/
`group_provisioned` expressions do not yet *measure* real post-provisioning
presence — see the spike report's "Known limitations" §; Plan B implements the
semantics correctly.)

### 2. Plan A's `ansible/` playbooks are committed SPIKE-GRADE; Plan B authors production account/teardown logic

Plan A's deliverable is the **launchd feasibility verdict** (2C viable, macOS +
Linux, recorded from real on-box evidence). The `ansible/` playbooks
(`signer.yml`, `signer-teardown.yml`, `tasks/create-service-account.yml`) and the
`signer-static.sh` arbiter + fixtures are the **scaffolding** that made the spike
executable. They were hardened across three adversarial `quality` rounds
(load-bearing correctness fixed and runtime-proven) but a third round surfaced
progressively marginal edge-cases. **Operator decision:** commit them spike-grade
with the residual edge-cases recorded as known limitations (spike report), and
have **Plan B** author production-grade account-management and teardown logic from
scratch — informed by all of this — rather than asymptotically polish throwaway
spike scaffolding. This is a deliberate scope boundary (spike vs production
library), not an oversight; the known-limitations list is the handoff to Plan B.

### 3. Latent agent-account gid drift corrected (incidental real finding)

Plan A's corrected (exact, non-substring) account guard exposed that the real
`gleipniragent` **user** had `PrimaryGroupID=20` (staff), not the intended `510`
(`agent-identity.env`'s `GLEIPNIR_AGENT_GID=510`, and a `gleipniragent` group
with gid 510 exists). The old broken substring-guard had never caught this. The
operator corrected the account (`dscl . -create /Users/gleipniragent
PrimaryGroupID 510`) so it now matches the `site.yml` creation contract
(`sysadminctl -addUser ... -GID {{ agent_gid }}`). Likely root cause: the BC-5
"`sysadminctl` unreliable on Darwin for non-login service accounts" behaviour the
plan already documents — `-GID` at creation time did not reliably set the primary
group. Recorded so it is not mistaken for a spike artifact.
