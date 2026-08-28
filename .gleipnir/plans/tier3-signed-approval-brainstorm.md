# Design Brief (PRE-CONVERGENCE): Tier-3 out-of-band signed-approval channel

_Author: `gleipnir-brainstorm`. Tier-0 artifact; disposable; NOT authoritative.
This proposes and grounds; it does not decide. **Status: CONVERGED — all five
threshold questions AND the one remaining identity-capture sub-decision are
operator-decided. Route α (Tailscale-injected identity) is chosen, built behind
a pluggable identity-resolver seam; freshness window = 3 minutes (within the
operator-confirmed 2–5 min band). This brief is READY FOR `gleipnir-plan` to
plan from — no further operator convergence is required.** `gleipnir-brainstorm`
does NOT write the ATLAS plan; that is `gleipnir-plan`'s stage. The pre-Clarify
Explore/Propose spectrum is retained below for provenance; the answers collapsed
it, and the collapse is documented in the Decision Analysis._

## Problem Statement

Mid-conversation about *who/what may write `.gleipnir/decisions/**` (Tier-3)*,
the operator raised a bigger question than the narrow writer-role one: rather
than (or in addition to) picking a narrow writer role, could a **Tier-3
approval/signing mechanism** — accessible only to the operator via an
**out-of-band** channel (a web UI with SAML/OIDC, OR a chat-ops workflow like
Slack / Discord / SMS) — **sign each decision record so it is attributable** to
a real, authenticated approval event?

The underlying worry is provenance/attribution integrity: today a Tier-3
write's authority rests on an *in-session* `question` answer plus a text
provenance footer. That has **no external verification** — a compromised or
confabulating orchestrator could in principle fabricate "the operator approved
X" and nothing outside the session would catch it. An out-of-band,
cryptographically-attributable approval event would make "the operator approved
this exact content" checkable independently of the (possibly compromised)
session that produced it.

The operator explicitly wants this treated as **its own real design thread**,
not folded hastily into the narrower writer-role question, and explicitly
widened the channel candidates beyond web+SAML to "Slack / Discord / SMS or
something."

## Relationship to the paused narrower thread (do not re-derive)

`plans/decision-scribe-control-proposal.md` (676 lines) already analysed the
narrow **"who holds the write grant"** question and recommended Option A: a
dedicated `decision-scribe` roster role (weighted-matrix 414 vs B 271 vs C 215).
That thread is **PAUSED, not decided**, pending this bigger question. The two
threads are orthogonal but composable:

