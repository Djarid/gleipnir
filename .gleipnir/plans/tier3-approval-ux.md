# Plan: Tier-3 Approval UX — staging, review page, URL discovery, manual retry

> **Source brief:** `.gleipnir/plans/tier3-approval-ux-brainstorm.md` (STATUS:
> CONVERGED — A=A1 staging, B review+diff page, C=C2 configured base URL,
> D=manual retry). This plan does NOT re-decide those four; it plans the bounded
> implementation *from* them. Any `[PLAN-STAGE JUDGMENT]` rows below are the
> narrow implementation details the brief explicitly left to the plan/code stage
> (`## Open Questions`), not reopened convergence.
>
> **Purely additive to an already-correct, already-tested crypto core.** Zero
> edits to `src/gleipnir/approval/token.py`, `gate.py`, `__main__.py`,
> `identity/**`. Read-and-confirmed unchanged this session; cited as fixed
> anchors below.

## GOTCHA pre-flight (visible)

- **Goals checked** (`.gleipnir/goals/manifest.md`): Plan format
  (`plan-format.md`) — this plan follows it (Decisions index + Architect +
  Trace + Link + Assemble + Stress-test + Execution Workflow + Design
  Principles). Methodology (ATLAS/GOTCHA ahead of planning) — satisfied: ATLAS
  Architect/Trace done to disk before any code. Brainstorm-first — satisfied:
  the converged brief exists and is the source.
- **Order confirmed:** plan-before-code. The pre-written tests are authored
  before the implementation (test-first, Axiom 1); `server.py` is the arbiter's
  subject, the `.ts` change is operator/build-mode applied.
- **Gap check:** no missing goal. One material tradeoff (staged-content origin,
  sub-decision A) was already surfaced to and converged by the operator in the
  brief — NOT re-decided here. No NEW material tradeoff is introduced by this
  plan (see the closing report). The `[PLAN-STAGE JUDGMENT]` rows are
  implementation details the brief delegated, not convergence.
- **GOTCHA layering:** Goals = "review-then-one-click == what-you-sign"; the
  Orchestration/enforcement layer (the hook + gate CLI) is unchanged in
  contract; this plan touches only the Tools/Context edges (a staging file, a
  GET route). No layer-2 (G-5) change; no new guard (per brief's hardened-path
  note).

## Decisions (index)

Only `[PLAN-STAGE JUDGMENT]` rows — the four brief-level decisions (A1/B/C2/D)
are converged and cited, not re-decided.

