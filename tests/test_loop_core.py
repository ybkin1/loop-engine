"""
Unit tests for loop_core: state_machine, router, enforcement.

Covers:
  - state_machine: phase transitions, gate approval, self-review detection
  - router: LIGHTWEIGHT/STANDARD/FULL routing, risk classification
  - enforcement: STRONG/MEDIUM/ADVISORY levels, hard constraint checks

All tests use in-memory data only — no external file dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ============================================================================
# state_machine tests
# ============================================================================

from loop_core.state_machine import (
    Phase,
    GateStatus,
    StateValidationResult,
    can_transition_phase,
    can_approve_gate,
    can_enter_phase,
    check_self_review,
    PHASE_TRANSITIONS,
    REVIEW_REQUIRED_PHASES,
    MINI_LOOP_PHASES,
)


class TestPhaseTransitions:
    """Tests for phase transition validation."""

    def test_valid_forward_transition(self):
        """S0-init -> S1-requirements is a valid transition."""
        result = can_transition_phase(Phase.S0_INIT, Phase.S1_REQUIREMENTS)
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_invalid_skip_transition(self):
        """S0-init -> S4-implementation (skipping phases) is not allowed."""
        result = can_transition_phase(Phase.S0_INIT, Phase.S4_IMPLEMENTATION)
        assert result.allowed is False
        assert len(result.errors) >= 1
        assert "S1-requirements" in result.errors[0]

    def test_loop_back_transition(self):
        """S11-maintenance -> S1-requirements (loop back) is a valid transition."""
        result = can_transition_phase(Phase.S11_MAINTENANCE, Phase.S1_REQUIREMENTS)
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_all_defined_transitions_have_valid_targets(self):
        """Every phase in PHASE_TRANSITIONS maps to valid Phase enum members."""
        for source, targets in PHASE_TRANSITIONS.items():
            assert isinstance(source, Phase)
            for target in targets:
                assert isinstance(target, Phase)
                assert target in Phase.__members__.values()

    def test_review_required_phases_are_valid(self):
        """All phases in REVIEW_REQUIRED_PHASES are valid Phase members."""
        for phase in REVIEW_REQUIRED_PHASES:
            assert phase in Phase.__members__.values()

    def test_mini_loop_phases_are_valid(self):
        """All phases in MINI_LOOP_PHASES are valid Phase members."""
        for phase in MINI_LOOP_PHASES:
            assert phase in Phase.__members__.values()


class TestGateApproval:
    """Tests for gate approval logic."""

    def test_all_roles_pass_gate_approved(self):
        """Gate should be approvable when all required roles pass."""
        result = can_approve_gate(
            gate_status=GateStatus.PENDING,
            role_verdicts={"architect": "PASS", "reviewer": "PASS"},
            required_roles=["architect", "reviewer"],
        )
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_one_role_blocked_gate_rejected(self):
        """Gate cannot be approved if any required role issues BLOCKED."""
        result = can_approve_gate(
            gate_status=GateStatus.PENDING,
            role_verdicts={"architect": "BLOCKED", "reviewer": "PASS"},
            required_roles=["architect", "reviewer"],
        )
        assert result.allowed is False
        assert any("BLOCKED" in err for err in result.errors)

    def test_missing_role_verdict(self):
        """Gate cannot be approved if a required role has not submitted."""
        result = can_approve_gate(
            gate_status=GateStatus.PENDING,
            role_verdicts={"architect": "PASS"},
            required_roles=["architect", "reviewer"],
        )
        assert result.allowed is False
        assert any("reviewer" in err.lower() for err in result.errors)

    def test_gate_not_pending(self):
        """A gate that is already approved cannot be approved again."""
        result = can_approve_gate(
            gate_status=GateStatus.APPROVED,
            role_verdicts={"architect": "PASS"},
            required_roles=["architect"],
        )
        assert result.allowed is False
        assert any("not pending" in err.lower() for err in result.errors)

    def test_all_roles_blocked(self):
        """Gate with all roles BLOCKED is correctly rejected with multiple errors."""
        result = can_approve_gate(
            gate_status=GateStatus.PENDING,
            role_verdicts={"architect": "BLOCKED", "reviewer": "BLOCKED"},
            required_roles=["architect", "reviewer"],
        )
        assert result.allowed is False
        assert len(result.errors) >= 2  # At least two BLOCKED messages


class TestSelfReviewDetection:
    """Tests for self-review violation detection."""

    def test_self_review_violation_same_ids(self):
        """Same developer and reviewer IDs should trigger a violation."""
        result = check_self_review(developer_id="agent-001", reviewer_id="agent-001")
        assert result.allowed is False
        assert len(result.errors) >= 1
        assert "SELF_REVIEW_VIOLATION" in result.errors[0]

    def test_self_review_ok_different_ids(self):
        """Different developer and reviewer IDs should be allowed."""
        result = check_self_review(developer_id="agent-001", reviewer_id="agent-002")
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_self_review_ok_none_ids(self):
        """None IDs (not yet assigned) should not trigger violation."""
        result = check_self_review(developer_id=None, reviewer_id=None)
        assert result.allowed is True
        assert len(result.errors) == 0

    def test_self_review_ok_one_none(self):
        """One None ID should not trigger violation."""
        result = check_self_review(developer_id="agent-001", reviewer_id=None)
        assert result.allowed is True
        assert len(result.errors) == 0


class TestPhaseEntry:
    """Tests for phase entry precondition checks."""

    def test_enter_phase_with_approved_gate(self):
        """Phase entry should be allowed when previous gate is approved."""
        result = can_enter_phase(
            phase=Phase.S4_IMPLEMENTATION,
            prev_gate_status=GateStatus.APPROVED,
            has_blockers=False,
        )
        assert result.allowed is True

    def test_enter_phase_with_rejected_gate(self):
        """Phase entry should be blocked when previous gate is rejected."""
        result = can_enter_phase(
            phase=Phase.S4_IMPLEMENTATION,
            prev_gate_status=GateStatus.REJECTED,
            has_blockers=False,
        )
        assert result.allowed is False
        assert any("not approved" in err.lower() for err in result.errors)

    def test_enter_phase_with_blockers(self):
        """Phase entry should be blocked when there are unresolved blockers."""
        result = can_enter_phase(
            phase=Phase.S5_QUALITY,
            prev_gate_status=GateStatus.APPROVED,
            has_blockers=True,
        )
        assert result.allowed is False
        assert any("blocker" in err.lower() for err in result.errors)

    def test_enter_phase_no_gate_no_blockers(self):
        """Phase entry without a previous gate (e.g., first phase) should be allowed."""
        result = can_enter_phase(
            phase=Phase.S0_INIT,
            prev_gate_status=None,
            has_blockers=False,
        )
        assert result.allowed is True


# ============================================================================
# router tests
# ============================================================================

from loop_core.router import (
    LoopMode,
    RiskLevel,
    ProjectProfile,
    RouteResult,
    route_intent,
)


class TestRiskLevelCalculation:
    """Tests for ProjectProfile.risk_level() classification."""

    def test_low_risk_no_flags(self):
        """Profile with no flags set should be LOW risk."""
        profile = ProjectProfile(description="Simple script")
        assert profile.risk_level() == RiskLevel.LOW

    def test_medium_risk_one_medium_flag(self):
        """A single medium-risk flag should yield MEDIUM."""
        profile = ProjectProfile(description="API integration", has_external_api=True)
        assert profile.risk_level() == RiskLevel.MEDIUM

    def test_high_risk_one_high_flag(self):
        """A single high-risk flag should yield HIGH."""
        profile = ProjectProfile(description="DB migration", has_database=True)
        assert profile.risk_level() == RiskLevel.HIGH

    def test_high_risk_three_medium_flags(self):
        """Three medium-risk flags should yield HIGH."""
        profile = ProjectProfile(
            description="Complex module",
            has_multiple_modules=True,
            has_external_api=True,
            requires_deployment=True,
        )
        assert profile.risk_level() == RiskLevel.HIGH

    def test_critical_risk_two_high_flags(self):
        """Two high-risk flags should yield CRITICAL."""
        profile = ProjectProfile(
            description="Payment system",
            has_payments=True,
            has_security_requirements=True,
        )
        assert profile.risk_level() == RiskLevel.CRITICAL

    def test_critical_risk_mixed_flags(self):
        """One high-risk + multiple medium flags (insufficient for CRITICAL alone)
        should NOT be CRITICAL — CRITICAL requires >= 2 high-risk flags."""
        profile = ProjectProfile(
            description="Auth module",
            has_auth_permissions=True,
            has_external_api=True,
            requires_deployment=True,
            has_high_uncertainty=True,
        )
        # 1 high + 3 medium = HIGH (not CRITICAL, need 2+ high)
        assert profile.risk_level() == RiskLevel.HIGH


class TestLoopRouting:
    """Tests for route_intent() and ProjectProfile.route()."""

    def test_lightweight_routing(self):
        """Low risk should route to LIGHTWEIGHT mode."""
        profile = ProjectProfile(description="Simple bug fix")
        result = route_intent(profile)
        assert result.mode == LoopMode.LIGHTWEIGHT
        assert result.risk_level == RiskLevel.LOW
        assert "S0-init" in result.recommended_phases
        assert "S4-implementation" in result.recommended_phases
        assert "S6-delivery" in result.recommended_phases
        # Should NOT include architecture or quality phases
        assert "S2-architecture" not in result.recommended_phases
        assert "S5-quality" not in result.recommended_phases

    def test_standard_routing(self):
        """Medium risk should route to STANDARD mode."""
        profile = ProjectProfile(description="API endpoint", has_external_api=True)
        result = route_intent(profile)
        assert result.mode == LoopMode.STANDARD
        assert result.risk_level == RiskLevel.MEDIUM
        assert "S1-requirements" in result.recommended_phases
        assert "S2-architecture" in result.recommended_phases
        assert "S5-quality" in result.recommended_phases
        # Should NOT include full-loop phases
        assert "S3-interface" not in result.recommended_phases
        assert "S10-performance" not in result.recommended_phases

    def test_full_routing_high(self):
        """High risk should route to FULL mode."""
        profile = ProjectProfile(description="Database schema change", has_database=True)
        result = route_intent(profile)
        assert result.mode == LoopMode.FULL
        assert result.risk_level == RiskLevel.HIGH

    def test_full_routing_critical(self):
        """Critical risk should route to FULL mode."""
        profile = ProjectProfile(
            description="Payment gateway",
            has_payments=True,
            has_security_requirements=True,
        )
        result = route_intent(profile)
        assert result.mode == LoopMode.FULL
        assert result.risk_level == RiskLevel.CRITICAL
        # Full mode should include all 12 phases
        assert len(result.recommended_phases) == 12

    def test_user_forced_mode_cannot_downgrade_risk(self):
        """User-forced mode cannot lower the minimum required risk mode."""
        profile = ProjectProfile(
            description="Critical payment system",
            has_payments=True,
            has_security_requirements=True,
            user_forced_mode=LoopMode.LIGHTWEIGHT,
        )
        # Critical risk must remain FULL even when LIGHTWEIGHT is requested.
        assert profile.risk_level() == RiskLevel.CRITICAL
        result = route_intent(profile)
        assert result.mode == LoopMode.FULL

    def test_route_result_has_reason(self):
        """Every RouteResult should include a non-empty reason string."""
        for desc, flags in [
            ("simple", {}),
            ("medium", {"has_external_api": True}),
            ("high", {"has_database": True}),
            ("critical", {"has_payments": True, "has_security_requirements": True}),
        ]:
            profile = ProjectProfile(description=desc, **flags)
            result = route_intent(profile)
            assert result.reason, f"RouteResult for {desc} missing reason"
            assert len(result.reason) > 0

    def test_route_intent_phases_are_strings(self):
        """All recommended phases should be strings."""
        profile = ProjectProfile(description="Test", has_database=True)
        result = route_intent(profile)
        for phase in result.recommended_phases:
            assert isinstance(phase, str)
            assert phase.startswith("S")


# ============================================================================
# enforcement tests
# ============================================================================

from loop_core.enforcement import (
    EnforcementLevel,
    HostCapabilities,
    EnforcementResult,
    HARD_CONSTRAINTS,
    validate_host_capabilities,
)


class TestEnforcementLevels:
    """Tests for enforcement level determination."""

    def test_strong_enforcement(self):
        """Host with all capabilities should be STRONG."""
        caps = HostCapabilities(
            can_intercept_writes=True,
            can_intercept_commands=True,
            can_isolate_agents=True,
            can_enforce_exit_codes=True,
            has_hooks_api=True,
        )
        assert caps.enforcement_level() == EnforcementLevel.STRONG

    def test_medium_enforcement_with_hooks(self):
        """Host with only hooks API should be MEDIUM."""
        caps = HostCapabilities(
            can_intercept_writes=False,
            can_intercept_commands=False,
            can_isolate_agents=False,
            can_enforce_exit_codes=False,
            has_hooks_api=True,
        )
        assert caps.enforcement_level() == EnforcementLevel.MEDIUM

    def test_medium_enforcement_with_isolation(self):
        """Host with only agent isolation should be MEDIUM."""
        caps = HostCapabilities(
            can_isolate_agents=True,
            has_hooks_api=False,
        )
        assert caps.enforcement_level() == EnforcementLevel.MEDIUM

    def test_advisory_enforcement(self):
        """Host with no enforcement capabilities should be ADVISORY."""
        caps = HostCapabilities()
        assert caps.enforcement_level() == EnforcementLevel.ADVISORY

    def test_strong_requires_all_three_core_capabilities(self):
        """STRONG requires write intercept AND command intercept AND exit code enforcement."""
        caps = HostCapabilities(
            can_intercept_writes=True,
            can_intercept_commands=True,
            can_enforce_exit_codes=False,  # Missing!
            has_hooks_api=True,
            can_isolate_agents=True,
        )
        # Missing can_enforce_exit_codes => falls to MEDIUM
        assert caps.enforcement_level() == EnforcementLevel.MEDIUM


class TestHardConstraints:
    """Tests for hard constraint definitions."""

    def test_all_constraints_have_required_fields(self):
        """Every hard constraint must have id and description."""
        for constraint in HARD_CONSTRAINTS:
            assert "id" in constraint, f"Constraint missing 'id': {constraint}"
            assert "description" in constraint, f"Constraint missing 'description': {constraint}"
            assert isinstance(constraint["id"], str)
            assert len(constraint["id"]) > 0
            assert isinstance(constraint["description"], str)
            assert len(constraint["description"]) > 0

    def test_constraint_ids_are_unique(self):
        """No two constraints should share the same id."""
        ids = [c["id"] for c in HARD_CONSTRAINTS]
        assert len(ids) == len(set(ids)), f"Duplicate constraint IDs found"

    def test_all_constraints_have_check_expression(self):
        """Every hard constraint must have a check expression."""
        for constraint in HARD_CONSTRAINTS:
            assert "check" in constraint, f"Constraint {constraint['id']} missing 'check'"
            assert isinstance(constraint["check"], str)
            assert len(constraint["check"]) > 0


class TestEnforcementResult:
    """Tests for EnforcementResult behavior."""

    def test_is_blocked_strong_with_violations(self):
        """At STRONG level, violations should be blocking."""
        result = EnforcementResult(
            level=EnforcementLevel.STRONG,
            violations=[{"id": "TEST", "desc": "Test violation"}],
        )
        assert result.is_blocked is True

    def test_not_blocked_strong_without_violations(self):
        """At STRONG level with no violations, should not be blocked."""
        result = EnforcementResult(
            level=EnforcementLevel.STRONG,
            violations=[],
        )
        assert result.is_blocked is False

    def test_not_blocked_advisory_with_violations(self):
        """At ADVISORY level, violations should NOT be blocking."""
        result = EnforcementResult(
            level=EnforcementLevel.ADVISORY,
            violations=[{"id": "TEST", "desc": "Test violation"}],
        )
        assert result.is_blocked is False

    def test_not_blocked_medium_with_violations(self):
        """At MEDIUM level, violations should NOT be blocking."""
        result = EnforcementResult(
            level=EnforcementLevel.MEDIUM,
            violations=[{"id": "TEST", "desc": "Test violation"}],
        )
        assert result.is_blocked is False

    def test_is_honest_always_true(self):
        """EnforcementResult.is_honest should always be True."""
        result = EnforcementResult(level=EnforcementLevel.ADVISORY)
        assert result.is_honest is True
        result2 = EnforcementResult(level=EnforcementLevel.STRONG)
        assert result2.is_honest is True

    def test_validate_host_capabilities_strong_with_gaps(self):
        """STRONG level missing write intercept should produce a warning and downgrade."""
        caps = HostCapabilities(
            can_intercept_writes=False,  # Missing
            can_intercept_commands=True,
            can_enforce_exit_codes=True,
        )
        result = validate_host_capabilities(caps)
        # Without write intercept, STRONG fails. Without hooks/isolation, MEDIUM fails. Falls to ADVISORY.
        assert result.level == EnforcementLevel.ADVISORY

    def test_validate_host_capabilities_strong_fully_capable(self):
        """Fully capable STRONG host should have no warnings."""
        caps = HostCapabilities(
            can_intercept_writes=True,
            can_intercept_commands=True,
            can_enforce_exit_codes=True,
        )
        result = validate_host_capabilities(caps)
        assert result.level == EnforcementLevel.STRONG
        assert len(result.warnings) == 0
        assert len(result.violations) == 0


class TestEnforcementLevelEnum:
    """Tests for EnforcementLevel enum values."""

    def test_enforcement_level_values(self):
        """EnforcementLevel should have the three expected values."""
        assert EnforcementLevel.STRONG.value == "STRONG"
        assert EnforcementLevel.MEDIUM.value == "MEDIUM"
        assert EnforcementLevel.ADVISORY.value == "ADVISORY"

    def test_enforcement_level_ordering(self):
        """STRONG > MEDIUM > ADVISORY for string comparison purposes."""
        levels = [EnforcementLevel.ADVISORY, EnforcementLevel.STRONG, EnforcementLevel.MEDIUM]
        sorted_levels = sorted(levels, key=lambda x: ["ADVISORY", "MEDIUM", "STRONG"].index(x.value))
        assert sorted_levels == [EnforcementLevel.ADVISORY, EnforcementLevel.MEDIUM, EnforcementLevel.STRONG]
