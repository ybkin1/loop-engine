# T-0036 F003 Closure Decision Execution Commands

Gate: `G-T-0036-F003-CLOSURE-DECISION-V0-1`

## Preflight

- Read current state, HANDOFF, T-0036, Gate record, task graph, closure decision packet, and latest rereview evidence.
- Run `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py .` -> `0`.
- Run `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py .` -> `0`.
- Verify exact execution request matches the approved Gate and no pending Gate exists.

## Bounded execution

- Record the latest rereview `PASS` as the evidence basis for closure.
- Mark only `T0036-F003` closed in the current T-0036 governance projection.
- Keep T-0036 active and retain all user-acceptance, project-PASS, installation, activation, runtime/tool, downstream-task, and real-project boundaries.

## Postflight

- Run `validate_state.py` and `audit_handoff.py`.
- Verify `T0036-F003` is absent from `blocking_findings`, the Gate is `closure_completed`, and no candidate path changed.
