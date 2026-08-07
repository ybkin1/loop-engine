"""
Cost tracker integration — Wire cost_tracker.py into the Loop workflow.

This module provides a decorator and context manager for tracking
token costs at the role and phase level during Loop execution.
"""
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CostEntry:
    """A single cost tracking entry."""
    timestamp: str
    role: str
    phase: str
    task_id: str
    tokens: int = 0
    agent_id: str = ""
    action: str = ""  # "agent_launch", "gate_approval", "phase_transition", "review"


class CostTracker:
    """Tracks Loop execution costs per role and phase."""

    def __init__(self, project_root: str | Path):
        self._root = Path(project_root)
        self._log_dir = self._root / ".ai" / "evidence" / "costs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / "cost_log.jsonl"
        self._entries: list[CostEntry] = []

    def record(self, role: str, phase: str, task_id: str, tokens: int = 0,
               agent_id: str = "", action: str = "") -> CostEntry:
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=role,
            phase=phase,
            task_id=task_id,
            tokens=tokens,
            agent_id=agent_id,
            action=action,
        )
        self._entries.append(entry)
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp,
                "role": entry.role,
                "phase": entry.phase,
                "task_id": entry.task_id,
                "tokens": entry.tokens,
                "agent_id": entry.agent_id,
                "action": entry.action,
            }, ensure_ascii=False) + "\n")
        return entry

    def summary(self) -> dict:
        """Generate cost summary by role and phase."""
        total = 0
        by_role: dict[str, int] = {}
        by_phase: dict[str, int] = {}
        by_action: dict[str, int] = {}

        for e in self._entries:
            total += e.tokens
            by_role[e.role] = by_role.get(e.role, 0) + e.tokens
            by_phase[e.phase] = by_phase.get(e.phase, 0) + e.tokens
            by_action[e.action] = by_action.get(e.action, 0) + e.tokens

        return {
            "total_tokens": total,
            "entry_count": len(self._entries),
            "by_role": by_role,
            "by_phase": by_phase,
            "by_action": by_action,
            "rework_ratio": self._rework_ratio(),
        }

    def _rework_ratio(self) -> float:
        """Estimate rework ratio: tasks that had >1 agent call in same phase."""
        task_phase_counts: dict[str, int] = {}
        for e in self._entries:
            key = f"{e.task_id}:{e.phase}"
            task_phase_counts[key] = task_phase_counts.get(key, 0) + 1
        reworked = sum(1 for v in task_phase_counts.values() if v > 1)
        return reworked / max(len(task_phase_counts), 1)


@contextmanager
def track_cost(tracker: CostTracker, role: str, phase: str, task_id: str,
               agent_id: str = "", action: str = ""):
    """Context manager that records a cost entry on exit."""
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        # Rough token estimate: ~1K tokens per second of agent work
        estimated_tokens = int(elapsed * 1000)
        tracker.record(role, phase, task_id, estimated_tokens, agent_id, action)
