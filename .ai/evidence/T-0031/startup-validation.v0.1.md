# Startup Validation - T-0031

Command:

    & 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'

Exit code: `2`

Output:

    [project-governor] phase: S0-method-repair
    [project-governor] current_task_id: T-0030
    [error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0004 task=active task_graph=completed
    [error] Historical task status mismatch: T-0005 task=active task_graph=completed
    [error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
    [error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress

The result is recorded as a real blocker inventory, not as success. The six known historical mismatches were not modified.
