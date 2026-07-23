# T-0036 Registration Validation v0.1

Command:

```text
C:\Python312\python.exe -B C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Environment: process-local `PYTHONDONTWRITEBYTECODE=1`.

Python exit code: `2`.

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[error] Pending gate(s) require user decision before continuing: G-T-0036-INDEPENDENT-CANDIDATE-REPAIR-CONTINUITY-FRESH-SESSION-RECOVERY-REVIEW
```

Result: `EXPECTED_PENDING_GATE_BLOCKER_ONLY`.

- Current task: `T-0036`.
- Current Gate: `G-T-0036-INDEPENDENT-CANDIDATE-REPAIR-CONTINUITY-FRESH-SESSION-RECOVERY-REVIEW`.
- Pending Gate count: `1`.
- T-0036 Gate record count: `1`.
- T-0036 task_graph node count: `1`.
- No additional validator warning or error was emitted.

This expected blocker is the registration stop condition, not a review verdict.
