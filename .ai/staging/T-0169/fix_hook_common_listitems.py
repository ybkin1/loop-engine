#!/usr/bin/env python3
"""fix_hook_common_listitems.py — 修复 extractYamlObjectList 顶格列表识别（T-0169 第二处）

问题：列表项识别正则 /^\\s+-\\s+/ 要求 `- ` 前至少一个空白，
ZCode 生成的 gates.yaml 是顶格 `- id:` → 列表项永不触发 → 对象 0 条。

修复：改为 /^\\s*-\\s+/（允许顶格），保留 T-0010 的嵌套缩进识别。
"""
from pathlib import Path

HC = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\hook_common.js")

def main() -> int:
    t = HC.read_text(encoding="utf-8")

    old = "    if (/^\\s+-\\s+/.test(line)) {"
    new = "    if (/^\\s*-\\s+/.test(line)) { // T-0169 修复：允许顶格 `- id:`（ZCode 生成的 gates.yaml 无缩进）"
    if "T-0169 修复：允许顶格" in t:
        print("[same] already fixed")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    HC.write_text(t, encoding="utf-8")
    print("[fix] list item regex now accepts top-level `- `")

    import subprocess
    r = subprocess.run(["node", "-c", str(HC)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[ok] syntax OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
