# Design Brief: S5 — G-3.1 attestation (HMAC marker) in TypeScript

> **Status: CONVERGED — all six decisions (D-S5-1..6) decided by the operator
> via the orchestrator's `question` tool (operator-via-orchestrator,
> L-C6-legitimate — NOT self-attested).** The Decision Analysis below is the
> INPUT to convergence (per K-3) and is left unchanged; the operator's converged
> choices are recorded in `## Selected Approach`. **Five of six matched the
> brainstorm recommendation; D-S5-4 DIVERGED** (operator chose the WIDER scope
> 4b over the recommended primitive-only 4a — see the divergence flag below).
> `gleipnir-plan` plans from this converged brief.

## Problem Statement

Re-express the keyed-HMAC verification marker natively in TypeScript inside the
pi extension, so the S4 engine's completion edges (specifically the GIT→GATE
`attempt_gate` edge, which S4 built to accept only a `GREEN` `Attestation`
VALUE object) can carry **unforgeable evidence** rather than an agent-asserted
claim. The S4 engine ported the attestation *contract shape*
(`Attestation`/`AttestationStatus` value type +
`attempt_gate` refusal logic) but — per the explicitly-drawn D-S4-4 boundary —
built **NO HMAC, NO key handling, NO marker verification, NO golden-vector
reproduction**. That is precisely S5's job.

The build-order S5 goal (L156-170) names the oracle as
`src/gleipnir/verify/marker.py` + `tests/fixtures/golden_marker*.json` +
`golden_key.bin`, with the cross-language golden-vector test as the exit
criterion, and flags **[ASSUMPTION-3]** (preserve the Python key/marker format
byte-for-byte vs re-specify) as a material decision to surface if
re-specification arises.

## The oracle's ACTUAL shape (read directly this session — a decisive finding)

Reading the source (not the build-order's summary) surfaced a **schema
mismatch that must be surfaced to the operator**, because it changes what
"reproduce the Python golden vectors" even means. There are **TWO distinct
HMAC-marker constructs** in the Python oracle, and the build-order's S5 text
conflates them:

### Construct 1 — `verify/marker.py` `Marker` (the build-order's named oracle file)
- Fields: `{version, tree_hash, minted_at, mac}` (222 lines, `test_marker.py`).
- **MAC binds a TREE HASH:** `mac = HMAC(key, canonical(version, tree_hash,
  minted_at))`, where `canonical = "\x1f".join([str(version), tree_hash,
  str(minted_at)])`, `DIGEST = sha256`, hex output.
- `compute_tree_hash` folds `src/`+`tests/` file paths+contents into one sha256.
- **Has NO committed golden JSON fixture.** Its tests mint-and-validate live
  against a `tmp_path` tree; the only shared asset is `golden_key.bin`.
- **This is the G-3.1 verifier** (the "did the tests actually run on THIS tree"
  skip-token). It is NOT what `attempt_gate` consumes.

### Construct 2 — `engine/bridge.py` `StateMarker` (what the golden fixtures ACTUALLY pin)
- Fields: `{version, pipeline_state, allowed_agents, minted_at, mac}` (192 lines,
  `test_bridge.py`).
- **MAC binds the STATE PAYLOAD directly** (no tree hash — a pipeline state has
  nothing to recompute off a tree): `mac = HMAC(key, canonical(version,
  pipeline_state, agents_joined, minted_at))`, where
  `agents_joined = "\x1e".join(sorted(allowed_agents))` and the four parts are
  `"\x1f"`-joined, sha256, hex.
- **`golden_marker.json`, `golden_marker_tampered.json`, and
  `dogfood_bridge.json` are ALL `StateMarker` vectors** — verified by reading
  them: `{"allowed_agents":["gleipnir-plan"],"mac":"2707c101…","minted_at":1000,
  "pipeline_state":"plan","version":1}`. The tampered one flips
  `pipeline_state` `plan`→`git`, keeps the MAC, and must fail.
- `bridge.py` *imports and reuses* `verify/marker.py`'s `load_key` /
  `KeyUnavailable` / `DIGEST` / fail-closed posture — so the KEY FORMAT and
  digest choice are shared, but the SIGNING INPUT differs (tree-hash vs
  state-payload).

### Construct 3 (already-existing, decisive) — the PROVEN opencode-side TS port
- `.gleipnir/plugins/sequence-gate.ts` **already re-expresses `StateMarker`
  validation in TypeScript** using Node's built-in `node:crypto`
  (`createHmac("sha256", key)…digest("hex")` + `timingSafeEqual`), with
  `canonicalSigningInput` identical to `bridge.py`'s (`\x1f`/`\x1e` separators,
  sorted agents).
- `tests/test_sequence_gate.mjs` **already proves this TS validates the Python
  golden `StateMarker` fixtures byte-for-byte** and rejects the tampered one,
  under Node's `node:crypto` — i.e. **the byte-for-byte cross-language
  reproduction the S5 exit criterion demands has already been demonstrated once,
  in TS, against these exact fixtures.** S5 is re-expressing a *proven-portable*
  contract into the pi-package, not discovering whether it ports.

**Why this is load-bearing for S5's decisions:** the S4 engine's `attempt_gate`
consumes an `Attestation{pipelineId, status}` VALUE object (G-3.2 shape) — which
is neither `Marker` nor `StateMarker`. So S5 must decide **which marker(s) it is
actually porting** and **how the HMAC primitive binds to the S4 `Attestation`
gate**. This is not a mechanical port of one file; it is a
boundary-and-scope decision. Full analysis in D-S5-1.

## How S5 attaches to the already-built S4 engine (confirmed by reading)

- `pi-package/src/engine/attestation.ts` (S4) — `Attestation` is a **real class**
  (brand-checked, `Object.freeze`d) + `AttestationStatus` const-object union.
  Its own header comment states: *"S5 extends it with real HMAC marker
  verification — VALUE/CONTRACT only here, per D-S4-4."* This is the explicit
  seam S5 extends.
