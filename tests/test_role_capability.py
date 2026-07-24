"""Tests for role_capability.py — v3.2 certification system."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.role_capability import (
    CapabilityStatus,
    CapabilityChallenge,
    DegradationRule,
    RoleCapabilityProfile,
    ROLE_CHALLENGES,
    DEGRADATION_RULES,
    check_role_admission,
    create_default_profiles,
    save_profile,
    load_profile,
    save_all_profiles,
    load_all_profiles,
)


class TestCapabilityStatus:
    def test_all_statuses_defined(self):
        assert len(CapabilityStatus) == 8  # UNCERTIFIED, CHALLENGE_PENDING, CERTIFIED, CERTIFIED_WITH_NOTES, CAPABILITY_DEGRADED, REVALIDATION_REQUIRED, ROLE_BLOCKED, CAPABILITY_UNAVAILABLE
        assert CapabilityStatus.UNCERTIFIED.value == "uncertified"
        assert CapabilityStatus.CERTIFIED.value == "certified"
        assert CapabilityStatus.ROLE_BLOCKED.value == "role_blocked"

    def test_status_is_string_enum(self):
        assert isinstance(CapabilityStatus.CERTIFIED.value, str)


class TestDegradationRules:
    def test_all_rules_have_ids(self):
        ids = {r.rule_id for r in DEGRADATION_RULES}
        assert "PASS_WITHOUT_EVIDENCE" in ids
        assert "MISSED_SEEDED_DEFECT" in ids
        assert "SCOPE_VIOLATION" in ids

    def test_each_rule_has_trigger_count(self):
        for rule in DEGRADATION_RULES:
            assert rule.trigger_count > 0


class TestRoleChallenges:
    def test_quality_engineer_has_challenge(self):
        ch = ROLE_CHALLENGES["quality-engineer"]
        assert len(ch.seeded_defects) == 3
        assert "empty_password" in ch.seeded_defects[0]["type"]

    def test_security_engineer_has_challenge(self):
        ch = ROLE_CHALLENGES["security-engineer"]
        assert len(ch.seeded_defects) == 3

    def test_developer_has_challenge(self):
        ch = ROLE_CHALLENGES["developer"]
        assert len(ch.pass_conditions) >= 3

    def test_reviewer_has_challenge(self):
        ch = ROLE_CHALLENGES["independent-reviewer"]
        assert len(ch.seeded_defects) == 3
        assert "At least 2 of 3" in ch.pass_conditions[0]


class TestRoleCapabilityProfile:
    def test_default_is_uncertified(self):
        p = RoleCapabilityProfile(role_id="developer")
        assert p.status == CapabilityStatus.UNCERTIFIED

    def test_uncertified_cannot_accept_task(self):
        p = RoleCapabilityProfile(role_id="developer")
        allowed, reason = p.can_accept_production_task()
        assert allowed is False
        assert "Not yet certified" in reason

    def test_certified_can_accept_task(self):
        p = RoleCapabilityProfile(role_id="developer", status=CapabilityStatus.CERTIFIED)
        allowed, reason = p.can_accept_production_task()
        assert allowed is True

    def test_blocked_cannot_accept_task(self):
        p = RoleCapabilityProfile(role_id="developer", status=CapabilityStatus.ROLE_BLOCKED)
        allowed, reason = p.can_accept_production_task()
        assert allowed is False
        assert "blocked" in reason.lower()

    def test_certify_sets_status_and_resets_counters(self):
        p = RoleCapabilityProfile(role_id="qa")
        p.pass_without_evidence_count = 5
        p.certify("CHALLENGE-QA-001")
        assert p.status == CapabilityStatus.CERTIFIED
        assert p.pass_without_evidence_count == 0
        assert p.certified_at is not None

    def test_pass_without_evidence_degradation(self):
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        p.record_pass_without_evidence()
        p.record_pass_without_evidence()
        result = p.record_pass_without_evidence()
        assert result == CapabilityStatus.CAPABILITY_DEGRADED
        assert p.status == CapabilityStatus.CAPABILITY_DEGRADED

    def test_missed_defect_triggers_revalidation(self):
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        result = p.record_missed_defect()
        assert result == CapabilityStatus.REVALIDATION_REQUIRED

    def test_scope_violation_triggers_block(self):
        p = RoleCapabilityProfile(role_id="dev", status=CapabilityStatus.CERTIFIED)
        result = p.record_scope_violation()
        assert result == CapabilityStatus.ROLE_BLOCKED

    def test_degradation_history_recorded(self):
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        p.record_missed_defect()
        assert len(p.degradation_history) == 1
        assert p.degradation_history[0]["rule_id"] == "MISSED_SEEDED_DEFECT"

    def test_to_dict(self):
        p = RoleCapabilityProfile(role_id="dev")
        d = p.to_dict()
        assert d["role_id"] == "dev"
        assert "degradation_counters" in d


class TestRoleAdmission:
    def test_certified_with_tools_passes(self):
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        allowed, _ = check_role_admission("qa", p, ["pytest"], ["pytest", "ruff"])
        assert allowed is True

    def test_missing_tools_blocks(self):
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        allowed, reason = check_role_admission("qa", p, ["pytest", "trivy"], ["pytest"])
        assert allowed is False
        assert "trivy" in reason

    def test_uncertified_blocks(self):
        allowed, reason = check_role_admission("qa")
        assert allowed is False


class TestDefaultProfiles:
    def test_all_11_roles_created(self):
        profiles = create_default_profiles()
        assert len(profiles) == 11
        assert "main-thread" in profiles
        assert "delivery-manager" in profiles

    def test_all_uncertified_by_default(self):
        profiles = create_default_profiles()
        for p in profiles.values():
            assert p.status == CapabilityStatus.UNCERTIFIED


class TestPersistence:
    """v3.2: degradation counters survive process restarts."""

    def test_save_and_load_roundtrip(self, tmp_path):
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        p.pass_without_evidence_count = 2
        p.missed_defect_count = 1
        save_profile(p, str(tmp_path))
        loaded = load_profile("qa", str(tmp_path))
        assert loaded.status == CapabilityStatus.CERTIFIED
        assert loaded.pass_without_evidence_count == 2
        assert loaded.missed_defect_count == 1

    def test_load_missing_returns_default(self, tmp_path):
        loaded = load_profile("nonexistent", str(tmp_path))
        assert loaded.role_id == "nonexistent"
        assert loaded.status == CapabilityStatus.UNCERTIFIED

    def test_save_all_and_load_all(self, tmp_path):
        profiles = create_default_profiles()
        profiles["quality-engineer"].status = CapabilityStatus.CERTIFIED
        profiles["quality-engineer"].certify()
        save_all_profiles(profiles, str(tmp_path))
        loaded = load_all_profiles(str(tmp_path))
        assert len(loaded) == 11
        assert loaded["quality-engineer"].status == CapabilityStatus.CERTIFIED

    def test_degradation_survives_restart(self, tmp_path):
        # Simulate: role gets degraded, process restarts, state persists
        p = RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED)
        p.record_pass_without_evidence()
        p.record_pass_without_evidence()
        p.record_pass_without_evidence()  # triggers degradation
        assert p.status == CapabilityStatus.CAPABILITY_DEGRADED
        save_profile(p, str(tmp_path))

        # "Restart" — load from disk
        loaded = load_profile("qa", str(tmp_path))
        assert loaded.status == CapabilityStatus.CAPABILITY_DEGRADED
        allowed, reason = loaded.can_accept_production_task()
        assert allowed is False
        assert "degraded" in reason.lower()

    def test_corrupt_file_returns_default(self, tmp_path):
        cert_dir = tmp_path / ".ai" / "certifications"
        cert_dir.mkdir(parents=True)
        (cert_dir / "qa.json").write_text("not valid json{{{")
        loaded = load_profile("qa", str(tmp_path))
        assert loaded.status == CapabilityStatus.UNCERTIFIED
