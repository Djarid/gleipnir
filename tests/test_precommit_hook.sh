#!/bin/sh
# Conformance test for hooks/pre-commit's config-scan wiring.
#
# Proves the shell hook maps the config-scan CLI exit-code contract
# (0=CLOSED/1=REFUSE/2=PROCEED_UNCLOSED/else=fail-closed) IDENTICALLY to
# .gleipnir/plugins/git-guard.ts's decideFromExit/PreflightUnavailable
# contract, is ALWAYS-ON (no GLEIPNIR_GIT_STRICT gate), does not weaken the
# existing secret-scan (neither check short-circuits the other), preserves
# `set -eu`, and does not regress the opt-in branch/data-file checks.
#
# Driven against a STUB `bin/gleipnir-preflight` in a throwaway temp git repo
# (a tiny shell script that exits with a controlled code), mirroring
# tests/test_git_guard.mjs's `makeRepoWithStub` approach — see .gleipnir/plans/
# config-scan-precommit-hook.md, Stress-test ST-1..ST-10.
#
# Run with:  sh tests/test_precommit_hook.sh
# (on the HOST, NOT via bin/gleipnir-sandbox test — this exercises the real
# hook against a real temp git index/repo; the sandbox's python:3.12-slim
# image has no fixture harness for this and is not the right arbiter for a
# #!/bin/sh VCS hook. Mirrors the host-run precedent of test_git_guard.mjs /
# test_sequence_gate.mjs, which are likewise run directly with `node --test`,
# not sandboxed.)
#
# EXECUTION NOTE (D-H): this script is AUTHORED by gleipnir-code but EXECUTED
# by the build-session/orchestrator — gleipnir-code's bash grant denies
# `sh*`/`bash*`/`*` (only `bin/gleipnir-sandbox test|lint` exact-match is
# allowed), so it cannot invoke this script itself.
#
# META-HAZARD GUARD: every fixture repo below is a throwaway `mktemp -d`
# directory with its OWN stub `bin/gleipnir-preflight`. This script NEVER
# stages anything in the real repo, NEVER points the real hook at a bad real
# config, and NEVER commits. `safe_rm_tree` refuses to `rm -rf` anything
# outside the temp-fixture naming convention, as a second guard against a
# typo'd path accidentally targeting something real.
#
# ST-10 is the one case that touches the real repo, and it is READ-ONLY: it
# invokes the real `bin/gleipnir-preflight config-scan` directly (the same
# scan git-guard.ts already runs before every broker git write, with no
# staging/commit side effects) against the real, unmodified repo state, to
# confirm the framework does not lock itself out. It stages nothing.

set -u

# ---------------------------------------------------------------------------
# Harness plumbing
# ---------------------------------------------------------------------------

TOTAL=0
FAILURES=0
ALL_TMP_DIRS=""

here=$(CDPATH= cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$here/.." && pwd)
HOOK_SRC="$REPO_ROOT/hooks/pre-commit"

pass_case() {
  TOTAL=$((TOTAL + 1))
  echo "PASS: $1"
}

fail_case() {
  TOTAL=$((TOTAL + 1))
  FAILURES=$((FAILURES + 1))
  echo "FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "      $2" | sed 's/^/      /'
  fi
}

# Refuse to rm -rf anything that isn't one of OUR temp fixtures (meta-hazard
# guard — see header). Every fixture dir this script creates is named via the
# gleipnir-hook-test- mktemp template below.
safe_rm_tree() {
  d="$1"
  case "$d" in
    */gleipnir-hook-test-*) rm -rf "$d" ;;
    *)
      echo "REFUSING to rm -rf non-fixture path: $d" >&2
      return 1
      ;;
  esac
}

cleanup_all() {
  for d in $ALL_TMP_DIRS; do
    safe_rm_tree "$d" 2>/dev/null || true
  done
}
trap cleanup_all EXIT

