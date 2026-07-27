# Hook-Probe Findings — opencode plugin hooks vs. Gleipnir engine wire-in

**Task:** Determine, from opencode's official docs + authoritative source, whether
two properties the Gleipnir G-5 engine depends on hold, plus re-confirm abort.
Research-only. Sources fetched: `opencode.ai/docs/plugins`, `/docs/sdk`,
`/docs/tools`, `/docs/agents`, and (authoritative) the pinned type/source files
on GitHub `anomalyco/opencode@dev`.

**Bottom line up front:**
- Point 1 (target-agent visibility, pre-tool): **YES** (from source; docs alone
  are AMBIGUOUS).
- Point 2 (post-tool fires w/ result): **YES**. (plugin can run arbitrary
  in-process JS / spawn subprocess / do file IO): **YES**. Invoke *Python*
  specifically: **YES via subprocess**, not via a Python-native binding.
- Point 3 (abort by throw): **YES**.
- **Overall:** the build gate can be **PASSED from authoritative source**
  (the pinned `@dev` type + `task.ts` schema). It **cannot be passed from the
  prose docs alone** — the docs never quote the `task` args shape or the
  hook input/output TypeScript types. See "Residual live-probe items" for the
  two things still worth a smoke-test even though source confirms them.

---

## Point 1 — TARGET-AGENT VISIBILITY (pre-tool). **YES**

### Hook input/output shape (authoritative — plugin package types, `@dev`)
`packages/plugin/src/index.ts`:

```ts
"tool.execute.before"?: (
  input: { tool: string; sessionID: string; callID: string },
  output: { args: any },
) => Promise<void>
```

