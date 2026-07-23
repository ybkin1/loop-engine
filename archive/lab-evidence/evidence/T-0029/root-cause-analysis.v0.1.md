# Root Cause Analysis - T-0029

## Confirmed Failure

T-0028 is `completed` in `.ai/tasks/T-0028.md` but `in_progress` in `.ai/task_graph.yaml` after closeout.

An isolated fixture under `.ai/evidence/T-0029/reproduction-fixture/` reproduced the behavior with the unmodified Project Governor scripts:

1. The fixture task file and task graph both started as `completed`.
2. `close_session.py` returned exit code `0`.
3. The task file remained `completed`.
4. The task graph was overwritten to `in_progress` with note `handoff generated`.
5. `validate_state.py` returned exit code `0` and `[ok] state is usable`.
6. `audit_handoff.py` returned exit code `0` and `[ok] handoff audit passed`.

## Direct Root Cause

`close_session.py` initializes closeout status to `in_progress` and only changes it to `blocked` for a pending gate. It never reads the task file lifecycle status. It then calls `append_task_graph_status`, which updates the matching task graph node in place.

The closeout operation therefore performs an implicit lifecycle transition even though generating a handoff should be a projection/rendering operation.

## Contributing Causes

- No single documented source of truth exists for task lifecycle status.
- `append_task_graph_status` is named like an event append but actually overwrites the current task graph node.
- `validate_state.py` checks file presence, current task existence, evidence directory presence, and pending gates, but not cross-artifact consistency.
- `audit_handoff.py` checks headings, placeholders, evidence presence, and pending gates, but not semantic agreement with state/task/gate/task graph records.
- HANDOFF generation uses a generic next-step sentence and generic startup prompt, independent of task terminal state and approved action mode.
- Closeout writes task graph, state, and HANDOFF sequentially without a transaction boundary or recovery journal.
- Action modes are not represented as a shared executable contract; current behavior relies on prompts and convention.

## Root Cause Classification

- Primary: lifecycle mutation is incorrectly coupled to handoff rendering.
- Secondary: missing semantic consistency validation.
- Tertiary: missing action-mode enforcement and atomic recovery contract.

## Non-Root Causes

- The T-0028 task file did not change during reproduction.
- Pending-gate handling is not required to trigger the completed-to-in-progress overwrite.
- The YAML writer preserves task identity; the wrong status is supplied before writing.

## Evidence

- `reproduction-fixture/task_graph.before.yaml`
- `reproduction-fixture/task_graph.after.yaml`
- `reproduction-fixture/HANDOFF.generated.md`
- `reproduction-fixture/close_session.output.txt`
- `reproduction-fixture/validate_state.output.txt`
- `reproduction-fixture/audit_handoff.output.txt`

