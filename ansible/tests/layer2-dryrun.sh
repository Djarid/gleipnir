#!/bin/sh
# ansible/tests/layer2-dryrun.sh
#
# Layer 2 (dry-run / check-mode): points `repo` at a DISPOSABLE fixture tree
# (built/torn down by this script — never the real repo) that mimics
# .gleipnir/'s shape (fake marker.key, fake agent-identity.env, absent
# plugins/ to exercise E-2), then runs `ansible-playbook --check` (AC-check)
# and asserts the fixture tree was NOT mutated.
#
# Requires the Ansible toolchain (not installed on this box as of D4) --
# SKIPs (exit 0) rather than FAILs when absent, per the honest
# authored-but-not-yet-executed labelling this harness carries.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)
# shellcheck source=lib/fixture_tree.sh
. "$here/lib/fixture_tree.sh"

if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "SKIP: ansible-playbook not installed (D4 -- authored, not yet executed)"
    exit 0
fi

fix=$(mktemp -d)
trap 'teardown_fixture_tree "$fix"' EXIT
build_fixture_tree "$fix" "$here/fixtures"

before_key_mode=$(file_mode "$fix/.gleipnir/keys/marker.key")
before_launch_mode=$(file_mode "$fix/bin/gleipnir-launch")

echo "== Layer 2: dry-run (--check) against a disposable fixture tree =="
echo "fixture: $fix"

# Note (E-8): act-1's `command:`/AC-4's `command:` tasks are skipped by
# Ansible in --check mode by default (and this playbook additionally
# guards them with `when: not ansible_check_mode` for the AC-4 command +
# assert pair) -- --check is a preview of the `file`-module perm tasks
# (acts 3/4/5/6), not a full dry-run of every act. Documented, not a bug.
ansible-playbook -i "$root/inventory.ini" "$root/site.yml" \
    --check \
    -e "repo=$fix" \
    -e "agent_account_name=staff"

echo "PASS: --check completed without error"

after_key_mode=$(file_mode "$fix/.gleipnir/keys/marker.key")
after_launch_mode=$(file_mode "$fix/bin/gleipnir-launch")

fail=0
if [ "$before_key_mode" != "$after_key_mode" ]; then
    echo "FAIL: --check mutated the fixture key mode ($before_key_mode -> $after_key_mode) -- --check must not mutate anything (AC-check)" >&2
    fail=1
fi
if [ "$before_launch_mode" != "$after_launch_mode" ]; then
    echo "FAIL: --check mutated bin/gleipnir-launch mode ($before_launch_mode -> $after_launch_mode) -- --check must not mutate anything (AC-check)" >&2
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "PASS: fixture tree was not mutated by --check"
fi

exit "$fail"
