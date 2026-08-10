#!/usr/bin/env python3
"""test_import_guard.py — import-guard 裸包检测行为验证"""
import json
import subprocess

evt = {
    "tool_name": "Write",
    "tool_input": {
        "file_path": r"C:\Users\Administrator\ZCodeProject\loop-engine\src\z_importtest.ts",
        "content": "import { x } from 'fabricated-pkg-xyz-2026';\nexport const z = x;",
    },
    "cwd": r"C:\Users\Administrator\ZCodeProject\loop-engine",
}
proc = subprocess.run(
    ["node", r"C:\Users\Administrator\.qoder-cn\hooks\scripts\import-guard.js"],
    input=json.dumps(evt),
    capture_output=True,
    text=True,
    encoding="utf-8",
    timeout=15,
)
print("exit:", proc.returncode)
print("stdout:", proc.stdout[:200] if proc.stdout else "(empty)")
print("stderr:", proc.stderr[:300] if proc.stderr else "(empty)")
