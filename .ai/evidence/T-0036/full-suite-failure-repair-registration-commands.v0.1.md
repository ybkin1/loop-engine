# T-0036 Full-Suite Failure Repair Gate Registration Commands v0.1

Gate: `G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
Project root: `C:\Users\Administrator\.codex\loop-engine-lab`
Registration mode: `create_pending_gate_only`

## Startup

- `validate_state.py`: PASS before registration; no pending Gate.
- `git status --porcelain -uall`: 157 lines; staged 0; tracked worktree 6; untracked 151; output SHA-256 `560B39A9D9E27D6D22D399BD578C2E0BC8ADA4ED16E87B3047EC0621C1CFA400`.
- Candidate failing test baseline: 13152 bytes, SHA-256 `ED22E7DCBFF310EB91AFB9713A2076E7C7140C77C37CEA418794E87717C77385`.
- Failure reproduction: full suite `40 passed, 6 failed`; focused suite `28 passed`.

## Registration assertions

- Only this Gate's three additive evidence files and the three governance projections are changed by registration.
- No candidate test, Project Governor script, global skill file, T-0036 material, freeze manifest, or prior review evidence is modified.
- Gate creation is not approval and does not execute the fixture repair.

## Post-registration checks

- Parse `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml` as UTF-8 YAML.
- Confirm exactly `G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1` is pending.
- Run `git diff --check`.
- Run `validate_state.py`; expected result is a pending-Gate user-decision stop.

## Required next decision

The user must approve or reject the exact Gate ID. Even after approval, a separate exact execution request is required before the candidate test file can change.

## Approval record

- approval_text: `批准 G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
- approval_actor: `user`
- approval_source: `explicit_user_message`
- approved_at: `2026-07-24T13:52:38+08:00`
- resulting_state: `approved_not_started`
- repair_execution_started: `false`
- exact execution request still required: `执行 G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
