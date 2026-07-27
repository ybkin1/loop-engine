from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkPacket:
    packet_id: str
    task_id: str
    phase_id: str
    role_id: str
    purpose: str
    inputs: tuple[str, ...] = ()
    selected_materials: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    allowed_read: tuple[str, ...] = ()
    allowed_write: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    context_budget_tokens: int = 1200

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoleRunEnvelope:
    run_id: str
    role_id: str
    role_version: str
    task_id: str
    phase_id: str
    input_fingerprints: dict[str, str] = field(default_factory=dict)
    tool_preflight: dict[str, Any] = field(default_factory=dict)
    permission_preflight: dict[str, Any] = field(default_factory=dict)
    capability_probe: dict[str, Any] = field(default_factory=dict)
    output_artifacts: list[str] = field(default_factory=list)
    deterministic_checks: list[dict[str, Any]] = field(default_factory=list)
    independent_verification: list[str] = field(default_factory=list)
    vetoes_or_abstentions: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    verdict: str = "NOT_ASSESSED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectOverlay:
    project_id: str
    goal: str
    risk_tier: str
    delivery_target: str
    technology_baseline: tuple[str, ...] = ()
    user_decisions: tuple[str, ...] = ()
    current_constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectProfile:
    project_id: str
    goal: str
    risk_tier: str = "medium"
    delivery_target: str = "candidate"
    host: str = "codex"
    technology_baseline: tuple[str, ...] = ()
    selected_materials: tuple[str, ...] = ()

    def to_overlay(self) -> ProjectOverlay:
        return ProjectOverlay(
            project_id=self.project_id,
            goal=self.goal,
            risk_tier=self.risk_tier,
            delivery_target=self.delivery_target,
            technology_baseline=self.technology_baseline,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
