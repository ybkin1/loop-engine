"""
Unit tests for loop_core.hard_constraints — Hard constraint checker.

Covers all 8 hard constraints:
  - C1: Requirements baseline (pass + violate)
  - C2: Architecture baseline (pass + violate)
  - C3: Task package (pass + violate)
  - C4: Path scope (pass + violate + empty allowed_paths)
  - C5: Verification (pass + violate: missing + failed)
  - C6: Independent review (pass + violate: missing + BLOCKED)
  - C7: Blockers (pass + violate: gates + tasks)
  - C8: Evidence freshness (pass + violate: expired + hash changed)

Also covers:
  - check_all with all-passing context returns passed=True
  - check_all with any BLOCKER returns passed=False
  - ConstraintCheckResult properties (blocker_count, warning_count)
  - EvidenceEnvelope.is_fresh() and has_hash_changed()
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.state_machine import Phase, GateStatus, TaskStatus
from loop_core.hard_constraints import (
    ConstraintID,
    Severity,
    ConstraintViolation,
    ConstraintCheckResult,
    EvidenceEnvelope,
    HardConstraints,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_context(**overrides):
    """Create a default context dict for check_all, with overrides."""
    ctx = {
        "current_phase": Phase.S0_INIT,
        "target_phase": None,
        "phase_gates": {},
        "gates": {},
        "tasks": [],
        "target_path": None,
        "allowed_paths": [],
        "quality_results": {},
        "review_status": {},
        "evidence_list": [],
        "current_hashes": {},
    }
    ctx.update(overrides)
    return ctx


def _fresh_evidence(
    evidence_id: str = "ev-001",
    content_hash: str = "abc123",
    offset_hours: int = 24,
    phase: Phase | None = None,
) -> EvidenceEnvelope:
    """Create a fresh (non-stale) evidence envelope."""
    now = datetime.now(timezone.utc)
    return EvidenceEnvelope(
        evidence_id=evidence_id,
        content_hash=content_hash,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(hours=offset_hours)).isoformat(),
        phase=phase,
    )


def _expired_evidence(
    evidence_id: str = "ev-old",
    content_hash: str = "exp123",
) -> EvidenceEnvelope:
    """Create an expired evidence envelope."""
    now = datetime.now(timezone.utc)
    return EvidenceEnvelope(
        evidence_id=evidence_id,
        content_hash=content_hash,
        created_at=(now - timedelta(hours=48)).isoformat(),
        expires_at=(now - timedelta(hours=24)).isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# EvidenceEnvelope tests
# ═══════════════════════════════════════════════════════════════════════════


class TestEvidenceEnvelope:
    """Tests for EvidenceEnvelope freshness and hash checking."""

    def test_is_fresh_when_not_expired(self):
        """Evidence in the future is fresh."""
        ev = _fresh_evidence(offset_hours=48)
        assert ev.is_fresh() is True

    def test_is_fresh_when_expired(self):
        """Evidence past expiration is not fresh."""
        ev = _expired_evidence()
        assert ev.is_fresh() is False

    def test_is_fresh_when_no_expiration(self):
        """Evidence with no expiration is always fresh."""
        ev = EvidenceEnvelope(
            evidence_id="ev-forever",
            content_hash="hash0",
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=None,
        )
        assert ev.is_fresh() is True

    def test_has_hash_changed_when_same(self):
        """Same hash returns False."""
        ev = EvidenceEnvelope(
            evidence_id="ev-same",
            content_hash="abc",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert ev.has_hash_changed("abc") is False

    def test_has_hash_changed_when_different(self):
        """Different hash returns True."""
        ev = EvidenceEnvelope(
            evidence_id="ev-diff",
            content_hash="old_hash",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert ev.has_hash_changed("new_hash") is True


# ═══════════════════════════════════════════════════════════════════════════
# C1: Requirements Baseline
# ═══════════════════════════════════════════════════════════════════════════


class TestC1RequirementsBaseline:
    """Tests for C1: No requirements baseline -> no formal implementation."""

    def test_pass_when_requirements_gate_approved(self):
        """C1 passes when S1-requirements gate is APPROVED and entering S4."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={Phase.S1_REQUIREMENTS: GateStatus.APPROVED},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 0

    def test_violate_when_requirements_gate_missing(self):
        """C1 violates when S1-requirements gate is completely missing."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C1_NO_REQUIREMENTS
        assert violations[0].severity == Severity.BLOCKER

    def test_violate_when_requirements_gate_pending(self):
        """C1 violates when S1-requirements gate is PENDING (not approved)."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={Phase.S1_REQUIREMENTS: GateStatus.PENDING},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 1
        assert violations[0].severity == Severity.BLOCKER

    def test_not_applicable_when_not_entering_s4(self):
        """C1 does not trigger when target_phase is not S4."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S1_REQUIREMENTS,
            phase_gates={},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 0

    def test_violate_when_already_in_s4_without_requirements(self):
        """C1 also triggers when current_phase is S4 and requirements gate missing."""
        hc = HardConstraints()
        ctx = _make_context(
            current_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 1

    def test_string_key_fallback(self):
        """C1 works with string key fallback when Phase enum key not present."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={"S1-requirements": GateStatus.APPROVED},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 0

    def test_relevant_in_s2_architecture(self):
        """C1 triggers when entering S2-architecture without requirements."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S2_ARCHITECTURE,
            phase_gates={},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C1_NO_REQUIREMENTS

    def test_relevant_in_s3_interface(self):
        """C1 triggers when entering S3-interface without requirements."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S3_INTERFACE,
            phase_gates={},
        )
        violations = hc.check_c1_requirements_baseline(ctx)
        assert len(violations) == 1


