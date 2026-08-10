#!/usr/bin/env python3
"""debug_gg_trace4.py — 在 gate-guard 里打印 root + cardPath + extractYamlList 结果"""
import subprocess

# 在 extractAllowedPaths 里加详细 trace
gg = r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js"
src = open(gg, encoding="utf-8").read()

old = "      const raw = fs.readFileSync(cardPath, 'utf-8').replace(/\\r\\n/g, '\\n');"
new = ("      const raw = fs.readFileSync(cardPath, 'utf-8').replace(/\\r\\n/g, '\\n');\n"
       "      process.stderr.write('[TRACE2] cardPath=' + cardPath + ' raw=' + JSON.stringify(raw.slice(0, 60)) + '\\n');")
if "[TRACE2]" not in src:
    assert src.count(old) == 1
    src = src.replace(old, new)
    open(gg, "w", encoding="utf-8").write(src)
    print("[patch] trace2 added")

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-t4-"));
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
console.log("STDERR:", p.stderr ? p.stderr.slice(0, 700) : "(empty)");
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
