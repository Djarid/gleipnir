#!/bin/sh
# ansible/tests/signer-static.sh
#
# Static (text/grep-only) checks S1-S6 for the signer service-account
# provisioning artifacts:
#   - ansible/signer.yml
#   - ansible/signer-teardown.yml
#   - ansible/tasks/create-service-account.yml
#   - ansible/site.yml
#
# Mirrors ansible/tests/layer1-static.sh's shape (fail=0 accumulator,
# PASS/FAIL echo lines, `exit "$fail"`), and needs NO Ansible toolchain --
# pure text/grep, exactly like layer1-static.sh's AC-* half. It genuinely
# runs today, with or without ansible-core installed.
#
# Usage: signer-static.sh [root]
#   root defaults to the real ansible/ directory, computed the same way
#   layer1-static.sh does. Pass a fixture directory (e.g.
#   ansible/tests/fixtures/broken/F3/) to run the same checks against a
#   single-defect tree instead.
#
# Each check degrades to FAIL -- never SKIP -- if a file it needs is
# missing at the given root (J23: a fixture/root missing a required file
# must never be silently waved through).
#
# On failure each check emits a machine-greppable reason token of the form
# FAIL[S<n>/<reason>] so a fixture harness can assert exactly which check
# fired, not merely that something did.
#
# Exit status: 0 if S1-S6 all passed.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
default_root=$(cd "$here/.." && pwd)
root="${1:-$default_root}"

signer_yml="$root/signer.yml"
teardown_yml="$root/signer-teardown.yml"
task_file="$root/tasks/create-service-account.yml"
site_yml="$root/site.yml"

fail=0

echo "== signer-static: S1-S6 (root=$root) =="

# --- small helpers ----------------------------------------------------------

