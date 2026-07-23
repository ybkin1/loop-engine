#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
role_isolation.py — ZCode PreToolUse hook：检测 self-review 违规并输出 WARN。

检查逻辑：
1. 从 state.yaml 读取 current_task_id
2. 从任务合同文件 (.ai/tasks/<task_id>.md) 读取 developer_agent_id 和 reviewer_agent_id
3. 如果两者相同且非空 → 判定为 self-review，输出 WARN JSON
4. 如果 hook_input 中包含 agent_id 字段（部分 host 提供），也纳入检查

重要：此 hook 只输出 WARN，不阻断（exit 0）。
Agent ID 在 hook 层面不可靠——真正的隔离应由 host 层执行。
这里的目的是提前发现潜在风险，通知用户决策。

退出码：0 = 放行（即使检测到 self-review 也只是 WARN，不阻断）。
JSON 输出到 stdout（ZCode 可解析的 hookSpecificOutput 格式）。
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (  # noqa: E402
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    load_config,
    load_state,
    normalize_rel,
    project_root,
    read_stdin_json,
)

EXIT_PASS = 0


def load_task_contract_roles(root: Path, task_id: str) -> dict:
    """从任务合同文件中提取角色分配。返回 {"developer_agent_id": ..., "reviewer_agent_id": ...}。

    缺失的键值为 None。
    """
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    result = {
        "developer_agent_id": None,
        "reviewer_agent_id": None,
    }
    if not task_path.exists():
        return result

    try:
        text = task_path.read_text(encoding="utf-8")
    except Exception:
        return result

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("developer_agent_id:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val and val.lower() != "null":
                result["developer_agent_id"] = val
        elif line.startswith("reviewer_agent_id:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val and val.lower() != "null":
                result["reviewer_agent_id"] = val

    return result


def load_task_graph_roles(root: Path, task_id: str) -> dict:
    """从 task_graph.yaml 中提取角色分配（YAML 版本）。"""
    task_graph_path = root / ".ai" / "task_graph.yaml"
    result = {
        "developer_agent_id": None,
        "reviewer_agent_id": None,
    }
    if not task_graph_path.exists():
        return result

    try:
        import yaml  # type: ignore
    except ImportError:
        return result

    try:
        with open(task_graph_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return result

    tasks = data.get("tasks", [])
    for task in tasks:
        if isinstance(task, dict) and task.get("id") == task_id:
            result["developer_agent_id"] = task.get("developer_agent_id")
            result["reviewer_agent_id"] = task.get("reviewer_agent_id")
            break

    return result


def emit_warn(reason: str, details: dict | None = None):
    """输出 WARN JSON 到 stdout（ZCode hookSpecificOutput 格式）。"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": (
                f"[role_isolation] WARN: {reason}"
            ),
        }
    }
    if details:
        output["hookSpecificOutput"]["_role_isolation_details"] = details
    sys.stdout.write(json.dumps(output, ensure_ascii=False))


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return EXIT_PASS

    try:
        cfg = load_config(root)
    except Exception:
        cfg = DEFAULT_CONFIG

    # 检查 role_isolation 配置是否启用
    role_cfg = cfg.get("role_isolation", {})
    if not role_cfg.get("enabled", True):
        return EXIT_PASS

    # 获取当前任务 ID
    try:
        state = load_state(root)
        task_id = state.get("current_task_id")
    except Exception:
        task_id = None

    if not task_id:
        return EXIT_PASS  # 没有活跃任务，无需检查

    # 从任务合同文件提取角色
    roles = load_task_contract_roles(root, task_id)

    # 如果合同文件没有角色信息，尝试 task_graph.yaml
    if roles["developer_agent_id"] is None and roles["reviewer_agent_id"] is None:
        graph_roles = load_task_graph_roles(root, task_id)
        if graph_roles["developer_agent_id"]:
            roles["developer_agent_id"] = graph_roles["developer_agent_id"]
        if graph_roles["reviewer_agent_id"]:
            roles["reviewer_agent_id"] = graph_roles["reviewer_agent_id"]

    dev_id = roles.get("developer_agent_id")
    rev_id = roles.get("reviewer_agent_id")

    # 两者都未设置 → 无角色隔离，放行
    if not dev_id and not rev_id:
        return EXIT_PASS

    # 只有一个角色设置 → 未完成角色分配，放行但提示
    if (dev_id and not rev_id) or (rev_id and not dev_id):
        if role_cfg.get("warn_incomplete_roles", True):
            emit_warn(
                f"任务 {task_id} 的角色分配不完整："
                f"developer={dev_id or '<未分配>'}, reviewer={rev_id or '<未分配>'}。"
                "建议在开始实现前完成双角色分配。",
                {"task_id": task_id, "developer_agent_id": dev_id, "reviewer_agent_id": rev_id},
            )
        return EXIT_PASS

    # 检查 self-review
    if dev_id and rev_id and dev_id == rev_id:
        emit_warn(
            f"SELF_REVIEW 风险：任务 {task_id} 的 developer 和 reviewer "
            f"是同一 Agent ({dev_id})。这违反了独立审查原则。"
            "请分配不同的 reviewer，或确保 host 层角色隔离生效。",
            {"task_id": task_id, "developer_agent_id": dev_id, "reviewer_agent_id": rev_id,
             "severity": "SELF_REVIEW"},
        )

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
