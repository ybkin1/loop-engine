"""loop_execute_phase — Execute a complete Loop phase."""
import sys
from pathlib import Path


def run(phase_id: str, project_root: str = ".") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.state_machine import Phase
    from codex_loop.core.executor import PhaseExecutor

    try:
        phase = Phase(phase_id)
    except ValueError:
        return {"error": f"Invalid phase: {phase_id}", "available": [p.value for p in Phase]}

    executor = PhaseExecutor()
    plan = executor.execute_phase(phase, Path(project_root))

    return {
        "phase": plan.phase.value,
        "status": plan.status.value,
        "steps_total": len(plan.steps),
        "steps_completed": sum(1 for s in plan.steps if s.status.value == "complete"),
        "steps_blocked": sum(1 for s in plan.steps if s.status.value == "blocked"),
        "gate_id": plan.gate_id,
    }
