#!/usr/bin/env python3
"""fix_hook_common_dash_only.py — 支持 `-` 单独成行的列表项（T-0169 P0 补全）

task_graph.yaml: `  -`（- 后无内容直接换行）
列表项识别正则 /^\\s*-\\s+/ 要求 - 后有空白 → 不匹配 `  -`。
修复：/^\\s*-\\s*(?:\\S|$)/（- 后可以是内容或换行）。
"""
from pathlib import Path

HC = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\hook_common.js")

def main() -> int:
    t = HC.read_text(encoding="utf-8")

    old = "    if (/^\\s*-\\s+/.test(line)) { // T-0169 修复：允许顶格 `- id:`（ZCode 生成的 gates.yaml 无缩进）"
    new = "    if (/^\\s*-\\s*(?:\\S|$)/.test(line)) { // T-0169：允许顶格 `- id:` 与单独 `-`（键在下一行）"
    if "单独 `-`" in t:
        print("[same] dash-only already supported")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    HC.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(HC)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[fix] list item regex accepts dash-only lines")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
