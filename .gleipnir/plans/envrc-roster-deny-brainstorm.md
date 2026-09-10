# Design Brief: Narrow O-3(b) — a roster-wide `.env*` opencode-permission-layer `read`+`edit` deny so the approval-listener key source moves from convention to an opencode-tool-dispatch capability wall (NOT a file-permission / OS-level control — see the correction in the Selected-Approach section)

_Author: `gleipnir-brainstorm`. Tier-0 artifact; disposable; NOT authoritative.
This grounds and records; it does **not** itself decide the material tradeoffs.
The four forks below are surfaced to the operator for the precept-10 convergence
gate — **not converged by this subagent** (a subagent's `question` cannot reach
the operator). Each fork carries my recommendation as advisory input only._

> **STATUS: CONVERGED — ready to hand to `gleipnir-plan`.** All four forks
> (F1 scope, F2 which-agents, F3 which-layer, F4 posture-consistency) were
> converged by the **operator in direct conversation with the orchestrator this
> session**; the converged answers are recorded verbatim in
> `## Selected Approach — CONVERGED` below, which now supersedes the placeholder.
> F1's convergence carried a **material correction to this brief's own framing**
> (see the correction note in the Selected-Approach section): the frontmatter
> deny is an **opencode-permission-layer** control, NOT a file-permission /
> OS-level control — that correction is folded into F1 and F4 below and into the
> deferred list, and is NOT walked back. The `## Decision Analysis` above is
> retained as the justification input; where its original F1/F4 wording implied
> file-permission-adjacent protection, the corrected framing below governs.

## Problem Statement

The just-merged supersession section of `decisions/tier3-signed-approval.md`
(lines 201–214) names an **honest, deliberately-deferred residual security
gap**, O-3(b), verbatim:

> isolation-by-convention, not isolation-by-capability, until the global
> `.envrc`/`.env*` deny is built (deferred, not in this plan's scope) — a roster
> agent with sufficient bash/read capability could in principle attempt to read
> the key's source, and only the current deny-by-default bash allowlists (not a
> dedicated `.envrc` read-deny) stand between an agent and that file today.

The approval-launcher MCP's whole key-isolation property rests on this claim:
_"`.envrc`/`.env*` is unreadable to the agent's tool surface, so the agent can
supervise-launch the MCP but can never obtain the signing-key path/value the
MCP's process env holds."_ **That property does not exist as a capability
today.** This brief explores how to make it structural.

> **Correction folded in at convergence (governs the wording below):** the layer
> this brief lands is opencode's **permission layer** — it denies the LLM's
> `read`/`edit` **tool** call for `.env*`. It is **NOT** a file-permission
> (chmod/chown) / OS-level control: the `gleipnir-approval` signer MCP and the
> agent's tool processes share **one OS uid** today, so no OS mechanism separates
> them. This deny closes the **opencode-tool-dispatch path** only; genuine
> OS-level isolation is the deferred **signer-uid-separation** follow-on named in
> the Selected-Approach and Honesty-ledger sections. Read the original
> "unreadable to the agent's tool surface" phrasing above as scoped to the
> **opencode tool surface**, not the OS.

**The precise gap (verified this session against disk — not assumed):**

- **`.gitignore:21`** contains exactly `.envrc` (single file), with the
  provenance comment _"Was previously tracked (scaffold commit `8cad21d`);
  untracked via `git rm --cached .envrc`."_ There is **NO broader `.env*` glob**
  in `.gitignore`. `.gleipnir/agent-identity.env` is gitignored *separately*
  (line 17) by exact name — there is no repo convention of a `.env*` wildcard
  ignore. (This matters for F1 scope: the repo does not today treat `.env*` as a
  class in `.gitignore`.)
