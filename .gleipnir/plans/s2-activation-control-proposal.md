# S-2 Activation — C2 Control Proposal (ready-to-apply artifact)

> **What this is.** This is the ready-to-apply control proposal drawn from the
> **approved** plan [`s2-activation.md`](./s2-activation.md) (its "C2 Control
> Proposal" section, source lines 293–445). It is reproduced here as a
> self-contained Tier-0 artifact so the operator has the apply-ready content in
> one file, source-linked back to the approving plan.
>
> **Status: draft only — nothing applied.** Per the approved plan's own
> instruction, *"`gleipnir-plan` drafts this proposal file and stops — does not
> implement"* (tier3-coach Anti-Pattern 3). None of the shell commands below
> have been executed. This is an **OS/host + Tier-3 POLICY** control; **no
> roster agent (including `gleipnir-plan`) can write or apply it** — the
> operator applies it by hand.

---

## Gap
The S-2/G-1 boundary is verified-but-dormant: on the single-uid host every
ENFORCEMENT_PATH is agent-writable in principle and the key agent-readable, so
enforcement is **cooperative policy**, not an OS wall. The missing controls (a
dedicated agent uid, OS-ro perms on the enforcement subtree, an unreadable key,
and an elevated launch that runs opencode as that uid) are **safety invariants**
that must be enforced somewhere — today nothing does. This is safety, not
preference.

## Correct layer
**OS / host layer** (uid creation, file perms, launch-as-uid) + **Tier-3 POLICY**
(the decision-record amendment). Per the tier3-coach layer map both are **No**
rows — no roster agent (including `gleipnir-plan`) can write them. Confirmed:
`gleipnir-code` denies `src/gleipnir/preflight/**` and `.gleipnir/**`; `bin/` is
operator territory; OS acts are outside every tier. → **proposal, not edit.**

## Proposed artifacts (ready-to-apply; adjust names/uids to the host)

Assume: operator = owner (`$(whoami)`); repo at `$REPO`; agent account name
`gleipniragent`. Pick a free uid/gid (e.g. `510`); verify free first with
`dscl . -list /Users UniqueID` and `dscl . -list /Groups PrimaryGroupID`.

**(1) Create the dedicated agent gid + uid (macOS `dscl`/`sysadminctl`):**
```sh
# Group first (so the user's PrimaryGroupID exists):
sudo dscl . -create /Groups/gleipniragent
sudo dscl . -create /Groups/gleipniragent PrimaryGroupID 510
sudo dscl . -create /Groups/gleipniragent RecordName gleipniragent

# User (non-login, no admin) — sysadminctl is the supported modern path:
sudo sysadminctl -addUser gleipniragent -UID 510 -GID 510 \
  -fullName "Gleipnir Agent" -home /var/empty -shell /usr/bin/false
# (Equivalent low-level dscl form if sysadminctl is unavailable:)
#   sudo dscl . -create /Users/gleipniragent
#   sudo dscl . -create /Users/gleipniragent UniqueID 510
#   sudo dscl . -create /Users/gleipniragent PrimaryGroupID 510
#   sudo dscl . -create /Users/gleipniragent UserShell /usr/bin/false
#   sudo dscl . -create /Users/gleipniragent NFSHomeDirectory /var/empty
# Verify:
dscl . -read /Users/gleipniragent UniqueID PrimaryGroupID
```

**(2) Single source of truth for the drop target (Pre-Mortem #3, D-F):**
```sh
# .gleipnir/agent-identity.env  — operator-owned, owner-writable only:
printf 'GLEIPNIR_AGENT_UID=510\nGLEIPNIR_AGENT_GID=510\n' \
  | sudo tee "$REPO/.gleipnir/agent-identity.env" >/dev/null
sudo chown "$(whoami)":staff "$REPO/.gleipnir/agent-identity.env"
sudo chmod 644 "$REPO/.gleipnir/agent-identity.env"   # readable, owner-write only
```

**(3) Ownership / group layout (Pre-Mortem #6):** operator owns all files; the
agent uid gets **group/other read of source**, and **write of Tier-0/1/2 only**
(`plans/`, `var/tmp/`, `logs/`, `memory/`, `lessons/`), while Tier-3 stays ro.
```sh
# Owner owns the whole repo:
sudo chown -R "$(whoami)":staff "$REPO"
# Source + config readable to all (agent needs to READ these):
sudo chmod -R a+rX "$REPO/src" "$REPO/.gleipnir"
# Tier-0/1/2 the agent may WRITE — grant the agent's group write there:
for d in .gleipnir/plans .gleipnir/var/tmp .gleipnir/logs .gleipnir/memory .gleipnir/lessons; do
  sudo chgrp -R gleipniragent "$REPO/$d" && sudo chmod -R g+w "$REPO/$d"
done
```

**(4) `chmod` the ENFORCEMENT_PATHS subtree OS-read-only to the agent uid**
(the LOCKED set — boundary.py:166-220; do not invent). Owner keeps write; group
+ other get **read + traverse only** (no write):
```sh
cd "$REPO/.gleipnir"
# File-level: agents/*.md, stage-role-map.md, AGENTS.md — owner rw, go read-only.
sudo chmod 644 agents/*.md stage-role-map.md AGENTS.md
# Directory-node hardening: explicitly go-w-strip (no new entries by group/other)
# and grant read+traverse (a+rX) to EVERY directory-type enforcement path — all
# 8 LOCKED ENFORCEMENT_PATHS treated explicitly, not by default-umask luck
# (review round R-1 added agents/ and keys/ to this line — previously only
# decisions/goals/sandbox/plugins were explicitly hardened here).
sudo chmod -R a+rX,go-w agents decisions goals keys sandbox plugins 2>/dev/null || true
# (plugins/ tolerates absence — the `|| true` covers an empty/absent dir.)
# NOTE: keys/ gets its dir-node hardened here (go-w, no group/other write of new
# entries); the KEY FILE ITSELF is then locked owner-only mode 600 in step (5)
# below — RO_AND_UNREADABLE requires the tighter file-level mode, which (5) sets
# AFTER this recursive dir pass so the 600 is not loosened by the a+rX above.
```

**(5) Place the G-3 key RO_AND_UNREADABLE — mode 600, owner-only (D3, PM #5):**
```sh
# The key lives under the ro boundary; only the OWNER (verifier) may read it.
sudo chown "$(whoami)":staff "$REPO/.gleipnir/keys/marker.key"
sudo chmod 600 "$REPO/.gleipnir/keys/marker.key"       # agent uid: no read, no write
export GLEIPNIR_MARKER_KEY_FILE="$REPO/.gleipnir/keys/marker.key"   # confirmed env var name
```
The verifier's `load_key` runs as owner (marker.py:86-106) → still readable to
it; the agent-uid read-probe reports read-denied → `keys/**` RO_AND_UNREADABLE
satisfied.

**(6) Launch-as-agent-uid wrapper (elevated; single-sourced uid/gid):**
```sh
# bin/gleipnir-launch  — operator-owned; run under sudo (root needed to setuid
# to another account on macOS). Sources the SAME agent-identity.env as the
# preflight (D-F) and asserts the exec'd account matches before launching.
#!/bin/sh
set -eu
here=$(cd "$(dirname "$0")" && pwd); repo=$(cd "$here/.." && pwd)
. "$repo/.gleipnir/agent-identity.env"          # GLEIPNIR_AGENT_UID / _GID (one source)

# 1. Fail-closed caged preflight AS OWNER (--mode caged, no override) — the
#    boundary must be CLOSED to proceed; caged mode refuses (exit 1) when not.
"$repo/bin/gleipnir-preflight" \
  --agent-uid "$GLEIPNIR_AGENT_UID" --agent-gid "$GLEIPNIR_AGENT_GID" --mode caged
# (exit 0 = CLOSED; the wrapper stops here on 1/2 because of `set -e`.)

# 2. Drop to the agent account and exec opencode. `sudo -u#uid` requires root;
#    the assert below guarantees the run uid == the preflight's drop target.
exec sudo -u "#${GLEIPNIR_AGENT_UID}" -g "#${GLEIPNIR_AGENT_GID}" \
  /bin/sh -c '
    if [ "$(id -u)" != "'"$GLEIPNIR_AGENT_UID"'" ]; then
      echo "gleipnir-launch: run uid $(id -u) != drop target '"$GLEIPNIR_AGENT_UID"'" >&2
      exit 1
    fi
    exec opencode
  '
```
Install: `sudo chown "$(whoami)":staff bin/gleipnir-launch && sudo chmod 755
bin/gleipnir-launch`, then launch sessions with `sudo bin/gleipnir-launch`.
**bin/ is Tier-3/operator territory — the operator creates this file, not an
agent (D-C, D-D).**

## Enforces / bypass semantics
Enforces real OS denial of writes to the enforcement subtree and reads of the
key **by the agent uid**. The operator (owner) can still edit Tier-3 normally —
that is the intended, structurally-clean escape hatch (owner ≠ agent-uid;
Second-Order insight), **not** a bypass of the agent cage. The agent cannot
`chmod` back (it does not own the files) and cannot `setuid` to the owner
(needs root). The elevated launch requires root once, by the operator.

## Honesty label
**Cooperative-policy-until-applied → hard OS boundary once AC-4 passes.** Until
the operator performs these acts and the no-override preflight reports CLOSED
with an empty reasons list, the boundary is dev-mode (C1) — honestly labelled
`G-1 NOT closed (dev-mode)` every session.

## Handoff
This is an **OS/host + Tier-3** control; no roster agent can write it. To apply:
the operator runs steps (1)-(6) above, then the AC-4 acceptance test, then flips
per D-G/step 6. `gleipnir-plan` drafts this proposal file and stops (does not
implement — tier3-coach Anti-Pattern 3).
