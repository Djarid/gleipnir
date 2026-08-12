# Plan: Bridge recovery path — `bridge-status` / `bridge-reset` (L-C19)

**Status:** Tier-0 plan artifact (disposable). Authored by `gleipnir-plan` via
ATLAS Architect/Trace **from** the operator-converged design brief
`.gleipnir/plans/bridge-recovery-brainstorm.md` (Selected Approach: Option A
subsuming C, clear-only, B/D rejected). This plan does **not** re-decide the
approach; it makes it concrete and ready to apply.

**READY-TO-APPLY, OPERATOR-ONLY.** This plan produces artifacts in
`bin/gleipnir-preflight` (already agent-unreachable), `src/gleipnir/preflight/`,
`.gleipnir/logs/` (Tier-1 framework-process writer, no roster grant), and the
`.gleipnir/decisions/` record (Tier-3). **Important correction (spec-review Fix
1):** `src/gleipnir/preflight/` is **NOT** currently protected by the
`.gleipnir/` tier model — `gleipnir-code`'s grant is `edit: "*": allow` with
only `.gleipnir/**` and `.git/**` denied (verified against
`.gleipnir/agents/gleipnir-code.md:11-16`), which **does reach**
`src/gleipnir/preflight/`. So this plan includes a **companion
permission-hardening diff** (add `"src/gleipnir/preflight/**": deny` to
`gleipnir-code.md`'s `permission.edit` map — see **Appendix D**) to close that
gap, and the operator applies both together in build mode, before or alongside
creating `bridge_recovery.py`. That hardening diff is itself Tier-3
(`.gleipnir/agents/*.md` is operator-authored, agent-unwritable). Once applied,
the plan's premise — this recovery tool's source is unreachable by any agent —
becomes actually true. The exact code and diffs below are for the **operator to
apply in a later build-mode session.** The *sole* possible carve-out is the
test files (they live under `tests/`, which `gleipnir-code` *can* write) —
called out explicitly in **§ Execution Workflow → Who may apply what**.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Recovery mechanism & home | Two subcommands on the existing out-of-framework `bin/gleipnir-preflight` CLI | (B) roster-role write-grant; (D) TTL/self-expiry | Operator-converged in brief (WDM 438 vs 242/244). Precedented home; no new agent power over enforcement evidence. **Note:** `src/gleipnir/preflight/` is NOT currently protected by the `.gleipnir/` tier model (`gleipnir-code`'s `edit:"*":allow` grant reaches it); Decision 12 adds a companion permission-hardening diff to close that gap |
| 2 | Reset semantics | **Clear-only (delete)** the bridge file; never re-mint at a state | Re-mint-at-named-state variant | Re-mint resurrects a permissive state = the fail-open the driver docstring forbids (brief pre-mortem #4). Operator-converged |
| 3 | Classification taxonomy | **healthy** / **stale** / **corrupt-or-tampered** / **absent** | 3-way (no explicit `absent`) | Task adds `absent` (no file) as a distinct, safe verdict; maps to "nothing to recover, run the pipeline normally" |
| 4 | Classification engine | Reuse `StateMarker.from_json` + split `validate_state` into MAC-check vs age-check by calling it twice (once at real `max_age`, once at `max_age=∞`) | Re-implement HMAC/age logic in preflight | `tests/test_preflight_stdlib_only.py` forbids `import hmac` and redefining `load_key`/`validate` in this package; must delegate to `gleipnir.engine.bridge` |
| 5 | In-framework-uid refusal signal | **Opt-in configured operator uid** via `GLEIPNIR_OPERATOR_UID` env; if unset, refuse-by-default is impossible so **warn honestly** and proceed on `--confirm-clear` | Fabricate an "am I inside an agent process" check | No reliable in-process agent signal exists in this codebase (confirmed). Brief explicitly says: note the limitation honestly rather than fabricate a check |
| 6 | `--confirm-clear` gating | `bridge-reset` refuses (exit 1) without the flag; prints old state/minted_at/age first, then requires the flag | default-yes / prompt | Brief pre-mortem #2 (no default-yes; scripted/stray clears blocked) |
| 7 | Audit log location & format | Append one dated line to `.gleipnir/logs/bridge-recovery.log` (Tier-1) | write into `var/run/`, or a new Tier | `logs/README.md`: Tier-1 framework-process writer, observation-only, carries provenance. CLI runs as owning uid so it can write there |
| 8 | Never-in-allowlist self-check | Test **and** CLI-startup guard: scan `.gleipnir/agents/*.md` for the literal `gleipnir-preflight`; fail/refuse if present | test-only, or CLI-only | Brief pre-mortem #1 (Critical). Defense-in-depth: a test catches it in CI; a startup guard catches it at runtime even if the test is skipped |
| 9 | Exit-code convention | Reuse the CLI's `0` = ok/healthy-or-clean, `1` = refuse/problem, `2` reserved (unused here) | new codes | Consistency with `config-scan` / boundary fail-closed 0/1/2 convention |
| 10 | Freshness window value | **Do not change** `DEFAULT_MAX_AGE_SECONDS = 3600`; import it, classify against it | pick a new window | Brief Open Question #1: explicitly undecided, out of scope |
| 11 | Dispatch shape | New leading positional tokens `bridge-status` / `bridge-reset` in `__main__.main()`, mirroring the `config-scan` branch exactly | argparse subparsers refactor of the whole CLI | Brief mandates "mirroring the existing `config-scan` dispatch pattern"; minimises blast radius to the existing flat boundary form |
| 12 | Harden the grant so the tool's source is actually agent-unreachable | Add `"src/gleipnir/preflight/**": deny` to `gleipnir-code.md`'s `permission.edit` map (companion Tier-3 diff, Appendix D); operator applies it with the rest in build mode | Leave the false "no roster grant covers it" premise; rely on convention only | `gleipnir-code`'s `edit:"*":allow` reaches `src/gleipnir/preflight/` (verified `gleipnir-code.md:11-16`); without the deny the plan's unreachability premise is false. Operator-converged (this spec-review delegation, Fix 1) |

---

## Architect

**Problem (one sentence).** The signed G-5 pipeline bridge
(`.gleipnir/var/run/pipeline-state.json`) has no in-framework recovery path when
it goes stale/corrupt/stuck, so an armed run fail-closes forever until the
operator deletes the file out of band (L-C19) — this plan gives the operator one
audited, out-of-framework command to *diagnose* and, deliberately, *clear* it,
without reintroducing the fail-open the design forbids.

**User.** The **operator** (owning uid), out-of-framework, before/around an
opencode session. Never a roster agent.

**Measurable success criteria.**
1. `bin/gleipnir-preflight bridge-status` prints one of exactly four
   classifications — **healthy / stale / corrupt-or-tampered / absent** — plus
   `minted_at`, age (seconds + human), and the **exact next command** to run;
   exits `0`; writes nothing; never raises on any bridge content.
2. `bin/gleipnir-preflight bridge-reset` **refuses** (exit 1, writes nothing)
   without `--confirm-clear`.
3. With `--confirm-clear`, it **deletes** the bridge (never re-mints), and
   appends one provenance-bearing line to `.gleipnir/logs/bridge-recovery.log`
   recording old-state / minted_at / action / timestamp.
4. `bridge-reset` **refuses** when `GLEIPNIR_OPERATOR_UID` is set and does not
   match the current uid; when it is **unset**, it prints an honest limitation
   warning and (with `--confirm-clear`) proceeds.
5. A test **and** a CLI-startup guard fail/refuse if the literal
   `gleipnir-preflight` appears in any `.gleipnir/agents/*.md`.
6. `src/gleipnir/preflight/` remains stdlib-only and never imports `hmac` /
   redefines `load_key`/`mint`/`validate` (existing conformance test stays
   green, extended to name the new submodule).

**Constraints (inherited from brief, non-negotiable).**
- **No silent reset.** Clearing is only ever a deliberate, `--confirm-clear`,
  operator-only act. Never auto-clear on staleness/corruption. (Constraint 1.)
- **No agent write over `.gleipnir/var/run/`.** The tool is operator-only,
  out-of-framework, in no allowlist. (Constraint 2.)
- **Honour the preflight precedent** (Constraint 3): subcommand on the *same*
  CLI, shared fail-closed exit convention, thin shim + logic under
  `src/gleipnir/preflight/`.
- **Honest status** (Constraint 4): cooperative-policy-until-S-2; label it.
- **stdlib-only** (`decisions/runtime-and-deps.md`): delegate all keyed logic to
  `gleipnir.engine.bridge` / `gleipnir.verify.marker`.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | State | Writer |
|---|---|---|---|
| Bridge file (read/deleted, never minted here) | `.gleipnir/var/run/pipeline-state.json` | exists at runtime | Driver (unchanged) |
| New recovery logic module | `src/gleipnir/preflight/bridge_recovery.py` | **to be created** | operator |
| Dispatch wiring | `src/gleipnir/preflight/__main__.py` | **to be edited** | operator |
| Never-in-allowlist startup guard | `src/gleipnir/preflight/bridge_recovery.py` (shared helper) | **to be created** | operator |
| Audit log | `.gleipnir/logs/bridge-recovery.log` | created on first reset | CLI (owning uid) |
| Tests | `tests/test_bridge_recovery.py` | **to be created** | operator *or* `gleipnir-code` (see Execution Workflow) |
| stdlib-only conformance | `tests/test_preflight_stdlib_only.py` | **to be edited** (grow submodule set) | operator *or* `gleipnir-code` |
| Durable decision record | `.gleipnir/decisions/bridge-recovery-path.md` | **to be created** | operator only (Tier-3) |
| Thin shim | `bin/gleipnir-preflight` | **unchanged** (`exec ... "$@"` already forwards new tokens) | — |

### Existing code the plan binds to (verified this session)

- `src/gleipnir/engine/bridge.py`: `StateMarker` (frozen dataclass;
  `.from_json(text)` raises `StateMarkerError` on bad JSON/shape),
  `validate_state(marker, key, max_age_seconds=DEFAULT_MAX_AGE_SECONDS, now=None)`
  → `bool` (checks version, MAC in constant time, then freshness),
  `DEFAULT_MAX_AGE_SECONDS` (= 3600, re-exported from `verify.marker`),
  `load_key(key_file=None)` → `bytes` (raises `KeyUnavailable`),
  `StateMarkerError`, `KeyUnavailable`.
- `src/gleipnir/preflight/__main__.py`: `main(argv)` dispatches on
  `resolved_argv[0] == "config-scan"` then falls through to the flat boundary
  parser. Exit convention `0`/`2`/`1`. `_repo_root()` = `parents[3]`.
- `.gleipnir/plugins/sequence-gate.ts`: `BRIDGE_REL = ".gleipnir/var/run/pipeline-state.json"`,
  `DEFAULT_MAX_AGE_SECONDS = 3600`, `ARM_ENV = "GLEIPNIR_PIPELINE"` — the exact
  path/window/arm-env the recovery tool must mirror.
- `tests/test_preflight_stdlib_only.py`: asserts `import hmac` absent and no
  `def load_key(`/`def mint(`/`def validate(` in the package, **and**
  `{"__init__","boundary","__main__"} <= names` (a `<=` subset check, so adding
  `bridge_recovery` does not break it, but the assertion should be updated to
  name it deliberately).

### The classification logic (exact)

Given the read of `.gleipnir/var/run/pipeline-state.json` and the key:

```
absent              := file does not exist / OSError on read
corrupt-or-tampered := StateMarker.from_json raises StateMarkerError
                       OR validate_state(marker, key, max_age_seconds=<huge>) is False
                          (i.e. MAC/version fail independent of age)
stale               := MAC valid (validate at max_age=huge is True)
                       AND validate_state(marker, key) is False   (real 3600 window)
                       AND age > DEFAULT_MAX_AGE_SECONDS
healthy             := validate_state(marker, key) is True         (MAC valid AND fresh)
```

Rationale for the double-call split (Decision 4): `validate_state` collapses
MAC-failure and age-failure into one `False`. To distinguish **stale** (MAC
valid, too old) from **corrupt-or-tampered** (MAC invalid), call it twice — once
with the real window (`healthy?`), once with an effectively infinite window
(`max_age_seconds=10**12`) to isolate whether the MAC/version alone passes. If
the infinite-window call is `True` but the real-window call is `False`, the only
remaining failure is freshness → **stale**. If the infinite-window call is
`False`, the MAC or version failed → **corrupt-or-tampered**. Age is computed as
`now - marker.minted_at` for display; a *negative* age (future-dated
`minted_at`) fails the real-window call (`age < 0`) but passes the infinite call
only if `age >= 0` — a negative age therefore classifies as **corrupt-or-tampered**
(the infinite-window call still enforces `age < 0 → False`), which is the
correct fail-closed verdict for a nonsense timestamp. State this explicitly in
the module docstring.

### Integrations map

- **Key loading:** `load_key(key_file=None)` reads `GLEIPNIR_MARKER_KEY_FILE`
  (same env var the driver and TS gate use). If the key is unavailable,
  `bridge-status` **cannot** distinguish stale from tampered (both need the
  MAC). Handle fail-closed: on `KeyUnavailable`, `bridge-status` reports
  **corrupt-or-tampered (key unavailable — cannot verify MAC)** and recommends
  the operator ensure the key is present; it never claims "healthy" without a
  verified MAC. `bridge-reset --confirm-clear` does **not** require the key
  (clearing a file needs no MAC) — but it logs whatever old state it *could*
  read (best-effort `from_json`, or "unreadable").
- **Exit codes:** `bridge-status` → `0` in the normal read-only case (the
  classification is in the output, not the exit code — mirrors "safe to run
  anytime"), **with one exception: exit `1` when the never-in-allowlist
  self-check guard fires** (`gleipnir-preflight` found in an agent file), since
  the tool disables itself if it detects it has been made agent-invocable —
  consistent with edge case 7 / stress-test item 21 / the Appendix A code.
  `bridge-reset` → `0` on successful clear, `1` on any refusal (missing flag,
  uid mismatch, allowlist-guard fire; nothing to clear is still `0` with an
  "already absent" message). Reserve `2` (unused).
- **Config root:** default `_repo_root() / ".gleipnir"`; bridge path
  `config_root / "var" / "run" / "pipeline-state.json"`; log path
  `config_root / "logs" / "bridge-recovery.log"`; agents dir
  `config_root / "agents"`. Accept an injectable `config_root` (for tests),
  mirroring `config_scan_main`.

### Edge cases

1. **No bridge file (absent).** `bridge-status` → healthy path is impossible;
   report **absent**, next command = "nothing to recover; start a run normally".
   `bridge-reset --confirm-clear` → "already absent; nothing to clear", exit `0`,
   log a `no-op` line (auditable that the operator ran it).
2. **Malformed JSON / wrong shape.** `from_json` raises `StateMarkerError` →
   **corrupt-or-tampered**. `bridge-reset` still clears it (that is the recovery
   for a corrupt file), logging old-state = "unparseable".
3. **Key unavailable.** As above — `bridge-status` cannot certify healthy;
   fail-closed to corrupt-or-tampered-with-key-note. `bridge-reset` still works.
4. **Future-dated `minted_at` (negative age).** → corrupt-or-tampered (see
   classification note).
5. **`GLEIPNIR_OPERATOR_UID` unset.** `bridge-reset` cannot enforce uid; prints
   the honest limitation and proceeds under `--confirm-clear`. **Not** a silent
   pass — the warning is on stderr and logged.
6. **`GLEIPNIR_OPERATOR_UID` set but not an int / not matching.** Non-int →
   refuse (exit 1, "misconfigured operator uid"). Mismatch → refuse (exit 1,
   "refusing under non-operator uid").
7. **`gleipnir-preflight` present in an agent file.** Startup guard in *both*
   subcommands → refuse (exit 1) with the pre-mortem-#1 message, before doing
   any status/reset work. (A deny that fails safe: the tool disables itself if
   it detects it has been made agent-invocable.)
8. **Logs dir missing.** `bridge-reset` creates `.gleipnir/logs/` if absent
   (`mkdir(parents=True, exist_ok=True)`) before appending — same pattern as
   `write_bridge`'s parent-mkdir.
9. **`GLEIPNIR_PIPELINE=on` in the current env** (brief pre-mortem #2 tail): a
   *nice-to-have* extra guard — warn that a run appears armed. Implement as a
   stderr warning only (not a hard refuse), since the operator clearing a stuck
   armed run is the whole point. Documented as advisory.

---

## Link (validated before building)

- ✅ Bridge path, arm env, and freshness window confirmed identical across
  `bridge.py`, `sequence-gate.ts` (`.gleipnir/var/run/pipeline-state.json`,
  `GLEIPNIR_PIPELINE`, `3600`).
- ✅ `StateMarker.from_json` / `validate_state` / `load_key` / `KeyUnavailable`
  / `StateMarkerError` / `DEFAULT_MAX_AGE_SECONDS` all importable from
  `gleipnir.engine.bridge` (verified signatures).
- ✅ `config-scan` dispatch pattern in `__main__.main()` confirmed (leading
  positional token branch that returns before the flat parser).
- ✅ `bin/gleipnir-preflight` shim `exec ... "$@"` forwards any new tokens with
  **no shim change** required.
- ✅ No `.gleipnir/agents/*.md` references `preflight` today (`grep` → zero) —
  the never-in-allowlist invariant currently holds.
- ✅ stdlib-only conformance test forbids `import hmac` and marker-fn
  redefinition, and uses a `<=` subset check for submodule names (adding a
  module is safe; will name it deliberately).
- ✅ `.gleipnir/logs/` is Tier-1 (framework-process writer), currently contains
  only `README.md`; no roster grant covers it → the operator-run CLI is a
  legitimate writer, agents are not. Log filename `bridge-recovery.log` is new.
- ℹ️ **Audit-log field-set differs from the G-4 bus convention, intentionally.**
  `logs/README.md` describes entries as carrying session id / originating turn /
  guard-surface identity / timestamp (per G-4a/G-4b). This CLI's audit line
  carries timestamp / action / old_state / minted_at / uid / surface but **no
  session id or originating turn** — because it is an *out-of-framework operator
  CLI invocation with no session/turn context* (there is no opencode session or
  turn to attribute it to). This is an intentional field-set difference, **not a
  defect**: a future G-4 bus consumer should treat the absent session/turn
  fields as "N/A — operator CLI provenance", not as a missing-data bug.
- ⚠️ **Open (not blocking):** No reliable in-process "am I an agent" signal
  exists → the uid refusal is opt-in via `GLEIPNIR_OPERATOR_UID` with an honest
  limitation note (Decision 5). This is a *known* cooperative-policy gap that S-2
  closes structurally; the plan does not pretend otherwise.

---

## Assemble (intended build order)

Test-first. Order chosen so each step is independently checkable and the
security-critical guards come before conveniences.

1. **Write tests** (`tests/test_bridge_recovery.py`) — full behaviour spec
   below; these define correctness (Axiom 1). Test-first: they fail until
   step 2/3 land.
2. **Create `src/gleipnir/preflight/bridge_recovery.py`** — the pure logic:
   - `Classification` enum: `HEALTHY / STALE / CORRUPT_OR_TAMPERED / ABSENT`.
   - `classify_bridge(text_or_none, key_or_none, *, now=None) -> (Classification, marker_or_None, age_or_None)`
     — pure, never raises, implements the double-call split (Decision 4).
   - `next_command(classification) -> str` — the exact next command string.
   - `preflight_is_agent_invocable(agents_dir: Path) -> str | None` — returns
     the offending filename if the literal `gleipnir-preflight` appears in any
     `*.md`, else `None` (the pre-mortem-#1 guard; pure, read-only).
   - `bridge_status_main(argv, *, config_root=None) -> int` — reads file+key
     (thin edge, `OSError`/`KeyUnavailable` caught), classifies, prints, exit 0.
   - `bridge_reset_main(argv, *, config_root=None) -> int` — argparse with
     `--confirm-clear`; runs the allowlist guard, the uid check, the
     confirm-flag check; on pass deletes the file and appends the audit line.
   - `_append_audit_line(log_path, old_state, minted_at, action)` — one JSON
     line with provenance (timestamp, action, old_state, minted_at, uid).
3. **Wire dispatch** into `src/gleipnir/preflight/__main__.py` — add two token
   branches *before* the flat parser, mirroring `config-scan` exactly:
   ```python
   if resolved_argv and resolved_argv[0] == "bridge-status":
       return bridge_recovery.bridge_status_main(list(resolved_argv[1:]))
   if resolved_argv and resolved_argv[0] == "bridge-reset":
       return bridge_recovery.bridge_reset_main(list(resolved_argv[1:]))
   ```
   (with `from . import bridge_recovery` at the import block).
4. **Extend `tests/test_preflight_stdlib_only.py`** — add `bridge_recovery` to
   the deliberately-named submodule set; the stdlib/no-hmac/no-marker-redef
   assertions already cover the new file automatically (they glob `*.py`).
5. **Author the durable decision record**
   `.gleipnir/decisions/bridge-recovery-path.md` (operator, Tier-3) — records
   the L-C19 gap, the converged decision, the no-silent-reset invariant, the
   pre-mortem mitigations (#1 self-check, #4 clear-not-re-mint), and the honest
   cooperative-policy-until-S-2 status.
6. **Run the suite** (operator/build-mode) — `pytest tests/test_bridge_recovery.py
   tests/test_preflight_stdlib_only.py` green; full suite unregressed.

---

## Stress-test (acceptance checks)

Concrete, checkable — each maps to a test in `tests/test_bridge_recovery.py`:

**Classification (pure, no I/O — via `classify_bridge`):**
1. Freshly minted marker (age 0, valid MAC) → `HEALTHY`.
2. Valid MAC, `minted_at` = now − 4000s (> 3600) → `STALE`.
3. Valid MAC, `minted_at` = now − 3599s → `HEALTHY` (boundary just inside).
4. Valid MAC, `minted_at` = now − 3601s → `STALE` (boundary just outside).
5. One-byte-tampered `mac` → `CORRUPT_OR_TAMPERED`.
6. Tampered `pipeline_state` (MAC no longer matches) → `CORRUPT_OR_TAMPERED`.
7. Wrong `version` → `CORRUPT_OR_TAMPERED`.
8. Malformed JSON / missing field → `CORRUPT_OR_TAMPERED` (via
   `StateMarkerError`, never raises out).
9. Future-dated `minted_at` (negative age) → `CORRUPT_OR_TAMPERED`.
10. `text_or_none is None` (absent) → `ABSENT`.
11. Key unavailable (`key_or_none is None`) with a real marker → classified
    `CORRUPT_OR_TAMPERED` and the status output notes "key unavailable — cannot
    verify MAC" (never `HEALTHY`).

**`bridge-status` CLI (`bridge_status_main`, injected `config_root`):**
12. Each classification prints its label + `minted_at` + age + the correct
    next command; exit `0`; the bridge file is unchanged on disk after the run.

**`bridge-reset` CLI (`bridge_reset_main`, injected `config_root`):**
13. Without `--confirm-clear` → exit `1`, file **still present**, nothing
    logged.
14. With `--confirm-clear`, healthy/stale/corrupt file present → file
    **deleted**, exit `0`, exactly one new line appended to
    `.gleipnir/logs/bridge-recovery.log` containing action=`cleared`,
    old_state, minted_at, an ISO/epoch timestamp, and the uid.
15. With `--confirm-clear`, file absent → exit `0`, message "already absent",
    one `no-op` audit line appended (auditable).
16. `GLEIPNIR_OPERATOR_UID` set to a **non-matching** int → exit `1`, file
    present, nothing cleared.
17. `GLEIPNIR_OPERATOR_UID` set to the **matching** uid → clear proceeds.
18. `GLEIPNIR_OPERATOR_UID` **unset** → stderr carries the honest limitation
    warning; with `--confirm-clear` the clear still proceeds (Decision 5).
19. `GLEIPNIR_OPERATOR_UID` set to a non-int → exit `1` ("misconfigured").

**Never-in-allowlist guard (pre-mortem #1):**
20. `preflight_is_agent_invocable` returns the filename when a fixture agent
    file under an injected `agents/` dir contains `gleipnir-preflight`; returns
    `None` for the real (clean) roster.
21. Both `bridge_status_main` and `bridge_reset_main` **refuse (exit 1)** when
    the guard fires, before any status/reset work.

**Conformance / hygiene:**
22. `tests/test_preflight_stdlib_only.py` stays green with `bridge_recovery.py`
    present (no `hmac` import; no `load_key`/`mint`/`validate` redefinition;
    stdlib-only).

---

## Execution Workflow

### For the operator applying this (build mode)

1. Read this plan and the brief. Confirm you accept the Decisions (index),
   especially #2 (clear-only), #5 (uid limitation), #8 (never-in-allowlist).
2. Apply in Assemble order 1→6. The exact code for step 2 and the exact diff
   for step 3 are in **Appendix A / B** below — apply them verbatim (adjust only
   if a later refactor moved a symbol).
3. Run `pytest tests/test_bridge_recovery.py tests/test_preflight_stdlib_only.py`
   then the full suite. All green before considering it done.
4. Author `.gleipnir/decisions/bridge-recovery-path.md` (step 5) — this is the
   durable Tier-3 record; do not skip it (the plan named it; the decision must
   persist beyond this disposable plan).
5. Manually smoke-test out-of-framework:
   `bin/gleipnir-preflight bridge-status` against a real/stale/absent bridge,
   then `bin/gleipnir-preflight bridge-reset` (expect refuse) and
   `... bridge-reset --confirm-clear` (expect clear + log line).

### Who may apply what — the Tier-3 boundary (explicit answer to the delegation)

| Artifact | Can `gleipnir-code` / `git-ops` do it **now**? | Verdict |
|---|---|---|
| `src/gleipnir/preflight/bridge_recovery.py` (new) | **Not currently blocked** — `gleipnir-code`'s `edit:"*":allow` reaches `src/gleipnir/preflight/` (only `.gleipnir/**`/`.git/**` are denied). This is a **gap** the plan closes: Decision 12 / Appendix D add `"src/gleipnir/preflight/**": deny` to `gleipnir-code.md`. After that hardening lands, no agent can write it. This is also the enforcement/recovery tool itself — putting an agent on it is pre-mortem #1. | **Operator only** (once Appendix D applied) |
| Edit `src/gleipnir/preflight/__main__.py` | **Not currently blocked** — same package, same `edit:"*":allow` reach; same Appendix D `"src/gleipnir/preflight/**": deny` closes it. | **Operator only** (once Appendix D applied) |
| `.gleipnir/logs/bridge-recovery.log` write path (runtime) | **No** — Tier-1, agents deny all `.gleipnir/**` writes outside their own `plans/**`; the CLI writes as the owning uid. | **Operator/CLI only** |
| `.gleipnir/decisions/bridge-recovery-path.md` | **No** — Tier-3, operator-only by every grant. | **Operator only** |
| `bin/gleipnir-preflight` | No change needed; and it is agent-unreachable by design. | **N/A (unchanged)** |
| `tests/test_bridge_recovery.py` (new) | **Yes, potentially.** `tests/` is not under `.gleipnir/**`; `gleipnir-code` in a normal (non-`.gleipnir`) build could author it. **But** the tests import `gleipnir.preflight.bridge_recovery`, which does not exist until the operator applies step 2 — so they'd be red until then. | **Possible follow-up split** |
| Edit `tests/test_preflight_stdlib_only.py` | **Yes, potentially** — same `tests/` reasoning. | **Possible follow-up split** |

**Recommended split (surfaced, operator's call — do not treat as decided):** the
two **test files** could be delegated to `gleipnir-code` as a *separate*
test-authoring slice (they live under `tests/`, outside the Tier-3 fence), while
the operator applies the `src/` code, the `__main__` wiring, the decision
record, and validates. The catch: the tests are red until the operator's `src/`
code lands, so either (a) `gleipnir-code` writes them test-first and the operator
applies `src/` immediately after in the same session, or (b) the operator does
the whole thing to keep it atomic. **This staging choice is a coordination
tradeoff, not a material design decision — flagging it, not resolving it.**

### Honest status label

Cooperative-policy-until-S-2. The operator-only / out-of-framework property of
the *shim invocation* is honoured by today's roster grants (`bin/gleipnir-preflight`
is in no allowlist). **But the tool's source is not yet protected:**
`src/gleipnir/preflight/` is NOT currently covered by the `.gleipnir/` tier
model — `gleipnir-code`'s `edit:"*":allow` grant reaches it. This plan includes
a companion permission-hardening diff (Decision 12 / Appendix D: add
`"src/gleipnir/preflight/**": deny` to `gleipnir-code.md`) to close that gap,
and the operator applies both together in build mode. Even after that, the whole
posture becomes *structural* (rather than cooperative-policy) only when the S-2
boundary + terminal closure land. The uid refusal (Decision 5) is likewise
cooperative until then.

---

## Appendix A — exact code for `src/gleipnir/preflight/bridge_recovery.py`

> Reference implementation for the operator to apply. Stdlib-only; delegates all
> keyed logic to `gleipnir.engine.bridge`. No `import hmac`; no redefinition of
> `load_key`/`mint`/`validate`.

```python
"""Operator-only bridge recovery for a stuck/stale G-5 pipeline bridge (L-C19).

OUT-OF-FRAMEWORK: run by the OPERATOR via `bin/gleipnir-preflight bridge-status`
/ `bridge-reset`, never by an in-framework agent. This module is deliberately
NOT referenced by any `.gleipnir/agents/*.md` permission map -- and both
subcommands REFUSE if they detect they have been made agent-invocable
(pre-mortem #1, brief `.gleipnir/plans/bridge-recovery-brainstorm.md`).

Clear-only (Decision 2): `bridge-reset` DELETES the bridge; it never re-mints a
state (re-minting a permissive state is the fail-open the driver docstring
forbids). Classification distinguishes stale (valid MAC, too old) from
corrupt-or-tampered (MAC/version invalid, unparseable, or future-dated) by
calling `validate_state` twice -- once at the real 3600s window, once at an
effectively-infinite window -- since `validate_state` alone collapses MAC- and
age-failures into one False.

Honest status: cooperative-policy-until-S-2. The uid refusal is opt-in via
GLEIPNIR_OPERATOR_UID; no reliable in-process "am I an agent" signal exists in
this codebase, so when the env var is unset the tool WARNS rather than
fabricating a check.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from enum import Enum
from pathlib import Path

from gleipnir.engine.bridge import (
    DEFAULT_MAX_AGE_SECONDS,
    KeyUnavailable,
    StateMarker,
    StateMarkerError,
    load_key,
)

BRIDGE_REL = Path("var") / "run" / "pipeline-state.json"
LOG_REL = Path("logs") / "bridge-recovery.log"
AGENTS_REL = Path("agents")
OPERATOR_UID_ENV = "GLEIPNIR_OPERATOR_UID"
ARM_ENV = "GLEIPNIR_PIPELINE"
PREFLIGHT_TOKEN = "gleipnir-preflight"
_EFFECTIVELY_INFINITE_AGE = 10 ** 12


class Classification(Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    CORRUPT_OR_TAMPERED = "corrupt-or-tampered"
    ABSENT = "absent"


def _repo_root() -> Path:
    # src/gleipnir/preflight/bridge_recovery.py -> repo root is three parents up
    # (same depth as __main__._repo_root()).
    return Path(__file__).resolve().parents[3]


def _default_config_root() -> Path:
    return _repo_root() / ".gleipnir"


def classify_bridge(
    text: str | None,
    key: bytes | None,
    *,
    now: int | None = None,
) -> tuple[Classification, StateMarker | None, int | None]:
    """Pure classifier. Never raises. Returns (classification, marker, age).

    * text is None            -> ABSENT
    * unparseable             -> CORRUPT_OR_TAMPERED
    * key is None             -> CORRUPT_OR_TAMPERED (cannot verify MAC)
    * MAC/version invalid, or
      future-dated (age < 0)  -> CORRUPT_OR_TAMPERED
    * MAC valid, age > 3600   -> STALE
    * MAC valid, fresh        -> HEALTHY
    """
    if text is None:
        return (Classification.ABSENT, None, None)
    try:
        marker = StateMarker.from_json(text)
    except StateMarkerError:
        return (Classification.CORRUPT_OR_TAMPERED, None, None)

    current = int(now if now is not None else time.time())
    age = current - marker.minted_at

    if key is None:
        return (Classification.CORRUPT_OR_TAMPERED, marker, age)

    # Import here is unnecessary; validate_state is delegated to below.
    from gleipnir.engine.bridge import validate_state

    mac_ok_any_age = validate_state(
        marker, key, max_age_seconds=_EFFECTIVELY_INFINITE_AGE, now=current
    )
    if not mac_ok_any_age:
        # MAC/version invalid, OR age < 0 (future-dated). Both fail-closed.
        return (Classification.CORRUPT_OR_TAMPERED, marker, age)

    fresh = validate_state(marker, key, now=current)  # real 3600 window
    if fresh:
        return (Classification.HEALTHY, marker, age)
    return (Classification.STALE, marker, age)


def next_command(classification: Classification) -> str:
    if classification is Classification.HEALTHY:
        return "(bridge is healthy; no recovery needed)"
    if classification is Classification.ABSENT:
        return "(no bridge present; start a run normally -- nothing to recover)"
    # STALE or CORRUPT_OR_TAMPERED
    return "bin/gleipnir-preflight bridge-reset --confirm-clear"


def preflight_is_agent_invocable(agents_dir: Path) -> str | None:
    """Return the offending agent filename if the literal `gleipnir-preflight`
    appears in ANY `.gleipnir/agents/*.md`, else None. Read-only; pre-mortem
    #1 guard. Never raises (a missing/unreadable dir -> None means 'no evidence
    it is agent-invocable' -- but see note: an unreadable agents dir is itself
    reported so the operator is not lulled)."""
    try:
        paths = sorted(agents_dir.glob("*.md"))
    except OSError:
        return None
    for path in paths:
        try:
            if PREFLIGHT_TOKEN in path.read_text():
                return path.name
        except OSError:
            continue
    return None


def _human_age(age: int | None) -> str:
    if age is None:
        return "n/a"
    if age < 0:
        return f"{age}s (FUTURE-DATED -- nonsense timestamp)"
    if age < 3600:
        return f"{age}s"
    return f"{age}s (~{age // 3600}h {(age % 3600) // 60}m)"


def _read_bridge_text(bridge_path: Path) -> str | None:
    try:
        return bridge_path.read_text()
    except OSError:
        return None


def _try_load_key() -> bytes | None:
    try:
        return load_key()
    except KeyUnavailable:
        return None


def _allowlist_guard(agents_dir: Path) -> int | None:
    offender = preflight_is_agent_invocable(agents_dir)
    if offender is not None:
        print(
            "bridge-recovery: REFUSING -- 'gleipnir-preflight' appears in "
            f"agent file {offender!r}. This tool must NEVER be agent-invocable "
            "(a guard whose activation is validated by the population it "
            "guards is defeated). Remove it from the allowlist first.",
            file=sys.stderr,
        )
        return 1
    return None


def bridge_status_main(argv: list[str] | None = None, *, config_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gleipnir-preflight bridge-status")
    parser.add_argument("--config-root", default=None)
    args = parser.parse_args(argv if argv is not None else [])

    root = Path(args.config_root) if args.config_root else (config_root or _default_config_root())

    guard = _allowlist_guard(root / AGENTS_REL)
    if guard is not None:
        return guard

    bridge_path = root / BRIDGE_REL
    text = _read_bridge_text(bridge_path)
    key = _try_load_key()
    classification, marker, age = classify_bridge(text, key)

    print(f"bridge-status: {classification.value}", file=sys.stderr)
    if marker is not None:
        print(f"  pipeline_state : {marker.pipeline_state}", file=sys.stderr)
        print(f"  minted_at      : {marker.minted_at}", file=sys.stderr)
        print(f"  age            : {_human_age(age)}", file=sys.stderr)
    if key is None and classification is Classification.CORRUPT_OR_TAMPERED and marker is not None:
        print("  note           : key unavailable -- MAC could NOT be verified; "
              "reporting fail-closed (cannot certify healthy)", file=sys.stderr)
    if os.environ.get(ARM_ENV, "").strip().lower() == "on":
        print(f"  warning        : {ARM_ENV}=on -- a gated run appears armed in "
              "this environment", file=sys.stderr)
    print(f"  next command   : {next_command(classification)}", file=sys.stderr)
    return 0  # read-only, always safe


def _append_audit_line(log_path: Path, *, action: str, old_state: str | None, minted_at: int | None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": int(time.time()),
        "action": action,
        "old_state": old_state,
        "minted_at": minted_at,
        "uid": os.getuid(),
        "surface": "bridge-reset",
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _uid_check() -> int | None:
    """Returns an exit code to abort with, or None to proceed. Decision 5:
    opt-in via GLEIPNIR_OPERATOR_UID; unset -> warn honestly and proceed."""
    raw = os.environ.get(OPERATOR_UID_ENV)
    if raw is None or raw.strip() == "":
        print(
            "bridge-reset: WARNING -- GLEIPNIR_OPERATOR_UID is not set, so this "
            "tool CANNOT verify it is running as the operator (no reliable "
            "in-process agent signal exists pre-S-2). Proceeding on your "
            "explicit --confirm-clear. Set GLEIPNIR_OPERATOR_UID to enforce.",
            file=sys.stderr,
        )
        return None
    try:
        expected = int(raw)
    except ValueError:
        print(f"bridge-reset: REFUSING -- {OPERATOR_UID_ENV}={raw!r} is not an "
              "integer uid (misconfigured).", file=sys.stderr)
        return 1
    if os.getuid() != expected:
        print(f"bridge-reset: REFUSING -- current uid {os.getuid()} != operator "
              f"uid {expected}; will not clear the bridge under a non-operator uid.",
              file=sys.stderr)
        return 1
    return None


def bridge_reset_main(argv: list[str] | None = None, *, config_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gleipnir-preflight bridge-reset")
    parser.add_argument("--config-root", default=None)
    parser.add_argument(
        "--confirm-clear",
        action="store_true",
        help="REQUIRED to actually delete the bridge; no default-yes.",
    )
    args = parser.parse_args(argv if argv is not None else [])

    root = Path(args.config_root) if args.config_root else (config_root or _default_config_root())

    guard = _allowlist_guard(root / AGENTS_REL)
    if guard is not None:
        return guard

    bridge_path = root / BRIDGE_REL
    log_path = root / LOG_REL

    # Best-effort read of the old state for the audit log (before any deletion).
    text = _read_bridge_text(bridge_path)
    old_state: str | None
    old_minted_at: int | None
    if text is None:
        old_state, old_minted_at = None, None
    else:
        try:
            m = StateMarker.from_json(text)
            old_state, old_minted_at = m.pipeline_state, m.minted_at
        except StateMarkerError:
            old_state, old_minted_at = "unparseable", None

    # Show what would be cleared, then require the flag (Decision 6).
    if not args.confirm_clear:
        print("bridge-reset: REFUSING -- --confirm-clear not given. Would clear:",
              file=sys.stderr)
        print(f"  old_state : {old_state}", file=sys.stderr)
        print(f"  minted_at : {old_minted_at}", file=sys.stderr)
        print("  Re-run with --confirm-clear to delete the bridge (clear-only; "
              "never re-mints a state).", file=sys.stderr)
        return 1

    uid_abort = _uid_check()
    if uid_abort is not None:
        return uid_abort

    if os.environ.get(ARM_ENV, "").strip().lower() == "on":
        print(f"bridge-reset: WARNING -- {ARM_ENV}=on; clearing a bridge for an "
              "armed run. This is intended for a stuck run; proceeding.",
              file=sys.stderr)

    if text is None:
        print("bridge-reset: bridge already absent; nothing to clear.", file=sys.stderr)
        _append_audit_line(log_path, action="no-op", old_state=None, minted_at=None)
        return 0

    try:
        bridge_path.unlink()
    except OSError as exc:
        print(f"bridge-reset: FAILED to delete bridge at {bridge_path}: {exc}",
              file=sys.stderr)
        return 1

    _append_audit_line(log_path, action="cleared", old_state=old_state, minted_at=old_minted_at)
    print(f"bridge-reset: cleared bridge (old_state={old_state}, "
          f"minted_at={old_minted_at}). Logged to {log_path}.", file=sys.stderr)
    return 0
```

> Note on the inner `from gleipnir.engine.bridge import validate_state`: fold it
> into the top-level import block on apply (it is written inline above only to
> keep the classifier's dependency obvious); the stdlib-only test does not object
> to importing `validate_state` (it is not `hmac`, `load_key`, `mint`, or a
> local redefinition).

## Appendix B — exact diff for `src/gleipnir/preflight/__main__.py`

```diff
 from . import config_scan
+from . import bridge_recovery
 from .boundary import Verdict, run_preflight
```

and inside `main()`, immediately after `resolved_argv = ...` and before the
existing `if resolved_argv and resolved_argv[0] == "config-scan":` branch (or
directly after it — order among sibling token branches is irrelevant):

```diff
     resolved_argv = sys.argv[1:] if argv is None else argv

+    if resolved_argv and resolved_argv[0] == "bridge-status":
+        return bridge_recovery.bridge_status_main(list(resolved_argv[1:]))
+
+    if resolved_argv and resolved_argv[0] == "bridge-reset":
+        return bridge_recovery.bridge_reset_main(list(resolved_argv[1:]))
+
     if resolved_argv and resolved_argv[0] == "config-scan":
```

## Appendix C — `tests/test_preflight_stdlib_only.py` edit

```diff
     def test_only_the_expected_preflight_submodules_exist(self):
         names = {p.stem for p in _preflight_py_files()}
-        assert {"__init__", "boundary", "__main__"} <= names
+        assert {"__init__", "boundary", "__main__", "bridge_recovery"} <= names
```

(The `no_non_stdlib_top_level_imports`, `never_reimplements_hmac`, and
`no_os_access` tests already glob `*.py`, so they cover `bridge_recovery.py`
with no change.)

## Appendix D — companion permission-hardening diff for `.gleipnir/agents/gleipnir-code.md`

> **Tier-3, operator-only.** `.gleipnir/agents/*.md` is operator-authored and
> agent-unwritable; no roster agent (including this planner) may apply this. The
> operator applies it in the same build-mode session as the rest of this plan,
> **before or alongside** creating `bridge_recovery.py`, so the tool's source is
> unreachable by any agent from the moment it exists (Decision 12 / Fix 1).
>
> Without this, `gleipnir-code`'s `edit: "*": allow` (with only `.gleipnir/**`
> and `.git/**` denied) reaches `src/gleipnir/preflight/` — the recovery tool's
> own source — which is exactly pre-mortem #1 (the guarded population able to
> edit the guard). The added deny closes that.

```diff
 permission:
   edit:
     "*": allow
     ".gleipnir/**": deny
     ".git/**": deny
+    "src/gleipnir/preflight/**": deny
   read: allow
```

Note the ordering is immaterial to opencode's most-specific-match semantics; the
new, more-specific `"src/gleipnir/preflight/**"` deny overrides the `"*": allow`
for that subtree, exactly as the existing `.gleipnir/**`/`.git/**` denies do.
After applying, re-run the suite and, ideally, add a roster-conformance
assertion (future work, out of scope here) that `src/gleipnir/preflight/**` is
denied for every implementation-capable agent — mirroring the never-in-allowlist
self-check discipline (Decision 8) at the grant layer.
