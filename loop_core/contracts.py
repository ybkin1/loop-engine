"""
Loop Core Contracts — Governance platform interface.

HostAdapter is the full governance contract that any AI coding host must
implement to support Loop engineering.  It covers:

  - Identity & capabilities                  (host_name, capabilities)
  - File system access                       (read/write/exists)
  - Command execution                        (execute)
  - Agent lifecycle                          (launch_agent)
  - State & gate management                  (load/save state, gates, tasks)
  - User interaction                         (present_gate, ask_user)
  - Evidence integrity                       (freeze_evidence, check_freshness)

Relationship with AgentAdapter
-------------------------------
AgentAdapter (loop_core/agent_adapter.py) is the minimal agent-execution
contract — just spawn, monitor, collect.  HostAdapter is the comprehensive
governance contract that includes agent management as one of its concerns.

A HostAdapter implementation SHOULD compose an AgentAdapter internally for
agent lifecycle operations.  The two interfaces serve different layers:

    HostAdapter   — governance platform ("what the Loop system needs")
    AgentAdapter  — agent executor     ("how to spawn and manage an agent")

They are intentionally separate, not conflicting.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from .enforcement import EnforcementLevel, HostCapabilities


class HostAdapter(ABC):
    """
    Abstract interface for a Loop host adapter.

    Each AI coding host (ZCode, Claude Code, Qoder, etc.) must implement
    this interface to connect Loop Core to the host's specific capabilities.
    """

    # ── Identity ──

    @property
    @abstractmethod
    def host_name(self) -> str:
        """Human-readable host name, e.g. 'ZCode', 'Claude Code'."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> HostCapabilities:
        """Declare what this host can actually enforce."""
        ...

    @property
    def enforcement_level(self) -> EnforcementLevel:
        return self.capabilities.enforcement_level()

    # ── File System ──

    @abstractmethod
    def read_file(self, path: str | Path) -> str:
        """Read a file from the project. May be intercepted by host hooks."""
        ...

    @abstractmethod
    def write_file(self, path: str | Path, content: str) -> bool:
        """
        Write a file. Returns False if blocked by host enforcement.
        At STRONG level, blocked writes must be truly prevented.
        """
        ...

    @abstractmethod
    def file_exists(self, path: str | Path) -> bool:
        ...

    # ── Command Execution ──

    @abstractmethod
    def execute(self, command: str, args: list[str], timeout_ms: int = 30000) -> tuple[int, str, str]:
        """
        Execute a command. Returns (exit_code, stdout, stderr).
        At STRONG level, dangerous commands must be blockable.
        """
        ...

    # ── Agent Management ──

    @abstractmethod
    def launch_agent(
        self,
        role_id: str,
        prompt: str,
        input_files: list[str],
        output_file: str,
    ) -> str:
        """
        Launch an isolated sub-agent for a role.
        Returns the agent_id for tracking (used in self-review checks).
        The agent MUST run in isolated context, not sharing the main session's memory.
        """
        ...

    # ── State Management ──

    @abstractmethod
    def load_state(self) -> dict[str, Any]:
        """Load the current project state (state.yaml equivalent)."""
        ...

    @abstractmethod
    def save_state(self, state: dict[str, Any]) -> bool:
        """Save project state. Returns False if blocked."""
        ...

    @abstractmethod
    def load_gates(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def load_tasks(self) -> list[dict[str, Any]]:
        ...

    # ── User Interaction ──

    @abstractmethod
    def present_gate(self, gate: dict[str, Any], summary: str) -> str:
        """
        Present a gate to the user for decision.
        Returns 'approved', 'rejected', or 'repair_requested'.
        """
        ...

    @abstractmethod
    def ask_user(self, question: str, context: str) -> str:
        """Ask the user a question that requires their input."""
        ...

    # ── Evidence ──

    @abstractmethod
    def freeze_evidence(self, evidence_id: str, bindings: dict[str, str]) -> str:
        """Freeze evidence with content hash. Returns the SHA256."""
        ...

    @abstractmethod
    def check_evidence_freshness(self, evidence_id: str) -> bool:
        """Check if evidence is still valid (inputs haven't changed)."""
        ...
