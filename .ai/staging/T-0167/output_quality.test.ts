/**
 * output_quality.test.ts — OQA-4D engine tests
 *
 * Covers:
 *  - REQUIREMENTS: task binding, AC coverage, traceability
 *  - CODING: secrets, debug residue, file scale, magic numbers, toolchain
 *  - DESIGN: architecture alignment, circular imports, layering, doc-impl
 *  - ENGINEERING: test existence, evidence, replayability, review, scope
 *  - Report schema & gate decisions
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  OutputQualityEngine,
  renderReportSummary,
  DIMENSION_ORDER,
  ENGINE_VERSION,
} from "../src/core/output_quality.js";

let root: string;

function write(rel: string, content: string): void {
  const p = join(root, rel);
  mkdirSync(require("node:path").dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}

function initProject(): void {
  write(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-0001\ncurrent_phase: S4\n");
  write(".ai/tasks/T-0001.md", [
    "---",
    "task_id: T-0001",
    "allowed_paths:",
    "  - src/",
    "  - tests/",
    "  - docs/",
    "---",
    "# T-0001: sample",
    "## 允许路径",
    "- src/",
    "## 可验证验收标准",
    "1. **[AC-01]** feature works",
    "2. **[AC-02]** tests pass",
  ].join("\n"));
}

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "oqa-"));
  initProject();
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

// ── REQUIREMENTS ─────────────────────────────────────────────────────

describe("REQUIREMENTS dimension", () => {
  it("RQ-01 blocks when no task_id in context", () => {
    write("src/a.ts", "export const a = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/a.ts", {});
    const rq = report.dimensions.find(d => d.dimension === "REQUIREMENTS")!;
    expect(rq.status).toBe("BLOCKED");
    expect(report.overall).toBe("BLOCKED");
    expect(report.blocked_by).toContain("REQUIREMENTS(1)");
  });

  it("RQ-01 blocks when target outside allowed_paths", () => {
    write("outside/x.ts", "export const x = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("outside/x.ts", { task_id: "T-0001" });
    const rq = report.dimensions.find(d => d.dimension === "REQUIREMENTS")!;
    expect(rq.status).toBe("BLOCKED");
  });

  it("RQ-01 passes when target inside allowed_paths", () => {
    write("src/a.ts", "export const a = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/a.ts", { task_id: "T-0001" });
    const rq = report.dimensions.find(d => d.dimension === "REQUIREMENTS")!;
    expect(rq.status).not.toBe("BLOCKED");
  });

  it("RQ-02 warns when ACs unreferenced, passes when referenced", () => {
    write("src/a.ts", "export const a = 1;\n");
    const engine = new OutputQualityEngine(root);
    const unreferenced = engine.verifyTarget("src/a.ts", { task_id: "T-0001" });
    const rq = unreferenced.dimensions.find(d => d.dimension === "REQUIREMENTS")!;
    expect(rq.warning_count).toBeGreaterThan(0);

    write("src/a.ts", "export const a = 1; // [AC-01] [AC-02]\n");
    const referenced = engine.verifyTarget("src/a.ts", { task_id: "T-0001" });
    const rq2 = referenced.dimensions.find(d => d.dimension === "REQUIREMENTS")!;
    expect(rq2.warning_count).toBe(0);
  });

  it("RQ-01 blocks when task card missing", () => {
    write("src/a.ts", "export const a = 1;\n");
    rmSync(join(root, ".ai/tasks"), { recursive: true, force: true });
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/a.ts", { task_id: "T-0001" });
    expect(report.overall).toBe("BLOCKED");
  });
});

// ── CODING ───────────────────────────────────────────────────────────

describe("CODING dimension", () => {
  it("CD-01 blocks on secret patterns", () => {
    write("src/bad.ts", 'const apiKey = "sk-0123456789abcdef0123456789abcdef";\n');
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/bad.ts", { task_id: "T-0001" });
    const cd = report.dimensions.find(d => d.dimension === "CODING")!;
    expect(cd.status).toBe("BLOCKED");
    expect(cd.blocker_count).toBeGreaterThan(0);
  });

  it("CD-01 blocks on private key block", () => {
    write("src/k.ts", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/k.ts", { task_id: "T-0001" });
    expect(report.overall).toBe("BLOCKED");
  });

  it("CD-02 warns on debug residue but does not block alone", () => {
    write("src/dbg.ts", "console.log('x');\nconsole.log('y');\nconsole.log('z');\nexport const d = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/dbg.ts", { task_id: "T-0001" });
    const cd = report.dimensions.find(d => d.dimension === "CODING")!;
    expect(cd.warning_count).toBeGreaterThan(0);
    // Only debug residue → no BLOCKER in CODING
    expect(cd.blocker_count).toBe(0);
  });

  it("CD-03 blocks oversized file (>1200 lines)", () => {
    const lines = Array.from({ length: 1300 }, (_, i) => `// line ${i}`).join("\n");
    write("src/big.ts", lines + "\nexport const big = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/big.ts", { task_id: "T-0001" });
    const cd = report.dimensions.find(d => d.dimension === "CODING")!;
    expect(cd.blocker_count).toBeGreaterThan(0);
  });

  it("CD-03 warns on moderately large file (>400 lines)", () => {
    const lines = Array.from({ length: 500 }, (_, i) => `// line ${i}`).join("\n");
    write("src/med.ts", lines + "\nexport const med = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/med.ts", { task_id: "T-0001" });
    const cd = report.dimensions.find(d => d.dimension === "CODING")!;
    expect(cd.warning_count).toBeGreaterThan(0);
    expect(cd.blocker_count).toBe(0);
  });

  it("clean code passes CODING without findings beyond INFO", () => {
    write("src/clean.ts", "export const clean = 42;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/clean.ts", { task_id: "T-0001" });
    const cd = report.dimensions.find(d => d.dimension === "CODING")!;
    expect(cd.blocker_count).toBe(0);
    expect(cd.warning_count).toBe(0);
  });
});

// ── DESIGN ───────────────────────────────────────────────────────────

describe("DESIGN dimension", () => {
  it("DS-02 blocks on circular imports", () => {
    write("src/a.ts", 'import { b } from "./b.js";\nexport const a = b;\n');
    write("src/b.ts", 'import { a } from "./a.js";\nexport const b = a;\n');
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src", { task_id: "T-0001" });
    const ds = report.dimensions.find(d => d.dimension === "DESIGN")!;
    expect(ds.status).toBe("BLOCKED");
    expect(ds.blocker_count).toBeGreaterThan(0);
  });

  it("DS-02 passes on acyclic imports", () => {
    write("src/a.ts", 'import { b } from "./b.js";\nexport const a = b;\n');
    write("src/b.ts", "export const b = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src", { task_id: "T-0001" });
    const ds = report.dimensions.find(d => d.dimension === "DESIGN")!;
    expect(ds.blocker_count).toBe(0);
  });

  it("DS-01 warns when file not in designed_files manifest", () => {
    write("docs/02-architecture.md", [
      "---",
      "designed_files: [src/declared.ts]",
      "---",
      "# Arch",
      "## modules",
    ].join("\n"));
    write("src/undeclared.ts", "export const u = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/undeclared.ts", { task_id: "T-0001" });
    const ds = report.dimensions.find(d => d.dimension === "DESIGN")!;
    expect(ds.warning_count).toBeGreaterThan(0);
  });

  it("DS-03 warns when tests import src internals", () => {
    write("src/lib/inner.ts", "export const inner = 1;\n");
    write("tests/inner.test.ts", 'import { inner } from "../src/lib/inner.js";\n');
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("tests", { task_id: "T-0001" });
    const ds = report.dimensions.find(d => d.dimension === "DESIGN")!;
    expect(ds.warning_count).toBeGreaterThan(0);
  });
});

// ── ENGINEERING ──────────────────────────────────────────────────────

describe("ENGINEERING dimension", () => {
  it("EN-01 warns when source has no test", () => {
    write("src/only.ts", "export const o = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/only.ts", { task_id: "T-0001" });
    const en = report.dimensions.find(d => d.dimension === "ENGINEERING")!;
    expect(en.warning_count).toBeGreaterThan(0);
  });

  it("EN-01 passes when test exists for source", () => {
    write("src/pair.ts", "export const p = 1;\n");
    write("tests/pair.test.ts", 'import { p } from "../src/pair.js";\n');
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget(".", { task_id: "T-0001" });
    const en = report.dimensions.find(d => d.dimension === "ENGINEERING")!;
    // EN-01 应零 warning；其他 EN 检查器可能产生 INFO/WARNING，因此只看 EN-01
    const en01 = en.checks.find(c => c.checker_id === "EN-01-test-existence")!;
    expect(en01.findings.filter(f => f.severity !== "INFO").length).toBe(0);
  });

  it("EN-02 warns without evidence dir, passes with it", () => {
    write("src/e.ts", "export const e = 1;\n");
    const engine = new OutputQualityEngine(root);
    const before = engine.verifyTarget("src/e.ts", { task_id: "T-0001" });
    const enBefore = before.dimensions.find(d => d.dimension === "ENGINEERING")!;
    const en02Before = enBefore.checks.find(c => c.checker_id === "EN-02-evidence-binding")!;
    expect(en02Before.findings.some(f => f.severity === "WARNING" && f.message.includes("No evidence"))).toBe(true);

    write(".ai/evidence/T-0001/quality.json", '{"overall": "PASS"}');
    const after = engine.verifyTarget("src/e.ts", { task_id: "T-0001" });
    const enAfter = after.dimensions.find(d => d.dimension === "ENGINEERING")!;
    const en02After = enAfter.checks.find(c => c.checker_id === "EN-02-evidence-binding")!;
    expect(en02After.findings.some(f => f.severity === "WARNING")).toBe(false);
  });

  it("EN-04 warns without review artifact", () => {
    write("src/r.ts", "export const r = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/r.ts", { task_id: "T-0001" });
    expect(report.dimensions.find(d => d.dimension === "ENGINEERING")!.warning_count).toBeGreaterThan(0);
  });
});

// ── Report & engine ──────────────────────────────────────────────────

describe("Report schema & engine behavior", () => {
  it("produces output_quality_report/v1 with all 4 dimensions", () => {
    write("src/schema.ts", "export const s = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/schema.ts", { task_id: "T-0001", phase: "S4", role: "R06" });
    expect(report.schema).toBe("output_quality_report/v1");
    expect(report.engine_version).toBe(ENGINE_VERSION);
    expect(report.dimensions.map(d => d.dimension)).toEqual(DIMENSION_ORDER);
    expect(report.context).toEqual({ task_id: "T-0001", phase: "S4", role: "R06" });
    expect(report.content_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(report.generated_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("isGateable returns false when BLOCKED, true otherwise", () => {
    write("src/g.ts", 'const secret = "sk-0123456789abcdef0123456789abcdef";\n');
    const engine = new OutputQualityEngine(root);
    expect(engine.isGateable("src/g.ts", { task_id: "T-0001" })).toBe(false);

    write("src/g.ts", "export const g = 1;\n");
    expect(engine.isGateable("src/g.ts", { task_id: "T-0001" })).toBe(true);
  });

  it("dimension subset restriction works", () => {
    write("src/sub.ts", "export const s = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/sub.ts", {
      task_id: "T-0001",
      dimensions: ["CODING"],
    });
    expect(report.dimensions.map(d => d.dimension)).toEqual(["CODING"]);
  });

  it("missing target produces virtual empty report (not BLOCKED)", () => {
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("nope/missing.ts", { task_id: "T-0001" });
    expect(report.target_kind).toBe("virtual");
    expect(report.overall).not.toBe("BLOCKED");
  });

  it("renderReportSummary contains dimension lines", () => {
    write("src/rep.ts", "export const r = 1;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/rep.ts", { task_id: "T-0001" });
    const text = renderReportSummary(report);
    expect(text).toContain("Output Quality Report");
    expect(text).toContain("REQUIREMENTS");
    expect(text).toContain("ENGINEERING");
  });

  it("directory target aggregates files", () => {
    write("src/a.ts", "export const a = 1;\n");
    write("src/b.ts", "export const b = 2;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src", { task_id: "T-0001" });
    expect(report.target_kind).toBe("directory");
    expect(report.content_hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it("replayability is deterministic for same content", () => {
    write("src/det.ts", "export const det = 1;\n");
    const engine = new OutputQualityEngine(root);
    const r1 = engine.verifyTarget("src/det.ts", { task_id: "T-0001" });
    const r2 = engine.verifyTarget("src/det.ts", { task_id: "T-0001" });
    expect(r1.content_hash).toBe(r2.content_hash);
    expect(r1.overall).toBe(r2.overall);
  });

  // ── 审查边界测试（F4/F5/F8 回归防护）──

  it("F4: DS-02 ignores comments containing from-like text", () => {
    write("src/onlya.ts", "export const a = 1;\n");
    write("src/onlyb.ts", "// comment: import { a } from './onlya.ts'\nexport const b = 2;\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src", { task_id: "T-0001" });
    const ds = report.dimensions.find(d => d.dimension === "DESIGN")!;
    expect(ds.blocker_count).toBe(0);
  });

  it("F5: RQ-02 does not match AC-01 against AC-010", () => {
    write("src/ac10.ts", "export const x = 1; // covers [AC-010] only\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src/ac10.ts", { task_id: "T-0001" });
    const rq = report.dimensions.find(d => d.dimension === "REQUIREMENTS")!;
    const rq02 = rq.checks.find(c => c.checker_id === "RQ-02-ac-reference")!;
    // AC-01/AC-02 不应被 AC-010 满足 → 仍有未覆盖 AC
    expect(rq02.findings.some(f => f.severity === "WARNING" && f.message.includes("not referenced"))).toBe(true);
  });

  it("F5: EN-01 does not pair different basenames", () => {
    write("src/only.ts", "export const o = 1;\n");
    write("tests/lonely.test.ts", "import { x } from './x';\n");
    const engine = new OutputQualityEngine(root);
    const report = engine.verifyTarget("src", { task_id: "T-0001" });
    const en = report.dimensions.find(d => d.dimension === "ENGINEERING")!;
    const en01 = en.checks.find(c => c.checker_id === "EN-01-test-existence")!;
    expect(en01.findings.some(f => f.severity === "WARNING" && f.message.includes("src/only.ts"))).toBe(true);
  });

  it("F3: verifyTarget rejects escape and empty targets", () => {
    write("src/e.ts", "export const e = 1;\n");
    const engine = new OutputQualityEngine(root);
    expect(() => engine.verifyTarget("../outside", { task_id: "T-0001" })).toThrow(/escapes project root/);
    expect(() => engine.verifyTarget("", { task_id: "T-0001" })).toThrow(/Invalid target/);
  });
});
