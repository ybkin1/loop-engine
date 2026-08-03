"""loop_enforcement_constants.py — loop_enforcement 共享常量表（T-0110 批 A，M 清单 hook 部分）。

落点依据：T-0106 design-common-weakness.md §2.2 —— hook 共享 EXIT_PASS/BLOCK
统一值（M-1）、timeout 族（M-3/4）、治理路径白名单。

本文件值与 hooks/scripts/loop_enforcement.py 现值逐字一致（纯外提供源）。
批 A 只新建本文件、不触碰任何 hook 文件；接线（loop_enforcement.py 与
gate_guard/path_guard/content_guard 改引本表）在批 C 执行。接线前本表与
各 hook 文件内定义并存，属预期（显式豁免），接线后本表为唯一来源。

本文件零依赖（纯常量表，可被任意 hook 脚本独立 import）。
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════
# hook 裁决返回码（M-1：EXIT_PASS=0/EXIT_BLOCK=2 多文件重复定义，
# loop_enforcement.py:172-173 现值；gate_guard.py/path_guard.py/
# content_guard.py 各自定义同值 —— 批 C 统一接线）
# ══════════════════════════════════════════════════════════════════════
EXIT_PASS = 0
EXIT_BLOCK = 2

# ══════════════════════════════════════════════════════════════════════
# 自愈重执行上限（loop_enforcement.py:80 _REEXEC_MAX 现值 = 1）
# ══════════════════════════════════════════════════════════════════════
REEXEC_MAX = 1

# ══════════════════════════════════════════════════════════════════════
# timeout 族（M-3：timeout=30 六文件七处同值；M-4：timeout=20 两处）
# ══════════════════════════════════════════════════════════════════════
COMMAND_TIMEOUT_SECONDS = 30   # M-3 工具/命令超时族：loop_enforcement.py:686
                               # （git diff --name-only HEAD）、content_guard.py:71,76、
                               # rollback.py:207、tool_evidence_chain.py:21,41、
                               # tool_cost_tracker.py:20、upgrade.py:251
GUARD_HEALTH_PROBE_TIMEOUT_SECONDS = 20  # M-4 guard 健康探测超时（loop_core/guard_health.py:247,258
                                         # —— 治理内核零触碰，保持原字面量，本表为共享登记）

# ══════════════════════════════════════════════════════════════════════
# 阈值族 / 默认值（loop_enforcement.py 现值）
# ══════════════════════════════════════════════════════════════════════
MAX_DIFF_FILES = 15            # check_diff_scope max_diff_files 默认值（:656，阻断信息列出上限）
DEFAULT_MAX_FILES = 10         # quality gate evidence max_files 默认值（:1130）

# ══════════════════════════════════════════════════════════════════════
# 治理路径白名单（loop_enforcement.py 现值逐字拷贝；批 C 接线后唯一来源）
# ══════════════════════════════════════════════════════════════════════

# Governance files that are always writable (same exemption as gate_guard)
GOVERNANCE_EXEMPT = [
    ".ai/gates.yaml",
    ".ai/state.yaml",
    ".ai/task_graph.yaml",
    ".ai/HANDOFF.md",
    ".ai/PROGRESS.md",
    ".ai/project_continuity.yaml",
    ".zcode/config.json",
]

# Governance metadata paths: always readable even without active task.
# Business files and project-level exploration without a task are blocked.
MINIMAL_METADATA_READ = [
    ".ai/state.yaml",
    ".ai/gates.yaml",
    ".ai/task_graph.yaml",
    ".ai/HANDOFF.md",
    ".ai/PROGRESS.md",
    ".ai/project_continuity.yaml",
    ".ai/transaction_registry.yaml",
    ".ai/tasks/",
    ".ai/evidence/",
    ".ai/schemas/",
    ".ai/certifications/",
    ".ai/runtime/",
    ".ai/checkers/",
    ".ai/guards/",
    "AGENTS.md",
    ".zcode/config.json",
    ".zcode/tools/",
    ".zcode/skills/",
    "loop_core/",
    "hooks/",
    "tools/",
    "agents/",
    "tests/",
]

# Files that the main-thread can always write (evidence, handoff)
MAIN_THREAD_ALLOWED = [
    ".ai/evidence/",
    ".ai/tasks/",
    ".ai/certifications/",
]

# 治理工具目录（逐段校验白名单：治理工具调用 / 项目根内 cd /
# 无写语义的只读显示段之外的任何段 → 整体不豁免，fail-closed 不变）
GOVERNANCE_TOOL_DIRS: tuple[str, ...] = (
    ".zcode/tools/",   # 治理工具（validate_state/repair_continuity/close_session...）
    ".ai/checkers/",   # 检查器（compile_gate/run_governance_checks...）
    ".ai/guards/",     # 守卫（policy_guard）
    "scripts/",        # 治理脚本（runtime_delivery_gate/regression_runner...）
    "hooks/",          # hook 自测
    "tools/",          # 项目 loop 工具 CLI/MCP（tool_state/tool_handoff/
                       # loop_guard_health/loop_self_audit...，与
                       # MINIMAL_METADATA_READ 中的 tools/ 治理语义一致）。
                       # T-0109 F5：36 工具 capability 化后工具清单见
                       # loop_core/capability_registry.py
                       # TOOL_CAPABILITY_MANIFEST；白名单按目录覆盖，工具
                       # 变更无需逐文件同步（一致性测试 AC-05 断言）。
)
