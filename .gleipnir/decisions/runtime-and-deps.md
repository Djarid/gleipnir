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
