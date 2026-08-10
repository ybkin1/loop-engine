#!/usr/bin/env python3
"""debug_import_guard.py — 直接调试 import-guard 内部函数"""
import json
import subprocess

node_script = r"""
const fs = require('fs');
const path = require('path');
// 直接 require 并调用内部函数（通过重新实现提取逻辑验证）
const content = "import { x } from 'fabricated-pkg-xyz-2026';\nexport const z = x;";
const esImportRe = /import\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]/g;
let m;
const imports = [];
while ((m = esImportRe.exec(content)) !== null) {
  imports.push(m[1]);
}
console.log("extracted imports:", JSON.stringify(imports));

// 用 guard 的事件模拟（最小依赖）
const { execFileSync } = require('child_process');
const evt = {
  tool_name: "Write",
  tool_input: { file_path: "C:/Users/Administrator/ZCodeProject/loop-engine/src/z_importtest.ts", content },
  cwd: "C:/Users/Administrator/ZCodeProject/loop-engine",
};
// 直接执行 guard 脚本并传入事件
const proc = require('child_process').spawnSync('node', ['C:/Users/Administrator/.qoder-cn/hooks/scripts/import-guard.js'], {
  input: JSON.stringify(evt),
  encoding: 'utf-8',
  timeout: 15000,
});
console.log("guard exit:", proc.status);
console.log("guard stderr:", JSON.stringify(proc.stderr || ""));
"""

proc = subprocess.run(
    ["node", "-e", node_script],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print(proc.stdout)
if proc.stderr.strip():
    print("STDERR:", proc.stderr[:500])
