#!/usr/bin/env python3
"""fix_hook_common_crlf.py — 修复 hook_common.js CRLF 解析缺陷（T-0169 P0-1/P0-2）

P0-1: listRegex `((?:(?:[ \\t]*).*\\n?)*)` 中点号不匹配 `\\r`，
      CRLF（Windows）文件每行在 `\\r` 前截断 → 仅捕获 1 行。
      修复：解析前统一 content.replace(/\\r\\n/g, '\\n') 规范化。
P0-2: 顶格列表项提取 `line.replace(/^\\s+-\\s+/, '')` 仍要求缩进，
      顶格 `- id:` 不触发 → id 丢失。
      修复：改为 /^\\s*-\\s+/。
"""
from pathlib import Path

HC = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\hook_common.js")

def main() -> int:
    t = HC.read_text(encoding="utf-8")

    # P0-1: extractYamlObjectList 入口统一 CRLF→LF
    old1 = "  const listBlock = listMatch[1];"
    new1 = (
        "  // T-0169 P0-1 修复：CRLF（Windows）文件每行带 \\r，JS 点号不匹配 \\r\n"
        "  // → 解析前统一为 \\n，避免列表块被截断为 1 行。\n"
        "  const listBlock = listMatch[1].replace(/\\r\\n/g, '\\n');"
    )
    if "P0-1 修复" in t:
        print("[same] P0-1 already fixed")
    else:
        assert t.count(old1) == 1, f"P0-1 anchor count={t.count(old1)}"
        t = t.replace(old1, new1)
        print("[fix] P0-1: CRLF normalized before parsing")

    # P0-2: 顶格列表项提取（第一键值对）
    old2 = "      const kvMatch = line.replace(/^\\s+-\\s+/, '').match(/^(\\w+):\\s*(.*)$/);"
    new2 = "      const kvMatch = line.replace(/^\\s*-\\s+/, '').match(/^(\\w+):\\s*(.*)$/); // T-0169 P0-2：顶格 `- id:` 也提取"
    if "P0-2" in t:
        print("[same] P0-2 already fixed")
    else:
        assert t.count(old2) == 1, f"P0-2 anchor count={t.count(old2)}"
        t = t.replace(old2, new2)
        print("[fix] P0-2: top-level list item key extraction")

    HC.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(HC)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[ok] hook_common.js syntax OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
