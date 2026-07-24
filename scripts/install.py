#!/usr/bin/env python3
"""
Loop Engine 安装器 — 在新项目中建立 Loop 治理上下文。

用法：python scripts/install.py <target_project_root>

操作：
1. 验证目标目录存在
2. 创建 .ai/ 目录结构
3. 写入初始 state.yaml（phase=S0-init, loop_mode=FULL）
4. 写入初始 task_graph.yaml（空任务列表）
5. 写入初始 gates.yaml（空 gate 列表）
6. 写入初始 HANDOFF.md（模板）
7. 创建 .ai/tasks/ 和 .ai/evidence/ 目录
8. 复制 .zcode/ 配置模板（如果目标项目中不存在）
9. 输出安装摘要和下一步说明
10. 返回 0（成功）或非 0（失败）
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup: allow imports from .zcode/tools/ in the source project ──
_SOURCE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOURCE_ROOT / ".zcode" / "tools"))

from governor_lib import transactional_write_texts, load_yaml, dump_yaml  # noqa: E402


# ── Templates ───────────────────────────────────────────────────────────

STATE_TEMPLATE = """schema_version: 1
project_name: {project_name}
current_phase: S0-init
current_task_id: null
current_gate_id: null
loop_mode: FULL
last_handoff_at: {last_handoff_at}
notes:
  - Loop 工程治理已安装。
  - 请创建第一个任务: .ai/tasks/T-0001.md
"""

TASK_GRAPH_TEMPLATE = """schema_version: 1
tasks: []
edges: []
"""

GATES_TEMPLATE = """schema_version: 1
gates: []
"""

HANDOFF_TEMPLATE = """# Handoff

## Current Phase
S0-init

## Current Task
无

## Current Status
Loop governance context installed. No pending gates.

## Next Session First Step
Create the first task under .ai/tasks/
"""

PROJECT_TEMPLATE = """# Project

{project_name}

## Goal

<用户目标一句话>
"""

NON_GOALS_TEMPLATE = """# Non-Goals

<!-- 列出明确不在本项目范围内的内容 -->
- 尚未定义
"""

ARCHITECTURE_TEMPLATE = """# Architecture

<!-- 项目架构概览 -->
待 S2-architecture 阶段填写。
"""

CONTRACTS_TEMPLATE = """# Contracts

<!-- 角色合同与职责划分 -->
待 S1-requirements 阶段填写。
"""

CODING_STANDARDS_TEMPLATE = """# Coding Standards

<!-- 编码规范 -->
待 S4-implementation 阶段填写。
"""

CONVENTIONS_TEMPLATE = """# Conventions

<!-- 项目约定 -->
待 S4-implementation 阶段填写。
"""

CODEMAP_TEMPLATE = """# Code Map

<!-- 代码地图 -->
待 S4-implementation 阶段填写。
"""

PROGRESS_TEMPLATE = """# Progress

## S0-init

- [x] Loop 治理上下文已安装
- [ ] 创建第一个任务

## 任务进度

暂无。
"""

QUALITY_GATES_TEMPLATE = """# Quality Gates

<!-- 质量门禁定义 -->
待 S5-quality 阶段填写。
"""

ACCEPTANCE_TEMPLATE = """# Acceptance

<!-- 验收标准 -->
待 S1-requirements 阶段填写。
"""

DECISIONS_TEMPLATE = """# Decisions

<!-- 关键决策记录 -->
待首次决策后填写。
"""

KNOWN_ISSUES_TEMPLATE = """# Known Issues

