# Plan: Prose/Config-Only Pipeline Track — `stage-role-map.md` amendment (Tier-3)

> **Kind:** ATLAS brief for a **Tier-3, operator-applied** amendment to
> `.gleipnir/stage-role-map.md`. Planned FROM the converged brief
> `.gleipnir/plans/prose-config-only-track-brainstorm.md` (Approach B, operator-
> converged at the precept-10 gate). `gleipnir-plan` does **not** re-decide the
> material tradeoff; it produces the concrete mechanics the brief deferred, and
> escalates only if Open Question #3 (determinism) proves unresolvable.
>
> **Result of the determinism check (Open Question #3): ENCODABLE.** The low/high
> blast-radius split can be made mechanical via a two-axis path + content-pattern
> classifier (see Decision D3 and Trace §T3). The plan therefore **proceeds on
> Approach B** and is **not** flagging the fallback-to-C escalation. The proposed
> rule is shown in full below (Trace §T3, Assemble step 2).
>
> **Capability note:** `stage-role-map.md` is Tier-3/operator-authored (G-1);
> no roster agent — including `gleipnir-plan` — may write it. This plan is the
> ready-to-apply text for `spec-review` (quality-reviewer, read-only) then
> **operator application**. `gleipnir-plan` wrote only this Tier-0 plan file.

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D0 | Which approach to plan | **Approach B** — track split by blast radius | A (ratify as-is), C (full 8, N/A stages), D (ad hoc) | Operator-converged at the precept-10 gate (brief §Selected Approach, lines 292–316). Not re-decided here. |
| D1 | Where the track block sits in `stage-role-map.md` | New `## Prose/config-only track` section **after** *Binding rules*, as a specialisation of the map | Rewriting `## The map` inline; a separate file | Additive; keeps the 8-stage pipeline as the default and the track as a scoped exception the engine reads after the base binding. Lowest amendment blast radius. |
| D2 | Mechanical trigger / track-eligibility (the disqualifier) | **Axis 1 (gate):** eligibility = the touched-path set is confined to prose+declarative-config globs AND contains **zero** paths under the executable/interpreted set (`src/**`, `tests/**`, `hooks/**`, `bin/**`, and named executable artifacts). Any one disqualifying byte → full 8-stage pipeline. | Judgment call on "is this basically config"; a size/line-count heuristic | Brief's mechanical trigger (lines 251–260, 311–316). Grep-able on the plan's declared touched-file set; kills Pre-Mortem risk #2 ("mostly config but one hook"). |
| D3 | **CRITICAL — is the low/high split mechanical? (Open Q#3)** | **YES — encodable.** **Axis 2 (route within eligible):** enforcement-bearing = touches any path in the enforcement-path set **OR** the diff adds/edits permission/grant-bearing content by pattern (frontmatter `permission:`/`tools:` keys; digests under `keys/**`; the map's own binding rows). Else low-consequence prose → light path. | Escalate to operator for fallback-to-C (the flagged alternative if NON-mechanical) | The split maps onto G-6's already-ratified principle: *"trust tier is a property of the path, encoded in code"* (`decisions/gleipnir-layout-and-memory-model.md` L115). The one wrinkle (Tier-3 files that are *prose*, e.g. `decisions/*.md`, the map's own narrative) is resolved deterministically by Axis 2's content-pattern sub-rule, NOT per-plan judgment. See Trace §T3 for the exact rule + edge-case table. Because it is mechanical, **no escalation**. |
| D4 | What "separate adversarial review pass + explicit negative-check attestation" means, checkably | Hardened path = **two rubrically-distinct passes** (spec-conformance, then blast-radius/false-success) that must **not** be fused, each emitting a verdict; plus a structured **negative-check attestation** listing each grant with its intended scope, the over-broad form that was checked-for-and-ruled-out, and the concrete evidence — signed by `quality-reviewer` (never self-attested by the author, L-C8). | "Fixtures ran once"; a single fused pass; free-prose "looks fine" | Brief lines 71–76, 210–217, 355–357; L-C7 (false-success needs adversarial second rubric). Makes the requirement a checkable Stress-test artifact, not aspirational prose. See Trace §T4. |
| D5 | Digest / committed-artifact edge case | A **committed digest under `keys/**` = enforcement-bearing** (hardened path); a generated non-authority artifact committed elsewhere (e.g. a doc build) is **not**, but if it lives under an executable/interpreted glob it disqualifies from the track entirely (Axis 1). | Treating all generated files as code; treating digests as inert data | Digests ARE enforcement evidence (G-3.1); a wrong digest is a false-success surface. Resolves Open Q#2's digest edge case. |
| D6 | Makefile/CI/Containerfile edge case | **Executable/interpreted → disqualifies (Axis 1).** `Makefile`, `Containerfile*`, CI YAML, shell/`bin/**`, `hooks/**` are build/enforcement machinery → full pipeline. | Treating YAML uniformly as "config" | A Makefile/CI file *runs*; it is not declarative prose-config. Resolves Open Q#2's Makefile/CI edge case. |
| D7 | Scope of this amendment beyond the map | **Map only.** Optional operator-authored pointer in `AGENTS.md` noted as follow-up, not required for the rule to stand. | Editing `quality-reviewer.md` frontmatter (no permission change needed — it is already bound to both stages) | quality-reviewer.md L35–38 already binds both rubrics; the hardened path re-uses existing bindings, so no Tier-3 agent-file edit is required. Keeps blast radius minimal. |
| D8 | **[spec-review round 2] Coverage gap: `opencode.jsonc` mis-routed light** | Add `opencode.jsonc` / `**/opencode.json` to the enforcement-path set `E` (Axis 2(a)); add a **JSON-syntax variant** of the Axis 2(b) G-patterns catching JSON-quoted enforcement keys (`"permission"`, `"tools"`, `"enabled"`, `"instructions"`, `"default_agent"`, `"subagent_depth"`, `"mcp"`). | Leaving `opencode.jsonc` unclassified (light path); adding a `.jsonc`→`X` disqualifier (wrong — it is declarative config, not executable) | Reviewer read live `opencode.jsonc` (verified this session): it lists `.gleipnir/stage-role-map.md` in `instructions` (L94–97) and gates the MCP brokers via `"enabled"` (L79/L89). Removing the map from `instructions` — the single most enforcement-relevant edit — routed **light** under the round-1 rules. Now hardened. `.envrc`/`pyproject.toml` noted as lower-confidence secondary instances; `opencode.jsonc` is the disk-verified gap closed here. Enumeration tightening, within mandate — no convergence return. |
| D9 | **[spec-review round 2] D4 was a presence check, not a substance check** | Add an explicit **substance rule**: the attestation `evidence` field must cite a **concrete, reproducible artifact** (literal grep/diff output, digest comparison, verbatim quoted line), not a narrative; spec-review MUST reject schema-complete-but-vague attestations. | Accepting any non-empty `evidence` string (allows "reviewed it, looks correct" to pass — the exact L-C7 false-success) | An author could satisfy all six fields with unfalsifiable prose and pass the mechanical gate with zero real assurance. The substance gate (Trace §T4 (iii)) makes the attestation falsifiable and re-runnable. Within mandate. |
| D10 | **[spec-review round 2] Digest bullet was descriptive, not grep-able** | Give the `keys/**` digest pattern a **concrete regex** `^[0-9a-f]{64}\b` (hex SHA-256/HMAC) and note it is **redundant** with Axis 2(a) (`keys/**` already in `E`), retained only as self-describing documentation. | Deleting it silently; leaving the non-regex descriptive phrasing | Reviewer found the prose "a keyed digest/HMAC line" was pattern-recognition, not a grep rule, and redundant. Made grep-able; redundancy stated explicitly so a reader/engine treats 2(a) as operative. Within mandate. |
| D11 | **[spec-review round 2 — BLOCKING] Substance rule (D9) lacked a correspondence check** | Add an explicit **correspondence gate (iv)** to §T4 checkability, the Assemble hardened-path text, and Stress-test item 8: spec-review MUST verify the `evidence` command/pattern/quoted-line tests the SAME over-broad form named in that row's `over_broad_form_checked` (same pattern, same target file) — not merely that *some* reproducible artifact was cited. **Also (non-blocking accuracy):** correct the §T3 `instructions`-removal row + belt-and-suspenders framing — for that diff, Axis 2(a) is the *sole* operative rule (path ∈ `E`); Axis 2(b) does NOT independently fire because the removed line is the array ELEMENT string, not the `"instructions":` KEY line the `^\s*"(...)"\s*:` regex matches. | Leaving (iii) as the only substance gate (allows a reproducible-but-wrong-pattern grep to pass — reviewer's `foo_unrelated_pattern` case); leaving the row's inaccurate "2(b) yes" claim | (iv) closes a real false-success: a `lessons/**`-absent claim "proven" by grepping an unrelated string is reproducible and non-narrative yet worthless. Correspondence makes the attestation actually test its own claim. The §T3 accuracy fix aligns the row with D10's honest "2(a) operative, 2(b) documentary" framing. Routing conclusion (HARDENED) unchanged — 2(a) alone is unconditional and sufficient. Within mandate — no convergence return. |

---

## Architect

**Problem (one sentence).** Ratify in `stage-role-map.md` a *deterministically
routable* "prose/config-only track" that collapses pipeline stages for genuinely
low-blast prose while forcing a hardened, adversarial, negative-check-attested
review pass for enforcement-bearing config — so the improvised precedent from
`lesson-escalation-process.md` stops hardening ad hoc and the highest-consequence
change class is never under-reviewed (L-C7).

**User.** Primary: the future **G-5 deterministic engine** (must route on the
rule with no per-plan LLM judgment). Pre-engine: the **orchestrator** (applies
the rule as prompt-level guidance) and **quality-reviewer** (executes the
hardened path). Ultimate: the **operator**, who applies the Tier-3 text.

**Measurable success criteria.**
1. Given any plan's declared touched-path set, the track decision
   (full-pipeline vs light vs hardened) is computable by a **grep/glob + pattern
   match**, yielding the same answer regardless of which model runs it — verified
   against the edge-case table (Trace §T3) with no "it depends" cell.
2. The amendment text is additive: the existing 8-stage pipeline and all four
   Binding rules remain intact and correct after the edit (diff in Assemble
   step 2 touches no existing line's meaning).
3. The hardened path's "separate adversarial pass + negative-check attestation"
   is expressed as a **checkable artifact** a reviewer must emit (Trace §T4),
   not as aspirational prose — a spec-reviewer can confirm its presence/absence
   mechanically.
4. Every path/artifact cited exists on disk (verified this session) or is marked
   to-be-created.

**Constraints (inherited from brief + framework).**
- **C-Tier3:** operator-applied only; agent-unwritable (G-1). This plan produces
  text, not an applied edit.
- **C-Integrity:** enforcement-integrity > efficiency; a false SUCCESS on a
  permission grant is the worst failure mode (L-C7, brief lines 39–48).
- **C-Determinism:** the rule must be mechanically routable; per-plan judgment is
  deferred ad-hoc-ery, not a rule (brief lines 49–52).
- **C-NoOverfit:** Tier-3 edits are rare; the rule must not be over-fitted to the
  one plan that raised it (brief lines 35–38).
- **C-NoSelfAttest:** the negative-check attestation must respect L-C8 (author
  cannot attest their own enforcement change; `quality-reviewer` attests).

---

## Trace

Artifacts, where they live (source of truth), integrations, and edge cases.

### §T1 — Artifacts and source of truth

| Artifact | Path (verified this session) | Tier | Role in this plan |
|---|---|---|---|
| The rule being amended | `.gleipnir/stage-role-map.md` (61 lines, read in full) | Tier 3 | **Target of the amendment.** Source of truth for the pipeline + binding rules. |
| Converged brief | `.gleipnir/plans/prose-config-only-track-brainstorm.md` (383 lines) | Tier 0 | Input; records Approach B + the fallback-to-C caveat + Open Questions. |
| Plan format | `.gleipnir/goals/plan-format.md` | Tier 3 | Governing structure for this file. |
| Trust-tier definition | `.gleipnir/decisions/gleipnir-layout-and-memory-model.md` (L57–62, L115) | Tier 3 | **Load-bearing:** "trust tier is a property of the path, encoded in code" — the principle that makes Axis 2 mechanical. |
| Reviewer bindings | `.gleipnir/agents/quality-reviewer.md` (L32–38) | Tier 3 | Confirms quality-reviewer already serves BOTH spec-review and quality; hardened path re-uses this — no agent-file edit needed (D7). |

### §T2 — Repository layout the trigger greps against (verified this session)

Confirmed on disk so the mechanical globs are grounded, not assumed (L-C15):

- **Repo root** (`/Users/jasonh/git/gleipnir/`): `src/`, `tests/`, `hooks/`,
  `bin/`, `Makefile`, `Containerfile`, `Containerfile.broker`,
  `Containerfile.node`, `opencode.jsonc`, `pyproject.toml`, plus `*.md` specs.
- **`.gleipnir/`**: `agents/`, `plugins/`, `sandbox/` (`profiles.toml`),
  `policy/` (`context-cap.jsonc`), `keys/`, `skills/`, `goals/`, `decisions/`,
  `memory/`, `lessons/`, `logs/`, `plans/`, `var/`, `stage-role-map.md`,
  `AGENTS.md`.

Key fact: **there is no `src/` or `tests/` under `.gleipnir/`** — those are
repo-root. The disqualifier globs must be repo-root-relative, not
`.gleipnir/`-relative.

### §T3 — THE MECHANICAL CLASSIFIER (Open Question #3 resolution)

The classifier operates on a plan's **declared touched-path set** `P` (the set
of repo-relative paths the plan will write). It is two axes, evaluated in order.

**Axis 1 — Gate (track-eligibility). Disqualify if ANY path in `P` matches the
executable/interpreted set `X`:**

```
X (disqualifiers — repo-root-relative globs):
  src/**            tests/**            hooks/**            bin/**
  **/Makefile       **/Containerfile*   **/*.mk
  **/*.sh  **/*.bash  **/*.py  **/*.js  **/*.ts  **/*.rs  **/*.go
  .github/**  **/*.yml  **/*.yaml   (CI/workflow + any build-executed YAML)
  any path with a file mode +x, or any interpreter shebang in added content
```

Note: opencode config files (`opencode.jsonc`, `**/opencode.json`) are **not**
in `X` — they are declarative config, not executable — but they carry framework
enforcement wiring, so they are routed to the **hardened** path via Axis 2(a)
below, not disqualified. (This closes the spec-review round-2 gap D8.)

If `P ∩ X ≠ ∅` → **NOT track-eligible → full 8-stage pipeline.** No exceptions,
regardless of how small the code portion is (brief lines 311–316; Pre-Mortem
risk #2). *Rationale for the YAML sweep:* declarative YAML that is **not**
build-executed (e.g. a `.gleipnir/agents/*.md` frontmatter block, which is
Markdown-embedded, not a standalone `.yml`) is handled by Axis 2; standalone
`.yml`/`.yaml` files are treated as potentially build-executed and disqualify,
because distinguishing "inert data YAML" from "CI YAML" is not reliably
grep-able — the safe-side default is full pipeline (integrity > efficiency).

**Axis 2 — Route (within eligible set). Enforcement-bearing if EITHER
sub-condition holds; else low-consequence prose:**

```
ENFORCEMENT-BEARING (→ hardened path) if:
  (a) PATH rule:  any path in P is under the enforcement-path set E:
        .gleipnir/agents/**          (permission maps)
        .gleipnir/plugins/**         (guard/enforcement wiring)
        .gleipnir/sandbox/**         (sandbox profiles)
        .gleipnir/policy/**          (policy config e.g. context-cap)
        .gleipnir/keys/**            (G-3 digests)
        .gleipnir/stage-role-map.md  (this file — the binding itself)
        opencode.jsonc               (root opencode config — loads the map,
        **/opencode.json              gates the MCP brokers, sets default_agent)
  OR
  (b) CONTENT rule: the added/changed lines in ANY touched file match a
      grant/enforcement pattern G, in EITHER its YAML/frontmatter form OR its
      JSON(C) form:
        YAML : ^\s*permission:            (opencode permission block)
        YAML : ^\s*tools:                 (tool allow/deny map)
        YAML : ^\s*(edit|write|task|bash|webfetch)\s*:   (capability lines)
        YAML : allow | deny               on a capability line
        JSON : ^\s*"(permission|tools|enabled|instructions|default_agent
                     |subagent_depth|mcp)"\s*:   (JSON-quoted enforcement keys)
        a new/edited row in stage-role-map.md's binding tables
        a keyed digest line under keys/** matching  ^[0-9a-f]{64}\b
                                    (hex SHA-256/HMAC digest; see note below)

LOW-CONSEQUENCE PROSE (→ light single-pass) otherwise:
  paths confined to  .gleipnir/goals/**  .gleipnir/decisions/**(prose sections)
  .gleipnir/plans/**  .gleipnir/logs/**  **/*.md docs  READMEs  comments
  AND no G-pattern content match.
```

**Why this is mechanical, not judgment.** Axis 1 is pure glob set-membership.
Axis 2(a) is pure glob set-membership. Axis 2(b) is a fixed regex set over the
diff, in **two syntactic dialects** — a YAML/frontmatter form (for
`.gleipnir/agents/**` grants) and a JSON(C) form (for `opencode.jsonc`'s
JSON-quoted enforcement keys). None require the router to *understand* the
change — only to match paths and line patterns. This is the same construction G-6 already ratified: *"Trust
tier is a property of the path, encoded in code (an ordered enum), not inferred
from content"* (`decisions/gleipnir-layout-and-memory-model.md` L115). Axis 2(b)
extends it with a **content tripwire** (consistent with that record's
suspicious-influence tripwire model, L119–121): a G-pattern match forces the
hardened path; **absence of a match is not a completeness claim** — it only
means Axis 2(a) governs. Because 2(a) already routes every enforcement *path* to
the hardened side, 2(b) is a belt-and-suspenders catch for grant content that
lands in an otherwise-prose file, not the sole line of defense. **Note (D11):**
for a path wholesale in `E` — notably `opencode.jsonc` — 2(a) is the sole
operative rule and 2(b) is not required to fire at all. In particular, the
`instructions`-array-element removal case matches 2(a) (path ∈ `E`) but NOT 2(b)
(the removed line is an array element string, not a `"instructions":` key
declaration, so the `^\s*"(...)"\s*:` key-regex does not match). This is the same
honest framing as the D10 digest case: 2(a) operative, 2(b) documentary. 2(b)'s
value is catching grant content in files *not* in `E`; where the path is already
in `E`, 2(b) firing is a bonus, not a requirement.

**On the digest regex (D10).** The `keys/**` digest line
(`^[0-9a-f]{64}\b`, hex SHA-256/HMAC) is included as a **concrete regex** rather
than the earlier descriptive phrasing. It is strictly redundant with Axis 2(a)
(every `keys/**` path is already in `E` → hardened), and is retained only so the
G-pattern set is self-describing if a digest ever appears **outside** `keys/**`
(a scenario that should not occur, but the regex costs nothing and is now
grep-able rather than a judgment cue). A reviewer/engine may treat 2(a) as the
operative rule for digests and this pattern as documentation.

**The wrinkle this resolves (why a naive "Tier-3 = hardened" rule fails).**
Tier-3 contains prose files (`decisions/*.md` narrative, the map's own
explanatory text, `goals/*.md`). A pure tier→hardened rule would over-route
every doc fix to the expensive path (collapsing toward Option C and defeating
B's efficiency win). The two-axis rule instead routes on **enforcement-path
membership + grant-content pattern**, so editing the *prose* of a decision
record is light, while editing a *permission map* or adding a *binding row* is
hardened — a clean mechanical line, not a per-plan call.

**Edge-case resolution table (no "it depends" cell permitted):**

| Case | `P` example | Axis 1? | Axis 2? | Route |
|---|---|---|---|---|
| One-line typo fix in a goal doc | `.gleipnir/goals/methodology.md` | pass | 2(a) no, 2(b) no | **Light** |
| Prose edit to a decision record | `.gleipnir/decisions/runtime-and-deps.md` | pass | no | **Light** |
| New agent permission grant | `.gleipnir/agents/notify.md` (frontmatter) | pass | 2(a) yes | **Hardened** |
| Widen a `bash` allowlist | `.gleipnir/agents/gleipnir-code.md` | pass | 2(a)+2(b) yes | **Hardened** |
| Add a binding row to the map | `.gleipnir/stage-role-map.md` | pass | 2(a) yes | **Hardened** |
| Edit ONLY the map's prose (e.g. this section's wording) | `.gleipnir/stage-role-map.md` | pass | 2(a) yes (path is E) | **Hardened** — the map is enforcement config; its prose is load-bearing routing text. Conservative-safe. |
| Commit a new keyed digest | `.gleipnir/keys/<x>.digest` | pass | 2(a) yes | **Hardened** (D5) |
| Sandbox profile change | `.gleipnir/sandbox/profiles.toml` | pass | 2(a) yes | **Hardened** |
| **Remove `stage-role-map.md` from `opencode.jsonc` `instructions`** | `opencode.jsonc` | pass (not in `X`) | **2(a) yes** (`opencode.jsonc ∈ E`) — **sole operative rule**. 2(b) does NOT independently fire: the removed line is the array ELEMENT `".gleipnir/stage-role-map.md"`, not the `"instructions":` KEY line, so the `^\s*"(...)"\s*:` key-regex does not match it. 2(a) alone is unconditional and sufficient. | **Hardened** (D8/D11 — the reviewer's concrete gap; the single most enforcement-relevant edit, caught by 2(a) path membership) |
| Toggle an MCP broker `"enabled"` in opencode config | `opencode.jsonc` | pass | 2(a)+2(b) yes (`"enabled"`) | **Hardened** (D8) |
| Change `"default_agent"`/`"subagent_depth"` | `opencode.jsonc` | pass | 2(a)+2(b) yes | **Hardened** (D8) |
| "Mostly config" + one bash hook | `.gleipnir/agents/x.md` + `hooks/pre.sh` | **fail** (`hooks/**`) | — | **Full pipeline** (D2, kills risk #2) |
| Makefile / CI YAML edit | `Makefile` or `.github/ci.yml` | **fail** | — | **Full pipeline** (D6) |
| README/doc-only PR | `README.md`, `docs/*.md` | pass | no | **Light** |
| A `.py` helper "that's basically config" | `src/gleipnir/x.py` | **fail** (`src/**`) | — | **Full pipeline** |

Every row is decided by set-membership + regex — **no case requires semantic
judgment.** This is the evidence the split is encodable; therefore the plan
proceeds on B and does **not** trigger the Open-Q#3 escalation.

### §T4 — Hardened path: what the attestation concretely is (Open Q#4)

"Separate adversarial review pass + explicit negative-check attestation" is made
checkable as follows. On the hardened path, `quality-reviewer` (already bound to
both rubrics, `quality-reviewer.md` L35–38) runs **two passes that must not be
fused into one**, and emits a structured attestation:

**Pass 1 — Spec-conformance (rubric = the brief/spec):** does the grant do what
the plan says it should? Verdict: `SPEC-CONFORM: PASS/FAIL` + findings.

**Pass 2 — Blast-radius / false-success (rubric = "how could this be wrongly
green?"):** an adversarial pass whose job is to find the over-broad / false-
CLOSED path (L-C7). This pass must be **separately recorded** — a single fused
"looks fine" is a non-conformance.

**Negative-check attestation (the artifact that replaces "fixtures ran once"):**
a structured block, one row per grant/enforcement change, that must assert for
each:

| Field | What it asserts | Example |
|---|---|---|
| `grant` | the exact grant/line changed | `lessons-writer: write .gleipnir/lessons/<named-file>` |
| `intended_scope` | the narrowest correct scope | single named file, not a glob |
| `over_broad_form_checked` | the specific wrong form ruled out | `lessons/**` glob absent |
| `evidence` | **a concrete, reproducible artifact** — literal grep/diff output, a digest comparison, or a byte-for-byte quote of the applied line — NOT a narrative assertion (see substance rule D9) | `$ grep -n '\*\*' .gleipnir/agents/x.md → (no match)`; or `sha256(file)=<hex> == keys/x.digest` |
| `negative_result` | the explicit NOT assertion | "`lessons/**` is NOT present" |
| `attested_by` | reviewer identity (NOT the author) | `quality-reviewer` (L-C8) |

**Substance rule (D9) — the `evidence` field must be falsifiable, not
narrative.** A schema-complete attestation with a vague `evidence` value
(e.g. `"reviewed the change, looks correct"`) is **the exact false-success L-C7
exists to catch** and MUST be rejected. `evidence` is only satisfied when it
cites a **concrete, reproducible artifact** — a literal command and its output
(`grep`/`diff`/digest comparison), or a byte-for-byte quote of the applied
line(s) — such that a second party can re-run it and get the same result. A
narrative assertion that cannot be independently reproduced is a non-conformance,
not evidence.

**Correspondence rule (D11) — the evidence must test the form it claims to
test.** A reproducible, non-narrative artifact is necessary but STILL not
sufficient: the cited command/pattern/quoted-line in `evidence` must be checking
for the **same over-broad form named in `over_broad_form_checked`** for that row.
Reviewer-constructed failure it closes: a row with
`over_broad_form_checked = "lessons/** glob absent"` but
`evidence = "$ grep -n 'foo_unrelated_pattern' … → (no match)"` — real,
reproducible, non-narrative, yet grepping for the *wrong* pattern entirely, so it
proves nothing about the `lessons/**` claim. Spec-review MUST verify the
`evidence` pattern/target is the SAME over-broad form as
`over_broad_form_checked` (and, where applicable, the same file as `grant`) — not
merely that *some* reproducible artifact was cited. A mismatch is a
non-conformance.

**Checkability:** a spec-reviewer / the engine can verify the hardened path was
honoured by confirming (i) two distinct verdict lines exist (not one fused
verdict); (ii) an attestation block with all six fields per grant exists and
`attested_by ≠ plan author`; **(iii) — the substance gate — each `evidence`
field cites a reproducible artifact (command+output, digest comparison, or
verbatim quoted line), NOT a narrative like "looks correct"**; **and (iv) — the
correspondence gate — each `evidence` artifact actually tests the specific form
named in that row's `over_broad_form_checked`/`negative_result` (same pattern,
same target file), not an unrelated pattern.** Spec-review MUST reject an
attestation that is schema-complete but fails (iii) [substantively vague] or
(iv) [evidence does not correspond to the claim]. Absence of any of (i)–(iv) →
the enforcement change is **not cleared**; it cannot report SUCCESS. This
directly answers the precedent's fixture-#10 concern (an over-broad `lessons/**`
glob vs. one named file passes a fixtures-ran-once check while being wrong — the
negative-check forces the reviewer to assert, with reproducible evidence *that
greps for `lessons/**` specifically*, that the glob is *absent*).

### §T5 — Integrations

- **G-5 engine (future):** reads the amended `stage-role-map.md`, computes Axis
  1/Axis 2 over the plan's declared touched-path set, routes. No LLM call in the
  route decision.
- **Orchestrator (pre-engine):** applies the same rule as prompt guidance when
  sequencing.
- **quality-reviewer:** executes the hardened path (§T4); no new binding needed.
- **G-3.1 digests / S-3 preflight:** unaffected; `keys/**` edits are simply
  routed hardened by Axis 2(a).

---

## Link — validated before "building" (writing the amendment text)

- ✅ `stage-role-map.md` read in full (61 lines); the amendment is additive and
  does not alter the meaning of any existing line (Assemble step 2 diff).
- ✅ Trust-tier path principle confirmed in the decision record (L115) — the
  classifier is consistent with an already-ratified framework construction, not
  a novel judgment surface.
- ✅ `quality-reviewer.md` L32–38 confirms both-stage binding — no agent-file
  edit required for the hardened path (D7).
- ✅ Repo + `.gleipnir/` layouts verified on disk so every glob in Axis 1/2
  refers to a real location (§T2).
- ✅ Determinism check completed against the edge-case table (§T3) — no "it
  depends" cell → **encodable → no escalation.**

---

## Assemble — intended build order (operator-applied)

**Step 1 — spec-review (quality-reviewer, read-only).** Check this plan's
amendment text (step 2) against the brief and the map: (a) is the classifier
truly mechanical (challenge every §T3 row for a hidden judgment call)? (b) does
the hardened-path attestation (§T4) satisfy L-C7/L-C8? (c) is the diff purely
additive? This is itself a Tier-3 *enforcement* change to the routing config, so
per the very rule it proposes, spec-review should treat it on the **hardened
path** (Axis 2(a): `stage-role-map.md ∈ E`).

**Step 2 — Operator applies the amendment to `.gleipnir/stage-role-map.md`.**
The precise before/after, diff-shaped:

**INSERT a new section immediately AFTER the existing `## Binding rules` block
(current lines 49–61), at end of file. No existing line is changed.** Current
file ends at line 61 (`  action are separate delegations (task-decomposition isolation).`).

```diff
   - One verb, object, verification and boundary per delegation; exploration and
     action are separate delegations (task-decomposition isolation).
+
+## Prose/config-only track (blast-radius split)
+
+**Status: ratified (Approach B), operator-applied.** A specialisation of the
+map above: some plans have **no executable artifact and no test arbiter** — they
+touch only prose and declarative config. The default is still the full 8-stage
+pipeline; this track is the scoped exception, and it is **split by blast
+radius** so the highest-consequence change class is never under-reviewed (L-C7).
+The route is **mechanically computable** from a plan's declared touched-path set
+`P` — the future G-5 engine routes on it with no per-plan LLM judgment.
+
+### Axis 1 — eligibility gate (the disqualifier)
+
+A plan is track-eligible **only if `P` contains zero executable/interpreted
+artifacts.** If any path in `P` matches the disqualifier set `X`, the plan runs
+the **full 8-stage pipeline**, no matter how small the code portion:
+
+> `X` = `src/**`, `tests/**`, `hooks/**`, `bin/**`, `**/Makefile`, `**/*.mk`,
+> `**/Containerfile*`, `.github/**`, any standalone `**/*.yml`/`**/*.yaml`, any
+> `**/*.sh|*.bash|*.py|*.js|*.ts|*.rs|*.go`, any file with mode `+x` or an
+> interpreter shebang in added content.
+
+Rationale: a Makefile/CI file/hook *runs*; distinguishing inert data-YAML from
+build-executed YAML is not reliably grep-able, so standalone YAML is disqualified
+safe-side (integrity > efficiency). This kills the "mostly config but one hook"
+trap. Note: `opencode.jsonc`/`opencode.json` are NOT in `X` (declarative, not
+executable) but ARE enforcement wiring — they are routed hardened via Axis 2(a),
+not disqualified.
+
+### Axis 2 — routing within the eligible set
+
+A track-eligible plan is **enforcement-bearing** (→ hardened path) if EITHER:
+
+- **(a) path rule:** any path in `P` is under the enforcement-path set `E` =
+  `.gleipnir/agents/**`, `.gleipnir/plugins/**`, `.gleipnir/sandbox/**`,
+  `.gleipnir/policy/**`, `.gleipnir/keys/**`, `.gleipnir/stage-role-map.md`
+  itself, or the root opencode config `opencode.jsonc` / `**/opencode.json`
+  (it loads this map via `instructions`, gates the MCP brokers via `enabled`,
+  and sets `default_agent`); **or**
+- **(b) content rule:** an added/changed line matches a grant/enforcement
+  pattern `G`, in EITHER its YAML/frontmatter form OR its JSON(C) form:
+    - YAML: a `permission:` or `tools:` block, or a capability line
+      (`edit|write|task|bash|webfetch` with `allow`/`deny`);
+    - JSON(C): a JSON-quoted enforcement key —
+      `"permission"|"tools"|"enabled"|"instructions"|"default_agent"|"subagent_depth"|"mcp"`;
+    - a new/edited row in this file's binding tables;
+    - a keyed digest line under `keys/**` matching `^[0-9a-f]{64}\b`
+      (redundant with Axis 2(a); retained as documentation).
+
+Otherwise the plan is **low-consequence prose** (→ light path): paths confined
+to `.gleipnir/goals/**`, `.gleipnir/decisions/**` prose, `.gleipnir/plans/**`,
+`.gleipnir/logs/**`, `**/*.md` docs, READMEs, comments, with no `G`-pattern
+match. (This is the same construction as G-6's trust tiers: *trust is a property
+of the path, encoded in code* — see
+`decisions/gleipnir-layout-and-memory-model.md`. Axis 2(b) is a content
+tripwire: a match forces the hardened path; an absence proves nothing, because
+Axis 2(a) already routes every enforcement *path* to the hardened side.)
+
+### Light path (low-consequence prose)
+
+Stages collapse to a **single spec-review pass** by `quality-reviewer`
+(`spec-review` and `quality` rubrics run together, since there is no
+post-implementation artifact to blast-radius-review); `test`/`code`/`git`/`gate`
+carry an attested **"N/A — no executable artifact"** transition. This is the
+precedent from `plans/lesson-escalation-process.md`, now ratified **only** for
+this low-blast subset.
+
+### Hardened path (enforcement-bearing config)
+
+The two rubrics **do NOT fuse.** `quality-reviewer` runs them as **two separate
+passes**, each with its own recorded verdict:
+
+1. **Spec-conformance** (rubric = the plan/spec): `SPEC-CONFORM: PASS/FAIL`.
+2. **Blast-radius / false-success** (rubric = *how could this be wrongly
+   green?*): an adversarial pass whose job is to find the over-broad / false-
+   CLOSED path (L-C7). A single fused "looks fine" verdict is a non-conformance.
+
+Plus an **explicit negative-check attestation** — replacing "fixtures ran once"
+— produced by `quality-reviewer` (never self-attested by the author, L-C8), one
+row per grant/enforcement change, each asserting: the exact grant, its intended
+(narrowest) scope, the specific **over-broad form checked-for-and-ruled-out**,
+the **evidence**, the explicit **negative result** ("`<over-broad form>` is
+NOT present"), and `attested_by`. Example: for a `lessons/` write grant, the
+attestation must assert a `lessons/**` glob is **NOT** present where a single
+named file is intended.
+
+**Substance rule:** the `evidence` field must cite a **concrete, reproducible
+artifact** — literal command+output (`grep`/`diff`), a digest comparison, or a
+byte-for-byte quote of the applied line — NOT a narrative assertion (e.g.
+"reviewed it, looks correct"). A schema-complete attestation whose evidence is
+substantively vague is the exact false-success L-C7 exists to catch and MUST be
+rejected at spec-review.
+
+**Correspondence rule:** the cited artifact must actually test the form it
+claims to. The pattern/target in `evidence` must be the **same over-broad form
+named in `over_broad_form_checked`** (and, where applicable, the same file as
+`grant`) — grepping for an unrelated pattern is reproducible but proves nothing
+and MUST be rejected. (E.g. a `lessons/**`-absent claim requires `evidence` that
+greps for `lessons/**` specifically, not some other string.)
+
+An enforcement-bearing prose/config plan may **not** report SUCCESS unless (i)
+two distinct pass verdicts exist, (ii) the negative-check attestation is present
+with all fields and `attested_by ≠ author`, (iii) every `evidence` field cites a
+reproducible artifact, not a narrative, and (iv) each `evidence` artifact tests
+the specific form named in that row's `over_broad_form_checked` (not an unrelated
+pattern).
```

**Step 3 — (optional, operator) pointer in `AGENTS.md`.** Add a one-line note in
the pipeline/guard-status framing that the prose/config-only track exists and is
blast-radius-split. Not required for the rule to stand (D7).

**Step 4 — (informational) supersede the precedent note.** In
`plans/lesson-escalation-process.md`, the improvised mapping is now superseded by
the ratified track (light path). Tier-0, informational; operator or a future
Tier-0 writer may annotate.

---

## Stress-test — acceptance checks the result is validated against

1. **Mechanical-route check (dominant).** For each row of the §T3 edge-case
   table, an independent reader computes the route using only glob membership +
   the `G` regex set and gets the table's answer. **Zero rows require semantic
   judgment.** (If any reviewer finds a row that genuinely needs a per-plan call,
   the encodability claim fails → re-open Open Q#3 → escalate to operator for
   fallback-to-C. This is the built-in tripwire, not a silent planner decision.)
2. **Additive-diff check.** Applying the Assemble step-2 diff leaves current
   lines 1–61 of `stage-role-map.md` byte-identical; only an appended section is
   added. The 8-stage pipeline and all four Binding rules still read correctly.
3. **Disqualifier check.** A plan whose `P` includes any element of `X`
   (e.g. one `hooks/*.sh`, one `Makefile`, one `src/*.py`) routes to the full
   8-stage pipeline — confirmed against §T3 "mostly config + hook", "Makefile/CI",
   and ".py helper" rows.
4. **Enforcement-route check.** A plan touching `.gleipnir/agents/**` or adding a
   `permission:`/`tools:` line or a `keys/**` digest routes to the **hardened**
   path — confirmed against §T3 rows 3–8.
5. **opencode-config check (D8/D11).** A plan editing `opencode.jsonc` — including
   the reviewer's concrete case, removing `.gleipnir/stage-role-map.md` from the
   `instructions` array, or toggling a broker `"enabled"`, or changing
   `"default_agent"`/`"subagent_depth"` — routes to the **hardened** path via
   **Axis 2(a)** (`opencode.jsonc ∈ E`), which alone is unconditional and
   sufficient. (Note per D11: for the `instructions`-element removal, Axis 2(b)
   does NOT independently fire — the removed line is an array element, not a key
   declaration — but 2(a) governs regardless.) Confirmed against §T3's three
   `opencode.jsonc` rows. It must NOT route light.
6. **Light-route check.** A doc/goal/decision-prose-only plan with no `G` match
   routes **light** — confirmed against §T3 goal-typo, decision-prose, and
   README rows.
7. **Hardened-path checkability.** A future enforcement-bearing prose/config plan
   is only clearable if it carries: two distinct verdict lines (spec-conform +
   blast-radius, unfused) **and** a negative-check attestation with all six
   fields per grant, `attested_by ≠ author`. A plan missing either is rejected
   by spec-review. (§T4.)
8. **Evidence-substance + correspondence check (D9/D11).** Each attestation
   `evidence` field (a) cites a concrete, reproducible artifact (command+output,
   digest comparison, or verbatim quoted line) — narrative-only evidence
   (e.g. "reviewed it, looks correct") is **rejected** (§T4 (iii)); **and (b) —
   the correspondence gate — the cited command/pattern/quoted-line tests the SAME
   over-broad form named in that row's `over_broad_form_checked` (same pattern,
   same target file), not an unrelated pattern** (§T4 (iv)). Reviewer's failure
   case that (b) rejects: `over_broad_form_checked = "lessons/** glob absent"`
   paired with `evidence = grep -n 'foo_unrelated_pattern' …` — reproducible and
   non-narrative, yet grepping the wrong pattern, so it proves nothing about the
   claim. Presence + reproducibility are necessary but not sufficient without
   correspondence.
9. **No-self-attest check (L-C8).** The attestation's `attested_by` is
   `quality-reviewer`, never the plan/author role.
10. **Existence check (L-C15).** Every path cited (`src/`, `tests/`, `hooks/`,
    `bin/`, `Makefile`, `opencode.jsonc`, `.gleipnir/agents/**`, `plugins/**`,
    `sandbox/**`, `policy/**`, `keys/**`, `goals/**`, `decisions/**`,
    `stage-role-map.md`) verified to exist on disk this session (§T2 + round-2
    read of `opencode.jsonc`), or the disqualifier globs are marked as
    forward-looking file *classes* rather than specific existing files.
11. **Digest-regex check (D10).** The digest pattern `^[0-9a-f]{64}\b` matches a
    sample 64-hex-char line (e.g. `a3f...` × 64 hex chars) and does NOT match a
    non-hex or wrong-length line — confirming the D10 pattern is a real regex,
    not descriptive prose. (Documentary: `keys/**` already routes via Axis 2(a);
    this check only validates the regex is well-formed.)

---

## Execution Workflow

1. **spec-review** (quality-reviewer, read-only, HARDENED per Axis 2(a) since the
   target is `stage-role-map.md ∈ E`): run the two unfused passes against this
   plan — Pass 1 spec-conformance vs the brief; Pass 2 adversarial: *attack the
   classifier* — try to construct a touched-path set that the §T3 rules route
   ambiguously. Produce a negative-check attestation for the amendment's own
   routing claim (the over-broad form to rule out: "a plan that touches enforce-
   ment config is mis-routed to the light path"). Emit verdict:
   APPROVED / APPROVED-WITH-NOTES / CHANGES-REQUIRED.
2. **If spec-review finds a genuinely non-mechanical §T3 row:** do **not** patch
   it in-planner. That is the Open-Q#3 determinism failure materialising →
   return to the convergence gate for the operator's **fallback-to-C** decision
   (brief lines 326–336, Open Q#3). The planner/reviewer must not choose C.
3. **If APPROVED:** hand the Assemble step-2 diff to the **operator** for
   application to `stage-role-map.md` (Tier-3, agent-unwritable, G-1). No roster
   agent applies it.
4. **Operator** applies the diff verbatim; optionally adds the AGENTS.md pointer
   (step 3) and annotates the superseded precedent (step 4).
5. **Post-application:** the amended map becomes the routing config the future
   G-5 engine reads; pre-engine, the orchestrator applies Axis 1/Axis 2 when
   sequencing prose/config plans.

**Boundary reminder for implementers:** this plan yields *text*, not an applied
Tier-3 edit. `gleipnir-plan` wrote only this Tier-0 plan file
(`.gleipnir/plans/prose-config-only-track.md`). The amendment itself is
operator-applied.
