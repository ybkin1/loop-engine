#!/usr/bin/env python3
"""debug_gate_b2.py — node 单文件调试 gate-guard 场景 B"""
import subprocess

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-b2-"));
fs.mkdirSync(path.join(tmp, ".ai/tasks"), { recursive: true });
fs.mkdirSync(path.join(tmp, "src"), { recursive: true });
fs.mkdirSync(path.join(tmp, "docs"), { recursive: true });
fs.mkdirSync(path.join(tmp, ".venv"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/state.yaml"), "schema_version: 1\ncurrent_task_id: T-9\nactive_task_id: T-9\ncurrent_phase: S4-implementation\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/gates.yaml"), "schema_version: 1\ngates:\n- id: G-T-9-REQUIREMENTS\n  task_id: T-9\n  phase: S4-implementation\n  status: approved\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/task_graph.yaml"), "schema_version: 1\ntasks:\n  -\n    id: T-9\n    status: in_progress\n", "utf-8");

const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const state = common.loadState(tmp);
console.log("active_task_id:", state.active_task_id);
const tasksData = common.loadTasks(tmp);
console.log("tasks count:", tasksData ? tasksData.tasks.length : "n/a");
const card = fs.readFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "utf-8");
const fm = card.match(/^---\n([\s\S]*?)\n---/);
console.log("card allowed_paths:", common.extractYamlList(fm[1], "allowed_paths"));

// 场景 B
const evt = { tool_name: "Write", tool_input: { file_path: tmp + "/docs/out.md", content: "# out" }, cwd: tmp };
const p = spawnSync("node", ["C:/Users/Administrator/.qoder-cn/hooks/scripts/gate-guard.js"], {
  input: JSON.stringify(evt), encoding: "utf-8", timeout: 15000,
});
console.log("SCENARIO B exit:", p.status);
console.log("stderr:", p.stderr ? p.stderr.slice(0, 300) : "(empty)");
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:300])
