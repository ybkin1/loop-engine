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


def _copy_dir(src: Path, dst: Path) -> None:
    """Recursively copy a directory, skipping __pycache__."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name == "__pycache__":
            continue
        target = dst / item.name
        if item.is_dir():
            _copy_dir(item, target)
        else:
            target.write_bytes(item.read_bytes())


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


    # T-0070: Install agent roles if agents/ directory is empty or missing
    agents_dir = root / "agents"
    source_agents = Path(__file__).resolve().parent.parent / "agents"
    if source_agents.exists() and source_agents.is_dir():
        required_roles = ["developer", "independent-reviewer", "test-engineer",
                         "quality-engineer", "security-engineer"]
        agents_dir.mkdir(parents=True, exist_ok=True)
        installed = 0
        for role in required_roles:
            src = source_agents / role
            dst = agents_dir / role
            if src.is_dir() and not dst.exists():
                _copy_dir(src, dst)
                installed += 1
        if installed > 0:
            print(f"[loop-onboard] ✅ Installed {installed} agent roles to agents/")
        missing = [r for r in required_roles if not (agents_dir / r / "SKILL.md").exists()]
        if missing:
            print(f"[loop-onboard] ⚠️ Missing agents: {missing}. Run 'loop_onboard --install-agents' to retry.")
    else:
        print("[loop-onboard] ⚠️ Source agents directory not found. Agents not installed.")

    # T-0078 P1: S0 阶段强制激活质量门禁配置
    # 如果项目没有 quality_gates 配置，从模板复制
    skill_config = root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
    if not skill_config.exists():
        # 从 loop-engine 自身复制模板
        template_config = Path(__file__).resolve().parent.parent / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        if template_config.exists():
            import shutil
            skill_config.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(template_config, skill_config)
            print("[loop-governance] [onboard] Quality gate config template copied from loop-engine")
    
    # 确保 .ai/checks/ 目录存在（语义规则目录）
    checks_dir = root / ".ai" / "checks"
    checks_dir.mkdir(parents=True, exist_ok=True)

    print(f"[loop-onboard] ✅ {root.name} 已接入 Loop 工程")
    print(f"[loop-onboard]    loop_mode: FULL")
    print(f"[loop-onboard]    state:     NO_ACTIVE_TASK")
    print(f"[loop-onboard]    下次打开项目时治理自动生效")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    onboard(target)

def update(root: str | Path) -> None:
    """Update Loop engineering in an existing project (sync agents + config)."""
    root = Path(root).resolve()
    if not (root / ".ai/state.yaml").exists():
        print("[loop-update] ⚠️ Project not onboarded. Run loop_onboard first.")
        return
    
    # Re-install agents (overwrite existing)
    source_agents = Path(__file__).resolve().parent.parent / "agents"
    agents_dir = root / "agents"
    required_roles = ["developer", "independent-reviewer", "test-engineer",
                     "quality-engineer", "security-engineer"]
    agents_dir.mkdir(parents=True, exist_ok=True)
    updated = 0
    for role in required_roles:
        src = source_agents / role
        dst = agents_dir / role
        if src.is_dir():
            if dst.exists():
                import shutil
                shutil.rmtree(str(dst))
            _copy_dir(src, dst)
            updated += 1
    
    print(f"[loop-update] ✅ Updated {updated} agent roles")
    print(f"[loop-update] ✅ Agents synced from source")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("project_root", nargs="?", default=".")
    p.add_argument("--update", action="store_true")
    args = p.parse_args()
    if args.update:
        update(args.project_root)
    else:
        onboard(args.project_root)
