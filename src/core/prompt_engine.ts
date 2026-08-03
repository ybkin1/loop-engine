/**
 * prompt_engine.ts — Four-Quadrant Prompt Engine
 *
 * Automatically generates contextual four-quadrant prompts based on:
 * - Current role (R01-R11)
 * - Current phase
 * - Task context (user input)
 * - Knowledge ledger lessons
 *
 * This module is called automatically by:
 * 1. role_context.ts — when generating subagent context (automatic)
 * 2. loop_prompt MCP tool — when user wants a ready-to-use prompt
 * 3. loop prompt CLI command — same as above via CLI
 *
 * The user never needs to remember how to write four-quadrant prompts.
 */

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

// ── Types ──────────────────────────────────────────────

export interface PromptContext {
  /** Role ID (R01-R11) */
  role_id?: string;
  /** Current phase (e.g. S1, S4-implementation) */
  phase_id?: string;
  /** What the user wants to do */
  task_description?: string;
  /** What the user already knows / has figured out */
  known_info?: string;
  /** What the user explicitly doesn't know */
  known_gaps?: string;
  /** Constraints (time, resources, tech, etc.) */
  constraints?: string;
  /** User's experience level on this task */
  experience_level?: string;
  /** Output mode: "subagent" for role context injection, "user" for copy-paste prompt */
  mode: "subagent" | "user" | "compact";
}

export interface PromptResult {
  /** The generated prompt text */
  prompt: string;
  /** Which quadrants are emphasized */
  active_quadrants: string[];
  /** Estimated token count */
  estimated_tokens: number;
  /** Mode used */
  mode: string;
}

// ── Role Quadrant Configurations ──────────────────────

interface RoleQuadrantConfig {
  /** Role display name */
  name: string;
  /** Primary quadrants to emphasize */
  primary: string[];
  /** Secondary quadrants */
  secondary: string[];
  /** Role-specific guidance text */
  guidance: string;
  /** Specific questions this role should ask */
  key_questions: string[];
}

const ROLE_QUADRANT_CONFIG: Record<string, RoleQuadrantConfig> = {
  R01: {
    name: "产品经理",
    primary: ["Q2", "Q3", "Q4"],
    secondary: ["Q1"],
    guidance: "你是产品经理。重点从用户模糊描述中定位认知缺口，用四象限做需求澄清。",
    key_questions: [
      "用户真正想解决什么问题？（区分'说的'和'要的'）",
      "有哪些需求维度用户可能完全没考虑到？",
      "用户是否有'看到才知道对不对'的隐性标准？",
    ],
  },
  R02: {
    name: "项目经理",
    primary: ["Q1", "Q3"],
    secondary: ["Q2"],
    guidance: "你是项目经理。重点确认计划约束，扫描遗漏的依赖和风险。",
    key_questions: [
      "任务依赖关系是否完整？",
      "有哪些风险用户可能没意识到？",
      "关键路径上的瓶颈是什么？",
    ],
  },
  R03: {
    name: "交付经理",
    primary: ["Q1", "Q3"],
    secondary: ["Q2"],
    guidance: "你是交付经理。重点确认交付标准，检查用户未意识到的发布风险。",
    key_questions: [
      "交付物完整性是否达标？",
      "回滚方案是否就绪？",
      "监控和告警是否配置？",
    ],
  },
  R04: {
    name: "系统架构师",
    primary: ["Q3", "Q2"],
    secondary: ["Q1", "Q4"],
    guidance: "你是系统架构师。重点扫描技术盲点，补充用户不懂的技术约束。",
    key_questions: [
      "模块边界是否清晰？有没有循环依赖？",
      "非功能需求（性能/安全/可用性）是否覆盖？",
      "有哪些技术债用户可能没意识到？",
    ],
  },
  R05: {
    name: "模块架构师",
    primary: ["Q1", "Q3"],
    secondary: ["Q2"],
    guidance: "你是模块架构师。重点确认接口规格，检查遗漏的边界条件。",
    key_questions: [
      "函数签名和前置/后置条件是否完整？",
      "异常契约是否覆盖所有路径？",
      "接口是否足够清晰让开发无歧义实现？",
    ],
  },
  R06: {
    name: "开发工程师",
    primary: ["Q1", "Q3"],
    secondary: ["Q2"],
    guidance: "你是开发工程师。重点确认实现规格，检查遗漏的边界条件和错误处理。",
    key_questions: [
      "接口契约是否足够清晰让我无歧义实现？",
      "边界条件和错误处理是否完整？",
      "是否有架构偏差需要报告？",
    ],
  },
  R07: {
    name: "质量工程师",
    primary: ["Q3"],
    secondary: ["Q1", "Q2"],
    guidance: "你是质量工程师。重点发现用户没意识到的质量风险面。",
    key_questions: [
      "P0 缺陷数是否为 0？",
      "测试覆盖率是否达标？",
      "回归测试是否执行？",
    ],
  },
  R08: {
    name: "安全工程师",
    primary: ["Q3"],
    secondary: ["Q1", "Q2"],
    guidance: "你是安全工程师。重点发现用户没意识到的安全风险面。",
    key_questions: [
      "是否存在 Critical/High 漏洞？",
      "是否有硬编码密钥或注入面？",
      "权限是否最小化？",
    ],
  },
  R09: {
    name: "独立评审员",
    primary: ["Q3"],
    secondary: ["Q1", "Q2"],
    guidance: "你是独立评审员。盲点扫描是评审的核心价值。从新鲜视角检查遗漏。",
    key_questions: [
      "P0/P1 缺陷是否清零？",
      "实现是否符合架构设计？",
      "是否存在安全漏洞或架构偏离？",
    ],
  },
  R10: {
    name: "运维工程师",
    primary: ["Q1", "Q3"],
    secondary: ["Q2"],
    guidance: "你是运维工程师。重点确认部署约束，检查运维盲点。",
    key_questions: [
      "构建是否可重复？",
      "部署是否可回滚？",
      "监控告警是否就绪？",
    ],
  },
  R11: {
    name: "编排器",
    primary: ["Q1", "Q2", "Q3", "Q4"],
    secondary: [],
    guidance: "你是编排器。在激活角色前，先对用户任务做四象限分类，将分类结果传递给下游角色。",
    key_questions: [
      "当前状态是什么？",
      "下一步应该激活哪个角色？",
      "交接物是否完整？",
    ],
  },
};

