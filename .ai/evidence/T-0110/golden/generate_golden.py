"""T-0110 批 B-1 golden 生成器（拆分前/后各跑一次，输出逐字节可比 JSON）。

用法：
    C:/Python312/python.exe .ai/evidence/T-0110/golden/generate_golden.py <out.json>

捕获内容：
- governance_metrics：常量表 / 分类与统计辅助 / 加载器（含失败路径）/
  纯度量函数 / SLO 配置（缺省+覆盖+无效） / SLI 评估 / budget 记账 /
  DORA / Repair / LoopEffectiveness / 评分呈现 / 全量报告（显式窗口+数据窗口）
- intent_router：词表与常量 / 变更类型 / 检测与评分辅助 / analyze×语料×上下文 /
  should_escalate / route / 切分与切换信号 / U5 路由主流程（sticky/switch/degraded）
- 两模块 dir() 全量快照（re-export 完整性基线）

运行期仅写 out.json；不触碰仓库任何产品代码。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from t0110_b1_golden import (  # noqa: E402
    capture_governance_metrics_golden,
    capture_intent_router_golden,
    dump_json,
    module_dir_snapshot,
)


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).parent / "golden-before.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        payload["governance_metrics"] = capture_governance_metrics_golden(
            Path(tmp))
    payload["intent_router"] = capture_intent_router_golden()
    payload["dir_snapshots"] = {
        "loop_core.governance_metrics": module_dir_snapshot(
            "loop_core.governance_metrics"),
        "loop_core.intent_router": module_dir_snapshot("loop_core.intent_router"),
    }

    out_path.write_text(dump_json(payload), encoding="utf-8")
    print(f"golden written: {out_path} "
          f"({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
