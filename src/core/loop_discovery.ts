/**
 * loop_discovery.ts — Loop Discovery Decision Gate
 *
 * Aligned with Better Harness's Loop Discovery model: decides whether
 * repeated or schedulable engineering work exists and which durable
 * surface should own it. It is a routing gate, not the owner of session
 * mining, skill design, hook design, or automation wiring.
 *
 * Ten evidence gates must be mostly concrete before a durable loop is
 * recommended. Missing evidence yields `needs_more_evidence` — never
 * promote a loop from file age, line count, churn, or counts alone.
 *
 * Core principle (borrowed from Better Harness):
 *   Configured assets prove presence only.
 *   Observed behavior proves use.
 */

import type { LessonRecord } from "../types/lesson.js";

// ── Types ────────────────────────────────────────────────────────────────────

/** The ten evidence gates from Better Harness Loop Discovery. */
export type DiscoveryGateId =
  | "repeated_intent"
  | "existing_coverage"
  | "stable_input"
  | "repeatable_procedure"
  | "verification"
  | "stop_condition"
  | "safety_boundary"
  | "state_contract"
  | "observability_contract"
  | "evaluation_contract";

/** Gate labels for reader-facing output. */
export const DISCOVERY_GATE_LABELS: Record<DiscoveryGateId, string> = {
  repeated_intent: "重复意图",
  existing_coverage: "现有覆盖",
  stable_input: "稳定输入",
  repeatable_procedure: "可重复流程",
  verification: "验证方式",
  stop_condition: "停止条件",
  safety_boundary: "安全边界",
  state_contract: "状态契约",
  observability_contract: "可观测性契约",
  evaluation_contract: "评估契约",
};

/** Evidence strength for a single gate. */
export type GateEvidenceStrength = "concrete" | "partial" | "missing";

/** Result of a single gate evaluation. */
export interface GateEvaluation {
  gate: DiscoveryGateId;
  label: string;
  /** Evidence strength observed for this gate. */
  strength: GateEvidenceStrength;
  /** What evidence was found (or what is missing). */
  evidence: string;
}

/** The runtime-fit classification for a candidate loop. */
export type RuntimeFit =
  | "workflow"
  | "agent"
  | "evaluator_optimizer"
  | "scheduled_background"
  | "human_gated"
  | "skill_shaped"
  | "not_a_loop";

/** The decision outcome of a Loop Discovery. */
export type DiscoveryDecision =
  | "covered"
  | "create_skill"
  | "extend_skill"
  | "automation"
  | "hook_rule"
  | "script"
  | "command"
  | "custom_agent"
  | "mcp_backed_loop"
  | "skip"
  | "needs_more_evidence";

/** A durable surface that could own the loop. */
export type DurableOwner =
  | "existing_surface"
  | "skill"
  | "automation"
  | "hook"
  | "rule"
  | "script"
  | "command"
  | "custom_agent"
  | "mcp"
  | "none";

/** Full Loop Discovery result. */
export interface LoopDiscoveryResult {
  /** Candidate loop name/description. */
  candidate: string;
  /** Decision gate outcome. */
  decision: DiscoveryDecision;
  /** Proposed durable owner. */
  proposed_owner: DurableOwner;
  /** Runtime fit classification. */
  runtime_fit: RuntimeFit;
  /** Per-gate evaluations. */
  gates: GateEvaluation[];
  /** Number of gates with concrete evidence. */
  concrete_gate_count: number;
  /** Missing evidence summary. */
  missing_evidence: string[];
  /** Suggested handoff surface (e.g. file path, skill name). */
  handoff: string;
  /** Reasoning summary (one paragraph). */
  reasoning: string;
}

