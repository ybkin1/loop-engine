"""
Loop Core Enforcement — Host capability grading and hard constraint validation.

Defines ENFORCEMENT_LEVEL and validates whether a host adapter can truthfully
claim a given level based on its actual capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EnforcementLevel(str, Enum):
    """How strongly a host can enforce Loop constraints."""
    STRONG = "STRONG"    # Can intercept file writes and command execution (exit 2 = deny)
    MEDIUM = "MEDIUM"    # Can control most flows via plugins/MCP/workflows
    ADVISORY = "ADVISORY"  # Read-only: can suggest but not enforce


@dataclass
class HostCapabilities:
    """Capabilities a host adapter must declare."""
    can_intercept_writes: bool = False       # Can block file write operations
    can_intercept_commands: bool = False     # Can block shell command execution
    can_isolate_agents: bool = False         # Can launch sub-agents with fresh context
    can_enforce_exit_codes: bool = False     # Exit 2 = deny is respected
    has_hooks_api: bool = False              # Has hook/plugin API

    def enforcement_level(self) -> EnforcementLevel:
        """Determine enforcement level from capabilities."""
        if self.can_intercept_writes and self.can_intercept_commands and self.can_enforce_exit_codes:
            return EnforcementLevel.STRONG
        if self.has_hooks_api or self.can_isolate_agents:
            return EnforcementLevel.MEDIUM
        return EnforcementLevel.ADVISORY


# Hard constraints that MUST be enforced at STRONG level.
# At MEDIUM/ADVISORY, these become warnings.
HARD_CONSTRAINTS = [
    {
        "id": "NO_IMPL_WITHOUT_REQUIREMENTS",
        "description": "Cannot enter implementation without approved requirements baseline",
        "check": "phase != 'S4-implementation' or prev_gate_approved('S1-requirements')",
    },
    {
        "id": "NO_DEV_WITHOUT_ARCHITECTURE",
        "description": "Cannot enter development without approved architecture",
        "check": "phase != 'S4-implementation' or prev_gate_approved('S2-architecture')",
    },
    {
        "id": "NO_WRITE_WITHOUT_TASK",
        "description": "Cannot write files without an active task defining allowed paths",
        "check": "has_active_task() and target_in_allowed_paths()",
    },
    {
        "id": "NO_DELIVERY_WITHOUT_VERIFICATION",
        "description": "Cannot deliver without deterministic verification (test/lint/build)",
        "check": "phase != 'S6-delivery' or has_evidence('test') and has_evidence('lint')",
    },
    {
        "id": "NO_PASS_WITHOUT_REVIEW",
        "description": "Implementation phase gate cannot pass without independent review",
        "check": "phase != 'S4-implementation' or has_role_verdict('independent-reviewer')",
    },
    {
        "id": "NO_NEXT_PHASE_WITH_BLOCKERS",
        "description": "Cannot enter next phase with unresolved blockers",
        "check": "not has_unresolved_blockers()",
    },
    {
        "id": "EVIDENCE_STALE_ON_CHANGE",
        "description": "Old verification evidence is invalidated when code/requirements change",
        "check": "not is_evidence_stale()",
    },
    {
        "id": "NO_AUTO_GATE_PASS",
        "description": "Phase gate cannot auto-pass without explicit user approval",
        "check": "gate_status != 'approved' or gate_approval_source == 'explicit_user_message'",
    },
]


@dataclass
class EnforcementResult:
    """Result of checking hard constraints against a host's enforcement level."""
    level: EnforcementLevel
    violations: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        """At STRONG level, violations are blocking. At ADVISORY, they are warnings."""
        return len(self.violations) > 0 and self.level == EnforcementLevel.STRONG

    @property
    def is_honest(self) -> bool:
        """An ADVISORY host must not claim violations as 'enforced'."""
        return True  # This module never lies about enforcement


def validate_host_capabilities(capabilities: HostCapabilities) -> EnforcementResult:
    """Validate that a host's claimed capabilities are internally consistent."""
    result = EnforcementResult(level=capabilities.enforcement_level())

    if capabilities.enforcement_level() == EnforcementLevel.STRONG:
        if not capabilities.can_intercept_writes:
            result.warnings.append({"id": "STRONG_WITHOUT_WRITE_INTERCEPT", "message": "STRONG level claimed but write interception not available"})
        if not capabilities.can_enforce_exit_codes:
            result.warnings.append({"id": "STRONG_WITHOUT_EXIT_CODE", "message": "STRONG level claimed but exit code enforcement not available"})

    return result
