#!/usr/bin/env python3
"""debug_govfile.py — 测试 isGovernanceFile 对 docs/ 的行为"""
import subprocess

ns = r"""
const common = require("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js");
const root = "C:/Users/Administrator/ZCodeProject/loop-engine";
console.log("docs/out.md:", common.isGovernanceFile(root + "/docs/out.md", root));
console.log("src/x.ts:", common.isGovernanceFile(root + "/src/x.ts", root));
console.log(".ai/state.yaml:", common.isGovernanceFile(root + "/.ai/state.yaml", root));
const src = require("fs").readFileSync("C:/Users/Administrator/.qoder-cn/hooks/scripts/hook_common.js", "utf-8");
const m = src.match(/GOVERNANCE_PATHS\s*=\s*\[[^\]]*\]/);
console.log("GOVERNANCE_PATHS:", m ? m[0] : "not found (const style?)");
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:200])
