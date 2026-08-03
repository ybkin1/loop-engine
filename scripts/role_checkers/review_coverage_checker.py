"""
review_coverage_checker.py — Verify review covered all changed files.

T-0110 批 A（P3 消解）：
- D3-6: `git diff --name-only` 补 timeout=GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS
  + 异常兜底（git 缺失/挂起 → status=ERROR dict，不再 crash）；
- D4-9: 裸 `except:` 收窄为 (ValueError, OSError)（JSON 解析/IO 错误）+ 记原因。
"""
import json
import logging
import sys
import subprocess
from pathlib import Path

# repo root 入 path：独立运行也可消费 loop_core.constants（D3-6 超时常量）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loop_core.constants import GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS  # noqa: E402

logger = logging.getLogger(__name__)


def check(project_root, evidence_path):
    try:
        # T-0110 D3-6: 补 timeout + 异常兜底（was 无 timeout，git 挂起即整体卡死）
        r = subprocess.run(["git", "diff", "--name-only", "HEAD~1"],
                           capture_output=True, text=True, cwd=project_root,
                           timeout=GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("git diff unavailable: %s", exc)
        return {"status": "ERROR", "changed": [],
                "reason": f"git diff unavailable: {type(exc).__name__}: {exc}"}
    changed = set(f.strip() for f in r.stdout.split("\n") if f.strip())
    ep = Path(evidence_path)
    if not ep.exists():
        return {"status": "MISSING", "changed": sorted(changed)}
    try:
        ev = json.loads(ep.read_text())
    except (ValueError, OSError) as exc:  # T-0110 D4-9: 收窄裸 except + 记原因
        logger.warning("evidence unreadable: %s", exc)
        return {"status": "INVALID"}
    reviewed = set(ev.get("files_reviewed", []))
    missing = changed - reviewed
    return {"status": "INCOMPLETE" if missing else "OK", "changed": len(changed), "reviewed": len(reviewed), "missing": sorted(missing), "coverage_pct": round(len(reviewed & changed) / len(changed) * 100, 1) if changed else 100}


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1] if len(sys.argv) > 1 else ".",
                           sys.argv[2] if len(sys.argv) > 2 else ""), indent=2))
