#!/bin/sh
# ansible/tests/run.sh
#
# Runs all three test layers (see README.md) and prints one honest summary.
#
# D4 HONESTY LABEL: Ansible (ansible/ansible-playbook/ansible-lint) is NOT
# installed on this box, and the S-2 sandbox has no [profile.ansible] (only
# python/node/broker) -- so most of what this script runs will report SKIP,
# not PASS, until the operator installs Ansible (brew/pipx) or a future
# sandbox profile lands. This is authored-but-not-yet-executed, exactly as
# converged in ../../.gleipnir/decisions/s2-caged-ansible.md D4. Do not
# read a clean exit from this script as "the Ansible playbook was verified
# green" -- read the SKIP/PASS/FAIL lines it prints.
set -eu

here=$(cd "$(dirname "$0")" && pwd)

overall_fail=0

if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "############################################################"
    echo "# Ansible toolchain NOT installed on this box (D4)."
    echo "# ansible-playbook / ansible / ansible-lint: not found."
    echo "# The layers below will report SKIP for anything that needs"
    echo "# to execute Ansible, and PASS/FAIL only for the pure-text"
    echo "# grep-based structural checks in layer 1."
    echo "# Install: brew install ansible ansible-lint  (or pipx)."
    echo "############################################################"
fi

for layer in layer1-static.sh layer2-dryrun.sh layer3-idempotency.sh; do
    echo
    echo ">>> running $layer"
    # Invoked via `sh` rather than direct exec so this works even if the
    # execute bit was not preserved (e.g. a fresh checkout/tarball) --
    # every script in this directory is written to be `sh`-invocable.
    if sh "$here/$layer"; then
        echo ">>> $layer: OK (see PASS/SKIP lines above)"
    else
        echo ">>> $layer: FAILED" >&2
        overall_fail=1
    fi
done

echo
if [ "$overall_fail" -eq 0 ]; then
    echo "== ansible/tests/run.sh: no FAILures (some checks may be SKIPped -- see above; D4) =="
else
    echo "== ansible/tests/run.sh: FAILURES ABOVE ==" >&2
fi
exit "$overall_fail"
