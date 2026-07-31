"""
Unified Verdict System — single source of truth for all quality/security/audit verdicts.

All reports MUST use these verdicts. No string comparison, no custom booleans.
"""
from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    """Standardized verdict for all quality and security checks.
    
    PASS         — Check passed, no issues found.
    BLOCKED      — Check found blocking issues; execution cannot proceed.
    FAIL         — Check failed but not blocking (e.g., warnings only).
    UNAVAILABLE  — Tool or dependency not available; check could not run.
    NOT_VERIFIED — Check was not performed (not in scope, skipped, or pending).
    ABSTAIN      — Check was intentionally skipped (e.g., not applicable to this phase).
    """
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    FAIL = "FAIL"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_VERIFIED = "NOT_VERIFIED"
    ABSTAIN = "ABSTAIN"

    def is_blocking(self) -> bool:
        """Returns True if this verdict should block further execution."""
        return self in (Verdict.BLOCKED, Verdict.FAIL)

    def is_conclusive(self) -> bool:
        """Returns True if this verdict represents a completed check (pass or fail)."""
        return self in (Verdict.PASS, Verdict.BLOCKED, Verdict.FAIL)


class ReportBinding:
    """Standard binding fields for all quality/security/audit reports.
    
    Every report MUST include these fields to enable traceability and
    prevent old/fake reports from being reused.
    """
    task_id: str
    phase: str
    gate_id: str | None
    execution_id: str | None
    git_commit: str
    diff_fingerprint: str | None
    timestamp: str  # ISO 8601
    tool_name: str
    tool_version: str

    def __init__(self, task_id: str, phase: str, gate_id: str | None = None,
                 execution_id: str | None = None, git_commit: str = "",
                 diff_fingerprint: str | None = None, timestamp: str = "",
                 tool_name: str = "", tool_version: str = ""):
        self.task_id = task_id
        self.phase = phase
        self.gate_id = gate_id
        self.execution_id = execution_id
        self.git_commit = git_commit
        self.diff_fingerprint = diff_fingerprint
        self.timestamp = timestamp
        self.tool_name = tool_name
        self.tool_version = tool_version

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "phase": self.phase,
            "gate_id": self.gate_id,
            "execution_id": self.execution_id,
            "git_commit": self.git_commit,
            "diff_fingerprint": self.diff_fingerprint,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReportBinding":
        return cls(
            task_id=d.get("task_id", ""),
            phase=d.get("phase", ""),
            gate_id=d.get("gate_id"),
            execution_id=d.get("execution_id"),
            git_commit=d.get("git_commit", ""),
            diff_fingerprint=d.get("diff_fingerprint"),
            timestamp=d.get("timestamp", ""),
            tool_name=d.get("tool_name", ""),
            tool_version=d.get("tool_version", ""),
        )

    def validate(self) -> list[str]:
        """Validate required fields. Returns list of missing field names."""
        missing = []
        if not self.task_id:
            missing.append("task_id")
        if not self.phase:
            missing.append("phase")
        if not self.git_commit:
            missing.append("git_commit")
        if not self.timestamp:
            missing.append("timestamp")
        return missing
