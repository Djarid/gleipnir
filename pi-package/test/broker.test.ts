/**
 * broker.test.ts — the correctness + G-2-reachability arbiter for the S6
 * broker extension (`.gleipnir/plans/pi-dev-replatform-s6.md`, Assemble step
 * 3b; AC-BROKER-1, AC-G2-1..3, AC-RELAY-1, AC-CRED-1, AC-CRED-2).
 *
 * Complements (does NOT duplicate) `roleTable.test.ts`'s AC-17/AC-G2-3 table
 * tests: those assert the DATA (`GIT_BROKER_TOOLS`/`PM_BROKER_TOOLS`
 * constants) resolve correctly through `canUse`. This file additionally
 * binds that to the REGISTERED tool objects the broker extensions actually
 * build (`buildGitBrokerTools()`/`buildPmBrokerTools()`), and to the
 * credential-isolation + relay-shape properties that are broker-module
 * concerns, not roleTable concerns.
 */

import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { readFileSync } from "node:fs";

import { canUse, ROLE_ALLOW_SETS, GIT_BROKER_TOOLS, PM_BROKER_TOOLS } from "../src/roleTable.ts";
import { buildGitBrokerTools, buildGitSpawnSpec } from "../src/broker/gitBroker.ts";
import { buildPmBrokerTools, buildPmSpawnSpec } from "../src/broker/pmBroker.ts";
import { relayToolCall, type SpawnSpec } from "../src/broker/mcpStdioClient.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const MOCK_BROKER_PATH = join(__dirname, "fixtures", "mock-broker.mjs");
const ALL_ROLES = Object.keys(ROLE_ALLOW_SETS);

// ---------------------------------------------------------------------------
// AC-BROKER-1: registration — the built tool objects' names EQUAL the
// concrete roleTable DATA rows exactly (never hand-duplicated literals that
// could drift).
// ---------------------------------------------------------------------------

test("AC-BROKER-1: buildGitBrokerTools() registers exactly the 4 GIT_BROKER_TOOLS names, in order", () => {
  const names = buildGitBrokerTools().map((tool) => tool.name);
  assert.deepEqual(names, [...GIT_BROKER_TOOLS]);
});

test("AC-BROKER-1: buildPmBrokerTools() registers exactly the 4 PM_BROKER_TOOLS names, in order", () => {
  const names = buildPmBrokerTools().map((tool) => tool.name);
  assert.deepEqual(names, [...PM_BROKER_TOOLS]);
});

// ---------------------------------------------------------------------------
// AC-G2-1/AC-G2-2: reachability bound to the ACTUAL registered names (not
// just the roleTable constant) — exactly one role reaches each namespace.
// ---------------------------------------------------------------------------

test("AC-G2-1 (sole-holder, registration-bound): every registered git tool name resolves true for git-ops", () => {
  for (const tool of buildGitBrokerTools()) {
    assert.equal(canUse("git-ops", tool.name), true, `git-ops must reach "${tool.name}"`);
  }
});

test("AC-G2-1 (sole-holder, registration-bound): every registered pm tool name resolves true for project-mgr", () => {
  for (const tool of buildPmBrokerTools()) {
    assert.equal(canUse("project-mgr", tool.name), true, `project-mgr must reach "${tool.name}"`);
  }
});

test("AC-G2-2 (deny-by-default, registration-bound): every registered git tool name resolves false for every OTHER role", () => {
  for (const tool of buildGitBrokerTools()) {
    for (const role of ALL_ROLES) {
      if (role === "git-ops") continue;
      assert.equal(canUse(role, tool.name), false, `${role} must NOT reach "${tool.name}"`);
    }
  }
});

test("AC-G2-2 (deny-by-default, registration-bound): every registered pm tool name resolves false for every OTHER role", () => {
  for (const tool of buildPmBrokerTools()) {
    for (const role of ALL_ROLES) {
      if (role === "project-mgr") continue;
      assert.equal(canUse(role, tool.name), false, `${role} must NOT reach "${tool.name}"`);
    }
  }
});

