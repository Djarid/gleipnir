# keys/ — Tier 3: POLICY (verifier key + approved integrity digests)

**Trust tier:** 3 (POLICY). **Writer:** nobody at runtime — the verifier key is
provisioned out of band and lives under the **S-2 boundary**, readable only by
the verifier process. No agent, in-framework or otherwise, reads or writes this
directory at runtime.

Holds:
- the **G-3.1 HMAC verifier key** (never on the agent surface), and
- the **approved integrity digests** for Tier-3 policy files and approved
  Tier-2 memory files (the *Bad Memory* "approved digest stored outside the
  agent-writable workspace" requirement).

## How it is used (G-3.1 mechanism, applied to memory security — G-6)

- Minting/validating a digest requires the key; an agent cannot forge one.
- **S-3 preflight** verifies each protected file against its approved digest at
  session start (and high-impact tool calls check before acting). A mismatch is
  fail-closed: the file is quarantined and the session refuses to proceed over
  it.

## Do not commit secrets

The actual key is **never** committed. Under S-2 it is a mount/secret-store
artifact provisioned outside the repo. This directory in-repo holds only the
policy (this README) and, later, digest manifests that are safe to version
(they reveal nothing without the key). The repo `.gitignore` and the S-2 mount
keep key material out.

**Status:** authored, not yet closed. The key location becomes real with S-2;
the digest manifests + preflight verification are the G-3.1-applied-to-memory
build step.
