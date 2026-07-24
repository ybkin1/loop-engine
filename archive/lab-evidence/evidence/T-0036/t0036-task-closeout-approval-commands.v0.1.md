# T-0036 Task-level Closeout Gate Approval Commands

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

## Pre-approval

- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0036.md`, `.ai/gates.yaml`, `.ai/task_graph.yaml`, `.ai/PROJECT.md`, and the task closeout evidence.
- `validate_state.py`: exit `1`, blocked by the pending Gate.
- `audit_handoff.py`: exit `1`, blocked by the pending Gate.
- The user's message exactly matched the Gate `approval_phrase`.

## Approval action

- Record the Gate as `approved_not_started`.
- Clear `.ai/state.yaml.current_gate_id` and the pending Gate listing.
- Keep T-0036 `active`, keep all execution/installation/activation/runtime/downstream/real-project flags false, and preserve F003 closure evidence.

## Post-approval

- Run `validate_state.py` and `audit_handoff.py`; both must pass.
- Stop before closeout execution and require the later exact execution request.
