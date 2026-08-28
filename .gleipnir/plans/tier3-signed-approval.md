# Plan: Tier-3 out-of-band signed-approval channel (Route α + freshness-bound token gate + `tier3-writer`)

> **Stage:** `plan` (gleipnir-plan). **Input:** the CONVERGED brief
> `.gleipnir/plans/tier3-signed-approval-brainstorm.md` (658 lines, read in
> full; `## Selected Approach — CONVERGED`). All five threshold questions AND
> the identity-capture sub-decision are operator-decided: **Route α**
> (Tailscale-injected identity) behind a **pluggable `IdentityResolver` seam**;
> **G-3.1-reused** freshness-bound, content-bound HMAC approval token;
> **3-minute / 180s** freshness window; a **code-enforced fail-closed
> write-gate**; a generalized **`tier3-writer` (signature-gated)** executor that
> **subsumes** the paused `decision-scribe` proposal and covers **ALL** of Tier-3
> (`agents/`, `skills/`, `goals/`, `stage-role-map.md`, `keys/`, `decisions/`).
> This plan does **not** re-decide any of those. It plans the *bounded*
> implementation work those decisions define, and resolves only the
> `[PLAN-STAGE JUDGMENT]` details the brief explicitly left to the plan stage
> (module layout, exact constant/type/method names, exact test file names, the
> listener start/stop story, the `tailscale whois` invocation shape).
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0); this file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it. Critically, **no
> in-framework agent (including `gleipnir-code`) may write any Tier-3 path,
> ever** — so the **THREE Tier-3 artifacts** this feature needs (the new
> `.gleipnir/agents/tier3-writer.md` frontmatter file; the new Tier-3 plugin
> `.gleipnir/plugins/tier3-gate.ts` — the code-enforced write-gate hook, in the
> `stage-role-map.md` enforcement-path set `E`; and the durable decision record
> `.gleipnir/decisions/tier3-signed-approval.md`) are **named here but applied
> by the operator / build-mode**, exactly like every prior Tier-3 rollout in
> this project (the `git-diff-distill` `profiles.toml` precedent, the
> `s2-g1-closure` boundary rollout, and the existing Tier-3 plugins
> `sequence-gate.ts`/`git-guard.ts`/`advance-hook.ts`). This plan does not write
> them.
>
> **This is Tier-3-enforcement-bearing** per `stage-role-map.md` Axis 1/2: `P`
> touches `.gleipnir/agents/**` (new `tier3-writer.md`), `.gleipnir/decisions/**`
> (new record), and — via Axis 2(b) content rule — a new agent `permission:`
> block granting Tier-3 `edit`/`write`. It therefore runs the **full hardened
> 8-stage pipeline** (NOT the light prose/config track), and the `quality` stage
> MUST run the **dual SPEC-CONFORM + BLAST-RADIUS passes plus a negative-check
> attestation** for the Tier-3 pieces (see Execution Workflow).

---

## Decisions (index)

