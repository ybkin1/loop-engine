#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SloGate — SLO 门禁检查器（T-0093 wave 2：error budget 耗尽自动冻结发布）。

纯确定性代码，不依赖 LLM。基于 D2（T-0090）的 error budget 核算把发布门禁
接线到发布验证链：budget 耗尽 → BLOCK（ERROR_BUDGET_EXHAUSTED）；健康 →
PASS；数据不足/不可判定 → fail-closed BLOCK（列出缺失源）。与
compile_gate.py 同款 CLI 风格，可被质量门禁系统或 release 验证脚本直接调用。

用法：
    python .ai/checkers/slo_gate_checker.py <project_root>
    python .ai/checkers/slo_gate_checker.py . --window 2026-07-01..2026-09-30
    python .ai/checkers/slo_gate_checker.py . --slo .ai/slo.yaml --releases 3 --output slo_gate_result.json

输出（JSON，stdout）：
    {
      "checker_id": "slo_gate",
      "status": "pass" | "block" | "error",
      "exit_code": 0 | 1 | 2,
      "decision": "PASS" | "BLOCK",
      "reason": "...",
      "status_detail": "HEALTHY | CONSUMING | FREEZE_RECOMMENDED | NOT_AVAILABLE | DISABLED",
      "budget": {...},
      "missing": [...],
      "warnings": [...],
      "notes": [...],
      "timestamp": "..."
    }

退出码：
    0 = PASS（含开关禁用 / 有效豁免放行）
    1 = BLOCK（error budget 耗尽，或数据不足 fail-closed）
    2 = 参数错误或无法访问目录
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

EXIT_PASS = 0
EXIT_BLOCK = 1
EXIT_ERROR = 2


def _parse_window(text: str | None) -> tuple[str, str] | None:
    if not text or text in ("all", "quarterly"):
        return None
    parts = text.split("..")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise SystemExit(
            f"bad --window {text!r}; expected 'all' or YYYY-MM-DD..YYYY-MM-DD"
        )
    return (parts[0].strip(), parts[1].strip())


def run_slo_gate_check(project_root: Path, window: tuple[str, str] | None = None,
                       slo_path: str | None = None,
                       releases: int = 0) -> dict:
    """Run the SLO gate and return a JSON-reportable dict.

    ``slo_path`` mirrors tools/loop_metrics.py --slo: an explicit slo.yaml
    override path (default: .ai/slo.yaml with B2 defaults).
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return {
            "checker_id": "slo_gate",
            "status": "error",
            "exit_code": EXIT_ERROR,
            "decision": None,
            "reason": f"Project root not found: {project_root}",
            "timestamp": timestamp,
        }

    # loop_core ships with this repository (.ai/checkers/../..).  The checker
    # may be invoked against a different project root (e.g. a fixture), so the
    # repo root is preferred; the target root comes second (a governed project
    # with its own loop_core still wins for its own gate semantics).
    repo_root = Path(__file__).resolve().parent.parent.parent
    for candidate in (repo_root, project_root):
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))

    try:
        from loop_core.governance_metrics import load_slo_config
        from loop_core.slo_gate import _check_with_config, check_slo_gate

        if slo_path:
            config = load_slo_config(project_root, slo_path=slo_path)
            result = _check_with_config(
                project_root, config, window=window, releases=releases,
            )
        else:
            result = check_slo_gate(project_root, window=window, releases=releases)
    except SystemExit:
        raise
    except Exception as exc:
        return {
            "checker_id": "slo_gate",
            "status": "error",
            "exit_code": EXIT_ERROR,
            "decision": None,
            "reason": f"SLO gate execution failed: {type(exc).__name__}: {exc}",
            "timestamp": timestamp,
        }

    payload = result.to_dict()
    payload["status"] = "pass" if result.decision == "PASS" else "block"
    payload["exit_code"] = EXIT_PASS if result.decision == "PASS" else EXIT_BLOCK
    payload["status_detail"] = result.status
    payload["timestamp"] = timestamp
    return payload


def main():
    parser = argparse.ArgumentParser(
        description="SloGate — SLO 门禁：error budget 耗尽自动冻结发布（T-0093 wave 2）"
    )
    parser.add_argument("project_root", help="项目根目录路径")
    parser.add_argument(
        "--window", default=None,
        help="budget 窗口：'all' 或 YYYY-MM-DD..YYYY-MM-DD（默认取 slo.yaml 窗口，"
             "否则全部数据）",
    )
    parser.add_argument(
        "--slo", default=None,
        help=".ai/slo.yaml 覆盖路径（可选；默认 .ai/slo.yaml，缺失时用 B2 默认值）",
    )
    parser.add_argument(
        "--releases", type=int, default=0,
        help="release 数量（release fee 消费；0 = 不评估）",
    )
    parser.add_argument(
        "--output", default=None,
        help="结果输出 JSON 文件路径（可选）。也始终输出到 stdout。",
    )
    args = parser.parse_args()

    try:
        window = _parse_window(args.window)
    except SystemExit as exc:
        result = {
            "checker_id": "slo_gate",
            "status": "error",
            "exit_code": EXIT_ERROR,
            "decision": None,
            "reason": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(EXIT_ERROR)

    result = run_slo_gate_check(
        Path(args.project_root), window=window, slo_path=args.slo,
        releases=args.releases,
    )

    json_output = json.dumps(result, ensure_ascii=False, indent=2)
    print(json_output)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output, encoding="utf-8")

    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
