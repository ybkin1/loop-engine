import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { OutputQualityEngine } from "../src/core/output_quality.js";

let root: string;

function write(rel: string, content: string): void {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}

// 完全复制原测试的 initProject
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
  root = mkdtempSync(join(tmpdir(), "auth-cmp-"));
  initProject();
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

describe("compare", () => {
  it("AF-01 with exact original setup", () => {
    write(".ai/evidence/T-0001/fake.json", JSON.stringify({
      content: "real output",
      content_hash: "f".repeat(64),
    }));
    const report = new OutputQualityEngine(root).verifyTarget(".ai/evidence/T-0001/fake.json", { task_id: "T-0001" });
    const dim = report.dimensions.find(d => d.dimension === "AUTHENTICITY")!;
    const c = dim.checks.find(ck => ck.checker_id === "AF-01-evidence-authenticity")!;
    console.log("target_kind:", report.target_kind);
    console.log("findings:", JSON.stringify(c.findings));
    expect(c.findings.some(f => f.severity === "BLOCKER" && f.message.includes("hash mismatch"))).toBe(true);
  });
});
