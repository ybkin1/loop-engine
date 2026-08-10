#!/usr/bin/env python3
"""debug_gates_parse.py — 定位 loadGates 解析失败原因"""
import subprocess

node_script = r"""
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const fs = require("fs");
const root = "C:/Users/Administrator/ZCodeProject/loop-engine";
const content = fs.readFileSync(root + "/.ai/gates.yaml", "utf-8");
console.log("file size:", content.length, "bytes");
console.log("MAX_YAML_SIZE check passed:", content.length <= 1000000);
// 手动测 listRegex
const listRegex = /gates:\s*\n((?:[\s]+.*\n?)*)/m;
const m = content.match(listRegex);
console.log("listRegex match:", !!m);
if (m) console.log("block head:", JSON.stringify(m[1].slice(0, 200)));
const list = common.extractYamlObjectList(content, "gates");
console.log("extractYamlObjectList count:", list.length);
if (list.length > 0) console.log("first gate keys:", Object.keys(list[0]).slice(0, 8));
"""

proc = subprocess.run(
    ["node", "-e", node_script],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print(proc.stdout)
if proc.stderr.strip():
    print("STDERR:", proc.stderr[:400])
