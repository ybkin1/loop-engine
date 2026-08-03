/**
 * review_advisor.ts — Knowledge-Powered Review Advisor
 *
 * Provides pre-review intelligence by querying the KnowledgeLedger for
 * historical failure patterns relevant to the current review context.
 *
 * Used by:
 * - R09 (Independent Reviewer): pre-review check before code review
 * - R07 (Quality Engineer): quality report historical defect analysis
 * - R11 (Orchestrator): injects advisories into role context
 *
 * Design: pure functions that consume a KnowledgeLedger instance.
 * No side effects — only reads from the ledger.
 */

import { KnowledgeLedger } from "./knowledge_ledger.js";
import { LessonCategory, LessonStatus } from "../types/lesson.js";
import type { LessonRecord, LessonStatistics } from "../types/lesson.js";

// ── Pre-Review Advisory ──────────────────────────────────────────────────────

/** Input for generating a pre-review advisory. */
export interface PreReviewInput {
  /** Phase being reviewed (e.g. "S4-implementation") */
  phase_id: string;
  /** Role whose output is being reviewed */
  role_id: string;
  /** Optional task ID for scoped queries */
  task_id?: string;
  /** Maximum number of historical lessons to return (default 5) */
  max_lessons?: number;
}

/** A single historical lesson formatted for reviewer consumption. */
export interface AdvisoryItem {
  lesson_id: string;
  category: LessonCategory;
  severity: "BLOCKER" | "WARNING";
  symptom: string;
  resolution?: string;
  tags: string[];
  occurred_at: string;
  relevance_reason: string;
}

/** Complete pre-review advisory result. */
export interface PreReviewAdvisory {
  /** The phase being reviewed */
  phase_id: string;
  /** Total historical lessons in this phase */
  total_historical: number;
  /** Unresolved lessons in this phase */
  unresolved_count: number;
  /** Top categories by frequency */
  top_categories: Array<{ category: LessonCategory; count: number }>;
  /** Relevant historical lessons for the reviewer to consider */
  relevant_lessons: AdvisoryItem[];
  /** Summary text for injection into reviewer context */
  summary: string;
}

/**
 * Generate a pre-review advisory by querying the knowledge ledger.
 *
 * Finds historical failures in the same phase, with the same role,
 * and identifies patterns that the reviewer should watch for.
 *
 * @param ledger - The KnowledgeLedger instance
 * @param input - Context for the review
 * @returns A structured advisory with relevant historical lessons
 */
export function generatePreReviewAdvisory(
  ledger: KnowledgeLedger,
  input: PreReviewInput,
): PreReviewAdvisory {
  const maxLessons = input.max_lessons ?? 5;

  // Query: same phase, all categories
  const samePhase = ledger.query({ phase_id: input.phase_id, limit: 50 });

  // Query: same role
  const sameRole = ledger.query({ role_id: input.role_id, limit: 50 });

  // Merge and deduplicate by lesson_id
  const seen = new Set<string>();
  const merged: LessonRecord[] = [];
  for (const r of [...samePhase, ...sameRole]) {
    if (!seen.has(r.lesson_id)) {
      seen.add(r.lesson_id);
      merged.push(r);
    }
  }

  // Unresolved count
  const unresolved = merged.filter(
    r => r.status === LessonStatus.OPEN || r.status === LessonStatus.ACKNOWLEDGED,
  );

  // Top categories
  const catCount = new Map<LessonCategory, number>();
  for (const r of merged) {
    catCount.set(r.category, (catCount.get(r.category) ?? 0) + 1);
  }
  const topCategories = [...catCount.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([category, count]) => ({ category, count }));

  // Score and select most relevant lessons
  const scored = merged.map(r => {
    let score = 0;
    // Unresolved = more relevant
    if (r.status === LessonStatus.OPEN || r.status === LessonStatus.ACKNOWLEDGED) score += 5;
    // Same phase = high relevance
    if (r.phase_id === input.phase_id) score += 3;
    // Same role = medium relevance
    if (r.role_id === input.role_id) score += 2;
    // BLOCKER severity = pay attention
    if (r.severity === "BLOCKER") score += 2;
    // LOGIC_ERROR and CONSTRAINT_VIOLATION are most actionable for reviewers
    if (r.category === LessonCategory.LOGIC_ERROR) score += 1;
    if (r.category === LessonCategory.CONSTRAINT_VIOLATION) score += 1;
    return { record: r, score };
  });

  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, maxLessons);

  // Build advisory items
  const relevantLessons: AdvisoryItem[] = top.map(({ record: r, score }) => ({
    lesson_id: r.lesson_id,
    category: r.category,
    severity: r.severity,
    symptom: r.symptom,
    resolution: r.resolution,
    tags: r.tags,
    occurred_at: r.timestamp,
    relevance_reason: buildRelevanceReason(r, input, score),
  }));

  // Build summary
  const summary = buildAdvisorySummary(
    input.phase_id,
    merged.length,
    unresolved.length,
    topCategories,
    relevantLessons,
  );

  return {
    phase_id: input.phase_id,
    total_historical: merged.length,
    unresolved_count: unresolved.length,
    top_categories: topCategories,
    relevant_lessons: relevantLessons,
    summary,
  };
}

// ── Quality Report Section ───────────────────────────────────────────────────

/** Input for generating a quality report knowledge section. */
export interface QualitySectionInput {
  /** Phase being reported on */
  phase_id: string;
  /** Role being evaluated */
  role_id?: string;
}

/**
 * Generate a "Historical Defect Analysis" section for quality reports.
 *
 * Provides statistics and patterns that R07 can include in quality reports
 * to show how current quality compares to historical trends.
 *
 * @param ledger - The KnowledgeLedger instance
 * @param input - Quality report context
 * @returns A markdown-formatted section ready for inclusion in quality reports
 */
