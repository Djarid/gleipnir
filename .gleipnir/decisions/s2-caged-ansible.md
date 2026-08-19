# Decision: S-2 caged-mode host setup is codified as an Ansible playbook

**Status:** durable Tier-3 decision record. Operator-converged this session
(brainstorm → converge gate). Supersedes the "operator hand-runs six shell acts
from a runbook" delivery of the S-2 caged-mode host setup; the six acts
themselves (their OS end-state) are unchanged and remain authoritatively
described in [`../plans/s2-activation-control-proposal.md`](../plans/s2-activation-control-proposal.md).

## Context / problem

The S-2 caged boundary (spec G-1) is applied by six host/OS acts — create a
dedicated agent uid/gid, write `agent-identity.env`, lay out ownership/group,
`chmod` the enforcement subtree OS-read-only, lock the G-3 key `mode 600`, and
install the `bin/gleipnir-launch` wrapper. Until now these were **hand-run shell
commands** an operator copy-pasted from a runbook. That delivery is fragile:

- **No idempotency / drift detection.** A half-applied or re-run sequence has no
  safe convergence; the operator cannot ask "is this box already correctly set
  up?" without eyeballing perms by hand.
- **Ordering hazards are load-bearing but implicit.** Acts (3)/(4) transiently
  loosen the G-3 key (recursive `a+rX` over `keys/`), and act (5) must re-tighten
  it to `600` *afterwards*. A hand-runner who stops between (4) and (5) leaves the
  key group/other-readable. (Observed this session.)
- **`sudo` env-stripping breaks the gate silently.** `sudo` uses `env_reset` and
  does not `env_keep` `GLEIPNIR_MARKER_KEY_FILE`, so the AC-4 preflight run under
  `sudo` sees "key absent" and REFUSEs even on a correctly-caged box — unless the
  var is passed explicitly. (Reproduced live this session; see
  [`operating-posture.md`](./operating-posture.md) and the `bin/gleipnir-launch`
  header comment.)
- **No verification built in.** Nothing failed the setup when the boundary did
  not actually close.

These are exactly the failure classes declarative configuration management
exists to remove.

## Decision

**Codify the six S-2 caged-mode host acts as an idempotent, re-runnable,
self-verifying Ansible playbook.** The playbook is the mechanised form of the
go-caged runbook's "Step 1 — OS-layer setup (run once)"; it does NOT replace the
runbook's operational surface (Steps 2–4, uncage, honesty label).

