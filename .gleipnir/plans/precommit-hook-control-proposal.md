# Tier-3 Control Proposal: git pre-commit hook (secret / branch / data-file checks)

_Produced by the `tier3-coach` skill. This is a PROPOSAL — the artifact belongs
in the substrate/VCS layer, which the agent cannot write. Apply per Handoff._

## Gap

The git broker (`src/gleipnir/broker/git/mcp_server.py`) was deliberately
stripped of commit-policy gating: `commit_changes` no longer runs a
`precommit_check` block (secret-scan / branch-protection / data-file checks are
not the broker's job). That relocation is correct — but it leaves the checks
**enforced by nothing** until they are installed where they belong. Concretely:

- **Safety (must live somewhere):** committing a live credential to history.
  Nothing currently catches it.
- **Preference (operator's choice):** protected-branch refusal, data-file
  hygiene. Off unless the operator wants them.

The broker's own docstrings now reference "a `pre-commit` hook the operator
installs" — this proposal is that hook.

## Correct layer

**Substrate / VCS** — a git `pre-commit` (and optional `pre-push`) hook. Per the
`tier3-coach` layer map, the agent cannot write this: `git-ops` denies all
`.git/**`, and no roster role has a hooks grant. It runs for humans and agents
alike, and — critically — the git broker refuses `--no-verify`/`-c
core.hooksPath` at its `_run_git` choke point, so an **agent cannot bypass this
hook** even though a human operator can (with their own `--no-verify`; their
call). That is the intended split: safety enforced for all, bypass reserved to
the operator.

## Proposed artifact

**Path:** `hooks/pre-commit` (a *committed*, repo-tracked hooks dir, activated
via `core.hooksPath` — so it is versioned and reviewable, not hidden in
`.git/hooks`).

**Content:**
```sh
#!/bin/sh
# Gleipnir pre-commit hook — secret-scan (always) + opt-in branch/data-file.
#
# Enforcement lives HERE (the VCS layer), not in the git broker. Runs for
# humans and agents. Humans may bypass with `git commit --no-verify` (their
# call); the gleipnir-git broker CANNOT pass --no-verify, so agents cannot
# bypass it. Mirrors src/gleipnir/broker/git/guards.py's advisory logic.
#
# Toggles (env):
#   GLEIPNIR_GIT_STRICT=1            enable branch + data-file checks
#   GLEIPNIR_GIT_PROTECT_BRANCHES=1  branch check only
#   GLEIPNIR_GIT_CHECK_DATA_FILES=1  data-file check only
#   GLEIPNIR_GIT_PROTECTED_BRANCHES  comma list (default main,master)
set -eu

fail=0

# --- Secret-scan (ALWAYS ON — the safety invariant) ---
# Scan only +-added lines of the staged diff.
added=$(git diff --cached --unified=0 | grep '^+' | grep -v '^+++' || true)
if printf '%s\n' "$added" | grep -Eq \
  'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|ghs_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20,}|xox[bps]-[0-9A-Za-z-]{10,}|-----BEGIN[[:space:]].*PRIVATE[[:space:]]KEY-----|AIza[0-9A-Za-z_-]{35}'; then
  echo "pre-commit: potential secret in staged changes — refusing." >&2
  echo "  (false positive? fix the content, or the operator may 'git commit --no-verify')" >&2
  fail=1
fi

# --- Branch protection (OPT-IN) ---
if [ "${GLEIPNIR_GIT_STRICT:-}" = "1" ] || [ "${GLEIPNIR_GIT_PROTECT_BRANCHES:-}" = "1" ]; then
  branch=$(git rev-parse --abbrev-ref HEAD)
  protected="${GLEIPNIR_GIT_PROTECTED_BRANCHES:-main,master}"
  IFS=','; for b in $protected; do
    [ "$branch" = "$(printf '%s' "$b" | tr -d ' ')" ] && {
      echo "pre-commit: commits to protected branch '$branch' are refused (strict)." >&2; fail=1; }
  done; unset IFS
fi

# --- Data-file hygiene (OPT-IN) ---
if [ "${GLEIPNIR_GIT_STRICT:-}" = "1" ] || [ "${GLEIPNIR_GIT_CHECK_DATA_FILES:-}" = "1" ]; then
  if git diff --cached --name-only | grep -Eq '(^|/)\.env(\.|$)|\.(db|sqlite|sqlite3)$|(^|/)\.?venv/'; then
    echo "pre-commit: staged data/artifact file (.env/.db/.sqlite/venv) — refusing (strict)." >&2
    fail=1
  fi
fi

exit $fail
```

**Activation (operator, build mode / shell):**
```sh
mkdir -p hooks
# write hooks/pre-commit with the content above
chmod +x hooks/pre-commit
git config core.hooksPath hooks   # repo-local; versioned hooks dir
```

**Enforces / bypass semantics:** secret-scan runs on every commit for everyone;
branch + data-file are opt-in via env. A human bypasses with `git commit
--no-verify` (deliberately theirs to choose). The `gleipnir-git` broker **cannot**
pass `--no-verify`/`-n`/`-c core.hooksPath` (refused at `_run_git`), so an agent
committing through the broker always runs this hook.

**Scope — team impact (verified):** The hook activation (`git config
core.hooksPath hooks`) is LOCAL to one working copy on one machine — it writes
to `.git/config`, which is never tracked, committed, pushed, or pulled. Team
members who clone or pull this repo:
- **WILL** see `hooks/pre-commit` appear as a normal tracked file (harmless — a
  file's presence alone does nothing).
- **WILL NOT** have it activated: `core.hooksPath` defaults to unset, so git
  falls back to the empty, untracked `.git/hooks/` — zero behaviour change
  unless they deliberately opt in with the same `git config` command, per
  clone.
- Are **NOT** affected by any auto-install: neither `Makefile` (test/lint/build
  → the sandbox entrypoint only) nor `.envrc` (sets only `OPENCODE_CONFIG_DIR`)
  touches git config. No `.github/` or `.gitlab-ci.yml` exists, so there is no
  server-side/remote enforcement layer either — this is purely a local, opt-in
  client-side hook.
- Team members who never touch the Gleipnir agent tooling and just use plain
  `git` are completely unaffected either way: the broker's `--no-verify`
  refusal lives inside `gleipnir-git`'s `_run_git` and only constrains AGENT
  commits routed through that broker; a human's own `git commit` (with or
  without `--no-verify`) is untouched by any of this.

**Bottom line:** adopting this hook is a per-person, per-clone choice. It does
not silently spread to teammates who haven't opted in, and it never restricts a
human's own git usage — only an agent operating through the `gleipnir-git`
broker.

**Honesty label:** cooperative-policy-until-S-2. `core.hooksPath` and the hook
file are operator-settable and (pre-S-2) not structurally locked; the guarantee
that the *agent* can't skip the hook rests on the broker's `_run_git` refusal,
which is real today. Regex secret-scan is a heuristic (false pos/neg) — a floor,
not a proof.

## Decision Analysis

The material tradeoff (secret-scan enforced vs optional; strict-by-default vs
not) was **already converged with the operator** this session:
- Secret-scan is a heuristic that caused false-positive lockups in AETOS →
  **not a hard broker gate**; it lives in the hook (bypassable by the human).
- Branch/data-file checks are **opt-in, default-off** (workflow preference, and
  a hard default would deadlock autonomous L2/L3 operators).
No new material tradeoff — this proposal simply realises those converged
decisions in the correct (VCS) layer.

## Handoff

This is a **substrate/VCS control; the agent cannot and should not write it.**
To apply: **switch to build and** create `hooks/pre-commit` with the content
above, `chmod +x` it, and `git config core.hooksPath hooks`. Optionally add a
`pre-push` mirror. The git broker's `_run_git` hook-bypass refusal (already
implemented + tested) is what makes this binding for agents.
