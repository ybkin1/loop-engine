#!/usr/bin/env python3
"""debug_gg_trace3.py — 打印 gate-guard 内 root 与 cardPath"""
import subprocess

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-t3-"));
fs.mkdirSync(path.join(tmp, ".ai/tasks"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n", "utf-8");
fs.writeFileSync(path.join(tmp, ".ai/state.yaml"), "schema_version: 1\ncurrent_task_id: T-9\nactive_task_id: T-9\ncurrent_phase: S4-implementation\n", "utf-8");

const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const evt = { tool_name: "Write", tool_input: { file_path: tmp + "/docs/out.md", content: "# out" }, cwd: tmp };
const root = common.projectRoot(evt);
console.log("projectRoot:", root);
const cardPath = path.join(root, '.ai', 'tasks', 'T-9.md');
console.log("cardPath:", cardPath, "exists:", fs.existsSync(cardPath));
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
