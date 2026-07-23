"""
Loop Core State Machine — Host-independent phase transitions and gate logic.

This module defines what CAN happen, not HOW it happens. It is called by
the host adapter to validate state transitions before they are executed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    S0_INIT = "S0-init"
    S1_REQUIREMENTS = "S1-requirements"
    S2_ARCHITECTURE = "S2-architecture"
    S3_INTERFACE = "S3-interface"
    S4_IMPLEMENTATION = "S4-implementation"
    S5_QUALITY = "S5-quality"
    S6_DELIVERY = "S6-delivery"
    S7_INTEGRATION = "S7-integration"
    S8_FUNCTIONAL_TEST = "S8-functional-test"
    S9_FIX_OPTIMIZE = "S9-fix-optimize"
    S10_PERFORMANCE = "S10-performance"
    S11_MAINTENANCE = "S11-maintenance"


class GateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    REJECTED = "rejected"


# Phase transition graph: from -> [to]
PHASE_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.S0_INIT: [Phase.S1_REQUIREMENTS],
    Phase.S1_REQUIREMENTS: [Phase.S2_ARCHITECTURE, Phase.S0_INIT],
    Phase.S2_ARCHITECTURE: [Phase.S3_INTERFACE, Phase.S1_REQUIREMENTS],
    Phase.S3_INTERFACE: [Phase.S4_IMPLEMENTATION, Phase.S2_ARCHITECTURE],
    Phase.S4_IMPLEMENTATION: [Phase.S5_QUALITY, Phase.S3_INTERFACE],
    Phase.S5_QUALITY: [Phase.S6_DELIVERY, Phase.S4_IMPLEMENTATION],
    Phase.S6_DELIVERY: [Phase.S7_INTEGRATION, Phase.S5_QUALITY],
    Phase.S7_INTEGRATION: [Phase.S8_FUNCTIONAL_TEST, Phase.S6_DELIVERY],
    Phase.S8_FUNCTIONAL_TEST: [Phase.S9_FIX_OPTIMIZE, Phase.S7_INTEGRATION],
    Phase.S9_FIX_OPTIMIZE: [Phase.S10_PERFORMANCE, Phase.S8_FUNCTIONAL_TEST, Phase.S4_IMPLEMENTATION],
    Phase.S10_PERFORMANCE: [Phase.S11_MAINTENANCE, Phase.S9_FIX_OPTIMIZE],
    Phase.S11_MAINTENANCE: [Phase.S1_REQUIREMENTS],  # Loop back for next iteration
}

# Phases that require independent review
REVIEW_REQUIRED_PHASES = {
    Phase.S4_IMPLEMENTATION,
    Phase.S5_QUALITY,
    Phase.S7_INTEGRATION,
}

# Phases where mini-loop (review -> fix -> re-review) is allowed
MINI_LOOP_PHASES = {
    Phase.S4_IMPLEMENTATION,
    Phase.S9_FIX_OPTIMIZE,
}


@dataclass
class StateValidationResult:
    """Result of validating a state transition."""
    allowed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def can_transition_phase(current: Phase, target: Phase) -> StateValidationResult:
    """Check if a phase transition is allowed."""
    if target not in PHASE_TRANSITIONS.get(current, []):
        return StateValidationResult(
            allowed=False,
            errors=[f"Cannot transition from {current.value} to {target.value}. "
                    f"Allowed transitions: {[p.value for p in PHASE_TRANSITIONS.get(current, [])]}"]
        )
    return StateValidationResult(allowed=True)


def can_approve_gate(
    gate_status: GateStatus,
    role_verdicts: dict[str, str],  # role_id -> "PASS" | "BLOCKED"
    required_roles: list[str],
) -> StateValidationResult:
    """Check if a gate can be approved given role verdicts."""
    errors = []

    if gate_status != GateStatus.PENDING:
        errors.append(f"Gate is not pending (current: {gate_status.value})")

    for role_id in required_roles:
        verdict = role_verdicts.get(role_id)
        if verdict is None:
            errors.append(f"Required role '{role_id}' has not submitted a verdict")
        elif verdict == "BLOCKED":
            errors.append(f"Role '{role_id}' issued BLOCKED — gate cannot be approved")

    return StateValidationResult(
        allowed=len(errors) == 0,
        errors=errors,
    )


def can_enter_phase(
    phase: Phase,
    prev_gate_status: Optional[GateStatus],
    has_blockers: bool,
) -> StateValidationResult:
    """Check if a phase can be entered."""
    errors = []

    if prev_gate_status is not None and prev_gate_status != GateStatus.APPROVED:
        errors.append(f"Previous phase gate is not approved (status: {prev_gate_status.value})")

    if has_blockers:
        errors.append("Unresolved blockers exist — cannot enter new phase")

    return StateValidationResult(
        allowed=len(errors) == 0,
        errors=errors,
    )


def check_self_review(developer_id: Optional[str], reviewer_id: Optional[str]) -> StateValidationResult:
    """Check that developer and reviewer are different agents."""
    if developer_id and reviewer_id and developer_id == reviewer_id:
        return StateValidationResult(
            allowed=False,
            errors=[f"SELF_REVIEW_VIOLATION: Same agent ({developer_id}) is both developer and reviewer"]
        )
    return StateValidationResult(allowed=True)
