/**
 * context_loader.ts — Progressive Context Loading
 *
 * Loads role-specific context progressively based on task complexity.
 * Simple tasks get minimal context (~200 tokens), complex tasks get
 * full three-layer architecture (~2600 tokens).
 *
 * Ported from ZCode loop_core/context_loader.py.
 */

import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

// ── Enums ────────────────────────────────────────────────────────────────────

/** Progressive loading levels — each tier adds more context. */
export enum LoadLevel {
  /** ~200 tokens — fixed stance only */
  MINIMAL = "MINIMAL",
  /** ~600 tokens — stance + thinking framework */
  STANDARD = "STANDARD",
  /** ~2600 tokens — all layers */
  FULL = "FULL",
}

// ── Interfaces ───────────────────────────────────────────────────────────────

/** Result of loading context for a role. */
export interface LoadedContext {
  role_id: string;
  level: LoadLevel;
  system_prompt: string;
  estimated_tokens: number;
  loaded_sections: string[];
}

/** A single section parsed from a Markdown document. */
export interface DocumentSection {
  title: string;
  level: number; // heading level (1 = #, 2 = ##, etc.)
  content: string;
  line_start: number;
  line_end: number;
}

/** Hierarchical index of a Markdown document. */
export interface DocumentIndex {
  doc_path: string;
  sections: DocumentSection[];
  total_lines: number;
  total_tokens: number;
}

// ── Constants ────────────────────────────────────────────────────────────────

/** Fixed one-stance descriptions per role (~30 tokens each). */
const ROLE_STANCES: Record<string, string> = {
  R01: "你是产品经理。从模糊需求中提炼清晰的产品定义。不决定技术方案。",
  R02: "你是项目经理。进度可控、依赖清晰、风险透明。不改变产品目标。",
  R03: "你是交付经理。判断交付物完整性、检查发布条件。不完整时拒绝上线。",
  R04: "你是系统架构师。像设计乐高一样设计软件。14项交付物缺一不可。不写实现代码。",
  R05: "你是模块架构师。将系统分解到组件/接口/类/函数级别。函数设计先于实现。",
  R06: "你是开发工程师。依据已批准设计实现代码。严格遵守规范。先写测试再写实现。",
  R07: "你是质量工程师。P0=0是交付最低门槛，不可谈判。",
  R08: "你是安全工程师。安全是底线不是功能。默认拒绝、最小权限、纵深防御。",
  R09: "你是独立代码评审员。六亲不认。P0/P1未清零不给PASS。",
  R10: "你是发布运维工程师。部署必须可重复、可回滚、可观测。",
  R11: "你是主控编排器。只编排、只维护事实，不替任何角色伪造结论。",
};

/** Generic thinking framework appended at STANDARD and above (~100 tokens). */
const THINKING_FRAMEWORK = `## 思考框架

1. **理解目标** — 明确本次任务的输入、约束与期望产出。
2. **拆解问题** — 将大任务分解为可独立验证的子步骤。
3. **逐项执行** — 按依赖顺序逐步完成，每步产出可追溯证据。
4. **自检交付** — 对照角色职责与完成标准，确认无遗漏。
5. **记录决策** — 所有关键判断写入审计日志，附理由。

> 原则：一次只做一件事，做完即验证，验证完再推进。`;

