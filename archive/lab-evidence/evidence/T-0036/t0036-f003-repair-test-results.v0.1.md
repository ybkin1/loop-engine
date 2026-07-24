# T-0036 F003 Repair Test Results v0.1

## RED

- `test_RUN_004_zero_test_stdout_spoof_is_rejected`: failed against the old runner because the spoof returned exit `0` and claimed one test.

## Focused GREEN

- RUN_002 through RUN_009: `8/8`, exit `0`.
- Covers real passing unittest, real failure with fake success text, zero-test stdout spoof, adapter/test drift, missing/unknown/duplicate envelope, nonce/fingerprint/ID/count mismatch, and non-clean outcomes.

## Full GREEN

- Candidate suite: `64/64`, exit `0`, no skipped test weakening.
- `E2E-CURRENT-001`: pass in temporary current-project-shaped fixture using the exact adapter protocol; remains fixture-only and does not establish production Stable or authority availability.

## Structured Final Run

- Adapter: `C57A5EB8567B0E6E07E9950138A1D0B134E48494A7F2A339DA580386085058AA`.
- Test file: `FD896C3D4062938DCE0C6CA3C462DFE2BAA2DF626408D596AE6898E1C70856CB`.
- Envelope result hash: `959B68653F2435C760529878A906F165FA90521749015787A44EF43E571D67F6`.
- Run nonce: `T0036-F003-FINAL-20260720`.
- Discovered unique IDs: `64`.
- Tests run: `64`.
- Failures/errors/skips/unexpected successes: `0/0/0/0`.
- Process exit: `0`.
- Stdout: 0 bytes, SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- Stderr: 25096 bytes, SHA-256 `629BB344B1ACBC6386FBF53E7EF46311FFCADA3262430BCF515CFEAB4A5FD0AE`.

Stdout/stderr were not used to establish test identity, count, or PASS.