### Converged decisions (operator-converged this session)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Tool | **Ansible playbook** | Nix / nix-darwin module; standalone idempotent shell installer | Operator-converged. Neither nix nor ansible is currently installed and the operator manages this mac with Homebrew, so Nix's whole-system-declarative value is low for one agent account and the `/nix` + nix-darwin adoption cost is disproportionate. Ansible is closest to the existing acts, idempotent, has `--check` dry-run, models "apply + verify", and installs via brew/pipx. A shell installer was rejected as weaker than Ansible's module + assertion ecosystem for this. |
| D2 | Scope of automation | **Apply acts (1)–(5) + install the wrapper (act 6); run AC-4 as a FAILING assertion; caged ENTRY stays an explicit operator act** | Full automation incl. auto-relaunch caged; setup-only with no AC-4 assertion | Operator-converged. The playbook installs the *capability* and asserts the boundary genuinely CLOSED (fails the run otherwise), but **entering a caged session (`sudo bin/gleipnir-launch`) remains a separate, explicit, observed operator act** — preserving the `operating-posture.md` honesty invariant (the operator always knows when they go caged; caged entry is never a side effect of running setup). |
| D3 | Test fidelity | **All three test layers, incl. layer-3 fixture-tree idempotency** — (1) static/syntax/lint + grep-asserts on the load-bearing invariants; (2) `--check` dry-run against a fake `.gleipnir/`-shaped fixture tree; (3) real `chmod` on a DISPOSABLE fixture tree, run twice, assert zero changes on the second run + the AC-4-fail path (wrong key mode → REFUSE → run fails) | Layers 1–2 only (no real chmod); layer 1 only (static) | Operator-converged (T1, surfaced by the planner, not baked in). Layer 3 is the ONLY layer that actually verifies the core Design Intent (idempotency) — `--check` alone asserts "run-twice = 0 changes" only in theory. The genuine caged-CLOSED AC-4 pass stays operator-run (uid 510 cannot be created in CI); CI covers everything up to that. Small disposable-fixture harness accepted as the cost of genuinely proving idempotency. |
| D4 | Test EXECUTION timing (toolchain gap) | **Author the playbook + the D3 3-layer test harness now; the tests run for the FIRST time once Ansible is installed — authored-but-not-yet-executed, honestly labelled** | Install Ansible on the host first and run tests this session; build an `[profile.ansible]` sandbox image first and run in-container | Operator-converged. Ansible (`ansible`/`ansible-playbook`/`ansible-lint`) is NOT installed on this box and the S-2 sandbox has NO Ansible profile (only python/node/broker), so the D3 harness CANNOT execute this session. Rather than block on a host-dependency install or a new hardened sandbox image, the harness is authored test-first and carries an explicit **"tests authored, not yet executed — requires Ansible install (brew/pipx) or an `[profile.ansible]` sandbox image"** honesty label (same shape as the framework's "authored, not yet closed" guard labels). First execution + genuine-green is a tracked follow-up (D4-FU), NOT a claim this session. This preserves test-first authoring while never asserting an unrun test passed (L-C8 discipline). |

### Binding constraints (inherited; the plan and playbook MUST honour these)

1. **Six acts are authoritative in `../plans/s2-activation-control-proposal.md`;
   the 8 enforcement paths are authoritative in `src/gleipnir/preflight/boundary.py`
   (the `ENFORCEMENT_PATHS` LOCKED set).** The playbook mechanises them, it does
   not re-author or "invent" the set. `plugins/` tolerates absence.
2. **Task ordering:** the key-`600` task (act 5) MUST run *after* the recursive
   enforcement-subtree `a+rX` task (act 4), so the recurse does not leave the key
   loosened. Ansible's deterministic top-down ordering makes this a sequencing
   requirement, not a handler.
3. **Key-600 is a permanent floor in BOTH modes** (`operating-posture.md`) —
   never relaxed by any uncage/teardown path; the key task is unconditional.
4. **The AC-4 assert task MUST set `GLEIPNIR_MARKER_KEY_FILE` explicitly** on the
   task environment (Ansible `environment:` survives `become`), because `sudo`
   strips it. Assert `rc == 0` under `--mode caged` (only `Verdict.CLOSED` yields
   0 in that mode; not-closed is REFUSE/exit 1).
5. **macOS user creation is the one act that is not a clean Ansible module.**
   `ansible.builtin.user` on Darwin is unreliable for a non-login service account
   (needs a password, incomplete dscl record, cross-version drift; no
   `sysadminctl` wrapper in `community.general`). Model act (1) as `command:
   sysadminctl`/`dscl` with a query-then-`when:` idempotency guard (there is no
   `creates` file for a dscl account).
6. **The playbook is out-of-framework OPERATOR tooling** (same class as `bin/`),
   run by the trusted principal under `sudo`/`become`. It is **never** run by an
   in-framework agent and **never** lives under `.gleipnir/` (which is the very
   subtree it hardens). Home: a repo-root `ansible/` directory.
7. **Caged entry stays explicit (D2).** The playbook never enters the cage or
   auto-declares caged; the authoritative caged signal is only ever the AC-4
   preflight verdict (`closed` + empty reasons + exit 0), never playbook success.

## Routing

The plan for this work routes to the **full 8-stage hardened pipeline**
(`brainstorm → plan → spec-review → test → code → quality → git → gate`): a
standalone Ansible `*.yml` is in Axis-1 disqualifier set `X` ("any standalone
`**/*.yml`/`**/*.yaml`" — executed YAML, disqualified safe-side), so the
prose/light track is unavailable regardless of documentation weight. Cognition
Gate-1 routes to **case (ii) executable-but-non-OOP** → DRY + Design Intent
required; SOLID/SRP attested `N/A — no object/function structure`.

## Consequences

- **Relationship to the runbook:** `go-caged-runbook.md` Step 1 becomes "run the
  Ansible playbook" (the runbook prose should be updated to point at it — a
  follow-up, not this record). Steps 2–4, uncage, and the honesty label remain
  the operator-operational surface the playbook does not touch.
- **New dependency:** Ansible must be installed (brew/pipx) to run the playbook.
  This is operator tooling, outside the stdlib-only enforcement-core constraint
  (`runtime-and-deps.md`) — the enforcement core is unchanged; Ansible is a
  host-provisioning tool the operator runs, not a framework runtime dependency.
- **Testability:** the playbook carries a `--check` dry-run path and a verify
  play; the AC-4 assertion converts "we assume it closed" into "the run fails if
  it did not."

## Provenance

Operator-converged this session via the orchestrator's `question` gate (tool =
Ansible; scope = acts 1–5 + wrapper install + AC-4-as-failing-assert, caged entry
stays operator-gated). Grounded by an explore-agent recon of the six acts, the
preflight exit contract, the sudo env-strip issue, and the routing determination.
The plan implementing this decision is authored separately by `gleipnir-plan`
under the full hardened pipeline.
