import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import * as fs from "node:fs";
import * as path from "node:path";

// ─── GSD State Extension ────────────────────────────────────────────────
// Maintains a .planning/STATE.md file that tracks:
//   - current_phase: what phase we're working on
//   - last_action: what was last done
//   - decisions: key decisions made
//   - blockers: open blockers
//
// Usage:
//   /gsd:state current        — show current state
//   /gsd:state phase N        — set current phase
//   /gsd:state decide "text"  — record a decision
//   /gsd:state block "text"   — record a blocker
//   /gsd:state resolve "text" — resolve a blocker

// ─── Paths ───────────────────────────────────────────────────────────────

const PLANNING_DIR = ".planning";
const STATE_FILE = "STATE.md";

function planningDir(cwd: string): string {
  return path.join(cwd, PLANNING_DIR);
}

function statePath(cwd: string): string {
  return path.join(planningDir(cwd), STATE_FILE);
}

// ─── State ───────────────────────────────────────────────────────────────

interface GsdState {
  current_phase: string;
  last_action: string;
  last_updated: string;
  decisions: string[];
  blockers: { text: string; resolved: boolean }[];
}

function loadState(cwd: string): GsdState {
  const sp = statePath(cwd);
  if (!fs.existsSync(sp)) {
    return {
      current_phase: "",
      last_action: "",
      last_updated: "",
      decisions: [],
      blockers: [],
    };
  }
  const raw = fs.readFileSync(sp, "utf-8");
  const state: GsdState = {
    current_phase: "",
    last_action: "",
    last_updated: "",
    decisions: [],
    blockers: [],
  };
  // Simple YAML-frontmatter parser
  const lines = raw.split("\n");
  let inFrontmatter = false;
  for (const line of lines) {
    if (line.trim() === "---") {
      inFrontmatter = !inFrontmatter;
      continue;
    }
    if (!inFrontmatter) continue;
    const m = line.match(/^(\w+):\s*(.*)/);
    if (!m) continue;
    const [, key, value] = m;
    if (key === "current_phase") state.current_phase = value.trim();
    if (key === "last_action") state.last_action = value.trim();
    if (key === "last_updated") state.last_updated = value.trim();
  }
  // Parse decisions and blockers from body
  let inDecisions = false;
  let inBlockers = false;
  for (const line of lines) {
    if (line.startsWith("## Decisions")) { inDecisions = true; inBlockers = false; continue; }
    if (line.startsWith("## Blockers")) { inBlockers = true; inDecisions = false; continue; }
    if (line.startsWith("## ")) { inDecisions = false; inBlockers = false; continue; }
    if (inDecisions && line.trim().startsWith("- ")) {
      state.decisions.push(line.trim().slice(2));
    }
    if (inBlockers && line.trim().startsWith("- ")) {
      const text = line.trim().slice(2);
      state.blockers.push({ text: text.replace(" [RESOLVED]", ""), resolved: line.includes("[RESOLVED]") });
    }
  }
  return state;
}

function saveState(cwd: string, state: GsdState): void {
  const pd = planningDir(cwd);
  if (!fs.existsSync(pd)) fs.mkdirSync(pd, { recursive: true });
  state.last_updated = new Date().toISOString();
  const content = [
    "---",
    `current_phase: ${state.current_phase}`,
    `last_action: ${state.last_action}`,
    `last_updated: ${state.last_updated}`,
    "---",
    "",
    "# Project State",
    "",
    "## Decisions",
    ...state.decisions.map(d => `- ${d}`),
    "",
    "## Blockers",
    ...state.blockers.map(b => `- ${b.text}${b.resolved ? " [RESOLVED]" : ""}`),
    "",
  ].join("\n");
  fs.writeFileSync(statePath(cwd), content, "utf-8");
}

// ─── Extension ───────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // Register a custom tool so the LLM can query state
  pi.registerTool({
    name: "gsd_state",
    label: "GSD State",
    description: "Read or update the GSD project state in .planning/STATE.md",
    parameters: Type.Object({
      action: Type.Union([
        Type.Literal("read"),
        Type.Literal("set_phase"),
        Type.Literal("record_decision"),
        Type.Literal("add_blocker"),
        Type.Literal("resolve_blocker"),
      ], { description: "Action: read state, set current phase, record a decision, add or resolve a blocker" }),
      value: Type.Optional(Type.String({ description: "Value for the action (phase number, decision text, blocker text)" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const cwd = ctx.cwd || process.cwd();
      const state = loadState(cwd);

      switch (params.action) {
        case "read": {
          return {
            content: [{
              type: "text",
              text: [
                `**Current Phase:** ${state.current_phase || "(none)"}`,
                `**Last Action:** ${state.last_action || "(none)"}`,
                `**Last Updated:** ${state.last_updated || "(never)"}`,
                `**Decisions:** ${state.decisions.length}`,
                ...state.decisions.map(d => `  - ${d}`),
                `**Blockers:** ${state.blockers.length}`,
                ...state.blockers.map(b => `  - ${b.text}${b.resolved ? " (resolved)" : " (open)"}`),
              ].join("\n"),
            }],
            details: { state },
          };
        }
        case "set_phase": {
          if (!params.value) return { content: [{ type: "text", text: "Error: value required for set_phase" }], details: {} };
          state.current_phase = params.value;
          state.last_action = `Set phase to ${params.value}`;
          saveState(cwd, state);
          return { content: [{ type: "text", text: `Phase set to ${params.value}` }], details: { state } };
        }
        case "record_decision": {
          if (!params.value) return { content: [{ type: "text", text: "Error: value required for record_decision" }], details: {} };
          state.decisions.push(params.value);
          state.last_action = `Recorded decision: ${params.value}`;
          saveState(cwd, state);
          return { content: [{ type: "text", text: `Decision recorded: ${params.value}` }], details: { state } };
        }
        case "add_blocker": {
          if (!params.value) return { content: [{ type: "text", text: "Error: value required for add_blocker" }], details: {} };
          state.blockers.push({ text: params.value, resolved: false });
          state.last_action = `Added blocker: ${params.value}`;
          saveState(cwd, state);
          return { content: [{ type: "text", text: `Blocker added: ${params.value}` }], details: { state } };
        }
        case "resolve_blocker": {
          if (!params.value) return { content: [{ type: "text", text: "Error: value required for resolve_blocker" }], details: {} };
          const blocker = state.blockers.find(b => b.text === params.value && !b.resolved);
          if (blocker) {
            blocker.resolved = true;
            state.last_action = `Resolved blocker: ${params.value}`;
            saveState(cwd, state);
            return { content: [{ type: "text", text: `Blocker resolved: ${params.value}` }], details: { state } };
          }
          return { content: [{ type: "text", text: `Blocker not found or already resolved: ${params.value}` }], details: { state } };
        }
      }
    },
  });

  // Register commands
  pi.registerCommand("gsd:state", {
    description: "Show GSD project state",
    handler: async (_args, ctx) => {
      const state = loadState(ctx.cwd || process.cwd());
      ctx.ui.notify(
        `Phase: ${state.current_phase || "(none)"} | Decisions: ${state.decisions.length} | Blockers: ${state.blockers.filter(b => !b.resolved).length}`,
        "info"
      );
    },
  });

  pi.on("session_start", async (_event, ctx) => {
    const state = loadState(ctx.cwd || process.cwd());
    if (state.current_phase) {
      ctx.ui.notify(`GSD: current phase = ${state.current_phase}`, "info");
    }
  });
}