/** Internal-loop guide appended at FULL level (~200 tokens per role). */
const ROLE_LOOP_GUIDES: Record<string, string> = {
  R01: `### 内部循环
- 接收需求 → 拆解为用户故事 → 定义验收标准 → 输出 PRD。
- 每个故事必须有：who / what / why / acceptance criteria。
- 需求变更必须记录变更原因并通知下游角色。`,

  R02: `### 内部循环
- 收集各角色进度 → 识别阻塞与依赖 → 更新甘特图/看板。
- 风险必须量化（概率 × 影响）并给出缓解方案。
- 周报格式：已完成 / 进行中 / 阻塞 / 下一步。`,

  R03: `### 内部循环
- 逐项检查交付物清单 → 对照发布条件 → 出具交付报告。
- 任何一项未达标即拒绝发布，并列出缺失项。
- 交付报告需包含：版本号、变更摘要、测试结果、回滚方案。`,

  R04: `### 内部循环
- 分析需求 → 设计系统拓扑 → 定义接口契约 → 输出 14 项架构交付物。
- 每项交付物必须通过架构评审检查表。
- 技术选型需附 ADR（Architecture Decision Record）。`,

  R05: `### 内部循环
- 接收系统架构 → 拆解模块 → 定义组件/接口/类/函数。
- 函数签名先于实现，接口契约先于编码。
- 输出模块设计文档，包含依赖图与接口定义。`,

  R06: `### 内部循环
- 接收模块设计 → 编写测试 → 实现代码 → 自测通过。
- 代码必须遵循项目编码规范，含类型注解与文档注释。
- 提交前运行 lint + 单元测试，覆盖率不低于阈值。`,

  R07: `### 内部循环
- 制定测试计划 → 编写测试用例 → 执行测试 → 输出质量报告。
- P0 缺陷 = 阻塞发布，P1 缺陷 = 限期修复，P2 缺陷 = 计划修复。
- 测试报告需包含：通过率、覆盖率、缺陷分布。`,

  R08: `### 内部循环
- 威胁建模 → 安全审查 → 漏洞扫描 → 输出安全报告。
- 所有输入必须验证，所有输出必须编码，所有密钥必须轮换。
- 安全审查结果分为：阻断 / 警告 / 建议。`,

  R09: `### 内部循环
- 逐文件审查 → 标注问题 → 汇总评审报告。
- 问题分级：P0（必须修复）/ P1（强烈建议）/ P2（建议改进）。
- 评审报告需包含：审查范围、问题列表、最终结论（PASS/FAIL）。`,

  R10: `### 内部循环
- 编写部署脚本 → 验证回滚 → 配置监控 → 执行发布。
- 部署三步验证：部署成功 → 健康检查通过 → 监控指标正常。
- 每次发布必须有回滚方案，回滚方案必须经过验证。`,

  R11: `### 内部循环
- 接收任务 → 分派角色 → 跟踪进度 → 汇总结果。
- 只维护事实，不替任何角色做决定。
- 冲突升级时提供事实摘要，由人类决策。`,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Determine the LoadLevel from a complexity score.
 *
 * - complexity < 0.3 → MINIMAL
 * - complexity < 0.7 → STANDARD
 * - complexity >= 0.7 → FULL
 */
function levelFromComplexity(complexity: number): LoadLevel {
  const c = Math.max(0, Math.min(1, complexity));
  if (c < 0.3) return LoadLevel.MINIMAL;
  if (c < 0.7) return LoadLevel.STANDARD;
  return LoadLevel.FULL;
}

// ── ContextLoader ────────────────────────────────────────────────────────────

export class ContextLoader {
  // ── Token estimation ─────────────────────────────────────────────────────

  /**
   * Estimate token count for text (supports CJK characters).
   * CJK characters ≈ 1.5 tokens each, ASCII ≈ 0.25 tokens per char.
   */
  estimateTokens(text: string): number {
    let cjkCount = 0;
    let asciiCount = 0;

    for (let i = 0; i < text.length; i++) {
      const code = text.charCodeAt(i);
      // CJK Unified Ideographs range: U+4E00 – U+9FFF
      // plus extensions: U+3400–U+4DBF, U+F900–U+FAFF, U+20000–U+2A6DF
      if (
        (code >= 0x4e00 && code <= 0x9fff) ||
        (code >= 0x3400 && code <= 0x4dbf) ||
        (code >= 0xf900 && code <= 0xfaff) ||
        (code >= 0xd800 &&
          code <= 0xdbff &&
          i + 1 < text.length &&
          text.charCodeAt(i + 1) >= 0xdc00 &&
          text.charCodeAt(i + 1) <= 0xdfff)
      ) {
        cjkCount++;
        // Skip surrogate pair second half
        if (code >= 0xd800 && code <= 0xdbff) i++;
      } else if (code < 128) {
        asciiCount++;
      }
    }

    return Math.ceil(cjkCount * 1.5 + asciiCount * 0.25);
  }

  // ── Role context loading ─────────────────────────────────────────────────

  /**
   * Load role context based on complexity (0.0–1.0).
   *
   * - complexity < 0.3 → MINIMAL  (stance only)
   * - complexity < 0.7 → STANDARD (stance + thinking framework)
   * - complexity >= 0.7 → FULL    (stance + framework + loop guide)
   */
  loadRoleContext(roleId: string, complexity: number): LoadedContext {
    const level = levelFromComplexity(complexity);
    const parts: string[] = [];
    const sections: string[] = [];

    // Layer 1 — fixed stance (always loaded)
    const stance = ROLE_STANCES[roleId];
    if (stance) {
      parts.push(`# ${roleId} 角色立场\n\n${stance}`);
      sections.push("stance");
    } else {
      parts.push(`# ${roleId}\n\n（未定义角色立场）`);
      sections.push("stance");
    }

    // Layer 2 — thinking framework (STANDARD+)
    if (level === LoadLevel.STANDARD || level === LoadLevel.FULL) {
      parts.push(THINKING_FRAMEWORK);
      sections.push("thinking_framework");
    }

    // Layer 3 — internal loop guide (FULL only)
    if (level === LoadLevel.FULL) {
      const loopGuide = ROLE_LOOP_GUIDES[roleId];
      if (loopGuide) {
        parts.push(loopGuide);
        sections.push("loop_guide");
      }
    }

    const system_prompt = parts.join("\n\n---\n\n");
    const estimated_tokens = this.estimateTokens(system_prompt);

    return {
      role_id: roleId,
      level,
      system_prompt,
      estimated_tokens,
      loaded_sections: sections,
    };
  }

  // ── Document indexing ────────────────────────────────────────────────────

  /**
   * Build a hierarchical index of a Markdown document.
   *
   * Reads the file at `docPath`, parses headings (`#`, `##`, `###`, …)
   * into DocumentSection entries, and computes line / token totals.
   */
  buildDocumentIndex(docPath: string): DocumentIndex {
    const absPath = resolve(docPath);
    const raw = readFileSync(absPath, "utf-8");
    const lines = raw.split("\n");

    const sections: DocumentSection[] = [];
    let currentTitle = "";
    let currentLevel = 0;
    let currentContent: string[] = [];
    let currentStart = 1;

    const headingRe = /^(#{1,6})\s+(.+)$/;

    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(headingRe);
      if (match) {
        // Flush previous section
        if (currentTitle || currentContent.length > 0) {
          sections.push({
            title: currentTitle,
            level: currentLevel,
            content: currentContent.join("\n").trim(),
            line_start: currentStart,
            line_end: i,
          });
        }
        currentLevel = match[1].length;
        currentTitle = match[2].trim();
        currentContent = [];
        currentStart = i + 1; // 1-based
      } else {
        currentContent.push(lines[i]);
      }
    }

    // Flush last section
    if (currentTitle || currentContent.length > 0) {
      sections.push({
        title: currentTitle,
        level: currentLevel,
        content: currentContent.join("\n").trim(),
        line_start: currentStart,
        line_end: lines.length,
      });
    }

    const total_lines = lines.length;
    const total_tokens = this.estimateTokens(raw);

    return { doc_path: absPath, sections, total_lines, total_tokens };
  }

  // ── Section loading ──────────────────────────────────────────────────────

  /**
   * Load a specific section from a document by title.
   *
   * Returns the section content string, or `null` if not found.
   */
  loadDocumentSection(docPath: string, sectionTitle: string): string | null {
    const index = this.buildDocumentIndex(docPath);
    const section = index.sections.find(
      (s) => s.title.toLowerCase() === sectionTitle.toLowerCase(),
    );
    return section ? section.content : null;
  }

  // ── Combined loader ──────────────────────────────────────────────────────

  /**
   * Combined entry: role context + relevant project document sections.
   *
   * 1. Loads role context via `loadRoleContext`.
   * 2. If `docPath` exists, builds a document index and appends all
   *    top-level sections (level ≤ 2) to the system prompt.
   */
  loadForRole(
    roleId: string,
    docPath: string,
    complexity: number,
  ): LoadedContext {
    const base = this.loadRoleContext(roleId, complexity);
    const parts: string[] = [base.system_prompt];
    const sections = [...base.loaded_sections];

    const absPath = resolve(docPath);
    if (existsSync(absPath)) {
      const index = this.buildDocumentIndex(absPath);

      // Include top-level sections (heading level ≤ 2)
      for (const sec of index.sections) {
        if (sec.level <= 2 && sec.content.length > 0) {
          const heading = "#".repeat(sec.level) + " " + sec.title;
          parts.push(`${heading}\n\n${sec.content}`);
          sections.push(`doc:${sec.title}`);
        }
      }
    }

    const system_prompt = parts.join("\n\n---\n\n");
    const estimated_tokens = this.estimateTokens(system_prompt);

    return {
      role_id: roleId,
      level: base.level,
      system_prompt,
      estimated_tokens,
      loaded_sections: sections,
    };
  }
}
