import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { KnowledgeLedger } from '../src/core/knowledge_ledger.js';
import {
  generatePreReviewAdvisory,
  generateQualitySection,
} from '../src/core/review_advisor.js';
import { LessonCategory, LessonStatus } from '../src/types/lesson.js';

// ── Helpers ────────────────────────────────────────────────────────

function makeLesson(ledger: KnowledgeLedger, overrides: Record<string, unknown> = {}) {
  return ledger.capture({
    phase_id: (overrides.phase_id as string) ?? "S4-implementation",
    role_id: (overrides.role_id as string) ?? "R06",
    category: (overrides.category as LessonCategory) ?? LessonCategory.LOGIC_ERROR,
    severity: ((overrides.severity as "BLOCKER" | "WARNING")) ?? "BLOCKER",
    symptom: (overrides.symptom as string) ?? "Test symptom",
    error_message: (overrides.error_message as string) ?? "Test error",
    tags: (overrides.tags as string[]) ?? ["test"],
  });
}

// ── generatePreReviewAdvisory ──────────────────────────────────────

describe('generatePreReviewAdvisory', () => {
  let tmpDir: string;
  let ledger: KnowledgeLedger;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'review-advisor-test-'));
    ledger = new KnowledgeLedger(join(tmpDir, 'lessons.jsonl'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  it('空账本返回空结果', () => {
    const advisory = generatePreReviewAdvisory(ledger, {
      phase_id: "S4-implementation",
      role_id: "R06",
    });
    expect(advisory.total_historical).toBe(0);
    expect(advisory.relevant_lessons).toHaveLength(0);
    expect(advisory.summary).toContain("暂无历史缺陷记录");
  });

  it('找到同阶段的经验教训', () => {
    makeLesson(ledger, { phase_id: "S4-implementation", category: LessonCategory.LOGIC_ERROR });
    makeLesson(ledger, { phase_id: "S4-implementation", category: LessonCategory.DESIGN_FLAW });
    makeLesson(ledger, { phase_id: "S5-quality", category: LessonCategory.CONSTRAINT_VIOLATION });

    const advisory = generatePreReviewAdvisory(ledger, {
      phase_id: "S4-implementation",
      role_id: "R06",
    });

    expect(advisory.total_historical).toBeGreaterThanOrEqual(2);
    expect(advisory.relevant_lessons.length).toBeGreaterThan(0);
  });

  it('包含 top_categories', () => {
    makeLesson(ledger, { phase_id: "S4-implementation", category: LessonCategory.LOGIC_ERROR });
    makeLesson(ledger, { phase_id: "S4-implementation", category: LessonCategory.LOGIC_ERROR });
    makeLesson(ledger, { phase_id: "S4-implementation", category: LessonCategory.DESIGN_FLAW });

    const advisory = generatePreReviewAdvisory(ledger, {
      phase_id: "S4-implementation",
      role_id: "R06",
    });

    expect(advisory.top_categories.length).toBeGreaterThan(0);
    const topCat = advisory.top_categories[0];
    expect(topCat.category).toBe(LessonCategory.LOGIC_ERROR);
    expect(topCat.count).toBeGreaterThanOrEqual(2);
  });

  it('未解决的问题评分更高', () => {
    makeLesson(ledger, {
      phase_id: "S4-implementation",
      category: LessonCategory.LOGIC_ERROR,
    });
    // Default is OPEN

    const advisory = generatePreReviewAdvisory(ledger, {
      phase_id: "S4-implementation",
      role_id: "R06",
      max_lessons: 3,
    });

    const unresolvedItems = advisory.relevant_lessons.filter(
      l => l.symptom.includes("Test symptom"),
    );
    expect(unresolvedItems.length).toBeGreaterThan(0);
  });

  it('max_lessons 限制返回数量', () => {
    for (let i = 0; i < 10; i++) {
      makeLesson(ledger, { phase_id: "S4-implementation", symptom: `Issue ${i}` });
    }

    const advisory = generatePreReviewAdvisory(ledger, {
      phase_id: "S4-implementation",
      role_id: "R06",
      max_lessons: 3,
    });

    expect(advisory.relevant_lessons.length).toBeLessThanOrEqual(3);
  });
});

// ── generateQualitySection ─────────────────────────────────────────

describe('generateQualitySection', () => {
  let tmpDir: string;
  let ledger: KnowledgeLedger;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'quality-section-test-'));
    ledger = new KnowledgeLedger(join(tmpDir, 'lessons.jsonl'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  it('空账本生成最小报告', () => {
    const section = generateQualitySection(ledger, {
      phase_id: "S4-implementation",
    });
    expect(section).toContain("历史缺陷分析");
    expect(section).toContain("总记录: 0");
  });

  it('包含阶段统计', () => {
    makeLesson(ledger, {
      phase_id: "S4-implementation",
      category: LessonCategory.LOGIC_ERROR,
      severity: "BLOCKER",
    });
    makeLesson(ledger, {
      phase_id: "S4-implementation",
      category: LessonCategory.DESIGN_FLAW,
      severity: "WARNING",
    });

    const section = generateQualitySection(ledger, {
      phase_id: "S4-implementation",
    });

    expect(section).toContain("S4-implementation");
    expect(section).toContain("BLOCKER");
    expect(section).toContain("WARNING");
  });

  it('包含重复缺陷预警', () => {
    makeLesson(ledger, { category: LessonCategory.LOGIC_ERROR });
    makeLesson(ledger, { category: LessonCategory.LOGIC_ERROR });

    const section = generateQualitySection(ledger, {
      phase_id: "S4-implementation",
    });

    expect(section).toContain("重复缺陷预警");
  });

  it('包含最近未解决教训列表', () => {
    makeLesson(ledger, { symptom: "Null reference bug" });
    makeLesson(ledger, { symptom: "Timeout issue" });

    const section = generateQualitySection(ledger, {
      phase_id: "S4-implementation",
    });

    expect(section).toContain("最近未解决的经验教训");
  });
});
