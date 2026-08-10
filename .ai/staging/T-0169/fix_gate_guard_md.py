#!/usr/bin/env python3
"""fix_gate_guard_md.py — extractAllowedPaths 支持 Markdown `## 允许路径` 节（T-0169）

任务卡有两种格式：
1. YAML front-matter（`---\\nallowed_paths:\\n  - src/\\n---`）
2. Markdown 节（`## 允许路径\\n- src/`）
"""
from pathlib import Path

GG = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js")

def main() -> int:
    t = GG.read_text(encoding="utf-8")

    old = """  // 1. 任务卡文件 front-matter
  const cardPath = path.join(root, '.ai', 'tasks', taskId + '.md');
  try {
    if (fs.existsSync(cardPath)) {
      const raw = fs.readFileSync(cardPath, 'utf-8');
      const fm = raw.match(/^---\\n([\\s\\S]*?)\\n---/);
      if (fm) {
        const list = common.extractYamlList(fm[1], 'allowed_paths');
        if (list.length > 0) return list;
      }
    }
  } catch { /* best effort */ }"""
    new = """  // 1. 任务卡文件：front-matter YAML 或 Markdown `## 允许路径` 节
  const cardPath = path.join(root, '.ai', 'tasks', taskId + '.md');
  try {
    if (fs.existsSync(cardPath)) {
      const raw = fs.readFileSync(cardPath, 'utf-8').replace(/\\r\\n/g, '\\n');
      // 1a. YAML front-matter
      const fm = raw.match(/^---\\n([\\s\\S]*?)\\n---/);
      if (fm) {
        const list = common.extractYamlList(fm[1], 'allowed_paths');
        if (list.length > 0) return list;
      }
      // 1b. Markdown `## 允许路径` 节（`- src/` 或 `- C:\\path`）
      const mdSection = raw.match(/##\\s*允许路径\\s*\\n([\\s\\S]*?)(?=\\n##\\s|\\n## Status|$)/);
      if (mdSection) {
        const list = [];
        for (const line of mdSection[1].split('\\n')) {
          const m = line.match(/^\\s*[-*]\\s*(.+?)\\s*$/);
          if (m && m[1] && !m[1].startsWith('#')) list.push(m[1].trim());
        }
        if (list.length > 0) return list;
      }
    }
  } catch { /* best effort */ }"""
    if "1b. Markdown" in t:
        print("[same] markdown section support already added")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    GG.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(GG)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[fix] extractAllowedPaths supports Markdown 允许路径 section")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
