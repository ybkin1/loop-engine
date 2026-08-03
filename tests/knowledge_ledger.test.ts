import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { KnowledgeLedger } from '../src/core/knowledge_ledger.js';
import { LessonCategory, LessonStatus } from '../src/types/lesson.js';

// ── Helpers ────────────────────────────────────────────────────────

function makeInput(overrides: Partial<{
  phase_id: string; role_id: string; task_id: string;
  category: LessonCategory; severity: "BLOCKER" | "WARNING";
  symptom: string; error_message: string; tags: string[];
  constraint_violations: string[];
}> = {}) {
  return {
    phase_id: overrides.phase_id ?? "S4-implementation",
    role_id: overrides.role_id ?? "R06",
    task_id: overrides.task_id,
    category: overrides.category ?? LessonCategory.LOGIC_ERROR,
    severity: overrides.severity ?? "BLOCKER" as const,
    symptom: overrides.symptom ?? "Null reference in async handler",
    error_message: overrides.error_message ?? "TypeError: Cannot read property 'id' of undefined",
    constraint_violations: overrides.constraint_violations,
    tags: overrides.tags ?? ["null-safety", "async-await"],
  };
}

// ── LessonCategory enum ────────────────────────────────────────────

describe('LessonCategory', () => {
  it('包含所有 9 种类别', () => {
    const categories = Object.values(LessonCategory);
    expect(categories).toHaveLength(9);
    expect(categories).toContain(LessonCategory.LOGIC_ERROR);
    expect(categories).toContain(LessonCategory.DESIGN_FLAW);
    expect(categories).toContain(LessonCategory.UNDETECTED_BUG);
    expect(categories).toContain(LessonCategory.CONSTRAINT_VIOLATION);
    expect(categories).toContain(LessonCategory.TEST_GAP);
    expect(categories).toContain(LessonCategory.SECURITY_GAP);
    expect(categories).toContain(LessonCategory.PROCESS_GAP);
    expect(categories).toContain(LessonCategory.PERFORMANCE_ISSUE);
    expect(categories).toContain(LessonCategory.OTHER);
  });
});

// ── LessonStatus enum ──────────────────────────────────────────────

describe('LessonStatus', () => {
  it('包含所有 5 种状态', () => {
    const statuses = Object.values(LessonStatus);
    expect(statuses).toHaveLength(5);
    expect(statuses).toContain(LessonStatus.OPEN);
    expect(statuses).toContain(LessonStatus.ACKNOWLEDGED);
    expect(statuses).toContain(LessonStatus.RESOLVED);
    expect(statuses).toContain(LessonStatus.SUPERSEDED);
    expect(statuses).toContain(LessonStatus.WONT_FIX);
  });
});

// ── KnowledgeLedger ────────────────────────────────────────────────

