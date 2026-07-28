from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EnforcementLevel(str, Enum):
    STRONG = "STRONG"
    HARD = "HARD"
    MEDIUM = "MEDIUM"
    PARTIAL = "PARTIAL"
    ADVISORY = "ADVISORY"

    @property
    def canonical(self) -> "EnforcementLevel":
        return _CANONICAL.get(self, self)


_CANONICAL = {
    EnforcementLevel.HARD: EnforcementLevel.STRONG,
    EnforcementLevel.STRONG: EnforcementLevel.STRONG,
    EnforcementLevel.PARTIAL: EnforcementLevel.MEDIUM,
    EnforcementLevel.MEDIUM: EnforcementLevel.MEDIUM,
    EnforcementLevel.ADVISORY: EnforcementLevel.ADVISORY,
}


@dataclass
class HostCapabilities:
    can_intercept_writes: bool = False
    can_intercept_commands: bool = False
    can_isolate_agents: bool = False
    can_enforce_exit_codes: bool = False
    has_hooks_api: bool = False

    def enforcement_level(self) -> EnforcementLevel:
        if self.can_intercept_writes and self.can_intercept_commands and self.can_enforce_exit_codes:
            return EnforcementLevel.STRONG
        if self.has_hooks_api or self.can_isolate_agents:
            return EnforcementLevel.MEDIUM
        return EnforcementLevel.ADVISORY


HARD_CONSTRAINTS = [
    {"id": "NO_IMPL_WITHOUT_REQUIREMENTS", "description": "Cannot enter implementation without approved requirements baseline"},
    {"id": "NO_DEV_WITHOUT_ARCHITECTURE", "description": "Cannot enter development without approved architecture"},
    {"id": "NO_WRITE_WITHOUT_TASK", "description": "Cannot write files without an active task defining allowed paths"},
    {"id": "NO_DELIVERY_WITHOUT_VERIFICATION", "description": "Cannot deliver without deterministic verification"},
    {"id": "NO_PASS_WITHOUT_REVIEW", "description": "Implementation phase gate cannot pass without independent review"},
    {"id": "NO_NEXT_PHASE_WITH_BLOCKERS", "description": "Cannot enter next phase with unresolved blockers"},
    {"id": "EVIDENCE_STALE_ON_CHANGE", "description": "Old verification evidence is invalidated when code/requirements change"},
    {"id": "NO_AUTO_GATE_PASS", "description": "Phase gate cannot auto-pass without explicit user approval"},
]


@dataclass
class EnforcementResult:
    level: EnforcementLevel
    violations: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return len(self.violations) > 0 and self.level == EnforcementLevel.STRONG

    @property
    def is_honest(self) -> bool:
        return True


HOST_PRESETS: dict[str, HostCapabilities] = {
    "codex": HostCapabilities(
        can_intercept_writes=True,
        can_intercept_commands=True,
        can_isolate_agents=True,
        can_enforce_exit_codes=True,
        has_hooks_api=True,
    ),
    "qoder": HostCapabilities(
        can_intercept_writes=True,
        can_intercept_commands=True,
        can_isolate_agents=False,
        can_enforce_exit_codes=True,
        has_hooks_api=True,
    ),
    "zcode": HostCapabilities(
        can_intercept_writes=True,
        can_intercept_commands=True,
        can_isolate_agents=True,
        can_enforce_exit_codes=True,
        has_hooks_api=True,
    ),
    "claude_code": HostCapabilities(
        can_intercept_writes=True,
        can_intercept_commands=True,
        can_isolate_agents=True,
        can_enforce_exit_codes=True,
        has_hooks_api=True,
    ),
    "standalone": HostCapabilities(
        can_intercept_writes=False,
        can_intercept_commands=False,
        can_isolate_agents=False,
        can_enforce_exit_codes=False,
        has_hooks_api=False,
    ),
}


def validate_host_capabilities(capabilities: HostCapabilities) -> EnforcementResult:
    result = EnforcementResult(level=capabilities.enforcement_level())
    if capabilities.enforcement_level() == EnforcementLevel.STRONG:
        if not capabilities.can_intercept_writes:
            result.warnings.append({"id": "STRONG_WITHOUT_WRITE_INTERCEPT", "message": "STRONG level claimed but write interception not available"})
        if not capabilities.can_enforce_exit_codes:
            result.warnings.append({"id": "STRONG_WITHOUT_EXIT_CODE", "message": "STRONG level claimed but exit code enforcement not available"})
    return result

