#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
role_isolation.py — ZCode PreToolUse hook：检测 self-review 违规并根据 enforcement_level 决定 WARN 或 DENY。

v2.0 升级：
- 当 loop_mode=FULL 且 enforcement 为 HARD 时 → 检测到 self-review 返回 deny（真阻断）
- 当 loop_mode=LIGHTWEIGHT 或 enforcement 为 ADVISORY 时 → 仅 WARN（保持向后兼容）
- 通过 EnforcementHub 读取治理状态，不再依赖主控自觉

检查逻辑：
1. 从 state.yaml 读取 loop_mode
2. 从任务文件读取 developer_agent_id 和 reviewer_agent_id
3. 如果两者相同且非空：
   - FULL mode → BLOCK (permissionDecision: "deny", exit 2)
   - 其他模式 → WARN (permissionDecision: "allow", exit 0)
4. 也检查 enforcement_level 声明

退出码：
- 2 = 阻断（HARD enforcement + self-review detected）
- 0 = 放行
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
    project_root,
    read_stdin_json,
    extract_target_path,
    normalize_rel,
)

# ── Governance file exemption — prevents fail-closed deadlock ──────────
GOVERNANCE_EXEMPT = [
    ".ai/gates.yaml",
    ".ai/state.yaml",
    ".ai/task_graph.yaml",
    ".ai/project_continuity.yaml",
]

EXIT_PASS = 0
EXIT_BLOCK = 2


def load_task_contract_roles(root: Path, task_id: str) -> dict:
    """从任务合同文件中提取角色分配。"""
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    result = {"developer_agent_id": None, "reviewer_agent_id": None}
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


def emit_deny(reason: str, details: dict | None = None):
    """输出 DENY JSON 到 stdout（阻断）。"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[role_isolation] DENY: {reason}",
            "enforcement_level": "HARD",
        }
    }
    if details:
        output["hookSpecificOutput"]["_role_isolation_details"] = details
    sys.stdout.write(json.dumps(output, ensure_ascii=False))


def emit_warn(reason: str, details: dict | None = None):
    """输出 WARN JSON 到 stdout（放行但警告）。"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"[role_isolation] WARN: {reason}",
            "enforcement_level": "ADVISORY",
        }
    }
    if details:
        output["hookSpecificOutput"]["_role_isolation_details"] = details
    sys.stdout.write(json.dumps(output, ensure_ascii=False))


def get_enforcement_level(state: dict, cfg: dict) -> str:
    """Determine enforcement level from state and config.

    FULL loop_mode → HARD enforcement
    STANDARD → PARTIAL
    LIGHTWEIGHT → ADVISORY
    """
    loop_mode = state.get("loop_mode", "").upper()
    if loop_mode == "FULL":
        return "HARD"
    elif loop_mode == "STANDARD":
        return "PARTIAL"
    return "ADVISORY"


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return EXIT_PASS

    try:
        cfg = load_config(root)
    except Exception:
        cfg = DEFAULT_CONFIG

    # Check role_isolation config
    role_cfg = cfg.get("role_isolation", {})
    if not role_cfg.get("enabled", True):
        return EXIT_PASS

    # ── Governance file exemption (v3.5) ────────────────────────────────
    # Allow writes to governance files even when state is corrupted,
    # so the user can fix the corruption. Without this, a corrupted
    # state.yaml triggers a permanent deadlock (blocked writes → can't fix).
    target = extract_target_path(hook_input)
    if target:
        rel = normalize_rel(root, target)
        if rel and rel.replace("\\", "/") in GOVERNANCE_EXEMPT:
            return EXIT_PASS

    # Get current state — FAIL CLOSED on error
    try:
        state = load_state(root)
        task_id = state.get("current_task_id")
    except Exception as e:
        emit_deny(
            f"无法读取治理状态（{e}）。按 fail-closed 策略阻断角色隔离检查；"
            "请先修复 .ai/state.yaml。"
        )
        return EXIT_BLOCK

    if not task_id:
        return EXIT_PASS

    # Determine enforcement level
    enf_level = get_enforcement_level(state, cfg)

    # Extract role assignments
    roles = load_task_contract_roles(root, task_id)
    dev_id = roles.get("developer_agent_id")
    rev_id = roles.get("reviewer_agent_id")

    # Both unset → pass
    if not dev_id and not rev_id:
        return EXIT_PASS

    # Incomplete role assignment → warn but pass
    if (dev_id and not rev_id) or (rev_id and not dev_id):
        if role_cfg.get("warn_incomplete_roles", True):
            emit_warn(
                f"任务 {task_id} 的角色分配不完整："
                f"developer={dev_id or '<未分配>'}, reviewer={rev_id or '<未分配>'}。",
                {"task_id": task_id, "developer_agent_id": dev_id, "reviewer_agent_id": rev_id},
            )
        return EXIT_PASS

    # Self-review detection
    if dev_id and rev_id and dev_id == rev_id:
        details = {
            "task_id": task_id,
            "developer_agent_id": dev_id,
            "reviewer_agent_id": rev_id,
            "severity": "SELF_REVIEW",
            "enforcement_level": enf_level,
        }

        if enf_level == "HARD":
            # v2.0: HARD enforcement — actually block
            emit_deny(
                f"SELF_REVIEW BLOCKED：任务 {task_id} 的 developer 和 reviewer "
                f"是同一 Agent ({dev_id})。在 FULL 模式下这违反独立审查原则，已被硬性阻断。"
                "请分配不同的 reviewer Agent。",
                details,
            )
            return EXIT_BLOCK
        else:
            # PARTIAL or ADVISORY — warn only (backward compatible)
            emit_warn(
                f"SELF_REVIEW 风险：任务 {task_id} 的 developer 和 reviewer "
                f"是同一 Agent ({dev_id})。当前 enforcement_level={enf_level}，仅警告不阻断。",
                details,
            )

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