# ═══════════════════════════════════════════════════════════════════════════
# C2: Architecture Baseline
# ═══════════════════════════════════════════════════════════════════════════


class TestC2ArchitectureBaseline:
    """Tests for C2: No architecture baseline -> no development."""

    def test_pass_when_architecture_gate_approved(self):
        """C2 passes when S2-architecture gate is APPROVED and entering S4."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={Phase.S2_ARCHITECTURE: GateStatus.APPROVED},
        )
        violations = hc.check_c2_architecture_baseline(ctx)
        assert len(violations) == 0

    def test_violate_when_architecture_gate_missing(self):
        """C2 violates when S2-architecture gate is missing entirely."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={},
        )
        violations = hc.check_c2_architecture_baseline(ctx)
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C2_NO_ARCHITECTURE
        assert violations[0].severity == Severity.BLOCKER

    def test_violate_when_architecture_gate_blocked(self):
        """C2 violates when S2-architecture gate is BLOCKED."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={Phase.S2_ARCHITECTURE: GateStatus.BLOCKED},
        )
        violations = hc.check_c2_architecture_baseline(ctx)
        assert len(violations) == 1
        assert violations[0].severity == Severity.BLOCKER

    def test_not_applicable_when_not_entering_s2_s3_s4(self):
        """C2 does not trigger for phases outside S2/S3/S4."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S0_INIT,
            phase_gates={},
        )
        violations = hc.check_c2_architecture_baseline(ctx)
        assert len(violations) == 0

    def test_string_key_fallback(self):
        """C2 works with string key fallback when Phase enum key not present."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={"S2-architecture": GateStatus.APPROVED},
        )
        violations = hc.check_c2_architecture_baseline(ctx)
        assert len(violations) == 0

    def test_relevant_in_s3_interface(self):
        """C2 triggers when entering S3-interface without architecture."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S3_INTERFACE,
            phase_gates={},
        )
        violations = hc.check_c2_architecture_baseline(ctx)
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C2_NO_ARCHITECTURE


# ═══════════════════════════════════════════════════════════════════════════
# C3: Task Package
# ═══════════════════════════════════════════════════════════════════════════


