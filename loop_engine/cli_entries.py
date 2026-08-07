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
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# 项目根：本文件位于 <root>/loop_engine/ 下
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS = PROJECT_ROOT / ".zcode" / "tools"
SCRIPTS = PROJECT_ROOT / "scripts"


def _run(script: Path, args: list[str], auto_root: bool = True) -> int:
    """调用项目内工具（默认追加项目根位置参数）。"""
    cmd = [sys.executable, str(script)]
    if auto_root:
        cmd.append(str(PROJECT_ROOT))
    cmd.extend(args)
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return proc.returncode


def main_validate() -> int:
    """loop-validate: 状态校验（--auto-sync 一步同步可选）。"""
    args = [a for a in sys.argv[1:] if a != "validate"]
    return _run(TOOLS / "validate_state.py", args)


def main_check() -> int:
    """loop-check: release 质量门前置（7 步）。"""
    args = [a for a in sys.argv[1:] if a != "check"]
    return _run(SCRIPTS / "release.py", ["check", *args])


def main_heartbeat() -> int:
    """loop-heartbeat: 自治心跳（rounds 悬空检测）。"""
    args = [a for a in sys.argv[1:] if a != "heartbeat"]
    return _run(TOOLS / "rounds_heartbeat.py", args)


def main_delegation() -> int:
    """loop-delegation: 委托链管理（register/revoke/status/check）。"""
    args = [a for a in sys.argv[1:] if a != "delegation"]
    return _run(TOOLS / "gov_delegation.py", args)


def main_conclusion() -> int:
    """loop-conclusion: 结论包生成。"""
    args = [a for a in sys.argv[1:] if a != "conclusion"]
    return _run(TOOLS / "conclusion_packet.py", args)


def main_mutation() -> int:
    """loop-mutation: M1 变异检出（scan 子命令）。"""
    args = [a for a in sys.argv[1:] if a != "mutation"]
    return _run(SCRIPTS / "mutation_tester.py", args)


ENTRY_POINTS = {
    "loop-validate": main_validate,
    "loop-check": main_check,
    "loop-heartbeat": main_heartbeat,
    "loop-delegation": main_delegation,
    "loop-conclusion": main_conclusion,
    "loop-mutation": main_mutation,
}


def _dispatch() -> int:
    """脚本直调分发：python loop_engine/cli_entries.py <entry> [args...]。"""
    name = sys.argv[1] if len(sys.argv) > 1 else "loop-validate"
    fn = ENTRY_POINTS.get(name)
    if fn is None:
        print(f"unknown entry: {name}; available: {', '.join(ENTRY_POINTS)}",
              file=sys.stderr)
        return 2
    return fn()


if __name__ == "__main__":
    raise SystemExit(_dispatch())
