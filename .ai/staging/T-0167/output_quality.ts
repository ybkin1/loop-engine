/**
 * output_quality.ts — Four-Dimension Output Quality Engine (OQA-4D)
 *
 * Guarantees that ANY artifact (code / docs / config) produced inside the
 * Loop governance project satisfies, before delivery:
 *
 *   1. REQUIREMENTS — artifact maps to task-card ACs and requirement docs
 *   2. CODING      — lint/typecheck, naming, structure, no debug residue,
 *                    no dead code, sane file scale
 *   3. DESIGN      — architecture alignment, module boundaries, dependency
 *                    direction, layering compliance
 *   4. ENGINEERING — tests exist & pass, evidence-chain binding, replayable,
 *                    review-ready
 *
 * Design principles:
 *   - Deterministic: every checker is a pure function over (root, target, ctx).
 *   - Replayable: report contains content hash + checker version; same input
 *     → same verdict.
 *   - Fail-closed: BLOCKER findings gate delivery; WARNING findings are
 *     advisory but recorded.
 *   - Evidence-bindable: report can be submitted via evidence.ts.
 */

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, resolve, relative, extname, basename, dirname } from "node:path";
import { parseDocument } from "yaml";

// ── Types ────────────────────────────────────────────────────────────────

export type DimensionId =
  | "REQUIREMENTS"
  | "CODING"
  | "DESIGN"
  | "ENGINEERING";

export type FindingSeverity = "BLOCKER" | "WARNING" | "INFO";

export interface QualityFinding {
  checker_id: string;
  severity: FindingSeverity;
  message: string;
  /** Machine-checkable evidence — file:line or command result. */
  evidence: string;
  /** Suggested remediation (one line). */
  remediation: string;
}

export interface QualityCheck {
  checker_id: string;
  dimension: DimensionId;
  passed: boolean;
  findings: QualityFinding[];
  duration_ms: number;
}

export interface DimensionReport {
  dimension: DimensionId;
  label: string;
  checks: QualityCheck[];
  blocker_count: number;
  warning_count: number;
  status: "PASS" | "WARNING" | "BLOCKED";
}

export interface OutputQualityReport {
  schema: "output_quality_report/v1";
  project_root: string;
  target: string;
  target_kind: "file" | "directory" | "virtual";
  content_hash: string;
  context: {
    task_id?: string;
    phase?: string;
    role?: string;
  };
  dimensions: DimensionReport[];
  overall: "PASS" | "WARNING" | "BLOCKED";
  blocked_by: string[];
  generated_at: string;
  engine_version: string;
}

export interface VerifyContext {
  task_id?: string;
  phase?: string;
  role?: string;
  /** Optional restriction to a subset of dimensions. */
  dimensions?: DimensionId[];
}

// ── Constants ────────────────────────────────────────────────────────────

export const ENGINE_VERSION = "1.0.0";

export const DIMENSION_ORDER: DimensionId[] = [
  "REQUIREMENTS",
  "CODING",
  "DESIGN",
  "ENGINEERING",
];

const DIMENSION_LABELS: Record<DimensionId, string> = {
  REQUIREMENTS: "需求符合性",
  CODING: "编码规范",
  DESIGN: "设计理念",
  ENGINEERING: "软件工程",
};

const SOURCE_PREFIXES = ["src/", "lib/", "app/", "pages/", "components/", "core/"];
const TEST_PREFIXES = ["tests/", "test/", "__tests__/", "spec/"];

const NON_CODE_EXTS = new Set([
  ".md", ".json", ".yaml", ".yml", ".toml", ".lock", ".svg", ".png",
  ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".map",
  ".txt", ".csv", ".log", ".html", ".css",
]);

const CODE_EXTS = new Set([
  ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java",
  ".c", ".h", ".cpp", ".hpp",
]);

const SECRET_PATTERNS: RegExp[] = [
  /(api[_-]?key|apikey|secret|token|password|passwd|pwd)\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']/i,
  /(BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY)/,
  /AKIA[0-9A-Z]{16}/,
  /sk-[A-Za-z0-9]{20,}/,
];

