"""
Unit tests for loop_core.verdicts: the unified verdict system (Phase 2).

Covers:
  - Verdict enum: exact member set, is_blocking(), is_conclusive()
  - ReportBinding: validate() missing-field reporting, dict round-trip
  - SecurityReport.bind(): fail-closed verdict for critical findings
  - AnalysisReport.bind(): FAIL verdict for error findings

All tests use in-memory data only — no external file dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ============================================================================
# Verdict enum tests
# ============================================================================

from loop_core.verdicts import Verdict, ReportBinding
from loop_core.security_scanner import SecurityReport, SecFinding
from loop_core.static_analyzer import AnalysisReport, Finding


class TestVerdictEnum:
    """Tests for the Verdict enum definition."""

    def test_verdict_contains_exactly_six_members(self):
        """Verdict should contain exactly the six unified verdicts, in order."""
        expected = ["PASS", "BLOCKED", "FAIL", "UNAVAILABLE", "NOT_VERIFIED", "ABSTAIN"]
        assert [member.name for member in Verdict] == expected

    def test_verdict_values_match_names(self):
        """Each verdict's value should equal its member name."""
        for verdict in Verdict:
            assert verdict.value == verdict.name

    def test_verdict_is_str_enum(self):
        """Verdict should be a str enum for serialization compatibility."""
        assert issubclass(Verdict, str)
        assert Verdict.PASS == "PASS"
        assert Verdict.BLOCKED == "BLOCKED"
        assert Verdict.NOT_VERIFIED == "NOT_VERIFIED"


class TestVerdictBlocking:
    """Tests for Verdict.is_blocking()."""

    def test_blocked_is_blocking(self):
        """BLOCKED should block further execution."""
        assert Verdict.BLOCKED.is_blocking() is True

    def test_pass_is_not_blocking(self):
        """PASS should never block."""
        assert Verdict.PASS.is_blocking() is False

    def test_fail_is_blocking(self):
        """FAIL should block further execution."""
        assert Verdict.FAIL.is_blocking() is True

    def test_unavailable_is_not_blocking(self):
        """UNAVAILABLE (tool missing) should not block."""
        assert Verdict.UNAVAILABLE.is_blocking() is False

    def test_not_verified_is_not_blocking(self):
        """NOT_VERIFIED (skipped check) should not block."""
        assert Verdict.NOT_VERIFIED.is_blocking() is False

    def test_abstain_is_not_blocking(self):
        """ABSTAIN (intentional skip) should not block."""
        assert Verdict.ABSTAIN.is_blocking() is False


class TestVerdictConclusive:
    """Tests for Verdict.is_conclusive()."""

    def test_pass_is_conclusive(self):
        """PASS represents a completed check."""
        assert Verdict.PASS.is_conclusive() is True

    def test_not_verified_is_not_conclusive(self):
        """NOT_VERIFIED represents an incomplete check."""
        assert Verdict.NOT_VERIFIED.is_conclusive() is False

    def test_blocked_is_conclusive(self):
        """BLOCKED represents a completed check with blocking issues."""
        assert Verdict.BLOCKED.is_conclusive() is True

    def test_fail_is_conclusive(self):
        """FAIL represents a completed check with non-blocking issues."""
        assert Verdict.FAIL.is_conclusive() is True

    def test_unavailable_is_not_conclusive(self):
        """UNAVAILABLE means the check could not run — not conclusive."""
        assert Verdict.UNAVAILABLE.is_conclusive() is False

    def test_abstain_is_not_conclusive(self):
        """ABSTAIN means the check was skipped — not conclusive."""
        assert Verdict.ABSTAIN.is_conclusive() is False


# ============================================================================
# ReportBinding tests
# ============================================================================

class TestReportBindingValidation:
    """Tests for ReportBinding.validate()."""

    def test_empty_binding_reports_all_required_missing(self):
        """An empty binding should report all four required fields missing."""
        binding = ReportBinding(task_id="", phase="")
        missing = binding.validate()
        assert "task_id" in missing
        assert "phase" in missing
        assert "git_commit" in missing
        assert "timestamp" in missing

    def test_partial_binding_reports_only_missing(self):
        """A partially filled binding should report only the missing fields."""
        binding = ReportBinding(task_id="T-0082", phase="S4-implementation")
        missing = binding.validate()
        assert "task_id" not in missing
        assert "phase" not in missing
        assert "git_commit" in missing
        assert "timestamp" in missing

    def test_valid_binding_has_no_missing_fields(self):
        """A fully populated binding should validate cleanly."""
        binding = ReportBinding(
            task_id="T-0082",
            phase="S4-implementation",
            git_commit="c6fda12",
            timestamp="2026-07-31T06:00:00+00:00",
        )
        assert binding.validate() == []

    def test_optional_fields_are_not_required(self):
        """gate_id/execution_id/diff_fingerprint/tool fields are optional."""
        binding = ReportBinding(
            task_id="T-0082",
            phase="S4-implementation",
            git_commit="c6fda12",
            timestamp="2026-07-31T06:00:00+00:00",
        )
        assert binding.gate_id is None
        assert binding.execution_id is None
        assert binding.diff_fingerprint is None
        assert binding.validate() == []


