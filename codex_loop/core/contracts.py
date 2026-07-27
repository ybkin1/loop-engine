"""
Loop Core Contracts — Interface that every Host Adapter must implement.

This defines the abstract boundary between Loop Core (host-independent)
and Host Adapter (host-specific). Any AI coding host that wants to implement
Loop governance must provide an adapter that satisfies this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from codex_loop.core.enforcement import EnforcementLevel, HostCapabilities


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



# ── Role Contract (from original codex_loop) ──────────────────────────

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleContract:
    """Immutable role specification used by the context builder."""
    role_id: str
    role_version: str
    system_prompt: str
    context_budget_tokens: int = 1200
    allowed_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    output_schema: dict | None = None

    def prompt_text(self) -> str:
        parts = [self.system_prompt]
        if self.allowed_tools:
            parts.append("Allowed tools: " + ", ".join(self.allowed_tools))
        if self.forbidden_tools:
            parts.append("Forbidden tools: " + ", ".join(self.forbidden_tools))
        if self.stop_conditions:
            parts.append("Stop conditions: " + "; ".join(self.stop_conditions))
        return "\n".join(parts)


@dataclass(frozen=True)
class RoleRegistry:
    """Immutable registry of role contracts keyed by role_id."""
    roles: dict[str, "RoleContract"]  # type: ignore[name-defined]

    def get(self, role_id: str) -> "RoleContract":  # type: ignore[name-defined]
        if role_id not in self.roles:
            raise KeyError(f"unknown role: {role_id}")
        return self.roles[role_id]
