#!/usr/bin/env python3
"""debug_guard.py — 调试 output_quality_guard.js 内部判定"""
import json
import subprocess

event = {
    "tool_name": "Write",
    "tool_input": {
        "file_path": r"C:\Users\Administrator\ZCodeProject\loop-engine\src\secret_test.ts",
        "content": 'const apiKey = "sk-0123456789abcdef0123456789abcdef";',
    },
    "cwd": r"C:\Users\Administrator\ZCodeProject\loop-engine",
}

node_script = r"""
const common = require("./hook_common.js");
const event = JSON.parse(process.argv[1]);
const root = common.projectRoot(event);
console.log("root:", root);
console.log("isGovernanceProject:", common.isGovernanceProject(root));
console.log("isLoopActive:", common.isLoopActive(root));
console.log("isGovernanceFile:", common.isGovernanceFile(event.tool_input.file_path, root));
"""

proc = subprocess.run(
    ["node", "-e", node_script, json.dumps(event)],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=r"C:\Users\Administrator\.qoder-cn\hooks\scripts",
)
print("STDOUT:", proc.stdout)
print("STDERR:", proc.stderr)
print("EXIT:", proc.returncode)
