# T-0035 Registration Validation v0.1

Validated: `2026-07-18T15:20:38.7983203+08:00` registration package.

## Startup Preconditions

- `T-0034` task status: `completed`.
- `current_gate_id` before registration: `null`.
- Pending Gates before registration: none.
- `.ai/tasks/T-0035.md` before registration: absent.
- T-0035 task graph node before registration: absent.
- T-0035 Gate before registration: absent.
- Candidate/global/old evidence files: read-only and baseline-captured.

## Post-Registration Validator

Command:

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Observed:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0035
[error] Pending gate(s) require user decision before continuing: G-T-0035-IMPLEMENT-T0030-REPAIR-AND-APPROVED-CONTINUITY-INTERFACES-IN-ISOLATED-CANDIDATE
VALIDATE_EXIT_CODE=2
```

Assessment: expected single pending-Gate blocker; no additional warning/error.

## Structural Assertions

- `state.current_task_id == T-0035`.
- `state.current_gate_id` equals the registered Gate ID.
- Exactly one pending Gate exists and it belongs to T-0035.
- T-0035 task status is `active` and task graph status is `active`.
- No candidate or global Project Governor path appears in the registration changed-path set.
