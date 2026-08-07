"""T-0135: CLI 入口薄封装（pyproject [project.scripts] 文档化入口）。

审计发现：工具仅项目内直接调用（python .zcode/tools/xxx.py .），pyproject
无 console scripts 入口，可发现性弱。本模块提供薄封装——定位项目根后
subprocess 调用既有工具，不复制任何判定逻辑（单一事实源不变）。

入口（pyproject [project.scripts]）：
- loop-validate   → validate_state（--auto-sync 可选）
- loop-check      → release.py check（发布质量门）
- loop-heartbeat  → rounds_heartbeat（自治心跳）
- loop-delegation → gov_delegation（委托链）
- loop-conclusion → conclusion_packet（结论包）
- loop-mutation   → mutation_tester scan（M1 变异检出）

调用模式：
1. console scripts（pip 安装后）：`loop-validate .` —— sys.argv[1:] 为用户参数
2. 脚本直调：`python loop_engine/cli_entries.py loop-validate .`
   —— _dispatch 剥离入口名后调用对应 main
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# 项目根：向上查找含 .zcode/tools 的目录（T-0143 2.1: 本文件已迁入
# src/loop_engine/ 以进入 wheel 分发集，不能再用固定 parent.parent）
def _find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".zcode" / "tools").is_dir():
            return p
    return start.parent.parent  # 兜底：找不到则退回旧语义


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
TOOLS = PROJECT_ROOT / ".zcode" / "tools"
SCRIPTS = PROJECT_ROOT / "scripts"


def _run(script: Path, args: list[str], inject_root: bool = True) -> int:
    """调用项目内工具。

    inject_root=True：工具首参为项目根（validate_state/rounds_heartbeat/
    gov_delegation/conclusion_packet）。
    inject_root=False：工具无 root 位置参数（release.py check / mutation_tester
    子命令），仅设置 cwd。
    """
    cmd = [sys.executable, str(script)]
    if inject_root:
        cmd.append(str(PROJECT_ROOT))
    cmd.extend(args)
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return proc.returncode


def main_validate(args: list[str] | None = None) -> int:
    """loop-validate: 状态校验（--auto-sync 一步同步可选）。"""
    args = sys.argv[1:] if args is None else args
    return _run(TOOLS / "validate_state.py", args)


def main_check(args: list[str] | None = None) -> int:
    """loop-check: release 质量门前置（7 步；无 root 位置参数）。"""
    args = sys.argv[1:] if args is None else args
    return _run(SCRIPTS / "release.py", ["check", *args], inject_root=False)


def main_heartbeat(args: list[str] | None = None) -> int:
    """loop-heartbeat: 自治心跳（rounds 悬空检测）。"""
    args = sys.argv[1:] if args is None else args
    return _run(TOOLS / "rounds_heartbeat.py", args)


def main_delegation(args: list[str] | None = None) -> int:
    """loop-delegation: 委托链管理（register/revoke/status/check）。"""
    args = sys.argv[1:] if args is None else args
    return _run(TOOLS / "gov_delegation.py", args)


def main_conclusion(args: list[str] | None = None) -> int:
    """loop-conclusion: 结论包生成。"""
    args = sys.argv[1:] if args is None else args
    return _run(TOOLS / "conclusion_packet.py", args)


def main_mutation(args: list[str] | None = None) -> int:
    """loop-mutation: M1 变异检出（scan 子命令；无 root 位置参数）。"""
    args = sys.argv[1:] if args is None else args
    return _run(SCRIPTS / "mutation_tester.py", args, inject_root=False)


ENTRY_POINTS = {
    "loop-validate": main_validate,
    "loop-check": main_check,
    "loop-heartbeat": main_heartbeat,
    "loop-delegation": main_delegation,
    "loop-conclusion": main_conclusion,
    "loop-mutation": main_mutation,
}


def _dispatch() -> int:
    """脚本直调分发：python loop_engine/cli_entries.py <entry> [args...]。

    剥离入口名（不传给工具），剩余参数透传。
    """
    if len(sys.argv) < 2:
        print(f"usage: python cli_entries.py <{'|'.join(ENTRY_POINTS)}> [args...]",
              file=sys.stderr)
        return 2
    name = sys.argv[1]
    fn = ENTRY_POINTS.get(name)
    if fn is None:
        print(f"unknown entry: {name}; available: {', '.join(ENTRY_POINTS)}",
              file=sys.stderr)
        return 2
    return fn(sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(_dispatch())
