/**
 * oqa_patterns.ts — OQA 模式库加载 + AI-03 AC 实现真实性检查器（T-0171）
 *
 * 1. 模式库机制：加载 .ai/oqa-patterns.yaml（项目级），与内置模式合并
 *    （项目级覆盖同名内置）；供 CD/AL/AH 检查器消费。
 * 2. AI-03 AC 实现真实性：从任务卡 AC 提取语义关键词（动词+名词），
 *    在实现文件中验证关键行为存在（函数名/调用/分支/return），
 *    无法验证 → WARNING 附人工确认要求；明确缺失 → BLOCKER。
 */

import { readFileSync, existsSync } from "node:fs";
import { join, extname } from "node:path";
import { parseDocument } from "yaml";

export interface OqaPattern {
  id: string;
  dimension: "REQUIREMENTS" | "CODING" | "DESIGN" | "ENGINEERING" | "AUTHENTICITY";
  severity: "BLOCKER" | "WARNING";
  patterns: RegExp[];
  message: string;
  remediation: string;
}

const BUILTIN_PATTERNS: OqaPattern[] = [
  {
    id: "LAZY-FAKE-DATA", dimension: "CODING", severity: "WARNING",
    patterns: [
      /return\s+\[\s*\]\s*;?\s*\/\/\s*(TODO|stub|fake)/,
      /return\s+\{\s*\}\s*;?\s*\/\/\s*(TODO|stub|fake)/,
      /return\s+null\s*;?\s*\/\/\s*(TODO|stub|fake)/,
    ],
    message: "可能返回假数据冒充实现",
    remediation: "实现真实逻辑或明确标记未完成",
  },
  {
    id: "LAZY-SWALLOW-EXCEPTION", dimension: "CODING", severity: "WARNING",
    patterns: [
      /except\s+(Exception|Error)\s*:\s*\n\s*(pass|return\s+None|return\s+null)/,
      /catch\s*\([^)]*\)\s*\{\s*\}/,
    ],
    message: "吞掉异常不处理不记录",
    remediation: "记录异常或显式降级",
  },
  {
    id: "LAZY-EMPTY-FUNCTION", dimension: "CODING", severity: "WARNING",
    patterns: [
      /def\s+\w+\s*\([^)]*\)\s*:\s*\n\s*(pass|return)/,
      /function\s+\w+\s*\([^)]*\)\s*\{\s*\}/,
    ],
    message: "空实现函数",
    remediation: "实现函数体或移除",
  },
  {
    id: "HALLUCINATE-COMMENT-CLAIM", dimension: "AUTHENTICITY", severity: "BLOCKER",
    patterns: [
      /\/\/\s*(实现|implemented|done|完成).{0,30}(TODO|待实现|not implemented)/,
      /#\s*(实现|implemented|done|完成).{0,30}(TODO|待实现|not implemented)/,
    ],
    message: "注释声称完成但同处含未实现标记",
    remediation: "清理矛盾注释或完成实现",
  },
  {
    id: "FABRICATE-HARDCODED-EXPECT", dimension: "AUTHENTICITY", severity: "WARNING",
    patterns: [
      /expect\s*\([^)]*\).{0,20}toBe\s*\(\s*\d+\s*\)\s*;?\s*\/\/\s*(fake|hardcode)/,
      /assert\s+\w+\s*==\s*\d+\s*#\s*(fake|hardcode)/,
    ],
    message: "硬编码测试期望（可能编造）",
    remediation: "用真实计算/输入构造期望值",
  },
];

/**
 * 加载模式库：内置 + 项目级 .ai/oqa-patterns.yaml（同名覆盖）。
 */