# Build a throwaway git repo with one seed commit (so HEAD/branch exist for
# the opt-in checks) and disabled gpgsign (avoid host-config interference).
make_repo() {
  dir=$(mktemp -d "${TMPDIR:-/tmp}/gleipnir-hook-test-XXXXXX")
  ALL_TMP_DIRS="$ALL_TMP_DIRS $dir"
  git -C "$dir" init -q
  git -C "$dir" config user.email "test@example.com"
  git -C "$dir" config user.name "Test"
  git -C "$dir" config commit.gpgsign false
  printf 'seed\n' >"$dir/seed.txt"
  git -C "$dir" add seed.txt
  git -C "$dir" commit -q -m seed
  # Deterministic branch name regardless of the host's init.defaultBranch.
  git -C "$dir" branch -m main
  cp "$HOOK_SRC" "$dir/pre-commit"
  chmod +x "$dir/pre-commit"
  printf '%s\n' "$dir"
}

# Install a stub bin/gleipnir-preflight that exits with a controlled code,
# asserting it is invoked with the config-scan subcommand (mirrors
# test_git_guard.mjs's makeRepoWithStub).
install_stub() {
  dir="$1"
  code="$2"
  mkdir -p "$dir/bin"
  cat >"$dir/bin/gleipnir-preflight" <<EOF
#!/bin/sh
[ "\$1" = "config-scan" ] || { echo "stub: expected config-scan, got \$1" >&2; exit 99; }
echo "stub config-scan (exit $code)" >&2
exit $code
EOF
  chmod +x "$dir/bin/gleipnir-preflight"
}

# Stage a fake secret that MATCHES the secret-scan AWS-key pattern
# (AKIA[0-9A-Z]{16}) as a new file inside the disposable fixture repo.
#
# The literal is assembled at RUNTIME from fragments so that no complete
# secret-scan-matching substring ever appears in THIS test's source. Otherwise
# committing this test file itself would (correctly) trip the very secret-scan
# it exercises -- a fixture that looks like a real key must not live verbatim in
# a tracked file. The concatenation below produces the full matching key only in
# the fixture's ephemeral secret.txt, never in tests/test_precommit_hook.sh.
stage_secret() {
  dir="$1"
  fake_key="AKIA$(printf 'ABCDEFGH12345678')"   # 20-char AWS-key shape, assembled at runtime only
  printf '%s\n' "$fake_key" >"$dir/secret.txt"
  git -C "$dir" add secret.txt
}

# Stage a data/artifact file the opt-in data-file check should flag.
stage_data_file() {
  dir="$1"
  printf 'SOME_VAR=1\n' >"$dir/.env"
  git -C "$dir" add .env
}

# Run the copied hook with cwd=$dir, optionally with extra env (passed as
# "NAME=VALUE" args), capturing combined output + exit code.
# Sets globals: RC, OUT.
run_hook() {
  dir="$1"
  shift
  envstr=""
  for kv in "$@"; do
    envstr="$envstr $kv"
  done
  OUT=$(cd "$dir" && env $envstr sh ./pre-commit 2>&1)
  RC=$?
}

