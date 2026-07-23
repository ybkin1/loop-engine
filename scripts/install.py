#!/usr/bin/env python3
"""
install.py — Loop 工程插件项目适配脚本。

将插件配置写入目标项目的 .zcode/ 和 .ai/ 目录，
使项目启用 Loop 工程治理。

用法：
    python install.py --project-root <目标项目根目录>
"""

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATES = {
    ".ai/state.yaml": """schema_version: 1
project_name: {project_name}
current_phase: S0-init
current_task_id: null
current_gate_id: null
notes:
  - Loop 工程治理已启用。
  - 请创建第一个任务：.ai/tasks/T-0001.md
""",
    ".ai/gates.yaml": "schema_version: 1\ngates: []\n",
    ".ai/task_graph.yaml": "tasks: []\nedges: []\n",
    ".ai/HANDOFF.md": """# Handoff

## Current Phase
S0-init

## Current Task
无

## Current Status
Loop governance runtime installed. No pending gates.

## Next Session First Step
Create the first task under .ai/tasks/
""",
    ".ai/PROJECT.md": "# Project\n\n{project_name}\n\n## Goal\n\n<用户目标一句话>\n",
}


def main():
    parser = argparse.ArgumentParser(description="Loop 工程插件——项目适配安装")
    parser.add_argument("--project-root", required=True, help="目标项目根目录")
    parser.add_argument("--project-name", default=None, help="项目名称（默认使用目录名）")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    project_name = args.project_name or project_root.name

    if not project_root.is_dir():
        print(f"[install] 项目目录不存在: {project_root}")
        sys.exit(1)

    # 1. 创建 .ai/ 模板目录
    for rel_path, content in TEMPLATES.items():
        target = project_root / rel_path
        if target.exists():
            print(f"[install] 跳过（已存在）: {rel_path}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.format(project_name=project_name), encoding="utf-8")
        print(f"[install] 已创建: {rel_path}")

    # 2. 创建 .ai/tasks/ 和 .ai/evidence/ 目录
    (project_root / ".ai" / "tasks").mkdir(parents=True, exist_ok=True)
    (project_root / ".ai" / "evidence").mkdir(parents=True, exist_ok=True)
    print("[install] 已创建: .ai/tasks/ .ai/evidence/")

    # 3. 复制 plugin config 到项目 .zcode/
    plugin_root = Path(__file__).resolve().parent.parent
    project_zcode = project_root / ".zcode" / "skills" / "loop-governance"
    project_zcode.mkdir(parents=True, exist_ok=True)

    config_src = plugin_root / "skills" / "loop-governance" / "config.yaml"
    chain_src = plugin_root / "skills" / "loop-governance" / "chain.yaml"
    if config_src.exists():
        shutil.copy2(config_src, project_zcode / "config.yaml")
        print("[install] 已复制: config.yaml → .zcode/skills/loop-governance/")
    if chain_src.exists():
        shutil.copy2(chain_src, project_zcode / "chain.yaml")
        print("[install] 已复制: chain.yaml → .zcode/skills/loop-governance/")

    # 4. 复制 validate_state.py 到项目工具目录
    # 优先从项目自身的 .zcode/tools/ 复制；否则从 archive 复制
    tools_src = plugin_root / ".zcode" / "tools"
    if not tools_src.exists():
        tools_src = plugin_root / "archive" / "lab-candidates" / "scripts"
    if tools_src.exists():
        project_tools = project_root / ".zcode" / "tools"
        project_tools.mkdir(parents=True, exist_ok=True)
        for fname in ["validate_state.py", "audit_handoff.py", "governor_lib.py",
                       "continuity_auditor.py", "continuity_producer.py"]:
            src = tools_src / fname
            if src.exists():
                shutil.copy2(src, project_tools / fname)
                print(f"[install] 已复制: {fname} → .zcode/tools/")

    print(f"\n[install] ✅ Loop 工程治理已在 {project_root} 启用。")
    print("[install] 下一步：在新 ZCode 会话中重载，或确保插件已启用。")
    print("[install] 创建第一个任务：.ai/tasks/T-0001.md")


if __name__ == "__main__":
    main()
