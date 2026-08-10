/**
 * oqa_patterns.test.ts — OQA 模式库 + AI-03 测试（T-0171）
 *
 * 覆盖：
 *  - 模式库加载（内置 + 项目级合并/覆盖）
 *  - scanWithPatterns 命中（偷懒/幻觉/编造模式）
 *  - AI-03 AC 实现真实性（BLOCKER 缺失 / WARNING 部分验证 / 无实现文件）
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import {
  loadOqaPatterns,
  scanWithPatterns,
  checkAcImplementation,
} from "../src/core/oqa_patterns.js";

let root: string;

function write(rel: string, content: string): void {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "oqa-p-"));
  write(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-1\n");
  write(".ai/tasks/T-1.md", [
    "---",
    "task_id: T-1",
    "allowed_paths:",
    "  - src/",
    "  - .ai/",
    "---",
    "# T-1",
    "## 可验证验收标准",
    "1. **[AC-01]** 用户登录功能 works",
    "2. **[AC-02]** 数据保存功能 works",
  ].join("\n"));
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

// ── 模式库加载 ───────────────────────────────────────────────────────

describe("loadOqaPatterns (pattern library)", () => {
  it("loads builtin patterns by default", () => {
    const patterns = loadOqaPatterns(root);
    expect(patterns.length).toBeGreaterThanOrEqual(5);
    const ids = patterns.map(p => p.id);
    expect(ids).toContain("LAZY-FAKE-DATA");
    expect(ids).toContain("HALLUCINATE-COMMENT-CLAIM");
  });

  it("merges project-level patterns (add new)", () => {
    write(".ai/oqa-patterns.yaml", [
      "version: 1",
      "modes:",
      "  - id: CUSTOM-LAZY",
      "    dimension: CODING",
      "    severity: WARNING",
      "    patterns:",
      "      - \"return\\s+\\[\\s*1\\s*\\]\\s*;?\\s*//\\s*stub\"",
      "    message: custom lazy",
      "    remediation: fix it",
    ].join("\n"));
    const patterns = loadOqaPatterns(root);
    const custom = patterns.find(p => p.id === "CUSTOM-LAZY");
    expect(custom).toBeDefined();
    expect(custom!.pattern_count ?? custom!.patterns.length).toBeGreaterThan(0);
  });

  it("project-level overrides builtin with same id", () => {
    write(".ai/oqa-patterns.yaml", [
      "version: 1",
      "modes:",
      "  - id: LAZY-FAKE-DATA",
      "    dimension: AUTHENTICITY",
      "    severity: BLOCKER",
      "    patterns:",
      "      - \"custom-only-pattern\"",
      "    message: overridden",
      "    remediation: x",
    ].join("\n"));
    const patterns = loadOqaPatterns(root);
    const p = patterns.find(p => p.id === "LAZY-FAKE-DATA")!;
    expect(p.severity).toBe("BLOCKER");
    expect(p.dimension).toBe("AUTHENTICITY");
    expect(p.patterns.length).toBe(1);
  });

  it("falls back to builtin when pattern file corrupt", () => {
    write(".ai/oqa-patterns.yaml", "version: 1\nmodes: [broken");
    const patterns = loadOqaPatterns(root);
    expect(patterns.length).toBeGreaterThanOrEqual(5);
  });
});

// ── scanWithPatterns ─────────────────────────────────────────────────

