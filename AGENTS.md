# Project Instructions

## Loop Governance

For implementation, review, debugging, design, handoff, task state changes, or governance work in this project, invoke the `loop-governance` skill before proceeding.

Project root:

`C:\Users\Administrator\ZCodeProject\loop-engine`

Required startup steps:

1. Read the latest user request first.
2. Confirm the project root.
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, the current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Run `python .zcode/tools/validate_state.py` (使用 `C:\Python312\python.exe`)。
5. If a pending gate exists, stop and ask the user to approve or reject it.
6. Continue only inside the approved task and gate scope.

## Boundaries

- Do not install or enable skill, MCP, agent, automation, or protocol behavior without a separate explicit user gate.
- Do not enter real business projects without a separate explicit user gate.
- Do not deploy, roll back, change databases, change permissions, handle secrets, perform payment actions, touch production data, or run migrations without a separate explicit user gate.
- Treat reviewer PASS, validator success, tests, and AI recommendations as evidence only, not user approval.
