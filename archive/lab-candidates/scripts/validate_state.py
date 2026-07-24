from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_auditor import audit_handoff_model
from continuity_producer import load_project_continuity
from governor_lib import (
    GovernanceError, REQUIRED_FILES, ai_dir, current_task_id, governance_invariant_errors,
    load_yaml, pending_gates, project_root_arg, read_text,
)


def main() -> int:
    args = project_root_arg().parse_args()
    root = Path(args.project_root).resolve()
    base = ai_dir(root)
    errors = []
    for relative in REQUIRED_FILES:
        if not (base / relative).exists():
            errors.append(f"Missing .ai/{relative}")
    state = load_yaml(base / "state.yaml")
    phase = state.get("current_phase")
    task_id = current_task_id(root)
    if not phase:
        errors.append("state.yaml missing current_phase")
    if task_id and not (base / "tasks" / f"{task_id}.md").is_file():
        errors.append(f"Current task file missing: .ai/tasks/{task_id}.md")
    pending = pending_gates(root)
    if pending:
        errors.append("Pending gate(s) require user decision before continuing: " + ", ".join(str(item.get("id")) for item in pending))
    errors.extend(governance_invariant_errors(root))
    try:
        load_project_continuity(root)
    except GovernanceError as exc:
        errors.append(f"{exc.code}: {exc}")
    handoff = read_text(base / "HANDOFF.md")
    if handoff:
        errors.extend(audit_handoff_model(root, handoff))
    print(f"[project-governor] phase: {phase or 'unknown'}")
    print(f"[project-governor] current_task_id: {task_id or 'none'}")
    for error in list(dict.fromkeys(errors)):
        print(f"[error] {error}")
    if errors:
        return 2
    print("[ok] state is usable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
