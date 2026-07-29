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
import logging
import sys
from pathlib import Path

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

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

    # T-0068: Human review interrupt — check if current phase requires human review
    current_phase = state.get("current_phase", "")
    human_review_phases = {
        "S1-requirements": "请用户确认需求范围、优先级、验收标准",
        "S2-architecture": "请用户确认技术选型、模块边界",
        "S5-quality": "请用户审查质量/测试/安全/Review 四项报告",
        "S6-delivery": "请用户做最终 GO/NO-GO 决策",
    }
    if current_phase in human_review_phases and not pending:
        lines.append("")
        lines.append("🤚 人工评审中断（HUMAN REVIEW REQUIRED）")
        lines.append(f"当前阶段 {current_phase} 要求人工评审: {human_review_phases[current_phase]}")
        lines.append("在用户完成评审并批准 gate 之前，AI 不得继续推进到下一阶段。")
        lines.append("将以下内容展示给用户：")
        lines.append("  1. 本阶段的全部强制产出")
        lines.append("  2. 子代理审查报告（如有）")
        lines.append("  3. gate 批准/拒绝/修复的选择")


    # T-0076 Layer 4: Check if current phase has required role evidence
    current_phase = state.get("current_phase", "")
    quality_phases = {"S5-quality", "S6-delivery"}
    if current_phase in quality_phases:
        try:
            from loop_core.role_orchestrator import get_roles_for_phase
            required = get_roles_for_phase(current_phase)
            task_id = state.get("current_task_id", "")
            missing = []
            for r in required:
                if r == "main-thread":
                    continue
                ev = root / ".ai/evidence" / task_id / "role-outputs" / f"{r}.json"
                if not ev.exists():
                    missing.append(r)
            if missing:
                lines.append("")
                lines.append("=== MISSING ROLE EVIDENCE (Layer 4) ===")
                lines.append(f"Phase {current_phase} requires roles: {', '.join(required)}")
                lines.append(f"Missing evidence for: {', '.join(missing)}")
                lines.append("The main agent MUST dispatch these roles via Agent() before advancing.")
                lines.append("Without role evidence, the gate cannot be approved.")
        except ImportError:
            pass

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
        # 注入失败不阻断会话，但治理项目中应以 ERROR 级别记录
        logger.error("session_brief 摘要生成失败（%s），治理状态注入缺失。", e, exc_info=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# Dashboard Summary (AutoPlan product layer)
try:
    from loop_core.status_dashboard import Dashboard
    import os as _os
    _proj_root = _os.environ.get("LOOP_PROJECT_ROOT", project_root)
    dashboard = Dashboard(_proj_root)
    status = dashboard.generate()
    brief_lines.append("")
    brief_lines.append("## 📊 Project Dashboard")
    brief_lines.append(f"- Health: {status.health_indicator}")
    brief_lines.append(f"- Tasks: {status.task_stats['completed']}/{status.task_stats['total']} completed, {status.task_stats['blocked']} blocked")
    brief_lines.append(f"- Inbox: {status.inbox_count} requirements")
    if status.ready_tasks:
        brief_lines.append(f"- Ready: {', '.join(status.ready_tasks[:3])}")
    if status.next_recommended:
        brief_lines.append(f"- Next: {status.next_recommended}")
    brief_lines.append(f"- Action: {status.next_action}")
except Exception:
    pass  # Dashboard unavailable — not a blocker
