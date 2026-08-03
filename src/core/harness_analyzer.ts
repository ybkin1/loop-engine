/**
 * harness_analyzer.ts — Self-Diagnosis Engine for Loop Engineering
 *
 * Inspired by Better Harness's five-dimension evaluation model.
 * Unlike Better Harness (which is a passive observer), this module
 * integrates with Loop's existing state machine, evidence system,
 * and knowledge ledger to produce an actionable health report.
 *
 * Core principle (borrowed from Better Harness):
 *   "Configuration exists" ≠ "Capability is effective"
 *   Only task-linked evidence proves a mechanism was actually used.
 *
 * Evidence-state model (aligned with Better Harness agent-work-loop):
 *   Present → Wired → Exercised → Outcome-supported
 *   Missing / Unobserved / Not applicable
 * Each state sets a score ceiling — a mechanism that merely exists
 * cannot score as high as one that was actually exercised.
 *
 * Five dimensions:
 *   1. Task Understanding — Are goals, context, and scope clear?
 *   2. Controlled Execution — Can the agent operate within boundaries?
 *   3. Change Verification — Are changes validated with evidence?
 *   4. Reliable Delivery — Is there verifiable proof of delivery?
 *   5. Learning Capture — Are lessons沉淀 and reused?
 */

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { resolve, join } from "node:path";
import { createHash } from "node:crypto";

// ── Types ────────────────────────────────────────────────────────────────────

/** Score for a single dimension (0–100). */
export type DimensionScore = number;

/** Severity of a finding. */
export type FindingSeverity = "critical" | "warning" | "info" | "passed";

/** A single actionable finding from the analysis. */
export interface Finding {
  /** Which dimension this finding belongs to. */
  dimension: DimensionName;
  /** Severity level. */
  severity: FindingSeverity;
  /** Human-readable title. */
  title: string;
  /** What's wrong or what's missing. */
  description: string;
  /** What evidence supports this finding (or "no evidence" if gap). */
  evidence: string;
  /** Concrete fix action. */
  fix_action: string;
}

/** The five evaluation dimensions. */
export type DimensionName =
  | "task_understanding"
  | "controlled_execution"
  | "change_verification"
  | "reliable_delivery"
  | "learning_capture";

/** Human-readable labels for dimensions. */
export const DIMENSION_LABELS: Record<DimensionName, string> = {
  task_understanding: "任务理解",
  controlled_execution: "可控执行",
  change_verification: "改动验证",
  reliable_delivery: "可靠交付",
  learning_capture: "经验沉淀",
};

/** Result for a single dimension. */
export interface DimensionResult {
  name: DimensionName;
  label: string;
  score: DimensionScore;
  findings: Finding[];
  /** Evidence items that contributed to this score. */
  evidence_items: EvidenceItem[];
  /**
   * Score ceiling imposed by the strongest evidence state.
   * Aligned with Better Harness: evidence limits score confidence.
   */
  ceiling: number;
  /** The evidence state that determined the ceiling. */
  ceiling_state: EvidenceState;
}

/**
 * Evidence state for a mechanism (aligned with Better Harness).
 *
 * Ordered by increasing proof strength. Each state sets a score ceiling:
 * - Missing / Unobserved / Not applicable → ceiling 59
 * - Present (mechanism or review contract exists) → ceiling 74
 * - Wired (task/trigger/owner route can reach it) → ceiling 84
 * - Exercised (a linked episode or inspection used it) → ceiling 94
 * - Outcome-supported (comparable later result) → ceiling 100
 */
export type EvidenceState =
  | "present"
  | "wired"
  | "exercised"
  | "outcome_supported"
  | "missing"
  | "unobserved"
  | "not_applicable";

/**
 * Score ceiling imposed by each evidence state.
 * A ceiling is not a score formula — it caps how high a dimension can score.
 */
export const EVIDENCE_STATE_CEILINGS: Record<EvidenceState, number> = {
  present: 74,
  wired: 84,
  exercised: 94,
  outcome_supported: 100,
  missing: 59,
  unobserved: 59,
  not_applicable: 59,
};

/**
 * Score ceiling for the Learning Capture dimension specifically,
 * which uses a distinct progression (35 floor, no zero).
 */
export const LEARNING_CAPTURE_CEILINGS: Record<EvidenceState, number> = {
  present: 74,
  wired: 84,
  exercised: 94,
  outcome_supported: 100,
  missing: 59,
  unobserved: 59,
  not_applicable: 59,
};

