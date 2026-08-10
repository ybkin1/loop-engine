#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_package.py — ZCode → Pi 任务包导出（P1-3 双向任务包协议）

把 ZCode 任务卡导出为"任务包"（JSON），Pi 侧 /task-import 可直接导入执行，
形成 ZCode 派发 → Pi 质量环执行 → 证据回灌验收的完整闭环。

用法：
    python .zcode/tools/task_package.py export --task T-XXXX [--to <path>]
      --task    ZCode 任务 ID（读 .ai/tasks/T-XXXX.md）
      --to      输出路径（缺省 .ai/evidence/T-XXXX/task-package.json；
                Pi 侧可读位置如 ~/.pi/agent/inbox/ 亦可）

输出 schema（task-package/v1）：
    task_id / title / ac[] / allowed_paths[] / forbidden_actions[] /
    verification[]（空，由 Pi 侧补）/ risk（标题关键词自动分级）/
    project_context（AGENTS.md 摘要）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HIGH_RISK_KEYWORDS = (
    "auth|login|password|secret|token|credential|api[-_ ]?key|database|migration|"
    "deploy|payment|stripe|external|ssh|证书|密钥|支付|权限|数据库|迁移|部署"
)


def parse_task_card(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    title = ""
    m = re.search(r"^#\s+T-\d+:\s*(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()

    def section(name: str) -> list[str]:
        # 匹配 "## <name>" 到下一个 "## " 之间的内容
        m = re.search(rf"^##\s+{name}\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.M)
        if not m:
            return []
        lines = []
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(("- ", "* ")):
                lines.append(line[2:].strip())
        return lines

    acs = []
    m = re.search(r"^##\s+可验证验收标准\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.M)
    if m:
        for line in m.group(1).splitlines():
            am = re.search(r"\[\s*AC-\d+\s*\]\s*(.+)", line.strip())
            if am:
                acs.append(am.group(1).strip().lstrip("* ").strip())

    allowed = section("允许路径")
    forbidden = section("禁止动作")
    return {"title": title, "ac": acs, "allowed_paths": allowed, "forbidden_actions": forbidden}


def main() -> int:
    ap = argparse.ArgumentParser(description="ZCode → Pi 任务包导出")
    ap.add_argument("export", nargs="?", default="export", help="子命令（当前仅 export）")
    ap.add_argument("--task", required=True, help="ZCode 任务 ID（T-XXXX）")
    ap.add_argument("--to", default=None, help="输出路径（缺省 .ai/evidence/<task>/task-package.json）")
    ap.add_argument("--zcode-root", default=".", help="ZCode 项目根")
    args = ap.parse_args()

    root = Path(args.zcode_root).resolve()
    task = args.task.upper()
    card = root / ".ai" / "tasks" / f"{task}.md"
    if not card.exists():
        print(f"[error] 任务卡不存在: {card}", file=sys.stderr)
        return 2

    parsed = parse_task_card(card)
    risk = "CRITICAL" if re.search(HIGH_RISK_KEYWORDS, parsed["title"], re.I) else "STANDARD"
    project_context = ""
    agents = root / "AGENTS.md"
    if agents.exists():
        project_context = agents.read_text(encoding="utf-8")[:1200]

    pkg = {
        "schema": "task-package/v1",
        "task_id": task,
        "title": parsed["title"],
        "ac": parsed["ac"],
        "allowed_paths": parsed["allowed_paths"],
        "forbidden_actions": parsed["forbidden_actions"],
        "verification": [],
        "risk": risk,
        "project_context": project_context,
    }

    out = Path(args.to) if args.to else root / ".ai" / "evidence" / task / "task-package.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] 任务包导出: {out}")
    print(f"[ok] {task} '{parsed['title']}' | AC {len(parsed['ac'])} 条 | risk {risk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