/** Input describing a candidate loop. */
export interface LoopCandidateInput {
  /** Candidate loop name/description. */
  candidate: string;
  /** Repeated user intents or prompt clusters (≥2 similar asks). */
  repeated_intents: string[];
  /** Existing coverage evidence (skills/hooks/scripts/rules that already cover it). */
  existing_coverage?: string[];
  /** Stable input context (diffs, logs, reports, manifests, validation output). */
  stable_inputs?: string[];
  /** Whether the procedure steps are reusable rather than fresh investigation. */
  procedure_reusable: boolean;
  /** Verification route (check, report, patch, review result, command). */
  verification?: string;
  /** Stop condition (state, score, count, result, human decision). */
  stop_condition?: string;
  /** Safety boundary description (permissions, secrets, external actions). */
  safety_boundary?: string;
  /** State contract (replayable input, checkpoint, session, artifact). */
  state_contract?: string;
  /** Observability contract (logs, traces, run directories, review artifacts). */
  observability_contract?: string;
  /** Evaluation contract (automated checks, LLM/human review, regression fixtures). */
  evaluation_contract?: string;
  /** Whether this is a one-off task (→ skip). */
  is_one_off?: boolean;
  /** Whether this is too broad, sensitive, or speculative (→ skip). */
  skip_reason?: string;
  /** Suggested runtime fit. */
  runtime_fit?: RuntimeFit;
  /** Suggested owner (handoff target). */
  suggested_owner?: DurableOwner;
}

// ── LoopDiscovery ────────────────────────────────────────────────────────────

/**
 * Loop Discovery decision gate.
 *
 * Evaluates a candidate loop against ten evidence gates and returns a
 * routing decision. Never promotes a loop from counts or file age alone.
 */
export class LoopDiscovery {
  /**
   * Evaluate a candidate loop.
   *
   * @param input - The candidate loop evidence.
   * @returns A {@link LoopDiscoveryResult} with decision and gate details.
   */
  discover(input: LoopCandidateInput): LoopDiscoveryResult {
    const gates = this.evaluateGates(input);
    const concreteCount = gates.filter(g => g.strength === "concrete").length;
    const missing = gates
      .filter(g => g.strength !== "concrete")
      .map(g => `${g.label}: ${g.evidence}`);

    // Skip rules
    if (input.is_one_off) {
      return this.buildResult(input, "skip", "none", missing, concreteCount, gates,
        "一次性任务，不构成循环。");
    }
    if (input.skip_reason) {
      return this.buildResult(input, "skip", "none", missing, concreteCount, gates,
        `跳过原因: ${input.skip_reason}`);
    }

    // Decision gate: most answers concrete (≥8 of 10)
    const decisionGatePassed = concreteCount >= 8;

    // Repeated intent is a hard prerequisite
    const repeatedConcrete = gates.find(g => g.gate === "repeated_intent")?.strength === "concrete";

    if (!repeatedConcrete) {
      return this.buildResult(input, "needs_more_evidence", "none", missing, concreteCount, gates,
        "缺少重复意图证据：至少需要两个相似请求，或一个高成本/高风险且可能重复的任务。");
    }

    if (!decisionGatePassed) {
      return this.buildResult(input, "needs_more_evidence", "none", missing, concreteCount, gates,
        `证据门通过 ${concreteCount}/10，不足 8/10。缺失证据: ${missing.slice(0, 4).join("; ")}`);
    }

    // Decide owner
    const owner = this.decideOwner(input, gates);
    const decision = this.decisionForOwner(owner);
    const handoff = this.handoffForOwner(owner, input.candidate);

    return this.buildResult(input, decision, owner, missing, concreteCount, gates,
      `循环成立（${concreteCount}/10 门通过），建议由 ${owner} 承载，交接面: ${handoff}`);
  }

