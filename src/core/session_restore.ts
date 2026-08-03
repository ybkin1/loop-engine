/**
 * session_restore.ts — Cross-Session Context Restoration
 *
 * Integrates loopany's task/outcome history with the KnowledgeLedger's
 * lesson database to provide comprehensive context restoration at the
 * start of each agent session.
 *
 * Used by:
 * - loopany Skill: session restore step
 * - auto-orchestrate.cjs: pre-session hook context injection
 * - R11 (Orchestrator): building role context for sub-agents
 */

import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

// ── Session Restore Result ───────────────────────────────────────────────────

/** A single unresolved lesson for session restore display. */
export interface UnresolvedLessonSummary {
  lesson_id: string;
  phase_id: string;
  role_id: string;
  category: string;
  symptom: string;
  tags: string[];
  captured_at: string;
}

/** Complete session restore context. */
export interface SessionRestoreContext {
  /** Project root directory */
  project_root: string;
  /** Current phase from state.yaml */
  current_phase: string;
  /** Number of unresolved lessons in the knowledge ledger */
  unresolved_lessons_count: number;
  /** Unresolved lessons for the current phase (most relevant) */
  current_phase_lessons: UnresolvedLessonSummary[];
  /** Other unresolved lessons across all phases */
  other_unresolved_lessons: UnresolvedLessonSummary[];
  /** Formatted markdown summary for display/injection */
  summary_markdown: string;
  /** Brief one-line reminders for console/log output */
  brief_reminders: string[];
}

// ── Knowledge Ledger Path ────────────────────────────────────────────────────

const DEFAULT_LEDGER_PATH = ".ai/lessons/lessons.jsonl";

/**
 * Read and parse the knowledge ledger JSONL file.
 * Returns parsed records or empty array if the ledger doesn't exist.
 */
function readKnowledgeLedgerRaw(projectRoot: string): Array<Record<string, unknown>> {
  const ledgerPath = resolve(projectRoot, DEFAULT_LEDGER_PATH);
  if (!existsSync(ledgerPath)) return [];

  try {
    const raw = readFileSync(ledgerPath, "utf-8");
    const records: Array<Record<string, unknown>> = [];
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (trimmed.length === 0) continue;
      try {
        records.push(JSON.parse(trimmed));
      } catch {
        // Skip malformed lines
      }
    }
    return records;
  } catch {
    return [];
  }
}

/**
 * Read the project state from state.yaml (simple YAML parsing).
 */
function readProjectState(projectRoot: string): { current_phase: string } {
  const statePath = resolve(projectRoot, ".ai/state.yaml");
  if (!existsSync(statePath)) return { current_phase: "unknown" };

  try {
    const raw = readFileSync(statePath, "utf-8");
    const match = raw.match(/^current_phase:\s*(.+)$/m);
    return { current_phase: match ? match[1].trim() : "unknown" };
  } catch {
    return { current_phase: "unknown" };
  }
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Restore session context by reading the knowledge ledger and project state.
 *
 * Returns a comprehensive context object designed for injection into
 * the agent's initial context or loopany's session restore output.
 *
 * @param projectRoot - Absolute path to the project root
 * @param maxLessons - Maximum number of lessons to include in summary (default 10)
 * @returns Session restore context with unresolved lessons and formatted summaries
 */
export function restoreSessionContext(
  projectRoot: string,
  maxLessons = 10,
): SessionRestoreContext {
  const state = readProjectState(projectRoot);
  const records = readKnowledgeLedgerRaw(projectRoot);

  // Filter to unresolved lessons (OPEN or ACKNOWLEDGED)
  const unresolved = records.filter(
    r => r.status === "OPEN" || r.status === "ACKNOWLEDGED",
  );

  // Map to summaries
  const toSummary = (r: Record<string, unknown>): UnresolvedLessonSummary => ({
    lesson_id: String(r.lesson_id ?? "unknown"),
    phase_id: String(r.phase_id ?? "unknown"),
    role_id: String(r.role_id ?? "unknown"),
    category: String(r.category ?? "OTHER"),
    symptom: String(r.symptom ?? ""),
    tags: Array.isArray(r.tags) ? r.tags as string[] : [],
    captured_at: String(r.timestamp ?? ""),
  });

  const allUnresolved = unresolved.map(toSummary);

  // Split: current phase vs others
  const currentPhaseLessons = allUnresolved.filter(
    l => l.phase_id === state.current_phase,
  );
  const otherLessons = allUnresolved.filter(
    l => l.phase_id !== state.current_phase,
  );

  // Limit
  const displayCurrent = currentPhaseLessons.slice(0, maxLessons);
  const displayOther = otherLessons.slice(0, Math.max(0, maxLessons - displayCurrent.length));

  // Build brief reminders
  const briefReminders: string[] = [];
  if (displayCurrent.length > 0) {
    briefReminders.push(
      `⚠️ 当前阶段 (${state.current_phase}) 有 ${currentPhaseLessons.length} 条未解决的经验教训`,
    );
  }
  if (otherLessons.length > 0) {
    briefReminders.push(
      `📝 其他阶段还有 ${otherLessons.length} 条未解决教训`,
    );
  }
  if (allUnresolved.length === 0) {
    briefReminders.push("✅ 知识账本无未解决教训");
  }

  // Build markdown summary
  const lines: string[] = [
    "## 🔄 会话恢复 — 知识沉淀提醒",
    "",
    `> 当前阶段: **${state.current_phase}** | 未解决教训: **${allUnresolved.length}** 条`,
    "",
  ];

  if (displayCurrent.length > 0) {
    lines.push(`### 当前阶段 (${state.current_phase}) 未解决问题`);
    lines.push("");
    for (const l of displayCurrent) {
      const shortSymptom = l.symptom.length > 100
        ? l.symptom.substring(0, 100) + "..."
        : l.symptom;
      lines.push(`- **${l.category}** [${l.lesson_id}] — ${shortSymptom}`);
    }
    lines.push("");
  }

  if (displayOther.length > 0) {
    lines.push("### 其他阶段未解决问题");
    lines.push("");
    for (const l of displayOther) {
      const shortSymptom = l.symptom.length > 100
        ? l.symptom.substring(0, 100) + "..."
        : l.symptom;
      lines.push(`- **${l.category}** [${l.lesson_id}] (${l.phase_id}) — ${shortSymptom}`);
    }
    lines.push("");
  }

  if (allUnresolved.length === 0) {
    lines.push("暂无未解决的经验教训。🎉");
    lines.push("");
  }

  lines.push("> 💡 这些问题在上次会话中被记录但尚未解决。建议在继续工作前优先处理。");

  return {
    project_root: projectRoot,
    current_phase: state.current_phase,
    unresolved_lessons_count: allUnresolved.length,
    current_phase_lessons: displayCurrent,
    other_unresolved_lessons: displayOther,
    summary_markdown: lines.join("\n"),
    brief_reminders: briefReminders,
  };
}

/**
 * Generate brief status text suitable for injection into auto-orchestrate
 * or session-brief hooks (kept short to avoid token waste).
 */
export function getKnowledgeStatusLine(projectRoot: string): string {
  const ctx = restoreSessionContext(projectRoot, 0);
  if (ctx.unresolved_lessons_count === 0) {
    return "✅ 知识账本: 无未解决教训";
  }
  return `⚠️ 知识账本: ${ctx.unresolved_lessons_count} 条未解决教训 (当前阶段 ${ctx.current_phase_lessons.length} 条)`;
}
