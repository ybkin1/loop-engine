#!/usr/bin/env python3
"""test_import_guard_escalate.py — import-guard 渐进升级验证（2 次触发 exit 2）"""
import json
import subprocess

ROOT = r"C:\Users\Administrator\ZCodeProject\loop-engine"
GUARD = r"C:\Users\Administrator\.qoder-cn\hooks\scripts\import-guard.js"
MARKER = ROOT + r"\.ai\.import-violations"

import os
# 清理标记
if os.path.exists(MARKER):
    os.remove(MARKER)

def fire(n: int):
    evt = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": rf"{ROOT}\src\z_importtest{n}.ts",
            "content": f"import {{ x }} from 'fabricated-pkg-xyz-2026';\nexport const z{n} = x;",
        },
        "cwd": ROOT,
    }
    proc = subprocess.run(["node", GUARD], input=json.dumps(evt), capture_output=True, text=True, encoding="utf-8", timeout=15)
    print(f"fire#{n}: exit={proc.returncode} stderr={'yes' if proc.stderr.strip() else 'no'}")

fire(1)  # 首次：计数，exit 0
fire(2)  # 第二次：累计 >=2 → exit 2 硬阻断
