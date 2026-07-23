# T-0036 F003 Completed-State Reproducibility Execution Implementation Report v0.1

Executor result: `PASS_PENDING_FRESH_INDEPENDENT_REREVIEW`

Only the approved test path changed:

`candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py`

Minimal repair:

- Assert the real completed-state `run_gate_bound_validation()` fails closed with `AUTHORITY_MISSING`.
- In the temporary E2E mirror, synchronize T-0036 task file and task graph to `in_progress`.
- Replace dependence on a live Gate with a synthetic `fixture_only` approved Gate and isolated approval/execution evidence.
- Keep the fixture Gate's `execution_status: in_progress` confined to the temporary mirror.
- Preserve live Gate status `approved_not_started` during test execution.

Protected production behavior was not changed:

- `validation_runner.py` was not modified.
- Gate-bound `in_progress` and task-status checks remain required.
- Completed live state still returns `AUTHORITY_MISSING`.
- stdout/stderr remain diagnostic only.
- `UnittestResultEnvelope/v1` binding remains unchanged.

No fresh independent rereview was executed.

