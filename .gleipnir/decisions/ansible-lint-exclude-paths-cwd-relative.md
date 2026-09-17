# Decision: `ansible-lint`'s `exclude_paths` resolves relative to the invocation cwd, not the config file's directory

**Status:** decided (this session). Durable decision record. Resolves a
plan-vs-tool-behaviour conflict found during **Plan A** (signer-uid-separation,
`.gleipnir/plans/signer-uid-separation-plan-a-launchd-spike.md`) Assemble
**step 4** (operator-run empirical verification of the test-stage arbiter).
Authored by the operator via the escape hatch (Tier-3, build mode), per the
`pi-replatform-open-q1.md` precedent (no roster subagent writes `decisions/`).

## The problem (verbatim empirical finding)

Plan A's **J26** decision (and its dependent acceptance criterion **SC-22**)
required a new `exclude_paths:` key in `ansible/.ansible-lint`, scoped to
**exactly** the one deliberately-broken fixture subtree, so that
`ansible/tests/layer1-static.sh`'s existing production `ansible-lint` pass
(which lints the whole `ansible/` tree) would not go red because of Plan A's
seven intentionally-defective fixture trees (`ansible/tests/fixtures/broken/F1..F7/`).

The plan, as originally authored, mandated the value `tests/fixtures/broken/`
(relative to `ansible/`, i.e. the config file's own directory — the natural
reading, and the convention most path-scoped tool configs use).

**Verified false at step 4, by actually running the tool on this host:**
`ansible-lint` resolves every `exclude_paths` entry against the **invocation
current working directory**, not the directory containing the config file
passed via `--config-file`. `layer1-static.sh` invokes:

```sh
ansible-lint --config-file "$root/.ansible-lint" "$root"
```

from the **repo root** (the orchestrator/operator's shell cwd), with
`$root` = the absolute path to `ansible/`. Because the exclusion match happens
against paths as seen from that cwd (repo root), the config-relative value
`tests/fixtures/broken/` matches **nothing on disk** — the deliberately-broken
fixture trees remained in the lint pass, producing 58 rule violations
(`no-changed-when`, `risky-file-permissions`, `ignore-errors`) and a **RED**
`ansible-lint` result, exactly the regression SC-22 exists to prevent.

Only the repo-root-relative value `ansible/tests/fixtures/broken/` actually
excludes the subtree. Verified both directions with a genuine positive control
(same invocation, only the config differing):

| Config state | Exit | Violations | F6's `ignore_errors: true` flagged? |
|---|---|---|---|
| `exclude_paths: [tests/fixtures/broken/]` (config-relative, the ORIGINAL plan value) | non-zero | 58 | yes |
| `exclude_paths: [ansible/tests/fixtures/broken/]` (repo-root-relative, the CORRECTED value) | 0 | 0 | no |
| `exclude_paths` key removed entirely | non-zero | 58 | yes |

## Decision

**`ansible/.ansible-lint`'s `exclude_paths` value is `ansible/tests/fixtures/broken/`
(repo-root-relative), not `tests/fixtures/broken/`.** This is the corrected,
empirically-verified value now applied to the file on disk and reflected in the
amended plan (J26, §2 Trace, SC-22(ii), Assemble steps 3/4 — all corrected by
`gleipnir-plan` this session; two cosmetic expected-output path descriptions in
step 4(iii) and SC-22(iv-a) also tightened to match).

**The scope intent is unchanged and preserved**: the value still names **exactly**
the one deliberately-broken fixture subtree and nothing broader — `tests/`,
`fixtures/`, `.`, or `**` remain explicit FAILs of SC-22(ii). Only the *anchor*
of the relative path changed (repo root instead of the config file's own
directory), not the *breadth* of what is excluded.

## Why this matters beyond this one file

This is a genuine, non-obvious tool-behaviour gotcha, not a one-off typo:

- **The natural assumption is wrong.** Most path-scoped config keys (e.g.
  `.gitignore`, many linters' `ignore`/`exclude` keys) resolve relative to the
  file that declares them, or to a detected project root. `ansible-lint`
  resolves `exclude_paths` relative to the **process's cwd at invocation time**,
  which is a caller-dependent, not config-dependent, anchor.
- **A wrong-but-plausible value fails silently, not loudly.** There is no
  warning or error when an `exclude_paths` entry matches nothing — the lint
  simply proceeds to scan the "excluded" content as if the key were absent.
  This is exactly the class of vacuous-guard failure SC-22(iv)'s positive
  control (run once WITH, once WITHOUT the exclusion, diff the two outcomes)
  exists to catch, and exactly why the plan's own text warns "the green pass
  alone does not discharge SC-22."
- **Anyone invoking `ansible-lint --config-file <path> <target>` from a
  DIFFERENT cwd than `layer1-static.sh` uses (repo root) would need a
  DIFFERENT relative value** for the same logical exclusion. Any future
  Ansible test harness, CI job, or manual invocation in this repo that adds or
  changes an `exclude_paths` entry must anchor it against **the cwd the
  invocation actually runs from**, not against `ansible/.ansible-lint`'s own
  location — and should re-run the same with/without positive control this
  session used, not just observe a green pass.

## Linkage

- **Derived from:** `../plans/signer-uid-separation-plan-a-launchd-spike.md`
  (Plan A), Decision row **J26**, acceptance criterion **SC-22**, and the
  Assemble **step 4** empirical verification run this session. The plan itself
  carries a "Step-4 amendment" note at J26 recording the same finding inline
  (Tier-0, disposable); this record is the durable Tier-3 home for it, per the
  memory-model rule that Tier-0 plan narrative does not outlive the plan.
- **Applies to:** `ansible/.ansible-lint`'s `exclude_paths` key (current value:
  `ansible/tests/fixtures/broken/`, repo-root-relative) and
  `ansible/tests/layer1-static.sh`'s `ansible-lint --config-file "$root/.ansible-lint" "$root"`
  invocation (cwd = repo root at the time this was verified).
- **Consulted by:** any future change to `ansible/.ansible-lint`'s
  `exclude_paths`, any new Ansible test-harness invocation added under
  `ansible/tests/**`, and any reviewer auditing an `exclude_paths` diff under
  the hardened-path negative-check attestation (`stage-role-map.md`'s
  substance/correspondence/post-change-state rules) — the correspondence rule
  requires evidence be captured against the **actual invocation**, and this
  record is why that matters here specifically.

## Provenance

Found via direct operator execution of Plan A's Assemble step 4 (build mode,
this session): running `sh ansible/tests/signer-static.sh` against the real
tree/fixtures, then `ansible-lint --config-file ... ` directly with the
config's `exclude_paths` present, absent, and value-varied, to isolate the
resolution-anchor behaviour. The plan amendment (J26/SC-22/§2 Trace/Assemble
steps 3-4, plus the two cosmetic path-string tightenings) was delegated to and
applied by `gleipnir-plan`; the `.ansible-lint` value change itself was applied
in build mode (the file is enforcement-path/hardened territory per
`stage-role-map.md` Axis 2(a), so it is operator/build-mode-only to touch,
mirroring J13's `.gitignore` precedent in the same plan).
