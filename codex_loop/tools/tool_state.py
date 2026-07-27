"""loop_state — Query current project state."""
import sys
from pathlib import Path


def run(project_root: str = ".") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.enforcement_hub import EnforcementHub

    hub = EnforcementHub(project_root)
    state = hub._read_state()
    tasks = hub._read_tasks()

    return {
        "project_name": state.get("project_name", ""),
        "current_phase": state.get("current_phase", ""),
        "current_task_id": state.get("current_task_id"),
        "current_gate_id": state.get("current_gate_id"),
        "loop_mode": state.get("loop_mode", ""),
        "last_handoff_at": state.get("last_handoff_at", ""),
        "active_tasks": [t.get("id") for t in tasks if t.get("status") in ("active", "in_progress")],
        "completed_tasks": [t.get("id") for t in tasks if t.get("status") == "completed"],
    }