/**
 * Human-readable labels for evidence states.
 */
export const EVIDENCE_STATE_LABELS: Record<EvidenceState, string> = {
  present: "已配置",
  wired: "已接通",
  exercised: "已使用",
  outcome_supported: "已验证成效",
  missing: "缺失",
  unobserved: "未观察到",
  not_applicable: "不适用",
};

/** An evidence item discovered during analysis. */
export interface EvidenceItem {
  /** What was found. */
  type: string;
  /** Where it was found. */
  source: string;
  /**
   * Evidence state (seven-level model).
   * Legacy "configured" maps to "present", "executed" to "exercised",
   * "verified" to "outcome_supported".
   */
  proof_level: EvidenceState;
  /** Human-readable description. */
  description: string;
  /** When the mechanism was last exercised (optional, for longitudinal checks). */
  last_exercised_at?: string;
  /** Whether a comparable later result supports the claimed effect. */
  outcome_supported?: boolean;
}

/**
 * Score ceiling applied to a dimension based on its strongest evidence state.
 * Maps to Better Harness: Missing/Unobserved/NA → 59, Present → 74,
 * Wired → 84, Exercised → 94, Outcome-supported → 100.
 */
export function applyEvidenceCeiling(
  rawScore: number,
  evidenceItems: EvidenceItem[],
): { score: number; ceiling: number; ceiling_state: EvidenceState } {
  // Learning Capture has its own 35 floor semantics; caller handles that.
  if (evidenceItems.length === 0) {
    return { score: Math.min(rawScore, 59), ceiling: 59, ceiling_state: "unobserved" };
  }

  // Find the strongest evidence state present (by ceiling ordering)
  const stateOrder: EvidenceState[] = [
    "outcome_supported", "exercised", "wired", "present",
    "missing", "unobserved", "not_applicable",
  ];

  let ceilingState: EvidenceState = "unobserved";
  for (const state of stateOrder) {
    if (evidenceItems.some(e => e.proof_level === state)) {
      ceilingState = state;
      break;
    }
  }

  const ceiling = EVIDENCE_STATE_CEILINGS[ceilingState];
  return {
    score: Math.min(rawScore, ceiling),
    ceiling,
    ceiling_state: ceilingState,
  };
}

/** The full analysis report. */
export interface HarnessReport {
  /** When the analysis was performed. */
  timestamp: string;
  /** Project root that was analyzed. */
  project_root: string;
  /** Overall score (weighted average of dimensions). */
  overall_score: DimensionScore;
  /** Per-dimension results. */
  dimensions: DimensionResult[];
  /** All findings sorted by severity. */
  findings: Finding[];
  /** Summary of detected Loop assets. */
  assets: LoopAssets;
  /** Report integrity hash. */
  report_hash: string;
}

/** Detected Loop engineering assets. */
export interface LoopAssets {
  roles_defined: number;
  gates_defined: number;
  evidence_files: number;
  handoff_records: number;
  lessons_captured: number;
  skills_present: number;
  hooks_present: number;
  state_files: string[];
}

// ── HarnessAnalyzer ──────────────────────────────────────────────────────────

export class HarnessAnalyzer {
  private projectRoot: string;
  private aiDir: string;

  constructor(projectRoot: string) {
    this.projectRoot = resolve(projectRoot);
    this.aiDir = resolve(this.projectRoot, ".ai");
  }

  /**
   * Run a full five-dimension analysis and produce a report.
   *
   * This is the main entry point — analogous to running "/better-harness".
   */
  async analyze(): Promise<HarnessReport> {
    const dimensions: DimensionResult[] = [];

    dimensions.push(this.analyzeTaskUnderstanding());
    dimensions.push(this.analyzeControlledExecution());
    dimensions.push(this.analyzeChangeVerification());
    dimensions.push(this.analyzeReliableDelivery());
    dimensions.push(this.analyzeLearningCapture());

    const allFindings = dimensions.flatMap(d => d.findings);
    const assets = this.detectAssets();

    // Weighted average: execution and verification matter most
    const weights: Record<DimensionName, number> = {
      task_understanding: 0.15,
      controlled_execution: 0.25,
      change_verification: 0.25,
      reliable_delivery: 0.20,
      learning_capture: 0.15,
    };

    const overallScore = Math.round(
      dimensions.reduce(
        (sum, d) => sum + d.score * (weights[d.name] ?? 0.2),
        0,
      ),
    );

    const report: HarnessReport = {
      timestamp: new Date().toISOString(),
      project_root: this.projectRoot,
      overall_score: overallScore,
      dimensions,
      findings: this.sortFindings(allFindings),
      assets,
      report_hash: "",
    };

    report.report_hash = this.computeReportHash(report);
    return report;
  }

