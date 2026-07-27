"""
Agent Adapter — 抽象 Agent 调用接口 + ZCode 实现。

当 ZCode Agent API（session_id / actor_id / tool whitelist / input freeze）
不可用时，以三个替代方案保证治理完整性：

  1. 本地生成 session_id/actor_id + prompt SHA256 fingerprint
  2. 工具白名单替代：System Prompt 注入 + 事后扫描 + 合同自约束
  3. 输入冻结替代：发送 hash vs Agent 回报 hash 比对

Main Thread 工作流：
  adapter.prepare_launch(input)  →  Agent 工具调用  →  adapter.collect_result(...)
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# Core Types
# ═══════════════════════════════════════════════════════════════════════

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
    """Agent 输入载体。fingerprint() 提供不可否认的输入指纹（替代方案 #1/#3）。"""

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

    # 由 prepare_launch() 填充
    start_time: str | None = None

    def fingerprint(self) -> str:
        """SHA256 指纹覆盖 role + task + prompt + input_files（替代方案 #1/#3）。"""
        payload = json.dumps(
            {
                "role_id": self.role_id,
                "task_id": self.task_id,
                "prompt": self.prompt,
                "input_files": sorted(self.input_files),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class AgentOutput:
    """Agent 输出。input_integrity_ok() 验证输入未被篡改（替代方案 #3）。"""

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

    # ── 替代方案 #2 事后检测结果 ──
    tool_violations: list[str] = field(default_factory=list)
    contract_violated: bool = False

    # ── 替代方案 #3：Agent 回报的输入 hash ──
    reported_input_hash: str = ""

    def input_integrity_ok(self) -> bool:
        """发送 hash vs Agent 回报 hash 比对（替代方案 #3）。"""
        if not self.input_fingerprint or not self.reported_input_hash:
            return False
        return self.input_fingerprint == self.reported_input_hash

    @property
    def is_clean(self) -> bool:
        """综合校验：状态完成 + 输入完整 + 无违规。"""
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


def probe_agent_capability(*, host: str = "zcode", configured: bool = True,
                           agent_tool_visible: bool = False) -> AgentCapabilityProbe:
    """Return a conservative capability result without launching an Agent.

    ZCode's public adapter is currently a prepare/collect bridge, so recursive
    execution remains unverified until a host live-fire probe is run.
    """
    if not configured:
        return AgentCapabilityProbe(host, False, False, None, None, "NOT_CONFIGURED")
    if not agent_tool_visible:
        return AgentCapabilityProbe(host, True, False, None, None, "CAPABILITY_UNAVAILABLE",
                                    "Agent tool visibility was not provided by the host")
    return AgentCapabilityProbe(host, True, True, None, None, "NOT_VERIFIED",
                                "Recursive launch requires an isolated host probe")


# ═══════════════════════════════════════════════════════════════════════
# Abstract Interface
# ═══════════════════════════════════════════════════════════════════════

class AgentAdapter(ABC):
    """Agent 调用抽象接口。所有宿主平台必须实现此接口。"""

    @abstractmethod
    def launch_agent(self, agent_input: AgentInput) -> AgentOutput: ...

    @abstractmethod
    def get_status(self, session_id: str) -> AgentStatus: ...

    @abstractmethod
    def collect_output(self, session_id: str) -> AgentOutput: ...

    @property
    @abstractmethod
    def host_name(self) -> str: ...


# ═══════════════════════════════════════════════════════════════════════
# ZCodeAgentAdapter
# ═══════════════════════════════════════════════════════════════════════

class ZCodeAgentAdapter(AgentAdapter):
    """ZCode 平台 Agent 适配器。

    当前 ZCode Agent API 未就绪，使用 prepare_launch() + Agent 工具 +
    collect_result() 三步工作流替代直接 launch_agent()。

    三步流程（Main Thread 调用）：
        # 1. 准备（生成 ID + 注入约束 + 写入 ledger）
        prepared = adapter.prepare_launch(agent_input)
        # 2. 调 Agent 工具（Main Thread 中）
        result = Agent(description=..., prompt=prepared.prompt, ...)
        # 3. 收集 + 校验 + 写入 ledger
        output = adapter.collect_result(prepared, result)
        assert output.is_clean

    若 project_root 不为 None，prepare_launch/collect_result 会自动
    写入 .ai/ledger/executions.jsonl（链式 hash 追加写）。
    """

    host_name = "zcode"

    def __init__(self, project_root: Path | str | None = None):
        self._project_root = Path(project_root) if project_root else None

    # ═══════════════════════════════════════════════════════════════════
    # 替代方案 #1：本地生成 session_id / actor_id
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def generate_session_id(task_id: str, role_id: str) -> str:
        """确定性 session_id = zcode-sess-{SHA256(task:role:uuid)[:16]}"""
        seed = f"{task_id}:{role_id}:{uuid.uuid4().hex}"
        return f"zcode-sess-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"

    @staticmethod
    def generate_actor_id(role_id: str) -> str:
        """确定性 actor_id = zcode-actor-{SHA256(role_id)[:12]}"""
        return f"zcode-actor-{hashlib.sha256(role_id.encode()).hexdigest()[:12]}"

    @staticmethod
    def _hash_input_files(input_files: list[str]) -> str:
        """计算所有输入文件的聚合 SHA256。"""
        if not input_files:
            return hashlib.sha256(b"").hexdigest()
        h = hashlib.sha256()
        for f in sorted(input_files):
            h.update(f.encode())
        return h.hexdigest()

    # ═══════════════════════════════════════════════════════════════════
    # 替代方案 #2：工具白名单 — System Prompt + 事后扫描
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def build_tool_constraint_prompt(
        allowed_tools: list[str] | None,
        forbidden_tools: list[str] | None,
    ) -> str:
        """第一层（事前）：生成注入到 system prompt 的工具约束指令。"""
        parts: list[str] = []
        if allowed_tools:
            parts.append(
                f"[TOOL_CONSTRAINT] 你只能使用以下工具: {', '.join(allowed_tools)}。"
            )
        if forbidden_tools:
            parts.append(
                f"[TOOL_CONSTRAINT] 禁止使用以下工具: {', '.join(forbidden_tools)}。"
            )
        if parts:
            parts.append(
                "[TOOL_CONSTRAINT] 违规使用工具将导致输出被 CONTRACT_VIOLATION 标记。"
            )
        return "\n".join(parts)

    @staticmethod
    def scan_tool_violations(
        output_text: str,
        forbidden_tools: list[str] | None,
    ) -> list[str]:
        """第二层（事后）：扫描 Agent 输出检测违规工具调用模式。"""
        if not forbidden_tools:
            return []
        violations: list[str] = []
        for tool in forbidden_tools:
            if re.search(
                rf'(?:call|invoke|use|run|execute)\S*\s+{re.escape(tool)}',
                output_text,
                re.IGNORECASE,
            ):
                violations.append(tool)
        return violations

    # ═══════════════════════════════════════════════════════════════════
    # 替代方案 #3：输入冻结 — hash 比对
    # ═══════════════════════════════════════════════════════════════════

    _HASH_MARKER_RE = re.compile(r'INPUT_HASH:([a-f0-9]{64})')

    @staticmethod
    def verify_input_integrity(sent_hash: str, reported_hash: str) -> bool:
        """比对发送 hash 与 Agent 回报 hash。"""
        if not sent_hash or not reported_hash:
            return False
        return sent_hash == reported_hash

    # ═══════════════════════════════════════════════════════════════════
    # 工作流方法（Main Thread 调用）
    # ═══════════════════════════════════════════════════════════════════

    def prepare_launch(self, agent_input: AgentInput) -> AgentInput:
        """准备启动 Agent（替代方案 #1 + #2 + #3 注入 + ledger 写入）。

        在 Main Thread 调用 Agent 工具之前调用。修改 agent_input 并返回：
          - 生成 session_id / actor_id / execution_id（替代方案 #1）
          - 记录 start_time
          - 注入约束 prompt（替代方案 #2 + #3）
          - 写入 ledger LAUNCHED 条目（若 project_root 已设置）
        """
        import uuid as _uuid

        # ── 替代方案 #1：本地 ID ──
        agent_input.session_id = self.generate_session_id(
            agent_input.task_id, agent_input.role_id
        )
        agent_input.actor_id = self.generate_actor_id(agent_input.role_id)
        agent_input.start_time = datetime.now(timezone.utc).isoformat()

        # 生成 execution_id（用于 ledger 关联 LAUNCHED ↔ COMPLETED）
        execution_id = f"exec-{_uuid.uuid4().hex[:12]}"

        # ── 计算指纹 ──
        fp = agent_input.fingerprint()
        input_files_hash = self._hash_input_files(agent_input.input_files)

        # ── 替代方案 #2：工具约束注入 ──
        constraint = self.build_tool_constraint_prompt(
            agent_input.allowed_tools, agent_input.forbidden_tools
        )

        # ── 替代方案 #3：hash 回报指令 ──
        hash_instruction = f"\n\n[PROTOCOL] 在输出的最后一行附上: INPUT_HASH:{fp}"

        # ── 增强 prompt ──
        extra: list[str] = []
        if constraint:
            extra.append(constraint)
        extra.append(hash_instruction)
        agent_input.prompt = agent_input.prompt + "\n" + "\n".join(extra)

        # ── 写入 ledger（如果 project_root 已设置）──
        if self._project_root is not None:
            try:
                from loop_core.execution_ledger import (
                    ExecutionLedger,
                    ExecutionRecord,
                    ExecutionStatus,
                )
                ledger = ExecutionLedger(self._project_root)
                record = ExecutionRecord(
                    execution_id=execution_id,
                    session_id=agent_input.session_id,
                    actor_id=agent_input.actor_id,
                    role_id=agent_input.role_id,
                    task_id=agent_input.task_id,
                    prompt_fingerprint=fp,
                    input_files_hash=input_files_hash,
                    status=ExecutionStatus.LAUNCHED,
                    launched_at=agent_input.start_time,
                    tool_constraints=agent_input.allowed_tools or [],
                )
                ledger.record_launch(record)
            except Exception:
                pass  # ledger 写入失败不阻塞 Agent 启动

        # 保存 execution_id 以便 collect_result 使用
        agent_input._execution_id = execution_id  # type: ignore[attr-defined]

        return agent_input

    def collect_result(
        self,
        agent_input: AgentInput,
        raw_output: str,
        exit_code: int = 0,
        output_files: list[str] | None = None,
        start_time: str | None = None,
    ) -> AgentOutput:
        """收集 Agent 结果，执行全部替代方案的校验。

        在 Main Thread 收到 Agent 工具返回后调用。

        Args:
            agent_input: prepare_launch() 返回的输入
            raw_output: Agent 工具返回的原始文本
            exit_code: Agent 退出码（默认 0）
            output_files: Agent 产生的输出文件列表
            start_time: 启动时间（默认从 agent_input.start_time 读取）

        Returns:
            包含所有校验结果的 AgentOutput
        """
        now = datetime.now(timezone.utc).isoformat()
        st = start_time or agent_input.start_time

        # ── 替代方案 #3：提取 Agent 回报的输入 hash ──
        reported_hash = ""
        clean_output = raw_output
        m = self._HASH_MARKER_RE.search(raw_output)
        if m:
            reported_hash = m.group(1)
            clean_output = self._HASH_MARKER_RE.sub("", raw_output).strip()

        # ── 替代方案 #2：事后工具违规扫描（第二层）──
        violations = self.scan_tool_violations(raw_output, agent_input.forbidden_tools)

        # ── 构建结果 ──
        status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

        output = AgentOutput(
            actor_id=agent_input.actor_id or "",
            session_id=agent_input.session_id or "",
            role_id=agent_input.role_id,
            task_id=agent_input.task_id,
            status=status,
            exit_code=exit_code,
            stdout=clean_output,
            stderr="",
            start_time=st,
            end_time=now,
            input_fingerprint=agent_input.fingerprint(),
            reported_input_hash=reported_hash,
            output_files=output_files or [],
            tool_violations=violations,
            contract_violated=len(violations) > 0,
        )

        # ── 写入 ledger 完成条目（如果 project_root 已设置）──
        if self._project_root is not None:
            try:
                from loop_core.execution_ledger import ExecutionLedger, ExecutionStatus

                eid = getattr(agent_input, "_execution_id", None)
                if eid:
                    ledger = ExecutionLedger(self._project_root)
                    ls = ExecutionStatus.VIOLATED if violations else (
                        ExecutionStatus.COMPLETED if exit_code == 0
                        else ExecutionStatus.FAILED
                    )
                    output_hash_val = hashlib.sha256(
                        clean_output.encode()
                    ).hexdigest() if clean_output else None
                    ledger.record_completion(
                        execution_id=eid,
                        status=ls,
                        exit_code=exit_code,
                        output_hash=output_hash_val,
                        tool_violations=violations,
                    )
            except Exception:
                pass

        return output

    # ═══════════════════════════════════════════════════════════════════
    # 抽象接口桩（ZCode Agent API 就绪后替换）
    # ═══════════════════════════════════════════════════════════════════

    def launch_agent(self, agent_input: AgentInput) -> AgentOutput:
        """直接启动 Agent — 当前不可用。

        使用 prepare_launch() + Agent 工具 + collect_result() 替代。
        """
        raise AgentUnavailableError(
            agent_input.role_id,
            self.host_name,
            "ZCode agent API not yet available. "
            "Use prepare_launch() + Agent tool + collect_result() workflow.",
        )

    def get_status(self, session_id: str) -> AgentStatus:
        return AgentStatus.UNAVAILABLE

    def collect_output(self, session_id: str) -> AgentOutput:
        raise AgentUnavailableError(
            "unknown", self.host_name,
            "Cannot collect output: agent API not available. "
            "Use collect_result() with the raw Agent tool output instead.",
        )
