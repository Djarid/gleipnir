# Plan: `request_approval` must fail loudly when the approval listener is dead

**Stage:** `plan` (ATLAS Architect/Trace/Link/Assemble/Stress-test).
**Scope class:** URGENT, BOUNDED bug fix. Split out of
`.gleipnir/plans/signer-uid-separation-brainstorm.md` by **operator direction**
(that brief's Decision 1 — "F-1 ... SPLIT OUT of this brief as its own
separately-planned bug fix ... an operator-directed split of work, *not* a
design choice among the brief's approaches", `:42-59`).

**Touched paths (`P`):**

- `src/gleipnir/approval/mcp_server.py` (EDIT — exists, 248 lines, verified)
- `tests/test_approval_mcp_server.py` (EDIT — exists, 518 lines, verified)

**Nothing else.** No `.gleipnir/**`, no `opencode.jsonc`, no `ansible/**`, no
`bin/**`, no `.gleipnir/plugins/**`, no `src/gleipnir/verify/**`, no
`src/gleipnir/approval/server.py`. See §Routing and §Scope discipline.

---

## Provenance — required reading actually read, and re-verified link by link

The delegation instructed me not to trust the brainstorm's F-1 claim. I read the
brief in full (995 lines) and then re-verified **every** cited line against the
real files. Result: **the F-1 chain is CORRECT as stated.** Verification table:

| # | Brief's claim | Cited site | Verified? | What I actually read |
|---|---|---|---|---|
| 1 | `gleipnir-launch` execs opencode as the agent uid | `bin/gleipnir-launch:37-43` | **YES** | `exec sudo -u "#${GLEIPNIR_AGENT_UID}" -g "#${GLEIPNIR_AGENT_GID}" /bin/sh -c '... exec opencode'` (`:37-44`; file is 44 lines) |
| 2a | ansible act-5 sets the key `0600`, owner operator | `ansible/site.yml:375-382` | **YES** | `act5: lock the G-3 key RO_AND_UNREADABLE (mode 600)` → `owner: "{{ operator }}"`, `mode: "0600"` |
| 2b | caged AC requires the agent uid **cannot** read it | `boundary.py:995-999` | **YES** | `if ep.posture is Posture.RO_AND_UNREADABLE:` → `read_result = read_probe(key_path, agent_uid, agent_gid)`; and `:345` `if posture is Posture.RO_AND_UNREADABLE and read_ok:` is the failure condition. Caged mode is *defined by* the read failing |
| 3 | `opencode.jsonc` spawns the signer as an opencode **child** | `opencode.jsonc:91-100` | **YES** | `"gleipnir-approval": { "type": "local", "command": [".venv/bin/python","-m","gleipnir.approval.mcp_server"], ... "enabled": true }` — a local MCP child, so it inherits opencode's uid |
| 4a | `mcp_server` → `run_server` → `load_key` | `mcp_server.py:206`, `server.py:398` | **YES** | `mcp_server.py:206` `run_server(key_file=key_file, token_dir=token_dir, **kwargs)`; `server.py:397-398` `register_default_resolvers()` then `key = load_key(key_file)` — **`load_key` runs BEFORE the socket bind** at `:402`. This ordering is load-bearing; see edge case E-4 |
| 4b | `load_key` raises `KeyUnavailable` on an unreadable file | `marker.py:100-103` | **YES** | `try: raw = Path(path).read_bytes()` / `except OSError as exc: raise KeyUnavailable(f"cannot read key at {path}: {exc}") from exc`. So an `EACCES` is **wrapped**, and does NOT surface as an `OSError` |
| 5 | broad `except Exception` → thread dies quietly | `mcp_server.py:207-212` | **YES** | `except Exception as exc:  # noqa: BLE001 -- Decision 19: log-and-continue` → a single `logger.warning(...)` then `return` |
| 6 | `request_approval` keeps returning URLs regardless | `mcp_server.py:159-178` | **YES** | The whole body is `change_hash = _stage_pending_content(...)` then `return _build_approval_url(change_hash)`. **No listener-health reference of any kind.** `_build_approval_url` (`:107-121`) only reads an env var and formats a string |
| 7 | Decision 19's rationale is port-conflict, not key-failure | `tier3-mcp-approval-launcher.md:82` | **YES, and this is the crux** | Decision 19's *stated* rationale is entirely about port conflict: "a second listener already running is the operator's own doing (e.g. a manual `bin/gleipnir-approval-server`), not a security regression". Its **implementation** (`except Exception`) is far broader than its rationale, and `edge case 1` (`:444-448`) was folded under the same catch. **The key-unavailable case was never argued on its own merits.** |
| 8 | An existing test asserts the buggy behaviour | `tests/test_approval_mcp_server.py:434-444` | **YES** | `TestT9FailClosedKeyDoesNotCrashTheProcess::test_request_approval_still_works_when_the_key_is_unavailable` asserts `"/approve/" in result` **after** a key-unavailable `_run_listener` call. This test is the codified form of the bug |

**One correction to the brief, in this plan's favour:** the brief (`:220`) says
the catch is at `mcp_server.py:207-212`; it is `207-212` inclusive of the
`logger.warning` call — accurate. No corrections needed. The chain stands.

**Additional facts I established that the brief does not state, and that shape
this plan** (each independently verified):

- **`KeyUnavailable` is NOT an `OSError`.** `marker.py:43-48`:
  `class MarkerError(Exception)` / `class KeyUnavailable(MarkerError)`. A
  port-bind conflict, by contrast, surfaces as `OSError` **with
  `errno == errno.EADDRINUSE`** out of
  `http.server.HTTPServer((host, port), ...)` at `server.py:402`. **The two
  failure modes Decision 19 conflates are disjoint by exception type.**
  Exception type alone is, however, **not a sufficient discriminator** —
  `HTTPServer` construction can raise `OSError` for reasons that are NOT a
  port conflict (`EACCES` on a privileged port, `EADDRNOTAVAIL` on a bad host,
  `EMFILE`/`ENFILE` under fd exhaustion) and none of those mean "another
  listener is already serving". The discriminator the fix actually uses is
  therefore **`isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE`**
  (spec-review round 1, Important defect 1 — see Decision 2). This needs
  **one new stdlib import, `errno`**, which is verified legal below.
- **`import errno` is legal — verified against every enforced constraint.**
  (i) T-11's `.server` closed allow-list constrains only
  `from .server import ...` names (`_dot_server_import_names`, `:79-91`), not
  the module's stdlib imports; (ii) `_all_identifiers` (`:94-110`) forbids
  exactly three names — `capture_approval`, `mint_approval`, `load_key`
  (`:54`) — and `errno`/`EADDRINUSE` are neither; (iii) T-4's import bans are
  an enumerated blacklist (`hmac`, `hashlib`, `http`, `webbrowser`,
  `:335-344`, `:262`), not a whitelist, so a fourth stdlib module is not
  caught; (iv) `tests/test_broker_stdlib_only.py` bans only `mcp` outside the
  carve-out (`:88-100`) and `errno` is stdlib, so the *stdlib-only enforcement
  core* rule (`decisions/runtime-and-deps.md`) is **satisfied, not strained** —
  it forbids third-party deps, and `errno` adds none. `pyproject.toml`
  `dependencies = []` (`:8`) is unchanged.
- **T-11 structurally FORBIDS the obvious alternative fix.**
  `tests/test_approval_mcp_server.py:474-518` is an **AST-based identifier
  scan** (`_all_identifiers`, `:94-110`: `ast.Name` ids, `ast.Attribute`
  attrs, and import names/aliases) that fails if `load_key`,
  `capture_approval` or `mint_approval` appear as an **identifier**
  (`_FORBIDDEN_MINT_KEY_SYMBOLS`, `:54`); it also asserts imports from
  `.server` are a subset of a five-name closed allow-list (`:44-50`).
  **Precisely scoped (spec-review round 1, minor correction):** it is *not* a
  literal source-text scan — prose mentions of these names in a docstring or
  comment (the module docstring already says `load_key` at `:37` and `:59` and
  is green today) do **not** trip it. Only an actual import, call, or
  attribute reference does. That is still enough: "have `request_approval`
  check whether the key is readable itself" requires a real `load_key`
  reference, so it is **illegal by an existing enforced test**. The wrapper can
  only learn about key-unavailability by *observing the exception the listener
  raised*. This is not a stylistic preference — it forces the design
  (Decision 1 below).
- **`tests/test_approval_mcp_server.py` is ALREADY wired into both gates.**
  `.gleipnir/sandbox/profiles.toml:60` lists it in `[profile.broker].test`
  (last entry, verified), and `tests/conftest.py:50` adds it to
  `collect_ignore` for the lean `python` profile. **Extending this file in place
  therefore requires ZERO Tier-3 edits.** A *new* test file would require an
  operator-only `profiles.toml` amendment (the precedent is explicit:
  `plans/broker-pm-coverage-gap.md` Decision 4, `plans/git-diff-distill.md`
  Decision 13). This decides the test-file question (Decision 7).
- **`gleipnir-code` can do all of this.** `edit: "*": allow` with denies on
  `.gleipnir/**`, `.git/**`, `.github/**`, `src/gleipnir/preflight/**`, `.env*`
  (`gleipnir-code.md:11-28`) — `src/gleipnir/approval/**` and `tests/**` are
  both allowed. `bash` allowlist includes
  `./bin/gleipnir-sandbox test --profile broker` (`:41,47`), the profile this
  test file runs under.
- **No other caller depends on the changed surface.** Grepped
  `request_approval|start_listener_thread` across all `*.py` (31 hits: only
  `mcp_server.py` itself and its test file) and across all `*.ts` (**zero**
  hits — no plugin calls it; `tier3-gate.ts` builds its own URL at `:435-445`
  and shells to `python -m gleipnir.approval.gate`, never to this MCP tool).
  The only production consumer is the MCP tool surface itself, held solely by
  `tier3-writer` (every other roster agent carries `"gleipnir-approval_*":
  false` — verified in 9 agent files).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| 1 | **`[PLAN-STAGE JUDGMENT]` The fix mechanism** (the delegation's a/b/c) | **(b) composed with (a), in that order** — `_run_listener` **classifies** the failure and records it in module-level listener state; `request_approval` **consults** that state and refuses loudly if it says the in-process listener is unavailable. Both halves are required: (b) alone changes nothing the caller can observe; (a) alone cannot tell a benign port conflict from a fatal key failure and would break Decision 19's legitimate case | (a) alone — a single "listener alive?" flag: would ALSO refuse on a benign port conflict, where the URL is genuinely serveable by the already-bound manual listener, destroying Decision 19's named behaviour. (c) "`request_approval` checks key readability itself" — **ILLEGAL**: T-11's AST identifier scan (`test_approval_mcp_server.py:474-484`, via `_all_identifiers` `:94-110`) fails the build if `load_key` appears as an identifier (import/call/attribute) in `mcp_server.py`. (c') "probe `127.0.0.1:8765` for liveness" — a real network probe from the tool path, a much larger change with new failure modes, deliberately out of scope | The port-conflict case is identifiable **exactly** (`OSError` with `errno == errno.EADDRINUSE`) while `KeyUnavailable(MarkerError)` is not an `OSError` at all, so classification is precise. T-11 makes the observe-the-exception shape the ONLY legal one. The underlying material tradeoff (fail loud vs fail silent on key-unavailable) is **already settled by the operator** — this is flagged an urgent bug, not a design question — so this row is implementation shape only. Flagged for spec-review |
| 2 | **`[PLAN-STAGE JUDGMENT]` Classification polarity: default-fatal, `EADDRINUSE`-ONLY benign carve-out** *(corrected — spec-review round 1, Important defect 1)* | **benign iff `isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE`** → `logger.warning`, state unchanged, `request_approval` keeps working (Decision 19 preserved for its *named* case). **Everything else fatal** — including an `OSError` whose `errno` is anything other than `EADDRINUSE`, and including `OSError` with `errno is None` → `logger.error` + state flips to unavailable + `request_approval` refuses | (i) **`except OSError` broadly → benign** — the shape this plan carried into spec-review round 1, now **REJECTED**; (ii) the inverse polarity — `except KeyUnavailable → fatal; except Exception → benign` | **Why the broad `except OSError` was wrong** (the round-1 defect, recorded rather than quietly replaced): `HTTPServer((host, port), ...)` at `server.py:402` raises `OSError` for several conditions that do **not** mean "another listener is already serving" — `EACCES` (privileged port / sandbox denial), `EADDRNOTAVAIL` (host not local), `EMFILE`/`ENFILE` (fd exhaustion). Under the broad form, every one of those was silently swallowed as benign and `request_approval` kept minting dead URLs — **recreating the exact silent-failure bug this plan exists to fix, merely with a different trigger.** Narrowing to the specific accepted condition is the only classification consistent with this plan's own "default-fatal" principle. The inverse polarity is rejected for the same underlying reason: it is **fail-open on the unknown**. Requires `import errno` (verified legal against T-11/T-4/stdlib-only in §Provenance). Flagged for spec-review |
| 3 | Exactly ONE new stdlib import (`errno`); nothing from `..verify.marker` | `import errno` (stdlib) for the `EADDRINUSE` comparison; **no** import from `..verify.marker`, `.token`, or any third party | `from ..verify.marker import KeyUnavailable` to catch it by name; or (round 1's shape) avoiding `errno` by catching `OSError` broadly | Constraint-driven, not preference. The closed allow-list (`_ALLOWED_SERVER_IMPORTS`) and the module's own "CLOSED IMPORT ALLOW-LIST" docstring (`:30-45`) make widening the **`.server`** import surface a reviewable event — and `import errno` does not touch it (`_dot_server_import_names` inspects only `from .server import`, `:79-91`). Round 1 avoided the import at the cost of an over-broad classifier; the correct trade is the opposite: pay one stdlib import, get an exact classifier. `errno` adds **zero dependencies**, so `decisions/runtime-and-deps.md`'s stdlib-only rule and `pyproject.toml`'s `dependencies = []` (`:8`) both hold unchanged. `KeyUnavailable` still needs no import, because "not-`EADDRINUSE`" already covers it. (Note: `test_never_imports_token_module_or_marker_module_directly` (`:503-518`) checks `node.module == "marker" and node.level == 2`, which would NOT actually catch `from ..verify.marker import X` — a real gap in that test. We do not exploit it, and we do not fix it either: out of scope) |
| 4 | **`[PLAN-STAGE JUDGMENT]` How `request_approval` fails** | **Raise** a new module-level `ApprovalListenerUnavailable(RuntimeError)`, whose message embeds `str(exc)` from the captured failure | Return an error *string* | "Fail loudly / fail closed" is the operator's directive. A returned string is a weak signal: the tool's contract is *"returns the review URL as a plain string"* (`:161`, and T-2 asserts `isinstance(result, str)`), so an error string is type-indistinguishable from success and an agent may well surface it to the operator as if it were a URL — the same silent-failure class, one layer up. An exception is out-of-band and unmistakable. `str(exc)` carries the real diagnosis verbatim (`KeyUnavailable`'s text is `"cannot read key at <path>: [Errno 13] Permission denied"`, `marker.py:103`), so the agent-visible error names the *actual* cause instead of leaving it buried in a `logger.warning` on a dead thread. Flagged for spec-review |
| 5 | **`[PLAN-STAGE JUDGMENT]` Refuse BEFORE staging** | The state check is the **first** statement in `request_approval`; on refusal **no** `pending-<hash>.json` is written | Stage first, then refuse | Staging a change nobody can approve leaves litter in `.gleipnir/var/tmp/` that a later `GET /approve/<hash>` would happily render as a live review page — a second, quieter false-success surface. Refusing first keeps the failure total and clean. Cost: none (the operator re-invokes after fixing the key). Flagged for spec-review |
| 6 | **`[PLAN-STAGE JUDGMENT]` Startup window is ALLOW; the guarantee is SCOPED, not timed** *(corrected — spec-review round 1, Important defect 2; option (b) chosen)* | The initial state is "no refusal reason recorded" and **allows**. Only an observed fatal failure flips it to refuse. **The guarantee this fix provides, stated exactly:** *any `request_approval` call that reads the listener state **after** `_run_listener` has recorded a fatal failure reason will observe it and refuse.* Nothing weaker, nothing stronger | (a) Strengthen the synchronisation so no call can race the window — e.g. a readiness barrier `request_approval` blocks on. **Rejected**, and rejected on substance, not convenience: a *positive*-ready signal is unobtainable without editing `server.py` (see below), so a barrier would have nothing sound to wait for; and a barrier in the tool path would convert a startup race into a startup **hang**. (Also rejected: round 1's own wording, which claimed a "sub-second" window and that "the very next call refuses") | A positive-ready signal is **not obtainable** without changing `server.py`: `run_server` (`:379-408`) blocks in `serve_forever()` and never returns on success, so "still running" and "not yet started" are indistinguishable from outside. Requiring a ready-signal would mean editing `server.py` — outside this plan's `P` and outside a bounded bug fix. **Named, ACCEPTED residual (this is not a guarantee this fix closes):** a `request_approval` call that races the startup/failure window — reading a clear, healthy-*looking* state before `_run_listener` has recorded anything — **will return a URL that may already be dead.** The lock makes each individual read/write atomic; it does **not** order the tool call against the listener's progress, and no such ordering exists. Round 1's "sub-second" / "the very next call refuses" language is **withdrawn as unsupported**: the plan makes no timing claim, because the mechanism supports none. What remains true and is the entire claim: the refusal is *durable once recorded* (nothing clears it but the test-only `reset()`), and today the state is *never* recorded at all. Strictly better on the post-record path; unchanged on the racing path. Arbiter for the accepted behaviour at the boundary: **AC-10** (event-driven, no sleeps, no timing assertion). Flagged for spec-review |
| 7 | **`[PLAN-STAGE JUDGMENT]` Test-file impact: UPDATE one existing test + ADD a new class, in the EXISTING file** | **Update** `TestT9FailClosedKeyDoesNotCrashTheProcess::test_request_approval_still_works_when_the_key_is_unavailable` (`:434-444`) — it currently asserts the bug. **Add** a new sibling class `TestT12ListenerUnavailableFailsLoud` in the **same** file. **No new test file.** | A new `tests/test_approval_listener_health.py`; or leaving the T-9 test as-is and only adding new tests | (i) The existing test **asserts the defect** (`assert "/approve/" in result` after a key-unavailable listener start) — leaving it would make the suite red-by-design or, worse, encode the bug as intended behaviour. It must be updated, not merely supplemented. (ii) A new file needs a **Tier-3, operator-only** `.gleipnir/sandbox/profiles.toml` `[profile.broker].test` amendment (the list is literal, `test_selector_prefix = false`, `:60,63`) plus a `conftest.py collect_ignore` addition — the exact gate `plans/broker-pm-coverage-gap.md` Decision 4 and `plans/git-diff-distill.md` Decision 13 both hit. Extending in place keeps this plan **entirely inside `src/**`+`tests/**` with zero Tier-3 coupling**, which for an URGENT fix is decisive. Flagged for spec-review |
| 8 | **`[PLAN-STAGE JUDGMENT]` Module-level state needs a test-isolation reset** | Add an **autouse** fixture in `tests/test_approval_mcp_server.py` that resets the listener state before every test in the module, plus an explicit reset seam on the state object | Relying on test declaration order | The state is module-level and **shared across every test in the process**. A T-9-class test that flips it to "unavailable" would poison the T-2/T-3 classes' `request_approval` calls (`:210-321`) if they ran afterwards. Today's file order happens to put T-9 late, but order is not a contract — this would be a latent, confusing flake. An autouse reset makes isolation explicit. Flagged for spec-review |
| 9 | Annotate Decision 19 in `plans/tier3-mcp-approval-launcher.md`? — **FLAGGED, deliberately NOT performed here** | **Recommended: YES, a one-line annotation**, but left to the orchestrator/operator to route. This plan does not silently edit another plan's decision text | Silently editing it as part of this plan; or ignoring the staleness | Decision 19 (`:82`) and edge case 1 (`:444-448`) are the cited authority for the current broad catch, and their text says "**ANY** failure ... is logged and this function simply returns". Left unannotated, a future reader re-derives the buggy behaviour from a stale-but-authoritative-looking plan (the L-C14 "phantom gap" failure mode). BUT: I hold the Tier-0 write grant for `.gleipnir/plans/**`, and editing a *different* plan's converged decision row from inside *this* plan's planning stage is exactly the kind of quiet, unreviewed mutation the framework exists to prevent. So: **named, not done.** The authoritative refinement is recorded in THIS plan (Decision 2), and the durable home for it, if the operator wants one, is `decisions/tier3-signed-approval.md` — **Tier-3, operator-only**. Non-blocking |
| 10 | Pipeline routing | **FULL 8-stage pipeline.** NOT prose/config-track eligible | The light prose/config track; the hardened prose/config track | Mechanical, per `stage-role-map.md` Axis 1: `P` contains `src/**` **and** `tests/**`, both explicit members of the disqualifier set `X` → "the plan runs the **full 8-stage pipeline**, no matter how small the code portion." Axis 2 is not even reached (it only routes *track-eligible* plans). See §Routing for the full derivation and for why the "negative-check attestation" is **not** an artifact of this plan |
| 11 | Scope: zero signer-uid architecture | This plan fixes **only** the silent-failure symptom. It does **not** touch the "signer shares the agent's uid" root cause, Ed25519/`cryptography`, IPC, uid provisioning, `ansible/**`, `opencode.jsonc`, `bin/gleipnir-launch`, the armed-pipeline collision (`sequence-gate.ts`/`advance-hook.ts`), or `boundary.py`'s signer-can-read assertion | Folding in any part of Forks 1–4 | Operator-directed split (brainstorm Decision 1, `:42-59`). Those items are a **separate, parallel, still-unconverged** thread (that brief's items 4–8 are OPEN; its own readiness verdict is "NOT ready for `gleipnir-plan`"). Per that brief's mitigation #4, F-1's urgency is preserved precisely by *not* bundling it. This plan also does **not** claim any key-confidentiality or isolation benefit — see §Honesty ledger |
| 12 | `run_server` returning **normally** leaves state unchanged | No branch for the normal-return path | Treating a normal return as "listener gone → refuse" | `run_server` only returns normally if `serve_forever()` exits, which inside `run_server` happens via its `except KeyboardInterrupt: pass` (`server.py:405-406`). CPython delivers `SIGINT` to the **main** thread only, and the listener is a non-main daemon thread (`:231-242`), so this is unreachable in production. Adding a branch would also break the existing T-1/T-8 tests, which fake `run_server` as an immediately-returning lambda (`:170,390`) and would then be classified as failures. Least code, no behaviour change, documented as edge case E-5 |
| 13 | **Named residual (NOT a resolved architecture item):** **persistent** refusal despite a genuinely-healthy manual listener at a *different* uid | Accept the false refusal; make the error message name the possibility and the remedy | "Fix" it with a liveness probe of `127.0.0.1:8765` | Because `load_key` runs **before** the bind (`server.py:397-398` vs `:402`), a caged in-process listener raises `KeyUnavailable` *even when* a healthy operator-run `bin/gleipnir-approval-server` (different uid, key readable) is bound and serving. The state flips fatal and — since nothing clears it in production — **stays** refusing for the life of the MCP process, though the URL would have worked. **This residual is the persistent-false-refusal case ONLY; it is NOT the startup race** (that is a distinct, separately-recorded residual — Decision 6 / E-6 — and the two must not be conflated: this one is a *durable over-refusal*, that one is a *transient under-refusal*). This is the **fail-closed direction** and is directly implied by the operator's "fail loudly / fail closed" directive, and it is trivially reversible (one conditional). Classified **NOT material** for that reason — but recorded prominently, and the remedy (a real liveness probe) is named as a **separate future change**, explicitly not folded in. **Scope note (spec-review round 1, minor correction):** this plan makes **no** claim that "no external listener could mint an approval" — an operator-run listener at another uid with a readable key can and does mint approvals, by design; that is precisely why refusing it is a *false* refusal. The only claim here is about **this** process's own tool surface. Spec-review is invited to disagree with this classification |
| 14 | Known limitation NOT fixed: `src/gleipnir/approval/**` has no coverage measurement | Record it; change nothing | Amending `[profile.broker].coverage` | `[profile.broker].coverage` is `--cov=src/gleipnir/broker` (`profiles.toml:62`) — it does not cover `approval/`; and the lean `python` profile `collect_ignore`s this test file (`conftest.py:50`). So `mcp_server.py` is *tested* but its coverage is *unmeasured*. Fixing that is a **Tier-3, operator-only** `profiles.toml` edit and is out of this plan's `P`. Named so it is not mistaken for a coverage claim |

---

## 1. Architect

**Problem (one sentence).** When the `gleipnir-approval` MCP's listener thread
dies because the signing key is unreadable, `request_approval` keeps returning
plausible `/approve/<hash>` URLs that nothing is listening to, so a total
failure of the Tier-3 approval subsystem presents as a working tool surface plus
one `logger.warning` on a dead background thread.

**User.**

- **Primary:** the **operator**, who receives a `/approve/<hash>` URL, opens it
  on a separate authenticated tailnet device, and finds nothing serving — with
  no indication of why, because the diagnosis is in a suppressed warning inside
  an opencode-supervised subprocess's stderr.
- **Secondary:** the **`tier3-writer` agent** (the sole holder of
  `gleipnir-approval_*`; every other roster agent denies it — verified in 9
  agent files), which today receives a success-shaped string and reports
  "approval requested" when in fact no approval can ever be minted.

**Measurable success criteria.**

1. With the key unreadable (or absent), `request_approval` **raises** an error
   naming the underlying cause **verbatim** plus recovery guidance, and writes
   **no** staging envelope. Arbiter: AC-2.
2. With a port-bind conflict (`OSError` whose `errno` **is** `EADDRINUSE`),
   behaviour is **byte-for-byte unchanged** from today: `logger.warning`,
   thread exits, `request_approval` stages and returns a URL. Decision 19's
   argued-for case survives intact. Arbiter: AC-3.
3. With any **other** `OSError` (`errno != EADDRINUSE`, or `errno is None`) —
   e.g. `PermissionError`/`EACCES`, `EADDRNOTAVAIL`, `EMFILE` — behaviour is
   the **fatal** path, identical to criterion 1: `logger.error`, state flips,
   `request_approval` refuses. *No* `OSError` is benign by type alone.
   Arbiter: AC-3b.
4. The failure is loud in **three** independent channels, not one:
   `logger.error` (not `warning`), the recorded state, and the raised
   tool-surface exception. Arbiter: AC-1 + AC-2.
5. The refusal is loud **at the real MCP tool-dispatch boundary**, not only to
   a direct Python caller: dispatching `request_approval` through the
   registered FastMCP tool surface yields a result that is unambiguously
   distinguishable from a successful URL result. Arbiter: AC-2b.
6. No regression to the happy path or to the never-started path: a running
   listener, and a `request_approval` call in a process where no listener was
   started, both return URLs as today. Arbiters: AC-4, AC-5.
7. Every existing structural guarantee still holds: T-11's reverse-import scan,
   the closed `.server` allow-list, no HTTP handler class, no `hmac`/`hashlib`
   import, no `webbrowser`. Arbiter: AC-6 (the existing T-4/T-5/T-11 classes,
   unmodified, must stay green).
8. Test isolation of the module-level state is guaranteed **without** depending
   on pytest run order. Arbiter: AC-7.
9. The whole `[profile.broker]` suite is green. Arbiter: AC-7b.

**Constraints (all verified against disk, not assumed).**

- **T-11 closed import allow-list.** `mcp_server.py` may import only
  `run_server, register_default_resolvers, compute_change_hash,
  staged_path_for, default_token_dir` from `.server`, and must contain **no
  identifier reference** (import / call / attribute — an AST scan, not a
  source-text scan) to `load_key`, `capture_approval`, `mint_approval`
  (`tests/test_approval_mcp_server.py:44-54, 94-110, 474-495`). **This plan
  adds exactly one import — `import errno` (stdlib) — and adds nothing to the
  `.server` allow-list.** Legality verified line-by-line in §Provenance.
- **`server.py` is NOT touched.** It is the shared listener core used by both
  launch paths (the MCP wrapper and the manual `bin/gleipnir-approval-server`
  shim, `server.py:12-22`). Touching it would widen blast radius beyond a
  bounded fix and would drag in the shim's behaviour.
- **`request_approval`'s success contract is preserved.** Still
  `(content, file_path="", tool="") -> str`, still the same
  `pending-<hash>.json` envelope, still the same URL text (T-2/T-3 assert all of
  this, `:210-321`). Only a *new refusal path* is added.
- **Decision 19's legitimate half must survive.** A bind conflict must not kill
  the MCP process or the tool surface.
- **Enforcement core stays stdlib-only** (`decisions/runtime-and-deps.md`); the
  `mcp` SDK carve-out remains confined to this one file. This plan adds no
  dependency of any kind — `errno` is stdlib, so `pyproject.toml`'s
  `dependencies = []` (`:8`) and `Containerfile.broker`'s pinned install set
  (`:27`) are both untouched.
- **Bounded-agent capability:** `gleipnir-code` may edit both files and may run
  `./bin/gleipnir-sandbox test --profile broker` (verified
  `gleipnir-code.md:11-28, 41-51`).

---

## 2. Trace

### Artifacts and where they live (source of truth)

| Artifact | File | Status | Owner | Change |
|---|---|---|---|---|
| Listener-state holder + classification + refusal | `src/gleipnir/approval/mcp_server.py` | **EXISTS** (248 lines) | bounded `gleipnir-code` | Add `import errno`; add a small state object + an `ApprovalListenerUnavailable` exception; replace `_run_listener`'s single `except Exception` with an `errno`-discriminated classifier (benign **iff** `OSError` and `errno == errno.EADDRINUSE`; fatal otherwise); add the state check as `request_approval`'s first statement; **update the three stale docstring passages** (`:55-63`, `:181-197`, and the tool docstring `:161-176`) so the module stops documenting "ANY failure → log-and-continue" |
| Updated + new tests | `tests/test_approval_mcp_server.py` | **EXISTS** (518 lines) | bounded `gleipnir-code` | **Update** `TestT9...::test_request_approval_still_works_when_the_key_is_unavailable` (`:434-444`); **add** `TestT12ListenerUnavailableFailsLoud` (incl. the non-`EADDRINUSE` `OSError` case, the FastMCP-dispatch case, and the event-driven startup-window case); **add** an autouse state-reset fixture **plus its own self-proving order-independence test** (AC-7). Also update the module docstring's test-inventory line (`:4-7`) to include T-12 |
| Sandbox profile wiring | `.gleipnir/sandbox/profiles.toml` | **EXISTS** | — | **NO CHANGE NEEDED** — `tests/test_approval_mcp_server.py` is already the last entry of `[profile.broker].test` (`:60`, verified). This is why Decision 7 extends in place |
| Lean-profile collection guard | `tests/conftest.py` | **EXISTS** | — | **NO CHANGE NEEDED** — already in `collect_ignore` (`:50`, verified) |
| Decision 19 annotation | `.gleipnir/plans/tier3-mcp-approval-launcher.md` | **EXISTS** | orchestrator/operator | **FLAGGED, NOT DONE** (Decision 9) |
| Durable record of the refinement | `.gleipnir/decisions/tier3-signed-approval.md` | **EXISTS** | **operator only (Tier 3)** | Optional; named, never touched by this plan |

### Proposed shape (design, not final code — `gleipnir-code` writes it)

Four additions to `mcp_server.py`, each with exactly one responsibility (plus
one stdlib import):

0. **`import errno`** — stdlib, the only new import. Sole purpose: name the
   `EADDRINUSE` constant symbolically rather than as a magic number.
1. **`ApprovalListenerUnavailable(RuntimeError)`** — module-level exception. Sole
   responsibility: signal to the MCP tool caller that no in-process listener can
   honour a review URL.
2. **A listener-state holder** — a small module-level object guarding one
   `Optional[str]` "refusal reason" behind a `threading.Lock` (the listener
   thread writes; the MCP main thread reads, so the lock is not decorative).
   Sole responsibility: carry the one-bit answer to *"has the listener failed in
   a way that makes an approval URL meaningless?"* across the thread boundary.
   Exposes exactly three operations: `mark_unavailable(reason)`,
   `refusal_reason() -> str | None`, and `reset()` (the test-isolation seam,
   Decision 8 — same "injectable seam only" convention already used by
   `token_dir=` at `:129,140-141`).
3. **The `errno`-discriminated classifier** in `_run_listener` — a **single**
   `except Exception as exc:` block containing **one** benign test, so the
   "default-fatal" polarity is structural rather than a matter of clause
   ordering:

   ```
   except Exception as exc:                        # noqa: BLE001
       if isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE:
           logger.warning(...)                     # Decision 19's named case
           return                                  # state UNTOUCHED
       logger.error(...)
       mark_unavailable(str(exc))                  # the new loud path
       return
   ```

   **Why one block with an inner test, not two `except` clauses** (this is the
   round-1 correction, made structural): with `except OSError` as its own
   clause, *every* `OSError` lands in the benign branch and the narrowing has
   to be remembered as an extra condition inside it — the exact omission
   spec-review found. With one block, **fatal is the fall-through** and benign
   requires an affirmative match on the accepted condition. A future editor who
   deletes the `if` gets *more* refusal, never less. `errno is None` (possible
   on a hand-constructed `OSError()`) compares unequal to `errno.EADDRINUSE`
   and is therefore fatal — correct by construction, not by a special case.
4. **The check** as `request_approval`'s first statement:
   `reason = refusal_reason()`; if not `None`, `raise
   ApprovalListenerUnavailable(<message including reason>)` — **before**
   `_stage_pending_content` (Decision 5).

Error-message content (the loudness payload — reviewed as part of AC-2, and
asserted **conjunctively** there, not by a single weak substring): it must name
(i) that the in-process listener is not running, (ii) the captured `str(exc)`
**verbatim** — the full recorded reason substring, not a paraphrase or a
keyword, (iii) that **this MCP's `request_approval` tool will not mint or make
available a review URL via the in-process listener, and will keep refusing for
the life of this process** — scoped exactly that way and **no wider**, and
(iv) the recovery guidance for the Decision 13 possibility — that a separately
run manual `bin/gleipnir-approval-server` at another uid, if healthy, is
**unaffected** and may still be serving and minting, and how to proceed if so.
A vague message here would recreate the defect one level up. AC-2 asserts (ii)
**and** (iv) together, so a generic message cannot pass.

**Scope discipline on (iii)** *(spec-review round 2 reconciliation)*: the message
must **not** claim that no approval can be minted, that the write will stay
refused system-wide, or that every other approval path is dead. The wrapper's own
recorded failure cannot establish any of that — it observed **its** listener
fail, and it has no knowledge of whether a manual listener at another uid is
healthy. Decision 13 says exactly this. A message overclaiming system-wide
impossibility is itself a false statement emitted by a fail-loud path, which is
the defect class inverted, and is a **NON-CONFORMANCE**.

### Integrations map

```
opencode (uid = agent uid under CAGED)
  └─ spawns local MCP child: .venv/bin/python -m gleipnir.approval.mcp_server
       (opencode.jsonc:91-100 — inherits the agent uid; NOT changed here)
       │
       ├─ main thread: mcp.run(transport="stdio")   [:248]
       │     └─ @mcp.tool() request_approval        [:159-178]
       │           1. NEW: refusal_reason()?  ──yes──> raise ApprovalListenerUnavailable
       │           2. _stage_pending_content(...) -> .gleipnir/var/tmp/pending-<hash>.json
       │           3. _build_approval_url(hash) -> "Approve at: .../approve/<hash>"
       │
       └─ daemon thread "gleipnir-approval-listener" [:231-242]
             └─ _run_listener()                      [:181-212]
                    register_default_resolvers()      [server.py:373-376]
                    run_server(...)                   [server.py:379-408]
                      ├─ load_key(key_file)           [server.py:398 -> marker.py:86-106]
                      │    EACCES under CAGED ──> KeyUnavailable (NOT an OSError)
                      │                              ──> FATAL: logger.error + mark_unavailable
                      └─ HTTPServer((host, port))     [server.py:402]
                           OSError, errno == EADDRINUSE
                                     ──> BENIGN: logger.warning, state untouched
                                                  (Decision 19, its ONE named case)
                           OSError, errno != EADDRINUSE  (EACCES / EADDRNOTAVAIL /
                                     EMFILE / ENFILE / errno is None)
                                     ──> FATAL: logger.error + mark_unavailable
                                                  (round-1 correction: NOT benign)
```

Unchanged and deliberately untouched by this plan: `server.py`,
`verify/marker.py`, `approval/token.py`, `approval/gate.py`,
`approval/__main__.py`, `.gleipnir/plugins/tier3-gate.ts` (it never calls this
tool — verified zero `request_approval` hits in any `*.ts`), `opencode.jsonc`,
`bin/**`, `ansible/**`, `boundary.py`.

### Edge cases

| # | Case | Behaviour | Where asserted |
|---|---|---|---|
| E-1 | Key file unreadable (`EACCES`, the caged case) | `KeyUnavailable` → fatal branch → `logger.error` + state flip → `request_approval` raises, stages nothing | AC-1, AC-2 |
| E-2 | Key env var unset / key empty | Also `KeyUnavailable` (`marker.py:96-99, 104-105`) → identical fatal path. This is the case the **existing** T-9 test exercises, which is why that test must be updated rather than duplicated | AC-2 (updated T-9) |
| E-3 | Port `8765` already bound (manual shim running) | `OSError` with `errno == EADDRINUSE` → **benign** → `logger.warning`, state untouched, `request_approval` fully functional. **Decision 19 intact** | AC-3 |
| **E-3b** | **Bind fails for a reason OTHER than a port conflict** — `PermissionError`/`EACCES` (privileged port, sandbox denial), `EADDRNOTAVAIL` (host not local), `EMFILE`/`ENFILE` (fd exhaustion), or any `OSError` with `errno is None` | **FATAL** → `logger.error` + state flips + `request_approval` refuses. **None of these implies "another listener is already serving"**, so treating them as benign would silently hand out dead URLs — the same defect class this plan fixes, different trigger. *(New — spec-review round 1, Important defect 1.)* | **AC-3b** |
| E-4 | Key unreadable **and** port already bound | `load_key` runs **before** the bind (`server.py:397-398` vs `:402`), so `KeyUnavailable` wins and we refuse — even though the bound manual listener might have served the URL. Accepted fail-closed; the error message names it | Decision 13; AC-2 message check |
| E-5 | `run_server` returns normally | State untouched; `request_approval` keeps working. Unreachable in production (`KeyboardInterrupt` is main-thread-only; the listener is a non-main daemon thread) | Decision 12; implicitly by AC-4/AC-5 |
| E-6 | `request_approval` called **before** `_run_listener` has recorded anything (startup window) | **Allowed** — state is initially clear, so a URL is returned. **This is a NAMED, ACCEPTED residual, not a closed hole:** the returned URL may already be dead, because there is no ordering between the tool call and the listener's progress. The scoped guarantee is only that a call reading the state **after** a fatal reason is recorded refuses. **No timing claim is made** (round 1's "sub-second"/"the very next call refuses" is withdrawn as unsupported) | Decision 6; **AC-10** (event-driven demonstration of the accepted boundary behaviour, no sleeps/timing assertions) |
| E-7 | `register_default_resolvers()` raises (not an `OSError`) | Fatal → refuse. Correct: no resolver means `resolve_identity` raises `IdentityUnresolved` for every POST (`registry.py:57-72`), so no token could ever be minted — a URL would be just as dead | AC-1 (parametrised by a non-`OSError` fault) |
| E-8 | Two tests in one process, one of which flips the state | Autouse reset fixture clears it before **and** after every test in the module; proved order-independently by an in-file assertion, not by a pytest CLI flag | Decision 8; **AC-7** |
| E-9 | Listener healthy, then `request_approval` called many times | No state change on the success path; no accumulation, no locking hot spot (one uncontended lock acquisition per call) | AC-4 |

---

## 3. Link (validated before building)

Everything below was checked against the real files during this planning stage.
Nothing in this plan cites a path or line that was not opened and read (L-C15).

- **`src/gleipnir/approval/mcp_server.py` exists, 248 lines** — read in full.
  The broad catch is at `:204-212`; `request_approval` at `:159-178` has no
  health reference; `start_listener_thread` at `:215-243`; `__main__` at
  `:246-248`.
- **`src/gleipnir/approval/server.py` exists, 432 lines** — read in full.
  `run_server` at `:379-408`; `load_key` call at `:398` **precedes** the
  `HTTPServer` bind at `:402` (the ordering behind E-4).
- **`src/gleipnir/verify/marker.py:43-48, 86-106`** — `KeyUnavailable` is a
  `MarkerError(Exception)`, **not** an `OSError`; `load_key` wraps `OSError` into
  it. The type-based discriminator is sound.
- **`tests/test_approval_mcp_server.py` exists, 518 lines** — read in full.
  T-9's third test (`:434-444`) asserts the current buggy behaviour; T-11's scan
  (`:474-518`) constrains the fix; T-1/T-8 fake `run_server` as an
  immediately-returning lambda (`:170,390`), which Decision 12 must not break.
- **`.gleipnir/sandbox/profiles.toml:58-63`** — `[profile.broker]`,
  digest-pinned image, `test` list already contains
  `tests/test_approval_mcp_server.py`, `test_selector_prefix = false`,
  `coverage` scoped to `src/gleipnir/broker` (Decision 14).
- **`tests/conftest.py:44-50`** — the file is already `collect_ignore`d for the
  lean `python` profile.
- **`.gleipnir/agents/gleipnir-code.md:11-51`** — `edit` reaches
  `src/gleipnir/approval/**` and `tests/**`; `bash` allows
  `./bin/gleipnir-sandbox test --profile broker`.
- **`.gleipnir/plans/tier3-mcp-approval-launcher.md:82` (Decision 19) and
  `:442-472` (edge cases 1 and 5)** — read; confirms the rationale is
  port-conflict-only while the implementation is `except Exception`.
- **`opencode.jsonc:91-100`, `bin/gleipnir-launch:37-44`,
  `ansible/site.yml:369-382`, `src/gleipnir/preflight/boundary.py:345,995-999`**
  — read, solely to verify the F-1 chain. **None is touched by this plan.**
- **No production caller of the changed surface** — `request_approval` /
  `start_listener_thread` grepped across all `*.py` (only `mcp_server.py` + its
  test) and all `*.ts` (**zero** hits).

**FastMCP's dispatch boundary — NOW VALIDATED `[D]`, not assumed**
*(spec-review round 1, Important defect 3(i); round 1 tagged this `[J]` and
designed around it, which left the plan's central loudness claim untested at
the only boundary that matters).* Round 1 asserted that no acceptance check
would depend on SDK marshalling because every check called
`mcp_server.request_approval(...)` as a bare Python function — the convention
T-2/T-3 use (`:219,240,253,311,319`). Spec-review correctly identified that as
the gap: the *entire* rationale for Decision 4 (raise, don't return a string)
is that the failure must be unmistakable **to the real caller**, and a bare
function call cannot show that. So the SDK was read. Verified facts:

- **There is an in-process dispatch entry point.**
  `mcp.server.fastmcp.server.FastMCP.call_tool(name, arguments)` (`server.py:346-349`)
  → `self._tool_manager.call_tool(name, arguments, context=..., convert_result=True)`.
  It is `async`, and the **existing test file already drives an async FastMCP
  method exactly this way**: `asyncio.run(mcp_server.mcp.list_tools())`
  (`tests/test_approval_mcp_server.py:143`). So AC-2b needs **no** new harness,
  no new dependency, and no stdio subprocess — it reuses an in-file pattern.
- **An exception from the tool function does NOT become a URL-shaped success.**
  `Tool.run` (`tools/base.py:93-117`) wraps the call in
  `try: ... except Exception as e: raise ToolError(f"Error executing tool {self.name}: {e}") from e`.
  So `ApprovalListenerUnavailable` surfaces as
  `mcp.server.fastmcp.exceptions.ToolError` — **raised**, never returned — and
  is therefore type-distinguishable from the success path, which returns
  content.
- **The captured cause SURVIVES marshalling.** The `ToolError` message
  interpolates `{e}`, i.e. `str(ApprovalListenerUnavailable)`, so the full
  refusal message — including the verbatim `str(exc)` cause and the recovery
  guidance (Decision 4) — is carried through the dispatch layer, not truncated
  to a generic code. `from e` also preserves `__cause__`. **This is what makes
  AC-2b assertable on message content and not merely on exception type.**
- **Residual, correctly scoped:** this validates the *in-process dispatch*
  boundary (`FastMCP.call_tool`), which is the layer this plan's `P` can reach.
  It does **not** validate the full stdio wire frame; the repo's precedent for
  that is a separate, heavier subprocess harness
  (`tests/test_broker_wire_protocol.py:86,279-324`, which established that
  FastMCP reports tool failures as `result.isError: true` rather than a
  JSON-RPC `error`). A wire-level approval test is **deliberately out of scope**
  for this bounded fix — but note the direction of that precedent *reinforces*
  the conclusion: either way, the failure is structurally flagged, never a
  URL-shaped success.

---

## 4. Assemble (intended build order)

Test-first (Axiom 1): the arbiter is written before the fix.

| Step | Stage | Actor | Work |
|---|---|---|---|
| 1 | `spec-review` | `quality-reviewer` | Review THIS plan against the rubric: the 14 Decisions rows (esp. the six `[PLAN-STAGE JUDGMENT]` rows 1,2,4,5,6,7,8), the Design-Intent **intent-quality sub-check** (specific + falsifiable, not a quality aspiration), the Decision 13 "not material" classification, and the Decision 10 routing derivation. A FAIL here stops the pipeline |
| 2 | `test` | `gleipnir-code` | **`tests/test_approval_mcp_server.py` only.** (a) Add the autouse state-reset fixture; (b) **UPDATE** `TestT9...::test_request_approval_still_works_when_the_key_is_unavailable` to assert the refusal + that no envelope is staged; (b2) **ADD AC-7's required entry-assertion line to one representative test each in T-2 and T-3** — a single leading `assert refusal_reason() is None`. These T-2/T-3 edits are **narrow, additive, assertion-only**: they add one new line and change **nothing** about T-2/T-3's own existing behavioural assertions, which must remain byte-for-byte unchanged. **This is PERMITTED and REQUIRED** (it is AC-7's in-file order-independence proof), and it is the *complete* list of edits outside T-9 — no other existing test may be touched in any way; (c) **ADD** `TestT12ListenerUnavailableFailsLoud` covering **AC-1, AC-2, AC-2b (FastMCP dispatch), AC-3, AC-3b (parametrised non-`EADDRINUSE` `OSError`), AC-4, AC-5, AC-7 (in-file order-independence), AC-10 (event-driven startup window)**, incl. E-7; (d) update the module docstring's test inventory (`:4-7`). Run `./bin/gleipnir-sandbox test --profile broker` — **no extra arguments; the CLI refuses them for this profile** — and confirm the new/updated tests **FAIL** against the unmodified source (a test that passes before the fix is not an arbiter). Note AC-3's and AC-5's tests legitimately pass pre-fix (they guard *preserved* behaviour); AC-1/AC-2/AC-2b/AC-3b/AC-10 must all fail pre-fix |
| 3 | `code` | `gleipnir-code` | **`src/gleipnir/approval/mcp_server.py` only.** Add `import errno`; add the exception + state holder; replace the single broad catch with the `errno`-discriminated classifier (benign **iff** `OSError` and `errno == errno.EADDRINUSE`, fatal fall-through); add the pre-staging check; update the three stale docstring passages (`:55-63`, `:161-176`, `:181-197`). Run the same command until **all** of AC-1..AC-10 (incl. AC-2b, AC-3b, AC-7b) are green with **no** existing test modified beyond step 2's named edits — i.e. beyond the T-9 rewrite (b) and the additive T-2/T-3 entry-assertion lines (b2), and **no** existing behavioural assertion altered anywhere |
| 4 | `quality` | `quality-reviewer` | Two things, per the cognition binding: (i) the **blast-radius / false-success** pass incl. the SOLID/DRY dimension — the adversarial question being *"how could this fix itself be wrongly green?"* (candidate answers to probe: a refusal path that stages anyway; **a benign branch keyed on `OSError` by TYPE rather than on `errno == errno.EADDRINUSE`, or widened to a set of errnos — the round-1 defect, AC-3b's target**; the state check placed after staging; an autouse fixture that masks a real leak; a test that asserts only `pytest.raises` and never checks the message carries **both** the verbatim cause and the recovery guidance; **a test that redirects `_run_listener`'s `token_dir=` but not `request_approval`'s own `default_token_dir()`, and so "proves" nothing was staged only because it inspected the wrong directory**; **a loudness claim resting solely on bare-function calls, with nothing exercising `mcp.call_tool`**; **any resurrected timing/"next call" language or a `time.sleep`-based startup test**; **any acceptance step requiring a pytest CLI flag, which this profile refuses outright**); (ii) the **honour check** — does the applied code honour the Design Intent below? A divergence is **Important** and blocks `git` until the operator acknowledges it |
| 5 | `git` | `git-ops` | Commit both files. Sole git holder |
| 6 | `gate` | `orchestrator` | Read evidence; emit pipeline state. **Do not self-declare done** |
| — | out of band | orchestrator/operator | Decision 9's optional Decision-19 annotation; Decision 14's optional coverage-scope amendment. **Neither blocks this fix** |

Steps 2 and 3 are strictly ordered (test before code). Steps 1→2 and 3→4 are
strictly ordered. No step touches a file outside `P`.

---

## 5. Stress-test (acceptance checks)

Concrete and checkable. All run via **exactly**
`./bin/gleipnir-sandbox test --profile broker`, with **no extra arguments**.

**This is a hard constraint on the whole table, not a convention** *(spec-review
round 1, Important defect 4)*. `[profile.broker]` declares
`test_selector_prefix = false` (`.gleipnir/sandbox/profiles.toml:63`), and the
sandbox CLI **refuses** — exit **3**, nothing run — if any extra pytest argument
is supplied for such a profile (`src/gleipnir/sandbox/__main__.py:131-139`).
Therefore **no AC in this table may depend on a pytest flag, a `-k` selector, a
`-p` plugin toggle, or a per-class invocation**; every acceptance condition must
be expressible as an assertion **inside the test file**, satisfied by the single
permitted command. An AC that needs a CLI flag is not a strict AC — it is an
unsatisfiable one (round 1's AC-7 was exactly that, and is replaced below).
Widening the profile to accept arguments is a **Tier-3 `profiles.toml` change,
out of `P` and out of scope** — it is not an available workaround.

| AC | Check | Pass condition |
|---|---|---|
| **AC-1** | Fatal classification. Call `_run_listener(key_file=None, token_dir=tmp_path)` with `GLEIPNIR_MARKER_KEY_FILE` deleted, capturing logs | A record at **`ERROR`** level (not `WARNING`) is emitted, its message names the listener and embeds the underlying reason; the function returns without raising; the state now reports a refusal reason. **Also parametrised for E-7** (a monkeypatched `register_default_resolvers` raising a non-`OSError`) → same fatal outcome |
| **AC-2** | Loud refusal + no litter, with a **CONJUNCTIVE** message assertion. **First redirect `request_approval`'s OWN staging call site** — `monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)`, the existing in-file pattern (`tests/test_approval_mcp_server.py:440`) — because `request_approval` calls `_stage_pending_content(content, file_path, tool)` with **no** `token_dir=` argument (`mcp_server.py:177`), so passing `token_dir=tmp_path` to `_run_listener` does **NOT** redirect it: they are **separate call sites** *(spec-review round 1, Important defect 3(iii))*. Then, after AC-1's fatal state, call `mcp_server.request_approval("x", file_path="f", tool="write")` | `pytest.raises(mcp_server.ApprovalListenerUnavailable)`, **and** the message satisfies **BOTH** of: **(a)** it contains the **verbatim recorded cause IN FULL**. State the requirement normatively, not by example: **`captured_reason in message`**, where `captured_reason` is the *complete* string the fatal branch recorded (`str(exc)`), obtained in the test from the state itself (`refusal_reason()`) or from the same `KeyUnavailable` the fault raised — **never** a hardcoded literal *(spec-review round 2 note: round 1's examples were misleading. `"cannot read key at "` is only a **prefix**; the real `marker.py:103` message is `f"cannot read key at {path}: {exc}"`, i.e. it continues with the path and the OS error — e.g. `cannot read key at /x/key: [Errno 13] Permission denied`. A test checking the prefix would pass on a message that truncated everything diagnostic, and the sibling forms differ again: `marker.py:97-99` is `f"no key path: set {KEY_ENV_VAR} or pass key_file explicitly"` and `marker.py:105` is `f"key at {path} is empty"`.)* So: assert the **whole captured reason** is a substring of the raised message. A bare keyword like `"key"`, a prefix, or any hand-written literal shorter than the full captured cause is explicitly insufficient; **and (b)** it contains the **recovery-guidance** text (the Decision 13 possibility: an operator-run `bin/gleipnir-approval-server` at another uid may still be serving, and how to proceed). A test asserting only (a), or asserting a weak keyword, is a **NON-CONFORMANCE** — a generic "listener unavailable" message MUST fail this AC. **Plus the stronger no-staging assertion** (the correct one for a fail-loud test, per Decision 5: staging must not happen **at all**): monkeypatch `mcp_server._stage_pending_content` to a sentinel that fails the test if called, and assert **it was never invoked**; retain `list(tmp_path.glob("pending-*.json")) == []` as the corroborating on-disk check |
| **AC-2b** | **Caller-visible loudness at the REAL MCP tool-dispatch boundary**, not merely to a bare Python caller *(new — spec-review round 1, Important defect 3(i); arbiter for Architect criterion 5)*. With the fatal state set, dispatch the tool the way a real caller does, through the registered tool surface: `asyncio.run(mcp_server.mcp.call_tool("request_approval", {"content": "x", "file_path": "f", "tool": "write"}))` — the in-process FastMCP dispatch entry point validated `[D]` in §Link, driven with the **pattern already in this file**, `asyncio.run(mcp_server.mcp.list_tools())` (`:143`). **No new harness, no new dependency, no stdio subprocess** | The dispatch result is **unambiguously distinguishable from a URL-shaped success**. Concretely, against the pinned broker image's SDK: the failure is **raised**, caught by `pytest.raises` as `mcp.server.fastmcp.exceptions.ToolError` (`Tool.run`, `tools/base.py:93-117`: `except Exception as e: raise ToolError(f"Error executing tool {self.name}: {e}") from e`), **and** the captured cause survives the `{e}` interpolation into its message (assert the same verbatim-cause substring AC-2 requires), **and** no `/approve/` substring appears anywhere in the outcome. **Contrast-asserted in the same test:** with a clean state (AC-5 conditions) the identical dispatch call DOES yield content containing `/approve/`, so the test proves a *difference at the dispatch layer*, not merely that an exception type exists. **If the pinned SDK marshals tool failure as an `isError`-flagged result object rather than a raised `ToolError`** (the `tests/test_broker_wire_protocol.py:86,279-324` precedent), assert on **whichever form that SDK actually produces** — the pass condition is **distinguishability from success plus cause-preservation**, not a specific exception class. A result that is *indistinguishable* from the success result is a **FAIL that must be escalated to the operator**, because it falsifies Decision 4's premise (raise-not-return) and would require re-opening it |
| **AC-3** | **Decision 19 preserved.** Monkeypatch `run_server` to raise `OSError(errno.EADDRINUSE, "Address already in use")`; call `_run_listener` | A **`WARNING`** record (no `ERROR`); the state reports **no** refusal reason; a subsequent `request_approval` returns a `str` containing `/approve/<expected_hash>` **and** the `pending-<hash>.json` envelope exists with the same shape T-2 asserts. This AC is the regression guard on the original design intent |
| **AC-3b** | **A non-`EADDRINUSE` `OSError` is FATAL, never benign** *(new — spec-review round 1, Important defect 1; arbiter for Architect criterion 3 and edge case E-3b)*. **Parametrised** over at least three faults, each monkeypatched as `run_server`'s raise and driven through `_run_listener`: (i) `PermissionError(errno.EACCES, "Permission denied")` — note `PermissionError` **is** an `OSError` subclass, which is exactly why type alone cannot discriminate; (ii) `OSError(errno.EADDRNOTAVAIL, "Cannot assign requested address")`; (iii) a bare `OSError("no errno")`, whose `.errno` **is `None`** | For **every** parameter, without exception: a record at **`ERROR`** level is emitted (and **no** warning-only, state-untouched outcome); the state reports a refusal reason; and a subsequent `request_approval` **raises** `ApprovalListenerUnavailable` and stages nothing (same no-staging assertion as AC-2). A parameter that logs `WARNING` and keeps returning URLs **is** the round-1 defect reintroduced and is an **automatic FAIL**. This AC is what makes "default-fatal" an *arbitrated* property rather than a stated intention |
| **AC-4** | Happy path. Monkeypatch `run_server` to a blocking fake (the T-1 `:177-201` pattern); start the thread; call `request_approval` | Thread alive; a URL string returned; envelope staged; no exception |
| **AC-5** | Never-started path. Fresh state, no listener thread started at all; call `request_approval` | A URL string returned (no refusal). Guards against a fix that refuses by default and breaks T-2/T-3 |
| **AC-6** | Structural guarantees intact. The **unmodified** T-4, T-5 and T-11 classes | All green. Specifically: `_all_identifiers(mcp_server.py)` still disjoint from `{capture_approval, mint_approval, load_key}`; `.server` imports still ⊆ the five-name allow-list; no `BaseHTTPRequestHandler` subclass; no `hmac`/`hashlib`/`http`/`webbrowser` |
| **AC-7** | **Order-independence proved by an IN-FILE deterministic assertion, not by a pytest CLI flag** *(replaced — spec-review round 1, Important defect 4; arbiter for Architect criterion 8)*. Round 1 required a run with `-p no:randomly` and the T-9 class forced first. **That is not executable and is hereby withdrawn:** `[profile.broker]` sets `test_selector_prefix = false` (`.gleipnir/sandbox/profiles.toml:63`), and `bin/gleipnir-sandbox test` **refuses** extra pytest args for such a profile — it prints `"does not support extra test-selector passthrough; refusing rather than forwarding"` and returns exit **3** without running anything (`src/gleipnir/sandbox/__main__.py:131-139`). So `-p no:randomly` cannot reach pytest by the permitted route at all; and even if it could, *disabling* random ordering would not *force* T-9 first. **Widening the profile's argument passthrough is explicitly NOT the fix** — that is a Tier-3 `profiles.toml` change, out of this plan's `P` and out of scope (Decision 7/Decision 14 precedent). **Instead, the guarantee is asserted inside the test file, where it needs no run order at all:** add to `TestT12ListenerUnavailableFailsLoud` a test that, **within one test function**, exercises the full pollution sequence deterministically — (1) assert `refusal_reason() is None` on entry (this is the autouse fixture's guaranteed-clean-state property, and asserting it *is* the order-independence proof: it holds no matter which test ran before, because the fixture runs before **every** test in the module); (2) flip the state fatal via `_run_listener`; (3) assert `request_approval` now refuses; (4) call the state's `reset()` seam; (5) assert `refusal_reason() is None` again **and** that `request_approval` returns a URL once more. **Additionally** add the same entry assertion (1) as an explicit first line in **at least one test of each of T-2, T-3 and T-9** that calls `request_approval`, so a leak from any predecessor is caught *at the victim*, deterministically, under any ordering including `pytest-randomly`'s | The in-file test passes, and it does so **under the profile's ordinary, unmodified command** — `./bin/gleipnir-sandbox test --profile broker` with **no extra arguments** (the only permitted invocation). Order-independence is established by the clean-state entry assertions holding on every run, not by any external flag, and **not** by any assumption about declaration order. Any acceptance condition requiring a pytest CLI flag through this profile is, by construction, unsatisfiable and MUST NOT be reintroduced |
| **AC-7b** | Whole-suite regression. Full `[profile.broker]` run via `./bin/gleipnir-sandbox test --profile broker`, no extra arguments | 100% pass — every pre-existing test in the profile still green, including the T-1/T-8 classes that fake `run_server` as an immediately-returning lambda (`:170,390`) and must **not** be reclassified as failures (Decision 12) |
| **AC-8** | Documentation is not stale. Inspect `mcp_server.py`'s docstrings | No passage still claims "ANY failure ... is logged and this function simply returns". `:55-63` and `:181-197` describe the **two** branches distinctly; `request_approval`'s docstring documents the refusal path and names the raised exception |
| **AC-9** | Scope containment. `git status` / the diff at the `git` stage | Exactly two files changed: `src/gleipnir/approval/mcp_server.py`, `tests/test_approval_mcp_server.py`. Any third path is an automatic FAIL |
| **AC-10** | **The SCOPED guarantee, demonstrated at its boundary with explicit event-based control — and NO timing assertion** *(new — spec-review round 1, Important defect 2, option (b); arbiter for Decision 6 and edge case E-6)*. Drive the boundary deterministically with a `threading.Event` the **test** controls, never a sleep: monkeypatch `run_server` to a fake that (1) waits on `gate = threading.Event()` and only then (2) raises a fatal fault. Start the real listener thread. **Before** `gate.set()` — the listener has provably recorded nothing — assert `request_approval` **returns a URL** (the ACCEPTED residual: this URL may already be dead, and the plan does not claim otherwise). Then `gate.set()`, `thread.join(timeout=5)`, `assert not thread.is_alive()` — the listener has now provably recorded its fatal reason, established by joining the thread, **not** by waiting for a duration. **After** that join, assert `request_approval` **raises** `ApprovalListenerUnavailable` | Both halves hold. **What this AC asserts, exactly:** *a call that reads the state after `_run_listener` has recorded a fatal reason observes it and refuses* — that, and nothing more. **What it must NOT assert, in any form:** any bound on elapsed time, any "sub-second" window, any claim that "the very next call refuses", or any ordering between an arbitrary tool call and the listener's progress. **No `time.sleep`, no wall-clock comparison, and no polling loop may appear in this test** — the `Event` and the `join` are the only synchronisation, and their presence is what makes the assertion sound rather than flaky. The pre-`set()` half is a **positive** assertion of the accepted residual (a URL IS returned), so the test documents the un-closed window honestly instead of pretending it is closed. A reviewer finding a timing assertion here should read it as the round-1 overclaim regrowing and FAIL it |

---

## 6. Execution Workflow

**For the implementing agent (`gleipnir-code`), so no protocol is rediscovered.**

- **Command (the only one you need, both steps):**
  `./bin/gleipnir-sandbox test --profile broker`.
  This test file is **not** collected by the default `python` profile
  (`conftest.py:50`) because it imports `mcp` transitively — a bare
  `bin/gleipnir-sandbox test` will silently not run it. Use `--profile broker`.
  Lint: `./bin/gleipnir-sandbox lint --profile broker` (note: that profile's
  lint is `compileall src/gleipnir/broker`, so it does **not** compile
  `approval/`; `./bin/gleipnir-sandbox lint --profile python` covers `src`).
- **Files you may write:** exactly the two in `P`. You do **not** need, and must
  not attempt, any `.gleipnir/**` edit — `profiles.toml` and `conftest.py`
  already list this test file (verified), and every `.gleipnir/**` path is
  denied to you anyway (`gleipnir-code.md:14`).
- **Order is not optional.** Step 2 (tests) before step 3 (source). Confirm the
  new/updated tests FAIL first. A test authored after the fix is not an arbiter.
- **Existing tests you may change — exactly two kinds, nothing else.**
  1. **The one existing test you MUST rewrite:**
     `TestT9FailClosedKeyDoesNotCrashTheProcess::test_request_approval_still_works_when_the_key_is_unavailable`
     (`tests/test_approval_mcp_server.py:434-444`). Its name and comment
     ("Edge case 1: staging is key-independent") both encode the defect; rename
     it to describe the new behaviour and rewrite the assertions. Its two
     siblings in that class (`:404-432`) remain **valid and unchanged** — the
     thread still must not crash the process and still must terminate; only the
     third one asserted the bug.
  2. **AC-7's required entry assertions — PERMITTED and REQUIRED, not a
     violation of the discipline above** *(spec-review round 2 reconciliation:
     this bullet previously said T-9 was "the only one", which directly
     contradicted AC-7 and made both instructions unsatisfiable at once)*. Add a
     single leading `assert refusal_reason() is None` to **one representative
     test each in T-2 and T-3** (and in T-9, per AC-7). These are **additive,
     assertion-only** edits — one new line each. You must **not** modify,
     reorder, weaken or rewrite any of T-2's or T-3's own existing behavioural
     assertions; they stay byte-for-byte as they are. Adding the entry line is
     the whole edit.

  **Beyond those two, touch no existing test.** The discipline is unchanged in
  substance: no existing behavioural assertion anywhere may be altered. AC-7's
  lines are additive proof-of-isolation instrumentation, which is why they are
  compatible with it rather than an exception to it.
- **The benign carve-out is `EADDRINUSE`-ONLY, and it is load-bearing in BOTH
  directions.** Keep it — it is Decision 19's argued-for port-conflict case, and
  AC-3 is its regression guard; deleting it re-breaks a shipped behaviour. But
  **do not widen it**: the test is `isinstance(exc, OSError) and exc.errno ==
  errno.EADDRINUSE`, a single affirmative condition inside **one**
  `except Exception` block so that **fatal is the fall-through** (Trace §3).
  Writing `except OSError:` as its own clause, or comparing against a *set* of
  errnos, reintroduces the round-1 defect and fails **AC-3b**.
- **Add exactly ONE new import: `import errno` (stdlib).** Nothing else — and in
  particular nothing from `..verify.marker`. T-11 and the closed `.server`
  allow-list are enforced tests, not advice; `errno`'s legality against T-11,
  T-4, the stdlib-only rule and `pyproject.toml`'s `dependencies = []` is
  verified line-by-line in §Provenance. `KeyUnavailable` still needs no import,
  because "not `EADDRINUSE`" already covers it.
- **`token_dir=` on `_run_listener` does NOT redirect `request_approval`'s
  staging.** They are separate call sites: `request_approval` calls
  `_stage_pending_content(content, file_path, tool)` with no `token_dir=`
  (`mcp_server.py:177`), so it resolves `default_token_dir()` itself
  (`:144`). In any test where staging location matters, **also**
  `monkeypatch.setattr(mcp_server, "default_token_dir", lambda: tmp_path)` — the
  pattern already in the file at `:440`. For the **fail-loud** tests the
  stronger and correct assertion is that **staging is never invoked at all**
  (Decision 5), so assert on a non-calling sentinel for
  `_stage_pending_content` rather than merely on an empty directory.
- **Do not touch `server.py`.** It is shared with the manual
  `bin/gleipnir-approval-server` launch path.
- **Message quality is part of the acceptance, not polish.** AC-2 asserts the
  message **conjunctively**: the **verbatim captured cause** AND the **recovery
  guidance**. Asserting a weak keyword like `"key"` is explicitly insufficient —
  a generic "listener unavailable" string that passes a weak substring check
  recreates the defect one layer up, which is precisely what AC-2 now forbids.
- **One test must go through the real tool-dispatch boundary (AC-2b).** Not every
  test — but at least one, because Decision 4's entire premise is that the
  failure is unmistakable to the **actual** caller, and a bare
  `mcp_server.request_approval(...)` call cannot show that. Use
  `asyncio.run(mcp_server.mcp.call_tool("request_approval", {...}))`, mirroring
  the file's existing `asyncio.run(mcp_server.mcp.list_tools())` at `:143`. If
  the pinned SDK surfaces the failure as an `isError`-flagged result rather than
  a raised `ToolError`, assert on that form — the requirement is
  **distinguishability from a URL success plus cause-preservation**, not a
  specific class. If it turns out to be **indistinguishable**, STOP and escalate:
  that falsifies Decision 4 and is not yours to work around.
- **If a test is hard to write because state is global**, that is Decision 8:
  add the autouse reset fixture and the `reset()` seam — do not work around it
  with ordering assumptions.
- **Never add a pytest flag to the command.** `--profile broker` sets
  `test_selector_prefix = false`, and the CLI **refuses with exit 3** on any
  extra argument (`src/gleipnir/sandbox/__main__.py:131-139`) — you would run
  *nothing* and might read the silence as green. Order-independence is proved by
  in-file assertions (AC-7), never by `-p no:randomly`. Do **not** edit
  `profiles.toml` to make a flag work: it is Tier-3 and denied to you.
- **No `time.sleep` and no wall-clock assertion in the NEW startup /
  synchronisation tests** — i.e. AC-10 and any other new test touching listener
  startup or the listener→tool state handoff. AC-10's startup-window test
  synchronises with a `threading.Event` the test controls plus a
  `thread.join(timeout=...)`. The plan makes **no** timing claim (Decision 6), so
  no such test may assert one. **Scope, stated precisely** *(spec-review round 2
  note: round 1's "anywhere" was over-broad)*: this is **not** a
  whole-file ban on timestamps. The **pre-existing** T-2 envelope test
  legitimately brackets the staged timestamp —
  `before = int(time.time())` … `assert before <= envelope["staged_at"] <= after`
  (`tests/test_approval_mcp_server.py:218-230`) — which asserts the *envelope's
  recorded field*, not a synchronisation window. That is **correct, in scope, and
  must not be removed, weakened, or read as violating this rule**; it is outside
  this bullet entirely (and outside your permitted edits — see the
  existing-tests bullet above).
- **Report at the end:** the exact command run, pass/fail counts, and which of
  **AC-1, AC-2, AC-2b, AC-3, AC-3b, AC-4..AC-7, AC-7b, AC-8, AC-9, AC-10** each
  new/updated test satisfies. Do not self-declare done; the `quality` stage is a
  separate role (L-C8: never self-attest).

**For `quality-reviewer` (step 4).** Both passes run, each with its own recorded
verdict. `SPEC-CONFORM: PASS/FAIL` against this plan; then the adversarial
blast-radius pass, whose named probes are listed in Assemble step 4. Tag every
finding `[D]` (tool-produced — e.g. sandbox output, a `grep`) or `[J]`
(judgment). The honour check against the Design Intent below is **Important**
severity: a divergence blocks `git` and must be escalated to the operator, never
self-cleared.

**Routing note for the orchestrator.** This is the **full 8-stage pipeline**.
There is **no** negative-check attestation artifact for this plan (that artifact
belongs to the *hardened prose/config-only track*, which this plan is
disqualified from — see §Routing). `spec-review` and `quality` run as ordinary,
separate stages, which is the default and is stricter than the collapsed
single-pass light track.

---

## 7. Routing (derived, not assumed)

Per `.gleipnir/stage-role-map.md`, "Prose/config-only track", checked in order:

**Axis 1 — eligibility gate.** `P` = { `src/gleipnir/approval/mcp_server.py`,
`tests/test_approval_mcp_server.py` }. The disqualifier set `X` includes
`src/**`, `tests/**`, and `**/*.py`. **`P ∩ X = P`** — both paths are
disqualifiers three times over. The rule is explicit: *"If any path in `P`
matches the disqualifier set `X`, the plan runs the **full 8-stage pipeline**,
no matter how small the code portion."*

**Verdict: NOT prose/config-track eligible. FULL 8-stage pipeline**
(`brainstorm → plan → spec-review → test → code → quality → git → gate`; the
`brainstorm` stage is satisfied by the operator-directed split out of
`signer-uid-separation-brainstorm.md`, which is where F-1 was found and
converged as a bug rather than a design question).

**Axis 2 is not reached.** It routes only *track-eligible* plans between the
light and hardened paths. For completeness, had it been reached: no path in `P`
is in the enforcement-path set `E` (no `.gleipnir/agents|plugins|sandbox|policy|keys`,
not `stage-role-map.md`, not `opencode.jsonc`/`opencode.json`, and none of the
enumerated repo-root cross-cutting files `.gitignore`/`.envrc`/`pyproject.toml`/
`.gitattributes`/`.gitmodules`), and no added line matches the grant/enforcement
pattern `G` (no `permission:`/`tools:` block, no capability line, no
JSON enforcement key, no binding-table row, no 64-hex digest line). **So the
"hardened path" two-pass-plus-negative-check-attestation machinery does not
apply to this plan** — but note the full pipeline already gives `spec-review`
and `quality` as two distinct stages with distinct rubrics, which is not a
weakening.

**Cross-check against the source brainstorm:** the parent brief's own routing
note (`signer-uid-separation-brainstorm.md:990-995`) reaches the same
conclusion for the *larger* work via `opencode.jsonc` + `.gleipnir/plugins/**` +
`ansible/**`. This split-out fix hits `X` by a different door (`src/**`,
`tests/**`) and lands in the same place, but **without** the Tier-3/enforcement-
path coupling — which is precisely the benefit of the split.

**Confirmed: no Tier-3 edit is required by this plan at all.** Both wiring files
that would normally need an operator amendment for a test change
(`.gleipnir/sandbox/profiles.toml:60` and `tests/conftest.py:50`) **already
list this test file**. This is the direct payoff of Decision 7.

---

## 8. Design Principles (cognition Gate 1)

**Routing case: (i) OOP/functional code plan.** `P ∩ X ≠ ∅` and the touched
`X`-member (`mcp_server.py`) has module/function structure. All three
sub-analyses apply, plus the Design Intent.

### Design Intent (specific and falsifiable)

> **`mcp_server.py`'s `request_approval` must, as its first statement, consult
> the recorded listener state; and (a) whenever that consult *observes a
> recorded fatal refusal reason* it must refuse — raising, before any staging,
> and never returning a `/approve/<hash>` URL string; while (b) it must never
> refuse in the accepted benign case, because an `OSError` whose `errno` is
> exactly `errno.EADDRINUSE` **records no fatal reason at all**, leaving the
> state clear and the URL serveable.**

**The invariant is a state-read boundary, not a listener-liveness claim** — and
this scoping is deliberate, matching exactly what Decision 6 and AC-10 already
establish. The intent is **not** "no URL is ever returned when the listener has
terminated for a non-`EADDRINUSE` reason": that would be *broader* than the
implementation guarantees. A call can read a clear state, the listener can
**then** record its fatal reason and terminate, and that call still returns a
URL — the named, accepted residual (Decision 6, E-6) that **AC-10 asserts as a
positive case**. What the intent binds is the *observation*: once a fatal reason
is recorded and observed, refusal is mandatory and precedes staging. Any wording
that promises more than the state read can deliver is the round-1 timing
overclaim regrowing (Decision 6 withdrew it) and must be rejected.

This is falsifiable in both directions, and a reviewer can point at code that
violates it:

- Violated by *omission*: a `request_approval` whose first statement is not the
  state consult (e.g. staging happens first, or the check is inside
  `_build_approval_url`) — because then a fatal-state process still emits a URL,
  or emits litter before refusing.
- Violated by *over-reach in the refusing direction*: widening the fatal branch
  to swallow the accepted case (e.g. keeping a single `except Exception` that
  flips state unconditionally) — because then a genuine port conflict, where the
  URL **is** serveable by the already-bound manual listener, is wrongly refused,
  regressing Decision 19.
- Violated by *over-reach in the permitting direction* **(the round-1 defect,
  now an explicit violation clause)**: treating `OSError` as benign **by type**
  rather than by `errno` (e.g. `except OSError: logger.warning(...); return`, or
  an `errno` test widened to a set of codes) — because a `PermissionError`,
  `EADDRNOTAVAIL`, `EMFILE` or an `errno is None` `OSError` then silently yields
  live-looking URLs for a listener that never bound. **This is the same
  silent-failure class the plan exists to close, so a fix that reintroduces it
  under a different trigger fails its own intent.**
- Violated by *state design*: a state flag set anywhere other than
  `_run_listener`'s fatal branch, or readable without the lock, or with no reset
  seam — because then the invariant is not actually carried across the thread
  boundary, or cannot be isolated in tests.

The invariant names a concrete boundary (`OSError` **with
`errno == errno.EADDRINUSE`** records no fatal reason and is therefore benign;
everything else records one and is fatal), a concrete responsibility (the
URL-returning function must consult the recorded state before doing anything
else), and a concrete constraint (both directions, scoped to what the state read
can actually establish). **AC-2, AC-2b, AC-3, AC-3b, AC-5 and AC-10** together
are its arbiter: AC-2 catches omission, AC-2b catches omission *at the real
dispatch boundary*, AC-3 catches over-reach in the refusing direction, **AC-3b
catches over-reach in the permitting direction** (the round-1 defect), AC-5
catches default-refusal, and **AC-10 arbitrates the state-read boundary itself**
— asserting refusal after a fatal reason is recorded, *and* positively asserting
the accepted pre-record residual, so the intent cannot be read as the broader
liveness promise it deliberately is not.

### SOLID analysis

- **Single Responsibility.** Three new units, one reason to change each:
  `ApprovalListenerUnavailable` — *name the condition*; the state holder —
  *carry one boolean-plus-reason across a thread boundary safely*; the split
  catch in `_run_listener` — *classify a listener failure as benign or fatal*.
  `request_approval` gains one responsibility it arguably always should have had
  (*refuse when the URL it would return is meaningless*) and keeps its existing
  one (*stage and format*); the refusal is a single guard clause delegating the
  judgment to the state holder, not a second policy implementation inline.
- **Open/Closed.** The classification lives in exactly one place
  (`_run_listener`'s `except` chain). A future third failure class (say, a
  resolver-registration fault deserving its own treatment) is added by a new
  `except` clause plus a new state reason — with **no** change to
  `request_approval`, which consults an opaque "is there a refusal reason?"
  answer rather than switching on failure types itself.
- **Liskov Substitution.** `ApprovalListenerUnavailable` subclasses
  `RuntimeError`; it strengthens nothing and weakens nothing about
  `RuntimeError`'s contract, so any caller catching `RuntimeError`/`Exception`
  behaves correctly. `OSError` is caught for its stdlib meaning (an OS-level
  socket failure), not redefined.
- **Interface Segregation.** The state holder exposes exactly three operations
  (`mark_unavailable`, `refusal_reason`, `reset`). The listener thread uses only
  the first; the tool path only the second; tests only the third. No consumer is
  forced to know about the others. It is *not* a general "listener status"
  object with a lifecycle enum nobody needs.
- **Dependency Inversion.** `request_approval` depends on the *question*
  ("is there a refusal reason?") not on the *mechanism* (threads, exception
  types, `run_server`'s internals). It has no knowledge of `OSError`,
  `KeyUnavailable`, `load_key` or sockets — which is also what keeps the T-11
  boundary intact. The dependency direction (high-level tool → small local
  state abstraction ← low-level thread target) is correct.

### DRY analysis

- **No duplicated logic.** The benign/fatal decision exists in exactly one
  `except` chain. The refusal decision exists in exactly one guard clause.
  There is no second copy of the URL-building or staging logic — both continue
  to reuse `_build_approval_url` (`:107-121`) and `_stage_pending_content`
  (`:124-156`), which themselves already reuse `.server`'s
  `compute_change_hash`/`staged_path_for`/`default_token_dir` by contract
  (Decision 14 of the original launcher plan). This fix adds nothing to that
  surface.
- **Existing helpers reused, not reimplemented.** `logger` (`:88`),
  `threading` (`:73`) and `Optional` (`:76`) are already imported and are
  **reused, not re-derived** — so the fix adds **exactly one** new import,
  `import errno` (stdlib), and no others *(spec-review round 2 note: this bullet
  previously said "no new imports at all", which was round-1 wording that
  Decision 3 superseded — `errno` is the one legal new import, and it is the
  minimum needed to name `EADDRINUSE` symbolically instead of duplicating a
  magic number)*. Nothing from `..verify.marker`, `.token`, or any third party.
  The `reset()` test seam follows the **existing**
  injectable-seam convention already used by `token_dir=` (`:129,140-141`)
  rather than inventing a new test hook style.
- **No repeated constants.** The refusal message is built in one place; the
  exception class name is referenced from one `raise` and one test import. The
  existing `_APPROVAL_BASE_URL_ENV` named-constant pattern (`:104`) is followed
  if any new literal is needed.
- **Tests:** the new T-12 class reuses the file's established fixtures and
  patterns (`monkeypatch.delenv`, `caplog.at_level`, `tmp_path`, direct
  `_run_listener` calls for determinism, `:404-441`) rather than introducing a
  parallel harness. The autouse reset fixture removes what would otherwise be
  copy-pasted setup in every test.

### Single Responsibility check (named, per component)

| Component | Its single responsibility |
|---|---|
| `ApprovalListenerUnavailable` | Name the "no in-process listener can honour a review URL" condition as a distinct, catchable type |
| listener-state holder | Carry one refusal-reason value across the listener-thread → main-thread boundary, safely and resettably |
| `_run_listener`'s `except` chain | Classify a listener failure as benign (socket bind) or fatal (everything else) |
| `request_approval`'s new guard clause | Refuse before doing any work when the state says a URL would be meaningless |
| `_stage_pending_content` (unchanged) | Write the staging envelope |
| `_build_approval_url` (unchanged) | Format the review URL exactly as `buildApprovalUrl` does |
| autouse reset fixture | Isolate module-level state between tests |

No component here has two reasons to change. Nothing was split further because
every unit above is already a single verb.

---

## 9. Honesty ledger (what this fix does NOT do)

Recorded so this cannot later be mistaken for more than it is — the discipline
the parent brainstorm's mitigations #1/#2 demand of anything split out of F-1.

- **It delivers ZERO key confidentiality and ZERO OS isolation.** The signer
  still runs as a child of opencode and therefore still shares the agent's uid
  (`opencode.jsonc:91-100`). Nothing about that changes here.
- **It does NOT close O-3(b)**, and does not make caged mode *work* — under
  caged mode the **in-process** listener spawned by this MCP is still
  **non-functional**. This fix makes that non-functionality **loud and
  diagnosable** instead of silent. That is the entire claim. Scoped precisely
  *(spec-review round 2 reconciliation, matching Decision 13)*: what remains
  broken until the separate signer-uid work lands is that **this MCP's
  `request_approval` tool will not mint or make available a URL via the
  in-process listener** under caged mode. This is **not** a claim that caged mode
  cannot mint approvals at all — a **separately run manual
  `bin/gleipnir-approval-server` listener at another uid, if healthy, is
  unaffected** and can still mint; that is exactly why Decision 13's refusal is a
  *false* refusal rather than an accurate one. Any wider claim here would
  contradict Decision 13.
- **It does NOT address the adjacent armed-pipeline collision.**
  `sequence-gate.ts` and `advance-hook.ts` hit the same caged key-read wall
  (brainstorm §F-1, item 8 — which that brief records as having **no home
  yet**). Still homeless after this plan. Deliberately not claimed.
- **It does NOT fix the E-4 false refusal** (a manual listener at another uid is
  still refused) — Decision 13, named with its remedy and left out of scope.
- **`src/gleipnir/approval/**` coverage remains unmeasured** — Decision 14.

---

## 10. Material tradeoffs surfaced to the operator

**None.** As the delegation anticipated, this is a bounded fix of
uncontroversial shape. The one material tradeoff in the vicinity — *fail loud vs
fail silent on key-unavailability* — was **already settled by the operator** by
directing this as an urgent bug fix rather than a design question, and is
recorded as such rather than re-litigated here.

Two items are surfaced as **flags, not decisions requiring convergence**:

1. **Decision 9** — whether `plans/tier3-mcp-approval-launcher.md`'s Decision 19
   text gets a one-line annotation, and whether the refinement earns a durable
   line in `decisions/tier3-signed-approval.md` (Tier-3, operator-only). I
   recommend the annotation and did **not** perform it.
2. **Decision 13** — the E-4 false-refusal residual. Classified NOT material
   (fail-closed direction, trivially reversible, directly implied by the
   operator's directive), but named explicitly with its remedy so spec-review
   can escalate it if it disagrees with that classification.

Seven `[PLAN-STAGE JUDGMENT]` rows (Decisions 1, 2, 4, 5, 6, 7, 8) are
implementation-shape calls made here and flagged for `spec-review`, per the
convention that the planner records shape decisions in the enforced artifact
rather than leaving them to be discovered in the diff.
