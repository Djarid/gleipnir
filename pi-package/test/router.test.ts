/**
 * router.test.ts — NEW mechanism tests for `router.ts` (no Python oracle;
 * plan §Stress-test "Router (`test/router.test.ts` — NEW, mechanism-not-
 * literals)"). Every test asserts the routing DECISION over representative
 * inputs, never the identity of the underlying literal set (D-S4-5 fix) —
 * so a later opencode->pi literal swap of `AXIS1_DISQUALIFIER_CONFIG` /
 * `AXIS2A_ENFORCEMENT_PATH_CONFIG` keeps this suite green. No test below
 * reads those config constants' contents; each only calls `routePlan` with
 * plain path/content inputs and checks the returned `RouteDecision`.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { RouteDecision, routePlan } from "../src/engine/router.ts";

// ---------------------------------------------------------------------------
// Axis-1 disqualifier `X` -> FULL_PIPELINE, regardless of how small/prose-
// heavy the rest of `P` is.
// ---------------------------------------------------------------------------

test("axis-1: a src/** path in P routes full pipeline", () => {
  const decision = routePlan({ paths: ["src/gleipnir/engine/__init__.py", "README.md"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a hooks/** path routes full pipeline", () => {
  const decision = routePlan({ paths: ["hooks/pre-commit"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a bin/** path routes full pipeline", () => {
  const decision = routePlan({ paths: ["bin/gleipnir-sandbox"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a .github/** path routes full pipeline", () => {
  const decision = routePlan({ paths: [".github/workflows/ci.yml"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a standalone *.yml path (outside .github) routes full pipeline", () => {
  const decision = routePlan({ paths: ["config/settings.yml"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a standalone *.yaml path routes full pipeline", () => {
  const decision = routePlan({ paths: ["config/settings.yaml"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a bare Makefile basename (any directory) routes full pipeline", () => {
  const decision = routePlan({ paths: ["tools/Makefile"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a Containerfile-prefixed basename routes full pipeline", () => {
  const decision = routePlan({ paths: ["Containerfile.node"] });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1: a *.sh/*.py/*.ts/*.rs/*.go file anywhere routes full pipeline", () => {
  for (const path of [
    "scripts/deploy.sh",
    "tools/generate.py",
    "pi-package/src/engine/state.ts",
    "crates/foo/lib.rs",
    "cmd/main.go",
  ]) {
    assert.equal(routePlan({ paths: [path] }), RouteDecision.FULL_PIPELINE, path);
  }
});

test("axis-1: shebang in added content routes full pipeline even with an otherwise-prose path set", () => {
  const decision = routePlan({
    paths: [".gleipnir/plans/some-plan.md"],
    addedLines: ["#!/usr/bin/env bash", "echo hi"],
  });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

test("axis-1 takes priority over an Axis-2(a) hit in the same P", () => {
  // A plan touching both an E-set file and a disqualifying src/** file is
  // still the full pipeline -- Axis-1 is checked first and is not merely
  // "the same as hardened."
  const decision = routePlan({
    paths: ["src/gleipnir/engine/__init__.py", ".gleipnir/agents/orchestrator.md"],
  });
  assert.equal(decision, RouteDecision.FULL_PIPELINE);
});

// ---------------------------------------------------------------------------
// Axis-2(a) enforcement-path `E` -> HARDENED (track-eligible, i.e. no Axis-1
// hit in P).
// ---------------------------------------------------------------------------

test("axis-2(a): a .gleipnir/agents/** path routes hardened", () => {
  const decision = routePlan({ paths: [".gleipnir/agents/orchestrator.md"] });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(a): .gleipnir/plugins/**, .gleipnir/sandbox/**, .gleipnir/policy/**, .gleipnir/keys/** all route hardened", () => {
  for (const path of [
    ".gleipnir/plugins/notes.md", // prose-shaped basename -- isolates the dir-prefix hit
    ".gleipnir/sandbox/notes.md",
    ".gleipnir/policy/notes.md",
    ".gleipnir/keys/README.md",
  ]) {
    assert.equal(routePlan({ paths: [path] }), RouteDecision.HARDENED, path);
  }
});

test("axis-2(a): stage-role-map.md itself routes hardened", () => {
  const decision = routePlan({ paths: [".gleipnir/stage-role-map.md"] });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(a): opencode.jsonc (root config) routes hardened", () => {
  const decision = routePlan({ paths: ["opencode.jsonc"] });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(a): a nested **/opencode.json routes hardened by basename", () => {
  const decision = routePlan({ paths: ["some/nested/opencode.json"] });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(a): the enumerated repo-root cross-cutting files route hardened", () => {
  for (const path of [".gitignore", ".envrc", "pyproject.toml", ".gitattributes", ".gitmodules"]) {
    assert.equal(routePlan({ paths: [path] }), RouteDecision.HARDENED, path);
  }
});

