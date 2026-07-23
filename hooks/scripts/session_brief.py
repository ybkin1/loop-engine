#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
session_brief.py — ZCode SessionStart hook：会话启动时注入治理状态摘要。

把 .ai/state.yaml / .ai/gates.yaml / .ai/HANDOFF.md 的关键事实作为
additionalContext 注入会话，使"启动检查"不依赖 AI 自觉阅读文件：
- 当前阶段、当前任务、current_gate_id
- pending gate 列表（最多 max_pending_listed 条）
- HANDOFF 中的 Next Session First Step（若存在）

本 hook 永不阻断：任何失败都 exit 0（非治理项目则完全静默）。
输出为 SessionStart JSON：{"hookSpecificOutput": {"hookEventName":
"SessionStart", "additionalContext": ...}}。
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (  # noqa: E402
    DEFAULT_CONFIG,
    is_governance_project,
    load_config,
    load_state,
    pending_gates,
    project_root,
    read_stdin_json,
)


def handoff_next_step(root):
    """提取 HANDOFF.md 的 'Next Session First Step' 一节前几行，失败返回 None。"""
    handoff = root / ".ai" / "HANDOFF.md"
    if not handoff.exists():
        return None
    try:
        text = handoff.read_text(encoding="utf-8")
    except Exception:
        return None
    marker = "## Next Session First Step"
    idx = text.find(marker)
    if idx == -1:
        return None
    section = text[idx + len(marker):].strip().splitlines()
    lines = [line for line in section if not line.startswith("## ")][:4]
    return "\n".join(lines).strip() or None


def build_brief(root, cfg):
    state = load_state(root)
    pending = pending_gates(root)
    brief_cfg = cfg.get("session_brief", DEFAULT_CONFIG["session_brief"])
    limit = int(brief_cfg.get("max_pending_listed", 10))

    lines = [
        "[loop-governance] 治理状态摘要（SessionStart hook 自动注入）",
        f"phase: {state.get('current_phase', '<unknown>')}",
        f"current_task_id: {state.get('current_task_id') or 'none'}",
        f"current_gate_id: {state.get('current_gate_id') or 'none'}",
    ]
    if pending:
        shown = pending[:limit]
        lines.append(
            "PENDING GATES（存在等待用户决策的 gate，写入操作已被 gate_guard 阻断）："
        )
        lines.extend(f"  - {g}" for g in shown)
        if len(pending) > limit:
            lines.append(f"  ... 以及另外 {len(pending) - limit} 条")
        lines.append("请向用户展示 gate 内容，等待明确批准、拒绝或修复请求。")
    else:
        lines.append("pending gates: none")

    next_step = handoff_next_step(root)
    if next_step:
        lines.append("HANDOFF next step:")
        lines.append(next_step)
    lines.append("提醒：reviewer PASS / validator / 测试通过均为 evidence，不等于用户批准。")
    return "\n".join(lines)


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return 0

    try:
        cfg = load_config(root)
        if not cfg.get("session_brief", DEFAULT_CONFIG["session_brief"]).get("enabled", True):
            return 0
        brief = build_brief(root, cfg)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": brief,
            }
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
    except Exception as e:
        # 注入失败不阻断会话，只在 stderr 留痕
        print(f"[session_brief] WARN: 摘要生成失败（{e}）。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
