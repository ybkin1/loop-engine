# Post-Registration HANDOFF Audit - T-0031

Command:

    & 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'

Exit code: `2`

Output:

    [error] Pending gate(s) not resolved: G-T-0031-T0030-IMPLEMENTATION-REVIEW-ACTIVATION-BOUNDARY-REPAIR-PLANNING
    [error] Current task status missing or invalid: T-0031
    [error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0004 task=active task_graph=completed
    [error] Historical task status mismatch: T-0005 task=active task_graph=completed
    [error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
    [error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
    [error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress
    [error] HANDOFF next action mismatch: expected marker approve or reject

The pending-gate blocker is expected. The task-status and HANDOFF next-action errors are new governance blockers, so registration is not considered successfully validated and no repair was attempted in this turn.
