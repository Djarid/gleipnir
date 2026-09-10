# Decision: Tier-3 out-of-band signed-approval channel (signature-gated `tier3-writer`)

**Status:** decided and BUILT (Python subsystem, this session — 1080 passed,
0 failed, 86% coverage) with three Tier-3 artifacts applied (operator/build-mode,
this session) + operator OS setup (`tailscale serve`, key confirmation) pending.
Durable decision record (Tier-3, operator-authored). Converged via the
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
  --content-file <file> --token <file>`, exit 0 = ALLOW, non-zero = REFUSE,
  mirroring `verify/__main__.py:_cmd_check` and `preflight/boundary.decide()`.
  The `change_hash` is computed over the `--content-file` bytes (the approved
  resulting content), NOT a fresh read of `--check` (Decision 19 — the
  mint-vs-check content-hash fix). No valid fresh content+identity-bound token
  ⇒ REFUSE. No override branch.
- **Deterministic write-block wiring** (`.gleipnir/plugins/tier3-gate.ts`): a
  `tool.execute.before` hook that, on any `edit`/`write` whose target is under
  the Tier-3 path-set, computes the exact resulting content (Decision 20:
  `write` → `args.content`; `edit` → fail-closed refuse, since opencode's
  fuzzy-replacer+formatter path is not reproducible out-of-band), writes it to
  a temp `--content-file`, shells out to the gate CLI, and **throws to abort**
  on non-ALLOW. Routes on the **target path**, not the acting agent (the
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

**Operator's converged answer on the identity route (verbatim):** "I'm happy
with route alpha as we use tailscale... but a future fix should open this up to
other OIDC providers." (Freshness window: operator confirmed the recommended
2–5 minute band; implemented at 180s / 3 minutes.)

## Honesty ledger (three columns — the same framing as G-1/G-2/G-3)

**Buildable-now — DONE this session (verified against disk + test run):**

- `src/gleipnir/approval/**` — `token.py` (mint/validate, 180s, G-3.1 reuse),
  `identity/` (Protocol + fail-closed registry + `TailscaleResolver`),
  `gate.py` + `__main__.py` (fail-closed write-gate + `--check`/`--content-file`
  CLI), `server.py` (stdlib `http.server` localhost listener), package inits.
- `bin/gleipnir-approval-server` — the operator start shim.
- Five test files — `tests/test_approval_token.py`,
  `tests/test_approval_identity_resolver.py`, `tests/test_approval_gate.py`
  (incl. the `TestContentDivergence` / T-22 regression proving the
  content-binding fix), `tests/test_approval_server.py`, and the `.mjs` plugin
  conformance test `tests/test_tier3_gate.mjs`.
- **Full suite: 1080 passed, 0 failed, 86% coverage this session.**
- **No new Python dependency** (`http.server`/`hmac`/`hashlib`/`json`/
  `dataclasses`/`subprocess`/`argparse` are all stdlib —
  `runtime-and-deps.md` satisfied). `verify/marker.py` and
  `preflight/boundary.py` are unchanged.

**Operator one-time setup — status:**

- Apply `.gleipnir/agents/tier3-writer.md` (Tier-3 POLICY) — APPLIED this session.
- Apply `.gleipnir/plugins/tier3-gate.ts` (Tier-3 enforcement-path set `E`) —
  APPLIED this session.
- Apply `.gleipnir/decisions/tier3-signed-approval.md` (this record) + the
  superseding banner atop `gleipnir-layout-and-memory-model.md`'s Tier-3
  section — APPLIED this session.
- Amend `.gleipnir/sandbox/profiles.toml` `[profile.node].test` to add
  `tests/test_tier3_gate.mjs` so the plugin conformance test runs — APPLIED
  this session.
- Configure `tailscale serve` to front the `127.0.0.1` listener (operator OS
  act) — PENDING.
- Confirm `GLEIPNIR_MARKER_KEY_FILE` key exists `chmod 600` (already present) —
  the approval token reuses the G-3.1 HMAC key; no new key is created —
  PENDING confirmation.

**Restart note:** the `tier3-gate.ts` hook and the `tier3-writer` role become
live only after a full opencode restart (L-C33: mid-session Tier-3/plugin
config is not loaded until restart). Until the restart, the gate does not yet
enforce and the role is not yet reachable — the artifacts are on disk but
dormant this session.

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
- Operator OS acts: `tailscale serve` config + key-permission confirmation.

## Supersession: launch mechanism (Decision 15 of the plan) — MCP-supervised

**Superseded by `../plans/tier3-mcp-approval-launcher.md` (this session).**
`../plans/tier3-signed-approval.md` **Decision 15** ("No auto-start… a
long-running process the operator starts manually… never launched by any
agent") is **narrowed**: the approval listener may now be started as a
**supervised subprocess spawned by opencode's `gleipnir-approval` local MCP**
(`gleipnir.approval.mcp_server`), OR by the manual `bin/gleipnir-approval-server`
shim (kept as a documented fallback). The MCP also exposes one agent-facing
tool, `request_approval`, holder-scoped to **`tier3-writer` only** (all 9 other
roster agents carry a `"gleipnir-approval_*": false` deny).

**Why the original "never launched by any agent" framing was miscalibrated.**
The security locus was never *who launches the process* — it is *who can read
the signing key and mint a token*. Launching the listener confers
process-supervision only; it does not grant the launcher the HMAC key or the
ability to mint. Identity is still resolved out-of-band via `tailscale whois`
against a **separate authenticated tailnet peer** at request time, and the
`request_approval` tool only **stages** a pending change + returns the
`/approve/<hash>` URL — it never mints (structurally enforced by the reverse-
import scan `test_approval_mcp_server.py::…T11`: `mcp_server.py` may not import
or call `capture_approval`/`mint_approval`/`load_key`). The key reaches the MCP
subprocess via `.envrc`/direnv → opencode inherited env → `{env:...}` reference
in `opencode.jsonc` (never a literal in tracked config); the agent tool surface
never sees the key bytes.

**Honest residual gap (carried forward, deliberately deferred — NOT closed by
this change).** The isolation this rests on is, today:

> isolation-by-convention, not isolation-by-capability, until the global
> `.envrc`/`.env*` deny is built (deferred, not in this plan's scope) — a roster
> agent with sufficient bash/read capability could in principle attempt to read
> the key's source, and only the current deny-by-default bash allowlists (not a
> dedicated `.envrc` read-deny) stand between an agent and that file today.

This becomes structural (not cooperative-policy) only when the global
`.envrc`/`.env*` roster-wide read-deny lands and, ultimately, under the S-2
mount + terminal closure named above. The `.envrc` key source is an **interim
choice**; a secret store (HashiCorp Vault / 1Password / similar) is the named
early-hardening candidate.
- The full opencode restart that makes the hook + role live.

## Narrowing: the `.env*` roster-wide permission deny (this session)

**Closes part of the O-3(b) residual named above — narrowed, not eliminated.**
Every roster agent's frontmatter now denies `permission.read`/`edit`/`write` for
the `.env*` glob (`.gleipnir/plans/envrc-roster-deny-brainstorm.md`, CONVERGED;
`.gleipnir/plans/envrc-roster-deny-plan.md`, spec-review PASS). This is a
genuine, real narrowing of the previously-named gap: before this change, only
deny-by-default bash allowlists stood between an agent and `.envrc`; now
opencode's own permission layer additionally refuses any `read`/`edit`/`write`
tool call an agent makes against a `.env*`-matching path.

**The required quote this amendment carries forward, verbatim, from
`.gleipnir/plans/envrc-roster-deny-plan.md:481-494`:**

> **O-3(b) — narrowed (not closed).** The roster-wide `.env*` `read`+`edit` deny
> now lands as an **opencode-permission-layer** control: opencode refuses every
> roster agent's `read`/`edit` tool call for a `.env*` path, in both caged and
> uncaged postures. This is **explicitly NOT** file-permission (chmod/chown)
> enforced and **explicitly NOT** OS-exclusive: the `gleipnir-approval` signer
> MCP subprocess and every agent's tool-invocation processes run under **one
> shared OS uid** today, so no OS-level control separates "signer" from "agent."
> The deny closes only the opencode-tool-dispatch path; it does nothing against a
> future `bash`/`exec` capability, a compromised MCP, a compromised opencode, or
> any OS-level access path. Genuine OS-level isolation is the **deferred
> signer-uid-separation follow-on** (dedicated service account + `chown` +
> uid-switched MCP launch, e.g. `sudo -u signer …`) — the same shape as the S-2
> dedicated-agent-uid machinery, inverted — plus the S-2 mount. O-3(b) is
> therefore **narrowed to "opencode-permission-layer enforced," NOT resolved.**

**This record therefore states plainly: the O-3(b) gap is narrowed to
"opencode-permission-layer enforced," explicitly NOT "file-permission
enforced" and explicitly NOT "operator has exclusive OS control of the key."**
Verified live (not merely asserted) via required runtime probes against the
already-gitignored `.envrc` — the recorded outcome of those probes is the
attestation evidence for the two agents whose maps carry a `"*": allow`
(`gleipnir-code`'s edit map, `git-ops`'s read map), per
`envrc-roster-deny-plan.md`'s two-tier attestation. **`gleipnir-code`'s
read/edit/write probes are empirically CLOSED (real permission-denial
responses, not content-mismatch failures); `git-ops`'s read-map probe is
tracked separately and must be closed before this attestation's row (b) is
complete — structural analogy to `gleipnir-code`'s result is not accepted as a
substitute per the plan's own per-target runtime-evidence requirement.**

**Deferred, named follow-on (distinct from this change, NOT folded in):**
genuine OS-level secret isolation would require the **signer to run under a
distinct uid from the agent's tool-invocation processes** — a dedicated
service account + `chown` + a uid-switched MCP launch (e.g.
`sudo -u signer …`), the same shape as this framework's S-2 dedicated-agent-uid
machinery, just **inverted** (protecting the signer *from* the agent's uid,
rather than restricting the agent's uid away from enforcement paths). Also
still deferred, unchanged: the `boundary.py`/OS-layer `ENFORCEMENT_PATHS`
addition (bites only in caged mode; `.envrc` sits outside `config_root`'s
`.gleipnir/`-relative invariant) and the `.gitignore` `.env*` widening
(a version-control-tracking concern, a separate follow-on).
