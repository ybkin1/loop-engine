#!/usr/bin/env python3
"""fix_hook_common_gates.py — 修复 hook_common.js loadGates 解析缺陷（T-0169）

问题：extractYamlObjectList 的 listRegex 要求列表行以空白开头（[\\s]+），
但 ZCode 生成的 gates.yaml 列表项是顶格 `- id:`（无缩进）→ 解析 0 条 →
isLoopActive=false → 所有 JS hooks 在真实项目上失效。

修复：listRegex 兼容"顶格 - 或缩进 -"两种列表格式。
只改 loadGates 相关正则，不改变其他函数语义。
"""
from pathlib import Path

HC = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\hook_common.js")

def main() -> int:
    t = HC.read_text(encoding="utf-8")

    old = "  const listRegex = new RegExp(`${escapedKey}:\\\\s*\\\\n((?:[\\\\s]+.*\\\\n?)*)`, 'm');"
    new = (
        "  // T-0169 修复：兼容顶格列表（`- id:` 无缩进）与缩进列表两种格式。\n"
        "  // 旧正则 `[\\s]+.*` 要求行首空白，ZCode 生成 gates.yaml 是顶格 `- ` → 解析 0 条。\n"
        "  const listRegex = new RegExp(`${escapedKey}:\\\\s*\\\\n((?:(?:[ \\\\t]*).*\\\\n?)*)`, 'm');"
    )
    if "T-0169 修复" in t:
        print("[same] already fixed")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    HC.write_text(t, encoding="utf-8")
    print("[fix] loadGates listRegex now accepts top-level `- id:` lists")

    import subprocess
    r = subprocess.run(["node", "-c", str(HC)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax check failed:", r.stderr[:300])
        return 1
    print("[ok] hook_common.js syntax OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