  /**
   * Convenience method: detect a learning loop from knowledge ledger lessons.
   *
   * Two or more lessons sharing the same category + overlapping tags form a
   * repeated-intent signature. This mirrors Better Harness's
   * `repeated-rediscovery` and `recurring-correction` patterns.
   *
   * @param lessons - Lessons from the knowledge ledger.
   * @param candidateName - Name for the candidate loop.
   * @returns A LoopDiscoveryResult.
   */
  discoverFromLessons(
    lessons: LessonRecord[],
    candidateName: string,
  ): LoopDiscoveryResult {
    // Group lessons by category
    const byCategory = new Map<string, LessonRecord[]>();
    for (const lesson of lessons) {
      const list = byCategory.get(lesson.category) ?? [];
      list.push(lesson);
      byCategory.set(lesson.category, list);
    }

    // Find categories with ≥2 lessons AND tag-overlap signature
    // (repeated intent requires a shared signature, not just a category)
    const repeatedCategories: [string, LessonRecord[]][] = [];
    for (const [category, list] of byCategory) {
      if (list.length < 2) continue;
      // Negative control: same category alone is NOT a repeated signature.
      // Require at least one shared tag between any two lessons
      // (Better Harness "recurring-correction" needs semantically
      // equivalent corrections, not mere co-occurrence).
      let hasSharedSignature = false;
      outer: for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          if (list[i].tags.some(t => list[j].tags.includes(t))) {
            hasSharedSignature = true;
            break outer;
          }
        }
      }
      if (hasSharedSignature) repeatedCategories.push([category, list]);
    }
    repeatedCategories.sort((a, b) => b[1].length - a[1].length);

    if (repeatedCategories.length === 0) {
      // Negative control: single lessons, or lessons without a shared
      // signature, must NOT produce a loop with auto-filled evidence.
      return this.discover({
        candidate: candidateName,
        repeated_intents: [],
        procedure_reusable: false,
        // Explicitly signal missing evidence on every gate
        verification: undefined,
        stop_condition: undefined,
        safety_boundary: undefined,
        state_contract: undefined,
        observability_contract: undefined,
        evaluation_contract: undefined,
      });
    }

    const [topCategory, topLessons] = repeatedCategories[0];
    const repeatedIntents = topLessons.map(l => l.symptom);
    const stableInputs = topLessons.map(l => l.error_message);

    return this.discover({
      candidate: `${candidateName} (${topCategory})`,
      repeated_intents: repeatedIntents,
      stable_inputs: stableInputs,
      procedure_reusable: true,
      verification: "知识账本记录已闭环（RESOLVED）且无重复复发",
      stop_condition: "连续 N 个任务无同类缺陷复发",
      safety_boundary: "只读分析知识账本，不修改任何代码",
      state_contract: "lessons.jsonl 链式哈希账本，可追溯",
      observability_contract: "知识账本记录 phase_id/role_id/tags，可回溯",
      evaluation_contract: "对比修复前后的同类缺陷复发率",
      runtime_fit: "workflow",
      suggested_owner: "hook",
    });
  }

  // ── Private helpers ────────────────────────────────────────────────────

  private evaluateGates(input: LoopCandidateInput): GateEvaluation[] {
    return [
      this.evalGate("repeated_intent",
        input.repeated_intents.length >= 2
          ? `发现 ${input.repeated_intents.length} 个相似请求`
          : input.repeated_intents.length === 1
            ? "仅 1 个请求（不足 2 个，除非高成本/高风险）"
            : "未提供重复请求证据"),
      this.evalGate("existing_coverage",
        input.existing_coverage && input.existing_coverage.length > 0
          ? `现有覆盖: ${input.existing_coverage.join(", ")}`
          : "未发现现有覆盖，或未提供覆盖检查证据"),
      this.evalGate("stable_input",
        input.stable_inputs && input.stable_inputs.length >= 2
          ? `发现 ${input.stable_inputs.length} 个稳定输入样本`
          : input.stable_inputs?.length === 1
            ? "仅 1 个稳定输入（不足）"
            : "未提供稳定输入证据"),
      this.evalGate("repeatable_procedure",
        input.procedure_reusable
          ? "流程步骤可复用（非一次性调查）"
          : "流程步骤每次都需要全新调查"),
      this.evalGate("verification",
        input.verification
          ? input.verification
          : "未提供验证方式"),
      this.evalGate("stop_condition",
        input.stop_condition
          ? input.stop_condition
          : "未提供停止条件"),
      this.evalGate("safety_boundary",
        input.safety_boundary
          ? input.safety_boundary
          : "未说明权限/机密/外部操作边界"),
      this.evalGate("state_contract",
        input.state_contract
          ? input.state_contract
          : "未说明暂停/多轮运行时的状态契约"),
      this.evalGate("observability_contract",
        input.observability_contract
          ? input.observability_contract
          : "未说明日志/追踪/运行目录契约"),
      this.evalGate("evaluation_contract",
        input.evaluation_contract
          ? input.evaluation_contract
          : "未说明自动化检查/回归夹具/对比标准"),
    ];
  }

  private evalGate(gate: DiscoveryGateId, evidence: string): GateEvaluation {
    // Heuristic: evidence strings that start with "未" or "不足" or "无" or
    // contain explicit missing markers indicate missing/partial strength.
    let strength: GateEvidenceStrength = "concrete";
    if (evidence.startsWith("未") || evidence.startsWith("无") || evidence.startsWith("仅")) {
      strength = "missing";
    } else if (evidence.includes("（不足）") || evidence.includes("不足 2")) {
      strength = "partial";
    }
    return { gate, label: DISCOVERY_GATE_LABELS[gate], strength, evidence };
  }

  private decideOwner(
    input: LoopCandidateInput,
    gates: GateEvaluation[],
  ): DurableOwner {
    if (input.suggested_owner) return input.suggested_owner;

    // Prefer the smallest durable owner
    const coverageGate = gates.find(g => g.gate === "existing_coverage");
    if (coverageGate && coverageGate.strength === "concrete") {
      return "existing_surface";
    }

    const fit = input.runtime_fit ?? "workflow";
    switch (fit) {
      case "workflow":
        return "hook";
      case "agent":
        return "custom_agent";
      case "evaluator_optimizer":
        return "automation";
      case "scheduled_background":
        return "automation";
      case "human_gated":
        return "rule";
      case "skill_shaped":
        return "skill";
      default:
        return "none";
    }
  }

  private decisionForOwner(owner: DurableOwner): DiscoveryDecision {
    switch (owner) {
      case "existing_surface": return "covered";
      case "skill": return "create_skill";
      case "automation": return "automation";
      case "hook": return "hook_rule";
      case "rule": return "hook_rule";
      case "script": return "script";
      case "command": return "command";
      case "custom_agent": return "custom_agent";
      case "mcp": return "mcp_backed_loop";
      default: return "needs_more_evidence";
    }
  }

  private handoffForOwner(owner: DurableOwner, candidate: string): string {
    const slug = candidate.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    switch (owner) {
      case "skill": return `.qoder/skills/${slug}/SKILL.md`;
      case "hook": return `.ai/hooks/${slug}.js`;
      case "rule": return `.ai/rules/${slug}.md`;
      case "script": return `scripts/${slug}.mjs`;
      case "command": return `CLI 命令: loop ${slug}`;
      case "custom_agent": return `agents/${slug}/AGENT.md`;
      case "automation": return `.ai/automation/${slug}.yaml`;
      case "mcp": return `MCP 工具: ${slug}`;
      case "existing_surface": return "已有承载面，引用即可";
      default: return "无（证据不足）";
    }
  }

  private buildResult(
    input: LoopCandidateInput,
    decision: DiscoveryDecision,
    owner: DurableOwner,
    missing: string[],
    concreteCount: number,
    gates: GateEvaluation[],
    reasoning: string,
  ): LoopDiscoveryResult {
    return {
      candidate: input.candidate,
      decision,
      proposed_owner: owner,
      runtime_fit: input.runtime_fit ?? (decision === "skip" ? "not_a_loop" : "workflow"),
      gates,
      concrete_gate_count: concreteCount,
      missing_evidence: missing,
      handoff: this.handoffForOwner(owner, input.candidate),
      reasoning,
    };
  }
}
