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

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "auth-diag-"));
  write(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-0001\n");
  write(".ai/tasks/T-0001.md", "---\ntask_id: T-0001\nallowed_paths:\n  - src/\n  - .ai/\n---\n# T\n## 可验证验收标准\n1. **[AC-01]** works\n");
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

describe("diagnose", () => {
  it("prints AF-01 internals", () => {
    write(".ai/evidence/T-0001/fake.json", JSON.stringify({ content: "real output", content_hash: "f".repeat(64) }));
    const report = new OutputQualityEngine(root).verifyTarget(".ai/evidence/T-0001/fake.json", { task_id: "T-0001" });
    console.log("target_kind:", report.target_kind);
    const dim = report.dimensions.find(d => d.dimension === "AUTHENTICITY");
    console.log("dim exists:", !!dim, "checkers:", dim?.checks.map(c => c.checker_id).join(","));
    const af01 = dim?.checks.find(c => c.checker_id === "AF-01-evidence-authenticity");
    console.log("AF-01 findings:", JSON.stringify(af01?.findings));
    // 直接看 files 列表 —— 需要从 report 无法获得，用引擎内部逻辑模拟
    const { readdirSync, statSync, existsSync } = require("node:fs");
    const { relative, resolve } = require("node:path");
    console.log("evidence exists:", existsSync(join(root, ".ai/evidence/T-0001/fake.json")));
  });
});
