# Decision: implementation language and dependency policy

**Status:** decided (this session). Durable decision record. Covers Gleipnir's
runtime-agnostic **enforcement core** (the G-3.1 verifier, the G-5 engine, the
future G-4 bus/ledger, the memory-write pipeline). Does **not** cover the
opencode plugin/hook layer, which is TypeScript/Bun by virtue of the runtime.

## Language: Python for the enforcement core

**Decision:** the enforcement core is written in **Python** (>=3.11).

**Rationale (checked, not assumed).**
- Python is the most heavily represented language in code-generation training
  corpora; the canonical code-gen benchmarks (HumanEval, MBPP and their
  descendants) are Python-native, and the open-source agentic/ML tooling
  ecosystem is Python-dominant. LLM code-generation reliability is therefore
  generally highest in Python.
- This serves the framework **goal** directly: higher per-step reliability from
  the implementer model means fewer failed steps, fewer retries, fewer tokens.
  Under Axiom 1 (the test is the arbiter) the model still isn't trusted, but a
  higher first-pass rate is cheaper regardless.
- It matches what already exists: the G-3.1 verifier (`src/gleipnir/verify/`)
  is Python stdlib.

**Scope boundary.** The opencode hooks (S-1) are TS/Bun; that is a runtime
fact, not reopened here. Enforcement core = Python; runtime hooks = TS. A future
pi.dev/pinion port is a contract-conformance exercise (S-1), not a rewrite.

## Dependencies: stdlib-only for the enforcement core

**Decision:** the enforcement core uses **only the Python standard library**.
Dev-only tooling (test runner) is permitted but must be **declared and pinned**.

**Rationale.** Every runtime dependency is something that must live *inside*
the S-2 trusted boundary (the read-only mount / trust domain). Fewer
dependencies = smaller trusted surface to audit = directly serves G-1/G-2.
Stdlib-only is not habit; it is trust-surface minimisation. `hashlib`, `hmac`,
`json`, `dataclasses`, `enum`, `typing`, `argparse`, `subprocess` cover the
core's needs (G-3.1 already proves this).

**Policy.**
- Enforcement-core runtime imports: **stdlib only.** A new third-party runtime
  dependency requires a recorded justification here and enters the S-2 trusted
  surface explicitly — it is a decision, not a convenience.
- Dev/test tooling (not shipped, not in the trusted runtime surface): allowed,
  declared under `[project.optional-dependencies]`, pinned.

## Amendment — the broker/integration layer is NOT enforcement core

**Status:** decided (broker-MCP session). Plan of record:
`../plans/broker-mcp.md`; brief: `../plans/broker-mcp-brainstorm.md` (Option B).

The stdlib-only rule scopes to the **enforcement core** (G-3.1 verifier, G-5
engine, G-4 bus/ledger, memory pipeline) and already excludes the TS hook layer.
This amendment names a third category:

- **Broker / integration layer** (`src/gleipnir/broker/**`) — the git and PM
  broker MCP servers (spec T-2 / G-2 single-holder, E-1). Not enforcement core;
  they hold no G-3/G-5/G-4/memory logic. They MAY carry **declared, justified**
  runtime deps, per the policy above.

**Each broker is its own independently-versioned component (operator decision).**
Every broker is a distinct installable component with its OWN `pyproject.toml` +
VERSION (`src/gleipnir/broker/{git,pm}/`), AETOS mono-repo style. Each manifest
declares a **compatibility range/matrix** for its deps — NOT a single frozen
pin, NOT tied to the framework version or the other broker. Decoupled; each
re-pins independently.

**Recorded dependency — the MCP SDK (FastMCP), version owned per-component:**
opencode speaks MCP over stdio; the brokers are stdio MCP servers. Writing the
JSON-RPC handshake by hand was considered and rejected in favour of the SDK; the
brokers run as separate stdio subprocesses, so the dep lives at the broker
boundary, not in the enforcement core. **VERSION CAVEAT (verified):** naive
`mcp>=1.0.0` resolves to `mcp 2.0.0`, which REMOVED `mcp.server.fastmcp`
(FastMCP split out). The FastMCP API lives in `mcp` 1.x (AETOS runs 1.27.1; we
verified 1.29.0) OR the standalone `fastmcp` 3.x. Each broker manifest MUST
declare a **bounded** range containing FastMCP — `mcp>=1.0,<2` — never
open-ended `>=1.0.0`.

**REJECTED:** `python-dotenv` — opencode injects env via the MCP `environment:{}`
block; `os.environ` suffices. No `.env` loader needed.

**Boundary drawn sharply.** "Enforcement core = stdlib-only" is unchanged. Only
`src/gleipnir/broker/**` may import the MCP SDK; every future dep still needs its
own recorded justification. A broker-scoped conformance test
(`tests/test_broker_stdlib_only.py`) asserts `mcp` never leaks into the core and,
within `broker/`, is imported only by the `mcp_server.py` modules.

## Accrued-tooling reconciliation (this session)

- **pytest** — the test runner. Was installed ad hoc into `.venv`. Now declared
  as a dev-only optional dependency in `pyproject.toml`. Not a runtime dep; not
  in the trusted surface.
- **pyyaml** — was installed transiently for a one-off agent-frontmatter
  validation during a prior turn. It is **not imported anywhere in the source
  or tests**, so it is *not* a project dependency and is **not** declared.
  Nothing to remove from code; simply not adopted.

## Conformance

- A check that the enforcement core imports only stdlib modules is a candidate
  C-3 meta-test (tool-contract stability / consistency): grep/AST the core for
  non-stdlib top-level imports; any hit fails unless recorded here.
