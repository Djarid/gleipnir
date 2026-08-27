/**
 * roleTable.test.ts — the deny-by-default arbiter for the S2 8-role table
 * (plan Assemble step 2; AC-16, AC-17, AC-18, AC-19).
 *
 * Pure, pi-SDK-free unit tests over `roleTable.ts`'s data + `canUse` lookup.
 * These are the exit-criterion core: every role expressed, deny-by-default per
 * role, the G-2 single-broker-holder invariant, SDK vocabulary fidelity, and
 * the frozen-table integrity property.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  canUse,
  GIT_BROKER_TOOLS,
  PM_BROKER_TOOLS,
  ROLE_ALLOW_SETS,
  SDK_BASE_TOOL_NAMES,
  UNIVERSALLY_DENIED,
  unionAllowSet,
  type RoleName,
} from "../src/roleTable.ts";

const ALL_ROLES: RoleName[] = Object.keys(ROLE_ALLOW_SETS);

const EXPECTED_ROLES = [
  "orchestrator",
  "gleipnir-brainstorm",
  "gleipnir-plan",
  "gleipnir-code",
  "quality-reviewer",
  "git-ops",
  "project-mgr",
  "notify",
];

test("success criterion 1: the table contains exactly the 8 roster roles", () => {
  assert.deepEqual(
    new Set(ALL_ROLES),
    new Set(EXPECTED_ROLES),
    "ROLE_ALLOW_SETS must contain exactly the 8 roster roles",
  );
});

test("success criterion 1: each role has a typed three-partition allow-set", () => {
  for (const role of ALL_ROLES) {
    const entry = ROLE_ALLOW_SETS[role];
    assert.ok(Array.isArray(entry.baseTools), `${role}.baseTools must be an array`);
    assert.ok(Array.isArray(entry.customTools), `${role}.customTools must be an array`);
    assert.ok(Array.isArray(entry.brokerTools), `${role}.brokerTools must be an array`);
  }
});

test("AC-16: deny-by-default holds for every one of the 8 roles (aggregate)", () => {
  for (const role of ALL_ROLES) {
    const union = unionAllowSet(role);
    // Every tool NOT in the role's union allow-set resolves to false.
    assert.equal(
      canUse(role, UNIVERSALLY_DENIED),
      false,
      `${role} must deny an unlisted tool (deny-by-default)`,
    );
    // And every tool that IS in the union resolves to true (positive control,
    // so the deny assertion above isn't vacuously passing on a blanket-deny).
    for (const tool of union) {
      assert.equal(
        canUse(role, tool),
        true,
        `${role} must allow its declared tool "${tool}"`,
      );
    }
  }
});

test("AC-16: unknown role and unset role both deny (deny-by-default base cases)", () => {
  assert.equal(canUse("not-a-role", "read"), false, "unknown role must deny");
  assert.equal(canUse(undefined, "read"), false, "unset role must deny");
  assert.equal(canUse("", "read"), false, "empty role must deny");
});

test("AC-17: git-ops is the sole broker (git) holder; every other role's brokerTools is empty", () => {
  const rolesWithBroker = ALL_ROLES.filter(
    (r) => ROLE_ALLOW_SETS[r].brokerTools.length > 0,
  );
  assert.deepEqual(
    rolesWithBroker,
    ["git-ops"],
    "exactly one role (git-ops) may have a non-empty brokerTools",
  );
  assert.deepEqual(
    [...ROLE_ALLOW_SETS["git-ops"].brokerTools],
    [...GIT_BROKER_TOOLS],
    "git-ops.brokerTools must carry exactly the 4 concrete git broker tool names (S6, D-S6-1b)",
  );
});

test("AC-17/AC-G2 (S6): each of the 4 concrete git broker tool names is granted to git-ops and denied to every other role (G-2)", () => {
  assert.equal(
    GIT_BROKER_TOOLS.length,
    4,
    "S6 registers exactly 4 concrete git broker tool names",
  );
  for (const gitTool of GIT_BROKER_TOOLS) {
    assert.equal(
      canUse("git-ops", gitTool),
      true,
      `git-ops must be able to use the concrete git broker tool "${gitTool}"`,
    );
    for (const role of ALL_ROLES) {
      if (role === "git-ops") continue;
      assert.equal(
        canUse(role, gitTool),
        false,
        `${role} must NOT be able to use the concrete git broker tool "${gitTool}" (G-2 sole-holder)`,
      );
    }
  }
});

test("AC-17 (P2) / AC-G2 (S6): the 4 concrete pm tool names live in project-mgr.customTools, uniquely, and NOT in any brokerTools", () => {
  assert.equal(
    PM_BROKER_TOOLS.length,
    4,
    "S6 registers exactly 4 concrete pm broker tool names",
  );
  for (const pmTool of PM_BROKER_TOOLS) {
    // project-mgr uniquely holds each concrete pm tool name.
    assert.equal(canUse("project-mgr", pmTool), true, `project-mgr holds "${pmTool}"`);
    for (const role of ALL_ROLES) {
      if (role === "project-mgr") continue;
      assert.equal(canUse(role, pmTool), false, `${role} must not hold "${pmTool}"`);
    }
    // pm must NOT dilute brokerTools (which is the git-only G-2 partition).
    for (const role of ALL_ROLES) {
      assert.ok(
        !ROLE_ALLOW_SETS[role].brokerTools.includes(pmTool),
        `${role}.brokerTools must not contain the pm tool "${pmTool}" (P2: git-only)`,
      );
    }
  }
});

test("AC-G2-3 (S6): canUse's function body is unaffected by the DATA-only edit — a role's union set still fails closed on any name outside its declared partitions", () => {
  // Cross-namespace denial: git-ops (the git sole-holder) must NOT be able
  // to use ANY pm tool name, and project-mgr (the pm sole-holder) must NOT
  // be able to use ANY git tool name — the two namespaces stay disjoint
  // under the SAME unchanged canUse matching logic.
  for (const pmTool of PM_BROKER_TOOLS) {
    assert.equal(canUse("git-ops", pmTool), false, `git-ops must not hold "${pmTool}"`);
  }
  for (const gitTool of GIT_BROKER_TOOLS) {
    assert.equal(canUse("project-mgr", gitTool), false, `project-mgr must not hold "${gitTool}"`);
  }
});

test("AC-18: base-tool vocabulary matches the SDK ToolName union; no read_file/write_file/powershell", () => {
  for (const role of ALL_ROLES) {
    for (const base of ROLE_ALLOW_SETS[role].baseTools) {
      assert.ok(
        SDK_BASE_TOOL_NAMES.has(base),
        `${role}.baseTools contains "${base}" which is not a real SDK base ToolName`,
      );
    }
  }
  // Explicit negative check on the retired S1 vocabulary + the README's error.
  const flat = JSON.stringify(ROLE_ALLOW_SETS);
  for (const bad of ["read_file", "write_file", "powershell"]) {
    assert.ok(!flat.includes(bad), `the table must not contain the stale name "${bad}"`);
  }
});

test("AC-21: D1 coarse-presence fix — present-but-scoped capabilities appear in baseTools with bounds recorded; genuinely-denied ones stay absent", () => {
  // Present-but-scoped (D1-corrected): the coarse answer to "can this role
  // EVER call this tool?" is yes, even though a fine-grained path/arg
  // restriction applies. The restriction must be recorded in `bounds`
  // (metadata, unenforced by S2), never silently dropped.
  const presentButScoped: Array<[RoleName, string]> = [
    ["gleipnir-brainstorm", "edit"],
    ["gleipnir-plan", "edit"],
    ["gleipnir-code", "bash"],
    ["quality-reviewer", "bash"],
    ["git-ops", "bash"],
  ];
  for (const [role, tool] of presentButScoped) {
    assert.equal(
      canUse(role, tool),
      true,
      `${role} must be allowed to call "${tool}" (D1 coarse-presence fix: present-but-scoped, not dropped)`,
    );
    const bounds = ROLE_ALLOW_SETS[role].bounds;
    assert.ok(
      bounds && bounds.length > 0,
      `${role}.bounds must be non-empty — the fine-grained restriction on "${tool}" must be recorded as metadata, not silently dropped`,
    );
  }

  // Genuinely-denied (absent, not scoped): the coarse answer is legitimately
  // "no" — these must stay false after the D1 fix.
  const genuinelyDenied: Array<[RoleName, string]> = [
    ["orchestrator", "edit"],
    ["orchestrator", "bash"],
    ["project-mgr", "bash"],
    ["notify", "bash"],
  ];
  for (const [role, tool] of genuinelyDenied) {
    assert.equal(
      canUse(role, tool),
      false,
      `${role} must still deny "${tool}" (genuinely absent from its frontmatter, not scoped)`,
    );
  }
});

test("AC-19: the table (including nested partitions) is frozen — no runtime widening", () => {
  assert.ok(Object.isFrozen(ROLE_ALLOW_SETS), "the top-level table must be frozen");
  for (const role of ALL_ROLES) {
    const entry = ROLE_ALLOW_SETS[role];
    assert.ok(Object.isFrozen(entry), `${role}'s allow-set object must be frozen`);
    assert.ok(Object.isFrozen(entry.baseTools), `${role}.baseTools must be frozen`);
    assert.ok(Object.isFrozen(entry.customTools), `${role}.customTools must be frozen`);
    assert.ok(Object.isFrozen(entry.brokerTools), `${role}.brokerTools must be frozen`);
    // A push into a frozen array throws in strict mode (test modules are ESM =
    // strict), proving the enforcement table cannot be widened at runtime.
    assert.throws(
      () => (entry.baseTools as string[]).push("bash"),
      TypeError,
      `${role}.baseTools must reject a runtime push`,
    );
  }
});
