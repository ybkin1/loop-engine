#!/usr/bin/env python3
"""verify_p14.py — P1-4 修复验证：含'查找/获取'的 AC 在实现缺失时应 BLOCKER"""
import subprocess

ns = r"""
const { OutputQualityEngine } = require("./dist/src/core/output_quality.js");
const { mkdtempSync, writeFileSync, mkdirSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, dirname } = require("node:path");
const root = mkdtempSync(join(tmpdir(), "p14-"));
function w(rel, c) { const p = join(root, rel); mkdirSync(dirname(p), { recursive: true }); writeFileSync(p, c, "utf-8"); }
w(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-9\n");
w(".ai/tasks/T-9.md", "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n## 可验证验收标准\n1. **[AC-01]** 支持按名称查找记录并获取详情\n2. **[AC-02]** 用户登录功能 works\n");
w("src/impl.ts", "export const unrelated = 1;\n");
const r = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-9" });
const auth = r.dimensions.find(d => d.dimension === "AUTHENTICITY");
const ai03 = auth.checks.find(c => c.checker_id === "AI-03-ac-implementation");
const blockers = ai03.findings.filter(f => f.severity === "BLOCKER");
console.log("AI-03 BLOCKER count:", blockers.length);
for (const b of blockers) console.log("  -", b.message.slice(0, 90));
console.log(blockers.length >= 2 ? "\n[PASS] P1-4 fixed: 查找/获取 + 登录 both detected" : "\n[FAIL] P1-4 not fully fixed");
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8", cwd=r"C:\Users\Administrator\.qoder-cn\loop-engine-lab")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