  // ── Dimension 1: Task Understanding ─────────────────────────────────────

  /**
   * Check if the agent understands the project, task origin, and scope.
   *
   * Evidence: PROJECT.md exists, state.yaml has current_task_id,
   * R01 (product manager) has produced requirements_doc evidence.
   */
  private analyzeTaskUnderstanding(): DimensionResult {
    const findings: Finding[] = [];
    const evidenceItems: EvidenceItem[] = [];
    let score = 0;

    // Check 1: PROJECT.md or project description exists
    const projectMd = this.fileExists(join(this.aiDir, "PROJECT.md"));
    if (projectMd) {
      score += 20;
      evidenceItems.push({
        type: "project_definition",
        source: ".ai/PROJECT.md",
        proof_level: "present",
        description: "项目定义文件存在",
      });
    } else {
      findings.push({
        dimension: "task_understanding",
        severity: "warning",
        title: "缺少项目定义文件",
        description: "PROJECT.md 不存在，Agent 可能缺少项目全局上下文",
        evidence: "未找到 .ai/PROJECT.md",
        fix_action: "创建 .ai/PROJECT.md，描述项目目标、技术栈和关键约束",
      });
    }

    // Check 2: state.yaml has task context
    const stateOk = this.checkStateHasTaskContext();
    if (stateOk) {
      score += 25;
      evidenceItems.push({
        type: "task_context",
        source: ".ai/state.yaml",
        proof_level: "present",
        description: "state.yaml 包含当前任务上下文",
      });
    } else {
      findings.push({
        dimension: "task_understanding",
        severity: "warning",
        title: "状态文件缺少任务上下文",
        description: "state.yaml 中 current_task_id 为空或缺失",
        evidence: "state.yaml current_task_id 未设置",
        fix_action: "运行 loop init 或手动设置 state.yaml 中的 current_task_id",
      });
    }

    // Check 3: Requirements evidence exists (R01 output)
    const reqEvidence = this.findEvidenceByType("requirements");
    if (reqEvidence) {
      score += 30;
      evidenceItems.push({
        type: "requirements_evidence",
        source: reqEvidence,
        proof_level: "exercised",
        description: "需求证据文件存在，R01 已产出",
      });
    } else {
      findings.push({
        dimension: "task_understanding",
        severity: "info",
        title: "未发现需求证据",
        description: "未找到与需求相关的证据文件，R01 可能尚未产出",
        evidence: "evidence/ 目录中无需求类型文件",
        fix_action: "在 S1-requirements 阶段确保 R01 产出需求文档并提交证据",
      });
    }

    // Check 4: ARCHITECTURE.md exists
    const archMd = this.fileExists(join(this.aiDir, "ARCHITECTURE.md"));
    if (archMd) {
      score += 25;
      evidenceItems.push({
        type: "architecture_doc",
        source: ".ai/ARCHITECTURE.md",
        proof_level: "present",
        description: "架构文档存在",
      });
    } else {
      findings.push({
        dimension: "task_understanding",
        severity: "info",
        title: "缺少架构文档",
        description: "ARCHITECTURE.md 不存在",
        evidence: "未找到 .ai/ARCHITECTURE.md",
        fix_action: "在 S2-architecture 阶段由 R04 产出架构文档",
      });
    }

    return {
      name: "task_understanding",
      label: DIMENSION_LABELS.task_understanding,
      findings,
      evidence_items: evidenceItems,
      ...applyEvidenceCeiling(score, evidenceItems),
    };
  }

  // ── Dimension 2: Controlled Execution ───────────────────────────────────

