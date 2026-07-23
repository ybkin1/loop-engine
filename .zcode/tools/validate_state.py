from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_auditor import audit_handoff_model
from governor_lib import (
    GovernanceError, REQUIRED_FILES, ai_dir, current_task_id,
    governance_invariant_errors,
    load_yaml, pending_gates, project_root_arg, read_text,
)


def main() -> int:
    args = project_root_arg().parse_args()
    root = Path(args.project_root).resolve()
    base = ai_dir(root)
    errors = []

    # 1. Check required files
    for relative in REQUIRED_FILES:
        if not (base / relative).exists():
            errors.append(f"Missing .ai/{relative}")

    # 2. Check state
    state = load_yaml(base / "state.yaml")
    phase = state.get("current_phase")
    task_id = current_task_id(root)
    if not phase:
        errors.append("state.yaml missing current_phase")
    if task_id and not (base / "tasks" / f"{task_id}.md").is_file():
        errors.append(f"Current task file missing: .ai/tasks/{task_id}.md")

    # 3. Check pending gates (BLOCKER)
    pending = pending_gates(root)
    if pending:
        errors.append(
            "Pending gate(s) require user decision before continuing: "
            + ", ".join(str(item.get("id")) for item in pending)
        )

    # 4. Governance invariants (skip ProjectContinuity check for S0-init)
    errors.extend(governance_invariant_errors(root))

    # 4.5 Task contract checks (self-review prevention + input freezing)
    if task_id:
        try:
            from task_contract import check_self_review, check_input_freezing, load_task
            contract = load_task(root, task_id)
            if contract:
                errors.extend(check_self_review(contract))
                errors.extend(check_input_freezing(root, task_id, contract))
        except ImportError:
            pass  # task_contract.py not available yet
        except Exception as e:
            errors.append(f"[warn] task_contract check failed: {e}")

    # 5. ProjectContinuity — skip in S0-init (too heavy for fresh project)
    continuity_path = base / "project_continuity.yaml"
    if continuity_path.exists():
        try:
            from continuity_producer import load_project_continuity
            load_project_continuity(root)
        except (GovernanceError, ImportError) as exc:
            errors.append(f"ProjectContinuity invalid: {exc}")
    else:
        print("[loop-governance] [info] ProjectContinuity not yet created (expected in S0-init)")

    # 6. Handoff audit (skip if continuity missing, audit_handoff_model requires it)
    handoff = read_text(base / "HANDOFF.md")
    if handoff and continuity_path.exists():
        errors.extend(audit_handoff_model(root, handoff))

    # Report
    print(f"[loop-governance] project_root: {root}")
    print(f"[loop-governance] phase: {phase or 'unknown'}")
    print(f"[loop-governance] current_task_id: {task_id or 'none'}")

    blocker_errors = [e for e in errors if not str(e).startswith("[warn]")]
    warn_errors = [e for e in errors if str(e).startswith("[warn]")]

    for error in warn_errors:
        print(error)
    for error in list(dict.fromkeys(blocker_errors)):
        print(f"[error] {error}")

    if blocker_errors:
        return 2
    print("[ok] state is usable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
