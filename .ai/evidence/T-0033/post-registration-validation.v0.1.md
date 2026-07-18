# T-0033 Post-Registration Validation

Command: `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`

Exit code: `2`

Actual output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0033
[warn] Missing evidence commands: C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0033\commands.md
[error] Pending gate(s) require user decision before continuing: G-T-0033-ESTABLISH-ISOLATED-CANDIDATE-RESTORE-ACTIVATION-BOUNDARY
[error] Historical task status mismatch: T-0002 task=active task_graph=in_progress
[error] Historical task status mismatch: T-0004 task=active task_graph=completed
[error] Historical task status mismatch: T-0005 task=active task_graph=completed
[error] Historical task status mismatch: T-0007 task=active task_graph=in_progress
[error] Historical task status mismatch: T-0009 task=in_progress task_graph=completed
[error] Historical task status mismatch: T-0028 task=completed task_graph=in_progress
```

The pending-gate blocker and six preserved historical mismatches are expected. The additional missing-`commands.md` warning is not allowed by the T-0033 registration specification.

The conflict is deterministic: current `governor_lib.py` hardcodes `.ai/evidence/<current-task>/commands.md`, while the explicitly authorized T-0033 fixed evidence list excludes and forbids that file. No forbidden `commands.md` file was created and no Project Governor script was modified.
