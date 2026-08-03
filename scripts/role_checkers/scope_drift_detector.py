"""scope_drift_detector.py — Detect scope drift: changed files vs allowed_paths.

T-0110 批 A（P3 消解）：
- D3-6: `git diff --name-only` 补 timeout=GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS
  + 异常兜底（git 缺失/挂起 → 返回 error dict，不再 crash）；
- D4-9: 裸 `except:` 收窄为 ImportError + 记原因（error 信息含导入失败详情）。
"""
import json
import logging
import sys
import subprocess
from pathlib import Path

# repo root 入 path：独立运行（python scripts/role_checkers/xxx.py）也可
# 消费 loop_core.constants（与 tools/loop_self_audit.py 同款引导）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loop_core.constants import GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS  # noqa: E402

logger = logging.getLogger(__name__)


def detect(project_root, task_id):
    root = Path(project_root)
    try:
        import yaml  # noqa: PLC0415
    except ImportError as exc:  # T-0110 D4-9: 收窄裸 except + 记原因
        logger.warning("yaml import failed: %s", exc)
        return {"error": f"yaml not available: {exc}"}
    if not yaml:
        return {"error": "yaml not available"}
    tg = yaml.safe_load((root / ".ai/task_graph.yaml").read_text()) or {}
    task = next((t for t in tg.get("tasks", []) if t.get("id") == task_id), None)
    if not task:
        return {"error": f"Task {task_id} not found"}
    allowed = set(task.get("allowed_paths", []))
    if not allowed:
        return {"status": "OK", "reason": "No allowed_paths defined"}
    try:
        # T-0110 D3-6: 补 timeout + 异常兜底（was 无 timeout，git 挂起即整体卡死）
        r = subprocess.run(["git", "diff", "--name-only", "HEAD~1"],
                           capture_output=True, text=True, cwd=str(root),
                           timeout=GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("git diff unavailable: %s", exc)
        return {"error": f"git diff unavailable: {type(exc).__name__}: {exc}"}
    changed = set(f.strip() for f in r.stdout.split("\n") if f.strip())
    violations = [f for f in changed if not any(f.startswith(a.rstrip("/")) for a in allowed)]
    return {"status": "SCOPE_DRIFT" if violations else "OK", "violations": violations, "count": len(violations)}


if __name__ == "__main__":
    print(json.dumps(detect(sys.argv[1] if len(sys.argv) > 1 else ".",
                            sys.argv[2] if len(sys.argv) > 2 else ""), indent=2))
