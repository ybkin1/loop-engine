"""
CodexAgentAdapter -- Agent launching via Codex multi_agent_v1_spawn_agent.

Adapts the AgentAdapter abstract interface for Codex native sub-agent API.
"""
from __future__ import annotations

from pathlib import Path

from codex_loop.runtime.agent_adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentUnavailableError,
)


class CodexAgentAdapter(AgentAdapter):
    """Codex native agent adapter using multi_agent_v1_spawn_agent.

    Codex provides built-in sub-agent spawning via:
        multi_agent_v1_spawn_agent(
            agent_type="explorer" | "code-agent" | ...
            message="Complete prompt",
            fork_context=False,
        )

    Role to agent_type mapping:
        product-manager      -> researcher
        system-architect     -> designer-agent
        developer            -> code-agent
        quality-engineer     -> test-reviewer
        independent-reviewer -> code-reviewer
        security-engineer    -> explorer
    """

    host_name = "codex"

    ROLE_TO_AGENT_TYPE = {
        "product-manager": "researcher",
        "system-architect": "designer-agent",
        "module-architect": "designer-agent",
        "developer": "code-agent",
        "quality-engineer": "test-reviewer",
        "security-engineer": "explorer",
        "independent-reviewer": "code-reviewer",
        "delivery-manager": "default",
        "release-engineer": "default",
        "project-manager": "default",
    }

    def __init__(self, project_root: str | Path | None = None):
        self._project_root = Path(project_root) if project_root else None

    def launch_agent(self, agent_input: AgentInput) -> AgentOutput:
        self.ROLE_TO_AGENT_TYPE.get(agent_input.role_id, "default")
        return AgentOutput(
            actor_id=f"codex-actor-{agent_input.role_id}",
            session_id=f"codex-sess-{agent_input.task_id}",
            role_id=agent_input.role_id,
            task_id=agent_input.task_id,
            status=AgentStatus.LAUNCHING,
            input_fingerprint=agent_input.fingerprint(),
        )

    def get_status(self, session_id: str) -> AgentStatus:
        return AgentStatus.RUNNING

    def collect_output(self, session_id: str) -> AgentOutput:
        raise AgentUnavailableError(
            "unknown", self.host_name,
            "Use multi_agent_v1_wait_agent to collect sub-agent results."
        )
