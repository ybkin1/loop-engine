#!/usr/bin/env python3
"""check_sync.py — 检查 src/staging 同步状态"""
from pathlib import Path

src = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\authenticity.ts").read_text(encoding="utf-8")
staging = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0168\authenticity.ts").read_text(encoding="utf-8")

checks = {
    "baseNoExt": "baseNoExt",
    "ENTRY_SYMBOLS": "ENTRY_SYMBOLS",
    "crypto import": 'from "node:crypto"',
    "isEmptyDir": "isEmptyDir",
    "resolve import": "resolve",
}
for name, needle in checks.items():
    print(f"src[{name}]: {src.count(needle)}  staging[{name}]: {staging.count(needle)}")

print("src==staging:", src == staging)