- `pi-package/src/engine/engine.ts` (S4) — holds `attemptGate(attestation)`,
  which brand-checks `instanceof Attestation`, requires `status===GREEN` and
  `pipelineId` match, refuses otherwise (state unchanged). S5 does **not** change
  this refusal logic; S5 supplies the *upstream* machinery that MINTS/VALIDATES
  the evidence an `Attestation` (or a persisted state marker) rests on.
- **The two named S4 hardening seams that "land here" (per SESSION-STATE +
  S4 addendum in `decisions/pi-replatform-open-q1.md`):**
  1. **resumeAt raw-string brand-check** — S4's `resumeAt(id, state)` accepts a
     same-valued raw string where Python's `isinstance` would reject, because
     D-S4-1's const-object-enum idiom makes states plain runtime strings.
     Operator-ACKNOWLEDGED accepted consequence; hardening deferred to S5.
  2. **Signed restart/compaction persistence** — S4 kept the engine an
     in-process singleton (D-S4-2); signed persistence over `pi.appendEntry` was
     flagged as the natural landing spot *if* S5's HMAC machinery is available.

## Constraints

- **Oracle-bound, and the oracle is now precisely identified** (above): the
  byte-for-byte target is the `StateMarker` construction (`golden_marker*.json`),
  and separately the `Marker` tree-hash construction if S5 also ports the G-3.1
  verifier. The exit criterion ("TS marker verifies against the existing golden
  fixtures") maps to the `StateMarker` fixtures.
- **Node built-in crypto, no new dependency** (`decisions/runtime-and-deps.md`):
  the stdlib-only-core posture forbids adding an npm HMAC package; Node's
  `node:crypto` is the stdlib-equivalent and is *already* what the proven
  opencode-side `sequence-gate.ts` uses. (D-S5-2 confirms; recommendation is
  effectively forced.)
- **Test harness:** pi-package tests run via
  `node --experimental-strip-types --test test/*.test.ts` under
  `bin/gleipnir-sandbox --profile pi` (`--network=none`). HMAC/key tests are
  pure and fully exercisable offline (no live model, no network) — the golden
  fixtures + key are committed files.
- **No scope-creep into S4's engine.** S5 must not alter `attemptGate`'s refusal
  logic, `TRANSITIONS`, the revert budget, or the five S1–S3 modules. S5 adds a
  `verify/` (marker) layer and, per the converged D-S5 scope, a thin seam.
- **Per L-C36:** all file shapes above were read directly this session.

## Approaches Considered (the overarching S5 shape)

Three genuinely distinct overall strategies; the six sub-decisions (D-S5-1..6)
are then analysed individually because each is separable.

### Approach A: Port ONLY the `verify/marker.py` `Marker` primitive (literal build-order reading)
**Summary:** Re-express `verify/marker.py` (`Marker`, `mint`, `validate`,
`load_key`, `compute_tree_hash`, canonical signing input) as
`pi-package/src/verify/marker.ts`, mirroring the Python module name; port
`test_marker.py`. Leave `StateMarker`/bridge entirely alone.
**Tradeoffs:**
- Pro: Most literal reading of the build-order's named oracle file.
- Pro: Cleanest single-module SRP; the G-3.1 verifier primitive stands alone.
- Con: **The named golden fixtures (`golden_marker*.json`) are `StateMarker`
  vectors, so `verify/marker.ts` alone CANNOT verify them** — the stated exit
  criterion would be unmet by this approach. `compute_tree_hash` also has no
  in-process pi consumer yet (the engine is a singleton; there is no fresh-process
  tree to re-hash for a skip-token in pi).
- Con: Leaves the S4 `attempt_gate` evidence unbound to any real HMAC.
**Estimated Scope:** `pi-package/src/verify/marker.ts` + `test/marker.test.ts`.
Complexity: **medium**.
**Risk:** **medium** — ships a correct primitive that does not satisfy the
literal exit criterion; risks a spec-review FAIL on "verifies against the golden
fixtures."

### Approach B: Port the `StateMarker` (bridge) construction — the fixtures' actual generator
**Summary:** Re-express `bridge.py`'s `StateMarker` (`mint_state`,
`validate_state`, `canonicalSigningInput`, `load_key`) as
`pi-package/src/verify/marker.ts` (or `stateMarker.ts`), reproducing the
`golden_marker*.json` / `dogfood_bridge.json` vectors byte-for-byte — exactly as
the proven `.gleipnir/plugins/sequence-gate.ts` already does. Port the golden
cross-language test as the exit criterion.
**Tradeoffs:**
- Pro: **Directly meets the stated exit criterion** ("verifies against the
  existing golden fixtures") — the fixtures ARE `StateMarker`.
- Pro: A proven TS reference implementation already exists (sequence-gate.ts);
  the re-expression is low-risk and byte-parity is already demonstrated once.
- Pro: `StateMarker` is what actually gates state authority (it carries
  `pipeline_state`+`allowed_agents`), so it is the construct that makes S4's
  in-process engine's *persisted* position unforgeable — directly enabling the
  deferred signed-restart seam (D-S5-4).
- Con: Diverges from the build-order's literal "port `verify/marker.py`" wording
  (needs the operator to ratify that the fixtures, not the filename, define the
  target).
- Con: Does not by itself port the tree-hash G-3.1 verifier (may or may not be
  in-scope — D-S5-1).
**Estimated Scope:** `pi-package/src/verify/marker.ts` + `test/marker.test.ts`
(golden-vector class) + committed-fixture reuse. Complexity: **medium**.
**Risk:** **low** — byte-parity already proven in TS; the main task is faithful
re-expression + test port.

### Approach C: Port BOTH constructs (verifier `Marker` + bridge `StateMarker`), scoped by consumer
**Summary:** Re-express BOTH `verify/marker.py`'s `Marker` (tree-hash G-3.1
verifier) AND `bridge.py`'s `StateMarker` (state-payload signer) in TS, sharing
the common key-load + digest + canonical-join primitives, each with its own
golden/parity tests. Bind the `StateMarker` path to the S4 engine's persisted
position (signed-restart seam); keep `Marker` as the standalone skip-token
primitive for a future preflight/test-gate consumer.
**Tradeoffs:**
- Pro: Complete parity with the Python `verify/` + `bridge/` HMAC surface;
  nothing about G-3.1 is left un-ported.
