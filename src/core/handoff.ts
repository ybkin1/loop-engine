import { readFileSync, writeFileSync, existsSync, renameSync } from "node:fs";
import { join } from "node:path";
import { stringify } from "yaml";
import { computeHash } from "./evidence.js";
import { loadState, saveState } from "./state-machine.js";
import type { HandoffRecord, HandoffResult } from "../types/index.js";

function handoffFile(root: string) { return join(root, ".ai", "HANDOFF.md"); }

function atomicWrite(filePath: string, content: string): void {
  const tmp = filePath + ".tmp";
  writeFileSync(tmp, content, "utf-8");
  renameSync(tmp, filePath);
}

export async function createHandoff(
  root: string,
  fromRole: string,
  toRole: string,
  artifacts: { path: string; version: string }[],
  contextSummary: string,
  unresolvedItems: string[] = [],
): Promise<HandoffResult> {
  const now = new Date().toISOString();
  const artifactsWithHash = artifacts.map(a => ({
    path: a.path,
    hash: computeHash(a.path + a.version),
    version: a.version,
  }));

  const record: HandoffRecord = {
    timestamp: now,
    from_role: fromRole,
    to_role: toRole,
    artifacts: artifactsWithHash,
    context_summary: contextSummary,
    unresolved_items: unresolvedItems,
  };

  // Append to HANDOFF.md
  const md = serializeHandoff(record);
  const existing = existsSync(handoffFile(root)) ? readFileSync(handoffFile(root), "utf-8") : "# Handoff Log\n\n";
  atomicWrite(handoffFile(root), existing + md);

  // Update state
  const state = await loadState(root);
  state.last_handoff_at = now;
  await saveState(root, state);

  return {
    success: true,
    handoff_id: `${fromRole}-to-${toRole}-${Date.now()}`,
    recorded_at: now,
    artifacts_count: artifacts.length,
  };
}

export function getHandoffHistory(root: string): string {
  const file = handoffFile(root);
  if (!existsSync(file)) return "";
  return readFileSync(file, "utf-8");
}

export function serializeHandoff(record: HandoffRecord): string {
  const lines: string[] = [];
  lines.push(`## [${record.timestamp}] ${record.from_role} → ${record.to_role}`);
  lines.push("");
  lines.push(`**Context:** ${record.context_summary}`);
  lines.push("");
  if (record.artifacts.length > 0) {
    lines.push("**Artifacts:**");
    for (const a of record.artifacts) {
      lines.push(`- \`${a.path}\` (v${a.version}, sha256:${a.hash.slice(0, 16)}...)`);
    }
    lines.push("");
  }
  if (record.unresolved_items.length > 0) {
    lines.push("**Unresolved:**");
    for (const item of record.unresolved_items) {
      lines.push(`- ${item}`);
    }
    lines.push("");
  }
  lines.push("---\n");
  return lines.join("\n");
}
