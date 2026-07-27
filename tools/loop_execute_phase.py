"""
loop_execute_phase — 两层模型：会话端 phase 执行器。

ZCode 会话调用此工具获取执行计划，然后按计划调用 Agent 工具。

用法：
    python tools/loop_execute_phase.py S4-implementation --task-id T-0001

输出：JSON 执行计划，包含每个批次的 Agent 调用参数。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.dispatcher import LoopDispatcher
from loop_core.subagent_manifest import SubagentManifest, SubagentSpec
from loop_core.agent_adapter import ZCodeAgentAdapter
from loop_core.state_machine import Phase


def build_plan(phase_id: str, task_id: str, adapter: ZCodeAgentAdapter) -> dict:
    phase = Phase(phase_id)
    manifest = _default_manifest_for_phase(phase, task_id)
    dispatcher = LoopDispatcher()
    plan = dispatcher.prepare(manifest, adapter)

    batches = []
    for batch in plan.batches:
        steps = []
        for step in batch:
            steps.append({
                "step_index": step.step_index,
                "agent_description": step.description,
                "subagent_id": step.spec.subagent_id,
                "role_hint": step.spec.role_hint,
                "prompt_preview": step.spec.prompt[:200],
                "session_id": step.agent_input.session_id,
                "actor_id": step.agent_input.actor_id,
                "timeout_seconds": step.spec.timeout_seconds,
                "max_parallel": step.spec.max_parallel,
                "full_prompt": step.agent_input.prompt,
            })
        batches.append({
            "batch_index": batch[0].batch_index if batch else 0,
            "parallel": batch[0].spec.max_parallel if batch else True,
            "steps": steps,
        })

    return {
        "phase": phase.value,
        "task_id": task_id,
        "manifest_id": manifest.manifest_id,
        "total_steps": plan.total_steps,
        "total_batches": len(batches),
        "aggregation_prompt": plan.aggregation_prompt,
        "batches": batches,
        "instructions": (
            f"Session workflow ({plan.total_steps} agents in {len(batches)} batches):\n"
            + "\n".join(
                f"  Batch {b['batch_index']}: call Agent() for {len(b['steps'])} role(s) "
                f"{'in PARALLEL' if b['parallel'] else 'SERIALLY'}"
                for b in batches
            )
            + f"\n  After all batches: call Agent('main-thread') with aggregation_prompt to present gate."
        ),
    }


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
    parser = argparse.ArgumentParser(description="Loop phase executor (two-layer model)")
    parser.add_argument("phase_id", help="Phase ID (S1-requirements, S4-implementation, etc.)")
    parser.add_argument("--task-id", default="T-0001", help="Task ID")
    args = parser.parse_args()

    adapter = ZCodeAgentAdapter()
    plan = build_plan(args.phase_id, args.task_id, adapter)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
