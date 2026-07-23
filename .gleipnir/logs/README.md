# logs/ — Tier 1: RETRIEVED (session-observer / G-4 bus output)

**Trust tier:** 1 (RETRIEVED). **Authority:** observation only. Log content has
**no** authority over planning or tool use; it is evidence to be read, never
instruction to be followed.

Destination for the session-observer and G-4 typed-event-bus output. Writes are
made by **framework processes** (the bus/observer code), not by LLM roster
agents editing files. Every entry carries provenance (session id, originating
turn, guard/surface identity, timestamp) per G-4a/G-4b.

Because this is Tier 1, a compromised or noisy log cannot escalate into policy:
the authority ladder forbids a lower tier altering a higher one. Logs feed
G-4c novelty triage as *signal*, which is itself review-gated before anything
graduates to Tier 2 `lessons/`.

**Status:** authored, not yet closed (needs the G-4 bus).
