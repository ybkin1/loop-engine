#!/usr/bin/env python3
"""fix_guard_placeholder.py — 修复 guard 占位符预检的模板字符串（反引号被 PowerShell 吞掉）"""
from pathlib import Path

p = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\output_quality_guard.js")
t = p.read_text(encoding="utf-8")

# 查找损坏的行（反引号丢失）
bad = "warnings.push(`[Loop Output Quality] WARN: ${placeholderHits} placeholder/TODO marker(s) in ${filePath}. Deep verification (AL-01) will BLOCK placeholders — implement fully.`);"
good = "warnings.push(`[Loop Output Quality] WARN: ${placeholderHits} placeholder/TODO marker(s) in ${filePath}. Deep verification (AL-01) will BLOCK placeholders — implement fully.`);"

if bad in t:
    t = t.replace(bad, good)
    p.write_text(t, encoding="utf-8")
    print("[fix] template string repaired")
else:
    # 检查是否反引号确实丢失
    import re
    m = re.search(r"warnings\.push\(\[Loop Output Quality\] WARN:.*?implement fully\.\)", t)
    if m:
        print("[warn] found damaged line, repairing...")
        damaged = m.group(0)
        repaired = "warnings.push(`[Loop Output Quality] WARN: ${placeholderHits} placeholder/TODO marker(s) in ${filePath}. Deep verification (AL-01) will BLOCK placeholders — implement fully.`);"
        t = t.replace(damaged, repaired)
        p.write_text(t, encoding="utf-8")
        print("[fix] damaged line repaired")
    else:
        print("[info] no damaged line found — checking full placeholder block")
        print("placeholder present:", "placeholder" in t)