  /**
   * Check if execution happens within defined boundaries.
   *
   * Evidence: gates.yaml has gate definitions, state.yaml tracks phases,
   * hard constraints are defined, enforcement is active.
   */
  private analyzeControlledExecution(): DimensionResult {
    const findings: Finding[] = [];
    const evidenceItems: EvidenceItem[] = [];
    let score = 0;

    // Check 1: gates.yaml exists and has gate definitions
    const gatesCount = this.countGates();
    if (gatesCount > 0) {
      score += 25;
      evidenceItems.push({
        type: "gate_definitions",
        source: ".ai/gates.yaml",
        proof_level: "present",
        description: `gates.yaml 定义了 ${gatesCount} 个 Gate`,
      });
    } else {
      findings.push({
        dimension: "controlled_execution",
        severity: "critical",
        title: "无 Gate 定义",
        description: "gates.yaml 不存在或无 Gate 定义，阶段推进无门禁控制",
        evidence: "gates.yaml 缺失或为空",
        fix_action: "运行 loop init 生成默认 Gate 定义",
      });
    }

    // Check 2: State machine is tracking phases
    const phaseTracking = this.checkPhaseTracking();
    if (phaseTracking) {
      score += 25;
      evidenceItems.push({
        type: "phase_tracking",
        source: ".ai/state.yaml",
        proof_level: "exercised",
        description: "状态机正在追踪阶段进展",
      });
    } else {
      findings.push({
        dimension: "controlled_execution",
        severity: "warning",
        title: "阶段追踪不完整",
        description: "state.yaml 中 phases 数组为空或缺失",
        evidence: "state.yaml phases 未初始化",
        fix_action: "确保 loop init 正确初始化 phases 数组",
      });
    }

    // Check 3: Hard constraints file or module exists
    const constraintsExist = this.fileExists(
      resolve(this.projectRoot, "src/core/hard_constraints.ts"),
    );
    if (constraintsExist) {
      score += 20;
      evidenceItems.push({
        type: "hard_constraints",
        source: "src/core/hard_constraints.ts",
        proof_level: "present",
        description: "硬约束模块存在",
      });
    }

    // Check 4: Audit ledger is recording
    const auditLedgerExists = this.fileExists(
      join(this.aiDir, "audit_ledger.jsonl"),
    );
    if (auditLedgerExists) {
      const entries = this.countJsonlEntries(
        join(this.aiDir, "audit_ledger.jsonl"),
      );
      if (entries > 0) {
        score += 30;
        evidenceItems.push({
          type: "audit_trail",
          source: ".ai/audit_ledger.jsonl",
          proof_level: "exercised",
          description: `审计日志记录了 ${entries} 条操作`,
        });
      } else {
        score += 10;
        findings.push({
          dimension: "controlled_execution",
          severity: "info",
          title: "审计日志为空",
          description: "audit_ledger.jsonl 存在但无记录",
          evidence: "audit_ledger.jsonl 0 条记录",
          fix_action: "确保状态变更操作写入审计日志",
        });
      }
    } else {
      findings.push({
        dimension: "controlled_execution",
        severity: "warning",
        title: "缺少审计日志",
        description: "audit_ledger.jsonl 不存在，操作不可追溯",
        evidence: "未找到 .ai/audit_ledger.jsonl",
        fix_action: "初始化审计日志系统",
      });
    }

    return {
      name: "controlled_execution",
      label: DIMENSION_LABELS.controlled_execution,
      findings,
      evidence_items: evidenceItems,
      ...applyEvidenceCeiling(score, evidenceItems),
    };
  }

  // ── Dimension 3: Change Verification ────────────────────────────────────

