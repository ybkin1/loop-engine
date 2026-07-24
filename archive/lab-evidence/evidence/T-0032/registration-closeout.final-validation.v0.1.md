# T-0032 Registration Closeout Final Validation

Command: `validate_state.py`

Exit code: `2`

Actual result: only the six preserved historical status mismatches for T-0002, T-0004, T-0005, T-0007, T-0009, and T-0028 were reported.

Confirmed:

- all three T-0032 gates remain `approved`;
- pending gate count is zero;
- `state.current_task_id` is `T-0032` and `state.current_gate_id` is null;
- T-0032 task and task graph are `completed`;
- T-0033 through T-0039 have no task files or task-graph nodes;
- no additional validation error occurred.