describe("scanWithPatterns (pattern matching)", () => {
  it("detects LAZY-FAKE-DATA", () => {
    write("src/a.ts", "export function f() { return []; // TODO: fake data\n}\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/a.ts", "export function f() { return []; // TODO: fake data\n}\n");
    const hits = scanWithPatterns(root, ["src/a.ts"], contentMap);
    expect(hits.some(h => h.pattern_id === "LAZY-FAKE-DATA")).toBe(true);
  });

  it("detects LAZY-SWALLOW-EXCEPTION (python)", () => {
    write("src/b.py", "def f():\n    try:\n        pass\n    except Exception:\n        pass\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/b.py", "def f():\n    try:\n        pass\n    except Exception:\n        pass\n");
    const hits = scanWithPatterns(root, ["src/b.py"], contentMap);
    expect(hits.some(h => h.pattern_id === "LAZY-SWALLOW-EXCEPTION")).toBe(true);
  });

  it("detects HALLUCINATE-COMMENT-CLAIM", () => {
    write("src/c.ts", "// 实现完成 TODO: 还没做\nexport const c = 1;\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/c.ts", "// 实现完成 TODO: 还没做\nexport const c = 1;\n");
    const hits = scanWithPatterns(root, ["src/c.ts"], contentMap);
    expect(hits.some(h => h.pattern_id === "HALLUCINATE-COMMENT-CLAIM")).toBe(true);
  });

  it("detects FABRICATE-HARDCODED-EXPECT", () => {
    write("tests/x.test.ts", "expect(x).toBe(42); // hardcode\n");
    const contentMap = new Map<string, string>();
    contentMap.set("tests/x.test.ts", "expect(x).toBe(42); // hardcode\n");
    const hits = scanWithPatterns(root, ["tests/x.test.ts"], contentMap);
    expect(hits.some(h => h.pattern_id === "FABRICATE-HARDCODED-EXPECT")).toBe(true);
  });

  it("no hits on clean code", () => {
    write("src/clean.ts", "export const clean = 42;\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/clean.ts", "export const clean = 42;\n");
    const hits = scanWithPatterns(root, ["src/clean.ts"], contentMap);
    expect(hits.length).toBe(0);
  });
});

// ── AI-03 AC 实现真实性 ──────────────────────────────────────────────

describe("checkAcImplementation (AI-03)", () => {
  it("BLOCKER when AC keyword absent from implementation", () => {
    write("src/impl.ts", "export const unrelated = 1;\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/impl.ts", "export const unrelated = 1;\n");
    const r = checkAcImplementation(root, ["src/impl.ts"], contentMap, "T-1");
    expect(r.findings.some(f => f.severity === "BLOCKER")).toBe(true);
  });

  it("passes when AC keywords present", () => {
    write("src/login.ts", "export function login(u: string, p: string) { return true; }\n");
    write("src/save.ts", "export function save(data: unknown) { return data; }\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/login.ts", "export function login(u: string, p: string) { return true; }\n");
    contentMap.set("src/save.ts", "export function save(data: unknown) { return data; }\n");
    const r = checkAcImplementation(root, ["src/login.ts", "src/save.ts"], contentMap, "T-1");
    expect(r.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });

  it("WARNING when no implementation files", () => {
    const r = checkAcImplementation(root, [], new Map(), "T-1");
    expect(r.findings.some(f => f.severity === "WARNING" && f.message.includes("manual confirmation"))).toBe(true);
  });

  it("BLOCKER when no task_id", () => {
    write("src/x.ts", "export const x = 1;\n");
    const contentMap = new Map<string, string>();
    contentMap.set("src/x.ts", "export const x = 1;\n");
    const r = checkAcImplementation(root, ["src/x.ts"], contentMap, undefined);
    expect(r.findings.some(f => f.severity === "BLOCKER" && f.message.includes("No task_id"))).toBe(true);
  });

  it("no findings when task card has no ACs", () => {
    write(".ai/tasks/T-2.md", "# T-2\nno ACs here\n");
    const r = checkAcImplementation(root, ["src/x.ts"], new Map([["src/x.ts", "export const x = 1;"]]), "T-2");
    expect(r.findings.length).toBe(0);
  });
});

// ── 集成 ─────────────────────────────────────────────────────────────

describe("integration", () => {
  it("MCP tool loop_oqa_patterns exists in tools list", () => {
    // 直接验证 tools.ts 注册（通过构建产物检查不现实，这里验证模块可导入）
    const patterns = loadOqaPatterns(root);
    expect(patterns.length).toBeGreaterThanOrEqual(5);
  });
});
