# Plan: Tier-3 approval listener as an opencode-spawned local MCP + agent-facing `request_approval` tool (supersedes Decision 15's "no auto-start")

> **Stage:** `plan` (gleipnir-plan). **Input:** the CONVERGED brief
> `.gleipnir/plans/tier3-mcp-approval-launcher-brainstorm.md` (555 lines, read
> in full; `> STATUS: CONVERGED`). The core shape (brief points 1–6) and **all
> five open items (O-1..O-5)** are operator-ratified (O-1 empirically via this
> repo's own `{env:VAR}` local-MCP precedent; O-2/O-4/O-5 approved; O-3 split
> into O-3(a) RESOLVED and O-3(b) DEFERRED as a named, honest, deliberately-
> accepted residual security gap). This plan does **not** re-decide any of
> those. It plans the *bounded* implementation those decisions define, and
> resolves only the `[PLAN-STAGE JUDGMENT]` details the brief explicitly left to
> the plan stage (module/file layout, exact MCP tool-surface library choice
> consistent with O-2, exact `.envrc` content shape / path-vs-value per O-3(a),
> whether `bin/gleipnir-approval-server` is retired or kept, new module name(s),
> test file names, and the process-concurrency shape for one process running two
> blocking loops).
>
> **Stale-phrase note (from the brief, expected — not open questions):** the
> brief's Scope Sketch header still reads "(indicative, pending O-1/O-3)" and its
> Honesty ledger still reads "IF O-2's dependency question is resolved". Both are
> **cosmetic stale artifacts of the convergence process** — superseded by the
> Open Items section, where O-1/O-2/O-3 are all resolved. They are NOT open
> questions; this plan treats O-1/O-2/O-3(a) as resolved and O-3(b) as a named
> deferral, per the Open Items section that supersedes those two header phrases.
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0); this file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it. **No in-framework agent
> (including `gleipnir-code`) may write any Tier-3 path, ever** — so the Tier-3
> artifacts this feature needs (the `opencode.jsonc` MCP-block addition — in the
> enforcement-path set `E`; and the per-agent frontmatter deny-list additions
> under `.gleipnir/agents/*.md`) are **named here but applied by the operator /
> build-mode**, exactly like every prior Tier-3 rollout in this project (the
> three supersession edits and the `tier3-writer.md`/`tier3-gate.ts` rollout of
> the sibling `tier3-signed-approval.md` plan). This plan does not write them.
>
> **This is Tier-3-enforcement-bearing** per `stage-role-map.md` Axis 1/2: `P`
> touches `opencode.jsonc` (explicitly enumerated in enforcement-path set `E`,
> Axis 2(a)) and `.gleipnir/agents/*.md` `tools:` blocks (Axis 2(b) content rule
> — a `tools:` capability line). It therefore runs the **full hardened 8-stage
> pipeline** (NOT the light prose/config track), and the `quality` stage MUST run
> the **dual SPEC-CONFORM + BLAST-RADIUS passes plus a negative-check
> attestation** for every enforcement-path touch (see Execution Workflow).

---

## Decisions (index)

