# T-0036 F003 Fresh Rereview Findings

Evidence-only verdict: `REPAIR_REQUIRED`

Finding: `T0036-F003`

Closure status: remains open.

## Basis

- `validation_runner.py` accepts only Gate-bound `UnittestResultEnvelope/v1` protocol for controlled test success.
- Arbitrary commands and zero-test stdout spoof paths fail closed with `UNSUPPORTED_TEST_PROTOCOL`.
- Bound success requires verified envelope, exit code `0`, no timeout, and no output limit.
- Stdout and stderr are recorded only as bytes and SHA-256 diagnostics; they do not decide test identity, test count, or PASS.
- Envelope verification binds nonce, adapter fingerprint, test fingerprint, exact discovered IDs, `tests_run > 0`, result hash, and clean outcome.
- Focused protocol tests passed `8/8`.
- Full structured adapter regression passed `64/64` only after temporary execution-time governance projection.
- A later fresh independent current-disk reproduction failed the full structured adapter regression `63/64` with `AUTHORITY_MISSING`, because the completed current disk state no longer contains one Gate-bound `in_progress` execution.

## Finding

The original zero-test stdout spoof path appears repaired, but the rereview requirement to independently run focused tests and full regression from disk is not satisfied by a stable completed-state reproduction. `T0036-F003` remains blocking until a repair or rereview design can reconcile full-regression reproducibility with the Gate-bound execution authority model.

## Boundaries

This verdict does not authorize repair execution, user acceptance, project PASS, installation, activation, T-0037, runtime enablement, global Project Governor modification, or real-project entry.
