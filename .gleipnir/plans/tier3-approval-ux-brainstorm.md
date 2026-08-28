# Design Brief: Tier-3 Approval UX — staging, review-page, URL discovery, retry

> **STATUS: CONVERGED.** All four sub-decisions are operator-converged (A=A1,
> B, C=C2, D). This brief is ready for `gleipnir-plan` to plan from — no
> further operator convergence is needed. The convergence was surfaced by the
> orchestrator (a subagent's `question` cannot reach the operator); the
> operator's converged choices on the two material sub-decisions (A and C) are
> recorded verbatim in `## Selected Approach` below.

## Problem Statement

The already-built-and-merged `tier3-signed-approval` subsystem (PR #5) has a
correct, tested crypto core but a **manual, error-prone approval UX**. Told how
to actually use it — start `bin/gleipnir-approval-server`, run
`tailscale serve --bg 8765`, then manually
`curl -X POST --data-binary @/path/to/new-content.txt https://<host>/approve`
with the EXACT proposed byte content as the body — the operator responded:
**"nope, that is a manual process that operators can get wrong!"**

They are right. The only server interface is `POST /approve` with the raw
pending content as the request body; `GET /` serves static instructions. There
is **no staging mechanism**: nothing computes and holds "the exact content a
specific pending Tier-3 write wants to produce" for the operator to review
before approving. The operator would have to obtain byte-identical content and
paste/curl it themselves — and any mismatch (even one byte) triggers a REFUSE
that is fail-closed but pure friction: a genuine attempt just fails, with no
easy way to know why or fix it.

**The key existing asset:** `.gleipnir/plugins/tier3-gate.ts` ALREADY computes
`resultingContentFor(tool, args)` — the exact resulting bytes a `write` call
will produce — as part of every gate check, at refuse-time, before it shells
out to the CLI. The hook already knows exactly what content needs approving; on
REFUSE today it simply discards that computed content and throws. This brief
turns that discarded asset into the staged content the operator reviews.

This is a **UX/workflow fix layered on an already-correct, already-tested crypto
core** — not a redesign of the crypto.

## Constraints (carried over, not re-litigated)

- **stdlib-only, no new Python dependency** — this subsystem's whole discipline.
- **Tailnet-only transport** (no standing public port) — unchanged.
- **The token/gate/CLI crypto layer is ALREADY correct and tested** —
  `token.py`, `gate.py`, `__main__.py`, `identity/**` (including the
  mint-vs-check content-hash fix, Decisions 19+20). This brief is about the
  user-facing review/approve experience *wrapped around* that layer, never the
  crypto itself. **Zero changes to those files.**
- **`tier3-gate.ts`'s `resultingContentFor` already exists** and is the source
  of the staged content on refuse — reuse it; do NOT duplicate the
  write-vs-edit logic.
- **Already-converged items stand, not reopened:** identity route
  (TailscaleResolver, Route α), token crypto (HMAC, content+identity+freshness
  binding), the 180s freshness window, the Tier-3 path-set scope, and
  `tier3-writer`'s grants.

## Approaches Considered

The change decomposes into four sub-decisions. Three are near-forced or bounded
by the existing assets; one (staged-content origin, sub-decision A) is the
single genuinely material architectural tradeoff. They compose into one
workflow: **on REFUSE the hook stages the exact bytes → the operator visits a
review page and one-clicks Approve → the token mints against those exact bytes →
the operator retries the write.**

### Sub-decision A: Where does the staged pending content come from? (MATERIAL)

The hook (`resultingContentFor`) is the *only* party that knows the exact
resulting bytes at refuse-time (the disk still holds pre-edit base content;
`edit` is already refused; only `write` yields certain bytes). The *server* is
the party that mints. So the staged bytes must travel from hook to server.

#### Approach A1: Hook stages to disk on refuse; server reads staged file (SELECTED)

**Summary:** On REFUSE, `tier3-gate.ts` writes the computed `resultingContent`
to `.gleipnir/var/tmp/pending-<change_hash>.json` (same Tier-0 dir, same trust
tier as the minted tokens already there), keyed by the same `change_hash` the
token needs. The server's new `GET /approve/<hash>` reads that staged file,
renders it for review, and its form-POST mints against those exact staged bytes.

**Tradeoffs:**
- Pro: reuses the existing `resultingContentFor` asset — the hook already
  computed these exact bytes; A1 stages them instead of discarding them.
- Pro: `change_hash` keying makes the staged file and the token line up **by
  construction** — no byte-mismatch REFUSE from manual operator error.
- Pro: content-binding integrity is **preserved, not weakened** — the server
  still hashes the staged bytes and mints over that hash exactly as it hashes a
  POSTed body today; the staged file is just a different transport for the same
  bytes.
- Pro: stays within the established Tier-0 trust envelope — tokens already live
  in `var/tmp/` (gitignored/disposable); the hook already writes a transient
  content-file today (to `os.tmpdir()`), so a Tier-0 write is not new in kind.
- Con: the hook (Tier-3 enforcement code) gains a write to Tier-0 `var/tmp/`.
  **Fix/mitigation:** consistent with the existing model (same trust tier, same
  disposability); the staged file is *input to be reviewed*, never authority.

**Estimated Scope:** `tier3-gate.ts` (stage-on-refuse + `change_hash`
computation), low-medium complexity.

**Risk:** low — additive, Two-Way Door, crypto core untouched.

#### Approach A2: Server recomputes resulting content itself (REJECTED)

**Summary:** The server re-derives what a pending write wants to produce.

**Tradeoffs:**
- Pro: no hook staging write.
- Con (fatal): the server is a standalone process the operator starts; it never
  sees the pending tool call's `output.args.content`. It would have to reproduce
  opencode's write semantics — exactly the fuzzy-replacer/formatter reproduction
  the hook already refuses to attempt for `edit`. **Duplicates the write-vs-edit
  logic the constraints forbid duplicating, and reintroduces mismatch risk.**

**Estimated Scope:** would touch server + reintroduce edit-reproduction logic,
high complexity.

**Risk:** high — reintroduces the exact mismatch/duplication the crypto core was
designed to avoid. **Rejected.**

#### Approach A3: Keep manual POST, only add a review page for pasted content (REJECTED)

**Summary:** Add a review page for whatever the operator pastes; keep manual POST.

**Tradeoffs:**
- Pro: minimal server change.
- Con (fatal): does not remove the manual byte-obtaining step — the operator
  still has to source byte-identical content. Status quo with lipstick; fails
  the operator's actual objection.

**Estimated Scope:** server-only, low complexity — but does not solve the problem.

**Risk:** the change does not address the stated gap. **Rejected.**

### Sub-decision B: Review-then-one-click page (near-forced)

**Approach B (SELECTED):** `GET /approve/<hash>` renders the staged content AND
a **diff against the current on-disk file** (so the operator sees *what
changes*, not opaque bytes), with a same-page HTML `<form method=POST>` that
submits to the existing mint path. No curl, no new dependency — stdlib
`http.server` already serves HTML (`do_GET` already returns an HTML body); same
tailnet-only transport, same trust envelope.

**Tradeoffs:**
- Pro: matches every standard human-approval flow (GitHub PR review, Slack
  approve button) — read-then-click, not raw-byte-paste.
- Pro: the diff view is the actual safety win — the operator reviews the change,
  not just opaque bytes.
- Con: the POST target must still content-bind. **Fix:** the form POSTs the
  staged content back (or the server re-reads the staged file by `<hash>`), and
  mint proceeds exactly as `POST /approve` does today — the existing
  `capture_approval` core is reused unchanged.

**Estimated Scope:** `server.py` (new `GET /approve/<hash>` route + diff render +
form), low-medium complexity.

**Risk:** low — additive; reuses `capture_approval` unchanged.

### Sub-decision C: How does the operator learn the URL? (open preference — converged)

The gate's REFUSE message (`decideFromExit`, already surfaced verbatim to
whoever triggered the write; `tier3-writer` is disciplined to report it
verbatim) should include the ready-to-visit URL
`https://<tailnet-host>/approve/<change_hash>`. The `<change_hash>` is available
by construction (A1 keys the staged file by it, so the hook computes that same
sha256 — trivial stdlib crypto in Node). The `<tailnet-host>` is the one open
input:

#### Approach C1: Derive host via `tailscale status --json` (NOT selected)

- Pro: zero operator config.
- Con: adds a `tailscale` invocation from the hook's message-building path
  (enforcement code should stay lean); `tailscale serve` port/path is
  operator-chosen and not reliably derivable from `status`.

#### Approach C2: Operator-configured base URL env var (SELECTED)

**Summary:** Operator sets the base URL once (env var, e.g.
`GLEIPNIR_APPROVAL_BASE_URL`), read by the hook when building the refusal
message. Graceful **relative-hint fallback** if unset (print `/approve/<hash>` +
"visit your approval listener").

- Pro: no new shell-out from enforcement code; explicit; matches the fact that
  the operator already runs `tailscale serve --bg 8765` by hand — they already
  know their own URL, so a one-time export is consistent friction, not new
  friction.
- Con: one-time operator setup.

**Estimated Scope:** `tier3-gate.ts` (read env var, build URL, fallback),
low complexity.

**Risk:** low.

### Sub-decision D: Retry semantics after approval (bounded — do not over-engineer)

**Approach D (SELECTED):** Manual retry, matching the framework's existing
human-in-the-loop shape. Once the operator approves (clicks Approve → token
minted), the *same* write is retried by whoever attempted it — the agent's
delegation retries once the operator confirms approval is done, exactly like the
`question` tool's Confirm step and the lesson-escalation gate. **No auto-retry
machinery.**

**Tradeoffs:**
- Pro: simple; matches existing gates; the 180s freshness window is the natural
  bound on the retry.
- Pro: no new cross-process state to hold/re-drive a pending tool call.
- Con: the operator/agent must remember to retry. **Fix:** the refusal message
  (sub-decision C) tells them exactly what to do; retry within 180s.

**Estimated Scope:** no code — a delegation/discipline pattern (documented, not
built).

**Risk:** low — deliberately minimal; auto-retry deferred as out-of-scope.

## Decision Analysis

**Framework used:** Reversibility Filter (applied first to the whole change) →
Second-Order Thinking → Pre-Mortem for the one material sub-decision (A,
staged-content origin), per the decision-frameworks auto-selection table for an
architectural tradeoff. Pros-Cons-Fixes for the near-forced sub-decisions (B,
C, D).

**Analysis results:**

*Reversibility Filter (whole change):*
- Reversibility: **Two-Way Door.** Every piece is additive to an
  already-correct, already-tested crypto core: a new staging write on refuse, a
  new `GET` route, a string in an error message. Nothing changes
  `token.py`/`gate.py`/`__main__.py`/`identity/**`.
- Reversal cost: deleting additive code; no data migration, no external
  commitment, no crypto rework.
- Recommendation: fast-track the three forced/bounded pieces (B, C, D); apply
  deeper analysis to the one material sub-decision (A) because it crosses the
  TS→Python trust boundary.

*Sub-decision A — Second-Order Thinking + Pre-Mortem:*
- A1 near-term: operator never obtains/pastes bytes — they click a link; the
  `change_hash` keying means staged file and token line up by construction (no
  byte-mismatch REFUSE from manual error).
- A1 far-term: the hook gains a Tier-0 `var/tmp/` write — consistent with the
  existing model (tokens already live there; hook already writes a temp
  content-file today), not new in kind.
- **Key insight:** content-binding integrity is *preserved, not weakened* — the
  server still hashes the staged bytes and mints over that hash exactly as it
  hashes a POSTed body today; the staged file is just a different transport for
  the same bytes.
- Pre-mortem killed A2 (server can't see the pending tool call → would duplicate
  the refused edit-reproduction logic) and A3 (does not remove the manual
  byte-obtaining step → fails the operator's objection).

*New-risk check (staging Tier-3 content in Tier-0 scratch):* **No new integrity
risk.** The staged file is *input to be reviewed*, never authority. Authority
still rests solely on the HMAC token the server mints only after an
identity-resolved approval. A poisoned/edited staged file only changes what the
operator *sees and would approve*; if they approve it, the token binds to those
exact bytes and the write produces exactly those bytes — the operator reviewed
and authorised them. Preserve: the review page MUST render the staged bytes the
mint will hash (what-you-see-is-what-you-sign). Minor hardening for the plan
(not a blocker): treat staged files as untrusted display input — HTML-escape on
render.

**Bias warnings (top 3 of 12 checked):**
- ⚠️ **Scope Creep Bias** *(most relevant)*: temptation to make retry automatic,
  add tailnet auto-discovery, add a listing page of all pending approvals. The
  operator said "keep it tight." Sub-decisions C and D are deliberately held to
  the minimum (configured URL, manual retry); anything else is deferred.
- ⚠️ **IKEA Effect**: `resultingContentFor` is our own recently-built asset and
  A1 leans on it heavily. Checked: it is genuinely the *only* party that knows
  the exact bytes at refuse-time (verified against `__main__.py`'s Decision-19
  note and the `edit`-refusal), so reuse is fitness-driven, not built-here
  favouritism. A2 was evaluated on merits and rejected for a concrete reason.
- ⚠️ **Status Quo Bias** *(inverted — flagged for honesty)*: the status quo
  (manual POST) is being *rejected*, so the risk is under-scrutinising the
  change. Checked: the change is a Two-Way Door, additive, crypto-core-untouched
  — low blast radius, so aggressive change is warranted, not reckless.
- *(Others checked, not triggered: Anchoring, Confirmation, Sunk Cost,
  Availability, Bandwagon, Dunning-Kruger, Survivorship, Recency, Authority.)*

**Recommendation:** A1 (hook stages on refuse) + B (review+diff+one-click page)
+ C2 (operator-configured base URL) + D (manual retry). All four were surfaced
to the operator via the orchestrator; A and C (the material/open ones) were
converged by the operator (see `## Selected Approach`).

## Selected Approach

**Choice:** A1 + B + C2 + D — a UX wrapper on the unchanged crypto core.

**All four sub-decisions, with the operator's converged choices explicit:**

- **A = A1 (operator-converged, material).** On REFUSE, `tier3-gate.ts` stages
  the already-computed `resultingContent` to
  `.gleipnir/var/tmp/pending-<change_hash>.json` (Tier-0, same trust tier as the
  minted tokens, gitignored/disposable), keyed by the same `change_hash` the
  token needs; the server reads that staged file. **Operator's converged answer
  (verbatim):** *"A = A1 (hook stages `resultingContent` to
  `.gleipnir/var/tmp/pending-<change_hash>.json` on refuse; server reads it)."*
  Rationale: reuses the existing `resultingContentFor` asset; `change_hash`
  keying aligns staged file and token by construction (no byte-mismatch from
  manual error); content-binding preserved, not weakened (server hashes the
  staged bytes exactly as it hashes a POSTed body today); stays within the
  established Tier-0 envelope. A2/A3 rejected (server can't see the pending call
  / does not remove the manual step).

- **B (operator-affirmed near-forced).** `GET /approve/<hash>` renders the staged
  content **plus a diff against the current on-disk file**, with a same-page
  HTML `<form method=POST>` that reuses the existing `capture_approval` mint path
  unchanged. No curl, no new dependency, same tailnet-only transport. Rationale:
  matches standard human-approval flows (PR review / Slack approve); the diff
  view is the safety win; content-binding preserved because the form POSTs the
  staged bytes back and mint proceeds as `POST /approve` does today.

- **C = C2 (operator-converged, open preference).** The gate's REFUSE message
  includes the ready-to-visit URL `https://<host>/approve/<change_hash>`; the
  `<change_hash>` is available because A1 makes the hook compute it to name the
  staged file; the `<host>` base URL is **operator-configured via an env var
  (e.g. `GLEIPNIR_APPROVAL_BASE_URL`)**, read by the hook when building the
  message, with a **graceful relative-hint fallback if unset**. **Operator's
  converged answer (verbatim):** *"C = C2 (operator-configured base URL via an
  env var, e.g. `GLEIPNIR_APPROVAL_BASE_URL`, read by the hook when building the
  refusal message; graceful relative-hint fallback if unset)."* Rationale: keeps
  enforcement code lean (no `tailscale` shell-out from the hook); explicit; the
  operator already runs `tailscale serve` by hand and knows their URL, so a
  one-time export is consistent friction, not new friction. C1 (derive via
  `tailscale status --json`) not selected.