// ── Quadrant Descriptions ─────────────────────────────

const QUADRANT_DESCRIPTIONS: Record<string, { name: string; instruction: string }> = {
  Q1: {
    name: "已知的已知",
    instruction: "用户明确给出的信息，直接执行，不重复询问。",
  },
  Q2: {
    name: "已知的未知",
    instruction: "用户明确表示不熟悉的领域，围绕缺口提问（最多3个关键问题），充当老师角色。",
  },
  Q3: {
    name: "未知的未知",
    instruction: "用户可能没意识到的重要变量，主动列出盲点及其对结果的影响。",
  },
  Q4: {
    name: "未知的已知",
    instruction: "用户可能有但说不清的标准，提供多方案/原型供选择，帮助用户把隐性标准试出来。",
  },
};

// ── Core Engine ───────────────────────────────────────

/**
 * Generate a four-quadrant prompt based on context.
 * This is the main entry point.
 */
export function generatePrompt(ctx: PromptContext): PromptResult {
  switch (ctx.mode) {
    case "subagent":
      return generateSubagentPrompt(ctx);
    case "user":
      return generateUserPrompt(ctx);
    case "compact":
      return generateCompactPrompt(ctx);
    default:
      return generateSubagentPrompt(ctx);
  }
}

// ── Subagent Mode ─────────────────────────────────────

function generateSubagentPrompt(ctx: PromptContext): PromptResult {
  const roleId = ctx.role_id ?? "R11";
  const config = ROLE_QUADRANT_CONFIG[roleId] ?? ROLE_QUADRANT_CONFIG["R11"];
  const lines: string[] = [];

  lines.push("## 四象限认知协议 (Four-Quadrant Cognitive Protocol)");
  lines.push("");
  lines.push("在执行本任务前，请先完成四象限认知定位：");
  lines.push("");

  // List all quadrants with emphasis markers
  for (const [key, desc] of Object.entries(QUADRANT_DESCRIPTIONS)) {
    const isPrimary = config.primary.includes(key);
    const marker = isPrimary ? "⭐" : "  ";
    lines.push(`${marker} **${key} ${desc.name}**：${desc.instruction}`);
  }

  lines.push("");
  lines.push("**执行原则**：");
  lines.push("- 不要只按字面要求生成结果，同步运用四象限分析");
  lines.push("- 若缺失信息会显著改变结果，最多提出 3 个关键问题");
  lines.push("- 若不影响推进，明确你的合理假设，先完成探索版本");
  lines.push("- 执行后解释你的决策过程，让用户确认理解");
  lines.push("");

  // Role-specific guidance
  lines.push(`> **${roleId} ${config.name}指引**：${config.guidance}`);
  lines.push("");

  // Key questions for this role
  if (config.key_questions.length > 0) {
    lines.push("**关键提问清单**（优先检查）：");
    for (const q of config.key_questions) {
      lines.push(`- ${q}`);
    }
    lines.push("");
  }

  // Phase context if available
  if (ctx.phase_id) {
    lines.push(`> 当前阶段：${ctx.phase_id}`);
    lines.push("");
  }

  const prompt = lines.join("\n");
  return {
    prompt,
    active_quadrants: [...config.primary, ...config.secondary],
    estimated_tokens: Math.ceil(prompt.length / 4),
    mode: "subagent",
  };
}

// ── User Mode ─────────────────────────────────────────