// ---------------------------------------------------------------------------
// Axis-2(b) grant/enforcement content pattern `G` -> HARDENED, isolated from
// any path signal (the touched paths are prose-only; only the CONTENT
// triggers the route).
// ---------------------------------------------------------------------------

test("axis-2(b): a YAML permission: block line routes hardened", () => {
  const decision = routePlan({
    paths: [".gleipnir/plans/some-plan.md"],
    addedLines: ["permission:", "  bash: deny"],
  });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(b): a YAML tools: block line routes hardened", () => {
  const decision = routePlan({
    paths: [".gleipnir/plans/some-plan.md"],
    addedLines: ["tools:", "  edit: true"],
  });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(b): a capability allow/deny line routes hardened", () => {
  for (const line of ["bash: deny", "edit: allow", "write: deny", "task: allow", "webfetch: deny"]) {
    const decision = routePlan({
      paths: [".gleipnir/plans/some-plan.md"],
      addedLines: [line],
    });
    assert.equal(decision, RouteDecision.HARDENED, line);
  }
});

test("axis-2(b): a JSON-quoted enforcement key routes hardened", () => {
  for (const key of [
    "permission",
    "tools",
    "enabled",
    "instructions",
    "default_agent",
    "subagent_depth",
    "mcp",
  ]) {
    const decision = routePlan({
      paths: ["docs/notes.md"],
      addedLines: [`  "${key}": true`],
    });
    assert.equal(decision, RouteDecision.HARDENED, key);
  }
});

test("axis-2(b): a keys/** digest line (64 lowercase hex) routes hardened", () => {
  const digest = "a".repeat(64);
  const decision = routePlan({
    paths: [".gleipnir/plans/some-plan.md"],
    addedLines: [`${digest} some-file.md`],
  });
  assert.equal(decision, RouteDecision.HARDENED);
});

test("axis-2(b): prose that merely mentions 'permission' without the enforcement shape does not route hardened", () => {
  const decision = routePlan({
    paths: [".gleipnir/plans/some-plan.md"],
    addedLines: ["We discussed permission and consent in the design review."],
  });
  assert.equal(decision, RouteDecision.LIGHT);
});

// ---------------------------------------------------------------------------
// Light path: prose-only P, no G-content match.
// ---------------------------------------------------------------------------

test("light: a prose-only P with no G-content match routes light", () => {
  const decision = routePlan({
    paths: [
      ".gleipnir/goals/manifest.md",
      ".gleipnir/decisions/some-decision.md",
      ".gleipnir/plans/some-plan.md",
      "README.md",
    ],
    addedLines: ["This is a plain prose change with no enforcement content."],
  });
  assert.equal(decision, RouteDecision.LIGHT);
});

test("light: an empty P with no added lines routes light", () => {
  const decision = routePlan({ paths: [] });
  assert.equal(decision, RouteDecision.LIGHT);
});

test("light: addedLines is optional -- omitting it entirely still resolves to light for a prose-only P", () => {
  const decision = routePlan({ paths: [".gleipnir/plans/some-plan.md"] });
  assert.equal(decision, RouteDecision.LIGHT);
});

// ---------------------------------------------------------------------------
// Literal-agnostic property (D-S4-5 fix): the tests above never assert the
// IDENTITY of AXIS1_DISQUALIFIER_CONFIG / AXIS2A_ENFORCEMENT_PATH_CONFIG --
// only the DECISION for representative inputs. This meta-test documents
// that the three decisions are mutually exclusive members of the same
// three-value RouteDecision vocabulary (a defence against a future config
// swap silently introducing a fourth ad-hoc decision string).
// ---------------------------------------------------------------------------

test("RouteDecision has exactly three members", () => {
  const names = new Set(Object.keys(RouteDecision));
  assert.deepEqual(names, new Set(["FULL_PIPELINE", "HARDENED", "LIGHT"]));
});
