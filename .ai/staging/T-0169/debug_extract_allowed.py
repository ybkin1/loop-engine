#!/usr/bin/env python3
"""debug_extract_allowed.py — 验证 extractYamlList 解析 front-matter allowed_paths"""
import subprocess

ns = r"""
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const fs = require("fs");
const root = "C:/Users/Administrator/ZCodeProject/loop-engine";
const card = fs.readFileSync(root + "/.ai/tasks/T-0169.md", "utf-8");
const fm = card.match(/^---\n([\s\S]*?)\n---/);
console.log("front-matter found:", !!fm);
if (fm) {
  console.log("front-matter head:", JSON.stringify(fm[1].slice(0, 120)));
  const list = common.extractYamlList(fm[1], "allowed_paths");
  console.log("extractYamlList allowed_paths:", JSON.stringify(list));
}
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