| # | Decision | Chosen | Rejected | Rationale |
|---|----------|--------|----------|-----------|
| P1 | **Staged-file JSON shape** for `pending-<hash>.json` | Small envelope `{content, filePath, tool, staged_at}` — `content` is the exact resulting string; `filePath` is the Tier-3 target (for the diff); `tool` and `staged_at` are context only | Raw-content-only file (no envelope) | The review page needs `filePath` to diff against on-disk, and `tool`/`staged_at` to show context. `content` is the ONLY field the hash/mint touches; the others are display-only. Keeps the file a transient Tier-0 vehicle, not a Gleipnir artifact (brief constraint). |
| P2 | **Hash-encoding confirmation** (TS `sha256` == Python `sha256`) byte-for-byte | TS computes `createHash("sha256").update(resultingContent, "utf8").digest("hex")`; the staged `content` is written/read as UTF-8; `server.py` re-hashes `content.encode("utf-8")` | Hashing a JSON-serialized envelope; hashing with a non-UTF-8 encoding | **Confirmed against real source:** `__main__.py:_compute_change_hash` = `sha256(content_path.read_bytes())`; the hook writes `--content-file` via `writeFileSync(contentFile, resultingContent)` (Node default UTF-8). So the mint-time byte-string is UTF-8(`resultingContent`). TS staging hash and server re-hash MUST use the identical UTF-8 byte-string or the staged-file name, the URL, and the minted token's `change_hash` diverge. This is the load-bearing what-you-see-is-what-you-sign invariant. |
| P3 | **Form-POST mechanics** (how staged bytes reach the mint path) | Server re-reads the staged file **by `<hash>`** on POST; the form carries only the `<hash>` (a hidden input / hash-scoped POST target `POST /approve/<hash>`), NOT the full content | Hidden `<input>` round-tripping the full content back in the form body | Avoids re-transmitting large content; the staged file already holds the exact bytes keyed by `<hash>`; re-reading by hash is simpler and removes a tamper surface (operator can't edit a hidden field). Existing `POST /approve` (raw-body) path is **kept unchanged**; the new `POST /approve/<hash>` is an additive sibling that reads the staged `content` then calls the SAME `capture_approval` core. |
| P4 | **HTML escaping** of staged bytes on render | `html.escape(content, quote=True)` (stdlib) for both the raw-content block and every diff line; the on-disk base file is escaped identically | Rendering raw bytes; escaping only `<`/`>` | Brief's new-risk check: staged files are untrusted display input. `html.escape` with `quote=True` neutralizes `< > & " '`. stdlib-only. Escaping does NOT touch the bytes that get hashed/minted — only the display copy — preserving what-you-sign. |
| P5 | **Diff rendering** | `difflib.unified_diff` (stdlib) between the current on-disk `filePath` bytes (decoded UTF-8, `errors="replace"`) and the staged `content`; if the target file is absent, show "new file" and skip the diff | A third-party diff lib; a char-level diff | stdlib-only (brief constraint); unified diff is the standard review shape; absent-file is a real case (creating a new Tier-3 file). Diff is display-only — never an input to the hash. |
| P6 | **`GET /approve/<hash>` routing within existing `do_GET`** | Extend `do_GET` to parse a `/approve/<hash>` path prefix; keep `/` and `/approve` (exact) serving the existing instructions page unchanged | A separate handler class; a regex router framework | Minimal, additive, stdlib — matches the existing thin-edge `do_GET` shape. The exact-match `/approve` (POST-target instructions) is preserved; only the `/approve/<hash>` GET and `/approve/<hash>` POST are new. |
| P7 | **Missing-staged-file case** | `GET /approve/<hash>` with no `pending-<hash>.json` → 404 with a clear text/HTML message ("no staged change for this hash — it may be stale, already approved, or the URL is wrong"). `POST /approve/<hash>` with no staged file → 404 likewise (never mints) | Silent empty page; 200 with blank content | Fail-closed and legible: the operator navigated to a stale/wrong URL; never mint against absent content. |
| P8 | **Env-var name + fallback wording** (C2 detail) | `GLEIPNIR_APPROVAL_BASE_URL`; if set → `Approve at: <base_url>/approve/<hash>`; if unset → `Approve at: <your approval listener>/approve/<hash> (set GLEIPNIR_APPROVAL_BASE_URL to show the full URL here)` | A required env var (hard-fail if unset) | The brief's working name, made concrete. Graceful relative-hint fallback is a brief requirement (never block the refusal on missing config). Trailing-slash normalization: strip one trailing `/` from `base_url` before joining. |

## Architect

**Problem (one sentence):** Replace the error-prone manual `curl`-the-exact-bytes
Tier-3 approval step with a review-then-one-click flow, by staging the exact
resulting bytes the hook already computed on REFUSE and serving a review+diff
page whose one-click form mints against those exact staged bytes.

**User:** the operator, who (today) must obtain byte-identical pending content
and POST it by hand; and the acting agent (`tier3-writer` or any agent whose
Tier-3 write was refused), which reports the refusal message verbatim and
retries after approval.

**Measurable success criteria:**

1. On a Tier-3-path `write` REFUSE, a file
   `.gleipnir/var/tmp/pending-<change_hash_hex>.json` exists, whose `content`
   field's UTF-8 bytes hash (sha256) to exactly `<change_hash_hex>`.
2. The `<change_hash_hex>` in the staged filename equals the TS-computed
   `sha256(resultingContent, utf8)` AND equals what the gate CLI / `server.py`
   compute over the same bytes — byte-for-byte (P2).
3. `GET /approve/<hash>` returns 200 rendering the staged `content`
   (HTML-escaped) and, when the target file exists on disk, a unified diff;
   returns 404 with a clear message when no staged file exists (P7).
4. Submitting the page's form mints a token whose `change_hash == sha256(X)`
   where `X` is the exact staged bytes the page rendered — proven end-to-end.
5. The refusal message includes a ready-to-visit URL when
   `GLEIPNIR_APPROVAL_BASE_URL` is set, and a graceful relative hint when unset
   (P8).
6. Zero edits to `token.py`, `gate.py`, `__main__.py`, `identity/**`; the
   existing `POST /approve` raw-body path and `capture_approval` core are
   unchanged (used, not modified).

**Constraints (carried from brief, not re-litigated):** stdlib-only (no new
Python dependency); Node stdlib only (`node:crypto`, `node:fs`) for the `.ts`
change; tailnet-only transport unchanged; crypto core untouched; the hook must
reuse the existing `resultingContentFor`, never duplicate write-vs-edit logic;
`.gleipnir/plugins/**` remains agent-unwritable (hook applied by
operator/build-mode only, hardened path).

## Trace

### Artifacts and where they live (source of truth)

**A. `.gleipnir/plugins/tier3-gate.ts`** — Tier-3 enforcement code (Tier-3 path
set `E`; **operator/build-mode applied, hardened path** — NOT a `gleipnir-code`
write). Additive changes ONLY inside the existing refuse path; no change to
`resultingContentFor`, `runGateCheck`, `decideFromExit`'s core contract, or
`isTier3Path`.

New helpers + wiring (exact layout):

- `import { createHash } from "node:crypto"` and `import { mkdirSync }`
  (extend the existing `node:fs` import list; `writeFileSync` already imported).
- `const STAGING_DIR_REL = ".gleipnir/var/tmp"` (the Decision-17 Tier-0 dir —
  same dir the token lands in; reuse the existing `TOKEN_DIR_REL` constant value
  or add a parallel named constant — implementation may alias
  `TOKEN_DIR_REL`).
- `export function computeChangeHash(resultingContent: string): string` —
  `return createHash("sha256").update(resultingContent, "utf8").digest("hex")`.
  **P2:** `"utf8"` is mandatory and must byte-match
  `__main__.py:_compute_change_hash` (`sha256(read_bytes())` where the bytes
  were written by `writeFileSync(contentFile, resultingContent)`, Node default
  UTF-8). Exported for the unit test.
- `export function stagePendingContent(directory, tool, filePath,
  resultingContent): string` — computes the hash, builds the envelope
  `{content: resultingContent, filePath, tool, staged_at: <epoch seconds>}`
  (P1), `mkdirSync(stagingDir, {recursive:true})`, writes
  `pending-<hash>.json` via `writeFileSync(path, JSON.stringify(envelope))`,
  returns the `<hash>`. NOTE: the envelope's `content` field preserves the exact
  string; JSON-encoding the envelope does NOT change what gets hashed — the hash
  is over `resultingContent` itself (P2), and the server re-hashes the envelope's
  `content` field, never the serialized envelope. Exported for the unit test.
- `export function buildApprovalUrl(hash: string): string` — reads
  `process.env.GLEIPNIR_APPROVAL_BASE_URL`; returns the full or relative-hint
  message tail per P8. Exported for the unit test (env-var toggling).
- **NEW subclass `export class GateRefused extends Tier3GateAbort {}`** —
  parallel to the existing `PreflightUnavailable extends Tier3GateAbort`. This
  is the exact classification mechanism that distinguishes a genuine policy
  refusal (from the gate CLI's non-zero exit) from every OTHER `Tier3GateAbort`
  (broken prerequisite `PreflightUnavailable`, or a content-uncomputable throw
  from `resultingContentFor` for `edit` / no-string-`content`, or the
  no-`filePath` throw). `decideFromExit` is changed to throw `GateRefused`
  (instead of a bare `Tier3GateAbort`) on the non-zero-exit branch — its
  return-`"allow"`-on-0 contract and its `REFUSED` message text are unchanged
  (the existing `test_tier3_gate.mjs` `/REFUSED/` assertions still pass because
  `GateRefused` is a `Tier3GateAbort` subclass carrying the same message).
  Exported for the unit test.
- **Wiring point:** the ONLY behavior change is inside the existing
  `tool.execute.before` `catch (err)` block. Currently that block rethrows any
  `err instanceof Tier3GateAbort` unchanged and wraps anything else. The change:
  **the staging branch keys off the NEW subclass, not off "any Tier3GateAbort"**
  — `if (err instanceof GateRefused) { const hash =
  stagePendingContent(directory, input.tool, filePath, resultingContent);
  throw new GateRefused(<original message> + " " + buildApprovalUrl(hash)); }`
  then the existing `if (err instanceof Tier3GateAbort) throw err` handles all
  the non-refusal aborts (PreflightUnavailable, edit/no-content throws) with NO
  staging. Because `resultingContent` is computed at `const resultingContent =
  resultingContentFor(...)` (line ~325, BEFORE `runGateCheck`), it is in scope
  in the `try`; but on any path where that call itself threw (edit,
  no-string-content), control never reached `runGateCheck`/`decideFromExit`, so
  no `GateRefused` is ever produced and the `instanceof GateRefused` branch is
  not taken. **Design constraint (now mechanically pinned, not "confirm at
  build"):** staging happens ONLY when `err instanceof GateRefused` — i.e. ONLY
  on a genuine policy REFUSE from the gate CLI — NEVER on `PreflightUnavailable`
  (broken interpreter), NEVER on `resultingContentFor`'s throw for `edit`, and
  NEVER on the no-`filePath`/no-string-`content` fail-closed throws. See edge
  cases E1–E3.

**B. `src/gleipnir/approval/server.py`** — ordinary `src/**`; `gleipnir-code`
build+test, full 8-stage pipeline. Additive:

- `import html` and `import difflib` (stdlib; extend the existing import block).
- `def staged_path_for(token_dir: Path, change_hash: str) -> Path:` returns
  `token_dir / f"pending-{change_hash}.json"`. NOTE the FULL hash (matches the
  hook's `pending-<hash>.json`), distinct from `token_path_for`'s 16-char
  prefix for the minted token — do not conflate.
- `def load_staged(token_dir, change_hash) -> dict | None:` reads + JSON-parses
  the staged envelope; returns `None` if absent/unparseable (→ 404). Pure,
  unit-testable. **Explicit UTF-8 read (REQUIRED, not implicit):** it MUST read
  the file as `staged_path_for(...).read_bytes()` then `json.loads(raw)`
  (`json.loads` accepts bytes and decodes UTF-8 per the JSON spec), OR
  `read_text(encoding="utf-8")` — NEVER a bare `Path.read_text()` with no
  encoding argument, whose decode is locale/platform-dependent and could corrupt
  multibyte content before it is hashed. This mirrors the hook's UTF-8
  `writeFileSync(path, JSON.stringify(envelope))` and is the Python side of the
  P2 byte-identity contract. The `read_bytes()` + `json.loads` form is preferred
  (it makes the UTF-8 decode the JSON parser's responsibility, matching how
  `JSON.stringify` emitted the bytes).
- `def render_review_page(envelope: dict, current_on_disk: bytes | None) -> bytes:`
  the pure HTML builder — HTML-escapes `envelope["content"]` (P4), builds the
  `difflib.unified_diff` against `current_on_disk` decoded UTF-8
  `errors="replace"` (or "new file" if `current_on_disk is None`, P5), and
  emits the `<form method="POST" action="/approve/<hash>">` with a single
  submit button (P3 — no content in the form; the hash is in the action URL).
  Pure, fully unit-testable (no sockets).
- `do_GET` extension (P6): if `self.path` matches `/approve/<hash>` (prefix
  parse, `<hash>` = the trailing path segment), resolve `token_dir` (same
  default as minting), `load_staged`; 404 (P7) if absent; else read the
  on-disk `envelope["filePath"]` bytes if the file exists (else `None`), call
  `render_review_page`, send 200 text/html. `/` and exact `/approve` unchanged.
- `do_POST` extension (P3): if `self.path` matches `/approve/<hash>`,
  `load_staged`; 404 if absent (never mint, P7); else call the EXISTING
  `capture_approval(..., pending_content=envelope["content"].encode("utf-8"),
  ...)` — reusing the unchanged core — and respond with the same 200/403 JSON
  shape the existing `POST /approve` uses. The existing exact `/approve`
  raw-body POST branch is preserved unchanged (P3).

**C. Staged file** `.gleipnir/var/tmp/pending-<change_hash_hex>.json` — Tier-0,
gitignored/disposable. Written by the hook (A), read by the server (B). Input to
review, never authority (authority is the HMAC token minted by `capture_approval`).

**D. Tests** (see Assemble for test-first order):
- `tests/test_tier3_gate.mjs` — extended (not replaced) with unit tests for
  `computeChangeHash`, `stagePendingContent`, `buildApprovalUrl`, and the
  staging-on-refuse wiring, using the existing `makeRepoWithStub`/temp-dir
  conventions.
- `tests/test_approval_server.py` — extended with tests for `staged_path_for`,
  `load_staged`, `render_review_page`, and the new POST-by-hash core path, using
  the existing injectable-core convention.
- **E2E conformance** — a new test (location: extend `test_approval_server.py`
  for the Python half; the cross-language byte-identity assertion is expressed
  as a Python-side sha256 over the same UTF-8 bytes the hook would stage). Proves
  what-you-see-is-what-you-sign: stage `X` → GET renders `X` → POST → minted
  token's `change_hash == sha256(X_utf8)`.

### Integrations map

```
Tier-3 write attempt (any agent)
  └─ tier3-gate.ts tool.execute.before
       ├─ isTier3Path? no → pass-through (UNCHANGED)
       └─ yes → resultingContentFor (UNCHANGED) → runGateCheck (UNCHANGED)
            ├─ decideFromExit(0) → allow (UNCHANGED)
            ├─ decideFromExit(non-zero) → throw GateRefused              [NEW subclass]
            │    └─ catch (err instanceof GateRefused):                  [NEW branch]
            │         ├─ stagePendingContent → var/tmp/pending-<hash>.json  [NEW]
            │         └─ throw GateRefused(msg + buildApprovalUrl(hash))     [NEW msg]
            └─ PreflightUnavailable / resultingContentFor-throw (edit, no-content):
                 └─ catch (err instanceof Tier3GateAbort) throw err → NO STAGING (UNCHANGED)
Operator visits GLEIPNIR_APPROVAL_BASE_URL/approve/<hash>
  └─ server.py do_GET /approve/<hash>
       ├─ load_staged → None → 404 (P7)                                          [NEW]
       └─ render_review_page (escaped content + unified diff + form)             [NEW]
Operator clicks Approve
  └─ server.py do_POST /approve/<hash>
       ├─ load_staged → None → 404                                              [NEW]
       └─ capture_approval(pending_content = content.encode utf-8)  (CORE UNCHANGED)
            └─ mint token, change_hash == sha256(content_utf8)  (token.py UNCHANGED)
Agent retries the SAME write within 180s → gate finds fresh token → ALLOW (D)
```

### Edge cases

- **E1 — REFUSE is a policy REFUSE, not a broken prerequisite.** Staging happens
  ONLY when the caught error `instanceof GateRefused` (the NEW subclass
  `decideFromExit` throws on the gate CLI's non-zero exit). A
  `PreflightUnavailable` (missing/non-exec interpreter) is a `Tier3GateAbort`
  but NOT a `GateRefused`, so it falls through to the existing
  `instanceof Tier3GateAbort` rethrow with NO staging (there is no meaningful
  content-review to offer — the gate could not even run). The `instanceof`
  discrimination is the mechanism; it is not left to build-time judgment.
- **E2 — `edit` to a Tier-3 path.** `resultingContentFor("edit", ...)` throws a
  `Tier3GateAbort` (not `GateRefused`) before any content exists and before
  `runGateCheck`/`decideFromExit` are reached; there is nothing to stage and no
  hash. It falls through the `instanceof Tier3GateAbort` rethrow — no staging.
  The refuse message stays the existing edit-refusal (use `write`).
- **E3 — `write` with no string `content`.** `resultingContentFor` throws a
  `Tier3GateAbort` (not `GateRefused`); no content, no `GateRefused`, no
  staging. Fail-closed as today.
- **E4 — stale/duplicate staged file.** Same content → same hash → same
  filename (idempotent overwrite; harmless). Different pending write → different
  hash → different file. No cross-contamination by construction (hash-keyed).
- **E5 — staged file present, target file absent on disk** (creating a new
  Tier-3 file). `render_review_page` shows "new file (no on-disk base to diff
  against)" and renders the full staged content; POST still mints normally.
- **E6 — untrusted staged content in the review page.** `html.escape(...,
  quote=True)` on the content and every diff line (P4). A staged file with
  embedded `<script>` renders inert. Escaping is display-only; the hashed bytes
  are the raw `content`.
- **E7 — malformed `<hash>` in the URL** (non-hex / wrong length). `load_staged`
  finds no matching file → 404 (P7). No path traversal: build the staged path
  as `token_dir / f"pending-{hash}.json"` only after validating `<hash>` is
  `[0-9a-f]{64}` (reject otherwise → 404), so a `../` segment can never reach
  the filesystem join.
- **E8 — large content in the form.** P3 avoids round-tripping content in the
  form body (hash-scoped POST re-reads the staged file), so form size is O(1)
  regardless of content size.

## Link (validated before building)

- **Read and confirmed unchanged (fixed anchors):** `token.py`
  (`mint_approval`, `compute`/`_canonical_signing_input`), `gate.py` via
  `__main__.py` (`_compute_change_hash = sha256(read_bytes())`),
  `identity/**` (via `capture_approval`'s `resolve` injection). These are NOT
  edited.
- **Confirmed the hash byte-string (P2, the load-bearing check):**
  `server.py:compute_change_hash(content: bytes)` = `sha256(content).hexdigest()`;
  `capture_approval` mints over `compute_change_hash(pending_content)`; the hook
  today writes `--content-file` via `writeFileSync(contentFile, resultingContent)`
  (Node default UTF-8) and the CLI hashes `read_bytes()` of that file. Therefore
  the canonical byte-string is **UTF-8(`resultingContent`)** and every party
  (TS staging hash, server GET/POST re-hash, gate CLI) must hash exactly those
  bytes. Verified by reading all three files this session.
- **Confirmed the reusable core:** `capture_approval` takes
  `pending_content: bytes` and mints + writes the token; the new POST path calls
  it UNCHANGED with `envelope["content"].encode("utf-8")`.
- **Confirmed test conventions:** `test_tier3_gate.mjs` uses temp-dir +
  stub-`.venv/bin/python` + real-hook (`makeRepoWithStub`, `runBefore`);
  `test_approval_server.py` uses injectable-core (`capture_approval` with fake
  `resolve`, `tmp_path` token_dir). Both are EXTENDED, not replaced.
- **Confirmed routing/tier:** `.gleipnir/plugins/**` ∈ `E` (hardened path,
  operator-applied); `src/**` ∈ Axis-1 disqualifier `X` (full 8-stage pipeline).

## Assemble (build order — test-first; operator/build vs gleipnir-code split explicit)

Two independently-buildable halves. The `.py` half is fully test-first and
`gleipnir-code`-owned; the `.ts` half is operator/build-mode applied on the
hardened path. The E2E conformance case bridges them (Python-side byte-identity
proof).

1. **[gleipnir-code] Write the failing Python unit tests** in
   `tests/test_approval_server.py` (extend): `staged_path_for` (full-hash name),
   `load_staged` (present → dict; absent/malformed → None), `render_review_page`
   (escapes content; includes a unified diff when base bytes given; "new file"
   when None; embeds `<form action="/approve/<hash>">`; HTML-escapes a
   `<script>` payload), and the POST-by-hash core: staging a dict then calling
   the mint path yields a token whose `change_hash == sha256(content_utf8)`.
   Red.
2. **[gleipnir-code] Write the failing E2E conformance test**
   (`test_approval_server.py`): stage envelope with content `X` → `load_staged`
   → `render_review_page` renders `X` (escaped) → drive `capture_approval` over
   `X.encode("utf-8")` → assert `token.change_hash == sha256(X_utf8).hexdigest()`
   and the rendered page contains the (escaped) `X`. Red.
3. **[gleipnir-code] Implement `server.py`** additively: `staged_path_for`,
   `load_staged`, `render_review_page`, `do_GET` `/approve/<hash>` branch,
   `do_POST` `/approve/<hash>` branch, imports (`html`, `difflib`), hash
   validation (E7). Run tests → green. Existing tests stay green (regression).
4. **[gleipnir-code] Extend `tests/test_tier3_gate.mjs`**
   (this test file is `tests/**`, so a `gleipnir-code` delegation MAY author the
   test; but it imports the Tier-3 `.ts` module, so it is RED until step 5 is
   operator-applied — mirror the existing "expected red at import until the
   operator applies the plugin" note already in that file). Add unit tests for
   `computeChangeHash` (asserts a known UTF-8 sha256 vector), `stagePendingContent`
   (writes `pending-<hash>.json`, envelope shape, hash keys the filename),
   `buildApprovalUrl` (env set vs unset wording, trailing-slash strip), a test
   that `decideFromExit(non-zero)` throws an error that is `instanceof
   GateRefused` (and `decideFromExit(0)` still returns `"allow"`), and a
   staging-on-refuse integration test keyed on the `GateRefused` discrimination:
   stub CLI exits non-zero → the thrown error is `GateRefused`, the staged file
   appears, AND the thrown message contains the URL; stub exits 0 → no staged
   file; `edit` (a `Tier3GateAbort` that is NOT `GateRefused`) → no staged file;
   `PreflightUnavailable` (missing/non-exec interpreter, a `Tier3GateAbort` that
   is NOT `GateRefused`) → no staged file (E1/E2, and S3/S12 below).
5. **[operator/build — HARDENED PATH] Apply the `tier3-gate.ts` change** — the
   NEW `GateRefused extends Tier3GateAbort` subclass, `decideFromExit` throwing
   `GateRefused` on non-zero exit, `computeChangeHash`, `stagePendingContent`,
   `buildApprovalUrl`, and the `catch (err instanceof GateRefused)` staging
   branch. Because `.gleipnir/plugins/**` ∈ `E`, no agent (not `gleipnir-code`)
   writes this file; it is operator/build-mode applied exactly like the original
   plugin, and routed through the hardened path (two reviewer passes +
   negative-check attestation, per `stage-role-map.md`). The negative-check
   attestation must specifically confirm staging is reachable ONLY via
   `instanceof GateRefused`, never via a bare `Tier3GateAbort`. After
   application, `node --test tests/test_tier3_gate.mjs` should go green.
6. **[gleipnir-code + operator] Integration confirmation:** with the plugin
   applied and the server running, a real Tier-3 `write` REFUSE stages a file,
   the URL resolves to a review page rendering the exact bytes, and the form
   mint yields a token that the gate then ALLOWs on retry (success criterion 4,
   end-to-end).

**Build-order summary:** Python tests (1,2) → Python impl (3) → TS tests (4) →
TS apply (5, operator/hardened) → E2E integration (6).

## Stress-test (concrete numbered acceptance criteria)

1. **S1 (hash byte-identity, P2):** For content `X = "α<b>\n"` (multibyte +
   markup + newline), `computeChangeHash(X)` (TS, utf8) ==
   `hashlib.sha256(X.encode("utf-8")).hexdigest()` (Python) ==
   `compute_change_hash(X.encode("utf-8"))` — all three equal, exact hex.
2. **S2 (staging on REFUSE only):** stub gate exits 1 → `pending-<hash>.json`
   exists with `{content: X, filePath, tool:"write", staged_at:<int>}` and the
   thrown message contains `/approve/<hash>`. Stub exits 0 → NO staged file.
3. **S3 (no staging for edit / preflight-fail):** `edit` to a Tier-3 path →
   throws, NO staged file. Missing interpreter (`PreflightUnavailable`) →
   throws, NO staged file (E1/E2). See S12 for the mechanism-level assertion.
4. **S4 (URL message, P8):** `GLEIPNIR_APPROVAL_BASE_URL=https://h.ts.net/`
   → message tail `Approve at: https://h.ts.net/approve/<hash>` (one trailing
   slash stripped). Unset → `Approve at: <your approval listener>/approve/<hash>
   (set GLEIPNIR_APPROVAL_BASE_URL to show the full URL here)`.
5. **S5 (review renders exactly the staged bytes):** `GET /approve/<hash>` for
   staged content `X` returns 200 whose body contains `html.escape(X,
   quote=True)` — and does NOT contain an un-escaped `<script>` if `X` embeds
   one (E6).
6. **S6 (diff present / new-file):** when `envelope["filePath"]` exists on disk
   with different bytes, the page contains a `difflib.unified_diff` block; when
   absent, it says "new file" and shows full content, no diff crash (E5).
7. **S7 (404 on missing/stale/malformed hash, P7/E7):** `GET /approve/<hash>`
   and `POST /approve/<hash>` with no staged file → 404 clear message, no mint.
   A non-`[0-9a-f]{64}` `<hash>` (incl. a `../` attempt) → 404, never touches
   the filesystem join.
8. **S8 (what-you-see-is-what-you-sign, E2E, success criterion 4):** stage `X`
   → GET renders `X` → `POST /approve/<hash>` → minted token file exists and
   `token.change_hash == sha256(X_utf8).hexdigest()` — the exact bytes rendered
   are the exact bytes signed.
9. **S9 (core reuse / no regression):** the existing `POST /approve` raw-body
   path, `capture_approval`, `token_path_for`, `compute_change_hash`, and all
   existing `test_approval_server.py` + `test_tier3_gate.mjs` cases still pass
   unchanged.
10. **S10 (zero crypto-core edits):** `git diff` touches only
    `.gleipnir/plugins/tier3-gate.ts`, `src/gleipnir/approval/server.py`,
    `tests/test_tier3_gate.mjs`, `tests/test_approval_server.py` — never
    `token.py`, `gate.py`, `__main__.py`, `identity/**`.
11. **S11 (large content, P3/E8):** a 1 MB staged content produces a form whose
    POST body is O(1) (carries only the hash), and the mint still binds the full
    1 MB.
12. **S12 (staging keyed strictly on `GateRefused`, not any `Tier3GateAbort`):**
    (a) `decideFromExit(non-zero)` throws an error that is `instanceof
    GateRefused` (and `instanceof Tier3GateAbort`); `decideFromExit(0)` returns
    `"allow"`. (b) On a stub gate exiting non-zero, the caught error is
    `GateRefused` AND a staged file appears. (c) On `PreflightUnavailable`
    (missing/non-exec interpreter — a `Tier3GateAbort` that is NOT `GateRefused`)
    NO staged file appears. (d) On an `edit` to a Tier-3 path (a `Tier3GateAbort`
    from `resultingContentFor`, NOT `GateRefused`) NO staged file appears. This
    proves the discrimination is by subclass, not by "any abort", closing the
    review's "outer catch treats all Tier3GateAbort the same" gap.
13. **S13 (cross-language JSON round-trip fidelity, multibyte/astral):** stage
    content `X` containing a genuine astral-plane character (e.g. `X = "emoji
    ✅🔐\n multibyte αβγ"` — a 4-byte-encoded emoji plus BMP multibyte) through
    the REAL path, not a shortcut: TS `JSON.stringify({content: X, ...})` →
    write to disk (UTF-8) → Python `load_staged` (`read_bytes()` + `json.loads`)
    → `envelope["content"].encode("utf-8")` → `compute_change_hash(...)`. Assert
    the resulting hash EQUALS both `computeChangeHash(X)` (TS, utf8, S1's direct
    path) and `hashlib.sha256(X.encode("utf-8")).hexdigest()` (Python direct
    path). This exercises the actual `JSON.stringify → disk → json.loads`
    envelope round trip that S1/S8 bypass (S1 hashes `X` directly; S8 builds the
    envelope as a Python dict). Concretely: the TS-side portion writes a real
    `pending-<hash>.json` via `stagePendingContent` in the `.mjs` test and
    asserts the filename hash matches; the Python-side portion in
    `test_approval_server.py` loads that same envelope shape (or a fixture
    written by `json.dumps({"content": X}, ensure_ascii=False)` AND a fixture
    matching TS's default `JSON.stringify`, which escapes non-ASCII to `\uXXXX`
    — BOTH must `json.loads`-decode to the identical `X` and hash identically,
    since `\uXXXX` escapes and raw UTF-8 bytes both parse to the same string).

**Deliberately-deferred non-blocker (honesty framing).** The `do_GET` diff read
resolves `envelope["filePath"]` and reads that on-disk file for the diff base.
The staged `filePath` is written by the Tier-3-gated hook (it is the gate's own
computed target, not free operator input) and the diff base is **display-only**
(never hashed, never minted — the what-you-sign bytes are always
`envelope["content"]`), so a poisoned `filePath` can at worst show a misleading
diff, not corrupt an approval. Full `filePath` re-validation/confinement for the
diff read is therefore **explicitly OUT OF SCOPE for this plan** and NOT built
here; it is noted as a known, bounded, low-severity follow-up rather than
scope-crept into now. (The `<hash>` URL segment IS validated — E7/S7 — because
it reaches a filesystem join; `filePath` reaches only a display read.)

## Execution Workflow

### Operator-vs-code split

| Step | Artifact | Owner | Routing / notes |
|------|----------|-------|-----------------|
| 1 | `tests/test_approval_server.py` (new unit tests) | **gleipnir-code** | `tests/**` — full pipeline; test-first (red) |
| 2 | `tests/test_approval_server.py` (E2E conformance) | **gleipnir-code** | `tests/**`; test-first (red) |
| 3 | `src/gleipnir/approval/server.py` (GET/POST `/approve/<hash>`, render, load, staged_path) | **gleipnir-code** | `src/**` ∈ Axis-1 `X` — **full 8-stage pipeline**, sandbox build/test, pre-written test is arbiter |
| 4 | `tests/test_tier3_gate.mjs` (new TS unit + staging-on-refuse tests) | **gleipnir-code** | `tests/**` — authored by code; RED at import until step 5 (mirrors existing file's note) |
| 5 | `.gleipnir/plugins/tier3-gate.ts` (staging + hash + URL message) | **OPERATOR / BUILD-MODE** | ⚠️ **Tier-3 enforcement code, `.gleipnir/plugins/** ∈ E`. NOT a gleipnir-code write, NOT a tier3-writer write (guard must not be reachable by the guarded, Axiom 2 / G-1). MUST route the HARDENED PATH: two reviewer passes (spec-conformance + blast-radius/false-success) + negative-check attestation per `stage-role-map.md`.** Applied exactly like the original plugin. |
| 6 | E2E integration confirmation (plugin applied + server running) | operator + gleipnir-code | Success criterion 4 / S8 verified live |

### Hardened-path flag (explicit)

The `.ts` change (step 5) is **enforcement-bearing** (`.gleipnir/plugins/**` ∈
the enforcement-path set `E`, and it edits capability-adjacent enforcement
logic). It runs the **hardened path**: `quality-reviewer` performs TWO separate
passes with two recorded verdicts — (1) spec-conformance against THIS plan, and
(2) an adversarial blast-radius/false-success pass — plus a negative-check
attestation (`attested_by ≠ author`) asserting the change did NOT broaden the
gate: specifically that staging happens ONLY on a policy REFUSE (not on
`PreflightUnavailable`, not on `edit`), that no new allow-path was introduced,
and that `isTier3Path`/`decideFromExit`/`runGateCheck`'s core contracts are
byte-unchanged. Because the overall change spans an enforcement path AND
executable `src/**`, the whole plan runs the full 8-stage pipeline on the
hardened path (brief §"Hardened-path routing requirement").

### Retry discipline (D — no code)

After the operator approves (token minted), whoever attempted the Tier-3 write
retries the **same** `write` within the 180s freshness window (`token.py`
`APPROVAL_MAX_AGE_SECONDS = 180`). No auto-retry machinery — matches the
`question`-tool Confirm step and lesson-escalation gate. The refusal message
(P8) tells the operator/agent exactly what to do.

## Design Principles (Gate 1 cognition layer)

**Routing:** `P ∩ X ≠ ∅` (touches `src/gleipnir/approval/server.py` ∈ `src/**`,
`tests/**`, and `.gleipnir/plugins/tier3-gate.ts` — a shebang-less but
executable TS plugin) AND the touched `X`-members have function/module
structure. **Case (i): OOP/functional code** → SOLID + DRY + SRP + Design
Intent all apply.

**Design Intent (specific, falsifiable — the load-bearing genuineness proxy):**
*The review page renders exactly the UTF-8 bytes that will be hashed and minted
— never a paraphrase, reconstruction, re-serialization, or lossy transform of
them.* Concretely: the bytes `render_review_page` HTML-escapes for display are
the SAME `envelope["content"]` string whose `.encode("utf-8")` the POST path
hands to `capture_approval`, and whose sha256 keyed the staged filename and the
approval URL. **Falsifiable by:** any implementation choice where the displayed
content is derived from a different source than the hashed content (e.g.
re-reading the on-disk target for display, hashing the JSON envelope instead of
the `content` field, decoding/re-encoding with a non-UTF-8 codec, or trimming
whitespace before hashing) — a reviewer can point to it and the intent is
violated. S1/S5/S8 test exactly this.

**Single Responsibility (name each new component's one responsibility):**
- `computeChangeHash(resultingContent)` (TS): compute the canonical
  UTF-8 sha256 of the resulting bytes — nothing else (no I/O, no message).
- `stagePendingContent(...)` (TS): persist the envelope to the Tier-0 staged
  file and return its hash — one reason to change (the staged-file shape).
- `buildApprovalUrl(hash)` (TS): turn a hash + env config into the message tail
  — one reason to change (the URL/message wording).
- `staged_path_for` (py): name→path mapping only.
- `load_staged` (py): read+parse a staged envelope, None on any fault — one
  reason to change (the staged-file read contract).
- `render_review_page` (py): produce the HTML (escape + diff + form) — pure,
  no I/O, no minting; one reason to change (the page layout/escaping).
- The `do_GET`/`do_POST` branches: thin edge wiring only — resolve dir, call the
  pure functions, map to HTTP status. They do NOT mint (they delegate to the
  unchanged `capture_approval`) and do NOT compute hashes independently.

**SOLID:**
- **S** — see above; each function has one reason to change; rendering is
  separated from reading is separated from minting.
- **O (Open/Closed):** `capture_approval`, `token_path_for`,
  `compute_change_hash`, `resultingContentFor`, `runGateCheck`, `decideFromExit`,
  `isTier3Path` are EXTENDED-around, not modified — the new POST path is a new
  call site of the unchanged core; the new hook staging is a new branch that
  reuses the unchanged `resultingContent`.
- **L (Liskov):** no new subclasses of `ApprovalRequestHandler` beyond the
  existing `make_handler_class` pattern; the new branches live in the same class
  and respect `BaseHTTPRequestHandler`'s contract (`do_GET`/`do_POST`
  signatures, `_send`). No new `Tier3GateAbort` subclass semantics beyond the
  existing `PreflightUnavailable` distinction.
- **I (Interface Segregation):** `render_review_page` takes only what it needs
  (`envelope`, `current_on_disk: bytes | None`) — not a socket, not a handler.
  `load_staged` takes `(token_dir, hash)` — not the whole request.
- **D (Dependency Inversion):** the pure builders (`render_review_page`,
  `load_staged`) depend on plain data (dict, bytes), not on `http.server`; the
  thin edge depends on them. Mirrors the existing pure-core/thin-edge split.

**DRY:**
- The hash discipline is defined ONCE per language and made to agree by P2
  (UTF-8), NOT re-derived divergently — the TS `computeChangeHash` and the
  Python `compute_change_hash` are two sides of the SAME byte-string contract,
  documented as such (not duplicated logic, but a deliberately-mirrored
  invariant with a test, S1, pinning the agreement).
- The minting path is NOT duplicated: the new POST-by-hash branch calls the
  existing `capture_approval` (rejected alternative: a second mint
  implementation).
- The staged-file directory is the existing Tier-0 `var/tmp` (reuse
  `TOKEN_DIR_REL` / `default_token_dir()`), not a new constant per file.
- HTML-escaping uses stdlib `html.escape` once, applied uniformly to content and
  diff lines (no bespoke escaper).

---
Provenance: plan authored by `gleipnir-plan` (Tier-0 writer) from the CONVERGED
brief `tier3-approval-ux-brainstorm.md`. The four brief-level decisions
(A1/B/C2/D) are cited, not re-decided; the `[PLAN-STAGE JUDGMENT]` rows (P1–P8)
are the implementation details the brief's `## Open Questions` delegated to this
stage. No new material tradeoff introduced. The `.ts` half is operator/build-mode
applied on the hardened path; the `.py` half is `gleipnir-code`-built-and-tested
on the full pipeline.
