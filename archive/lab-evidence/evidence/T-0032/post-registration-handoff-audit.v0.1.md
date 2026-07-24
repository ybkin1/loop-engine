# Post-Registration HANDOFF Audit - T-0032

Command:

    & 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'

Exit code: `2`

Output:

    [error] Pending gate(s) not resolved: G-T-0032-REGISTER-T0030-REPAIR-PROGRAM-T0031-REMEDIATION-FREEZE
    [error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0004 task=active task_graph=completed
    [error] Historical task status mismatch: T-0005 task=active task_graph=completed
    [error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
    [error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress

No additional HANDOFF task-status or next-action mismatch was reported.
