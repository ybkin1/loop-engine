"""
Loop Core Router — Project classification and Loop routing.

Determines whether a user intent should enter lightweight or full Loop,
based on risk factors. Host-independent decision logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LoopMode(str, Enum):
    LIGHTWEIGHT = "lightweight"  # Simple task, single agent, minimal ceremony
    STANDARD = "standard"        # Moderate project, basic Loop phases
    FULL = "full"                # High-risk project, complete 12-phase Loop


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProjectProfile:
    """Profile of a user intent, used to determine Loop routing."""
    description: str = ""

    # Risk factors
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

    # Explicit overrides
    user_forced_mode: LoopMode | None = None

    def risk_level(self) -> RiskLevel:
        """Calculate risk level from profile factors."""
        high_risk_flags = sum([
            self.has_database,
            self.has_auth_permissions,
            self.has_payments,
            self.has_production_data,
            self.has_security_requirements,
        ])
        medium_risk_flags = sum([
            self.has_multiple_modules,
            self.has_external_api,
            self.has_concurrency_performance,
            self.requires_deployment,
            self.requires_monitoring_rollback,
            self.requires_ongoing_iteration,
            self.has_high_uncertainty,
        ])

        if high_risk_flags >= 2:
            return RiskLevel.CRITICAL
        if high_risk_flags >= 1 or medium_risk_flags >= 3:
            return RiskLevel.HIGH
        if medium_risk_flags >= 1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def route(self) -> LoopMode:
        """Determine which Loop mode to use."""
        if self.user_forced_mode:
            return self.user_forced_mode

        risk = self.risk_level()
        if risk == RiskLevel.CRITICAL:
            return LoopMode.FULL
        if risk == RiskLevel.HIGH:
            return LoopMode.FULL
        if risk == RiskLevel.MEDIUM:
            return LoopMode.STANDARD
        return LoopMode.LIGHTWEIGHT


@dataclass
class RouteResult:
    """Result of Loop routing decision."""
    mode: LoopMode
    risk_level: RiskLevel
    reason: str
    recommended_phases: list[str] = field(default_factory=list)


def route_intent(profile: ProjectProfile) -> RouteResult:
    """Route a user intent to the appropriate Loop mode."""
    mode = profile.route()
    risk = profile.risk_level()

    if mode == LoopMode.LIGHTWEIGHT:
        phases = ["S0-init", "S4-implementation", "S6-delivery"]
        reason = "Low-risk task: minimal ceremony, single agent, basic checks only."
    elif mode == LoopMode.STANDARD:
        phases = ["S0-init", "S1-requirements", "S2-architecture", "S4-implementation", "S5-quality", "S6-delivery"]
        reason = "Moderate project: core Loop phases with architecture and quality gates."
    else:
        phases = [
            "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
            "S4-implementation", "S5-quality", "S6-delivery",
            "S7-integration", "S8-functional-test", "S9-fix-optimize",
            "S10-performance", "S11-maintenance",
        ]
        reason = f"High-risk project (level: {risk.value}): complete 12-phase Loop with all gates."

    return RouteResult(mode=mode, risk_level=risk, reason=reason, recommended_phases=[str(p) for p in phases])