export function loadOqaPatterns(root: string): OqaPattern[] {
  const merged = new Map<string, OqaPattern>();
  for (const p of BUILTIN_PATTERNS) merged.set(p.id, p);
  try {
    const pFile = join(root, ".ai", "oqa-patterns.yaml");
    if (existsSync(pFile)) {
      const raw = readFileSync(pFile, "utf-8");
      const data = parseDocument(raw).toJSON() as { modes?: Array<Record<string, unknown>> };
      if (Array.isArray(data?.modes)) {
        for (const m of data.modes) {
          if (typeof m.id !== "string") continue;
          merged.set(m.id, {
            id: m.id,
            dimension: (m.dimension as OqaPattern["dimension"]) ?? "CODING",
            severity: (m.severity as OqaPattern["severity"]) ?? "WARNING",
            patterns: ((m.patterns as string[] | undefined) ?? []).map(p => new RegExp(p, "i")),
            message: String(m.message ?? "模式命中"),
            remediation: String(m.remediation ?? ""),
          });
        }
      }
    }
  } catch {
    /* 模式库损坏时用内置 */
  }
  return [...merged.values()];
}

/**
 * 用模式库扫描内容，返回命中 finding 列表。
 */
export function scanWithPatterns(
  root: string,
  files: string[],
  contentMap: Map<string, string>,
): Array<{ pattern_id: string; dimension: OqaPattern["dimension"]; severity: OqaPattern["severity"]; message: string; evidence: string; remediation: string }> {
  const patterns = loadOqaPatterns(root);
  const out: Array<{ pattern_id: string; dimension: OqaPattern["dimension"]; severity: OqaPattern["severity"]; message: string; evidence: string; remediation: string }> = [];
  for (const f of files) {
    const c = contentMap.get(f) ?? "";
    if (!c) continue;
    for (const p of patterns) {
      for (const re of p.patterns) {
        const m = re.exec(c);
        if (m) {
          const line = c.slice(0, m.index ?? 0).split("\n").length;
          out.push({
            pattern_id: p.id, dimension: p.dimension, severity: p.severity,
            message: `${p.message} (${f}:${line})`,
            evidence: `${f}:${line}`,
            remediation: p.remediation,
          });
          break;
        }
      }
    }
  }
  return out;
}

// ── AI-03 AC 实现真实性 ──────────────────────────────────────────────

