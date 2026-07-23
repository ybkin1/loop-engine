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

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 防止 hook 运行产生 __pycache__ 污染（T-0032 事故教训）

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (  # noqa: E402
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    load_config,
    load_state,
    normalize_rel,
    pending_gates,
    project_root,
    read_stdin_json,
)

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
            print(
                f"[gate_guard] BLOCKED: 无法读取治理状态（{e}）。"
                "按 fail-closed 策略阻断写入；请先修复 .ai/state.yaml / .ai/gates.yaml。",
                file=sys.stderr,
            )
            return EXIT_BLOCK
        print(f"[gate_guard] WARN: 状态不可读（{e}），按 fail-open 放行。", file=sys.stderr)
        return EXIT_PASS

    current_gate_id = state.get("current_gate_id")
    if current_gate_id and str(current_gate_id) not in pending:
        pending.append(str(current_gate_id))

    if pending:
        print(
            "[gate_guard] BLOCKED: 存在等待用户决策的 gate："
            + ", ".join(pending)
            + "。在用户明确批准、拒绝或要求修复之前，禁止写入操作。"
            "请向用户展示 gate 内容并等待决策。",
            file=sys.stderr,
        )
        return EXIT_BLOCK

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
