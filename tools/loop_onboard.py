#!/usr/bin/env python3
"""
loop_onboard.py — 一条命令完成 Loop 工程接入。

用法：
    python tools/loop_onboard.py [项目目录]

效果：
    1. 创建 .ai/state.yaml (loop_mode=FULL)
    2. 创建 .ai/gates.yaml, .ai/task_graph.yaml, .ai/HANDOFF.md
    3. 创建 AGENTS.md（如果不存在）
    4. 初始化 runtime controller
    5. 运行 validate_state.py 确认

接入后，下次打开项目时 Loop 治理自动生效。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def onboard(root: str | Path) -> None:
    """One-shot project onboarding."""
    root = Path(root).resolve()

    from loop_core.runtime_controller import RuntimeController
    controller = RuntimeController(root)
    controller.onboard_project("start Loop")

    # AGENTS.md — only create if absent (protected file)
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        agents_md.write_text("""\
## Loop Governance

For implementation, review, debugging, design, handoff, task state changes,
or governance work in this project, invoke the `loop-governance` skill before proceeding.

Required startup steps:
1. Read the latest user request first.
2. Confirm the project root.
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, the current task file,
   `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Run `python .zcode/tools/validate_state.py`.
5. If a pending gate exists, stop and ask the user to approve or reject it.
6. Continue only inside the approved task and gate scope.

## Boundaries

- Do not install or enable skill, MCP, agent, automation, or protocol behavior
  without a separate explicit user gate.
- Do not enter real business projects without a separate explicit user gate.
- Do not deploy, roll back, change databases, change permissions, handle secrets,
  perform payment actions, touch production data, or run migrations without a
  separate explicit user gate.
- Treat reviewer PASS, validator success, tests, and AI recommendations as
  evidence only, not user approval.
""", encoding="utf-8")

    print(f"[loop-onboard] ✅ {root.name} 已接入 Loop 工程")
    print(f"[loop-onboard]    loop_mode: FULL")
    print(f"[loop-onboard]    state:     NO_ACTIVE_TASK")
    print(f"[loop-onboard]    下次打开项目时治理自动生效")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    onboard(target)
