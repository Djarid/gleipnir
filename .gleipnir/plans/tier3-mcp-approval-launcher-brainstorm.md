# Design Brief: Tier-3 approval listener as an opencode-spawned global MCP (supersedes Decision 15's "no auto-start"; key-isolation via env-referenced secret)

_Author: `gleipnir-brainstorm`. Tier-0 artifact; disposable; NOT authoritative.
This grounds and records; it does not itself decide material tradeoffs._

> **STATUS: CONVERGED — ready to hand to `gleipnir-plan`.** The core shape
> (points 1–6 below) and **all five open items (O-1 through O-5)** are now
> **operator-ratified** — the shape in direct orchestrator↔operator conversation
> earlier this session (the operator explicitly asked to stop using the
> `question` tool for this exploratory back-and-forth and discuss directly), and
> O-1 through O-5 likewise ratified directly by the operator (orchestrator↔operator,
> plain conversation, this session) and relayed to this subagent for recording.
> Those are recorded here verbatim/faithfully and cited to that conversation —
> **not re-decided by this subagent.** What this brief adds on top: (a) a genuine
> Explore/verify pass on the mechanics (points 7–9 of the delegation), (b) my own
> recommendation + Decision Analysis for the two genuinely-open *implementation*
> forks, and (c) the now-closed open items. O-1 was resolved empirically (this
> repo's own live `{env:VAR}` precedent). O-2/O-4/O-5 are resolved/approved.
> O-3 is split: O-3(a) (create a new untracked repo-local `.envrc`) is resolved,
> and O-3(b) (the global `.envrc`/`.env*` agent read+edit deny) is **explicitly
> DEFERRED and recorded as a named, honest, deliberately-accepted residual
> security gap** (isolation-by-convention, not -by-capability, until built) — it
> does **not** block this feature's build, exactly like the E-1/E-2 seams carried
> elsewhere in this repo. Nothing further gates the hand-off to planning.

## Problem Statement

The already-merged `tier3-signed-approval` subsystem
(`decisions/tier3-signed-approval.md`) works but has an **operator-run,
manually-started** approval listener: `bin/gleipnir-approval-server` is a thin
shim the operator starts by hand and Ctrl-Cs to stop, deliberately **never**
auto-started and **never** on any agent's allowlist (Decision 15 of
`plans/tier3-signed-approval.md`; the shim header at
`bin/gleipnir-approval-server:4-18`; the `server.py` docstring "No auto-start
(Decision 15)... not a daemon, not launched by any agent").

The operator wants to remove that manual step: have **opencode itself spawn the
listener** as a **global local MCP** at launch, and additionally expose an
**agent-facing tool** (working name `request_approval`) so that when an agent
hits a gated Tier-3 write, it can stage the pending content and get back the
`tailscale serve`-fronted `/approve/<hash>` review URL for the operator to
approve on a separate authenticated device.

The design hinges on a **trust correction** the operator surfaced this session:
Decision 15's rationale conflated *who launches the listener process* with *who
can mint a valid approval token*. Those are separable. The forgeable-activation
concern is real but was **miscalibrated to process-launch**; the correct locus
is **key-readability**. Launching the process is fine for opencode/an MCP config
to do (process supervision only) **as long as the signing key is never reachable
by the agent's tool surface**, and identity is still resolved via `tailscale
whois` against a separate authenticated tailnet peer at request time.

## Constraints (grounded; carried over, not re-litigated)

- **The crypto core is already correct, tested, and MUST NOT change.**
  `src/gleipnir/approval/{token.py,gate.py,__main__.py,identity/**}`,
  `verify/marker.py` — content+identity+freshness binding, 180s window,
  fail-closed gate — are untouched by this design. This is a
  *process-supervision + agent-tool-surface* change, not a crypto change.
- **stdlib-only enforcement core** (`decisions/runtime-and-deps.md`). The MCP
  process itself must not drag a new Python runtime dependency into the trusted
  surface. (An MCP-protocol layer, if one is needed, is the one place this must
  be watched — see fork (a).)
- **Tailnet-only transport** via `tailscale serve` fronting a `127.0.0.1`
  listener — unchanged.
- **The write-block hook (`.gleipnir/plugins/tier3-gate.ts`) already exists and
  already stages `pending-<hash>.json` on REFUSE and appends an
  `/approve/<hash>` URL** (verified: `tier3-gate.ts:132-152`, `stagePendingContent`
  at `:408-426`, `buildApprovalUrl` at `:435-445`). The proposed
  `request_approval` agent tool overlaps heavily with what the hook already
  does; the design must not duplicate that logic (fork (b) addresses this).
- **Tier-3 immutability from the agent side is a capability, not a promise.**
  `opencode.jsonc` is itself Tier-3 enforcement wiring (enforcement-path set
  `E`, `stage-role-map.md` Axis 2(a)): it is tracked, agent-readable, and
  operator-applied. **No literal secret may ever be written into it.**

## Explore — verification of the delegation's load-bearing facts

Every fact below that I could reach with a repo tool call, I verified
independently and cite exactly. Host-shell facts I cannot run (no `bash`
capability) I mark as **relied-on-from-the-session-prompt**, not independently
re-verified.

### Point 7 — is there a filesystem read/edit deny on `.envrc`/`.env*` today? NO.

- `grep 'env'` over `.gleipnir/agents/*.md` returns **three** matches, and only
  one is in a deny context:
  - `gleipnir-code.md:58` → `"env*": deny` — this line sits **inside the `bash:`
    block** (that block runs `.gleipnir/agents/gleipnir-code.md:31-59`,
    `bash:` at `:31`, closing with `"curl*": deny` at `:59`). It is a
    **bash-command deny** (blocks running the `env` shell command, alongside
    `git*`/`sh*`/`bash*`/`curl*`), **NOT** a filesystem read/edit glob on
    `.envrc`/`.env*` files. Confirmed by reading the full frontmatter.
  - `project-mgr.md:40` and `git-ops.md:81` → prose mentions of
    `GITLAB_TOKEN`/`GITHUB_TOKEN` env injection. Not denies.
- `grep '\.envrc|\.env'` over `.gleipnir/agents/*.md` → **No files found.**
- The full `grep 'deny'` dump of every roster agent (72 matches) shows every
  `edit`/`read`/`bash`/tool deny in the roster. **None** is a filesystem glob
  for `.envrc` or `.env*`. `gleipnir-code` has `read: allow` (`:28`) with **no
  `.envrc`/`.env*` read exception**, and its `edit` denies are `.gleipnir/**`,
  `.git/**`, `.github/**`, `src/gleipnir/preflight/**` — **not** `.envrc`.

**Conclusion (verified):** the isolation property this design leans on —
"`.envrc`/`.env*` is unreadable to the agent's tool surface" — **does not exist
as a capability today.** Any agent with `read: allow` (e.g. `gleipnir-code`,
`quality-reviewer`, `orchestrator`) can `read` a repo-root `.envrc` if one
exists. This is a real, named prerequisite (delegation point 5), not a
background assumption.

### Point 8 — does `.envrc` exist in the repo root today? NO.

- `glob .envrc` (repo root) → **No files found.** `.envrc` does not exist.
- Host facts **relied-on-from-the-session-prompt** (I have no `bash`, cannot
  independently run `git status`/`which`): only `.venv/` and a gitignored
  `.gleipnir/agent-identity.env` are present; `direnv` **is** installed on the
  host (`which direnv` succeeds per the prompt). I did not re-verify these two
  and flag them as prompt-sourced.

### Point 9 — `{env:VAR}` substitution for a LOCAL-MCP `environment:` block? **NOT documented. Real open feasibility question.**

Re-fetched `https://opencode.ai/docs/mcp-servers` this session. Findings, quoted:

- The **local** MCP `environment` block is documented with a **literal-value**
  example only:
  `"environment": { "MY_ENV_VAR": "my_env_var_value" }`, and the Options table
  entry reads verbatim: *"`environment` | Object | Environment variables to set
  when running the server."* **No `{env:VAR}` example, and no statement that
  substitution is applied to this block.**
- The `{env:VAR}` substitution pattern is documented **only in the REMOTE-MCP
  sections**:
  - remote `oauth`: `"clientId": "{env:MY_MCP_CLIENT_ID}"`,
    `"clientSecret": "{env:MY_MCP_CLIENT_SECRET}"`;
  - remote `headers`: `"Authorization": "Bearer {env:MY_API_KEY}"` and
    `"CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}"`.

**Conclusion (verified against the docs):** the docs do **NOT** document
`{env:VAR}` substitution as generally available for the `environment:` block of
a **local** MCP entry. It is documented only for remote-MCP `headers`/`oauth`
fields. **This is the single load-bearing feasibility fact for the whole
key-isolation design, and it is currently UNRESOLVED in the design's favour.**
Per the delegation I do **not** assume it works — I name it as a real open
question (see Open Items O-1).

> Why this is load-bearing: point 4's key-isolation claim requires that the
> MCP's `environment:` in `opencode.jsonc` be a **reference** (e.g.
> `{env:GLEIPNIR_MARKER_KEY_FILE}`) resolved from the launching shell, so the
> literal key/path is **never** written into the tracked, agent-readable
> `opencode.jsonc`. If local-`environment` does **not** honour `{env:VAR}`, the
> obvious naive workaround — inlining the literal value — is **forbidden** (it
> would put a Tier-3 secret into an agent-readable tracked file), so a different
> mechanism is required (see fork/mitigation notes and O-1).

### Adjacent facts verified while exploring

- `tier3-gate.ts` already binds an approval URL via `GLEIPNIR_APPROVAL_BASE_URL`
  (`:435-445`) and stages `pending-<hash>.json` under `.gleipnir/var/tmp/`
  (`:408-426`). A `request_approval` tool would ride on this existing staging,
  not reinvent it.
- The existing UX thread (`plans/tier3-approval-ux-brainstorm.md`) already
  converged the staging/review-page/one-click-approve experience. This MCP
  thread is **orthogonal**: it changes *how the listener is launched* and *adds
  an agent-facing request path*, layered on that already-converged UX. Filename
  `tier3-mcp-approval-launcher-brainstorm.md` chosen to avoid collision with
  both `tier3-signed-approval-brainstorm.md` and `tier3-approval-ux-brainstorm.md`
  (naming precedent `<feature>-brainstorm.md` confirmed by `ls *brainstorm*`).
- No `.gleipnir/plugins/**` or `src/gleipnir/approval/**` change is *required by
  the converged shape* beyond the listener's entrypoint and the new MCP tool
  surface; the crypto/gate files stay untouched (constraint above).

## The design ALREADY CONVERGED this session (recorded, cited to the session's direct orchestrator↔operator conversation — NOT re-decided here)

Recorded faithfully per the delegation. Citation for all six: **this session's
direct orchestrator↔operator conversation** (operator instruction: "stop using
the Q tool while we discuss"). These are the operator's decisions, not this
subagent's.

1. **[CONVERGED] Global local MCP, spawned by opencode, replaces the manual
   start.** On MCP startup it starts/binds the approval listener
   (`127.0.0.1:8765`, unchanged; `tailscale serve` still fronts it, unchanged).
2. **[CONVERGED] The MCP also exposes an agent-facing tool** (working name
   `request_approval`) letting an agent, when a gated Tier-3 write is about to be
   attempted, stage the pending content (same `pending-<hash>.json` staging the
   `tier3-gate.ts` hook already writes on REFUSE) and get back / have opened the
   `tailscale serve`-fronted `/approve/<hash>` review URL for out-of-band,
   separate-device operator approval.
3. **[CONVERGED] Trust correction (the key finding).** Operator's words:
   *"starting the process is NOT the same as using the service to sign shit."*
   Launching the listener MAY be done by opencode/an MCP config (process
   supervision only) **provided the SIGNING KEY (`GLEIPNIR_MARKER_KEY_FILE` /
   the HMAC key it points to) is never reachable by the AGENT's tool-calling
   surface** (bash/read/etc.), and identity is still resolved via `tailscale
   whois` against a genuinely separate authenticated tailnet peer at request
   time. Decision 15's forgeable-activation concern is REAL but was miscalibrated
   to "who launches the process"; the correct locus is **"who can read the key."**
   (See the explicit supersession clause below.)
4. **[CONVERGED, explicitly INTERIM] Key source = environment variable, for
   now.** The MCP subprocess's `environment:` value in `opencode.jsonc` must be a
   **reference** resolved from the operator's launching shell (sourced via
   `.envrc`/direnv) — e.g. `{env:GLEIPNIR_MARKER_KEY_FILE}` or equivalent —
   **never a literal key/path written into the tracked `opencode.jsonc`.** The
   isolation property: `.envrc`/`.env*` must be unreadable to the agent's tool
   surface, so the agent can supervise-launch the MCP but can never obtain the
   key value the MCP's process env holds. **Vault (HashiCorp Vault / 1Password /
   similar) is the explicitly-named STRONGER future option, deliberately
   DEFERRED** — recorded here as a named deferral: *env var now, vault is the
   early hardening candidate.*
5. **[CONVERGED as a real, named prerequisite — NOT yet built]** For point 4's
   isolation to be true, **every roster agent** (not just `gleipnir-code`) needs
   an actual filesystem `read`/`edit` deny on `.envrc` and `.env*`. Verified
   above (point 7): **none exists today.** This is itself Tier-3
   enforcement-bearing (agent frontmatter permission blocks). It belongs in this
   plan's Decisions index as a named decision row, under the repo's own honesty
   ledger: **until the global deny exists and is real, this design is
   "isolation-by-convention," not "isolation-by-capability."** That gap must be
   named in the plan, not glossed. (The operator converged that this is required;
   whether it is built in *this* plan or a follow-up is a scoping call — see O-3.)
6. **[CONVERGED context] `.envrc` does not currently exist** (verified, point 8).
   Whether authoring it is in scope for this plan or a separate follow-up is
   flagged (O-3); my recommendation is below.

**Nothing in points 1–6 was decided by me.** Where I could not fully stand a
point up on verified mechanics, I did not soften the operator's decision — I
recorded it as converged **and** raised the mechanics gap separately as an open
item (O-1 for point 4's `{env:VAR}` dependency; O-3 for point 5/6 scoping).
That is the honest split the delegation asked for.

## Propose — the two genuinely-open IMPLEMENTATION forks (my analysis; operator decides only if a fork turns out material)

These are implementation forks the delegation named. Both are **within the
converged shape**; I give my recommendation. Neither is a re-litigation of
points 1–6.

### Fork (a) — does the MCP reuse `src/gleipnir/approval/server.py` as-is, or need a new thin MCP-protocol wrapper module?

**Approach A1 — MCP process = the existing `server.py` listener, spawned
directly.** The MCP `command` execs `python -m gleipnir.approval.server` (the
exact target `bin/gleipnir-approval-server` already execs, per the shim at
`:30`). The "MCP" is really just opencode supervising the existing stdlib HTTP
listener as a managed subprocess.
- Pro: zero new module; the crypto/HTTP surface stays exactly as tested.
- Pro: stdlib-only preserved trivially (no MCP SDK).
- Con: an opencode **local MCP** speaks the **MCP protocol over stdio**, not
  raw HTTP. A plain `http.server` on `127.0.0.1:8765` is **not** an MCP server.
  So "spawn `server.py` as the MCP" only supervises the process; it does **not**
  by itself give opencode an MCP tool (`request_approval`) — that needs an MCP
  protocol endpoint. A1 alone therefore satisfies point 1 (launch) but **not**
  point 2 (agent-facing tool).

**Approach A2 — a new thin MCP-protocol wrapper module that (i) starts/owns the
HTTP listener in-process and (ii) exposes the `request_approval` MCP tool.** A
small `src/gleipnir/approval/mcp.py` (or similar) is the MCP `command` target;
on startup it binds the same `127.0.0.1:8765` listener (importing `server.py`'s
handler, not duplicating it) and registers the MCP tool that stages content +
returns the `/approve/<hash>` URL.
- Pro: satisfies **both** point 1 and point 2 in one process.
- Pro: keeps `server.py`'s HTTP/crypto surface reused (import, don't fork).
- Con: an MCP-protocol wrapper likely needs an **MCP server library** — a
  **candidate new runtime dependency**, which collides with the stdlib-only
  enforcement-core constraint. This must be checked: is there a stdlib-only way
  to speak MCP-over-stdio, or is the MCP tool surface acceptably *outside* the
  enforcement core's stdlib boundary (it is a supervision/UX convenience, not a
  crypto/gate path)? That classification is itself worth an operator/architect
  note (see O-2).

**My recommendation (NOT operator-decided): A2, but structured so the MCP
wrapper is a thin, import-only shell over the untouched `server.py`, and the
stdlib-boundary question for the MCP library is raised explicitly at plan time.**
Rationale: point 2 (the agent-facing tool) is an explicit converged requirement,
and A1 cannot deliver it — so a protocol wrapper is needed regardless. Keeping
it import-only over `server.py` preserves the "crypto core untouched" constraint.
The one real risk (a new dependency vs. stdlib-only) is surfaced, not buried
(O-2). **Reversibility: two-way door** — the wrapper is additive and removable;
falling back to the manual shim is always possible.

### Fork (b) — exact `request_approval` tool shape: auto-open a browser, or return a URL string?

**Approach B1 — return the `/approve/<hash>` URL string** (and stage the pending
content). The agent surfaces the URL to the operator (who opens it on a separate
authenticated device); no browser is launched by the framework.

**Approach B2 — auto-open a browser** to the review page from the MCP host.

**My recommendation (NOT operator-decided): B1 (return the URL string), plus
reuse the hook's existing staging rather than re-implementing it.** Rationale:
1. The whole design's out-of-band security property is that approval happens on
   a **separate authenticated device** (point 3; `tailscale whois` identity).
   Auto-opening a browser **on the MCP/agent host** actively undercuts that —
   it nudges approval onto the same machine as the (possibly compromised)
   session, weakening the separation the token model depends on. B2 is a mild
   security anti-pattern here.
2. `tier3-gate.ts` **already** builds this exact URL (`buildApprovalUrl`,
   `:435-445`) and stages `pending-<hash>.json` (`:408-426`). B1 lets
   `request_approval` **reuse** that staging/URL machinery (satisfying "do not
   duplicate the hook's logic"); B2 adds host-side browser-launch code that is
   pure surface with no security benefit.
3. B1 degrades gracefully when `GLEIPNIR_APPROVAL_BASE_URL` is unset (the hook
   already has a relative-hint fallback, `:441-444`).

**Reversibility: two-way door.** A tool that returns a string is trivially
changed later; auto-open could be added as an opt-in flag if the operator ever
wants it, without redesign.

## Decision Analysis

**Framework selected:** Reversibility Filter → Pros-Cons-Fixes for each fork
(both are bounded binary/near-binary implementation choices, two-way doors), plus
a targeted **Pre-Mortem** on the one genuinely material, less-reversible element
that the *converged shape* introduces — the **key-exposure surface** created by
letting opencode spawn the key-holding process. Rationale: per the auto-selection
table, binary implementation choices route to Reversibility→Pros-Cons-Fixes; the
security-critical key-exposure property warrants a Pre-Mortem. The two
implementation forks are **not** material tradeoffs requiring operator
convergence (both two-way doors with a clear recommended answer); the
key-exposure surface and the `{env:VAR}` feasibility gap **are** the consequential
parts, and those are surfaced to the operator as open items rather than resolved
here.

**Reversibility:**
- Fork (a): **two-way door** (additive wrapper; manual shim remains a fallback).
- Fork (b): **two-way door** (string vs browser is a trivially-changed tool
  detail).
- The **converged shape's key-exposure surface** (opencode now spawns the
  key-holding process, and the key reference lives in config/`.envrc`): this is
  the closest thing to a **one-way-ish** element, because it changes the threat
  surface — hence the Pre-Mortem below. But note: the *operator already converged
  this shape*; the Pre-Mortem exists to surface residual risks and required
  mitigations for the plan, not to reopen the decision.

**Pros-Cons-Fixes — Fork (a) (recommended A2):**

| Con | Fix |
|-----|-----|
| MCP wrapper may pull a non-stdlib MCP library (violates enforcement-core stdlib-only) | Raise at plan time (O-2): confirm a stdlib-only MCP-over-stdio path, OR classify the MCP tool surface as a supervision/UX layer explicitly *outside* the stdlib-bound enforcement core (it touches no crypto/gate path). Do not let the library into `token.py`/`gate.py`/`marker.py`. |
| Wrapper could accidentally duplicate `server.py` HTTP/crypto logic | Import `server.py`'s handler; forbid re-implementation (a plan constraint + a structural test, mirroring the existing "gate/mint name no concrete provider" source-scan discipline). |

**Pros-Cons-Fixes — Fork (b) (recommended B1):**

| Con | Fix |
|-----|-----|
| Returning a URL is slightly less "one-click" than auto-open | The already-converged UX thread's staged review page + `GLEIPNIR_APPROVAL_BASE_URL` full-URL rendering already make it one-click **on the separate device** — which is the security-correct place, not the host. |

**Pre-Mortem (assume the converged shape failed — key exposure):**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **`{env:VAR}` not honoured for local `environment`; someone inlines the literal key/path into `opencode.jsonc`** (a tracked, agent-readable, enforcement-path-`E` file) → key/path leaks to any `read:allow` agent | **M–H (docs do NOT confirm substitution — O-1)** | **H** | BLOCK on O-1 before build: confirm substitution works for local `environment` (test it), OR choose an alternate injection that never writes the literal into tracked config (e.g. the MCP command reads the key file path from the *inherited* process env set by `.envrc`/direnv at opencode launch, with NO value in `opencode.jsonc` at all). Never inline the literal. |
| 2 | **`.envrc`/`.env*` is agent-readable** (verified true today, point 7) → an agent `read`s the key path (and, if the key file itself is agent-readable, the key) | **H (true today)** | **H** | Point 5's prerequisite: add a filesystem `read` **and** `edit` deny on `.envrc`/`.env*` to **every** roster agent before this is relied on as capability. Until then label the design **isolation-by-convention, not -by-capability** (honesty ledger). Also confirm the key *file* itself (`GLEIPNIR_MARKER_KEY_FILE` target) is outside every agent's `read` grant, `chmod 600`. |
| 3 | **The key file path is agent-readable even if `.envrc` is denied** (the path is only a pointer, but the file it points to is the real secret) | M | H | Ensure the key file lives at a path denied to all agents' `read` (the S-2 key location); the env var carries only the *path*, and the *file* is unreadable. This is the existing `keys/**` RO_AND_UNREADABLE posture in `preflight/boundary.py` — confirm the approval key is under it. |
| 4 | **Auto-started MCP means the listener runs in every session, widening the window a stale/rogue approval endpoint is live** | L–M | M | Listener stays `127.0.0.1`-bound + tailnet-only via `tailscale serve`; identity still resolved per-request via `tailscale whois` (no ambient trust); 180s token freshness unchanged. Auto-start does not weaken the token gate — it only removes the manual launch step (the converged trust correction, point 3). |
| 5 | **Forgeable-activation regression** — the very thing Decision 15's header warned about | L | H | The supersession clause (below) is explicit: activation-by-launch was the *wrong* locus; the guard's integrity rests on **key-unreachability + per-request `tailscale whois` identity**, both preserved. The population that could "forge activation" (the agent) still cannot read the key or mint a token. |

**Top risks: #1 and #2** — and critically, **both are currently UNMITIGATED**:
#1 depends on the unresolved `{env:VAR}` feasibility (O-1), and #2 is verified
*true today* (no `.envrc`/`.env*` deny exists, point 7 / O-3). **Verdict:
Proceed to plan ONLY after the operator resolves O-1 and O-3;** the converged
shape is sound, but its security property is not real until those two are closed.

**Bias check (12 detectors run; top matches surfaced):**
- ⚠️ *Confirmation Bias (guard against):* the session's converged shape is
  attractive and it would be easy to write the mechanics up as "works." I
  deliberately did **not** — the `{env:VAR}` local-`environment` support is
  **not** in the docs, and I recorded that as an open feasibility question
  rather than assuming the design's happy path.
- ⚠️ *Status Quo Bias (checked, mild):* Decision 15's "no auto-start" is the
  incumbent; the operator's trust correction (point 3) is the reasoned override,
  not mere change-for-its-own-sake — the incumbent rationale was *miscalibrated*,
  which is a merits-based reason to supersede.
- ⚠️ *Scope Creep (checked, averted):* vault is explicitly deferred (point 4);
  Tier-2/G-4c generalization is untouched; the two forks are kept to bounded
  implementation choices. The one legitimate scope addition (the `.envrc`/`.env*`
  global deny, point 5) is a *converged prerequisite*, not creep — but its
  in-this-plan-vs-follow-up placement is flagged (O-3), not silently expanded.
- (Others — anchoring, sunk-cost, availability, bandwagon, authority,
  survivorship, recency, Dunning-Kruger, IKEA — checked; none materially
  triggered. Note: Dunning-Kruger on opencode's config-substitution internals is
  precisely *why* O-1 is flagged as a must-verify rather than assumed.)

## Supersession clause — Decision 15 and the shim/docstring forgeable-activation framing

**This brief explicitly supersedes** the following, on the operator-converged
rationale of point 3:

1. **`plans/tier3-signed-approval.md` Decision 15** ("Listener module +
   start/stop… No auto-start"; rejected alternative "An auto-started/daemonized
   listener… not in the brief; 'cooperative-until-closed' framing wants an honest
   operator-run process"). **Superseded:** an opencode-spawned MCP MAY launch the
   listener. The "honest operator-run process" concern is re-located: honesty and
   integrity are guaranteed not by *manual launch* but by **key-unreachability
   (the agent cannot read `GLEIPNIR_MARKER_KEY_FILE` or its target) + per-request
   `tailscale whois` identity resolution against a separate authenticated tailnet
   peer**. Auto-start supervises the *process*; it grants no ability to *mint*.
2. **`bin/gleipnir-approval-server` header (`:4-18`)** — "run by the OPERATOR,
   manually… never by an in-framework agent, and never auto-started" and "a guard
   whose activation is validated by the population it guards is the G-3
   forgeable-evidence failure applied to activation." **Corrected:** the
   forgeable-activation concern conflated *process launch* with *token minting*.
   The population that could forge — the agent — still cannot read the key or
   mint a token; launching the process is not "validating activation by the
   guarded population," because launching confers no signing capability. The
   header's warning should be **narrowed** to: *the agent must never be able to
   read the signing key or mint a token* (which remains true and enforced), not
   *the agent/opencode must never launch the process*.
3. **`src/gleipnir/approval/server.py` docstring** — "No auto-start (Decision
   15)… not a daemon, not launched by any agent." **Corrected** to reflect that
   opencode/an MCP config MAY launch it as a supervised subprocess, provided the
   key stays unreachable to the agent tool surface.

> **These are Tier-3 / enforcement-adjacent edits** (the shim is `bin/**`
> executable; `server.py` is source; Decision 15 lives in a plan; the framing
> also touches the durable `decisions/tier3-signed-approval.md`). The actual
> edits are **applied by operator/build-mode**, and the durable rationale must be
> recorded in `decisions/tier3-signed-approval.md` (Tier-3, operator-authored) —
> this Tier-0 brief only *names* the supersession; it does not perform it.

## Open Items — ALL RESOLVED (operator-ratified directly; recorded here for `gleipnir-plan`)

All five items below have been **ratified directly by the operator**
(orchestrator↔operator, plain conversation, this session) and relayed to this
subagent for faithful recording — **not** obtained or decided by this subagent.
O-1 was resolved empirically by this repo's own live precedent; O-2, O-4, O-5
are resolved/approved; O-3 is split into O-3(a) (RESOLVED) and O-3(b) (DEFERRED
as a named, honest, deliberately-accepted residual security gap). **No open item
remains that gates the hand-off to `gleipnir-plan`.**

- **O-1 [RESOLVED — empirically, by this repo's own live precedent]: opencode
  DOES substitute `{env:VAR}` inside a *local* MCP's `environment:` block.** The
  earlier doc-based caution (the docs document `{env:VAR}` only for *remote*-MCP
  `headers`/`oauth`, with local `environment` shown only via a literal-value
  example — point 9) was reasonable but is now **falsified by a working,
  load-bearing precedent already running in this exact repo**: `opencode.jsonc`'s
  `gleipnir-pm` broker is a `"type": "local"` MCP whose `environment` block uses
  `"GITLAB_TOKEN": "{env:GITLAB_TOKEN}"` / `"GITHUB_TOKEN": "{env:GITHUB_TOKEN}"`
  substitution, and `project-mgr` has used exactly this mechanism all session to
  authenticate real PR/MR operations against live GitHub/GitLab (PR#1/PR#2 merges
  via `gleipnir-pm_pr_create`, per SESSION-STATE). The `{env:VAR}` mechanic is
  therefore **proven** for local-MCP `environment` blocks by this repo's own
  config; `GLEIPNIR_MARKER_KEY_FILE` (or the raw HMAC key, per whichever the plan
  stage ultimately specifies) slots into the new approval-launcher MCP's
  `environment` block the identical way — **no new mechanism needs inventing and
  no further feasibility test is needed before planning.** **Under no
  circumstance inline the literal key/path into `opencode.jsonc`** (the reference
  form, not the literal, is what the precedent proves and what is required).
  Evidence: `opencode.jsonc:84-88`.

- **O-2 [RESOLVED — approved by operator, direct conversation with orchestrator,
  this session]: an MCP-protocol library dependency IS acceptable for the new
  approval-launcher MCP's tool-surface layer.** Fork (a)/A2 (the recommended
  path, needed for the agent-facing tool, point 2) wants an MCP-over-stdio layer;
  this is now ratified as acceptable on the **same precedent** as the existing
  `gleipnir-git`/`gleipnir-pm` local MCP brokers, which already import the `mcp`
  SDK (FastMCP) per `opencode.jsonc`'s own header comment ("bounded `mcp>=1.0,<2`
  range… enforcement core stays stdlib-only") and `decisions/runtime-and-deps.md`.
  **The stdlib-only constraint remains scoped to the enforcement core
  specifically** — `src/gleipnir/approval/token.py`, `gate.py`, and
  `verify/marker.py` (which it reuses) — and **the MCP dependency must never
  enter those three files.** Scoping rule restated for `gleipnir-plan`: the
  dependency is **confined to the new MCP tool-surface wrapper module**
  (fork a / A2's `src/gleipnir/approval/mcp.py` or similar) and **never** the
  crypto/gate core (`token.py`/`gate.py`/`marker.py`).

- **O-3(a) [RESOLVED — approved by operator, direct conversation with
  orchestrator, this session]: the key's home is a NEW repo-local `.envrc`.**
  Create a new repo-local `.envrc` as the home for `GLEIPNIR_MARKER_KEY_FILE`
  (or the raw key value — the exact **path-vs-value** choice is left to
  `gleipnir-plan`'s own judgment, consistent with how `GITHUB_TOKEN`/`GITLAB_TOKEN`
  are referenced today). This new `.envrc` is to be **untracked**, and it already
  lands untracked with **no `.gitignore` edit required**: verified this session,
  **`.gitignore:20-21` ALREADY contains `.envrc`** with the provenance comment
  *"Was previously tracked (scaffold commit `8cad21d`); untracked via `git rm
  --cached .envrc`"* — so a newly-authored `.envrc` is already-gitignored. This
  makes it a **no-new-work item on the gitignore side** (existing precedent,
  `.gitignore:20-21`).
  - **Note for `gleipnir-plan` — `[PLAN-STAGE JUDGMENT]`:** authoring `.envrc`
    itself is **in-scope for this feature's plan stage** — it is a **new file,
    and it IS enumerated in the enforcement-path set `E`** (`stage-role-map.md`
    Axis 2(a) lists `.envrc` by name among the repo-root cross-cutting files,
    with the rationale that it sets `OPENCODE_CONFIG_DIR=.gleipnir`, wiring which
    config dir opencode loads). It is the operator's own
    local secrets file, conventionally **hand-authored / operator-applied** (like
    `.gleipnir/agent-identity.env`), **not** something `gleipnir-code` writes. The
    placement question — repo-local `.envrc` vs. following the same existing
    (possibly non-repo-local) mechanism `GITHUB_TOKEN`/`GITLAB_TOKEN` resolve
    from, and the path-vs-value choice above — is **flagged explicitly for
    `gleipnir-plan` to resolve as a `[PLAN-STAGE JUDGMENT]` row.** This subagent
    does **not** resolve it here; the operator ratified *that a new repo-local
    `.envrc` is the chosen home*, and left the mechanical details to the plan.
  - Also (carried forward, unchanged): confirm the **key file itself** is under
    an agent-unreadable path (Pre-Mortem #3), not just the `.envrc` referencing
    it.

- **O-3(b) [DEFERRED — explicitly ratified by operator, direct conversation with
  orchestrator, this session, as a named, honest security gap (operator's own
  words: "defer, flag as a security gap")]: the GLOBAL `.envrc`/`.env*`
  filesystem read+edit deny across EVERY roster agent is NOT built as part of
  this feature.** Verified today (point 7): **no such deny exists** (only
  `gleipnir-code`'s unrelated bash `env*` *command*-deny). This is recorded
  plainly in the repo's honesty-ledger convention (the "cooperative-policy-until-S-2"
  style label — cf. `decisions/tier3-signed-approval.md`'s own honesty ledger for
  the pattern):

  > **isolation-by-convention, not isolation-by-capability, until the global
  > `.envrc`/`.env*` deny is built (deferred, not in this plan's scope) — a
  > roster agent with sufficient bash/read capability could in principle attempt
  > to read the key's source, and only the current deny-by-default bash
  > allowlists (not a dedicated `.envrc` read-deny) stand between an agent and
  > that file today.**

  This is a **durable, visible caveat** — it must travel with whatever this brief
  hands to `gleipnir-plan` and, eventually, the decision record; it is **not** a
  footnote to be lost (see the cross-reference added to the Honesty ledger
  below). It **does NOT block this feature's build**: it is a named,
  deliberately-accepted residual gap, exactly like the E-1/E-2 seams already
  carried elsewhere in this repo.

- **O-4 [RESOLVED — approved by operator, direct conversation with orchestrator,
  this session]: B1.** `request_approval` **returns the `/approve/<hash>` URL as
  a plain string** (and reuses the hook's existing staging); the MCP **does NOT
  auto-open a browser on the host.** Rationale (ratified): auto-opening on the
  host that's running the agent would defeat the design's
  "approve-from-a-separate-authenticated-device" property (point 3;
  `tailscale whois` identity).

- **O-5 [RESOLVED — approved by operator, direct conversation with orchestrator,
  this session]: the tool name is `request_approval`** (as originally proposed;
  operator raised no objection). It matches the existing `/approve` +
  `pending-<hash>` vocabulary.

## Scope Sketch (indicative, pending O-1/O-3)

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| MCP entrypoint (fork a / A2) | NEW thin `src/gleipnir/approval/mcp.py` (or similar): imports `server.py`'s handler, binds `127.0.0.1:8765`, registers the `request_approval` tool. **Reuses, does not fork, the crypto/HTTP surface.** |
| opencode config | `opencode.jsonc` `mcp.<name>` local block: `type:"local"`, `command`, `environment` referencing the key by name (O-1) — **operator-applied; enforcement-path `E`; NO literal secret.** |
| Key isolation prerequisite (point 5 / O-3) | EVERY `.gleipnir/agents/*.md`: add `read`+`edit` deny for `.envrc`/`.env*` (Tier-3 frontmatter; operator/build-mode applied). Confirm key-file path agent-unreadable. |
| `.envrc` (O-3) | NEW repo-root `.envrc` (direnv) exporting `GLEIPNIR_MARKER_KEY_FILE` — cross-cutting/enforcement-adjacent; operator-applied. |
| `request_approval` tool (fork b / B1) | The MCP tool: reuse `tier3-gate.ts`'s staging (`pending-<hash>.json`) + `buildApprovalUrl`/`GLEIPNIR_APPROVAL_BASE_URL`; return the `/approve/<hash>` URL. **No duplication of hook logic.** |
| Supersession edits | `plans/tier3-signed-approval.md` Decision 15; `bin/gleipnir-approval-server` header; `src/gleipnir/approval/server.py` docstring; durable rationale in `decisions/tier3-signed-approval.md` — all operator/build-mode applied. |
| Unchanged (must NOT change) | `src/gleipnir/approval/{token.py,gate.py,__main__.py,identity/**}`, `verify/marker.py`, the token gate/freshness/content-binding crypto. |

## Honesty ledger (mirrors the repo's G-1/G-2/G-3 convention)

- **Buildable now (agent-buildable, testable):** the MCP entrypoint module
  (reusing `server.py`), the `request_approval` tool (reusing the hook's
  staging), tests — **all under `src/`/`tests/`**, IF O-2's dependency question
  is resolved stdlib-compatibly.
- **Operator one-time / Tier-3 acts:** the `opencode.jsonc` MCP block; the
  per-agent `.envrc`/`.env*` denies; authoring `.envrc`; the three supersession
  edits; the durable decision-record update. None agent-doable.
- **Isolation-by-convention-until-closed:** O-1's `{env:VAR}` dependency is now
  **resolved** (this repo's own live local-MCP `environment` precedent,
  `opencode.jsonc:84-88`), so that leg no longer gates. The remaining gap is
  **O-3(b): the global `.envrc`/`.env*` agent read+edit deny does NOT exist and
  is DEFERRED out of this feature's scope** — until it is built, the
  key-isolation property is a convention honoured by the roster + config, **not**
  a substrate-enforced capability. See **O-3(b)** above for the full,
  deliberately-accepted "isolation-by-convention, not -by-capability" gap label
  (operator-ratified deferral, this session); it is labelled exactly like the
  other "authored, not yet closed" guards and the E-1/E-2 seams.