function generateUserPrompt(ctx: PromptContext): PromptResult {
  const lines: string[] = [];

  lines.push("## 任务描述");
  lines.push(ctx.task_description ?? "[请描述你要做什么]");
  lines.push("");

  lines.push("## 我的起点");
  lines.push(`- 我的经验水平：${ctx.experience_level ?? "[在这个任务上的经验程度]"}`);
  lines.push(`- 我已经想到的：${ctx.known_info ?? "[你目前掌握的信息]"}`);
  lines.push(`- 我明确不熟悉的：${ctx.known_gaps ?? "[你清楚自己不懂的部分]"}`);
  lines.push(`- 我的限制条件：${ctx.constraints ?? "[时间/资源/技术等现实约束]"}`);
  lines.push("");

  lines.push("## 四象限协作指令");
  lines.push("");
  lines.push("执行本任务时，不要只按字面要求生成结果，请同步运用以下四象限：");
  lines.push("");

  lines.push("**一、共同已知（Q1）**");
  lines.push("先确认任务目标、已有背景、交付标准和明确边界。");
  lines.push("信息充分时直接执行，不要重复询问。");
  lines.push("");

  lines.push("**二、我的未知，你的已知（Q2）**");
  lines.push("识别可能只存在于我脑中的真实语境、审美偏好、判断标准和现实限制。");
  lines.push("若缺失信息会显著改变结果，最多提出 3 个关键问题。");
  lines.push("若不影响推进，则明确你的合理假设，先完成探索版本。");
  lines.push("");

  lines.push("**三、未知的未知（Q3 — 盲点扫描）**");
  lines.push("主动补充我可能没考虑到的知识、方法、风险和替代路径。");
  lines.push("不要局限于我的原始方案。");
  lines.push("如果我的前提可能错误，请直接指出并给出更优建议及取舍依据。");
  lines.push("");

  lines.push("**四、共同未知（Q4 — 原型试探）**");
  lines.push("识别无法仅靠现有信息确定的问题，把它们转化为可验证的假设。");
  lines.push("必要时设计最小实验：说明要改变的单一变量、成功/失败信号、以及后续需要回收的数据。");
  lines.push("先给出差异足够大的 2-3 个方向/原型，我来选择。");
  lines.push("");

  lines.push("## 执行要求");
  lines.push("- 执行前先给我一份：盲点清单 + 执行计划 + 原型（如需要）");
  lines.push("- 执行中记录偏离计划的情况和你做的替代决策");
  lines.push("- 执行后解释你的完整决策过程，不要只给结论");

  // If role is specified, add role-specific section
  if (ctx.role_id) {
    const config = ROLE_QUADRANT_CONFIG[ctx.role_id];
    if (config) {
      lines.push("");
      lines.push(`## ${ctx.role_id} ${config.name}视角补充`);
      lines.push(`重点象限：${config.primary.join(" + ")}`);
      lines.push("");
      lines.push("**关键提问**：");
      for (const q of config.key_questions) {
        lines.push(`- ${q}`);
      }
    }
  }

  const prompt = lines.join("\n");
  return {
    prompt,
    active_quadrants: ["Q1", "Q2", "Q3", "Q4"],
    estimated_tokens: Math.ceil(prompt.length / 4),
    mode: "user",
  };
}

// ── Compact Mode ──────────────────────────────────────

function generateCompactPrompt(ctx: PromptContext): PromptResult {
  const lines: string[] = [];

  lines.push(`我要做 ${ctx.task_description ?? "[任务]"}。`);
  if (ctx.known_info) lines.push(`我已经知道 ${ctx.known_info}。`);
  if (ctx.known_gaps) lines.push(`我不懂 ${ctx.known_gaps}。`);
  lines.push("");
  lines.push("在动手之前：");
  lines.push("1. 我有没有遗漏什么重要变量？（盲点扫描）");
  lines.push("2. 有哪些地方你不确定我到底要什么？（隐性标准）→ 先给我 2-3 个方向让我选");
  lines.push("3. 如果你最多只能问我 3 个问题，问什么？（知识缺口）");
  lines.push("");
  lines.push("然后给我执行计划，再动手。");

  const prompt = lines.join("\n");
  return {
    prompt,
    active_quadrants: ["Q2", "Q3", "Q4"],
    estimated_tokens: Math.ceil(prompt.length / 4),
    mode: "compact",
  };
}

// ── Template Loader ───────────────────────────────────

/**
 * Load the four-quadrant template file from .ai/prompt-templates/.
 */
export function loadQuadrantTemplate(projectRoot: string): string | null {
  const templatePath = join(projectRoot, ".ai", "prompt-templates", "four-quadrants.md");
  if (!existsSync(templatePath)) return null;
  try {
    return readFileSync(templatePath, "utf-8");
  } catch {
    return null;
  }
}

/**
 * Get role quadrant config for external use.
 */
export function getRoleQuadrantConfig(roleId: string): RoleQuadrantConfig | null {
  return ROLE_QUADRANT_CONFIG[roleId] ?? null;
}
