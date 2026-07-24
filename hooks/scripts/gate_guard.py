#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gate_guard.py — ZCode PreToolUse hook：pending gate 存在时阻断写入操作。

语义（与 .ai 治理契约一致）：
- 非治理项目（无 .ai/state.yaml）→ 一律放行（exit 0）。
- 存在 status == "pending" 的 gate，或 state.yaml 的 current_gate_id 非空
  → 阻断（exit 2），stderr 输出需要用户决策的 gate 列表。
- 例外：对 .ai/gates.yaml 本身的写入放行——这是"决策记录豁免"：
  注册 pending gate 和记录用户决策都必须能写 gates.yaml，
  否则用户批准之后 AI 反而无法落盘，形成死锁（见 references/decision-rules.md）。
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

    current_gate_id = state.get("current_gate_id")
    if current_gate_id and str(current_gate_id) not in pending:
        pending.append(str(current_gate_id))

    if pending:
        logger.warning(
            "BLOCKED: 存在等待用户决策的 gate：%s。"
            "在用户明确批准、拒绝或要求修复之前，禁止写入操作。"
            "请向用户展示 gate 内容并等待决策。",
            ", ".join(pending),
        )
        return EXIT_BLOCK

    # ── HardConstraints: C7 Blocker Check ──
    # 委托给 HardConstraints.check_c7_blockers() 检测 blocked gates/tasks。
    # HardConstraints 不可用时（ImportError），静默跳过（不阻断已有逻辑）。
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
            # C7 检查异常：按 hooks.fail_closed_on_error 配置决定阻断或放行
            if should_fail_closed(root):
                return EXIT_BLOCK
            logger.warning(
                "[warn] HardConstraints C7 检查异常，fail-open 放行：%s", e
            )
            # 不阻断 —— 回退到已有的 pending gate 检查结果

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
