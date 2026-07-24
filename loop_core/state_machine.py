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


class ProjectStatus(str, Enum):
    """Project lifecycle status (v3.1 — iteration support)."""
    DRAFT = "draft"           # Unpublished — free to modify
    RELEASED = "released"     # Published (git tag) — changes require full process
    MAINTENANCE = "maintenance"  # In maintenance mode


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

# Reentry transitions: allowed entry points from any completed project (v3.1)
# These enable change iteration without requiring the full transition graph.
REENTRY_TRANSITIONS: dict[str, set[Phase]] = {
    "bug_fix":             {Phase.S9_FIX_OPTIMIZE, Phase.S4_IMPLEMENTATION},
    "feature_add":         {Phase.S4_IMPLEMENTATION},
    "refactor":            {Phase.S4_IMPLEMENTATION},
    "requirement_change":  {Phase.S1_REQUIREMENTS},
    "quality_fix":         {Phase.S5_QUALITY, Phase.S9_FIX_OPTIMIZE},
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
    reentry: bool = False,
) -> StateValidationResult:
    """Check if a phase can be entered.

    When reentry=True (v3.1), skips the previous-gate approval check
    because we're re-entering from a completed project, not advancing
    linearly through the phase graph.
    """
    errors = []

    if not reentry:
        if prev_gate_status is not None and prev_gate_status != GateStatus.APPROVED:
            errors.append(f"Previous phase gate is not approved (status: {prev_gate_status.value})")

    if has_blockers:
        errors.append("Unresolved blockers exist — cannot enter new phase")

    return StateValidationResult(
        allowed=len(errors) == 0,
        errors=errors,
    )


