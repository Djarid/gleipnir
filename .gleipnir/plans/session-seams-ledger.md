# Session seams ledger (Tier-0, disposable)

**Tier-0 TEMPORARY session artifact — disposable.** This is a convenience
snapshot so the open-seams list is not lost between sessions. It is NOT
authoritative: the authoritative homes are the individual `../decisions/`
records + the spec's Part D E-seams. When a seam closes, update its decision
record; this file may be deleted at any time.

## Tracked open seams

- **Node profile real-run:** needs an operator-built digest-pinned node
  Containerfile + image; until then node is dispatch-proven only.
- **Dogfood node cross-language block** (`tests/test_sequence_gate.mjs`):
  committed but NOT yet agent-run (no roster agent has a node grant; sandbox had
  no node profile image). Statically sound; fixture MAC confirmed Python-side.
- **S-2 activation (operator):** dedicated agent uid + chmod the enforcement
  subtree OS-ro + place the G-3 key OS-unreadable + run `bin/gleipnir-preflight`
  before sessions. Code built (commit `5cd329c`); activation is an operator
  action.
- **S-2 mount + terminal closure + S-3 preflight wiring:** the structural
  boundary that makes `.gleipnir/` unwritable (vs today's preflight-verified
  OS-perms floor).
- **G-4 remainder:** observer, novelty triage (G-4c), TS-side emit;
  cost/economic-chain in the ledger (needs the S-2 rate-table + token provenance
  on the bus).
- **E-1** broker argument policy; **E-2** platform-webhook receiver; **E-3**
  novelty-triage signal quality.
- **Engine hybrid-C per-stage escalation:** deferred; global revert budget is the
  current trigger.
- **Live TS `tool.execute.after` advance hook** (armed-run dogfood seam 7);
  real-CI attestation feeding `attempt_gate` / G-3.2 sourcing (seam 8).
- **Rust/C/C++ sandbox profiles** + the offline-deps fetch-then-seal decision.
- **`bin/gleipnir-sandbox lint`** fails writing `__pycache__` under the ro `src`
  mount (pre-existing, all files).
- **git-ops allowlist** lacks `git diff`/`git log` (read-only inspection gap).
- **Pending durable-decision/lesson persistence** is now done (this pass).
