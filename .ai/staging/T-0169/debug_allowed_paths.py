#!/usr/bin/env python3
"""debug_allowed_paths.py — 直接验证 extractYamlList 对 front-matter 的解析"""
import subprocess

ns = r"""
const fs = require("fs");
const path = require("path");
const os = require("os");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dbg-ap-"));
fs.mkdirSync(path.join(tmp, ".ai/tasks"), { recursive: true });
fs.writeFileSync(path.join(tmp, ".ai/tasks/T-9.md"), "---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n", "utf-8");

const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const cardPath = path.join(tmp, ".ai/tasks/T-9.md");
const raw = fs.readFileSync(cardPath, "utf-8").replace(/\r\n/g, "\n");
console.log("raw:", JSON.stringify(raw));
const fm = raw.match(/^---\n([\s\S]*?)\n---/);
console.log("fm found:", !!fm);
if (fm) {
  const list = common.extractYamlList(fm[1], "allowed_paths");
  console.log("extractYamlList:", JSON.stringify(list));
}
fs.rmSync(tmp, { recursive: true, force: true });
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:300])