# Trim leading/trailing spaces and one pair of surrounding double quotes.
clean_val() {
    v=$1
    v=${v%%#*}
    while [ "${v% }" != "$v" ]; do v=${v% }; done
    while [ "${v# }" != "$v" ]; do v=${v# }; done
    case "$v" in
        \"*\") v=${v#\"}; v=${v%\"} ;;
    esac
    printf '%s' "$v"
}

# --- S1: no hardcoded uid/gid ------------------------------------------------
# Every line matching UniqueID, PrimaryGroupID, -UID or -GID in signer.yml /
# the shared task-file must contain a {{ ... }} template and no bare digit
# run outside that template.
check_s1() {
    label="S1"; token="hardcoded-uid"
    bad=0
    for f in "$signer_yml" "$task_file"; do
        if [ ! -f "$f" ]; then
            echo "FAIL[$label/$token]: missing file $f" >&2
            bad=1
            continue
        fi
        matches=$(grep -nE 'UniqueID|PrimaryGroupID|-UID|-GID' "$f" || true)
        [ -z "$matches" ] && continue
        while IFS= read -r m; do
            [ -z "$m" ] && continue
            content=${m#*:}
            # Skip YAML `- name:` / `name:` description lines -- a human-
            # readable task TITLE (e.g. `- name: "... PrimaryGroupID"`) is
            # not a command/attribute assignment and must not be judged as
            # a hardcoded-uid violation. Only strip a leading "- " list
            # marker when it is followed by whitespace (a real list-item
            # marker), so a folded-command continuation line beginning
            # with "-UID"/"-GID" (no space after the dash) is untouched.
            trimmed=$(printf '%s' "$content" | sed -E 's/^[[:space:]]+//; s/^-[[:space:]]+//')
            case "$trimmed" in
                name:*) continue ;;
            esac
            if ! printf '%s' "$content" | grep -q '{{'; then
                echo "FAIL[$label/$token]: no {{ }} template on: $m ($f)" >&2
                bad=1
                continue
            fi
            stripped=$(printf '%s' "$content" | sed -E 's/\{\{[^}]*\}\}//g')
            if printf '%s' "$stripped" | grep -qE '[0-9]+'; then
                echo "FAIL[$label/$token]: bare digit run outside template on: $m ($f)" >&2
                bad=1
            fi
        done <<EOF
$matches
EOF
    done
    if [ "$bad" -eq 0 ]; then
        echo "PASS: S1 no hardcoded uid/gid"
    else
        fail=1
    fi
}

# --- S2: write-target-only check (read/write classifier) --------------------
# Classifies each path:/dest:/src: (and command:/shell: redirection) by its
# enclosing module. stat/slurp (and when:/assert: references, which are not
# module targets at all) are READ -- always allowed. file/copy/template/
# lineinfile/blockinfile path:/dest:, and command:/shell: redirections, are
# WRITE -- must be {{ spike_root }}-relative or one of the three enumerated
# external literals (the two plist paths, and the teardown receipt path).
s2_classify() {
    awk '
    function lws(s) { match(s, /^[ \t]*/); return RLENGTH }
    {
        line = $0
        n = lws(line)
        trimmed = line
        sub(/^[ \t]*-[ \t]*/, "", trimmed)
        sub(/^[ \t]*/, "", trimmed)
        if (trimmed ~ /^(ansible\.builtin\.)?(stat|slurp):/) { cur_module="READ"; cur_indent=n; next }
        if (trimmed ~ /^(ansible\.builtin\.)?(file|copy|template|lineinfile|blockinfile):/) { cur_module="WRITE"; cur_indent=n; next }
        if (trimmed ~ /^(ansible\.builtin\.)?(command|shell):/) {
            val = trimmed
            sub(/^(ansible\.builtin\.)?(command|shell):[ \t]*/, "", val)
            if (val ~ /(>>|>|\|[ \t]*tee)/) print NR "|CMD-WRITE|" val
            cur_module=""
            next
        }
        if (cur_module != "" && n <= cur_indent) cur_module=""
        if (trimmed ~ /^(path|dest|src):/) {
            val = trimmed
            sub(/^(path|dest|src):[ \t]*/, "", val)
            if (cur_module == "WRITE") print NR "|WRITE|" val
        }
    }
    ' "$1"
}

s2_target_allowed() {
    # $1 = cleaned target string
    case "$1" in
        '{{ spike_root }}'*) return 0 ;;
        '~/Library/LaunchAgents/dev.gleipnir.signer.spike.agent.plist') return 0 ;;
        '/Library/LaunchDaemons/dev.gleipnir.signer.spike.daemon.plist') return 0 ;;
        '/private/tmp/gleipnir-signer-spike.torndown') return 0 ;;
        # The two manifest-derived plist-path VARIABLES (corrected teardown:
        # a `~`-under-sudo literal resolves under ROOT's home, so the real
        # paths are parsed from created.env's PLIST_A_PATH=/PLIST_B_PATH=
        # instead). Allowed here as exact-string template tokens ONLY --
        # check_s2 additionally requires their provenance (a set_fact from
        # regex_search over the manifest) to be present in the SAME file
        # before this allowance is honoured, so the exact-token match here
        # is necessary but not sufficient (see the provenance gate below).
        '{{ plist_a_path }}') return 0 ;;
        '{{ plist_b_path }}') return 0 ;;
        *) return 1 ;;
    esac
}

# Bounds the S2 allowance for `{{ plist_a_path }}` / `{{ plist_b_path }}`
# (added above) to the ONE provenance that makes them safe: a `set_fact`
# whose value is a `regex_search(...)` over the recorded manifest key
# (PLIST_A_PATH=/PLIST_B_PATH=). Without this, allowing the bare variable
# NAME would let any assignment (e.g. from an unrelated/attacker-controlled
# source) inherit the enumerated-external exception. $1 = file, $2 = var
# name (plist_a_path/plist_b_path), $3 = manifest key (PLIST_A_PATH/
# PLIST_B_PATH). Two conditions, both required: (a) a line assigning the
# var whose value contains regex_search('<key>=...'), and (b) that line
# sits within a `set_fact:` module block (a `set_fact:`/
# `ansible.builtin.set_fact:` key line within a few lines above it) --
# a bare "var: regex_search(...)" under some OTHER module would not prove
# the value actually came from a fact assignment.
s2_plist_var_provenance_ok() {
    # NOTE: plain POSIX sh function -- no `local`, so these names are
    # global. Deliberately prefixed pv_* to avoid clobbering check_s2's
    # own loop variables (lineno/class/val/raw/target/f), which are still
    # live in the caller's scope across this call (check_s2 prints
    # "$lineno" in its FAIL message AFTER calling this function).
    pv_file=$1; pv_var=$2; pv_key=$3
    # Find the line that OPENS this var's assignment (`<var>:`). The value may
    # be inline OR a folded/block scalar continued on following lines, so the
    # regex_search('<key>=...') provenance token can sit on the var line OR a
    # few lines below it. Search a small forward window from the var line for
    # that token, and confirm the assignment sits within a set_fact: block
    # (a set_fact: key line in a small window ABOVE the var line).
    pv_match=$(grep -nE "^[[:space:]]*${pv_var}:" "$pv_file" | head -1 || true)
    [ -z "$pv_match" ] && return 1
    pv_lineno=${pv_match%%:*}
    pv_fwd_end=$((pv_lineno + 4))
    pv_fwd=$(sed -n "${pv_lineno},${pv_fwd_end}p" "$pv_file")
    # The value must be a regex_search over the RECORDED MANIFEST specifically
    # (manifest_raw.content), not any arbitrary source -- this is what bounds
    # the plist-path variable to a provably manifest-derived value.
    printf '%s' "$pv_fwd" | grep -qE "regex_search\('${pv_key}=" || return 1
    printf '%s' "$pv_fwd" | grep -q 'manifest_raw' || return 1
    pv_win_start=$((pv_lineno - 4))
    [ "$pv_win_start" -lt 1 ] && pv_win_start=1
    pv_block=$(sed -n "${pv_win_start},${pv_lineno}p" "$pv_file")
    printf '%s' "$pv_block" | grep -qE '^[[:space:]]*(ansible\.builtin\.)?set_fact:[[:space:]]*$'
}