// ---------------------------------------------------------------------------
// AC-G2-3: `canUse`'s matching code path is unaffected by S6 — a structural,
// automated proxy for the byte-identical claim. TRUE byte-for-byte
// before/after comparison is `git diff` against the pre-S6 commit, which
// this delegation cannot run (`bash: git*` is denied by capability, per the
// gleipnir-code role's own corrected permission model) — that authoritative
// check is left to `git-ops`/`quality-reviewer` downstream. This test is a
// standing regression guard: it fails loudly if a FUTURE change reintroduces
// glob/wildcard matching into `canUse` (the exact shape spec-review rejected
// for the ORIGINAL S6 plan, D-S6-1b).
// ---------------------------------------------------------------------------

test("AC-G2-3 (structural regression guard): canUse's runtime source still resolves via exact-match .includes() only, no glob/wildcard construct", () => {
  const src = canUse.toString();
  assert.ok(src.includes(".includes("), "canUse must still resolve via .includes()");
  for (const forbidden of ["RegExp", ".startsWith(", ".endsWith(", ".match(", ".test(", "glob", "wildcard"]) {
    assert.ok(
      !src.includes(forbidden),
      `canUse's body must not contain "${forbidden}" — any glob/wildcard matching is a canUse body change the operator rejected (D-S6-1b)`,
    );
  }
});

// ---------------------------------------------------------------------------
// AC-RELAY-1: structured params, never argv. Exercised at the shared
// transport (`relayToolCall`) both broker modules delegate to, using the
// SAME mock fixture `mcpStdioClient.test.ts` uses — a `--no-verify`-shaped
// substring travels as a params VALUE, never assembled into argv. (Static
// confirmation that gitBroker.ts/pmBroker.ts themselves never construct argv
// is in this file's source-purity checks below.)
// ---------------------------------------------------------------------------

test("AC-RELAY-1: a commit_changes-shaped call whose message contains --no-verify relays it as the structured params VALUE, not argv", async () => {
  const spec: SpawnSpec = { command: process.execPath, args: [MOCK_BROKER_PATH], env: { MOCK_MODE: "echo" } };
  const controller = new AbortController();
  const params = { message: "chore: mention --no-verify in a commit message body", files: "" };
  const result = await relayToolCall(spec, "commit_changes", params, controller.signal);
  assert.equal(result.success, true);
  const parsed = JSON.parse(result.result ?? "{}");
  assert.deepEqual(parsed.arguments, params, "the relay must pass params through verbatim, never reshaped into an argv array");
});

test("AC-RELAY-1 (static): gitBroker.ts's execute() bodies contain no argv-construction — every execute call site hands `params` straight to relayToolCall", () => {
  const src = readFileSync(join(__dirname, "..", "src", "broker", "gitBroker.ts"), "utf8");
  assert.ok(src.includes("relayToolCall(") , "gitBroker.ts must delegate to relayToolCall");
  for (const forbidden of ["spawn(", "child_process", "--no-verify", "argv"]) {
    assert.ok(!src.includes(forbidden), `gitBroker.ts must not contain "${forbidden}" (Boundary A/C — no framing, no pi-side arg policy)`);
  }
});

test("AC-RELAY-1 (static): pmBroker.ts's execute() bodies contain no argv-construction — every execute call site hands `params` straight to relayToolCall", () => {
  const src = readFileSync(join(__dirname, "..", "src", "broker", "pmBroker.ts"), "utf8");
  assert.ok(src.includes("relayToolCall("), "pmBroker.ts must delegate to relayToolCall");
  for (const forbidden of ["spawn(", "child_process", "argv"]) {
    assert.ok(!src.includes(forbidden), `pmBroker.ts must not contain "${forbidden}" (Boundary A/C)`);
  }
});

// ---------------------------------------------------------------------------
// AC-CRED-1: git spawn spec carries NO credential-bearing env at all.
// ---------------------------------------------------------------------------

test("AC-CRED-1: buildGitSpawnSpec()'s env carries no token/credential-shaped key", () => {
  const spec = buildGitSpawnSpec();
  const keys = Object.keys(spec.env ?? {});
  for (const key of keys) {
    assert.ok(
      !/token|secret|credential|password/i.test(key),
      `git spawn env must carry no credential-shaped key; found "${key}"`,
    );
  }
  assert.ok(!("GITHUB_TOKEN" in (spec.env ?? {})));
  assert.ok(!("GITLAB_TOKEN" in (spec.env ?? {})));
});

