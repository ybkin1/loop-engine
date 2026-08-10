#!/usr/bin/env python3
"""debug_guard2.py — 调试 loadState/loadGates 解析"""
import json
import subprocess

node_script = r"""
const common = require("./hook_common.js");
const root = process.argv[1];
const state = common.loadState(root);
console.log("state keys:", state ? Object.keys(state).join(",") : "null");
console.log("state.current_phase:", state ? state.current_phase : "N/A");
const gates = common.loadGates(root);
console.log("gates keys:", gates ? Object.keys(gates).join(",") : "null");
console.log("gates.gates length:", gates && gates.gates ? gates.gates.length : "N/A");
"""

proc = subprocess.run(
    ["node", "-e", node_script, r"C:\Users\Administrator\ZCodeProject\loop-engine"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=r"C:\Users\Administrator\.qoder-cn\hooks\scripts",
)
print("STDOUT:", proc.stdout)
print("STDERR:", proc.stderr[:500] if proc.stderr else "")
