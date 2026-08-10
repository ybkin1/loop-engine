#!/usr/bin/env python3
"""debug_gg_trace.py — 在 gate-guard 加临时 trace 后跑场景 B"""
import subprocess

# 先给 gate-guard 打 trace 补丁
gg = r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js"
src = open(gg, encoding="utf-8").read()

old = "        const allowedPaths = extractAllowedPaths(root, state.active_task_id, activeTask);"
new = ("        const allowedPaths = extractAllowedPaths(root, state.active_task_id, activeTask);\n"
       "        process.stderr.write('[TRACE] allowedPaths=' + JSON.stringify(allowedPaths) + ' filePath=' + (filePath||'') + ' isFileWrite=' + isFileWrite + '\\n');")
if "[TRACE]" not in src:
    assert src.count(old) == 1
    src = src.replace(old, new)
    open(gg, "w", encoding="utf-8").write(src)
    print("[patch] trace added")
else:
    print("[info] trace already present")

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-t-"));
fs.mkdirSync(path.join(tmp, ".ai/tasks"), { recursive: true });
fs.mkdirSync(path.join(tmp, "src"), { recursive: true });
fs.mkdirSync(path.join(tmp, "docs"), { recursive: true });
fs.mkdirSync(path.join(tmp, ".venv"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/state.yaml"), "schema_version: 1\ncurrent_task_id: T-9\nactive_task_id: T-9\ncurrent_phase: S4-implementation\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/gates.yaml"), "schema_version: 1\ngates:\n- id: G-T-9-REQUIREMENTS\n  task_id: T-9\n  phase: S4-implementation\n  status: approved\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/task_graph.yaml"), "schema_version: 1\ntasks:\n  -\n    id: T-9\n    status: in_progress\n", "utf-8");
const evt = { tool_name: "Write", tool_input: { file_path: tmp + "/docs/out.md", content: "# out" }, cwd: tmp };
const p = spawnSync("node", ["C:/Users/Administrator/.qoder-cn/hooks/scripts/gate-guard.js"], {
  input: JSON.stringify(evt), encoding: "utf-8", timeout: 15000,
});
console.log("EXIT:", p.status);
console.log("STDERR:", p.stderr ? p.stderr.slice(0, 500) : "(empty)");
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
