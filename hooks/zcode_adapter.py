"""
ZCode Agent Adapter — ZCode-specific implementation of the AgentAdapter interface.

Moved from loop_core/agent_adapter.py to hooks/ in v3.7 to respect the
host-independence principle: loop_core/ contains only the abstract interface
(AgentAdapter ABC + data classes), while this hooks/ module provides the
ZCode concrete implementation.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from loop_core.agent_adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentUnavailableError,
)


class ZCodeAgentAdapter(AgentAdapter):
    """ZCode platform agent adapter.

    Uses prepare_launch() + Agent tool + collect_result() three-step
    workflow instead of direct launch_agent().

    If project_root is set, prepare_launch/collect_result automatically
    write to .ai/ledger/executions.jsonl (chained hash append).
    """

    host_name = "zcode"

    def __init__(self, project_root: Path | str | None = None):
        self._project_root = Path(project_root) if project_root else None

    @staticmethod
    def generate_session_id(task_id: str, role_id: str) -> str:
        seed = f"{task_id}:{role_id}:{uuid.uuid4().hex}"
        return f"zcode-sess-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"

    @staticmethod
    def generate_actor_id(role_id: str) -> str:
        return f"zcode-actor-{hashlib.sha256(role_id.encode()).hexdigest()[:12]}"

    @staticmethod
    def _hash_input_files(input_files: list[str]) -> str:
        if not input_files:
            return hashlib.sha256(b"").hexdigest()
        h = hashlib.sha256()
        for f in sorted(input_files):
            h.update(f.encode())
        return h.hexdigest()

    @staticmethod
    def build_tool_constraint_prompt(
        allowed_tools: list[str] | None,
        forbidden_tools: list[str] | None,
    ) -> str:
        parts: list[str] = []
        if allowed_tools:
            parts.append(f"[TOOL_CONSTRAINT] Allowed: {', '.join(allowed_tools)}")
        if forbidden_tools:
            parts.append(f"[TOOL_CONSTRAINT] Forbidden: {', '.join(forbidden_tools)}")
        if parts:
            parts.append("[TOOL_CONSTRAINT] Violations → CONTRACT_VIOLATION")
        return "\n".join(parts)

    @staticmethod
    def scan_tool_violations(
        output_text: str, forbidden_tools: list[str] | None,
    ) -> list[str]:
        if not forbidden_tools:
            return []
        violations: list[str] = []
        for tool in forbidden_tools:
            if re.search(
                rf'(?:call|invoke|use|run|execute)\S*\s+{re.escape(tool)}',
                output_text, re.IGNORECASE,
            ):
                violations.append(tool)
        return violations

    _HASH_MARKER_RE = re.compile(r'INPUT_HASH:([a-f0-9]{64})')

    @staticmethod
    def verify_input_integrity(sent_hash: str, reported_hash: str) -> bool:
        return bool(sent_hash and reported_hash and sent_hash == reported_hash)

    def prepare_launch(self, agent_input: AgentInput) -> AgentInput:
        import uuid as _uuid
        agent_input.session_id = self.generate_session_id(agent_input.task_id, agent_input.role_id)
        agent_input.actor_id = self.generate_actor_id(agent_input.role_id)
        agent_input.start_time = datetime.now(timezone.utc).isoformat()
        execution_id = f"exec-{_uuid.uuid4().hex[:12]}"
        fp = agent_input.fingerprint()
        constraint = self.build_tool_constraint_prompt(agent_input.allowed_tools, agent_input.forbidden_tools)
        hash_instruction = f"\n\n[PROTOCOL] INPUT_HASH:{fp}"
        extra: list[str] = []
        if constraint:
            extra.append(constraint)
        extra.append(hash_instruction)
        agent_input.prompt = agent_input.prompt + "\n" + "\n".join(extra)
        if self._project_root is not None:
            try:
                from loop_core.execution_ledger import ExecutionLedger, ExecutionRecord, ExecutionStatus
                ledger = ExecutionLedger(self._project_root)
                record = ExecutionRecord(
                    execution_id=execution_id, session_id=agent_input.session_id,
                    actor_id=agent_input.actor_id, role_id=agent_input.role_id,
                    task_id=agent_input.task_id, prompt_fingerprint=fp,
                    input_files_hash=self._hash_input_files(agent_input.input_files),
                    status=ExecutionStatus.LAUNCHED, launched_at=agent_input.start_time,
                    tool_constraints=agent_input.allowed_tools or [],
                )
                ledger.record_launch(record)
            except Exception:
                pass
        agent_input._execution_id = execution_id  # type: ignore[attr-defined]
        return agent_input

    def collect_result(self, agent_input: AgentInput, raw_output: str,
                       exit_code: int = 0, output_files: list[str] | None = None,
                       start_time: str | None = None) -> AgentOutput:
        now = datetime.now(timezone.utc).isoformat()
        st = start_time or agent_input.start_time
        reported_hash = ""
        clean_output = raw_output
        m = self._HASH_MARKER_RE.search(raw_output)
        if m:
            reported_hash = m.group(1)
            clean_output = self._HASH_MARKER_RE.sub("", raw_output).strip()
        violations = self.scan_tool_violations(raw_output, agent_input.forbidden_tools)
        status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED
        output = AgentOutput(
            actor_id=agent_input.actor_id or "", session_id=agent_input.session_id or "",
            role_id=agent_input.role_id, task_id=agent_input.task_id, status=status,
            exit_code=exit_code, stdout=clean_output, stderr="", start_time=st,
            end_time=now, input_fingerprint=agent_input.fingerprint(),
            reported_input_hash=reported_hash, output_files=output_files or [],
            tool_violations=violations, contract_violated=len(violations) > 0,
        )
        if self._project_root is not None:
            try:
                from loop_core.execution_ledger import ExecutionLedger, ExecutionStatus
                eid = getattr(agent_input, "_execution_id", None)
                if eid:
                    ledger = ExecutionLedger(self._project_root)
                    ls = ExecutionStatus.VIOLATED if violations else (
                        ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED)
                    output_hash_val = hashlib.sha256(clean_output.encode()).hexdigest() if clean_output else None
                    ledger.record_completion(execution_id=eid, status=ls, exit_code=exit_code,
                                             output_hash=output_hash_val, tool_violations=violations)
            except Exception:
                pass
        return output

    def launch_agent(self, agent_input: AgentInput) -> AgentOutput:
        raise AgentUnavailableError(agent_input.role_id, self.host_name,
            "ZCode agent API not yet available.")

    def get_status(self, session_id: str) -> AgentStatus:
        return AgentStatus.UNAVAILABLE

    def collect_output(self, session_id: str) -> AgentOutput:
        raise AgentUnavailableError("unknown", self.host_name,
            "Cannot collect output: agent API not available.")
