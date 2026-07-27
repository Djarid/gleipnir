# Decision: S-2 / G-1 closure — first slice (fail-closed boundary preflight)

**Status:** decided and implemented. Durable decision record (Tier-3, operator-
authored via the built-in escape hatch). Converged via the orchestrator-
surfaced decision gate. Plan of record: `../plans/s2-g1-closure-first-slice.md`
(spec-review APPROVED, 2 rounds; quality-gated, 3 rounds). Implementing commits:
`5cd329c` + `356eb05` (conftest follow-up). Architecture frame:
`substrate-design-pass.md` (Option B core / A-where-containers-unavailable).

## The central reframe

The resolved architecture named "Option B read-only mount," but that assumed
the agent runs INSIDE the container. On the v0.1 host-run model, opencode runs
on the HOST — the existing container is only a build/test EXECUTOR (T-6 blast
radius), not the agent's execution home. A host-run agent is exactly the
condition under which the resolved decision sanctions "Option A where containers
are unavailable." So the v0.1 close is the **relocate-and-deny hybrid**, not
containerising the session.

## Converged decisions (operator-decided via the orchestrator; LOCKED)

- **D1 — Relocate-and-deny hybrid.** The enforcement subset of `.gleipnir/` is
  made OS-read-only to the agent uid + covered by the agent permission-map deny,
  verified by an out-of-framework preflight. B-literal (containerise the whole
  session) is deferred to the C-hardening tier.

- **CRUX — uid separation, verified by a fail-closed preflight.** The hybrid
  only truly closes G-1 if the agent process runs as a DIFFERENT OS uid than the
  owner of the enforcement files (else `chmod` is self-removable — a prose
  guard). Handled by a preflight that FAILS CLOSED: it behaviourally probes —
  attempts a write to each enforcement file, and a read of the key, AS the agent
  uid via a forked privilege drop (`setgroups([])` + `setgid` + `setuid`) with
  independent euid/uid/egid/gid read-back — and REFUSES to launch if any
  enforcement file is writable or the key readable. On a single-uid dev box with
  no real separation, the preflight fails closed: honest, no false "G-1 closed"
  claim. The drop and the write/read are separately classified
  (`DROP_FAILED` / `DROP_UNVERIFIED` / `WRITE_DENIED` / `WRITE_OK` /
  `PROBE_ERROR`); only `WRITE_DENIED` contributes a CLOSED signal, so a failed
  or unverified drop can never masquerade as "safely read-only."

- **D2 — config-load-path.** A single `OPENCODE_CONFIG_DIR` with per-subtree OS
  perms: enforcement subdirs OS-ro to the agent uid; non-enforcement authoring
  content stays writable. Symlink resolution is checked — a read-only
  enforcement file or a symlinked subdir whose resolved target escapes the ro
  subtree forces NOT_CLOSED. Directory entries are probed PER FILE (a read-only
  directory can still contain writable files — the permission maps G-1 protects).

- **Enforcement path set (Tier-3 POLICY):** `agents/*.md`, `stage-role-map.md`,
  `decisions/**`, `goals/**`, `keys/**` (key OS-UNREADABLE, not merely
  unwritable), `plugins/**` (tolerate-absent), `AGENTS.md`. The one justified
  narrowing: skill BODIES stay writable (methodology prose, not
  enforcement-bearing).

- **D3 — key/rate-table/toggles.** Live under the ro boundary; the key must be
  OS-unreadable to the agent uid (via the existing `GLEIPNIR_MARKER_KEY_FILE`,
  no marker code change). External secret-store is the C evolution, deferred.

- **D4 — preflight.** An OUT-OF-FRAMEWORK launch wrapper (`bin/gleipnir-
  preflight`, a thin shim), run as the owning principal BEFORE the session,
  fail-closed, NOT on any agent allowlist, and it does NOT check or restrict the
  operator's escape-hatch `/plan` `/build` agents (Part 0). The probe/decision
  LOGIC lives in `src/gleipnir/preflight/boundary.py` (pure + data — readable
  grants no power); the INVOCATION is out-of-framework. Exit codes: `0=CLOSED`,
  `1=REFUSE`, `2=PROCEED_UNCLOSED`. `os.access` is deliberately NOT used in the
  verdict (real-uid + root bypass make it a false-pass source); the verdict
  comes from an actually-attempted write/read after a verified drop.

- **Operator override.** A Part-0 operator-acknowledged marker (out of agent
  reach) can only escalate `NOT_CLOSED -> PROCEED_UNCLOSED` with an honest
  "G-1 NOT closed (dev-mode)" label; it can NEVER produce `CLOSED`.

- **D5 — first-slice boundary.** uid-separation handling + OS-ro/unreadable
  enforcement subset + the out-of-framework launch-wrapper preflight. DEFERRED:
  containerising the whole opencode session (B-literal -> C), the broker /
  credential isolation + E-1 argument policy (build-order step 4), the full
  plugins/hooks-registered + bus-reachable preflight checks (gated on those
  subsystems existing).

## Honesty labelling

This is an OS-perms FLOOR, not the terminal boundary. B-literal / C-tier
(containerised session, remote verifier, "root inside yields nothing") remain
the hardening direction. The floor is honest because it FAILS CLOSED rather
than claiming a closure it cannot prove.

## Verification

`src/gleipnir/preflight/boundary.py` + `bin/gleipnir-preflight` + tests,
in-sandbox: 379 passed, 11 skipped (hostonly real-perms tests skip under root —
root bypasses permission bits), 93% coverage. A cardinal false-CLOSED (directory
write-bit vs per-file content perms) and two residual variants (symlinked
subdir; swallowed `os.walk` error) were caught across three quality rounds and
fixed with real end-to-end proof (real-chmod hostonly + monkeypatched scan
failure).

## Pending operator activation

The CODE is built; ACTIVATION is an operator action, not an agent one:
1. Establish a dedicated agent OS uid distinct from the enforcement-file owner.
2. `chmod` the enforcement subtree OS-read-only to that uid, and place the G-3
   key OS-unreadable to it.
3. Run `bin/gleipnir-preflight` (as the owning principal) before each session,
   fail-closed.

Until then the preflight honestly reports NOT_CLOSED on a single-uid box.

## Known not-yet-closed / seams

- Containerised session (B-literal) + C-tier remote verifier — the hardening
  direction, deferred.
- Broker / credential isolation + E-1 argument policy — build-order step 4.
- Full preflight checklist (hooks-registered, bus-reachable) — gated on those
  subsystems.
- The S-3 preflight's own out-of-repo home for hardened deployments.
- `bin/gleipnir-sandbox lint` fails writing `__pycache__` under the read-only
  `src/` mount (pre-existing, affects all files, out of scope for this slice).