<!-- 已知问题列表 -->
暂无。
"""


# ── All files needed for a valid governance context (matching REQUIRED_FILES in governor_lib) ──

_REQUIRED_FILES = [
    "PROJECT.md",
    "NON_GOALS.md",
    "ARCHITECTURE.md",
    "CONTRACTS.md",
    "CODING_STANDARDS.md",
    "CONVENTIONS.md",
    "CODEMAP.md",
    "PROGRESS.md",
    "QUALITY_GATES.md",
    "ACCEPTANCE.md",
    "DECISIONS.md",
    "KNOWN_ISSUES.md",
    "state.yaml",
    "task_graph.yaml",
    "gates.yaml",
    "HANDOFF.md",
]

_REQUIRED_DIRS = [
    "tasks",
    "evidence",
]


# ── Public API ──────────────────────────────────────────────────────────

def install(target_root: Path, *, interactive: bool = True) -> int:
    """在新项目中安装 Loop 治理上下文。

    Args:
        target_root: 目标项目根目录的 Path 对象。
        interactive: 如果为 True，遇到已存在的 .ai/ 时会提示用户确认。

    Returns:
        0 表示成功，非 0 表示失败。
    """
    target_root = target_root.resolve()
    ai_dir = target_root / ".ai"

    # 1. 验证目标目录存在
    if not target_root.is_dir():
        print(f"[install] 错误：目标目录不存在: {target_root}")
        return 1

    # 2. 检查是否已安装
    if ai_dir.exists():
        if interactive:
            print(f"[install] 警告：{target_root} 中已存在 .ai/ 目录。")
            try:
                response = input("[install] 是否覆盖？将跳过已存在的文件。(y/N): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n[install] 已取消。")
                return 1
            if response not in ("y", "yes"):
                print("[install] 已取消。")
                return 0
        else:
            print(f"[install] 警告：{target_root} 中已存在 .ai/ 目录，将跳过已存在的文件。")

    project_name = target_root.name
    now_iso = datetime.now(timezone.utc).isoformat()

    # 3. 准备写入内容（跳过已存在的文件）
    changes: dict[Path, str] = {}
    skipped: list[str] = []

    file_contents = [
        (ai_dir / "PROJECT.md", PROJECT_TEMPLATE.format(project_name=project_name)),
        (ai_dir / "NON_GOALS.md", NON_GOALS_TEMPLATE),
        (ai_dir / "ARCHITECTURE.md", ARCHITECTURE_TEMPLATE),
        (ai_dir / "CONTRACTS.md", CONTRACTS_TEMPLATE),
        (ai_dir / "CODING_STANDARDS.md", CODING_STANDARDS_TEMPLATE),
        (ai_dir / "CONVENTIONS.md", CONVENTIONS_TEMPLATE),
        (ai_dir / "CODEMAP.md", CODEMAP_TEMPLATE),
        (ai_dir / "PROGRESS.md", PROGRESS_TEMPLATE),
        (ai_dir / "QUALITY_GATES.md", QUALITY_GATES_TEMPLATE),
        (ai_dir / "ACCEPTANCE.md", ACCEPTANCE_TEMPLATE),
        (ai_dir / "DECISIONS.md", DECISIONS_TEMPLATE),
        (ai_dir / "KNOWN_ISSUES.md", KNOWN_ISSUES_TEMPLATE),
        (ai_dir / "state.yaml", STATE_TEMPLATE.format(
            project_name=project_name, last_handoff_at=now_iso)),
        (ai_dir / "task_graph.yaml", TASK_GRAPH_TEMPLATE),
        (ai_dir / "gates.yaml", GATES_TEMPLATE),
        (ai_dir / "HANDOFF.md", HANDOFF_TEMPLATE),
    ]

    for path, content in file_contents:
        if path.exists():
            skipped.append(str(path.relative_to(target_root)))
        else:
            changes[path] = content

    # 4. 创建目录
    for dir_name in _REQUIRED_DIRS:
        dir_path = ai_dir / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"[install] 已创建: {dir_path.relative_to(target_root)}")
        else:
            print(f"[install] 已存在: {dir_path.relative_to(target_root)}")

    # 5. 原子写入文件
    if changes:
        try:
            transactional_write_texts(ai_dir, changes)
        except Exception as exc:
            print(f"[install] 错误：写入失败: {exc}")
            return 1
        for path in changes:
            print(f"[install] 已创建: {path.relative_to(target_root)}")

    for rel in skipped:
        print(f"[install] 跳过（已存在）: {rel}")

    # 6. 复制 .zcode/ 工具模板
    _copy_zcode_tools(target_root)

    # 7. 输出摘要
    print(f"\n[install] Loop 治理上下文已在 {target_root} 安装完成。")
    print("[install] 下一步：")
    print("[install]   1. 创建第一个任务: .ai/tasks/T-0001.md")
    print("[install]   2. 在 ZCode 会话中重载项目以启用治理规则")
    print("[install]   3. 运行 validate_state.py 确认状态一致性")

    return 0


def verify_installation(target_root: Path) -> bool:
    """验证安装完整性——所有必要文件存在且格式正确。

    Args:
        target_root: 目标项目根目录。

    Returns:
        True 如果安装完整且有效。
    """
    target_root = target_root.resolve()
    ai_dir = target_root / ".ai"

    if not ai_dir.exists():
        print(f"[verify] 失败: .ai/ 目录不存在: {ai_dir}")
        return False

    errors: list[str] = []

    # 检查必要文件
    for fname in _REQUIRED_FILES:
        fpath = ai_dir / fname
        if not fpath.exists():
            errors.append(f"缺少文件: .ai/{fname}")

    # 检查必要目录
    for dname in _REQUIRED_DIRS:
        dpath = ai_dir / dname
        if not dpath.is_dir():
            errors.append(f"缺少目录: .ai/{dname}")

    # 检查 state.yaml 内容
    state_path = ai_dir / "state.yaml"
    if state_path.exists():
        try:
            state = load_yaml(state_path)
        except Exception as exc:
            errors.append(f"state.yaml 解析失败: {exc}")
        else:
            if not isinstance(state, dict):
                errors.append("state.yaml 不是有效的映射")
            else:
                if not state.get("current_phase"):
                    errors.append("state.yaml 缺少 current_phase")
                if not state.get("project_name"):
                    errors.append("state.yaml 缺少 project_name")

    # 检查 gates.yaml 内容
    gates_path = ai_dir / "gates.yaml"
    if gates_path.exists():
        try:
            gate_data = load_yaml(gates_path)
        except Exception as exc:
            errors.append(f"gates.yaml 解析失败: {exc}")
        else:
            if not isinstance(gate_data, dict) or "gates" not in gate_data:
                errors.append("gates.yaml 格式无效：缺少 'gates' 键")

    # 检查 task_graph.yaml 内容
    tg_path = ai_dir / "task_graph.yaml"
    if tg_path.exists():
        try:
            tg_data = load_yaml(tg_path)
        except Exception as exc:
            errors.append(f"task_graph.yaml 解析失败: {exc}")
        else:
            if not isinstance(tg_data, dict) or "tasks" not in tg_data:
                errors.append("task_graph.yaml 格式无效：缺少 'tasks' 键")

    if errors:
        for err in errors:
            print(f"[verify] {err}")
        return False

    print(f"[verify] 安装验证通过: {ai_dir}")
    return True


# ── Internal helpers ────────────────────────────────────────────────────

def _copy_zcode_tools(target_root: Path) -> None:
    """复制 .zcode/tools/ 到目标项目（如不存在）。"""
    src_tools = _SOURCE_ROOT / ".zcode" / "tools"
    if not src_tools.is_dir():
        print("[install] 注意: 源项目 .zcode/tools/ 不存在，跳过工具复制。")
        return

    dst_tools = target_root / ".zcode" / "tools"
    if dst_tools.exists():
        print("[install] 跳过: .zcode/tools/ 已存在")
        return

    dst_tools.mkdir(parents=True, exist_ok=True)
    copied = 0
    for fpath in src_tools.iterdir():
        if fpath.suffix == ".py" and fpath.is_file():
            shutil.copy2(fpath, dst_tools / fpath.name)
            copied += 1
    if copied:
        print(f"[install] 已复制 {copied} 个工具脚本到 .zcode/tools/")
    else:
        print("[install] 注意: 未找到可复制的 .py 工具文件。")


# ── CLI entry point ─────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Loop Engine 安装器 — 在新项目中建立 Loop 治理上下文"
    )
    parser.add_argument(
        "target_root",
        help="目标项目根目录",
    )
    parser.add_argument(
        "--non-interactive", "-n",
        action="store_true",
        help="非交互模式（不提示确认）",
    )
    args = parser.parse_args()

    target = Path(args.target_root)
    return install(target, interactive=not args.non_interactive)


if __name__ == "__main__":
    raise SystemExit(main())
