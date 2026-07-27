"""
Agent Adapter — Minimal agent-execution contract.

AgentAdapter defines the smallest interface needed to spawn, monitor, and
collect results from an AI agent.  It is deliberately narrow — just the
agent lifecycle.  Everything else (file I/O, state management, gate
presentation, evidence, user interaction) belongs to HostAdapter
(loop_core/contracts.py).

Relationship with HostAdapter
-------------------------------
HostAdapter is the comprehensive governance contract.  AgentAdapter is the
focused agent-execution contract.  A HostAdapter implementation SHOULD
compose an AgentAdapter internally for agent lifecycle operations.

    HostAdapter   — governance platform ("what the Loop system needs")
    AgentAdapter  — agent executor     ("how to spawn and manage an agent")

Specific platform implementations (e.g. ZCodeAgentAdapter) live in the
host adapter layer (hooks/, tools/), NOT in loop_core/.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class AgentStatus(str, Enum):
    PENDING = "pending"
    LAUNCHING = "launching"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


@dataclass
class AgentInput:
    """Agent 输入载体。fingerprint() 提供不可否认的输入指纹。"""

    role_id: str
    task_id: str
    prompt: str
    input_files: list[str] = field(default_factory=list)
    read_scope: list[str] = field(default_factory=list)
    write_scope: list[str] = field(default_factory=list)
    session_id: str | None = None
    actor_id: str | None = None
    allowed_tools: list[str] | None = None
    forbidden_tools: list[str] | None = None
    start_time: str | None = None

    def fingerprint(self) -> str:
        payload = json.dumps({
            "role_id": self.role_id, "task_id": self.task_id,
            "prompt": self.prompt, "input_files": sorted(self.input_files),
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class AgentOutput:
    """Agent 输出。input_integrity_ok() 验证输入未被篡改。"""

    actor_id: str
    session_id: str
    role_id: str
    task_id: str
    status: AgentStatus
    exit_code: int = 0
    output_artifact: dict[str, Any] | None = None
    stdout: str = ""
    stderr: str = ""
    start_time: str | None = None
    end_time: str | None = None
    input_fingerprint: str = ""
    output_files: list[str] = field(default_factory=list)
    tool_violations: list[str] = field(default_factory=list)
    contract_violated: bool = False
    reported_input_hash: str = ""

    def input_integrity_ok(self) -> bool:
        if not self.input_fingerprint or not self.reported_input_hash:
            return False
        return self.input_fingerprint == self.reported_input_hash

    @property
    def is_clean(self) -> bool:
        return (
            self.status == AgentStatus.COMPLETED
            and self.input_integrity_ok()
            and not self.contract_violated
        )


class AgentUnavailableError(RuntimeError):
    """Agent 不可用。不可 fallback 到 fixture 模拟。"""

    def __init__(self, role_id: str, host: str, reason: str = ""):
        msg = f"REAL_AGENT_UNAVAILABLE: role='{role_id}' host='{host}'"
        if reason:
            msg += f". {reason}"
        super().__init__(msg)
        self.role_id = role_id
        self.host = host


@dataclass(frozen=True)
class DelegationRequest:
    """受限子代理委派请求；默认不允许角色代理继续委派。"""

    parent_execution_id: str
    parent_role_id: str
    task_id: str
    phase: str
    gate_id: str
    child_role_id: str
    allowed_paths: tuple[str, ...]
    allowed_tools: tuple[str, ...] = ()
    depth: int = 1
    max_depth: int = 1
    delegation_allowed: bool = False
    read_only: bool = True
    budget_seconds: int = 300

    def validate(self) -> tuple[bool, str]:
        if not self.parent_execution_id or not self.task_id or not self.phase or not self.gate_id:
            return False, "DELEGATION_CONTEXT_REQUIRED"
        if not self.child_role_id or not self.allowed_paths:
            return False, "DELEGATION_SCOPE_REQUIRED"
        if self.depth > 1 and not self.delegation_allowed:
            return False, "DELEGATION_NOT_ALLOWED"
        if self.depth < 1 or self.max_depth < self.depth:
            return False, "DELEGATION_DEPTH_INVALID"
        if self.budget_seconds <= 0:
            return False, "DELEGATION_BUDGET_INVALID"
        if self.child_role_id == "independent-reviewer" and self.parent_role_id == "developer":
            return False, "REVIEWER_MUST_NOT_BE_DEVELOPER_CHILD"
        return True, "AUTHORIZED"


@dataclass(frozen=True)
class AgentCapabilityProbe:
    """宿主能力探针结果；配置存在不等于递归能力已验证。"""

    host: str
    configured: bool
    agent_tool_visible: bool
    recursive_launch: bool | None
    governed_recursive_launch: bool | None
    status: str
    detail: str = ""


def probe_agent_capability(*, host: str = "", configured: bool = True,
                           agent_tool_visible: bool = False) -> AgentCapabilityProbe:
    """Return a conservative capability result without launching an Agent."""
    if not host:
        return AgentCapabilityProbe("unknown", False, False, None, None, "NOT_CONFIGURED",
                                    "Host name is required for capability probe")
    if not configured:
        return AgentCapabilityProbe(host, False, False, None, None, "NOT_CONFIGURED")
    if not agent_tool_visible:
        return AgentCapabilityProbe(host, True, False, None, None, "CAPABILITY_UNAVAILABLE",
                                    "Agent tool visibility was not provided by the host")
    return AgentCapabilityProbe(host, True, True, None, None, "NOT_VERIFIED",
                                "Recursive launch requires an isolated host probe")


class AgentAdapter(ABC):
    """Minimal agent-execution contract — just spawn, monitor, collect.

    This is deliberately narrow.  File I/O, state management, gate presentation,
    evidence, and user interaction belong to HostAdapter (loop_core/contracts.py).

    Concrete implementations (e.g. ZCodeAgentAdapter) live in hooks/ or tools/.
    """

    @abstractmethod
    def launch_agent(self, agent_input: AgentInput) -> AgentOutput: ...

    @abstractmethod
    def get_status(self, session_id: str) -> AgentStatus: ...

    @abstractmethod
    def collect_output(self, session_id: str) -> AgentOutput: ...

    @property
    @abstractmethod
    def host_name(self) -> str: ...