  /**
   * Check if changes are validated with evidence (tests, lint, reviews).
   *
   * Evidence: evidence/ directory has test/review files,
   * freshness checks pass, compile gate exists.
   */
  private analyzeChangeVerification(): DimensionResult {
    const findings: Finding[] = [];
    const evidenceItems: EvidenceItem[] = [];
    let score = 0;

    // Check 1: Evidence directory has files
    const evidenceCount = this.countEvidenceFiles();
    if (evidenceCount > 0) {
      score += 25;
      evidenceItems.push({
        type: "evidence_files",
        source: ".ai/evidence/",
        proof_level: "exercised",
        description: `evidence/ 目录包含 ${evidenceCount} 个证据文件`,
      });
    } else {
      findings.push({
        dimension: "change_verification",
        severity: "critical",
        title: "无验证证据",
        description: "evidence/ 目录为空或不存在，没有任何变更验证证据",
        evidence: "evidence/ 目录无文件",
        fix_action: "在阶段执行过程中通过 loop evidence submit 提交验证证据",
      });
    }

    // Check 2: Test results exist as evidence
    const testEvidence = this.findEvidenceByType("test");
    if (testEvidence) {
      score += 25;
      evidenceItems.push({
        type: "test_evidence",
        source: testEvidence,
        proof_level: "outcome_supported",
        description: "测试结果证据存在",
      });
    } else {
      findings.push({
        dimension: "change_verification",
        severity: "warning",
        title: "缺少测试证据",
        description: "未找到测试相关的证据文件",
        evidence: "evidence/ 中无 test 类型文件",
        fix_action: "确保 R07（质量工程师）提交测试报告作为证据",
      });
    }

    // Check 3: Review evidence exists
    const reviewEvidence = this.findEvidenceByType("review");
    if (reviewEvidence) {
      score += 25;
      evidenceItems.push({
        type: "review_evidence",
        source: reviewEvidence,
        proof_level: "outcome_supported",
        description: "评审证据存在",
      });
    } else {
      findings.push({
        dimension: "change_verification",
        severity: "warning",
        title: "缺少评审证据",
        description: "未找到评审相关的证据文件",
        evidence: "evidence/ 中无 review 类型文件",
        fix_action: "确保 R09（独立评审员）提交评审报告作为证据",
      });
    }

    // Check 4: Knowledge ledger has entries (shows learning from failures)
    const lessonsExist = this.fileExists(
      join(this.aiDir, "lessons", "lessons.jsonl"),
    );
    if (lessonsExist) {
      const lessonCount = this.countJsonlEntries(
        join(this.aiDir, "lessons", "lessons.jsonl"),
      );
      if (lessonCount > 0) {
        score += 25;
        evidenceItems.push({
          type: "knowledge_ledger",
          source: ".ai/lessons/lessons.jsonl",
          proof_level: "exercised",
          description: `知识账本记录了 ${lessonCount} 条经验教训`,
        });
      }
    }

    return {
      name: "change_verification",
      label: DIMENSION_LABELS.change_verification,
      findings,
      evidence_items: evidenceItems,
      ...applyEvidenceCeiling(score, evidenceItems),
    };
  }

  // ── Dimension 4: Reliable Delivery ──────────────────────────────────────

  /**
   * Check if delivery has verifiable proof and rollback plans.
   *
   * Evidence: HANDOFF.md exists, delivery evidence, ops runbook.
   */
  private analyzeReliableDelivery(): DimensionResult {
    const findings: Finding[] = [];
    const evidenceItems: EvidenceItem[] = [];
    let score = 0;

    // Check 1: HANDOFF.md exists and has records
    const handoffPath = join(this.aiDir, "HANDOFF.md");
    const handoffExists = this.fileExists(handoffPath);
    if (handoffExists) {
      const handoffSize = this.getFileSize(handoffPath);
      if (handoffSize > 100) {
        score += 30;
        evidenceItems.push({
          type: "handoff_records",
          source: ".ai/HANDOFF.md",
          proof_level: "exercised",
          description: "交接记录文件存在且有内容",
        });
      } else {
        score += 10;
        findings.push({
          dimension: "reliable_delivery",
          severity: "info",
          title: "交接记录为空",
          description: "HANDOFF.md 存在但内容过少，可能无实际交接记录",
          evidence: "HANDOFF.md 文件过小",
          fix_action: "在角色交接时通过 loop handoff 记录交接物",
        });
      }
    } else {
      findings.push({
        dimension: "reliable_delivery",
        severity: "warning",
        title: "缺少交接记录",
        description: "HANDOFF.md 不存在，角色间交接不可追溯",
        evidence: "未找到 .ai/HANDOFF.md",
        fix_action: "使用 loop handoff 命令创建交接记录",
      });
    }

    // Check 2: Delivery evidence exists
    const deliveryEvidence = this.findEvidenceByType("delivery");
    if (deliveryEvidence) {
      score += 25;
      evidenceItems.push({
        type: "delivery_evidence",
        source: deliveryEvidence,
        proof_level: "outcome_supported",
        description: "交付证据存在",
      });
    }

    // Check 3: Registry has run records
    const runsRegistry = this.fileExists(
      join(this.projectRoot, "registry", "runs.yaml"),
    );
    if (runsRegistry) {
      score += 20;
      evidenceItems.push({
        type: "run_registry",
        source: "registry/runs.yaml",
        proof_level: "present",
        description: "运行注册表存在",
      });
    }

    // Check 4: Templates exist for delivery artifacts
    const templatesDir = resolve(this.projectRoot, "templates");
    if (this.dirExists(templatesDir)) {
      const templateFiles = this.listFiles(templatesDir);
      if (templateFiles.length > 0) {
        score += 25;
        evidenceItems.push({
          type: "delivery_templates",
          source: "templates/",
          proof_level: "present",
          description: `交付模板文件存在（${templateFiles.length} 个）`,
        });
      }
    }

    return {
      name: "reliable_delivery",
      label: DIMENSION_LABELS.reliable_delivery,
      findings,
      evidence_items: evidenceItems,
      ...applyEvidenceCeiling(score, evidenceItems),
    };
  }

