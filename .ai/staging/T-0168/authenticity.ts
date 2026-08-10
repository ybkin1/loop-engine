/**
 * authenticity.ts — AUTHENTICITY dimension checkers (OQA-5D, T-0168)
 *
 * Verifies that AI-produced artifacts are REAL, not just well-shaped:
 *
 *   AH-01 reference-existence   (hallucination)  import/require targets exist
 *   AH-02 file-ref-existence    (hallucination)  doc/code referenced paths exist
 *   AF-01 evidence-authenticity (fabrication)    evidence content_hash matches
 *   AF-02 completion-claims     (fabrication)    completed tasks have AC artifacts
 *   AL-01 placeholder-detection (laziness)       TODO/stub/empty bodies
 *   AL-02 test-quality          (laziness)       tests have assertions & failure paths
 *   AO-01 dead-code             (over-engineering) exported symbols with 0 refs
 *   AO-02 ghost-interfaces      (over-engineering) interfaces without impl/callers
 *   AI-01 doc-impl-drift        (inconsistency)  doc signatures vs actual signatures
 *   AI-02 state-artifact-drift  (inconsistency)  state.yaml status vs artifacts
 *
 * Severity: AH/AF/AL-01 = BLOCKER (authenticity red lines);
 *           AL-02/AO/AI = WARNING (quality debt).
 *
 * All checkers are pure functions over (root, target, files, ctx, contentMap)
 * — same inputs, same verdicts (replayable).
 */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join, extname, basename, resolve, relative, dirname } from "node:path";
import { createHash } from "node:crypto";
import { parseDocument } from "yaml";

// ── Shared types (mirror output_quality.ts, keep module self-contained) ──

export type FindingSeverity = "BLOCKER" | "WARNING" | "INFO";

export interface QualityFinding {
  checker_id: string;
  severity: FindingSeverity;
  message: string;
  evidence: string;
  remediation: string;
}

export interface QualityCheck {
  checker_id: string;
  dimension: "AUTHENTICITY";
  passed: boolean;
  findings: QualityFinding[];
  duration_ms: number;
}

export interface AuthenticityEnv {
  root: string;
  target: string;
  files: string[];
  ctx: { task_id?: string; phase?: string; role?: string; dimensions?: unknown[] };
  contentMap: Map<string, string>;
}

function finding(
  checkerId: string,
  severity: FindingSeverity,
  message: string,
  evidence: string,
  remediation: string,
): QualityFinding {
  return { checker_id: checkerId, severity, message, evidence, remediation };
}

function readMaybe(root: string, rel: string): string | null {
  try {
    return readFileSync(join(root, rel), "utf-8");
  } catch {
    return null;
  }
}

/** Strip comments from code (line + block), keep strings (import paths are strings). */
function stripComments(code: string): string {
  return code
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");
}

