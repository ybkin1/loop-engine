#!/usr/bin/env python3
"""debug_pending.py — 验证 pendingGates 对临时项目的行为"""
import subprocess

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-p-"));
fs.mkdirSync(path.join(tmp, ".ai"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/state.yaml"), "schema_version: 1\ncurrent_task_id: T-9\nactive_task_id: T-9\ncurrent_phase: S4-implementation\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/gates.yaml"), "schema_version: 1\ngates:\n- id: G-T-9-REQUIREMENTS\n  task_id: T-9\n  phase: S4-implementation\n  status: approved\n", "utf-8");
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const gates = common.loadGates(tmp);
console.log("parsed gates:", gates ? gates.gates.length : "n/a");
if (gates && gates.gates[0]) console.log("gate0 status:", gates.gates[0].status, "id:", gates.gates[0].id);
console.log("pendingGates:", JSON.stringify(common.pendingGates(tmp)));
console.log("blockedGates:", JSON.stringify(common.blockedGates(tmp)));
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