class TestC3TaskPackage:
    """Tests for C3: No active task package -> no code writing."""

    def test_pass_with_active_task(self):
        """C3 passes when at least one task is active."""
        hc = HardConstraints()
        tasks = [
            {"id": "task-1", "status": TaskStatus.ACTIVE.value},
        ]
        violations = hc.check_c3_task_package(tasks)
        assert len(violations) == 0

    def test_pass_with_in_progress_task(self):
        """C3 passes when at least one task is in_progress."""
        hc = HardConstraints()
        tasks = [
            {"id": "task-1", "status": TaskStatus.IN_PROGRESS.value},
        ]
        violations = hc.check_c3_task_package(tasks)
        assert len(violations) == 0

    def test_pass_with_mixed_tasks(self):
        """C3 passes when there is one active among pending/completed tasks."""
        hc = HardConstraints()
        tasks = [
            {"id": "task-1", "status": TaskStatus.PENDING.value},
            {"id": "task-2", "status": TaskStatus.ACTIVE.value},
            {"id": "task-3", "status": TaskStatus.COMPLETED.value},
        ]
        violations = hc.check_c3_task_package(tasks)
        assert len(violations) == 0

    def test_violate_when_no_tasks(self):
        """C3 violates when task list is empty."""
        hc = HardConstraints()
        violations = hc.check_c3_task_package([])
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C3_NO_TASK_PACKAGE
        assert violations[0].severity == Severity.BLOCKER

    def test_violate_when_all_tasks_pending(self):
        """C3 violates when all tasks are PENDING (none active)."""
        hc = HardConstraints()
        tasks = [
            {"id": "task-1", "status": TaskStatus.PENDING.value},
            {"id": "task-2", "status": TaskStatus.PENDING.value},
        ]
        violations = hc.check_c3_task_package(tasks)
        assert len(violations) == 1

    def test_violate_when_all_tasks_blocked(self):
        """C3 violates when all tasks are BLOCKED."""
        hc = HardConstraints()
        tasks = [
            {"id": "task-1", "status": TaskStatus.BLOCKED.value},
        ]
        violations = hc.check_c3_task_package(tasks)
        assert len(violations) == 1


# ═══════════════════════════════════════════════════════════════════════════
# C4: Path Scope
# ═══════════════════════════════════════════════════════════════════════════


