"""T-0110 批 B-2 golden 生成器（human_review_packet / context_loader 拆分前/后）。

用法：
    C:/Python312/python.exe .ai/evidence/T-0110/golden/generate_golden_b2.py <out.json>

捕获内容：
- human_review_packet：常量/枚举/模型默认值/序列化往返+失败路径（U6）/
  build_resume_payload 成功+11 例 fail-closed/resume_from_payload 成功+9 例
  drift/to_markdown+to_plain_text 全文（全节/最小/否决包）/渲染辅助/
  builder 三路（phase/veto/raw）+translate_technical_risk 5 例/_extract_key_choices
- context_loader：常量/正则族/摘要级别与行选择辅助/summarize_text 5 例/
  estimate_tokens 5 例/CitationResolver 9 例（含自定义 roots）/
  repair_truncated_references 3 例（含 T-0095 子串守卫）/
  ContextCompressor 8 例/load_role_context 3 级+3 失败/D3 记忆注入 6 例
  （默认 False 保持 + 损坏存储 fail-closed）/文档索引 4 例/load_for_role 3 例/
  _select_relevant_sections 7 例（含路由表）/front-matter+路由缓存
- 两模块 dir() 全量快照（re-export 完整性基线）

运行期仅写 out.json；不触碰仓库任何产品代码。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from t0110_b1_golden import dump_json, module_dir_snapshot  # noqa: E402
from t0110_b2_golden import (  # noqa: E402
    capture_context_loader_golden,
    capture_human_review_packet_golden,
)


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).parent / "golden-b2-before.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        payload["human_review_packet"] = capture_human_review_packet_golden(
            Path(tmp))
        payload["context_loader"] = capture_context_loader_golden(Path(tmp))
    payload["dir_snapshots"] = {
        "loop_core.human_review_packet": module_dir_snapshot(
            "loop_core.human_review_packet"),
        "loop_core.context_loader": module_dir_snapshot(
            "loop_core.context_loader"),
    }

    out_path.write_text(dump_json(payload), encoding="utf-8")
    print(f"golden written: {out_path} "
          f"({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
