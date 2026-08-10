#!/usr/bin/env python3
"""debug_vitest_env.py — 复现 vitest 环境的路径行为（通过 node 直接跑 vitest 同款代码）"""
import subprocess

# 用 vitest 相同的方式：把调试脚本作为临时测试运行
node_script = r"""
const { OutputQualityEngine } = require("./dist/src/core/output_quality.js");
const { mkdtempSync, writeFileSync, mkdirSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, dirname } = require("node:path");

const root = mkdtempSync(join(tmpdir(), "auth-vit-"));
function write(rel, content) {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}
// 模拟测试的 initProject
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

const engine = new OutputQualityEngine(root);

// AF-01
write(".ai/evidence/T-0001/fake.json", JSON.stringify({ content: "real output", content_hash: "f".repeat(64) }));
const r1 = engine.verifyTarget(".ai/evidence/T-0001/fake.json", { task_id: "T-0001" });
const d1 = r1.dimensions.find(d => d.dimension === "AUTHENTICITY");
console.log("AF-01 target_kind:", r1.target_kind, "files count in report:", "n/a");
const af01 = d1.checks.find(c => c.checker_id === "AF-01-evidence-authenticity");
console.log("AF-01 findings:", JSON.stringify(af01.findings.map(f => f.message.slice(0, 60))));

// AL-02
write("src/g.ts", "export const g = 1;\n");
write("tests/g.test.ts", "import { g } from '../src/g.js';\nexpect(g).toBe(1);\n");
const r2 = engine.verifyTarget("tests", { task_id: "T-0001" });
const d2 = r2.dimensions.find(d => d.dimension === "AUTHENTICITY");
const al02 = d2.checks.find(c => c.checker_id === "AL-02-test-quality");
console.log("AL-02 findings:", JSON.stringify(al02.findings.map(f => f.message.slice(0, 60))));

// AI-02
const r3 = engine.verifyTarget("src", { task_id: "T-0001", phase: "S4" });
const d3 = r3.dimensions.find(d => d.dimension === "AUTHENTICITY");
const ai02 = d3.checks.find(c => c.checker_id === "AI-02-state-artifact-drift");
console.log("AI-02 findings:", JSON.stringify(ai02.findings.map(f => f.message.slice(0, 80))));
console.log("AI-02 target_kind:", r3.target_kind);
"""

proc = subprocess.run(
    ["node", "-e", node_script],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=r"C:\Users\Administrator\.qoder-cn\loop-engine-lab",
)
print(proc.stdout)
if proc.stderr.strip():
    print("STDERR:", proc.stderr[:500])
