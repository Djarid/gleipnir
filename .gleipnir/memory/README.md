# memory/ — Tier 2: USER_REVIEWED (T-1 concept graph)

**Trust tier:** 2 (USER_REVIEWED). **Authority:** supplies facts and concept
knowledge; **never** tool permissions or safety policy.

Long-term cross-session memory: the OKF-style concept graph (T-1) — one
markdown file per concept, markdown-link relationships, `index.md` as the
traversal entry point.

## Write rule (G-6)

This directory is **not** written by an agent editing files directly. Entries
arrive only through the **deterministic review-gated memory-write pipeline**
(see `../decisions/gleipnir-layout-and-memory-model.md`):

1. an agent *proposes* an entry;
2. the pipeline classifies source + trust tier, validates schema/destination;
3. a human-readable diff is required and approval is bound to that exact diff;
4. an audit event with provenance is appended to the G-4 bus;
5. persistence probes run.

Each approved file carries a keyed integrity digest in `../keys/` (the G-3.1
mechanism); S-3 preflight verifies it at session start. Content that does not
match its approved digest is quarantined (fail-closed).

**Status:** authored, not yet closed. The pipeline, digests and preflight are
later build steps; until then this is the contract, not an enforced boundary.
