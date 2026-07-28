from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codex_loop.core.contracts import RoleRegistry
from codex_loop.planning.graph import TaskGraph, TaskNode
from codex_loop.planning.phases import default_phases


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: str
    message: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.check_id, "status": self.status, "message": self.message, "evidence": list(self.evidence)}


def check_role_registry(registry: RoleRegistry) -> CheckResult:
    isolation_errors = registry.validate_isolation()
    if isolation_errors:
        return CheckResult("role_registry", "FAIL", "; ".join(isolation_errors))
    return CheckResult("role_registry", "PASS", f"validated {len(registry.roles)} role contracts")


def check_role_prompts(registry: RoleRegistry) -> CheckResult:
    markers = ("只做：", "禁止：", "必须输出：", "交接：")
    errors = [
        f"{role.role_id} prompt missing {marker}"
        for role in registry.roles
        for marker in markers
        if marker not in role.prompt_text()
    ]
    if errors:
        return CheckResult("role_prompts", "FAIL", "; ".join(errors))
    return CheckResult("role_prompts", "PASS", f"validated bounded prompt markers for {len(registry.roles)} roles")


def check_task_graph(graph: TaskGraph) -> CheckResult:
    try:
        graph.validate()
    except ValueError as exc:
        return CheckResult("task_graph", "FAIL", str(exc))
    return CheckResult("task_graph", "PASS", f"validated {len(graph.nodes)} tasks")


def check_phase_transition(
    internal_checks: tuple[CheckResult, ...],
    user_decision: str | None,
    user_gate_required: bool,
) -> CheckResult:
    failed = [result.check_id for result in internal_checks if result.status != "PASS"]
    if failed:
        return CheckResult("phase_transition", "BLOCKED", f"internal checks not passed: {', '.join(failed)}")
    if user_gate_required and user_decision != "approve":
        return CheckResult("phase_transition", "USER_DECISION_REQUIRED", "user phase decision is not approved")
    return CheckResult("phase_transition", "PASS", "phase may advance under current policy")


def check_required_mapping(payload: dict[str, Any], required: tuple[str, ...], check_id: str) -> CheckResult:
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return CheckResult(check_id, "FAIL", f"missing required sections: {', '.join(missing)}")
    return CheckResult(check_id, "PASS", "required sections are present")


def check_candidate_store(loop_root: Path) -> CheckResult:
    errors: list[str] = []
    try:
        project = json.loads((loop_root / "project.json").read_text(encoding="utf-8"))
        if project.get("host") != "codex":
            errors.append("project host must be codex")
        phases = json.loads((loop_root / "phases/default.json").read_text(encoding="utf-8"))
        if len(phases.get("phases", [])) != len(default_phases()):
            errors.append("phase profile is incomplete")
        raw_graph = json.loads((loop_root / "tasks/default-graph.json").read_text(encoding="utf-8"))
        graph = TaskGraph()
        for raw in raw_graph.get("nodes", []):
            graph.add(TaskNode(**raw))
        graph.validate()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"store structure invalid: {exc}")
    for path in (loop_root / "packets/functional").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if text.count("## ") < 7 or "Feature ID:" not in text:
            errors.append(f"functional packet incomplete: {path.name}")
    for path in (loop_root / "packets/review").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "approve" not in text or "repair" not in text or "reject" not in text:
            errors.append(f"human review packet incomplete: {path.name}")
    if errors:
        return CheckResult("candidate_store", "FAIL", "; ".join(errors))
    return CheckResult("candidate_store", "PASS", f"validated Codex store at {loop_root}")
