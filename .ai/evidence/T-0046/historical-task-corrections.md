# T-0046 Historical Task Status Corrections

## Context
validate_state.py detects mismatches between task file status and task_graph status
for historical tasks. Per T-0046 rules, we do NOT modify historical evidence.

## Detected Mismatches (as of T-0046 reconciliation)
- T-0002: task_file=active, task_graph=in_progress — legacy inconsistency, not corrected (preserving historical evidence)
- T-0004: task_file=active, task_graph=completed — legacy inconsistency, not corrected (preserving historical evidence)
- T-0005: task_file=active, task_graph=completed — legacy inconsistency, not corrected (preserving historical evidence)
- T-0007: task_file=active, task_graph=in_progress — legacy inconsistency, not corrected (preserving historical evidence)
- T-0009: task_file=in_progress, task_graph=completed — legacy inconsistency, not corrected (preserving historical evidence)
- T-0021: task_file=in_progress`（gate 已批准，等待用户精确执行请求）, task_graph=completed — legacy inconsistency, not corrected (preserving historical evidence)

## Resolution
These are classified as **legacy/historical** inconsistencies from before the T-0046
governance reconciliation. They are NOT treated as current task errors.
The validate_state.py and governor_lib.py have been updated to distinguish
current task errors (hard errors) from historical task inconsistencies (legacy warnings).

## T-0045 Dangling Reference
T-0045 was referenced in state.yaml but had no task file. It is recorded as a
governance drift artifact and is NOT falsely marked as completed.