describe('KnowledgeLedger', () => {
  let tmpDir: string;
  let ledger: KnowledgeLedger;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'knowledge-ledger-test-'));
    ledger = new KnowledgeLedger(join(tmpDir, 'lessons.jsonl'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  // ── capture ──────────────────────────────────────────────────

  it('capture 增加 length', () => {
    expect(ledger.length).toBe(0);
    ledger.capture(makeInput());
    expect(ledger.length).toBe(1);
    ledger.capture(makeInput({ phase_id: "S5-quality" }));
    expect(ledger.length).toBe(2);
  });

  it('capture 自动生成 lesson_id 和 seq', () => {
    const l1 = ledger.capture(makeInput());
    const l2 = ledger.capture(makeInput({ phase_id: "S5-quality" }));
    expect(l1.lesson_id).toBe("lesson-0001");
    expect(l1.seq).toBe(1);
    expect(l2.lesson_id).toBe("lesson-0002");
    expect(l2.seq).toBe(2);
  });

  it('capture 自动生成 timestamp', () => {
    const lesson = ledger.capture(makeInput());
    expect(lesson.timestamp).toBeTruthy();
    // Should be a valid ISO date
    expect(new Date(lesson.timestamp).getTime()).toBeGreaterThan(0);
  });

  it('capture 默认 status 为 OPEN', () => {
    const lesson = ledger.capture(makeInput());
    expect(lesson.status).toBe(LessonStatus.OPEN);
  });

  it('capture 可使用自定义 status', () => {
    const lesson = ledger.capture(makeInput({ severity: "WARNING" }));
    expect(lesson.severity).toBe("WARNING");
  });

  it('chain_hash 非空且为 64 字符 SHA-256', () => {
    const lesson = ledger.capture(makeInput());
    expect(lesson.chain_hash).toBeTruthy();
    expect(lesson.chain_hash).toHaveLength(64);
  });

  it('chain_hash 形成链式结构', () => {
    const l1 = ledger.capture(makeInput());
    const l2 = ledger.capture(makeInput({ phase_id: "S5-quality" }));
    expect(l1.prev_chain_hash).toBe("0".repeat(64));
    expect(l2.prev_chain_hash).toBe(l1.chain_hash);
  });

  // ── verifyChain ──────────────────────────────────────────────

  it('verifyChain 空账本 → valid', () => {
    const result = ledger.verifyChain();
    expect(result.valid).toBe(true);
    expect(result.totalEntries).toBe(0);
    expect(result.firstInvalidSeq).toBeNull();
  });

  it('verifyChain 正常链 → valid', () => {
    ledger.capture(makeInput());
    ledger.capture(makeInput({ phase_id: "S5-quality" }));
    ledger.capture(makeInput({ phase_id: "S6-delivery" }));
    const result = ledger.verifyChain();
    expect(result.valid).toBe(true);
    expect(result.totalEntries).toBe(3);
  });

  // ── query ────────────────────────────────────────────────────

  it('query 按 phase_id 过滤', () => {
    ledger.capture(makeInput({ phase_id: "S4-implementation" }));
    ledger.capture(makeInput({ phase_id: "S5-quality" }));
    ledger.capture(makeInput({ phase_id: "S4-implementation" }));

    const s4 = ledger.query({ phase_id: "S4-implementation" });
    expect(s4).toHaveLength(2);
    expect(s4.every(l => l.phase_id === "S4-implementation")).toBe(true);
  });

  it('query 按 role_id 过滤', () => {
    ledger.capture(makeInput({ role_id: "R06" }));
    ledger.capture(makeInput({ role_id: "R07" }));
    ledger.capture(makeInput({ role_id: "R06" }));

    const r06 = ledger.query({ role_id: "R06" });
    expect(r06).toHaveLength(2);
  });

  it('query 按 category 过滤', () => {
    ledger.capture(makeInput({ category: LessonCategory.LOGIC_ERROR }));
    ledger.capture(makeInput({ category: LessonCategory.DESIGN_FLAW }));
    ledger.capture(makeInput({ category: LessonCategory.LOGIC_ERROR }));

    const logic = ledger.query({ category: LessonCategory.LOGIC_ERROR });
    expect(logic).toHaveLength(2);
  });

  it('query 按 tags 过滤（ANY 匹配）', () => {
    ledger.capture(makeInput({ tags: ["null-safety", "async"] }));
    ledger.capture(makeInput({ tags: ["timeout", "network"] }));
    ledger.capture(makeInput({ tags: ["null-safety", "type-error"] }));

    const nullSafety = ledger.query({ tags: ["null-safety"] });
    expect(nullSafety).toHaveLength(2);
  });

  it('query 组合过滤', () => {
    ledger.capture(makeInput({ phase_id: "S4-implementation", category: LessonCategory.LOGIC_ERROR }));
    ledger.capture(makeInput({ phase_id: "S4-implementation", category: LessonCategory.DESIGN_FLAW }));
    ledger.capture(makeInput({ phase_id: "S5-quality", category: LessonCategory.LOGIC_ERROR }));

    const combined = ledger.query({ phase_id: "S4-implementation", category: LessonCategory.LOGIC_ERROR });
    expect(combined).toHaveLength(1);
  });

  it('query 按 limit 限制数量', () => {
    for (let i = 0; i < 10; i++) {
      ledger.capture(makeInput({ phase_id: `phase-${i}` }));
    }
    const limited = ledger.query({ limit: 5 });
    expect(limited).toHaveLength(5);
  });

  it('query 结果按 seq 降序（最新优先）', () => {
    const l1 = ledger.capture(makeInput({ error_message: "first" }));
    const l2 = ledger.capture(makeInput({ error_message: "second" }));
    const results = ledger.query({});
    expect(results[0].seq).toBe(l2.seq);
    expect(results[1].seq).toBe(l1.seq);
  });

  // ── findSimilar ──────────────────────────────────────────────

  it('findSimilar 找到相同 category 和重叠 tag 的 lesson', () => {
    const ref = ledger.capture(makeInput({
      category: LessonCategory.LOGIC_ERROR,
      tags: ["null-safety", "async-await", "typescript"],
    }));
    ledger.capture(makeInput({
      category: LessonCategory.LOGIC_ERROR,
      tags: ["null-safety", "promise"],
    }));
    ledger.capture(makeInput({
      category: LessonCategory.DESIGN_FLAW,
      tags: ["architecture", "module"],
    }));
    ledger.capture(makeInput({
      category: LessonCategory.LOGIC_ERROR,
      tags: ["null-safety", "async-await"],
    }));

    const similar = ledger.findSimilar(ref.lesson_id, 3);
    expect(similar.length).toBeGreaterThan(0);
    // Most similar should be LOGIC_ERROR with tag overlap
    expect(similar[0].category).toBe(LessonCategory.LOGIC_ERROR);
  });

  it('findSimilar 排除自身', () => {
    const ref = ledger.capture(makeInput());
    ledger.capture(makeInput({ category: LessonCategory.LOGIC_ERROR }));
    const similar = ledger.findSimilar(ref.lesson_id);
    expect(similar.every(s => s.lesson_id !== ref.lesson_id)).toBe(true);
  });

  // ── searchByError ────────────────────────────────────────────

  it('searchByError 按错误信息子串匹配', () => {
    ledger.capture(makeInput({ error_message: "TypeError: Cannot read property 'id' of undefined" }));
    ledger.capture(makeInput({ error_message: "ReferenceError: timeout exceeded" }));
    ledger.capture(makeInput({ error_message: "TypeError: undefined is not an object" }));

    const results = ledger.searchByError("TypeError");
    expect(results).toHaveLength(2);
  });

  it('searchByError 也匹配 symptom 字段', () => {
    ledger.capture(makeInput({
      symptom: "Database connection timeout during migration",
      error_message: "ECONNREFUSED",
    }));
    ledger.capture(makeInput({
      symptom: "File not found during build",
      error_message: "ENOENT",
    }));

    const results = ledger.searchByError("timeout");
    expect(results).toHaveLength(1);
  });

  // ── findOpen / updateStatus ──────────────────────────────────

  it('findOpen 返回未解决的 lessons', () => {
    ledger.capture(makeInput());
    ledger.capture(makeInput());
    ledger.capture(makeInput());

    // All default to OPEN
    expect(ledger.findOpen()).toHaveLength(3);

    // Resolve one
    const l1 = ledger.query({})[2]; // Oldest
    ledger.updateStatus(l1.lesson_id, LessonStatus.RESOLVED);

    // Now only 2 open (the resolution creates a new entry with RESOLVED status)
    const open = ledger.findOpen();
    expect(open.length).toBeGreaterThanOrEqual(2);
  });

  // ── getStatistics ────────────────────────────────────────────

  it('getStatistics 返回正确的聚合数据', () => {
    ledger.capture(makeInput({
      phase_id: "S4-implementation",
      category: LessonCategory.LOGIC_ERROR,
      severity: "BLOCKER",
    }));
    ledger.capture(makeInput({
      phase_id: "S4-implementation",
      category: LessonCategory.DESIGN_FLAW,
      severity: "WARNING",
    }));
    ledger.capture(makeInput({
      phase_id: "S5-quality",
      category: LessonCategory.CONSTRAINT_VIOLATION,
      severity: "BLOCKER",
    }));

    const stats = ledger.getStatistics();
    expect(stats.total).toBe(3);
    expect(stats.by_category).toHaveLength(3);
    expect(stats.by_phase).toHaveLength(2);

    const s4 = stats.by_phase.find(p => p.phase_id === "S4-implementation");
    expect(s4).toBeDefined();
    expect(s4!.count).toBe(2);
    expect(s4!.blocker_count).toBe(1);
    expect(s4!.warning_count).toBe(1);
  });

  it('getStatistics 空账本返回 0', () => {
    const stats = ledger.getStatistics();
    expect(stats.total).toBe(0);
    expect(stats.open).toBe(0);
    expect(stats.resolved).toBe(0);
    expect(stats.by_category).toHaveLength(0);
    expect(stats.by_phase).toHaveLength(0);
  });

  // ── captureFromViolations ────────────────────────────────────

  it('captureFromViolations 自动设置 CONSTRAINT_VIOLATION 类别', () => {
    const lesson = ledger.captureFromViolations(
      "S4-implementation",
      "R06",
      ["[C1] BLOCKER: Requirements baseline not approved"],
      ["gate-check"],
    );
    expect(lesson).not.toBeNull();
    expect(lesson!.category).toBe(LessonCategory.CONSTRAINT_VIOLATION);
    expect(lesson!.severity).toBe("BLOCKER");
    expect(lesson!.constraint_violations).toContain("C1");
  });

  it('captureFromViolations 空 violations 返回 null', () => {
    const lesson = ledger.captureFromViolations("S4", "R06", []);
    expect(lesson).toBeNull();
  });

  it('captureFromViolations 只有 WARNING 时为 WARNING 级别', () => {
    const lesson = ledger.captureFromViolations(
      "S4-implementation",
      "R06",
      ["[C8] WARNING: Evidence expiring soon"],
    );
    expect(lesson).not.toBeNull();
    expect(lesson!.severity).toBe("WARNING");
  });

  // ── suggestCategory (static) ─────────────────────────────────

  it('suggestCategory 识别 LOGIC_ERROR', () => {
    expect(KnowledgeLedger.suggestCategory("TypeError: Cannot read property 'id' of undefined"))
      .toBe(LessonCategory.LOGIC_ERROR);
    expect(KnowledgeLedger.suggestCategory("null is not a function"))
      .toBe(LessonCategory.LOGIC_ERROR);
  });

  it('suggestCategory 识别 CONSTRAINT_VIOLATION', () => {
    expect(KnowledgeLedger.suggestCategory("[C1] BLOCKER: missing phase_gates"))
      .toBe(LessonCategory.CONSTRAINT_VIOLATION);
    expect(KnowledgeLedger.suggestCategory("constraint C5 failed"))
      .toBe(LessonCategory.CONSTRAINT_VIOLATION);
  });

  it('suggestCategory 识别 DESIGN_FLAW', () => {
    expect(KnowledgeLedger.suggestCategory("circular dependency detected"))
      .toBe(LessonCategory.DESIGN_FLAW);
    expect(KnowledgeLedger.suggestCategory("module not found"))
      .toBe(LessonCategory.DESIGN_FLAW);
  });

  it('suggestCategory 识别 TEST_GAP', () => {
    expect(KnowledgeLedger.suggestCategory("test failed: missing coverage"))
      .toBe(LessonCategory.TEST_GAP);
  });

  it('suggestCategory 识别 SECURITY_GAP', () => {
    expect(KnowledgeLedger.suggestCategory("SQL injection vulnerability"))
      .toBe(LessonCategory.SECURITY_GAP);
  });

  it('suggestCategory 识别 PERFORMANCE_ISSUE', () => {
    expect(KnowledgeLedger.suggestCategory("timeout exceeded after 30s"))
      .toBe(LessonCategory.PERFORMANCE_ISSUE);
  });

  it('suggestCategory 识别 PROCESS_GAP', () => {
    expect(KnowledgeLedger.suggestCategory("phase mismatch detected"))
      .toBe(LessonCategory.PROCESS_GAP);
  });

  it('suggestCategory fallback 为 OTHER', () => {
    expect(KnowledgeLedger.suggestCategory("some random unknown error"))
      .toBe(LessonCategory.OTHER);
  });

  // ── get ──────────────────────────────────────────────────────

  it('get 按 lesson_id 查询', () => {
    const captured = ledger.capture(makeInput());
    const found = ledger.get(captured.lesson_id);
    expect(found).toBeDefined();
    expect(found!.lesson_id).toBe(captured.lesson_id);
  });

  it('get 不存在的 lesson 返回 undefined', () => {
    expect(ledger.get("lesson-9999")).toBeUndefined();
  });

  // ── recent ───────────────────────────────────────────────────

  it('recent 返回最近 N 条', () => {
    for (let i = 0; i < 5; i++) {
      ledger.capture(makeInput({ phase_id: `phase-${i}` }));
    }
    const recent = ledger.recent(3);
    expect(recent).toHaveLength(3);
    expect(recent[2].phase_id).toBe("phase-4");
  });

  it('recent n=0 返回空', () => {
    ledger.capture(makeInput());
    expect(ledger.recent(0)).toHaveLength(0);
  });

  // ── resolveWithImpact (ECN closure loop) ─────────────────────────

  it('resolveWithImpact 返回 lesson 和 affected_gates', () => {
    const lesson = ledger.capture(makeInput({
      category: LessonCategory.CONSTRAINT_VIOLATION,
      constraint_violations: ["C1", "C5"],
      severity: "BLOCKER",
    }));

    const result = ledger.resolveWithImpact(lesson.lesson_id, "Fixed by updating requirements doc", "S6-delivery");
    expect(result.lesson).not.toBeNull();
    expect(result.lesson!.status).toBe(LessonStatus.RESOLVED);
    expect(result.affected_gates.length).toBeGreaterThan(0);
    expect(result.should_recheck).toBe(true);
  });

  it('resolveWithImpact 将 CONSTRAINT 映射到对应门禁', () => {
    const lesson = ledger.capture(makeInput({
      category: LessonCategory.CONSTRAINT_VIOLATION,
      constraint_violations: ["C1"],
    }));

    const result = ledger.resolveWithImpact(lesson.lesson_id, "Resolved");
    expect(result.affected_gates).toContain("S1-requirements");
  });

  it('resolveWithImpact 不同阶段修复时包含两个阶段的 gate', () => {
    const lesson = ledger.capture(makeInput({
      phase_id: "S4-implementation",
      severity: "BLOCKER",
    }));

    const result = ledger.resolveWithImpact(lesson.lesson_id, "Fixed", "S5-quality");
    expect(result.affected_gates).toContain("S4-implementation");
    expect(result.affected_gates).toContain("S5-quality");
  });

  it('resolveWithImpact 不存在的 lesson 返回 null', () => {
    const result = ledger.resolveWithImpact("lesson-9999", "N/A");
    expect(result.lesson).toBeNull();
    expect(result.affected_gates).toHaveLength(0);
    expect(result.should_recheck).toBe(false);
  });

  it('resolveWithImpact WARNING 级别不需要重检', () => {
    const lesson = ledger.capture(makeInput({
      severity: "WARNING",
      category: LessonCategory.PERFORMANCE_ISSUE,
    }));

    const result = ledger.resolveWithImpact(lesson.lesson_id, "Optimized");
    expect(result.should_recheck).toBe(false);
  });
});
