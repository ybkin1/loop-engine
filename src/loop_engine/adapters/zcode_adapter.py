"""
ZCode Host Adapter — Concrete implementation of HostAdapter for ZCode.

Bridges Loop Core's host-independent protocol to ZCode's actual capabilities:
- STRONG enforcement (PreToolUse hooks intercept Write/Edit/Bash/ApplyPatch/Agent)
- Agent isolation via ZCode's Agent tool
- State/gate/task management via .ai/ YAML files
- Evidence freezing via SHA256 hashing

Declares: ENFORCEMENT_LEVEL = STRONG (hooks.json has PreToolUse interception for Write+Edit+Bash+ApplyPatch+Agent)

T-0177 M1: 共享实现移至 _host_base.HostAdapterBase（参数化宿主配置目录）；
本类只声明 ZCode 宿主身份、能力与配置目录（.zcode/）。
"""
from __future__ import annotations

from pathlib import Path

# Loop Core imports
from loop_core.enforcement import EnforcementLevel, HostCapabilities

from loop_engine.adapters._host_base import HostAdapterBase


class ZCodeAdapter(HostAdapterBase):
    """
    ZCode-specific implementation of the Loop Host Adapter.

    Uses:
    - ZCode hooks (gate_guard, path_guard) for write interception
    - ZCode Agent tool for role isolation
    - .ai/ YAML files for state management
    - SHA256 for evidence freezing
    """

    def __init__(self, project_root: str | Path):
        super().__init__(project_root, config_dir_name=".zcode")

    # ── Identity ──

    @property
    def host_name(self) -> str:
        return "ZCode"

    @property
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            can_intercept_writes=True,       # PreToolUse hooks intercept Write/Edit
            can_intercept_commands=True,      # PreToolUse hooks intercept Bash (hooks.json matcher includes "Bash")
            can_isolate_agents=True,          # Agent tool = fresh context
            can_enforce_exit_codes=True,      # exit 2 = deny in hooks
            has_hooks_api=True,               # hooks.json + events schema
        )

    @property
    def enforcement_level(self) -> EnforcementLevel:
        # ZCode's PreToolUse hooks intercept Write/Edit/Bash/ApplyPatch/Agent.
        # Per enforcement.py: STRONG requires write + command + exit_code enforcement.
        # ZCode qualifies for STRONG because hooks.json matcher includes all operation types.
        return self.capabilities.enforcement_level()