export function generateQualitySection(
  ledger: KnowledgeLedger,
  input: QualitySectionInput,
): string {
  const stats = ledger.getStatistics();

  // Phase-specific stats
  const phaseStats = stats.by_phase.find(p => p.phase_id === input.phase_id);
  const phaseLessons = input.phase_id
    ? ledger.query({ phase_id: input.phase_id, limit: 100 })
    : [];

  const openPhase = phaseLessons.filter(
    r => r.status === LessonStatus.OPEN || r.status === LessonStatus.ACKNOWLEDGED,
  );
  const resolvedPhase = phaseLessons.filter(r => r.status === LessonStatus.RESOLVED);

  // Category breakdown for this phase
  const phaseCatCount = new Map<LessonCategory, number>();
  for (const r of phaseLessons) {
    phaseCatCount.set(r.category, (phaseCatCount.get(r.category) ?? 0) + 1);
  }

  const lines: string[] = [
    "## 历史缺陷分析（Knowledge Ledger）",
    "",
    `> 数据来源: \`.ai/lessons/lessons.jsonl\` | 总记录: ${stats.total} | 未解决: ${stats.open} | 已解决: ${stats.resolved}`,
    "",
  ];

  // Phase-specific
  if (input.phase_id) {
    lines.push(`### 阶段 ${input.phase_id} 历史缺陷统计`);
    lines.push("");
    lines.push(`| 指标 | 数值 |`);
    lines.push(`|------|------|`);
    lines.push(`| 历史缺陷总数 | ${phaseLessons.length} |`);
    lines.push(`| 未解决 | ${openPhase.length} |`);
    lines.push(`| 已解决 | ${resolvedPhase.length} |`);
    lines.push(`| BLOCKER 级别 | ${phaseStats?.blocker_count ?? 0} |`);
    lines.push(`| WARNING 级别 | ${phaseStats?.warning_count ?? 0} |`);
    lines.push("");

    if (phaseCatCount.size > 0) {
      lines.push("#### 缺陷类别分布");
      lines.push("");
      lines.push("| 类别 | 数量 |");
      lines.push("|------|------|");
      for (const [cat, count] of [...phaseCatCount.entries()].sort((a, b) => b[1] - a[1])) {
        lines.push(`| ${cat} | ${count} |`);
      }
      lines.push("");
    }
  }

  // Global summary
  lines.push("### 全局缺陷类别分布");
  lines.push("");
  lines.push("| 类别 | 总数 | 已解决 | 未解决 |");
  lines.push("|------|------|--------|--------|");
  for (const cs of stats.by_category) {
    lines.push(`| ${cs.category} | ${cs.count} | ${cs.resolved} | ${cs.open} |`);
  }
  lines.push("");

  // Repeat defect warning
  const topCategory = stats.by_category[0];
  if (topCategory && topCategory.count > 0) {
    lines.push("### ⚠️ 重复缺陷预警");
    lines.push("");
    lines.push(`最高频缺陷类别: **${topCategory.category}**（${topCategory.count} 次）`);
    if (topCategory.open > 0) {
      lines.push(`仍有 **${topCategory.open}** 条未解决，建议优先处理。`);
    }
    lines.push("");
  }

  // Recent unresolved
  const unresolvedLessons = ledger.query({ status: LessonStatus.OPEN, limit: 5 });
  if (unresolvedLessons.length > 0) {
    lines.push("### 最近未解决的经验教训");
    lines.push("");
    for (const r of unresolvedLessons) {
      lines.push(`- **${r.lesson_id}** [${r.category}] ${r.symptom.substring(0, 100)}`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildRelevanceReason(
  r: LessonRecord,
  input: PreReviewInput,
  score: number,
): string {
  const reasons: string[] = [];
  if (r.phase_id === input.phase_id) reasons.push("同阶段");
  if (r.role_id === input.role_id) reasons.push("同角色");
  if (r.status === LessonStatus.OPEN || r.status === LessonStatus.ACKNOWLEDGED) {
    reasons.push("未解决");
  }
  if (r.severity === "BLOCKER") reasons.push("曾阻塞");
  if (r.resolution) reasons.push("有修复记录");
  return reasons.join("、") || `相关性评分: ${score}`;
}

function buildAdvisorySummary(
  phaseId: string,
  total: number,
  unresolved: number,
  topCategories: Array<{ category: LessonCategory; count: number }>,
  relevant: AdvisoryItem[],
): string {
  const parts: string[] = [
    `## 📋 评审前历史教训提醒`,
    "",
    `阶段 **${phaseId}** 历史累计 **${total}** 条经验记录，其中 **${unresolved}** 条尚未解决。`,
    "",
  ];

  if (topCategories.length > 0) {
    const topCatNames = topCategories.slice(0, 3).map(c => c.category).join("、");
    parts.push(`历史高频缺陷类别: ${topCatNames}`);
    parts.push("");
  }

  if (relevant.length > 0) {
    parts.push("### 建议重点关注的类似历史问题：");
    parts.push("");
    for (const item of relevant) {
      const statusIcon = item.resolution ? "✅" : "⚠️";
      parts.push(`- ${statusIcon} **${item.category}** — ${item.symptom.substring(0, 120)}`);
      parts.push(`  - 相关原因: ${item.relevance_reason}`);
      if (item.resolution) {
        parts.push(`  - 修复方式: ${item.resolution.substring(0, 100)}`);
      }
    }
    parts.push("");
  } else {
    parts.push("该阶段暂无历史缺陷记录。");
    parts.push("");
  }

  parts.push("> 💡 以上信息来自知识沉淀账本，仅供评审时参考。评审结论仍需基于当前代码的独立判断。");
  parts.push("");

  return parts.join("\n");
}
