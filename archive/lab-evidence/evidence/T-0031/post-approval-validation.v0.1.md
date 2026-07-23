# Post-Approval Validation - T-0031

Actual output:

    [project-governor] phase: S0-method-repair
    [project-governor] current_task_id: T-0031
    [error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0004 task=active task_graph=completed
    [error] Historical task status mismatch: T-0005 task=active task_graph=completed
    [error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
    [error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress

Exit code: `2`.

Confirmed after approval recording:

- No pending gate remains.
- T-0031 is `approved_not_started`.
- `current_gate_id` is null.
- The prior T-0031 task-status blocker is resolved.
- Review, repair planning, implementation, rollback, installation, activation, and historical repair did not occur.
