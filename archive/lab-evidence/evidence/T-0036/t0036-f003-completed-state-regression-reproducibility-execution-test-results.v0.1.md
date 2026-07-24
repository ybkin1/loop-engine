# T-0036 F003 Completed-State Reproducibility Execution Test Results v0.1

## GREEN Structured Run

Exact command:

`C:\Python312\python.exe -B scripts/unittest_result_adapter.py tests/test_project_governor_consistency.py --result-envelope <temp> --run-nonce T0036-F003-GREEN3-COMPLETED-STATE-20260721`

Result: exit `0`, `64/64`, no failures/errors/skips/unexpected successes.

Envelope:

- Schema: `UnittestResultEnvelope/v1`
- Discovered unique IDs: `64`
- `tests_run`: `64`
- Failures/errors/skips/unexpected successes: `0/0/0/0`
- `successful`: `true`
- Result envelope SHA-256: `AB89E1922C9951663912E2552EE657556BBCBE79FD131E5FF66C6F615E778465`
- Envelope file SHA-256: `647FC29B4FA8B6C8A03E4D208A14CA71A7DBEDE177E7F5709B07D4D3E61E54AE`
- Adapter SHA-256: `C57A5EB8567B0E6E07E9950138A1D0B134E48494A7F2A339DA580386085058AA`
- Test SHA-256: `FFDE0360908BA4DB852151426653E4F2C00BB85BC895CE3BC7D2FB6BAA511E14`
- Stdout: `0` bytes, SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- Stderr: `25096` bytes, SHA-256 `3520F6E88F233F323298136A86DCBA53372E9A4749209A6116ECB3C40ABC7904`

## Focused F003 Protocol Coverage

RUN_002 through RUN_009 all passed: `8/8`.

Covered real passing tests, failure-vs-fake-success, zero-test stdout spoof rejection, adapter/test fingerprint drift, malformed/missing/duplicate envelopes, nonce/fingerprint/ID/count mismatch, and non-clean outcomes.

`test_E2E_CURRENT_001_contract_entrypoint_exists` passed with a temporary `fixture_only` Gate-bound `in_progress` mirror state.

All temporary envelope, stdout, and stderr files were removed after hashes were recorded.

