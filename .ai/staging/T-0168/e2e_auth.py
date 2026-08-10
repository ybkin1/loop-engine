#!/usr/bin/env python3
"""e2e_auth.py — OQA-5D AUTHENTICITY 维度端到端实测（临时项目）"""
import json
import subprocess
import tempfile
import os
from pathlib import Path

node_script = r"""
const { OutputQualityEngine, renderReportSummary } = require("./dist/src/core/output_quality.js");
const { mkdtempSync, writeFileSync, mkdirSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, dirname } = require("node:path");

const root = mkdtempSync(join(tmpdir(), "oqa5-e2e-"));
function write(rel, content) {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}
write(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-9001\ncurrent_phase: S4\n");
write(".ai/tasks/T-9001.md", [
  "---",
  "task_id: T-9001",
  "allowed_paths:",
  "  - src/",
  "  - tests/",
  "  - docs/",
  "  - .ai/",
  "---",
  "# T-9001",
  "## 可验证验收标准",
  "1. **[AC-01]** feature works",
].join("\n"));

// 幻觉：import 不存在的模块
write("src/hallucination.ts", 'import { ghost } from "./ghost-module.js";\nexport const h = ghost;\n');
// 编造：证据哈希不符
write(".ai/evidence/T-9001/fake.json", JSON.stringify({ content: "x", content_hash: "0".repeat(64) }));
// 偷懒：占位符
write("src/lazy.ts", "// TODO: implement\nexport function lazy(): never { throw new Error('NotImplemented'); }\n");
// 测试质量差
write("src/real.ts", "export const real = 1;\n");
write("tests/real.test.ts", "import { real } from '../src/real.js';\nexpect(real).toBe(1);\n");

const engine = new OutputQualityEngine(root);
const report = engine.verifyTarget("src", { task_id: "T-9001", phase: "S4" });
const auth = report.dimensions.find(d => d.dimension === "AUTHENTICITY");
console.log(JSON.stringify({
  schema: report.schema,
  overall: report.overall,
  blocked_by: report.blocked_by,
  auth_status: auth.status,
  findings: auth.checks.flatMap(c => c.findings.filter(f => f.severity !== "INFO"))
    .map(f => `${f.severity} ${f.checker_id}: ${f.message.slice(0, 70)}`),
}, null, 2));
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
    print("STDERR:", proc.stderr[:400])
print("EXIT:", proc.returncode)
