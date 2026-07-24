# G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1 Gate Request

Requested under explicit user registration-only authorization on 2026-07-21.

This request registers one pending repair Gate only. It does not approve or execute repair.

Gate ID: `G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1`

Task: `T-0036`

Finding: `T0036-F003`

## Target

Make the complete structured adapter regression independently reproducible from the stable completed-state disk while preserving the requirement that real controlled validation accepts only one correctly bound Gate-bound `in_progress` execution.

The current `63/64` result is not described as the original stdout spoof remaining exploitable. The original zero-test stdout spoof appears rejected, stdout/stderr remain diagnostic evidence only, and the sole current failure is `AUTHORITY_MISSING` because `E2E-CURRENT-001` requires one Gate-bound `in_progress` execution that is absent from stable completed state.

## Preferred Future Repair

Prefer a test or isolated temporary fixture change that constructs an explicit, closed, non-production `in_progress` state in a temporary directory. The fixture must not depend on the live Gate, must not be treated as a real Gate or runtime authority, and must not alter the completed project state. Production candidate logic changes are not presumed necessary.

## User Decision Phrases

- Approval: `批准 G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1`
- Rejection: `拒绝 G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1`
- Later execution: `执行已批准的 G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1`

Approval is not execution. A later exact execution request is required. A later fresh independent rereview must be separately gated and executed before `T0036-F003` can close.

