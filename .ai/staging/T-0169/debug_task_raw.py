#!/usr/bin/env python3
"""debug_task_raw.py — 验证 task 对象是否含 _raw 与 allowed_paths"""
import subprocess

ns = r"""
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const tasksData = common.loadTasks("C:/Users/Administrator/ZCodeProject/loop-engine");
const t9 = tasksData.tasks.find(t => (t.task_id || t.id) === "T-0169");
console.log("T-0169 task keys:", t9 ? Object.keys(t9).join(",") : "not found");
console.log("T-0169 allowed_paths:", t9 ? JSON.stringify(t9.allowed_paths) : "n/a");
console.log("T-0169 _raw:", t9 && t9._raw ? "present" : "MISSING");
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
