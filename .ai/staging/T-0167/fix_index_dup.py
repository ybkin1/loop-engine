#!/usr/bin/env python3
"""fix_index_dup.py — 移除 core/index.ts 中重复的 FindingSeverity 导出"""
from pathlib import Path

p = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\index.ts")
t = p.read_text(encoding="utf-8")

old = '  DimensionId,\n  FindingSeverity,\n  QualityFinding,'
new = '  DimensionId,\n  QualityFinding,'
assert t.count(old) == 1, f"count={t.count(old)}"
p.write_text(t.replace(old, new), encoding="utf-8")
print("removed duplicate FindingSeverity export from OQA block")
