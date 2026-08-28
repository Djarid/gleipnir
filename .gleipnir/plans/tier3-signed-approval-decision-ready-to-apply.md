# READY TO APPLY VERBATIM to `.gleipnir/decisions/tier3-signed-approval.md`

> **Stage:** `plan` (gleipnir-plan) hand-off artifact. **Tier-0, disposable.**
> This file persists the complete, ready-to-apply durable decision record — the
> third of the three Tier-3 artifacts named in
> `.gleipnir/plans/tier3-signed-approval.md`. `.gleipnir/decisions/**` is Tier-3
> POLICY; **no in-framework agent — not even `gleipnir-code` — may write it.**
> Preserved here so the **operator / build-mode** can apply it verbatim.
>
> **Apply to:** `.gleipnir/decisions/tier3-signed-approval.md` (create;
> operator/build-mode).
>
> **This file also contains, in a separately-labeled section below, the
> superseding-banner text to add atop the Tier-3 section of
> `.gleipnir/decisions/gleipnir-layout-and-memory-model.md`** — apply that
> alongside, exactly as `operating-posture.md`'s banner was added to that file.

---

## Content 1 of 2 — the exact content to apply to `.gleipnir/decisions/tier3-signed-approval.md`

```markdown
# Decision: Tier-3 out-of-band signed-approval channel (signature-gated `tier3-writer`)

**Status:** decided and BUILT (Python subsystem, this session — 1076 passed,
0 failed, 86% coverage) with three Tier-3 artifacts + operator OS setup pending
apply. Durable decision record (Tier-3, operator-authored). Converged via the
orchestrator-surfaced precept-10 brainstorm gate
(brief: `../plans/tier3-signed-approval-brainstorm.md`), planned from that
converged brief (`../plans/tier3-signed-approval.md`, spec-review PASS), and
implemented under the full hardened 8-stage pipeline this session.

## Why this exists

A Tier-3 write's authority previously rested on an **in-session `question`
answer plus a text provenance footer with no external verification**. A
compromised or confabulating session could fabricate "the operator approved X"
— the exact forgeable-evidence failure Axiom 2 / G-3 exist to close, but at the
POLICY-write boundary rather than the test-marker boundary. The
`gleipnir-layout-and-memory-model.md` contract said "no in-framework agent
writes Tier-3, ever" precisely because there was no way to *prove* a Tier-3
write was operator-authorised. This record replaces "ever" with a
cryptographically-verifiable, out-of-band, freshness-bound authorisation.

## What it narrows (the governing change)

This record **narrows `gleipnir-layout-and-memory-model.md`'s Tier-3 write path
#1** — "**Tier 3 (POLICY) — operator-only.** No in-framework agent writes it,
ever." — to:

> **Only the signature-gated `tier3-writer`, and only when `tier3-gate.ts`'s
> fail-closed hook has verified a valid, fresh (≤180s), content-bound approval
> token exists for that exact change — a token minted only by an out-of-band,
> Tailscale/Entra-identity-resolved approval flow.**

Every other Tier-3 write path is unchanged: the operator's own editor / build
mode remains the escape hatch; no OTHER roster agent gains any Tier-3 write.
This is a *narrowing with a proof obligation*, not a loosening: the previous
"ever" had no verification; the new path has HMAC + content-binding +
identity-binding + freshness + a deterministic in-process block.

## The converged design (operator-decided; recorded, not re-decided here)

- **Route α — Tailscale-injected identity** resolved via `tailscale whois`
  (Entra-backed), behind a **pluggable `IdentityResolver` seam**. Chosen for
  buildable-now stdlib fit + already-deployed infra; other OIDC providers add
  as a second resolver by registration alone (extensibility requirement).
- **G-3.1-reused token primitive** (`src/gleipnir/approval/token.py`): an HMAC
  over a canonical `\x1f`-joined input, reusing `verify.marker`'s discipline
  and the SAME key (`GLEIPNIR_MARKER_KEY_FILE`); **content-bound**
  (`change_hash`), **identity-bound** (`approver_identity` + `provider`), and
  **freshness-bound** at `APPROVAL_MAX_AGE_SECONDS = 180`. `verify/marker.py`
  is reused, NOT modified.
- **Code-enforced fail-closed write-gate** (`src/gleipnir/approval/gate.py` +
  `approval/__main__.py` CLI): `python -m gleipnir.approval.gate --check <path>
  --token <file>`, exit 0 = ALLOW, non-zero = REFUSE, mirroring
  `verify/__main__.py:_cmd_check` and `preflight/boundary.decide()`. No valid
  fresh content+identity-bound token ⇒ REFUSE. No override branch.
- **Deterministic write-block wiring** (`.gleipnir/plugins/tier3-gate.ts`): a
  `tool.execute.before` hook that, on any `edit`/`write` whose target is under
  the Tier-3 path-set, shells out to the gate CLI and **throws to abort** on
  non-ALLOW. Routes on the **target path**, not the acting agent (the
  before-hook input does not carry acting-agent identity), so it gates EVERY
  agent's Tier-3 write, not merely `tier3-writer`'s. ALWAYS-ACTIVE (not
  arming-gated), mirroring `git-guard.ts`.
- **Generalized signature-gated `tier3-writer`** (`.gleipnir/agents/tier3-writer.md`):
  deny-by-default, grants the Tier-3 path-set (agents/skills/goals/decisions/
  keys/stage-role-map.md — NOT plugins/), append-only discipline, holds no
  `question`/git/bash/task/webfetch. It does NOT check the token itself; the
  hook enforces that around its write. **Subsumes the paused `decision-scribe`
  proposal** (which was `decisions/`-only; this covers all of Tier-3).
- **Tailnet-only transport** via `tailscale serve` fronting a `127.0.0.1`
  stdlib `http.server` listener (`src/gleipnir/approval/server.py`, started by
  the operator shim `bin/gleipnir-approval-server`). No standing public
  inbound port (dodges the E-2 standing-public-surface trap).
- **Closes the approval-inbound slice of E-2** (first component home); general
  platform-webhook ingress remains open.

## Extensibility seam (Route α now, others addable without redesign)

Identity capture is behind an `IdentityResolver` Protocol + a fail-closed
register/dispatch registry (`src/gleipnir/approval/identity/`). Today the ONE
registered resolver is `TailscaleResolver` (Route α). A future **Route β
(direct Entra OIDC)** — or any other OIDC provider — plugs in as a **second
registered resolver, with NO edit to `gate.py`, `token.py`, or the dispatcher**
(proven by the mandatory extensibility test, and by a structural source-scan
test asserting the gate/mint/dispatcher name no concrete provider). The
dispatcher fails closed on no-match (raises `IdentityUnresolved` — never
defaults to an unauthenticated identity), the deliberate inversion of the
`content_handlers` benign-passthrough dispatcher it otherwise mirrors.

## Honesty ledger (three columns — the same framing as G-1/G-2/G-3)

**Buildable-now — DONE this session (verified against disk + test run):**

- `src/gleipnir/approval/**` — `token.py` (mint/validate, 180s, G-3.1 reuse),
  `identity/` (Protocol + fail-closed registry + `TailscaleResolver`),
  `gate.py` + `__main__.py` (fail-closed write-gate + `--check` CLI),
  `server.py` (stdlib `http.server` localhost listener), package inits.
- `bin/gleipnir-approval-server` — the operator start shim.
- Five test files — `tests/test_approval_token.py`,
  `tests/test_approval_identity_resolver.py`, `tests/test_approval_gate.py`,
  `tests/test_approval_server.py`, and the `.mjs` plugin conformance test
  `tests/test_tier3_gate.mjs`.
- **Full suite: 1076 passed, 0 failed, 86% coverage this session.**
- **No new Python dependency** (`http.server`/`hmac`/`hashlib`/`json`/
  `dataclasses`/`subprocess`/`argparse` are all stdlib —
  `runtime-and-deps.md` satisfied). `verify/marker.py` and
  `preflight/boundary.py` are unchanged.

**Operator one-time setup — PENDING apply (the hand-off checklist):**

- Apply `.gleipnir/agents/tier3-writer.md` (Tier-3 POLICY).
- Apply `.gleipnir/plugins/tier3-gate.ts` (Tier-3 enforcement-path set `E`).
- Apply `.gleipnir/decisions/tier3-signed-approval.md` (this record) + the
  superseding banner atop `gleipnir-layout-and-memory-model.md`'s Tier-3 section.
- Amend `.gleipnir/sandbox/profiles.toml` `[profile.node].test` to add
  `tests/test_tier3_gate.mjs` so the plugin conformance test runs in CI.
- Configure `tailscale serve` to front the `127.0.0.1` listener (operator OS act).
- Confirm `GLEIPNIR_MARKER_KEY_FILE` key exists `chmod 600` (already present) —
  the approval token reuses the G-3.1 HMAC key; no new key is created.

**Cooperative-until-closed — HONEST scope (same as G-1/G-2/G-3):**

The gate is enforced AT THE HOOK. The plugin file, the gate CLI, and the key
all sit in agent-writable / agent-adjacent space until the **S-2 mount** makes
them structurally unreachable and **S-3 preflight** verifies their integrity
digests. Until then this is **cooperative-policy, not a hard substrate wall** —
authored, not yet closed, labelled exactly like the other guards. A caged-mode
(`operating-posture.md`) session is where this hardens into a boundary; the
uncaged default trusts the single-principal operator, as everywhere else.

## Reused primitive: G-3.1 IS the token defense

The approval token is not new crypto — it reuses the built, tested G-3.1 HMAC
discipline (`src/gleipnir/verify/marker.py`): the same key, the same
`hmac.new(key, canonical_input, "sha256").hexdigest()` mint, the same
`hmac.compare_digest` fail-closed validate, the same freshness discipline —
with identity as a first-class token field (not smuggled into `tree_hash`) and
the window narrowed to 180s. The key lives outside the agent surface (S-2
boundary target), so the token cannot be forged without it.

## Status: authored, not yet closed (the parts that remain)

- S-2 mount + terminal closure to make the plugin / gate / key structurally
  unreachable (the cooperative-until-closed column above).
- S-3 preflight verification of the new Tier-3 artifacts' integrity digests.
- Route β (OIDC) implementation — seam only today; additive later.
- Tier-2 / G-4c (lessons/memory) generalization of the signed-approval gate —
  out of scope now; the seam is designed so it is additive, not a redesign.
```

---

## Content 2 of 2 — superseding-banner text for `.gleipnir/decisions/gleipnir-layout-and-memory-model.md`

Add this banner **immediately above** the `## The three write paths` section's
path-#1 text (line 75, "1. **Tier 3 (POLICY) — operator-only.** No in-framework
agent writes it, ever."), mirroring how `operating-posture.md`'s banner was
added atop that file's top. Apply verbatim:

```markdown
> **NARROWED IN PART by `tier3-signed-approval.md` (signature-gated Tier-3
> write path).** Write path #1 below ("no in-framework agent writes Tier-3,
> ever") now has ONE verified exception: the signature-gated `tier3-writer`
> may write Tier-3 when — and only when — `tier3-gate.ts`'s fail-closed hook
> has verified a valid, fresh (≤180s), content-bound, identity-bound signed
> approval token exists for that exact change, minted via an out-of-band
> Tailscale/Entra-resolved approval flow. This is a narrowing with a
> cryptographic proof obligation, not a loosening: the old "ever" had no
> verification. Every OTHER Tier-3 write path (operator editor / build mode)
> and every other roster agent's Tier-3-unwritability are unchanged. The
> `keys/` mode-600 floor is retained. See `tier3-signed-approval.md` for the
> governing design, the honesty ledger, and the cooperative-until-S-2 scope.
```

---

## Provenance footer

Drafted by `gleipnir-plan` (this session) from the converged brief
(`.gleipnir/plans/tier3-signed-approval-brainstorm.md`) and the spec-reviewed,
now-built plan (`.gleipnir/plans/tier3-signed-approval.md`). Persisted to a
Tier-0 hand-off file because `.gleipnir/decisions/**` is Tier-3 POLICY and no
in-framework agent may write it. Applied by operator/build-mode. Structure
mirrors `.gleipnir/decisions/session-scribe.md` and
`.gleipnir/decisions/operating-posture.md`.
