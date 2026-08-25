# Decision: pi.dev replatform Open-Q1 — delegation-isolation boundary (in-process vs process-isolated)

**Status:** decided (this session). Durable decision record. Resolves **Open-Q1**
of the pi.dev replatform (Approach B) for **Step S3** of the build order.
Authored by the operator via the escape hatch (Tier-3, build mode). Derivation:
`../plans/pi-dev-replatform-s3.md` (the S3 closure record) and
`../plans/pi-dev-replatform-s3-brainstorm.md` §D-S3-A (the converged design
brief). Convergence authority: the operator, via the orchestrator's `question`
tool (L-C6 — a subagent's `question` cannot reach the operator; the orchestrator
surfaced D-S3-A and the operator selected the resolution), matching the brief's
§D-S3-A recommendation with **no divergence**.

## The question (Open-Q1, verbatim from the roadmap)

Whether the pi-native delegation edge should be **in-process**
(`createAgentSession`, child session in the same address space as the parent
extension) or **process-isolated** (`runRpcMode` / `pi --mode rpc --no-session`,
a JSONL subprocess boundary). The build-order's [ASSUMPTION-2] provisionally
built S3 on the in-process assumption and flagged that this question "needs
operator convergence on Open-Q1 before S3 is *finalised* (it can start on the
in-process assumption)."

## Decision

**Open-Q1 is RESOLVED for S3 = in-process `createAgentSession`.** This is the
final delegation-isolation answer for S3; the S3 delegation edge is in-process
only and requires no RPC variant to close. There is no `runRpcMode` code in
`pi-package/src/**` (grep-confirmed, brief §F1), and none is required for S3 to
close.

### S6-conditional future-work item (TRACKED FUTURE WORK)

If the S6 sandbox/broker convergence (**Open-Q3**) requires process isolation
for any role, add a `runRpcMode` variant to the delegation edge **at S6** — this
is **additive, not a rebuild**, because:

- `delegate.ts` is SRP-scoped to construct/bound/run a child session and
  explicitly does **NOT** decide in-process-vs-RPC isolation (module header:
  "does NOT decide in-process-vs-RPC isolation — that is Open-Q1, revisited at
  S3/S6"); and
- `activeRole.ts`'s per-process stack model does not need to change under a move
  to `runRpcMode` (each process gets its own module instance; the stack model is
  isolation-agnostic).

The **trigger to revisit** Open-Q1 is the S6/Open-Q3 convergence; until then,
in-process is final for S3. This item is S6-conditional and is not built now
(deciding it now would decide a downstream-dependent question before its input —
the S6/Open-Q3 broker boundary — exists; see the brief's Second-Order analysis
and the L-C20 antipattern).

## Carried residuals (recorded as NON-DEFECTS)

These are inherited from S1/S2, are empirical/scope matters (not delegation-model
defects), and do **not** block S3's closure. Recorded here so the durable record
carries them, not just the disposable plan:

1. **Live-model-turn gap.** A real top-level orchestrator session, under a live
   model, emitting a real `delegate` call and running a real child model turn, is
   untested — because `createAgentSession`'s body reaches provider auth
   (`ModelRuntime.create` / `findInitialModel` against `~/.pi/agent`) that is
   unreachable under the sandbox's `--network=none` regime with no in-container
   provider credentials. This is a **sandbox/auth limitation, unclosable by
   delegation code**. Everything up to and including the real `tool_call`
   dispatch pipeline IS proven (AC-9-E2E). If ever wanted, closing this is an
   Open-Q1 / S-2 sandbox-regime (network/auth-in-sandbox) question, not a
   delegation-model one.
2. **Arg-level (`event.input`) enforcement.** Per-path/per-arg bounds (the E-1
   argument-policy seam) are **legitimately deferred to S7**. They are already
   recorded as `bounds` metadata in `roleTable.ts` per S2; S2/S3 enforce coarse
   tool-presence containment only. Pinning arg-level enforcement into S3 would
   expand the exit criterion (explicitly not done — D-S3-B convergence).

## Scope

This record resolves **Open-Q1 only.** It does not touch Open-Q2 (human-gate
policy under `-p`/`--mode rpc`/`--mode json`), Open-Q3 (MCP-broker reachability,
→ S6), or Open-Q4 (cutover/retirement sequencing, → S9).

## Linkage

- **Derived from:** `../plans/pi-dev-replatform-s3.md` (S3 closure record) and
  `../plans/pi-dev-replatform-s3-brainstorm.md` §D-S3-A (converged brief).
- **Consulted by:** S4 (the G-5 engine sequences over a *stable* in-process
  delegation edge — this record is the stability guarantee) and S6 (the
  RPC-variant trigger — this record names the S6-conditional future work).