So the pre-tool hook sees `input.tool` (the tool name) and a mutable
`output.args` (the tool's arguments). This matches the docs' examples, e.g.
the `.env` protection sample:

> `"tool.execute.before": async (input, output) => { if (input.tool === "read" && output.args.filePath.includes(".env")) { throw new Error("Do not read .env files") } }`
> — /docs/plugins, ".env protection"

### Is the dispatched subagent's identity in `output.args` for a `task` call?
The docs do **not** document the `task` tool or its argument names anywhere
(the /docs/tools page lists bash/edit/write/read/grep/glob/lsp/apply_patch/
skill/todowrite/webfetch/websearch/question — **no `task` entry**). On the
docs alone this is **AMBIGUOUS**.

It is resolved **YES** by the authoritative tool schema,
`packages/opencode/src/tool/task.ts@dev`. The `task` tool id and parameters:

```ts
const id = "task"
const BaseParameterFields = {
  description:    Schema.String,   // "A short (3-5 words) description of the task"
  prompt:         Schema.String,   // "The task for the agent to perform"
  subagent_type:  Schema.String,   // "The type of specialized agent to use for this task"
  task_id:        Schema.optional(Schema.String),
  command:        Schema.optional(Schema.String),
}
```

Therefore for a task delegation the gate can read, in the pre-tool hook:
- `input.tool === "task"`  → identifies it as a task dispatch, AND
- `output.args.subagent_type` (string) → the IDENTITY of the target subagent.

Also usable: `output.args.description`, `output.args.prompt`, and
`output.args.task_id` (set only on resume). Note the field name is
`subagent_type` (snake case), NOT `agent`/`agent_name`.

Corroboration that opencode itself gates dispatch on exactly this field:
task.ts calls `ctx.ask({ permission: "task", patterns: [params.subagent_type], … })`,
and /docs/agents documents per-agent `permission.task` glob rules matched
against the subagent name ("Control which subagents an agent can invoke via
the Task tool with `permission.task`. Uses glob patterns"). So the subagent
identity is unambiguously the gating key.

**Verdict Point 1: YES** — subagent identity is `output.args.subagent_type`,
tool identity is `input.tool === "task"`. (Docs-only: AMBIGUOUS; confirmed by
`@dev` source.)

---

## Point 2 — POST-TOOL OBSERVATION + IN-PROCESS ADVANCE

### 2a. `tool.execute.after` fires after the tool completes, with identity+result. **YES**
`packages/plugin/src/index.ts@dev`:

```ts
"tool.execute.after"?: (
  input: { tool: string; sessionID: string; callID: string; args: any },
  output: {
    title: string
    output: string
    metadata: any
  },
) => Promise<void>
```

`input.tool` gives the tool identity (`"task"`), `input.args` echoes the call
args (so `subagent_type` is available post-hoc too), and `output.output` /
`output.metadata` carry the result. For a completed foreground task, task.ts
returns `{ title, metadata, output: renderOutput({state:"completed", …}) }`,
where `renderOutput` emits `<task id="…" state="completed"><task_result>…`.
The docs list `tool.execute.after` as an available Tool event but do not quote
its shape — so, docs-only this is thinly documented; **source confirms YES**.

Caveat for background subagents: `background=true` (experimental,
`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`) returns `state:"running"`
immediately; completion is delivered later via a synthetic message injection,
not a second `tool.execute.after`. For the default **foreground** task path
(what the engine uses), `tool.execute.after` firing with the completed result
is correct.

### 2b. Can the plugin run arbitrary in-process code / subprocess / file IO, w/o a roster-agent bash grant? **YES**
The plugin is **framework code**, not an agent tool call. It is a JS/TS module
that opencode loads and runs in-process; roster-agent `permission`/`bash`
grants gate what the *LLM agent* may call, and are orthogonal to what the
*plugin function body* may do. Evidence:

- The plugin function receives a context with Bun's shell:
  > "`$`: Bun's shell API for executing commands." — /docs/plugins, "Basic structure"
  Confirmed in `PluginInput` (`@dev`): `$: BunShell`, plus `client`, `project`,
  `directory`, `worktree`, `serverUrl`.
- The docs' own notification example runs an arbitrary subprocess from a hook:
  > `await $\`osascript -e 'display notification "Session completed!" …'\`` — /docs/plugins
- Custom-tool `execute` functions "can execute arbitrary code" (/docs/tools,
  "Custom tools"), and plugins may add them; the plugin module can `import`
  npm deps via a config-dir `package.json` (/docs/plugins, "Dependencies").

**File IO:** not called out as a named API, but a plugin is an ordinary
Bun/Node module and can use `fs` / Bun file APIs directly in-process, and/or
`$` for shell IO. The docs don't *explicitly* say "a plugin may fs.writeFile",
so that specific claim is **inferred (not doc-quoted)** — but it follows
directly from "it's a JS/TS module" + Bun runtime, and the `$` shell API is an
explicit, documented fallback that trivially does file IO.

**Invoke local Python specifically:** there is no Python-native binding. The
supported path is: the plugin (framework code) shells out with `$` (e.g.
`await $\`python3 .gleipnir/engine/advance.py …\``) or does the driver-advance
in-process JS directly (read engine state file, rewrite it) with no agent bash
grant involved. Both are within documented capability.

**Verdict Point 2:** post-tool fires with tool identity + result — **YES**.
Plugin can run in-process JS / spawn subprocess / do file IO without a
roster-agent bash grant — **YES** (Python only via `$` subprocess, not a
native binding; direct `fs` IO is inferred from "it's a Bun module", not a
verbatim doc quote).

---

## Point 3 — ABORT CAPABILITY. **YES**
`tool.execute.before` can throw to abort the tool call. Documented verbatim:

> "Prevent opencode from reading `.env` files:
> `"tool.execute.before": async (input, output) => { if (input.tool === "read" && output.args.filePath.includes(".env")) { throw new Error("Do not read .env files") } }`"
> — /docs/plugins, ".env protection"

A thrown error in the pre-tool hook aborts the call. **YES** (re-confirmed,
consistent with S-1 verification).

---

## Overall: can the build gate be PASSED from docs alone?
- **From the authoritative pinned source (`anomalyco/opencode@dev`
  `packages/plugin/src/index.ts` + `packages/opencode/src/tool/task.ts`):
  YES — all three points pass.**
- **From the prose docs (`opencode.ai/docs/*`) alone: NO.** The docs never
  document the `task` tool nor its `subagent_type` arg (Point 1), and never
  quote the `tool.execute.before/after` input/output types (Points 1–2). Those
  come only from source.

### Residual live-probe items (recommended even though source confirms)
1. **Point 1 arg key at runtime.** Source says `output.args.subagent_type`.
   The `@dev` source is a moving target and could rename. A 1-shot probe hook
   that logs `input.tool` + `Object.keys(output.args)` on a real `task`
   dispatch pins the exact runtime key for the installed opencode version.
   Cheap; removes the last "source ≠ installed build" risk.
2. **Point 2b direct `fs` IO from a hook.** Doc-inferred, not doc-quoted.
   Trivially confirmable by having the same probe hook write a file. (If
   preferred, sidestep entirely by using the documented `$` shell API for the
   driver-advance, which is explicitly supported.)

Neither residual item blocks the design decision; both are smoke-tests to lock
the exact runtime contract of the installed binary against the `@dev` source.

**Version note:** hook shapes taken from the `dev` branch; the installed
opencode should be spot-checked against its own version for the two items above.
