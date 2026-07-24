# Controlled Runner Results

The candidate test suite was independently executed from the frozen candidate twice:

- Command: `C:\Python312\python.exe -B candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py -v`
- First result, before the governance projection was synchronized: `57` passed, `1` failed, `58` total, exit `1`.
- Failed test: `T0036RepairRedContractTests.test_E2E_CURRENT_001_contract_entrypoint_exists`.
- Failure: controlled runner returned `AUTHORITY_MISSING: Controlled validation requires one Gate-bound in-progress execution` in the E2E mirror.

- Second result, after the separately allowed T-0036/task-graph and Gate execution-evidence projection sync (candidate unchanged): `58` passed, `58` total, exit `0`, `OK`.

Independent adversarial fixture probe:

- Temporary command printed `Ran 1 test in 0.001s` and `OK` and exited `0` without defining or running a test.
- Candidate `validation_runner.py` returned exit `0` and `[ok] CONTROLLED_VALIDATION_COMMAND_ACTUALLY_EXECUTED tests=1`.
- This demonstrates that execution occurs, but success still trusts spoofable unittest-like stdout and does not prove test identity/execution.

The controlled runner therefore closes the normal positive path, but does not independently close F003 because the adversarial zero-test stdout spoof still binds as success. The first E2E failure is retained as a startup-projection sensitivity, not a persistent candidate failure. No repository subject was changed.
