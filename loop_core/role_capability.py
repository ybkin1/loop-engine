"""
Role Capability Certification — v3.2

Ensures roles "genuinely function" through verifiable capability challenges,
not prompt claims. Absorbs concepts from Qoder's certification.ts.

Key concepts:
- CapabilityStatus: state machine for role certification lifecycle
- CapabilityChallenge: isolated fixture test each role must pass
- DegradationEngine: detects when a role should be degraded or blocked
- RoleAdmission: pre-flight check before a role starts production work
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CapabilityStatus(str, Enum):
    """Role certification lifecycle."""
    UNCERTIFIED = "uncertified"                # Never challenged
    CHALLENGE_PENDING = "challenge_pending"    # Challenge submitted, awaiting results
    CERTIFIED = "certified"                    # Passed challenge, eligible for production work
    CERTIFIED_WITH_NOTES = "certified_with_notes"  # Passed with minor findings
    CAPABILITY_DEGRADED = "capability_degraded"    # Degradation detected (e.g., 3x no-evidence PASS)
    REVALIDATION_REQUIRED = "revalidation_required"  # Must re-challenge (missed seeded defect)
    ROLE_BLOCKED = "role_blocked"              # Cannot perform this role (violation detected)
    CAPABILITY_UNAVAILABLE = "capability_unavailable"  # Tool/input missing, can't operate


# ── Degradation Triggers ────────────────────────────────────────────────

@dataclass
class DegradationRule:
    """A rule that triggers capability degradation."""
    rule_id: str
    description: str
    trigger_count: int = 3       # How many occurrences before triggering
    new_status: CapabilityStatus = CapabilityStatus.CAPABILITY_DEGRADED


DEGRADATION_RULES: list[DegradationRule] = [
    DegradationRule(
        "PASS_WITHOUT_EVIDENCE",
        "Role submitted PASS verdict without structured evidence (3 consecutive times)",
        trigger_count=3,
        new_status=CapabilityStatus.CAPABILITY_DEGRADED,
    ),
    DegradationRule(
        "MISSED_SEEDED_DEFECT",
        "Quality/Security role failed to detect a seeded defect in capability challenge",
        trigger_count=1,
        new_status=CapabilityStatus.REVALIDATION_REQUIRED,
    ),
    DegradationRule(
        "SCOPE_VIOLATION",
        "Role performed action outside its allowed scope (e.g., developer modified architecture)",
        trigger_count=1,
        new_status=CapabilityStatus.ROLE_BLOCKED,
    ),
    DegradationRule(
        "REPEATED_REWORK",
        "Same type of rework triggered 5+ times without improvement",
        trigger_count=5,
        new_status=CapabilityStatus.CAPABILITY_DEGRADED,
    ),
    DegradationRule(
        "TOOL_FAILURE",
        "Required tools unavailable or failing for 3+ consecutive role runs",
        trigger_count=3,
        new_status=CapabilityStatus.CAPABILITY_UNAVAILABLE,
    ),
    DegradationRule(
        "CONTEXT_STALENESS",
        "Role operated on stale inputs (evidence expired) 3+ times",
        trigger_count=3,
        new_status=CapabilityStatus.REVALIDATION_REQUIRED,
    ),
]


# ── Capability Challenge Definition ──────────────────────────────────────

@dataclass
class CapabilityChallenge:
    """A test each role must pass in an isolated fixture before production work."""
    challenge_id: str
    role_id: str
    description: str
    required_tools: list[str] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    seeded_defects: list[dict] = field(default_factory=list)
    pass_conditions: list[str] = field(default_factory=list)
    max_attempts: int = 3
    timeout_seconds: int = 300


# Standard challenges per role
ROLE_CHALLENGES: dict[str, CapabilityChallenge] = {
    "quality-engineer": CapabilityChallenge(
        challenge_id="CHALLENGE-QA-001",
        role_id="quality-engineer",
        description="质量工程师能力挑战：检测预埋缺陷",
        required_tools=["pytest", "ruff"],
        required_inputs=["seeded_defect_code.py", "test_suite.py"],
        seeded_defects=[
            {"id": "SD-001", "type": "empty_password", "description": "空密码可登录"},
            {"id": "SD-002", "type": "sql_injection", "description": "SQL 字符串拼接"},
            {"id": "SD-003", "type": "missing_auth", "description": "端点无鉴权"},
        ],
        pass_conditions=[
            "All 3 seeded defects detected",
            "quality_report.json produced with correct schema",
            "overall verdict = BLOCKED (because defects exist)",
        ],
    ),
    "security-engineer": CapabilityChallenge(
        challenge_id="CHALLENGE-SEC-001",
        role_id="security-engineer",
        description="安全工程师能力挑战：检测安全漏洞",
        required_tools=["detect-secrets", "pip-audit"],
        required_inputs=["vulnerable_code.py"],
        seeded_defects=[
            {"id": "SD-004", "type": "hardcoded_secret", "description": "AWS_KEY 硬编码"},
            {"id": "SD-005", "type": "sql_injection", "description": "os.system 注入"},
            {"id": "SD-006", "type": "xss_unencoded", "description": "innerHTML XSS"},
        ],
        pass_conditions=[
            "All 3 seeded defects detected",
            "security_report.json produced with correct schema",
            "overall verdict = BLOCKED",
        ],
    ),
    "developer": CapabilityChallenge(
        challenge_id="CHALLENGE-DEV-001",
        role_id="developer",
        description="开发工程师能力挑战：按契约实现且不越界",
        required_tools=["pytest", "ruff"],
        required_inputs=["interface-contract.json", "architecture.md"],
        seeded_defects=[],
        pass_conditions=[
            "Code compiles and runs",
            "All unit tests pass",
            "lint 0 errors",
            "No files written outside allowed_paths",
            "No architecture contract violations",
        ],
    ),
    "independent-reviewer": CapabilityChallenge(
        challenge_id="CHALLENGE-REV-001",
        role_id="independent-reviewer",
        description="独立评审员能力挑战：发现预埋代码缺陷",
        required_tools=[],
        required_inputs=["code_with_defects.py", "architecture.md"],
        seeded_defects=[
            {"id": "SD-007", "type": "maintainability", "description": "函数 150 行无注释"},
            {"id": "SD-008", "type": "security", "description": "明文密码在日志中"},
            {"id": "SD-009", "type": "architecture", "description": "循环依赖"},
        ],
        pass_conditions=[
            "At least 2 of 3 seeded defects found at P0/P1 level",
            "review_report.json produced with correct schema",
            "verdict = BLOCKED (because P0 defects exist)",
        ],
    ),
}


# ── Role Capability Profile ──────────────────────────────────────────────

@dataclass
class RoleCapabilityProfile:
    """Tracks a role's certification state and degradation signals."""
    role_id: str
    status: CapabilityStatus = CapabilityStatus.UNCERTIFIED
    certified_at: str | None = None
    last_challenge_id: str | None = None
    challenge_attempts: int = 0

    # Degradation counters
    pass_without_evidence_count: int = 0
    missed_defect_count: int = 0
    scope_violation_count: int = 0
    rework_count: int = 0
    tool_failure_count: int = 0
    context_stale_count: int = 0

    # Evidence
    last_run_id: str | None = None
    degradation_history: list[dict] = field(default_factory=list)

    def can_accept_production_task(self) -> tuple[bool, str]:
        """Check if this role is eligible for production work."""
        if self.status in (CapabilityStatus.CERTIFIED, CapabilityStatus.CERTIFIED_WITH_NOTES):
            return True, "Certified"
        if self.status == CapabilityStatus.UNCERTIFIED:
            return False, "Not yet certified — must pass capability challenge first"
        if self.status == CapabilityStatus.REVALIDATION_REQUIRED:
            return False, "Revalidation required — missed seeded defect or stale context"
        if self.status == CapabilityStatus.CAPABILITY_DEGRADED:
            return False, "Capability degraded — too many no-evidence PASS verdicts"
        if self.status == CapabilityStatus.ROLE_BLOCKED:
            return False, "Role blocked — scope violation detected"
        if self.status == CapabilityStatus.CAPABILITY_UNAVAILABLE:
            return False, "Capability unavailable — required tools missing or failing"
        return False, f"Status {self.status.value} requires resolution before production work"

    def record_pass_without_evidence(self) -> CapabilityStatus | None:
        """Record a PASS verdict without structured evidence. Returns new status if degraded."""
        self.pass_without_evidence_count += 1
        return self._check_degradation("PASS_WITHOUT_EVIDENCE", self.pass_without_evidence_count)

    def record_missed_defect(self) -> CapabilityStatus | None:
        """Record failure to detect a seeded defect."""
        self.missed_defect_count += 1
        return self._check_degradation("MISSED_SEEDED_DEFECT", self.missed_defect_count)

    def record_scope_violation(self) -> CapabilityStatus | None:
        """Record a scope-violating action."""
        self.scope_violation_count += 1
        return self._check_degradation("SCOPE_VIOLATION", self.scope_violation_count)

    def _check_degradation(self, rule_id: str, count: int) -> CapabilityStatus | None:
        """Check if a degradation rule has been triggered."""
        for rule in DEGRADATION_RULES:
            if rule.rule_id == rule_id and count >= rule.trigger_count:
                old_status = self.status
                self.status = rule.new_status
                self.degradation_history.append({
                    "rule_id": rule_id,
                    "from": old_status.value,
                    "to": rule.new_status.value,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "count": count,
                })
                return rule.new_status
        return None

    def certify(self, challenge_id: str | None = None) -> None:
        """Mark role as certified after passing challenge."""
        self.status = CapabilityStatus.CERTIFIED
        self.certified_at = datetime.now(timezone.utc).isoformat()
        self.last_challenge_id = challenge_id
        # Reset degradation counters on successful certification
        self.pass_without_evidence_count = 0
        self.missed_defect_count = 0
        self.rework_count = 0
        self.tool_failure_count = 0
        self.context_stale_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "status": self.status.value,
            "certified_at": self.certified_at,
            "last_challenge_id": self.last_challenge_id,
            "challenge_attempts": self.challenge_attempts,
            "degradation_counters": {
                "pass_without_evidence": self.pass_without_evidence_count,
                "missed_defect": self.missed_defect_count,
                "scope_violation": self.scope_violation_count,
                "rework": self.rework_count,
                "tool_failure": self.tool_failure_count,
                "context_stale": self.context_stale_count,
            },
        }


