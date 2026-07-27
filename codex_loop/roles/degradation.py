"""
ENFORCEMENT_LEVEL degradation paths and multi-host adapter contracts.

Defines what happens when a host cannot provide STRONG enforcement,
and provides adapter contracts for Claude Code and Qoder.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from codex_loop.core.enforcement import EnforcementLevel, HostCapabilities, HARD_CONSTRAINTS


class DegradationAction(str, Enum):
    """What to do when a constraint cannot be enforced at the current level."""
    BLOCK = "block"        # Still block (STRONG → exit 2)
    WARN = "warn"          # Warn but allow (MEDIUM → stderr warning)
    ADVISORY = "advisory"  # Note only, no blocking (ADVISORY → log only)


@dataclass
class LevelBehavior:
    """How each constraint behaves at each enforcement level."""
    constraint_id: str
    strong_action: DegradationAction = DegradationAction.BLOCK
    medium_action: DegradationAction = DegradationAction.WARN
    advisory_action: DegradationAction = DegradationAction.ADVISORY


# Degradation table: constraint → behavior per level
DEGRADATION_TABLE: dict[str, LevelBehavior] = {
    "NO_IMPL_WITHOUT_REQUIREMENTS": LevelBehavior("NO_IMPL_WITHOUT_REQUIREMENTS"),
    "NO_DEV_WITHOUT_ARCHITECTURE": LevelBehavior("NO_DEV_WITHOUT_ARCHITECTURE"),
    "NO_WRITE_WITHOUT_TASK": LevelBehavior("NO_WRITE_WITHOUT_TASK"),
    "NO_DELIVERY_WITHOUT_VERIFICATION": LevelBehavior("NO_DELIVERY_WITHOUT_VERIFICATION"),
    "NO_PASS_WITHOUT_REVIEW": LevelBehavior(
        "NO_PASS_WITHOUT_REVIEW",
        strong_action=DegradationAction.BLOCK,
        medium_action=DegradationAction.WARN,    # Can't enforce agent isolation but can still suggest
        advisory_action=DegradationAction.ADVISORY,
    ),
    "NO_NEXT_PHASE_WITH_BLOCKERS": LevelBehavior("NO_NEXT_PHASE_WITH_BLOCKERS"),
    "EVIDENCE_STALE_ON_CHANGE": LevelBehavior(
        "EVIDENCE_STALE_ON_CHANGE",
        strong_action=DegradationAction.BLOCK,
        medium_action=DegradationAction.WARN,    # Can detect staleness but can't block writes
        advisory_action=DegradationAction.ADVISORY,
    ),
    "NO_AUTO_GATE_PASS": LevelBehavior(
        "NO_AUTO_GATE_PASS",
        strong_action=DegradationAction.BLOCK,
        medium_action=DegradationAction.BLOCK,   # Gate approval is always user-gated
        advisory_action=DegradationAction.WARN,
    ),
}


def get_action_for_level(constraint_id: str, level: EnforcementLevel) -> DegradationAction:
    """Get the degradation action for a constraint at a given enforcement level."""
    behavior = DEGRADATION_TABLE.get(constraint_id)
    if not behavior:
        return DegradationAction.WARN

    if level == EnforcementLevel.STRONG:
        return behavior.strong_action
    elif level == EnforcementLevel.MEDIUM:
        return behavior.medium_action
    else:
        return behavior.advisory_action


# ── Multi-Host Adapter Capability Declarations ──

# Claude Code capabilities (estimated)
CLAUDE_CODE_CAPABILITIES = HostCapabilities(
    can_intercept_writes=True,       # Claude Code has hooks
    can_intercept_commands=True,     # Bash interception available
    can_isolate_agents=True,         # Sub-agents supported
    can_enforce_exit_codes=True,     # Exit code semantics respected
    has_hooks_api=True,
)

# Qoder capabilities (estimated - weaker integration)
QODER_CAPABILITIES = HostCapabilities(
    can_intercept_writes=False,      # No hook API
    can_intercept_commands=False,
    can_isolate_agents=True,         # Sub-agents via API
    can_enforce_exit_codes=False,
    has_hooks_api=False,
)

# Standalone CLI capabilities (no host)
STANDALONE_CAPABILITIES = HostCapabilities(
    can_intercept_writes=False,
    can_intercept_commands=False,
    can_isolate_agents=False,
    can_enforce_exit_codes=False,
    has_hooks_api=False,
)


def get_adapter_info(host_name: str) -> dict:
    """Get capability and enforcement info for a known host."""
    caps = {
        "zcode": HostCapabilities(True, False, True, True, True),
        "claude_code": CLAUDE_CODE_CAPABILITIES,
        "qoder": QODER_CAPABILITIES,
        "standalone": STANDALONE_CAPABILITIES,
    }
    cap = caps.get(host_name.lower(), STANDALONE_CAPABILITIES)
    level = cap.enforcement_level()

    # Get constraint behaviors at this level
    constraints = {}
    for cid in DEGRADATION_TABLE:
        action = get_action_for_level(cid, level)
        constraints[cid] = {
            "action": action.value,
            "can_enforce": action == DegradationAction.BLOCK,
        }

    return {
        "host": host_name,
        "enforcement_level": level.value,
        "can_block_writes": cap.can_intercept_writes,
        "can_block_commands": cap.can_intercept_commands,
        "can_isolate_agents": cap.can_isolate_agents,
        "constraints": constraints,
    }
