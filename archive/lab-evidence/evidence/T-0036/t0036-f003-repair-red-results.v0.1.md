# T-0036 F003 Repair RED Results v0.1

Command:

`C:\Python312\python.exe -B tests\test_project_governor_consistency.py T0036RepairRedContractTests.test_RUN_004_zero_test_stdout_spoof_is_rejected -v`

Result: exit `1`, one expected test failure.

Observed vulnerable behavior:

```text
AssertionError: 0 != 2 : [ok] CONTROLLED_VALIDATION_COMMAND_ACTUALLY_EXECUTED tests=1
```

The command under validation defined and ran no tests. It only printed `Ran 1 test in 0.001s` and `OK`, then exited zero. The existing runner incorrectly bound success, reproducing T0036-F003 before implementation.