class TestC4PathScope:
    """Tests for C4: Target path outside allowed scope -> write denied."""

    def test_pass_with_exact_match(self):
        """C4 passes when target_path exactly matches an allowed path."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "src/main.py",
            ["src/main.py"],
        )
        assert len(violations) == 0

    def test_pass_with_parent_directory(self):
        """C4 passes when target_path is inside an allowed directory."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "src/module/sub.py",
            ["src/"],
        )
        assert len(violations) == 0

    def test_pass_with_multiple_allowed(self):
        """C4 passes when target matches one of several allowed paths."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "tests/test_x.py",
            ["src/", "tests/", "docs/"],
        )
        assert len(violations) == 0

    def test_violate_when_path_outside_scope(self):
        """C4 violates when target is outside all allowed paths."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "/etc/passwd",
            ["src/", "tests/"],
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C4_PATH_OUT_OF_SCOPE
        assert violations[0].severity == Severity.BLOCKER

    def test_violate_when_no_allowed_paths(self):
        """C4 violates when allowed_paths is empty."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "src/main.py",
            [],
        )
        assert len(violations) == 1

    def test_violate_with_partial_prefix_mismatch(self):
        """C4 violates when target shares a prefix but is not actually inside."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "src_other/file.py",
            ["src/"],
        )
        assert len(violations) == 1

    def test_pass_with_windows_backslash_paths(self):
        """C4 handles Windows backslash paths correctly after normalization."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "src\\module\\sub.py",
            ["src\\", "tests\\"],
        )
        assert len(violations) == 0

    def test_pass_with_mixed_slash_paths(self):
        """C4 handles mixed forward/backslash paths."""
        hc = HardConstraints()
        violations = hc.check_c4_path_scope(
            "src/module\\sub.py",
            ["src/"],
        )
        assert len(violations) == 0


# ═══════════════════════════════════════════════════════════════════════════
# C5: Verification
# ═══════════════════════════════════════════════════════════════════════════


class TestC5Verification:
    """Tests for C5: No deterministic verification -> no delivery."""

    def test_pass_when_all_checks_pass(self):
        """C5 passes when test, lint, build all return PASS."""
        hc = HardConstraints()
        violations = hc.check_c5_verification(
            quality_results={"test": "PASS", "lint": "PASS", "build": "PASS"},
            target_phase=Phase.S6_DELIVERY,
        )
        assert len(violations) == 0

    def test_violate_when_test_fails(self):
        """C5 violates when test does not return PASS."""
        hc = HardConstraints()
        violations = hc.check_c5_verification(
            quality_results={"test": "FAIL", "lint": "PASS", "build": "PASS"},
            target_phase=Phase.S6_DELIVERY,
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C5_NO_VERIFICATION
        assert violations[0].severity == Severity.BLOCKER

    def test_violate_when_lint_missing(self):
        """C5 violates when lint result is missing entirely."""
        hc = HardConstraints()
        violations = hc.check_c5_verification(
            quality_results={"test": "PASS", "build": "PASS"},
            target_phase=Phase.S6_DELIVERY,
        )
        assert len(violations) == 1

    def test_violate_when_build_missing(self):
        """C5 violates when build result is missing."""
        hc = HardConstraints()
        violations = hc.check_c5_verification(
            quality_results={"test": "PASS", "lint": "PASS"},
            target_phase=Phase.S6_DELIVERY,
        )
        assert len(violations) == 1

    def test_not_applicable_when_not_entering_delivery(self):
        """C5 does not trigger for non-S6 target phases."""
        hc = HardConstraints()
        violations = hc.check_c5_verification(
            quality_results={},
            target_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 0

    def test_not_applicable_when_target_phase_is_none(self):
        """C5 does not trigger when target_phase is None (with warning)."""
        hc = HardConstraints()
        import warnings as _warnings
        with _warnings.catch_warnings(record=True) as w:
            _warnings.simplefilter("always")
            violations = hc.check_c5_verification(
                quality_results={},
                target_phase=None,
            )
            assert len(violations) == 0
            assert len(w) == 1
            assert "target_phase=None" in str(w[0].message)


# ═══════════════════════════════════════════════════════════════════════════
# C6: Independent Review
# ═══════════════════════════════════════════════════════════════════════════


class TestC6IndependentReview:
    """Tests for C6: No independent review -> cannot pass implementation gate."""

    def test_pass_when_reviewer_passes(self):
        """C6 passes when independent-reviewer verdict is PASS."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={"independent-reviewer": "PASS"},
            current_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 0

    def test_violate_when_no_review_submitted(self):
        """C6 violates when independent-reviewer has not submitted."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={},
            current_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C6_NO_INDEPENDENT_REVIEW
        assert violations[0].severity == Severity.BLOCKER

    def test_violate_when_reviewer_blocked(self):
        """C6 produces WARNING when independent-reviewer returned BLOCKED."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={
                "independent-reviewer": "BLOCKED",
                "findings": "Security vulnerability in auth module",
            },
            current_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_not_applicable_when_not_in_implementation(self):
        """C6 does not trigger when current_phase is not S4."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={},
            current_phase=Phase.S1_REQUIREMENTS,
        )
        assert len(violations) == 0

    def test_not_applicable_when_phase_is_none(self):
        """C6 does not trigger when current_phase is None (with warning)."""
        hc = HardConstraints()
        import warnings as _warnings
        with _warnings.catch_warnings(record=True) as w:
            _warnings.simplefilter("always")
            violations = hc.check_c6_independent_review(
                review_status={},
                current_phase=None,
            )
            assert len(violations) == 0
            assert len(w) == 1
            assert "current_phase=None" in str(w[0].message)

    def test_warning_when_reviewer_pending(self):
        """C6 produces WARNING when independent-reviewer verdict is PENDING."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={"independent-reviewer": "PENDING"},
            current_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert "PENDING" in violations[0].message

    def test_warning_when_reviewer_fail(self):
        """C6 produces WARNING when independent-reviewer verdict is FAIL."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={"independent-reviewer": "FAIL"},
            current_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_warning_when_reviewer_unknown(self):
        """C6 produces WARNING when independent-reviewer verdict is unknown."""
        hc = HardConstraints()
        violations = hc.check_c6_independent_review(
            review_status={"independent-reviewer": "UNKNOWN_VERDICT"},
            current_phase=Phase.S4_IMPLEMENTATION,
        )
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING


# ═══════════════════════════════════════════════════════════════════════════
# C7: Blockers
# ═══════════════════════════════════════════════════════════════════════════


class TestC7Blockers:
    """Tests for C7: Blockers exist -> cannot advance phase."""

    def test_pass_when_no_blockers(self):
        """C7 passes when no gates or tasks are blocked."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={Phase.S1_REQUIREMENTS: GateStatus.APPROVED},
            tasks=[{"id": "task-1", "status": TaskStatus.ACTIVE.value}],
        )
        assert len(violations) == 0

    def test_pass_with_empty_gates_and_tasks(self):
        """C7 passes when there are no gates and no tasks."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={},
            tasks=[],
        )
        assert len(violations) == 0

    def test_pass_with_none_gates(self):
        """C7 passes when gates is None."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates=None,
            tasks=[{"id": "task-1", "status": TaskStatus.ACTIVE.value}],
        )
        assert len(violations) == 0

    def test_violate_when_gate_is_blocked(self):
        """C7 violates when any gate has BLOCKED status."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={Phase.S4_IMPLEMENTATION: GateStatus.BLOCKED},
            tasks=[],
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C7_BLOCKER_EXISTS
        assert violations[0].severity == Severity.BLOCKER
        assert "S4-implementation" in violations[0].detail

    def test_violate_when_task_is_blocked(self):
        """C7 violates when any task has blocked status."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={},
            tasks=[
                {"id": "task-1", "status": TaskStatus.COMPLETED.value},
                {"id": "task-2", "status": TaskStatus.BLOCKED.value},
            ],
        )
        assert len(violations) >= 1
        assert any(
            v.constraint_id == ConstraintID.C7_BLOCKER_EXISTS
            for v in violations
        )

    def test_violate_when_both_gate_and_task_blocked(self):
        """C7 produces multiple violations when both gates and tasks are blocked."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={Phase.S5_QUALITY: GateStatus.BLOCKED},
            tasks=[{"id": "task-99", "status": TaskStatus.BLOCKED.value}],
        )
        # Two violations: one for gate, one for task
        assert len(violations) == 2
        for v in violations:
            assert v.severity == Severity.BLOCKER

    def test_violate_with_string_gate_keys(self):
        """C7 handles string keys in the gates dict."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={"S3-interface": GateStatus.BLOCKED},
            tasks=[],
        )
        assert len(violations) == 1

    def test_warning_for_unrecognized_gate_status(self):
        """C7 produces WARNING when gate status string is not a valid GateStatus."""
        hc = HardConstraints()
        violations = hc.check_c7_blockers(
            gates={"S3-interface": "INVALID_STATUS"},
            tasks=[],
        )
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert violations[0].constraint_id == ConstraintID.C7_BLOCKER_EXISTS
        assert "INVALID_STATUS" in violations[0].message

    def test_type_error_for_non_dict_gates(self):
        """C7 raises TypeError when gates is not a dict or None."""
        hc = HardConstraints()
        import pytest
        with pytest.raises(TypeError, match="gates must be a dict or None"):
            hc.check_c7_blockers(gates="not_a_dict", tasks=[])