- Pro: Satisfies BOTH the literal filename reading AND the golden-fixture exit
  criterion.
- Con: **Largest scope** — ports a `compute_tree_hash` + `Marker` primitive that
  has NO in-process pi consumer yet (the engine is a singleton; there is no
  fresh-process skip-token flow in pi). Risks building the tree-hash verifier
  ahead of any consumer, against the roadmap's "no step builds ahead of need"
  discipline.
- Con: Two marker schemas in one slice raises the SRP/decomposition question
  (D-S5-5) and the review burden.
**Estimated Scope:** `pi-package/src/verify/{marker,stateMarker}.ts` (or one
module, two exports) + two test classes. Complexity: **medium-high**.
**Risk:** **medium** — over-building risk; the tree-hash half has no pi consumer.

## Decision Analysis

> **Not converged. Each D-S5-N below is options + framework + recommendation,
> to be surfaced to the operator by the orchestrator. The recommendation is the
> INPUT to convergence, per K-3 — never the decision.**

Six material decisions. D-S5-1 (which marker construct[s] S5 ports) is the
central one and conditions the rest; the build-order's ASSUMPTION-3 is embedded
in it.

### D-S5-1 — Which marker construct does S5 port? (THE central decision; resolves ASSUMPTION-3's real content)

**Framework used:** Reversibility Filter → Weighted Decision Matrix
(multi-option architectural choice with long-lived consequences; S6/S8 build on
whatever S5 ships).

**Reversibility:** One-Way Door (soft). S5's marker module shape is consumed by
the signed-restart seam and by S8's attested bus events; re-porting after those
build on it is costly. Full analysis warranted.

**The ASSUMPTION-3 reproduction analysis actually performed** (the build-order
asked for this, not a guess): reading `marker.py`'s algorithm (sha256,
`\x1f`-joined `[version, tree_hash, minted_at]`, hex) AND the golden fixtures
shows the fixtures are **`StateMarker`** (`bridge.py`) vectors, NOT `Marker`
vectors. `bridge.py`'s construction (sha256, `\x1f`-joined
`[version, pipeline_state, "\x1e".sorted(agents), minted_at]`, hex) is exactly
what `golden_marker.json` pins, and `.gleipnir/plugins/sequence-gate.ts` already
reproduces it byte-for-byte in Node `node:crypto`. **Conclusion of the
reproduction analysis: byte-for-byte reproduction is ACHIEVABLE and already
PROVEN for the `StateMarker` construction; NO re-specification is needed. The
key format (`golden_key.bin`, trimmed bytes), digest (sha256), and canonical
signing input all port unchanged.** ASSUMPTION-3 HOLDS — with the caveat that
"the marker" the fixtures define is `StateMarker`, so the operator must confirm
the target is the fixtures (Approach B/C), not the `verify/marker.py` filename
in isolation (Approach A, which cannot verify them).

**Analysis results:**

| Criterion | Weight | A (verifier `Marker` only) | B (`StateMarker` only) | C (both) |
|---|---|---|---|---|
| Meets stated exit criterion ("verifies golden fixtures") | 10 | 2 → 20 | 10 → 100 | 10 → 100 |
| Binds S4 `attempt_gate`/persisted-position to real HMAC | 9 | 3 → 27 | 9 → 81 | 9 → 81 |
| Byte-parity already proven in TS (low port risk) | 7 | 4 → 28 | 10 → 70 | 8 → 56 |
| No building ahead of a pi consumer (roadmap discipline) | 8 | 5 → 40 | 9 → 72 | 4 → 32 |
| Completeness of G-3.1 HMAC surface parity | 6 | 4 → 24 | 6 → 36 | 10 → 60 |
| Implementation + review cost (higher = cheaper) | 5 | 7 → 35 | 8 → 40 | 4 → 20 |
| **Total** | | **174** | **399** | **349** |