class TestReportBindingRoundTrip:
    """Tests for ReportBinding.to_dict()/from_dict()."""

    def test_round_trip_full_binding(self):
        """A fully populated binding should survive to_dict/from_dict intact."""
        original = ReportBinding(
            task_id="T-0082",
            phase="S4-implementation",
            gate_id="G-T-0082-REQUIREMENTS",
            execution_id="exec-12345",
            git_commit="c6fda12",
            diff_fingerprint="fp-abc123",
            timestamp="2026-07-31T06:00:00+00:00",
            tool_name="loop_core.security_scanner",
            tool_version="1.0",
        )
        restored = ReportBinding.from_dict(original.to_dict())
        assert restored.to_dict() == original.to_dict()

    def test_round_trip_minimal_binding(self):
        """A minimal binding with None optional fields should round-trip."""
        original = ReportBinding(task_id="T-0082", phase="S4-implementation")
        restored = ReportBinding.from_dict(original.to_dict())
        assert restored.to_dict() == original.to_dict()
        assert restored.task_id == "T-0082"
        assert restored.phase == "S4-implementation"
        assert restored.gate_id is None

    def test_from_dict_empty_dict_uses_defaults(self):
        """from_dict({}) should produce an empty binding, not raise."""
        restored = ReportBinding.from_dict({})
        assert restored.task_id == ""
        assert restored.phase == ""
        assert restored.gate_id is None

    def test_to_dict_contains_all_binding_fields(self):
        """to_dict() should include every binding field."""
        binding = ReportBinding(task_id="T-0082", phase="S4-implementation")
        data = binding.to_dict()
        for field in ("task_id", "phase", "gate_id", "execution_id", "git_commit",
                      "diff_fingerprint", "timestamp", "tool_name", "tool_version"):
            assert field in data


# ============================================================================
# SecurityReport.bind() tests
# ============================================================================

class TestSecurityReportBinding:
    """Tests for SecurityReport.bind() verdict computation."""

    def test_critical_finding_yields_blocked(self):
        """Fail-closed: any critical finding must yield Verdict.BLOCKED."""
        report = SecurityReport(files_scanned=1, findings=[
            SecFinding(
                rule_id="SS-001",
                severity="critical",
                file="app.py",
                line=10,
                message="Hardcoded secret detected",
                snippet='api_key = "abcdef1234567890"',
            ),
        ])
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.verdict == Verdict.BLOCKED
        assert report.verdict.is_blocking() is True

    def test_no_findings_yields_pass(self):
        """A clean security scan should yield Verdict.PASS."""
        report = SecurityReport(files_scanned=1)
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.verdict == Verdict.PASS
        assert report.verdict.is_conclusive() is True

    def test_bind_sets_binding_and_content_hash(self):
        """bind() should populate binding, verdict, and content hash."""
        report = SecurityReport(files_scanned=1, findings=[
            SecFinding(
                rule_id="SS-001",
                severity="critical",
                file="app.py",
                line=10,
                message="Hardcoded secret detected",
            ),
        ])
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.binding is not None
        assert report.binding.validate() == []
        assert report.binding.tool_name == "loop_core.security_scanner"
        assert report.content_hash != ""
        assert report.is_valid() is True


# ============================================================================
# AnalysisReport.bind() tests
# ============================================================================

class TestAnalysisReportBinding:
    """Tests for AnalysisReport.bind() verdict computation."""

    def test_error_finding_yields_fail(self):
        """A static analysis error should yield Verdict.FAIL (non-blocking)."""
        report = AnalysisReport(files_scanned=1, findings=[
            Finding(
                rule_id="SA-001",
                severity="error",
                file="app.py",
                line=10,
                message="Extracted value never verified",
            ),
        ])
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.verdict == Verdict.FAIL
        assert report.verdict.is_blocking() is True

    def test_no_findings_yields_pass(self):
        """A clean analysis should yield Verdict.PASS."""
        report = AnalysisReport(files_scanned=1)
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.verdict == Verdict.PASS

    def test_warning_only_yields_pass(self):
        """Warnings alone (no errors) should yield Verdict.PASS."""
        report = AnalysisReport(files_scanned=1, findings=[
            Finding(
                rule_id="SA-002",
                severity="warning",
                file="app.py",
                line=5,
                message="Bare except: — catches all exceptions",
            ),
        ])
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.verdict == Verdict.PASS

    def test_bind_sets_binding_and_content_hash(self):
        """bind() should populate binding, verdict, and content hash."""
        report = AnalysisReport(files_scanned=1, findings=[
            Finding(
                rule_id="SA-001",
                severity="error",
                file="app.py",
                line=10,
                message="Extracted value never verified",
            ),
        ])
        report.bind(task_id="T-0082", phase="S4-implementation", git_commit="c6fda12")
        assert report.binding is not None
        assert report.binding.validate() == []
        assert report.binding.tool_name == "loop_core.static_analyzer"
        assert report.content_hash != ""
        assert report.is_valid() is True