# ═══════════════════════════════════════════════════════════════════════════
# C8: Evidence Freshness
# ═══════════════════════════════════════════════════════════════════════════


class TestC8EvidenceFreshness:
    """Tests for C8: Stale evidence -> old results invalidated."""

    def test_pass_when_all_evidence_fresh(self):
        """C8 passes when all evidence is fresh and hashes match."""
        hc = HardConstraints()
        ev = _fresh_evidence("ev-001", "abc")
        violations = hc.check_c8_evidence_freshness(
            evidence_list=[ev],
            current_hashes={"ev-001": "abc"},
        )
        assert len(violations) == 0

    def test_pass_with_empty_evidence_list(self):
        """C8 passes when there is no evidence to check."""
        hc = HardConstraints()
        violations = hc.check_c8_evidence_freshness([])
        assert len(violations) == 0

    def test_violate_when_evidence_expired(self):
        """C8 violates when evidence has passed its expiration."""
        hc = HardConstraints()
        ev = _expired_evidence("ev-old", "oldhash")
        violations = hc.check_c8_evidence_freshness(
            evidence_list=[ev],
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C8_STALE_EVIDENCE
        assert violations[0].severity == Severity.BLOCKER
        assert "expired" in violations[0].detail.lower()

    def test_violate_when_hash_changed(self):
        """C8 violates when content hash differs from recorded hash."""
        hc = HardConstraints()
        ev = _fresh_evidence("ev-001", "recorded_hash_abc")
        violations = hc.check_c8_evidence_freshness(
            evidence_list=[ev],
            current_hashes={"ev-001": "different_hash_xyz"},
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C8_STALE_EVIDENCE
        assert "hash changed" in violations[0].detail.lower()

    def test_violate_when_both_expired_and_hash_changed(self):
        """C8 produces single violation even when both freshness checks fail."""
        hc = HardConstraints()
        ev = _expired_evidence("ev-both", "oldhash")
        violations = hc.check_c8_evidence_freshness(
            evidence_list=[ev],
            current_hashes={"ev-both": "newhash"},
        )
        # Single violation per evidence, even with multiple reasons
        assert len(violations) == 1
        assert "expired" in violations[0].detail.lower()
        assert "hash changed" in violations[0].detail.lower()

    def test_violate_multiple_stale_evidence(self):
        """C8 returns one violation per stale evidence item."""
        hc = HardConstraints()
        ev1 = _expired_evidence("ev-1", "h1")
        ev2 = _expired_evidence("ev-2", "h2")
        violations = hc.check_c8_evidence_freshness(
            evidence_list=[ev1, ev2],
        )
        assert len(violations) == 2

    def test_warning_for_non_envelope_object(self):
        """C8 produces WARNING when evidence_list contains non-EvidenceEnvelope items."""
        hc = HardConstraints()
        ev = _fresh_evidence("ev-001", "abc")
        violations = hc.check_c8_evidence_freshness(
            evidence_list=[ev, "not_an_envelope", 42, {"key": "value"}],
        )
        # 1 fresh evidence + 3 non-envelope warnings = 4 total
        assert len(violations) == 3
        non_env = [v for v in violations if "Non-EvidenceEnvelope" in v.message]
        assert len(non_env) == 3
        for v in non_env:
            assert v.severity == Severity.WARNING
            assert v.constraint_id == ConstraintID.C8_STALE_EVIDENCE


# ═══════════════════════════════════════════════════════════════════════════
# check_all integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckAll:
    """Integration tests for HardConstraints.check_all()."""

    def test_all_pass_with_clean_context(self):
        """check_all returns passed=True when no constraint is violated."""
        hc = HardConstraints()
        ctx = _make_context(
            current_phase=Phase.S1_REQUIREMENTS,
            target_phase=Phase.S2_ARCHITECTURE,
            phase_gates={
                Phase.S1_REQUIREMENTS: GateStatus.APPROVED,
                Phase.S2_ARCHITECTURE: GateStatus.APPROVED,
            },
            tasks=[{"id": "task-1", "status": TaskStatus.ACTIVE.value}],
            target_path="src/main.py",
            allowed_paths=["src/"],
            quality_results={"test": "PASS", "lint": "PASS", "build": "PASS"},
            review_status={"independent-reviewer": "PASS"},
            gates={Phase.S1_REQUIREMENTS: GateStatus.APPROVED},
            evidence_list=[_fresh_evidence()],
            current_hashes={"ev-001": "abc123"},
        )
        result = hc.check_all(ctx)
        assert result.passed is True
        assert len(result.violations) == 0
        assert result.blocker_count == 0
        assert result.warning_count == 0

    def test_fails_with_c4_path_out_of_scope(self):
        """check_all returns passed=False when C4 is violated."""
        hc = HardConstraints()
        ctx = _make_context(
            target_path="/etc/shadow",
            allowed_paths=["src/"],
            tasks=[{"id": "t1", "status": TaskStatus.ACTIVE.value}],
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        assert result.blocker_count >= 1
        c4_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C4_PATH_OUT_OF_SCOPE
        ]
        assert len(c4_violations) == 1

    def test_fails_when_no_active_tasks(self):
        """check_all returns passed=False when C3 is violated."""
        hc = HardConstraints()
        ctx = _make_context(
            tasks=[],
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        assert result.blocker_count >= 1
        c3_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C3_NO_TASK_PACKAGE
        ]
        assert len(c3_violations) == 1

    def test_fails_when_requirements_gate_missing_for_s4(self):
        """check_all returns passed=False when C1 is violated entering S4."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={},
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        c1_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C1_NO_REQUIREMENTS
        ]
        c2_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C2_NO_ARCHITECTURE
        ]
        assert len(c1_violations) == 1
        assert len(c2_violations) == 1

    def test_fails_when_verification_missing_for_delivery(self):
        """check_all returns passed=False when C5 is violated entering S6."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S6_DELIVERY,
            quality_results={},
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        c5_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C5_NO_VERIFICATION
        ]
        assert len(c5_violations) == 1

    def test_fails_when_review_missing_in_s4(self):
        """check_all returns passed=False when C6 is violated in S4."""
        hc = HardConstraints()
        ctx = _make_context(
            current_phase=Phase.S4_IMPLEMENTATION,
            review_status={},
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        c6_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C6_NO_INDEPENDENT_REVIEW
        ]
        assert len(c6_violations) == 1

    def test_fails_when_blocked_gate_exists(self):
        """check_all returns passed=False when C7 is violated by blocked gate."""
        hc = HardConstraints()
        ctx = _make_context(
            gates={Phase.S4_IMPLEMENTATION: GateStatus.BLOCKED},
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        c7_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C7_BLOCKER_EXISTS
        ]
        assert len(c7_violations) == 1

    def test_fails_when_evidence_stale(self):
        """check_all returns passed=False when C8 is violated by stale evidence."""
        hc = HardConstraints()
        ctx = _make_context(
            evidence_list=[_expired_evidence()],
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        c8_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C8_STALE_EVIDENCE
        ]
        assert len(c8_violations) == 1

    def test_multiple_violations_aggregated(self):
        """check_all collects violations from multiple constraints."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={},  # triggers C1 and C2
            tasks=[],        # triggers C3
            target_path="/bad/path",
            allowed_paths=["src/"],  # triggers C4
            gates={Phase.S5_QUALITY: GateStatus.BLOCKED},  # triggers C7
        )
        result = hc.check_all(ctx)
        assert result.passed is False
        # Should have violations from C1, C2, C3, C4, C7
        assert result.blocker_count >= 5

    def test_checked_at_is_populated(self):
        """check_all result includes an ISO 8601 timestamp."""
        hc = HardConstraints()
        result = hc.check_all(_make_context())
        assert result.checked_at is not None
        assert "T" in result.checked_at  # ISO 8601 includes T separator
        assert result.checked_at.endswith("+00:00") or result.checked_at.endswith("Z")

    def test_warning_violations_do_not_cause_passed_false(self):
        """WARNING-level violations do not cause check_all to return passed=False."""
        hc = HardConstraints()
        ctx = _make_context(
            current_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={
                Phase.S1_REQUIREMENTS: GateStatus.APPROVED,
                Phase.S2_ARCHITECTURE: GateStatus.APPROVED,
            },
            review_status={"independent-reviewer": "PENDING"},
            tasks=[{"id": "t1", "status": TaskStatus.ACTIVE.value}],
        )
        result = hc.check_all(ctx)
        # C6 produces WARNING for PENDING verdict
        # C1/C2 are satisfied by the approved phase_gates
        assert result.passed is True
        assert result.warning_count >= 1
        assert result.blocker_count == 0

    def test_c1_c2_repeated_check_returns_same_result(self):
        """C1/C2 regression: repeated checks produce consistent results."""
        hc = HardConstraints()
        ctx = _make_context(
            target_phase=Phase.S4_IMPLEMENTATION,
            phase_gates={
                Phase.S1_REQUIREMENTS: GateStatus.APPROVED,
                Phase.S2_ARCHITECTURE: GateStatus.APPROVED,
            },
        )
        result1 = hc.check_c1_requirements_baseline(ctx)
        result2 = hc.check_c1_requirements_baseline(ctx)
        assert len(result1) == len(result2) == 0

        result1 = hc.check_c2_architecture_baseline(ctx)
        result2 = hc.check_c2_architecture_baseline(ctx)
        assert len(result1) == len(result2) == 0


# ═══════════════════════════════════════════════════════════════════════════
# ConstraintCheckResult property tests
# ═══════════════════════════════════════════════════════════════════════════


class TestConstraintCheckResult:
    """Tests for ConstraintCheckResult dataclass properties."""

    def test_empty_result_is_passing(self):
        """A result with no violations is passing."""
        result = ConstraintCheckResult(passed=True)
        assert result.passed is True
        assert result.blocker_count == 0
        assert result.warning_count == 0

    def test_passed_false_when_blockers_exist(self):
        """A result with BLOCKER violations should have passed=False."""
        violations = [
            ConstraintViolation(
                constraint_id=ConstraintID.C1_NO_REQUIREMENTS,
                severity=Severity.BLOCKER,
                message="Test",
                detail="Test detail",
                remediation="Fix it",
            ),
        ]
        result = ConstraintCheckResult(passed=False, violations=violations)
        assert result.passed is False
        assert result.blocker_count == 1
        assert result.warning_count == 0

    def test_warning_count_excludes_blockers(self):
        """warning_count only counts WARNING severity violations."""
        violations = [
            ConstraintViolation(
                constraint_id=ConstraintID.C1_NO_REQUIREMENTS,
                severity=Severity.BLOCKER,
                message="B",
                detail="D",
                remediation="R",
            ),
            ConstraintViolation(
                constraint_id=ConstraintID.C8_STALE_EVIDENCE,
                severity=Severity.WARNING,
                message="W",
                detail="D",
                remediation="R",
            ),
        ]
        result = ConstraintCheckResult(passed=False, violations=violations)
        assert result.blocker_count == 1
        assert result.warning_count == 1
