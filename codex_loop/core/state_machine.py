"""
Loop Core State Machine -- Host-independent phase transitions and gate logic.

Adapted from zcode loop-engine v3.0.0 loop_core/state_machine.py for Codex.
Import paths adjusted for codex_loop package.
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
    DRAFT = "draft"
    RELEASED = "released"
    MAINTENANCE = "maintenance"


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
    Phase.S11_MAINTENANCE: [Phase.S1_REQUIREMENTS],
}

REENTRY_TRANSITIONS: dict[str, set[Phase]] = {
    "bug_fix":             {Phase.S9_FIX_OPTIMIZE, Phase.S4_IMPLEMENTATION},
    "feature_add":         {Phase.S4_IMPLEMENTATION},
    "refactor":            {Phase.S4_IMPLEMENTATION},
    "requirement_change":  {Phase.S1_REQUIREMENTS},
    "quality_fix":         {Phase.S5_QUALITY, Phase.S9_FIX_OPTIMIZE},
}

REVIEW_REQUIRED_PHASES = {
    Phase.S4_IMPLEMENTATION,
    Phase.S5_QUALITY,
    Phase.S7_INTEGRATION,
}

# Phases requiring explicit user gate approval
USER_GATE_PHASES = {
    Phase.S1_REQUIREMENTS,
    Phase.S6_DELIVERY,
}

MINI_LOOP_PHASES = {
    Phase.S4_IMPLEMENTATION,
    Phase.S9_FIX_OPTIMIZE,
}


@dataclass
class StateValidationResult:
    allowed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def can_transition_phase(current: Phase, target: Phase) -> StateValidationResult:
    if target not in PHASE_TRANSITIONS.get(current, []):
        return StateValidationResult(
            allowed=False,
            errors=[f"Cannot transition from {current.value} to {target.value}. "
                    f"Allowed transitions: {[p.value for p in PHASE_TRANSITIONS.get(current, [])]}"])
    return StateValidationResult(allowed=True)


def can_approve_gate(
    gate_status: GateStatus,
    role_verdicts: dict[str, str],
    required_roles: list[str],
) -> StateValidationResult:
    errors = []
    if gate_status != GateStatus.PENDING:
        errors.append(f"Gate is not pending (current: {gate_status.value})")
    for role_id in required_roles:
        verdict = role_verdicts.get(role_id)
        if verdict is None:
            errors.append(f"Required role '{role_id}' has not submitted a verdict")
        elif verdict == "BLOCKED":
            errors.append(f"Role '{role_id}' issued BLOCKED -- gate cannot be approved")
    return StateValidationResult(allowed=len(errors) == 0, errors=errors)


def can_enter_phase(
    phase: Phase,
    prev_gate_status: Optional[GateStatus],
    has_blockers: bool,
    reentry: bool = False,
) -> StateValidationResult:
    errors = []
    if not reentry:
        if prev_gate_status is not None and prev_gate_status != GateStatus.APPROVED:
            errors.append(f"Previous phase gate is not approved (status: {prev_gate_status.value})")
    if has_blockers:
        errors.append("Unresolved blockers exist -- cannot enter new phase")
    return StateValidationResult(allowed=len(errors) == 0, errors=errors)


def validate_reentry(
    entry_phase: Phase,
    change_type: str,
    project_status: str = "draft",
) -> StateValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    allowed_phases = REENTRY_TRANSITIONS.get(change_type, set())
    if not allowed_phases:
        errors.append(f"Unknown change_type '{change_type}' -- no reentry transitions defined")
    elif entry_phase not in allowed_phases:
        errors.append(
            f"Cannot re-enter {entry_phase.value} for change_type '{change_type}'. "
            f"Allowed: {[p.value for p in allowed_phases]}")
    if project_status == ProjectStatus.RELEASED.value:
        if change_type in ("bug_fix", "quality_fix"):
            pass
        elif change_type in ("requirement_change",):
            warnings.append("RELEASED project: requirement changes should go through full iteration loop (S1->S6)")
        elif change_type in ("feature_add", "refactor"):
            warnings.append("RELEASED project: feature additions and refactors require independent review and full quality gate pass")
    return StateValidationResult(allowed=len(errors) == 0, errors=errors, warnings=warnings)


def check_self_review(developer_id: Optional[str], reviewer_id: Optional[str]) -> StateValidationResult:
    if developer_id and reviewer_id and developer_id == reviewer_id:
        return StateValidationResult(
            allowed=False,
            errors=[f"SELF_REVIEW_VIOLATION: Same agent ({developer_id}) is both developer and reviewer"])
    return StateValidationResult(allowed=True)


@dataclass
class RoleIsolationCheck:
    developer_actor_id: str | None
    reviewer_actor_id: str | None
    developer_session_id: str | None
    reviewer_session_id: str | None
    developer_input_fingerprint: str | None
    reviewer_input_fingerprint: str | None


def check_role_isolation(check: RoleIsolationCheck) -> StateValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if check.developer_actor_id is not None and check.reviewer_actor_id is not None:
        if check.developer_actor_id == check.reviewer_actor_id:
            errors.append(f"ROLE_ISOLATION_ACTOR: Same actor_id ({check.developer_actor_id}) used for both Developer and Reviewer roles")
    elif check.developer_actor_id is None or check.reviewer_actor_id is None:
        warnings.append("ROLE_ISOLATION_INCOMPLETE: One or both actor_ids are None")
    if check.developer_session_id is not None and check.reviewer_session_id is not None:
        if check.developer_session_id == check.reviewer_session_id:
            errors.append("ROLE_ISOLATION_SESSION: Same session_id used for both Developer and Reviewer")
    elif check.developer_session_id is None or check.reviewer_session_id is None:
        warnings.append("ROLE_ISOLATION_INCOMPLETE: One or both session_ids are None")
    if check.developer_input_fingerprint is not None and check.reviewer_input_fingerprint is not None:
        if check.developer_input_fingerprint == check.reviewer_input_fingerprint:
            errors.append("ROLE_ISOLATION_INPUT: Same input_fingerprint for Developer and Reviewer")
    elif check.developer_input_fingerprint is None or check.reviewer_input_fingerprint is None:
        warnings.append("ROLE_ISOLATION_INCOMPLETE: One or both input_fingerprints are None")
    return StateValidationResult(allowed=len(errors) == 0, errors=errors, warnings=warnings)


def resolve_gate_status(current_gate_id: str | None, gates: list[dict]) -> GateStatus | None:
    if current_gate_id is None:
        return None
    matching_gate: dict | None = None
    for gate in gates:
        if gate.get("id") == current_gate_id:
            matching_gate = gate
            break
    if matching_gate is None:
        import warnings as _warnings
        _warnings.warn(f"STALE_GATE_REFERENCE: current_gate_id '{current_gate_id}' does not match any gate")
        return None
    raw_status = matching_gate.get("status", "pending")
    try:
        return GateStatus(raw_status)
    except ValueError:
        return GateStatus.PENDING


@dataclass
class PhaseConstraint:
    constraint_id: str
    phase: Phase
    description: str
    blocker: bool = True


PHASE_CONSTRAINTS: dict[Phase, list[PhaseConstraint]] = {
    Phase.S1_REQUIREMENTS: [
        PhaseConstraint("C0-no-init", Phase.S1_REQUIREMENTS, "Project must be initialised (S0-init completed)"),
    ],
    Phase.S2_ARCHITECTURE: [
        PhaseConstraint("C1-no-requirements", Phase.S2_ARCHITECTURE, "Requirements baseline required"),
    ],
    Phase.S3_INTERFACE: [
        PhaseConstraint("C2-no-architecture", Phase.S3_INTERFACE, "Architecture baseline required"),
    ],
    Phase.S4_IMPLEMENTATION: [
        PhaseConstraint("C1-no-requirements", Phase.S4_IMPLEMENTATION, "Requirements baseline required"),
        PhaseConstraint("C2-no-architecture", Phase.S4_IMPLEMENTATION, "Architecture baseline required"),
        PhaseConstraint("C3-no-task-package", Phase.S4_IMPLEMENTATION, "Task package required"),
    ],
    Phase.S5_QUALITY: [
        PhaseConstraint("C4-no-implementation", Phase.S5_QUALITY, "Implementation baseline required"),
        PhaseConstraint("C15-compile-check", Phase.S5_QUALITY, "Compile check must pass"),
    ],
    Phase.S6_DELIVERY: [
        PhaseConstraint("C5-no-verification", Phase.S6_DELIVERY, "Deterministic verification required"),
        PhaseConstraint("C6-no-independent-review", Phase.S6_DELIVERY, "Independent review required"),
        PhaseConstraint("C7-blocker-exists", Phase.S6_DELIVERY, "No unresolved blockers allowed"),
    ],
    Phase.S7_INTEGRATION: [
        PhaseConstraint("C8-no-delivery-approval", Phase.S7_INTEGRATION, "Delivery approval required"),
    ],
    Phase.S8_FUNCTIONAL_TEST: [
        PhaseConstraint("C9-no-integration", Phase.S8_FUNCTIONAL_TEST, "Integration baseline required"),
    ],
    Phase.S9_FIX_OPTIMIZE: [
        PhaseConstraint("C10-no-functional-test", Phase.S9_FIX_OPTIMIZE, "Functional test results required", blocker=False),
    ],
    Phase.S10_PERFORMANCE: [
        PhaseConstraint("C11-no-fix-verification", Phase.S10_PERFORMANCE, "Fix verification required"),
    ],
    Phase.S11_MAINTENANCE: [
        PhaseConstraint("C12-no-performance-baseline", Phase.S11_MAINTENANCE, "Performance baseline required"),
    ],
}


def get_constraints_for_phase(phase: Phase) -> list[PhaseConstraint]:
    return PHASE_CONSTRAINTS.get(phase, [])


def get_blocker_constraints(phase: Phase) -> list[PhaseConstraint]:
    return [c for c in get_constraints_for_phase(phase) if c.blocker]


def phase_needs_user_gate(phase):
    """True if this phase requires a user gate, not just internal role verdicts."""
    return phase in USER_GATE_PHASES


def check_phase_constraints(
    phase: Phase,
    approved_gate_ids: set[str],
    task_has_active: bool = False,
    verification_passed: bool = False,
    compile_passed: bool = False,
) -> StateValidationResult:
    constraints = get_constraints_for_phase(phase)
    errors: list[str] = []
    warnings: list[str] = []
    for constraint in constraints:
        satisfied = _check_single_constraint(constraint, approved_gate_ids, task_has_active, verification_passed, compile_passed)
        if not satisfied:
            msg = f"Constraint '{constraint.constraint_id}' not satisfied: {constraint.description}"
            if constraint.blocker:
                errors.append(msg)
            else:
                warnings.append(msg)
    return StateValidationResult(allowed=len(errors) == 0, errors=errors, warnings=warnings)


def _check_single_constraint(
    constraint: PhaseConstraint,
    approved_gate_ids: set[str],
    task_has_active: bool,
    verification_passed: bool,
    compile_passed: bool = False,
) -> bool:
    cid = constraint.constraint_id
    gate_constraint_map: dict[str, str] = {
        "C0-no-init": "S0-init", "C1-no-requirements": "S1-requirements",
        "C2-no-architecture": "S2-architecture", "C4-no-implementation": "S4-implementation",
        "C8-no-delivery-approval": "S6-delivery", "C9-no-integration": "S7-integration",
        "C10-no-functional-test": "S8-functional-test", "C11-no-fix-verification": "S9-fix-optimize",
        "C12-no-performance-baseline": "S10-performance",
    }
    if cid in gate_constraint_map:
        required = gate_constraint_map[cid]
        return any(required in gate_id for gate_id in approved_gate_ids)
    if cid == "C3-no-task-package":
        return task_has_active
    if cid == "C5-no-verification":
        return verification_passed
    if cid == "C6-no-independent-review":
        return "independent-review" in approved_gate_ids or any("independent-review" in gid for gid in approved_gate_ids)
    if cid == "C7-blocker-exists":
        return True
    if cid == "C15-compile-check":
        return compile_passed
    return True


def atomic_write_state(root: str, state: dict) -> None:
    import os
    from pathlib import Path as _Path
    root_p = _Path(root)
    state_path = root_p / ".ai" / "state.yaml"
    tmp_path = root_p / ".ai" / "state.yaml.tmp"
    import yaml
    tmp_path.write_text(yaml.dump(state, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    os.replace(str(tmp_path), str(state_path))


@dataclass
class GateCondition:
    condition_id: str
    type: str
    description: str
    params: dict = field(default_factory=dict)


def evaluate_condition(
    condition: GateCondition,
    completed_roles: list[str],
    active_role: str | None = None,
    evidence_dir: str | None = None,
    phases: list[dict] | None = None,
) -> bool:
    if condition.type == "role_required":
        role_id = condition.params.get("role_id", "")
        required_status = condition.params.get("status", "completed")
        if required_status == "completed":
            return role_id in (completed_roles or [])
        return active_role == role_id
    if condition.type == "evidence_required":
        evidence_type = condition.params.get("evidence_type", "")
        if not evidence_dir:
            return False
        from pathlib import Path as _Path
        import json
        ev_dir = _Path(evidence_dir)
        if not ev_dir.exists():
            return False
        for f in ev_dir.rglob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("type") == evidence_type:
                    return True
            except (json.JSONDecodeError, OSError):
                continue
        return False
    if condition.type == "phase_required":
        phase_id = condition.params.get("phase_id", "")
        if not phases:
            return False
        return any(p.get("phase_id") == phase_id and p.get("status") == "completed" for p in phases)
    if condition.type == "manual_approval":
        return False
    return False


def init_project(root: str, project_name: str) -> dict:
    from pathlib import Path as _Path
    from datetime import datetime as _dt, timezone as _tz
    root_p = _Path(root)
    ai_dir = root_p / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "evidence").mkdir(exist_ok=True)
    now = _dt.now(_tz.utc).isoformat()
    phases = [
        {"phase_id": "S1-requirements", "status": "active", "entered_at": now},
        {"phase_id": "S2-architecture", "status": "pending"},
        {"phase_id": "S3-interface", "status": "pending"},
        {"phase_id": "S4-implementation", "status": "pending"},
        {"phase_id": "S5-quality", "status": "pending"},
        {"phase_id": "S6-delivery", "status": "pending"},
    ]
    state = {
        "schema_version": 1, "project_name": project_name,
        "current_phase": "S1-requirements", "current_task_id": None,
        "current_gate_id": "gate-requirements", "loop_mode": "FULL",
        "completed_roles": [], "phases": phases, "last_handoff_at": now,
    }
    gate_defs = [
        {"id": "gate-requirements", "phase": "S1-requirements",
         "conditions": [{"condition_id": "req-baselined", "type": "role_required", "description": "requirements baselined", "params": {"role_id": "product-manager", "status": "completed"}}], "status": "pending"},
        {"id": "gate-architecture", "phase": "S2-architecture",
         "conditions": [{"condition_id": "arch-complete", "type": "role_required", "description": "architecture complete", "params": {"role_id": "system-architect", "status": "completed"}}], "status": "pending"},
        {"id": "gate-implementation", "phase": "S4-implementation",
         "conditions": [{"condition_id": "code-complete", "type": "role_required", "description": "code complete", "params": {"role_id": "developer", "status": "completed"}}, {"condition_id": "tests-pass", "type": "evidence_required", "description": "tests pass", "params": {"evidence_type": "test_result"}}], "status": "pending"},
        {"id": "gate-quality", "phase": "S5-quality",
         "conditions": [{"condition_id": "qa-pass", "type": "role_required", "description": "quality pass", "params": {"role_id": "quality-engineer", "status": "completed"}}, {"condition_id": "security-pass", "type": "role_required", "description": "security pass", "params": {"role_id": "security-engineer", "status": "completed"}}], "status": "pending"},
        {"id": "gate-delivery", "phase": "S6-delivery",
         "conditions": [{"condition_id": "delivery-ready", "type": "role_required", "description": "delivery ready", "params": {"role_id": "delivery-manager", "status": "completed"}}, {"condition_id": "human-approval", "type": "manual_approval", "description": "user acceptance", "params": {}}], "status": "pending"},
    ]
    gates = {"schema_version": 1, "gates": gate_defs}
    atomic_write_state(root_p, state)
    import yaml
    import os
    gates_path = ai_dir / "gates.yaml"
    tmp_path = ai_dir / "gates.yaml.tmp"
    tmp_path.write_text(yaml.dump(gates, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    os.replace(str(tmp_path), str(gates_path))
    return state

