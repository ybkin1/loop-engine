#!/usr/bin/env python3
"""
conclusion_packet.py — T-0134 P4 结论包生成器（授权模型 v2）。

用户接触面收敛为三件事：输入目标 / 验收结论 / 随时说"停"。
结论包 = 成果一句话 + 演示/冒烟 + 证据路径（想看才看）；验收对象是成果，
不是过程。

用法：
    python conclusion_packet.py <root> --task T-XXXX \
        --summary "一句话成果" --demo "演示/冒烟说明" [--evidence "路径1,路径2"]

产出 .ai/evidence/<task>/conclusion-packet.md
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def generate(root: Path, task_id: str, summary: str, demo: str,
             evidence: list[str]) -> Path:
    out = root / ".ai" / "evidence" / task_id / "conclusion-packet.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 结论包（T-0134）— {task_id}",
        "",
        f"> 生成于 {datetime.now(timezone.utc).isoformat()}",
        "",
        "## 成果（一句话）",
        "",
        summary,
        "",
        "## 演示 / 冒烟",
        "",
        demo,
        "",
        "## 证据路径（想看才看）",
        "",
    ]
    for e in evidence:
        lines.append(f"- `{e}`")
    if not evidence:
        lines.append("- （无显式证据路径，见任务 evidence 目录）")
    lines.append("")
    lines.append("> 验收对象是成果，不是过程。不满意可要求自修重交；随时可喊停（revoke）。")
    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    print(f"[conclusion] written {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="T-0134 conclusion packet generator")
    parser.add_argument("root")
    parser.add_argument("--task", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--demo", required=True)
    parser.add_argument("--evidence", default="", help="comma-separated evidence paths")
    args = parser.parse_args()
    generate(Path(args.root).resolve(), args.task, args.summary, args.demo,
             [e.strip() for e in args.evidence.split(",") if e.strip()])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
