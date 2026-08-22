# Plan: D5 sidecar `head_sha` write side effect in `commit_changes` (ready-to-apply diff)

**Status:** PLAN / DIFF-DRAFT — authored by `gleipnir-plan` (Tier-0 writer).
This is a **disposable Tier-0 session artifact**. It contains a ready-to-apply
diff for `src/gleipnir/broker/git/mcp_server.py` that the operator applies (or
routes to the appropriate author) and that `gleipnir-code` accompanies with
tests. **`gleipnir-plan` has no write access to `src/**` or `tests/**` and did
not — and must not — apply any of this.**

**Parent plan:** `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble Phase 3
step 5, Trace table row "Run manifest `head_sha` **write side** (D5)"
(lines ~320-338, ~168). Quality-review confirmed this side effect was never
actually added — a genuine spec-conformance gap against that step.

---

## GOTCHA pre-flight (visible)

- **Goals / order:** bounded design task — draft the exact diff the parent
  plan already assigns to this file. Plan-before-code order honored: this
  artifact is the plan; `gleipnir-code` writes the tests and the operator (or
  routed author) applies the diff afterward.
- **Boundary:** I may write only `.gleipnir/plans/**`. I did not call
  `edit`/`write` on `src/**` or `tests/**`, per the delegation.
- **Gap watched (and found):** the delegation flagged "is `pipeline_id`
  available to `commit_changes`?" as a possible sub-gap. **It is not** — see
  the finding below. The diff therefore also resolves that sub-gap, sourcing
  `pipeline_id` from the same session env-var convention the Phase-2 hook
  already established, WITHOUT adding an agent-facing tool parameter.

---

## FINDING — `pipeline_id` availability at commit time (the sub-gap)

**`commit_changes` has NO access to a `pipeline_id` today, and neither does any
other broker code.** Verified:

- `grep pipeline_id src/gleipnir/broker/` → **zero matches**. The broker
  package is completely unaware of pipeline identity.
- `commit_changes(message, files="", repo_dir="")` (mcp_server.py:267) has no
  `pipeline_id` parameter, and its MCP tool schema exposes none.
- The broker DOES already read process env for its own config
  (`guards.py` uses `os.environ.get("GLEIPNIR_GIT_*")`), so env-var sourcing is
  an established pattern in this exact module family. `mcp_server.py` itself
  does not yet import `os`.

**Where `pipeline_id` comes from in the rest of this feature.** The Phase-2
advance hook already resolved the identical "where does `pipeline_id` come
from across a fresh process" question and documented the convention verbatim
(`.gleipnir/plugins/advance-hook.ts:53-69`, `PIPELINE_ID_ENV = "GLEIPNIR_PIPELINE_ID"`):

> "this hook reads it from `GLEIPNIR_PIPELINE_ID` — the SAME session-scoped
> env-var pattern already used for `GLEIPNIR_MARKER_KEY_FILE` /
> `GLEIPNIR_PIPELINE` (set once by whoever arms the run; inherited by every
> `tool.execute.after` call in this session)."

**Decision for this diff (NOT a new material tradeoff — it reuses the
already-established Phase-2 convention):** source `pipeline_id` from the
`GLEIPNIR_PIPELINE_ID` environment variable, exactly as the advance hook does.
Do **NOT** add a `pipeline_id` tool parameter. Rationale:

1. **Security.** Adding `pipeline_id` to the MCP tool schema would make it an
   **agent-controllable input**. The whole point of D5/Q4 is that
   `attempt_gate` refuses on `pipeline_id` mismatch (a GREEN run for run A must
   not gate run B). If an agent could set `pipeline_id` on `commit_changes`, it
   could forge the correlation identity written into the sidecar — precisely
   the forgery the correlation exists to prevent. The env var is set once by
   whoever arms the run and is *not* an agent tool argument, preserving the
   "framework-written, agent-read-only" property of D5.
2. **D5 constraint fidelity.** The delegation and parent plan both state this
   is "an internal side effect of the existing `commit_changes` implementation
   … not an agent-facing tool change." A new tool parameter WOULD be an
   agent-facing change. The env-var read is not.
3. **Consistency.** It matches the Phase-2 hook's convention byte-for-byte, so
   the same `GLEIPNIR_PIPELINE_ID` value that drives `advance` also stamps the
   sidecar — the two halves agree on the run identity by construction.

**Structural requirement that makes sourcing `pipeline_id` non-optional.** The
already-built READ side, `read_pipeline_run_identity` (advance.py:286-322),
returns `None` (fail-closed) unless the file is a JSON object with **both**
`pipeline_id` AND `head_sha` present as **non-empty strings**. So the broker
cannot write `head_sha` alone: a well-formed, readable sidecar *requires* a
`pipeline_id` too. Sourcing it is structurally forced by the read contract,
not a nice-to-have.

**Armed-only, fail-safe.** The sidecar write happens ONLY when
`GLEIPNIR_PIPELINE_ID` is set and non-empty (i.e. an armed pipeline run).
When it is absent (an ordinary, non-pipeline commit), the broker writes NO
sidecar and behaves exactly as today. This keeps the change inert for every
non-pipeline use of the broker and mirrors the hook's arming discipline.

---

## READ-side contract this WRITE must satisfy (verified against
`src/gleipnir/preflight/advance.py`)

The write must produce a file the already-built reader can consume. From
`read_pipeline_run_identity` / `pipeline_run_path` (advance.py:278-322):

- **Path:** `<repo_root>/.gleipnir/var/run/pipeline-run.json`
  (`DEFAULT_RUN_ROOT / PIPELINE_RUN_FILENAME`, advance.py:274-283).
- **Shape:** a JSON **object** (`isinstance(data, dict)`), UTF-8.
- **Keys (exact names):** `"pipeline_id"` and `"head_sha"` — both must be
  **non-empty `str`** or the reader returns `None` (advance.py:315-320).
- **No MAC / digest / signature** in the file (D5 CONVERGED: plain file, no own
  HMAC). Just the two-key JSON object.

The diff below writes exactly `{"pipeline_id": <str>, "head_sha": <str>}` to
that path — nothing more, so the reader accepts it and no extra field can be
misread as identity.

---

## 1. The exact diff for `src/gleipnir/broker/git/mcp_server.py`

Three hunks: (A) imports; (B) a small private helper + path constant; (C) a
call to that helper immediately after `commit_changes` computes `commit_hash`,
BEFORE it returns. The existing return value is untouched.

### Hunk A — imports (add `os` and `Path`)

```diff
 from __future__ import annotations

 import json
+import os
 import subprocess
+from pathlib import Path
 from typing import Any, Dict, List, Optional

 from mcp.server.fastmcp import FastMCP
```

### Hunk B — new module-level constant + private helper

Insert immediately **after** the `_current_branch` helper (i.e. after
mcp_server.py:166, before the `# Read-only tools` section comment at line 169):

```diff
 def _current_branch(repo_dir: Optional[str] = None) -> str:
     result = _run_git(["branch", "--show-current"], repo_dir)
     if result.get("success"):
         return result["stdout"].strip()
     return ""


+# ---------------------------------------------------------------------------
+# D5 run-manifest sidecar write (Seam 8; `.gleipnir/plans/seam7-seam8-wiring.md`
+# Assemble Phase 3 step 5). After a successful commit, the broker PROCESS (not
+# a roster agent) stamps the new HEAD into the framework-written,
+# agent-read-only run manifest so the fresh-process advance/fetch path can
+# correlate `(pipeline_id, head_sha)` for GIT->GATE. D5 CONVERGED: this is a
+# PLAIN FILE (no own HMAC/digest) -- integrity comes solely from the existing
+# `.gleipnir/var/run/` agent-unwritable grant class, NOT from any signature
+# added here. The shape/keys/path exactly match the READ side,
+# `gleipnir.preflight.advance.read_pipeline_run_identity`
+# (`{"pipeline_id": <str>, "head_sha": <str>}` at
+# `.gleipnir/var/run/pipeline-run.json`), which fail-closes to `None` unless
+# BOTH keys are non-empty strings -- so both are written together or not at
+# all.
+#
+# `pipeline_id` is sourced from the `GLEIPNIR_PIPELINE_ID` env var -- the SAME
+# session-scoped arming convention the Phase-2 advance hook already uses
+# (`.gleipnir/plugins/advance-hook.ts`, `PIPELINE_ID_ENV`), NOT an agent-facing
+# tool parameter: making it a tool arg would let an agent forge the correlation
+# identity the gate refuses mismatches on. When it is unset/empty (an ordinary
+# non-pipeline commit, i.e. an UNARMED run) NO sidecar is written and
+# `commit_changes` behaves exactly as before. The write is best-effort and
+# NEVER changes `commit_changes`'s success/return contract: the commit has
+# already happened, so a sidecar-write failure must not turn a successful
+# commit into a reported failure (that would be a false-negative worse than a
+# missing sidecar, which the read side already fail-closes on).
+# ---------------------------------------------------------------------------
+
+_PIPELINE_ID_ENV = "GLEIPNIR_PIPELINE_ID"
+
+# Repo-root-relative location, matching `gleipnir.preflight.advance`
+# (`DEFAULT_RUN_ROOT / PIPELINE_RUN_FILENAME`). Resolved from this file's path:
+# src/gleipnir/broker/git/mcp_server.py -> repo root is four parents up.
+_PIPELINE_RUN_REL = Path(".gleipnir") / "var" / "run" / "pipeline-run.json"
+
+
+def _repo_root() -> Path:
+    # .../src/gleipnir/broker/git/mcp_server.py -> parents[4] is the repo root.
+    return Path(__file__).resolve().parents[4]
+
+
+def _write_run_manifest_head_sha(commit_hash: str) -> None:
+    """Best-effort D5 sidecar stamp: write `{pipeline_id, head_sha}` to
+    `.gleipnir/var/run/pipeline-run.json` after a successful commit, ONLY when
+    armed (``GLEIPNIR_PIPELINE_ID`` set and non-empty) and ``commit_hash`` is a
+    non-empty string. Never raises: any failure is swallowed so a
+    sidecar-write problem cannot flip an already-succeeded commit's result.
+    Writes both required keys together (the read side fail-closes on a missing
+    or empty either-key), plain file, no MAC (D5 CONVERGED)."""
+    pipeline_id = os.environ.get(_PIPELINE_ID_ENV, "").strip()
+    if not pipeline_id or not commit_hash:
+        return
+    try:
+        path = _repo_root() / _PIPELINE_RUN_REL
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_text(
+            json.dumps({"pipeline_id": pipeline_id, "head_sha": commit_hash}),
+            encoding="utf-8",
+        )
+    except OSError:
+        # Fail-safe: the commit already succeeded. A missing/failed sidecar
+        # write degrades to "GATE cannot yet be attempted" on the read side
+        # (`read_pipeline_run_identity` -> None -> `MissingRunIdentity`), which
+        # is the correct fail-closed outcome -- never a false green, and never
+        # a false commit failure.
+        return
+
+
 # ---------------------------------------------------------------------------
 # Read-only tools
 # ---------------------------------------------------------------------------
```

### Hunk C — call the helper inside `commit_changes`, after computing the hash

Change the tail of `commit_changes` (mcp_server.py:367-377):

```diff
     hash_result = _run_git(["rev-parse", "HEAD"], rd)
     commit_hash = hash_result["stdout"].strip() if hash_result.get("success") else ""

+    # D5 (Seam 8): stamp the new HEAD into the run-manifest sidecar as a
+    # best-effort side effect of this commit -- armed runs only, never alters
+    # the return contract below. See `_write_run_manifest_head_sha`.
+    _write_run_manifest_head_sha(commit_hash)
+
     return json.dumps(
         {
             "success": True,
             "hash": commit_hash,
             "message": message,
             "branch": branch,
         }
     )
```

### Consolidated "after" view of the changed `commit_changes` tail

```python
    hash_result = _run_git(["rev-parse", "HEAD"], rd)
    commit_hash = hash_result["stdout"].strip() if hash_result.get("success") else ""

    # D5 (Seam 8): stamp the new HEAD into the run-manifest sidecar as a
    # best-effort side effect of this commit -- armed runs only, never alters
    # the return contract below. See `_write_run_manifest_head_sha`.
    _write_run_manifest_head_sha(commit_hash)

    return json.dumps(
        {
            "success": True,
            "hash": commit_hash,
            "message": message,
            "branch": branch,
        }
    )
```

---

## 2. Plain-language explanation (why, referencing the Trace table)

The parent plan's Trace row **"Run manifest `head_sha` write side (D5)"** assigns
this exact side effect to `src/gleipnir/broker/git/mcp_server.py::commit_changes`:
"Writes/updates `head_sha` in the sidecar at the git stage. `commit_changes`
already computes the new HEAD via `git rev-parse HEAD` (`mcp_server.py:367-368`);
it persists that value into `.gleipnir/var/run/pipeline-run.json` in the same
call. This is the broker *process's* write; `git-ops` the agent has
`edit: deny`/`write: deny` and never writes the sidecar."

What the diff does, step by step:

- **After** the always-on secret-scan gate has passed and the `git commit` has
  succeeded, `commit_changes` already runs `git rev-parse HEAD` and stores the
  result in `commit_hash` (unchanged).
- The diff adds ONE new statement right there: `_write_run_manifest_head_sha(commit_hash)`.
- That helper, **only when the run is armed** (`GLEIPNIR_PIPELINE_ID` set), writes
  the plain-file sidecar `{"pipeline_id": <env>, "head_sha": <commit_hash>}` to
  `.gleipnir/var/run/pipeline-run.json` — the exact path, keys, and JSON shape
  the already-built `read_pipeline_run_identity` (advance.py) expects. This is
  the WRITE side that pairs with that READ side, closing Seam 8's `(pipeline_id,
  head_sha)` correlation for GIT→GATE.
- It is the broker **process's** write (framework-written), reached through the
  MCP server's own Python, not through a `git-ops` agent capability. The agent's
  grants (`edit: deny`/`write: deny`) are untouched and irrelevant to this
  process-side write — consistent with D5's "framework-written, agent-read-only."
- **No MAC/digest** is added (D5 CONVERGED: plain file; integrity from the
  `.gleipnir/var/run/` agent-unwritable grant class). The bridge marker and
  `StateMarker` are **not touched** — this diff imports nothing from `bridge.py`
  and constructs no marker; the golden-fixture MAC contract is byte-unaffected.

---

## 3. Additive-only / observable-contract preservation confirmation

**The existing commit-and-return-hash behavior is preserved byte-for-byte in its
observable contract for every caller that does not care about the sidecar.**

- `commit_changes`'s **signature is unchanged** (`message, files="", repo_dir=""`)
  — no new parameter, no schema change to the MCP tool.
- Its **return value is unchanged**: the same
  `{"success": True, "hash": commit_hash, "message": message, "branch": branch}`
  JSON on success, and every existing failure branch (staging failure, secret
  finding, diff-read failure, commit/hook failure) is **untouched** — the new
  code is only reached on the already-successful path, after `commit_hash` is
  computed and before the existing `return`.
- The new call is a **pure side effect** whose failure is **swallowed**
  (`except OSError: return`), so it can NEVER convert a successful commit into a
  reported failure. A caller that ignores the sidecar sees identical behavior to
  today, byte-for-byte.
- When **unarmed** (`GLEIPNIR_PIPELINE_ID` unset/empty), the helper returns
  immediately and writes nothing — the broker is completely inert for all
  non-pipeline commits, exactly as before.
- The only observable difference, and only for an armed run, is the appearance
  of the sidecar file the READ side is already waiting for — which is the entire
  point of the assigned step.

Note: the added `import os` / `from pathlib import Path` and the two module-level
helpers are additive; no existing symbol is renamed or removed.

---

## 4. Test specification (for `gleipnir-code` to author under `tests/**`)

`gleipnir-plan` cannot write `tests/**`. The following is the specification the
accompanying tests MUST assert. Suggested home:
`tests/test_broker_run_manifest.py` (new), keeping broker-surface invariants in
`tests/test_broker_tool_surface.py` intact.

**Armed happy path (the core assertion):**
1. With `GLEIPNIR_PIPELINE_ID` set to a known value (e.g. via
   `monkeypatch.setenv`), a real temp git repo (`git init`, a staged change),
   and `commit_changes(message, repo_dir=<tmp>)` invoked, assert:
   - the returned JSON still has `success: True` and a non-empty `hash`
     (contract preserved), AND
   - `.gleipnir/var/run/pipeline-run.json` (at the resolved repo root — see the
     path-resolution note below) now contains a JSON object with
     `pipeline_id == <the env value>` and `head_sha == <the returned hash>`.
2. **Round-trip against the real reader (strongest assertion):** feed the
   written file to `gleipnir.preflight.advance.read_pipeline_run_identity`
   (using its `run_root=` injection to point at the test's run dir) and assert
   it returns exactly `(<env pipeline_id>, <commit hash>)` — proving the WRITE
   side and the already-built READ side agree on shape/keys/path. This is the
   test that would have caught the original gap.

**Unarmed no-op:**
3. With `GLEIPNIR_PIPELINE_ID` **unset**, `commit_changes` succeeds and NO
   `pipeline-run.json` is created (or an existing one is left untouched) — assert
   file absence / non-modification, and assert the return JSON is unchanged.

**Contract preservation / fail-safe:**
4. A sidecar-write failure does NOT fail the commit: simulate the write path
   raising `OSError` (e.g. monkeypatch `_write_run_manifest_head_sha`'s
   `Path.write_text` or make the run dir unwritable) and assert `commit_changes`
   still returns `success: True` with the correct hash. (The commit already
   happened; the sidecar failure is swallowed.)
5. **Both-keys-together invariant:** assert the written file, when armed, always
   contains BOTH `pipeline_id` and `head_sha` as non-empty strings (never one
   alone) — mirror `read_pipeline_run_identity`'s fail-closed contract so a
   regression that writes only `head_sha` is caught.
6. **No-MAC / plain-file invariant (D5):** assert the written JSON object has
   EXACTLY the keys `{"pipeline_id", "head_sha"}` and no signature/digest/MAC
   field — guards against a future regression re-adding a second integrity
   scheme the operator explicitly rejected.

**Bridge / marker untouched (blast-radius):**
7. Assert (or rely on the existing golden-fixture conformance test) that this
   change imports nothing from `engine.bridge` and constructs no `StateMarker`
   — the marker MAC contract is byte-unchanged. A `grep` in review suffices; a
   test can assert `mcp_server` has no `bridge`/`StateMarker` attribute.

**Broker surface invariants preserved:**
8. The existing `tests/test_broker_tool_surface.py` (no `--force`, no
   `--no-verify` reachable) must still pass unchanged — the diff adds no argv and
   no new tool.

**Path-resolution note for the test author.** The helper resolves the repo root
via `Path(__file__).resolve().parents[4]` and writes to the real
`.gleipnir/var/run/`. The READ side (`advance.py`) took an *injectable*
`run_root` precisely so tests avoid the real (sandbox-read-only) tree. This diff
keeps the broker helper minimal (matching the existing broker style, which reads
env directly and has no injection seams), so the test should run against a
**temp git repo whose own `.gleipnir/var/run/` is writable** (create it under
`tmp_path` and invoke with `repo_dir=<tmp>`) — BUT note the helper computes the
path from `__file__`, not from `repo_dir`. **This is a real seam the test author
and reviewer must confirm:** either (a) the test tolerates the write landing at
the source-tree repo root (cleaning up after), or (b) `gleipnir-code`/operator
adds a small injectable `run_root` seam to `_write_run_manifest_head_sha`
(mirroring `advance.py`) so the test can point it at `tmp_path`. **Option (b) is
recommended** for testability parity with the read side; if adopted, the helper
gains a `*, run_root: Path | None = None` keyword defaulting to
`_repo_root() / ".gleipnir" / "var" / "run"`, and `commit_changes` calls it
without that arg (production default). I flag this rather than silently bake in
one choice — it is a minor, non-material testability decision for the
implementing stage, not a material design tradeoff for the operator.

---

## Return-to-orchestrator note (report)

**Plan/diff written to:** `.gleipnir/plans/seam8-d5-sidecar-write-diff.md`
(Tier-0; my only permitted write path). **No `edit`/`write` was attempted on
`src/**` or `tests/**`.**

**The `pipeline_id`-availability finding (the delegation's key question):**
`commit_changes` has **NO** `pipeline_id` today — zero references anywhere in
`src/gleipnir/broker/`. The diff sources it from the **`GLEIPNIR_PIPELINE_ID`
env var**, reusing the *exact* session-scoped arming convention the Phase-2
advance hook already established (`advance-hook.ts` `PIPELINE_ID_ENV`), and
deliberately **NOT** as a new agent-facing tool parameter (a tool arg would let
an agent forge the gate-correlation identity — a security regression, and a
violation of D5's "not an agent-facing tool change"). Sourcing it is
structurally forced: the built READ side fail-closes unless BOTH `pipeline_id`
and `head_sha` are non-empty, so the file cannot be written with `head_sha`
alone.

**Diff shape (apply order):** Hunk A (add `import os`, `from pathlib import
Path`) → Hunk B (constant `_PIPELINE_ID_ENV`, `_PIPELINE_RUN_REL`, `_repo_root`,
`_write_run_manifest_head_sha` after `_current_branch`) → Hunk C (one call to
`_write_run_manifest_head_sha(commit_hash)` in `commit_changes`, after the hash
is computed, before the existing `return`). Additive-only; existing signature,
return value, and every failure branch preserved byte-for-byte; write is
armed-only and best-effort (swallows `OSError`, never fails the commit).
Bridge/`StateMarker` untouched (no import from `bridge.py`); plain file, no MAC
(D5 CONVERGED).

**One flagged (non-material) seam for the implementing stage, NOT a material
operator tradeoff:** the helper resolves its path from `__file__`, so a clean
`tmp_path` test needs either cleanup or an optional injectable `run_root=` seam
(recommended, mirroring `advance.py`). I named it rather than baking one choice
in. **No material design tradeoff remains open** — D5 is already operator-
converged; this diff implements it as decided.

**Separately flagged (already in the parent plan, restated so the orchestrator
routes authorship correctly):** `src/gleipnir/broker/git/mcp_server.py` is NOT
in `gleipnir-code`'s deny set, so by current grant the code agent *could* edit
it — but it is enforcement-bearing broker code (E-1 surface). The parent plan
(§ Execution Workflow) says to treat this edit as enforcement code and route it
accordingly; whether to add `src/gleipnir/broker/**` to `gleipnir-code`'s deny
set is a Tier-3 grant decision for the operator, out of this Tier-0 scope.