- **`broker/git/guards.py`** (per the delegation's note) flags `.env`/`.env.*`
  as data/secret artifacts in *commit* content — a git-hook secret-scan concern,
  a different layer than an agent read/edit capability. It establishes that the
  repo *does* recognise `.env*` as a secret class in at least one enforcement
  layer, which is a (weak) consistency argument for F1(b).
- **Per-agent capability ground truth (all 10 agents read in full, not
  sampled):**

  | Agent | `read` | `edit` | `bash` | Can it reach `.envrc` today? |
  |---|---|---|---|---|
  | `gleipnir-code` | `allow` (no `.envrc` exception) | `"*": allow` + denies for `.gleipnir/**`, `.git/**`, `.github/**`, `preflight/**` — **`.envrc` NOT denied** | `"*": deny` + sandbox allowlist + `env*: deny` (a bash *command* deny, not a filesystem glob) | **READ: yes. EDIT: yes** (the only agent that can *write/overwrite* `.envrc`) |
  | `orchestrator` | *unspecified* in block | `deny` | `deny` | read depends on opencode default; edit no |
  | `quality-reviewer` | `allow` | `deny` (+`write: deny`) | `"*": deny` + git read-only | READ: yes. EDIT: no |
  | `gleipnir-plan` | `allow` | `"*": deny` + `plans/**` | `deny` | READ: yes. EDIT: no |
  | `gleipnir-brainstorm` | `allow` | `"*": deny` + `plans/**` | `deny` | READ: yes. EDIT: no |
  | `tier3-writer` | `allow` | `"*": deny` + Tier-3 allowlist | `deny` | READ: yes. EDIT: no |
  | `git-ops` | `"*": allow` + `.git/**: deny` | `deny` (+`write: deny`) | `"*": deny` + git allowlist | READ: yes. EDIT: no |
  | `project-mgr` | `allow` | `deny` (+`write: deny`) | `deny` | READ: yes. EDIT: no |
  | `notify` | `allow` | `deny` (+`write: deny`) | `deny` | READ: yes. EDIT: no |
  | `session-scribe` | `allow` | `"*": deny` + Tier-0 + 1 Tier-2 file | `deny` | READ: yes. EDIT: no |

**The two load-bearing conclusions from that table:**

1. **The residual risk is the `read` tool, not `bash`.** Nine of ten agents are
   `bash: "*": deny` entirely; the two with bash (`gleipnir-code`, `git-ops`)
   have *scoped allowlists* with no `cat`/`env`/`sh`/`source` — no shell path to
   the file's contents. What actually lets an agent obtain `.envrc` today is the
   **`read` tool** (which in this environment reads arbitrary repo files), held
   broadly by 8–9 of 10 agents. So the deny that matters is a **`read` deny**;
   `gleipnir-code`'s existing `env*` bash-command deny is unrelated and
   insufficient (confirmed: it is inside the `bash:` block, blocking the `env`
   *shell command*, not the `.envrc` *file*).
2. **Only `gleipnir-code` can currently *edit* `.envrc`.** Every other agent
   already has `edit: deny` or a `"*": deny`-plus-allowlist that structurally
   excludes `.envrc`. So a *write/overwrite* risk (a blind clobber of `.envrc`,
   arguably worse than a read — see F1(c)) exists today for exactly one agent.

## Constraints (grounded)

- **This is Tier-3 enforcement-bearing → FULL hardened 8-stage pipeline.** The
  work touches `.gleipnir/agents/**` (enforcement-path set `E`, `stage-role-map.md`
  Axis 2(a)) and adds `permission`/`tools` capability lines (Axis 2(b) content
  rule). It is **not** light-track eligible; the `quality` stage must run the
  dual SPEC-CONFORM + BLAST-RADIUS passes plus a per-grant negative-check
  attestation. If F3 chooses the code layer, `P` also touches
  `src/gleipnir/preflight/boundary.py` (an `X`-member: `src/**`) — reinforcing
  full-pipeline routing and adding a test arbiter.
- **No in-framework agent may write Tier-3.** The per-agent frontmatter edits
  are applied by **operator / build-mode** (or the signature-gated `tier3-writer`
  behind a fresh token), exactly like the `gleipnir-approval_*` deny rollout
  they mirror. `gleipnir-code` may write `boundary.py` (it is `src/`, not
  Tier-3) **only if** F3 selects the code layer — but note `gleipnir-code`
  currently has `preflight/**: deny` on edits with named-file allow-list
  exceptions that do **not** include `boundary.py`, so even the code-layer path
  would need an operator/build-mode edit or a new named-file allow (itself a
  Tier-3 frontmatter change — a dependency worth surfacing).
- **The established idiom must be matched, not reinvented.** The precedent to
  mirror is the `gleipnir-approval_*: false` / `gleipnir-git_*: false` /
  `gleipnir-pm_*: false` rows (a **top-level `tools:` boolean** namespace deny)
  and the `permission.edit`/`permission.read` **glob deny** shape (e.g.
  `gleipnir-code`'s `".gleipnir/**": deny`). A filesystem path deny belongs in
  `permission.read` / `permission.edit`, NOT in `tools:` (that's for MCP
  namespaces).
- **Uncaged-default posture (honesty constraint).** Per `AGENTS.md`, the default
  posture is UNCAGED and trusts the single-principal operator; the
  Tier-3-unwritable invariant is opt-in-caged-only. A `read` deny in agent
  frontmatter is enforced by **opencode's permission layer at tool-call time**,
  which operates in *both* modes — so it is NOT a caged-only guarantee (unlike
  `boundary.py`'s OS-perms preflight, which only bites in caged mode). F4
  examines this honestly.

## Approaches Considered

The task decomposes into four genuinely-distinct forks. Each is a real decision
with viable alternatives; none is mechanical. I present the fork options here,
then a `## Decision Analysis` per fork.

### Fork F1 — Scope of the deny pattern

- **F1(a): deny exactly `.envrc`** (matches today's single real file + the
  single `.gitignore` entry).
- **F1(b): deny a broader glob `.env*`** (catches `.env`, `.env.local`,
  `.env.production`, etc. — pre-empts future files; aligns with
  `guards.py`'s `.env`/`.env.*` secret-class treatment).
- **F1(c): the read-vs-edit-vs-both sub-fork.** Independent of (a)/(b): should
  the deny be a `read` deny, an `edit` deny, or **both**? (A blind
  overwrite of `.envrc` by an agent that can't read it is a distinct — arguably
  worse — integrity risk. Only `gleipnir-code` can edit `.envrc` today.)

### Fork F2 — Which agents get the deny

- **F2(a): only the agents that materially can reach it** — i.e. the `read`
  deny on the 8–9 agents with `read: allow`, and the `edit` deny on the one
  agent (`gleipnir-code`) that can edit it.
- **F2(b): all 10 uniformly, for defense-in-depth + consistency** — mirroring
  how `gleipnir-approval_*: false` was applied to all 9 non-holders uniformly
  even where most had no realistic path.

### Fork F3 — Which layer(s) carry the enforcement

- **F3(a): per-agent frontmatter only** (`permission.read`/`permission.edit`
  glob deny in each `.gleipnir/agents/*.md`) — mirrors the
  `gleipnir-approval_*` precedent exactly.
- **F3(b): `boundary.py` `ENFORCEMENT_PATHS` only** (a code-level OS-perms
  target, caged-mode).
- **F3(c): both layers** (frontmatter for uncaged-default reachability + a
  `boundary.py` entry for the caged-mode OS wall).

### Fork F4 — Posture consistency (does a READ deny hold under the uncaged default?)

- Not an independent choice so much as a **framing the operator must ratify**:
  what, honestly, does a frontmatter `.envrc` read-deny *guarantee* under the
  uncaged default, and how should the decision record state it? (It is enforced
  by opencode's permission layer in both modes, but is it a *capability* wall or
  still cooperative until S-2? This determines whether O-3(b) can be marked
  "closed" or only "narrowed.")

---

## Decision Analysis

### F1 — Scope of the deny pattern

**Framework selected:** Reversibility Filter → Pros-Cons-Fixes (F1(a)-vs-(b) is
a bounded binary; F1(c) is a small A/B/both). Both are **two-way doors** — a
glob is a one-line frontmatter change, trivially widened or narrowed later.

**Reversibility:** F1(a)↔F1(b): two-way door (edit one glob string).
F1(c): two-way door (add/remove a `permission.edit` block).

**Pros-Cons-Fixes — F1(a) `.envrc` exact vs F1(b) `.env*` glob:**

| Option | Pros | Cons + Fix |
|---|---|---|
| **F1(a) `.envrc` only** | Matches the *one* real file + the *one* `.gitignore` entry exactly; zero risk of over-denying an unrelated `.env`-named file an agent legitimately needs to read (e.g. a fixture); narrowest-scope = clearest negative-check attestation | Con: a future `.env.local`/`.env` holding a secret would be unprotected → **Fix:** the glob is a one-line widen when such a file is introduced; OR pre-empt via F1(b) |
| **F1(b) `.env*` glob** | Pre-empts the whole `.env*` secret class in one grant; consistent with `guards.py`'s `.env`/`.env.*` commit-secret treatment (a real repo precedent for `.env*`-as-a-class); defense-in-depth against a file that doesn't exist yet | Con: over-denies — could block an agent reading a *non-secret* `.env.example`/`.env.sample` (common convention: example files are meant to be readable) → **Fix:** if a readable `.env.example` is ever needed, carve an exact-path allow after the glob (last-match-wins), mirroring `gleipnir-code`'s named-file allows after its `preflight/**` deny |

**F1(c) read-vs-edit-vs-both (Pros-Cons-Fixes):**

| Option | Verdict |
|---|---|
| **read only** | Closes the *stated* O-3(b) gap (key-source readability) but leaves `gleipnir-code` able to blind-overwrite `.envrc` — a config-integrity risk (an agent could clobber `OPENCODE_CONFIG_DIR`/the key path). Marginal. |
| **edit only** | Nonsensical here — the gap is about *reading* the key source; leaves the read hole wide open. Not viable. |
| **both (read + edit)** | Closes read (the named gap) **and** the write/clobber risk in one grant. `.envrc` is operator-authored-by-convention (per the sibling plan's Decision 18) — **no agent has a legitimate reason to read OR write it**, so a `read`+`edit` deny costs nothing and is strictly safer. |

**Bias check (F1):**
- ⚠️ *Scope Creep (checked, mild):* F1(b)+F1(c)-both is the widest option; I
  guard against "deny everything to avoid deciding." But the widening here is
  *principled* (a named secret class + a real clobber risk), not avoidance —
  and F1(a)/read-only remains a legitimate narrowest choice the operator may
  prefer for attestation clarity. Surfaced, not resolved.
- ⚠️ *Availability (checked):* `guards.py`'s `.env*` treatment is a vivid nearby
  example that could over-pull toward F1(b); noted that it is a *commit-scan*
  layer, not a read-capability layer — a weak, not decisive, analogy.
- (Others: none materially triggered.)

**Recommendation (advisory): F1(b) `.env*` glob + F1(c) both (read AND edit),
with a documented exact-path allow carve-out available if a readable
`.env.example` is ever needed.** Rationale: the file is operator-authored and
agent-irrelevant in both read and write directions; a `.env*` glob pre-empts the
class with a known, cheap carve-out escape; denying edit too closes the
`gleipnir-code` clobber risk at zero cost. **But F1(a) + read-only is the
defensible narrowest alternative** if the operator prefers minimal scope and
maximally-clean attestation — this is a genuine operator call.

### F2 — Which agents get the deny

**Framework selected:** Pros-Cons-Fixes (binary, two-way door).

**Reversibility:** two-way door (add/remove rows per agent).

| Option | Pros | Cons + Fix |
|---|---|---|
| **F2(a) only reachable agents** | Minimal churn; each row is individually justified by a real capability | Con: creates a *non-uniform* roster (some agents have the deny, some don't) — a future agent added with `read: allow` and no deny silently reopens the gap; the asymmetry is a latent audit hazard → **Fix:** a roster-consistency test, but that's new machinery |
| **F2(b) all 10 uniformly** | Matches the shipped `gleipnir-approval_*` precedent exactly (all 9 non-holders got the deny even with no path); uniform roster = trivially auditable ("every agent denies `.env*`"); future-proof (a new agent copied from any existing one inherits the deny); defense-in-depth | Con: a few rows are "redundant" (e.g. `orchestrator` has `edit: deny` already, `bash: deny`, read unspecified) → **Fix:** redundancy here is a *feature* (belt-and-suspenders on the highest-value secret), not waste; the `gleipnir-approval_*` rollout already established this exact pattern is acceptable |

**Bias check (F2):**
- ⚠️ *Status Quo / consistency pull (checked):* F2(b) is attractive partly
  *because* it mirrors the recent `gleipnir-approval_*` shipment — I checked
  this is a merits reason (uniform-roster auditability + future-proofing), not
  mere pattern-matching. The `gleipnir-approval_*` uniformity was itself chosen
  for auditability, so the analogy is sound, not bandwagon.
- (Others: none materially triggered.)

**Recommendation (advisory): F2(b) all 10 uniformly.** The uniform-roster
auditability and future-proofing (a new agent inherits the deny) outweigh the
cosmetic redundancy on the 2–3 agents that already can't reach it, and it
matches the just-shipped precedent the operator already ratified. The
`orchestrator`'s unspecified `read` is itself a reason to be explicit
everywhere.

### F3 — Which layer(s) carry the enforcement

**Framework selected:** Second-Order Thinking → Pre-Mortem (this is the
architectural fork with the longest-lived consequences and a real
false-assurance failure mode). This is the **most material fork** — it
determines whether the control is uncaged-reachable, caged-only, or both, and
whether it touches code (adding a test arbiter and `src/` blast radius).

**Reversibility:** F3(a) frontmatter-only ↔ F3(c) both: **near two-way** (adding
a `boundary.py` entry later is additive). F3(b) code-only is a **poor** choice
for a different reason (below), so the live question is F3(a) vs F3(c).

**The decisive structural fact (verified in `boundary.py`):**
`ENFORCEMENT_PATHS` entries are all resolved as `config_root / ep.relative`
where `config_root` is the **`.gleipnir/` directory** (OPENCODE_CONFIG_DIR).
Every current entry (`agents`, `decisions`, `keys`, `stage-role-map.md`,
`sandbox`, `AGENTS.md`, …) lives *under* `.gleipnir/`. **`.envrc` lives at the
repo root, OUTSIDE `.gleipnir/`.** So adding `.envrc` to `ENFORCEMENT_PATHS` is
**not** a clean one-tuple-row addition — it requires either a repo-root-relative
escape from `config_root` (breaking the "everything is relative to
`config_root`" invariant the module is built on) or a structural change to how
the preflight resolves targets. That is a real design cost, not a copy-paste.

**Second-order analysis:**

| Layer | First-order | Second-order (near) | Second-order (far) |
|---|---|---|---|
| **F3(a) frontmatter only** | opencode denies `read`/`edit` of `.env*` per-agent at tool-call time, in BOTH caged and uncaged modes | The uncaged-default gains a real capability wall immediately (the common operating mode) | Under caged mode the wall is *also* present, but it is enforced by opencode config (agent-adjacent), not the OS — so a compromised-opencode scenario isn't covered; that's the S-2 job, consistent with every other guard |
| **F3(b) `boundary.py` only** | An OS-perms `RO`/`RO_AND_UNREADABLE` target — but **only checked in caged-mode preflight** | Uncaged default (the common mode) gets **NO** protection — the gap stays open exactly where it's most often exercised | Requires breaking the `config_root`-relative invariant; and `.envrc` at repo-root isn't under the `.gleipnir/` RO mount story — architecturally awkward |
| **F3(c) both** | Frontmatter wall in both modes + an OS wall in caged mode | Best coverage; the two layers are the same belt-and-suspenders as `keys/**` (frontmatter-adjacent + OS `RO_AND_UNREADABLE`) | Carries the `boundary.py` `config_root` structural cost + a code change (test arbiter, `src/` blast radius, and a `gleipnir-code` edit grant since `boundary.py` is under `preflight/**: deny`) |

**Pre-Mortem (assume the chosen layer failed to close O-3(b)):**

| # | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **F3(b) chosen; uncaged sessions (the default, the common case) never run the preflight → gap stays fully open in normal use** | H (if F3(b)) | H | Do NOT choose F3(b) alone. Frontmatter is the layer that bites in the default posture |
| 2 | **F3(a) chosen; operator believes it's an OS-level guarantee** when it's an opencode-config guarantee (agent-adjacent, defeated if opencode itself is compromised) | M | M | Honesty-ledger label per F4: "capability-enforced at the opencode permission layer in both modes; hardens to an OS wall under S-2" — narrows O-3(b), doesn't claim S-2-grade closure |
| 3 | **F3(c) chosen; the `boundary.py` `config_root` escape introduces a path-resolution bug** that makes an unrelated enforcement path mis-probe → a false CLOSED elsewhere | L–M | H | If F3(c), the `boundary.py` change needs its own tests + the module's existing fail-closed discipline; treat repo-root `.envrc` as a *separate* probe target, not a hacked `config_root`-relative entry. This is real added complexity — a reason to prefer F3(a) now, F3(c) later |
| 4 | **`gleipnir-code`'s `preflight/** : deny` blocks the very `boundary.py` edit F3(b)/(c) needs** → the code change can't be made by the bounded coder without a *new* Tier-3 frontmatter allow (scope creep into the roster the deny is trying to lock down) | M (if F3(b)/(c)) | M | Named dependency: F3(b)/(c) requires either operator/build-mode authoring of `boundary.py` or a new named-file allow — surface this to the operator as a cost of the code layer |

**Top risks: #1 (F3(b) leaves the default open) and #4 (code-layer needs a new
edit grant).** Both argue against a code-only or code-first approach.

**Bias check (F3):**
- ⚠️ *IKEA / "use the nice machinery we built" (checked):* `boundary.py` is
  elegant and it's tempting to route this through it because it exists. But the
  verified `config_root`-relative fact + the caged-only reach make it the
  *wrong primary* layer for a repo-root file that must be protected in the
  uncaged default. I flag this so the operator isn't over-sold on the code
  layer.
- ⚠️ *Confirmation (guard against):* the frontmatter precedent (`gleipnir-approval_*`)
  is fresh and attractive; I verified it's the *right* layer on merits (it's the
  only layer enforced in the default posture), not just the familiar one.
- (Others: none materially triggered.)

**Recommendation (advisory): F3(a) frontmatter now; F3(c)'s `boundary.py` half
deferred to the S-2 caged-mode hardening as a named follow-up.** The frontmatter
deny is the only layer that protects the **uncaged default** (the common
operating mode), it mirrors the shipped precedent, and it avoids the
`config_root`-invariant break + the `preflight/**: deny` grant-expansion that
the code layer drags in. Adding the `boundary.py` OS target later (when `.envrc`
protection is folded into the S-2 mount story) is additive and belongs with the
other caged-mode OS work — **not** blended into this frontmatter change. This
keeps the change clean and the attestation tight.

### F4 — Posture consistency (what does the read-deny honestly guarantee?)

**Framework selected:** Pros-Cons-Fixes on the *framing*, not a build choice —
this is the honesty-ledger wording the decision record must carry.

**Analysis.** A frontmatter `permission.read` deny is enforced by opencode's
permission layer **at tool-call time, in both caged and uncaged modes** — unlike
`boundary.py`'s OS preflight (caged-only). So F3(a) *does* give the uncaged
default a real capability wall: an agent's `read` tool call for `.envrc` is
refused by opencode before it executes. **What it does NOT give:** protection if
opencode itself (the enforcer) is compromised, or against a non-opencode process
— that residual is the S-2 OS-mount's job, exactly as for every other guard
(`keys/**` is `RO_AND_UNREADABLE` at the OS layer *in addition to* being
agent-adjacent-denied). So:

- **Honest claim (recommended ledger wording):** O-3(b) moves from
  "isolation-by-convention" to **"isolation-by-capability at the opencode
  permission layer, in both postures"** — a genuine narrowing/closure of the
  *stated* gap (the gap was specifically "no dedicated `.envrc` read-deny, only
  bash allowlists"; a dedicated read-deny now exists). The *further* S-2 OS-mount
  hardening (making `.envrc` unreadable even to a compromised opencode) remains
  an open seam, tracked alongside the existing `keys/**`/S-2 work — the same
  "authored, not yet closed" shape as every other guard.
- **Do NOT overclaim** that this makes the key source unreadable under a
  compromised-opencode or compromised-host threat model — that's S-2, and
  claiming it here would repeat the exact over-assertion the honesty ledgers
  exist to prevent.

**Bias check (F4):**
- ⚠️ *Dunning-Kruger on opencode's permission internals (checked):* I assert the
  `read` deny is enforced in both modes based on the permission-model docs and
  the fact that `gleipnir-approval_*`/`.gleipnir/** ` denies are relied on today
  without a caged gate. If opencode's `permission.read` semantics differ from
  this understanding (e.g. read denies are advisory for some tool), the F4
  framing must be corrected — flag as a **verify-at-plan-or-spec-review** item,
  not an assumed fact.

**Recommendation (advisory):** Record O-3(b) as **narrowed to
capability-enforced at the opencode permission layer (both postures)**, with the
OS-mount hardening explicitly listed as the remaining seam — NOT as fully closed
in the S-2 sense. Verify the both-modes enforcement claim at plan/spec-review.

---

## Selected Approach — CONVERGED

**Converged by:** the operator, in direct conversation with the orchestrator,
this session. Recorded here faithfully by `gleipnir-brainstorm` from the choices
the orchestrator handed back — **not** a retroactive re-presentation of this
subagent's own advisory recommendation. Where the operator's convergence
corrected this brief's framing, the correction (not the original framing)
governs.

### Material correction folded into F1 and F4 (the category-error fix)

This brief's original F1 proposed a `.env*` `read`+`edit` deny and implicitly
framed it as **file-permission-adjacent** protection. The operator identified a
**category error** in that framing, which is corrected here and is **not walked
back**:

> **An agent-frontmatter `permission.read`/`edit` deny is NOT a file-permission
> (chmod/chown) control.** Real OS file permissions can only separate two
> processes if they run under **different uids**. Today, the `gleipnir-approval`
> MCP subprocess (the signer — it reads `GLEIPNIR_MARKER_KEY_FILE` via
> `load_key()`) and every roster agent's tool-invocation processes
> (`read`/`bash`/etc.) run under the **same OS user/uid** — there is no
> dedicated signer uid and no dedicated agent uid (that is the still-unbuilt S-2
> dedicated-uid work). So `chmod 600` on `.envrc` or the key file does **not**
> distinguish "the signer" from "the agent's `read` tool" — they are the
> **identical OS principal**.
>
> A frontmatter deny is instead an **opencode-application-level gate**: it
> governs what opencode's own `read`/`edit` **tool** will serve to the LLM when
> the LLM asks for the file via that specific tool call. It has real, non-zero
> value — it closes the **casual/accidental path through opencode's own
> tool-dispatch layer** — but it does **NOT** give the operator exclusive
> OS-level control of the file, and does **NOT** protect against anything that
> bypasses opencode's permission layer entirely: a future `bash`/`exec`
> capability, a compromised MCP, or any OS-level access path.
>
> Genuine OS-level secret isolation would require the **signer to run under a
> distinct uid from the agent's tool-invocation processes** — a real, larger,
> not-yet-scoped piece of work (dedicated service account + `chown` + a
> uid-switched MCP launch, e.g. `sudo -u signer …`), the same shape as this
> framework's S-2 dedicated-agent-uid machinery, just **inverted** (protecting
> the signer *from* the agent's uid, rather than restricting the agent's uid
> away from enforcement paths). That work is named in the deferred list below;
> it is explicitly **not** folded into this bounded frontmatter change.

### F1 — Scope of the deny pattern → **`.env*` glob; deny BOTH `read` and `edit`**

**Converged choice (operator, direct conversation with orchestrator, this
session):** use the `.env*` glob (not just `.envrc`), and deny **both** `read`
and `edit`.

**Explicitly re-labeled per the correction above — this is an
opencode-permission-layer control, NOT a file-permission / OS-level control:**

- **Real value:** it closes the **casual/accidental path through opencode's own
  tool dispatch** — an agent's `read`/`edit` tool call for a `.env*` file is
  refused by opencode's permission layer before it executes.
- **Zero value against anything that bypasses that layer:** a future
  `bash`/`exec` capability, a compromised MCP, or any OS-level access path — 
  **because nothing at the OS layer distinguishes "signer" from "agent" today**
  (same uid, no dedicated signer/agent accounts).

This supersedes the Decision-Analysis F1 wording wherever that wording implied
the deny is file-permission-adjacent or confers OS-level exclusivity.

### F2 — Which agents get the deny → **all 10 roster agents, uniformly**

**Converged choice (operator, direct conversation with orchestrator, this
session):** apply the deny to **all 10 roster agents, uniformly** — matching the
shipped `gleipnir-approval_*` uniform-rollout precedent, giving a trivially
auditable roster ("every agent denies `.env*`") and future-proofing (a new agent
copied from any existing one inherits the deny). This matches this subagent's
advisory F2(b).

### F3 — Which layer carries the enforcement → **frontmatter now; OS-layer deferred; signer-uid separation named as a DISTINCT follow-on**

**Converged choice (operator, direct conversation with orchestrator, this
session):**

- **Frontmatter now** — the cooperative / opencode-permission-layer control
  (per-agent `permission.read`/`permission.edit` `.env*` deny), applied this
  change.
- The `boundary.py` / OS-layer work **stays deferred as before** (it does not
  cleanly hold a repo-root file under the `config_root`-relative invariant, and
  it bites only in caged mode — see Decision-Analysis F3).
- **New, per the correction:** **genuine uid separation for the signer** is named
  as a **distinct, larger, not-yet-scoped follow-on**, explicitly **not** folded
  into this bounded frontmatter change (see the deferred list below).

### F4 — Posture / honesty framing → **"honestly," sharpened per the correction**

**Converged choice (operator, direct conversation with orchestrator, this
session):** record this honestly — and, sharpened per the correction, record it
as narrowing O-3(b) to **"opencode-permission-layer enforced"** — explicitly
**NOT** "file-permission enforced" and explicitly **NOT** "operator has exclusive
OS control of the key."

The O-3(b)-successor gap label in the eventual `decisions/` update **must state
this distinction plainly, not gloss it**: the residual is that the signer and
the agent's tool processes share one uid, so no OS-level control separates them;
the frontmatter deny closes only the opencode-tool-dispatch path. Genuine
OS-level isolation is the deferred signer-uid-separation follow-on, not something
this change delivers.

This supersedes the Decision-Analysis F4 wording wherever that wording could be
read as claiming a file-permission-grade or OS-exclusive guarantee. The
"capability-enforced at the opencode permission layer" claim remains — but it is
an **opencode-application-layer** capability, not an OS/file-permission
capability, and the ledger must say so.

### Converged bundle (one line)

**F1: `.env*` glob, `read`+`edit` deny (opencode-permission-layer, NOT
file-permission) · F2: all 10 agents uniformly · F3: frontmatter now, OS-layer
deferred, signer-uid separation named as a distinct follow-on · F4: record as
"opencode-permission-layer enforced," explicitly not file-permission / not
OS-exclusive.**

## Open Questions (for `gleipnir-plan`, after convergence)

_F1–F4 are CONVERGED (see `## Selected Approach — CONVERGED`): the glob is
`.env*`, the deny is `read`+`edit`, all 10 agents uniformly, frontmatter layer
only. These are settled inputs, not open. The items below are the remaining
**mechanical** questions for planning._

- **Exact-path carve-out:** whether an exact-path `.env.example`/`.env.sample`
  **allow** is pre-authored after the `.env*` deny (last-match-wins), in case an
  agent legitimately needs to read an example file. Decide at plan time; the glob
  itself is fixed (`.env*`).
- **Placement within each frontmatter `permission` block:** a `read` glob deny
  goes in `permission.read` (which for most agents is currently the scalar
  `read: allow` — it must become a map `read: { "*": allow, ".env*": deny }`,
  matching `git-ops`'s existing `read:` *map* shape). The `edit` deny slots into
  each agent's existing `edit` map. Confirm the scalar→map rewrite is done per
  the established idiom and that last-match-wins ordering is correct.
- **`orchestrator`'s unspecified `read`:** add an explicit `read:` map (required
  under F2's all-10-uniformly convergence, since its read is currently
  default-allow).
- **`gleipnir-code`'s `edit` map** already denies `.gleipnir/**` etc.; the
  `.env*` edit-deny is a new entry — confirm it does not collide with the
  named-file allows below it (it won't; `.env*` is repo-root, the allows are
  under `preflight/`/`plugins/`).
- **Verify (plan/spec-review):** that a `permission.read`/`permission.edit` glob
  deny is enforced by opencode's permission layer in the uncaged default (F4's
  load-bearing claim). **Framing check (per the correction):** confirm the
  decision-record wording labels this an **opencode-permission-layer** control,
  NOT a file-permission / OS-level one — the reviewer must reject any ledger
  wording that claims OS-exclusive control of the key or file-permission-grade
  isolation, since the signer and agent share one uid today.

## Scope Sketch (indicative, pending convergence)

_Reflects the converged bundle: `.env*` glob, `read`+`edit`, all 10 agents,
frontmatter layer only. The `boundary.py` OS-perms row is **not** in scope
(F3 converged to frontmatter-now, OS-layer deferred)._

| Area | Files/Modules Likely Affected | Writer |
|---|---|---|
| Per-agent `read`+`edit` deny (all 10, uniform) | All 10 `.gleipnir/agents/*.md` — add the `.env*` deny to `permission.read` (rewriting scalar `read: allow` → map where needed) **and** to `permission.edit` | **operator / build-mode** (Tier-3) |
| Honesty-ledger update | `.gleipnir/decisions/tier3-signed-approval.md` O-3(b) section: mark narrowed per F4 wording — **"opencode-permission-layer enforced," explicitly NOT file-permission / NOT OS-exclusive** (state the shared-uid residual plainly, do not gloss); name the signer-uid-separation follow-on as the remaining OS-level seam | **operator / build-mode** (Tier-3) |
| Negative-check attestation | Produced at `quality` by `quality-reviewer` — one row per grant, asserting the intended narrow scope and the over-broad form ruled out | `quality-reviewer` |
| _(Deferred — NOT this change)_ genuine signer-uid separation | dedicated service account + `chown` + uid-switched MCP launch (`sudo -u signer …`) — tracked follow-on, unscoped; see Honesty ledger | _future / operator-scoped_ |

## Honesty ledger (mirrors the repo convention)

- **Buildable now (bounded):** the per-agent frontmatter `read`+`edit` deny rows
  (converged F3: frontmatter now) — but Tier-3, so operator/build-mode-applied,
  not agent-written. No `src/` change under the converged frontmatter-only
  choice.
- **What it is (corrected framing — governs over the Decision-Analysis wording):**
  the frontmatter `.env*` deny is an **opencode-permission-layer** control — it
  governs what opencode's own `read`/`edit` tool serves to the LLM. It is **NOT**
  a file-permission (chmod/chown) control and does **NOT** give the operator
  exclusive OS-level control of the key or file. **Why:** the `gleipnir-approval`
  signer MCP and every agent's tool-invocation process run under the **same
  OS uid** today, so no OS-level mechanism distinguishes "signer" from "agent."
- **Capability-vs-convention (sharpened per the correction):** O-3(b) moves from
  "isolation-by-convention" to **"isolation-by-capability at the opencode
  permission layer"** — a real narrowing of the *stated* gap (a dedicated
  `.env*` read/edit deny now exists where before only bash allowlists stood).
  **Explicitly NOT** "file-permission enforced" and **explicitly NOT** "operator
  has exclusive OS control of the key." The deny closes the casual/accidental
  opencode-tool-dispatch path; it does nothing against anything that bypasses
  opencode's permission layer (a future `bash`/`exec` capability, a compromised
  MCP, any OS-level access path). The O-3(b)-successor label in the `decisions/`
  update must state this shared-uid distinction plainly, **not gloss it**.
- **Deferred (named) — genuine signer-uid separation (the real OS-level fix):**
  making the key genuinely OS-isolated requires the **signer to run under a
  distinct uid from the agent's tool-invocation processes** — a dedicated service
  account + `chown` of the key/`.envrc` to it + a **uid-switched MCP launch**
  (e.g. `sudo -u signer …`). This is the **same shape as the S-2
  dedicated-agent-uid machinery, inverted** (it protects the signer *from* the
  agent's uid, rather than restricting the agent's uid away from enforcement
  paths). It is a **real, larger, not-yet-scoped follow-on**, tracked but
  **explicitly out of scope** for this bounded frontmatter change, and is
  **distinct** from it. Until it lands, no OS-level control separates signer from
  agent — the frontmatter deny is the opencode-layer control only.
- **Deferred (named) — `boundary.py` OS target (the earlier F3(c) half):**
  additive, belongs with S-2 caged-mode work; also out of this change's scope.
  Note it is a *caged-mode OS-perms preflight* target and is separate from the
  signer-uid-separation follow-on above (which is a runtime uid-launch concern,
  not a preflight check).
