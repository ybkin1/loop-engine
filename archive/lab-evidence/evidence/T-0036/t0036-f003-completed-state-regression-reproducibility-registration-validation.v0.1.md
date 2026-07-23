# T-0036 F003 Completed-State Reproducibility Registration Validation

Gate: `G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1`

## Pre-Registration

Command:

`C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`

Observed:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[ok] state is usable
LASTEXITCODE=0
```

## Post-Registration

Command:

`C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`

Observed mechanical result after this registration:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[error] Pending gate(s) require user decision before continuing: G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1
LASTEXITCODE=2
```

This exit `2` is the intended pending-gate blocker, not project damage. Registration stops here. No approval, repair execution, rereview, candidate/test modification, production authority fabrication, or Gate closure is performed.