- **D (operator-affirmed bounded).** Manual retry, matching the `question`-tool
  Confirm step and the lesson-escalation gate: once approved (token minted), the
  same write is retried by whoever attempted it; no auto-retry machinery. The
  180s freshness window bounds the retry; the refusal message (C) tells the
  operator/agent exactly what to do. Deliberately minimal — auto-retry deferred
  as out-of-scope (Scope Creep Bias check).

**Rationale (summary):** This is purely additive to the already-merged crypto
core. It converts an error-prone manual `curl` of raw bytes into a
review-then-one-click flow by reusing the hook's already-computed
`resultingContent`, preserving content-binding exactly, staying stdlib-only and
tailnet-only, and touching no crypto file.

### Purely additive — zero changes to the crypto core

**Zero changes** to `src/gleipnir/approval/token.py`,
`src/gleipnir/approval/gate.py`, `src/gleipnir/approval/__main__.py`, and
`src/gleipnir/approval/identity/**`. The token/gate/CLI/identity layer is
already correct and tested (including the Decisions 19+20 mint-vs-check
content-hash fix) and stands unchanged. This brief adds a UX wrapper *around*
that layer only.

### Hardened-path routing requirement (blast-radius split)

The two touched files sit in **different trust tiers** and route differently:

- **`tier3-gate.ts` — Tier-3 enforcement code (`.gleipnir/plugins/**`).** It is
  in the enforcement-path set `E` (`stage-role-map.md`), so its change is an
  **operator/build-mode act**, applied exactly like the original plugin was —
  NOT a `gleipnir-code` write and NOT a `tier3-writer` write (`.gleipnir/plugins/**`
  is deliberately absent from `tier3-writer`'s grant; the guard must not be
  reachable by the guarded, Axiom 2 / G-1). The plan built from this brief MUST
  route the `.ts` change through the **hardened path** (two separate reviewer
  passes — spec-conformance + blast-radius/false-success — plus the
  negative-check attestation, per `stage-role-map.md`).
