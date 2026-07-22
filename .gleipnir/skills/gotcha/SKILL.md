---
version: "1.0"
name: gotcha
description: "GOTCHA framework: a 6-layer architecture for agentic AI systems. Separates Goals, Orchestration, Tools, Context, Hard prompts, and Args to bridge probabilistic LLM reasoning with deterministic code execution."
license: MIT
metadata:
  version: "1.0"
  origin: aetos
  inherited_by: gleipnir
  inheritance: gotcha-as-amended
  amendments:
    - "A1: Orchestration (layer 2) rewritten to the G-5 deterministic engine model; the LLM never decides sequence."
    - "A2: prose 'modify only with permission' rewritten to S-2 structural immutability for enforcement-bearing config."
---

> **GLEIPNIR INHERITANCE NOTE (read first).** This is the AETOS GOTCHA v1.0
> skill inherited verbatim as the K-2 base, then amended in exactly two
> places to conform to Gleipnir's enforcement requirements. Both amendments
> are at, or downstream of, **layer 2 (Orchestration)** — the one place the
> v1.0 methodology collides with Gleipnir Axiom 2. Everything else is a
> faithful copy. The amended passages are marked inline with
> **[GLEIPNIR A1]** and **[GLEIPNIR A2]**. Do not reintroduce the v1.0
> "the LLM decides which tools and in what order" model: G-5 supersedes it.

# The GOTCHA Framework

A 6-layer architecture for agentic systems that separates concerns between
probabilistic reasoning (the AI) and deterministic execution (tools/scripts).

## Why This Exists

When AI tries to do everything itself, errors compound fast. 90% accuracy per
step sounds good until you realise that is roughly 59% accuracy over 5 steps.

The solution:

- Push **reliability** into deterministic code (tools)
- Push **flexibility and reasoning** into the LLM (orchestration)
- Push **process clarity** into goals
- Push **behaviour settings** into args files
- Push **domain knowledge** into the context layer
- Keep each layer focused on a single responsibility

---

## The 6 Layers

### 1. Goals (`goals/`)

Task-specific instructions in clear markdown. Each goal defines:

- Objective
- Inputs
- Which tools to use
- Expected outputs
- Edge cases

Written like you are briefing someone competent. Goals tell the system **what**
to achieve, not how it should behave today.

**[GLEIPNIR A2 — permission model rewritten to conform to G-1/S-2.]** The
v1.0 rule "only modify goals with explicit permission" is a prose guard, the
Dromi-class kind G-1 replaces. Under Gleipnir: enforcement-bearing config
(permission definitions, guard code, the rate table, weakening toggles) is
**immutable from the agent side by the S-2 substrate boundary, not by
instruction**. An agent cannot edit it because the substrate denies the
write, not because a goal asked it not to. The prose "modify only with
permission" convention applies to **non-enforcement goals and context only**,
where it remains a courtesy discipline rather than a security control.

### 2. Orchestration (the AI agent)

**[GLEIPNIR A1 — layer 2 rewritten to conform to G-5.]** Under Gleipnir,
orchestration is **the deterministic G-5 engine, not the LLM**. The engine
sequences pipeline transitions, loop caps, and escalation branches in code,
and calls the LLM for each step's judgment only (classification, routing,
content generation). The LLM's outputs feed the deterministic router; **the
LLM does not decide order and never narrates its own sequence.** This
replaces the AETOS v1.0 description below, which had the LLM decide which
tools to run and in what order — the prose-orchestration model that Gleipnir
Axiom 2 forbids (a guard reachable and blindable by momentum). Flexibility is
preserved where it belongs: the per-step judgment is still the LLM's; the
composition around it is code.

Under Gleipnir the orchestration layer therefore:

- Is code (the G-5 engine), which reads the relevant goal
- **Sequences the pipeline deterministically** — the LLM is called per step, it does not choose the order
- Applies args settings to shape behaviour
- References context for domain knowledge
- Enforces loop caps and escalation branches structurally (a counter in code cannot forget it is on round two)
- Blocks on the human-question primitive as a pipeline state with no outgoing edge until a human answers
- **Never executes work directly** -- it delegates to capability-bounded subagents

<details>
<summary>AETOS v1.0 original (superseded by A1, retained for provenance)</summary>

The AI manager that sits between what needs to happen and getting it done:

- Reads the relevant goal
- Decides which tools to use and in what order
- Applies args settings to shape behaviour
- References context for domain knowledge
- Handles errors, asks clarifying questions, makes judgment calls
- **Never executes work directly** -- it delegates to tools

</details>

### 3. Tools (`tools/`)

Deterministic scripts organised by workflow. Each tool has **one job**: API
calls, data processing, file operations, database work, etc.

- Fast, documented, testable, deterministic
- They do not think. They do not decide. They execute.
- Credentials and environment variables handled via `.env`
- All tools must be listed in `tools/manifest.md`

### 4. Context (`context/`)

Static reference material the system uses to reason:

- Tone rules, writing samples
- ICP descriptions, case studies
- Domain-specific knowledge
- Negative examples (what not to do)

Context shapes quality and style. It is not process or behaviour.

### 5. Hard Prompts (`hardprompts/`)

Reusable text templates for LLM sub-tasks:

- Outline to post
- Rewrite in voice
- Summarise transcript
- Create visual brief

Hard prompts are fixed instructions, not context or goals.

### 6. Args (`args/`)

YAML or JSON files controlling how the system behaves right now:

- Daily themes, frameworks, modes
- Output lengths, schedules
- Model choices, feature flags

Changing args changes behaviour without editing goals or tools.

---

## How to Operate

### 1. Check for existing goals first

Before starting a task, check `goals/manifest.md` for a relevant workflow.
If a goal exists, follow it.

### 2. Check for existing tools

Before writing new code, read `tools/manifest.md`. If a tool exists, use it.
If you create a new tool, **add it to the manifest** with a one-sentence
description.

### 3. When tools fail, fix and document

- Read the error and stack trace carefully
- Update the tool to handle the issue
- Add what you learned to the goal
- If a goal exceeds reasonable length, propose splitting it

### 4. Treat goals as living documentation

Update only when better approaches or constraints emerge. Never modify or
create goals without explicit permission. **[GLEIPNIR A2]** This convention
governs non-enforcement goals and context only; enforcement-bearing config is
not protected by this rule but by the S-2 boundary, which denies the write
outright (see the Goals layer note above).

### 5. Communicate clearly when stuck

If you cannot complete a task with existing tools and goals:

- Explain what is missing
- Explain what you need
- Do not guess or invent capabilities

### 6. Read args before running any workflow

The args layer controls current behaviour. Always check it before executing.

---

## File Structure

| Directory | Layer | Purpose |
|---|---|---|
| `goals/` | Process | What to achieve |
| `tools/` | Execution | Deterministic scripts |
| `args/` | Behaviour | Settings that change output |
| `context/` | Knowledge | Domain reference material |
| `hardprompts/` | Templates | Reusable LLM instructions |
| `memory/` | Persistence | Session logs, MEMORY.md |
| `data/` | Storage | SQLite databases |
| `.env` | Secrets | API keys, credentials |

### Manifests

- `goals/manifest.md` -- Index of available goal workflows
- `tools/manifest.md` -- Master list of tools and their functions

### Temporary Work

Use `.tmp/` for scrapes, raw data, intermediate files. Always disposable.
Never store important data in `.tmp/`.

---

## Memory Protocol

If the project uses the aetos memory system:

**At session start (preferred -- MCP):**

Call `memory_read` from `aetos-memory` to load full session context
(MEMORY.md + logs + DB entries + tasks) in a single tool call.

**At session start (fallback -- filesystem):**

If the MCP server is not available, read files directly:

1. Read `memory/MEMORY.md` for curated facts and preferences
2. Read today's log: `memory/logs/YYYY-MM-DD.md`
3. Read yesterday's log for continuity
4. Check pending tasks

**During session:**

- `memory_write` for facts, insights, events, preferences (MCP preferred)
- `memory_log` for quick session notes
- `memory_persist` for truly persistent facts (appends to MEMORY.md)
- Fallback: append directly to log files and MEMORY.md

**Search:**

- `memory_search` for keyword search (auto-falls back to semantic in large DBs)
- Fallback: keyword search via file reads

---

## The Continuous Improvement Loop

Every failure strengthens the system:

1. Identify what broke and why
2. Fix the tool script
3. Test until it works reliably
4. Update the goal with new knowledge
5. Next time: automatic success

---

## Guardrails

Document mistakes and learned behaviours here. Keep this under 15 items.

> **[GLEIPNIR link — Guardrails map to G-4c.]** Under Gleipnir this graduated
> Guardrails list is inherited, but its promotion path changes. The manual
> "keep under 15, graduate stable ones to `context/LESSONS.md`" cap is
> replaced by G-4c's **measured graduation criteria**: a candidate guard
> graduates only if, during trial, it (a) fired at least once on a real
> event, (b) is associated with a measured reduction in the correction or
> failure rate it was proposed against, and (c) stays under a false-positive
> threshold. Failing candidates expire. The proposal structure comes from the
> K-3 decision-frameworks catalogue. The list below is inherited as seed
> content; new entries flow through G-4c, not a manual cap.

- Always check `tools/manifest.md` before writing a new script
- Verify tool output format before chaining into another tool
- Do not assume APIs support batch operations -- check first
- When a workflow fails mid-execution, preserve intermediate outputs before retrying
- Read the full goal before starting a task -- do not skim
- **Write plans to disk immediately, using the plan format goal** -- Persist
  design documents to `.opencode/plans/` or equivalent at the moment of
  creation. Chat-only designs are lost on context compaction. The plan file
  is the artifact. Use `goals/plan-format.md` as the required structure --
  a plan without an Execution Workflow section is incomplete and will cause
  the implementing agent to rediscover the protocol from scratch.
  **Writing a plan file is planning, not implementation -- it is never
  blocked by read-only or plan mode. Never defer plan persistence.**
- **Follow the platform lifecycle protocol** -- Before creating any
  milestone, issue, or MR, read `goals/platform-lifecycle.md`. Covers:
  issue creation at plan time (not build time), assignment/estimation/
  workflow state before implementation, milestone description format
  (use `hardprompts/milestone-description.md`), aetos-pm tools preferred
  over raw API. If you are in build mode and issues don't exist, you
  failed to plan properly -- stop and create them first.
- **Reinstall after editing aetos source files** -- When you edit any
  file under `src/python/aetos/`, the installed package becomes stale.  Run
  `pip install -e ".[mcp]"` (or the project's equivalent editable
  install command) **before** invoking MCP tools or importing from the
  package in inline scripts.  Stale installs silently use old code --
  this caused an entire session's worth of comments to be posted without
  the robot stamp.  The platform layer includes a version-drift warning
  to catch this, but do not rely on it.
- **Complete the milestone/session checklist** -- Run the full test suite
  before every commit (never commit with known failures unless explicitly
  instructed). Keep the tracker log (`.aetos/tracker/LOG.md`) updated
  throughout the session, not just at close. Clean up plan files in
  `.opencode/plans/` after the associated feature is merged. See
  `skills/github-flow/SKILL.md` Post-Merge step 5 for the full checklist
  and `skills/ai-dev-tracker/SKILL.md` for the tracker entry format.
- **Verify cross-file consistency before committing changes to skill
  files or AGENTS.md** -- Tool counts, version strings, and cross-skill
  references must agree across all instruction files. Run the Pre-Merge
  Consistency Checklist in `skills/github-flow/SKILL.md` before
  requesting review. The automated checks in `tests/test_consistency.py`
  catch mechanical issues; the checklist catches semantic ones.