test("AC-CRED-1 (static): gitBroker.ts's source never names GITHUB_TOKEN or GITLAB_TOKEN", () => {
  const src = readFileSync(join(__dirname, "..", "src", "broker", "gitBroker.ts"), "utf8");
  assert.ok(!src.includes("GITHUB_TOKEN"));
  assert.ok(!src.includes("GITLAB_TOKEN"));
});

// ---------------------------------------------------------------------------
// AC-CRED-2: pm spawn spec carries the two token vars BY NAME ONLY; the
// extension source never reads `process.env.GITHUB_TOKEN`/`GITLAB_TOKEN`
// into an inspected local; and relaying through the mock (substituting the
// mock for the real `python` target, since the pi sandbox has no Python —
// see the plan's Test-harness constraint) never leaks the value.
// ---------------------------------------------------------------------------

test("AC-CRED-2 (static): pmBroker.ts never dereferences process.env.GITHUB_TOKEN / GITLAB_TOKEN directly — only pickEnv (by-name) touches process.env", () => {
  const src = readFileSync(join(__dirname, "..", "src", "broker", "pmBroker.ts"), "utf8");
  assert.ok(
    !src.includes("process.env.GITHUB_TOKEN") && !src.includes("process.env.GITLAB_TOKEN"),
    "pmBroker.ts must never read the token VALUE directly — only by-NAME via pickEnv",
  );
  assert.ok(src.includes("GITHUB_TOKEN") && src.includes("GITLAB_TOKEN"), "pmBroker.ts must still NAME the two token vars (for pickEnv's allowlist)");
  assert.ok(src.includes("pickEnv("), "pmBroker.ts must build its spawn env via the generic pickEnv utility");
});

test("AC-CRED-2: buildPmSpawnSpec() carries the CURRENT process.env token value under the SAME name (by-name passthrough works)", () => {
  const previous = process.env.GITHUB_TOKEN;
  process.env.GITHUB_TOKEN = "test-token-value-not-a-real-secret";
  try {
    const spec = buildPmSpawnSpec();
    assert.equal(spec.env?.GITHUB_TOKEN, "test-token-value-not-a-real-secret");
  } finally {
    if (previous === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = previous;
  }
});

test("AC-CRED-2 (no leak): relaying with the pm spec's REAL env-passthrough shape (target swapped to the mock — no Python in this sandbox) never leaks the token substring in any result/error", async () => {
  const sentinel = "SENTINEL-PM-TOKEN-7f2c9a";
  const previous = process.env.GITHUB_TOKEN;
  process.env.GITHUB_TOKEN = sentinel;
  try {
    const pmSpec = buildPmSpawnSpec();
    // Swap ONLY the executable target (python -> the mock's node runtime),
    // keeping the SAME env object pmBroker.ts actually builds — this
    // exercises the real credential-passthrough shape without requiring a
    // Python interpreter in-sandbox (Test-harness constraint).
    const mockSpec: SpawnSpec = { ...pmSpec, command: process.execPath, args: [MOCK_BROKER_PATH] };
    const controller = new AbortController();
    const result = await relayToolCall(mockSpec, "issue_create", { title: "t" }, controller.signal);
    const payload = JSON.stringify(result);
    assert.ok(!payload.includes(sentinel), "no relayed result/error may contain the token substring");
  } finally {
    if (previous === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = previous;
  }
});

// ---------------------------------------------------------------------------
// AC-NODEP / AC-PURITY cross-check (broker-module half): neither broker
// module imports anything beyond the client + pi/typebox types.
// ---------------------------------------------------------------------------

test("AC-PURITY (broker modules): gitBroker.ts / pmBroker.ts import only the client, pi types, and typebox — no raw node:child_process of their own", () => {
  for (const file of ["gitBroker.ts", "pmBroker.ts"]) {
    const src = readFileSync(join(__dirname, "..", "src", "broker", file), "utf8");
    assert.ok(!src.includes("node:child_process"), `${file} must delegate spawning to mcpStdioClient.ts, not import node:child_process itself`);
  }
});
