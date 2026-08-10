#!/usr/bin/env python3
"""fix_t171_status.py — T-0171.md 加 `## Status` 尾节（completed，校验读取格式）"""
import re
from pathlib import Path

p = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine\.ai\tasks\T-0171.md")
t = p.read_text(encoding="utf-8")
if "\n## Status\n\ncompleted" in t:
    print("[same] Status section already correct")
else:
    t = re.sub(r"\n## Status\n+[^\n]*\n?$", "", t).rstrip() + "\n\n## Status\n\ncompleted\n"
    p.write_text(t, encoding="utf-8")
    print("[fix] Status section set to completed")