- **`server.py` — ordinary `src/gleipnir/**` code.** Its change (the new
  `GET /approve/<hash>` review+diff page and form-POST reuse of
  `capture_approval`) is buildable and testable directly by any `gleipnir-code`
  delegation in the sandbox — the full 8-stage pipeline with the pre-written
  test as arbiter (it is in the Axis-1 disqualifier set `X = src/**`, so it runs
  the full pipeline, not the prose/config track).

Because the change spans an enforcement path (`.gleipnir/plugins/**`) and
executable source (`src/**`), the plan is enforcement-bearing and executable —
it runs the **full 8-stage pipeline on the hardened path**. The `.ts` half is
operator/build-mode applied; the `.py` half is `gleipnir-code`-built-and-tested.

## Open Questions

- **None blocking.** Both material/open sub-decisions (A, C) are
  operator-converged; B and D stand as affirmed near-forced/bounded
  recommendations. Items for `gleipnir-plan` / the code stage to settle as
  implementation detail (not convergence):
  - The staged-file JSON shape for `pending-<change_hash>.json` (must at minimum
    carry the exact resulting bytes the server will hash; keep it a transient
    Tier-0 vehicle, not a Gleipnir artifact).
  - HTML-escaping the staged bytes on render (what-you-see-is-what-you-sign;
    treat staged files as untrusted display input).
  - Exact env-var name (`GLEIPNIR_APPROVAL_BASE_URL` is the working name) and
    the precise relative-hint fallback wording in the refuse message.
  - Whether `GET /approve/<hash>` re-reads the staged file by `<hash>` or the
    form round-trips the bytes — either preserves content-binding; pick the
    simpler at code stage.

