# Plan: fix `bin/gleipnir-sandbox lint` (read-only-mount write failure + false-green exit)

**Stage:** plan (from operator-provided problem statement; no separate
brainstorm brief — the operator framed the problem and enumerated the option
set, so this plan bounds the work and surfaces the one material tradeoff as a
Decision).
**Bound implementer:** `gleipnir-code` (Sonnet). Touched paths are in its
editable set (`src/gleipnir/sandbox/**`; `preflight/**` is denied but not
touched here).
**Route:** full 8-stage pipeline — `P` contains `src/**` and `tests/**`
(executable artifacts), which are in the disqualifier set `X`
(`stage-role-map.md` Axis 1). This is NOT the prose/config track. Test-first.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | How to stop `compileall` writing `.pyc` into the read-only `/work` mount | Set `PYTHONPYCACHEPREFIX` to a path under the writable scratch mount (`/work/.scratch`), so all bytecode output is redirected there; `compileall` still does a real byte-compile (full syntax + import-structure check) | (b) replace `compileall` with `ast.parse`/`py_compile` (weaker check, or `py_compile` also writes); (c) `compileall -x` (does not stop writes) | `PYTHONPYCACHEPREFIX` is CPython-wide and honored by `python -m compileall` (verified against docs: compileall "respects the `sys.pycache_prefix` setting", which `PYTHONPYCACHEPREFIX` sets). Keeps the strongest check; touches nothing about *what* is compiled |
| D2 | Where the `PYTHONPYCACHEPREFIX` value comes from | Hardcode it unconditionally in `_cmd_lint` via `prepare_sandbox_run(..., extra_env=[("PYTHONPYCACHEPREFIX", "<scratch>")])`. No Tier-3 `profiles.toml` change | (i) Profile-configured lint-env mirroring the coverage `file_env`/`file_path` shape (needs `profiles.py` schema change + live `profiles.toml` + fixture edits, all Tier-3/operator-gated); (ii) place the env unconditionally in `runtime.py::build_run_argv` next to the existing hardcoded `PYTHONDONTWRITEBYTECODE=1` (`runtime.py:318`) | The setting is a **generic, universally-safe** CPython env var: correct for the `python` and `broker` compileall lints, and inert for the `node` lint (node ignores `PYTHON*`). Hardcoding in the profile-agnostic `_cmd_lint` fixes **both** buggy profiles at once with the least surface and **zero Tier-3 change**. Per-profile configurability (the only thing route (i) buys) is worth nothing when one value is correct everywhere. Route (ii) would be more DRY and auto-cover any future compileall profile, but was rejected for **minimal blast radius**: it shares `build_run_argv` with the `test` path, so it would force a lint-specific env onto every `test` run too — `_cmd_lint` scopes the change to the one command that needs it. **Surfaced as a material tradeoff for operator awareness; recommended, not silently enshrined** |
| D3 | The in-container path for the pycache prefix | `/work/.scratch/pycache` (a subdir of the existing rw scratch mount `SCRATCH_SUBPATH`), constructed from `runtime.WORKDIR` + `SCRATCH_SUBPATH` so it stays coupled to the mount, not a magic string | A bare `/tmp` path (works, but decouples from the audited mount layout and is undocumented in `build_run_argv`) | Reuses the exact writable mount the coverage fix already relies on (`runtime.py:313-314`); keeps all writes inside the one audited rw location; symmetry with the `COVERAGE_FILE` pattern |
| D4 | Scope of the false-green exit-0 (Problem 2) | Treat as a **separate investigation task** the implementer must resolve before claiming success, NOT assumed-fixed-by-D1. Static analysis proves `compileall` itself returns exit 1 on the OSError, so the observed exit 0 originates elsewhere in the invocation chain and must be reproduced/located | Assume D1 incidentally fixes it (unverified — the exit-0 was NOT `compileall` swallowing the error, per source read) | CPython 3.12 `compileall.__main__`: `compile_file` catches `OSError` → `success=False`; `main()` returns it; `__main__` does `exit_status = int(not main())` → exit **1**. So the write-OSError *does* propagate. The operator's observed `=== exit: 0 ===` is therefore an **independent, unexplained** defect that must be located, not hand-waved. Acceptance requires a broken-`.py` → non-zero-exit proof |

