#!/usr/bin/env python3
"""fix_gate_guard_allowed.py — 修复 gate-guard allowed_paths 读取（T-0169 P1 根治）

缺陷：gate-guard.js 从 task_graph.yaml 的 task 对象读 allowed_paths（`activeTask._raw`），
但：① task 对象无 _raw；② allowed_paths 实际在任务卡文件 `.ai/tasks/<id>.md` 的
front-matter 中，不在 task_graph.yaml 节点里 → 检查在真实项目上从未生效。

修复：allowed_paths 从任务卡文件 front-matter 读取（yaml 块 `allowed_paths:` 列表），
保留 task_graph 兜底（若节点本身含 allowed_paths）。
"""
from pathlib import Path

GG = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js")

def main() -> int:
    t = GG.read_text(encoding="utf-8")

    old = """      if (activeTask && activeTask.allowed_paths) {
        const allowedPaths = common.extractYamlList(activeTask._raw || '', 'allowed_paths');

        if (allowedPaths.length > 0 && isFileWrite && filePath) {"""
    new = """      if (activeTask) {
        // T-0169 修复：allowed_paths 从任务卡文件 front-matter 读取（task_graph 节点不含此字段）
        const allowedPaths = extractAllowedPaths(root, state.active_task_id, activeTask);

        if (allowedPaths.length > 0 && isFileWrite && filePath) {"""
    if "extractAllowedPaths" in t:
        print("[same] already fixed")
        return 0
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)

    # 添加辅助函数（在 main 之前）
    helper = """
/**
 * T-0169：从任务卡 front-matter 提取 allowed_paths（YAML 块 `allowed_paths:` 列表）。
 * 兜底：activeTask.allowed_paths（若解析器已提取）或 activeTask._raw（旧格式）。
 */
function extractAllowedPaths(root, taskId, activeTask) {
  // 1. 任务卡文件 front-matter
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
  } catch { /* best effort */ }
  // 2. 兜底：task_graph 节点字段
  if (activeTask && Array.isArray(activeTask.allowed_paths) && activeTask.allowed_paths.length > 0) {
    return activeTask.allowed_paths;
  }
  if (activeTask && activeTask._raw) {
    const list = common.extractYamlList(activeTask._raw, 'allowed_paths');
    if (list.length > 0) return list;
  }
  return [];
}

"""
    # 插入到 main 函数定义前
    anchor_main = "async function main() {"
    assert t.count(anchor_main) == 1, "main anchor"
    t = t.replace(anchor_main, helper + anchor_main, 1)

    GG.write_text(t, encoding="utf-8")

    import subprocess
    r = subprocess.run(["node", "-c", str(GG)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[err] syntax:", r.stderr[:300])
        return 1
    print("[fix] gate-guard allowed_paths now reads task card front-matter")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
