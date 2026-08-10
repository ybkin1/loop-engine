#!/usr/bin/env python3
"""fix_t171_tail.py — 清理 T-0171.md 残留尾节"""
from pathlib import Path

p = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine\.ai\tasks\T-0171.md")
t = p.read_text(encoding="utf-8")
idx = t.find("\n## Status\n\nin_progress")
if idx > 0:
    t = t[:idx] + "\n"
    p.write_text(t, encoding="utf-8")
    print("[fix] T-0171.md tail removed")
else:
    print("[info] no tail section found")
