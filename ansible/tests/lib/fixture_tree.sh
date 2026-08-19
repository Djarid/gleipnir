# ansible/tests/lib/fixture_tree.sh
#
# Shared helpers for the layer-2 (dry-run) and layer-3 (idempotency) test
# harnesses: build and tear down a DISPOSABLE fixture tree that mimics the
# shape of .gleipnir/ well enough to exercise the playbook's task plumbing,
# without ever touching the real repo. Sourced, not executed directly:
#   . "$(dirname "$0")/lib/fixture_tree.sh"
#
# Deliberately NOT a full replica of .gleipnir/ — only what the playbook's
# acts 3/4/5/6 + AC-4 touch: the 8 enforcement paths (boundary.py mirror,
# minus plugins/ which is left ABSENT on purpose to exercise E-2 tolerance),
# the Tier-0/1/2 writable dirs act-3 chgrp's, a fake key, a fake
# agent-identity.env (uid/gid 9999, never 510), and fake bin/gleipnir-launch
# + bin/gleipnir-preflight stand-ins (see fixtures/fake-gleipnir-preflight.sh
# for why a stand-in, not the real preflight).

# file_mode PATH -- portable (BSD/GNU) octal mode read, used by the layer-2
# "mutated nothing" check and the layer-3 idempotency/AC-4-fail assertions.
#
# ORDER MATTERS (do not reorder to BSD-first): GNU coreutils `stat` (common on
# a Homebrew/`coreutils` PATH) treats `-f` as "filesystem info", printing a
# multi-line fsinfo dump to STDOUT and exiting 0 -- so a `stat -f ... || stat -c`
# fallback NEVER reaches the `-c` branch and captures garbage as the "mode"
# (observed: spurious layer-2 "mutation" + layer-3a false REFUSE). Trying the
# GNU `-c '%a'` form FIRST is safe: on BSD `stat`, `-c` is unknown and exits
# non-zero cleanly, so the `-f '%Lp'` (BSD octal) fallback fires correctly.
file_mode() {
    stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1"
}

# build_fixture_tree FIXTURE_DIR FIXTURES_SRC_DIR
#   FIXTURE_DIR      -- an already-created empty directory (e.g. mktemp -d).
#   FIXTURES_SRC_DIR -- ansible/tests/fixtures (holds the two checked-in
#                       templates this copies in).
build_fixture_tree() {
    fix="$1"
    src="$2"

    mkdir -p "$fix/bin"
    mkdir -p "$fix/src"

    # The 8 LOCKED enforcement paths (boundary.py mirror) -- EXCEPT
    # plugins/, which is deliberately left absent to exercise the E-2
    # tolerate_absent path (BC-1).
    mkdir -p "$fix/.gleipnir/agents"
    mkdir -p "$fix/.gleipnir/decisions"
    mkdir -p "$fix/.gleipnir/goals"
    mkdir -p "$fix/.gleipnir/keys"
    mkdir -p "$fix/.gleipnir/sandbox"
    # (no plugins/ -- absence is the point, E-2)

    # Tier-0/1/2 writable dirs act-3 chgrp's + g+w's.
    mkdir -p "$fix/.gleipnir/plans"
    mkdir -p "$fix/.gleipnir/var/tmp"
    mkdir -p "$fix/.gleipnir/logs"
    mkdir -p "$fix/.gleipnir/memory"
    mkdir -p "$fix/.gleipnir/lessons"

    printf '# fixture stand-in\n' > "$fix/.gleipnir/AGENTS.md"
    printf '# fixture stand-in\n' > "$fix/.gleipnir/stage-role-map.md"
    printf '# fixture stand-in\n' > "$fix/.gleipnir/agents/orchestrator.md"
    printf '# fixture stand-in\n' > "$fix/.gleipnir/decisions/dummy.md"
    printf '# fixture stand-in\n' > "$fix/.gleipnir/goals/dummy.md"
    printf 'fixture: true\n' > "$fix/.gleipnir/sandbox/dummy.yml"
    printf '# fixture src marker\n' > "$fix/src/.keep"

    # The fake G-3 key -- starts at a DELIBERATELY WRONG mode (644) so both
    # AC-idem (act-5 must converge it to 600) and AC-4-fail (a run that
    # never reaches act-5, e.g. --tags ac4, must see it still wrong and
    # REFUSE) are exercisable from the same starting fixture.
    printf 'FAKE-KEY-NOT-REAL\n' > "$fix/.gleipnir/keys/marker.key"
    chmod 644 "$fix/.gleipnir/keys/marker.key"

    cp "$src/agent-identity.env" "$fix/.gleipnir/agent-identity.env"

    cp "$src/fake-gleipnir-preflight.sh" "$fix/bin/gleipnir-preflight"
    chmod 755 "$fix/bin/gleipnir-preflight"

    printf '#!/bin/sh\necho "fixture stand-in -- not the real gleipnir-launch"\n' \
        > "$fix/bin/gleipnir-launch"
    chmod 644 "$fix/bin/gleipnir-launch"   # act-6 should flip this to 0755
}

# teardown_fixture_tree FIXTURE_DIR
#   Refuses to rm -rf anything that doesn't look like a mktemp -d path, as a
#   defence-in-depth guard against a typo'd/empty argument nuking something
#   real.
teardown_fixture_tree() {
    fix="$1"
    case "$fix" in
        /tmp/*|/var/folders/*/T/*)
            rm -rf "$fix"
            ;;
        *)
            echo "teardown_fixture_tree: refusing to rm -rf unexpected path: '$fix'" >&2
            return 1
            ;;
    esac
}
