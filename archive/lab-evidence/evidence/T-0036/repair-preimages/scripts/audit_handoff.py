from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governor_lib import (
    ai_dir,
    current_task_id,
    evidence_status,
    governance_invariant_errors,
    handoff_contract_errors,
    pending_gates,
    project_root_arg,
    read_text,
    task_status,
)


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
    errors.extend(governance_invariant_errors(root))

    status = task_status(root, task_id)
    if task_id and task_id not in section(text, "## Current Task"):
        errors.append(f"HANDOFF current task mismatch: expected {task_id}")
    handoff_status = status_from_handoff(text)
    if status and handoff_status != status:
        errors.append(f"HANDOFF task status mismatch: expected {status}, found {handoff_status or 'missing'}")
    errors.extend(handoff_contract_errors(root, text))

    errors = list(dict.fromkeys(errors))
    for item in warnings:
        print(f"[warn] {item}")
    for item in errors:
        print(f"[error] {item}")
    if errors:
        return 2
    print("[ok] handoff audit passed")
    print(f"[evidence] {detail}")
    return 0


def section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


def status_from_handoff(text: str) -> str | None:
    current = section(text, "## Current Task")
    marker = "Status: `"
    start = current.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = current.find("`", start)
    return current[start:end] if end >= 0 else None


if __name__ == "__main__":
    raise SystemExit(main())
