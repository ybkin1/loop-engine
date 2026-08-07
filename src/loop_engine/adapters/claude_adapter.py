"""
Claude Code Host Adapter — STRONG enforcement.

Claude Code provides hooks for both file writes AND shell command interception,
along with sub-agent isolation. This adapter implements the HostAdapter interface
for Claude Code with honest STRONG enforcement level.
"""
from __future__ import annotations

from loop_engine.adapters.zcode_adapter import ZCodeAdapter
from loop_core.enforcement import EnforcementLevel, HostCapabilities


class ClaudeCodeAdapter(ZCodeAdapter):
    """
    Claude Code adapter. Inherits most behavior from ZCodeAdapter but
    declares STRONG enforcement (can intercept both writes AND commands).
    """

    @property
    def host_name(self) -> str:
        return "Claude Code"

    @property
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            can_intercept_writes=True,        # Claude Code hooks
            can_intercept_commands=True,       # Bash interception available
            can_isolate_agents=True,           # Sub-agents supported
            can_enforce_exit_codes=True,       # Exit code semantics
            has_hooks_api=True,
        )

    @property
    def enforcement_level(self) -> EnforcementLevel:
        return EnforcementLevel.STRONG

    # All other behavior inherited from ZCodeAdapter (file ops, state, agent, evidence)
