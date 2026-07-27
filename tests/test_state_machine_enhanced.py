"""
Unit tests for state_machine.py enhancements:
  - RoleIsolationCheck / check_role_isolation
  - resolve_gate_status (P0-E deadlock fix)
  - PhaseConstraint / PHASE_CONSTRAINTS / check_phase_constraints
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.state_machine import (
    Phase,
    GateStatus,
    StateValidationResult,
    PhaseConstraint,
    PHASE_CONSTRAINTS,
    RoleIsolationCheck,
    check_role_isolation,
    resolve_gate_status,
    get_constraints_for_phase,
    get_blocker_constraints,
    check_phase_constraints,
    can_transition_phase,
    can_approve_gate,
    can_enter_phase,
    check_self_review,
)


# ═══════════════════════════════════════════════════════════════════════
# RoleIsolation 检查
# ═══════════════════════════════════════════════════════════════════════

class TestRoleIsolation:
    """Tests for check_role_isolation and RoleIsolationCheck."""

    def test_all_different_ids_passes(self):
        """All IDs differ -> allowed."""
        check = RoleIsolationCheck(
            developer_actor_id="dev-agent-1",
            reviewer_actor_id="rev-agent-2",
            developer_session_id="sess-dev-001",
            reviewer_session_id="sess-rev-002",
            developer_input_fingerprint="sha256:dev_input_hash",
            reviewer_input_fingerprint="sha256:rev_input_hash",
        )
        result = check_role_isolation(check)
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_same_actor_id_fails(self):
        """Same actor_id for Developer and Reviewer -> error."""
        check = RoleIsolationCheck(
            developer_actor_id="same-agent",
            reviewer_actor_id="same-agent",
            developer_session_id="sess-dev-001",
            reviewer_session_id="sess-rev-002",
            developer_input_fingerprint="sha256:hash_a",
            reviewer_input_fingerprint="sha256:hash_b",
        )
        result = check_role_isolation(check)
        assert result.allowed is False
        assert any("ACTOR" in e for e in result.errors)

    def test_same_session_id_fails(self):
        """Same session_id -> error."""
        check = RoleIsolationCheck(
            developer_actor_id="dev-agent-1",
            reviewer_actor_id="rev-agent-2",
            developer_session_id="same-session",
            reviewer_session_id="same-session",
            developer_input_fingerprint="sha256:hash_a",
            reviewer_input_fingerprint="sha256:hash_b",
        )
        result = check_role_isolation(check)
        assert result.allowed is False
        assert any("SESSION" in e for e in result.errors)

    def test_same_input_fingerprint_fails(self):
        """Same input_fingerprint -> error (reviewer not seeing frozen snapshot)."""
        check = RoleIsolationCheck(
            developer_actor_id="dev-agent-1",
            reviewer_actor_id="rev-agent-2",
            developer_session_id="sess-dev-001",
            reviewer_session_id="sess-rev-002",
            developer_input_fingerprint="sha256:same_hash",
            reviewer_input_fingerprint="sha256:same_hash",
        )
        result = check_role_isolation(check)
        assert result.allowed is False
        assert any("INPUT" in e for e in result.errors)

    def test_none_ids_produce_warnings_not_errors(self):
        """None actor_ids produce warnings but do not block."""
        check = RoleIsolationCheck(
            developer_actor_id=None,
            reviewer_actor_id="rev-agent-2",
            developer_session_id=None,
            reviewer_session_id="sess-rev-002",
            developer_input_fingerprint=None,
            reviewer_input_fingerprint="sha256:hash_b",
        )
        result = check_role_isolation(check)
        assert result.allowed is True
        assert len(result.warnings) > 0
        assert len(result.errors) == 0

    def test_all_none_produces_warnings_only(self):
        """All fields None -> warnings but allowed (incomplete data)."""
        check = RoleIsolationCheck(
            developer_actor_id=None,
            reviewer_actor_id=None,
            developer_session_id=None,
            reviewer_session_id=None,
            developer_input_fingerprint=None,
            reviewer_input_fingerprint=None,
        )
        result = check_role_isolation(check)
        assert result.allowed is True
        assert len(result.warnings) >= 3
        assert len(result.errors) == 0

    def test_multiple_violations_reported(self):
        """All three dimensions violated -> three errors."""
        check = RoleIsolationCheck(
            developer_actor_id="same",
            reviewer_actor_id="same",
            developer_session_id="same",
            reviewer_session_id="same",
            developer_input_fingerprint="same",
            reviewer_input_fingerprint="same",
        )
        result = check_role_isolation(check)
        assert result.allowed is False
        assert len(result.errors) == 3


# ═══════════════════════════════════════════════════════════════════════
# Gate 交叉校验 (P0-E 死锁修复)
# ═══════════════════════════════════════════════════════════════════════

class TestResolveGateStatus:
    """Tests for resolve_gate_status — the P0-E deadlock fix."""

    def test_none_gate_id_returns_none(self):
        """current_gate_id is None -> returns None."""
        gates = [{"id": "G-T-001", "status": "pending"}]
        result = resolve_gate_status(None, gates)
        assert result is None

    def test_gate_id_not_found_returns_none(self):
        """Gate ID does not exist in gates list -> returns None (stale ref)."""
        gates = [{"id": "G-T-001", "status": "pending"}]
        result = resolve_gate_status("G-T-NONEXISTENT", gates)
        assert result is None

    def test_pending_gate_returns_pending(self):
        """Gate exists and status is 'pending' -> returns GateStatus.PENDING."""
        gates = [
            {"id": "G-T-001", "status": "pending"},
            {"id": "G-T-002", "status": "approved"},
        ]
        result = resolve_gate_status("G-T-001", gates)
        assert result == GateStatus.PENDING

    def test_approved_gate_does_not_return_pending(self):
        """Gate exists and status is 'approved' -> returns APPROVED, not PENDING.

        This is the key P0-E fix: a stale current_gate_id pointing to an
        already-approved gate must NOT be treated as PENDING.
        """
        gates = [
            {"id": "G-T-0034-DESIGN", "status": "approved"},
        ]
        result = resolve_gate_status("G-T-0034-DESIGN", gates)
        assert result == GateStatus.APPROVED
        assert result != GateStatus.PENDING

    def test_rejected_gate_returns_rejected(self):
        """Gate exists and status is 'rejected' -> returns REJECTED."""
        gates = [{"id": "G-T-003", "status": "rejected"}]
        result = resolve_gate_status("G-T-003", gates)
        assert result == GateStatus.REJECTED

    def test_blocked_gate_returns_blocked(self):
        """Gate exists and status is 'blocked' -> returns BLOCKED."""
        gates = [{"id": "G-T-004", "status": "blocked"}]
        result = resolve_gate_status("G-T-004", gates)
        assert result == GateStatus.BLOCKED

    def test_empty_gates_list_with_id_returns_none(self):
        """Empty gates list with a current_gate_id -> returns None."""
        result = resolve_gate_status("G-T-005", [])
        assert result is None

    def test_unknown_status_defaults_to_pending(self):
        """Gate with unknown status string defaults to PENDING (safe fallback)."""
        gates = [{"id": "G-T-006", "status": "unknown_weird_status"}]
        result = resolve_gate_status("G-T-006", gates)
        assert result == GateStatus.PENDING


# ═══════════════════════════════════════════════════════════════════════
# PhaseConstraint 映射完整性检查
# ═══════════════════════════════════════════════════════════════════════

class TestPhaseConstraints:
    """Tests for PhaseConstraint dataclass and PHASE_CONSTRAINTS mapping."""

    def test_phase_constraint_creation(self):
        """PhaseConstraint can be instantiated."""
        pc = PhaseConstraint(
            constraint_id="C1-no-requirements",
            phase=Phase.S4_IMPLEMENTATION,
            description="Needs requirements baseline",
            blocker=True,
        )
        assert pc.constraint_id == "C1-no-requirements"
        assert pc.phase == Phase.S4_IMPLEMENTATION
        assert pc.blocker is True

    def test_phase_constraint_default_blocker_true(self):
        """Default blocker value is True."""
        pc = PhaseConstraint(
            constraint_id="C0-no-init",
            phase=Phase.S1_REQUIREMENTS,
            description="Needs init",
        )
        assert pc.blocker is True

    def test_phase_constraint_non_blocker(self):
        """Non-blocker constraint: blocker=False."""
        # S9_FIX_OPTIMIZE has C10 as non-blocker
        constraints = get_constraints_for_phase(Phase.S9_FIX_OPTIMIZE)
        non_blockers = [c for c in constraints if not c.blocker]
        assert len(non_blockers) >= 1
        assert any(c.constraint_id == "C10-no-functional-test" for c in non_blockers)

    def test_s4_implementation_has_three_constraints(self):
        """S4-implementation should have C1, C2, C3 constraints."""
        constraints = get_constraints_for_phase(Phase.S4_IMPLEMENTATION)
        ids = {c.constraint_id for c in constraints}
        assert "C1-no-requirements" in ids
        assert "C2-no-architecture" in ids
        assert "C3-no-task-package" in ids

    def test_s6_delivery_has_blocker_constraints(self):
        """S6-delivery should have C5, C6, C7 as blocker constraints."""
        blockers = get_blocker_constraints(Phase.S6_DELIVERY)
        ids = {c.constraint_id for c in blockers}
        assert "C5-no-verification" in ids
        assert "C6-no-independent-review" in ids
        assert "C7-blocker-exists" in ids

    def test_all_phases_have_constraint_ids_unique(self):
        """Within each phase, constraint IDs should be unique."""
        for phase, constraints in PHASE_CONSTRAINTS.items():
            ids = [c.constraint_id for c in constraints]
            assert len(ids) == len(set(ids)), \
                f"Duplicate constraint IDs in phase {phase.value}: {ids}"

    def test_all_phases_in_transitions_have_constraints_or_empty(self):
        """Phases with defined transitions may or may not have constraints."""
        # Verify that every Phase in the enum can be looked up
        for phase in Phase:
            result = get_constraints_for_phase(phase)
            assert isinstance(result, list)

    def test_constraint_phase_field_matches_mapping_key(self):
        """Each constraint's .phase should match the dict key it's under."""
        for phase, constraints in PHASE_CONSTRAINTS.items():
            for c in constraints:
                assert c.phase == phase, \
                    f"Constraint {c.constraint_id} has phase={c.phase} but is under key {phase}"


# ═══════════════════════════════════════════════════════════════════════
# check_phase_constraints 集成测试
# ═══════════════════════════════════════════════════════════════════════

class TestCheckPhaseConstraints:
    """Integration tests for check_phase_constraints."""

    def test_s4_with_all_gates_approved_and_active_task_passes(self):
        """All S4 constraints satisfied -> allowed."""
        approved_gates = {"G-S1-requirements", "G-S2-architecture"}
        result = check_phase_constraints(
            Phase.S4_IMPLEMENTATION,
            approved_gate_ids=approved_gates,
            task_has_active=True,
        )
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_s4_missing_requirements_gate_fails(self):
        """Missing S1-requirements gate approval -> blocked."""
        approved_gates = {"G-S2-architecture"}  # No S1 gate
        result = check_phase_constraints(
            Phase.S4_IMPLEMENTATION,
            approved_gate_ids=approved_gates,
            task_has_active=True,
        )
        assert result.allowed is False
        assert any("C1" in e for e in result.errors)

    def test_s4_missing_task_package_fails(self):
        """No active task -> C3 constraint fails."""
        approved_gates = {"G-S1-requirements", "G-S2-architecture"}
        result = check_phase_constraints(
            Phase.S4_IMPLEMENTATION,
            approved_gate_ids=approved_gates,
            task_has_active=False,  # No active task
        )
        assert result.allowed is False
        assert any("C3" in e for e in result.errors)

    def test_s6_all_satisfied_passes(self):
        """Delivery phase with all checks -> allowed."""
        approved_gates = {"G-S6-independent-review"}
        result = check_phase_constraints(
            Phase.S6_DELIVERY,
            approved_gate_ids=approved_gates,
            verification_passed=True,
        )
        assert result.allowed is True

    def test_s6_missing_verification_fails(self):
        """Missing verification -> C5 constraint fails."""
        approved_gates = {"G-S6-independent-review"}
        result = check_phase_constraints(
            Phase.S6_DELIVERY,
            approved_gate_ids=approved_gates,
            verification_passed=False,
        )
        assert result.allowed is False
        assert any("C5" in e for e in result.errors)

    def test_s6_missing_independent_review_fails(self):
        """Missing independent review gate -> C6 constraint fails."""
        approved_gates = set()  # No independent review gate
        result = check_phase_constraints(
            Phase.S6_DELIVERY,
            approved_gate_ids=approved_gates,
            verification_passed=True,
        )
        assert result.allowed is False
        assert any("C6" in e for e in result.errors)

    def test_non_blocker_constraint_produces_warning(self):
        """Non-blocker constraint (C10) produces warning, not error."""
        result = check_phase_constraints(
            Phase.S9_FIX_OPTIMIZE,
            approved_gate_ids=set(),
            verification_passed=False,
        )
        # C10 is non-blocker, so it produces a warning
        assert any("C10" in w for w in result.warnings)


# ═══════════════════════════════════════════════════════════════════════
# 向后兼容：现有函数签名和行为不变
# ═══════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """Ensure existing functions still work exactly as before."""

    def test_can_transition_valid(self):
        result = can_transition_phase(Phase.S4_IMPLEMENTATION, Phase.S5_QUALITY)
        assert result.allowed is True

    def test_can_transition_invalid(self):
        result = can_transition_phase(Phase.S4_IMPLEMENTATION, Phase.S1_REQUIREMENTS)
        assert result.allowed is False

    def test_can_approve_gate_all_pass(self):
        result = can_approve_gate(
            GateStatus.PENDING,
            {"architect": "PASS", "reviewer": "PASS"},
            ["architect", "reviewer"],
        )
        assert result.allowed is True

    def test_can_approve_gate_one_blocked(self):
        result = can_approve_gate(
            GateStatus.PENDING,
            {"architect": "PASS", "reviewer": "BLOCKED"},
            ["architect", "reviewer"],
        )
        assert result.allowed is False

    def test_can_approve_gate_not_pending(self):
        result = can_approve_gate(
            GateStatus.APPROVED,
            {"architect": "PASS"},
            ["architect"],
        )
        assert result.allowed is False

    def test_can_enter_phase_approved(self):
        result = can_enter_phase(Phase.S4_IMPLEMENTATION, GateStatus.APPROVED, False)
        assert result.allowed is True

    def test_can_enter_phase_blocked(self):
        result = can_enter_phase(Phase.S4_IMPLEMENTATION, GateStatus.APPROVED, True)
        assert result.allowed is False

    def test_can_enter_phase_gate_not_approved(self):
        result = can_enter_phase(Phase.S4_IMPLEMENTATION, GateStatus.PENDING, False)
        assert result.allowed is False

    def test_check_self_review_same_agent(self):
        result = check_self_review("agent-1", "agent-1")
        assert result.allowed is False

    def test_check_self_review_different_agents(self):
        result = check_self_review("agent-1", "agent-2")
        assert result.allowed is True