  // ── Dimension 5: Learning Capture ───────────────────────────────────────

  /**
   * Check if lessons are captured and reused.
   *
   * Evidence: lessons.jsonl has entries, resolved lessons exist,
   * session restore is configured.
   */
  private analyzeLearningCapture(): DimensionResult {
    const findings: Finding[] = [];
    const evidenceItems: EvidenceItem[] = [];
    let score = 0;

    // Check 1: Knowledge ledger exists
    const ledgerPath = join(this.aiDir, "lessons", "lessons.jsonl");
    const ledgerExists = this.fileExists(ledgerPath);
    if (ledgerExists) {
      const count = this.countJsonlEntries(ledgerPath);
      if (count > 0) {
        score += 30;
        evidenceItems.push({
          type: "knowledge_ledger",
          source: ".ai/lessons/lessons.jsonl",
          proof_level: "exercised",
          description: `知识账本有 ${count} 条记录`,
        });

        // Check for resolved lessons
        const resolvedCount = this.countResolvedLessons(ledgerPath);
        if (resolvedCount > 0) {
          score += 20;
          evidenceItems.push({
            type: "resolved_lessons",
            source: ".ai/lessons/lessons.jsonl",
            proof_level: "outcome_supported",
            description: `${resolvedCount} 条经验已解决闭环`,
          });
        } else {
          findings.push({
            dimension: "learning_capture",
            severity: "warning",
            title: "经验未闭环",
            description: "知识账本有记录但无已解决的经验，学习回路未闭合",
            evidence: "lessons.jsonl 无 RESOLVED 状态记录",
            fix_action: "定期回顾知识账本，将已修复的问题标记为 RESOLVED",
          });
        }
      } else {
        findings.push({
          dimension: "learning_capture",
          severity: "info",
          title: "知识账本为空",
          description: "lessons.jsonl 存在但无记录",
          evidence: "lessons.jsonl 0 条记录",
          fix_action: "确保 PhaseExecutor 配置了 knowledge_ledger 以自动捕获失败教训",
        });
      }
    } else {
      findings.push({
        dimension: "learning_capture",
        severity: "warning",
        title: "缺少知识沉淀机制",
        description: "知识账本未初始化，失败经验无法沉淀",
        evidence: "未找到 .ai/lessons/lessons.jsonl",
        fix_action: "初始化 KnowledgeLedger 并配置到 PhaseExecutor",
      });
    }

    // Check 2: Skills directory has loop-related skills
    // 平台项目级 Skill 存储为 .qoder/skills/（或 .agents/skills/），兼容旧版顶层 skills/
    const skillsCandidates: Array<[string, string]> = [
      [resolve(this.projectRoot, ".qoder", "skills"), ".qoder/skills/"],
      [resolve(this.projectRoot, ".agents", "skills"), ".agents/skills/"],
      [resolve(this.projectRoot, "skills"), "skills/"],
    ];
    for (const [skillsDir, skillsSource] of skillsCandidates) {
      if (!this.dirExists(skillsDir)) continue;
      const skillDirs = this.listDirs(skillsDir);
      if (skillDirs.length > 0) {
        score += 25;
        evidenceItems.push({
          type: "skills",
          source: skillsSource,
          proof_level: "present",
          description: `${skillDirs.length} 个 Skill 已定义`,
        });
        break;
      }
    }

    // Check 3: Role contracts exist
    const rolesDir = resolve(this.projectRoot, "roles");
    if (this.dirExists(rolesDir)) {
      const roleFiles = this.listFiles(rolesDir).filter(f => f.endsWith(".md"));
      if (roleFiles.length > 0) {
        score += 25;
        evidenceItems.push({
          type: "role_contracts",
          source: "roles/",
          proof_level: "present",
          description: `${roleFiles.length} 个角色契约已定义`,
        });
      }
    }

    // Check 4: DECISIONS.md or PROGRESS.md exists (explicit knowledge)
    const decisionsExist = this.fileExists(join(this.aiDir, "DECISIONS.md"));
    const progressExist = this.fileExists(join(this.aiDir, "PROGRESS.md"));
    if (decisionsExist || progressExist) {
      score += 20;
      evidenceItems.push({
        type: "explicit_knowledge",
        source: decisionsExist ? ".ai/DECISIONS.md" : ".ai/PROGRESS.md",
        proof_level: "present",
        description: "显式知识文档存在",
      });
    }

    // Learning Capture uses a 35 floor: a bounded review never projects zero.
    const ceilingApplied = applyEvidenceCeiling(score, evidenceItems);
    const learningScore = Math.max(35, ceilingApplied.score);

    return {
      name: "learning_capture",
      label: DIMENSION_LABELS.learning_capture,
      score: learningScore,
      findings,
      evidence_items: evidenceItems,
      ceiling: ceilingApplied.ceiling,
      ceiling_state: ceilingApplied.ceiling_state,
    };
  }

