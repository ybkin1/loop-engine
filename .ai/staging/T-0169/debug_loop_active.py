#!/usr/bin/env python3
"""debug_loop_active.py — 确认 isLoopActive 在 loop-engine 上的行为"""
import subprocess

node_script = r"""
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const root = "C:/Users/Administrator/ZCodeProject/loop-engine";
console.log("isGovernanceProject:", common.isGovernanceProject(root));
console.log("isLoopActive:", common.isLoopActive(root));
const state = common.loadState(root);
console.log("state.current_phase:", state ? state.current_phase : "null");
const gates = common.loadGates(root);
console.log("gates count:", gates && gates.gates ? gates.gates.length : "n/a");
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
