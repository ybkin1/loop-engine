#!/usr/bin/env python3
"""fix_legacy_status.py — 同步 T-0169/T-0170 任务卡尾节状态为 completed"""
import re
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine")

for task in ["T-0169", "T-0170"]:
    p = ROOT / f".ai/tasks/{task}.md"
    if not p.exists():
        print(f"[skip] {task} not found")
        continue
    t = p.read_text(encoding="utf-8")
    t2 = re.sub(r"\n## Status\n+[^\n]*\n?$", "\n\n## Status\n\ncompleted\n", t)
    if t2 != t:
        p.write_text(t2, encoding="utf-8")
        print(f"[fix] {task} Status -> completed")
    else:
        print(f"[same] {task} already ok")
