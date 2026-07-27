#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gate_guard.py — ZCode PreToolUse hook：pending gate 存在时阻断写入操作。

语义（与 .ai 治理契约一致，T-0046 修复 Gate 生命周期）：
- 非治理项目（无 .ai/state.yaml）→ 一律放行（exit 0）。
- 存在 status == "pending" 的 gate → 阻断（exit 2）。
- current_gate_id 指向 approved+in_progress/approved_not_started → 放行（在 scope 内）。
- current_gate_id 指向 approved+completed → 不作为当前执行 gate，放行。
- current_gate_id 指向 rejected/blocked → 阻断。
- current_gate_id 指向不存在的 gate → fail-closed 阻断。
- current_gate_id 属于其他 task → fail-closed 阻断。
- current_gate_id 非空本身不能直接等同于 pending。
- 例外：对 .ai/gates.yaml 本身的写入放行——这是"决策记录豁免"。
- 状态文件损坏时按 config.yaml 的 fail_on_state_error 决定（默认 closed = 阻断）。

退出码：0 = 放行；2 = 阻断（ZCode 对 PreToolUse 的 deny 语义）。
"""

import logging
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 防止 hook 运行产生 __pycache__ 污染（T-0032 事故教训）

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Also add loop-engine project root so loop_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import (  # noqa: E402
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    load_config,
    load_gates_for_context,
    load_state,
    load_tasks_for_context,
    normalize_rel,
    pending_gates,
    project_root,
    read_stdin_json,
    should_fail_closed,
    try_import_hard_constraints,
)

_HardConstraints, _Severity = try_import_hard_constraints()
_HARD_CONSTRAINTS_AVAILABLE = _HardConstraints is not None

EXIT_PASS = 0
EXIT_BLOCK = 2


def _load_gate_data(root):
    """Load full gate data from gates.yaml for lifecycle checks."""
    gates_path = root / ".ai" / "gates.yaml"
    if not gates_path.exists():
        return []
    try:
        import yaml as _yaml
        with open(gates_path, "r", encoding="utf-8") as f:
            data = _yaml.safe_load(f) or {}
        return data.get("gates", []) if isinstance(data.get("gates"), list) else []
    except Exception:
        return []


def _check_gate_lifecycle(root, current_gate_id, state):
    """Check gate lifecycle for current_gate_id.

    Returns:
        "allow" — gate is approved and execution is in progress or not started
        "block_pending" — gate is actually pending (needs user decision)
        "block_rejected" — gate is rejected or blocked
        "block_missing" — gate referenced by state but not in register (fail-closed)
        "block_task_mismatch" — gate belongs to a different task (fail-closed)
        "skip" — gate is approved+completed, not active
        "allow_legacy" — approved with no execution_status (legacy gate)
    """
    gate_id_str = str(current_gate_id)
    gate_list = _load_gate_data(root)

    gate_data = None
    for g in gate_list:
        if isinstance(g, dict) and str(g.get("id")) == gate_id_str:
            gate_data = g
            break

    if gate_data is None:
        return "block_missing"

    status = gate_data.get("status", "")
    exec_status = gate_data.get("execution_status", "")
    gate_task_id = str(gate_data.get("task_id", ""))
    state_task_id = str(state.get("current_task_id", ""))

    # Pending status check — task-scoped (T-0050 fix)
    # Only block writes when the pending gate belongs to the CURRENT task.
    # If a pending gate belongs to a different task, treat it as a legacy gate (allow writes).
    if status == "pending":
        if gate_task_id and state_task_id and gate_task_id != state_task_id:
            return "allow_legacy"
        return "block_pending"

    # Fail-closed: gate belongs to a different task (only for non-pending gates)
    if gate_task_id and state_task_id and gate_task_id != state_task_id:
        return "block_task_mismatch"
    elif status == "approved":
        if exec_status == "completed":
            return "skip"
        elif exec_status in ("approved_not_started", "in_progress"):
            return "allow"
        else:
            # Approved but no execution_status → legacy gate, allow
            return "allow_legacy"
    elif status in ("rejected", "blocked"):
        return "block_rejected"
    else:
        # Unknown status → fail-closed
        return "block_missing"


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return EXIT_PASS

    cfg = load_config(root)
    gate_cfg = cfg.get("gate_guard", DEFAULT_CONFIG["gate_guard"])
    if not gate_cfg.get("enabled", True):
        return EXIT_PASS

    # 决策记录豁免：pending 期间允许写 gates.yaml 本身
    target = extract_target_path(hook_input)
    if target:
        rel = normalize_rel(root, target)
        exempt = [p.replace("\\", "/") for p in gate_cfg.get("decision_recording_exempt", [])]
        if rel and rel in exempt:
            return EXIT_PASS

    try:
        pending = pending_gates(root)
        state = load_state(root)
    except Exception as e:
        policy = gate_cfg.get("fail_on_state_error", "closed")
        if policy == "closed":
            logger.warning(
                "BLOCKED: 无法读取治理状态（%s）。"
                "按 fail-closed 策略阻断写入；请先修复 .ai/state.yaml / .ai/gates.yaml。",
                e,
            )
            return EXIT_BLOCK
        logger.warning("状态不可读（%s），按 fail-open 放行。", e)
        return EXIT_PASS

    # ── Gate lifecycle check (T-0046 fix) ──
    # current_gate_id alone does NOT mean "pending".
    # Must cross-reference gates.yaml to determine actual gate status.
    current_gate_id = state.get("current_gate_id")
    if current_gate_id:
        gate_id_str = str(current_gate_id)
        lifecycle = _check_gate_lifecycle(root, gate_id_str, state)

        if lifecycle == "block_missing":
            logger.warning(
                "BLOCKED: current_gate_id '%s' 在 gates.yaml 中不存在。"
                "治理状态漂移，请先修复 gate register。",
                gate_id_str,
            )
            return EXIT_BLOCK

        elif lifecycle == "block_task_mismatch":
            gate_data = next(
                (g for g in _load_gate_data(root) if str(g.get("id")) == gate_id_str), None
            )
            gate_task = gate_data.get("task_id", "?") if gate_data else "?"
            state_task = state.get("current_task_id", "?")
            logger.warning(
                "BLOCKED: current_gate_id '%s' 属于 task '%s'，但当前 task 是 '%s'。",
                gate_id_str, gate_task, state_task,
            )
            return EXIT_BLOCK

        elif lifecycle == "block_rejected":
            logger.warning(
                "BLOCKED: current_gate_id '%s' 状态为 rejected/blocked。"
                "在用户明确处理之前，禁止写入操作。",
                gate_id_str,
            )
            return EXIT_BLOCK

        elif lifecycle == "block_pending":
            # Actually pending — needs user decision
            if gate_id_str not in pending:
                pending.append(gate_id_str)

        elif lifecycle in ("allow", "allow_legacy"):
            # Approved + in_progress/approved_not_started → allow within scope
            logger.debug(
                "Gate '%s' is approved; allowing execution within scope.",
                gate_id_str,
            )

        elif lifecycle == "skip":
            # Approved + completed → not active execution gate
            logger.debug(
                "Gate '%s' is approved+completed; not treated as active.",
                gate_id_str,
            )

    if pending:
        logger.warning(
            "BLOCKED: 存在等待用户决策的 gate：%s。"
            "在用户明确批准、拒绝或要求修复之前，禁止写入操作。"
            "请向用户展示 gate 内容并等待决策。",
            ", ".join(pending),
        )
        return EXIT_BLOCK

    # ── HardConstraints: C7 Blocker Check ──
    if _HARD_CONSTRAINTS_AVAILABLE:
        try:
            hc = _HardConstraints()
            gates_dict = load_gates_for_context(root)
            tasks_list = load_tasks_for_context(root)

            c7_violations = hc.check_c7_blockers(gates_dict, tasks_list)

            blocker_violations = [
                v for v in c7_violations if v.severity == _Severity.BLOCKER
            ]
            if blocker_violations:
                for v in blocker_violations:
                    logger.warning(
                        "[HardConstraints] C7 BLOCKER: %s", v.message
                    )
                logger.warning(
                    "BLOCKED: HardConstraints C7 检测到 %d 个 BLOCKER 违规",
                    len(blocker_violations),
                )
                return EXIT_BLOCK

            if c7_violations:
                logger.debug(
                    "[HardConstraints] C7 passed with %d warning(s)",
                    len(c7_violations),
                )
        except Exception as e:
            if should_fail_closed(root):
                return EXIT_BLOCK
            logger.warning(
                "[warn] HardConstraints C7 检查异常，fail-open 放行：%s", e
            )

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
