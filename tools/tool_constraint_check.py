"""loop_constraint_check — Run all 8 hard constraints (C1-C8)."""
import sys
from pathlib import Path


def run(project_root: str = ".", target_path: str = None, allowed_paths: list = None,
        current_phase: str = None, target_phase: str = None) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from loop_core.hard_constraints import HardConstraints, Severity
    from loop_core.state_machine import Phase

    hc = HardConstraints()
    ctx = {}
    # T-0107 D4-3: 非法 phase 值不再静默丢弃（was `except ValueError: pass`）——
    # 约束在无 phase 上下文下运行可能产生误导性 PASS/BLOCK，必须显式上报。
    phase_problems: list[str] = []
    if target_path: ctx["target_path"] = target_path
    if allowed_paths: ctx["allowed_paths"] = allowed_paths
    if current_phase:
        try: ctx["current_phase"] = Phase(current_phase)
        except ValueError:
            phase_problems.append(
                f"current_phase={current_phase!r} 非法，约束在无 phase 上下文下运行"
            )
    if target_phase:
        try: ctx["target_phase"] = Phase(target_phase)
        except ValueError:
            phase_problems.append(
                f"target_phase={target_phase!r} 非法，约束在无 phase 上下文下运行"
            )

    result = hc.check_all(ctx)
    blockers = [v.message for v in result.violations if v.severity == Severity.BLOCKER]
    warnings = [v.message for v in result.violations if v.severity == Severity.WARNING]

    return {
        "passed": result.passed,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        # T-0107 D4-3: 非法 phase 告警字段（调用方可据此拒绝误导性判定）
        "phase_problems": phase_problems,
        "phase_problem_count": len(phase_problems),
    }