def validate_reentry(
    entry_phase: Phase,
    change_type: str,
    project_status: str = "draft",
) -> StateValidationResult:
    """Validate that a reentry into entry_phase is allowed for the given change_type.

    Args:
        entry_phase: The target phase to re-enter.
        change_type: One of bug_fix/feature_add/refactor/requirement_change/quality_fix.
        project_status: draft/released/maintenance (from ProjectStatus).

    Returns:
        StateValidationResult with errors if reentry is not allowed.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check if entry_phase is in the allowed reentry set for this change type
    allowed_phases = REENTRY_TRANSITIONS.get(change_type, set())
    if not allowed_phases:
        errors.append(f"Unknown change_type '{change_type}' — no reentry transitions defined")
    elif entry_phase not in allowed_phases:
        errors.append(
            f"Cannot re-enter {entry_phase.value} for change_type '{change_type}'. "
            f"Allowed: {[p.value for p in allowed_phases]}"
        )

    # Released projects have stricter rules
    if project_status == ProjectStatus.RELEASED.value:
        if change_type in ("bug_fix", "quality_fix"):
            # Allowed — these are maintenance operations
            pass
        elif change_type in ("requirement_change",):
            warnings.append(
                "RELEASED project: requirement changes should go through "
                "full iteration loop (S1→S6) with user gate at each phase."
            )
        elif change_type in ("feature_add", "refactor"):
            warnings.append(
                "RELEASED project: feature additions and refactors require "
                "independent review and full quality gate pass."
            )

    return StateValidationResult(
        allowed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def check_self_review(developer_id: Optional[str], reviewer_id: Optional[str]) -> StateValidationResult:
    """Check that developer and reviewer are different agents."""
    if developer_id and reviewer_id and developer_id == reviewer_id:
        return StateValidationResult(
            allowed=False,
            errors=[f"SELF_REVIEW_VIOLATION: Same agent ({developer_id}) is both developer and reviewer"]
        )
    return StateValidationResult(allowed=True)


# ── Role Isolation ─────────────────────────────────────────────────────


@dataclass
class RoleIsolationCheck:
    """Check that Developer and Reviewer have true context isolation.

    The Reviewer must review a frozen snapshot of the Developer's output,
    not the Developer's live context. This ensures independence.
    """
    developer_actor_id: str | None
    reviewer_actor_id: str | None
    developer_session_id: str | None
    reviewer_session_id: str | None
    developer_input_fingerprint: str | None
    reviewer_input_fingerprint: str | None


def check_role_isolation(check: RoleIsolationCheck) -> StateValidationResult:
    """Validate role isolation across three dimensions.

    - actor_id must differ (different agent/identity)
    - session_id must differ (different session/context window)
    - input_fingerprint must differ (Reviewer sees frozen snapshot, not live context)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check 1: actor_id must differ
    if check.developer_actor_id is not None and check.reviewer_actor_id is not None:
        if check.developer_actor_id == check.reviewer_actor_id:
            errors.append(
                f"ROLE_ISOLATION_ACTOR: Same actor_id ({check.developer_actor_id}) "
                "used for both Developer and Reviewer roles"
            )
    elif check.developer_actor_id is None or check.reviewer_actor_id is None:
        warnings.append("ROLE_ISOLATION_INCOMPLETE: One or both actor_ids are None — "
                        "cannot verify actor isolation")

    # Check 2: session_id must differ
    if check.developer_session_id is not None and check.reviewer_session_id is not None:
        if check.developer_session_id == check.reviewer_session_id:
            errors.append(
                "ROLE_ISOLATION_SESSION: Same session_id used for both Developer "
                "and Reviewer — Reviewer must operate in an independent session"
            )
    elif check.developer_session_id is None or check.reviewer_session_id is None:
        warnings.append("ROLE_ISOLATION_INCOMPLETE: One or both session_ids are None — "
                        "cannot verify session isolation")

    # Check 3: input_fingerprint must differ
    if check.developer_input_fingerprint is not None and check.reviewer_input_fingerprint is not None:
        if check.developer_input_fingerprint == check.reviewer_input_fingerprint:
            errors.append(
                "ROLE_ISOLATION_INPUT: Same input_fingerprint for Developer and Reviewer "
                "— Reviewer must review a frozen snapshot, not the Developer's live context"
            )
    elif check.developer_input_fingerprint is None or check.reviewer_input_fingerprint is None:
        warnings.append("ROLE_ISOLATION_INCOMPLETE: One or both input_fingerprints are None — "
                        "cannot verify input isolation")

    return StateValidationResult(
        allowed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ── Gate Cross-Validation (P0-E Deadlock Fix) ──────────────────────────


def resolve_gate_status(current_gate_id: str | None,
                        gates: list[dict]) -> GateStatus | None:
    """Cross-validate current_gate_id against the authoritative gates list.

    This is the core fix for P0-E deadlock: instead of unconditionally
    trusting current_gate_id (which may be stale), we cross-reference it
    with the gates list from gates.yaml.

    Args:
        current_gate_id: The gate ID from state.yaml (may be stale or None).
        gates: The authoritative list of gate dicts from gates.yaml.
               Each dict must have at least "id" (str) and "status" (str).

    Returns:
        - None if current_gate_id is None.
        - None if the gate ID does not exist in the gates list (with warning).
        - The actual GateStatus if the gate exists (PENDING or resolved).
    """
    if current_gate_id is None:
        return None

    # Find the gate by ID in the authoritative list
    matching_gate: dict | None = None
    for gate in gates:
        if gate.get("id") == current_gate_id:
            matching_gate = gate
            break

    if matching_gate is None:
        # Gate ID points to a non-existent gate — stale reference
        import warnings as _warnings
        _warnings.warn(
            f"STALE_GATE_REFERENCE: current_gate_id '{current_gate_id}' "
            f"does not match any gate in the authoritative gates list. "
            f"This may indicate a stale state.yaml reference that needs cleanup."
        )
        return None

    raw_status = matching_gate.get("status", "pending")
    try:
        return GateStatus(raw_status)
    except ValueError:
        # Unknown status string — treat as PENDING to be safe
        return GateStatus.PENDING


# ── Phase Constraints ──────────────────────────────────────────────────


@dataclass
class PhaseConstraint:
    """A precondition that must be satisfied before entering a phase.

    Constraint IDs correspond to the conceptual ConstraintID namespace
    from HardConstraints (see hard_constraints.py for full definitions).
    """
    constraint_id: str          # e.g. "C1-no-requirements"
    phase: Phase                # The phase this constraint applies to
    description: str
    blocker: bool = True        # True = blocks phase entry; False = warning only


# Precondition constraints for each phase.
# These encode the hard dependency rules: you cannot enter implementation
# without requirements, cannot deliver without verification, etc.
PHASE_CONSTRAINTS: dict[Phase, list[PhaseConstraint]] = {
    Phase.S1_REQUIREMENTS: [
        PhaseConstraint(
            "C0-no-init", Phase.S1_REQUIREMENTS,
            "Project must be initialised (S0-init completed)",
        ),
    ],
    Phase.S2_ARCHITECTURE: [
        PhaseConstraint(
            "C1-no-requirements", Phase.S2_ARCHITECTURE,
            "Requirements baseline required (S1-requirements gate approved)",
        ),
    ],
    Phase.S3_INTERFACE: [
        PhaseConstraint(
            "C2-no-architecture", Phase.S3_INTERFACE,
            "Architecture baseline required (S2-architecture gate approved)",
        ),
    ],
    Phase.S4_IMPLEMENTATION: [
        PhaseConstraint(
            "C1-no-requirements", Phase.S4_IMPLEMENTATION,
            "Requirements baseline required (S1-requirements gate approved)",
        ),
        PhaseConstraint(
            "C2-no-architecture", Phase.S4_IMPLEMENTATION,
            "Architecture baseline required (S2-architecture gate approved)",
        ),
        PhaseConstraint(
            "C3-no-task-package", Phase.S4_IMPLEMENTATION,
            "Task package required (task_graph.yaml has at least one active task)",
        ),
    ],
    Phase.S5_QUALITY: [
        PhaseConstraint(
            "C4-no-implementation", Phase.S5_QUALITY,
            "Implementation baseline required (S4-implementation gate approved)",
        ),
    ],
    Phase.S6_DELIVERY: [
        PhaseConstraint(
            "C5-no-verification", Phase.S6_DELIVERY,
            "Deterministic verification required (tests/lint/build all pass)",
        ),
        PhaseConstraint(
            "C6-no-independent-review", Phase.S6_DELIVERY,
            "Independent review required (independent-reviewer verdict is PASS)",
        ),
        PhaseConstraint(
            "C7-blocker-exists", Phase.S6_DELIVERY,
            "No unresolved blockers allowed (gate/task status must not be blocked)",
        ),
    ],
    Phase.S7_INTEGRATION: [
        PhaseConstraint(
            "C8-no-delivery-approval", Phase.S7_INTEGRATION,
            "Delivery approval required (S6-delivery gate approved)",
        ),
    ],
    Phase.S8_FUNCTIONAL_TEST: [
        PhaseConstraint(
            "C9-no-integration", Phase.S8_FUNCTIONAL_TEST,
            "Integration baseline required (S7-integration gate approved)",
        ),
    ],
    Phase.S9_FIX_OPTIMIZE: [
        PhaseConstraint(
            "C10-no-functional-test", Phase.S9_FIX_OPTIMIZE,
            "Functional test results required (S8-functional-test gate approved or feedback recorded)",
            blocker=False,  # Fix phase can be entered with warnings from tests
        ),
    ],
    Phase.S10_PERFORMANCE: [
        PhaseConstraint(
            "C11-no-fix-verification", Phase.S10_PERFORMANCE,
            "Fix verification required (S9-fix-optimize gate approved)",
        ),
    ],
    Phase.S11_MAINTENANCE: [
        PhaseConstraint(
            "C12-no-performance-baseline", Phase.S11_MAINTENANCE,
            "Performance baseline required (S10-performance gate approved)",
        ),
    ],
}


def get_constraints_for_phase(phase: Phase) -> list[PhaseConstraint]:
    """Return all constraints for a given phase, or empty list if none defined."""
    return PHASE_CONSTRAINTS.get(phase, [])


def get_blocker_constraints(phase: Phase) -> list[PhaseConstraint]:
    """Return only blocker (blocking) constraints for a given phase."""
    return [c for c in get_constraints_for_phase(phase) if c.blocker]


def check_phase_constraints(
    phase: Phase,
    approved_gate_ids: set[str],
    task_has_active: bool = False,
    verification_passed: bool = False,
) -> StateValidationResult:
    """Check whether all constraints for a phase are satisfied.

    Args:
        phase: The target phase to enter.
        approved_gate_ids: Set of gate IDs that have been approved.
        task_has_active: Whether task_graph.yaml has at least one active task.
        verification_passed: Whether deterministic verification (tests/lint/build) passed.

    Returns:
        StateValidationResult with errors for each unsatisfied blocker constraint.
    """
    constraints = get_constraints_for_phase(phase)
    errors: list[str] = []
    warnings: list[str] = []

    for constraint in constraints:
        satisfied = _check_single_constraint(
            constraint, approved_gate_ids, task_has_active, verification_passed
        )
        if not satisfied:
            msg = f"Constraint '{constraint.constraint_id}' not satisfied: {constraint.description}"
            if constraint.blocker:
                errors.append(msg)
            else:
                warnings.append(msg)

    return StateValidationResult(
        allowed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _check_single_constraint(
    constraint: PhaseConstraint,
    approved_gate_ids: set[str],
    task_has_active: bool,
    verification_passed: bool,
) -> bool:
    """Evaluate a single constraint against the provided state."""
    cid = constraint.constraint_id

    # Gate-based constraints — map constraint ID to required gate ID pattern
    gate_constraint_map: dict[str, str] = {
        "C0-no-init":              "S0-init",
        "C1-no-requirements":      "S1-requirements",
        "C2-no-architecture":      "S2-architecture",
        "C4-no-implementation":    "S4-implementation",
        "C8-no-delivery-approval": "S6-delivery",
        "C9-no-integration":       "S7-integration",
        "C10-no-functional-test":  "S8-functional-test",
        "C11-no-fix-verification": "S9-fix-optimize",
        "C12-no-performance-baseline": "S10-performance",
    }

    if cid in gate_constraint_map:
        required = gate_constraint_map[cid]
        # Check if any approved gate ID contains the required phase prefix
        return any(required in gate_id for gate_id in approved_gate_ids)

    if cid == "C3-no-task-package":
        return task_has_active

    if cid == "C5-no-verification":
        return verification_passed

    if cid == "C6-no-independent-review":
        return "independent-review" in approved_gate_ids or any(
            "independent-review" in gid for gid in approved_gate_ids
        )

    if cid == "C7-blocker-exists":
        # This is checked externally — if we're calling this, assume no blockers
        # (the caller should have already verified this)
        return True

    # Unknown constraint — warn but don't block
    return True
