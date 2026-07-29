# Plan: Pointy git + PM broker MCP servers (`gleipnir-git` / `gleipnir-pm`)

> **Stage:** `plan` (gleipnir-plan). **Input:** the CONVERGED brief
> `broker-mcp-brainstorm.md` (operator-converged via the orchestrator). This
> plan does **not** re-decide the six material tradeoffs recorded there
> (MECHANISM=`mcp`/FastMCP out-of-core / SCOPE=git+PM only / POINTY 4+4 tools /
> E-1 answer=structural refusal / stateless PM / credential-co-location honestly
> labelled). It plans the *bounded* work those decisions define and sequences
> the Tier-3 dependency-record amendment as an explicit first gate.
>
> **Capability note.** `gleipnir-plan` may write only `.gleipnir/plans/**`
> (Tier 0). This file is the sole artifact of this stage. Every step it
> describes is executed later by the role bound to it — the orchestrator
> sequences that; nothing here is executed now. In particular, this plan
> **names** the Tier-3 edits (runtime-and-deps.md amendment, new decision
> record, opencode.jsonc wiring, agent-file rewrites); it does not write them.

---

## GOTCHA pre-flight (visible, per methodology)

- **Goals checked (`goals/manifest.md`):** "Plan format" (`plan-format.md`) and
  "Methodology (ATLAS/GOTCHA ahead of planning)" apply. This plan follows the
  required Architect / Trace / Link / Assemble / Stress-test / Execution
  Workflow structure. No pipeline-sequencing goal is authored or implied (G-5
  rule respected — sequencing stays with the orchestrator/engine).
- **Order:** plan-before-code confirmed. This is the `plan` stage; no code,
  tests, or git are produced here.
- **Layer placement (GOTCHA layers):** the brokers are **Tools-layer** concerns
  (the git/PM tool surface an agent may call) plus **Args-layer** structural
  enforcement (`commit_changes`'s in-code gate; the deliberate *absence* of any
  force-push argv). They are explicitly **NOT** enforcement-core
  (no G-3/G-5/G-4/memory logic), which is the whole basis for the out-of-core
  dependency carve-out. They do **not** touch G-5 pipeline ordering — the `git`
  stage still binds only to `git-ops`; this feature only changes *how* `git-ops`
  performs it (MCP tools instead of a bash allowlist).
- **Gaps / factual findings named (mechanical, NOT material):**
  1. **`python-dotenv` is NOT needed (Link-time technical call, resolved here).**
     opencode launches each MCP server as a stdio subprocess with an
     `environment:{...}` block that injects env vars directly, so `os.environ`
     already sees `GITLAB_TOKEN`/`GITHUB_TOKEN`/`GLEIPNIR_GIT_PROTECTED_BRANCHES`.
     AETOS's `_load_dotenv` is itself a hand-rolled *stdlib* fallback
     (`git/mcp_server.py:33-51`), not a use of the `python-dotenv` package on the
     hot path. **Recommendation: do NOT adopt `python-dotenv`.** Record it as
     considered-and-rejected in the runtime-and-deps amendment. If a standalone-dev `.env`
     convenience is ever wanted, port AETOS's stdlib `_load_dotenv` helper
     (zero new dependency) rather than adding the package. This is a mechanical
     resolution of the brief's open question, not a re-decision.
  2. **Gleipnir has NO existing `detect_remote`/`parse_remote_url`.** The
     `src/gleipnir/` tree (verify, engine, sandbox, bus, ledger, preflight) has
     no git-remote parsing. The PM platform client's remote/token detection must
     be **built fresh**, influenced by AETOS `git/remote.py` (the
     `RemoteInfo`/`parse_remote_url`/`detect_remote` shape + env-var token
     priority) — influence, not import. Mechanical; planner's call taken here:
     build a small Gleipnir `broker/pm/platform.py` remote+token helper on the
     AETOS pattern.
  3. **The stdlib-only meta-tests are strictly PER-DIRECTORY.** Verified:
     `test_bus_stdlib_only.py`, `test_ledger_stdlib_only.py`,
     `test_preflight_stdlib_only.py` each hardcode their own `*_DIR` and glob
     only that directory. **No test scans the whole `src/gleipnir/` tree.**
     Consequence: introducing `import mcp` under `src/gleipnir/broker/` would
     **NOT** silently fail any existing meta-test (none looks there). So the
     brief's phrasing "the meta-test still passes" is true only vacuously. The
     honest requirement (see Stress-test T-F) is: **add a NEW broker-scoped
     conformance test** that (i) asserts `mcp` appears *only* under `broker/`
     and never leaks into the core packages, and (ii) documents the broker
     exemption explicitly rather than relying on omission. Recommendation made
     in Stress-test T-F.

**New material tradeoff found?** **Yes — one (in addition to the deadlock
tradeoff below), and it is already operator-converged; the planner is recording,
not deciding.** During build a verified fact surfaced (`mcp>=1.0.0` resolves to
`mcp 2.0.0`, which REMOVED `mcp.server.fastmcp`), which forced a packaging /
dependency-versioning decision. The operator converged on **per-component
independent versioning + a bounded per-broker MCP-SDK compliance matrix**
(replacing the earlier single top-level `broker` optional-dependency extra).
This is baked in throughout this revision and recorded as a second resolved
material tradeoff in the final "New material tradeoff report" section. The six
converged design decisions (4+4 tools, E-1 structural refusal, git-ops
narrow-not-delete allowlist, credential honesty labels, scope, stateless PM)
stand unchanged. Everything else below is mechanical wiring, a factual
correction, or a Link-time technical resolution the brief already delegated to
the planner.

---

## 1. Architect

**Problem (one sentence):** Replace `git-ops`'s unsound E-1 bash force-push
*pattern* denies and stand up `project-mgr`'s missing PM namespace by building
two pointy, purpose-scoped FastMCP stdio broker servers — `gleipnir-git`
(4 tools) and `gleipnir-pm` (4 tools) — where the git write path enforces
protected-branch and secret-scan refusal *structurally in Python* and no
force-push argv is ever constructed, with `mcp` declared as a justified,
isolated, **out-of-enforcement-core** dependency.

**User:** the `git-ops` and `project-mgr` roster agents (and behind them the
orchestrator sequencing the `git` stage), plus the **operator** who owns the
trust-surface decision (the Tier-3 dependency record and agent rewrites).

**Measurable success criteria:**

1. Two MCP servers exist under `src/gleipnir/broker/` and register in
   `opencode.jsonc` under `mcp.gleipnir-git` and `mcp.gleipnir-pm`, each
   `type:"local"` with a `command` launching `python -m` on the server module
   and an `environment` block injecting the needed env vars.
2. `gleipnir-git` exposes **exactly four** tools: `git_status`, `git_diff`
   (read); `commit_changes`, `push_current_branch` (write, gated). No more.
3. `gleipnir-pm` exposes **exactly four** tools: `issue_create`, `issue_update`,
   `issue_comment`, `issue_close`. No more.
4. `commit_changes` **structurally refuses** (a) commits on a protected branch
   and (b) commits whose staged diff matches any secret pattern — returning a
   redacted structured finding, never proceeding to the commit argv.
