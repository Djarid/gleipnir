# var/ — Tier 0: TEMPORARY (scratch)

**Trust tier:** 0 (TEMPORARY). **Authority:** none. **Writer:** any bounded
roster agent may use `var/tmp/` for scratch/intermediate files.

Disposable working space. Nothing here has authority over planning, tool use,
or policy, and nothing here is expected to persist. Never store anything
durable in `var/`; promote durable outcomes to their proper tier
(`../decisions/` for rulings, the review-gated `../memory/` for facts).

Contents are gitignored except this README.

**Status:** active (no enforcement needed — Tier 0 is authority-free by
definition).
