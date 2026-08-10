#!/usr/bin/env python3
"""check_clean.py — 核查 src/dist 中 OQA 注册与 handler 唯一性"""
from pathlib import Path

def count_occ(path: str, needle: str) -> int:
    return Path(path).read_text(encoding="utf-8").count(needle)

src = r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\server\tools.ts"
dist = r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\dist\src\server\tools.js"

print("src  cases loop_output_quality:", count_occ(src, 'case "loop_output_quality":'))
print("src  cases loop_quality_gate:  ", count_occ(src, 'case "loop_quality_gate":'))
print("src  regs loop_output_quality: ", count_occ(src, 'name: "loop_output_quality"'))
print("src  regs loop_quality_gate:   ", count_occ(src, 'name: "loop_quality_gate"'))
print("dist cases loop_output_quality:", count_occ(dist, 'case "loop_output_quality"'))
print("dist cases loop_quality_gate:  ", count_occ(dist, 'case "loop_quality_gate"'))
print("dist regs loop_output_quality: ", count_occ(dist, 'name: "loop_output_quality"'))
print("dist regs loop_quality_gate:   ", count_occ(dist, 'name: "loop_quality_gate"'))

# default 位置核查：handler 必须在最后一个 default 之前
s = Path(src).read_text(encoding="utf-8")
idx_case = s.index('case "loop_output_quality"')
idx_default = s.rindex("default:")
print("handler before default:", idx_case < idx_default)
