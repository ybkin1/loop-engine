# T-0036 F003 Completed-State Reproducibility Execution RED Results v0.1

Exact command:

`C:\Python312\python.exe -B scripts/unittest_result_adapter.py tests/test_project_governor_consistency.py --result-envelope <temp> --run-nonce T0036-F003-RED-COMPLETED-STATE-20260721`

Environment: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH` absent/empty. The live Gate was not changed to `in_progress`.

Observed result:

- Exit code: `1`
- Discovered tests: `64`
- Tests run: `64`
- Passed: `63`
- Failed: `1`
- Failing test: `test_project_governor_consistency.T0036RepairRedContractTests.test_E2E_CURRENT_001_contract_entrypoint_exists`
- Failure: `AUTHORITY_MISSING: Controlled validation requires one Gate-bound in-progress execution`
- Stdout: empty; stdout/stderr were diagnostic only and not used as test authority.

This reproduces the completed-state regression without mutating the live Gate. The temporary envelope and diagnostic files were cleaned after capture; no production authority was fabricated.