  // ── Asset Detection ─────────────────────────────────────────────────────

  /**
   * Detect all Loop engineering assets in the project.
   */
  private detectAssets(): LoopAssets {
    const rolesDir = resolve(this.projectRoot, "roles");
    const skillsDir = resolve(this.projectRoot, "skills");
    const evidenceDir = join(this.aiDir, "evidence");

    return {
      roles_defined: this.dirExists(rolesDir)
        ? this.listFiles(rolesDir).filter(f => f.endsWith(".md")).length
        : 0,
      gates_defined: this.countGates(),
      evidence_files: this.countEvidenceFiles(),
      handoff_records: this.fileExists(join(this.aiDir, "HANDOFF.md")) ? 1 : 0,
      lessons_captured: this.fileExists(join(this.aiDir, "lessons", "lessons.jsonl"))
        ? this.countJsonlEntries(join(this.aiDir, "lessons", "lessons.jsonl"))
        : 0,
      skills_present: this.dirExists(skillsDir) ? this.listDirs(skillsDir).length : 0,
      hooks_present: this.countHooks(),
      state_files: this.detectStateFiles(),
    };
  }

  // ── File System Helpers ─────────────────────────────────────────────────

  private fileExists(path: string): boolean {
    try {
      return existsSync(path);
    } catch {
      return false;
    }
  }

  private dirExists(path: string): boolean {
    try {
      return existsSync(path) && statSync(path).isDirectory();
    } catch {
      return false;
    }
  }

  private getFileSize(path: string): number {
    try {
      return statSync(path).size;
    } catch {
      return 0;
    }
  }

  private listFiles(dir: string): string[] {
    try {
      return readdirSync(dir).filter(f => {
        try { return statSync(resolve(dir, f)).isFile(); } catch { return false; }
      });
    } catch {
      return [];
    }
  }

  private listDirs(dir: string): string[] {
    try {
      return readdirSync(dir).filter(f => {
        try { return statSync(resolve(dir, f)).isDirectory(); } catch { return false; }
      });
    } catch {
      return [];
    }
  }

  private countJsonlEntries(path: string): number {
    try {
      const raw = readFileSync(path, "utf-8");
      return raw.split("\n").filter(l => l.trim().length > 0).length;
    } catch {
      return 0;
    }
  }

  private countResolvedLessons(path: string): number {
    try {
      const raw = readFileSync(path, "utf-8");
      let count = 0;
      for (const line of raw.split("\n")) {
        if (line.includes('"RESOLVED"')) count++;
      }
      return count;
    } catch {
      return 0;
    }
  }

  private countGates(): number {
    const gatesPath = join(this.aiDir, "gates.yaml");
    if (!this.fileExists(gatesPath)) return 0;
    try {
      const raw = readFileSync(gatesPath, "utf-8");
      const matches = raw.match(/^\s*-?\s*gate_id:/gm);
      return matches ? matches.length : 0;
    } catch {
      return 0;
    }
  }

  private countEvidenceFiles(): number {
    const evidenceDir = join(this.aiDir, "evidence");
    if (!this.dirExists(evidenceDir)) return 0;
    return this.listFiles(evidenceDir).length;
  }

  private countHooks(): number {
    // Check for hook scripts in .ai/checkers/ and .ai/guards/
    let count = 0;
    for (const dir of ["checkers", "guards"]) {
      const hookDir = join(this.aiDir, dir);
      if (this.dirExists(hookDir)) {
        count += this.listFiles(hookDir).length;
      }
    }
    return count;
  }

