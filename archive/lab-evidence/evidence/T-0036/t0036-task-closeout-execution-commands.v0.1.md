# T-0036 Task-level Closeout Execution Commands

Working directory: `C:\Users\Administrator\.codex\loop-engine-lab`

## Preflight

- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0036.md`, `.ai/gates.yaml`, `.ai/task_graph.yaml`, `.ai/PROJECT.md`, and task closeout evidence.
- `validate_state.py` -> exit `0`; state usable.
- `audit_handoff.py` -> exit `0`; handoff audit passed.
- Verified Gate `approved_not_started`, T-0036 `active`, task graph `active`, `current_gate_id: null`, and exact execution phrase.
- Verified T-0036 evidence inventory: `196` files, `3` directories.

## Execution

- Applied only the approved governance projection changes and additive T-0036 execution evidence.
- Ran `close_session.py --note` after task and task graph status synchronization.

## Final validation

- Ran `validate_state.py` and `audit_handoff.py` after closeout.
- Compared protected evidence hashes and verified no candidate/test/runtime/downstream path changes.
