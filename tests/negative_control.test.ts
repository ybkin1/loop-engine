/**
 * negative_control.test.ts — Negative control tests
 *
 * Aligned with Better Harness's Learning Loop Patterns: every pattern has a
 * negative control that must NOT trigger a candidate. These tests verify that
 * the Loop Discovery gate and KnowledgeLedger heuristics do not over-trigger
 * on weak evidence.
 *
 * Negative controls here:
 * 1. LoopDiscovery: repeated edits/reads alone must NOT yield a loop decision.
 * 2. LoopDiscovery: file age / counts alone must NOT yield a loop decision.
 * 3. KnowledgeLedger.suggestCategory: unrelated failures must NOT be
 *    classified as the same category via false keyword matches.
 * 4. KnowledgeLedger.resolve: a fix marks pending_no_later_window (not
 *    verified) — same-window validation proves repair state, not effectiveness.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { LoopDiscovery } from "../src/core/loop_discovery.js";
import { KnowledgeLedger } from "../src/core/knowledge_ledger.js";
import { LessonCategory, LessonStatus } from "../src/types/lesson.js";

// ── LoopDiscovery negative controls ─────────────────────────────────────────

describe("LoopDiscovery negative controls", () => {
  const discovery = new LoopDiscovery();

  it("重复编辑或读取次数 alone 不构成循环（repeated-rediscovery 负面控制）", () => {
    // Negative control: many edits/reads but no repeated intent evidence
    const result = discovery.discover({
      candidate: "hot-file-refactor",
      repeated_intents: [], // no repeated user asks
      stable_inputs: ["file A edited 50 times", "file B read 30 times"],
      procedure_reusable: true,
    });

    expect(result.decision).toBe("needs_more_evidence");
    expect(result.proposed_owner).toBe("none");
    // Repeated intent gate must be missing
    const intentGate = result.gates.find(g => g.gate === "repeated_intent");
    expect(intentGate?.strength).toBe("missing");
  });

  it("文件年龄/行数/churn alone 不构成循环（counts are not findings）", () => {
    const result = discovery.discover({
      candidate: "stale-docs-cleanup",
      repeated_intents: [],
      stable_inputs: [], // no actual input samples
      procedure_reusable: false,
      verification: "docs are old (2 years)",
    });

    expect(result.decision).toBe("needs_more_evidence");
    // Stop condition missing too
    const stopGate = result.gates.find(g => g.gate === "stop_condition");
    expect(stopGate?.strength).toBe("missing");
  });

  it("单次请求（即使高成本说明）在无证据时仍返回 needs_more_evidence", () => {
    const result = discovery.discover({
      candidate: "one-off-migration",
      repeated_intents: ["migrate legacy module once"],
      procedure_reusable: false,
      verification: "migration script exists",
    });

    // 1 intent + missing gates → needs_more_evidence, not skip (one-off flag not set)
    expect(result.decision).toBe("needs_more_evidence");
    const intentGate = result.gates.find(g => g.gate === "repeated_intent");
    expect(intentGate?.strength).not.toBe("concrete");
  });

  it("显式标记一次性任务 → skip，且不产生 owner", () => {
    const result = discovery.discover({
      candidate: "rename-variable",
      repeated_intents: ["rename a variable once"],
      procedure_reusable: false,
      is_one_off: true,
    });

    expect(result.decision).toBe("skip");
    expect(result.proposed_owner).toBe("none");
    expect(result.runtime_fit).toBe("not_a_loop");
  });

  it("两个相似课程但不共享语义特征时不构成重复（recurring-correction 负面控制）", () => {
    // Negative control: two lessons in the same category but with NO tag
    // overlap and unrelated error messages — the repeated-intent signature
    // is weak, so the decision gate must stay conservative.
    const lessons = [
      {
        lesson_id: "lesson-001",
        seq: 1,
        chain_hash: "a",
        prev_chain_hash: "0",
        timestamp: "2026-01-01T00:00:00.000Z",
        phase_id: "S4-implementation",
        role_id: "R06",
        category: LessonCategory.LOGIC_ERROR,
        severity: "BLOCKER" as const,
        symptom: "Null reference in payment module",
        error_message: "TypeError: cannot read 'id' of undefined",
        status: LessonStatus.OPEN,
        tags: ["payment", "null-check"],
      },
      {
        lesson_id: "lesson-002",
        seq: 2,
        chain_hash: "b",
        prev_chain_hash: "a",
        timestamp: "2026-01-02T00:00:00.000Z",
        phase_id: "S4-implementation",
        role_id: "R06",
        category: LessonCategory.LOGIC_ERROR,
        severity: "WARNING" as const,
        symptom: "Off-by-one in report pagination",
        error_message: "RangeError: Invalid array length",
        status: LessonStatus.OPEN,
        tags: ["reporting", "pagination"],
      },
    ];

    // DiscoverFromLessons groups by category, but the Loop Discovery gate
    // must still verify that the evidence is concrete. Without tag overlap
    // or shared signatures, the loop must NOT be promoted.
    const result = discovery.discoverFromLessons(lessons, "logic-error-loop");
    // Both lessons share only the category — this is weak evidence:
    // the gate must not certify a durable owner.
    expect(result.proposed_owner).toBe("none");
    expect(result.decision).toBe("needs_more_evidence");
  });
});

// ── KnowledgeLedger.suggestCategory negative controls ───────────────────────

describe("KnowledgeLedger.suggestCategory negative controls", () => {
  it("普通文本含 'c1' 子串不误判为 CONSTRAINT_VIOLATION", () => {
    // Negative control: "c1" appears in "process1" or "ac1d" but is not a
    // constraint ID reference.
    const result = KnowledgeLedger.suggestCategory("process1 failed to start");
    expect(result).not.toBe(LessonCategory.CONSTRAINT_VIOLATION);
  });

  it("'test' 出现但不含 fail/missing 不误判为 TEST_GAP", () => {
    const result = KnowledgeLedger.suggestCategory("added test coverage for new feature");
    expect(result).not.toBe(LessonCategory.TEST_GAP);
  });

  it("'role' 出现在业务词中不误判为 PROCESS_GAP", () => {
    const result = KnowledgeLedger.suggestCategory("role-based access control works");
    expect(result).not.toBe(LessonCategory.PROCESS_GAP);
  });

  it("无匹配关键词 → OTHER（保守分类）", () => {
    const result = KnowledgeLedger.suggestCategory("the widget glitched while scrolling");
    expect(result).toBe(LessonCategory.OTHER);
  });
});

// ── KnowledgeLedger longitudinal validation ─────────────────────────────────

describe("KnowledgeLedger longitudinal validation (negative control: repair ≠ effectiveness)", () => {
  let dir: string;
  let ledger: KnowledgeLedger;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "loop-negctrl-"));
    ledger = new KnowledgeLedger(join(dir, "lessons.jsonl"));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it("resolve() 后 validation_status 为 pending_no_later_window（同一窗口验证≠有效性）", () => {
    const lesson = ledger.capture({
      phase_id: "S4-implementation",
      role_id: "R06",
      category: LessonCategory.LOGIC_ERROR,
      severity: "BLOCKER",
      symptom: "async pipeline crash",
      error_message: "TypeError: undefined",
      tags: ["async"],
    });

    const resolved = ledger.resolve(lesson.lesson_id, "added null guard");
    expect(resolved?.status).toBe(LessonStatus.RESOLVED);
    // Negative control: same-window fix must NOT claim effectiveness
    expect(resolved?.validation_status).toBe("pending_no_later_window");
  });

  it("confirmValidation(verified) 需要外部可比证据引用", () => {
    const lesson = ledger.capture({
      phase_id: "S4-implementation",
      role_id: "R06",
      category: LessonCategory.CONSTRAINT_VIOLATION,
      severity: "WARNING",
      symptom: "gate C6 not met",
      error_message: "review missing",
      tags: ["review"],
    });
    ledger.resolve(lesson.lesson_id, "obtained review");

    const validated = ledger.confirmValidation(
      lesson.lesson_id,
      "verified",
      "task-T0098: comparable S4 exit without C6 violation",
    );
    expect(validated?.validation_status).toBe("verified");
    expect(validated?.validation_evidence_ref).toContain("T0098");
  });

  it("confirmValidation(regressed) 记录复发，可被 findPendingValidations 排除", () => {
    const lesson = ledger.capture({
      phase_id: "S2-architecture",
      role_id: "R04",
      category: LessonCategory.DESIGN_FLAW,
      severity: "WARNING",
      symptom: "circular dependency",
      error_message: "import cycle detected",
      tags: ["architecture"],
    });
    ledger.resolve(lesson.lesson_id, "split module");

    ledger.confirmValidation(lesson.lesson_id, "regressed", "task-T0101: cycle returned");

    const pending = ledger.findPendingValidations();
    // The lesson resolved→regressed, so it must NOT appear as pending
    expect(pending.some(l => l.lesson_id === lesson.lesson_id)).toBe(false);
    // But the lesson record itself should exist with regressed status
    const latest = ledger.get(lesson.lesson_id);
    expect(latest?.validation_status).toBe("regressed");
  });
});
