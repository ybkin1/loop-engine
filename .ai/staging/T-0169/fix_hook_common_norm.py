#!/usr/bin/env python3
"""fix_hook_common_norm.py — extractYamlObjectList 入口统一 CRLF 规范化（T-0169 P0-1 补全）

listRegex 在原始 CRLF content 上匹配仍截断 → 入口先 content.replace(/\\r\\n/g,'\\n')。
"""
from pathlib import Path

HC = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\hook_common.js")

def main() -> int:
    t = HC.read_text(encoding="utf-8")

    old = "function extractYamlObjectList(content, listKey) {\n  if (!_validateYamlInput(content, listKey)) return [];"
    new = (
        "function extractYamlObjectList(content, listKey) {\n"
        "  if (!_validateYamlInput(content, listKey)) return [];\n"
        "  // T-0169 P0-1：统一 CRLF→LF，避免正则 . 不匹配 \\r 导致列表截断\n"
        "  content = content.replace(/\\r\\n/g, '\\n');"
    )
    if "统一 CRLF→LF" in t:
        print("[same] already normalized at entry")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    HC.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(HC)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[fix] extractYamlObjectList entry CRLF normalized")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
