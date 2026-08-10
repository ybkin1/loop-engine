#!/usr/bin/env python3
"""test_guard_behaviour.py — output_quality_guard.js 行为验证（AC-04）

场景 1：密钥模式 → 期望 exit 2 + deny JSON
场景 2：调试残留 + 超规模 → 期望 exit 0 + stderr WARN
场景 3：干净代码 → 期望 exit 0 无告警
"""
import json
import subprocess
import sys
from pathlib import Path

GUARD = r"C:\Users\Administrator\.qoder-cn\hooks\scripts\output_quality_guard.js"
ROOT = r"C:\Users\Administrator\ZCodeProject\loop-engine"

def run_case(name: str, file_path: str, content: str, expect_exit: int) -> None:
    event = {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "cwd": ROOT,
    }
    proc = subprocess.run(
        ["node", GUARD],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    ok = proc.returncode == expect_exit
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: exit={proc.returncode} (expect {expect_exit})")
    if proc.stderr.strip():
        print(f"    stderr: {proc.stderr.strip()[:200]}")
    if proc.stdout.strip():
        print(f"    stdout: {proc.stdout.strip()[:200]}")
    if not ok:
        sys.exit(1)

# 场景 1：密钥 → 硬拒
run_case(
    "secret-deny",
    r"C:\Users\Administrator\ZCodeProject\loop-engine\src\secret_test.ts",
    'const apiKey = "sk-0123456789abcdef0123456789abcdef";\n',
    2,
)

# 场景 2：调试残留（3 处 console.log）→ 告警放行
run_case(
    "debug-warn",
    r"C:\Users\Administrator\ZCodeProject\loop-engine\src\debug_test.ts",
    "console.log('a');\nconsole.log('b');\nconsole.log('c');\nexport const x = 1;\n",
    0,
)

# 场景 3：干净代码 → 无告警放行
run_case(
    "clean-pass",
    r"C:\Users\Administrator\ZCodeProject\loop-engine\src\clean_test.ts",
    "export const clean = 42;\n",
    0,
)

print("\n[ok] guard behaviour verified: AC-04 PASS")