# ── Role Admission Check ─────────────────────────────────────────────────

def check_role_admission(
    role_id: str,
    profile: RoleCapabilityProfile | None = None,
    required_tools: list[str] | None = None,
    available_tools: list[str] | None = None,
) -> tuple[bool, str]:
    """Pre-flight check before a role starts a production task.

    Checks:
    1. Role is certified (or certification is not required for this task type)
    2. Required tools are available
    3. No active degradation

    Returns (allowed, reason).
    """
    if profile is None:
        profile = RoleCapabilityProfile(role_id=role_id)

    # Check certification
    allowed, reason = profile.can_accept_production_task()
    if not allowed:
        return False, reason

    # Check tool availability
    if required_tools and available_tools is not None:
        missing = set(required_tools) - set(available_tools)
        if missing:
            return False, f"Required tools unavailable: {missing}"

    return True, "Admission approved"


# ── Default profiles for all 11 roles ────────────────────────────────────

def create_default_profiles() -> dict[str, RoleCapabilityProfile]:
    """Create default (uncertified) profiles for all 11 roles."""
    roles = [
        "developer", "quality-engineer", "security-engineer",
        "independent-reviewer", "system-architect", "module-architect",
        "product-manager", "project-manager", "delivery-manager",
        "release-engineer", "main-thread",
    ]
    return {role: RoleCapabilityProfile(role_id=role) for role in roles}


