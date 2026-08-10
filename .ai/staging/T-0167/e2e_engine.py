#!/usr/bin/env python3
"""e2e_engine.py — OQA-4D 引擎端到端实测（在真实 loop-engine 项目上）"""
import json
import subprocess

node_script = r"""
const { OutputQualityEngine, renderReportSummary } = require("./dist/src/core/output_quality.js");
const engine = new OutputQualityEngine("C:/Users/Administrator/ZCodeProject/loop-engine");
// 验证真实目标：引擎自身（代码）+ 标准文档（文档）
const report = engine.verifyTarget(".ai/staging/T-0167/output_quality.ts", {
  task_id: "T-0167",
  phase: "S6-delivery",
  role: "R06",
});
console.log(JSON.stringify({
  schema: report.schema,
  target: report.target,
  overall: report.overall,
  blocked_by: report.blocked_by,
  dimensions: report.dimensions.map(d => ({ dim: d.dimension, status: d.status, blockers: d.blocker_count, warnings: d.warning_count })),
  hash: report.content_hash.slice(0, 16),
}, null, 2));
console.log("---summary---");
console.log(renderReportSummary(report).split("\n").slice(0, 12).join("\n"));
"""

proc = subprocess.run(
    ["node", "-e", node_script],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=r"C:\Users\Administrator\.qoder-cn\loop-engine-lab",
)
print("STDOUT:", proc.stdout)
if proc.stderr:
    print("STDERR:", proc.stderr[:500])
print("EXIT:", proc.returncode)
