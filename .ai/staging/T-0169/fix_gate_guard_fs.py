#!/usr/bin/env python3
"""fix_gate_guard_fs.py — 修复 extractAllowedPaths 中 fs 未定义（T-0169）

gate-guard.js 顶部只 require 了 path 和 common，没有 require fs。
helper 用了 fs.existsSync/readFileSync → ReferenceError → catch 吞掉 → 返回 []。
修复：helper 内改用 require('fs')。
"""
from pathlib import Path

GG = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js")

def main() -> int:
    t = GG.read_text(encoding="utf-8")

    old = "function extractAllowedPaths(root, taskId, activeTask) {\n  // 1. 任务卡文件：front-matter YAML 或 Markdown `## 允许路径` 节\n  const cardPath = path.join(root, '.ai', 'tasks', taskId + '.md');\n  try {\n    if (fs.existsSync(cardPath)) {"
    new = "function extractAllowedPaths(root, taskId, activeTask) {\n  // T-0169 修复：gate-guard 未 require fs，此处显式引入\n  const fs = require('fs');\n  // 1. 任务卡文件：front-matter YAML 或 Markdown `## 允许路径` 节\n  const cardPath = path.join(root, '.ai', 'tasks', taskId + '.md');\n  try {\n    if (fs.existsSync(cardPath)) {"
    if "此处显式引入" in t:
        print("[same] fs already required in helper")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    GG.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(GG)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[fix] extractAllowedPaths now requires fs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
