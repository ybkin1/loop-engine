"""loop_execute_phase — Execute a complete Loop phase."""
import sys
from pathlib import Path


def run(phase_id: str, project_root: str = ".") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from loop_core.runtime_controller import RuntimeController, RuntimeState
    from loop_core.state_machine import Phase
    from loop_core.executor import PhaseExecutor

    controller = RuntimeController(project_root)
    runtime_state = controller.inspect()
    if runtime_state in {RuntimeState.USER_APPROVAL_REQUIRED, RuntimeState.WORK_PACKAGE_PROPOSAL}:
        return {"error": "EXECUTION_NOT_APPROVED", "runtime_state": runtime_state.value}

    try:
        phase = Phase(phase_id)
    except ValueError:
        return {"error": f"Invalid phase: {phase_id}", "available": [p.value for p in Phase]}

    executor = PhaseExecutor()
    plan = executor.execute_phase(phase, Path(project_root))
    checkpoint = controller.checkpoint(
        "review" if plan.status.value == "complete" else "repair",
        summary=f"loop_execute_phase {phase.value}: {plan.status.value}",
    )

    return {
        "phase": plan.phase.value,
        "status": plan.status.value,
        "steps_total": len(plan.steps),
        "steps_completed": sum(1 for s in plan.steps if s.status.value == "complete"),
        "steps_blocked": sum(1 for s in plan.steps if s.status.value == "blocked"),
        "gate_id": plan.gate_id,
        "checkpoint_ref": str(checkpoint.relative_to(Path(project_root).resolve())),
        "runtime_state": controller.snapshot().runtime_state,
    }