> **CORRECTION (live reproduction, this session):** Bug 2 (the suspected false-green exit 0) was found **NOT to exist**. The original observation was a measurement artifact: the orchestrator piped the output through `| tail`, so the shell reported tail's exit code (0), not compileall's (1). On live reproduction: `python -m compileall` correctly returns exit 1 on both SyntaxErrors and read-only-mount OSErrors. `bin/gleipnir-sandbox lint` propagates it faithfully. Therefore, **only Bug 1 (the PYTHONPYCACHEPREFIX redirect, D1) required a code change.** A regression-guard test was added anyway (`tests/test_sandbox_cli.py::test_lint_exit_code_propagates_from_exec`) to lock in the correct exit-code-propagation behavior and prevent a future regression that could reintroduce a false-green. See lesson candidate L-C25: "a bug report can be a measurement artifact; reproduce the raw signal before planning a fix."

| D5 | HOW the D4 exit-code defect may be fixed | A **genuine returncode-propagation fix** keyed off the actual subprocess/container returncode or another structural signal | Grepping `compileall`'s stdout/stderr for an error string and forcing a nonzero exit on a match | Output-string-parsing is the **G-4a prose-parsing anti-pattern** this codebase explicitly disavows (`runtime.py::parse_machine_list` docstring: "never parses the connection-error string (the G-4a prose-parsing anti-pattern)"). A grep-the-output "fix" could pass the broken-source arbiter fixture while remaining fragile/wrong in general — the exact false-success class L-C7 exists to catch. **Spec-review of the implementation will reject an output-string-matching approach** |
| D6 | If the D4 root cause is OUTSIDE the agent edit boundary | **Stop and route back to the operator** (symmetric with D2's Tier-3 clause) | Edit out-of-boundary files (`Containerfile`/`Containerfile.broker`, a `bin/gleipnir-sandbox` shim, etc.) to force the fix through | The fix is bounded to `src/gleipnir/sandbox/**` + `tests/**` (gleipnir-code's grant). Low probability the defect lives elsewhere — spec-review confirmed no `ENTRYPOINT` wrapper exists and `_exec` uses a bare `subprocess.run` with no shell — but if reproduction locates it in `Containerfile*` or requires a `bin/**` shim change (possibly outside gleipnir-code's edit grant), that is a new out-of-boundary decision the operator must own |

---

## Architect

**Problem (one sentence):** `bin/gleipnir-sandbox lint` runs `python -m compileall
-q src` inside a container where the source is mounted read-only, so `compileall`'s
explicit `.pyc` writes fail with `OSError: [Errno 30] Read-only file system` for
every file — and yet the command was observed to exit 0, making lint a
false-green that would pass genuinely broken code.

**User:** `gleipnir-code` (the implementation agent, whose *only* build/verify
capability is `bin/gleipnir-sandbox test|lint`) and, transitively, the whole
pipeline that trusts a green lint as evidence of syntactically valid source.

**Measurable success criteria:**
1. `bin/gleipnir-sandbox lint` completes with **no `Read-only file system`
   error** for any file in `src` (python profile) or `src/gleipnir/broker`
   (broker profile).
2. On a tree of valid source, `lint` exits **0**.
3. On a tree containing at least one deliberately-broken `.py` (syntax error),
   `lint` exits **non-zero** (the whole point of lint). This is the
   false-green regression guard for D4.
4. No `.pyc`/`__pycache__` artifact is written under the read-only `/work`
   source mount; any bytecode lands only under the rw scratch mount.
5. Unit-level: the lint argv/env constructed by `_cmd_lint` includes the
   `PYTHONPYCACHEPREFIX` redirect pointing into `/work/.scratch`, asserted by a
   test in the same faked-`prepare_sandbox_run` style as the existing coverage
   test.
6. No change to the agent-facing verb surface (`test`/`lint`/`image-build`
   unchanged); no new CLI flag; no env-var/CLI override of config.
7. **No Tier-3 `.gleipnir/sandbox/profiles.toml` change** (per D2). If the
   implementer finds a reason D2 must flip to the profile route, that is a new
   material decision → stop and route back to the operator.

**Constraints:**
- stdlib-only (`decisions/runtime-and-deps.md`); `PYTHONPYCACHEPREFIX` and
  `compileall` are both stdlib/interpreter — compliant.
- Touched paths limited to `src/gleipnir/sandbox/**` and `tests/**` (both
  editable by `gleipnir-code`; `src/gleipnir/preflight/**` is denied and is NOT
  touched).
- The `config_root` production path stays fixed/internal (test-harness seam
  only) — do not add any env/flag override.
- `runtime.build_run_argv` mount layout is audited (S-2); reuse the existing rw
  scratch mount, do not add a new mount.

---

## Trace

**Artifacts and where they live (source of truth):**

| Artifact | File | Role in the fix |
|---|---|---|
| Lint dispatch | `src/gleipnir/sandbox/__main__.py::_cmd_lint` (lines 145-164) | **PRIMARY CHANGE.** Today calls `prepare_sandbox_run(lint_cmd, ..., image=...)` with **no `extra_env`**. Add `extra_env=[("PYTHONPYCACHEPREFIX", <scratch pycache path>)]`. This is the whole D1/D2 code change |
| Env threading | `src/gleipnir/sandbox/__main__.py::_cmd_test` (lines 115-142) | **REFERENCE PATTERN ONLY** — shows how `extra_env` is already threaded through `prepare_sandbox_run` for the coverage `COVERAGE_FILE` case (line 127, 137). `_cmd_lint` mirrors this shape |
| argv/env construction | `src/gleipnir/sandbox/runtime.py::build_run_argv` (lines 276-323) / `prepare_sandbox_run` (355-404) | **NO CHANGE NEEDED** — already accepts and emits `extra_env` as `-e NAME=VALUE` (lines 283, 320-321, 362, 403). The plumbing exists; only `_cmd_lint` fails to use it |
| Scratch mount constants | `src/gleipnir/sandbox/runtime.py` `WORKDIR="/work"` (57), `SCRATCH_SUBPATH=".scratch"` (58) | Source of the in-container scratch path. The pycache prefix = `f"{WORKDIR}/{SCRATCH_SUBPATH}/pycache"` = `/work/.scratch/pycache`. Import these rather than hardcoding the string |
| Live lint commands | `.gleipnir/sandbox/profiles.toml` python `lint = [..., "compileall", "-q", "src"]` (line 24); broker `lint = [..., "compileall", "-q", "src/gleipnir/broker"]` (line 61) | **NO CHANGE (D2).** Both carry the same bug; both are fixed by the `_cmd_lint` env, which is profile-agnostic. node lint (line 41, `node --check`) is unaffected and the env is inert for it |
| CLI tests | `tests/test_sandbox_cli.py` | **NEW/CHANGED TEST.** `test_python_profile_lint_runs_configured_command` (167-181) currently fakes `prepare_sandbox_run` with a signature that has **no `extra_env`** (line 172: `def fake_prepare(cmd, *, repo_root, scratch_dir, image)`). This will break once `_cmd_lint` passes `extra_env` — the fake must accept it, and a new assertion must check the redirect is present |
| Runtime/profile tests | `tests/test_sandbox_runtime.py`, `tests/test_sandbox_profiles.py` | Likely unaffected (no runtime/profile schema change). Implementer confirms by running the suite |

**Integrations map:**
- `_cmd_lint` → `prepare_sandbox_run` → `build_run_argv` → `-e
  PYTHONPYCACHEPREFIX=/work/.scratch/pycache` in the container argv.
- In-container: CPython reads `PYTHONPYCACHEPREFIX` → sets `sys.pycache_prefix`
  → `compileall.compile_file` writes every `.pyc` under that prefix (a mirror
  tree on the rw scratch mount) instead of `src/**/__pycache__/` on the ro
  mount.
- The scratch host dir already exists and is created by `_scratch_dir(repo)`
  (`__main__.py:73-76`) and mounted rw (`runtime.py:313-314`). The pycache
  subdir is created lazily by CPython under the prefix — no host-side mkdir
  needed, but the implementer must confirm the prefix path is writable
  in-container (it is a child of the rw mount).

**Edge cases:**
- **node profile:** `PYTHONPYCACHEPREFIX` is set but node ignores all `PYTHON*`
  env — inert. Confirm a node-profile lint test (if one exists) still passes;
  the env being present is harmless.
- **broker profile:** same `compileall` bug, same fix applies automatically via
  the profile-agnostic `_cmd_lint`. No separate code path.
- **A real syntax error** must still fail: `compileall` writes the `.pyc` for
  good files to scratch and, for a file with a `SyntaxError`, hits
  `py_compile.PyCompileError` → `success=False` → exit 1. So once D1 lands,
  criterion 3 is achievable — **but only if the exit-code chain (D4) actually
  propagates the container's non-zero exit to `bin/gleipnir-sandbox`'s exit.**
- **D4 unknown:** static reading proves `compileall` returns 1 on the OSError,
  so the observed exit 0 is NOT explained. Possible locations the implementer
  must check by reproduction: (i) does `podman run`/`docker run` propagate the
  in-container process exit code to `subprocess.run(argv).returncode`
  (`_exec`, `__main__.py:79-83`)? (ii) was the observed run actually reaching
  the OSError path for every file, or exiting early? (iii) is there any wrapper
  swallowing it? The plan does not pre-judge the location; it requires the
  broken-source proof (criterion 3) to be green as the arbiter.

---

## Link (validated before building)

- **`PYTHONPYCACHEPREFIX` is honored by `python -m compileall`** — verified
  against the CPython docs: `PYTHONPYCACHEPREFIX` "Python will write `.pyc`
  files in a mirror directory tree at this path, instead of in `__pycache__`
  directories within the source tree"; and compileall docs: "the `compile()`
  function respects the `sys.pycache_prefix` setting." `PYTHONPYCACHEPREFIX`
  sets `sys.pycache_prefix`. (Not guessed — read this session.)
- **`compileall` has no "syntax-check-only / don't-write" flag** — confirmed
  from its option list (`-l/-f/-q/-d/-s/-p/-x/-i/-b/-r/-j/--invalidation-mode/
  -o/-e/--hardlink-dupes`); none suppress writing. So option (b)'s `compileall`
  variant is impossible; option (c) is a non-fix. (Confirms rejecting them.)
- **`py_compile` also writes `.pyc`** — so a `py_compile`-based rewrite (part of
  option b) would hit the same ro-mount failure; rejected.
- **Exit-code propagation inside `compileall`** — verified from CPython 3.12
  `Lib/compileall.py`: `compile_file` `except (SyntaxError, UnicodeError,
  OSError)` → `success=False`; `main()` returns `success`; `__main__` does
  `exit_status = int(not main())`. An OSError therefore yields exit 1. This is
  what makes the observed exit 0 an **independent** defect (D4) rather than a
  compileall quirk.
- **The `extra_env` plumbing already exists end-to-end** — `prepare_sandbox_run`
  and `build_run_argv` accept `extra_env` and emit `-e NAME=VALUE`; only
  `_cmd_lint` fails to pass it. So D1/D2 is a ~2-line call-site change plus a
  path constant, not new plumbing. (Read `runtime.py` this session.)
- **`gleipnir-code` may edit `src/gleipnir/sandbox/**` and `tests/**`** —
  confirmed against `.gleipnir/agents/gleipnir-code.md` (only `.gleipnir/**`,
  `.git/**`, `src/gleipnir/preflight/**` are denied). No Tier-3 write needed
  under D2.

---

## Assemble (intended build order)

1. **(test-first) Add the unit test for the redirect env.** In
   `tests/test_sandbox_cli.py`, update `test_python_profile_lint_runs_configured_command`
   so its `fake_prepare` accepts `extra_env=()` (mirroring the coverage test's
   fake at line 132), and add an assertion that
   `("PYTHONPYCACHEPREFIX", "/work/.scratch/pycache")` is in the captured
   `extra_env`. Add a companion assertion (or a new test) that the broker
   profile's lint likewise receives the redirect (materialize a broker-style
   config fixture, or assert profile-agnostically that `_cmd_lint` always sets
   it). Run — it must FAIL (red) before the code change.
