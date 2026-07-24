# T-0036 F003 Repair Implementation Report v0.1

Completed: `2026-07-20T18:49:27.3917473+08:00`

## Executor Result

`PASS_PENDING_FRESH_INDEPENDENT_REREVIEW`

This is repair-executor evidence only. It does not independently close T0036-F003.

## Behavior Change

- Removed stdout/stderr regex and `OK` text from controlled-test success authority.
- Added exact Gate-bound `scripts/unittest_result_adapter.py` using `unittest` loader/runner APIs.
- Added create-only closed `UnittestResultEnvelope/v1` with parent nonce, adapter/test fingerprints, exact discovered IDs, actual `tests_run`, outcomes, timestamps, and canonical result hash.
- Parent runner accepts only exact Python/`-B`/adapter/test argv and independently verifies protocol schema/config, nonce, fingerprints, IDs/count, clean outcome, result hash, bounded bytes, stable file identity, and non-reparse subjects.
- Stdout/stderr remain hashed diagnostics only.

## RED To GREEN

- RED: zero-test command printed `Ran 1 test in 0.001s` and `OK`; old runner returned exit `0` and claimed one test.
- GREEN: the same arbitrary script is rejected before execution binding with `UNSUPPORTED_TEST_PROTOCOL`.
- Focused protocol tests: `8/8`, exit `0`.
- Full regression suite after final changes: `64/64`, exit `0`.
- Actual adapter final run: 64 unique discovered IDs, `tests_run: 64`, zero failures/errors/skips/unexpected successes, exit `0`.

## Adversarial Coverage

- stdout-only spoof and fake success with real failure
- unsupported arbitrary command
- adapter and test fingerprint drift
- missing, malformed, duplicate-field, unknown-field, wrong-nonce, wrong-fingerprint, wrong-ID/count, zero-test, failed/error/skipped/unexpected-success envelope
- stale targets, timeout/output limits, evidence manifest, protected fingerprints, E2E-CURRENT-001, and existing regressions

## Threat Limit

The adapter and test bytes are trusted because they are exact Gate-bound fingerprinted subjects. Test code runs in the adapter interpreter; this repair does not claim a cryptographic boundary against hostile approved test code.

## Residual Boundaries

- F001/F002 remain `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE`.
- Candidate live validation still fails closed with `PROJECT_CONTINUITY_MISSING` because live structured state is absent.
- Installation eligibility remains `BLOCKED`.
- Global Project Governor HANDOFF tooling was not modified.
- Fresh independent rereview, installation, activation, T-0037, runtime/tool enablement, and real-project entry were not performed or authorized.
