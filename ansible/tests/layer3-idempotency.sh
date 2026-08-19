#!/bin/sh
# ansible/tests/layer3-idempotency.sh
#
# Layer 3 (idempotency + the AC-4-fail "no false green" proof): the ONLY
# layer that runs real `chmod`/`chown` (against a DISPOSABLE fixture tree,
# never the real repo, and never the destructive act-1 uid/gid create --
# that is excluded via `--skip-tags destructive`).
#
# Two sub-tests, per D3/AC-idem/AC-4-fail:
#   3a. Idempotency -- run the perms portion twice against a fresh fixture;
#       the SECOND run must report changed=0.
#   3b. AC-4-fail    -- with acts 3/4/5/6 excluded (`--tags ac4`, isolating
#       just the pre-tasks + the AC-4 command/assert pair), a fixture whose
#       key mode is left wrong must make the run FAIL at the AC-4 assert.
#
# `agent_account_name` is overridden to `staff` (a group that genuinely
# exists, unprivileged) rather than the real `gleipniragent`, so act-3's
# `chgrp` step exercises real, idempotent group-set logic without ever
# creating an OS group/account (which would require root -- exactly the
# privilege this harness avoids). This substitutes the group NAME only; it
# does not change any of the mode-bit / ordering logic being proven.
#
# Requires the Ansible toolchain (not installed on this box as of D4) --
# SKIPs (exit 0) rather than FAILs when absent.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)
# shellcheck source=lib/fixture_tree.sh
. "$here/lib/fixture_tree.sh"

if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "SKIP: ansible-playbook not installed (D4 -- authored, not yet executed)"
    exit 0
fi

fail=0

# --- 3a. Idempotency (AC-idem) --------------------------------------------
echo "== Layer 3a: idempotency (real chmod on a disposable fixture, run twice) =="

fix_a=$(mktemp -d)
build_fixture_tree "$fix_a" "$here/fixtures"
echo "fixture: $fix_a"

run1_out=$(ansible-playbook -i "$root/inventory.ini" "$root/site.yml" \
    --skip-tags destructive \
    -e "repo=$fix_a" \
    -e "agent_account_name=staff" 2>&1) || run1_rc=$?
run1_rc=${run1_rc:-0}
echo "$run1_out"

if [ "$run1_rc" -ne 0 ]; then
    echo "FAIL: first (converging) run did not exit 0" >&2
    fail=1
else
    run2_out=$(ansible-playbook -i "$root/inventory.ini" "$root/site.yml" \
        --skip-tags destructive \
        -e "repo=$fix_a" \
        -e "agent_account_name=staff" 2>&1) || run2_rc=$?
    run2_rc=${run2_rc:-0}
    echo "$run2_out"

    if [ "$run2_rc" -ne 0 ]; then
        echo "FAIL: second run did not exit 0" >&2
        fail=1
    else
        changed=$(printf '%s\n' "$run2_out" | grep -Eo 'changed=[0-9]+' | tail -1 | cut -d= -f2 || true)
        if [ "${changed:-unknown}" = "0" ]; then
            echo "PASS: second run reported changed=0 (AC-idem)"
        else
            echo "FAIL: second run reported changed=${changed:-unknown} (want 0, AC-idem)" >&2
            fail=1
        fi

        key_mode=$(file_mode "$fix_a/.gleipnir/keys/marker.key")
        if [ "$key_mode" = "600" ]; then
            echo "PASS: final key mode is 0600 (AC-order proven at runtime)"
        else
            echo "FAIL: final key mode is $key_mode, want 600" >&2
            fail=1
        fi
    fi
fi

teardown_fixture_tree "$fix_a"

# --- 3b. AC-4-fail (no false green) ---------------------------------------
echo "== Layer 3b: AC-4-fail path (wrong key mode -> REFUSE -> run fails) =="

fix_b=$(mktemp -d)
build_fixture_tree "$fix_b" "$here/fixtures"
echo "fixture: $fix_b"
# build_fixture_tree already leaves the key at mode 644 (deliberately
# wrong); running with --tags ac4 means acts 3/4/5/6 never execute, so
# nothing repairs it before the AC-4 assert runs.

set +e
run3_out=$(ansible-playbook -i "$root/inventory.ini" "$root/site.yml" \
    --tags ac4 \
    -e "repo=$fix_b" \
    -e "agent_account_name=staff" 2>&1)
run3_rc=$?
set -e
echo "$run3_out"

if [ "$run3_rc" -eq 0 ]; then
    echo "FAIL: run with a drifted key mode reported success -- false green (violates BC-7)" >&2
    fail=1
elif printf '%s\n' "$run3_out" | grep -qi 'S-2 caged boundary NOT closed'; then
    echo "PASS: run failed at the AC-4 assert, naming the REFUSE verdict (BC-7)"
else
    echo "FAIL: run failed (rc=$run3_rc) but not with the expected AC-4 assert message" >&2
    fail=1
fi

teardown_fixture_tree "$fix_b"

if [ "$fail" -eq 0 ]; then
    echo "== Layer 3: ALL CHECKS THAT RAN PASSED =="
else
    echo "== Layer 3: FAILURES ABOVE ==" >&2
fi
exit "$fail"