2. **Implement D1/D2/D3 in `_cmd_lint`** (`src/gleipnir/sandbox/__main__.py`):
   import `WORKDIR`, `SCRATCH_SUBPATH` from `runtime` (or compute the path from
   the already-imported `SCRATCH_SUBPATH`), build
   `pycache_prefix = f"{WORKDIR}/{SCRATCH_SUBPATH}/pycache"`, and pass
   `extra_env=[("PYTHONPYCACHEPREFIX", pycache_prefix)]` to
   `prepare_sandbox_run`. No change to `runtime.py`. Re-run the unit test —
   green.
3. **Run the full sandbox unit suite** (`tests/test_sandbox_cli.py`,
   `test_sandbox_runtime.py`, `test_sandbox_profiles.py`) via
   `bin/gleipnir-sandbox test` — all green, coverage reported.
4. **Investigate + resolve D4 (the exit-0 defect).** Reproduce
   `bin/gleipnir-sandbox lint` end-to-end in the container. With D1 in place,
   confirm criterion 2 (valid tree → exit 0, no ro errors). Then prove the
   broken-source arbiter (criterion 5) using, in order of preference:
   - **(i) PREFERRED — isolated fixture + `config_root` injection:** stand up a
     dedicated fixture directory containing the deliberately-broken `.py` and a
     profile whose lint targets it, injected in-process via
     `main(argv, config_root=...)` exactly as the existing CLI-test harness
     already does (`tests/test_sandbox_cli.py` fixtures). This **never mutates
     the real `src/` tree**, so there is nothing to clean up.
   - **(ii) fallback ONLY if (i) is genuinely unavoidable — real-tree fixture:**
     if a broken file must be placed inside the real `src/` tree, the step MUST
     include an explicit cleanup that removes it and a `git status`-clean
     verification (criterion 6b) proving the working tree carries no leftover
     fixture. Do not leave a syntax-error file in `src/`.

   If lint does NOT return non-zero, locate where the exit code is lost
   (`_exec`/`subprocess.run` return path, or the container-runtime exit-code
   propagation) and fix that defect. **The fix MUST be a genuine
   returncode-propagation fix keyed off the actual subprocess/container
   returncode or another structural signal — NOT a grep of `compileall`'s
   stdout/stderr for an error string (D5).** Output-string-parsing is the G-4a
   prose-parsing anti-pattern (`runtime.py::parse_machine_list`: "never parses
   the connection-error string (the G-4a prose-parsing anti-pattern)"); a
   grep-the-output "fix" could pass the arbiter fixture while remaining wrong in
   general (the L-C7 false-success class), and **spec-review of the
   implementation will reject it.** If reproduction locates the defect
   **outside** `src/gleipnir/sandbox/**` / `tests/**` (e.g. in
   `Containerfile`/`Containerfile.broker`, or requiring a `bin/gleipnir-sandbox`
   shim change that may be outside gleipnir-code's edit grant), **STOP and route
   back to the operator (D6)** rather than editing out-of-boundary files. Add a
   regression test/verification for criterion 5. **Do not claim success on
   criterion 5 by assertion — the broken-source run is the arbiter.**
5. **Confirm no artifact under the ro mount** (criterion 4): after a lint run,
   verify no `__pycache__`/`.pyc` appears under `src/**` on the host (they
   should be under the scratch dir only), AND that the working tree is
   git-clean — no leftover broken-source fixture (criterion 6b).
6. **Report** back to the orchestrator: files changed, pass count + coverage%,
   the D4 finding (where the exit-0 came from and how it was fixed, or evidence
   D1 alone made criterion 3 pass), and explicit confirmation that no Tier-3
   `profiles.toml` change was made.

---

## Stress-test (acceptance checks)

Concrete, checkable — not "it works":

1. **Unit — redirect present:** `test_python_profile_lint_runs_configured_command`
   asserts `("PYTHONPYCACHEPREFIX", "/work/.scratch/pycache") in extra_env` and
   that the lint command HEAD is still `["python","-m","compileall","-q","src"]`
   (unchanged). PASS.
2. **Unit — broker lint also redirected:** a broker-profile dispatch through
   `_cmd_lint` receives the same `PYTHONPYCACHEPREFIX` (profile-agnostic). PASS.
3. **Unit — no verb-surface widening:** existing parser tests
   (`test_lint_subparser_has_no_image_flag`, etc.) still PASS unchanged.
4. **Integration — clean tree, no ro error:** `bin/gleipnir-sandbox lint` on the
   real `src` produces **zero** `Read-only file system` lines and exits **0**.
5. **Integration — false-green regression guard (the D4 arbiter):** with a
   deliberately-broken `.py` in a linted path (preferably an isolated fixture +
   `config_root` injection, per Assemble 4(i)), `bin/gleipnir-sandbox lint`
   exits **non-zero**. (This is the criterion that proves lint can still fail;
   it must be demonstrated, not asserted.) **The mechanism must be a genuine
   returncode-propagation fix, NOT an stdout/stderr error-string grep (D5) —
   spec-review will reject an output-string-matching approach.**
6. **Integration — no ro-mount artifacts:** after a lint run, `git status` /
   filesystem shows no new `src/**/__pycache__/` or `.pyc` under the ro source
   mount.
6b. **Working tree git-clean after the broken-source test:** `git status` shows
   **no leftover broken-source fixture** (and no other stray file) in the
   working tree once criterion 5 has been demonstrated. If Assemble 4(i)
   (isolated fixture) was used this is automatic; if 4(ii) was unavoidable, the
   explicit cleanup must leave the tree clean.
7. **Suite regression:** full `bin/gleipnir-sandbox test` green, coverage at/above
   target (or justified), no other sandbox test regressed.
8. **No Tier-3 change:** `.gleipnir/sandbox/profiles.toml` is byte-identical to
   pre-change (D2). If it changed, the plan's D2 was violated → reject.

---

## Execution Workflow

- **Implementer:** `gleipnir-code`, single bounded delegation. Verb: *fix the
  lint read-only-write failure and the false-green exit in
  `src/gleipnir/sandbox/**`*. Object: `_cmd_lint` env redirect + the D4
  exit-code investigation. Boundary: `src/gleipnir/sandbox/**` and `tests/**`
  only — never `.gleipnir/**` (Tier-3 `profiles.toml` is off-limits and, per
  D2, unnecessary), never `src/gleipnir/preflight/**`.
- **Test-first:** write/adjust the failing unit test (Assemble step 1) before
  the code change (step 2). Do not weaken a test to make it green.
- **Verify in-container:** all verification via `bin/gleipnir-sandbox test|lint`
  (the only granted build capability); report pass count + line+branch
  coverage%.
- **D4 is a gate, not a hope:** success may not be claimed until criterion 5
  (broken source → non-zero exit) is demonstrated green. If D1 alone does not
  achieve it, find and fix the exit-code-propagation defect and say where it
  was. **The fix must key off the actual subprocess/container returncode or a
  structural signal — never an stdout/stderr error-string grep (D5, the G-4a
  prose-parsing anti-pattern); spec-review will reject an output-matching
  approach.** Prefer proving the arbiter with an isolated fixture +
  `config_root` injection (Assemble 4(i)) so the real `src/` tree is never
  mutated; if a real-tree fixture is unavoidable, clean it up and leave the
  working tree git-clean (criterion 6b).
- **Escalate, do not decide (two clauses):**
  - if the implementer concludes D2 must flip to the profile-configured route
    (e.g. `PYTHONPYCACHEPREFIX` turns out unsafe for some profile), that is a
    new material tradeoff touching Tier-3 `profiles.toml` and `profiles.py` —
    **stop and route back to the operator/brainstorm gate**; do not silently
    edit Tier-3 config.
  - if the D4 root cause is located **outside** `src/gleipnir/sandbox/**` /
    `tests/**` (e.g. `Containerfile`/`Containerfile.broker`, or a
    `bin/gleipnir-sandbox` shim that may be outside gleipnir-code's edit grant),
    **stop and route back to the operator (D6)** — do not edit out-of-boundary
    files to force the fix through.
- **Report format:** files changed; verification run (pass count + coverage%);
  the D4 root-cause finding; explicit "`profiles.toml` unchanged" confirmation;
  anything the orchestrator must know before the git stage.
- **Post-merge:** this plan is a transient Tier-0 artifact
  (`.gleipnir/plans/README.md`); no durable decision record is produced unless
  the D4 investigation surfaces a reusable substrate finding worth promoting to
  `decisions/` (operator-authored).
