#!/usr/bin/env python3
"""fix_p1_ab.py — 修复终审 P1-a（TRACE2 残留）+ P1-b（task_graph 兜底失效）"""
from pathlib import Path

GG = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js")

def main() -> int:
    t = GG.read_text(encoding="utf-8")

    # P1-a: 删除 TRACE2 残留
    tr2 = "       process.stderr.write('[TRACE2] cardPath=' + cardPath + ' raw=' + JSON.stringify(raw.slice(0, 60)) + '\\n');\n"
    if tr2 in t:
        t = t.replace(tr2, "")
        print("[fix] P1-a: TRACE2 removed")
    else:
        print("[info] P1-a: no TRACE2 found (maybe different indent)")

    # P1-b: task_graph 兜底改读原始文件（不依赖解析器产物）
    old_b = """  // 2. 兜底：task_graph 节点字段
  if (activeTask && Array.isArray(activeTask.allowed_paths) && activeTask.allowed_paths.length > 0) {
    return activeTask.allowed_paths;
  }
  if (activeTask && activeTask._raw) {
    const list = common.extractYamlList(activeTask._raw, 'allowed_paths');
    if (list.length > 0) return list;
  }
  return [];"""
    new_b = """  // 2. 兜底：task_graph.yaml 原始文本（解析器产物无 _raw 且 allowed_paths 值可能为空串）
  try {
    const graphPath = path.join(root, '.ai', 'task_graph.yaml');
    if (fs.existsSync(graphPath)) {
      const graphRaw = fs.readFileSync(graphPath, 'utf-8').replace(/\\r\\n/g, '\\n');
      const list = common.extractYamlList(graphRaw, 'allowed_paths');
      if (list.length > 0) return list;
    }
  } catch { /* best effort */ }
  return [];"""
    if "graphPath" in t:
        print("[info] P1-b: already fixed")
    else:
        assert t.count(old_b) == 1, f"P1-b anchor count={t.count(old_b)}"
        t = t.replace(old_b, new_b)
        print("[fix] P1-b: task_graph fallback reads raw file")

    GG.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(GG)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    if "TRACE" in t:
        print("[warn] still contains TRACE strings!")
    else:
        print("[ok] no TRACE strings remain")
    print("[ok] syntax OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
