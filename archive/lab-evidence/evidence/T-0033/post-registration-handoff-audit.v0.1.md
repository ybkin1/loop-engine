# T-0033 Post-Registration HANDOFF Audit

Command: `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab`

Exit code: `2`

Actual output:

```text
[error] Missing evidence commands: C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0033\commands.md
[error] Pending gate(s) not resolved: G-T-0033-ESTABLISH-ISOLATED-CANDIDATE-RESTORE-ACTIVATION-BOUNDARY
[error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
[error] Historical task status mismatch: T-0004 task=active task_graph=completed
[error] Historical task status mismatch: T-0005 task=active task_graph=completed
[error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
[error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
[error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress
```

The pending-gate blocker and six preserved historical mismatches are expected. The additional missing-`commands.md` error prevents a clean registration audit.

No workaround was applied because adding `commands.md` would violate the fixed evidence list and modifying the auditor or global Project Governor scripts is explicitly forbidden in this turn.