  private detectStateFiles(): string[] {
    const candidates = [
      "state.yaml", "gates.yaml", "task_graph.yaml",
      "audit_ledger.jsonl", "HANDOFF.md",
    ];
    return candidates.filter(f => this.fileExists(join(this.aiDir, f)));
  }

  private findEvidenceByType(typeHint: string): string | null {
    const evidenceDir = join(this.aiDir, "evidence");
    if (!this.dirExists(evidenceDir)) return null;
    try {
      const files = this.listFiles(evidenceDir);
      const match = files.find(f => f.toLowerCase().includes(typeHint));
      return match ? resolve(evidenceDir, match) : null;
    } catch {
      return null;
    }
  }

  private checkStateHasTaskContext(): boolean {
    const statePath = join(this.aiDir, "state.yaml");
    if (!this.fileExists(statePath)) return false;
    try {
      const raw = readFileSync(statePath, "utf-8");
      return raw.includes("current_task_id") && !raw.includes("current_task_id: null");
    } catch {
      return false;
    }
  }

  private checkPhaseTracking(): boolean {
    const statePath = join(this.aiDir, "state.yaml");
    if (!this.fileExists(statePath)) return false;
    try {
      const raw = readFileSync(statePath, "utf-8");
      return raw.includes("phases:") && raw.includes("phase_id:");
    } catch {
      return false;
    }
  }

  // ── Report Utilities ────────────────────────────────────────────────────

  private sortFindings(findings: Finding[]): Finding[] {
    const severityOrder: Record<FindingSeverity, number> = {
      critical: 0,
      warning: 1,
      info: 2,
      passed: 3,
    };
    return findings.sort(
      (a, b) => (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3),
    );
  }

  private computeReportHash(report: HarnessReport): string {
    const hasher = createHash("sha256");
    hasher.update(report.timestamp);
    hasher.update(report.project_root);
    hasher.update(String(report.overall_score));
    for (const d of report.dimensions) {
      hasher.update(d.name);
      hasher.update(String(d.score));
    }
    return hasher.digest("hex");
  }

  /**
   * Format a report as Markdown for human/AI consumption.
   */
  static toMarkdown(report: HarnessReport): string {
    const lines: string[] = [];

    lines.push("# Loop Engineering Harness 健康报告");
    lines.push("");
    lines.push(`**生成时间**: ${report.timestamp}`);
    lines.push(`**项目路径**: ${report.project_root}`);
    lines.push(`**综合评分**: ${report.overall_score}/100`);
    lines.push(`**报告哈希**: ${report.report_hash.substring(0, 16)}...`);
    lines.push("");

    // Dimension scores
    lines.push("## 五维评分");
    lines.push("");
    for (const dim of report.dimensions) {
      const bar = "█".repeat(Math.round(dim.score / 5)) + "░".repeat(20 - Math.round(dim.score / 5));
      lines.push(`- **${dim.label}**: ${dim.score}/100 ${bar}`);
    }
    lines.push("");

    // Findings
    if (report.findings.length > 0) {
      lines.push("## 发现（按优先级排序）");
      lines.push("");
      for (const f of report.findings) {
        const icon = f.severity === "critical" ? "🔴" : f.severity === "warning" ? "🟡" : "🔵";
        lines.push(`### ${icon} ${f.title}`);
        lines.push(`- **维度**: ${DIMENSION_LABELS[f.dimension]}`);
        lines.push(`- **严重度**: ${f.severity}`);
        lines.push(`- **描述**: ${f.description}`);
        lines.push(`- **证据**: ${f.evidence}`);
        lines.push(`- **修复方案**: ${f.fix_action}`);
        lines.push("");
      }
    }

    // Assets
    lines.push("## 检测到的 Loop 资产");
    lines.push("");
    lines.push(`| 资产类型 | 数量 |`);
    lines.push(`|---------|------|`);
    lines.push(`| 角色契约 | ${report.assets.roles_defined} |`);
    lines.push(`| Gate 定义 | ${report.assets.gates_defined} |`);
    lines.push(`| 证据文件 | ${report.assets.evidence_files} |`);
    lines.push(`| 交接记录 | ${report.assets.handoff_records} |`);
    lines.push(`| 经验教训 | ${report.assets.lessons_captured} |`);
    lines.push(`| Skills | ${report.assets.skills_present} |`);
    lines.push(`| Hooks | ${report.assets.hooks_present} |`);
    lines.push(`| 状态文件 | ${report.assets.state_files.join(", ")} |`);
    lines.push("");

    return lines.join("\n");
  }
}