# ── Persistence (v3.2) ──────────────────────────────────────────────────
# Degradation counters survive process restarts via .ai/certifications/

import json
from pathlib import Path as _Path


def save_profile(profile: RoleCapabilityProfile, project_root: str | _Path) -> None:
    """Persist a role capability profile to .ai/certifications/<role_id>.json."""
    cert_dir = _Path(project_root) / ".ai" / "certifications"
    cert_dir.mkdir(parents=True, exist_ok=True)
    filepath = cert_dir / f"{profile.role_id}.json"
    filepath.write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
                        encoding="utf-8")


def load_profile(role_id: str, project_root: str | _Path) -> RoleCapabilityProfile:
    """Load a role capability profile from disk, or return default if not found."""
    filepath = _Path(project_root) / ".ai" / "certifications" / f"{role_id}.json"
    if not filepath.exists():
        return RoleCapabilityProfile(role_id=role_id)
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        profile = RoleCapabilityProfile(role_id=role_id)
        profile.status = CapabilityStatus(data.get("status", "uncertified"))
        profile.certified_at = data.get("certified_at")
        profile.last_challenge_id = data.get("last_challenge_id")
        profile.challenge_attempts = data.get("challenge_attempts", 0)
        counters = data.get("degradation_counters", {})
        profile.pass_without_evidence_count = counters.get("pass_without_evidence", 0)
        profile.missed_defect_count = counters.get("missed_defect", 0)
        profile.scope_violation_count = counters.get("scope_violation", 0)
        profile.rework_count = counters.get("rework", 0)
        profile.tool_failure_count = counters.get("tool_failure", 0)
        profile.context_stale_count = counters.get("context_stale", 0)
        return profile
    except (json.JSONDecodeError, KeyError, ValueError):
        return RoleCapabilityProfile(role_id=role_id)


def save_all_profiles(profiles: dict[str, RoleCapabilityProfile],
                      project_root: str | _Path) -> None:
    """Persist all role profiles."""
    for profile in profiles.values():
        save_profile(profile, project_root)


def load_all_profiles(project_root: str | _Path) -> dict[str, RoleCapabilityProfile]:
    """Load all role profiles, creating defaults for missing ones."""
    defaults = create_default_profiles()
    for role_id in defaults:
        loaded = load_profile(role_id, project_root)
        if loaded.status != CapabilityStatus.UNCERTIFIED or loaded.certified_at:
            defaults[role_id] = loaded
    return defaults