5. **No force-push is constructible.** `push_current_branch` builds only
   `["push", "origin", <branch>]` (and a `-u` tracking retry) — `--force`/`-f`
   appears nowhere in the broker's argv construction, and no tool exposes a
   force parameter. Force-push is *absent*, not *denied*.
6. `git-ops.md`'s bash allowlist is **narrowed, not deleted**: the two
   force-push pattern denies (`"git push --force*"`, `"git push -f*"`, lines
   32-33) and the write verbs now covered by MCP tools (`"git commit*"`,
   `"git push"`, `"git push origin*"`, `"git add*"`) are removed; the
   non-dangerous branch/sync verbs with **no MCP replacement** —
   `"git status*"` (also covered by `git_status` but harmless to keep),
   `"git checkout*"`, `"git switch*"`, `"git branch*"`, `"git merge*"`,
   `"git fetch*"`, `"git pull*"` — are **KEPT** as a scoped bash allowlist
   alongside the new MCP tools. This prevents the deadlock where a
   protected-branch `commit_changes` refusal leaves no tool to switch off `main`.
   `commit_changes` **internally stages** (`git add -A`, or per-file `git add`
   when `files` is given) as part of the tool, so the separate `"git add*"` bash
   verb is **not** needed and is removed. `project-mgr.md` is bound to the PM
   broker's tool surface.
7. `runtime-and-deps.md` is amended to carve the `broker/**` layer out of the
   enforcement-core stdlib-only scope and to record the MCP SDK (FastMCP) as a
   justified, isolated, out-of-core dependency **owned per-component** — each
   broker is its own independently-versioned component with its own
   `pyproject.toml`, its own VERSION, and its own **bounded** MCP-SDK
   compliance range (NOT a single frozen framework-wide pin) — and to record
   `python-dotenv` as **considered and rejected** (see pre-flight gap 1).
   *(This amendment has already been made and corrected to the matrix model this
   session — see Assemble Step 1.)*
