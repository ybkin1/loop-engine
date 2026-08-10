/**
 * authenticity.test.ts — AUTHENTICITY dimension tests (OQA-5D, T-0168)
 *
 * Covers all 10 checkers with positive & negative cases:
 *  AH-01 reference-existence   AH-02 file-ref-existence
 *  AF-01 evidence-authenticity AF-02 completion-claims
 *  AL-01 placeholder-detection AL-02 test-quality
 *  AO-01 dead-code             AO-02 ghost-interfaces
 *  AI-01 doc-impl-drift        AI-02 state-artifact-drift
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { createHash } from "node:crypto";
import { OutputQualityEngine, renderReportSummary } from "../src/core/output_quality.js";

let root: string;

function write(rel: string, content: string): void {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
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
    "  - .ai/",
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
  root = mkdtempSync(join(tmpdir(), "auth-"));
  initProject();
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

function authDim(report: ReturnType<OutputQualityEngine["verifyTarget"]>) {
  return report.dimensions.find(d => d.dimension === "AUTHENTICITY")!;
}

function findCheck(report: ReturnType<OutputQualityEngine["verifyTarget"]>, id: string) {
  const dim = authDim(report);
  return dim.checks.find(c => c.checker_id === id)!;
}

// ── AH-01 reference-existence ─────────────────────────────────────────

describe("AH-01 reference-existence (hallucination)", () => {
  it("BLOCKER when import target does not exist", () => {
    write("src/a.ts", 'import { x } from "./ghost.js";\nexport const a = x;\n');
    const report = new OutputQualityEngine(root).verifyTarget("src/a.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AH-01-reference-existence");
    expect(c.findings.some(f => f.severity === "BLOCKER" && f.message.includes("ghost"))).toBe(true);
  });

  it("passes when import target exists", () => {
    write("src/a.ts", 'import { b } from "./b.js";\nexport const a = b;\n');
    write("src/b.ts", "export const b = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AH-01-reference-existence");
    expect(c.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });

  it("BLOCKER on python missing relative module import", () => {
    write("src/main.py", "from .ghost_module import helper\ndef run():\n    return helper()\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AH-01-reference-existence");
    expect(c.findings.some(f => f.severity === "BLOCKER" && f.message.includes("ghost_module"))).toBe(true);
  });

  it("passes on python stdlib imports (no false positive)", () => {
    write("src/stdlib.py", "import os\nimport json\nfrom pathlib import Path\nimport numpy as np\n\ndef run():\n    return Path(os.getcwd())\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AH-01-reference-existence");
    expect(c.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });

  it("BLOCKER on CJS require of missing module", () => {
    write("src/cjs.js", "const ghost = require('./ghost-module.js');\nmodule.exports = ghost;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/cjs.js", { task_id: "T-0001" });
    const c = findCheck(report, "AH-01-reference-existence");
    expect(c.findings.some(f => f.severity === "BLOCKER" && f.message.includes("ghost-module"))).toBe(true);
  });

  it("ignores bare package specifiers (checked by manifest elsewhere)", () => {
    write("src/a.ts", 'import { z } from "zod";\nexport const a = z;\n');
    const report = new OutputQualityEngine(root).verifyTarget("src/a.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AH-01-reference-existence");
    expect(c.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });
});

// ── AH-02 file-ref-existence ──────────────────────────────────────────

describe("AH-02 file-ref-existence (hallucination)", () => {
  it("WARNING when markdown link target missing", () => {
    write("docs/readme.md", "# Readme\nSee [guide](./guide.md) for details.\n");
    const report = new OutputQualityEngine(root).verifyTarget("docs", { task_id: "T-0001" });
    const c = findCheck(report, "AH-02-file-ref-existence");
    expect(c.findings.some(f => f.message.includes("guide.md"))).toBe(true);
  });

  it("passes when markdown link target exists", () => {
    write("docs/readme.md", "# Readme\nSee [guide](./guide.md).\n");
    write("docs/guide.md", "# Guide\n");
    const report = new OutputQualityEngine(root).verifyTarget("docs", { task_id: "T-0001" });
    const c = findCheck(report, "AH-02-file-ref-existence");
    expect(c.findings.length).toBe(0);
  });

  it("ignores external URLs", () => {
    write("docs/readme.md", "# Readme\nSee [web](https://example.com/x).\n");
    const report = new OutputQualityEngine(root).verifyTarget("docs", { task_id: "T-0001" });
    const c = findCheck(report, "AH-02-file-ref-existence");
    expect(c.findings.length).toBe(0);
  });
});

// ── AF-01 evidence-authenticity ───────────────────────────────────────

describe("AF-01 evidence-authenticity (fabrication)", () => {
  it("BLOCKER when evidence content_hash does not match content", () => {
    write(".ai/evidence/T-0001/fake.json", JSON.stringify({
      content: "real output",
      content_hash: "f".repeat(64),
    }));
    const report = new OutputQualityEngine(root).verifyTarget(".ai/evidence/T-0001/fake.json", { task_id: "T-0001" });
    const c = findCheck(report, "AF-01-evidence-authenticity");
    expect(c.findings.some(f => f.severity === "BLOCKER" && (f.message.includes("hash") || f.evidence.includes("hash")))).toBe(true);
  });

  it("passes when evidence hash matches", () => {
    const content = "real output";
    const hash = createHash("sha256").update(content, "utf-8").digest("hex");
    write(".ai/evidence/T-0001/ok.json", JSON.stringify({ content, content_hash: hash }));
    const report = new OutputQualityEngine(root).verifyTarget(".ai/evidence/T-0001/ok.json", { task_id: "T-0001" });
    const c = findCheck(report, "AF-01-evidence-authenticity");
    expect(c.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });

  it("BLOCKER when evidence claims artifact that does not exist", () => {
    write(".ai/evidence/T-0001/claim.json", JSON.stringify({
      exit_code: 0,
      artifacts: ["src/never-written.ts"],
    }));
    const report = new OutputQualityEngine(root).verifyTarget(".ai/evidence/T-0001/claim.json", { task_id: "T-0001" });
    const c = findCheck(report, "AF-01-evidence-authenticity");
    expect(c.findings.some(f => f.severity === "BLOCKER" && f.message.includes("never-written"))).toBe(true);
  });
});

// ── AF-02 completion-claims ───────────────────────────────────────────

describe("AF-02 completion-claims (fabrication)", () => {
  it("WARNING when task has ACs but no evidence dir", () => {
    write("src/done.ts", "export const done = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/done.ts", { task_id: "T-0001", phase: "S4" });
    const c = findCheck(report, "AF-02-completion-claims");
    expect(c.findings.some(f => f.message.includes("no evidence"))).toBe(true);
  });

  it("passes when evidence dir exists", () => {
    write(".ai/evidence/T-0001/quality.json", '{"overall":"PASS"}');
    write("src/done.ts", "export const done = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/done.ts", { task_id: "T-0001", phase: "S4" });
    const c = findCheck(report, "AF-02-completion-claims");
    expect(c.findings.filter(f => f.severity === "WARNING").length).toBe(0);
  });
});

// ── AL-01 placeholder-detection ───────────────────────────────────────

describe("AL-01 placeholder-detection (laziness)", () => {
  it("BLOCKER on TODO in code", () => {
    write("src/todo.ts", "// TODO: implement later\nexport const t = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/todo.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AL-01-placeholder-detection");
    expect(c.findings.some(f => f.severity === "BLOCKER" && f.message.includes("TODO"))).toBe(true);
  });

  it("BLOCKER on NotImplemented", () => {
    write("src/stub.ts", "export function stub(): never { throw new Error('NotImplemented'); }\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/stub.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AL-01-placeholder-detection");
    expect(c.findings.some(f => f.severity === "BLOCKER")).toBe(true);
  });

  it("passes on clean code", () => {
    write("src/clean.ts", "export const clean = 42;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/clean.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AL-01-placeholder-detection");
    expect(c.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });

  it("passes on JSX placeholder attribute (no false positive)", () => {
    write("src/input.tsx", "export const Input = () => <input placeholder=\"Enter name\" />;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/input.tsx", { task_id: "T-0001" });
    const c = findCheck(report, "AL-01-placeholder-detection");
    expect(c.findings.filter(f => f.severity === "BLOCKER").length).toBe(0);
  });
});

// ── AL-02 test-quality ────────────────────────────────────────────────

describe("AL-02 test-quality (laziness)", () => {
  it("WARNING on test with 0 assertions", () => {
    write("src/f.ts", "export const f = 1;\n");
    write("tests/f.test.ts", "import { f } from '../src/f.js';\n// no assertions\n");
    const report = new OutputQualityEngine(root).verifyTarget("tests", { task_id: "T-0001" });
    const c = findCheck(report, "AL-02-test-quality");
    expect(c.findings.some(f => f.message.includes("0 assertions"))).toBe(true);
  });

  it("WARNING on happy-path-only test", () => {
    write("src/g.ts", "export const g = 1;\n");
    write("tests/g.test.ts", "import { g } from '../src/g.js';\nexpect(g).toBe(1);\n");
    const report = new OutputQualityEngine(root).verifyTarget("tests", { task_id: "T-0001" });
    const c = findCheck(report, "AL-02-test-quality");
    expect(c.findings.some(f => f.severity === "WARNING" && (f.message.includes("failure-path") || f.evidence.includes("happy-path")))).toBe(true);
  });

  it("passes on test with assertions + failure path", () => {
    write("src/h.ts", "export const h = 1;\n");
    write("tests/h.test.ts", [
      "import { h } from '../src/h.js';",
      "describe('h', () => {",
      "  it('works', () => { expect(h).toBe(1); });",
      "  it('throws on invalid', () => { expect(() => h).toThrow(); });",
      "});",
    ].join("\n"));
    const report = new OutputQualityEngine(root).verifyTarget("tests", { task_id: "T-0001" });
    const c = findCheck(report, "AL-02-test-quality");
    expect(c.findings.filter(f => f.severity === "WARNING").length).toBe(0);
  });

  it("passes on python bare assert tests (no false positive)", () => {
    write("src/pyf.py", "def f(x):\n    return x + 1\n");
    write("tests/test_pyf.py", [
      "from src.pyf import f",
      "def test_add():",
      "    assert f(1) == 2",
      "def test_add_negative():",
      "    assert f(-1) == 0",
      "def test_add_type_error():",
      "    try:",
      "        f('x')",
      "    except TypeError:",
      "        pass",
    ].join("\n"));
    const report = new OutputQualityEngine(root).verifyTarget("tests", { task_id: "T-0001" });
    const c = findCheck(report, "AL-02-test-quality");
    expect(c.findings.filter(f => f.severity === "WARNING" && f.message.includes("0 assertions")).length).toBe(0);
  });
});

// ── AO-01 dead-code ───────────────────────────────────────────────────

describe("AO-01 dead-code (over-engineering)", () => {
  it("WARNING on exported symbol with zero references", () => {
    write("src/util.ts", "export const unusedHelper = () => 42;\nexport const usedHelper = () => 1;\n");
    write("src/main.ts", "import { usedHelper } from './util.js';\nexport const main = usedHelper();\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AO-01-dead-code");
    expect(c.findings.some(f => f.message.includes("unusedHelper"))).toBe(true);
  });

  it("passes when all exports are referenced", () => {
    write("src/util.ts", "export const usedHelper = () => 1;\n");
    write("src/main.ts", "import { usedHelper } from './util.js';\nexport const main = usedHelper();\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AO-01-dead-code");
    expect(c.findings.filter(f => f.severity === "WARNING").length).toBe(0);
  });
});

// ── AO-02 ghost-interfaces ────────────────────────────────────────────

describe("AO-02 ghost-interfaces (over-engineering)", () => {
  it("WARNING on interface with no implementer or caller", () => {
    write("src/types.ts", "export interface GhostInterface { id: string; }\n");
    write("src/main.ts", "export const main = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AO-02-ghost-interfaces");
    expect(c.findings.some(f => f.message.includes("GhostInterface"))).toBe(true);
  });

  it("passes when interface is consumed", () => {
    write("src/types.ts", "export interface UsedInterface { id: string; }\n");
    write("src/main.ts", "import type { UsedInterface } from './types.js';\nexport const main: UsedInterface = { id: 'x' };\n");
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001" });
    const c = findCheck(report, "AO-02-ghost-interfaces");
    expect(c.findings.filter(f => f.severity === "WARNING").length).toBe(0);
  });
});

// ── AI-01 doc-impl-drift ──────────────────────────────────────────────

describe("AI-01 doc-impl-drift (inconsistency)", () => {
  it("WARNING when doc params mismatch signature", () => {
    write("src/api.ts", [
      "/**",
      " * Docs.",
      " * @param a first",
      " * @param b second",
      " */",
      "export function api(a: number): number { return a; }",
    ].join("\n"));
    const report = new OutputQualityEngine(root).verifyTarget("src/api.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AI-01-doc-impl-drift");
    expect(c.findings.some(f => f.message.includes("documents 2 param(s) but declares 1"))).toBe(true);
  });

  it("passes when doc params match signature", () => {
    write("src/api.ts", [
      "/**",
      " * Docs.",
      " * @param a first",
      " */",
      "export function api(a: number): number { return a; }",
    ].join("\n"));
    const report = new OutputQualityEngine(root).verifyTarget("src/api.ts", { task_id: "T-0001" });
    const c = findCheck(report, "AI-01-doc-impl-drift");
    expect(c.findings.filter(f => f.severity === "WARNING").length).toBe(0);
  });
});