const CODE_EXTS = new Set([".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".hpp"]);

/** AC 语义关键词提取：取 AC 文本中的动词/名词（简单分词 + 中英文行为词）。 */
function extractAcKeywords(acText: string): string[] {
  const text = acText.replace(/\[AC-\d+\]\s*/, "");
  const words: string[] = [];
  for (const m of text.matchAll(/\b(login|auth|validate|save|load|create|delete|update|search|filter|sort|send|receive|parse|convert|calculate|compute|check|verify|format|render|fetch|submit|cancel|approve|reject|export|import|merge|split|join|hash|encrypt|decrypt)\b/gi)) {
    words.push(m[1].toLowerCase());
  }
  // 中英同义映射：中文关键词 → 英文等价词一并检查
  const CN_EN_MAP: Record<string, string[]> = {
    "登录": ["login"], "校验": ["validate"], "验证": ["verify", "validate"],
    "保存": ["save"], "加载": ["load"], "创建": ["create"], "删除": ["delete"],
    "更新": ["update"], "查询": ["query", "search"], "搜索": ["search"],
    "过滤": ["filter"], "排序": ["sort"], "发送": ["send"], "接收": ["receive"],
    "解析": ["parse"], "转换": ["convert"], "计算": ["calc", "compute"],
    "检查": ["check"], "格式化": ["format"], "渲染": ["render"],
    "提交": ["submit"], "取消": ["cancel"], "批准": ["approve"], "拒绝": ["reject"],
    "导出": ["export"], "导入": ["import"], "合并": ["merge"], "拆分": ["split"],
    "加密": ["encrypt"], "解密": ["decrypt"],
    "查找": ["find", "get", "search"], "获取": ["get", "fetch"],
    "添加": ["add", "create"], "移除": ["remove", "delete"],
    "写入": ["write", "save"], "读取": ["read", "load"],
    "认证": ["auth", "authenticate", "signIn"], "登出": ["logout", "signOut"],
    "权限": ["permission", "checkPermission", "authorize"],
  };
  for (const m of text.matchAll(/(登录|校验|验证|保存|加载|创建|删除|更新|查询|搜索|查找|获取|添加|移除|写入|读取|认证|登出|权限|过滤|排序|发送|接收|解析|转换|计算|检查|格式化|渲染|提交|取消|批准|拒绝|导出|导入|合并|拆分|加密|解密)/g)) {
    words.push(m[1]);
    const en = CN_EN_MAP[m[1]];
    if (en) words.push(...en);
  }
  return [...new Set(words)];
}

export interface AcImplementationResult {
  findings: Array<{ checker_id: string; severity: "BLOCKER" | "WARNING"; message: string; evidence: string; remediation: string }>;
}

/**
 * AI-03：验证 AC 语义关键词在实现文件中是否真实存在行为。
 * 无法验证（无实现文件或无关键词）→ WARNING 附人工确认要求；
 * 明确缺失（有实现文件但关键词行为不存在）→ BLOCKER。
 */
export function checkAcImplementation(
  root: string,
  files: string[],
  contentMap: Map<string, string>,
  taskId?: string,
): AcImplementationResult {
  const findings: AcImplementationResult["findings"] = [];
  if (!taskId) {
    return { findings: [{
      checker_id: "AI-03-ac-implementation", severity: "BLOCKER",
      message: "No task_id in context — AC implementation cannot be verified.",
      evidence: "context.task_id undefined",
      remediation: "Pass task_id to verify AC implementation.",
    }] };
  }
  const cardRaw = (() => {
    try { return readFileSync(join(root, ".ai", "tasks", `${taskId}.md`), "utf-8"); } catch { return null; }
  })();
  if (!cardRaw) {
    return { findings: [] };
  }
  const acs = [...cardRaw.matchAll(/\[AC-\d+\][^\n]*/g)].map(m => m[0].trim());
  if (acs.length === 0) {
    return { findings: [] };
  }
  const codeFiles = files.filter(f => CODE_EXTS.has(extname(f).toLowerCase()));
  if (codeFiles.length === 0) {
    return { findings: [{
      checker_id: "AI-03-ac-implementation", severity: "WARNING",
      message: `Task ${taskId} has ${acs.length} ACs but no implementation files in target — manual confirmation required.`,
      evidence: "no code files in target",
      remediation: "Produce implementation or confirm ACs are doc-only.",
    }] };
  }
  // P1-3 修复：剥离注释/字符串后再验证行为词（防注释/字符串伪造）
  const allCode = codeFiles.map(f => contentMap.get(f) ?? "").join("\n");
  const stripped = allCode
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "")
    .replace(/"[^"]*"/g, "")
    .replace(/'[^']*'/g, "");
  const codeLower = stripped.toLowerCase();
  let unverified = 0;
  for (const ac of acs) {
    const keywords = extractAcKeywords(ac);
    if (keywords.length === 0) continue;
    const missing = keywords.filter(k => !codeLower.includes(k));
    if (missing.length === keywords.length) {
      findings.push({
        checker_id: "AI-03-ac-implementation", severity: "BLOCKER",
        message: `AC "${ac.slice(0, 40)}" keywords [${missing.join(", ")}] not found in any implementation — likely unimplemented.`,
        evidence: `AC: ${ac}`,
        remediation: "Implement the AC behavior or remove the claim.",
      });
    } else if (missing.length > 0) {
      unverified += 1;
    }
  }
  if (unverified > 0 && findings.length === 0) {
    findings.push({
      checker_id: "AI-03-ac-implementation", severity: "WARNING",
      message: `${unverified} AC(s) partially verified — manual confirmation recommended for keyword coverage.`,
      evidence: `partial keywords: ${unverified}`,
      remediation: "Confirm AC behaviors with a reviewer.",
    });
  }
  return { findings };
}