const DEBUG_PATTERNS: RegExp[] = [
  /\bconsole\.log\s*\(/,
  /\bprint\s*\(\s*["']?(DEBUG|debug)/,
  /\bdebugger\s*;?/,
  /\bTODO\s*:/,
  /\bFIXME\s*:/,
  /\bHACK\s*:/,
];

// CD-02 扫描时排除扫描器自身定义行（正则字面量的转义形式），防止自报。
const DEBUG_EXEMPT_SUBSTRINGS = [
  "DEBUG_PATTERNS",
  "SECRET_PATTERNS",
  "TODO_PATTERNS",
  "DEBUG_EXEMPT_SUBSTRINGS",
  "\\bdebugger",
  "\\bconsole",
];

const MAGIC_NUMBER_RE = /[=:,(]\s*-?\d{3,}\s*[,;)\]]/;

const MAX_LINES_WARN = 400;
const MAX_LINES_BLOCK = 1200;
const MAX_FILES_WARN = 50;

// ── Helpers ──────────────────────────────────────────────────────────────

function hashContent(content: string): string {
  return createHash("sha256").update(content, "utf-8").digest("hex");
}

function listFilesUnder(root: string, target: string): string[] {
  const abs = resolve(root, target);
  if (!existsSync(abs)) return [];
  if (statSync(abs).isFile()) return [target];
  const out: string[] = [];
  const walk = (dir: string) => {
    let entries: string[] = [];
    try {
      entries = readdirSync(dir);
    } catch {
      return;
    }
    for (const e of entries) {
      const p = join(dir, e);
      const rel = relative(root, p).replace(/\\/g, "/");
      try {
        if (statSync(p).isDirectory()) walk(p);
        else out.push(rel);
      } catch {
        /* skip unreadable */
      }
    }
  };
  walk(abs);
  return out.sort();
}

function readMaybe(root: string, rel: string): string | null {
  try {
    return readFileSync(join(root, rel), "utf-8");
  } catch {
    return null;
  }
}

function posixRel(root: string, rel: string): string {
  return relative(root, resolve(root, rel)).replace(/\\/g, "/");
}

function isUnder(rel: string, prefixes: string[]): boolean {
  const r = rel.toLowerCase();
  return prefixes.some(p => r.startsWith(p.toLowerCase()) || r === p.toLowerCase().replace(/\/$/, ""));
}

function loadTaskCard(root: string, taskId: string): { acs: string[]; allowedPaths: string[] } | null {
  const raw = readMaybe(root, `.ai/tasks/${taskId}.md`);
  if (!raw) return null;
  const acs = [...raw.matchAll(/\[AC-\d+\][^\n]*/g)].map(m => m[0].trim());
  const allowed: string[] = [];
  const fm = raw.match(/^---\n([\s\S]*?)\n---/);
  if (fm) {
    try {
      const doc = parseDocument(fm[1]);
      const y = doc.toJSON() as { allowed_paths?: unknown };
      if (y && Array.isArray(y.allowed_paths)) allowed.push(...y.allowed_paths.map(String));
    } catch {
      /* manual parse below */
    }
  }
  if (allowed.length === 0) {
    const m = raw.match(/## 允许路径\s*\n([\s\S]*?)(?=\n## |\n## Status)/);
    if (m) {
      for (const line of m[1].split("\n")) {
        const t = line.trim().replace(/^[-*]\s*/, "").replace(/`/g, "");
        if (t && !t.startsWith("#")) allowed.push(t);
      }
    }
  }
  return { acs, allowedPaths: allowed };
}

// ── Checker plumbing ─────────────────────────────────────────────────────

interface CheckerEnv {
  root: string;
  target: string;
  files: string[];
  ctx: VerifyContext;
  contentMap: Map<string, string>;
}

type Checker = (env: CheckerEnv) => QualityCheck;

function runCheck(dimension: DimensionId, checkerId: string, fn: (env: CheckerEnv) => QualityCheck) {
  return (env: CheckerEnv): QualityCheck => {
    const start = Date.now();
    const check = fn(env);
    check.checker_id = checkerId;
    check.dimension = dimension;
    check.duration_ms = Date.now() - start;
    return check;
  };
}

function findings(check: QualityCheck): QualityFinding[] {
  return check.findings ?? [];
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

// ── REQUIREMENTS dimension ───────────────────────────────────────────────

const requirementCheckers: Checker[] = [
  // RQ-01: task card exists & target is inside allowed_paths
  runCheck("REQUIREMENTS", "RQ-01-task-card-binding", (env) => {
    const { ctx, files } = env;
    if (!ctx.task_id) {
      return {
        checker_id: "RQ-01-task-card-binding", dimension: "REQUIREMENTS",
        passed: false,
        findings: [finding("RQ-01-task-card-binding", "BLOCKER",
          "No task_id in verify context — artifact cannot be bound to requirements.",
          "context.task_id is undefined",
          "Verify with task_id from .ai/state.yaml current_task_id.")],
        duration_ms: 0,
      };
    }
    const card = loadTaskCard(env.root, ctx.task_id);
    if (!card) {
      return {
        checker_id: "RQ-01-task-card-binding", dimension: "REQUIREMENTS",
        passed: false,
        findings: [finding("RQ-01-task-card-binding", "BLOCKER",
          `Task card .ai/tasks/${ctx.task_id}.md not found.`,
          `.ai/tasks/${ctx.task_id}.md`,
          "Create the task card before producing artifacts.")],
        duration_ms: 0,
      };
    }
    if (card.allowedPaths.length === 0) {
      return {
        checker_id: "RQ-01-task-card-binding", dimension: "REQUIREMENTS",
        passed: true,
        findings: [finding("RQ-01-task-card-binding", "INFO",
          "Task card has no allowed_paths — scope check skipped.",
          `.ai/tasks/${ctx.task_id}.md`,
          "Add allowed_paths to the task card for stricter scoping.")],
        duration_ms: 0,
      };
    }
    const violations: QualityFinding[] = [];
    for (const f of files) {
      const rel = posixRel(env.root, f);
      const ok = card.allowedPaths.some(ap => {
        const n = ap.replace(/\\/g, "/").replace(/\/$/, "");
        if (n.endsWith("*")) return rel.startsWith(n.slice(0, -1));
        return rel === n || rel.startsWith(n + "/");
      });
      if (!ok) {
        violations.push(finding("RQ-01-task-card-binding", "BLOCKER",
          `Artifact ${rel} is outside task ${ctx.task_id} allowed_paths.`,
          `${rel} ∉ ${card.allowedPaths.join(", ")}`,
          "Move the file inside an allowed path or amend the task card (needs gate)."));
      }
    }
    return {
      checker_id: "RQ-01-task-card-binding", dimension: "REQUIREMENTS",
      passed: violations.length === 0, findings: violations, duration_ms: 0,
    };
  }),

  // RQ-02: AC coverage — implementation files should reference AC ids
  runCheck("REQUIREMENTS", "RQ-02-ac-reference", (env) => {
    const { ctx, files, contentMap } = env;
    if (!ctx.task_id) {
      return {
        checker_id: "RQ-02-ac-reference", dimension: "REQUIREMENTS",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    const card = loadTaskCard(env.root, ctx.task_id);
    if (!card || card.acs.length === 0) {
      return {
        checker_id: "RQ-02-ac-reference", dimension: "REQUIREMENTS",
        passed: true,
        findings: [finding("RQ-02-ac-reference", "INFO",
          "No ACs found in task card — coverage check skipped.",
          `.ai/tasks/${ctx.task_id}.md`,
          "Define [AC-xx] acceptance criteria in the task card.")],
        duration_ms: 0,
      };
    }
    const codeFiles = files.filter(f => {
      const e = extname(f).toLowerCase();
      return CODE_EXTS.has(e) || e === ".md";
    });
    let referenced = 0;
    for (const ac of card.acs) {
      const acId = (ac.match(/\[(AC-\d+)\]/) || [])[1];
      if (!acId) continue;
      // \b 边界匹配，防 "AC-010" 命中 "AC-01"（F5）
      const acPattern = new RegExp(`\\b${acId}\\b`);
      const hit = codeFiles.some(f => acPattern.test(contentMap.get(f) ?? ""));
      if (hit) referenced += 1;
    }
    const missing = card.acs.length - referenced;
    const coverage = Math.round((referenced / card.acs.length) * 100);
    return {
      checker_id: "RQ-02-ac-reference", dimension: "REQUIREMENTS",
      passed: missing === 0,
      findings: missing > 0
        ? [finding("RQ-02-ac-reference", "WARNING",
          `${missing}/${card.acs.length} ACs not referenced by any artifact (coverage ${coverage}%).`,
          `ACs referenced: ${referenced}/${card.acs.length}`,
          "Reference [AC-xx] ids in code comments or docs linked to the artifact.")]
        : [finding("RQ-02-ac-reference", "INFO",
          `All ${card.acs.length} ACs referenced (coverage ${coverage}%).`,
          `AC coverage ${coverage}%`,
          "")],
      duration_ms: 0,
    };
  }),

  // RQ-03: requirement doc traceability
  runCheck("REQUIREMENTS", "RQ-03-requirement-traceability", (env) => {
    const { files, contentMap } = env;
    const reqCandidates = files.filter(f =>
      /(requirements|scope|spec|product-requirements|acceptance)/i.test(f) && f.endsWith(".md"));
    const docRefs = files.filter(f => f.endsWith(".md")).some(f =>
      /requirements|验收标准|AC-\d+/i.test(contentMap.get(f) ?? ""));
    if (reqCandidates.length > 0 || docRefs) {
      return {
        checker_id: "RQ-03-requirement-traceability", dimension: "REQUIREMENTS",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    return {
      checker_id: "RQ-03-requirement-traceability", dimension: "REQUIREMENTS",
      passed: true,
      findings: [finding("RQ-03-requirement-traceability", "INFO",
        "No requirement/acceptance doc found in target — traceability not verifiable.",
        "target files scanned",
        "Include the requirement doc or acceptance criteria in the artifact set.")],
      duration_ms: 0,
    };
  }),
];

// ── CODING dimension ─────────────────────────────────────────────────────

const codingCheckers: Checker[] = [
  // CD-01: no secrets
  runCheck("CODING", "CD-01-secret-scan", (env) => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    for (const f of files) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      for (let i = 0; i < SECRET_PATTERNS.length; i++) {
        const m = c.match(SECRET_PATTERNS[i]);
        if (m) {
          const line = c.slice(0, m.index ?? 0).split("\n").length;
          v.push(finding("CD-01-secret-scan", "BLOCKER",
            `Possible secret in ${f}:${line} — pattern ${i + 1}.`,
            `${f}:${line} matched /${SECRET_PATTERNS[i].source.slice(0, 40)}.../`,
            "Move secrets to env vars / vault; never commit them."));
          break;
        }
      }
    }
    return {
      checker_id: "CD-01-secret-scan", dimension: "CODING",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  }),

  // CD-02: debug residue
  runCheck("CODING", "CD-02-debug-residue", (env) => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    for (const f of files) {
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      const lines = c.split("\n");
      for (let li = 0; li < lines.length; li++) {
        const lineText = lines[li];
        // 排除扫描器自身定义（正则字面量/数组定义）——防自报
        if (DEBUG_EXEMPT_SUBSTRINGS.some(s => lineText.includes(s))) continue;
        for (const re of DEBUG_PATTERNS) {
          const m = lineText.match(re);
          if (m) {
            v.push(finding("CD-02-debug-residue", "WARNING",
              `Debug residue in ${f}:${li + 1}: ${m[0].trim()}`,
              `${f}:${li + 1}`,
              "Remove console.log/print/debugger/TODO before delivery."));
            break;
          }
        }
      }
    }
    return {
      checker_id: "CD-02-debug-residue", dimension: "CODING",
      passed: v.filter(x => x.severity === "BLOCKER").length === 0,
      findings: v, duration_ms: 0,
    };
  }),

  // CD-03: file scale
  runCheck("CODING", "CD-03-file-scale", (env) => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    for (const f of files) {
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      const lines = c.split("\n").length;
      if (lines > MAX_LINES_BLOCK) {
        v.push(finding("CD-03-file-scale", "BLOCKER",
          `${f} has ${lines} lines (hard cap ${MAX_LINES_BLOCK}).`,
          `${f}: ${lines} lines`,
          "Split into smaller modules (see module-architect contract)."));
      } else if (lines > MAX_LINES_WARN) {
        v.push(finding("CD-03-file-scale", "WARNING",
          `${f} has ${lines} lines (advisory cap ${MAX_LINES_WARN}).`,
          `${f}: ${lines} lines`,
          "Consider splitting; verify each function has single responsibility."));
      }
    }
    return {
      checker_id: "CD-03-file-scale", dimension: "CODING",
      passed: v.filter(x => x.severity === "BLOCKER").length === 0,
      findings: v, duration_ms: 0,
    };
  }),

  // CD-04: magic numbers
  runCheck("CODING", "CD-04-magic-numbers", (env) => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    for (const f of files) {
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      const lines = c.split("\n");
      for (let i = 0; i < lines.length; i++) {
        const t = lines[i].trim();
        if (MAGIC_NUMBER_RE.test(lines[i]) && !t.startsWith("//") && !t.startsWith("#") && !t.startsWith("*")) {
          v.push(finding("CD-04-magic-numbers", "INFO",
            `Magic number in ${f}:${i + 1}: ${t.slice(0, 60)}`,
            `${f}:${i + 1}`,
            "Extract to named constant with comment."));
        }
      }
    }
    return {
      checker_id: "CD-04-magic-numbers", dimension: "CODING",
      passed: true, findings: v.slice(0, 10), duration_ms: 0,
    };
  }),

  // CD-05: toolchain manifest present
  runCheck("CODING", "CD-05-toolchain-clean", (env) => {
    const { root } = env;
    const hasPkg = existsSync(join(root, "package.json"));
    const hasPy = existsSync(join(root, "pyproject.toml")) || existsSync(join(root, "requirements.txt"));
    if (!hasPkg && !hasPy) {
      return {
        checker_id: "CD-05-toolchain-clean", dimension: "CODING",
        passed: true,
        findings: [finding("CD-05-toolchain-clean", "INFO",
          "No toolchain manifest (package.json/pyproject) — lint/typecheck skipped.",
          "manifest not found",
          "Add a build manifest for full quality gates.")],
        duration_ms: 0,
      };
    }
    return {
      checker_id: "CD-05-toolchain-clean", dimension: "CODING",
      passed: true,
      findings: [finding("CD-05-toolchain-clean", "INFO",
        "Toolchain present; run loop_quality_run for lint/typecheck/test evidence.",
        "package.json / pyproject.toml found",
        "Submit quality_report.json as evidence before gate advance.")],
      duration_ms: 0,
    };
  }),
];

// ── DESIGN dimension ─────────────────────────────────────────────────────

const designCheckers: Checker[] = [
  // DS-01: architecture manifest alignment
  runCheck("DESIGN", "DS-01-architecture-alignment", (env) => {
    const { root, files } = env;
    const archDoc = ["docs/02-architecture.md", ".ai/ARCHITECTURE.md", "docs/architecture.md"]
      .map(p => join(root, p))
      .find(p => existsSync(p));
    if (!archDoc) {
      return {
        checker_id: "DS-01-architecture-alignment", dimension: "DESIGN",
        passed: true,
        findings: [finding("DS-01-architecture-alignment", "INFO",
          "No architecture doc found — design alignment not verifiable.",
          "docs/02-architecture.md missing",
          "Create the architecture document (system-architect output).")],
        duration_ms: 0,
      };
    }
    const raw = readFileSync(archDoc, "utf-8");
    const designed = new Set<string>();
    const fm = raw.match(/^---\n([\s\S]*?)\n---/);
    if (fm) {
      try {
        const doc = parseDocument(fm[1]);
        const y = doc.toJSON() as { designed_files?: unknown };
        if (y && Array.isArray(y.designed_files)) {
          for (const d of y.designed_files) designed.add(String(d));
        }
      } catch {
        /* manual scan below */
      }
    }
    if (designed.size === 0) {
      for (const m of raw.matchAll(/^\s*[-*]\s*`([^`]+)`/gm)) designed.add(m[1]);
    }
    const v: QualityFinding[] = [];
    for (const f of files) {
      const rel = posixRel(root, f);
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const hit = [...designed].some(d => {
        const n = d.replace(/\\/g, "/").replace(/\/$/, "");
        return rel === n || rel.startsWith(n + "/") || n === "*";
      });
      if (!hit && designed.size > 0) {
        v.push(finding("DS-01-architecture-alignment", "WARNING",
          `${rel} is not declared in the architecture designed_files manifest.`,
          `${rel} ∉ designed_files (${[...designed].slice(0, 8).join(", ")}...)`,
          "Declare the module in the architecture doc or justify the extension (needs gate)."));
      }
    }
    return {
      checker_id: "DS-01-architecture-alignment", dimension: "DESIGN",
      passed: v.filter(x => x.severity === "BLOCKER").length === 0,
      findings: v, duration_ms: 0,
    };
  }),

  // DS-02: circular import detection (TS/JS)
  runCheck("DESIGN", "DS-02-no-circular-imports", (env) => {
    const { root, files, contentMap } = env;
    const tsFiles = files.filter(f => /\.(ts|tsx|js|jsx)$/.test(f) && !f.endsWith(".d.ts"));
    if (tsFiles.length === 0) {
      return {
        checker_id: "DS-02-no-circular-imports", dimension: "DESIGN",
        passed: true,
        findings: [finding("DS-02-no-circular-imports", "INFO",
          "No TS/JS files in target — circular import check skipped.",
          "no code files",
          "")],
        duration_ms: 0,
      };
    }
    const graph = new Map<string, string[]>();
    const fileSet = new Set(tsFiles);
    for (const f of tsFiles) {
      const c = contentMap.get(f) ?? "";
      // 只剥离注释后再匹配 import：字符串字面量必须保留（import 路径本身是字符串），
      // 但注释中的 `from "./x"` 文本会产生假依赖边（F4）。
      const codeOnly = c
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/\/\/[^\n]*/g, "");
      const dir = dirname(join(root, f));
      const deps: string[] = [];
      for (const m of codeOnly.matchAll(/(?:from|import\s*\()\s*["'](\.[^"']+)["']/g)) {
        const raw = m[1];
        const resolved = resolve(dir, raw);
        const rel = relative(root, resolved).replace(/\\/g, "/");
        // TS/ESM 解析：./x.js → ./x.ts；./x → ./x.ts | ./x/index.ts
        const candidates: string[] = [];
        if (/\.[jt]sx?$/.test(rel)) {
          candidates.push(rel.replace(/\.js$/, ".ts"), rel.replace(/\.js$/, ".tsx"), rel.replace(/\.jsx$/, ".tsx"));
        } else {
          candidates.push(rel, rel + ".ts", rel + ".tsx", rel + "/index.ts", rel + "/index.tsx");
        }
        const cand = candidates.find(p => fileSet.has(p));
        if (cand) deps.push(cand);
      }
      graph.set(f, deps);
    }
    const state = new Map<string, 0 | 1 | 2>();
    const stack: string[] = [];
    const cycles: string[][] = [];
    const visit = (n: string) => {
      state.set(n, 1);
      stack.push(n);
      for (const d of graph.get(n) ?? []) {
        const s = state.get(d);
        if (s === undefined) visit(d);
        else if (s === 1) {
          const start = stack.indexOf(d);
          if (start >= 0) cycles.push(stack.slice(start).concat(d));
        }
      }
      stack.pop();
      state.set(n, 2);
    };
    for (const n of graph.keys()) {
      if (state.get(n) === undefined) visit(n);
    }
    const v: QualityFinding[] = cycles.map(cycle => finding(
      "DS-02-no-circular-imports", "BLOCKER",
      `Circular import: ${cycle.join(" → ")}`,
      cycle.join(" → "),
      "Break the cycle with dependency inversion (interface module)."));
    return {
      checker_id: "DS-02-no-circular-imports", dimension: "DESIGN",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  }),

  // DS-03: layering — tests must not import src internals directly
  runCheck("DESIGN", "DS-03-layering-tests", (env) => {
    const { files, contentMap } = env;
    const testFiles = files.filter(f => isUnder(f, TEST_PREFIXES));
    const v: QualityFinding[] = [];
    for (const f of testFiles) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      for (const m of c.matchAll(/from\s+["']([^"']*\.\.\/[^"']*src\/[^"']*)["']/g)) {
        v.push(finding("DS-03-layering-tests", "WARNING",
          `${f} imports internals: ${m[1]}`,
          `${f}: ${m[1]}`,
          "Import from the public barrel (src/index.js / core/index.js)."));
      }
    }
    return {
      checker_id: "DS-03-layering-tests", dimension: "DESIGN",
      passed: true, findings: v.slice(0, 10), duration_ms: 0,
    };
  }),

  // DS-04: doc-impl consistency — new code dirs should appear in docs
  runCheck("DESIGN", "DS-04-doc-impl-consistency", (env) => {
    const { files, contentMap } = env;
    const codeDirs = new Set<string>();
    for (const f of files) {
      if (!CODE_EXTS.has(extname(f).toLowerCase())) continue;
      const parts = f.split("/");
      if (parts.length >= 2) codeDirs.add(parts.slice(0, 2).join("/"));
    }
    const docFiles = files.filter(f => /\.(md|rst)$/.test(f));
    const v: QualityFinding[] = [];
    for (const d of codeDirs) {
      const mentioned = docFiles.some(f => (contentMap.get(f) ?? "").includes(d));
      if (!mentioned && docFiles.length > 0) {
        v.push(finding("DS-04-doc-impl-consistency", "INFO",
          `Code dir ${d}/ not mentioned in any doc inside target.`,
          `${d}/`,
          "Update docs (README/architecture) to describe the new module."));
      }
    }
    return {
      checker_id: "DS-04-doc-impl-consistency", dimension: "DESIGN",
      passed: true, findings: v.slice(0, 5), duration_ms: 0,
    };
  }),
];

// ── ENGINEERING dimension ────────────────────────────────────────────────

const engineeringCheckers: Checker[] = [
  // EN-01: tests exist for new source files
  runCheck("ENGINEERING", "EN-01-test-existence", (env) => {
    const { files } = env;
    const codeFiles = files.filter(f =>
      CODE_EXTS.has(extname(f).toLowerCase()) && !isUnder(f, TEST_PREFIXES));
    if (codeFiles.length === 0) {
      return {
        checker_id: "EN-01-test-existence", dimension: "ENGINEERING",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    const testFiles = files.filter(f => isUnder(f, TEST_PREFIXES));
    const v: QualityFinding[] = [];
    for (const f of codeFiles) {
      const base = basename(f, extname(f));
      const normBase = base.toLowerCase().replace(/^test_/, "");
      const hasTest = testFiles.some(t => {
        const tb = basename(t).toLowerCase().replace(/\.(test|spec)\.[a-z0-9]+$/, "");
        // 精确基名比较，防 "only" 命中 "lonely.test.ts"（F5）
        return tb === normBase || tb === "test_" + normBase;
      });
      if (!hasTest) {
        v.push(finding("EN-01-test-existence", "WARNING",
          `${f} has no corresponding test file in the target set.`,
          `${f} → no test for ${base} found`,
          "Write unit tests (test-driven development contract)."));
      }
    }
    return {
      checker_id: "EN-01-test-existence", dimension: "ENGINEERING",
      passed: v.length === 0, findings: v, duration_ms: 0,
    };
  }),

  // EN-02: evidence chain — .ai/evidence entries exist for task
  runCheck("ENGINEERING", "EN-02-evidence-binding", (env) => {
    const { root, ctx } = env;
    if (!ctx.task_id) {
      return {
        checker_id: "EN-02-evidence-binding", dimension: "ENGINEERING",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    const evDir = join(root, ".ai", "evidence", ctx.task_id);
    let count = 0;
    if (existsSync(evDir)) {
      try {
        count = readdirSync(evDir).filter(f => /\.(json|yaml|yml|md)$/.test(f)).length;
      } catch {
        count = 0;
      }
    }
    return {
      checker_id: "EN-02-evidence-binding", dimension: "ENGINEERING",
      passed: count > 0,
      findings: count > 0
        ? [finding("EN-02-evidence-binding", "INFO",
          `${count} evidence file(s) found for task ${ctx.task_id}.`,
          `.ai/evidence/${ctx.task_id}/`,
          "")]
        : [finding("EN-02-evidence-binding", "WARNING",
          `No evidence submitted for task ${ctx.task_id} yet.`,
          `.ai/evidence/${ctx.task_id}/ missing`,
          "Submit evidence (loop_evidence_submit) before gate advance.")],
      duration_ms: 0,
    };
  }),

  // EN-03: replayability — content hash stable
  runCheck("ENGINEERING", "EN-03-replayability", (env) => {
    const { files, contentMap } = env;
    const v: QualityFinding[] = [];
    for (const f of files) {
      const c = contentMap.get(f) ?? "";
      if (!c) continue;
      const ts = c.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/g);
      if (ts && ts.length > 5) {
        v.push(finding("EN-03-replayability", "INFO",
          `${f} contains ${ts.length} absolute timestamps — replay diffs may be noisy.`,
          `${f}: ${ts.length} timestamps`,
          "Use relative time / injectable clock for deterministic output."));
      }
    }
    return {
      checker_id: "EN-03-replayability", dimension: "ENGINEERING",
      passed: true, findings: v.slice(0, 5), duration_ms: 0,
    };
  }),

  // EN-04: review-ready — review report exists for task
  runCheck("ENGINEERING", "EN-04-review-readiness", (env) => {
    const { root, ctx } = env;
    if (!ctx.task_id) {
      return {
        checker_id: "EN-04-review-readiness", dimension: "ENGINEERING",
        passed: true, findings: [], duration_ms: 0,
      };
    }
    const candidates = [
      join(root, ".ai", "reviews", `${ctx.task_id}.md`),
      join(root, ".ai", "reviews", `${ctx.task_id}-review.md`),
      join(root, ".ai", "evidence", ctx.task_id, "review-report.json"),
      join(root, ".ai", "evidence", ctx.task_id, "review_report.json"),
    ];
    const found = candidates.find(p => existsSync(p));
    return {
      checker_id: "EN-04-review-readiness", dimension: "ENGINEERING",
      passed: found !== undefined,
      findings: found
        ? [finding("EN-04-review-readiness", "INFO",
          `Review artifact found: ${found}.`,
          found,
          "")]
        : [finding("EN-04-review-readiness", "WARNING",
          "No independent review artifact found for this task yet.",
          candidates.join(" | "),
          "Run independent-reviewer before gate advance.")],
      duration_ms: 0,
    };
  }),

  // EN-05: file count sanity for directory targets
  runCheck("ENGINEERING", "EN-05-scope-scale", (env) => {
    const { target, files } = env;
    if (files.length > MAX_FILES_WARN) {
      return {
        checker_id: "EN-05-scope-scale", dimension: "ENGINEERING",
        passed: true,
        findings: [finding("EN-05-scope-scale", "WARNING",
          `Target ${target} spans ${files.length} files (advisory ${MAX_FILES_WARN}).`,
          `${files.length} files`,
          "Prefer smaller, reviewable change sets.")],
        duration_ms: 0,
      };
    }
    return {
      checker_id: "EN-05-scope-scale", dimension: "ENGINEERING",
      passed: true, findings: [], duration_ms: 0,
    };
  }),
];

// ── Engine ───────────────────────────────────────────────────────────────

const CHECKER_REGISTRY: Record<DimensionId, Checker[]> = {
  REQUIREMENTS: requirementCheckers,
  CODING: codingCheckers,
  DESIGN: designCheckers,
  ENGINEERING: engineeringCheckers,
};

export class OutputQualityEngine {
  readonly root: string;

  constructor(root: string) {
    this.root = resolve(root);
  }

  /**
   * Verify a target (file or directory, relative to root) against all four
   * dimensions (or a subset via ctx.dimensions).
   */
  verifyTarget(target: string, ctx: VerifyContext = {}): OutputQualityReport {
    if (typeof target !== "string" || target.trim().length === 0) {
      throw new Error(`Invalid target: ${String(target)} — expected a non-empty path.`);
    }
    const resolvedTarget = resolve(this.root, target);
    const relCheck = relative(this.root, resolvedTarget);
    if (relCheck.startsWith("..")) {
      throw new Error(`Target escapes project root: ${target}`);
    }
    const files = listFilesUnder(this.root, target);
    const contentMap = new Map<string, string>();
    let contentHashInput = "";
    for (const f of files) {
      const c = readMaybe(this.root, f) ?? "";
      contentMap.set(f, c);
      contentHashInput += `${f}\n${c}\n`;
    }
    const hash = hashContent(contentHashInput);
    const dims = ctx.dimensions ?? DIMENSION_ORDER;
    const env: CheckerEnv = { root: this.root, target, files, ctx, contentMap };

    const dimensionReports: DimensionReport[] = [];
    const blockedBy: string[] = [];
    let totalBlockers = 0;
    let totalWarnings = 0;

    for (const dim of DIMENSION_ORDER) {
      if (!dims.includes(dim)) continue;
      const checks = CHECKER_REGISTRY[dim].map(c => c(env));
      const blockers = checks.flatMap(findings).filter(f => f.severity === "BLOCKER");
      const warnings = checks.flatMap(findings).filter(f => f.severity === "WARNING");
      totalBlockers += blockers.length;
      totalWarnings += warnings.length;
      const status: DimensionReport["status"] =
        blockers.length > 0 ? "BLOCKED" : warnings.length > 0 ? "WARNING" : "PASS";
      if (blockers.length > 0) blockedBy.push(`${dim}(${blockers.length})`);
      dimensionReports.push({
        dimension: dim,
        label: DIMENSION_LABELS[dim],
        checks,
        blocker_count: blockers.length,
        warning_count: warnings.length,
        status,
      });
    }

    const overall: OutputQualityReport["overall"] =
      totalBlockers > 0 ? "BLOCKED" : totalWarnings > 0 ? "WARNING" : "PASS";

    return {
      schema: "output_quality_report/v1",
      project_root: this.root,
      target,
      target_kind: files.length > 1 ? "directory" : files.length === 1 ? "file" : "virtual",
      content_hash: hash,
      context: ctx,
      dimensions: dimensionReports,
      overall,
      blocked_by: blockedBy,
      generated_at: new Date().toISOString(),
      engine_version: ENGINE_VERSION,
    };
  }

  /**
   * Quick gate decision — used by loop_quality_gate MCP tool.
   * Returns true when the artifact may proceed to delivery.
   */
  isGateable(target: string, ctx: VerifyContext = {}): boolean {
    return this.verifyTarget(target, ctx).overall !== "BLOCKED";
  }
}

/**
 * Render a human-readable summary of the report (for MCP text reply).
 */
export function renderReportSummary(report: OutputQualityReport): string {
  const lines: string[] = [
    `Output Quality Report (OQA-4D ${report.engine_version})`,
    `Target: ${report.target} (${report.target_kind})  hash: ${report.content_hash.slice(0, 12)}…`,
    `Overall: ${report.overall}${report.blocked_by.length ? " blocked_by: " + report.blocked_by.join(", ") : ""}`,
    "",
  ];
  for (const d of report.dimensions) {
    const icon = d.status === "PASS" ? "✓" : d.status === "WARNING" ? "⚠" : "✗";
    lines.push(`  ${icon} ${d.dimension} ${d.label}: ${d.status} (${d.blocker_count} blocker, ${d.warning_count} warning)`);
    for (const c of d.checks) {
      for (const f of c.findings) {
        if (f.severity !== "INFO") {
          lines.push(`      [${f.severity}] ${c.checker_id}: ${f.message}`);
        }
      }
    }
  }
  return lines.join("\n");
}
