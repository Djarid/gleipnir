#!/bin/sh
# ansible/tests/run.sh
#
# Runs all three test layers (see README.md) and prints one honest summary.
#
# STATUS (D4-FU done): this harness has been run and passes green with Ansible
# installed (see ../../.gleipnir/decisions/s2-caged-ansible.md D4/D5/D6). It
# still degrades honestly: on a box WITHOUT ansible/ansible-playbook/ansible-lint
# (or with no [profile.ansible] sandbox), the layers that need the toolchain
# print SKIP, not PASS -- so always read the SKIP/PASS/FAIL lines below, not just
# the exit code. The banner further down fires only when the toolchain is absent.
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