## Scope Sketch

| Area | Files/Modules Likely Affected | Tier / Routing |
|------|-------------------------------|----------------|
| Stage-on-refuse + `change_hash` compute + URL message (C2 env var, fallback) | `.gleipnir/plugins/tier3-gate.ts` | **Tier-3 enforcement code** — operator/build-mode applied, **hardened path** (2 reviewer passes + negative-check attestation) |
| Review+diff page + one-click form-POST reusing `capture_approval` | `src/gleipnir/approval/server.py` | Ordinary `src/**` — `gleipnir-code` build+test, full 8-stage pipeline |
| Crypto core (token / gate / CLI / identity) | `token.py`, `gate.py`, `__main__.py`, `identity/**` | **UNCHANGED — zero edits** |
| Staged content (transient) | `.gleipnir/var/tmp/pending-<change_hash>.json` | Tier-0, gitignored/disposable — input-to-review, never authority |

---
Provenance: design brief written by gleipnir-brainstorm (Tier-0 writer) under
bounded delegation. Convergence surfaced by the orchestrator (a subagent's
`question` cannot reach the operator). Operator's converged answers on the two
material/open sub-decisions (A, C) are quoted verbatim in `## Selected
Approach`. B and D stand as operator-affirmed near-forced/bounded
recommendations. Decision Analysis (framework + bias check) is the
justification. Ready for `gleipnir-plan`.
