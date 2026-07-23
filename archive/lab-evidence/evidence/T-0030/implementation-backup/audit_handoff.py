from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governor_lib import ai_dir, current_task_id, evidence_status, pending_gates, project_root_arg, read_text


REQUIRED_HEADINGS = [
    "## Current Phase",
    "## Current Task",
    "## Allowed Scope",
    "## Forbidden Scope",
    "## Verified",
    "## Unverified",
    "## Evidence",
    "## Integration Impact",
    "## Next Session First Step",
]


def main() -> int:
    parser = project_root_arg()
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    base = ai_dir(root)
    text = read_text(base / "HANDOFF.md")
    errors: list[str] = []
    warnings: list[str] = []

    if not text:
        errors.append("Missing or empty .ai/HANDOFF.md")
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"HANDOFF.md missing heading: {heading}")
    for marker in ["TBD", "unknown"]:
        if marker in text:
            warnings.append(f"HANDOFF.md still contains placeholder-like marker: {marker}")

    task_id = current_task_id(root)
    ok, detail = evidence_status(root, task_id)
    if not ok:
        errors.append(detail)
    pending = pending_gates(root)
    if pending:
        ids = ", ".join(str(gate.get("id", "unknown")) for gate in pending)
        errors.append(f"Pending gate(s) not resolved: {ids}")

    for item in warnings:
        print(f"[warn] {item}")
    for item in errors:
        print(f"[error] {item}")
    if errors:
        return 2
    print("[ok] handoff audit passed")
    print(f"[evidence] {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
