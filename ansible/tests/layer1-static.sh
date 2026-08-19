#!/bin/sh
# ansible/tests/layer1-static.sh
#
# Layer 1 (static / syntax): the cheap, always-in-CI layer. Runs
# `ansible-playbook --syntax-check` + `ansible-lint` IF the Ansible
# toolchain is installed (it is NOT installed on this box as of D4 --
# see ansible/tests/README.md), and — regardless of toolchain
# availability — the grep-based structural invariant checks (AC-order,
# AC-env, AC-nolit, AC-mirror) that encode BC-1/BC-2/BC-4 as text, without
# executing any act.
#
# Exit status: 0 if every check that COULD run passed (toolchain-absent
# checks are reported as SKIP, not FAIL, and do not affect the exit code).
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)

fail=0

echo "== Layer 1: static / syntax =="

# --- ansible-playbook --syntax-check (AC-syntax) --------------------------
if command -v ansible-playbook >/dev/null 2>&1; then
    echo "-- ansible-playbook --syntax-check"
    if ansible-playbook -i "$root/inventory.ini" "$root/site.yml" --syntax-check; then
        echo "PASS: --syntax-check"
    else
        echo "FAIL: --syntax-check" >&2
        fail=1
    fi
else
    echo "SKIP: ansible-playbook not installed (D4 -- authored, not yet executed)"
fi

# --- ansible-lint (AC-lint) ------------------------------------------------
if command -v ansible-lint >/dev/null 2>&1; then
    echo "-- ansible-lint"
    if ansible-lint "$root"; then
        echo "PASS: ansible-lint"
    else
        echo "FAIL: ansible-lint" >&2
        fail=1
    fi
else
    echo "SKIP: ansible-lint not installed (D4 -- authored, not yet executed)"
fi

# --- AC-order: act5 key-0600 task textually AFTER act4 recurse task -------
echo "-- AC-order: act5 key task after act4 recurse task"
act4_line=$(grep -n 'act4: harden the 8 LOCKED enforcement paths' "$root/site.yml" | head -1 | cut -d: -f1 || true)
act5_line=$(grep -n 'act5: lock the G-3 key' "$root/site.yml" | head -1 | cut -d: -f1 || true)
if [ -z "${act4_line:-}" ] || [ -z "${act5_line:-}" ]; then
    echo "FAIL: could not locate the act4/act5 task-name markers in site.yml" >&2
    fail=1
elif [ "$act5_line" -le "$act4_line" ]; then
    echo "FAIL: act5 key task (line $act5_line) is NOT after act4 recurse task (line $act4_line)" >&2
    fail=1
else
    echo "PASS: act5 (line $act5_line) after act4 (line $act4_line)"
fi

# --- AC-env: AC-4 task sets environment: GLEIPNIR_MARKER_KEY_FILE ---------
echo "-- AC-env: AC-4 task carries environment: GLEIPNIR_MARKER_KEY_FILE"
ac4_block=$(awk '/name: "AC-4: run the caged preflight/{flag=1} flag{print} flag && /tags: \[ac4\]/{c++; if (c==1) exit}' "$root/site.yml")
if printf '%s' "$ac4_block" | grep -q 'GLEIPNIR_MARKER_KEY_FILE'; then
    echo "PASS: AC-4 task sets the environment fix"
else
    echo "FAIL: AC-4 task is missing environment: GLEIPNIR_MARKER_KEY_FILE (BC-4/E-4)" >&2
    fail=1
fi

# --- AC-nolit: no literal 510 (or bare numeric uid/gid) anywhere ----------
echo "-- AC-nolit: no literal 510 in site.yml / group_vars/all.yml"
if grep -nE '\b510\b' "$root/site.yml" "$root/group_vars/all.yml"; then
    echo "FAIL: literal 510 found (see above) -- uid/gid must come from agent-identity.env (P3)" >&2
    fail=1
else
    echo "PASS: no literal 510"
fi

# --- AC-mirror: enforcement_paths == the 8 LOCKED boundary.py paths -------
echo "-- AC-mirror: enforcement_paths mirrors boundary.py ENFORCEMENT_PATHS"
# LOCKED order per src/gleipnir/preflight/boundary.py:168-222. If boundary.py
# ever changes this set, update BOTH it and group_vars/all.yml, then this
# expected list, together (BC-1: mechanise, never re-author).
expected='agents
stage-role-map.md
decisions
goals
keys
plugins
sandbox
AGENTS.md'
actual=$(grep -oE '^\s+relative:\s*.*' "$root/group_vars/all.yml" | sed -E 's/^\s+relative:\s*//' | tr -d '"'"'"'')
if [ "$actual" = "$expected" ]; then
    echo "PASS: enforcement_paths mirrors boundary.py's 8 LOCKED paths exactly"
else
    echo "FAIL: enforcement_paths mismatch against boundary.py" >&2
    echo "  expected:" >&2
    printf '%s\n' "$expected" | sed 's/^/    /' >&2
    echo "  actual:" >&2
    printf '%s\n' "$actual" | sed 's/^/    /' >&2
    fail=1
fi

# --- plugins/ is the ONLY tolerate_absent: true member (E-2/BC-1) --------
echo "-- plugins/ is the sole tolerate_absent: true entry"
# BUG-3 fix: a bare `grep -c 'tolerate_absent: true' group_vars/all.yml`
# false-FAILs here because the file's own header commentary (a few lines
# above the enforcement_paths list) MENTIONS that exact string in prose
# ("Only `plugins` carries `tolerate_absent: true` (boundary.py's
# EnforcementPath(..., tolerate_absent=True) ..."), so the naive substring
# count is 2 (the comment + the one real YAML entry), not 1 -- a false FAIL
# against genuinely-correct data. Parse the actual YAML list items instead
# of grepping the whole file for a substring: walk item-by-item (each
# delimited by a `- label:` line), track that item's `relative` and
# `tolerate_absent` values, and only count real key: value lines (anchored
# to start-of-line-after-whitespace, which no prose/comment line matches,
# since every comment line here starts with `#`).
tol_summary=$(awk '
    function flush() {
        if (rel != "") {
            if (tol == "true") {
                tol_true_count++
                if (rel == "plugins") { plugins_match++ } else { other_rel = rel }
            }
        }
    }
    /^[[:blank:]]*-[[:blank:]]*label:/ { flush(); rel = ""; tol = "" }
    /^[[:blank:]]*relative:[[:blank:]]*/ { rel = $2 }
    /^[[:blank:]]*tolerate_absent:[[:blank:]]*true[[:blank:]]*$/ { tol = "true" }
    END { flush(); printf "%d %d %s", tol_true_count + 0, plugins_match + 0, (other_rel == "" ? "-" : other_rel) }
' "$root/group_vars/all.yml")
tol_true_count=$(printf '%s' "$tol_summary" | cut -d' ' -f1)
plugins_match=$(printf '%s' "$tol_summary" | cut -d' ' -f2)
other_rel=$(printf '%s' "$tol_summary" | cut -d' ' -f3)

if [ "${tol_true_count:-0}" -eq 1 ] && [ "${plugins_match:-0}" -eq 1 ]; then
    echo "PASS: exactly one tolerate_absent: true, on plugins"
else
    echo "FAIL: expected exactly one tolerate_absent: true entry, on the plugins item (found count=${tol_true_count:-0}, non-plugins offender=${other_rel:-none})" >&2
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "== Layer 1: ALL CHECKS THAT RAN PASSED =="
else
    echo "== Layer 1: FAILURES ABOVE ==" >&2
fi
exit "$fail"
