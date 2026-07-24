# T-0036 F003 Fresh Rereview Controlled Runner Results

## Focused F003 Protocol Tests

RUN_002 through RUN_009 passed `8/8`, exit code `0`.

Covered:

- real passing unittest
- fake success text with real failure
- zero-test stdout spoof
- adapter fingerprint drift
- missing, unknown, and duplicate envelope fields
- wrong nonce, wrong fingerprint, zero-test, and count mismatch
- failure, error, skip, and unexpected-success outcomes

## Full Structured Adapter Regression

Execution-time rerun command used `C:/Python312/python.exe -B scripts/unittest_result_adapter.py tests/test_project_governor_consistency.py --result-envelope <temp> --run-nonce T0036-F003-REREVIEW-FULL-RERUN3-20260721`.

Result: `64/64`, exit code `0`.

Envelope facts:

- schema: `UnittestResultEnvelope/v1`
- run nonce: `T0036-F003-REREVIEW-FULL-RERUN3-20260721`
- adapter SHA-256: `C57A5EB8567B0E6E07E9950138A1D0B134E48494A7F2A339DA580386085058AA`
- test SHA-256: `FD896C3D4062938DCE0C6CA3C462DFE2BAA2DF626408D596AE6898E1C70856CB`
- discovered IDs: `64`
- tests_run: `64`
- failures/errors/skips/unexpected successes: `0/0/0/0`
- result SHA-256: `DA25095B5B3A4B35D303F8BBCAD4772E5D3FB5E45FD2AEA37F44A35BF324A4C2`

Earlier full-suite attempts failed only due to execution-time governance projection mismatches, then passed after task and gate projection matched the controlled validation requirements.

## Current-Disk Independent Reproduction

A later fresh independent `fork_context=false` reviewer and the main controller reran the checks from the completed current disk state.

- Focused RUN_002 through RUN_009: passed `8/8`, exit code `0`.
- Full structured adapter regression: failed `63/64`, exit code `1`.
- Failing test: `test_project_governor_consistency.T0036RepairRedContractTests.test_E2E_CURRENT_001_contract_entrypoint_exists`.
- Failure reason: `AUTHORITY_MISSING: Controlled validation requires one Gate-bound in-progress execution`.
- Local post-compaction nonce: `T0036-F003-LOCAL-POST-INDEPENDENT-20260721`.
- Local post-compaction result SHA-256: `AB7EE16606E63783A26295EC015F3215AE5019166704D821D651223AD3261D26`.

This means the full adapter regression result is not reproducible from the completed current disk state without a temporary in-progress execution projection.
