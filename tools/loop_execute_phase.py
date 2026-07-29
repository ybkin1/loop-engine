"""
loop_execute_phase — 两层模型：自动化 phase 执行器。

ZCode 会话调用此工具获取完整执行脚本，按脚本自动完成整个阶段。

用法：
    python tools/loop_execute_phase.py S4-implementation --task-id T-0001

输出：完整 JSON 执行脚本，包括每步的 Agent 调用参数、重试策略、角色隔离验证。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.dispatcher import LoopDispatcher
from loop_core.subagent_manifest import SubagentManifest, SubagentSpec
from loop_core.state_machine import Phase
from hooks.zcode_adapter import ZCodeAgentAdapter


def build_script(phase_id: str, task_id: str, adapter: ZCodeAgentAdapter) -> dict:
    """Build a complete execution script for a phase.

    The output is a step-by-step script that the session follows:
    1. For each batch: call Agent() for each step (parallel if max_parallel)
    2. If a step fails: retry with failure feedback, up to max_retries
    3. After all batches: call Agent('main-thread') to aggregate and present gate
    """
    phase = Phase(phase_id)
    manifest = _default_manifest_for_phase(phase, task_id)
    dispatcher = LoopDispatcher()
    return dispatcher.build_execution_script(manifest, adapter)


def _default_manifest_for_phase(phase: Phase, task_id: str) -> SubagentManifest:
    defaults = {
        Phase.S1_REQUIREMENTS: [
            SubagentSpec("product-manager", "general-purpose",
                         f"执行 S1 需求分析。任务 {task_id}。读取项目上下文，产出需求文档。"),
            SubagentSpec("project-manager", "general-purpose",
                         f"执行 S1 项目管理。任务 {task_id}。产出阶段计划和风险清单。"),
        ],
        Phase.S2_ARCHITECTURE: [
            SubagentSpec("system-architect", "general-purpose",
                         f"执行 S2 架构设计。任务 {task_id}。产出系统架构文档。"),
        ],
        Phase.S3_INTERFACE: [
            SubagentSpec("module-architect", "general-purpose",
                         f"执行 S3 接口设计。任务 {task_id}。产出接口契约。"),
        ],
        Phase.S4_IMPLEMENTATION: [
            SubagentSpec(f"developer:{task_id}", "general-purpose",
                         f"执行 S4 代码实现。任务 {task_id}。按架构和接口契约编写代码。",
                         max_parallel=True),
            SubagentSpec(f"quality-engineer:{task_id}", "general-purpose",
                         f"执行 S4 质量检查。任务 {task_id}。运行测试和门禁。",
                         max_parallel=False),
            SubagentSpec(f"independent-reviewer:{task_id}", "general-purpose",
                         f"执行 S4 独立评审。任务 {task_id}。审查代码质量、架构一致性。",
                         max_parallel=False),
        ],
        Phase.S5_QUALITY: [
            SubagentSpec("quality-engineer", "general-purpose",
                         f"执行 S5 质量门禁。任务 {task_id}。运行全部门禁。"),
            SubagentSpec("security-engineer", "general-purpose",
                         f"执行 S5 安全审查。任务 {task_id}。运行安全扫描。"),
        ],
        Phase.S6_DELIVERY: [
            SubagentSpec("delivery-manager", "general-purpose",
                         f"执行 S6 交付准备。任务 {task_id}。产出交付物清单和部署方案。"),
        ],
    }

    subs = defaults.get(phase, [
        SubagentSpec(f"{phase.value}:default", "general-purpose",
                     f"执行 {phase.value}。任务 {task_id}。"),
    ])

    return SubagentManifest(
        manifest_id=f"MANIFEST-{phase.value}-{task_id}",
        parent_role_id="main-thread",
        parent_task_id=task_id,
        phase=phase.value,
        subagents=subs,
        aggregation_prompt=(
            f"汇总 {phase.value} 阶段所有角色产出。"
            f"逐项对照验证标准检查。生成 gate 呈现包。"
        ),
        input_fingerprint="DEFAULT_PLAN",
        max_parallel_subagents=3,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Loop phase executor (two-layer, auto-retry)")
    parser.add_argument("phase_id", help="Phase ID (S1-requirements, S4-implementation, etc.)")
    parser.add_argument("--task-id", default="T-0001", help="Task ID")
    parser.add_argument("--main-thread-first", action="store_true",
                        help="Call main-thread Agent first to generate custom manifest")
    args = parser.parse_args()

    adapter = ZCodeAgentAdapter()
    script = build_script(args.phase_id, args.task_id, adapter)
    print(json.dumps(script, ensure_ascii=False, indent=2))
