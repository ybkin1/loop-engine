#!/usr/bin/env python3
"""debug_gg_trace2.py — extractAllowedPaths 内部细粒度 trace"""
import subprocess

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-t2-"));
fs.mkdirSync(path.join(tmp, ".ai/tasks"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n", "utf-8");

const cardPath = path.join(tmp, '.ai', 'tasks', 'T-9' + '.md');
console.log("cardPath:", cardPath, "exists:", fs.existsSync(cardPath));
const raw = fs.readFileSync(cardPath, 'utf-8').replace(/\r\n/g, '\n');
const fm = raw.match(/^---\n([\s\S]*?)\n---/);
console.log("fm:", !!fm);
if (fm) {
  const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
  const list = common.extractYamlList(fm[1], 'allowed_paths');
  console.log("list:", JSON.stringify(list));
}
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