check_s2() {
    label="S2"; token="repo-write"
    bad=0
    for f in "$signer_yml" "$teardown_yml"; do
        if [ ! -f "$f" ]; then
            echo "FAIL[$label/$token]: missing file $f" >&2
            bad=1
            continue
        fi
        candidates=$(s2_classify "$f")
        [ -z "$candidates" ] && continue
        while IFS='|' read -r lineno class val; do
            [ -z "$lineno" ] && continue
            if [ "$class" = "CMD-WRITE" ]; then
                case "$val" in
                    *'>>'*) raw=${val##*>>} ;;
                    *'>'*) raw=${val##*>} ;;
                    *'tee'*) raw=${val##*tee} ;;
                    *) raw=$val ;;
                esac
            else
                raw=$val
            fi
            target=$(clean_val "$raw")
            if ! s2_target_allowed "$target"; then
                echo "FAIL[$label/$token]: write target '$target' (line $lineno, $f) is not scratch-root-relative or an enumerated external path" >&2
                bad=1
            else
                case "$target" in
                    '{{ plist_a_path }}')
                        if ! s2_plist_var_provenance_ok "$f" plist_a_path PLIST_A_PATH; then
                            echo "FAIL[$label/$token]: write target '$target' (line $lineno, $f) is allowed only when plist_a_path's provenance is a set_fact assigning regex_search('PLIST_A_PATH=...') over the manifest -- no such assignment found in $f" >&2
                            bad=1
                        fi
                        ;;
                    '{{ plist_b_path }}')
                        if ! s2_plist_var_provenance_ok "$f" plist_b_path PLIST_B_PATH; then
                            echo "FAIL[$label/$token]: write target '$target' (line $lineno, $f) is allowed only when plist_b_path's provenance is a set_fact assigning regex_search('PLIST_B_PATH=...') over the manifest -- no such assignment found in $f" >&2
                            bad=1
                        fi
                        ;;
                esac
            fi
        done <<EOF
$candidates
EOF
    done
    if [ "$bad" -eq 0 ]; then
        echo "PASS: S2 write targets confined to scratch root / enumerated externals"
    else
        fail=1
    fi
}

# --- S3: scratch-root mkdir is exclusive (no -p, no creates:) ---------------
check_s3() {
    label="S3"; token="mkdir-p"
    bad=0
    if [ ! -f "$signer_yml" ]; then
        echo "FAIL[$label/$token]: missing file $signer_yml" >&2
        fail=1
        return
    fi
    mkdir_lines=$(grep -n 'mkdir' "$signer_yml" || true)
    if [ -z "$mkdir_lines" ]; then
        echo "FAIL[$label/$token]: no mkdir invocation found for the scratch root in $signer_yml" >&2
        fail=1
        return
    fi
    while IFS=: read -r lineno rest; do
        [ -z "$lineno" ] && continue
        if printf '%s' "$rest" | grep -qE -- '(^|[[:space:]])-p([[:space:]]|$)'; then
            echo "FAIL[$label/$token]: mkdir invoked with -p at line $lineno ($signer_yml)" >&2
            bad=1
        fi
        window_end=$((lineno + 8))
        window=$(sed -n "${lineno},${window_end}p" "$signer_yml")
        if printf '%s' "$window" | grep -qE '^[[:space:]]*creates:'; then
            echo "FAIL[$label/$token]: creates: key found near mkdir at line $lineno ($signer_yml)" >&2
            bad=1
        fi
    done <<EOF
$mkdir_lines
EOF
    if [ "$bad" -eq 0 ]; then
        echo "PASS: S3 mkdir is exclusive (no -p, no creates:)"
    else
        fail=1
    fi
}