// ── AI-02 state-artifact-drift ────────────────────────────────────────

describe("AI-02 state-artifact-drift (inconsistency)", () => {
  it("WARNING when state claims task active but target empty", () => {
    const report = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-0001", phase: "S4" });
    const c = findCheck(report, "AI-02-state-artifact-drift");
    expect(c.findings.some(f => f.severity === "WARNING" && (f.message.includes("no artifacts") || f.evidence.includes("0 files")))).toBe(true);
  });

  it("passes when artifacts exist", () => {
    write("src/real.ts", "export const real = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/real.ts", { task_id: "T-0001", phase: "S4" });
    const c = findCheck(report, "AI-02-state-artifact-drift");
    expect(c.findings.filter(f => f.severity === "WARNING").length).toBe(0);
  });
});

// ── Dimension integration ─────────────────────────────────────────────

describe("AUTHENTICITY dimension integration (OQA-5D)", () => {
  it("appears in DIMENSION_ORDER with 10 checkers", () => {
    write("src/integ.ts", "export const i = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/integ.ts", { task_id: "T-0001" });
    const dim = authDim(report);
    expect(dim.dimension).toBe("AUTHENTICITY");
    expect(dim.checks.length).toBe(10);
  });

  it("report title reflects OQA-5D", () => {
    write("src/t.ts", "export const t = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/t.ts", { task_id: "T-0001" });
    expect(renderReportSummary(report)).toContain("OQA-5D");
  });

  it("AH blocker fails the gate (isGateable false)", () => {
    write("src/bad.ts", 'import { x } from "./nope.js";\nexport const a = x;\n');
    const engine = new OutputQualityEngine(root);
    expect(engine.isGateable("src/bad.ts", { task_id: "T-0001" })).toBe(false);
  });

  it("dimension subset filter includes AUTHENTICITY", () => {
    write("src/sub.ts", "export const s = 1;\n");
    const report = new OutputQualityEngine(root).verifyTarget("src/sub.ts", {
      task_id: "T-0001",
      dimensions: ["AUTHENTICITY"],
    });
    expect(report.dimensions.map(d => d.dimension)).toEqual(["AUTHENTICITY"]);
  });
});
