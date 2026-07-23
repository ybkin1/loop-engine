# T-0036 F003 Closure Decision Approval Commands

Gate: `G-T-0036-F003-CLOSURE-DECISION-V0-1`

## Pre-approval checks

- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0036.md`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- `validate_state.py`: exit `1`, correctly blocked by the pending Gate before approval.
- `audit_handoff.py`: exit `1`, correctly blocked by the pending Gate before approval.
- Approval phrase matched the Gate's exact `approval_phrase`.

## Approval action

- Record the explicit user approval as `approved_not_started`.
- Clear the pending `current_gate_id` pointer and pending Gate listing.
- Keep closure execution and all implementation, installation, activation, runtime/tool, downstream-task, and real-project authorization flags false.

## Post-approval checks

- Run `validate_state.py` and `audit_handoff.py` after recording approval.
- Verify the Gate is `approved`, `execution_status` is `approved_not_started`, and `T0036-F003` remains open/blocking.
