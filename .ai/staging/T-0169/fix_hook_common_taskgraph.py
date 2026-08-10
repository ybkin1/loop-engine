#!/usr/bin/env python3
"""fix_hook_common_taskgraph.py — 支持 task_graph 的 `-` 空列表项格式（T-0169 P0 补全）

task_graph.yaml: `  -`（- 后无内容，键在下一行缩进 4）
gates.yaml:      `- id:`（键同行，顶格）
两种格式都要支持：
1. 列表项行 `-` 后无内容 → 也创建对象（首键从后续续行提取）
2. 续行缩进限制 topIndent+2 → topIndent+4（task_graph 键在缩进 4）
"""
from pathlib import Path

HC = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\hook_common.js")

def main() -> int:
    t = HC.read_text(encoding="utf-8")

    # 1. 空 `-` 列表项：`-` 后无内容时也创建对象
    old1 = "      const kvMatch = line.replace(/^\\s*-\\s+/, '').match(/^(\\w+):\\s*(.*)$/); // T-0169 P0-2：顶格 `- id:` 也提取\n      if (kvMatch) {\n        currentObj[kvMatch[1]] = kvMatch[2].trim().replace(/^['\"]|['\"]$/g, '');\n      }"
    new1 = (
        "      const trimmedItem = line.replace(/^\\s*-\\s*/, '');\n"
        "      const kvMatch = trimmedItem.match(/^(\\w+):\\s*(.*)$/); // T-0169 P0-2：顶格 `- id:` 也提取\n"
        "      if (kvMatch) {\n"
        "        currentObj[kvMatch[1]] = kvMatch[2].trim().replace(/^['\"]|['\"]$/g, '');\n"
        "      } // 空 `-`（键在下一行，task_graph 格式）→ 对象已创建，键由续行提取"
    )
    if "键在下一行" in t:
        print("[same] empty-dash item already handled")
    else:
        assert t.count(old1) == 1, f"anchor1 count={t.count(old1)}"
        t = t.replace(old1, new1)
        print("[fix] empty `-` list item creates object")

    # 2. 续行缩进限制放宽：topIndent+2 → topIndent+4
    old2 = "      if (topIndent !== null && indent > topIndent + 2) continue;"
    new2 = "      if (topIndent !== null && indent > topIndent + 4) continue; // T-0169：task_graph 键在缩进 4"
    if "缩进 4" in t:
        print("[same] continuation indent already relaxed")
    else:
        assert t.count(old2) == 1, f"anchor2 count={t.count(old2)}"
        t = t.replace(old2, new2)
        print("[fix] continuation indent relaxed to +4")

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
