from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_auditor import audit_handoff_model
from governor_lib import ai_dir, current_task_id, governance_invariant_errors, project_root_arg, read_text


REQUIRED_HEADINGS = [
    "## Product Direction And Authority", "## Current Phase", "## Current Task",
    "## Allowed Scope", "## Forbidden Scope", "## Verified", "## Unverified",
    "## Evidence", "## Integration Impact", "## Structured Lifecycle",
    "## Structured Next Action", "## Checkpoint", "## Next Session First Step",
]


def main() -> int:
    args = project_root_arg().parse_args()
    root = Path(args.project_root).resolve()
    text = read_text(ai_dir(root) / "HANDOFF.md")
    errors = []
    if not text:
        errors.append("Missing or empty .ai/HANDOFF.md")
    errors.extend(f"HANDOFF.md missing heading: {heading}" for heading in REQUIRED_HEADINGS if heading not in text)
    errors.extend(governance_invariant_errors(root))
    errors.extend(audit_handoff_model(root, text))
    errors = list(dict.fromkeys(errors))
    blocker_errors = [e for e in errors if not str(e).startswith("[warn]") and not str(e).startswith("[legacy]")]
    legacy_errors = [e for e in errors if str(e).startswith("[legacy]")]
    for error in legacy_errors:
        print(f"[legacy] {error[9:]}")
    # T-0101: idle 稳态语义分流（与 validate_state.py 对齐）——
    # 仅 NO_ACTIVE_TASK 一个 blocker（current_task_id=null 合法阻塞态）
    # → 独立 [info] 段 + exit 3；存在其他 blocker → 保持 [error] + exit 2（fail-closed）。
    no_active_task_msg = "NO_ACTIVE_TASK: state.current_task_id is null"
    if current_task_id(root) is None and blocker_errors == [no_active_task_msg]:
        print(
            f"[info] {no_active_task_msg}（合法阻塞态：等待任务发起；handoff 审计不含 "
            "usable 语义）"
        )
        return 3
    for error in blocker_errors:
        print(f"[error] {error}")
    if blocker_errors:
        return 2
    print("[ok] handoff audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