- The **decision-scribe** thread answers *which bounded agent executes the
  write*, and its human-review step is an **in-session** `question` (its own
  record calls this "the interim substitute for a future signed policy-change
  command").
- **This** thread answers *whether the approval that authorises the write is an
  out-of-band, externally-attributable event* rather than an in-session answer.

They are not either/or: the signed-approval channel could become the *gate that
feeds* a decision-scribe write (scribe still executes; the authorising token is
now externally minted), or it could stand alone. Whether decision-scribe is
subsumed, kept, or composed is one of the open questions below.

## Constraints (grounded in what already exists — do not re-derive)

- **A working "signing" primitive already exists: G-3.1** (`src/gleipnir/verify/
  marker.py`, tested). Keyed HMAC over a tree hash; key read from
  `GLEIPNIR_MARKER_KEY_FILE`; constant-time validate; **fail-closed**; freshness
  bound. `gleipnir-layout-and-memory-model.md` line 105 explicitly names
  extending this SAME primitive to Tier-3 policy files ("G-3.1 IS the
  integrity-digest defense") — but it was **never wired to `decisions/**`
  content**. What it does today: proves a *local tree state* was certified by
  the key-holding process. What it does NOT do: attribute a *content approval*
  to an *authenticated human via an out-of-band channel*. That gap is the
  substance of this thread.
- **`notify` is outbound-only.** `.gleipnir/agents/notify.md` sends a message TO
  a human (one webhook target for v0.1; **Block Kit** — Slack's formatting API —
  and email deferred; both unbuilt). There is **no mechanism to receive a
  reply/approval FROM a human.** So Slack was already the *implicitly-planned
  outbound* target; the inbound half is missing.
- **The inbound half is a NAMED, TRACKED open seam with no component home: E-2
  ("platform-webhook receiver has no component home").** Confirmed across
  `substrate-design-pass.md` (#8: "opencode has no persistent inbound
  receiver — ABSENT = E-2"), `g4-bus.md`, and `seam7-seam8-wiring-brainstorm.md`
  (where an inbound-receiver option **8B was rejected** precisely because it
  "drags in a CI signing-key surface and an E-2-shaped transport that has no
  component home yet"). **This thread is largely a proposal to give E-2 its
  first real reason-to-exist and component home.** The brief should explicitly
  connect to — and potentially help close — E-2.
- **Structural obstacle behind E-2:** opencode (and the pi.dev replatform) is a
  **fresh-process model with no persistent inbound network listener**
  (`substrate-design-pass.md` #8; `seam7-seam8-wiring-brainstorm.md`: "no
  inbound network listener to secure"). Any inbound approval channel needs a
  *persistent process* the ephemeral agent host does not provide — a genuinely
  new component, not a config tweak.
- **Threat-model envelope (`operating-posture.md`).** The uncaged default is
  safe ONLY within "session access equals full operator authority AND no
  untrusted content enters context." An out-of-band signed-approval channel is a
  control that matters *more outside* that envelope — compromised session,
  untrusted content, unattended/autonomous, and explicitly **"multi-agent /
  hosted operation (C-tier)"**, already named as a future higher-assurance
  trigger. Framing question: near-term single-operator hardening, or
  infrastructure aimed at that future multi-principal/hosted case? (This is
  threshold question 4.)
- **G-4c connection.** Today's interim substitute for the not-yet-built
  review-gated Tier-2 promotion pipeline (memory/lessons) is also the in-session
  `question` + text footer, with the same "no external verification" weakness.
  An out-of-band signed-approval channel would be a genuine hardening of G-4c's
  eventual real form, **generalizable beyond `decisions/**` to Tier-2
  promotions**. Note the generalization possibility — but do NOT assume it is in
  scope; it is threshold question 3.
- **Reversibility.** Building a whole external channel (workspace/number/OIDC
  provider + a persistent receiver process + key/token plumbing) is a
  **multi-session infrastructure commitment** with real reversal friction
  (provisioned accounts, a standing network surface to secure, a new decision
  record other records will cite). Extending G-3.1's keyed digest to
  `decisions/**` content is a near-two-way-door by comparison. The two ends of
  the spectrum are *very different lifts* — which is why the threshold answers
  must precede any recommendation.

## Explore / Propose — the SPECTRUM (grounding shapes only, NOT a converged menu)

Three points on a spectrum, cheapest-and-most-precedented first. Presented so
the operator has concrete shapes to react to when answering the Clarify
questions — **not** a finalised A/B/C to pick from yet (the threshold answers
below reshape which of these is even coherent).

### Point 1 (cheap, already-built primitive) — extend G-3.1 keyed digest to `decisions/**` content

**Summary:** Reuse the existing HMAC marker: on an operator-approved Tier-3
write, mint a keyed digest over the *record content* (not just a tree) and store
it in `keys/`; a fail-closed check at session start / before high-impact use
verifies the record matches its approved digest. No web UI, no SAML/OIDC, no
chat. "Out-of-band" here means **OS file-permission-gated to the operator's own
account + physical possession of the key** (`marker.key`, `chmod 600`), not a
federated identity event. This is exactly the `gleipnir-layout-and-memory-model.md`
line-105 "G-3.1 IS the integrity-digest defense" extension, finally wired.

**Tradeoffs:**
- Pro: near-zero new surface; primitive is built, tested, fail-closed.
- Pro: no new persistent process; sidesteps E-2 entirely.
- Pro: composes cleanly with the paused decision-scribe thread (scribe writes;
  digest attests content).
- Con: identity guarantee is only "whoever holds the key + the OS account" — it
  does **not** prove *which authenticated human* approved via an independent
  channel. If the threat is a compromised session on the operator's own box, the
  key may be in the same blast radius. It hardens *content-integrity/attribution
  to the key*, not *federated human identity*.

**Estimated scope:** `src/gleipnir/verify/**` (content-digest mode), `keys/**`
(new digest entries), a preflight check hook, one decision record. Low-medium.

**Risk:** low — but may not satisfy the operator's actual identity goal (that is
threshold question 1).

### Point 2 (moderate) — chat-ops approval bot with reply-webhook (Slack / Discord / SMS)

**Summary:** A persistent receiver component (the first real **E-2** home)
listens for an out-of-band approval action — a Slack/Discord button click or an
SMS/OTP reply — bound to a specific pending decision-record diff. Identity is
the channel's own auth (Slack/Discord workspace membership + OAuth, or
possession of the registered phone number). On approval, an
externally-originated signed token authorises the Tier-3 write (which
decision-scribe, or the orchestrator, then executes). Reuses the
already-implied-Slack `notify` outbound leg for the *request*; adds the missing
*inbound* leg.

**Tradeoffs:**
- Pro: approval is genuinely out-of-band — a compromised session cannot forge a
  Slack click / SMS reply from the operator's real account/number.
- Pro: gives E-2 its first concrete component home; the outbound half is already
  the planned `notify` target.
- Pro: single-channel first slice is feasible (one workspace or one Twilio
  number), deferring multi-channel.
- Con: needs a **persistent inbound process** the fresh-process opencode host
  does not provide (the structural E-2 obstacle) — a real new standing network
  surface to build and secure; this is the reason 8B was rejected before.
- Con: identity is "channel possession," not federated SSO — weaker than
  SAML/OIDC if the goal is provable named-human federation (threshold q1).

**Estimated scope:** a new persistent `src/gleipnir/**` receiver + bus ingress
(E-2), `notify` outbound wiring/Block Kit, token minting reusing G-3.1, external
account/app registration, a decision record + threat-model note. Medium-high.

**Risk:** high — new standing network surface; external-account operational
dependency; the E-2 obstacle is real.

### Point 3 (heavy) — full web UI with SAML/OIDC federated identity

**Summary:** A hosted approval web UI behind a SAML/OIDC IdP. Each pending
Tier-3 (and optionally Tier-2) change is presented as a reviewable diff; the
operator authenticates via the IdP and signs the exact diff; the signed
assertion (bound to a federated identity) authorises the write. This is the
"prove it was THIS specific authenticated human" end.

**Tradeoffs:**
- Pro: strongest identity guarantee — federated, named-human, multi-reviewer
  capable; the natural fit for the future multi-principal / hosted (C-tier) case.
- Pro: cleanest audit story — signed assertion bound to an external identity,
  independently verifiable.
- Pro: naturally generalizes to Tier-2 G-4c promotions and multi-reviewer
  workflows.
- Con: heaviest lift by far — a persistent web service (E-2 + more), an
  IdP/OIDC provider dependency, session/CSRF/signing-key management, hosting.
  Multi-session infrastructure investment.
- Con: for a *single trusted operator on their own box*, SAML/OIDC's
  multi-identity machinery may be paying for a guarantee not yet needed
  (threshold q4 decides this).

**Estimated scope:** a new hosted service, IdP integration, signing
infrastructure, E-2 receiver, multiple decision records + threat model. High.

**Risk:** high — largest surface, external IdP dependency, likely premature for
the current single-operator posture unless q4 says multi-principal is the target.

## Open Questions — CLARIFY (returned to the orchestrator VERBATIM for the operator)

_These are genuinely open threshold questions; the answers reshape which
spectrum point is even coherent, so they must be answered before any
`## Selected Approach` or numeric recommendation is produced. Verbatim per
L-C18._

1. **Identity guarantee sought.** Is the goal **strong federated identity proof**
   (SAML/OIDC — "prove it was THIS specific authenticated human") — or is a
   **simpler out-of-band shared-secret / HMAC signature** (reusing the existing
   G-3.1 keyed marker, gated by OS file permissions + physical possession of a
   channel such as a personal Slack account or phone) actually sufficient? These
   are very different lifts, and the answer largely selects the spectrum point.

2. **Channel(s) and available infrastructure.** Is any ONE of {web-UI+SAML/OIDC,
   Slack, Discord, SMS} acceptable as a first slice, or do you want multiple
   channels from day one? And is there an **existing account/workspace/number
   already available** to build against (a real Slack workspace, a Twilio number,
   an OIDC provider), or would that infrastructure need to be provisioned from
   scratch?

3. **Scope of what gets signed.** Should the signed-approval mechanism cover
   **JUST `.gleipnir/decisions/**` writes**, or **ALL Tier-3 writes** (agents/,
   skills/, goals/, stage-role-map.md, keys/), or generalize **further to
   G-4c's Tier-2 promotion pipeline** (lessons/, memory/) as well?

4. **Single-operator vs multi-principal horizon.** Is this hardening for the
   **CURRENT single-trusted-operator** posture, or explicitly aimed at a
   **future multi-reviewer / hosted (C-tier)** scenario? (This materially
   changes whether SAML/OIDC's multi-identity machinery is worth its cost now,
   vs. an HMAC/chat-ops slice.)

5. **Urgency / horizon.** Is this something you want usable in the **next
   session or two** (favouring the cheap G-3.1 extension), or an acknowledged
   **multi-session infrastructure investment** (which opens the chat-ops or web
   UI ends)?

**One additional design question raised by the exploration (please also weigh
in when convenient):** should this **subsume, keep, or compose with** the paused
`decision-scribe` thread? (Signed-approval-as-gate + scribe-as-executor compose
cleanly; a full web-UI/OIDC path might subsume the need for a roster scribe
entirely.)

## Scope Sketch (indicative, pending Clarify answers)

| Area | Files/Modules Likely Affected (depends on chosen point) |
|------|----------------------------------------------------------|
| Signing primitive | `src/gleipnir/verify/**` (content-digest mode), `keys/**` |
| Inbound channel (E-2) | new persistent `src/gleipnir/**` receiver; `bus/` ingress |
| Outbound request | `.gleipnir/agents/notify.md` + T-5 webhook / Block Kit |
| Write execution | paused `decision-scribe` role, or orchestrator (per that thread) |
| Policy / provenance | `.gleipnir/decisions/**` (new record; narrows the "no agent, ever" line and/or supersedes the decision-scribe interim-gate framing) |
| Threat model | `operating-posture.md` (caged/multi-principal linkage) |

## Bias / discipline note

- ⚠️ *Scope Creep* watch: the temptation is to build the heaviest (web+OIDC)
  option "to cover everything." Threshold q3/q4 exist to force a scoped choice
  rather than expanding to satisfy all cases at once.
- ⚠️ *IKEA Effect* watch (mild): G-3.1 is *ours* and already built, which may
  inflate Point 1's appeal — but Point 1 genuinely may not deliver the *federated
  identity* guarantee q1 might demand; that must be judged on the identity
  requirement, not on "we built it."
- No convergence performed at CLARIFY time. This subagent's `question` does not
  reach the operator; the recommendation was deferred until the answers
  returned. They have now returned — see below.

---

# POST-CLARIFY (answers in; converging)

## Clarify answers (verbatim summary of what the operator returned)

1. **Identity:** already have federated identity — **Azure Entra ID**, plus
   **Tailscale's identity-aware networking (IdP backed by Entra)**. So SAML/OIDC
   *from scratch* is NOT the lift; **integrating with already-deployed
   Entra/Tailscale** is. Reason concretely about what THAT makes cheap.
2. **Channel:** one channel first, simplest available **given the existing
   infra** — likely a tiny local endpoint fronted by Tailscale, not Slack/
   Discord/SMS (which need separate infra that does not yet exist).
3. **Scope:** **ALL Tier-3 writes** (`agents/`, `skills/`, `goals/`,
   `stage-role-map.md`, `keys/`, `decisions/`), not just `decisions/**`.
4. **Horizon:** **single-operator, near-term** (usable in a session or two);
   lean on already-deployed Entra/Tailscale, do NOT build heavy new infra.
5. **Composition:** compose (signed-approval gate + a Tier-3 executor role),
   **provided the write path is CODE-ENFORCED to refuse any Tier-3 write lacking
   a valid signature, and the signature is TIME-SCOPED / freshness-bound** (short
   window, genuine temporal immediacy; no stale/replayed approval).

**Effect on the spectrum:** the answers collapse it decisively. Point 3 (build a
web+OIDC stack *from scratch*) is off — but its *identity strength* is achievable
cheaply because the IdP already exists. Point 2's chat-ops variants (Slack/
Discord/SMS) are **de-prioritised**: each needs net-new infra (bot tokens, Twilio,
OAuth app registrations) whereas Tailscale+Entra is already deployed. Point 1's
G-3.1 reuse survives — not as the *identity* layer but as the **freshness-bound
signed-token + fail-closed-gate primitive** the operator explicitly asked for.
The winning design is a *composite*: **Tailscale/Entra for identity capture +
G-3.1-style freshness-bound HMAC token for the deterministic write-gate.**

## Explore findings (grounded in the ACTUAL Entra/Tailscale + G-3.1 specifics)

### What the already-deployed identity infra makes cheap

- **Tailscale Serve** can front a tiny **localhost** HTTP endpoint on the tailnet
  and terminate TLS, exposing it only to the operator's own devices — **no public
  ingress, no inbound port on the open internet**. This directly answers the
  structural E-2 obstacle ("opencode is a fresh-process model with no persistent
  inbound listener"): the listener need only bind `127.0.0.1` and be *reachable*
  via `tailscale serve`, so the "standing public network surface" that got option
  8B rejected in `seam7-seam8-wiring-brainstorm.md` **does not arise** — the
  surface is tailnet-only, device-scoped.
- **Identity capture, two concrete routes (this is the one open sub-decision):**
  - **Route α — Tailscale-injected identity (simplest).** A request arriving via
    `tailscale serve` carries the caller's tailnet identity; the local receiver
    reads it either from the injected header (`Tailscale-User-Login` /
    equivalent) or by calling `tailscale whois <remote-ip>` (LocalAPI) to resolve
    the connecting identity. Because the tailnet IdP is **backed by Entra**, that
    login IS an Entra-authenticated identity — **no OIDC client dance, no app
    registration, no redirect/callback/token-exchange to implement.** The
    receiver trusts the tailnet's own authenticated transport.
  - **Route β — direct Entra OIDC app.** Register an OIDC app in Entra; the
    endpoint runs a real authorization-code flow; the approval is bound to the
    `id_token`'s verified claims. Stronger *explicit* federation (a real signed
    assertion from Entra), but it is the heavier lift Route α avoids, and it
    needs an app registration the operator would have to create.
  - **Judgment:** Route α is dramatically cheaper and *sufficient* for a
    single-operator near-term posture, because tailnet membership is already
    Entra-gated — the identity guarantee is "the connecting device is an
    Entra-authenticated member of the operator's own tailnet." Route β buys a
    portable, independently-verifiable Entra assertion (better for the future
    multi-principal/hosted case), at real extra cost now. **This is the single
    remaining operator sub-decision** (stated at the end). It does not change the
    approach shape — only how the endpoint learns *who* approved.
- **Neither route needs Slack/Discord/SMS.** Those were the pre-answer Point-2
  channels; all require net-new infra. Tailscale+Entra already exists, so the
  simplest single channel (answer 2) is **the tailnet-served local endpoint.**

### The G-3.1 primitives this reuses (verified against the code)

The operator's answer-5 requirements map *exactly* onto mechanisms G-3.1 already
implements and tests — this is reuse, not new crypto:

- **`mint(tree_hash, key, minted_at)`** (`verify/marker.py:166`) produces a
  keyed HMAC over a canonical, length-prefixed input, stamped with `minted_at`.
  The **approval token is the same shape**: mint an HMAC over the *canonical
  content of the exact pending Tier-3 change* (the diff/blob hash) + the approver
  identity + a timestamp. "What carries the signature" = a short-lived signed
  **token file** of exactly this form (a `Marker`-like record).
- **`validate(...)`** (`verify/marker.py:180`) already does, in constant time and
  **fail-closed**: version check, **content-binding** (`compare_digest` of the
  bound hash — a one-byte change invalidates), **HMAC unforgeability** (no key →
  cannot mint), and **freshness** (`age > max_age_seconds` → invalid; future-
  dated → invalid). Answer-5's "time-scoped / no replay" is **the existing
  freshness bound** — just with `max_age_seconds` set to **minutes, not the
  default 3600s**. Recommend **~2–5 minutes** (`DEFAULT_MAX_AGE_SECONDS` is
  overridable per-call; the CLI already exposes `--max-age`).
- **The deterministic write-gate = the existing `check`/`validate` fail-closed
  pattern** (`verify/__main__.py:_cmd_check`: exit non-zero ⇒ REFUSE; missing
  token ⇒ REFUSE), which is the *same* shape as the preflight `boundary.decide()`
  → `REFUSE`-on-any-doubt discipline (`preflight/boundary.py`). "What enforces
  the deterministic block" = a **preflight check that runs before ANY Tier-3
  write path executes and returns REFUSE unless a valid, fresh, content-bound
  token for *this exact change* is present.** Not documented discipline — a
  code gate that fail-closes, exactly like the marker check already does.
- **stdlib-only, buildable now.** `runtime-and-deps.md` fixes the enforcement
  core at Python stdlib-only; G-3.1 uses `hashlib`/`hmac`/`json`/`dataclasses`.
  The token mint/validate and the local HTTP endpoint are all
  **stdlib-implementable** (`http.server`, `hmac`, `hashlib`, `json`,
  `subprocess` for `tailscale whois`). No new runtime dependency enters the S-2
  trusted surface. Route β (OIDC) *would* likely pull a dependency for token
  validation — another reason Route α is the near-term-cheap default.

### Executor role — rename/generalize `decision-scribe`

Scope is now **ALL Tier-3** (answer 3), so the paused `decision-scribe` (scoped
to `decisions/**` only) is the *right shape but the wrong scope/name*. The clean
composition: a **generalized `tier3-writer` (signature-gated)** executor —
deny-by-default; `edit`/`write` allow the Tier-3 path-set; but its writes are
**preceded by the code-enforced token gate** (it cannot write a Tier-3 path
unless a valid fresh token bound to that exact change exists). It holds no
`question` (cannot self-originate approval), no git/bash/task. The
`decision-scribe` proposal's append-only integrity floor, verbatim-provenance,
and verify-against-disk discipline carry over unchanged; only the scope widens
and the *authorising gate* upgrades from an in-session `question` to an
out-of-band freshness-bound signed token. **decision-scribe is subsumed**, not
kept alongside — one executor for all Tier-3, gated by signature.

### Does this close E-2? — Yes, first real home (qualified)

E-2 is "platform-webhook receiver has no component home." This design gives the
**inbound approval receiver its first concrete component home** — a small
tailnet-served local listener under `src/gleipnir/**`. It is a *narrower* home
than the general "platform webhook receiver" E-2 was originally framed around
(GitHub/Slack webhooks into the G-4 bus): this receiver's job is specifically
**approval capture**, not general event ingress. So: **it closes the "no home"
gap for the approval-inbound case and establishes the receiver-component
pattern**, while general platform-event ingress (GitHub/Slack → bus) remains a
broader E-2 surface this does not fully cover. Recommend the brief/plan record
this as "E-2 first home (approval-inbound slice); general webhook ingress still
open."

## Decision Analysis

**Framework selected:** Reversibility Filter → Weighted Decision Matrix, with a
Pre-Mortem on the material risk and a full 12-detector bias pass. Rationale: the
threshold answers turned an open spectrum into a **concrete multi-option identity/
transport choice** (Route α vs Route β vs a chat-ops channel vs pure-local
G-3.1), which the auto-selection table routes to the Weighted Decision Matrix;
the freshness/no-replay requirement is a security-critical property warranting a
Pre-Mortem.

**Reversibility:** **Two-Way Door** for Route α (a tailnet-served local endpoint
+ a token gate is removable; no external account provisioned, no public surface,
no data migration). Route β (Entra OIDC app registration) has mild one-way
friction (a registered app, a dependency in the trusted surface). The gate itself
(code-enforced refuse-without-token) is cheaply revertible. ⇒ deeper analysis
warranted for the *identity route* choice, not for the overall shape.

**Options scored** (0–10 per cell × weight; higher = better). "Identity strength"
= how well it proves *which authenticated human* approved; "buildable-now" = fits
single-operator/near-term with stdlib + already-deployed infra:

| Criterion | Weight | α: Tailscale-injected identity + G-3.1 token | β: Direct Entra OIDC app + G-3.1 token | γ: Chat-ops (Slack/Discord/SMS) + token | δ: Pure-local G-3.1 (OS-perm only, no identity capture) |
|---|---|---|---|---|---|
| Buildable now (stdlib, no new infra) | 10 | 9 → **90** | 5 → **50** | 3 → **30** | 10 → **100** |
| Identity strength (which human approved) | 8 | 8 → **64** | 10 → **80** | 6 → **48** | 3 → **24** |
| No new standing/public network surface (dodges the 8B/E-2 trap) | 8 | 9 → **72** | 7 → **56** | 4 → **32** | 10 → **80** |
| Code-enforced refuse-without-fresh-token (answer 5) | 9 | 9 → **81** | 9 → **81** | 9 → **81** | 9 → **81** |
| Freshness / no-replay (minutes window) | 9 | 9 → **81** | 9 → **81** | 8 → **72** | 8 → **72** |
| Out-of-band-ness (compromised session can't forge it) | 8 | 8 → **64** | 9 → **72** | 8 → **64** | 3 → **24** |
| Single-operator near-term fit (answer 4) | 7 | 9 → **63** | 6 → **42** | 4 → **28** | 8 → **56** |
| Path to multi-principal/hosted later | 4 | 7 → **28** | 9 → **36** | 6 → **24** | 2 → **8** |
| **Total** | | **543** | **498** | **379** | **445** |

**Recommended: Route α — Tailscale-injected identity + a G-3.1-style
freshness-bound HMAC approval token + a code-enforced fail-closed write-gate +
a generalized signature-gated `tier3-writer` executor. Score 543.**

**Caveats where the winner scores poorly / close calls:**
- **α vs β on identity strength (64 vs 80) and future multi-principal (28 vs 36):**
  β's explicit Entra assertion is genuinely stronger and more portable. α wins
  overall on *buildable-now* (90 vs 50) and *near-term fit* (63 vs 42), which are
  the operator's stated priorities (answers 4 + 5). **This gap is exactly the one
  remaining operator sub-decision** — α is recommended for now, β is the documented
  upgrade path if/when the multi-principal trigger fires.
- **δ (pure-local G-3.1) scores surprisingly high (445)** on buildable-now and
  no-surface — but its *identity strength* (24) and *out-of-band-ness* (24) are
  poor: it proves "the key-holder on this box approved," not "an
  Entra-authenticated human approved out-of-band." If the threat model is a
  *compromised session on the operator's own box*, δ's key may be in the same
  blast radius. α is preferred because it adds real out-of-band identity capture
  for modest extra cost while keeping δ's fail-closed token gate.
- **γ (chat-ops) is dominated** — it scores worst on the operator's top-weighted
  buildable-now criterion (needs net-new bot/Twilio/OAuth infra) and is not
  meaningfully stronger elsewhere. Correctly de-prioritised by the answers.

**Pre-Mortem (assume the recommended α failed):**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Token replay** — an old approval reused to authorise a later write | M | H | Freshness bound (`max_age` = minutes) + content-binding: the token's HMAC covers *this exact change hash*, so it authorises only that change, and only within minutes. Both already in `validate()`. |
| 2 | **Gate bypass** — a Tier-3 write path exists that doesn't call the check | M | H | Single choke-point: the code gate runs in the `tier3-writer` executor AND (belt-and-braces) as a preflight over the Tier-3 path-set; conformance test asserts no Tier-3 write path lacks the gate. Same discipline as `boundary.decide()` REFUSE-on-doubt. |
| 3 | **Identity spoof on the local endpoint** — a non-operator process hits `127.0.0.1` and gets counted as approved | M | H | Bind localhost + require the request to arrive via `tailscale serve` (tailnet-authenticated); resolve identity via `tailscale whois`, never trust an unauthenticated header on a raw port. Reject any request whose identity can't be resolved (fail-closed). |
| 4 | **Key compromise** — the HMAC key leaks, tokens become forgeable | L | H | Key stays `chmod 600` owner-only (the `operating-posture.md` key-protected floor, retained in both modes); key lives outside the agent surface (`GLEIPNIR_MARKER_KEY_FILE`, the S-2 location). Same posture G-3.1 already relies on. |
| 5 | **Clock skew** invalidates genuine fresh tokens or admits stale ones | L | M | Single-host mint+validate (same clock); `validate()` already rejects future-dated and over-age. Minutes-window tolerates normal skew. |

**Top risks:** #1, #2, #3 — all mitigated by mechanisms G-3.1/`boundary.py`
already implement (content-binding, freshness, fail-closed choke-point) plus
tailnet-authenticated transport. **Verdict: Proceed with mitigations.**

**Bias check (12 detectors run; top matches surfaced):**
- ⚠️ *IKEA Effect (low-moderate):* the design leans hard on **our own** G-3.1 and
  the tailnet we already run. Mitigation: the matrix scores α on independent
  criteria (identity strength, out-of-band-ness, no-surface), not on "it's ours."
  α still leads even discounting reuse — and where β is genuinely stronger
  (identity), that gap is surfaced as the explicit open sub-decision rather than
  buried.
- ⚠️ *Anchoring (mild):* answer 1's "we already have Entra + Tailscale" strongly
  anchors toward Route α. Mitigation: β (fuller OIDC) and γ (chat-ops) and δ
  (pure-local) were each scored on the same criteria; α wins on the operator's
  *own* stated priorities, not merely because it was mentioned first.
- ⚠️ *Scope Creep (checked, largely averted):* answer 3 widened scope to ALL
  Tier-3 — a legitimate operator choice, not creep. The design *resists* further
  creep by explicitly NOT pulling in Tier-2/G-4c generalization now and NOT
  claiming to close all of E-2 (only the approval-inbound slice).
- (Others — confirmation, sunk-cost, status-quo, bandwagon, authority,
  survivorship, recency, availability, Dunning-Kruger — checked; none materially
  triggered. One note: Dunning-Kruger on OIDC/Tailscale internals is a *reason*
  to prefer Route α, whose tailnet-trusts-transport model needs no hand-rolled
  OIDC validation we might get subtly wrong.)

**This IS a converged-enough recommendation to write a Selected Approach** — the
operator's answers determined the shape decisively (single-operator, near-term,
reuse Entra/Tailscale + G-3.1, code-enforced freshness-bound gate, all-Tier-3,
compose-with-executor). The Selected Approach records that shape. The ONE
genuinely-open sub-decision (Route α vs β for identity capture) is flagged for a
final operator confirmation and does not alter the approach shape.

## Selected Approach — CONVERGED (Route α, pluggable resolver seam, 3-minute window)

**Choice:** A **composite signature-gated Tier-3 write path**, with identity
capture built behind a **pluggable identity-resolver seam** (Route α registered
now; future OIDC providers addable without editing the gate/mint code):

1. **Approval capture (out-of-band, identity-bearing, PLUGGABLE).** A tiny
   **stdlib `http.server`** listener binds `127.0.0.1`, reachable only via
   **`tailscale serve`** (tailnet-only; no public ingress). The operator approves
   a *specific pending Tier-3 change* by hitting the served URL, which shows the
   exact diff/content. Identity is resolved through a **generic
   `IdentityResolver` interface** (see the extensibility requirement below), with
   a **single registered resolver today — `TailscaleResolver`** (Route α: resolve
   the connecting tailnet identity via `tailscale whois`, which is
   Entra-backed). The approval-gate and token-mint code depend ONLY on the
   generic resolver contract, never on Tailscale specifics.
2. **Token mint (freshness-bound, content-bound HMAC — reuse G-3.1).** On
   approval the receiver **mints a short-lived signed token** of the same shape
   as `verify.marker.Marker`: HMAC (key from `GLEIPNIR_MARKER_KEY_FILE`,
   `chmod 600`) over `canonical(change_content_hash, approver_identity,
   minted_at)`, where `approver_identity` is whatever the resolver returned.
   **Validity window = 3 minutes** (see below).
3. **Deterministic write-gate (code-enforced fail-closed — reuse the
   `check`/`validate` + `boundary.decide()` pattern).** BEFORE any Tier-3 write
   executes, a preflight `validate`s the token against *this exact change*:
   version + **content-binding** + **HMAC** + **freshness**. Any failure/absence
   ⇒ **REFUSE** (exit non-zero), exactly like the marker check and
   `boundary.decide()`. **No valid fresh token bound to this change ⇒ no Tier-3
   write.** This is code, not documented discipline (answer 5).
4. **Executor (generalized, subsumes `decision-scribe`).** A **`tier3-writer`
   (signature-gated)** deny-by-default role writes the Tier-3 path-set
   (`agents/`, `skills/`, `goals/`, `stage-role-map.md`, `keys/`, `decisions/`)
   under the existing append-only/verbatim-provenance/verify-against-disk
   discipline — but ONLY after the gate passes. Holds no `question` (cannot
   self-originate approval), no git/bash/task. The paused `decision-scribe`
   proposal is **subsumed** (its disciplines carry over; scope widens to all
   Tier-3; the in-session-`question` gate is upgraded to the out-of-band token).

### Extensibility requirement (forward-looking design constraint — testable, NOT a comment)

Operator answer, verbatim: *"I'm happy with route alpha as we use tailscale...
but a future fix should open this up to other OIDC providers."* This is a
**binding, testable design constraint**, modelled EXACTLY on this session's
already-proven `git-diff-distill` content-handler plugin library
(`src/gleipnir/broker/git/content_handlers/{protocol.py,registry.py}`):

- **Contract half (mirrors `protocol.py`'s `Handler` Protocol +
  `ProcessedResult`).** A stdlib `typing.Protocol` **`IdentityResolver`** with a
  minimal surface — e.g. `can_resolve(request_ctx) -> bool` and
  `resolve(request_ctx) -> ResolvedIdentity` — where `ResolvedIdentity` is a
  frozen dataclass carrying only the identity string (+ provider tag), and
  **nothing token/gate-specific is reachable through the contract** (the same
  "structurally unreachable, not merely omitted" safety `protocol.py` documents
  and `TestStructuralSafety` proves via `inspect.signature`).
- **Dispatcher half (mirrors `registry.py`'s `register`/`dispatch`).** A generic
  resolver registry: `register(resolver)` + a `resolve(request_ctx)` that walks
  registered resolvers, first-match-wins, **fail-closed** if none resolves
  (reject the approval — never default to an unauthenticated identity). This
  dispatcher module contains **no** reference to Tailscale, Entra, or any
  concrete provider, and imports **no** concrete resolver — identical to the
  `registry.py` open/closed discipline.
- **The one registered resolver today:** `TailscaleResolver` (Route α),
  registered at the receiver's composition root (analogous to a broker's
  `mcp_server.py` calling `register(...)`), not inside the dispatcher.
- **The testable extensibility property (the actual acceptance criterion).**
  Mirroring `registry.py`'s "adding a new handler never requires editing this
  module": a test registers a **second, dummy resolver** (a fake OIDC provider)
  and asserts it is selected/used **without any edit to the approval-gate module,
  the token-mint module, or the dispatcher module** — proving a future Route β
  (direct Entra OIDC) or any other OIDC provider plugs in as a second resolver by
  registration alone. Plus a source-level structural test (like
  `test_broker_stdlib_only.py` part (ii) and `TestStructuralSafety`) asserting
  the gate/mint/dispatcher source never names a concrete identity provider.

This makes "open it up to other OIDC providers later" a **built-in seam with a
green test today**, not a deferred promise — the same shape the content-handler
library already demonstrates works.

### Freshness window — 3 minutes (concrete value within the confirmed 2–5 min band)

`validate()`'s `max_age_seconds` is set to **180 seconds (3 minutes)**.
Rationale: long enough for a human to receive the prompt, open the tailnet URL,
read the exact diff, and click Approve without racing a timer; short enough that
a captured/stale token is useless within a few minutes, giving the approval
genuine temporal immediacy relative to the write it authorizes (answer 5). 3 min
is the midpoint of the operator-confirmed 2–5 min band — deliberately not the
2-min floor (too tight for reading a real diff) nor the 5-min ceiling (wider
replay surface than needed). The plan should implement 180s as a named constant
(overridable, like the CLI's existing `--max-age`), not a magic literal.

**Rationale (overall):** matches every operator answer — single-operator/
near-term (α is stdlib + already-deployed infra), all-Tier-3 (executor scope),
code-enforced + freshness-bound (the G-3.1 `validate` gate at 180s), composed
with an executor, and future-extensible to other OIDC providers via the resolver
seam. It reuses tested primitives (G-3.1 mint/validate freshness + content-
binding; `boundary.decide()` fail-closed choke-point; the content-handler
dispatcher/handler open-closed pattern) rather than inventing anything, and it
dodges the standing-public-surface trap that got option 8B rejected by keeping
the listener tailnet-only. It gives **E-2 its first real component home**
(approval-inbound receiver), while honestly noting general platform-webhook
ingress remains a broader open E-2 surface.

**Buildable-now vs operator-setup vs cooperative-until-closed (honesty ledger):**
- **Buildable now (Python stdlib, agent-buildable, testable):** the token
  mint/validate (extend `src/gleipnir/verify/**` with a content+identity token
  mode), the fail-closed write-gate preflight, the local `http.server` receiver,
  the `tier3-writer` role skeleton, conformance tests (replay rejected, stale
  rejected, content-mismatch rejected, gate-bypass path absent).
- **Operator one-time setup (Tier-3 / OS acts, NOT agent-doable):** configure
  `tailscale serve` to front the endpoint; ensure `GLEIPNIR_MARKER_KEY_FILE`
  key exists `chmod 600`; if Route β is chosen, register the Entra OIDC app;
  apply the new/renamed `tier3-writer` agent file + the subsuming decision
  record (itself a Tier-3 write — the same bootstrap paradox the decision-scribe
  proposal noted: the FIRST application is an operator/build-mode act).
- **Cooperative-policy-until-closed (mirrors the AGENTS.md G-1/G-2/G-3 honesty
  convention):** until S-2 makes the key/gate agent-unreachable and S-3 preflight
  verifies it, the gate is honoured by the roster + the code path, not yet a
  substrate wall; label it "authored, not yet closed" like the other guards.

## Open Questions (final) — all convergence-blocking questions RESOLVED

- **Identity-capture route: RESOLVED — Route α (Tailscale-injected identity),**
  built behind the pluggable `IdentityResolver` seam so a future Route β (direct
  Entra OIDC) or any other OIDC provider registers as a second resolver without
  editing the gate/mint/dispatcher code (operator: *"happy with route alpha as we
  use tailscale... but a future fix should open this up to other OIDC
  providers"*).
- **Freshness window: RESOLVED — 3 minutes (180s)** within the operator-confirmed
  2–5 min band.
- **Remaining items are plan-time details, NOT convergence gates:** exact module
  layout, the resolver contract's precise method signatures, and conformance-test
  specifics are for `gleipnir-plan` (ATLAS) to specify — they do not require
  further operator decision.
- **Explicitly out of scope now (avoid scope creep):** generalizing the same gate
  to **G-4c Tier-2 promotions** (lessons/memory). Noted as a natural future
  extension; revisit when G-4c is built. The resolver seam and the token-gate are
  designed so that extension is additive, not a rewrite.

## Scope Sketch (post-convergence)

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| Signed-token primitive | `src/gleipnir/verify/**` — content+identity token mode reusing `mint`/`validate` (freshness, content-binding) |
| Write-gate (fail-closed) | new preflight check (pattern of `verify/__main__.py:_cmd_check` + `preflight/boundary.decide()`), run before any Tier-3 write |
| Approval receiver (E-2 first home) | new stdlib `http.server` listener under `src/gleipnir/**`, tailnet-served (`tailscale serve`, localhost bind) |
| Identity-resolver seam (pluggable) | new stdlib `Protocol` `IdentityResolver` + `ResolvedIdentity` (contract half) + a `register`/`resolve` dispatcher (fail-closed), mirroring `broker/git/content_handlers/{protocol.py,registry.py}`; ONE registered resolver now — `TailscaleResolver` (Route α); extensibility + structural tests prove a 2nd resolver registers without editing gate/mint/dispatcher |
| Executor role | new `.gleipnir/agents/tier3-writer.md` (subsumes `decision-scribe`); deny-by-default, Tier-3 path-set, gate-preceded |
| Policy / provenance | new `.gleipnir/decisions/*.md` (subsumes decision-scribe record; narrows "no agent writes Tier-3, ever" to "only the signature-gated `tier3-writer`, only with a valid fresh token") |
| Key floor | `GLEIPNIR_MARKER_KEY_FILE` / `keys/` `chmod 600` (retained both modes) |
| Threat model | `operating-posture.md` linkage (out-of-band control that matters more outside the uncaged envelope; caged-mode interaction) |
| Seam | E-2 partial close (approval-inbound receiver home; general webhook ingress still open) |