Every decision this plan fixes, in order encountered. Rows 1–9 → the CONVERGED
brief (operator-converged; **recorded, NOT re-decided** — cited to the brief).
Rows 10–18 → `[PLAN-STAGE JUDGMENT]` details made during Architect/Trace,
flagged for spec-review per the delegation. Row 19 → a bounded edge-case
handling decision **made at spec-review** (port-conflict handling, edge case 5;
recorded here, not re-decided). Row 20 → a **plan-completeness addition found
during the `code` stage by `gleipnir-code`** (the `runtime-and-deps.md`
carve-out + paired `test_broker_stdlib_only.py` widening the artifact/Trace
sections originally missed — not a new material tradeoff, since Decision 8 / O-2
already approved the `mcp` dependency for `approval/mcp_server.py`; the same
incomplete-supersession-scope shape as round-1's Defect 1, for a different file
pair). Full reasoning for each row is in the sections below.

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Launch mechanism | **Opencode spawns the listener as a global `type:"local"` MCP** at launch; replaces the manual `bin/` start step | The manual-only operator shim as the *primary* path (Decision 15's "no auto-start") | Removes the manual step the operator wants gone; launch is process-supervision only, confers no minting ability. **Brief point 1 + Supersession clause — operator-converged.** |
| 2 | Agent-facing tool | **The MCP exposes `request_approval`** — stages pending content + returns the `/approve/<hash>` review URL | No agent-facing tool (launch-only) | Explicit converged requirement so an agent hitting a gated Tier-3 write can stage + surface the review URL for out-of-band approval. **Brief point 2 — operator-converged.** |
| 3 | Trust locus correction | **Key-readability, not process-launch, is the security locus.** Launch by opencode/MCP is fine **iff** the signing key is never reachable by the agent tool surface + per-request `tailscale whois` identity is preserved | Decision 15's "manual launch = integrity" framing (miscalibrated to process-launch) | *"starting the process is NOT the same as using the service to sign shit."* The forgeable-activation concern is real but relocated to key-unreachability. **Brief point 3 + Supersession clause — operator-converged.** |
| 4 | Key source (interim) | **Env-var reference** resolved from the operator's launching shell (via `.envrc`/direnv), passed into the MCP `environment:` block as `{env:VAR}` — **never a literal key/path in `opencode.jsonc`** | Inlining the literal key/path into `opencode.jsonc` (a tracked, agent-readable, `E`-path file); Vault now (explicitly deferred) | `{env:VAR}` for a local-MCP `environment:` block is proven by this repo's own `gleipnir-pm` precedent (`opencode.jsonc:86-88`). Vault is the named future hardening. **Brief point 4 / O-1 — operator-converged.** |
| 5 | Isolation prerequisite (named gap) | **A global `.envrc`/`.env*` read+edit deny across every roster agent is REQUIRED for capability-isolation but is NOT built here** — deferred as a named, honest, deliberately-accepted residual security gap (O-3(b)) | Building the global deny in this plan; or silently glossing the gap | Verified: no such deny exists today. Deferral is operator-ratified and carried as a durable, visible caveat, not a footnote. **Brief point 5 / O-3(b) — operator-converged (deferral explicit).** |
| 6 | MCP tool shape | **B1** — `request_approval` returns the `/approve/<hash>` URL string (reusing the hook's existing staging); MCP does **not** auto-open a browser on the host | B2 — auto-open a browser on the MCP/agent host | Auto-opening on the agent host undercuts the "approve-from-a-separate-authenticated-device" property (point 3; `tailscale whois`). **Brief O-4 (fork b) — operator-converged.** |
| 7 | Tool name | **`request_approval`** | Any other name | Matches the existing `/approve` + `pending-<hash>` vocabulary. **Brief O-5 — operator-converged.** |
| 8 | MCP-library dependency acceptable | **Yes**, on the same precedent as `gleipnir-git`/`gleipnir-pm` (they import FastMCP / the `mcp` SDK from `.venv`); the dependency is confined to the new MCP tool-surface wrapper and **never** enters `token.py`/`gate.py`/`marker.py` | A stdlib-only MCP-over-stdio hand-roll; or letting `mcp` into the crypto core | The enforcement core stays stdlib-only (`decisions/runtime-and-deps.md`); the MCP wrapper is a supervision/UX layer explicitly outside that boundary. **Brief O-2 (fork a / A2) — operator-converged.** |
| 9 | Crypto core untouched | `server.py`, `token.py`, `gate.py`, `identity/**`, `verify/marker.py`, the content-binding mechanism, and `tier3-gate.ts`'s write-block logic are **NOT modified** | Re-implementing/forking any of that logic into the MCP | The MCP wraps (imports) the untouched core (Fork a / A2). **Brief Constraints + O-2 — operator-converged.** |
| 10 | **`[PLAN-STAGE JUDGMENT]`** MCP wrapper module name + home | New module **`src/gleipnir/approval/mcp_server.py`** (sibling to the existing `approval/server.py`) | `approval/mcp.py` (the brief's placeholder "or similar"); a new top-level package | Matches the established broker convention `broker/{git,pm}/mcp_server.py` **exactly** — every existing local-MCP entrypoint in this repo is named `mcp_server.py`, run as `python -m gleipnir.<pkg>.mcp_server`. Consistency beats the brief's tentative `mcp.py`. Flagged for spec-review. |
| 11 | **`[PLAN-STAGE JUDGMENT]`** MCP library | **`FastMCP` (the `mcp` SDK already in `.venv`)**, run `mcp.run(transport="stdio")` — the identical shape as `broker/git/mcp_server.py:524` | A different/new MCP library; a bespoke stdio protocol implementation | O-2 ratified the dependency on the broker precedent; reusing the *same* library the two existing brokers use adds zero new dependency surface (`mcp>=1.0,<2` is already the bounded range per `opencode.jsonc:57`). Flagged for spec-review. |
| 12 | **`[PLAN-STAGE JUDGMENT]`** Two-blocking-loops concurrency shape | The MCP process runs `mcp.run(transport="stdio")` on the **main thread**; the HTTP listener (`server.run_server`, which blocks on `serve_forever()`) runs on a **daemon background thread** started once at MCP module startup | Running the listener on the main thread (would block the stdio MCP loop, breaking the tool surface); a second OS subprocess (needless, loses the single-process supervision the brief wants) | Both `mcp.run(...)` and `serve_forever()` block; one process needs both. A `threading.Thread(target=run_server, daemon=True)` started at startup is the standard, bounded shape. Daemon so the listener dies with the MCP process (no orphan). This is an implementation detail of the converged "one MCP process launches the listener," **not a new material tradeoff**. Flagged for spec-review. |
| 13 | **`[PLAN-STAGE JUDGMENT]`** Listener-import boundary (no forked logic) | `mcp_server.py` **imports** `run_server`/`register_default_resolvers` from `approval/server.py` and calls them on the background thread; it re-implements **no** HTTP/crypto/identity logic. A structural source-scan test asserts `mcp_server.py` **defines no HTTP handler and no `hmac`/`hashlib` mint/validate call** | Copying `run_server`'s socket/handler wiring into the MCP module; importing `token.py`/`gate.py`/`marker.py` into the wrapper | Fork a / A2's "thin, import-only wrapper" (O-2). Mirrors how `broker/git/mcp_server.py` imports `guards`/`content_handlers` rather than reimplementing them. The structural test makes "wraps, does not fork" falsifiable. Flagged for spec-review. |
| 14 | **`[PLAN-STAGE JUDGMENT]`** `request_approval` tool internals (reuse, don't duplicate) | The tool **reuses the TypeScript hook's staging + URL machinery's Python-side equivalents already living in `server.py`**: it stages via the same `pending-<hash>.json` envelope shape `stagePendingContent` writes (`.gleipnir/var/tmp/`, Decision 17 dir) and returns the `/approve/<hash>` URL built from `GLEIPNIR_APPROVAL_BASE_URL` (same env var + same relative-hint fallback as `buildApprovalUrl`, `tier3-gate.ts:435-445`) | Re-implementing a *different* staging format or a *different* URL scheme in Python; duplicating `buildApprovalUrl`'s fallback logic verbatim in a new place | Brief O-4 + Constraint "must not duplicate the hook's logic." The envelope shape and URL contract are already fixed by `server.py`/`tier3-gate.ts`; the tool must produce the **same** artifacts the hook produces on REFUSE, so `server.py`'s `GET /approve/<hash>` renders them identically. Flagged for spec-review. |
| 15 | **`[PLAN-STAGE JUDGMENT]`** `bin/gleipnir-approval-server`: retire or keep | **KEEP it as a documented manual fallback**, but demote it from "the start path" to "a fallback for when opencode is not the launcher (debugging, CI, a headless operator run)". Its header comment is updated (a supersession edit, below) to say so | Retiring/deleting the shim | The shim and the MCP both exec the *same* `run_server` entrypoint, so the shim costs nothing to keep and is genuinely useful when opencode is not running (e.g. an operator wants to accept an approval outside a session, or a test harness). Retiring it would remove a zero-cost, orthogonal capability and force the listener to exist *only* inside an opencode session — a strictly-narrower posture with no security benefit (the key-isolation property is identical either way). Two-way door; keeping is the reversible, lower-regret choice. Flagged for spec-review. |
| 16 | **`[PLAN-STAGE JUDGMENT]`** MCP tool namespace + name | opencode names local-MCP tools `<server>_<tool>`, so registering the server as **`gleipnir-approval`** with tool `request_approval` yields the tool id **`gleipnir-approval_request_approval`** and namespace glob **`gleipnir-approval_*`** | A server name that collides with `gleipnir-git`/`gleipnir-pm`; a bare `request_approval` with no server prefix | Follows the exact `<server>_<tool>` convention documented in `opencode.jsonc:69-70`. The namespace glob is what the per-agent deny rows target (Decision 17). Flagged for spec-review. |
| 17 | **`[PLAN-STAGE JUDGMENT]`** Per-agent deny-list scope | Add a **single** `"gleipnir-approval_*": false` row to the `tools:` block of **every roster agent EXCEPT the sole holder** — mirroring the existing `"gleipnir-git_*": false`/`"gleipnir-pm_*": false` rows. **Holder RESOLVED (operator, direct conversation with orchestrator, this session): Option (ii) — only `tier3-writer` holds `gleipnir-approval_*`.** `tier3-writer` holds it *by absence of a deny* (the global-enable + per-agent deny-list pattern, exactly like `git-ops` holds `gleipnir-git_*`); every OTHER roster agent gets an explicit `: false` deny row. See the RESOLVED "material tradeoff" section below for the full enumerated agent list. | Silently granting the tool to all agents (default-enabled, no deny); silently granting it to a chosen agent without operator sign-off; **Options (i) no holder and (iii) a broader stage-role set — both rejected by the operator this session in favour of (ii)** | The MCP tool is enabled globally in `opencode.jsonc` (like the brokers), so *absence of a deny = the agent holds it*. That default-on posture means the deny-list must be authored deliberately. The "who holds it" decision was material (a Tier-3 capability grant) and was decided by the operator directly, not by this plan: `tier3-writer` is the role that hits gated Tier-3 writes, so it is the natural and narrowest single holder. Flagged for spec-review. |
| 18 | **`[PLAN-STAGE JUDGMENT]`** `.envrc` content shape (path-vs-value) + authorship placement | **(a) Content:** `.envrc` exports **`OPENCODE_CONFIG_DIR=.gleipnir`** (existing, per `opencode.jsonc:15`) **plus** `export GLEIPNIR_MARKER_KEY_FILE=<absolute path to the key file>` — i.e. the **path form, not the raw key value**. **(b) Authorship:** `.envrc` is **operator-authored by convention** (hand-applied like `.gleipnir/agent-identity.env`), NOT written by `gleipnir-code`, even though it is capability-writable by `gleipnir-code` (it is outside `.gleipnir/**` and outside `E`). | Storing the raw HMAC key value in `.envrc` (secret-in-a-file, worse blast radius than a path); having `gleipnir-code` author `.envrc` directly | **Path-vs-value:** the key *file* already exists (`.gleipnir/keys/marker.key`, `chmod 600`, agent-unreadable via `boundary.py`'s `RO_AND_UNREADABLE`); exporting the *path* keeps the secret in one already-protected place and matches `marker.py`'s `KEY_ENV_VAR = GLEIPNIR_MARKER_KEY_FILE` (a path env var, not a value). **Authorship:** see the dedicated subsection below — this is a live judgment call the brief left open; I resolve it as operator-authored-by-convention and justify it. Flagged for spec-review. |
| 19 | **Port-conflict handling on the daemon listener thread** (edge case 5) | **Log-and-continue on the daemon thread** — a `HTTPServer` bind failure on `127.0.0.1:8765` is logged and the thread exits, but the MCP process (and its stdio `request_approval` tool surface) keeps running | **Fail the whole MCP process** on a listener bind failure | A bind failure killing the whole MCP process would also kill the `request_approval` stdio tool surface, destroying the auto-launch benefit for a purely transient/already-benign conflict: a second listener already running is the operator's own doing (e.g. a manual `bin/gleipnir-approval-server`), not a security regression. The key-isolation property is unaffected either way. **Decided at spec-review** (records the plan's own stated recommendation in edge case 5); recorded here in the enforced artifact shape, not floating in prose. |
| 20 | **`mcp`-import carve-out must be widened for `approval/mcp_server.py`** (found during the `code` stage by `gleipnir-code`, NOT pre-existing) | **Widen the `runtime-and-deps.md` "Boundary drawn sharply" MCP-SDK carve-out** from "Only `src/gleipnir/broker/**`" to also name the single file `src/gleipnir/approval/mcp_server.py` (Tier-3, operator/build-mode) **and** add the paired single-named-file exception to `tests/test_broker_stdlib_only.py` (ordinary `tests/**` code, sequenced AFTER the record amendment) | Leaving the carve-out at broker-only (leaves `mcp_server.py`'s `import mcp` failing `test_no_core_package_imports_mcp`); widening to a blanket "any subpackage" or an `approval/**` glob (over-broad — would stop scanning `token.py`/`gate.py` for `mcp` leaks) | **Not a new material tradeoff:** Decision 8 / O-2 already approved the `mcp` dependency for `approval/mcp_server.py` on the broker precedent; this row only records the *plan-completeness* artifacts that consequence requires. `gleipnir-code` correctly built `mcp_server.py` importing `mcp`, which trips the EXISTING `test_broker_stdlib_only.py::TestEnforcementCoreNeverImportsMcp::test_no_core_package_imports_mcp` (scans every non-`broker` core package). The record must be the narrowest **file-named** exception (not a glob/subpackage widening), and the test must mirror it and move only after it. Same incomplete-supersession-scope shape as round-1's Defect 1, different file pair. |

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`goals/manifest.md`):** "Plan format" (`plan-format.md`) and
  "Methodology (ATLAS/GOTCHA ahead of planning)" apply; followed here
  (Decisions-index / Architect / Trace / Link / Assemble / Stress-test /
  Execution Workflow / Design Principles). No pipeline-sequencing goal authored
  (G-5 rule respected).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or Tier-3 writes are produced here — only this plan file.
- **Layer placement (GOTCHA layers):** this is primarily an **Orchestration /
  Tools-layer** change (opencode supervises a new MCP process; a new agent-facing
  tool appears) with a real **Args-layer** boundary (the MCP wrapper's import-only
  seam against the untouched `server.py`; the key reference must be a `{env:VAR}`
  *arg*, never a literal). It touches the **G-1/S-2 boundary** posture (the
  key-isolation property is cooperative-until-closed, exactly like the sibling
  plan's gate) and **G-6** (it launches the process that mints Tier-3 approval
  tokens). It does **not** amend the G-5 pipeline ordering, and it does **not**
  touch the crypto core.
- **Gaps / factual findings named (mechanical, not material):**
  1. **`src/gleipnir/approval/` has no `mcp_server.py` today** (verified:
     `glob *.py src/gleipnir/approval` returns `__init__.py`, `__main__.py`,
     `gate.py`, `server.py`, `token.py`, `identity/*` — no `mcp_server.py`). This
     plan builds the **first** MCP wrapper for this subsystem.
  2. **The MCP entrypoint convention in this repo is `mcp_server.py`, not
     `mcp.py`** (verified: `broker/git/mcp_server.py`, `broker/pm/mcp_server.py`;
     each ends `mcp.run(transport="stdio")`, `broker/git/mcp_server.py:524`).
     Decision 10 follows that convention over the brief's tentative `mcp.py`.
  3. **`mcp.run(transport="stdio")` blocks the main thread** (verified,
     `broker/git/mcp_server.py:524`), and `server.run_server` blocks on
     `serve_forever()` (`server.py:394`). One process running both requires the
     listener on a background thread (Decision 12) — a bounded concurrency detail,
     surfaced not smuggled.
  4. **`{env:VAR}` for a local-MCP `environment:` block is proven in this repo**
     (verified: `opencode.jsonc:86-88`, `gleipnir-pm`'s `"GITLAB_TOKEN":
     "{env:GITLAB_TOKEN}"`). O-1's empirical resolution holds against real config.
  5. **`.envrc` is already gitignored** (verified: `.gitignore:21`, with the
     `git rm --cached` provenance comment O-3(a) cites). No `.gitignore` edit is
     needed; a newly-authored `.envrc` lands untracked automatically.
  6. **The per-agent deny-list shape is `"<namespace>_*": false` inside a
     frontmatter `tools:` block** (verified: `"gleipnir-git_*": false` /
     `"gleipnir-pm_*": false` present in `gleipnir-code.md:63-64`,
     `orchestrator.md:47-48`, and ~7 more). The new `gleipnir-approval_*` deny
     follows this exact shape (Decision 17).

**New material tradeoff found?** **One was surfaced and has since been RESOLVED
by the operator directly** (Option (ii): only `tier3-writer` holds
`gleipnir-approval_*` — see the RESOLVED section below). Everything else is a
bounded implementation detail flagged as a `[PLAN-STAGE JUDGMENT]` row. The
converged shape (points 1–6) and O-1..O-5 are recorded, not re-decided. **No
open material tradeoff now remains** (the one factual correction re `.envrc` ∈
`E`, below, is a classification fix, not a tradeoff).

---

## 1. Architect

**Problem (one sentence):** The already-merged `tier3-signed-approval` subsystem
requires the operator to **manually** start (`bin/gleipnir-approval-server`) and
Ctrl-C stop the out-of-band approval listener (Decision 15's "no auto-start");
this plan removes that manual step by having **opencode itself spawn the listener
as a global local MCP** at launch **and** exposes an agent-facing
`request_approval` tool that stages pending Tier-3 content and returns the
`tailscale serve`-fronted `/approve/<hash>` review URL — all **without ever
making the HMAC signing key reachable by the agent's tool surface**, so the
launch confers process-supervision only and never the ability to mint a token.

**Users:**
- the **operator**, who no longer starts the listener by hand (opencode does it)
  and still approves out-of-band on a separate authenticated tailnet device;
- the **agent that hits a gated Tier-3 write**, which calls `request_approval` to
  stage the pending content and get back the review URL to surface to the
  operator (instead of hand-crafting the staging/URL);
- the **maintainer** who later hardens the key source (env var → Vault, deferred)
  without touching the crypto core or the MCP tool surface.

**Measurable success criteria:**

1. A new **`src/gleipnir/approval/mcp_server.py`** exists that, when run as
   `python -m gleipnir.approval.mcp_server`, (a) starts the existing
   `approval/server.py` listener on a background daemon thread (binding
   `127.0.0.1:8765`, unchanged) and (b) serves the MCP protocol over stdio,
   exposing exactly one tool, `request_approval`.
2. The MCP-started listener is **provably the SAME `server.py` core, unmodified**:
   `mcp_server.py` **imports** `run_server`/`register_default_resolvers` from
   `approval/server.py` and calls them; it re-implements no HTTP handler, no
   identity resolution, and no mint/validate. A **structural source-scan test**
   asserts `mcp_server.py` contains no HTTP request-handler class and makes no
   `hmac`/`hashlib` mint/validate call of its own (it wraps, it does not fork).
   `git diff` shows `server.py`, `token.py`, `gate.py`, `identity/**`,
   `verify/marker.py`, and `tier3-gate.ts` are **byte-for-byte unchanged**.
3. `request_approval` **returns the `/approve/<hash>` URL as a plain string**
   (O-4/B1) and **reuses the existing staging contract**: it writes the same
   `pending-<hash>.json` envelope shape (`{content, filePath, tool, staged_at}`)
   to the same `.gleipnir/var/tmp/` directory `stagePendingContent` uses, and
   builds the URL from `GLEIPNIR_APPROVAL_BASE_URL` with the same relative-hint
   fallback as `buildApprovalUrl` when the env var is unset. It does **not**
   auto-open a browser on the host.
4. The **key never appears as a literal** in `opencode.jsonc`: the MCP block's
   `environment:` passes the key **by reference** (`"GLEIPNIR_MARKER_KEY_FILE":
   "{env:GLEIPNIR_MARKER_KEY_FILE}"`), resolved from the operator's launching
   shell (via `.envrc`/direnv). A grep of `opencode.jsonc` finds **no** raw key
   bytes and **no** absolute key-file path — only the `{env:...}` reference.
5. **No new Python runtime dependency enters the crypto core:** the `mcp` SDK
   (FastMCP) is imported **only** in `mcp_server.py`; `token.py`, `gate.py`, and
   `verify/marker.py` remain `mcp`-free (a source-scan / import check confirms
   it). The `mcp` dependency is already present for the two existing brokers
   (`mcp>=1.0,<2`, `opencode.jsonc:57`) — no new range is added.
6. The **listener dies with the MCP process** (daemon thread) — no orphaned
   `127.0.0.1:8765` listener survives an opencode shutdown.
7. The **O-3(b) security-gap label is carried into this plan's text** (below,
   verbatim) **and** flagged as something the eventual decision-record update
   must state — not just this plan.
8. Every enforcement-path touch (the `opencode.jsonc` MCP block; any per-agent
   `gleipnir-approval_*` deny row) is applied by **operator/build-mode only** and
   passes the hardened-path dual-pass + negative-check attestation at `quality`.

**Constraints (from the brief — FIXED, not re-litigated):**

- **The crypto core is already correct, tested, and MUST NOT change**
  (`server.py`, `token.py`, `gate.py`, `__main__.py`, `identity/**`,
  `verify/marker.py`, the content-binding mechanism, `tier3-gate.ts`'s
  write-block logic, the `IdentityResolver` seam). This is a
  *process-supervision + agent-tool-surface* change, not a crypto change.
- **stdlib-only enforcement core** (`decisions/runtime-and-deps.md`): the `mcp`
  dependency is confined to `mcp_server.py` and must never enter
  `token.py`/`gate.py`/`marker.py` (O-2's scoping rule).
- **Tailnet-only transport** via `tailscale serve` fronting a `127.0.0.1`
  listener — unchanged; the `tailscale serve` config itself is an operator OS
  act, not code this plan builds.
- **`opencode.jsonc` is Tier-3 enforcement wiring** (enforcement-path set `E`,
  Axis 2(a)): tracked, agent-readable, operator-applied. **No literal secret may
  ever be written into it.**

**The O-3(b) security-gap label — carried forward VERBATIM from the brief
(brief O-3(b), the blockquote):**

> **isolation-by-convention, not isolation-by-capability, until the global
> `.envrc`/`.env*` deny is built (deferred, not in this plan's scope) — a
> roster agent with sufficient bash/read capability could in principle attempt
> to read the key's source, and only the current deny-by-default bash
> allowlists (not a dedicated `.envrc` read-deny) stand between an agent and
> that file today.**

**Instruction to whoever updates the durable decision record (do not let this
gap evaporate):** when `.gleipnir/decisions/tier3-signed-approval.md` receives
its eventual superseding update for this MCP-launcher change (see the
"Decision-record update" subsection under Execution Workflow), that update
**MUST carry the O-3(b) gap label above forward verbatim** into the decision
record's honesty ledger, in the same "cooperative-policy-until-closed" /
"authored, not yet closed" style the record already uses for its
S-2/S-3/Route-β/`tailscale serve` deferrals. This is a named, deliberately-
accepted residual gap (operator-ratified, this session), exactly like the
E-1/E-2 seams carried elsewhere in this repo — it must travel from brief → plan
→ decision record, not be softened or dropped at any hop.

**Explicitly NOT in scope:** the global `.envrc`/`.env*` read+edit deny across
every roster agent (O-3(b), deferred); Vault/1Password key source (O-4's future
hardening, deferred); any change to the crypto core; the `tailscale serve`
configuration itself (operator OS act); Route β (OIDC) resolver; Tier-2/G-4c
generalization.

### `.envrc` authorship — the live judgment call (Decision 18(b), resolved, not dodged)

The delegation asks me to decide **plainly** whether `gleipnir-code` may write
`.envrc` directly (it is a repo-root file outside `.gleipnir/**` and outside the
explicit enumeration of enforcement-path set `E`, so it is **not**
capability-Tier-3), or whether it should be operator-authored by convention
despite not being capability-Tier-3.

**Resolution: `.envrc` is OPERATOR-AUTHORED BY CONVENTION, not written by
`gleipnir-code`.** Reasoning:

1. **Capability fact (stated plainly):** `.envrc` is NOT in enforcement-path set
   `E` (which enumerates `opencode.jsonc`, `.gitignore`, `.envrc`… — wait: check
   this). **Correction after re-reading `stage-role-map.md` Axis 2(a):** `.envrc`
   **IS** explicitly enumerated in `E` ("`.envrc` sets
   `OPENCODE_CONFIG_DIR=.gleipnir`, wiring which config dir opencode loads at
   all"). So a plan whose `P` touches `.envrc` is **enforcement-bearing by the
   Axis 2(a) path rule**, and `.envrc` is an operator/build-mode artifact by the
   same token as `opencode.jsonc`. This **overrides** the brief's O-3(a) note
   that called `.envrc` "not Tier-3, not in E" — the brief was mistaken on that
   specific point; `stage-role-map.md`'s own text enumerates `.envrc` in `E`.
   (I flag this as a correction of the brief, not a re-decision of the converged
   shape: the *shape* — a new repo-local `.envrc` exporting the key path — is
   unchanged; only the *authorship classification* is corrected to match
   `stage-role-map.md`.)
2. **Therefore:** `.envrc` is applied by **operator/build-mode**, exactly like
   `opencode.jsonc` and `.gleipnir/agent-identity.env`. `gleipnir-code` does
   **not** write it. This is both the capability-correct answer (it is in `E`)
   and the convention-correct answer (it is a host-local secrets-adjacent file,
   like `agent-identity.env`).
3. **Consequence for routing:** because `P` includes `.envrc` ∈ `E`, this plan is
   **enforcement-bearing on that ground alone**, independent of the
   `opencode.jsonc` and agent-frontmatter touches — reinforcing the full-hardened
   pipeline routing.

**This is a genuine correction I am surfacing, not silently absorbing:** the
brief's O-3(a) sub-note asserted `.envrc` is "not Tier-3, not in the
enforcement-path set `E`." Re-reading `stage-role-map.md` Axis 2(a), `.envrc` is
**explicitly enumerated in `E`**. I resolve the authorship question in line with
`stage-role-map.md` (operator-authored, enforcement-bearing) and flag the
brief's contrary note as an error for the operator's awareness (see "NEW
material tradeoff surfaced" — this is adjacent to it but is a factual correction,
not itself a tradeoff).

---

## 2. Trace

### Chosen module layout (Decision 10/12/13 — `[PLAN-STAGE JUDGMENT]`, flagged for spec-review)

```
src/gleipnir/approval/
  __init__.py                  # UNCHANGED (public surface already exports the core)
  token.py                     # UNCHANGED — crypto core, mcp-free (asserted by import scan)
  gate.py                      # UNCHANGED — crypto core, mcp-free
  __main__.py                  # UNCHANGED — the gate CLI
  identity/**                  # UNCHANGED — resolver seam
  server.py                    # UNCHANGED — the stdlib http.server listener; run_server is imported, not edited
  mcp_server.py                # NEW — the MCP tool-surface wrapper (Decisions 10/11/12/13/14):
                               #   * imports run_server + register_default_resolvers from .server (no forked logic)
                               #   * starts the listener on a daemon background thread at startup (Decision 12)
                               #   * FastMCP("gleipnir-approval"); one @mcp.tool() request_approval (Decision 14)
                               #   * ends: mcp.run(transport="stdio")  (mirrors broker/git/mcp_server.py:524)
                               #   * imports mcp SDK — the ONLY file in approval/ that does (Decision 8)
                               #   * CLOSED IMPORT ALLOW-LIST (the "wraps, never mints" boundary — T-11):
                               #       mcp_server.py may import ONLY these symbols from the core:
                               #         - run_server, register_default_resolvers            (from .server — launch)
                               #         - compute_change_hash, staged_path_for, default_token_dir (staging/URL reuse, Decision 14 DRY)
                               #       It MUST NOT import or call any MINTING/KEY symbol —
                               #       specifically NOT capture_approval / mint_approval (server.py:227) nor
                               #       load_key (marker/server). capture_approval mints internally + needs a
                               #       remote_ip for resolve_identity's `tailscale whois` (server.py:224-225);
                               #       calling it from inside the MCP process (e.g. remote_ip="127.0.0.1") would
                               #       resolve identity against the local host and mint a valid token with ZERO
                               #       human review — a complete bypass of the separate-device approval property
                               #       (Decision 3 / Supersession clause). Enforced structurally by T-11.

bin/gleipnir-approval-server   # KEPT as a manual fallback (Decision 15); header comment updated (supersession edit)

tests/test_approval_mcp_server.py   # NEW (broker profile — needs the `mcp` SDK, like test_broker_*):
                                    #   * request_approval stages the pending-<hash>.json envelope + returns the URL string
                                    #   * URL uses GLEIPNIR_APPROVAL_BASE_URL when set; relative-hint fallback when unset
                                    #   * the listener thread is started daemon at startup (injectable/observable)
                                    #   * STRUCTURAL source-scan: mcp_server.py defines no HTTP handler class and
                                    #     makes no hmac/hashlib mint/validate call (wraps, does not fork — Decision 13)
                                    #   * IMPORT scan: token.py/gate.py/verify.marker do NOT import mcp (Decision 8/criterion 5)
                                    #   * REVERSE-IMPORT scan (T-11): mcp_server.py contains NO reference to
                                    #     capture_approval/mint_approval/load_key — imports ONLY the closed allow-list
                                    #     (run_server, register_default_resolvers, compute_change_hash, staged_path_for,
                                    #     default_token_dir); the "wraps, never mints" boundary (Decision 3/13)
```

**Operator/build-mode Tier-3 artifacts (named here, NOT written by any agent):**

```
opencode.jsonc                 # ADD an mcp."gleipnir-approval" local block (enforcement-path E, Axis 2(a)):
                               #   type:"local"; command [".venv/bin/python","-m","gleipnir.approval.mcp_server"];
                               #   environment { "PYTHONPATH":"src",
                               #                 "GLEIPNIR_MARKER_KEY_FILE":"{env:GLEIPNIR_MARKER_KEY_FILE}",
                               #                 "GLEIPNIR_APPROVAL_BASE_URL":"{env:GLEIPNIR_APPROVAL_BASE_URL}" };
                               #   enabled:true.  NO literal key/path — reference form ONLY (Decision 4, O-1).
.gleipnir/agents/*.md          # ADD "gleipnir-approval_*": false to the tools: block of every roster agent
                               #   EXCEPT tier3-writer (Decision 17). Holder RESOLVED (operator, direct, this session):
                               #   only tier3-writer holds it (by absence of a deny); all 9 others get the deny row.
.envrc                         # NEW (operator-authored; in E per Axis 2(a); already gitignored, .gitignore:21):
                               #   export OPENCODE_CONFIG_DIR=.gleipnir
                               #   export GLEIPNIR_MARKER_KEY_FILE=<abs path to .gleipnir/keys/marker.key>   (path, not value — Decision 18)
                               #   export GLEIPNIR_APPROVAL_BASE_URL=<tailscale-serve base URL>              (optional; enables full URL)
```

**Supersession edits (operator/build-mode applied; named, not performed here):**

```
bin/gleipnir-approval-server   # header comment: demote from "the start path" to "a manual fallback"; narrow the
                               #   forgeable-activation warning to "the agent must never read the key or mint a token"
                               #   (NOT "never auto-started") — per the brief's Supersession clause item 2. Executable
                               #   (bin/**, Axis-1 disqualifier) but the EDIT is comment-only; still operator-applied
                               #   because the file's launch semantics are enforcement-adjacent.
src/gleipnir/approval/server.py  # TWO independent "no auto-start" docstring claims corrected (both DOCSTRING-ONLY,
                                 #   NO logic change): (1) the module-level docstring (:12-15) "No auto-start (Decision 15)...
                                 #   not launched by any agent"; AND (2) the run_server() docstring (:383-385) "No auto-start:
                                 #   nothing calls this except the operator's explicit shim invocation." Both corrected to
                                 #   "opencode/an MCP config MAY launch it as a supervised subprocess, provided the key
                                 #   stays unreachable to the agent tool surface" (Supersession clause item 3). server.py's
                                 #   code stays byte-identical in behaviour — the diff is docstring lines at :12-15 and :383-385 only.
.gleipnir/plans/tier3-signed-approval.md  # Decision 15 annotated as SUPERSEDED (plan is Tier-0; annotation only).
.gleipnir/decisions/tier3-signed-approval.md  # DURABLE superseding update (see Execution Workflow) — MUST carry the
                               #   O-3(b) gap label forward verbatim.
```

> **Note on the two "docstring/comment-only" edits to `server.py` and
> `bin/gleipnir-approval-server`:** these touch files the brief's Constraints
> mark "MUST NOT change" for *logic*. The edits are **comment/docstring-only, no
> behaviour change** — they update the now-stale "no auto-start" framing the
> Supersession clause explicitly corrects. This is consistent with "the crypto
> core MUST NOT change": no crypto/HTTP/identity **logic** changes. Spec-review
> must confirm these edits are provably comment/docstring-only (a `git diff`
> showing only comment/docstring lines changed).

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Source-of-truth role |
|---|---|---|---|---|
| **MCP wrapper** | NEW `src/gleipnir/approval/mcp_server.py` | source tree (under `src/`) | bounded `gleipnir-code` | FastMCP server `gleipnir-approval`; imports `run_server`/`register_default_resolvers` from `server.py` (no forked logic); starts listener on a daemon thread; exposes `request_approval`; ends `mcp.run(transport="stdio")`. The ONLY `approval/` file importing `mcp`. |
| MCP wrapper tests | NEW `tests/test_approval_mcp_server.py` | source tree | bounded `gleipnir-code` | Arbiter for: tool stages+returns URL (B1); URL env-var + fallback; daemon-thread startup; **structural scan (no forked HTTP/crypto)**; **import scan (crypto core mcp-free)**. Runs under the **broker** profile (needs `mcp`). |
| Listener core | `src/gleipnir/approval/server.py` | source tree | — (**docstring-only** edit at BOTH `:12-15` (module docstring) and `:383-385` (`run_server` docstring), operator/build-mode, supersession) | Reused by import; `run_server` unchanged in behaviour. Both "no auto-start" docstring claims corrected; docstring-only diff at `:12-15` and `:383-385`. |
| Crypto core | `src/gleipnir/approval/{token.py,gate.py,__main__.py,identity/**}`, `verify/marker.py` | source tree | — (**NOT edited**) | Untouched; asserted mcp-free by import scan. |
| Write-block hook | `.gleipnir/plugins/tier3-gate.ts` | Tier-3 POLICY (`E`) | — (**NOT edited**) | `buildApprovalUrl`/`stagePendingContent` reused *by contract* (the MCP tool produces the same envelope+URL); the hook file itself is unchanged. |
| **opencode MCP block** | `opencode.jsonc` (ADD `mcp."gleipnir-approval"`) | **Tier-3 POLICY** (enforcement-path `E`, Axis 2(a)) | **operator / build-mode ONLY** | Local-MCP entry; `{env:VAR}` reference ONLY, no literal secret. Mirrors `gleipnir-pm` (`:81-90`). |
| **Per-agent deny rows** | `.gleipnir/agents/*.md` (ADD `"gleipnir-approval_*": false`) | **Tier-3 POLICY** (Axis 2(b) content rule) | **operator / build-mode ONLY** | Single deny row on every agent EXCEPT `tier3-writer` (the sole holder, by absence of a deny); mirrors the existing `gleipnir-git_*`/`gleipnir-pm_*` rows. Holder RESOLVED (operator, direct, this session): Option (ii). See RESOLVED section for the 9-file list. |
| **`.envrc`** | NEW repo-root `.envrc` | **Tier-3 POLICY** (in `E`, Axis 2(a)) — see Architect subsection | **operator / build-mode ONLY** | Exports `OPENCODE_CONFIG_DIR`, `GLEIPNIR_MARKER_KEY_FILE` (path form), optional `GLEIPNIR_APPROVAL_BASE_URL`. Already gitignored (`.gitignore:21`). |
| Manual-fallback shim | `bin/gleipnir-approval-server` | source tree (executable) | — (**comment-only** edit, operator/build-mode) | Kept as fallback (Decision 15); header demoted + warning narrowed. |
| **Durable decision record** | `.gleipnir/decisions/tier3-signed-approval.md` (superseding update) | **Tier-3 POLICY** | **operator / build-mode ONLY** | Records the launch supersession; **MUST carry the O-3(b) gap label forward verbatim**. |
| **Runtime/deps carve-out record** | `.gleipnir/decisions/runtime-and-deps.md` (amend "Boundary drawn sharply") | **Tier-3 POLICY** | **operator / build-mode ONLY** | Widen the MCP-SDK carve-out from "Only `src/gleipnir/broker/**`" to also name the single file `src/gleipnir/approval/mcp_server.py` (Decision 20). A narrow, file-named exception — NOT a blanket "any subpackage may import mcp". Found during the `code` stage by `gleipnir-code`. |

**Critical Trace consequence:** the *code* portion is bounded `gleipnir-code`
territory — one new module (`mcp_server.py`), one new test file, the two
comment/docstring-only supersession edits, and the single-line widening of the
existing `tests/test_broker_stdlib_only.py` carve-out (Assemble step 2b; in
`tests/**`, ordinary `gleipnir-code` territory, sequenced AFTER the Tier-3
`runtime-and-deps.md` amendment). The **five Tier-3 / enforcement-path actions**
(operator/build-mode only) are: the `opencode.jsonc` MCP-block addition, the
per-agent `gleipnir-approval_*` deny rows, the `.envrc` authoring, the
`tier3-signed-approval.md` durable decision-record update, and the
`runtime-and-deps.md` "Boundary drawn sharply" carve-out amendment (Decision 20,
found during the `code` stage by `gleipnir-code`). No in-framework agent writes
any of those five.

### Integrations map

- **opencode → MCP process:** opencode reads the new `mcp."gleipnir-approval"`
  block at launch, spawns `.venv/bin/python -m gleipnir.approval.mcp_server` with
  the `environment:` (including the `{env:GLEIPNIR_MARKER_KEY_FILE}`-resolved
  path), and speaks MCP-over-stdio to it. (Same wiring as `gleipnir-git`/`-pm`.)
- **MCP process (main thread) → agents:** exposes `request_approval` over stdio;
  agents that hold `gleipnir-approval_*` may call it.
- **MCP process (daemon thread) → listener:** at startup, calls
  `register_default_resolvers()` then `run_server(...)` on a background daemon
  thread; the listener binds `127.0.0.1:8765`, `tailscale serve` fronts it
  (operator OS act).
- **`request_approval` → staging + URL:** stages the `pending-<hash>.json`
  envelope in `.gleipnir/var/tmp/` (same shape/dir as `stagePendingContent`) and
  returns the `/approve/<hash>` URL (same `GLEIPNIR_APPROVAL_BASE_URL` contract +
  fallback as `buildApprovalUrl`). The operator opens it on a separate
  authenticated device; `server.py`'s `GET /approve/<hash>` renders the review
  page; `POST` mints the token — all unchanged.
- **Key flow:** `.envrc`/direnv exports `GLEIPNIR_MARKER_KEY_FILE` (path) into the
  operator's shell → opencode inherits it → `{env:...}` resolves it into the MCP
  subprocess env → `server.load_key()` reads the file. The **agent tool surface
  never sees the key file's contents** (the file is `chmod 600` + agent-unreadable
  via `boundary.py`), and never sees the literal path in tracked config (it is a
  `{env:...}` reference). **Caveat: this is isolation-by-convention until the
  O-3(b) deny is built** (see the gap label above).

### Edge cases

1. **`GLEIPNIR_MARKER_KEY_FILE` unset at opencode launch** → `{env:...}` resolves
   empty → `server.load_key()` fail-closes (`KeyUnavailable` propagates,
   `server.py:388`), so the MCP process refuses to start the listener rather than
   serving without a usable key. `request_approval` staging still works (staging
   is key-independent), but no token can be minted — correct fail-closed posture.
2. **`GLEIPNIR_APPROVAL_BASE_URL` unset** → `request_approval` returns the
   relative-hint fallback string (same as `buildApprovalUrl:441-444`); approval
   readiness never depends on the env var (parity with the hook).
3. **MCP process crash / opencode shutdown** → the listener runs on a **daemon**
   thread, so it dies with the process; no orphaned `127.0.0.1:8765` listener
   (Decision 12).
4. **`request_approval` called with no gated write pending** → it stages whatever
   content it is handed and returns a URL; the token is only minted on operator
   POST. No security consequence (staging is Tier-0 input-to-review, never
   authority — the HMAC token is authority, per `tier3-gate.ts:166-169`).
5. **Port `8765` already in use** (a manual `bin/gleipnir-approval-server` already
   running) → `HTTPServer` bind raises on the daemon thread; the MCP tool surface
   still comes up (stdio is independent). **Resolved as Decision 19
   (log-and-continue on the daemon thread)** — the thread logs the bind failure
   and exits, but the MCP process and its `request_approval` tool surface keep
   running (the tool surface is still useful; a second listener is the operator's
   own doing, not a security regression). See Decision 19 in the index for the
   full rationale.
6. **An agent that should not mint tries to call `request_approval`** → if the
   agent's frontmatter has `"gleipnir-approval_*": false`, the tool is not on its
   surface (deny-list, Decision 17). Per the operator's resolution (Option (ii)),
   only `tier3-writer` lacks that deny (holds the tool); all 9 other roster
   agents carry it and cannot call `request_approval`.

---

## 3. Link (validated before building)

- **`{env:VAR}` in a local-MCP `environment:` block works** — verified against
  this repo's live `gleipnir-pm` config (`opencode.jsonc:86-88`), which has
  authenticated real PR/MR operations this session (O-1's empirical resolution).
- **The `mcp` SDK (FastMCP) is available in `.venv`** and is the established
  local-MCP library here — verified `from mcp.server.fastmcp import FastMCP`
  (`broker/git/mcp_server.py:44`) and `mcp.run(transport="stdio")` (`:524`).
- **`server.run_server` is importable and is exactly what the shim execs** —
  verified `bin/gleipnir-approval-server:30` execs `-m gleipnir.approval.server`,
  whose `run_server` (`server.py:372`) registers resolvers, loads the key
  fail-closed, and `serve_forever()`s.
- **The staging + URL contract is fixed by existing code** — verified
  `stagePendingContent` (`tier3-gate.ts:408-426`), `buildApprovalUrl`
  (`:435-445`), and `server.py`'s `pending-<hash>.json` reader (`load_staged`,
  `:112`) + `GET/POST /approve/<hash>` (`:263-291`).
- **`.envrc` is already gitignored** — verified `.gitignore:21`.
- **The per-agent deny-list shape** — verified `"gleipnir-git_*": false` /
  `"gleipnir-pm_*": false` in `gleipnir-code.md:63-64` and ~8 other agents.
- **The crypto core is untouched today** — verified `glob` shows no
  `mcp_server.py` in `approval/`; the new module is additive.

---

## 4. Assemble (intended build order)

1. **Write `tests/test_approval_mcp_server.py` first** (test-first): assert the
   `request_approval` tool stages the envelope + returns the URL string (B1);
   env-var URL + fallback; daemon-thread startup; the structural source-scan (no
   forked HTTP/crypto); the import scan (crypto core mcp-free). Runs under the
   **broker** sandbox profile (it needs `mcp`, like `test_broker_*`).
2. **Implement `src/gleipnir/approval/mcp_server.py`** to green the tests:
   FastMCP `gleipnir-approval`; daemon-thread `run_server`; one `request_approval`
   tool reusing the staging/URL contract; `mcp.run(transport="stdio")`. **This
   import of the `mcp` SDK is what triggers the two paired carve-out edits below
   (2a-Tier-3 / 2b-code) — the existing
   `tests/test_broker_stdlib_only.py::TestEnforcementCoreNeverImportsMcp::
   test_no_core_package_imports_mcp` scans every `src/gleipnir/` subpackage
   except `broker/` and would fail on `approval/mcp_server.py`'s `import mcp`
   until the carve-out is widened.**
2a. **[operator/build-mode Tier-3 — Decision 20, found during the `code` stage
   by `gleipnir-code`]** Amend `.gleipnir/decisions/runtime-and-deps.md`'s
   "Boundary drawn sharply" section to widen the MCP-SDK carve-out from "Only
   `src/gleipnir/broker/**`" to also name the single file
   `src/gleipnir/approval/mcp_server.py` (a narrow, file-named exception — NOT a
   blanket "any subpackage may import mcp" widening). See the exact replacement
   wording under "Runtime/deps carve-out amendment (Decision 20)" below. Tier-3
   decision-record file; operator/build-mode-applied, **never**
   `gleipnir-code`-written.
2b. **[code — `gleipnir-code`; SEQUENCED AFTER step 2a]** Widen the exception in
   `tests/test_broker_stdlib_only.py` so the single named file
   `src/gleipnir/approval/mcp_server.py` is permitted to import `mcp`, alongside
   the existing `broker/**` carve-out. This file is **NOT** Tier-3 (it is in
   `tests/**`, ordinary `gleipnir-code` territory), but per this plan's own
   sequencing discipline it is widened **only after** step 2a applies the
   `runtime-and-deps.md` amendment the test enforces — the test mirrors the
   decision record, so the record must move first. See the exact required change
   under "Test carve-out widening (step 2b)" below.
3. **Apply the two comment/docstring-only supersession edits** to
   `bin/gleipnir-approval-server` (header demote) and `server.py` — the latter
   corrects **BOTH** "no auto-start" docstring claims: the module-level docstring
   (`:12-15`) AND the `run_server()` docstring (`:383-385`) — operator/build-mode;
   provably comment/docstring-only (diff confined to those docstring lines).
4. **[operator/build-mode Tier-3]** Author `.envrc` (path form, Decision 18);
   confirm `.gleipnir/keys/marker.key` is `chmod 600` + agent-unreadable.
5. **[operator/build-mode Tier-3]** Add the `mcp."gleipnir-approval"` block to
   `opencode.jsonc` (`{env:VAR}` reference ONLY).
6. **[operator/build-mode Tier-3 — HOLDER RESOLVED: Option (ii), operator,
   direct conversation with orchestrator, this session]** The sole holder is
   **`tier3-writer`**, which holds `gleipnir-approval_*` **by absence of a deny**
   (the global-enable + per-agent deny-list pattern — exactly how `git-ops`
   holds `gleipnir-git_*` and `project-mgr` holds `gleipnir-pm_*`); it therefore
   gets **NO** `gleipnir-approval_*` row. Add `"gleipnir-approval_*": false` to
   the `tools:` block of **every OTHER roster agent** — the full enumerated list
   (verified against the current roster, `ls .gleipnir/agents/*.md`, **10 files
   total, 9 non-holders**):
   1. `.gleipnir/agents/session-scribe.md` (already has a `tools:` block, lines 42–43)
   2. `.gleipnir/agents/quality-reviewer.md` (lines 26–27)
   3. `.gleipnir/agents/gleipnir-code.md` (lines 63–64)
   4. `.gleipnir/agents/notify.md` (lines 20–21)
   5. `.gleipnir/agents/gleipnir-plan.md` (lines 24–25)
   6. `.gleipnir/agents/project-mgr.md` (has `tools:` with `"gleipnir-git_*": false` only, line 23 — add the approval deny alongside it)
   7. `.gleipnir/agents/git-ops.md` (has `tools:` with `"gleipnir-pm_*": false` only, line 51 — add the approval deny alongside it)
   8. `.gleipnir/agents/gleipnir-brainstorm.md` (lines 29–30)
   9. `.gleipnir/agents/orchestrator.md` (lines 47–48)

   The **10th file, `.gleipnir/agents/tier3-writer.md` (the holder), is
   deliberately EXCLUDED** — adding a deny there would revoke the very grant the
   operator chose. (Note: `tier3-writer` also carries `"gleipnir-git_*": false`
   and `"gleipnir-pm_*": false`, lines 65–66 — it is a non-holder of the two
   broker namespaces but the holder of the approval namespace; leave those two
   broker denies untouched and add nothing for approval.)
7. **[operator/build-mode Tier-3]** Superseding update to
   `.gleipnir/decisions/tier3-signed-approval.md` — carry the O-3(b) gap label
   forward verbatim; annotate `plans/tier3-signed-approval.md` Decision 15 as
   superseded.
8. **Restart opencode** (L-C33: mid-session MCP/plugin config is not loaded until
   restart) — the MCP + tool go live only after a full restart.

Steps 1, 2, and 2b are `gleipnir-code`; step 2a is an operator/build-mode
Tier-3 act (and MUST precede step 2b); step 3 is comment/docstring-only
operator/build edits; steps 4–7 are operator/build-mode Tier-3 acts; step 8 is
an operator act.

### Runtime/deps carve-out amendment (Decision 20) — exact replacement wording

`.gleipnir/decisions/runtime-and-deps.md`'s "Boundary drawn sharply" section
currently reads (verified against the file):

> **Boundary drawn sharply.** "Enforcement core = stdlib-only" is unchanged. Only
> `src/gleipnir/broker/**` may import the MCP SDK; every future dep still needs its
> own recorded justification. A broker-scoped conformance test
> (`tests/test_broker_stdlib_only.py`) asserts `mcp` never leaks into the core and,
> within `broker/`, is imported only by the `mcp_server.py` modules.

Replace it (operator/build-mode) with the narrow, file-named widening — style
consistent with the existing paragraph:

> **Boundary drawn sharply.** "Enforcement core = stdlib-only" is unchanged. Only
> `src/gleipnir/broker/**` and the single named file
> `src/gleipnir/approval/mcp_server.py` may import the MCP SDK; every future dep
> still needs its own recorded justification. The `approval/mcp_server.py`
> exception is the opencode-spawned approval-listener MCP wrapper
> (`../plans/tier3-mcp-approval-launcher.md`, Decision 8 / O-2 — the same
> broker-precedent carve-out); it is a **single named file**, NOT a blanket
> widening of the whole approval package (`token.py`/`gate.py`/`verify/marker.py`
> stay `mcp`-free). A broker-scoped conformance test
> (`tests/test_broker_stdlib_only.py`) asserts `mcp` never leaks into the core
> except that one named file and, within `broker/`, is imported only by the
> `mcp_server.py` modules.

This is a **narrow, named exception** — the over-broad forms explicitly rejected
are (a) any-subpackage-may-import-mcp, and (b) an `approval/**` glob rather than
the single file `approval/mcp_server.py` (see negative-check attestation row 5).

### Test carve-out widening (step 2b) — exact required change

`tests/test_broker_stdlib_only.py` currently excludes only `broker/` (and
`__pycache__`) from the enforcement-core scan, via `_core_package_dirs()` (lines
61–69) which feeds `TestEnforcementCoreNeverImportsMcp::
test_no_core_package_imports_mcp` (lines 82–91). That test iterates **every**
`.py` file in each non-`broker` core package and asserts `"mcp" not in roots`.
Because `approval/` is a core package (not `broker/`), `approval/mcp_server.py`'s
`import mcp` will make that assertion fail. The verified relevant existing code:

```python
def _core_package_dirs() -> list[Path]:
    """Every immediate subpackage of src/gleipnir/ EXCEPT broker/."""
    dirs = [
        p
        for p in SRC_GLEIPNIR_DIR.iterdir()
        if p.is_dir() and p.name != "broker" and p.name != "__pycache__"
    ]
    ...

class TestEnforcementCoreNeverImportsMcp:
    def test_no_core_package_imports_mcp(self):
        for pkg_dir in _core_package_dirs():
            for py_file in _py_files(pkg_dir):
                roots = _top_level_import_roots(py_file)
                assert "mcp" not in roots, (
                    ...
                )
```

**Required change (minimal, single named exception — NOT a package-level
exclusion):** add a module-level constant naming the one permitted file and
skip exactly it inside the `test_no_core_package_imports_mcp` loop, so the
`approval` package is still fully scanned for every OTHER file. For example:

```python
# The single non-broker file permitted to import the MCP SDK, per the
# .gleipnir/decisions/runtime-and-deps.md "Boundary drawn sharply" carve-out
# (Decision 20 of ../.gleipnir/plans/tier3-mcp-approval-launcher.md). This is
# ONE named file, not an approval/** package exclusion.
APPROVAL_MCP_SERVER = SRC_GLEIPNIR_DIR / "approval" / "mcp_server.py"

class TestEnforcementCoreNeverImportsMcp:
    def test_no_core_package_imports_mcp(self):
        for pkg_dir in _core_package_dirs():
            for py_file in _py_files(pkg_dir):
                if py_file == APPROVAL_MCP_SERVER:
                    continue  # named carve-out (runtime-and-deps.md, Decision 20)
                roots = _top_level_import_roots(py_file)
                assert "mcp" not in roots, (
                    ...
                )
```

`gleipnir-code` MUST implement it as a **single-file** skip (`py_file ==
APPROVAL_MCP_SERVER`), never by adding `"approval"` to the `_core_package_dirs()`
exclusion (which would stop scanning the whole `approval/` package — the
over-broad form). The exact idiom is `gleipnir-code`'s to finalise (a `continue`
skip, a `!=` guard in `_py_files`, or an allow-set membership test) so long as it
is keyed on the single named file, keeps every other `approval/` file scanned,
and is applied only after step 2a. This step's correctness is proven by the
existing broker-profile test suite staying green with the new exception.

---

## 5. Stress-test (acceptance checks)

- **T-1** `python -m gleipnir.approval.mcp_server` starts, binds
  `127.0.0.1:8765` on a background thread, and serves MCP-over-stdio exposing
  exactly one tool `request_approval`. (broker-profile test)
- **T-2** `request_approval` stages a `pending-<hash>.json` envelope matching
  `stagePendingContent`'s shape in `.gleipnir/var/tmp/` and returns the
  `/approve/<hash>` URL string; **no browser is opened** (B1). (test)
- **T-3** URL uses `GLEIPNIR_APPROVAL_BASE_URL` when set; returns the
  relative-hint fallback when unset (parity with `buildApprovalUrl`). (test)
- **T-4 (structural)** `mcp_server.py` defines **no** HTTP request-handler class
  and makes **no** `hmac`/`hashlib` mint/validate call — it wraps `server.py`,
  it does not fork it. (source-scan test)
- **T-5 (import)** `token.py`, `gate.py`, and `verify/marker.py` do **not**
  import `mcp` — the crypto core stays stdlib-only. (import-scan test)
- **T-6 (byte-identity)** `git diff` shows `server.py` changed **only** in its
  **two** docstrings — the module-level docstring (`:12-15`) AND the
  `run_server()` docstring (`:383-385`), both "no auto-start" claims — with **no
  logic lines** changed, and `token.py`/`gate.py`/`__main__.py`/
  `identity/**`/`verify/marker.py`/`tier3-gate.ts` are **byte-for-byte
  unchanged**.
- **T-7 (no literal secret)** `grep` of `opencode.jsonc` finds no raw key bytes
  and no absolute key-file path — only the `{env:GLEIPNIR_MARKER_KEY_FILE}`
  reference. (hardened-path negative-check, below)
- **T-8 (daemon lifecycle)** the listener thread is a daemon thread (dies with
  the process; no orphan). (test)
- **T-9 (fail-closed key)** with `GLEIPNIR_MARKER_KEY_FILE` unset/empty, the MCP
  process refuses to serve the listener (KeyUnavailable), rather than serving
  keyless. (test)
- **T-10 (deny-list negative-check)** for each agent that must not hold the tool,
  its frontmatter carries `"gleipnir-approval_*": false` and does **not** carry
  an over-broad allow. (hardened-path negative-check, below)
- **T-11 (structural — "wraps, never mints" reverse-import scan)** `mcp_server.py`'s
  source contains **NO** reference — by name — to `capture_approval`,
  `mint_approval`, or `load_key`, i.e. **no** `from .server import`/`from .token
  import`/`from ..verify.marker import` (nor any qualified call) of those
  minting/key symbols. This is the reverse-direction complement to T-5's
  import-scan (T-5 asserts the crypto core does not import `mcp`; T-11 asserts the
  MCP wrapper does not import the minting core): it closes the concrete bypass a
  grep for `hmac`/`hashlib` alone misses — a `from .server import capture_approval`
  followed by a call would mint a valid, content-bound approval token from inside
  the MCP's own process (resolving identity against the local host via `tailscale
  whois` on `remote_ip`, `server.py:224-227`), silently defeating the
  separate-authenticated-device approval property (Decision 3 / the Supersession
  clause). The scan asserts `mcp_server.py` imports **only** the closed allow-list
  named in Trace: `run_server`, `register_default_resolvers`,
  `compute_change_hash`, `staged_path_for`, `default_token_dir` — and **no**
  minting/key symbol. (source-scan test)

---

## 6. Design Principles (Gate-1 cognition layer — case (i): OOP/functional code with real structure)

`P ∩ X ≠ ∅` (touches `src/**` — a new module with function/class structure) →
full **SOLID + DRY + SRP + Design Intent**.

**SOLID:**
- **Single Responsibility** — `mcp_server.py` has exactly one reason to change:
  *the MCP tool-surface + process-supervision contract*. It does not own crypto
  (delegated to `token.py`/`marker.py`, untouched), HTTP handling (delegated to
  `server.py`, imported), or identity resolution (delegated to `identity/**`,
  untouched). If the crypto/HTTP/identity logic changes, `mcp_server.py` does
  **not** change; if the MCP tool surface or launch supervision changes, only it
  changes.
- **Open/Closed** — the design extends the approval subsystem (adds an MCP entry
  point + a tool) **without modifying** `server.py`'s logic, `token.py`,
  `gate.py`, or the resolver seam. The listener is reused by import.
- **Liskov** — `mcp_server.py` introduces no subclass of an existing type; it
  composes (imports+calls) rather than subclasses, so no parent contract is at
  risk. (Attested: no substitution relationship introduced.)
- **Interface Segregation** — the MCP surface is a single narrow tool
  (`request_approval`); it does not expose the listener's HTTP internals or the
  crypto mint/validate as tools. Agents see one focused capability.
- **Dependency Inversion** — `mcp_server.py` depends on `server.py`'s
  **public functions** (`run_server`, `register_default_resolvers`) and the
  existing staging/URL **contract**, not on private HTTP-handler internals; the
  `mcp` SDK is an outer detail confined to this one module, never inverted into
  the crypto core.

**DRY:**
- `request_approval` **reuses** the `pending-<hash>.json` envelope shape and the
  `GLEIPNIR_APPROVAL_BASE_URL` URL contract already fixed by
  `tier3-gate.ts`/`server.py` — it does **not** re-implement a second staging
  format or URL scheme (Decision 14). The listener is **imported** from
  `server.py`, not copied (Decision 13). The `mcp` invocation mirrors the two
  existing brokers' `mcp.run(transport="stdio")` shape rather than inventing a
  new startup idiom. The token directory constant is the one Decision-17 dir,
  not re-derived.

**Single Responsibility (named, per module):**
- `mcp_server.py`: *own the opencode-facing MCP process — supervise the listener
  and expose `request_approval` — and nothing else* (no crypto, no HTTP handler,
  no identity logic).

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**
> **`mcp_server.py` is a thin, import-only wrapper: it MUST contain no HTTP
> request-handler class and no HMAC/hashlib mint-or-validate call of its own, the
> `mcp` SDK import MUST NOT appear in `token.py`, `gate.py`, or
> `verify/marker.py`, and `mcp_server.py` MUST NOT import or call any
> minting/key symbol.** A reviewer can falsify this by pointing at (a) an HTTP
> handler or a `hmac.new(...)`/`hashlib.sha256(...)`-for-minting call inside
> `mcp_server.py`, or (b) an `import mcp` (or `from mcp...`) anywhere in the three
> named crypto-core files, or **(c) any import of, or call to,
> `capture_approval`/`mint_approval`/`load_key` from within `mcp_server.py`**
> (which would let the MCP process mint a valid approval token itself — the
> "wraps, never mints" bypass; see T-11). Any of the three is a violation of the
> intent, caught by T-4/T-5/T-11.

This Design Intent is checked at **spec-review** (intent-quality sub-check: is it
specific/falsifiable? — yes, it names the exact forbidden constructs) and at
**quality** (honour check: does the applied `mcp_server.py` honour it? — verified
by T-4/T-5/T-11 and the byte-identity diff T-6).

---

## 7. Execution Workflow

**Pipeline:** the **full hardened 8-stage pipeline** (`brainstorm → plan →
spec-review → test → code → quality → git → gate`). This plan is
**Tier-3-enforcement-bearing** and does **NOT** take the light prose/config
track, because `P` touches enforcement-path set `E` on **three** independent
grounds (Axis 2(a) path rule for `opencode.jsonc` and `.envrc`; Axis 2(b) content
rule for the `.gleipnir/agents/*.md` `tools:` deny rows).

**Stage handoffs:**
- **spec-review** (`quality-reviewer`): verify this plan against the brief and
  `plan-format.md`; run the cognition cross-check's **intent-quality sub-check**
  (is the Design Intent specific/falsifiable? — it names the forbidden
  constructs, so yes). Confirm no crypto-core logic is planned to change.
- **test** (`gleipnir-code`): write `tests/test_approval_mcp_server.py` first
  (T-1..T-5, T-8, T-9, and the T-11 reverse-import scan), under the **broker**
  profile.
- **code** (`gleipnir-code`): implement `mcp_server.py` to green; apply the two
  comment/docstring-only supersession edits (provably comment-only).
- **quality** (`quality-reviewer`) — **DUAL PASS + negative-check attestation,
  mandatory** (`stage-role-map.md` "Hardened path"):
  1. **SPEC-CONFORM pass** (rubric = this plan/the brief): `SPEC-CONFORM:
     PASS/FAIL` — including the cognition **honour check** (does the applied
     `mcp_server.py` honour the Design Intent? — T-4/T-5/T-6/T-11).
  2. **BLAST-RADIUS / false-success pass** (rubric = *how could this be wrongly
     green?*): adversarial — find the over-broad grant or the false-CLOSED path;
     includes the **SOLID/DRY dimension** (Important severity).
  3. **Negative-check attestation** — one row **per enforcement-path touch**,
     produced by `quality-reviewer` (never self-attested by the author, L-C8),
     each with the required fields: **grant / narrowest-intended-scope /
     over-broad-form-checked-for / evidence (`[D]` reproducible artifact, not
     narrative) / negative-result / attested_by**, captured against the
     **applied/post-change** file state.
- **git** (`git-ops`): commit only after the dual pass + attestation are green
  and any cognition honour-check divergence is operator-acknowledged.
- **gate** (`orchestrator`): reads attestation, emits pipeline state.

**Enforcement-path touches requiring a negative-check attestation row at
`quality` (enumerated — every one):**

1. **`opencode.jsonc` — the new `mcp."gleipnir-approval"` block.**
   Expected attestation shape:
   - `grant`: add local-MCP `gleipnir-approval` with `command` +
     `environment {PYTHONPATH, GLEIPNIR_MARKER_KEY_FILE:"{env:...}",
     GLEIPNIR_APPROVAL_BASE_URL:"{env:...}"}` + `enabled:true`.
   - `narrowest-intended-scope`: a **reference-only** `{env:VAR}` for the key;
     `enabled:true` for the one new server only; no change to `gleipnir-git`/`-pm`.
   - `over-broad-form-checked-for`: **a literal key value or a literal absolute
     key-file path inlined into `environment`** (instead of `{env:...}`); an
     unintended edit to the existing broker blocks.
   - `evidence` (`[D]`) — **covers BOTH named risks**:
     1. **(literal-secret risk)** `grep -nE '(marker\.key|/keys/|[0-9a-f]{64})'
        opencode.jsonc` against the post-change file → shows only the
        `{env:GLEIPNIR_MARKER_KEY_FILE}` reference, no literal key/path.
     2. **(broker-block-edit risk)** a scoped byte-identity check on the existing
        `gleipnir-git` and `gleipnir-pm` MCP blocks — e.g.
        `git diff opencode.jsonc` restricted to those two blocks shows **no
        changed lines** within them (only the new `gleipnir-approval` block is
        added), or an equivalent pre-vs-post hash comparison of each block's byte
        range → both broker blocks are **byte-unchanged**.
   - `negative-result`: "no literal key/path is present in `opencode.jsonc` (the
     key is a `{env:...}` reference only); AND the existing `gleipnir-git`/
     `gleipnir-pm` broker blocks are byte-unchanged (only the new
     `gleipnir-approval` block was added)."
   - `attested_by`: `quality-reviewer` (≠ author).
2. **Each `.gleipnir/agents/*.md` — the `"gleipnir-approval_*": false` deny row**
   (one attestation row per file edited — **9 non-holder files**: session-scribe,
   quality-reviewer, gleipnir-code, notify, gleipnir-plan, project-mgr, git-ops,
   gleipnir-brainstorm, orchestrator).
   Expected attestation shape:
   - `grant`: add `"gleipnir-approval_*": false` to that agent's `tools:` block.
   - `narrowest-intended-scope`: the **exact** namespace glob `gleipnir-approval_*`
     denied; no wider tool deny; no accidental *allow*.
   - `over-broad-form-checked-for`: a `"gleipnir-approval_*": true` (an
     accidental grant), or a broader `"*": ...` tool change.
   - `evidence` (`[D]`): `grep -n 'gleipnir-approval' <agent>.md` on the
     post-change file → shows exactly the `: false` row.
   - `negative-result`: "the row is `: false` (deny), not `: true`; no other
     `tools:` line changed."
   - `attested_by`: `quality-reviewer` (≠ author).
   **Plus one HOLDER-EXCLUSION attestation row** (Option (ii), operator-decided):
   - `grant`: `tier3-writer` is the **sole holder** — it must hold
     `gleipnir-approval_*` **by absence of a deny** (global-enable pattern).
   - `narrowest-intended-scope`: `tier3-writer.md` carries **no**
     `gleipnir-approval_*` row at all; its two existing broker denies
     (`gleipnir-git_*`/`gleipnir-pm_*`, lines 65–66) are **unchanged**.
   - `over-broad-form-checked-for`: an accidental `"gleipnir-approval_*": false`
     added to `tier3-writer.md` (which would revoke the operator's chosen grant);
     or a second agent left without the deny (an accidental extra holder).
   - `evidence` (`[D]`): `grep -c 'gleipnir-approval' .gleipnir/agents/tier3-writer.md`
     → `0` on the post-change file; and `grep -L 'gleipnir-approval_' .gleipnir/agents/*.md`
     → returns **only** `tier3-writer.md` (exactly one file lacks the deny).
   - `negative-result`: "exactly one roster file (`tier3-writer.md`) lacks the
     `gleipnir-approval_*` deny — it is the sole holder by design; all other 9
     files carry the `: false` deny."
   - `attested_by`: `quality-reviewer` (≠ author).
3. **`.envrc` — the new operator secrets file** (in `E`, Axis 2(a)).
   Expected attestation shape:
   - `grant`: export `OPENCODE_CONFIG_DIR`, `GLEIPNIR_MARKER_KEY_FILE` (path),
     optional `GLEIPNIR_APPROVAL_BASE_URL`.
   - `narrowest-intended-scope`: the **path** form (not the raw key value); no
     other exports.
   - `over-broad-form-checked-for`: the **raw HMAC key value** exported instead of
     the path; unrelated exports leaking into the shell.
   - `evidence` (`[D]`) — **REDACTED form ONLY** (a plain `cat .envrc` is
     **forbidden** here: it would place the operator's real absolute host
     key-path into the written attestation record). Two greps on the applied
     file, neither of which discloses the literal path value:
     1. `grep -c '^export GLEIPNIR_MARKER_KEY_FILE=' .envrc` → expect **`1`**
        (the path-form export is present exactly once);
     2. `grep -Ev '^export (OPENCODE_CONFIG_DIR|GLEIPNIR_MARKER_KEY_FILE|GLEIPNIR_APPROVAL_BASE_URL)=' .envrc`
        → expect **empty output** (no unrelated/unexpected exports, e.g. no raw
        key value line).
   - `negative-result`: "`.envrc` exports the key **path**, not the key value
     (confirmed by the count `1` on the path-form export and empty output from
     the negative grep — with **no literal path value disclosed** in this
     record); and it is gitignored (`.gitignore:21`) so it is never committed."
   - `attested_by`: `quality-reviewer` (≠ author).
4. **`.gleipnir/decisions/tier3-signed-approval.md` — the superseding update.**
   Expected attestation shape:
   - `grant`: append a superseding section recording the MCP-launch change +
     the O-3(b) gap label.
   - `narrowest-intended-scope`: append/annotate only; do **not** rewrite the
     existing converged-design record; **carry the O-3(b) gap label VERBATIM**.
   - `over-broad-form-checked-for`: the O-3(b) gap label **softened or dropped**;
     any unrelated Tier-3 record altered.
   - `evidence` (`[D]`): `grep -F 'isolation-by-convention, not
     isolation-by-capability' .gleipnir/decisions/tier3-signed-approval.md` on the
     post-change file → the verbatim label is present.
   - `negative-result`: "the O-3(b) gap label is present verbatim; no other
     decision record was touched."
   - `attested_by`: `quality-reviewer` (≠ author).
5. **`.gleipnir/decisions/runtime-and-deps.md` — the "Boundary drawn sharply"
   MCP-SDK carve-out widening (Decision 20, found during the `code` stage).**
   Expected attestation shape:
   - `grant`: widen the carve-out to also name the single file
     `src/gleipnir/approval/mcp_server.py` alongside the existing
     `src/gleipnir/broker/**`.
   - `narrowest-intended-scope`: the **single named file**
     `src/gleipnir/approval/mcp_server.py` — no wider `approval/**` glob, no
     any-subpackage widening; `approval/{token.py,gate.py}` and
     `verify/marker.py` remain `mcp`-free.
   - `over-broad-form-checked-for`: the carve-out widened to **ANY subpackage**
     (e.g. dropping the broker-only scoping) OR to a **glob**
     (`src/gleipnir/approval/**` / `approval/**`) **rather than the single named
     file** `src/gleipnir/approval/mcp_server.py`.
   - `evidence` (`[D]`) — three greps on the **applied/post-change** file:
      1. `grep -F 'src/gleipnir/approval/mcp_server.py'
         .gleipnir/decisions/runtime-and-deps.md` → the single-file exception is
         present (present exactly as the named file, not a glob);
      2. `grep -E 'approval/\*\*|approval/[^m]' .gleipnir/decisions/runtime-and-deps.md`
         → **empty output** (no `approval/**` glob and no `approval/`-directory
         widening is present in the carve-out);
      3. `grep -F 'Only `src/gleipnir/broker/**` and the single named file'
         .gleipnir/decisions/runtime-and-deps.md` → **matches** (the restrictive
         "Only `broker/**` **and the single named file** …" framing survived
         intact — the broker-only scoping was NOT dropped and the exception was
         NOT widened to any subpackage; this is the positive counterpart to
         grep 2's absence check, tests the exact "Only" clause from this plan's
         own proposed replacement wording above).
   - `negative-result`: "BOTH named over-broad forms are evidenced. (a) The
     **glob-widening** form is ruled out: the carve-out names the single file
     `src/gleipnir/approval/mcp_server.py` (confirmed present by grep 1) and does
     **NOT** contain an `approval/**` glob or `approval/`-directory widening
     (confirmed by the empty output of grep 2). (b) The **any-subpackage /
     dropped-broker-only-scoping** form is ruled out: the restrictive `Only
     `src/gleipnir/broker/**` and the single named file …` framing is confirmed
     present intact (grep 3 matches), so the broker-only scoping survived and the
     exception was not widened to any subpackage."
   - `attested_by`: `quality-reviewer` (≠ author).

### Decision-record update (durable — operator/build-mode)

`.gleipnir/decisions/tier3-signed-approval.md` gets a **superseding update**
(superseding-banner style, matching how this repo already handles decision
supersession — e.g. `gleipnir-layout-and-memory-model.md` carries a superseding
banner from the original tier3-signed-approval work). The update must:
1. record that **Decision 15's "no auto-start" is superseded** — opencode/an MCP
   config MAY launch the listener (process-supervision only), on the
   key-unreachability + per-request `tailscale whois` rationale (brief point 3 /
   Supersession clause);
2. record the new `mcp."gleipnir-approval"` launch path + the `request_approval`
   tool (B1); and
3. **carry the O-3(b) gap label forward VERBATIM** (the blockquote in Architect)
   into its honesty ledger, labelled "authored, not yet closed" like the
   record's existing S-2/S-3/`tailscale serve` deferrals — this is the explicit
   instruction so the gap does not evaporate between brief, plan, and record.

---

## Material tradeoff — RESOLVED by the operator (Option (ii))

**Status: RESOLVED. Decided by the operator directly (orchestrator ↔ operator,
this session, plain conversation) — NOT a plan-stage recommendation.**

The brief's Decisions/Open-Items did **not** settle **which roster agent(s), if
any, should HOLD the `request_approval` tool.** Because the MCP tool is enabled
globally in `opencode.jsonc` (the broker pattern), **absence of a per-agent deny
= that agent holds the tool by default.** So authoring the deny-list is not
mechanical: it encodes a **material Tier-3 capability decision** — *who is
allowed to stage Tier-3 content and obtain an approval URL.* This plan surfaced
it and did **not** resolve it; the operator has now resolved it directly.

**The options that were put to the operator:**
- **(i) no agent holds it** — every roster agent gets `"gleipnir-approval_*":
  false`; the tool exists but only a human/operator context could invoke it
  (most conservative; the launch benefit still lands, the agent-facing benefit
  does not);
- **(ii) only `tier3-writer` holds it** — it is the role that hits gated Tier-3
  writes, so it is the natural (and narrowest) holder;
- **(iii) a specific stage role holds it** (e.g. whichever role stages Tier-3
  changes in the pipeline).

**OPERATOR'S DECISION (this session, direct conversation with the
orchestrator): Option (ii) — only `tier3-writer` holds `gleipnir-approval_*`
(the tool namespace, per Decision 16). Options (i) and (iii) were rejected.**

This is the single-holder pattern applied to the new `gleipnir-approval`
namespace: `tier3-writer` is the single holder (mirroring how `git-ops` is the
single holder of `gleipnir-git_*` and `project-mgr` of `gleipnir-pm_*`), and it
holds by **absence of a deny** (the tool is globally enabled in
`opencode.jsonc`). Every OTHER roster agent gets an explicit
`"gleipnir-approval_*": false` deny row — exactly as `opencode.jsonc`'s own
comment prescribes for the broker namespaces ("Single-holder scoping is done
per-agent by DENY-LIST … every OTHER roster agent denies BOTH"), the SAME
pattern, single-holder = `tier3-writer` instead of the two dual-holders.

**The full enumerated list of agent files that get the new
`"gleipnir-approval_*": false` deny row** (verified against the current roster
via `ls .gleipnir/agents/*.md` — **10 files total; 9 non-holders get the deny,
the 1 holder does not**):

| # | Agent file | Gets `"gleipnir-approval_*": false`? | Existing `tools:` block |
|---|---|---|---|
| 1 | `session-scribe.md` | **YES** (deny) | has both broker denies (42–43) |
| 2 | `quality-reviewer.md` | **YES** (deny) | has both broker denies (26–27) |
| 3 | `gleipnir-code.md` | **YES** (deny) | has both broker denies (63–64) |
| 4 | `notify.md` | **YES** (deny) | has both broker denies (20–21) |
| 5 | `gleipnir-plan.md` | **YES** (deny) | has both broker denies (24–25) |
| 6 | `project-mgr.md` | **YES** (deny) | has `gleipnir-git_*: false` only (23) — pm-namespace holder |
| 7 | `git-ops.md` | **YES** (deny) | has `gleipnir-pm_*: false` only (51) — git-namespace holder |
| 8 | `gleipnir-brainstorm.md` | **YES** (deny) | has both broker denies (29–30) |
| 9 | `orchestrator.md` | **YES** (deny) | has both broker denies (47–48) |
| 10 | `tier3-writer.md` | **NO — the sole HOLDER** (holds by absence of a deny) | has both broker denies (65–66); the approval namespace is left un-denied so it holds it |

Every one of the 9 non-holder files already has a frontmatter `tools:` block
(confirmed: each carries at least one existing `"gleipnir-*_*": false` broker
row), so the change is a **single added line** in an existing block, never a
new block. `tier3-writer.md` is **excluded** — adding a deny there would revoke
the operator's chosen grant.

This decision is now recorded in Decision 17 (index), Assemble step 6, the
Trace artifacts table/note, edge case 6, and the negative-check attestation row
(2) in the Execution Workflow. It is a **Tier-3 capability grant** and belongs
in the durable decision-record update (Execution Workflow → Decision-record
update) so it persists beyond this Tier-0 plan; the plan records it, the
decision record makes it durable.

**Also flag to the operator (a factual correction, adjacent to the above, not a
tradeoff):** the brief's **O-3(a) sub-note asserts `.envrc` is "not Tier-3, not
in the enforcement-path set `E`."** Re-reading `stage-role-map.md` Axis 2(a),
**`.envrc` IS explicitly enumerated in `E`.** I resolved authorship accordingly
(operator-authored, enforcement-bearing — Decision 18(b) / the Architect
subsection), but the operator should be aware the brief was mistaken on that
specific classification so the decision record does not inherit the error.
