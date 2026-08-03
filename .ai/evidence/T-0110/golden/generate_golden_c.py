"""T-0110 批 C golden 生成器（hooks/scripts/loop_enforcement.py 拆分前/后）。

用法：
    C:/Python312/python.exe .ai/evidence/T-0110/golden/generate_golden_c.py <out.json>

捕获内容：
- hook 入口判定矩阵（子进程实跑 loop_enforcement.py，40+ 场景：
  PASS 放行/外部 BLOCK/治理工具/MCP 白名单/多门禁/自审/runtime projection/
  只读豁免/legacy fixture/C11 计数）
- 关键函数直接调用（路径/命令判定、契约解析、gate 证据检查、context
  builders、check_diff_scope patch subprocess 确定性捕获）
- loop_enforcement 模块 dir() 全量快照 + import * 公开面（re-export 完整性）

运行期只写 out.json；不触碰仓库任何产品代码（fixture 全在临时目录）。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from t0110_c_golden import capture_all, dump_json  # noqa: E402


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).parent / "golden-c-before.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        payload = capture_all(Path(tmp))

    out_path.write_text(dump_json(payload), encoding="utf-8")
    print(f"golden written: {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
