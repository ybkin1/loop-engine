#!/usr/bin/env python3
"""debug_listblock.py — 查看 listBlock 实际捕获内容"""
import subprocess

node_script = r"""
const fs = require("fs");
const content = fs.readFileSync("C:/Users/Administrator/ZCodeProject/loop-engine/.ai/gates.yaml", "utf-8");
const normalized = content.replace(/\r\n/g, '\n');
const escapedKey = "gates".replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const listRegex = new RegExp(`${escapedKey}:\\s*\\n((?:(?:[ \\t]*).*\\n?)*)`, 'm');
const m = normalized.match(listRegex);
console.log("matched:", !!m);
if (m) {
  const block = m[1];
  console.log("block length:", block.length);
  console.log("block first 300:", JSON.stringify(block.slice(0, 300)));
  console.log("block lines:", block.split('\n').length);
  const dashLines = (block.match(/^\s*- id:/gm) || []).length;
  console.log("dash id lines in block:", dashLines);
}
"""

proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, encoding="utf-8")
print(proc.stdout)
if proc.stderr.strip():
    print("STDERR:", proc.stderr[:300])