Every decision this plan fixes, in order encountered. Rows 1–9 → the CONVERGED
brief (operator-converged; **recorded, NOT re-decided** — cited to the brief).
Rows 10–18 → `[PLAN-STAGE JUDGMENT]` details made during Architect/Trace,
flagged for spec-review per the delegation. Full reasoning for each row is in
the sections below.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Identity capture route | **Route α** — Tailscale-injected identity resolved via `tailscale whois`, Entra-backed | Route β (direct Entra OIDC app); γ (Slack/Discord/SMS); δ (pure-local OS-perm only) | Buildable-now (stdlib + already-deployed infra), single-operator near-term fit; matrix 543. **Brief `## Selected Approach` + Decision Analysis — operator-converged.** |
| 2 | Extensibility | Pluggable `IdentityResolver` seam; Route β / other OIDC add as a 2nd resolver by registration alone | Hard-coding Tailscale into the gate/mint code | Operator: *"a future fix should open this up to other OIDC providers."* Testable design constraint. **Brief `## Extensibility requirement` — operator-converged.** |
| 3 | Token primitive | **Reuse G-3.1** (`verify.marker` mint/validate) — HMAC over canonical content, freshness-bound, content-bound, fail-closed | New crypto; a bespoke token format | Answer-5's "time-scoped / no replay / content-bound" maps exactly onto existing `validate()` mechanisms. **Brief `## The G-3.1 primitives this reuses` — operator-converged.** |
| 4 | Freshness window | **180 seconds (3 minutes)**, a named constant, overridable | 2-min floor (too tight to read a real diff); 5-min ceiling (wider replay surface); default 3600s | Midpoint of operator-confirmed 2–5 min band. **Brief `## Freshness window — 3 minutes` — operator-converged.** |
| 5 | Write-gate | **Code-enforced fail-closed** preflight: no valid fresh content-bound token ⇒ REFUSE, before any Tier-3 write executes | Documented discipline; in-session `question` | Answer-5 requires a *code* gate, mirroring `verify/__main__.py:_cmd_check` + `preflight/boundary.decide()`. **Brief item 3 of Selected Approach — operator-converged.** |
| 6 | Executor role | Generalized **`tier3-writer` (signature-gated)**, deny-by-default, all-Tier-3 path-set, no `question`/git/bash/task | Keeping `decision-scribe` (decisions/-only scope) alongside | Scope is all-Tier-3 (answer 3); `decision-scribe` is subsumed. The role holds NO tool through which it could itself pre-call the gate; the gate is enforced *around* it by an out-of-band plugin hook (Decision 14a), not *inside* its own tool sequence. **Brief `## Executor role` — operator-converged.** |
| 7 | Transport / no public surface | Tailnet-only via `tailscale serve`; listener binds `127.0.0.1` | A standing public inbound port (the rejected option-8B trap) | Dodges the E-2 standing-public-surface obstacle. **Brief `## What the already-deployed identity infra makes cheap` — operator-converged.** |
| 8 | E-2 | Closes the **approval-inbound slice** of E-2 (first component home); general webhook ingress remains open | Claiming full E-2 closure | Honest scoping. **Brief `## Does this close E-2?` — operator-converged.** |
| 9 | Out-of-scope | Tier-2 / G-4c (lessons/memory) generalization NOT built now; seam designed so it is additive later | Generalizing the gate to Tier-2 now (scope creep) | **Brief `## Open Questions (final)` — operator-converged.** |
| 10 | **`[PLAN-STAGE JUDGMENT]`** Module home | New sibling package **`src/gleipnir/approval/`** (sibling to `broker/`, `verify/`, `preflight/`, `engine/`) | Folding into `verify/` (mixes marker-CLI with a network listener); into `preflight/` (mixes boundary probe with approval capture) | Approval capture is a distinct responsibility (a network receiver + identity resolution + token mint orchestration) with its own new blast radius (a listener). `src/gleipnir/` convention is one directory per subsystem; this is a new subsystem. Flagged for spec-review. |
| 11 | **`[PLAN-STAGE JUDGMENT]`** Token type | New module `approval/token.py`: `ApprovalToken` frozen dataclass + `mint_approval(change_hash, approver_identity, provider, key, minted_at=None)` and `validate_approval(token, change_hash, approver_identity, key, max_age_seconds=APPROVAL_MAX_AGE_SECONDS, now=None) -> bool`, both **delegating to `verify.marker`'s HMAC over a canonical `\x1f`-joined input** | Re-implementing HMAC; storing raw `verify.marker.Marker` with a synthetic tree_hash smuggling identity in | Reuses the *tested* `_canonical_signing_input` length-prefixing discipline and `hmac.compare_digest` validate shape without overloading `Marker`'s tree-binding semantics; identity is a first-class token field, not smuggled. Flagged for spec-review. |
| 12 | **`[PLAN-STAGE JUDGMENT]`** Freshness constant name | `APPROVAL_MAX_AGE_SECONDS = 180` in `approval/token.py` (overridable per-call, like `validate`'s `max_age_seconds`) | A magic literal `180`; reusing `marker.DEFAULT_MAX_AGE_SECONDS` (3600, wrong window) | Brief mandates "180s as a named constant, not a magic literal." Flagged for spec-review. |
| 13 | **`[PLAN-STAGE JUDGMENT]`** Resolver seam layout | `approval/identity/{protocol.py,registry.py,tailscale_resolver.py,__init__.py}` mirroring `broker/git/content_handlers/{protocol.py,registry.py,__init__.py}` EXACTLY, but with a **fail-closed** dispatcher (no-match ⇒ raise/reject, NOT return-unchanged) | A single hard-coded Tailscale call; reusing content_handlers directly (its no-match fallback is benign-passthrough, wrong here) | The content_handler dispatcher returns content unchanged on no-match (benign); an identity dispatcher must **reject** on no-match (never default to an unauthenticated identity — brief). Same open/closed shape, opposite no-match posture. Flagged for spec-review. |
| 14 | **`[PLAN-STAGE JUDGMENT]`** Write-gate location | New module `approval/gate.py`: `require_valid_token(change_hash, approver_identity, token_path, key, *, max_age_seconds, now) -> GateDecision` returning REFUSE on any failure/absence, plus a **CLI entry point `python -m gleipnir.approval.gate --check <path> --token <token-file>`** (exit 0 = ALLOW, non-zero = REFUSE, mirroring `verify/__main__.py:_cmd_check`) so an out-of-band caller can invoke it | A single call site (a bypass risk per Pre-Mortem #2) | Single choke-point discipline of `boundary.decide()`. The gate LOGIC lives here; the deterministic BLOCK on writing-without-signature is wired by Decision 14a (the gate is a library + CLI; the block is a hook that calls it). Flagged for spec-review. |
| 14a | **`[PLAN-STAGE JUDGMENT]`** Deterministic write-block wiring | New **Tier-3 opencode plugin `.gleipnir/plugins/tier3-gate.ts`** hooking `tool.execute.before` for `edit`/`write`; routes on the **target path** (`output.args.filePath` — the same shape the documented `.env`-protection example uses) — if the write targets a Tier-3 path (the enforcement path-set), it computes the exact resulting content this call will produce (Decision 20) and shells out to `python -m gleipnir.approval.gate --check <filePath> --content-file <temp> --token <token-file>` and **throws to abort the tool call** on any non-ALLOW exit (fail-closed). Mirrors `git-guard.ts`/`sequence-gate.ts` EXACTLY (both throw from `tool.execute.before`) | (i) A role-side pre-call — impossible: `tier3-writer` holds no git/bash/task tool to invoke the gate before its own `edit`/`write` (Decision 6); (ii) documented-discipline / manual-only preflight — explicitly REJECTED by the operator's converged answer ("provided there is a deterministic block on writing without signature", brief) | The ONLY mechanism that makes the code-enforced gate real: the plugin is framework code that runs in-process before the tool executes and can throw to abort (verified: `hook-probe-findings.md` Point 3 + the two existing `tool.execute.before` throwing gates). Routing on the **target path** (not the acting-agent identity, which the before-hook input does NOT carry) is the robust form the review recommended: **any** agent's `edit`/`write` to a Tier-3 path is gated, not just `tier3-writer`'s. `.gleipnir/plugins/**` is in enforcement-path set `E`, so this is a Tier-3 artifact applied by operator/build-mode. Flagged for spec-review. |
| 15 | **`[PLAN-STAGE JUDGMENT]`** Listener module + start/stop | `approval/server.py` (stdlib `http.server.HTTPServer` + `BaseHTTPRequestHandler`, bind `127.0.0.1`), started by a **thin operator shim `bin/gleipnir-approval-server`** (same shape as `bin/gleipnir-preflight`); a long-running process the operator starts manually and Ctrl-C stops. **No auto-start.** | An auto-started/daemonized listener (not in the brief; "cooperative-until-closed" framing wants an honest operator-run process) | Matches the brief's honesty ledger ("Buildable now: the local `http.server` receiver") and the `bin/` thin-shim precedent. `bin/gleipnir-approval-server` itself is a NEW `bin/**` file — executable, Axis-1 disqualifier — built by `gleipnir-code` under the hardened path (not Tier-3, but blast-radius-reviewed). Flagged for spec-review. |
| 16 | **`[PLAN-STAGE JUDGMENT]`** `tailscale whois` invocation | `subprocess.run(["tailscale", "whois", "--json", remote_ip], capture_output=True, text=True, timeout=...)`, parse stdout JSON for the user login; **stdlib `subprocess` only, NO new Python dependency**; requires the `tailscale` CLI installed system-side (an environmental prerequisite, named honestly, not a Python dep) | Trusting an injected `Tailscale-User-Login` header on a raw port (spoofable per Pre-Mortem #3); a Python Tailscale SDK (new dep) | `subprocess` is stdlib-compatible (`runtime-and-deps.md`); resolving via LocalAPI `whois` is authenticated. Header-only trust rejected by the brief's Pre-Mortem #3. Flagged for spec-review. |
| 17 | **`[PLAN-STAGE JUDGMENT]`** Token file path | Token minted to a path under `.gleipnir/var/tmp/` (Tier-0, gitignored) — e.g. `var/tmp/approval-<change_hash_prefix>.json`; gate reads it by path | Committing tokens; storing in `keys/` (Tier-3, and tokens are ephemeral not policy) | Tokens are short-lived (180s) Tier-0 scratch; `var/tmp/` is the disposable tier per AGENTS.md layout. Flagged for spec-review. |
| 18 | **`[PLAN-STAGE JUDGMENT]`** Test file names | `tests/test_approval_token.py` (mint/validate/freshness/content-binding/identity-binding), `tests/test_approval_identity_resolver.py` (contract + fail-closed dispatch + extensibility 2nd-resolver + structural source-scan), `tests/test_approval_gate.py` (fail-closed gate + end-to-end mint→gate→refuse/accept), `tests/test_approval_server.py` (listener request→resolve→mint round-trip with injected fakes) | One monolithic test file | Mirrors `git-diff-distill`'s per-concern test split; each is stdlib-only (no `mcp`) so runs under the default `python` profile. Flagged for spec-review. |
| 19 | **`[PLAN-STAGE JUDGMENT]`** Check-time content source (the mint-vs-check hash-mismatch fix) | The gate CLI hashes **the exact resulting bytes this specific tool call will produce**, handed to it via a new **`--content-file <path>`** argument (a temp file the plugin writes with the proposed post-write content), **NOT** a fresh `read_bytes()` of the live target file. `--check <filePath>` is retained purely as the file **identifier** (which Tier-3 file), never re-hashed. `server.py`'s mint-time `compute_change_hash(pending_content)` and the CLI's check-time hash now compute over the **identical byte-string definition** ("the exact resulting file content"), so a one-byte divergence genuinely invalidates the token (Architect criterion 2). | (a) Hashing `target_path.read_bytes()` at check-time — the ORIGINAL BUG: `tool.execute.before` fires *before* the write lands, so the disk bytes are always the pre-edit/base content, never the approved new content ⇒ every legit edit refused; (b) "fixing" it by binding the token to the base content ⇒ a bait-and-switch hole (verifies nothing about what actually gets written). Both contradict criterion 2. | The token was minted over the NEW proposed content the operator approved on the web page (`server.py` hashes the POSTed body). The check must therefore hash the *same* new content — which only the plugin knows (it is the tool call's proposed result), not the disk. Handing it in via `--content-file` is the single mechanism that makes mint-time and check-time hash the same thing. **Bounded implementation of the already-converged "code-enforced content-binding" (Decision 5), not a new material tradeoff.** Flagged for spec-review. |
| 20 | **`[PLAN-STAGE JUDGMENT]`** Resulting-content computation per tool (`edit` fail-closed) | In `tier3-gate.ts`: for a **`write`** call the resulting content is `output.args.content` directly (verified against opencode source `packages/opencode/src/tool/write.ts@dev`: `write` params are `{content, filePath}` and the written bytes are exactly `params.content`) → written to a temp file, passed as `--content-file`. For an **`edit`** call the plugin **CANNOT reliably reproduce** the resulting bytes and therefore **fails closed (throws/REFUSE)**: opencode's `edit` (`packages/opencode/src/tool/edit.ts@dev`) does NOT do a plain `oldString`→`newString` replace — it runs a **9-replacer fuzzy-match cascade** (Simple/LineTrimmed/BlockAnchor/WhitespaceNormalized/IndentationFlexible/EscapeNormalized/TrimmedBoundary/ContextAware/MultiOccurrence, with Levenshtein-similarity thresholds), plus BOM + line-ending normalization, plus a post-write auto-`format.file()` pass — none of which is reliably reproducible out-of-band in TypeScript. | (i) Reproducing opencode's `edit` replacement in TS — REJECTED: the fuzzy cascade + formatter cannot be certain to match opencode's bytes, so a guess risks either false-REFUSE or (worse) a computed-content that DIFFERS from what opencode writes, defeating the binding; (ii) hashing the base file for `edit` — REJECTED (the bait-and-switch hole of row 19). | The existing fail-closed design principle: **if the plugin cannot be CERTAIN of the resulting content, it must REFUSE rather than guess** (Decision 5, `boundary.decide()` discipline). `write` IS certain (the content is handed over verbatim); `edit` is NOT. So Tier-3 changes go through `write` (full-file, deterministic), and an `edit` to a Tier-3 path is refused with a message directing the operator to use `write`. This keeps the content-binding SOUND for every allowed path. Flagged for spec-review. |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`goals/manifest.md`):** "Plan format" (`plan-format.md`) and
  "Methodology (ATLAS/GOTCHA ahead of planning)" apply; followed here
  (Decisions-index / Architect / Trace / Link / Assemble / Stress-test /
  Execution Workflow / Design Principles). No pipeline-sequencing goal authored
  (G-5 rule respected).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or Tier-3 writes are produced here — only this plan file.
- **Layer placement (GOTCHA layers):** this is primarily an **enforcement-core /
  Tools-layer** concern with a real **Args-layer** structural boundary (the
  `IdentityResolver` contract cannot reach token/gate internals). It touches
  **G-3.1** (token reuse), the **G-1/S-2 boundary** posture (the gate is
  cooperative-until-closed, like the other guards), and **G-6** (a Tier-3 write
  path). It does **not** amend the G-5 pipeline ordering.
- **Gaps / factual findings named (mechanical, not material):**
  1. **There is NO code Tier-3 write invocation point today.** `src/gleipnir/`
     contains `broker/ bus/ engine/ ledger/ preflight/ sandbox/ verify/` — **no
     `approval/`**, and `grep approval src/gleipnir` returns nothing. Every
     prior Tier-3 write in this project was an *ad-hoc operator / build-mode
     edit* (agent frontmatter `edit` grants + human hands), NOT a code path.
     `preflight/boundary.py` already lists `decisions/**`, `keys/**`,
     `agents/*.md`, `goals/**`, `stage-role-map.md` in `ENFORCEMENT_PATHS`
     (lines 168–222) and *denies agent writes to them at the OS layer* — but it
     does **not** gate a *legitimate* Tier-3 write on a fresh token. **So this
     plan must build the FIRST Tier-3 write-with-gate invocation point.** That
     invocation point is a **`tool.execute.before` plugin hook**
     (`.gleipnir/plugins/tier3-gate.ts`, Decision 14a) that, on any `edit`/`write`
     targeting a Tier-3 path, calls the `approval/gate.py` choke-point (via its
     CLI, Decision 14) and **throws to abort** if no valid fresh token is bound
     to that change. The `tier3-writer` role holds no tool through which it could
     call the gate itself (Decision 6), so the gate is enforced *around* the tool
     call by the plugin, not *inside* the role's own action — this is exactly the
     wiring shape of the three existing Tier-3 plugins
     (`sequence-gate.ts`/`git-guard.ts`/`advance-hook.ts`). Reported honestly per
     the delegation. (This is a *bounded build*, not a material tradeoff: the
     brief already decided the gate exists and is code-enforced; where the first
     call site lives — and that the deterministic block is a hook, mirroring the
     existing precedent — is the plan-stage detail, Decisions 14 + 14a.)
  2. **`keys/marker.key` already exists** (`.gleipnir/keys/marker.key`
     confirmed on disk) and `KEY_ENV_VAR = "GLEIPNIR_MARKER_KEY_FILE"`
     (`marker.py:40`) is the shared key location. **No new key is created** —
     the approval token reuses the G-3.1 HMAC key. Confirmed this session.
  3. **`bin/` has a thin-shim precedent** (`bin/gleipnir-preflight`,
     `bin/gleipnir-sandbox`, `bin/gleipnir-launch`): each is a `#!/bin/sh`
     exec-into-stdlib-Python shim, run by the operator, not on any agent
     allowlist. `bin/gleipnir-approval-server` follows this exact shape.
  4. **The content-handler dispatcher's no-match posture is WRONG for identity
     and must be inverted.** `content_handlers/registry.py:dispatch` returns
     `ProcessedResult(content=content)` unchanged on no-match (benign
     passthrough). The identity dispatcher must instead **fail closed (reject)**
     on no-match — never default to an unauthenticated identity (brief). Same
     open/closed register/dispatch shape, deliberately opposite no-match branch
     (Decision 13).
  5. **[QUALITY-REVIEW DEFECT, fixed this revision] Mint-time vs check-time
     content-hash mismatch.** As originally specified, the gate CLI's
     `_compute_change_hash` hashed `target_path.read_bytes()` — the file's LIVE
     DISK bytes at check-time. But `tier3-gate.ts` runs the CLI from
     `tool.execute.before`, which fires **strictly before** the edit/write lands
     on disk, so at check-time the disk always holds the **pre-edit/base**
     content — never the approved NEW content. Meanwhile `server.py` mints the
     token over the **posted new content** the operator approved. These are
     different byte-strings for any genuine edit ⇒ `hmac.compare_digest` never
     matches ⇒ every legitimately-approved Tier-3 edit is REFUSED (or, if
     "fixed" by binding to the base, a bait-and-switch hole). Both readings
     contradict Architect criterion 2. **Fix (Decisions 19 + 20):** the CLI
     hashes content **handed to it** via a new `--content-file` arg (the exact
     proposed resulting bytes), not a fresh disk read; the plugin computes that
     content — trivially for `write` (`output.args.content`), and **fails closed
     for `edit`** because opencode's fuzzy-replacer + formatter `edit` path is
     not reliably reproducible out-of-band. Verified against real code
     (`__main__.py:_compute_change_hash`, `server.py:compute_change_hash`,
     `token.py:validate_approval`) and against opencode's authoritative tool
     schemas (`write.ts`/`edit.ts@dev`) this session.

**New material tradeoff found?** **No.** Every material tradeoff was settled in
the CONVERGED brief (Route α, resolver seam, 3-min window, code-enforced gate,
`tier3-writer`, all-Tier-3, E-2-partial). The plan-stage items (module layout,
constant/type/method names, listener start/stop story, `whois` invocation, test
file names, first-call-site location) are **bounded implementation details, not
material design tradeoffs** — the brief's `## Open Questions (final)`
explicitly names "exact module layout, the resolver contract's precise method
signatures, and conformance-test specifics are for `gleipnir-plan` (ATLAS) to
specify — they do not require further operator decision." I record them as
`[PLAN-STAGE JUDGMENT]` rows for spec-review. **Nothing here is a
quietly-enshrined material decision** — the one arguably-consequential detail
(building the first Tier-3 write call site, finding 1) is surfaced explicitly,
not smuggled, and follows directly from the already-converged code-enforced-gate
decision. The content-hash-mismatch fix (finding 5, Decisions 19 + 20) is
likewise **not** a new material tradeoff: the material decision
("code-enforced content-binding") was already converged (Decision 5); Decisions
19 + 20 are the *correct implementation* of it, and are bounded technical
judgment calls flagged for spec-review — the `edit`-fail-closed choice follows
directly from the pre-existing "refuse rather than guess" fail-closed principle.

---

## 1. Architect

**Problem (one sentence):** A Tier-3 write's authority today rests on an
in-session `question` answer plus a text provenance footer with **no external
verification** — a compromised or confabulating session could fabricate "the
operator approved X"; fix it by making every Tier-3 write require a **fresh
(≤180s), content-bound, HMAC-signed approval token** minted only by an
out-of-band, tailnet-authenticated (Entra-backed) approval event, enforced by a
**code gate that fail-closes** (no valid fresh token bound to *this exact
change* ⇒ no write), executed by a single generalized signature-gated
`tier3-writer` role, with identity capture behind a pluggable resolver seam so
future OIDC providers plug in by registration alone.

**User:** the operator (approves out-of-band via a tailnet URL); the
`tier3-writer` executor role (writes Tier-3 only after the gate passes); the
future maintainer who registers a second `IdentityResolver` (e.g. direct Entra
OIDC) without editing the gate/mint/dispatcher; and every downstream reader of a
Tier-3 record, who can now check "an Entra-authenticated human approved this
exact content within a 3-minute window" independently of the session.

**Measurable success criteria:**

1. A new stdlib-only `src/gleipnir/approval/` subsystem exists providing:
   (a) a `token.py` with `mint_approval(...)` / `validate_approval(...)` reusing
   G-3.1's HMAC discipline, content-bound + identity-bound + freshness-bound at
   `APPROVAL_MAX_AGE_SECONDS = 180`; (b) an `identity/` resolver seam
   (`IdentityResolver` Protocol + `ResolvedIdentity` frozen dataclass +
   register/dispatch registry, **fail-closed on no-match**) + one registered
   `TailscaleResolver`; (c) a `gate.py` fail-closed write-gate; (d) a
   `server.py` stdlib `http.server` localhost listener.
2. The approval token is **content-bound to the exact resulting file content**:
   the token is minted (`server.py`) over the sha256 of the NEW proposed
   content the operator approved, and the gate **re-checks against that same
   resulting content** — a one-byte change to the pending Tier-3 content
   invalidates it (via `hmac.compare_digest` of the bound hash, the exact
   `validate()` discipline). **Critically, both mint-time and check-time hash
   the SAME byte-string definition ("the exact resulting file content"), NOT
   the live on-disk bytes at an arbitrary moment.** The gate CLI is handed the
   proposed resulting content directly (via `--content-file`, Decision 19) and
   hashes THAT — it never re-reads the live target file to derive the hash,
   because `tool.execute.before` fires before the write lands, so the live disk
   bytes are the pre-edit/base content and would never match the approved-new
   content (the mint-vs-check mismatch this revision fixes).
3. The token is **identity-bound**: the minted token carries the resolver's
   `approver_identity` + `provider`, and `validate_approval` checks it.
4. The token is **freshness-bound**: `age > 180` ⇒ invalid; future-dated ⇒
   invalid (the exact `validate()` freshness discipline, window overridden to
   180s).
5. The **write-gate fail-closes**: `gate.require_valid_token(...)` returns
   REFUSE on missing token, stale token, content-mismatch, identity-mismatch,
   wrong version, or unusable key — mirroring `verify/__main__.py:_cmd_check`
   (exit non-zero) and `preflight/boundary.decide()` (REFUSE-on-any-doubt) — and
   this REFUSE is turned into a **deterministic block on the actual write** by
   the `.gleipnir/plugins/tier3-gate.ts` `tool.execute.before` hook: on any
   `edit`/`write` whose target path is under the Tier-3 path-set, the hook
   computes **the exact resulting content this tool call will produce**, writes
   it to a temp file, and invokes the gate (via `python -m gleipnir.approval.gate
   --check <filePath> --content-file <temp> --token <token-file>`) which hashes
   that handed-in content and **throws to abort the tool call** unless the gate
   returns ALLOW. For a `write` call the resulting content is `output.args.content`
   directly; for an `edit` call the plugin **fails closed (throws) because
   opencode's fuzzy-replacer + formatter `edit` semantics are not reliably
   reproducible out-of-band** (Decision 20) — Tier-3 changes are therefore made
   via `write` (full-file, deterministic content). No in-framework agent
   (including a compromised session) can write a Tier-3 path without a valid
   fresh token bound to *the exact content being written*, because the block is
   enforced *around* the tool call by framework code, not *inside* any agent's
   cooperation.
6. The **resolver seam is extensible, proven by a test**: registering a second
   dummy resolver (a fake OIDC provider) results in it being selected/used
   **without any edit** to `gate.py`, `token.py`, or the resolver dispatcher —
   plus a source-scan test asserting the gate/mint/dispatcher source **never
   names a concrete identity provider** (no `tailscale`, `entra`, `oidc`).
7. The **dispatcher fails closed on no-match**: an unresolvable request rejects
   the approval (never defaults to an unauthenticated identity).
8. An **end-to-end** test proves: mint → gate → **refuse** without a token, and
   mint → gate → **accept** with a valid fresh content+identity-bound token; a
   stale token, a content-mismatched token, and an identity-mismatched token are
   each **refused**.
9. **No new Python runtime dependency** (`http.server`, `hmac`, `hashlib`,
   `json`, `dataclasses`, `subprocess` are all stdlib) — a positive property,
   held as a Stress-test criterion and by the enforcement-core stdlib-only
   discipline (`decisions/runtime-and-deps.md`).
10. The **THREE Tier-3 artifacts** — the executor role
    (`.gleipnir/agents/tier3-writer.md`), the write-block plugin
    (`.gleipnir/plugins/tier3-gate.ts`), and the **durable decision record**
    (`.gleipnir/decisions/tier3-signed-approval.md`) — are authored *as specified
    text in this plan* and applied by operator/build-mode — never written by any
    in-framework agent.
11. A **conformance test proves the plugin actually blocks** (T-21): with the
    real hook driven against a stub gate CLI in a temp dir (the
    `test_git_guard.mjs` shape), a Tier-3-path `edit`/`write` with no/expired
    token is aborted (throws) and one with a valid fresh token proceeds — this is
    what makes "no Tier-3 write path lacks the gate" (Decision 14/14a) real and
    falsifiable rather than a claim about code that no test exercises.

**Constraints (from the brief — FIXED, not re-litigated):**

- Route α only (resolver seam registers others later); 180s window; code-enforced
  fail-closed gate; all-Tier-3 executor scope; compose (gate + executor);
  tailnet-only (no public surface); E-2 approval-inbound slice only.
- **stdlib-only** enforcement core (`decisions/runtime-and-deps.md`) — Route α
  chosen partly *because* Route β (OIDC) would likely pull a token-validation
  dependency. `subprocess`-to-`tailscale`-CLI is stdlib-compatible; the
  `tailscale` CLI itself is a system-side environmental prerequisite, not a
  Python dependency.
- **Tier-3-cannot-self-apply:** no in-framework agent writes `agents/**` or
  `decisions/**`; the two Tier-3 artifacts are operator/build-mode hand-offs.
- **Cooperative-policy-until-closed:** until S-2 makes the key/gate
  agent-unreachable and S-3 preflight verifies it, the gate is honoured by the
  roster + the code path, not yet a substrate wall — labelled "authored, not yet
  closed" like the other guards (brief honesty ledger).

**Explicitly NOT in scope:** Route β (OIDC) implementation (seam only); Tier-2 /
G-4c (lessons/memory) generalization; general platform-webhook ingress (only
the approval-inbound E-2 slice); the `tailscale serve` configuration itself (an
operator hand-off, not code this plan builds); any change to `verify/marker.py`
(it is reused, not modified).

---

## 2. Trace

### Chosen module layout (Decision 10 — `[PLAN-STAGE JUDGMENT]`, flagged for spec-review)

```
src/gleipnir/approval/                    # NEW subsystem (sibling to broker/, verify/, preflight/)
  __init__.py                             # exports the public surface (mint_approval, validate_approval,
                                          #   require_valid_token, ApprovalToken, GateDecision, resolve_identity, register)
  token.py                                # ApprovalToken frozen dataclass + mint_approval / validate_approval
                                          #   (delegates HMAC to verify.marker discipline; APPROVAL_MAX_AGE_SECONDS=180)
  gate.py                                 # require_valid_token(...) -> GateDecision; fail-closed write-gate
                                          #   + __main__-style CLI: python -m gleipnir.approval.gate --check <path> --content-file <path> --token <file>
                                          #   (exit 0 = ALLOW, non-zero = REFUSE; mirrors verify/__main__.py:_cmd_check)
  __main__.py                             # argparse CLI dispatch for `python -m gleipnir.approval.gate`; hashes the
                                          #   --content-file bytes (the exact proposed RESULTING content), NOT a fresh
                                          #   read of --check (which is the file IDENTIFIER only) — Decision 19
  server.py                               # stdlib http.server localhost listener; request -> resolve -> mint
  identity/                               # the pluggable resolver seam (mirrors broker/git/content_handlers/)
    __init__.py                           # exports IdentityResolver, ResolvedIdentity, register, resolve_identity
    protocol.py                           # IdentityResolver Protocol + ResolvedIdentity frozen dataclass; NO provider logic
    registry.py                           # register(resolver) / resolve_identity(ctx); FAIL-CLOSED on no-match; NO provider logic
    tailscale_resolver.py                 # the ONE registered resolver: TailscaleResolver (Route α, subprocess `tailscale whois`)

bin/gleipnir-approval-server              # NEW thin operator shim (execs `python -m gleipnir.approval.server`)

.gleipnir/plugins/tier3-gate.ts           # NEW Tier-3 plugin (enforcement path-set E) — tool.execute.before
                                          #   edit/write write-block hook; shells out to the gate CLI, throws to abort.
                                          #   Applied by operator/build-mode ONLY (like sequence-gate.ts/git-guard.ts).

tests/test_approval_token.py             # NEW (stdlib-only)
tests/test_approval_identity_resolver.py # NEW (stdlib-only) — contract + fail-closed + extensibility + structural scan
tests/test_approval_gate.py              # NEW (stdlib-only) — fail-closed gate + CLI --check exit-code contract + end-to-end mint->gate->refuse/accept
tests/test_approval_server.py            # NEW (stdlib-only) — listener round-trip with injected fakes
tests/test_tier3_gate.mjs                # NEW (.mjs conformance test, test_git_guard.mjs shape) — the plugin
                                          #   actually blocks: no/expired token -> throws; valid fresh token -> proceeds;
                                          #   non-Tier-3 path -> pass-through
```

**Rationale (Decision 10):** approval capture is a distinct subsystem — a
network receiver + identity resolution + token-mint orchestration + a
write-gate — with a new blast radius (a persistent listener) that does not
belong inside `verify/` (marker CLI) or `preflight/` (boundary probe). The
`src/gleipnir/` convention is one directory per subsystem (`broker/`, `bus/`,
`engine/`, `ledger/`, `preflight/`, `sandbox/`, `verify/`); this adds one.
Spec-review should confirm or overturn.

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Source-of-truth role |
|---|---|---|---|---|
| Approval token type + mint/validate | NEW `src/gleipnir/approval/token.py` | source tree (under `src/`) | bounded `gleipnir-code` | `ApprovalToken` + `mint_approval`/`validate_approval`; reuses G-3.1 HMAC discipline. stdlib-only. |
| Write-gate + CLI | NEW `src/gleipnir/approval/gate.py` + `approval/__main__.py` | source tree | bounded `gleipnir-code` | `require_valid_token(...) -> GateDecision` (library) + `python -m gleipnir.approval.gate --check <path> --content-file <path> --token <file>` CLI (exit 0 ALLOW / non-zero REFUSE). **Hashes the `--content-file` bytes (the exact proposed resulting content), NOT a fresh read of `--check`** (which is the file identifier only) — the mint-vs-check fix, Decision 19. Fail-closed choke-point. stdlib-only. |
| **Write-block plugin (2nd Tier-3 artifact)** | NEW `.gleipnir/plugins/tier3-gate.ts` | **Tier-3 POLICY** (enforcement path-set `E`) | **operator / build-mode ONLY** | `tool.execute.before` hook on `edit`/`write`; routes on target path (`output.args.filePath`); if Tier-3, **computes the exact resulting content** (`write` ⇒ `output.args.content`; `edit` ⇒ **fail-closed throw**, Decision 20), writes it to a temp file, and shells out to the gate CLI with `--content-file <temp>`, **throwing to abort** on non-ALLOW. Mirrors `git-guard.ts`. The deterministic block the brief requires. |
| Listener | NEW `src/gleipnir/approval/server.py` | source tree | bounded `gleipnir-code` | stdlib `http.server`, bind `127.0.0.1`; request → resolve → mint. stdlib-only. |
| Resolver contract | NEW `src/gleipnir/approval/identity/protocol.py` | source tree | bounded `gleipnir-code` | `IdentityResolver` Protocol + `ResolvedIdentity`; NO provider logic. Mirrors `content_handlers/protocol.py`. |
| Resolver dispatcher | NEW `src/gleipnir/approval/identity/registry.py` | source tree | bounded `gleipnir-code` | `register`/`resolve_identity`; **fail-closed** on no-match; NO provider logic; imports no concrete resolver. Mirrors `content_handlers/registry.py` (inverted no-match). |
| The ONE resolver | NEW `src/gleipnir/approval/identity/tailscale_resolver.py` | source tree | bounded `gleipnir-code` | `TailscaleResolver` (Route α, `subprocess` `tailscale whois`). Registered at the server composition root, not in the dispatcher. |
| Package inits | NEW `approval/__init__.py`, `approval/identity/__init__.py` | source tree | bounded `gleipnir-code` | Public-surface re-exports (the reuse seam). |
| Operator start shim | NEW `bin/gleipnir-approval-server` | source tree (executable, Axis-1 disqualifier) | bounded `gleipnir-code` (hardened path — blast-radius reviewed) | `#!/bin/sh` exec into `python -m gleipnir.approval.server`; operator-run, not on any agent allowlist. Mirrors `bin/gleipnir-preflight`. |
| Token unit tests | NEW `tests/test_approval_token.py` | source tree | bounded `gleipnir-code` | Arbiter for mint/validate/freshness/content-binding/identity-binding. stdlib-only. |
| Resolver tests | NEW `tests/test_approval_identity_resolver.py` | source tree | bounded `gleipnir-code` | Arbiter for the contract, fail-closed dispatch, extensibility (2nd resolver), structural source-scan. |
| Gate + e2e tests | NEW `tests/test_approval_gate.py` | source tree | bounded `gleipnir-code` | Arbiter for fail-closed gate + mint→gate→refuse/accept end-to-end. |
| Server tests | NEW `tests/test_approval_server.py` | source tree | bounded `gleipnir-code` | Listener request→resolve→mint round-trip with injected fakes. |
| Plugin conformance test | NEW `tests/test_tier3_gate.mjs` | source tree | bounded `gleipnir-code` | Arbiter that the plugin BLOCKS: no/expired token ⇒ throws; valid fresh token ⇒ proceeds; non-Tier-3 path ⇒ pass-through. `test_git_guard.mjs` shape (real hook + stub CLI + temp dir). |
| **Executor role (the ONE Tier-3 code artifact)** | NEW `.gleipnir/agents/tier3-writer.md` | **Tier-3 POLICY** | **operator / build-mode ONLY** | `tier3-writer` frontmatter: deny-by-default, Tier-3 path-set `edit`/`write`, no `question`/git/bash/task, gate-preceded. Subsumes `decision-scribe`. |
| **Durable decision record** | NEW `.gleipnir/decisions/tier3-signed-approval.md` | **Tier-3 POLICY** | **operator / build-mode ONLY** | Records the converged design; narrows "no agent writes Tier-3, ever" to "only the signature-gated `tier3-writer`, only with a valid fresh token." |
| Boundary enforcement (unchanged) | `src/gleipnir/preflight/boundary.py` | source tree | — (NOT edited) | Already lists `agents/*.md`, `decisions/**`, `keys/**`, `goals/**`, `stage-role-map.md` in `ENFORCEMENT_PATHS` (168–222). No edit needed. |
| G-3.1 marker (unchanged) | `src/gleipnir/verify/marker.py` | source tree | — (NOT edited) | Reused, not modified. `token.py` imports/mirrors its discipline. |

**Critical Trace consequence:** the feature is *mostly* bounded `gleipnir-code`
territory (all `src/gleipnir/approval/**`, five test files including the `.mjs`
plugin conformance test, and the `bin/gleipnir-approval-server` shim — all under
`src/`, `tests/`, `bin/`, outside `.gleipnir/**` policy paths). The **three
Tier-3 operator/build-mode actions** are applying
`.gleipnir/agents/tier3-writer.md`, `.gleipnir/plugins/tier3-gate.ts` (the
write-block hook — enforcement path-set `E`), and
`.gleipnir/decisions/tier3-signed-approval.md`. All three are made explicit in
the Execution Workflow split table. Note the plugin `.ts` SOURCE is written by
`gleipnir-code` only insofar as it is *specified as text in this plan* — but
because `.gleipnir/plugins/**` is Tier-3, the actual file is **applied by
operator/build-mode**, never written by an in-framework agent, exactly like the
three existing plugins.

### The content-binding mechanism — mint-time vs check-time hash source (Decisions 19 + 20; the quality-review defect fix)

**The invariant both sides MUST honour:** `hmac.compare_digest(token.change_hash,
change_hash)` in `validate_approval` (`token.py:170`) only matches when both
hashes are computed over the **identical byte-string definition**. That
definition is fixed here as **"the exact resulting file content"** — the bytes
the Tier-3 file will hold *after* the approved write is applied.

- **Mint-time (`server.py`, unchanged in source but re-confirmed):**
  `capture_approval` computes `change_hash = compute_change_hash(pending_content)`
  where `pending_content` is the **raw bytes POSTed to `/approve`** — the NEW
  proposed content the operator reviewed and approved on the served page. This
  is already "the exact resulting content." **No `server.py` change is required**
  (verified: `server.py:53-56` hashes the posted body, `:88` mints over it) —
  the fix is entirely on the check side, which was hashing the *wrong* bytes.
- **Check-time (`__main__.py`, CHANGED):** the ORIGINAL bug —
  `_compute_change_hash(target_path)` hashed `target_path.read_bytes()`, the
  file's **live disk bytes at check-time**. Because `tier3-gate.ts` invokes the
  CLI from `tool.execute.before` (fires *before* the write lands), those bytes
  are always the **pre-edit/base** content, never the approved-new content ⇒
  the compare never matches ⇒ every legit edit refused. **Fix:** the CLI hashes
  content **handed to it** via a new `--content-file <path>` argument — the exact
  proposed resulting bytes the plugin computed — and `--check <filePath>` is
  retained purely as the file **identifier** (never re-hashed). `_cmd_check`
  keeps its `target_path.is_file()` fail-closed guard (there must be a real
  Tier-3 file being targeted) but derives the `change_hash` from
  `Path(args.content_file).read_bytes()`, not from `target_path`.
- **What the token path-scopes on:** `token.py`'s `_canonical_signing_input`
  (`:92-107`) signs `(version, change_hash, approver_identity, provider,
  minted_at)` — the **file path is NOT part of the signed input**; only the
  content hash binds content. So `--check <filePath>` carries no signed
  path-scoping today; it is purely the "which file" identifier + the
  is-there-a-real-target fail-closed guard. (If a future revision wants signed
  path-scoping, it adds the path to `_canonical_signing_input` on BOTH mint and
  validate — out of scope here; noted so the identifier role is not mistaken for
  a security binding it does not yet provide.)

**Resulting-content computation in `tier3-gate.ts` (Decision 20), per tool:**

- **`write`** — verified against opencode source
  `packages/opencode/src/tool/write.ts@dev`: the tool's parameters are
  `{content: string, filePath: string}` and the bytes written are exactly
  `params.content` (modulo a BOM-preservation detail that does not change the
  logical content). So the resulting content = `output.args.content`, handed to
  the CLI directly. **Certain and deterministic.**
- **`edit`** — verified against `packages/opencode/src/tool/edit.ts@dev`:
  opencode's `edit` does **NOT** perform a plain `oldString`→`newString`
  substring replace. `replace()` runs a **cascade of nine fuzzy replacers**
  (`SimpleReplacer`, `LineTrimmedReplacer`, `BlockAnchorReplacer`,
  `WhitespaceNormalizedReplacer`, `IndentationFlexibleReplacer`,
  `EscapeNormalizedReplacer`, `TrimmedBoundaryReplacer`, `ContextAwareReplacer`,
  `MultiOccurrenceReplacer`) with **Levenshtein-similarity thresholds (0.65)**,
  plus line-ending normalization/conversion, BOM handling, and a **post-write
  auto-`format.file()`** pass that can further mutate the bytes. **None of this
  is reliably reproducible out-of-band in TypeScript**, so the plugin **cannot
  be CERTAIN** of the resulting bytes. Per the existing fail-closed principle
  ("refuse rather than guess", Decision 5), the plugin **fails closed (throws)**
  for an `edit` to a Tier-3 path, with a message directing the operator to use
  `write` (full-file, deterministic) for Tier-3 changes. This keeps the
  content-binding **sound for every allowed path** — the alternative (guessing
  the edit result) risks either false-REFUSE or a computed content that DIFFERS
  from what opencode actually writes, which would defeat the binding entirely.

**Temp-file location (Decision 20):** the plugin writes the computed resulting
content to a fresh file under **Node's own `os.tmpdir()`** (via
`fs.mkdtempSync` + a unique name), **not** under `.gleipnir/var/tmp/`. Rationale:
(a) the content-file is a transient argument-passing vehicle consumed
synchronously by the `spawnSync` gate call and unlinked immediately after — it
is not a Gleipnir artifact and has no Tier-0 lifecycle meaning; (b) writing it
under `.gleipnir/var/tmp/` would put attacker-influenced proposed-write bytes
into the same directory the approval **tokens** live in, muddying that
directory's single purpose (minted tokens) and risking a name collision with
the `approval-*.json` glob the hook scans; (c) `os.tmpdir()` is per-process and
OS-cleaned, matching the vehicle's throwaway nature. The plugin **unlinks the
temp file in a `finally`** so a spawn failure never leaks it.

### The G-3.1 primitives this reuses (verified against real source this session)

Read from `src/gleipnir/verify/marker.py`:

- **`mint(tree_hash: str, key: bytes, minted_at: int | None = None) -> Marker`**
  (`marker.py:166`). Produces `Marker(version, tree_hash, minted_at, mac)` where
  `mac = hmac.new(key, _canonical_signing_input(...), DIGEST).hexdigest()`
  (`:176`). `Marker` is a `@dataclass(frozen=True)` with `to_json`/`from_json`
  (`:51`–`:83`).
- **`validate(marker, current_tree_hash, key, max_age_seconds=DEFAULT_MAX_AGE_SECONDS, now=None) -> bool`**
  (`marker.py:180`). Fail-closed. Checks, in order: `marker.version != MARKER_VERSION`
  ⇒ False (`:200`); `hmac.compare_digest(marker.tree_hash, current_tree_hash)`
  (content-binding, `:204`); recomputed-HMAC `hmac.compare_digest`
  (unforgeability, `:213`); freshness `age < 0 or age > max_age_seconds` ⇒ False
  (`:219`).
- **`_canonical_signing_input(version, tree_hash, minted_at) -> bytes`**
  (`marker.py:109`): `b"\x1f".join(p.encode("utf-8") for p in parts)` — the
  length-prefixed, ambiguity-free canonical form this plan's token input mirrors.
- **`load_key(key_file=None) -> bytes`** (`marker.py:86`) reads
  `GLEIPNIR_MARKER_KEY_FILE` (`KEY_ENV_VAR`, `:40`); fail-closed on absent/empty.
- **Constants:** `MARKER_VERSION = 1` (`:34`), `DIGEST = "sha256"` (`:35`),
  `DEFAULT_MAX_AGE_SECONDS = 3600` (`:38`).

**How `token.py` reuses this (Decision 11):** `mint_approval` builds a canonical
`\x1f`-joined input over `(APPROVAL_TOKEN_VERSION, change_hash,
approver_identity, provider, minted_at)` and HMACs it with the **same key**
(`load_key`, same `GLEIPNIR_MARKER_KEY_FILE`) using the same
`hmac.new(key, signing_input, "sha256").hexdigest()`. `validate_approval`
recomputes and `hmac.compare_digest`s the mac, `hmac.compare_digest`s the bound
`change_hash` AND `approver_identity`, and checks freshness against
`APPROVAL_MAX_AGE_SECONDS = 180`. This is the *same shape* as `Marker`/`validate`
— content-binding + identity-binding + unforgeability + freshness — but with
identity as a first-class field rather than smuggled into `tree_hash`, and
`verify/marker.py` is **not modified**.

### The `boundary.decide()` fail-closed pattern this mirrors (verified this session)

Read from `src/gleipnir/preflight/boundary.py`:

- **`decide(path_probes, key_state, *, override_ack=False, requested_mode=RequestedMode.UNCAGED) -> PreflightDecision`**
  (`:535`). Returns `PreflightDecision(verdict, label, reasons)`; `Verdict` is
  `{CLOSED, PROCEED_UNCLOSED, REFUSE}` (`:502`). It is fail-closed by
  construction: `if not path_probes: all_closed = False` (an empty evidence set
  is ambiguous ⇒ refuse, `:558`); ANY `NOT_CLOSED` path or non-`PRESENT` key ⇒
  not closed. This is the "REFUSE on any doubt" discipline `gate.py` mirrors.
- **`verify/__main__.py:_cmd_check`** (`:67`): missing marker ⇒ return 1
  (fail-closed, `:71`); key unavailable ⇒ return 3 (`:76`); invalid/stale ⇒
  return 1 (`:91`); valid ⇒ return 0 (`:89`). `gate.py`'s `GateDecision` mirrors
  this: absence/failure ⇒ REFUSE; only a fully-valid fresh content+identity-bound
  token ⇒ ALLOW.
- **`ENFORCEMENT_PATHS`** (`:168`–`:222`) already includes `agents/*.md`,
  `stage-role-map.md`, `decisions/**`, `goals/**`, `keys/**` (RO_AND_UNREADABLE)
  — so the boundary **already** protects the Tier-3 write *targets* against
  agent writes at the OS layer. **This plan does not edit `boundary.py`**; the
  new gate is a *distinct, complementary* check (does a fresh token authorise
  *this specific legitimate* write?) layered on top of the boundary's
  is-it-agent-unwritable check.

### The resolver seam contract/dispatcher (mirrors `content_handlers/`, verified this session)

Read from `src/gleipnir/broker/git/content_handlers/{protocol.py,registry.py}`
and `tests/test_broker_git_content_handlers.py`:

- **Contract half** — mirrors `protocol.py`'s `@runtime_checkable Handler(Protocol)`
  (`can_handle(content, hint) -> bool`, `process(content) -> ProcessedResult`)
  and frozen `ProcessedResult(content: str)`. This plan's:
  - `@dataclass(frozen=True) class ResolvedIdentity:` with exactly two fields —
    `identity: str` and `provider: str` — and **nothing token/gate-specific**
    (no `mac`, no `change_hash`, no `key`, no `token`). Structurally unreachable,
    not merely omitted (the same safety `protocol.py` documents and
    `TestStructuralSafety` proves via `inspect.signature`).
  - `@runtime_checkable class IdentityResolver(Protocol):` with exactly
    `can_resolve(self, request_ctx: RequestContext) -> bool` and
    `resolve(self, request_ctx: RequestContext) -> ResolvedIdentity`.
    (`RequestContext` is a small frozen dataclass carrying only the raw request
    facts a resolver needs — e.g. `remote_ip: str`, `headers: Mapping[str, str]`
    — and nothing token/gate-reachable.)
- **Dispatcher half** — mirrors `registry.py`'s module-level `_handlers: List`,
  `register(handler)`, `dispatch(...)` walking first-match-wins. This plan's
  `identity/registry.py`: module-level `_resolvers`, `register(resolver)`, and
  `resolve_identity(request_ctx) -> ResolvedIdentity` walking registered
  resolvers first-match-wins — but **FAIL-CLOSED on no-match**: where
  `content_handlers` returns `ProcessedResult(content=content)` unchanged
  (`registry.py:50`, benign), `resolve_identity` **raises `IdentityUnresolved`
  (⇒ the server rejects the approval)**. This module contains **no** reference
  to Tailscale/Entra/OIDC and imports **no** concrete resolver — identical
  open/closed discipline to `registry.py`.
- **The ONE resolver today:** `TailscaleResolver` in `tailscale_resolver.py`,
  registered at the server composition root (`server.py` calls
  `register(TailscaleResolver())`, analogous to a broker's `mcp_server.py`
  calling `register(...)`), never inside the dispatcher.

### Integrations map

```
Operator opens tailnet URL (tailscale serve fronts 127.0.0.1 listener)
   │
   ▼
approval/server.py  (stdlib http.server, bind 127.0.0.1)
   │  build RequestContext(remote_ip, headers) from the request
   │  identity = resolve_identity(ctx)          # identity/registry.py — FAIL-CLOSED on no-match
   │     └─ TailscaleResolver.can_resolve(ctx)? -> resolve(ctx):
   │           subprocess.run(["tailscale","whois","--json",ctx.remote_ip], ...) -> ResolvedIdentity(identity, "tailscale")
   │  change_hash = sha256(the exact NEW proposed resulting file content)  # POSTed body; shown as a diff in the served page
   │  token = mint_approval(change_hash, identity.identity, identity.provider, key=load_key())  # token.py — 180s
   │  write token -> .gleipnir/var/tmp/approval-<change_hash_prefix>.json   (Tier-0)
   ▼
Later, ANY agent attempts an edit/write to a Tier-3 path:
   opencode fires tool.execute.before  →  .gleipnir/plugins/tier3-gate.ts
      │  is output.args.filePath under the Tier-3 path-set?  (no ⇒ pass-through)
      │  yes ⇒ compute the EXACT resulting content this call will produce:
      │           • write  ⇒ resulting = output.args.content        (deterministic, verified vs write.ts@dev)
      │           • edit   ⇒ FAIL-CLOSED: the fuzzy-replacer+formatter edit path is not reproducible
      │                       out-of-band ⇒ THROW (use `write` for Tier-3 changes)  (Decision 20)
      │        write resulting content -> a temp file  (Node os.tmpdir(), see below)
      │  spawn: python -m gleipnir.approval.gate --check <filePath> --content-file <temp> --token <token-file>
      │           └─ __main__ hashes the --content-file bytes (NOT a fresh read of --check) -> change_hash
      │           └─ gate.require_valid_token(change_hash, approver_identity, token_path, key, max_age_seconds=180)
      │                 └─ validate_approval(token, change_hash, approver_identity, key, 180) -> bool
      │                       version + content-binding + identity-binding + HMAC + freshness
      │                 → exit 0 (ALLOW) only if fully valid+fresh AND the resulting-content hash matches
      │                    the approved-content hash; else non-zero (REFUSE)  (fail-closed)
      │  non-zero ⇒ the hook THROWS ⇒ opencode aborts the edit/write; the Tier-3 file is never touched.
      ▼
   exit 0 ⇒ fall through ⇒ opencode performs the edit/write; the temp file is unlinked afterwards.
```

- The resolver receives **only** a `RequestContext` and returns **only** a
  `ResolvedIdentity` — it never sees the key, the token, the change hash, or the
  gate (item-5-style structural unreachability).
- **No credential in code, no network dependency beyond the local `tailscale`
  CLI** — the listener binds localhost; `tailscale serve` (operator-configured)
  provides the tailnet transport; identity resolution is a local `subprocess`
  call to the already-installed `tailscale` CLI.

### Edge cases

1. **No token present** → `gate.require_valid_token` returns REFUSE (mirrors
   `_cmd_check` missing-marker ⇒ 1). No Tier-3 write.
2. **Stale token** (age > 180s) → `validate_approval` freshness check fails ⇒
   REFUSE.
3. **Future-dated token** (clock skew / forgery) → `age < 0` ⇒ REFUSE.
4. **Content mismatch** (token bound to a different change) →
   `hmac.compare_digest(change_hash, ...)` fails ⇒ REFUSE.
5. **Identity mismatch** (token bound to a different approver) → identity
   `compare_digest` fails ⇒ REFUSE.
6. **Key unavailable** (`GLEIPNIR_MARKER_KEY_FILE` absent/empty) → `load_key`
   raises `KeyUnavailable`; gate catches and returns REFUSE (never ALLOW).
7. **No resolver matches** the request → `resolve_identity` raises
   `IdentityUnresolved` ⇒ the server rejects the approval (never mints an
   unauthenticated token) — the fail-closed dispatcher no-match branch.
8. **`tailscale whois` fails / not installed / returns unparseable JSON** →
   `TailscaleResolver.resolve` raises (or `can_resolve` returns False) ⇒
   fail-closed rejection; the environmental prerequisite (CLI installed) is
   named in the operator hand-off.
9. **A second (future) resolver registered** → dispatched first-match-wins with
   no edit to gate/mint/dispatcher (the extensibility acceptance criterion).
10. **Tampered token file** (mac altered) → HMAC recompute mismatch ⇒ REFUSE.
11. **`edit`/`write` to a Tier-3 path with no/expired token** → `tier3-gate.ts`
    hook calls the gate CLI, gets a non-zero (REFUSE) exit, and **throws** ⇒
    opencode aborts the tool call; the Tier-3 file is never touched (the
    deterministic block).
12. **`edit`/`write` to a NON-Tier-3 path** (e.g. `src/**`, `tests/**`) →
    `tier3-gate.ts` sees the target path is not under the Tier-3 path-set and
    **passes through** (never runs the gate CLI, never throws) — normal writes
    are unobstructed, mirroring `git-guard.ts`'s `if (!GATED_TOOLS.has(...)) return`.
13. **Gate CLI missing / non-executable / spawn failure** → the hook **fails
    closed** (throws, distinct `PreflightUnavailable`-style broken-prerequisite
    message), never silently allows — mirrors `git-guard.ts`'s `accessSync` +
    spawn-error handling exactly.

---

## 3. Link — what was validated BEFORE building

Every fact below was re-read from the actual files this session:

- **L1 (G-3.1 signatures verified).** `mint`/`validate`/`_canonical_signing_input`/
  `load_key`/`Marker` read at `marker.py` lines 166, 180, 109, 86, 51; constants
  `MARKER_VERSION=1`/`DIGEST="sha256"`/`DEFAULT_MAX_AGE_SECONDS=3600`/`KEY_ENV_VAR`
  at 34/35/38/40. `validate` is fail-closed with content-binding + HMAC +
  freshness exactly as the brief claims. Reuse-not-modify confirmed.
- **L2 (boundary.decide fail-closed verified).** `decide(...) -> PreflightDecision`
  at `boundary.py:535`; `Verdict.{CLOSED,PROCEED_UNCLOSED,REFUSE}` at 502; empty
  evidence ⇒ not-closed at 558. `ENFORCEMENT_PATHS` (168–222) already covers all
  Tier-3 write targets — so the OS-layer protection exists and `boundary.py`
  needs **no edit**. The new gate is complementary.
- **L3 (content_handlers template verified).** `protocol.py`
  (`@runtime_checkable Handler(Protocol)`, frozen `ProcessedResult`),
  `registry.py` (module `_handlers`, `register`, `dispatch` first-match-wins,
  **no-match returns unchanged**), and `__init__.py` re-export surface all read.
  The dispatcher no-match posture is benign-passthrough — **must be inverted to
  fail-closed** for identity (Decision 13; brief).
- **L4 (structural-test template verified).** `tests/test_broker_git_content_handlers.py`
  read: `TestStructuralSafety` uses `inspect.signature`; `TestExtensibility`
  registers a `_StubHandler` defined *in the test module* and asserts no edit to
  `registry.py`/handler needed; `TestRegistrySingleResponsibility` uses
  `inspect.getsource` for a source-scan of forbidden tokens; the
  `_isolated_registry` fixture does `monkeypatch.setattr(registry_module,
  "_handlers", [])`. This plan's resolver tests mirror all four patterns.
- **L5 (no existing approval subsystem).** `src/gleipnir/` = `broker/ bus/
  engine/ ledger/ preflight/ sandbox/ verify/`; `grep approval src/gleipnir`
  returns nothing. `approval/` is net-new; **there is no code Tier-3 write call
  site today** — this plan builds the first (pre-flight finding 1).
- **L6 (key exists — no new key).** `.gleipnir/keys/marker.key` present on disk;
  `keys/README.md` confirms it is the G-3.1 HMAC key, provisioned out of band,
  Tier-3, `chmod 600` floor. The approval token reuses it via
  `GLEIPNIR_MARKER_KEY_FILE`. No new key created. Confirmed.
- **L7 (bin/ thin-shim precedent).** `bin/gleipnir-preflight` read: `#!/bin/sh`,
  resolves repo root, execs `python -m gleipnir.preflight`, run by the operator,
  **not on any agent allowlist**, "a guard whose activation is validated by the
  population it guards is the G-3 forgeable-evidence failure" — so
  `bin/gleipnir-approval-server` follows this shape and is likewise off every
  agent allowlist.
- **L8 (stdlib-only confirmed).** `http.server`, `hmac`, `hashlib`, `json`,
  `dataclasses`, `subprocess`, `typing`, `argparse` are all Python stdlib. No new
  Python dependency enters (`decisions/runtime-and-deps.md` satisfied). The
  `tailscale` CLI is a system-side environmental prerequisite (operator
  hand-off), not a Python package.
- **L9 (the plugin-hook write-block mechanism verified against real source this
  session).** Read `.gleipnir/plugins/{sequence-gate.ts,git-guard.ts,advance-hook.ts}`
  and `.gleipnir/plans/hook-probe-findings.md`:
  - **`tool.execute.before` can throw to abort the tool call** — confirmed
    verbatim in `hook-probe-findings.md` Point 3 (the documented `.env`-protection
    example) and used in production by BOTH `sequence-gate.ts` (throws `GateAbort`)
    and `git-guard.ts` (throws `GitGuardAbort`). This is a real, already-used
    abort channel on THIS hook — distinct from the after-hook's unverified-mutation
    status.
  - **The target path is `output.args.filePath`** for file tools — the documented
    example is exactly `input.tool === "read" && output.args.filePath.includes(".env")`
    (`hook-probe-findings.md` line 40/156). So routing on the **target path** is
    directly supported by the before-hook input shape
    (`{tool, sessionID, callID}` + mutable `output.args`).
  - **The before-hook input does NOT carry the acting-agent identity** (only
    `task` calls expose the *delegated-to* agent via `output.args.subagent_type`,
    which is the wrong signal for an `edit`/`write`). Therefore the review's
    recommended **path-based** routing is not just more robust but the *only*
    reliable form: gate on "is the target under the Tier-3 path-set", which gates
    **every** agent's write to a Tier-3 path, not merely `tier3-writer`'s.
  - **The shell-out-to-a-`bin`/CLI-and-map-exit-codes pattern is precedented** in
    `git-guard.ts` (`spawnSync(cli, ["config-scan"])`, `decideFromExit`, throw on
    REFUSE, distinct `PreflightUnavailable` for a broken tool). `tier3-gate.ts`
    reuses this shape against `python -m gleipnir.approval.gate --check`.
  - **The `.mjs` conformance-test layer is precedented** — `tests/test_git_guard.mjs`
    drives the real hook against a stub CLI in a temp dir; `tests/test_tier3_gate.mjs`
    mirrors it. **Conclusion: the wiring is feasible on the current substrate; the
    plugin path (Decision 14a) is taken, NOT the downgrade-to-manual path.**

- **L10 (the mint-vs-check content-hash defect + the opencode tool schemas
  verified against real source this session).** Read
  `src/gleipnir/approval/{__main__.py,gate.py,token.py,server.py}` and
  `tests/test_approval_gate.py` in full, and opencode's authoritative tool
  schemas `packages/opencode/src/tool/{write.ts,edit.ts}@dev`:
  - **Defect confirmed:** `__main__.py:_compute_change_hash` (`:39-45`) hashes
    `path.read_bytes()` — the live disk bytes; `_cmd_check` (`:80`) uses that as
    the check-time `change_hash`. `server.py:compute_change_hash` (`:53-56`)
    hashes the POSTed pending content (the new approved content).
    `token.py:validate_approval` (`:170`) requires
    `hmac.compare_digest(token.change_hash, change_hash)`. Since
    `tool.execute.before` fires before the write lands, the check-time disk
    bytes are the base content, so the two hashes diverge for any genuine edit —
    the bug exactly as reviewed. The **test suite hid it** (`test_approval_gate.py:169-170`,
    `:266`) because the CLI "allow" tests hash `target.read_bytes()` of a
    **never-mutated file**, so mint-time and check-time coincide by construction.
  - **`write` args:** `Parameters = {content, filePath}`; the written bytes are
    exactly `params.content` (`write.ts@dev`). ⇒ resulting content =
    `output.args.content`, deterministic.
  - **`edit` args:** `{filePath, oldString, newString, replaceAll?}`; `replace()`
    runs a **9-replacer fuzzy cascade with Levenshtein thresholds** + line-ending
    normalization + BOM handling + a post-write `format.file()` pass
    (`edit.ts@dev`) — NOT a plain substring replace, and **not reliably
    reproducible out-of-band**. ⇒ `edit` to a Tier-3 path **fails closed**
    (Decision 20). This is the decisive fact behind the `edit`-refuse choice —
    it is not conservatism for its own sake, it is that the resulting bytes are
    genuinely unknowable to the plugin.

**Gate rule:** No hard Tier-3-ordering gate as in `broker-mcp.md` — no new
Python dependency, so no `runtime-and-deps.md` amendment. The only ordering
constraints are the standard test-first one (Assemble) and the Tier-3
hand-off: the two Tier-3 artifacts (`tier3-writer.md`, the decision record) are
applied by operator/build-mode after the code + tests are green (they are what
*authorises* the executor, so they land at rollout, not mid-build).

---

## 4. Assemble — intended build order

Ordered so (i) tests precede implementation (Axiom 1 — the test is the arbiter),
(ii) the generic resolver seam + token primitive land before the gate/server
that compose them, (iii) the operator start-shim lands after the server it
execs, and (iv) the two Tier-3 hand-offs are sequenced explicitly at rollout.

**Step 1 — [code] Write FAILING tests first (test-first, Axiom 1).** All four
stdlib-only test files, EXPECTED TO FAIL (ImportError — `approval/` absent):
- `tests/test_approval_token.py`: mint→validate happy path; content-mismatch
  invalid; identity-mismatch invalid; stale (age > 180) invalid; future-dated
  invalid; wrong version invalid; key-unavailable handled fail-closed; the 180s
  window is honoured (a token minted at `now-179` valid, at `now-181` invalid).
- `tests/test_approval_identity_resolver.py`: `ResolvedIdentity` is frozen and
  has exactly `{identity, provider}` (no token/gate fields) via `dataclasses.fields`;
  `IdentityResolver` protocol exposes exactly `{can_resolve, resolve}` via `dir`;
  `resolve` signature via `inspect.signature`; **fail-closed dispatch** —
  `resolve_identity` with no matching resolver **raises** `IdentityUnresolved`
  (NOT return-unchanged); **extensibility** — register a second dummy resolver
  (defined in the test module) for its own context and assert it is selected
  **with no edit** to `gate.py`/`token.py`/`registry.py`; **structural
  source-scan** (`inspect.getsource`) asserting `registry.py`, `gate.py`,
  `token.py` source text contains no `tailscale`/`entra`/`oidc` token.
- `tests/test_approval_gate.py`: `require_valid_token` returns REFUSE on missing
  token, stale token, content-mismatch, identity-mismatch, key-unavailable;
  ALLOW only on a fully-valid fresh content+identity-bound token; the
  **end-to-end** mint→gate→refuse-without-token and mint→gate→accept-with-valid-token.
  **CLI tests take `--content-file` (not a live re-read of `--check`).** **T-22
  content-divergence (the defect regression test):** mint a token over content
  `X`; run the CLI with `--check <target>` (whose disk bytes may be the BASE, a
  DIFFERENT string) and `--content-file <file containing X>` ⇒ **ALLOW**; then
  run it with `--content-file <file containing X-with-one-byte-changed>` ⇒
  **REFUSE** — proving the gate binds to the handed-in *resulting* content, not
  the live disk bytes of `--check`. This test MUST make the disk bytes of
  `--check` DIFFER from the approved content `X`, so it genuinely exercises
  divergence (the original suite did not — it re-read a never-mutated file).
- `tests/test_approval_server.py`: with an injected fake resolver and fake key,
  a request round-trips to a minted token bound to the shown change hash; an
  unresolvable request is rejected (no token minted).
- `tests/test_tier3_gate.mjs` (the `.mjs` plugin conformance test, mirroring
  `tests/test_git_guard.mjs`): drives the REAL `Tier3Gate({directory})["tool.execute.before"]`
  hook against a **stub gate CLI** in a temp dir. Asserts (a) a **`write`** to a
  Tier-3 path with the stub CLI exiting non-zero (no/expired token) ⇒ the hook
  **throws** (abort); (b) a **`write`** with the stub CLI exiting 0 (valid fresh
  token) ⇒ the hook does **not** throw (proceeds); (c) an `edit`/`write` to a
  NON-Tier-3 path ⇒ **pass-through** (stub CLI never invoked, no throw); (d)
  stub CLI missing / non-executable ⇒ fail-closed throw (broken-prerequisite
  class); (e) **an `edit` to a Tier-3 path ⇒ fail-closed throw WITHOUT invoking
  the stub CLI** (Decision 20: `edit` result is not reproducible ⇒ `resultingContentFor`
  throws before any spawn — assert the stub CLI was never called); (f) a
  **`write`** to a Tier-3 path stub-exiting 0 ⇒ the hook writes the resulting
  content (`output.args.content`) to a temp file and passes it as
  `--content-file` (assert via a stub CLI that records its argv that
  `--content-file` is present and its file contains exactly `output.args.content`,
  and that the temp file is unlinked afterward). This is the test that makes
  Decision 14/14a AND the content-binding (Decisions 19 + 20) falsifiable
  (Architect criterion 11 / T-21).
- The Python test files MUST fail (modules absent); the `.mjs` test MUST fail
  (plugin absent) — that is the point.

**Step 2 — [code] Implement the resolver seam** `approval/identity/`:
- `protocol.py`: `RequestContext` + `ResolvedIdentity` frozen dataclasses;
  `IdentityResolver` `@runtime_checkable Protocol` (`can_resolve`/`resolve`).
  **No provider logic.**
- `registry.py`: module-level `_resolvers`; `register(resolver)`;
  `resolve_identity(ctx)` first-match-wins, **raises `IdentityUnresolved` on
  no-match**. **No provider logic; imports no concrete resolver.**
- `__init__.py`: re-export `IdentityResolver`, `ResolvedIdentity`,
  `RequestContext`, `register`, `resolve_identity`, `IdentityUnresolved`.

**Step 3 — [code] Implement the token primitive** `approval/token.py`:
- `APPROVAL_TOKEN_VERSION = 1`, `APPROVAL_MAX_AGE_SECONDS = 180` (named
  constants). `ApprovalToken` frozen dataclass (`version, change_hash,
  approver_identity, provider, minted_at, mac`) with `to_json`/`from_json`.
- `mint_approval(...)` and `validate_approval(...)` reusing the G-3.1 HMAC
  discipline (canonical `\x1f`-joined input, `hmac.new(...sha256).hexdigest()`,
  `hmac.compare_digest` for mac + change_hash + identity, freshness at 180s).
  Reads the key via `verify.marker.load_key` / `GLEIPNIR_MARKER_KEY_FILE`.
  `verify/marker.py` is **not modified**.

**Step 4 — [code] Implement the write-gate + CLI** `approval/gate.py` + `approval/__main__.py`:
- `GateDecision` (ALLOW/REFUSE + reasons); `require_valid_token(...)` reads the
  token by path, `validate_approval`s it against the exact change_hash +
  approver_identity, returns REFUSE on any failure/absence (mirrors
  `_cmd_check` + `boundary.decide`). **No provider logic.** (`gate.py` is
  unchanged by the content-hash fix — it already takes `change_hash` as a
  parameter; only its *source* in the CLI changes.)
- `approval/__main__.py`: an `argparse` CLI **`python -m gleipnir.approval.gate
  --check <path> --content-file <path> --token <token-file>`**. It derives the
  `change_hash` for the pending write from **`--content-file` bytes**
  (`Path(args.content_file).read_bytes()`), **NOT** from a fresh read of
  `--check` (Decision 19 — the mint-vs-check fix). `--check <path>` is retained
  as the file **identifier** and its `is_file()` fail-closed guard (there must
  be a real Tier-3 target); `--content-file` is `required` and its own
  fail-closed guard (missing/unreadable content-file ⇒ non-zero). Then calls
  `require_valid_token(...)` and exits **0 on ALLOW, non-zero on REFUSE** — the
  exit-code contract the plugin consumes (mirrors `verify/__main__.py:_cmd_check`'s
  0/1/3 shape). Missing token / key-unavailable / missing content-file ⇒
  non-zero (fail-closed). **Update `tests/test_approval_gate.py`'s CLI tests to
  pass `--content-file` and to add the content-divergence test (T-22 below).**

**Step 5 — [code] Implement the resolver + listener:**
- `approval/identity/tailscale_resolver.py`: `TailscaleResolver` —
  `can_resolve(ctx)` true when a tailnet identity is resolvable;
  `resolve(ctx)` runs `subprocess.run(["tailscale","whois","--json",
  ctx.remote_ip], capture_output=True, text=True, timeout=...)`, parses JSON,
  returns `ResolvedIdentity(login, "tailscale")`; fail-closed on any error.
- `approval/server.py`: stdlib `http.server` bound `127.0.0.1`; the composition
  root that calls `register(TailscaleResolver())`; per request builds
  `RequestContext`, calls `resolve_identity`, computes `change_hash`, mints,
  writes the token to `var/tmp/`. The `subprocess`/network edges are injectable
  so tests use fakes.
- `approval/__init__.py`: re-export the public surface.
- Run Step-1 tests to green (all stdlib-only, default `python` profile).

**Step 6 — [code] Add the operator start shim** `bin/gleipnir-approval-server`
(`#!/bin/sh`, execs `python -m gleipnir.approval.server`), mirroring
`bin/gleipnir-preflight`; NOT added to any agent allowlist.

**Step 7 — [spec, applied Tier-3] Specify the write-block plugin**
`.gleipnir/plugins/tier3-gate.ts` (its full source is authored as text under the
hardened pipeline; the FILE is applied by operator/build-mode at rollout, like
`sequence-gate.ts`/`git-guard.ts` — no in-framework agent writes
`.gleipnir/plugins/**`). Shape (mirrors `git-guard.ts` structurally):
- Exports `Tier3Gate = async ({ directory }) => ({ "tool.execute.before": ... })`.
- On `input.tool` ∈ `{"edit","write"}`, read `output.args.filePath`; if it is
  NOT under the Tier-3 path-set (`.gleipnir/agents/**`, `.gleipnir/skills/**`,
  `.gleipnir/goals/**`, `.gleipnir/decisions/**`, `.gleipnir/keys/**`,
  `.gleipnir/stage-role-map.md`, `.gleipnir/plugins/**`) ⇒ **return
  (pass-through)**. Otherwise **compute the exact resulting content this call
  will produce** (Decision 20): for `input.tool === "write"`, resulting content
  = `output.args.content` (verified vs `write.ts@dev`); for
  `input.tool === "edit"`, **throw to abort (fail-closed)** — opencode's fuzzy
  `edit` path is not reproducible out-of-band, so a Tier-3 change must use
  `write`. Write the resulting content to a temp file under `os.tmpdir()`
  (`fs.mkdtempSync`), then shell out (`spawnSync`) to
  `python -m gleipnir.approval.gate --check <filePath> --content-file <temp>
  --token <token-file>` in `directory`, **unlink the temp file in a `finally`**,
  and **throw to abort** on any non-zero exit (fail-closed); distinct
  broken-prerequisite class if the CLI is missing/non-executable (`accessSync`
  pre-check, mirroring `git-guard.ts`). ALWAYS-ACTIVE (like `git-guard.ts`, NOT
  arming-gated — a Tier-3 write must be gated in every session). Run
  `tests/test_tier3_gate.mjs` to green.

**Step 8 — [Tier-3 / operator or build-mode] Apply the three Tier-3 artifacts**
(named verbatim / specified as text in this plan; NOT written by any agent):
- `.gleipnir/agents/tier3-writer.md` (the signature-gated executor).
- `.gleipnir/plugins/tier3-gate.ts` (the write-block hook — Step-7 source).
- `.gleipnir/decisions/tier3-signed-approval.md` (the durable record).
- Configure `tailscale serve` to front the listener (operator OS act).
- Confirm `GLEIPNIR_MARKER_KEY_FILE` key exists `chmod 600` (already present).

**Assemble step order (summary):**
`1 (code: FAILING tests — token + resolver + gate/e2e incl. T-22 content-divergence + server + tier3-gate.mjs plugin) →
2 (code: identity/ resolver seam, fail-closed dispatcher) →
3 (code: token.py mint/validate, 180s reuse of G-3.1) →
4 (code: gate.py fail-closed write-gate + __main__.py --check IDENTIFIER + --content-file HASH-SOURCE CLI) →
5 (code: TailscaleResolver + server.py listener; run tests green) →
6 (code: bin/gleipnir-approval-server operator shim) →
7 (spec: tier3-gate.ts write-block plugin source — resulting-content compute [write=content, edit=fail-closed] + --content-file; run tier3-gate.mjs green) →
8 (Tier-3 operator/build-mode: apply tier3-writer.md + tier3-gate.ts + decision
record; configure tailscale serve; confirm key)`

---

## 5. Stress-test — acceptance checks

Each is concrete and checkable (not "it works"). The four Python test files are
stdlib-only (no `mcp`), collected under the default `python` profile; the fifth,
`tests/test_tier3_gate.mjs`, is a Node `--test` `.mjs` conformance test run
exactly as `tests/test_git_guard.mjs` (`node --test tests/test_tier3_gate.mjs`).

- **T-1 (mint→validate happy path) — unit.** `validate_approval(mint_approval(
  h, id, prov, key), h, id, key, 180)` is True for a just-minted token.
- **T-2 (content-binding) — unit.** A token minted for `change_hash=h1`
  validated against `h2 != h1` returns False (a one-byte change to the pending
  content flips the hash). Mirrors `validate`'s `compare_digest` content-binding.
  (T-2 tests the token primitive; T-22 tests that the CLI hashes the RIGHT
  bytes — the two together close the mint-vs-check defect.)
- **T-3 (identity-binding) — unit.** A token minted for `approver="alice"`
  validated against `approver="bob"` returns False.
- **T-4 (freshness, lower boundary) — unit.** A token with
  `minted_at = now - 179` validates True at `max_age_seconds=180`; a token with
  `minted_at = now - 181` validates **False** (pins the 180s window).
- **T-5 (future-dated rejected) — unit.** `minted_at = now + 5` ⇒ `age < 0` ⇒
  False.
- **T-6 (unforgeability) — unit.** A token whose `mac` is altered by one hex
  char validates False; a token minted with the wrong key validates False under
  the right key.
- **T-7 (wrong version rejected) — unit.** `version != APPROVAL_TOKEN_VERSION`
  ⇒ False.
- **T-8 (gate fail-closed — no token) — unit.** `require_valid_token` with a
  missing token path returns `GateDecision.REFUSE` (never ALLOW). Mirrors
  `_cmd_check` missing-marker ⇒ exit 1.
- **T-9 (gate fail-closed — key unavailable) — unit.** With
  `GLEIPNIR_MARKER_KEY_FILE` unset/empty, the gate returns REFUSE (catches
  `KeyUnavailable`), never ALLOW.
- **T-10 (end-to-end refuse-without-token) — unit.** Full path: no token minted
  ⇒ `require_valid_token(...)` REFUSE.
- **T-11 (end-to-end accept-with-valid-token) — unit.** Full path:
  `mint_approval` → write token → `require_valid_token(...)` ALLOW; and a stale /
  content-mismatched / identity-mismatched token each ⇒ REFUSE.
- **T-12 (resolver contract structural safety, type-level) — unit.**
  `dataclasses.fields(ResolvedIdentity) == {identity, provider}` (no
  token/gate/key/change_hash field); `IdentityResolver` protocol members ==
  `{can_resolve, resolve}`; `inspect.signature(TailscaleResolver.resolve)` takes
  exactly one non-self `RequestContext` param and returns `ResolvedIdentity`.
  **Pass = token/gate internals are unreachable through the contract by
  construction, not by convention.** Mirrors `TestStructuralSafety`.
- **T-13 (dispatcher fail-closed on no-match) — unit.** `resolve_identity` with
  an empty registry (or no matching resolver) **raises `IdentityUnresolved`** —
  it does NOT return a default/unauthenticated identity. This is the deliberate
  inversion of `content_handlers.dispatch`'s benign passthrough.
- **T-14 (extensibility — MANDATORY) — unit.** Register a second dummy resolver
  (a fake OIDC provider, defined **in the test module**) matching its own
  `RequestContext`; assert (a) it is selected/used for its context, (b)
  `TailscaleResolver` still resolves its own context, and (c) **no edit** to
  `gate.py`, `token.py`, or `identity/registry.py` was needed (the dummy lives
  entirely in the test). **This is the concrete proof a future Route β / OIDC
  provider plugs in by registration alone.** Mirrors `TestExtensibility`.
- **T-15 (structural source-scan) — unit.** `inspect.getsource` of
  `identity/registry.py`, `gate.py`, and `token.py` contains **none** of the
  tokens `tailscale`, `entra`, `oidc` (case-insensitive) — proving the
  gate/mint/dispatcher name no concrete identity provider. Mirrors
  `TestRegistrySingleResponsibility`.
- **T-16 (no new dependency / stdlib-only) — meta/grep check.** No new Python
  package is added (no `pyproject.toml` dependency edit); the new modules import
  only `http.server`, `hmac`, `hashlib`, `json`, `dataclasses`, `subprocess`,
  `typing`, and `gleipnir.verify.marker`. A grep confirms no third-party import.
- **T-17 (server round-trip, isolated) — unit.** With an injected fake resolver
  (returns a fixed `ResolvedIdentity`) and injected fake key, a request produces
  a token bound to the shown `change_hash` + that identity; an unresolvable
  request (fake resolver raises / no resolver) yields **no token** and a rejected
  response.
- **T-18 (`tailscale whois` invocation shape) — unit.** With `subprocess.run`
  injected/monkeypatched, `TailscaleResolver.resolve` invokes
  `["tailscale","whois","--json", remote_ip]` and parses the login from JSON;
  a non-zero exit / unparseable output ⇒ fail-closed (raises / `can_resolve`
  False), never a silent default identity.
- **T-19 (tier integrity — authorship check).** No bounded `gleipnir-code` agent
  wrote any Tier-3 path. The two Tier-3 artifacts
  (`.gleipnir/agents/tier3-writer.md`, `.gleipnir/decisions/tier3-signed-approval.md`)
  were applied by operator/build-mode (Step 7); all code/test/shim writes were
  confined to `src/gleipnir/approval/**`, `tests/**`, `bin/**` (outside
  `.gleipnir/**` policy paths). **`verify/marker.py` and `preflight/boundary.py`
  are unchanged.**
- **T-20 (Tier-3 agent frontmatter negative-check — hardened path).** For the
  `quality` stage: the `tier3-writer.md` `permission:` block grants exactly the
  intended Tier-3 path-set and **NOT** an over-broad glob — e.g. the executor's
  `edit`/`write` allow-list names the six Tier-3 path prefixes, and a `"**"` or
  bare-`.gleipnir/**` allow is **NOT present**; it holds no `question`, no
  `bash`, no `task`, no git. (Negative-check attestation form per
  `stage-role-map.md` hardened path — see Execution Workflow.)
- **T-21 (the plugin actually BLOCKS — the deterministic write-block proof) —
  `.mjs` conformance.** `tests/test_tier3_gate.mjs` drives the REAL
  `Tier3Gate({directory})["tool.execute.before"]` hook against a **stub gate
  CLI** in a temp dir (the `test_git_guard.mjs` shape — real hook, stub `bin`,
  no live gate run needed). Asserts:
  (a) a **`write`** whose `output.args.filePath` is a Tier-3 path, with the
  stub gate CLI exiting **non-zero** (no token / expired-stale token) ⇒ the hook
  **throws** (the tool call is aborted — the Tier-3 file is never written);
  (b) the same `write` with the stub CLI exiting **0** (valid fresh token) ⇒ the
  hook does **NOT** throw (the write proceeds);
  (c) an `edit`/`write` to a **non-Tier-3** path (e.g. `src/foo.py`) ⇒
  **pass-through**: the gate CLI is never invoked and the hook never throws;
  (d) a **missing / non-executable** gate CLI ⇒ **fail-closed** throw
  (broken-prerequisite class, distinct from a policy REFUSE), mirroring
  `test_git_guard.mjs`'s `PreflightUnavailable` cases;
  (e) **an `edit` to a Tier-3 path ⇒ fail-closed throw and the gate CLI is
  NEVER invoked** — `resultingContentFor` throws for `edit` before any spawn
  (Decision 20: the opencode fuzzy-`edit` result is not reproducible
  out-of-band, so it is refused rather than guessed; assert the stub CLI's
  invocation count is zero);
  (f) **content-binding wiring — a `write` to a Tier-3 path stub-exiting 0
  passes the resulting content via `--content-file`** — using a stub CLI that
  records its argv and the `--content-file` contents, assert the invocation
  carried `--content-file`, that the file's bytes equalled `output.args.content`
  exactly (the approved resulting content, NOT the target's disk bytes), and
  that the temp file no longer exists after the call (unlinked in `finally`).
  This is the `.mjs`-level complement to T-22 (which proves the *CLI* hashes the
  handed-in content): (f) proves the *hook* hands over the right content.
  **This is the test that makes Decision 14/14a's "no Tier-3 write path lacks
  the gate" claim, AND the Decision 19/20 content-binding, real and
  falsifiable** (Architect criterion 11) — it is referenced by Design-Principles
  falsifiability claim (a). Without it, those claims are vacuous; with it, a
  regression that removed the throw, mis-scoped the Tier-3 path-set, fail-opened
  on a missing CLI, silently allowed a Tier-3 `edit` (case e), or stopped
  passing the resulting content via `--content-file` (case f) would fail T-21.
- **T-22 (mint-vs-check content-divergence — the quality-review-defect
  regression test; the criterion this revision adds) — CLI end-to-end.** In
  `tests/test_approval_gate.py`, exercise the CLI over content that *genuinely
  diverges from the target file's live disk bytes* — the exact case the original
  suite never did (it re-read a never-mutated file, so mint-time and check-time
  hashed the same bytes by construction, masking the defect). Concretely:
  1. Pick an approved-content byte-string `X` (e.g. `b"approved NEW content"`)
     and write the target file `--check <target>` with a **DIFFERENT** base
     byte-string `B != X` (e.g. `b"pre-edit BASE content"`), so the live disk
     bytes at check-time are `B`, never `X` — reproducing the
     `tool.execute.before`-fires-before-the-write timing.
  2. Mint a fresh token over `sha256(X)` (the `server.py` `compute_change_hash`
     definition — the approved NEW content).
  3. Run the CLI with `--check <target> --content-file <file containing X>
     --token <token>` ⇒ **exit 0 (ALLOW)** — proving the gate binds to the
     handed-in *resulting* content `X`, NOT the live disk bytes `B` of `--check`
     (which, if the old `read_bytes()` path were still in place, would hash `B`,
     mismatch the token, and wrongly REFUSE a legitimately-approved write).
  4. Run the CLI again with `--content-file <file containing X′>` where `X′` is
     `X` with **exactly one byte changed** ⇒ **exit 1 (REFUSE)** — proving a
     one-byte divergence in the *resulting* content invalidates the token
     (Architect criterion 2), the bait-and-switch hole is closed, and the CLI is
     not silently binding to `B`.
  **Pass = the CLI hashes the `--content-file` bytes (the approved resulting
  content), never a fresh read of `--check`; a genuine content divergence
  between the approved bytes and the on-disk base is exercised end-to-end.**
  T-22 is the CLI-level complement to T-2 (which tests the token primitive's
  content-binding): T-2 proves `validate_approval` compares hashes; T-22 proves
  the CLI feeds it the *right* hash-source. Together they close the mint-vs-check
  defect. Without T-22, a regression reverting `__main__.py` to
  `target_path.read_bytes()` would pass the entire existing suite (which only
  tests never-mutated files) yet break every legitimate Tier-3 edit in
  production — exactly the false-green this criterion exists to catch.

**For the orchestrator sequencing this plan.** ATLAS/GOTCHA already ran (this
plan). The pipeline from here is the **full hardened 8-stage pipeline**:
`spec-review → test → code → quality → git → gate`. This is
**Tier-3-enforcement-bearing** (`P` touches `.gleipnir/agents/**`,
`.gleipnir/decisions/**`, and adds a new agent `permission:` block — Axis 1 path
rule + Axis 2(b) content rule), so it is **NOT** the light prose/config track.

**Hardened-path dual-review requirement (flag for `quality-reviewer`).** At the
`quality` stage, `quality-reviewer` MUST run **two distinct passes with two
recorded verdicts** (they do NOT fuse) per `stage-role-map.md`:
1. **SPEC-CONFORM: PASS/FAIL** — the approval subsystem matches this plan/brief.
2. **BLAST-RADIUS / false-success: PASS/FAIL** — an adversarial pass hunting the
   over-broad / false-CLOSED path, including the **SOLID/DRY dimension** (the
   resolver seam's SRP claims below) and the **cognition honour-check** (does the
   applied gate/dispatcher honour the stated Design Intent — a fail-closed gate
   and a provider-agnostic dispatcher?).
Plus a **negative-check attestation** (`attested_by ≠ author`) for the Tier-3
pieces, one row per grant, each with a **reproducible `evidence` artifact**
(literal `grep`/`diff` of the applied `tier3-writer.md`), asserting the exact
grant, its narrowest intended scope, the **over-broad form checked-for-and-ruled-out**,
and the explicit negative result. Example row: for the `tier3-writer` `edit`
grant, `over_broad_form_checked = "edit '**': allow" or "edit '.gleipnir/**': allow"`,
`evidence = grep of the applied .gleipnir/agents/tier3-writer.md showing the six
enumerated Tier-3 prefixes and the absence of a catch-all glob`, `negative_result
= "'**' / bare '.gleipnir/**' allow is NOT present"`. The evidence MUST be
captured against the **applied / post-change** state of `tier3-writer.md` (T-20).

### Operator-vs-code-agent split (explicit)

| # | Task | Zone | Assemble step |
|---|---|---|---|
| 1 | Write FAILING tests (token + resolver + gate/e2e + server) | bounded `gleipnir-code` (under `tests/`) | 1 |
| 2 | Implement `approval/identity/` resolver seam (fail-closed dispatcher) | bounded `gleipnir-code` (under `src/`) | 2 |
| 3 | Implement `approval/token.py` (mint/validate, 180s, G-3.1 reuse) | bounded `gleipnir-code` (under `src/`) | 3 |
| 4 | Implement `approval/gate.py` (fail-closed write-gate) | bounded `gleipnir-code` (under `src/`) | 4 |
| 5 | Implement `TailscaleResolver` + `approval/server.py` listener | bounded `gleipnir-code` (under `src/`) | 5 |
| 6 | Add `bin/gleipnir-approval-server` operator shim (executable; blast-radius reviewed) | bounded `gleipnir-code` (under `bin/`) | 6 |
| 7a | **Apply `.gleipnir/agents/tier3-writer.md`** | **Tier-3 / operator or build-mode ONLY** | 8 |
| 7b | **Apply `.gleipnir/plugins/tier3-gate.ts`** (the write-block hook — enforcement path-set `E`; the deterministic block that makes Decisions 5/14/14a real; source authored at Step 7) | **Tier-3 / operator or build-mode ONLY** | 8 |
| 7c | **Apply `.gleipnir/decisions/tier3-signed-approval.md`** | **Tier-3 / operator or build-mode ONLY** | 8 |
| 7d | **Configure `tailscale serve`** to front the `127.0.0.1` listener | **operator OS act** (not code this plan builds) | 8 |
| 7e | Confirm `GLEIPNIR_MARKER_KEY_FILE` key exists `chmod 600` (already present) | **operator OS act** | 8 |

### Notes for the implementing agent

- **The test is the arbiter (Axiom 1).** The fail-closed properties (gate REFUSE
  on any doubt, dispatcher reject on no-match), content/identity/freshness
  binding, and the extensibility property are the correctness contract. Do not
  weaken a test to make code pass.
- **Reuse, do not modify, G-3.1.** `token.py` mirrors `verify.marker`'s HMAC
  discipline and reads the same key; it does **not** edit `verify/marker.py`.
- **Fail closed everywhere.** Any absence, error, unresolvable identity, or
  ambiguity ⇒ REFUSE / reject — the `boundary.decide()` and `_cmd_check`
  discipline. Never default to an unauthenticated identity or an unvalidated
  token.
- **The dispatcher's no-match branch is inverted vs `content_handlers`.**
  `content_handlers.dispatch` returns content unchanged on no-match (benign);
  `resolve_identity` MUST **raise** on no-match. This is deliberate, not a bug.
- **stdlib-only, no new Python dependency.** `subprocess`-to-`tailscale`-CLI is
  the identity edge; the `tailscale` CLI is a system-side prerequisite (operator
  hand-off), not a Python package. No `pyproject.toml` dependency edit.
- **No auto-start listener.** `server.py` runs only when the operator starts
  `bin/gleipnir-approval-server`; it is a cooperative process, "authored, not
  yet closed" until S-2/S-3 make it a substrate wall.
- **The two Tier-3 artifacts are hand-offs.** Do not attempt to write
  `.gleipnir/agents/**` or `.gleipnir/decisions/**` — no in-framework agent may.

---

## 7. Design Principles (cognition-layer Gate 1)

**Routing (case (i)).** `P` touches `src/gleipnir/approval/**` — executable
Python with real class/function/module structure (an `IdentityResolver`
Protocol, `ResolvedIdentity`/`ApprovalToken`/`RequestContext` dataclasses, a
registry, a gate, a listener, a resolver class). Axis-1 `X` fires (`src/**`,
`bin/**`) AND the touched members have OOP/functional structure → **Gate-1 case
(i): full SOLID + DRY + SRP + Design Intent, specific and falsifiable.**

### Design Intent (specific, falsifiable — the load-bearing genuineness proxy)

**A Tier-3 write is authorised by, and only by, a fresh (≤180s), content-bound,
identity-bound, HMAC-signed token that the write-gate independently re-validates
and fail-closes on — and the identity that mints it is resolved through a
provider-agnostic seam that names no concrete provider in the gate, mint, or
dispatcher code.** Falsifiable: (a) if any code path can produce a Tier-3 write
without a passing `require_valid_token`, the intent is violated; (b) if the gate
returns ALLOW on a missing/stale/content-mismatched/identity-mismatched/
key-unavailable token, it is violated; (c) if `gate.py`, `token.py`, or
`identity/registry.py` source names `tailscale`/`entra`/`oidc`, the
provider-agnosticism is violated (T-15); (d) if the dispatcher returns a default
identity on no-match instead of rejecting, it is violated (T-13).

### Single Responsibility (falsifiable claims)

- **`identity/registry.py` (dispatcher) knows NOTHING about any provider.**
  Responsibility: given a `RequestContext`, select the first resolver whose
  `can_resolve` is True and return its `ResolvedIdentity`, else **raise**.
  **Falsifiable:** if it contains `tailscale`/`entra`/`oidc` or imports a
  concrete resolver module, the claim is violated (T-15).
- **`TailscaleResolver` knows NOTHING about tokens or the gate.**
  Responsibility: resolve a tailnet identity via `tailscale whois`. **Falsifiable:**
  if it imports `token`/`gate` or references `mac`/`change_hash`, violated.
- **`token.py` knows NOTHING about resolution or the network.** Responsibility:
  mint/validate a content+identity-bound freshness-bound HMAC token.
  **Falsifiable:** if it imports the resolver registry or `http.server`, violated.
- **`gate.py` knows NOTHING about how identity was captured or how the token was
  transported.** Responsibility: fail-closed re-validation of a token against an
  exact change + identity. **Falsifiable:** if it resolves identity itself or
  mints tokens, it has >1 responsibility and must be split.
- **`ResolvedIdentity`** carries exactly `{identity, provider}`. **Falsifiable:**
  if it grows a `mac`/`token`/`change_hash`/`key` field, structural safety and
  its SRP are both violated (T-12).

### SOLID analysis (evaluated against the proposed design)

- **Single Responsibility** — as above; each module has exactly one reason to
  change.
- **Open/Closed** — the resolver dispatcher is **open for extension** (register a
  new resolver) and **closed for modification** (no dispatcher edit to add
  Route β / any OIDC provider) — exactly the extensibility property T-14 proves.
- **Liskov Substitution** — every resolver is substitutable through the
  `IdentityResolver` protocol; the dispatcher depends only on
  `can_resolve`/`resolve`, so `TailscaleResolver`, the test dummy, and a future
  OIDC resolver work identically in the dispatch loop (T-14 is a direct Liskov
  check).
- **Interface Segregation** — `IdentityResolver` is minimal (exactly
  `can_resolve`, `resolve`); the gate/token contracts expose nothing a caller
  does not need; `ResolvedIdentity`/`RequestContext` carry only their own facts.
- **Dependency Inversion** — `server.py` (high-level policy: "capture an
  out-of-band approval") depends on the **abstractions** (`resolve_identity` +
  the `IdentityResolver` protocol, `mint_approval`), naming the concrete
  `TailscaleResolver` only at the single composition-root registration site; the
  gate depends on the `validate_approval` abstraction, never on a provider.

### DRY analysis

- The HMAC/canonical-input discipline is **reused from `verify.marker`**, not
  re-implemented — `token.py` delegates to the tested primitive rather than
  duplicating `hmac.new(...).hexdigest()` + `compare_digest` logic in a second
  place.
- `APPROVAL_MAX_AGE_SECONDS = 180` and `APPROVAL_TOKEN_VERSION = 1` are **named
  module constants** referenced by name, never repeated literals (no magic
  `180`).
- The resolver register/dispatch shape mirrors the proven
  `content_handlers/registry.py` structure rather than inventing a second
  registry idiom (one dispatch pattern in the codebase, applied twice with the
  one deliberate no-match difference).