**Recommended (D-S5-1): Approach B — port the `StateMarker` construction (the
fixtures' actual generator) as the S5 marker primitive, reproducing
`golden_marker*.json` byte-for-byte via Node `node:crypto`, exactly as the
proven `sequence-gate.ts` reference does.** B directly meets the exit criterion,
binds the engine's persisted position to real HMAC, and has the lowest port risk
(byte-parity already demonstrated). **The tree-hash `verify/marker.py` `Marker`
(Approach A/C's extra half) is recommended DEFERRED** until a pi consumer for a
tree-hash skip-token exists (none does in the in-process engine today) — porting
it now is building ahead of need. **The decision the operator must make: B vs C**
(A is not recommended — it cannot verify the named golden fixtures). Choose C
only if the operator wants full `verify/` + `bridge/` HMAC parity in this slice
despite no current pi consumer for the tree-hash half.

**Bias check:** ⚠️ *Scope Creep (candidate, ruled out for B):* C would fold in a
tree-hash verifier with no consumer "while we're in the crypto file" — the
detector says force the narrower boundary. B resists it. No other detector fires
decisively; the byte-parity evidence is real (not availability bias — it is a
committed, passing test).

### D-S5-2 — Node crypto module choice (built-in `node:crypto` vs npm package)

**Framework used:** Reversibility Filter (fast-track — the constraint plus prior
art make this a confirm-not-decide).

**Reversibility:** Two-Way Door, but effectively forced by policy + precedent.

**Analysis:** `decisions/runtime-and-deps.md` mandates stdlib-only for the
enforcement core (of which the G-3.1 marker is a canonical member) —
*"Fewer dependencies = smaller trusted surface to audit = directly serves
G-1/G-2. Stdlib-only is not habit; it is trust-surface minimisation."* Node's
`node:crypto` is the stdlib-equivalent (ships with the Node runtime, no
`package.json` dependency, nothing new inside the S-2 boundary). The proven
opencode-side port (`sequence-gate.ts`, `test_advance_hook.mjs`) **already uses
`createHmac`/`timingSafeEqual` from `node:crypto`** and reproduces the golden
vectors — so the choice is both policy-compliant AND precedented.

**Recommended (D-S5-2): Node built-in `node:crypto`
(`createHmac("sha256", key).update(input,"utf8").digest("hex")` +
`timingSafeEqual` for the constant-time compare). NO npm HMAC package.** This is
effectively forced by the stdlib-only-core constraint and matches the proven
reference implementation exactly. **Operator confirms** (recommended: yes). The
one sub-point to flag: `timingSafeEqual` requires equal-length buffers; the
reference guards length first (`if (got.length !== exp.length) return false`)
before the constant-time compare — S5 must preserve that guard.

**Bias check:** ⚠️ *Bandwagon (candidate, ruled out):* the recommendation rests
on the recorded trust-surface decision + a passing precedent, not on "everyone
uses node:crypto." None fires.

### D-S5-3 — Scope of the `resumeAt` raw-string brand-check hardening

**Framework used:** Pros-Cons-Fixes + Reversibility Filter (a scope-boundary
decision on a named, operator-acknowledged deferred seam).

**The precise question:** S4's `resumeAt(id, state)` accepts a same-valued raw
string (e.g. `resumeAt(id, "spec_review")`) where the Python oracle's
`isinstance(state, PipelineState)` raises, because D-S4-1's const-object-enum
idiom makes `PipelineState` values plain runtime strings. This is an
operator-acknowledged accepted consequence, with hardening deferred to S5. Is it
IN scope for S5?

**The key distinction:** this is an **engine-layer input-validation** concern
(reject a raw string at the rehydration-seam entry), NOT an HMAC/marker concern.
It shares S5's *theme* (hardening the persistence-seam entry) but is a different
mechanism (a runtime brand/tag check on the `state` argument, e.g. a
`PipelineState` set-membership guard or a branded type), touching
`engine/state.ts`/`engine.ts` — S4's modules — not the new `verify/` marker.

**Options:**
- **Option 3a — IN scope for S5, done alongside the marker.** S5 is "the
  persistence-seam session"; wiring signed persistence (D-S5-4) naturally passes
  a `state` value through the rehydration entry, so hardening the raw-string
  acceptance there is a coherent bundle.
- **Option 3b — IN scope for S5 ONLY IF signed persistence (D-S5-4) is also in
  scope** (they share the rehydration entry point); otherwise its own follow-up.
- **Option 3c — deferred further, as its own small engine-hardening follow-up**
  (it is not HMAC; it can stand alone with a `set`-membership guard + a test,
  independent of any marker work).

**Analysis:** The brand-check is genuinely small and independent (validate
`state` is a member of the `PipelineState` set at `resumeAt` entry; throw
otherwise — mirroring the Python `isinstance` refusal). Its natural coupling is
to the **rehydration entry**, which is exactly what D-S5-4's signed persistence
wires. If D-S5-4 lands in S5, doing the brand-check in the same slice is
efficient (Fix for the coupling con: the plan states the two touch the same
`resumeAt`/rehydration seam and are reviewed together). If D-S5-4 is deferred,
the brand-check has no marker to attach to and is cleaner as its own follow-up.

**Recommended (D-S5-3): Option 3b — bind the `resumeAt` brand-check hardening to
whatever D-S5-4 decides. If signed restart/compaction persistence is IN scope
for S5 (see D-S5-4), do the brand-check in the same slice (they share the
rehydration entry, and a signed marker feeding an unvalidated raw-string
`resumeAt` would be a hole). If persistence is deferred, defer the brand-check
with it as a joint small follow-up.** This keeps the two coupled concerns
together and avoids a signed-but-unvalidated seam. **Operator decides:** couple
to D-S5-4 (recommended), or split it out now regardless (3c) as a standalone
engine-hardening item.

**Bias check:** ⚠️ *Scope Creep (candidate, noted):* bundling non-HMAC engine
hardening into "the HMAC slice" could bloat S5 — mitigated because the coupling
is real (shared rehydration entry) and the item is tiny; the recommendation
explicitly ties it to whether the entry is touched at all. Not decisive.

### D-S5-4 — Scope of signed restart/compaction persistence (marker primitive only, vs wire the persistence)

**Framework used:** Second-Order Thinking + the build-order's own dependency
graph (S4 → S5 → S8).

**The precise question:** does S5 wire ACTUAL signed persistence of engine
position (mint a `StateMarker` on each transition, persist it over
`pi.appendEntry`, validate + rehydrate on session restart/compaction) — or does
S5 build ONLY the marker primitive (mint/validate + golden parity) and leave the
persistence WIRING to a later step?

**The dependency-graph argument (grounded in the build-order):** the roadmap's
graph is `S4 (engine) → S5 (attestation) → S8 (bus/ledger)`. S4 (D-S4-2)
converged the engine as an **in-process singleton with restart-survival
explicitly DEFERRED to "a named seam that S5 closes."** So the build-order does
anticipate S5 as the *natural landing spot* for signed persistence. BUT: S8 is
the bus/ledger/observer slice that consumes attested events, and
`session_before_compact`/`session_start(resume)` wiring is lifecycle-hook
integration that overlaps S8's event-stream concerns more than S5's
primitive-porting concern.

**Second-order analysis:**
- **Option 4a — marker primitive ONLY (mint/validate + golden parity + the
  `Attestation`-binding), persistence wiring DEFERRED.** Near-term: S5 ships a
  proven, tested HMAC primitive that S4's `attempt_gate` and a future persistence
  step both consume; S5's exit criterion ("verifies against golden fixtures") is
  met purely by the primitive + its tests. Far-term: clean — the *primitive*
  (hard part: byte-parity crypto) is proven once; wiring it into `pi.appendEntry`
  + the compaction/resume lifecycle hooks is a separable integration step that
  can land in S8 (which already owns lifecycle/event wiring) or its own S5.5.
- **Option 4b — marker primitive + FULL signed persistence wiring in S5.**
  Near-term: S5 delivers end-to-end restart survival. Far-term: pulls
  `session_before_compact`/`session_start(resume)` lifecycle-hook integration
  and `pi.appendEntry` semantics into the "port the HMAC" slice — a scope the
  build-order graph associates more with S8; risks S5 blocking on lifecycle-hook
  behaviour (does a freshly-resumed session re-bind the engine singleton?) that
  is genuinely new integration, not a port.

**Key insight (separability, mirroring D-S4-2's own logic):** persistence
*integrity* (the signed marker) and persistence *survival/wiring* (appendEntry +
lifecycle hooks) are separable — D-S4-2 already made exactly this split when it
deferred survival to "a named seam S5 closes (signed via S5's HMAC marker)." S5
can legitimately *close the integrity half* (ship the marker primitive the seam
needs) and leave the *survival-wiring half* as the seam's remaining wire-in,
without S5 having to own the lifecycle-hook integration.

**Recommended (D-S5-4): Option 4a — S5 builds the marker PRIMITIVE only
(`StateMarker` mint/validate, `node:crypto`, golden-vector parity, and the
binding that lets S4's `attempt_gate`/persisted position rest on a real HMAC).
The ACTUAL persistence WIRING (mint-on-transition + `pi.appendEntry` +
`session_before_compact`/`session_start(resume)` rehydration) is DEFERRED to a
named seam — landing most naturally in S8 (lifecycle/event integration) or a
scoped S5.5, per the operator's call.** This meets S5's stated exit criterion
with the primitive, respects the S4→S5→S8 graph (integration lives with S8's
lifecycle wiring), and does not make the HMAC port block on genuinely-new
lifecycle-hook behaviour. **Operator decides:** primitive-only (recommended,
4a), or wire full signed persistence now (4b — accepts pulling lifecycle-hook
integration into S5). Note D-S5-3 is coupled to this: if 4a, the `resumeAt`
brand-check defers with the wiring; if 4b, it comes into S5.

**Bias check:** ⚠️ *Scope Creep (candidate, ruled out for 4a):* 4b broadens the
HMAC slice to absorb lifecycle-hook integration — the detector says force the
narrower boundary. ⚠️ *Sunk Cost (candidate, N/A):* no prior investment pressures
either way. 4a is the boundary-respecting call.

### D-S5-5 — Module placement / decomposition (`verify/marker.ts` vs fold into `engine/attestation.ts`)

**Framework used:** Pros-Cons-Fixes, anchored on SRP + the S4 idiom-mapping
precedent.

**The precise question:** does the HMAC marker live in a new
`pi-package/src/verify/marker.ts` (mirroring the Python `src/gleipnir/verify/`
module name), or folded into the existing `engine/attestation.ts`?

**Analysis (SRP + precedent):**
- `attestation.ts`'s OWN header states its single responsibility is *"the
  attestation VALUE contract, and nothing else… One reason to change: the
  attestation shape."* Folding HMAC minting/validation + key-loading + canonical
  signing into it gives it a SECOND reason to change (the crypto construction)
  — a direct SRP violation the S4 module explicitly guarded against.
- The Python oracle keeps `verify/marker.py` a SEPARATE module from the engine's
  attestation types; `bridge.py` is likewise its own module importing
  `verify.marker`'s primitives. The pi-package's own S4 layering (separate
  `state.ts`/`transitions.ts`/`engine.ts`/`attestation.ts`/`allowTable.ts`/
  `judges.ts`/`router.ts`) is a one-module-one-reason precedent.
- The proven opencode reference keeps the marker logic in a dedicated file
  (`sequence-gate.ts`'s `validateMarker`/`canonicalSigningInput`), not inside an
  attestation value type.

**Options:**
- **Option 5a — new `pi-package/src/verify/marker.ts`** (mirror the Python
  module name + directory), exporting `mintState`/`validateState`/`loadKey`/
  `canonicalSigningInput` + a `StateMarker` type. `attestation.ts` stays the
  pure VALUE contract; if a binding is needed, it imports from `verify/`.
- **Option 5b — fold into `engine/attestation.ts`.**
- **Option 5c — `verify/marker.ts` for the primitive PLUS a thin
  `engine/attestation.ts` extension** that binds a validated marker to the
  `Attestation` value (only if D-S5-1/D-S5-4 require an explicit binding beyond
  what `attempt_gate` already does).

**Recommended (D-S5-5): Option 5a — new `pi-package/src/verify/marker.ts`,
mirroring the Python `verify/` module name, holding the HMAC primitive
(`StateMarker` type, `mintState`/`validateState`/`loadKey`/`canonicalSigningInput`,
`node:crypto`). `attestation.ts` remains the pure VALUE contract (its stated
single responsibility), importing from `verify/` only if an explicit binding
seam is needed.** This honours SRP (the very SRP `attestation.ts` documents),
mirrors both the Python module layout and the pi-package's own S4 decomposition,
and matches the proven reference's separation. **Operator confirms** (recommended:
5a). The mirror-name choice (`verify/marker.ts`) also gives the idiom-mapping
table a clean Python→TS module correspondence — the same auditability discipline
S4 used.

**Bias check:** None fires decisively. (⚠️ *IKEA Effect* candidate — "our S4
layering is beloved" — noted, but the recommendation rests on the documented SRP
and the Python precedent, not attachment.)

### D-S5-6 — Test-port manifest (which Python test files port; is the golden-vector test its own class?)

**Framework used:** Pros-Cons-Fixes (a scoping decision keyed on D-S5-1).

**The Python test files that exist** (found this session):
- `tests/test_bridge.py` — `StateMarker` unit tests (roundtrip, forge-without-
  key fails, wrong-key fails, mac-lifted-onto-different-state fails,
  agent-added/removed fails, stale/future/wrong-version fails, malformed JSON
  raises, key fail-closed). **This is the unit oracle for Approach B's
  `StateMarker`.**
- `tests/test_marker.py` — `Marker` (tree-hash) unit tests. The unit oracle for
  the `verify/marker.py` primitive (only relevant if D-S5-1 = A or C).
- `tests/test_sequence_gate.mjs` — the **existing TS golden-vector cross-language
  test** for `StateMarker` (validates `golden_marker.json`, rejects tampered,
  rejects wrong key, freshness, future-dated, `isDelegationAllowed`). **This is
  the direct template for S5's golden-vector test class**, already in TS.
- `tests/test_armed_run_dogfood.py` (Python side) + the dogfood block in
  `test_sequence_gate.mjs` — the `dogfood_bridge.json` live-mint byte-parity
  cross-language handshake.

**Options:**
- **Option 6a (recommended if D-S5-1 = B) — port `test_bridge.py` as the
  `StateMarker` unit suite (adapted to `node --test`), PLUS a DISTINCT
  golden-vector cross-language test class** (`test/marker.test.ts` golden block)
  that loads the committed `tests/fixtures/golden_marker*.json` + `golden_key.bin`
  and asserts byte-for-byte validate/reject — modelled directly on
  `test_sequence_gate.mjs`. The golden-vector class is NOT the same as the unit
  suite: the unit suite proves the *logic* (forge/wrong-key/stale refusals) with
  locally-minted markers; the golden class proves *cross-language byte-parity*
  against Python-minted committed fixtures. Keeping them distinct mirrors the
  Python/opencode split (`test_bridge.py` unit vs `test_sequence_gate.mjs`
  golden) and makes a byte-drift failure diagnosable separately from a logic bug.
- **Option 6b — one combined test file** mixing unit + golden assertions.
- **Option 6c (if D-S5-1 = C) — 6a PLUS port `test_marker.py`** as a separate
  tree-hash `Marker` unit suite.

**Recommended (D-S5-6): Option 6a — port `test_bridge.py`'s assertions as the
`StateMarker` unit suite in `pi-package/test/marker.test.ts`, AND add a DISTINCT
golden-vector cross-language test class (in the same or a sibling file) that
reuses the committed `tests/fixtures/golden_marker*.json` + `golden_key.bin`,
modelled on the proven `test_sequence_gate.mjs`. The golden-vector test IS a
separate concern from the ported unit tests and should be a clearly-labelled
distinct class/block.** This gives both the logic oracle (ported unit tests) and
the byte-parity oracle (golden vectors) the exit criterion names, and keeps a
cross-language drift failure diagnosable independently of a logic regression.
(If D-S5-1 converges to C, extend to 6c: add `test_marker.py`'s tree-hash suite.)
**Operator confirms** the split (recommended: yes — distinct golden class), vs a
single combined file (6b). **Fixture reuse note to flag:** S5 can reuse the
existing committed `tests/fixtures/golden_*` files directly (the pi-package test
can read them via a relative path, as `test_sequence_gate.mjs` does), OR copy
them under `pi-package/test/fixtures/`; reuse-in-place is recommended (single
source of truth for the golden vectors — a copy could drift).

### Bias warnings summary (across all six)

- ⚠️ **Scope Creep** (D-S5-1 C-vs-B, D-S5-3, D-S5-4): surfaced three times — each
  recommendation forces the narrower boundary (StateMarker-only over both;
  brand-check coupled not free-floating; primitive-only over full wiring).
- ⚠️ **Bandwagon** (D-S5-2, ruled out): the `node:crypto` choice rests on the
  recorded trust-surface decision + a passing precedent, not popularity.
- ⚠️ **IKEA Effect** (mild, D-S5-5): the S4 layering is "ours"; the SRP argument
  is independent of attachment. Noted, not decisive.
- ⚠️ **Availability** (checked, ruled out, D-S5-1): the "byte-parity already
  proven" evidence is a committed passing test (`test_sequence_gate.mjs`), not a
  vivid recent memory — it is base-rate evidence, legitimately decisive.
- No other detectors triggered.

## Selected Approach

**CONVERGED by the operator (via the orchestrator's `question` tool;
operator-via-orchestrator, L-C6-legitimate — not self-attested). Five choices
matched the brainstorm recommendation; D-S5-4 DIVERGED to the wider scope.**
These are the decided choices `gleipnir-plan` plans from:

- **D-S5-1: CONVERGED → Option B (StateMarker only).** MATCHES recommendation.
  Port `bridge.py`'s `StateMarker` construction (`mintState`/`validateState`/
  `loadKey`/`canonicalSigningInput`, sha256, `\x1f`-field / `\x1e`-agent
  separators, sorted agents); reproduce `golden_marker*.json` byte-for-byte. The
  tree-hash `Marker` (`verify/marker.py`) is DEFERRED — no in-process pi consumer
  exists (building it now would be building ahead of need). ASSUMPTION-3 resolved:
  byte-for-byte reproduction, NO re-specification.
- **D-S5-2: CONVERGED → Node built-in `node:crypto`.** MATCHES recommendation.
  `createHmac("sha256", key).update(input,"utf8").digest("hex")` +
  `timingSafeEqual` (with the equal-length guard preserved). NO npm HMAC
  dependency — honours the stdlib-only-core constraint (`runtime-and-deps.md`)
  and matches the proven `sequence-gate.ts` reference.
- **D-S5-4: CONVERGED → Option 4b (primitive + FULL signed-persistence wiring
  NOW). ⚠️ DIVERGES from the brainstorm recommendation (4a, primitive-only).**
  The operator explicitly chose the WIDER scope: S5 also wires the full
  signed-persistence lifecycle in this session — mint-on-transition, persist over
  `pi.appendEntry`, and rehydrate/validate on `session_before_compact` /
  `session_start(resume)`. **Recorded consequences (per the operator):**
  1. **S5's scope is now larger than the build-order's original framing** ("S5 =
     primitive only; S8 wires persistence"). `gleipnir-plan` MUST scope the S5
     plan to this widened surface — the primitive is no longer the whole of S5.
  2. **The build-order's S5→S8 dependency-graph framing must be ANNOTATED, not
     silently contradicted.** The build-order (Tier-0, `pi-dev-replatform-build-order.md`)
     currently associates persistence-wiring/lifecycle integration with S8's
     bus/ledger slice; the operator's 4b choice moves that wiring EARLIER into S5.
     This brief records the move; the build-order annotation itself is a Tier-0
     edit for the plan/orchestrator to enact (this brainstorm does not edit the
     build-order). The S8 slice's scope correspondingly shrinks (it no longer
     owns the engine-position persistence wiring; it retains bus/ledger/observer
     + attested events).
  3. **A NEW open-question-shaped risk surfaces from the widened scope** — the
     reachability/documentation status of the two lifecycle hooks
     `session_before_compact` and `session_start(resume)` in the pi SDK is NOT
     re-verified against primary source this session (see the "Newly-surfaced
     risk" flag below). This is the Open-Q3-shaped pattern (a primitive the
     wiring depends on whose SDK surface is unconfirmed).
- **D-S5-3: CONVERGED → Option 3b (couple to D-S5-4) → because D-S5-4 = 4b, the
  `resumeAt` raw-string brand-check hardening is NOW IN SCOPE for S5** (bundled
  with the persistence wiring). Rationale (the brainstorm's own coupling logic):
  a signed `StateMarker` feeding an *unvalidated raw-string* `resumeAt` at the
  rehydration entry would be a real hole — so once S5 wires the signed
  rehydration path, the brand-check must land in the same slice. Mechanism:
  reject a raw `state` argument that is not a `PipelineState` set member at
  `resumeAt` entry (mirroring the Python oracle's `isinstance` refusal), closing
  the operator-acknowledged S4 accepted-consequence (S4 addendum in
  `decisions/pi-replatform-open-q1.md`; idiom-table row 15 in
  `pi-dev-replatform-s4.md`).
- **D-S5-5: CONVERGED → Option 5a (new `pi-package/src/verify/marker.ts`).**
  MATCHES recommendation. Mirror the Python `verify/` module name; hold the HMAC
  primitive there. `engine/attestation.ts` stays the pure VALUE contract (its
  documented single responsibility), importing from `verify/` only for the
  additive binding seam. Honours the SRP `attestation.ts` explicitly guards.
- **D-S5-6: CONVERGED → Option 6a (ported unit suite + DISTINCT golden-vector
  class).** MATCHES recommendation. Port `test_bridge.py`'s assertions as the
  `StateMarker` unit suite in `pi-package/test/marker.test.ts`; add a DISTINCT
  golden-vector cross-language test class reusing the committed
  `tests/fixtures/golden_marker*.json` + `golden_key.bin` IN PLACE (single source
  of truth — no copy that could drift), modelled on `test_sequence_gate.mjs`.
  Unit suite proves logic with locally-minted markers; golden class proves
  cross-language byte-parity against Python-minted fixtures — kept separate so a
  byte-drift failure is diagnosable independently of a logic regression. **Scope
  note under 4b:** the persistence-wiring and `resumeAt` brand-check (now
  in-scope) need their OWN tests beyond the 6a marker manifest — see the
  converged scope summary.

## Newly-surfaced risk from the 4b widened scope (for `gleipnir-plan` ATLAS Architect/Trace)

**⚠️ Open-Q3-shaped risk: the pi SDK surface for `session_before_compact` and
`session_start(resume)` is NOT re-verified against primary source.** The 4b
divergence pulls lifecycle-hook wiring into S5, which depends on these two hooks
being reachable and behaving as the wiring assumes. Checking the build-order's
own primitive-verification table (`pi-dev-replatform-build-order.md` L20-42):

- `pi.appendEntry()` (the persist primitive) — sourced to `docs/extensions.md`
  (documented; **lower** risk).
- `session_start` (startup/new/**resume**/fork) + `session_shutdown` +
  `agent_start/end` — sourced to `docs/sdk.md`, `06-extensions.ts` (documented;
  **lower** risk, though the *resume* sub-behaviour's exact payload/rebind
  semantics for a persisted engine singleton are not proven).
- `session_before_compact` / `session_compact` — sourced explicitly to **"brief
  Explore (table row 6)"**, i.e. the *brief's* summary, **NOT** re-verified
  hands-on against primary source this session (unlike the rows attributed to
  `docs/sdk.md`/examples). This is the **highest-risk** of the three: the
  compaction-hook surface is the least-confirmed primitive the 4b wiring now
  depends on.

**Why this is Open-Q3-shaped:** exactly like Open-Q3 (MCP-broker reachability
from a pi extension — surveyed SDK exports showed no `mcp:` client config, so the
step was BLOCKED pending confirmation), the 4b persistence wiring now depends on
a primitive (`session_before_compact`) whose SDK surface is **unconfirmed by
primary source**. If that hook does not exist / is not reachable / does not fire
where the wiring needs it, the compaction-survival half of 4b cannot be built as
scoped.

**Recommended handling for `gleipnir-plan` (ATLAS Architect/Trace):**
1. **Trace step: re-verify hands-on** (against the earendil-works/pi source +
   `pi.dev/docs`, per the L-C36 read-directly discipline) that
   `session_before_compact` and `session_start(resume)` exist, are subscribable
   from an extension, and expose the payload/rebind hooks the persistence wiring
   needs — BEFORE committing the plan to the full 4b wiring.
2. **If `session_before_compact` is confirmed** → plan the full 4b wiring.
3. **If it is UNCONFIRMED / unreachable** → this is a genuine blocking
   open-question (Open-Q5-shaped) that must route back to the operator: the 4b
   divergence may need to fall back to a bounded subset (e.g. mint-on-transition
   + `pi.appendEntry` + `session_start(resume)` rehydration WITHOUT the
   compaction hook), with compaction-survival deferred. `gleipnir-plan` does NOT
   silently narrow the operator's converged 4b — it surfaces the reachability
   finding back to the orchestrator/operator, mirroring how Open-Q3 blocked S6.
4. **Additionally flag for Architect judgment:** whether pulling lifecycle-hook
   integration into S5 disturbs the D-S4-6 boundary (S5 must still not modify the
   five S1–S3 modules; the mint-on-transition wiring touches the engine's
   transition path in `engine.ts`, which is an S4 module — the plan must state
   how mint-on-transition attaches ADDITIVELY, e.g. at the driver/caller edge,
   not by rewriting `Engine.step`/`attemptGate` internals).

## Open Questions (for `gleipnir-plan`, AFTER convergence)

- **Exact `verify/marker.ts` export surface** (once D-S5-1/D-S5-5 converge):
  `StateMarker` type, `mintState`, `validateState`, `loadKey`,
  `canonicalSigningInput`, constants (`STATE_MARKER_VERSION=1`, `FIELD_SEP="\x1f"`,
  `AGENT_SEP="\x1e"`, `DEFAULT_MAX_AGE_SECONDS=3600`, `DIGEST="sha256"`) — mirror
  the proven `sequence-gate.ts` names or the Python `bridge.py` names; the plan's
  idiom-mapping table (S4 precedent) records each Python→TS surface choice.
- **`Attestation` binding shape** (if D-S5-1/D-S5-4 require an explicit link):
  does a validated `StateMarker` feed/construct the `Attestation` the S4
  `attempt_gate` consumes, or do they stay parallel (marker = persisted position
  integrity; `Attestation` = the GATE evidence value)? The plan must state the
  seam as additive — no change to `attemptGate`'s refusal logic.
- **Golden-fixture access path** from `pi-package/test/` (reuse-in-place vs copy)
  — recommended reuse-in-place; the plan pins the exact relative path.
- **If D-S5-4 = 4a (deferred wiring):** the plan names the persistence-wiring
  seam explicitly (which later step: S8 vs S5.5) so it is not lost, mirroring how
  D-S4-2 named this very seam.
- **If D-S5-3 couples in:** the `resumeAt` brand-check test (raw-string rejected;
  `PipelineState`-member accepted) and its exact guard mechanism.
- **Idiom-mapping table:** required as the falsifiable Design Intent (S4
  precedent), one row per Python→TS surface deviation in the marker port.

## Scope Sketch

| Area | Files/Modules Likely Affected |
|------|-------------------------------|
| HMAC marker primitive (new) | `pi-package/src/verify/marker.ts` — `StateMarker` type, `mintState`/`validateState`/`loadKey`/`canonicalSigningInput`, `node:crypto` (`createHmac`/`timingSafeEqual`), constants mirrored from `bridge.py` |
| Attestation binding (additive, IF needed) | thin extension so a validated `StateMarker` relates to `engine/attestation.ts`'s `Attestation` — NO change to `attemptGate` refusal logic |
| `resumeAt` brand-check (D-S5-3 → **IN SCOPE** via 4b) | `pi-package/src/engine/state.ts`/`engine.ts` — reject raw-string `state` at `resumeAt` (not a `PipelineState` member → throw), mirroring Python `isinstance`; bundled with persistence wiring |
| Signed-persistence wiring (D-S5-4 = 4b → **IN SCOPE NOW**) | mint-on-transition (additive, at driver/caller edge — NOT rewriting `Engine.step`/`attemptGate`) + persist over `pi.appendEntry` + rehydrate/validate on `session_before_compact` / `session_start(resume)`. ⚠️ compaction-hook surface UNCONFIRMED (see Newly-surfaced risk) |
| Unit tests (ported oracle) | `pi-package/test/marker.test.ts` — `test_bridge.py` assertions adapted to `node --test` |
| Golden-vector cross-language test (DISTINCT class) | reuse committed `tests/fixtures/golden_marker*.json` + `golden_key.bin`; modelled on `tests/test_sequence_gate.mjs`; byte-for-byte validate/reject |
| Test harness | `node --experimental-strip-types --test` under `bin/gleipnir-sandbox --profile pi` (`--network=none`; HMAC/key tests are pure/offline) |

## Design Principles (Gate 1 — brainstorm artifact)

**Routing:** this artifact is **prose-only** (`P = { this .md file }`,
`P ∩ X = ∅`). Per `plan-format.md` case (iii), SOLID/DRY/SRP are
**`N/A — no executable artifact`**.

**Design Intent (specific, falsifiable):** *This brief must surface every S5
material decision the delegation named (ASSUMPTION-3 reproduction, node crypto,
resumeAt brand-check scope, signed-persistence scope, module placement,
test-port manifest) as an explicit D-S5-N with options + framework +
recommendation, deciding NONE, AND must ground the ASSUMPTION-3 analysis in the
oracle's actual algorithm (not a guess) — specifically identifying which
construct the golden fixtures pin.* Falsifiable by: any named decision missing or
silently decided; or an ASSUMPTION-3 treatment that did not read `marker.py`'s
and the fixtures' actual bytes (it did — the fixtures are `StateMarker`, and
byte-parity is already proven in `sequence-gate.ts`).

## Decision Frameworks Note
Frameworks applied: Reversibility Filter + Weighted Decision Matrix (D-S5-1),
Reversibility Filter (D-S5-2), Pros-Cons-Fixes (D-S5-3, D-S5-5, D-S5-6),
Second-Order Thinking (D-S5-4). Bias detectors run across all six; Scope Creep
(×3), Bandwagon, a mild IKEA Effect, and a ruled-out Availability check surfaced
and are addressed. Per the K-3 binding, these analyses are the INPUT to the
operator's convergence, not the decision.
