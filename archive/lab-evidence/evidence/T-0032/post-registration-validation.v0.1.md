# Post-Registration Validation - T-0032

Command:

    & 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'

Exit code: `2`

Output:

    [project-governor] phase: S0-method-repair
    [project-governor] current_task_id: T-0032
    [error] Pending gate(s) require user decision before continuing: G-T-0032-REGISTER-T0030-REPAIR-PROGRAM-T0031-REMEDIATION-FREEZE
    [error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0004 task=active task_graph=completed
    [error] Historical task status mismatch: T-0005 task=active task_graph=completed
    [error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
    [error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress

No additional task-status, YAML, evidence-directory, or governance-state error was reported.
