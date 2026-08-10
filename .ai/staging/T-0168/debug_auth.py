#!/usr/bin/env python3
"""debug_auth.py — 调试 AL-02 / AI-02 检查器实际行为"""
import subprocess

node_script = r"""
const { OutputQualityEngine } = require("./dist/src/core/output_quality.js");
const { mkdtempSync, writeFileSync, mkdirSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, dirname } = require("node:path");

const root = mkdtempSync(join(tmpdir(), "auth-dbg-"));
function write(rel, content) {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}
write(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-0001\ncurrent_phase: S4\n");
write(".ai/tasks/T-0001.md", "---\ntask_id: T-0001\nallowed_paths:\n  - src/\n  - tests/\n  - docs/\n  - .ai/\n---\n# T-0001\n## 可验证验收标准\n1. **[AC-01]** feature works\n");
write("src/g.ts", "export const g = 1;\n");
write("tests/g.test.ts", "import { g } from '../src/g.js';\nexpect(g).toBe(1);\n");

const engine = new OutputQualityEngine(root);
const report = engine.verifyTarget("tests", { task_id: "T-0001" });
const dim = report.dimensions.find(d => d.dimension === "AUTHENTICITY");
console.log("=== AL-02 findings ===");
const al02 = dim.checks.find(c => c.checker_id === "AL-02-test-quality");
console.log(JSON.stringify(al02.findings, null, 2));

console.log("=== AI-02 with empty src target ===");
const report2 = engine.verifyTarget("src", { task_id: "T-0001", phase: "S4" });
const dim2 = report2.dimensions.find(d => d.dimension === "AUTHENTICITY");
const ai02 = dim2.checks.find(c => c.checker_id === "AI-02-state-artifact-drift");
console.log("files:", JSON.stringify(report2.target), report2.target_kind);
console.log(JSON.stringify(ai02.findings, null, 2));

console.log("=== AH-01 with valid import ===");
write("src/b.ts", "export const b = 1;\n");
write("src/a.ts", "import { b } from './b.js';\nexport const a = b;\n");
const report3 = engine.verifyTarget("src", { task_id: "T-0001" });
const dim3 = report3.dimensions.find(d => d.dimension === "AUTHENTICITY");
const ah01 = dim3.checks.find(c => c.checker_id === "AH-01-reference-existence");
console.log("AH-01 blockers:", JSON.stringify(ah01.findings.filter(f => f.severity === "BLOCKER"), null, 2));

console.log("=== AF-01 hash mismatch ===");
write(".ai/evidence/T-0001/fake.json", JSON.stringify({ content: "real output", content_hash: "f".repeat(64) }));
const report4 = engine.verifyTarget(".ai/evidence/T-0001/fake.json", { task_id: "T-0001" });
const dim4 = report4.dimensions.find(d => d.dimension === "AUTHENTICITY");
const af01 = dim4.checks.find(c => c.checker_id === "AF-01-evidence-authenticity");
console.log("AF-01 blockers:", JSON.stringify(af01.findings.filter(f => f.severity === "BLOCKER"), null, 2));
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
    print("STDERR:", proc.stderr[:1000])
