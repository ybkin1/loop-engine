"""
ENFORCEMENT_LEVEL degradation — Actual behavior for MEDIUM and ADVISORY.

At STRONG level: exit 2 blocks the operation.
At MEDIUM level: return permissionDecision=ask (user confirms) or stderr warning.
At ADVISORY level: log only, never block.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from enum import Enum

from codex_loop.core.enforcement import EnforcementLevel


class EnforcementAction(str, Enum):
    BLOCK = "block"          # exit 2, hard stop
    ASK = "ask"              # permissionDecision=ask in JSON output
    WARN = "warn"            # stderr warning, allow
    LOG = "log"              # silent log, always allow


@dataclass
class DegradationDecision:
    """Decision produced by the degradation engine."""
    action: EnforcementAction
    reason: str
    can_proceed: bool  # True = operation allowed, False = blocked

    def apply(self) -> int:
        """Apply the decision: return exit code and optionally output JSON."""
        if self.action == EnforcementAction.BLOCK:
            print(f"[loop_enforcement] BLOCKED: {self.reason}", file=sys.stderr)
            return 2
        elif self.action == EnforcementAction.ASK:
            decision = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"[loop_enforcement] {self.reason}",
                }
            }
            sys.stdout.write(json.dumps(decision, ensure_ascii=False))
            return 0
        elif self.action == EnforcementAction.WARN:
            print(f"[loop_enforcement] WARN: {self.reason}", file=sys.stderr)
            return 0
        else:
            return 0  # LOG: silent


def degrade_constraint(
    constraint_id: str,
    level: EnforcementLevel,
    reason: str,
) -> DegradationDecision:
    """Determine what action to take for a constraint at a given enforcement level."""
    if level == EnforcementLevel.STRONG:
        return DegradationDecision(EnforcementAction.BLOCK, reason, False)
    elif level == EnforcementLevel.MEDIUM:
        # Can't hard-block, but can ask user or warn
        if "write" in constraint_id.lower() or "execution" in constraint_id.lower():
            return DegradationDecision(EnforcementAction.ASK, reason, True)
        return DegradationDecision(EnforcementAction.WARN, reason, True)
    else:
        return DegradationDecision(EnforcementAction.LOG, reason, True)


def build_enforcement_capability_matrix() -> dict:
    """Build a capability matrix showing what each level can enforce."""
    return {
        "STRONG": {
            "can_block_writes": True,
            "can_block_commands": True,
            "can_isolate_agents": True,
            "exit_code_semantics": "exit_2_deny",
            "user_interaction": "not_required_for_technical_blocks",
        },
        "MEDIUM": {
            "can_block_writes": True,
            "can_block_commands": False,
            "can_isolate_agents": True,
            "exit_code_semantics": "exit_2_deny_for_writes_only",
            "user_interaction": "ask_for_command_interception_gaps",
        },
        "ADVISORY": {
            "can_block_writes": False,
            "can_block_commands": False,
            "can_isolate_agents": False,
            "exit_code_semantics": "none",
            "user_interaction": "all_constraints_are_advisory_only",
        },
    }