7a. **Two per-broker component manifests exist:**
    `src/gleipnir/broker/git/pyproject.toml` and
    `src/gleipnir/broker/pm/pyproject.toml`, each declaring (i) its OWN component
    VERSION (mirroring AETOS's `dynamic = ["version"]` + `[tool.setuptools.dynamic]
    version = {file = "VERSION"}` from a sibling `VERSION` file) and (ii) its OWN
    **bounded** MCP-SDK compliance range that actually CONTAINS FastMCP — e.g.
    `mcp>=1.0,<2` (which keeps `mcp.server.fastmcp`), never an open-ended
    `>=1.0.0` (which resolves to a FastMCP-less `mcp 2.0.0`). The two brokers are
    decoupled: each fixes and records its own verified-green matrix independently,
    NOT tied to the framework version or to the other broker. The
    enforcement-core `pyproject.toml` (repo root) stays `dependencies = []`.
8. A new durable decision record `.gleipnir/decisions/broker-mcp.md` exists and
   carries the honesty label: this feature closes only E-1's **argument-policy**
   half; credential **unreachability** is NOT closed (the token is still
   co-located with the session address space until S-2 gives the broker a
   separate one).
9. The enforcement core remains stdlib-only, proven by a **new broker-scoped
   conformance test** (Stress-test T-F).

**Constraints (from the brief — FIXED, not re-litigated):**

- **MECHANISM:** adopt `mcp`/FastMCP (Option B), isolated & out-of-core. The
  runtime-and-deps amendment (Tier-3) MUST land before the dependency is
  introduced in code. **Packaging (operator decision):** each broker is its own
  independently-versioned component with its own `pyproject.toml` + VERSION and
  its own bounded MCP-SDK compliance range (NOT a single top-level shared extra,
  NOT a frozen framework-wide pin).
- **SCOPE:** git broker + PM broker ONLY. Notify explicitly **deferred**
  (would add `slack-sdk`; untouched here).
- **POINTY SURFACES:** exactly 4 + 4 tools as enumerated. No scope creep — no
  `create_pr`, no `git_log`, no branch-management tools, no PM milestones/time
  tracking beyond the 4 verbs.
- **E-1 ANSWER:** port the AETOS guard *pattern* (not code): `is_protected_branch`
  + secret-scan combined into a single pre-commit gate wired into
  `commit_changes`; force-push structurally absent from `push_current_branch`.
- **PM broker:** stateless, no local cache (no SQLite); token via
  `GITLAB_TOKEN`/`GITHUB_TOKEN` env, platform detected from the remote.
- **Influence, don't steal.** AETOS `guards.py`/`remote.py`/`mcp_server.py` are
  the *pattern* (tool shape, guard structure, platform split); Gleipnir writes
  its own modules under its own package. No AETOS code/dependency import.
- **Runtime:** Python >= 3.11 (matches `pyproject.toml`). Servers launched by
  opencode as stdio subprocesses.
- **Trust tiers (two kinds of Tier-3, stated precisely):** all five
  operator-authored artifacts are Tier-3, but they split by *enforcement*:
  - **Capability-enforced Tier-3** — `.gleipnir/decisions/runtime-and-deps.md`,
    `.gleipnir/decisions/broker-mcp.md`, `.gleipnir/agents/git-ops.md`,
    `.gleipnir/agents/project-mgr.md`. These live under `.gleipnir/**`, which
    `gleipnir-code`'s grant explicitly denies (`edit "*":allow` **except**
    `.gleipnir/**` and `.git/**`). A bounded code agent **cannot** write them
    today — enforced by capability.
  - **Cooperative-policy Tier-3** — `opencode.jsonc`. It sits at the **repo
    root, outside `.gleipnir/**`**, so `gleipnir-code`'s grant does **NOT** deny
    it: a bounded code agent **could** structurally write it today. It is
    Tier-3 **by intent / cooperative policy**, not by capability — the same
    honesty posture `.gleipnir/decisions/context-cap.md:82-84` already
    established for `opencode.jsonc`. We still **route it to the
    operator/build-mode** by convention; we do not claim the capability layer
    prevents an agent from touching it (it does not, until S-2/G-1 make the
    repo-root config agent-unreachable).
  - The source tree (`pyproject.toml`, `src/gleipnir/broker/**`, `tests/**`) is
    bounded `gleipnir-code` territory (its grant covers `*` except
    `.gleipnir/**` and `.git/**`).

---

## 2. Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Trust tier | Writer | Source-of-truth role |
|---|---|---|---|---|
| Dependency-policy **amendment** (carve `broker/**` out of core scope; record `mcp>=1.0.0`; record `python-dotenv` rejected) | `.gleipnir/decisions/runtime-and-deps.md` (edit) | **Tier-3 POLICY** | **operator only** | The recorded justification that legitimises the `mcp` dependency. MUST exist before code declares the dep. |
| New durable **decision record** (broker design + honesty labels) | new: `.gleipnir/decisions/broker-mcp.md` | **Tier-3 POLICY** | **operator only** | Kept rationale: 4+4 scope, structural-refusal E-1 answer, credential-co-location honesty label, `mcp` version pin, validated opencode MCP-config shape. |
| MCP **registration** + per-agent tool scoping | `opencode.jsonc` — new `mcp.gleipnir-git` / `mcp.gleipnir-pm` blocks | **Tier-3** (repo-root config) | **operator only** | What opencode actually reads to launch the stdio servers and scope tools to agents. |
| `git-ops` **permission rewrite** | `.gleipnir/agents/git-ops.md` (edit) | **Tier-3 POLICY** (capability-enforced) | **operator only** | **Narrow** the bash allowlist: remove the two force-push denies (lines 32-33) and the MCP-covered write verbs (`git commit*`, `git push`, `git push origin*`, `git add*`); **KEEP** `git checkout*`, `git switch*`, `git branch*`, `git merge*`, `git fetch*`, `git pull*` (and `git status*`) — non-dangerous, no MCP replacement. Grant the four `gleipnir-git` MCP tools alongside. Update the E-1 status note. |
| `project-mgr` **binding** | `.gleipnir/agents/project-mgr.md` (edit) | **Tier-3 POLICY** | **operator only** | Bind to the `gleipnir-pm` tool surface (the currently-missing PM namespace). |
| Git broker **component manifest** | new: `src/gleipnir/broker/git/pyproject.toml` (+ sibling `VERSION`) | source tree (under `src/`, **outside `.gleipnir/**`**) | **bounded `gleipnir-code`** | Declares the git broker as its OWN independently-versioned component: own VERSION (dynamic, `{file = "VERSION"}` per AETOS) + its OWN **bounded** MCP-SDK compliance range containing FastMCP (e.g. `mcp>=1.0,<2`, never `>=1.0.0`). Isolated dep so `broker/git/**` imports `mcp` without touching the core `dependencies = []`. |
| PM broker **component manifest** | new: `src/gleipnir/broker/pm/pyproject.toml` (+ sibling `VERSION`) | source tree (under `src/`, **outside `.gleipnir/**`**) | **bounded `gleipnir-code`** | Declares the PM broker as its OWN independently-versioned component: own VERSION + its OWN **bounded** MCP-SDK compliance range containing FastMCP, decoupled from the git broker's and from the framework version. |
| Enforcement-core manifest (UNCHANGED) | `pyproject.toml` (repo root) | source tree | (unchanged) | Stays `dependencies = []` — the MCP SDK lives ONLY in the per-broker component manifests, never at the core. |
| Git broker **guards module** (protected-branch + secret-scan + combined gate) | new: `src/gleipnir/broker/git/guards.py` | source tree | **bounded `gleipnir-code`** | The correctness arbiter of the write path. stdlib-only (`os`, `re`, `subprocess`). |
| Git broker **server** (4 FastMCP tools) | new: `src/gleipnir/broker/git/mcp_server.py` | source tree | **bounded `gleipnir-code`** | Wires the guard into `commit_changes`; constructs no force-push argv. Imports `mcp`. |
| PM broker **platform client** (remote+token detection, REST) | new: `src/gleipnir/broker/pm/platform.py` | source tree | **bounded `gleipnir-code`** | Fresh, AETOS-influenced remote/token detection + GitLab/GitHub REST for the 4 verbs. stdlib-only (`os`, `re`, `subprocess`, `json`, `urllib`). |
| PM broker **server** (4 FastMCP tools) | new: `src/gleipnir/broker/pm/mcp_server.py` | source tree | **bounded `gleipnir-code`** | Exposes `issue_create/update/comment/close`. Stateless, no cache. Imports `mcp`. |
| Package init files | new: `src/gleipnir/broker/__init__.py`, `broker/git/__init__.py`, `broker/pm/__init__.py` | source tree | **bounded `gleipnir-code`** | Package structure. |
| Tests (guards, platform, tool-surface, force-push absence) | new: `tests/test_broker_git_guards.py`, `tests/test_broker_pm_platform.py`, `tests/test_broker_tool_surface.py`, `tests/test_broker_stdlib_only.py` | source tree | **bounded `gleipnir-code`** | The arbiter. Written test-first (see Assemble). |

**Critical Trace consequence:** the feature is **split** across two authorship
zones. The dependency record, decision record, `opencode.jsonc` wiring, and both
agent-file rewrites are **Tier-3 operator actions** a code agent cannot perform.
The `pyproject.toml` extra, all `src/gleipnir/broker/**` modules, and all
`tests/**` are **bounded `gleipnir-code`** deliverables. This is made explicit in
the Execution Workflow's operator-vs-code-agent split table.

### Chosen module layout (resolving brief open question "package/module layout")

```
src/gleipnir/broker/
  __init__.py
  git/
    __init__.py
    pyproject.toml   # git broker COMPONENT manifest: own version + own bounded MCP-SDK range (e.g. mcp>=1.0,<2)
    VERSION          # git broker's own component version (dynamic {file="VERSION"}, AETOS pattern)
    guards.py        # is_protected_branch + SECRET_PATTERNS + scan + combined gate; stdlib-only
    mcp_server.py    # FastMCP "gleipnir-git", 4 tools; imports guards + mcp
  pm/
    __init__.py
    pyproject.toml   # pm broker COMPONENT manifest: own version + own bounded MCP-SDK range, decoupled from git broker
    VERSION          # pm broker's own component version
    platform.py      # RemoteInfo/detect_remote/parse_remote_url (fresh, AETOS-influenced) + REST; stdlib-only
    mcp_server.py    # FastMCP "gleipnir-pm", 4 tools; imports platform + mcp
```

Rationale: mirrors the AETOS mono-repo layout — each broker is its **own
independently-versioned component** with its **own `pyproject.toml` + VERSION**
(cf. `../aetos/packages/git/pyproject.toml`, `../aetos/packages/pm/pyproject.toml`,
both `dynamic = ["version"]` + `[tool.setuptools.dynamic] version = {file =
"VERSION"}`). Each component owns and bounds its own MCP-SDK compliance range,
decoupled from the other broker and from the framework version — replacing the
earlier single top-level `broker` extra. **These `pyproject.toml`/`VERSION`
files sit under `src/`, OUTSIDE `.gleipnir/**`, so a bounded `gleipnir-code`
agent CAN write them** (its grant covers `*` except `.gleipnir/**` and
`.git/**`). Keeping each broker's guard/platform logic in a stdlib-only module
separate from the `mcp`-importing server module makes it unit-testable without
`mcp` installed and keeps the `mcp` import surface minimal and locatable by the
conformance test. Note: unlike AETOS (which naively pins `mcp>=1.0.0` — the very
pin that resolves to the FastMCP-less `mcp 2.0.0`), each Gleipnir broker MUST
declare a **bounded** range that actually contains FastMCP. No shared `guards.py`
at `broker/` root — the git guards are git-specific; a shared root module would
be premature.

### Integrations map

```
opencode ──launches──> stdio subprocess: python -m gleipnir.broker.git.mcp_server
                          │                (env injected: GLEIPNIR_GIT_PROTECTED_BRANCHES only —
                          │                 NO platform token needed; see below)
                          └──launches──> python -m gleipnir.broker.pm.mcp_server
                                           (env injected: GITLAB_TOKEN / GITHUB_TOKEN)
        │
   FastMCP tool dispatch
        │
  gleipnir-git ──> guards.py (protected-branch + secret-scan gate) ──> subprocess `git`
                   (push relies on AMBIENT host git/SSH credential config — no token)
  gleipnir-pm  ──> platform.py (detect_remote + token) ──> GitLab/GitHub REST (urllib)
```

- **Git-broker push authentication (Issue-2 determination, stated plainly):**
  `push_current_branch` runs plain `git push origin <branch>` (and a `-u`
  tracking retry) via `subprocess`. It does **NOT** use `GITLAB_TOKEN` /
  `GITHUB_TOKEN`. Push authenticates through the **ambient git/SSH credential
  configuration already present on the host** (SSH key or git credential-helper),
  which is outside the broker's control and outside its address space. This
  matches the influencing AETOS pattern, where `repo.py:_run_git` runs bare
  `git` in `cwd` with no credential injection and `push_branch` constructs
  `["push", "origin", branch]` with no token — verified this session. Gleipnir's
  own answer: **the git broker needs no platform token.**
- **PM-broker token source:** `os.environ` only (no `python-dotenv`; see
  pre-flight gap 1). The PM broker is the **only** broker that holds a platform
  token; `platform.py` resolves it with env-var priority
  (`GITLAB_TOKEN`/`GITHUB_TOKEN`) over any URL-embedded token. The git broker's
  `environment:{}` block therefore carries **only**
  `GLEIPNIR_GIT_PROTECTED_BRANCHES`, not a token.
- **Protected-branch source:** `GLEIPNIR_GIT_PROTECTED_BRANCHES` env
  (comma-separated, default `main,master`) — the Gleipnir-named equivalent of
  AETOS's `AETOS_GIT_PROTECTED_BRANCHES` (resolves the brief's env-var-name open
  question).
- **Per-agent scoping:** `opencode.jsonc` scopes `gleipnir-git` tools to
  `git-ops` and `gleipnir-pm` tools to `project-mgr`, keeping the added context
  surface minimal (the pointy-scope constraint).

### Edge cases

1. **Commit on a protected branch** → refuse structurally; return
   `{"passed": false, ...on_feature_branch.error...}`; never reach the commit argv.
2. **Secret in the staged diff** → refuse; return redacted findings
   (`match[:6]+"..."+match[-4:]`), never commit.
3. **Force-push requested** → impossible: no tool takes a force flag; no argv
   contains `--force`/`-f`. The request cannot even be expressed.
4. **PM call with no token** → structured `{"success": false, "error": "..."}`
   (no crash), matching AETOS's `has_token()` guard shape.
5. **Offline / API unreachable** → PM broker is stateless (no cache); returns a
   structured error, does not hang beyond a bounded `urllib` timeout.
6. **`mcp` not installed / wrong `mcp` version** → the server module fails to
   import; this is why the guard/platform logic lives in separate stdlib-only
   modules (unit-testable without `mcp`) and why each broker's own component
   `pyproject.toml` must declare a **bounded** MCP-SDK range that contains
   FastMCP (e.g. `mcp>=1.0,<2`). A naive `>=1.0.0` would resolve to `mcp 2.0.0`,
   which removed `mcp.server.fastmcp`, and `from mcp.server.fastmcp import
   FastMCP` would then fail at import — the acceptance check (T-D/T-H) forbids
   that unbounded pin. The conformance test asserts core modules never import
   `mcp`.
7. **Push when no upstream tracking is set** → the `-u` retry path
   (`["push", "-u", "origin", branch]`) — still no force flag.
8. **Data-file staging** (`.db`, `.env`, `venv/`) — AETOS's guard also refuses
   these. **Decision for the planner (mechanical):** keep the data-file check in
   the combined gate (it is a strict *superset* safety, costs nothing, and the
   converged E-1 answer is "port the guard pattern"). It is additive safety, not
   scope creep of the *tool surface* (still 4 tools). Recorded so it is explicit,
   not silent.

---

## 3. Link — what must be validated BEFORE building

Every fact below was re-read from the actual files this session (extending the
brief's Explore pass):

- **L1 (dependency-record precedence — the first gate).** The repo-root
  `pyproject.toml` today is `dependencies = []` with the stdlib-only comment
  pointing at `runtime-and-deps.md`. `runtime-and-deps.md` states a new runtime
  dep "requires a recorded justification here … it is a decision, not a
  convenience." **Therefore the Tier-3 amendment MUST land before either
  per-broker component `pyproject.toml` declares the MCP-SDK dependency.**
  Confirmed done this session: the amendment (`runtime-and-deps.md` §"Amendment
  — the broker/integration layer is NOT enforcement core") already records the
  **per-component matrix model** — each broker owns its own `pyproject.toml`,
  own VERSION, own bounded compliance range — and the **FastMCP-removal version
  caveat** (`mcp>=1.0.0` → `mcp 2.0.0`, no `mcp.server.fastmcp`; use `mcp>=1.0,<2`
  or standalone `fastmcp`). The code manifests (Step 4) must be consistent with
  that record. This ordering is not stylistic — declaring the dep in code before
  the justifying record exists would violate the stated policy.
- **L2 (`python-dotenv` not needed).** Resolved in pre-flight gap 1: opencode's
  `environment:{}` block injects env into the subprocess; `os.environ` suffices.
  Recommendation: reject `python-dotenv`; record it as considered-and-rejected in
  the amendment.
- **L3 (no existing remote parser).** Confirmed via glob of `src/gleipnir/**`:
  no `remote`/`detect_remote`/`parse_remote_url` anywhere. Build fresh in
  `broker/pm/platform.py`, influenced by AETOS `git/remote.py`. (AETOS reuses
  its git remote helper from the PM package; Gleipnir has no git broker remote
  helper to share yet, so the PM broker owns its own — acceptable; a later
  refactor could share it, out of scope now.)
- **L4 (force-push is already structurally absent in the influencing pattern).**
  Confirmed: AETOS `repo.py:push_branch` (lines 454-484) constructs only
  `["push", "origin", branch]` and `["push", "-u", "origin", branch]` — no
  `--force`/`-f` anywhere. The Gleipnir port inherits this by construction; the
  E-1 "structural absence" requirement is satisfied by *not writing* a force
  path, and asserted by test T-A.
- **L5 (guard pattern shape).** Confirmed: AETOS `guards.py` gives
  `get_protected_branches()`/`is_protected_branch()`, `SECRET_PATTERNS` (14
  patterns) + `scan_diff_for_secrets()`, and `pre_commit_checklist()` combining
  branch + secrets (+ data-files) into one pass/fail result. Gleipnir's
  `broker/git/guards.py` reimplements this shape freshly (influence), reading
  `GLEIPNIR_GIT_PROTECTED_BRANCHES`.
- **L6 (stdlib-only meta-tests are per-directory).** Confirmed: `test_bus_*`,
  `test_ledger_*`, `test_preflight_*` each hardcode a single `*_DIR` and glob
  only that dir; **none scans `broker/` or the whole tree.** So `broker/`'s
  `mcp` import will not fail any existing meta-test. The plan therefore ADDS a
  broker-scoped conformance test (T-F) rather than relying on omission.
- **L7 (opencode MCP config shape).** The `mcp.<name>` `type:"local"` +
  `command:[...]` + `environment:{...}` + per-agent `tools:{}` shape is inherited
  from the brief's prior-session opencode-docs fetch and matches the AETOS
  config pattern. **This is the one item NOT re-verified against live opencode
  docs this session** — flagged as a known-unknown to confirm at wiring time
  (Assemble Step 5 is an operator action that will validate the shape against
  this environment's opencode before committing). Not a material tradeoff; a
  wiring-verification item.

**Gate rule:** L1 is a hard ordering gate — the runtime-and-deps amendment
(Assemble Step 1, already persisted + corrected to the matrix model this
session) must precede any code that declares or imports `mcp` in either
per-broker component manifest (Steps 2+). Nothing else is legitimate.

---

## 4. Assemble — intended build order

Ordered so (i) the Tier-3 dependency justification lands before the dependency
is introduced, (ii) tests precede implementation (Axiom 1 — the test is the
arbiter), (iii) the remaining Tier-3 wiring (config + agent files + decision
record) lands last, and (iv) a restart-verify step proves the live wiring.

**Step 1 — [Tier-3 / operator] Amend `runtime-and-deps.md` FIRST — ALREADY DONE
+ CORRECTED this session.** The amendment carves the `broker/**` layer out of the
enforcement-core stdlib-only rule and records the MCP SDK (FastMCP) as a
justified, isolated, out-of-core dependency **owned per-component**: each broker
is its own independently-versioned component with its own `pyproject.toml`, own
VERSION, and its own **bounded** MCP-SDK compliance range/matrix (NOT a single
frozen framework-wide pin, NOT tied to the other broker) — with the boundary
drawn sharply ("enforcement core = stdlib-only; each broker = its own recorded,
bounded dep matrix", per the "scope-creep of the exception" warning). It records
the **FastMCP-removal version caveat** explicitly: `mcp>=1.0.0` resolves to
`mcp 2.0.0`, which removed `mcp.server.fastmcp`, so each broker manifest MUST
declare a bounded range that contains FastMCP (e.g. `mcp>=1.0,<2`, AETOS runs
`mcp==1.27.1`) or the standalone `fastmcp` distribution. It records
`python-dotenv` as **considered and rejected** (env injected by opencode;
`os.environ` suffices). This plan's Step 4 code manifests MUST match that
corrected record. *Nothing downstream is legitimate until this record exists —
it does.*

**Step 2 — [code] Write FAILING tests first (test-first, Axiom 1).** Before any
implementation:
- `tests/test_broker_git_guards.py`: protected-branch refusal (default
  `main`/`master` + custom `GLEIPNIR_GIT_PROTECTED_BRANCHES`); secret-scan
  detects a planted fake secret in a `+`-added diff line and returns a redacted
  finding; combined gate `passed:false` on either failure; data-file detection.
- `tests/test_broker_pm_platform.py`: `parse_remote_url` handles HTTPS/SSH/SCP;
  platform detection (github vs gitlab); env-var token priority; `has_token()`
  false → structured error, no crash. REST calls mocked (no live network in the
  test).
- `tests/test_broker_tool_surface.py`: introspect each FastMCP server's
  registered tool names and assert **exactly** the 4+4 set (T-D) and that no
  registered tool exposes a force/`--force`/`-f` parameter (supports T-A).
- `tests/test_broker_stdlib_only.py`: the broker-scoped conformance test (T-F).
These MUST fail (modules absent) at authoring — that is the point.

**Step 3 — [code] Implement `broker/git/guards.py`** (stdlib-only) to satisfy the
guard tests: `get_protected_branches`/`is_protected_branch` reading
`GLEIPNIR_GIT_PROTECTED_BRANCHES`; `SECRET_PATTERNS` + `scan_diff_for_secrets`
(redacting matches); `check_staged_data_files`; a combined pre-commit gate. No
`mcp` import here (keeps it unit-testable + core-clean).

**Step 4 — [code] Implement the servers + PM platform client:**
- `broker/pm/platform.py` (stdlib-only): fresh `RemoteInfo`/`parse_remote_url`/
  `detect_remote` + env-var token resolution + GitLab/GitHub REST (via `urllib`,
  bounded timeout) for the 4 verbs.
- `broker/git/mcp_server.py`: `FastMCP("gleipnir-git")` with exactly
  `git_status`, `git_diff`, `commit_changes` (wired to the guard — refuse before
  any commit argv), `push_current_branch` (argv `["push","origin",branch]` + `-u`
  retry, **no force path**). `mcp.run(transport="stdio")`.
- `broker/pm/mcp_server.py`: `FastMCP("gleipnir-pm")` with exactly
  `issue_create`, `issue_update`, `issue_comment`, `issue_close`, stateless,
  token from env, structured error when no token. `mcp.run(transport="stdio")`.
- **Author the two per-broker component manifests** (now legitimate — Step 1
  recorded the per-component matrix model). Each is its own `pyproject.toml`
  under `src/gleipnir/broker/{git,pm}/` with a sibling `VERSION` file, mirroring
  AETOS's `dynamic = ["version"]` + `[tool.setuptools.dynamic] version = {file =
  "VERSION"}` pattern:
  - `src/gleipnir/broker/git/pyproject.toml` — own component name/version; its
    OWN **bounded** MCP-SDK compliance range (e.g. `mcp>=1.0,<2`), NEVER an
    open-ended `>=1.0.0`.
  - `src/gleipnir/broker/pm/pyproject.toml` — own component name/version;
    its OWN bounded range, chosen independently of the git broker.
  The repo-root `pyproject.toml` stays `dependencies = []` — do NOT add a
  top-level `broker` extra. Each broker fixes its bounded range to **whatever it
  verified green**, then **verify FastMCP actually imports** for that pin
  (`python -c "from mcp.server.fastmcp import FastMCP"` under the installed
  matrix version) **before proceeding** — the guard against silently pinning a
  FastMCP-less `mcp 2.x`. Record the verified-green range in that broker's own
  manifest. Then run the Step-2 tests to green.

**Step 5 — [Tier-3 / operator] Wire `opencode.jsonc`.** Add `mcp.gleipnir-git`
and `mcp.gleipnir-pm` blocks (`type:"local"`, `command:["python","-m",
"gleipnir.broker.git.mcp_server"]` / `...pm.mcp_server`, `environment:{...}`),
per-agent `tools` scoping (git tools → `git-ops`, pm tools → `project-mgr`).
**Validate the config shape against this environment's opencode first** (Link L7
known-unknown).

**Step 6 — [Tier-3 / operator] Rewrite the agent files.**
- `git-ops.md`: **narrow** the bash allowlist, do NOT delete it. Remove ONLY the
  two force-push pattern denies (`git push --force*`, `git push -f*`, lines
  32-33) and the write verbs the new MCP tools now cover (`git commit*`,
  `git push`, `git push origin*`, and `git add*` — `git add*` drops because
  `commit_changes` internally stages via `git add -A` / per-file `git add`).
  **KEEP** `git status*`, `git checkout*`, `git switch*`, `git branch*`,
  `git merge*`, `git fetch*`, `git pull*` as a scoped bash allowlist **alongside**
  the four new `gleipnir-git` MCP tools — these are non-dangerous, have no MCP
  replacement, and prevent the commit-deadlock (a session left on a protected
  branch must still be able to `checkout`/`switch` off it). Update the E-1 status
  note to say the argument-policy half is now closed structurally
  (credential-unreachability half still open — see honesty label).
- `project-mgr.md`: bind to the four `gleipnir-pm` tools (the previously-missing
  PM namespace).

**Step 7 — [Tier-3 / operator] Author the decision record**
`.gleipnir/decisions/broker-mcp.md`: 4+4 scope, structural-refusal E-1 answer,
the `mcp>=1.0.0` pin + `python-dotenv`-rejected note, the validated opencode
MCP-config shape/version, and the **credential-co-location honesty label**
(closes E-1 argument-policy half ONLY; the PM broker's env-injected token stays
co-located with the session trust domain, and the git broker holds no token but
authenticates push via ambient host git/SSH credential config — neither is made
unreachable until S-2 gives the broker a separate address space).

**Step 8 — [Tier-3 / operator] RESTART-VERIFY (live).** Restart opencode so the
new `mcp` blocks load, then run the Stress-test acceptance checks that require a
live server: `git-ops` can invoke a `gleipnir-git` tool; force-push is
structurally absent (no such tool/param); secret-scan fires on a planted fake
secret; protected-branch commit is refused; `gleipnir-pm` performs
create/update/comment/close against a real test target if available, else
mocked. Confirm the tool surface is exactly 4+4 as loaded.

**Assemble step order (summary):**
`1 (Tier-3 runtime-and-deps amendment — done, matrix model) →
2 (code: FAILING tests first) → 3 (code: guards.py) →
4 (code: servers + pm platform + two per-broker pyproject.toml/VERSION with
bounded MCP-SDK ranges + FastMCP-import verify) → 5 (Tier-3 opencode.jsonc
wiring) → 6 (Tier-3 agent-file rewrites) → 7 (Tier-3 decision record) →
8 (restart-verify)`

---

## 5. Stress-test — acceptance checks

Each maps to a required check from the converged instructions. "unit" = runnable
in the test suite (Step 2/4); "live" = restart-verify (Step 8).

- **T-A (force-push structurally IMPOSSIBLE, not merely denied) — unit + live.**
  (i) `tests/test_broker_tool_surface.py` asserts no registered `gleipnir-git`
  tool takes a `force`/`--force`/`-f` parameter. (ii) A source-level assertion /
  grep in the test confirms `push_current_branch`'s implementation constructs
  only `["push","origin",...]` / `["push","-u","origin",...]` and the string
  `--force`/`" -f"` appears nowhere in `broker/git/**`. (iii) live: `git-ops`
  has no tool by which to request a force-push. **Pass = the operation cannot be
  expressed, not that it is caught.**
- **T-B (secret-scan blocks a planted fake secret) — unit + live.** Feed the
  guard a staged-diff string containing a fake token matching a `SECRET_PATTERNS`
  entry (e.g. a synthetic `AKIA…`/`ghp_…`-shaped string on a `+` line);
  `commit_changes`'s gate returns `passed:false` with a **redacted** finding and
  does not commit. Live: attempt a commit with a planted fake secret in a staged
  file → refused.
- **T-C (protected-branch commit refused — ONLY when opted in) — unit + live.**
  **REVISED (operator convergence, see tradeoff report):** protected-branch
  refusal is **opt-in, default OFF** — it is a workflow policy, not a safety
  invariant, and a hard refusal would deadlock an autonomous (L2/L3) operator
  and brick trunk-based / commit-to-`main` users. Non-strict (default): a commit
  on `main` **passes** (assert `passed:true`). With `GLEIPNIR_GIT_STRICT` (or
  `GLEIPNIR_GIT_PROTECT_BRANCHES`) set: the gate refuses on `main` and returns
  the protected-branch error, no commit argv reached. The **secret-scan (T-B) is
  always on regardless of mode** — that is the safety invariant that keeps the
  broker worth using; branch/data-file checks are the opt-in workflow layer.
- **T-D (tool surface is EXACTLY 4+4 — no scope creep) — unit + live.** Introspect
  each server's registered tools: `gleipnir-git` == {`git_status`, `git_diff`,
  `commit_changes`, `push_current_branch`}; `gleipnir-pm` == {`issue_create`,
  `issue_update`, `issue_comment`, `issue_close`}. Assert set **equality** (not
  subset) so an added tool fails the test. Live: confirm the same as loaded by
  opencode.
- **T-D2 (per-broker independent versioning + bounded, FastMCP-containing MCP-SDK
  range) — unit/manifest check.** For **each** broker manifest
  (`src/gleipnir/broker/git/pyproject.toml`,
  `src/gleipnir/broker/pm/pyproject.toml`): (i) it declares its OWN component
  VERSION (dynamic `{file = "VERSION"}` with a sibling `VERSION` present, or an
  explicit version) — proving per-component independent versioning, decoupled
  from the framework version and from the other broker; and (ii) its MCP-SDK
  requirement is a **BOUNDED** range (has an upper bound, e.g. `mcp>=1.0,<2`, or
  targets the standalone `fastmcp` distribution) — **NOT** a naive open-ended
  `mcp>=1.0.0`. The test parses each manifest's dependency spec and FAILS if the
  requirement is unbounded on the upper side OR would admit `mcp 2.x` (which
  removed `mcp.server.fastmcp`). Complementary positive check: under each
  broker's declared/installed range, `from mcp.server.fastmcp import FastMCP`
  succeeds — the range actually CONTAINS FastMCP. The repo-root `pyproject.toml`
  is asserted to remain `dependencies = []` (no top-level `broker` extra). This
  is the direct guard against re-introducing the FastMCP-less-`2.0.0` mistake.
- **T-E (credential co-location HONESTLY labelled) — doc check.** The decision
  record `.gleipnir/decisions/broker-mcp.md` must state explicitly that this
  feature closes E-1's **argument-policy** half only, and must distinguish the
  two brokers: the **PM broker's env-injected token**
  (`GITLAB_TOKEN`/`GITHUB_TOKEN`) is still **co-located** with the session trust
  domain (no separate broker address space until S-2), while the **git broker
  holds no token** and authenticates push via **ambient host git/SSH
  credential-helper config** — so credential **unreachability** is NOT closed
  for either, but for different reasons. `git-ops.md`'s status note must not
  overclaim (it may say the force-push footgun is structurally gone; it must NOT
  say credentials are isolated). Verified by reading the record and the agent
  file.
- **T-F (stdlib-only enforcement-core meta-test — accurate framing + explicit
  recommendation) — meta-test.**
  **Finding (verified this session):** the stdlib-only conformance tests are
  **per-directory** — `test_bus_stdlib_only.py` (`bus/`),
  `test_ledger_stdlib_only.py` (`ledger/`), `test_preflight_stdlib_only.py`
  (`preflight/`). **No test scans the whole `src/gleipnir/` tree or the
  `broker/` directory.** Therefore introducing `import mcp` under `broker/`
  **does NOT silently fail any existing meta-test** — the broker is exempt *by
  omission* today.
  **Recommendation (EXPLICIT):** do **NOT** rely on exemption-by-omission. Add a
  **new** broker-scoped conformance test `tests/test_broker_stdlib_only.py` that:
  (i) asserts the enforcement-core packages (`verify`, `engine`, `sandbox`,
  `bus`, `ledger`, `preflight`) still import **no** non-stdlib top-level module —
  i.e. `mcp` has NOT leaked into the core (a positive guard that the carve-out is
  respected); and (ii) asserts that within `broker/`, `mcp` is imported **only**
  by the `mcp_server.py` modules and that `guards.py`/`platform.py` remain
  stdlib-only (so the guard/platform logic stays testable without `mcp` and the
  `mcp` surface stays minimal and locatable). This converts the silent exemption
  into an *asserted, documented* boundary — directly serving the brief's
  "sharpen the core/non-core line" second-order warning. The existing three
  per-directory tests remain unchanged (they already scope-exclude `broker/` by
  construction). **T-F is unaffected in intent by the packaging change:** the
  `mcp` SDK is now declared in the two per-broker component manifests (not a
  single shared top-level extra), but the carve-out invariant is identical —
  `mcp` appears ONLY under `broker/` (and only in the `mcp_server.py` modules),
  never in the enforcement core. Which manifest declares the dep is orthogonal
  to the core-vs-broker import line this test asserts.
- **T-G (Notify untouched) — doc/grep check.** No `slack-sdk` or notify tooling
  introduced; `notify.md` unchanged; the only runtime dep added is the bounded
  MCP SDK, and only within the two per-broker component manifests.
- **T-H (dependency-record precedence honoured) — authorship/order check.** The
  `runtime-and-deps.md` amendment (Step 1) precedes the two per-broker component
  `pyproject.toml` manifests (Step 4) declaring the MCP-SDK dependency. Verifiable
  by commit order / that the record (already carrying the per-component matrix
  model + FastMCP-version caveat) exists before the dep is declared in code. The
  repo-root `pyproject.toml` stays `dependencies = []` (no top-level `broker`
  extra).
- **T-I (tier integrity) — authorship check.** No bounded `gleipnir-code` agent
  wrote any Tier-3 path (`decisions/**`, `opencode.jsonc`, `agents/**`); all
  Tier-3 edits (Steps 1, 5, 6, 7) were operator actions. Code-agent writes were
  confined to `src/gleipnir/broker/**` (including the two per-broker
  `pyproject.toml` + `VERSION` component manifests, which live under `src/`,
  outside `.gleipnir/**`, and are therefore within the bounded grant) and
  `tests/**`. The repo-root `pyproject.toml` remained `dependencies = []`.

---

## 6. Execution Workflow

**For the orchestrator sequencing this plan.** ATLAS/GOTCHA already ran (this
plan). The pipeline from here: `spec-review → test → code → quality → (Tier-3
operator wiring) → restart-verify`. This feature is **mixed authorship**: the
guard/platform/server source and tests are bounded `gleipnir-code` units; the
dependency record, decision record, `opencode.jsonc` wiring, and agent-file
rewrites are Tier-3 operator actions. The dependency-record amendment gates
everything (L1).

### Operator-vs-code-agent split (explicit)

| # | Task | Zone | Assemble step |
|---|---|---|---|
| 1 | Amend `runtime-and-deps.md` (carve out `broker/**`; record `mcp>=1.0.0`; reject `python-dotenv`) | **Tier-3 / operator only** | 1 |
| 2 | Write failing tests (guards, platform, tool-surface, stdlib-only) | bounded `gleipnir-code` | 2 |
| 3 | Implement `broker/git/guards.py` (stdlib-only) | bounded `gleipnir-code` | 3 |
| 4 | Implement `broker/pm/platform.py`, both `mcp_server.py`, and the **two per-broker component manifests** `broker/git/pyproject.toml`+`VERSION` and `broker/pm/pyproject.toml`+`VERSION` (each: own version + own BOUNDED MCP-SDK range containing FastMCP; verify `from mcp.server.fastmcp import FastMCP` imports); repo-root `pyproject.toml` stays `dependencies = []` | bounded `gleipnir-code` (all under `src/`, outside `.gleipnir/**`) | 4 |
| 5 | Wire `opencode.jsonc` `mcp` blocks + per-agent tool scoping | **Tier-3 / operator only** | 5 |
| 6 | Rewrite `git-ops.md` (**narrow** the bash allowlist: drop only the two force-push denies + MCP-covered write verbs `git commit*`/`git push*`/`git add*`; **KEEP** `git status*`/`checkout*`/`switch*`/`branch*`/`merge*`/`fetch*`/`pull*`; grant the four MCP tools alongside) and `project-mgr.md` (bind PM tools) | **Tier-3 / operator only** | 6 |
| 7 | Author `.gleipnir/decisions/broker-mcp.md` with honesty labels | **Tier-3 / operator only** | 7 |
| 8 | Restart opencode; run live Stress-test checks (T-A..T-D live, T-E doc) | **Tier-3 / operator** (restart + verify) | 8 |

**Why the split matters (two kinds of Tier-3):** a bounded `gleipnir-code`
agent's edit grant covers `*` except `.gleipnir/**` and `.git/**`. So it **can**
write `pyproject.toml`, `src/gleipnir/broker/**`, and `tests/**`, and it **can**
also structurally write `opencode.jsonc` (repo root, outside `.gleipnir/**`).
- **Tasks 1, 6, 7 are capability-enforced Tier-3:** they touch
  `.gleipnir/decisions/**` and `.gleipnir/agents/**`, which the grant explicitly
  denies — a code agent **cannot** write them today.
- **Task 5 (`opencode.jsonc`) is cooperative-policy Tier-3:** the grant does
  **NOT** deny it (repo root, outside `.gleipnir/**`), so a code agent **could**
  write it today. It is routed to the operator **by intent / convention**, not
  by capability — the same honesty posture
  `.gleipnir/decisions/context-cap.md:82-84` established for `opencode.jsonc`.
  It becomes agent-unreachable only after S-2/G-1 make the repo-root config
  OS-unreachable. Do not overclaim that the capability layer prevents it today.

### Bounded `gleipnir-code` task constraints

- **One verb, one object per delegation.** Split as: (a) *author failing tests*;
  (b) *implement guards.py*; (c) *implement pm platform.py*; (d) *implement git
  server*; (e) *implement pm server*; (f) *add pyproject broker extra*. Do not
  bundle exploration with action.
- **stdlib-only outside the server modules.** `guards.py` and `platform.py` must
  import only stdlib (verified by T-F). `mcp` may be imported **only** in
  `*/mcp_server.py`.
- **Influence, don't steal.** Reimplement the AETOS guard/remote *shape* in
  Gleipnir's own package; do not import from or copy AETOS wholesale.
- **No force path, ever.** `push_current_branch` constructs only non-force argv;
  no tool exposes a force parameter. (T-A.)
- **Never write Tier-3 paths.** No edits to `.gleipnir/decisions/**`,
  `.gleipnir/agents/**`, `.gleipnir/skills/**`, `.gleipnir/goals/**`, or
  `opencode.jsonc`.

### Honesty labels to carry forward (bake into `.gleipnir/decisions/broker-mcp.md`)

- **Credential co-location is NOT closed.** This feature closes E-1's
  *argument-policy* half (force-push structurally absent; protected-branch and
  secret-scan refusal in code). It does **not** close the *credential-
  unreachability* half, and the two brokers differ in *what* stays reachable:
  - **PM broker:** the platform **token** (`GITLAB_TOKEN`/`GITHUB_TOKEN`,
    env-injected) remains co-located with the session's trust domain — the PM
    broker runs as an opencode-launched stdio subprocess in the same trust
    domain, not an S-2 separate-address-space broker.
  - **Git broker:** holds **no** platform token; `push_current_branch`
    authenticates via the **ambient host git/SSH credential config**
    (SSH key or credential-helper). Those ambient credentials remain reachable
    from the same trust domain too, but the point is there is no *env-injected
    token* in the git broker to isolate.
  The real fix (a separate broker address space) waits on the S-2 substrate
  boundary. State this plainly per broker; do not gloss it into one blurred
  "platform/push token."
- **`mcp` is now inside the S-2 trusted surface.** It must be pinned
  (`mcp>=1.0.0`) and audited like any dependency; the carve-out applies to
  `broker/**` ONLY — the enforcement core stays stdlib-only (asserted by T-F).
  Guard against scope-creep of the exception.
- **opencode MCP-config shape is coupled to this environment's opencode
  version.** Record the version validated at Step 5/8; an opencode upgrade is a
  re-validation trigger.

### Deferred / out of scope (do not bundle — brief-excluded)

- **Notify broker** (`slack-sdk`) — explicitly deferred (brief).
- **Extra git tools** (`create_pr`, `git_log`, branch management, tags,
  rebase/squash) and **extra PM verbs** (milestones, releases, time tracking) —
  the pointy 4+4 scope is fixed; these are AETOS's ~21/~27 surface, deliberately
  NOT ported.
- **PM local cache** (SQLite) — brief-converged as stateless; no cache.
- **Sharing a single remote helper between git and PM brokers** — a later
  refactor; the PM broker owns its own remote helper for now.
- **The S-2 credential-unreachability fix** — future substrate pass; only its
  honesty label lands here.

---

## New material tradeoff report (to the operator)

**One material tradeoff WAS found — during spec-review — and has been
converged.** The plan's initial draft silently widened the converged change
"drop `git-ops`'s two force-push bash denies (`git push --force*`,
`git push -f*`)" into "delete the **entire** bash git allowlist" — including
`git checkout*`, `git switch*`, `git branch*`, `git merge*`, `git fetch*`,
`git pull*`, which have **no MCP replacement**. That risked a **commit
deadlock**: if a session were left on a protected branch, `commit_changes` would
structurally refuse, and with no `checkout`/`switch` verb left there would be no
tool to move off `main`. This was a genuine material tradeoff (a
lasting/hard-to-reverse capability-surface choice), not a mechanical wiring
detail. **Spec-review caught it**, the **orchestrator routed it to the operator**
as a three-way choice, and the **operator converged on option (a): keep
`checkout`/`switch`/`branch`/`merge`/`fetch`/`pull` (and `status`) as a scoped
bash allowlist ALONGSIDE the new broker tools**, removing from the allowlist
ONLY the two force-push denies and the write verbs the MCP tools now cover
(`git commit*`, `git push*`, `git add*`). This is now correctly reflected in the
Architect success criteria (item 6), the Trace table (`git-ops` permission-
rewrite row), and Assemble Step 6. It is recorded here as a **resolved** material
tradeoff — surfaced and converged, not decided by the planner.

**A THIRD material tradeoff was found — during build (post-implementation) — and
converged: enforcement strictness / adoption.** The operator observed that the
shipped guard baked a *branching workflow* into an *enforcement layer*:
`commit_changes` refused every commit on `main`/`master` unconditionally. That
(a) bricks legitimate trunk-based / commit-to-`main` workflows, (b) **deadlocks
an autonomous L2/L3 operator** that has no human to answer a "switch branches"
prompt, and (c) risks the worst outcome for the framework — people bypassing
Gleipnir entirely because the guard nags more than it helps, losing even the
real safety value. **Converged fix: non-strict by default.** The checks are
split by nature — **secret-scan + structural force-push absence are always-on
SAFETY**; protected-branch refusal and data-file detection become **opt-in
workflow policy, default OFF** (`GLEIPNIR_GIT_STRICT`, or the individual
`GLEIPNIR_GIT_PROTECT_BRANCHES` / `GLEIPNIR_GIT_CHECK_DATA_FILES` toggles).
Reflected in `guards.py` (`strict_mode`/`branch_protection_enabled`/
`data_file_check_enabled`), the revised `test_broker_git_guards.py` (42 tests
green), T-C above, and `.gleipnir/decisions/broker-mcp.md`. This corrects
resolved item 5 below (the data-file check is no longer "always additive" — it
is strict-only) and item 4 (the protected-branch list is consulted only when
protection is opted in).

**No OTHER material tradeoff was found; the six converged decisions hold
unchanged.** Everything else this plan resolved was mechanical or a Link-time
technical call the brief explicitly delegated to the planner:

1. **`python-dotenv` — rejected** (not needed; opencode injects env; `os.environ`
   suffices). Recorded, not a value-choice.
2. **No existing Gleipnir remote parser** — build fresh in `broker/pm/platform.py`,
   AETOS-influenced. Mechanical.
3. **Module layout** — `broker/git/` + `broker/pm/`, guard/platform logic in
   stdlib-only modules separate from `mcp`-importing servers. Mechanical.
4. **Protected-branch env var** — `GLEIPNIR_GIT_PROTECTED_BRANCHES` (default
   `main,master`). Mechanical.
5. **Data-file check** — kept in the combined gate as additive safety (tool
   surface still 4); recorded so it is explicit, not silent.
6. **stdlib-only meta-test framing** — the accurate finding (per-directory tests
   only; `broker/` exempt by omission today) is surfaced with an **explicit
   recommendation to ADD a broker-scoped conformance test** (T-F) that asserts
   the carve-out positively rather than relying on omission. This is a
   test-design recommendation, not an operator value-choice.

**One item is a wiring-verification known-unknown, not a decision:** the exact
`opencode.jsonc` `mcp` block shape for this environment's opencode version is
inherited from a prior-session docs fetch (Link L7), to be confirmed at Step 5
before committing. If — and only if — that verification reveals the MCP-config
mechanism cannot express per-agent tool scoping or `type:"local"` stdio launch
in this environment, that would be a genuine blocker to surface at the
convergence gate; until then it is a mechanical wiring check, not a material
tradeoff.
