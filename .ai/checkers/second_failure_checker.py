#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SecondFailureGate — 二次失败门禁检查器（T-0097，B2 §3.4 second-failure
doctrine）。

纯确定性代码，不依赖 LLM。同类失败复发（同类别 + 同根因指纹）且未解决
（关联复盘无 open 行动项）→ BLOCK（SECOND_FAILURE_UNRESOLVED，含明细）；
有 owner 行动项 / 复盘已闭环 / 记录已显式 resolved → PASS；有效豁免
（reason/expires_at/approver，SLO 同款）→ PASS；证据文件不可解析 →
fail-closed BLOCK（列出文件）；开关未启用 → PASS（advisory，附说明）。
与 compile_gate.py / slo_gate_checker.py 同款 CLI 风格，可被质量门禁系统或
release 验证脚本直接调用。

用法：
    python .ai/checkers/second_failure_checker.py <project_root>
    python .ai/checkers/second_failure_checker.py . --detect --output sf_result.json

--detect：评估前先运行复发检测并把新检测到的 second-failure 记录落盘到
    .ai/evidence/observability/second-failures.yaml（report 级）。默认不写
    任何文件（纯只读门禁）。

开关（默认关闭，wave 1 advisory / opt-in）：
    LOOP_SECOND_FAILURE_GATE_ENABLED=1|true 环境变量，或
    .zcode/skills/loop-governance/config.yaml 中
        second_failure_gate:
          enabled: true

输出（JSON，stdout）：
    {
      "checker_id": "second_failure",
      "status": "pass" | "block" | "error",
      "exit_code": 0 | 1 | 2,
      "decision": "PASS" | "BLOCK",
      "reason": "...",
      "status_detail": "PASS | BLOCKED | NOT_AVAILABLE | DISABLED",
      "blocking": [...],
      "warnings": [...],
      "notes": [...],
      "exemption": {...} | null,
      "gate_enabled": true | false,
      "timestamp": "..."
    }

退出码：
    0 = PASS（含开关禁用 / 有效豁免放行）
    1 = BLOCK（未解决 second-failure，或证据不可解析 fail-closed）
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


def run_second_failure_check(project_root: Path, detect: bool = False) -> dict:
    """Run the second-failure gate and return a JSON-reportable dict.

    ``detect=True`` persists newly detected recurrence records first (report
    maintenance mode); the gate evaluation itself is read-only.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return {
            "checker_id": "second_failure",
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
        from loop_core.second_failure import (
            record_second_failure,
            second_failure_block,
        )

        if detect:
            record_second_failure(project_root)
        result = second_failure_block(project_root)
    except SystemExit:
        raise
    except Exception as exc:
        return {
            "checker_id": "second_failure",
            "status": "error",
            "exit_code": EXIT_ERROR,
            "decision": None,
            "reason": (
                f"Second-failure gate execution failed: "
                f"{type(exc).__name__}: {exc}"
            ),
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
        description=(
            "SecondFailureGate — 二次失败门禁：同类失败复发未解决时阻断 "
            "（T-0097，B2 §3.4）"
        )
    )
    parser.add_argument("project_root", help="项目根目录路径")
    parser.add_argument(
        "--detect", action="store_true",
        help="评估前先运行复发检测并落盘 second-failures.yaml（report 级；"
             "默认只读，不写任何文件）",
    )
    parser.add_argument(
        "--output", default=None,
        help="结果输出 JSON 文件路径（可选）。也始终输出到 stdout。",
    )
    args = parser.parse_args()

    result = run_second_failure_check(Path(args.project_root), detect=args.detect)

    json_output = json.dumps(result, ensure_ascii=False, indent=2)
    print(json_output)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output, encoding="utf-8")

    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