# --- S4: control-flow check on tasks/create-service-account.yml -------------
# (i) a fail task exists on the mismatch branch; (ii)/(iii) every creation
# task's when: carries the absent-sentinel conjoined with a mismatch-free
# assertion; (iv) the fail is not swallowed (ignore_errors / failed_when:
# false / a swallowing rescue:); (v) the fail precedes every creation task.
check_s4() {
    label="S4"
    bad_bypass=0
    bad_swallow=0
    f="$task_file"
    if [ ! -f "$f" ]; then
        echo "FAIL[$label/mismatch-guard-bypassed]: missing file $f" >&2
        fail=1
        return
    fi

    # ALL fail: tasks must be checked for swallowing, not just the first --
    # the guard file legitimately has multiple fail: tasks (operational-error,
    # account-mismatch, group-mismatch), and a swallowed mismatch fail on ANY
    # of them defeats the guard. `head -1` would only inspect the earliest.
    fail_lines=$(grep -nE '^[[:space:]]*(ansible\.builtin\.)?fail:' "$f" | cut -d: -f1 || true)
    first_fail_line=$(printf '%s' "$fail_lines" | head -1)
    if [ -z "${first_fail_line:-}" ]; then
        echo "FAIL[$label/mismatch-guard-bypassed]: no fail task found in $f" >&2
        bad_bypass=1
    else
        for fl in $fail_lines; do
            # Scan the fail task's FULL OWN block -- from its OWN "- name:" line
            # (nearest at/above the fail: key) to the next "- name:" or EOF --
            # NOT from the fail: key forward. `ignore_errors`/`failed_when` are
            # valid ABOVE the fail: key within the same task (e.g. right after
            # the "- name:"), so a forward-only scan from fail: would miss them;
            # and a multi-line msg: folded scalar can push them past a fixed
            # window below. Scanning the whole task block catches both placements.
            fblock_start=$(awk -v fl="$fl" '
                /^[[:space:]]*-[[:space:]]*name:/ { if (NR <= fl) start = NR }
                END { print start + 0 }
            ' "$f")
            [ "$fblock_start" -eq 0 ] && fblock_start="$fl"
            fblock_end=$(awk -v fl="$fl" '
                NR > fl && /^[[:space:]]*-[[:space:]]*name:/ { print NR - 1; found=1; exit }
                END { if (!found) print NR }
            ' "$f")
            window=$(sed -n "${fblock_start},${fblock_end}p" "$f")
            if printf '%s' "$window" | grep -qE 'ignore_errors:[[:space:]]*(true|yes)'; then
                echo "FAIL[$label/ignore_errors]: fail task at line $fl guarded by ignore_errors ($f)" >&2
                bad_swallow=1
            fi
            if printf '%s' "$window" | grep -qE 'failed_when:[[:space:]]*(false|no)'; then
                echo "FAIL[$label/ignore_errors]: fail task at line $fl guarded by failed_when: false ($f)" >&2
                bad_swallow=1
            fi
        done
        preceding=$(sed -n "1,${first_fail_line}p" "$f")
        if printf '%s' "$preceding" | grep -qE '^[[:space:]]*rescue:[[:space:]]*$'; then
            block_ignore=$(printf '%s' "$preceding" | grep -cE '^[[:space:]]*ignore_errors:[[:space:]]*(true|yes)[[:space:]]*$' || true)
            if [ "${block_ignore:-0}" -gt 0 ]; then
                echo "FAIL[$label/ignore_errors]: fail task at line $first_fail_line sits inside a swallowing rescue: block ($f)" >&2
                bad_swallow=1
            fi
        fi
    fi
    # For the creation-precedes-fail ORDER check we need the MISMATCH fail
    # specifically -- NOT merely the first fail: (which may now be an
    # operational-error fail that legitimately precedes everything). Identify
    # the fail: task whose own block references attrs_mismatch; the mismatch
    # guard must sit before the creation tasks. Fall back to the first fail:
    # if none references attrs_mismatch (older single-fail shape).
    mismatch_fail_line=""
    for fl in $fail_lines; do
        fb_start=$(awk -v fl="$fl" '/^[[:space:]]*-[[:space:]]*name:/ { if (NR <= fl) s = NR } END { print s + 0 }' "$f")
        [ "$fb_start" -eq 0 ] && fb_start="$fl"
        fb_end=$(awk -v fl="$fl" 'NR > fl && /^[[:space:]]*-[[:space:]]*name:/ { print NR-1; found=1; exit } END { if (!found) print NR }' "$f")
        if sed -n "${fb_start},${fb_end}p" "$f" | grep -q 'attrs_mismatch'; then
            mismatch_fail_line="$fl"
            break
        fi
    done
    [ -z "$mismatch_fail_line" ] && mismatch_fail_line="$first_fail_line"
    fail_line="$mismatch_fail_line"

    creation_lines=$(grep -nE '(sysadminctl[[:space:]]+-addUser|dscl[[:space:]]+\.[[:space:]]+-create[[:space:]]+/(Users|Groups))' "$f" || true)
    if [ -z "$creation_lines" ]; then
        echo "FAIL[$label/mismatch-guard-bypassed]: no account/group creation commands found in $f" >&2
        bad_bypass=1
    else
        while IFS=: read -r cl rest; do
            [ -z "$cl" ] && continue
            if [ -n "${fail_line:-}" ] && [ "$cl" -le "$fail_line" ]; then
                echo "FAIL[$label/mismatch-guard-bypassed]: creation command at line $cl precedes the mismatch fail task (line $fail_line) in $f" >&2
                bad_bypass=1
            fi
            # Find this creation command's OWN task block -- from the
            # nearest "- name:" line at/above cl down to (but excluding)
            # the next "- name:" line after that (or EOF) -- and search
            # for when: WITHIN that block. A when: may sit either BEFORE
            # or AFTER the command key within the same task (both are
            # valid YAML); a fixed backward-only window can instead pick
            # up a PRECEDING task's when: (e.g. the mismatch fail task's)
            # when this task's own when: sits below its command key.
            block_start=$(awk -v cl="$cl" '
                /^[[:space:]]*-[[:space:]]*name:/ { if (NR <= cl) start = NR }
                END { print start + 0 }
            ' "$f")
            [ "$block_start" -eq 0 ] && block_start=1
            block_end=$(awk -v bs="$block_start" '
                NR > bs && /^[[:space:]]*-[[:space:]]*name:/ { print NR - 1; found=1; exit }
                END { if (!found) print NR }
            ' "$f")
            block=$(sed -n "${block_start},${block_end}p" "$f")
            when_line=$(printf '%s' "$block" | grep -E '^[[:space:]]*when:' | tail -1 || true)
            if [ -z "$when_line" ]; then
                echo "FAIL[$label/mismatch-guard-bypassed]: creation task near line $cl has no when: guard ($f)" >&2
                bad_bypass=1
                continue
            fi
            absent_ok=0
            printf '%s' "$when_line" | grep -qE '(is[[:space:]]+false|rc[[:space:]]*!=[[:space:]]*0|not[[:space:]]+[A-Za-z0-9_]*present[A-Za-z0-9_]*)' && absent_ok=1
            mismatch_ok=0
            printf '%s' "$when_line" | grep -qE '(not[[:space:]]+[A-Za-z0-9_]*mismatch[A-Za-z0-9_]*|[A-Za-z0-9_]*mismatch[A-Za-z0-9_]*[[:space:]]+is[[:space:]]+false)' && mismatch_ok=1
            if [ "$absent_ok" -eq 0 ] || [ "$mismatch_ok" -eq 0 ]; then
                echo "FAIL[$label/mismatch-guard-bypassed]: creation task near line $cl when: '$when_line' lacks the absent+mismatch-free conjunction ($f)" >&2
                bad_bypass=1
            fi
            # Genuine CONJUNCTION required, not merely both substrings
            # present independently: `rc != 0 or not attrs_mismatch` would
            # satisfy both greps above yet let a mismatch through (`or`
            # short-circuits true on the absent-sentinel alone). A bare
            # ` or ` anywhere in the when: line is treated as disjoining
            # the two clauses -- this check's job is to catch exactly the
            # bypass shape, not to parse full boolean precedence.
            if printf '%s' "$when_line" | grep -qE '[[:space:]]or[[:space:]]'; then
                echo "FAIL[$label/mismatch-guard-bypassed]: creation task near line $cl when: '$when_line' joins the absent-sentinel and mismatch-free clauses with 'or' instead of 'and' -- a mismatch could pass through ($f)" >&2
                bad_bypass=1
            fi
        done <<EOF
$creation_lines
EOF
    fi

    if [ "$bad_bypass" -eq 0 ] && [ "$bad_swallow" -eq 0 ]; then
        echo "PASS: S4 mismatch-guard control flow"
    else
        fail=1
    fi
}

# --- S5: site.yml adopts the shared task-file, no inline commands left ------
check_s5() {
    label="S5"; token="inline-commands-restored"
    bad=0
    reasons=""
    if [ ! -f "$site_yml" ]; then
        echo "FAIL[$label/$token]: missing file $site_yml" >&2
        fail=1
        return
    fi
    # Match EITHER include form, but require the include to actually TARGET
    # create-service-account.yml (not merely both tokens appearing anywhere
    # in the file -- two independent whole-file greps would let an
    # unrelated include_tasks: plus an unrelated comment mentioning the
    # filename pass):
    #   (i) the compact single-line form (fixtures):
    #       include_tasks: tasks/create-service-account.yml
    #   (ii) the map-style form required for apply:/tag-propagation
    #        (J24(b), real site.yml), where `include_tasks:` and the
    #        `file:`-referenced create-service-account.yml sit on
    #        DIFFERENT lines, the latter within a few lines AFTER:
    #          ansible.builtin.include_tasks:
    #            file: tasks/create-service-account.yml
    #            apply:
    #              tags: [...]
    # Every `include_tasks:` key line is a candidate; it corresponds iff
    # EITHER create-service-account.yml appears on that SAME line, OR a
    # `file:` line referencing it appears within the next 4 lines. Absence
    # of any corresponding include is a FAIL, same as before.
    include_target_ok=0
    include_lines=$(grep -nE '(ansible\.builtin\.)?include_tasks:' "$site_yml" || true)
    if [ -n "$include_lines" ]; then
        while IFS=: read -r inc_ln inc_rest; do
            [ -z "$inc_ln" ] && continue
            if printf '%s' "$inc_rest" | grep -q 'create-service-account\.yml'; then
                include_target_ok=1
                break
            fi
            inc_window_end=$((inc_ln + 4))
            inc_window=$(sed -n "$((inc_ln + 1)),${inc_window_end}p" "$site_yml")
            if printf '%s' "$inc_window" | grep -qE '^[[:space:]]*file:.*create-service-account\.yml'; then
                include_target_ok=1
                break
            fi
        done <<EOF
$include_lines
EOF
    fi
    if [ "$include_target_ok" -ne 1 ]; then
        bad=1
        reasons="${reasons}no include_tasks: targeting tasks/create-service-account.yml found in $site_yml (an include_tasks: key and/or the filename may be present, but none correspond); "
    fi
    if grep -qE 'sysadminctl[[:space:]]+-addUser' "$site_yml"; then
        bad=1
        reasons="${reasons}inline sysadminctl -addUser found in $site_yml; "
    fi
    if grep -qE 'dscl[[:space:]]+\.[[:space:]]+-create[[:space:]]+/Users' "$site_yml"; then
        bad=1
        reasons="${reasons}inline dscl . -create /Users found in $site_yml; "
    fi
    if [ "$bad" -eq 0 ]; then
        echo "PASS: S5 site.yml adopts the shared task-file, no inline commands remain"
    else
        echo "FAIL[$label/$token]: ${reasons%; }" >&2
        fail=1
    fi
}

# --- S6: teardown references + gating + receipt placement -------------------
check_s6() {
    label="S6"; token="ungated-removal"
    bad=0
    f="$teardown_yml"
    if [ ! -f "$f" ]; then
        echo "FAIL[$label/$token]: missing file $f" >&2
        fail=1
        return
    fi
    if ! grep -qi 'account' "$f"; then
        echo "FAIL[$label/$token]: no account reference found in $f" >&2
        bad=1
    fi
    if ! grep -qi 'group' "$f"; then
        echo "FAIL[$label/$token]: no group reference found in $f" >&2
        bad=1
    fi
    if ! grep -q 'spike_root' "$f"; then
        echo "FAIL[$label/$token]: no scratch-root (spike_root) reference found in $f" >&2
        bad=1
    fi

    removal_lines=$(grep -nE '(state:[[:space:]]*absent|launchctl[[:space:]]+bootout|sysadminctl[[:space:]]+-deleteUser|dscl[[:space:]]+\.[[:space:]]+-delete)' "$f" || true)
    if [ -z "$removal_lines" ]; then
        echo "FAIL[$label/$token]: no removal actions found in $f" >&2
        bad=1
    else
        while IFS=: read -r rl rest; do
            [ -z "$rl" ] && continue
            # Scope the when: search to the removal's OWN task block -- from the
            # nearest "- name:" at/above the removal line down to the removal
            # line -- NOT a fixed backward window. A fixed window + `tail -1`
            # can grab a PRECEDING task's when: (e.g. an adjacent bootout task's
            # LABEL_*_CREATED gate), masking an ungated removal whose own task
            # has no when: at all. Block-scoping makes each removal answer for
            # its OWN gate only.
            r_block_start=$(awk -v rl="$rl" '
                /^[[:space:]]*-[[:space:]]*name:/ { if (NR <= rl) start = NR }
                END { print start + 0 }
            ' "$f")
            [ "$r_block_start" -eq 0 ] && r_block_start=1
            block=$(sed -n "${r_block_start},${rl}p" "$f")
            when_line=$(printf '%s' "$block" | grep -E '^[[:space:]]*when:' | tail -1 || true)
            if [ -z "$when_line" ] || ! printf '%s' "$when_line" | grep -qE '(ACCOUNT_CREATED|GROUP_CREATED|ROOT_CREATED|PLIST_[A-Za-z0-9_]*_CREATED|LABEL_[A-Za-z0-9_]*_CREATED)'; then
                echo "FAIL[$label/$token]: removal task near line $rl in $f is not gated on a created.env *_CREATED flag" >&2
                bad=1
            fi
        done <<EOF
$removal_lines
EOF
    fi

    receipt_line=$(grep -nE 'gleipnir-signer-spike\.torndown' "$f" | tail -1 | cut -d: -f1 || true)
    if [ -z "${receipt_line:-}" ]; then
        echo "FAIL[$label/$token]: no completion receipt (gleipnir-signer-spike.torndown) write found in $f" >&2
        bad=1
    else
        after=$(sed -n "$((receipt_line + 1)),\$p" "$f")
        if printf '%s' "$after" | grep -qE '^[[:space:]]*-[[:space:]]*name:'; then
            echo "FAIL[$label/$token]: a task follows the completion-receipt write in $f -- receipt is not the final task" >&2
            bad=1
        fi
        win_start=$((receipt_line - 5))
        [ "$win_start" -lt 1 ] && win_start=1
        receipt_block=$(sed -n "${win_start},${receipt_line}p" "$f")
        if printf '%s' "$receipt_block" | grep -q 'spike_root'; then
            echo "FAIL[$label/$token]: completion receipt task references spike_root in $f -- receipt must be written outside the scratch root" >&2
            bad=1
        fi
    fi

    if [ "$bad" -eq 0 ]; then
        echo "PASS: S6 teardown references + gating + receipt placement"
    else
        fail=1
    fi
}

echo "-- S1: no hardcoded uid/gid"
check_s1
echo "-- S2: write targets confined to scratch root / enumerated externals"
check_s2
echo "-- S3: scratch-root mkdir is exclusive"
check_s3
echo "-- S4: mismatch-guard control flow"
check_s4
echo "-- S5: site.yml adopts the shared task-file"
check_s5
echo "-- S6: teardown references + gating + receipt placement"
check_s6

if [ "$fail" -eq 0 ]; then
    echo "== signer-static: ALL CHECKS PASSED =="
else
    echo "== signer-static: FAILURES ABOVE ==" >&2
fi
exit "$fail"
