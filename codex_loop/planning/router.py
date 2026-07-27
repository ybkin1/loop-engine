from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LoopMode(str, Enum):
    LIGHTWEIGHT = "lightweight"
    STANDARD = "standard"
    FULL = "full"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProjectProfile:
    description: str = ""
    has_multiple_modules: bool = False
    has_database: bool = False
    has_auth_permissions: bool = False
    has_payments: bool = False
    has_production_data: bool = False
    has_external_api: bool = False
    has_concurrency_performance: bool = False
    has_security_requirements: bool = False
    requires_deployment: bool = False
    requires_monitoring_rollback: bool = False
    requires_ongoing_iteration: bool = False
    has_high_uncertainty: bool = False
    user_forced_mode: LoopMode | None = None

    def risk_level(self) -> RiskLevel:
        high_risk_flags = sum([self.has_database, self.has_auth_permissions, self.has_payments, self.has_production_data, self.has_security_requirements])
        medium_risk_flags = sum([self.has_multiple_modules, self.has_external_api, self.has_concurrency_performance, self.requires_deployment, self.requires_monitoring_rollback, self.requires_ongoing_iteration, self.has_high_uncertainty])
        if high_risk_flags >= 2:
            return RiskLevel.CRITICAL
        if high_risk_flags >= 1 or medium_risk_flags >= 3:
            return RiskLevel.HIGH
        if medium_risk_flags >= 1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def route(self) -> LoopMode:
        risk = self.risk_level()
        minimum = LoopMode.FULL if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) else (LoopMode.STANDARD if risk == RiskLevel.MEDIUM else LoopMode.LIGHTWEIGHT)
        if self.user_forced_mode is None:
            return minimum
        order = {LoopMode.LIGHTWEIGHT: 0, LoopMode.STANDARD: 1, LoopMode.FULL: 2}
        return self.user_forced_mode if order[self.user_forced_mode] >= order[minimum] else minimum


@dataclass
class RouteResult:
    mode: LoopMode
    risk_level: RiskLevel
    reason: str
    recommended_phases: list[str] = field(default_factory=list)


def route_intent(profile: ProjectProfile) -> RouteResult:
    mode = profile.route()
    risk = profile.risk_level()
    from codex_loop.core.state_machine import Phase
    if mode == LoopMode.LIGHTWEIGHT:
        phases = ["S0-init", "S4-implementation", "S6-delivery"]
        reason = "Low-risk task: minimal ceremony, single agent, basic checks only."
    elif mode == LoopMode.STANDARD:
        phases = ["S0-init", "S1-requirements", "S2-architecture", "S4-implementation", "S5-quality", "S6-delivery"]
        reason = "Moderate project: core Loop phases with architecture and quality gates."
    else:
        phases = [p.value for p in Phase]
        reason = f"High-risk project (level: {risk.value}): complete 12-phase Loop with all gates."
    return RouteResult(mode=mode, risk_level=risk, reason=reason, recommended_phases=phases)

