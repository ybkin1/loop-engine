#!/usr/bin/env python3
"""debug_gate_guard_internal.py — 在 gate-guard 进程内验证 extractAllowedPaths"""
import subprocess

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-gg-"));
fs.mkdirSync(path.join(tmp, ".ai/tasks"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/state.yaml"), "schema_version: 1\ncurrent_task_id: T-9\nactive_task_id: T-9\ncurrent_phase: S4-implementation\n", "utf-8");

// 读取 gate-guard 源码并 eval 其中的 extractAllowedPaths
const src = fs.readFileSync("C:/Users/Administrator/.qoder-cn/hooks/scripts/gate-guard.js", "utf-8");
// 提取函数体
const start = src.indexOf("function extractAllowedPaths");
const end = src.indexOf("\n}\n", start);
const fnSrc = src.slice(start, end + 3);
// 提取需要的依赖
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const g = new Function("path", "fs", "common", "root", "taskId", "activeTask", fnSrc + "; return extractAllowedPaths(root, taskId, activeTask);");
const result = g(path, fs, common, tmp, "T-9", {});
console.log("extractAllowedPaths result:", JSON.stringify(result));
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:300])
