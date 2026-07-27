# -*- coding: utf-8 -*-
"""
test_veto_escalation.py — comprehensive tests for the veto escalation protocol.

Covers:
  - Single-role veto → ROLE_INTERNAL
  - Two roles same domain → CROSS_ROLE
  - Two roles cross-domain → USER_GATE
  - Security-engineer + any role → USER_GATE
  - 3+ distinct roles → USER_GATE
  - VetoRecord serialization / deserialization
  - generate_human_review_packet readability
  - Veto resolution and its effect on escalation
  - WARNING vetoes do not trigger escalation
  - Edge cases: zero vetoes, all resolved, unknown roles
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

# Ensure loop_core is importable
_SRC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SRC_ROOT))

from loop_core.veto_escalation import (
    CROSS_ROLE_ONLY_DOMAIN_PAIRS,
    ROLE_DOMAINS,
    EscalationDecision,
    EscalationLevel,
    VetoEscalation,
    VetoRecord,
    VetoSeverity,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_veto(
    veto_id: str = "v-001",
    role_id: str = "quality-engineer",
    task_id: str = "task-1",
    gate_id: str | None = "gate-s5-quality",
    severity: VetoSeverity = VetoSeverity.BLOCKER,
    reason: str = "Coverage below threshold",
    evidence_refs: list[str] | None = None,
    remediation: str = "Add more tests to reach 80% coverage",
) -> VetoRecord:
    """Factory helper to reduce boilerplate in tests."""
    return VetoRecord(
        veto_id=veto_id,
        role_id=role_id,
        target_task_id=task_id,
        target_gate_id=gate_id,
        severity=severity,
        reason=reason,
        evidence_refs=evidence_refs or ["coverage_report.json"],
        suggested_remediation=remediation,
        recorded_at=datetime.now(timezone.utc).isoformat(),
    )


class VetoRecordSerializationTest(unittest.TestCase):
    """VetoRecord to_dict / from_dict round-trip."""

    def test_round_trip_full(self):
        original = VetoRecord(
            veto_id="v-42",
            role_id="security-engineer",
            target_task_id="task-auth",
            target_gate_id="gate-s4-impl",
            severity=VetoSeverity.BLOCKER,
            reason="Critical CVE in auth module",
            evidence_refs=["audit.json", "cve-details.md"],
            suggested_remediation="Upgrade library to patched version",
            recorded_at="2026-07-23T10:00:00+00:00",
        )
        d = original.to_dict()
        restored = VetoRecord.from_dict(d)

        self.assertEqual(restored.veto_id, original.veto_id)
        self.assertEqual(restored.role_id, original.role_id)
        self.assertEqual(restored.target_task_id, original.target_task_id)
        self.assertEqual(restored.target_gate_id, original.target_gate_id)
        self.assertEqual(restored.severity, original.severity)
        self.assertEqual(restored.reason, original.reason)
        self.assertEqual(restored.evidence_refs, original.evidence_refs)
        self.assertEqual(restored.suggested_remediation, original.suggested_remediation)
        self.assertEqual(restored.recorded_at, original.recorded_at)

    def test_round_trip_minimal(self):
        """Minimal VetoRecord with only required fields."""
        original = VetoRecord(
            veto_id="v-min",
            role_id="developer",
            target_task_id="task-x",
            target_gate_id=None,
            severity=VetoSeverity.WARNING,
            reason="Minor style inconsistency",
        )
        d = original.to_dict()
        restored = VetoRecord.from_dict(d)

        self.assertEqual(restored.veto_id, "v-min")
        self.assertEqual(restored.target_gate_id, None)
        self.assertEqual(restored.severity, VetoSeverity.WARNING)
        self.assertEqual(restored.evidence_refs, [])
        self.assertEqual(restored.suggested_remediation, "")

    def test_from_dict_defaults(self):
        """from_dict fills missing optional fields with defaults."""
        minimal_dict = {
            "veto_id": "v-defaults",
            "role_id": "delivery-manager",
            "target_task_id": "task-d",
            "severity": "blocker",
        }
        record = VetoRecord.from_dict(minimal_dict)
        self.assertEqual(record.veto_id, "v-defaults")
        self.assertEqual(record.target_gate_id, None)
        self.assertEqual(record.reason, "")
        self.assertEqual(record.evidence_refs, [])
        self.assertEqual(record.suggested_remediation, "")
        self.assertEqual(record.severity, VetoSeverity.BLOCKER)

    def test_json_serializable(self):
        """to_dict output is JSON-serializable."""
        record = _make_veto()
        d = record.to_dict()
        raw = json.dumps(d)
        back = json.loads(raw)
        self.assertEqual(back["veto_id"], record.veto_id)
        self.assertEqual(back["severity"], "blocker")

    def test_recorded_at_default(self):
        """recorded_at gets an ISO timestamp by default."""
        record = VetoRecord(
            veto_id="v-time",
            role_id="product-manager",
            target_task_id="task-pm",
            target_gate_id=None,
            severity=VetoSeverity.WARNING,
            reason="Just a warning",
        )
        self.assertIsNotNone(record.recorded_at)
        self.assertIn("T", record.recorded_at)  # ISO-8601 contains 'T'


class SingleRoleVetoTest(unittest.TestCase):
    """Rule 5: Single role veto → ROLE_INTERNAL."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_single_blocker_role_internal(self):
        self.engine.record_veto(_make_veto(role_id="quality-engineer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertIn("quality-engineer", decision.reason)
        self.assertIsNone(decision.human_review_packet)

    def test_multiple_vetoes_same_role_still_internal(self):
        """Multiple BLOCKER vetoes from the same role → still ROLE_INTERNAL."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="quality-engineer",
                                            reason="Lint errors also found"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertEqual(len(decision.involved_roles), 1)

    def test_warning_only_no_escalation(self):
        """WARNING vetoes do not trigger any escalation."""
        self.engine.record_veto(_make_veto(
            severity=VetoSeverity.WARNING, reason="Nitpick: variable name",
            role_id="developer",
        ))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertIn("No active BLOCKER", decision.reason)

    def test_single_blocker_plus_warning_still_internal(self):
        """A WARNING alongside a BLOCKER from same role → ROLE_INTERNAL."""
        self.engine.record_veto(_make_veto(veto_id="v-1", severity=VetoSeverity.BLOCKER,
                                            role_id="developer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", severity=VetoSeverity.WARNING,
                                            role_id="developer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)


class SameDomainTwoRolesTest(unittest.TestCase):
    """Rule 3: Two roles from the same domain → CROSS_ROLE."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_system_and_module_architect(self):
        """system-architect + module-architect are both in 'architecture' domain."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="system-architect",
                                            reason="Architecture violates layering"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="module-architect",
                                            reason="Module boundary not respected"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)
        self.assertIn("architecture", decision.reason)
        self.assertEqual(len(decision.involved_roles), 2)

    def test_same_role_different_vetoes(self):
        """Two BLOCKER vetoes from roles in the same domain → CROSS_ROLE."""
        # Use delivery-manager and project-manager — both in 'management'?
        # Actually project-manager = 'management', delivery-manager = 'delivery'
        # Let's use system-architect + module-architect which are both 'architecture'
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="system-architect"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="module-architect"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)


class CrossDomainTwoRolesTest(unittest.TestCase):
    """Rule 4: Two roles from different domains → USER_GATE (with exceptions)."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_quality_and_delivery_cross_domain(self):
        """quality-engineer (quality) + delivery-manager (delivery) → USER_GATE."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer",
                                            reason="Coverage too low"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager",
                                            reason="Schedule risk unacceptable"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertIsNotNone(decision.human_review_packet)
        self.assertIn("quality", decision.reason.lower())
        self.assertIn("delivery", decision.reason.lower())

    def test_quality_and_reviewer_cross_domain(self):
        """quality-engineer + independent-reviewer → USER_GATE."""
        self.engine.record_veto(_make_veto(role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="independent-reviewer",
                                            reason="Review found logical errors"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)

    def test_quality_and_product_cross_domain(self):
        """quality-engineer + product-manager → USER_GATE."""
        self.engine.record_veto(_make_veto(role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="product-manager",
                                            reason="Does not meet acceptance criteria"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)


class ArchitectureDevelopmentPairTest(unittest.TestCase):
    """Exception: architecture + development domains → CROSS_ROLE (not USER_GATE).

    These two domains are closely coupled — their conflict is a design
    tension that should be negotiated, not escalated to the user.
    """

    def setUp(self):
        self.engine = VetoEscalation()

    def test_architect_and_developer_cross_role(self):
        """system-architect + developer → CROSS_ROLE (not USER_GATE)."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="system-architect",
                                            reason="Design does not follow approved architecture"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="developer",
                                            reason="Architecture too rigid for this use case"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)
        self.assertNotEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertIsNone(decision.human_review_packet)
        self.assertIn("closely coupled", decision.reason.lower())

    def test_module_architect_and_developer_cross_role(self):
        """module-architect + developer → CROSS_ROLE."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="module-architect"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="developer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)


class SecurityEngineerTest(unittest.TestCase):
    """Rule 1: Security-engineer + any other role → immediate USER_GATE."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_security_and_quality(self):
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="security-engineer",
                                            reason="CVE-2026-1234 in dependency"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="quality-engineer",
                                            reason="Coverage below threshold"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertIsNotNone(decision.human_review_packet)
        self.assertIn("security", decision.reason.lower())

    def test_security_and_developer(self):
        self.engine.record_veto(_make_veto(role_id="security-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="developer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)

    def test_security_and_delivery_manager(self):
        self.engine.record_veto(_make_veto(role_id="security-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)

    def test_security_and_architect(self):
        """Even architecture+development is CROSS_ROLE, but security+anything is USER_GATE."""
        self.engine.record_veto(_make_veto(role_id="security-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="system-architect"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)

    def test_security_alone_role_internal(self):
        """Security-engineer with no other vetoes → ROLE_INTERNAL (no conflict)."""
        self.engine.record_veto(_make_veto(role_id="security-engineer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)


class ThreePlusRolesTest(unittest.TestCase):
    """Rule 2: 3+ distinct roles with BLOCKER vetoes → USER_GATE."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_three_distinct_roles(self):
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        self.engine.record_veto(_make_veto(veto_id="v-3", role_id="product-manager",
                                            reason="Wrong feature scope"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertEqual(len(decision.involved_roles), 3)
        self.assertIsNotNone(decision.human_review_packet)

    def test_four_distinct_roles(self):
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        self.engine.record_veto(_make_veto(veto_id="v-3", role_id="product-manager"))
        self.engine.record_veto(_make_veto(veto_id="v-4", role_id="system-architect"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertEqual(len(decision.involved_roles), 4)

    def test_three_roles_including_security(self):
        """3+ roles including security → still USER_GATE (rule 2 catches it
        even before rule 1, but both rules agree)."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="security-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-3", role_id="developer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertEqual(len(decision.involved_roles), 3)

    def test_three_architects_plus_developer(self):
        """system-architect + module-architect (same domain) + developer → 3 roles → USER_GATE.

        Even though architecture+development would normally be CROSS_ROLE,
        having 3+ distinct roles overrides that exception.
        """
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="system-architect"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="module-architect"))
        self.engine.record_veto(_make_veto(veto_id="v-3", role_id="developer"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)


class VetoResolutionTest(unittest.TestCase):
    """Resolving vetoes removes them from escalation consideration."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_resolve_single_veto_clears_escalation(self):
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.resolve_veto("v-1", "Coverage improved to 82%")
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertIn("No active BLOCKER", decision.reason)

    def test_resolve_one_of_two_reduces_escalation(self):
        """Two cross-domain roles → USER_GATE; resolve one → ROLE_INTERNAL."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        # Before resolution: USER_GATE
        decision_before = self.engine.check_escalation("task-1")
        self.assertEqual(decision_before.level, EscalationLevel.USER_GATE)

        # Resolve quality-engineer's veto
        self.engine.resolve_veto("v-1", "Coverage fixed")
        decision_after = self.engine.check_escalation("task-1")
        self.assertEqual(decision_after.level, EscalationLevel.ROLE_INTERNAL)

    def test_resolve_both_clears(self):
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        self.engine.resolve_veto("v-1", "Done")
        self.engine.resolve_veto("v-2", "Done")
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertIn("No active BLOCKER", decision.reason)

    def test_is_resolved_flag(self):
        self.engine.record_veto(_make_veto(veto_id="v-resolve-me"))
        self.assertFalse(self.engine.is_resolved("v-resolve-me"))
        self.engine.resolve_veto("v-resolve-me", "Fixed")
        self.assertTrue(self.engine.is_resolved("v-resolve-me"))

    def test_resolve_unknown_veto_id_no_error(self):
        """Resolving a non-existent veto ID should not raise an error."""
        self.engine.resolve_veto("nonexistent", "Doesn't matter")
        self.assertTrue(self.engine.is_resolved("nonexistent"))


class HumanReviewPacketTest(unittest.TestCase):
    """generate_human_review_packet produces readable markdown output."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_packet_contains_key_sections(self):
        self.engine.record_veto(_make_veto(
            veto_id="v-sec", role_id="security-engineer",
            reason="Critical vulnerability in auth module",
            evidence_refs=["audit.json", "cve-2026-1234.md"],
            remediation="Upgrade authlib to v3.2.1",
        ))
        self.engine.record_veto(_make_veto(
            veto_id="v-qa", role_id="quality-engineer",
            reason="Test coverage only 62%",
            remediation="Add integration tests for auth flow",
        ))

        packet = self.engine.generate_human_review_packet("task-1")

        # Structural sections
        self.assertIn("HUMAN REVIEW PACKET", packet)
        self.assertIn("DECISION REQUIRED", packet)
        self.assertIn("BLOCKER VETOES", packet)
        self.assertIn("SUGGESTED RESOLUTIONS", packet)
        self.assertIn("END OF HUMAN REVIEW PACKET", packet)

        # Content
        self.assertIn("task-1", packet)
        self.assertIn("security-engineer", packet)
        self.assertIn("quality-engineer", packet)
        self.assertIn("Critical vulnerability", packet)
        self.assertIn("coverage", packet.lower())
        self.assertIn("Upgrade authlib", packet)
        self.assertIn("integration tests", packet.lower())

    def test_packet_with_no_blockers(self):
        """Packet for a task with zero BLOCKER vetoes."""
        packet = self.engine.generate_human_review_packet("task-empty")
        self.assertIn("HUMAN REVIEW PACKET", packet)
        self.assertIn("No blocking vetoes active", packet)
        self.assertIn("task-empty", packet)

    def test_packet_includes_warnings_section(self):
        self.engine.record_veto(_make_veto(
            veto_id="v-blk", role_id="quality-engineer",
            severity=VetoSeverity.BLOCKER, reason="Coverage too low",
        ))
        self.engine.record_veto(_make_veto(
            veto_id="v-warn", role_id="developer",
            severity=VetoSeverity.WARNING, reason="Naming convention drift",
        ))
        packet = self.engine.generate_human_review_packet("task-1")
        self.assertIn("WARNINGS", packet)
        self.assertIn("Naming convention", packet)

    def test_packet_with_no_remediation(self):
        """Packet lists 'No remediation suggestions' when none provided."""
        self.engine.record_veto(_make_veto(
            veto_id="v-nofix", role_id="delivery-manager",
            reason="Deadline cannot be met",
            remediation="",  # no remediation
        ))
        packet = self.engine.generate_human_review_packet("task-1")
        self.assertIn("No remediation suggestions", packet)

    def test_packet_escalation_level_displayed(self):
        self.engine.record_veto(_make_veto(role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        packet = self.engine.generate_human_review_packet(
            "task-1",
            escalation_level=EscalationLevel.USER_GATE,
            escalation_reason="Cross-domain conflict.",
        )
        self.assertIn("user_gate", packet.lower())


class EdgeCasesTest(unittest.TestCase):
    """Boundary conditions and edge cases."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_no_vetoes_at_all(self):
        decision = self.engine.check_escalation("task-nonexistent")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertIn("No active BLOCKER", decision.reason)
        self.assertEqual(decision.involved_roles, [])
        self.assertIsNone(decision.human_review_packet)

    def test_all_vetoes_resolved(self):
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager"))
        self.engine.resolve_veto("v-1", "Fixed")
        self.engine.resolve_veto("v-2", "Fixed")
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertEqual(len(decision.involved_roles), 0)

    def test_unknown_role_gets_unknown_domain(self):
        """A role not in ROLE_DOMAINS gets domain 'unknown' and still works."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="mystery-role"))
        decision = self.engine.check_escalation("task-1")
        self.assertEqual(decision.level, EscalationLevel.ROLE_INTERNAL)
        self.assertIn("mystery-role", decision.reason)

    def test_two_unknown_roles_treated_as_same_domain(self):
        """Two roles both unknown → same domain → CROSS_ROLE."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="unknown-a"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="unknown-b"))
        decision = self.engine.check_escalation("task-1")
        # Both map to 'unknown' domain → CROSS_ROLE
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)

    def test_get_active_vetoes_returns_only_unresolved(self):
        self.engine.record_veto(_make_veto(veto_id="v-1"))
        self.engine.record_veto(_make_veto(veto_id="v-2"))
        self.engine.record_veto(_make_veto(veto_id="v-3"))
        self.engine.resolve_veto("v-2", "Done")

        active = self.engine.get_active_vetoes("task-1")
        self.assertEqual(len(active), 2)
        active_ids = {v.veto_id for v in active}
        self.assertIn("v-1", active_ids)
        self.assertNotIn("v-2", active_ids)
        self.assertIn("v-3", active_ids)

    def test_multiple_tasks_isolation(self):
        """Vetoes for different tasks do not interfere."""
        self.engine.record_veto(_make_veto(veto_id="v-a", task_id="task-a",
                                            role_id="quality-engineer"))
        self.engine.record_veto(_make_veto(veto_id="v-b", task_id="task-b",
                                            role_id="delivery-manager"))

        # task-a has only quality-engineer → ROLE_INTERNAL
        dec_a = self.engine.check_escalation("task-a")
        self.assertEqual(dec_a.level, EscalationLevel.ROLE_INTERNAL)

        # task-b has only delivery-manager → ROLE_INTERNAL
        dec_b = self.engine.check_escalation("task-b")
        self.assertEqual(dec_b.level, EscalationLevel.ROLE_INTERNAL)

        # task-c untouched → no blockers
        dec_c = self.engine.check_escalation("task-c")
        self.assertIn("No active BLOCKER", dec_c.reason)

    def test_escalation_decision_fields_populated(self):
        """EscalationDecision has all fields populated correctly."""
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer",
                                            reason="Reason Q"))
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager",
                                            reason="Reason D"))
        decision = self.engine.check_escalation("task-1")

        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        self.assertIsNotNone(decision.reason)
        self.assertTrue(len(decision.reason) > 0)
        self.assertEqual(decision.involved_roles, ["delivery-manager", "quality-engineer"])
        self.assertIn("Reason Q", decision.veto_summary)
        self.assertIn("Reason D", decision.veto_summary)
        self.assertIsNotNone(decision.human_review_packet)
        self.assertTrue(len(decision.human_review_packet) > 0)

    def test_severity_enum_values(self):
        self.assertEqual(VetoSeverity.BLOCKER.value, "blocker")
        self.assertEqual(VetoSeverity.WARNING.value, "warning")

    def test_escalation_level_enum_values(self):
        self.assertEqual(EscalationLevel.ROLE_INTERNAL.value, "role_internal")
        self.assertEqual(EscalationLevel.CROSS_ROLE.value, "cross_role")
        self.assertEqual(EscalationLevel.USER_GATE.value, "user_gate")

    def test_role_domains_mapping_complete(self):
        """Verify all known roles have domain mappings."""
        known_roles = [
            "security-engineer", "quality-engineer", "delivery-manager",
            "developer", "system-architect", "module-architect",
            "product-manager", "project-manager", "release-engineer",
            "independent-reviewer",
        ]
        for role in known_roles:
            self.assertIn(role, ROLE_DOMAINS, f"Role {role} missing from ROLE_DOMAINS")
            self.assertIsNotNone(ROLE_DOMAINS[role])

    def test_cross_role_only_pairs_are_frozensets(self):
        """CROSS_ROLE_ONLY_DOMAIN_PAIRS contains frozensets of domains."""
        self.assertIn(frozenset({"architecture", "development"}),
                      CROSS_ROLE_ONLY_DOMAIN_PAIRS)


class RealWorldScenarioTest(unittest.TestCase):
    """End-to-end scenarios that mimic real deadlock situations."""

    def setUp(self):
        self.engine = VetoEscalation()

    def test_scenario_quality_blocks_security_also_blocks(self):
        """Quality vetoes on low coverage; security also vetoes on a CVE.
        This should escalate to USER_GATE immediately due to security rule."""
        self.engine.record_veto(_make_veto(
            veto_id="v-qa", role_id="quality-engineer",
            task_id="task-auth",
            reason="Coverage dropped to 61% after last commit",
            remediation="Add unit tests for new API handlers",
        ))
        self.engine.record_veto(_make_veto(
            veto_id="v-sec", role_id="security-engineer",
            task_id="task-auth",
            reason="CVE-2026-9999: Remote code execution in image parser",
            evidence_refs=["trivy-scan.json", "cve-2026-9999.md"],
            remediation="Upgrade image-parser to >= 4.1.0 or apply patch",
        ))
        decision = self.engine.check_escalation("task-auth")
        self.assertEqual(decision.level, EscalationLevel.USER_GATE)
        # Verify the packet contains both vetoes
        self.assertIn("v-qa", decision.human_review_packet)
        self.assertIn("v-sec", decision.human_review_packet)

    def test_scenario_architect_blocks_developer_agrees(self):
        """Architect vetoes on design; developer also vetoes but for different reason.
        This should be CROSS_ROLE because architecture+development is a special pair."""
        self.engine.record_veto(_make_veto(
            veto_id="v-arch", role_id="system-architect",
            task_id="task-design",
            reason="New module breaks layering principle",
            remediation="Move data access to repository layer",
        ))
        self.engine.record_veto(_make_veto(
            veto_id="v-dev", role_id="developer",
            task_id="task-design",
            reason="Repository layer adds too much indirection for this use case",
            remediation="Consider a simpler data-access approach",
        ))
        decision = self.engine.check_escalation("task-design")
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)
        self.assertIsNone(decision.human_review_packet)
        self.assertIn("closely coupled", decision.reason.lower())

    def test_scenario_step_by_step_escalation(self):
        """Simulate a project progressing through veto stages."""
        # Stage 1: Quality engineer flags a concern
        self.engine.record_veto(_make_veto(veto_id="v-1", role_id="quality-engineer",
                                            task_id="task-proj"))
        d1 = self.engine.check_escalation("task-proj")
        self.assertEqual(d1.level, EscalationLevel.ROLE_INTERNAL)

        # Stage 2: Delivery manager also vetoes → cross-domain
        self.engine.record_veto(_make_veto(veto_id="v-2", role_id="delivery-manager",
                                            task_id="task-proj"))
        d2 = self.engine.check_escalation("task-proj")
        self.assertEqual(d2.level, EscalationLevel.USER_GATE)

        # Stage 3: Quality engineer resolves their veto
        self.engine.resolve_veto("v-1", "Coverage improved")
        d3 = self.engine.check_escalation("task-proj")
        self.assertEqual(d3.level, EscalationLevel.ROLE_INTERNAL)

        # Stage 4: Delivery manager also resolves
        self.engine.resolve_veto("v-2", "Schedule renegotiated")
        d4 = self.engine.check_escalation("task-proj")
        self.assertIn("No active BLOCKER", d4.reason)

    def test_scenario_architect_module_architect_conflict(self):
        """Two architects disagree on module boundary → CROSS_ROLE (same domain)."""
        self.engine.record_veto(_make_veto(
            veto_id="v-sys", role_id="system-architect",
            task_id="task-boundary",
            reason="Module should be a separate service",
        ))
        self.engine.record_veto(_make_veto(
            veto_id="v-mod", role_id="module-architect",
            task_id="task-boundary",
            reason="Module is fine as a library within the monolith",
        ))
        decision = self.engine.check_escalation("task-boundary")
        self.assertEqual(decision.level, EscalationLevel.CROSS_ROLE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