# ---------------------------------------------------------------------------
# ST-1: clean config (stub exit 0), no secret -> hook exits 0 (proceed)
# ---------------------------------------------------------------------------
test_st1() {
  dir=$(make_repo)
  install_stub "$dir" 0
  run_hook "$dir"
  if [ "$RC" -eq 0 ]; then
    pass_case "ST-1 (clean config -> proceed)"
  else
    fail_case "ST-1 (clean config -> proceed)" "expected rc=0, got rc=$RC; output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-2: config-scan REFUSE (stub exit 1) -> hook exits non-zero (block)
# ---------------------------------------------------------------------------
test_st2() {
  dir=$(make_repo)
  install_stub "$dir" 1
  run_hook "$dir"
  if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -q 'REFUSED'; then
    pass_case "ST-2 (config-scan REFUSE -> block)"
  else
    fail_case "ST-2 (config-scan REFUSE -> block)" "expected rc!=0 and 'REFUSED' in output; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-3: bin/gleipnir-preflight missing entirely -> fail-closed block
# ---------------------------------------------------------------------------
test_st3() {
  dir=$(make_repo)
  # deliberately do NOT install bin/gleipnir-preflight
  run_hook "$dir"
  if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -q 'missing or not executable' && ! printf '%s' "$OUT" | grep -q 'REFUSED'; then
    pass_case "ST-3 (CLI missing -> fail-closed block, broken-prerequisite class)"
  else
    fail_case "ST-3 (CLI missing -> fail-closed block, broken-prerequisite class)" "expected rc!=0, 'missing or not executable' present, 'REFUSED' absent; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-3b: bin/gleipnir-preflight present but NOT executable (mode 0644) ->
# same fail-closed broken-prerequisite class (the test_bin_executable.py
# regression class).
# ---------------------------------------------------------------------------
test_st3b() {
  dir=$(make_repo)
  mkdir -p "$dir/bin"
  printf '#!/bin/sh\nexit 0\n' >"$dir/bin/gleipnir-preflight"
  chmod 0644 "$dir/bin/gleipnir-preflight"
  run_hook "$dir"
  if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -q 'missing or not executable'; then
    pass_case "ST-3b (CLI non-exec -> fail-closed block)"
  else
    fail_case "ST-3b (CLI non-exec -> fail-closed block)" "expected rc!=0 and 'missing or not executable'; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-4: config-scan exit 2 (PROCEED_UNCLOSED) -> hook exits 0, warns
# ---------------------------------------------------------------------------
test_st4() {
  dir=$(make_repo)
  install_stub "$dir" 2
  run_hook "$dir"
  if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'PROCEED_UNCLOSED'; then
    pass_case "ST-4 (exit 2 PROCEED_UNCLOSED -> warn + proceed)"
  else
    fail_case "ST-4 (exit 2 PROCEED_UNCLOSED -> warn + proceed)" "expected rc=0 and 'PROCEED_UNCLOSED' in output; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-5: unexpected exit codes (7, 42) -> fail-closed block
# ---------------------------------------------------------------------------
test_st5() {
  for code in 7 42; do
    dir=$(make_repo)
    install_stub "$dir" "$code"
    run_hook "$dir"
    if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -q 'unexpected exit code'; then
      pass_case "ST-5 (unexpected exit code $code -> fail-closed block)"
    else
      fail_case "ST-5 (unexpected exit code $code -> fail-closed block)" "expected rc!=0 and 'unexpected exit code' in output; got rc=$RC, output: $OUT"
    fi
  done
}

# ---------------------------------------------------------------------------
# ST-6: secret-scan not weakened — config-scan CLOSED (0) but a secret is
# staged -> hook still blocks (secret-scan fires independently).
# ---------------------------------------------------------------------------
test_st6() {
  dir=$(make_repo)
  install_stub "$dir" 0
  stage_secret "$dir"
  run_hook "$dir"
  if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -q 'potential secret'; then
    pass_case "ST-6 (secret-scan still fires when config-scan passes)"
  else
    fail_case "ST-6 (secret-scan still fires when config-scan passes)" "expected rc!=0 and 'potential secret'; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-7: both checks run, neither short-circuits the other — config-scan
# REFUSEs (1) AND a secret is staged -> hook blocks, BOTH messages present.
# ---------------------------------------------------------------------------
test_st7() {
  dir=$(make_repo)
  install_stub "$dir" 1
  stage_secret "$dir"
  run_hook "$dir"
  if [ "$RC" -ne 0 ] \
    && printf '%s' "$OUT" | grep -q 'potential secret' \
    && printf '%s' "$OUT" | grep -q 'REFUSED'; then
    pass_case "ST-7 (both secret-scan and config-scan fire; no short-circuit)"
  else
    fail_case "ST-7 (both secret-scan and config-scan fire; no short-circuit)" "expected rc!=0 with BOTH 'potential secret' and 'REFUSED'; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-8: `set -eu` preserved — the config-scan mapping actually runs (i.e. the
# hook does not abort on config-scan's non-zero exit before printing the
# mapped verdict). Proven by asserting the mapped-verdict message is present
# for both a REFUSE (1) and an unexpected code (7) — if `set -e` had aborted
# the hook at the bare invocation, no mapped message would ever print, and
# the hook's PLAIN exit code (fail-fast, no message) would be
# indistinguishable from a real ERR-exit abort rather than the intended
# mapping. This is an explicit, separately-named assertion per the plan
# (distinct from ST-2/ST-5's own pass/fail, even though it re-uses the same
# fixtures) so a regression to a bare (unguarded) `"$cli" config-scan`
# invocation is caught by name.
# ---------------------------------------------------------------------------
test_st8() {
  dir=$(make_repo)
  install_stub "$dir" 1
  run_hook "$dir"
  refuse_ok=0
  printf '%s' "$OUT" | grep -q 'REFUSED' && refuse_ok=1

  dir2=$(make_repo)
  install_stub "$dir2" 7
  run_hook "$dir2"
  unexpected_ok=0
  printf '%s' "$OUT" | grep -q 'unexpected exit code' && unexpected_ok=1

  if [ "$refuse_ok" -eq 1 ] && [ "$unexpected_ok" -eq 1 ]; then
    pass_case "ST-8 (set -eu preserved: mapping runs to completion, not aborted by set -e)"
  else
    fail_case "ST-8 (set -eu preserved: mapping runs to completion, not aborted by set -e)" "mapped-verdict message missing on one of REFUSE/unexpected-code fixtures (refuse_ok=$refuse_ok unexpected_ok=$unexpected_ok)"
  fi
}

# ---------------------------------------------------------------------------
# ST-9: opt-in branch/data-file checks still function alongside config-scan
# (regression guard). GLEIPNIR_GIT_STRICT=1, on branch "main" (protected),
# with a staged .env file, and config-scan CLOSED (0) — both opt-in checks
# must still fire.
# ---------------------------------------------------------------------------
test_st9() {
  dir=$(make_repo)
  install_stub "$dir" 0
  stage_data_file "$dir"
  run_hook "$dir" "GLEIPNIR_GIT_STRICT=1"
  if [ "$RC" -ne 0 ] \
    && printf '%s' "$OUT" | grep -q 'protected branch' \
    && printf '%s' "$OUT" | grep -q 'data/artifact file'; then
    pass_case "ST-9 (opt-in branch + data-file checks intact alongside config-scan)"
  else
    fail_case "ST-9 (opt-in branch + data-file checks intact alongside config-scan)" "expected rc!=0 with BOTH 'protected branch' and 'data/artifact file'; got rc=$RC, output: $OUT"
  fi
}

# ---------------------------------------------------------------------------
# ST-10: live-repo self-pass — no lockout. READ-ONLY: invokes the REAL
# bin/gleipnir-preflight config-scan directly against the real repo (no
# staging, no commit, no stub) and asserts it reports CLOSED (exit 0) — the
# framework's own current config does not lock itself out. This is the one
# case that is executed by the build-session/orchestrator against the real
# checkout, per the plan's D-H executor split; gleipnir-code authors it but
# does not run it.
# ---------------------------------------------------------------------------
test_st10() {
  real_cli="$REPO_ROOT/bin/gleipnir-preflight"
  if [ ! -x "$real_cli" ]; then
    fail_case "ST-10 (live-repo self-pass)" "real CLI '$real_cli' is not executable in this checkout — cannot verify (this itself would be the ST-3-class broken-prerequisite the hook fails closed on)"
    return
  fi
  st10_code=0
  st10_out=$(cd "$REPO_ROOT" && "$real_cli" config-scan 2>&1) || st10_code=$?
  if [ "$st10_code" -eq 0 ]; then
    pass_case "ST-10 (live-repo self-pass -- real config-scan reports CLOSED, no lockout)"
  else
    fail_case "ST-10 (live-repo self-pass -- real config-scan reports CLOSED, no lockout)" "expected exit 0 against the real repo, got $st10_code: $st10_out"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

test_st1
test_st2
test_st3
test_st3b
test_st4
test_st5
test_st6
test_st7
test_st8
test_st9
test_st10

echo ""
echo "$TOTAL case(s) run, $FAILURES failed."
if [ "$FAILURES" -eq 0 ]; then
  echo "ALL PASS"
  exit 0
else
  echo "SOME FAILED"
  exit 1
fi
