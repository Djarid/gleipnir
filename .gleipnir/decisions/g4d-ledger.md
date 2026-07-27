# Decision: G-4d metrics ledger — first slice (honesty skeleton + revert metric)

**Status:** decided and implemented. Durable decision record (Tier-3,
operator-authored). Converged via the orchestrator-surfaced decision gate
(brainstorm Decision Analysis → operator convergence). Plan of record:
`../plans/g4d-ledger-first-slice.md` (spec-review APPROVED + 3 minors folded;
quality-gated, 2 blockers fixed).

## Scope (first slice only)

Realises the minimal, HONEST first slice of the G-4d metrics ledger: the
deterministic event→metric **reduction skeleton** + the **measured/estimated
honesty type** + the **rate-table home/loader/digest** + **reconciliation**,
with exactly **one real metric** wired — the revert-derived baseline. The
economic chain (cost, uplift) and the other measured metrics are **deferred as
named "bus-emission gaps"**, never fabricated numbers.

The governing principle (spec G-4d): *"an unlabelled estimate is a vanity
metric, more dangerous than a bad test because it flatters the system."* This
slice builds the honest structure and **refuses to emit numbers whose inputs do
not yet exist.**

## Converged decisions (operator-decided)

- **D1 — First-slice boundary = the deterministic skeleton + ONE real metric.**
  `reduce(session_log_path) -> LedgerReport` reads the bus JSONL (via the bus's
  typed `Event.from_json_line` — never hand-parsed, never string-matched) and
  computes the **revert-derived baseline** (revert count; escalation rate). This
  is the spec's own named G-3.2 system-state baseline ("how often work reached a
  terminal and had to be undone"). Every other metric — iterations, retries,
  token usage, cost, effort attribution, efficiency, uplift — is an explicit
  `Gap`, never a fabricated zero. Reverts are NOT conflated with "retries" (a
  distinct measured metric, deferred).
- **D2 — Rate table: home + loader + digest now, cost NUMBER deferred.** The
  rate table's permanent home is Tier-3 POLICY (operator-authored, agent-deny),
  and its loader verifies a **G-3.1 keyed HMAC digest** (reusing `verify.marker`
  primitives — `load_key` + `hmac.compare_digest`, NOT `Marker.validate`'s
  freshness pipeline, which is the wrong semantic for a static config file),
  **fail-closed** on missing file / digest mismatch / key unavailable / corrupt
  bytes → cost stays a `Gap` with a precise reason, never a guessed rate. **Cost
  is a `Gap` UNCONDITIONALLY this slice — even when the digest verifies** —
  because publishing a cost number before the S-2 mount makes the rate table
  structurally agent-unwritable would assert an unforgeability guarantee that is
  not yet true. Cost lands when S-2 lands.
- **D3 — Measured-vs-estimated honesty type.** `Measured`, `Estimated`, and
  `Gap` are three genuinely distinct frozen dataclasses (not a shared struct +
  flag). `Gap` has no `value` field at all, so it cannot be read as, or
  deserialize into, `Measured(0)`. `Estimated` construction is **fail-closed**:
  raises `LedgerError` without a `CalibrationBand`, and — when
  `kind is EstimateKind.UPLIFT` — without a versioned `NotionalHumanRate`. The
  uplift precondition is gated on the **typed `EstimateKind` enum identity**, NOT
  a `name == "uplift"` string branch (an AST test proves no such string branch
  exists). Built and tested now even though no estimate is emitted this slice.
- **D4 — Reconciliation = re-derive + explicit gap-report.** `reconcile()`
  independently re-derives the revert count, escalation count, AND escalation
  rate from the raw JSONL (a separate function body, via the same typed read
  door) and raises `LedgerError` on any divergence from the report; it emits an
  explicit gap-report enumerating every non-revert metric as a `Gap`.

## Robustness posture (from the quality gate)

Telemetry reads are **robust** (never crash on Tier-1 corruption); the rate
table is **fail-closed** (contract). Logs are read as **bytes and decoded
per-line**, so an encoding-corrupt line (e.g. a process killed mid-write across
a multibyte boundary) is folded into an `unreadable` count like a malformed JSON
line — it must NOT blind the ledger to the valid lines around it. Empty/missing
log → all gaps (+ a real `Measured(0)` revert count), not an error. The
rate-table loader never raises into the caller.

The escalation-rate **zero-denominator convention**: when `revert_count == 0`,
`escalation_rate` is `Measured(value=None, denominator=0)` — the *vacuous
sentinel*, never a misleading `0.0`. When reverts exist but none escalated, it
is a genuine `Measured(value=0.0, denominator>0)`.

## Operator hand-offs (Tier-3, NOT authored by the implementing agent)

- **The rate-table file + its approved keyed digest** must be placed by the
  operator (proposed under `.gleipnir/keys/`). Until then (and until S-2), cost
  is a `Gap` — which is the correct, honest state. The ledger code (agent-
  writable `src/`) was built without ever creating these Tier-3 files; tests use
  their own fixtures under tmp.

## Verification

`src/gleipnir/ledger/{metric,reduce,ratetable,reconcile}.py`, in-sandbox: 291
passed, 97% coverage (line+branch). Anti-vanity guarantees covered by real
type/instance assertions (Gap-is-not-Measured(0), Estimated-raises-uncalibrated,
no-cost-number-even-on-valid-digest, typed-read-no-prose-parse, zero-denominator
sentinel). stdlib-only (hashlib/hmac via `verify.marker`). Quality-gated (2
crash-on-corruption blockers fixed; 3 minors closed).

## Known not-yet-closed / seams

- **Cost + the economic chain** — gated on the S-2 mount (rate-table
  unforgeability) AND token provenance on the bus. Named gaps until then.
- **Token usage, effort attribution, efficiency, iterations, retries** — need
  new bus event kinds (terminal events, token-provenance ingress). Named gaps;
  the reduction skeleton is the plug-in point.
- **Uplift** — the honesty type is built and fail-closed, but no uplift is
  emitted; needs the calibration machinery + a counterfactual estimate source.
- **Cross-source reconciliation** — this slice reconciles self-consistently
  (same bus JSONL, same typed read path); the spec's full Conformance [D] form
  (reconcile against runtime usage logs + rate table) is a seam for when those
  inputs land.
