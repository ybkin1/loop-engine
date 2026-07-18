from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governor_lib import (
    ai_dir,
    append_task_graph_status,
    current_task_id,
    evidence_status,
    gates,
    git_status,
    load_yaml,
    now,
    pending_gates,
    project_root_arg,
    read_text,
    write_text,
    write_yaml,
)


def main() -> int:
    parser = project_root_arg()
    parser.add_argument("--note", default="", help="Optional human summary to include")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    base = ai_dir(root)
    state = load_yaml(base / "state.yaml")
    task_id = current_task_id(root)
    task_text = read_text(base / "tasks" / f"{task_id}.md") if task_id else ""
    evidence_ok, evidence_detail = evidence_status(root, task_id)
    pending = pending_gates(root)
    all_gates = gates(root)
    docs_to_review = []
    for rel in ["CONTRACTS.md", "DECISIONS.md", "KNOWN_ISSUES.md", "ACCEPTANCE.md", "QUALITY_GATES.md"]:
        text = read_text(base / rel)
        if "TBD" in text:
            docs_to_review.append(rel)

    status = "in_progress"
    note = "handoff generated"
    if pending:
        status = "blocked"
        note = "pending gate blocks continuation"
    elif not evidence_ok:
        note = "handoff generated with missing evidence"
    if task_id:
        append_task_graph_status(root, task_id, status, note)

    state["last_handoff_at"] = now()
    write_yaml(base / "state.yaml", state)

    gate_lines = ["- none"] if not pending else [f"- {gate.get('id', 'unknown')}: {gate.get('title', 'pending gate')}" for gate in pending]
    doc_lines = ["- none"] if not docs_to_review else [f"- .ai/{rel} still contains TBD; review whether updates are required" for rel in docs_to_review]
    evidence_lines = [f"- {evidence_detail}"] if evidence_ok else [f"- MISSING: {evidence_detail}"]
    all_gate_summary = ["- none"] if not all_gates else [f"- {gate.get('id', 'unknown')}: {gate.get('status', 'unknown')} - {gate.get('title', '')}" for gate in all_gates]
    startup = (
        "Use $project-governor. Confirm the project root, read `.ai/state.yaml`, `.ai/HANDOFF.md`, "
        "and the current task file, run `validate_state.py`, resolve any pending gates with the user, "
        "then continue only inside the approved scope."
    )

    handoff = f"""# Handoff

## Current Phase

{state.get('current_phase', 'unknown')}

## Current Task

{task_id or 'none'}

{first_nonempty_section(task_text) if task_text else 'No current task file loaded.'}

## Allowed Scope

- Continue only inside `.ai/tasks/{task_id}.md` and approved gates.
- Update project facts in `.ai/` when evidence changes stable decisions or known issues.

## Forbidden Scope

- Do not approve gates without explicit user approval.
- Do not deploy, delete data, change production, migrate databases, or handle secrets without a new user approval.

## Recent Changes

{args.note or 'Generated closeout from current project files.'}

## Verified

{chr(10).join(evidence_lines)}

## Unverified

{chr(10).join(doc_lines)}

## Evidence

{chr(10).join(evidence_lines)}

## Integration Impact

- git status: {git_status(root)}
- task graph status for current task: {status if task_id else 'no current task'}

## Pending Gates And Blockers

{chr(10).join(gate_lines)}

## Gate Register Snapshot

{chr(10).join(all_gate_summary)}

## Next Session First Step

Run `python <project-governor>/scripts/validate_state.py "{root}"`, then address pending gates or missing evidence before implementation.

## Startup Prompt

{startup}
"""
    write_text(base / "HANDOFF.md", handoff)
    print(f"[ok] wrote {base / 'HANDOFF.md'}")
    print("[startup-prompt]")
    print(startup)
    if pending or not evidence_ok:
        return 2
    return 0


def first_nonempty_section(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:12])


if __name__ == "__main__":
    raise SystemExit(main())
