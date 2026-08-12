# Decision: bin/* executable-bit durability + detection

**Status:** decided and applied (acute fix). Durable decision record (Tier-3,
operator-authored). Converged via the orchestrator-surfaced gate; brief:
`../plans/bin-executable-bit-fix-brainstorm.md`; plan:
`../plans/bin-executable-bit-fix.md`.

## Context

`bin/gleipnir-preflight` was found tracked as mode `100644` (non-executable).
The always-active `plugins/git-guard.ts` gate shells out to
`bin/gleipnir-preflight config-scan` before every broker git write; a
non-executable entrypoint makes `spawnSync` fail and the gate abort fail-closed,
blocking ALL broker commits/pushes with an error indistinguishable from a policy
rejection.

## Decisions

- **The durable fix is the committed index mode.** `chmod +x` on the working
  tree is not enough — the executable bit must be recorded in git's index/tree
  as `100755`. Set it with `git update-index --chmod=+x bin/<file>` (or
  `chmod +x` then `git add`), and verify with `git ls-files -s bin/` (the mode
  is the first field). Applied for `bin/gleipnir-preflight` in commit
  `9645974` (restored `100755`).
- **`.gitattributes` has NO portable executable-bit directive.** A common
  misconception is that a `.gitattributes` entry can force the +x bit
  cross-platform; there is no such attribute. The committed tree mode is the
  only portable carrier of the executable bit. Do not add or rely on a
  `.gitattributes` line for this.
- **Verify `core.fileMode` is not disabled.** With `git config core.fileMode
  false`, git ignores working-tree mode changes, which can hide a wrong
  committed mode from a working-tree `os.access(..., os.X_OK)` check. Detection
  must (and does — see below) assert the COMMITTED mode via `git ls-files -s`,
  not the working-tree bit. Operators should confirm `core.fileMode` is not
  set to false in their environment.

## Detection / diagnosability (implemented separately)

- `tests/test_bin_executable.py` (agent-built, normal pipeline) asserts the
  committed mode of every tracked `bin/*` is executable, failing loudly and
  early with the exact fix command. Skips cleanly where no usable git tooling is
  present (e.g. the `bin/gleipnir-sandbox` test run, whose base image likely has
  no `git` binary).
- `plugins/git-guard.ts` distinguishes a broken/missing preflight tool
  (`PreflightUnavailable`) from a genuine config-scan REFUSE, so a future
  occurrence is a one-line "chmod this" fix rather than a multi-step
  investigation. Fail-closed behaviour is unchanged.

## Honesty label

Cooperative-policy-until-S-2 for the Tier-3 pieces (plugin, this record). The
detection test is real today (no S-2 dependency). None of this loosens the
fail-closed gate; it only makes a self-inflicted broken prerequisite fast to
diagnose and less likely to recur silently.
