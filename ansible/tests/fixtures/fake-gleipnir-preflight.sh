#!/bin/sh
# ansible/tests/fixtures/fake-gleipnir-preflight.sh
#
# A lightweight stand-in for the real bin/gleipnir-preflight, copied into a
# DISPOSABLE fixture tree's bin/gleipnir-preflight by ansible/tests/lib/
# fixture_tree.sh (layer-2/layer-3 harnesses).
#
# WHY A STAND-IN, NOT THE REAL PREFLIGHT: the real bin/gleipnir-preflight
# execs "$repo/.venv/bin/python" -m gleipnir.preflight from *its own*
# on-disk location (bin/gleipnir-preflight:19-21), and boundary.py's
# behavioural probe is anchored to that real checkout's .venv (L-4) — it is
# not meant to run rootless against an arbitrary disposable directory that
# has no venv. boundary.py's own OS-behavioural-probe logic already has its
# own unit tests (tests/test_preflight_decision.py and friends); THIS
# harness's job is narrower: prove the Ansible task *plumbing* around that
# binary (the environment: fix survives, the rc is checked, act-5-then-AC-4
# ordering holds) — not to re-derive boundary.py's own verdict logic. A
# small stand-in that honours the same three-way rc contract (0 = CLOSED,
# 1 = REFUSE, ignoring 2/--override-ack since --mode caged never emits it)
# is the honest, minimal way to test that plumbing without a live venv.
#
# Contract mirrored (src/gleipnir/preflight/__main__.py:147-156, `--mode
# caged` branch): rc 0 = CLOSED, rc 1 = REFUSE. All CLI args
# (--agent-uid/--agent-gid/--mode/...) are accepted and ignored — this stub
# checks exactly one thing: is GLEIPNIR_MARKER_KEY_FILE set, present, and
# mode 600? That is the one perm the layer-2/3 harness manipulates to
# exercise both the pass path and the AC-4-fail path (BC-7 "no false
# green" proof).
set -eu

key="${GLEIPNIR_MARKER_KEY_FILE:-}"

if [ -z "$key" ]; then
    echo "fake-gleipnir-preflight: GLEIPNIR_MARKER_KEY_FILE is unset -- the" >&2
    echo "  Ansible AC-4 task's 'environment:' fix did not survive (BC-4/E-4)." >&2
    exit 1
fi

if [ ! -f "$key" ]; then
    echo "fake-gleipnir-preflight: key file not found: $key" >&2
    exit 1
fi

mode=$(stat -f '%Lp' "$key" 2>/dev/null || stat -c '%a' "$key" 2>/dev/null)

if [ "$mode" = "600" ]; then
    echo "fake-gleipnir-preflight: CLOSED (key mode 600) -- rc 0"
    exit 0
fi

echo "fake-gleipnir-preflight: REFUSE (key mode $mode, want 600) -- rc 1" >&2
exit 1
