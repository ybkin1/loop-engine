#!/usr/bin/env python3
"""test_escape.py — F3 验证：越界 target 必须被拒绝"""
import subprocess

node_script = r"""
const { OutputQualityEngine } = require("./dist/src/core/output_quality.js");
const engine = new OutputQualityEngine("C:/Users/Administrator/ZCodeProject/loop-engine");
try {
  engine.verifyTarget("../harness-agentic", { task_id: "T-0167" });
  console.log("ESCAPE_NOT_BLOCKED");
} catch (e) {
  console.log("ESCAPE_BLOCKED:", e.message.slice(0, 80));
}
try {
  engine.verifyTarget("", { task_id: "T-0167" });
  console.log("EMPTY_NOT_BLOCKED");
} catch (e) {
  console.log("EMPTY_BLOCKED:", e.message.slice(0, 80));
}
// 合法路径应正常工作
const ok = engine.verifyTarget("src", { task_id: "T-0167" });
console.log("VALID_TARGET_OK:", ok.target, ok.overall);
"""

proc = subprocess.run(
    ["node", "-e", node_script],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=r"C:\Users\Administrator\.qoder-cn\loop-engine-lab",
)
print(proc.stdout.strip())
if proc.stderr.strip():
    print("stderr:", proc.stderr.strip()[:300])
print("EXIT:", proc.returncode)
