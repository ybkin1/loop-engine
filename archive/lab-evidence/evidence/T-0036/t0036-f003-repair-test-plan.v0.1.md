# T-0036 F003 Repair Test Plan v0.1

Gate: `G-T-0036-REPAIR-F003-CONTROLLED-TEST-RESULT-PROTOCOL-V0-1`

Status: pre-implementation plan only.

| ID | Scenario | Required GREEN result |
| --- | --- | --- |
| F003-RED-001 | Zero-test script prints `Ran 1 test ...` and `OK`, exit 0 | Rejected; no bound success |
| F003-RED-002 | Arbitrary script prints a valid-looking JSON envelope | `UNSUPPORTED_TEST_PROTOCOL` or envelope rejection |
| F003-PROTO-001 | Exact Gate-bound adapter discovers and runs approved tests | Structured IDs/count/result bind; stdout is diagnostic only |
| F003-PROTO-002 | Zero tests discovered | Failed validation |
| F003-PROTO-003 | Wrong/missing/replayed nonce | Failed validation |
| F003-PROTO-004 | Malformed/unknown/duplicate envelope field | Closed-schema rejection |
| F003-PROTO-005 | Adapter fingerprint differs from Gate | Failed validation before success bind |
| F003-PROTO-006 | Test fingerprint or discovered ID set differs | Failed validation |
| F003-PROTO-007 | `testsRun` differs from discovered IDs | Failed validation |
| F003-PROTO-008 | Failure/error/unexpected success exists | Failed validation |
| F003-PROTO-009 | Envelope claims success but process exits non-zero | Failed validation |
| F003-PROTO-010 | Process exits zero but envelope absent | Failed validation |
| F003-REG-001 | Existing controlled-runner and boundary regressions | PASS without skipped/xfail weakening |
| F003-BND-001 | Global Project Governor, markers, protected anchors drift | Completion blocked |

RED evidence must retain the independent rereview reproduction. GREEN evidence must include the exact adapter/test fingerprints, structured result envelope hash, actual command result, and per-scenario disposition.

Fresh independent rereview remains separately gated and must reproduce `F003-RED-001` without trusting repair-session conclusions.
