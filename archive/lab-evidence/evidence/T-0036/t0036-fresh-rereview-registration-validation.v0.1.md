# T-0036 Fresh Rereview Gate Registration Validation v0.1

Validated: `2026-07-20T15:57:27.8878569+08:00`

## Mechanical Result

- YAML parsing: `PASS` for `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- Pending Gate count: exactly `1`.
- Pending Gate ID: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`.
- `state.current_gate_id`: exact match.
- `state.current_task_id`: `T-0036`; task remains `active`.
- `independent_rereview_authorized`: `false` in state and Gate.
- `repair_authorized`: `false`, meaning the completed repair authorization is closed.
- Installation, activation, runtime/tool enablement, downstream task creation, and real-project entry authorization: `false`.

## Validator And Audit Interpretation

- Immediately before registration, global Project Governor `validate_state.py`: exit `0`.
- Immediately before registration, global Project Governor `audit_handoff.py`: exit `0`.
- After registration, global `validate_state.py`: exit `2` with `Pending gate(s) require user decision before continuing: G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`.
- After registration, global `audit_handoff.py`: exit `2` with `Pending gate(s) not resolved: G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`.

The post-registration exit `2` results are the expected governance stop condition for the single pending Gate, not malformed state.

Separately, the candidate live-project validator returns exit `2`, `PROJECT_CONTINUITY_MISSING`, because live `.ai/project_continuity.yaml` is absent. That is expected fail-closed candidate behavior and does not establish a complete production validation path.

## Boundary Result

- Candidate: 16 files, 2 directories, 0 reparse points, 0 cache/compiled artifacts.
- All 16 candidate SHA-256, size, and mtime_ns values match the registration freeze.
- All 33 protected subjects match the repair-final protected baseline: drift `0`.
- Candidate `NOT_INSTALLED` and `NOT_ACTIVATED`: unchanged.
- Live `.ai/project_continuity.yaml`: absent.
- Live `.ai/transaction_registry.yaml`: absent.
- T-0037: absent.
- No rereview was executed and no finding was independently closed.

Result: `PENDING_GATE_REGISTERED_MECHANICALLY_VALID`.
