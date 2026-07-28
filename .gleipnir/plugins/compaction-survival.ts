// Gleipnir port of the AETOS compaction-survival plugin (reference version 3.19.0,
// ../aetos/.aetos/plugins/compaction-survival.ts). Scans .gleipnir/ paths instead
// of .opencode/, and drops the AETOS-specific rules/ and python-manifest scans.
//
// Purpose: preserve the orchestrator's pinned critical guardrails across context
// compaction. When opencode compacts the session (at the operator-set context cap,
// see .gleipnir/policy/context-cap.jsonc), this hook re-injects any
// `compaction_survival:` entries declared in agent frontmatter / skill SKILL.md
// files, so the orchestrator's hard rules survive the compaction rather than being
// summarised away. No hard truncation, no fail-closed — compaction proceeds and the
// pinned rules ride through it.
//
// Tier-3 enforcement-bearing code: **authored, enforced-at-hook, not yet closed**
// until S-2 boundary + G-1 preflight make plugins/** OS-ro to the agent uid
// (.gleipnir/decisions/s2-g1-closure.md). It is cooperative policy today, not an
// unbreakable guard.
//
// Experimental-hook coupling: `experimental.session.compacting` and `chat.params`
// are experimental opencode hooks ("may change without notice"). The validated
// opencode version is recorded in .gleipnir/decisions/context-cap.md; an opencode
// upgrade is a re-validation trigger.
import type { Plugin } from "@opencode-ai/plugin";
import * as fs from "fs";
import * as path from "path";

// Scan a directory for .md files matching a glob pattern
function findMdFiles(pattern: string): string[] {
  try {
    const cwd = process.cwd();
    // pattern like ".gleipnir/agents/*.md"
    const parts = pattern.split("/");
    const dir = parts.slice(0, -1).join("/");
    const fullDir = path.join(cwd, dir);
    if (!fs.existsSync(fullDir)) return [];
    const files = fs.readdirSync(fullDir);
    return files
      .filter(f => f.endsWith(".md"))
      .map(f => path.join(fullDir, f));
  } catch {
    return [];
  }
}

function findSkillFiles(): string[] {
  try {
    const cwd = process.cwd();
    const skillsDir = path.join(cwd, ".gleipnir", "skills");
    if (!fs.existsSync(skillsDir)) return [];
    const pluginDirs = fs.readdirSync(skillsDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => path.join(skillsDir, d.name, "SKILL.md"));
    return pluginDirs.filter(p => fs.existsSync(p));
  } catch {
    return [];
  }
}

function extractCompactionSurvival(filePath: string): string[] {
  try {
    const content = fs.readFileSync(filePath, "utf-8");
    // Find YAML frontmatter between --- delimiters
    const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!fmMatch) return [];
    const frontmatter = fmMatch[1];
    // Find compaction_survival: key
    const csIdx = frontmatter.indexOf("compaction_survival:");
    if (csIdx === -1) return [];
    const afterKey = frontmatter.slice(csIdx + "compaction_survival:".length);
    const items: string[] = [];
    // Collect lines starting with '  - "'
    for (const line of afterKey.split("\n")) {
      const m = line.match(/^  - "(.*)"$/);
      if (!m) {
        // Stop when we hit a non-item line that isn't blank
        if (line.trim() && !line.startsWith("  ")) break;
        continue;
      }
      // Interpret \n escape sequences as real newlines
      items.push(m[1].replace(/\\n/g, "\n"));
    }
    return items;
  } catch {
    return [];
  }
}

// The frontmatter key this plugin owns. It is consumed by the
// experimental.session.compacting hook below (read from files) and must be
// swallowed from the outbound request by the chat.params hook, so it never
// reaches the model. opencode's parameter transparency otherwise spreads
// unrecognised agent frontmatter into the request options, and a strict schema
// (Bedrock/aperture) rejects unknown fields.
const OWNED_KEY = "compaction_survival";

export const CompactionSurvival: Plugin = async (_ctx) => {
  return {
    "experimental.session.compacting": async (
      _input: unknown,
      output: { context: string[] }
    ) => {
      const allTraits: string[] = [];

      // Scan agent templates
      const agentFiles = findMdFiles(".gleipnir/agents/*.md");
      for (const f of agentFiles) {
        allTraits.push(...extractCompactionSurvival(f));
      }

      // Scan skill SKILL.md files
      const skillFiles = findSkillFiles();
      for (const f of skillFiles) {
        allTraits.push(...extractCompactionSurvival(f));
      }

      // Deduplicate by exact string match
      const seen = new Set<string>();
      const unique = allTraits.filter(t => {
        if (seen.has(t)) return false;
        seen.add(t);
        return true;
      });

      if (unique.length === 0) return;

      const block = "## Critical Guardrails (preserved across compaction)\n\n" + unique.join("\n\n");
      output.context.push(block);
    },

    // Swallow-on-consumption: this plugin owns OWNED_KEY, so it removes that
    // key from the outbound model request. opencode spreads unrecognised agent
    // frontmatter into the options bag; without this, the key reaches the
    // provider and is rejected as an unpermitted extra input.
    "chat.params": async (
      _input: unknown,
      output: { options?: Record<string, unknown> } & Record<string, unknown>
    ) => {
      if (output.options && OWNED_KEY in output.options) {
        delete output.options[OWNED_KEY];
      }
      // Defensive: some opencode versions may surface the spread key at the top
      // level of the params object rather than nested under options.
      if (OWNED_KEY in output) {
        delete (output as Record<string, unknown>)[OWNED_KEY];
      }
    },
  };
};

export default CompactionSurvival;