const CODE_EXTS = new Set([".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".hpp"]);

// ── Checkers ────────────────────────────────────────────────────────────

export const authenticityCheckers: Array<(env: AuthenticityEnv) => QualityCheck> = [
  // ── AH-01: import/require targets must exist (hallucination) ──
  (env): QualityCheck => {
    const { root, files, contentMap } = env;
    const v: QualityFinding[] = [];
    const fileSet = new Set(files.map(f => f.replace(/\\/g, "/")));

    for (const f of files) {
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const c = stripComments(contentMap.get(f) ?? "");
      if (!c) continue;
      // TS/JS style imports（含 CJS require —— 修复 P1-5）
      for (const m of c.matchAll(/(?:from|import\s*\(|import|require\s*\()\s*["'](\.[^"']+)["']/g)) {
        const raw = m[1];
        if (!raw.startsWith(".")) continue; // bare specifier — checked via manifest elsewhere
        // resolve relative import candidates (normalize ./ ../ and extensions)
        const resolved = resolve(join(root, dirname(f)), raw);
        const rel = relative(root, resolved).replace(/\\/g, "/");
        // 剥掉 .js/.jsx 扩展名再补候选（TS 源码常 import "./b.js" 指向 b.ts）
        const baseNoExt = rel.replace(/\.(js|jsx|ts|tsx)$/, "");
        const cands = [
          rel,
          rel + ".ts",
          rel + ".tsx",
          rel + ".js",
          rel + ".jsx",
          baseNoExt + ".ts",
          baseNoExt + ".tsx",
          baseNoExt + ".js",
          baseNoExt + ".jsx",
          baseNoExt + "/index.ts",
          baseNoExt + "/index.js",
        ];
        const hit = cands.some(cd => fileSet.has(cd) || existsSync(join(root, cd)));
        if (!hit) {
          v.push(finding(
            "AH-01-reference-existence", "BLOCKER",
            `${f} imports "${raw}" but the target file does not exist in the artifact set.`,
            `${f}: import ${raw}`,
            "Fix the import path or create the missing module (no fabricated paths).",
          ));
        }
      }
      // Python style imports —— 仅检查相对导入（from . / from .pkg），
      // 标准库与第三方库（os/json/pathlib/numpy/pytest 等）由依赖清单管理，
      // 不在源码树内存在是常态，不得误报（修复 P0-1）。
      for (const m of c.matchAll(/^\s*(?:from\s+(\.[\w.]*)\s+import|import\s+(\.[\w.]+))/gm)) {
        const mod = m[1] || m[2];
        if (!mod || !mod.startsWith(".")) continue; // 绝对导入跳过
        const modPath = mod.replace(/\./g, "/").replace(/^\.\/?/, "");
        // 相对导入解析到源码目录
        const baseDir = f.split("/").slice(0, -1).join("/");
        const cands = [
          [baseDir, modPath + ".py"].filter(Boolean).join("/"),
          [baseDir, modPath + "/__init__.py"].filter(Boolean).join("/"),
        ];
        const hit = cands.some(cd => fileSet.has(cd) || existsSync(join(root, cd)));
        if (!hit) {
          v.push(finding(
            "AH-01-reference-existence", "BLOCKER",
            `${f} imports relative module "${mod}" but no matching module file exists.`,
            `${f}: import ${mod}`,
            "Fix the import or create the module (no fabricated imports).",
          ));
        }
      }
    }
    return {
      checker_id: "AH-01-reference-existence", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },

  // ── AH-02: doc/code referenced relative paths must exist ──
  (env): QualityCheck => {
    const { root, files, contentMap } = env;
    const v: QualityFinding[] = [];
    const fileSet = new Set(files.map(f => f.replace(/\\/g, "/")));

    for (const f of files) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      // markdown links [x](path) and code comments referencing paths
      for (const m of c.matchAll(/\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)/g)) {
        const raw = m[1];
        if (/^(https?:|mailto:|data:)/.test(raw)) continue;
        if (raw.startsWith("#")) continue; // anchor
        const cleaned = raw.split("?")[0];
        if (!cleaned) continue;
        const norm = cleaned.replace(/\\/g, "/").replace(/^\.\//, "");
        const base = f.split("/").slice(0, -1).join("/");
        const joined = [base, norm].filter(Boolean).join("/").replace(/\/+/g, "/");
        const candidates = [joined, joined + ".md", joined + ".ts", joined + ".js"];
        const hit = candidates.some(cd => fileSet.has(cd) || existsSync(join(root, cd)));
        if (!hit) {
          v.push(finding(
            "AH-02-file-ref-existence", "WARNING",
            `${f} references "${raw}" but the target does not exist.`,
            `${f}: ${raw}`,
            "Fix the reference or create the file (broken links = fabricated docs).",
          ));
        }
      }
    }
    return {
      checker_id: "AH-02-file-ref-existence", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },

  // ── AF-01: evidence content_hash must match real files (fabrication) ──
  (env): QualityCheck => {
    const { root, files } = env;
    const v: QualityFinding[] = [];

    // Evidence files inside target that claim a content_hash
    for (const f of files) {
      if (!/\.(json|yaml|yml)$/.test(f) || !f.includes(".ai/evidence")) continue;
      const raw = readMaybe(root, f);
      if (!raw) continue;
      let parsed: { content_hash?: unknown; content?: unknown; stdout_hash?: unknown; exit_code?: unknown; artifacts?: unknown } | null = null;
      try {
        if (f.endsWith(".json")) parsed = JSON.parse(raw);
        else parsed = parseDocument(raw).toJSON() as typeof parsed;
      } catch {
        continue; // not parseable → other checkers handle
      }
      if (!parsed) continue;

      // Evidence with content + content_hash → verify hash matches
      if (typeof parsed.content === "string" && typeof parsed.content_hash === "string") {
        const actual = createHash("sha256").update(parsed.content, "utf-8").digest("hex");
        if (actual !== parsed.content_hash) {
          v.push(finding(
            "AF-01-evidence-authenticity", "BLOCKER",
            `${f} claims content_hash ${parsed.content_hash.slice(0, 12)}… but real hash is ${actual.slice(0, 12)}….`,
            `${f}: hash mismatch`,
            "Recompute evidence with loop_evidence_submit — do not fabricate hashes.",
          ));
        }
      }
      // exit_code=0 evidence must have a corresponding artifact
      if (parsed.exit_code === 0 && Array.isArray(parsed.artifacts)) {
        for (const a of parsed.artifacts as string[]) {
          if (!existsSync(join(root, a))) {
            v.push(finding(
              "AF-01-evidence-authenticity", "BLOCKER",
              `${f} claims artifact "${a}" but it does not exist.`,
              `${f}: artifact ${a}`,
              "Do not claim artifacts that were not produced.",
            ));
          }
        }
      }
    }
    return {
      checker_id: "AF-01-evidence-authenticity", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },

  // ── AF-02: completed tasks must have AC artifacts (fabrication) ──
  (env): QualityCheck => {
    const { root, ctx } = env;
    const v: QualityFinding[] = [];
    if (!ctx.task_id) {
      return {
        checker_id: "AF-02-completion-claims", dimension: "AUTHENTICITY",
        passed: true,
        findings: [finding(
          "AF-02-completion-claims", "INFO",
          "No task_id in context — completion claim check skipped.",
          "context.task_id undefined",
          "Pass task_id to verify completion claims.",
        )],
        duration_ms: 0,
      };
    }
    // 读取任务状态：state.yaml current_task_id / task_graph 状态（修复 P1-3）
    const stateRaw = readMaybe(root, ".ai/state.yaml");
    const cardRaw = readMaybe(root, `.ai/tasks/${ctx.task_id}.md`);
    if (!cardRaw) {
      return {
        checker_id: "AF-02-completion-claims", dimension: "AUTHENTICITY",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    const acs = [...cardRaw.matchAll(/\[AC-\d+\][^\n]*/g)].map(m => m[0].trim());
    // 任务状态：completed/active 才检查；requirements 阶段（S1）不要求证据
    let taskStatus = "";
    try {
      if (stateRaw) {
        const state = parseDocument(stateRaw).toJSON() as { current_task_id?: string };
        if (state.current_task_id === ctx.task_id) taskStatus = "active";
      }
      const graphRaw = readMaybe(root, ".ai/task_graph.yaml");
      if (graphRaw) {
        const graph = parseDocument(graphRaw).toJSON() as { tasks?: Array<{ id?: string; status?: string }> };
        const node = graph.tasks?.find(t => t.id === ctx.task_id);
        if (node?.status) taskStatus = node.status;
      }
    } catch {
      /* best effort */
    }

    // 任务声明完成但无证据 → 编造；仅对完成态检查（修复 P1-3：不再误伤 S2/S3 进行中任务）
    const evDir = join(root, ".ai", "evidence", ctx.task_id);
    const hasEvidence = existsSync(evDir) && (() => {
      try { return readdirSync(evDir).length > 0; } catch { return false; }
    })();
    const claimsDone = taskStatus === "completed" || taskStatus === "active";
    if (acs.length > 0 && !hasEvidence && claimsDone && ctx.phase !== "S1") {
      v.push(finding(
        "AF-02-completion-claims", "WARNING",
        `Task ${ctx.task_id} (${taskStatus}) has ${acs.length} ACs but no evidence directory (.ai/evidence/${ctx.task_id}/).`,
        `.ai/evidence/${ctx.task_id}/ missing`,
        "Submit evidence for each AC before claiming completion.",
      ));
    }
    return {
      checker_id: "AF-02-completion-claims", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },

  // ── AL-01: placeholder detection (laziness) — BLOCKER ──
  (env): QualityCheck => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    const PLACEHOLDER_PATTERNS: RegExp[] = [
      /\bTODO\s*:/,
      /\bFIXME\s*:/,
      /\bHACK\s*:/,
      /\bNotImplementedError\b/,
      /\bNotImplemented\b/,
      /\bthrow new Error\(["']not implemented/i,
      /\blorem ipsum\b/i,
    ];
    const SELF_EXEMPT = ["PLACEHOLDER_PATTERNS", "TODO_PATTERNS", "AL-01-placeholder"];
    // placeholder 单词需限定上下文（修复 P1-1）：仅当作为属性值/注释目标出现才报，
    // 排除 JSX/HTML placeholder="..." 属性与普通单词使用。
    const CONTEXT_PLACEHOLDER_RE = /(?:\/\/|#|\*|<!--|\/\*)[^\n]*\bplaceholder\b/i;

    for (const f of files) {
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      const lines = c.split("\n");
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (SELF_EXEMPT.some(s => line.includes(s))) continue;
        for (const re of PLACEHOLDER_PATTERNS) {
          const m = line.match(re);
          if (m) {
            v.push(finding(
              "AL-01-placeholder-detection", "BLOCKER",
              `Placeholder in ${f}:${i + 1}: ${m[0].trim()}`,
              `${f}:${i + 1}`,
              "Implement fully — placeholders are not deliverable code.",
            ));
            break;
          }
        }
        // 上下文限定的 placeholder（注释中提及）→ WARNING 而非 BLOCKER
        const cm = line.match(CONTEXT_PLACEHOLDER_RE);
        if (cm && !line.includes("PLACEHOLDER_PATTERNS")) {
          v.push(finding(
            "AL-01-placeholder-detection", "WARNING",
            `Placeholder mention in comment at ${f}:${i + 1}.`,
            `${f}:${i + 1}`,
            "Resolve or remove placeholder comments before delivery.",
          ));
        }
      }
    }
    return {
      checker_id: "AL-01-placeholder-detection", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },

  // ── AL-02: test quality (laziness) — WARNING ──
  (env): QualityCheck => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    const testFiles = files.filter(f =>
      /\.(test|spec)\.(ts|tsx|js|jsx)$/.test(f) || /^test_.*\.py$/.test(basename(f)));

    for (const f of testFiles) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      const codeOnly = stripComments(c);
      // 断言计数：TS/JS expect/toBe + Python assert（裸 assert 无括号，修复 P1-2）
      const assertions = (codeOnly.match(/\b(expect|assertEqual|assertIn|assertTrue|assertFalse|assertIs|assertRaises|strictEqual|deepEqual|should|toEqual|toBe|toBeTruthy|ok\()\s*\(/g) || []).length
        + (codeOnly.match(/^\s*assert\s+[^\n]+/gm) || []).length;
      if (assertions === 0) {
        v.push(finding(
          "AL-02-test-quality", "WARNING",
          `${f} has 0 assertions — it cannot detect regressions.`,
          `${f}: 0 assertions`,
          "Add assertions; a test without assertions is theater.",
        ));
        continue;
      }
      // failure-path presence: look for negative/edge keywords
      const hasFailurePath = /(throws?|reject|error|invalid|empty|not found|edge|boundary|fail|negative)/i.test(codeOnly);
      if (!hasFailurePath) {
        v.push(finding(
          "AL-02-test-quality", "WARNING",
          `${f} has ${assertions} assertion(s) but no failure-path cases (throws/error/edge/negative).`,
          `${f}: happy-path only`,
          "Add failure-path tests (errors, boundaries, invalid input).",
        ));
      }
    }
    return {
      checker_id: "AL-02-test-quality", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },

  // ── AO-01: dead code — exported symbols with 0 references (over-engineering) ──
  (env): QualityCheck => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    const tsFiles = files.filter(f => /\.(ts|tsx)$/.test(f) && !f.endsWith(".d.ts"));
    if (tsFiles.length < 2) {
      return {
        checker_id: "AO-01-dead-code", dimension: "AUTHENTICITY",
        passed: true,
        findings: [finding(
          "AO-01-dead-code", "INFO",
          "Fewer than 2 TS files — dead-code scan skipped.",
          "ts files < 2",
          "",
        )],
        duration_ms: 0,
      };
    }
    const allCode = tsFiles.map(f => contentMap.get(f) ?? "").join("\n");
    const selfExempt = ["AO-01-dead-code", "DEAD_EXEMPT"];
    // 入口符号（main/run/start/app/index/handler/bootstrap）由宿主调用，不算死代码
    const ENTRY_SYMBOLS = new Set(["main", "run", "start", "app", "index", "handler", "bootstrap", "init"]);

    for (const f of tsFiles) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      // exported identifiers: export const/function/class X / export { X }
      for (const m of c.matchAll(/export\s+(?:const|function|class|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)/g)) {
        const sym = m[1];
        if (selfExempt.some(s => s.includes(sym))) continue;
        if (ENTRY_SYMBOLS.has(sym)) continue; // entry symbol — invoked by host
        if (sym === "OutputQualityEngine" || sym === "renderReportSummary") continue; // public API
        // count references in other files
        const refsInOthers = tsFiles.filter(o => o !== f).some(o =>
          (contentMap.get(o) ?? "").includes(sym));
        const refsInSelf = (c.match(new RegExp(`\\b${sym}\\b`, "g")) || []).length;
        if (!refsInOthers && refsInSelf <= 1) {
          v.push(finding(
            "AO-01-dead-code", "WARNING",
            `${f} exports "${sym}" but no other file references it (dead export).`,
            `${f}: export ${sym}`,
            "Remove unused exports or wire them to real callers.",
          ));
        }
      }
    }
    return {
      checker_id: "AO-01-dead-code", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v.slice(0, 10), duration_ms: 0,
    };
  },

  // ── AO-02: ghost interfaces (over-engineering) — WARNING ──
  (env): QualityCheck => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    const tsFiles = files.filter(f => /\.(ts|tsx)$/.test(f) && !f.endsWith(".d.ts"));
    if (tsFiles.length < 2) {
      return {
        checker_id: "AO-02-ghost-interfaces", dimension: "AUTHENTICITY",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    const allCode = tsFiles.map(f => contentMap.get(f) ?? "").join("\n");

    for (const f of tsFiles) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      for (const m of c.matchAll(/export\s+interface\s+([A-Za-z_$][\w$]*)/g)) {
        const iface = m[1];
        const usedElsewhere = tsFiles.filter(o => o !== f).some(o =>
          (contentMap.get(o) ?? "").includes(iface));
        const usedInSelf = (c.match(new RegExp(`\\b${iface}\\b`, "g")) || []).length > 1;
        if (!usedElsewhere && !usedInSelf) {
          v.push(finding(
            "AO-02-ghost-interfaces", "WARNING",
            `${f} exports interface "${iface}" with no implementer or caller.`,
            `${f}: interface ${iface}`,
            "Remove the ghost interface or implement/consume it.",
          ));
        }
      }
    }
    return {
      checker_id: "AO-02-ghost-interfaces", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v.slice(0, 10), duration_ms: 0,
    };
  },

  // ── AI-01: doc-impl drift (inconsistency) — WARNING ──
  (env): QualityCheck => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    const tsFiles = files.filter(f => /\.(ts|tsx)$/.test(f) && !f.endsWith(".d.ts"));
    if (tsFiles.length === 0) {
      return {
        checker_id: "AI-01-doc-impl-drift", dimension: "AUTHENTICITY",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    // For each exported function, check any doc comment's param count vs actual params
    for (const f of tsFiles) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      // find doc comments (@param N) followed by function signature
      const docParamBlocks = [...c.matchAll(/\/\*\*[\s\S]*?@param\s+(\w+)[\s\S]*?\*\/\s*export\s+function\s+(\w+)\s*\(([^)]*)\)/g)];
      for (const m of docParamBlocks) {
        const docParams = (c.match(/@param\s+(\w+)/g) || []).length;
        const actualParams = m[3].split(",").filter(p => p.trim() !== "" && !p.trim().startsWith("...")).length;
        void docParams;
        // count params inside this specific block
        const block = m[0];
        const blockDocParams = (block.match(/@param\s+(\w+)/g) || []).length;
        if (blockDocParams !== actualParams) {
          v.push(finding(
            "AI-01-doc-impl-drift", "WARNING",
            `${f} function "${m[2]}" documents ${blockDocParams} param(s) but declares ${actualParams}.`,
            `${f}: ${m[2]}()`,
            "Sync doc comments with the actual signature (docs lying = fabricated API).",
          ));
        }
      }
    }
    return {
      checker_id: "AI-01-doc-impl-drift", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v.slice(0, 10), duration_ms: 0,
    };
  },

  // ── AI-02: state-artifact drift (inconsistency) — WARNING ──
  (env): QualityCheck => {
    const { root, ctx, files, target } = env;
    const v: QualityFinding[] = [];
    if (!ctx.task_id) {
      return {
        checker_id: "AI-02-state-artifact-drift", dimension: "AUTHENTICITY",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    // state.yaml / task_graph claims vs artifacts in target
    const stateRaw = readMaybe(root, ".ai/state.yaml");
    if (!stateRaw) return {
      checker_id: "AI-02-state-artifact-drift", dimension: "AUTHENTICITY",
      passed: true, findings: [], duration_ms: 0,
    };
    try {
      const state = parseDocument(stateRaw).toJSON() as { current_task_id?: string; current_phase?: string };
      // 目标目录不存在或无文件 → 状态声称活跃但无产物
      const targetAbs = join(root, target);
      const targetExists = existsSync(targetAbs);
      const isEmptyDir = targetExists && (() => {
        try { return readdirSync(targetAbs).length === 0; } catch { return false; }
      })();
      if (state.current_task_id === ctx.task_id && (files.length === 0 || isEmptyDir)) {
        v.push(finding(
          "AI-02-state-artifact-drift", "WARNING",
          `state.yaml claims task ${ctx.task_id} active but target "${target}" contains no artifacts.`,
          `${target}: ${files.length} file(s)`,
          "Produce the task artifacts or update state (state lying = fabricated progress).",
        ));
      }
    } catch {
      /* unparseable state — skip */
    }
    return {
      checker_id: "AI-02-state-artifact-drift", dimension: "AUTHENTICITY",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  },
];

// ── Label for the dimension ──
export const AUTHENTICITY_LABEL = "真实性（AI 行为验证）";
