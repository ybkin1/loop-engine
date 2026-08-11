"""
Claude Code Host Adapter — STRONG enforcement.

Claude Code provides hooks (settings.json hooks / PreToolUse) for both file
writes AND shell command interception, along with sub-agent isolation.
This adapter implements the HostAdapter interface for Claude Code with
honest STRONG enforcement level.

T-0177 M1: 原实现为 38 行纯继承 ZCodeAdapter（宿主身份是假的——Claude Code
没有 .zcode/ 目录）。现基于共享 HostAdapterBase 独立实现，宿主配置目录为
.claude/，能力声明与 Claude Code 的 hooks/settings 机制对应。
"""
from __future__ import annotations

from pathlib import Path

from loop_core.enforcement import EnforcementLevel, HostCapabilities

from loop_engine.adapters._host_base import HostAdapterBase


class ClaudeCodeAdapter(HostAdapterBase):
    """
    Claude Code-specific implementation of the Loop Host Adapter.

    Uses:
    - Claude Code hooks (.claude/settings.json PreToolUse) for interception
    - Claude Code sub-agents for role isolation
    - .ai/ YAML files for state management
    - SHA256 for evidence freezing
    """

    def __init__(self, project_root: str | Path):
        super().__init__(project_root, config_dir_name=".claude")

    # ── Identity ──

    @property
    def host_name(self) -> str:
        return "Claude Code"

    @property
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            can_intercept_writes=True,        # Claude Code hooks (PreToolUse)
            can_intercept_commands=True,       # Bash interception available
            can_isolate_agents=True,           # Sub-agents supported
            can_enforce_exit_codes=True,       # Exit code semantics
            has_hooks_api=True,
        )

    @property
    def enforcement_level(self) -> EnforcementLevel:
        return self.capabilities.enforcement_level()

    def validate_startup(self) -> dict:
        """Claude Code 启动校验：在基座检查之上追加宿主配置目录检查。"""
        result = super().validate_startup()
        settings = self._config_dir / "settings.json"
        if not settings.exists():
            result.setdefault("warnings", []).append(
                f"Missing {settings.name} — Claude Code hooks 未配置"
            )
        return result
