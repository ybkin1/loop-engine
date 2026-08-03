"""
Inbox — Structured requirement intake for Loop Engine.

Accepts natural-language requirements, analyses them via intent_router,
and stores them as structured Requirement objects.  Requirements are NOT
tasks — they must go through Planner → user approval → Gate before any
task is registered in task_graph.yaml.

Design constraints:
- Read-only analysis via intent_router (no side effects).
- One requirement per file under .ai/inbox/ (avoids giant YAML files).
- Fail-closed: any exception returns BLOCKED, never PASS.
- Does NOT write to task_graph.yaml, gates.yaml, or state.yaml.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class RequirementType(str, Enum):
    FEATURE = "FEATURE"
    BUG_FIX = "BUG_FIX"
    IMPROVEMENT = "IMPROVEMENT"
    QUESTION = "QUESTION"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class InboxStatus(str, Enum):
    NEW = "NEW"
    CLARIFYING = "CLARIFYING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    PLANNED = "PLANNED"


@dataclass
class Requirement:
    """A structured user requirement stored in the Inbox."""
    requirement_id: str
    title: str
    description: str
    type: RequirementType = RequirementType.FEATURE
    priority: Priority = Priority.P2
    status: InboxStatus = InboxStatus.NEW
    tags: list[str] = field(default_factory=list)
    source: str = "user"
    created_at: str = ""
    updated_at: str = ""
    linked_task_ids: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    clarification_rounds: int = 0
    linked_plan_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "linked_task_ids": self.linked_task_ids,
            "clarification_questions": self.clarification_questions,
            "clarification_rounds": self.clarification_rounds,
            "linked_plan_id": self.linked_plan_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Requirement":
        return cls(
            requirement_id=d["requirement_id"],
            title=d["title"],
            description=d["description"],
            type=RequirementType(d.get("type", "FEATURE")),
            priority=Priority(d.get("priority", "P2")),
            status=InboxStatus(d.get("status", "NEW")),
            tags=d.get("tags", []),
            source=d.get("source", "user"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            linked_task_ids=d.get("linked_task_ids", []),
            clarification_questions=d.get("clarification_questions", []),
            clarification_rounds=d.get("clarification_rounds", 0),
            linked_plan_id=d.get("linked_plan_id", ""),
        )


class InboxError(Exception):
    """Base exception for Inbox operations."""


class Inbox:
    """Manages requirement intake and lifecycle."""

    def __init__(self, project_root: str | Path) -> None:
        self._root = Path(project_root)
        self._inbox_dir = self._root / ".ai" / "inbox"
        self._inbox_dir.mkdir(parents=True, exist_ok=True)

    def submit(self, title: str, description: str, source: str = "user") -> Requirement:
        if not title.strip():
            raise InboxError("Requirement title must not be empty")
        if not description.strip():
            raise InboxError("Requirement description must not be empty")
        req_id = self._next_id()
        req = Requirement(
            requirement_id=req_id,
            title=title.strip(),
            description=description.strip(),
            source=source,
        )
        self._analyse(req)
        self._save(req)
        return req

    def get(self, requirement_id: str) -> Requirement:
        path = self._path_for(requirement_id)
        if not path.exists():
            raise InboxError(f"Requirement not found: {requirement_id}")
        return self._load(path)

    def list_all(self, status: str | None = None) -> list[Requirement]:
        results = []
        for entry in sorted(self._inbox_dir.glob("REQ-*.yaml")):
            try:
                req = self._load(entry)
                if status is None or req.status.value == status:
                    results.append(req)
            except Exception:
                continue
        return results

    def update_status(self, requirement_id: str, new_status: InboxStatus) -> Requirement:
        req = self.get(requirement_id)
        self._validate_status_transition(req.status, new_status)
        req.status = new_status
        req.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(req)
        return req

    def add_clarification_questions(self, requirement_id: str, questions: list[str]) -> Requirement:
        """(legacy) Replace the full clarification question list in one shot."""
        req = self.get(requirement_id)
        req.clarification_questions = questions
        req.clarification_rounds = max(req.clarification_rounds, 1)
        if req.status == InboxStatus.NEW:
            req.status = InboxStatus.CLARIFYING
        req.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(req)
        return req

    def ask_clarification(self, requirement_id: str, questions: list[str]) -> Requirement:
        """Append one round of clarification questions (Q2 teaching-style multi-round).

        Unlike ``add_clarification_questions`` (which replaces the whole
        list), this method APPENDS a new round to an existing CLARIFYING
        requirement, so a user's answer can be followed by another round
        of questions ("回答→再问" closed loop).  The flat
        ``clarification_questions`` list accumulates questions across
        rounds for backward compatibility; ``clarification_rounds``
        tracks how many rounds have been asked.

        Args:
            requirement_id: The requirement to append questions to.
            questions: One round of questions (governance R11: <= 3 per round).

        Returns:
            The updated Requirement, now in CLARIFYING status.
        """
        if not questions:
            raise InboxError("questions must not be empty")
        req = self.get(requirement_id)
        req.clarification_questions = list(req.clarification_questions) + [
            str(q) for q in questions
        ]
        req.clarification_rounds += 1
        if req.status == InboxStatus.NEW:
            req.status = InboxStatus.CLARIFYING
        req.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(req)
        return req

    def link_task(self, requirement_id: str, task_id: str) -> Requirement:
        req = self.get(requirement_id)
        if task_id not in req.linked_task_ids:
            req.linked_task_ids = sorted(req.linked_task_ids + [task_id])
        req.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(req)
        return req

    def link_plan(self, requirement_id: str, plan_id: str) -> Requirement:
        req = self.get(requirement_id)
        req.linked_plan_id = plan_id
        req.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(req)
        return req

    def _analyse(self, req: Requirement) -> None:
        try:
            from loop_core.intent_router import analyse_intent
            result = analyse_intent(req.description)
            if result.domains:
                req.tags = result.domains
            req.priority = self._map_risk_to_priority(getattr(result, 'risk_level', 'MEDIUM'))
        except ImportError:
            self._fallback_analyse(req)

    def _fallback_analyse(self, req: Requirement) -> None:
        desc_lower = req.description.lower()
        tags = []
        domain_map = {
            "web": ["html", "css", "javascript", "react", "vue", "frontend", "website"],
            "api": ["api", "rest", "graphql", "endpoint", "backend"],
            "data": ["database", "sql", "migration", "schema"],
            "cli": ["cli", "command", "terminal", "script"],
            "ai_ml": ["ai", "ml", "llm", "model", "training"],
        }
        for domain, keywords in domain_map.items():
            if any(kw in desc_lower for kw in keywords):
                tags.append(domain)
        req.tags = tags

    @staticmethod
    def _map_risk_to_priority(risk_level: str) -> Priority:
        mapping = {"CRITICAL": Priority.P0, "HIGH": Priority.P1, "MEDIUM": Priority.P2, "LOW": Priority.P3}
        return mapping.get(risk_level, Priority.P2)

    def _path_for(self, requirement_id: str) -> Path:
        return self._inbox_dir / f"{requirement_id}.yaml"

    def _save(self, req: Requirement) -> None:
        import yaml
        path = self._path_for(req.requirement_id)
        data = req.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    def _load(self, path: Path) -> Requirement:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise InboxError(f"Invalid requirement file: {path}")
        if "requirement_id" not in data:
            data["requirement_id"] = path.stem
        return Requirement.from_dict(data)

    def _next_id(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        existing = sorted(self._inbox_dir.glob(f"REQ-{today}-*.yaml"))
        if existing:
            nums = [int(p.stem.split("-")[-1]) for p in existing if p.stem.split("-")[-1].isdigit()]
            next_num = max(nums) + 1 if nums else 1
        else:
            next_num = 1
        return f"REQ-{today}-{next_num:03d}"

    @staticmethod
    def _validate_status_transition(current: InboxStatus, new: InboxStatus) -> None:
        allowed = {
            InboxStatus.NEW: {InboxStatus.CLARIFYING, InboxStatus.ACCEPTED, InboxStatus.DECLINED},
            InboxStatus.CLARIFYING: {InboxStatus.ACCEPTED, InboxStatus.DECLINED, InboxStatus.NEW},
            InboxStatus.ACCEPTED: {InboxStatus.PLANNED, InboxStatus.DECLINED},
            InboxStatus.DECLINED: {InboxStatus.NEW},
            InboxStatus.PLANNED: {InboxStatus.ACCEPTED},
        }
        if new not in allowed.get(current, set()):
            raise InboxError(f"Invalid status transition: {current.value} -> {new.value}")


def inbox_summary(project_root: str | Path) -> dict:
    """Return a lightweight inbox summary for the dashboard."""
    inbox = Inbox(project_root)
    all_reqs = inbox.list_all()
    by_status = {}
    for req in all_reqs:
        s = req.status.value
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": len(all_reqs),
        "by_status": by_status,
        "new_count": by_status.get("NEW", 0),
        "clarifying_count": by_status.get("CLARIFYING", 0),
        "accepted_count": by_status.get("ACCEPTED", 0),
        "planned_count": by_status.get("PLANNED", 0),
        "declined_count": by_status.get("DECLINED", 0),
    }
