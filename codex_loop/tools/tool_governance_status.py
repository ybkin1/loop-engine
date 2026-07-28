"""loop_governance_status — Get full governance health summary."""
import sys
from pathlib import Path


def run(project_root: str = ".") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.enforcement_hub import EnforcementHub, quick_check

    hub = EnforcementHub(project_root)
    state = hub._read_state()
    gates = hub._read_gates()
    tasks = hub._read_tasks()

    pending_gates = [g.get("id", "?") for g in gates if isinstance(g, dict) and g.get("status") == "pending"]
    blocked_gates = [g.get("id", "?") for g in gates if isinstance(g, dict) and g.get("status") == "blocked"]
    active_tasks = [t.get("id", "?") for t in tasks if t.get("status") in ("active", "in_progress")]

    quick = quick_check(project_root)

    # Determine overall health
    if blocked_gates:
        overall = "BLOCKED"
    elif pending_gates and not active_tasks:
        overall = "DEGRADED"
    elif quick.allowed:
        overall = "HEALTHY"
    else:
        overall = "DEGRADED"

    return {
        "project_root": str(hub.root),
        "current_phase": state.get("current_phase", "unknown"),
        "current_task": state.get("current_task_id"),
        "loop_mode": state.get("loop_mode", "unknown"),
        "enforcement_level": hub.get_enforcement_level().value,
        "active_tasks": active_tasks,
        "pending_gates": pending_gates,
        "blocked_gates": blocked_gates,
        "blocker_count": quick.blocker_count,
        "overall_status": overall,
        "violations": [v.message for v in quick.violations if v.severity.value == "blocker"],
    }
