# T-0036 F003 Post-Completed-State Rereview Protocol Results

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-F003-POST-COMPLETED-STATE-REPAIR-V0-1`

## Focused F003 Checks

- Corrected direct selector: `T0036RepairRedContractTests.test_RUN_002` through `test_RUN_009`.
- Result: `8/8`, failures `0`, errors `0`, actual exit code `0`.
- Two earlier selector-construction attempts returned exit code `1` because the module/class selector was wrong; no candidate test failure was bound to those attempts.

## Full Structured Run

- Exact executable/argv: `C:/Python312/python.exe -B scripts/unittest_result_adapter.py tests/test_project_governor_consistency.py --result-envelope <temporary> --run-nonce T0036-F003-POST-COMPLETED-STATE-REREVIEW-FULL-20260721`.
- Actual process exit code: `0`.
- Protocol: `UnittestResultEnvelope/v1`; nonce matched exactly.
- Adapter SHA-256: `C57A5EB8567B0E6E07E9950138A1D0B134E48494A7F2A339DA580386085058AA`.
- Test SHA-256: `FFDE0360908BA4DB852151426653E4F2C00BB85BC895CE3BC7D2FB6BAA511E14`.
- Discovered IDs: `64`; ID-list SHA-256: `BFF820A568336F75B92CFB6FE53AB910EC4D7B764D9FB766FFD276EF310883E6`.
- `tests_run`: `64`; failures/errors/skips/unexpected successes: `0/0/0/0`; `successful: true`.
- Result SHA-256: `1688608C4B254A30BCED5F9D0B49CBA5D3B60EDCC47A96B10B3FF08933A31FF5`.
- Envelope file SHA-256: `AB804DD28A3CB4372BA882D44C77900644E13FA79410C174E12AD64E1E9815FE`.
- `test_E2E_CURRENT_001` passed inside the isolated `fixture_only` temporary mirror; fixture-only `64/64` did not mutate live Gate state.

## Authority And Diagnostics

- Real completed-state `run_gate_bound_validation()` returned `AUTHORITY_MISSING`; the checking process actual exit code was `0`.
- stdout: `0` bytes, SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- stderr: `12067` bytes, SHA-256 `526DA2587D442EA87786E5000307D5670EA99A9BE18C328CAF948FECB75DD91B`.
- stdout/stderr were retained only as diagnostics; identity, count, and success came from the structured envelope and binding checks.
- Temporary directory existed before cleanup and was absent after cleanup.
