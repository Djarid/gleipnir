# Decision: Bridge recovery path — `bridge-status` / `bridge-reset` (L-C19)

**Status:** DURABLE decision record (Tier-3 POLICY, operator-authored).
Persists beyond the disposable Tier-0 plan/brief. Records the converged
resolution of L-C19; the implementation lives in
`src/gleipnir/preflight/bridge_recovery.py` (+ dispatch in
`src/gleipnir/preflight/__main__.py`).

## The gap (L-C19)

The signed G-5 pipeline bridge (`.gleipnir/var/run/pipeline-state.json`) is a
fail-closed enforcement file: when armed (`GLEIPNIR_PIPELINE=on`), the
`sequence-gate.ts` hook aborts **every** `task` delegation if the bridge fails
MAC/freshness validation — and a bridge older than the 1-hour freshness window
is *by design* invalid. This occurred for real: a ~17-day-stale bridge would
fail-closed every delegation, and **no roster agent's permission grant covers
`.gleipnir/var/run/`** — so the operator had to `rm` the file out of band. A
fail-closed mechanism with no deliberate recovery path degenerates into
"permanently inaccessible until manual out-of-framework intervention," a worse
failure mode than the one the gate prevents.

## The decision (operator-converged)

**Option A subsuming C — clear-only, out-of-framework, operator-only.** Two
subcommands on the existing agent-unreachable `bin/gleipnir-preflight` CLI:

- **`bridge-status`** (read-only diagnostic): classifies the bridge as
  **healthy / stale / corrupt-or-tampered / absent**, prints `minted_at`, age,
  and the exact next command. Safe to run anytime; writes nothing.
- **`bridge-reset --confirm-clear`** (recovery): **deletes** the bridge
  (clear-only; **never re-mints** a state), refuses without the explicit flag,
  refuses under a non-operator uid when `GLEIPNIR_OPERATOR_UID` is set, and
  appends a provenance-bearing line to `.gleipnir/logs/bridge-recovery.log`.

**Rejected:** (B) a roster-role write-grant over the bridge — a G-2 regression
(lets the guarded population write the evidence the guard trusts); (D) TTL /
auto-clear-on-staleness — the fail-open the driver docstring explicitly forbids.

## Invariants this preserves

1. **No silent reset.** Clearing is only ever a deliberate, `--confirm-clear`,
   operator act. The tool never auto-clears on staleness/corruption. Re-minting
   a state is structurally absent (clear = delete only) — resurrecting a
   permissive state would be the fail-open `driver.py` forbids ("a fresh Driver
   at BRAINSTORM is never silently returned in place of an untrusted bridge").
2. **Never agent-invocable (pre-mortem #1).** Both subcommands refuse (exit 1)
   if the literal `gleipnir-preflight` appears in any `.gleipnir/agents/*.md` —
   a guard whose activation is validated by the population it guards is
   defeated. A companion permission-hardening change added
   `"src/gleipnir/preflight/**": deny` to `gleipnir-code.md`'s `edit` map so the
   tool's *own source* is also agent-unreachable (previously `edit:"*":allow`
   reached it — the false-premise defect spec-review caught).

## Honest status

**Cooperative-policy-until-S-2.** The operator-only / out-of-framework property
of the shim invocation is honoured by today's roster grants (`bin/gleipnir-preflight`
is in no allowlist) and, now, by the `src/gleipnir/preflight/**` edit-deny. The
uid refusal (`GLEIPNIR_OPERATOR_UID`) is opt-in: **no reliable in-process "am I
an agent" signal exists in this codebase**, so when the env var is unset the
tool WARNS rather than fabricating a check. The whole posture becomes
*structural* (rather than cooperative-policy) only when the S-2 boundary +
terminal closure land.

## Open (deferred, not decided here)

The 1-hour freshness window (`DEFAULT_MAX_AGE_SECONDS = 3600`) is unchanged and
imported, not re-decided — the incident (17-day-stale bridge) suggests it may be
worth revisiting whether 1 hour is the intended window, but that is out of this
decision's scope (brief Open Question #1).

## Provenance

Brief: `.gleipnir/plans/bridge-recovery-brainstorm.md` (Option A subsuming C,
clear-only; B/D rejected; WDM 438 vs 242/244 + pre-mortem). Plan:
`.gleipnir/plans/bridge-recovery.md` (spec-review APPROVED, 2 rounds). Applied
by the operator in build mode, this session.
