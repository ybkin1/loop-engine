from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governor_lib import (
    REQUIRED_FILES,
    ai_dir,
    current_task_id,
    evidence_status,
    governance_invariant_errors,
    handoff_contract_errors,
    load_yaml,
    pending_gates,
    project_root_arg,
)


def main() -> int:
    parser = project_root_arg()
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    base = ai_dir(root)
    errors: list[str] = []
    warnings: list[str] = []

    if not base.exists():
        errors.append(f"Missing .ai directory: {base}")
    else:
        for rel in REQUIRED_FILES:
            if not (base / rel).exists():
                errors.append(f"Missing .ai/{rel}")

    state = load_yaml(base / "state.yaml")
    phase = state.get("current_phase")
    if not phase:
        errors.append("state.yaml missing current_phase")

    task_id = current_task_id(root)
    if task_id:
        if not (base / "tasks" / f"{task_id}.md").exists():
            errors.append(f"Current task file missing: .ai/tasks/{task_id}.md")
        ok, detail = evidence_status(root, task_id)
        if not ok:
            warnings.append(detail)
    else:
        warnings.append("No current_task_id set")

    pending = pending_gates(root)
    if pending:
        ids = ", ".join(str(gate.get("id", "unknown")) for gate in pending)
        errors.append(f"Pending gate(s) require user decision before continuing: {ids}")
    errors.extend(governance_invariant_errors(root))
    errors.extend(handoff_contract_errors(root))

    print(f"[project-governor] phase: {phase or 'unknown'}")
    print(f"[project-governor] current_task_id: {task_id or 'none'}")
    for item in warnings:
        print(f"[warn] {item}")
    for item in errors:
        print(f"[error] {item}")
    if errors:
        return 2
    print("[ok] state is usable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
