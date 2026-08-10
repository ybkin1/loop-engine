#!/usr/bin/env python3
"""verify_gates_parse.py — 行为级验证：真实 gates.yaml 解析（T-0169 P0 修复验收）"""
import subprocess

node_script = r"""
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const fs = require("fs");
const root = "C:/Users/Administrator/ZCodeProject/loop-engine";

const gatesContent = fs.readFileSync(root + "/.ai/gates.yaml", "utf-8");
const dashCount = (gatesContent.match(/^\s*- id:/gm) || []).length;
console.log("gates.yaml `- id:` count:", dashCount);

const gatesData = common.loadGates(root);
const gates = gatesData ? gatesData.gates : [];
console.log("loadGates parsed count:", gates.length);
console.log("gates[0] keys:", gates[0] ? Object.keys(gates[0]).slice(0, 8) : "none");
console.log("gates[0].id:", gates[0] ? gates[0].id : "none");

const pending = common.pendingGates(root);
const blocked = common.blockedGates(root);
console.log("pendingGates:", pending.length, "blockedGates:", blocked.length);

const tasksData = common.loadTasks(root);
console.log("loadTasks count:", tasksData && tasksData.tasks ? tasksData.tasks.length : "n/a");

const ok = gates.length === dashCount && gates[0] && gates[0].id;
console.log(ok ? "\n[PASS] gates parsed correctly" : "\n[FAIL] gates parse broken");
process.exit(ok ? 0 : 1);
"""

proc = subprocess.run(
    ["node", "-e", node_script],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print(proc.stdout)
if proc.stderr.strip():
    print("STDERR:", proc.stderr[:300])
print("EXIT:", proc.returncode)