- **Block on user decisions, never assume** -- After creating a PR/MR and
  sending notification, use the `question` tool to ask the user for merge
  status before proceeding to cleanup. This applies at any decision point
  where the workflow needs user input to continue. Never silently return
  to standby after PR creation -- see `goals/platform-lifecycle.md`
  Section 4 (MR Gate).

- **Verify subagent outputs against inputs** -- When a subagent reports
  success, verify that the output is consistent with the delegation
  inputs. If you asked the subagent to notify user X and it reports
  notifying user Y, that is a failure -- not a success. Subagents can
  hallucinate outputs when they lack the tools to complete the task.

- **Never rebase a pushed feature branch — merge instead** -- When a
  feature branch has diverged from main, run `git fetch origin && git merge
  origin/main` (or call `merge_branch` MCP tool). Rebase rewrites commit
  history and requires force-push, which is structurally blocked by hooks
  and plugins. This caused 6 wasted agent cycles on 2026-04-07.

- **Audit tests when removing or renaming functions** -- When removing or
  renaming a function, class, or public symbol, grep for all tests that
  import or reference it and update or delete them in the same commit.
  A function removal without a corresponding test update is an incomplete
  change. Use `grep -r "symbol_name" tests/` (or the project's test
  directory) before committing the removal.

- **One open MR per target branch at a time** -- Never raise a second MR
  against the same target branch while a first is still open. The second
  MR will conflict on VERSION (due to `auto_bump_patch`) the moment the
  first merges. Wait for the first MR to merge, then merge the target
  into the next feature branch and raise its MR. This caused 4 stale MRs
  and repeated VERSION conflicts on 2026-04-07.

*(Add new guardrails as mistakes happen. Graduate stable guardrails to
`context/LESSONS.md` -- see the graduation protocol.)*

---

## Pre-Flight Checklist

**Before writing any code**, output this checklist visibly in chat.  Skip
items whose gate skill/MCP is not wired up in the current project.  If any
required item answers "no," **stop and fix it before proceeding.**

Detection: a skill is "wired" if it appears in `.mcp.json`, `opencode.json`,
`claude.json`, or equivalent agent config.  If you cannot determine wiring,
assume the skill is active when its `skills/` directory exists.

```
PRE-FLIGHT  (items marked * are conditional)

[ ] Plan file exists on disk (using goals/plan-format.md structure)?
    Gate: always
    Path: .opencode/plans/<name>.md or equivalent

[ ] *Platform lifecycle completed?
    Gate: aetos-pm + github-flow
    Read: goals/platform-lifecycle.md
    Verify: issue exists, assigned, estimated, workflow_state=doing,
            milestone has full description (hardprompts/milestone-description.md)

[ ] *Editable install current after source edits?
    Gate: editing files under src/python/aetos/
    Action: pip install -e ".[mcp]"

[ ] *Consistency check needed?
    Gate: editing skill files or AGENTS.md
    Action: run tests/test_consistency.py + Pre-Merge Consistency Checklist

[ ] Checked tools/manifest.md for existing tools?
    Gate: goals/ and tools/ directories exist

[ ] Read the full goal before starting?
    Gate: goals/ directory exists
```

**When to run:** before every implementation block -- defined as any
sequence of file edits intended to fulfil an issue, task, or user request.
Planning (writing plan files, creating issues) is NOT an implementation
block and does not require the checklist.

**Failure mode this prevents:** the agent jumps into coding under momentum,
skipping issue creation, lifecycle steps, or plan persistence.  Making the
checklist visible in chat means the operator can spot violations in the log
without watching in real time.

---

## Summary

You sit between what needs to happen (goals) and getting it done (tools).
Read instructions, apply args, use context, delegate well, handle failures,
and strengthen the system with each run.
