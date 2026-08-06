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
from datetime import datetime, timedelta, timezone
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
ROLE_IDS: tuple[str, ...] = (
    "main-thread", "product-manager", "project-manager", "system-architect",
    "module-architect", "developer", "quality-engineer", "test-engineer",
    "security-engineer", "independent-reviewer", "delivery-manager", "release-engineer",
)

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
    # v3.3 — expanded to all 11 roles (Qoder certification.ts pattern)
    "main-thread": CapabilityChallenge(
        challenge_id="CHALLENGE-MAIN-001",
        role_id="main-thread",
        description="主控线程能力挑战：角色隔离与否决链",
        required_tools=[],
        required_inputs=["task_file.json"],
        seeded_defects=[
            {"id": "SD-010", "type": "self_review", "description": "developer==reviewer agent_id"},
        ],
        pass_conditions=[
            "Detected self-review violation (developer==reviewer)",
            "BLOCKED verdict not overwritten",
            "All role outputs have verdict field",
        ],
    ),
    "product-manager": CapabilityChallenge(
        challenge_id="CHALLENGE-PM-001",
        role_id="product-manager",
        description="产品经理能力挑战：优先级分布与验收标准",
        required_tools=[],
        required_inputs=["user_stories.json"],
        seeded_defects=[
            {"id": "SD-011", "type": "p0_exceeds_30pct", "description": "P0 超过 30%"},
            {"id": "SD-012", "type": "technical_keyword", "description": "需求含技术关键词"},
        ],
        pass_conditions=[
            "P0 <= 30% of total stories",
            "P3 >= 10% of total stories",
            "All stories have Given-When-Then AC",
            "No technical keywords in requirements",
        ],
    ),
    "project-manager": CapabilityChallenge(
        challenge_id="CHALLENGE-PJ-001",
        role_id="project-manager",
        description="项目经理能力挑战：DAG 与任务覆盖",
        required_tools=[],
        required_inputs=["task_graph.json"],
        seeded_defects=[
            {"id": "SD-013", "type": "dag_cycle", "description": "任务图存在循环依赖"},
            {"id": "SD-014", "type": "p0_uncovered", "description": "P0 故事未覆盖"},
        ],
        pass_conditions=[
            "No cycles in task dependency graph",
            "All P0 stories covered by at least one task",
            "All task IDs unique",
            "All dependencies reference valid tasks",
        ],
    ),
    "system-architect": CapabilityChallenge(
        challenge_id="CHALLENGE-SA-001",
        role_id="system-architect",
        description="系统架构师能力挑战：依赖分析与文档完整性",
        required_tools=["madge"],
        required_inputs=["architecture.md", "dependency_graph.json"],
        seeded_defects=[
            {"id": "SD-015", "type": "circular_dep", "description": "domain↔infrastructure 循环依赖"},
        ],
        pass_conditions=[
            "Circular dependency detected in dependency graph",
            "Architecture doc has all 7 required sections",
            "Each tech choice has verifiable rationale",
        ],
    ),
    "module-architect": CapabilityChallenge(
        challenge_id="CHALLENGE-MA-001",
        role_id="module-architect",
        description="模块架构师能力挑战：接口契约完整性",
        required_tools=["validate_contract.py"],
        required_inputs=["interface-contract.json"],
        seeded_defects=[
            {"id": "SD-016", "type": "ambiguous_type", "description": "函数返回类型为 any/object"},
            {"id": "SD-017", "type": "missing_idempotency", "description": "有副作用的函数未声明幂等性"},
        ],
        pass_conditions=[
            "No ambiguous types (object/any/unknown)",
            "All exports have input/output/error types",
            "All functions with side effects declare idempotency",
            "Schema field is 'interface-contract/v1'",
        ],
    ),
    "delivery-manager": CapabilityChallenge(
        challenge_id="CHALLENGE-DM-001",
        role_id="delivery-manager",
        description="交付经理能力挑战：GO/NOGO 决策",
        required_tools=[],
        required_inputs=["release_checklist.json"],
        seeded_defects=[
            {"id": "SD-018", "type": "missing_rollback", "description": "缺回滚方案但标记 GO"},
        ],
        pass_conditions=[
            "GO only when all signoffs PASS + all deliverables complete",
            "NOGO when any deliverable incomplete",
            "NOGO includes blocking_issues list",
            "Decision is only GO or NOGO (no CONDITIONAL_GO)",
        ],
    ),
    "release-engineer": CapabilityChallenge(
        challenge_id="CHALLENGE-RE-001",
        role_id="release-engineer",
        description="发布工程师能力挑战：8 维度部署就绪检查",
        required_tools=[],
        required_inputs=["release_report.json"],
        seeded_defects=[
            {"id": "SD-019", "type": "missing_health_check", "description": "缺健康检查端点"},
        ],
        pass_conditions=[
            "All 8 dimensions checked: build/deploy/health/logging/rollback/monitoring/config/secrets",
            "Each check has evidence (file + line)",
            "Overall PASS only when all 8 dimensions pass + upstream PASS",
        ],
    ),
    # T-0123: 补 test-engineer challenge（ROLE_CHALLENGES 12/12 覆盖闭环，
    # 风格对齐既有 11 项——测试工程能力挑战，验证缺陷检测与报告契约）
    "test-engineer": CapabilityChallenge(
        challenge_id="CHALLENGE-TE-001",
        role_id="test-engineer",
        description="测试工程师能力挑战：编写并执行测试且报告契约完整",
        required_tools=["pytest"],
        required_inputs=["contract.md", "sample_module.py"],
        seeded_defects=[
            {"id": "SD-020", "type": "boundary_off_by_one", "description": "边界值 off-by-one"},
            {"id": "SD-021", "type": "exception_unhandled", "description": "异常未处理路径"},
        ],
        pass_conditions=[
            "Test suite covers contract.md 全部验收点",
            "pytest 全绿（含 seeded_defects 检出断言）",
            "test_report.json produced with correct schema",
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
    certification_expires_at: str | None = None
    revalidation_interval_days: int = 45
    grace_period_days: int = 7
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


# ── Default profiles for all registered roles ─────────────────────────────

def create_default_profiles() -> dict[str, RoleCapabilityProfile]:
    """Create default (uncertified) profiles for every canonical role."""
    return {role: RoleCapabilityProfile(role_id=role) for role in ROLE_IDS}


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
        profile.certification_expires_at = data.get("certification_expires_at")
        profile.revalidation_interval_days = int(data.get("revalidation_interval_days", 45))
        profile.grace_period_days = int(data.get("grace_period_days", 7))
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
